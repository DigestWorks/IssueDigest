"""Pure Assembly capture + operator job to the existing private provisioning contract."""

import re
from hashlib import sha256

from issuedigest_connectors import canonical_url, extract_assembly_summary, parse_capture
from issuedigest_connectors.html import detail_fields, normalize_text, visible_text
from issuedigest_domain import (
    Citation,
    DocumentVersion,
    EvidenceBundle,
    ParsedRepresentation,
    SourceDocument,
    TextQuoteSelector,
    validate_citation,
)
from issuedigest_storage.provisioning import (
    ProvisioningPlan,
    ProvisioningSnapshot,
    parse_plan,
    validate_plan,
)
from pydantic import AnyHttpUrl

from .assembly_models import AssemblyJob, parse_assembly_job
from .bounds import preflight_model
from .models import PreparationError
from .prepare import _aliases


def prepare_assembly_plan(
    job: AssemblyJob, capture_raw: bytes, base: ProvisioningPlan
) -> ProvisioningPlan:
    """Hash exact input JSON bytes, preserve approved base, never connect or invent IDs."""
    try:
        if (
            type(job) is not AssemblyJob
            or type(base) is not ProvisioningPlan
            or type(capture_raw) is not bytes
        ):
            raise ValueError("Invalid preparation input")
        preflight_model(job)
        preflight_model(base)
        job = parse_assembly_job(job.model_dump_json(warnings="error"))
        base = parse_plan(base.model_dump_json(warnings="error"))
        capture = parse_capture(capture_raw)
        if capture.bill_id != job.bill_id or capture.collected_at != job.collected_at:
            raise ValueError("Capture does not match approved job")
        fields, _, detail_display = detail_fields(capture.detail_html, job.bill_id)
        display = detail_display + "\n" + visible_text(capture.summary_html)
        if (
            normalize_text(job.title) not in display
            or re.search(r"(?<![0-9])" + re.escape(job.bill_number) + r"(?![0-9])", display) is None
            or ("billNo" in fields and fields["billNo"] != job.bill_number)
        ):
            raise ValueError("Operator metadata not found in capture")
        text = extract_assembly_summary(capture.summary_html)
        representation = ParsedRepresentation(
            representation_id=job.representation_id,
            document_version_id=job.version_id,
            parser_name="assembly-prntSummary-htmlparser",
            parser_version="1",
            normalization_profile="assembly-summary-visible-blocks-v1",
            text=text,
            text_sha256=sha256(text.encode("utf-8")).hexdigest(),
            pages=(),
            tables=(),
        )
        citation = Citation(
            citation_id=job.citation_id,
            document_version_id=job.version_id,
            representation_id=job.representation_id,
            selector=TextQuoteSelector(start=0, end=len(text), quote=text, prefix="", suffix=""),
        )
        validate_citation(citation, representation)
        snapshot = ProvisioningSnapshot(
            snapshot_id=job.snapshot_id,
            bundle=EvidenceBundle(
                document=SourceDocument(
                    document_id=job.document_id,
                    workspace_id=base.workspace_id,
                    provider="assembly",
                    source_id=job.bill_id,
                    source_kind="bill",
                    canonical_url=AnyHttpUrl(canonical_url(job.bill_id)),
                ),
                version=DocumentVersion(
                    version_id=job.version_id,
                    document_id=job.document_id,
                    raw_object_id=job.raw_object_id,
                    raw_sha256=sha256(capture_raw).hexdigest(),
                    media_type="application/vnd.issuedigest.assembly-capture+json",
                    collected_at=job.collected_at,
                ),
                representation=representation,
                citations=(citation,),
            ),
        )
        snapshots = list(base.snapshots)
        previous = next((s for s in snapshots if s.snapshot_id == snapshot.snapshot_id), None)
        if previous is not None and previous != snapshot:
            raise ValueError("Conflicting snapshot")
        if previous is None:
            snapshots.append(snapshot)
        result = ProvisioningPlan(
            schema_version=base.schema_version,
            expected_database=base.expected_database,
            workspace_id=base.workspace_id,
            invites=base.invites,
            snapshots=tuple(snapshots),
        )
        preflight_model(result)
        _aliases(result.snapshots)
        result = parse_plan(result.model_dump_json(warnings="error"))
        validate_plan(result)
        return result
    except Exception:
        raise PreparationError("Unable to prepare Assembly plan") from None
