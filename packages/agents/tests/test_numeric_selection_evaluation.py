"""Synthetic field-reference regressions; matching never certifies numeric truth."""

import builtins
import importlib
import importlib.util
import io
import json
import os
import socket
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from issuedigest_agents.numeric_candidates import ExactSpan, build_numeric_candidates
from issuedigest_agents.numeric_evidence import KnownUsage
from pydantic import create_model
from test_numeric_evidence import document
from test_numeric_selection import anchor, fact, pure


def api():
    name = "issuedigest_agents.numeric_selection_evaluation"
    assert importlib.util.find_spec(name) is not None, "Missing pure numeric selection evaluator"
    return importlib.import_module(name)


def span(src, text, *, occurrence=0, citation=0):
    quote = src[1].citations[citation].selector.quote
    start = -1
    for _ in range(occurrence + 1):
        start = quote.index(text, start + 1)
    return ExactSpan(
        citation_id=str(src[1].citations[citation].citation_id),
        text=text,
        start=start,
        end=start + len(text),
    ).model_dump(mode="json")


def rule(src=None, *texts, mode="absent", **position):
    return {
        "mode": "one_of" if texts else mode,
        "alternatives": [span(src, text, **position) for text in texts],
    }


def ref_fact(src, candidate="n1", *, kind="unknown", **fields):
    return {
        "candidate_id": candidate,
        "subject": rule(),
        "period": rule(),
        "condition": rule(),
        "kind": kind,
        "status_text": rule(),
        **fields,
    }


def reference(src, facts=(), *, coverage="complete"):
    return {
        "profile": "numeric-selection-reference-v1",
        "candidate_index": build_numeric_candidates(src).model_dump(mode="json"),
        "candidate_set": coverage,
        "facts": list(facts),
    }


def checks(report):
    return [(c.candidate_id, c.field, c.result) for c in report.checks]


def rich():
    src = document("🧪 A 올해 조건 충족 시 10명 전망. B 내년 예외 시 20명 실적.")
    expected = ref_fact(
        src,
        kind="forecast",
        subject=rule(src, "A"),
        period=rule(src, "올해"),
        condition=rule(src, "조건 충족 시"),
        status_text=rule(src, "전망"),
    )
    proposal = pure(
        src,
        [
            fact(
                kind="forecast",
                subject=anchor("A"),
                period=anchor("올해"),
                condition=anchor("조건 충족 시"),
                status=anchor("전망"),
            )
        ],
    )
    return src, reference(src, [expected]), proposal


def test_complete_reference_matches_all_roles_in_documented_order():
    src, ref, proposal = rich()
    report = api().evaluate_numeric_selection(src, ref, proposal)
    assert report.profile == "numeric-selection-evaluation-v1"
    assert report.scope == "fact_fields_only"
    assert report.outcome == "reference_match"
    assert (report.expected_facts, report.received_facts) == (1, 1)
    assert checks(report) == [
        ("n1", "presence", "match"),
        ("n1", "subject", "match"),
        ("n1", "period", "match"),
        ("n1", "condition", "match"),
        ("n1", "kind", "match"),
        ("n1", "status_text", "match"),
    ]
    assert report.usage == KnownUsage(input_tokens=100, output_tokens=30, requests=1)


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("subject", anchor("B", "s2")),
        ("period", anchor("내년", "s2")),
        ("condition", anchor("예외 시", "s2")),
        ("status_text", anchor("실적", "s2")),
        ("kind", "observed"),
    ],
)
def test_source_valid_but_wrong_semantic_role_mismatches_only_that_field(field, replacement):
    src, ref, _ = rich()
    values = dict(
        kind="forecast",
        subject=anchor("A"),
        period=anchor("올해"),
        condition=anchor("조건 충족 시"),
        status=anchor("전망"),
    )
    values["status" if field == "status_text" else field] = replacement
    report = api().evaluate_numeric_selection(src, ref, pure(src, [fact(**values)]))
    assert report.outcome == "reference_mismatch"
    assert [c.field for c in report.checks if c.result == "mismatch"] == [field]


@pytest.mark.parametrize("field", ["subject", "period", "condition", "status_text"])
def test_missing_role_anchor_is_visible_as_field_mismatch(field):
    src, ref, _ = rich()
    values = dict(
        kind="unknown",
        subject=anchor("A"),
        period=anchor("올해"),
        condition=anchor("조건 충족 시"),
        status=anchor("전망"),
    )
    values["status" if field == "status_text" else field] = None
    ref["facts"][0]["kind"] = "unknown"
    report = api().evaluate_numeric_selection(src, ref, pure(src, [fact(**values)]))
    assert [c.field for c in report.checks if c.result == "mismatch"] == [field]


