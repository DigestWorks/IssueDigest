"""Explicit, bounded, private reviewed policy intake. Construction performs no IO."""

from __future__ import annotations

# These envelopes validate stored provenance without importing an HTTP connector or worker.
import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Annotated, Any, Literal
from uuid import UUID

from issuedigest_domain import EvidenceBundle, SourcePresentation
from pydantic import UUID4, AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Connection, Engine, insert, select, text

from . import schema
from .operator_security import reject_json_constant, unique_json_object
from .policy_collection import (
    MAX_CAPTURE_BYTES,
    MAX_REPORT_BYTES,
    PolicyCollectionBaseline,
    PolicyCollectionConfig,
    _attempt,
    _binding,
    _config,
    _database,
    _history,
)
from .policy_collection_schema import policy_collection_attempts as attempts
from .policy_collection_schema import policy_collection_channels as channels
from .policy_intake_schema import PolicyIntakeReceipt
from .policy_intake_schema import policy_intake_receipts as receipts
from .repository import EvidenceRepository, _digest, _payload, _validate_bundle
from .research import ResearchRepository
from .research_schema import source_presentations
from .search import rebuild_projection


class PolicyIntakeError(Exception):
    def __init__(self) -> None:
        super().__init__("Policy intake unavailable")


class PolicyIntakeCommitUnknown(PolicyIntakeError):
    def __init__(self) -> None:
        Exception.__init__(self, "Policy intake commit unknown")


_Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
_News = Annotated[str, Field(pattern=r"^[0-9]{9}$")]
_FIELDS = Literal[
    "text_sha256",
    "title",
    "publisher",
    "publication_date",
    "license_notice",
    "license_url",
    "parser_name",
    "parser_version",
    "normalization_profile",
]


class _Private(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", hide_input_in_errors=True)


class PolicyIntakeEntry(_Private):
    snapshot_id: UUID4 = Field(repr=False)
    bundle: EvidenceBundle = Field(repr=False)
    presentation: SourcePresentation = Field(repr=False)
    fingerprint_sha256: _Hash = Field(repr=False)


class PolicyIntakePlan(_Private):
    collection: PolicyCollectionConfig = Field(repr=False)
    attempt_id: UUID4 = Field(repr=False)
    workspace_id: UUID4 = Field(repr=False)
    approval_sha256: _Hash = Field(repr=False)
    entries: tuple[PolicyIntakeEntry, ...] = Field(min_length=1, max_length=2, repr=False)


class PolicyIntakeResult(_Private):
    schema_version: Literal[1] = 1
    outcome: Literal["checked", "applied", "already_applied", "busy"]
    sources: int = Field(ge=0, le=2)
    new_versions: int = Field(ge=0, le=2)
    reused_versions: int = Field(ge=0, le=2)
    receipts_created: int = Field(ge=0, le=2)

    @field_validator("schema_version", mode="before")
    @classmethod
    def _version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Invalid version")
        return value


class _Article(_Private):
    news_id: _News
    canonical_url: str = Field(max_length=100)
    html: str = Field(min_length=1, max_length=8 * 1024 * 1024)


class _Capture(_Private):
    schema_version: Literal[1]
    collected_at: AwareDatetime
    articles: tuple[_Article, ...] = Field(min_length=1, max_length=2)


class _Change(_Private):
    source_id: _News
    status: Literal["new", "changed", "unchanged", "not_observed"]
    before_fingerprint: _Hash | None
    after_fingerprint: _Hash | None
    changed_fields: tuple[_FIELDS, ...]


class _Report(_Private):
    schema_version: Literal[1]
    profile: Literal["policy-change-v1"]
    before_capture_sha256: _Hash | None
    before_collected_at: AwareDatetime | None
    after_capture_sha256: _Hash
    after_collected_at: AwareDatetime
    sources: tuple[_Change, ...] = Field(min_length=1, max_length=4)


def _json_model[T: BaseModel](raw: bytes, model: type[T]) -> T:
    data = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=unique_json_object,
        parse_constant=reject_json_constant,
    )
    if type(data) is not dict or type(data.get("schema_version")) is not int:
        raise PolicyIntakeError()
    return model.model_validate_json(
        json.dumps(data, ensure_ascii=False, allow_nan=False), strict=True
    )


