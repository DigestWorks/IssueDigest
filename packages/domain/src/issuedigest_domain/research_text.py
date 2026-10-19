"""Explicit v6 text presence; shared metadata and historical profiles keep their contracts."""

import re

# Union of Python Unicode whitespace and ECMAScript WhiteSpace/LineTerminator.
# Include Python-only U+001C..001F/U+0085 and ECMAScript-only U+FEFF explicitly.
_V6_NONBLANK = re.compile(
    r"[^\u0009-\u000D\u001C-\u0020\u0085\u00A0\u1680\u2000-\u200A"
    r"\u2028\u2029\u202F\u205F\u3000\uFEFF]"
)


def has_v6_text(value: str) -> bool:
    """Require at least one character outside the v6 whitespace union, without mutation."""
    return _V6_NONBLANK.search(value) is not None