@pytest.mark.parametrize("kind", ["observed", "planned", "forecast", "unknown"])
def test_each_kind_compares_exactly(kind):
    src = document("A 10명 계획.")
    ref = reference(src, [ref_fact(src, kind=kind, status_text=rule(src, "계획"))])
    result = api().evaluate_numeric_selection(
        src, ref, pure(src, [fact(kind=kind, status=anchor("계획"))])
    )
    assert result.outcome == "reference_match"


@pytest.mark.parametrize(
    "coverage,want,extra",
    [("complete", "reference_mismatch", "mismatch"), ("partial", "inconclusive", "unassessed")],
)
def test_incidental_date_is_unexpected_fact_separate_from_missing_fact(coverage, want, extra):
    src = document("올해 A 10명. 공고일 2026-10-20.")
    ref = reference(src, [ref_fact(src)], coverage=coverage)
    result = api().evaluate_numeric_selection(src, ref, pure(src, [fact(), fact("n2")]))
    assert result.outcome == want
    assert checks(result)[-1] == ("n2", "presence", extra)
    missing = api().evaluate_numeric_selection(src, ref, pure(src, [fact("n2")]))
    assert missing.outcome == "reference_mismatch"
    assert checks(missing) == [("n1", "presence", "mismatch"), ("n2", "presence", extra)]


@pytest.mark.parametrize(
    "coverage,want", [("complete", "reference_match"), ("partial", "inconclusive")]
)
def test_empty_reference_and_empty_proposal_respect_coverage(coverage, want):
    src = document("A 10명.")
    result = api().evaluate_numeric_selection(src, reference(src, coverage=coverage), pure(src))
    assert result.outcome == want
    assert checks(result) == []
    assert (result.expected_facts, result.received_facts) == (0, 0)


@pytest.mark.parametrize("field", ["subject", "period", "condition", "kind", "status_text"])
def test_unassessed_role_prevents_match_even_if_actual_is_present(field):
    src, ref, proposal = rich()
    ref["facts"][0][field] = None if field == "kind" else rule(mode="unassessed")
    report = api().evaluate_numeric_selection(src, ref, proposal)
    assert report.outcome == "inconclusive"
    assert [c.field for c in report.checks if c.result == "unassessed"] == [field]
    ref["facts"][0]["subject"] = rule()
    if field != "subject":
        assert api().evaluate_numeric_selection(src, ref, proposal).outcome == "reference_mismatch"


def test_absent_rule_requires_actual_null():
    src, _, proposal = rich()
    result = api().evaluate_numeric_selection(src, reference(src, [ref_fact(src)]), proposal)
    assert [c.field for c in result.checks if c.result == "mismatch"] == [
        "subject",
        "period",
        "condition",
        "kind",
        "status_text",
    ]


def test_exact_alternatives_accept_listed_wider_text_but_not_unlisted_equivalent():
    src = document("우리 A 올해 10명 전망.")
    expected = ref_fact(src, subject=rule(src, "A", "우리 A"))
    ref = reference(src, [expected])
    assert (
        api()
        .evaluate_numeric_selection(src, ref, pure(src, [fact(subject=anchor("우리 A"))]))
        .outcome
        == "reference_match"
    )
    ref["facts"][0]["subject"] = rule(src, "A")
    report = api().evaluate_numeric_selection(src, ref, pure(src, [fact(subject=anchor("우리 A"))]))
    assert (report.outcome, checks(report)[1]) == (
        "reference_mismatch",
        ("n1", "subject", "mismatch"),
    )


def test_reference_accepts_repeated_phrase_positions_without_provider_uniqueness_constraint():
    src = document("A A 10명. A 20명.")
    ref = reference(
        src,
        [
            ref_fact(
                src,
                subject={
                    "mode": "one_of",
                    "alternatives": [
                        span(src, "A"),
                        span(src, "A", occurrence=1),
                        span(src, "A", occurrence=2),
                    ],
                },
            )
        ],
    )
    proposal = pure(src, [fact(subject=anchor("A", "s2"))])
    assert api().evaluate_numeric_selection(src, ref, proposal).outcome == "reference_match"
    ref["facts"][0]["subject"]["alternatives"] = [span(src, "A")]
    assert api().evaluate_numeric_selection(src, ref, proposal).outcome == "reference_mismatch"


