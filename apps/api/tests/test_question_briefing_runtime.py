"""Optional service lifetime precedes engine disposal; root remains explicit."""

import asyncio

import pytest
from issuedigest_api import runtime
from issuedigest_api.auth_config import RuntimeConfigurationError
from sqlalchemy import create_engine
from test_auth_config import values


@pytest.mark.parametrize("fail", [False, True])
def test_optional_service_lifetime(monkeypatch, fail):
    for key, value in values().items():
        monkeypatch.setenv(key, value)
    engine = create_engine("postgresql+psycopg://issuedigest_test@127.0.0.1:25607/issuedigest_test")
    order = []
    monkeypatch.setattr(runtime, "create_storage_engine", lambda _: engine)
    monkeypatch.setattr(engine, "dispose", lambda: order.append("dispose"))

    class Service:
        async def start(self):
            order.append("start")
            if fail:
                raise RuntimeError("PRIVATE")

        async def aclose(self):
            order.append("close")

    service = Service()
    application = runtime.create_configured_app(
        service_factory=lambda actual: service if actual is engine else None
    )

    async def exercise():
        async with application.router.lifespan_context(application):
            order.append("serve")

    if fail:
        with pytest.raises(RuntimeConfigurationError) as caught:
            asyncio.run(exercise())
        assert "PRIVATE" not in str(caught.value)
        assert caught.value.__context__ is None
    else:
        asyncio.run(exercise())
    assert order == (
        ["start", "close", "dispose"] if fail else ["start", "serve", "close", "dispose"]
    )


