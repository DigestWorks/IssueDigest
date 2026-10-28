"""Owned host configuration and loop isolation contracts."""

import asyncio
import importlib
import threading
from uuid import uuid4

import pytest
from issuedigest_agents.question_submission import QuestionSubmissionError
from sqlalchemy import create_engine


def service_api():
    return importlib.import_module("issuedigest_worker.question_service")


def test_explicit_configuration_and_safe_errors():
    api = service_api()
    for values in (
        {},
        {"ISSUEDIGEST_QUESTION_BRIEFING_ENABLED": "1"},
        {"ISSUEDIGEST_QUESTION_BRIEFING_ENABLED": "0", "OPENAI_API_KEY": "synthetic"},
    ):
        with pytest.raises(QuestionSubmissionError) as caught:
            api.QuestionServiceConfig.from_environment(values)
        assert caught.value.kind == "unavailable"
        assert caught.value.__context__ is None
    config = api.QuestionServiceConfig.from_environment(
        {"ISSUEDIGEST_QUESTION_BRIEFING_ENABLED": "1", "OPENAI_API_KEY": "synthetic"}
    )
    assert config.schema == "issuedigest_question_briefing"
    assert config.app_version == "question-briefing-http-v1"
    assert "synthetic" not in repr(config)
    for schema in ("dbos", "public", "pg_catalog", "bad-name"):
        with pytest.raises(QuestionSubmissionError):
            api.QuestionServiceConfig(api_key="synthetic", schema=schema)


def test_worker_loop_bridge_cancellation_and_close(monkeypatch):
    api = service_api()
    caller_thread = threading.get_ident()
    events = []

    async def boot(self):
        events.append(("start", threading.get_ident(), asyncio.get_running_loop()))

    async def stop(self):
        events.append(("close", threading.get_ident(), asyncio.get_running_loop()))

    async def authorize(self, *args):
        events.append(("authorize", threading.get_ident(), asyncio.get_running_loop()))
        return True

    monkeypatch.setattr(api.OwnedQuestionExecutionService, "_start_worker", boot)
    monkeypatch.setattr(api.OwnedQuestionExecutionService, "_close_worker", stop)
    monkeypatch.setattr(api.OwnedQuestionExecutionService, "_authorize_worker", authorize)
    service = api.OwnedQuestionExecutionService(
        create_engine("postgresql+psycopg://issuedigest_test@127.0.0.1:25607/issuedigest_test"),
        api.QuestionServiceConfig(api_key="synthetic"),
    )

    async def exercise():
        await service.start()
        assert await service.authorize("A" * 43, uuid4(), uuid4(), "질문")
        await service.aclose()
        await service.aclose()
        with pytest.raises(QuestionSubmissionError):
            await service.authorize("A" * 43, uuid4(), uuid4(), "질문")

    asyncio.run(exercise())
    assert [x[0] for x in events] == ["start", "authorize", "close"]
    assert len({x[1] for x in events}) == 1 and events[0][1] != caller_thread
    assert len({id(x[2]) for x in events}) == 1
    assert not service._thread.is_alive()


@pytest.mark.parametrize("failure", ["foreign", "lease", "provider", "register", "launch", "queue"])
def test_startup_failure_releases_only_owned_state(monkeypatch, failure):
    from contextlib import contextmanager
    from types import SimpleNamespace

    api = service_api()
    events = []
    foreign = object() if failure == "foreign" else None
    monkeypatch.setattr(api.dbos_runtime, "_dbos_global_instance", foreign)
    monkeypatch.setattr(api.dbos_runtime, "_dbos_global_registry", None)

    @contextmanager
    def lease(engine):
        events.append("lease")
        if failure == "lease":
            raise RuntimeError("PRIVATE")
        try:
            yield lambda: None
        finally:
            events.append("release")

    class Provider:
        def __init__(self, **kwargs):
            events.append("provider")
            if failure == "provider":
                raise RuntimeError("PRIVATE")

        async def close(self):
            events.append("provider-close")

    def phase(name):
        def call(*args, **kwargs):
            events.append(name)
            if failure == name:
                raise RuntimeError("PRIVATE")

        return call

    class Runtime:
        def __init__(self, **kwargs):
            events.append("runtime")

        launch = staticmethod(phase("launch"))
        destroy = staticmethod(phase("destroy"))

    monkeypatch.setattr(api, "research_worker_lock", lease)
    monkeypatch.setattr(api, "AsyncOpenAI", Provider)
    monkeypatch.setattr(api, "DBOS", Runtime)
    monkeypatch.setattr(api, "register_evidence_workflow", phase("register"))
    monkeypatch.setattr(api, "register_evidence_workflow_v3", phase("register-v3"))
    monkeypatch.setattr(api, "register_evidence_workflow_v5", phase("register-v5"))
    monkeypatch.setattr(api, "register_briefing_workflow", phase("register-final"))
    monkeypatch.setattr(api, "configure_briefing_queue", phase("queue"))
    monkeypatch.setattr(
        api, "DBOSClient", lambda **kwargs: SimpleNamespace(destroy=phase("client-close"))
    )
    service = api.OwnedQuestionExecutionService(
        create_engine("postgresql+psycopg://issuedigest_test@127.0.0.1:25607/issuedigest_test"),
        api.QuestionServiceConfig(api_key="synthetic"),
    )
    with pytest.raises(QuestionSubmissionError) as caught:
        asyncio.run(service.start())
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert not service._thread.is_alive()
    assert not api._HOST_LOCK.locked()
    if failure == "foreign":
        assert events == [] and api.dbos_runtime._dbos_global_instance is foreign
    if failure in ("register", "launch", "queue"):
        assert "destroy" in events and "provider-close" in events and "release" in events
    if failure == "queue":
        assert (
            events.index("register")
            < events.index("register-v3")
            < events.index("register-final")
            < events.index("launch")
        )


