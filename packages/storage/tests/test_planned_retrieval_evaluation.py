"""Synthetic planned search comparisons: labels, provenance, scope and no writes."""

import importlib
import importlib.util
import json
from uuid import UUID, uuid4

import pytest
from issuedigest_storage import EvidenceRepository
from sqlalchemy import event, inspect, text
from test_evidence_search import make_bundle
from test_retrieval_evaluation import job, raw


def api():
    name = "issuedigest_storage.planned_retrieval_evaluation"
    assert importlib.util.find_spec(name) is not None, "planned comparison SDK is missing"
    return importlib.import_module(name)


def planned(baseline=None):
    baseline = baseline or job()
    return {
        "schema_version": 1,
        "baseline": baseline,
        "plans": [
            {
                "case_id": case["case_id"],
                "origin": "recorded_planner_output",
                "queries": ["복구어"],
                "irrelevant_snapshot_ids": [],
            }
            for case in baseline["cases"]
        ],
    }


def corpus(engine, bodies=("복구어", "복구어 무관", "모름")):
    workspace = uuid4()
    identities = tuple(UUID(f"00000000-0000-4000-8000-{i:012d}") for i in range(1, len(bodies) + 1))
    repo = EvidenceRepository(engine)
    for identity, body in zip(identities, bodies, strict=True):
        bundle = make_bundle(body, workspace=workspace)
        repo.save(identity, bundle)
        repo.rebuild_projection(workspace, identity)
    baseline = job(identities[0], workspace)
    baseline["corpus_snapshot_ids"] = list(map(str, identities))
    baseline["cases"][0]["question"] = "미발견어"
    baseline["cases"][1]["question"] = "없는어"
    data = planned(baseline)
    data["plans"][0]["irrelevant_snapshot_ids"] = [str(identities[1])]
    data["plans"][1].update(origin="operator_authored", queries=["모름"])
    return identities, data


def test_recovers_gold_and_irrelevant_with_honest_unjudged_denominators(engine):
    ids, data = corpus(engine)
    report = api().evaluate(engine, raw(data))
    first, negative = report.cases
    assert first.baseline.ranked_snapshot_ids == ()
    assert first.planned.ranked_snapshot_ids == ids[:2]
    assert first.original_terms == ("미발견어",)
    assert first.query_terms == (("복구어",),)
    assert first.planned.family_ranks == ((1,),)
    assert first.planned.family_recall_at_5 == 1
    assert first.planned.relevant_count == 1
    assert first.planned.irrelevant_count == 1
    assert first.planned.unjudged_count == 0
    assert first.planned.returned_count == 2
    assert first.planned.judged_precision == 0.5
    assert first.baseline.judged_precision is None
    assert negative.planned.ranked_snapshot_ids == (ids[2],)
    assert negative.planned.unjudged_count == 1
    assert negative.planned.judged_precision is None
    assert negative.planned.negative_no_match is False
    assert report.profile == "planned-retrieval-comparison-v1"
    assert report.retrieval_profile == "question-topics-ko-v2"
    assert report.judged_precision_denominator == "relevant_plus_irrelevant_excludes_unjudged"
    assert report.origin_case_counts == {"recorded_planner_output": 1, "operator_authored": 1}
    assert report.summary["baseline"]["macro_family_recall_at_5"] == 0
    assert report.summary["planned"] == {
        "cases": 2,
        "positive_cases": 1,
        "negative_cases": 1,
        "hit_at_1": 1.0,
        "macro_family_recall_at_5": 1.0,
        "all_required_at_5": 1.0,
        "negative_no_match": 0.0,
        "returned_count": 3,
        "relevant_count": 1,
        "irrelevant_count": 1,
        "unjudged_count": 1,
        "judged_precision": 0.5,
    }
    assert "복구어" not in repr(report) and str(ids[0]) not in repr(report)


