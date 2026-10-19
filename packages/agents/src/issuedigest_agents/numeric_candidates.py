"""Finite lexical candidates from whole quotations; no semantic certification or I/O."""

import re
from hashlib import sha256
from typing import Annotated, Literal, Self

from issuedigest_domain.sources import Sha256
from pydantic import UUID4, Field, model_validator

from .numeric_evidence import QuoteProvenance, Source, _json, _plain, _source_data, _StrictModel

type LexicalKind = Literal["number", "temporal", "identifier", "ambiguous"]


class NumericCandidateError(ValueError):
    """Sanitized failure of the complete, pure candidate operation."""


class ExactSpan(_StrictModel):
    """Half-open Python Unicode code-point offsets in one original whole quote."""

    citation_id: str
    text: Annotated[str, Field(min_length=1)]
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(gt=0)]

    @model_validator(mode="after")
    def exact_length(self) -> Self:
        if self.end <= self.start or self.end - self.start != len(self.text):
            raise ValueError("Invalid span length")
        return self


class SentenceCandidate(_StrictModel):
    sentence_id: str
    span: ExactSpan


class NumericAtom(_StrictModel):
    number: ExactSpan
    unit: ExactSpan | None

    @model_validator(mode="after")
    def numeric_span(self) -> Self:
        if not any("0" <= c <= "9" for c in self.number.text):
            raise ValueError("Atom requires ASCII digit")
        if self.unit is not None and (
            self.unit.citation_id != self.number.citation_id or self.unit.start < self.number.end
        ):
            raise ValueError("Invalid atom unit")
        return self


class NumericCandidate(_StrictModel):
    candidate_id: str
    sentence_ids: tuple[str, ...] = Field(min_length=1)
    expression: ExactSpan
    atoms: tuple[NumericAtom, ...] = Field(min_length=1, max_length=2)
    separator: ExactSpan | None
    qualifiers: tuple[ExactSpan, ...] = Field(max_length=2)
    lexical_kind: LexicalKind

    @model_validator(mode="after")
    def ordered_children(self) -> Self:
        if len(set(self.sentence_ids)) != len(self.sentence_ids):
            raise ValueError("Duplicate sentence references")
        if (len(self.atoms) == 2) != (self.separator is not None):
            raise ValueError("Invalid range separator")
        children = [s for a in self.atoms for s in (a.number, a.unit) if s is not None]
        if any(a.start >= b.start for a, b in zip(children, children[1:], strict=False)):
            raise ValueError("Unordered atoms")
        if self.separator is not None:
            left = self.atoms[0].unit or self.atoms[0].number
            if (
                not left.end
                <= self.separator.start
                < self.separator.end
                <= self.atoms[1].number.start
            ):
                raise ValueError("Separator outside range")
            children.append(self.separator)
        if any(
            a.start >= b.start for a, b in zip(self.qualifiers, self.qualifiers[1:], strict=False)
        ):
            raise ValueError("Unordered qualifiers")
        first = self.atoms[0].number.start
        last = (self.atoms[-1].unit or self.atoms[-1].number).end
        for qualifier in self.qualifiers:
            if not (qualifier.end <= first or qualifier.start >= last):
                raise ValueError("Qualifier inside number")
        children.extend(self.qualifiers)
        children.sort(key=lambda span: span.start)
        for child in children:
            if (
                child.citation_id != self.expression.citation_id
                or not self.expression.start <= child.start < child.end <= self.expression.end
                or self.expression.text[
                    child.start - self.expression.start : child.end - self.expression.start
                ]
                != child.text
            ):
                raise ValueError("Child outside expression")
        if any(a.end > b.start for a, b in zip(children, children[1:], strict=False)):
            raise ValueError("Overlapping children")
        return self


class NumericCandidateIndex(_StrictModel):
    profile: Literal["numeric-candidates-v1"] = "numeric-candidates-v1"
    status: Literal["unreviewed"] = "unreviewed"
    snapshot_id: UUID4
    workspace_id: UUID4
    source_sha256: Sha256
    citations: tuple[QuoteProvenance, ...] = Field(min_length=1, max_length=20)
    sentences: tuple[SentenceCandidate, ...]
    candidates: tuple[NumericCandidate, ...] = Field(max_length=256)


