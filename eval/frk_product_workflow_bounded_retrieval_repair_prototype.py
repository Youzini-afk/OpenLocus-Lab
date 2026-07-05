#!/usr/bin/env python3
"""OpenLocus v2 FRK product-workflow bounded retrieval repair prototype.

This phase executes one bounded same-budget prototype arm over the Phase-5
product-workflow task set. It may run local OpenLocus retrieve/read/citation
validation actions, but it does not add retrieval channels, expand candidate or
read budgets, scan sources, call providers, use network/CI, train, change
runtime/defaults, or harden kernels. Private rows are written only under ignored
``runs/`` storage after explicit private input/output confirmations; the public
report is aggregate-only.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import frk_product_workflow_failure_decomposition as decomposition
import frk_product_workflow_specific_retrieval_repair_design as design
import frk_product_workflow_trace_benchmark as benchmark
import rpm_trace_schema as schema


REPO = Path(__file__).resolve().parent.parent
PHASE = "openlocus_v2_frk_product_workflow_bounded_retrieval_repair_prototype"
REPORT_SCHEMA_VERSION = "frk_product_workflow_bounded_retrieval_repair_prototype_public_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / "frk_product_workflow_bounded_retrieval_repair_prototype" / "frk_product_workflow_bounded_retrieval_repair_prototype_report.json"
BENCH_REPORT = benchmark.DEFAULT_REPORT
DECOMP_REPORT = decomposition.DEFAULT_REPORT
DESIGN_REPORT = design.DEFAULT_REPORT

PRIVATE_PREFIX = "frk_product_workflow_bounded_repair_private_"
TRACE_FILENAME = "frk_product_workflow_bounded_repair_state_action_rows.jsonl"
LABEL_FILENAME = "frk_product_workflow_bounded_repair_private_expected_labels.jsonl"

PROTOTYPE_ARM = "frk_bounded_repair_wrong_file_guard_fixed_budget"
PREVIOUS_HYBRID_ARM = "openlocus_hybrid_retrieve"
ALLOWED_CHANNEL_FAMILIES = ("bm25_text", "symbol_regex", "existing_hybrid_retrieve")
EXECUTED_CHANNEL_FAMILIES = ("existing_hybrid_retrieve",)

STATUS_INCOMPLETE = "frk_product_workflow_bounded_retrieval_repair_prototype_incomplete_targeted_repair_only"
STATUS_NO_LIFT = "frk_product_workflow_bounded_retrieval_repair_prototype_complete_no_lift_stop_or_failure_decomposition"
STATUS_PARTIAL = "frk_product_workflow_bounded_retrieval_repair_prototype_partial_lift_not_best_baseline"
STATUS_POSITIVE = "frk_product_workflow_bounded_retrieval_repair_prototype_positive_same_budget_heldout_design_authorized"
STATUS_FAILURE = "frk_product_workflow_bounded_retrieval_repair_prototype_failed_privacy_schema_or_currentness_repair_only"

AUTH_INCOMPLETE = "targeted_bounded_retrieval_repair_prototype_repair_only"
AUTH_FAILURE = "targeted_privacy_schema_currentness_repair_only"
AUTH_STOP = "frk_product_workflow_bounded_repair_failure_decomposition_or_stop_current_candidate"
AUTH_PARTIAL = "frk_product_workflow_bounded_repair_failure_decomposition_or_metric_task_balance_review"
AUTH_HELDOUT = "frk_product_workflow_heldout_same_budget_retrieval_repair_validation_design"

PUBLIC_FORBIDDEN = {
    "d2_model_scaling",
    "rpm_training",
    "training_claim",
    "runtime_default_claim",
    "default_claim",
    "provider_claim",
    "network_claim",
    "ci_claim",
    "method_claim",
    "scale_claim",
    "winner_claim",
    "broad_source_scan",
    "source_scan",
    "candidate_generation_expansion",
    "candidate_expansion",
    "new_channel_family",
    "new_provider",
    "new_retrieval_experiment_beyond_bounded_prototype",
    "kernel_hardening_continuation",
    "old_heuristic_chain",
    "raw_publication",
    "private_trace_publication",
    "frk_j",
    "frk_b_c_resurrection",
    "frk_i_selector_variants",
    "ldi_b_easy_continuation",
    "haae_sg",
    "haae_t",
}

MECHANISM_KEYS = (
    "wrong_file_or_rank_miss",
    "read_budget_or_topk_pressure",
    "no_hit",
    "stale_or_currentness_failure",
    "validation_failure",
)


class PrototypeError(Exception):
    pass


def bucket_count(count: int) -> str:
    return benchmark.bucket_count(count)


def bucket_rate(success: int, total: int) -> str:
    return benchmark.bucket_rate(success, total)


def delta_bucket(a_success: int, a_total: int, b_success: int, b_total: int) -> str:
    a = a_success / a_total if a_total else 0.0
    b = b_success / b_total if b_total else 0.0
    if a > b:
        return "positive_lift"
    if a == b:
        return "neutral_no_lift"
    return "negative_delta"


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PrototypeError(f"required public report missing: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise PrototypeError(f"required public report malformed: {path.name}") from exc
    if not isinstance(payload, dict):
        raise PrototypeError(f"required public report must be object: {path.name}")
    return payload


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_previous_private_inputs(confirm_private_input: bool, trace_jsonl: Path | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not confirm_private_input:
        raise PrototypeError("--confirm-private-input is required before reading private product-workflow inputs or labels")
    try:
        rows, labels, manifest = decomposition.load_private_inputs(True, trace_jsonl)
    except decomposition.DecompositionError as exc:
        raise PrototypeError(str(exc)) from exc
    if labels and not all(item.get("label_timing") == "after_action" for item in labels):
        raise PrototypeError("private labels must be joined only after action")
    manifest = dict(manifest)
    manifest["private_input_confirmation"] = "confirmed"
    return rows, labels, manifest


def source_readbacks(bench: dict[str, Any], decomp: dict[str, Any], design_report: dict[str, Any]) -> dict[str, Any]:
    decomp_summary = decomp.get("decomposition_summary", {})
    design_gates = design_report.get("static_replay_simulation_summary", {}).get("concrete_design_gate_results", {})
    return {
        "benchmark_status": bench.get("status"),
        "benchmark_candidate_vs_best_baseline_delta_bucket": bench.get("best_baseline_comparison", {}).get("candidate_vs_best_baseline_delta_bucket"),
        "benchmark_schema_gate": bench.get("validation_summary", {}).get("strict_phase1_schema"),
        "benchmark_privacy_gate": bench.get("validation_summary", {}).get("privacy_leak_scan"),
        "decomposition_status": decomp.get("status"),
        "decomposition_primary_mechanism": decomp_summary.get("primary_mechanism_bucket"),
        "decomposition_secondary_mechanism": decomp_summary.get("secondary_mechanism_bucket"),
        "decomposition_confidence_bucket": decomp_summary.get("confidence_bucket"),
        "design_status": design_report.get("status"),
        "design_authorized_next_phase": design_report.get("stop_go", {}).get("authorized_next_phase"),
        "design_same_budget_gate": bool(design_gates.get("same_candidate_cap")) and bool(design_gates.get("same_read_cap")),
        "design_no_new_channel_gate": bool(design_gates.get("no_new_retrieval_channel_family")),
        "design_concrete_gates_passed": design_report.get("validation_summary", {}).get("concrete_design_gates_passed"),
    }


def source_readbacks_ok(readbacks: dict[str, Any]) -> bool:
    return (
        readbacks.get("benchmark_status") == benchmark.STATUS_NO_LIFT
        and readbacks.get("benchmark_candidate_vs_best_baseline_delta_bucket") == "negative_vs_best_baseline"
        and readbacks.get("benchmark_schema_gate") == "passed"
        and readbacks.get("benchmark_privacy_gate") == "passed"
        and readbacks.get("decomposition_status") == decomposition.STATUS_RETRIEVAL_REPAIR
        and readbacks.get("decomposition_primary_mechanism") == "wrong_file_or_rank_miss"
        and readbacks.get("decomposition_secondary_mechanism") == "read_budget_or_topk_limit"
        and readbacks.get("design_status") == design.STATUS_CONCRETE
        and readbacks.get("design_authorized_next_phase") == design.AUTH_CONCRETE
        and readbacks.get("design_same_budget_gate") is True
        and readbacks.get("design_no_new_channel_gate") is True
        and readbacks.get("design_concrete_gates_passed") is True
    )


TOKEN_RE = re.compile(r"[A-Za-z0-9_]{3,}")


def tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def intent_score(task: benchmark.WorkflowTask, candidate: dict[str, Any], read_payload: dict[str, Any] | None = None) -> int:
    query_tokens = tokens(" ".join([task.text_query, task.symbol_or_regex_query, task.hybrid_query]))
    haystack = []
    spec = benchmark.evidence_read_spec(candidate)
    if spec:
        haystack.append(spec)
    path = benchmark.evidence_path(candidate)
    if path:
        haystack.append(path)
    if isinstance(read_payload, dict):
        for key in ("path", "text", "content", "snippet"):
            value = read_payload.get(key)
            if isinstance(value, str):
                haystack.append(value[:2000])
    return len(query_tokens & tokens(" ".join(haystack)))


def guarded_read_order(task: benchmark.WorkflowTask, candidates: list[dict[str, Any]], first_read_payload: dict[str, Any] | None) -> list[int]:
    """Pick the second read using only existing candidates and label-blind intent.

    If the guard cannot distinguish candidates, fixed original order is used. The
    expected path/label is intentionally not read here.
    """
    if len(candidates) <= 1:
        return []
    scored: list[tuple[int, int]] = []
    first_score = intent_score(task, candidates[0], first_read_payload)
    for idx, cand in enumerate(candidates[1:5], start=1):
        scored.append((intent_score(task, cand, None), idx))
    if not scored or all(score == 0 for score, _idx in scored) or (first_score == 0 and max(score for score, _idx in scored) == 0):
        return [idx for _score, idx in scored]
    return [idx for _score, idx in sorted(scored, key=lambda pair: (-pair[0], pair[1]))]


def run_prototype_task(binary: Path, private_root: Path, task: benchmark.WorkflowTask, order_start: int) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], int]:
    rows: list[dict[str, Any]] = []
    order = order_start
    candidates, availability, retrieval_latency, channel = benchmark.run_retrieval(binary, task, PREVIOUS_HYBRID_ARM)
    candidates = candidates[:5]
    candidate_count = len(candidates)
    rows.append(benchmark.build_row(
        task=task,
        arm=PROTOTYPE_ARM,
        action_type="bounded_retrieval",
        step_index=0,
        order_index=order,
        observation_status="observed" if candidate_count else "failed_safe",
        result_bucket="evidence_added" if candidate_count else "no_change",
        evidence_delta_bucket="delta_2_to_5" if candidate_count >= 2 else ("delta_1" if candidate_count == 1 else "delta_0"),
        latency_bucket=benchmark.bucket_latency(retrieval_latency),
        failure_bucket="none" if candidate_count else "missing_source",
        outcome_bucket="partial_bucket" if candidate_count else "failure_bucket",
        evidence_required=bool(candidate_count),
        evidence_linked=bool(candidate_count),
    ))
    order += 1

    read_count = 0
    validate_count = 0
    valid_count = 0
    invalid_count = 0
    match_found = False
    wrong_file_seen = False
    stale_currentness_failure = False
    validation_failure = False
    guard_reordered = False
    first_payload: dict[str, Any] | None = None
    read_indices: list[int] = []
    if candidates:
        read_indices.append(0)
    idx_cursor = 0
    while idx_cursor < len(read_indices) and read_count < 2:
        idx = read_indices[idx_cursor]
        idx_cursor += 1
        cand = candidates[idx]
        spec = benchmark.evidence_read_spec(cand)
        if not spec:
            continue
        read_payload, read_rc, read_latency = benchmark.run_cli(binary, ["read", spec, "--json"], fail_safe=True)
        read_ok = read_rc == 0 and isinstance(read_payload, dict)
        if read_ok and idx == 0:
            first_payload = read_payload
        cand_path = benchmark.evidence_path(read_payload if isinstance(read_payload, dict) else cand)
        expected_hit = cand_path == task.expected_path  # scoring only after read action selection
        wrong_file_seen = wrong_file_seen or (read_ok and not expected_hit)
        rows.append(benchmark.build_row(
            task=task,
            arm=PROTOTYPE_ARM,
            action_type="read_current_source",
            step_index=order - order_start,
            order_index=order,
            observation_status="observed" if read_ok else "failed_safe",
            result_bucket="evidence_added" if read_ok else "failure",
            evidence_delta_bucket="delta_1" if read_ok else "delta_0",
            latency_bucket=benchmark.bucket_latency(read_latency),
            failure_bucket="none" if read_ok else "missing_source",
            outcome_bucket="partial_bucket" if read_ok else "failure_bucket",
            evidence_required=read_ok,
            evidence_linked=read_ok,
        ))
        order += 1
        if not read_ok:
            continue
        read_count += 1
        evidence_file = private_root / f"prototype_evidence_{benchmark.private_ref('evidence', task.opaque_id, PROTOTYPE_ARM, str(idx))}.json"
        evidence_file.write_text(json.dumps(read_payload, sort_keys=True) + "\n", encoding="utf-8")
        validate_payload, validate_rc, validate_latency = benchmark.run_cli(binary, ["citations", "validate", str(evidence_file), "--json"], fail_safe=True)
        raw_valid = int(validate_payload.get("valid_count", 0)) if isinstance(validate_payload, dict) else 0
        raw_invalid = int(validate_payload.get("invalid_count", 0)) if isinstance(validate_payload, dict) else 0
        valid = validate_rc == 0 and raw_valid >= 1
        valid_count += 1 if valid else 0
        invalid_count += 0 if valid else max(1, raw_invalid)
        validate_count += 1
        validation_failure = validation_failure or not valid
        stale_currentness_failure = stale_currentness_failure or not valid
        match_found = match_found or (valid and expected_hit)
        rows.append(benchmark.build_row(
            task=task,
            arm=PROTOTYPE_ARM,
            action_type="validate_evidence",
            step_index=order - order_start,
            order_index=order,
            observation_status="observed" if valid else "failed_safe",
            result_bucket="evidence_added" if valid else "evidence_rejected",
            evidence_delta_bucket="delta_1" if valid else "delta_0",
            latency_bucket=benchmark.bucket_latency(validate_latency),
            failure_bucket="none" if valid else "validation_failed",
            outcome_bucket="success_bucket" if valid and expected_hit else ("partial_bucket" if valid else "failure_bucket"),
            evidence_required=True,
            evidence_linked=valid,
            stale=not valid,
        ))
        order += 1
        if read_count == 1 and len(candidates) > 1:
            guarded = guarded_read_order(task, candidates, first_payload)
            if guarded:
                guard_reordered = guarded[0] != 1
                read_indices.extend(guarded[:1])

    if match_found:
        final_failure = "none"
        final_result = "workflow_advanced"
        final_outcome = "success_bucket"
        final_observation = "observed"
    elif candidate_count == 0:
        final_failure = "missing_source"
        final_result = "failure"
        final_outcome = "failure_bucket"
        final_observation = "failed_safe"
    elif validation_failure:
        final_failure = "validation_failed"
        final_result = "failure"
        final_outcome = "failure_bucket"
        final_observation = "failed_safe"
    elif wrong_file_seen:
        final_failure = "other"
        final_result = "failure"
        final_outcome = "failure_bucket"
        final_observation = "failed_safe"
    else:
        final_failure = "other"
        final_result = "failure"
        final_outcome = "partial_bucket"
        final_observation = "failed_safe"
    rows.append(benchmark.build_row(
        task=task,
        arm=PROTOTYPE_ARM,
        action_type="workflow_step",
        step_index=order - order_start,
        order_index=order,
        observation_status=final_observation,
        result_bucket=final_result,
        evidence_delta_bucket="delta_1" if match_found else "delta_0",
        latency_bucket="lt_1s",
        failure_bucket=final_failure,
        outcome_bucket=final_outcome,
        evidence_required=False,
        evidence_linked=False,
    ))
    order += 1
    label = {
        "trace_id": benchmark.private_ref("trace", task.opaque_id, PROTOTYPE_ARM),
        "task_id_private": benchmark.private_ref("task", task.opaque_id),
        "arm_private": benchmark.private_ref("arm", PROTOTYPE_ARM),
        "expected_path_after_action_private": task.expected_path,
        "expected_range_after_action_private": task.expected_range,
        "retrieval_channel_after_action_private": channel,
        "validated_current_evidence_matches_private_expected_workflow_need": match_found,
        "label_timing": "after_action",
    }
    stats = {
        "arm": PROTOTYPE_ARM,
        "family": task.family,
        "candidate_count": candidate_count,
        "read_count": read_count,
        "validate_count": validate_count,
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "success": match_found,
        "no_hit": candidate_count == 0,
        "wrong_file_or_rank_miss": (not match_found) and wrong_file_seen,
        "read_budget_or_topk_pressure": (not match_found) and read_count >= 2 and candidate_count > read_count,
        "stale_or_currentness_failure": (not match_found) and stale_currentness_failure,
        "validation_failure": (not match_found) and validation_failure,
        "guard_reordered": guard_reordered,
        "availability": availability,
        "latency_buckets": [benchmark.bucket_latency(retrieval_latency)],
    }
    return rows, stats, label, order


def run_executable_prototype(confirm_private_input: bool, confirm_private_output: bool, trace_jsonl: Path | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    previous_rows, previous_labels, previous_manifest = load_previous_private_inputs(confirm_private_input, trace_jsonl)
    if not confirm_private_output:
        raise PrototypeError("--confirm-private-output is required before writing private bounded repair prototype rows")
    binary = benchmark.ensure_openlocus()
    private_root = REPO / "runs" / f"{PRIVATE_PREFIX}{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    private_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    order = 0
    for task in benchmark.TASKS:
        task_rows, task_stats, task_label, order = run_prototype_task(binary, private_root, task, order)
        rows.extend(task_rows)
        stats.append(task_stats)
        labels.append(task_label)
    errors = schema.validate_trace_rows(rows)
    if errors:
        raise PrototypeError("private prototype rows failed Phase-1 schema validation: " + "; ".join(errors[:5]))
    trace_path = private_root / TRACE_FILENAME
    label_path = private_root / LABEL_FILENAME
    write_jsonl(trace_path, rows)
    write_jsonl(label_path, labels)
    manifest = {
        "storage_class": "ignored_repo_runs_private_jsonl",
        "row_count": len(rows),
        "episode_count": len({row["trace_identity"]["trace_id"] for row in rows}),
        "task_count": len(benchmark.TASKS),
        "prototype_arm": PROTOTYPE_ARM,
        "private_trace_path": str(trace_path),
        "private_label_path": str(label_path),
        "private_output_confirmation": "confirmed",
    }
    return rows, stats, labels, manifest, previous_rows, previous_labels, previous_manifest


def previous_rates(previous_rows: list[dict[str, Any]], previous_labels: list[dict[str, Any]]) -> dict[str, tuple[int, int]]:
    metrics = decomposition.trace_metrics(previous_rows, previous_labels)
    total = Counter(item["arm"] for item in metrics.values())
    success = Counter(item["arm"] for item in metrics.values() if item["success"])
    return {arm: (success.get(arm, 0), total.get(arm, 0)) for arm in benchmark.ARMS}


def previous_mechanisms(previous_rows: list[dict[str, Any]], previous_labels: list[dict[str, Any]]) -> Counter[str]:
    metrics = decomposition.trace_metrics(previous_rows, previous_labels)
    groups: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for item in metrics.values():
        groups[item["task_private"]][item["arm"]] = item
    counts: Counter[str] = Counter({name: 0 for name in MECHANISM_KEYS})
    for group in groups.values():
        cand = group.get(PREVIOUS_HYBRID_ARM)
        if not cand or cand.get("success"):
            continue
        mechanism = decomposition.classify_loss(cand, group)
        if mechanism == "wrong_file_or_rank_miss":
            counts["wrong_file_or_rank_miss"] += 1
        if mechanism == "read_budget_or_topk_limit" or (cand.get("read_count", 0) >= 2 and cand.get("topk_candidates_present")):
            counts["read_budget_or_topk_pressure"] += 1
        if cand.get("no_candidate"):
            counts["no_hit"] += 1
        if cand.get("validation_failed") or cand.get("stale_or_invalid"):
            counts["validation_failure"] += 1
            counts["stale_or_currentness_failure"] += 1
    return counts


def prototype_mechanisms(stats: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter({name: 0 for name in MECHANISM_KEYS})
    for item in stats:
        if item.get("wrong_file_or_rank_miss"):
            counts["wrong_file_or_rank_miss"] += 1
        if item.get("read_budget_or_topk_pressure"):
            counts["read_budget_or_topk_pressure"] += 1
        if item.get("no_hit"):
            counts["no_hit"] += 1
        if item.get("stale_or_currentness_failure"):
            counts["stale_or_currentness_failure"] += 1
        if item.get("validation_failure"):
            counts["validation_failure"] += 1
    return counts


def validation_buckets(rows: list[dict[str, Any]], labels: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    errors = schema.validate_trace_rows(rows)
    state_currentness = Counter(row["state_features"]["currentness_bucket"] for row in rows)
    labels_after_action = all(row["outcome_label"]["label_timing"] == "after_action" and row["outcome_label"]["label_used_in_state_or_action_bool"] is False for row in rows) and all(label.get("label_timing") == "after_action" for label in labels)
    return {
        "private_row_count_bucket": bucket_count(int(manifest.get("row_count", len(rows)))),
        "private_episode_count_bucket": bucket_count(int(manifest.get("episode_count", 0))),
        "phase1_schema": "passed" if not errors else "failed",
        "schema_error_bucket": bucket_count(len(errors)),
        "label_after_action": "passed" if labels_after_action else "failed",
        "currentness_leakage": "passed" if set(state_currentness) == {"not_checked"} else "failed",
    }


def choose_status(readbacks_ok: bool, validation: dict[str, Any], proto: tuple[int, int], prev: tuple[int, int], best: tuple[int, int], prototype_arm_present: bool, mechanism_improved: bool) -> tuple[str, str, str]:
    if validation.get("phase1_schema") != "passed" or validation.get("currentness_leakage") != "passed" or validation.get("label_after_action") != "passed" or not readbacks_ok:
        return STATUS_FAILURE, AUTH_FAILURE, "targeted_privacy_schema_currentness_repair_only"
    if not prototype_arm_present or proto[1] == 0:
        return STATUS_INCOMPLETE, AUTH_INCOMPLETE, "targeted_bounded_retrieval_repair_prototype_repair_only"
    vs_prev = delta_bucket(*proto, *prev)
    vs_best = delta_bucket(*proto, *best)
    if vs_prev == "positive_lift" and vs_best == "positive_lift" and mechanism_improved:
        return STATUS_POSITIVE, AUTH_HELDOUT, "heldout_same_budget_retrieval_repair_validation_design_authorized"
    if vs_prev == "positive_lift" and vs_best != "positive_lift":
        return STATUS_PARTIAL, AUTH_PARTIAL, "failure_decomposition_or_metric_task_balance_review"
    return STATUS_NO_LIFT, AUTH_STOP, "failure_decomposition_or_stop_current_candidate"


def build_report(
    rows: list[dict[str, Any]],
    stats: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    manifest: dict[str, Any],
    previous_rows: list[dict[str, Any]],
    previous_labels: list[dict[str, Any]],
    previous_manifest: dict[str, Any],
    bench_report: dict[str, Any],
    decomp_report: dict[str, Any],
    design_report: dict[str, Any],
) -> dict[str, Any]:
    readbacks = source_readbacks(bench_report, decomp_report, design_report)
    prev_rates = previous_rates(previous_rows, previous_labels)
    proto_success = sum(1 for item in stats if item.get("success"))
    proto_total = len(stats)
    prev_hybrid = prev_rates.get(PREVIOUS_HYBRID_ARM, (0, 0))
    baseline_rates = [prev_rates.get(arm, (0, 0)) for arm in benchmark.BASELINE_ARMS]
    best_baseline = max(baseline_rates, key=lambda pair: (pair[0] / pair[1]) if pair[1] else 0.0) if baseline_rates else (0, 0)
    validation = validation_buckets(rows, labels, manifest)
    proto_mech = prototype_mechanisms(stats)
    prev_mech = previous_mechanisms(previous_rows, previous_labels)
    prototype_arm_present = {item.get("arm") for item in stats} == {PROTOTYPE_ARM}
    mechanism_delta = {name: prev_mech.get(name, 0) - proto_mech.get(name, 0) for name in MECHANISM_KEYS}
    mechanism_improved = any(value > 0 for value in mechanism_delta.values())
    status, authorized, decision = choose_status(source_readbacks_ok(readbacks), validation, (proto_success, proto_total), prev_hybrid, best_baseline, prototype_arm_present, mechanism_improved)
    max_candidate_count = max((int(item.get("candidate_count", 0)) for item in stats), default=0)
    max_read_count = max((int(item.get("read_count", 0)) for item in stats), default=0)
    max_validate_count = max((int(item.get("validate_count", 0)) for item in stats), default=0)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "source_readbacks": readbacks,
        "execution_attestations": {
            "executable_bounded_prototype": True,
            "prototype_arm": PROTOTYPE_ARM,
            "prototype_arm_count_bucket": bucket_count(1 if prototype_arm_present else 0),
            "same_task_set_as_phase5": True,
            "same_candidate_cap_bucket": "count_2_to_5",
            "same_read_cap_bucket": "count_2_to_5",
            "same_validate_cap_bucket": "count_2_to_5",
            "allowed_channel_families": list(ALLOWED_CHANNEL_FAMILIES),
            "executed_candidate_channel_families": list(EXECUTED_CHANNEL_FAMILIES),
            "new_channel_family_used": False,
            "wrong_file_intent_guard_before_second_read": True,
            "undecidable_guard_uses_fixed_ordering": True,
            "local_openlocus_actions_executed": True,
            "source_scan_executed": False,
            "candidate_generation_executed": False,
            "candidate_expansion_executed": False,
            "provider_or_model_calls_executed": False,
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "training_executed": False,
            "runtime_default_changed": False,
            "kernel_hardening_executed": False,
        },
        "trace_validation_buckets": {
            **validation,
            "previous_private_row_count_bucket": bucket_count(int(previous_manifest.get("row_count", len(previous_rows)))),
            "previous_private_episode_count_bucket": bucket_count(int(previous_manifest.get("episode_count", 0))),
            "observed_max_candidate_count_bucket": bucket_count(max_candidate_count),
            "observed_max_read_count_bucket": bucket_count(max_read_count),
            "observed_max_validate_count_bucket": bucket_count(max_validate_count),
        },
        "arm_comparison": {
            "prototype_utility_bucket": bucket_rate(proto_success, proto_total),
            "previous_hybrid_bucket": bucket_rate(*prev_hybrid),
            "best_fixed_baseline_bucket": bucket_rate(*best_baseline),
            "delta_prototype_vs_previous_hybrid": delta_bucket(proto_success, proto_total, *prev_hybrid),
            "delta_prototype_vs_best_fixed_baseline": delta_bucket(proto_success, proto_total, *best_baseline),
        },
        "mechanism_impact_buckets": {
            "prototype_failure_buckets": {name: bucket_count(proto_mech.get(name, 0)) for name in MECHANISM_KEYS},
            "previous_hybrid_failure_buckets": {name: bucket_count(prev_mech.get(name, 0)) for name in MECHANISM_KEYS},
            "reduced_failure_buckets": {name: bucket_count(max(0, value)) for name, value in mechanism_delta.items()},
            "any_mechanism_improved": mechanism_improved,
        },
        "privacy_contract": {
            "publication_level": "aggregate_only",
            "private_input_confirmation": "confirmed",
            "private_output_confirmation": manifest.get("private_output_confirmation"),
            "raw_paths_public": False,
            "queries_public": False,
            "ranges_public": False,
            "snippets_public": False,
            "hashes_public": False,
            "raw_task_ids_public": False,
            "private_refs_public": False,
            "private_trace_path_public": False,
            "private_label_path_public": False,
            "private_trace_rows_public": False,
            "raw_rows_public": False,
            "per_task_outcomes_public": False,
            "evidence_filenames_public": False,
            "exact_labels_public": False,
            "provider_payloads_public": False,
            "raw_publication": False,
        },
        "stop_go": {
            "decision": decision,
            "authorized_next_phase": authorized,
            "explicitly_forbidden": sorted(PUBLIC_FORBIDDEN),
            "targeted_repair_only_if_incomplete_or_schema_privacy_currentness_failure": status in {STATUS_INCOMPLETE, STATUS_FAILURE},
            "stop_or_failure_decomposition_if_no_lift": status == STATUS_NO_LIFT,
            "partial_lift_not_best_baseline_no_method_claim": status == STATUS_PARTIAL,
            "heldout_design_only_if_positive_same_budget": status == STATUS_POSITIVE,
            "d2_or_model_scaling_authorized": False,
            "rpm_training_authorized": False,
            "runtime_or_default_authorized": False,
            "provider_network_ci_authorized": False,
            "method_scale_winner_default_claims_allowed": False,
            "broad_source_scan_authorized": False,
            "candidate_expansion_authorized": False,
            "new_channel_family_authorized": False,
            "kernel_hardening_authorized": False,
            "raw_publication_authorized": False,
            "frk_j_b_c_i_revival_authorized": False,
        },
        "validation_summary": {
            "privacy_leak_scan": "pending",
            "self_test_mutation_coverage": "available",
            "public_report_level": "aggregate_only",
        },
    }


REPORT_KEYS = {
    "schema_version", "phase", "status", "source_readbacks", "execution_attestations", "trace_validation_buckets",
    "arm_comparison", "mechanism_impact_buckets", "privacy_contract", "stop_go", "validation_summary",
}
SOURCE_KEYS = set(source_readbacks({}, {}, {}))
EXECUTION_KEYS = {
    "executable_bounded_prototype", "prototype_arm", "prototype_arm_count_bucket", "same_task_set_as_phase5", "same_candidate_cap_bucket",
    "same_read_cap_bucket", "same_validate_cap_bucket", "allowed_channel_families", "executed_candidate_channel_families", "new_channel_family_used",
    "wrong_file_intent_guard_before_second_read", "undecidable_guard_uses_fixed_ordering", "local_openlocus_actions_executed", "source_scan_executed",
    "candidate_generation_executed", "candidate_expansion_executed", "provider_or_model_calls_executed", "network_access", "ci_execution",
    "training_executed", "runtime_default_changed", "kernel_hardening_executed",
}
TRACE_VALIDATION_KEYS = {
    "private_row_count_bucket", "private_episode_count_bucket", "phase1_schema", "schema_error_bucket", "label_after_action", "currentness_leakage",
    "previous_private_row_count_bucket", "previous_private_episode_count_bucket", "observed_max_candidate_count_bucket", "observed_max_read_count_bucket",
    "observed_max_validate_count_bucket",
}
ARM_COMPARISON_KEYS = {"prototype_utility_bucket", "previous_hybrid_bucket", "best_fixed_baseline_bucket", "delta_prototype_vs_previous_hybrid", "delta_prototype_vs_best_fixed_baseline"}
PRIVACY_KEYS = {
    "publication_level", "private_input_confirmation", "private_output_confirmation", "raw_paths_public", "queries_public", "ranges_public", "snippets_public",
    "hashes_public", "raw_task_ids_public", "private_refs_public", "private_trace_path_public", "private_label_path_public", "private_trace_rows_public",
    "raw_rows_public", "per_task_outcomes_public", "evidence_filenames_public", "exact_labels_public", "provider_payloads_public", "raw_publication",
}
STOP_KEYS = {
    "decision", "authorized_next_phase", "explicitly_forbidden", "targeted_repair_only_if_incomplete_or_schema_privacy_currentness_failure",
    "stop_or_failure_decomposition_if_no_lift", "partial_lift_not_best_baseline_no_method_claim", "heldout_design_only_if_positive_same_budget",
    "d2_or_model_scaling_authorized", "rpm_training_authorized", "runtime_or_default_authorized", "provider_network_ci_authorized",
    "method_scale_winner_default_claims_allowed", "broad_source_scan_authorized", "candidate_expansion_authorized", "new_channel_family_authorized",
    "kernel_hardening_authorized", "raw_publication_authorized", "frk_j_b_c_i_revival_authorized",
}
VALIDATION_KEYS = {"privacy_leak_scan", "self_test_mutation_coverage", "public_report_level"}
COUNT_BUCKETS = {"count_0", "count_1", "count_2_to_5", "count_6_to_20", "count_21_to_50", "count_gt_50"}
RATE_BUCKETS = {"rate_0", "rate_lt_25", "rate_25_to_50", "rate_50_to_75", "rate_75_to_99", "rate_1"}
DELTA_BUCKETS = {"positive_lift", "neutral_no_lift", "negative_delta"}
STATUSES = {STATUS_INCOMPLETE, STATUS_NO_LIFT, STATUS_PARTIAL, STATUS_POSITIVE, STATUS_FAILURE}
AUTH_BY_STATUS = {
    STATUS_INCOMPLETE: AUTH_INCOMPLETE,
    STATUS_FAILURE: AUTH_FAILURE,
    STATUS_NO_LIFT: AUTH_STOP,
    STATUS_PARTIAL: AUTH_PARTIAL,
    STATUS_POSITIVE: AUTH_HELDOUT,
}
DECISION_BY_STATUS = {
    STATUS_INCOMPLETE: "targeted_bounded_retrieval_repair_prototype_repair_only",
    STATUS_FAILURE: "targeted_privacy_schema_currentness_repair_only",
    STATUS_NO_LIFT: "failure_decomposition_or_stop_current_candidate",
    STATUS_PARTIAL: "failure_decomposition_or_metric_task_balance_review",
    STATUS_POSITIVE: "heldout_same_budget_retrieval_repair_validation_design_authorized",
}


def strings_in(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(strings_in(item))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(strings_in(item))
        return out
    return []


def public_leak_errors(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    path_pattern = re.compile(r"(/workspace/|runs/|\.jsonl\b|\b(?:crates|eval|docs|scripts)/[^\s]+|:[0-9]+-[0-9]+)")
    task_pattern = re.compile(r"\bwf[0-9]{2}\b")
    hash_pattern = re.compile(r"\b[a-f0-9]{32,}\b", re.I)
    for text in strings_in(report):
        if "private_ref_" in text:
            errors.append("private_ref leak")
        if "content_sha" in text:
            errors.append("hash/snippet leak")
        if path_pattern.search(text):
            errors.append("raw path/query/snippet/private file leak")
        if task_pattern.search(text):
            errors.append("raw task id leak")
        if hash_pattern.search(text):
            errors.append("hash leak")
        if text.startswith("{") and "trace_identity" in text:
            errors.append("raw row leak")
    return errors


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be object"]
    if set(report) != REPORT_KEYS:
        errors.append("unknown or missing top-level keys")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append("schema_version drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    status = report.get("status")
    if status not in STATUSES:
        errors.append("unknown status")
        status = ""
    source = report.get("source_readbacks", {})
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        errors.append("source readback keys drift")
    elif not source_readbacks_ok(source):
        errors.append("bad source status/mechanism/gate readback")
    att = report.get("execution_attestations", {})
    if not isinstance(att, dict) or set(att) != EXECUTION_KEYS:
        errors.append("execution attestation keys drift")
    for field in ("executable_bounded_prototype", "same_task_set_as_phase5", "wrong_file_intent_guard_before_second_read", "undecidable_guard_uses_fixed_ordering", "local_openlocus_actions_executed"):
        if att.get(field) is not True:
            errors.append(f"execution_attestations.{field} must be true")
    if att.get("prototype_arm") != PROTOTYPE_ARM or att.get("prototype_arm_count_bucket") != "count_1":
        errors.append("prototype arm missing or drifted")
    for field in ("same_candidate_cap_bucket", "same_read_cap_bucket", "same_validate_cap_bucket"):
        if att.get(field) != "count_2_to_5":
            errors.append(f"{field} same-budget drift")
    if set(att.get("allowed_channel_families", [])) != set(ALLOWED_CHANNEL_FAMILIES):
        errors.append("allowed channel family drift")
    if not set(att.get("executed_candidate_channel_families", [])).issubset(set(ALLOWED_CHANNEL_FAMILIES)):
        errors.append("new channel family executed")
    for field in ("new_channel_family_used", "source_scan_executed", "candidate_generation_executed", "candidate_expansion_executed", "provider_or_model_calls_executed", "training_executed", "runtime_default_changed", "kernel_hardening_executed"):
        if att.get(field) is not False:
            errors.append(f"execution_attestations.{field} must be false")
    if att.get("network_access") != "no_network" or att.get("ci_execution") != "local_manual_only":
        errors.append("provider/network/CI attestation drift")
    trace = report.get("trace_validation_buckets", {})
    if not isinstance(trace, dict) or set(trace) != TRACE_VALIDATION_KEYS:
        errors.append("trace validation key drift")
    for field in ("private_row_count_bucket", "private_episode_count_bucket", "previous_private_row_count_bucket", "previous_private_episode_count_bucket"):
        if trace.get(field) not in COUNT_BUCKETS:
            errors.append(f"{field} bucket drift")
    if trace.get("phase1_schema") != "passed" or trace.get("schema_error_bucket") != "count_0":
        errors.append("Phase-1 schema invalid")
    if trace.get("label_after_action") != "passed":
        errors.append("label-after-action violation")
    if trace.get("currentness_leakage") != "passed":
        errors.append("post-action currentness leaked into state")
    cmp = report.get("arm_comparison", {})
    if not isinstance(cmp, dict) or set(cmp) != ARM_COMPARISON_KEYS:
        errors.append("arm comparison keys drift")
    for field in ("prototype_utility_bucket", "previous_hybrid_bucket", "best_fixed_baseline_bucket"):
        if cmp.get(field) not in RATE_BUCKETS:
            errors.append(f"{field} rate bucket drift")
    for field in ("delta_prototype_vs_previous_hybrid", "delta_prototype_vs_best_fixed_baseline"):
        if cmp.get(field) not in DELTA_BUCKETS:
            errors.append(f"{field} delta drift")
    mechanisms = report.get("mechanism_impact_buckets", {})
    if not isinstance(mechanisms, dict) or set(mechanisms) != {"prototype_failure_buckets", "previous_hybrid_failure_buckets", "reduced_failure_buckets", "any_mechanism_improved"}:
        errors.append("mechanism impact key drift")
    else:
        for section in (mechanisms.get("prototype_failure_buckets"), mechanisms.get("previous_hybrid_failure_buckets"), mechanisms.get("reduced_failure_buckets")):
            if not isinstance(section, dict) or set(section) != set(MECHANISM_KEYS) or any(value not in COUNT_BUCKETS for value in section.values()):
                errors.append("mechanism bucket drift")
        if mechanisms.get("any_mechanism_improved") is not any(value != "count_0" for value in mechanisms.get("reduced_failure_buckets", {}).values()):
            errors.append("mechanism improvement summary drift")
    privacy = report.get("privacy_contract", {})
    if not isinstance(privacy, dict) or set(privacy) != PRIVACY_KEYS:
        errors.append("privacy contract keys drift")
    if privacy.get("publication_level") != "aggregate_only" or privacy.get("private_input_confirmation") != "confirmed" or privacy.get("private_output_confirmation") != "confirmed":
        errors.append("privacy confirmation/publication drift")
    for field in PRIVACY_KEYS - {"publication_level", "private_input_confirmation", "private_output_confirmation"}:
        if privacy.get(field) is not False:
            errors.append(f"privacy_contract.{field} must be false")
    stop = report.get("stop_go", {})
    if not isinstance(stop, dict) or set(stop) != STOP_KEYS:
        errors.append("stop/go keys drift")
    if stop.get("authorized_next_phase") != AUTH_BY_STATUS.get(status):
        errors.append("authorized next phase drift")
    if stop.get("decision") != DECISION_BY_STATUS.get(status):
        errors.append("stop/go decision drift")
    if set(stop.get("explicitly_forbidden", [])) != PUBLIC_FORBIDDEN:
        errors.append("forbidden route set drift")
    if stop.get("authorized_next_phase") in stop.get("explicitly_forbidden", []):
        errors.append("forbidden phase authorized")
    expected_flags = {
        "targeted_repair_only_if_incomplete_or_schema_privacy_currentness_failure": status in {STATUS_INCOMPLETE, STATUS_FAILURE},
        "stop_or_failure_decomposition_if_no_lift": status == STATUS_NO_LIFT,
        "partial_lift_not_best_baseline_no_method_claim": status == STATUS_PARTIAL,
        "heldout_design_only_if_positive_same_budget": status == STATUS_POSITIVE,
    }
    for field, expected in expected_flags.items():
        if stop.get(field) is not expected:
            errors.append(f"stop_go.{field} inconsistent with status")
    for field in ("d2_or_model_scaling_authorized", "rpm_training_authorized", "runtime_or_default_authorized", "provider_network_ci_authorized", "method_scale_winner_default_claims_allowed", "broad_source_scan_authorized", "candidate_expansion_authorized", "new_channel_family_authorized", "kernel_hardening_authorized", "raw_publication_authorized", "frk_j_b_c_i_revival_authorized"):
        if stop.get(field) is not False:
            errors.append(f"stop_go.{field} must be false")
    if status in {STATUS_INCOMPLETE, STATUS_FAILURE} and trace.get("phase1_schema") == "passed" and trace.get("label_after_action") == "passed" and trace.get("currentness_leakage") == "passed" and source_readbacks_ok(source):
        errors.append("repair/failure status requires source/schema/privacy/currentness failure or incomplete prototype")
    for field in ("observed_max_candidate_count_bucket", "observed_max_read_count_bucket", "observed_max_validate_count_bucket"):
        if trace.get(field) != "count_2_to_5":
            errors.append(f"{field} observed budget drift")
    if status == STATUS_POSITIVE and (cmp.get("delta_prototype_vs_previous_hybrid") != "positive_lift" or cmp.get("delta_prototype_vs_best_fixed_baseline") != "positive_lift" or trace.get("phase1_schema") != "passed" or report.get("validation_summary", {}).get("privacy_leak_scan") != "passed" or mechanisms.get("any_mechanism_improved") is not True):
        errors.append("fake positive without positive deltas or schema/privacy pass")
    if status == STATUS_PARTIAL and cmp.get("delta_prototype_vs_previous_hybrid") != "positive_lift":
        errors.append("partial lift requires positive previous-hybrid delta")
    validation = report.get("validation_summary", {})
    if not isinstance(validation, dict) or set(validation) != VALIDATION_KEYS:
        errors.append("validation summary keys drift")
    if validation.get("privacy_leak_scan") != "passed":
        errors.append("privacy leak scan not passed")
    if validation.get("self_test_mutation_coverage") != "available" or validation.get("public_report_level") != "aggregate_only":
        errors.append("validation summary drift")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    final = copy.deepcopy(report)
    final["validation_summary"]["privacy_leak_scan"] = "passed" if not public_leak_errors(final) else "failed"
    errors = validate_public_report(final)
    if errors:
        raise PrototypeError("public report validation failed: " + "; ".join(errors[:12]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fixture_rows_stats(success_count: int = 13) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    order = 0
    for idx, task in enumerate(benchmark.TASKS):
        success = idx < success_count
        for step, action_type in enumerate(("bounded_retrieval", "read_current_source", "validate_evidence", "workflow_step")):
            rows.append(benchmark.build_row(
                task=task,
                arm=PROTOTYPE_ARM,
                action_type=action_type,
                step_index=step,
                order_index=order,
                observation_status="observed" if success else "failed_safe",
                result_bucket="workflow_advanced" if action_type == "workflow_step" and success else ("failure" if action_type == "workflow_step" else "evidence_added"),
                evidence_delta_bucket="delta_1" if success else "delta_0",
                latency_bucket="lt_1s",
                failure_bucket="none" if success else ("other" if action_type == "workflow_step" else "none"),
                outcome_bucket="success_bucket" if success else "failure_bucket",
                evidence_required=action_type != "workflow_step",
                evidence_linked=action_type != "workflow_step",
            ))
            order += 1
        stats.append({
            "arm": PROTOTYPE_ARM,
            "family": task.family,
            "candidate_count": 5,
            "read_count": 2,
            "validate_count": 2,
            "valid_count": 2,
            "invalid_count": 0,
            "success": success,
            "no_hit": False,
            "wrong_file_or_rank_miss": not success,
            "read_budget_or_topk_pressure": not success,
            "stale_or_currentness_failure": False,
            "validation_failure": False,
            "guard_reordered": False,
            "availability": "available",
            "latency_buckets": ["lt_1s"],
        })
        labels.append({"trace_id": benchmark.private_ref("trace", task.opaque_id, PROTOTYPE_ARM), "label_timing": "after_action"})
    manifest = {"row_count": len(rows), "episode_count": len(stats), "task_count": len(benchmark.TASKS), "private_output_confirmation": "confirmed"}
    return rows, stats, labels, manifest


def fixture_previous(success_hybrid: int = 8, success_text: int = 11, success_symbol: int = 6) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    order = 0
    success_map = {"text_bm25_baseline": success_text, "symbol_regex_baseline": success_symbol, PREVIOUS_HYBRID_ARM: success_hybrid}
    for task_idx, task in enumerate(benchmark.TASKS):
        for arm in benchmark.ARMS:
            success = task_idx < success_map[arm]
            for step, action_type in enumerate(("bounded_retrieval", "read_current_source", "validate_evidence", "workflow_step")):
                rows.append(benchmark.build_row(task=task, arm=arm, action_type=action_type, step_index=step, order_index=order, observation_status="observed" if success else "failed_safe", result_bucket="workflow_advanced" if action_type == "workflow_step" and success else ("failure" if action_type == "workflow_step" else "evidence_added"), evidence_delta_bucket="delta_1" if success else "delta_0", latency_bucket="lt_1s", failure_bucket="none" if success else ("other" if action_type == "workflow_step" else "none"), outcome_bucket="success_bucket" if success else "failure_bucket", evidence_required=action_type != "workflow_step", evidence_linked=action_type != "workflow_step"))
                order += 1
            labels.append({"trace_id": benchmark.private_ref("trace", task.opaque_id, arm), "task_id_private": benchmark.private_ref("task", task.opaque_id), "arm_private": benchmark.private_ref("arm", arm), "validated_current_evidence_matches_private_expected_workflow_need": success, "label_timing": "after_action"})
    return rows, labels, {"row_count": len(rows), "episode_count": len(labels), "labels_present": True}


def fixture_source_reports() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    bench = {"status": benchmark.STATUS_NO_LIFT, "best_baseline_comparison": {"candidate_vs_best_baseline_delta_bucket": "negative_vs_best_baseline"}, "validation_summary": {"strict_phase1_schema": "passed", "privacy_leak_scan": "passed"}}
    decomp = {"status": decomposition.STATUS_RETRIEVAL_REPAIR, "decomposition_summary": {"primary_mechanism_bucket": "wrong_file_or_rank_miss", "secondary_mechanism_bucket": "read_budget_or_topk_limit", "confidence_bucket": "high"}}
    des = {"status": design.STATUS_CONCRETE, "stop_go": {"authorized_next_phase": design.AUTH_CONCRETE}, "static_replay_simulation_summary": {"concrete_design_gate_results": {"same_candidate_cap": True, "same_read_cap": True, "no_new_retrieval_channel_family": True}}, "validation_summary": {"concrete_design_gates_passed": True}}
    return bench, decomp, des


def fixture_report(success_count: int = 13) -> dict[str, Any]:
    rows, stats, labels, manifest = fixture_rows_stats(success_count)
    prev_rows, prev_labels, prev_manifest = fixture_previous()
    bench, decomp, des = fixture_source_reports()
    report = build_report(rows, stats, labels, manifest, prev_rows, prev_labels, prev_manifest, bench, decomp, des)
    report["validation_summary"]["privacy_leak_scan"] = "passed"
    return report


def run_self_tests() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, condition))

    valid = fixture_report()
    check("fixture_report_valid", not validate_public_report(valid))
    check("fixture_rows_schema_valid", not schema.validate_trace_rows(fixture_rows_stats()[0]))
    try:
        load_previous_private_inputs(False)
        check("missing_private_input_confirmation_rejected", False)
    except PrototypeError:
        check("missing_private_input_confirmation_rejected", True)
    tmp = REPO / "artifacts" / "frk_product_workflow_bounded_retrieval_repair_prototype" / "selftest_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        bad = tmp / "bad.jsonl"
        bad.write_text("{bad}\n", encoding="utf-8")
        try:
            load_previous_private_inputs(True, bad)
            check("schema_invalid_or_malformed_private_rows_rejected", False)
        except PrototypeError:
            check("schema_invalid_or_malformed_private_rows_rejected", True)
    finally:
        for child in tmp.glob("*"):
            child.unlink()
        tmp.rmdir()
    rows, stats, labels, manifest = fixture_rows_stats()
    prev_rows, prev_labels, prev_manifest = fixture_previous()
    bench, decomp, des = fixture_source_reports()
    try:
        run_executable_prototype(True, False)
        check("missing_private_output_confirmation_rejected", False)
    except PrototypeError:
        check("missing_private_output_confirmation_rejected", True)
    mutations: list[tuple[str, list[str], Any]] = [
        ("bad_source_status_rejected", ["source_readbacks", "benchmark_status"], "bad"),
        ("bad_source_mechanism_rejected", ["source_readbacks", "decomposition_primary_mechanism"], "bad"),
        ("bad_design_gate_rejected", ["source_readbacks", "design_no_new_channel_gate"], False),
        ("label_leakage_rejected", ["trace_validation_buckets", "label_after_action"], "failed"),
        ("post_action_currentness_state_rejected", ["trace_validation_buckets", "currentness_leakage"], "failed"),
        ("phase1_schema_invalid_rejected", ["trace_validation_buckets", "phase1_schema"], "failed"),
        ("observed_candidate_budget_expansion_rejected", ["trace_validation_buckets", "observed_max_candidate_count_bucket"], "count_6_to_20"),
        ("observed_read_budget_expansion_rejected", ["trace_validation_buckets", "observed_max_read_count_bucket"], "count_6_to_20"),
        ("observed_validate_budget_expansion_rejected", ["trace_validation_buckets", "observed_max_validate_count_bucket"], "count_6_to_20"),
        ("cap_expansion_candidate_rejected", ["execution_attestations", "same_candidate_cap_bucket"], "count_6_to_20"),
        ("cap_expansion_read_rejected", ["execution_attestations", "same_read_cap_bucket"], "count_6_to_20"),
        ("cap_expansion_validate_rejected", ["execution_attestations", "same_validate_cap_bucket"], "count_6_to_20"),
        ("new_channel_family_rejected", ["execution_attestations", "allowed_channel_families"], ["bm25_text", "symbol_regex", "existing_hybrid_retrieve", "dense"]),
        ("executed_new_channel_rejected", ["execution_attestations", "executed_candidate_channel_families"], ["dense"]),
        ("source_scan_flag_rejected", ["execution_attestations", "source_scan_executed"], True),
        ("candidate_generation_flag_rejected", ["execution_attestations", "candidate_generation_executed"], True),
        ("provider_flag_rejected", ["execution_attestations", "provider_or_model_calls_executed"], True),
        ("network_flag_rejected", ["execution_attestations", "network_access"], "network_allowed"),
        ("ci_flag_rejected", ["execution_attestations", "ci_execution"], "ci"),
        ("training_flag_rejected", ["execution_attestations", "training_executed"], True),
        ("runtime_flag_rejected", ["execution_attestations", "runtime_default_changed"], True),
        ("kernel_flag_rejected", ["execution_attestations", "kernel_hardening_executed"], True),
        ("prototype_arm_missing_rejected", ["execution_attestations", "prototype_arm"], "other_arm"),
        ("same_budget_drift_rejected", ["execution_attestations", "same_task_set_as_phase5"], False),
        ("fake_positive_previous_delta_rejected", ["arm_comparison", "delta_prototype_vs_previous_hybrid"], "neutral_no_lift"),
        ("fake_positive_best_delta_rejected", ["arm_comparison", "delta_prototype_vs_best_fixed_baseline"], "negative_delta"),
        ("privacy_scan_fail_rejected", ["validation_summary", "privacy_leak_scan"], "failed"),
        ("d2_overauth_rejected", ["stop_go", "d2_or_model_scaling_authorized"], True),
        ("rpm_training_overauth_rejected", ["stop_go", "rpm_training_authorized"], True),
        ("runtime_overauth_rejected", ["stop_go", "runtime_or_default_authorized"], True),
        ("provider_ci_overauth_rejected", ["stop_go", "provider_network_ci_authorized"], True),
        ("method_winner_overauth_rejected", ["stop_go", "method_scale_winner_default_claims_allowed"], True),
        ("candidate_expansion_overauth_rejected", ["stop_go", "candidate_expansion_authorized"], True),
        ("new_channel_overauth_rejected", ["stop_go", "new_channel_family_authorized"], True),
        ("kernel_overauth_rejected", ["stop_go", "kernel_hardening_authorized"], True),
        ("frk_revival_overauth_rejected", ["stop_go", "frk_j_b_c_i_revival_authorized"], True),
        ("stop_go_decision_inconsistency_rejected", ["stop_go", "decision"], "stop_or_failure_decomposition_only"),
        ("authorized_next_phase_inconsistency_rejected", ["stop_go", "authorized_next_phase"], AUTH_STOP),
        ("unknown_top_key_rejected", ["unknown"], True),
        ("unknown_execution_key_rejected", ["execution_attestations", "unexpected"], True),
        ("unknown_stop_key_rejected", ["stop_go", "unexpected"], True),
        ("mechanism_key_drop_rejected", ["mechanism_impact_buckets", "prototype_failure_buckets"], {"wrong_file_or_rank_miss": "count_1"}),
        ("mechanism_improvement_summary_drift_rejected", ["mechanism_impact_buckets", "any_mechanism_improved"], False),
    ]
    for name, path, value in mutations:
        mutated = copy.deepcopy(valid)
        target = mutated
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        check(name, bool(validate_public_report(mutated)))
    for leak_name, leak_value in (
        ("path", "/workspace/OpenLocus/OpenLocus-Lab/runs/x.jsonl"),
        ("query", "crates/openlocus-cli/src/lib.rs:60-110"),
        ("snippet", "docs/en/research-summary.md"),
        ("hash", "a" * 64),
        ("task", "wf01"),
        ("private_ref", "private_ref_trace_abc"),
        ("raw_rows", '{"trace_identity": {}}'),
        ("per_task_outcomes", "wf03 success"),
    ):
        mutated = copy.deepcopy(valid)
        mutated["source_readbacks"]["decomposition_confidence_bucket"] = leak_value
        check(f"leak_{leak_name}_rejected", bool(validate_public_report(mutated)))
    # Failure status is valid only for real schema/privacy/source-currentness failure.
    failed_report = copy.deepcopy(valid)
    failed_report["status"] = STATUS_FAILURE
    failed_report["stop_go"]["authorized_next_phase"] = AUTH_FAILURE
    failed_report["stop_go"]["decision"] = "targeted_privacy_schema_currentness_repair_only"
    failed_report["stop_go"]["targeted_repair_only_if_incomplete_or_schema_privacy_currentness_failure"] = True
    failed_report["stop_go"]["heldout_design_only_if_positive_same_budget"] = False
    check("failure_status_without_failure_rejected", bool(validate_public_report(failed_report)))
    no_lift = fixture_report(success_count=8)
    check("no_lift_fixture_valid", not validate_public_report(no_lift))
    positive_no_mechanism = copy.deepcopy(valid)
    positive_no_mechanism["mechanism_impact_buckets"]["reduced_failure_buckets"] = {name: "count_0" for name in MECHANISM_KEYS}
    positive_no_mechanism["mechanism_impact_buckets"]["any_mechanism_improved"] = False
    check("fake_positive_without_mechanism_improvement_rejected", bool(validate_public_report(positive_no_mechanism)))
    check("self_test_count_consistency", len(checks) >= 59)
    failed = [name for name, ok in checks if not ok]
    return {"status": "passed" if not failed else "failed", "checks_passed": len(checks) - len(failed), "checks_total": len(checks), "failed_checks": failed}


def run_prototype(confirm_private_input: bool, confirm_private_output: bool, trace_jsonl: Path | None = None) -> dict[str, Any]:
    rows, stats, labels, manifest, previous_rows, previous_labels, previous_manifest = run_executable_prototype(confirm_private_input, confirm_private_output, trace_jsonl)
    return build_report(rows, stats, labels, manifest, previous_rows, previous_labels, previous_manifest, read_json(BENCH_REPORT), read_json(DECOMP_REPORT), read_json(DESIGN_REPORT))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run-prototype", action="store_true")
    parser.add_argument("--confirm-private-input", action="store_true")
    parser.add_argument("--confirm-private-output", action="store_true")
    parser.add_argument("--trace-jsonl", type=Path, default=None)
    parser.add_argument("--validate-report", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            result = run_self_tests()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "passed" else 1
        if args.run_prototype:
            report = run_prototype(args.confirm_private_input, args.confirm_private_output, args.trace_jsonl)
            write_report(report)
            final = read_json(DEFAULT_REPORT)
            print(json.dumps({
                "public_report": str(DEFAULT_REPORT),
                "status": final["status"],
                "prototype_utility_bucket": final["arm_comparison"]["prototype_utility_bucket"],
                "delta_prototype_vs_previous_hybrid": final["arm_comparison"]["delta_prototype_vs_previous_hybrid"],
                "delta_prototype_vs_best_fixed_baseline": final["arm_comparison"]["delta_prototype_vs_best_fixed_baseline"],
                "authorized_next_phase": final["stop_go"]["authorized_next_phase"],
            }, indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = read_json(args.validate_report)
            errors = validate_public_report(report)
            if errors:
                raise PrototypeError("public report validation failed: " + "; ".join(errors[:12]))
            print(f"Validation passed: {args.validate_report}")
            return 0
        parser.print_help()
        return 2
    except PrototypeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