def test_original_first_round_robin_max_five_partial_family_and_member_counts(engine):
    ids, data = corpus(engine, ("원래어", "원래어", "원래어", "복구어", "복구어", "복구어", "모름"))
    data["baseline"]["cases"] = [data["baseline"]["cases"][0]]
    data["baseline"]["cases"][0].update(
        question="원래어", expected_families=[[str(ids[0]), str(ids[1])], [str(ids[6])]]
    )
    data["plans"] = [data["plans"][0]]
    data["plans"][0]["irrelevant_snapshot_ids"] = [str(ids[3])]
    report = api().evaluate(engine, raw(data))
    result = report.cases[0].planned
    assert result.ranked_snapshot_ids == (ids[0], ids[3], ids[1], ids[4], ids[2])
    assert result.family_ranks == ((1, 3), (None,))
    assert result.family_recall_at_5 == 0.5
    assert result.all_required_at_5 is False and result.hit_at_1 is True
    assert (result.relevant_count, result.irrelevant_count, result.unjudged_count) == (2, 1, 2)
    assert result.judged_precision == 2 / 3
    assert report.summary["planned"]["negative_cases"] == 0
    assert report.summary["planned"]["negative_no_match"] is None


@pytest.mark.parametrize("bad", [b"\xff", b'{"x":1,"x":2}', b'{"x":NaN}', b" " * 262145, "json"])
def test_bounded_untrusted_json_rejected(bad):
    with pytest.raises(ValueError, match="^Unable to validate planned retrieval evaluation job$"):
        api().parse_job(bad)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda j: j.update(extra=True),
        lambda j: j.update(schema_version=True),
        lambda j: j["baseline"].update(schema_version="1"),
        lambda j: j["baseline"]["cases"][0].update(no_match=0),
        lambda j: j["plans"].reverse(),
        lambda j: j["plans"].pop(),
        lambda j: j["plans"].append(j["plans"][0]),
        lambda j: j["plans"][0].update(case_id="other"),
        lambda j: j["plans"][0].update(origin="model_execution"),
        lambda j: j["plans"][0].update(queries=[]),
        lambda j: j["plans"][0].update(queries=["a"] * 4),
        lambda j: j["plans"][0].update(queries=["a" * 65]),
        lambda j: j["plans"][0].update(queries=[" "]),
        lambda j: j["plans"][0].update(queries=["a\nb"]),
        lambda j: j["plans"][0].update(queries=["a\u200db"]),
        lambda j: j["plans"][0].update(queries=[7]),
        lambda j: j["plans"][0].update(extra="private"),
        lambda j: j["plans"][0].update(
            irrelevant_snapshot_ids=j["baseline"]["corpus_snapshot_ids"]
        ),
        lambda j: j["plans"][1].update(
            irrelevant_snapshot_ids=j["baseline"]["corpus_snapshot_ids"] * 2
        ),
        lambda j: j["plans"][0].update(irrelevant_snapshot_ids=[str(uuid4())]),
        lambda j: j["plans"][0].update(irrelevant_snapshot_ids=[str(uuid4()) for _ in range(51)]),
        lambda j: j["plans"][0].update(
            irrelevant_snapshot_ids=["00000000-0000-1000-8000-000000000001"]
        ),
    ],
)
def test_strict_nested_plan_case_order_and_labels(mutation):
    data = planned()
    mutation(data)
    with pytest.raises(ValueError, match="^Unable to validate planned retrieval evaluation job$"):
        api().parse_job(raw(data))


def test_every_expected_member_is_protected_from_irrelevant_overlap():
    data = planned()
    other = str(uuid4())
    data["baseline"]["corpus_snapshot_ids"].append(other)
    data["baseline"]["cases"][0]["expected_families"][0].append(other)
    data["plans"][0]["irrelevant_snapshot_ids"] = [other]
    with pytest.raises(ValueError):
        api().parse_job(raw(data))


def test_maximal_plan_bounds_nested_duplicate_and_nonfinite_rejected():
    data = planned()
    ids = [str(uuid4()) for _ in range(50)]
    data["baseline"]["corpus_snapshot_ids"] = ids
    data["baseline"]["cases"] = [
        {"case_id": f"q{i}", "question": "a" * 1500, "expected_families": [], "no_match": True}
        for i in range(40)
    ]
    data["plans"] = [
        {
            "case_id": f"q{i}",
            "origin": "operator_authored",
            "queries": ["a" * 64] * 3,
            "irrelevant_snapshot_ids": ids,
        }
        for i in range(40)
    ]
    assert len(api().parse_job(raw(data)).plans) == 40
    for bad in [
        raw(data).replace(b'"schema_version": 1', b'"schema_version": 1e999', 1),
        raw(data).replace(
            b'"origin": "operator_authored"',
            b'"origin":"operator_authored","origin":"recorded_planner_output"',
            1,
        ),
    ]:
        with pytest.raises(ValueError):
            api().parse_job(bad)


