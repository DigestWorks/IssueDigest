"""Trusted auth orchestration and cookie-only browser routes."""

from typing import Annotated, Any, Protocol

from fastapi import APIRouter, HTTPException, Request, Security
from fastapi.responses import RedirectResponse, Response
from issuedigest_domain import SessionInfo
from issuedigest_storage import (
    AuthenticationDenied,
    ConsumedLogin,
    IssuedSession,
    OAuthRepository,
    PendingLogin,
    SessionRepository,
    StorageError,
    WorkspaceAccessRepository,
)
from issuedigest_storage.sessions import valid_session_token
from starlette.concurrency import run_in_threadpool

from .auth_config import AuthConfig, visible_ascii
from .cookies import SESSION_COOKIE, clear_session_cookie, set_session_cookie
from .errors import AuthUnavailableError, EvidenceAuthenticationError, OriginDeniedError
from .evidence import COOKIE_AUTH, PROTECTED_HEADERS
from .google_oauth import GOOGLE_ISSUER, ProviderDenied, VerifiedIdentity

FLOW_COOKIE = "__Host-issuedigest_oauth"
AUTH_UNAVAILABLE = "Authentication service unavailable"


class IdentityProvider(Protocol):
    def authorize_url(self, pending: PendingLogin) -> str: ...
    async def verify_code(self, code: str, flow: ConsumedLogin) -> VerifiedIdentity: ...


class AuthService:
    """Dependencies are server-owned; no HTTP-supplied provider or identity configuration."""

    def __init__(
        self,
        config: AuthConfig,
        oauth_repository: OAuthRepository,
        session_repository: SessionRepository,
        provider: IdentityProvider,
    ):
        self.config = config
        self._oauth = oauth_repository
        self._sessions = session_repository
        self._provider = provider

    async def begin(self) -> tuple[PendingLogin, str]:
        pending = await run_in_threadpool(self._oauth.begin_login)
        return pending, self._provider.authorize_url(pending)

    async def consume(self, state: str, browser: str) -> ConsumedLogin:
        return await run_in_threadpool(self._oauth.consume_login, state, browser)

    async def complete(
        self, code: str, flow: ConsumedLogin, previous_token: str | None
    ) -> IssuedSession:
        identity = await self._provider.verify_code(code, flow)
        await run_in_threadpool(
            self._oauth.resolve_invited_identity,
            identity.issuer,
            identity.subject,
            identity.email,
            identity.authoritative_email,
        )
        return await run_in_threadpool(
            self._oauth.issue_authorized_session,
            identity.issuer,
            identity.subject,
            previous_token if valid_session_token(previous_token) else None,
        )

    async def logout(self, token: str) -> None:
        await run_in_threadpool(self._sessions.revoke_session, token)


def _same_origin(request: Request, service: AuthService) -> None:
    if request.headers.getlist("origin") != [service.config.public_origin] or (
        "sec-fetch-site" in request.headers
        and request.headers.getlist("sec-fetch-site") != ["same-origin"]
    ):
        raise HTTPException(403, "Request origin denied")


