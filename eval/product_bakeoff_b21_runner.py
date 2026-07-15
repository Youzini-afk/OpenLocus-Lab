#!/usr/bin/env python3
"""B2.1 oracle-free split-plot runner with same-arm own-parent lineage."""

from __future__ import annotations

import ctypes
import dataclasses
import hashlib
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from product_bakeoff_contract import PackTarget, ResourceSample
from product_bakeoff_conformance import (
    EpisodeRegistry,
    require_scoreable,
    stable_target_id,
    validate_run_record,
)
from product_bakeoff_b1_adapters import (
    enforce_source_immutability,
    enforce_wsr_inventory,
    verify_index_seal,
    write_index_seal,
)
from product_bakeoff_b1_spec import adapter_supports_support
from product_bakeoff_b1_runner import _clear_lineage_receipt, _json_safe, _write_lineage_receipt
from product_bakeoff_b2_adapters import B2_ADAPTERS
import product_bakeoff_b2_corpus as b2c
import product_bakeoff_b2_runner as b2r
import product_bakeoff_b2_protocol as b2p
from product_bakeoff_b21_corpus import validate_freeze_receipt
from product_bakeoff_b21_protocol import (
    B21_PARENT_UNAVAILABLE_POLICY,
    b21_execution_schedule_digest,
)


B21_RUNNER_VERSION = "product_bakeoff_b21_runner.v1"
B21_PRIVATE_RUN_SCHEMA = "product_bakeoff_b21_private_run.v1"
B21_TERMINAL_SCHEMA = "product_bakeoff_b21_terminal_support.v1"


class B21RunError(RuntimeError):
    """Fail-closed B2.1 execution error."""


@dataclass
class B21TerminalSupportCell:
    adapter_id: str
    run_cell_id: str
    adapter_repetition: int
    cache_state: str
    cell_key: tuple[Any, ...]
    context_cell: b2r.B2CellResult
    reason: str
    resource_sample: ResourceSample
    semantic_hash: str
    static_fingerprint: str
    parent_receipt: dict[str, Any]


@dataclass
class B21RunResult(b2r.B2RunResult):
    terminal_support_cells: list[B21TerminalSupportCell] = field(default_factory=list)
    logical_execution_keys: list[tuple[Any, ...]] = field(default_factory=list)
    holdout_binding: dict[str, Any] | None = None
    terminal_parent_receipts: list[dict[str, Any]] = field(default_factory=list)

    @property
    def logical_record_count(self) -> int:
        return len(self.records) + len(self.terminal_support_cells)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _request_token(prefix: str, task: b2c.B2PublicTask, repetition: int) -> str:
    short = hashlib.sha256(
        f"b21|{prefix}|{task.slot_id}|{repetition}".encode("utf-8")
    ).hexdigest()[:12]
    return f"b21_{prefix}_{task.slot_id}_r{repetition}_{short}"


def _current_rss_bytes() -> int:
    if os.name == "nt":
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("PageFaultCount", ctypes.c_ulong),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
            ctypes.c_ulong,
        ]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        ok = psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(),
            ctypes.byref(counters),
            counters.cb,
        )
        if not ok:
            raise B21RunError("parent RSS measurement failed")
        return int(counters.WorkingSetSize)
    import resource

    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value * 1024 if sys.platform != "darwin" else value


def _static_payload_from_context(
    context_cell: b2r.B2CellResult,
    *,
    support_request_id: str,
) -> dict[str, Any]:
    payload = dataclasses.asdict(context_cell.request.run_spec)
    payload["operation"] = "support"
    payload["request_id"] = support_request_id
    payload["parent_result_id"] = None
    payload["bound_target_id"] = None
    return payload


def _support_static_fingerprint(
    context_cell: b2r.B2CellResult,
    *,
    support_request_id: str,
) -> str:
    return _digest(
        "b21static_",
        _static_payload_from_context(
            context_cell,
            support_request_id=support_request_id,
        ),
    )


def _own_parent_target(context_cell: b2r.B2CellResult) -> PackTarget | None:
    require_scoreable(context_cell.record, context_cell.capture)
    output = context_cell.capture.output
    if output is None:
        raise B21RunError("accepted context capture is missing")
    if output.pack.pack_status == "ready" and len(output.pack.targets) == 1:
        return output.pack.targets[0]
    return None


def _terminal_semantic_hash(
    context_cell: b2r.B2CellResult,
    *,
    reason: str,
) -> str:
    return _digest(
        "b21terminal_sem_",
        {
            "adapter_id": context_cell.record.adapter_id,
            "run_cell_id": context_cell.record.run_cell_id,
            "reason": reason,
            "context_semantic_hash": context_cell.semantic_hash,
        },
    )


def _index_state_bytes(seal: Mapping[str, Any]) -> int:
    total = 0
    for value in seal["inventory"].values():
        if value == "directory":
            continue
        size_text, separator, _ = value.partition(":")
        if not separator or not size_text.isdigit():
            raise B21RunError("terminal index inventory byte count malformed")
        total += int(size_text)
    return total