def test_cancelled_bridge_finishes_worker_caller_without_stopping_host(monkeypatch):
    api = service_api()
    entered, cancelled = threading.Event(), threading.Event()
    finalizing, release = threading.Event(), threading.Event()

    async def noop(self):
        pass

    async def blocking(self, *args):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            finalizing.set()
            await asyncio.to_thread(release.wait, 2)
            cancelled.set()

    monkeypatch.setattr(api.OwnedQuestionExecutionService, "_start_worker", noop)
    monkeypatch.setattr(api.OwnedQuestionExecutionService, "_close_worker", noop)
    monkeypatch.setattr(api.OwnedQuestionExecutionService, "_authorize_worker", blocking)
    service = api.OwnedQuestionExecutionService(
        create_engine("postgresql+psycopg://issuedigest_test@127.0.0.1:25607/issuedigest_test"),
        api.QuestionServiceConfig(api_key="synthetic"),
    )

    async def exercise():
        await service.start()
        caller = asyncio.create_task(service.authorize("A" * 43, uuid4(), uuid4(), "질문"))
        assert await asyncio.to_thread(entered.wait, 2)
        try:
            caller.cancel()
            assert await asyncio.to_thread(finalizing.wait, 2)
            await asyncio.sleep(0.02)
            assert not caller.done(), "Caller returned before worker finalizer finished"
            assert len(service._callers) == 1
            assert not cancelled.is_set()
            assert service._thread.is_alive()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await caller
            assert cancelled.is_set()
            assert not service._callers
            assert service._thread.is_alive()
        finally:
            release.set()
            await service.aclose()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "category", ["unauthorized", "forbidden", "conflict", "budget", "unavailable"]
)
def test_worker_error_categories_have_no_private_chain(monkeypatch, category):
    api = service_api()
    types = dict(
        unauthorized=api.AuthenticationDenied,
        forbidden=api.ResearchForbidden,
        conflict=api.ResearchConflict,
        budget=api.ResearchBudgetExceeded,
        unavailable=RuntimeError,
    )

    async def noop(self):
        pass

    async def failure(self, *args):
        raise types[category]("PRIVATE question token DSN")

    monkeypatch.setattr(api.OwnedQuestionExecutionService, "_start_worker", noop)
    monkeypatch.setattr(api.OwnedQuestionExecutionService, "_close_worker", noop)
    monkeypatch.setattr(api.OwnedQuestionExecutionService, "_authorize_worker", failure)
    service = api.OwnedQuestionExecutionService(
        create_engine("postgresql+psycopg://issuedigest_test@127.0.0.1:25607/issuedigest_test"),
        api.QuestionServiceConfig(api_key="synthetic"),
    )

    async def exercise():
        await service.start()
        try:
            with pytest.raises(QuestionSubmissionError) as caught:
                await service.authorize("A" * 43, uuid4(), uuid4(), "질문")
            assert caught.value.kind == category
            assert caught.value.__context__ is None and caught.value.__cause__ is None
            assert "PRIVATE" not in str(caught.value)
        finally:
            await service.aclose()

    asyncio.run(exercise())


def test_native_missing_schema_fails_closed_and_releases_lease(engine, monkeypatch):
    from issuedigest_worker.research_recovery import research_worker_lock
    from sqlalchemy import text

    api = service_api()
    assert engine.url.port == 25607
    schema = "qwh_" + uuid4().hex

    def migration_forbidden(*args, **kwargs):
        pytest.fail("Runtime must never migrate")

    monkeypatch.setattr(api.DBOS, "migrate", migration_forbidden)
    service = api.OwnedQuestionExecutionService(
        engine, api.QuestionServiceConfig(api_key="synthetic", schema=schema)
    )
    with pytest.raises(QuestionSubmissionError):
        asyncio.run(service.start())
    assert not service._thread.is_alive()
    with engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM pg_namespace WHERE nspname=:schema"), {"schema": schema}
            )
            == 0
        )
    with research_worker_lock(engine) as check:
        check()


