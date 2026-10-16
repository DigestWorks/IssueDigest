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
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
    identities = IdentityRepository(engine)
    identities.register_identity(user, "synthetic", str(user))
    identities.set_membership(user, bundle.document.workspace_id, role)
    token = SessionRepository(engine).issue_session(user).token
    return bundle, snapshot, user, token


def test_duplicate_submission_is_same_run_and_different_input_conflicts(engine):
    bundle, snapshot, _user, token = setup_run(engine)
    repository = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    request = ResearchRequest(request_id=uuid4(), question="80% 의미는?")
    first = repository.submit(token, workspace, request)
    assert first.status == "queued" and first.snapshot_ids == ()
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
                ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
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
            ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
        )
    assert repository.list_runs(token, workspace).items == ()
    IdentityRepository(engine).set_membership(user, workspace, "viewer", False)
    assert repository.list_runs(token, workspace) is None


def test_monthly_budget_is_durable(engine):
    from issuedigest_storage.research import ResearchBudgetExceeded
    from issuedigest_storage.research_schema import research_budget_months
    from sqlalchemy import insert, select

    bundle, _snapshot, _actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
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
            ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
        )
    assert repo.list_runs(token, bundle.document.workspace_id).items == ()


def test_worker_demotion_prevents_result_publication(engine):
    bundle, snapshot, actor, token = setup_run(engine, "editor")
    repo = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    run = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
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
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
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
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
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
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    parent = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
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
    historical = result.model_dump(mode="python")
    historical["canvas"]["research"]["claims"][0]["derivation"]["method_version"] = "research-v1"
    result = ResearchResult.model_validate(historical)
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


def add_topic(engine, workspace, text):
    data = bundle_data()
    data["document"]["workspace_id"] = str(workspace)
    data["representation"].update(
        text=text, text_sha256=sha256(text.encode()).hexdigest(), pages=[], tables=[]
    )
    data["version"]["media_type"] = "text/plain"
    data["citations"] = [data["citations"][0]]
    data["citations"][0]["selector"] = {"kind": "text", "start": 0, "end": len(text), "quote": text}
    bundle = EvidenceBundle.model_validate(data)
    snapshot = uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, workspace, snapshot)
    return snapshot, bundle


def test_question_retrieval_is_scoped_ranked_bounded_and_frozen(engine):
    bundle, unrelated, _actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    less_relevant, _ = add_topic(engine, workspace, "주거지원 관련 보도")
    expected = []
    for _ in range(6):
        snapshot, _ = add_topic(engine, workspace, "주거지원 확대 발표")
        expected.append(snapshot)
    foreign, _ = add_topic(engine, uuid4(), "주거지원 확대 발표")
    run = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question="주거지원은 확대가 무엇인가요?"),
    )
    assert run.snapshot_ids == ()
    loaded = repo.worker_load(run.run_id)
    assert loaded is not None
    current, sources = loaded
    assert current.status == "retrieving"
    assert current.snapshot_ids == tuple(sorted(expected, key=str)[:5])
    assert tuple(source[0] for source in sources) == current.snapshot_ids
    assert (
        unrelated not in current.snapshot_ids
        and less_relevant not in current.snapshot_ids
        and foreign not in current.snapshot_ids
    )
    assert [event.status for event in current.events] == ["queued", "retrieving"]
    add_topic(engine, workspace, "주거지원 확대 발표")
    replayed = repo.worker_load(run.run_id)
    assert replayed[0].snapshot_ids == current.snapshot_ids
    assert replayed[0].events == current.events
    assert (
        repo.submit(
            token, workspace, ResearchRequest(request_id=run.request_id, question=run.question)
        ).snapshot_ids
        == current.snapshot_ids
    )


def test_nohit_and_cancel_never_choose_default_sources(engine):
    bundle, _snapshot, _actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    run = repo.submit(
        token, workspace, ResearchRequest(request_id=uuid4(), question="양자컴퓨터 소식은?")
    )
    assert repo.worker_load(run.run_id) is None
    final = repo.get_run(token, workspace, run.run_id)
    assert final.status == "failed" and final.error_code == "insufficient_evidence"
    assert final.snapshot_ids == () and final.result is None
    assert final.input_tokens == 0 and final.output_tokens == 0
    assert repo.worker_load(run.run_id) is None
    assert repo.cancel(token, workspace, run.run_id) == final
    cancelled = repo.submit(
        token, workspace, ResearchRequest(request_id=uuid4(), question="80% 의미는?")
    )
    repo.cancel(token, workspace, cancelled.run_id)
    assert repo.worker_load(cancelled.run_id) is None
    assert repo.get_run(token, workspace, cancelled.run_id).snapshot_ids == ()