def _make_terminal_support(
    *,
    context_cell: b2r.B2CellResult,
    support_request_id: str,
    cell_key: tuple[Any, ...],
) -> B21TerminalSupportCell:
    if context_cell.record.status != "accepted":
        raise B21RunError("terminal support requires an accepted context outcome")
    if _own_parent_target(context_cell) is not None:
        raise B21RunError("terminal support forbidden when a ready parent exists")
    cpu_started = time.process_time()
    setup_started = time.perf_counter()
    seal = verify_index_seal(context_cell.cell_root)
    enforce_source_immutability(context_cell.cell_root, context_cell.source_digests)
    enforce_wsr_inventory(context_cell.cell_root, expected_index_sealed=True)
    setup_elapsed = time.perf_counter() - setup_started
    terminal_started = time.perf_counter()
    reason = "parent_unavailable"
    semantic_hash = _terminal_semantic_hash(context_cell, reason=reason)
    static_fingerprint = _support_static_fingerprint(
        context_cell,
        support_request_id=support_request_id,
    )
    terminal_elapsed = time.perf_counter() - terminal_started
    resource = ResourceSample(
        setup_seconds=(setup_elapsed if context_cell.record.cache_state == "cold" else None),
        index_seconds=None,
        query_seconds=terminal_elapsed,
        materialize_seconds=0.0,
        render_seconds=0.0,
        rss_bytes=_current_rss_bytes(),
        cpu_seconds=time.process_time() - cpu_started,
    ).validate()
    receipt = {
        "schema_version": "product_bakeoff_b21_terminal_parent_receipt.v1",
        "adapter_id": context_cell.record.adapter_id,
        "task_slug": context_cell.record.run_cell_id,
        "operation": "support",
        "cache_state": context_cell.record.cache_state,
        "adapter_repetition": context_cell.record.adapter_repetition,
        "terminal_outcome": reason,
        "context_canonical_result_hash": context_cell.record.canonical_result_hash,
        "context_canonical_pack_hash": context_cell.record.canonical_pack_hash,
        "context_semantic_hash": context_cell.semantic_hash,
        "provider_network_call_count": 0,
        "index_inventory_digest": seal["inventory_digest"],
        "index_state_bytes": _index_state_bytes(seal),
        "source_immutable": True,
        "static_fingerprint": static_fingerprint,
    }
    return B21TerminalSupportCell(
        adapter_id=context_cell.record.adapter_id,
        run_cell_id=context_cell.record.run_cell_id,
        adapter_repetition=context_cell.record.adapter_repetition,
        cache_state=context_cell.record.cache_state,
        cell_key=cell_key,
        context_cell=context_cell,
        reason=reason,
        resource_sample=resource,
        semantic_hash=semantic_hash,
        static_fingerprint=static_fingerprint,
        parent_receipt=receipt,
    )


def _terminal_to_private_dict(cell: B21TerminalSupportCell) -> dict[str, Any]:
    return {
        "schema_version": B21_TERMINAL_SCHEMA,
        "runner_version": B21_RUNNER_VERSION,
        "adapter_id": cell.adapter_id,
        "run_cell_id": cell.run_cell_id,
        "adapter_repetition": cell.adapter_repetition,
        "cache_state": cell.cache_state,
        "cell_key": _json_safe(cell.cell_key),
        "reason": cell.reason,
        "resource_sample": _json_safe(cell.resource_sample),
        "semantic_hash": cell.semantic_hash,
        "static_fingerprint": cell.static_fingerprint,
        "parent_receipt": cell.parent_receipt,
    }


def _persist_terminal(cell: B21TerminalSupportCell, private_root: Path) -> None:
    path = (
        private_root
        / "terminal_support"
        / f"{cell.adapter_id}__{cell.run_cell_id}__r{cell.adapter_repetition}.json"
    )
    b2c.write_json(path, _terminal_to_private_dict(cell))


def _append_normal(
    result: B21RunResult,
    cell: b2r.B2CellResult,
    descriptor: Any,
    private_root: Path,
) -> None:
    b2r._finish_cell(result, cell, descriptor, private_root)
    result.logical_execution_keys.append(cell.cell_key)


def _append_terminal(
    result: B21RunResult,
    cell: B21TerminalSupportCell,
    private_root: Path,
) -> None:
    result.terminal_support_cells.append(cell)
    result.terminal_parent_receipts.append(cell.parent_receipt)
    result.logical_execution_keys.append(cell.cell_key)
    _persist_terminal(cell, private_root)


