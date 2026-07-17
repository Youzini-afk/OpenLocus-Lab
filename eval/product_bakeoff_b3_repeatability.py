#!/usr/bin/env python3
"""Shared B3 repeatability canonicalization for both gate and scorer.

This module is future-only.  It does not reopen or reinterpret B2.5.  B3 uses
one implementation for the pre-score repeatability gate and for scorer-side
selection of one canonical quality observation per logical cell.  Diagnostic
serialization may drift without invalidating quality comparability, but every
field that can change a frozen score or same-arm support routing is retained.

The caller must provide the complete expected observation plan.  This makes a
wholly missing logical group, a duplicated repetition, or a cache-label drift
fail closed instead of disappearing from a grouping pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Iterable, Mapping, Sequence


B3_REPEATABILITY_POLICY_VERSION = "product_bakeoff_b3_repeatability.v1"
B3_EXPECTED_REPETITIONS = (1, 2, 3, 4)
B3_EXPECTED_CACHE_COUNTS = {"cold": 1, "warm": 3}

GroupKey = tuple[str, str, str]
ObservationSignature = tuple[int, str]
ExpectedObservationPlan = Mapping[GroupKey, Sequence[ObservationSignature]]


class B3RepeatabilityError(ValueError):
    """Fail-closed error for malformed or noncomparable B3 observations."""


@dataclass(frozen=True)
class CanonicalizedRepeatedOutcomes:
    """Canonical representatives selected by the shared gate/scorer core."""

    normal_cells: Mapping[GroupKey, Any]
    terminal_cells: Mapping[GroupKey, Any]
    projection_hashes: Mapping[GroupKey, str]
    diagnostic_drift_groups: tuple[GroupKey, ...]

    @property
    def logical_group_count(self) -> int:
        return len(self.normal_cells) + len(self.terminal_cells)


@dataclass(frozen=True)
class RepeatabilityGateResult:
    passed: bool
    failures: tuple[str, ...]
    diagnostic_drift_group_count: int


@dataclass(frozen=True)
class _ObservedOutcome:
    kind: str
    signature: ObservationSignature
    projection: Mapping[str, Any]
    projection_hash: str
    diagnostic_hash: str | None
    value: Any


_MISSING = object()


def _field(value: Any, name: str, default: Any = _MISSING) -> Any:
    if isinstance(value, Mapping):
        found = value.get(name, _MISSING)
    else:
        found = getattr(value, name, _MISSING)
    if found is _MISSING:
        if default is not _MISSING:
            return default
        raise B3RepeatabilityError(f"missing required field: {name}")
    return found


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _prefixed_digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value)).hexdigest()


def _validate_nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise B3RepeatabilityError(f"{name} must be a nonempty string")
    return value


def _span_tuple(value: Any) -> tuple[str, int, int]:
    path = _validate_nonempty_string(_field(value, "path"), "span path")
    start = _field(value, "start_line")
    end = _field(value, "end_line")
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 1
        or end < start
    ):
        raise B3RepeatabilityError("span range is invalid")
    return path, start, end


def normalize_span_union(values: Iterable[Any]) -> tuple[tuple[str, int, int], ...]:
    """Return the exact path/line atom union as canonical merged intervals."""

    grouped: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for value in values:
        path, start, end = _span_tuple(value)
        grouped[path].append((start, end))

    merged: list[tuple[str, int, int]] = []
    for path in sorted(grouped):
        current_start: int | None = None
        current_end: int | None = None
        for start, end in sorted(grouped[path]):
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
    """Canonicalize the support atoms read by the frozen B2/B2.1 scorer."""

    grouped: dict[tuple[str, str, str], list[SimpleNamespace]] = defaultdict(list)
    for value in values:
        relation_kind = _validate_nonempty_string(
            _field(value, "relation_kind"), "support relation kind"
        )
        parent_target_id = _validate_nonempty_string(
            _field(value, "parent_target_id"), "support parent target id"
        )
        path, start, end = _span_tuple(value)
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


def _target_cardinality_class(targets: Sequence[Any]) -> str:
    if not targets:
        return "empty"
    if len(targets) == 1:
        return "single"
    return "multiple"


def _require_admitted_normal(record: Any, output: Any) -> None:
    if _field(record, "status") != "accepted":
        raise B3RepeatabilityError("normal observation was not accepted")
    if _field(record, "result_status") != "ok":
        raise B3RepeatabilityError("normal observation result was not ok")
    if output is None:
        raise B3RepeatabilityError("accepted observation has no output")


def scorer_and_routing_projection(cell: Any) -> dict[str, Any]:
    """Project one admitted normal observation onto score/routing semantics.

    Context target cardinality is retained separately from its line union.
    A single ready target permits same-arm support execution and support credit;
    multiple targets do not, even when duplicate spans have the same atom union.
    """

    record = _field(cell, "record")
    capture = _field(cell, "capture")
    output = _field(capture, "output")
    _require_admitted_normal(record, output)
    operation = _field(record, "operation")
    if operation not in {"context", "support"}:
        raise B3RepeatabilityError(f"unknown scorer operation: {operation}")
    pack = _field(output, "pack")
    projection: dict[str, Any] = {
        "policy_version": B3_REPEATABILITY_POLICY_VERSION,
        "outcome_kind": "normal",
        "operation": operation,
        "admission_class": "accepted_scoreable_normal",
    }
    if operation == "context":
        targets = tuple(_field(pack, "targets"))
        projection.update(
            {
                "candidate_set_nonempty": bool(
                    _field(output, "validated_candidates")
                ),
                "pack_status": _field(pack, "pack_status"),
                "evidence_union": normalize_span_union(_field(output, "evidence")),
                "target_union": normalize_span_union(targets),
                "target_cardinality_class": _target_cardinality_class(targets),
                "support_set_nonempty": bool(_field(pack, "support")),
            }
        )
    else:
        projection["support_union"] = normalize_support_union(
            _field(pack, "support")
        )
    return projection


def scorer_and_routing_hash(cell: Any) -> str:
    return _prefixed_digest("b3outcome_sem_", scorer_and_routing_projection(cell))


def terminal_scorer_and_routing_projection(cell: Any) -> dict[str, Any]:
    reason = _validate_nonempty_string(_field(cell, "reason"), "terminal reason")
    context_cell = _field(cell, "context_cell")
    context_projection = scorer_and_routing_projection(context_cell)
    if context_projection.get("operation") != "context":
        raise B3RepeatabilityError("terminal support parent is not a context observation")
    return {
        "policy_version": B3_REPEATABILITY_POLICY_VERSION,
        "outcome_kind": "terminal_support",
        "operation": "support",
        "admission_class": "validated_terminal_support",
        "reason": reason,
        "context_score_and_routing_semantics": context_projection,
    }


def terminal_scorer_and_routing_hash(cell: Any) -> str:
    return _prefixed_digest(
        "b3terminal_outcome_sem_", terminal_scorer_and_routing_projection(cell)
    )


def _validate_group_key(value: Any) -> GroupKey:
    if not isinstance(value, tuple) or len(value) != 3:
        raise B3RepeatabilityError("expected-plan group key must be a three-tuple")
    adapter_id, run_cell_id, operation = value
    adapter_id = _validate_nonempty_string(adapter_id, "adapter id")
    run_cell_id = _validate_nonempty_string(run_cell_id, "run cell id")
    operation = _validate_nonempty_string(operation, "operation")
    if operation not in {"context", "support"}:
        raise B3RepeatabilityError("expected-plan operation is invalid")
    return adapter_id, run_cell_id, operation


def _validate_signature(value: Any) -> ObservationSignature:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise B3RepeatabilityError("observation signature must be repetition/cache")
    repetition, cache_state = value
    if (
        not isinstance(repetition, int)
        or isinstance(repetition, bool)
        or repetition not in B3_EXPECTED_REPETITIONS
    ):
        raise B3RepeatabilityError("observation repetition is invalid")
    if cache_state not in B3_EXPECTED_CACHE_COUNTS:
        raise B3RepeatabilityError("observation cache state is invalid")
    return repetition, cache_state


def validate_expected_observation_plan(
    expected_plan: ExpectedObservationPlan,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(expected_plan, Mapping) or not expected_plan:
        return ["expected observation plan must be a nonempty mapping"]
    normalized_keys: set[GroupKey] = set()
    for raw_key, raw_signatures in expected_plan.items():
        try:
            key = _validate_group_key(raw_key)
        except B3RepeatabilityError as exc:
            errors.append(str(exc))
            continue
        if key in normalized_keys:
            errors.append(f"duplicate expected logical group: {key}")
        normalized_keys.add(key)
        try:
            signatures = tuple(_validate_signature(value) for value in raw_signatures)
        except (B3RepeatabilityError, TypeError) as exc:
            errors.append(f"{key}: {exc}")
            continue
        if len(signatures) != len(B3_EXPECTED_REPETITIONS):
            errors.append(f"{key}: expected four observation signatures")
        if len(set(signatures)) != len(signatures):
            errors.append(f"{key}: duplicate expected observation signature")
        if {repetition for repetition, _ in signatures} != set(
            B3_EXPECTED_REPETITIONS
        ):
            errors.append(f"{key}: repetition set drifted")
        if Counter(cache for _, cache in signatures) != Counter(
            B3_EXPECTED_CACHE_COUNTS
        ):
            errors.append(f"{key}: cache-state margins drifted")
    return sorted(set(errors))


def _normal_group_key(cell: Any) -> GroupKey:
    record = _field(cell, "record")
    return _validate_group_key(
        (
            _field(record, "adapter_id"),
            _field(record, "run_cell_id"),
            _field(record, "operation"),
        )
    )


def _normal_signature(cell: Any) -> ObservationSignature:
    record = _field(cell, "record")
    return _validate_signature(
        (_field(record, "adapter_repetition"), _field(record, "cache_state"))
    )


def _terminal_group_key(cell: Any) -> GroupKey:
    return _validate_group_key(
        (_field(cell, "adapter_id"), _field(cell, "run_cell_id"), "support")
    )


def _terminal_signature(cell: Any) -> ObservationSignature:
    return _validate_signature(
        (_field(cell, "adapter_repetition"), _field(cell, "cache_state"))
    )


def _diagnostic_hash(value: Any) -> str | None:
    found = _field(value, "semantic_hash", None)
    if found is None:
        return None
    return _validate_nonempty_string(found, "diagnostic semantic hash")


def _normalized_expected_plan(
    expected_plan: ExpectedObservationPlan,
) -> dict[GroupKey, tuple[ObservationSignature, ...]]:
    errors = validate_expected_observation_plan(expected_plan)
    if errors:
        raise B3RepeatabilityError("invalid expected observation plan: " + "; ".join(errors))
    return {
        _validate_group_key(key): tuple(
            sorted(_validate_signature(value) for value in signatures)
        )
        for key, signatures in expected_plan.items()
    }


def _collect_observations(
    normal_cells: Sequence[Any], terminal_cells: Sequence[Any]
) -> dict[GroupKey, list[_ObservedOutcome]]:
    groups: dict[GroupKey, list[_ObservedOutcome]] = defaultdict(list)
    for cell in normal_cells:
        projection = scorer_and_routing_projection(cell)
        groups[_normal_group_key(cell)].append(
            _ObservedOutcome(
                kind="normal",
                signature=_normal_signature(cell),
                projection=projection,
                projection_hash=_prefixed_digest("b3outcome_sem_", projection),
                diagnostic_hash=_diagnostic_hash(cell),
                value=cell,
            )
        )
    for cell in terminal_cells:
        projection = terminal_scorer_and_routing_projection(cell)
        groups[_terminal_group_key(cell)].append(
            _ObservedOutcome(
                kind="terminal",
                signature=_terminal_signature(cell),
                projection=projection,
                projection_hash=_prefixed_digest(
                    "b3terminal_outcome_sem_", projection
                ),
                diagnostic_hash=_diagnostic_hash(cell),
                value=cell,
            )
        )
    return groups


def _canonicalize_repeated_outcomes(
    normal_cells: Sequence[Any],
    terminal_cells: Sequence[Any],
    *,
    expected_plan: ExpectedObservationPlan,
) -> CanonicalizedRepeatedOutcomes:
    expected = _normalized_expected_plan(expected_plan)
    actual = _collect_observations(normal_cells, terminal_cells)
    failures: list[str] = []
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    if missing:
        failures.append(f"missing logical groups: {missing[:8]}")
    if unexpected:
        failures.append(f"unexpected logical groups: {unexpected[:8]}")

    normal_canonical: dict[GroupKey, Any] = {}
    terminal_canonical: dict[GroupKey, Any] = {}
    projection_hashes: dict[GroupKey, str] = {}
    diagnostic_drift: list[GroupKey] = []

    for key in sorted(set(expected) & set(actual)):
        observations = actual[key]
        actual_signatures = tuple(sorted(item.signature for item in observations))
        if actual_signatures != expected[key]:
            failures.append(
                f"{key}: observation signatures drifted "
                f"expected={expected[key]} actual={actual_signatures}"
            )
            continue
        if len({item.projection_hash for item in observations}) != 1:
            failures.append(f"{key}: score or routing semantics drifted")
            continue
        kinds = {item.kind for item in observations}
        if len(kinds) != 1:
            failures.append(f"{key}: normal/terminal outcome kind drifted")
            continue
        diagnostic_hashes = {
            item.diagnostic_hash
            for item in observations
            if item.diagnostic_hash is not None
        }
        if len(diagnostic_hashes) > 1:
            diagnostic_drift.append(key)
        chosen = min(observations, key=lambda item: item.signature)
        projection_hashes[key] = chosen.projection_hash
        if chosen.kind == "normal":
            normal_canonical[key] = chosen.value
        else:
            terminal_canonical[key] = chosen.value

    if failures:
        raise B3RepeatabilityError("; ".join(failures))
    return CanonicalizedRepeatedOutcomes(
        normal_cells=normal_canonical,
        terminal_cells=terminal_canonical,
        projection_hashes=projection_hashes,
        diagnostic_drift_groups=tuple(sorted(diagnostic_drift)),
    )


def canonicalize_for_scoring(
    normal_cells: Sequence[Any],
    terminal_cells: Sequence[Any] = (),
    *,
    expected_plan: ExpectedObservationPlan,
) -> CanonicalizedRepeatedOutcomes:
    """The only B3 scorer-side repeated-cell canonicalization entry point."""

    return _canonicalize_repeated_outcomes(
        normal_cells, terminal_cells, expected_plan=expected_plan
    )


def repeatability_gate(
    normal_cells: Sequence[Any],
    terminal_cells: Sequence[Any] = (),
    *,
    expected_plan: ExpectedObservationPlan,
) -> RepeatabilityGateResult:
    """Run the pre-score gate through the same core used by the scorer."""

    try:
        canonical = canonicalize_for_scoring(
            normal_cells, terminal_cells, expected_plan=expected_plan
        )
    except B3RepeatabilityError as exc:
        return RepeatabilityGateResult(
            passed=False,
            failures=(str(exc),),
            diagnostic_drift_group_count=0,
        )
    return RepeatabilityGateResult(
        passed=True,
        failures=(),
        diagnostic_drift_group_count=len(canonical.diagnostic_drift_groups),
    )


def repeatability_policy_payload() -> dict[str, Any]:
    return {
        "policy_version": B3_REPEATABILITY_POLICY_VERSION,
        "expected_repetitions": list(B3_EXPECTED_REPETITIONS),
        "expected_cache_counts": dict(B3_EXPECTED_CACHE_COUNTS),
        "complete_expected_group_set_required": True,
        "exact_repetition_and_cache_signatures_required": True,
        "gate_and_scorer_share_one_canonicalization_core": True,
        "quality_canonical_representative": "lowest_repetition_after_equivalence",
        "context_projection": [
            "accepted_scoreable_admission_class",
            "candidate_set_empty_or_nonempty",
            "pack_status",
            "evidence_line_union",
            "target_line_union",
            "target_cardinality_empty_single_or_multiple",
            "support_set_empty_or_nonempty",
        ],
        "support_projection": [
            "accepted_scoreable_admission_class",
            "relation_kind",
            "parent_target_id",
            "support_path_and_line_union",
        ],
        "terminal_projection": [
            "validated_terminal_admission_class",
            "terminal_reason",
            "context_score_and_routing_projection",
        ],
        "diagnostic_only_fields_excluded": [
            "candidate_native_score_and_order_when_nonempty",
            "evidence_and_support_duplicate_segmentation",
            "excerpt_channel_explanation_and_status_reason_text",
            "exact_pack_serialization_and_diagnostic_receipts",
        ],
        "diagnostic_hash_drift_recorded_but_not_score_gate_failure": True,
        "resource_measurements_are_not_canonicalized_or_required_equal": True,
        "separate_mandatory_gates": [
            "complete_execution_schedule",
            "record_validation_and_scoreability",
            "source_currentness_and_workspace_strictness",
            "same_arm_parent_lineage",
            "cross_arm_static_fairness",
            "provider_network_isolation",
        ],
    }


def repeatability_policy_digest() -> str:
    return _prefixed_digest("b3repeatpolicy_", repeatability_policy_payload())


def _span(path: str, start: int, end: int, **extra: Any) -> SimpleNamespace:
    return SimpleNamespace(path=path, start_line=start, end_line=end, **extra)


def _normal_cell(
    *,
    repetition: int,
    cache_state: str,
    operation: str = "context",
    candidates: Sequence[Any] = ({"path": "a.rs"},),
    evidence: Sequence[Any] = (_span("a.rs", 1, 3),),
    targets: Sequence[Any] = (_span("a.rs", 10, 12),),
    support: Sequence[Any] = (),
    pack_status: str = "ready",
    semantic_hash: str | None = None,
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
            cache_state=cache_state,
            status="accepted",
            result_status="ok",
        ),
        capture=SimpleNamespace(output=output),
        semantic_hash=semantic_hash,
    )


def _expected_plan(*, include_support: bool = True) -> dict[GroupKey, tuple[ObservationSignature, ...]]:
    signatures = ((1, "cold"), (2, "warm"), (3, "warm"), (4, "warm"))
    plan: dict[GroupKey, tuple[ObservationSignature, ...]] = {
        ("s0", "task", "context"): signatures
    }
    if include_support:
        plan[("s0", "task", "support")] = signatures
    return plan


def _equivalent_contexts() -> list[SimpleNamespace]:
    cells: list[SimpleNamespace] = []
    for repetition, cache_state in _expected_plan(include_support=False)[
        ("s0", "task", "context")
    ]:
        cells.append(
            _normal_cell(
                repetition=repetition,
                cache_state=cache_state,
                candidates=[
                    {"path": "elsewhere.rs", "native_score": repetition},
                    {"path": "a.rs", "native_score": 100 - repetition},
                ],
                evidence=(
                    [_span("a.rs", 1, 1), _span("a.rs", 2, 3)]
                    if repetition % 2
                    else [_span("a.rs", 1, 3, excerpt="diagnostic")]
                ),
                targets=[_span("a.rs", 10, 12, channel=f"c{repetition}")],
                semantic_hash=f"diagnostic-{repetition}",
            )
        )
    return cells


def _equivalent_supports() -> list[SimpleNamespace]:
    cells: list[SimpleNamespace] = []
    for repetition, cache_state in _expected_plan()[
        ("s0", "task", "support")
    ]:
        spans = (
            [
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
            ]
            if repetition % 2
            else [
                _span(
                    "b.rs",
                    20,
                    21,
                    relation_kind="import",
                    parent_target_id="parent",
                )
            ]
        )
        cells.append(
            _normal_cell(
                repetition=repetition,
                cache_state=cache_state,
                operation="support",
                candidates=[],
                evidence=[],
                targets=[],
                support=spans,
                semantic_hash=f"support-diagnostic-{repetition}",
            )
        )
    return cells


def run_self_test() -> dict[str, Any]:
    contexts = _equivalent_contexts()
    supports = _equivalent_supports()
    plan = _expected_plan()
    canonical = canonicalize_for_scoring(
        [*contexts, *supports], expected_plan=plan
    )
    gate = repeatability_gate([*contexts, *supports], expected_plan=plan)

    target_cardinality_drift = _equivalent_contexts()
    target_cardinality_drift[-1] = _normal_cell(
        repetition=4,
        cache_state="warm",
        candidates=[{"path": "a.rs"}],
        evidence=[_span("a.rs", 1, 3)],
        targets=[_span("a.rs", 10, 12), _span("a.rs", 10, 12)],
        semantic_hash="duplicate-targets",
    )
    target_gate = repeatability_gate(
        [*target_cardinality_drift, *supports], expected_plan=plan
    )
    missing_group_gate = repeatability_gate(contexts, expected_plan=plan)

    duplicate_repetition = [*contexts, *supports]
    duplicate_repetition[-1] = _normal_cell(
        repetition=3,
        cache_state="warm",
        operation="support",
        candidates=[],
        evidence=[],
        targets=[],
        support=[
            _span(
                "b.rs",
                20,
                21,
                relation_kind="import",
                parent_target_id="parent",
            )
        ],
    )
    duplicate_gate = repeatability_gate(
        duplicate_repetition, expected_plan=plan
    )

    checks = [
        not validate_expected_observation_plan(plan),
        canonical.logical_group_count == 2,
        len(canonical.normal_cells) == 2,
        len(canonical.terminal_cells) == 0,
        len(canonical.diagnostic_drift_groups) == 2,
        gate.passed,
        gate.diagnostic_drift_group_count == 2,
        not target_gate.passed,
        not missing_group_gate.passed,
        not duplicate_gate.passed,
        repeatability_policy_digest().startswith("b3repeatpolicy_"),
    ]
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
        "b25_reopened_or_reinterpreted": False,
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[bool] = []
    contexts = _equivalent_contexts()
    supports = _equivalent_supports()
    plan = _expected_plan()

    malformed = _normal_cell(
        repetition=1,
        cache_state="cold",
        evidence=[_span("a.rs", 0, 1)],
    )
    try:
        scorer_and_routing_projection(malformed)
    except B3RepeatabilityError:
        checks.append(True)
    else:
        checks.append(False)

    invalid_plan = dict(plan)
    invalid_plan[("s0", "task", "context")] = (
        (1, "cold"),
        (2, "warm"),
        (3, "warm"),
    )
    checks.append(bool(validate_expected_observation_plan(invalid_plan)))

    changed_evidence = _equivalent_contexts()
    changed_evidence[-1] = _normal_cell(
        repetition=4,
        cache_state="warm",
        evidence=[_span("a.rs", 1, 4)],
        semantic_hash="changed-evidence",
    )
    checks.append(
        not repeatability_gate(
            [*changed_evidence, *supports], expected_plan=plan
        ).passed
    )

    empty_candidates = _equivalent_contexts()
    empty_candidates[-1] = _normal_cell(
        repetition=4,
        cache_state="warm",
        candidates=[],
        semantic_hash="empty-candidates",
    )
    checks.append(
        not repeatability_gate(
            [*empty_candidates, *supports], expected_plan=plan
        ).passed
    )

    terminal_contexts = _equivalent_contexts()
    terminals = [
        SimpleNamespace(
            adapter_id="s0",
            run_cell_id="task",
            adapter_repetition=repetition,
            cache_state=cache_state,
            reason=("parent_unavailable" if repetition < 4 else "different_reason"),
            context_cell=terminal_contexts[repetition - 1],
            semantic_hash=f"terminal-{repetition}",
        )
        for repetition, cache_state in plan[("s0", "task", "support")]
    ]
    checks.append(
        not repeatability_gate(
            terminal_contexts,
            terminals,
            expected_plan=plan,
        ).passed
    )

    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def _print(value: Any) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Shared B3 gate/scorer repeatability canonicalization"
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
    "B3_REPEATABILITY_POLICY_VERSION",
    "B3_EXPECTED_REPETITIONS",
    "B3_EXPECTED_CACHE_COUNTS",
    "B3RepeatabilityError",
    "CanonicalizedRepeatedOutcomes",
    "RepeatabilityGateResult",
    "normalize_span_union",
    "normalize_support_union",
    "scorer_and_routing_projection",
    "scorer_and_routing_hash",
    "terminal_scorer_and_routing_projection",
    "terminal_scorer_and_routing_hash",
    "validate_expected_observation_plan",
    "canonicalize_for_scoring",
    "repeatability_gate",
    "repeatability_policy_payload",
    "repeatability_policy_digest",
    "run_self_test",
    "run_fault_test",
]