def test_close_failure_is_sanitized_after_thread_cleanup(monkeypatch):
    api = service_api()

    async def boot(self):
        pass

    async def stop(self):
        raise RuntimeError("PRIVATE provider key")

    monkeypatch.setattr(api.OwnedQuestionExecutionService, "_start_worker", boot)
    monkeypatch.setattr(api.OwnedQuestionExecutionService, "_close_worker", stop)
    service = api.OwnedQuestionExecutionService(
        create_engine("postgresql+psycopg://issuedigest_test@127.0.0.1:25607/issuedigest_test"),
        api.QuestionServiceConfig(api_key="synthetic"),
    )

    async def exercise():
        await service.start()
        with pytest.raises(QuestionSubmissionError) as caught:
            await service.aclose()
        assert caught.value.__context__ is None and caught.value.__cause__ is None
        assert not service._thread.is_alive()

    asyncio.run(exercise())


def test_evidence_profile_configuration_is_private_and_strict():
    api = service_api()
    env = {"ISSUEDIGEST_QUESTION_BRIEFING_ENABLED": "1", "OPENAI_API_KEY": "synthetic"}
    assert api.QuestionServiceConfig.from_environment(env).evidence_profile == (
        "guarded-question-evidence-v2"
    )
    for profile in (
        "guarded-question-evidence-v2",
        "guarded-question-evidence-v3",
        "guarded-question-evidence-v5",
    ):
        config = api.QuestionServiceConfig.from_environment(
            env | {"ISSUEDIGEST_QUESTION_EVIDENCE_PROFILE": profile}
        )
        assert config.evidence_profile == profile
    for profile in ("", "v3", "guarded-question-evidence-v4"):
        with pytest.raises(QuestionSubmissionError):
            api.QuestionServiceConfig.from_environment(
                env | {"ISSUEDIGEST_QUESTION_EVIDENCE_PROFILE": profile}
            )


@pytest.mark.parametrize(
    "model,profile,amount",
    [
        ("gpt-6.1-sol", "guarded-question-evidence-v2", ".50"),
        ("gpt-6-astra", "guarded-question-evidence-v5", "1.00"),
    ],
)
def test_model_configuration_derives_fixed_reservations(model, profile, amount):
    from decimal import Decimal

    api = service_api()
    env = {"ISSUEDIGEST_QUESTION_BRIEFING_ENABLED": "1", "OPENAI_API_KEY": "synthetic"}
    default = api.QuestionServiceConfig.from_environment(env)
    assert default.model == "gpt-6.1-sol"
    config = api.QuestionServiceConfig.from_environment(
        env
        | {
            "ISSUEDIGEST_QUESTION_MODEL": model,
            "ISSUEDIGEST_QUESTION_EVIDENCE_PROFILE": profile,
            "ISSUEDIGEST_QUESTION_RESERVATION_USD": ".01",
        }
    )
    assert config.model == model
    assert config.evidence_reservation_usd == Decimal(amount)
    assert config.briefing_reservation_usd == Decimal(amount)


@pytest.mark.parametrize(
    "model,profile",
    [
        ("unknown", "guarded-question-evidence-v5"),
        ("gpt-6-astra ", "guarded-question-evidence-v5"),
        ("gpt-6-astra", "guarded-question-evidence-v2"),
        ("gpt-6-astra", "guarded-question-evidence-v3"),
    ],
)
def test_invalid_model_profile_is_rejected_before_start(model, profile):
    api = service_api()
    with pytest.raises(QuestionSubmissionError) as caught:
        api.QuestionServiceConfig.from_environment(
            {
                "ISSUEDIGEST_QUESTION_BRIEFING_ENABLED": "1",
                "OPENAI_API_KEY": "synthetic",
                "ISSUEDIGEST_QUESTION_MODEL": model,
                "ISSUEDIGEST_QUESTION_EVIDENCE_PROFILE": profile,
            }
        )
    assert caught.value.kind == "unavailable"


