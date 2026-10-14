"""Permanent pure job boundary for later runtime orchestration; no DB calls."""

from uuid import UUID

from issuedigest_domain import Citation, EvidenceBundle, validate_citation
from issuedigest_ingestion import (
    HwpxLimits,
    extract_hwpx,
    locate_hwpx_cell,
    locate_hwpx_quote,
    to_hwpx_representation,
)
from issuedigest_storage.provisioning import (
    ProvisioningPlan,
    ProvisioningSnapshot,
    parse_plan,
    validate_plan,
)
from pydantic import BaseModel

from .files import read_private
from .models import HwpxJob, PreparationError, TextCitationRequest, parse_job


def _aliases(snapshots: tuple[ProvisioningSnapshot, ...]) -> None:
    aliases: dict[tuple[str, UUID], str] = {}
    for snapshot in snapshots:
        bundle = snapshot.bundle
        entities: tuple[tuple[str, UUID, BaseModel], ...] = (
            ("document", bundle.document.document_id, bundle.document),
            ("version", bundle.version.version_id, bundle.version),
            ("representation", bundle.representation.representation_id, bundle.representation),
            *(("citation", citation.citation_id, citation) for citation in bundle.citations),
        )
        for kind, identity, model in entities:
            content = model.model_dump_json(warnings="error")
            key = (kind, identity)
            if key in aliases and aliases[key] != content:
                raise ValueError("Conflicting reference content")
            aliases[key] = content


def prepare_hwpx_plan(job: HwpxJob, base: ProvisioningPlan) -> ProvisioningPlan:
    """Revalidate both inputs, prepare exact evidence, append without changing approvals."""
    try:
        if not isinstance(job, HwpxJob) or not isinstance(base, ProvisioningPlan):
            raise ValueError("Invalid preparation input")
        job = parse_job(job.model_dump_json(warnings="error"))
        base = parse_plan(base.model_dump_json(warnings="error"))
        _aliases(base.snapshots)
        snapshots = list(base.snapshots)
        by_snapshot = {s.snapshot_id: s for s in snapshots}
        raw_total = text_total = cell_total = 0
        limits = HwpxLimits()
        for source in job.sources:
            if source.document.workspace_id != base.workspace_id:
                raise ValueError("Invalid workspace")
            raw = read_private(
                source.raw_path, min(limits.max_raw_bytes, 32 * 1024 * 1024 - raw_total)
            )
            raw_total += len(raw)
            extraction = extract_hwpx(
                raw,
                expected_sha256=source.version.raw_sha256,
                limits=HwpxLimits(
                    max_total_bytes=max(1, 32 * 1024 * 1024 // len(job.sources)),
                    max_text_characters=max(1, 1_000_000 - text_total),
                    max_cells=max(1, 20_000 - cell_total),
                ),
            )
            text_total += len(extraction.text)
            cell_total += sum(len(t.cells) for t in extraction.tables)
            if text_total > 1_000_000 or cell_total > 20_000:
                raise ValueError("Aggregate extraction limit exceeded")
            representation = to_hwpx_representation(
                extraction,
                representation_id=source.representation_id,
                document_version_id=source.version.version_id,
            )
            citations: list[Citation] = []
            for request in source.citations:
                selector = (
                    locate_hwpx_quote(representation, quote=request.quote, start=request.start)
                    if isinstance(request, TextCitationRequest)
                    else locate_hwpx_cell(
                        representation, table_id=request.table_id, cell_id=request.cell_id
                    )
                )
                if not selector.quote.strip():
                    raise ValueError("Empty citation")
                citation = Citation(
                    citation_id=request.citation_id,
                    document_version_id=source.version.version_id,
                    representation_id=source.representation_id,
                    selector=selector,
                )
                validate_citation(citation, representation)
                citations.append(citation)
            snapshot = ProvisioningSnapshot(
                snapshot_id=source.snapshot_id,
                bundle=EvidenceBundle(
                    document=source.document,
                    version=source.version,
                    representation=representation,
                    citations=tuple(citations),
                ),
            )
            previous = by_snapshot.get(snapshot.snapshot_id)
            if previous is not None:
                if previous != snapshot:
                    raise ValueError("Conflicting snapshot")
                continue
            snapshots.append(snapshot)
            by_snapshot[snapshot.snapshot_id] = snapshot
        _aliases(tuple(snapshots))
        result = ProvisioningPlan(
            schema_version=base.schema_version,
            expected_database=base.expected_database,
            workspace_id=base.workspace_id,
            invites=base.invites,
            snapshots=tuple(snapshots),
        )
        result = parse_plan(result.model_dump_json(warnings="error"))
        validate_plan(result)
        return result
    except Exception:
        raise PreparationError("Unable to prepare HWPX plan") from None