def _validate_terminal(cell: B21TerminalSupportCell) -> list[str]:
    errors: list[str] = []
    if cell.reason != B21_PARENT_UNAVAILABLE_POLICY["terminal_outcome"]:
        errors.append("terminal reason drift")
    if cell.context_cell.record.status != "accepted":
        errors.append("terminal context is not accepted")
    try:
        require_scoreable(cell.context_cell.record, cell.context_cell.capture)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"terminal context not scoreable: {type(exc).__name__}")
    else:
        if _own_parent_target(cell.context_cell) is not None:
            errors.append("terminal has a usable parent")
    try:
        cell.resource_sample.validate()
    except Exception as exc:  # noqa: BLE001
        errors.append(f"terminal resource invalid: {type(exc).__name__}")
    if not cell.semantic_hash.startswith("b21terminal_sem_"):
        errors.append("terminal semantic hash malformed")
    if not cell.static_fingerprint.startswith("b21static_"):
        errors.append("terminal static fingerprint malformed")
    if cell.parent_receipt.get("provider_network_call_count") != 0:
        errors.append("terminal provider count nonzero")
    return errors


def _logical_semantic_gate(result: B21RunResult) -> tuple[bool, str]:
    groups: dict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)
    for cell in result.cells:
        groups[(
            cell.record.adapter_id,
            cell.record.run_cell_id,
            cell.record.operation,
        )].append(("normal", cell.semantic_hash or ""))
    for cell in result.terminal_support_cells:
        groups[(cell.adapter_id, cell.run_cell_id, "support")].append(
            ("terminal", cell.semantic_hash)
        )
    failures: list[str] = []
    for key, values in groups.items():
        if len(values) != len(b2p.B2_REPETITIONS):
            failures.append(f"{key}: observations={len(values)}")
            continue
        if len(set(values)) != 1:
            failures.append(f"{key}: semantic or terminal-kind drift")
    return not failures, "; ".join(failures[:8])


def _same_arm_lineage_gate(result: B21RunResult) -> tuple[bool, str]:
    contexts: dict[tuple[str, str, int], b2r.B2CellResult] = {}
    supports: dict[tuple[str, str, int], b2r.B2CellResult | B21TerminalSupportCell] = {}
    for cell in result.cells:
        key = (
            cell.record.adapter_id,
            cell.record.run_cell_id,
            cell.record.adapter_repetition,
        )
        if cell.record.operation == "context":
            contexts[key] = cell
        elif cell.record.operation == "support":
            supports[key] = cell
    for cell in result.terminal_support_cells:
        supports[(cell.adapter_id, cell.run_cell_id, cell.adapter_repetition)] = cell
    failures: list[str] = []
    for key, context in contexts.items():
        if context.record.interaction_mode != "two_step":
            continue
        support = supports.get(key)
        if support is None:
            failures.append(f"{key}: missing support opportunity")
            continue
        target = _own_parent_target(context)
        if isinstance(support, B21TerminalSupportCell):
            if target is not None:
                failures.append(f"{key}: terminal despite ready target")
            continue
        if target is None:
            failures.append(f"{key}: executed support without ready target")
            continue
        expected_id = stable_target_id(target)
        if support.request.run_spec.bound_target_id != expected_id:
            failures.append(f"{key}: bound target is not own context target")
        if support.request.run_spec.parent_result_id != context.request.run_spec.request_id:
            failures.append(f"{key}: parent result id drift")
        output = support.capture.output
        if output is None:
            failures.append(f"{key}: support capture missing")
            continue
        for relation in output.pack.support:
            if relation.parent_target_id != expected_id:
                failures.append(f"{key}: support relation parent drift")
                break
    return not failures, "; ".join(failures[:8])


def _fairness_gate(result: B21RunResult) -> tuple[bool, str]:
    context_fingerprints: dict[tuple[str, int, str], set[str]] = defaultdict(set)
    support_static: dict[tuple[str, int, str], set[str]] = defaultdict(set)
    for cell in result.cells:
        key = (
            cell.record.run_cell_id,
            cell.record.adapter_repetition,
            cell.record.cache_state,
        )
        if cell.record.operation == "context":
            context_fingerprints[key].add(cell.record.fingerprint)
        else:
            support_static[key].add(
                _support_static_fingerprint(
                    cell.context_cell if hasattr(cell, "context_cell") else _find_context(result, cell),
                    support_request_id=cell.request.run_spec.request_id,
                )
            )
    for terminal in result.terminal_support_cells:
        key = (terminal.run_cell_id, terminal.adapter_repetition, terminal.cache_state)
        support_static[key].add(terminal.static_fingerprint)
    failures = [
        f"context:{key}" for key, values in context_fingerprints.items() if len(values) != 1
    ]
    failures.extend(
        f"support:{key}" for key, values in support_static.items() if len(values) != 1
    )
    return not failures, "; ".join(failures[:8])


def _find_context(result: B21RunResult, support: b2r.B2CellResult) -> b2r.B2CellResult:
    matches = [
        cell
        for cell in result.cells
        if cell.record.operation == "context"
        and cell.record.adapter_id == support.record.adapter_id
        and cell.record.run_cell_id == support.record.run_cell_id
        and cell.record.adapter_repetition == support.record.adapter_repetition
    ]
    if len(matches) != 1:
        raise B21RunError("support does not have exactly one same-arm context")
    return matches[0]


