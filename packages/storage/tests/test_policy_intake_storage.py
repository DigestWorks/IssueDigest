"""Synthetic PostgreSQL explicit reviewed intake storage boundaries."""

import importlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from issuedigest_storage.policy_collection import PolicyCollectionConfig, PolicyCollectionRepository
from sqlalchemy import event, inspect, text

NOW = datetime(2026, 10, 18, 12, tzinfo=UTC)


def api():
    try:
        return importlib.import_module("issuedigest_storage.policy_intake")
    except ModuleNotFoundError:
        pytest.fail("Reviewed intake storage is missing")


def config():
    return PolicyCollectionConfig(
        schema_version=1,
        expected_database="issuedigest_test",
        collection_id=uuid4(),
        news_ids=("123456789",),
        minimum_interval_seconds=60,
        max_age_seconds=120,
        max_attempts=16,
    )


def succeeded(engine, cfg, capture=b"capture", report=b"report", now=NOW):
    with PolicyCollectionRepository(engine).lease(cfg) as session:
        attempt = session.start(now=now).attempt
        session.succeed(attempt.attempt_id, capture, report, finished_at=now)
    return attempt.attempt_id


def test_fixed_successful_capture_is_read_only_not_latest(engine):
    a, cfg = api(), config()
    first = succeeded(engine, cfg)
    succeeded(engine, cfg, b"later", b"later report", NOW + timedelta(seconds=60))
    statements = []

    def observe(conn, cursor, statement, parameters, context, many):
        statements.append(statement)
        if "FROM policy_collection" in statement:
            assert conn.exec_driver_sql("SHOW transaction_read_only").scalar() == "on"

    event.listen(engine, "before_cursor_execute", observe)
    try:
        repo = a.PolicyIntakeRepository(engine)
        baseline = repo.load_capture(cfg, first)
        assert baseline.attempt.attempt_id == first
        assert baseline.capture_bytes == b"capture"
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert not any(
        s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE"))
        or "advisory" in s.lower()
        for s in statements
    )
    with pytest.raises(a.PolicyIntakeError):
        repo.load_capture(cfg, uuid4())


def test_receipt_schema_is_registered_and_has_scope_relations(engine):
    a = api()
    assert a.PolicyIntakeRepository(engine)._engine is engine
    with engine.connect() as conn:
        inspector = inspect(conn)
        assert "policy_intake_receipts" in inspector.get_table_names()
        assert inspector.get_pk_constraint("policy_intake_receipts")["constrained_columns"] == [
            "workspace_id",
            "attempt_id",
            "news_id",
        ]
        assert len(inspector.get_foreign_keys("policy_intake_receipts")) >= 3
        assert conn.scalar(text("SELECT count(*) FROM policy_intake_receipts")) == 0


