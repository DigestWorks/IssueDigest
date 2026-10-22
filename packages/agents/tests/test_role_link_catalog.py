"""Synthetic surface inventories preserve locations; they do not establish semantics."""

import importlib
import importlib.util
import json
import re
from copy import deepcopy
from hashlib import sha256

import pytest
from pydantic import BaseModel, Field, create_model
from test_numeric_evidence import document
from test_semantic_role_audit_contract import generation
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


def api():
    name = "issuedigest_agents.role_link_catalog"
    assert importlib.util.find_spec(name) is not None, "Missing pure role link catalog"
    return importlib.import_module(name)


def original(*quotes, numbers=()):
    # The existing balanced generation contract requires at least one candidate.
    if not any(re.search(r"[0-9]", quote) for quote in quotes):
        quotes = (*quotes[:-1], quotes[-1] + " 3명.")
    src = document(*quotes)
    data = dict(contexts=[], events=[], bindings=[], relations=[])
    if numbers:
        data["contexts"] = [
            dict(
                id="c1",
                event="e1",
                entity=None,
                scopes=[],
                period=None,
                status="unknown",
                condition=None,
                purpose=None,
                basis=None,
                baseline=None,
            )
        ]
        data["events"] = [
            dict(id="e1", kind="unknown", actor=None, predicate=None, tense="unknown")
        ]
        data["bindings"] = [
            dict(number=n, context="c1", scopes=[], status_sentence=None, change=None)
            for n in numbers
        ]
    return src, generation(src, data)


def test_literal_projection_keeps_full_packet_and_required_order_but_hides_origins():
    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    result = mod.build_role_link_catalog(src, gen)
    packet = mod.role_link_packet(src, gen)
    table = importlib.import_module("issuedigest_agents.role_table_packet")
    assert packet == dict(
        profile="role-link-review-v1",
        source_packet=table.build_role_table_packet(src, gen),
        hint_table=dict(
            columns=["id", "quote_id", "s", "t", "c"], rows=[["m1", "q1", "s1", "현재", None]]
        ),
        domains=[dict(quote_id="q1", numbers=["n1"], hints=["m1"])],
        role_order="STOREIBP",
        role_legend=dict(
            S="measurement_scope",
            T="measurement_period",
            O="operator",
            R="reporter",
            E="entity_qualifier",
            I="programme_identity",
            B="comparison_baseline",
            P="purpose",
        ),
        state_legend={"-": "explicitly_unrelated", "?": "linkage_uncertain", "_": "not_reviewed"},
        source_inventory_exhaustive=False,
    )
    assert result.generation == gen

    def canonical(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    assert (
        result.generation_sha256
        == sha256(canonical(gen.model_dump(mode="json")).encode()).hexdigest()
    )
    assert (
        result.source_packet_sha256
        == sha256(canonical(packet["source_packet"]).encode()).hexdigest()
    )
    assert mod.validate_role_link_catalog(src, result) == result
    assert mod.validate_role_link_catalog(src, json.loads(result.model_dump_json())) == result
    encoding = mod.role_link_encoding_metadata()
    assert encoding["encoding_version"] == "role-link-matrix-v1"
    assert encoding["role_order"] == "STOREIBP"
    encoding["role_legend"]["S"] = "altered"
    packet["role_legend"]["S"] = "altered"
    assert mod.role_link_encoding_metadata()["role_legend"]["S"] == "measurement_scope"


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "서울·부산",
            [("서울", ("dot_member",)), ("서울·부산", ("dot_list",)), ("부산", ("dot_member",))],
        ),
        (
            "2026년간 2년까지 3년부터 4년",
            [
                ("2026년간", ("year_surface",)),
                ("2년까지", ("year_surface",)),
                ("3년부터", ("year_surface",)),
                ("4년", ("year_surface",)),
            ],
        ),
        (
            "올해 3월부터 전년도 대비 현재",
            [
                ("올해 3월부터", ("relative_time_surface",)),
                ("전년도", ("place_suffix_surface",)),
                ("전년도 대비", ("relative_time_surface",)),
                ("현재", ("relative_time_surface",)),
            ],
        ),
        (
            "합성부는 합성청에서 합성공단으로 합성위원회가 합성정부의 합성대학에",
            [
                (word, ("institution_suffix_surface",))
                for word in ("합성부", "합성청", "합성공단", "합성위원회", "합성정부", "합성대학")
            ],
        ),
        (
            "합성특별자치도는 합성특별시가 합성광역시에 합성도로 합성시에서 합성군의 합성구와",
            [
                (word, ("place_suffix_surface",))
                for word in (
                    "합성특별자치도",
                    "합성특별시",
                    "합성광역시",
                    "합성도",
                    "합성시",
                    "합성군",
                    "합성구",
                )
            ],
        ),
        (
            "'사업' ‘계획’ ｢목적｣",
            [(word, ("quoted_phrase",)) for word in ("'사업'", "‘계획’", "｢목적｣")],
        ),
        (
            "전년도·현재",
            [
                ("전년도", ("dot_member", "place_suffix_surface", "relative_time_surface")),
                ("전년도·현재", ("dot_list",)),
                ("현재", ("dot_member", "relative_time_surface")),
            ],
        ),
    ],
)
def test_exact_lexical_patterns_and_same_position_origin_dedup(text, expected):
    mod = api()
    src, gen = original(text)
    result = mod.build_role_link_catalog(src, gen)
    assert [(h.anchor.t, h.origins) for h in result.hints] == expected
    assert [h.hint_id for h in result.hints] == [f"m{i}" for i in range(1, len(expected) + 1)]
    for h in result.hints:
        assert text[h.span.start : h.span.end] == h.anchor.t


