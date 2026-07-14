#!/usr/bin/env python3
"""B2 split-plot real-repository matrix runner (RUN phase, oracle-free)."""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

from product_bakeoff_contract import (
    AdapterDescriptor,
    AdapterHooks,
    AdapterRequest,
    BakeoffRunSpec,
    BudgetCaps,
    ContractError,
    FrozenSnapshot,
    PackTarget,
    materialize_snapshot,
    snapshot_source_visibility_digest,
)
from product_bakeoff_conformance import (
    EpisodeRegistry,
    PrivateValidatedOutputCapture,
    ValidatedRunRecord,
    require_scoreable,
    run_adapter,
    stable_target_id,
    validate_run_record,
)
from product_bakeoff_b1_spec import (
    B1_ADAPTER_VERSION,
    B1_EPISODE_ESTIMATE_CAP,
    B1_EPISODE_STEP_CAP,
    B1_INDEX_SEAL_REL,
    B1_MAX_CANDIDATES,
    B1_MAX_EVIDENCE,
    B1_MAX_RENDER_BYTES,
    B1_MAX_RENDER_CHARS,
    B1_MAX_RENDER_ESTIMATE,
    B1_MAX_SUPPORT,
    B1_MAX_TARGETS,
    B1_TIMEOUT_SECONDS,
    B1_TRANSCRIPT_DIR_REL,
    B1_WSR_REL,
    adapter_context_components,
    adapter_support_components,
    adapter_supports_support,
)
from product_bakeoff_b1_adapters import (
    _evidence_to_candidates,
    _find_cli,
    _snapshot_source_digests,
    enforce_source_immutability,
    enforce_wsr_inventory,
    initialize_b1_wsr,
    load_invocation_transcript,
    verify_index_seal,
    write_index_seal,
)
from product_bakeoff_b1_runner import (
    _b1_semantic_hash,
    _clear_lineage_receipt,
    _json_safe,
    _write_lineage_receipt,
)
from product_bakeoff_b2_adapters import (
    B2_ADAPTERS,
    B2_VISIBLE_MANIFEST_ENV,
    parse_b2_query_transcript,
)
from product_bakeoff_b2_corpus import (
    B2CorpusError,
    B2PublicTask,
    build_external_visible_manifest,
    copy_visible_snapshot,
    file_sha256,
    load_json,
    load_repo_lock,
    load_task_manifest,
    repo_by_slot,
    validate_freeze_receipt,
    write_json,
)
from product_bakeoff_b2_protocol import (
    B2_ADAPTER_IDS,
    B2_INDEX_BUILD_COUNT,
    B2_REPETITIONS,
    B2_SCHEMA_VERSION,
    B2_TOTAL_RECORDS,
    build_execution_schedule,
    build_task_slots,
    execution_schedule_digest,
    validate_execution_schedule,
)


B2_RUNNER_VERSION = "product_bakeoff_b2_runner.v1"
B2_PRIVATE_RUN_SCHEMA = "product_bakeoff_b2_private_run.v1"


class B2RunError(RuntimeError):
    """Fail-closed B2 execution error."""


def b2_caps() -> BudgetCaps:
    return BudgetCaps(
        max_candidates=B1_MAX_CANDIDATES,
        max_evidence=B1_MAX_EVIDENCE,
        max_targets=B1_MAX_TARGETS,
        max_support=B1_MAX_SUPPORT,
        max_render_chars=B1_MAX_RENDER_CHARS,
        max_render_bytes=B1_MAX_RENDER_BYTES,
        max_render_estimate=B1_MAX_RENDER_ESTIMATE,
        episode_step_cap=B1_EPISODE_STEP_CAP,
        episode_estimate_cap=B1_EPISODE_ESTIMATE_CAP,
    ).validate()


def _request_token(prefix: str, task: B2PublicTask, repetition: int) -> str:
    digest = hashlib.sha256(
        f"{prefix}|{task.slot_id}|{repetition}".encode("utf-8")
    ).hexdigest()[:12]
    return f"b2_{prefix}_{task.slot_id}_r{repetition}_{digest}"


def make_b2_request(
    *,
    task: B2PublicTask,
    snapshot: FrozenSnapshot,
    repo_visible_digest: str,
    adapter_id: str,
    repetition: int,
    cache_state: str,
    operation: str,
    episode_id: str,
    request_id: str,
    parent_result_id: str | None = None,
    bound_target_id: str | None = None,
) -> AdapterRequest:
    run_spec = BakeoffRunSpec(
        schema_id=B2_SCHEMA_VERSION,
        run_cell_id=task.task_slug,
        task=task.to_bakeoff_task(operation),
        snapshot_id=repo_visible_digest,
        source_visibility_id="b2_frozen_visible",
        snapshot_manifest_digest=snapshot.manifest_digest,
        source_visibility_digest=snapshot_source_visibility_digest(snapshot),
        visible_tree_digest=snapshot.visible_tree_digest,
        adapter_repetition=repetition,
        cache_state=cache_state,
        interaction_mode=task.interaction_mode,
        operation=operation,
        episode_id=episode_id,
        request_id=request_id,
        parent_result_id=parent_result_id,
        bound_target_id=bound_target_id,
        caps=b2_caps(),
        timeout_seconds=B1_TIMEOUT_SECONDS,
        renderer_version="harness_renderer_v4",
        materializer_version="harness_common_v4",
        budget_estimator_version="v4",
        writable_state_root_id=snapshot.writable_state_root_id,
    ).validate()
    return AdapterRequest(
        run_spec=run_spec,
        adapter_id=adapter_id,
        adapter_version=B1_ADAPTER_VERSION,
    ).validate()