def _callback_response(destination: str) -> RedirectResponse:
    response = RedirectResponse(destination, status_code=303)
    response.delete_cookie(FLOW_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


def auth_router(
    service: AuthService | None, workspace: WorkspaceAccessRepository | None
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/auth")
    errors: dict[int | str, dict[str, Any]] = {
        401: {
            "description": "Authentication required",
            "headers": PROTECTED_HEADERS,
            "model": EvidenceAuthenticationError,
        },
        403: {
            "description": "Request origin denied",
            "headers": PROTECTED_HEADERS,
            "model": OriginDeniedError,
        },
        503: {
            "description": AUTH_UNAVAILABLE,
            "headers": PROTECTED_HEADERS,
            "model": AuthUnavailableError,
        },
    }

    redirect_headers = PROTECTED_HEADERS | {
        "Location": {"description": "Fixed server destination", "schema": {"type": "string"}},
    }

    @router.post(
        "/google/start",
        status_code=303,
        responses=errors
        | {
            303: {
                "description": "Google authorization or fixed login error",
                "headers": redirect_headers,
            },
        },
    )
    async def start(request: Request) -> Response:
        if service is None:
            raise HTTPException(503, AUTH_UNAVAILABLE)
        _same_origin(request, service)
        try:
            pending, url = await service.begin()
        except StorageError:
            return _callback_response("/login?error=unavailable")
        response = RedirectResponse(url, status_code=303)
        response.set_cookie(
            FLOW_COOKIE,
            pending.browser_token,
            max_age=600,
            path="/",
            secure=True,
            httponly=True,
            samesite="lax",
        )
        return response

    @router.get(
        "/google/callback",
        status_code=303,
        responses={
            303: {
                "description": "Fixed success or login error",
                "headers": redirect_headers
                | {
                    "Referrer-Policy": {"schema": {"type": "string", "const": "no-referrer"}},
                },
            },
        },
    )
    async def callback(request: Request) -> Response:
        if service is None:
            return _callback_response("/login?error=unavailable")
        query = request.query_params
        state, code, _, issuer = [query.get(key) for key in ("state", "code", "error", "iss")]
        browser = request.cookies.get(FLOW_COOKIE)
        invalid = (
            any(len(query.getlist(key)) > 1 for key in ("state", "code", "error", "iss"))
            or not valid_session_token(state)
            or not valid_session_token(browser)
            or ("code" in query and "error" in query)
            or ("iss" in query and issuer != GOOGLE_ISSUER)
            or ("code" in query and not visible_ascii(code, 2048))
            or ("code" not in query and "error" not in query)
        )
        if invalid:
            return _callback_response("/login?error=invalid")
        try:
            # Validated above; consume before provider calls, including a provider decline.
            assert state is not None and browser is not None
            flow = await service.consume(state, browser)
            if "error" in query:
                return _callback_response("/login?error=denied")
            assert code is not None
            issued = await service.complete(code, flow, request.cookies.get(SESSION_COOKIE))
            response = _callback_response("/")
            set_session_cookie(response, issued)
            return response
        except (AuthenticationDenied, ProviderDenied):
            return _callback_response("/login?error=invalid")
        except Exception:
            # Every callback failure clears the browser binding without clearing its session.
            return _callback_response("/login?error=unavailable")

    @router.get(
        "/session",
        response_model=None,
        responses=errors
        | {
            200: {
                "headers": PROTECTED_HEADERS,
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/SessionInfo"}}
                },
            },
        },
    )
    def session(token: Annotated[str | None, Security(COOKIE_AUTH)]) -> Response:
        if not valid_session_token(token):
            raise HTTPException(401, "Authentication required")
        if workspace is None:
            raise HTTPException(503, AUTH_UNAVAILABLE)
        try:
            assert token is not None
            info = workspace.get_session(token)
            validated = SessionInfo.model_validate_json(info.model_dump_json(warnings=False))
            return Response(validated.model_dump_json(), media_type="application/json")
        except AuthenticationDenied:
            raise HTTPException(401, "Authentication required") from None
        except (StorageError, ValueError, TypeError, AttributeError):
            raise HTTPException(503, AUTH_UNAVAILABLE) from None

    @router.post("/logout", status_code=204, responses=errors)
    async def logout(
        request: Request, token: Annotated[str | None, Security(COOKIE_AUTH)]
    ) -> Response:
        if service is None:
            raise HTTPException(503, AUTH_UNAVAILABLE)
        _same_origin(request, service)
        if valid_session_token(token):
            try:
                assert token is not None
                await service.logout(token)
            except StorageError:
                raise HTTPException(503, AUTH_UNAVAILABLE) from None
        response = Response(status_code=204)
        clear_session_cookie(response)
        return response

    return router
