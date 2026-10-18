"""Current approved question retrieval over real synthetic PostgreSQL intake."""

from datetime import timedelta
from uuid import uuid4

import pytest
from issuedigest_domain import EvidenceBundle, EvidenceSearchQuery
from issuedigest_storage import EvidenceRepository, StorageCorruption
from issuedigest_storage.policy_intake import PolicyIntakeRepository
from issuedigest_storage.research_retrieval import variant_candidates
from issuedigest_storage.search import search_evidence
from sqlalchemy import delete, event, inspect, text
from test_evidence_search import make_bundle
from test_policy_intake_storage import NOW, config, plan_for
from test_research_retrieval import retrieve, save


def intake(engine, cfg, *, prior=None, body="주거지원", seconds=0):
    plan, raw = plan_for(
        engine,
        cfg,
        now=NOW + timedelta(seconds=seconds),
        body=body,
        workspace=prior.workspace_id if prior else None,
        document=prior.entries[0].bundle.document.document_id if prior else None,
    )
    outcome = PolicyIntakeRepository(engine).apply(plan)
    return plan, raw, outcome


def test_latest_receipt_controls_same_changed_and_reverted_approvals(engine):
    cfg = config()
    first, _, _ = intake(engine, cfg, body="구판단어 주거지원")
    workspace, original = first.workspace_id, first.entries[0].snapshot_id
    same, _, outcome = intake(engine, cfg, prior=first, body="구판단어 주거지원", seconds=60)
    assert outcome.reused_versions == 1
    assert retrieve(engine, workspace, "주거지원") == (original,)

    changed, _, _ = intake(engine, cfg, prior=same, body="신판단어 주거지원", seconds=120)
    current = changed.entries[0].snapshot_id
    assert retrieve(engine, workspace, "구판단어") == ()
    assert retrieve(engine, workspace, "주거지원") == (current,)
    _, _, outcome = intake(engine, cfg, prior=changed, body="신판단어 주거지원", seconds=180)
    assert outcome.reused_versions == 1
    assert retrieve(engine, workspace, "주거지원") == (current,)

    reverted, _, _ = intake(engine, cfg, prior=changed, body="구판단어 주거지원", seconds=240)
    assert retrieve(engine, workspace, "신판단어") == ()
    assert retrieve(engine, workspace, "구판단어") == (reverted.entries[0].snapshot_id,)
    # Ordinary literal search and exact canonical readers retain historical evidence.
    with engine.connect() as conn:
        literal = search_evidence(conn, workspace, EvidenceSearchQuery(terms=("신판단어",)))
    assert {hit.snapshot_id for hit in literal.hits} == {current}
    assert EvidenceRepository(engine).load(workspace, original) == first.entries[0].bundle
    assert EvidenceRepository(engine).load(workspace, current) == changed.entries[0].bundle


def test_latest_unindexed_snapshot_never_falls_back_and_other_documents_stay_scoped(engine):
    cfg = config()
    first, _, _ = intake(engine, cfg)
    newer, _, _ = intake(engine, cfg, prior=first, body="주거지원 변경", seconds=60)
    from issuedigest_storage.search_schema import projections

    with engine.begin() as conn:
        conn.execute(
            delete(projections).where(projections.c.snapshot_id == newer.entries[0].snapshot_id)
        )
    legacy = save(engine, first.workspace_id, "주거지원")
    foreign, _, _ = intake(engine, config(), body="주거지원")
    with engine.connect() as conn:
        candidates = variant_candidates(conn, first.workspace_id, "주거지원")
    assert candidates.snapshot_ids == (legacy,)
    assert candidates.scanned_candidates == 1 and not candidates.truncated
    assert retrieve(engine, foreign.workspace_id, "주거지원") == (foreign.entries[0].snapshot_id,)


@pytest.mark.parametrize("damage", ["hash", "identity", "time", "source", "canonical"])
def test_selected_receipt_and_canonical_corruption_fail_closed(engine, damage):
    plan, _, _ = intake(engine, config())
    # Simulate owner corruption inside a rolled-back transaction, restoring constraints.
    with engine.connect() as conn:
        if damage == "hash":
            conn.execute(
                text(
                    "ALTER TABLE policy_intake_receipts DROP CONSTRAINT policy_intake_capture_hash"
                )
            )
            conn.execute(text("UPDATE policy_intake_receipts SET capture_sha256='invalid'"))
        elif damage == "identity":
            fk = next(
                fk["name"]
                for fk in inspect(conn).get_foreign_keys("policy_intake_receipts")
                if fk["referred_table"] == "evidence_snapshots"
            )
            conn.execute(text(f'ALTER TABLE policy_intake_receipts DROP CONSTRAINT "{fk}"'))
            conn.execute(text("UPDATE policy_intake_receipts SET version_id=:id"), {"id": uuid4()})
        elif damage == "time":
            conn.execute(
                text(
                    "UPDATE policy_intake_receipts SET capture_collected_at="
                    "capture_collected_at + interval '1 minute'"
                )
            )
        elif damage == "source":
            conn.execute(text("UPDATE policy_intake_receipts SET news_id='987654321'"))
        else:
            conn.execute(
                text(
                    "UPDATE parsed_representations SET "
                    "payload=jsonb_set(payload,'{text}','\"forged\"')"
                )
            )
        with pytest.raises(StorageCorruption):
            variant_candidates(conn, plan.workspace_id, "주거지원")


