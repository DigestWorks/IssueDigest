"""One bounded table-input audit with independent receipts and unchanged role reports."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel
from pydantic_ai import ToolOutput
from pydantic_ai.models import Model

from .balanced_role_generation import RoleAliasGenerationV2, validate_balanced_role_generation
from .numeric_evidence import KnownUsage, Source, _json, _StrictModel
from .numeric_selection_evaluation import _read
from .role_alias_contract import _guard
from .role_aware_audit_contract import RoleAwareAuditInput
from .role_bounded_runtime import RoleRequestError, _request_envelope, _run_role_request
from .role_table_packet import (
    _copy_json,
    _original_values,
    build_role_table_packet,
    decode_role_table_packet,
)
from .scope_role_audit import _sum_usage
from .semantic_role_audit import (
    SEMANTIC_ROLE_AUDIT_INSTRUCTIONS,
    _audit_tools,
    _combined_usage,
    _remaining,
)
from .semantic_role_audit import (
    _build_output as _semantic_build_output,
)
from .semantic_role_audit_contract import (
    SemanticRoleAuditContractError,
    SemanticRoleAuditReport,
    _checked_generation,
    _frame,
    build_semantic_role_audit_report,
    validate_semantic_role_audit_report,
)

PROVIDER_IDENTITY = "issuedigest_role_table_audit_v1"
_DECODER = (
    "Tables {columns,rows} carry complete original objects: map each row cell to its exact "
    "named column, in order. All cells exist, including null and empty lists. Nested "
    "anchors/scopes/change stay named objects. Read candidates and scope slots the same "
    "way; concatenate each quote sentence table text column in row order with no "
    "separators, preserving blanks and whitespace. Never infer missing cells or merge rows. "
)
ROLE_TABLE_AUDIT_INSTRUCTIONS = _DECODER + SEMANTIC_ROLE_AUDIT_INSTRUCTIONS.replace(
    "audit_role_aware_v2", "audit_role_table_v1"
)


class RoleTableAuditError(SemanticRoleAuditContractError):
    """Sanitized failure retaining observed costs and uncertainty about dispatch."""

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


class RoleTableAuditGeneration(_StrictModel):
    profile: Literal["role-table-audit-v1"]
    input_format: Literal["named-columns-v1"]
    report: SemanticRoleAuditReport
    prompt_sha256: Sha256
    instructions_sha256: Sha256
    audit_usage: KnownUsage | None
    combined_usage: KnownUsage


def _build_output(
    source: Source,
    generation: RoleAliasGenerationV2,
    output: BaseModel,
    output_type: type[BaseModel],
) -> SemanticRoleAuditReport:
    _guard(output, output_type)
    _original_values(output, output_type)
    return _semantic_build_output(source, generation, output, output_type)


def _preflight(
    source: Source, generation: RoleAliasGenerationV2
) -> tuple[str, list[ToolOutput[BaseModel]], int, int]:
    packet = build_role_table_packet(source, generation)
    decode_role_table_packet(source, generation, packet)
    generation = _checked_generation(source, generation)
    prompt = _json(packet)
    remaining, cap = _remaining(generation.usage)
    if not generation.frame.input.bindings:
        return prompt, [], remaining, cap
    if cap <= 0 or remaining <= 0:
        raise ValueError("No audit budget remains")
    tools = [
        ToolOutput(tool.output, name="audit_role_table_v1", strict=True)
        for tool in _audit_tools(generation)
    ]
    if _request_envelope(prompt, tools, ROLE_TABLE_AUDIT_INSTRUCTIONS, cap) > remaining:
        raise ValueError("Full table audit envelope exceeds remaining total")
    return prompt, tools, remaining, cap


def role_table_audit_prompt(source: Source, generation: RoleAliasGenerationV2) -> str:
    """Preflight complete current input and actual dynamic schema without I/O."""
    known = None
    try:
        # The codec checks original concrete fields before validators can serialize them.
        build_role_table_packet(source, generation)
        generation = _checked_generation(source, generation)
        known = generation.usage
        return _preflight(source, generation)[0]
    except Exception:
        raise RoleTableAuditError("Invalid table audit input", generation_usage=known) from None


def validate_role_table_audit_generation(
    source: Source, result: RoleTableAuditGeneration | dict[str, Any]
) -> RoleTableAuditGeneration:
    """Rebuild current table input, report/schema and this profile's own stage receipts."""
    generation_usage = audit_usage = None
    selected = False
    try:
        _original_values(source, Source)
        _guard(result, RoleTableAuditGeneration)
        if isinstance(result, BaseModel):
            _original_values(result, RoleTableAuditGeneration)
            fields = result.__dict__
        else:
            fields = _copy_json(result)
        report_fields = fields["report"]
        original_fields = (
            report_fields["generation"]
            if isinstance(report_fields, dict)
            else report_fields.generation
        )
        original = validate_balanced_role_generation(source, original_fields)
        build_role_table_packet(source, original)
        generation_usage = original.usage
        selected = bool(_frame(original).facts)
        checked = _read(RoleTableAuditGeneration, result)
        audit_usage = checked.audit_usage
        report = validate_semantic_role_audit_report(source, checked.report)
        prompt, tools, _, _ = _preflight(source, original)
        if selected:
            output_type = tools[0].output
            assert isinstance(output_type, type) and issubclass(output_type, BaseModel)
            dynamic = output_type.model_validate_json(report.input.model_dump_json(), strict=True)
            if _build_output(source, original, dynamic, output_type) != report:
                raise ValueError("Stored dynamic report differs from reconstruction")
        combined = _combined_usage(original.usage, audit_usage, selected=selected)
        if (
            checked.combined_usage != combined
            or checked.prompt_sha256 != sha256(prompt.encode()).hexdigest()
            or checked.instructions_sha256
            != sha256(ROLE_TABLE_AUDIT_INSTRUCTIONS.encode()).hexdigest()
        ):
            raise ValueError("Stored table audit receipts differ from reconstruction")
        return checked
    except Exception:
        raise RoleTableAuditError(
            "Invalid table audit generation",
            generation_usage=generation_usage,
            audit_usage=audit_usage,
            audit_may_have_started=selected,
        ) from None


