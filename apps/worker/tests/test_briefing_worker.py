"""Synthetic native final-worker contracts; dedicated SQL only."""

import asyncio
import importlib
import sys
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import httpx2 as httpx
import pytest
from openai import AsyncOpenAI
from sqlalchemy import text


@pytest.fixture(scope="module", autouse=True)
def restore_imports():
    packages = [importlib.import_module(n) for n in ("issuedigest_agents", "issuedigest_worker")]
    before, paths = set(sys.modules), sys.path.copy()
    attrs = [vars(p).copy() for p in packages]
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "packages/agents/tests"))
    yield
    for n in set(sys.modules) - before:
        if n.startswith(("issuedigest_agents.", "issuedigest_worker.briefing_worker", "test_")):
            sys.modules.pop(n, None)
    sys.path[:] = paths
    for p, a in zip(packages, attrs, strict=True):
        for n in set(vars(p)) - a.keys():
            delattr(p, n)
        for n, v in a.items():
            setattr(p, n, v)


@pytest.fixture
def jobs(engine):
    from issuedigest_storage.briefing_jobs import BriefingJobRepository

    with engine.begin() as c:
        c.execute(text("TRUNCATE briefing_jobs, evidence_jobs, question_source_plans"))
    yield BriefingJobRepository(engine)
    with engine.begin() as c:
        c.execute(text("TRUNCATE briefing_jobs, evidence_jobs, question_source_plans"))


def api():
    return importlib.import_module("issuedigest_worker.briefing_worker")


