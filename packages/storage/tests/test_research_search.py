"""Atomic planner-assisted retrieval over dedicated synthetic PostgreSQL evidence."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from uuid import uuid4

import pytest
from issuedigest_domain.research_journey import ResearchRequest
from issuedigest_storage import IdentityRepository, SessionRepository, StorageCorruption
from issuedigest_storage.research import ResearchRepository
from issuedigest_storage.research_schema import research_runs, source_presentations
from issuedigest_storage.search_schema import projections, units
from sqlalchemy import delete, event, select, update
from test_policy_intake_retrieval import intake
from test_policy_intake_storage import config
from test_research_repository import add_topic, setup_run


def submit(repo, token, workspace, question="없는질문", parent=None):
    return repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question=question, parent_run_id=parent),
    )


def start(repo, run):
    assert repo.worker_prepare_search(run.run_id) == run
    assert repo.worker_transition(run.run_id, "retrieving")


@contextmanager
def index_reads(engine):
    statements = []

    def observe(conn, cursor, statement, parameters, context, many):
        if statement.lstrip().startswith("SELECT") and "evidence_search_units" in statement:
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", observe)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", observe)


def test_prepare_preserves_question_and_queued_state_without_search_or_no_match(engine):
    bundle, _, _, token = setup_run(engine)
    repo = ResearchRepository(engine)
    run = submit(repo, token, bundle.document.workspace_id)
    with index_reads(engine) as reads:
        assert repo.worker_prepare_search(run.run_id) == run
    assert reads == []
    assert repo.get_run(token, run.workspace_id, run.run_id) == run
    assert repo.worker_prepare_search(uuid4()) is None


def test_plan_can_find_evidence_when_original_question_has_no_literal_hits(engine):
    bundle, snapshot, _, token = setup_run(engine)
    repo = ResearchRepository(engine)
    run = submit(repo, token, bundle.document.workspace_id)
    start(repo, run)
    assert repo.worker_search_and_fix(run.run_id, ("80%",), input_tokens=120, output_tokens=10) == (
        snapshot,
    )
    current = repo.get_run(token, run.workspace_id, run.run_id)
    assert current.status == "retrieving" and current.snapshot_ids == (snapshot,)
    assert [e.status for e in current.events] == ["queued", "retrieving"]
    assert repo.worker_load(run.run_id)[0] == current


def test_original_first_round_robin_deduplicates_and_caps_five_with_three_queries(engine):
    bundle, _, _, token = setup_run(engine)
    workspace = bundle.document.workspace_id
    repo = ResearchRepository(engine)
    groups = []
    for topic in ("원질문", "계획하나", "계획둘", "계획셋"):
        groups.append(
            tuple(sorted((add_topic(engine, workspace, topic)[0] for _ in range(3)), key=str))
        )
    foreign, _ = add_topic(engine, uuid4(), "원질문 계획하나 계획둘 계획셋")
    run = submit(repo, token, workspace, "원질문")
    start(repo, run)
    selected = repo.worker_search_and_fix(run.run_id, ("계획하나", "계획둘", "계획셋"))
    assert selected == (groups[0][0], groups[1][0], groups[2][0], groups[3][0], groups[0][1])
    assert foreign not in selected
    repo.cancel(token, workspace, run.run_id)
    duplicate = submit(repo, token, workspace, "원질문")
    start(repo, duplicate)
    assert repo.worker_search_and_fix(duplicate.run_id, ("원질문", "원질문")) == groups[0]


@pytest.mark.parametrize(
    "queries",
    [
        (),
        ("a", "b", "c", "d"),
        ["80%"],
        "80%",
        (1,),
        ("",),
        (" \u3000",),
        ("x" * 65,),
        ("a\n",),
        ("a\x00",),
        ("a\u200b",),
    ],
)
def test_invalid_queries_are_rejected_without_mutating_run(engine, queries):
    bundle, _, _, token = setup_run(engine)
    repo = ResearchRepository(engine)
    run = submit(repo, token, bundle.document.workspace_id)
    start(repo, run)
    before = repo.get_run(token, run.workspace_id, run.run_id)
    with pytest.raises(ValueError), index_reads(engine) as reads:
        repo.worker_search_and_fix(run.run_id, queries)
    assert reads == []
    assert repo.get_run(token, run.workspace_id, run.run_id) == before


@pytest.mark.parametrize(
    "usage", [(-1, 0), (True, 0), (0, False), (1.0, 0), (0, 501), (8001, 0), (7501, 500)]
)
def test_invalid_planner_usage_is_rejected_before_search(engine, usage):
    bundle, _, _, token = setup_run(engine)
    repo = ResearchRepository(engine)
    run = submit(repo, token, bundle.document.workspace_id)
    start(repo, run)
    with pytest.raises(ValueError), index_reads(engine) as reads:
        repo.worker_search_and_fix(
            run.run_id, ("80%",), input_tokens=usage[0], output_tokens=usage[1]
        )
    assert reads == []
    assert repo.get_run(token, run.workspace_id, run.run_id).snapshot_ids == ()


def test_first_fix_requires_retrieving_and_known_no_match_usage_is_atomic_and_terminal(engine):
    bundle, _, _, token = setup_run(engine)
    repo = ResearchRepository(engine)
    run = submit(repo, token, bundle.document.workspace_id)
    with index_reads(engine) as reads:
        assert repo.worker_search_and_fix(run.run_id, ("80%",)) is None
    assert reads == []
    start(repo, run)
    assert (
        repo.worker_search_and_fix(run.run_id, ("없는주제",), input_tokens=7500, output_tokens=500)
        is None
    )
    failed = repo.get_run(token, run.workspace_id, run.run_id)
    assert (failed.status, failed.error_code, failed.input_tokens, failed.output_tokens) == (
        "failed",
        "insufficient_evidence",
        7500,
        500,
    )
    assert failed.snapshot_ids == () and failed.result is None
    add_topic(engine, run.workspace_id, "없는주제")
    with index_reads(engine) as reads:
        assert repo.worker_prepare_search(run.run_id) is None
        assert repo.worker_search_and_fix(run.run_id, ("없는주제",), input_tokens=1) is None
    assert reads == []
    assert repo.get_run(token, run.workspace_id, run.run_id) == failed


@pytest.mark.parametrize("change", ["viewer", "inactive", "cancel"])
def test_current_authority_or_cancel_stops_before_index_after_prepare(engine, change):
    bundle, _, actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
    run = submit(repo, token, bundle.document.workspace_id)
    start(repo, run)
    if change == "cancel":
        repo.cancel(token, run.workspace_id, run.run_id)
    else:
        IdentityRepository(engine).set_membership(
            actor, run.workspace_id, "viewer", change != "inactive"
        )
    with index_reads(engine) as reads:
        assert repo.worker_search_and_fix(run.run_id, ("80%",)) is None
        assert repo.worker_prepare_search(run.run_id) is None
    assert reads == []
    with engine.connect() as conn:
        row = (
            conn.execute(select(research_runs).where(research_runs.c.run_id == run.run_id))
            .mappings()
            .one()
        )
    assert row["status"] == ("cancelled" if change == "cancel" else "failed")
    assert row["error_code"] == ("cancelled" if change == "cancel" else "authority_changed")
    assert row["snapshot_ids"] == []


def test_fixed_replay_never_searches_or_changes_progress_after_index_changes(engine):
    bundle, snapshot, _, token = setup_run(engine)
    repo = ResearchRepository(engine)
    run = submit(repo, token, bundle.document.workspace_id)
    start(repo, run)
    assert repo.worker_search_and_fix(run.run_id, ("80%",)) == (snapshot,)
    assert repo.worker_transition(run.run_id, "generating")
    before = repo.get_run(token, run.workspace_id, run.run_id)
    with engine.begin() as conn:
        conn.execute(delete(projections).where(projections.c.snapshot_id == snapshot))
    add_topic(engine, run.workspace_id, "80%")
    with index_reads(engine) as reads:
        assert repo.worker_search_and_fix(run.run_id, ("다른검색",)) == (snapshot,)
    assert reads == []
    assert repo.get_run(token, run.workspace_id, run.run_id) == before


def test_concurrent_fix_commits_one_selection_and_replays_it_without_new_search(engine):
    bundle, snapshot, _, token = setup_run(engine)
    repo = ResearchRepository(engine)
    run = submit(repo, token, bundle.document.workspace_id)
    start(repo, run)
    with index_reads(engine) as reads, ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(lambda _: repo.worker_search_and_fix(run.run_id, ("80%",)), range(2))
        )
    assert outcomes == [(snapshot,), (snapshot,)]
    assert len(reads) == 2
    assert [e.status for e in repo.get_run(token, run.workspace_id, run.run_id).events] == [
        "queued",
        "retrieving",
    ]


@pytest.mark.parametrize("damage", ["unit", "presentation"])
def test_corruption_rolls_back_selection_presentations_and_events(engine, damage):
    bundle, snapshot, _, token = setup_run(engine)
    workspace = bundle.document.workspace_id
    repo = ResearchRepository(engine)
    other, _ = add_topic(engine, workspace, "추가주제")
    run = submit(repo, token, workspace, "80%")
    start(repo, run)
    with engine.begin() as conn:
        if damage == "unit":
            conn.execute(
                update(units).where(units.c.snapshot_id == other).values(text_sha256="b" * 64)
            )
        else:
            conn.execute(
                source_presentations.insert().values(
                    snapshot_id=other, workspace_id=workspace, payload={"bad": "presentation"}
                )
            )
    before = repo.get_run(token, workspace, run.run_id)
    with pytest.raises((StorageCorruption, ValueError)):
        repo.worker_search_and_fix(run.run_id, ("추가주제",), input_tokens=90, output_tokens=20)
    assert repo.get_run(token, workspace, run.run_id) == before
    with engine.connect() as conn:
        assert (
            conn.scalar(
                select(source_presentations.c.snapshot_id).where(
                    source_presentations.c.snapshot_id == snapshot
                )
            )
            is None
        )


def test_generic_parent_reuses_all_exact_legacy_evidence_ignoring_plan(
    engine, historical_expanded_run
):
    old = historical_expanded_run
    repo = old["repo"]
    child = submit(repo, old["token"], old["workspace"], "더 자세히 알려줘", old["run"].run_id)
    start(repo, child)
    add_topic(engine, old["workspace"], "계획새주제")
    with index_reads(engine) as reads:
        assert repo.worker_search_and_fix(child.run_id, ("계획새주제",)) == tuple(
            source[0] for source in old["sources"]
        )
    assert reads == []
    repo.cancel(old["token"], old["workspace"], child.run_id)
    fresh = submit(repo, old["token"], old["workspace"], "없는주제", old["run"].run_id)
    start(repo, fresh)
    assert repo.worker_search_and_fix(fresh.run_id, ("없는주제",)) is None
    assert repo.get_run(old["token"], old["workspace"], old["run"].run_id).result == old["result"]


@pytest.mark.parametrize("stage", ["prepare", "fix"])
def test_parent_mismatch_is_rechecked_before_search(engine, historical_expanded_run, stage):
    old = historical_expanded_run
    repo = old["repo"]
    child = submit(repo, old["token"], old["workspace"], "새주제", old["run"].run_id)
    if stage == "fix":
        start(repo, child)
    with engine.begin() as conn:
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == old["run"].run_id)
            .values(snapshot_ids=[str(uuid4())])
        )
    with pytest.raises(StorageCorruption), index_reads(engine) as reads:
        if stage == "prepare":
            repo.worker_prepare_search(child.run_id)
        else:
            repo.worker_search_and_fix(child.run_id, ("주거지원",))
    assert reads == []
    assert repo.get_run(old["token"], old["workspace"], child.run_id).snapshot_ids == ()


def intake_actor(engine, workspace):
    actor = uuid4()
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, workspace, "owner")
    return SessionRepository(engine).issue_session(actor).token


@pytest.mark.parametrize("new_body,unindexed", [("신판단어", False), ("구판단어 변경", True)])
def test_plan_uses_latest_approval_without_old_version_fallback(engine, new_body, unindexed):
    cfg = config()
    first, _, _ = intake(engine, cfg, body="구판단어")
    newer, _, _ = intake(engine, cfg, prior=first, body=new_body, seconds=60)
    if unindexed:
        with engine.begin() as conn:
            conn.execute(
                delete(projections).where(projections.c.snapshot_id == newer.entries[0].snapshot_id)
            )
    token = intake_actor(engine, first.workspace_id)
    repo = ResearchRepository(engine)
    run = submit(repo, token, first.workspace_id)
    start(repo, run)
    assert repo.worker_search_and_fix(run.run_id, ("구판단어",)) is None
    run = submit(repo, token, first.workspace_id)
    start(repo, run)
    expected = None if unindexed else (newer.entries[0].snapshot_id,)
    assert repo.worker_search_and_fix(run.run_id, ("신판단어",)) == expected


def test_fixed_replay_keeps_old_approval_and_validates_original_presentation(engine):
    first, _, _ = intake(engine, config(), body="주거지원 구판")
    token = intake_actor(engine, first.workspace_id)
    repo = ResearchRepository(engine)
    run = submit(repo, token, first.workspace_id, "주거지원")
    start(repo, run)
    fixed = (first.entries[0].snapshot_id,)
    assert repo.worker_search_and_fix(run.run_id, ("주거지원",)) == fixed
    intake(engine, config(), prior=first, body="주거지원 신판", seconds=60)
    with index_reads(engine) as reads:
        assert repo.worker_search_and_fix(run.run_id, ("주거지원",)) == fixed
    assert reads == []
    with engine.begin() as conn:
        conn.execute(
            update(source_presentations)
            .where(source_presentations.c.snapshot_id == fixed[0])
            .values(payload={"bad": "presentation"})
        )
    with pytest.raises(ValueError):
        repo.worker_search_and_fix(run.run_id, ("주거지원",))


def test_generic_fixed_replay_rejects_sources_outside_exact_parent(engine, historical_expanded_run):
    old = historical_expanded_run
    repo = old["repo"]
    child = submit(repo, old["token"], old["workspace"], "더 자세히 알려줘", old["run"].run_id)
    start(repo, child)
    assert repo.worker_search_and_fix(child.run_id, ("주거지원",)) == tuple(
        source[0] for source in old["sources"]
    )
    foreign, _ = add_topic(engine, old["workspace"], "다른근거")
    with engine.begin() as conn:
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == child.run_id)
            .values(snapshot_ids=[str(foreign)])
        )
    with pytest.raises(StorageCorruption), index_reads(engine) as reads:
        repo.worker_search_and_fix(child.run_id, ("다른근거",))
    assert reads == []
