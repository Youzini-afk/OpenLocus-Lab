#!/usr/bin/env python3
"""OpenLocus v2 FRK product-workflow failure decomposition.

This phase performs an executable empirical decomposition over the existing
private product-workflow benchmark traces only.  It never reruns retrieval,
search, read, citation validation, candidate generation, provider/model calls,
network work, CI, training, kernel hardening, or runtime/default changes.
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

import frk_product_workflow_trace_benchmark as benchmark
import rpm_trace_schema as schema


REPO = Path(__file__).resolve().parent.parent
PHASE = "openlocus_v2_frk_product_workflow_failure_decomposition"
REPORT_SCHEMA_VERSION = "frk_product_workflow_failure_decomposition_public_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / "frk_product_workflow_failure_decomposition" / "frk_product_workflow_failure_decomposition_report.json"
SOURCE_REPORT = REPO / "artifacts" / "frk_product_workflow_trace_benchmark" / "frk_product_workflow_trace_benchmark_report.json"
PRIVATE_PREFIX = "frk_product_workflow_private_"
TRACE_FILENAME = "frk_product_workflow_state_action_rows.jsonl"
LABEL_FILENAME = "frk_product_workflow_private_expected_labels.jsonl"

STATUS_REPAIR = "frk_product_workflow_failure_decomposition_incomplete_targeted_repair_only"
STATUS_INCONCLUSIVE = "frk_product_workflow_failure_decomposition_inconclusive_metric_design_trace_expansion_only"
STATUS_PROXY_FIXTURE = "frk_product_workflow_failure_decomposition_proxy_or_fixture_bias_trace_expansion_authorized"
STATUS_RETRIEVAL_REPAIR = "frk_product_workflow_failure_decomposition_query_channel_budget_repair_design_authorized"
STATUS_STOP = "frk_product_workflow_failure_decomposition_baseline_saturation_stop_or_collect_new_pain"

AUTHORIZED_REPAIR = "targeted_frk_product_workflow_failure_decomposition_repair_only"
AUTHORIZED_INCONCLUSIVE = "frk_product_workflow_trace_expansion_with_metric_design_repair"
AUTHORIZED_PROXY_FIXTURE = "frk_product_workflow_trace_expansion_with_proxy_or_fixture_repair"
AUTHORIZED_RETRIEVAL_REPAIR = "frk_product_workflow_specific_retrieval_repair_design"
AUTHORIZED_STOP = "stop_current_hybrid_retrieve_candidate_or_collect_new_product_workflow_pain"

ARMS = tuple(benchmark.ARMS)
BASELINE_ARMS = tuple(benchmark.BASELINE_ARMS)
CANDIDATE_ARM = "openlocus_hybrid_retrieve"

MECHANISMS = (
    "query_formulation_or_channel_mismatch",
    "retrieve_cli_fallback_or_channel_unavailable",
    "symbol_regex_dominance",
    "bm25_text_dominance",
    "wrong_file_or_rank_miss",
    "read_budget_or_topk_limit",
    "citation_or_currentness_failure",
    "task_fixture_bias",
    "success_proxy_weakness",
    "baseline_saturation",
    "inconclusive_private_trace_limit",
)

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
    "candidate_generation_expansion",
    "new_retrieval_experiment",
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


class DecompositionError(Exception):
    pass


def bucket_count(count: int) -> str:
    if count <= 0:
        return "count_0"
    if count == 1:
        return "count_1"
    if count <= 5:
        return "count_2_to_5"
    if count <= 20:
        return "count_6_to_20"
    if count <= 50:
        return "count_21_to_50"
    return "count_gt_50"


def bucket_rate(success: int, total: int) -> str:
    if total <= 0 or success <= 0:
        return "rate_0"
    rate = success / total
    if rate >= 1.0:
        return "rate_1"
    if rate >= 0.75:
        return "rate_75_to_99"
    if rate >= 0.50:
        return "rate_50_to_75"
    if rate >= 0.25:
        return "rate_25_to_50"
    return "rate_lt_25"


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DecompositionError(f"required public report missing: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise DecompositionError("required public report is malformed JSON") from exc
    if not isinstance(payload, dict):
        raise DecompositionError("required public report must be a JSON object")
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DecompositionError("private trace JSONL file is missing") from exc
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DecompositionError(f"malformed JSONL at private line {line_no}") from exc
        if not isinstance(item, dict):
            raise DecompositionError(f"private JSONL line {line_no} is not an object")
        rows.append(item)
    return rows


def latest_private_root() -> Path:
    runs = REPO / "runs"
    roots = [path for path in runs.glob(f"{PRIVATE_PREFIX}*") if path.is_dir() and (path / TRACE_FILENAME).exists()]
    if not roots:
        raise DecompositionError("no private product workflow trace root found")
    return sorted(roots, key=lambda path: (path.stat().st_mtime, path.name))[-1]


def load_private_inputs(confirm_private_input: bool, trace_jsonl: Path | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not confirm_private_input:
        raise DecompositionError("--confirm-private-input is required before reading private product-workflow traces")
    trace_path = trace_jsonl or (latest_private_root() / TRACE_FILENAME)
    rows = read_jsonl(trace_path)
    if not rows:
        raise DecompositionError("private trace JSONL is empty")
    row_errors = schema.validate_trace_rows(rows)
    if row_errors:
        raise DecompositionError("private trace rows failed Phase-1 schema validation: " + "; ".join(row_errors[:5]))
    label_path = trace_path.parent / LABEL_FILENAME
    labels = read_jsonl(label_path) if label_path.exists() else []
    if labels and not all(item.get("label_timing") == "after_action" for item in labels):
        raise DecompositionError("private labels must be after-action labels")
    manifest = {
        "storage_class": "ignored_repo_runs_private_jsonl",
        "row_count": len(rows),
        "episode_count": len({row["trace_identity"]["trace_id"] for row in rows}),
        "labels_present": bool(labels),
    }
    return rows, labels, manifest


def arm_maps() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    by_label = {benchmark.private_ref("arm", arm): arm for arm in ARMS}
    by_policy = {benchmark.private_ref("behavior_policy", arm): arm for arm in ARMS}
    family_by_task = {benchmark.private_ref("task", task.opaque_id): task.family for task in benchmark.TASKS}
    return by_label, by_policy, family_by_task


def trace_metrics(rows: list[dict[str, Any]], labels: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_arm_label, by_policy, family_by_task = arm_maps()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["trace_identity"]["trace_id"]].append(row)
    label_by_trace = {item.get("trace_id"): item for item in labels if isinstance(item.get("trace_id"), str)}
    metrics: dict[str, dict[str, Any]] = {}
    for trace_id, trace_rows in grouped.items():
        ordered = sorted(trace_rows, key=lambda row: row["trace_identity"]["created_order_index"])
        first = ordered[0]
        label = label_by_trace.get(trace_id, {})
        arm = by_arm_label.get(str(label.get("arm_private")), by_policy.get(first["policy_learning_support"].get("behavior_policy_id", ""), "unknown_arm"))
        task_private = str(label.get("task_id_private", ""))
        family = family_by_task.get(task_private, "unknown_family")
        workflow_rows = [row for row in ordered if row["action"]["action_type"] == "workflow_step"]
        workflow = workflow_rows[-1] if workflow_rows else ordered[-1]
        label_success = label.get("validated_current_evidence_matches_private_expected_workflow_need")
        success = bool(label_success) if isinstance(label_success, bool) else workflow["outcome_label"]["outcome_bucket"] == "success_bucket"
        retrieval_rows = [row for row in ordered if row["action"]["action_type"] == "bounded_retrieval"]
        retrieval = retrieval_rows[0] if retrieval_rows else ordered[0]
        read_rows = [row for row in ordered if row["action"]["action_type"] == "read_current_source"]
        validate_rows = [row for row in ordered if row["action"]["action_type"] == "validate_evidence"]
        valid_rows = [row for row in validate_rows if row["observation_result"]["failure_bucket"] == "none" and row["evidencecore_linkage"]["evidencecore_link_status"] == "linked_current"]
        metrics[trace_id] = {
            "arm": arm,
            "task_private": task_private,
            "family": family,
            "success": success,
            "workflow_failure_bucket": workflow["observation_result"]["failure_bucket"],
            "workflow_outcome_bucket": workflow["outcome_label"]["outcome_bucket"],
            "retrieval_failure_bucket": retrieval["observation_result"]["failure_bucket"],
            "retrieval_delta_bucket": retrieval["observation_result"]["evidence_delta_bucket"],
            "retrieval_result_bucket": retrieval["observation_result"]["result_bucket"],
            "read_count": len(read_rows),
            "validate_count": len(validate_rows),
            "valid_count": len(valid_rows),
            "validation_failed": any(row["observation_result"]["failure_bucket"] == "validation_failed" for row in validate_rows),
            "stale_or_invalid": any(row["evidencecore_linkage"]["evidencecore_link_status"] in {"stale_rejected", "missing"} for row in validate_rows),
            "partial_valid_wrong": (not success) and bool(valid_rows),
            "no_candidate": retrieval["observation_result"]["result_bucket"] == "no_change" or retrieval["observation_result"]["failure_bucket"] == "missing_source",
            "topk_candidates_present": retrieval["observation_result"]["evidence_delta_bucket"] in {"delta_2_to_5", "delta_gt_5"},
        }
    return metrics


def classify_loss(candidate: dict[str, Any], task_group: dict[str, dict[str, Any]]) -> str:
    text_success = task_group.get("text_bm25_baseline", {}).get("success") is True
    symbol_success = task_group.get("symbol_regex_baseline", {}).get("success") is True
    if candidate.get("no_candidate"):
        return "query_formulation_or_channel_mismatch"
    if candidate.get("validation_failed") or candidate.get("stale_or_invalid"):
        return "citation_or_currentness_failure"
    if candidate.get("partial_valid_wrong") or candidate.get("workflow_failure_bucket") == "other":
        return "wrong_file_or_rank_miss"
    if candidate.get("read_count", 0) >= 2 and candidate.get("topk_candidates_present"):
        return "read_budget_or_topk_limit"
    if text_success and symbol_success:
        return "baseline_saturation"
    if text_success:
        return "bm25_text_dominance"
    if symbol_success:
        return "symbol_regex_dominance"
    if candidate.get("validate_count", 0) == 0:
        return "retrieve_cli_fallback_or_channel_unavailable"
    return "success_proxy_weakness"


def decompose(rows: list[dict[str, Any]], labels: list[dict[str, Any]], source_report: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    metrics = trace_metrics(rows, labels)
    task_groups: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for item in metrics.values():
        task_groups[item["task_private"]][item["arm"]] = item

    arm_total = Counter(item["arm"] for item in metrics.values())
    arm_success = Counter(item["arm"] for item in metrics.values() if item["success"])
    candidate = CANDIDATE_ARM
    best_success_by_task = 0
    candidate_success_when_best_success = 0
    candidate_loss_when_best_success = 0
    candidate_success_when_best_failure = 0
    both_failure = 0
    mechanisms = Counter({name: 0 for name in MECHANISMS})
    family_losses = Counter()
    loss_total = 0
    for group in task_groups.values():
        cand = group.get(candidate)
        if cand is None:
            mechanisms["inconclusive_private_trace_limit"] += 1
            continue
        baseline_success = any(group.get(arm, {}).get("success") is True for arm in BASELINE_ARMS)
        if baseline_success:
            best_success_by_task += 1
            if cand["success"]:
                candidate_success_when_best_success += 1
            else:
                candidate_loss_when_best_success += 1
                loss_total += 1
                mechanism = classify_loss(cand, group)
                mechanisms[mechanism] += 1
                if mechanism != "read_budget_or_topk_limit" and cand.get("read_count", 0) >= 2 and cand.get("topk_candidates_present"):
                    mechanisms["read_budget_or_topk_limit"] += 1
                family_losses[cand["family"]] += 1
        elif cand["success"]:
            candidate_success_when_best_failure += 1
        else:
            both_failure += 1

    if not labels:
        mechanisms["inconclusive_private_trace_limit"] += max(1, len(task_groups))
    if loss_total:
        top_family_count = family_losses.most_common(1)[0][1] if family_losses else 0
        if top_family_count / loss_total >= 0.50:
            mechanisms["task_fixture_bias"] += top_family_count
    partial_failure_count = sum(1 for item in metrics.values() if item["arm"] == candidate and not item["success"] and item["workflow_outcome_bucket"] == "partial_bucket")
    if partial_failure_count >= max(2, loss_total // 3):
        mechanisms["success_proxy_weakness"] += partial_failure_count

    primary, primary_count = mechanisms.most_common(1)[0]
    secondary = mechanisms.most_common(2)[1][0] if len(mechanisms) > 1 else "inconclusive_private_trace_limit"
    if manifest["row_count"] < 120 or manifest["episode_count"] < 60 or not labels:
        primary = "inconclusive_private_trace_limit"
        status = STATUS_INCONCLUSIVE
        authorized = AUTHORIZED_INCONCLUSIVE
        confidence = "low"
    elif primary in {"task_fixture_bias", "success_proxy_weakness"}:
        status = STATUS_PROXY_FIXTURE
        authorized = AUTHORIZED_PROXY_FIXTURE
        confidence = "medium"
    elif primary in {"query_formulation_or_channel_mismatch", "retrieve_cli_fallback_or_channel_unavailable", "symbol_regex_dominance", "bm25_text_dominance", "wrong_file_or_rank_miss", "read_budget_or_topk_limit", "citation_or_currentness_failure"}:
        status = STATUS_RETRIEVAL_REPAIR
        authorized = AUTHORIZED_RETRIEVAL_REPAIR
        confidence = "high" if primary_count >= max(3, loss_total // 2) and manifest["row_count"] >= 120 else "medium"
    else:
        status = STATUS_STOP
        authorized = AUTHORIZED_STOP
        confidence = "medium"

    arm_rates = {arm: bucket_rate(arm_success.get(arm, 0), arm_total.get(arm, 0)) for arm in ARMS}
    return build_report(
        status=status,
        authorized=authorized,
        confidence=confidence,
        primary=primary,
        secondary=secondary,
        mechanisms=mechanisms,
        family_losses=family_losses,
        arm_rates=arm_rates,
        source_report=source_report,
        manifest=manifest,
        matrix={
            "best_baseline_success_candidate_success": candidate_success_when_best_success,
            "best_baseline_success_candidate_failure": candidate_loss_when_best_success,
            "best_baseline_failure_candidate_success": candidate_success_when_best_failure,
            "best_baseline_failure_candidate_failure": both_failure,
        },
    )


def build_report(
    *,
    status: str,
    authorized: str,
    confidence: str,
    primary: str,
    secondary: str,
    mechanisms: Counter[str],
    family_losses: Counter[str],
    arm_rates: dict[str, str],
    source_report: dict[str, Any],
    manifest: dict[str, Any],
    matrix: dict[str, int],
) -> dict[str, Any]:
    decision = EXPECTED_DECISION_BY_AUTH[authorized]
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "source_report_readback": {
            "source_phase": source_report.get("phase"),
            "source_status": source_report.get("status"),
            "source_best_baseline_delta_bucket": source_report.get("best_baseline_comparison", {}).get("candidate_vs_best_baseline_delta_bucket"),
            "source_public_report_level": source_report.get("validation_summary", {}).get("public_report_level"),
        },
        "input_attestation": {
            "private_input_confirmation": "confirmed",
            "existing_private_trace_rows_only": True,
            "matching_private_labels_used_if_present": bool(manifest.get("labels_present")),
            "committed_public_benchmark_report_used": True,
            "benchmark_script_used_for_schema_action_arm_readback_only": True,
            "new_retrieval_actions_executed": False,
            "search_read_or_citations_validate_rerun": False,
            "source_scan_executed": False,
            "candidate_generation_executed": False,
            "provider_or_model_calls_executed": False,
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "training_executed": False,
            "runtime_default_changed": False,
        },
        "aggregate_buckets": {
            "private_row_count_bucket": bucket_count(int(manifest.get("row_count", 0))),
            "private_episode_count_bucket": bucket_count(int(manifest.get("episode_count", 0))),
            "arm_utility_buckets_from_private_trace": arm_rates,
            "arm_vs_best_baseline_outcome_matrix_bucket": {key: bucket_count(value) for key, value in sorted(matrix.items())},
            "family_level_loss_concentration_buckets": {key: bucket_count(value) for key, value in sorted(family_losses.items())},
        },
        "mechanism_buckets": {name: bucket_count(mechanisms.get(name, 0)) for name in MECHANISMS},
        "decomposition_summary": {
            "primary_mechanism_bucket": primary,
            "secondary_mechanism_bucket": secondary,
            "confidence_bucket": confidence,
            "recommended_next_action_bucket": authorized,
            "publication_level": "aggregate_only",
        },
        "privacy_contract": {
            "publication_level": "aggregate_only",
            "private_trace_path_public": False,
            "private_label_path_public": False,
            "raw_task_ids_public": False,
            "raw_rows_public": False,
            "raw_paths_public": False,
            "ranges_public": False,
            "queries_public": False,
            "snippets_public": False,
            "hashes_public": False,
            "private_refs_public": False,
            "per_task_outcomes_public": False,
            "per_task_mechanisms_public": False,
            "evidence_filenames_public": False,
            "exact_labels_public": False,
            "raw_publication": False,
        },
        "stop_go": {
            "decision": decision,
            "authorized_next_phase": authorized,
            "explicitly_forbidden": sorted(PUBLIC_FORBIDDEN),
            "targeted_repair_only_if_input_schema_privacy_fails": True,
            "trace_expansion_with_metric_design_repair_if_inconclusive": status == STATUS_INCONCLUSIVE,
            "trace_expansion_with_proxy_or_fixture_repair_if_proxy_fixture_bias": status == STATUS_PROXY_FIXTURE,
            "specific_retrieval_repair_design_if_query_channel_budget_mechanism": status == STATUS_RETRIEVAL_REPAIR,
            "stop_or_collect_new_pain_if_baseline_saturation": status == STATUS_STOP,
            "d2_or_model_scaling_authorized": False,
            "rpm_training_authorized": False,
            "runtime_or_default_authorized": False,
            "provider_network_ci_authorized": False,
            "method_scale_winner_claims_allowed": False,
            "broad_source_scan_authorized": False,
            "candidate_expansion_authorized": False,
            "new_retrieval_experiment_authorized": False,
            "kernel_hardening_authorized": False,
            "raw_publication_authorized": False,
        },
        "validation_summary": {
            "strict_phase1_schema": "passed",
            "privacy_leak_scan": "pending",
            "self_test_mutation_coverage": "available",
            "public_report_level": "aggregate_only",
        },
    }


REPORT_TOP_KEYS = {
    "schema_version",
    "phase",
    "status",
    "source_report_readback",
    "input_attestation",
    "aggregate_buckets",
    "mechanism_buckets",
    "decomposition_summary",
    "privacy_contract",
    "stop_go",
    "validation_summary",
}

SOURCE_READBACK_KEYS = {
    "source_phase",
    "source_status",
    "source_best_baseline_delta_bucket",
    "source_public_report_level",
}
INPUT_ATTESTATION_KEYS = {
    "private_input_confirmation",
    "existing_private_trace_rows_only",
    "matching_private_labels_used_if_present",
    "committed_public_benchmark_report_used",
    "benchmark_script_used_for_schema_action_arm_readback_only",
    "new_retrieval_actions_executed",
    "search_read_or_citations_validate_rerun",
    "source_scan_executed",
    "candidate_generation_executed",
    "provider_or_model_calls_executed",
    "network_access",
    "ci_execution",
    "training_executed",
    "runtime_default_changed",
}
AGGREGATE_BUCKET_KEYS = {
    "private_row_count_bucket",
    "private_episode_count_bucket",
    "arm_utility_buckets_from_private_trace",
    "arm_vs_best_baseline_outcome_matrix_bucket",
    "family_level_loss_concentration_buckets",
}
MATRIX_KEYS = {
    "best_baseline_success_candidate_success",
    "best_baseline_success_candidate_failure",
    "best_baseline_failure_candidate_success",
    "best_baseline_failure_candidate_failure",
}
SUMMARY_KEYS = {
    "primary_mechanism_bucket",
    "secondary_mechanism_bucket",
    "confidence_bucket",
    "recommended_next_action_bucket",
    "publication_level",
}
PRIVACY_KEYS = {
    "publication_level",
    "private_trace_path_public",
    "private_label_path_public",
    "raw_task_ids_public",
    "raw_rows_public",
    "raw_paths_public",
    "ranges_public",
    "queries_public",
    "snippets_public",
    "hashes_public",
    "private_refs_public",
    "per_task_outcomes_public",
    "per_task_mechanisms_public",
    "evidence_filenames_public",
    "exact_labels_public",
    "raw_publication",
}
STOP_GO_KEYS = {
    "decision",
    "authorized_next_phase",
    "explicitly_forbidden",
    "targeted_repair_only_if_input_schema_privacy_fails",
    "trace_expansion_with_metric_design_repair_if_inconclusive",
    "trace_expansion_with_proxy_or_fixture_repair_if_proxy_fixture_bias",
    "specific_retrieval_repair_design_if_query_channel_budget_mechanism",
    "stop_or_collect_new_pain_if_baseline_saturation",
    "d2_or_model_scaling_authorized",
    "rpm_training_authorized",
    "runtime_or_default_authorized",
    "provider_network_ci_authorized",
    "method_scale_winner_claims_allowed",
    "broad_source_scan_authorized",
    "candidate_expansion_authorized",
    "new_retrieval_experiment_authorized",
    "kernel_hardening_authorized",
    "raw_publication_authorized",
}
VALIDATION_KEYS = {
    "strict_phase1_schema",
    "privacy_leak_scan",
    "self_test_mutation_coverage",
    "public_report_level",
}
COUNT_BUCKETS = {"count_0", "count_1", "count_2_to_5", "count_6_to_20", "count_21_to_50", "count_gt_50"}
RATE_BUCKETS = {"rate_0", "rate_lt_25", "rate_25_to_50", "rate_50_to_75", "rate_75_to_99", "rate_1"}
CONFIDENCE_BUCKETS = {"high", "medium", "low", "inconclusive"}
EXPECTED_DECISION_BY_AUTH = {
    AUTHORIZED_REPAIR: "repair_only",
    AUTHORIZED_INCONCLUSIVE: "trace_expansion_with_metric_design_repair_only",
    AUTHORIZED_PROXY_FIXTURE: "trace_expansion_with_proxy_or_fixture_repair_only",
    AUTHORIZED_RETRIEVAL_REPAIR: "specific_retrieval_repair_design_only",
    AUTHORIZED_STOP: "stop_current_candidate_or_collect_new_pain_only",
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
    hash_pattern = re.compile(r"\b[a-f0-9]{64}\b")
    for text in strings_in(report):
        if "private_ref_" in text:
            errors.append("private_ref leak")
        if "content_sha" in text:
            errors.append("content_sha leak")
        if path_pattern.search(text):
            errors.append("raw path/range/private file leak")
        if task_pattern.search(text):
            errors.append("exact task id leak")
        if hash_pattern.search(text):
            errors.append("hash leak")
    return errors


def expected_allowed_for_status(status: str) -> str | None:
    return {
        STATUS_REPAIR: AUTHORIZED_REPAIR,
        STATUS_INCONCLUSIVE: AUTHORIZED_INCONCLUSIVE,
        STATUS_PROXY_FIXTURE: AUTHORIZED_PROXY_FIXTURE,
        STATUS_RETRIEVAL_REPAIR: AUTHORIZED_RETRIEVAL_REPAIR,
        STATUS_STOP: AUTHORIZED_STOP,
    }.get(status)


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(report) != REPORT_TOP_KEYS:
        errors.append("public report has missing or unknown top-level keys")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append("schema_version drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    status = report.get("status")
    if not isinstance(status, str):
        errors.append("status must be string")
        status = ""
    if status not in {STATUS_REPAIR, STATUS_INCONCLUSIVE, STATUS_PROXY_FIXTURE, STATUS_RETRIEVAL_REPAIR, STATUS_STOP}:
        errors.append("unknown status")

    source = report.get("source_report_readback", {})
    if not isinstance(source, dict) or set(source) != SOURCE_READBACK_KEYS:
        errors.append("source readback keys drift")
    if source.get("source_status") != benchmark.STATUS_NO_LIFT:
        errors.append("source benchmark no-lift status not read back")
    if source.get("source_best_baseline_delta_bucket") != "negative_vs_best_baseline":
        errors.append("source best-baseline negative delta not read back")

    input_attestation = report.get("input_attestation", {})
    if not isinstance(input_attestation, dict) or set(input_attestation) != INPUT_ATTESTATION_KEYS:
        errors.append("input attestation keys drift")
    for field in (
        "existing_private_trace_rows_only",
        "committed_public_benchmark_report_used",
        "benchmark_script_used_for_schema_action_arm_readback_only",
    ):
        if input_attestation.get(field) is not True:
            errors.append(f"input_attestation.{field} must be true")
    for field in (
        "new_retrieval_actions_executed",
        "search_read_or_citations_validate_rerun",
        "source_scan_executed",
        "candidate_generation_executed",
        "provider_or_model_calls_executed",
        "training_executed",
        "runtime_default_changed",
    ):
        if input_attestation.get(field) is not False:
            errors.append(f"input_attestation.{field} must be false")
    if input_attestation.get("private_input_confirmation") != "confirmed":
        errors.append("private input confirmation missing")
    if input_attestation.get("network_access") != "no_network" or input_attestation.get("ci_execution") != "local_manual_only":
        errors.append("network/CI attestation drift")

    aggregate = report.get("aggregate_buckets", {})
    if not isinstance(aggregate, dict) or set(aggregate) != AGGREGATE_BUCKET_KEYS:
        errors.append("aggregate bucket keys drift")
    if aggregate.get("private_row_count_bucket") not in COUNT_BUCKETS:
        errors.append("private row count bucket invalid")
    if aggregate.get("private_episode_count_bucket") not in COUNT_BUCKETS:
        errors.append("private episode count bucket invalid")
    arm_rates = aggregate.get("arm_utility_buckets_from_private_trace", {})
    if not isinstance(arm_rates, dict) or set(arm_rates) != set(ARMS):
        errors.append("arm utility bucket keys drift")
    elif any(value not in RATE_BUCKETS for value in arm_rates.values()):
        errors.append("arm utility bucket value invalid")
    matrix = aggregate.get("arm_vs_best_baseline_outcome_matrix_bucket", {})
    if not isinstance(matrix, dict) or set(matrix) != MATRIX_KEYS:
        errors.append("arm-vs-best-baseline matrix keys drift")
    elif any(value not in COUNT_BUCKETS for value in matrix.values()):
        errors.append("arm-vs-best-baseline matrix bucket invalid")
    family_buckets = aggregate.get("family_level_loss_concentration_buckets", {})
    if not isinstance(family_buckets, dict) or any(value not in COUNT_BUCKETS for value in family_buckets.values()):
        errors.append("family loss concentration bucket invalid")

    mechanisms = report.get("mechanism_buckets", {})
    if set(mechanisms) != set(MECHANISMS):
        errors.append("mechanism coverage keys drift")
    elif any(value not in COUNT_BUCKETS for value in mechanisms.values()):
        errors.append("mechanism bucket invalid")
    if all(value == "count_0" for value in mechanisms.values()):
        errors.append("no mechanism coverage")
    summary = report.get("decomposition_summary", {})
    if not isinstance(summary, dict) or set(summary) != SUMMARY_KEYS:
        errors.append("decomposition summary keys drift")
    primary = summary.get("primary_mechanism_bucket")
    secondary = summary.get("secondary_mechanism_bucket")
    if primary not in MECHANISMS or secondary not in MECHANISMS:
        errors.append("primary/secondary mechanism not in public mechanism enum")
    if summary.get("confidence_bucket") not in CONFIDENCE_BUCKETS:
        errors.append("confidence bucket invalid")
    if summary.get("recommended_next_action_bucket") != expected_allowed_for_status(status):
        errors.append("summary recommended next action drift")
    row_bucket = aggregate.get("private_row_count_bucket")
    if summary.get("confidence_bucket") == "high" and row_bucket not in {"count_21_to_50", "count_gt_50"}:
        errors.append("high confidence with insufficient rows")
    if summary.get("publication_level") != "aggregate_only":
        errors.append("summary publication level drift")

    privacy = report.get("privacy_contract", {})
    if not isinstance(privacy, dict) or set(privacy) != PRIVACY_KEYS:
        errors.append("privacy contract keys drift")
    for field in (
        "private_trace_path_public", "private_label_path_public", "raw_task_ids_public", "raw_rows_public",
        "raw_paths_public", "ranges_public", "queries_public", "snippets_public", "hashes_public",
        "private_refs_public", "per_task_outcomes_public", "per_task_mechanisms_public", "evidence_filenames_public",
        "exact_labels_public", "raw_publication",
    ):
        if privacy.get(field) is not False:
            errors.append(f"privacy_contract.{field} must be false")
    if privacy.get("publication_level") != "aggregate_only":
        errors.append("privacy publication level drift")

    stop = report.get("stop_go", {})
    if not isinstance(stop, dict) or set(stop) != STOP_GO_KEYS:
        errors.append("stop/go keys drift")
    if stop.get("authorized_next_phase") != expected_allowed_for_status(status):
        errors.append("authorized next phase drift")
    authorized_next = stop.get("authorized_next_phase")
    expected_decision = EXPECTED_DECISION_BY_AUTH.get(authorized_next) if isinstance(authorized_next, str) else None
    if stop.get("decision") != expected_decision:
        errors.append("stop/go decision drift")
    if set(stop.get("explicitly_forbidden", [])) != PUBLIC_FORBIDDEN:
        errors.append("forbidden route set drift")
    for field in (
        "d2_or_model_scaling_authorized", "rpm_training_authorized", "runtime_or_default_authorized",
        "provider_network_ci_authorized", "method_scale_winner_claims_allowed", "broad_source_scan_authorized",
        "candidate_expansion_authorized", "new_retrieval_experiment_authorized", "kernel_hardening_authorized",
        "raw_publication_authorized",
    ):
        if stop.get(field) is not False:
            errors.append(f"stop_go.{field} must be false")
    if stop.get("authorized_next_phase") in stop.get("explicitly_forbidden", []):
        errors.append("forbidden phase authorized")
    if status == STATUS_RETRIEVAL_REPAIR and primary not in {
        "query_formulation_or_channel_mismatch",
        "retrieve_cli_fallback_or_channel_unavailable",
        "symbol_regex_dominance",
        "bm25_text_dominance",
        "wrong_file_or_rank_miss",
        "read_budget_or_topk_limit",
        "citation_or_currentness_failure",
    }:
        errors.append("retrieval repair status without retrieval mechanism")
    expected_flags = {
        "trace_expansion_with_metric_design_repair_if_inconclusive": status == STATUS_INCONCLUSIVE,
        "trace_expansion_with_proxy_or_fixture_repair_if_proxy_fixture_bias": status == STATUS_PROXY_FIXTURE,
        "specific_retrieval_repair_design_if_query_channel_budget_mechanism": status == STATUS_RETRIEVAL_REPAIR,
        "stop_or_collect_new_pain_if_baseline_saturation": status == STATUS_STOP,
    }
    for field, expected in expected_flags.items():
        if stop.get(field) is not expected:
            errors.append(f"stop_go.{field} inconsistent with status")
    if stop.get("targeted_repair_only_if_input_schema_privacy_fails") is not True:
        errors.append("targeted repair fallback not locked")
    validation = report.get("validation_summary", {})
    if not isinstance(validation, dict) or set(validation) != VALIDATION_KEYS:
        errors.append("validation summary keys drift")
    if validation.get("strict_phase1_schema") != "passed":
        errors.append("strict schema validation not passed")
    if validation.get("privacy_leak_scan") != "passed":
        errors.append("privacy leak scan not passed")
    if validation.get("self_test_mutation_coverage") != "available":
        errors.append("self-test mutation coverage not available")
    if validation.get("public_report_level") != "aggregate_only":
        errors.append("validation publication level drift")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    final = copy.deepcopy(report)
    final["validation_summary"]["privacy_leak_scan"] = "passed" if not public_leak_errors(final) else "failed"
    errors = validate_public_report(final)
    if errors:
        raise DecompositionError("public report validation failed: " + "; ".join(errors[:8]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fixture_report() -> dict[str, Any]:
    mechanisms = Counter({name: 0 for name in MECHANISMS})
    mechanisms["wrong_file_or_rank_miss"] = 7
    mechanisms["bm25_text_dominance"] = 4
    return build_report(
        status=STATUS_RETRIEVAL_REPAIR,
        authorized=AUTHORIZED_RETRIEVAL_REPAIR,
        confidence="high",
        primary="wrong_file_or_rank_miss",
        secondary="bm25_text_dominance",
        mechanisms=mechanisms,
        family_losses=Counter({"index_search_behavior": 3, "cli_usage_api_lookup": 2}),
        arm_rates={"text_bm25_baseline": "rate_50_to_75", "symbol_regex_baseline": "rate_25_to_50", "openlocus_hybrid_retrieve": "rate_25_to_50"},
        source_report={
            "phase": benchmark.PHASE,
            "status": benchmark.STATUS_NO_LIFT,
            "best_baseline_comparison": {"candidate_vs_best_baseline_delta_bucket": "negative_vs_best_baseline"},
            "validation_summary": {"public_report_level": "aggregate_only"},
        },
        manifest={"row_count": 336, "episode_count": 60, "labels_present": True},
        matrix={
            "best_baseline_success_candidate_success": 7,
            "best_baseline_success_candidate_failure": 8,
            "best_baseline_failure_candidate_success": 1,
            "best_baseline_failure_candidate_failure": 4,
        },
    )


def run_self_tests() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, condition))

    valid = fixture_report()
    valid["validation_summary"]["privacy_leak_scan"] = "passed"
    check("fixture_report_valid", not validate_public_report(valid))
    try:
        load_private_inputs(False)
        check("missing_private_input_confirmation_rejected", False)
    except DecompositionError as exc:
        check("missing_private_input_confirmation_rejected", "--confirm-private-input" in str(exc))
    tmp = REPO / "artifacts" / "frk_product_workflow_failure_decomposition" / "selftest_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        try:
            load_private_inputs(True, tmp / "missing.jsonl")
            check("missing_trace_file_rejected", False)
        except DecompositionError as exc:
            check("missing_trace_file_rejected", "private trace JSONL file is missing" in str(exc))
        bad_jsonl = tmp / "bad.jsonl"
        bad_jsonl.write_text("{not json}\n", encoding="utf-8")
        try:
            load_private_inputs(True, bad_jsonl)
            check("malformed_jsonl_rejected", False)
        except DecompositionError as exc:
            check("malformed_jsonl_rejected", "malformed JSONL" in str(exc))
        rows, _stats, _manifest = benchmark.fixture_rows_and_stats()
        rows[0]["trace_identity"]["schema_version"] = "bad"
        invalid_trace = tmp / "invalid_rows.jsonl"
        invalid_trace.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        try:
            load_private_inputs(True, invalid_trace)
            check("phase1_schema_invalid_row_rejected", False)
        except DecompositionError as exc:
            check("phase1_schema_invalid_row_rejected", "Phase-1 schema validation" in str(exc))
    finally:
        for child in tmp.glob("*"):
            child.unlink()
        tmp.rmdir()

    for leak_name, leak_value in (
        ("raw_path", "/workspace/OpenLocus/OpenLocus-Lab/runs/private/foo.jsonl"),
        ("query", "crates/openlocus-cli/src/lib.rs:60-110"),
        ("snippet", "docs/en/research-summary.md"),
        ("private_ref", "private_ref_trace_abcdef"),
        ("hash", "a" * 64),
        ("content_sha", "content_sha"),
        ("exact_task_id", "wf03"),
    ):
        mutated = copy.deepcopy(valid)
        mutated["decomposition_summary"]["recommended_next_action_bucket"] = leak_value
        check(f"public_leak_{leak_name}_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["unknown"] = True
    check("unknown_report_key_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["stop_go"]["d2_or_model_scaling_authorized"] = True
    mutated["stop_go"]["rpm_training_authorized"] = True
    check("fake_lift_d2_training_overauthorization_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["stop_go"]["runtime_or_default_authorized"] = True
    mutated["stop_go"]["provider_network_ci_authorized"] = True
    check("runtime_default_provider_network_ci_overauthorization_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["mechanism_buckets"] = {name: "count_0" for name in MECHANISMS}
    check("no_mechanism_coverage_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["aggregate_buckets"]["private_row_count_bucket"] = "count_6_to_20"
    mutated["decomposition_summary"]["confidence_bucket"] = "high"
    check("high_confidence_with_insufficient_rows_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["input_attestation"]["new_retrieval_actions_executed"] = True
    check("new_retrieval_flag_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["input_attestation"]["source_scan_executed"] = True
    check("source_scan_flag_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["source_report_readback"]["unexpected"] = "field"
    check("source_readback_key_drift_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["aggregate_buckets"]["arm_vs_best_baseline_outcome_matrix_bucket"].pop("best_baseline_failure_candidate_success")
    check("matrix_key_drop_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["aggregate_buckets"]["arm_utility_buckets_from_private_trace"]["openlocus_hybrid_retrieve"] = "rate_100"
    check("arm_rate_bucket_drift_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["mechanism_buckets"]["wrong_file_or_rank_miss"] = "count_999"
    check("mechanism_bucket_drift_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["decomposition_summary"]["recommended_next_action_bucket"] = AUTHORIZED_INCONCLUSIVE
    check("summary_next_action_drift_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["privacy_contract"].pop("queries_public")
    check("privacy_key_drop_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["stop_go"].pop("new_retrieval_experiment_authorized")
    check("stop_go_key_drop_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["stop_go"]["decision"] = "trace_expansion_with_metric_design_repair_only"
    check("stop_go_decision_drift_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["stop_go"]["specific_retrieval_repair_design_if_query_channel_budget_mechanism"] = False
    check("status_flag_inconsistency_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["validation_summary"]["privacy_leak_scan"] = "pending"
    check("privacy_scan_pending_rejected", bool(validate_public_report(mutated)))
    check("self_test_count_consistency", len(checks) >= 28)
    failed = [name for name, ok in checks if not ok]
    return {"status": "passed" if not failed else "failed", "checks_passed": len(checks) - len(failed), "checks_total": len(checks), "failed_checks": failed}


def run_decomposition(confirm_private_input: bool, trace_jsonl: Path | None = None) -> dict[str, Any]:
    rows, labels, manifest = load_private_inputs(confirm_private_input, trace_jsonl)
    source_report = read_json(SOURCE_REPORT)
    return decompose(rows, labels, source_report, manifest)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run-failure-decomposition", action="store_true")
    parser.add_argument("--confirm-private-input", action="store_true")
    parser.add_argument("--trace-jsonl", type=Path, default=None)
    parser.add_argument("--validate-report", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        if args.self_test:
            result = run_self_tests()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "passed" else 1
        if args.run_failure_decomposition:
            report = run_decomposition(args.confirm_private_input, args.trace_jsonl)
            write_report(report)
            final = read_json(DEFAULT_REPORT)
            print(json.dumps({
                "public_report": str(DEFAULT_REPORT),
                "status": final["status"],
                "primary_mechanism_bucket": final["decomposition_summary"]["primary_mechanism_bucket"],
                "secondary_mechanism_bucket": final["decomposition_summary"]["secondary_mechanism_bucket"],
                "authorized_next_phase": final["stop_go"]["authorized_next_phase"],
            }, indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = read_json(args.validate_report)
            errors = validate_public_report(report)
            if errors:
                raise DecompositionError("public report validation failed: " + "; ".join(errors[:10]))
            print(f"Validation passed: {args.validate_report}")
            return 0
        parser.print_help()
        return 2
    except DecompositionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