def plan_for(
    engine,
    cfg,
    *,
    now=NOW,
    body="주거 지원 정책",
    workspace=None,
    document=None,
    quote=None,
    previous=None,
):
    import json
    from hashlib import sha256

    from issuedigest_domain import (
        Citation,
        DocumentVersion,
        EvidenceBundle,
        SourceDocument,
        SourcePresentation,
    )
    from issuedigest_ingestion import (
        extract_policy_html,
        locate_policy_html_quote,
        to_policy_html_representation,
    )
    from issuedigest_worker.policy_changes import compare_policy_captures

    a = api()
    workspace, document = workspace or uuid4(), document or uuid4()
    entries, articles = [], []
    for news in cfg.news_ids:
        url = f"https://www.korea.kr/news/policyNewsView.do?newsId={news}"
        notice = (
            "이 자료는 텍스트에 한하여 공공누리 제1유형(출처표시)의 조건에 따라 이용할 수 있습니다."
        )
        html = (
            f'<html><head><meta property="og:url" content="{url}"></head><body>'
            '<div class="view_title"><h1>합성 정책</h1></div>'
            '<div class="variety"><div class="info">2026.10.16 '
            '<a class="gotosite">합성부</a></div></div>'
            f'<div class="view_cont"><p>{body}</p></div>'
            f'<div class="kogl_wrap"><div class="type"><span>{notice}</span></div></div>'
            "</body></html>"
        )
        articles.append(dict(news_id=news, canonical_url=url, html=html))
    raw = json.dumps(
        dict(schema_version=1, collected_at=now.isoformat(), articles=articles), ensure_ascii=False
    ).encode()
    report = compare_policy_captures(raw, previous_raw=previous)
    attempt = succeeded(engine, cfg, raw, report.model_dump_json().encode(), now)
    for i, article in enumerate(articles):
        version, representation, snapshot = uuid4(), uuid4(), uuid4()
        doc_id = document if i == 0 else uuid4()
        extraction = extract_policy_html(
            article["html"].encode(),
            expected_sha256=sha256(article["html"].encode()).hexdigest(),
            canonical_url=article["canonical_url"],
        )
        parsed = to_policy_html_representation(
            extraction, representation_id=representation, document_version_id=version
        )
        bundle = EvidenceBundle(
            document=SourceDocument(
                document_id=doc_id,
                workspace_id=workspace,
                provider="korea_policy",
                source_id=article["news_id"],
                source_kind="government_document",
                canonical_url=article["canonical_url"],
            ),
            version=DocumentVersion(
                version_id=version,
                document_id=doc_id,
                raw_object_id=uuid4(),
                raw_sha256=sha256(raw).hexdigest(),
                media_type="application/vnd.issuedigest.policy-capture+json",
                collected_at=now,
            ),
            representation=parsed,
            citations=(
                Citation(
                    citation_id=uuid4(),
                    document_version_id=version,
                    representation_id=representation,
                    selector=locate_policy_html_quote(parsed, quote=quote or body),
                ),
            ),
        )
        entries.append(
            a.PolicyIntakeEntry(
                snapshot_id=snapshot,
                bundle=bundle,
                presentation=SourcePresentation(
                    snapshot_id=snapshot,
                    workspace_id=workspace,
                    title=extraction.title,
                    profile="policy-html-v1",
                ),
                fingerprint_sha256=next(
                    s.after_fingerprint for s in report.sources if s.source_id == article["news_id"]
                ),
            )
        )
    return a.PolicyIntakePlan(
        collection=cfg,
        attempt_id=attempt,
        workspace_id=workspace,
        approval_sha256="a" * 64,
        entries=tuple(entries),
    ), raw


def counts(engine):
    names = (
        "source_documents",
        "document_versions",
        "evidence_snapshots",
        "citations",
        "snapshot_citations",
        "outbox",
        "source_presentations",
        "evidence_search_projections",
        "policy_intake_receipts",
    )
    with engine.connect() as conn:
        return {n: conn.scalar(text(f"SELECT count(*) FROM {n}")) for n in names}


def test_first_intake_check_atomic_apply_and_exact_retry(engine):
    a, cfg = api(), config()
    plan, _ = plan_for(engine, cfg)
    repo = a.PolicyIntakeRepository(engine)
    before = counts(engine)
    checked = repo.check(plan)
    assert checked.outcome == "checked" and checked.new_versions == 1
    assert checked.receipts_created == 0 and counts(engine) == before
    applied = repo.apply(plan)
    assert applied.outcome == "applied" and applied.new_versions == 1
    assert applied.receipts_created == 1
    after = counts(engine)
    assert all(after[n] == before[n] + 1 for n in after)
    assert repo.apply(plan).outcome == "already_applied" and counts(engine) == after
    assert repo.check(plan).outcome == "checked" and counts(engine) == after
    with pytest.raises(a.PolicyIntakeError):
        repo.apply(plan.model_copy(update={"approval_sha256": "b" * 64}))
    assert "123456789" not in repr(plan)


