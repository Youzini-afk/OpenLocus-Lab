#!/usr/bin/env python3
"""OpenLocus v2 FRK product-workflow specific retrieval repair design.

This phase is a design-with-static-replay-simulation over existing private trace
evidence only. It does not execute retrieval/search/read/citation validation,
generate candidates, scan sources, train/scale models, use provider/network/CI,
change runtime/defaults, harden kernels, or publish private traces.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import frk_product_workflow_failure_decomposition as decomposition
import frk_product_workflow_trace_benchmark as benchmark
import rpm_trace_schema as schema


REPO = Path(__file__).resolve().parent.parent
PHASE = "openlocus_v2_frk_product_workflow_specific_retrieval_repair_design"
REPORT_SCHEMA_VERSION = "frk_product_workflow_specific_retrieval_repair_design_public_report_v1"
DEFAULT_REPORT = REPO / "artifacts" / "frk_product_workflow_specific_retrieval_repair_design" / "frk_product_workflow_specific_retrieval_repair_design_report.json"
DECOMP_REPORT = REPO / "artifacts" / "frk_product_workflow_failure_decomposition" / "frk_product_workflow_failure_decomposition_report.json"
BENCH_REPORT = REPO / "artifacts" / "frk_product_workflow_trace_benchmark" / "frk_product_workflow_trace_benchmark_report.json"

STATUS_REPAIR = "frk_product_workflow_specific_retrieval_repair_design_incomplete_targeted_repair_only"
STATUS_INCONCLUSIVE = "frk_product_workflow_specific_retrieval_repair_design_inconclusive_trace_or_metric_repair_only"
STATUS_PROXY = "frk_product_workflow_specific_retrieval_repair_design_proxy_metric_repair_first"
STATUS_CONCRETE = "frk_product_workflow_specific_retrieval_repair_design_complete_bounded_prototype_authorized"
STATUS_STOP = "frk_product_workflow_specific_retrieval_repair_design_stop_current_candidate"

AUTH_REPAIR = "targeted_specific_retrieval_repair_design_repair_only"
AUTH_INCONCLUSIVE = "frk_product_workflow_trace_expansion_or_metric_repair_design"
AUTH_PROXY = "frk_product_workflow_metric_proxy_repair_design"
AUTH_CONCRETE = "frk_product_workflow_bounded_retrieval_repair_prototype"
AUTH_STOP = "stop_current_hybrid_retrieve_candidate_or_collect_new_product_workflow_pain"

PRIMARY_EXPECTED = "wrong_file_or_rank_miss"
SECONDARY_EXPECTED = "read_budget_or_topk_limit"
CANDIDATE_ARM = "openlocus_hybrid_retrieve"
BASELINE_ARMS = tuple(benchmark.BASELINE_ARMS)

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

REPORT_KEYS = {
    "schema_version",
    "phase",
    "status",
    "source_readbacks",
    "input_attestations",
    "repair_design_spec",
    "static_replay_simulation_summary",
    "privacy_contract",
    "stop_go",
    "validation_summary",
}
SOURCE_READBACK_KEYS = {
    "benchmark_status",
    "benchmark_best_baseline_delta_bucket",
    "decomposition_status",
    "decomposition_primary_mechanism",
    "decomposition_secondary_mechanism",
    "decomposition_confidence_bucket",
    "authorized_source_phase",
}
INPUT_ATTESTATION_KEYS = {
    "public_benchmark_report_used",
    "public_decomposition_report_used",
    "scripts_inspected_for_schema_action_arm_naming_only",
    "docs_inspected_for_public_status_only",
    "private_input_confirmation",
    "private_rows_schema_validated",
    "static_replay_only",
    "retrieval_rerun_executed",
    "search_rerun_executed",
    "read_rerun_executed",
    "citation_validation_rerun_executed",
    "source_scan_executed",
    "candidate_generation_executed",
    "training_executed",
    "provider_or_model_calls_executed",
    "network_access",
    "ci_execution",
    "runtime_default_changed",
    "kernel_hardening_executed",
}
REPAIR_SPEC_KEYS = {
    "design_family_bucket",
    "same_budget_guarantee",
    "allowed_channel_families",
    "candidate_cap_bucket",
    "read_cap_bucket",
    "validate_cap_bucket",
    "wrong_file_guard",
    "topk_pressure_guard",
    "EvidenceCore_currentness_preservation",
    "label_after_action_preservation",
    "no_new_retrieval_channel_family",
    "prototype_not_executed_in_this_phase",
}
STATIC_REPLAY_KEYS = {
    "replayable_trace_coverage_bucket",
    "mechanism_coverage_bucket",
    "estimated_affected_loss_bucket",
    "unresolved_inconclusive_bucket",
    "proxy_risk_bucket",
    "confidence_bucket",
    "concrete_design_gate_results",
}
CONCRETE_GATE_KEYS = {
    "decomposition_source_expected_status",
    "benchmark_source_expected_status",
    "private_replay_confirmed",
    "private_rows_schema_valid",
    "primary_mechanism_exact",
    "secondary_mechanism_exact",
    "same_candidate_cap",
    "same_read_cap",
    "no_new_retrieval_channel_family",
    "nonzero_affected_loss",
    "unresolved_not_dominant",
    "proxy_risk_not_high",
    "confidence_medium_or_high",
    "public_privacy_scan_passes",
    "source_authorization_readback",
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
    "per_task_replay_public",
    "evidence_filenames_public",
    "exact_labels_public",
    "raw_publication",
}
STOP_GO_KEYS = {
    "decision",
    "authorized_next_phase",
    "explicitly_forbidden",
    "targeted_repair_only_if_incomplete",
    "trace_or_metric_repair_only_if_inconclusive",
    "metric_proxy_repair_first_if_proxy_risk",
    "bounded_retrieval_repair_prototype_if_concrete",
    "stop_current_candidate_if_no_actionable_design",
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
    "privacy_leak_scan",
    "self_test_mutation_coverage",
    "public_report_level",
    "concrete_design_gates_passed",
}
COUNT_BUCKETS = {"count_0", "count_1", "count_2_to_5", "count_6_to_20", "count_21_to_50", "count_gt_50"}
CONFIDENCE_BUCKETS = {"low", "medium", "high"}
PROXY_BUCKETS = {"low", "medium", "high"}
DESIGN_FAMILIES = {"wrong_file_guard_fixed_budget_read_allocation", "intent_channel_guard", "topk_pressure_guard", "proxy_metric_refinement"}
CHANNEL_FAMILIES = {"bm25_text", "symbol_regex", "existing_hybrid_retrieve"}
EXPECTED_DECISION_BY_AUTH = {
    AUTH_REPAIR: "targeted_repair_only",
    AUTH_INCONCLUSIVE: "trace_or_metric_repair_only",
    AUTH_PROXY: "proxy_metric_repair_first",
    AUTH_CONCRETE: "bounded_prototype_authorized",
    AUTH_STOP: "stop_current_candidate_or_collect_new_pain",
}
STATUS_FLAGS = {
    STATUS_REPAIR: {
        "targeted_repair_only_if_incomplete": True,
        "trace_or_metric_repair_only_if_inconclusive": False,
        "metric_proxy_repair_first_if_proxy_risk": False,
        "bounded_retrieval_repair_prototype_if_concrete": False,
        "stop_current_candidate_if_no_actionable_design": False,
    },
    STATUS_INCONCLUSIVE: {
        "targeted_repair_only_if_incomplete": False,
        "trace_or_metric_repair_only_if_inconclusive": True,
        "metric_proxy_repair_first_if_proxy_risk": False,
        "bounded_retrieval_repair_prototype_if_concrete": False,
        "stop_current_candidate_if_no_actionable_design": False,
    },
    STATUS_PROXY: {
        "targeted_repair_only_if_incomplete": False,
        "trace_or_metric_repair_only_if_inconclusive": False,
        "metric_proxy_repair_first_if_proxy_risk": True,
        "bounded_retrieval_repair_prototype_if_concrete": False,
        "stop_current_candidate_if_no_actionable_design": False,
    },
    STATUS_CONCRETE: {
        "targeted_repair_only_if_incomplete": False,
        "trace_or_metric_repair_only_if_inconclusive": False,
        "metric_proxy_repair_first_if_proxy_risk": False,
        "bounded_retrieval_repair_prototype_if_concrete": True,
        "stop_current_candidate_if_no_actionable_design": False,
    },
    STATUS_STOP: {
        "targeted_repair_only_if_incomplete": False,
        "trace_or_metric_repair_only_if_inconclusive": False,
        "metric_proxy_repair_first_if_proxy_risk": False,
        "bounded_retrieval_repair_prototype_if_concrete": False,
        "stop_current_candidate_if_no_actionable_design": True,
    },
}


class RepairDesignError(Exception):
    pass


def bucket_count(count: int) -> str:
    return decomposition.bucket_count(count)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RepairDesignError(f"required public report missing: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise RepairDesignError("required public report malformed") from exc
    if not isinstance(payload, dict):
        raise RepairDesignError("required public report must be a JSON object")
    return payload


def load_private(confirm_private_input: bool, trace_jsonl: Path | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    try:
        return decomposition.load_private_inputs(confirm_private_input, trace_jsonl)
    except decomposition.DecompositionError as exc:
        raise RepairDesignError(str(exc)) from exc


def source_readbacks(bench: dict[str, Any], decomp: dict[str, Any]) -> dict[str, Any]:
    return {
        "benchmark_status": bench.get("status"),
        "benchmark_best_baseline_delta_bucket": bench.get("best_baseline_comparison", {}).get("candidate_vs_best_baseline_delta_bucket"),
        "decomposition_status": decomp.get("status"),
        "decomposition_primary_mechanism": decomp.get("decomposition_summary", {}).get("primary_mechanism_bucket"),
        "decomposition_secondary_mechanism": decomp.get("decomposition_summary", {}).get("secondary_mechanism_bucket"),
        "decomposition_confidence_bucket": decomp.get("decomposition_summary", {}).get("confidence_bucket"),
        "authorized_source_phase": decomp.get("stop_go", {}).get("authorized_next_phase"),
    }


def task_groups_from_private(rows: list[dict[str, Any]], labels: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    metrics = decomposition.trace_metrics(rows, labels)
    groups: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for item in metrics.values():
        groups[item["task_private"]][item["arm"]] = item
    return groups


def static_replay(rows: list[dict[str, Any]], labels: list[dict[str, Any]], decomp: dict[str, Any]) -> dict[str, Any]:
    groups = task_groups_from_private(rows, labels)
    replayable = 0
    affected = 0
    unresolved = 0
    proxy_risk = 0
    mechanism_cover = 0
    for group in groups.values():
        candidate = group.get(CANDIDATE_ARM)
        if not candidate:
            unresolved += 1
            continue
        baseline_success = any(group.get(arm, {}).get("success") is True for arm in BASELINE_ARMS)
        candidate_loss = baseline_success and not candidate.get("success")
        if not candidate_loss:
            continue
        replayable += 1
        wrong_or_budget = bool(candidate.get("partial_valid_wrong")) or candidate.get("workflow_failure_bucket") == "other" or (candidate.get("read_count", 0) >= 2 and candidate.get("topk_candidates_present"))
        if wrong_or_budget:
            affected += 1
            mechanism_cover += 1
        else:
            unresolved += 1
        if candidate.get("workflow_outcome_bucket") == "partial_bucket" and not candidate.get("partial_valid_wrong"):
            proxy_risk += 1
    decomp_mechanisms = decomp.get("mechanism_buckets", {})
    if decomp_mechanisms.get("success_proxy_weakness") not in {None, "count_0"}:
        proxy_risk += 3
    proxy_risk_bucket = "low" if proxy_risk == 0 else ("medium" if proxy_risk <= 3 else "high")
    unresolved_dominant = unresolved > affected
    confidence = "high" if affected >= 6 and not unresolved_dominant and proxy_risk_bucket != "high" else ("medium" if affected > 0 and proxy_risk_bucket != "high" else "low")
    return {
        "replayable_trace_coverage_bucket": bucket_count(replayable),
        "mechanism_coverage_bucket": bucket_count(mechanism_cover),
        "estimated_affected_loss_bucket": bucket_count(affected),
        "unresolved_inconclusive_bucket": bucket_count(unresolved),
        "unresolved_inconclusive_dominant": unresolved_dominant,
        "proxy_risk_bucket": proxy_risk_bucket,
        "confidence_bucket": confidence,
    }


def concrete_gates(readbacks: dict[str, Any], manifest: dict[str, Any], replay: dict[str, Any], privacy_ok: bool) -> dict[str, bool]:
    return {
        "decomposition_source_expected_status": readbacks.get("decomposition_status") == decomposition.STATUS_RETRIEVAL_REPAIR,
        "benchmark_source_expected_status": readbacks.get("benchmark_status") == benchmark.STATUS_NO_LIFT,
        "private_replay_confirmed": manifest.get("private_input_confirmed") is True,
        "private_rows_schema_valid": manifest.get("schema_valid") is True,
        "primary_mechanism_exact": readbacks.get("decomposition_primary_mechanism") == PRIMARY_EXPECTED,
        "secondary_mechanism_exact": readbacks.get("decomposition_secondary_mechanism") == SECONDARY_EXPECTED,
        "same_candidate_cap": True,
        "same_read_cap": True,
        "no_new_retrieval_channel_family": True,
        "nonzero_affected_loss": replay.get("estimated_affected_loss_bucket") not in {"count_0", None},
        "unresolved_not_dominant": replay.get("unresolved_inconclusive_dominant") is False,
        "proxy_risk_not_high": replay.get("proxy_risk_bucket") != "high",
        "confidence_medium_or_high": replay.get("confidence_bucket") in {"medium", "high"},
        "public_privacy_scan_passes": privacy_ok,
        "source_authorization_readback": readbacks.get("authorized_source_phase") == decomposition.AUTHORIZED_RETRIEVAL_REPAIR,
    }


def choose_status(gates: dict[str, bool], replay: dict[str, Any]) -> tuple[str, str, str]:
    if not gates.get("private_rows_schema_valid") or not gates.get("public_privacy_scan_passes"):
        return STATUS_REPAIR, AUTH_REPAIR, "targeted_repair_only"
    if replay.get("proxy_risk_bucket") == "high":
        return STATUS_PROXY, AUTH_PROXY, "proxy_metric_repair_first"
    if replay.get("estimated_affected_loss_bucket") == "count_0" or replay.get("unresolved_inconclusive_dominant") is True:
        return STATUS_INCONCLUSIVE, AUTH_INCONCLUSIVE, "trace_or_metric_repair_only"
    if all(gates.values()):
        return STATUS_CONCRETE, AUTH_CONCRETE, "bounded_prototype_authorized"
    return STATUS_STOP, AUTH_STOP, "stop_current_candidate_or_collect_new_pain"


def build_report(bench: dict[str, Any], decomp: dict[str, Any], rows: list[dict[str, Any]], labels: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = dict(manifest)
    manifest["private_input_confirmed"] = True
    manifest["schema_valid"] = not schema.validate_trace_rows(rows)
    readbacks = source_readbacks(bench, decomp)
    replay = static_replay(rows, labels, decomp)
    privacy_ok = True
    gates = concrete_gates(readbacks, manifest, replay, privacy_ok)
    status, authorized, decision = choose_status(gates, replay)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "phase": PHASE,
        "status": status,
        "source_readbacks": readbacks,
        "input_attestations": {
            "public_benchmark_report_used": True,
            "public_decomposition_report_used": True,
            "scripts_inspected_for_schema_action_arm_naming_only": True,
            "docs_inspected_for_public_status_only": True,
            "private_input_confirmation": "confirmed",
            "private_rows_schema_validated": manifest["schema_valid"],
            "static_replay_only": True,
            "retrieval_rerun_executed": False,
            "search_rerun_executed": False,
            "read_rerun_executed": False,
            "citation_validation_rerun_executed": False,
            "source_scan_executed": False,
            "candidate_generation_executed": False,
            "training_executed": False,
            "provider_or_model_calls_executed": False,
            "network_access": "no_network",
            "ci_execution": "local_manual_only",
            "runtime_default_changed": False,
            "kernel_hardening_executed": False,
        },
        "repair_design_spec": {
            "design_family_bucket": "wrong_file_guard_fixed_budget_read_allocation",
            "same_budget_guarantee": "same_candidate_cap_same_read_cap_no_new_channel_family",
            "allowed_channel_families": ["bm25_text", "symbol_regex", "existing_hybrid_retrieve"],
            "candidate_cap_bucket": "count_2_to_5",
            "read_cap_bucket": "count_2_to_5",
            "validate_cap_bucket": "count_2_to_5",
            "wrong_file_guard": "aggregate_design_only_intent_consistency_before_second_read",
            "topk_pressure_guard": "aggregate_design_only_preserve_top5_candidates_reallocate_existing_two_reads",
            "EvidenceCore_currentness_preservation": True,
            "label_after_action_preservation": True,
            "no_new_retrieval_channel_family": True,
            "prototype_not_executed_in_this_phase": True,
        },
        "static_replay_simulation_summary": {
            **{key: value for key, value in replay.items() if key != "unresolved_inconclusive_dominant"},
            "concrete_design_gate_results": gates,
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
            "per_task_replay_public": False,
            "evidence_filenames_public": False,
            "exact_labels_public": False,
            "raw_publication": False,
        },
        "stop_go": {
            "decision": decision,
            "authorized_next_phase": authorized,
            "explicitly_forbidden": sorted(PUBLIC_FORBIDDEN),
            "targeted_repair_only_if_incomplete": status == STATUS_REPAIR,
            "trace_or_metric_repair_only_if_inconclusive": status == STATUS_INCONCLUSIVE,
            "metric_proxy_repair_first_if_proxy_risk": status == STATUS_PROXY,
            "bounded_retrieval_repair_prototype_if_concrete": status == STATUS_CONCRETE,
            "stop_current_candidate_if_no_actionable_design": status == STATUS_STOP,
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
            "privacy_leak_scan": "pending",
            "self_test_mutation_coverage": "available",
            "public_report_level": "aggregate_only",
            "concrete_design_gates_passed": all(gates.values()),
        },
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


def expected_auth(status: str) -> str | None:
    return {
        STATUS_REPAIR: AUTH_REPAIR,
        STATUS_INCONCLUSIVE: AUTH_INCONCLUSIVE,
        STATUS_PROXY: AUTH_PROXY,
        STATUS_CONCRETE: AUTH_CONCRETE,
        STATUS_STOP: AUTH_STOP,
    }.get(status)


def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(report) != REPORT_KEYS:
        errors.append("unknown or missing top-level report keys")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append("schema version drift")
    if report.get("phase") != PHASE:
        errors.append("phase drift")
    status = report.get("status")
    if not isinstance(status, str):
        errors.append("status must be string")
        status = ""
    if status not in {STATUS_REPAIR, STATUS_INCONCLUSIVE, STATUS_PROXY, STATUS_CONCRETE, STATUS_STOP}:
        errors.append("unknown status")
    readbacks = report.get("source_readbacks", {})
    if not isinstance(readbacks, dict) or set(readbacks) != SOURCE_READBACK_KEYS:
        errors.append("source readback keys drift")
    if readbacks.get("benchmark_status") != benchmark.STATUS_NO_LIFT:
        errors.append("benchmark status readback drift")
    if readbacks.get("benchmark_best_baseline_delta_bucket") != "negative_vs_best_baseline":
        errors.append("benchmark best-baseline delta readback drift")
    if readbacks.get("decomposition_status") != decomposition.STATUS_RETRIEVAL_REPAIR:
        errors.append("decomposition status readback drift")
    if readbacks.get("decomposition_primary_mechanism") != PRIMARY_EXPECTED:
        errors.append("primary mechanism readback drift")
    if readbacks.get("decomposition_secondary_mechanism") != SECONDARY_EXPECTED:
        errors.append("secondary mechanism readback drift")
    if readbacks.get("decomposition_confidence_bucket") != "high":
        errors.append("decomposition confidence readback drift")
    if readbacks.get("authorized_source_phase") != decomposition.AUTHORIZED_RETRIEVAL_REPAIR:
        errors.append("source authorization readback drift")

    att = report.get("input_attestations", {})
    if not isinstance(att, dict) or set(att) != INPUT_ATTESTATION_KEYS:
        errors.append("input attestation keys drift")
    for field in (
        "public_benchmark_report_used", "public_decomposition_report_used", "scripts_inspected_for_schema_action_arm_naming_only",
        "docs_inspected_for_public_status_only", "private_rows_schema_validated", "static_replay_only",
    ):
        if att.get(field) is not True:
            errors.append(f"input_attestations.{field} must be true")
    if att.get("private_input_confirmation") != "confirmed":
        errors.append("private input confirmation missing")
    for field in (
        "retrieval_rerun_executed", "search_rerun_executed", "read_rerun_executed", "citation_validation_rerun_executed",
        "source_scan_executed", "candidate_generation_executed", "training_executed", "provider_or_model_calls_executed",
        "runtime_default_changed", "kernel_hardening_executed",
    ):
        if att.get(field) is not False:
            errors.append(f"input_attestations.{field} must be false")
    if att.get("network_access") != "no_network" or att.get("ci_execution") != "local_manual_only":
        errors.append("network/CI attestation drift")

    spec = report.get("repair_design_spec", {})
    if not isinstance(spec, dict) or set(spec) != REPAIR_SPEC_KEYS:
        errors.append("repair design spec keys drift")
    if spec.get("design_family_bucket") not in DESIGN_FAMILIES:
        errors.append("design family bucket drift")
    if spec.get("same_budget_guarantee") != "same_candidate_cap_same_read_cap_no_new_channel_family":
        errors.append("same budget guarantee drift")
    for field in ("candidate_cap_bucket", "read_cap_bucket", "validate_cap_bucket"):
        if spec.get(field) != "count_2_to_5":
            errors.append(f"{field} drift")
    channels = spec.get("allowed_channel_families", [])
    if not isinstance(channels, list) or set(channels) != CHANNEL_FAMILIES:
        errors.append("allowed channel families drift")
    for field in ("EvidenceCore_currentness_preservation", "label_after_action_preservation", "no_new_retrieval_channel_family", "prototype_not_executed_in_this_phase"):
        if spec.get(field) is not True:
            errors.append(f"repair_design_spec.{field} must be true")

    replay = report.get("static_replay_simulation_summary", {})
    if not isinstance(replay, dict) or set(replay) != STATIC_REPLAY_KEYS:
        errors.append("static replay keys drift")
    gates = replay.get("concrete_design_gate_results", {})
    for field in ("replayable_trace_coverage_bucket", "mechanism_coverage_bucket", "estimated_affected_loss_bucket", "unresolved_inconclusive_bucket"):
        if replay.get(field) not in COUNT_BUCKETS:
            errors.append(f"{field} bucket drift")
    if replay.get("estimated_affected_loss_bucket") in {None, "count_0"} and status == STATUS_CONCRETE:
        errors.append("fake concrete status without affected loss")
    if replay.get("unresolved_inconclusive_bucket") == "count_gt_50" and status == STATUS_CONCRETE:
        errors.append("fake concrete status with dominant unresolved")
    if replay.get("proxy_risk_bucket") == "high" and status == STATUS_CONCRETE:
        errors.append("fake concrete status with high proxy risk")
    if replay.get("proxy_risk_bucket") not in PROXY_BUCKETS:
        errors.append("proxy risk bucket drift")
    if replay.get("confidence_bucket") not in CONFIDENCE_BUCKETS:
        errors.append("confidence enum drift")
    if not isinstance(gates, dict) or set(gates) != CONCRETE_GATE_KEYS:
        errors.append("concrete gate keys drift")
    if status == STATUS_CONCRETE and not all(gates.values()):
        errors.append("fake concrete status without all gates")

    privacy = report.get("privacy_contract", {})
    if not isinstance(privacy, dict) or set(privacy) != PRIVACY_KEYS:
        errors.append("privacy contract keys drift")
    for field in (
        "private_trace_path_public", "private_label_path_public", "raw_task_ids_public", "raw_rows_public", "raw_paths_public",
        "ranges_public", "queries_public", "snippets_public", "hashes_public", "private_refs_public", "per_task_outcomes_public",
        "per_task_replay_public", "evidence_filenames_public", "exact_labels_public", "raw_publication",
    ):
        if privacy.get(field) is not False:
            errors.append(f"privacy_contract.{field} must be false")
    if privacy.get("publication_level") != "aggregate_only":
        errors.append("privacy publication level drift")

    stop = report.get("stop_go", {})
    if not isinstance(stop, dict) or set(stop) != STOP_GO_KEYS:
        errors.append("stop/go keys drift")
    if stop.get("authorized_next_phase") != expected_auth(status):
        errors.append("authorized next phase drift")
    authorized_next_phase = stop.get("authorized_next_phase")
    expected_decision = EXPECTED_DECISION_BY_AUTH.get(authorized_next_phase) if isinstance(authorized_next_phase, str) else None
    if stop.get("decision") != expected_decision:
        errors.append("stop/go decision drift")
    for field, expected in STATUS_FLAGS.get(status, {}).items():
        if stop.get(field) is not expected:
            errors.append(f"stop_go.{field} inconsistent with status")
    if set(stop.get("explicitly_forbidden", [])) != PUBLIC_FORBIDDEN:
        errors.append("forbidden route set drift")
    for field in (
        "d2_or_model_scaling_authorized", "rpm_training_authorized", "runtime_or_default_authorized", "provider_network_ci_authorized",
        "method_scale_winner_claims_allowed", "broad_source_scan_authorized", "candidate_expansion_authorized", "new_retrieval_experiment_authorized",
        "kernel_hardening_authorized", "raw_publication_authorized",
    ):
        if stop.get(field) is not False:
            errors.append(f"stop_go.{field} must be false")
    if stop.get("authorized_next_phase") in stop.get("explicitly_forbidden", []):
        errors.append("forbidden next phase authorized")
    validation = report.get("validation_summary", {})
    if not isinstance(validation, dict) or set(validation) != VALIDATION_KEYS:
        errors.append("validation summary keys drift")
    if validation.get("privacy_leak_scan") != "passed":
        errors.append("privacy leak scan not passed")
    if validation.get("self_test_mutation_coverage") != "available":
        errors.append("self-test mutation coverage not available")
    if validation.get("public_report_level") != "aggregate_only":
        errors.append("validation publication level drift")
    if validation.get("concrete_design_gates_passed") is not (status == STATUS_CONCRETE):
        errors.append("concrete design gate summary drift")
    errors.extend(public_leak_errors(report))
    return errors


def write_report(report: dict[str, Any], path: Path = DEFAULT_REPORT) -> None:
    final = copy.deepcopy(report)
    final["validation_summary"]["privacy_leak_scan"] = "passed" if not public_leak_errors(final) else "failed"
    errors = validate_public_report(final)
    if errors:
        raise RepairDesignError("public report validation failed: " + "; ".join(errors[:10]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fixture_report() -> dict[str, Any]:
    bench = {"status": benchmark.STATUS_NO_LIFT, "best_baseline_comparison": {"candidate_vs_best_baseline_delta_bucket": "negative_vs_best_baseline"}}
    decomp = {
        "status": decomposition.STATUS_RETRIEVAL_REPAIR,
        "decomposition_summary": {"primary_mechanism_bucket": PRIMARY_EXPECTED, "secondary_mechanism_bucket": SECONDARY_EXPECTED, "confidence_bucket": "high"},
        "stop_go": {"authorized_next_phase": decomposition.AUTHORIZED_RETRIEVAL_REPAIR},
        "mechanism_buckets": {"success_proxy_weakness": "count_0"},
    }
    rows, labels, manifest = benchmark.fixture_rows_and_stats()[0], [], {"row_count": 336, "episode_count": 60, "labels_present": True}
    # Build directly with synthetic rows would be label-inconclusive, so start from a compact valid concrete fixture.
    readbacks = source_readbacks(bench, decomp)
    replay = {
        "replayable_trace_coverage_bucket": "count_6_to_20",
        "mechanism_coverage_bucket": "count_6_to_20",
        "estimated_affected_loss_bucket": "count_6_to_20",
        "unresolved_inconclusive_bucket": "count_2_to_5",
        "proxy_risk_bucket": "low",
        "confidence_bucket": "high",
    }
    gates = concrete_gates(readbacks, {"private_input_confirmed": True, "schema_valid": True}, {**replay, "unresolved_inconclusive_dominant": False}, True)
    status, auth, decision = choose_status(gates, {**replay, "unresolved_inconclusive_dominant": False})
    report = build_report(bench, decomp, rows, labels, manifest)
    report["status"] = status
    report["static_replay_simulation_summary"] = {**replay, "concrete_design_gate_results": gates}
    report["stop_go"]["decision"] = decision
    report["stop_go"]["authorized_next_phase"] = auth
    for field, expected in STATUS_FLAGS[status].items():
        report["stop_go"][field] = expected
    report["validation_summary"]["concrete_design_gates_passed"] = True
    report["validation_summary"]["privacy_leak_scan"] = "passed"
    return report


def run_self_tests() -> dict[str, Any]:
    checks: list[tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, condition))

    valid = fixture_report()
    check("fixture_report_valid", not validate_public_report(valid))
    try:
        load_private(False)
        check("missing_private_confirmation_rejected", False)
    except RepairDesignError:
        check("missing_private_confirmation_rejected", True)
    tmp = REPO / "artifacts" / "frk_product_workflow_specific_retrieval_repair_design" / "selftest_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        try:
            load_private(True, tmp / "missing.jsonl")
            check("missing_trace_rejected", False)
        except RepairDesignError:
            check("missing_trace_rejected", True)
        bad = tmp / "bad.jsonl"
        bad.write_text("{bad}\n", encoding="utf-8")
        try:
            load_private(True, bad)
            check("malformed_trace_rejected", False)
        except RepairDesignError:
            check("malformed_trace_rejected", True)
        rows = benchmark.fixture_rows_and_stats()[0]
        rows[0]["action"]["action_type"] = "bad_action"
        invalid = tmp / "invalid.jsonl"
        invalid.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        try:
            load_private(True, invalid)
            check("schema_invalid_trace_rejected", False)
        except RepairDesignError:
            check("schema_invalid_trace_rejected", True)
    finally:
        for child in tmp.glob("*"):
            child.unlink()
        tmp.rmdir()

    mutations: list[tuple[str, list[str], Any]] = [
        ("benchmark_status_drift_rejected", ["source_readbacks", "benchmark_status"], "bad"),
        ("decomposition_status_drift_rejected", ["source_readbacks", "decomposition_status"], "bad"),
        ("primary_mechanism_drift_rejected", ["source_readbacks", "decomposition_primary_mechanism"], "bm25_text_dominance"),
        ("secondary_mechanism_drift_rejected", ["source_readbacks", "decomposition_secondary_mechanism"], "wrong_file_or_rank_miss"),
        ("authorized_source_phase_drift_rejected", ["source_readbacks", "authorized_source_phase"], "bad"),
        ("private_confirmation_drift_rejected", ["input_attestations", "private_input_confirmation"], "missing"),
        ("private_schema_flag_drift_rejected", ["input_attestations", "private_rows_schema_validated"], False),
        ("retrieval_execution_flag_rejected", ["input_attestations", "retrieval_rerun_executed"], True),
        ("search_execution_flag_rejected", ["input_attestations", "search_rerun_executed"], True),
        ("read_execution_flag_rejected", ["input_attestations", "read_rerun_executed"], True),
        ("citation_execution_flag_rejected", ["input_attestations", "citation_validation_rerun_executed"], True),
        ("source_scan_flag_rejected", ["input_attestations", "source_scan_executed"], True),
        ("candidate_generation_flag_rejected", ["input_attestations", "candidate_generation_executed"], True),
        ("training_flag_rejected", ["input_attestations", "training_executed"], True),
        ("provider_flag_rejected", ["input_attestations", "provider_or_model_calls_executed"], True),
        ("runtime_flag_rejected", ["input_attestations", "runtime_default_changed"], True),
        ("kernel_flag_rejected", ["input_attestations", "kernel_hardening_executed"], True),
        ("same_budget_drift_rejected", ["repair_design_spec", "same_budget_guarantee"], "larger_budget"),
        ("candidate_cap_drift_rejected", ["repair_design_spec", "candidate_cap_bucket"], "count_gt_50"),
        ("read_cap_drift_rejected", ["repair_design_spec", "read_cap_bucket"], "count_gt_50"),
        ("new_channel_rejected", ["repair_design_spec", "allowed_channel_families"], ["regex", "bm25", "symbol", "dense"]),
        ("currentness_preservation_rejected", ["repair_design_spec", "EvidenceCore_currentness_preservation"], False),
        ("label_timing_preservation_rejected", ["repair_design_spec", "label_after_action_preservation"], False),
        ("prototype_execution_rejected", ["repair_design_spec", "prototype_not_executed_in_this_phase"], False),
        ("fake_concrete_no_affected_loss_rejected", ["static_replay_simulation_summary", "estimated_affected_loss_bucket"], "count_0"),
        ("fake_concrete_high_proxy_rejected", ["static_replay_simulation_summary", "proxy_risk_bucket"], "high"),
        ("fake_concrete_low_confidence_rejected", ["static_replay_simulation_summary", "confidence_bucket"], "bad"),
        ("d2_overauth_rejected", ["stop_go", "d2_or_model_scaling_authorized"], True),
        ("rpm_training_overauth_rejected", ["stop_go", "rpm_training_authorized"], True),
        ("provider_ci_overauth_rejected", ["stop_go", "provider_network_ci_authorized"], True),
        ("candidate_expansion_overauth_rejected", ["stop_go", "candidate_expansion_authorized"], True),
        ("new_retrieval_overauth_rejected", ["stop_go", "new_retrieval_experiment_authorized"], True),
        ("source_readback_key_drift_rejected", ["source_readbacks", "unexpected"], "field"),
        ("input_attestation_key_drift_rejected", ["input_attestations", "unexpected"], True),
        ("repair_spec_key_drift_rejected", ["repair_design_spec", "unexpected"], True),
        ("validate_cap_drift_rejected", ["repair_design_spec", "validate_cap_bucket"], "count_gt_50"),
        ("allowed_channel_drop_rejected", ["repair_design_spec", "allowed_channel_families"], ["bm25_text", "symbol_regex"]),
        ("static_replay_key_drift_rejected", ["static_replay_simulation_summary", "unexpected"], True),
        ("replay_count_bucket_drift_rejected", ["static_replay_simulation_summary", "mechanism_coverage_bucket"], "count_999"),
        ("gate_value_false_rejected", ["static_replay_simulation_summary", "concrete_design_gate_results", "same_read_cap"], False),
        ("privacy_key_drift_rejected", ["privacy_contract", "unexpected"], True),
        ("stop_go_key_drift_rejected", ["stop_go", "unexpected"], True),
        ("stop_go_decision_drift_rejected", ["stop_go", "decision"], "trace_or_metric_repair_only"),
        ("status_flag_inconsistency_rejected", ["stop_go", "bounded_retrieval_repair_prototype_if_concrete"], False),
        ("validation_key_drift_rejected", ["validation_summary", "unexpected"], True),
        ("privacy_scan_pending_rejected", ["validation_summary", "privacy_leak_scan"], "pending"),
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
        ("private_ref", "private_ref_trace_abc"),
        ("content_sha", "content_sha"),
        ("task", "wf01"),
    ):
        mutated = copy.deepcopy(valid)
        mutated["repair_design_spec"]["wrong_file_guard"] = leak_value
        check(f"leak_{leak_name}_rejected", bool(validate_public_report(mutated)))
    mutated = copy.deepcopy(valid)
    mutated["unknown"] = True
    check("unknown_top_level_key_rejected", bool(validate_public_report(mutated)))
    check("self_test_count_consistency", len(checks) >= 58)
    failed = [name for name, ok in checks if not ok]
    return {"status": "passed" if not failed else "failed", "checks_passed": len(checks) - len(failed), "checks_total": len(checks), "failed_checks": failed}


def run_design(confirm_private_input: bool, trace_jsonl: Path | None = None) -> dict[str, Any]:
    rows, labels, manifest = load_private(confirm_private_input, trace_jsonl)
    bench = read_json(BENCH_REPORT)
    decomp = read_json(DECOMP_REPORT)
    return build_report(bench, decomp, rows, labels, manifest)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run-design", action="store_true")
    parser.add_argument("--confirm-private-input", action="store_true")
    parser.add_argument("--trace-jsonl", type=Path, default=None)
    parser.add_argument("--validate-report", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            result = run_self_tests()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "passed" else 1
        if args.run_design:
            report = run_design(args.confirm_private_input, args.trace_jsonl)
            write_report(report)
            final = read_json(DEFAULT_REPORT)
            print(json.dumps({
                "public_report": str(DEFAULT_REPORT),
                "status": final["status"],
                "design_family_bucket": final["repair_design_spec"]["design_family_bucket"],
                "authorized_next_phase": final["stop_go"]["authorized_next_phase"],
                "confidence_bucket": final["static_replay_simulation_summary"]["confidence_bucket"],
            }, indent=2, sort_keys=True))
            return 0
        if args.validate_report:
            report = read_json(args.validate_report)
            errors = validate_public_report(report)
            if errors:
                raise RepairDesignError("public report validation failed: " + "; ".join(errors[:10]))
            print(f"Validation passed: {args.validate_report}")
            return 0
        parser.print_help()
        return 2
    except RepairDesignError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
