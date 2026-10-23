import json
from collections.abc import Iterator

import pytest
from issuedigest_agents.json_whitespace_guard import JsonWhitespaceGuard, JsonWhitespaceGuardError

PARTITIONS = [(10_000,), (1,), (2,), (3, 1, 11, 2, 7)]


def chunks(text: str, widths: tuple[int, ...]) -> Iterator[str]:
    """Partition a synthetic fixture, including empty boundary chunks."""
    yield ""
    offset = 0
    index = 0
    while offset < len(text):
        width = widths[index % len(widths)]
        yield text[offset : offset + width]
        yield ""
        offset += width
        index += 1


def feed_preserved(guard: JsonWhitespaceGuard, text: str, widths: tuple[int, ...]) -> None:
    for delta in chunks(text, widths):
        assert guard.feed(delta) is delta


def test_new_guard_starts_with_empty_read_only_observation() -> None:
    from issuedigest_agents.json_whitespace_guard import (
        JSON_WHITESPACE_GUARD_PROFILE,
        JSON_WHITESPACE_RUN_LIMIT,
        JsonWhitespaceGuard,
        JsonWhitespaceGuardError,
    )

    guard = JsonWhitespaceGuard()

    assert JSON_WHITESPACE_GUARD_PROFILE == "json-whitespace-guard-v1"
    assert JSON_WHITESPACE_RUN_LIMIT == 256
    assert issubclass(JsonWhitespaceGuardError, ValueError)
    assert guard.failed is False
    assert guard.characters_consumed == 0
    assert guard.outside_whitespace_run == 0


@pytest.mark.parametrize("widths", PARTITIONS)
@pytest.mark.parametrize("length", [0, 1, 255, 256])
def test_outside_whitespace_through_256_is_preserved(widths: tuple[int, ...], length: int) -> None:
    guard = JsonWhitespaceGuard()
    feed_preserved(guard, " " * length, widths)
    assert guard.failed is False
    assert guard.characters_consumed == length
    assert guard.outside_whitespace_run == length


@pytest.mark.parametrize("widths", PARTITIONS)
@pytest.mark.parametrize("whitespace", [" " * 257, "\t\r\n " * 64 + "\t"])
def test_257th_outside_whitespace_fails_before_the_suffix(
    widths: tuple[int, ...], whitespace: str
) -> None:
    guard = JsonWhitespaceGuard()
    text = "🧪[]" + whitespace + '"unvisited synthetic suffix"' + " " * 300

    with pytest.raises(JsonWhitespaceGuardError, match="^JSON whitespace run limit exceeded$"):
        feed_preserved(guard, text, widths)

    assert guard.failed is True
    assert guard.characters_consumed == 260
    assert guard.outside_whitespace_run == 257
    for delta in ["", "[]", " " * 300]:
        with pytest.raises(
            JsonWhitespaceGuardError, match="^JSON whitespace guard already failed$"
        ):
            guard.feed(delta)
        assert guard.characters_consumed == 260
        assert guard.outside_whitespace_run == 257


@pytest.mark.parametrize("widths", PARTITIONS)
@pytest.mark.parametrize("separator", ["0", "{", "}", "[", "]", ",", ":", '""'])
def test_non_whitespace_resets_the_run(widths: tuple[int, ...], separator: str) -> None:
    guard = JsonWhitespaceGuard()
    text = " " * 256 + separator + "\t\r\n " * 64
    feed_preserved(guard, text, widths)
    assert guard.failed is False
    assert guard.outside_whitespace_run == 256
    assert guard.characters_consumed == len(text)


@pytest.mark.parametrize("widths", PARTITIONS)
@pytest.mark.parametrize("string_space", [" " * 2048, "\t\r\n " * 512])
def test_long_whitespace_inside_strings_is_preserved(
    widths: tuple[int, ...], string_space: str
) -> None:
    guard = JsonWhitespaceGuard()
    text = '"' + string_space + '" \t'
    feed_preserved(guard, text, widths)
    assert guard.characters_consumed == len(text)
    assert guard.outside_whitespace_run == 2


@pytest.mark.parametrize("widths", PARTITIONS)
@pytest.mark.parametrize("backslashes", [1, 2, 3, 4, 5, 6])
def test_odd_and_even_backslashes_control_whether_quote_closes_string(
    widths: tuple[int, ...], backslashes: int
) -> None:
    guard = JsonWhitespaceGuard()
    prefix = '"' + "\\" * backslashes + '"'
    if backslashes % 2:
        text = prefix + " " * 300 + '" \t'
        feed_preserved(guard, text, widths)
        assert guard.characters_consumed == len(text)
        assert guard.outside_whitespace_run == 2
    else:
        with pytest.raises(JsonWhitespaceGuardError, match="^JSON whitespace run limit exceeded$"):
            feed_preserved(guard, prefix + " " * 300, widths)
        assert guard.characters_consumed == len(prefix) + 257
        assert guard.outside_whitespace_run == 257


@pytest.mark.parametrize("widths", PARTITIONS)
def test_literal_unicode_escape_is_not_decoded_into_a_quote(widths: tuple[int, ...]) -> None:
    guard = JsonWhitespaceGuard()
    text = r'"\u0022' + " " * 300 + r"\u005c\"" + " " * 300 + '" '
    feed_preserved(guard, text, widths)
    assert guard.characters_consumed == len(text)
    assert guard.outside_whitespace_run == 1


