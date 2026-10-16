"""Count an untrusted model graph before any complete JSON allocation.

Occurrences, including shared aliases, consume the serialization budget individually.
Only the existing contract model types and bounded JSON scalar types are traversed.
Nested domain revalidation remains the responsibility of the existing JSON parsers.
"""

import json
import math
from datetime import datetime
from typing import Annotated
from uuid import UUID

from issuedigest_domain import (
    Citation,
    DocumentVersion,
    EvidenceBundle,
    NormalizedBox,
    PageSpan,
    ParsedRepresentation,
    ParsedTable,
    PdfQuoteSelector,
    SourceDocument,
    TableCell,
    TableCellSelector,
    TextQuoteSelector,
)
from issuedigest_storage.provisioning import (
    MAX_PLAN_BYTES,
    ProvisioningInvite,
    ProvisioningPlan,
    ProvisioningSnapshot,
)
from pydantic import AnyHttpUrl, BaseModel, TypeAdapter, UrlConstraints

from .assembly_models import AssemblyJob
from .models import (
    CellCitationRequest,
    HwpxJob,
    HwpxSource,
    LicenseAttestation,
    TextCitationRequest,
)

_MODEL_TYPES = {
    AssemblyJob,
    HwpxJob,
    HwpxSource,
    LicenseAttestation,
    TextCitationRequest,
    CellCitationRequest,
    ProvisioningPlan,
    ProvisioningInvite,
    ProvisioningSnapshot,
    EvidenceBundle,
    SourceDocument,
    DocumentVersion,
    ParsedRepresentation,
    ParsedTable,
    TableCell,
    PageSpan,
    Citation,
    TextQuoteSelector,
    TableCellSelector,
    PdfQuoteSelector,
    NormalizedBox,
}
_COLLECTION_LIMITS: dict[tuple[type[BaseModel], str], tuple[int, int]] = {
    (HwpxJob, "sources"): (1, 10),
    (HwpxSource, "citations"): (1, 100),
    (ProvisioningPlan, "snapshots"): (1, 50),
    (ProvisioningPlan, "invites"): (1, 2),
}
_STRING_LIMITS: dict[tuple[type[BaseModel], str], int] = {
    (AssemblyJob, "bill_id"): 80,
    (AssemblyJob, "title"): 300,
    (AssemblyJob, "bill_number"): 10,
    (HwpxSource, "raw_path"): 4096,
    (LicenseAttestation, "evidence_url"): 4096,
    (TextCitationRequest, "quote"): 100_000,
    (CellCitationRequest, "table_id"): 96,
    (CellCitationRequest, "cell_id"): 96,
}
# Validate the core URL rather than the wrapper: Pydantic's wrapper instance shortcut
# otherwise skips max_length. The core validator checks its Rust string before copying.
_URL = TypeAdapter(Annotated[AnyHttpUrl, UrlConstraints(max_length=MAX_PLAN_BYTES)])


class _Budget:
    def __init__(self) -> None:
        self.remaining = MAX_PLAN_BYTES
        self.active: set[int] = set()

    def consume(self, count: int) -> None:
        self.remaining -= count
        if self.remaining < 0:
            raise ValueError("Model byte budget exceeded")

    def string(self, value: str) -> None:
        # Characters alone are a lower bound. Escape/UTF-8 expansion is counted in
        # small chunks, so a single enormous forged field is never encoded in full.
        if len(value) > self.remaining:
            raise ValueError("Model string budget exceeded")
        self.consume(2)
        for start in range(0, len(value), 4096):
            chunk = json.dumps(value[start : start + 4096], ensure_ascii=False)
            self.consume(len(chunk.encode("utf-8")) - 2)

    def visit(self, value: object, depth: int = 0) -> None:
        if depth > 32:
            raise ValueError("Model depth exceeded")
        kind = type(value)
        if kind is str:
            assert isinstance(value, str)
            self.string(value)
        elif value is None or kind is bool:
            self.consume(4 if value is None or value is True else 5)
        elif kind is int:
            assert isinstance(value, int)
            if value.bit_length() > 64:
                raise ValueError("Model integer limit exceeded")
            self.consume(len(str(value)))
        elif kind is float:
            assert isinstance(value, float)
            if not math.isfinite(value):
                raise ValueError("Nonfinite model value")
            self.consume(len(json.dumps(value)))
        elif kind is UUID:
            self.consume(38)
        elif kind is datetime:
            assert isinstance(value, datetime)
            instant = value.isoformat()
            self.string(instant[:-6] + "Z" if instant.endswith("+00:00") else instant)
        elif kind is AnyHttpUrl:
            assert isinstance(value, AnyHttpUrl)
            validated = _URL.validate_python(value._url)
            self.string(str(validated))
        elif kind is tuple or kind in _MODEL_TYPES:
            identity = id(value)
            if identity in self.active:
                raise ValueError("Cyclic model input")
            self.active.add(identity)
            try:
                if isinstance(value, tuple):
                    # Every occurrence requires at least one byte, even if aliases
                    # refer to one object. Check count before walking any contents.
                    if len(value) > self.remaining:
                        raise ValueError("Model collection limit exceeded")
                    self.consume(2 + max(0, len(value) - 1))
                    for item in value:
                        self.visit(item, depth + 1)
                else:
                    assert isinstance(value, BaseModel)
                    fields = type(value).model_fields
                    if len(value.__dict__) != len(fields) or value.__pydantic_extra__:
                        raise ValueError("Unexpected model fields")
                    self.consume(2 + max(0, len(fields) - 1))
                    for name in fields:
                        item = value.__dict__[name]
                        limits = _COLLECTION_LIMITS.get((type(value), name))
                        if limits is not None and (
                            type(item) is not tuple or not limits[0] <= len(item) <= limits[1]
                        ):
                            raise ValueError("Model collection bounds exceeded")
                        maximum = _STRING_LIMITS.get((type(value), name))
                        if maximum is not None and (type(item) is not str or len(item) > maximum):
                            raise ValueError("Model field bounds exceeded")
                        self.string(name)
                        self.consume(1)
                        self.visit(item, depth + 1)
            finally:
                self.active.remove(identity)
        else:
            raise ValueError("Unsupported model input")


def preflight_model(value: HwpxJob | AssemblyJob | ProvisioningPlan) -> None:
    """Bound counts, depth and aggregate escaped UTF-8 bytes before full serialization."""
    if type(value) is HwpxJob:
        if type(value.sources) is not tuple or not 1 <= len(value.sources) <= 10:
            raise ValueError("Invalid source count")
        # Bound these counts before traversing any citation contents.
        count = 0
        for source in value.sources:
            if type(source) is not HwpxSource or type(source.citations) is not tuple:
                raise ValueError("Invalid source input")
            if not 1 <= len(source.citations) <= 100:
                raise ValueError("Invalid citation count")
            count += len(source.citations)
        if count > 200:
            raise ValueError("Too many citations")
    elif type(value) not in {AssemblyJob, ProvisioningPlan}:
        raise ValueError("Invalid model input")
    _Budget().visit(value)
