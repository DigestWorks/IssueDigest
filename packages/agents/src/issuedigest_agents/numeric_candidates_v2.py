"""Pure, versioned school/people approximation hints; never semantic certification."""

from hashlib import sha256
from typing import Literal, Self

from issuedigest_domain.sources import Sha256
from pydantic import UUID4, Field, model_validator

from . import numeric_candidates as v1
from .numeric_candidates import (
    ExactSpan,
    LexicalKind,
    NumericAtom,
    NumericCandidateError,
    SentenceCandidate,
)
from .numeric_evidence import QuoteProvenance, Source, _json, _plain, _source_data, _StrictModel
from .numeric_selection_evaluation import _canonical_models
from .shared_measurement_context import _actual_models


class NumericCandidateV2(_StrictModel):
    candidate_id: str
    sentence_ids: tuple[str, ...] = Field(min_length=1)
    expression: ExactSpan
    atoms: tuple[NumericAtom, ...] = Field(min_length=1, max_length=2)
    separator: ExactSpan | None
    qualifiers: tuple[ExactSpan, ...] = Field(max_length=4)
    lexical_kind: LexicalKind

    @model_validator(mode="after")
    def ordered_children(self) -> Self:
        # Preserve the frozen atom/range checks; only qualifier placement is new.
        v1.NumericCandidate(
            candidate_id=self.candidate_id,
            sentence_ids=self.sentence_ids,
            expression=self.expression,
            atoms=self.atoms,
            separator=self.separator,
            qualifiers=(),
            lexical_kind=self.lexical_kind,
        )
        first = self.atoms[0].number.start
        last = (self.atoms[-1].unit or self.atoms[-1].number).end
        children = [s for a in self.atoms for s in (a.number, a.unit) if s is not None]
        if self.separator is not None:
            children.append(self.separator)
        for qualifier in self.qualifiers:
            outside = qualifier.end <= first or qualifier.start >= last
            medial = any(
                a.unit is not None
                and a.unit.text == "명"
                and qualifier.text == "여"
                and a.number.end <= qualifier.start < qualifier.end <= a.unit.start
                and not self.expression.text[
                    a.number.end - self.expression.start : qualifier.start - self.expression.start
                ].strip(" \t")
                and not self.expression.text[
                    qualifier.end - self.expression.start : a.unit.start - self.expression.start
                ].strip(" \t")
                for a in self.atoms
            )
            if not (outside or medial):
                raise ValueError("Invalid qualifier position")
            if (
                qualifier.citation_id != self.expression.citation_id
                or not self.expression.start
                <= qualifier.start
                < qualifier.end
                <= self.expression.end
                or self.expression.text[
                    qualifier.start - self.expression.start : qualifier.end - self.expression.start
                ]
                != qualifier.text
            ):
                raise ValueError("Invalid qualifier source")
        if any(
            a.start >= b.start for a, b in zip(self.qualifiers, self.qualifiers[1:], strict=False)
        ):
            raise ValueError("Unordered qualifiers")
        children.extend(self.qualifiers)
        children.sort(key=lambda span: span.start)
        if any(a.end > b.start for a, b in zip(children, children[1:], strict=False)):
            raise ValueError("Overlapping children")
        return self


class NumericCandidateIndexV2(_StrictModel):
    profile: Literal["numeric-candidates-v2"] = "numeric-candidates-v2"
    status: Literal["unreviewed"] = "unreviewed"
    snapshot_id: UUID4
    workspace_id: UUID4
    source_sha256: Sha256
    citations: tuple[QuoteProvenance, ...] = Field(min_length=1, max_length=20)
    sentences: tuple[SentenceCandidate, ...]
    candidates: tuple[NumericCandidateV2, ...] = Field(max_length=256)


def _boundary(text: str, pos: int) -> bool:
    if pos == len(text) or (not text[pos].isalnum() and text[pos] != "_"):
        return True
    # A whole finite ending is allowed; a prefix of an attached word is not.
    return any(
        text.startswith(ending, pos) and _terminal(text, pos + len(ending))
        for ending in v1._ENDINGS
    )


