#!/usr/bin/env python3
"""FRK-P2 direct product-workflow TraceV2 task-state capture expansion.

This phase emits strict nested ``openlocus.state_action_trace.v2`` rows from a
predeclared bounded product-workflow manifest. It is trace capture only: it does
not add retrieval algorithms/channels, train, replay HAAE/RPM, change runtime
defaults, call providers/network/CI, harden kernels, scan broadly, or publish raw
private traces.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frk_product_workflow_bounded_retrieval_repair_prototype as repair_proto
import frk_product_workflow_trace_benchmark as benchmark
import state_action_trace_v2_bootstrap as tracev2


REPO = Path(__file__).resolve().parent.parent
PHASE = "openlocus_v2_frk_p2_workflow_v2_task_state_capture_expansion"
REPORT_SCHEMA_VERSION = "frk_p2_workflow_v2_task_state_capture_expansion_public_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / "frk_p2_workflow_v2_task_state_capture_expansion" / "frk_p2_workflow_v2_task_state_capture_expansion_report.json"
TRACEV2_A_REPORT = tracev2.DEFAULT_REPORT
PRIVATE_PREFIX = "frk_p2_workflow_v2_capture_private_"
PRIVATE_ROW_FILENAME = "frk_p2_workflow_v2_state_action_rows.jsonl"

STATUS_HAAE = "frk_p2_workflow_v2_capture_complete_haae_a2_replay_authorized"
STATUS_CAPTURE_REPAIR = "frk_p2_workflow_v2_capture_complete_targeted_capture_repair_only"
STATUS_LABEL_REPAIR = "frk_p2_workflow_v2_capture_complete_label_or_proxy_repair_only"
STATUS_FAILED = "frk_p2_workflow_v2_capture_failed_schema_privacy_currentness_repair_only"
STATUS_STOPPED = "frk_p2_workflow_v2_capture_stopped_insufficient_product_workflow_substrate"

AUTH_HAAE = "haae_a2_offline_action_replay_smoke_over_frk_p2_v2_rows"
AUTH_CAPTURE_REPAIR = "targeted_frk_p2_workflow_v2_capture_repair_only"
AUTH_LABEL_REPAIR = "targeted_frk_p2_label_or_proxy_repair_only"
AUTH_SCHEMA_REPAIR = "targeted_frk_p2_schema_privacy_currentness_repair_only"
AUTH_STOP = "none_insufficient_product_workflow_substrate"

ALLOWED_CHANNELS = ("bm25_text", "symbol_regex", "existing_hybrid_retrieve")
ACTION_SEQUENCE = ("retrieve_candidates", "read_next", "validate_now", "stop")
FORBIDDEN = {
    "new_retrieval_algorithm",
    "new_channel_family",
    "broad_source_scan",
    "candidate_expansion_beyond_fixed_caps",
    "provider_claim",
    "model_provider_call",
    "network_claim",
    "ci_claim",
    "rpm_d2_training",
    "training_claim",
    "model_scaling",
    "haae_a2_replay_inside_phase",
    "runtime_default_claim",
    "method_claim",
    "scale_claim",
    "winner_claim",
    "default_claim",
    "kernel_hardening",
    "raw_publication",
    "private_trace_publication",
    "frk_j",
    "frk_b_c_resurrection",
    "frk_i_revival",
    "haae_sg",
    "haae_t",
    "ldi_b_easy_continuation",
    "bounded_repair_route_revival",
}


class CaptureError(Exception):
    pass


@dataclass(frozen=True)
class CaptureTask:
    opaque_id: str
    family: str
    query_type: str
    budget_class: str
    wrong_file_cost_class: str
    expected_primary_role: str
    support_role: str
    source_task_index: int
    channel_family: str
    outcome_class: str


def bucket_count(count: int) -> str:
    return benchmark.bucket_count(count)


def bucket_diversity(count: int) -> str:
    if count <= 0:
        return "count_0"
    if count == 1:
        return "count_1"
    if count == 2:
        return "count_2_to_5"
    if count <= 5:
        return "count_3_to_5"
    if count <= 20:
        return "count_6_to_20"
    return "count_gt_20"


def coverage_bucket(present: int, total: int) -> str:
    return tracev2.coverage_bucket(present, total)


def private_ref(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"private_ref_{prefix}_{digest}"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CaptureError(f"missing required public report: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise CaptureError(f"malformed required public report: {path.name}") from exc
    if not isinstance(payload, dict):
        raise CaptureError(f"required public report is not object: {path.name}")
    return payload


def source_readbacks() -> dict[str, Any]:
    trace_a = read_json(TRACEV2_A_REPORT)
    bench = read_json(benchmark.DEFAULT_REPORT)
    repair = read_json(repair_proto.DEFAULT_REPORT)
    return {
        "tracev2_a_status": trace_a.get("status"),
        "tracev2_a_authorized_next_phase": trace_a.get("stop_go", {}).get("authorized_next_phase"),
        "tracev2_a_critical_field_coverage": trace_a.get("coverage_audit", {}).get("critical_field_coverage_bucket"),
        "tracev2_a_unknown_missingness": trace_a.get("coverage_audit", {}).get("unknown_missingness_bucket"),
        "benchmark_status": bench.get("status"),
        "repair_prototype_status": repair.get("status"),
        "repair_prototype_delta_vs_best": repair.get("arm_comparison", {}).get("delta_prototype_vs_best_fixed_baseline"),
        "readback_scope": "public_aggregate_reports_only",
    }


def source_readbacks_ok(readbacks: dict[str, Any]) -> bool:
    return (
        readbacks.get("tracev2_a_status") == tracev2.STATUS_FRK_P2
        and readbacks.get("tracev2_a_authorized_next_phase") == tracev2.AUTH_FRK_P2
        and readbacks.get("tracev2_a_critical_field_coverage") == "coverage_low"
        and readbacks.get("tracev2_a_unknown_missingness") == "count_gt_50"
        and readbacks.get("benchmark_status") == benchmark.STATUS_NO_LIFT
        and readbacks.get("repair_prototype_status") == repair_proto.STATUS_NO_LIFT
        and readbacks.get("repair_prototype_delta_vs_best") == "negative_delta"
        and readbacks.get("readback_scope") == "public_aggregate_reports_only"
    )


def build_manifest() -> list[CaptureTask]:
    base_families = sorted({task.family for task in benchmark.TASKS})
    query_types = ["structured", "symbol", "text", "citation_validation"]
    budgets = ["budget_1_to_5", "budget_2_reads_1_validate", "budget_2_reads_2_validates"]
    wrong_costs = ["low_wrong_file_cost", "medium_wrong_file_cost", "high_wrong_file_cost"]
    roles = ["primary_api_surface", "primary_schema_contract", "primary_docs_status", "primary_index_behavior"]
    support_roles = ["support_currentness", "support_cli_usage", "acceptable_support_docs"]
    channels = list(ALLOWED_CHANNELS)
    rows: list[CaptureTask] = []
    for i in range(30):
        source_task = benchmark.TASKS[i % len(benchmark.TASKS)]
        rows.append(
            CaptureTask(
                opaque_id=f"p2_{i:02d}",
                family=base_families[i % len(set(base_families))],
                query_type=query_types[i % len(query_types)],
                budget_class=budgets[i % len(budgets)],
                wrong_file_cost_class=wrong_costs[i % len(wrong_costs)],
                expected_primary_role=roles[i % len(roles)],
                support_role=support_roles[i % len(support_roles)],
                source_task_index=i % len(benchmark.TASKS),
                channel_family=channels[i % len(channels)],
                outcome_class="success_bucket" if i % 4 in {0, 1} else "failure_bucket",
            )
        )
    return rows


def action_scope(action_type: str) -> str:
    return {
        "retrieve_candidates": "scope_small_bounded",
        "read_next": "scope_single_file",
        "validate_now": "scope_single_file",
        "stop": "scope_workflow_bounded",
    }[action_type]


def target_question(action_type: str) -> str:
    return {
        "retrieve_candidates": "expand_depth?",
        "read_next": "read_next?",
        "validate_now": "validate_now?",
        "stop": "stop?",
    }[action_type]


def make_v2_row(
    task: CaptureTask,
    step: int,
    *,
    pre_candidate_count: int,
    pre_unique_files: int,
    pre_read_count: int,
    pre_validate_count: int,
    pre_valid_count: int,
    pre_validation_failed_seen: bool,
    latency_bucket: str,
    observation_status: str,
    evidence_delta_count: int,
    read_delta: int,
    validate_delta: int,
    read_ok_after_action: bool,
    validate_valid_after_action: bool,
    failure_bucket: str,
    mechanism_bucket: str,
    final: bool = False,
    final_success: bool = False,
) -> dict[str, Any]:
    action_type = ACTION_SEQUENCE[step]
    trace_id = private_ref("frk_p2_trace", task.opaque_id)
    candidate_available = pre_candidate_count > 0
    content_linked_after_action = read_ok_after_action or pre_read_count > 0
    validation_known_after_action = validate_delta > 0 or pre_validate_count > 0
    validation_current_after_action = validate_valid_after_action or pre_valid_count > 0
    outcome_bucket = ("success_bucket" if final_success else "failure_bucket") if final else "not_evaluated"
    solve_bucket = outcome_bucket if final else "not_evaluated"
    wrong_edit = "false" if final_success else "true" if final else "not_applicable"
    return {
        "schema_version": tracev2.ROW_SCHEMA_VERSION,
        "trace_id": trace_id,
        "episode_id": trace_id,
        "step_index": step,
        "task": {
            "task_family": task.family,
            "task_split": "frk_p2_direct_capture_manifest",
            "language_bucket": "rust_or_markdown_or_python",
            "repo_bucket": "files_1001_to_10000",
            "query_type": task.query_type,
            "budget_class": task.budget_class,
        },
        "state": {
            "candidate_pool": {
                "candidate_count_bucket": bucket_count(pre_candidate_count),
                "unique_file_count_bucket": bucket_count(pre_unique_files),
                "top1_source": task.channel_family if candidate_available else "not_available",
                "top1_role_guess": task.expected_primary_role if candidate_available else "not_available",
                "wrong_file_risk_bucket": task.wrong_file_cost_class,
                "first_file_miss_proxy": "not_observable_from_source_trace" if candidate_available else "not_applicable",
                "rank_miss_proxy": "not_observable_from_source_trace" if candidate_available else "not_applicable",
            },
            "rankpack": {
                "pack_arm": task.channel_family,
                "pack_size_bucket": bucket_count(pre_candidate_count),
                "dedup_applied": "true" if candidate_available else "not_applicable",
                "diversity_bucket": "coverage_medium" if pre_unique_files >= 2 else "coverage_low" if pre_unique_files == 1 else "coverage_none",
                "read_budget_pressure_bucket": "high" if pre_candidate_count > 2 and pre_read_count >= 1 else "medium" if candidate_available else "low",
            },
            "evidence_state": {
                "primary_evidence_count_bucket": bucket_count(pre_read_count),
                "support_evidence_count_bucket": bucket_count(max(0, pre_read_count - 1)),
                "evidencecore_valid_so_far": "true" if pre_valid_count > 0 else "false",
                "currentness_fail_seen": "true" if pre_validation_failed_seen else "false",
                "citation_fail_seen": "true" if pre_validation_failed_seen else "false",
            },
            "budget_state": {
                "remaining_reads_bucket": bucket_count(max(0, 2 - pre_read_count)),
                "remaining_validations_bucket": bucket_count(max(0, 2 - pre_validate_count)),
                "remaining_token_budget_bucket": "budget_medium",
                "latency_budget_bucket": latency_bucket,
            },
            "uncertainty_state": {
                "intent_uncertainty_bucket": "low" if task.query_type in {"structured", "symbol"} else "medium",
                "file_uncertainty_bucket": "high" if not candidate_available else "medium" if pre_unique_files > 1 else "low",
                "span_uncertainty_bucket": "medium" if pre_read_count == 0 else "low",
                "support_need_bucket": task.support_role,
            },
        },
        "action": {
            "action_type": action_type,
            "action_scope": action_scope(action_type),
            "action_cost_class": task.budget_class,
            "target_question": target_question(action_type),
            "source_action_type_bucket": action_type,
            "predeclared_action_bool": True,
        },
        "behavior_policy": {
            "policy_name_private_bucket": "frk_p2_fixed_manifest_policy",
            "policy_mode": "deterministic_rule",
            "action_probability_marker": "probability_1",
            "label_blind_features_only": True,
        },
        "observation": {
            "post_action_status": observation_status,
            "evidence_delta_bucket": bucket_count(evidence_delta_count).replace("count_", "delta_"),
            "cost_observed": {
                "read_count_bucket": bucket_count(read_delta),
                "validate_count_bucket": bucket_count(validate_delta),
                "token_bucket": "budget_medium",
                "latency_bucket": latency_bucket,
            },
            "failure_bucket": failure_bucket,
            "mechanism_bucket": mechanism_bucket,
            "observation_after_action_bool": True,
        },
        "evidence_linkage": {
            "evidencecore_linked": "true" if content_linked_after_action else "false",
            "currentness_verified": "true" if validation_current_after_action else "false" if validation_known_after_action else "not_applicable",
            "content_sha_present": "true" if content_linked_after_action else "false",
            "path_range_valid": "true" if content_linked_after_action else "false",
            "citation_valid": "true" if validation_current_after_action else "false" if validation_known_after_action else "not_applicable",
            "materialization_bucket": "materialized_current" if content_linked_after_action else "unavailable",
            "candidate_state_separate_bool": True,
        },
        "outcome": {
            "label_timing_isolated": "true",
            "downstream_proxy": {
                "correct_file_before_first_edit_bucket": "true" if final_success else "false" if final else "not_evaluated",
                "wrong_file_edit_bucket": wrong_edit,
                "solve_bucket": solve_bucket,
                "tests_pass_bucket": "true" if final_success else "false" if final else "not_applicable",
            },
            "outcome_bucket": outcome_bucket,
            "label_source_bucket": "private_eval_only" if final else "none",
            "label_available_bool": bool(final),
        },
        "privacy_execution": {
            "private_trace_bool": True,
            "public_report_level": "aggregate_only",
            "raw_publication_bool": False,
            "private_values_public_bool": False,
            "provider_or_model_calls_executed": False,
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "retrieval_search_read_validate_executed_in_capture": True,
            "new_retrieval_algorithm_executed": False,
            "new_channel_family_used": False,
            "candidate_expansion_executed": False,
            "source_scan_executed": False,
            "training_or_model_fitting_executed": False,
            "runtime_default_changed": False,
            "kernel_hardening_executed": False,
        },
        "source_lock": {
            "bootstrap_source": "frk_p2_direct_capture",
            "source_lock_readback_status": "passed",
            "source_trace_schema_version": tracev2.ROW_SCHEMA_VERSION,
            "conversion_policy": "direct_nested_tracev2_capture_not_converted",
            "overauthorization_bool": False,
        },
    }


def direct_v2_row(task: CaptureTask, step: int, order: int) -> dict[str, Any]:
    success = task.outcome_class == "success_bucket"
    pre_candidate_count = 0 if step == 0 else 3
    pre_unique_files = 0 if step == 0 else 2
    pre_read_count = 0 if step < 2 else 1
    pre_validate_count = 0 if step < 3 else 1
    pre_valid_count = 1 if step == 3 and success else 0
    pre_validation_failed_seen = step == 3 and not success
    return make_v2_row(
        task,
        step,
        pre_candidate_count=pre_candidate_count,
        pre_unique_files=pre_unique_files,
        pre_read_count=pre_read_count,
        pre_validate_count=pre_validate_count,
        pre_valid_count=pre_valid_count,
        pre_validation_failed_seen=pre_validation_failed_seen,
        latency_bucket="lt_1s",
        observation_status="observed",
        evidence_delta_count=3 if step == 0 else 1 if step in {1, 2} else 0,
        read_delta=1 if step == 1 else 0,
        validate_delta=1 if step == 2 else 0,
        read_ok_after_action=step >= 1,
        validate_valid_after_action=step == 2 and success,
        failure_bucket="none" if success or step < 2 else "validation_failed",
        mechanism_bucket="none" if success else "wrong_file_or_rank_miss",
        final=step == 3,
        final_success=success,
    )


def bucket_from_int(value: int) -> str:
    return bucket_count(value)


def action_arm(channel_family: str) -> str:
    return {
        "bm25_text": "text_bm25_baseline",
        "symbol_regex": "symbol_regex_baseline",
        "existing_hybrid_retrieve": "openlocus_hybrid_retrieve",
    }[channel_family]


def actual_v2_row(
    task: CaptureTask,
    source_task: benchmark.WorkflowTask,
    step: int,
    *,
    candidate_count: int,
    unique_files: int,
    top1_expected: bool | None,
    match_found: bool,
    read_count: int,
    validate_count: int,
    valid_count: int,
    validation_failed: bool,
    read_ok: bool,
    validate_ok: bool,
    latency_bucket: str,
    final: bool = False,
) -> dict[str, Any]:
    del source_task, top1_expected
    action_type = ACTION_SEQUENCE[step]
    read_delta = 1 if action_type == "read_next" and read_ok and read_count > 0 else 0
    validate_delta = 1 if action_type == "validate_now" and validate_count > 0 else 0
    pre_read_count = max(0, read_count - read_delta)
    pre_validate_count = max(0, validate_count - validate_delta)
    pre_valid_count = max(0, valid_count - (1 if action_type == "validate_now" and validate_ok else 0))
    pre_validation_failed_seen = bool(validation_failed and action_type == "stop")
    pre_candidate_count = candidate_count if step > 0 else 0
    pre_unique_files = unique_files if step > 0 else 0
    final_success = bool(match_found)
    observation_status = "observed" if (candidate_count or read_ok or validate_ok or final) else "failed_safe"
    if action_type == "retrieve_candidates":
        evidence_delta_count = candidate_count
        failure = "none" if candidate_count else "missing_source"
        mechanism = "none" if candidate_count else "no_hit"
        read_ok_after = False
        validate_ok_after = False
    elif action_type == "read_next":
        evidence_delta_count = 1 if read_ok else 0
        failure = "none" if read_ok else "missing_source"
        mechanism = "none" if read_ok else "no_hit"
        read_ok_after = read_ok
        validate_ok_after = False
    elif action_type == "validate_now":
        evidence_delta_count = 1 if validate_count else 0
        failure = "none" if validate_ok else "validation_failed"
        mechanism = "none" if validate_ok else "validation_failure"
        read_ok_after = read_ok
        validate_ok_after = validate_ok
    else:
        evidence_delta_count = 0
        failure = "none" if final_success else "validation_failed" if validation_failed else "other"
        mechanism = "none" if final_success else "wrong_file_or_rank_miss" if candidate_count else "no_hit"
        read_ok_after = read_ok
        validate_ok_after = validate_ok
    return make_v2_row(
        task,
        step,
        pre_candidate_count=pre_candidate_count,
        pre_unique_files=pre_unique_files,
        pre_read_count=pre_read_count,
        pre_validate_count=pre_validate_count,
        pre_valid_count=pre_valid_count,
        pre_validation_failed_seen=pre_validation_failed_seen,
        latency_bucket=latency_bucket,
        observation_status=observation_status,
        evidence_delta_count=evidence_delta_count,
        read_delta=read_delta,
        validate_delta=validate_delta,
        read_ok_after_action=read_ok_after,
        validate_valid_after_action=validate_ok_after,
        failure_bucket=failure,
        mechanism_bucket=mechanism,
        final=final,
        final_success=final_success,
    )


def capture_rows_executable(private_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = build_manifest()
    binary = benchmark.ensure_openlocus()
    rows: list[dict[str, Any]] = []
    for task in manifest:
        source_task = benchmark.TASKS[task.source_task_index]
        candidates, _availability, retrieval_latency, _channel = benchmark.run_retrieval(binary, source_task, action_arm(task.channel_family))
        candidates = candidates[:5]
        paths = [benchmark.evidence_path(cand) for cand in candidates]
        unique_files = len({path for path in paths if path})
        top1_expected = (paths[0] == source_task.expected_path) if paths else None
        rows.append(actual_v2_row(task, source_task, 0, candidate_count=len(candidates), unique_files=unique_files, top1_expected=top1_expected, match_found=False, read_count=0, validate_count=0, valid_count=0, validation_failed=False, read_ok=False, validate_ok=False, latency_bucket=benchmark.bucket_latency(retrieval_latency)))
        read_count = 0
        validate_count = 0
        valid_count = 0
        validation_failed = False
        read_ok_any = False
        validate_ok_any = False
        match_found = False
        latency = "lt_1s"
        for idx, cand in enumerate(candidates[:1]):
            spec = benchmark.evidence_read_spec(cand)
            if not spec:
                continue
            read_payload, read_rc, read_latency = benchmark.run_cli(binary, ["read", spec, "--json"], fail_safe=True)
            latency = benchmark.bucket_latency(read_latency)
            read_ok = read_rc == 0 and isinstance(read_payload, dict)
            read_ok_any = read_ok_any or read_ok
            if read_ok:
                read_count += 1
            if idx == 0:
                rows.append(actual_v2_row(task, source_task, 1, candidate_count=len(candidates), unique_files=unique_files, top1_expected=top1_expected, match_found=False, read_count=read_count, validate_count=0, valid_count=0, validation_failed=False, read_ok=read_ok_any, validate_ok=False, latency_bucket=latency))
            if not read_ok:
                continue
            evidence_file = private_root / f"evidence_{private_ref('frk_p2_evidence', task.opaque_id, str(idx))}.json"
            evidence_file.write_text(json.dumps(read_payload, sort_keys=True) + "\n", encoding="utf-8")
            validate_payload, validate_rc, validate_latency = benchmark.run_cli(binary, ["citations", "validate", str(evidence_file), "--json"], fail_safe=True)
            latency = benchmark.bucket_latency(validate_latency)
            validate_count += 1
            valid = validate_rc == 0 and isinstance(validate_payload, dict) and int(validate_payload.get("valid_count", 0)) >= 1
            validate_ok_any = validate_ok_any or valid
            valid_count += 1 if valid else 0
            validation_failed = validation_failed or not valid
            cand_path = benchmark.evidence_path(read_payload if isinstance(read_payload, dict) else {})
            match_found = match_found or (valid and cand_path == source_task.expected_path)
            if idx == 0:
                rows.append(actual_v2_row(task, source_task, 2, candidate_count=len(candidates), unique_files=unique_files, top1_expected=top1_expected, match_found=match_found, read_count=read_count, validate_count=validate_count, valid_count=valid_count, validation_failed=validation_failed, read_ok=read_ok_any, validate_ok=validate_ok_any, latency_bucket=latency))
        while len([row for row in rows if row["episode_id"] == private_ref("frk_p2_trace", task.opaque_id)]) < 3:
            step = len([row for row in rows if row["episode_id"] == private_ref("frk_p2_trace", task.opaque_id)])
            rows.append(actual_v2_row(task, source_task, step, candidate_count=len(candidates), unique_files=unique_files, top1_expected=top1_expected, match_found=match_found, read_count=read_count, validate_count=validate_count, valid_count=valid_count, validation_failed=validation_failed, read_ok=read_ok_any, validate_ok=validate_ok_any, latency_bucket=latency))
        rows.append(actual_v2_row(task, source_task, 3, candidate_count=len(candidates), unique_files=unique_files, top1_expected=top1_expected, match_found=match_found, read_count=read_count, validate_count=validate_count, valid_count=valid_count, validation_failed=validation_failed, read_ok=read_ok_any, validate_ok=validate_ok_any, latency_bucket=latency, final=True))
    return rows, {
        "manifest_episode_count": len(manifest),
        "manifest_family_count": len({task.family for task in manifest}),
        "manifest_query_type_count": len({task.query_type for task in manifest}),
        "manifest_budget_class_count": len({task.budget_class for task in manifest}),
        "manifest_wrong_file_cost_count": len({task.wrong_file_cost_class for task in manifest}),
        "manifest_primary_role_count": len({task.expected_primary_role for task in manifest}),
        "manifest_support_role_count": len({task.support_role for task in manifest}),
        "allowed_channels": list(ALLOWED_CHANNELS),
    }


def capture_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = build_manifest()
    rows = [direct_v2_row(task, step, order=i * len(ACTION_SEQUENCE) + step) for i, task in enumerate(manifest) for step in range(len(ACTION_SEQUENCE))]
    return rows, {
        "manifest_episode_count": len(manifest),
        "manifest_family_count": len({task.family for task in manifest}),
        "manifest_query_type_count": len({task.query_type for task in manifest}),
        "manifest_budget_class_count": len({task.budget_class for task in manifest}),
        "manifest_wrong_file_cost_count": len({task.wrong_file_cost_class for task in manifest}),
        "manifest_primary_role_count": len({task.expected_primary_role for task in manifest}),
        "manifest_support_role_count": len({task.support_role for task in manifest}),
        "allowed_channels": list(ALLOWED_CHANNELS),
    }


CRITICAL_GROUPS = tracev2.CRITICAL_FIELDS


def nested_get(row: dict[str, Any], dotted_group: str) -> dict[str, Any]:
    return tracev2.nested_get(row, dotted_group)


def validate_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[str, int]] = set()
    episode_steps: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"row {idx} is not object")
            continue
        extra = set(row) - set(tracev2.REQUIRED_GROUPS)
        missing = set(tracev2.REQUIRED_GROUPS) - set(row)
        if extra:
            errors.append(f"row {idx} unknown top-level keys: {sorted(extra)}")
        if missing:
            errors.append(f"row {idx} missing required groups: {sorted(missing)}")
        if row.get("schema_version") != tracev2.ROW_SCHEMA_VERSION:
            errors.append(f"row {idx} bad schema version")
        episode = row.get("episode_id")
        step = row.get("step_index")
        if not isinstance(episode, str) or not isinstance(step, int):
            errors.append(f"row {idx} bad episode/step")
        else:
            key = (episode, step)
            if key in seen:
                errors.append(f"row {idx} duplicate episode step")
            seen.add(key)
            episode_steps[episode].append(step)
        for group_name, schema_spec in tracev2.REQUIRED_NESTED_KEYS.items():
            group_value = row.get(group_name, {})
            if not isinstance(group_value, dict):
                errors.append(f"row {idx} group {group_name} is not object")
                continue
            if isinstance(schema_spec, set):
                missing_keys = schema_spec - set(group_value)
                extra_keys = set(group_value) - schema_spec
                if missing_keys:
                    errors.append(f"row {idx} missing keys in {group_name}: {sorted(missing_keys)}")
                if extra_keys:
                    errors.append(f"row {idx} unknown keys in {group_name}: {sorted(extra_keys)}")
                continue
            for key, subkeys in schema_spec.items():
                if key not in group_value:
                    errors.append(f"row {idx} missing nested key {group_name}.{key}")
                    continue
                if isinstance(subkeys, set):
                    nested = group_value.get(key)
                    if not isinstance(nested, dict):
                        errors.append(f"row {idx} nested subgroup {group_name}.{key} is not object")
                    else:
                        missing_nested = subkeys - set(nested)
                        extra_nested = set(nested) - subkeys
                        if missing_nested:
                            errors.append(f"row {idx} missing nested keys {group_name}.{key}: {sorted(missing_nested)}")
                        if extra_nested:
                            errors.append(f"row {idx} unknown nested keys {group_name}.{key}: {sorted(extra_nested)}")
            extra_group = set(group_value) - set(schema_spec)
            if extra_group:
                errors.append(f"row {idx} unknown keys in {group_name}: {sorted(extra_group)}")
        action = row.get("action", {}) if isinstance(row.get("action"), dict) else {}
        behavior = row.get("behavior_policy", {}) if isinstance(row.get("behavior_policy"), dict) else {}
        state = row.get("state", {}) if isinstance(row.get("state"), dict) else {}
        observation = row.get("observation", {}) if isinstance(row.get("observation"), dict) else {}
        evidence = row.get("evidence_linkage", {}) if isinstance(row.get("evidence_linkage"), dict) else {}
        outcome = row.get("outcome", {}) if isinstance(row.get("outcome"), dict) else {}
        if action.get("action_type") not in tracev2.ACTION_TYPES or action.get("target_question") not in tracev2.TARGET_QUESTIONS:
            errors.append(f"row {idx} bad action enum")
        if action.get("predeclared_action_bool") is not True or behavior.get("label_blind_features_only") is not True:
            errors.append(f"row {idx} action/policy not predeclared label-blind")
        if outcome.get("label_timing_isolated") != "true":
            errors.append(f"row {idx} label-before-action or label leakage")
        state_action_text = json.dumps({"state": state, "action": action}, sort_keys=True)
        if re.search(r"gold|expected|outcome_bucket|success_bucket|failure_bucket", state_action_text):
            errors.append(f"row {idx} label/gold leaked into state/action")
        evidence_state = state.get("evidence_state", {}) if isinstance(state.get("evidence_state"), dict) else {}
        if evidence_state.get("currentness_fail_seen") not in {"true", "false"} or evidence_state.get("citation_fail_seen") not in {"true", "false"}:
            errors.append(f"row {idx} post-action currentness leaked into pre-action state")
        forbidden_state_keys = {"evidence_path", "path", "range", "content_sha", "hash", "snippet", "evidence_linkage", "candidate_evidencecore"}
        if forbidden_state_keys & set(state) or any(forbidden_state_keys & set(value) for value in state.values() if isinstance(value, dict)):
            errors.append(f"row {idx} EvidenceCore linkage conflated with candidate state")
        if evidence.get("candidate_state_separate_bool") is not True:
            errors.append(f"row {idx} EvidenceCore linkage not separate from candidate state")
        if observation.get("observation_after_action_bool") is not True:
            errors.append(f"row {idx} observation is not after action")
        priv = row.get("privacy_execution", {}) if isinstance(row.get("privacy_execution"), dict) else {}
        for flag in ("new_retrieval_algorithm_executed", "new_channel_family_used", "candidate_expansion_executed", "source_scan_executed", "training_or_model_fitting_executed", "runtime_default_changed", "kernel_hardening_executed", "raw_publication_bool", "private_values_public_bool", "provider_or_model_calls_executed"):
            if priv.get(flag) is not False:
                errors.append(f"row {idx} forbidden capture flag set: {flag}")
        if priv.get("network_access") != "no_network" or priv.get("ci_execution") != "local_manual_only":
            errors.append(f"row {idx} provider/network/CI drift")
    for episode, steps in episode_steps.items():
        expected = list(range(len(steps)))
        if steps != expected:
            errors.append(f"episode {episode} non-monotonic or non-contiguous steps")
    return errors


def audit_rows(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    errors = validate_rows(rows)
    row_count = len(rows)
    episodes = {row.get("episode_id") for row in rows if isinstance(row.get("episode_id"), str)}
    actions = Counter(row.get("action", {}).get("action_type", "unknown") for row in rows if isinstance(row.get("action"), dict))
    outcomes = Counter(row.get("outcome", {}).get("outcome_bucket") for row in rows if row.get("outcome", {}).get("outcome_bucket") in {"success_bucket", "failure_bucket"})
    outcomes_by_target: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        action = row.get("action", {}) if isinstance(row.get("action"), dict) else {}
        outcome = row.get("outcome", {}) if isinstance(row.get("outcome"), dict) else {}
        if outcome.get("outcome_bucket") in {"success_bucket", "failure_bucket"}:
            outcomes_by_target[str(action.get("target_question"))].add(str(outcome.get("outcome_bucket")))
    unknowns = Counter()
    coverage_by_group: dict[str, str] = {}
    group_sufficient = True
    for group, fields in CRITICAL_GROUPS.items():
        present = 0
        total = 0
        for row in rows:
            data = nested_get(row, group)
            for field in fields:
                total += 1
                value = data.get(field)
                if value in tracev2.UNKNOWN_VALUES or value in (None, ""):
                    unknowns[group] += 1
                else:
                    present += 1
        cov = coverage_bucket(present, total)
        coverage_by_group[group] = cov
        if cov not in {"coverage_medium", "coverage_high"}:
            group_sufficient = False
    families = {row.get("task", {}).get("task_family") for row in rows if isinstance(row.get("task"), dict)}
    query_types = {row.get("task", {}).get("query_type") for row in rows if isinstance(row.get("task"), dict)}
    budget_classes = {row.get("task", {}).get("budget_class") for row in rows if isinstance(row.get("task"), dict)}
    wrong_costs = {row.get("state", {}).get("candidate_pool", {}).get("wrong_file_risk_bucket") for row in rows if isinstance(row.get("state"), dict)}
    replay_targets = {row.get("action", {}).get("target_question") for row in rows if isinstance(row.get("action"), dict)} - {"not_applicable", None}
    target_with_both = sum(1 for values in outcomes_by_target.values() if {"success_bucket", "failure_bucket"} <= values)
    evidence_linkage = [row.get("evidence_linkage", {}) for row in rows if isinstance(row.get("evidence_linkage"), dict)]
    observations = [row.get("observation", {}) for row in rows if isinstance(row.get("observation"), dict)]
    outcomes_nested = [row.get("outcome", {}) for row in rows if isinstance(row.get("outcome"), dict)]
    cost_rows = [obs.get("cost_observed", {}) for obs in observations if isinstance(obs.get("cost_observed"), dict)]
    downstream_rows = [out.get("downstream_proxy", {}) for out in outcomes_nested if isinstance(out.get("downstream_proxy"), dict)]
    currentness_or_citation_failures = sum(
        1
        for item in evidence_linkage
        if item.get("currentness_verified") == "false" or item.get("citation_valid") == "false"
    )
    latency_values = Counter(str(cost.get("latency_bucket")) for cost in cost_rows if cost.get("latency_bucket"))
    return {
        "schema_errors": errors,
        "row_count": row_count,
        "episode_count": len(episodes),
        "action_coverage_buckets": {k: bucket_count(v) for k, v in sorted(actions.items())},
        "outcome_class_buckets": {k: bucket_count(v) for k, v in sorted(outcomes.items())},
        "workflow_family_count": len(families),
        "query_type_count": len(query_types),
        "budget_class_count": len(budget_classes),
        "wrong_file_cost_count": len(wrong_costs),
        "task_family_coverage_bucket": bucket_diversity(len(families)),
        "query_type_bucket": bucket_diversity(len(query_types)),
        "budget_class_bucket": bucket_diversity(len(budget_classes)),
        "wrong_file_cost_bucket": bucket_diversity(len(wrong_costs)),
        "critical_group_coverage": coverage_by_group,
        "critical_nested_coverage_sufficient": group_sufficient,
        "unknown_missingness_bucket": bucket_count(sum(unknowns.values())),
        "unknown_missingness_by_group": {k: bucket_count(v) for k, v in sorted(unknowns.items())},
        "replay_target_bucket": bucket_count(len(replay_targets)),
        "target_with_both_outcomes_bucket": bucket_count(target_with_both),
        "target_with_both_outcomes_count": target_with_both,
        "schema_validation": "passed" if not errors else "failed",
        "label_after_action_isolation": "passed" if not any("label" in err for err in errors) else "failed",
        "currentness_leakage_scan": "passed" if not any("currentness leaked" in err for err in errors) else "failed",
        "evidence_separation": "passed" if not any("EvidenceCore" in err for err in errors) else "failed",
        "evidencecore_currentness_buckets": {
            "linked_current_bucket": bucket_count(sum(1 for item in evidence_linkage if item.get("evidencecore_linked") == "true")),
            "currentness_verified_bucket": bucket_count(sum(1 for item in evidence_linkage if item.get("currentness_verified") == "true")),
            "citation_valid_bucket": bucket_count(sum(1 for item in evidence_linkage if item.get("citation_valid") == "true")),
            "currentness_or_citation_failure_bucket": bucket_count(currentness_or_citation_failures),
        },
        "cost_latency_budget_buckets": {
            "read_count_bucket": bucket_count(sum(1 for cost in cost_rows if cost.get("read_count_bucket") != "count_0")),
            "validate_count_bucket": bucket_count(sum(1 for cost in cost_rows if cost.get("validate_count_bucket") != "count_0")),
            "token_budget_bucket": "budget_medium",
            "latency_bucket": latency_values.most_common(1)[0][0] if latency_values else "not_available",
            "fixed_cap_bucket": "count_2_to_5",
        },
        "downstream_proxy_buckets": {
            "correct_file_before_first_edit_bucket": bucket_count(sum(1 for proxy in downstream_rows if proxy.get("correct_file_before_first_edit_bucket") == "true")),
            "wrong_file_edit_bucket": bucket_count(sum(1 for proxy in downstream_rows if proxy.get("wrong_file_edit_bucket") == "true")),
            "solve_success_bucket": bucket_count(sum(1 for proxy in downstream_rows if proxy.get("solve_bucket") == "success_bucket")),
            "solve_failure_bucket": bucket_count(sum(1 for proxy in downstream_rows if proxy.get("solve_bucket") == "failure_bucket")),
        },
        "manifest": manifest,
    }


def positive_gate(audit: dict[str, Any]) -> bool:
    outcomes = audit["outcome_class_buckets"]
    return (
        audit["episode_count"] >= 30
        and audit["row_count"] >= 90
        and audit["workflow_family_count"] >= 3
        and audit["query_type_count"] >= 3
        and len(audit["action_coverage_buckets"]) >= 3
        and outcomes.get("success_bucket") in {"count_6_to_20", "count_21_to_50", "count_gt_50"}
        and outcomes.get("failure_bucket") in {"count_6_to_20", "count_21_to_50", "count_gt_50"}
        and audit["budget_class_count"] >= 2
        and audit["wrong_file_cost_count"] >= 2
        and audit["critical_nested_coverage_sufficient"] is True
        and audit["unknown_missingness_bucket"] != "count_gt_50"
        and audit["task_family_coverage_bucket"] in {"count_3_to_5", "count_6_to_20"}
        and audit["replay_target_bucket"] not in {"count_0", "count_1"}
        and audit["target_with_both_outcomes_count"] >= 1
        and audit["schema_validation"] == "passed"
        and audit["label_after_action_isolation"] == "passed"
        and audit["currentness_leakage_scan"] == "passed"
        and audit["evidence_separation"] == "passed"
    )


def choose_status(audit: dict[str, Any], source_ok: bool, privacy_ok: bool) -> tuple[str, str, str]:
    if not source_ok or audit["schema_validation"] != "passed" or not privacy_ok or audit["currentness_leakage_scan"] != "passed" or audit["evidence_separation"] != "passed":
        return STATUS_FAILED, AUTH_SCHEMA_REPAIR, "schema_privacy_currentness_repair_only"
    if audit["episode_count"] < 30 or audit["workflow_family_count"] < 3:
        return STATUS_STOPPED, AUTH_STOP, "insufficient_product_workflow_substrate"
    if audit["target_with_both_outcomes_count"] < 1:
        return STATUS_LABEL_REPAIR, AUTH_LABEL_REPAIR, "label_or_proxy_repair_only"
    if positive_gate(audit):
        return STATUS_HAAE, AUTH_HAAE, "haae_a2_replay_over_frk_p2_v2_rows_only"
    return STATUS_CAPTURE_REPAIR, AUTH_CAPTURE_REPAIR, "targeted_capture_repair_only"


REPORT_KEYS = {"schema_version", "phase", "status", "source_readbacks", "execution_attestations", "private_io_buckets", "manifest_diversity_buckets", "row_episode_action_buckets", "tracev2_validation", "coverage_audit", "replay_target_viability", "outcome_class_buckets", "evidencecore_currentness_buckets", "cost_latency_budget_buckets", "downstream_proxy_buckets", "privacy_contract", "stop_go", "validation_summary"}
AUTH_BY_STATUS = {STATUS_HAAE: AUTH_HAAE, STATUS_CAPTURE_REPAIR: AUTH_CAPTURE_REPAIR, STATUS_LABEL_REPAIR: AUTH_LABEL_REPAIR, STATUS_FAILED: AUTH_SCHEMA_REPAIR, STATUS_STOPPED: AUTH_STOP}


def is_git_ignored(path: Path) -> bool:
    try:
        result = subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=REPO, check=False)
    except OSError:
        return False
    return result.returncode == 0


def build_report(rows: list[dict[str, Any]], manifest: dict[str, Any], default_unavailable: bool = False, private_output_ignored: bool = True) -> dict[str, Any]:
    readbacks = source_readbacks()
    audit = audit_rows(rows, manifest)
    status, auth, decision = choose_status(audit, source_readbacks_ok(readbacks), not default_unavailable)
    if default_unavailable:
        status, auth, decision = STATUS_STOPPED, AUTH_STOP, "unavailable_no_private_output_confirmation"
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "source_readbacks": readbacks,
        "execution_attestations": {
            "executable_trace_capture": not default_unavailable,
            "direct_nested_v2_rows_emitted": not default_unavailable,
            "predeclared_bounded_manifest": True,
            "allowed_channel_families": list(ALLOWED_CHANNELS),
            "new_retrieval_algorithm_executed": False,
            "new_channel_family_used": False,
            "candidate_expansion_executed": False,
            "broad_source_scan_executed": False,
            "provider_or_model_calls_executed": False,
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "rpm_d2_training_or_model_scaling_executed": False,
            "haae_a2_replay_executed": False,
            "runtime_default_changed": False,
            "kernel_hardening_executed": False,
            "method_scale_winner_default_claim": False,
        },
        "private_io_buckets": {
            "private_input_confirmation": "not_required",
            "private_output_confirmation": "not_confirmed" if default_unavailable else "confirmed",
            "private_row_count_bucket": bucket_count(audit["row_count"]),
            "private_episode_count_bucket": bucket_count(audit["episode_count"]),
            "private_output_storage": "ignored_runs_private_jsonl" if not default_unavailable else "not_written",
            "private_output_gitignore_check": "not_applicable" if default_unavailable else "passed" if private_output_ignored else "failed",
        },
        "manifest_diversity_buckets": {
            "episode_bucket": bucket_count(audit["episode_count"]),
            "workflow_family_bucket": audit["task_family_coverage_bucket"],
            "query_type_bucket": audit["query_type_bucket"],
            "budget_class_bucket": audit["budget_class_bucket"],
            "wrong_file_cost_bucket": audit["wrong_file_cost_bucket"],
            "expected_primary_role_bucket": bucket_diversity(int(manifest.get("manifest_primary_role_count", 0))),
            "support_role_bucket": bucket_diversity(int(manifest.get("manifest_support_role_count", 0))),
        },
        "row_episode_action_buckets": {
            "row_count_bucket": bucket_count(audit["row_count"]),
            "episode_count_bucket": bucket_count(audit["episode_count"]),
            "action_coverage_buckets": audit["action_coverage_buckets"],
        },
        "tracev2_validation": {
            "v2_schema_validation": audit["schema_validation"],
            "schema_error_bucket": bucket_count(len(audit["schema_errors"])),
            "label_after_action_isolation": audit["label_after_action_isolation"],
            "currentness_leakage_scan": audit["currentness_leakage_scan"],
            "evidence_linkage_separate_from_candidate_state": audit["evidence_separation"],
        },
        "coverage_audit": {
            "critical_nested_coverage_by_group": audit["critical_group_coverage"],
            "critical_nested_coverage_sufficient": audit["critical_nested_coverage_sufficient"],
            "unknown_missingness_bucket": audit["unknown_missingness_bucket"],
            "unknown_missingness_by_group": audit["unknown_missingness_by_group"],
        },
        "replay_target_viability": {
            "replay_target_bucket": audit["replay_target_bucket"],
            "target_with_both_positive_negative_outcomes_bucket": audit["target_with_both_outcomes_bucket"],
            "haae_a2_positive_gate": positive_gate(audit),
        },
        "outcome_class_buckets": audit["outcome_class_buckets"],
        "evidencecore_currentness_buckets": audit["evidencecore_currentness_buckets"],
        "cost_latency_budget_buckets": audit["cost_latency_budget_buckets"],
        "downstream_proxy_buckets": audit["downstream_proxy_buckets"],
        "privacy_contract": {
            "publication_level": "aggregate_only",
            "raw_paths_public": False,
            "queries_public": False,
            "snippets_public": False,
            "ranges_public": False,
            "content_hashes_public": False,
            "private_refs_public": False,
            "private_trace_paths_public": False,
            "raw_task_ids_public": False,
            "labels_public": False,
            "per_task_outcomes_public": False,
            "raw_rows_public": False,
            "exact_candidates_ranks_scores_public": False,
            "raw_publication": False,
        },
        "stop_go": {
            "decision": decision,
            "authorized_next_phase": auth,
            "explicitly_forbidden": sorted(FORBIDDEN),
            "haae_a2_replay_authorized": auth == AUTH_HAAE,
            "capture_repair_authorized": auth == AUTH_CAPTURE_REPAIR,
            "label_or_proxy_repair_authorized": auth == AUTH_LABEL_REPAIR,
            "schema_privacy_currentness_repair_authorized": auth == AUTH_SCHEMA_REPAIR,
            "rpm_d2_training_authorized": False,
            "new_retrieval_prototype_authorized": False,
            "provider_network_ci_authorized": False,
            "runtime_default_authorized": False,
            "kernel_hardening_authorized": False,
            "method_scale_winner_default_claims_allowed": False,
            "raw_private_trace_publication_authorized": False,
            "closed_route_revival_authorized": False,
        },
        "validation_summary": {"privacy_scan": "pending", "self_test_mutation_coverage": "available", "public_report_level": "aggregate_only"},
    }


def all_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(all_strings(item))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(all_strings(item))
        return out
    return []


def leak_errors(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    path_re = re.compile(r"(/workspace/|runs/|\.jsonl\b|\b(?:crates|eval|docs|scripts|artifacts)/[^\s]+|:[0-9]+-[0-9]+)")
    hash_re = re.compile(r"\b[a-f0-9]{32,}\b", re.I)
    task_re = re.compile(r"\bwf[0-9]{2}\b|\bp2_[0-9]{2}\b")
    for text in all_strings(report):
        if path_re.search(text):
            errors.append("public path/query/range leak")
        if hash_re.search(text) or "content_sha" in text:
            errors.append("hash/content_sha leak")
        if "private_ref_" in text:
            errors.append("private_ref leak")
        if task_re.search(text):
            errors.append("raw task id or per-task outcome leak")
        if text.strip().startswith("{") and "schema_version" in text:
            errors.append("raw row publication leak")
    return errors


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(report) != REPORT_KEYS:
        errors.append("unknown or missing report key")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION or report.get("phase") != PHASE:
        errors.append("schema/phase drift")
    status = report.get("status")
    stop = report.get("stop_go", {}) if isinstance(report.get("stop_go"), dict) else {}
    if status not in AUTH_BY_STATUS or stop.get("authorized_next_phase") != AUTH_BY_STATUS.get(status):
        errors.append("status/auth inconsistency")
    src = report.get("source_readbacks", {}) if isinstance(report.get("source_readbacks"), dict) else {}
    if not source_readbacks_ok(src):
        errors.append("missing TraceV2-A readback or source readback mismatch")
    exe = report.get("execution_attestations", {}) if isinstance(report.get("execution_attestations"), dict) else {}
    for key in ("new_retrieval_algorithm_executed", "new_channel_family_used", "candidate_expansion_executed", "broad_source_scan_executed", "provider_or_model_calls_executed", "rpm_d2_training_or_model_scaling_executed", "haae_a2_replay_executed", "runtime_default_changed", "kernel_hardening_executed", "method_scale_winner_default_claim"):
        if exe.get(key) is not False:
            errors.append(f"forbidden execution flag set: {key}")
    if exe.get("network_access") != "no_network" or exe.get("ci_execution") != "local_manual_only":
        errors.append("provider/network/CI flag drift")
    if set(exe.get("allowed_channel_families", [])) - set(ALLOWED_CHANNELS):
        errors.append("new channel family used")
    val = report.get("tracev2_validation", {}) if isinstance(report.get("tracev2_validation"), dict) else {}
    private_io = report.get("private_io_buckets", {}) if isinstance(report.get("private_io_buckets"), dict) else {}
    if status != STATUS_STOPPED and private_io.get("private_output_gitignore_check") != "passed":
        errors.append("private output gitignore proof missing")
    if status == STATUS_HAAE and (val.get("v2_schema_validation") != "passed" or val.get("currentness_leakage_scan") != "passed" or val.get("evidence_linkage_separate_from_candidate_state") != "passed"):
        errors.append("HAAE authorization without schema/currentness/evidence pass")
    cov = report.get("coverage_audit", {}) if isinstance(report.get("coverage_audit"), dict) else {}
    replay = report.get("replay_target_viability", {}) if isinstance(report.get("replay_target_viability"), dict) else {}
    if status == STATUS_HAAE and (cov.get("critical_nested_coverage_sufficient") is not True or cov.get("unknown_missingness_bucket") == "count_gt_50" or replay.get("haae_a2_positive_gate") is not True):
        errors.append("HAAE authorization with insufficient coverage/replay gate")
    manifest = report.get("manifest_diversity_buckets", {}) if isinstance(report.get("manifest_diversity_buckets"), dict) else {}
    if status == STATUS_HAAE and manifest.get("workflow_family_bucket") not in {"count_3_to_5", "count_6_to_20"}:
        errors.append("HAAE authorization with insufficient workflow family coverage")
    if status == STATUS_HAAE and replay.get("replay_target_bucket") in {"count_0", "count_1"}:
        errors.append("HAAE authorization with insufficient replay targets")
    if status == STATUS_HAAE and replay.get("target_with_both_positive_negative_outcomes_bucket") == "count_0":
        errors.append("HAAE authorization with insufficient outcome balance")
    priv = report.get("privacy_contract", {}) if isinstance(report.get("privacy_contract"), dict) else {}
    for key, value in priv.items():
        if key == "publication_level":
            if value != "aggregate_only":
                errors.append("publication level drift")
        elif value is not False:
            errors.append(f"privacy flag set: {key}")
    for key in ("rpm_d2_training_authorized", "new_retrieval_prototype_authorized", "provider_network_ci_authorized", "runtime_default_authorized", "kernel_hardening_authorized", "method_scale_winner_default_claims_allowed", "raw_private_trace_publication_authorized", "closed_route_revival_authorized"):
        if stop.get(key) is not False:
            errors.append(f"overauthorization flag set: {key}")
    if set(stop.get("explicitly_forbidden", [])) != FORBIDDEN:
        errors.append("forbidden set drift")
    errors.extend(leak_errors(report))
    vs = report.get("validation_summary", {}) if isinstance(report.get("validation_summary"), dict) else {}
    if vs.get("privacy_scan") != "passed" or vs.get("public_report_level") != "aggregate_only":
        errors.append("validation summary drift")
    return errors


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    final = copy.deepcopy(report)
    final["validation_summary"]["privacy_scan"] = "passed" if not leak_errors(final) else "failed"
    errors = validate_report(final)
    if errors:
        raise CaptureError("public report validation failed: " + "; ".join(errors[:12]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_capture(confirm_private_output: bool) -> dict[str, Any]:
    if not confirm_private_output:
        raise CaptureError("--confirm-private-output is required before writing private FRK-P2 TraceV2 rows")
    root = REPO / "runs" / f"{PRIVATE_PREFIX}{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    root.mkdir(parents=True, exist_ok=True)
    rows, manifest = capture_rows_executable(root)
    errors = validate_rows(rows)
    if errors:
        raise CaptureError("captured TraceV2 rows failed validation: " + "; ".join(errors[:8]))
    write_jsonl(root / PRIVATE_ROW_FILENAME, rows)
    return build_report(rows, manifest, private_output_ignored=is_git_ignored(root))


def default_report() -> dict[str, Any]:
    return build_report([], {"manifest_primary_role_count": 0, "manifest_support_role_count": 0}, default_unavailable=True)


def fixture_report() -> dict[str, Any]:
    rows, manifest = capture_rows()
    report = build_report(rows, manifest)
    report["validation_summary"]["privacy_scan"] = "passed"
    return report


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    def check(name: str, ok: bool) -> None:
        checks.append((name, ok))
    rows, manifest = capture_rows()
    check("valid_rows", not validate_rows(rows))
    report = fixture_report()
    check("valid_report", not validate_report(report))
    fixture_episode_counts = Counter(row["episode_id"] for row in rows)
    fixture_actions = {row["action"]["action_type"] for row in rows}
    check(
        "selftest_minimum_count_anchor",
        len(rows) >= 90
        and len(fixture_episode_counts) >= 30
        and set(fixture_episode_counts.values()) == {len(ACTION_SEQUENCE)}
        and fixture_actions == set(ACTION_SEQUENCE)
        and manifest.get("manifest_episode_count") == len(fixture_episode_counts)
        and int(manifest.get("manifest_family_count", 0)) >= 3
        and int(manifest.get("manifest_query_type_count", 0)) >= 3,
    )
    try:
        run_capture(False)
        check("missing_private_output_confirmation_rejected", False)
    except CaptureError as exc:
        check("missing_private_output_confirmation_rejected", "--confirm-private-output" in str(exc))
    row_mutations = [
        ("unknown_top_level_rejected", ["unexpected"], True),
        ("missing_required_group_rejected", ["task"], None),
        ("missing_nested_state_subgroup_rejected", ["state", "candidate_pool"], None),
        ("unknown_nested_key_rejected", ["state", "rankpack", "bad"], "x"),
        ("bad_action_enum_rejected", ["action", "action_type"], "bad"),
        ("bad_target_question_rejected", ["action", "target_question"], "bad?"),
        ("non_predeclared_action_rejected", ["action", "predeclared_action_bool"], False),
        ("label_blind_policy_rejected", ["behavior_policy", "label_blind_features_only"], False),
        ("label_timing_rejected", ["outcome", "label_timing_isolated"], "false"),
        ("label_gold_state_rejected", ["state", "candidate_pool", "gold"], "success"),
        ("currentness_leak_rejected", ["state", "evidence_state", "currentness_fail_seen"], "verified_current"),
        ("evidence_conflation_rejected", ["state", "candidate_pool", "content_sha"], "abc"),
        ("observation_after_action_rejected", ["observation", "observation_after_action_bool"], False),
        ("new_algorithm_flag_rejected", ["privacy_execution", "new_retrieval_algorithm_executed"], True),
        ("new_channel_flag_rejected", ["privacy_execution", "new_channel_family_used"], True),
        ("candidate_expansion_flag_rejected", ["privacy_execution", "candidate_expansion_executed"], True),
        ("source_scan_flag_rejected", ["privacy_execution", "source_scan_executed"], True),
        ("provider_flag_rejected", ["privacy_execution", "provider_or_model_calls_executed"], True),
        ("network_flag_rejected", ["privacy_execution", "network_access"], "network_allowed"),
        ("ci_flag_rejected", ["privacy_execution", "ci_execution"], "ci"),
        ("training_flag_rejected", ["privacy_execution", "training_or_model_fitting_executed"], True),
        ("runtime_flag_rejected", ["privacy_execution", "runtime_default_changed"], True),
        ("kernel_flag_rejected", ["privacy_execution", "kernel_hardening_executed"], True),
    ]
    for name, path, value in row_mutations:
        mutated = copy.deepcopy(rows[:4])
        target = mutated[0]
        if value is None:
            for key in path[:-1]:
                target = target[key]
            target.pop(path[-1], None)
        else:
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
        check(name, bool(validate_rows(mutated)))
    non_monotonic = copy.deepcopy(rows[:4])
    non_monotonic[0], non_monotonic[1] = non_monotonic[1], non_monotonic[0]
    check("non_monotonic_episode_steps_rejected", bool(validate_rows(non_monotonic)))
    non_contiguous = copy.deepcopy(rows[:4])
    non_contiguous[3]["step_index"] = 4
    check("non_contiguous_episode_steps_rejected", bool(validate_rows(non_contiguous)))
    report_mutations = [
        ("public_path_leak_rejected", ["source_readbacks", "readback_scope"], "/workspace/OpenLocus/OpenLocus-Lab/runs/x.jsonl"),
        ("public_query_leak_rejected", ["source_readbacks", "readback_scope"], "crates/openlocus-cli/src/lib.rs:1-2"),
        ("public_hash_leak_rejected", ["source_readbacks", "readback_scope"], "a" * 64),
        ("public_private_ref_leak_rejected", ["source_readbacks", "readback_scope"], "private_ref_x"),
        ("raw_task_id_leak_rejected", ["source_readbacks", "readback_scope"], "wf00 success"),
        ("raw_row_publication_rejected", ["source_readbacks", "readback_scope"], '{"schema_version":"openlocus.state_action_trace.v2"}'),
        ("unknown_report_key_rejected", ["unexpected"], True),
        ("status_auth_inconsistency_rejected", ["stop_go", "authorized_next_phase"], AUTH_STOP),
        ("missing_tracev2a_readback_rejected", ["source_readbacks", "tracev2_a_status"], "bad"),
        ("private_output_gitignore_missing_rejected", ["private_io_buckets", "private_output_gitignore_check"], "failed"),
        ("report_new_algorithm_rejected", ["execution_attestations", "new_retrieval_algorithm_executed"], True),
        ("report_new_channel_rejected", ["execution_attestations", "new_channel_family_used"], True),
        ("report_candidate_cap_rejected", ["execution_attestations", "candidate_expansion_executed"], True),
        ("report_broad_scan_rejected", ["execution_attestations", "broad_source_scan_executed"], True),
        ("report_provider_rejected", ["execution_attestations", "provider_or_model_calls_executed"], True),
        ("report_network_rejected", ["execution_attestations", "network_access"], "network_allowed"),
        ("report_ci_rejected", ["execution_attestations", "ci_execution"], "ci"),
        ("report_training_rejected", ["execution_attestations", "rpm_d2_training_or_model_scaling_executed"], True),
        ("report_runtime_rejected", ["execution_attestations", "runtime_default_changed"], True),
        ("report_kernel_rejected", ["execution_attestations", "kernel_hardening_executed"], True),
        ("report_overauth_d2_rejected", ["stop_go", "rpm_d2_training_authorized"], True),
        ("report_overauth_new_prototype_rejected", ["stop_go", "new_retrieval_prototype_authorized"], True),
        ("privacy_summary_rejected", ["validation_summary", "privacy_scan"], "failed"),
    ]
    for name, path, value in report_mutations:
        mutated = copy.deepcopy(report)
        target = mutated
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        check(name, bool(validate_report(mutated)))
    haae_report = copy.deepcopy(report)
    haae_report["status"] = STATUS_HAAE
    haae_report["stop_go"]["authorized_next_phase"] = AUTH_HAAE
    haae_report["stop_go"]["decision"] = "haae_a2_replay_over_frk_p2_v2_rows_only"
    haae_report["stop_go"]["haae_a2_replay_authorized"] = True
    haae_report["stop_go"]["capture_repair_authorized"] = False
    haae_report["coverage_audit"]["critical_nested_coverage_sufficient"] = True
    haae_report["coverage_audit"]["unknown_missingness_bucket"] = "count_6_to_20"
    haae_report["manifest_diversity_buckets"]["workflow_family_bucket"] = "count_3_to_5"
    haae_report["replay_target_viability"]["replay_target_bucket"] = "count_2_to_5"
    haae_report["replay_target_viability"]["target_with_both_positive_negative_outcomes_bucket"] = "count_1"
    haae_report["replay_target_viability"]["haae_a2_positive_gate"] = True
    check("haae_fixture_valid", not validate_report(haae_report))
    haae_mutations = [
        ("haae_low_coverage_rejected", ["coverage_audit", "critical_nested_coverage_sufficient"], False),
        ("haae_low_family_rejected", ["manifest_diversity_buckets", "workflow_family_bucket"], "count_1"),
        ("haae_low_replay_rejected", ["replay_target_viability", "replay_target_bucket"], "count_1"),
        ("haae_low_outcome_balance_rejected", ["replay_target_viability", "target_with_both_positive_negative_outcomes_bucket"], "count_0"),
        ("schema_failure_auth_rejected", ["tracev2_validation", "v2_schema_validation"], "failed"),
    ]
    for name, path, value in haae_mutations:
        mutated = copy.deepcopy(haae_report)
        target = mutated
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        check(name, bool(validate_report(mutated)))
    failed = [name for name, ok in checks if not ok]
    return {"status": "passed" if not failed else "failed", "checks_passed": len(checks) - len(failed), "checks_total": len(checks), "failed_checks": failed}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run-capture", action="store_true")
    parser.add_argument("--confirm-private-output", action="store_true")
    parser.add_argument("--confirm-private-input", action="store_true", help="Accepted for contract compatibility; private input is not used by default")
    parser.add_argument("--validate-report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            result = run_self_test()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "passed" else 1
        if args.run_capture:
            report = run_capture(args.confirm_private_output)
            write_report(report)
            print(json.dumps({"public_report": str(DEFAULT_REPORT), "status": report["status"], "authorized_next_phase": report["stop_go"]["authorized_next_phase"], "private_row_count_bucket": report["private_io_buckets"]["private_row_count_bucket"], "private_episode_count_bucket": report["private_io_buckets"]["private_episode_count_bucket"]}, indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = read_json(args.validate_report)
            errors = validate_report(report)
            if errors:
                raise CaptureError("public report validation failed: " + "; ".join(errors[:12]))
            print(f"Validation passed: {args.validate_report}")
            return 0
        report = default_report()
        write_report(report)
        print(json.dumps({"public_report": str(DEFAULT_REPORT), "status": report["status"], "mode": "default_unavailable_no_private_output_confirmation"}, indent=2, sort_keys=True))
        return 0
    except CaptureError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
