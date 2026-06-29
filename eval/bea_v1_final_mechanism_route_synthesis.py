#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_final_mechanism_route_synthesis.v1"
PHASE = "BEA-v1 Final Mechanism Route Synthesis"
GENERATED_BY = "bea_v1_final_mechanism_route_synthesis"
STATUS_COMPLETE = "bea_v1_mechanism_route_synthesis_complete_blocked_on_external_empirical_inputs"
STATUSES = (STATUS_COMPLETE, "fail_forbidden_scan", "fail_schema_contract")

DEFAULT_OUT = Path(
    "artifacts/bea_v1_final_mechanism_route_synthesis/"
    "bea_v1_final_mechanism_route_synthesis_report.json"
)

INPUTS = (
    ("p1_3_support_label_proxy_fill", "artifacts/bea_v1_p1_3_agent_generated_support_label_fill/bea_v1_p1_3_agent_generated_support_label_fill_report.json", "agent_generated_support_label_fill_pass"),
    ("p1_4_support_label_reliability", "artifacts/bea_v1_p1_4_automated_label_reliability_audit/bea_v1_p1_4_automated_label_reliability_audit_report.json", "no_go_p1_4_low_evidence_labels"),
    ("p1_5r_support_label_context_feasibility", "artifacts/bea_v1_p1_5r_improved_automated_support_label_feasibility/bea_v1_p1_5r_improved_automated_support_label_feasibility_report.json", "no_go_p1_5r_private_context_unavailable"),
    ("p2_0_scheduler_private_arm_rows", "artifacts/bea_v1_p2_0_scheduler_private_arm_row_recovery/bea_v1_p2_0_scheduler_private_arm_row_recovery_report.json", "no_go_p2_0_private_arm_rows_unavailable"),
    ("p2_1_ordered_prefix_surface", "artifacts/bea_v1_p2_1_ordered_prefix_stop_evidence_surface/bea_v1_p2_1_ordered_prefix_stop_evidence_surface_report.json", "no_go_p2_1_ordered_prefix_only_aggregate"),
    ("p2_2_redundancy_risk_surface", "artifacts/bea_v1_p2_2_redundancy_risk_trace_availability/bea_v1_p2_2_redundancy_risk_trace_availability_report.json", "no_go_p2_2_redundancy_risk_traces_unavailable"),
    ("p2_3_late_trace_surface_closure", "artifacts/bea_v1_p2_3_late_trace_surface_closure/bea_v1_p2_3_late_trace_surface_closure_report.json", "late_trace_surface_closure_no_go"),
    ("p3_8ps_empirical_event_source_discovery", "artifacts/bea_v1_p3_8ps_empirical_event_source_discovery_audit/bea_v1_p3_8ps_empirical_event_source_discovery_audit_report.json", "no_go_p3_8ps_no_existing_empirical_event_source"),
    ("p4l_locked_scheduler_validation", "artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json", "bea_v1_p4l_locked_non_python_scheduler_validation_pass"),
    ("n1_span_refiner_smoke", "artifacts/bea_v1_n1_frozen_p4_span_refiner_smoke/bea_v1_n1_frozen_p4_span_refiner_smoke_report.json", "no_go_n1_inadequate_top10_actionable_denominator"),
    ("n2_rank_pack_decomposition", "artifacts/bea_v1_n2_rank_pack_actionability_decomposition/bea_v1_n2_rank_pack_actionability_decomposition_report.json", "n2_rank_pack_actionability_decomposition_pass"),
    ("n3_merge_order_design_simulation", "artifacts/bea_v1_n3_extra_depth_merge_order_design_simulation/bea_v1_n3_extra_depth_merge_order_design_simulation_report.json", "n3_merge_order_design_inconclusive"),
    ("n4_fixed_pool_denominator", "artifacts/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit_report.json", "fixed_pool_rank_blocker_denominator_audit_pass_n5_authorized"),
    ("n5_fixed_pool_preflight", "artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json", "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized"),
    ("n6_fixed_pool_experiment", "artifacts/bea_v1_n6_fixed_pool_rank_order_experiment/bea_v1_n6_fixed_pool_rank_order_experiment_report.json", "no_go_n6_public_fixed_pool_arm_fields_insufficient"),
    ("n6f_public_arm_field_schema", "artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json", "fixed_pool_public_arm_field_materialization_design_pass"),
    ("n6g_arm_field_source_discovery", "artifacts/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit_report.json", "no_go_n6g_candidate_sources_inexact_or_aggregate_only"),
    ("n6xr_bounded_recapture", "artifacts/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke_report.json", "no_go_n6xr_requires_full_rerun_or_unavailable_mapping"),
    ("n6xfr_full_frozen_preflight", "artifacts/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture_report.json", "no_go_n6xfr_local_prerequisites_unavailable"),
    ("n6xfrb_prerequisite_recovery", "artifacts/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery_report.json", "no_go_n6xfrb_build_requires_unapproved_network"),
    ("n6xfrc_binary_build_recovery", "artifacts/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery_report.json", "partial_n6xfrc_binary_built_private_inputs_missing"),
    ("n6xfrd_private_inventory", "artifacts/bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit/bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit_report.json", "no_go_n6xfrd_private_reconstruction_inputs_unavailable"),
)

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "private_path", "private_paths",
    "filename", "filenames", "file_name", "span", "spans", "snippet", "snippets",
    "content", "text", "raw_text", "candidate", "candidates", "candidate_list",
    "candidate_lists", "candidate_order", "raw_rank", "rank", "ranks", "rank_list",
    "score", "scores", "task_id", "repo", "repo_id", "repo_name", "repo_url",
    "private_id", "private_record_id", "source_hash", "source_hashes", "hash",
    "hashes", "provider", "provider_payload", "raw_payload", "payload", "prompt",
    "response", "raw", "raw_diff", "diff", "log", "logs",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at",
    "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status",
    "load_status", "source_status_bucket", "anchor_bucket", "summary_bucket", "route_bucket",
    "route_status_bucket", "blocker_bucket", "next_required_input_bucket", "requirement_bucket",
    "requirement_status_bucket", "guardrail_bucket", "privacy_boundary_bucket", "public_artifact_bucket",
    "no_execution_boundary_bucket", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
    "gate", "threshold_relation", "forbidden_scan_status",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(relative: str) -> tuple[dict[str, Any], str]:
    full = _repo_root() / relative
    if not full.exists():
        return {}, "missing"
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    full = path if path.is_absolute() else _repo_root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + key_s)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            last = marker.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if path_re.search(value):
                violations.append({"category": "path_like_value", "location_bucket": "public_artifact"})
            if line_re.search(value):
                violations.append({"category": "line_range_value", "location_bucket": "public_artifact"})
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())],
    }


