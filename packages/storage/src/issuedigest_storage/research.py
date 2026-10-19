"""Transactional protected research repository and durable worker state."""

import json
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Any, cast
from uuid import UUID, uuid4

from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import (
    ResearchRequest,
    ResearchResult,
    ResearchRun,
    ResearchRunEvent,
    ResearchRunList,
    RunStatus,
    SourcePresentation,
    presentation_for,
)
from sqlalchemy import Connection, Engine, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .auth_schema import auth_sessions, auth_users, auth_workspace_memberships
from .engine import verify_engine
from .repository import EvidenceRepository, StorageCorruption, StorageError, _uuid4
from .research_schema import (
    research_budget_months,
    research_events,
    research_runs,
    source_presentations,
)
from .schema import evidence_snapshots
from .session_policy import SESSION_IDLE_TIMEOUT_SECONDS
from .sessions import AuthenticationDenied, token_digest


class ResearchConflict(Exception):
    """Known, fixed conflict: idempotency, active run or monthly budget."""


class ResearchBudgetExceeded(ResearchConflict):
    """Monthly reservation cap reached."""


class ResearchForbidden(Exception):
    """A current member lacks write authority."""


class ResearchRepository:
    def __init__(self, engine: Engine):
        verify_engine(engine)
        self.engine = engine

    def _transaction[T](self, operation: Callable[[Connection], T]) -> T:
        try:
            with self.engine.begin() as conn:
                return operation(conn)
        except IntegrityError:
            raise ResearchConflict("Research request conflicts with an active run") from None
        except SQLAlchemyError:
            raise StorageError("Research storage unavailable") from None

    @staticmethod
    def _member(
        conn: Connection, user_id: UUID, workspace_id: UUID, *, write: bool = False
    ) -> bool:
        row = conn.execute(
            select(auth_workspace_memberships.c.role)
            .join(auth_users, auth_users.c.user_id == auth_workspace_memberships.c.user_id)
            .where(
                auth_workspace_memberships.c.workspace_id == workspace_id,
                auth_workspace_memberships.c.user_id == user_id,
                auth_workspace_memberships.c.active.is_(True),
                auth_users.c.enabled.is_(True),
            )
            .with_for_update()
        ).scalar_one_or_none()
        if row is None:
            return False
        if write and row not in {"owner", "editor"}:
            raise ResearchForbidden("Research write forbidden")
        return True

    @staticmethod
    def _actor(
        conn: Connection, token: str, workspace_id: UUID, *, write: bool = False
    ) -> UUID | None:
        digest = token_digest(token)
        session = (
            conn.execute(
                select(auth_sessions)
                .where(auth_sessions.c.token_sha256 == digest)
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        now = cast(datetime, conn.scalar(select(func.clock_timestamp())))
        if (
            session is None
            or session["revoked"]
            or session["expires_at"] <= now
            or session["last_activity_at"] <= now - timedelta(seconds=SESSION_IDLE_TIMEOUT_SECONDS)
        ):
            raise AuthenticationDenied("Authentication required")
        user_id = cast(UUID, session["user_id"])
        if not ResearchRepository._member(conn, user_id, workspace_id, write=write):
            return None
        conn.execute(
            update(auth_sessions)
            .where(auth_sessions.c.token_sha256 == digest)
            .values(last_activity_at=func.clock_timestamp())
        )
        return user_id

    @staticmethod
    def _presentation(
        conn: Connection, workspace_id: UUID, snapshot_id: UUID, bundle: Any
    ) -> SourcePresentation:
        row = conn.execute(
            select(source_presentations.c.payload).where(
                source_presentations.c.workspace_id == workspace_id,
                source_presentations.c.snapshot_id == snapshot_id,
            )
        ).scalar_one_or_none()
        if row is not None:
            presentation = SourcePresentation.model_validate(row)
            if presentation.workspace_id != workspace_id or presentation.snapshot_id != snapshot_id:
                raise StorageCorruption("Source presentation mismatch")
            return presentation
        presentation = presentation_for(bundle, snapshot_id)
        conn.execute(
            pg_insert(source_presentations)
            .values(
                snapshot_id=snapshot_id,
                workspace_id=workspace_id,
                payload=presentation.model_dump(mode="json"),
            )
            .on_conflict_do_nothing()
        )
        return presentation

    def upsert_presentation(self, presentation: SourcePresentation) -> None:
        """Operator-supplied verified metadata; no immutable evidence mutation."""

        self._transaction(lambda conn: self._upsert_presentation(conn, presentation))

    @staticmethod
    def _upsert_presentation(conn: Connection, presentation: SourcePresentation) -> None:
        exists = conn.scalar(
            select(evidence_snapshots.c.snapshot_id).where(
                evidence_snapshots.c.workspace_id == presentation.workspace_id,
                evidence_snapshots.c.snapshot_id == presentation.snapshot_id,
            )
        )
        if exists is None:
            raise ResearchConflict("Unknown snapshot")
        conn.execute(
            pg_insert(source_presentations)
            .values(
                snapshot_id=presentation.snapshot_id,
                workspace_id=presentation.workspace_id,
                payload=presentation.model_dump(mode="json"),
            )
            .on_conflict_do_update(
                index_elements=[source_presentations.c.snapshot_id],
                set_={"payload": presentation.model_dump(mode="json")},
            )
        )

    @staticmethod
    def _run(conn: Connection, row: Mapping[Any, Any]) -> ResearchRun:
        events = (
            conn.execute(
                select(research_events)
                .where(research_events.c.run_id == row["run_id"])
                .order_by(research_events.c.sequence)
            )
            .mappings()
            .all()
        )
        result = (
            ResearchResult.model_validate_json(json.dumps(row["result"], allow_nan=False))
            if row["result"] is not None
            else None
        )
        run = ResearchRun(
            run_id=row["run_id"],
            workspace_id=row["workspace_id"],
            request_id=row["request_id"],
            question=row["question"],
            snapshot_ids=tuple(UUID(s) for s in row["snapshot_ids"]),
            parent_run_id=row["parent_run_id"],
            status=row["status"],
            error_code=row["error_code"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            events=tuple(
                ResearchRunEvent(
                    sequence=e["sequence"], status=e["status"], created_at=e["created_at"]
                )
                for e in events
            ),
            result=result,
            model=row["model"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
        )
        if run.status != "completed":
            return run
        return ResearchRepository._completed_provenance(conn, row, run)

    @staticmethod
    def _completed_provenance(
        conn: Connection, row: Mapping[Any, Any], run: ResearchRun
    ) -> ResearchRun:
        """Revalidate originals; expand only proven legacy seed provenance, without writes."""
        assert run.result is not None
        evidence = run.result.canvas.research.evidence
        if not 1 <= len(evidence) <= 5:
            raise StorageCorruption("Invalid completed source count")
        known = tuple(
            EvidenceRepository._load(conn, run.workspace_id, snapshot)
            for snapshot in run.snapshot_ids
        )
        if known != evidence[: len(known)]:
            raise StorageCorruption("Research result differs from fixed provenance")
        if len(known) == len(evidence):
            return run
        # v1 hashed the request's selected seeds. v2 hashes question/parent only.
        # Check the historical input as well as derivations, including no-claim results.
        legacy_input = json.dumps(
            {
                "question": run.question,
                "snapshot_ids": [str(snapshot) for snapshot in run.snapshot_ids],
                "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        if (
            not 1 <= len(known) <= 3
            or row["input_hash"] != sha256(legacy_input.encode()).hexdigest()
            or any(
                claim.derivation is None or claim.derivation.method_version != "research-v1"
                for claim in run.result.canvas.research.claims
            )
        ):
            raise StorageCorruption("Research result differs from fixed provenance")
        resolved = list(run.snapshot_ids)
        for bundle in evidence[len(known) :]:
            snapshot = conn.scalar(
                select(evidence_snapshots.c.snapshot_id)
                .where(
                    evidence_snapshots.c.workspace_id == run.workspace_id,
                    evidence_snapshots.c.document_id == bundle.document.document_id,
                    evidence_snapshots.c.version_id == bundle.version.version_id,
                    evidence_snapshots.c.representation_id
                    == bundle.representation.representation_id,
                    evidence_snapshots.c.payload == bundle.model_dump(mode="json"),
                )
                .order_by(evidence_snapshots.c.snapshot_id)
                .limit(1)
            )
            if (
                snapshot is None
                or snapshot in resolved
                or EvidenceRepository._load(conn, run.workspace_id, snapshot) != bundle
            ):
                raise StorageCorruption("Historical source provenance unavailable")
            resolved.append(snapshot)
        return run.model_copy(update={"snapshot_ids": tuple(resolved)})

    def submit(
        self, token: str, workspace_id: UUID, request: ResearchRequest
    ) -> ResearchRun | None:
        _uuid4(workspace_id)
        request = ResearchRequest.model_validate(dict(request.__dict__))
        canonical = json.dumps(
            request.model_dump(mode="json", exclude={"request_id"}),
            sort_keys=True,
            ensure_ascii=False,
        )
        digest = sha256(canonical.encode()).hexdigest()

        def save(conn: Connection) -> ResearchRun | None:
            actor = self._actor(conn, token, workspace_id, write=True)
            if actor is None:
                return None
            lock_key = int.from_bytes(
                sha256(workspace_id.bytes + actor.bytes + request.request_id.bytes).digest()[:8],
                "big",
                signed=True,
            )
            conn.scalar(select(func.pg_advisory_xact_lock(lock_key)))
            prior = (
                conn.execute(
                    select(research_runs).where(
                        research_runs.c.workspace_id == workspace_id,
                        research_runs.c.actor_id == actor,
                        research_runs.c.request_id == request.request_id,
                    )
                )
                .mappings()
                .one_or_none()
            )
            if prior is not None:
                if prior["input_hash"] != digest:
                    raise ResearchConflict("Idempotency key changed input")
                return self._run(conn, prior)
            if request.parent_run_id is not None:
                parent = conn.execute(
                    select(research_runs.c.status).where(
                        research_runs.c.run_id == request.parent_run_id,
                        research_runs.c.workspace_id == workspace_id,
                    )
                ).scalar_one_or_none()
                if parent != "completed":
                    raise ResearchConflict("Parent research unavailable")
            active = conn.scalar(
                select(research_runs.c.run_id).where(
                    research_runs.c.workspace_id == workspace_id,
                    research_runs.c.status.in_(
                        ["queued", "retrieving", "generating", "validating"]
                    ),
                )
            )
            if active is not None:
                raise ResearchConflict("Research already active")
            month = conn.scalar(select(func.to_char(func.clock_timestamp(), "YYYY-MM")))
            conn.execute(
                pg_insert(research_budget_months).values(month=month).on_conflict_do_nothing()
            )
            budget = (
                conn.execute(
                    select(research_budget_months)
                    .where(research_budget_months.c.month == month)
                    .with_for_update()
                )
                .mappings()
                .one()
            )
            if budget["reservation_count"] >= 40 or budget["reserved_usd"] + Decimal(
                "0.25"
            ) > Decimal("10.00"):
                raise ResearchBudgetExceeded("Monthly research budget reached")
            conn.execute(
                update(research_budget_months)
                .where(research_budget_months.c.month == month)
                .values(
                    reserved_usd=research_budget_months.c.reserved_usd + Decimal("0.25"),
                    reservation_count=research_budget_months.c.reservation_count + 1,
                )
            )
            run_id = uuid4()
            conn.execute(
                insert(research_runs).values(
                    run_id=run_id,
                    workspace_id=workspace_id,
                    actor_id=actor,
                    request_id=request.request_id,
                    input_hash=digest,
                    question=request.question,
                    snapshot_ids=[],
                    parent_run_id=request.parent_run_id,
                    status="queued",
                    model="gpt-5.4-mini",
                    budget_month=month,
                    reserved_usd=Decimal("0.25"),
                )
            )
            conn.execute(insert(research_events).values(run_id=run_id, sequence=1, status="queued"))
            row = (
                conn.execute(select(research_runs).where(research_runs.c.run_id == run_id))
                .mappings()
                .one()
            )
            return self._run(conn, row)

        return self._transaction(save)

    def get_run(self, token: str, workspace_id: UUID, run_id: UUID) -> ResearchRun | None:
        _uuid4(workspace_id)
        _uuid4(run_id)

        def read(conn: Connection) -> ResearchRun | None:
            if self._actor(conn, token, workspace_id) is None:
                return None
            row = (
                conn.execute(
                    select(research_runs).where(
                        research_runs.c.workspace_id == workspace_id,
                        research_runs.c.run_id == run_id,
                    )
                )
                .mappings()
                .one_or_none()
            )
            return self._run(conn, row) if row is not None else None

        return self._transaction(read)

    def list_runs(self, token: str, workspace_id: UUID) -> ResearchRunList | None:
        _uuid4(workspace_id)

        def read(conn: Connection) -> ResearchRunList | None:
            if self._actor(conn, token, workspace_id) is None:
                return None
            rows = (
                conn.execute(
                    select(research_runs)
                    .where(research_runs.c.workspace_id == workspace_id)
                    .order_by(research_runs.c.created_at.desc())
                    .limit(100)
                )
                .mappings()
                .all()
            )
            return ResearchRunList(
                workspace_id=workspace_id, items=tuple(self._run(conn, row) for row in rows)
            )

        return self._transaction(read)

    def cancel(self, token: str, workspace_id: UUID, run_id: UUID) -> ResearchRun | None:
        _uuid4(workspace_id)
        _uuid4(run_id)

        def change(conn: Connection) -> ResearchRun | None:
            if self._actor(conn, token, workspace_id, write=True) is None:
                return None
            row = (
                conn.execute(
                    select(research_runs)
                    .where(
                        research_runs.c.workspace_id == workspace_id,
                        research_runs.c.run_id == run_id,
                    )
                    .with_for_update()
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            if row["status"] in {"queued", "retrieving", "generating", "validating"}:
                self._transition(conn, row, "cancelled", "cancelled")
            final = (
                conn.execute(select(research_runs).where(research_runs.c.run_id == run_id))
                .mappings()
                .one()
            )
            return self._run(conn, final)

        return self._transaction(change)

    @staticmethod
    def _transition(
        conn: Connection,
        row: Mapping[Any, Any],
        status: RunStatus,
        error_code: str | None = None,
        result: ResearchResult | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        sequence = (
            cast(
                int,
                conn.scalar(
                    select(func.coalesce(func.max(research_events.c.sequence), 0)).where(
                        research_events.c.run_id == row["run_id"]
                    )
                ),
            )
            + 1
        )
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == row["run_id"])
            .values(
                status=status,
                error_code=error_code,
                result=result.model_dump(mode="json") if result else None,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                updated_at=func.clock_timestamp(),
            )
        )
        conn.execute(
            insert(research_events).values(run_id=row["run_id"], sequence=sequence, status=status)
        )

    def worker_states(self, run_ids: tuple[UUID, ...]) -> dict[UUID, RunStatus]:
        """Read only owned application states for bounded DBOS recovery metadata checks."""

        def read(conn: Connection) -> dict[UUID, RunStatus]:
            return {
                row.run_id: row.status
                for row in conn.execute(
                    select(research_runs.c.run_id, research_runs.c.status).where(
                        research_runs.c.run_id.in_(run_ids)
                    )
                )
            }

        return self._transaction(read)

    def worker_active_runs(self, after: UUID | None = None) -> tuple[tuple[UUID, RunStatus], ...]:
        """Page active rows without reopening originals, sessions or provider requests."""

        def read(conn: Connection) -> tuple[tuple[UUID, RunStatus], ...]:
            query = select(research_runs.c.run_id, research_runs.c.status).where(
                research_runs.c.status.in_(["queued", "retrieving", "generating", "validating"])
            )
            if after is not None:
                query = query.where(research_runs.c.run_id > after)
            return tuple(
                (row.run_id, row.status)
                for row in conn.execute(query.order_by(research_runs.c.run_id).limit(20))
            )

        return self._transaction(read)

    def queued_ids(self) -> tuple[UUID, ...]:
        def read(conn: Connection) -> tuple[UUID, ...]:
            return tuple(
                conn.scalars(
                    select(research_runs.c.run_id)
                    .where(research_runs.c.status == "queued")
                    .order_by(research_runs.c.created_at)
                    .limit(20)
                ).all()
            )

        return self._transaction(read)

    def _worker_row(self, conn: Connection, run_id: UUID) -> Mapping[Any, Any] | None:
        """Keep the membership-before-run lock order shared with cancellation."""
        row = (
            conn.execute(select(research_runs).where(research_runs.c.run_id == run_id))
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        try:
            allowed = self._member(conn, row["actor_id"], row["workspace_id"], write=True)
        except ResearchForbidden:
            allowed = False
        row = (
            conn.execute(
                select(research_runs).where(research_runs.c.run_id == run_id).with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if row is None or row["status"] not in {
            "queued",
            "retrieving",
            "generating",
            "validating",
        }:
            return None
        if not allowed:
            self._transition(conn, row, "failed", "authority_changed")
            return None
        return row

    def _worker_parent(self, conn: Connection, row: Mapping[Any, Any]) -> ResearchRun | None:
        verified_parent: ResearchRun | None = None
        if row["parent_run_id"] is not None:
            parent = (
                conn.execute(
                    select(research_runs).where(
                        research_runs.c.run_id == row["parent_run_id"],
                        research_runs.c.workspace_id == row["workspace_id"],
                        research_runs.c.status == "completed",
                    )
                )
                .mappings()
                .one_or_none()
            )
            if parent is None:
                raise StorageCorruption("Parent research unavailable")
            verified_parent = self._run(conn, parent)
        return verified_parent

    def _worker_sources(
        self,
        conn: Connection,
        workspace_id: UUID,
        candidate_ids: tuple[UUID, ...],
        parent_evidence: tuple[EvidenceBundle, ...] | None = None,
    ) -> tuple[tuple[UUID, Any, SourcePresentation], ...]:
        sources = []
        for snapshot_id in candidate_ids:
            bundle = EvidenceRepository._load(conn, workspace_id, snapshot_id)
            if bundle is None:
                raise StorageCorruption("Retrieved source unavailable")
            if parent_evidence is not None and bundle not in parent_evidence:
                raise StorageCorruption("Parent source provenance mismatch")
            sources.append(
                (snapshot_id, bundle, self._presentation(conn, workspace_id, snapshot_id, bundle))
            )
        return tuple(sources)

    def worker_prepare_search(self, run_id: UUID) -> ResearchRun | None:
        """Authorize the planner without searching or advancing application state."""
        _uuid4(run_id)

        def read(conn: Connection) -> ResearchRun | None:
            row = self._worker_row(conn, run_id)
            if row is None:
                return None
            self._worker_parent(conn, row)
            return self._run(conn, row)

        return self._transaction(read)

    def worker_search_and_fix(
        self,
        run_id: UUID,
        queries: tuple[str, ...],
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> tuple[UUID, ...] | None:
        """Atomically reauthorize, select exact sources, or record a known no-match."""
        from .research_retrieval import is_generic_followup, question_terms
        from .research_search import search_candidates, validate_plan

        _uuid4(run_id)
        validate_plan(queries, input_tokens, output_tokens)

        def fix(conn: Connection) -> tuple[UUID, ...] | None:
            row = self._worker_row(conn, run_id)
            if row is None:
                return None
            parent = self._worker_parent(conn, row)
            fixed = tuple(UUID(value) for value in row["snapshot_ids"])
            if fixed:
                if len(fixed) > 5 or len(set(fixed)) != len(fixed):
                    raise StorageCorruption("Invalid fixed source count")
                if (
                    parent is not None
                    and not question_terms(row["question"])
                    and is_generic_followup(row["question"])
                    and fixed != parent.snapshot_ids
                ):
                    raise StorageCorruption("Parent source provenance mismatch")
                self._worker_sources(conn, row["workspace_id"], fixed)
                return fixed
            if row["status"] != "retrieving":
                return None
            candidate_ids, parent_evidence = search_candidates(conn, row, queries, parent)
            if not candidate_ids:
                self._transition(
                    conn,
                    row,
                    "failed",
                    "insufficient_evidence",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                return None
            self._worker_sources(conn, row["workspace_id"], candidate_ids, parent_evidence)
            conn.execute(
                update(research_runs)
                .where(research_runs.c.run_id == run_id)
                .values(snapshot_ids=[str(identity) for identity in candidate_ids])
            )
            return candidate_ids

        return self._transaction(fix)

    @staticmethod
    def _relevance_ids(candidate_ids: tuple[UUID, ...], *, empty: bool = False) -> None:
        if (
            type(candidate_ids) is not tuple
            or not (0 if empty else 1) <= len(candidate_ids) <= 5
            or len(set(candidate_ids)) != len(candidate_ids)
        ):
            raise ValueError("Invalid relevance source count")
        for identity in candidate_ids:
            _uuid4(identity)

    def _relevance_row(
        self, conn: Connection, run_id: UUID, candidate_ids: tuple[UUID, ...]
    ) -> tuple[Mapping[Any, Any], tuple[tuple[UUID, Any, SourcePresentation], ...]] | None:
        row = self._worker_row(conn, run_id)
        if row is None:
            return None
        parent = self._worker_parent(conn, row)
        if parent is not None:
            from .research_retrieval import is_generic_followup, question_terms

            if (
                not question_terms(row["question"])
                and is_generic_followup(row["question"])
                and candidate_ids != parent.snapshot_ids
            ):
                raise StorageCorruption("Parent source provenance mismatch")
        fixed = tuple(UUID(value) for value in row["snapshot_ids"])
        if not fixed or fixed != tuple(s for s in candidate_ids if s in fixed):
            raise StorageCorruption("Relevance candidate provenance changed")
        # Reopen *all* originals, including excluded ones, on every recovery.
        sources = self._worker_sources(conn, row["workspace_id"], candidate_ids)
        return row, sources

    def worker_record_relevance_usage(
        self, run_id: UUID, *, input_tokens: int, output_tokens: int
    ) -> tuple[int, int]:
        """Trusted v9 accounting only, even after cancellation or authority revocation.

        Never changes status, result, provenance, authority or conservative reservations.
        Earlier replay subtotals cannot erase a later known response's usage.
        """
        _uuid4(run_id)
        if (
            type(input_tokens) is not int
            or type(output_tokens) is not int
            or input_tokens < 0
            or output_tokens < 0
            or input_tokens + output_tokens > 24_000
            or output_tokens > 2_500
        ):
            raise ValueError("Invalid relevance accounting")

        def record(conn: Connection) -> tuple[int, int]:
            result = conn.execute(
                update(research_runs)
                .where(research_runs.c.run_id == run_id)
                .values(
                    input_tokens=func.greatest(research_runs.c.input_tokens, input_tokens),
                    output_tokens=func.greatest(research_runs.c.output_tokens, output_tokens),
                )
                .returning(research_runs.c.input_tokens, research_runs.c.output_tokens)
            ).one_or_none()
            return (result.input_tokens, result.output_tokens) if result is not None else (0, 0)

        return self._transaction(record)

    def worker_load_relevance_candidates(
        self, run_id: UUID, candidate_ids: tuple[UUID, ...]
    ) -> tuple[ResearchRun, tuple[tuple[UUID, Any, SourcePresentation], ...]] | None:
        """Trusted journal candidates only; never grants authority or repeats search."""
        _uuid4(run_id)
        self._relevance_ids(candidate_ids)

        def read(
            conn: Connection,
        ) -> tuple[ResearchRun, tuple[tuple[UUID, Any, SourcePresentation], ...]] | None:
            loaded = self._relevance_row(conn, run_id, candidate_ids)
            if loaded is None:
                return None
            row, sources = loaded
            return self._run(conn, row), sources

        return self._transaction(read)

    def worker_apply_relevance_selection(
        self,
        run_id: UUID,
        candidate_ids: tuple[UUID, ...],
        selected_ids: tuple[UUID, ...],
        *,
        input_tokens: int,
        output_tokens: int,
    ) -> tuple[UUID, ...] | None:
        """One ordered narrowing or identical replay, in the existing authority lock order."""
        _uuid4(run_id)
        self._relevance_ids(candidate_ids)
        self._relevance_ids(selected_ids, empty=True)
        if selected_ids != tuple(s for s in candidate_ids if s in selected_ids):
            raise ValueError("Invalid ordered relevance subset")
        if (
            type(input_tokens) is not int
            or type(output_tokens) is not int
            or input_tokens < 0
            or output_tokens < 0
            or input_tokens + output_tokens > 20_000
            or output_tokens > 1_000
        ):
            raise ValueError("Invalid relevance usage")

        def apply(conn: Connection) -> tuple[UUID, ...] | None:
            loaded = self._relevance_row(conn, run_id, candidate_ids)
            if loaded is None:
                return None
            row, _ = loaded
            fixed = tuple(UUID(value) for value in row["snapshot_ids"])
            if fixed not in (candidate_ids, selected_ids):
                raise StorageCorruption("Relevance selection changed")
            conn.execute(
                update(research_runs)
                .where(research_runs.c.run_id == run_id)
                .values(
                    snapshot_ids=[str(identity) for identity in selected_ids],
                    input_tokens=func.greatest(research_runs.c.input_tokens, input_tokens),
                    output_tokens=func.greatest(research_runs.c.output_tokens, output_tokens),
                )
            )
            if not selected_ids:
                self._transition(
                    conn,
                    row,
                    "failed",
                    "insufficient_evidence",
                    input_tokens=max(row["input_tokens"], input_tokens),
                    output_tokens=max(row["output_tokens"], output_tokens),
                )
                return None
            return selected_ids

        return self._transaction(apply)

    def worker_load(
        self, run_id: UUID
    ) -> tuple[ResearchRun, tuple[tuple[UUID, Any, SourcePresentation], ...]] | None:
        """Recheck actor membership and canonical evidence before model input."""

        def read(
            conn: Connection,
        ) -> tuple[ResearchRun, tuple[tuple[UUID, Any, SourcePresentation], ...]] | None:
            row = self._worker_row(conn, run_id)
            if row is None:
                return None
            verified_parent = self._worker_parent(conn, row)
            parent_evidence: tuple[EvidenceBundle, ...] | None = None
            if row["status"] == "queued":
                from .research_retrieval import (
                    is_generic_followup,
                    question_terms,
                    retrieve_snapshot_ids,
                )

                terms = question_terms(row["question"])
                candidate_ids = retrieve_snapshot_ids(conn, row["workspace_id"], terms)
                if (
                    not terms
                    and verified_parent is not None
                    and is_generic_followup(row["question"])
                ):
                    candidate_ids = verified_parent.snapshot_ids
                    assert verified_parent.result is not None
                    parent_evidence = verified_parent.result.canvas.research.evidence
                if not candidate_ids:
                    self._transition(conn, row, "failed", "insufficient_evidence")
                    return None
            else:
                # Replay uses the committed provenance, never today's search results.
                candidate_ids = tuple(UUID(snapshot) for snapshot in row["snapshot_ids"])
            sources = self._worker_sources(
                conn, row["workspace_id"], candidate_ids, parent_evidence
            )
            if row["status"] == "queued":
                conn.execute(
                    update(research_runs)
                    .where(research_runs.c.run_id == run_id)
                    .values(snapshot_ids=[str(identity) for identity in candidate_ids])
                )
                self._transition(conn, row, "retrieving")
                row = (
                    conn.execute(select(research_runs).where(research_runs.c.run_id == run_id))
                    .mappings()
                    .one()
                )
            return self._run(conn, row), sources

        return self._transaction(read)

    def worker_parent_context(self, run_id: UUID) -> str | None:
        def read(conn: Connection) -> str | None:
            row = (
                conn.execute(select(research_runs).where(research_runs.c.run_id == run_id))
                .mappings()
                .one_or_none()
            )
            if (
                row is None
                or row["parent_run_id"] is None
                or not self._member(conn, row["actor_id"], row["workspace_id"])
            ):
                return None
            parent = (
                conn.execute(
                    select(research_runs).where(
                        research_runs.c.run_id == row["parent_run_id"],
                        research_runs.c.workspace_id == row["workspace_id"],
                        research_runs.c.status == "completed",
                    )
                )
                .mappings()
                .one_or_none()
            )
            if parent is None:
                return None
            result = ResearchResult.model_validate_json(
                json.dumps(parent["result"], allow_nan=False)
            )
            claims = [claim.text for claim in result.canvas.research.claims[:4]]
            return json.dumps(
                {"prior_question": parent["question"], "prior_interpretations": claims},
                ensure_ascii=False,
            )[:1500]

        return self._transaction(read)

    def worker_transition(
        self,
        run_id: UUID,
        status: RunStatus,
        *,
        error_code: str | None = None,
        result: ResearchResult | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> bool:
        def change(conn: Connection) -> bool:
            row = (
                conn.execute(select(research_runs).where(research_runs.c.run_id == run_id))
                .mappings()
                .one_or_none()
            )
            if row is None:
                return False
            try:
                allowed = self._member(conn, row["actor_id"], row["workspace_id"], write=True)
            except ResearchForbidden:
                allowed = False
            row = (
                conn.execute(
                    select(research_runs).where(research_runs.c.run_id == run_id).with_for_update()
                )
                .mappings()
                .one_or_none()
            )
            if row is None or row["status"] in {"cancelled", "failed", "completed"}:
                return False
            if not allowed:
                status_final: RunStatus = "failed"
                self._transition(conn, row, status_final, "authority_changed")
                return False
            progress = {"queued": 0, "retrieving": 1, "generating": 2, "validating": 3}
            if status in progress and progress[status] <= progress[row["status"]]:
                # A recovered DBOS workflow replays application code around its checkpoints.
                return True
            if status == "completed":
                if (
                    result is None
                    or result.canvas.revision.run_id != run_id
                    or result.canvas.revision.workspace_id != row["workspace_id"]
                ):
                    raise StorageError("Invalid research result")
                expected = tuple(
                    EvidenceRepository._load(conn, row["workspace_id"], UUID(snapshot))
                    for snapshot in row["snapshot_ids"]
                )
                if not expected or result.canvas.research.evidence != expected:
                    raise StorageCorruption("Research result differs from fixed provenance")
            self._transition(conn, row, status, error_code, result, input_tokens, output_tokens)
            return True

        return self._transaction(change)