def test_repeated_overlapping_phrase_uses_shortest_context_then_left_position():
    mod = api()
    src, gen = original("현재현재")
    result = mod.build_role_link_catalog(src, gen)
    assert [(h.span.start, h.span.end, h.anchor.c) for h in result.hints] == [
        (0, 2, "현재현"),
        (2, 4, "재현재"),
    ]


def test_domains_follow_quote_and_binding_order_including_empty_domains_and_sentences():
    mod = api()
    src, gen = original("\n현재 3명. 4명.\n", "올해 5명.", "설명만.", numbers=("n3", "n2", "n1"))
    result = mod.build_role_link_catalog(src, gen)
    assert [d.model_dump(mode="json") for d in result.domains] == [
        dict(quote_id="q1", numbers=["n2", "n1"], hints=["m1"]),
        dict(quote_id="q2", numbers=["n3"], hints=["m2"]),
        dict(quote_id="q3", numbers=[], hints=[]),
    ]
    assert result.hints[0].anchor.s == "s2"
    assert result.hints[0].span.start == 1
    for text in ("설명만.", "현재 3명."):
        empty_src, empty_gen = original(text)
        body = mod.role_link_packet(empty_src, empty_gen)
        assert body["domains"][0]["numbers"] == []
        assert (
            "".join(r[1] for r in body["source_packet"]["quotes"][0]["sentences"]["rows"])
            == empty_src[1].citations[0].selector.quote
        )


@pytest.mark.parametrize("count,reason", [(24, None), (25, "candidate_overflow")])
def test_per_quote_hint_limit_is_inclusive_and_does_not_truncate(count, reason):
    mod = api()
    src, gen = original(" ".join(f"'항목{chr(65 + i)}'" for i in range(count)))
    if reason:
        with pytest.raises(mod.RoleLinkCatalogError) as caught:
            mod.build_role_link_catalog(src, gen)
        assert caught.value.reason == reason
    else:
        assert len(mod.build_role_link_catalog(src, gen).hints) == count


@pytest.mark.parametrize("length,reason", [(998, None), (999, "unlocatable_hint")])
def test_anchor_length_limit_is_exact_and_error_is_sanitized(length, reason):
    mod = api()
    text = "'" + "가" * length + "'"
    src, gen = original(text)
    if reason:
        with pytest.raises(mod.RoleLinkCatalogError) as caught:
            mod.build_role_link_catalog(src, gen)
        assert caught.value.reason == reason
        assert text not in str(caught.value)
        assert caught.value.__cause__ is None
    else:
        assert mod.build_role_link_catalog(src, gen).hints[0].anchor.t == text


def test_overflow_checked_before_unlocatable_hint_and_applies_to_each_quote():
    mod = api()
    src, gen = original("'" + "가" * 1001 + "' " + " ".join("현재" for _ in range(24)))
    with pytest.raises(mod.RoleLinkCatalogError) as caught:
        mod.build_role_link_catalog(src, gen)
    assert caught.value.reason == "candidate_overflow"
    quote = " ".join(f"'항목{chr(65 + i)}'" for i in range(24))
    src, gen = original(quote, quote)
    assert len(mod.build_role_link_catalog(src, gen).hints) == 48


def test_unresolvable_repeated_anchor_fails_instead_of_omitting():
    mod = api()
    src, gen = original("'" + "a" * 998 + "'" + "'" + "a" * 998 + "'")
    with pytest.raises(mod.RoleLinkCatalogError) as caught:
        mod.build_role_link_catalog(src, gen)
    assert caught.value.reason == "unlocatable_hint"


class StringSubclass(str):
    pass


class ListSubclass(list):
    pass


class DictSubclass(dict):
    pass


class TupleSubclass(tuple):
    pass


