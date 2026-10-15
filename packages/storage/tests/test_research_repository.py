"""Real PostgreSQL security, idempotency, budget and restart persistence."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from hashlib import sha256
from threading import Event, current_thread
from uuid import uuid4

import pytest
from issuedigest_agents.research import AIOutput, build_canvas
from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import ResearchRequest, ResearchResult
from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
from issuedigest_storage.research import ResearchConflict, ResearchForbidden, ResearchRepository
from issuedigest_storage.research_schema import research_runs
from pydantic import ValidationError
from sqlalchemy import update

from conftest import bundle_data


def setup_run(engine, role="owner"):
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, user = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(user, "synthetic", str(user))
    identities.set_membership(user, bundle.document.workspace_id, role)
    token = SessionRepository(engine).issue_session(user).token
    return bundle, snapshot, user, token


def test_duplicate_submission_is_same_run_and_different_input_conflicts(engine):
    bundle, snapshot, _user, token = setup_run(engine)
    repository = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    request = ResearchRequest(
        request_id=uuid4(), question="무엇이 다른가?", snapshot_ids=(snapshot,)
    )
    first = repository.submit(token, workspace, request)
    assert first.status == "queued"
    assert repository.submit(token, workspace, request).run_id == first.run_id
    with pytest.raises(ResearchConflict):
        repository.submit(token, workspace, request.model_copy(update={"question": "다른 질문"}))
    assert repository.list_runs(token, workspace).items[0].run_id == first.run_id
    assert repository.cancel(token, workspace, first.run_id).status == "cancelled"


def test_global_reservation_caps_and_active_workspace_run(engine):
    bundle, snapshot, _user, token = setup_run(engine)
    repository = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                repository.submit,
                token,
                workspace,
                ResearchRequest(request_id=uuid4(), question="질문", snapshot_ids=(snapshot,)),
            )
            for _ in range(2)
        ]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(future.result())
            except ResearchConflict:
                pass
    assert len(outcomes) == 1
    assert repository.get_run(token, workspace, outcomes[0].run_id).run_id == outcomes[0].run_id


def test_viewer_cannot_submit_and_revoked_membership_cannot_read(engine):
    bundle, snapshot, user, token = setup_run(engine, "viewer")
    repository = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    with pytest.raises(ResearchForbidden):
        repository.submit(
            token,
            workspace,
            ResearchRequest(request_id=uuid4(), question="질문", snapshot_ids=(snapshot,)),
        )
    assert repository.list_sources(token, workspace).items[0].title == "수집 자료"
    IdentityRepository(engine).set_membership(user, workspace, "viewer", False)
    assert repository.list_sources(token, workspace) is None


def test_operator_title_and_monthly_budget_are_durable(engine):
    from issuedigest_domain.research_journey import SourcePresentation
    from issuedigest_storage.research import ResearchBudgetExceeded
    from issuedigest_storage.research_schema import research_budget_months
    from sqlalchemy import insert, select

    bundle, snapshot, _actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
    presentation = SourcePresentation(
        snapshot_id=snapshot,
        workspace_id=bundle.document.workspace_id,
        title="검증된 정부 문서",
        profile="operator-verified-v1",
    )
    repo.upsert_presentation(presentation)
    assert (
        repo.list_sources(token, bundle.document.workspace_id).items[0].title == "검증된 정부 문서"
    )
    with engine.begin() as conn:
        month = conn.scalar(
            select(
                __import__("sqlalchemy").func.to_char(
                    __import__("sqlalchemy").func.clock_timestamp(), "YYYY-MM"
                )
            )
        )
        conn.execute(
            insert(research_budget_months).values(
                month=month, reserved_usd=10, reservation_count=40
            )
        )
    with pytest.raises(ResearchBudgetExceeded):
        repo.submit(
            token,
            bundle.document.workspace_id,
            ResearchRequest(request_id=uuid4(), question="질문", snapshot_ids=(snapshot,)),
        )
    assert repo.list_runs(token, bundle.document.workspace_id).items == ()


def test_worker_demotion_prevents_result_publication(engine):
    bundle, snapshot, actor, token = setup_run(engine, "editor")
    repo = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    run = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question="질문", snapshot_ids=(snapshot,)),
    )
    assert run is not None
    IdentityRepository(engine).set_membership(actor, workspace, "viewer")
    assert repo.worker_load(run.run_id) is None
    final = repo.get_run(token, workspace, run.run_id)
    assert (
        final is not None and final.status == "failed" and final.error_code == "authority_changed"
    )


def test_replay_does_not_regress_progress_or_duplicate_events(engine):
    bundle, snapshot, _actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    run = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question="질문", snapshot_ids=(snapshot,)),
    )
    assert run is not None
    for status in ("retrieving", "generating", "validating"):
        assert repo.worker_transition(run.run_id, status)
    for status in ("retrieving", "generating", "validating"):
        assert repo.worker_transition(run.run_id, status)
    current = repo.get_run(token, workspace, run.run_id)
    assert current is not None
    assert current.status == "validating"
    assert [event.status for event in current.events] == [
        "queued",
        "retrieving",
        "generating",
        "validating",
    ]


def test_cancel_and_publication_share_lock_order(engine, monkeypatch):
    bundle, snapshot, _actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    run = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question="질문", snapshot_ids=(snapshot,)),
    )
    assert run is not None
    loaded = repo.worker_load(run.run_id)
    assert loaded is not None
    sources = loaded[1]
    output = AIOutput.model_validate(
        {
            "outcome": "answer",
            "modules": [
                {
                    "kind": "summary",
                    "title": "요약",
                    "claims": [
                        {"text": "합성 해석", "citation_ids": [bundle.citations[0].citation_id]}
                    ],
                }
            ],
        }
    )
    result = ResearchResult(
        canvas=build_canvas(run.run_id, workspace, sources, output),
        source_titles={bundle.document.document_id: "합성 문서"},
    )
    cancel_member_held, publisher_at_member = Event(), Event()
    original_actor = ResearchRepository._actor
    original_member = ResearchRepository._member

    def actor_gate(conn, session_token, workspace_id, *, write=False):
        actor = original_actor(conn, session_token, workspace_id, write=write)
        if current_thread().name == "cancel-race" and write:
            cancel_member_held.set()
            assert publisher_at_member.wait(5)
        return actor

    def member_gate(conn, user_id, workspace_id, *, write=False):
        if current_thread().name == "publish-race":
            publisher_at_member.set()
        return original_member(conn, user_id, workspace_id, write=write)

    monkeypatch.setattr(ResearchRepository, "_actor", staticmethod(actor_gate))
    monkeypatch.setattr(ResearchRepository, "_member", staticmethod(member_gate))

    def cancel():
        current_thread().name = "cancel-race"
        return repo.cancel(token, workspace, run.run_id)

    def publish():
        current_thread().name = "publish-race"
        return repo.worker_transition(run.run_id, "completed", result=result)

    with ThreadPoolExecutor(max_workers=2) as pool:
        cancelling = pool.submit(cancel)
        assert cancel_member_held.wait(5)
        publishing = pool.submit(publish)
        assert cancelling.result(timeout=7).status == "cancelled"
        assert publishing.result(timeout=7) is False
    final = repo.get_run(token, workspace, run.run_id)
    assert final is not None and final.status == "cancelled" and final.result is None


def test_timeline_jsonb_reopens_lists_and_supplies_followup_context(engine):
    data = bundle_data()
    original_text = data["representation"]["text"]
    event_day = "2024-01-02"
    data["representation"]["text"] = original_text + " " + event_day
    data["representation"]["text_sha256"] = sha256(
        data["representation"]["text"].encode()
    ).hexdigest()
    data["representation"]["pages"][0]["end"] = len(data["representation"]["text"])
    citation_id = uuid4()
    data["citations"].append(
        {
            "citation_id": str(citation_id),
            "document_version_id": data["version"]["version_id"],
            "representation_id": data["representation"]["representation_id"],
            "selector": {
                "kind": "text",
                "start": len(original_text) + 1,
                "end": len(original_text) + 11,
                "quote": event_day,
            },
        }
    )
    bundle = EvidenceBundle.model_validate(data)
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    parent = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question="어느 날짜?", snapshot_ids=(snapshot,)),
    )
    assert parent is not None
    loaded = repo.worker_load(parent.run_id)
    assert loaded is not None
    output = AIOutput.model_validate(
        {
            "outcome": "answer",
            "modules": [
                {
                    "kind": "timeline",
                    "title": "날짜",
                    "claims": [
                        {
                            "text": "합성 날짜 해석",
                            "citation_ids": [str(citation_id)],
                            "event_date": event_day,
                        }
                    ],
                }
            ],
        }
    )
    result = ResearchResult(
        canvas=build_canvas(parent.run_id, workspace, loaded[1], output),
        source_titles={bundle.document.document_id: "합성 일정 자료"},
    )
    for status in ("retrieving", "generating", "validating"):
        assert repo.worker_transition(parent.run_id, status)
    assert repo.worker_transition(parent.run_id, "completed", result=result)

    reopened = repo.get_run(token, workspace, parent.run_id)
    assert reopened is not None and reopened.result is not None
    assert reopened.result.canvas.research.claims[0].valid_period.start_date == date(2024, 1, 2)
    assert repo.list_runs(token, workspace).items[0].run_id == parent.run_id
    child = repo.submit(
        token,
        workspace,
        ResearchRequest(
            request_id=uuid4(),
            question="그다음은?",
            snapshot_ids=(snapshot,),
            parent_run_id=parent.run_id,
        ),
    )
    assert child is not None
    context = repo.worker_parent_context(child.run_id)
    assert context is not None and "합성 날짜 해석" in context

    damaged = result.model_dump(mode="json")
    damaged["canvas"]["research"]["claims"][0]["valid_period"]["start_date"] = "2024-02-30"
    with engine.begin() as conn:
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == parent.run_id)
            .values(result=damaged)
        )
    with pytest.raises(ValidationError):
        repo.get_run(token, workspace, parent.run_id)
    with pytest.raises(ValidationError):
        repo.list_runs(token, workspace)
    with pytest.raises(ValidationError):
        repo.worker_parent_context(child.run_id)
