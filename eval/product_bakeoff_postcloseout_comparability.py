#!/usr/bin/env python3
"""Scorer-equivalent repeatability policy for a future tournament design.

This module does **not** alter, reopen, or reinterpret B2.5.  The formal B2.5
attempt remains governed by its frozen exact semantic-hash gate and remains
failed closed.  The helpers below are post-closeout design material for a
separately preregistered future experiment.

The historical semantic hash covered diagnostic metadata, candidate ordering,
native candidate scores, and exact pack serialization.  Those fields are useful
for debugging, but some do not affect any B2/B2.1 quality score.  A scientific
comparability gate should fail when repeated observations can change a score,
lineage decision, or admitted outcome; diagnostic-only drift should be recorded
separately rather than silently converted into a different empirical claim.

The projection here is deliberately oracle-blind.  It retains every feature
that can affect the frozen scorer for *any* oracle row:

* admitted result/pack envelope;
* whether the candidate set is empty;
* the union of evidence and target line atoms;
* pack status; and
* support relation kind, parent target, path, and union of line atoms.

Ordering, duplicate segmentation, candidate-native scores, excerpts, channel
labels, explanations, and other diagnostic metadata are excluded because the
frozen scorer never reads them.  Source-currentness, lineage, fairness, and
provider isolation remain separate mandatory gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence


COMPARABILITY_POLICY_VERSION = (
    "product_bakeoff_postcloseout_scorer_equivalent_comparability.v1"
)


class ComparabilityError(ValueError):
    """Fail-closed error for malformed scorer-equivalence input."""


_MISSING = object()


def _field(value: Any, name: str, default: Any = _MISSING) -> Any:
    if isinstance(value, Mapping):
        found = value.get(name, _MISSING)
    else:
        found = getattr(value, name, _MISSING)
    if found is _MISSING:
        if default is not _MISSING:
            return default
        raise ComparabilityError(f"missing required field: {name}")
    return found


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _span_tuple(value: Any) -> tuple[str, int, int]:
    path = _field(value, "path")
    start = _field(value, "start_line")
    end = _field(value, "end_line")
    if not isinstance(path, str) or not path:
        raise ComparabilityError("scorer span path must be nonempty")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 1
        or end < start
    ):
        raise ComparabilityError("scorer span range is invalid")
    return path, start, end


def normalize_span_union(values: Iterable[Any]) -> tuple[tuple[str, int, int], ...]:
    """Return a canonical interval union equivalent to the scorer's atom set."""

    grouped: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for value in values:
        path, start, end = _span_tuple(value)
        grouped[path].append((start, end))

    merged: list[tuple[str, int, int]] = []
    for path in sorted(grouped):
        ranges = sorted(grouped[path])
        current_start: int | None = None
        current_end: int | None = None
        for start, end in ranges:
            if current_start is None:
                current_start, current_end = start, end
                continue
            assert current_end is not None
            if start <= current_end + 1:
                current_end = max(current_end, end)
                continue
            merged.append((path, current_start, current_end))
            current_start, current_end = start, end
        if current_start is not None:
            assert current_end is not None
            merged.append((path, current_start, current_end))
    return tuple(merged)


def normalize_support_union(
    values: Iterable[Any],
) -> tuple[tuple[str, str, str, int, int], ...]:
    grouped: dict[tuple[str, str, str], list[SimpleNamespace]] = defaultdict(list)
    for value in values:
        relation_kind = _field(value, "relation_kind")
        parent_target_id = _field(value, "parent_target_id")
        path, start, end = _span_tuple(value)
        if not isinstance(relation_kind, str) or not relation_kind:
            raise ComparabilityError("support relation kind must be nonempty")
        if not isinstance(parent_target_id, str) or not parent_target_id:
            raise ComparabilityError("support parent target id must be nonempty")
        grouped[(relation_kind, parent_target_id, path)].append(
            SimpleNamespace(path=path, start_line=start, end_line=end)
        )

    normalized: list[tuple[str, str, str, int, int]] = []
    for relation_kind, parent_target_id, path in sorted(grouped):
        for _, start, end in normalize_span_union(
            grouped[(relation_kind, parent_target_id, path)]
        ):
            normalized.append((relation_kind, parent_target_id, path, start, end))
    return tuple(normalized)