def test_same_semantics_reuses_original_ids_but_quote_change_and_aba_create(engine):
    a, cfg = api(), config()
    first, raw = plan_for(engine, cfg)
    repo = a.PolicyIntakeRepository(engine)
    repo.apply(first)
    before = counts(engine)
    second, raw2 = plan_for(
        engine,
        cfg,
        now=NOW + timedelta(seconds=60),
        workspace=first.workspace_id,
        document=first.entries[0].bundle.document.document_id,
        previous=raw,
    )
    result = repo.apply(second)
    assert result.reused_versions == 1 and result.new_versions == 0
    after = counts(engine)
    assert after["policy_intake_receipts"] == 2
    assert {k: v for k, v in after.items() if k != "policy_intake_receipts"} == {
        k: v for k, v in before.items() if k != "policy_intake_receipts"
    }
    from issuedigest_storage.policy_intake_schema import policy_intake_receipts as receipts
    from sqlalchemy import select

    with engine.connect() as conn:
        assert conn.execute(select(receipts.c.snapshot_id)).scalars().all() == [
            first.entries[0].snapshot_id,
            first.entries[0].snapshot_id,
        ]
    quote, raw3 = plan_for(
        engine,
        cfg,
        now=NOW + timedelta(seconds=120),
        workspace=first.workspace_id,
        document=first.entries[0].bundle.document.document_id,
        quote="주거",
        previous=raw2,
    )
    assert repo.apply(quote).new_versions == 1
    changed, raw4 = plan_for(
        engine,
        cfg,
        now=NOW + timedelta(seconds=180),
        body="바뀐 정책",
        workspace=first.workspace_id,
        document=first.entries[0].bundle.document.document_id,
        previous=raw3,
    )
    assert repo.apply(changed).new_versions == 1
    back, _ = plan_for(
        engine,
        cfg,
        now=NOW + timedelta(seconds=240),
        workspace=first.workspace_id,
        document=first.entries[0].bundle.document.document_id,
        previous=raw4,
    )
    assert repo.apply(back).new_versions == 1
    assert counts(engine)["document_versions"] == 4


def test_busy_and_raw_report_tampering_fail_without_writes(engine):
    a, cfg = api(), config()
    plan, _ = plan_for(engine, cfg)
    repo = a.PolicyIntakeRepository(engine)
    before = counts(engine)
    with engine.begin() as conn:
        assert conn.scalar(text("SELECT pg_try_advisory_xact_lock(104704, 3)"))
        assert repo.apply(plan).outcome == "busy"
        assert repo.check(plan).new_versions == 1
    assert counts(engine) == before
    from issuedigest_storage.policy_collection_schema import policy_collection_attempts
    from sqlalchemy import update

    with engine.begin() as conn:
        conn.execute(update(policy_collection_attempts).values(capture_bytes=b"corrupt"))
    with pytest.raises(a.PolicyIntakeError):
        repo.apply(plan)
    assert counts(engine) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "report_order",
        "report_first",
        "report_time",
        "report_extra",
        "raw_duplicate",
        "raw_boolean",
        "raw_scope",
        "raw_time",
        "raw_url",
    ],
)
def test_stored_envelopes_reject_even_when_bytes_hash_is_updated(engine, mutation):
    import json
    from hashlib import sha256

    from issuedigest_storage.policy_collection_schema import policy_collection_attempts as attempts
    from sqlalchemy import update

    a, cfg = api(), config()
    plan, _ = plan_for(engine, cfg)
    baseline = a.PolicyIntakeRepository(engine).load_capture(cfg, plan.attempt_id)
    capture, report = json.loads(baseline.capture_bytes), json.loads(baseline.report_bytes)
    target = "capture"
    if mutation.startswith("report"):
        target = "report"
        if mutation == "report_order":
            report["sources"][0]["source_id"] = "123456788"
        elif mutation == "report_first":
            report["sources"][0]["status"] = "unchanged"
            report["sources"][0]["before_fingerprint"] = report["sources"][0]["after_fingerprint"]
        elif mutation == "report_time":
            report["before_capture_sha256"] = "f" * 64
            report["before_collected_at"] = report["after_collected_at"]
        else:
            report["extra"] = True
    elif mutation == "raw_boolean":
        capture["schema_version"] = True
    elif mutation == "raw_scope":
        capture["articles"][0]["news_id"] = "123456788"
    elif mutation == "raw_time":
        capture["collected_at"] = "2026-10-17T00:00:00Z"
    elif mutation == "raw_url":
        capture["articles"][0]["canonical_url"] += "&extra=bad"
    raw = json.dumps(report if target == "report" else capture).encode()
    if mutation == "raw_duplicate":
        raw = raw[:-1] + b',"schema_version":1}'
    with engine.begin() as conn:
        conn.execute(
            update(attempts)
            .where(attempts.c.attempt_id == plan.attempt_id)
            .values(**{target + "_bytes": raw, target + "_sha256": sha256(raw).hexdigest()})
        )
    before = counts(engine)
    with pytest.raises(a.PolicyIntakeError):
        a.PolicyIntakeRepository(engine).check(plan)
    assert counts(engine) == before