def test_all_untracked_old_versions_are_excluded_before_candidate_budget(engine):
    cfg = config()
    plan, _ = plan_for(engine, cfg, body="주거지원")
    # An existing pre-intake version has enough matching units to exhaust the cap.
    old = make_bundle(
        workspace=plan.workspace_id,
        cells=tuple({"cell_id": str(i), "text": "주거지원"} for i in range(210)),
    )
    old = EvidenceBundle(
        document=plan.entries[0].bundle.document,
        version=old.version.model_copy(
            update={"document_id": plan.entries[0].bundle.document.document_id}
        ),
        representation=old.representation,
        citations=old.citations,
    )
    old_id = uuid4()
    repo = EvidenceRepository(engine)
    repo.save(old_id, old)
    repo.rebuild_projection(plan.workspace_id, old_id)
    PolicyIntakeRepository(engine).apply(plan)
    with engine.connect() as conn:
        candidates = variant_candidates(conn, plan.workspace_id, "주거지원")
    assert candidates.snapshot_ids == (plan.entries[0].snapshot_id,)
    assert candidates.scanned_candidates == 1 and not candidates.truncated


def test_frozen_run_and_generic_parent_keep_old_citations_after_new_approval(engine):
    from issuedigest_agents.research import AIOutput, build_canvas
    from issuedigest_domain.research_journey import ResearchRequest, ResearchResult
    from issuedigest_storage import IdentityRepository, SessionRepository
    from issuedigest_storage.research import ResearchRepository

    first, _, _ = intake(engine, config(), body="주거지원 구판")
    workspace, old = first.workspace_id, first.entries[0]
    actor = uuid4()
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, workspace, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    parent = repo.submit(token, workspace, ResearchRequest(request_id=uuid4(), question="주거지원"))
    frozen, sources = repo.worker_load(parent.run_id)
    assert frozen.snapshot_ids == (old.snapshot_id,)

    changed, _, _ = intake(engine, config(), prior=first, body="주거지원 신판", seconds=60)
    assert repo.worker_load(parent.run_id) == (frozen, sources)
    proposal = AIOutput.model_validate(
        {
            "outcome": "answer",
            "modules": [
                {
                    "kind": "summary",
                    "title": "해석",
                    "claims": [
                        {
                            "text": "합성 해석",
                            "citation_ids": [str(old.bundle.citations[0].citation_id)],
                        }
                    ],
                }
            ],
        }
    )
    result = ResearchResult(
        canvas=build_canvas(parent.run_id, workspace, sources, proposal),
        source_titles={old.bundle.document.document_id: "합성 정책"},
    )
    assert repo.worker_transition(parent.run_id, "completed", result=result)
    child = repo.submit(
        token,
        workspace,
        ResearchRequest(
            request_id=uuid4(), question="더 자세히 알려줘", parent_run_id=parent.run_id
        ),
    )
    child_run, child_sources = repo.worker_load(child.run_id)
    assert child_run.snapshot_ids == (old.snapshot_id,)
    assert child_sources == sources
    repo.cancel(token, workspace, child.run_id)
    fresh = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question="주거지원", parent_run_id=parent.run_id),
    )
    assert repo.worker_load(fresh.run_id)[0].snapshot_ids == (changed.entries[0].snapshot_id,)
    assert repo.get_run(token, workspace, parent.run_id).result == result


def test_query_needs_only_receipt_select_plus_existing_canonical_index_rights(engine):
    plan, _, _ = intake(engine, config())
    role = "synthetic_intake_query_" + uuid4().hex
    tables = (
        "source_documents,document_versions,parsed_representations,citations,"
        "snapshot_citations,evidence_snapshots,evidence_search_projections,"
        "evidence_search_units,policy_intake_receipts"
    )
    with engine.connect() as conn:
        # Transaction rollback removes the temporary role and its exact grants.
        conn.execute(text(f"CREATE ROLE {role}"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(text(f"GRANT SELECT ON {tables} TO {role}"))
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        for table in ("policy_collection_channels", "policy_collection_attempts"):
            assert not conn.scalar(
                text("SELECT has_table_privilege(current_user,:table,'SELECT')"), {"table": table}
            )
        assert not conn.scalar(
            text("SELECT has_table_privilege(current_user,'policy_intake_receipts','INSERT')")
        )
        statements = []

        def observe(conn, cursor, statement, parameters, context, many):
            statements.append(statement)

        event.listen(conn, "before_cursor_execute", observe)
        try:
            candidates = variant_candidates(conn, plan.workspace_id, "주거지원")
        finally:
            event.remove(conn, "before_cursor_execute", observe)
        assert candidates.snapshot_ids == (plan.entries[0].snapshot_id,)
        assert statements and all(s.lstrip().upper().startswith("SELECT") for s in statements)
