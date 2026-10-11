"""Bundle integrity checks supplied references without endorsing their content."""

import importlib
import importlib.util
import json
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4

import pytest
from pydantic import ValidationError

research = (
    importlib.import_module("issuedigest_domain.research")
    if importlib.util.find_spec("issuedigest_domain.research")
    else None
)
relations = (
    importlib.import_module("issuedigest_domain.relations")
    if importlib.util.find_spec("issuedigest_domain.relations")
    else None
)


def test_research_contracts_available():
    assert research is not None and relations is not None, "research/relations contracts missing"


def uid():
    return str(uuid4())


def evidence(workspace):
    document, version, representation, citation = uid(), uid(), uid(), uid()
    text = "정부가 법안을 검토했다"
    return {
        "document": {
            "document_id": document,
            "workspace_id": workspace,
            "provider": "synthetic",
            "source_id": document,
            "source_kind": "other",
        },
        "version": {
            "version_id": version,
            "document_id": document,
            "raw_object_id": uid(),
            "raw_sha256": "a" * 64,
            "media_type": "text/plain",
            "collected_at": "2026-01-01T00:00:00Z",
        },
        "representation": {
            "representation_id": representation,
            "document_version_id": version,
            "parser_name": "synthetic",
            "parser_version": "1",
            "normalization_profile": "identity",
            "text": text,
            "text_sha256": sha256(text.encode()).hexdigest(),
            "pages": [],
            "tables": [],
        },
        "citations": [
            {
                "citation_id": citation,
                "document_version_id": version,
                "representation_id": representation,
                "selector": {"kind": "text", "start": 0, "end": len(text), "quote": text},
            }
        ],
    }


def ref(kind, identifier):
    return {"kind": kind, f"{kind}_id": identifier}


def bundle_data():
    workspace = uid()
    proof = evidence(workspace)
    citations = [proof["citations"][0]["citation_id"]]
    entities = [
        {"entity_id": uid(), "workspace_id": workspace, "kind": kind, "name": "동일 이름"}
        for kind in ["bill", "person", "organization", "bill", "policy", "issue", "place"]
    ]
    claims = [
        {
            "claim_id": uid(),
            "workspace_id": workspace,
            "text": text,
            "basis": "source_assertion",
            "speaker_entity_id": None,
            "subject_entity_ids": [],
            "citation_ids": citations,
        }
        for text in ["화자가 말한 내용", "내용의 참 여부는 미검증"]
    ]
    relation = {
        "relation_id": uid(),
        "workspace_id": workspace,
        "predicate": "reviewed_by",
        "source": ref("entity", entities[0]["entity_id"]),
        "target": ref("entity", entities[2]["entity_id"]),
        "basis": "source_assertion",
        "citation_ids": citations,
    }
    return {
        "workspace_id": workspace,
        "evidence": [proof],
        "entities": entities,
        "claims": claims,
        "relations": [relation],
        "observations": [],
        "support_reviews": [],
    }


def review(citations, **changes):
    return {
        "review_id": uid(),
        "reviewer_kind": "human",
        "reviewer_id": "reader",
        "method": "reading",
        "method_version": "1",
        "reviewed_at": "2026-01-01T00:00:00Z",
        "rationale": "해당 자료에서 확인",
        "citation_ids": citations,
        **changes,
    }


def validate(data):
    return research.ResearchBundle.model_validate_json(json.dumps(data))


def test_bundle_roundtrip_same_names_and_evidence_do_not_certify_claim_truth():
    data = bundle_data()
    data["claims"][0]["speaker_entity_id"] = data["entities"][1]["entity_id"]
    data["claims"][0]["subject_entity_ids"] = [data["entities"][0]["entity_id"]]
    data["support_reviews"] = [
        review(
            data["claims"][0]["citation_ids"],
            target=ref("claim", data["claims"][0]["claim_id"]),
            scope="attribution",
            assessment="supported",
        )
    ]
    item = validate(data)
    assert item.entities[0].name == item.entities[1].name
    assert item.claims[0].speaker_entity_id == item.entities[1].entity_id
    assert item.support_reviews[0].scope == "attribution"
    assert research.ResearchBundle.model_validate_json(item.model_dump_json()) == item
    assert item.entities[0].identity_review is None
    assert isinstance(item.relations, tuple)
    with pytest.raises(ValidationError):
        item.relations[0].predicate = "causes"


