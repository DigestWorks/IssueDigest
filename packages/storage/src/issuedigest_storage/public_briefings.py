"""Trusted publication writes and anonymous validated reads, solely in public tables."""

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from issuedigest_domain.contract_values import SafePositive
from issuedigest_domain.public_briefings import (
    PublicBriefingDetail,
    PublicBriefingList,
    PublicBriefingPlan,
    PublicBriefingSummary,
    PublicSourceReview,
    Slug,
    canonical_hash,
    content_hash,
    plan_hash,
    publish_copy,
    revalidate_plan,
)
from issuedigest_domain.sources import Sha256
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import Connection, Engine, func, insert, select, text, update
from sqlalchemy.exc import SQLAlchemyError

from .public_briefing_schema import public_briefing_heads as heads
from .public_briefing_schema import public_briefings as rows
from .repository import StorageConflict, StorageCorruption, StorageError


class PublicBriefingRepository:
    def __init__(self, engine: Engine) -> None:
        if engine.dialect.name != "postgresql" or engine.dialect.driver != "psycopg":
            raise ValueError("Public storage requires PostgreSQL with psycopg")
        self.engine = engine

    @staticmethod
    def _row(row: Mapping[Any, Any], head: Mapping[Any, Any]) -> PublicBriefingDetail:
        try:
            detail = PublicBriefingDetail.model_validate_json(json.dumps(row["payload"]))
            TypeAdapter(Sha256).validate_python(row["plan_sha256"])
            review_record = row["review_record"]
            if review_record["review_sha256"] != canonical_hash(
                {key: value for key, value in review_record.items() if key != "review_sha256"}
            ):
                raise ValueError("Public review integrity mismatch")
            if (
                row["content_sha256"] != content_hash(detail)
                or row["slug"] != detail.slug
                or row["version"] != detail.version
                or row["public_id"] != detail.public_id
                or row["published_at"] != detail.published_at
                or head["public_id"] != detail.public_id
                or head["slug"] != detail.slug
                or row["version"] > head["latest_version"]
                or (
                    row["version"] == head["latest_version"]
                    and row["content_sha256"] != head["latest_content_sha256"]
                )
                or row["review_record"]["plan_sha256"] != row["plan_sha256"]
            ):
                raise ValueError("Public row mismatch")
            reviews = TypeAdapter(tuple[PublicSourceReview, ...]).validate_json(
                json.dumps(row["review_record"]["sources"])
            )
            if len(reviews) != len(detail.sources) or len({s.document_id for s in reviews}) != len(
                reviews
            ):
                raise ValueError("Public review mismatch")
            for review, attribution in zip(reviews, detail.sources, strict=True):
                if (
                    review.model_dump(
                        exclude={
                            "document_id",
                            "checked_at",
                            "reviewer",
                            "photos_excluded",
                            "third_party_material_excluded",
                        }
                    )
                    != attribution.model_dump(exclude={"document_id"})
                    or review.checked_at > detail.published_at
                    or review.checked_at < detail.as_of
                ):
                    raise ValueError("Public review mismatch")
            return detail
        except Exception:
            raise StorageCorruption("Public publication integrity check failed") from None

    @staticmethod
    def _head(conn: Connection, slug: str) -> Mapping[Any, Any] | None:
        head = conn.execute(select(heads).where(heads.c.slug == slug)).mappings().one_or_none()
        if head is not None:
            count, maximum = conn.execute(
                select(func.count(), func.max(rows.c.version)).where(rows.c.slug == slug)
            ).one()
            if maximum != head["latest_version"] or count != maximum:
                raise StorageCorruption("Public latest history is inconsistent")
            latest = (
                conn.execute(
                    select(rows).where(
                        rows.c.slug == slug, rows.c.version == head["latest_version"]
                    )
                )
                .mappings()
                .one_or_none()
            )
            if latest is None:
                raise StorageCorruption("Public latest reference missing")
            PublicBriefingRepository._row(latest, head)
        return head

    @staticmethod
    def _lock(conn: Connection, slug: str) -> None:
        # Transaction lock also serializes the first publication, before a row exists.
        key = int.from_bytes(sha256(f"public-briefing:{slug}".encode()).digest()[:8], signed=True)
        conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})

    @staticmethod
    def _candidate(conn: Connection, plan: PublicBriefingPlan) -> PublicBriefingDetail | None:
        head = PublicBriefingRepository._head(conn, plan.slug)
        if head is None:
            if plan.version != 1 or conn.scalar(
                select(heads.c.slug).where(heads.c.public_id == plan.public_id)
            ):
                raise StorageConflict("Public publication version conflict")
            return None
        if head["public_id"] != plan.public_id:
            raise StorageConflict("Public publication identity conflict")
        row = (
            conn.execute(
                select(rows).where(rows.c.slug == plan.slug, rows.c.version == plan.version)
            )
            .mappings()
            .one_or_none()
        )
        if row is not None:
            detail = PublicBriefingRepository._row(row, head)
            if row["plan_sha256"] != plan_hash(plan) or row["withdrawn_at"] is not None:
                raise StorageConflict("Public publication immutable version conflict")
            return detail
        if plan.version != head["latest_version"] + 1:
            raise StorageConflict("Public publication sequential version required")
        return None

    def check(self, plan: PublicBriefingPlan) -> dict[str, str]:
        plan = revalidate_plan(plan)
        try:
            with (
                self.engine.connect().execution_options(
                    isolation_level="READ COMMITTED", postgresql_readonly=True
                ) as conn,
                conn.begin(),
            ):
                candidate = self._candidate(conn, plan)
                return {
                    "status": "already_published" if candidate else "database_checked",
                    "plan_sha256": plan_hash(plan),
                }
        except SQLAlchemyError:
            raise StorageError("Unable to check public publication database") from None

    def publish(self, plan: PublicBriefingPlan, *, reviewed_sha256: str) -> PublicBriefingDetail:
        plan = revalidate_plan(plan)
        digest = plan_hash(plan)
        if reviewed_sha256 != digest:
            raise ValueError("Exact reviewed publication hash required")
        try:
            with (
                self.engine.connect().execution_options(isolation_level="READ COMMITTED") as conn,
                conn.begin(),
            ):
                self._lock(conn, plan.slug)
                existing = self._candidate(conn, plan)
                if existing is not None:
                    return existing
                detail = publish_copy(plan, datetime.now(UTC))
                if plan.version == 1:
                    conn.execute(
                        insert(heads).values(
                            slug=plan.slug,
                            public_id=plan.public_id,
                            latest_version=1,
                            latest_content_sha256=detail.content_sha256,
                        )
                    )
                review_record = {
                    "plan_sha256": digest,
                    "sources": [s.model_dump(mode="json") for s in plan.sources],
                }
                review_record["review_sha256"] = canonical_hash(review_record)
                conn.execute(
                    insert(rows).values(
                        slug=plan.slug,
                        version=plan.version,
                        public_id=plan.public_id,
                        payload=detail.model_dump(mode="json"),
                        content_sha256=detail.content_sha256,
                        plan_sha256=digest,
                        review_record=review_record,
                        published_at=detail.published_at,
                    )
                )
                if plan.version != 1:
                    result = conn.execute(
                        update(heads)
                        .where(
                            heads.c.slug == plan.slug,
                            heads.c.public_id == plan.public_id,
                            heads.c.latest_version == plan.version - 1,
                        )
                        .values(
                            latest_version=plan.version, latest_content_sha256=detail.content_sha256
                        )
                    )
                    if result.rowcount != 1:
                        raise StorageConflict("Public latest publication conflict")
                return detail
        except SQLAlchemyError as error:
            if getattr(getattr(error, "orig", None), "sqlstate", None) == "23505":
                raise StorageConflict("Public publication identity conflict") from None
            raise StorageError("Unable to publish public briefing") from None

    def withdraw(self, plan: PublicBriefingPlan, *, reviewed_sha256: str) -> None:
        plan = revalidate_plan(plan)
        digest = plan_hash(plan)
        if reviewed_sha256 != digest:
            raise ValueError("Exact reviewed publication hash required")
        try:
            with (
                self.engine.connect().execution_options(isolation_level="READ COMMITTED") as conn,
                conn.begin(),
            ):
                self._lock(conn, plan.slug)
                head = self._head(conn, plan.slug)
                row = (
                    conn.execute(
                        select(rows).where(rows.c.slug == plan.slug, rows.c.version == plan.version)
                    )
                    .mappings()
                    .one_or_none()
                )
                if head is None or row is None:
                    raise StorageConflict("Public withdrawal version conflict")
                self._row(row, head)
                if row["plan_sha256"] != digest:
                    raise StorageConflict("Public withdrawal review conflict")
                if row["withdrawn_at"] is None:
                    conn.execute(
                        update(rows)
                        .where(
                            rows.c.slug == plan.slug,
                            rows.c.version == plan.version,
                            rows.c.content_sha256 == row["content_sha256"],
                            rows.c.withdrawn_at.is_(None),
                        )
                        .values(withdrawn_at=datetime.now(UTC))
                    )
        except SQLAlchemyError:
            raise StorageError("Unable to withdraw public briefing") from None

    def load(self, slug: str, version: int | None = None) -> PublicBriefingDetail | None:
        TypeAdapter(Slug).validate_python(slug)
        if version is not None:
            TypeAdapter(SafePositive).validate_python(version)
        try:
            with (
                self.engine.connect().execution_options(
                    isolation_level="REPEATABLE READ", postgresql_readonly=True
                ) as conn,
                conn.begin(),
            ):
                head = self._head(conn, slug)
                if head is None:
                    return None
                row = (
                    conn.execute(
                        select(rows).where(
                            rows.c.slug == slug,
                            rows.c.version == (version or head["latest_version"]),
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if row is None:
                    return None
                detail = self._row(row, head)
                return detail if row["withdrawn_at"] is None else None
        except SQLAlchemyError:
            raise StorageError("Unable to read public briefing") from None

    def list_latest(self) -> PublicBriefingList:
        try:
            with (
                self.engine.connect().execution_options(
                    isolation_level="REPEATABLE READ", postgresql_readonly=True
                ) as conn,
                conn.begin(),
            ):
                # Limit only after selecting the explicit latest row, never older live rows.
                selected = conn.execute(
                    select(rows)
                    .join(
                        heads,
                        (rows.c.slug == heads.c.slug) & (rows.c.version == heads.c.latest_version),
                    )
                    .where(rows.c.withdrawn_at.is_(None))
                    .order_by(rows.c.published_at.desc(), rows.c.slug)
                    .limit(20)
                ).mappings()
                summaries = []
                for row in selected:
                    head = self._head(conn, row["slug"])
                    if head is None:
                        raise StorageCorruption("Public latest reference missing")
                    detail = self._row(row, head)
                    summaries.append(
                        PublicBriefingSummary.model_validate(
                            detail.model_dump(include=set(PublicBriefingSummary.model_fields))
                        )
                    )
                return PublicBriefingList(items=tuple(summaries))
        except (ValidationError, TypeError, ValueError):
            raise StorageCorruption("Public publication integrity check failed") from None
        except SQLAlchemyError:
            raise StorageError("Unable to list public briefings") from None
