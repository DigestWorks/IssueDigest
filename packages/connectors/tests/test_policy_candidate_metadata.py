"""Additive discovery metadata contract over synthetic list HTML only."""

from datetime import UTC, date, datetime

import pytest
from issuedigest_connectors import policy_sdk as sdk
from pydantic import ValidationError


def row(identity="123456789", title="합성 제목", day="2024.02.29", publisher="합성부", href=None):
    href = href or f"/news/policyNewsView.do?newsId={identity}"
    return (
        f'<li><a href="{href}"><span class="text"><strong>{title}</strong>'
        f'<span class="source"><span>{day}</span><span>{publisher}</span></span>'
        "</span></a></li>"
    )


def listing(*rows):
    return (
        '<div class="article_body"><div class="list_type"><ul>'
        + "".join(rows)
        + "</ul></div></div>"
    )


def capture(*rows):
    return sdk.PolicyDiscovery(
        schema_version=1,
        collected_at=datetime(2026, 10, 19, tzinfo=UTC),
        list_html=listing(*(rows or (row(),))),
    )


def metadata(value):
    function = getattr(sdk, "policy_candidate_metadata", None)
    assert callable(function), "missing additive metadata SDK"
    return function(value)


def test_metadata_normalizes_visible_fields_preserves_exact_capture_and_hides_repr():
    value = capture(row(title=" 합성\n 제목 é 😀 ", publisher=" 합성\t 부 "))
    raw = sdk.serialize_policy_discovery(value)
    result = metadata(value)
    assert len(result) == 1
    item = result[0]
    assert item.model_dump() == {
        "news_id": "123456789",
        "canonical_url": "https://www.korea.kr/news/policyNewsView.do?newsId=123456789",
        "title": "합성 제목 é 😀",
        "published_on": date(2024, 2, 29),
        "publisher": "합성 부",
    }
    assert sdk.serialize_policy_discovery(value) == raw
    assert repr(item) == "PolicyCandidateMetadata()"
    import issuedigest_connectors as public

    assert public.PolicyCandidateMetadata is type(item)
    assert public.policy_candidate_metadata(value) == result
    with pytest.raises(ValidationError):
        item.publisher = "다른 부"
    for update in ({"published_on": "2024-02-29"}, {"extra": "PRIVATE"}, {"news_id": 123456789}):
        with pytest.raises(ValidationError):
            type(item).model_validate({**item.model_dump(), **update})


@pytest.mark.parametrize(
    "day",
    [
        "2023.02.29",
        "2024.02.30",
        "2024.2.29",
        "２０２４.02.29",
        " 2024.02.29",
        "2024.02.29 ",
        "2024-02-29",
        "0000.01.01",
        "2024.13.01",
        "2024.02.29 extra",
    ],
)
def test_metadata_rejects_ambiguous_date_without_narrowing_title_only_sdk(day):
    value = capture(row(day=day))
    assert sdk.policy_candidates(value)[0].title == "합성 제목"
    with pytest.raises(sdk.PolicyError, match="^Unable to validate policy discovery$"):
        metadata(value)


@pytest.mark.parametrize("publisher", ["x" * 201, "\u200b" * 201])
def test_metadata_rejects_oversized_publisher_but_old_sdk_accepts(publisher):
    value = capture(row(publisher=publisher))
    assert len(sdk.policy_candidates(value)) == 1
    with pytest.raises(sdk.PolicyError):
        metadata(value)


@pytest.mark.parametrize("field", ["date", "publisher", "title"])
def test_conflicting_duplicate_metadata_rejects_whole_discovery(field):
    first = row()
    second = row(
        day="2024.03.01" if field == "date" else "2024.02.29",
        publisher="다른 부" if field == "publisher" else "합성부",
        title="다른 제목" if field == "title" else "합성 제목",
    )
    if field == "title":
        # Existing title conflict guard already rejects at discovery construction.
        with pytest.raises(ValidationError):
            capture(first, second)
    else:
        value = capture(first, second)
        assert len(sdk.policy_candidates(value)) == 1
        with pytest.raises(sdk.PolicyError):
            metadata(value)


def test_identical_duplicates_collapse_and_noncanonical_links_never_become_candidates():
    result = metadata(
        capture(row(), row(publisher=" 합성부 "), row(href="https://evil.test/PRIVATE"))
    )
    assert [item.news_id for item in result] == ["123456789"]


@pytest.mark.parametrize("mutation", ["hidden", "missing", "ambiguous", "blank"])
@pytest.mark.parametrize("part", ["2024.02.29", "합성부"])
def test_missing_hidden_or_ambiguous_metadata_fails_closed(mutation, part):
    html = listing(row())
    original = f"<span>{part}</span>"
    replacement = {
        "hidden": f"<span hidden>{part}</span>",
        "missing": "",
        "ambiguous": original * 2,
        "blank": "<span> </span>",
    }[mutation]
    forged = capture().model_copy(update={"list_html": html.replace(original, replacement)})
    with pytest.raises(sdk.PolicyError):
        metadata(forged)


@pytest.mark.parametrize(
    "update",
    [
        {"schema_version": True},
        {"extra": "PRIVATE"},
        {"list_html": "PRIVATE"},
        {"collected_at": "2026-10-19T00:00:00Z"},
    ],
)
def test_metadata_revalidates_forged_capture_without_logging(update, caplog, capsys):
    with pytest.raises(sdk.PolicyError) as caught:
        metadata(capture().model_copy(update=update))
    assert caught.value.__suppress_context__
    assert caplog.text == "" and capsys.readouterr() == ("", "")
