"""Atomic immutable evidence snapshots and their initial outbox event."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import TYPE_CHECKING, Any
from uuid import UUID

from issuedigest_domain import EvidenceBundle
from pydantic import BaseModel, ValidationError
from sqlalchemy import Connection, Engine, Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from . import schema
from .engine import verify_engine

if TYPE_CHECKING:
    from .search import RebuildProjectionResult


class StorageError(RuntimeError):
    """Sanitized DB failure; a lost commit response can leave save outcome unknown."""


class StorageConflict(StorageError):
    """An immutable ID or source identity was submitted with different content."""


class StorageCorruption(StorageError):
    """Stored evidence, integrity hash, or relational references are inconsistent."""


def _canonical_json(value: Any) -> Any:
    """Match JSONB's numeric zero sign without changing strings or other values."""
    if isinstance(value, dict):
        return {key: _canonical_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonical_json(item) for item in value]
    if isinstance(value, float) and value == 0.0:
        return 0.0
    return value


def _digest(payload: object) -> str:
    return sha256(
        json.dumps(
            _canonical_json(payload),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _payload(model: BaseModel) -> dict[str, Any]:
    result: dict[str, Any] = _canonical_json(json.loads(model.model_dump_json()))
    return result


def _uuid4(value: UUID) -> None:
    if not isinstance(value, UUID) or value.version != 4:
        raise ValueError("A UUID v4 is required")


def _check_row(row: Mapping[Any, Any], expected: Mapping[str, Any]) -> None:
    if row["content_sha256"] != _digest(row["payload"]):
        raise StorageCorruption("Stored evidence integrity check failed")
    if any(row[key] != value for key, value in expected.items()):
        raise StorageCorruption("Stored evidence references or content are inconsistent")


def _values(bundle: EvidenceBundle) -> list[tuple[Table, str, dict[str, Any]]]:
    workspace = bundle.document.workspace_id
    document = bundle.document.document_id
    version = bundle.version.version_id
    representation = bundle.representation.representation_id
    chain = {
        "workspace_id": workspace,
        "document_id": document,
        "version_id": version,
        "representation_id": representation,
    }
    records: list[tuple[Table, str, dict[str, Any]]] = [
        (
            schema.source_documents,
            "document_id",
            {
                "workspace_id": workspace,
                "document_id": document,
                "provider": bundle.document.provider,
                "source_id": bundle.document.source_id,
                "payload": _payload(bundle.document),
            },
        ),
        (
            schema.document_versions,
            "version_id",
            {
                "workspace_id": workspace,
                "document_id": document,
                "version_id": version,
                "payload": _payload(bundle.version),
            },
        ),
        (
            schema.parsed_representations,
            "representation_id",
            {
                **chain,
                "payload": _payload(bundle.representation),
            },
        ),
    ]
    # Stable lock order prevents opposite citation tuple orders from deadlocking.
    records.extend(
        (
            schema.citations,
            "citation_id",
            {
                **chain,
                "citation_id": citation.citation_id,
                "payload": _payload(citation),
            },
        )
        for citation in sorted(bundle.citations, key=lambda citation: citation.citation_id)
    )
    for _, _, values in records:
        values["content_sha256"] = _digest(values["payload"])
    return records


def _validate_bundle(bundle: EvidenceBundle) -> EvidenceBundle:
    try:
        validated = EvidenceBundle.model_validate_json(bundle.model_dump_json(warnings=False))
    except (ValidationError, ValueError, TypeError, AttributeError):
        raise ValueError("Invalid evidence bundle") from None
    return validated


class EvidenceRepository:
    """Internal persistence; workspace filtering does not establish authorization."""

    def __init__(self, engine: Engine):
        verify_engine(engine)
        self._engine = engine

    @staticmethod
    def _ensure(
        connection: Connection, table: Table, identity: str, values: dict[str, Any]
    ) -> bool:
        inserted = connection.execute(
            insert(table).values(**values).on_conflict_do_nothing().returning(table.c[identity])
        ).scalar_one_or_none()
        row = connection.execute(select(table).where(table.c[identity] == values[identity]))
        stored = row.mappings().one_or_none()
        if stored is None:
            raise StorageConflict("Source identity already belongs to another document")
        if stored["content_sha256"] != _digest(stored["payload"]):
            raise StorageCorruption("Stored evidence integrity check failed")
        if any(stored[key] != value for key, value in values.items()):
            raise StorageConflict("Immutable evidence ID already has different content")
        return inserted is not None

    @staticmethod
    def _save(connection: Connection, snapshot_id: UUID, bundle: EvidenceBundle) -> bool:
        """Validate and save on a caller-owned READ COMMITTED transaction.

        The caller owns connection, commit, rollback and DB-error sanitization.
        """
        _uuid4(snapshot_id)
        validated = _validate_bundle(bundle)
        records = _values(validated)
        chain = {
            "workspace_id": validated.document.workspace_id,
            "document_id": validated.document.document_id,
            "version_id": validated.version.version_id,
            "representation_id": validated.representation.representation_id,
        }
        payload = _payload(validated)
        for table, identity, values in records:
            EvidenceRepository._ensure(connection, table, identity, values)
        created = EvidenceRepository._ensure(
            connection,
            schema.evidence_snapshots,
            "snapshot_id",
            {
                **chain,
                "snapshot_id": snapshot_id,
                "schema_version": validated.schema_version,
                "payload": payload,
                "content_sha256": _digest(payload),
            },
        )
        if not created:
            # A retry must not silently accept damaged stored snapshot relationships.
            EvidenceRepository._load(connection, chain["workspace_id"], snapshot_id)
            return False
        if validated.citations:
            connection.execute(
                insert(schema.snapshot_citations),
                [
                    {
                        **chain,
                        "snapshot_id": snapshot_id,
                        "ordinal": ordinal,
                        "citation_id": citation.citation_id,
                    }
                    for ordinal, citation in enumerate(validated.citations)
                ],
            )
        references = {
            key: str(value) for key, value in {**chain, "snapshot_id": snapshot_id}.items()
        }
        connection.execute(
            insert(schema.outbox).values(
                **chain,
                snapshot_id=snapshot_id,
                event_id=snapshot_id,
                event_type="evidence.snapshot_saved.v1",
                payload=references,
            )
        )
        return True

    def save(self, snapshot_id: UUID, bundle: EvidenceBundle) -> bool:
        """Return True for a new snapshot, False for an identical normalized retry."""
        _uuid4(snapshot_id)
        validated = _validate_bundle(bundle)
        try:
            with self._engine.connect().execution_options(
                isolation_level="READ COMMITTED"
            ) as connection:
                with connection.begin():
                    return self._save(connection, snapshot_id, validated)
        except SQLAlchemyError:
            raise StorageError(
                "Evidence snapshot save could not be confirmed; check or retry the same snapshot ID"
            ) from None

    @staticmethod
    def _load(
        connection: Connection, workspace_id: UUID, snapshot_id: UUID
    ) -> EvidenceBundle | None:
        snapshot = (
            connection.execute(
                select(schema.evidence_snapshots).where(
                    schema.evidence_snapshots.c.workspace_id == workspace_id,
                    schema.evidence_snapshots.c.snapshot_id == snapshot_id,
                )
            )
            .mappings()
            .one_or_none()
        )
        if snapshot is None:
            return None
        try:
            bundle = EvidenceBundle.model_validate_json(json.dumps(snapshot["payload"]))
            chain = {
                "workspace_id": bundle.document.workspace_id,
                "document_id": bundle.document.document_id,
                "version_id": bundle.version.version_id,
                "representation_id": bundle.representation.representation_id,
            }
            _check_row(
                snapshot,
                {
                    **chain,
                    "snapshot_id": snapshot_id,
                    "schema_version": bundle.schema_version,
                    "payload": _payload(bundle),
                },
            )
            if bundle.document.workspace_id != workspace_id:
                raise StorageCorruption("Stored snapshot workspace is inconsistent")
            for table, identity, values in _values(bundle):
                row = (
                    connection.execute(
                        select(table).where(
                            table.c[identity] == values[identity],
                            table.c.workspace_id == workspace_id,
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if row is None:
                    raise StorageCorruption("Stored evidence object is missing")
                _check_row(row, values)
            links = (
                connection.execute(
                    select(schema.snapshot_citations)
                    .where(
                        schema.snapshot_citations.c.snapshot_id == snapshot_id,
                    )
                    .order_by(schema.snapshot_citations.c.ordinal)
                )
                .mappings()
                .all()
            )
            expected_links = [
                {
                    **chain,
                    "snapshot_id": snapshot_id,
                    "ordinal": ordinal,
                    "citation_id": citation.citation_id,
                }
                for ordinal, citation in enumerate(bundle.citations)
            ]
            if [dict(link) for link in links] != expected_links:
                raise StorageCorruption("Stored snapshot citation references are inconsistent")
            return bundle
        except (ValidationError, ValueError, TypeError, KeyError, UnicodeError):
            raise StorageCorruption("Stored evidence validation failed") from None

    def load(self, workspace_id: UUID, snapshot_id: UUID) -> EvidenceBundle | None:
        """Read and revalidate a snapshot and every normalized object/reference."""
        _uuid4(workspace_id)
        _uuid4(snapshot_id)
        try:
            with self._engine.connect().execution_options(
                isolation_level="REPEATABLE READ"
            ) as conn:
                with conn.begin():
                    return self._load(conn, workspace_id, snapshot_id)
        except SQLAlchemyError:
            raise StorageError("Unable to load evidence snapshot") from None

    def rebuild_projection(
        self, workspace_id: UUID, snapshot_id: UUID
    ) -> RebuildProjectionResult | None:
        """Explicitly replace disposable units atomically under a snapshot advisory lock."""
        from .search import rebuild_projection

        _uuid4(workspace_id)
        _uuid4(snapshot_id)
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    return rebuild_projection(conn, workspace_id, snapshot_id)
        except SQLAlchemyError:
            raise StorageError("Unable to rebuild evidence search projection") from None
