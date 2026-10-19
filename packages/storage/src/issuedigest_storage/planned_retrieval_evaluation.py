"""Read-only original versus recorded/operator-authored independent search comparisons."""

import json
from collections import Counter
from collections.abc import Sequence
from typing import Annotated, Literal, Self

from pydantic import UUID4, Field, field_validator, model_validator
from sqlalchemy import Connection, Engine
from sqlalchemy.engine import URL

from . import research_search
from . import retrieval_evaluation as v1
from .repository import _digest, _payload
from .research_retrieval import RETRIEVAL_PROFILE, question_terms
from .retrieval_evaluation import MAX_JOB_BYTES as MAX_JOB_BYTES

Origin = Literal["recorded_planner_output", "operator_authored"]


class EvaluationPlan(v1._PrivateModel):
    case_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$", repr=False)
    origin: Origin
    queries: Annotated[tuple[str, ...], Field(min_length=1, max_length=3)] = Field(repr=False)
    irrelevant_snapshot_ids: Annotated[tuple[UUID4, ...], Field(max_length=50)] = Field(repr=False)

    @model_validator(mode="after")
    def valid_plan(self) -> Self:
        research_search.validate_plan(self.queries, 0, 0)
        if len(set(self.irrelevant_snapshot_ids)) != len(self.irrelevant_snapshot_ids):
            raise ValueError("Invalid labels")
        return self


class PlannedEvaluationJob(v1._PrivateModel):
    schema_version: Literal[1]
    baseline: v1.EvaluationJob = Field(repr=False)
    plans: Annotated[tuple[EvaluationPlan, ...], Field(min_length=1, max_length=40)] = Field(
        repr=False
    )

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        return v1.EvaluationJob.integer_version(value)

    @model_validator(mode="after")
    def valid_labels_and_order(self) -> Self:
        if tuple(p.case_id for p in self.plans) != tuple(c.case_id for c in self.baseline.cases):
            raise ValueError("Invalid case order")
        corpus = set(self.baseline.corpus_snapshot_ids)
        for case, plan in zip(self.baseline.cases, self.plans, strict=True):
            gold = {member for family in case.expected_families for member in family}
            labels = set(plan.irrelevant_snapshot_ids)
            if not labels <= corpus or gold & labels:
                raise ValueError("Invalid labels")
        return self


class JudgedCaseResult(v1.CaseResult):
    returned_count: int
    relevant_count: int
    irrelevant_count: int
    unjudged_count: int
    judged_precision: float | None


class ComparisonCaseResult(v1._PrivateModel):
    case: v1.EvaluationCase = Field(repr=False)
    plan: EvaluationPlan = Field(repr=False)
    original_terms: tuple[str, ...] = Field(repr=False)
    query_terms: tuple[tuple[str, ...], ...] = Field(repr=False)
    baseline: JudgedCaseResult = Field(repr=False)
    planned: JudgedCaseResult = Field(repr=False)


class PlannedEvaluationReport(v1._PrivateModel):
    schema_version: Literal[1] = 1
    profile: Literal["planned-retrieval-comparison-v1"] = "planned-retrieval-comparison-v1"
    retrieval_profile: str
    judged_precision_denominator: Literal["relevant_plus_irrelevant_excludes_unjudged"] = (
        "relevant_plus_irrelevant_excludes_unjudged"
    )
    job: PlannedEvaluationJob = Field(repr=False)
    job_sha256: str
    question_gold_sha256: str
    plans_labels_sha256: str
    declared_corpus_sha256: str
    corpus_sha256: str
    fingerprints: tuple[v1.SnapshotFingerprint, ...] = Field(repr=False)
    cases: tuple[ComparisonCaseResult, ...] = Field(repr=False)
    summary: dict[str, dict[str, int | float | None]]
    origin_case_counts: dict[Origin, int]


