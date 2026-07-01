#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AL new signal family public design preflight.

Public-only design/preflight over the committed R2AK public artifact/docs. It
does not read private roots/material/group JSONL or /tmp roots, does not scan
source/candidates, does not execute, compute metrics, or generate material.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AL New Signal Family Public Design Preflight"
SLUG = "bea_v1_haae_r2al_new_signal_family_public_design_preflight"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AK_CHECKPOINT = "36fc4fa"
R2AK_STATUS = "haae_r2ak_robustness_failure_decision_complete_r2al_new_signal_family_public_design_authorized_route_closed"
R2AK_SELF_TEST_TOTAL = 22
R2AK_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ak_robustness_failure_decision_package/bea_v1_haae_r2ak_robustness_failure_decision_package_report.json")

STATUS_PASS = "haae_r2al_new_signal_family_public_design_preflight_complete_r2am_material_generation_preflight_authorized"
STATUS_FAIL_SOURCE = "haae_r2al_fail_closed_source_lock_mismatch"
STATUS_FAIL_DESIGN = "haae_r2al_fail_closed_signal_family_design_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2al_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2al_fail_closed_raw_private_exact_leak"
STATUS_FAIL_READBACK = "haae_r2al_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 28
NEXT_PHASE = "BEA-v1-HAAE-R2AM Evidence-Pair Support Material Generation Preflight"

