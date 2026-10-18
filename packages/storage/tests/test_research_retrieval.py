"""Bounded Korean lexical retrieval against synthetic canonical PostgreSQL evidence."""

import json
import os
from pathlib import Path
from random import Random
from uuid import UUID, uuid4

import pytest
from issuedigest_storage import EvidenceRepository, StorageCorruption
from issuedigest_storage.research_retrieval import (
    is_generic_followup,
    question_terms,
    retrieve_snapshot_ids,
    topic_variants,
    variant_candidates,
)
from issuedigest_storage.retrieval_evaluation import evaluate
from sqlalchemy import event, text
from test_evidence_search import make_bundle


def save(engine, workspace, body="", cells=(), identity=None):
    bundle = make_bundle(body, workspace=workspace, cells=cells)
    identity = identity or uuid4()
    repo = EvidenceRepository(engine)
    repo.save(identity, bundle)
    repo.rebuild_projection(workspace, identity)
    return identity


def retrieve(engine, workspace, question):
    with engine.connect() as conn:
        return retrieve_snapshot_ids(conn, workspace, question_terms(question))


def test_synthetic_fixed_evaluation_before_after(engine, monkeypatch):
    import conftest

    random = Random(415)
    monkeypatch.setattr(conftest, "uuid4", lambda: UUID(int=random.getrandbits(128), version=4))
    workspace = UUID("00000000-0000-4000-8000-000000000001")
    bodies = [
        "AI 도입",
        "2026년 사업",
        "지방 국립대학교 등록금 지원",
        "반복주제",
        "반복주제",
        "한국어",
    ]
    snapshots = []
    for i, body in enumerate(bodies, 10):
        identity = UUID(f"00000000-0000-4000-8000-{i:012d}")
        cells = tuple({"cell_id": str(n), "text": body} for n in range(25)) if i == 13 else ()
        snapshots.append(save(engine, workspace, "" if cells else body, cells, identity))
    definitions = [
        ("mixed", "AI는?", [[snapshots[0]]]),
        ("year", "2026년에는?", [[snapshots[1]]]),
        ("spacing", "지방국립대학교등록금지원", [[snapshots[2]]]),
        ("balanced", "반복주제", [[snapshots[3]], [snapshots[4]]]),
        ("unchanged", "한국어", [[snapshots[5]]]),
        ("unavailable", "자료없는정책", [[snapshots[5]]]),
        ("negative", "없는주제", []),
    ]
    job = {
        "schema_version": 1,
        "expected_database": "issuedigest_test",
        "workspace_id": str(workspace),
        "corpus_snapshot_ids": list(map(str, snapshots)),
        "cases": [
            {
                "case_id": name,
                "question": question,
                "expected_families": [[str(x) for x in family] for family in families],
                "no_match": not families,
            }
            for name, question, families in definitions
        ],
    }
    report = evaluate(engine, json.dumps(job, ensure_ascii=False).encode())
    capture = os.environ.get("TASK2_SYNTHETIC_CAPTURE")
    if capture:
        Path(capture).write_text(report.model_dump_json(indent=2))
    assert [case.family_recall_at_5 for case in report.cases[:6]] == [1, 1, 1, 1, 1, 0]
    assert report.summary["negative_no_match"] == 1


def test_question_preserves_original_topics_and_filters_presentation_words():
    assert question_terms("AI는 2026년에는 등록금은 비교해줘 요약해줘") == (
        "ai는",
        "2026년에는",
        "등록금은",
    )
    assert question_terms("오픈에이아이 서울과학기술대학교") == (
        "오픈에이아이",
        "서울과학기술대학교",
    )
    assert len(question_terms("하나 둘 셋 넷 다섯 여섯 일곱 여덟 아홉 열")) == 8


@pytest.mark.parametrize(
    "question", ["😀", "Ω", "１", "\u200b", "더 " + "가" * 65, "더 +", "더 양자컴퓨터는"]
)
def test_unknown_tokens_symbols_and_oversized_topics_never_become_generic(question):
    assert not is_generic_followup(question)


@pytest.mark.parametrize(
    "question", ["더 자세히 알려줘", "그럼 요약해주세요?", "의미가 무엇인가요?"]
)
def test_existing_generic_followups_remain_conservative(question):
    assert not question_terms(question)
    assert is_generic_followup(question)


def test_distinct_topic_coverage_then_original_match_rank_without_variant_or_row_bonus(engine):
    workspace = uuid4()
    original = save(engine, workspace, "AI는 등록금은")
    variant = save(engine, workspace, "AI 등록금")
    repeated = save(
        engine,
        workspace,
        cells=tuple({"cell_id": str(i), "text": "AI는 AI 등록금"} for i in range(25)),
    )
    only_one = save(engine, workspace, "AI는 AI")
    ranked = retrieve(engine, workspace, "AI는 등록금은")
    assert ranked == (original, repeated, variant, only_one)