def test_empty_work_bundle_is_valid():
    item = research.ResearchBundle(
        workspace_id=uuid4(),
        evidence=(),
        entities=(),
        claims=(),
        relations=(),
        observations=(),
        support_reviews=(),
    )
    assert item.schema_version == 1


@pytest.mark.parametrize("value", [True, 1.0, "1", 2])
def test_research_schema_version_rejects_coercion_and_unknown_versions(value):
    with pytest.raises(ValidationError):
        validate({**bundle_data(), "schema_version": value})


@pytest.mark.parametrize(
    "predicate,source,target",
    [
        ("introduced_by", 0, 1),
        ("introduced_by", 0, 2),
        ("reviewed_by", 0, 2),
        ("alternative_to", 0, 3),
    ],
)
def test_registered_entity_relation_directions_are_supported(predicate, source, target):
    data = bundle_data()
    data["relations"][0].update(
        predicate=predicate,
        source=ref("entity", data["entities"][source]["entity_id"]),
        target=ref("entity", data["entities"][target]["entity_id"]),
    )
    assert validate(data).relations[0].predicate == predicate


@pytest.mark.parametrize("predicate", ["supports", "contradicts"])
def test_claim_relations_are_directed_and_not_automatically_reversed(predicate):
    data = bundle_data()
    data["relations"][0].update(
        predicate=predicate,
        source=ref("claim", data["claims"][0]["claim_id"]),
        target=ref("claim", data["claims"][1]["claim_id"]),
    )
    assert len(validate(data).relations) == 1


@pytest.mark.parametrize("index", list(range(7)))
def test_document_mentions_all_supported_entity_kinds(index):
    data = bundle_data()
    data["relations"][0].update(
        predicate="mentions",
        source=ref("document", data["evidence"][0]["document"]["document_id"]),
        target=ref("entity", data["entities"][index]["entity_id"]),
    )
    assert validate(data).relations[0].predicate == "mentions"


@pytest.mark.parametrize(
    "predicate,source,target",
    [
        ("introduced_by", 1, 0),
        ("introduced_by", 0, 4),
        ("reviewed_by", 2, 0),
        ("reviewed_by", 0, 1),
        ("alternative_to", 0, 1),
        ("alternative_to", 1, 3),
    ],
)
def test_entity_kind_and_reverse_directions_are_rejected(predicate, source, target):
    data = bundle_data()
    data["relations"][0].update(
        predicate=predicate,
        source=ref("entity", data["entities"][source]["entity_id"]),
        target=ref("entity", data["entities"][target]["entity_id"]),
    )
    with pytest.raises(ValidationError):
        validate(data)


@pytest.mark.parametrize(
    "changes",
    [
        {"predicate": "causes"},
        {"ontology_version": "v2"},
        {"citation_ids": []},
        {"basis": "inference"},
        {"predicate": "supports"},
        {"source": {"kind": "claim", "claim_id": uid()}},
        {"target": {"kind": "document", "document_id": uid()}},
        {"source": {"kind": "relation", "relation_id": uid()}},
        {"derivation": {"method": "a", "method_version": "1", "rationale": "r"}},
    ],
)
def test_relation_local_contract_rejects_unknown_or_inconsistent_input(changes):
    with pytest.raises(ValidationError):
        relations.Relation.model_validate({**bundle_data()["relations"][0], **changes})


def test_self_relation_duplicate_citations_and_unregistered_inferred_causality_are_rejected():
    relation = bundle_data()["relations"][0]
    for changes in [
        {"target": relation["source"]},
        {"citation_ids": relation["citation_ids"] * 2},
        {
            "predicate": "causes",
            "basis": "inference",
            "derivation": {
                "method": "time order",
                "method_version": "1",
                "rationale": "co-occurrence",
            },
        },
    ]:
        with pytest.raises(ValidationError):
            relations.Relation.model_validate({**relation, **changes})


@pytest.mark.parametrize(
    "collection", ["entities", "claims", "relations", "observations", "evidence"]
)
def test_every_record_and_document_requires_root_workspace(collection):
    data = bundle_data()
    if collection == "observations":
        data[collection] = [observation_data(data)]
    item = data[collection][0]
    (item["document"] if collection == "evidence" else item)["workspace_id"] = uid()
    with pytest.raises(ValidationError):
        validate(data)