def scorer_equivalence_projection(cell: Any) -> dict[str, Any]:
    capture = _field(cell, "capture")
    output = _field(capture, "output")
    if output is None:
        raise ComparabilityError("accepted cell has no output")
    record = _field(cell, "record")
    pack = _field(output, "pack")
    operation = _field(record, "operation")
    projection: dict[str, Any] = {
        "policy_version": COMPARABILITY_POLICY_VERSION,
        "outcome_kind": "normal",
        "operation": operation,
        "admission_envelope": {
            "status": _field(record, "status"),
            "result_status": _field(record, "result_status"),
            "record_pack_status": _field(record, "pack_status"),
            "failure_category": _field(record, "failure_category", None),
        },
    }
    if operation == "context":
        projection.update(
            {
                "candidate_set_nonempty": bool(
                    _field(output, "validated_candidates")
                ),
                "pack_status": _field(pack, "pack_status"),
                "evidence_union": normalize_span_union(_field(output, "evidence")),
                "target_union": normalize_span_union(_field(pack, "targets")),
                "support_set_nonempty": bool(_field(pack, "support")),
            }
        )
    elif operation == "support":
        projection["support_union"] = normalize_support_union(
            _field(pack, "support")
        )
    else:
        raise ComparabilityError(f"unknown scorer operation: {operation}")
    return projection


def scorer_equivalence_hash(cell: Any) -> str:
    return "postcloseout_score_sem_" + hashlib.sha256(
        _canonical(scorer_equivalence_projection(cell))
    ).hexdigest()


def terminal_scorer_equivalence_hash(cell: Any) -> str:
    reason = _field(cell, "reason")
    context_cell = _field(cell, "context_cell")
    payload = {
        "policy_version": COMPARABILITY_POLICY_VERSION,
        "outcome_kind": "terminal_support",
        "reason": reason,
        "context_score_semantics": scorer_equivalence_projection(context_cell),
    }
    return "postcloseout_terminal_score_sem_" + hashlib.sha256(
        _canonical(payload)
    ).hexdigest()


def score_relevant_repeatability_gate(
    cells: Sequence[Any],
    terminal_cells: Sequence[Any] = (),
    *,
    expected_observations: int = 4,
) -> tuple[bool, tuple[str, ...]]:
    if expected_observations < 1:
        raise ComparabilityError("expected observations must be positive")
    groups: dict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)
    for cell in cells:
        record = _field(cell, "record")
        key = (
            _field(record, "adapter_id"),
            _field(record, "run_cell_id"),
            _field(record, "operation"),
        )
        groups[key].append(("normal", scorer_equivalence_hash(cell)))
    for cell in terminal_cells:
        key = (
            _field(cell, "adapter_id"),
            _field(cell, "run_cell_id"),
            "support",
        )
        groups[key].append(("terminal", terminal_scorer_equivalence_hash(cell)))

    failures: list[str] = []
    for key in sorted(groups):
        observations = groups[key]
        if len(observations) != expected_observations:
            failures.append(f"{key}: observations={len(observations)}")
        elif len(set(observations)) != 1:
            failures.append(f"{key}: scorer-relevant semantic drift")
    return not failures, tuple(failures)


def _span(path: str, start: int, end: int, **extra: Any) -> SimpleNamespace:
    return SimpleNamespace(path=path, start_line=start, end_line=end, **extra)


def _synthetic_cell(
    *,
    evidence: Sequence[Any],
    targets: Sequence[Any],
    support: Sequence[Any],
    candidates: Sequence[Any],
    pack_status: str = "ready",
    repetition: int = 1,
    operation: str = "context",
) -> SimpleNamespace:
    output = SimpleNamespace(
        validated_candidates=list(candidates),
        evidence=list(evidence),
        pack=SimpleNamespace(
            pack_status=pack_status,
            targets=list(targets),
            support=list(support),
        ),
    )
    return SimpleNamespace(
        record=SimpleNamespace(
            adapter_id="s0",
            run_cell_id="task",
            operation=operation,
            adapter_repetition=repetition,
            status="accepted",
            result_status="accepted",
            pack_status=pack_status,
            failure_category=None,
        ),
        capture=SimpleNamespace(output=output),
    )


def _equivalent_pair() -> tuple[SimpleNamespace, SimpleNamespace]:
    first = _synthetic_cell(
        evidence=[_span("a.rs", 1, 2), _span("a.rs", 3, 3)],
        targets=[_span("a.rs", 10, 11), _span("a.rs", 12, 12)],
        support=[
            _span(
                "b.rs",
                20,
                21,
                relation_kind="import",
                parent_target_id="parent",
            )
        ],
        candidates=[{"path": "a.rs", "native_score": 100, "rank": 1}],
    )
    second = _synthetic_cell(
        evidence=[_span("a.rs", 1, 3, why="different segmentation")],
        targets=[_span("a.rs", 10, 12, excerpt="diagnostic only")],
        support=[
            _span(
                "b.rs",
                20,
                20,
                relation_kind="import",
                parent_target_id="parent",
            ),
            _span(
                "b.rs",
                21,
                21,
                relation_kind="import",
                parent_target_id="parent",
            ),
        ],
        candidates=[
            {"path": "elsewhere.rs", "native_score": 1, "rank": 99},
            {"path": "a.rs", "native_score": 2, "rank": 2},
        ],
    )
    return first, second


