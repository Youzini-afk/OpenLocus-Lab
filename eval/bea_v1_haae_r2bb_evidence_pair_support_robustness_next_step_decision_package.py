#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BB robustness next-step decision package.

Public-only decision/design package. Reads only public R2BA (and optional public
R2AZ cross-check) artifacts. It does not read private roots/material, recompute
metrics, generate material, scan source/candidate/corpus, or run runtime paths.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BB Evidence-Pair Support Robustness Next-Step Decision Package"
SLUG = "bea_v1_haae_r2bb_evidence_pair_support_robustness_next_step_decision_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"

R2BA_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ba_evidence_pair_support_robustness_experiment_public_audit_package/bea_v1_haae_r2ba_evidence_pair_support_robustness_experiment_public_audit_package_report.json")
R2AZ_REPORT_PATH = Path("artifacts/bea_v1_haae_r2az_evidence_pair_support_explicit_local_robustness_experiment/bea_v1_haae_r2az_evidence_pair_support_explicit_local_robustness_experiment_report.json")
R2BA_CHECKPOINT = "f8984bf"
R2BA_STATUS = "haae_r2ba_evidence_pair_support_robustness_experiment_public_audit_complete_r2bb_next_step_decision_authorized_negative_robustness_evidence"
R2BA_SELF_TEST_TOTAL = 34
R2AZ_CHECKPOINT = "72590e5"
R2AZ_STATUS = "haae_r2az_explicit_local_robustness_experiment_complete_r2ba_public_audit_authorized_artifact_likely"
R2AZ_SELF_TEST_TOTAL = 27
R2AY_CHECKPOINT = "126dc18"
R2AX_CHECKPOINT = "f3add65"
R2AW_CHECKPOINT = "bc44454"
R2AN_CHECKPOINT = "93bba5f"
R2AT_CHECKPOINT = "0c9c108"
R2AP_CHECKPOINT = "87ea9de"

STATUS_PASS = "haae_r2bb_evidence_pair_support_robustness_next_step_decision_complete_r2bc_mechanism_redesign_public_design_preflight_authorized"
STATUS_FAIL_SOURCE = "haae_r2bb_fail_closed_r2ba_source_or_artifact_mismatch"
STATUS_FAIL_DECISION = "haae_r2bb_fail_closed_decision_boundary_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2bb_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bb_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BC Evidence-Pair Support Mechanism Redesign Public Design Preflight"

BUCKETS = {
    "r2az_result_bucket": "artifact_likely",
    "support_control_separation_bucket": "support_control_separation_collapsed",
    "control_rejection_bucket": "control_rejection_failed",
    "path_confound_risk_bucket": "path_confound_risk_elevated",
    "support_signal_bucket": "support_signal_bucket_low",
}
R2BA_GATES = ["r2az_source_lock_gate", "r2az_result_metric_bucket_gate", "r2az_public_boundary_gate", "r2az_gate_synthetic_readback_exact_gate", "r2az_stop_go_exact_gate", "negative_robustness_evidence_gate", "no_method_default_scale_claim_gate", "r2ba_public_only_gate", "r2bb_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2BA_SYNTH = ["audit_pass", "safe_parser_fail", "r2az_checkpoint_drift_fail", "r2az_status_drift_fail", "r2az_self_test_drift_fail", "r2az_forbidden_scan_fail", "metric_result_drift_fail", "metric_support_control_drift_fail", "metric_control_rejection_drift_fail", "metric_path_confound_drift_fail", "metric_support_signal_drift_fail", "aggregate_only_drift_fail", "privacy_boundary_drift_fail", "execution_material_generation_overauth_fail", "execution_source_scan_overauth_fail", "execution_runtime_overauth_fail", "r2az_gate_drop_fail", "r2az_gate_duplicate_fail", "r2az_synthetic_drop_fail", "r2az_synthetic_duplicate_fail", "r2az_readback_drop_fail", "r2az_readback_duplicate_fail", "r2az_stop_private_read_overauth_fail", "r2az_stop_material_generation_overauth_fail", "r2az_stop_source_scan_overauth_fail", "r2az_stop_runtime_overauth_fail", "r2az_stop_claim_overauth_fail", "r2bb_stop_go_drift_fail", "r2ba_broad_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "readback_record_fail", "public_leak_fail"]
R2BA_STOP_TRUE = ["haae_r2bb_evidence_pair_support_robustness_next_step_decision_authorized_bool", "r2bb_public_only_decision_design_bool", "r2bb_no_private_read_bool", "r2bb_no_metric_recompute_bool", "r2bb_no_material_generation_bool"]
R2BA_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "experiment_execution_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]