def _terminal(text: str, pos: int) -> bool:
    return pos == len(text) or (not text[pos].isalnum() and text[pos] != "_")


def _unit_boundary(text: str, pos: int) -> bool:
    suffix = v1._SUFFIX.match(text, pos)
    return (
        _boundary(text, pos)
        or (suffix is not None and _boundary(text, suffix.end()))
        or (text.startswith("내외", pos) and _boundary(text, pos + 2))
    )


def _prefix_boundary(text: str, start: int) -> bool:
    if start == 0 or not (text[start - 1].isalnum() or text[start - 1] == "_"):
        return True
    prefix = v1._PREFIX.search(text, 0, start)
    return prefix is not None and (
        prefix.start() == 0
        or not (text[prefix.start() - 1].isalnum() or text[prefix.start() - 1] == "_")
    )


def _atom(
    cid: str, text: str, start: int
) -> tuple[NumericAtom, int, LexicalKind, tuple[ExactSpan, ...]] | None:
    parsed = v1._atom(cid, text, start)
    if parsed is None:
        return None
    atom, end, kind = parsed
    unit_start = v1._horizontal(text, atom.number.end)
    school = text.startswith("개교", unit_start)
    medial = text.startswith("여", unit_start)
    if school or medial:
        unit_end = unit_start + 2 if school else v1._horizontal(text, unit_start + 1) + 1
        supported = school or text[unit_end - 1 : unit_end] == "명"
        if supported and _prefix_boundary(text, start) and _unit_boundary(text, unit_end):
            unit = v1._span(cid, text, unit_start if school else unit_end - 1, unit_end)
            qualifiers = () if school else (v1._span(cid, text, unit_start, unit_start + 1),)
            return (
                NumericAtom(number=atom.number, unit=unit),
                unit_end,
                ("ambiguous" if kind == "ambiguous" else "number"),
                qualifiers,
            )
        # Keep the original conservative partition, but do not certify attached names.
        return atom, end, "ambiguous" if kind == "ambiguous" else "identifier", ()
    suffix = v1._horizontal(text, end)
    if (
        atom.unit is None
        and kind == "identifier"
        and text.startswith("내외", suffix)
        and _boundary(text, suffix + 2)
        and _prefix_boundary(text, start)
    ):
        kind = "number"
    return atom, end, kind, ()