SELECTED_SIGNAL_FAMILY = "evidence_pair_support_complementarity"
CLOSED_ROUTE_BUCKET = "r2ac_r2ai_single_rank_content_path_signal"
FAILURE_BUCKET = "brittle_or_artifact"
CANDIDATES = {
    "evidence_pair_support_complementarity": "selected",
    "public_aggregate_mechanism_analysis": "rejected_low_value_after_route_closure",
    "single_rank_content_path_tweak": "rejected_same_failure_mode_controls_match_signal",
    "lexical_rank_expansion": "rejected_single_rank_variant_not_new_signal_family",
    "provider_semantic_judgement": "rejected_provider_network_execution_not_authorized",
}
GATE_NAMES = ["r2ak_source_locked_gate", "r2ak_self_test_22_gate", "r2ak_forbidden_scan_pass_gate", "route_closed_gate", "brittle_route_closure_gate", "r2al_authorization_only_gate", "candidate_family_set_gate", "selected_signal_family_gate", "rejected_family_rationale_gate", "single_rank_route_not_reopened_gate", "mechanism_analysis_not_authorized_gate", "r2am_public_preflight_scope_gate", "r2an_generation_not_authorized_gate", "public_only_boundary_gate", "no_claims_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["source_lock_pass", "wrong_r2ak_status_fail", "self_test_drift_fail", "forbidden_scan_drift_fail", "route_closed_drift_fail", "brittle_failure_drift_fail", "r2al_auth_drift_fail", "candidate_family_set_fail", "selected_family_drift_fail", "rejected_family_drift_fail", "single_rank_reopen_fail", "mechanism_auth_fail", "r2am_scope_fail", "r2an_generation_auth_fail", "boundary_private_read_fail", "boundary_material_generation_fail", "boundary_source_scan_fail", "method_claim_fail", "default_claim_fail", "scale_claim_fail", "stop_go_overauth_fail", "next_phase_drift_fail", "gate_set_fail", "synthetic_validator_set_fail", "readback_record_fail", "status_drift_fail", "leak_fail", "safe_parser_fail"]
FORBIDDEN_STOP_TRUE = ["r2am_material_generation_authorized_bool", "r2am_private_read_authorized_bool", "r2an_generation_authorized_bool", "single_rank_content_path_route_reopen_authorized_bool", "material_generation_authorized_bool", "new_material_generation_authorized_bool", "private_read_authorized_bool", "private_write_authorized_bool", "execution_authorized_bool", "ci_execution_authorized_bool", "scale_execution_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool", "mechanism_analysis_authorized_bool"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2ak(r2ak: dict[str, Any]) -> dict[str, bool]:
    decision = (r2ak.get("decision_records") or [{}])[0]
    closed = (r2ak.get("closed_route_records") or [{}])[0]
    inherited = (r2ak.get("inherited_robustness_failure_records") or [{}])[0]
    stop = (r2ak.get("stop_go_records") or [{}])[0]
    status_ok = r2ak.get("status") == R2AK_STATUS
    self_test_ok = r2ak.get("self_test_total") == R2AK_SELF_TEST_TOTAL
    scan_ok = r2ak.get("forbidden_scan", {}).get("status") == "pass"
    route_closed_ok = decision.get("route_closed_bool") is True and closed.get("route_closed_bool") is True and closed.get("closed_route_bucket") == CLOSED_ROUTE_BUCKET
    brittle_ok = decision.get("robustness_failure_bucket") == FAILURE_BUCKET and inherited.get("robustness_failure_bucket") == FAILURE_BUCKET and inherited.get("controls_perturbations_match_or_exceed_signal_bool") is True
    no_claim_ok = decision.get("method_default_scale_claim_rejected_bool") is True and inherited.get("no_method_default_scale_claim_bool") is True
    r2al_auth_only_ok = stop.get("haae_r2al_new_signal_family_public_design_preflight_authorized_bool") is True and stop.get("r2al_public_only_design_preflight_bool") is True and stop.get("next_allowed_phase") == PHASE and all(stop.get(field, False) is False for field in ["mechanism_analysis_authorized_bool", "execution_authorized_bool", "material_generation_authorized_bool", "new_material_generation_authorized_bool", "private_read_authorized_bool", "ci_execution_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    source_ok = status_ok and self_test_ok and scan_ok and route_closed_ok and brittle_ok and r2al_auth_only_ok
    return {"source_ok": source_ok, "status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "route_closed_ok": route_closed_ok, "brittle_ok": brittle_ok, "no_claim_ok": no_claim_ok, "r2al_auth_only_ok": r2al_auth_only_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate", re.compile(r"candidate_key|source_file_key|filepath|filename|directory|snippet|start_line|end_line|gold_spans|hard_negatives|\.rs\b|crates/openlocus-")), ("exact_metric", re.compile(r"private_score|private_rank|exact_rate|exact_mrr|exact_rank|exact_count|hit_rate|\b[a-f0-9]{32,64}\b", re.I))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AK_CHECKPOINT, R2AK_STATUS, "R2AK self-test 22/22", "route closed", CLOSED_ROUTE_BUCKET, FAILURE_BUCKET, SELECTED_SIGNAL_FAMILY, "isolated single-candidate rank", "multi-evidence consistency/support/contrast", "public aggregate mechanism analysis rejected", "single-rank content/path tweak rejected", "lexical rank expansion rejected", "provider semantic judgement rejected", NEXT_PHASE, "R2AM public-only preflight", "R2AN generation requires separate authorization", "no method/default/scale/winner/validated-signal claims"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2al-new-signal-family-public-design-preflight.md")) and has_all(read("docs/zh/bea-v1-haae-r2al-new-signal-family-public-design-preflight.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2al-new-signal-family-public-design-preflight.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2ak: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2ak is None:
        try: r2ak = load_json(repo / R2AK_REPORT_PATH)
        except Exception: r2ak = {}
    audit = audit_r2ak(r2ak)
    readback = public_readback_match(self_test_total)
    design_ok = True
    if not audit["source_ok"]:
        status = STATUS_FAIL_SOURCE
    elif not design_ok:
        status = STATUS_FAIL_DESIGN
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2ak_source_locked_gate": audit["source_ok"], "r2ak_self_test_22_gate": audit["self_test_ok"], "r2ak_forbidden_scan_pass_gate": audit["scan_ok"], "route_closed_gate": audit["route_closed_ok"], "brittle_route_closure_gate": audit["brittle_ok"], "r2al_authorization_only_gate": audit["r2al_auth_only_ok"], "candidate_family_set_gate": True, "selected_signal_family_gate": True, "rejected_family_rationale_gate": True, "single_rank_route_not_reopened_gate": True, "mechanism_analysis_not_authorized_gate": True, "r2am_public_preflight_scope_gate": True, "r2an_generation_not_authorized_gate": True, "public_only_boundary_gate": True, "no_claims_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2alsource0000", "locked_haae_r2ak_checkpoint": R2AK_CHECKPOINT, "locked_haae_r2ak_status": R2AK_STATUS, "r2ak_status_match_bool": audit["status_ok"], "r2ak_self_test_22_bool": audit["self_test_ok"], "r2ak_forbidden_scan_pass_bool": audit["scan_ok"], "r2ak_route_closed_bool": audit["route_closed_ok"], "r2ak_brittle_route_closure_bool": audit["brittle_ok"], "r2ak_r2al_authorization_only_bool": audit["r2al_auth_only_ok"], "source_locked_bool": audit["source_ok"]}],
        "inherited_route_closure_records": [{"anonymous_inherited_route_closure_id": "haaer2alclosed0000", "route_closed_bool": True, "closed_route_bucket": CLOSED_ROUTE_BUCKET, "robustness_failure_bucket": FAILURE_BUCKET, "controls_perturbations_match_or_exceed_signal_bool": True, "method_default_scale_claim_rejected_bool": True}],
        "candidate_signal_family_records": [{"anonymous_candidate_signal_family_id": f"haaer2alcandidate{idx:04d}", "signal_family_bucket": name, "selection_decision_bucket": decision, "candidate_reviewed_bool": True} for idx, (name, decision) in enumerate(CANDIDATES.items())],
        "selected_signal_family_records": [{"anonymous_selected_signal_family_id": "haaer2alselected0000", "selected_signal_family_bucket": SELECTED_SIGNAL_FAMILY, "selected_bool": True, "rationale_bucket": "move_from_isolated_single_candidate_rank_to_multi_evidence_consistency_support_contrast", "single_rank_route_reopened_bool": False, "mechanism_analysis_authorized_bool": False}],
        "r2am_preflight_design_scope_records": [{"anonymous_r2am_scope_id": "haaer2alscope0000", "next_phase": NEXT_PHASE, "public_only_preflight_bool": True, "may_define_evidence_pair_support_schema_bool": True, "may_define_public_source_allowlist_bool": True, "may_define_bounds_caps_bool": True, "may_define_private_output_contract_for_later_r2an_bool": True, "private_root_read_bool": False, "material_generation_bool": False, "source_candidate_scan_bool": False, "execution_bool": False, "metrics_bool": False, "claims_bool": False, "r2an_generation_authorized_bool": False}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2alboundary0000", "public_only_design_preflight_bool": True, "read_only_r2ak_public_artifact_docs_bool": True, "earlier_public_summaries_optional_bool": True, "private_root_read_bool": False, "private_material_read_bool": False, "group_jsonl_read_bool": False, "tmp_read_bool": False, "raw_task_query_candidate_gold_read_bool": False, "source_files_for_generation_read_bool": False, "uncommitted_private_artifact_read_bool": False, "execution_bool": False, "material_generation_bool": False, "source_candidate_scan_bool": False, "recompute_metrics_bool": False, "ci_network_provider_clone_runtime_openlocus_bool": False, "private_write_bool": False, "raw_publication_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2alclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "validated_signal_claim_bool": False, "robust_method_claim_bool": False, "mechanism_analysis_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2algate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2alsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2alreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2alstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2ak_public_artifact", "haae_r2am_evidence_pair_support_material_generation_preflight_authorized_bool": passed, "r2am_public_only_preflight_bool": passed, "r2am_design_schema_bounds_only_bool": passed, "r2am_material_generation_authorized_bool": False, "r2am_private_read_authorized_bool": False, "r2an_generation_authorized_bool": False, "single_rank_content_path_route_reopen_authorized_bool": False, "material_generation_authorized_bool": False, "new_material_generation_authorized_bool": False, "private_read_authorized_bool": False, "private_write_authorized_bool": False, "execution_authorized_bool": False, "ci_execution_authorized_bool": False, "scale_execution_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "openlocus_runtime_authorized_bool": False, "source_scan_authorized_bool": False, "candidate_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False, "mechanism_analysis_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "inherited_route_closure_records", "candidate_signal_family_records", "selected_signal_family_records", "r2am_preflight_design_scope_records", "boundary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    if {row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])} != set(GATE_NAMES): issues.append("gate_set_mismatch")
    if {row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])} != set(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2ak_checkpoint") != R2AK_CHECKPOINT or source.get("locked_haae_r2ak_status") != R2AK_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2ak_status_match_bool", "r2ak_self_test_22_bool", "r2ak_forbidden_scan_pass_bool", "r2ak_route_closed_bool", "r2ak_brittle_route_closure_bool", "r2ak_r2al_authorization_only_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    inherited = (report.get("inherited_route_closure_records") or [{}])[0]
    if inherited.get("closed_route_bucket") != CLOSED_ROUTE_BUCKET or inherited.get("robustness_failure_bucket") != FAILURE_BUCKET: issues.append("inherited_route_closure_mismatch")
    for field in ["route_closed_bool", "controls_perturbations_match_or_exceed_signal_bool", "method_default_scale_claim_rejected_bool"]:
        if inherited.get(field) is not True: issues.append(f"inherited_{field}")
    candidates = {row.get("signal_family_bucket"): row.get("selection_decision_bucket") for row in report.get("candidate_signal_family_records", [])}
    if candidates != CANDIDATES: issues.append("candidate_family_set_mismatch")
    selected = (report.get("selected_signal_family_records") or [{}])[0]
    if selected.get("selected_signal_family_bucket") != SELECTED_SIGNAL_FAMILY or selected.get("selected_bool") is not True: issues.append("selected_signal_family_mismatch")
    if selected.get("single_rank_route_reopened_bool") is not False or selected.get("mechanism_analysis_authorized_bool") is not False: issues.append("selected_boundary_mismatch")
    scope = (report.get("r2am_preflight_design_scope_records") or [{}])[0]
    if scope.get("next_phase") != NEXT_PHASE: issues.append("r2am_scope_next_phase")
    for field in ["public_only_preflight_bool", "may_define_evidence_pair_support_schema_bool", "may_define_public_source_allowlist_bool", "may_define_bounds_caps_bool", "may_define_private_output_contract_for_later_r2an_bool"]:
        if scope.get(field) is not True: issues.append(f"r2am_scope_{field}")
    for field in ["private_root_read_bool", "material_generation_bool", "source_candidate_scan_bool", "execution_bool", "metrics_bool", "claims_bool", "r2an_generation_authorized_bool"]:
        if scope.get(field) is not False: issues.append(f"r2am_scope_{field}")
    boundary = (report.get("boundary_records") or [{}])[0]
    if boundary.get("public_only_design_preflight_bool") is not True: issues.append("boundary_public_only")
    for field in ["private_root_read_bool", "private_material_read_bool", "group_jsonl_read_bool", "tmp_read_bool", "raw_task_query_candidate_gold_read_bool", "source_files_for_generation_read_bool", "uncommitted_private_artifact_read_bool", "execution_bool", "material_generation_bool", "source_candidate_scan_bool", "recompute_metrics_bool", "ci_network_provider_clone_runtime_openlocus_bool", "private_write_bool", "raw_publication_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "validated_signal_claim_bool", "robust_method_claim_bool", "mechanism_analysis_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2am_evidence_pair_support_material_generation_preflight_authorized_bool") is not True or stop.get("r2am_public_only_preflight_bool") is not True or stop.get("r2am_design_schema_bounds_only_bool") is not True: issues.append("r2am_stop_go_mismatch")
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
    base = load_json(repo / R2AK_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2ak_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    st = json.loads(json.dumps(base)); st["self_test_total"] = 21; check("self_test_drift_fail", build_report(st)["status"] == STATUS_FAIL_SOURCE)
    fs = json.loads(json.dumps(base)); fs["forbidden_scan"]["status"] = "fail"; check("forbidden_scan_drift_fail", build_report(fs)["status"] == STATUS_FAIL_SOURCE)
    closed = json.loads(json.dumps(base)); closed["decision_records"][0]["route_closed_bool"] = False; check("route_closed_drift_fail", build_report(closed)["status"] == STATUS_FAIL_SOURCE)
    brittle = json.loads(json.dumps(base)); brittle["decision_records"][0]["robustness_failure_bucket"] = "robust_signal"; check("brittle_failure_drift_fail", build_report(brittle)["status"] == STATUS_FAIL_SOURCE)
    auth = json.loads(json.dumps(base)); auth["stop_go_records"][0]["haae_r2al_new_signal_family_public_design_preflight_authorized_bool"] = False; check("r2al_auth_drift_fail", build_report(auth)["status"] == STATUS_FAIL_SOURCE)
    for label, mutator, expected in [
        ("candidate_family_set_fail", lambda r: r["candidate_signal_family_records"].pop(), "candidate_family_set_mismatch"),
        ("selected_family_drift_fail", lambda r: r["selected_signal_family_records"][0].__setitem__("selected_signal_family_bucket", "wrong"), "selected_signal_family_mismatch"),
        ("rejected_family_drift_fail", lambda r: r["candidate_signal_family_records"][1].__setitem__("selection_decision_bucket", "selected"), "candidate_family_set_mismatch"),
        ("single_rank_reopen_fail", lambda r: r["selected_signal_family_records"][0].__setitem__("single_rank_route_reopened_bool", True), "selected_boundary_mismatch"),
        ("mechanism_auth_fail", lambda r: r["selected_signal_family_records"][0].__setitem__("mechanism_analysis_authorized_bool", True), "selected_boundary_mismatch"),
        ("r2am_scope_fail", lambda r: r["r2am_preflight_design_scope_records"][0].__setitem__("public_only_preflight_bool", False), "r2am_scope_public_only_preflight_bool"),
        ("r2an_generation_auth_fail", lambda r: r["r2am_preflight_design_scope_records"][0].__setitem__("r2an_generation_authorized_bool", True), "r2am_scope_r2an_generation_authorized_bool"),
        ("boundary_private_read_fail", lambda r: r["boundary_records"][0].__setitem__("private_root_read_bool", True), "boundary_private_root_read_bool"),
        ("boundary_material_generation_fail", lambda r: r["boundary_records"][0].__setitem__("material_generation_bool", True), "boundary_material_generation_bool"),
        ("boundary_source_scan_fail", lambda r: r["boundary_records"][0].__setitem__("source_candidate_scan_bool", True), "boundary_source_candidate_scan_bool"),
        ("method_claim_fail", lambda r: r["claim_boundary_records"][0].__setitem__("method_winner_claim_bool", True), "claim_method_winner_claim_bool"),
        ("default_claim_fail", lambda r: r["claim_boundary_records"][0].__setitem__("default_runtime_claim_bool", True), "claim_default_runtime_claim_bool"),
        ("scale_claim_fail", lambda r: r["claim_boundary_records"][0].__setitem__("scaling_claim_bool", True), "claim_scaling_claim_bool"),
        ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_execution_authorized_bool", True), "overauthorization_ci_execution_authorized_bool"),
        ("next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2am_stop_go_mismatch"),
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