def test_crlf_unicode_and_cross_sentence_reference_keep_original_codepoints():
    src = document("🧪 e\u0301 A 10명.\r\n 올해 조건 전망.")
    ref = reference(
        src, [ref_fact(src, subject=rule(src, "e\u0301 A"), condition=rule(src, ".\r\n 올해"))]
    )
    report = api().evaluate_numeric_selection(
        src, ref, pure(src, [fact(subject=anchor("e\u0301 A"))])
    )
    assert checks(report)[1:4] == [
        ("n1", "subject", "match"),
        ("n1", "period", "match"),
        ("n1", "condition", "mismatch"),
    ]
    for text in ["é A", ".\n 올해"]:
        bad = deepcopy(ref)
        target = "subject" if text.startswith("é") else "condition"
        bad["facts"][0][target]["alternatives"][0].update(text=text, end=2 + len(text))
        with pytest.raises(api().NumericSelectionEvaluationError):
            api().evaluate_numeric_selection(src, bad, None)


def test_check_order_follows_reference_then_unexpected_proposal_order():
    src = document("A 10명. B 20명. C 30명. D 40명.")
    ref = reference(src, [ref_fact(src, "n3"), ref_fact(src, "n1")])
    result = api().evaluate_numeric_selection(
        src, ref, pure(src, [fact("n4"), fact("n1"), fact("n2")])
    )
    assert checks(result) == [
        ("n3", "presence", "mismatch"),
        ("n1", "presence", "match"),
        ("n1", "subject", "match"),
        ("n1", "period", "match"),
        ("n1", "condition", "match"),
        ("n1", "kind", "match"),
        ("n1", "status_text", "match"),
        ("n4", "presence", "mismatch"),
        ("n2", "presence", "mismatch"),
    ]


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {"input_tokens": 0, "output_tokens": 0, "requests": 0},
        {"input_tokens": 90000, "output_tokens": 10000, "requests": 3},
    ],
)
def test_rejected_result_never_accepts_raw_facts_or_infers_free_usage(usage):
    src, ref, _ = rich()
    result = api().evaluate_numeric_selection(src, ref, None, rejected_usage=usage)
    assert result.outcome == "rejected"
    assert (result.received_facts, result.proposal_sha256, result.checks) == (None, None, ())
    assert result.expected_facts == 1
    assert (result.usage.model_dump() if result.usage else None) == usage
    if usage:
        known = KnownUsage(**usage)
        assert api().evaluate_numeric_selection(src, ref, None, rejected_usage=known) == result


def test_proposal_and_rejected_usage_are_contradictory_even_zero_usage():
    src, ref, proposal = rich()
    with pytest.raises(api().NumericSelectionEvaluationError):
        api().evaluate_numeric_selection(
            src,
            ref,
            proposal,
            rejected_usage={"input_tokens": 0, "output_tokens": 0, "requests": 0},
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "unknown",
        "cross_quote",
        "text",
        "offset",
        "bool",
        "duplicate_alternative",
        "too_many",
        "missing_field",
        "absent_with_alternatives",
        "empty_one_of",
        "extra",
        "bad_mode",
        "too_many_facts",
        "stale_index",
    ],
)
def test_invalid_reference_is_rejected_before_comparison_or_rejected_report(mutation):
    src = document("A 10명.", "B 20명.")
    ref = reference(src, [ref_fact(src, subject=rule(src, "A"))])
    row = ref["facts"][0]
    alternatives = row["subject"]["alternatives"]
    if mutation == "duplicate":
        ref["facts"].append(deepcopy(row))
    elif mutation == "unknown":
        row["candidate_id"] = "synthetic-secret-id"
    elif mutation == "cross_quote":
        row["subject"] = rule(src, "B", citation=1)
    elif mutation == "text":
        alternatives[0]["text"] = "Z"
    elif mutation == "offset":
        alternatives[0].update(start=1, end=2)
    elif mutation == "bool":
        alternatives[0]["start"] = False
    elif mutation == "duplicate_alternative":
        alternatives.append(deepcopy(alternatives[0]))
    elif mutation == "too_many":
        row["subject"] = rule(src, "A", " ", "10", "명", ".")
    elif mutation == "missing_field":
        del row["kind"]
    elif mutation == "absent_with_alternatives":
        row["subject"]["mode"] = "absent"
    elif mutation == "empty_one_of":
        row["subject"]["alternatives"] = []
    elif mutation == "extra":
        alternatives[0]["synthetic-secret-id"] = "synthetic-private-text"
    elif mutation == "bad_mode":
        row["subject"]["mode"] = "truth"
    elif mutation == "too_many_facts":
        ref["facts"] = [deepcopy(row)] * 13
    elif mutation == "stale_index":
        ref["candidate_index"]["candidates"].pop()
    with pytest.raises(api().NumericSelectionEvaluationError) as error:
        api().evaluate_numeric_selection(src, ref, None)
    assert str(error.value) == "Invalid numeric selection evaluation input"
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__


