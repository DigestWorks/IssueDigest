"""Durable lexical selections; no models, reservations or execution activation.

All operations share the evidence-job SQL transaction gate before auth locks.
This also serializes bounded new searches with short evidence-job transactions;
throughput and operational load acceptance remain separate work.
Canonical hashes detect corruption, not replacement of all data and its hashes.
"""

import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from issuedigest_domain.question_source_plan import QuestionSourceChoice, QuestionSourcePlan
from pydantic import ValidationError
from sqlalchemy import (
    CheckConstraint,
    Column,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    insert,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.engine import Connection, Engine

from . import research_retrieval
from .evidence_jobs import EvidenceJobRepository, digest, source_digest
from .repository import EvidenceRepository, StorageCorruption
from .research import ResearchConflict, ResearchForbidden, ResearchRepository

EVIDENCE_PROFILES = (
    "guarded-question-evidence-v2",
    "guarded-question-evidence-v3",
    "guarded-question-evidence-v5",
)


def validate_evidence_profile(value: object) -> str:
    if type(value) is not str or value not in EVIDENCE_PROFILES:
        raise ValueError("Invalid evidence profile")
    return value


metadata = MetaData()
question_source_plans = Table(
    "question_source_plans",
    metadata,
    *[
        Column(name, PGUUID(as_uuid=True), primary_key=name == "plan_id", nullable=False)
        for name in ("plan_id", "workspace_id", "actor_id", "request_id")
    ],
    *[
        Column(name, String, nullable=False)
        for name in ("question", "input_sha256", "payload_sha256")
    ],
    Column("payload", JSONB, nullable=False),
    Column("evidence_profile", String, nullable=False, server_default=EVIDENCE_PROFILES[0]),
    # Historical migrations 0011/0013 require this v2/v3 baseline.
    # Migration 0014 alone extends the actual database CHECK to v5.
    CheckConstraint(
        "evidence_profile IN ('guarded-question-evidence-v2', 'guarded-question-evidence-v3')",
        name="question_source_plans_evidence_profile_check",
    ),
    UniqueConstraint("workspace_id", "actor_id", "request_id"),
)


def _id(value: object) -> None:
    if type(value) is not UUID or value.version != 4:
        raise ValueError("A UUID v4 is required")


def _input(
    actor: UUID,
    workspace: UUID,
    request: UUID,
    question: str,
    evidence_profile: str = EVIDENCE_PROFILES[0],
) -> str:
    identity = dict(
        actor_id=str(actor),
        workspace_id=str(workspace),
        request_id=str(request),
        question=question,
        profile="question-source-plan-v1",
        retrieval_profile="question-topics-ko-v2",
    )
    if evidence_profile != EVIDENCE_PROFILES[0]:
        identity["evidence_profile"] = validate_evidence_profile(evidence_profile)
    return digest(identity)


class QuestionPlanRepository:
    def __init__(self, engine: Engine, *, evidence_profile: str = EVIDENCE_PROFILES[0]):
        self.evidence_profile = validate_evidence_profile(evidence_profile)
        self.engine = engine
        self._base = ResearchRepository(engine)

    @staticmethod
    def _source(conn: Connection, workspace: UUID, snapshot: UUID) -> str:
        bundle = EvidenceRepository._load(conn, workspace, snapshot)
        if bundle is None:
            raise ResearchConflict("Question plan source unavailable")
        try:
            presentation = ResearchRepository._presentation(conn, workspace, snapshot, bundle)
        except (ValidationError, ValueError, TypeError):
            raise StorageCorruption("Question plan source changed") from None
        return source_digest((snapshot, bundle, presentation))

    @staticmethod
    def _dto(conn: Connection, row: Mapping[Any, Any]) -> QuestionSourcePlan:
        try:
            for field in ("plan_id", "workspace_id", "actor_id", "request_id"):
                _id(row[field])
            profile = validate_evidence_profile(row["evidence_profile"])
            raw = row["payload"]
            if type(raw) is not dict or set(raw) != set(QuestionSourcePlan.model_fields):
                raise ValueError
            if type(raw["sources"]) is not list or any(
                type(source) is not dict or set(source) != set(QuestionSourceChoice.model_fields)
                for source in raw["sources"]
            ):
                raise ValueError
            plan = QuestionSourcePlan.model_validate_json(
                json.dumps(raw, ensure_ascii=False, allow_nan=False), strict=True
            )
            if (
                plan.plan_id != row["plan_id"]
                or plan.workspace_id != row["workspace_id"]
                or plan.request_id != row["request_id"]
                or type(row["question"]) is not str
                or plan.question != row["question"]
                or row["payload_sha256"] != digest(dict(actor_id=str(row["actor_id"]), payload=raw))
                or row["input_sha256"]
                != _input(
                    row["actor_id"], plan.workspace_id, plan.request_id, plan.question, profile
                )
            ):
                raise ValueError
        except (ValidationError, ValueError, TypeError, KeyError):
            raise StorageCorruption("Question plan integrity check failed") from None
        if not ResearchRepository._member(conn, row["actor_id"], plan.workspace_id, write=True):
            raise ResearchForbidden("Question plan authority unavailable")
        for source in plan.sources:
            if (
                QuestionPlanRepository._source(conn, plan.workspace_id, source.snapshot_id)
                != source.source_sha256
            ):
                raise StorageCorruption("Question plan source changed")
        return plan

    def submit(
        self, token: str, workspace_id: UUID, request_id: UUID, question: str
    ) -> QuestionSourcePlan | None:
        _id(workspace_id)
        _id(request_id)
        if type(question) is not str or not question.strip() or len(question) > 1500:
            raise ValueError("Invalid question plan input")

        def save(conn: Connection) -> QuestionSourcePlan | None:
            EvidenceJobRepository._lock_jobs(conn)
            actor = self._base._actor(conn, token, workspace_id, write=True)
            if actor is None:
                return None
            prior = (
                conn.execute(
                    select(question_source_plans)
                    .where(
                        question_source_plans.c.workspace_id == workspace_id,
                        question_source_plans.c.actor_id == actor,
                        question_source_plans.c.request_id == request_id,
                    )
                    .with_for_update()
                )
                .mappings()
                .one_or_none()
            )
            if prior is not None:
                plan = self._dto(conn, prior)
                if plan.question != question:
                    raise ResearchConflict("Question plan request changed")
                return plan
            terms = research_retrieval.question_terms(question)
            ids = (
                research_retrieval.retrieve_snapshot_ids(conn, workspace_id, terms) if terms else ()
            )
            try:
                if type(ids) is not tuple or len(ids) > 5 or len(set(ids)) != len(ids):
                    raise ValueError
                for identity in ids:
                    _id(identity)
            except (TypeError, ValueError):
                raise StorageCorruption("Question plan search result invalid") from None
            sources = tuple(
                QuestionSourceChoice(
                    snapshot_id=identity, source_sha256=self._source(conn, workspace_id, identity)
                )
                for identity in ids
            )
            plan = QuestionSourcePlan(
                plan_id=uuid4(),
                workspace_id=workspace_id,
                request_id=request_id,
                question=question,
                status="selected" if sources else "no_match",
                reason=None if sources else "no_candidates" if terms else "no_terms",
                sources=sources,
            )
            payload = plan.model_dump(mode="json")
            conn.execute(
                insert(question_source_plans).values(
                    plan_id=plan.plan_id,
                    workspace_id=workspace_id,
                    actor_id=actor,
                    request_id=request_id,
                    question=question,
                    input_sha256=_input(
                        actor, workspace_id, request_id, question, self.evidence_profile
                    ),
                    evidence_profile=self.evidence_profile,
                    payload=payload,
                    payload_sha256=digest(dict(actor_id=str(actor), payload=payload)),
                )
            )
            return plan

        return self._base._transaction(save)

    def get(self, token: str, workspace_id: UUID, plan_id: UUID) -> QuestionSourcePlan | None:
        _id(workspace_id)
        _id(plan_id)

        def read(conn: Connection) -> QuestionSourcePlan | None:
            EvidenceJobRepository._lock_jobs(conn)
            if self._base._actor(conn, token, workspace_id) is None:
                return None
            row = (
                conn.execute(
                    select(question_source_plans)
                    .where(
                        question_source_plans.c.workspace_id == workspace_id,
                        question_source_plans.c.plan_id == plan_id,
                    )
                    .with_for_update()
                )
                .mappings()
                .one_or_none()
            )
            return self._dto(conn, row) if row is not None else None

        return self._base._transaction(read)

    def get_evidence_profile(self, token: str, workspace_id: UUID, plan_id: UUID) -> str | None:
        _id(workspace_id)
        _id(plan_id)

        def read(conn: Connection) -> str | None:
            EvidenceJobRepository._lock_jobs(conn)
            if self._base._actor(conn, token, workspace_id) is None:
                return None
            row = (
                conn.execute(
                    select(question_source_plans)
                    .where(
                        question_source_plans.c.workspace_id == workspace_id,
                        question_source_plans.c.plan_id == plan_id,
                    )
                    .with_for_update()
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            self._dto(conn, row)
            return validate_evidence_profile(row["evidence_profile"])

        return self._base._transaction(read)