def test_native_http_submission_replay_history_and_loop_liveness(engine, database_url, monkeypatch):
    import json
    import threading
    from pathlib import Path
    from types import SimpleNamespace
    from uuid import uuid4

    import httpx2 as httpx
    from dbos import DBOS
    from issuedigest_api.cookies import SESSION_COOKIE
    from issuedigest_api.main import create_app
    from issuedigest_domain import EvidenceBundle
    from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
    from issuedigest_storage.briefing_jobs import BriefingJobRepository
    from issuedigest_worker import question_service as host
    from openai import AsyncOpenAI
    from sqlalchemy import MetaData, Table, event, select, text, update
    from sqlalchemy.schema import DropSchema
    from sqlalchemy.sql import quoted_name

    root = Path(__file__).resolve().parents[3]
    for path in ("packages/agents/tests", "apps/worker/tests"):
        monkeypatch.syspath_prepend(str(root / path))
    from test_guarded_responses_stream import Body, events
    from test_question_briefing import source
    from test_question_briefing_generation import rows
    from test_question_evidence_propositions import packet

    assert engine.url.port == 25607
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE briefing_jobs, evidence_jobs, question_source_plans"))
    schema = "qwh_" + uuid4().hex
    original = source()
    raw = original[1].model_dump(mode="json")
    raw["version"]["media_type"] = "text/plain"
    src = original[0], EvidenceBundle.model_validate(raw), original[2]
    sid, bundle, _ = src
    actor, workspace, request_id = uuid4(), bundle.document.workspace_id, uuid4()
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, workspace, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    evidence = EvidenceRepository(engine)
    evidence.save(sid, bundle)
    evidence.rebuild_projection(workspace, sid)
    requests, loops = [], []
    entered, release = threading.Event(), threading.Event()
    blocked = False

    def sql(*args):
        nonlocal blocked
        statement = args[2]
        if (
            threading.current_thread().name == "issuedigest-question-worker"
            and "evidence_jobs" in statement
            and not blocked
        ):
            blocked = True
            entered.set()
            assert release.wait(10)

    def serve(request):
        requests.append(request)
        loops.append(("use", threading.get_ident(), asyncio.get_running_loop()))
        data = json.loads(request.content)
        if "fill_question_evidence_v2" in str(data["tools"]):
            stream = events(json.dumps(packet(src)))
            for row in stream:
                for item in [row.get("item"), *row.get("response", {}).get("output", [])]:
                    if item is not None:
                        item["name"] = "fill_question_evidence_v2"
            body = Body(stream)
        else:
            body = Body(
                rows(dict(outcome="insufficient_evidence", message="합성 근거 부족", modules=[]))
            )
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=body)

    class Provider(AsyncOpenAI):
        def __init__(self, **kwargs):
            loops.append(("create", threading.get_ident(), asyncio.get_running_loop()))
            super().__init__(
                **kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(serve))
            )

        async def close(self):
            loops.append(("close", threading.get_ident(), asyncio.get_running_loop()))
            await super().close()

    monkeypatch.setattr(host, "AsyncOpenAI", Provider)
    service = host.OwnedQuestionExecutionService(
        engine, host.QuestionServiceConfig(api_key="synthetic", schema=schema)
    )
    app = create_app(
        question_service=service,
        briefing_job_repository=BriefingJobRepository(engine),
        auth_service=SimpleNamespace(config=SimpleNamespace(public_origin="https://example.test")),
    )

    def counts():
        with engine.connect() as conn:
            return tuple(
                conn.execute(
                    text(
                        "SELECT (SELECT count(*) FROM evidence_jobs), "
                        "(SELECT count(*) FROM briefing_jobs), "
                        "(SELECT sum(reserved_usd) FROM research_budget_months)"
                    )
                ).one()
            )

    async def exercise():
        await service.start()
        event.listen(engine, "before_cursor_execute", sql)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="https://example.test",
            cookies={SESSION_COOKIE: token},
        ) as client:
            route = f"/api/v1/workspaces/{workspace}/question-briefings"

            async def submit():
                response = await client.post(
                    route,
                    json=dict(request_id=str(request_id), question="기관"),
                    headers={"Origin": "https://example.test"},
                )
                assert response.status_code == 200, response.text
                assert response.text.count("event: progress") == 1
                assert "event: result" in response.text, response.text
                return json.loads(response.text.split("event: result\ndata: ")[1])

            first = asyncio.create_task(submit())
            assert await asyncio.to_thread(entered.wait, 15)
            assert (await asyncio.wait_for(client.get("/health/live"), 0.5)).status_code == 200
            release.set()
            second = asyncio.create_task(submit())
            one, two = await asyncio.gather(first, second)
            assert one == two and one["kind"] == "briefing"
            job = one["job_id"]
            for _ in range(100):
                response = await client.get(f"/api/v1/workspaces/{workspace}/briefing-jobs/{job}")
                assert response.status_code == 200, response.text
                if response.json()["status"] == "completed":
                    break
                await asyncio.sleep(0.05)
            assert response.json()["status"] == "completed", response.text
            assert response.json()["result"]["message"] == "합성 근거 부족"
            history = await client.get(f"/api/v1/workspaces/{workspace}/briefing-jobs")
            assert history.json() == {
                "items": [{"job_id": job, "question": "기관", "status": "completed"}]
            }
            before = await asyncio.to_thread(counts)
            assert await submit() == one
            assert await asyncio.to_thread(counts) == before
            assert len(requests) == 2
            identities.set_membership(actor, workspace, "viewer")
            forbidden = await client.post(
                route,
                json=dict(request_id=str(request_id), question="기관"),
                headers={"Origin": "https://example.test"},
            )
            assert forbidden.status_code == 403
            assert await asyncio.to_thread(counts) == before and len(requests) == 2
            identities.set_membership(actor, workspace, "owner")
        event.remove(engine, "before_cursor_execute", sql)
        await service.aclose()
        # Simulate a process loss after persisted checkpoints but before terminal
        # status commit. Both names must resolve during the next launch recovery.
        statuses = Table("workflow_status", MetaData(), schema=schema, autoload_with=engine)
        with engine.begin() as conn:
            assert conn.scalar(select(text("count(*)")).select_from(statuses)) == 2
            conn.execute(update(statuses).values(status="PENDING", output=None, error=None))
        restarted = host.OwnedQuestionExecutionService(
            engine, host.QuestionServiceConfig(api_key="synthetic", schema=schema)
        )
        try:
            await restarted.start()

            def recovered():
                with engine.connect() as conn:
                    return tuple(conn.scalars(select(statuses.c.status)))

            for _ in range(150):
                if await asyncio.to_thread(recovered) == ("SUCCESS", "SUCCESS"):
                    break
                await asyncio.sleep(0.05)
            assert await asyncio.to_thread(recovered) == ("SUCCESS", "SUCCESS")
            assert await asyncio.to_thread(counts) == before and len(requests) == 2
        finally:
            await restarted.aclose()
        assert not restarted._thread.is_alive()

    try:
        DBOS.migrate(database_url, schema=schema, application_role=engine.url.username)
        asyncio.run(exercise())
    finally:
        release.set()
        if event.contains(engine, "before_cursor_execute", sql):
            event.remove(engine, "before_cursor_execute", sql)
        if not service._closed:
            asyncio.run(service.aclose())
        with engine.begin() as conn:
            conn.execute(DropSchema(quoted_name(schema, True), cascade=True, if_exists=True))
    assert [row[0] for row in loops] == ["create", "use", "use", "close", "create", "close"]
    assert len({row[1] for row in loops[:4]}) == 1
    assert len({id(row[2]) for row in loops[:4]}) == 1
    assert loops[4][2] is loops[5][2] and loops[4][2] is not loops[0][2]
    assert not service._thread.is_alive()