def observation_data(data):
    return {
        "observation_id": uid(),
        "workspace_id": data["workspace_id"],
        "subject_entity_id": data["entities"][0]["entity_id"],
        "raw_value": "40%",
        "value": "40",
        "context": {"metric": "support"},
        "citation_ids": data["claims"][0]["citation_ids"],
    }


@pytest.mark.parametrize(
    "collection", ["entities", "claims", "relations", "observations", "support_reviews"]
)
def test_each_collection_id_is_unique(collection):
    data = bundle_data()
    if collection == "observations":
        data[collection] = [observation_data(data)]
    if collection == "support_reviews":
        data[collection] = [
            review(
                data["claims"][0]["citation_ids"],
                target=ref("claim", data["claims"][0]["claim_id"]),
                scope="content",
                assessment="insufficient",
            )
        ]
    data[collection].append(deepcopy(data[collection][0]))
    with pytest.raises(ValidationError):
        validate(data)


@pytest.mark.parametrize(
    "location",
    [
        "speaker",
        "subject",
        "observation",
        "relation_source",
        "relation_target",
        "review_target",
        "review_relation",
    ],
)
def test_unknown_or_wrong_typed_references_are_rejected(location):
    data = bundle_data()
    unknown = uid()
    if location == "speaker":
        data["claims"][0]["speaker_entity_id"] = unknown
    elif location == "subject":
        data["claims"][0]["subject_entity_ids"] = [data["claims"][1]["claim_id"]]
    elif location == "observation":
        data["observations"] = [{**observation_data(data), "subject_entity_id": unknown}]
    elif location.startswith("relation_"):
        data["relations"][0][location.removeprefix("relation_")]["entity_id"] = unknown
    else:
        kind = "relation" if location == "review_relation" else "claim"
        data["support_reviews"] = [
            review(
                data["claims"][0]["citation_ids"],
                target=ref(kind, unknown),
                scope="relation" if kind == "relation" else "content",
                assessment="supported",
            )
        ]
    with pytest.raises(ValidationError):
        validate(data)


@pytest.mark.parametrize(
    "target", ["claim", "relation", "observation", "identity_review", "support_review"]
)
def test_every_citation_reference_must_exist(target):
    data = bundle_data()
    unknown = [uid()]
    if target == "claim":
        data["claims"][0]["citation_ids"] = unknown
    elif target == "relation":
        data["relations"][0]["citation_ids"] = unknown
    elif target == "observation":
        data["observations"] = [{**observation_data(data), "citation_ids": unknown}]
    elif target == "identity_review":
        data["entities"][0]["identity_review"] = review(unknown, assessment="confirmed")
    else:
        data["support_reviews"] = [
            review(
                unknown,
                target=ref("claim", data["claims"][0]["claim_id"]),
                scope="content",
                assessment="supported",
            )
        ]
    with pytest.raises(ValidationError):
        validate(data)


def test_external_identity_collision_cannot_be_overridden_by_review():
    data = bundle_data()
    identity = {"provider": "synthetic", "namespace": "person", "value": "123"}
    for item in data["entities"][:2]:
        item["source_identities"] = [identity]
        item["identity_review"] = review(data["claims"][0]["citation_ids"], assessment="confirmed")
    with pytest.raises(ValidationError):
        validate(data)


def test_external_identity_namespace_and_provider_are_part_of_the_key():
    data = bundle_data()
    for index, item in enumerate(data["entities"][:2]):
        item["source_identities"] = [
            {"provider": str(index), "namespace": "person", "value": "123"}
        ]
    assert len(validate(data).entities) == 7


@pytest.mark.parametrize("case", ["identity_identity", "identity_support"])
def test_review_ids_are_unique_across_nested_identity_and_support_records(case):
    data = bundle_data()
    metadata = review(data["claims"][0]["citation_ids"])
    data["entities"][0]["identity_review"] = {**metadata, "assessment": "confirmed"}
    if case == "identity_identity":
        data["entities"][1]["identity_review"] = {**metadata, "assessment": "ambiguous"}
    else:
        data["support_reviews"] = [
            {
                **metadata,
                "target": ref("claim", data["claims"][0]["claim_id"]),
                "scope": "content",
                "assessment": "supported",
            }
        ]
    with pytest.raises(ValidationError):
        validate(data)