def _check_pre_score_gates(
    result: B21RunResult,
    *,
    expected_keys: Sequence[tuple[Any, ...]],
    scorer_modules_unloaded: bool,
    freeze_valid: bool,
) -> b2r.B2GateResult:
    gate = b2r.B2GateResult()
    logical_count = result.logical_record_count
    gate.check(
        "private_holdout_and_runtime_frozen",
        freeze_valid,
        "B2.1 receipt did not bind current holdout/source/runtime",
    )
    gate.check(
        "complete_1440_logical_record_matrix",
        logical_count == b2p.B2_TOTAL_RECORDS
        and result.logical_execution_keys == list(expected_keys)
        and len(set(result.logical_execution_keys)) == b2p.B2_TOTAL_RECORDS,
        f"logical_records={logical_count}/{b2p.B2_TOTAL_RECORDS}",
    )
    invalid_records = [
        (record.adapter_id, record.run_cell_id, validate_run_record(record))
        for record in result.records
        if validate_run_record(record)
    ]
    gate.check("normal_run_records_valid", not invalid_records, str(invalid_records[:3]))
    gate.check(
        "normal_adapter_records_accepted",
        all(record.status == "accepted" and record.result_status == "ok" for record in result.records),
        f"not_accepted={sum(record.status != 'accepted' or record.result_status != 'ok' for record in result.records)}",
    )
    scoreable_errors: list[str] = []
    for record, capture in zip(result.records, result.captures):
        try:
            require_scoreable(record, capture)
        except Exception as exc:  # noqa: BLE001
            scoreable_errors.append(
                f"{record.adapter_id}/{record.run_cell_id}:{type(exc).__name__}"
            )
    gate.check("normal_adapter_records_scoreable", not scoreable_errors, str(scoreable_errors[:5]))
    terminal_errors = [
        (cell.adapter_id, cell.run_cell_id, _validate_terminal(cell))
        for cell in result.terminal_support_cells
        if _validate_terminal(cell)
    ]
    gate.check("terminal_support_records_valid", not terminal_errors, str(terminal_errors[:3]))
    normal_resources = sum(
        record.resource_sample is not None
        and record.resource_sample.cpu_seconds is not None
        and record.resource_sample.rss_bytes is not None
        and record.resource_sample.query_seconds is not None
        for record in result.records
    )
    terminal_resources = sum(
        cell.resource_sample.cpu_seconds is not None
        and cell.resource_sample.rss_bytes is not None
        and cell.resource_sample.query_seconds is not None
        for cell in result.terminal_support_cells
    )
    gate.check(
        "all_logical_resource_samples_complete",
        normal_resources + terminal_resources == logical_count,
        f"complete={normal_resources + terminal_resources}/{logical_count}",
    )
    gate.check(
        "source_immutable_and_wsr_strict",
        len(result.parent_receipts) == len(result.records)
        and len(result.terminal_parent_receipts) == len(result.terminal_support_cells)
        and not result.parent_receipt_failures,
        str(result.parent_receipt_failures[:5]),
    )
    index_builds = sum(
        receipt["lifecycle_command_kind"] == "rust_index_build"
        for receipt in result.parent_receipts
    )
    gate.check(
        "exact_split_plot_index_build_count",
        index_builds == b2p.B2_INDEX_BUILD_COUNT,
        f"index_builds={index_builds}/{b2p.B2_INDEX_BUILD_COUNT}",
    )
    semantic_ok, semantic_detail = _logical_semantic_gate(result)
    gate.check("cold_warm_and_repetition_semantics_equal", semantic_ok, semantic_detail)
    lineage_ok, lineage_detail = _same_arm_lineage_gate(result)
    gate.check("same_arm_parent_lineage_valid", lineage_ok, lineage_detail)
    fairness_ok, fairness_detail = _fairness_gate(result)
    gate.check("static_fairness_equal_across_arms", fairness_ok, fairness_detail)
    provider_count = sum(
        int(receipt["provider_network_call_count"])
        for receipt in (*result.parent_receipts, *result.terminal_parent_receipts)
    )
    result.provider_network_call_count = provider_count
    gate.check("provider_network_call_count_zero", provider_count == 0, str(provider_count))
    gate.check(
        "scorer_and_oracle_unloaded_before_gates",
        scorer_modules_unloaded,
        "author/oracle/scorer module imported before pre-score gates",
    )
    return gate


def _write_private_summary(result: B21RunResult, private_root: Path) -> None:
    summary = {
        "schema_version": "product_bakeoff_b21_private_summary.v1",
        "runner_version": B21_RUNNER_VERSION,
        "logical_record_count": result.logical_record_count,
        "normal_record_count": len(result.records),
        "terminal_support_record_count": len(result.terminal_support_cells),
        "normal_accepted_count": sum(record.status == "accepted" for record in result.records),
        "parent_receipt_count": len(result.parent_receipts),
        "terminal_parent_receipt_count": len(result.terminal_parent_receipts),
        "parent_receipt_failures": result.parent_receipt_failures[:20],
        "provider_network_call_count": result.provider_network_call_count,
        "runtime_seconds": result.runtime_seconds,
        "pre_score_gates_passed": bool(result.gate_result and result.gate_result.passed),
        "pre_score_gate_failures": dict(result.gate_result.failures) if result.gate_result else {},
        "repo_lock_digest": result.repo_lock["repo_lock_digest"] if result.repo_lock else None,
        "task_manifest_digest": result.task_manifest["task_manifest_digest"] if result.task_manifest else None,
        "freeze_receipt_digest": result.freeze_receipt["freeze_receipt_digest"] if result.freeze_receipt else None,
    }
    b2c.write_json(private_root / "b21_private_summary.json", summary)


