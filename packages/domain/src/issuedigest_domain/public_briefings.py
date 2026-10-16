"""Explicit rights-reviewed, bounded, immutable public copies; no private repository access."""

import json
import re
from datetime import date, datetime
from hashlib import sha256
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import (
    UUID4,
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from .canvas import CanvasBundle
from .contract_values import ContractModel, NonBlank, SafePositive, UtcInstant
from .research_journey import SourcePresentation
from .sources import Sha256

MAX_PLAN_BYTES = 8 * 1024 * 1024
Slug = Annotated[
    str,
    StringConstraints(
        strict=True, min_length=3, max_length=80, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$"
    ),
]
Title = Annotated[NonBlank, Field(max_length=150)]
Description = Annotated[NonBlank, Field(max_length=350)]
OfficialUrl = Annotated[str, StringConstraints(strict=True, max_length=180)]


def official_url(value: str) -> str:
    if (
        re.fullmatch(r"https://www\.korea\.kr/news/policyNewsView\.do\?newsId=[0-9]+", value)
        is None
    ):
        raise ValueError("Unsupported official source URL")
    return value


def canonical_hash(value: Any) -> str:
    return sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


class PublicSourceAttribution(ContractModel):
    document_id: UUID4
    official_url: OfficialUrl
    title: Annotated[NonBlank, Field(max_length=255)]
    publisher: Annotated[NonBlank, Field(max_length=255)]
    published_on: date
    license: Literal["kogl-type-1"]
    attribution: Annotated[NonBlank, Field(max_length=1000)]
    text_sha256: Sha256

    @field_validator("title")
    @classmethod
    def display_title(cls, value: str) -> str:
        return SourcePresentation.display_title(value)

    @field_validator("official_url")
    @classmethod
    def approved_url(cls, value: str) -> str:
        return official_url(value)

    @field_validator("published_on", mode="before")
    @classmethod
    def exact_date(cls, value: object) -> date:
        if type(value) is date:
            return value
        if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            return date.fromisoformat(value)
        raise ValueError("Exact source publication date required")


class PublicSourceReview(PublicSourceAttribution):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    checked_at: UtcInstant
    reviewer: Annotated[NonBlank, Field(max_length=255, repr=False)]
    photos_excluded: bool = Field(strict=True)
    third_party_material_excluded: bool = Field(strict=True)

    @model_validator(mode="after")
    def reviewed_rights(self) -> Self:
        if (
            not self.photos_excluded
            or not self.third_party_material_excluded
            or self.checked_at.date() < self.published_on
        ):
            raise ValueError("Individual source rights review required")
        return self


def validate_public_canvas(canvas: CanvasBundle) -> None:
    """The research v1/v2 display subset; citation matches never certify claim truth."""
    research, revision = canvas.research, canvas.revision
    if (
        not 1 <= len(research.evidence) <= 5
        or len(research.claims) > 12
        or research.entities
        or research.relations
        or research.observations
        or research.support_reviews
        or revision.draft.outcome != "answer"
        or not 2 <= len(revision.draft.modules) <= 4
        or revision.revision_number != 1
        or revision.parent_revision_id is not None
        or len({e.document.document_id for e in research.evidence}) != len(research.evidence)
        or set(revision.selected_version_ids) != {e.version.version_id for e in research.evidence}
    ):
        raise ValueError("Unsupported public Canvas scope")
    citations = {c.citation_id: c for e in research.evidence for c in e.citations}
    if len(citations) > 100 or any(len(e.citations) > 32 for e in research.evidence):
        raise ValueError("Public citation bounds exceeded")
    for claim in research.claims:
        if (
            claim.basis != "inference"
            or claim.derivation is None
            or claim.derivation.method != "pydantic-ai"
            or claim.derivation.method_version not in {"research-v1", "research-v2"}
            or len(claim.text) > 500
            or len(claim.citation_ids) > 3
            or claim.speaker_entity_id is not None
            or claim.subject_entity_ids
            or claim.raw_event_time_text is not None
            or len(claim.derivation.rationale) > 200
        ):
            raise ValueError("Unsupported public interpretation")
    referenced: set[UUID] = set()
    all_cited: set[UUID] = set()
    evidence_modules = 0
    for index, module in enumerate(revision.draft.modules):
        if (
            module.kind not in {"summary", "comparison", "timeline", "evidence"}
            or len(module.title) > 100
            or module.span != "full"
            or len(module.citation_ids) > (36 if module.kind == "evidence" else 12)
            or {a.citation_id for a in module.actions if a.kind == "open_evidence"}
            != set(module.citation_ids)
            or any(action.kind != "open_evidence" for action in module.actions)
        ):
            raise ValueError("Unsupported public module")
        if module.kind == "evidence":
            evidence_modules += 1
            if (
                index != len(revision.draft.modules) - 1
                or evidence_modules != 1
                or set(module.citation_ids) != all_cited
            ):
                raise ValueError("Public evidence module must close the exact citation union")
        else:
            all_cited.update(module.citation_ids)
            claim_ids = module.claim_ids
            if len(claim_ids) > 4 or referenced.intersection(claim_ids):
                raise ValueError("Public module claim bounds exceeded")
            referenced.update(claim_ids)
            for claim in research.claims:
                if claim.claim_id not in claim_ids:
                    continue
                if module.kind == "timeline":
                    period = claim.valid_period
                    if (
                        period is None
                        or period.start_date != period.end_date
                        or not any(
                            period.start_date.isoformat() in citations[c].selector.quote
                            for c in claim.citation_ids
                        )
                    ):
                        raise ValueError("Public timeline requires exact quoted event date")
                elif claim.valid_period is not None:
                    raise ValueError("Only public timeline claims carry event dates")
    if evidence_modules != 1 or referenced != {c.claim_id for c in research.claims}:
        raise ValueError("Public claims must be displayed")


def _sources_match(canvas: CanvasBundle, sources: tuple[PublicSourceAttribution, ...]) -> None:
    index = {s.document_id: s for s in sources}
    if len(index) != len(sources) or set(index) != {
        e.document.document_id for e in canvas.research.evidence
    }:
        raise ValueError("Source reviews must exactly match public evidence")
    for proof in canvas.research.evidence:
        source = index[proof.document.document_id]
        if (
            str(proof.document.canonical_url) != source.official_url
            or proof.representation.text_sha256 != source.text_sha256
        ):
            raise ValueError("Source review does not match exact evidence")


class PublicBriefingPlan(ContractModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    slug: Slug
    public_id: UUID4
    version: SafePositive
    title: Title
    description: Description
    as_of: UtcInstant
    canvas: CanvasBundle = Field(repr=False)
    sources: tuple[PublicSourceReview, ...] = Field(min_length=1, max_length=5, repr=False)

    @field_validator("canvas", mode="before")
    @classmethod
    def exact_original_urls(cls, value: Any) -> Any:
        # URL types normalize hosts/default ports. Check original plan input first.
        if isinstance(value, dict):
            research = value.get("research")
            if isinstance(research, dict) and isinstance(research.get("evidence"), (list, tuple)):
                for proof in research["evidence"]:
                    if isinstance(proof, dict) and isinstance(proof.get("document"), dict):
                        url = proof["document"].get("canonical_url")
                        if not isinstance(url, (str, AnyHttpUrl)):
                            raise ValueError("Exact official source URL required")
                        official_url(str(url))
        return value

    @model_validator(mode="after")
    def valid_plan(self) -> Self:
        validate_public_canvas(self.canvas)
        _sources_match(self.canvas, self.sources)
        if any(s.published_on > self.as_of.date() for s in self.sources):
            raise ValueError("Source publication must precede content baseline")
        if any(
            s.checked_at < self.as_of or s.checked_at < e.version.collected_at
            for s in self.sources
            for e in self.canvas.research.evidence
            if s.document_id == e.document.document_id
        ):
            raise ValueError("Content and collected evidence must precede review")
        if len(self.model_dump_json().encode()) > MAX_PLAN_BYTES:
            raise ValueError("Publication plan exceeds size bounds")
        return self


def _raw_model(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return {key: _raw_model(item) for key, item in value.__dict__.items()}
    if isinstance(value, dict):
        return {key: _raw_model(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(_raw_model(item) for item in value)
    return value


def revalidate_plan(plan: PublicBriefingPlan) -> PublicBriefingPlan:
    if not isinstance(plan, PublicBriefingPlan):
        raise ValueError("Validated publication plan required")
    return PublicBriefingPlan.model_validate(_raw_model(plan))


def plan_hash(plan: PublicBriefingPlan) -> str:
    return canonical_hash(revalidate_plan(plan).model_dump(mode="json"))


class PublicBriefingSummary(ContractModel):
    slug: Slug
    public_id: UUID4
    version: SafePositive
    title: Title
    description: Description
    as_of: UtcInstant
    published_at: UtcInstant
    content_sha256: Sha256

    @model_validator(mode="after")
    def valid_public_time(self) -> Self:
        if self.published_at < self.as_of:
            raise ValueError("Publication cannot precede content")
        return self


class PublicBriefingDetail(PublicBriefingSummary):
    canvas: CanvasBundle
    source_titles: dict[UUID4, str]
    sources: tuple[PublicSourceAttribution, ...] = Field(min_length=1, max_length=5)

    @field_validator("canvas", mode="before")
    @classmethod
    def exact_public_urls(cls, value: Any) -> Any:
        return PublicBriefingPlan.exact_original_urls(value)

    @model_validator(mode="after")
    def valid_public_copy(self) -> Self:
        validate_public_canvas(self.canvas)
        _sources_match(self.canvas, self.sources)
        if any(s.published_on > self.as_of.date() for s in self.sources):
            raise ValueError("Source publication must precede content baseline")
        if self.source_titles != {s.document_id: s.title for s in self.sources}:
            raise ValueError("Public source titles mismatch")
        if _remap_canvas(self.canvas, self.public_id, self.version) != self.canvas:
            raise ValueError("Invalid public identity namespace")
        if any(
            e.document.provider != "public-reviewed-copy"
            or e.document.source_id != str(e.document.document_id)
            or e.representation.parser_name != "public-reviewed-copy"
            or e.representation.parser_version != "1"
            or e.representation.normalization_profile != "public-reviewed-copy-v1"
            for e in self.canvas.research.evidence
        ):
            raise ValueError("Public copy provenance required")
        if self.content_sha256 != content_hash(self):
            raise ValueError("Public payload hash mismatch")
        if len(self.model_dump_json().encode()) > MAX_PLAN_BYTES:
            raise ValueError("Public payload exceeds bounds")
        return self


class PublicBriefingList(ContractModel):
    items: tuple[PublicBriefingSummary, ...] = Field(max_length=20)

    @model_validator(mode="after")
    def unique_slugs(self) -> Self:
        if len({item.slug for item in self.items}) != len(self.items):
            raise ValueError("Duplicate public latest entry")
        return self


def revalidate_public_detail(value: PublicBriefingDetail) -> PublicBriefingDetail:
    if not isinstance(value, PublicBriefingDetail):
        raise ValueError("Validated public detail required")
    return PublicBriefingDetail.model_validate(_raw_model(value))


def revalidate_public_list(value: PublicBriefingList) -> PublicBriefingList:
    if not isinstance(value, PublicBriefingList):
        raise ValueError("Validated public list required")
    return PublicBriefingList.model_validate(_raw_model(value))


def content_hash(detail: PublicBriefingDetail) -> str:
    return canonical_hash(detail.model_dump(mode="json", exclude={"content_sha256"}))


def _public_uuid(public_id: UUID, version: int, position: int) -> str:
    digest = sha256(f"public-briefing-v1:{public_id}:{version}:{position}".encode()).digest()
    return str(UUID(bytes=digest[:16], version=4))


def _remap_canvas(canvas: CanvasBundle, public_id: UUID, version: int) -> CanvasBundle:
    payload = canvas.model_dump(mode="json")
    mapping: dict[str, str] = {}
    identity_fields = {
        "workspace_id",
        "run_id",
        "document_id",
        "version_id",
        "raw_object_id",
        "representation_id",
        "document_version_id",
        "citation_id",
        "claim_id",
        "draft_id",
        "module_id",
        "revision_id",
        "parent_revision_id",
        "selected_version_ids",
        "citation_ids",
        "claim_ids",
    }

    def rewrite(value: Any, field: str = "") -> Any:
        if isinstance(value, dict):
            return {key: rewrite(item, key) for key, item in value.items()}
        if isinstance(value, list):
            return [rewrite(item, field) for item in value]
        if field in identity_fields and isinstance(value, str):
            if value not in mapping:
                mapping[value] = _public_uuid(public_id, version, len(mapping))
            return mapping[value]
        return value

    result = rewrite(payload)
    for evidence in result["research"]["evidence"]:
        evidence["document"].update(
            provider="public-reviewed-copy", source_id=evidence["document"]["document_id"]
        )
        evidence["representation"].update(
            parser_name="public-reviewed-copy",
            parser_version="1",
            normalization_profile="public-reviewed-copy-v1",
        )
    return CanvasBundle.model_validate_json(json.dumps(result, allow_nan=False))


def publish_copy(plan: PublicBriefingPlan, published_at: datetime) -> PublicBriefingDetail:
    plan = revalidate_plan(plan)
    if published_at < max(s.checked_at for s in plan.sources):
        raise ValueError("Publication cannot precede rights review")
    canvas = _remap_canvas(plan.canvas, plan.public_id, plan.version)
    mapping = {
        old.document.document_id: new.document.document_id
        for old, new in zip(plan.canvas.research.evidence, canvas.research.evidence, strict=True)
    }
    sources = tuple(
        PublicSourceAttribution.model_validate(
            {
                **source.model_dump(mode="json", include=set(PublicSourceAttribution.model_fields)),
                "document_id": mapping[source.document_id],
            }
        )
        for source in plan.sources
    )
    data = {
        **plan.model_dump(exclude={"canvas", "sources"}),
        "published_at": published_at,
        "canvas": canvas,
        "source_titles": {s.document_id: s.title for s in sources},
        "sources": sources,
    }
    candidate = PublicBriefingDetail.model_construct(content_sha256="0" * 64, **data)
    data["content_sha256"] = content_hash(candidate)
    return PublicBriefingDetail.model_validate(data)
