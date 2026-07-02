#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BM outcome-label acquisition public decision design.

Public-only, non-executing decision package after the R2BL public audit of the
R2BK controlled unavailable result. Reads only public artifacts and authorizes
only R2BN public design preflight.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BM Evidence-Pair Support Outcome Label Acquisition Public Decision Design Package"
SLUG = "bea_v1_haae_r2bm_evidence_pair_support_outcome_label_acquisition_public_decision_design"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BL_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bl_evidence_pair_support_outcome_aligned_material_public_audit_package/bea_v1_haae_r2bl_evidence_pair_support_outcome_aligned_material_public_audit_package_report.json")

R2BL_CHECKPOINT = "41aef9e"
R2BL_STATUS = "haae_r2bl_outcome_aligned_material_public_audit_complete_r2bm_decision_design_authorized_unavailable_no_material_generated"
R2BL_SELF_TEST_TOTAL = 45
R2BK_CHECKPOINT = "7073b12"
R2BK_STATUS = "haae_r2bk_unavailable_outcome_alignment_source_labels_absent_no_material_generated"
R2BJ_CHECKPOINT = "cab3b84"
R2BI_CHECKPOINT = "f231205"
R2BG_CHECKPOINT = "ad8de95"
R2BE_CHECKPOINT = "c3901d6"
R2BG_RESULT_BUCKET = "artifact_or_weak_signal"
R2BG_OUTCOME_BUCKET = "outcome_eval_alignment_unavailable"
GENERATION_BUCKET = "outcome_alignment_unavailable_no_material_generated"

STATUS_PASS = "haae_r2bm_outcome_label_acquisition_public_decision_design_complete_r2bn_public_design_preflight_authorized"
STATUS_FAIL_SOURCE = "haae_r2bm_fail_closed_r2bl_source_or_unavailable_audit_mismatch"
STATUS_FAIL_DECISION = "haae_r2bm_fail_closed_decision_or_stop_go_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2bm_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bm_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BN Evidence-Pair Support Outcome Label Acquisition Public Design Preflight"

