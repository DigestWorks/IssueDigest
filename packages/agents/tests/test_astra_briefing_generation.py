"""Synthetic expanded final model contract; no network or key access."""

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import SourcePresentation
from issuedigest_storage.briefing_jobs import BriefingJob
from test_briefing_receipts import packet
from test_question_briefing import claim, proposal, reference
from test_question_briefing import restore_imports as restore_imports
from test_question_briefing_generation import api, failure, run

ASTRA = "gpt-6-astra"
SOL = "gpt-6.1-sol"


def test_astra_v5_final_native_request_differs_only_in_model():
    inputs, rec = packet(5)
    data = proposal(claim(reference(inputs.sources[0])))
    sol, _, sol_requests = run(inputs.sources, (rec,), data)
    astra, _, astra_requests = run(inputs.sources, (rec,), data, options=dict(model=ASTRA))
    assert type(astra) is api().QuestionBriefingGeneration
    assert astra.model == ASTRA and sol.model == SOL
    assert astra.briefing == sol.briefing
    assert astra.prompt_sha256 == sol.prompt_sha256
    assert len(sol_requests) == len(astra_requests) == 1
    assert astra_requests[0].content == sol_requests[0].content.replace(
        b'"model":"gpt-6.1-sol"', b'"model":"gpt-6-astra"', 1
    )
    checked = api().validate_question_briefing_generation(
        inputs.question, inputs.sources, (rec,), astra.model_dump(mode="json")
    )
    assert checked == astra


@pytest.mark.parametrize("version,model", [(2, ASTRA), (3, ASTRA), (5, "other"), (5, True)])
def test_invalid_final_model_or_astra_legacy_profile_precedes_provider(version, model):
    inputs, rec = packet(version)
    got, _, requests = run(
        inputs.sources,
        (rec,),
        proposal(claim(reference(inputs.sources[0]))),
        options=dict(model=model),
    )
    failure(got, "input", started=False, closed=False)
    assert requests == []


def test_old_sol_v2_v3_final_wire_is_byte_identical():
    baseline = json.loads(
        (Path(__file__).parent / "fixtures/question-final-sol-wire.json").read_bytes()
    )
    source = baseline["source"]
    src = (
        UUID(source[0]),
        EvidenceBundle.model_validate(source[1]),
        SourcePresentation.model_validate(source[2]),
    )
    from issuedigest_agents.question_briefing import validate_question_evidence_receipt

    for row in baseline["rows"]:
        question = json.loads(row["body"])["input"]
        question = json.loads(question)["question"]
        rec = validate_question_evidence_receipt(src, question, row["receipt"])
        got, _, requests = run(
            (src,), (rec,), proposal(claim(reference(src))), options=dict(question=question)
        )
        assert type(got) is api().QuestionBriefingGeneration
        assert requests[0].content == row["body"].encode()


@pytest.mark.parametrize("version", [2, 3])
def test_saved_astra_final_cannot_relabel_sol_legacy_receipts(version):
    inputs, rec = packet(version)
    got, _, _ = run(inputs.sources, (rec,), proposal(claim(reference(inputs.sources[0]))))
    changed = got.model_dump(mode="json")
    changed["model"] = ASTRA
    with pytest.raises(api().QuestionBriefingGenerationError):
        api().validate_question_briefing_generation(
            inputs.question, inputs.sources, (rec,), changed
        )


def final_job(inputs, result, model=ASTRA, reservation=Decimal("1.00")):
    return BriefingJob(
        job_id=uuid4(),
        workspace_id=inputs.plan.workspace_id,
        actor_id=uuid4(),
        request_id=uuid4(),
        plan_id=inputs.plan.plan_id,
        question=inputs.question,
        model=model,
        profile=result.profile,
        reservation_usd=reservation,
        status="completed",
        inputs_sha256=inputs.inputs_sha256,
        child_job_ids=tuple(c.job_id for c in inputs.children),
        prompt_sha256=result.prompt_sha256,
        instructions_sha256=result.instructions_sha256,
        receipt=result.model_dump(mode="json"),
        known_usage=result.usage.model_dump(),
        usage_complete=True,
        stream_closed=True,
        reason=None,
    )


def test_saved_astra_packet_and_receipt_bind_exact_job_model():
    from issuedigest_agents.briefing_receipts import validate_stored_briefing

    inputs, rec = packet(5)
    inputs = replace(inputs, children=tuple(replace(c, model=ASTRA) for c in inputs.children))
    result, _, _ = run(
        inputs.sources,
        (rec,),
        proposal(claim(reference(inputs.sources[0]))),
        options=dict(model=ASTRA),
    )
    assert type(result) is api().QuestionBriefingGeneration
    job = final_job(inputs, result)
    assert validate_stored_briefing(job, inputs) == result
    for changed in (replace(job, model=SOL), replace(job, reservation_usd=Decimal(".99"))):
        with pytest.raises(ValueError):
            validate_stored_briefing(changed, inputs)
    changed = replace(job, receipt=dict(job.receipt, model=SOL))
    with pytest.raises(ValueError):
        validate_stored_briefing(changed, inputs)


def test_mixed_child_models_rejected_by_packet():
    from issuedigest_agents.briefing_receipts import validate_briefing_packet

    inputs, _ = packet(5)
    child = inputs.children[0]
    inputs = replace(
        inputs,
        sources=inputs.sources * 2,
        children=(child, replace(child, job_id=uuid4(), model=ASTRA)),
    )
    with pytest.raises(ValueError):
        validate_briefing_packet(inputs)