@pytest.mark.parametrize(
    "model,profile,amount",
    [
        ("gpt-6.1-sol", "guarded-question-evidence-v2", ".50"),
        ("gpt-6-astra", "guarded-question-evidence-v5", "1.00"),
    ],
)
@pytest.mark.parametrize(
    "status,kind",
    [("no_match", "no_match"), ("blocked", "blocked"), ("evidence_complete", "blocked")],
)
@pytest.mark.parametrize(
    "input_format", ["question-briefing-source-v1", "question-briefing-source-v2"]
)
def test_run_bridge_passes_configured_model_and_reservations(
    monkeypatch, model, profile, amount, status, kind, input_format
):
    from decimal import Decimal
    from types import SimpleNamespace

    api = service_api()
    captured = {}
    for name in ("QuestionPlanRepository", "EvidenceJobRepository", "BriefingJobRepository"):
        monkeypatch.setattr(api, name, lambda *args, **kwargs: None)

    async def run(*args, **kwargs):
        captured.update(kwargs)
        return api.QuestionBriefingRun(evidence=SimpleNamespace(status=status), briefing=None)

    monkeypatch.setattr(api, "run_question_briefing", run)
    service = api.OwnedQuestionExecutionService(
        create_engine("postgresql+psycopg://synthetic@127.0.0.1:25607/synthetic"),
        api.QuestionServiceConfig(
            api_key="synthetic", model=model, evidence_profile=profile, input_format=input_format
        ),
    )
    service._client = object()
    result = asyncio.run(service._run_worker("A" * 43, uuid4(), uuid4(), "질문"))
    assert result.kind == kind and result.job_id is None
    assert captured["model"] == model
    assert captured["evidence_reservation_usd"] == Decimal(amount)
    assert captured["briefing_reservation_usd"] == Decimal(amount)
    if input_format == "question-briefing-source-v1":
        assert "input_format" not in captured
    else:
        assert captured["input_format"] == input_format


def test_provider_ignores_ambient_endpoint_tenant_and_proxy(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace

    import httpx2
    from openai import AsyncOpenAI

    api = service_api()
    for key in ("OPENAI_BASE_URL", "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(key, "https://ambient.invalid")
    monkeypatch.setenv("OPENAI_ORG_ID", "ambient-org")
    monkeypatch.setenv("OPENAI_PROJECT_ID", "ambient-project")
    for name in ("QuestionPlanRepository", "EvidenceJobRepository", "BriefingJobRepository"):
        monkeypatch.setattr(api, name, lambda *args, **kwargs: None)
    providers, provider_args, transport_args = [], [], []
    actual_http = httpx2.AsyncClient

    class Transport(actual_http):
        def __init__(self, **kwargs):
            transport_args.append(kwargs)
            super().__init__(**kwargs)

    def provider(**kwargs):
        provider_args.append(kwargs)
        instance = AsyncOpenAI(**kwargs)
        providers.append(instance)
        return instance

    @contextmanager
    def lease(engine):
        yield lambda: None

    monkeypatch.setattr(api.dbos_runtime, "_dbos_global_instance", None)
    monkeypatch.setattr(api, "research_worker_lock", lease)
    monkeypatch.setattr(api, "AsyncOpenAI", provider)
    monkeypatch.setattr(api.httpx, "AsyncClient", Transport)

    class Runtime:
        def __init__(self, **kwargs):
            pass

        @staticmethod
        def launch():
            pass

        @staticmethod
        def destroy(**kwargs):
            pass

    monkeypatch.setattr(api, "DBOS", Runtime)
    for name in (
        "register_evidence_workflow",
        "register_evidence_workflow_v3",
        "register_evidence_workflow_v5",
        "register_briefing_workflow",
        "configure_briefing_queue",
    ):
        monkeypatch.setattr(api, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(api, "DBOSClient", lambda **kwargs: SimpleNamespace(destroy=lambda: None))
    service = api.OwnedQuestionExecutionService(
        create_engine("postgresql+psycopg://synthetic@127.0.0.1:25607/synthetic"),
        api.QuestionServiceConfig(api_key="synthetic"),
    )

    async def exercise():
        try:
            await service.start()
            actual = providers[0]
            assert str(actual.base_url) == "https://api.openai.com/v1/"
            assert actual.organization is None and actual.project is None
            assert actual.max_retries == 0 and actual.timeout == 60
            assert provider_args[0]["organization"] is None
            assert provider_args[0]["project"] is None
            assert transport_args == [{"trust_env": False}]
        finally:
            await service.aclose()
        assert providers[0].is_closed()

    asyncio.run(exercise())


def test_final_input_format_default_and_strict_explicit_opt_in():
    api = importlib.import_module("issuedigest_worker.question_service")
    env = {"ISSUEDIGEST_QUESTION_BRIEFING_ENABLED": "1", "OPENAI_API_KEY": "synthetic"}
    assert (
        api.QuestionServiceConfig.from_environment(env).input_format
        == "question-briefing-source-v1"
    )
    env["ISSUEDIGEST_QUESTION_BRIEFING_INPUT_FORMAT"] = "question-briefing-source-v2"
    assert (
        api.QuestionServiceConfig.from_environment(env).input_format
        == "question-briefing-source-v2"
    )
    env["ISSUEDIGEST_QUESTION_BRIEFING_INPUT_FORMAT"] = "unknown"
    with pytest.raises(QuestionSubmissionError):
        api.QuestionServiceConfig.from_environment(env)
