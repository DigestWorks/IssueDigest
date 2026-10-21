"""One bounded borrowed-model diagnosis of four roles on an unchanged generation."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, Field, create_model
from pydantic_ai import Agent, ToolOutput, UsageLimits, capture_run_messages
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.settings import ModelSettings

from .compact_shared_context import _require_stored_generation_markers, _source_packet
from .contextual_anchor import ContextualAnchor
from .numeric_evidence import (
    MAX_OUTPUT_TOKENS,
    MAX_RUN_TOKENS,
    KnownUsage,
    Source,
    _json,
    _known_usage,
    _StrictModel,
)
from .numeric_selection import _captured_usage
from .numeric_selection_evaluation import _canonical_models, _read
from .research import PROVIDER_FRAMING_ALLOWANCE
from .research_v5 import _provider_schema_bytes_v5
from .research_v7 import _validate_result_usage
from .scope_audit_contract import (
    AuditedGeneration,
    ScopeAuditCheck,
    ScopeAuditError,
    ScopeAuditInput,
    ScopeAuditIssue,
    ScopeAuditProjection,
    ScopeAuditReport,
    _checked_generation,
    _projection,
    build_scope_audit_report,
    validate_scope_audit_report,
)
from .shared_measurement_context import _actual_models

PROVIDER_IDENTITY = "issuedigest_scope_role_audit_v1"
SCOPE_ROLE_AUDIT_INSTRUCTIONS = (
    "Use audit_scope_roles_v1 once to diagnose only measured_entity, target_scope, period "
    "and reporting_actor of the selected projection. Never rewrite, repair, inherit or "
    "generate values or roles. quotes contain complete ordered sentences {id,text}; "
    "concatenate without separators to reconstruct each quote, preserving whitespace. "
    "Local quote_id labels are not provenance or authorization. Candidates preserve full "
    "quantity expressions including ranges, units and qualifiers. The projection is the "
    "unchanged proposal; target scope slots r1..r4 are read-only and ordered. Check whether "
    "each proposed phrase is linked to this quantity in that role, not merely present. "
    "Look for omitted broad/subregions and explicit business years. Do not turn an "
    "operator or organizer into the measured population's affiliation; an explicitly "
    "stated affiliation may legitimately share the operator's name. Never infer roles "
    "from a title, adjacency or institution name alone. Ambiguous linkage is uncertain. "
    "Return checks exactly once for each selected candidate in projection order, at most "
    "12. Each status is no_issue_found, issues_found or uncertain. Return at most 12 "
    "issues with candidate_id, role, kind (missing/unsupported/uncertain), required nullable "
    "scope_slot and source_anchor, and support_sentence_ids. Only target_scope can have "
    "a nonnull current slot. missing requires null slot and exact nonnull evidence; "
    "unsupported must point to an existing nonnull field and an existing slot for scope. "
    "uncertain may have a null anchor. Anchors are {sentence_id,text,context_text}; exact "
    "nonblank text/context_text have 1..1000 code points. Null context_text requires a "
    "unique text occurrence in that sentence; otherwise supply a unique exact context "
    "containing text exactly once, counting overlapping matches. Never guess locations. "
    "Support selects 1..20 contiguous ordered current sentences in one quote containing "
    "the full candidate expression and any anchor. Never duplicate diagnoses. missing or "
    "unsupported requires issues_found; only uncertain issues require uncertain. With no "
    "issues use no_issue_found only if incomplete=false. Set incomplete=true when further "
    "necessary diagnoses exceed the limit; candidates without diagnoses then remain "
    "uncertain. Hard issues retain issues_found even when incomplete. This audit does not "
    "assess omissions from numeric selection or certify truth, neutrality, authorization "
    "or human approval. Return no status, hashes, usage or approval fields outside this tool."
)


def _sum_usage(generation: KnownUsage, audit: KnownUsage | None) -> KnownUsage:
    return KnownUsage(
        input_tokens=generation.input_tokens + (audit.input_tokens if audit is not None else 0),
        output_tokens=generation.output_tokens + (audit.output_tokens if audit is not None else 0),
        requests=generation.requests + (audit.requests if audit is not None else 0),
    )


class ScopeRoleAuditError(ScopeAuditError):
    """Sanitized stage accounting; unknown started audit usage never becomes zero."""

    def __init__(
        self,
        message: str,
        *,
        generation_usage: KnownUsage | None = None,
        audit_usage: KnownUsage | None = None,
        audit_may_have_started: bool = False,
    ):
        super().__init__(message)
        self.generation_usage = generation_usage
        self.audit_usage = audit_usage
        self.audit_may_have_started = audit_may_have_started
        self.combined_usage = (
            _sum_usage(generation_usage, audit_usage)
            if generation_usage is not None
            and (audit_usage is not None or not audit_may_have_started)
            else None
        )


class ScopeRoleAuditGeneration(_StrictModel):
    """Current-source report and stage receipts; never semantic approval or billing proof."""

    profile: Literal["scope-role-audit-v1"]
    report: ScopeAuditReport
    prompt_sha256: Sha256
    instructions_sha256: Sha256
    audit_usage: KnownUsage | None
    combined_usage: KnownUsage


def _audit_tools(
    generation: AuditedGeneration, projection: tuple[ScopeAuditProjection, ...]
) -> list[ToolOutput[BaseModel]]:
    candidate_id: Any = Literal[tuple(p.candidate_id for p in projection)]
    sentence_id: Any = Literal[
        tuple(s.sentence_id for s in generation.frame.candidate_index.sentences)
    ]
    slots = tuple(dict.fromkeys(s.slot for p in projection for s in p.target_scopes))
    scope_slot: Any = Literal[slots] | None if slots else type(None)
    anchor = create_model(
        "ScopeAuditAnchorV1", __base__=ContextualAnchor, sentence_id=(sentence_id, ...)
    )
    check = create_model(
        "ScopeAuditCheckV1", __base__=ScopeAuditCheck, candidate_id=(candidate_id, ...)
    )
    nullable_anchor: Any = anchor | None
    issue = create_model(
        "ScopeAuditIssueV1",
        __base__=ScopeAuditIssue,
        candidate_id=(candidate_id, ...),
        scope_slot=(scope_slot, ...),
        source_anchor=(nullable_anchor, ...),
        support_sentence_ids=(tuple[sentence_id, ...], Field(min_length=1, max_length=20)),
    )
    output = create_model(
        "ScopeAuditOutputV1",
        __base__=ScopeAuditInput,
        checks=(tuple[check, ...], Field(max_length=12)),  # type: ignore[valid-type]
        issues=(tuple[issue, ...], Field(max_length=12)),  # type: ignore[valid-type]
    )
    return [ToolOutput(output, name="audit_scope_roles_v1", strict=True)]


def _remaining(generation_usage: KnownUsage) -> tuple[int, int]:
    return (
        MAX_RUN_TOKENS - generation_usage.input_tokens - generation_usage.output_tokens,
        min(1000, MAX_OUTPUT_TOKENS - generation_usage.output_tokens),
    )


def _preflight(
    source: Source, generation: AuditedGeneration
) -> tuple[str, list[ToolOutput[BaseModel]], int, int]:
    generation = _checked_generation(source, generation)
    projection = _projection(generation)
    prompt = _json(
        {
            "profile": "scope-role-audit-v1",
            **_source_packet(generation.frame.candidate_index),
            "projection": [p.model_dump(mode="json") for p in projection],
        }
    )
    remaining, cap = _remaining(generation.usage)
    if not projection:
        return prompt, [], remaining, cap
    if cap <= 0:
        raise ValueError("No audit output budget remains")
    tools = _audit_tools(generation, projection)
    envelope = (
        len(prompt.encode("utf-8"))
        + len(SCOPE_ROLE_AUDIT_INSTRUCTIONS.encode("utf-8"))
        + max(_provider_schema_bytes_v5(tools))
        + PROVIDER_FRAMING_ALLOWANCE
        + cap
    )
    if envelope > remaining:
        raise ValueError("Audit request exceeds remaining generation budget")
    return prompt, tools, remaining, cap


def scope_role_audit_prompt(source: Source, generation: AuditedGeneration) -> str:
    """Preflight complete source/projection and actual dynamic schema without I/O."""
    known = None
    try:
        generation = _checked_generation(source, generation)
        known = generation.usage
        return _preflight(source, generation)[0]
    except Exception:
        raise ScopeRoleAuditError(
            "Invalid scope role audit input", generation_usage=known
        ) from None


def _combined_usage(
    generation: KnownUsage, audit: KnownUsage | None, *, selected: bool
) -> KnownUsage:
    if selected:
        if audit is None:
            raise ValueError("Completed audit requires known stage usage")
        remaining, cap = _remaining(generation)
        if (
            audit.requests != 1
            or cap <= 0
            or audit.output_tokens > cap
            or audit.input_tokens + audit.output_tokens > remaining
        ):
            raise ValueError("Audit stage exceeds remaining budget")
    elif audit is not None:
        raise ValueError("Empty selection must have no audit usage")
    combined = _sum_usage(generation, audit)
    if (
        combined.requests != (2 if selected else 1)
        or combined.input_tokens + combined.output_tokens > MAX_RUN_TOKENS
        or combined.output_tokens > MAX_OUTPUT_TOKENS
    ):
        raise ValueError("Invalid combined generation and audit budget")
    return combined


def validate_scope_role_audit_generation(
    source: Source, result: ScopeRoleAuditGeneration | dict[str, Any]
) -> ScopeRoleAuditGeneration:
    """Rebuild original generation, current source/schema, diagnosis, hashes and accounting."""
    generation_usage = audit_usage = None
    selected = False
    try:
        _canonical_models(result, ScopeRoleAuditGeneration)
        if isinstance(result, BaseModel):
            _actual_models(result, ScopeRoleAuditGeneration)
        if isinstance(result, dict):
            _require_stored_generation_markers(result["report"]["generation"])
        checked = _read(ScopeRoleAuditGeneration, result)
        original = _checked_generation(source, checked.report.generation)
        generation_usage = original.usage
        selected = bool(original.frame.facts)
        audit_usage = checked.audit_usage
        report = validate_scope_audit_report(source, checked.report)
        prompt, tools, _, _ = _preflight(source, original)
        if selected:
            output_type = tools[0].output
            assert isinstance(output_type, type) and issubclass(output_type, BaseModel)
            dynamic = output_type.model_validate_json(report.input.model_dump_json(), strict=True)
            if _build_output(source, original, dynamic, output_type) != report:
                raise ValueError("Stored dynamic diagnosis differs from reconstruction")
        combined = _combined_usage(original.usage, audit_usage, selected=selected)
        if (
            checked.combined_usage != combined
            or checked.prompt_sha256 != sha256(prompt.encode()).hexdigest()
            or checked.instructions_sha256
            != sha256(SCOPE_ROLE_AUDIT_INSTRUCTIONS.encode()).hexdigest()
        ):
            raise ValueError("Stored audit receipts differ from current reconstruction")
        return checked
    except Exception:
        raise ScopeRoleAuditError(
            "Invalid scope role audit generation",
            generation_usage=generation_usage,
            audit_usage=audit_usage,
            audit_may_have_started=selected,
        ) from None


def _build_output(
    source: Source,
    generation: AuditedGeneration,
    output: BaseModel,
    output_type: type[BaseModel],
) -> ScopeAuditReport:
    _canonical_models(output, output_type)
    _actual_models(output, output_type)
    dynamic = _read(output_type, output)
    canonical = ScopeAuditInput.model_validate_json(dynamic.model_dump_json(), strict=True)
    return build_scope_audit_report(source, generation, canonical)


class _ObservedAuditModel(WrapperModel):
    """Observe raw response usage before SDK limits can discard its message.

    This local gate forwards one nonstreaming request and leaves all client
    construction, settings and lifecycle with the borrowed caller model.
    """

    def __init__(self, model: Model):
        super().__init__(model)
        self.responses: list[ModelMessage] = []
        self.request_started = False

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        if self.request_started:
            raise ValueError("Audit cannot make a second model request")
        self.request_started = True
        response = await self.wrapped.request(messages, model_settings, model_request_parameters)
        self.responses.append(response)
        return response


@dataclass(frozen=True)
class _ScopeRoleAuditor:
    model: Model


def create_scope_role_auditor(model: Model) -> _ScopeRoleAuditor:
    """Lazily borrow a required caller model, retaining caller lifecycle and settings."""
    if not isinstance(model, Model):
        raise ScopeRoleAuditError("Invalid scope role audit model") from None
    return _ScopeRoleAuditor(model)


def run_scope_role_auditor(
    auditor: _ScopeRoleAuditor, source: Source, generation: AuditedGeneration
) -> ScopeRoleAuditGeneration:
    """Add diagnosis with at most one request, no retry/repair/fallback or regeneration."""
    generation_usage = audit_usage = None
    started = False
    captured: list[ModelMessage] = []
    observed: _ObservedAuditModel | None = None
    try:
        generation = _checked_generation(source, generation)
        generation_usage = generation.usage
        if type(auditor) is not _ScopeRoleAuditor or not isinstance(auditor.model, Model):
            raise ValueError("Invalid borrowed auditor")
        prompt, tools, remaining, cap = _preflight(source, generation)
    except Exception:
        raise ScopeRoleAuditError(
            "Invalid scope role audit input", generation_usage=generation_usage
        ) from None
    try:
        if not generation.frame.facts:
            report = build_scope_audit_report(
                source, generation, ScopeAuditInput(checks=(), issues=(), incomplete=False)
            )
        else:
            observed = _ObservedAuditModel(auditor.model)
            agent: Agent[None, BaseModel] = Agent(
                observed,
                name=PROVIDER_IDENTITY,
                instructions=SCOPE_ROLE_AUDIT_INSTRUCTIONS,
                output_type=tools,
                retries=0,
            )
            with capture_run_messages() as captured:
                # From here the provider may have received a request even if no response arrives.
                started = True
                result = agent.run_sync(
                    prompt,
                    model_settings=OpenAIResponsesModelSettings(
                        openai_store=False, max_tokens=cap, timeout=30
                    ),
                    usage_limits=UsageLimits(
                        request_limit=1, output_tokens_limit=cap, total_tokens_limit=remaining
                    ),
                    retries=0,
                )
            audit_usage = _known_usage(result)
            _validate_result_usage(result, total=remaining, output=cap)
            if type(result.usage.requests) is not int or result.usage.requests != 1:
                raise ValueError("Invalid audit request count")
            _combined_usage(generation_usage, audit_usage, selected=True)
            output_type = tools[0].output
            assert isinstance(output_type, type) and issubclass(output_type, BaseModel)
            if type(result.output) is not output_type:
                raise ValueError("Expected actual dynamic audit output")
            report = _build_output(source, generation, result.output, output_type)
        stored = ScopeRoleAuditGeneration(
            profile="scope-role-audit-v1",
            report=report,
            prompt_sha256=sha256(prompt.encode()).hexdigest(),
            instructions_sha256=sha256(SCOPE_ROLE_AUDIT_INSTRUCTIONS.encode()).hexdigest(),
            audit_usage=audit_usage,
            combined_usage=_combined_usage(
                generation_usage, audit_usage, selected=bool(generation.frame.facts)
            ),
        )
        return validate_scope_role_audit_generation(source, stored)
    except Exception:
        if audit_usage is None:
            audit_usage = _captured_usage(observed.responses if observed is not None else captured)
        raise ScopeRoleAuditError(
            "Scope role audit failed",
            generation_usage=generation_usage,
            audit_usage=audit_usage,
            audit_may_have_started=started,
        ) from None
