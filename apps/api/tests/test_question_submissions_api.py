"""Synthetic question stream boundaries and strict DTOs."""

import asyncio
import importlib.util
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from issuedigest_api.cookies import SESSION_COOKIE
from issuedigest_api.main import create_app


def test_submission_contract_exists():
    assert importlib.util.find_spec("issuedigest_domain.question_submission") is not None
    assert importlib.util.find_spec("issuedigest_agents.question_submission") is not None


def test_route_fails_closed():
    response = TestClient(create_app()).post(f"/api/v1/workspaces/{uuid4()}/question-briefings")
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"


def client_for(service):
    client = TestClient(
        create_app(
            question_service=service,
            auth_service=SimpleNamespace(
                config=SimpleNamespace(public_origin="https://example.test")
            ),
        ),
        base_url="https://example.test",
        follow_redirects=False,
    )
    client.cookies.set(SESSION_COOKIE, "a" * 42 + "A")
    return client


class Service:
    async def authorize(self, *args):
        return True

    async def run(self, token, workspace_id, request_id, question):
        from issuedigest_domain.question_submission import QuestionSubmissionResult

        return QuestionSubmissionResult(request_id=request_id, kind="no_match", job_id=None)


def post(client, body, suffix=""):
    return client.post(
        f"/api/v1/workspaces/{uuid4()}/question-briefings" + suffix,
        content=body,
        headers={"Origin": "https://example.test", "Content-Type": "application/json"},
    )


def test_stream_result_and_trace():
    import json

    rid = uuid4()
    response = post(
        client_for(Service()), json.dumps(dict(request_id=str(rid), question="합성 질문"))
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert response.headers["x-accel-buffering"] == "no"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] != str(rid)
    assert response.text.count("event: progress") == 1
    assert "event: result" in response.text
    assert json.loads(response.text.split("event: result\ndata: ")[1]) == dict(
        request_id=str(rid), kind="no_match", job_id=None
    )


@pytest.mark.parametrize(
    "body",
    [
        b"{}",
        b"null",
        b"[]",
        b'{"question":NaN}',
        b'{"question":"a","question":"b"}',
        b"\xff",
        b"x" * 16385,
    ],
)
def test_invalid_body_is_fixed(body):
    response = post(client_for(Service()), body)
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid question submission request"}


@pytest.mark.parametrize("suffix", ["?private=secret", "/?private=secret"])
def test_query_redirect_and_headers(suffix):
    response = post(client_for(Service()), b"{}", suffix)
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]
    assert "location" not in response.headers
    assert "secret" not in response.text


def test_origin_service_and_permission_failures():
    client = client_for(Service())
    assert client.post(f"/api/v1/workspaces/{uuid4()}/question-briefings").status_code == 403
    client = client_for(None)
    assert post(client, b"{}").status_code == 503

    class Denied(Service):
        async def authorize(self, *args):
            return False

    import json

    body = json.dumps(dict(request_id=str(uuid4()), question="합성"))
    assert post(client_for(Denied()), body).status_code == 404


@pytest.mark.parametrize(
    "kind", ["unauthorized", "forbidden", "conflict", "budget", "unavailable", "unknown", "forged"]
)
def test_safe_stream_errors(kind):
    import json

    from issuedigest_agents.question_submission import QuestionSubmissionError
    from issuedigest_domain.question_submission import QuestionSubmissionResult

    class Broken(Service):
        async def run(self, *args):
            if kind == "unknown":
                raise RuntimeError("private secret token question")
            if kind == "forged":
                return QuestionSubmissionResult.model_construct(
                    request_id=args[2], kind="briefing", job_id=None
                )
            raise QuestionSubmissionError(kind)

    response = post(
        client_for(Broken()), json.dumps(dict(request_id=str(uuid4()), question="합성"))
    )
    assert response.status_code == 200
    assert "event: error" in response.text
    assert "private secret" not in response.text
    expected = "unavailable" if kind in {"unknown", "forged"} else kind
    assert json.loads(response.text.split("event: error\ndata: ")[1])["kind"] == expected


def test_dtos_reject_coercion_extra_and_invalid_terminal():
    from issuedigest_domain.question_submission import (
        QuestionSubmissionRequest,
        QuestionSubmissionResult,
    )
    from pydantic import ValidationError

    for fields in [
        dict(question=123),
        dict(question=" "),
        dict(question="a" * 1501),
        dict(question="a", model="secret"),
        dict(question="\ud800"),
    ]:
        with pytest.raises((ValidationError, UnicodeError)):
            QuestionSubmissionRequest(request_id=uuid4(), **fields)
    with pytest.raises(ValidationError):
        QuestionSubmissionRequest(request_id=str(uuid4()), question="a")
    with pytest.raises(ValidationError):
        QuestionSubmissionResult(request_id=uuid4(), kind="briefing", job_id=None)