# Numeric text ends in a digit; terminal punctuation is handled by the partition.
_RUN = re.compile(r"[+−-]?[0-9]+(?:[.,][0-9.,]*[0-9])?")
_NORMAL = re.compile(r"[+−-]?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?\Z")
_DATE = re.compile(r"(?:[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{4}/[0-9]{2}/[0-9]{2})(?![0-9])")
_LEGAL = re.compile(r"제([0-9]+)[조항호]")
_MULTIPLIERS = "십백천만억조"
_TEMPORAL = ("개월", "년", "월", "일", "시", "분", "초")
_UNITS = tuple(
    sorted(
        (
            "%p",
            "%",
            "bp",
            "p",
            "호",
            "명",
            "원",
            "건",
            "개",
            "배",
            "점",
            "석",
            "곳",
            "km²",
            "km2",
            "㎢",
            "km",
            "m²",
            "m2",
            "㎡",
            "m",
            "kg",
            "g",
            "t",
            *_TEMPORAL,
        ),
        key=len,
        reverse=True,
    )
)
_PREFIX = re.compile(r"(?:최대|최소|약)[ \t]*\Z")
_SUFFIX = re.compile(r"[ \t]*(이상|이하|초과|미만)")
# Finite grammatical endings take precedence over attached-name hints.
_ENDINGS = (
    "으로",
    "로",
    "이다",
    "이었다",
    "입니다",
    "이고",
    "이며",
    "에서",
    "에",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "와",
    "과",
    "의",
    "도",
    "만",
    "부터",
    "까지",
    "보다",
)
_SEPARATORS = "~∼～–—-"


def _span(cid: str, text: str, start: int, end: int) -> ExactSpan:
    return ExactSpan(citation_id=cid, text=text[start:end], start=start, end=end)


def _horizontal(text: str, pos: int) -> int:
    while pos < len(text) and text[pos] in " \t":
        pos += 1
    return pos


def _sentences(cid: str, text: str, base: int) -> list[SentenceCandidate]:
    result: list[SentenceCandidate] = []
    start = 0
    for pos, char in enumerate(text):
        decimal = (
            char == "."
            and pos > 0
            and pos + 1 < len(text)
            and "0" <= text[pos - 1] <= "9"
            and "0" <= text[pos + 1] <= "9"
        )
        if char == "\n" or (char in ".?!。！？" and not decimal):
            result.append(
                SentenceCandidate(
                    sentence_id=f"s{base + len(result) + 1}", span=_span(cid, text, start, pos + 1)
                )
            )
            start = pos + 1
    if start < len(text):
        result.append(
            SentenceCandidate(
                sentence_id=f"s{base + len(result) + 1}", span=_span(cid, text, start, len(text))
            )
        )
    return result


def _atom(cid: str, text: str, start: int) -> tuple[NumericAtom, int, LexicalKind] | None:
    # A sign cannot turn a following whole date into an ordinary numeric atom.
    if text[start : start + 1] in ("+", "-", "−") and _DATE.match(text, start + 1):
        return None
    match = _RUN.match(text, start)
    if match is None:
        return None
    end = match.end()
    kind: LexicalKind = "number" if _NORMAL.fullmatch(match[0]) else "ambiguous"
    if kind == "number":
        # Only a multiplier licenses another horizontally separated numeric group.
        while True:
            multiplier = _horizontal(text, end)
            stop = multiplier
            while stop < len(text) and text[stop] in _MULTIPLIERS:
                stop += 1
            if stop == multiplier:
                break
            end = stop
            continuation = _horizontal(text, end)
            # Compound groups are unsigned; leave a hyphen for the range parser.
            if continuation == len(text) or not "0" <= text[continuation] <= "9":
                break
            # Whole-date priority also applies inside a compound's lookahead.
            if _DATE.match(text, continuation):
                break
            following = _RUN.match(text, continuation)
            if following is None or not _NORMAL.fullmatch(following[0]):
                break
            end = following.end()
    number = _span(cid, text, start, end)
    unit = None
    unit_start = _horizontal(text, end)
    # A complete qualifier wins over a partial unit prefix (notably 초과/초).
    has_suffix = _SUFFIX.match(text, end) is not None
    if not has_suffix:
        for spelling in _UNITS:
            if text.startswith(spelling, unit_start):
                unit = _span(cid, text, unit_start, unit_start + len(spelling))
                end = unit.end
                if kind != "ambiguous":
                    kind = "temporal" if spelling in _TEMPORAL else "number"
                break
    if unit is None and kind == "number":
        suffix = text[end:]
        suffix_name = bool(
            not has_suffix and suffix and suffix[0].isalpha() and not suffix.startswith(_ENDINGS)
        )
        prefix_name = (
            start > 0
            and text[start - 1].isalpha()
            and not text[:start].endswith(("약", "최대", "최소"))
        )
        if suffix_name or prefix_name:
            kind = "identifier"
    return NumericAtom(number=number, unit=unit), end, kind