def parse_job(raw: bytes) -> PlannedEvaluationJob:
    """Validate bounded UTF-8 JSON, preserving strict nested v1 baseline contracts."""
    try:
        return PlannedEvaluationJob.model_validate_json(
            json.dumps(v1._job_data(raw), allow_nan=False)
        )
    except Exception:
        raise ValueError("Unable to validate planned retrieval evaluation job") from None


def validate_database_url(value: str | URL, job: PlannedEvaluationJob) -> URL:
    return v1.validate_database_url(value, job.baseline)


def _judged(result: v1.CaseResult, plan: EvaluationPlan) -> JudgedCaseResult:
    gold = {member for family in result.case.expected_families for member in family}
    relevant = sum(identity in gold for identity in result.ranked_snapshot_ids)
    irrelevant = sum(
        identity in plan.irrelevant_snapshot_ids for identity in result.ranked_snapshot_ids
    )
    returned = len(result.ranked_snapshot_ids)
    return JudgedCaseResult(
        **result.model_dump(),
        returned_count=returned,
        relevant_count=relevant,
        irrelevant_count=irrelevant,
        unjudged_count=returned - relevant - irrelevant,
        judged_precision=relevant / (relevant + irrelevant) if relevant + irrelevant else None,
    )


def _summary(cases: Sequence[JudgedCaseResult]) -> dict[str, int | float | None]:
    summary = v1._summary(cases)
    returned = sum(c.returned_count for c in cases)
    relevant = sum(c.relevant_count for c in cases)
    irrelevant = sum(c.irrelevant_count for c in cases)
    summary.update(
        returned_count=returned,
        relevant_count=relevant,
        irrelevant_count=irrelevant,
        unjudged_count=sum(c.unjudged_count for c in cases),
        judged_precision=relevant / (relevant + irrelevant) if relevant + irrelevant else None,
    )
    return summary


def _compare(
    conn: Connection, job: PlannedEvaluationJob, case: v1.EvaluationCase, plan: EvaluationPlan
) -> ComparisonCaseResult:
    original = v1._case_result(conn, job.baseline, case)
    outcome = research_search.search_candidates(
        conn,
        {"workspace_id": job.baseline.workspace_id, "question": case.question},
        plan.queries,
        None,
    )
    if type(outcome) is not tuple or len(outcome) != 2 or outcome[1] is not None:
        raise ValueError("Invalid independent search result")
    planned = v1._ranked_case_result(job.baseline, case, original.terms, outcome[0])
    return ComparisonCaseResult(
        case=case,
        plan=plan,
        original_terms=original.terms,
        query_terms=tuple(question_terms(query) for query in plan.queries),
        baseline=_judged(original, plan),
        planned=_judged(planned, plan),
    )


def evaluate(engine: Engine, raw: bytes) -> PlannedEvaluationReport:
    """Evaluate every original and planned path in one verified read-only transaction."""
    try:
        job = parse_job(raw)
        with v1._evaluation_connection(engine, job.baseline) as conn:
            fingerprints = v1._fingerprints(conn, job.baseline)
            cases = tuple(
                _compare(conn, job, case, plan)
                for case, plan in zip(job.baseline.cases, job.plans, strict=True)
            )
        return PlannedEvaluationReport(
            retrieval_profile=RETRIEVAL_PROFILE,
            job=job,
            job_sha256=_digest(_payload(job)),
            question_gold_sha256=_digest([_payload(c) for c in job.baseline.cases]),
            plans_labels_sha256=_digest([_payload(p) for p in job.plans]),
            declared_corpus_sha256=_digest(sorted(map(str, job.baseline.corpus_snapshot_ids))),
            corpus_sha256=_digest([_payload(fp) for fp in fingerprints]),
            fingerprints=fingerprints,
            cases=cases,
            summary={
                "baseline": _summary([c.baseline for c in cases]),
                "planned": _summary([c.planned for c in cases]),
            },
            origin_case_counts=dict(Counter(p.origin for p in job.plans)),
        )
    except Exception:
        raise ValueError("Unable to evaluate planned retrieval") from None
