"""Real transactional PostgreSQL public-copy lifecycle, corruption and concurrency."""

import importlib
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier, Event
from uuid import uuid4

import pytest
from issuedigest_domain.public_briefings import PublicBriefingPlan, plan_hash
from issuedigest_storage.repository import StorageConflict, StorageCorruption
from sqlalchemy import event, text, update

from conftest import public_plan_data

pb = (
    importlib.import_module("issuedigest_storage.public_briefings")
    if importlib.util.find_spec("issuedigest_storage.public_briefings")
    else None
)


def test_public_repository_exists():
    assert pb is not None, "public publication repository missing"


@pytest.fixture
def repo(engine):
    if pb is None:
        pytest.skip("not available")
    return pb.PublicBriefingRepository(engine)


def plan():
    return PublicBriefingPlan.model_validate(public_plan_data())


def test_lifecycle_immutable_versions_and_no_latest_revival(repo, engine):
    first = plan()
    before = private_counts(engine)
    one = repo.publish(first, reviewed_sha256=plan_hash(first))
    assert repo.publish(first, reviewed_sha256=plan_hash(first)) == one
    second = first.model_copy(update={"version": 2, "title": "개정 합성 제목"})
    two = repo.publish(second, reviewed_sha256=plan_hash(second))
    assert two.canvas != one.canvas
    assert repo.load(first.slug) == two
    assert repo.load(first.slug, 1) == one
    assert repo.list_latest().items[0].version == 2
    repo.withdraw(second, reviewed_sha256=plan_hash(second))
    assert repo.load(first.slug) is None
    assert repo.load(first.slug, 2) is None
    assert repo.load(first.slug, 1) == one
    assert repo.list_latest().items == ()
    repo.withdraw(second, reviewed_sha256=plan_hash(second))
    with pytest.raises(StorageConflict):
        repo.publish(second, reviewed_sha256=plan_hash(second))
    assert private_counts(engine) == before


def private_counts(engine):
    names = [
        "source_documents",
        "document_versions",
        "auth_sessions",
        "research_runs",
        "research_events",
        "research_budget_months",
        "outbox",
    ]
    with engine.connect() as conn:
        return {name: conn.scalar(text(f"SELECT count(*) FROM {name}")) for name in names}


def test_reviewed_hash_version_identity_and_overwrite_fail_closed(repo):
    first = plan()
    with pytest.raises(ValueError):
        repo.publish(first, reviewed_sha256="0" * 64)
    assert repo.list_latest().items == ()
    with pytest.raises(StorageConflict):
        skipped = first.model_copy(update={"version": 2})
        repo.publish(skipped, reviewed_sha256=plan_hash(skipped))
    repo.publish(first, reviewed_sha256=plan_hash(first))
    for changes in (
        {"title": "다른 제목"},
        {"version": 3},
        {"public_id": uuid4(), "version": 2},
        {"slug": "another-slug"},
    ):
        candidate = first.model_copy(update=changes)
        with pytest.raises(StorageConflict):
            repo.publish(candidate, reviewed_sha256=plan_hash(candidate))
    wrong = first.model_copy(update={"title": "다른 내용"})
    with pytest.raises(StorageConflict):
        repo.withdraw(wrong, reviewed_sha256=plan_hash(wrong))
    assert repo.load(first.slug) is not None


def test_check_is_readonly_and_does_not_publish(repo):
    first = plan()
    assert repo.check(first)["status"] == "database_checked"
    assert repo.list_latest().items == ()
    repo.publish(first, reviewed_sha256=plan_hash(first))
    assert repo.check(first)["status"] == "already_published"


@pytest.mark.parametrize(
    ("candidate_version", "status"), [(1, "already_published"), (2, "database_checked")]
)
def test_check_keeps_consistent_snapshot_during_concurrent_publication(
    repo, engine, candidate_version, status
):
    first = plan()
    repo.publish(first, reviewed_sha256=plan_hash(first))
    second = first.model_copy(update={"version": 2, "title": "개정 합성 제목"})
    candidate = first if candidate_version == 1 else second
    head_read, resume = Event(), Event()

    def after_head_select(conn, cursor, statement, parameters, context, many):
        if not statement.startswith("SELECT public_briefing_heads.slug") or head_read.is_set():
            return
        head_read.set()
        assert resume.wait(timeout=10)

    event.listen(engine, "after_cursor_execute", after_head_select)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            checking = pool.submit(repo.check, candidate)
            try:
                assert head_read.wait(timeout=5)
                # The check still owns its connection; publication commits on another one.
                published = repo.publish(second, reviewed_sha256=plan_hash(second))
                assert repo.load(first.slug) == published
                resume.set()
                assert checking.result(timeout=5) == {
                    "status": status,
                    "plan_sha256": plan_hash(candidate),
                }
            finally:
                resume.set()
    finally:
        event.remove(engine, "after_cursor_execute", after_head_select)


@pytest.mark.parametrize("different", [False, True])
def test_concurrent_same_and_different_plan_publish(repo, different):
    first = plan()
    other = first.model_copy(update={"title": "경쟁 합성 내용"}) if different else first
    barrier = Barrier(2)

    def run(candidate):
        barrier.wait(timeout=5)
        try:
            return repo.publish(candidate, reviewed_sha256=plan_hash(candidate))
        except StorageConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, [first, other]))
    if different:
        assert sum(result is None for result in results) == 1
    else:
        assert results[0] == results[1]
    assert len(repo.list_latest().items) == 1