def test_two_sources_roll_back_first_complete_graph_on_second_insert_failure(engine):
    a = api()
    cfg = config().model_copy(update={"news_ids": ("123456788", "123456789")})
    plan, _ = plan_for(engine, cfg)
    assert len(plan.entries) == 2
    before = counts(engine)
    snapshots = 0

    def fail_second(conn, cursor, statement, parameters, context, many):
        nonlocal snapshots
        if statement.startswith("INSERT INTO evidence_snapshots"):
            snapshots += 1
            if snapshots == 2:
                raise RuntimeError("private second graph failure")

    event.listen(engine, "before_cursor_execute", fail_second)
    try:
        with pytest.raises(a.PolicyIntakeError, match="^Policy intake unavailable$"):
            a.PolicyIntakeRepository(engine).apply(plan)
    finally:
        event.remove(engine, "before_cursor_execute", fail_second)
    assert snapshots == 2 and counts(engine) == before
    assert a.PolicyIntakeRepository(engine).apply(plan).new_versions == 2


def test_commit_ack_loss_is_unknown_and_exact_retry_detects_actual_commit(engine, monkeypatch):
    from sqlalchemy import Connection

    a, cfg = api(), config()
    plan, _ = plan_for(engine, cfg)
    repo = a.PolicyIntakeRepository(engine)
    original = Connection.commit

    def ack_lost(conn):
        original(conn)
        raise RuntimeError("private acknowledgement loss")

    with monkeypatch.context() as scoped:
        scoped.setattr(Connection, "commit", ack_lost)
        with pytest.raises(a.PolicyIntakeCommitUnknown, match="^Policy intake commit unknown$"):
            repo.apply(plan)
    before = counts(engine)
    assert before["policy_intake_receipts"] == 1
    assert repo.apply(plan).outcome == "already_applied"
    assert counts(engine) == before


@pytest.mark.parametrize(
    "mutation",
    [
        "snapshot_hash",
        "version_hash",
        "citation_link",
        "outbox",
        "presentation",
        "receipt_fingerprint",
        "origin_collected_at",
    ],
)
def test_retry_revalidates_canonical_graph_receipt_and_presentation(engine, mutation):
    from issuedigest_storage import schema
    from issuedigest_storage.policy_intake_schema import policy_intake_receipts as receipts
    from issuedigest_storage.research_schema import source_presentations
    from sqlalchemy import delete, update

    a, cfg = api(), config()
    first, raw = plan_for(engine, cfg)
    repo = a.PolicyIntakeRepository(engine)
    repo.apply(first)
    plan = first
    if mutation == "origin_collected_at":
        plan, _ = plan_for(
            engine,
            cfg,
            now=NOW + timedelta(seconds=60),
            previous=raw,
            workspace=first.workspace_id,
            document=first.entries[0].bundle.document.document_id,
        )
        repo.apply(plan)
    with engine.begin() as conn:
        if mutation == "snapshot_hash":
            conn.execute(update(schema.evidence_snapshots).values(content_sha256="0" * 64))
        elif mutation == "version_hash":
            conn.execute(update(schema.document_versions).values(content_sha256="0" * 64))
        elif mutation == "citation_link":
            conn.execute(delete(schema.snapshot_citations))
        elif mutation == "outbox":
            conn.execute(delete(schema.outbox))
        elif mutation == "presentation":
            payload = first.entries[0].presentation.model_dump(mode="json")
            payload["title"] = "변조된 제목"
            conn.execute(update(source_presentations).values(payload=payload))
        elif mutation == "receipt_fingerprint":
            conn.execute(update(receipts).values(fingerprint_sha256="f" * 64))
        else:
            conn.execute(
                update(receipts)
                .where(receipts.c.attempt_id == first.attempt_id)
                .values(capture_collected_at=NOW - timedelta(seconds=1))
            )
    before = counts(engine)
    with pytest.raises(a.PolicyIntakeError):
        repo.apply(plan)
    assert counts(engine) == before


def test_cross_channel_last_approval_is_validated_and_reused(engine):
    a, cfg = api(), config()
    first, _ = plan_for(engine, cfg)
    repo = a.PolicyIntakeRepository(engine)
    repo.apply(first)
    other, _ = plan_for(
        engine,
        config(),
        now=NOW + timedelta(seconds=60),
        workspace=first.workspace_id,
        document=first.entries[0].bundle.document.document_id,
    )
    assert repo.apply(other).reused_versions == 1


