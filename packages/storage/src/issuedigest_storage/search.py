"""Explicit projection rebuild and bounded canonical-checked literal search."""

from collections.abc import Mapping
from hashlib import sha256
from typing import Any, Literal
from uuid import UUID

from issuedigest_domain import (
    EvidenceBundle,
    EvidenceSearchHit,
    EvidenceSearchQuery,
    EvidenceSearchResult,
    SearchCoverage,
    SearchProjection,
    SearchUnit,
    build_search_projection,
    literal_matches,
    literal_ngrams,
)
from pydantic import UUID4, BaseModel, ConfigDict, Field
from sqlalchemy import Connection, DateTime, and_, cast, delete, func, insert, select

from .repository import EvidenceRepository, StorageCorruption, _digest, _payload
from .schema import document_versions, evidence_snapshots, source_documents
from .search_schema import projections, units


class RebuildProjectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_id: UUID4
    status: Literal["rebuilt", "unchanged"]
    profile: Literal["literal-ngrams-v1"] = "literal-ngrams-v1"
    unit_count: int = Field(strict=True, ge=0, le=6000)
    skipped_empty_cells: int = Field(strict=True, ge=0, le=20000)
    skipped_large_cells: int = Field(strict=True, ge=0, le=20000)


def _manifest(
    bundle: EvidenceBundle, snapshot_id: UUID, projection: SearchProjection
) -> dict[str, Any]:
    return dict(
        snapshot_id=snapshot_id,
        workspace_id=bundle.document.workspace_id,
        document_id=bundle.document.document_id,
        version_id=bundle.version.version_id,
        representation_id=bundle.representation.representation_id,
        profile=projection.profile,
        canonical_sha256=_digest(_payload(bundle)),
        projection_sha256=_digest(_payload(projection)),
        unit_count=len(projection.units),
        unit_text_characters=sum(len(u.text) for u in projection.units),
        skipped_empty_cells=projection.skipped_empty_cells,
        skipped_large_cells=projection.skipped_large_cells,
        collected_at=bundle.version.collected_at,
    )


def _unit_values(workspace_id: UUID, snapshot_id: UUID, unit: SearchUnit) -> dict[str, Any]:
    return dict(
        workspace_id=workspace_id,
        snapshot_id=snapshot_id,
        ordinal=unit.ordinal,
        selector=_payload(unit.selector),
        text=unit.text,
        text_sha256=unit.text_sha256,
        ngrams=list(unit.ngrams),
    )


def rebuild_projection(
    conn: Connection, workspace_id: UUID, snapshot_id: UUID
) -> RebuildProjectionResult | None:
    # The lock needs no UPDATE privilege on immutable source rows. Hash collisions only
    # serialize unrelated snapshots; they cannot mix their workspace-scoped contents.
    lock_key = int.from_bytes(sha256(snapshot_id.bytes).digest()[:8], "big", signed=True)
    conn.execute(select(func.pg_advisory_xact_lock(lock_key)))
    snapshot = conn.execute(
        select(evidence_snapshots.c.snapshot_id).where(
            evidence_snapshots.c.workspace_id == workspace_id,
            evidence_snapshots.c.snapshot_id == snapshot_id,
        )
    ).scalar_one_or_none()
    if snapshot is None:
        return None
    bundle = EvidenceRepository._load(conn, workspace_id, snapshot_id)
    if bundle is None:
        raise StorageCorruption("Stored search evidence is inconsistent")
    projection = build_search_projection(bundle)
    manifest = _manifest(bundle, snapshot_id, projection)
    expected_units = [_unit_values(workspace_id, snapshot_id, u) for u in projection.units]
    stored = (
        conn.execute(
            select(projections).where(
                projections.c.workspace_id == workspace_id, projections.c.snapshot_id == snapshot_id
            )
        )
        .mappings()
        .one_or_none()
    )
    stored_units = (
        conn.execute(
            select(units)
            .where(units.c.workspace_id == workspace_id, units.c.snapshot_id == snapshot_id)
            .order_by(units.c.ordinal)
        )
        .mappings()
        .all()
    )
    unchanged = (
        stored is not None
        and dict(stored) == manifest
        and [dict(u) for u in stored_units] == expected_units
    )
    if not unchanged:
        conn.execute(
            delete(projections).where(
                projections.c.workspace_id == workspace_id, projections.c.snapshot_id == snapshot_id
            )
        )
        conn.execute(insert(projections).values(**manifest))
        if expected_units:
            conn.execute(insert(units), expected_units)
    return RebuildProjectionResult(
        snapshot_id=snapshot_id,
        status="unchanged" if unchanged else "rebuilt",
        unit_count=len(projection.units),
        skipped_empty_cells=projection.skipped_empty_cells,
        skipped_large_cells=projection.skipped_large_cells,
    )