def _url(news: str) -> str:
    return "https://www.korea.kr/news/policyNewsView.do?newsId=" + news


def _envelopes(
    baseline: PolicyCollectionBaseline, collection: PolicyCollectionConfig
) -> tuple[_Capture, _Report]:
    capture = _json_model(baseline.capture_bytes, _Capture)
    report = _json_model(baseline.report_bytes, _Report)
    ids = [a.news_id for a in capture.articles]
    changes = [s.source_id for s in report.sources]
    if (
        set(ids) != set(collection.news_ids)
        or len(ids) != len(set(ids))
        or len(changes) != len(set(changes))
        or tuple(changes) != collection.news_ids
        or report.after_capture_sha256 != baseline.capture_sha256
        or report.after_collected_at != capture.collected_at
        or baseline.attempt.finished_at is None
        or capture.collected_at > baseline.attempt.finished_at
        or capture.collected_at < baseline.attempt.started_at
        or (report.before_capture_sha256 is None) != (report.before_collected_at is None)
        or (
            report.before_collected_at is not None
            and report.before_collected_at >= capture.collected_at
        )
    ):
        raise PolicyIntakeError()
    for article in capture.articles:
        if article.canonical_url != _url(article.news_id) or not article.html.strip():
            raise PolicyIntakeError()
    for source in report.sources:
        fields = source.changed_fields
        if (
            (report.before_capture_sha256 is None and source.status != "new")
            or (
                report.before_capture_sha256 is not None
                and source.status not in {"changed", "unchanged"}
            )
            or source.after_fingerprint is None
            or source.status == "not_observed"
            or len(fields) != len(set(fields))
            or tuple(sorted(fields)) != fields
            or (source.status == "new" and (source.before_fingerprint is not None or fields))
            or (
                source.status == "unchanged"
                and (source.before_fingerprint != source.after_fingerprint or fields)
            )
            or (
                source.status == "changed"
                and (
                    source.before_fingerprint is None
                    or source.before_fingerprint == source.after_fingerprint
                    or not fields
                )
            )
        ):
            raise PolicyIntakeError()
    return capture, report


def _bounded(value: Any, depth: int = 0) -> None:
    if depth > 24:
        raise PolicyIntakeError()
    if isinstance(value, BaseModel):
        if value.__pydantic_extra__ or set(value.__dict__) != set(type(value).model_fields):
            raise PolicyIntakeError()
        for item in value.__dict__.values():
            _bounded(item, depth + 1)
    elif isinstance(value, (tuple, list, dict)):
        if len(value) > 20000:
            raise PolicyIntakeError()
        for item in value.values() if isinstance(value, dict) else value:
            _bounded(item, depth + 1)
    elif isinstance(value, str) and len(value) > 100000:
        raise PolicyIntakeError()


def _plan(value: PolicyIntakePlan) -> PolicyIntakePlan:
    if type(value) is not PolicyIntakePlan:
        raise PolicyIntakeError()
    _bounded(value)
    raw = value.model_dump_json(warnings="error")
    if len(raw.encode("utf-8")) > 2 * 1024 * 1024:
        raise PolicyIntakeError()
    return PolicyIntakePlan.model_validate_json(raw, strict=True)


def _selectors(bundle: EvidenceBundle) -> list[dict[str, Any]]:
    return [_payload(c.selector) for c in bundle.citations]


def _parsed_content(bundle: EvidenceBundle) -> dict[str, Any]:
    payload = _payload(bundle.representation)
    payload.pop("representation_id")
    payload.pop("document_version_id")
    return payload