def test_chronology_rejects_older_or_equal_capture_after_later_approval(engine):
    a, cfg = api(), config()
    first, raw = plan_for(engine, cfg)
    second, _ = plan_for(
        engine,
        cfg,
        now=NOW + timedelta(seconds=60),
        previous=raw,
        workspace=first.workspace_id,
        document=first.entries[0].bundle.document.document_id,
    )
    repo = a.PolicyIntakeRepository(engine)
    repo.apply(second)
    before = counts(engine)
    with pytest.raises(a.PolicyIntakeError):
        repo.apply(first)
    # A distinct channel can capture at exactly the previous approved instant.
    same, _ = plan_for(
        engine,
        config(),
        now=NOW + timedelta(seconds=60),
        workspace=first.workspace_id,
        document=first.entries[0].bundle.document.document_id,
    )
    with pytest.raises(a.PolicyIntakeError):
        repo.apply(same)
    assert counts(engine) == before


@pytest.mark.parametrize(
    "target",
    [
        "snapshot_id",
        "version_id",
        "representation_id",
        "raw_object_id",
        "citation_id",
        "document_id",
        "workspace_id",
        "graph",
        "fingerprint",
    ],
)
def test_candidate_conflicting_ids_and_provenance_are_rejected_before_writes(engine, target):
    from issuedigest_domain import EvidenceBundle

    a, cfg = api(), config()
    first, raw = plan_for(engine, cfg)
    repo = a.PolicyIntakeRepository(engine)
    repo.apply(first)
    plan, _ = plan_for(
        engine,
        cfg,
        body="변경된 정책",
        now=NOW + timedelta(seconds=60),
        previous=raw,
        workspace=first.workspace_id,
        document=first.entries[0].bundle.document.document_id,
    )
    entry, original = plan.entries[0], first.entries[0]
    data = entry.bundle.model_dump(mode="json")
    if target == "snapshot_id":
        entry = entry.model_copy(
            update={
                "snapshot_id": original.snapshot_id,
                "presentation": entry.presentation.model_copy(
                    update={"snapshot_id": original.snapshot_id}
                ),
            }
        )
    elif target == "fingerprint":
        entry = entry.model_copy(update={"fingerprint_sha256": "e" * 64})
    else:
        if target == "version_id":
            old = str(original.bundle.version.version_id)
            data["version"]["version_id"] = old
            data["representation"]["document_version_id"] = old
            data["citations"][0]["document_version_id"] = old
        elif target == "representation_id":
            old = str(original.bundle.representation.representation_id)
            data["representation"]["representation_id"] = old
            data["citations"][0]["representation_id"] = old
        elif target == "raw_object_id":
            data["version"]["raw_object_id"] = str(original.bundle.version.raw_object_id)
        elif target == "citation_id":
            data["citations"][0]["citation_id"] = str(original.bundle.citations[0].citation_id)
        elif target == "document_id":
            data["document"]["document_id"] = str(uuid4())
            data["version"]["document_id"] = data["document"]["document_id"]
        elif target == "workspace_id":
            data["document"]["workspace_id"] = str(uuid4())
        else:
            data["version"]["raw_sha256"] = "f" * 64
        entry = entry.model_copy(update={"bundle": EvidenceBundle.model_validate(data)})
    plan = plan.model_copy(update={"entries": (entry,)})
    before = counts(engine)
    with pytest.raises(a.PolicyIntakeError):
        repo.check(plan)
    with pytest.raises(a.PolicyIntakeError):
        repo.apply(plan)
    assert counts(engine) == before


def test_first_tracking_creates_new_baseline_instead_of_guessing_legacy_equal(engine):
    from issuedigest_storage import EvidenceRepository

    a, cfg = api(), config()
    old, raw = plan_for(engine, cfg)
    EvidenceRepository(engine).save(old.entries[0].snapshot_id, old.entries[0].bundle)
    later, _ = plan_for(
        engine,
        cfg,
        now=NOW + timedelta(seconds=60),
        previous=raw,
        workspace=old.workspace_id,
        document=old.entries[0].bundle.document.document_id,
    )
    assert a.PolicyIntakeRepository(engine).apply(later).new_versions == 1
    assert counts(engine)["document_versions"] == 2
    assert (
        EvidenceRepository(engine).load(old.workspace_id, old.entries[0].snapshot_id)
        == old.entries[0].bundle
    )


