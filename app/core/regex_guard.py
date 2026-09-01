"""Regular expressions supplied by a visitor, run without hanging the server.

A pattern like `(a+)+$` against thirty characters backtracks exponentially. The
tool endpoint is `async`, so that runs on the event loop — one such request
freezes every other request on the box, not just its own. Sixty of them a minute
get through the rate limiter easily.

`regex` is used when installed because it can enforce a wall-clock timeout that
works from any thread. Without it we fall back to refusing the shapes that cause
the blow-up, which is stricter than necessary but never dangerous.
"""
from __future__ import annotations

import re

try:  # optional, see requirements.txt
    import regex as _regex
except ImportError:  # pragma: no cover - depends on the deployment
    _regex = None

TIMEOUT_SECONDS = 2.0

# A quantified group whose body itself repeats or alternates: (a+)+, (a|a)*,
# (.*x){10}. This is the classic catastrophic-backtracking shape.
_NESTED_QUANTIFIER = re.compile(r"\((?![?]:?[=!<])[^()]*[*+{|][^()]*\)\s*[*+]|\)\s*\{\d+,?\d*\}")


class UnsafePattern(ValueError):
    """The pattern was refused before it could be run."""


def compile_pattern(pattern: str, flags: int = 0):
    """Compile a visitor's pattern, refusing what cannot be run safely."""
    if len(pattern) > 1000:
        raise UnsafePattern("That pattern is unreasonably long.")
    if _regex is None and _NESTED_QUANTIFIER.search(pattern):
        raise UnsafePattern(
            "This pattern nests one repeat inside another (like (a+)+), which can "
            "take exponential time to match. Rewrite it without the nested repeat."
        )
    engine = _regex if _regex is not None else re
    try:
        return engine.compile(pattern, flags)
    except Exception as exc:  # both engines raise their own error type
        raise UnsafePattern(f"Invalid pattern: {exc}") from exc


def _timed(fn, *args, **kwargs):
    if _regex is not None:
        return fn(*args, timeout=TIMEOUT_SECONDS, **kwargs)
    return fn(*args, **kwargs)


def find_all(compiled, subject: str, limit: int = 200) -> list:
    """Matches, capped in both time and count."""
    try:
        out = []
        for match in _timed(compiled.finditer, subject):
            out.append(match)
            if len(out) >= limit:
                break
        return out
    except TimeoutError as exc:
        raise UnsafePattern(
            f"That pattern took longer than {TIMEOUT_SECONDS:g}s against this text. "
            "It is almost certainly backtracking — simplify it."
        ) from exc


def substitute(compiled, replacement: str, subject: str) -> tuple[str, int]:
    try:
        return _timed(compiled.subn, replacement, subject)
    except TimeoutError as exc:
        raise UnsafePattern(
            f"That pattern took longer than {TIMEOUT_SECONDS:g}s against this text. "
            "It is almost certainly backtracking — simplify it."
        ) from exc
