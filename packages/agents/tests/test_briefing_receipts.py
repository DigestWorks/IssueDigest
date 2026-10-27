"""Pure saved binding checks, with no repository or provider calls."""

from dataclasses import replace
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

import pytest
from issuedigest_domain.question_source_plan import QuestionSourceChoice, QuestionSourcePlan
from issuedigest_storage.briefing_jobs import BriefingJob, BriefingJobInputs
from issuedigest_storage.evidence_jobs import EvidenceJob
from test_question_briefing import claim, proposal, receipt, receipt_v3, reference, source
from test_question_briefing import restore_imports as restore_imports
from test_question_briefing_generation import run
from test_question_evidence_propositions import QUESTION


def packet(version):
    src = source()
    rec = (receipt if version == 2 else receipt_v3)(src)
    plan = QuestionSourcePlan(
        plan_id=uuid4(),
        workspace_id=src[1].document.workspace_id,
        request_id=uuid4(),
        question=QUESTION,
        status="selected",
        reason=None,
        sources=(
            QuestionSourceChoice(snapshot_id=src[0], source_sha256=rec.evidence.source_sha256),
        ),
    )
    child = EvidenceJob(
        job_id=uuid4(),
        workspace_id=plan.workspace_id,
        snapshot_id=src[0],
        question=QUESTION,
        model="gpt-6.1-sol",
        status="completed",
        source_sha256=rec.evidence.source_sha256,
        prompt_sha256=rec.prompt_sha256,
        instructions_sha256=rec.instructions_sha256,
        receipt=rec.model_dump(mode="json"),
        known_usage=rec.usage.model_dump(),
        usage_complete=True,
        stream_closed=True,
        reason=None,
        profile=rec.profile,
    )
    return BriefingJobInputs(QUESTION, plan, (src,), (child,), "1" * 64), rec


@pytest.mark.parametrize("version", [2, 3])
def test_saved_read_uses_original_version_and_matches_final_binding(version):
    from issuedigest_agents.briefing_receipts import validate_stored_briefing

    inputs, rec = packet(version)
    result, _, _ = run(inputs.sources, (rec,), proposal(claim(reference(inputs.sources[0]))))
    job = BriefingJob(
        job_id=uuid4(),
        workspace_id=inputs.plan.workspace_id,
        actor_id=uuid4(),
        request_id=uuid4(),
        plan_id=inputs.plan.plan_id,
        question=QUESTION,
        model="gpt-6.1-sol",
        profile=result.profile,
        reservation_usd=Decimal("1"),
        status="completed",
        inputs_sha256=inputs.inputs_sha256,
        child_job_ids=(inputs.children[0].job_id,),
        prompt_sha256=result.prompt_sha256,
        instructions_sha256=result.instructions_sha256,
        receipt=result.model_dump(mode="json"),
        known_usage=result.usage.model_dump(),
        usage_complete=True,
        stream_closed=True,
        reason=None,
    )
    assert validate_stored_briefing(job, inputs) == result
    with pytest.raises(ValueError):
        validate_stored_briefing(replace(job, prompt_sha256=sha256(b"changed").hexdigest()), inputs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("profile", "unknown"),
        ("profile", "guarded-question-evidence-v2"),
        ("source_sha256", "0" * 64),
        ("question", "changed"),
        ("prompt_sha256", "0" * 64),
        ("instructions_sha256", "0" * 64),
        ("known_usage", dict(input_tokens=11, output_tokens=5, requests=1)),
        ("workspace_id", uuid4()),
        ("snapshot_id", uuid4()),
    ],
)
def test_packet_rejects_changed_child_binding(field, value):
    from issuedigest_agents.briefing_receipts import validate_briefing_packet

    inputs, _ = packet(3)
    inputs = replace(inputs, children=(replace(inputs.children[0], **{field: value}),))
    with pytest.raises(ValueError):
        validate_briefing_packet(inputs)


def test_packet_rejects_mixed_versions_without_database():
    from issuedigest_agents.briefing_receipts import validate_briefing_packet

    old, _ = packet(2)
    new, _ = packet(3)
    mixed = replace(old, sources=old.sources + new.sources, children=old.children + new.children)
    with pytest.raises(ValueError):
        validate_briefing_packet(mixed)


@pytest.mark.parametrize("field", ["workspace_id", "plan_id"])
def test_final_binding_rejects_changed_parent(field):
    from issuedigest_agents.briefing_receipts import validate_briefing_binding

    inputs, rec = packet(3)
    result, _, _ = run(inputs.sources, (rec,), proposal(claim(reference(inputs.sources[0]))))
    job = BriefingJob(
        job_id=uuid4(),
        workspace_id=inputs.plan.workspace_id,
        actor_id=uuid4(),
        request_id=uuid4(),
        plan_id=inputs.plan.plan_id,
        question=QUESTION,
        model="gpt-6.1-sol",
        profile=result.profile,
        reservation_usd=Decimal("1"),
        status="completed",
        inputs_sha256=inputs.inputs_sha256,
        child_job_ids=(inputs.children[0].job_id,),
        prompt_sha256=result.prompt_sha256,
        instructions_sha256=result.instructions_sha256,
        receipt=result.model_dump(mode="json"),
        known_usage=result.usage.model_dump(),
        usage_complete=True,
        stream_closed=True,
        reason=None,
    )
    with pytest.raises(ValueError):
        validate_briefing_binding(replace(job, **{field: uuid4()}), inputs, result.prompt_sha256)