def run_self_test() -> dict[str, Any]:
    first, equivalent = _equivalent_pair()
    changed_evidence = _synthetic_cell(
        evidence=[_span("a.rs", 1, 4)],
        targets=[_span("a.rs", 10, 12)],
        support=[
            _span(
                "b.rs",
                20,
                21,
                relation_kind="import",
                parent_target_id="parent",
            )
        ],
        candidates=[{"path": "a.rs"}],
    )
    empty_candidates = _synthetic_cell(
        evidence=[_span("a.rs", 1, 3)],
        targets=[_span("a.rs", 10, 12)],
        support=[
            _span(
                "b.rs",
                20,
                21,
                relation_kind="import",
                parent_target_id="parent",
            )
        ],
        candidates=[],
    )
    status_changed = _synthetic_cell(
        evidence=[_span("a.rs", 1, 3)],
        targets=[_span("a.rs", 10, 12)],
        support=[
            _span(
                "b.rs",
                20,
                21,
                relation_kind="import",
                parent_target_id="parent",
            )
        ],
        candidates=[{"path": "a.rs"}],
        pack_status="uncertain",
    )

    repeats = [first, equivalent, first, equivalent]
    repeat_ok, _ = score_relevant_repeatability_gate(repeats)
    drift_ok, _ = score_relevant_repeatability_gate(
        [first, equivalent, first, changed_evidence]
    )
    support_first = _synthetic_cell(
        operation="support",
        evidence=[_span("diagnostic.rs", 1, 100)],
        targets=[_span("diagnostic.rs", 1, 100)],
        support=[
            _span(
                "b.rs",
                20,
                21,
                relation_kind="import",
                parent_target_id="parent",
            )
        ],
        candidates=[{"native_score": 100}],
    )
    support_equivalent = _synthetic_cell(
        operation="support",
        evidence=[],
        targets=[],
        support=[
            _span(
                "b.rs",
                20,
                20,
                relation_kind="import",
                parent_target_id="parent",
            ),
            _span(
                "b.rs",
                21,
                21,
                relation_kind="import",
                parent_target_id="parent",
            ),
        ],
        candidates=[],
    )
    checks = [
        scorer_equivalence_hash(first) == scorer_equivalence_hash(equivalent),
        scorer_equivalence_hash(support_first)
        == scorer_equivalence_hash(support_equivalent),
        scorer_equivalence_hash(first) != scorer_equivalence_hash(changed_evidence),
        scorer_equivalence_hash(first) != scorer_equivalence_hash(empty_candidates),
        scorer_equivalence_hash(first) != scorer_equivalence_hash(status_changed),
        repeat_ok,
        not drift_ok,
        normalize_span_union([_span("a.rs", 1, 2), _span("a.rs", 3, 3)])
        == normalize_span_union([_span("a.rs", 1, 3)]),
    ]
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
        "b25_reinterpreted_or_reopened": False,
    }


def run_fault_test() -> dict[str, Any]:
    first, equivalent = _equivalent_pair()
    malformed = _synthetic_cell(
        evidence=[_span("a.rs", 0, 1)],
        targets=[],
        support=[],
        candidates=[],
    )
    checks: list[bool] = []
    try:
        scorer_equivalence_hash(malformed)
    except ComparabilityError:
        checks.append(True)
    else:
        checks.append(False)

    missing_output = SimpleNamespace(
        record=first.record, capture=SimpleNamespace(output=None)
    )
    try:
        scorer_equivalence_hash(missing_output)
    except ComparabilityError:
        checks.append(True)
    else:
        checks.append(False)

    incomplete_ok, _ = score_relevant_repeatability_gate([first, equivalent, first])
    checks.append(not incomplete_ok)

    terminal_a = SimpleNamespace(
        adapter_id="s0",
        run_cell_id="task",
        reason="parent_unavailable",
        context_cell=first,
    )
    terminal_b = SimpleNamespace(
        adapter_id="s0",
        run_cell_id="task",
        reason="different_reason",
        context_cell=equivalent,
    )
    terminal_ok, _ = score_relevant_repeatability_gate(
        [], [terminal_a, terminal_a, terminal_a, terminal_b]
    )
    checks.append(not terminal_ok)

    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def _print(value: Any) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Post-closeout scorer-equivalent comparability design"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    args = parser.parse_args()
    result = run_self_test() if args.self_test else run_fault_test()
    _print(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COMPARABILITY_POLICY_VERSION",
    "ComparabilityError",
    "normalize_span_union",
    "normalize_support_union",
    "scorer_equivalence_projection",
    "scorer_equivalence_hash",
    "terminal_scorer_equivalence_hash",
    "score_relevant_repeatability_gate",
    "run_self_test",
    "run_fault_test",
]
