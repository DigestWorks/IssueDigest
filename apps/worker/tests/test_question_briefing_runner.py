"""Caller-lived composition contracts, with dedicated synthetic native integration."""

import asyncio
import importlib
from decimal import Decimal
from uuid import uuid4

import pytest


def api():
    assert importlib.util.find_spec("issuedigest_worker.question_briefing_runner"), "Missing runner"
    return importlib.import_module("issuedigest_worker.question_briefing_runner")


def repositories():
    from issuedigest_storage.briefing_jobs import BriefingJobRepository
    from issuedigest_storage.evidence_jobs import EvidenceJobRepository
    from issuedigest_storage.question_plans import QuestionPlanRepository
    from sqlalchemy import create_engine

    engine = create_engine("postgresql+psycopg://issuedigest_test@127.0.0.1:25605/issuedigest_test")
    return (
        QuestionPlanRepository(engine),
        EvidenceJobRepository(engine),
        BriefingJobRepository(engine),
    )


def inputs():
    return dict(
        client=object(),
        app_version="qbr-test",
        token="A" * 43,
        workspace_id=uuid4(),
        request_id=uuid4(),
        question="앞",
        model="gpt-6.1-sol",
        evidence_reservation_usd=Decimal(".25"),
        briefing_reservation_usd=Decimal(".50"),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("total_timeout_seconds", True),
        ("total_timeout_seconds", 0),
        ("total_timeout_seconds", 601),
        ("app_version", "bad version"),
        ("token", "bad"),
        ("workspace_id", "bad"),
        ("request_id", "bad"),
        ("question", " "),
        ("question", "x" * 1501),
        ("model", "other"),
        ("evidence_reservation_usd", 0.25),
        ("briefing_reservation_usd", Decimal("NaN")),
        ("briefing_reservation_usd", Decimal(".001")),
    ],
)
def test_invalid_inputs_precede_every_helper(monkeypatch, field, value):
    runner = api()

    async def forbidden(*args, **kwargs):
        pytest.fail("Invalid input reached helper")

    monkeypatch.setattr(runner, "run_question_plan", forbidden)
    with pytest.raises(ValueError):
        asyncio.run(runner.run_question_briefing(*repositories(), **(inputs() | {field: value})))


def test_no_match_and_none_stop_composition(monkeypatch):
    from issuedigest_agents.question_dispatch import QuestionDispatch
    from issuedigest_worker.question_runner import QuestionEvidenceRun

    runner = api()
    result = QuestionEvidenceRun(QuestionDispatch(uuid4(), "no_match", 0, 0, ()), ())

    async def plan(*args, **kwargs):
        return result

    monkeypatch.setattr(runner, "run_question_plan", plan)
    value = asyncio.run(runner.run_question_briefing(*repositories(), **inputs()))
    assert value.evidence == result.dispatch and value.briefing is None
    result = None
    assert asyncio.run(runner.run_question_briefing(*repositories(), **inputs())) is None


def test_raw_errors_have_no_cause_or_context(monkeypatch):
    runner = api()

    async def bad(*args, **kwargs):
        raise RuntimeError("secret token question DSN")

    monkeypatch.setattr(runner, "run_question_plan", bad)
    with pytest.raises(runner.QuestionBriefingRunError) as caught:
        asyncio.run(runner.run_question_briefing(*repositories(), **inputs()))
    assert "secret" not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__context__ is None


@pytest.mark.parametrize("raw", [object(), (), False])
def test_forged_evidence_rejected(monkeypatch, raw):
    runner = api()

    async def bad(*args, **kwargs):
        return raw

    monkeypatch.setattr(runner, "run_question_plan", bad)
    with pytest.raises(runner.QuestionBriefingRunError):
        asyncio.run(runner.run_question_briefing(*repositories(), **inputs()))


@pytest.mark.parametrize("wrong_engine", [False, True])
def test_repository_configuration_precedes_analysis(monkeypatch, wrong_engine):
    runner = api()
    repos = list(repositories())
    if wrong_engine:
        repos[2].engine = object()
    else:
        repos[2] = object()

    async def forbidden(*args, **kwargs):
        pytest.fail("Configuration reached analysis")

    monkeypatch.setattr(runner, "run_question_plan", forbidden)
    with pytest.raises(ValueError):
        asyncio.run(runner.run_question_briefing(*repos, **inputs()))


