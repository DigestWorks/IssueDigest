"""Anonymous public reads are isolated from sessions, private storage and execution."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from issuedigest_api.main import create_app
from issuedigest_domain.public_briefings import PublicBriefingPlan, plan_hash, publish_copy
from issuedigest_storage.public_briefings import PublicBriefingRepository
from issuedigest_storage.repository import StorageCorruption

from conftest import public_plan_data


def test_optional_public_repository_and_anonymous_unconfigured_routes():
    client = TestClient(create_app(public_repository=None))
    for path, code in [
        ("/api/v1/briefings", 503),
        ("/api/v1/briefings/synthetic-policy", 503),
        ("/api/v1/briefings/synthetic-policy/versions/1", 503),
        ("/api/v1/briefings/SECRET--INPUT", 422),
        ("/api/v1/briefings/synthetic-policy/versions/SECRET", 422),
        ("/api/v1/briefings/synthetic-policy/versions/1.0", 422),
        ("/api/v1/briefings/synthetic-policy/versions/9007199254740992", 422),
    ]:
        response = client.get(path)
        assert response.status_code == code
        assert response.headers["cache-control"] == "no-store"
        assert uuid4().__class__(response.headers["x-request-id"]).version == 4
        assert "SECRET" not in response.text
        assert "input" not in response.json()
    assert client.post("/api/v1/briefings", json={"private": "secret"}).status_code == 405
    private = f"/api/v1/workspaces/{uuid4()}/evidence/{uuid4()}"
    assert client.get(private).status_code == 401


def test_real_public_reads_withdrawal_and_private_repositories_never_called(engine):
    class ForbiddenPrivate:
        def __getattr__(self, name):
            raise AssertionError("Public read touched private repository")

    repository = PublicBriefingRepository(engine)
    plan = PublicBriefingPlan.model_validate(public_plan_data())
    detail = repository.publish(plan, reviewed_sha256=plan_hash(plan))
    client = TestClient(
        create_app(
            public_repository=repository,
            access_repository=ForbiddenPrivate(),
            workspace_repository=ForbiddenPrivate(),
            research_repository=ForbiddenPrivate(),
        )
    )
    listing = client.get("/api/v1/briefings")
    assert listing.status_code == 200
    assert listing.json()["items"][0]["content_sha256"] == detail.content_sha256
    assert "canvas" not in listing.json()["items"][0]
    for path in (f"/api/v1/briefings/{plan.slug}", f"/api/v1/briefings/{plan.slug}/versions/1"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == detail.model_dump(mode="json")
        assert "private-reviewer" not in response.text
    repository.withdraw(plan, reviewed_sha256=plan_hash(plan))
    assert client.get(f"/api/v1/briefings/{plan.slug}").status_code == 404
    assert client.get(f"/api/v1/briefings/{plan.slug}/versions/1").status_code == 404
    assert client.get("/api/v1/briefings").json() == {"items": []}


@pytest.mark.parametrize("wrong", ["hash", "slug", "version", "storage"])
def test_http_boundary_revalidates_injected_public_results(wrong):
    plan = PublicBriefingPlan.model_validate(public_plan_data())
    detail = publish_copy(plan, datetime(2026, 10, 14, tzinfo=UTC))
    if wrong == "hash":
        detail = detail.model_copy(update={"content_sha256": "0" * 64})
    elif wrong == "slug":
        changed = plan.model_copy(update={"slug": "different-slug"})
        detail = publish_copy(changed, detail.published_at)
    elif wrong == "version":
        changed = plan.model_copy(update={"version": 2})
        detail = publish_copy(changed, detail.published_at)

    class Broken:
        def load(self, slug, version=None):
            if wrong == "storage":
                raise StorageCorruption("PRIVATE ERROR")
            return detail

    client = TestClient(create_app(public_repository=Broken()))
    response = client.get(f"/api/v1/briefings/{plan.slug}/versions/1")
    assert response.status_code == 503
    assert "PRIVATE" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_select_only_public_role_reads_without_private_or_write_permissions(engine):
    from sqlalchemy import create_engine, event, text

    plan = PublicBriefingPlan.model_validate(public_plan_data())
    owner = PublicBriefingRepository(engine)
    owner.publish(plan, reviewed_sha256=plan_hash(plan))
    role = "synthetic_public_" + uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(text(f"GRANT SELECT ON public_briefings, public_briefing_heads TO {role}"))
    reader = create_engine(engine.url, hide_parameters=True)

    @event.listens_for(reader, "begin")
    def enter_role(conn):
        conn.execute(text(f"SET LOCAL ROLE {role}"))

    try:
        with reader.connect() as conn:
            for table in ("public_briefings", "public_briefing_heads"):
                assert conn.scalar(
                    text("SELECT has_table_privilege(current_user, :table, 'SELECT')"),
                    {"table": table},
                )
                for permission in ("INSERT", "UPDATE", "DELETE"):
                    assert not conn.scalar(
                        text("SELECT has_table_privilege(current_user, :table, :permission)"),
                        {"table": table, "permission": permission},
                    )
            assert not conn.scalar(
                text("SELECT has_table_privilege(current_user, 'research_runs', 'SELECT')")
            )
        repository = PublicBriefingRepository(reader)
        client = TestClient(create_app(public_repository=repository))
        assert client.get("/api/v1/briefings").status_code == 200
        assert client.get(f"/api/v1/briefings/{plan.slug}").status_code == 200
        assert client.get(f"/api/v1/briefings/{plan.slug}/versions/1").status_code == 200
    finally:
        reader.dispose()
        with engine.begin() as conn:
            conn.execute(text(f"DROP OWNED BY {role}"))
            conn.execute(text(f"DROP ROLE {role}"))


def test_forged_boolean_version_is_not_silently_normalized_at_http_boundary():
    from issuedigest_domain.public_briefings import PublicBriefingList, PublicBriefingSummary

    plan = PublicBriefingPlan.model_validate(public_plan_data())
    detail = publish_copy(plan, datetime(2026, 10, 14, tzinfo=UTC))
    forged = detail.model_copy(update={"version": True})
    summary = PublicBriefingSummary.model_validate(
        detail.model_dump(include=set(PublicBriefingSummary.model_fields))
    ).model_copy(update={"version": True})

    class Broken:
        def load(self, slug, version=None):
            return forged

        def list_latest(self):
            return PublicBriefingList.model_construct(items=(summary,))

    client = TestClient(create_app(public_repository=Broken()))
    assert client.get(f"/api/v1/briefings/{plan.slug}/versions/1").status_code == 503
    assert client.get("/api/v1/briefings").status_code == 503