def _candidate(
    entry: PolicyIntakeEntry,
    plan: PolicyIntakePlan,
    baseline: PolicyCollectionBaseline,
    capture: _Capture,
    report: _Report,
) -> None:
    bundle = _validate_bundle(entry.bundle)
    doc, version, parsed = bundle.document, bundle.version, bundle.representation
    source = next((s for s in report.sources if s.source_id == doc.source_id), None)
    p = entry.presentation
    if (
        doc.workspace_id != plan.workspace_id
        or doc.provider != "korea_policy"
        or doc.source_kind != "government_document"
        or doc.source_id not in plan.collection.news_ids
        or str(doc.canonical_url) != _url(doc.source_id)
        or version.raw_sha256 != baseline.capture_sha256
        or version.collected_at != capture.collected_at
        or version.media_type != "application/vnd.issuedigest.policy-capture+json"
        or parsed.parser_name != "korea-policy-html"
        or parsed.parser_version not in {"1", "2", "3"}
        or parsed.normalization_profile != "korea-policy-paragraphs-v1"
        or len(parsed.text) > 100000
        or parsed.tables
        or parsed.pages
        or not 1 <= len(bundle.citations) <= 10
        or any(c.selector.kind != "text" or len(c.selector.quote) > 2000 for c in bundle.citations)
        or p.workspace_id != plan.workspace_id
        or p.snapshot_id != entry.snapshot_id
        or p.profile != "policy-html-v1"
        or p.bill_number is not None
        or p.proposed_on is not None
        or source is None
        or entry.fingerprint_sha256 != source.after_fingerprint
    ):
        raise PolicyIntakeError()


def _receipt_collection(
    conn: Connection, collection_id: UUID, expected_database: str
) -> PolicyCollectionConfig:
    payload = conn.scalar(
        select(channels.c.config).where(channels.c.collection_id == collection_id)
    )
    if payload is None:
        raise PolicyIntakeError()
    collection = PolicyCollectionConfig.model_validate_json(json.dumps(payload), strict=True)
    if collection.expected_database != expected_database:
        raise PolicyIntakeError()
    return collection


def validate_policy_intake_receipt(row: Mapping[Any, Any]) -> PolicyIntakeReceipt:
    """Validate structure only, without a connection or journal/canonical reads."""
    try:
        return PolicyIntakeReceipt.model_validate(dict(row), strict=True)
    except Exception:
        raise PolicyIntakeError() from None