@pytest.fixture
def stages(monkeypatch):
    from types import SimpleNamespace

    from issuedigest_agents.briefing_dispatch import BriefingDispatch
    from issuedigest_agents.evidence_dispatch import EvidenceDispatch
    from issuedigest_agents.guarded_question_evidence_v2 import GuardedQuestionEvidenceGenerationV2
    from issuedigest_agents.question_dispatch import QuestionDispatch
    from issuedigest_storage.briefing_jobs import BriefingJob
    from issuedigest_worker.question_runner import QuestionEvidenceRun

    runner, args = api(), inputs()
    child, plan_id, job_id = uuid4(), uuid4(), uuid4()
    receipt = GuardedQuestionEvidenceGenerationV2.model_construct()
    dispatch = QuestionDispatch(
        plan_id,
        "evidence_complete",
        1,
        1,
        (EvidenceDispatch(child, "guarded-evidence-" + str(child), "completed", False),),
    )
    state = SimpleNamespace(
        evidence=QuestionEvidenceRun(dispatch, (receipt,)),
        job=BriefingJob(
            job_id,
            args["workspace_id"],
            uuid4(),
            args["request_id"],
            plan_id,
            args["question"],
            args["model"],
            "question-briefing-generation-v1",
            Decimal(".50"),
            "pending",
            "a" * 64,
            (child,),
            "b" * 64,
            "c" * 64,
            None,
            None,
            False,
            False,
            None,
        ),
        ack=BriefingDispatch(job_id, "question-briefing-" + str(job_id), "pending", True),
        calls=[],
        args=args,
    )

    async def plan(*pos, **kw):
        state.calls.append(("plan", pos, kw))
        return state.evidence

    async def submit(*pos, **kw):
        state.calls.append(("submit", pos, kw))
        return state.job

    async def enqueue(*pos, **kw):
        state.calls.append(("enqueue", pos, kw))
        return state.ack

    monkeypatch.setattr(runner, "run_question_plan", plan)
    monkeypatch.setattr(runner, "submit_briefing_job", submit)
    monkeypatch.setattr(runner, "enqueue_briefing_job", enqueue)
    return state


def invoke(stages):
    return asyncio.run(api().run_question_briefing(*repositories(), **stages.args))


def test_order_original_request_and_exact_parameters(stages):
    result = invoke(stages)
    assert result.evidence == stages.evidence.dispatch and result.briefing == stages.ack
    assert [c[0] for c in stages.calls] == ["plan", "submit", "enqueue"]
    plan, submit, queue = stages.calls
    assert plan[2]["request_id"] == stages.args["request_id"]
    assert plan[2]["total_timeout_seconds"] == 600
    assert submit[1][1:] == (
        stages.args["token"],
        stages.args["workspace_id"],
        stages.args["request_id"],
        stages.evidence.dispatch.plan_id,
        stages.job.child_job_ids,
    )
    assert submit[2] == dict(model="gpt-6.1-sol", reservation_usd=Decimal(".50"))
    assert queue[2]["client"] is stages.args["client"]


@pytest.mark.parametrize("stage", ["job", "ack"])
def test_none_at_each_final_boundary(stages, stage):
    setattr(stages, stage, None)
    assert invoke(stages) is None
    assert len(stages.calls) == (2 if stage == "job" else 3)


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_id", "bad"),
        ("request_id", uuid4()),
        ("plan_id", uuid4()),
        ("workspace_id", uuid4()),
        ("question", "different"),
        ("model", "other"),
        ("child_job_ids", (uuid4(),)),
        ("status", "unknown"),
        ("usage_complete", 1),
        ("profile", "other"),
        ("inputs_sha256", "bad"),
        ("reservation_usd", 0.5),
    ],
)
def test_forged_final_fields_never_enqueue(stages, field, value):
    from dataclasses import replace

    stages.job = replace(stages.job, **{field: value})
    with pytest.raises(api().QuestionBriefingRunError):
        invoke(stages)
    assert len(stages.calls) == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_id", uuid4()),
        ("workflow_id", "wrong"),
        ("status", "unknown"),
        ("status", 1),
        ("queued", 1),
        ("status", "completed"),
    ],
)
def test_forged_acknowledgement_rejected(stages, field, value):
    from dataclasses import replace

    stages.ack = replace(stages.ack, **{field: value})
    with pytest.raises(api().QuestionBriefingRunError):
        invoke(stages)


@pytest.mark.parametrize("receipts", [[], (), (object(),), (object(), object())])
def test_receipt_shape_and_count_rejected(stages, receipts):
    from dataclasses import replace

    stages.evidence = replace(stages.evidence, receipts=receipts)
    with pytest.raises(api().QuestionBriefingRunError):
        invoke(stages)
    assert len(stages.calls) == 1