def _scan(
    cid: str, text: str, sentences: list[SentenceCandidate], base: int
) -> list[NumericCandidate]:
    result: list[NumericCandidate] = []
    pos = 0
    while pos < len(text):
        legal = _LEGAL.match(text, pos)
        date = _DATE.match(text, pos)
        qualifier_spans: list[ExactSpan] = []
        separator = None
        start = pos
        atoms: tuple[NumericAtom, ...]
        kind: LexicalKind
        if legal is not None:
            end = legal.end()
            atoms = (NumericAtom(number=_span(cid, text, legal.start(1), legal.end(1)), unit=None),)
            kind = "identifier"
        elif date is not None:
            end = date.end()
            atoms = (NumericAtom(number=_span(cid, text, pos, end), unit=None),)
            kind = "temporal"
        else:
            parsed = _atom(cid, text, pos)
            if parsed is None:
                pos += 1
                continue
            atom, end, kind = parsed
            atoms = (atom,)
            separator_start = _horizontal(text, end)
            if separator_start < len(text) and text[separator_start] in _SEPARATORS:
                right_start = _horizontal(text, separator_start + 1)
                right = (
                    None
                    if _DATE.match(text, right_start) or _LEGAL.match(text, right_start)
                    else _atom(cid, text, right_start)
                )
                if right is not None:
                    right_atom, right_end, right_kind = right
                    separator = _span(cid, text, separator_start, separator_start + 1)
                    atoms = (atom, right_atom)
                    end = right_end
                    if "ambiguous" in (kind, right_kind):
                        kind = "ambiguous"
                    elif "temporal" in (kind, right_kind):
                        kind = "temporal"
                    elif "identifier" in (kind, right_kind):
                        kind = "identifier"
        # A prefix cannot consume text already assigned to the previous candidate.
        prefix_floor = result[-1].expression.end if result else 0
        prefix = _PREFIX.search(text, prefix_floor, pos)
        if prefix is not None:
            start = prefix.start()
            qualifier_end = pos
            while text[qualifier_end - 1] in " \t":
                qualifier_end -= 1
            qualifier_spans.append(_span(cid, text, start, qualifier_end))
        suffix = _SUFFIX.match(text, end)
        if suffix is not None:
            qualifier_spans.append(_span(cid, text, suffix.start(1), suffix.end(1)))
            end = suffix.end()
        expression = _span(cid, text, start, end)
        overlapping = tuple(
            s.sentence_id for s in sentences if s.span.start < end and s.span.end > start
        )
        result.append(
            NumericCandidate(
                candidate_id=f"n{base + len(result) + 1}",
                sentence_ids=overlapping,
                expression=expression,
                atoms=atoms,
                separator=separator,
                qualifiers=tuple(qualifier_spans),
                lexical_kind=kind,
            )
        )
        if base + len(result) > 256:
            raise ValueError("Candidate limit exceeded")
        pos = end
    return result


def _build(source: Source) -> NumericCandidateIndex:
    data = _source_data(source)
    sentences: list[SentenceCandidate] = []
    candidates: list[NumericCandidate] = []
    for citation in data.citations:
        parts = _sentences(citation.citation_id, citation.quote, len(sentences))
        sentences.extend(parts)
        candidates.extend(_scan(citation.citation_id, citation.quote, parts, len(candidates)))
    return NumericCandidateIndex(
        snapshot_id=data.snapshot_id,
        workspace_id=data.workspace_id,
        source_sha256=sha256(_json(data.payload()).encode("utf-8")).hexdigest(),
        citations=data.citations,
        sentences=tuple(sentences),
        candidates=tuple(candidates),
    )


def build_numeric_candidates(source: Source) -> NumericCandidateIndex:
    """Build a complete unreviewed lexical index or reject the entire operation."""
    try:
        return _build(source)
    except Exception:
        raise NumericCandidateError("Invalid numeric candidate input") from None


def validate_numeric_candidates(
    source: Source, index: NumericCandidateIndex
) -> NumericCandidateIndex:
    """Recreate every field from the current canonical source, including omissions."""
    try:
        if type(index) is not NumericCandidateIndex:
            raise ValueError("Invalid index type")
        checked = NumericCandidateIndex.model_validate(_plain(index), strict=True)
        expected = _build(source)
        if checked != expected:
            raise ValueError("Index differs from source regeneration")
        return expected
    except Exception:
        raise NumericCandidateError("Invalid numeric candidate index") from None


def numeric_candidates_packet(source: Source, index: NumericCandidateIndex) -> str:
    """Canonical whole-source JSON; provider schema/instructions/budget are separate."""
    checked = validate_numeric_candidates(source, index)
    return _json(checked.model_dump(mode="json"))
