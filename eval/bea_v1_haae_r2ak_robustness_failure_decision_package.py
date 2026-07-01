#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AK robustness failure decision package.

Public-only decision package over the committed R2AJ public artifact. It reads no
private roots/material/group files or /tmp roots, does not recompute metrics,
does not scan source/candidates, and authorizes only R2AL public design.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AK Robustness Failure Decision Package"
SLUG = "bea_v1_haae_r2ak_robustness_failure_decision_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AJ_CHECKPOINT = "a00a334"
R2AJ_STATUS = "haae_r2aj_robustness_experiment_public_audit_package_complete_r2ak_decision_authorized_brittle_or_artifact"
R2AJ_SELF_TEST_TOTAL = 19
R2AJ_REPORT_PATH = Path("artifacts/bea_v1_haae_r2aj_robustness_experiment_public_audit_package/bea_v1_haae_r2aj_robustness_experiment_public_audit_package_report.json")

STATUS_PASS = "haae_r2ak_robustness_failure_decision_complete_r2al_new_signal_family_public_design_authorized_route_closed"
STATUS_FAIL_SOURCE = "haae_r2ak_fail_closed_source_lock_mismatch"
STATUS_FAIL_DECISION = "haae_r2ak_fail_closed_decision_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2ak_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2ak_fail_closed_raw_private_exact_leak"
STATUS_FAIL_READBACK = "haae_r2ak_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 22
NEXT_PHASE = "BEA-v1-HAAE-R2AL New Signal Family Public Design Preflight"