def _scan(
    cid: str, text: str, sentences: list[SentenceCandidate], base: int
) -> list[NumericCandidateV2]:
    result: list[NumericCandidateV2] = []
    pos = 0
    while pos < len(text):
        legal, date = v1._LEGAL.match(text, pos), v1._DATE.match(text, pos)
        qualifiers: list[ExactSpan] = []
        separator = None
        atoms: tuple[NumericAtom, ...]
        if legal is not None or date is not None:
            # Reuse whole-token priority and exact offsets, including invalid calendar dates.
            token = legal if legal is not None else date
            assert token is not None
            end = token.end()
            number_start = legal.start(1) if legal is not None else pos
            number_end = legal.end(1) if legal is not None else end
            atoms = (NumericAtom(number=v1._span(cid, text, number_start, number_end), unit=None),)
            kind: LexicalKind = "identifier" if legal is not None else "temporal"
        else:
            parsed = _atom(cid, text, pos)
            if parsed is None:
                pos += 1
                continue
            atom, end, kind, medial = parsed
            atoms = (atom,)
            qualifiers.extend(medial)
            delimiter = v1._horizontal(text, end)
            if delimiter < len(text) and text[delimiter] in v1._SEPARATORS:
                right_start = v1._horizontal(text, delimiter + 1)
                right = (
                    None
                    if (v1._DATE.match(text, right_start) or v1._LEGAL.match(text, right_start))
                    else _atom(cid, text, right_start)
                )
                if right is not None:
                    right_atom, end, right_kind, right_medial = right
                    atoms = (atom, right_atom)
                    separator = v1._span(cid, text, delimiter, delimiter + 1)
                    qualifiers.extend(right_medial)
                    kind = next(
                        (
                            k
                            for k in ("ambiguous", "temporal", "identifier")
                            if k in (kind, right_kind)
                        ),
                        "number",
                    )
        start = pos
        prefix = v1._PREFIX.search(text, result[-1].expression.end if result else 0, pos)
        if prefix is not None:
            start = prefix.start()
            prefix_end = pos
            while text[prefix_end - 1] in " \t":
                prefix_end -= 1
            qualifiers.insert(0, v1._span(cid, text, start, prefix_end))
        suffix = v1._SUFFIX.match(text, end)
        if suffix is not None:
            qualifiers.append(v1._span(cid, text, suffix.start(1), suffix.end(1)))
            end = suffix.end()
        else:
            near = v1._horizontal(text, end)
            quantity = kind == "number" or (
                kind == "temporal"
                and any(a.unit is not None and a.unit.text in v1._TEMPORAL for a in atoms)
            )
            if (
                text.startswith("내외", near)
                and _boundary(text, near + 2)
                and quantity
                and all(_prefix_boundary(text, a.number.start) for a in atoms)
            ):
                qualifiers.append(v1._span(cid, text, near, near + 2))
                end = near + 2
        result.append(
            NumericCandidateV2(
                candidate_id=f"n{base + len(result) + 1}",
                sentence_ids=tuple(
                    s.sentence_id for s in sentences if s.span.start < end and s.span.end > start
                ),
                expression=v1._span(cid, text, start, end),
                atoms=atoms,
                separator=separator,
                qualifiers=tuple(qualifiers),
                lexical_kind=kind,
            )
        )
        if base + len(result) > 256:
            raise ValueError("Candidate limit exceeded")
        pos = end
    return result


def _build(source: Source) -> NumericCandidateIndexV2:
    _canonical_models(source, Source)
    _actual_models(source, Source)
    data = _source_data(source)
    sentences: list[SentenceCandidate] = []
    candidates: list[NumericCandidateV2] = []
    for citation in data.citations:
        parts = v1._sentences(citation.citation_id, citation.quote, len(sentences))
        sentences.extend(parts)
        candidates.extend(_scan(citation.citation_id, citation.quote, parts, len(candidates)))
    return NumericCandidateIndexV2(
        snapshot_id=data.snapshot_id,
        workspace_id=data.workspace_id,
        source_sha256=sha256(_json(data.payload()).encode("utf-8")).hexdigest(),
        citations=data.citations,
        sentences=tuple(sentences),
        candidates=tuple(candidates),
    )


def build_numeric_candidates_v2(source: Source) -> NumericCandidateIndexV2:
    """Build the entire unreviewed v2 source index without I/O or model requests."""
    try:
        return _build(source)
    except Exception:
        raise NumericCandidateError("Invalid numeric candidate input") from None


def validate_numeric_candidates_v2(
    source: Source, index: NumericCandidateIndexV2
) -> NumericCandidateIndexV2:
    """Reject unchecked actual types before dumping; recreate all fields and omissions."""
    try:
        if type(index) is not NumericCandidateIndexV2:
            raise ValueError("Invalid index type")
        _canonical_models(index, NumericCandidateIndexV2)
        _actual_models(index, NumericCandidateIndexV2)
        checked = NumericCandidateIndexV2.model_validate(_plain(index), strict=True)
        expected = _build(source)
        if checked != expected:
            raise ValueError("Index differs from source regeneration")
        return expected
    except Exception:
        raise NumericCandidateError("Invalid numeric candidate index") from None


def numeric_candidates_packet_v2(source: Source, index: NumericCandidateIndexV2) -> str:
    """Canonical whole-source JSON after strict, complete reconstruction."""
    return _json(validate_numeric_candidates_v2(source, index).model_dump(mode="json"))
