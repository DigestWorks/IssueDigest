"""Transactional protected research repository and durable worker state."""

import json
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from typing import Any, cast
from uuid import UUID, uuid4

from issuedigest_domain import EvidenceSearchQuery
from issuedigest_domain.research_journey import (
    ResearchRequest,
    ResearchResult,
    ResearchRun,
    ResearchRunEvent,
    ResearchRunList,
    ResearchSource,
    ResearchSourceCatalog,
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
            or session["last_activity_at"] <= now - timedelta(minutes=30)
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

        def save(conn: Connection) -> None:
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

        self._transaction(save)

    def list_sources(self, token: str, workspace_id: UUID) -> ResearchSourceCatalog | None:
        _uuid4(workspace_id)

        def read(conn: Connection) -> ResearchSourceCatalog | None:
            if self._actor(conn, token, workspace_id) is None:
                return None
            ids = conn.scalars(
                select(evidence_snapshots.c.snapshot_id)
                .where(evidence_snapshots.c.workspace_id == workspace_id)
                .order_by(evidence_snapshots.c.created_at.desc())
                .limit(101)
            ).all()
            items = []
            for snapshot_id in ids[:100]:
                bundle = EvidenceRepository._load(conn, workspace_id, snapshot_id)
                if bundle is None:
                    raise StorageError("Source unavailable")
                title = self._presentation(conn, workspace_id, snapshot_id, bundle)
                excerpt = bundle.representation.text[:160]
                if bundle.representation.normalization_profile == "legacy-bill-dossier-v1":
                    marker = "제안이유·주요내용\n"
                    if marker in bundle.representation.text:
                        excerpt = bundle.representation.text.split(marker, 1)[1][:160]
                items.append(
                    ResearchSource(
                        snapshot_id=snapshot_id,
                        document_id=bundle.document.document_id,
                        title=title.title,
                        source_kind=bundle.document.source_kind,
                        bill_number=title.bill_number,
                        proposed_on=title.proposed_on,
                        collected_at=bundle.version.collected_at,
                        canonical_url=bundle.document.canonical_url,
                        citation_count=len(bundle.citations),
                        excerpt=excerpt,
                    )
                )
            return ResearchSourceCatalog(workspace_id=workspace_id, items=tuple(items))

        return self._transaction(read)

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
        return ResearchRun(
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

    def submit(
        self, token: str, workspace_id: UUID, request: ResearchRequest
    ) -> ResearchRun | None:
        _uuid4(workspace_id)
        request = ResearchRequest.model_validate(request)
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
            for snapshot_id in request.snapshot_ids:
                if (
                    conn.scalar(
                        select(evidence_snapshots.c.snapshot_id).where(
                            evidence_snapshots.c.workspace_id == workspace_id,
                            evidence_snapshots.c.snapshot_id == snapshot_id,
                        )
                    )
                    is None
                ):
                    raise ResearchConflict("Selected source unavailable")
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
                    snapshot_ids=[str(s) for s in request.snapshot_ids],
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

    def worker_load(
        self, run_id: UUID
    ) -> tuple[ResearchRun, tuple[tuple[UUID, Any, SourcePresentation], ...]] | None:
        """Recheck actor membership and canonical evidence before model input."""

        def read(
            conn: Connection,
        ) -> tuple[ResearchRun, tuple[tuple[UUID, Any, SourcePresentation], ...]] | None:
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
            candidate_ids = [UUID(snapshot) for snapshot in row["snapshot_ids"][:3]]
            # Existing literal index adds only query-relevant sources; selected seeds always lead.
            from .search import search_evidence

            terms = tuple(dict.fromkeys(re.findall(r"[가-힣A-Za-z0-9]{2,32}", row["question"])))[:4]
            for term in terms:
                if len(candidate_ids) >= 5:
                    break
                found = search_evidence(
                    conn, row["workspace_id"], EvidenceSearchQuery(terms=(term,), limit=10)
                )
                for hit in found.hits:
                    if hit.snapshot_id not in candidate_ids:
                        candidate_ids.append(hit.snapshot_id)
                    if len(candidate_ids) >= 5:
                        break
            sources = []
            for snapshot_id in candidate_ids:
                bundle = EvidenceRepository._load(conn, row["workspace_id"], snapshot_id)
                if bundle is None:
                    raise StorageCorruption("Selected source unavailable")
                sources.append(
                    (
                        snapshot_id,
                        bundle,
                        self._presentation(conn, row["workspace_id"], snapshot_id, bundle),
                    )
                )
            return self._run(conn, row), tuple(sources)

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
            self._transition(conn, row, status, error_code, result, input_tokens, output_tokens)
            return True

        return self._transaction(change)
