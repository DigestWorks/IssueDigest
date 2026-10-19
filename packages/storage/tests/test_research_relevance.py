"""Explicit journal candidates narrowed atomically in synthetic PostgreSQL."""

from uuid import uuid4

import pytest
from issuedigest_domain.research_journey import ResearchRequest
from issuedigest_storage import StorageCorruption
from issuedigest_storage.research import ResearchRepository
from issuedigest_storage.research_schema import research_runs
from sqlalchemy import update
from test_research_repository import add_topic, setup_run


def prepared(engine):
    bundle, sid, user, token = setup_run(engine)
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
    )
    repo.worker_transition(run.run_id, "retrieving")
    fixed = repo.worker_search_and_fix(run.run_id, ("80%",))
    return repo, run, token, user, fixed


def test_explicit_candidates_are_reopened_after_atomic_selection(engine):
    repo, run, token, _, fixed = prepared(engine)
    assert hasattr(repo, "worker_load_relevance_candidates"), "missing explicit relevance load"
    loaded = repo.worker_load_relevance_candidates(run.run_id, fixed)
    assert tuple(s[0] for s in loaded[1]) == fixed
    assert (
        repo.worker_apply_relevance_selection(
            run.run_id, fixed, fixed, input_tokens=200, output_tokens=100
        )
        == fixed
    )
    assert (
        repo.worker_apply_relevance_selection(
            run.run_id, fixed, fixed, input_tokens=200, output_tokens=100
        )
        == fixed
    )


@pytest.mark.parametrize(
    "mutation", ["unknown", "duplicate", "reorder", "oversize", "row", "empty-candidates"]
)
def test_invalid_selection_never_changes_fixed_ids(engine, mutation):
    repo, run, token, _, fixed = prepared(engine)
    assert hasattr(repo, "worker_apply_relevance_selection"), "missing atomic relevance apply"
    candidates = fixed
    selected = (uuid4(),)
    if mutation == "duplicate":
        selected = fixed + fixed
    if mutation == "reorder":
        other, _ = add_topic(engine, run.workspace_id, "80%")
        candidates = (*fixed, other)
        with engine.begin() as conn:
            conn.execute(
                update(research_runs)
                .where(research_runs.c.run_id == run.run_id)
                .values(snapshot_ids=list(map(str, candidates)))
            )
        selected = candidates[::-1]
    if mutation == "oversize":
        candidates = tuple(uuid4() for _ in range(6))
    if mutation == "row":
        candidates = (uuid4(),)
        selected = candidates
    if mutation == "empty-candidates":
        candidates = ()
        selected = ()
    with pytest.raises((ValueError, StorageCorruption)):
        repo.worker_apply_relevance_selection(
            run.run_id, candidates, selected, input_tokens=200, output_tokens=100
        )


def test_all_excluded_is_atomic_known_usage_failure(engine):
    repo, run, token, _, fixed = prepared(engine)
    assert hasattr(repo, "worker_apply_relevance_selection"), "missing atomic relevance apply"
    assert (
        repo.worker_apply_relevance_selection(
            run.run_id, fixed, (), input_tokens=200, output_tokens=100
        )
        is None
    )
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.snapshot_ids == () and after.error_code == "insufficient_evidence"
    assert (after.input_tokens, after.output_tokens) == (200, 100)


def test_relevance_accounting_is_monotonic_even_after_cancel(engine):
    repo, run, token, _, fixed = prepared(engine)
    assert hasattr(repo, "worker_record_relevance_usage"), "missing v9-only accounting"
    repo.cancel(token, run.workspace_id, run.run_id)
    # The v9 worker restores its validated journal subtotal after the legacy cancel
    # transition; terminal status itself remains unchanged.
    repo.worker_record_relevance_usage(run.run_id, input_tokens=300, output_tokens=150)
    repo.worker_record_relevance_usage(run.run_id, input_tokens=100, output_tokens=50)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.status == "cancelled"
    assert (after.input_tokens, after.output_tokens) == (300, 150)


def test_ordered_narrowing_reopens_excluded_originals_and_rejects_second_choice(engine):
    from issuedigest_storage.schema import evidence_snapshots

    repo, run, token, _, fixed = prepared(engine)
    second, _ = add_topic(engine, run.workspace_id, "80% 두번째 자료")
    candidates = (*fixed, second)
    with engine.begin() as conn:
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == run.run_id)
            .values(snapshot_ids=list(map(str, candidates)))
        )
    assert (
        repo.worker_apply_relevance_selection(
            run.run_id, candidates, fixed, input_tokens=200, output_tokens=100
        )
        == fixed
    )
    assert (
        tuple(s[0] for s in repo.worker_load_relevance_candidates(run.run_id, candidates)[1])
        == candidates
    )
    with pytest.raises(StorageCorruption):
        repo.worker_apply_relevance_selection(
            run.run_id, candidates, (second,), input_tokens=200, output_tokens=100
        )
    with engine.begin() as conn:
        conn.execute(
            update(evidence_snapshots)
            .where(evidence_snapshots.c.snapshot_id == second)
            .values(payload={})
        )
    with pytest.raises((ValueError, StorageCorruption)):
        repo.worker_load_relevance_candidates(run.run_id, candidates)
    assert repo.get_run(token, run.workspace_id, run.run_id).snapshot_ids == fixed


