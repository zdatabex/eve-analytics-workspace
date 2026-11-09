"""Stable source identifiers and document numbers."""

from __future__ import annotations

from collections import defaultdict


class IdFactory:
    """Counters only. Identifiers do not use the random stream."""

    def __init__(self) -> None:
        self._hubspot = 10_000_000
        self._prefixed: dict[str, int] = defaultdict(int)

    def hubspot(self) -> str:
        self._hubspot += 1
        return str(self._hubspot)

    def prefixed(self, prefix: str, width: int = 6) -> str:
        self._prefixed[prefix] += 1
        return f"{prefix}{self._prefixed[prefix]:0{width}d}"

    def document(self, prefix: str) -> str:
        key = f"doc:{prefix}"
        self._prefixed[key] += 1
        return f"{prefix}-{self._prefixed[key]:06d}"
