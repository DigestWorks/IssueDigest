"""Private briefing HTTP contracts; no provider execution."""

import asyncio
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from issuedigest_api.cookies import SESSION_COOKIE
from issuedigest_api.main import create_app
from sqlalchemy import text


def test_briefing_paths_fail_closed():
    client = TestClient(create_app(), follow_redirects=False)
    path = (
        "/api/v1/workspaces/10000000-0000-4000-8000-000000000001/briefing-jobs/"
        "10000000-0000-4000-8000-000000000002"
    )
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]
    assert client.get(path + "/?secret=private").status_code == 422


@pytest.fixture
def briefing_seed(engine):
    packages = [importlib.import_module(n) for n in ("issuedigest_agents", "issuedigest_worker")]
    before, paths = set(sys.modules), sys.path.copy()
    attrs = [vars(p).copy() for p in packages]
    root = Path(__file__).resolve().parents[3]
    sys.path[:0] = [str(root / "apps/worker/tests"), str(root / "packages/agents/tests")]
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE briefing_jobs, evidence_jobs, question_source_plans"))
    helper = importlib.import_module("test_briefing_worker")
    from issuedigest_storage.briefing_jobs import BriefingJobRepository

    repo = BriefingJobRepository(engine)
    try:
        yield helper, repo, helper.seed(engine)
    finally:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE briefing_jobs, evidence_jobs, question_source_plans"))
        for name in set(sys.modules) - before:
            if name.startswith(("issuedigest_agents.", "issuedigest_worker.", "test_")):
                sys.modules.pop(name, None)
        sys.path[:] = paths
        for package, original in zip(packages, attrs, strict=True):
            for name in set(vars(package)) - original.keys():
                delattr(package, name)
            for name, value in original.items():
                setattr(package, name, value)


def private_client(repo, seed):
    origin = "https://example.test"
    client = TestClient(
        create_app(
            briefing_job_repository=repo,
            auth_service=SimpleNamespace(config=SimpleNamespace(public_origin=origin)),
        ),
        base_url=origin,
        follow_redirects=False,
    )
    client.cookies.set(SESSION_COOKIE, seed[0])
    return client


def test_sql_completed_current_projection_and_no_new_reservation(briefing_seed, engine):
    helper, repo, seed = briefing_seed
    job = helper.admit(repo, seed)
    result, calls = asyncio.run(helper.exercise(repo, job))
    assert result is not None and len(calls) == 1
    client = private_client(repo, seed)
    path = f"/api/v1/workspaces/{seed[1]}/briefing-jobs/{job.job_id}"
    with engine.connect() as conn:
        reservations = conn.scalar(
            text("SELECT sum(reservation_count) FROM research_budget_months")
        )
    for _ in range(2):
        response = client.get(path)
        assert response.status_code == 200, response.text
        assert response.json()["result"]["outcome"] == "insufficient_evidence"
        assert response.json()["result"]["additional_quotes"]
        assert response.headers["cache-control"] == "no-store"
    response = client.post(
        path + "/cancel",
        content=b"{}",
        headers={"Content-Type": "application/json", "Origin": "https://example.test"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    with engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT sum(reservation_count) FROM research_budget_months"))
            == reservations
        )
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE briefing_jobs SET receipt = jsonb_set(receipt, '{prompt_sha256}', "
                "'\"broken-secret\"') WHERE job_id=:id"
            ),
            {"id": job.job_id},
        )
    response = client.get(path)
    assert response.status_code == 503
    assert "broken-secret" not in response.text