@pytest.mark.parametrize(
    "name", ["run_question_plan", "submit_briefing_job", "enqueue_briefing_job"]
)
def test_cancellation_has_no_continuation(stages, monkeypatch, name):
    runner = api()

    async def exercise():
        entered = asyncio.Event()

        async def stall(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(runner, name, stall)
        task = asyncio.create_task(runner.run_question_briefing(*repositories(), **stages.args))
        await entered.wait()
        count = len(stages.calls)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)
        assert len(stages.calls) == count

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "name", ["run_question_plan", "submit_briefing_job", "enqueue_briefing_job"]
)
def test_total_timeout_covers_each_boundary(stages, monkeypatch, name):
    runner = api()

    async def stall(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(runner, name, stall)
    with pytest.raises(TimeoutError):
        asyncio.run(
            runner.run_question_briefing(*repositories(), **stages.args, total_timeout_seconds=1)
        )


@pytest.fixture(scope="module", autouse=True)
def restore_modules():
    import sys
    from pathlib import Path

    paths, before = sys.path.copy(), set(sys.modules)
    packages = [importlib.import_module(n) for n in ("issuedigest_agents", "issuedigest_worker")]
    attrs = [vars(p).copy() for p in packages]
    root = Path(__file__).resolve().parents[3]
    for path in ("apps/worker/tests", "packages/agents/tests", "packages/storage/tests"):
        sys.path.insert(0, str(root / path))
    yield
    for name in set(sys.modules) - before:
        if name.startswith(("issuedigest_agents.", "issuedigest_worker.", "test_")):
            sys.modules.pop(name, None)
    sys.path[:] = paths
    for package, original in zip(packages, attrs, strict=True):
        for key in set(vars(package)) - original.keys():
            delattr(package, key)
        for key, value in original.items():
            setattr(package, key, value)


@pytest.fixture
def admitted(engine):
    from issuedigest_domain import EvidenceBundle
    from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
    from issuedigest_storage.briefing_jobs import BriefingJobRepository
    from issuedigest_storage.evidence_jobs import EvidenceJobRepository
    from issuedigest_storage.question_plans import QuestionPlanRepository
    from sqlalchemy import text
    from test_question_briefing import source

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE briefing_jobs,evidence_jobs,question_source_plans"))
    src = source()
    raw = src[1].model_dump(mode="json")
    raw["version"]["media_type"] = "text/plain"
    src = src[0], EvidenceBundle.model_validate(raw), src[2]
    snapshot, bundle, _ = src
    workspace, actor = bundle.document.workspace_id, uuid4()
    identity = IdentityRepository(engine)
    identity.register_identity(actor, "synthetic", str(actor))
    identity.set_membership(actor, workspace, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    EvidenceRepository(engine).save(snapshot, bundle)
    EvidenceRepository(engine).rebuild_projection(workspace, snapshot)
    args = inputs() | dict(token=token, workspace_id=workspace, question="기관")
    yield (
        (
            QuestionPlanRepository(engine),
            EvidenceJobRepository(engine),
            BriefingJobRepository(engine),
        ),
        args,
        src,
    )
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE briefing_jobs,evidence_jobs,question_source_plans"))


def test_native_composition_replay_receipt_offloop(admitted, engine, database_url):
    import json
    import threading

    import httpx2 as httpx
    from dbos import DBOS, DBOSClient
    from issuedigest_worker.briefing_queue import register_briefing_queue
    from issuedigest_worker.briefing_worker import read_completed_briefing_job
    from issuedigest_worker.evidence_queue import register_evidence_queue
    from openai import AsyncOpenAI
    from sqlalchemy import event, text
    from sqlalchemy.schema import DropSchema
    from sqlalchemy.sql import quoted_name
    from test_guarded_responses_stream import Body, events
    from test_question_briefing_generation import rows

    repos, args, src = admitted
    schema, requests, threads = "qbr_" + uuid4().hex, [], []

    def sql(*_):
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        threads.append((threading.get_ident(), task.get_name() if task else None))

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

    def serve(request):
        requests.append(request)
        data = json.loads(request.content)
        if "fill_question_evidence_v2" in str(data["tools"]):
            from test_question_evidence_propositions import packet

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

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as http:
            provider = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
            client = None
            try:
                DBOS.migrate(database_url, schema=schema, application_role=engine.url.username)
                DBOS(
                    config=dict(
                        name="qbr-synthetic",
                        system_database_url=database_url,
                        dbos_system_schema=schema,
                        application_version="qbr-test",
                        run_admin_server=False,
                    )
                )
                client = DBOSClient(
                    system_database_url=database_url,
                    application_name="qbr-synthetic",
                    dbos_system_schema=schema,
                )
                DBOS.launch()
                await asyncio.to_thread(
                    register_evidence_queue,
                    repos[1],
                    client=provider,
                    check_ownership=lambda _: True,
                )
                await asyncio.to_thread(
                    register_briefing_queue,
                    repos[2],
                    client=provider,
                    check_ownership=lambda _: True,
                )
                event.listen(engine, "before_cursor_execute", sql)
                a, b = await asyncio.gather(
                    *(
                        asyncio.create_task(
                            api().run_question_briefing(*repos, **(args | dict(client=client))),
                            name="qbr-caller",
                        )
                        for _ in range(2)
                    )
                )
                assert a.evidence == b.evidence
                assert a.briefing.job_id == b.briefing.job_id
                assert a.evidence.status == "evidence_complete"
                handle = await client.retrieve_workflow_async(a.briefing.workflow_id)
                await asyncio.wait_for(handle.get_result(), 30)
                receipt = await read_completed_briefing_job(
                    repos[2], a.briefing.job_id, check_ownership=lambda _: True
                )
                assert receipt.status == "unreviewed"
                assert len(requests) == 2
                assert threads and not any(name == "qbr-caller" for _, name in threads)
                before = await asyncio.to_thread(counts)
                replay = await api().run_question_briefing(*repos, **(args | dict(client=client)))
                assert replay.briefing.status == "completed" and replay.briefing.queued is False
                assert len(requests) == 2 and await asyncio.to_thread(counts) == before
                assert not provider.is_closed()
            finally:
                if event.contains(engine, "before_cursor_execute", sql):
                    event.remove(engine, "before_cursor_execute", sql)
                try:
                    if client is not None:
                        client.destroy()
                finally:
                    try:
                        DBOS.destroy(destroy_registry=True)
                    finally:
                        await provider.close()

    try:
        asyncio.run(exercise())
    finally:
        with engine.begin() as conn:
            conn.execute(DropSchema(quoted_name(schema, True), cascade=True, if_exists=True))


@pytest.mark.parametrize("field", ["evidence_reservation_usd", "briefing_reservation_usd"])
@pytest.mark.parametrize(
    "value", [Decimal("0.50000000000000000000000000000000000001"), Decimal("1E-999999")]
)
def test_exact_cent_precision_precedes_analysis(monkeypatch, field, value):
    runner = api()

    async def forbidden(*args, **kwargs):
        pytest.fail("Noncent value reached analysis")

    monkeypatch.setattr(runner, "run_question_plan", forbidden)
    with pytest.raises(ValueError):
        asyncio.run(runner.run_question_briefing(*repositories(), **(inputs() | {field: value})))


@pytest.mark.parametrize(
    "name", ["run_question_plan", "submit_briefing_job", "enqueue_briefing_job"]
)
@pytest.mark.parametrize("kind", ["auth", "forbidden", "budget", "storage", "queue", "raw"])
def test_helper_failures_preserve_only_safe_errors(stages, monkeypatch, name, kind):
    from issuedigest_agents.briefing_dispatch import BriefingDispatchError
    from issuedigest_storage.repository import StorageCorruption
    from issuedigest_storage.research import ResearchBudgetExceeded, ResearchForbidden
    from issuedigest_storage.sessions import AuthenticationDenied

    runner = api()
    failures = dict(
        auth=AuthenticationDenied("Authentication required"),
        forbidden=ResearchForbidden("Forbidden"),
        budget=ResearchBudgetExceeded("Budget exceeded"),
        storage=StorageCorruption("Corrupt"),
        queue=BriefingDispatchError(stages.job.job_id, stages.ack.workflow_id),
        raw=RuntimeError("secret DSN question"),
    )
    error = failures[kind]

    async def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(runner, name, fail)
    with pytest.raises(runner.QuestionBriefingRunError if kind == "raw" else type(error)) as caught:
        invoke(stages)
    if kind == "raw":
        assert caught.value.__context__ is None and caught.value.__cause__ is None
        assert "secret" not in str(caught.value)
    else:
        assert caught.value is error


def test_blocked_evidence_has_no_final_admission(stages):
    from dataclasses import replace

    dispatch = stages.evidence.dispatch
    ack = replace(dispatch.dispatches[0], status="failed")
    stages.evidence = replace(
        stages.evidence,
        dispatch=replace(dispatch, status="blocked", completed_count=0, dispatches=(ack,)),
        receipts=(),
    )
    result = invoke(stages)
    assert result.briefing is None and result.evidence.status == "blocked"
    assert len(stages.calls) == 1


@pytest.mark.parametrize(
    "field,value", [("dispatches", []), ("completed_count", True), ("status", "in_progress")]
)
def test_forged_dispatch_rejected(stages, field, value):
    from dataclasses import replace

    stages.evidence = replace(
        stages.evidence, dispatch=replace(stages.evidence.dispatch, **{field: value})
    )
    with pytest.raises(api().QuestionBriefingRunError):
        invoke(stages)
    assert len(stages.calls) == 1


def test_extra_dataclass_fields_rejected(stages):
    object.__setattr__(stages.evidence, "extra", "injected")
    with pytest.raises(api().QuestionBriefingRunError):
        invoke(stages)