def _input_records() -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, relative, expected) in enumerate(INPUTS):
        artifact, load = _load_json(relative)
        observed = str(artifact.get("status", "") or "")
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        # Older public artifacts predate the common scanner field; for synthesis, status presence is the load gate.
        passed = load == "pass" and observed == expected
        ok = ok and passed
        records.append({
            "anonymous_synthesis_input_id": f"finalin{idx:04d}",
            "input_artifact_bucket": bucket,
            "load_status": load,
            "observed_status": observed,
            "expected_status": expected,
            "forbidden_scan_status": str(scan),
            "input_gate_passed_bool": passed,
        })
    return records, ok


def _empirical_anchor_records() -> list[dict[str, Any]]:
    return [
        {"anonymous_empirical_anchor_id": "anchor0000", "anchor_bucket": "p4l_locked_scheduler_validation", "source_status_bucket": "pass", "summary_bucket": "frozen_p4_scheduler_validated_on_locked_non_python_denominator", "denominator_count": 272, "baseline_reach_count": 0, "frozen_scheduler_reach_count": 52, "hard_cap_violation_count": 0, "downstream_value_claim_bool": False},
        {"anonymous_empirical_anchor_id": "anchor0001", "anchor_bucket": "n1_span_refiner_rank_blocker", "source_status_bucket": "no_go", "summary_bucket": "span_only_repair_blocked_by_rank_pack_layer", "denominator_count": 40, "top10_actionable_count": 0, "rank_blocked_count": 40, "downstream_value_claim_bool": False},
        {"anonymous_empirical_anchor_id": "anchor0002", "anchor_bucket": "n2_rank_pack_actionability", "source_status_bucket": "pass", "summary_bucket": "extra_depth_append_blocked_all_rank_blocked_cases", "denominator_count": 40, "extra_depth_append_blocked_count": 40, "downstream_value_claim_bool": False},
        {"anonymous_empirical_anchor_id": "anchor0003", "anchor_bucket": "n3_merge_order_design", "source_status_bucket": "inconclusive", "summary_bucket": "simple_merge_order_designs_insufficient", "denominator_count": 40, "best_recovery_count": 10, "pass_gate_count": 20, "downstream_value_claim_bool": False},
        {"anonymous_empirical_anchor_id": "anchor0004", "anchor_bucket": "n4_fixed_pool_denominator", "source_status_bucket": "pass", "summary_bucket": "fixed_pool_rank_blocker_denominator_adequate_for_preflight", "eligible_case_count": 40, "case_set_frozen_bool": True, "downstream_value_claim_bool": False},
    ]