def _stored_receipt(
    conn: Connection, row: Mapping[Any, Any], collection: PolicyCollectionConfig
) -> tuple[EvidenceBundle, SourcePresentation]:
    validate_policy_intake_receipt(row)
    # Re-read exact original journal and all canonical normalized rows on every reuse/retry.
    collection = _receipt_collection(conn, row["collection_id"], collection.expected_database)
    baseline = PolicyIntakeRepository._capture(conn, collection, row["attempt_id"])
    capture, report = _envelopes(baseline, collection)
    source = next((s for s in report.sources if s.source_id == row["news_id"]), None)
    if (
        row["collection_id"] != collection.collection_id
        or row["capture_sha256"] != baseline.capture_sha256
        or row["report_sha256"] != baseline.report_sha256
        or row["capture_collected_at"] != capture.collected_at
        or source is None
        or row["fingerprint_sha256"] != source.after_fingerprint
    ):
        raise PolicyIntakeError()
    bundle = EvidenceRepository._load(conn, row["workspace_id"], row["snapshot_id"])
    if (
        bundle is None
        or bundle.document.provider != "korea_policy"
        or bundle.document.source_id != row["news_id"]
    ):
        raise PolicyIntakeError()
    chain = dict(
        document_id=bundle.document.document_id,
        version_id=bundle.version.version_id,
        representation_id=bundle.representation.representation_id,
    )
    if any(row[k] != v for k, v in chain.items()):
        raise PolicyIntakeError()
    # The selected canonical version belongs to its original created receipt, including
    # when this receipt reused it at a later collection time.
    origin = (
        conn.execute(
            select(receipts).where(
                receipts.c.workspace_id == row["workspace_id"],
                receipts.c.snapshot_id == row["snapshot_id"],
                receipts.c.decision == "created",
            )
        )
        .mappings()
        .all()
    )
    if len(origin) != 1:
        raise PolicyIntakeError()
    original = origin[0]
    validate_policy_intake_receipt(original)
    origin_collection = _receipt_collection(
        conn, original["collection_id"], collection.expected_database
    )
    origin_baseline = PolicyIntakeRepository._capture(
        conn, origin_collection, original["attempt_id"]
    )
    origin_capture, origin_report = _envelopes(origin_baseline, origin_collection)
    if (
        bundle.version.raw_sha256 != origin_baseline.capture_sha256
        or bundle.version.collected_at != origin_capture.collected_at
        or original["capture_sha256"] != origin_baseline.capture_sha256
        or original["report_sha256"] != origin_baseline.report_sha256
        or original["fingerprint_sha256"] != row["fingerprint_sha256"]
        or original["capture_collected_at"] != origin_capture.collected_at
        or original["news_id"] != row["news_id"]
        or any(
            original[key] != row[key]
            for key in (
                "workspace_id",
                "document_id",
                "version_id",
                "representation_id",
                "snapshot_id",
            )
        )
    ):
        raise PolicyIntakeError()
    outbox = (
        conn.execute(select(schema.outbox).where(schema.outbox.c.snapshot_id == row["snapshot_id"]))
        .mappings()
        .one_or_none()
    )
    references = {**chain, "workspace_id": row["workspace_id"], "snapshot_id": row["snapshot_id"]}
    if (
        outbox is None
        or outbox["event_id"] != row["snapshot_id"]
        or outbox["event_type"] != "evidence.snapshot_saved.v1"
        or outbox["payload"] != {key: str(value) for key, value in references.items()}
        or any(outbox[key] != value for key, value in references.items())
    ):
        raise PolicyIntakeError()
    payload = conn.scalar(
        select(source_presentations.c.payload).where(
            source_presentations.c.workspace_id == row["workspace_id"],
            source_presentations.c.snapshot_id == row["snapshot_id"],
        )
    )
    if payload is None:
        raise PolicyIntakeError()
    presentation = SourcePresentation.model_validate_json(json.dumps(payload), strict=True)
    entry = PolicyIntakeEntry(
        snapshot_id=row["snapshot_id"],
        bundle=bundle,
        presentation=presentation,
        fingerprint_sha256=row["fingerprint_sha256"],
    )
    original_plan = PolicyIntakePlan(
        collection=origin_collection,
        attempt_id=original["attempt_id"],
        workspace_id=row["workspace_id"],
        approval_sha256=original["approval_sha256"],
        entries=(entry,),
    )
    _candidate(entry, original_plan, origin_baseline, origin_capture, origin_report)
    return bundle, presentation


def _fresh_ids(conn: Connection, entry: PolicyIntakeEntry) -> None:
    bundle = entry.bundle
    for table, key, value in (
        (schema.evidence_snapshots, "snapshot_id", entry.snapshot_id),
        (schema.document_versions, "version_id", bundle.version.version_id),
        (
            schema.parsed_representations,
            "representation_id",
            bundle.representation.representation_id,
        ),
        *((schema.citations, "citation_id", c.citation_id) for c in bundle.citations),
    ):
        if conn.scalar(select(table.c[key]).where(table.c[key] == value)) is not None:
            raise PolicyIntakeError()
    if (
        conn.scalar(
            select(schema.document_versions.c.version_id).where(
                schema.document_versions.c.payload["raw_object_id"].astext
                == str(bundle.version.raw_object_id)
            )
        )
        is not None
    ):
        raise PolicyIntakeError()