@contextlib.contextmanager
def _visible_manifest_env(path: Path) -> Iterator[None]:
    old = os.environ.get(B2_VISIBLE_MANIFEST_ENV)
    os.environ[B2_VISIBLE_MANIFEST_ENV] = str(path.resolve())
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(B2_VISIBLE_MANIFEST_ENV, None)
        else:
            os.environ[B2_VISIBLE_MANIFEST_ENV] = old


@dataclass
class B2CellResult:
    record: ValidatedRunRecord
    capture: PrivateValidatedOutputCapture
    request: AdapterRequest
    cell_key: tuple[Any, ...]
    cell_root: Path
    visible_manifest_path: Path
    source_digests: dict[str, str]
    semantic_hash: str | None = None
    parent_receipt: dict[str, Any] | None = None
    parent_receipt_error: str | None = None


@dataclass
class B2GateResult:
    passed: bool = True
    failures: dict[str, str] = field(default_factory=dict)

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if not condition:
            self.failures[name] = detail or "failed"
        self.passed = self.passed and condition


@dataclass
class B2RunResult:
    records: list[ValidatedRunRecord] = field(default_factory=list)
    captures: list[PrivateValidatedOutputCapture] = field(default_factory=list)
    cells: list[B2CellResult] = field(default_factory=list)
    parent_receipts: list[dict[str, Any]] = field(default_factory=list)
    parent_receipt_failures: list[str] = field(default_factory=list)
    execution_keys: list[tuple[Any, ...]] = field(default_factory=list)
    gate_result: B2GateResult | None = None
    repo_lock: dict[str, Any] | None = None
    task_manifest: dict[str, Any] | None = None
    tasks: tuple[B2PublicTask, ...] = ()
    freeze_receipt: dict[str, Any] | None = None
    provider_network_call_count: int = 0
    runtime_seconds: float = 0.0
    runs_dir: str = ""


def _run_cell(
    *,
    hooks: AdapterHooks,
    descriptor: AdapterDescriptor,
    request: AdapterRequest,
    snapshot: FrozenSnapshot,
    cell_root: Path,
    visible_manifest_path: Path,
    episode_registry: EpisodeRegistry | None,
    materialize_step: int,
) -> B2CellResult:
    source_digests = _snapshot_source_digests(cell_root)
    capture = PrivateValidatedOutputCapture()
    with _visible_manifest_env(visible_manifest_path):
        record = run_adapter(
            hooks,
            request,
            cell_root,
            descriptor,
            snapshot,
            conformance_category="b2_real_repo_tournament",
            episode_registry=episode_registry,
            materialize_step=materialize_step,
            capture=capture,
        )
    key = (
        request.adapter_id,
        request.run_spec.run_cell_id,
        request.run_spec.adapter_repetition,
        request.run_spec.cache_state,
        (request.run_spec.interaction_mode, request.run_spec.operation),
    )
    return B2CellResult(
        record=record,
        capture=capture,
        request=request,
        cell_key=key,
        cell_root=cell_root,
        visible_manifest_path=visible_manifest_path,
        source_digests=source_digests,
    )


def _transcript_digest(root: Path, request_id: str, phase: str) -> str:
    path = root / B1_TRANSCRIPT_DIR_REL / f"{request_id}.{phase}.json"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _index_state_bytes(seal: Mapping[str, Any]) -> int:
    total = 0
    for value in seal["inventory"].values():
        if value == "directory":
            continue
        size_text, separator, _ = value.partition(":")
        if not separator or not size_text.isdigit():
            raise ContractError("index seal inventory byte count malformed")
        total += int(size_text)
    return total