@pytest.mark.parametrize(
    "target", ["reference", "rule", "span", "proposal", "proposal_span", "usage"]
)
@pytest.mark.parametrize("attack", ["unchecked_extra", "subclass_extra"])
def test_nested_unchecked_and_declared_subclass_extras_are_not_dropped(target, attack):
    mod = api()
    src, raw_ref, proposal = rich()
    ref = mod.NumericSelectionReference.model_validate_json(json.dumps(raw_ref), strict=True)
    usage = KnownUsage(input_tokens=30, output_tokens=10, requests=1)
    objects = {
        "reference": ref,
        "rule": ref.facts[0].subject,
        "span": ref.facts[0].subject.alternatives[0],
        "proposal": proposal,
        "proposal_span": proposal.facts[0].subject.span,
        "usage": usage,
    }
    obj = objects[target]
    if attack == "unchecked_extra":
        changed = obj.model_copy(update={"synthetic_secret": "synthetic-private-text"})
    else:
        subclass = create_model("SyntheticExtra", __base__=type(obj), synthetic_secret=(str, ...))
        changed = subclass(**obj.model_dump(), synthetic_secret="synthetic-private-text")
    if target == "reference":
        ref = changed
    elif target in {"rule", "span"}:
        changed_rule = (
            changed
            if target == "rule"
            else ref.facts[0].subject.model_copy(update={"alternatives": (changed,)})
        )
        ref = ref.model_copy(
            update={"facts": (ref.facts[0].model_copy(update={"subject": changed_rule}),)}
        )
    elif target == "proposal":
        proposal = changed
    elif target == "proposal_span":
        changed_anchor = proposal.facts[0].subject.model_copy(update={"span": changed})
        proposal = proposal.model_copy(
            update={"facts": (proposal.facts[0].model_copy(update={"subject": changed_anchor}),)}
        )
    else:
        usage = changed
    with pytest.raises(mod.NumericSelectionEvaluationError):
        mod.evaluate_numeric_selection(
            src,
            ref,
            None if target == "usage" else proposal,
            rejected_usage=usage if target == "usage" else None,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "bool_usage",
        "bool_offset",
        "text",
        "offset",
        "prompt_hash",
        "missing_candidate",
        "duplicate_fact",
        "raw_facts",
        "status",
    ],
)
def test_unchecked_proposal_tampering_cannot_become_a_mismatch_report(mutation):
    src, ref, proposal = rich()
    raw = proposal.model_dump(mode="json")
    if mutation == "bool_usage":
        raw["usage"]["input_tokens"] = True
    elif mutation == "bool_offset":
        raw["facts"][0]["subject"]["span"]["start"] = True
    elif mutation == "text":
        raw["facts"][0]["subject"]["span"]["text"] = "Z"
    elif mutation == "offset":
        raw["facts"][0]["subject"]["span"].update(start=1, end=2)
    elif mutation == "prompt_hash":
        raw["prompt_sha256"] = "0" * 64
    elif mutation == "missing_candidate":
        raw["candidate_index"]["candidates"].pop()
    elif mutation == "duplicate_fact":
        raw["facts"].append(deepcopy(raw["facts"][0]))
    elif mutation == "raw_facts":
        raw = {"facts": [fact()]}
    elif mutation == "status":
        raw["status"] = "reviewed"
    with pytest.raises(api().NumericSelectionEvaluationError):
        api().evaluate_numeric_selection(src, ref, raw)