def test_check_uses_readonly_and_no_advisory_lock_or_projection_repair(engine):
    from issuedigest_storage.search_schema import projections
    from sqlalchemy import delete

    a, cfg = api(), config()
    plan, _ = plan_for(engine, cfg)
    repo = a.PolicyIntakeRepository(engine)
    repo.apply(plan)
    with engine.begin() as conn:
        conn.execute(delete(projections))
    before = counts(engine)
    statements = []
    observing = False

    def observe(conn, cursor, statement, parameters, context, many):
        nonlocal observing
        if observing:
            return
        statements.append(statement)
        observing = True
        try:
            assert conn.exec_driver_sql("SHOW transaction_read_only").scalar() == "on"
        finally:
            observing = False

    event.listen(engine, "before_cursor_execute", observe)
    try:
        assert repo.check(plan).outcome == "checked"
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert not any(
        s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) or "advisory" in s.lower()
        for s in statements
    )
    assert counts(engine) == before
    assert repo.apply(plan).outcome == "already_applied"
    after = counts(engine)
    assert after["evidence_search_projections"] == 1
    assert {k: v for k, v in after.items() if k != "evidence_search_projections"} == {
        k: v for k, v in before.items() if k != "evidence_search_projections"
    }


def test_loss_of_original_transaction_lock_after_write_rolls_everything_back(engine):
    a, cfg = api(), config()
    plan, _ = plan_for(engine, cfg)
    before = counts(engine)
    observed = False

    def invalidate_after_receipt(conn, cursor, statement, parameters, context, many):
        nonlocal observed
        if statement.startswith("INSERT INTO policy_intake_receipts"):
            observed = True
            conn.invalidate()

    event.listen(engine, "after_cursor_execute", invalidate_after_receipt)
    try:
        with pytest.raises(a.PolicyIntakeError):
            a.PolicyIntakeRepository(engine).apply(plan)
    finally:
        event.remove(engine, "after_cursor_execute", invalidate_after_receipt)
    assert observed and counts(engine) == before


def test_migration_roundtrip_preserves_existing_private_public_and_session_rows(
    engine, database_url
):
    from alembic import command
    from issuedigest_domain import EvidenceBundle
    from issuedigest_domain.public_briefings import PublicBriefingPlan, plan_hash
    from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
    from issuedigest_storage.public_briefings import PublicBriefingRepository

    from conftest import bundle_data, migration_config, public_plan_data

    bundle = EvidenceBundle.model_validate(bundle_data())
    EvidenceRepository(engine).save(uuid4(), bundle)
    actor = uuid4()
    IdentityRepository(engine).register_identity(actor, "synthetic", str(actor))
    SessionRepository(engine).issue_session(actor)
    public = PublicBriefingPlan.model_validate(public_plan_data())
    PublicBriefingRepository(engine).publish(public, reviewed_sha256=plan_hash(public))
    cfg = config()
    attempt = succeeded(engine, cfg)
    names = (
        "source_documents",
        "document_versions",
        "parsed_representations",
        "citations",
        "evidence_snapshots",
        "snapshot_citations",
        "outbox",
        "auth_users",
        "auth_sessions",
        "public_briefings",
        "public_briefing_heads",
        "policy_collection_channels",
        "policy_collection_attempts",
    )

    def originals():
        with engine.connect() as conn:
            return {n: conn.execute(text(f"SELECT * FROM {n}")).mappings().all() for n in names}

    before = originals()
    migration = migration_config(database_url)
    command.downgrade(migration, "0008_policy_collection")
    assert originals() == before
    command.upgrade(migration, "head")
    command.upgrade(migration, "head")
    assert originals() == before
    assert (
        api().PolicyIntakeRepository(engine).load_capture(cfg, attempt).capture_bytes == b"capture"
    )