def _collect_parent_receipt(
    cell: B2CellResult,
    descriptor: AdapterDescriptor,
) -> dict[str, Any]:
    request = cell.request
    root = cell.cell_root
    verify_index_seal(root)
    enforce_source_immutability(root, cell.source_digests)
    enforce_wsr_inventory(root, expected_index_sealed=True)
    lifecycle = None
    if request.run_spec.cache_state == "cold":
        lifecycle = load_invocation_transcript(request, root, "prepare")
        expected_kind = (
            "rust_index_build"
            if request.run_spec.operation == "context"
            else "local_index_seal_verify"
        )
        if lifecycle["command_kind"] != expected_kind:
            raise ContractError("B2 lifecycle transcript command mismatch")
    else:
        prepare_path = (
            root / B1_TRANSCRIPT_DIR_REL / f"{request.run_spec.request_id}.prepare.json"
        )
        if prepare_path.exists():
            raise ContractError("warm B2 request unexpectedly executed prepare")
    with _visible_manifest_env(cell.visible_manifest_path):
        query_transcript, parsed = parse_b2_query_transcript(request, root)
    if cell.record.status != "accepted" or cell.capture.output is None:
        raise ContractError("B2 parent receipt requires accepted same-execution output")
    output = cell.capture.output
    expected_candidates = ()
    provider_calls = 0
    component_receipts: list[dict[str, Any]] = []
    trace_written = False
    if parsed is not None:
        expected_candidates = _evidence_to_candidates(
            parsed.evidence,
            request.adapter_id,
            descriptor.output_channels,
            B1_MAX_CANDIDATES
            if request.run_spec.operation == "context"
            else B1_MAX_SUPPORT,
            mode=request.run_spec.operation,
        )
        provider_calls = parsed.provider.remote_calls + parsed.provider.outbound_calls
        component_receipts = [_json_safe(item) for item in parsed.receipts]
        trace_written = parsed.trace.written
    else:
        component_receipts = [dict(query_transcript["local_receipt"])]
    if tuple(output.validated_candidates) != tuple(expected_candidates):
        raise ContractError("B2 receipt/capture candidate mismatch")
    if parsed is not None and request.run_spec.operation == "support":
        bindings = output.validated_result.binding_proposal
        if bindings is None or len(bindings.support_bindings) != len(parsed.support_relations):
            raise ContractError("B2 support relation/binding mismatch")
        for binding, relation in zip(bindings.support_bindings, parsed.support_relations):
            if (
                binding.relation_kind != relation.relation_kind
                or binding.parent_target_id != request.run_spec.bound_target_id
            ):
                raise ContractError("B2 support lineage was not preserved")
    resource = cell.record.resource_sample
    if resource is None:
        raise ContractError("B2 parent receipt requires resource sample")
    if request.run_spec.cache_state == "cold":
        if resource.setup_seconds is None:
            raise ContractError("cold B2 record lacks prepare timing")
    elif resource.setup_seconds is not None or resource.index_seconds is not None:
        raise ContractError("warm B2 record carries lifecycle timing")
    semantic_hash = _b1_semantic_hash(cell.capture)
    seal = verify_index_seal(root)
    receipt = {
        "schema_version": "product_bakeoff_b2_parent_receipt.v1",
        "request_id": request.run_spec.request_id,
        "adapter_id": request.adapter_id,
        "task_slug": request.run_spec.task.task_slug,
        "operation": request.run_spec.operation,
        "cache_state": request.run_spec.cache_state,
        "adapter_repetition": request.run_spec.adapter_repetition,
        "record_fingerprint": cell.record.fingerprint,
        "canonical_result_hash": cell.record.canonical_result_hash,
        "canonical_pack_hash": cell.record.canonical_pack_hash,
        "semantic_hash": semantic_hash,
        "component_receipts": component_receipts,
        "provider_network_call_count": provider_calls,
        "trace_written": trace_written,
        "lifecycle_command_kind": lifecycle["command_kind"] if lifecycle else None,
        "index_inventory_digest": seal["inventory_digest"],
        "index_state_bytes": _index_state_bytes(seal),
        "prepare_transcript_sha256": (
            _transcript_digest(root, request.run_spec.request_id, "prepare")
            if lifecycle is not None
            else None
        ),
        "query_transcript_sha256": _transcript_digest(
            root, request.run_spec.request_id, "query"
        ),
        "capture_candidate_count": len(output.validated_candidates),
        "capture_evidence_count": len(output.evidence),
        "capture_target_count": len(output.pack.targets),
        "capture_support_count": len(output.pack.support),
    }
    cell.semantic_hash = semantic_hash
    cell.parent_receipt = receipt
    return receipt


def _persist_cell(cell: B2CellResult, private_root: Path) -> None:
    payload = {
        "schema_version": B2_PRIVATE_RUN_SCHEMA,
        "runner_version": B2_RUNNER_VERSION,
        "record": _json_safe(cell.record),
        "capture": _json_safe(cell.capture.output),
        "cell_key": _json_safe(cell.cell_key),
        "parent_receipt": cell.parent_receipt,
        "parent_receipt_error": cell.parent_receipt_error,
        "semantic_hash": cell.semantic_hash,
    }
    path = (
        private_root
        / "cells"
        / f"{cell.request.adapter_id}__{cell.request.run_spec.request_id}.json"
    )
    write_json(path, payload)


def _finish_cell(
    result: B2RunResult,
    cell: B2CellResult,
    descriptor: AdapterDescriptor,
    private_root: Path,
) -> None:
    result.records.append(cell.record)
    result.captures.append(cell.capture)
    result.cells.append(cell)
    result.execution_keys.append(cell.cell_key)
    try:
        receipt = _collect_parent_receipt(cell, descriptor)
        result.parent_receipts.append(receipt)
    except Exception as exc:  # noqa: BLE001 - converted to a pre-score gate failure
        cell.parent_receipt_error = f"{type(exc).__name__}: {exc}"
        result.parent_receipt_failures.append(
            f"{cell.request.run_spec.request_id}: {cell.parent_receipt_error}"
        )
    _persist_cell(cell, private_root)


