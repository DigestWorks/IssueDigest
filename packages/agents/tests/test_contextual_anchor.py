"""Synthetic exact contextual locations; provenance never certifies semantic correctness."""

import builtins
import importlib
import importlib.util
import io
import json
import os
import socket
import sys
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import Field, create_model
from test_numeric_evidence import document


@pytest.fixture(scope="module", autouse=True)
def restore_new_module_imports():
    # Frozen candidate/selection tests reload modules. Keep this test's first imports
    # from retaining their old Pydantic classes in modules used by later tests.
    names = (
        "issuedigest_agents.contextual_anchor",
        "issuedigest_agents.numeric_selection_evaluation",
        "issuedigest_agents.numeric_selection",
    )
    introduced = [name for name in names if name not in sys.modules]
    yield
    for name in introduced:
        sys.modules.pop(name, None)


def api():
    name = "issuedigest_agents.contextual_anchor"
    assert importlib.util.find_spec(name) is not None, "Missing pure contextual anchor resolver"
    return importlib.import_module(name)


def anchor(text="전월비", context_text=None, sentence_id="s1"):
    return {"sentence_id": sentence_id, "text": text, "context_text": context_text}


def repeated():
    return document("🧪 취업자 전월비 10명 증가, 실업자 전월비 20명 감소.")


def test_explicit_contexts_select_each_repeated_short_span_without_expansion():
    mod = api()
    src = repeated()
    left = mod.resolve_contextual_anchor(src, anchor(context_text="취업자 전월비 10명"))
    right = mod.resolve_contextual_anchor(src, anchor(context_text="실업자 전월비 20명"))
    assert (left.resolved.span.start, left.resolved.span.end) == (6, 9)
    assert (right.resolved.span.start, right.resolved.span.end) == (22, 25)
    assert left.resolved.span.text == right.resolved.span.text == "전월비"
    assert left.resolved.sentence_id == right.resolved.sentence_id == "s1"
    assert left.resolved.span.citation_id == str(src[1].citations[0].citation_id)
    assert (left.profile, left.status) == ("contextual-anchor-v1", "unreviewed")
    assert left.snapshot_id == src[0]
    assert left.workspace_id == src[2].workspace_id
    from issuedigest_agents.numeric_candidates import build_numeric_candidates

    assert left.source_sha256 == build_numeric_candidates(src).source_sha256
    assert set(left.model_dump()) == {
        "profile",
        "status",
        "snapshot_id",
        "workspace_id",
        "source_sha256",
        "anchor",
        "resolved",
    }
    assert mod.validate_contextual_anchor(src, left) == left
    assert mod.validate_contextual_anchor(src, right) == right


def test_no_context_keeps_unique_sentence_rule_and_context_is_required_nullable():
    mod = api()
    src = repeated()
    with pytest.raises(mod.ContextualAnchorError):
        mod.resolve_contextual_anchor(src, anchor())
    result = mod.resolve_contextual_anchor(src, anchor("취업자"))
    assert (result.resolved.span.start, result.resolved.span.end) == (2, 5)
    assert result.anchor.context_text is None
    assert isinstance(result.anchor, mod.SentenceAnchor)
    missing = anchor("취업자")
    del missing["context_text"]
    with pytest.raises(mod.ContextualAnchorError):
        mod.resolve_contextual_anchor(src, missing)


@pytest.mark.parametrize(
    "quote,text,context",
    [
        ("aaaa", "a", "aa"),  # Overlapping context occurrences.
        ("X aaaa Y", "aa", "X aaaa"),  # Overlapping phrase occurrences inside unique context.
        ("X ababa Y", "aba", "ababa"),
        ("X A B A", "A", "A B A"),
        ("A left A right", "A", "absent"),
        ("A left A right", "A", "left"),
        ("A 10명. B 20명.", "명", "명. B"),
        ("A\r\nB", "B", "\r\nB"),
        ("e\u0301 value", "é", "e\u0301 value"),
        ("A  B", "A B", "A  B"),
        ("A  B", "B", "A B"),
        ("X aaaa Y", "aa", None),
    ],
)
def test_missing_repeated_overlapping_normalized_or_cross_sentence_input_rejects(
    quote, text, context
):
    mod = api()
    with pytest.raises(mod.ContextualAnchorError):
        mod.resolve_contextual_anchor(document(quote), anchor(text, context))