def _decide(
    conn: Connection, plan: PolicyIntakePlan
) -> tuple[list[tuple[PolicyIntakeEntry, dict[str, Any], bool]], bool]:
    baseline = PolicyIntakeRepository._capture(conn, plan.collection, plan.attempt_id)
    capture, report = _envelopes(baseline, plan.collection)
    if {e.bundle.document.source_id for e in plan.entries} != set(plan.collection.news_ids):
        raise PolicyIntakeError()
    # All candidates are validated, including candidates whose new IDs are not selected.
    for entry in plan.entries:
        _candidate(entry, plan, baseline, capture, report)
    for identities in (
        [e.bundle.document.source_id for e in plan.entries],
        [e.bundle.document.document_id for e in plan.entries],
        [e.snapshot_id for e in plan.entries],
        [e.bundle.version.version_id for e in plan.entries],
        [e.bundle.version.raw_object_id for e in plan.entries],
        [e.bundle.representation.representation_id for e in plan.entries],
        [c.citation_id for e in plan.entries for c in e.bundle.citations],
    ):
        if len(set(identities)) != len(identities):
            raise PolicyIntakeError()
    request_hash = _digest(plan.model_dump(mode="json"))
    existing = (
        conn.execute(
            select(receipts).where(
                receipts.c.workspace_id == plan.workspace_id,
                receipts.c.attempt_id == plan.attempt_id,
            )
        )
        .mappings()
        .all()
    )
    if existing and len(existing) != len(plan.entries):
        raise PolicyIntakeError()
    selected = []
    for entry in plan.entries:
        bundle, doc = entry.bundle, entry.bundle.document
        same = next((r for r in existing if r["news_id"] == doc.source_id), None)
        if same is not None:
            stored, presentation = _stored_receipt(conn, same, plan.collection)
            if (
                same["request_sha256"] != request_hash
                or same["approval_sha256"] != plan.approval_sha256
                or same["fingerprint_sha256"] != entry.fingerprint_sha256
                or _selectors(stored) != _selectors(bundle)
                or stored.document != doc
                or presentation.title != entry.presentation.title
                or (same["decision"] == "created" and stored != bundle)
                or _parsed_content(stored) != _parsed_content(bundle)
            ):
                raise PolicyIntakeError()
            selected.append((entry, dict(same), False))
            continue
        source_row = (
            conn.execute(
                select(schema.source_documents).where(
                    schema.source_documents.c.workspace_id == plan.workspace_id,
                    schema.source_documents.c.provider == "korea_policy",
                    schema.source_documents.c.source_id == doc.source_id,
                )
            )
            .mappings()
            .one_or_none()
        )
        if source_row is not None and (
            source_row["document_id"] != doc.document_id
            or source_row["payload"] != _payload(doc)
            or source_row["content_sha256"] != _digest(source_row["payload"])
        ):
            raise PolicyIntakeError()
        # A document UUID cannot be borrowed from any other scope/source.
        by_id = (
            conn.execute(
                select(schema.source_documents).where(
                    schema.source_documents.c.document_id == doc.document_id
                )
            )
            .mappings()
            .one_or_none()
        )
        if by_id is not None and (
            by_id["payload"] != _payload(doc)
            or by_id["content_sha256"] != _digest(by_id["payload"])
        ):
            raise PolicyIntakeError()
        last = (
            conn.execute(
                select(receipts)
                .where(
                    receipts.c.workspace_id == plan.workspace_id,
                    receipts.c.document_id == doc.document_id,
                )
                .order_by(receipts.c.capture_collected_at.desc())
                .limit(1)
            )
            .mappings()
            .one_or_none()
        )
        reuse = False
        if last is not None:
            stored, presentation = _stored_receipt(conn, last, plan.collection)
            if capture.collected_at <= last["capture_collected_at"]:
                raise PolicyIntakeError()
            reuse = last["fingerprint_sha256"] == entry.fingerprint_sha256 and _selectors(
                stored
            ) == _selectors(bundle)
            if reuse and (
                stored.document != doc
                or presentation.title != entry.presentation.title
                or stored.representation.text != bundle.representation.text
                or stored.representation.parser_name != bundle.representation.parser_name
                or stored.representation.parser_version != bundle.representation.parser_version
                or stored.representation.normalization_profile
                != bundle.representation.normalization_profile
            ):
                raise PolicyIntakeError()
        versions = (
            conn.execute(
                select(schema.document_versions).where(
                    schema.document_versions.c.workspace_id == plan.workspace_id,
                    schema.document_versions.c.document_id == doc.document_id,
                )
            )
            .mappings()
            .all()
        )
        for row in versions:
            from issuedigest_domain import DocumentVersion

            version = DocumentVersion.model_validate_json(json.dumps(row["payload"]), strict=True)
            if (
                row["content_sha256"] != _digest(row["payload"])
                or version.version_id != row["version_id"]
                or version.document_id != doc.document_id
                or capture.collected_at <= version.collected_at
            ):
                raise PolicyIntakeError()
        if not reuse:
            _fresh_ids(conn, entry)
        selected_bundle = stored if reuse else bundle
        selected_snapshot = last["snapshot_id"] if reuse and last is not None else entry.snapshot_id
        values = dict(
            workspace_id=plan.workspace_id,
            attempt_id=plan.attempt_id,
            news_id=doc.source_id,
            collection_id=plan.collection.collection_id,
            document_id=doc.document_id,
            version_id=selected_bundle.version.version_id,
            representation_id=selected_bundle.representation.representation_id,
            snapshot_id=selected_snapshot,
            capture_collected_at=capture.collected_at,
            capture_sha256=baseline.capture_sha256,
            report_sha256=baseline.report_sha256,
            request_sha256=request_hash,
            approval_sha256=plan.approval_sha256,
            fingerprint_sha256=entry.fingerprint_sha256,
            decision="reused" if reuse else "created",
        )
        selected.append((entry, values, not reuse))
    return selected, bool(existing)