def _create_repo_rep_cells(
    *,
    group_root: Path,
    private_root: Path,
    repo_row: Mapping[str, Any],
    repetition: int,
) -> dict[str, tuple[Path, FrozenSnapshot, Path]]:
    cells: dict[str, tuple[Path, FrozenSnapshot, Path]] = {}
    snapshot_bindings: set[tuple[str, str, str, str]] = set()
    for adapter_id in B2_ADAPTER_IDS:
        cell_root = group_root / adapter_id
        visible_files = copy_visible_snapshot(repo_row, cell_root)
        snapshot = materialize_snapshot(
            cell_root,
            visible_files,
            writable_state_root=cell_root / B1_WSR_REL,
        )
        initialize_b1_wsr(cell_root)
        external = build_external_visible_manifest(
            request_manifest_digest=snapshot.manifest_digest,
            source_visibility_digest=snapshot_source_visibility_digest(snapshot),
            visible_tree_digest=snapshot.visible_tree_digest,
            visible_files=snapshot.visible_files,
        )
        manifest_path = (
            private_root
            / "visible_manifests"
            / f"{repo_row['repo_slot']}__rep{repetition}__{adapter_id}.json"
        )
        write_json(manifest_path, external)
        cells[adapter_id] = (cell_root, snapshot, manifest_path)
        snapshot_bindings.add(
            (
                snapshot.manifest_digest,
                snapshot_source_visibility_digest(snapshot),
                snapshot.visible_tree_digest,
                snapshot.writable_state_root_id,
            )
        )
    if len(snapshot_bindings) != 1:
        raise B2RunError("arm snapshots are not byte-identical/comparable")
    return cells


def _schedule_groups(rows: Sequence[Any]) -> list[tuple[str, int, list[Any]]]:
    groups: list[tuple[str, int, list[Any]]] = []
    current_key: tuple[str, int] | None = None
    current_rows: list[Any] = []
    for row in rows:
        key = (row.repo_slot, row.repetition)
        if current_key is not None and key != current_key:
            groups.append((current_key[0], current_key[1], current_rows))
            current_rows = []
        current_key = key
        current_rows.append(row)
    if current_key is not None:
        groups.append((current_key[0], current_key[1], current_rows))
    for repo_slot, repetition, group_rows in groups:
        if len(group_rows) != 4 or [row.task_position for row in group_rows] != [1, 2, 3, 4]:
            raise B2RunError(f"schedule grouping drift for {repo_slot}/rep{repetition}")
    return groups


def expected_execution_keys(
    tasks: Sequence[B2PublicTask], rows: Sequence[Any]
) -> list[tuple[Any, ...]]:
    task_by_slot = {task.slot_id: task for task in tasks}
    keys: list[tuple[Any, ...]] = []
    for row in rows:
        task = task_by_slot[row.slot_id]
        if task.interaction_mode == "two_step":
            for adapter_id in row.arm_order:
                keys.append((
                    adapter_id, task.task_slug, row.repetition, row.cache_state,
                    (task.interaction_mode, "context"),
                ))
            for adapter_id in row.arm_order:
                keys.append((
                    adapter_id, task.task_slug, row.repetition, row.cache_state,
                    (task.interaction_mode, "support"),
                ))
            continue
        for adapter_id in row.arm_order:
            keys.append((
                adapter_id, task.task_slug, row.repetition, row.cache_state,
                (task.interaction_mode, "context"),
            ))
    return keys


def _canonical_parent_target(
    context_cells: Mapping[str, B2CellResult],
) -> PackTarget:
    """Normalize overlapping same-path context windows to their intersection."""
    if set(context_cells) != set(B2_ADAPTER_IDS):
        raise B2RunError("two-step context set does not contain all six arms")
    targets: list[PackTarget] = []
    for adapter_id in B2_ADAPTER_IDS:
        cell = context_cells[adapter_id]
        output = cell.capture.output
        if (
            cell.record.status != "accepted"
            or output is None
            or output.pack.pack_status != "ready"
            or len(output.pack.targets) != 1
        ):
            raise B2RunError("two-step context did not produce one accepted ready target")
        targets.append(output.pack.targets[0])
    paths = {target.path for target in targets}
    if len(paths) != 1:
        raise B2RunError("two-step context targets diverged across source paths")
    start = max(target.start_line for target in targets)
    end = min(target.end_line for target in targets)
    if start > end:
        raise B2RunError("two-step context target ranges have no common intersection")
    return PackTarget(
        evidence_index=0,
        path=targets[0].path,
        start_line=start,
        end_line=end,
    )


def _semantic_gate(cells: Sequence[B2CellResult]) -> tuple[bool, str]:
    by_group: dict[tuple[str, str, str], list[B2CellResult]] = defaultdict(list)
    for cell in cells:
        by_group[(
            cell.record.adapter_id,
            cell.record.run_cell_id,
            cell.record.operation,
        )].append(cell)
    failures: list[str] = []
    for key, group in by_group.items():
        if len(group) != len(B2_REPETITIONS):
            failures.append(f"{key}: observations={len(group)}")
            continue
        hashes = {cell.semantic_hash for cell in group}
        if None in hashes or len(hashes) != 1:
            failures.append(f"{key}: semantic hash drift")
        statuses = {
            (
                cell.record.status,
                cell.record.result_status,
                cell.record.pack_status,
                cell.record.failure_category,
            )
            for cell in group
        }
        if len(statuses) != 1:
            failures.append(f"{key}: semantic envelope drift")
    return (not failures, "; ".join(failures[:8]))