def test_sql_cancel_and_private_boundary(briefing_seed):
    helper, repo, seed = briefing_seed
    job = helper.admit(repo, seed)
    client = private_client(repo, seed)
    path = f"/api/v1/workspaces/{seed[1]}/briefing-jobs/{job.job_id}"
    assert client.get(path).json()["result"] is None
    assert client.get(path + "?private=secret").status_code == 422
    assert client.get(path.replace(str(job.job_id), "secret")).status_code == 422
    assert client.get(path + "/?private=secret").status_code == 422
    for body, content_type in [
        (b" {}", "application/json"),
        (b"{}", "application/json; charset=utf-8"),
        (b"x" * 16385, "application/json"),
    ]:
        response = client.post(
            path + "/cancel",
            content=body,
            headers={"Origin": "https://example.test", "Content-Type": content_type},
        )
        assert response.status_code == 422
    assert (
        client.post(
            path + "/cancel", content=b"{}", headers={"Content-Type": "application/json"}
        ).status_code
        == 403
    )
    response = client.post(
        path + "/cancel",
        content=b"{}",
        headers={"Origin": "https://example.test", "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["result"] is None
    assert client.get(path.replace(str(seed[1]), str(uuid4()))).status_code == 404


def test_sql_answer_plaintext_and_off_loop(briefing_seed, engine):
    from sqlalchemy import event
    from test_guarded_responses_stream import Body
    from test_question_briefing_generation import rows

    helper, repo, seed = briefing_seed
    job = helper.admit(repo, seed)
    _, packet = repo.prepare(job.job_id)
    sid = packet.sources[0][0]
    body = Body(
        rows(
            dict(
                outcome="answer",
                message=None,
                modules=[
                    dict(
                        kind="summary",
                        title="<b>합성</b>",
                        claims=[
                            dict(
                                text="<script>자료 주장</script>",
                                references=[dict(snapshot_id=str(sid), proposition_id="p1")],
                                event_date=None,
                            )
                        ],
                    )
                ],
            )
        )
    )
    result, calls = asyncio.run(helper.exercise(repo, job, body=body))
    assert result is not None and len(calls) == 1

    def off_loop(*args):
        with pytest.raises(RuntimeError, match="no running event loop"):
            asyncio.get_running_loop()

    event.listen(engine, "before_cursor_execute", off_loop)
    try:
        client = private_client(repo, seed)
        path = f"/api/v1/workspaces/{seed[1]}/briefing-jobs/{job.job_id}"
        response = client.get(path)
        assert response.status_code == 200, response.text
        module = response.json()["result"]["modules"][0]
        assert module["title"] == "<b>합성</b>"
        claim = module["claims"][0]
        assert claim["text"] == "<script>자료 주장</script>"
        for quote in claim["quotes"]:
            assert quote["citation_quote"][quote["start"] : quote["end"]] == quote["text"]
        assert len(claim["quotes"]) == len(
            {
                (q["snapshot_id"], q["citation_id"], q["start"], q["end"], q["text"])
                for q in claim["quotes"]
            }
        )
    finally:
        event.remove(engine, "before_cursor_execute", off_loop)


def test_projection_dependency_closure_dates_uncertainty_and_dedupe(briefing_seed):
    from issuedigest_agents.question_briefing import build_question_briefing
    from issuedigest_api.briefing_jobs import project_briefing
    from test_question_briefing import (
        QUESTION,
        TEXT,
        claim,
        packet,
        proposal,
        receipt,
        reference,
        source,
    )
    from test_question_evidence_propositions import proposition

    src = source(TEXT + " 2026-10-26")
    data = packet(src)
    data["propositions"] += [
        proposition(src, "p2", depends_on_ids=["p3"]),
        proposition(src, "p3", epistemic_status="uncertain", subject_refs=[]),
        proposition(src, "p4"),
        proposition(src, "p5"),
    ]
    data["propositions"][0]["depends_on_ids"] = ["p2"]
    data["coverage"] = dict(
        linked_proposition_ids=["p4", "p1", "p5"], unresolved_reason="ambiguous"
    )
    rec = receipt(src, data)
    submitted = proposal(claim(reference(src)))
    submitted["modules"].append(
        dict(
            kind="comparison",
            title="비교",
            claims=[claim(reference(src)), claim(reference(src, "p4"))],
        )
    )
    # A dated claim is allowed only with a directly supporting literal date.
    submitted["modules"].append(
        dict(kind="timeline", title="시점", claims=[claim(reference(src), event_date="2026-10-26")])
    )
    briefing = build_question_briefing(QUESTION, (src,), (rec,), submitted)
    projected = project_briefing(
        SimpleNamespace(briefing=briefing), SimpleNamespace(sources=(src,))
    )
    assert projected.modules[0].claims[0].epistemic_status == "uncertain"
    assert projected.modules[2].claims[0].event_date.isoformat() == "2026-10-26"
    quotes = projected.modules[0].claims[0].quotes
    keys = [(q.snapshot_id, q.citation_id, q.start, q.end, q.text) for q in quotes]
    assert len(keys) == len(set(keys))
    assert projected.additional_quotes


@pytest.mark.parametrize("status", ["running", "failed", "cancelled", "indeterminate"])
def test_sql_noncompleted_never_returns_result(briefing_seed, engine, status):
    helper, repo, seed = briefing_seed
    job = helper.admit(repo, seed)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE briefing_jobs SET status=:status WHERE job_id=:id"),
            dict(status=status, id=job.job_id),
        )
    response = private_client(repo, seed).get(
        f"/api/v1/workspaces/{seed[1]}/briefing-jobs/{job.job_id}"
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == status
    assert response.json()["result"] is None


@pytest.mark.parametrize("change", ["source", "author", "reader"])
def test_sql_current_source_and_author_rights(briefing_seed, engine, change):
    from issuedigest_storage import IdentityRepository, SessionRepository

    helper, repo, seed = briefing_seed
    job = helper.admit(repo, seed)
    assert asyncio.run(helper.exercise(repo, job))[0] is not None
    identities = IdentityRepository(engine)
    reader = uuid4()
    identities.register_identity(reader, "synthetic", str(reader))
    identities.set_membership(reader, seed[1], "viewer")
    reader_token = SessionRepository(engine).issue_session(reader).token
    client = private_client(repo, seed)
    client.cookies.set(SESSION_COOKIE, reader_token)
    path = f"/api/v1/workspaces/{seed[1]}/briefing-jobs/{job.job_id}"
    assert client.get(path).status_code == 200
    if change == "source":
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE source_presentations SET payload=jsonb_set(payload, "
                    "'{title}', '\"private changed source\"')"
                )
            )
    else:
        actor = seed[4] if change == "author" else reader
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM auth_workspace_memberships WHERE user_id=:actor"),
                dict(actor=actor),
            )
    response = client.get(path)
    assert response.status_code in {403, 404, 503}
    assert "result" not in response.json()
    assert "private changed source" not in response.text


