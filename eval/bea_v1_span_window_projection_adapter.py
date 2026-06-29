#!/usr/bin/env python3
"""Default-off eval-only span projection adapter for BEA-v1.

This adapter is intentionally pure and inert by default. It performs no
filesystem IO, no private reads, no retrieval, no runtime configuration, and no
gold-aware behavior. Callers must explicitly pass ``enabled=True`` to project
fixed span-window expansions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from bea_v1_span_window_repair_helpers import expand_evidence_span_record


def project_evidence_span_record(
    record: Mapping[str, Any],
    *,
    expansion_each_side: int,
    enabled: bool = False,
) -> dict[str, Any]:
    """Return a projected copy of one evidence span record.

    When ``enabled`` is false, the record is copied unchanged. When enabled is
    true, only ``start_line`` and ``end_line`` are expanded by the fixed caller
    supplied amount. No path, content, or gold fields are required.
    """

    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    if not enabled:
        return dict(record)
    return expand_evidence_span_record(record, expansion_each_side=expansion_each_side)


def project_evidence_spans(
    records: Iterable[Mapping[str, Any]],
    *,
    expansion_each_side: int,
    enabled: bool = False,
) -> list[dict[str, Any]]:
    """Project a sequence of evidence span records without changing order/count."""

    if isinstance(records, (str, bytes)):
        raise TypeError("records must be an iterable of mappings")
    return [
        project_evidence_span_record(record, expansion_each_side=expansion_each_side, enabled=enabled)
        for record in records
    ]