def _check_pre_score_gates(
    result: B2RunResult,
    *,
    expected_keys: Sequence[tuple[Any, ...]],
    scorer_modules_unloaded: bool,
    freeze_valid: bool,
) -> B2GateResult:
    gate = B2GateResult()
    records = result.records
    cells = result.cells
    gate.check(
        "private_manifests_and_runtime_frozen",
        freeze_valid,
        "freeze receipt did not bind current manifests/source/runtime",
    )
    gate.check(
        "complete_1440_record_matrix",
        len(records) == B2_TOTAL_RECORDS
        and result.execution_keys == list(expected_keys)
        and len(set(result.execution_keys)) == B2_TOTAL_RECORDS,
        f"records={len(records)} expected={B2_TOTAL_RECORDS}",
    )
    invalid_records = [
        (record.adapter_id, record.run_cell_id, validate_run_record(record))
        for record in records
        if validate_run_record(record)
    ]
    gate.check("all_run_records_valid", not invalid_records, str(invalid_records[:3]))
    gate.check(
        "all_records_accepted",
        len(records) == B2_TOTAL_RECORDS
        and all(record.status == "accepted" and record.result_status == "ok" for record in records),
        f"rejected_or_not_ok={sum(record.status != 'accepted' or record.result_status != 'ok' for record in records)}",
    )
    resource_complete = sum(
        record.resource_sample is not None
        and record.resource_sample.cpu_seconds is not None
        and record.resource_sample.rss_bytes is not None
        and record.resource_sample.query_seconds is not None
        for record in records
    )
    gate.check(
        "all_resource_samples_complete",
        resource_complete == B2_TOTAL_RECORDS,
        f"complete={resource_complete}/{B2_TOTAL_RECORDS}",
    )
    scoreable_errors: list[str] = []
    for record, capture in zip(records, result.captures):
        try:
            require_scoreable(record, capture)
        except Exception as exc:  # noqa: BLE001
            scoreable_errors.append(
                f"{record.adapter_id}/{record.run_cell_id}:{type(exc).__name__}"
            )
    gate.check("all_records_scoreable", not scoreable_errors, str(scoreable_errors[:5]))
    gate.check(
        "source_immutable_and_wsr_strict",
        len(result.parent_receipts) == B2_TOTAL_RECORDS
        and not result.parent_receipt_failures,
        str(result.parent_receipt_failures[:5]),
    )
    index_builds = sum(
        receipt["lifecycle_command_kind"] == "rust_index_build"
        for receipt in result.parent_receipts
    )
    gate.check(
        "exact_split_plot_index_build_count",
        index_builds == B2_INDEX_BUILD_COUNT,
        f"index_builds={index_builds}/{B2_INDEX_BUILD_COUNT}",
    )
    semantic_ok, semantic_detail = _semantic_gate(cells)
    gate.check("cold_warm_and_repetition_semantics_equal", semantic_ok, semantic_detail)
    fingerprints: dict[tuple[Any, ...], set[str]] = defaultdict(set)
    for cell in cells:
        fingerprints[(
            cell.record.run_cell_id,
            cell.record.adapter_repetition,
            cell.record.cache_state,
            cell.record.operation,
        )].add(cell.record.fingerprint)
    incomparable = [key for key, values in fingerprints.items() if len(values) != 1]
    gate.check("fairness_fingerprints_equal_across_arms", not incomparable, str(incomparable[:5]))
    two_step_groups: dict[tuple[str, int], dict[str, B2CellResult]] = defaultdict(dict)
    support_groups: dict[tuple[str, int], list[B2CellResult]] = defaultdict(list)
    for cell in cells:
        if cell.record.interaction_mode != "two_step":
            continue
        key = (cell.record.run_cell_id, cell.record.adapter_repetition)
        if cell.record.operation == "context":
            two_step_groups[key][cell.record.adapter_id] = cell
        else:
            support_groups[key].append(cell)
    normalization_errors: list[str] = []
    for key, contexts in two_step_groups.items():
        try:
            canonical = _canonical_parent_target(contexts)
            expected_id = stable_target_id(canonical)
            supports = support_groups.get(key, [])
            if len(supports) != len(B2_ADAPTER_IDS) or any(
                cell.request.run_spec.bound_target_id != expected_id
                for cell in supports
            ):
                normalization_errors.append(f"{key}: support parent binding drift")
        except Exception as exc:  # noqa: BLE001
            normalization_errors.append(f"{key}: {type(exc).__name__}")
    gate.check(
        "two_step_parent_intersection_normalized",
        len(two_step_groups) == 48 and not normalization_errors,
        str(normalization_errors[:5]),
    )
    lineage_errors: list[str] = []
    for cell in cells:
        if cell.record.operation != "support" or cell.capture.output is None:
            continue
        for support in cell.capture.output.pack.support:
            if support.parent_target_id != cell.request.run_spec.bound_target_id:
                lineage_errors.append(cell.request.run_spec.request_id)
                break
    gate.check("two_step_lineage_valid", not lineage_errors, str(lineage_errors[:5]))
    provider_count = sum(
        int(receipt["provider_network_call_count"])
        for receipt in result.parent_receipts
    )
    result.provider_network_call_count = provider_count
    gate.check("provider_network_call_count_zero", provider_count == 0, str(provider_count))
    gate.check(
        "scorer_and_oracle_unloaded_before_gates",
        scorer_modules_unloaded,
        "author/oracle/scorer module was imported before pre-score gates",
    )
    return gate