def run_full_matrix(
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
    keep_worktrees: bool = False,
) -> B21RunResult:
    forbidden_modules = {
        "product_bakeoff_b2_author",
        "product_bakeoff_b2_oracle",
        "product_bakeoff_b2_scorer",
        "product_bakeoff_b21_scorer",
    }
    if forbidden_modules & set(sys.modules):
        raise B21RunError("B2.1 RUN phase began after author/oracle/scorer import")
    runs_dir = Path(runs_dir)
    if runs_dir.exists() and any(runs_dir.iterdir()):
        raise B21RunError("B2.1 runs_dir must be absent or empty")
    runs_dir.mkdir(parents=True, exist_ok=True)
    private_root = runs_dir / "private"
    work_root = runs_dir / "work"
    private_root.mkdir()
    work_root.mkdir()
    result = B21RunResult(runs_dir=str(runs_dir.resolve()))
    started = time.perf_counter()

    cli_path = b2r._find_cli()
    os.environ["OPENLOCUS_CLI"] = cli_path
    repo_lock = b2c.load_repo_lock(repo_lock_path, require_sources=True)
    task_manifest, tasks = b2c.load_task_manifest(
        task_manifest_path,
        repo_lock_digest=repo_lock["repo_lock_digest"],
    )
    binding = b2c.load_json(holdout_binding_path)
    freeze = b2c.load_json(freeze_receipt_path)
    if freeze.get("freeze_receipt_digest") != expected_freeze_digest:
        raise B21RunError("explicit expected B2.1 freeze digest does not match receipt")
    if binding.get("holdout_binding_digest") != freeze.get("holdout_binding_digest"):
        raise B21RunError("holdout binding digest does not match freeze receipt")
    freeze = validate_freeze_receipt(
        freeze,
        repo_lock_digest=repo_lock["repo_lock_digest"],
        task_manifest_digest=task_manifest["task_manifest_digest"],
        oracle_manifest_digest=freeze.get("oracle_manifest_digest", ""),
        holdout_binding_digest_value=binding["holdout_binding_digest"],
        repo_lock_path=repo_lock_path,
        task_manifest_path=task_manifest_path,
        oracle_manifest_path=oracle_manifest_path,
        holdout_binding_path=holdout_binding_path,
        excluded_repo_lock_path=excluded_repo_lock_path,
        preflight_exclusion_path=preflight_exclusion_path,
        cli_path=cli_path,
    )
    result.repo_lock = repo_lock
    result.task_manifest = task_manifest
    result.tasks = tasks
    result.freeze_receipt = freeze
    result.holdout_binding = binding

    rows = b2p.build_execution_schedule()
    schedule_errors = b2p.validate_execution_schedule(rows, b2p.build_task_slots())
    if schedule_errors or b21_execution_schedule_digest() != freeze["b21_execution_schedule_digest"]:
        raise B21RunError("B2.1 execution schedule validation/digest failed")
    expected_keys = b2r.expected_execution_keys(tasks, rows)
    if len(expected_keys) != b2p.B2_TOTAL_RECORDS or len(set(expected_keys)) != b2p.B2_TOTAL_RECORDS:
        raise B21RunError("expected B2.1 keys are not an exact 1,440-cell set")
    task_by_slot = {task.slot_id: task for task in tasks}
    repos = b2c.repo_by_slot(repo_lock)
    adapter_map = {
        adapter_id: (descriptor_factory(), hooks_factory())
        for adapter_id, descriptor_factory, hooks_factory in B2_ADAPTERS
    }
    groups = b2r._schedule_groups(rows)

    for group_index, (repo_slot, repetition, group_rows) in enumerate(groups, start=1):
        group_root = work_root / f"g{group_index:02d}_{repo_slot}_r{repetition}"
        group_root.mkdir(parents=True)
        cell_map = b2r._create_repo_rep_cells(
            group_root=group_root,
            private_root=private_root,
            repo_row=repos[repo_slot],
            repetition=repetition,
        )
        for row in group_rows:
            task = task_by_slot[row.slot_id]
            episode_id = _request_token("ep", task, repetition)
            context_id = _request_token("ctx", task, repetition)
            support_id = _request_token("sup", task, repetition)
            context_cells: dict[str, b2r.B2CellResult] = {}
            for adapter_id in row.arm_order:
                descriptor, hooks = adapter_map[adapter_id]
                cell_root, snapshot, visible_path = cell_map[adapter_id]
                request = b2r.make_b2_request(
                    task=task,
                    snapshot=snapshot,
                    repo_visible_digest=repos[repo_slot]["visible"]["manifest_digest"],
                    adapter_id=adapter_id,
                    repetition=repetition,
                    cache_state=row.cache_state,
                    operation="context",
                    episode_id=episode_id,
                    request_id=context_id,
                )
                cell = b2r._run_cell(
                    hooks=hooks,
                    descriptor=descriptor,
                    request=request,
                    snapshot=snapshot,
                    cell_root=cell_root,
                    visible_manifest_path=visible_path,
                    episode_registry=None,
                    materialize_step=1,
                )
                if row.cache_state == "cold" and cell.record.status == "accepted":
                    write_index_seal(cell_root)
                _append_normal(result, cell, descriptor, private_root)
                context_cells[adapter_id] = cell
            if task.interaction_mode != "two_step":
                continue
            for adapter_id in row.arm_order:
                descriptor, hooks = adapter_map[adapter_id]
                cell_root, snapshot, visible_path = cell_map[adapter_id]
                context = context_cells[adapter_id]
                target = _own_parent_target(context)
                support_key = (
                    adapter_id,
                    task.task_slug,
                    repetition,
                    row.cache_state,
                    (task.interaction_mode, "support"),
                )
                if target is None:
                    terminal = _make_terminal_support(
                        context_cell=context,
                        support_request_id=support_id,
                        cell_key=support_key,
                    )
                    _append_terminal(result, terminal, private_root)
                    continue
                bound_target_id = stable_target_id(target)
                output = context.capture.output
                if output is None:
                    raise B21RunError("own-parent context capture missing")
                registry = EpisodeRegistry()
                registered_id = registry.register(
                    result_id=context_id,
                    target=target,
                    snapshot=snapshot,
                    request=context.request,
                    episode_estimate_used=output.pack.budget_usage.episode_estimate_used,
                    parent_step=1,
                )
                if registered_id != bound_target_id:
                    raise B21RunError("own-parent target id drift")
                _write_lineage_receipt(
                    cell_root,
                    support_id,
                    context_id,
                    bound_target_id,
                    target.path,
                    target.start_line,
                    target.end_line,
                    snapshot.manifest_digest,
                    context.record.canonical_result_hash or "",
                    context.record.canonical_pack_hash or "",
                )
                support_request = b2r.make_b2_request(
                    task=task,
                    snapshot=snapshot,
                    repo_visible_digest=repos[repo_slot]["visible"]["manifest_digest"],
                    adapter_id=adapter_id,
                    repetition=repetition,
                    cache_state=row.cache_state,
                    operation="support",
                    episode_id=episode_id,
                    request_id=support_id,
                    parent_result_id=context_id,
                    bound_target_id=bound_target_id,
                )
                support_cell = b2r._run_cell(
                    hooks=hooks,
                    descriptor=descriptor,
                    request=support_request,
                    snapshot=snapshot,
                    cell_root=cell_root,
                    visible_manifest_path=visible_path,
                    episode_registry=registry,
                    materialize_step=2,
                )
                _append_normal(result, support_cell, descriptor, private_root)
                _clear_lineage_receipt(cell_root)
        for cell_root, _, _ in cell_map.values():
            enforce_wsr_inventory(cell_root, expected_index_sealed=True)
        print(
            f"B2.1 group {group_index}/{len(groups)} complete; logical_records={result.logical_record_count}",
            flush=True,
        )
        if not keep_worktrees:
            shutil.rmtree(group_root)

    scorer_modules_unloaded = not bool(forbidden_modules & set(sys.modules))
    result.gate_result = _check_pre_score_gates(
        result,
        expected_keys=expected_keys,
        scorer_modules_unloaded=scorer_modules_unloaded,
        freeze_valid=True,
    )
    result.runtime_seconds = time.perf_counter() - started
    _write_private_summary(result, private_root)
    return result


