"""Synthetic operator evaluation: strict input, honest metrics and real read-only PG."""

import importlib
import json
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from test_evidence_search import make_bundle


def api():
    return importlib.import_module("issuedigest_storage.retrieval_evaluation")


def job(snapshot=None, workspace=None):
    snapshot, workspace = snapshot or uuid4(), workspace or uuid4()
    return {
        "schema_version": 1,
        "expected_database": "issuedigest_test",
        "workspace_id": str(workspace),
        "corpus_snapshot_ids": [str(snapshot)],
        "cases": [
            {
                "case_id": "positive",
                "question": "한국어",
                "expected_families": [[str(snapshot)]],
                "no_match": False,
            },
            {
                "case_id": "negative",
                "question": "전혀없는단어",
                "expected_families": [],
                "no_match": True,
            },
        ],
    }


def raw(data):
    return json.dumps(data, ensure_ascii=False).encode()


@pytest.mark.parametrize("bad", [b"\xff", b'{"x":1,"x":2}', b'{"x":NaN}', b" " * 262145])
def test_untrusted_json_is_bounded_strict_and_private(bad):
    with pytest.raises(ValueError, match="^Unable to validate retrieval evaluation job$"):
        api().parse_job(bad)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda j: j.update(extra="private"),
        lambda j: j.update(schema_version=True),
        lambda j: j.update(corpus_snapshot_ids=[]),
        lambda j: j.update(corpus_snapshot_ids=j["corpus_snapshot_ids"] * 51),
        lambda j: j.update(cases=[]),
        lambda j: j.update(cases=j["cases"] * 21),
        lambda j: j["cases"][0].update(question="x" * 1501),
        lambda j: j["cases"][0].update(question=" "),
        lambda j: j["cases"][0].update(no_match=True),
        lambda j: j["cases"][1].update(no_match=False),
        lambda j: j["cases"][0].update(expected_families=[[str(uuid4())]]),
        lambda j: j["cases"][0].update(expected_families=[j["corpus_snapshot_ids"]] * 2),
        lambda j: j["cases"][1].update(case_id="positive"),
    ],
)
def test_invalid_gold_and_bounds_fail_closed(mutation):
    data = job()
    mutation(data)
    with pytest.raises(ValueError, match="^Unable to validate retrieval evaluation job$"):
        api().parse_job(raw(data))


def corpus(engine):
    from issuedigest_storage import EvidenceRepository

    repo = EvidenceRepository(engine)
    bundle = make_bundle("한국어 합성 자료")
    identities = [uuid4() for _ in range(3)]
    for identity in identities:
        repo.save(identity, bundle)
        repo.rebuild_projection(bundle.document.workspace_id, identity)
    identities.sort(key=str)
    data = job(identities[0], bundle.document.workspace_id)
    data["corpus_snapshot_ids"] = list(map(str, identities))
    data["cases"][0]["expected_families"] = [
        [str(identities[0]), str(identities[1])],
        [str(identities[2])],
    ]
    data["cases"].append(
        {
            "case_id": "miss",
            "question": "발견못함",
            "expected_families": [[str(identities[0])]],
            "no_match": False,
        }
    )
    return repo, bundle, identities, data


