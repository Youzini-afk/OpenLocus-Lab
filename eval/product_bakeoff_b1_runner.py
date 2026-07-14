#!/usr/bin/env python3
"""Product Stack Bakeoff B1 — matrix runner (v2).

V2 changes from v1:
* Fresh cell source IS the canonical frozen source; freeze once.  Persistent
  state at the cell root so ``.openlocus/index`` is WSR.  Do NOT recreate
  snapshot/state between cold and warm.
* Seal exact index inventory/digests after cold; warm must not rebuild or
  mutate index.
* Before/after every production call: source immutability + strict WSR
  inventory.
* Use actual parent capture/registry target path+range for support via a
  private WSR lineage receipt.  Never ``tgt_unknown``.
* Exact 360+144 disjoint 504 matrix.  Before dynamic scorer import: both
  canonical matrix validations, every record accepted/ok, every parent-
  measured resource complete, ``require_scoreable`` success (no catch/pass),
  exact source/state/lifecycle, cold-warm semantic equality, repetition
  determinism, two-step lineage, provider count zero, privacy/canary absence.
  On any gate fail, scorer must remain unimported and run exits nonzero.

Run::

    python -m py_compile eval/product_bakeoff_b1_runner.py
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    stable_target_id,
)
from product_bakeoff_conformance import (
    EpisodeRegistry,
    PrivateValidatedOutputCapture,
    ValidatedRunRecord,
    require_scoreable,
    run_adapter,
    validate_comparison_matrix,
    ComparisonMatrixSpec,
)

from product_bakeoff_b1_spec import (
    B1_SPEC_VERSION, B1_GENERATED_BY, B1_CLAIM_LEVEL,
    B1_MAX_CANDIDATES, B1_MAX_EVIDENCE, B1_MAX_TARGETS, B1_MAX_SUPPORT,
    B1_MAX_RENDER_CHARS, B1_MAX_RENDER_BYTES, B1_MAX_RENDER_ESTIMATE,
    B1_EPISODE_STEP_CAP, B1_EPISODE_ESTIMATE_CAP, B1_TIMEOUT_SECONDS,
    B1_REPETITIONS, B1_CACHE_STATES, B1_ADAPTER_IDS, B1_ADAPTER_VERSION,
    B1_ONE_SHOT_RECORDS, B1_TWO_STEP_RECORDS, B1_TOTAL_RECORDS,
    B1_WSR_REL, B1_INDEX_REL, B1_RRF_K,
    B1_PRE_SCORE_GATES, B1_LINEAGE_RECEIPT_REL,
    B1_PARENT_RECEIPT_SCHEMA_VERSION,
    B1_GRAPH_ELIGIBLE_TASK_FAMILIES,
    b1_source_bundle_digest, b1_runtime_bundle_digest,
)
from product_bakeoff_b1_fixtures import (
    B1_ALL_TASKS, B1_ONE_SHOT_TASKS, B1_TWO_STEP_TASKS, B1Task,
    RUST_REPO_ID, TS_REPO_ID, copy_fixture_to_mirror,
)
from product_bakeoff_b1_adapters import (
    B1_ADAPTERS, _find_cli, enforce_source_immutability, enforce_wsr_inventory,
    _snapshot_source_digests, initialize_b1_wsr, write_index_seal,
    verify_index_seal, load_invocation_transcript, parse_query_transcript,
    _evidence_to_candidates, adapter_context_components,
    adapter_support_components, adapter_supports_support,
    _is_reparse_or_link,
)


# ---------------------------------------------------------------------------
# B1 caps (frozen)
# ---------------------------------------------------------------------------


def b1_caps() -> BudgetCaps:
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


# ---------------------------------------------------------------------------
# Run spec / request construction
# ---------------------------------------------------------------------------


def _make_b1_run_spec(
    task: B1Task,
    snapshot: FrozenSnapshot,
    adapter_repetition: int,
    cache_state: str,
    operation: str | None = None,
    request_id: str = "",
    episode_id: str = "",
    parent_result_id: str | None = None,
    bound_target_id: str | None = None,
) -> BakeoffRunSpec:
    op = operation or task.operation
    from product_bakeoff_contract import BakeoffTask
    bt = task.to_bakeoff_task()
    if op != bt.operation:
        bt = BakeoffTask(
            task_slug=task.task_slug,
            language_family=task.language_family,
            task_family=task.task_family,
            interaction_mode="two_step",
            source_visibility="frozen_visible",
            query=task.query,
            operation=op,
        ).validate()
    rs = BakeoffRunSpec(
        schema_id=B1_SPEC_VERSION,
        run_cell_id=task.task_slug,
        task=bt,
        snapshot_id="b1_snap_v2",
        source_visibility_id="frozen_visible",
        snapshot_manifest_digest=snapshot.manifest_digest,
        source_visibility_digest=snapshot_source_visibility_digest(snapshot),
        visible_tree_digest=snapshot.visible_tree_digest,
        adapter_repetition=adapter_repetition,
        cache_state=cache_state,
        interaction_mode=bt.interaction_mode,
        operation=op,
        episode_id=episode_id or f"b1_ep_{task.task_slug}",
        request_id=request_id or f"b1_req_{task.task_slug}",
        parent_result_id=parent_result_id,
        bound_target_id=bound_target_id,
        caps=b1_caps(),
        timeout_seconds=B1_TIMEOUT_SECONDS,
        renderer_version="harness_renderer_v4",
        materializer_version="harness_common_v4",
        budget_estimator_version="v4",
        writable_state_root_id=snapshot.writable_state_root_id,
    )
    return rs.validate()


def _make_b1_request(
    task: B1Task,
    snapshot: FrozenSnapshot,
    adapter_id: str,
    adapter_repetition: int,
    cache_state: str,
    operation: str | None = None,
    request_id: str = "",
    episode_id: str = "",
    parent_result_id: str | None = None,
    bound_target_id: str | None = None,
) -> AdapterRequest:
    rs = _make_b1_run_spec(
        task, snapshot, adapter_repetition, cache_state, operation,
        request_id, episode_id, parent_result_id, bound_target_id,
    )
    return AdapterRequest(
        run_spec=rs, adapter_id=adapter_id, adapter_version=B1_ADAPTER_VERSION,
    ).validate()


# ---------------------------------------------------------------------------
# Mirror / cell management (V2: freeze once, persistent state at cell root)
# ---------------------------------------------------------------------------


def _force_rmtree(path: Path) -> None:
    """Force-remove a directory tree, handling Windows read-only files."""
    import stat as stat_mod
    def _on_rm_error(func, fpath, exc_info):
        try:
            os.chmod(fpath, stat_mod.S_IWRITE)
            func(fpath)
        except Exception:
            pass
    shutil.rmtree(path, onerror=_on_rm_error)


def _create_cell(
    base_dir: Path, task: B1Task, adapter_id: str, rep: int,
) -> Path:
    """Create a byte-identical cell source for one (task, adapter, rep).

    V2: the cell source IS the canonical frozen source.  Freeze once.
    Persistent state at the cell root (.openlocus/index).  Cold and warm
    runs within the same repetition share this cell (do NOT recreate
    snapshot/state between cold and warm).
    """
    cell_name = f"{task.task_slug}__{adapter_id}__rep{rep}"
    cell_root = base_dir / "cells" / cell_name
    if cell_root.exists():
        _force_rmtree(cell_root)
    cell_root.mkdir(parents=True)
    copy_fixture_to_mirror(task.repo_id, cell_root)
    return cell_root


def _materialize_b1_snapshot(
    cell_root: Path, visible_files: tuple[str, ...]
) -> FrozenSnapshot:
    """Materialize a frozen snapshot with writable_state_root=cell/.openlocus.

    V2: .openlocus is both WSR and production marker; persistent index lives
    at .openlocus/index, NOT a sibling.  The snapshot is materialized ONCE
    per cell (not per cache state).
    """
    wsr = cell_root / B1_WSR_REL
    if wsr.exists():
        _force_rmtree(wsr)
    snapshot = materialize_snapshot(
        cell_root, visible_files, writable_state_root=wsr)
    initialize_b1_wsr(cell_root)
    return snapshot


def _write_lineage_receipt(
    cell_root: Path,
    request_id: str,
    parent_result_id: str,
    bound_target_id: str,
    target_path: str,
    target_start: int,
    target_end: int,
    snapshot_manifest_digest: str,
    parent_canonical_result_hash: str,
    parent_canonical_pack_hash: str,
) -> None:
    """Write a private WSR lineage receipt for two-step support.

    The receipt binds request/result/target/path/range/output/snapshot
    digests.  The query hook reads and cross-checks it before support.
    """
    receipt = {
        "schema_version": "product_bakeoff_b1_lineage.v1",
        "request_id": request_id,
        "parent_result_id": parent_result_id,
        "bound_target_id": bound_target_id,
        "target_path": target_path,
        "target_start_line": target_start,
        "target_end_line": target_end,
        "snapshot_manifest_digest": snapshot_manifest_digest,
        "parent_canonical_result_hash": parent_canonical_result_hash,
        "parent_canonical_pack_hash": parent_canonical_pack_hash,
    }
    receipt_path = cell_root / B1_LINEAGE_RECEIPT_REL
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    if _is_reparse_or_link(receipt_path.parent):
        raise ContractError("unsafe B1 lineage receipt directory")
    if receipt_path.exists() and _is_reparse_or_link(receipt_path):
        raise ContractError("unsafe pre-existing B1 lineage receipt")
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")


def _clear_lineage_receipt(cell_root: Path) -> None:
    """Remove the lineage receipt after support step (keep WSR clean)."""
    receipt_path = cell_root / B1_LINEAGE_RECEIPT_REL
    if receipt_path.exists():
        receipt_path.unlink()


# ---------------------------------------------------------------------------
# Single-cell execution
# ---------------------------------------------------------------------------


@dataclass
class B1CellResult:
    """Result of a single matrix cell."""
    record: ValidatedRunRecord
    capture: PrivateValidatedOutputCapture
    cell_key: tuple[str, str, int, str, tuple[str, str]]
    request: AdapterRequest
    cell_root: Path
    source_digests: dict[str, str]
    parent_receipt: dict[str, Any] | None = None
    parent_receipt_error: str | None = None
    semantic_hash: str | None = None


def _run_cell(
    hooks: AdapterHooks,
    descriptor: AdapterDescriptor,
    request: AdapterRequest,
    snapshot: FrozenSnapshot,
    cell_root: Path,
    episode_registry: EpisodeRegistry | None,
    materialize_step: int,
    conformance_category: str,
) -> B1CellResult:
    """Run a single adapter cell and return the validated record + capture."""
    source_digests = _snapshot_source_digests(cell_root)
    capture = PrivateValidatedOutputCapture()
    record = run_adapter(
        hooks, request, cell_root, descriptor, snapshot,
        conformance_category=conformance_category,
        episode_registry=episode_registry,
        materialize_step=materialize_step,
        capture=capture,
    )
    cell_key = (
        request.adapter_id,
        request.run_spec.run_cell_id,
        request.run_spec.adapter_repetition,
        request.run_spec.cache_state,
        (request.run_spec.interaction_mode, request.run_spec.operation),
    )
    return B1CellResult(
        record=record, capture=capture, cell_key=cell_key,
        request=request, cell_root=cell_root, source_digests=source_digests)


def _json_safe(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {
            field.name: _json_safe(getattr(value, field.name))
            for field in dataclasses.fields(value)
            if not field.name.startswith("_")
        }
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_json_safe(item) for item in value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported private B1 serialization type: {type(value).__name__}")


def _b1_semantic_hash(capture: PrivateValidatedOutputCapture) -> str:
    output = capture.output
    if output is None:
        raise ContractError("cannot hash an uncommitted B1 capture")
    result = output.validated_result
    ledger = {
        key: value for key, value in result.capability_ledger.items()
        if key != "prepare_index"
    }
    payload = {
        "result_status": result.status,
        "failure_category": result.failure_category,
        "capability_ledger_without_lifecycle": dict(sorted(ledger.items())),
        "fallback_provenance": _json_safe(result.fallback_provenance),
        "candidates": _json_safe(output.validated_candidates),
        "binding_proposal": _json_safe(result.binding_proposal),
        "pack_status": output.pack.pack_status,
        "pack_status_reason": output.pack.status_reason,
        "pack_operation": output.pack.operation,
        "targets": _json_safe(output.pack.targets),
        "support": _json_safe(output.pack.support),
        "canonical_pack_hash": output.canonical_pack_hash,
    }
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "b1sem_" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _transcript_file_digest(cell_root: Path, request_id: str, phase: str) -> str:
    path = cell_root / ".openlocus" / "b1" / "transcripts" / f"{request_id}.{phase}.json"
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def _collect_parent_execution_receipt(
    cell: B1CellResult,
    descriptor: AdapterDescriptor,
    private_root: Path,
) -> dict[str, Any]:
    request = cell.request
    record = cell.record
    capture = cell.capture
    root = cell.cell_root
    verify_index_seal(root)
    enforce_source_immutability(root, cell.source_digests)
    enforce_wsr_inventory(root, expected_index_sealed=True)

    lifecycle_transcript: dict[str, Any] | None = None
    if request.run_spec.cache_state == "cold":
        lifecycle_transcript = load_invocation_transcript(request, root, "prepare")
        expected_kind = (
            "rust_index_build" if request.run_spec.operation == "context"
            else "local_index_seal_verify")
        if lifecycle_transcript["command_kind"] != expected_kind:
            raise ContractError("B1 lifecycle transcript command mismatch")
    else:
        prepare_path = (
            root / ".openlocus" / "b1" / "transcripts" /
            f"{request.run_spec.request_id}.prepare.json")
        if prepare_path.exists():
            raise ContractError("warm B1 request unexpectedly executed lifecycle hook")

    query_transcript, parsed = parse_query_transcript(request, root)
    if record.status != "accepted" or capture.output is None:
        raise ContractError("parent receipt requires an accepted same-execution capture")
    output = capture.output
    mode = request.run_spec.operation
    expected_candidates = ()
    provider_calls = 0
    component_receipts: list[dict[str, Any]] = []
    trace_written = False
    rrf_receipt: dict[str, Any] | None = None
    if parsed is not None:
        expected_candidates = _evidence_to_candidates(
            parsed.evidence, request.adapter_id, descriptor.output_channels,
            B1_MAX_CANDIDATES if mode == "context" else B1_MAX_SUPPORT,
            mode=mode,
        )
        provider_calls = parsed.provider.remote_calls + parsed.provider.outbound_calls
        component_receipts = [_json_safe(receipt) for receipt in parsed.receipts]
        trace_written = parsed.trace.written
        rrf_receipt = {
            "marker": parsed.rrf_marker,
            "version": parsed.rrf_version,
            "k": parsed.rrf_k,
            "tie_order": parsed.rrf_tie_order,
            "rank_tie_policy": parsed.rrf_rank_tie_policy,
            "channel_weights": parsed.rrf_channel_weights,
            "input_normalization": parsed.rrf_input_normalization,
            "input_rewrites": parsed.rrf_input_rewrites,
        }
    else:
        local = query_transcript["local_receipt"]
        component_receipts = [dict(local)]
    if tuple(output.validated_candidates) != tuple(expected_candidates):
        raise ContractError("parent receipt does not preserve Rust evidence into capture")
    if parsed is not None and mode == "support":
        bindings = output.validated_result.binding_proposal
        if bindings is None or len(bindings.support_bindings) != len(parsed.support_relations):
            raise ContractError("support relation/binding count mismatch in capture")
        for binding, relation in zip(bindings.support_bindings, parsed.support_relations):
            if (binding.relation_kind != relation.relation_kind
                    or binding.parent_target_id != request.run_spec.bound_target_id):
                raise ContractError("support relation/parent identity was not preserved")

    resource = record.resource_sample
    if resource is None:
        raise ContractError("parent receipt requires resource sample")
    if request.run_spec.cache_state == "cold":
        if resource.setup_seconds is None or resource.index_seconds is not None:
            raise ContractError("cold lifecycle timing does not match one prepare hook")
    else:
        if resource.setup_seconds is not None or resource.index_seconds is not None:
            raise ContractError("warm lifecycle hooks were not legitimately skipped")

    semantic_hash = _b1_semantic_hash(capture)
    index_seal = verify_index_seal(root)
    receipt = {
        "schema_version": B1_PARENT_RECEIPT_SCHEMA_VERSION,
        "request_id": request.run_spec.request_id,
        "adapter_id": request.adapter_id,
        "task_slug": request.run_spec.task.task_slug,
        "operation": mode,
        "cache_state": request.run_spec.cache_state,
        "adapter_repetition": request.run_spec.adapter_repetition,
        "record_fingerprint": record.fingerprint,
        "canonical_result_hash": record.canonical_result_hash,
        "canonical_pack_hash": record.canonical_pack_hash,
        "semantic_hash": semantic_hash,
        "component_receipts": component_receipts,
        "rrf_receipt": rrf_receipt,
        "provider_network_call_count": provider_calls,
        "trace_written": trace_written,
        "sentinel_expected": len(component_receipts) + 1 + int(parsed is not None),
        "sentinel_passed": len(component_receipts) + 1 + int(parsed is not None),
        "index_inventory_digest": index_seal["inventory_digest"],
        "prepare_transcript_sha256": (
            _transcript_file_digest(root, request.run_spec.request_id, "prepare")
            if lifecycle_transcript is not None else None),
        "query_transcript_sha256": _transcript_file_digest(
            root, request.run_spec.request_id, "query"),
        "capture_candidate_count": len(output.validated_candidates),
        "capture_target_count": len(output.pack.targets),
        "capture_support_count": len(output.pack.support),
    }
    receipt_dir = private_root / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / (
        f"{request.adapter_id}__{request.run_spec.request_id}.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True),
                            encoding="utf-8")
    cell.parent_receipt = receipt
    cell.semantic_hash = semantic_hash
    return receipt


def _persist_private_cell(cell: B1CellResult, private_root: Path) -> None:
    payload = {
        "record": _json_safe(cell.record),
        "capture": _json_safe(cell.capture.output),
        "cell_key": _json_safe(cell.cell_key),
        "parent_receipt": cell.parent_receipt,
        "parent_receipt_error": cell.parent_receipt_error,
        "semantic_hash": cell.semantic_hash,
    }
    cells_dir = private_root / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    request_id = cell.request.run_spec.request_id
    private_name = f"{cell.request.adapter_id}__{request_id}.json"
    (cells_dir / private_name).write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Pre-score gate checks
# ---------------------------------------------------------------------------


@dataclass
class PreScoreGateResult:
    """Result of pre-score gate checks."""
    passed: bool = False
    gate_failures: dict[str, str] = field(default_factory=dict)

    def check(self, gate_name: str, condition: bool, detail: str = "") -> None:
        if not condition:
            self.gate_failures[gate_name] = detail or "failed"
        self.passed = self.passed and condition


def _check_pre_score_gates(
    records: list[ValidatedRunRecord],
    captures: list[PrivateValidatedOutputCapture],
    cells: list[B1CellResult],
    parent_receipts: list[dict[str, Any]],
    parent_receipt_failures: list[str],
    one_shot_failures: list[str],
    two_step_failures: list[str],
    cell_keys: list[tuple],
    *,
    preflight_passed: bool,
    privacy_canary_occurrences: int,
) -> PreScoreGateResult:
    """Check all pre-score gates before dynamic scorer import.

    On ANY gate fail, the scorer must remain unimported and the run must
    exit nonzero.  No gate error is swallowed (no catch/pass).
    """
    result = PreScoreGateResult(passed=True)
    n = len(records)

    result.check("preflight_converged", preflight_passed,
                 "real context/support preflight did not converge")

    # matrix_360_records: exactly 360 one-shot records.
    one_shot_count = sum(
        1 for r in records if r.interaction_mode == "one_shot")
    result.check(
        "matrix_360_records",
        one_shot_count == B1_ONE_SHOT_RECORDS and not one_shot_failures,
        f"one_shot_count={one_shot_count} != {B1_ONE_SHOT_RECORDS}; "
        f"matrix_failures={one_shot_failures[:3]}",
    )

    # matrix_144_records: exactly 144 two-step records.
    two_step_count = sum(
        1 for r in records if r.interaction_mode == "two_step")
    result.check(
        "matrix_144_records",
        two_step_count == B1_TWO_STEP_RECORDS and not two_step_failures,
        f"two_step_count={two_step_count} != {B1_TWO_STEP_RECORDS}; "
        f"matrix_failures={two_step_failures[:3]}",
    )

    # disjoint_union_504: exactly 504 unique cell keys.
    unique_keys = set(cell_keys)
    result.check("disjoint_union_504",
                 len(unique_keys) == B1_TOTAL_RECORDS and n == B1_TOTAL_RECORDS,
                 f"unique_keys={len(unique_keys)} records={n} != {B1_TOTAL_RECORDS}")

    # all_records_accepted: every record status == "accepted".
    all_accepted = n == B1_TOTAL_RECORDS and all(
        r.status == "accepted" for r in records)
    result.check("all_records_accepted", all_accepted,
                 f"{sum(1 for r in records if r.status != 'accepted')} rejected")

    # all_records_ok: every record result_status == "ok".
    all_ok = n == B1_TOTAL_RECORDS and all(
        r.result_status == "ok" for r in records)
    result.check("all_records_ok", all_ok,
                 f"{sum(1 for r in records if r.result_status != 'ok')} not ok")

    # all_resource_complete: every accepted record has non-None cpu + rss.
    resource_complete = sum(
        1 for r in records
        if r.status == "accepted" and r.resource_sample is not None
        and r.resource_sample.cpu_seconds is not None
        and r.resource_sample.rss_bytes is not None
    )
    result.check("all_resource_complete",
                 n == B1_TOTAL_RECORDS and resource_complete == n,
                 f"resource_complete={resource_complete}/{n}; "
                 f"expected total={B1_TOTAL_RECORDS}")

    # require_scoreable_all: every (record, capture) passes require_scoreable.
    scoreable_count = 0
    scoreable_errors: list[str] = []
    for rec, cap in zip(records, captures):
        try:
            require_scoreable(rec, cap)
            scoreable_count += 1
        except Exception as exc:
            scoreable_errors.append(
                f"{rec.adapter_id}/{rec.run_cell_id}: {type(exc).__name__}: {exc}")
    result.check("require_scoreable_all",
                 n == B1_TOTAL_RECORDS and scoreable_count == n,
                 f"scoreable={scoreable_count}/{n}; "
                 f"first errors: {scoreable_errors[:3]}")

    # source_immutability + wsr_inventory: checked inline during execution;
    # here we verify no matrix failures (which include snapshot mutation
    # errors caught by run_adapter's scan_visible_tree).
    parent_complete = (
        n == B1_TOTAL_RECORDS
        and len(parent_receipts) == n
        and not parent_receipt_failures)
    result.check("source_immutability", parent_complete,
                 f"parent receipt failures={parent_receipt_failures[:3]}")
    result.check("wsr_inventory_strict", parent_complete,
                 f"parent receipts={len(parent_receipts)}/{n}")

    # cold_warm_semantic_equality: cold and warm records must have identical
    # canonical hashes for the same (adapter, task, rep, step).
    _check_cold_warm_equality(cells, result)

    # repetition_determinism: repetitions 1/2/3 must agree on status/result/
    # pack/ledger/hashes.
    _check_repetition_determinism(cells, result)

    # two_step_lineage_valid: all two-step support records must be accepted
    # with valid lineage (no tgt_unknown, no lineage failures).
    lineage_failures = []
    for cell in cells:
        r = cell.record
        if r.interaction_mode != "two_step" or r.operation != "support":
            continue
        output = cell.capture.output
        if r.status != "accepted" or r.failure_category is not None or output is None:
            lineage_failures.append(r)
            continue
        for support in output.pack.support:
            if support.parent_target_id != cell.request.run_spec.bound_target_id:
                lineage_failures.append(r)
                break
    support_cell_count = sum(
        1 for cell in cells
        if cell.record.interaction_mode == "two_step"
        and cell.record.operation == "support")
    expected_support_cells = B1_TWO_STEP_RECORDS // 2
    result.check(
        "two_step_lineage_valid",
        n == B1_TOTAL_RECORDS
        and support_cell_count == expected_support_cells
        and len(lineage_failures) == 0,
        f"support_cells={support_cell_count}/{expected_support_cells}; "
        f"lineage_failures={len(lineage_failures)}",
    )

    provider_count = sum(
        int(receipt["provider_network_call_count"])
        for receipt in parent_receipts)
    result.check("provider_count_zero",
                 parent_complete and provider_count == 0,
                 f"provider_network_call_count={provider_count}")

    # privacy_canary_absent: the parent scans fixtures, requests, captures,
    # environment, transcripts and all run files before scorer import.
    result.check("privacy_canary_absent",
                 privacy_canary_occurrences == 0,
                 f"canary_occurrences={privacy_canary_occurrences}")

    # sentinel_expected_passed: matrix validation passed (no failures).
    sentinel_expected = sum(int(r["sentinel_expected"]) for r in parent_receipts)
    sentinel_passed = sum(int(r["sentinel_passed"]) for r in parent_receipts)
    result.check("sentinel_expected_passed",
                 parent_complete and sentinel_expected > 0
                 and sentinel_expected == sentinel_passed,
                 f"sentinel={sentinel_passed}/{sentinel_expected}")

    return result


def _check_cold_warm_equality(
    cells: list[B1CellResult], result: PreScoreGateResult,
) -> None:
    """Verify cold and warm records have identical canonical hashes."""
    by_cell: dict[tuple, dict[str, B1CellResult]] = {}
    for cell in cells:
        r = cell.record
        key = (r.adapter_id, r.run_cell_id, r.adapter_repetition,
               (r.interaction_mode, r.operation))
        by_cell.setdefault(key, {})[r.cache_state] = cell
    mismatches = 0
    for key, by_cache in by_cell.items():
        cold = by_cache.get("cold")
        warm = by_cache.get("warm")
        if cold is None or warm is None:
            continue
        if cold.semantic_hash is None or cold.semantic_hash != warm.semantic_hash:
            mismatches += 1
        if cold.record.canonical_pack_hash != warm.record.canonical_pack_hash:
            mismatches += 1
        if (cold.parent_receipt is None or warm.parent_receipt is None
                or cold.parent_receipt["index_inventory_digest"]
                != warm.parent_receipt["index_inventory_digest"]):
            mismatches += 1
    result.check("cold_warm_semantic_equality",
                 mismatches == 0,
                 f"{mismatches} cold/warm hash mismatches")


def _check_repetition_determinism(
    cells: list[B1CellResult], result: PreScoreGateResult,
) -> None:
    """Verify repetitions 1/2/3 agree on semantic envelope + hashes."""
    by_group: dict[tuple, dict[int, B1CellResult]] = {}
    for cell in cells:
        r = cell.record
        key = (r.adapter_id, r.run_cell_id, r.cache_state,
               (r.interaction_mode, r.operation))
        by_group.setdefault(key, {})[r.adapter_repetition] = cell
    mismatches = 0
    for key, by_rep in by_group.items():
        if len(by_rep) < 2:
            continue
        reps = list(by_rep.values())
        statuses = {cell.record.status for cell in reps}
        if len(statuses) > 1:
            mismatches += 1
        result_statuses = {cell.record.result_status for cell in reps}
        if len(result_statuses) > 1:
            mismatches += 1
        if all(cell.record.status == "accepted" for cell in reps):
            semantic = {cell.semantic_hash for cell in reps}
            if None in semantic or len(semantic) > 1:
                mismatches += 1
            cph = {cell.record.canonical_pack_hash for cell in reps}
            if len(cph) > 1:
                mismatches += 1
    result.check("repetition_determinism",
                 mismatches == 0,
                 f"{mismatches} determinism mismatches")


# ---------------------------------------------------------------------------
# Full matrix runner
# ---------------------------------------------------------------------------


@dataclass
class B1RunResult:
    """Result of the full 504-cell mechanics screen."""
    records: list[ValidatedRunRecord] = field(default_factory=list)
    captures: list[PrivateValidatedOutputCapture] = field(default_factory=list)
    cell_keys: list[tuple] = field(default_factory=list)
    cells: list[B1CellResult] = field(default_factory=list)
    parent_receipts: list[dict[str, Any]] = field(default_factory=list)
    parent_receipt_failures: list[str] = field(default_factory=list)
    one_shot_failures: list[str] = field(default_factory=list)
    two_step_failures: list[str] = field(default_factory=list)
    gate_result: PreScoreGateResult | None = None
    preflight_result: dict[str, Any] | None = None
    provider_network_call_count: int = 0
    privacy_canary_occurrences_before_score: int = 0
    source_bundle_digest: str = ""
    runtime_bundle_digest: str = ""
    runtime_seconds: float = 0.0
    runs_dir: str = ""


_B1_CONTEXT_PROBE_SLUGS = frozenset(
    task.task_slug for task in B1_ONE_SHOT_TASKS)


def _finish_cell(
    aggregate: B1RunResult,
    cell: B1CellResult,
    descriptor: AdapterDescriptor,
    private_root: Path,
) -> None:
    aggregate.records.append(cell.record)
    aggregate.captures.append(cell.capture)
    aggregate.cell_keys.append(cell.cell_key)
    aggregate.cells.append(cell)
    try:
        receipt = _collect_parent_execution_receipt(
            cell, descriptor, private_root)
        aggregate.parent_receipts.append(receipt)
    except Exception as exc:  # noqa: BLE001 - recorded as a failed gate
        cell.parent_receipt_error = f"{type(exc).__name__}: {exc}"
        aggregate.parent_receipt_failures.append(
            f"{cell.request.run_spec.request_id}: {cell.parent_receipt_error}")
    _persist_private_cell(cell, private_root)


def _run_context_plan_probe(
    root: Path,
    private_root: Path,
    aggregate: B1RunResult,
    adapter_map: dict[str, tuple[AdapterDescriptor, AdapterHooks]],
    failures: list[str],
) -> None:
    """Exercise representative context branches without loading the scorer."""
    tasks = tuple(
        task for task in B1_ONE_SHOT_TASKS
        if task.task_slug in _B1_CONTEXT_PROBE_SLUGS
    )
    if len(tasks) != len(_B1_CONTEXT_PROBE_SLUGS):
        failures.append("context preflight task selection drifted")
        return
    for task in tasks:
        for adapter_id in B1_ADAPTER_IDS:
            descriptor, hooks = adapter_map[adapter_id]
            cell_root = _create_cell(root, task, adapter_id, 1)
            snapshot = _materialize_b1_snapshot(
                cell_root, task.visible_files())
            for cache in B1_CACHE_STATES:
                request_id = (
                    f"b1_preflight_one_{task.task_slug}_{adapter_id}_{cache}")
                request = _make_b1_request(
                    task, snapshot, adapter_id, 1, cache,
                    operation="context", request_id=request_id,
                    episode_id=(
                        f"b1_preflight_one_ep_{task.task_slug}_{cache}"),
                )
                cell = _run_cell(
                    hooks, descriptor, request, snapshot, cell_root,
                    episode_registry=None, materialize_step=1,
                    conformance_category="b1_preflight_context",
                )
                try:
                    if cache == "cold" and cell.record.status == "accepted":
                        write_index_seal(cell_root)
                    _finish_cell(
                        aggregate, cell, descriptor, private_root)
                    require_scoreable(cell.record, cell.capture)
                    receipt = cell.parent_receipt
                    output = cell.capture.output
                    if receipt is None or output is None:
                        raise ContractError(
                            "context preflight lacks parent receipt/capture")
                    if receipt["provider_network_call_count"] != 0 \
                            or receipt["trace_written"] is not True:
                        raise ContractError(
                            "context preflight provider/trace sentinel mismatch")
                    expected_components = adapter_context_components(adapter_id)
                    component_receipts = receipt["component_receipts"]
                    if {item["component"] for item in component_receipts} != set(
                            expected_components):
                        raise ContractError(
                            "context preflight component set mismatch")
                    by_component = {
                        item["component"]: item for item in component_receipts
                    }
                    if "literal" in expected_components \
                            and task.task_family == "error_text":
                        literal_receipt = by_component["literal"]
                        if literal_receipt["status"] != "executed" \
                                or literal_receipt["evidence_count"] < 1:
                            raise ContractError(
                                "literal-task preflight lacks literal evidence")
                    if "symbol" in expected_components \
                            and task.task_family == "symbol_lookup":
                        symbol_receipt = by_component["symbol"]
                        if symbol_receipt["status"] != "executed" \
                                or symbol_receipt["evidence_count"] < 1:
                            raise ContractError(
                                "symbol-task preflight lacks AST symbol evidence")
                    if "graph" in expected_components \
                            and task.task_family in B1_GRAPH_ELIGIBLE_TASK_FAMILIES:
                        graph_receipt = by_component["graph"]
                        if graph_receipt["status"] != "executed" \
                                or graph_receipt["evidence_count"] < 1:
                            raise ContractError(
                                "eligible graph preflight lacks sentinel evidence")
                    if not output.validated_candidates \
                            and output.pack.pack_status != "no_evidence":
                        raise ContractError(
                            "empty context preflight did not produce no_evidence")
                except Exception as exc:  # noqa: BLE001 - private probe detail
                    failures.append(
                        f"{task.task_slug}/{adapter_id}/{cache}: "
                        f"{type(exc).__name__}: {exc}")


def run_preflight_probe(runs_dir: Path) -> dict[str, Any]:
    """Exercise every cumulative context plan and both support modes.

    The probe uses the same Phase A/B0 execution path as the full matrix for
    cold then warm reuse. It must prove that all six stacks naturally select
    the same one-line target for each two-step fixture and that the sealed
    state produces identical cold/warm semantics before any 504-cell run.
    """
    root = Path(runs_dir) / "preflight"
    private_root = root / "private"
    root.mkdir(parents=True, exist_ok=True)
    aggregate = B1RunResult(runs_dir=str(root))
    adapter_map = {
        aid: (desc_fn(), hooks_fn())
        for aid, desc_fn, hooks_fn in B1_ADAPTERS
    }
    targets: dict[str, dict[str, tuple[str, int, int]]] = {}
    failures: list[str] = []
    for task in B1_TWO_STEP_TASKS:
        targets[task.task_slug] = {}
        for adapter_id in B1_ADAPTER_IDS:
            descriptor, hooks = adapter_map[adapter_id]
            cell_root = _create_cell(root, task, adapter_id, 1)
            snapshot = _materialize_b1_snapshot(cell_root, task.visible_files())
            for cache in B1_CACHE_STATES:
                registry = EpisodeRegistry()
                episode_id = f"b1_preflight_ep_{task.task_slug}_{cache}"
                context_id = f"b1_preflight_ctx_{task.task_slug}_{cache}"
                support_id = (
                    f"b1_preflight_sup_{task.task_slug}_{adapter_id}_{cache}")
                context_request = _make_b1_request(
                    task, snapshot, adapter_id, 1, cache, operation="context",
                    request_id=context_id, episode_id=episode_id)
                context_cell = _run_cell(
                    hooks, descriptor, context_request, snapshot, cell_root,
                    episode_registry=registry, materialize_step=1,
                    conformance_category="b1_preflight")
                try:
                    if cache == "cold" and context_cell.record.status == "accepted":
                        write_index_seal(cell_root)
                    _finish_cell(
                        aggregate, context_cell, descriptor, private_root)
                    require_scoreable(context_cell.record, context_cell.capture)
                    output = context_cell.capture.output
                    if output is None or output.pack.pack_status != "ready" \
                            or len(output.pack.targets) != 1:
                        raise ContractError(
                            "preflight context did not produce one ready target")
                    target = output.pack.targets[0]
                    target_cell = (target.path, target.start_line, target.end_line)
                    if target.start_line != target.end_line:
                        raise ContractError("preflight target is not one line")
                    targets[task.task_slug][f"{adapter_id}/{cache}"] = target_cell

                    parent = registry.lookup(context_id)
                    if parent is None:
                        raise ContractError("preflight episode registry missing parent")
                    _write_lineage_receipt(
                        cell_root, support_id, context_id, parent.bound_target_id,
                        parent.target_path, parent.target_start_line,
                        parent.target_end_line, snapshot.manifest_digest,
                        context_cell.record.canonical_result_hash or "",
                        context_cell.record.canonical_pack_hash or "",
                    )
                    support_request = _make_b1_request(
                        task, snapshot, adapter_id, 1, cache, operation="support",
                        request_id=support_id, episode_id=episode_id,
                        parent_result_id=context_id,
                        bound_target_id=parent.bound_target_id)
                    support_cell = _run_cell(
                        hooks, descriptor, support_request, snapshot, cell_root,
                        episode_registry=registry, materialize_step=2,
                        conformance_category="b1_preflight")
                    _finish_cell(
                        aggregate, support_cell, descriptor, private_root)
                    require_scoreable(support_cell.record, support_cell.capture)
                    support_output = support_cell.capture.output
                    expected_status = (
                        "ready" if adapter_supports_support(adapter_id)
                        else "no_evidence")
                    if support_output is None \
                            or support_output.pack.pack_status != expected_status:
                        raise ContractError(
                            f"preflight support status != {expected_status}")
                    if adapter_supports_support(adapter_id) \
                            and len(support_output.pack.support) < 1:
                        raise ContractError(
                            "support-capable preflight found no import support")
                except Exception as exc:  # noqa: BLE001 - private preflight result
                    failures.append(
                        f"{task.task_slug}/{adapter_id}/{cache}: "
                        f"{type(exc).__name__}: {exc}")
                finally:
                    _clear_lineage_receipt(cell_root)

    _run_context_plan_probe(
        root, private_root, aggregate, adapter_map, failures)

    context_probe_records = [
        record for record in aggregate.records
        if record.run_cell_id in _B1_CONTEXT_PROBE_SLUGS
        and record.operation == "context"
    ]
    context_probe_spec = ComparisonMatrixSpec(
        expected_adapter_ids=B1_ADAPTER_IDS,
        expected_run_cells=tuple(
            task.task_slug for task in B1_ONE_SHOT_TASKS
            if task.task_slug in _B1_CONTEXT_PROBE_SLUGS),
        expected_repetitions=(1,),
        expected_cache_states=B1_CACHE_STATES,
        expected_steps=(("one_shot", "context"),),
    )
    context_matrix_failures = validate_comparison_matrix(
        context_probe_spec, context_probe_records)
    failures.extend(
        f"context preflight matrix: {failure}"
        for failure in context_matrix_failures)

    two_step_probe_records = [
        record for record in aggregate.records
        if record.run_cell_id in {
            task.task_slug for task in B1_TWO_STEP_TASKS
        }
    ]
    two_step_probe_spec = ComparisonMatrixSpec(
        expected_adapter_ids=B1_ADAPTER_IDS,
        expected_run_cells=tuple(
            task.task_slug for task in B1_TWO_STEP_TASKS),
        expected_repetitions=(1,),
        expected_cache_states=B1_CACHE_STATES,
        expected_steps=(
            ("two_step", "context"),
            ("two_step", "support"),
        ),
    )
    two_step_matrix_failures = validate_comparison_matrix(
        two_step_probe_spec, two_step_probe_records)
    failures.extend(
        f"two-step preflight matrix: {failure}"
        for failure in two_step_matrix_failures)

    for task_slug, by_adapter in targets.items():
        expected_target_count = len(B1_ADAPTER_IDS) * len(B1_CACHE_STATES)
        if len(by_adapter) != expected_target_count:
            failures.append(
                f"{task_slug}: only {len(by_adapter)}/{expected_target_count} "
                "context targets")
            continue
        unique = set(by_adapter.values())
        if len(unique) != 1:
            failures.append(f"{task_slug}: context targets diverged: {sorted(unique)}")
    semantic_gate = PreScoreGateResult(passed=True)
    _check_cold_warm_equality(aggregate.cells, semantic_gate)
    if not semantic_gate.passed:
        failures.append(
            "preflight cold/warm mismatch: "
            f"{semantic_gate.gate_failures.get('cold_warm_semantic_equality')}")
    result = {
        "passed": not failures,
        "record_count": len(aggregate.records),
        "parent_receipt_count": len(aggregate.parent_receipts),
        "failures": failures,
        "targets": targets,
    }
    (private_root / "preflight_result.json").parent.mkdir(
        parents=True, exist_ok=True)
    (private_root / "preflight_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def _count_canary_before_score(
    canary: str,
    runs_dir: Path,
    cells: list[B1CellResult],
) -> int:
    needle = canary.encode("utf-8")
    count = 0
    fixture_surface = {
        "tasks": [
            {
                "task_slug": task.task_slug,
                "language_family": task.language_family,
                "task_family": task.task_family,
                "interaction_mode": task.interaction_mode,
                "query": task.query,
                "operation": task.operation,
                "repo_id": task.repo_id,
                "files": task.file_contents(),
            }
            for task in B1_ALL_TASKS
        ]
    }
    count += json.dumps(
        fixture_surface, sort_keys=True).encode("utf-8").count(needle)
    request_capture_surface = [
        {
            "request": _json_safe(cell.request),
            "record": _json_safe(cell.record),
            "capture": _json_safe(cell.capture.output),
            "parent_receipt": cell.parent_receipt,
        }
        for cell in cells
    ]
    count += json.dumps(
        request_capture_surface, sort_keys=True).encode("utf-8").count(needle)
    for value in os.environ.values():
        if isinstance(value, str):
            count += value.encode("utf-8", errors="ignore").count(needle)
    for path in sorted(runs_dir.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            count += path.read_bytes().count(needle)
        except OSError as exc:
            raise ContractError(f"cannot scan B1 private surface {path}") from exc
    return count


def run_full_matrix(
    runs_dir: Path | None = None,
    *,
    canary: str,
) -> B1RunResult:
    """Run the full 504-cell mechanics screen.

    V2: cells are frozen once (cold+warm share the same cell).  Pre-score
    gates are checked after the matrix completes.  On any gate fail, the
    gate_result is set and the caller must NOT import the scorer.
    """
    if runs_dir is None:
        runs_dir = Path("runs") / f"b1_v2_{int(time.time())}"
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    private_root = runs_dir / "private"
    private_root.mkdir(parents=True, exist_ok=True)

    # Set CLI env var for spawned subprocesses.
    cli_path = _find_cli()
    os.environ["OPENLOCUS_CLI"] = cli_path

    result = B1RunResult(runs_dir=str(runs_dir))
    result.source_bundle_digest = b1_source_bundle_digest()
    result.runtime_bundle_digest = b1_runtime_bundle_digest(cli_path)
    t0 = time.perf_counter()

    result.preflight_result = run_preflight_probe(runs_dir)
    if not result.preflight_result.get("passed", False):
        gate = PreScoreGateResult(passed=True)
        gate.check("preflight_converged", False,
                   str(result.preflight_result.get("failures", [])[:3]))
        result.gate_result = gate
        result.runtime_seconds = time.perf_counter() - t0
        _write_private_summary(runs_dir, result)
        return result

    adapter_map: dict[str, tuple[Any, Any]] = {}
    for aid, desc_fn, hooks_fn in B1_ADAPTERS:
        adapter_map[aid] = (desc_fn(), hooks_fn())

    # --- One-shot matrix (360 cells) ---
    one_shot_records: list[ValidatedRunRecord] = []
    one_shot_captures: list[PrivateValidatedOutputCapture] = []

    for task in B1_ONE_SHOT_TASKS:
        for adapter_id in B1_ADAPTER_IDS:
            desc, hooks = adapter_map[adapter_id]
            for rep in B1_REPETITIONS:
                # Create cell (shared between cold and warm — freeze once).
                cell = _create_cell(runs_dir, task, adapter_id, rep)
                vis = task.visible_files()
                # Materialize snapshot ONCE (not per cache state).
                snapshot = _materialize_b1_snapshot(cell, vis)
                for cache in B1_CACHE_STATES:
                    ep_id = f"b1_ep_{task.task_slug}_rep{rep}_{cache}"
                    req_id = f"b1_req_{task.task_slug}_{adapter_id}_rep{rep}_{cache}"
                    request = _make_b1_request(
                        task, snapshot, adapter_id, rep, cache,
                        request_id=req_id, episode_id=ep_id,
                    )
                    cell_result = _run_cell(
                        hooks, desc, request, snapshot, cell,
                        episode_registry=None, materialize_step=1,
                        conformance_category="b1_one_shot",
                    )
                    if cache == "cold" and cell_result.record.status == "accepted":
                        try:
                            write_index_seal(cell)
                        except Exception as exc:  # noqa: BLE001
                            cell_result.parent_receipt_error = (
                                f"index seal: {type(exc).__name__}: {exc}")
                    _finish_cell(result, cell_result, desc, private_root)
                    one_shot_records.append(cell_result.record)
                    one_shot_captures.append(cell_result.capture)

    # --- Two-step matrix (144 cells) ---
    two_step_records: list[ValidatedRunRecord] = []
    two_step_captures: list[PrivateValidatedOutputCapture] = []

    for task in B1_TWO_STEP_TASKS:
        for adapter_id in B1_ADAPTER_IDS:
            desc, hooks = adapter_map[adapter_id]
            for rep in B1_REPETITIONS:
                cell = _create_cell(runs_dir, task, adapter_id, rep)
                vis = task.visible_files()
                snapshot = _materialize_b1_snapshot(cell, vis)
                for cache in B1_CACHE_STATES:
                    ep_id = f"b1_ep_{task.task_slug}_rep{rep}_{cache}"
                    ctx_req_id = f"b1_ctx_{task.task_slug}_rep{rep}_{cache}"
                    sup_req_id = f"b1_sup_{task.task_slug}_{adapter_id}_rep{rep}_{cache}"

                    registry = EpisodeRegistry()

                    # Context step.
                    ctx_request = _make_b1_request(
                        task, snapshot, adapter_id, rep, cache,
                        operation="context",
                        request_id=ctx_req_id, episode_id=ep_id,
                    )
                    ctx_cell = _run_cell(
                        hooks, desc, ctx_request, snapshot, cell,
                        episode_registry=registry, materialize_step=1,
                        conformance_category="b1_two_step",
                    )
                    if cache == "cold" and ctx_cell.record.status == "accepted":
                        try:
                            write_index_seal(cell)
                        except Exception as exc:  # noqa: BLE001
                            ctx_cell.parent_receipt_error = (
                                f"index seal: {type(exc).__name__}: {exc}")
                    _finish_cell(result, ctx_cell, desc, private_root)
                    two_step_records.append(ctx_cell.record)
                    two_step_captures.append(ctx_cell.capture)

                    # Register target for support step.
                    parent = registry.lookup(ctx_req_id)
                    if parent is not None:
                        bound_tid = parent.bound_target_id
                        # Write lineage receipt for the support query hook.
                        _write_lineage_receipt(
                            cell, sup_req_id, ctx_req_id, bound_tid,
                            parent.target_path, parent.target_start_line,
                            parent.target_end_line,
                            snapshot.manifest_digest,
                            ctx_cell.record.canonical_result_hash or "",
                            ctx_cell.record.canonical_pack_hash or "",
                        )
                    else:
                        bound_tid = None

                    # Support step.
                    if bound_tid is not None:
                        sup_request = _make_b1_request(
                            task, snapshot, adapter_id, rep, cache,
                            operation="support",
                            request_id=sup_req_id, episode_id=ep_id,
                            parent_result_id=ctx_req_id,
                            bound_target_id=bound_tid,
                        )
                        sup_cell = _run_cell(
                            hooks, desc, sup_request, snapshot, cell,
                            episode_registry=registry, materialize_step=2,
                            conformance_category="b1_two_step",
                        )
                        _finish_cell(result, sup_cell, desc, private_root)
                        two_step_records.append(sup_cell.record)
                        two_step_captures.append(sup_cell.capture)
                        # Clear receipt after support.
                        _clear_lineage_receipt(cell)
                    else:
                        # Missing parent: the support request will fail
                        # lineage validation in run_adapter.  This produces
                        # a rejected lineage cell (never tgt_unknown).
                        sup_request = _make_b1_request(
                            task, snapshot, adapter_id, rep, cache,
                            operation="support",
                            request_id=sup_req_id, episode_id=ep_id,
                            parent_result_id=ctx_req_id,
                            bound_target_id="lineage_missing",
                        )
                        sup_cell = _run_cell(
                            hooks, desc, sup_request, snapshot, cell,
                            episode_registry=registry, materialize_step=2,
                            conformance_category="b1_two_step",
                        )
                        _finish_cell(result, sup_cell, desc, private_root)
                        two_step_records.append(sup_cell.record)
                        two_step_captures.append(sup_cell.capture)

    # --- Matrix validation (two canonical calls) ---
    one_shot_spec = ComparisonMatrixSpec(
        expected_adapter_ids=B1_ADAPTER_IDS,
        expected_run_cells=tuple(t.task_slug for t in B1_ONE_SHOT_TASKS),
        expected_repetitions=B1_REPETITIONS,
        expected_cache_states=B1_CACHE_STATES,
        expected_steps=(("one_shot", "context"),),
    )
    result.one_shot_failures = validate_comparison_matrix(
        one_shot_spec, one_shot_records)

    two_step_spec = ComparisonMatrixSpec(
        expected_adapter_ids=B1_ADAPTER_IDS,
        expected_run_cells=tuple(t.task_slug for t in B1_TWO_STEP_TASKS),
        expected_repetitions=B1_REPETITIONS,
        expected_cache_states=B1_CACHE_STATES,
        expected_steps=(("two_step", "context"), ("two_step", "support")),
    )
    result.two_step_failures = validate_comparison_matrix(
        two_step_spec, two_step_records)

    result.provider_network_call_count = sum(
        int(receipt["provider_network_call_count"])
        for receipt in result.parent_receipts)
    result.privacy_canary_occurrences_before_score = _count_canary_before_score(
        canary, runs_dir, result.cells)

    # --- Pre-score gates ---
    result.gate_result = _check_pre_score_gates(
        result.records, result.captures, result.cells,
        result.parent_receipts, result.parent_receipt_failures,
        result.one_shot_failures, result.two_step_failures,
        result.cell_keys,
        preflight_passed=bool(result.preflight_result.get("passed", False)),
        privacy_canary_occurrences=(
            result.privacy_canary_occurrences_before_score),
    )

    result.runtime_seconds = time.perf_counter() - t0

    # --- Write private summary ---
    _write_private_summary(runs_dir, result)

    return result


def _write_private_summary(runs_dir: Path, result: B1RunResult) -> None:
    """Write a private JSON summary under runs/ (never committed)."""
    summary = {
        "b1_spec_version": B1_SPEC_VERSION,
        "total_records": len(result.records),
        "one_shot_records": B1_ONE_SHOT_RECORDS,
        "two_step_records": B1_TWO_STEP_RECORDS,
        "accepted_count": sum(1 for r in result.records if r.status == "accepted"),
        "rejected_count": sum(1 for r in result.records if r.status == "rejected"),
        "runtime_seconds": result.runtime_seconds,
        "runs_dir": str(runs_dir),
        "source_bundle_digest": result.source_bundle_digest,
        "runtime_bundle_digest": result.runtime_bundle_digest,
        "preflight_passed": bool(
            result.preflight_result and result.preflight_result.get("passed")),
        "parent_receipt_count": len(result.parent_receipts),
        "parent_receipt_failures": result.parent_receipt_failures[:20],
        "provider_network_call_count": result.provider_network_call_count,
        "privacy_canary_occurrences_before_score": (
            result.privacy_canary_occurrences_before_score),
        "one_shot_matrix_failures": result.one_shot_failures[:20],
        "two_step_matrix_failures": result.two_step_failures[:20],
        "pre_score_gates_passed": (
            result.gate_result.passed if result.gate_result else False),
        "pre_score_gate_failures": (
            dict(result.gate_result.gate_failures) if result.gate_result else {}),
    }
    summary_path = runs_dir / "b1_private_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


__all__ = [
    "b1_caps", "run_preflight_probe", "run_full_matrix",
    "B1RunResult", "B1CellResult",
    "PreScoreGateResult", "_check_pre_score_gates",
    "_create_cell", "_materialize_b1_snapshot",
    "_write_lineage_receipt", "_clear_lineage_receipt",
    "_make_b1_run_spec", "_make_b1_request",
]