def test_hashes_are_canonical_and_separate_questions_plans_labels_and_corpus(engine):
    _, data = corpus(engine)
    before = api().evaluate(engine, raw(data))
    reordered = json.dumps(data, sort_keys=True, indent=2).encode()
    assert api().evaluate(engine, reordered) == before
    data["plans"][0]["irrelevant_snapshot_ids"] = []
    labels = api().evaluate(engine, raw(data))
    assert labels.plans_labels_sha256 != before.plans_labels_sha256
    assert labels.job_sha256 != before.job_sha256
    assert labels.question_gold_sha256 == before.question_gold_sha256
    assert labels.corpus_sha256 == before.corpus_sha256
    assert labels.declared_corpus_sha256 == before.declared_corpus_sha256
    data["baseline"]["cases"][0]["question"] = "새질문"
    changed = api().evaluate(engine, raw(data))
    assert changed.question_gold_sha256 != before.question_gold_sha256
    assert changed.plans_labels_sha256 == labels.plans_labels_sha256
    data["plans"][0]["origin"] = "operator_authored"
    assert api().evaluate(engine, raw(data)).plans_labels_sha256 != changed.plans_labels_sha256


@pytest.mark.parametrize(
    "damage", ["scope", "workspace", "projection", "units", "canonical", "missing", "database"]
)
def test_scope_and_projection_corruption_fail_wholly(engine, damage):
    _, data = corpus(engine)
    with engine.begin() as conn:
        if damage == "scope":
            data["baseline"]["corpus_snapshot_ids"].pop()
        elif damage == "workspace":
            data["baseline"]["workspace_id"] = str(uuid4())
        elif damage == "database":
            data["baseline"]["expected_database"] = "wrong_private"
        elif damage == "projection":
            conn.execute(
                text("UPDATE evidence_search_projections SET projection_sha256=repeat('f',64)")
            )
        elif damage == "units":
            conn.execute(text("UPDATE evidence_search_units SET text='forged'"))
        elif damage == "canonical":
            conn.execute(
                text(
                    "UPDATE parsed_representations "
                    "SET payload=jsonb_set(payload,'{text}','\"forged\"')"
                )
            )
        else:
            conn.execute(text("DELETE FROM evidence_search_projections"))
    with pytest.raises(ValueError, match="^Unable to evaluate planned retrieval$"):
        api().evaluate(engine, raw(data))


@pytest.mark.parametrize("path", ["baseline", "planned"])
@pytest.mark.parametrize("damage", ["list", "duplicate", "outside", "too_many", "partial_failure"])
def test_malformed_runtime_results_never_repaired_or_cases_omitted(
    engine, monkeypatch, path, damage
):
    ids, data = corpus(engine)
    module = api()
    calls = 0

    def retrieve(*args):
        nonlocal calls
        calls += 1
        if damage == "partial_failure":
            if calls == 2:
                raise RuntimeError("private result body")
            return (ids[0],)
        return {
            "list": [ids[0]],
            "duplicate": (ids[0], ids[0]),
            "outside": (uuid4(),),
            "too_many": tuple(uuid4() for _ in range(6)),
        }[damage]

    if path == "baseline":
        monkeypatch.setattr(
            importlib.import_module("issuedigest_storage.retrieval_evaluation"),
            "retrieve_snapshot_ids",
            retrieve,
        )
    else:
        monkeypatch.setattr(
            module.research_search, "search_candidates", lambda *args: (retrieve(), None)
        )
    with pytest.raises(ValueError, match="^Unable to evaluate planned retrieval$"):
        module.evaluate(engine, raw(data))


def test_same_readonly_repeatable_transaction_and_every_public_table_unchanged(engine):
    _, data = corpus(engine)
    statements, connections = [], set()

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

    def observe(conn, cursor, statement, parameters, context, executemany):
        if not statement.startswith("SHOW"):
            statements.append(statement)
            connections.add(id(conn))
            assert conn.scalar(text("SHOW transaction_isolation")) == "repeatable read"
            assert conn.scalar(text("SHOW transaction_read_only")) == "on"

    before = state()
    event.listen(engine, "before_cursor_execute", observe)
    try:
        api().evaluate(engine, raw(data))
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert statements and all(s.lstrip().upper().startswith("SELECT") for s in statements)
    assert len(connections) == 1
    assert state() == before