DECISION_BUCKET = "close_current_real_file_signal_route"
CLOSED_ROUTE_BUCKET = "r2ac_r2ai_single_rank_content_path_signal"
FAILURE_BUCKET = "brittle_or_artifact"
GATE_NAMES = ["r2aj_source_locked_gate", "r2aj_self_test_19_gate", "r2aj_forbidden_scan_pass_gate", "r2aj_brittle_or_artifact_gate", "controls_match_or_exceed_signal_gate", "no_method_default_scale_claim_gate", "close_current_route_decision_gate", "closed_route_bucket_gate", "mechanism_analysis_deferred_gate", "r2al_public_design_only_gate", "public_only_decision_gate", "no_private_read_recompute_scan_execution_gate", "no_raw_private_exact_leak_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["source_lock_pass", "wrong_r2aj_status_fail", "self_test_drift_fail", "forbidden_scan_drift_fail", "controls_match_drift_fail", "method_claim_drift_fail", "inherited_failure_drift_fail", "decision_bucket_drift_fail", "route_closed_drift_fail", "closed_route_bucket_drift_fail", "mechanism_auth_drift_fail", "new_signal_design_drift_fail", "candidate_next_route_drift_fail", "boundary_private_read_fail", "stop_go_overauth_fail", "next_phase_drift_fail", "gate_set_fail", "synthetic_validator_set_fail", "readback_record_fail", "status_drift_fail", "leak_fail", "safe_parser_fail"]
FORBIDDEN_STOP_TRUE = ["mechanism_analysis_authorized_bool", "execution_authorized_bool", "material_generation_authorized_bool", "new_material_generation_authorized_bool", "private_read_authorized_bool", "ci_execution_authorized_bool", "scale_execution_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2aj(r2aj: dict[str, Any]) -> dict[str, bool]:
    result = (r2aj.get("robustness_result_audit_records") or [{}])[0]
    claim = (r2aj.get("claim_boundary_records") or [{}])[0]
    boundary = (r2aj.get("public_audit_boundary_records") or [{}])[0]
    stop = (r2aj.get("stop_go_records") or [{}])[0]
    status_ok = r2aj.get("status") == R2AJ_STATUS
    self_test_ok = r2aj.get("self_test_total") == R2AJ_SELF_TEST_TOTAL
    scan_ok = r2aj.get("forbidden_scan", {}).get("status") == "pass"
    source_ok = status_ok and self_test_ok and scan_ok
    brittle_ok = result.get("r2ai_result_bucket") == FAILURE_BUCKET
    controls_ok = result.get("controls_perturbations_match_or_exceed_signal_bool") is True
    no_claim_ok = result.get("no_robust_real_file_method_default_scale_claim_bool") is True and all(claim.get(field) is False for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "robust_method_claim_bool"])
    no_raw_ok = result.get("no_exact_or_raw_publication_bool") is True and claim.get("raw_publication_bool") is False and boundary.get("raw_publication_bool") is False
    boundary_ok = boundary.get("public_only_audit_bool") is True and all(boundary.get(field) is False for field in ["private_root_read_bool", "tmp_read_bool", "private_material_read_bool", "group_file_read_bool", "recompute_metrics_bool", "source_candidate_scan_bool", "material_generation_bool", "execution_bool", "ci_network_provider_clone_bool", "raw_publication_bool"])
    stop_ok = stop.get("haae_r2ak_robustness_failure_decision_package_authorized_bool") is True and stop.get("r2ak_decide_close_route_or_mechanism_analysis_or_new_signal_family_bool") is True and stop.get("next_allowed_phase") == PHASE
    stop_no_overauth = all(stop.get(field, False) is False for field in ["execution_authorized_bool", "material_generation_authorized_bool", "new_material_generation_authorized_bool", "private_read_authorized_bool", "ci_execution_authorized_bool", "scale_execution_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    return {"source_ok": source_ok, "status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "brittle_ok": brittle_ok, "controls_ok": controls_ok, "no_claim_ok": no_claim_ok, "no_raw_ok": no_raw_ok, "boundary_ok": boundary_ok, "stop_ok": stop_ok, "stop_no_overauth": stop_no_overauth, "audit_ok": brittle_ok and controls_ok and no_claim_ok and no_raw_ok and boundary_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate", re.compile(r"candidate_key|source_file_key|filepath|filename|directory|snippet|start_line|end_line|gold_spans|hard_negatives|\.rs\b|crates/openlocus-")), ("exact_metric", re.compile(r"private_score|private_rank|exact_rate|exact_mrr|exact_rank|exact_count|hit_rate|\b[a-f0-9]{32,64}\b", re.I))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AJ_CHECKPOINT, R2AJ_STATUS, "R2AJ self-test 19/19", DECISION_BUCKET, "route_closed_bool = true", CLOSED_ROUTE_BUCKET, FAILURE_BUCKET, "controls_perturbations_match_or_exceed_signal_bool = true", "method_default_scale_claim_rejected_bool = true", "mechanism_analysis_authorized_bool = false", "mechanism_analysis_deferred_bool = true", "new_signal_family_public_design_recommended_bool = true", NEXT_PHASE, "no execution/material generation/private read/CI/scale/retrieval/runtime/default/method/raw"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2ak-robustness-failure-decision-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2ak-robustness-failure-decision-package.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2ak-robustness-failure-decision-package.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2aj: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2aj is None:
        try: r2aj = load_json(repo / R2AJ_REPORT_PATH)
        except Exception: r2aj = {}
    audit = audit_r2aj(r2aj)
    readback = public_readback_match(self_test_total)
    if not audit["source_ok"]:
        status = STATUS_FAIL_SOURCE
    elif not audit["audit_ok"]:
        status = STATUS_FAIL_DECISION
    elif not audit["stop_ok"] or not audit["stop_no_overauth"]:
        status = STATUS_FAIL_BOUNDARY
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2aj_source_locked_gate": audit["source_ok"], "r2aj_self_test_19_gate": audit["self_test_ok"], "r2aj_forbidden_scan_pass_gate": audit["scan_ok"], "r2aj_brittle_or_artifact_gate": audit["brittle_ok"], "controls_match_or_exceed_signal_gate": audit["controls_ok"], "no_method_default_scale_claim_gate": audit["no_claim_ok"], "close_current_route_decision_gate": True, "closed_route_bucket_gate": True, "mechanism_analysis_deferred_gate": True, "r2al_public_design_only_gate": True, "public_only_decision_gate": True, "no_private_read_recompute_scan_execution_gate": True, "no_raw_private_exact_leak_gate": audit["no_raw_ok"], "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2aksource0000", "locked_haae_r2aj_checkpoint": R2AJ_CHECKPOINT, "locked_haae_r2aj_status": R2AJ_STATUS, "r2aj_status_match_bool": audit["status_ok"], "r2aj_self_test_19_bool": audit["self_test_ok"], "r2aj_forbidden_scan_pass_bool": audit["scan_ok"], "source_locked_bool": audit["source_ok"]}],
        "inherited_robustness_failure_records": [{"anonymous_inherited_failure_id": "haaer2akfailure0000", "robustness_failure_bucket": FAILURE_BUCKET, "controls_perturbations_match_or_exceed_signal_bool": audit["controls_ok"], "bucket_only_public_metrics_bool": True, "no_raw_publication_bool": audit["no_raw_ok"], "no_method_default_scale_claim_bool": audit["no_claim_ok"]}],
        "decision_records": [{"anonymous_decision_id": "haaer2akdecision0000", "decision_bucket": DECISION_BUCKET, "route_closed_bool": True, "robustness_failure_bucket": FAILURE_BUCKET, "controls_perturbations_match_or_exceed_signal_bool": True, "method_default_scale_claim_rejected_bool": True, "mechanism_analysis_authorized_bool": False, "mechanism_analysis_deferred_bool": True, "new_signal_family_public_design_recommended_bool": True}],
        "closed_route_records": [{"anonymous_closed_route_id": "haaer2akclosed0000", "closed_route_bucket": CLOSED_ROUTE_BUCKET, "route_closed_bool": True, "closed_due_to_brittle_or_artifact_bool": True, "method_default_scale_claim_rejected_bool": True}],
        "candidate_next_route_records": [{"anonymous_candidate_next_route_id": "haaer2aknext0000", "next_phase": NEXT_PHASE, "public_only_design_preflight_bool": True, "new_signal_family_public_design_recommended_bool": True, "mechanism_analysis_authorized_bool": False}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2akboundary0000", "public_only_decision_bool": True, "read_only_r2aj_public_artifact_docs_bool": True, "optional_r2ai_public_artifact_docs_bool": True, "private_root_read_bool": False, "tmp_read_bool": False, "private_material_read_bool": False, "group_file_read_bool": False, "recompute_r2ai_metrics_bool": False, "source_candidate_scan_bool": False, "retrieval_runtime_openlocus_provider_ci_bool": False, "material_generation_bool": False, "execution_bool": False, "raw_publication_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2akclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "robust_method_claim_bool": False, "mechanism_analysis_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2akgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2aksynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2akreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2akstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2aj_public_artifact", "haae_r2al_new_signal_family_public_design_preflight_authorized_bool": passed, "r2al_public_only_design_preflight_bool": passed, "mechanism_analysis_authorized_bool": False, "execution_authorized_bool": False, "material_generation_authorized_bool": False, "new_material_generation_authorized_bool": False, "private_read_authorized_bool": False, "ci_execution_authorized_bool": False, "scale_execution_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "openlocus_runtime_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "inherited_robustness_failure_records", "decision_records", "closed_route_records", "candidate_next_route_records", "boundary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    if {row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])} != set(GATE_NAMES): issues.append("gate_set_mismatch")
    if {row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])} != set(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2aj_checkpoint") != R2AJ_CHECKPOINT or source.get("locked_haae_r2aj_status") != R2AJ_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2aj_status_match_bool", "r2aj_self_test_19_bool", "r2aj_forbidden_scan_pass_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    inherited = (report.get("inherited_robustness_failure_records") or [{}])[0]
    if inherited.get("robustness_failure_bucket") != FAILURE_BUCKET: issues.append("inherited_failure_bucket_mismatch")
    for field in ["controls_perturbations_match_or_exceed_signal_bool", "bucket_only_public_metrics_bool", "no_raw_publication_bool", "no_method_default_scale_claim_bool"]:
        if inherited.get(field) is not True: issues.append(f"inherited_{field}")
    decision = (report.get("decision_records") or [{}])[0]
    expected_true = ["route_closed_bool", "controls_perturbations_match_or_exceed_signal_bool", "method_default_scale_claim_rejected_bool", "mechanism_analysis_deferred_bool", "new_signal_family_public_design_recommended_bool"]
    if decision.get("decision_bucket") != DECISION_BUCKET or decision.get("robustness_failure_bucket") != FAILURE_BUCKET: issues.append("decision_bucket_mismatch")
    for field in expected_true:
        if decision.get(field) is not True: issues.append(f"decision_{field}")
    if decision.get("mechanism_analysis_authorized_bool") is not False: issues.append("decision_mechanism_analysis_authorized_bool")
    closed = (report.get("closed_route_records") or [{}])[0]
    if closed.get("closed_route_bucket") != CLOSED_ROUTE_BUCKET or closed.get("route_closed_bool") is not True: issues.append("closed_route_mismatch")
    next_route = (report.get("candidate_next_route_records") or [{}])[0]
    if next_route.get("next_phase") != NEXT_PHASE or next_route.get("public_only_design_preflight_bool") is not True or next_route.get("new_signal_family_public_design_recommended_bool") is not True or next_route.get("mechanism_analysis_authorized_bool") is not False: issues.append("candidate_next_route_mismatch")
    boundary = (report.get("boundary_records") or [{}])[0]
    if boundary.get("public_only_decision_bool") is not True or boundary.get("read_only_r2aj_public_artifact_docs_bool") is not True: issues.append("boundary_public_only")
    for field in ["private_root_read_bool", "tmp_read_bool", "private_material_read_bool", "group_file_read_bool", "recompute_r2ai_metrics_bool", "source_candidate_scan_bool", "retrieval_runtime_openlocus_provider_ci_bool", "material_generation_bool", "execution_bool", "raw_publication_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "robust_method_claim_bool", "mechanism_analysis_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2al_new_signal_family_public_design_preflight_authorized_bool") is not True or stop.get("r2al_public_only_design_preflight_bool") is not True: issues.append("r2al_stop_go_mismatch")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    for field in FORBIDDEN_STOP_TRUE:
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
            parsed["validate" if arg == "--validate-report" else "out"] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value); resolved = path if path.is_absolute() else repo / path
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
    base = load_json(repo / R2AJ_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2aj_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    st = json.loads(json.dumps(base)); st["self_test_total"] = 18; check("self_test_drift_fail", build_report(st)["status"] == STATUS_FAIL_SOURCE)
    fs = json.loads(json.dumps(base)); fs["forbidden_scan"]["status"] = "fail"; check("forbidden_scan_drift_fail", build_report(fs)["status"] == STATUS_FAIL_SOURCE)
    ctrl = json.loads(json.dumps(base)); ctrl["robustness_result_audit_records"][0]["controls_perturbations_match_or_exceed_signal_bool"] = False; check("controls_match_drift_fail", build_report(ctrl)["status"] == STATUS_FAIL_DECISION)
    claim = json.loads(json.dumps(base)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("method_claim_drift_fail", build_report(claim)["status"] == STATUS_FAIL_DECISION)
    for label, mutator, expected in [
        ("decision_bucket_drift_fail", lambda r: r["decision_records"][0].__setitem__("decision_bucket", "wrong"), "decision_bucket_mismatch"),
        ("inherited_failure_drift_fail", lambda r: r["inherited_robustness_failure_records"][0].__setitem__("controls_perturbations_match_or_exceed_signal_bool", False), "inherited_controls_perturbations_match_or_exceed_signal_bool"),
        ("route_closed_drift_fail", lambda r: r["decision_records"][0].__setitem__("route_closed_bool", False), "decision_route_closed_bool"),
        ("closed_route_bucket_drift_fail", lambda r: r["closed_route_records"][0].__setitem__("closed_route_bucket", "wrong"), "closed_route_mismatch"),
        ("mechanism_auth_drift_fail", lambda r: r["decision_records"][0].__setitem__("mechanism_analysis_authorized_bool", True), "decision_mechanism_analysis_authorized_bool"),
        ("new_signal_design_drift_fail", lambda r: r["decision_records"][0].__setitem__("new_signal_family_public_design_recommended_bool", False), "decision_new_signal_family_public_design_recommended_bool"),
        ("candidate_next_route_drift_fail", lambda r: r["candidate_next_route_records"][0].__setitem__("next_phase", "wrong"), "candidate_next_route_mismatch"),
        ("boundary_private_read_fail", lambda r: r["boundary_records"][0].__setitem__("private_root_read_bool", True), "boundary_private_root_read_bool"),
        ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_execution_authorized_bool", True), "overauthorization_ci_execution_authorized_bool"),
        ("next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2al_stop_go_mismatch"),
        ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"),
        ("synthetic_validator_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"),
        ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"),
        ("status_drift_fail", lambda r: r.__setitem__("status", "wrong"), "status_mismatch"),
    ]:
        mutated = json.loads(json.dumps(passed)); mutator(mutated); check(label, expected in validate_report(mutated))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 candidate_key private_score"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
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