@pytest.mark.parametrize(
    "followup_question",
    ["더 자세히 알려줘", "무슨 의미인가?", "그것은 무엇인가?", "“그것은 무엇인가?”…"],
)
def test_only_topicless_followup_reuses_verified_parent_sources(engine, followup_question):
    bundle, snapshot, _actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    parent = repo.submit(
        token, workspace, ResearchRequest(request_id=uuid4(), question="80% 의미는?")
    )
    loaded = repo.worker_load(parent.run_id)
    proposal = AIOutput.model_validate(
        {
            "outcome": "answer",
            "modules": [
                {
                    "kind": "summary",
                    "title": "해석",
                    "claims": [
                        {
                            "text": "합성 의미",
                            "citation_ids": [str(bundle.citations[0].citation_id)],
                        }
                    ],
                }
            ],
        }
    )
    result = ResearchResult(
        canvas=build_canvas(parent.run_id, workspace, loaded[1], proposal),
        source_titles={bundle.document.document_id: "합성 문서"},
    )
    assert repo.worker_transition(parent.run_id, "completed", result=result)
    followup = repo.submit(
        token,
        workspace,
        ResearchRequest(
            request_id=uuid4(), question=followup_question, parent_run_id=parent.run_id
        ),
    )
    followup_loaded = repo.worker_load(followup.run_id)
    assert followup_loaded is not None
    assert followup_loaded[0].snapshot_ids == (snapshot,)
    repo.cancel(token, workspace, followup.run_id)
    new_topic = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question="양자컴퓨터는?", parent_run_id=parent.run_id),
    )
    assert repo.worker_load(new_topic.run_id) is None
    assert repo.get_run(token, workspace, new_topic.run_id).snapshot_ids == ()
    # The original completed result remains byte-for-byte readable under the same IDs.
    assert repo.get_run(token, workspace, parent.run_id).result == result


def test_failed_retrieval_transaction_does_not_publish_partial_sources(engine, monkeypatch):
    from issuedigest_storage import StorageCorruption
    from issuedigest_storage.search_schema import units

    bundle, snapshot, _actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
    )
    with engine.begin() as conn:
        conn.execute(
            update(units).where(units.c.snapshot_id == snapshot).values(text_sha256="b" * 64)
        )
    with pytest.raises(StorageCorruption):
        repo.worker_load(run.run_id)
    unchanged = repo.get_run(token, bundle.document.workspace_id, run.run_id)
    assert unchanged.status == "queued" and unchanged.snapshot_ids == ()
    assert len(unchanged.events) == 1


def test_parent_provenance_is_verified_before_topicless_reuse(engine):
    from issuedigest_storage import StorageCorruption

    bundle, snapshot, _actor, token = setup_run(engine)
    workspace = bundle.document.workspace_id
    repo = ResearchRepository(engine)
    parent = repo.submit(
        token, workspace, ResearchRequest(request_id=uuid4(), question="80% 의미는?")
    )
    loaded = repo.worker_load(parent.run_id)
    proposal = AIOutput(outcome="insufficient_evidence", message="합성 불충분", modules=())
    result = ResearchResult(
        canvas=build_canvas(parent.run_id, workspace, loaded[1], proposal),
        source_titles={bundle.document.document_id: "합성 자료"},
    )
    assert repo.worker_transition(parent.run_id, "completed", result=result)
    unrelated, _ = add_topic(engine, workspace, "다른 주제의 합성 자료")
    with engine.begin() as conn:
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == parent.run_id)
            .values(snapshot_ids=[str(unrelated)])
        )
    followup = repo.submit(
        token,
        workspace,
        ResearchRequest(
            request_id=uuid4(), question="더 자세히 알려줘", parent_run_id=parent.run_id
        ),
    )
    with pytest.raises(StorageCorruption):
        repo.worker_load(followup.run_id)
    assert repo.get_run(token, workspace, followup.run_id).snapshot_ids == ()


def test_result_publication_rejects_evidence_outside_fixed_provenance(engine):
    from issuedigest_storage import StorageError

    bundle, _snapshot, _actor, token = setup_run(engine)
    workspace = bundle.document.workspace_id
    repo = ResearchRepository(engine)
    run = repo.submit(token, workspace, ResearchRequest(request_id=uuid4(), question="80% 의미는?"))
    repo.worker_load(run.run_id)
    unrelated, other = add_topic(engine, workspace, "다른 주제")
    from issuedigest_domain.research_journey import presentation_for

    sources = ((unrelated, other, presentation_for(other, unrelated)),)
    proposal = AIOutput(outcome="insufficient_evidence", message="합성 불충분", modules=())
    forged = ResearchResult(
        canvas=build_canvas(run.run_id, workspace, sources, proposal),
        source_titles={other.document.document_id: "합성 자료"},
    )
    with pytest.raises(StorageError):
        repo.worker_transition(run.run_id, "completed", result=forged)
    assert repo.get_run(token, workspace, run.run_id).status == "retrieving"