def test_negative_only_empty_results_preserve_null_denominators(engine):
    _, data = corpus(engine)
    data["baseline"]["cases"] = [data["baseline"]["cases"][1]]
    data["plans"] = [data["plans"][1]]
    data["plans"][0]["queries"] = ["없는어"]
    report = api().evaluate(engine, raw(data))
    for summary in report.summary.values():
        assert summary["positive_cases"] == 0 and summary["negative_cases"] == 1
        assert summary["hit_at_1"] is None and summary["macro_family_recall_at_5"] is None
        assert summary["all_required_at_5"] is None and summary["negative_no_match"] == 1
        assert summary["returned_count"] == 0 and summary["judged_precision"] is None


def test_sdk_rejects_forged_models_and_wrong_engine_before_access(engine):
    from sqlalchemy import create_engine

    module = api()
    model = module.parse_job(raw(planned()))
    with pytest.raises(ValueError, match="^Unable to evaluate planned retrieval$"):
        module.evaluate(engine, model.model_construct(plans=(object(),) * 100000))
    sqlite = create_engine("sqlite://")
    try:
        with pytest.raises(ValueError, match="^Unable to evaluate planned retrieval$"):
            module.evaluate(sqlite, raw(planned()))
    finally:
        sqlite.dispose()


def test_all_unjudged_positive_case_does_not_claim_precision(engine):
    ids, data = corpus(engine)
    data["baseline"]["cases"] = [data["baseline"]["cases"][0]]
    data["plans"] = [data["plans"][0]]
    data["plans"][0].update(queries=["모름"], irrelevant_snapshot_ids=[])
    report = api().evaluate(engine, raw(data))
    assert report.cases[0].planned.ranked_snapshot_ids == (ids[2],)
    assert report.cases[0].planned.family_recall_at_5 == 0
    assert report.summary["planned"]["unjudged_count"] == 1
    assert report.summary["planned"]["relevant_count"] == 0
    assert report.summary["planned"]["irrelevant_count"] == 0
    assert report.summary["planned"]["judged_precision"] is None


def test_original_and_planned_paths_keep_snapshot_during_concurrent_insert(engine, monkeypatch):
    ids, data = corpus(engine)
    module = api()
    actual_search = module.research_search.search_candidates
    inserted = False

    def insert_then_search(conn, row, queries, parent):
        nonlocal inserted
        assert parent is None
        if not inserted:
            inserted = True
            identity = uuid4()
            bundle = make_bundle("복구어", workspace=data["baseline"]["workspace_id"])
            repo = EvidenceRepository(engine)
            repo.save(identity, bundle)
            repo.rebuild_projection(bundle.document.workspace_id, identity)
        return actual_search(conn, row, queries, parent)

    monkeypatch.setattr(module.research_search, "search_candidates", insert_then_search)
    assert module.evaluate(engine, raw(data)).cases[0].planned.ranked_snapshot_ids == ids[:2]
    with pytest.raises(ValueError, match="^Unable to evaluate planned retrieval$"):
        module.evaluate(engine, raw(data))


@pytest.mark.parametrize("outcome", [[], (), ((),), ((), None, None), ((), ())])
def test_forged_search_envelope_rejected(engine, monkeypatch, outcome):
    _, data = corpus(engine)
    module = api()
    monkeypatch.setattr(module.research_search, "search_candidates", lambda *args: outcome)
    with pytest.raises(ValueError, match="^Unable to evaluate planned retrieval$"):
        module.evaluate(engine, raw(data))


def test_planned_corpus_hash_changes_for_valid_canonical_replacement(engine):
    _, data = corpus(engine)
    before = api().evaluate(engine, raw(data))
    repo = EvidenceRepository(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE source_documents, outbox CASCADE"))
    for identity in data["baseline"]["corpus_snapshot_ids"]:
        bundle = make_bundle("다른 합성 자료", workspace=data["baseline"]["workspace_id"])
        repo.save(UUID(identity), bundle)
        repo.rebuild_projection(bundle.document.workspace_id, UUID(identity))
    after = api().evaluate(engine, raw(data))
    assert after.corpus_sha256 != before.corpus_sha256
    assert after.question_gold_sha256 == before.question_gold_sha256
    assert after.plans_labels_sha256 == before.plans_labels_sha256
    assert after.declared_corpus_sha256 == before.declared_corpus_sha256
