#!/usr/bin/env python3
"""B4 raw execution adapter over the frozen B2.1/B2.4 mechanics.

Each B4 panel has the same public 12-repository/48-task frame as B2, but it
uses three arms, one repository/arm lifecycle, and no technical repetitions.
The historical runners are not edited.  This module applies a narrowly scoped
override for one child process, restores every historical binding on exit, and
converts the validated raw result into the identity-free B4 task-outcome
surface.  A parent controller should run one panel per fresh subprocess so the
RUN-phase scorer import fence remains real and memory stays bounded.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import math
import os
import sys
import tempfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterator, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import product_bakeoff_b2_protocol as b2p  # noqa: E402
import product_bakeoff_b2_runner as b2r  # noqa: E402
import product_bakeoff_b21_runner as b21r  # noqa: E402
import product_bakeoff_b24_runner as b24r  # noqa: E402
import product_bakeoff_b4_protocol as b4p  # noqa: E402
import product_bakeoff_b4_runner as b4r  # noqa: E402


B4_EXECUTION_ADAPTER_VERSION = "product_bakeoff_b4_execution_adapter.v1"
B4_PANEL_OUTCOME_SCHEMA = "product_bakeoff_b4_private_panel_outcomes.v1"
B4_PANEL_ENVELOPE_SCHEMA = "product_bakeoff_b4_private_panel_launch.v1"
B4_PANEL_REPETITIONS = (1,)
B4_PANEL_LOGICAL_RECORD_COUNT = b4p.B4_GROUPS_PER_ARM_PANEL * len(b4p.B4_ARMS)
B4_PANEL_RECORDS_PER_ARM = b4p.B4_GROUPS_PER_ARM_PANEL
B4_PANEL_INDEX_BUILD_COUNT = b4p.B4_REPOSITORIES_PER_PANEL * len(b4p.B4_ARMS)
B4_PANEL_TASK_OUTCOME_COUNT = b4p.B4_TASKS_PER_PANEL * len(b4p.B4_ARMS)

_FROZEN_B2P_BINDINGS = {
    "B2_ADAPTER_IDS": b2p.B2_ADAPTER_IDS,
    "B2_ADAPTER_COUNT": b2p.B2_ADAPTER_COUNT,
    "B2_REPETITIONS": b2p.B2_REPETITIONS,
    "B2_TOTAL_RECORDS": b2p.B2_TOTAL_RECORDS,
    "B2_RECORDS_PER_ARM": b2p.B2_RECORDS_PER_ARM,
    "B2_INDEX_BUILD_COUNT": b2p.B2_INDEX_BUILD_COUNT,
    "build_execution_schedule": b2p.build_execution_schedule,
    "validate_execution_schedule": b2p.validate_execution_schedule,
}
_FROZEN_B2R_BINDINGS = {
    "B2_ADAPTER_IDS": b2r.B2_ADAPTER_IDS,
    "B2_REPETITIONS": b2r.B2_REPETITIONS,
    "B2_TOTAL_RECORDS": b2r.B2_TOTAL_RECORDS,
    "B2_INDEX_BUILD_COUNT": b2r.B2_INDEX_BUILD_COUNT,
}
_FROZEN_B21_SCHEDULE_DIGEST = b21r.b21_execution_schedule_digest


class B4ExecutionAdapterError(RuntimeError):
    """Fail-closed B4 raw-adapter error without private identifiers."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _digest(prefix: str, value: Mapping[str, Any], key: str) -> str:
    payload = copy.deepcopy(dict(value))
    payload.pop(key, None)
    return prefix + hashlib.sha256(_canonical(payload)).hexdigest()


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise B4ExecutionAdapterError("B4 private JSON contains a duplicate key")
        value[key] = item
    return value


def _reject_nonfinite_constant(_: str) -> Any:
    raise B4ExecutionAdapterError("B4 private JSON contains a non-finite number")


def _load_private_json(path: Path) -> Any:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise B4ExecutionAdapterError("B4 private JSON input is missing or unsafe")
    try:
        return json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_constant,
        )
    except B4ExecutionAdapterError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise B4ExecutionAdapterError("B4 private JSON input is malformed") from exc


def _exact_int(value: Any) -> bool:
    return type(value) is int


def _require_panel_index(panel_index: Any) -> int:
    if not _exact_int(panel_index) or not 1 <= panel_index <= b4p.B4_PANEL_COUNT:
        raise B4ExecutionAdapterError("B4 panel index is outside the frozen design")
    return panel_index


def build_panel_schedule(
    panel_index: int,
    slots: Sequence[b2p.B2TaskSlot] | None = None,
) -> tuple[b2p.B2ScheduleRow, ...]:
    """Project one frozen B4 panel onto the B2.1 loop's row interface."""

    panel_index = _require_panel_index(panel_index)
    task_slots = tuple(slots or b2p.build_task_slots())
    if len(task_slots) != b4p.B4_TASKS_PER_PANEL:
        raise B4ExecutionAdapterError("B4 panel task-slot count drifted")
    if len({slot.slot_id for slot in task_slots}) != len(task_slots):
        raise B4ExecutionAdapterError("B4 panel task slots are not unique")
    public_rows = {
        row.task_index: row
        for row in b4p.build_schedule()
        if row.panel_index == panel_index
    }
    if len(public_rows) != b4p.B4_TASKS_PER_PANEL:
        raise B4ExecutionAdapterError("B4 public panel schedule is incomplete")

    rows: list[b2p.B2ScheduleRow] = []
    for repository_index in range(1, b4p.B4_REPOSITORIES_PER_PANEL + 1):
        start = (repository_index - 1) * b4p.B4_TASKS_PER_REPOSITORY
        pairs = [
            (task_slots[start + offset], public_rows[start + offset + 1])
            for offset in range(b4p.B4_TASKS_PER_REPOSITORY)
        ]
        pairs.sort(key=lambda pair: (pair[1].cache_state != "cold", pair[1].task_index))
        for task_position, (slot, public) in enumerate(pairs, start=1):
            if slot.role != public.task_role:
                raise B4ExecutionAdapterError("B4 task-role projection drifted")
            rows.append(
                b2p.B2ScheduleRow(
                    slot_id=slot.slot_id,
                    repo_slot=slot.repo_slot,
                    repetition=1,
                    cache_state=public.cache_state,
                    task_position=task_position,
                    arm_order=public.arm_order,
                )
            )
    return tuple(rows)