def seed(engine):
    from issuedigest_agents.guarded_question_evidence_v2 import (
        GUARDED_QUESTION_V2_INSTRUCTIONS,
        _preflight,
    )
    from issuedigest_agents.question_evidence_propositions import (
        build_question_evidence_propositions,
    )
    from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
    from issuedigest_storage.evidence_jobs import EvidenceJobRepository
    from issuedigest_storage.question_plans import QuestionPlanRepository
    from test_question_briefing import source
    from test_question_evidence_propositions import packet

    src = source()
    from issuedigest_domain import EvidenceBundle

    raw = src[1].model_dump(mode="json")
    raw["version"]["media_type"] = "text/plain"
    src = src[0], EvidenceBundle.model_validate(raw), src[2]
    sid, bundle, _ = src
    evidence = EvidenceRepository(engine)
    evidence.save(sid, bundle)
    evidence.rebuild_projection(bundle.document.workspace_id, sid)
    actor, workspace = uuid4(), bundle.document.workspace_id
    identity = IdentityRepository(engine)
    identity.register_identity(actor, "synthetic", str(actor))
    identity.set_membership(actor, workspace, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    plan = QuestionPlanRepository(engine).submit(token, workspace, uuid4(), "기관")
    assert plan is not None and len(plan.sources) == 1
    # Use the actual current SQL presentation, never a fixture's old metadata.
    children = EvidenceJobRepository(engine)
    child = children.submit(
        token,
        workspace,
        uuid4(),
        sid,
        plan.question,
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    _, src = children.prepare(child.job_id)
    prompt, _ = _preflight(src, plan.question)
    ph = sha256(prompt.encode()).hexdigest()
    ih = sha256(GUARDED_QUESTION_V2_INSTRUCTIONS.encode()).hexdigest()
    children.claim(child.job_id, prompt_sha256=ph, instructions_sha256=ih)
    usage = dict(input_tokens=10, output_tokens=5, requests=1)
    receipt = dict(
        profile="guarded-question-evidence-v2",
        status="unreviewed",
        transport_profile="guarded-responses-tool-v1",
        input_format="question-evidence-source-v2",
        prompt_sha256=ph,
        instructions_sha256=ih,
        usage=usage,
        evidence=build_question_evidence_propositions(src, plan.question, packet(src)).model_dump(
            mode="json"
        ),
    )
    children.finish(
        child.job_id, receipt=receipt, known_usage=usage, usage_complete=True, stream_closed=True
    )
    return token, workspace, plan.plan_id, (child.job_id,), actor


def admit(jobs, p):
    return asyncio.run(
        api().submit_briefing_job(
            jobs,
            p[0],
            p[1],
            uuid4(),
            p[2],
            p[3],
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".25"),
        )
    )


async def exercise(jobs, job, *, mutate=None, ownership=None, body=None):
    from test_guarded_responses_stream import Body
    from test_question_briefing_generation import rows

    requests = []

    def serve(request):
        requests.append(request)
        if mutate:
            mutate()
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=body
            or Body(
                rows(
                    {"result": {"outcome": "insufficient_evidence", "message": "합성 근거 부족"}}
                    if job.instructions_sha256
                    == sha256(
                        api()
                        .briefing_generation_instructions("question-briefing-source-v3")
                        .encode()
                    ).hexdigest()
                    else dict(
                        outcome="insufficient_evidence", message="합성 근거 부족", modules=[]
                    ),
                    "compose_question_briefing_v2"
                    if job.instructions_sha256
                    == sha256(
                        api()
                        .briefing_generation_instructions("question-briefing-source-v3")
                        .encode()
                    ).hexdigest()
                    else "compose_question_briefing_v1",
                )
            ),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as http:
        client = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
        result = await api().execute_briefing_job(
            jobs, job.job_id, client=client, check_ownership=ownership or (lambda _: True)
        )
        assert not client.is_closed()
        await client.close()
        return result, requests


def test_complete_persist_replay(jobs, engine):
    p = seed(engine)
    job = admit(jobs, p)
    result, requests = asyncio.run(exercise(jobs, job))
    assert result.status == "unreviewed" and len(requests) == 1
    replay, calls = asyncio.run(exercise(jobs, job))
    assert replay == result and calls == []
    saved = jobs.prepare(job.job_id)[0]
    assert saved.status == "completed" and saved.known_usage == result.usage.model_dump()
    with engine.connect() as c:
        assert c.scalar(text("SELECT reservation_count FROM research_budget_months")) == 2


def test_running_waiter_does_not_recover(jobs, engine):
    job = admit(jobs, seed(engine))
    assert jobs.claim(
        job.job_id,
        expected_inputs_sha256=job.inputs_sha256,
        prompt_sha256=job.prompt_sha256,
        instructions_sha256=job.instructions_sha256,
    )
    assert asyncio.run(exercise(jobs, job)) == (None, [])
    assert jobs.prepare(job.job_id)[0].status == "running"
    jobs.recover(job.job_id)
    assert asyncio.run(exercise(jobs, job)) == (None, [])


def test_cancel_retains_usage(jobs, engine):
    p = seed(engine)
    job = admit(jobs, p)
    result, calls = asyncio.run(
        exercise(jobs, job, mutate=lambda: jobs.cancel(p[0], p[1], job.job_id))
    )
    assert result is None and len(calls) == 1
    saved = jobs.prepare(job.job_id)[0]
    assert saved.status == "cancelled" and saved.receipt is None
    assert saved.known_usage == dict(input_tokens=10, output_tokens=5, requests=1)


def test_concurrent_workers_one_native_call(jobs, engine):
    job = admit(jobs, seed(engine))

    async def run():
        results = await asyncio.gather(exercise(jobs, job), exercise(jobs, job))
        assert sum(len(calls) for _, calls in results) == 1
        assert any(result is not None for result, _ in results)

    asyncio.run(run())


def test_every_sql_call_is_off_loop(jobs, engine, monkeypatch):
    import threading

    main = threading.get_ident()
    for name in ("inputs", "submit", "prepare", "claim", "finish"):
        original = getattr(jobs, name)

        def checked(*args, _original=original, **kwargs):
            assert threading.get_ident() != main
            return _original(*args, **kwargs)

        monkeypatch.setattr(jobs, name, checked)
    job = admit(jobs, seed(engine))
    assert asyncio.run(exercise(jobs, job))[0] is not None
    assert asyncio.run(exercise(jobs, job))[1] == []


def test_lost_completion_ack_wins(jobs, engine, monkeypatch):
    job = admit(jobs, seed(engine))
    original = jobs.finish

    def lost(*args, **kwargs):
        saved = original(*args, **kwargs)
        if kwargs.get("receipt") is not None:
            raise RuntimeError("private lost acknowledgement")
        return saved

    monkeypatch.setattr(jobs, "finish", lost)
    result, calls = asyncio.run(exercise(jobs, job))
    assert result is not None and len(calls) == 1
    assert jobs.prepare(job.job_id)[0].status == "completed"


@pytest.mark.parametrize("mode", ["false", "integer", "unknown"])
def test_callback_loss_retains_usage_without_raw_context(jobs, engine, mode):
    from issuedigest_storage.research import ResearchForbidden

    job = admit(jobs, seed(engine))
    lost = False

    def mutate():
        nonlocal lost
        lost = True

    def owned(identifier):
        assert identifier == job.job_id
        if not lost:
            return True
        if mode == "unknown":
            raise RuntimeError("private callback secret")
        return 1 if mode == "integer" else False

    with pytest.raises((ResearchForbidden, ValueError)) as caught:
        asyncio.run(exercise(jobs, job, mutate=mutate, ownership=owned))
    assert "secret" not in str(caught.value)
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    saved = jobs.prepare(job.job_id)[0]
    assert saved.status == "failed" and saved.receipt is None
    assert saved.known_usage == dict(input_tokens=10, output_tokens=5, requests=1)


@pytest.mark.parametrize("mode", ["writer", "source"])
def test_late_authority_source_loss_retains_usage(jobs, engine, mode):
    from issuedigest_storage import IdentityRepository
    from issuedigest_storage.repository import StorageCorruption
    from issuedigest_storage.research import ResearchConflict, ResearchForbidden

    p = seed(engine)
    job = admit(jobs, p)

    def mutate():
        if mode == "writer":
            IdentityRepository(engine).set_membership(p[4], p[1], "viewer")
        else:
            with engine.begin() as c:
                c.execute(
                    text(
                        "UPDATE source_presentations "
                        "SET payload=jsonb_set(payload, '{title}', :value)"
                    ),
                    dict(value='"changed"'),
                )

    with pytest.raises((ResearchForbidden, ResearchConflict, StorageCorruption)):
        asyncio.run(exercise(jobs, job, mutate=mutate))
    with engine.connect() as c:
        saved = c.execute(text("SELECT status,receipt,known_usage FROM briefing_jobs")).one()
    assert saved.status == "failed" and saved.receipt is None
    assert saved.known_usage == dict(input_tokens=10, output_tokens=5, requests=1)


def test_native_cancel_persists_identity_and_stream_observations(jobs, engine):
    from issuedigest_agents.guarded_responses_stream import GuardedResponsesCancelled
    from test_guarded_responses_stream import Body

    job = admit(jobs, seed(engine))

    async def run():
        body = Body([], wait=True)
        task = asyncio.create_task(exercise(jobs, job, body=body))
        await body.blocked.wait()
        task.cancel()
        with pytest.raises(GuardedResponsesCancelled) as caught:
            await task
        assert caught.value.stream_closed is True and body.closed

    asyncio.run(run())
    saved = jobs.prepare(job.job_id)[0]
    assert saved.status == "cancelled" and saved.receipt is None and saved.stream_closed is True


def test_unknown_execution_error_is_context_free(jobs, engine, monkeypatch):
    job = admit(jobs, seed(engine))

    async def fail(**kwargs):
        raise RuntimeError("private provider value")

    monkeypatch.setattr(api(), "run_question_briefing_generation", fail)
    with pytest.raises(ValueError) as caught:
        asyncio.run(exercise(jobs, job))
    assert str(caught.value) == "Briefing job outcome unavailable"
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert jobs.prepare(job.job_id)[0].status == "indeterminate"
    assert asyncio.run(exercise(jobs, job)) == (None, [])


def test_canonical_tamper_rejected_even_with_rehashed_opaque_receipt(jobs, engine):
    import json

    from issuedigest_storage.evidence_jobs import digest

    job = admit(jobs, seed(engine))
    result, _ = asyncio.run(exercise(jobs, job))
    receipt = result.model_dump(mode="json")
    receipt["aggregate_usage"]["input_tokens"] += 1
    with engine.begin() as c:
        c.execute(
            text("UPDATE briefing_jobs SET receipt=CAST(:r AS jsonb),receipt_sha256=:h"),
            dict(r=json.dumps(receipt), h=digest(receipt)),
        )
    from issuedigest_agents.question_briefing_generation import QuestionBriefingGenerationError

    with pytest.raises(QuestionBriefingGenerationError):
        asyncio.run(exercise(jobs, job))


@pytest.mark.parametrize("mode", ["hash", "usage", "boolean", "no_link"])
def test_child_deep_validation_before_reservation(jobs, engine, mode):
    import json

    from issuedigest_storage.evidence_jobs import digest

    p = seed(engine)
    with engine.begin() as c:
        r = c.scalar(text("SELECT receipt FROM evidence_jobs"))
        if mode == "hash":
            r["prompt_sha256"] = "a" * 64
            c.execute(text("UPDATE evidence_jobs SET prompt_sha256=:h"), dict(h="a" * 64))
        elif mode == "usage":
            r["usage"]["input_tokens"] += 1
        elif mode == "boolean":
            r["usage"]["input_tokens"] = True
        else:
            r["evidence"]["coverage"]["linked_proposition_ids"] = []
        c.execute(
            text("UPDATE evidence_jobs SET receipt=CAST(:r AS jsonb),receipt_sha256=:h"),
            dict(r=json.dumps(r), h=digest(r)),
        )
    from issuedigest_agents.guarded_responses_stream import GuardedResponsesError
    from issuedigest_storage.repository import StorageCorruption

    with pytest.raises((StorageCorruption, GuardedResponsesError, ValueError)):
        admit(jobs, p)
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM briefing_jobs")) == 0
        assert c.scalar(text("SELECT reservation_count FROM research_budget_months")) == 1


@pytest.mark.parametrize("mode", ["model", "decimal", "ids", "request"])
def test_raw_admission_guards_before_sql(jobs, monkeypatch, mode):
    options = dict(model="gpt-6.1-sol", reservation_usd=Decimal(".25"))
    ids, request = (uuid4(),), uuid4()
    if mode == "model":

        class Str(str):
            pass

        options["model"] = Str("gpt-6.1-sol")
    elif mode == "decimal":
        options["reservation_usd"] = 0.25
    elif mode == "ids":
        ids = list(ids)
    else:
        request = str(request)

    def forbidden(*args):
        pytest.fail("Invalid input reached SQL")

    monkeypatch.setattr(jobs, "inputs", forbidden)
    with pytest.raises(ValueError):
        asyncio.run(
            api().submit_briefing_job(jobs, "synthetic", uuid4(), request, uuid4(), ids, **options)
        )


def test_budget_rejection_no_extra_charge(jobs, engine):
    from issuedigest_storage.research import ResearchBudgetExceeded

    p = seed(engine)
    with engine.begin() as c:
        c.execute(text("UPDATE research_budget_months SET reservation_count=40"))
    with pytest.raises(ResearchBudgetExceeded):
        admit(jobs, p)
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM briefing_jobs")) == 0
        assert c.scalar(text("SELECT reserved_usd FROM research_budget_months")) == Decimal(".25")


def test_cancel_after_successful_sdk_preserves_observations(jobs, engine, monkeypatch):
    job = admit(jobs, seed(engine))
    original = api().run_question_briefing_generation

    async def completed_then_cancel(**kwargs):
        result = await original(**kwargs)
        # Simulate task cancellation during the subsequent current-authority await.
        original_prepare = jobs.prepare

        def cancelled_prepare(*args):
            raise asyncio.CancelledError()

        monkeypatch.setattr(jobs, "prepare", cancelled_prepare)
        monkeypatch.setattr(jobs, "_test_original_prepare", original_prepare, raising=False)
        return result

    monkeypatch.setattr(api(), "run_question_briefing_generation", completed_then_cancel)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(exercise(jobs, job))
    saved = jobs._test_original_prepare(job.job_id)[0]
    assert saved.known_usage == dict(input_tokens=10, output_tokens=5, requests=1)
    assert saved.status == "cancelled" and saved.stream_closed is True


def test_unknown_prepare_error_sanitized(jobs, engine, monkeypatch):
    job = admit(jobs, seed(engine))

    def broken(*args):
        raise RuntimeError("private SQL error content")

    monkeypatch.setattr(jobs, "prepare", broken)
    with pytest.raises(ValueError) as caught:
        asyncio.run(exercise(jobs, job))
    assert "private" not in str(caught.value)
    assert caught.value.__context__ is None and caught.value.__cause__ is None


def test_receipt_acceptance_failure_rolls_back_then_observation_survives(jobs, engine, monkeypatch):
    from issuedigest_storage import IdentityRepository
    from issuedigest_storage.research import ResearchForbidden

    p = seed(engine)
    job = admit(jobs, p)
    original = jobs.finish

    def reject(*args, **kwargs):
        if kwargs.get("receipt") is not None:
            IdentityRepository(engine).set_membership(p[4], p[1], "viewer")
        return original(*args, **kwargs)

    monkeypatch.setattr(jobs, "finish", reject)
    with pytest.raises(ResearchForbidden):
        asyncio.run(exercise(jobs, job))
    with engine.connect() as c:
        saved = c.execute(text("SELECT status,receipt,known_usage FROM briefing_jobs")).one()
    assert saved.status == "failed" and saved.receipt is None
    assert saved.known_usage == dict(input_tokens=10, output_tokens=5, requests=1)


def test_fake_sdk_mapping_cannot_be_completed(jobs, engine, monkeypatch):
    job = admit(jobs, seed(engine))

    async def fake(**kwargs):
        return {"usage": dict(input_tokens=10, output_tokens=5, requests=1)}

    monkeypatch.setattr(api(), "run_question_briefing_generation", fake)
    with pytest.raises(ValueError):
        asyncio.run(exercise(jobs, job))
    saved = jobs.prepare(job.job_id)[0]
    assert saved.status == "failed" and saved.receipt is None and saved.known_usage is None


def test_full_sdk_preflight_failure_precedes_reservation(jobs, engine, monkeypatch):
    p = seed(engine)

    def too_large(*args):
        raise ValueError("synthetic complete input exceeds envelope")

    monkeypatch.setattr(
        importlib.import_module("issuedigest_agents.briefing_receipts"),
        "question_briefing_prompt",
        too_large,
    )
    with pytest.raises(ValueError):
        admit(jobs, p)
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM briefing_jobs")) == 0
        assert c.scalar(text("SELECT reservation_count FROM research_budget_months")) == 1


def test_ownership_loss_during_claim_sends_nothing(jobs, engine, monkeypatch):
    from issuedigest_storage.research import ResearchForbidden

    job = admit(jobs, seed(engine))
    original = jobs.claim
    lost = False

    def claim(*args, **kwargs):
        nonlocal lost
        result = original(*args, **kwargs)
        lost = True
        return result

    monkeypatch.setattr(jobs, "claim", claim)
    with pytest.raises(ResearchForbidden):
        asyncio.run(exercise(jobs, job, ownership=lambda _: not lost))
    assert jobs.prepare(job.job_id)[0].known_usage is None


def test_ownership_loss_during_post_sdk_prepare_rejects_receipt(jobs, engine, monkeypatch):
    from issuedigest_storage.research import ResearchForbidden

    job = admit(jobs, seed(engine))
    original = jobs.prepare
    lost = False
    calls = 0

    def prepare(*args, **kwargs):
        nonlocal lost, calls
        packet = original(*args, **kwargs)
        calls += 1
        if calls == 2:
            # First prepare precedes the SDK; the second follows its success.
            lost = True
        return packet

    monkeypatch.setattr(jobs, "prepare", prepare)
    with pytest.raises(ResearchForbidden):
        asyncio.run(exercise(jobs, job, ownership=lambda _: not lost))
    saved = original(job.job_id)[0]
    assert saved.status == "failed" and saved.receipt is None
    assert saved.known_usage == dict(input_tokens=10, output_tokens=5, requests=1)
    assert saved.usage_complete is True and saved.stream_closed is True


@pytest.mark.parametrize(
    "model,reservation", [("gpt-6-astra", Decimal(".99")), ("other", Decimal("1.00"))]
)
def test_expanded_model_controls_reject_before_inputs_or_reservation(
    jobs, monkeypatch, model, reservation
):
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid final model/reservation reached repository")

    monkeypatch.setattr(jobs, "inputs", forbidden)
    monkeypatch.setattr(jobs, "submit", forbidden)
    with pytest.raises(ValueError):
        asyncio.run(
            api().submit_briefing_job(
                jobs,
                "synthetic",
                uuid4(),
                uuid4(),
                uuid4(),
                (uuid4(),),
                model=model,
                reservation_usd=reservation,
            )
        )


def test_final_requested_model_must_match_valid_child_before_reservation(jobs, engine, monkeypatch):
    p = seed(engine)

    def forbidden(*args, **kwargs):
        pytest.fail("Mismatched final model reached reservation")

    monkeypatch.setattr(jobs, "submit", forbidden)
    with pytest.raises(ValueError):
        asyncio.run(
            api().submit_briefing_job(
                jobs,
                p[0],
                p[1],
                uuid4(),
                p[2],
                p[3],
                model="gpt-6-astra",
                reservation_usd=Decimal("1.00"),
            )
        )


@pytest.mark.parametrize(
    "selected",
    ["question-briefing-source-v1", "question-briefing-source-v2", "question-briefing-source-v3"],
)
def test_v2_admission_execution_replay_and_v1_idempotency_conflict(jobs, engine, selected):
    from issuedigest_agents.question_briefing_generation import (
        briefing_generation_instructions,
        briefing_input_format_from_instructions_hash,
    )
    from issuedigest_storage.research import ResearchConflict

    p = seed(engine)
    request_id = uuid4()

    async def submit(input_format):
        return await api().submit_briefing_job(
            jobs,
            p[0],
            p[1],
            request_id,
            p[2],
            p[3],
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".25"),
            input_format=input_format,
        )

    v2 = selected
    job = asyncio.run(submit(v2))
    assert briefing_input_format_from_instructions_hash(job.instructions_sha256) == v2
    assert (
        job.instructions_sha256 == sha256(briefing_generation_instructions(v2).encode()).hexdigest()
    )
    result, requests = asyncio.run(exercise(jobs, job))
    assert result.input_format == v2 and len(requests) == 1
    replay, calls = asyncio.run(exercise(jobs, job))
    assert replay == result and calls == []
    with pytest.raises(ResearchConflict):
        asyncio.run(
            submit(
                "question-briefing-source-v1"
                if selected == "question-briefing-source-v2"
                else "question-briefing-source-v2"
            )
        )


@pytest.mark.parametrize("hash_value", ["0" * 64, "v1"])
def test_pending_unknown_instructions_never_calls_provider(jobs, engine, hash_value):
    p = seed(engine)
    job = admit(jobs, p)
    if hash_value == "v1":
        from issuedigest_agents.question_briefing_generation import briefing_generation_instructions

        hash_value = sha256(
            briefing_generation_instructions("question-briefing-source-v2").encode()
        ).hexdigest()
    with engine.begin() as c:
        c.execute(
            text("UPDATE briefing_jobs SET instructions_sha256=:hash WHERE job_id=:id"),
            {"hash": hash_value, "id": job.job_id},
        )
    with pytest.raises(ValueError):
        asyncio.run(exercise(jobs, job))
    assert jobs.prepare(job.job_id)[0].status == "failed"