@pytest.mark.parametrize(
    "mutation",
    ["stale_snapshot", "invalid_metadata", "stale_quote", "subclass_extra", "unchecked_extra"],
)
def test_current_source_is_revalidated_even_on_rejection(mutation):
    src, ref, _ = rich()
    sid, bundle, presentation = src
    if mutation == "stale_snapshot":
        sid = uuid4()
        presentation = presentation.model_copy(update={"snapshot_id": sid})
    elif mutation == "invalid_metadata":
        presentation = presentation.model_copy(update={"title": ""})
    elif mutation == "stale_quote":
        bundle = bundle.model_copy(
            update={
                "citations": (
                    bundle.citations[0].model_copy(
                        update={
                            "selector": bundle.citations[0].selector.model_copy(
                                update={"quote": "tampered"}
                            )
                        }
                    ),
                )
            }
        )
    else:
        item = bundle.citations[0]
        if mutation == "subclass_extra":
            subclass = create_model(
                "SyntheticCitation", __base__=type(item), extra_field=(str, ...)
            )
            item = subclass(**item.model_dump(), extra_field="synthetic-private-text")
        else:
            item = item.model_copy(update={"extra_field": "synthetic-private-text"})
        bundle = bundle.model_copy(update={"citations": (item,)})
    with pytest.raises(api().NumericSelectionEvaluationError):
        api().evaluate_numeric_selection((sid, bundle, presentation), ref, None)


@pytest.mark.parametrize(
    "field,value",
    [("input_tokens", True), ("output_tokens", -1), ("requests", 1.0), ("requests", "1")],
)
def test_rejected_usage_is_strict_and_never_coerced(field, value):
    src, ref, _ = rich()
    usage = {"input_tokens": 100, "output_tokens": 30, "requests": 1, field: value}
    with pytest.raises(api().NumericSelectionEvaluationError):
        api().evaluate_numeric_selection(src, ref, None, rejected_usage=usage)


def test_model_and_json_inputs_hash_canonical_checked_json_and_report_has_no_text():
    src, ref, proposal = rich()
    mod = api()
    checked_ref = mod.NumericSelectionReference.model_validate_json(json.dumps(ref), strict=True)
    expected_ref_hash = sha256(
        json.dumps(
            checked_ref.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    ).hexdigest()
    expected_proposal_hash = sha256(
        json.dumps(
            proposal.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    ).hexdigest()
    report = mod.evaluate_numeric_selection(src, checked_ref, proposal)
    assert (report.reference_sha256, report.proposal_sha256) == (
        expected_ref_hash,
        expected_proposal_hash,
    )
    assert (
        mod.evaluate_numeric_selection(
            src, dict(reversed(list(ref.items()))), proposal.model_dump(mode="json")
        )
        == report
    )
    assert set(report.model_dump()) == {
        "profile",
        "scope",
        "outcome",
        "reference_sha256",
        "proposal_sha256",
        "expected_facts",
        "received_facts",
        "checks",
        "usage",
    }
    assert all(
        set(row) == {"candidate_id", "field", "result"} for row in report.model_dump()["checks"]
    )
    assert "올해" not in report.model_dump_json()
    ref["candidate_set"] = "partial"
    assert mod.evaluate_numeric_selection(src, ref, proposal).reference_sha256 != expected_ref_hash


def test_import_and_run_block_external_io_except_pydantic_plugin_configuration(monkeypatch):
    src, ref, proposal = rich()
    name = "issuedigest_agents.numeric_selection_evaluation"
    assert importlib.util.find_spec(name) is not None, "Missing pure numeric selection evaluator"
    spec = importlib.util.find_spec(name)
    module = importlib.util.module_from_spec(spec)

    def forbidden(*args, **kwargs):
        raise AssertionError("Evaluator attempted external I/O")

    def plugin_configuration(name, default=None):
        # Installed Pydantic checks this switch when it creates strict model classes.
        # Return a fixed value without reading the process environment or any key.
        if name != "PYDANTIC_DISABLE_PLUGINS":
            forbidden()
        return None

    with monkeypatch.context() as patch:
        for obj, attr in [
            (builtins, "open"),
            (io, "open"),
            (Path, "open"),
            (os, "getenv"),
            (type(os.environ), "__getitem__"),
            (socket, "socket"),
            (socket, "create_connection"),
        ]:
            patch.setattr(obj, attr, forbidden)
        patch.setattr(os, "getenv", plugin_configuration)
        spec.loader.exec_module(module)
        assert module.evaluate_numeric_selection(src, ref, proposal).outcome == "reference_match"
        assert module.evaluate_numeric_selection(src, ref, None).outcome == "rejected"
