"""Incremental lexical detection of excessive whitespace in JSON arguments."""

JSON_WHITESPACE_GUARD_PROFILE = "json-whitespace-guard-v1"
JSON_WHITESPACE_RUN_LIMIT = 256


class JsonWhitespaceGuardError(ValueError):
    """A tool-argument stream has violated the whitespace guard policy."""


class JsonWhitespaceGuard:
    """Observe one stream without parsing JSON, retaining text, or cancelling transport.

    Feed each argument delta before buffering or using it. Successful feeds return
    the original object; a rejected chunk returns no prefix. This fixed heuristic
    can reject legal formatting and does not certify content or completion.
    """

    __slots__ = ("_in_string", "_escape", "_run", "_characters", "_failed")

    def __init__(self) -> None:
        self._in_string = False
        self._escape = False
        self._run = 0
        self._characters = 0
        self._failed = False

    @property
    def failed(self) -> bool:
        return self._failed

    @property
    def characters_consumed(self) -> int:
        return self._characters

    @property
    def outside_whitespace_run(self) -> int:
        return self._run

    def feed(self, delta: str) -> str:
        """Inspect exact string chunks and latch failure at the first violation.

        The character count includes an offending code point, but excludes the
        uninspected suffix. It does not measure forwarded text, tokens, or cost.
        """
        if self._failed:
            raise JsonWhitespaceGuardError("JSON whitespace guard already failed") from None
        if type(delta) is not str:
            self._failed = True
            raise JsonWhitespaceGuardError("Invalid JSON argument chunk") from None

        for character in delta:
            self._characters += 1
            if self._in_string:
                if self._escape:
                    self._escape = False
                elif character == "\\":
                    self._escape = True
                elif character == '"':
                    self._in_string = False
            elif character in " \t\r\n":
                self._run += 1
                if self._run > JSON_WHITESPACE_RUN_LIMIT:
                    self._failed = True
                    raise JsonWhitespaceGuardError("JSON whitespace run limit exceeded") from None
            else:
                self._run = 0
                if character == '"':
                    self._in_string = True

        return delta