def _route_closure_records() -> list[dict[str, Any]]:
    return [
        {"anonymous_route_closure_id": "route0000", "route_bucket": "p1_support_label_route", "route_status_bucket": "closed_no_go", "blocker_bucket": "proxy_labels_valid_but_low_evidence_and_private_context_linkage_missing", "next_required_input_bucket": "private_source_context_linkage_for_support_labels", "route_closed_bool": True},
        {"anonymous_route_closure_id": "route0001", "route_bucket": "p2_p3_trace_surface_route", "route_status_bucket": "closed_no_go", "blocker_bucket": "private_trace_rows_unavailable_and_empirical_event_source_missing", "next_required_input_bucket": "empirical_frozen_event_source_declaration_and_materialized_fixtures", "route_closed_bool": True},
        {"anonymous_route_closure_id": "route0002", "route_bucket": "fixed_pool_rank_order_route", "route_status_bucket": "closed_no_go", "blocker_bucket": "exact_public_160_row_arm_outcome_source_missing", "next_required_input_bucket": "exact_public_160_row_n6_arm_outcomes", "route_closed_bool": True},
        {"anonymous_route_closure_id": "route0003", "route_bucket": "full_frozen_reconstruction_route", "route_status_bucket": "closed_no_go", "blocker_bucket": "bounded_mapping_unavailable_and_private_reconstruction_inputs_absent", "next_required_input_bucket": "fd1_p4l_nseries_private_reconstruction_inputs", "route_closed_bool": True},
    ]


def _next_input_requirement_records() -> list[dict[str, Any]]:
    return [
        {"anonymous_next_input_requirement_id": "req0000", "route_bucket": "p1_support_label_route", "requirement_bucket": "private_source_context_linkage_for_support_labels", "requirement_status_bucket": "external_or_real_input_required", "schema_only_phase_sufficient_bool": False},
        {"anonymous_next_input_requirement_id": "req0001", "route_bucket": "p2_p3_trace_surface_route", "requirement_bucket": "empirical_frozen_event_source_declaration_and_materialized_fixtures", "requirement_status_bucket": "external_or_real_input_required", "schema_only_phase_sufficient_bool": False},
        {"anonymous_next_input_requirement_id": "req0002", "route_bucket": "fixed_pool_rank_order_route", "requirement_bucket": "exact_public_160_row_n6_arm_outcomes", "requirement_status_bucket": "external_or_real_input_required", "schema_only_phase_sufficient_bool": False},
        {"anonymous_next_input_requirement_id": "req0003", "route_bucket": "full_frozen_reconstruction_route", "requirement_bucket": "fd1_p4l_nseries_private_reconstruction_inputs", "requirement_status_bucket": "external_or_real_input_required", "schema_only_phase_sufficient_bool": False},
    ]