def test_publish_and_withdraw_race_never_reactivates(repo):
    first = plan()
    original = repo.publish(first, reviewed_sha256=plan_hash(first))
    barrier = Barrier(2)

    def run(withdraw):
        barrier.wait(timeout=5)
        try:
            return (repo.withdraw if withdraw else repo.publish)(
                first, reviewed_sha256=plan_hash(first)
            )
        except StorageConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, [False, True]))
    assert repo.load(first.slug) is None
    assert repo.list_latest().items == ()
    with pytest.raises(StorageConflict):
        repo.publish(first, reviewed_sha256=plan_hash(first))
    assert original.version == 1


@pytest.mark.parametrize("tamper", ["payload", "hash", "row_reference", "latest_hash", "review"])
def test_corrupt_payload_or_latest_integrity_is_not_served(repo, engine, tamper):
    from issuedigest_storage.public_briefing_schema import public_briefing_heads, public_briefings

    first = plan()
    detail = repo.publish(first, reviewed_sha256=plan_hash(first))
    with engine.begin() as conn:
        if tamper == "payload":
            data = deepcopy(detail.model_dump(mode="json"))
            data["title"] = "tampered"
            conn.execute(update(public_briefings).values(payload=data))
        elif tamper == "hash":
            conn.execute(update(public_briefings).values(content_sha256="0" * 64))
        elif tamper == "row_reference":
            conn.execute(update(public_briefings).values(public_id=uuid4()))
        elif tamper == "review":
            from sqlalchemy import select

            record = deepcopy(conn.scalar(select(public_briefings.c.review_record)))
            record["sources"][0]["reviewer"] = "tampered-private-reviewer"
            conn.execute(update(public_briefings).values(review_record=record))
        else:
            conn.execute(update(public_briefing_heads).values(latest_content_sha256="0" * 64))
    for read in (lambda: repo.load(first.slug), lambda: repo.load(first.slug, 1), repo.list_latest):
        with pytest.raises(StorageCorruption):
            read()


def test_list_is_latest_twenty_only(repo):
    for index in range(22):
        candidate = plan().model_copy(update={"slug": f"synthetic-{index}"})
        repo.publish(candidate, reviewed_sha256=plan_hash(candidate))
    listing = repo.list_latest()
    assert len(listing.items) == 20
    assert all(not hasattr(item, "canvas") for item in listing.items)


def test_demoted_latest_head_cannot_revive_older_publication(repo, engine):
    from issuedigest_storage.public_briefing_schema import public_briefing_heads

    first = plan()
    one = repo.publish(first, reviewed_sha256=plan_hash(first))
    second = first.model_copy(update={"version": 2})
    repo.publish(second, reviewed_sha256=plan_hash(second))
    repo.withdraw(second, reviewed_sha256=plan_hash(second))
    with engine.begin() as conn:
        conn.execute(
            update(public_briefing_heads).values(
                latest_version=1, latest_content_sha256=one.content_sha256
            )
        )
    for read in (lambda: repo.load(first.slug), lambda: repo.load(first.slug, 1), repo.list_latest):
        with pytest.raises(StorageCorruption):
            read()


def test_public_lifecycle_preserves_existing_private_session_research_and_evidence(
    historical_expanded_run, engine
):
    names = [
        "auth_users",
        "auth_sessions",
        "auth_workspace_memberships",
        "research_runs",
        "research_events",
        "research_budget_months",
        "source_documents",
        "document_versions",
        "parsed_representations",
        "citations",
        "evidence_snapshots",
        "outbox",
    ]

    def snapshot():
        with engine.connect() as conn:
            return {
                name: sorted(
                    str(row) for row in conn.execute(text(f"SELECT row_to_json(t) FROM {name} t"))
                )
                for name in names
            }

    before = snapshot()
    assert any(before.values())
    repository = pb.PublicBriefingRepository(engine)
    first = plan()
    repository.publish(first, reviewed_sha256=plan_hash(first))
    repository.list_latest()
    repository.load(first.slug)
    repository.load(first.slug, 1)
    repository.withdraw(first, reviewed_sha256=plan_hash(first))
    assert snapshot() == before


def test_same_slug_publication_blocks_on_actual_postgresql_transaction_lock(repo, engine):
    from threading import Event
    from time import monotonic

    from sqlalchemy import event

    first = plan()
    acquired, second_started, release = Event(), Event(), Event()
    pids = {}

    def before(conn, cursor, statement, parameters, context, many):
        if "SELECT pg_advisory_xact_lock" not in statement:
            return
        pid = conn.connection.driver_connection.info.backend_pid
        if "first" not in pids:
            pids["first"] = pid
        elif pid != pids["first"]:
            pids["second"] = pid
            second_started.set()

    def after(conn, cursor, statement, parameters, context, many):
        if (
            "SELECT pg_advisory_xact_lock" in statement
            and conn.connection.driver_connection.info.backend_pid == pids.get("first")
        ):
            acquired.set()
            assert release.wait(timeout=10)

    event.listen(engine, "before_cursor_execute", before)
    event.listen(engine, "after_cursor_execute", after)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(repo.publish, first, reviewed_sha256=plan_hash(first))
            try:
                assert acquired.wait(timeout=5)
                two = pool.submit(repo.publish, first, reviewed_sha256=plan_hash(first))
                assert second_started.wait(timeout=5)
                deadline = monotonic() + 5
                with engine.connect() as observer:
                    while pids["first"] not in observer.scalar(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": pids["second"]}
                    ):
                        assert monotonic() < deadline
                        Event().wait(0.01)
                release.set()
                assert one.result(timeout=5) == two.result(timeout=5)
            finally:
                release.set()
    finally:
        event.remove(engine, "before_cursor_execute", before)
        event.remove(engine, "after_cursor_execute", after)