def validate_panel_schedule(
    rows: Sequence[b2p.B2ScheduleRow],
    slots: Sequence[b2p.B2TaskSlot] | None = None,
    *,
    panel_index: int,
) -> list[str]:
    """Validate only properties appropriate to the no-repeat B4 panel."""

    errors: list[str] = []
    try:
        panel_index = _require_panel_index(panel_index)
    except B4ExecutionAdapterError:
        return ["B4 panel index invalid"]
    task_slots = tuple(slots or b2p.build_task_slots())
    if len(task_slots) != b4p.B4_TASKS_PER_PANEL:
        return ["B4 panel task-slot count drifted"]
    slot_by_id = {slot.slot_id: slot for slot in task_slots}
    slot_index = {slot.slot_id: index + 1 for index, slot in enumerate(task_slots)}
    public = {
        row.task_index: row
        for row in b4p.build_schedule()
        if row.panel_index == panel_index
    }
    if b4p.validate_schedule(b4p.build_schedule()):
        errors.append("B4 public schedule is invalid")
    if len(rows) != b4p.B4_TASKS_PER_PANEL:
        errors.append("B4 panel schedule row count drifted")
    if len({row.slot_id for row in rows}) != len(rows):
        errors.append("B4 panel schedule has duplicate slots")
    if set(row.slot_id for row in rows) != set(slot_by_id):
        errors.append("B4 panel schedule slot set is incomplete")

    record_count = 0
    position_counts: Counter[tuple[str, int]] = Counter()
    for row in rows:
        slot = slot_by_id.get(row.slot_id)
        if slot is None:
            errors.append("B4 panel schedule contains an unknown slot")
            continue
        public_row = public.get(slot_index[row.slot_id])
        if public_row is None:
            errors.append("B4 panel schedule lacks a public binding")
            continue
        if row.repo_slot != slot.repo_slot:
            errors.append("B4 panel repository-slot projection drifted")
        if row.repetition != 1:
            errors.append("B4 panel introduced a technical repetition")
        if row.cache_state != public_row.cache_state:
            errors.append("B4 panel cache-state projection drifted")
        if tuple(row.arm_order) != tuple(public_row.arm_order):
            errors.append("B4 panel arm-order projection drifted")
        if set(row.arm_order) != set(b4p.B4_ARMS) or len(row.arm_order) != len(
            b4p.B4_ARMS
        ):
            errors.append("B4 panel arm order is not an exact permutation")
        if row.cache_state == "cold" and row.task_position != 1:
            errors.append("B4 panel cold task is not first in lifecycle")
        if row.cache_state == "warm" and row.task_position == 1:
            errors.append("B4 panel first lifecycle task is not cold")
        for position, arm_id in enumerate(row.arm_order, start=1):
            position_counts[(arm_id, position)] += 1
        record_count += len(b4p.B4_ARMS) * (
            2 if slot.interaction_mode == "two_step" else 1
        )

    grouped: dict[str, list[b2p.B2ScheduleRow]] = {}
    for row in rows:
        grouped.setdefault(row.repo_slot, []).append(row)
    if len(grouped) != b4p.B4_REPOSITORIES_PER_PANEL:
        errors.append("B4 panel repository lifecycle count drifted")
    for group in grouped.values():
        if len(group) != b4p.B4_TASKS_PER_REPOSITORY:
            errors.append("B4 panel repository lifecycle is incomplete")
            continue
        if [row.task_position for row in group] != [1, 2, 3, 4]:
            errors.append("B4 panel repository lifecycle order drifted")
        if Counter(row.cache_state for row in group) != Counter({"cold": 1, "warm": 3}):
            errors.append("B4 panel repository cache lifecycle drifted")
    expected_position = b4p.B4_TASKS_PER_PANEL // len(b4p.B4_ARMS)
    for arm_id in b4p.B4_ARMS:
        for position in range(1, len(b4p.B4_ARMS) + 1):
            if position_counts[(arm_id, position)] != expected_position:
                errors.append("B4 panel arm-position balance drifted")
    if record_count != B4_PANEL_LOGICAL_RECORD_COUNT:
        errors.append("B4 panel logical record count drifted")
    return sorted(set(errors))


def panel_schedule_digest(panel_index: int) -> str:
    panel_index = _require_panel_index(panel_index)
    rows = build_panel_schedule(panel_index)
    return "b4panelsched_" + hashlib.sha256(
        _canonical(
            {
                "panel_index": panel_index,
                "rows": [row.to_dict() for row in rows],
            }
        )
    ).hexdigest()


def _assert_unmodified_historical_bindings() -> None:
    for name, value in _FROZEN_B2P_BINDINGS.items():
        if getattr(b2p, name) is not value:
            raise B4ExecutionAdapterError(f"historical B2 protocol binding already changed: {name}")
    for name, value in _FROZEN_B2R_BINDINGS.items():
        if getattr(b2r, name) is not value:
            raise B4ExecutionAdapterError(f"historical B2 runner binding already changed: {name}")
    if b21r.b21_execution_schedule_digest is not _FROZEN_B21_SCHEDULE_DIGEST:
        raise B4ExecutionAdapterError("historical B2.1 schedule digest already changed")


@contextlib.contextmanager
def b4_panel_engine_override(panel_index: int) -> Iterator[None]:
    """Bind one B2.1 child run to one B4 panel and restore on every exit."""

    panel_index = _require_panel_index(panel_index)
    _assert_unmodified_historical_bindings()
    if b21r.B2_ADAPTERS is not b24r.B24_ADAPTERS:
        raise B4ExecutionAdapterError("B4 panel override requires the B2.4 runtime envelope")
    b24_adapters = tuple(
        row for row in b24r.B24_ADAPTERS if row[0] in set(b4p.B4_ARMS)
    )
    if tuple(row[0] for row in b24_adapters) != b4p.B4_ARMS:
        raise B4ExecutionAdapterError("B4 arm registry does not match the frozen arm order")

    def schedule_factory(
        slots: Sequence[b2p.B2TaskSlot] | None = None,
    ) -> tuple[b2p.B2ScheduleRow, ...]:
        return build_panel_schedule(panel_index, slots)

    def schedule_validator(
        rows: Sequence[b2p.B2ScheduleRow],
        slots: Sequence[b2p.B2TaskSlot] | None = None,
    ) -> list[str]:
        return validate_panel_schedule(rows, slots, panel_index=panel_index)

    def schedule_digest() -> str:
        return panel_schedule_digest(panel_index)

    replacements = {
        "B2_ADAPTER_IDS": b4p.B4_ARMS,
        "B2_ADAPTER_COUNT": len(b4p.B4_ARMS),
        "B2_REPETITIONS": B4_PANEL_REPETITIONS,
        "B2_TOTAL_RECORDS": B4_PANEL_LOGICAL_RECORD_COUNT,
        "B2_RECORDS_PER_ARM": B4_PANEL_RECORDS_PER_ARM,
        "B2_INDEX_BUILD_COUNT": B4_PANEL_INDEX_BUILD_COUNT,
        "build_execution_schedule": schedule_factory,
        "validate_execution_schedule": schedule_validator,
    }
    runner_replacements = {
        "B2_ADAPTER_IDS": b4p.B4_ARMS,
        "B2_REPETITIONS": B4_PANEL_REPETITIONS,
        "B2_TOTAL_RECORDS": B4_PANEL_LOGICAL_RECORD_COUNT,
        "B2_INDEX_BUILD_COUNT": B4_PANEL_INDEX_BUILD_COUNT,
    }
    for name, value in replacements.items():
        setattr(b2p, name, value)
    for name, value in runner_replacements.items():
        setattr(b2r, name, value)
    b21r.b21_execution_schedule_digest = schedule_digest
    b21r.B2_ADAPTERS = b24_adapters
    try:
        yield
    finally:
        b21r.B2_ADAPTERS = b24r.B24_ADAPTERS
        b21r.b21_execution_schedule_digest = _FROZEN_B21_SCHEDULE_DIGEST
        for name, value in _FROZEN_B2R_BINDINGS.items():
            setattr(b2r, name, value)
        for name, value in _FROZEN_B2P_BINDINGS.items():
            setattr(b2p, name, value)