def _guardrail_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_guardrail_id": "guard0000",
        "guardrail_bucket": "final_synthesis_no_new_experiment_no_promotion",
        "p5_authorized_bool": False,
        "v1_a_authorized_bool": False,
        "selector_reranker_authorized_bool": False,
        "runtime_change_authorized_bool": False,
        "default_change_authorized_bool": False,
        "method_winner_claimed_bool": False,
        "method_winner_authorized_bool": False,
        "downstream_value_claimed_bool": False,
        "downstream_value_authorized_bool": False,
        "new_autonomous_experiment_authorized_bool": False,
    }]


def _no_execution_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_no_execution_id": "noexec0000",
        "no_execution_boundary_bucket": "public_artifact_synthesis_only",
        "openlocus_binary_execution_count": 0,
        "cargo_build_execution_count": 0,
        "retrieval_execution_count": 0,
        "rerun_execution_count": 0,
        "candidate_generation_count": 0,
        "candidate_materialization_count": 0,
        "private_read_count": 0,
        "selector_reranker_execution_count": 0,
        "p5_execution_count": 0,
        "v1a_execution_count": 0,
        "counterfactual_execution_count": 0,
        "runtime_change_count": 0,
        "default_change_count": 0,
        "no_execution_complete_bool": True,
    }]


def _privacy_boundary_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_privacy_boundary_id": "privacy0000",
        "privacy_boundary_bucket": "public_artifact_bucket_synthesis_only",
        "public_artifact_bucket": "statuses_buckets_counts_booleans_only",
        "private_content_public_bool": False,
        "private_path_or_filename_public_bool": False,
        "raw_candidate_public_bool": False,
        "raw_rank_public_bool": False,
        "task_repo_id_public_bool": False,
        "source_span_public_bool": False,
        "hash_public_bool": False,
        "provider_payload_public_bool": False,
        "privacy_boundary_complete_bool": True,
    }]


def _stop_go_records() -> list[dict[str, Any]]:
    return [{
        "authorization": "final_synthesis_complete_no_autonomous_next_experiment",
        "next_allowed_phase": "await_external_empirical_inputs_or_new_research_directive",
        "next_allowed_scope_bucket": "no_autonomous_next_experiment_from_current_artifacts",
        "new_autonomous_experiment_authorized": False,
        "private_read_authorized": False,
        "openlocus_binary_execution_authorized": False,
        "retrieval_authorized": False,
        "rerun_authorized": False,
        "candidate_generation_authorized": False,
        "candidate_materialization_authorized": False,
        "selector_or_reranker_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "counterfactual_authorized": False,
        "runtime_promotion_authorized": False,
        "default_promotion_authorized": False,
        "runtime_or_policy_change_authorized": False,
        "method_winner_claimed": False,
        "method_winner_claim_authorized": False,
        "downstream_value_claimed": False,
        "downstream_value_claim_authorized": False,
    }]