def test_concurrent_worker_load_fixes_sources_only_once(engine):
    bundle, snapshot, _actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        loaded = list(pool.map(repo.worker_load, [run.run_id, run.run_id]))
    assert loaded[0][0] == loaded[1][0]
    assert loaded[0][0].snapshot_ids == (snapshot,)
    assert [event.status for event in loaded[0][0].events] == ["queued", "retrieving"]


def test_request_rejects_forged_model_extra_fields_before_reserving(engine):
    bundle, snapshot, _actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
    request = ResearchRequest(request_id=uuid4(), question="80% 의미는?").model_copy(
        update={"snapshot_ids": (snapshot,)}
    )
    with pytest.raises(ValidationError):
        repo.submit(token, bundle.document.workspace_id, request)
    assert repo.list_runs(token, bundle.document.workspace_id).items == ()


def test_retrieval_caps_topical_terms_at_eight(engine):
    bundle, _snapshot, _actor, token = setup_run(engine)
    workspace = bundle.document.workspace_id
    add_topic(engine, workspace, "ninthtopic")
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        workspace,
        ResearchRequest(
            request_id=uuid4(),
            question="alpha bravo charlie delta echo foxtrot golf hotel ninthtopic",
        ),
    )
    assert repo.worker_load(run.run_id) is None
    assert repo.get_run(token, workspace, run.run_id).error_code == "insufficient_evidence"


def test_worker_rechecks_parent_completion_even_for_a_new_topic(engine):
    from issuedigest_storage import StorageCorruption

    bundle, _snapshot, _actor, token = setup_run(engine)
    workspace = bundle.document.workspace_id
    repo = ResearchRepository(engine)
    parent = repo.submit(
        token, workspace, ResearchRequest(request_id=uuid4(), question="80% 의미는?")
    )
    loaded = repo.worker_load(parent.run_id)
    output = AIOutput(outcome="insufficient_evidence", message="합성 불충분", modules=())
    result = ResearchResult(
        canvas=build_canvas(parent.run_id, workspace, loaded[1], output),
        source_titles={bundle.document.document_id: "합성 자료"},
    )
    repo.worker_transition(parent.run_id, "completed", result=result)
    child = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question="80% 새 질문", parent_run_id=parent.run_id),
    )
    with engine.begin() as conn:
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == parent.run_id)
            .values(status="failed")
        )
    with pytest.raises(StorageCorruption):
        repo.worker_load(child.run_id)
    assert repo.get_run(token, workspace, child.run_id).snapshot_ids == ()


@pytest.mark.parametrize(
    "new_question",
    ["돈?", "z" * 100 + "?", "日本について 설명해줘", "💰 설명해줘", "$ 설명해줘", "+ 설명해줘"],
)
def test_unrecognized_new_topic_never_reuses_parent(engine, new_question):
    bundle, _snapshot, _actor, token = setup_run(engine)
    workspace = bundle.document.workspace_id
    repo = ResearchRepository(engine)
    parent = repo.submit(
        token, workspace, ResearchRequest(request_id=uuid4(), question="80% 의미는?")
    )
    loaded = repo.worker_load(parent.run_id)
    output = AIOutput(outcome="insufficient_evidence", message="합성 불충분", modules=())
    result = ResearchResult(
        canvas=build_canvas(parent.run_id, workspace, loaded[1], output),
        source_titles={bundle.document.document_id: "합성 자료"},
    )
    repo.worker_transition(parent.run_id, "completed", result=result)
    child = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question=new_question, parent_run_id=parent.run_id),
    )
    assert repo.worker_load(child.run_id) is None
    assert repo.get_run(token, workspace, child.run_id).snapshot_ids == ()


def test_worker_uses_durable_operator_source_presentation(engine):
    from issuedigest_domain.research_journey import SourcePresentation

    bundle, snapshot, _actor, token = setup_run(engine)
    repo = ResearchRepository(engine)
    presentation = SourcePresentation(
        snapshot_id=snapshot,
        workspace_id=bundle.document.workspace_id,
        title="검증된 정부 문서",
        profile="operator-verified-v1",
    )
    repo.upsert_presentation(presentation)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
    )
    loaded = repo.worker_load(run.run_id)
    assert loaded[1][0][2] == presentation