def _guard(conn: Connection, collection: PolicyCollectionConfig, driver: Any, pid: int) -> None:
    if conn.closed or conn.invalidated or conn.connection.driver_connection is not driver:
        raise PolicyIntakeError()
    _database(conn, collection)
    if not conn.scalar(
        text(
            "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype='advisory' "
            "AND pid=pg_backend_pid() AND classid=104704 AND objid=3 AND objsubid=2 AND granted) "
            "AND pg_backend_pid()=:pid"
        ),
        {"pid": pid},
    ):
        raise PolicyIntakeError()


def _result(
    outcome: Literal["checked", "applied", "already_applied", "busy"],
    sources: int,
    new: int = 0,
    reused: int = 0,
    created: int = 0,
) -> PolicyIntakeResult:
    return PolicyIntakeResult(
        outcome=outcome,
        sources=sources,
        new_versions=new,
        reused_versions=reused,
        receipts_created=created,
    )


def _check(self: PolicyIntakeRepository, plan: PolicyIntakePlan) -> PolicyIntakeResult:
    try:
        plan = _plan(plan)
        self._validate(plan.collection)
        with self._engine.connect().execution_options(
            isolation_level="REPEATABLE READ", postgresql_readonly=True
        ) as conn:
            with conn.begin():
                decisions, existing = _decide(conn, plan)
                new = sum(d[2] for d in decisions)
                return _result("checked", len(decisions), new, len(decisions) - new)
    except Exception:
        raise PolicyIntakeError() from None