@pytest.mark.parametrize(
    "quote,text,context,sentence,start,end",
    [
        ("A\r\n🧪 e\u0301  A  B.", "e\u0301", "🧪 e\u0301  A", "s2", 5, 7),
        ("A\r\n🧪 e\u0301  A  B.", " A  ", "e\u0301  A  B", "s2", 8, 12),
        ("abcab", "ab", "bca", "s1", 0, 0),
        ("ababa", "aba", "abab", "s1", 0, 3),
        ("ababa", "aba", "baba", "s1", 2, 5),
        ("abc", "abc", "abc", "s1", 0, 3),
        ("abc", "a", "ab", "s1", 0, 1),
        ("abc", "c", "bc", "s1", 2, 3),
        ("A\r\nB", "A\r\n", "A\r\n", "s1", 0, 3),
        ("x" + "a" * 999, "x" + "a" * 999, "x" + "a" * 999, "s1", 0, 1000),
        ("🧪" * 1000, "🧪" * 1000, "🧪" * 1000, "s1", 0, 1000),
    ],
)
def test_exact_codepoints_whitespace_boundaries_and_overlapping_distinct_contexts(
    quote, text, context, sentence, start, end
):
    mod = api()
    if start == end:
        # A phrase extending past a context boundary is absent from that context.
        with pytest.raises(mod.ContextualAnchorError):
            mod.resolve_contextual_anchor(document(quote), anchor(text, context, sentence))
        return
    result = mod.resolve_contextual_anchor(document(quote), anchor(text, context, sentence))
    assert (result.resolved.span.start, result.resolved.span.end) == (start, end)
    assert result.resolved.span.text == quote[start:end] == text


def test_sentence_and_quote_are_explicit_and_never_inferred():
    mod = api()
    src = document("A shared.", "B shared.")
    result = mod.resolve_contextual_anchor(src, anchor("shared", "B shared", "s2"))
    assert result.resolved.span.citation_id == str(src[1].citations[1].citation_id)
    assert (result.resolved.span.start, result.resolved.span.end) == (2, 8)
    for data in [anchor("shared", "B shared"), anchor("shared", "A shared.\nB", "s2")]:
        with pytest.raises(mod.ContextualAnchorError):
            mod.resolve_contextual_anchor(src, data)


@pytest.mark.parametrize("field", ["text", "context_text"])
@pytest.mark.parametrize("value", ["", " \t\r\n", "x" * 1001, True, 1, [], "\ud800"])
def test_bounded_nonblank_exact_strings_are_strict(field, value):
    mod = api()
    with pytest.raises(mod.ContextualAnchorError):
        mod.resolve_contextual_anchor(repeated(), {**anchor(), field: value})


@pytest.mark.parametrize(
    "update", [{"sentence_id": True}, {"sentence_id": "s99"}, {"text": None}, {"start": 0}]
)
def test_unknown_sentence_types_and_extra_input_are_rejected(update):
    mod = api()
    with pytest.raises(mod.ContextualAnchorError):
        mod.resolve_contextual_anchor(repeated(), {**anchor("취업자"), **update})


def test_typed_input_and_json_dict_roundtrip_keep_exact_anchor_and_unreviewed_semantics():
    mod = api()
    src = repeated()
    # Caller may semantically choose the wrong group: only exact source linkage is established.
    data = mod.ContextualAnchor(**anchor(context_text="실업자 전월비 20명"))
    result = mod.resolve_contextual_anchor(src, data)
    assert result.anchor == data
    assert result.status == "unreviewed"
    assert mod.validate_contextual_anchor(src, json.loads(result.model_dump_json())) == result
    assert mod.ContextualAnchorResolution.model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValueError):
        result.status = "reviewed"


@pytest.mark.parametrize(
    "path,value",
    [
        (("profile",), "numeric-frame-v1"),
        (("status",), "reviewed"),
        (("snapshot_id",), str(uuid4())),
        (("workspace_id",), str(uuid4())),
        (("source_sha256",), "0" * 64),
        (("source_sha256",), "A" * 64),
        (("source_sha256",), True),
        (("anchor", "context_text"), "실업자 전월비 20명"),
        (("anchor", "text"), "취업자"),
        (("anchor", "secret"), "synthetic-private-text"),
        (("resolved", "sentence_id"), "s2"),
        (("resolved", "span", "citation_id"), str(uuid4())),
        (("resolved", "span", "start"), 23),
        (("resolved", "span", "start"), False),
        (("resolved", "span", "end"), 26),
        (("resolved", "span", "text"), "실업자"),
        (("resolved", "span", "secret"), "synthetic-private-text"),
        (("resolved", "secret"), "synthetic-private-text"),
        (("secret",), "synthetic-private-text"),
    ],
)
def test_full_reconstruction_rejects_every_forged_output_field(path, value):
    mod = api()
    src = repeated()
    result = mod.resolve_contextual_anchor(src, anchor(context_text="취업자 전월비 10명"))
    raw = result.model_dump(mode="json")
    target = raw
    for field in path[:-1]:
        target = target[field]
    target[path[-1]] = value
    with pytest.raises(mod.ContextualAnchorError) as error:
        mod.validate_contextual_anchor(src, raw)
    assert str(error.value) == "Invalid contextual anchor resolution"
    assert error.value.__suppress_context__


