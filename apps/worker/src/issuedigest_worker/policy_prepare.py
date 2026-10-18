"""Offline capture + approved job → append-only existing plan and verified presentation."""

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from issuedigest_connectors import parse_policy_capture, policy_url
from issuedigest_domain import (
    Citation,
    DocumentVersion,
    EvidenceBundle,
    SourceDocument,
    SourcePresentation,
    validate_citation,
)
from issuedigest_ingestion import (
    extract_policy_html,
    locate_policy_html_quote,
    to_policy_html_representation,
)
from issuedigest_storage.provisioning import (
    ProvisioningPlan,
    ProvisioningSnapshot,
    parse_plan,
    validate_plan,
)
from pydantic import UUID4, AnyHttpUrl, TypeAdapter

from .bounds import preflight_model
from .models import PreparationError
from .policy_job import PolicyJob, parse_policy_job
from .prepare import _aliases


@dataclass(frozen=True, repr=False)
class PreparedPolicy:
    plan: ProvisioningPlan
    presentations: tuple[SourcePresentation, ...]


@dataclass(frozen=True, repr=False)
class PreparedPolicyCandidates:
    snapshots: tuple[ProvisioningSnapshot, ...]
    presentations: tuple[SourcePresentation, ...]


def prepare_policy_candidates(
    job: PolicyJob, capture_raw: bytes, workspace_id: UUID
) -> PreparedPolicyCandidates:
    """Recheck exact approved artifact and quotes without base plans, IO or ID allocation."""
    try:
        if type(job) is not PolicyJob or type(capture_raw) is not bytes:
            raise ValueError("Invalid preparation input")
        workspace_id = TypeAdapter(UUID4).validate_python(workspace_id, strict=True)
        preflight_model(job)
        job = parse_policy_job(job.model_dump_json(warnings="error"))
        capture = parse_policy_capture(capture_raw)
        if (
            sha256(capture_raw).hexdigest() != job.capture_sha256
            or capture.collected_at != job.collected_at
            or {a.news_id for a in capture.articles} != {s.news_id for s in job.sources}
        ):
            raise ValueError("Capture does not match approved job")
        snapshots: list[ProvisioningSnapshot] = []
        articles = {a.news_id: a for a in capture.articles}
        presentations: list[SourcePresentation] = []
        for source in job.sources:
            article = articles[source.news_id]
            extraction = extract_policy_html(
                article.html.encode("utf-8"),
                expected_sha256=source.article_sha256,
                canonical_url=policy_url(source.news_id),
            )
            if extraction.text_sha256 != source.text_sha256:
                raise ValueError("Body does not match approved job")
            representation = to_policy_html_representation(
                extraction,
                representation_id=source.representation_id,
                document_version_id=source.version_id,
            )
            citations: list[Citation] = []
            for request in source.citations:
                citation = Citation(
                    citation_id=request.citation_id,
                    document_version_id=source.version_id,
                    representation_id=source.representation_id,
                    selector=locate_policy_html_quote(
                        representation, quote=request.quote, start=request.start
                    ),
                )
                validate_citation(citation, representation)
                citations.append(citation)
            snapshot = ProvisioningSnapshot(
                snapshot_id=source.snapshot_id,
                bundle=EvidenceBundle(
                    document=SourceDocument(
                        document_id=source.document_id,
                        workspace_id=workspace_id,
                        provider="korea_policy",
                        source_id=source.news_id,
                        source_kind="government_document",
                        canonical_url=AnyHttpUrl(article.canonical_url),
                    ),
                    version=DocumentVersion(
                        version_id=source.version_id,
                        document_id=source.document_id,
                        raw_object_id=source.raw_object_id,
                        raw_sha256=job.capture_sha256,
                        media_type="application/vnd.issuedigest.policy-capture+json",
                        collected_at=job.collected_at,
                    ),
                    representation=representation,
                    citations=tuple(citations),
                ),
            )
            snapshots.append(snapshot)
            # Title comes solely from this article's parsed metadata, never list/lead/job.
            presentations.append(
                SourcePresentation(
                    snapshot_id=source.snapshot_id,
                    workspace_id=workspace_id,
                    title=extraction.title,
                    profile="policy-html-v1",
                )
            )
        _aliases(tuple(snapshots))
        return PreparedPolicyCandidates(tuple(snapshots), tuple(presentations))
    except Exception:
        raise PreparationError("Unable to prepare policy candidates") from None


def prepare_policy_plan(
    job: PolicyJob, capture_raw: bytes, base: ProvisioningPlan
) -> PreparedPolicy:
    """Retain exact artifact hash/time, validate approved quotes/rights, never register or index."""
    try:
        if (
            type(job) is not PolicyJob
            or type(base) is not ProvisioningPlan
            or type(capture_raw) is not bytes
        ):
            raise ValueError("Invalid preparation input")
        # Bound both graphs before serializing any caller-created construct/copy values.
        preflight_model(job)
        preflight_model(base)
        job = parse_policy_job(job.model_dump_json(warnings="error"))
        base = parse_plan(base.model_dump_json(warnings="error"))
        _aliases(base.snapshots)
        candidates = prepare_policy_candidates(job, capture_raw, base.workspace_id)
        snapshots = list(base.snapshots)
        by_snapshot = {s.snapshot_id: s for s in snapshots}
        for snapshot in candidates.snapshots:
            previous = by_snapshot.get(snapshot.snapshot_id)
            if previous is not None and previous != snapshot:
                raise ValueError("Conflicting snapshot")
            if previous is None:
                snapshots.append(snapshot)
                by_snapshot[snapshot.snapshot_id] = snapshot
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
        return PreparedPolicy(plan=result, presentations=candidates.presentations)
    except Exception:
        raise PreparationError("Unable to prepare policy plan") from None
