"""Reviewed legal aliases stay inside the canonical, bounded question index."""

import importlib
from uuid import UUID, uuid4

import pytest
from issuedigest_storage import StorageCorruption
from issuedigest_storage.research_retrieval import question_terms
from sqlalchemy import text
from test_research_retrieval import save

PUNISHMENT = "스토킹범죄의 처벌 등에 관한 법률"
PROTECTION = "스토킹방지 및 피해자보호 등에 관한 법률"


def api():
    return importlib.import_module("issuedigest_storage.question_retrieval_v3")


def retrieve(engine, workspace, question):
    with engine.connect() as conn:
        return api().retrieve_snapshot_ids(conn, workspace, question_terms(question))


def test_reviewed_nickname_finds_both_full_titles_and_prefers_original(engine):
    workspace = uuid4()
    first = save(engine, workspace, PUNISHMENT)
    second = save(engine, workspace, PROTECTION)
    direct = save(
        engine, workspace, "스토킹법", identity=UUID("ffffffff-ffff-4fff-bfff-ffffffffffff")
    )
    assert retrieve(engine, workspace, "최근에 스토킹법 관련하여 궁금해.") == (
        direct,
        *sorted((first, second), key=str),
    )
    assert retrieve(engine, workspace, "스토킹처벌법은?") == (first,)
    assert retrieve(engine, workspace, "스토킹방지법은?") == (second,)


def test_alias_expansions_award_only_one_topic_credit(engine):
    workspace = uuid4()
    both = save(engine, workspace, PUNISHMENT + " " + PROTECTION)
    two_topics = save(engine, workspace, PUNISHMENT + " 피해지원")
    assert retrieve(engine, workspace, "스토킹법 피해지원")[0] == two_topics
    assert both in retrieve(engine, workspace, "스토킹법 피해지원")


def test_unknown_aliases_are_never_invented_and_workspace_is_strict(engine):
    workspace = uuid4()
    save(engine, workspace, "상상범죄의 처벌 등에 관한 법률")
    save(engine, uuid4(), PUNISHMENT)
    save(engine, workspace, "일반 정책 소식")
    assert retrieve(engine, workspace, "상상법") == ()
    assert retrieve(engine, workspace, "스토킹법") == ()


def test_alias_candidate_projection_corruption_fails_closed(engine):
    workspace = uuid4()
    identity = save(engine, workspace, PUNISHMENT)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE evidence_search_units SET text=text || '변조' WHERE snapshot_id=:s"),
            {"s": identity},
        )
    with pytest.raises(StorageCorruption):
        retrieve(engine, workspace, "스토킹법")


def test_eight_topics_keep_five_queries_per_group_bound(engine):
    from sqlalchemy import event

    workspace = uuid4()
    statements = []

    def observed(conn, cursor, statement, parameters, context, executemany):
        if "row_number() OVER" in statement:
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", observed)
    try:
        assert (
            retrieve(
                engine,
                workspace,
                "스토킹법 스토킹법은 스토킹법을 스토킹법이 "
                "스토킹처벌법 스토킹방지법 알파 베타 감마 델타 엡실론",
            )
            == ()
        )
    finally:
        event.remove(engine, "before_cursor_execute", observed)
    # First eight original topics only; four umbrella forms share one bounded group.
    assert len(statements) == 4 + 2 + 2 + 1 + 1


def test_umbrella_topic_finds_bill_summary_without_full_statute_title(engine):
    workspace = uuid4()
    bill = save(
        engine, workspace, "현행법은 반복되는 스토킹행위로 인한 피해자 보호조치를 규정하고 있음."
    )
    assert retrieve(engine, workspace, "최근에 스토킹법 관련하여 궁금해.") == (bill,)


def test_v3_question_terms_remove_only_reviewed_conversational_fillers():
    assert api().question_terms("최근에 스토킹법 관련하여 궁금해.") == ("스토킹법",)
    assert api().question_terms("관련하여 관련해서 궁금해 궁금해요 궁금합니다") == ()
    assert api().question_terms("관련하여는 궁금해요는") == ()
    assert api().question_terms("스토킹법은 궁금해요") == ("스토킹법은",)
    assert api().question_terms("관련하여개정 궁금해지원") == ("관련하여개정", "궁금해지원")


def test_reviewed_fillers_do_not_consume_eight_true_topic_budget():
    question = (
        "관련하여 관련해서 궁금해 궁금해요 궁금합니다 관련하여는 관련해서는 궁금해요는 스토킹법"
    )
    assert api().question_terms(question) == ("스토킹법",)
    assert len(api().question_terms("알파 베타 감마 델타 엡실론 제타 에타 세타 이오타")) == 8
