"""Canonical current-input validation for stored final briefing receipts; no execution."""

from hashlib import sha256

from issuedigest_storage.briefing_jobs import BriefingJob, BriefingJobInputs
from issuedigest_storage.evidence_jobs import EvidenceJob

from .guarded_question_evidence_v2 import (
    GuardedQuestionEvidenceGenerationV2,
    validate_guarded_question_evidence_v2,
)
from .question_briefing_generation import (
    BRIEFING_GENERATION_INSTRUCTIONS,
    QuestionBriefingGeneration,
    question_briefing_prompt,
    validate_question_briefing_generation,
)

_INSTRUCTIONS_HASH = sha256(BRIEFING_GENERATION_INSTRUCTIONS.encode()).hexdigest()


def validate_briefing_packet(
    packet: BriefingJobInputs,
) -> tuple[tuple[GuardedQuestionEvidenceGenerationV2, ...], str]:
    if (
        type(packet) is not BriefingJobInputs
        or type(packet.question) is not str
        or type(packet.sources) is not tuple
        or type(packet.children) is not tuple
        or not 1 <= len(packet.sources) <= 5
        or len(packet.sources) != len(packet.children)
        or type(packet.inputs_sha256) is not str
    ):
        raise ValueError("Briefing inputs unavailable")
    receipts = []
    for source, child in zip(packet.sources, packet.children, strict=True):
        if (
            type(source) is not tuple
            or type(child) is not EvidenceJob
            or child.status != "completed"
            or child.question != packet.question
            or child.snapshot_id != source[0]
            or child.model != "gpt-6.1-sol"
            or type(child.receipt) is not dict
            or child.usage_complete is not True
            or child.stream_closed is not True
        ):
            raise ValueError("Briefing evidence unavailable")
        receipt = validate_guarded_question_evidence_v2(source, packet.question, child.receipt)
        if (
            receipt.prompt_sha256 != child.prompt_sha256
            or receipt.instructions_sha256 != child.instructions_sha256
            or receipt.usage.model_dump() != child.known_usage
        ):
            raise ValueError("Briefing evidence changed")
        receipts.append(receipt)
    checked = tuple(receipts)
    prompt = question_briefing_prompt(packet.question, packet.sources, checked)
    return checked, sha256(prompt.encode()).hexdigest()


def validate_briefing_binding(
    job: BriefingJob, packet: BriefingJobInputs, prompt_hash: str
) -> None:
    if (
        type(job) is not BriefingJob
        or job.question != packet.question
        or job.inputs_sha256 != packet.inputs_sha256
        or job.prompt_sha256 != prompt_hash
        or job.instructions_sha256 != _INSTRUCTIONS_HASH
        or job.profile != "question-briefing-generation-v1"
        or job.model != "gpt-6.1-sol"
        or job.child_job_ids != tuple(c.job_id for c in packet.children)
    ):
        raise ValueError("Briefing job inputs changed")


def validate_stored_briefing(
    job: BriefingJob, packet: BriefingJobInputs
) -> QuestionBriefingGeneration:
    """Validate a completed receipt without creating a client or performing I/O."""
    if type(job) is not BriefingJob or job.status != "completed":
        raise ValueError("Briefing completion unavailable")
    receipts, prompt_hash = validate_briefing_packet(packet)
    validate_briefing_binding(job, packet, prompt_hash)
    if job.receipt is None:
        raise ValueError("Briefing completion unavailable")
    result = validate_question_briefing_generation(
        packet.question, packet.sources, receipts, job.receipt
    )
    if (
        result.usage.model_dump() != job.known_usage
        or job.usage_complete is not True
        or job.stream_closed is not True
    ):
        raise ValueError("Briefing completion changed")
    return result