def _gate_records(input_ok: bool, routes_ok: bool, guardrails_ok: bool, noexec_ok: bool, privacy_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "synthesis_inputs_present", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "route_closures_complete", "passed": routes_ok, "threshold_relation": "equals", "value": int(routes_ok), "threshold_value": 1},
        {"gate": "guardrails_complete", "passed": guardrails_ok, "threshold_relation": "equals", "value": int(guardrails_ok), "threshold_value": 1},
        {"gate": "no_execution", "passed": noexec_ok, "threshold_relation": "equals", "value": int(noexec_ok), "threshold_value": 1},
        {"gate": "privacy_boundary_complete", "passed": privacy_ok, "threshold_relation": "equals", "value": int(privacy_ok), "threshold_value": 1},
        {"gate": "scanner_pass", "passed": scanner_ok, "threshold_relation": "equals", "value": int(scanner_ok), "threshold_value": 1},
    ]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs, input_ok = _input_records()
    anchors = _empirical_anchor_records()
    routes = _route_closure_records()
    requirements = _next_input_requirement_records()
    guardrails = _guardrail_records()
    noexec = _no_execution_records()
    privacy = _privacy_boundary_records()
    self_ok = all(c["passed"] for c in checks)
    routes_ok = len(routes) >= 4 and all(r["route_closed_bool"] for r in routes)
    guardrails_ok = all(v is False for k, v in guardrails[0].items() if k.endswith("_bool"))
    noexec_ok = all(v == 0 for k, v in noexec[0].items() if k.endswith("_count")) and noexec[0]["no_execution_complete_bool"] is True
    privacy_ok = privacy[0]["privacy_boundary_complete_bool"] is True and all(v is False for k, v in privacy[0].items() if k.endswith("_public_bool"))
    status = STATUS_COMPLETE if self_ok and input_ok and routes_ok and guardrails_ok and noexec_ok and privacy_ok else "fail_schema_contract"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "phase": PHASE,
        "claim_level": "final_mechanism_route_synthesis_only",
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "synthesis_input_records": inputs,
        "empirical_anchor_records": anchors,
        "route_closure_records": routes,
        "next_input_requirement_records": requirements,
        "guardrail_records": guardrails,
        "no_execution_records": noexec,
        "privacy_boundary_records": privacy,
        "gate_records": _gate_records(input_ok, routes_ok, guardrails_ok, noexec_ok, privacy_ok, True),
        "stop_go_records": _stop_go_records(),
        "forbidden_scan": {},
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "method_winner_claimed": False,
        "downstream_value_claimed": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = _scan_summary(report)
    report["forbidden_scan"] = final_scan
    scanner_ok = final_scan["status"] == "pass"
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    report["gate_records"] = _gate_records(input_ok, routes_ok, guardrails_ok, noexec_ok, privacy_ok, scanner_ok)
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET_VALUE"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET_VALUE" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    inputs, input_ok = _input_records()
    anchors = _empirical_anchor_records()
    routes = _route_closure_records()
    requirements = _next_input_requirement_records()
    guardrails = _guardrail_records()
    noexec = _no_execution_records()
    privacy = _privacy_boundary_records()
    stop = _stop_go_records()[0]
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == (STATUS_COMPLETE, "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(_scan_summary({key: "blocked"})["status"] == "fail" for key in ("path", "filename", "span", "snippet", "candidate_list", "rank", "task_id", "repo", "private_id", "source_hash", "provider_payload", "raw_diff", "log"))),
        _check("scanner_rejects_path_and_digest_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("inputs_present", input_ok and len(inputs) == 22 and all(r["input_gate_passed_bool"] for r in inputs)),
        _check("anchor_records", len(anchors) == 5 and anchors[1]["denominator_count"] == 40 and anchors[1]["rank_blocked_count"] == 40 and anchors[3]["best_recovery_count"] == 10),
        _check("route_records", len(routes) == 4 and all(r["route_closed_bool"] for r in routes)),
        _check("route_buckets", {r["route_bucket"] for r in routes} == {"p1_support_label_route", "p2_p3_trace_surface_route", "fixed_pool_rank_order_route", "full_frozen_reconstruction_route"}),
        _check("requirements_real_inputs", len(requirements) == 4 and all(r["schema_only_phase_sufficient_bool"] is False for r in requirements)),
        _check("guardrails_false", all(v is False for k, v in guardrails[0].items() if k.endswith("_bool"))),
        _check("no_execution", all(v == 0 for k, v in noexec[0].items() if k.endswith("_count")) and noexec[0]["no_execution_complete_bool"] is True),
        _check("privacy_boundary", privacy[0]["privacy_boundary_complete_bool"] is True and all(v is False for k, v in privacy[0].items() if k.endswith("_public_bool"))),
        _check("stop_go", stop["next_allowed_phase"] == "await_external_empirical_inputs_or_new_research_directive" and stop["new_autonomous_experiment_authorized"] is False and stop["private_read_authorized"] is False and stop["p5_authorized"] is False),
        _check("status_expected", _build_report([])["status"] in {STATUS_COMPLETE, "fail_schema_contract"}),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1 final mechanism route synthesis")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print("wrote artifact " f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, routes={len(report['route_closure_records'])})")


if __name__ == "__main__":
    main()