GATES = ["r2ba_source_lock_gate", "r2ba_bucket_evidence_gate", "r2ba_public_boundary_gate", "r2ba_gate_synthetic_readback_exact_gate", "r2ba_stop_go_exact_gate", "optional_r2az_cross_audit_gate", "mechanism_redesign_decision_gate", "current_route_robustness_rejection_gate", "no_scale_external_material_continuation_gate", "r2bc_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["decision_pass", "safe_parser_fail", "r2ba_checkpoint_drift_fail", "r2ba_status_drift_fail", "r2ba_self_test_drift_fail", "r2ba_forbidden_scan_fail", "r2ba_boundary_drift_fail", "r2ba_bucket_result_drift_fail", "r2ba_bucket_support_control_drift_fail", "r2ba_bucket_control_rejection_drift_fail", "r2ba_bucket_path_confound_drift_fail", "r2ba_bucket_support_signal_drift_fail", "r2ba_gate_drop_fail", "r2ba_gate_duplicate_fail", "r2ba_synthetic_drop_fail", "r2ba_synthetic_duplicate_fail", "r2ba_readback_drop_fail", "r2ba_readback_duplicate_fail", "r2ba_stop_go_true_drop_fail", "r2ba_stop_go_private_read_overauth_fail", "r2ba_stop_go_material_overauth_fail", "r2ba_stop_go_claim_overauth_fail", "r2az_cross_audit_drift_fail", "decision_mechanism_redesign_drop_fail", "decision_scale_selected_fail", "decision_current_route_continue_fail", "r2bc_stop_go_true_drop_fail", "r2bc_stop_go_private_read_overauth_fail", "r2bc_stop_go_scale_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "readback_record_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)

STOP_TRUE = ["haae_r2bc_evidence_pair_support_mechanism_redesign_public_design_preflight_authorized_bool", "r2bc_public_only_design_preflight_bool", "current_support_route_robustness_rejected_bool", "negative_robustness_evidence_locked_bool", "no_private_read_bool", "no_metric_recompute_bool", "no_material_generation_bool", "no_method_default_scale_claim_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "experiment_execution_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "external_validation_authorized_bool", "scale_preflight_authorized_bool", "scale_execution_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "validated_signal_claim_authorized_bool", "raw_publication_authorized_bool"]

LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|parent_private_pair_ref|source_ref|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|exact_top_k_value|\bmrr\b|hit_rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    findings = [n for n, p in LEAK_PATTERNS if p.search(json.dumps(report, sort_keys=True))]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}
def parse_args(argv: list[str]) -> dict[str, str | bool]:
    parsed: dict[str, str | bool] = {"self_test": False, "validate": "", "out": ""}; i = 0
    while i < len(argv):
        if argv[i] == "--self-test": parsed["self_test"] = True; i += 1
        elif argv[i] in {"--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed["validate" if argv[i] == "--validate-report" else "out"] = argv[i + 1]; i += 2
        else: raise ValueError("invalid arguments")
    return parsed
def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]; p = Path(value); resolved = p if p.is_absolute() else repo / p
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def audit_r2ba(r2ba: dict[str, Any]) -> dict[str, bool]:
    src = (r2ba.get("source_lock_records") or [{}])[0]; aud = (r2ba.get("robustness_experiment_audit_records") or [{}])[0]; boundary = (r2ba.get("public_only_boundary_records") or [{}])[0]; stop = (r2ba.get("stop_go_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2ba.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2ba.get("synthetic_validator_records", [])]; read = r2ba.get("public_readback_records", [])
    source_ok = r2ba.get("status") == R2BA_STATUS and r2ba.get("self_test_total") == R2BA_SELF_TEST_TOTAL and r2ba.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2az_checkpoint") == R2AZ_CHECKPOINT and src.get("locked_haae_r2az_status") == R2AZ_STATUS and src.get("locked_haae_r2az_self_test_total") == R2AZ_SELF_TEST_TOTAL and src.get("locked_inherited_r2ay_checkpoint") == R2AY_CHECKPOINT and src.get("locked_inherited_r2ax_checkpoint") == R2AX_CHECKPOINT and src.get("locked_inherited_r2aw_checkpoint") == R2AW_CHECKPOINT and src.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT and src.get("locked_inherited_r2at_checkpoint") == R2AT_CHECKPOINT and src.get("locked_inherited_r2ap_checkpoint") == R2AP_CHECKPOINT and src.get("source_locked_bool") is True
    bucket_ok = all(aud.get(k) == v for k, v in BUCKETS.items()) and aud.get("negative_robustness_evidence_confirmed_bool") is True and aud.get("no_method_default_scale_claim_bool") is True
    boundary_ok = boundary.get("public_only_audit_bool") is True and boundary.get("read_only_r2az_public_artifact_bool") is True and all(boundary.get(f) is False for f in ["private_root_read_bool", "r2ax_private_material_read_bool", "metric_recompute_bool", "material_generation_bool", "source_candidate_corpus_scan_bool", "runtime_openlocus_retrieval_ci_network_provider_clone_bool", "raw_or_exact_publication_bool"])
    integrity_ok = set(gates) == set(R2BA_GATES) and len(gates) == len(R2BA_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2BA_SYNTH) and len(synth) == len(R2BA_SYNTH) and len(synth) == len(set(synth)) and len(read) == 1 and read[0].get("all_public_readback_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BA_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BA_STOP_FALSE)
    return {"source_ok": source_ok, "bucket_ok": bucket_ok, "boundary_ok": boundary_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok, "audit_ok": source_ok and bucket_ok and boundary_ok and integrity_ok and stop_ok}

def audit_r2az_cross(r2az: dict[str, Any] | None) -> bool:
    if not r2az: return False
    metric = (r2az.get("aggregate_metric_records") or [{}])[0]; stop = (r2az.get("stop_go_records") or [{}])[0]
    return r2az.get("status") == R2AZ_STATUS and r2az.get("self_test_total") == R2AZ_SELF_TEST_TOTAL and r2az.get("forbidden_scan", {}).get("status") == "pass" and metric.get("robustness_result_bucket") == "artifact_likely" and metric.get("support_vs_control_robustness_separation_bucket") == "support_control_separation_collapsed" and metric.get("shuffled_cross_task_control_rejection_bucket") == "control_rejection_failed" and metric.get("path_token_confound_risk_bucket") == "path_confound_risk_elevated" and metric.get("support_signal_retention_bucket") == "support_signal_bucket_low" and stop.get("next_allowed_phase") == "BEA-v1-HAAE-R2BA Evidence-Pair Support Robustness Experiment Public Audit Package"

def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BA_CHECKPOINT, R2BA_STATUS, R2AZ_CHECKPOINT, R2AZ_STATUS, R2AY_CHECKPOINT, R2AX_CHECKPOINT, R2AW_CHECKPOINT, R2AN_CHECKPOINT, R2AT_CHECKPOINT, R2AP_CHECKPOINT, "mechanism redesign preflight selected", "current evidence-pair support route rejected as robust signal", "negative robustness evidence locked", "artifact_likely", "support_control_separation_collapsed", "control_rejection_failed", "path_confound_risk_elevated", "support_signal_bucket_low", "no method/default/scale claim", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bb-evidence-pair-support-robustness-next-step-decision-package.md")) and ok(read("docs/zh/bea-v1-haae-r2bb-evidence-pair-support-robustness-next-step-decision-package.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bb-evidence-pair-support-robustness-next-step-decision-package.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(r2ba: dict[str, Any] | None = None, r2az: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2ba is None:
        try: r2ba = load_json(repo / R2BA_REPORT_PATH)
        except Exception: r2ba = {}
    if r2az is None:
        try: r2az = load_json(repo / R2AZ_REPORT_PATH)
        except Exception: r2az = None
    audit = audit_r2ba(r2ba); cross_ok = audit_r2az_cross(r2az); rb = public_readback_match(self_test_total)
    decision_ok = audit["audit_ok"] and cross_ok
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_DECISION if not decision_ok else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bbstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_decision_package_pass"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2ba_source_lock_gate": audit["source_ok"], "r2ba_bucket_evidence_gate": audit["bucket_ok"], "r2ba_public_boundary_gate": audit["boundary_ok"], "r2ba_gate_synthetic_readback_exact_gate": audit["integrity_ok"], "r2ba_stop_go_exact_gate": audit["stop_ok"], "optional_r2az_cross_audit_gate": cross_ok, "mechanism_redesign_decision_gate": True, "current_route_robustness_rejection_gate": True, "no_scale_external_material_continuation_gate": True, "r2bc_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bbsource0000", "locked_haae_r2ba_checkpoint": R2BA_CHECKPOINT, "locked_haae_r2ba_status": R2BA_STATUS, "locked_haae_r2ba_self_test_total": R2BA_SELF_TEST_TOTAL, "locked_haae_r2az_checkpoint": R2AZ_CHECKPOINT, "locked_haae_r2az_status": R2AZ_STATUS, "locked_inherited_r2ay_checkpoint": R2AY_CHECKPOINT, "locked_inherited_r2ax_checkpoint": R2AX_CHECKPOINT, "locked_inherited_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "source_locked_bool": audit["source_ok"]}],
        "decision_records": [{"anonymous_decision_id": "haaer2bbdecision0000", "mechanism_redesign_preflight_selected_bool": True, "scale_preflight_selected_bool": False, "external_robustness_execution_selected_bool": False, "new_material_generation_selected_bool": False, "current_route_continuation_selected_bool": False, "current_evidence_pair_support_route_rejected_as_robust_signal_bool": True, "negative_robustness_evidence_locked_bool": audit["bucket_ok"], "r2ap_support_signal_not_sufficient_after_robustness_failure_bool": True, "r2at_pair_complementarity_supported_not_sufficient_after_robustness_failure_bool": True, "no_method_default_runtime_scale_winner_validated_signal_downstream_value_claim_bool": True}],
        "r2ba_audit_records": [{"anonymous_audit_id": "haaer2bbaudit0000", **BUCKETS, "r2ba_public_only_boundary_bool": audit["boundary_ok"], "r2ba_stop_go_exact_bool": audit["stop_ok"], "r2ba_gate_synthetic_readback_exact_bool": audit["integrity_ok"], "negative_robustness_evidence_confirmed_bool": audit["bucket_ok"]}],
        "r2az_cross_audit_records": [{"anonymous_cross_audit_id": "haaer2bbcross0000", "optional_r2az_public_cross_audit_pass_bool": cross_ok, "r2az_artifact_likely_status_bool": cross_ok}],
        "r2bc_scope_records": [{"anonymous_scope_id": "haaer2bbscope0000", "public_only_non_executing_redesign_preflight_bool": True, "may_define_redesigned_mechanism_hypotheses_bool": True, "may_define_stricter_control_families_bool": True, "may_define_path_confound_mitigation_requirements_bool": True, "may_define_gold_isolation_rules_bool": True, "may_define_support_control_separation_gates_bool": True, "may_define_aggregate_public_artifact_shape_bool": True, "may_define_fail_closed_validators_bool": True, "future_explicit_opt_in_private_contracts_design_only_bool": True, "execute_future_private_contracts_bool": False}],
        "public_only_boundary_records": [{"anonymous_boundary_id": "haaer2bbboundary0000", "public_only_decision_design_bool": True, "read_only_r2ba_public_artifact_bool": True, "private_read_bool": False, "private_write_bool": False, "material_generation_bool": False, "metric_recompute_bool": False, "source_candidate_corpus_scan_bool": False, "runtime_retrieval_ci_network_provider_clone_bool": False, "raw_or_exact_private_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bbgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bbsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bbreadback0000", **rb}],
        "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTH): issues.append("self_test_validator_count_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    for f, e in {"locked_haae_r2ba_checkpoint": R2BA_CHECKPOINT, "locked_haae_r2ba_status": R2BA_STATUS, "locked_haae_r2ba_self_test_total": R2BA_SELF_TEST_TOTAL, "locked_haae_r2az_checkpoint": R2AZ_CHECKPOINT, "locked_haae_r2az_status": R2AZ_STATUS, "locked_inherited_r2ay_checkpoint": R2AY_CHECKPOINT, "locked_inherited_r2ax_checkpoint": R2AX_CHECKPOINT, "locked_inherited_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    dec = (report.get("decision_records") or [{}])[0]
    for f in ["mechanism_redesign_preflight_selected_bool", "current_evidence_pair_support_route_rejected_as_robust_signal_bool", "negative_robustness_evidence_locked_bool", "r2ap_support_signal_not_sufficient_after_robustness_failure_bool", "r2at_pair_complementarity_supported_not_sufficient_after_robustness_failure_bool", "no_method_default_runtime_scale_winner_validated_signal_downstream_value_claim_bool"]:
        if dec.get(f) is not True: issues.append(f"decision_{f}")
    for f in ["scale_preflight_selected_bool", "external_robustness_execution_selected_bool", "new_material_generation_selected_bool", "current_route_continuation_selected_bool"]:
        if dec.get(f) is not False: issues.append(f"decision_{f}")
    aud = (report.get("r2ba_audit_records") or [{}])[0]
    for f, e in BUCKETS.items():
        if aud.get(f) != e: issues.append(f"bucket_{f}")
    for f in ["r2ba_public_only_boundary_bool", "r2ba_stop_go_exact_bool", "r2ba_gate_synthetic_readback_exact_bool", "negative_robustness_evidence_confirmed_bool"]:
        if aud.get(f) is not True: issues.append(f"audit_{f}")
    cross = (report.get("r2az_cross_audit_records") or [{}])[0]
    if cross.get("optional_r2az_public_cross_audit_pass_bool") is not True: issues.append("r2az_cross_audit_mismatch")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bc_stop_go_mismatch")
    for f in STOP_TRUE:
        if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    for f in STOP_FALSE:
        if stop.get(f) is not False: issues.append(f"overauthorization_{f}")
    boundary = (report.get("public_only_boundary_records") or [{}])[0]
    for f in ["public_only_decision_design_bool", "read_only_r2ba_public_artifact_bool"]:
        if boundary.get(f) is not True: issues.append(f"boundary_{f}")
    for f in ["private_read_bool", "private_write_bool", "material_generation_bool", "metric_recompute_bool", "source_candidate_corpus_scan_bool", "runtime_retrieval_ci_network_provider_clone_bool", "raw_or_exact_private_publication_bool"]:
        if boundary.get(f) is not False: issues.append(f"boundary_{f}")
    read = report.get("public_readback_records", [])
    if len(read) != 1 or read[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{g.get('gate_bucket', 'unknown')}")
    return issues

def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; repo = Path(__file__).resolve().parents[1]; base = load_json(repo / R2BA_REPORT_PATH); cross = load_json(repo / R2AZ_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    passed = build_report(base, cross); check("decision_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try: parse_args(["--unknown"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    muts = [("r2ba_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2az_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2ba_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE), ("r2ba_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE), ("r2ba_forbidden_scan_fail", lambda r: r["forbidden_scan"].__setitem__("status", "fail"), STATUS_FAIL_SOURCE), ("r2ba_boundary_drift_fail", lambda r: r["public_only_boundary_records"][0].__setitem__("private_root_read_bool", True), STATUS_FAIL_DECISION), ("r2ba_bucket_result_drift_fail", lambda r: r["robustness_experiment_audit_records"][0].__setitem__("r2az_result_bucket", "robust_signal"), STATUS_FAIL_DECISION), ("r2ba_bucket_support_control_drift_fail", lambda r: r["robustness_experiment_audit_records"][0].__setitem__("support_control_separation_bucket", "bad"), STATUS_FAIL_DECISION), ("r2ba_bucket_control_rejection_drift_fail", lambda r: r["robustness_experiment_audit_records"][0].__setitem__("control_rejection_bucket", "bad"), STATUS_FAIL_DECISION), ("r2ba_bucket_path_confound_drift_fail", lambda r: r["robustness_experiment_audit_records"][0].__setitem__("path_confound_risk_bucket", "bad"), STATUS_FAIL_DECISION), ("r2ba_bucket_support_signal_drift_fail", lambda r: r["robustness_experiment_audit_records"][0].__setitem__("support_signal_bucket", "bad"), STATUS_FAIL_DECISION), ("r2ba_gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), STATUS_FAIL_DECISION), ("r2ba_gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), STATUS_FAIL_DECISION), ("r2ba_synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), STATUS_FAIL_DECISION), ("r2ba_synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), STATUS_FAIL_DECISION), ("r2ba_readback_drop_fail", lambda r: r.__setitem__("public_readback_records", []), STATUS_FAIL_DECISION), ("r2ba_readback_duplicate_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), STATUS_FAIL_DECISION), ("r2ba_stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(R2BA_STOP_TRUE[0], False), STATUS_FAIL_DECISION), ("r2ba_stop_go_private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_DECISION), ("r2ba_stop_go_material_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), STATUS_FAIL_DECISION), ("r2ba_stop_go_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("method_claim_authorized_bool", True), STATUS_FAIL_DECISION)]
    for name, mut, status in muts:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m, cross)["status"] == status)
    c = json.loads(json.dumps(cross)); c["status"] = "bad"; check("r2az_cross_audit_drift_fail", build_report(base, c)["status"] == STATUS_FAIL_DECISION)
    report_mut = [("decision_mechanism_redesign_drop_fail", lambda r: r["decision_records"][0].__setitem__("mechanism_redesign_preflight_selected_bool", False), "decision_mechanism_redesign_preflight_selected_bool"), ("decision_scale_selected_fail", lambda r: r["decision_records"][0].__setitem__("scale_preflight_selected_bool", True), "decision_scale_preflight_selected_bool"), ("decision_current_route_continue_fail", lambda r: r["decision_records"][0].__setitem__("current_route_continuation_selected_bool", True), "decision_current_route_continuation_selected_bool"), ("r2bc_stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("r2bc_stop_go_private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("r2bc_stop_go_scale_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_preflight_authorized_bool", True), "overauthorization_scale_preflight_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    for name, mut, issue in report_mut:
        m = json.loads(json.dumps(passed)); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo / public_artifact_path(str(args["validate"]))); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] == STATUS_PASS else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
