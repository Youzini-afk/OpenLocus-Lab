#!/usr/bin/env python3
"""Closed B4 task-outcome matrix contract and synthetic runner validation.

This module does not execute repositories.  It defines the exact private,
identity-free task-outcome surface that the later Linux execution adapter must
produce after all raw source-currentness, oracle, lineage, scoreability, and
resource receipts pass.  Keeping this boundary separate lets the B4 scorer and
publication rules be exhaustively fault-tested before any private holdout or
treatment output exists.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_protocol as b2  # noqa: E402
import product_bakeoff_b4_protocol as b4p  # noqa: E402


B4_RUNNER_VERSION = "product_bakeoff_b4_runner.v1"
B4_TASK_OUTCOME_SCHEMA = "product_bakeoff_b4_private_task_outcome.v1"
B4_RUN_RESULT_SCHEMA = "product_bakeoff_b4_private_run_result.v1"

B4_TASK_OUTCOME_COUNT = b4p.B4_LOGICAL_TASK_COUNT * len(b4p.B4_ARMS)
B4_CONTEXT_GROUP_COUNT = B4_TASK_OUTCOME_COUNT
B4_SUPPORT_GROUP_COUNT = (
    b4p.B4_PANEL_COUNT
    * b4p.B4_REPOSITORIES_PER_PANEL
    * len(b4p.B4_ARMS)
)

B4_REQUIRED_PRE_SCORE_GATES = frozenset(
    {
        "complete_frozen_schedule",
        "source_currentness",
        "oracle_binding",
        "same_arm_support_lineage",
        "scoreability",
        "resource_receipts",
        "provider_network_isolation",
        "single_lifecycle_cardinality",
        "durable_operation_receipts",
    }
)


class B4RunError(ValueError):
    """Fail-closed B4 task-outcome matrix error."""


@dataclass(frozen=True)
class B4TaskOutcome:
    schema_version: str
    panel_index: int
    repository_index: int
    task_index: int
    task_role: str
    cache_state: str
    arm_id: str
    sequence_index: int
    arm_position: int
    task_success: bool
    harmful_evidence: bool
    status_or_target_success: bool
    context_f05_ppm: int
    query_us: int
    peak_rss_bytes: int


@dataclass(frozen=True)
class B4RunResult:
    schema_version: str
    outcomes: tuple[B4TaskOutcome, ...]
    logical_group_count: int
    logical_record_count: int
    index_build_count: int
    provider_network_call_count: int
    passed_pre_score_gates: frozenset[str]
    raw_operation_receipts_complete: bool
    private_detail_public: bool = False


def _exact_int(value: Any) -> bool:
    return type(value) is int


def _schedule_map() -> dict[tuple[int, int], b4p.B4ScheduleRow]:
    rows = b4p.build_schedule()
    errors = b4p.validate_schedule(rows)
    if errors:
        raise B4RunError("B4 public schedule invalid: " + "; ".join(errors))
    return {(row.panel_index, row.task_index): row for row in rows}


def expected_outcome_keys() -> frozenset[tuple[int, int, str]]:
    return frozenset(
        (panel_index, task_index, arm_id)
        for panel_index in range(1, b4p.B4_PANEL_COUNT + 1)
        for task_index in range(1, b4p.B4_TASKS_PER_PANEL + 1)
        for arm_id in b4p.B4_ARMS
    )


def validate_task_outcome(
    outcome: Any,
    *,
    schedule: Mapping[tuple[int, int], b4p.B4ScheduleRow] | None = None,
) -> list[str]:
    if not isinstance(outcome, B4TaskOutcome):
        return ["B4 task outcome has wrong type"]
    errors: list[str] = []
    if outcome.schema_version != B4_TASK_OUTCOME_SCHEMA:
        errors.append("B4 task outcome schema drifted")
    for field_name, lower, upper in (
        ("panel_index", 1, b4p.B4_PANEL_COUNT),
        ("repository_index", 1, b4p.B4_REPOSITORIES_PER_PANEL),
        ("task_index", 1, b4p.B4_TASKS_PER_PANEL),
    ):
        value = getattr(outcome, field_name)
        if not _exact_int(value) or not lower <= value <= upper:
            errors.append(f"B4 task outcome {field_name} invalid")
    if outcome.task_role not in b2.B2_TASK_ROLES:
        errors.append("B4 task outcome role invalid")
    if outcome.cache_state not in {"cold", "warm"}:
        errors.append("B4 task outcome cache state invalid")
    if outcome.arm_id not in b4p.B4_ARMS:
        errors.append("B4 task outcome arm invalid")
    if not _exact_int(outcome.sequence_index) or outcome.sequence_index not in range(
        len(b4p.B4_ARM_SEQUENCES)
    ):
        errors.append("B4 task outcome sequence index invalid")
    if not _exact_int(outcome.arm_position) or outcome.arm_position not in range(
        1, len(b4p.B4_ARMS) + 1
    ):
        errors.append("B4 task outcome arm position invalid")
    for field_name in (
        "task_success",
        "harmful_evidence",
        "status_or_target_success",
    ):
        if type(getattr(outcome, field_name)) is not bool:
            errors.append(f"B4 task outcome {field_name} must be bool")
    if not _exact_int(outcome.context_f05_ppm) or not (
        0 <= outcome.context_f05_ppm <= 1_000_000
    ):
        errors.append("B4 task outcome context F0.5 invalid")
    if not _exact_int(outcome.query_us) or outcome.query_us <= 0:
        errors.append("B4 task outcome query time invalid")
    if not _exact_int(outcome.peak_rss_bytes) or outcome.peak_rss_bytes <= 0:
        errors.append("B4 task outcome peak RSS invalid")

    if not errors:
        row = (schedule or _schedule_map()).get(
            (outcome.panel_index, outcome.task_index)
        )
        if row is None:
            errors.append("B4 task outcome lacks schedule row")
        else:
            if outcome.repository_index != row.repository_index:
                errors.append("B4 task outcome repository index drifted")
            if outcome.task_role != row.task_role:
                errors.append("B4 task outcome role drifted")
            if outcome.cache_state != row.cache_state:
                errors.append("B4 task outcome cache state drifted")
            if outcome.arm_id not in row.arm_order:
                errors.append("B4 task outcome arm missing from schedule order")
            else:
                if outcome.sequence_index != row.sequence_index:
                    errors.append("B4 task outcome sequence index drifted")
                if outcome.arm_position != row.arm_order.index(outcome.arm_id) + 1:
                    errors.append("B4 task outcome arm position drifted")
    return sorted(set(errors))


def validate_run_result(result: Any) -> list[str]:
    if not isinstance(result, B4RunResult):
        return ["B4 run result has wrong type"]
    errors: list[str] = []
    if result.schema_version != B4_RUN_RESULT_SCHEMA:
        errors.append("B4 run result schema drifted")
    if not isinstance(result.outcomes, tuple):
        errors.append("B4 run outcomes must be a tuple")
        return errors
    if len(result.outcomes) != B4_TASK_OUTCOME_COUNT:
        errors.append("B4 task outcome count drifted")
    schedule = _schedule_map()
    observed_keys: list[tuple[int, int, str]] = []
    for outcome in result.outcomes:
        errors.extend(validate_task_outcome(outcome, schedule=schedule))
        if isinstance(outcome, B4TaskOutcome):
            observed_keys.append(
                (outcome.panel_index, outcome.task_index, outcome.arm_id)
            )
    if len(set(observed_keys)) != len(observed_keys):
        errors.append("B4 run result contains duplicate outcome keys")
    if frozenset(observed_keys) != expected_outcome_keys():
        errors.append("B4 run result outcome key set is incomplete")
    if result.logical_group_count != b4p.B4_LOGICAL_GROUP_COUNT:
        errors.append("B4 logical group count drifted")
    if result.logical_record_count != b4p.B4_LOGICAL_RECORD_COUNT:
        errors.append("B4 logical record count drifted")
    if result.index_build_count != b4p.B4_INDEX_BUILD_COUNT:
        errors.append("B4 index build count drifted")
    if result.provider_network_call_count != 0:
        errors.append("B4 provider/network isolation failed")
    if result.passed_pre_score_gates != B4_REQUIRED_PRE_SCORE_GATES:
        errors.append("B4 pre-score gate set incomplete or contaminated")
    if result.raw_operation_receipts_complete is not True:
        errors.append("B4 raw operation receipts are incomplete")
    if result.private_detail_public is not False:
        errors.append("B4 private detail publication flag invalid")

    if not errors:
        for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
            for arm_id in b4p.B4_ARMS:
                subset = [
                    row
                    for row in result.outcomes
                    if row.panel_index == panel_index and row.arm_id == arm_id
                ]
                if Counter(row.cache_state for row in subset) != Counter(
                    {"cold": 12, "warm": 36}
                ):
                    errors.append("B4 panel/arm cache cardinality drifted")
                if Counter(row.task_role for row in subset) != Counter(
                    {role: 12 for role in b2.B2_TASK_ROLES}
                ):
                    errors.append("B4 panel/arm task-role cardinality drifted")
    return sorted(set(errors))


def require_valid_run_result(result: Any) -> B4RunResult:
    errors = validate_run_result(result)
    if errors:
        raise B4RunError("invalid B4 run result: " + "; ".join(errors[:8]))
    return result


def _arm_quality(
    arm_id: str,
    *,
    repository_index: int,
    role_index: int,
    tie: bool,
) -> tuple[bool, bool, bool, int]:
    baseline_success = role_index in {0, 2}
    if tie or arm_id == b4p.B4_BASELINE_ARM:
        success = baseline_success
        context = 500_000 + role_index * 10_000
    elif arm_id == b2.S1_ADAPTER_ID:
        success = baseline_success or (
            role_index == 1 and repository_index % 3 == 0
        )
        context = 530_000 + role_index * 10_000
    elif arm_id == b2.S4_ADAPTER_ID:
        success = baseline_success or (
            role_index == 1 and repository_index % 2 == 0
        )
        context = 560_000 + role_index * 10_000
    else:  # pragma: no cover - closed arm set checked by caller
        raise B4RunError("unknown synthetic B4 arm")
    return success, False, success, context


def synthetic_run_result(
    *,
    tie: bool = False,
    s1_resource_regression: bool = False,
    s1_harm_regression: bool = False,
) -> B4RunResult:
    outcomes: list[B4TaskOutcome] = []
    for row in b4p.build_schedule():
        role_index = b2.B2_TASK_ROLES.index(row.task_role)
        base_query_us = 1_000 + row.repository_index * 3 + role_index
        base_rss = 100_000_000 + row.repository_index * 10_000
        for arm_id in row.arm_order:
            success, harmful, status_success, context = _arm_quality(
                arm_id,
                repository_index=row.repository_index,
                role_index=role_index,
                tie=tie,
            )
            if tie or arm_id == b4p.B4_BASELINE_ARM:
                query_us = base_query_us
                peak_rss = base_rss
            elif arm_id == b2.S1_ADAPTER_ID:
                query_us = base_query_us * (15 if s1_resource_regression else 11) // 10
                peak_rss = base_rss * (130 if s1_resource_regression else 105) // 100
                if s1_harm_regression and role_index == 0:
                    harmful = True
            else:
                query_us = base_query_us * 19 // 10
                peak_rss = base_rss * 120 // 100
            outcomes.append(
                B4TaskOutcome(
                    schema_version=B4_TASK_OUTCOME_SCHEMA,
                    panel_index=row.panel_index,
                    repository_index=row.repository_index,
                    task_index=row.task_index,
                    task_role=row.task_role,
                    cache_state=row.cache_state,
                    arm_id=arm_id,
                    sequence_index=row.sequence_index,
                    arm_position=row.arm_order.index(arm_id) + 1,
                    task_success=success,
                    harmful_evidence=harmful,
                    status_or_target_success=status_success,
                    context_f05_ppm=context,
                    query_us=query_us,
                    peak_rss_bytes=peak_rss,
                )
            )
    return B4RunResult(
        schema_version=B4_RUN_RESULT_SCHEMA,
        outcomes=tuple(outcomes),
        logical_group_count=b4p.B4_LOGICAL_GROUP_COUNT,
        logical_record_count=b4p.B4_LOGICAL_RECORD_COUNT,
        index_build_count=b4p.B4_INDEX_BUILD_COUNT,
        provider_network_call_count=0,
        passed_pre_score_gates=B4_REQUIRED_PRE_SCORE_GATES,
        raw_operation_receipts_complete=True,
    )


def run_self_test() -> dict[str, Any]:
    result = synthetic_run_result()
    tie = synthetic_run_result(tie=True)
    checks = [
        not validate_run_result(result),
        not validate_run_result(tie),
        len(result.outcomes) == 1_728,
        result.logical_group_count == 2_160,
        B4_CONTEXT_GROUP_COUNT + B4_SUPPORT_GROUP_COUNT == 2_160,
        result.index_build_count == 432,
        len(expected_outcome_keys()) == 1_728,
        all(row.schema_version == B4_TASK_OUTCOME_SCHEMA for row in result.outcomes),
        all(not hasattr(row, "repository_slug") for row in result.outcomes),
        all(not hasattr(row, "task_slug") for row in result.outcomes),
    ]
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
        "synthetic_task_outcomes": len(result.outcomes),
        "logical_groups": result.logical_group_count,
    }


def run_fault_test() -> dict[str, Any]:
    base = synthetic_run_result()
    checks: list[bool] = []

    def rejects(value: B4RunResult) -> None:
        checks.append(bool(validate_run_result(value)))

    rejects(replace(base, outcomes=base.outcomes[:-1]))
    rejects(replace(base, outcomes=base.outcomes[:-1] + (base.outcomes[0],)))
    rejects(replace(base, index_build_count=431))
    rejects(replace(base, provider_network_call_count=1))
    rejects(replace(base, passed_pre_score_gates=frozenset()))
    rejects(replace(base, raw_operation_receipts_complete=False))

    wrong_role = replace(base.outcomes[0], task_role="invalid")
    rejects(replace(base, outcomes=(wrong_role,) + base.outcomes[1:]))
    wrong_cache = replace(
        base.outcomes[0],
        cache_state="warm" if base.outcomes[0].cache_state == "cold" else "cold",
    )
    rejects(replace(base, outcomes=(wrong_cache,) + base.outcomes[1:]))
    bool_as_int = replace(base.outcomes[0], task_success=1)  # type: ignore[arg-type]
    rejects(replace(base, outcomes=(bool_as_int,) + base.outcomes[1:]))
    wrong_position = replace(
        base.outcomes[0], arm_position=1 if base.outcomes[0].arm_position != 1 else 2
    )
    rejects(replace(base, outcomes=(wrong_position,) + base.outcomes[1:]))

    copied = copy.deepcopy(base)
    checks.append(not validate_run_result(copied))
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def _print(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="B4 closed task-outcome matrix")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    args = parser.parse_args(argv)
    report = run_self_test() if args.self_test else run_fault_test()
    _print(report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B4_RUNNER_VERSION",
    "B4_TASK_OUTCOME_SCHEMA",
    "B4_RUN_RESULT_SCHEMA",
    "B4_REQUIRED_PRE_SCORE_GATES",
    "B4TaskOutcome",
    "B4RunResult",
    "B4RunError",
    "expected_outcome_keys",
    "validate_task_outcome",
    "validate_run_result",
    "require_valid_run_result",
    "synthetic_run_result",
    "run_self_test",
    "run_fault_test",
]
