"""Real SQL metadata reads preserve current shared authorization and budgets."""

from uuid import uuid4

import pytest
from issuedigest_storage import IdentityRepository, SessionRepository
from issuedigest_storage.briefing_jobs import BriefingJobRepository
from issuedigest_storage.repository import StorageCorruption
from issuedigest_storage.research import ResearchForbidden
from sqlalchemy import text
from test_briefing_jobs import admit, packet


def test_list_current_exists():
    assert hasattr(BriefingJobRepository, "list_current")


def test_list_shared_current_and_budget(engine):
    repo = BriefingJobRepository(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE briefing_jobs, evidence_jobs, question_source_plans"))
    p = packet(engine)
    job = admit(repo, p)
    viewer = uuid4()
    identities = IdentityRepository(engine)
    identities.register_identity(viewer, "synthetic", str(viewer))
    identities.set_membership(viewer, p[1], "viewer")
    token = SessionRepository(engine).issue_session(viewer).token
    with engine.connect() as conn:
        budget = conn.execute(text("SELECT * FROM research_budget_months")).all()
    result = repo.list_current(token, p[1])
    assert [item.job_id for item in result.items] == [job.job_id]
    assert set(result.items[0].model_dump()) == {"job_id", "question", "status"}
    assert repo.list_current(token, uuid4()) is None
    with engine.connect() as conn:
        assert conn.execute(text("SELECT * FROM research_budget_months")).all() == budget
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM auth_workspace_memberships WHERE user_id=:actor"),
            dict(actor=job.actor_id),
        )
    with pytest.raises(ResearchForbidden):
        repo.list_current(token, p[1])


@pytest.mark.parametrize("change", ["source", "reader"])
def test_list_current_source_or_requester_loss(engine, change):
    repo = BriefingJobRepository(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE briefing_jobs, evidence_jobs, question_source_plans"))
    p = packet(engine)
    job = admit(repo, p)
    assert repo.list_current(p[0], p[1]).items
    with engine.begin() as conn:
        if change == "reader":
            conn.execute(
                text("DELETE FROM auth_workspace_memberships WHERE user_id=:actor"),
                dict(actor=job.actor_id),
            )
        else:
            conn.execute(
                text(
                    "UPDATE source_presentations SET payload=jsonb_set(payload, "
                    "'{title}', '\"changed\"')"
                )
            )
    if change == "reader":
        assert repo.list_current(p[0], p[1]) is None
    else:
        with pytest.raises(StorageCorruption):
            repo.list_current(p[0], p[1])


def test_list_cap_order_offloop_http_and_no_model(engine):
    import asyncio

    from fastapi.testclient import TestClient
    from issuedigest_api.cookies import SESSION_COOKIE
    from issuedigest_api.main import create_app
    from sqlalchemy import event

    repo = BriefingJobRepository(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE briefing_jobs, evidence_jobs, question_source_plans"))
    p = packet(engine)
    job = admit(repo, p)
    repo.cancel(p[0], p[1], job.job_id)
    identities = [job.job_id] + [uuid4() for _ in range(54)]
    with engine.begin() as conn:
        columns = (
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='briefing_jobs' ORDER BY ordinal_position"
                )
            )
            .scalars()
            .all()
        )
        names = ",".join(columns)
        values = ",".join(
            ":newid" if name == "job_id" else ":requestid" if name == "request_id" else name
            for name in columns
        )
        for identifier in identities[1:]:
            conn.execute(
                text(
                    f"INSERT INTO briefing_jobs ({names}) SELECT {values} "
                    "FROM briefing_jobs WHERE job_id=:original"
                ),
                dict(newid=identifier, requestid=uuid4(), original=job.job_id),
            )
        budget = conn.execute(text("SELECT * FROM research_budget_months")).all()

    result = repo.list_current(p[0], p[1])
    assert len(result.items) == 50
    from issuedigest_domain.question_submission import BriefingJobList

    BriefingJobList.model_validate_json(result.model_dump_json())

    def offloop(*args):
        with pytest.raises(RuntimeError, match="no running event loop"):
            asyncio.get_running_loop()

    event.listen(engine, "before_cursor_execute", offloop)
    try:
        client = TestClient(create_app(briefing_job_repository=repo), follow_redirects=False)
        client.cookies.set(SESSION_COOKIE, p[0])
        path = f"/api/v1/workspaces/{p[1]}/briefing-jobs"
        response = client.get(path)
        assert response.status_code == 200, response.text
        assert [item["job_id"] for item in response.json()["items"]] == [
            str(v) for v in sorted(identities)[:50]
        ]
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-request-id"]
        for suffix in ["?private=secret", "/?private=secret"]:
            invalid = client.get(path + suffix)
            assert invalid.status_code == 422
            assert "secret" not in invalid.text and "location" not in invalid.headers
            assert invalid.headers["cache-control"] == "no-store"
    finally:
        event.remove(engine, "before_cursor_execute", offloop)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT * FROM research_budget_months")).all() == budget