def test_unknown_error_sanitized_and_no_redirect_secrets(briefing_seed, monkeypatch):
    helper, repo, seed = briefing_seed
    job = helper.admit(repo, seed)
    client = private_client(repo, seed)
    path = f"/api/v1/workspaces/{seed[1]}/briefing-jobs/{job.job_id}"

    def broken(*args):
        raise RuntimeError("private source token cookie")

    monkeypatch.setattr(repo, "get", broken)
    response = client.get(path)
    assert response.status_code == 503
    assert response.json() == {"detail": "Briefing service unavailable"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]
    for method, suffix in [(client.get, "/"), (client.post, "/cancel/")]:
        response = method(path + suffix + "?private=secret")
        assert response.status_code == 422
        assert "location" not in response.headers
        assert "secret" not in response.text


def test_quote_unicode_codepoints_and_end_overrun_rejected():
    from issuedigest_domain.briefing_job_view import BriefingQuoteView
    from pydantic import ValidationError

    quote = dict(
        snapshot_id=uuid4(),
        citation_id=uuid4(),
        source_title="합성",
        start=1,
        end=4,
        text="😀é",
        citation_quote="앞😀é",
    )
    assert BriefingQuoteView(**quote).text == "😀é"
    with pytest.raises(ValidationError):
        BriefingQuoteView(**(quote | dict(end=5)))


@pytest.mark.parametrize(
    "failure, expected",
    [
        ("auth", 401),
        ("forbidden", 403),
        ("missing", 404),
        ("conflict", 409),
        ("unknown", 503),
        ("no_repository", 503),
    ],
)
def test_fixed_failures_and_repository_configuration(failure, expected):
    from issuedigest_storage import AuthenticationDenied
    from issuedigest_storage.research import ResearchConflict, ResearchForbidden

    def get(*args):
        if failure == "missing":
            return None
        errors = {
            "auth": AuthenticationDenied,
            "forbidden": ResearchForbidden,
            "conflict": ResearchConflict,
            "unknown": RuntimeError,
        }
        raise errors[failure]("private token source")

    client = TestClient(
        create_app(
            briefing_job_repository=None if failure == "no_repository" else SimpleNamespace(get=get)
        )
    )
    client.cookies.set(SESSION_COOKIE, "a" * 42 + "A")
    response = client.get(f"/api/v1/workspaces/{uuid4()}/briefing-jobs/{uuid4()}")
    assert response.status_code == expected
    assert "private token source" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]