def test_spacing_is_whole_string_actual_match_not_ngram_or_semantic_equivalence(engine):
    workspace = uuid4()
    found = save(engine, workspace, "지방\t국립대학교\n등록금 지원")
    save(engine, workspace, "지방국립대학교 다른 등록금지원")
    save(engine, workspace, "지방\u200b국립대학교등록금지원")
    save(engine, workspace, "aba|bab")
    save(engine, workspace, "２０２６년 2027년")
    assert retrieve(engine, workspace, "지방국립대학교등록금지원") == (found,)
    assert retrieve(engine, workspace, "ababa") == ()
    assert retrieve(engine, workspace, "2026년") == ()


def test_repeated_paragraphs_do_not_hide_other_snapshot_and_workspace_stays_scoped(engine):
    workspace = uuid4()
    first = save(
        engine, workspace, cells=tuple({"cell_id": str(i), "text": "반복주제"} for i in range(210))
    )
    other = save(engine, workspace, "반복주제")
    save(engine, uuid4(), "반복주제")
    assert retrieve(engine, workspace, "반복주제") == tuple(sorted((first, other), key=str))


@pytest.mark.parametrize("damage", ["text", "selector", "manifest", "canonical"])
def test_internal_retrieval_rejects_corrupt_canonical_projection_and_selectors(engine, damage):
    workspace = uuid4()
    save(engine, workspace, "한국어")
    sql = {
        "text": "UPDATE evidence_search_units SET text='한국어 forged'",
        "selector": (
            "UPDATE evidence_search_units SET selector=jsonb_set(selector,'{quote}','\"forged\"')"
        ),
        "manifest": "UPDATE evidence_search_projections SET projection_sha256=repeat('f',64)",
        "canonical": (
            "UPDATE parsed_representations SET payload="
            "jsonb_set(payload,'{text}','\"한국어 forged\"')"
        ),
    }[damage]
    with engine.begin() as conn:
        conn.execute(text(sql))
    with pytest.raises(StorageCorruption):
        retrieve(engine, workspace, "한국어")


def test_twenty_distinct_snapshot_pool_and_final_five_are_stable(engine):
    workspace = uuid4()
    identities = [UUID(f"00000000-0000-4000-8000-{i:012d}") for i in range(1, 23)]
    for identity in reversed(identities):
        save(engine, workspace, "주제", identity=identity)
    with engine.connect() as conn:
        candidates = variant_candidates(conn, workspace, "주제")
    assert candidates.snapshot_ids == tuple(identities[:20])
    assert candidates.scanned_candidates == 22 and candidates.truncated
    assert retrieve(engine, workspace, "주제") == tuple(identities[:5])


def test_each_variant_scans_at_most_200_balanced_rows_and_detects_201(engine):
    workspace = uuid4()
    for _ in range(2):
        save(
            engine,
            workspace,
            cells=tuple({"cell_id": str(n), "text": "한국어"} for n in range(110)),
        )
    with engine.connect() as conn:
        candidates = variant_candidates(conn, workspace, "한국어")
    assert len(candidates.snapshot_ids) == 2
    assert candidates.scanned_candidates == 200 and candidates.truncated


@pytest.mark.parametrize(
    "term,want",
    [
        ("ai는", ("ai는", "ai")),
        ("2026년에는", ("2026년에는", "2026년")),
        ("2026년도", ("2026년도", "2026년")),
        ("2026년", ("2026년",)),
        ("100만은", ("100만은", "100만")),
        ("10도는", ("10도는", "10도")),
        ("10원만", ("10원만", "10원")),
        ("ai도", ("ai도", "ai")),
        ("80%", ("80%",)),
        ("오픈에이아이", ("오픈에이아이", "오픈에이아")),
    ],
)
def test_particle_variants_preserve_original_units_and_proper_names(term, want):
    assert topic_variants(term) == want


def test_eight_topic_bound_and_duplicate_variants_do_not_add_topic_bonus(engine):
    workspace = uuid4()
    raw = save(engine, workspace, "AI는 AI")
    both = save(engine, workspace, "AI 등록금")
    assert retrieve(engine, workspace, "AI는 AI 등록금") == (both, raw)
    save(engine, workspace, "아홉주제")
    assert (
        retrieve(
            engine,
            workspace,
            "첫주제 둘주제 셋주제 넷주제 다섯주제 여섯주제 일곱주제 여덟주제 아홉주제",
        )
        == ()
    )


def test_two_hundred_candidate_boundary_without_truncation(engine):
    workspace = uuid4()
    save(engine, workspace, cells=tuple({"cell_id": str(n), "text": "한국어"} for n in range(200)))
    with engine.connect() as conn:
        candidates = variant_candidates(conn, workspace, "한국어")
    assert candidates.scanned_candidates == 200 and not candidates.truncated