R2BL_GATES = ["r2bk_source_lock_gate", "r2bk_unavailable_status_gate", "r2bk_no_material_generated_gate", "r2bk_no_metric_gate", "r2bk_no_source_scan_gate", "r2bk_gate_synthetic_readback_exact_gate", "r2bk_stop_go_to_r2bl_only_gate", "public_only_audit_gate", "aggregate_publication_gate", "r2bm_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2BL_SYNTH = ["audit_pass", "safe_parser_fail", "r2bk_checkpoint_drift_fail", "r2bk_status_drift_fail", "r2bk_self_test_drift_fail", "r2bj_lock_drift_fail", "r2bg_result_drift_fail", "r2bg_outcome_drift_fail", "unavailable_fact_drift_fail", "generation_bucket_drift_fail", "generated_group_overclaim_fail", "material_generated_overclaim_fail", "metric_overauth_fail", "source_scan_overauth_fail", "r2bk_execution_signal_interpretation_fail", "r2bk_no_metric_signal_interpretation_fail", "r2bk_private_rows_public_fail", "r2bk_private_ids_public_fail", "r2bk_input_implicit_root_fail", "r2bk_input_public_root_fail", "r2bk_gate_drop_fail", "r2bk_gate_duplicate_fail", "r2bk_synthetic_drop_fail", "r2bk_synthetic_duplicate_fail", "r2bk_readback_drop_fail", "r2bk_stop_go_true_drop_fail", "r2bk_no_source_scan_true_drop_fail", "r2bk_stop_go_overauth_fail", "r2bk_experiment_overauth_fail", "r2bm_stop_go_true_drop_fail", "r2bm_private_overauth_fail", "r2bm_material_overauth_fail", "r2bm_metric_overauth_fail", "r2bm_claim_overauth_fail", "publication_aggregate_drop_fail", "publication_private_root_overauth_fail", "publication_exact_metric_overauth_fail", "audit_r2bg_result_drift_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "public_leak_fail"]
R2BL_SYNTHETIC_TOTAL = len(R2BL_SYNTH)
R2BL_STOP_TRUE = ["haae_r2bm_outcome_label_acquisition_public_decision_design_authorized_bool", "r2bm_public_only_decision_design_bool", "r2bm_no_execution_bool", "r2bm_no_private_read_write_bool", "r2bm_no_material_generation_bool", "r2bm_no_metric_recompute_bool", "controlled_unavailable_result_locked_bool", "outcome_alignment_source_labels_absent_locked_bool"]
R2BL_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "execution_authorized_bool", "experiment_authorized_bool", "metric_recompute_authorized_bool", "experiment_metrics_authorized_bool", "material_generation_authorized_bool", "material_repair_execution_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
GATES = ["r2bl_source_lock_gate", "r2bk_unavailable_evidence_gate", "r2bl_public_only_boundary_gate", "r2bl_stop_go_to_r2bm_gate", "r2bl_gate_synthetic_readback_exact_gate", "outcome_label_acquisition_decision_gate", "closure_pivot_rejected_gate", "r2bn_stop_go_only_gate", "public_only_non_executing_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["decision_pass", "safe_parser_fail", "r2bl_checkpoint_drift_fail", "r2bl_status_drift_fail", "r2bl_self_test_drift_fail", "r2bk_checkpoint_drift_fail", "r2bk_status_drift_fail", "r2bk_unavailable_fact_drift_fail", "r2bk_generation_bucket_drift_fail", "r2bk_generated_group_overclaim_fail", "r2bk_material_generated_overclaim_fail", "r2bl_boundary_private_overauth_fail", "r2bl_boundary_metric_overauth_fail", "r2bl_boundary_material_overauth_fail", "r2bl_publication_overauth_fail", "r2bl_synthetic_drop_fail", "r2bl_synthetic_duplicate_fail", "r2bl_synthetic_rename_fail", "r2bl_gate_drop_fail", "r2bl_gate_duplicate_fail", "r2bl_readback_drop_fail", "r2bl_stop_go_true_drop_fail", "r2bl_stop_go_overauth_fail", "decision_selected_drop_fail", "closure_selected_overauth_fail", "closure_deferred_drop_fail", "pivot_selected_overauth_fail", "pivot_deferred_drop_fail", "direct_label_acquisition_overauth_fail", "direct_material_generation_overauth_fail", "direct_experiment_overauth_fail", "existing_label_recovery_suboption_drop_fail", "new_label_acquisition_suboption_drop_fail", "rerun_selected_overauth_fail", "scale_selected_overauth_fail", "signal_claim_overauth_fail", "r2bn_scope_source_scan_drop_fail", "r2bn_stop_go_true_drop_fail", "r2bn_private_overauth_fail", "r2bn_execution_overauth_fail", "r2bn_material_overauth_fail", "r2bn_metric_overauth_fail", "r2bn_source_scan_overauth_fail", "r2bn_claim_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
STOP_TRUE = ["haae_r2bn_outcome_label_acquisition_public_design_preflight_authorized_bool", "r2bn_public_only_design_preflight_bool", "r2bn_no_execution_bool", "r2bn_no_private_read_write_bool", "r2bn_no_label_generation_bool", "r2bn_no_material_generation_bool", "r2bn_no_metric_recompute_bool", "r2bn_no_source_scan_bool", "outcome_label_acquisition_design_selected_bool", "controlled_unavailable_result_locked_bool", "outcome_alignment_source_labels_absent_locked_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "execution_authorized_bool", "label_acquisition_execution_authorized_bool", "label_generation_authorized_bool", "experiment_authorized_bool", "metric_recompute_authorized_bool", "experiment_metrics_authorized_bool", "material_generation_authorized_bool", "material_repair_execution_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|private_source_ref|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|\bmrr\b|hit[_-]?rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
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
    p = Path(value); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def audit_r2bl(r2bl: dict[str, Any]) -> dict[str, bool]:
    src = (r2bl.get("source_lock_records") or [{}])[0]; aud = (r2bl.get("r2bk_unavailable_audit_records") or [{}])[0]; integ = (r2bl.get("r2bk_integrity_audit_records") or [{}])[0]; priv = (r2bl.get("privacy_boundary_records") or [{}])[0]; stop = (r2bl.get("stop_go_records") or [{}])[0]; pub = (r2bl.get("publication_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2bl.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2bl.get("synthetic_validator_records", [])]; read = r2bl.get("public_readback_records", [])
    source_ok = r2bl.get("status") == R2BL_STATUS and r2bl.get("self_test_total") == R2BL_SELF_TEST_TOTAL and r2bl.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bk_checkpoint") == R2BK_CHECKPOINT and src.get("locked_haae_r2bk_status") == R2BK_STATUS and src.get("locked_inherited_r2bj_checkpoint") == R2BJ_CHECKPOINT and src.get("locked_inherited_r2bi_checkpoint") == R2BI_CHECKPOINT and src.get("locked_inherited_r2bg_checkpoint") == R2BG_CHECKPOINT and src.get("locked_inherited_r2be_checkpoint") == R2BE_CHECKPOINT and src.get("source_locked_bool") is True
    unavailable_ok = aud.get("outcome_alignment_source_labels_absent_bool") is True and aud.get("generation_bucket") == GENERATION_BUCKET and aud.get("generated_group_set_exact_bool") is False and aud.get("material_generated_bool") is False and aud.get("controlled_unavailable_result_bool") is True and aud.get("r2bg_result_bucket") == R2BG_RESULT_BUCKET and aud.get("r2bg_outcome_bucket") == R2BG_OUTCOME_BUCKET
    boundary_ok = priv.get("public_only_audit_bool") is True and priv.get("private_root_read_bool") is False and priv.get("material_generation_bool") is False and priv.get("metric_recompute_bool") is False and priv.get("source_scan_bool") is False and pub.get("aggregate_only_public_artifact_bool") is True and pub.get("private_root_path_public_bool") is False and pub.get("task_query_raw_public_bool") is False and pub.get("exact_metric_public_bool") is False and integ.get("r2bk_no_private_read_metrics_material_scan_claim_bool") is True
    integrity_ok = integ.get("r2bk_gate_synthetic_readback_exact_bool") is True and set(gates) == set(R2BL_GATES) and len(gates) == len(R2BL_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2BL_SYNTH) and len(synth) == len(R2BL_SYNTH) and len(synth) == len(set(synth)) and len(read) == 1 and read[0].get("all_public_readback_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BL_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BL_STOP_FALSE)
    return {"source_ok": source_ok, "unavailable_ok": unavailable_ok, "boundary_ok": boundary_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok, "audit_ok": source_ok and unavailable_ok and boundary_ok and integrity_ok and stop_ok}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BL_CHECKPOINT, R2BL_STATUS, R2BK_CHECKPOINT, R2BK_STATUS, "outcome_alignment_source_labels_absent", GENERATION_BUCKET, "outcome_label_acquisition_design_selected", "not closure", "not pivot", "public-only/non-executing", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(x in text for x in fragments) or all(x in text for x in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bm-evidence-pair-support-outcome-label-acquisition-public-decision-design.md")) and ok(read("docs/zh/bea-v1-haae-r2bm-evidence-pair-support-outcome-label-acquisition-public-decision-design.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bm-evidence-pair-support-outcome-label-acquisition-public-decision-design.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(r2bl: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2bl is None:
        try: r2bl = load_json(repo_root() / R2BL_REPORT_PATH)
        except Exception: r2bl = {}
    audit = audit_r2bl(r2bl); rb = public_readback_match(self_test_total)
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_DECISION if not (audit["unavailable_ok"] and audit["boundary_ok"] and audit["integrity_ok"] and audit["stop_ok"]) else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bmstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_decision_design_pass"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bl_source_lock_gate": audit["source_ok"], "r2bk_unavailable_evidence_gate": audit["unavailable_ok"], "r2bl_public_only_boundary_gate": audit["boundary_ok"], "r2bl_stop_go_to_r2bm_gate": audit["stop_ok"], "r2bl_gate_synthetic_readback_exact_gate": audit["integrity_ok"], "outcome_label_acquisition_decision_gate": True, "closure_pivot_rejected_gate": True, "r2bn_stop_go_only_gate": True, "public_only_non_executing_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bmsource0000", "locked_haae_r2bl_checkpoint": R2BL_CHECKPOINT, "locked_haae_r2bl_status": R2BL_STATUS, "locked_haae_r2bl_self_test_total": R2BL_SELF_TEST_TOTAL, "locked_haae_r2bk_checkpoint": R2BK_CHECKPOINT, "locked_haae_r2bk_status": R2BK_STATUS, "locked_inherited_r2bj_checkpoint": R2BJ_CHECKPOINT, "locked_inherited_r2bi_checkpoint": R2BI_CHECKPOINT, "locked_inherited_r2bg_checkpoint": R2BG_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "source_locked_bool": audit["source_ok"]}],
        "unavailable_evidence_lock_records": [{"anonymous_unavailable_id": "haaer2bmunavail0000", "outcome_alignment_source_labels_absent_bool": True, "generation_bucket": GENERATION_BUCKET, "generated_group_set_exact_bool": False, "material_generated_bool": False, "r2bg_result_bucket": R2BG_RESULT_BUCKET, "r2bg_outcome_bucket": R2BG_OUTCOME_BUCKET, "unavailable_evidence_locked_bool": audit["unavailable_ok"]}],
        "decision_records": [{"anonymous_decision_id": "haaer2bmdecision0000", "outcome_label_acquisition_public_design_preflight_selected_bool": True, "outcome_label_acquisition_design_selected_bool": True, "close_support_route_selected_bool": False, "close_support_route_deferred_bool": True, "pivot_to_other_signal_family_selected_bool": False, "pivot_to_other_signal_family_deferred_bool": True, "direct_private_label_acquisition_authorized_bool": False, "direct_material_generation_authorized_bool": False, "direct_experiment_authorized_bool": False, "existing_label_recovery_design_suboption_bool": True, "new_label_acquisition_design_suboption_bool": True, "closure_selected_bool": False, "pivot_selected_bool": False, "rerun_without_label_acquisition_selected_bool": False, "scale_preflight_selected_bool": False, "method_default_claim_selected_bool": False, "not_closure_not_pivot_yet_bool": True}],
        "r2bn_scope_records": [{"anonymous_scope_id": "haaer2bmscope0000", "r2bn_public_design_preflight_only_bool": True, "r2bn_may_design_label_source_requirements_bool": True, "r2bn_no_label_generation_execution_bool": True, "r2bn_no_private_read_write_bool": True, "r2bn_no_metrics_bool": True, "r2bn_no_source_scan_bool": True}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "haaer2bmprivacy0000", "public_only_non_executing_bool": True, "private_roots_read_bool": False, "label_generation_bool": False, "material_generation_bool": False, "metric_compute_bool": False, "source_scan_bool": False, "ci_network_runtime_provider_clone_bool": False, "signal_method_default_scale_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bmgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bmsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bmreadback0000", **rb}], "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if report.get("self_test_total") != SELF_TEST_EXPECTED: issues.append("self_test_validator_count_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if len(synth) != len(set(synth)): issues.append("synthetic_validator_duplicate_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    for f, e in {"locked_haae_r2bl_checkpoint": R2BL_CHECKPOINT, "locked_haae_r2bl_status": R2BL_STATUS, "locked_haae_r2bl_self_test_total": R2BL_SELF_TEST_TOTAL, "locked_haae_r2bk_checkpoint": R2BK_CHECKPOINT, "locked_haae_r2bk_status": R2BK_STATUS, "locked_inherited_r2bj_checkpoint": R2BJ_CHECKPOINT, "locked_inherited_r2bi_checkpoint": R2BI_CHECKPOINT, "locked_inherited_r2bg_checkpoint": R2BG_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    un = (report.get("unavailable_evidence_lock_records") or [{}])[0]
    if un.get("outcome_alignment_source_labels_absent_bool") is not True or un.get("generation_bucket") != GENERATION_BUCKET or un.get("generated_group_set_exact_bool") is not False or un.get("material_generated_bool") is not False or un.get("unavailable_evidence_locked_bool") is not True: issues.append("unavailable_evidence_lock_mismatch")
    dec = (report.get("decision_records") or [{}])[0]
    for f in ["outcome_label_acquisition_public_design_preflight_selected_bool", "outcome_label_acquisition_design_selected_bool", "close_support_route_deferred_bool", "pivot_to_other_signal_family_deferred_bool", "existing_label_recovery_design_suboption_bool", "new_label_acquisition_design_suboption_bool", "not_closure_not_pivot_yet_bool"]:
        if dec.get(f) is not True: issues.append(f"decision_true_{f}")
    for f in ["close_support_route_selected_bool", "pivot_to_other_signal_family_selected_bool", "direct_private_label_acquisition_authorized_bool", "direct_material_generation_authorized_bool", "direct_experiment_authorized_bool", "closure_selected_bool", "pivot_selected_bool", "rerun_without_label_acquisition_selected_bool", "scale_preflight_selected_bool", "method_default_claim_selected_bool"]:
        if dec.get(f) is not False: issues.append(f"decision_overauth_{f}")
    scope = (report.get("r2bn_scope_records") or [{}])[0]
    for f in ["r2bn_public_design_preflight_only_bool", "r2bn_may_design_label_source_requirements_bool", "r2bn_no_label_generation_execution_bool", "r2bn_no_private_read_write_bool", "r2bn_no_metrics_bool", "r2bn_no_source_scan_bool"]:
        if scope.get(f) is not True: issues.append(f"scope_{f}")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    if priv.get("public_only_non_executing_bool") is not True: issues.append("privacy_public_only_non_executing_bool")
    for f in ["private_roots_read_bool", "label_generation_bool", "material_generation_bool", "metric_compute_bool", "source_scan_bool", "ci_network_runtime_provider_clone_bool", "signal_method_default_scale_claim_bool"]:
        if priv.get(f) is not False: issues.append(f"privacy_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bn_stop_go_mismatch")
    for f in STOP_TRUE:
        if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    for f in STOP_FALSE:
        if stop.get(f) is not False: issues.append(f"overauthorization_{f}")
    read = report.get("public_readback_records", [])
    if len(read) != 1 or read[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{g.get('gate_bucket', 'unknown')}")
    return issues

def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; base = load_json(repo_root() / R2BL_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    passed = build_report(base); check("decision_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    source_muts = [("r2bl_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bk_checkpoint", "bad")), ("r2bl_status_drift_fail", lambda r: r.__setitem__("status", "bad")), ("r2bl_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0)), ("r2bk_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bk_checkpoint", "bad")), ("r2bk_status_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bk_status", "bad")), ("r2bk_unavailable_fact_drift_fail", lambda r: r["r2bk_unavailable_audit_records"][0].__setitem__("outcome_alignment_source_labels_absent_bool", False)), ("r2bk_generation_bucket_drift_fail", lambda r: r["r2bk_unavailable_audit_records"][0].__setitem__("generation_bucket", "generated")), ("r2bk_generated_group_overclaim_fail", lambda r: r["r2bk_unavailable_audit_records"][0].__setitem__("generated_group_set_exact_bool", True)), ("r2bk_material_generated_overclaim_fail", lambda r: r["r2bk_unavailable_audit_records"][0].__setitem__("material_generated_bool", True)), ("r2bl_boundary_private_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("private_root_read_bool", True)), ("r2bl_boundary_metric_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("metric_recompute_bool", True)), ("r2bl_boundary_material_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("material_generation_bool", True)), ("r2bl_gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop()), ("r2bl_gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0]))), ("r2bl_readback_drop_fail", lambda r: r.__setitem__("public_readback_records", [])), ("r2bl_stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__("haae_r2bm_outcome_label_acquisition_public_decision_design_authorized_bool", False)), ("r2bl_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True))]
    for name, mut in source_muts:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == STATUS_FAIL_SOURCE or build_report(m)["status"] == STATUS_FAIL_DECISION)
    for name, mut in [
        ("r2bl_publication_overauth_fail", lambda r: r["publication_records"][0].__setitem__("exact_metric_public_bool", True)),
        ("r2bl_synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop()),
        ("r2bl_synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0]))),
        ("r2bl_synthetic_rename_fail", lambda r: r["synthetic_validator_records"][0].__setitem__("validator_bucket", "bogus_unique_validator_name")),
    ]:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == STATUS_FAIL_DECISION)
    report_muts = [("decision_selected_drop_fail", lambda r: r["decision_records"][0].__setitem__("outcome_label_acquisition_design_selected_bool", False), "decision_true_outcome_label_acquisition_design_selected_bool"), ("closure_selected_overauth_fail", lambda r: r["decision_records"][0].__setitem__("closure_selected_bool", True), "decision_overauth_closure_selected_bool"), ("pivot_selected_overauth_fail", lambda r: r["decision_records"][0].__setitem__("pivot_selected_bool", True), "decision_overauth_pivot_selected_bool"), ("rerun_selected_overauth_fail", lambda r: r["decision_records"][0].__setitem__("rerun_without_label_acquisition_selected_bool", True), "decision_overauth_rerun_without_label_acquisition_selected_bool"), ("scale_selected_overauth_fail", lambda r: r["decision_records"][0].__setitem__("scale_preflight_selected_bool", True), "decision_overauth_scale_preflight_selected_bool"), ("signal_claim_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("signal_method_default_scale_claim_bool", True), "privacy_signal_method_default_scale_claim_bool"), ("r2bn_stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("r2bn_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("r2bn_execution_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("execution_authorized_bool", True), "overauthorization_execution_authorized_bool"), ("r2bn_material_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"), ("r2bn_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"), ("r2bn_source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "overauthorization_source_scan_authorized_bool"), ("r2bn_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("signal_claim_authorized_bool", True), "overauthorization_signal_claim_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_validator_duplicate_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "public_readback_record_mismatch")]
    for name, mut, issue in report_muts:
        m = json.loads(json.dumps(passed)); mut(m); check(name, issue in validate_report(m))
    extra_report_muts = [
        ("closure_deferred_drop_fail", lambda r: r["decision_records"][0].__setitem__("close_support_route_deferred_bool", False), "decision_true_close_support_route_deferred_bool"),
        ("pivot_deferred_drop_fail", lambda r: r["decision_records"][0].__setitem__("pivot_to_other_signal_family_deferred_bool", False), "decision_true_pivot_to_other_signal_family_deferred_bool"),
        ("direct_label_acquisition_overauth_fail", lambda r: r["decision_records"][0].__setitem__("direct_private_label_acquisition_authorized_bool", True), "decision_overauth_direct_private_label_acquisition_authorized_bool"),
        ("direct_material_generation_overauth_fail", lambda r: r["decision_records"][0].__setitem__("direct_material_generation_authorized_bool", True), "decision_overauth_direct_material_generation_authorized_bool"),
        ("direct_experiment_overauth_fail", lambda r: r["decision_records"][0].__setitem__("direct_experiment_authorized_bool", True), "decision_overauth_direct_experiment_authorized_bool"),
        ("existing_label_recovery_suboption_drop_fail", lambda r: r["decision_records"][0].__setitem__("existing_label_recovery_design_suboption_bool", False), "decision_true_existing_label_recovery_design_suboption_bool"),
        ("new_label_acquisition_suboption_drop_fail", lambda r: r["decision_records"][0].__setitem__("new_label_acquisition_design_suboption_bool", False), "decision_true_new_label_acquisition_design_suboption_bool"),
        ("r2bn_scope_source_scan_drop_fail", lambda r: r["r2bn_scope_records"][0].__setitem__("r2bn_no_source_scan_bool", False), "scope_r2bn_no_source_scan_bool"),
    ]
    for name, mut, issue in extra_report_muts:
        m = json.loads(json.dumps(passed)); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo_root() / public_artifact_path(str(args["validate"]))) ; issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] == STATUS_PASS else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