def _scope(workspace_id: UUID, query: EvidenceSearchQuery) -> tuple[Any, list[Any]]:
    source = source_documents
    versions = document_versions
    snapshots = evidence_snapshots
    join = snapshots.join(
        source,
        and_(
            source.c.workspace_id == snapshots.c.workspace_id,
            source.c.document_id == snapshots.c.document_id,
        ),
    ).join(
        versions,
        and_(
            versions.c.workspace_id == snapshots.c.workspace_id,
            versions.c.document_id == snapshots.c.document_id,
            versions.c.version_id == snapshots.c.version_id,
        ),
    )
    predicates = [
        snapshots.c.workspace_id == workspace_id,
        source.c.workspace_id == workspace_id,
        versions.c.workspace_id == workspace_id,
    ]
    if query.provider is not None:
        predicates.append(source.c.provider == query.provider)
    if query.source_id is not None:
        predicates.append(source.c.source_id == query.source_id)
    if query.source_kind is not None:
        predicates.append(source.c.payload["source_kind"].astext == query.source_kind)
    collected = cast(versions.c.payload["collected_at"].astext, DateTime(timezone=True))
    if query.collected_from is not None:
        predicates.append(collected >= query.collected_from)
    if query.collected_to is not None:
        predicates.append(collected < query.collected_to)
    return join, predicates


def _check_manifest(
    row: Mapping[Any, Any], bundle: EvidenceBundle, snapshot_id: UUID, projection: SearchProjection
) -> None:
    if dict(row) != _manifest(bundle, snapshot_id, projection):
        raise StorageCorruption("Stored search projection is inconsistent")


def search_evidence(
    conn: Connection, workspace_id: UUID, query: EvidenceSearchQuery
) -> EvidenceSearchResult:
    scoped, predicates = _scope(workspace_id, query)
    covered = scoped.outerjoin(
        projections,
        and_(
            projections.c.workspace_id == workspace_id,
            projections.c.snapshot_id == evidence_snapshots.c.snapshot_id,
        ),
    )
    coverage_row = conn.execute(
        select(
            func.count().label("total"),
            func.count(projections.c.snapshot_id).label("indexed"),
            func.coalesce(func.sum(projections.c.skipped_empty_cells), 0).label("empty"),
            func.coalesce(func.sum(projections.c.skipped_large_cells), 0).label("large"),
        )
        .select_from(covered)
        .where(*predicates)
    ).one()
    coverage = SearchCoverage(
        total_snapshots=coverage_row.total,
        indexed_snapshots=coverage_row.indexed,
        missing_snapshots=coverage_row.total - coverage_row.indexed,
        skipped_empty_cells=coverage_row.empty,
        skipped_large_cells=coverage_row.large,
    )
    required = sorted({gram for term in query.terms for gram in literal_ngrams(term)})
    joined = covered.join(
        units,
        and_(
            units.c.workspace_id == workspace_id,
            units.c.snapshot_id == evidence_snapshots.c.snapshot_id,
        ),
    )
    collected = cast(document_versions.c.payload["collected_at"].astext, DateTime(timezone=True))
    # PostgreSQL text cannot contain NUL; no saved unit can match such a literal term.
    rows = (
        []
        if any("\x00" in term for term in query.terms)
        else conn.execute(
            select(units)
            .select_from(joined)
            .where(*predicates, units.c.ngrams.contains(required))
            .order_by(collected.desc(), evidence_snapshots.c.snapshot_id, units.c.ordinal)
            .limit(201)
        )
        .mappings()
        .all()
    )
    hits: list[EvidenceSearchHit] = []
    current: tuple[UUID, EvidenceBundle, SearchProjection] | None = None
    bundle: EvidenceBundle | None = None
    projection: SearchProjection | None = None
    match_count = 0
    for row in rows[:200]:
        snapshot_id = row["snapshot_id"]
        if current is None or current[0] != snapshot_id:
            # SQL ordering keeps snapshot groups contiguous. Release the previous full
            # bundle/projection before loading another; retained hits own only selectors.
            current = None
            bundle = None
            projection = None
            bundle = EvidenceRepository._load(conn, workspace_id, snapshot_id)
            if bundle is None:
                raise StorageCorruption("Stored search evidence is inconsistent")
            try:
                projection = build_search_projection(bundle)
            except ValueError:
                raise StorageCorruption("Stored search projection is inconsistent") from None
            manifest = (
                conn.execute(
                    select(projections).where(
                        projections.c.workspace_id == workspace_id,
                        projections.c.snapshot_id == snapshot_id,
                    )
                )
                .mappings()
                .one_or_none()
            )
            if manifest is None:
                raise StorageCorruption("Stored search projection is inconsistent")
            _check_manifest(manifest, bundle, snapshot_id, projection)
            current = (snapshot_id, bundle, projection)
        _, bundle, projection = current
        ordinal = row["ordinal"]
        if not 0 <= ordinal < len(projection.units) or dict(row) != _unit_values(
            workspace_id, snapshot_id, projection.units[ordinal]
        ):
            raise StorageCorruption("Stored search unit is inconsistent")
        if not literal_matches(query, row["text"]):
            continue
        match_count += 1
        if len(hits) < query.limit:
            hits.append(
                EvidenceSearchHit(
                    workspace_id=workspace_id,
                    snapshot_id=snapshot_id,
                    document_id=bundle.document.document_id,
                    version_id=bundle.version.version_id,
                    representation_id=bundle.representation.representation_id,
                    provider=bundle.document.provider,
                    source_id=bundle.document.source_id,
                    source_kind=bundle.document.source_kind,
                    canonical_url=bundle.document.canonical_url,
                    collected_at=bundle.version.collected_at,
                    unit_ordinal=ordinal,
                    selector=projection.units[ordinal].selector,
                    matched_terms=query.terms,
                )
            )
    return EvidenceSearchResult(
        workspace_id=workspace_id,
        query=query,
        hits=tuple(hits),
        coverage=coverage,
        scanned_candidates=min(len(rows), 200),
        truncated=len(rows) > 200 or match_count > query.limit,
    )
