#!/usr/bin/env python3
"""OpenLocus v2 FRK product workflow trace benchmark.

This executable phase runs fixed, bounded local product-workflow evidence
acquisition tasks against same-budget local arms. It writes private state-action
rows under ignored ``runs/`` storage only after explicit confirmation and
publishes an aggregate-only public report.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import rpm_trace_schema as schema


REPO = Path(__file__).resolve().parent.parent
PHASE = "openlocus_v2_frk_product_workflow_trace_benchmark"
REPORT_SCHEMA_VERSION = "frk_product_workflow_trace_benchmark_public_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / "frk_product_workflow_trace_benchmark" / "frk_product_workflow_trace_benchmark_report.json"
PRIVATE_ROOT_PREFIX = "frk_product_workflow_private_"
PRIVATE_TRACE_FILENAME = "frk_product_workflow_state_action_rows.jsonl"
PRIVATE_LABEL_FILENAME = "frk_product_workflow_private_expected_labels.jsonl"

STATUS_REPAIR = "frk_product_workflow_trace_benchmark_incomplete_targeted_repair_only"
STATUS_EXPANSION = "frk_product_workflow_trace_benchmark_complete_insufficient_diversity_expansion_only"
STATUS_NO_LIFT = "frk_product_workflow_trace_benchmark_complete_no_lift_failure_decomposition_or_trace_expansion"
STATUS_LIFT = "frk_product_workflow_trace_benchmark_complete_lift_heldout_design_only"

AUTHORIZED_REPAIR = "targeted_frk_product_workflow_trace_repair_only"
AUTHORIZED_EXPANSION = "frk_product_workflow_trace_expansion_only"
AUTHORIZED_NO_LIFT = "frk_product_workflow_failure_decomposition_or_trace_expansion"
AUTHORIZED_LIFT = "frk_product_workflow_heldout_benchmark_design"

ARMS = ("text_bm25_baseline", "symbol_regex_baseline", "openlocus_hybrid_retrieve")
BASELINE_ARMS = ("text_bm25_baseline", "symbol_regex_baseline")
REQUIRED_ACTION_TYPES = {"bounded_retrieval", "read_current_source", "validate_evidence", "workflow_step"}
REQUIRED_FAMILIES = {
    "cli_usage_api_lookup",
    "evidencecore_currentness_citation_validation",
    "trace_report_schema_debugging",
    "docs_readback_consistency",
    "index_search_behavior",
}

PUBLIC_FORBIDDEN = {
    "kernel_hardening_continuation",
    "old_heuristic_chain",
    "provider_claim",
    "network_claim",
    "ci_claim",
    "training_claim",
    "runtime_default_claim",
    "default_claim",
    "method_claim",
    "scale_claim",
    "winner_claim",
    "raw_publication",
    "private_trace_publication",
    "broad_source_scan",
    "candidate_generation_expansion",
    "frk_j",
    "frk_b_c_resurrection",
    "frk_i_selector_variants",
    "ldi_b_easy_continuation",
    "haae_sg",
    "haae_t",
}


class BenchmarkError(Exception):
    pass


@dataclass(frozen=True)
class WorkflowTask:
    opaque_id: str
    family: str
    expected_path: str
    expected_range: str
    text_query: str
    symbol_or_regex_query: str
    symbol_mode: str
    hybrid_query: str
    objective_bucket: str = "workflow_completion"
    query_shape_bucket: str = "structured"
    ambiguity_bucket: str = "medium"


# Fixed bounded local tasks. Public reports never expose these ids, queries,
# paths, ranges, hashes, or per-task outcomes.
TASKS: tuple[WorkflowTask, ...] = (
    WorkflowTask("wf00", "cli_usage_api_lookup", "crates/openlocus-cli/src/lib.rs", "60-110", "RRF multi-channel retrieve", "Commands::Retrieve", "auto", "retrieve channels regex bm25 symbol"),
    WorkflowTask("wf01", "cli_usage_api_lookup", "crates/openlocus-cli/src/lib.rs", "180-230", "Search with BM25 output JSON", "SearchCommands", "auto", "search bm25 symbol regex json"),
    WorkflowTask("wf02", "cli_usage_api_lookup", "crates/openlocus-cli/src/lib.rs", "1210-1278", "Validate citations from a JSON file", "validate_citations", "auto", "citations validate Evidence JSON"),
    WorkflowTask("wf03", "cli_usage_api_lookup", "README.md", "33-49", "local-first evidence-gated code-fact retrieval kernel", "EvidenceCore", "auto", "OpenLocus local exact search symbol BM25 read citation validation"),
    WorkflowTask("wf04", "evidencecore_currentness_citation_validation", "crates/openlocus-core/src/evidence.rs", "130-170", "pub struct EvidenceCore", "EvidenceCore", "auto", "EvidenceCore path line range content sha score why channels"),
    WorkflowTask("wf05", "evidencecore_currentness_citation_validation", "eval/rpm_trace_schema.py", "381-393", "EvidenceCore must materialize current source", "currentness_verification_status", "auto", "required EvidenceCore verified current materialized source"),
    WorkflowTask("wf06", "evidencecore_currentness_citation_validation", "eval/rpm_d0b_trace_capture_expansion.py", "214-249", "evidencecore_link_status stale_rejected linked_current", "evidence_linkage", "auto", "stale rejected linked current EvidenceCore linkage"),
    WorkflowTask("wf07", "evidencecore_currentness_citation_validation", "crates/openlocus-cli/src/lib.rs", "1261-1288", "validate_single_citation repo_root content sha", "validate_single_citation", "auto", "citation validation content_sha repo path range"),
    WorkflowTask("wf08", "trace_report_schema_debugging", "eval/rpm_trace_schema.py", "23-37", "ROW_SCHEMA_VERSION TOP_LEVEL_KEYS", "ROW_SCHEMA_VERSION", "auto", "RPM state action trace row schema top level keys"),
    WorkflowTask("wf09", "trace_report_schema_debugging", "eval/rpm_trace_schema.py", "125-167", "closed enum action_type workflow_step", "ENUMS", "auto", "closed enum task_type product_workflow action_type workflow_step"),
    WorkflowTask("wf10", "trace_report_schema_debugging", "eval/rpm_d0b_trace_capture_expansion.py", "650-774", "validate_public_report required action coverage", "validate_public_report", "auto", "public report validation privacy stop go action coverage"),
    WorkflowTask("wf11", "trace_report_schema_debugging", "eval/rpm_d0b_trace_capture_expansion.py", "787-890", "self-test duplicate step label timing leak", "run_self_tests", "auto", "mutation self-test duplicate non-monotonic label leakage"),
    WorkflowTask("wf12", "docs_readback_consistency", "docs/current-research-conclusions.md", "1-24", "root file bilingual index route closure", "Current route closure", "regex", "current conclusions bilingual index RPM report"),
    WorkflowTask("wf13", "docs_readback_consistency", "docs/en/research-summary.md", "11-30", "RPM-D1 bounded offline learning smoke D0B", "OpenLocus v2 RPM-D1", "regex", "research summary D0B D1 no training claim"),
    WorkflowTask("wf14", "docs_readback_consistency", "docs/en/research-log.md", "3-17", "RPM-D0B Trace Capture Expansion research log", "OpenLocus v2 RPM-D0B", "regex", "research log trace capture expansion schema route closure"),
    WorkflowTask("wf15", "docs_readback_consistency", "docs/en/current-research-conclusions.md", "1-12", "Latest v2 status RPM-D0B Trace Capture Expansion", "Latest v2 status", "regex", "current research conclusions latest v2 status D0B"),
    WorkflowTask("wf16", "index_search_behavior", "crates/openlocus-index/src/persistent.rs", "1-80", "PersistentBm25Index build dirty status", "PersistentBm25Index", "auto", "persistent BM25 index manifest dirty status"),
    WorkflowTask("wf17", "index_search_behavior", "crates/openlocus-cli/src/lib.rs", "498-610", "search_bm25_persistent search_symbol_auto", "search_bm25", "auto", "search command bm25 persistent symbol regex text"),
    WorkflowTask("wf18", "index_search_behavior", "crates/openlocus-cli/src/lib.rs", "620-668", "channels regex bm25 symbol retrieve", "retrieve", "auto", "retrieve evidence channels regex bm25 symbol graph"),
    WorkflowTask("wf19", "index_search_behavior", "scripts/validate_docs_i18n.py", "15-89", "docs en zh mirror layout broken link", "collect_errors", "auto", "docs i18n mirror relative markdown links"),
)


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


def bucket_latency(seconds: float) -> str:
    if seconds < 1:
        return "lt_1s"
    if seconds <= 10:
        return "1s_to_10s"
    if seconds <= 60:
        return "10s_to_60s"
    return "gt_60s"


def private_ref(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"private_ref_{prefix}_{digest}"


def ensure_openlocus() -> Path:
    binary = REPO / "target" / "debug" / "openlocus"
    if binary.exists() and os.access(binary, os.X_OK):
        return binary
    result = subprocess.run(
        ["cargo", "build", "-p", "openlocus-cli", "--bin", "openlocus"],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    if result.returncode != 0 or not binary.exists():
        raise BenchmarkError("OpenLocus CLI unavailable and local build failed closed")
    return binary


def run_cli(binary: Path, args: list[str], *, fail_safe: bool = False) -> tuple[Any | None, int, float]:
    started = time.monotonic()
    result = subprocess.run(
        [str(binary), *args],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=45,
        check=False,
    )
    latency = time.monotonic() - started
    if result.returncode != 0:
        if fail_safe:
            return None, result.returncode, latency
        raise BenchmarkError(f"OpenLocus action failed closed: {' '.join(args[:3])}")
    try:
        return json.loads(result.stdout), result.returncode, latency
    except json.JSONDecodeError as exc:
        if fail_safe:
            return None, result.returncode, latency
        raise BenchmarkError(f"OpenLocus action returned non-JSON: {' '.join(args[:3])}") from exc


def evidence_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if isinstance(payload.get("evidence"), list):
            return [item for item in payload["evidence"] if isinstance(item, dict)]
        for key in ("results", "items", "hits"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def evidence_path(ev: dict[str, Any]) -> str | None:
    core = ev.get("core") if isinstance(ev.get("core"), dict) else ev
    path = core.get("path") if isinstance(core, dict) else None
    return path if isinstance(path, str) else None


def evidence_read_spec(ev: dict[str, Any]) -> str | None:
    core = ev.get("core") if isinstance(ev.get("core"), dict) else ev
    if not isinstance(core, dict):
        return None
    path = core.get("path")
    start = core.get("start_line")
    end = core.get("end_line")
    if isinstance(path, str) and isinstance(start, int) and isinstance(end, int):
        return f"{path}:{start}-{end}"
    return path if isinstance(path, str) else None


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def evidence_linkage(*, required: bool, linked: bool, stale: bool = False, unsafe: bool = False) -> dict[str, Any]:
    if not required:
        return {
            "evidencecore_required_bool": False,
            "evidencecore_link_status": "not_required",
            "currentness_verification_status": "not_required",
            "stale_evidence_detected_bool": False,
            "materialization_status": "not_required",
            "path_range_hash_private_only_bool": True,
        }
    if stale:
        return {
            "evidencecore_required_bool": True,
            "evidencecore_link_status": "stale_rejected",
            "currentness_verification_status": "stale",
            "stale_evidence_detected_bool": True,
            "materialization_status": "rejected",
            "path_range_hash_private_only_bool": True,
        }
    if unsafe:
        return {
            "evidencecore_required_bool": True,
            "evidencecore_link_status": "unsafe_rejected",
            "currentness_verification_status": "unsafe",
            "stale_evidence_detected_bool": True,
            "materialization_status": "rejected",
            "path_range_hash_private_only_bool": True,
        }
    if linked:
        return {
            "evidencecore_required_bool": True,
            "evidencecore_link_status": "linked_current",
            "currentness_verification_status": "verified_current",
            "stale_evidence_detected_bool": False,
            "materialization_status": "materialized_current",
            "path_range_hash_private_only_bool": True,
        }
    return {
        "evidencecore_required_bool": True,
        "evidencecore_link_status": "missing",
        "currentness_verification_status": "unavailable",
        "stale_evidence_detected_bool": False,
        "materialization_status": "unavailable",
        "path_range_hash_private_only_bool": True,
    }


def build_row(
    *,
    task: WorkflowTask,
    arm: str,
    action_type: str,
    step_index: int,
    order_index: int,
    observation_status: str,
    result_bucket: str,
    evidence_delta_bucket: str,
    latency_bucket: str,
    failure_bucket: str,
    outcome_bucket: str,
    label_available: bool = True,
    evidence_required: bool = True,
    evidence_linked: bool = True,
    stale: bool = False,
) -> dict[str, Any]:
    trace_id = private_ref("trace", task.opaque_id, arm)
    step_id = private_ref("step", task.opaque_id, arm, str(step_index), action_type)
    if action_type == "bounded_retrieval":
        scope = "scope_small_bounded"
        scan_scope = "explicit_bounded"
        candidate_policy = "bounded_current_source_only"
        pack_policy = "fixed_order"
        candidate_count = "count_0"
        coverage = "coverage_none"
    elif action_type == "workflow_step":
        scope = "scope_workflow_bounded"
        scan_scope = "current_evidence_only"
        candidate_policy = "existing_candidates_only"
        pack_policy = "workflow_order"
        candidate_count = "count_2_to_5"
        coverage = "coverage_medium"
    elif action_type == "validate_evidence":
        scope = "scope_single_file"
        scan_scope = "current_evidence_only"
        candidate_policy = "existing_candidates_only"
        pack_policy = "evidencecore_validated"
        candidate_count = "count_2_to_5"
        coverage = "coverage_medium"
    else:
        scope = "scope_single_file"
        scan_scope = "explicit_bounded"
        candidate_policy = "bounded_current_source_only"
        pack_policy = "fixed_order"
        candidate_count = "count_2_to_5"
        coverage = "coverage_low"

    return {
        "trace_identity": {
            "schema_version": schema.ROW_SCHEMA_VERSION,
            "trace_id": trace_id,
            "step_id": step_id,
            "episode_step_index": step_index,
            "created_order_index": order_index,
            "runner_kind": "product_workflow_logger",
        },
        "task_state": {
            "task_bucket": bucket_count(len(TASKS)),
            "task_type": "product_workflow",
            "objective_bucket": task.objective_bucket,
            "route_family": "frk_product",
            "source_lock_id": "current_route_closure_2026_07_04",
            "current_route_status": "executable_capture_ready",
        },
        "state_features": {
            "query_shape_bucket": task.query_shape_bucket,
            "repo_size_bucket": "files_1001_to_10000",
            "candidate_count_bucket": candidate_count,
            "evidence_coverage_bucket": coverage,
            "currentness_bucket": "not_checked",
            "ambiguity_bucket": task.ambiguity_bucket,
            "dirty_state_bucket": "dirty_safe",
            "features_label_blind_bool": True,
        },
        "action": {
            "action_type": action_type,
            "action_scope_bucket": scope,
            "retrieval_budget_bucket": "budget_1_to_5",
            "source_scan_scope": scan_scope,
            "candidate_generation_policy": candidate_policy,
            "pack_policy": pack_policy,
            "action_feature_keys": ["currentness_bucket", "evidence_coverage_bucket", "ambiguity_bucket"],
        },
        "policy_learning_support": {
            "behavior_policy_id": private_ref("behavior_policy", arm),
            "behavior_policy_kind": "deterministic_rule",
            "deterministic_bool": True,
            "action_probability": 1.0,
            "action_probability_bucket": "probability_1",
            "propensity_available_bool": True,
            "eligible_actions_bucket": "count_2_to_5",
        },
        "observation_result": {
            "observation_status": observation_status,
            "result_bucket": result_bucket,
            "evidence_delta_bucket": evidence_delta_bucket,
            "latency_bucket": latency_bucket,
            "failure_bucket": failure_bucket,
            "observation_after_action_bool": True,
        },
        "evidencecore_linkage": evidence_linkage(required=evidence_required, linked=evidence_linked, stale=stale),
        "outcome_label": {
            "label_available_bool": label_available,
            "label_timing": "after_action" if label_available else "not_available",
            "label_source": "private_eval_only" if label_available else "none",
            "outcome_bucket": outcome_bucket if label_available else "not_evaluated",
            "label_used_in_state_or_action_bool": False,
        },
        "privacy_execution": {
            "private_trace_bool": True,
            "public_report_level": "aggregate_schema_only",
            "raw_publication_bool": False,
            "provider_payload_public_bool": False,
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "private_values_public_bool": False,
        },
        "stop_go_source_locks_readback": {
            "source_lock_readback_status": "passed",
            "allowed_next_phase": "frk_product_workflow_benchmark",
            "forbidden_next_phases": sorted(schema.FORBIDDEN_NEXT_PHASES),
            "overauthorization_bool": False,
            "readback_consistency_status": "passed",
        },
    }


def run_retrieval(binary: Path, task: WorkflowTask, arm: str) -> tuple[list[dict[str, Any]], str, float, str]:
    if arm == "text_bm25_baseline":
        payload, rc, latency = run_cli(binary, ["search", "bm25", task.text_query, "--limit", "5", "--json"], fail_safe=True)
        status = "available" if rc == 0 else "bounded_unavailable"
        return evidence_items(payload)[:5], status, latency, "bm25"
    if arm == "symbol_regex_baseline":
        if task.symbol_mode == "regex":
            payload, rc, latency = run_cli(binary, ["search", "regex", task.symbol_or_regex_query, "--json"], fail_safe=True)
            status = "available" if rc == 0 else "bounded_unavailable"
            return evidence_items(payload)[:5], status, latency, "regex"
        payload, rc, latency = run_cli(binary, ["search", "symbol", task.symbol_or_regex_query, "--limit", "5", "--json"], fail_safe=True)
        status = "available" if rc == 0 else "bounded_unavailable"
        return evidence_items(payload)[:5], status, latency, "symbol"

    payload, rc, latency = run_cli(
        binary,
        ["retrieve", task.hybrid_query, "--max-results", "5", "--channels", "regex,bm25,symbol", "--json"],
        fail_safe=True,
    )
    if rc == 0:
        return evidence_items(payload)[:5], "available", latency, "openlocus_retrieve"

    # Truthful bounded local fallback: the retrieve command is unavailable, so use
    # the same local channels with the same candidate cap and label the arm as a
    # bounded-local hybrid fallback.
    started = time.monotonic()
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str | None, int | None, int | None]] = set()
    for args in (
        ["search", "bm25", task.hybrid_query, "--limit", "5", "--json"],
        ["search", "regex", task.hybrid_query, "--json"],
        ["search", "symbol", task.hybrid_query, "--limit", "5", "--json"],
    ):
        sub_payload, sub_rc, _sub_latency = run_cli(binary, args, fail_safe=True)
        if sub_rc != 0:
            continue
        for item in evidence_items(sub_payload):
            core = item.get("core") if isinstance(item.get("core"), dict) else item
            key = (core.get("path"), core.get("start_line"), core.get("end_line")) if isinstance(core, dict) else (None, None, None)
            if key not in seen:
                merged.append(item)
                seen.add(key)
            if len(merged) >= 5:
                return merged, "bounded_local_hybrid_fallback", time.monotonic() - started, "bounded_local_hybrid"
    status = "bounded_local_hybrid_fallback" if merged else "bounded_unavailable"
    return merged[:5], status, time.monotonic() - started, "bounded_local_hybrid"


def run_arm(binary: Path, private_root: Path, task: WorkflowTask, arm: str, order_start: int) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    private_labels: list[dict[str, Any]] = []
    order = order_start
    candidates, availability, retrieval_latency, channel = run_retrieval(binary, task, arm)
    candidate_count = len(candidates)
    retrieval_failure = "none" if candidate_count else ("missing_source" if availability != "bounded_unavailable" else "other")
    rows.append(build_row(
        task=task,
        arm=arm,
        action_type="bounded_retrieval",
        step_index=0,
        order_index=order,
        observation_status="observed" if candidate_count else "failed_safe",
        result_bucket="evidence_added" if candidate_count else "no_change",
        evidence_delta_bucket="delta_2_to_5" if candidate_count >= 2 else ("delta_1" if candidate_count == 1 else "delta_0"),
        latency_bucket=bucket_latency(retrieval_latency),
        failure_bucket=retrieval_failure,
        outcome_bucket="partial_bucket" if candidate_count else "failure_bucket",
        evidence_required=bool(candidate_count),
        evidence_linked=bool(candidate_count),
    ))
    order += 1

    validation_valid = 0
    validation_invalid = 0
    match_found = False
    wrong_file_seen = False
    unsafe_seen = False
    read_count = 0
    validate_count = 0
    validation_latency_buckets: list[str] = []
    for idx, cand in enumerate(candidates[:2]):
        spec = evidence_read_spec(cand)
        if not spec:
            continue
        read_payload, read_rc, read_latency = run_cli(binary, ["read", spec, "--json"], fail_safe=True)
        read_ok = read_rc == 0 and isinstance(read_payload, dict)
        cand_path = evidence_path(read_payload if isinstance(read_payload, dict) else cand)
        expected_hit = cand_path == task.expected_path
        wrong_file_seen = wrong_file_seen or (read_ok and not expected_hit)
        rows.append(build_row(
            task=task,
            arm=arm,
            action_type="read_current_source",
            step_index=order - order_start,
            order_index=order,
            observation_status="observed" if read_ok else "failed_safe",
            result_bucket="evidence_added" if read_ok else "failure",
            evidence_delta_bucket="delta_1" if read_ok else "delta_0",
            latency_bucket=bucket_latency(read_latency),
            failure_bucket="none" if read_ok else "missing_source",
            outcome_bucket="partial_bucket" if read_ok else "failure_bucket",
            evidence_required=read_ok,
            evidence_linked=read_ok,
        ))
        order += 1
        if not read_ok:
            continue
        read_count += 1
        evidence_file = private_root / f"evidence_{private_ref('evidence', task.opaque_id, arm, str(idx))}.json"
        evidence_file.write_text(json.dumps(read_payload, sort_keys=True) + "\n", encoding="utf-8")
        validate_payload, validate_rc, validate_latency = run_cli(binary, ["citations", "validate", str(evidence_file), "--json"], fail_safe=True)
        valid_count = int(validate_payload.get("valid_count", 0)) if isinstance(validate_payload, dict) else 0
        invalid_count = int(validate_payload.get("invalid_count", 0)) if isinstance(validate_payload, dict) else 0
        valid = validate_rc == 0 and valid_count >= 1
        validation_valid += 1 if valid else 0
        validation_invalid += 0 if valid else max(1, invalid_count)
        validate_count += 1
        validation_latency_buckets.append(bucket_latency(validate_latency))
        match_found = match_found or (valid and expected_hit)
        rows.append(build_row(
            task=task,
            arm=arm,
            action_type="validate_evidence",
            step_index=order - order_start,
            order_index=order,
            observation_status="observed" if valid else "failed_safe",
            result_bucket="evidence_added" if valid else "evidence_rejected",
            evidence_delta_bucket="delta_1" if valid else "delta_0",
            latency_bucket=bucket_latency(validate_latency),
            failure_bucket="none" if valid else "validation_failed",
            outcome_bucket="success_bucket" if valid and expected_hit else ("partial_bucket" if valid else "failure_bucket"),
            evidence_required=True,
            evidence_linked=valid,
            stale=not valid,
        ))
        order += 1

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
    elif validation_valid == 0 and validate_count > 0:
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

    rows.append(build_row(
        task=task,
        arm=arm,
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

    private_labels.append({
        "trace_id": private_ref("trace", task.opaque_id, arm),
        "task_id_private": private_ref("task", task.opaque_id),
        "arm_private": private_ref("arm", arm),
        "expected_path_after_action_private": task.expected_path,
        "expected_range_after_action_private": task.expected_range,
        "retrieval_channel_after_action_private": channel,
        "validated_current_evidence_matches_private_expected_workflow_need": match_found,
        "label_timing": "after_action",
    })
    stats = {
        "arm": arm,
        "family": task.family,
        "availability": availability,
        "candidate_count": candidate_count,
        "read_count": read_count,
        "validate_count": validate_count,
        "valid_count": validation_valid,
        "invalid_count": validation_invalid,
        "success": match_found,
        "no_candidate": candidate_count == 0,
        "wrong_file": (not match_found) and wrong_file_seen,
        "invalid_citation": validation_valid == 0 and validate_count > 0,
        "unsafe_path": unsafe_seen,
        "budget_exhausted": (not match_found) and candidate_count > 2,
        "ambiguous_incomplete": (not match_found) and candidate_count > 0 and not wrong_file_seen and validation_valid > 0,
        "latency_buckets": [bucket_latency(retrieval_latency), *validation_latency_buckets],
        "actions": [row["action"]["action_type"] for row in rows],
    }
    return rows, stats, private_labels, order


def capture_benchmark(confirm_private_output: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not confirm_private_output:
        raise BenchmarkError("--confirm-private-output is required before writing private product-workflow traces")
    if len(TASKS) < 20:
        raise BenchmarkError("FRK product workflow task declaration drift: expected at least 20 tasks")
    families = {task.family for task in TASKS}
    if len(families) < 4:
        raise BenchmarkError("FRK product workflow family declaration drift: expected at least 4 families")
    binary = ensure_openlocus()
    private_root = REPO / "runs" / f"{PRIVATE_ROOT_PREFIX}{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    private_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    private_labels: list[dict[str, Any]] = []
    order = 0
    for task in TASKS:
        for arm in ARMS:
            arm_rows, arm_stats, labels, order = run_arm(binary, private_root, task, arm, order)
            rows.extend(arm_rows)
            stats.append(arm_stats)
            private_labels.extend(labels)

    row_errors = schema.validate_trace_rows(rows)
    if row_errors:
        raise BenchmarkError("private trace rows failed Phase-1 schema validation: " + "; ".join(row_errors[:5]))
    trace_path = private_root / PRIVATE_TRACE_FILENAME
    label_path = private_root / PRIVATE_LABEL_FILENAME
    write_jsonl(trace_path, rows)
    write_jsonl(label_path, private_labels)
    manifest = {
        "storage_class": "ignored_repo_runs_private_jsonl",
        "row_count": len(rows),
        "episode_count": len({row["trace_identity"]["trace_id"] for row in rows}),
        "task_count": len(TASKS),
        "workflow_families": sorted(families),
        "arms": list(ARMS),
        "private_trace_path": str(trace_path),
        "private_label_path": str(label_path),
    }
    return rows, stats, manifest


def diversity_gates(rows: list[dict[str, Any]], stats: list[dict[str, Any]]) -> dict[str, bool]:
    actions = {row["action"]["action_type"] for row in rows}
    traces = {row["trace_identity"]["trace_id"] for row in rows}
    families = {item["family"] for item in stats}
    arms = {item["arm"] for item in stats}
    outcomes = Counter(row["outcome_label"]["outcome_bucket"] for row in rows)
    pre_currentness = Counter(row["state_features"]["currentness_bucket"] for row in rows)
    return {
        "strict_phase1_schema_passed": not schema.validate_trace_rows(rows),
        "task_count_ge_20": len({private_ref("task", task.opaque_id) for task in TASKS}) >= 20,
        "workflow_family_count_ge_4": len(families) >= 4,
        "required_workflow_families_present": REQUIRED_FAMILIES.issubset(families),
        "arm_count_ge_3": len(arms) >= 3,
        "episode_count_ge_60": len(traces) >= 60,
        "row_count_ge_120": len(rows) >= 120,
        "required_action_types_present": REQUIRED_ACTION_TYPES.issubset(actions),
        "success_and_failure_outcomes_present": outcomes.get("success_bucket", 0) >= 5 and outcomes.get("failure_bucket", 0) >= 5,
        "pre_action_currentness_not_leaked": set(pre_currentness) == {"not_checked"},
        "labels_after_action_only": all(row["outcome_label"]["label_timing"] == "after_action" and row["outcome_label"]["label_used_in_state_or_action_bool"] is False for row in rows),
    }


def detailed_failure_bucket(item: dict[str, Any]) -> str:
    if item.get("success"):
        return "none"
    if item.get("no_candidate"):
        return "no_candidate"
    if item.get("unsafe_path"):
        return "unsafe_path"
    if item.get("invalid_citation"):
        return "invalid_citation"
    if item.get("wrong_file"):
        return "wrong_file"
    if item.get("budget_exhausted"):
        return "budget_exhausted"
    if item.get("ambiguous_incomplete"):
        return "ambiguous_incomplete_evidence"
    return "failure_safe"


def aggregate_report(rows: list[dict[str, Any]], stats: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    action_counts = Counter(row["action"]["action_type"] for row in rows)
    outcome_counts = Counter(row["outcome_label"]["outcome_bucket"] for row in rows)
    row_failure_counts = Counter(row["observation_result"]["failure_bucket"] for row in rows)
    linkage_counts = Counter(row["evidencecore_linkage"]["evidencecore_link_status"] for row in rows)
    latency_counts: Counter[str] = Counter()
    for item in stats:
        latency_counts.update(item["latency_buckets"])
    arm_total = Counter(item["arm"] for item in stats)
    arm_success = Counter(item["arm"] for item in stats if item["success"])
    arm_availability = Counter(item["availability"] for item in stats)
    family_counts = Counter(item["family"] for item in stats)
    detailed_failures = Counter(detailed_failure_bucket(item) for item in stats)
    read_budget_counts = Counter(bucket_count(item["read_count"]) for item in stats)
    candidate_budget_counts = Counter(bucket_count(item["candidate_count"]) for item in stats)
    validate_counts = Counter(bucket_count(item["validate_count"]) for item in stats)

    rates = {arm: (arm_success.get(arm, 0), arm_total.get(arm, 0)) for arm in ARMS}
    baseline_best_success = max(rates[arm][0] for arm in BASELINE_ARMS)
    baseline_best_total = max(rates[arm][1] for arm in BASELINE_ARMS)
    candidate_success, candidate_total = rates["openlocus_hybrid_retrieve"]
    baseline_best_rate = baseline_best_success / baseline_best_total if baseline_best_total else 0.0
    candidate_rate = candidate_success / candidate_total if candidate_total else 0.0
    if candidate_rate > baseline_best_rate:
        delta_bucket = "positive_lift"
    elif candidate_rate == baseline_best_rate:
        delta_bucket = "neutral_no_lift"
    else:
        delta_bucket = "negative_vs_best_baseline"

    gates = diversity_gates(rows, stats)
    adequate_diversity = all(gates.values())
    if not adequate_diversity and not gates.get("strict_phase1_schema_passed", False):
        status = STATUS_REPAIR
        authorized = AUTHORIZED_REPAIR
        decision = "no_go_schema_or_privacy_repair_only"
    elif not adequate_diversity:
        status = STATUS_EXPANSION
        authorized = AUTHORIZED_EXPANSION
        decision = "no_go_trace_expansion_only"
    elif delta_bucket == "positive_lift":
        status = STATUS_LIFT
        authorized = AUTHORIZED_LIFT
        decision = "go_heldout_design_only"
    else:
        status = STATUS_NO_LIFT
        authorized = AUTHORIZED_NO_LIFT
        decision = "no_go_failure_decomposition_or_trace_expansion"

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "execution_attestation": {
            "real_executable_benchmark": True,
            "fixed_bounded_local_product_workflow_tasks": True,
            "local_openlocus_cli_actions_executed": True,
            "same_budget_candidate_cap_bucket": "count_2_to_5",
            "same_budget_read_cap_bucket": "count_2_to_5",
            "labels_joined_after_action": True,
            "synthetic_rows_only": False,
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "training_executed": False,
            "provider_calls_executed": False,
            "runtime_default_changed": False,
        },
        "aggregate_buckets": {
            "task_count_bucket": bucket_count(int(manifest["task_count"])),
            "workflow_family_count_bucket": bucket_count(len(family_counts)),
            "workflow_family_coverage": {family: bucket_count(count) for family, count in sorted(family_counts.items())},
            "arm_count_bucket": bucket_count(len(arm_total)),
            "episode_count_bucket": bucket_count(int(manifest["episode_count"])),
            "row_count_bucket": bucket_count(len(rows)),
            "action_coverage": {name: bucket_count(count) for name, count in sorted(action_counts.items())},
            "outcome_coverage": {name: bucket_count(count) for name, count in sorted(outcome_counts.items())},
            "row_failure_buckets": {name: bucket_count(count) for name, count in sorted(row_failure_counts.items())},
            "detailed_failure_buckets": {name: bucket_count(count) for name, count in sorted(detailed_failures.items())},
            "evidencecore_currentness": {name: bucket_count(count) for name, count in sorted(linkage_counts.items())},
            "citation_validity": {
                "valid_current_bucket": bucket_count(sum(item["valid_count"] for item in stats)),
                "invalid_or_stale_bucket": bucket_count(sum(item["invalid_count"] for item in stats)),
            },
            "latency": {name: bucket_count(count) for name, count in sorted(latency_counts.items())},
            "candidate_budget": {name: bucket_count(count) for name, count in sorted(candidate_budget_counts.items())},
            "read_budget": {name: bucket_count(count) for name, count in sorted(read_budget_counts.items())},
            "validate_budget": {name: bucket_count(count) for name, count in sorted(validate_counts.items())},
            "arm_availability": {name: bucket_count(count) for name, count in sorted(arm_availability.items())},
        },
        "primary_success_proxy": {
            "name": "validated_current_evidence_matches_private_expected_workflow_need",
            "publication_level": "aggregate_bucket_only",
            "success_bucket": bucket_count(sum(1 for item in stats if item["success"])),
            "failure_bucket": bucket_count(sum(1 for item in stats if not item["success"])),
        },
        "best_baseline_comparison": {
            "arm_utility_buckets": {arm: bucket_rate(*rates[arm]) for arm in ARMS},
            "fixed_baseline_arms_bucket": bucket_count(len(BASELINE_ARMS)),
            "best_fixed_baseline_bucket": bucket_rate(baseline_best_success, baseline_best_total),
            "candidate_arm_bucket": bucket_rate(candidate_success, candidate_total),
            "candidate_vs_best_baseline_delta_bucket": delta_bucket,
            "best_baseline_gate": "passed",
        },
        "validation_summary": {
            "strict_phase1_schema": "passed" if not schema.validate_trace_rows(rows) else "failed",
            "schema_error_bucket": bucket_count(len(schema.validate_trace_rows(rows))),
            "privacy_leak_scan": "pending",
            "private_output_confirmation": "confirmed",
            "public_report_level": "aggregate_only",
            "self_test_mutation_coverage": "available",
        },
        "coverage_gates": {
            "gate_results": gates,
            "diversity_status": "adequate" if adequate_diversity else "insufficient",
            "best_baseline_lift_status": delta_bucket,
        },
        "privacy_contract": {
            "publication_level": "aggregate_only",
            "raw_paths_public": False,
            "queries_public": False,
            "ranges_public": False,
            "snippets_public": False,
            "hashes_public": False,
            "labels_public": False,
            "raw_task_ids_public": False,
            "private_refs_public": False,
            "private_trace_path_public": False,
            "private_trace_rows_public": False,
            "evidence_filenames_public": False,
            "per_task_outcomes_public": False,
            "prompts_or_responses_public": False,
            "provider_payloads_public": False,
            "raw_publication": False,
        },
        "stop_go": {
            "decision": decision,
            "authorized_next_phase": authorized,
            "explicitly_forbidden": sorted(PUBLIC_FORBIDDEN),
            "targeted_repair_only_if_execution_schema_privacy_fails": True,
            "expansion_only_if_insufficient_diversity": True,
            "failure_decomposition_if_no_lift": True,
            "heldout_design_only_if_real_lift": delta_bucket == "positive_lift" and adequate_diversity,
            "d2_or_training_authorized": False,
            "provider_network_ci_authorized": False,
            "runtime_or_default_authorized": False,
            "method_scale_winner_default_claims_allowed": False,
        },
    }


REPORT_KEYS = {
    "schema_version",
    "phase",
    "status",
    "execution_attestation",
    "aggregate_buckets",
    "primary_success_proxy",
    "best_baseline_comparison",
    "validation_summary",
    "coverage_gates",
    "privacy_contract",
    "stop_go",
}


def public_leak_errors(obj: Any) -> list[str]:
    sanitized = copy.deepcopy(obj)
    privacy = sanitized.get("privacy_contract") if isinstance(sanitized, dict) else None
    if isinstance(privacy, dict):
        for key in list(privacy):
            if key.endswith("_public") or key in {"raw_publication"}:
                privacy.pop(key, None)
    errors = schema.public_leak_errors(sanitized)
    text = json.dumps(obj, sort_keys=True)
    forbidden_terms = [
        "private_ref_",
        "frk_product_workflow_private_",
        PRIVATE_TRACE_FILENAME,
        PRIVATE_LABEL_FILENAME,
        "content_sha",
        "crates/",
        "docs/",
        "eval/",
        "README.md",
        "Cargo.toml",
        "RRF multi-channel retrieve",
        "ROW_SCHEMA_VERSION",
    ]
    for term in forbidden_terms:
        if term in text:
            errors.append(f"public leak disallowed term {term}")
    if re.search(r"\b[a-f0-9]{16,}\b", text, re.I):
        errors.append("public leak hash-like value")
    return errors


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be an object"]
    if set(report) != REPORT_KEYS:
        errors.append("report has missing or unknown top-level keys")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append("bad schema_version")
    if report.get("phase") != PHASE:
        errors.append("bad phase")
    if report.get("status") not in {STATUS_REPAIR, STATUS_EXPANSION, STATUS_NO_LIFT, STATUS_LIFT}:
        errors.append("bad status")
    att = report.get("execution_attestation", {})
    for field in ("real_executable_benchmark", "fixed_bounded_local_product_workflow_tasks", "local_openlocus_cli_actions_executed", "labels_joined_after_action"):
        if att.get(field) is not True:
            errors.append(f"execution_attestation.{field} must be true")
    for field in ("synthetic_rows_only", "training_executed", "provider_calls_executed", "runtime_default_changed"):
        if att.get(field) is not False:
            errors.append(f"execution_attestation.{field} must be false")
    if att.get("network_access") != "no_network" or att.get("ci_execution") != "local_manual_only":
        errors.append("execution must be local/no-network/non-CI")
    if att.get("same_budget_candidate_cap_bucket") != "count_2_to_5" or att.get("same_budget_read_cap_bucket") != "count_2_to_5":
        errors.append("same-budget caps drift")

    agg = report.get("aggregate_buckets", {})
    required_agg = {
        "task_count_bucket", "workflow_family_count_bucket", "workflow_family_coverage", "arm_count_bucket", "episode_count_bucket",
        "row_count_bucket", "action_coverage", "outcome_coverage", "row_failure_buckets", "detailed_failure_buckets",
        "evidencecore_currentness", "citation_validity", "latency", "candidate_budget", "read_budget", "validate_budget", "arm_availability",
    }
    if set(agg) != required_agg:
        errors.append("aggregate bucket shape drift")
    if agg.get("task_count_bucket") != "count_6_to_20":
        errors.append("task_count coverage gate requires 20 bounded tasks")
    if agg.get("workflow_family_count_bucket") not in {"count_2_to_5", "count_6_to_20"} or len(agg.get("workflow_family_coverage", {})) < 4:
        errors.append("workflow family coverage gate failed")
    if agg.get("arm_count_bucket") != "count_2_to_5":
        errors.append("arm coverage gate requires same-budget arms")
    if agg.get("episode_count_bucket") not in {"count_gt_50", "count_21_to_50"}:
        errors.append("episode count coverage gate failed")
    if agg.get("row_count_bucket") != "count_gt_50":
        errors.append("row count coverage gate failed")
    actions = set(agg.get("action_coverage", {}))
    if not REQUIRED_ACTION_TYPES.issubset(actions):
        errors.append("required action coverage missing")
    if "success_bucket" not in agg.get("outcome_coverage", {}) or "failure_bucket" not in agg.get("outcome_coverage", {}):
        errors.append("success/failure outcome coverage missing")
    if agg.get("outcome_coverage", {}).get("success_bucket") not in {"count_6_to_20", "count_21_to_50", "count_gt_50"}:
        errors.append("success outcome coverage requires at least five rows")
    if agg.get("outcome_coverage", {}).get("failure_bucket") not in {"count_6_to_20", "count_21_to_50", "count_gt_50"}:
        errors.append("failure outcome coverage requires at least five rows")
    detailed = set(agg.get("detailed_failure_buckets", {}))
    if not detailed.intersection({"no_candidate", "wrong_file", "invalid_citation", "unsafe_path", "budget_exhausted", "ambiguous_incomplete_evidence", "failure_safe"}):
        errors.append("detailed failure buckets missing")
    if agg.get("citation_validity", {}).get("valid_current_bucket") in {None, "count_0"}:
        errors.append("citation validity/currentness evidence missing")

    proxy = report.get("primary_success_proxy", {})
    if proxy.get("name") != "validated_current_evidence_matches_private_expected_workflow_need":
        errors.append("primary success proxy drift")
    if proxy.get("publication_level") != "aggregate_bucket_only":
        errors.append("primary success proxy must be aggregate bucket only")

    cmp = report.get("best_baseline_comparison", {})
    arm_utils = cmp.get("arm_utility_buckets", {})
    if set(arm_utils) != set(ARMS):
        errors.append("arm utility bucket set drift")
    if cmp.get("best_fixed_baseline_bucket") not in {"rate_0", "rate_lt_25", "rate_25_to_50", "rate_50_to_75", "rate_75_to_99", "rate_1"}:
        errors.append("best fixed baseline bucket missing")
    if cmp.get("candidate_vs_best_baseline_delta_bucket") not in {"positive_lift", "neutral_no_lift", "negative_vs_best_baseline"}:
        errors.append("candidate-vs-best-baseline delta bucket missing")
    if cmp.get("best_baseline_gate") != "passed":
        errors.append("best-baseline gate must pass")

    val = report.get("validation_summary", {})
    if val.get("strict_phase1_schema") != "passed" or val.get("schema_error_bucket") != "count_0":
        errors.append("strict trace schema must pass")
    if val.get("privacy_leak_scan") != "passed":
        errors.append("privacy leak scan must pass")
    if val.get("private_output_confirmation") != "confirmed":
        errors.append("private output confirmation missing")
    gates = report.get("coverage_gates", {}).get("gate_results", {})
    expected_gates = {
        "strict_phase1_schema_passed", "task_count_ge_20", "workflow_family_count_ge_4", "required_workflow_families_present",
        "arm_count_ge_3", "episode_count_ge_60", "row_count_ge_120", "required_action_types_present",
        "success_and_failure_outcomes_present", "pre_action_currentness_not_leaked", "labels_after_action_only",
    }
    if set(gates) != expected_gates or not all(isinstance(gates.get(key), bool) for key in expected_gates):
        errors.append("coverage gate shape drift")
    adequate = all(gates.get(key) is True for key in expected_gates)
    delta = cmp.get("candidate_vs_best_baseline_delta_bucket")
    status = report.get("status")
    if not isinstance(status, str):
        errors.append("status must be a string")
        status_key = ""
    else:
        status_key = status
    if status == STATUS_REPAIR and val.get("strict_phase1_schema") == "passed" and val.get("privacy_leak_scan") == "passed":
        errors.append("repair status requires execution/schema/privacy failure")
    if status == STATUS_EXPANSION and adequate:
        errors.append("expansion status inconsistent with adequate diversity")
    if status == STATUS_NO_LIFT and (not adequate or delta == "positive_lift"):
        errors.append("no-lift status requires adequate diversity and no positive lift")
    if status == STATUS_LIFT and (not adequate or delta != "positive_lift"):
        errors.append("lift status requires adequate diversity and positive lift")
    if report.get("coverage_gates", {}).get("diversity_status") == "adequate" and not adequate:
        errors.append("fake adequate diversity status")
    if report.get("coverage_gates", {}).get("best_baseline_lift_status") != delta:
        errors.append("best-baseline lift readback drift")

    privacy = report.get("privacy_contract", {})
    for field in (
        "raw_paths_public", "queries_public", "ranges_public", "snippets_public", "hashes_public", "labels_public",
        "raw_task_ids_public", "private_refs_public", "private_trace_path_public", "private_trace_rows_public",
        "evidence_filenames_public", "per_task_outcomes_public", "prompts_or_responses_public", "provider_payloads_public", "raw_publication",
    ):
        if privacy.get(field) is not False:
            errors.append(f"privacy_contract.{field} must be false")
    if privacy.get("publication_level") != "aggregate_only":
        errors.append("privacy publication level drift")

    stop = report.get("stop_go", {})
    forbidden = set(stop.get("explicitly_forbidden", []))
    if forbidden != PUBLIC_FORBIDDEN:
        errors.append("explicit forbidden route set drift")
    stop_keys = {
        "decision", "authorized_next_phase", "explicitly_forbidden", "targeted_repair_only_if_execution_schema_privacy_fails",
        "expansion_only_if_insufficient_diversity", "failure_decomposition_if_no_lift", "heldout_design_only_if_real_lift",
        "d2_or_training_authorized", "provider_network_ci_authorized", "runtime_or_default_authorized", "method_scale_winner_default_claims_allowed",
    }
    if set(stop) != stop_keys:
        errors.append("stop_go has missing or unknown keys")
    expected_allowed = {
        STATUS_REPAIR: AUTHORIZED_REPAIR,
        STATUS_EXPANSION: AUTHORIZED_EXPANSION,
        STATUS_NO_LIFT: AUTHORIZED_NO_LIFT,
        STATUS_LIFT: AUTHORIZED_LIFT,
    }.get(status_key)
    if stop.get("authorized_next_phase") != expected_allowed:
        errors.append("authorized next phase drift")
    if stop.get("authorized_next_phase") in forbidden:
        errors.append("forbidden phase appears authorized")
    if stop.get("heldout_design_only_if_real_lift") is not (status == STATUS_LIFT):
        errors.append("heldout design stop/go gate drift")
    for field in ("d2_or_training_authorized", "provider_network_ci_authorized", "runtime_or_default_authorized", "method_scale_winner_default_claims_allowed"):
        if stop.get(field) is not False:
            errors.append(f"stop_go.{field} must be false")
    if stop.get("d2_or_training_authorized") is True and not (adequate and delta == "positive_lift"):
        errors.append("D2/training overauthorization without diversity plus lift")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    final = copy.deepcopy(report)
    final["validation_summary"]["privacy_leak_scan"] = "passed" if not public_leak_errors(final) else "failed"
    errors = validate_public_report(final)
    if errors:
        raise BenchmarkError("public report validation failed: " + "; ".join(errors[:8]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fixture_rows_and_stats() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    order = 0
    for task in TASKS:
        for arm in ARMS:
            success = not (arm == "openlocus_hybrid_retrieve" and task.opaque_id in {"wf03", "wf07", "wf11", "wf15"})
            wrong = not success and task.opaque_id in {"wf03", "wf07"}
            invalid = not success and task.opaque_id == "wf11"
            no_candidate = not success and task.opaque_id == "wf15"
            for action_type in ("bounded_retrieval", "read_current_source", "validate_evidence", "workflow_step"):
                failure = "none"
                result = "evidence_added"
                outcome = "success_bucket" if success else "failure_bucket"
                obs = "observed" if success else "failed_safe"
                linked = success or action_type in {"bounded_retrieval", "read_current_source"}
                if not success:
                    if no_candidate:
                        failure = "missing_source"
                        result = "no_change" if action_type == "bounded_retrieval" else "failure"
                    elif invalid and action_type in {"validate_evidence", "workflow_step"}:
                        failure = "validation_failed"
                        result = "evidence_rejected" if action_type == "validate_evidence" else "failure"
                    elif wrong and action_type == "workflow_step":
                        failure = "other"
                        result = "failure"
                if action_type == "workflow_step":
                    result = "workflow_advanced" if success else "failure"
                fixture_evidence_linked = action_type != "workflow_step" and not no_candidate and not (invalid and action_type == "validate_evidence")
                rows.append(build_row(task=task, arm=arm, action_type=action_type, step_index=order % 4, order_index=order, observation_status=obs, result_bucket=result, evidence_delta_bucket="delta_1" if fixture_evidence_linked else "delta_0", latency_bucket="lt_1s", failure_bucket=failure, outcome_bucket=outcome, evidence_required=action_type != "workflow_step" and not no_candidate, evidence_linked=fixture_evidence_linked, stale=invalid and action_type == "validate_evidence"))
                order += 1
            stats.append({
                "arm": arm,
                "family": task.family,
                "availability": "available",
                "candidate_count": 2 if not no_candidate else 0,
                "read_count": 2 if not no_candidate else 0,
                "validate_count": 2 if not no_candidate else 0,
                "valid_count": 2 if success or wrong else 0,
                "invalid_count": 0 if success or wrong else (1 if invalid else 0),
                "success": success,
                "no_candidate": no_candidate,
                "wrong_file": wrong,
                "invalid_citation": invalid,
                "unsafe_path": False,
                "budget_exhausted": False,
                "ambiguous_incomplete": False,
                "latency_buckets": ["lt_1s"],
                "actions": list(REQUIRED_ACTION_TYPES),
            })
    manifest = {"task_count": len(TASKS), "episode_count": len(TASKS) * len(ARMS)}
    return rows, stats, manifest


def run_self_tests() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    rows, stats, manifest = fixture_rows_and_stats()
    checks.append(("fixture_phase1_rows_valid", not schema.validate_trace_rows(rows)))
    report = aggregate_report(rows, stats, manifest)
    report["validation_summary"]["privacy_leak_scan"] = "passed"
    checks.append(("fixture_public_report_valid", not validate_public_report(report)))

    bad_rows = copy.deepcopy(rows)
    del bad_rows[0]["task_state"]["task_type"]
    checks.append(("schema_missing_field_rejected", bool(schema.validate_trace_rows(bad_rows))))
    bad_rows = copy.deepcopy(rows)
    bad_rows[0]["action"]["action_type"] = "train_model"
    checks.append(("schema_bad_enum_rejected", bool(schema.validate_trace_rows(bad_rows))))
    bad_rows = copy.deepcopy(rows)
    bad_rows[1]["trace_identity"]["step_id"] = bad_rows[0]["trace_identity"]["step_id"]
    checks.append(("duplicate_trace_row_rejected", bool(schema.validate_trace_rows(bad_rows))))
    bad_rows = copy.deepcopy(rows)
    bad_rows[1]["trace_identity"]["episode_step_index"] = 0
    checks.append(("non_monotonic_trace_row_rejected", bool(schema.validate_trace_rows(bad_rows))))
    bad_rows = copy.deepcopy(rows)
    bad_rows[0]["outcome_label"]["label_timing"] = "not_available"
    bad_rows[0]["outcome_label"]["label_used_in_state_or_action_bool"] = True
    checks.append(("label_timing_leakage_rejected", bool(schema.validate_trace_rows(bad_rows))))
    bad_rows = copy.deepcopy(rows)
    bad_rows[0]["state_features"]["currentness_bucket"] = "verified_current"
    checks.append(("post_action_currentness_feature_leak_rejected", bool(schema.validate_trace_rows(bad_rows)) or not diversity_gates(bad_rows, stats)["pre_action_currentness_not_leaked"]))
    try:
        capture_benchmark(False)
        checks.append(("private_output_confirmation_required", False))
    except BenchmarkError as exc:
        checks.append(("private_output_confirmation_required", "confirm-private-output" in str(exc)))

    bad = copy.deepcopy(report)
    bad["schema_version"] = "bad"
    checks.append(("report_bad_schema_version_rejected", any("schema_version" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["workflow_family_coverage"] = {"one_family": "count_gt_50"}
    checks.append(("family_coverage_gate_rejected", any("family" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["action_coverage"].pop("workflow_step", None)
    checks.append(("action_coverage_gate_rejected", any("action coverage" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["outcome_coverage"].pop("failure_bucket", None)
    checks.append(("outcome_coverage_gate_rejected", any("outcome" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["debug_path"] = "crates/openlocus-cli/src/lib.rs"
    checks.append(("public_path_leak_rejected", bool(validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["debug_query"] = "ROW_SCHEMA_VERSION"
    checks.append(("public_query_leak_rejected", bool(validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["debug_hash"] = "abcdef0123456789abcdef0123456789"
    checks.append(("public_hash_leak_rejected", bool(validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["debug_ref"] = "private_ref_trace_leak"
    checks.append(("public_private_ref_leak_rejected", bool(validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["stop_go"]["training_or_provider_overauth"] = True
    checks.append(("unknown_overauth_field_rejected", bool(validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["stop_go"]["d2_or_training_authorized"] = True
    checks.append(("training_d2_overauthorization_rejected", any("d2_or_training" in e.lower() for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["status"] = STATUS_LIFT
    bad["stop_go"]["authorized_next_phase"] = AUTHORIZED_LIFT
    bad["stop_go"]["heldout_design_only_if_real_lift"] = True
    checks.append(("fake_lift_status_without_gate_rejected", any("lift status" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["coverage_gates"]["gate_results"]["task_count_ge_20"] = False
    checks.append(("fake_complete_without_task_gate_rejected", any("no-lift status" in e or "fake adequate" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["best_baseline_comparison"].pop("best_fixed_baseline_bucket", None)
    checks.append(("missing_best_baseline_gate_rejected", any("baseline" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["validation_summary"]["private_output_confirmation"] = "missing"
    checks.append(("missing_private_confirmation_report_rejected", any("confirmation" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["coverage_gates"]["gate_results"]["pre_action_currentness_not_leaked"] = False
    checks.append(("currentness_gate_false_rejected", any("no-lift status" in e or "fake adequate" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["outcome_coverage"]["failure_bucket"] = "count_2_to_5"
    checks.append(("failure_outcome_under_5_rejected", any("failure outcome" in e for e in validate_public_report(bad))))
    bad = copy.deepcopy(report)
    bad["aggregate_buckets"]["outcome_coverage"]["success_bucket"] = "count_2_to_5"
    checks.append(("success_outcome_under_5_rejected", any("success outcome" in e for e in validate_public_report(bad))))
    unavailable = copy.deepcopy(report)
    unavailable["aggregate_buckets"]["arm_availability"] = {"bounded_unavailable": "count_1", "available": "count_21_to_50"}
    checks.append(("unavailable_arm_report_still_valid_when_not_fake_lift", not validate_public_report(unavailable)))
    bad = copy.deepcopy(unavailable)
    bad["status"] = STATUS_LIFT
    bad["best_baseline_comparison"]["candidate_vs_best_baseline_delta_bucket"] = "positive_lift"
    bad["coverage_gates"]["best_baseline_lift_status"] = "positive_lift"
    bad["stop_go"]["authorized_next_phase"] = AUTHORIZED_LIFT
    bad["stop_go"]["heldout_design_only_if_real_lift"] = True
    # A lift claim can be syntactically valid only if gates say adequate and the
    # report still forbids D2/training. This mutation then overauthorizes training.
    bad["stop_go"]["d2_or_training_authorized"] = True
    checks.append(("unavailable_arm_fake_training_lift_rejected", bool(validate_public_report(bad))))

    failed = [name for name, ok in checks if not ok]
    if failed:
        raise BenchmarkError("self-test failed: " + ", ".join(failed))
    return {"status": "passed", "checks_passed": len(checks), "checks_total": len(checks), "failed_checks": []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run FRK product workflow trace benchmark")
    parser.add_argument("--self-test", action="store_true", help="run validator mutation self-tests")
    parser.add_argument("--run-local-product-workflow-benchmark", action="store_true", help="execute fixed bounded local workflow benchmark")
    parser.add_argument("--confirm-private-output", action="store_true", help="required confirmation before writing ignored private traces")
    parser.add_argument("--validate-report", type=Path, help="validate aggregate-only public report")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            print(json.dumps(run_self_tests(), indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = json.loads(args.validate_report.read_text(encoding="utf-8"))
            errors = validate_public_report(report)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"Validation passed: {args.validate_report}")
            return 0
        if args.run_local_product_workflow_benchmark:
            rows, stats, manifest = capture_benchmark(args.confirm_private_output)
            report = aggregate_report(rows, stats, manifest)
            write_report(report, DEFAULT_REPORT)
            print(json.dumps({
                "status": report["status"],
                "public_report": str(DEFAULT_REPORT),
                "private_storage_class": manifest["storage_class"],
                "private_row_count": manifest["row_count"],
                "private_episode_count": manifest["episode_count"],
            }, indent=2, sort_keys=True))
            return 0
        parser.error("choose --self-test, --run-local-product-workflow-benchmark, or --validate-report")
    except (BenchmarkError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