def test_receipts_have_read_only_structural_contract_and_unique_current_order(engine):
    from issuedigest_storage.policy_intake_schema import policy_intake_receipts as receipts
    from sqlalchemy import select

    a, cfg = api(), config()
    plan, _ = plan_for(engine, cfg)
    a.PolicyIntakeRepository(engine).apply(plan)
    with engine.connect() as conn:
        row = conn.execute(select(receipts)).mappings().one()
        receipt = a.validate_policy_intake_receipt(row)
        assert receipt.snapshot_id == plan.entries[0].snapshot_id
        inspector = inspect(conn)
        assert any(
            u["column_names"] == ["workspace_id", "document_id", "capture_collected_at"]
            for u in inspector.get_unique_constraints("policy_intake_receipts")
        )
        assert any(
            i["name"] == "ix_policy_intake_latest"
            for i in inspector.get_indexes("policy_intake_receipts")
        )
    assert repr(receipt) == "PolicyIntakeReceipt()"
    for changes in (
        {"decision": "bad"},
        {"capture_sha256": "private"},
        {"workspace_id": str(uuid4())},
        {"capture_collected_at": NOW.replace(tzinfo=None)},
    ):
        with pytest.raises(a.PolicyIntakeError):
            a.validate_policy_intake_receipt(dict(row) | changes)


def test_autocommit_parent_engine_still_rolls_back_when_precommit_guard_fails(engine):
    a, cfg = api(), config()
    plan, _ = plan_for(engine, cfg)
    before = counts(engine)
    written = False

    def after(conn, cursor, statement, parameters, context, many):
        nonlocal written
        if statement.startswith("INSERT INTO policy_intake_receipts"):
            written = True

    def before_guard(conn, cursor, statement, parameters, context, many):
        if written and statement == "SELECT current_database()":
            raise RuntimeError("private precommit failure")

    event.listen(engine, "after_cursor_execute", after)
    event.listen(engine, "before_cursor_execute", before_guard)
    try:
        with pytest.raises(a.PolicyIntakeError):
            a.PolicyIntakeRepository(engine.execution_options(isolation_level="AUTOCOMMIT")).apply(
                plan
            )
    finally:
        event.remove(engine, "after_cursor_execute", after)
        event.remove(engine, "before_cursor_execute", before_guard)
    assert written and counts(engine) == before


def test_exact_retry_checks_stored_semantics_against_original_candidate(engine):
    from hashlib import sha256

    from issuedigest_storage import schema
    from issuedigest_storage.repository import _digest
    from sqlalchemy import update

    a, cfg = api(), config()
    plan, _ = plan_for(engine, cfg)
    repo = a.PolicyIntakeRepository(engine)
    repo.apply(plan)
    payload = plan.entries[0].bundle.model_dump(mode="json")
    parsed = payload["representation"]
    parsed["text"] += " 조작된 뒷부분"
    parsed["text_sha256"] = sha256(parsed["text"].encode()).hexdigest()
    with engine.begin() as conn:
        conn.execute(
            update(schema.parsed_representations).values(
                payload=parsed, content_sha256=_digest(parsed)
            )
        )
        conn.execute(
            update(schema.evidence_snapshots).values(
                payload=payload, content_sha256=_digest(payload)
            )
        )
    with pytest.raises(a.PolicyIntakeError):
        repo.apply(plan)


def test_constructor_performs_no_io_and_forged_plan_revalidates_before_connection(
    engine, monkeypatch
):
    a, cfg = api(), config()
    plan, _ = plan_for(engine, cfg)

    def forbidden(*args, **kwargs):
        raise AssertionError("connection must not open")

    monkeypatch.setattr(engine, "connect", forbidden)
    repo = a.PolicyIntakeRepository(engine)
    for changes in (
        {"attempt_id": str(uuid4())},
        {"entries": ()},
        {"approval_sha256": "private"},
        {"workspace_id": True},
    ):
        with pytest.raises(a.PolicyIntakeError):
            repo.apply(plan.model_copy(update=changes))


@pytest.mark.parametrize("state", ["running", "failed", "foreign_channel"])
def test_fixed_attempt_requires_exact_channel_and_success(engine, state):
    a, cfg = api(), config()
    with PolicyCollectionRepository(engine).lease(cfg) as session:
        attempt = session.start(now=NOW).attempt.attempt_id
        if state == "failed":
            session.fail(attempt, "capture_failed", finished_at=NOW)
        elif state == "foreign_channel":
            session.succeed(attempt, b"capture", b"report", finished_at=NOW)
    if state == "foreign_channel":
        cfg = config()
        succeeded(engine, cfg)
    before = counts(engine)
    with pytest.raises(a.PolicyIntakeError):
        a.PolicyIntakeRepository(engine).load_capture(cfg, attempt)
    assert counts(engine) == before