def test_metrics_fingerprints_ranks_and_readonly_repeatable_read(engine):
    _, _, identities, data = corpus(engine)
    statements = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
        assert conn.scalar(text("SHOW transaction_isolation")) == "repeatable read"
        assert conn.scalar(text("SHOW transaction_read_only")) == "on"

    # Avoid recursively observing the assertions' own SHOWs.
    def guarded(conn, cursor, statement, parameters, context, executemany):
        if not statement.startswith("SHOW"):
            observe(conn, cursor, statement, parameters, context, executemany)

    event.listen(engine, "before_cursor_execute", guarded)
    try:
        report = api().evaluate(engine, raw(data))
    finally:
        event.remove(engine, "before_cursor_execute", guarded)
    assert statements and all(s.lstrip().upper().startswith("SELECT") for s in statements)
    assert report.summary == {
        "cases": 3,
        "positive_cases": 2,
        "negative_cases": 1,
        "hit_at_1": 0.5,
        "macro_family_recall_at_5": 0.5,
        "all_required_at_5": 0.5,
        "negative_no_match": 1.0,
    }
    assert report.cases[0].ranked_snapshot_ids == tuple(identities)
    assert report.cases[0].family_ranks == ((1, 2), (3,))
    assert report.cases[1].ranked_snapshot_ids == ()
    assert report.cases[2].family_recall_at_5 == 0
    again = api().evaluate(engine, raw(data))
    assert report == again
    assert len(report.corpus_sha256) == 64 and len(report.question_gold_sha256) == 64
    changed = json.loads(raw(data))
    changed["cases"][0]["question"] = "다른질문"
    newer = api().evaluate(engine, raw(changed))
    assert newer.question_gold_sha256 != report.question_gold_sha256
    assert newer.corpus_sha256 == report.corpus_sha256
    assert "한국어" not in repr(report) and str(identities[0]) not in repr(report)


@pytest.mark.parametrize("damage", ["scope", "missing", "projection", "units", "canonical"])
def test_missing_extra_or_corrupt_corpus_rejected_before_case_results(engine, damage):
    repo, bundle, identities, data = corpus(engine)
    with engine.begin() as conn:
        if damage == "scope":
            data["corpus_snapshot_ids"].pop()
            data["cases"] = [data["cases"][1]]
        elif damage == "missing":
            conn.execute(
                text("DELETE FROM evidence_search_projections WHERE snapshot_id=:id"),
                {"id": identities[0]},
            )
        elif damage == "projection":
            conn.execute(
                text("UPDATE evidence_search_projections SET projection_sha256=repeat('f',64)")
            )
        elif damage == "units":
            conn.execute(text("UPDATE evidence_search_units SET text='private forged'"))
        else:
            conn.execute(
                text(
                    "UPDATE parsed_representations "
                    "SET payload=jsonb_set(payload,'{text}','\"private forged\"')"
                )
            )
    with pytest.raises(ValueError, match="^Unable to evaluate retrieval$"):
        api().evaluate(engine, raw(data))


@pytest.mark.parametrize("result", ["duplicate", "outside", "too_many"])
def test_invalid_retrieval_result_rejected(engine, monkeypatch, result):
    _, _, identities, data = corpus(engine)
    values = {
        "duplicate": (identities[0],) * 2,
        "outside": (uuid4(),),
        "too_many": tuple(uuid4() for _ in range(6)),
    }[result]
    monkeypatch.setattr(api(), "retrieve_snapshot_ids", lambda *args: values)
    with pytest.raises(ValueError, match="^Unable to evaluate retrieval$"):
        api().evaluate(engine, raw(data))


def test_sdk_rejects_models_before_dump_and_wrong_database(engine):
    module = api()
    model = module.parse_job(raw(job()))
    with pytest.raises(ValueError, match="^Unable to evaluate retrieval$"):
        module.evaluate(engine, model.model_construct(cases=(object(),) * 100000))
    with pytest.raises(ValueError, match="^Unable to evaluate retrieval$"):
        module.evaluate(engine, raw({**job(), "expected_database": "wrong_private"}))


def test_negative_only_and_positive_only_denominators_are_explicit(engine):
    _, _, _, data = corpus(engine)
    data["cases"] = [data["cases"][1]]
    summary = api().evaluate(engine, raw(data)).summary
    assert summary["positive_cases"] == 0 and summary["hit_at_1"] is None
    assert summary["macro_family_recall_at_5"] is None
    data["cases"] = [job(data["corpus_snapshot_ids"][0])["cases"][0]]
    summary = api().evaluate(engine, raw(data)).summary
    assert summary["negative_cases"] == 0 and summary["negative_no_match"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        lambda j: j.update(corpus_snapshot_ids=[str(uuid4()) for _ in range(51)]),
        lambda j: j["cases"][0].update(expected_families=[j["corpus_snapshot_ids"] * 2]),
        lambda j: j["cases"][0].update(expected_families=[[str(uuid4()) for _ in range(11)]]),
        lambda j: j["cases"][0].update(expected_families=[[str(uuid4())] for _ in range(6)]),
        lambda j: j["cases"][0].update(no_match=0),
        lambda j: j["cases"][0].update(extra="private"),
    ],
)
def test_each_nested_boundary_and_strict_type_is_enforced(mutation):
    data = job()
    mutation(data)
    with pytest.raises(ValueError):
        api().parse_job(raw(data))