@pytest.mark.parametrize("kind", ["claim", "relation"])
def test_review_citations_must_be_subset_of_target_even_when_other_evidence_exists(kind):
    data = bundle_data()
    another = evidence(data["workspace_id"])
    data["evidence"].append(another)
    target = data["claims" if kind == "claim" else "relations"][0]
    data["support_reviews"] = [
        review(
            [another["citations"][0]["citation_id"]],
            target=ref(kind, target[f"{kind}_id"]),
            scope="content" if kind == "claim" else "relation",
            assessment="supported",
        )
    ]
    with pytest.raises(ValidationError):
        validate(data)
    data["support_reviews"][0]["citation_ids"] = target["citation_ids"]
    assert validate(data).support_reviews[0].assessment == "supported"


def test_mentions_accepts_any_source_version_but_rejects_other_document_evidence():
    data = bundle_data()
    first = data["evidence"][0]
    another_version = evidence(data["workspace_id"])
    another_version["document"] = deepcopy(first["document"])
    another_version["version"]["document_id"] = first["document"]["document_id"]
    other_document = evidence(data["workspace_id"])
    data["evidence"] += [another_version, other_document]
    data["relations"][0].update(
        predicate="mentions",
        source=ref("document", first["document"]["document_id"]),
        citation_ids=[
            first["citations"][0]["citation_id"],
            another_version["citations"][0]["citation_id"],
        ],
    )
    assert validate(data).relations[0].predicate == "mentions"
    data["relations"][0]["citation_ids"].append(other_document["citations"][0]["citation_id"])
    with pytest.raises(ValidationError):
        validate(data)


def shared_representation(data):
    extra = deepcopy(data["evidence"][0])
    extra["representation"]["representation_id"] = uid()
    extra["representation"]["parser_version"] = "2"
    extra["citations"][0]["citation_id"] = uid()
    extra["citations"][0]["representation_id"] = extra["representation"]["representation_id"]
    return extra


def test_same_document_and_version_allow_distinct_parsing_representations():
    data = bundle_data()
    data["evidence"].append(shared_representation(data))
    assert len(validate(data).evidence) == 2


@pytest.mark.parametrize("case", ["document", "version", "representation", "citation"])
def test_evidence_rejects_conflicts_and_duplicate_representation_or_citation_ids(case):
    data = bundle_data()
    extra = shared_representation(data)
    if case == "document":
        extra["document"]["source_id"] = "conflicting identity"
    elif case == "version":
        extra["version"]["raw_sha256"] = "b" * 64
    elif case == "representation":
        extra["representation"]["representation_id"] = data["evidence"][0]["representation"][
            "representation_id"
        ]
        extra["citations"][0]["representation_id"] = extra["representation"]["representation_id"]
    else:
        extra["citations"][0]["citation_id"] = data["evidence"][0]["citations"][0]["citation_id"]
    data["evidence"].append(extra)
    with pytest.raises(ValidationError):
        validate(data)


def test_nested_evidence_anchor_validation_is_preserved():
    data = bundle_data()
    data["evidence"][0]["citations"][0]["selector"]["quote"] = "wrong quote"
    with pytest.raises(ValidationError):
        validate(data)


def test_document_endpoint_must_exist_with_its_document_tag():
    data = bundle_data()
    data["relations"][0].update(
        predicate="mentions",
        source=ref("document", data["entities"][0]["entity_id"]),
    )
    with pytest.raises(ValidationError):
        validate(data)


def test_same_uuid_in_different_endpoint_types_is_not_a_self_relation():
    data = bundle_data()
    document = data["evidence"][0]["document"]["document_id"]
    data["entities"][0]["entity_id"] = document
    data["relations"][0].update(
        predicate="mentions",
        source=ref("document", document),
        target=ref("entity", document),
    )
    item = validate(data)
    assert item.relations[0].source.kind == "document"
    assert item.relations[0].target.kind == "entity"


def test_observation_nullable_subject_and_inference_relation_roundtrip():
    data = bundle_data()
    data["observations"] = [{**observation_data(data), "subject_entity_id": None}]
    data["relations"][0].update(
        basis="inference",
        derivation={"method": "supplied reasoning", "method_version": "1", "rationale": "provided"},
    )
    item = validate(data)
    assert item.observations[0].subject_entity_id is None
    assert item.relations[0].derivation.method == "supplied reasoning"
    assert research.ResearchBundle.model_validate_json(item.model_dump_json()) == item