@pytest.mark.parametrize(
    "field", ["snapshot_id", "workspace_id", "source_sha256", "anchor", "resolved"]
)
def test_missing_required_output_rejects(field):
    mod = api()
    src = repeated()
    raw = mod.resolve_contextual_anchor(src, anchor("취업자")).model_dump(mode="json")
    del raw[field]
    with pytest.raises(mod.ContextualAnchorError):
        mod.validate_contextual_anchor(src, raw)


def hidden(item):
    subclass = create_model(
        "SyntheticHidden", __base__=type(item), secret=(str, Field(exclude=True))
    )
    return subclass(**item.model_dump(), secret="synthetic-private-text")


@pytest.mark.parametrize("kind", ["subclass", "extra", "pydantic_extra"])
@pytest.mark.parametrize(
    "target",
    [
        "input",
        "output",
        "output_anchor",
        "resolved",
        "span",
        "bundle",
        "document",
        "representation",
        "citation",
        "selector",
        "presentation",
    ],
)
def test_actual_models_and_hidden_fields_are_checked_before_dump(kind, target):
    mod = api()
    src = repeated()
    data = mod.ContextualAnchor(**anchor("취업자"))
    result = mod.resolve_contextual_anchor(src, data)

    def forge(item):
        if kind == "subclass":
            return hidden(item)
        item = item.model_copy()
        if kind == "extra":
            item.__dict__["secret"] = "synthetic-private-text"
        else:
            object.__setattr__(item, "__pydantic_extra__", {"secret": "synthetic-private-text"})
        return item

    if target == "input":
        data = forge(data)
    elif target == "output":
        result = forge(result)
    elif target == "output_anchor":
        result = result.model_copy(update={"anchor": forge(result.anchor)})
    elif target == "resolved":
        result = result.model_copy(update={"resolved": forge(result.resolved)})
    elif target == "span":
        resolved = result.resolved.model_copy(update={"span": forge(result.resolved.span)})
        result = result.model_copy(update={"resolved": resolved})
    else:
        sid, bundle, presentation = src
        if target == "bundle":
            bundle = forge(bundle)
        elif target == "presentation":
            presentation = forge(presentation)
        elif target in {"document", "representation"}:
            bundle = bundle.model_copy(update={target: forge(getattr(bundle, target))})
        else:
            citation = bundle.citations[0]
            citation = (
                forge(citation)
                if target == "citation"
                else citation.model_copy(update={"selector": forge(citation.selector)})
            )
            bundle = bundle.model_copy(update={"citations": (citation,)})
        src = sid, bundle, presentation
    with pytest.raises(mod.ContextualAnchorError):
        if target == "input":
            mod.resolve_contextual_anchor(src, data)
        else:
            mod.validate_contextual_anchor(src, result)
    if target in {"bundle", "document", "representation", "citation", "selector", "presentation"}:
        with pytest.raises(mod.ContextualAnchorError):
            mod.resolve_contextual_anchor(src, data)


@pytest.mark.parametrize("method", ["model_construct", "model_copy"])
@pytest.mark.parametrize("target", ["input", "output", "resolved", "span"])
def test_unchecked_model_construction_and_copy_are_strictly_revalidated(method, target):
    mod = api()
    src = repeated()
    data = mod.ContextualAnchor(**anchor("취업자"))
    result = mod.resolve_contextual_anchor(src, data)

    def forge(item, update):
        if method == "model_construct":
            return type(item).model_construct(**{**item.model_dump(), **update})
        return item.model_copy(update=update)

    if target == "input":
        data = forge(data, {"context_text": True})
    elif target == "output":
        result = forge(result, {"status": "reviewed"})
    elif target == "resolved":
        result = result.model_copy(
            update={"resolved": forge(result.resolved, {"sentence_id": True})}
        )
    else:
        resolved = result.resolved.model_copy(
            update={"span": forge(result.resolved.span, {"start": False})}
        )
        result = result.model_copy(update={"resolved": resolved})
    with pytest.raises(mod.ContextualAnchorError):
        if target == "input":
            mod.resolve_contextual_anchor(src, data)
        else:
            mod.validate_contextual_anchor(src, result)