def run_real_repo_preflight(
    *,
    repo_row: Mapping[str, Any],
    task: b2c.B2PublicTask,
    runs_dir: Path,
) -> dict[str, Any]:
    """Exercise six-arm own-parent context/support mechanics on an unused repo."""
    if task.interaction_mode != "two_step":
        raise B21RunError("B2.1 real preflight requires a two-step task")
    runs_dir = Path(runs_dir)
    if runs_dir.exists() and any(runs_dir.iterdir()):
        raise B21RunError("B2.1 preflight runs_dir must be absent or empty")
    private_root = runs_dir / "private"
    group_root = runs_dir / "work" / "preflight_group"
    private_root.mkdir(parents=True)
    group_root.mkdir(parents=True)
    os.environ["OPENLOCUS_CLI"] = b2r._find_cli()
    adapter_map = {
        adapter_id: (descriptor_factory(), hooks_factory())
        for adapter_id, descriptor_factory, hooks_factory in B2_ADAPTERS
    }
    cell_map = b2r._create_repo_rep_cells(
        group_root=group_root,
        private_root=private_root,
        repo_row=repo_row,
        repetition=1,
    )
    result = B21RunResult(runs_dir=str(runs_dir.resolve()))
    episode_id = _request_token("probe_ep", task, 1)
    context_id = _request_token("probe_ctx", task, 1)
    support_id = _request_token("probe_sup", task, 1)
    contexts: dict[str, b2r.B2CellResult] = {}
    failures: list[str] = []
    support_statuses: dict[str, str] = {}
    target_paths: set[str] = set()
    for adapter_id in b2p.B2_ADAPTER_IDS:
        descriptor, hooks = adapter_map[adapter_id]
        cell_root, snapshot, visible_path = cell_map[adapter_id]
        request = b2r.make_b2_request(
            task=task,
            snapshot=snapshot,
            repo_visible_digest=repo_row["visible"]["manifest_digest"],
            adapter_id=adapter_id,
            repetition=1,
            cache_state="cold",
            operation="context",
            episode_id=episode_id,
            request_id=context_id,
        )
        cell = b2r._run_cell(
            hooks=hooks,
            descriptor=descriptor,
            request=request,
            snapshot=snapshot,
            cell_root=cell_root,
            visible_manifest_path=visible_path,
            episode_registry=None,
            materialize_step=1,
        )
        if cell.record.status == "accepted":
            write_index_seal(cell_root)
        _append_normal(result, cell, descriptor, private_root)
        contexts[adapter_id] = cell
        try:
            target = _own_parent_target(cell)
            if target is not None:
                target_paths.add(target.path)
        except Exception as exc:  # noqa: BLE001 - private preflight detail
            failures.append(f"{adapter_id}:context:{type(exc).__name__}")
    for adapter_id in b2p.B2_ADAPTER_IDS:
        descriptor, hooks = adapter_map[adapter_id]
        cell_root, snapshot, visible_path = cell_map[adapter_id]
        context = contexts[adapter_id]
        support_key = (
            adapter_id,
            task.task_slug,
            1,
            "cold",
            (task.interaction_mode, "support"),
        )
        try:
            target = _own_parent_target(context)
            if target is None:
                terminal = _make_terminal_support(
                    context_cell=context,
                    support_request_id=support_id,
                    cell_key=support_key,
                )
                _append_terminal(result, terminal, private_root)
                support_statuses[adapter_id] = "parent_unavailable"
                continue
            output = context.capture.output
            if output is None:
                raise B21RunError("preflight context capture missing")
            bound_target_id = stable_target_id(target)
            registry = EpisodeRegistry()
            registry.register(
                result_id=context_id,
                target=target,
                snapshot=snapshot,
                request=context.request,
                episode_estimate_used=output.pack.budget_usage.episode_estimate_used,
                parent_step=1,
            )
            _write_lineage_receipt(
                cell_root,
                support_id,
                context_id,
                bound_target_id,
                target.path,
                target.start_line,
                target.end_line,
                snapshot.manifest_digest,
                context.record.canonical_result_hash or "",
                context.record.canonical_pack_hash or "",
            )
            request = b2r.make_b2_request(
                task=task,
                snapshot=snapshot,
                repo_visible_digest=repo_row["visible"]["manifest_digest"],
                adapter_id=adapter_id,
                repetition=1,
                cache_state="cold",
                operation="support",
                episode_id=episode_id,
                request_id=support_id,
                parent_result_id=context_id,
                bound_target_id=bound_target_id,
            )
            cell = b2r._run_cell(
                hooks=hooks,
                descriptor=descriptor,
                request=request,
                snapshot=snapshot,
                cell_root=cell_root,
                visible_manifest_path=visible_path,
                episode_registry=registry,
                materialize_step=2,
            )
            _append_normal(result, cell, descriptor, private_root)
            require_scoreable(cell.record, cell.capture)
            support_output = cell.capture.output
            if support_output is None:
                raise B21RunError("preflight support capture missing")
            support_statuses[adapter_id] = support_output.pack.pack_status
            expected_status = "ready" if adapter_supports_support(adapter_id) else "no_evidence"
            if support_output.pack.pack_status != expected_status:
                raise B21RunError(f"preflight support status != {expected_status}")
            if expected_status == "ready" and not support_output.pack.support:
                raise B21RunError("support-capable preflight found no relation")
        except Exception as exc:  # noqa: BLE001 - private preflight detail
            failures.append(
                f"{adapter_id}:support:{type(exc).__name__}:{str(exc)[:160]}"
            )
        finally:
            _clear_lineage_receipt(cell_root)
    lineage_ok, lineage_detail = _same_arm_lineage_gate(result)
    fairness_ok, fairness_detail = _fairness_gate(result)
    if not lineage_ok:
        failures.append("lineage:" + lineage_detail)
    if not fairness_ok:
        failures.append("fairness:" + fairness_detail)
    provider_calls = sum(
        int(receipt["provider_network_call_count"])
        for receipt in (*result.parent_receipts, *result.terminal_parent_receipts)
    )
    if provider_calls != 0:
        failures.append(f"provider_calls={provider_calls}")
    if result.logical_record_count != 12:
        failures.append(f"logical_records={result.logical_record_count}")
    preflight = {
        "passed": not failures,
        "logical_record_count": result.logical_record_count,
        "normal_record_count": len(result.records),
        "terminal_support_record_count": len(result.terminal_support_cells),
        "normal_accepted_count": sum(record.status == "accepted" for record in result.records),
        "parent_receipt_count": len(result.parent_receipts),
        "terminal_parent_receipt_count": len(result.terminal_parent_receipts),
        "provider_network_call_count": provider_calls,
        "distinct_context_target_path_count": len(target_paths),
        "path_divergence_tolerated": len(target_paths) > 1 and not failures,
        "support_status_counts": {
            status: sum(value == status for value in support_statuses.values())
            for status in sorted(set(support_statuses.values()))
        },
        "failures": failures,
    }
    b2c.write_json(private_root / "b21_real_repo_preflight.json", preflight)
    shutil.rmtree(group_root)
    return preflight