def test_unicode_number_topic_is_preserved_and_never_reduced_to_ascii_or_year_unit(engine):
    workspace = uuid4()
    ascii_year = save(engine, workspace, "2026년")
    fullwidth_year = save(engine, workspace, "２０２６년")
    assert question_terms("２０２６년") == ("２０２６년",)
    assert retrieve(engine, workspace, "２０２６년") == (fullwidth_year,)
    assert retrieve(engine, workspace, "2026년") == (ascii_year,)


def test_201st_candidate_is_sentinel_but_200th_is_canonical_checked(engine):
    workspace = uuid4()
    first = UUID("00000000-0000-4000-8000-000000000001")
    second = UUID("00000000-0000-4000-8000-000000000002")
    cells = tuple({"cell_id": str(n), "text": "한국어"} for n in range(110))
    for identity in (first, second):
        save(engine, workspace, cells=cells, identity=identity)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE evidence_search_units SET selector="
                "jsonb_set(selector,'{quote}','\"forged\"') WHERE snapshot_id=:id AND ordinal=100"
            ),
            {"id": first},
        )
    with engine.connect() as conn:
        result = variant_candidates(conn, workspace, "한국어")
    assert result.scanned_candidates == 200 and result.truncated
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE evidence_search_units SET selector="
                "jsonb_set(selector,'{quote}','\"forged\"') WHERE snapshot_id=:id AND ordinal=99"
            ),
            {"id": second},
        )
    with engine.connect() as conn, pytest.raises(StorageCorruption):
        variant_candidates(conn, workspace, "한국어")


def test_at_most_twenty_four_search_variants_for_eight_original_topics(engine):
    workspace = uuid4()
    save(engine, workspace, "주제")
    statements = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        if "row_number()" in statement:
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", observe)
    try:
        retrieve(
            engine,
            workspace,
            "첫주제는 둘주제는 셋주제는 넷주제는 "
            "다섯주제는 여섯주제는 일곱주제는 여덟주제는 아홉주제는",
        )
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert 8 <= len(statements) <= 24


@pytest.mark.parametrize(
    "term,other",
    [
        ("100만", "100원"),
        ("10도", "10원"),
        ("100.5만", "100.5원"),
        ("１００만", "１００원"),
    ],
)
def test_numeric_magnitude_and_unit_endings_are_not_particle_expansions(engine, term, other):
    workspace = uuid4()
    wanted = save(engine, workspace, term)
    save(engine, workspace, other)
    assert question_terms(term) == (term,)
    assert topic_variants(term) == (term,)
    assert retrieve(engine, workspace, term) == (wanted,)


def test_all_preserved_originals_receive_one_order_independent_direct_credit(engine):
    workspace = uuid4()
    plain = UUID("00000000-0000-4000-8000-000000000001")
    suffixed = UUID("00000000-0000-4000-8000-000000000002")
    save(engine, workspace, "AI", identity=plain)
    save(engine, workspace, "AI는", identity=suffixed)
    assert retrieve(engine, workspace, "AI AI는") == (plain, suffixed)
    assert retrieve(engine, workspace, "AI는 AI") == (plain, suffixed)


def test_all_group_originals_count_once_with_at_most_three_search_variants(engine):
    workspace = uuid4()
    plain = UUID("00000000-0000-4000-8000-000000000001")
    later_original = UUID("00000000-0000-4000-8000-000000000002")
    multiple_originals = UUID("00000000-0000-4000-8000-000000000003")
    save(engine, workspace, "AI", identity=plain)
    save(engine, workspace, "AI와", identity=later_original)
    save(engine, workspace, "AI가 AI는 AI를", identity=multiple_originals)
    statements = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        if "row_number()" in statement:
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", observe)
    try:
        assert retrieve(engine, workspace, "AI는 AI가 AI를 AI와") == (
            later_original,
            multiple_originals,
            plain,
        )
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert 1 <= len(statements) <= 3
    assert retrieve(engine, workspace, "AI와 AI를 AI가 AI는") == (
        later_original,
        multiple_originals,
        plain,
    )


@pytest.mark.parametrize(
    "quantity,other",
    [
        ("1천만", "1천원"),
        ("10여만", "10여원"),
        ("１천만", "１천원"),
        ("1가나다만", "1가나다원"),
        ("1천도", "1천원"),
    ],
)
def test_mixed_numeric_quantity_keeps_ambiguous_magnitude_and_unit(engine, quantity, other):
    workspace = uuid4()
    wanted = save(engine, workspace, quantity)
    save(engine, workspace, other)
    assert topic_variants(quantity) == (quantity,)
    assert retrieve(engine, workspace, quantity) == (wanted,)


@pytest.mark.parametrize(
    "term,want",
    [
        ("1천만은", ("1천만은", "1천만")),
        ("10여만에는", ("10여만에는", "10여만")),
        ("1천만원만", ("1천만원만", "1천만원")),
        ("10여만명도", ("10여만명도", "10여만명")),
        ("2026년도", ("2026년도", "2026년")),
    ],
)
def test_known_particles_after_retained_numeric_units_still_expand(term, want):
    assert topic_variants(term) == want