def run_panel_engine(
    *,
    panel_index: int,
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
    """Execute exactly one panel under B2.4 timeouts and B2.1 gates."""

    panel_index = _require_panel_index(panel_index)
    forbidden = {
        "product_bakeoff_b2_author",
        "product_bakeoff_b2_oracle",
        "product_bakeoff_b2_scorer",
        "product_bakeoff_b21_scorer",
        "product_bakeoff_b24_scorer",
        "product_bakeoff_b25_scorer",
        "product_bakeoff_b3_scorer",
        "product_bakeoff_b4_scorer",
    }
    if forbidden & set(sys.modules):
        raise B4ExecutionAdapterError("B4 RUN phase began after an author/oracle/scorer import")
    if not callable(receipt_validator):
        raise B4ExecutionAdapterError("B4 panel requires a closed freeze validator")
    with b24r._longrun_runtime_override(receipt_validator):
        with b4_panel_engine_override(panel_index):
            result = b21r.run_full_matrix(
                repo_lock_path=Path(repo_lock_path),
                task_manifest_path=Path(task_manifest_path),
                oracle_manifest_path=Path(oracle_manifest_path),
                holdout_binding_path=Path(holdout_binding_path),
                excluded_repo_lock_path=Path(excluded_repo_lock_path),
                preflight_exclusion_path=Path(preflight_exclusion_path),
                freeze_receipt_path=Path(freeze_receipt_path),
                expected_freeze_digest=expected_freeze_digest,
                runs_dir=Path(runs_dir),
                keep_worktrees=keep_worktrees,
            )
    return result


def _raw_panel_errors(result: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(result, b21r.B21RunResult):
        return ["B4 raw panel result has wrong type"]
    if result.gate_result is None or not result.gate_result.passed:
        errors.append("B4 raw panel pre-score gates did not all pass")
    if result.logical_record_count != B4_PANEL_LOGICAL_RECORD_COUNT:
        errors.append("B4 raw panel logical record count drifted")
    if result.provider_network_call_count != 0:
        errors.append("B4 raw panel provider/network isolation failed")
    if len(result.tasks) != b4p.B4_TASKS_PER_PANEL:
        errors.append("B4 raw panel task count drifted")
    expected_slots = {slot.slot_id for slot in b2p.build_task_slots()}
    if {getattr(task, "slot_id", None) for task in result.tasks} != expected_slots:
        errors.append("B4 raw panel task-slot set drifted")
    normal_count = len(result.cells)
    terminal_count = len(result.terminal_support_cells)
    if normal_count + terminal_count != B4_PANEL_LOGICAL_RECORD_COUNT:
        errors.append("B4 raw panel operation receipts are incomplete")
    if len(result.parent_receipts) != normal_count:
        errors.append("B4 raw panel normal operation receipts are incomplete")
    if len(result.terminal_parent_receipts) != terminal_count:
        errors.append("B4 raw panel terminal operation receipts are incomplete")
    index_builds = sum(
        receipt.get("lifecycle_command_kind") == "rust_index_build"
        for receipt in result.parent_receipts
        if isinstance(receipt, Mapping)
    )
    if index_builds != B4_PANEL_INDEX_BUILD_COUNT:
        errors.append("B4 raw panel index-build count drifted")
    arm_ids = {
        getattr(getattr(cell, "record", None), "adapter_id", None)
        for cell in result.cells
    } | {getattr(cell, "adapter_id", None) for cell in result.terminal_support_cells}
    if arm_ids != set(b4p.B4_ARMS):
        errors.append("B4 raw panel arm set drifted")
    repetitions = {
        getattr(getattr(cell, "record", None), "adapter_repetition", None)
        for cell in result.cells
    } | {
        getattr(cell, "adapter_repetition", None)
        for cell in result.terminal_support_cells
    }
    if repetitions != {1}:
        errors.append("B4 raw panel contains a technical repetition")
    if result.repo_lock is None or result.task_manifest is None or result.freeze_receipt is None:
        errors.append("B4 raw panel lacks frozen input bindings")
    return sorted(set(errors))


def _resource_us(cell: Any) -> int:
    sample = getattr(getattr(cell, "record", None), "resource_sample", None)
    if sample is None:
        raise B4ExecutionAdapterError("B4 raw normal operation lacks resource sample")
    total = 0.0
    for name in ("query_seconds", "materialize_seconds", "render_seconds"):
        value = getattr(sample, name, None)
        if value is None:
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise B4ExecutionAdapterError("B4 raw operation timing has wrong type")
        value = float(value)
        if not math.isfinite(value) or value < 0:
            raise B4ExecutionAdapterError("B4 raw operation timing is invalid")
        total += value
    # The scorer uses log ratios.  One microsecond is the explicit measurement
    # resolution floor, not an imputed zero or a performance win.
    return max(1, int(total * 1_000_000))


def _resource_rss(cell: Any) -> int:
    sample = getattr(getattr(cell, "record", None), "resource_sample", None)
    value = getattr(sample, "rss_bytes", None) if sample is not None else None
    if not _exact_int(value) or value <= 0:
        raise B4ExecutionAdapterError("B4 raw operation RSS sample is invalid")
    return value


def project_panel_outcomes(
    *,
    panel_index: int,
    tasks: Sequence[Any],
    scores: Mapping[tuple[str, str], Any],
    resources: Mapping[tuple[str, str], tuple[int, int]],
) -> tuple[b4r.B4TaskOutcome, ...]:
    """Project scored private task slugs onto public panel/task indices."""

    panel_index = _require_panel_index(panel_index)
    task_rows = tuple(tasks)
    slots = tuple(b2p.build_task_slots())
    if len(task_rows) != len(slots):
        raise B4ExecutionAdapterError("B4 scored panel task count drifted")
    task_by_slot = {getattr(task, "slot_id", None): task for task in task_rows}
    if set(task_by_slot) != {slot.slot_id for slot in slots}:
        raise B4ExecutionAdapterError("B4 scored panel task-slot set drifted")
    if len(task_by_slot) != len(task_rows):
        raise B4ExecutionAdapterError("B4 scored panel task slots are duplicated")

    schedule = {
        row.task_index: row
        for row in b4p.build_schedule()
        if row.panel_index == panel_index
    }
    outcomes: list[b4r.B4TaskOutcome] = []
    observed_keys: set[tuple[str, str]] = set()
    for task_index, slot in enumerate(slots, start=1):
        task = task_by_slot[slot.slot_id]
        task_slug = getattr(task, "task_slug", None)
        if not isinstance(task_slug, str) or not task_slug:
            raise B4ExecutionAdapterError("B4 scored panel task token is invalid")
        if getattr(task, "role", None) != slot.role:
            raise B4ExecutionAdapterError("B4 scored panel task role drifted")
        public = schedule[task_index]
        for arm_id in public.arm_order:
            key = (task_slug, arm_id)
            score = scores.get(key)
            resource = resources.get(key)
            if score is None or resource is None:
                raise B4ExecutionAdapterError("B4 scored panel key set is incomplete")
            observed_keys.add(key)
            query_us, peak_rss = resource
            outcomes.append(
                b4r.B4TaskOutcome(
                    schema_version=b4r.B4_TASK_OUTCOME_SCHEMA,
                    panel_index=panel_index,
                    repository_index=public.repository_index,
                    task_index=task_index,
                    task_role=public.task_role,
                    cache_state=public.cache_state,
                    arm_id=arm_id,
                    sequence_index=public.sequence_index,
                    arm_position=public.arm_order.index(arm_id) + 1,
                    task_success=score.task_success,
                    harmful_evidence=score.harmful_evidence,
                    status_or_target_success=score.target_or_status_success,
                    context_f05_ppm=score.context_f05_ppm,
                    query_us=query_us,
                    peak_rss_bytes=peak_rss,
                )
            )
    expected_keys = {
        (getattr(task, "task_slug"), arm_id)
        for task in task_rows
        for arm_id in b4p.B4_ARMS
    }
    if observed_keys != expected_keys or set(scores) != expected_keys or set(resources) != expected_keys:
        raise B4ExecutionAdapterError("B4 scored panel key set contains drift")
    if len(outcomes) != B4_PANEL_TASK_OUTCOME_COUNT:
        raise B4ExecutionAdapterError("B4 panel outcome count drifted")
    outcome_schedule = {
        (row.panel_index, row.task_index): row
        for row in b4p.build_schedule()
        if row.panel_index == panel_index
    }
    errors = [
        error
        for outcome in outcomes
        for error in b4r.validate_task_outcome(outcome, schedule=outcome_schedule)
    ]
    if errors:
        raise B4ExecutionAdapterError("B4 projected panel outcomes failed validation")
    return tuple(outcomes)


def convert_panel_result(
    *,
    panel_index: int,
    result: b21r.B21RunResult,
    oracle_manifest_path: Path,
) -> tuple[b4r.B4TaskOutcome, ...]:
    """Score one completed raw panel and erase all identity-bearing fields."""

    errors = _raw_panel_errors(result)
    if errors:
        raise B4ExecutionAdapterError("invalid B4 raw panel: " + "; ".join(errors))

    # These modules are intentionally imported only after the RUN phase has
    # completed.  The panel subprocess exits after writing the closed outcome.
    import product_bakeoff_b2_corpus as b2c  # noqa: PLC0415
    import product_bakeoff_b2_oracle as b2o  # noqa: PLC0415
    import product_bakeoff_b2_scorer as b2s  # noqa: PLC0415

    oracle_manifest = b2c.load_json(Path(oracle_manifest_path))
    oracles = b2o.validate_oracle_manifest(
        oracle_manifest,
        tasks=result.tasks,
        repo_lock=result.repo_lock,
        task_manifest_digest=result.task_manifest["task_manifest_digest"],
    )
    if oracle_manifest.get("oracle_manifest_digest") != result.freeze_receipt.get(
        "oracle_manifest_digest"
    ):
        raise B4ExecutionAdapterError("B4 oracle manifest differs from the frozen receipt")
    oracle_by_slug = {oracle.task_slug: oracle for oracle in oracles}

    normal: dict[tuple[str, str, str], Any] = {}
    for cell in result.cells:
        key = (cell.record.adapter_id, cell.record.run_cell_id, cell.record.operation)
        if key in normal:
            raise B4ExecutionAdapterError("B4 raw panel contains a duplicate normal outcome")
        normal[key] = cell
    terminals: dict[tuple[str, str], Any] = {}
    for cell in result.terminal_support_cells:
        key = (cell.adapter_id, cell.run_cell_id)
        if key in terminals:
            raise B4ExecutionAdapterError("B4 raw panel contains a duplicate terminal outcome")
        terminals[key] = cell

    scores: dict[tuple[str, str], Any] = {}
    resources: dict[tuple[str, str], tuple[int, int]] = {}
    for task in result.tasks:
        oracle = oracle_by_slug[task.task_slug]
        for arm_id in b4p.B4_ARMS:
            context = normal.get((arm_id, task.task_slug, "context"))
            if context is None:
                raise B4ExecutionAdapterError("B4 raw panel lacks a context outcome")
            normal_resource_cells = [context]
            if task.interaction_mode == "one_shot":
                score = b2s.score_task(
                    task=task,
                    oracle=oracle,
                    context_cell=context,
                    support_cell=None,
                )
            else:
                terminal = terminals.get((arm_id, task.task_slug))
                support = normal.get((arm_id, task.task_slug, "support"))
                if (terminal is None) == (support is None):
                    raise B4ExecutionAdapterError(
                        "B4 two-step task lacks exactly one support outcome kind"
                    )
                if terminal is not None:
                    target_success = b2s._context_target_success(context, oracle)
                    evidence_atoms = b2s._evidence_atoms(context)
                    positive_atoms = b2s._span_atoms(oracle.positive_spans)
                    negative_atoms = b2s._span_atoms(oracle.negative_spans)
                    context_score = (
                        b2s.f05_ppm(evidence_atoms, positive_atoms)
                        if oracle.oracle_kind != "abstain"
                        else 0
                    )
                    harmful = (
                        bool(evidence_atoms & negative_atoms)
                        if oracle.oracle_kind != "abstain"
                        else False
                    )
                    score = b2s.TaskScore(
                        target_or_status_success=target_success,
                        support_success=False,
                        task_success=False,
                        context_f05_ppm=context_score,
                        harmful_evidence=harmful,
                    )
                else:
                    score = b2s.score_task(
                        task=task,
                        oracle=oracle,
                        context_cell=context,
                        support_cell=support,
                    )
                    normal_resource_cells.append(support)
            scores[(task.task_slug, arm_id)] = score
            resources[(task.task_slug, arm_id)] = (
                sum(_resource_us(cell) for cell in normal_resource_cells),
                max(_resource_rss(cell) for cell in normal_resource_cells),
            )
    return project_panel_outcomes(
        panel_index=panel_index,
        tasks=result.tasks,
        scores=scores,
        resources=resources,
    )


def build_panel_outcome_report(
    panel_index: int,
    outcomes: Sequence[b4r.B4TaskOutcome],
) -> dict[str, Any]:
    panel_index = _require_panel_index(panel_index)
    rows = tuple(outcomes)
    if len(rows) != B4_PANEL_TASK_OUTCOME_COUNT:
        raise B4ExecutionAdapterError("B4 private panel outcome count drifted")
    if any(row.panel_index != panel_index for row in rows):
        raise B4ExecutionAdapterError("B4 private panel outcome panel binding drifted")
    outcome_schedule = {
        (row.panel_index, row.task_index): row
        for row in b4p.build_schedule()
        if row.panel_index == panel_index
    }
    if any(
        b4r.validate_task_outcome(row, schedule=outcome_schedule) for row in rows
    ):
        raise B4ExecutionAdapterError("B4 private panel outcome validation failed")
    report: dict[str, Any] = {
        "schema_version": B4_PANEL_OUTCOME_SCHEMA,
        "adapter_version": B4_EXECUTION_ADAPTER_VERSION,
        "panel_index": panel_index,
        "schedule_digest": panel_schedule_digest(panel_index),
        "task_outcome_count": len(rows),
        "logical_record_count": B4_PANEL_LOGICAL_RECORD_COUNT,
        "index_build_count": B4_PANEL_INDEX_BUILD_COUNT,
        "provider_network_call_count": 0,
        "raw_operation_receipts_complete": True,
        "outcomes": [asdict(row) for row in rows],
        "panel_outcome_digest": "",
    }
    report["panel_outcome_digest"] = _digest(
        "b4panelout_", report, "panel_outcome_digest"
    )
    return report


def validate_panel_outcome_report(report: Any) -> list[str]:
    if not isinstance(report, dict):
        return ["B4 private panel outcome report must be an object"]
    expected_keys = {
        "schema_version",
        "adapter_version",
        "panel_index",
        "schedule_digest",
        "task_outcome_count",
        "logical_record_count",
        "index_build_count",
        "provider_network_call_count",
        "raw_operation_receipts_complete",
        "outcomes",
        "panel_outcome_digest",
    }
    errors: list[str] = []
    if set(report) != expected_keys:
        errors.append("B4 private panel outcome report shape drifted")
        return errors
    try:
        panel_index = _require_panel_index(report["panel_index"])
    except B4ExecutionAdapterError:
        return ["B4 private panel outcome panel index invalid"]
    if report["schema_version"] != B4_PANEL_OUTCOME_SCHEMA:
        errors.append("B4 private panel outcome schema drifted")
    if report["adapter_version"] != B4_EXECUTION_ADAPTER_VERSION:
        errors.append("B4 private panel outcome adapter version drifted")
    if report["schedule_digest"] != panel_schedule_digest(panel_index):
        errors.append("B4 private panel outcome schedule digest drifted")
    if report["task_outcome_count"] != B4_PANEL_TASK_OUTCOME_COUNT:
        errors.append("B4 private panel outcome count drifted")
    if report["logical_record_count"] != B4_PANEL_LOGICAL_RECORD_COUNT:
        errors.append("B4 private panel logical record count drifted")
    if report["index_build_count"] != B4_PANEL_INDEX_BUILD_COUNT:
        errors.append("B4 private panel index-build count drifted")
    if report["provider_network_call_count"] != 0:
        errors.append("B4 private panel provider count is nonzero")
    if report["raw_operation_receipts_complete"] is not True:
        errors.append("B4 private panel operation receipts are incomplete")
    raw_outcomes = report["outcomes"]
    if not isinstance(raw_outcomes, list):
        errors.append("B4 private panel outcomes must be a list")
    else:
        parsed: list[b4r.B4TaskOutcome] = []
        expected_fields = set(b4r.B4TaskOutcome.__dataclass_fields__)
        for raw in raw_outcomes:
            if not isinstance(raw, dict) or set(raw) != expected_fields:
                errors.append("B4 private panel task outcome shape drifted")
                continue
            try:
                parsed.append(b4r.B4TaskOutcome(**raw))
            except TypeError:
                errors.append("B4 private panel task outcome could not be reconstructed")
        if len(parsed) == len(raw_outcomes):
            if len(parsed) != B4_PANEL_TASK_OUTCOME_COUNT:
                errors.append("B4 private panel task outcome cardinality drifted")
            if any(row.panel_index != panel_index for row in parsed):
                errors.append("B4 private panel task outcome binding drifted")
            outcome_schedule = {
                (row.panel_index, row.task_index): row
                for row in b4p.build_schedule()
                if row.panel_index == panel_index
            }
            errors.extend(
                error
                for outcome in parsed
                for error in b4r.validate_task_outcome(
                    outcome, schedule=outcome_schedule
                )
            )
            keys = {(row.task_index, row.arm_id) for row in parsed}
            expected = {
                (task_index, arm_id)
                for task_index in range(1, b4p.B4_TASKS_PER_PANEL + 1)
                for arm_id in b4p.B4_ARMS
            }
            if keys != expected or len(keys) != len(parsed):
                errors.append("B4 private panel task outcome key set drifted")
    if report["panel_outcome_digest"] != _digest(
        "b4panelout_", report, "panel_outcome_digest"
    ):
        errors.append("B4 private panel outcome digest mismatch")
    return sorted(set(errors))


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    parent = path.parent.resolve(strict=True)
    target = parent / path.name
    if os.path.lexists(target):
        raise B4ExecutionAdapterError("B4 private panel outcome already exists")
    descriptor, temporary_raw = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_raw)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(
                (json.dumps(value, indent=2, sort_keys=True) + "\n").encode(
                    "utf-8"
                )
            )
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        if os.path.lexists(target):
            raise B4ExecutionAdapterError(
                "B4 private panel outcome appeared concurrently"
            )
        os.replace(temporary, target)
        if os.name != "nt":
            directory_fd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_panel_outcome_report(
    path: Path,
    panel_index: int,
    outcomes: Sequence[b4r.B4TaskOutcome],
) -> Path:
    report = build_panel_outcome_report(panel_index, outcomes)
    errors = validate_panel_outcome_report(report)
    if errors:
        raise B4ExecutionAdapterError("refusing to write invalid B4 panel outcome")
    _atomic_write_json(Path(path), report)
    return Path(path)


def load_panel_outcome_report(path: Path) -> tuple[int, tuple[b4r.B4TaskOutcome, ...]]:
    report = _load_private_json(Path(path))
    errors = validate_panel_outcome_report(report)
    if errors:
        raise B4ExecutionAdapterError("invalid B4 private panel outcome report")
    outcomes = tuple(b4r.B4TaskOutcome(**row) for row in report["outcomes"])
    return report["panel_index"], outcomes


def assemble_run_result(
    panel_reports: Sequence[Mapping[str, Any]],
) -> b4r.B4RunResult:
    if len(panel_reports) != b4p.B4_PANEL_COUNT:
        raise B4ExecutionAdapterError("B4 private panel report count drifted")
    by_panel: dict[int, tuple[b4r.B4TaskOutcome, ...]] = {}
    for report in panel_reports:
        errors = validate_panel_outcome_report(report)
        if errors:
            raise B4ExecutionAdapterError("invalid B4 private panel report")
        panel_index = report["panel_index"]
        if panel_index in by_panel:
            raise B4ExecutionAdapterError("B4 private panel report is duplicated")
        by_panel[panel_index] = tuple(
            b4r.B4TaskOutcome(**row) for row in report["outcomes"]
        )
    if set(by_panel) != set(range(1, b4p.B4_PANEL_COUNT + 1)):
        raise B4ExecutionAdapterError("B4 private panel report set is incomplete")
    result = b4r.B4RunResult(
        schema_version=b4r.B4_RUN_RESULT_SCHEMA,
        outcomes=tuple(
            outcome
            for panel_index in range(1, b4p.B4_PANEL_COUNT + 1)
            for outcome in by_panel[panel_index]
        ),
        logical_group_count=b4p.B4_LOGICAL_GROUP_COUNT,
        logical_record_count=b4p.B4_LOGICAL_RECORD_COUNT,
        index_build_count=b4p.B4_INDEX_BUILD_COUNT,
        provider_network_call_count=0,
        passed_pre_score_gates=b4r.B4_REQUIRED_PRE_SCORE_GATES,
        raw_operation_receipts_complete=True,
    )
    return b4r.require_valid_run_result(result)


def validate_panel_envelope(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["B4 private panel envelope must be an object"]
    expected = {
        "schema_version",
        "panel_index",
        "repo_lock_path",
        "task_manifest_path",
        "oracle_manifest_path",
        "holdout_binding_path",
        "excluded_repo_lock_path",
        "preflight_exclusion_path",
        "freeze_receipt_path",
        "expected_freeze_digest",
        "runs_dir",
        "outcome_path",
        "keep_worktrees",
    }
    errors: list[str] = []
    if set(value) != expected:
        return ["B4 private panel envelope shape drifted"]
    if value["schema_version"] != B4_PANEL_ENVELOPE_SCHEMA:
        errors.append("B4 private panel envelope schema drifted")
    try:
        _require_panel_index(value["panel_index"])
    except B4ExecutionAdapterError:
        errors.append("B4 private panel envelope panel index invalid")
    for key in expected - {"schema_version", "panel_index", "keep_worktrees"}:
        if not isinstance(value[key], str) or not value[key]:
            errors.append("B4 private panel envelope contains an invalid string field")
    if type(value["keep_worktrees"]) is not bool:
        errors.append("B4 private panel envelope keep-worktrees flag invalid")
    return sorted(set(errors))


def execute_panel_envelope(path: Path) -> dict[str, Any]:
    envelope = _load_private_json(Path(path))
    errors = validate_panel_envelope(envelope)
    if errors:
        raise B4ExecutionAdapterError("invalid B4 private panel launch envelope")
    # The control module contains no scorer/oracle import and is safe to load
    # before the raw RUN phase.  The validator binds this panel to the frozen
    # 12-panel holdout and exact runtime/source receipts.
    import product_bakeoff_b4_control as b4c  # noqa: PLC0415

    panel_index = envelope["panel_index"]

    def receipt_validator(raw: Any, **kwargs: Any) -> Mapping[str, Any]:
        return b4c.validate_panel_freeze_receipt(
            raw, panel_index=panel_index, **kwargs
        )

    result = run_panel_engine(
        panel_index=panel_index,
        repo_lock_path=Path(envelope["repo_lock_path"]),
        task_manifest_path=Path(envelope["task_manifest_path"]),
        oracle_manifest_path=Path(envelope["oracle_manifest_path"]),
        holdout_binding_path=Path(envelope["holdout_binding_path"]),
        excluded_repo_lock_path=Path(envelope["excluded_repo_lock_path"]),
        preflight_exclusion_path=Path(envelope["preflight_exclusion_path"]),
        freeze_receipt_path=Path(envelope["freeze_receipt_path"]),
        expected_freeze_digest=envelope["expected_freeze_digest"],
        runs_dir=Path(envelope["runs_dir"]),
        receipt_validator=receipt_validator,
        keep_worktrees=envelope["keep_worktrees"],
    )
    outcomes = convert_panel_result(
        panel_index=panel_index,
        result=result,
        oracle_manifest_path=Path(envelope["oracle_manifest_path"]),
    )
    write_panel_outcome_report(
        Path(envelope["outcome_path"]), panel_index, outcomes
    )
    return {
        "passed": True,
        "panel_index": panel_index,
        "task_outcome_count": len(outcomes),
        "logical_record_count": result.logical_record_count,
        "index_build_count": B4_PANEL_INDEX_BUILD_COUNT,
    }


def _synthetic_tasks() -> tuple[SimpleNamespace, ...]:
    return tuple(
        SimpleNamespace(
            slot_id=slot.slot_id,
            task_slug=f"synthetic_{slot.slot_id}",
            role=slot.role,
            interaction_mode=slot.interaction_mode,
        )
        for slot in b2p.build_task_slots()
    )


def run_self_test() -> dict[str, Any]:
    checks: list[bool] = []
    for panel_index in range(1, b4p.B4_PANEL_COUNT + 1):
        rows = build_panel_schedule(panel_index)
        checks.extend(
            [
                not validate_panel_schedule(rows, panel_index=panel_index),
                len(rows) == b4p.B4_TASKS_PER_PANEL,
                len(b2r._schedule_groups(rows)) == b4p.B4_REPOSITORIES_PER_PANEL,
                panel_schedule_digest(panel_index).startswith("b4panelsched_"),
            ]
        )

    before = (
        tuple((name, getattr(b2p, name)) for name in _FROZEN_B2P_BINDINGS),
        tuple((name, getattr(b2r, name)) for name in _FROZEN_B2R_BINDINGS),
        b21r.b21_execution_schedule_digest,
        b21r.B2_ADAPTERS,
    )

    def receipt_validator(raw: Any, **_: Any) -> Mapping[str, Any]:
        if not isinstance(raw, Mapping):
            raise B4ExecutionAdapterError("synthetic receipt has wrong type")
        return raw

    with b24r._longrun_runtime_override(receipt_validator):
        with b4_panel_engine_override(1):
            rows = b2p.build_execution_schedule()
            checks.extend(
                [
                    b2p.B2_ADAPTER_IDS == b4p.B4_ARMS,
                    b2p.B2_REPETITIONS == (1,),
                    b2p.B2_TOTAL_RECORDS == B4_PANEL_LOGICAL_RECORD_COUNT,
                    b2r.B2_INDEX_BUILD_COUNT == B4_PANEL_INDEX_BUILD_COUNT,
                    not b2p.validate_execution_schedule(rows, b2p.build_task_slots()),
                    b21r.b21_execution_schedule_digest() == panel_schedule_digest(1),
                    tuple(row[0] for row in b21r.B2_ADAPTERS) == b4p.B4_ARMS,
                ]
            )
        checks.append(b21r.B2_ADAPTERS is b24r.B24_ADAPTERS)
    after = (
        tuple((name, getattr(b2p, name)) for name in _FROZEN_B2P_BINDINGS),
        tuple((name, getattr(b2r, name)) for name in _FROZEN_B2R_BINDINGS),
        b21r.b21_execution_schedule_digest,
        b21r.B2_ADAPTERS,
    )
    checks.append(before == after)

    runtime_before = (
        b2r.make_b2_request,
        b24r.b1a._CLI_TIMEOUT,
        b21r.validate_freeze_receipt,
        b21r.B2_ADAPTERS,
    )
    original_run_full_matrix = b21r.run_full_matrix
    sentinel = object()
    engine_observations: list[bool] = []

    def fake_run_full_matrix(**kwargs: Any) -> object:
        engine_observations.extend(
            [
                b2p.B2_ADAPTER_IDS == b4p.B4_ARMS,
                b2p.B2_REPETITIONS == (1,),
                b2r.B2_TOTAL_RECORDS == B4_PANEL_LOGICAL_RECORD_COUNT,
                b21r.b21_execution_schedule_digest()
                == panel_schedule_digest(2),
                tuple(row[0] for row in b21r.B2_ADAPTERS) == b4p.B4_ARMS,
                b21r.validate_freeze_receipt is receipt_validator,
                kwargs["expected_freeze_digest"] == "b4freeze_synthetic",
            ]
        )
        return sentinel

    b21r.run_full_matrix = fake_run_full_matrix
    try:
        engine_result = run_panel_engine(
            panel_index=2,
            repo_lock_path=Path("repo.json"),
            task_manifest_path=Path("tasks.json"),
            oracle_manifest_path=Path("oracle.json"),
            holdout_binding_path=Path("binding.json"),
            excluded_repo_lock_path=Path("history.json"),
            preflight_exclusion_path=Path("exclusions.json"),
            freeze_receipt_path=Path("freeze.json"),
            expected_freeze_digest="b4freeze_synthetic",
            runs_dir=Path("runs"),
            receipt_validator=receipt_validator,
        )
    finally:
        b21r.run_full_matrix = original_run_full_matrix
    runtime_after = (
        b2r.make_b2_request,
        b24r.b1a._CLI_TIMEOUT,
        b21r.validate_freeze_receipt,
        b21r.B2_ADAPTERS,
    )
    checks.extend(
        [
            engine_result is sentinel,
            all(engine_observations),
            runtime_before == runtime_after,
        ]
    )

    tasks = _synthetic_tasks()
    scores: dict[tuple[str, str], Any] = {}
    resources: dict[tuple[str, str], tuple[int, int]] = {}
    for task in tasks:
        for arm_index, arm_id in enumerate(b4p.B4_ARMS):
            scores[(task.task_slug, arm_id)] = SimpleNamespace(
                task_success=arm_index > 0,
                harmful_evidence=False,
                target_or_status_success=True,
                context_f05_ppm=500_000 + arm_index,
            )
            resources[(task.task_slug, arm_id)] = (
                1_000 + arm_index,
                100_000_000 + arm_index,
            )
    projected = project_panel_outcomes(
        panel_index=1, tasks=tasks, scores=scores, resources=resources
    )
    checks.extend(
        [
            len(projected) == B4_PANEL_TASK_OUTCOME_COUNT,
            not validate_panel_outcome_report(build_panel_outcome_report(1, projected)),
        ]
    )

    synthetic = b4r.synthetic_run_result()
    panel_reports = [
        build_panel_outcome_report(
            panel_index,
            [row for row in synthetic.outcomes if row.panel_index == panel_index],
        )
        for panel_index in range(1, b4p.B4_PANEL_COUNT + 1)
    ]
    assembled = assemble_run_result(panel_reports)
    checks.extend(
        [
            not b4r.validate_run_result(assembled),
            assembled.outcomes == synthetic.outcomes,
            assembled.logical_record_count == b4p.B4_LOGICAL_RECORD_COUNT,
        ]
    )
    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
        "panel_count": b4p.B4_PANEL_COUNT,
        "panel_logical_records": B4_PANEL_LOGICAL_RECORD_COUNT,
        "total_task_outcomes": len(assembled.outcomes),
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[bool] = []
    base_rows = list(build_panel_schedule(1))
    checks.append(bool(validate_panel_schedule(base_rows[:-1], panel_index=1)))
    drifted = list(base_rows)
    drifted[0] = b2p.B2ScheduleRow(
        slot_id=drifted[0].slot_id,
        repo_slot=drifted[0].repo_slot,
        repetition=2,
        cache_state=drifted[0].cache_state,
        task_position=drifted[0].task_position,
        arm_order=drifted[0].arm_order,
    )
    checks.append(bool(validate_panel_schedule(drifted, panel_index=1)))

    synthetic = b4r.synthetic_run_result()
    panel_one = [row for row in synthetic.outcomes if row.panel_index == 1]
    base = build_panel_outcome_report(1, panel_one)
    mutations = []
    missing = copy.deepcopy(base)
    missing["outcomes"] = missing["outcomes"][:-1]
    mutations.append(missing)
    duplicate = copy.deepcopy(base)
    duplicate["outcomes"][-1] = copy.deepcopy(duplicate["outcomes"][0])
    mutations.append(duplicate)
    wrong_panel = copy.deepcopy(base)
    wrong_panel["outcomes"][0]["panel_index"] = 2
    mutations.append(wrong_panel)
    bool_as_int = copy.deepcopy(base)
    bool_as_int["outcomes"][0]["query_us"] = True
    mutations.append(bool_as_int)
    leaked = copy.deepcopy(base)
    leaked["outcomes"][0]["repository_slug"] = "forbidden"
    mutations.append(leaked)
    bad_digest = copy.deepcopy(base)
    bad_digest["panel_outcome_digest"] = "b4panelout_" + "0" * 64
    mutations.append(bad_digest)
    checks.extend(bool(validate_panel_outcome_report(value)) for value in mutations)

    with tempfile.TemporaryDirectory() as raw:
        path = Path(raw) / "panel.json"
        write_panel_outcome_report(path, 1, panel_one)
        try:
            write_panel_outcome_report(path, 1, panel_one)
            exclusive_outcome_write = False
        except B4ExecutionAdapterError:
            exclusive_outcome_write = True
        duplicate_path = Path(raw) / "duplicate.json"
        duplicate_path.write_text('{"value":1,"value":2}\n', encoding="utf-8")
        nonfinite_path = Path(raw) / "nonfinite.json"
        nonfinite_path.write_text('{"value":NaN}\n', encoding="utf-8")
        try:
            _load_private_json(duplicate_path)
            duplicate_json_rejected = False
        except B4ExecutionAdapterError:
            duplicate_json_rejected = True
        try:
            _load_private_json(nonfinite_path)
            nonfinite_json_rejected = False
        except B4ExecutionAdapterError:
            nonfinite_json_rejected = True
    checks.append(exclusive_outcome_write)
    checks.extend((duplicate_json_rejected, nonfinite_json_rejected))

    try:
        with b24r._longrun_runtime_override(lambda raw, **_: raw):
            with b4_panel_engine_override(1):
                with b4_panel_engine_override(1):
                    pass
        nested_rejected = False
    except B4ExecutionAdapterError:
        nested_rejected = True
    checks.append(nested_rejected)

    runtime_before = (
        b2r.make_b2_request,
        b24r.b1a._CLI_TIMEOUT,
        b21r.validate_freeze_receipt,
        b21r.B2_ADAPTERS,
        tuple((name, getattr(b2p, name)) for name in _FROZEN_B2P_BINDINGS),
        tuple((name, getattr(b2r, name)) for name in _FROZEN_B2R_BINDINGS),
        b21r.b21_execution_schedule_digest,
    )
    original_run_full_matrix = b21r.run_full_matrix

    def failing_run_full_matrix(**_: Any) -> object:
        raise RuntimeError("synthetic raw-panel failure")

    b21r.run_full_matrix = failing_run_full_matrix
    restored_after_exception = False
    try:
        run_panel_engine(
            panel_index=1,
            repo_lock_path=Path("repo.json"),
            task_manifest_path=Path("tasks.json"),
            oracle_manifest_path=Path("oracle.json"),
            holdout_binding_path=Path("binding.json"),
            excluded_repo_lock_path=Path("history.json"),
            preflight_exclusion_path=Path("exclusions.json"),
            freeze_receipt_path=Path("freeze.json"),
            expected_freeze_digest="b4freeze_synthetic",
            runs_dir=Path("runs"),
            receipt_validator=lambda raw, **_: raw,
        )
    except RuntimeError:
        runtime_after = (
            b2r.make_b2_request,
            b24r.b1a._CLI_TIMEOUT,
            b21r.validate_freeze_receipt,
            b21r.B2_ADAPTERS,
            tuple((name, getattr(b2p, name)) for name in _FROZEN_B2P_BINDINGS),
            tuple((name, getattr(b2r, name)) for name in _FROZEN_B2R_BINDINGS),
            b21r.b21_execution_schedule_digest,
        )
        restored_after_exception = runtime_before == runtime_after
    finally:
        b21r.run_full_matrix = original_run_full_matrix
    checks.append(restored_after_exception)

    return {
        "passed": all(checks),
        "checks_total": len(checks),
        "checks_passed": sum(checks),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fault-test", action="store_true")
    mode.add_argument("--run-panel-envelope", type=Path)
    parser.add_argument("--confirm-private-input", action="store_true")
    parser.add_argument("--confirm-private-output", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        report = run_self_test()
    elif args.fault_test:
        report = run_fault_test()
    else:
        if not args.confirm_private_input or not args.confirm_private_output:
            raise B4ExecutionAdapterError(
                "B4 panel execution requires explicit private input/output confirmations"
            )
        report = execute_panel_envelope(args.run_panel_envelope)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B4_EXECUTION_ADAPTER_VERSION",
    "B4_PANEL_OUTCOME_SCHEMA",
    "B4_PANEL_ENVELOPE_SCHEMA",
    "B4_PANEL_LOGICAL_RECORD_COUNT",
    "B4_PANEL_INDEX_BUILD_COUNT",
    "B4ExecutionAdapterError",
    "build_panel_schedule",
    "validate_panel_schedule",
    "panel_schedule_digest",
    "b4_panel_engine_override",
    "run_panel_engine",
    "project_panel_outcomes",
    "convert_panel_result",
    "build_panel_outcome_report",
    "validate_panel_outcome_report",
    "write_panel_outcome_report",
    "load_panel_outcome_report",
    "assemble_run_result",
    "validate_panel_envelope",
    "execute_panel_envelope",
    "run_self_test",
    "run_fault_test",
]