def _apply(self: PolicyIntakeRepository, plan: PolicyIntakePlan) -> PolicyIntakeResult:
    try:
        plan = _plan(plan)
        self._validate(plan.collection)
        with self._engine.connect().execution_options(
            isolation_level="READ COMMITTED", postgresql_readonly=False
        ) as conn:
            driver = conn.connection.driver_connection
            pid = conn.scalar(text("SELECT pg_backend_pid()"))
            _database(conn, plan.collection)
            if not conn.scalar(text("SELECT pg_try_advisory_xact_lock(104704, 3)")):
                conn.rollback()
                return _result("busy", len(plan.entries))
            _guard(conn, plan.collection, driver, pid)
            decisions, existing = _decide(conn, plan)
            _guard(conn, plan.collection, driver, pid)
            for entry, values, create in decisions:
                if not existing:
                    if create:
                        if not EvidenceRepository._save(conn, entry.snapshot_id, entry.bundle):
                            raise PolicyIntakeError()
                        ResearchRepository._upsert_presentation(conn, entry.presentation)
                    conn.execute(insert(receipts).values(**values))
                if rebuild_projection(conn, plan.workspace_id, values["snapshot_id"]) is None:
                    raise PolicyIntakeError()
            _guard(conn, plan.collection, driver, pid)
            # Revalidation immediately before commit detects concurrent scope/journal edits.
            _decide(conn, plan)
            _guard(conn, plan.collection, driver, pid)
            try:
                conn.commit()
            except Exception:
                raise PolicyIntakeCommitUnknown() from None
            new = sum(d[2] for d in decisions)
            return _result(
                "already_applied" if existing else "applied",
                len(decisions),
                new,
                len(decisions) - new,
                0 if existing else len(decisions),
            )
    except PolicyIntakeCommitUnknown:
        raise
    except Exception:
        raise PolicyIntakeError() from None


class PolicyIntakeRepository:
    def __init__(self, engine: Engine):
        self._engine = engine

    def _validate(self, collection: PolicyCollectionConfig) -> PolicyCollectionConfig:
        collection = _config(collection)
        if (
            self._engine.dialect.name != "postgresql"
            or self._engine.dialect.driver != "psycopg"
            or self._engine.url.database != collection.expected_database
        ):
            raise PolicyIntakeError()
        return collection

    @staticmethod
    def _capture(
        conn: Connection, collection: PolicyCollectionConfig, attempt_id: UUID
    ) -> PolicyCollectionBaseline:
        if type(attempt_id) is not UUID or attempt_id.version != 4:
            raise PolicyIntakeError()
        _database(conn, collection)
        if not _binding(conn, collection):
            raise PolicyIntakeError()
        _history(conn, collection, None)
        row = (
            conn.execute(
                select(attempts).where(
                    attempts.c.attempt_id == attempt_id,
                    attempts.c.collection_id == collection.collection_id,
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None or row["state"] != "succeeded":
            raise PolicyIntakeError()
        for name, limit in (("capture", MAX_CAPTURE_BYTES), ("report", MAX_REPORT_BYTES)):
            raw = row[name + "_bytes"]
            if (
                type(raw) is not bytes
                or not 1 <= len(raw) <= limit
                or sha256(raw).hexdigest() != row[name + "_sha256"]
            ):
                raise PolicyIntakeError()
        return PolicyCollectionBaseline(
            attempt=_attempt(row),
            capture_bytes=row["capture_bytes"],
            capture_sha256=row["capture_sha256"],
            report_bytes=row["report_bytes"],
            report_sha256=row["report_sha256"],
        )

    def load_capture(
        self, collection: PolicyCollectionConfig, attempt_id: UUID
    ) -> PolicyCollectionBaseline:
        try:
            collection = self._validate(collection)
            with self._engine.connect().execution_options(
                isolation_level="REPEATABLE READ", postgresql_readonly=True
            ) as conn:
                with conn.begin():
                    return self._capture(conn, collection, attempt_id)
        except Exception:
            raise PolicyIntakeError() from None

    def check(self, plan: PolicyIntakePlan) -> PolicyIntakeResult:
        return _check(self, plan)

    def apply(self, plan: PolicyIntakePlan) -> PolicyIntakeResult:
        return _apply(self, plan)