def test_disconnect_cancels_and_awaits_caller_with_heartbeat(monkeypatch):
    import json

    from issuedigest_api import question_submissions

    monkeypatch.setattr(question_submissions, "HEARTBEAT_SECONDS", 0.01)

    async def exercise():
        started, cleaned, disconnect = asyncio.Event(), asyncio.Event(), asyncio.Event()
        chunks = []

        class Slow(Service):
            async def run(self, *args):
                started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    await asyncio.sleep(0.01)
                    cleaned.set()

        app = create_app(
            question_service=Slow(),
            auth_service=SimpleNamespace(
                config=SimpleNamespace(public_origin="https://example.test")
            ),
        )
        raw = json.dumps(dict(request_id=str(uuid4()), question="합성")).encode()
        first = True

        async def receive():
            nonlocal first
            if first:
                first = False
                return {"type": "http.request", "body": raw, "more_body": False}
            await disconnect.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))
                if b"keepalive" in chunks[-1]:
                    disconnect.set()

        scope = dict(
            type="http",
            asgi={"version": "3.0", "spec_version": "2.0"},
            http_version="1.1",
            method="POST",
            scheme="https",
            path=f"/api/v1/workspaces/{uuid4()}/question-briefings",
            raw_path=b"/",
            query_string=b"",
            root_path="",
            server=("example.test", 443),
            client=("127.0.0.1", 1234),
            headers=[
                (b"host", b"example.test"),
                (b"origin", b"https://example.test"),
                (b"content-type", b"application/json"),
                (b"cookie", f"{SESSION_COOKIE}={'a' * 42}A".encode()),
            ],
        )
        await asyncio.wait_for(app(scope, receive, send), 2)
        assert started.is_set()
        assert cleaned.is_set()
        assert b": keepalive\n\n" in b"".join(chunks)
        assert b"event: result" not in b"".join(chunks)

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "kind,status",
    [
        ("unauthorized", 401),
        ("forbidden", 403),
        ("conflict", 409),
        ("budget", 429),
        ("unavailable", 503),
        ("unknown", 503),
    ],
)
def test_authorization_error_status_and_no_stream(kind, status):
    import json

    from issuedigest_agents.question_submission import QuestionSubmissionError

    class Broken(Service):
        async def authorize(self, *args):
            if kind == "unknown":
                raise RuntimeError("secret token question")
            raise QuestionSubmissionError(kind)

    response = post(
        client_for(Broken()), json.dumps(dict(request_id=str(uuid4()), question="합성"))
    )
    assert response.status_code == status
    assert "secret" not in response.text
    assert "event:" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_mismatched_result_identity_is_unavailable():
    import json

    from issuedigest_domain.question_submission import QuestionSubmissionResult

    class Wrong(Service):
        async def run(self, *args):
            return QuestionSubmissionResult(request_id=uuid4(), kind="blocked", job_id=None)

    response = post(client_for(Wrong()), json.dumps(dict(request_id=str(uuid4()), question="합성")))
    assert "event: result" not in response.text
    assert '"kind":"unavailable"' in response.text


def test_body_extra_query_content_type_and_malformed_path():
    import json

    client = client_for(Service())
    body = json.dumps(dict(request_id=str(uuid4()), question="합성", model="secret"))
    assert post(client, body).status_code == 422
    body = json.dumps(dict(request_id=str(uuid4()), question="합성"))
    path = f"/api/v1/workspaces/{uuid4()}/question-briefings"
    response = client.post(
        path,
        content=body,
        headers={
            "Origin": "https://example.test",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    assert response.status_code == 422
    response = client.post(
        path.replace(path.split("/")[4], "secret"),
        content=body,
        headers={"Origin": "https://example.test", "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert "secret" not in response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("value", [1, "yes", None, {}])
def test_authorize_requires_actual_boolean(value):
    import json

    class Invalid(Service):
        async def authorize(self, *args):
            return value

    response = post(
        client_for(Invalid()), json.dumps(dict(request_id=str(uuid4()), question="합성"))
    )
    assert response.status_code == 503
    assert "event:" not in response.text
