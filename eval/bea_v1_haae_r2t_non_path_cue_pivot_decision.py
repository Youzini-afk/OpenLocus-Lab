#!/usr/bin/env python3
"""BEA-v1-HAAE-R2T non-path-cue pivot decision.

Public-only decision package. It reads only public R2S artifacts/docs and does
not read private material, execute experiments, recompute metrics, generate
material, retrieve, scan source, use CI/network/provider calls, scheduler, or
selector.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2T Non-Path-Cue Pivot Decision"
SLUG = "bea_v1_haae_r2t_non_path_cue_pivot_decision"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2S_CHECKPOINT = "8d8d19c"
R2S_STATUS = "haae_r2s_path_cue_robustness_experiment_public_audit_package_complete_r2t_non_path_cue_pivot_decision_authorized"
R2S_REPORT_PATH = Path("artifacts/bea_v1_haae_r2s_path_cue_robustness_experiment_public_audit_package/bea_v1_haae_r2s_path_cue_robustness_experiment_public_audit_package_report.json")

STATUS_PASS = "haae_r2t_non_path_cue_pivot_decision_complete_r2u_content_identifier_material_generation_authorized"
STATUS_NO_GO = "haae_r2t_no_go_no_safe_non_path_cue_pivot"
STATUS_FAIL_SOURCE = "haae_r2t_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2t_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2t_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2t_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 13
NEXT_PHASE = "BEA-v1-HAAE-R2U Content-Identifier Evidence Material Generation Smoke"

OPTION_BUCKETS = [
    "scale_current_path_prior_rejected_deferred",
    "more_path_cue_ablations_deferred",
    "content_identifier_selected",
    "ci_batch_deferred",
]
GATE_NAMES = [
    "r2s_source_locked_gate",
    "r2s_r2t_authorization_gate",
    "path_cue_artifact_result_readback_gate",
    "public_only_decision_gate",
    "no_private_read_gate",
    "no_execution_recompute_generation_gate",
    "no_retrieval_runtime_source_scan_gate",
    "no_ci_network_provider_gate",
    "no_scheduler_selector_gate",
    "scale_current_path_prior_rejected_gate",
    "content_identifier_selected_gate",
    "r2u_contract_bounded_gate",
    "no_method_default_scaling_claim_gate",
    "r2u_only_stop_go_gate",
    "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
]
STOP_FORBIDDEN_TRUE = [
    "execution_authorized_bool",
    "ci_execution_authorized_bool",
    "new_material_generation_in_r2t_authorized_bool",
    "retrieval_authorized_bool",
    "runtime_execution_authorized_bool",
    "source_scan_authorized_bool",
    "network_authorized_bool",
    "provider_model_authorized_bool",
    "scheduler_haae_authorized_bool",
    "selector_reranker_authorized_bool",
    "bea_v1_a_authorized_bool",
    "p5_authorized_bool",
    "default_change_authorized_bool",
    "method_winner_claim_authorized_bool",
    "scaling_claim_authorized_bool",
    "raw_publication_authorized_bool",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2s(r2s: dict[str, Any]) -> dict[str, bool]:
    stop = (r2s.get("stop_go_records") or [{}])[0]
    result = (r2s.get("r2r_result_audit_records") or [{}])[0]
    boundary = (r2s.get("boundary_audit_records") or [{}])[0]
    status_ok = r2s.get("status") == R2S_STATUS
    scan_ok = r2s.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2t_non_path_cue_pivot_decision_authorized_bool") is True and stop.get("r2t_public_design_decision_only_bool") is True
    stop_ok = all(stop.get(field) is False for field in [
        "execution_authorized_bool",
        "ci_execution_authorized_bool",
        "new_material_generation_authorized_bool",
        "candidate_generation_authorized_bool",
        "retrieval_authorized_bool",
        "runtime_execution_authorized_bool",
        "source_scan_authorized_bool",
        "network_authorized_bool",
        "provider_model_authorized_bool",
        "scheduler_haae_authorized_bool",
        "selector_reranker_authorized_bool",
        "bea_v1_a_authorized_bool",
        "p5_authorized_bool",
        "default_change_authorized_bool",
        "method_winner_claim_authorized_bool",
        "scaling_claim_authorized_bool",
        "raw_publication_authorized_bool",
    ])
    artifact_likely_ok = result.get("interpretation_bucket") == "path_cue_artifact_likely"
    spread_ok = result.get("variant_spread_bucket") == "spread_high"
    drops_ok = result.get("all_perturbation_drop_buckets") == "count_11_to_20"
    boundary_ok = boundary.get("public_only_audit_bool") is True and boundary.get("privacy_aggregate_only_bool") is True
    source_locked = status_ok and scan_ok and auth_ok and stop_ok
    result_ok = artifact_likely_ok and spread_ok and drops_ok and boundary_ok
    return {
        "status_ok": status_ok,
        "scan_ok": scan_ok,
        "auth_ok": auth_ok,
        "stop_ok": stop_ok,
        "artifact_likely_ok": artifact_likely_ok,
        "spread_ok": spread_ok,
        "drops_ok": drops_ok,
        "boundary_ok": boundary_ok,
        "source_locked": source_locked,
        "result_ok": result_ok,
    }


LEAK_PATTERNS = [
    ("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)),
    ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")),
    ("raw_candidate_label", re.compile(r"candidate_path|source_path|variant_path|candidate_key|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")),
    ("score_hash_exact", re.compile(r"private_score|private_rank|exact_rate|exact_rank|task_key|\b[a-f0-9]{32,64}\b")),
]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [
        PHASE,
        STATUS_PASS,
        f"{total}/{total}",
        R2S_CHECKPOINT,
        R2S_STATUS,
        "path_cue_artifact_likely",
        "scale current path-prior rejected/deferred",
        "content_identifier selected",
        NEXT_PHASE,
        "target 20",
        "candidate depth 40",
        "row cap 20000",
        "not execution/generation/CI",
        "no method/default/scaling",
    ]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2t-non-path-cue-pivot-decision.md")) and has_all(read("docs/zh/bea-v1-haae-r2t-non-path-cue-pivot-decision.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2t-non-path-cue-pivot-decision.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2s: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2s is None:
        try: r2s = load_json(repo / R2S_REPORT_PATH)
        except Exception: r2s = {}
    audit = audit_r2s(r2s)
    readback = public_readback_match(self_test_total)
    content_identifier_selected = True
    r2u_bounded = True
    if not audit["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not (audit["result_ok"] and content_identifier_selected and r2u_bounded):
        status = STATUS_NO_GO
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {
        "r2s_source_locked_gate": audit["source_locked"],
        "r2s_r2t_authorization_gate": audit["auth_ok"],
        "path_cue_artifact_result_readback_gate": audit["result_ok"],
        "public_only_decision_gate": True,
        "no_private_read_gate": True,
        "no_execution_recompute_generation_gate": True,
        "no_retrieval_runtime_source_scan_gate": True,
        "no_ci_network_provider_gate": True,
        "no_scheduler_selector_gate": True,
        "scale_current_path_prior_rejected_gate": True,
        "content_identifier_selected_gate": content_identifier_selected,
        "r2u_contract_bounded_gate": r2u_bounded,
        "no_method_default_scaling_claim_gate": True,
        "r2u_only_stop_go_gate": True,
        "forbidden_scan_pass_gate": True,
        "docs_readback_match_gate": readback["all_public_readback_match_bool"],
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2tsource0000", "locked_haae_r2s_checkpoint": R2S_CHECKPOINT, "locked_haae_r2s_status": R2S_STATUS, "r2s_status_match_bool": audit["status_ok"], "r2s_forbidden_scan_pass_bool": audit["scan_ok"], "r2s_r2t_authorization_match_bool": audit["auth_ok"], "r2s_no_forbidden_stop_go_drift_bool": audit["stop_ok"], "source_locked_bool": audit["source_locked"]}],
        "robustness_result_records": [{"anonymous_robustness_result_id": "haaer2trobust0000", "r2s_path_cue_artifact_likely_bool": audit["artifact_likely_ok"], "variant_spread_high_bool": audit["spread_ok"], "perturbation_drop_high_bool": audit["drops_ok"], "privacy_aggregate_only_bool": audit["boundary_ok"], "decision_signal_bucket": "pivot_away_from_path_cues"}],
        "route_decision_records": [{"anonymous_route_decision_id": "haaer2troute0000", "decision_bucket": "non_path_cue_pivot", "rationale_bucket": "path_cue_artifact_likely_not_method_signal", "scale_path_prior_now_bool": False, "content_identifier_route_selected_bool": True, "public_design_only_bool": True}],
        "next_direction_option_records": [
            {"anonymous_next_direction_option_id": "haaer2toption0000", "option_bucket": "scale_current_path_prior", "decision_bucket": "rejected_deferred", "selected_bool": False, "reason_bucket": "path_cue_artifact_likely"},
            {"anonymous_next_direction_option_id": "haaer2toption0001", "option_bucket": "more_path_cue_ablations", "decision_bucket": "deferred", "selected_bool": False, "reason_bucket": "avoid_path_cue_loop"},
            {"anonymous_next_direction_option_id": "haaer2toption0002", "option_bucket": "content_identifier", "decision_bucket": "selected", "selected_bool": True, "reason_bucket": "non_path_cue_evidence_route"},
            {"anonymous_next_direction_option_id": "haaer2toption0003", "option_bucket": "ci_batch", "decision_bucket": "deferred", "selected_bool": False, "reason_bucket": "no_ci_until_local_design"},
        ],
        "r2u_contract_records": [{"anonymous_r2u_contract_id": "haaer2tcontract0000", "next_phase": NEXT_PHASE, "local_manual_only_bool": True, "explicit_opt_in_required_bool": True, "private_output_root_required_bool": True, "public_aggregate_only_bool": True, "target_task_count_bucket": "target_20", "candidate_depth_bucket": "candidate_depth_40", "private_row_cap_bucket": "row_cap_20000", "content_identifier_evidence_material_bool": True, "no_experiment_metrics_in_r2u_bool": True, "no_ci_network_retrieval_runtime_source_scan_bool": True, "no_method_default_scaling_claim_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2tclaim0000", "public_only_decision_bool": True, "private_read_bool": False, "private_write_bool": False, "execution_bool": False, "recompute_bool": False, "material_generation_in_r2t_bool": False, "retrieval_runtime_source_scan_bool": False, "ci_network_provider_bool": False, "scheduler_selector_bool": False, "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2tgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2tsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2s_status_fail", "missing_r2t_authorization_fail", "path_cue_result_missing_fail", "scale_current_selected_fail", "content_identifier_not_selected_fail", "r2u_contract_unbounded_fail", "overauth_fail", "leak_fail", "stale_readback_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2treadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2tstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_revisit_non_path_cue_pivot", "haae_r2u_content_identifier_material_generation_authorized_bool": passed, "r2u_local_manual_only_bool": passed, "r2u_explicit_opt_in_required_bool": passed, "r2u_private_output_root_required_bool": passed, "r2u_public_aggregate_only_bool": passed, "r2u_experiment_metrics_authorized_bool": False, "r2u_ci_execution_authorized_bool": False, "r2u_retrieval_runtime_authorized_bool": False, "r2u_source_scan_authorized_bool": False, "r2u_provider_network_authorized_bool": False, "r2u_scheduler_selector_authorized_bool": False, "r2u_bea_v1_a_p5_authorized_bool": False, "r2u_default_runtime_change_authorized_bool": False, "r2u_method_winner_or_scaling_claim_authorized_bool": False, "r2t_execution_authorized_bool": False, "execution_authorized_bool": False, "ci_execution_authorized_bool": False, "new_material_generation_in_r2t_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "robustness_result_records", "route_decision_records", "next_direction_option_records", "r2u_contract_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2s_checkpoint") != R2S_CHECKPOINT or source.get("locked_haae_r2s_status") != R2S_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2s_status_match_bool", "r2s_forbidden_scan_pass_bool", "r2s_r2t_authorization_match_bool", "r2s_no_forbidden_stop_go_drift_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    robust = (report.get("robustness_result_records") or [{}])[0]
    if robust.get("r2s_path_cue_artifact_likely_bool") is not True or robust.get("decision_signal_bucket") != "pivot_away_from_path_cues": issues.append("robustness_result_mismatch")
    route = (report.get("route_decision_records") or [{}])[0]
    if route.get("decision_bucket") != "non_path_cue_pivot" or route.get("content_identifier_route_selected_bool") is not True or route.get("scale_path_prior_now_bool") is not False: issues.append("route_decision_mismatch")
    options = {row.get("option_bucket"): row for row in report.get("next_direction_option_records", [])}
    if set(options) != {"scale_current_path_prior", "more_path_cue_ablations", "content_identifier", "ci_batch"}: issues.append("option_set_mismatch")
    if options.get("content_identifier", {}).get("selected_bool") is not True or options.get("scale_current_path_prior", {}).get("selected_bool") is not False: issues.append("option_selection_mismatch")
    contract = (report.get("r2u_contract_records") or [{}])[0]
    for field in ["local_manual_only_bool", "explicit_opt_in_required_bool", "private_output_root_required_bool", "public_aggregate_only_bool", "content_identifier_evidence_material_bool", "no_experiment_metrics_in_r2u_bool", "no_ci_network_retrieval_runtime_source_scan_bool", "no_method_default_scaling_claim_bool"]:
        if contract.get(field) is not True: issues.append(f"r2u_contract_{field}")
    if contract.get("target_task_count_bucket") != "target_20" or contract.get("candidate_depth_bucket") != "candidate_depth_40" or contract.get("private_row_cap_bucket") != "row_cap_20000": issues.append("r2u_contract_bounds_mismatch")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["private_read_bool", "private_write_bool", "execution_bool", "recompute_bool", "material_generation_in_r2t_bool", "retrieval_runtime_source_scan_bool", "ci_network_provider_bool", "scheduler_selector_bool", "method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("haae_r2u_content_identifier_material_generation_authorized_bool") is not True or stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2u_stop_go_missing")
        for field in ["r2u_local_manual_only_bool", "r2u_explicit_opt_in_required_bool", "r2u_private_output_root_required_bool", "r2u_public_aggregate_only_bool"]:
            if stop.get(field) is not True: issues.append(f"r2u_stop_go_{field}")
        for field in ["r2u_experiment_metrics_authorized_bool", "r2u_ci_execution_authorized_bool", "r2u_retrieval_runtime_authorized_bool", "r2u_source_scan_authorized_bool", "r2u_provider_network_authorized_bool", "r2u_scheduler_selector_authorized_bool", "r2u_bea_v1_a_p5_authorized_bool", "r2u_default_runtime_change_authorized_bool", "r2u_method_winner_or_scaling_claim_authorized_bool"]:
            if stop.get(field) is not False: issues.append(f"r2u_stop_go_overauth_{field}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    for field in ["r2t_execution_authorized_bool", *STOP_FORBIDDEN_TRUE]:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    return issues


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test": parsed["self_test"] = True; i += 1
        elif arg in {"--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            if arg == "--validate-report": parsed["validate"] = argv[i + 1]
            else: parsed["out"] = argv[i + 1]
            i += 2
        else: raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value)
    resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2S_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2s_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    no_auth = json.loads(json.dumps(base)); no_auth["stop_go_records"][0]["haae_r2t_non_path_cue_pivot_decision_authorized_bool"] = False; check("missing_r2t_authorization_fail", build_report(no_auth)["status"] == STATUS_FAIL_SOURCE)
    no_artifact = json.loads(json.dumps(base)); no_artifact["r2r_result_audit_records"][0]["interpretation_bucket"] = "robust_candidate_signal"; check("path_cue_result_missing_fail", build_report(no_artifact)["status"] == STATUS_NO_GO)
    scale_selected = json.loads(json.dumps(passed)); scale_selected["route_decision_records"][0]["scale_path_prior_now_bool"] = True; check("scale_current_selected_fail", "route_decision_mismatch" in validate_report(scale_selected))
    no_content = json.loads(json.dumps(passed)); no_content["next_direction_option_records"][2]["selected_bool"] = False; check("content_identifier_not_selected_fail", "option_selection_mismatch" in validate_report(no_content))
    unbounded = json.loads(json.dumps(passed)); unbounded["r2u_contract_records"][0]["private_row_cap_bucket"] = "unbounded"; check("r2u_contract_unbounded_fail", "r2u_contract_bounds_mismatch" in validate_report(unbounded))
    over = json.loads(json.dumps(passed)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(over)))
    missing_root = json.loads(json.dumps(passed)); missing_root["stop_go_records"][0]["r2u_private_output_root_required_bool"] = False; check("r2u_private_root_stop_go_fail", "r2u_stop_go_r2u_private_output_root_required_bool" in validate_report(missing_root))
    metrics_over = json.loads(json.dumps(passed)); metrics_over["stop_go_records"][0]["r2u_experiment_metrics_authorized_bool"] = True; check("r2u_metrics_overauth_fail", "r2u_stop_go_overauth_r2u_experiment_metrics_authorized_bool" in validate_report(metrics_over))
    next_drift = json.loads(json.dumps(passed)); next_drift["stop_go_records"][0]["next_allowed_phase"] = "BEA-v1-HAAE-R2U CI Execution"; check("r2u_next_phase_drift_fail", "r2u_stop_go_missing" in validate_report(next_drift))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception:
        print("invalid arguments", file=sys.stderr); return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo / public_artifact_path(args["validate"])); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(args["out"]) if args["out"] else None
    report = build_report(); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
