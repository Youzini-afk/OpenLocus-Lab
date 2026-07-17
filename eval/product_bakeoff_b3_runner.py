#!/usr/bin/env python3
"""B3 schedule and repeatability integration around the frozen B2.1 engine.

The historical B2.1 modules are not edited.  During one single-process B3 run,
this module temporarily injects the preregistered Williams schedule and the B3
shared gate/scorer repeatability core, then restores every historical function.
The B2.1 source-currentness, scoreability, split-plot, lineage, fairness, and
provider-isolation gates remain active.

This is an engine layer only.  A future B3 launch envelope must validate the
private freeze/readiness/attempt boundary and provide a closed receipt
validator before calling ``run_full_matrix_engine``.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterator, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_corpus as b2c  # noqa: E402
import product_bakeoff_b2_protocol as b2p  # noqa: E402
import product_bakeoff_b21_runner as b21r  # noqa: E402
import product_bakeoff_b24_runner as b24r  # noqa: E402
import product_bakeoff_b3_protocol as b3p  # noqa: E402
import product_bakeoff_b3_repeatability as b3r  # noqa: E402


B3_RUNNER_VERSION = "product_bakeoff_b3_runner.v1"
B3_ENGINE_POLICY_VERSION = "product_bakeoff_b3_b21_engine_integration.v1"

_FROZEN_B2_BUILD_EXECUTION_SCHEDULE = b2p.build_execution_schedule
_FROZEN_B21_SCHEDULE_DIGEST = b21r.b21_execution_schedule_digest
_FROZEN_B21_LOGICAL_SEMANTIC_GATE = b21r._logical_semantic_gate


class B3RunError(RuntimeError):
    """Fail-closed B3 engine-integration error."""


def _task_field(task: Any, name: str) -> Any:
    if isinstance(task, Mapping):
        if name not in task:
            raise B3RunError(f"task lacks required field: {name}")
        return task[name]
    if not hasattr(task, name):
        raise B3RunError(f"task lacks required field: {name}")
    return getattr(task, name)


def build_expected_observation_plan(
    tasks: Sequence[Any],
    rows: Sequence[b3p.B3ScheduleRow] | None = None,
) -> dict[b3r.GroupKey, tuple[b3r.ObservationSignature, ...]]:
    """Bind the public slot schedule to private task slugs without publishing it."""

    task_rows = tuple(tasks)
    if len(task_rows) != b2p.B2_TASK_COUNT:
        raise B3RunError("B3 expected-plan task count is not 48")
    slot_ids = [_task_field(task, "slot_id") for task in task_rows]
    task_slugs = [_task_field(task, "task_slug") for task in task_rows]
    expected_slots = {slot.slot_id for slot in b2p.build_task_slots()}
    if set(slot_ids) != expected_slots or len(set(slot_ids)) != len(slot_ids):
        raise B3RunError("B3 task slots are not the exact public frame")
    if any(not isinstance(slug, str) or not slug for slug in task_slugs):
        raise B3RunError("B3 task slug must be nonempty")
    if len(set(task_slugs)) != len(task_slugs):
        raise B3RunError("B3 task slugs must be unique")
    task_by_slot = {slot_id: task for slot_id, task in zip(slot_ids, task_rows)}

    schedule = tuple(rows or b3p.build_execution_schedule())
    schedule_errors = b3p.validate_execution_schedule(schedule)
    if schedule_errors:
        raise B3RunError("B3 schedule is invalid: " + "; ".join(schedule_errors))
    groups: dict[b3r.GroupKey, list[b3r.ObservationSignature]] = defaultdict(list)
    for row in schedule:
        task = task_by_slot[row.slot_id]
        task_slug = _task_field(task, "task_slug")
        interaction_mode = _task_field(task, "interaction_mode")
        if interaction_mode not in {"one_shot", "two_step"}:
            raise B3RunError("B3 task interaction mode is invalid")
        for adapter_id in row.arm_order:
            groups[(adapter_id, task_slug, "context")].append(
                (row.repetition, row.cache_state)
            )
            if interaction_mode == "two_step":
                groups[(adapter_id, task_slug, "support")].append(
                    (row.repetition, row.cache_state)
                )
    plan = {key: tuple(sorted(values)) for key, values in sorted(groups.items())}
    errors = b3r.validate_expected_observation_plan(plan)
    if errors:
        raise B3RunError("B3 private expected observation plan invalid: " + "; ".join(errors))
    if len(plan) != 360 or sum(len(values) for values in plan.values()) != 1440:
        raise B3RunError("B3 private expected observation plan count drifted")
    return plan


def _b3_logical_semantic_gate(result: b21r.B21RunResult) -> tuple[bool, str]:
    """B2.1 gate hook backed by the shared B3 scorer canonicalization core."""

    try:
        expected_plan = build_expected_observation_plan(result.tasks)
        gate = b3r.repeatability_gate(
            result.cells,
            result.terminal_support_cells,
            expected_plan=expected_plan,
        )
    except (B3RunError, b3r.B3RepeatabilityError, TypeError, ValueError) as exc:
        return False, f"B3 repeatability gate error: {type(exc).__name__}"
    result.b3_diagnostic_drift_group_count = gate.diagnostic_drift_group_count
    if gate.passed:
        return True, ""
    return False, "; ".join(gate.failures[:8])


def _b3_schedule_factory(
    slots: Sequence[b2p.B2TaskSlot] | None = None,
) -> tuple[b3p.B3ScheduleRow, ...]:
    return b3p.build_execution_schedule(slots)


def _b3_schedule_digest() -> str:
    return b3p.execution_schedule_digest()


@contextlib.contextmanager
def b3_engine_override() -> Iterator[None]:
    """Temporarily bind the B2.1 loop to the frozen B3 schedule and gate."""

    if b2p.build_execution_schedule is not _FROZEN_B2_BUILD_EXECUTION_SCHEDULE:
        raise B3RunError("B2 execution schedule factory is already overridden")
    if b21r.b21_execution_schedule_digest is not _FROZEN_B21_SCHEDULE_DIGEST:
        raise B3RunError("B2.1 schedule digest function is already overridden")
    if b21r._logical_semantic_gate is not _FROZEN_B21_LOGICAL_SEMANTIC_GATE:
        raise B3RunError("B2.1 logical semantic gate is already overridden")
    b2p.build_execution_schedule = _b3_schedule_factory
    b21r.b21_execution_schedule_digest = _b3_schedule_digest
    b21r._logical_semantic_gate = _b3_logical_semantic_gate
    try:
        yield
    finally:
        b21r._logical_semantic_gate = _FROZEN_B21_LOGICAL_SEMANTIC_GATE
        b21r.b21_execution_schedule_digest = _FROZEN_B21_SCHEDULE_DIGEST
        b2p.build_execution_schedule = _FROZEN_B2_BUILD_EXECUTION_SCHEDULE


def _write_private_engine_summary(result: b21r.B21RunResult, runs_dir: Path) -> None:
    private_root = Path(runs_dir) / "private"
    summary = {
        "schema_version": "product_bakeoff_b3_private_engine_summary.v1",
        "runner_version": B3_RUNNER_VERSION,
        "engine_policy_version": B3_ENGINE_POLICY_VERSION,
        "schedule_digest": b3p.execution_schedule_digest(),
        "repeatability_policy_digest": b3r.repeatability_policy_digest(),
        "logical_record_count": result.logical_record_count,
        "pre_score_gates_passed": bool(result.gate_result and result.gate_result.passed),
        "pre_score_gate_failure_names": sorted(
            result.gate_result.failures if result.gate_result else {}
        ),
        "diagnostic_drift_group_count": int(
            getattr(result, "b3_diagnostic_drift_group_count", 0)
        ),
        "private_detail_public": False,
    }
    b2c.write_json(private_root / "b3_private_engine_summary.json", summary)


def run_full_matrix_engine(
    *,
    repo_lock_path: Path,
    task_manifest_path: Path,
    oracle_manifest_path: Path,
    holdout_binding_path: Path,
    excluded_repo_lock_path: Path,
    preflight_exclusion_path: Path,
    freeze_receipt_path: Path,
    expected_freeze_digest: str,
    runs_dir: Path,
    receipt_validator: Callable[..., Mapping[str, Any]],
    keep_worktrees: bool = False,
) -> b21r.B21RunResult:
    """Run the frozen B2.1 mechanics under B3 schedule/gate bindings.

    The caller owns private launch admission and the attempt-boundary receipt.
    This function deliberately accepts no launch authorization or readiness
    object so those layers cannot be confused with engine mechanics.
    """

    forbidden_modules = {
        "product_bakeoff_b2_author",
        "product_bakeoff_b2_oracle",
        "product_bakeoff_b2_scorer",
        "product_bakeoff_b21_scorer",
        "product_bakeoff_b24_scorer",
        "product_bakeoff_b25_scorer",
        "product_bakeoff_b3_scorer",
    }
    if forbidden_modules & set(sys.modules):
        raise B3RunError("B3 RUN phase began after author/oracle/scorer import")
    if not callable(receipt_validator):
        raise B3RunError("B3 engine requires a closed freeze receipt validator")
    with b24r._longrun_runtime_override(receipt_validator):
        with b3_engine_override():
            result = b21r.run_full_matrix(
                repo_lock_path=repo_lock_path,
                task_manifest_path=task_manifest_path,
                oracle_manifest_path=oracle_manifest_path,
                holdout_binding_path=holdout_binding_path,
                excluded_repo_lock_path=excluded_repo_lock_path,
                preflight_exclusion_path=preflight_exclusion_path,
                freeze_receipt_path=freeze_receipt_path,
                expected_freeze_digest=expected_freeze_digest,
                runs_dir=runs_dir,
                keep_worktrees=keep_worktrees,
            )
    _write_private_engine_summary(result, runs_dir)
    return result


def _synthetic_tasks() -> tuple[SimpleNamespace, ...]:
    return tuple(
        SimpleNamespace(
            slot_id=slot.slot_id,
            task_slug=f"synthetic_{slot.slot_id}",
            interaction_mode=slot.interaction_mode,
            language=slot.language,
            size_band=slot.size_band,
            role=slot.role,
        )
        for slot in b2p.build_task_slots()
    )


def _span(path: str, start: int, end: int, **extra: Any) -> SimpleNamespace:
    return SimpleNamespace(path=path, start_line=start, end_line=end, **extra)


def _synthetic_result(*, target_cardinality_drift: bool = False) -> b21r.B21RunResult:
    tasks = _synthetic_tasks()
    plan = build_expected_observation_plan(tasks)
    cells: list[SimpleNamespace] = []
    changed = False
    for (adapter_id, run_cell_id, operation), signatures in plan.items():
        for repetition, cache_state in signatures:
            if operation == "context":
                targets: list[Any] = [_span("a.rs", 10, 12)]
                if target_cardinality_drift and not changed and repetition == 4:
                    targets = [_span("a.rs", 10, 12), _span("a.rs", 10, 12)]
                    changed = True
                output = SimpleNamespace(
                    validated_candidates=[{"path": "a.rs", "rank": repetition}],
                    evidence=[
                        _span("a.rs", 1, 1),
                        _span("a.rs", 2, 3),
                    ],
                    pack=SimpleNamespace(
                        pack_status="ready",
                        targets=targets,
                        support=[],
                    ),
                )
            else:
                output = SimpleNamespace(
                    validated_candidates=[],
                    evidence=[],
                    pack=SimpleNamespace(
                        pack_status="ready",
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
                    ),
                )
            cells.append(
                SimpleNamespace(
                    record=SimpleNamespace(
                        adapter_id=adapter_id,
                        run_cell_id=run_cell_id,
                        operation=operation,
                        adapter_repetition=repetition,
                        cache_state=cache_state,
                        status="accepted",
                        result_status="ok",
                    ),
                    capture=SimpleNamespace(output=output),
                    semantic_hash=(
                        f"diagnostic-{adapter_id}-{run_cell_id}-{operation}-{repetition}"
                    ),
                )
            )
    return b21r.B21RunResult(cells=cells, tasks=tasks)


def run_self_test() -> dict[str, Any]:
    tasks = _synthetic_tasks()
    plan = build_expected_observation_plan(tasks)
    result = _synthetic_result()
    historical_ok, _ = _FROZEN_B21_LOGICAL_SEMANTIC_GATE(result)
    b3_ok, detail = _b3_logical_semantic_gate(result)
    checks = [
        len(plan) == 360,
        sum(len(values) for values in plan.values()) == 1440,
        not historical_ok,
        b3_ok,
        detail == "",
        getattr(result, "b3_diagnostic_drift_group_count", 0) == 360,
    ]

    before = (
        b2p.build_execution_schedule,
        b21r.b21_execution_schedule_digest,
        b21r._logical_semantic_gate,
    )
    with b3_engine_override():
        rows = b2p.build_execution_schedule()
        checks.extend(
            [
                isinstance(rows[0], b3p.B3ScheduleRow),
                b21r.b21_execution_schedule_digest()
                == b3p.execution_schedule_digest(),
                b21r._logical_semantic_gate(result)[0],
            ]
        )
    after = (
        b2p.build_execution_schedule,
        b21r.b21_execution_schedule_digest,
        b21r._logical_semantic_gate,
    )
    checks.append(before == after)

    def receipt_validator(raw: Any, **_: Any) -> Mapping[str, Any]:
        if not isinstance(raw, Mapping):
            raise B3RunError("synthetic receipt is not a mapping")
        return raw

    with b24r._longrun_runtime_override(receipt_validator):
        with b3_engine_override():
            checks.extend(
                [
                    b21r.validate_freeze_receipt is receipt_validator,
                    isinstance(b2p.build_execution_schedule()[0], b3p.B3ScheduleRow),
                ]
            )
    checks.append(before == (
        b2p.build_execution_schedule,
        b21r.b21_execution_schedule_digest,
        b21r._logical_semantic_gate,
    ))

    drift_result = _synthetic_result(target_cardinality_drift=True)
    drift_ok, _ = _b3_logical_semantic_gate(drift_result)
    checks.append(not drift_ok)
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
        "synthetic_logical_groups": len(plan),
        "synthetic_observations": sum(len(values) for values in plan.values()),
        "historical_modules_modified": False,
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[bool] = []
    tasks = list(_synthetic_tasks())
    try:
        build_expected_observation_plan(tasks[:-1])
    except B3RunError:
        checks.append(True)
    else:
        checks.append(False)

    duplicate = list(tasks)
    duplicate[-1] = SimpleNamespace(**vars(duplicate[0]))
    try:
        build_expected_observation_plan(duplicate)
    except B3RunError:
        checks.append(True)
    else:
        checks.append(False)

    try:
        with b3_engine_override():
            try:
                with b3_engine_override():
                    pass
            except B3RunError:
                checks.append(True)
            else:
                checks.append(False)
            raise RuntimeError("exercise restoration")
    except RuntimeError:
        pass
    checks.append(
        b2p.build_execution_schedule is _FROZEN_B2_BUILD_EXECUTION_SCHEDULE
        and b21r.b21_execution_schedule_digest is _FROZEN_B21_SCHEDULE_DIGEST
        and b21r._logical_semantic_gate is _FROZEN_B21_LOGICAL_SEMANTIC_GATE
    )

    drift_ok, _ = _b3_logical_semantic_gate(
        _synthetic_result(target_cardinality_drift=True)
    )
    checks.append(not drift_ok)
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def _print(value: Any) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main() -> int:
    parser = argparse.ArgumentParser(description="B3 B2.1-engine integration")
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
    "B3_RUNNER_VERSION",
    "B3_ENGINE_POLICY_VERSION",
    "B3RunError",
    "build_expected_observation_plan",
    "b3_engine_override",
    "run_full_matrix_engine",
    "run_self_test",
    "run_fault_test",
]