@dataclass(frozen=True)
class _RoleTableAuditor:
    model: Model


def create_role_table_auditor(model: Model) -> _RoleTableAuditor:
    """Lazily borrow the caller's Model without changing settings or ownership."""
    if not isinstance(model, Model):
        raise RoleTableAuditError("Invalid table audit model") from None
    return _RoleTableAuditor(model)


def run_role_table_auditor(
    auditor: _RoleTableAuditor, source: Source, generation: RoleAliasGenerationV2
) -> RoleTableAuditGeneration:
    """Audit once, retaining observed usage through every later validation failure."""
    generation_usage = audit_usage = None
    started = False
    try:
        build_role_table_packet(source, generation)
        generation = _checked_generation(source, generation)
        generation_usage = generation.usage
        if type(auditor) is not _RoleTableAuditor or not isinstance(auditor.model, Model):
            raise ValueError("Invalid borrowed auditor")
        prompt, tools, remaining, cap = _preflight(source, generation)
    except Exception:
        raise RoleTableAuditError(
            "Invalid table audit input", generation_usage=generation_usage
        ) from None
    try:
        selected = bool(_frame(generation).facts)
        if selected:
            output, audit_usage = _run_role_request(
                model=auditor.model,
                prompt=prompt,
                tools=tools,
                instructions=ROLE_TABLE_AUDIT_INSTRUCTIONS,
                identity=PROVIDER_IDENTITY,
                total_limit=remaining,
                output_limit=cap,
            )
            started = True
            output_type = tools[0].output
            assert isinstance(output_type, type) and issubclass(output_type, BaseModel)
            report = _build_output(source, generation, output, output_type)
        else:
            report = build_semantic_role_audit_report(
                source, generation, RoleAwareAuditInput(checks=(), issues=(), incomplete=False)
            )
        stored = RoleTableAuditGeneration(
            profile="role-table-audit-v1",
            input_format="named-columns-v1",
            report=report,
            prompt_sha256=sha256(prompt.encode()).hexdigest(),
            instructions_sha256=sha256(ROLE_TABLE_AUDIT_INSTRUCTIONS.encode()).hexdigest(),
            audit_usage=audit_usage,
            combined_usage=_combined_usage(generation_usage, audit_usage, selected=selected),
        )
        return validate_role_table_audit_generation(source, stored)
    except RoleRequestError as error:
        raise RoleTableAuditError(
            "Table audit failed",
            generation_usage=generation_usage,
            audit_usage=audit_usage if audit_usage is not None else error.known_usage,
            audit_may_have_started=started or error.may_have_started,
        ) from None
    except Exception:
        raise RoleTableAuditError(
            "Table audit failed",
            generation_usage=generation_usage,
            audit_usage=audit_usage,
            audit_may_have_started=started,
        ) from None
