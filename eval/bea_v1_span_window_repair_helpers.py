#!/usr/bin/env python3
"""Default-off BEA-v1 span-window repair helpers.

This module is intentionally pure: it performs no filesystem IO, no retrieval,
no runtime configuration, and no gold-aware behavior. It only expands line
windows for already-selected evidence records.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _require_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def expand_span_window(
    start: int,
    end: int,
    *,
    expansion_each_side: int,
    min_line: int = 1,
) -> dict[str, int]:
    """Expand a closed line window symmetrically and clamp the start.

    Returns a small dictionary with ``expanded_start_line`` and
    ``expanded_end_line``. The helper is gold-free and content-free: expansion is
    determined only by the input boundaries and fixed expansion amount.
    """

    start_i = _require_int("start", start)
    end_i = _require_int("end", end)
    expansion_i = _require_int("expansion_each_side", expansion_each_side)
    min_line_i = _require_int("min_line", min_line)
    if start_i > end_i:
        raise ValueError("start must be less than or equal to end")
    if expansion_i < 0:
        raise ValueError("expansion_each_side must be non-negative")
    if min_line_i < 1:
        raise ValueError("min_line must be at least 1")
    return {
        "expanded_start_line": max(min_line_i, start_i - expansion_i),
        "expanded_end_line": end_i + expansion_i,
    }


def expand_evidence_span_record(
    record: Mapping[str, Any],
    *,
    expansion_each_side: int,
) -> dict[str, Any]:
    """Return a copy of an evidence record with an expanded line window.

    The input record is not mutated. Only ``start_line`` and ``end_line`` are
    required; no path, content, or gold fields are required by this helper.
    """

    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    if "start_line" not in record or "end_line" not in record:
        raise ValueError("record must include start_line and end_line")
    expanded = expand_span_window(
        record["start_line"],
        record["end_line"],
        expansion_each_side=expansion_each_side,
    )
    copied = dict(record)
    copied["start_line"] = expanded["expanded_start_line"]
    copied["end_line"] = expanded["expanded_end_line"]
    return copied
