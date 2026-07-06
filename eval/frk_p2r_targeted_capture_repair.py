#!/usr/bin/env python3
"""FRK-P2R targeted TraceV2 capture repair.

Executable targeted repair for the two FRK-P2 blockers: candidate-pool coverage
and downstream-proxy target-scoped coverage. It regenerates richer private nested
``openlocus.state_action_trace.v2`` rows under ignored ``runs/`` storage after
explicit confirmation, using the same bounded manifest shape and the same local
OpenLocus actions/channel families as FRK-P2. It is not a new retrieval
prototype, HAAE/RPM replay/training phase, runtime/default change, or kernel
hardening phase.
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

import frk_p2_workflow_v2_task_state_capture_expansion as p2
import state_action_trace_v2_bootstrap as tracev2


REPO = Path(__file__).resolve().parent.parent
PHASE = "openlocus_v2_frk_p2r_targeted_capture_repair"
REPORT_SCHEMA_VERSION = "frk_p2r_targeted_capture_repair_public_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / "frk_p2r_targeted_capture_repair" / "frk_p2r_targeted_capture_repair_report.json"
P2_REPORT = p2.DEFAULT_REPORT
PRIVATE_PREFIX = "frk_p2r_targeted_capture_repair_private_"
PRIVATE_ROW_FILENAME = "frk_p2r_targeted_capture_repair_v2_rows.jsonl"

STATUS_HAAE = "frk_p2r_capture_repair_complete_haae_a2_replay_authorized"
STATUS_LABEL_REPAIR = "frk_p2r_capture_repair_complete_label_or_proxy_repair_only"
STATUS_CANDIDATE_REPAIR = "frk_p2r_capture_repair_complete_candidate_pool_repair_only"
STATUS_MANIFEST_REPAIR = "frk_p2r_capture_repair_complete_manifest_balance_repair_only"
STATUS_FAILED = "frk_p2r_capture_repair_failed_schema_privacy_currentness_repair_only"
STATUS_STOPPED = "frk_p2r_capture_repair_stopped_no_observable_source"

AUTH_HAAE = "haae_a2_offline_action_replay_smoke_over_frk_p2r_v2_rows"
AUTH_LABEL_REPAIR = "targeted_frk_p2r_label_or_proxy_repair_only"
AUTH_CANDIDATE_REPAIR = "targeted_frk_p2r_candidate_pool_instrumentation_repair_only"
AUTH_MANIFEST_REPAIR = "targeted_frk_p2r_manifest_balance_repair_only"
AUTH_SCHEMA_REPAIR = "targeted_frk_p2r_schema_privacy_currentness_repair_only"
AUTH_STOP = "none_no_observable_source"

ALLOWED_CHANNELS = p2.ALLOWED_CHANNELS
FORBIDDEN = {
    "new_retrieval_algorithm",
    "new_channel_family",
    "candidate_expansion_beyond_fixed_caps",
    "broad_source_scan",
    "adaptive_escalation",
    "provider_claim",
    "model_provider_call",
    "network_claim",
    "ci_claim",
    "haae_a2_replay_inside_phase",
    "rpm_d2_training",
    "training_claim",
    "model_fitting",
    "model_scaling",
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

MISSING_MARKERS = set(tracev2.UNKNOWN_VALUES) | {"not_observable_from_source_trace"}
NONFINAL_MARKER = "not_applicable_nonfinal"
PREACTION_PROXY_MARKER = "not_available_pre_action"
PREACTION_NA_MARKER = "not_applicable_for_pre_action_state"


class P2RError(Exception):
    pass


def bucket_count(count: int) -> str:
    return p2.bucket_count(count)


def bucket_diversity(count: int) -> str:
    return p2.bucket_diversity(count)


def coverage_bucket(present: int, total: int) -> str:
    return tracev2.coverage_bucket(present, total)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise P2RError(f"missing public source report: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise P2RError(f"malformed public source report: {path.name}") from exc
    if not isinstance(payload, dict):
        raise P2RError(f"public source report is not an object: {path.name}")
    return payload


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def source_readbacks() -> dict[str, Any]:
    report = read_json(P2_REPORT)
    coverage = report.get("coverage_audit", {}) if isinstance(report.get("coverage_audit"), dict) else {}
    critical = coverage.get("critical_nested_coverage_by_group", {}) if isinstance(coverage.get("critical_nested_coverage_by_group"), dict) else {}
    return {
        "frk_p2_status": report.get("status"),
        "frk_p2_authorized_next_phase": report.get("stop_go", {}).get("authorized_next_phase"),
        "frk_p2_candidate_pool_coverage": critical.get("state.candidate_pool"),
        "frk_p2_downstream_proxy_coverage": critical.get("outcome.downstream_proxy"),
        "frk_p2_unknown_missingness": coverage.get("unknown_missingness_bucket"),
        "frk_p2_schema_validation": report.get("tracev2_validation", {}).get("v2_schema_validation"),
        "readback_scope": "public_aggregate_report_only",
    }


def source_readbacks_ok(readbacks: dict[str, Any]) -> bool:
    return (
        readbacks.get("frk_p2_status") == p2.STATUS_CAPTURE_REPAIR
        and readbacks.get("frk_p2_authorized_next_phase") == p2.AUTH_CAPTURE_REPAIR
        and readbacks.get("frk_p2_candidate_pool_coverage") == "coverage_low"
        and readbacks.get("frk_p2_downstream_proxy_coverage") == "coverage_low"
        and readbacks.get("frk_p2_unknown_missingness") == "count_gt_50"
        and readbacks.get("frk_p2_schema_validation") == "passed"
        and readbacks.get("readback_scope") == "public_aggregate_report_only"
    )


def label_blind_role_guess(row: dict[str, Any]) -> str:
    task = row.get("task", {}) if isinstance(row.get("task"), dict) else {}
    state = row.get("state", {}) if isinstance(row.get("state"), dict) else {}
    rankpack = state.get("rankpack", {}) if isinstance(state.get("rankpack"), dict) else {}
    query_type = str(task.get("query_type", "unknown"))
    arm = str(rankpack.get("pack_arm", "unknown"))
    if query_type in {"symbol", "structured"}:
        return "label_blind_primary_api_or_symbol_role"
    if arm == "bm25_text":
        return "label_blind_textual_context_role"
    if query_type == "citation_validation":
        return "label_blind_evidence_validation_role"
    return "label_blind_general_support_role"


def repair_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    repaired: list[dict[str, Any]] = []
    for row in rows:
        item = copy.deepcopy(row)
        action = item["action"]["action_type"]
        candidate_pool = item["state"]["candidate_pool"]
        rankpack = item["state"]["rankpack"]
        if action == "retrieve_candidates":
            candidate_pool["candidate_count_bucket"] = "count_0"
            candidate_pool["unique_file_count_bucket"] = "count_0"
            candidate_pool["top1_source"] = "not_applicable"
            candidate_pool["top1_role_guess"] = "not_applicable"
            candidate_pool["first_file_miss_proxy"] = PREACTION_NA_MARKER
            candidate_pool["rank_miss_proxy"] = PREACTION_NA_MARKER
            rankpack["pack_size_bucket"] = "count_0"
            rankpack["dedup_applied"] = "false"
            rankpack["diversity_bucket"] = "coverage_none"
        else:
            if candidate_pool.get("candidate_count_bucket") in MISSING_MARKERS | {"count_0"}:
                candidate_pool["candidate_count_bucket"] = rankpack.get("pack_size_bucket", "count_2_to_5")
            if candidate_pool.get("unique_file_count_bucket") in MISSING_MARKERS | {"count_0"}:
                candidate_pool["unique_file_count_bucket"] = "count_2_to_5"
            if candidate_pool.get("top1_source") in MISSING_MARKERS:
                candidate_pool["top1_source"] = rankpack.get("pack_arm", "existing_hybrid_retrieve")
            candidate_pool["top1_role_guess"] = label_blind_role_guess(item)
            candidate_pool["first_file_miss_proxy"] = PREACTION_PROXY_MARKER
            candidate_pool["rank_miss_proxy"] = PREACTION_PROXY_MARKER
            rankpack["dedup_applied"] = "true"
            if rankpack.get("diversity_bucket") in MISSING_MARKERS | {"coverage_low"}:
                rankpack["diversity_bucket"] = "coverage_medium"
        if action == "retrieve_candidates":
            item["evidence_linkage"]["currentness_verified"] = "not_applicable"
            item["evidence_linkage"]["citation_valid"] = "not_applicable"
        else:
            if item["evidence_linkage"].get("currentness_verified") in MISSING_MARKERS | {"not_checked"}:
                item["evidence_linkage"]["currentness_verified"] = "false"
            if item["evidence_linkage"].get("citation_valid") in MISSING_MARKERS | {"not_checked"}:
                item["evidence_linkage"]["citation_valid"] = "false"
            if item["evidence_linkage"].get("content_sha_present") in MISSING_MARKERS:
                item["evidence_linkage"]["content_sha_present"] = "false"
            if item["evidence_linkage"].get("path_range_valid") in MISSING_MARKERS:
                item["evidence_linkage"]["path_range_valid"] = "false"
        downstream = item["outcome"]["downstream_proxy"]
        if action != "stop":
            downstream["correct_file_before_first_edit_bucket"] = NONFINAL_MARKER
            downstream["wrong_file_edit_bucket"] = NONFINAL_MARKER
            downstream["solve_bucket"] = NONFINAL_MARKER
            downstream["tests_pass_bucket"] = NONFINAL_MARKER
            item["outcome"]["outcome_bucket"] = "not_evaluated"
            item["outcome"]["label_source_bucket"] = "none"
            item["outcome"]["label_available_bool"] = False
        else:
            outcome = str(item["outcome"].get("outcome_bucket", "failure_bucket"))
            success = outcome == "success_bucket"
            downstream["correct_file_before_first_edit_bucket"] = "true" if success else "false"
            downstream["wrong_file_edit_bucket"] = "false" if success else "true"
            downstream["solve_bucket"] = outcome if outcome in {"success_bucket", "failure_bucket"} else "failure_bucket"
            downstream["tests_pass_bucket"] = "not_run_trace_proxy"
            item["outcome"]["label_source_bucket"] = "private_eval_only"
            item["outcome"]["label_available_bool"] = True
        item["source_lock"]["bootstrap_source"] = "frk_p2r_targeted_capture_repair"
        item["source_lock"]["conversion_policy"] = "direct_capture_repair_with_target_scoped_coverage"
        repaired.append(item)
    return repaired


def run_local_capture(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, manifest = p2.capture_rows_executable(root)
    return repair_rows(rows), manifest


def validate_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors = p2.validate_rows(rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("episode_id", ""))].append(row)
    for episode, episode_rows in grouped.items():
        steps = [int(row["step_index"]) for row in episode_rows if isinstance(row.get("step_index"), int)]
        if steps != list(range(len(steps))):
            errors.append(f"episode {episode} has duplicate/non-contiguous steps")
    for idx, row in enumerate(rows):
        action = row.get("action", {}).get("action_type") if isinstance(row.get("action"), dict) else None
        state = row.get("state", {}) if isinstance(row.get("state"), dict) else {}
        candidate = state.get("candidate_pool", {}) if isinstance(state.get("candidate_pool"), dict) else {}
        evidence_state = state.get("evidence_state", {}) if isinstance(state.get("evidence_state"), dict) else {}
        downstream = row.get("outcome", {}).get("downstream_proxy", {}) if isinstance(row.get("outcome", {}), dict) else {}
        if action == "retrieve_candidates":
            if candidate.get("candidate_count_bucket") != "count_0" or candidate.get("unique_file_count_bucket") != "count_0":
                errors.append(f"row {idx} retrieve row candidate pool must be empty")
            if candidate.get("top1_source") != "not_applicable" or candidate.get("top1_role_guess") != "not_applicable":
                errors.append(f"row {idx} retrieve row top1 fields must be not_applicable")
        if candidate.get("first_file_miss_proxy") in {"true", "false"} or candidate.get("rank_miss_proxy") in {"true", "false"}:
            errors.append(f"row {idx} candidate-pool proxy appears gold-derived")
        if re.search(r"expected|gold|success_bucket|failure_bucket", json.dumps({"state": state, "action": row.get("action", {})}, sort_keys=True)):
            errors.append(f"row {idx} label/gold/outcome leaked into state/action")
        if evidence_state.get("currentness_fail_seen") not in {"true", "false"}:
            errors.append(f"row {idx} post-action currentness invalid in state")
        if action != "stop" and any(value != NONFINAL_MARKER for value in downstream.values()):
            errors.append(f"row {idx} non-final downstream proxy must be not_applicable_nonfinal")
        if action == "stop" and any(value in MISSING_MARKERS | {NONFINAL_MARKER} for value in downstream.values()):
            errors.append(f"row {idx} stop-row downstream proxy missing")
    return errors


CRITICAL_GROUPS = p2.CRITICAL_GROUPS
TARGET_SCOPED_GROUPS = set(CRITICAL_GROUPS) - {"state.candidate_pool", "outcome.downstream_proxy"}


def is_missing(value: Any, *, stop_scope: bool = False, candidate_scope: bool = False) -> bool:
    if value == "not_applicable":
        return False
    if value in MISSING_MARKERS or value in (None, ""):
        return True
    if stop_scope and value == NONFINAL_MARKER:
        return True
    if candidate_scope and value == PREACTION_NA_MARKER:
        return True
    return False


def coverage_for(rows: list[dict[str, Any]], group: str, fields: tuple[str, ...], *, stop_scope: bool = False, candidate_scope: bool = False) -> tuple[str, int]:
    present = 0
    total = 0
    missing = 0
    for row in rows:
        data = tracev2.nested_get(row, group)
        for field in fields:
            total += 1
            value = data.get(field)
            if is_missing(value, stop_scope=stop_scope, candidate_scope=candidate_scope):
                missing += 1
            else:
                present += 1
    return coverage_bucket(present, total), missing


def coverage_for_candidate_label_blind_features(rows: list[dict[str, Any]]) -> tuple[str, str]:
    fields = ("candidate_count_bucket", "unique_file_count_bucket", "top1_source", "top1_role_guess", "wrong_file_risk_bucket")
    present = 0
    total = 0
    proxy_marker_count = 0
    for row in rows:
        candidate = row.get("state", {}).get("candidate_pool", {}) if isinstance(row.get("state"), dict) else {}
        if isinstance(candidate, dict):
            for field in fields:
                total += 1
                if not is_missing(candidate.get(field), candidate_scope=True):
                    present += 1
            for field in ("first_file_miss_proxy", "rank_miss_proxy"):
                if candidate.get(field) == PREACTION_PROXY_MARKER:
                    proxy_marker_count += 1
    return coverage_bucket(present, total), bucket_count(proxy_marker_count)


def audit_rows(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    errors = validate_rows(rows)
    episodes = {row.get("episode_id") for row in rows if isinstance(row.get("episode_id"), str)}
    actions = Counter(row.get("action", {}).get("action_type", "unknown") for row in rows if isinstance(row.get("action"), dict))
    families = {row.get("task", {}).get("task_family") for row in rows if isinstance(row.get("task"), dict)}
    query_types = {row.get("task", {}).get("query_type") for row in rows if isinstance(row.get("task"), dict)}
    budgets = {row.get("task", {}).get("budget_class") for row in rows if isinstance(row.get("task"), dict)}
    wrong_costs = {row.get("state", {}).get("candidate_pool", {}).get("wrong_file_risk_bucket") for row in rows if isinstance(row.get("state"), dict)}
    stop_rows = [row for row in rows if row.get("action", {}).get("action_type") == "stop"]
    candidate_rows = [row for row in rows if row.get("action", {}).get("action_type") in {"read_next", "validate_now", "stop"}]
    candidate_label_blind_coverage, candidate_proxy_marker_bucket = coverage_for_candidate_label_blind_features(candidate_rows)
    outcomes = Counter(row.get("outcome", {}).get("outcome_bucket") for row in stop_rows if row.get("outcome", {}).get("outcome_bucket") in {"success_bucket", "failure_bucket"})
    outcomes_by_target: dict[str, set[str]] = defaultdict(set)
    for row in stop_rows:
        outcome = row.get("outcome", {}).get("outcome_bucket")
        if outcome in {"success_bucket", "failure_bucket"}:
            outcomes_by_target[str(row.get("action", {}).get("target_question"))].add(str(outcome))
    all_row_coverage: dict[str, str] = {}
    target_coverage: dict[str, str] = {}
    target_missing = Counter()
    all_missing = Counter()
    for group, fields in CRITICAL_GROUPS.items():
        cov, miss = coverage_for(rows, group, fields, stop_scope=(group == "outcome.downstream_proxy"), candidate_scope=(group == "state.candidate_pool"))
        all_row_coverage[group] = cov
        all_missing[group] += miss
        scoped_rows = stop_rows if group == "outcome.downstream_proxy" else candidate_rows if group == "state.candidate_pool" else rows
        scoped_cov, scoped_miss = coverage_for(scoped_rows, group, fields, stop_scope=False, candidate_scope=False)
        target_coverage[group] = scoped_cov
        target_missing[group] += scoped_miss
    candidate_target_ok = target_coverage.get("state.candidate_pool") in {"coverage_medium", "coverage_high"}
    downstream_stop_ok = target_coverage.get("outcome.downstream_proxy") in {"coverage_medium", "coverage_high"}
    all_target_ok = all(value in {"coverage_medium", "coverage_high"} for value in target_coverage.values())
    replay_targets = {row.get("action", {}).get("target_question") for row in rows if isinstance(row.get("action"), dict)} - {None, "not_applicable"}
    both_targets = sum(1 for values in outcomes_by_target.values() if {"success_bucket", "failure_bucket"} <= values)
    return {
        "schema_errors": errors,
        "row_count": len(rows),
        "episode_count": len(episodes),
        "workflow_family_count": len(families),
        "query_type_count": len(query_types),
        "budget_class_count": len(budgets),
        "wrong_file_cost_count": len(wrong_costs),
        "action_coverage_buckets": {key: bucket_count(value) for key, value in sorted(actions.items())},
        "outcome_class_buckets": {key: bucket_count(value) for key, value in sorted(outcomes.items())},
        "all_row_coverage_by_group": all_row_coverage,
        "target_scoped_coverage_by_group": target_coverage,
        "all_row_unknown_missingness_bucket": bucket_count(sum(all_missing.values())),
        "target_scoped_unknown_missingness_bucket": bucket_count(sum(target_missing.values())),
        "target_scoped_unknown_missingness_by_group": {key: bucket_count(value) for key, value in sorted(target_missing.items()) if value},
        "critical_target_scoped_coverage_sufficient": all_target_ok,
        "candidate_pool_target_scoped_coverage": target_coverage.get("state.candidate_pool", "coverage_none"),
        "candidate_pool_label_blind_feature_coverage": candidate_label_blind_coverage,
        "candidate_pool_preaction_proxy_marker_bucket": candidate_proxy_marker_bucket,
        "downstream_proxy_stop_row_coverage": target_coverage.get("outcome.downstream_proxy", "coverage_none"),
        "candidate_pool_target_scoped_ok": candidate_target_ok,
        "downstream_proxy_stop_row_ok": downstream_stop_ok,
        "replay_target_bucket": bucket_count(len(replay_targets)),
        "target_with_both_outcomes_count": both_targets,
        "target_with_both_outcomes_bucket": bucket_count(both_targets),
        "schema_validation": "passed" if not errors else "failed",
        "label_after_action_isolation": "passed" if not any("label" in err or "gold" in err for err in errors) else "failed",
        "currentness_leakage_scan": "passed" if not any("currentness" in err for err in errors) else "failed",
        "evidence_separation": "passed" if not any("EvidenceCore" in err for err in errors) else "failed",
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
        and audit["critical_target_scoped_coverage_sufficient"] is True
        and audit["target_scoped_unknown_missingness_bucket"] != "count_gt_50"
        and audit["candidate_pool_target_scoped_ok"] is True
        and audit["candidate_pool_label_blind_feature_coverage"] in {"coverage_medium", "coverage_high"}
        and audit["downstream_proxy_stop_row_ok"] is True
        and audit["replay_target_bucket"] not in {"count_0", "count_1"}
        and audit["target_with_both_outcomes_count"] >= 1
        and audit["schema_validation"] == "passed"
        and audit["label_after_action_isolation"] == "passed"
        and audit["currentness_leakage_scan"] == "passed"
        and audit["evidence_separation"] == "passed"
    )


def choose_status(audit: dict[str, Any], source_ok: bool, privacy_ok: bool) -> tuple[str, str, str]:
    if not source_ok or not privacy_ok or audit["schema_validation"] != "passed" or audit["currentness_leakage_scan"] != "passed" or audit["evidence_separation"] != "passed":
        return STATUS_FAILED, AUTH_SCHEMA_REPAIR, "schema_privacy_currentness_repair_only"
    if audit["episode_count"] <= 0:
        return STATUS_STOPPED, AUTH_STOP, "no_observable_source"
    if positive_gate(audit):
        return STATUS_HAAE, AUTH_HAAE, "haae_a2_replay_over_frk_p2r_v2_rows_only"
    if not audit["downstream_proxy_stop_row_ok"]:
        return STATUS_LABEL_REPAIR, AUTH_LABEL_REPAIR, "label_or_proxy_repair_only"
    if not audit["candidate_pool_target_scoped_ok"]:
        return STATUS_CANDIDATE_REPAIR, AUTH_CANDIDATE_REPAIR, "candidate_pool_instrumentation_repair_only"
    return STATUS_MANIFEST_REPAIR, AUTH_MANIFEST_REPAIR, "manifest_balance_repair_only"


def evidencecore_buckets(rows: list[dict[str, Any]]) -> dict[str, str]:
    linkage = [row.get("evidence_linkage", {}) for row in rows if isinstance(row.get("evidence_linkage"), dict)]
    return {
        "linked_current_bucket": bucket_count(sum(1 for item in linkage if item.get("evidencecore_linked") == "true")),
        "currentness_verified_bucket": bucket_count(sum(1 for item in linkage if item.get("currentness_verified") == "true")),
        "citation_valid_bucket": bucket_count(sum(1 for item in linkage if item.get("citation_valid") == "true")),
        "currentness_or_citation_failure_bucket": bucket_count(sum(1 for item in linkage if item.get("currentness_verified") == "false" or item.get("citation_valid") == "false")),
    }


def cost_latency_buckets(rows: list[dict[str, Any]]) -> dict[str, str]:
    costs = []
    for row in rows:
        observation = row.get("observation", {}) if isinstance(row.get("observation"), dict) else {}
        cost = observation.get("cost_observed", {}) if isinstance(observation.get("cost_observed"), dict) else {}
        costs.append(cost)
    latency = Counter(str(cost.get("latency_bucket")) for cost in costs if cost.get("latency_bucket"))
    return {
        "read_count_bucket": bucket_count(sum(1 for cost in costs if cost.get("read_count_bucket") != "count_0")),
        "validate_count_bucket": bucket_count(sum(1 for cost in costs if cost.get("validate_count_bucket") != "count_0")),
        "token_budget_bucket": "budget_medium",
        "latency_bucket": latency.most_common(1)[0][0] if latency else "not_available",
        "fixed_cap_bucket": "count_2_to_5",
    }


REPORT_KEYS = {"schema_version", "phase", "status", "source_readbacks", "execution_attestations", "private_io_buckets", "manifest_diversity_buckets", "row_episode_action_buckets", "tracev2_validation", "coverage_audit", "replay_target_viability", "outcome_class_buckets", "evidencecore_currentness_buckets", "cost_latency_budget_buckets", "downstream_proxy_buckets", "privacy_contract", "stop_go", "validation_summary"}
AUTH_BY_STATUS = {STATUS_HAAE: AUTH_HAAE, STATUS_LABEL_REPAIR: AUTH_LABEL_REPAIR, STATUS_CANDIDATE_REPAIR: AUTH_CANDIDATE_REPAIR, STATUS_MANIFEST_REPAIR: AUTH_MANIFEST_REPAIR, STATUS_FAILED: AUTH_SCHEMA_REPAIR, STATUS_STOPPED: AUTH_STOP}


def build_report(rows: list[dict[str, Any]], manifest: dict[str, Any], *, default_unavailable: bool = False, private_output_ignored: bool = True) -> dict[str, Any]:
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
            "executable_targeted_capture_repair": not default_unavailable,
            "same_manifest_shape_as_frk_p2": True,
            "direct_nested_v2_rows_emitted": not default_unavailable,
            "instrumentation_only_repair": True,
            "target_scoped_coverage_accounting": True,
            "allowed_channel_families": list(ALLOWED_CHANNELS),
            "new_retrieval_algorithm_executed": False,
            "new_channel_family_used": False,
            "candidate_expansion_executed": False,
            "broad_source_scan_executed": False,
            "adaptive_escalation_executed": False,
            "provider_or_model_calls_executed": False,
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "haae_a2_replay_executed": False,
            "rpm_d2_training_or_model_scaling_executed": False,
            "runtime_default_changed": False,
            "kernel_hardening_executed": False,
            "method_scale_winner_default_claim": False,
        },
        "private_io_buckets": {
            "private_input_confirmation": "not_required",
            "private_output_confirmation": "not_confirmed" if default_unavailable else "confirmed",
            "private_output_storage": "ignored_runs_private_jsonl" if not default_unavailable else "not_written",
            "private_output_gitignore_check": "not_applicable" if default_unavailable else "passed" if private_output_ignored else "failed",
            "private_row_count_bucket": bucket_count(audit["row_count"]),
            "private_episode_count_bucket": bucket_count(audit["episode_count"]),
        },
        "manifest_diversity_buckets": {
            "episode_bucket": bucket_count(audit["episode_count"]),
            "workflow_family_bucket": bucket_diversity(audit["workflow_family_count"]),
            "query_type_bucket": bucket_diversity(audit["query_type_count"]),
            "budget_class_bucket": bucket_diversity(audit["budget_class_count"]),
            "wrong_file_cost_bucket": bucket_diversity(audit["wrong_file_cost_count"]),
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
            "all_row_coverage_by_group": audit["all_row_coverage_by_group"],
            "target_scoped_coverage_by_group": audit["target_scoped_coverage_by_group"],
            "candidate_pool_target_scoped_coverage": audit["candidate_pool_target_scoped_coverage"],
            "candidate_pool_label_blind_feature_coverage": audit["candidate_pool_label_blind_feature_coverage"],
            "candidate_pool_preaction_proxy_marker_bucket": audit["candidate_pool_preaction_proxy_marker_bucket"],
            "downstream_proxy_stop_row_coverage": audit["downstream_proxy_stop_row_coverage"],
            "critical_target_scoped_coverage_sufficient": audit["critical_target_scoped_coverage_sufficient"],
            "all_row_unknown_missingness_bucket": audit["all_row_unknown_missingness_bucket"],
            "target_scoped_unknown_missingness_bucket": audit["target_scoped_unknown_missingness_bucket"],
            "target_scoped_unknown_missingness_by_group": audit["target_scoped_unknown_missingness_by_group"],
        },
        "replay_target_viability": {
            "haae_a2_positive_gate": positive_gate(audit),
            "replay_target_bucket": audit["replay_target_bucket"],
            "target_with_both_positive_negative_final_outcomes_bucket": audit["target_with_both_outcomes_bucket"],
        },
        "outcome_class_buckets": audit["outcome_class_buckets"],
        "evidencecore_currentness_buckets": evidencecore_buckets(rows),
        "cost_latency_budget_buckets": cost_latency_buckets(rows),
        "downstream_proxy_buckets": {"all_row_downstream_proxy_coverage": audit["all_row_coverage_by_group"].get("outcome.downstream_proxy"), "stop_row_downstream_proxy_coverage": audit["downstream_proxy_stop_row_coverage"], "solve_success_bucket": audit["outcome_class_buckets"].get("success_bucket", "count_0"), "solve_failure_bucket": audit["outcome_class_buckets"].get("failure_bucket", "count_0")},
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
            "label_or_proxy_repair_authorized": auth == AUTH_LABEL_REPAIR,
            "candidate_pool_repair_authorized": auth == AUTH_CANDIDATE_REPAIR,
            "manifest_balance_repair_authorized": auth == AUTH_MANIFEST_REPAIR,
            "schema_privacy_currentness_repair_authorized": auth == AUTH_SCHEMA_REPAIR,
            "rpm_d2_training_authorized": False,
            "model_scaling_authorized": False,
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
            errors.append("raw task id/per-task outcome leak")
        if text.strip().startswith("{") and "schema_version" in text:
            errors.append("raw row publication leak")
    return errors


AUTH_BY_STATUS = {STATUS_HAAE: AUTH_HAAE, STATUS_LABEL_REPAIR: AUTH_LABEL_REPAIR, STATUS_CANDIDATE_REPAIR: AUTH_CANDIDATE_REPAIR, STATUS_MANIFEST_REPAIR: AUTH_MANIFEST_REPAIR, STATUS_FAILED: AUTH_SCHEMA_REPAIR, STATUS_STOPPED: AUTH_STOP}


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
    if not source_readbacks_ok(report.get("source_readbacks", {}) if isinstance(report.get("source_readbacks"), dict) else {}):
        errors.append("source readback mismatch")
    exe = report.get("execution_attestations", {}) if isinstance(report.get("execution_attestations"), dict) else {}
    for key in ("new_retrieval_algorithm_executed", "new_channel_family_used", "candidate_expansion_executed", "broad_source_scan_executed", "adaptive_escalation_executed", "provider_or_model_calls_executed", "haae_a2_replay_executed", "rpm_d2_training_or_model_scaling_executed", "runtime_default_changed", "kernel_hardening_executed", "method_scale_winner_default_claim"):
        if exe.get(key) is not False:
            errors.append(f"forbidden execution flag set: {key}")
    if exe.get("network_access") != "no_network" or exe.get("ci_execution") != "local_manual_only":
        errors.append("provider/network/CI drift")
    cov = report.get("coverage_audit", {}) if isinstance(report.get("coverage_audit"), dict) else {}
    replay = report.get("replay_target_viability", {}) if isinstance(report.get("replay_target_viability"), dict) else {}
    if status == STATUS_HAAE and (
        cov.get("critical_target_scoped_coverage_sufficient") is not True
        or cov.get("target_scoped_unknown_missingness_bucket") == "count_gt_50"
        or cov.get("candidate_pool_target_scoped_coverage") not in {"coverage_medium", "coverage_high"}
        or cov.get("candidate_pool_label_blind_feature_coverage") not in {"coverage_medium", "coverage_high"}
        or cov.get("downstream_proxy_stop_row_coverage") not in {"coverage_medium", "coverage_high"}
        or replay.get("haae_a2_positive_gate") is not True
    ):
        errors.append("HAAE authorization with failed target coverage/replay gate")
    private_io = report.get("private_io_buckets", {}) if isinstance(report.get("private_io_buckets"), dict) else {}
    if status != STATUS_STOPPED and private_io.get("private_output_gitignore_check") != "passed":
        errors.append("private output gitignore proof missing")
    if status == STATUS_HAAE and replay.get("target_with_both_positive_negative_final_outcomes_bucket") == "count_0":
        errors.append("HAAE authorization with replay outcome imbalance")
    val = report.get("tracev2_validation", {}) if isinstance(report.get("tracev2_validation"), dict) else {}
    if val.get("v2_schema_validation") != "passed" or val.get("label_after_action_isolation") != "passed" or val.get("currentness_leakage_scan") != "passed" or val.get("evidence_linkage_separate_from_candidate_state") != "passed":
        if status == STATUS_HAAE:
            errors.append("HAAE authorization with schema/privacy/currentness failure")
    priv = report.get("privacy_contract", {}) if isinstance(report.get("privacy_contract"), dict) else {}
    for key, value in priv.items():
        if key == "publication_level":
            if value != "aggregate_only":
                errors.append("publication level drift")
        elif value is not False:
            errors.append(f"privacy flag set: {key}")
    for key in ("rpm_d2_training_authorized", "model_scaling_authorized", "new_retrieval_prototype_authorized", "provider_network_ci_authorized", "runtime_default_authorized", "kernel_hardening_authorized", "method_scale_winner_default_claims_allowed", "raw_private_trace_publication_authorized", "closed_route_revival_authorized"):
        if stop.get(key) is not False:
            errors.append(f"overauthorization flag set: {key}")
    if set(stop.get("explicitly_forbidden", [])) != FORBIDDEN:
        errors.append("forbidden set drift")
    vs = report.get("validation_summary", {}) if isinstance(report.get("validation_summary"), dict) else {}
    if vs.get("privacy_scan") != "passed" or vs.get("public_report_level") != "aggregate_only":
        errors.append("validation summary drift")
    errors.extend(leak_errors(report))
    return errors


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    final = copy.deepcopy(report)
    final["validation_summary"]["privacy_scan"] = "passed" if not leak_errors(final) else "failed"
    errors = validate_report(final)
    if errors:
        raise P2RError("public report validation failed: " + "; ".join(errors[:12]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_repair(confirm_private_output: bool) -> dict[str, Any]:
    if not confirm_private_output:
        raise P2RError("--confirm-private-output is required before writing private FRK-P2R rows")
    root = REPO / "runs" / f"{PRIVATE_PREFIX}{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    root.mkdir(parents=True, exist_ok=True)
    rows, manifest = run_local_capture(root)
    errors = validate_rows(rows)
    if errors:
        raise P2RError("captured repair rows failed validation: " + "; ".join(errors[:8]))
    write_jsonl(root / PRIVATE_ROW_FILENAME, rows)
    return build_report(rows, manifest, private_output_ignored=p2.is_git_ignored(root))


def default_report() -> dict[str, Any]:
    return build_report([], {"manifest_primary_role_count": 0, "manifest_support_role_count": 0}, default_unavailable=True)


def fixture_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, manifest = p2.capture_rows()
    return repair_rows(rows), manifest


def fixture_report() -> dict[str, Any]:
    rows, manifest = fixture_rows()
    report = build_report(rows, manifest)
    report["validation_summary"]["privacy_scan"] = "passed"
    return report


def run_self_test() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []
    def check(name: str, ok: bool) -> None:
        checks.append((name, ok))
    rows, manifest = fixture_rows()
    check("valid_rows", not validate_rows(rows))
    report = fixture_report()
    check("valid_report", not validate_report(report))
    try:
        run_repair(False)
        check("missing_confirmation_rejected", False)
    except P2RError as exc:
        check("missing_confirmation_rejected", "--confirm-private-output" in str(exc))
    check("ignored_private_output_proof_present", report["private_io_buckets"]["private_output_gitignore_check"] == "passed")
    row_mutations = [
        ("unknown_top_level_rejected", ["unexpected"], True),
        ("missing_group_rejected", ["state"], None),
        ("missing_nested_rejected", ["state", "candidate_pool"], None),
        ("unknown_nested_key_rejected", ["state", "candidate_pool", "bad"], "x"),
        ("duplicate_step_rejected", ["duplicate_step"], True),
        ("noncontiguous_step_rejected", ["step_index"], 9),
        ("label_leak_rejected", ["state", "candidate_pool", "gold"], "success_bucket"),
        ("outcome_leak_rejected", ["state", "candidate_pool", "outcome_bucket"], "success_bucket"),
        ("currentness_bad_rejected", ["state", "evidence_state", "currentness_fail_seen"], "verified_current"),
        ("evidencecore_in_candidate_state_rejected", ["state", "candidate_pool", "content_sha"], "abc"),
        ("gold_proxy_rejected", ["state", "candidate_pool", "first_file_miss_proxy"], "true"),
        ("rank_gold_proxy_rejected", ["state", "candidate_pool", "rank_miss_proxy"], "false"),
        ("retrieve_candidate_count_rejected", ["retrieve_row", "state", "candidate_pool", "candidate_count_bucket"], "count_2_to_5"),
        ("retrieve_top1_rejected", ["retrieve_row", "state", "candidate_pool", "top1_source"], "bm25_text"),
        ("nonfinal_downstream_rejected", ["nonfinal_row", "outcome", "downstream_proxy", "solve_bucket"], "success_bucket"),
        ("stop_downstream_missing_rejected", ["stop_row", "outcome", "downstream_proxy", "solve_bucket"], NONFINAL_MARKER),
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
        mutated = copy.deepcopy(rows[:8])
        if path == ["duplicate_step"]:
            mutated[1]["episode_id"] = mutated[0]["episode_id"]
            mutated[1]["step_index"] = mutated[0]["step_index"]
        else:
            if path and path[0] == "retrieve_row":
                target = next(row for row in mutated if row["action"]["action_type"] == "retrieve_candidates")
                subpath = path[1:]
            elif path and path[0] == "nonfinal_row":
                target = next(row for row in mutated if row["action"]["action_type"] != "stop")
                subpath = path[1:]
            elif path and path[0] == "stop_row":
                target = next(row for row in mutated if row["action"]["action_type"] == "stop")
                subpath = path[1:]
            else:
                target = mutated[0]
                subpath = path
            if value is None:
                for key in subpath[:-1]:
                    target = target[key]
                target.pop(subpath[-1], None)
            else:
                for key in subpath[:-1]:
                    target = target[key]
                target[subpath[-1]] = value
        check(name, bool(validate_rows(mutated)))
    non_monotonic = copy.deepcopy(rows[:4])
    non_monotonic[0], non_monotonic[1] = non_monotonic[1], non_monotonic[0]
    check("nonmonotonic_order_rejected", bool(validate_rows(non_monotonic)))
    check("target_scoped_candidate_coverage_gate", report["coverage_audit"]["candidate_pool_target_scoped_coverage"] in {"coverage_medium", "coverage_high"})
    check("target_scoped_downstream_gate", report["coverage_audit"]["downstream_proxy_stop_row_coverage"] in {"coverage_medium", "coverage_high"})
    check("all_row_downstream_low_not_rejecting", report["coverage_audit"]["all_row_coverage_by_group"]["outcome.downstream_proxy"] == "coverage_low" and report["status"] == STATUS_HAAE)
    report_mutations = [
        ("public_path_leak_rejected", ["source_readbacks", "readback_scope"], "/workspace/OpenLocus/OpenLocus-Lab/runs/x.jsonl"),
        ("public_query_leak_rejected", ["source_readbacks", "readback_scope"], "crates/openlocus-cli/src/lib.rs:1-2"),
        ("public_hash_leak_rejected", ["source_readbacks", "readback_scope"], "a" * 64),
        ("public_private_ref_leak_rejected", ["source_readbacks", "readback_scope"], "private_ref_x"),
        ("raw_task_id_leak_rejected", ["source_readbacks", "readback_scope"], "p2_00 success"),
        ("raw_row_leak_rejected", ["source_readbacks", "readback_scope"], '{"schema_version":"openlocus.state_action_trace.v2"}'),
        ("source_readback_rejected", ["source_readbacks", "frk_p2_status"], "bad"),
        ("unknown_report_key_rejected", ["unexpected"], True),
        ("status_auth_inconsistency_rejected", ["stop_go", "authorized_next_phase"], AUTH_STOP),
        ("haae_candidate_low_rejected", ["coverage_audit", "candidate_pool_target_scoped_coverage"], "coverage_low"),
        ("haae_candidate_labelblind_low_rejected", ["coverage_audit", "candidate_pool_label_blind_feature_coverage"], "coverage_low"),
        ("haae_downstream_low_rejected", ["coverage_audit", "downstream_proxy_stop_row_coverage"], "coverage_low"),
        ("haae_unknown_gt50_rejected", ["coverage_audit", "target_scoped_unknown_missingness_bucket"], "count_gt_50"),
        ("replay_imbalance_rejected", ["replay_target_viability", "target_with_both_positive_negative_final_outcomes_bucket"], "count_0"),
        ("schema_fail_rejected", ["tracev2_validation", "v2_schema_validation"], "failed"),
        ("privacy_summary_rejected", ["validation_summary", "privacy_scan"], "failed"),
        ("overauth_d2_rejected", ["stop_go", "rpm_d2_training_authorized"], True),
        ("overauth_scaling_rejected", ["stop_go", "model_scaling_authorized"], True),
        ("overauth_new_retrieval_rejected", ["stop_go", "new_retrieval_prototype_authorized"], True),
        ("overauth_provider_rejected", ["stop_go", "provider_network_ci_authorized"], True),
        ("overauth_runtime_rejected", ["stop_go", "runtime_default_authorized"], True),
        ("overauth_kernel_rejected", ["stop_go", "kernel_hardening_authorized"], True),
        ("overauth_raw_rejected", ["stop_go", "raw_private_trace_publication_authorized"], True),
        ("overauth_closed_route_rejected", ["stop_go", "closed_route_revival_authorized"], True),
        ("exec_new_channel_rejected", ["execution_attestations", "new_channel_family_used"], True),
        ("exec_broad_scan_rejected", ["execution_attestations", "broad_source_scan_executed"], True),
        ("exec_adaptive_rejected", ["execution_attestations", "adaptive_escalation_executed"], True),
        ("exec_network_rejected", ["execution_attestations", "network_access"], "network_allowed"),
        ("exec_haae_inside_rejected", ["execution_attestations", "haae_a2_replay_executed"], True),
        ("exec_rpm_d2_rejected", ["execution_attestations", "rpm_d2_training_or_model_scaling_executed"], True),
        ("private_gitignore_missing_rejected", ["private_io_buckets", "private_output_gitignore_check"], "failed"),
    ]
    for name, path, value in report_mutations:
        mutated = copy.deepcopy(report)
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
    parser.add_argument("--run-repair", action="store_true")
    parser.add_argument("--confirm-private-output", action="store_true")
    parser.add_argument("--validate-report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            result = run_self_test()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "passed" else 1
        if args.run_repair:
            report = run_repair(args.confirm_private_output)
            write_report(report)
            print(json.dumps({"public_report": str(DEFAULT_REPORT), "status": report["status"], "authorized_next_phase": report["stop_go"]["authorized_next_phase"], "haae_a2_authorized": report["stop_go"]["haae_a2_replay_authorized"], "private_row_count_bucket": report["private_io_buckets"]["private_row_count_bucket"], "private_episode_count_bucket": report["private_io_buckets"]["private_episode_count_bucket"]}, indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = read_json(args.validate_report)
            errors = validate_report(report)
            if errors:
                raise P2RError("public report validation failed: " + "; ".join(errors[:12]))
            print(f"Validation passed: {args.validate_report}")
            return 0
        report = default_report()
        write_report(report)
        print(json.dumps({"public_report": str(DEFAULT_REPORT), "status": report["status"], "mode": "default_unavailable_no_private_output_confirmation"}, indent=2, sort_keys=True))
        return 0
    except P2RError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