def _write_private_summary(result: B2RunResult, private_root: Path) -> None:
    summary = {
        "schema_version": "product_bakeoff_b2_private_summary.v1",
        "runner_version": B2_RUNNER_VERSION,
        "record_count": len(result.records),
        "accepted_count": sum(record.status == "accepted" for record in result.records),
        "rejected_count": sum(record.status == "rejected" for record in result.records),
        "parent_receipt_count": len(result.parent_receipts),
        "parent_receipt_failures": result.parent_receipt_failures[:20],
        "provider_network_call_count": result.provider_network_call_count,
        "runtime_seconds": result.runtime_seconds,
        "pre_score_gates_passed": bool(result.gate_result and result.gate_result.passed),
        "pre_score_gate_failures": (
            dict(result.gate_result.failures) if result.gate_result else {}
        ),
        "repo_lock_digest": (
            result.repo_lock["repo_lock_digest"] if result.repo_lock else None
        ),
        "task_manifest_digest": (
            result.task_manifest["task_manifest_digest"]
            if result.task_manifest
            else None
        ),
        "freeze_receipt_digest": (
            result.freeze_receipt["freeze_receipt_digest"]
            if result.freeze_receipt
            else None
        ),
    }
    write_json(private_root / "b2_private_summary.json", summary)