def test_maximal_valid_job_and_nested_ambiguous_json():
    identities = [str(uuid4()) for _ in range(50)]
    data = job()
    data["corpus_snapshot_ids"] = identities
    data["cases"] = [
        {
            "case_id": f"q{i}",
            "question": "x" * 1500,
            "expected_families": [identities[i : i + 10] for i in range(0, 50, 10)],
            "no_match": False,
        }
        for i in range(40)
    ]
    assert len(api().parse_job(raw(data)).cases) == 40
    for bad in [
        raw(job()).replace(b'"no_match": false', b'"no_match": false,"no_match": true'),
        raw(job()).replace(b'"schema_version": 1', b'"schema_version": 1e999'),
    ]:
        with pytest.raises(ValueError):
            api().parse_job(bad)


def test_macro_recall_counts_families_equally_and_misses_in_denominator(engine, monkeypatch):
    _, _, identities, data = corpus(engine)
    monkeypatch.setattr(api(), "retrieve_snapshot_ids", lambda *args: (identities[0],))
    report = api().evaluate(engine, raw(data))
    assert report.cases[0].family_recall_at_5 == 0.5
    assert report.cases[0].all_required_at_5 is False
    assert report.summary["macro_family_recall_at_5"] == 0.75  # (1/2 + 1) / 2
    assert report.summary["negative_no_match"] == 0


def test_corpus_fingerprint_changes_with_actual_canonical_projection_content(engine):
    repo, bundle, identities, data = corpus(engine)
    before = api().evaluate(engine, raw(data))
    # Replace only the synthetic fixture, preserving declared identities and questions.
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE source_documents, outbox CASCADE"))
    replacement = bundle.model_copy(
        update={"document": bundle.document.model_copy(update={"provider": "changed"})}
    )
    for identity in identities:
        repo.save(identity, replacement)
        repo.rebuild_projection(bundle.document.workspace_id, identity)
    after = api().evaluate(engine, raw(data))
    assert before.corpus_sha256 != after.corpus_sha256
    assert before.question_gold_sha256 == after.question_gold_sha256
    assert before.declared_corpus_sha256 == after.declared_corpus_sha256


def test_repeatable_read_keeps_cases_on_same_corpus_during_concurrent_insert(engine, monkeypatch):
    repo, bundle, identities, data = corpus(engine)
    real_retrieve = api().retrieve_snapshot_ids
    inserted = False

    def insert_then_retrieve(conn, workspace, terms):
        nonlocal inserted
        if not inserted:
            inserted = True
            later = uuid4()
            repo.save(later, bundle)
            repo.rebuild_projection(workspace, later)
        return real_retrieve(conn, workspace, terms)

    monkeypatch.setattr(api(), "retrieve_snapshot_ids", insert_then_retrieve)
    assert api().evaluate(engine, raw(data)).cases[0].ranked_snapshot_ids == tuple(identities)
    with pytest.raises(ValueError, match="^Unable to evaluate retrieval$"):
        api().evaluate(engine, raw(data))  # Next execution sees the changed whole workspace.


def test_evaluation_preserves_every_public_table(engine):
    from sqlalchemy import inspect

    _, _, _, data = corpus(engine)

    def state():
        with engine.connect() as conn:
            return {
                name: conn.scalar(
                    text(
                        "SELECT md5(string_agg(to_jsonb(t)::text, ',' ORDER BY to_jsonb(t)::text)) "
                        f"FROM {engine.dialect.identifier_preparer.quote_identifier(name)} AS t"
                    )
                )
                for name in inspect(engine).get_table_names(schema="public")
            }

    before = state()
    api().evaluate(engine, raw(data))
    assert state() == before