@pytest.mark.parametrize("terminal", ["cancelled", "failed", "completed"])
def test_terminal_rows_cannot_apply_selection(engine, terminal):
    repo, run, token, _, fixed = prepared(engine)
    if terminal == "cancelled":
        repo.cancel(token, run.workspace_id, run.run_id)
    else:
        with engine.begin() as conn:
            conn.execute(
                update(research_runs)
                .where(research_runs.c.run_id == run.run_id)
                .values(status=terminal)
            )
    assert repo.worker_load_relevance_candidates(run.run_id, fixed) is None
    assert (
        repo.worker_apply_relevance_selection(
            run.run_id, fixed, fixed, input_tokens=200, output_tokens=100
        )
        is None
    )


@pytest.mark.parametrize(
    "inputs,outputs", [(True, 0), (0, True), (-1, 0), (0, -1), (20000, 1), (0, 1001)]
)
def test_apply_rejects_invalid_combined_usage_atomically(engine, inputs, outputs):
    repo, run, token, _, fixed = prepared(engine)
    with pytest.raises(ValueError):
        repo.worker_apply_relevance_selection(
            run.run_id, fixed, (), input_tokens=inputs, output_tokens=outputs
        )
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.status == "retrieving" and after.snapshot_ids == fixed


def test_two_concurrent_same_selections_are_atomic_idempotent(engine):
    from concurrent.futures import ThreadPoolExecutor

    repo, run, token, _, fixed = prepared(engine)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                repo.worker_apply_relevance_selection,
                run.run_id,
                fixed,
                fixed,
                input_tokens=200,
                output_tokens=100,
            )
            for _ in range(2)
        ]
        assert [future.result(timeout=5) for future in futures] == [fixed, fixed]
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.snapshot_ids == fixed and (after.input_tokens, after.output_tokens) == (200, 100)


def test_apply_replay_cannot_erase_later_known_final_usage(engine):
    repo, run, token, _, fixed = prepared(engine)
    repo.worker_apply_relevance_selection(
        run.run_id, fixed, fixed, input_tokens=200, output_tokens=100
    )
    repo.worker_record_relevance_usage(run.run_id, input_tokens=300, output_tokens=150)
    repo.worker_apply_relevance_selection(
        run.run_id, fixed, fixed, input_tokens=200, output_tokens=100
    )
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert (after.input_tokens, after.output_tokens) == (300, 150)


def test_explicit_candidates_cannot_borrow_another_workspace(engine):
    repo, run, token, _, fixed = prepared(engine)
    _, foreign, _, _ = setup_run(engine)
    with pytest.raises(StorageCorruption):
        repo.worker_load_relevance_candidates(run.run_id, (*fixed, foreign))
    with pytest.raises(StorageCorruption):
        repo.worker_apply_relevance_selection(
            run.run_id, (*fixed, foreign), fixed, input_tokens=200, output_tokens=100
        )
    assert repo.get_run(token, run.workspace_id, run.run_id).snapshot_ids == fixed


def test_narrowed_generic_child_revalidates_original_parent_candidates(
    engine, historical_expanded_run
):
    old = historical_expanded_run
    repo = old["repo"]
    child = repo.submit(
        old["token"],
        old["workspace"],
        ResearchRequest(
            request_id=uuid4(), question="더 자세히 알려줘", parent_run_id=old["run"].run_id
        ),
    )
    repo.worker_transition(child.run_id, "retrieving")
    candidates = repo.worker_search_and_fix(child.run_id, ("주거지원",))
    assert candidates == tuple(s[0] for s in old["sources"])
    selected = candidates[:1]
    repo.worker_apply_relevance_selection(
        child.run_id, candidates, selected, input_tokens=200, output_tokens=100
    )
    assert (
        tuple(s[0] for s in repo.worker_load_relevance_candidates(child.run_id, candidates)[1])
        == candidates
    )
    with engine.begin() as conn:
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == old["run"].run_id)
            .values(status="failed", result=None)
        )
    with pytest.raises(StorageCorruption):
        repo.worker_load_relevance_candidates(child.run_id, candidates)