def run_real_repo_preflight(
    *,
    repo_row: Mapping[str, Any],
    task: B2PublicTask,
    runs_dir: Path,
) -> dict[str, Any]:
    """Six-arm cold context/support mechanics probe on a non-tournament repo."""
    if task.interaction_mode != "two_step":
        raise B2RunError("real-repo preflight requires a two-step task")
    runs_dir = Path(runs_dir)
    if runs_dir.exists() and any(runs_dir.iterdir()):
        raise B2RunError("preflight runs_dir must be absent or empty")
    private_root = runs_dir / "private"
    group_root = runs_dir / "work" / "preflight_group"
    private_root.mkdir(parents=True)
    group_root.mkdir(parents=True)
    os.environ["OPENLOCUS_CLI"] = _find_cli()
    adapter_map = {
        adapter_id: (descriptor_factory(), hooks_factory())
        for adapter_id, descriptor_factory, hooks_factory in B2_ADAPTERS
    }
    cell_map = _create_repo_rep_cells(
        group_root=group_root,
        private_root=private_root,
        repo_row=repo_row,
        repetition=1,
    )
    aggregate = B2RunResult(runs_dir=str(runs_dir.resolve()))
    context_cells: dict[str, B2CellResult] = {}
    support_statuses: dict[str, str] = {}
    failures: list[str] = []
    episode_id = _request_token("probe_ep", task, 1)
    context_id = _request_token("probe_ctx", task, 1)
    support_id = _request_token("probe_sup", task, 1)
    for adapter_id in B2_ADAPTER_IDS:
        descriptor, hooks = adapter_map[adapter_id]
        cell_root, snapshot, visible_path = cell_map[adapter_id]
        context_request = make_b2_request(
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
        context_cell = _run_cell(
            hooks=hooks,
            descriptor=descriptor,
            request=context_request,
            snapshot=snapshot,
            cell_root=cell_root,
            visible_manifest_path=visible_path,
            episode_registry=None,
            materialize_step=1,
        )
        if context_cell.record.status == "accepted":
            write_index_seal(cell_root)
        _finish_cell(aggregate, context_cell, descriptor, private_root)
        try:
            require_scoreable(context_cell.record, context_cell.capture)
            context_cells[adapter_id] = context_cell
        except Exception as exc:  # noqa: BLE001 - private probe detail only
            failures.append(f"{adapter_id}:{type(exc).__name__}:{exc}")
    canonical_target: PackTarget | None = None
    try:
        canonical_target = _canonical_parent_target(context_cells)
    except Exception as exc:  # noqa: BLE001 - private probe detail only
        failures.append(f"canonical_parent:{type(exc).__name__}:{exc}")
    if canonical_target is not None:
        bound_target_id = stable_target_id(canonical_target)
        for adapter_id in B2_ADAPTER_IDS:
            descriptor, hooks = adapter_map[adapter_id]
            cell_root, snapshot, visible_path = cell_map[adapter_id]
            context_cell = context_cells[adapter_id]
            context_output = context_cell.capture.output
            if context_output is None:
                failures.append(f"{adapter_id}:missing context capture")
                continue
            registry = EpisodeRegistry()
            registry.register(
                result_id=context_id,
                target=canonical_target,
                snapshot=snapshot,
                request=context_cell.request,
                episode_estimate_used=context_output.pack.budget_usage.episode_estimate_used,
                parent_step=1,
            )
            try:
                _write_lineage_receipt(
                    cell_root,
                    support_id,
                    context_id,
                    bound_target_id,
                    canonical_target.path,
                    canonical_target.start_line,
                    canonical_target.end_line,
                    snapshot.manifest_digest,
                    context_cell.record.canonical_result_hash or "",
                    context_cell.record.canonical_pack_hash or "",
                )
                support_request = make_b2_request(
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
                support_cell = _run_cell(
                    hooks=hooks,
                    descriptor=descriptor,
                    request=support_request,
                    snapshot=snapshot,
                    cell_root=cell_root,
                    visible_manifest_path=visible_path,
                    episode_registry=registry,
                    materialize_step=2,
                )
                _finish_cell(aggregate, support_cell, descriptor, private_root)
                require_scoreable(support_cell.record, support_cell.capture)
                support_output = support_cell.capture.output
                if support_output is None:
                    raise ContractError("preflight support capture missing")
                support_statuses[adapter_id] = support_output.pack.pack_status
                expected_status = (
                    "ready" if adapter_supports_support(adapter_id) else "no_evidence"
                )
                if support_output.pack.pack_status != expected_status:
                    raise ContractError(f"preflight support status != {expected_status}")
                if expected_status == "ready" and not support_output.pack.support:
                    raise ContractError("support-capable preflight found no relation")
            except Exception as exc:  # noqa: BLE001 - private probe detail only
                failures.append(f"{adapter_id}:{type(exc).__name__}:{exc}")
            finally:
                _clear_lineage_receipt(cell_root)
    if aggregate.parent_receipt_failures:
        failures.extend(aggregate.parent_receipt_failures[:6])
    provider_calls = sum(
        int(receipt["provider_network_call_count"])
        for receipt in aggregate.parent_receipts
    )
    if provider_calls != 0:
        failures.append(f"provider calls={provider_calls}")
    result = {
        "passed": not failures,
        "record_count": len(aggregate.records),
        "accepted_count": sum(record.status == "accepted" for record in aggregate.records),
        "parent_receipt_count": len(aggregate.parent_receipts),
        "provider_network_call_count": provider_calls,
        "context_target_converged": canonical_target is not None,
        "support_status_counts": {
            status: sum(value == status for value in support_statuses.values())
            for status in sorted(set(support_statuses.values()))
        },
        "failures": failures,
    }
    write_json(private_root / "b2_real_repo_preflight.json", result)
    shutil.rmtree(group_root)
    return result


def run_full_matrix(
    *,
    repo_lock_path: Path,
    task_manifest_path: Path,
    oracle_manifest_path: Path,
    freeze_receipt_path: Path,
    expected_freeze_digest: str,
    runs_dir: Path,
    keep_worktrees: bool = False,
) -> B2RunResult:
    """Execute the exact frozen 1,440-record matrix without loading labels."""
    forbidden_modules = {
        "product_bakeoff_b2_author",
        "product_bakeoff_b2_oracle",
        "product_bakeoff_b2_scorer",
    }
    if forbidden_modules & set(sys.modules):
        raise B2RunError("B2 RUN phase began after an author/oracle/scorer import")
    runs_dir = Path(runs_dir)
    if runs_dir.exists() and any(runs_dir.iterdir()):
        raise B2RunError("B2 runs_dir must be absent or empty (no selective resume/rerun)")
    runs_dir.mkdir(parents=True, exist_ok=True)
    private_root = runs_dir / "private"
    work_root = runs_dir / "work"
    private_root.mkdir()
    work_root.mkdir()
    result = B2RunResult(runs_dir=str(runs_dir.resolve()))
    started = time.perf_counter()

    cli_path = _find_cli()
    os.environ["OPENLOCUS_CLI"] = cli_path
    repo_lock = load_repo_lock(repo_lock_path, require_sources=True)
    task_manifest, tasks = load_task_manifest(
        task_manifest_path, repo_lock_digest=repo_lock["repo_lock_digest"]
    )
    freeze = load_json(freeze_receipt_path)
    if freeze.get("freeze_receipt_digest") != expected_freeze_digest:
        raise B2RunError("explicit expected freeze digest does not match receipt")
    freeze = validate_freeze_receipt(
        freeze,
        repo_lock_digest=repo_lock["repo_lock_digest"],
        task_manifest_digest_value=task_manifest["task_manifest_digest"],
        oracle_manifest_digest=freeze.get("oracle_manifest_digest", ""),
        repo_lock_path=repo_lock_path,
        task_manifest_path=task_manifest_path,
        oracle_manifest_path=oracle_manifest_path,
        cli_path=cli_path,
    )
    result.repo_lock = repo_lock
    result.task_manifest = task_manifest
    result.tasks = tasks
    result.freeze_receipt = freeze

    rows = build_execution_schedule()
    schedule_errors = validate_execution_schedule(rows, build_task_slots())
    if schedule_errors or execution_schedule_digest(rows) != freeze["execution_schedule_digest"]:
        raise B2RunError("execution schedule validation/digest failed")
    expected_keys = expected_execution_keys(tasks, rows)
    if len(expected_keys) != B2_TOTAL_RECORDS or len(set(expected_keys)) != B2_TOTAL_RECORDS:
        raise B2RunError("expected B2 execution keys are not an exact 1,440-cell set")
    task_by_slot = {task.slot_id: task for task in tasks}
    repos = repo_by_slot(repo_lock)
    adapter_map = {
        adapter_id: (descriptor_factory(), hooks_factory())
        for adapter_id, descriptor_factory, hooks_factory in B2_ADAPTERS
    }
    groups = _schedule_groups(rows)

    for group_index, (repo_slot, repetition, group_rows) in enumerate(groups, start=1):
        group_root = work_root / f"g{group_index:02d}_{repo_slot}_r{repetition}"
        group_root.mkdir(parents=True)
        cell_map = _create_repo_rep_cells(
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
            context_cells: dict[str, B2CellResult] = {}
            for adapter_id in row.arm_order:
                descriptor, hooks = adapter_map[adapter_id]
                cell_root, snapshot, visible_path = cell_map[adapter_id]
                context_request = make_b2_request(
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
                context_cell = _run_cell(
                    hooks=hooks,
                    descriptor=descriptor,
                    request=context_request,
                    snapshot=snapshot,
                    cell_root=cell_root,
                    visible_manifest_path=visible_path,
                    episode_registry=None,
                    materialize_step=1,
                )
                if row.cache_state == "cold" and context_cell.record.status == "accepted":
                    write_index_seal(cell_root)
                _finish_cell(result, context_cell, descriptor, private_root)
                context_cells[adapter_id] = context_cell
            if task.interaction_mode != "two_step":
                continue
            canonical_target = _canonical_parent_target(context_cells)
            bound_target_id = stable_target_id(canonical_target)
            for adapter_id in row.arm_order:
                descriptor, hooks = adapter_map[adapter_id]
                cell_root, snapshot, visible_path = cell_map[adapter_id]
                context_cell = context_cells[adapter_id]
                context_output = context_cell.capture.output
                if context_output is None:
                    raise B2RunError("canonical two-step context capture is missing")
                registry = EpisodeRegistry()
                registered_id = registry.register(
                    result_id=context_id,
                    target=canonical_target,
                    snapshot=snapshot,
                    request=context_cell.request,
                    episode_estimate_used=(
                        context_output.pack.budget_usage.episode_estimate_used
                    ),
                    parent_step=1,
                )
                if registered_id != bound_target_id:
                    raise B2RunError("canonical parent target id drift")
                _write_lineage_receipt(
                    cell_root,
                    support_id,
                    context_id,
                    bound_target_id,
                    canonical_target.path,
                    canonical_target.start_line,
                    canonical_target.end_line,
                    snapshot.manifest_digest,
                    context_cell.record.canonical_result_hash or "",
                    context_cell.record.canonical_pack_hash or "",
                )
                support_request = make_b2_request(
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
                support_cell = _run_cell(
                    hooks=hooks,
                    descriptor=descriptor,
                    request=support_request,
                    snapshot=snapshot,
                    cell_root=cell_root,
                    visible_manifest_path=visible_path,
                    episode_registry=registry,
                    materialize_step=2,
                )
                _finish_cell(result, support_cell, descriptor, private_root)
                _clear_lineage_receipt(cell_root)
        for cell_root, _, _ in cell_map.values():
            enforce_wsr_inventory(cell_root, expected_index_sealed=True)
        print(
            f"B2 group {group_index}/{len(groups)} complete; records={len(result.records)}",
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


def run_self_test() -> dict[str, Any]:
    from types import SimpleNamespace

    checks: list[tuple[str, bool]] = []
    tasks = tuple(
        B2PublicTask(
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
        for slot in build_task_slots()
    )
    rows = build_execution_schedule()
    keys = expected_execution_keys(tasks, rows)
    groups = _schedule_groups(rows)
    checks.append(("exact_key_count", len(keys) == B2_TOTAL_RECORDS))
    checks.append(("keys_unique", len(set(keys)) == B2_TOTAL_RECORDS))
    checks.append(("split_plot_groups", len(groups) == 48))
    checks.append(("four_rows_per_group", all(len(group[2]) == 4 for group in groups)))
    context_stubs = {
        adapter_id: SimpleNamespace(
            record=SimpleNamespace(status="accepted"),
            capture=SimpleNamespace(
                output=SimpleNamespace(
                    pack=SimpleNamespace(
                        pack_status="ready",
                        targets=(PackTarget(0, "src/a.py", 2 + index % 2, 6 - index % 2),),
                    )
                )
            ),
        )
        for index, adapter_id in enumerate(B2_ADAPTER_IDS)
    }
    canonical = _canonical_parent_target(context_stubs)
    checks.append((
        "two_step_parent_intersection",
        (canonical.path, canonical.start_line, canonical.end_line) == ("src/a.py", 3, 5),
    ))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


def run_fault_test() -> dict[str, Any]:
    from types import SimpleNamespace

    checks: list[tuple[str, bool]] = []
    rows = list(build_execution_schedule())
    broken = rows[:-1]
    try:
        _schedule_groups(broken)
        broken_rejected = False
    except B2RunError:
        broken_rejected = True
    checks.append(("incomplete_group_rejected", broken_rejected))
    divergent = {
        adapter_id: SimpleNamespace(
            record=SimpleNamespace(status="accepted"),
            capture=SimpleNamespace(
                output=SimpleNamespace(
                    pack=SimpleNamespace(
                        pack_status="ready",
                        targets=(PackTarget(0, f"src/{index}.py", 1, 1),),
                    )
                )
            ),
        )
        for index, adapter_id in enumerate(B2_ADAPTER_IDS)
    }
    try:
        _canonical_parent_target(divergent)
        divergent_rejected = False
    except B2RunError:
        divergent_rejected = True
    checks.append(("divergent_parent_paths_rejected", divergent_rejected))
    failed = [name for name, passed in checks if not passed]
    return {
        "passed": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "failed": failed,
    }


__all__ = [
    "B2RunError", "B2CellResult", "B2GateResult", "B2RunResult",
    "b2_caps", "make_b2_request", "expected_execution_keys",
    "run_real_repo_preflight", "run_full_matrix", "run_self_test", "run_fault_test",
]