def run_self_test() -> dict[str, Any]:
    from types import SimpleNamespace

    checks: list[tuple[str, bool]] = []
    tasks = tuple(
        b2c.B2PublicTask(
            slot_id=slot.slot_id,
            task_slug=f"b2_t{int(slot.slot_id[-2:]):02d}_{int(slot.slot_id[-2:]):012x}",
            repo_slot=slot.repo_slot,
            language=slot.language,
            size_band=slot.size_band,
            role=slot.role,
            task_family=slot.task_family,
            interaction_mode=slot.interaction_mode,
            query=("AbsentStableToken" if slot.task_family == "no_answer" else "StableToken"),
        ).validate()
        for slot in b2p.build_task_slots()
    )
    rows = b2p.build_execution_schedule()
    keys = b2r.expected_execution_keys(tasks, rows)
    groups = b2r._schedule_groups(rows)
    checks.append(("exact_logical_key_count", len(keys) == b2p.B2_TOTAL_RECORDS))
    checks.append(("logical_keys_unique", len(set(keys)) == b2p.B2_TOTAL_RECORDS))
    checks.append(("split_plot_group_count", len(groups) == 48))
    checks.append(("terminal_policy_enabled", B21_PARENT_UNAVAILABLE_POLICY["logical_support_record_still_required"]))
    targets = [
        PackTarget(0, f"src/{index % 2}.py", index + 1, index + 1)
        for index in range(len(b2p.B2_ADAPTER_IDS))
    ]
    checks.append((
        "own_parent_divergence_preserved",
        len({target.path for target in targets}) == 2
        and len({stable_target_id(target) for target in targets}) == len(targets),
    ))
    fake_payload = {
        "schema_id": "x",
        "run_cell_id": "task",
        "operation": "support",
        "request_id": "support",
        "parent_result_id": None,
        "bound_target_id": None,
    }
    checks.append(("static_digest_deterministic", _digest("b21static_", fake_payload) == _digest("b21static_", fake_payload)))
    terminal_resource = ResourceSample(
        setup_seconds=None,
        index_seconds=None,
        query_seconds=0.001,
        materialize_seconds=0.0,
        render_seconds=0.0,
        rss_bytes=1,
        cpu_seconds=0.001,
    ).validate()
    checks.append(("terminal_resource_valid", terminal_resource.rss_bytes == 1))
    cold_stub = SimpleNamespace(
        record=SimpleNamespace(adapter_id="s0", run_cell_id="task", cache_state="cold"),
        semantic_hash="context-semantic",
    )
    warm_stub = SimpleNamespace(
        record=SimpleNamespace(adapter_id="s0", run_cell_id="task", cache_state="warm"),
        semantic_hash="context-semantic",
    )
    checks.append((
        "terminal_semantics_ignore_cache_label",
        _terminal_semantic_hash(cold_stub, reason="parent_unavailable")
        == _terminal_semantic_hash(warm_stub, reason="parent_unavailable"),
    ))
    checks.append(("parent_rss_observed", _current_rss_bytes() > 0))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    try:
        b2r._schedule_groups(list(b2p.build_execution_schedule())[:-1])
        incomplete_rejected = False
    except Exception:
        incomplete_rejected = True
    checks.append(("incomplete_split_plot_group_rejected", incomplete_rejected))
    try:
        ResourceSample(
            setup_seconds=None,
            index_seconds=None,
            query_seconds=-1.0,
            materialize_seconds=0.0,
            render_seconds=0.0,
            rss_bytes=1,
            cpu_seconds=0.0,
        ).validate()
        negative_rejected = False
    except Exception:
        negative_rejected = True
    checks.append(("negative_terminal_timing_rejected", negative_rejected))
    checks.append(("cross_arm_normalization_absent", not hasattr(sys.modules[__name__], "_canonical_parent_target")))
    checks.append((
        "static_fingerprint_detects_task_drift",
        _digest("b21static_", {"query": "a"})
        != _digest("b21static_", {"query": "b"}),
    ))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B21RunError",
    "B21TerminalSupportCell",
    "B21RunResult",
    "run_real_repo_preflight",
    "run_full_matrix",
    "run_self_test",
    "run_fault_test",
]