@pytest.mark.parametrize(
    "mutation",
    [
        "profile",
        "rules_version",
        "source_inventory_exhaustive",
        "generation_sha256",
        "source_packet_sha256",
        "rules_sha256",
        "hint_id",
        "quote_id",
        "span",
        "origins",
        "anchor",
        "numbers",
        "hints",
        "domain_quote",
        "missing_hint",
        "extra_domain",
    ],
)
def test_reconstruction_rejects_all_catalog_and_domain_drift(mutation):
    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    body = mod.build_role_link_catalog(src, gen).model_dump(mode="json")
    if mutation in (
        "profile",
        "rules_version",
        "generation_sha256",
        "source_packet_sha256",
        "rules_sha256",
    ):
        body[mutation] = "altered"
    elif mutation == "source_inventory_exhaustive":
        body[mutation] = True
    elif mutation in ("hint_id", "quote_id"):
        body["hints"][0][mutation] = "other"
    elif mutation == "span":
        body["hints"][0]["span"]["start"] = 1
    elif mutation == "origins":
        body["hints"][0]["origins"] = ["year_surface"]
    elif mutation == "anchor":
        body["hints"][0]["anchor"]["c"] = "현재 3명"
    elif mutation in ("numbers", "hints"):
        body["domains"][0][mutation] = []
    elif mutation == "domain_quote":
        body["domains"][0]["quote_id"] = "q2"
    elif mutation == "missing_hint":
        body["hints"] = []
    elif mutation == "extra_domain":
        body["domains"].append(deepcopy(body["domains"][0]))
    with pytest.raises(mod.RoleLinkCatalogError):
        mod.validate_role_link_catalog(src, body)


@pytest.mark.parametrize("mode", ["actual", "raw"])
@pytest.mark.parametrize(
    "mutation",
    [
        "missing_profile",
        "missing_rules",
        "missing_flag",
        "missing_generation_marker",
        "missing_index_marker",
        "missing_nullable",
        "missing_default",
        "string_subclass",
        "tuple_list",
        "container_subclass",
        "model_subclass",
        "raw_nested",
        "bool_int",
    ],
)
def test_strict_boundaries_reject_before_any_dump(mode, mutation, monkeypatch):
    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    body = mod.build_role_link_catalog(src, gen)
    if mode == "raw":
        body = body.model_dump(mode="json")

    def fields(node):
        return node.__dict__ if isinstance(node, BaseModel) else node

    root = fields(body)
    stored = fields(root["generation"])
    frame = fields(stored["frame"])
    index = fields(fields(frame["frame"])["candidate_index"])
    hint = fields(root["hints"][0])
    if mutation in ("missing_profile", "missing_rules", "missing_flag"):
        del root[
            {
                "missing_profile": "profile",
                "missing_rules": "rules_version",
                "missing_flag": "source_inventory_exhaustive",
            }[mutation]
        ]
    elif mutation == "missing_generation_marker":
        del stored["status"]
    elif mutation == "missing_index_marker":
        del index["status"]
    elif mutation == "missing_nullable":
        del fields(hint["anchor"])["c"]
    elif mutation == "missing_default":
        del src[1].document.__dict__["canonical_url"]
    elif mutation == "string_subclass":
        hint["hint_id"] = StringSubclass("m1")
    elif mutation == "tuple_list":
        root["hints"] = list(root["hints"]) if mode == "actual" else tuple(root["hints"])
    elif mutation == "container_subclass":
        root["hints"] = (
            TupleSubclass(root["hints"]) if mode == "actual" else ListSubclass(root["hints"])
        )
    elif mutation == "model_subclass":
        if mode == "actual":
            sub = create_model(
                "ExcludedHint",
                __base__=type(root["hints"][0]),
                hidden=(str, Field(default="hidden", exclude=True)),
            )
            root["hints"] = (sub.model_validate(root["hints"][0].model_dump()),)
        else:
            root["hints"][0] = DictSubclass(root["hints"][0])
    elif mutation == "raw_nested":
        if mode == "actual":
            hint["anchor"] = hint["anchor"].model_dump(mode="json")
        else:
            root["generation"] = gen
    elif mutation == "bool_int":
        fields(stored["usage"])["requests"] = True
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise RuntimeError("must guard before serialization")

    monkeypatch.setattr(BaseModel, "model_dump", forbidden)
    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    with pytest.raises(mod.RoleLinkCatalogError) as caught:
        mod.validate_role_link_catalog(src, body)
    assert caught.value.reason == "invalid_input"
    assert calls == []


def test_current_source_and_generation_changes_cannot_reuse_catalog():
    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    result = mod.build_role_link_catalog(src, gen)
    changed = deepcopy(src)
    changed[1].representation.__dict__["text"] += " "
    with pytest.raises(mod.RoleLinkCatalogError):
        mod.validate_role_link_catalog(changed, result)
    forged = result.model_copy(deep=True)
    forged.generation.usage.__dict__["input_tokens"] += 1
    with pytest.raises(mod.RoleLinkCatalogError):
        mod.validate_role_link_catalog(src, forged)