@pytest.mark.parametrize("widths", PARTITIONS)
@pytest.mark.parametrize("separator", ["\u00a0", "\u2003", "\u2028", "\u3000", "\v", "\f", "🧪"])
def test_non_json_whitespace_and_emoji_reset_run_without_normalization(
    widths: tuple[int, ...], separator: str
) -> None:
    guard = JsonWhitespaceGuard()
    text = " " * 256 + separator + " " * 256
    feed_preserved(guard, text, widths)
    assert guard.characters_consumed == 513
    assert guard.outside_whitespace_run == 256


def test_empty_chunks_preserve_pending_escape_and_outside_run() -> None:
    guard = JsonWhitespaceGuard()
    guard.feed(" " * 256)
    assert guard.feed("") == ""
    assert guard.outside_whitespace_run == 256
    guard.feed('"\\')
    assert guard.feed("") == ""
    guard.feed('"' + " " * 300)
    assert guard.outside_whitespace_run == 0
    guard.feed('"')
    assert guard.characters_consumed == 560


class Untouchable:
    def __str__(self) -> str:
        raise AssertionError("must not stringify rejected input")

    def __repr__(self) -> str:
        raise AssertionError("must not represent rejected input")

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("must not iterate rejected input")


class StringSubclass(str):
    def __str__(self) -> str:
        raise AssertionError("must not stringify a str subclass")

    def __repr__(self) -> str:
        raise AssertionError("must not represent a str subclass")

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("must not iterate a str subclass")


@pytest.mark.parametrize(
    "delta",
    [None, b" ", 7, True, Untouchable(), StringSubclass(" ")],
    ids=["none", "bytes", "integer", "boolean", "untouchable", "str-subclass"],
)
def test_only_exact_str_is_accepted_without_inspecting_invalid_objects(delta: object) -> None:
    guard = JsonWhitespaceGuard()
    guard.feed("[] ")
    with pytest.raises(JsonWhitespaceGuardError, match="^Invalid JSON argument chunk$") as raised:
        guard.feed(delta)  # type: ignore[arg-type]
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True
    assert guard.failed is True
    assert guard.characters_consumed == 3
    assert guard.outside_whitespace_run == 1
    with pytest.raises(JsonWhitespaceGuardError, match="^JSON whitespace guard already failed$"):
        guard.feed(Untouchable())  # type: ignore[arg-type]
    assert guard.characters_consumed == 3
    assert guard.outside_whitespace_run == 1


def test_rejected_chunk_returns_no_prefix_and_errors_suppress_ambient_cause() -> None:
    guard = JsonWhitespaceGuard()
    accepted = [guard.feed("[]")]
    try:
        raise RuntimeError("synthetic private marker")
    except RuntimeError:
        with pytest.raises(JsonWhitespaceGuardError) as raised:
            accepted.append(guard.feed(" " * 257 + "synthetic private marker"))
        assert str(raised.value) == "JSON whitespace run limit exceeded"
        assert raised.value.args == ("JSON whitespace run limit exceeded",)
        assert raised.value.__cause__ is None
        assert raised.value.__suppress_context__ is True
        with pytest.raises(JsonWhitespaceGuardError) as latched:
            guard.feed(Untouchable())  # type: ignore[arg-type]
        assert latched.value.__cause__ is None
        assert latched.value.__suppress_context__ is True
    assert accepted == ["[]"]
    assert guard.characters_consumed == 259


@pytest.mark.parametrize("widths", PARTITIONS)
@pytest.mark.parametrize("ensure_ascii", [False, True])
def test_known_valid_json_documents_are_preserved(
    widths: tuple[int, ...], ensure_ascii: bool
) -> None:
    document = {"title": '한글 🧪 "quoted" \\', "body": " " * 1024, "items": [None, True, 3]}
    text = json.dumps(document, ensure_ascii=ensure_ascii, indent=2)
    guard = JsonWhitespaceGuard()
    feed_preserved(guard, text, widths)
    assert guard.failed is False
    assert guard.characters_consumed == len(text)
    assert guard.outside_whitespace_run == 0


@pytest.mark.parametrize("widths", PARTITIONS)
@pytest.mark.parametrize("text", ["not json,,,", '"unfinished\\', "{{{{::::", '"' + " " * 300])
def test_guard_accepts_malformed_and_incomplete_fragments_without_certifying_json(
    widths: tuple[int, ...], text: str
) -> None:
    guard = JsonWhitespaceGuard()
    feed_preserved(guard, text, widths)
    assert guard.failed is False
    assert guard.characters_consumed == len(text)


def test_observation_properties_are_read_only_and_guard_has_no_reset_or_resume() -> None:
    guard = JsonWhitespaceGuard()
    for name in ["failed", "characters_consumed", "outside_whitespace_run"]:
        with pytest.raises(AttributeError):
            setattr(guard, name, 0)
    assert not hasattr(guard, "reset")
    assert not hasattr(guard, "resume")
    with pytest.raises(TypeError):
        JsonWhitespaceGuard(257)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        JsonWhitespaceGuard(limit=257)  # type: ignore[call-arg]


def test_state_stays_scalar_and_does_not_retain_input_chunks() -> None:
    guard = JsonWhitespaceGuard()
    initial_field_count = len(guard.__slots__)
    text = '"synthetic unique marker ' + "🧪 " * 10_000 + '"'
    assert guard.feed(text) is text
    assert not hasattr(guard, "__dict__")
    assert len(guard.__slots__) == initial_field_count
    assert all(type(getattr(guard, name)) in (bool, int) for name in guard.__slots__)
    with pytest.raises(JsonWhitespaceGuardError):
        guard.feed(" " * 257 + "unvisited marker")
    assert all(type(getattr(guard, name)) in (bool, int) for name in guard.__slots__)
