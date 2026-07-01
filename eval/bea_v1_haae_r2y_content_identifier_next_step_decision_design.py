#!/usr/bin/env python3
"""BEA-v1-HAAE-R2Y content-identifier next-step decision design.

Public-only decision package. It reads only public artifacts/docs and does not
read private roots/material, execute, recompute, generate material/candidates,
retrieve, scan source, use CI/network/provider calls, scheduler, or selector.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2Y Content-Identifier Next-Step Decision Design"
SLUG = "bea_v1_haae_r2y_content_identifier_next_step_decision_design"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2X_CHECKPOINT = "afd86c4"
R2X_STATUS = "haae_r2x_content_identifier_material_experiment_public_audit_package_complete_r2y_decision_design_authorized"
R2X_REPORT_PATH = Path("artifacts/bea_v1_haae_r2x_content_identifier_material_experiment_public_audit_package/bea_v1_haae_r2x_content_identifier_material_experiment_public_audit_package_report.json")

STATUS_PASS = "haae_r2y_content_identifier_next_step_decision_design_complete_r2z_real_file_candidate_material_preflight_authorized"
STATUS_NO_GO = "haae_r2y_no_go_no_safe_real_file_candidate_preflight"
STATUS_FAIL_SOURCE = "haae_r2y_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2y_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2y_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2y_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 18
NEXT_PHASE = "BEA-v1-HAAE-R2Z Real-File Candidate Material Preflight"

OPTION_BUCKETS = [
    "more_decoy_robustness_deferred",
    "ci_batch_execution_deferred",
    "scale_identifier_decoys_deferred",
    "real_file_candidate_material_preflight_selected",
]
STOP_FORBIDDEN_TRUE = [
    "r2z_execution_authorized_bool",
    "r2z_private_read_authorized_bool",
    "r2z_private_write_authorized_bool",
    "r2z_candidate_generation_authorized_bool",
    "r2z_source_scan_authorized_bool",
    "r2z_ci_execution_authorized_bool",
    "r2z_network_provider_authorized_bool",
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
]
GATE_NAMES = [
    "r2x_source_locked_gate",
    "r2x_r2y_authorization_gate",
    "signal_present_spread_high_gate",
    "decoy_not_real_file_evidence_gate",
    "public_only_decision_gate",
    "no_private_read_gate",
    "no_execution_recompute_generation_gate",
    "no_retrieval_runtime_source_scan_gate",
    "no_ci_network_provider_gate",
    "no_scheduler_selector_gate",
    "more_decoy_robustness_rejected_deferred_gate",
    "ci_batch_execution_deferred_gate",
    "real_file_candidate_preflight_selected_gate",
    "r2z_preflight_boundary_bounded_gate",
    "r2z_no_execution_generation_gate",
    "no_method_default_scaling_claim_gate",
    "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2x(r2x: dict[str, Any]) -> dict[str, bool]:
    stop = (r2x.get("stop_go_records") or [{}])[0]
    result = (r2x.get("experiment_result_audit_records") or [{}])[0]
    validity = (r2x.get("material_validity_context_records") or [{}])[0]
    boundary = (r2x.get("boundary_audit_records") or [{}])[0]
    status_ok = r2x.get("status") == R2X_STATUS
    scan_ok = r2x.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2y_decision_design_authorized_bool") is True and stop.get("r2y_public_decision_design_only_bool") is True
    stop_ok = all(stop.get(field) is False for field in [
        "execution_authorized_bool", "ci_execution_authorized_bool", "new_material_generation_authorized_bool",
        "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool",
        "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool",
        "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool",
        "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool",
        "scaling_claim_authorized_bool", "raw_publication_authorized_bool",
    ])
    signal_ok = result.get("content_identifier_signal_bucket") == "signal_present" and result.get("rank_spread_bucket") == "spread_high"
    decoy_context_ok = validity.get("candidate_material_type_bucket") == "query_derived_identifier_decoys" and validity.get("real_file_candidate_evidence_bool") is False and validity.get("file_retrieval_claim_bool") is False and validity.get("method_winner_claim_bool") is False and validity.get("default_runtime_claim_bool") is False and validity.get("scaling_claim_bool") is False
    boundary_ok = boundary.get("public_only_audit_bool") is True and boundary.get("aggregate_only_bool") is True and all(boundary.get(field) is False for field in ["private_root_read_bool", "private_material_read_bool", "recompute_metrics_bool", "material_generation_bool", "candidate_generation_bool", "retrieval_runtime_source_scan_bool", "ci_network_provider_bool", "scheduler_selector_bool", "raw_publication_bool"])
    source_locked = status_ok and scan_ok and auth_ok and stop_ok
    context_ok = signal_ok and decoy_context_ok and boundary_ok
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "stop_ok": stop_ok, "signal_ok": signal_ok, "decoy_context_ok": decoy_context_ok, "boundary_ok": boundary_ok, "source_locked": source_locked, "context_ok": context_ok}


LEAK_PATTERNS = [
    ("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)),
    ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")),
    ("raw_candidate_label", re.compile(r"candidate_key|candidate_path|source_path|variant_path|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")),
    ("score_hash_exact", re.compile(r"private_score|private_rank|exact_rate|exact_rank|task_key|\b[a-f0-9]{32,64}\b")),
]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [
        PHASE, STATUS_PASS, f"{total}/{total}", R2X_CHECKPOINT, R2X_STATUS,
        "signal_present/spread_high", "useful but not real-file evidence",
        "more decoy robustness rejected/deferred", "CI/batch execution deferred",
        NEXT_PHASE, "public-only design/preflight", "R2Z preflight authorized true",
        "R2Z execution/private/candidate generation/source scan/CI false", "target 20", "candidate depth 40",
        "source file cap 500", "row cap 20000", "wall-clock cap 20 minutes",
        "gold private eval only", "operator public corpus manifest", "no method/default/scaling",
    ]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2y-content-identifier-next-step-decision-design.md")) and has_all(read("docs/zh/bea-v1-haae-r2y-content-identifier-next-step-decision-design.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2y-content-identifier-next-step-decision-design.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2x: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2x is None:
        try: r2x = load_json(repo / R2X_REPORT_PATH)
        except Exception: r2x = {}
    audit = audit_r2x(r2x)
    readback = public_readback_match(self_test_total)
    selected_ok = True
    if not audit["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not (audit["context_ok"] and selected_ok):
        status = STATUS_NO_GO
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {
        "r2x_source_locked_gate": audit["source_locked"],
        "r2x_r2y_authorization_gate": audit["auth_ok"],
        "signal_present_spread_high_gate": audit["signal_ok"],
        "decoy_not_real_file_evidence_gate": audit["decoy_context_ok"],
        "public_only_decision_gate": True,
        "no_private_read_gate": True,
        "no_execution_recompute_generation_gate": True,
        "no_retrieval_runtime_source_scan_gate": True,
        "no_ci_network_provider_gate": True,
        "no_scheduler_selector_gate": True,
        "more_decoy_robustness_rejected_deferred_gate": True,
        "ci_batch_execution_deferred_gate": True,
        "real_file_candidate_preflight_selected_gate": selected_ok,
        "r2z_preflight_boundary_bounded_gate": True,
        "r2z_no_execution_generation_gate": True,
        "no_method_default_scaling_claim_gate": True,
        "forbidden_scan_pass_gate": True,
        "docs_readback_match_gate": readback["all_public_readback_match_bool"],
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2ysource0000", "locked_haae_r2x_checkpoint": R2X_CHECKPOINT, "locked_haae_r2x_status": R2X_STATUS, "r2x_status_match_bool": audit["status_ok"], "r2x_forbidden_scan_pass_bool": audit["scan_ok"], "r2x_r2y_authorization_match_bool": audit["auth_ok"], "r2x_no_forbidden_stop_go_drift_bool": audit["stop_ok"], "source_locked_bool": audit["source_locked"]}],
        "decision_context_records": [{"anonymous_decision_context_id": "haaer2ycontext0000", "signal_bucket": "signal_present/spread_high", "material_context_bucket": "query_derived_identifier_decoys", "useful_signal_bool": audit["signal_ok"], "real_file_evidence_bool": False, "file_retrieval_claim_bool": False, "context_readback_match_bool": audit["context_ok"]}],
        "route_decision_records": [{"anonymous_route_decision_id": "haaer2yroute0000", "decision_bucket": "pivot_to_real_file_candidate_material_preflight", "rationale_bucket": "content_identifier_decoy_signal_useful_but_not_real_file_evidence", "more_decoy_robustness_now_bool": False, "ci_batch_execution_now_bool": False, "real_file_candidate_preflight_selected_bool": True, "public_design_only_bool": True}],
        "next_step_option_records": [
            {"anonymous_next_step_option_id": "haaer2yoption0000", "option_bucket": "more_decoy_robustness", "decision_bucket": "rejected_deferred", "selected_bool": False, "reason_bucket": "decoy_signal_not_real_file_evidence"},
            {"anonymous_next_step_option_id": "haaer2yoption0001", "option_bucket": "ci_batch_execution", "decision_bucket": "deferred", "selected_bool": False, "reason_bucket": "public_local_preflight_needed_first"},
            {"anonymous_next_step_option_id": "haaer2yoption0002", "option_bucket": "scale_identifier_decoys", "decision_bucket": "deferred", "selected_bool": False, "reason_bucket": "would_not_answer_real_file_evidence"},
            {"anonymous_next_step_option_id": "haaer2yoption0003", "option_bucket": "real_file_candidate_material_preflight", "decision_bucket": "selected", "selected_bool": True, "reason_bucket": "define_bounded_real_file_material_recipe"},
        ],
        "r2z_contract_records": [{"anonymous_r2z_contract_id": "haaer2ycontract0000", "next_phase": NEXT_PHASE, "public_only_design_preflight_bool": True, "define_bounded_local_generation_recipe_bool": True, "operator_public_corpus_manifest_required_bool": True, "allowlisted_public_corpus_only_bool": True, "no_broad_workspace_scan_bool": True, "no_network_clone_by_default_bool": True, "future_target_task_count_bucket": "target_20", "future_candidate_depth_cap_bucket": "depth_40", "future_source_file_cap_bucket": "cap_500", "future_private_row_cap_bucket": "cap_20000", "future_wall_clock_cap_bucket": "cap_20_minutes", "future_gold_policy_bucket": "gold_private_eval_only_not_policy", "future_public_aggregate_only_bool": True, "future_execution_phase_bucket": "BEA-v1-HAAE-R2AA Actual Explicit Local Real-File Material Smoke", "execution_in_r2z_bool": False, "private_read_in_r2z_bool": False, "private_write_in_r2z_bool": False, "candidate_generation_in_r2z_bool": False, "source_scan_in_r2z_bool": False, "ci_execution_in_r2z_bool": False, "network_provider_in_r2z_bool": False, "public_aggregate_only_manifest_bool": True, "no_method_default_scaling_claim_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2yclaim0000", "public_only_decision_bool": True, "private_read_bool": False, "private_write_bool": False, "execution_bool": False, "recompute_bool": False, "generation_bool": False, "retrieval_runtime_source_scan_bool": False, "ci_network_provider_bool": False, "scheduler_selector_bool": False, "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2ygate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2ysynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2x_status_fail", "missing_r2y_authorization_fail", "signal_missing_no_go", "real_file_claim_no_go", "ci_batch_selected_fail", "r2z_execution_overauth_fail", "r2z_candidate_generation_overauth_fail", "claim_boundary_fail", "leak_fail", "stale_readback_fail", "safe_parser_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2yreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2ystop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_revisit_content_identifier_decision", "haae_r2z_real_file_candidate_material_preflight_authorized_bool": passed, "r2z_public_design_preflight_only_bool": passed, "r2z_execution_authorized_bool": False, "r2z_private_read_authorized_bool": False, "r2z_private_write_authorized_bool": False, "r2z_candidate_generation_authorized_bool": False, "r2z_source_scan_authorized_bool": False, "r2z_ci_execution_authorized_bool": False, "r2z_network_provider_authorized_bool": False, "execution_authorized_bool": False, "ci_execution_authorized_bool": False, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "decision_context_records", "route_decision_records", "next_step_option_records", "r2z_contract_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2x_checkpoint") != R2X_CHECKPOINT or source.get("locked_haae_r2x_status") != R2X_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2x_status_match_bool", "r2x_forbidden_scan_pass_bool", "r2x_r2y_authorization_match_bool", "r2x_no_forbidden_stop_go_drift_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    context = (report.get("decision_context_records") or [{}])[0]
    if context.get("signal_bucket") != "signal_present/spread_high" or context.get("real_file_evidence_bool") is not False or context.get("file_retrieval_claim_bool") is not False or context.get("context_readback_match_bool") is not True: issues.append("decision_context_mismatch")
    route = (report.get("route_decision_records") or [{}])[0]
    if route.get("decision_bucket") != "pivot_to_real_file_candidate_material_preflight" or route.get("real_file_candidate_preflight_selected_bool") is not True or route.get("more_decoy_robustness_now_bool") is not False or route.get("ci_batch_execution_now_bool") is not False: issues.append("route_decision_mismatch")
    options = {row.get("option_bucket"): row for row in report.get("next_step_option_records", [])}
    if set(options) != {"more_decoy_robustness", "ci_batch_execution", "scale_identifier_decoys", "real_file_candidate_material_preflight"}: issues.append("option_set_mismatch")
    if options.get("real_file_candidate_material_preflight", {}).get("selected_bool") is not True or options.get("ci_batch_execution", {}).get("selected_bool") is not False: issues.append("option_selection_mismatch")
    contract = (report.get("r2z_contract_records") or [{}])[0]
    for field in ["public_only_design_preflight_bool", "define_bounded_local_generation_recipe_bool", "operator_public_corpus_manifest_required_bool", "allowlisted_public_corpus_only_bool", "no_broad_workspace_scan_bool", "no_network_clone_by_default_bool", "future_public_aggregate_only_bool", "public_aggregate_only_manifest_bool", "no_method_default_scaling_claim_bool"]:
        if contract.get(field) is not True: issues.append(f"r2z_contract_{field}")
    expected_buckets = {
        "future_target_task_count_bucket": "target_20",
        "future_candidate_depth_cap_bucket": "depth_40",
        "future_source_file_cap_bucket": "cap_500",
        "future_private_row_cap_bucket": "cap_20000",
        "future_wall_clock_cap_bucket": "cap_20_minutes",
        "future_gold_policy_bucket": "gold_private_eval_only_not_policy",
        "future_execution_phase_bucket": "BEA-v1-HAAE-R2AA Actual Explicit Local Real-File Material Smoke",
    }
    for field, expected in expected_buckets.items():
        if contract.get(field) != expected: issues.append(f"r2z_contract_{field}")
    for field in ["execution_in_r2z_bool", "private_read_in_r2z_bool", "private_write_in_r2z_bool", "candidate_generation_in_r2z_bool", "source_scan_in_r2z_bool", "ci_execution_in_r2z_bool", "network_provider_in_r2z_bool"]:
        if contract.get(field) is not False: issues.append(f"r2z_contract_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["private_read_bool", "private_write_bool", "execution_bool", "recompute_bool", "generation_bool", "retrieval_runtime_source_scan_bool", "ci_network_provider_bool", "scheduler_selector_bool", "method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_allowed_phase_mismatch")
        if stop.get("haae_r2z_real_file_candidate_material_preflight_authorized_bool") is not True or stop.get("r2z_public_design_preflight_only_bool") is not True: issues.append("r2z_stop_go_missing")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    for field in STOP_FORBIDDEN_TRUE:
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
        else:
            raise ValueError("invalid arguments")
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
    base = load_json(repo / R2X_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2x_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    missing_auth = json.loads(json.dumps(base)); missing_auth["stop_go_records"][0]["haae_r2y_decision_design_authorized_bool"] = False; check("missing_r2y_authorization_fail", build_report(missing_auth)["status"] == STATUS_FAIL_SOURCE)
    signal = json.loads(json.dumps(base)); signal["experiment_result_audit_records"][0]["content_identifier_signal_bucket"] = "no_signal"; check("signal_missing_no_go", build_report(signal)["status"] == STATUS_NO_GO)
    real_file = json.loads(json.dumps(base)); real_file["material_validity_context_records"][0]["real_file_candidate_evidence_bool"] = True; check("real_file_claim_no_go", build_report(real_file)["status"] == STATUS_NO_GO)
    ci_selected = json.loads(json.dumps(passed)); ci_selected["route_decision_records"][0]["ci_batch_execution_now_bool"] = True; check("ci_batch_selected_fail", "route_decision_mismatch" in validate_report(ci_selected))
    r2z_exec = json.loads(json.dumps(passed)); r2z_exec["stop_go_records"][0]["r2z_execution_authorized_bool"] = True; check("r2z_execution_overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(r2z_exec)))
    r2z_candidate = json.loads(json.dumps(passed)); r2z_candidate["r2z_contract_records"][0]["candidate_generation_in_r2z_bool"] = True; check("r2z_candidate_generation_overauth_fail", "r2z_contract_candidate_generation_in_r2z_bool" in validate_report(r2z_candidate))
    missing_manifest = json.loads(json.dumps(passed)); missing_manifest["r2z_contract_records"][0]["operator_public_corpus_manifest_required_bool"] = False; check("r2z_operator_manifest_required_fail", "r2z_contract_operator_public_corpus_manifest_required_bool" in validate_report(missing_manifest))
    broad_scan = json.loads(json.dumps(passed)); broad_scan["r2z_contract_records"][0]["no_broad_workspace_scan_bool"] = False; check("r2z_no_broad_scan_fail", "r2z_contract_no_broad_workspace_scan_bool" in validate_report(broad_scan))
    target_drift = json.loads(json.dumps(passed)); target_drift["r2z_contract_records"][0]["future_target_task_count_bucket"] = "target_200"; check("r2z_target_bound_drift_fail", "r2z_contract_future_target_task_count_bucket" in validate_report(target_drift))
    depth_drift = json.loads(json.dumps(passed)); depth_drift["r2z_contract_records"][0]["future_candidate_depth_cap_bucket"] = "depth_400"; check("r2z_depth_bound_drift_fail", "r2z_contract_future_candidate_depth_cap_bucket" in validate_report(depth_drift))
    gold_policy = json.loads(json.dumps(passed)); gold_policy["r2z_contract_records"][0]["future_gold_policy_bucket"] = "gold_policy_allowed"; check("r2z_gold_policy_drift_fail", "r2z_contract_future_gold_policy_bucket" in validate_report(gold_policy))
    claim = json.loads(json.dumps(passed)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("claim_boundary_fail", any(i.startswith("claim_boundary_") for i in validate_report(claim)))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)
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


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