@pytest.mark.parametrize(
    "mutation",
    [
        "snapshot",
        "workspace",
        "other_source",
        "quote",
        "valid_changed_quote",
        "invalid_metadata",
        "dict_source",
    ],
)
def test_current_source_identity_hash_and_canonical_structure_are_rechecked(mutation):
    mod = api()
    src = repeated()
    data = anchor("취업자")
    result = mod.resolve_contextual_anchor(src, data)
    sid, bundle, presentation = src
    if mutation == "snapshot":
        sid = uuid4()
        presentation = presentation.model_copy(update={"snapshot_id": sid})
    elif mutation == "workspace":
        wid = uuid4()
        bundle = bundle.model_copy(
            update={"document": bundle.document.model_copy(update={"workspace_id": wid})}
        )
        presentation = presentation.model_copy(update={"workspace_id": wid})
    elif mutation == "other_source":
        sid, bundle, presentation = repeated()
    elif mutation == "quote":
        bundle = deepcopy(bundle)
        citation = bundle.citations[0]
        bundle = bundle.model_copy(
            update={
                "citations": (
                    citation.model_copy(
                        update={
                            "selector": citation.selector.model_copy(
                                update={"quote": "synthetic-forged"}
                            )
                        }
                    ),
                )
            }
        )
    elif mutation == "valid_changed_quote":
        raw = bundle.model_dump(mode="json")
        text = raw["representation"]["text"].replace("10명", "11명")
        raw["representation"].update(text=text, text_sha256=sha256(text.encode()).hexdigest())
        raw["citations"][0]["selector"]["quote"] = text
        bundle = type(bundle).model_validate(raw)
    elif mutation == "invalid_metadata":
        presentation = presentation.model_copy(update={"title": ""})
    else:
        bundle = bundle.model_dump(mode="json")
    changed = sid, bundle, presentation
    with pytest.raises(mod.ContextualAnchorError):
        mod.validate_contextual_anchor(changed, result)
    if mutation in {"quote", "invalid_metadata", "dict_source"}:
        with pytest.raises(mod.ContextualAnchorError):
            mod.resolve_contextual_anchor(changed, data)
    if mutation == "valid_changed_quote":
        current = mod.resolve_contextual_anchor(changed, data)
        assert current.snapshot_id == result.snapshot_id
        assert current.workspace_id == result.workspace_id
        assert current.resolved == result.resolved
        assert current.source_sha256 != result.source_sha256


def test_source_caps_remain_owned_by_existing_candidate_builder():
    mod = api()
    for src in [document(*["X" for _ in range(21)]), document("X" * 12001)]:
        with pytest.raises(mod.ContextualAnchorError):
            mod.resolve_contextual_anchor(src, anchor("X"))


def test_import_and_apis_perform_no_external_io_except_pydantic_plugin_switch(monkeypatch):
    import openai
    import pydantic_ai

    mod = api()
    src = repeated()
    spec = importlib.util.find_spec(mod.__name__)
    assert spec is not None
    fresh = importlib.util.module_from_spec(spec)

    def forbidden(*args, **kwargs):
        raise AssertionError("Contextual anchor attempted external I/O")

    def plugin_switch(key, default=None):
        if key != "PYDANTIC_DISABLE_PLUGINS":
            forbidden()
        return None

    with monkeypatch.context() as patch:
        for obj, name in [
            (builtins, "open"),
            (io, "open"),
            (Path, "open"),
            (type(os.environ), "__getitem__"),
            (socket, "socket"),
            (socket, "create_connection"),
            (pydantic_ai, "Agent"),
            (openai.AsyncOpenAI, "__init__"),
            (openai.OpenAI, "__init__"),
        ]:
            patch.setattr(obj, name, forbidden)
        patch.setattr(os, "getenv", plugin_switch)
        spec.loader.exec_module(fresh)
        result = fresh.resolve_contextual_anchor(src, anchor(context_text="취업자 전월비 10명"))
        assert fresh.validate_contextual_anchor(src, result).status == "unreviewed"
        with pytest.raises(fresh.ContextualAnchorError) as error:
            fresh.resolve_contextual_anchor(src, anchor("synthetic-private-text"))
        assert str(error.value) == "Invalid contextual anchor input"
        assert error.value.__suppress_context__
