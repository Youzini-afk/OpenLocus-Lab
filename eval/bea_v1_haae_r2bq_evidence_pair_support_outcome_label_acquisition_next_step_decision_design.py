#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BQ outcome-label acquisition next-step decision/design.

Public-only decision package. It reads only the R2BP public artifact, locks the
R2BO/R2BP label-acquisition audit facts, and authorizes only R2BR public design
preflight. It performs no private reads, execution, repair/generation, metrics,
source scan, runtime, network, or claims.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BQ Evidence-Pair Support Outcome Label Source Acquisition Next-Step Decision Design Package"
SLUG = "bea_v1_haae_r2bq_evidence_pair_support_outcome_label_acquisition_next_step_decision_design"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BP_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bp_evidence_pair_support_outcome_label_source_acquisition_public_audit_package/bea_v1_haae_r2bp_evidence_pair_support_outcome_label_source_acquisition_public_audit_package_report.json")

R2BP_CHECKPOINT = "82c5d65"
R2BP_STATUS = "haae_r2bp_outcome_label_source_acquisition_public_audit_complete_r2bq_decision_design_authorized"
R2BP_SELF_TEST_TOTAL = 51
R2BO_CHECKPOINT = "07b9eef"
R2BO_STATUS = "haae_r2bo_explicit_local_outcome_label_source_acquisition_complete_r2bp_public_audit_authorized"
R2BO_SELF_TEST_TOTAL = 51
R2BN_CHECKPOINT = "af901f6"
R2BM_CHECKPOINT = "219c890"
R2BL_CHECKPOINT = "41aef9e"
R2BK_CHECKPOINT = "7073b12"
R2BE_CHECKPOINT = "c3901d6"

STATUS_PASS = "haae_r2bq_outcome_label_acquisition_next_step_decision_design_complete_r2br_repair_design_preflight_authorized"
STATUS_FAIL_SOURCE = "haae_r2bq_fail_closed_r2bp_source_lock_mismatch"
STATUS_FAIL_FACT = "haae_r2bq_fail_closed_r2bo_label_acquisition_fact_mismatch"
STATUS_FAIL_DECISION = "haae_r2bq_fail_closed_decision_or_stop_go_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2bq_fail_closed_boundary_overauthorization"
STATUS_FAIL_PRIVACY = "haae_r2bq_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bq_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BR Evidence-Pair Support Outcome-Aligned Material Repair Public Design Preflight"

R2BO_GROUPS = ["outcome_label_source_manifest_private", "outcome_label_task_alignment_private", "outcome_label_pair_family_alignment_private", "outcome_label_provenance_private", "manual_label_import_private", "existing_label_recovery_private", "label_quality_qa_private", "parent_r2be_row_ref_private"]
R2BP_GATES = ["r2bo_source_lock_gate", "r2bo_explicit_execution_gate", "r2bo_group_exact_gate", "r2bo_label_acquisition_bucket_gate", "r2bo_bounds_gate", "r2bo_privacy_publication_gate", "r2bo_no_material_repair_metric_scan_gate", "r2bo_gate_synthetic_readback_exact_gate", "r2bo_stop_go_to_r2bp_only_gate", "public_only_audit_gate", "r2bq_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2BP_SYNTH = ["audit_pass", "safe_parser_fail", "r2bo_status_drift_fail", "r2bo_checkpoint_drift_fail", "r2bo_self_test_drift_fail", "r2bn_source_lock_drift_fail", "r2bn_status_drift_fail", "r2be_inherited_lock_drift_fail", "explicit_execution_bucket_drift_fail", "explicit_opt_in_drift_fail", "private_r2be_read_drift_fail", "label_manifest_read_drift_fail", "private_output_write_drift_fail", "label_acquisition_bool_drift_fail", "group_exact_drift_fail", "group_missing_fail", "group_extra_fail", "label_acquisition_bucket_drift_fail", "bounds_drift_fail", "privacy_aggregate_drop_fail", "privacy_private_root_overauth_fail", "privacy_raw_label_overauth_fail", "material_repair_overauth_fail", "metric_overauth_fail", "source_scan_overauth_fail", "runtime_overauth_fail", "r2bo_gate_drop_fail", "r2bo_gate_duplicate_fail", "r2bo_synthetic_drop_fail", "r2bo_synthetic_duplicate_fail", "r2bo_readback_drop_fail", "r2bo_stop_true_drop_fail", "r2bo_stop_private_overauth_fail", "r2bo_stop_material_overauth_fail", "r2bo_stop_metric_overauth_fail", "execution_private_read_attestation_drift_fail", "execution_label_manifest_attestation_drift_fail", "execution_private_output_attestation_drift_fail", "r2bq_stop_true_drop_fail", "r2bq_private_overauth_fail", "r2bq_execution_overauth_fail", "r2bq_material_overauth_fail", "r2bq_metric_overauth_fail", "r2bq_claim_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "public_leak_fail"]
R2BP_STOP_TRUE = ["haae_r2bq_outcome_label_source_acquisition_next_step_decision_design_authorized_bool", "r2bq_public_only_decision_design_bool", "r2bq_no_private_read_write_bool", "r2bq_no_execution_bool", "r2bq_no_material_repair_generation_bool", "r2bq_no_metric_recompute_bool", "r2bo_label_acquisition_result_locked_bool"]
R2BP_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "execution_authorized_bool", "label_acquisition_authorized_bool", "label_generation_authorized_bool", "material_generation_authorized_bool", "material_repair_execution_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
STOP_TRUE = ["haae_r2br_outcome_aligned_material_repair_public_design_preflight_authorized_bool", "r2br_public_only_design_preflight_bool", "r2br_no_private_read_write_bool", "r2br_no_execution_bool", "r2br_no_material_generation_bool", "r2br_no_metric_recompute_bool", "r2br_no_source_scan_bool", "r2bo_label_acquisition_result_locked_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "execution_authorized_bool", "label_acquisition_authorized_bool", "label_generation_authorized_bool", "material_generation_authorized_bool", "material_repair_execution_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
GATES = ["r2bp_source_lock_gate", "r2bo_label_acquisition_fact_gate", "decision_select_r2br_gate", "reject_direct_repair_experiment_scale_claim_gate", "public_only_boundary_gate", "r2br_stop_go_only_gate", "gate_synthetic_readback_exact_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["decision_pass", "safe_parser_fail", "r2bp_status_drift_fail", "r2bp_self_test_drift_fail", "r2bo_checkpoint_drift_fail", "r2bo_status_drift_fail", "r2bo_self_test_drift_fail", "r2bn_inherited_drift_fail", "r2be_inherited_drift_fail", "r2bp_forbidden_scan_fail", "r2bo_group_missing_fail", "r2bo_group_extra_fail", "r2bo_group_exact_false_fail", "label_bucket_drift_fail", "r2bo_execution_attestation_drift_fail", "aggregate_boundary_drift_fail", "material_repair_overauth_fail", "metric_overauth_fail", "source_scan_overauth_fail", "private_read_overauth_fail", "r2bp_gate_drop_fail", "r2bp_gate_duplicate_fail", "r2bp_synthetic_drop_fail", "r2bp_synthetic_duplicate_fail", "r2bp_synthetic_rename_fail", "r2bp_readback_drop_fail", "r2bp_stop_true_drop_fail", "r2bp_stop_private_overauth_fail", "decision_selected_false_fail", "rationale_bucket_drift_fail", "direct_repair_selected_fail", "direct_repair_execution_selected_fail", "direct_experiment_selected_fail", "scale_selected_fail", "closure_selected_fail", "closure_deferred_drop_fail", "pivot_selected_fail", "pivot_deferred_drop_fail", "method_default_claim_selected_fail", "stop_true_drop_fail", "stop_private_overauth_fail", "stop_execution_overauth_fail", "stop_material_overauth_fail", "stop_metric_overauth_fail", "stop_source_scan_overauth_fail", "stop_claim_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|fixtures/r14|\.jsonl", re.I)), ("raw_task", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_label", re.compile(r"gold_spans|hard_negatives|start_line|end_line|mined_high_confidence", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|private_source_ref|\.rs\b|crates/openlocus-|hash_value", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|top[-_]?k|\bmrr\b|hit[_-]?rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    findings = [name for name, pat in LEAK_PATTERNS if pat.search(json.dumps(report, sort_keys=True))]
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

def audit_r2bp(r2bp: dict[str, Any]) -> dict[str, bool]:
    src = (r2bp.get("source_lock_records") or [{}])[0]; exe = (r2bp.get("r2bo_execution_audit_records") or [{}])[0]; grp = (r2bp.get("r2bo_group_audit_records") or [{}])[0]; priv = (r2bp.get("privacy_boundary_records") or [{}])[0]; stop = (r2bp.get("stop_go_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2bp.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2bp.get("synthetic_validator_records", [])]; read = r2bp.get("public_readback_records", [])
    source_ok = r2bp.get("status") == R2BP_STATUS and r2bp.get("self_test_total") == R2BP_SELF_TEST_TOTAL and r2bp.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bo_checkpoint") == R2BO_CHECKPOINT and src.get("locked_haae_r2bo_status") == R2BO_STATUS and src.get("locked_haae_r2bo_self_test_total") == R2BO_SELF_TEST_TOTAL and src.get("locked_haae_r2bn_checkpoint") == R2BN_CHECKPOINT and src.get("locked_inherited_r2bm_checkpoint") == R2BM_CHECKPOINT and src.get("locked_inherited_r2bl_checkpoint") == R2BL_CHECKPOINT and src.get("locked_inherited_r2bk_checkpoint") == R2BK_CHECKPOINT and src.get("locked_inherited_r2be_checkpoint") == R2BE_CHECKPOINT and src.get("source_locked_bool") is True
    facts_ok = exe.get("execution_mode_bucket") == "explicit_local_label_source_acquisition" and exe.get("status_execution_consistency_bool") is True and exe.get("label_acquisition_bucket") == "labels_acquired_private" and exe.get("explicit_opt_in_bool") is True and exe.get("private_r2be_material_read_attested_bool") is True and exe.get("label_source_manifest_read_attested_bool") is True and exe.get("private_output_write_attested_bool") is True and grp.get("required_group_buckets") == R2BO_GROUPS and grp.get("generated_group_set_exact_bool") is True and grp.get("bounds_satisfied_bool") is True and grp.get("private_rows_bucket") == "private_rows_le_20000"
    boundary_ok = priv.get("public_only_audit_bool") is True and priv.get("read_only_r2bo_public_artifact_bool") is True and priv.get("aggregate_only_public_artifact_bool") is True and all(priv.get(f) is False for f in ["private_root_read_bool", "private_output_read_bool", "label_reacquisition_bool", "material_repair_generation_bool", "metric_recompute_bool", "source_scan_bool", "runtime_ci_network_bool", "raw_private_exact_publication_bool"])
    integrity_ok = set(gates) == set(R2BP_GATES) and len(gates) == len(R2BP_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2BP_SYNTH) and len(synth) == len(R2BP_SYNTH) and len(synth) == len(set(synth)) and len(read) == 1 and read[0].get("all_public_readback_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BP_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BP_STOP_FALSE)
    return {"source_ok": source_ok, "facts_ok": facts_ok, "boundary_ok": boundary_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok, "audit_ok": source_ok and facts_ok and boundary_ok and integrity_ok and stop_ok}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BP_CHECKPOINT, R2BP_STATUS, R2BO_CHECKPOINT, R2BO_STATUS, "outcome_aligned_material_repair_public_design_preflight_selected", "labels_acquired_but_material_repair_not_yet_designed", "R2BR", "public-only decision", "no private read", "no material repair", "no experiment metrics", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bq-evidence-pair-support-outcome-label-acquisition-next-step-decision-design.md")) and ok(read("docs/zh/bea-v1-haae-r2bq-evidence-pair-support-outcome-label-acquisition-next-step-decision-design.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bq-evidence-pair-support-outcome-label-acquisition-next-step-decision-design.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(r2bp: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2bp is None:
        try: r2bp = load_json(repo_root() / R2BP_REPORT_PATH)
        except Exception: r2bp = {}
    audit = audit_r2bp(r2bp); rb = public_readback_match(self_test_total)
    decision_ok = audit["audit_ok"]
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_FACT if not (audit["facts_ok"] and audit["integrity_ok"]) else (STATUS_FAIL_BOUNDARY if not audit["boundary_ok"] else (STATUS_FAIL_DECISION if not audit["stop_ok"] else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS))))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bqstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_decision_validation_pass"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bp_source_lock_gate": audit["source_ok"], "r2bo_label_acquisition_fact_gate": audit["facts_ok"], "decision_select_r2br_gate": decision_ok, "reject_direct_repair_experiment_scale_claim_gate": True, "public_only_boundary_gate": audit["boundary_ok"], "r2br_stop_go_only_gate": passed, "gate_synthetic_readback_exact_gate": audit["integrity_ok"], "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bqsource0000", "locked_haae_r2bp_checkpoint": R2BP_CHECKPOINT, "locked_haae_r2bp_status": R2BP_STATUS, "locked_haae_r2bp_self_test_total": R2BP_SELF_TEST_TOTAL, "locked_haae_r2bo_checkpoint": R2BO_CHECKPOINT, "locked_haae_r2bo_status": R2BO_STATUS, "locked_haae_r2bo_self_test_total": R2BO_SELF_TEST_TOTAL, "locked_inherited_r2bn_checkpoint": R2BN_CHECKPOINT, "locked_inherited_r2bm_checkpoint": R2BM_CHECKPOINT, "locked_inherited_r2bk_checkpoint": R2BK_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "source_locked_bool": audit["source_ok"]}],
        "r2bo_label_acquisition_fact_records": [{"anonymous_fact_id": "haaer2bqfact0000", "labels_acquired_private_bool": True, "label_acquisition_bucket": "labels_acquired_private", "outcome_label_source_manifest_private_bool": True, "private_r2be_material_read_attested_bool": audit["facts_ok"], "label_source_manifest_read_attested_bool": audit["facts_ok"], "private_output_write_attested_bool": audit["facts_ok"], "generated_group_set_exact_bool": audit["facts_ok"], "aggregate_only_public_artifact_bool": audit["boundary_ok"], "no_material_repair_metrics_source_scan_bool": audit["boundary_ok"]}],
        "decision_records": [{"anonymous_decision_id": "haaer2bqdecision0000", "outcome_aligned_material_repair_public_design_preflight_selected_bool": True, "direct_material_repair_selected_bool": False, "direct_material_repair_execution_selected_bool": False, "direct_experiment_selected_bool": False, "scale_selected_bool": False, "closure_selected_bool": False, "close_support_route_deferred_bool": True, "pivot_selected_bool": False, "pivot_deferred_bool": True, "method_default_winner_signal_scale_claim_selected_bool": False, "rationale_bucket": "labels_acquired_but_material_repair_not_yet_designed"}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "haaer2bqprivacy0000", "public_only_decision_bool": True, "private_root_read_bool": False, "private_write_bool": False, "label_acquisition_generation_bool": False, "material_repair_generation_bool": False, "metric_recompute_bool": False, "source_scan_bool": False, "runtime_ci_network_provider_bool": False, "raw_private_exact_publication_bool": False, "signal_method_default_scale_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bqgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bqsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bqreadback0000", **rb}], "stop_go_records": [stop]}
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
    expected = {"locked_haae_r2bp_checkpoint": R2BP_CHECKPOINT, "locked_haae_r2bp_status": R2BP_STATUS, "locked_haae_r2bp_self_test_total": R2BP_SELF_TEST_TOTAL, "locked_haae_r2bo_checkpoint": R2BO_CHECKPOINT, "locked_haae_r2bo_status": R2BO_STATUS, "locked_haae_r2bo_self_test_total": R2BO_SELF_TEST_TOTAL, "locked_inherited_r2bn_checkpoint": R2BN_CHECKPOINT, "locked_inherited_r2bm_checkpoint": R2BM_CHECKPOINT, "locked_inherited_r2bk_checkpoint": R2BK_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT}
    for f, e in expected.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    fact = (report.get("r2bo_label_acquisition_fact_records") or [{}])[0]
    for f in ["labels_acquired_private_bool", "outcome_label_source_manifest_private_bool", "private_r2be_material_read_attested_bool", "label_source_manifest_read_attested_bool", "private_output_write_attested_bool", "generated_group_set_exact_bool", "aggregate_only_public_artifact_bool", "no_material_repair_metrics_source_scan_bool"]:
        if fact.get(f) is not True: issues.append(f"fact_{f}")
    if fact.get("label_acquisition_bucket") != "labels_acquired_private": issues.append("fact_label_acquisition_bucket")
    dec = (report.get("decision_records") or [{}])[0]
    if dec.get("outcome_aligned_material_repair_public_design_preflight_selected_bool") is not True or dec.get("rationale_bucket") != "labels_acquired_but_material_repair_not_yet_designed": issues.append("decision_selection_mismatch")
    for f in ["close_support_route_deferred_bool", "pivot_deferred_bool"]:
        if dec.get(f) is not True: issues.append(f"decision_{f}")
    for f in ["direct_material_repair_selected_bool", "direct_material_repair_execution_selected_bool", "direct_experiment_selected_bool", "scale_selected_bool", "closure_selected_bool", "pivot_selected_bool", "method_default_winner_signal_scale_claim_selected_bool"]:
        if dec.get(f) is not False: issues.append(f"decision_{f}")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    if priv.get("public_only_decision_bool") is not True: issues.append("privacy_public_only_decision_bool")
    for f in ["private_root_read_bool", "private_write_bool", "label_acquisition_generation_bool", "material_repair_generation_bool", "metric_recompute_bool", "source_scan_bool", "runtime_ci_network_provider_bool", "raw_private_exact_publication_bool", "signal_method_default_scale_claim_bool"]:
        if priv.get(f) is not False: issues.append(f"privacy_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2br_stop_go_mismatch")
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
    failures: list[str] = []; base = load_json(repo_root() / R2BP_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    passed = build_report(base); check("decision_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    muts = [("r2bp_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE), ("r2bp_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE), ("r2bo_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bo_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2bo_status_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bo_status", "bad"), STATUS_FAIL_SOURCE), ("r2bo_self_test_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bo_self_test_total", 0), STATUS_FAIL_SOURCE), ("r2bn_inherited_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bn_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2be_inherited_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2be_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2bp_forbidden_scan_fail", lambda r: r["forbidden_scan"].__setitem__("status", "fail"), STATUS_FAIL_SOURCE), ("r2bo_group_missing_fail", lambda r: r["r2bo_group_audit_records"][0]["required_group_buckets"].pop(), STATUS_FAIL_FACT), ("r2bo_group_extra_fail", lambda r: r["r2bo_group_audit_records"][0]["required_group_buckets"].append("extra"), STATUS_FAIL_FACT), ("r2bo_group_exact_false_fail", lambda r: r["r2bo_group_audit_records"][0].__setitem__("generated_group_set_exact_bool", False), STATUS_FAIL_FACT), ("label_bucket_drift_fail", lambda r: r["r2bo_execution_audit_records"][0].__setitem__("label_acquisition_bucket", "none"), STATUS_FAIL_FACT), ("aggregate_boundary_drift_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("aggregate_only_public_artifact_bool", False), STATUS_FAIL_BOUNDARY), ("material_repair_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("material_repair_generation_bool", True), STATUS_FAIL_BOUNDARY), ("metric_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("metric_recompute_bool", True), STATUS_FAIL_BOUNDARY), ("source_scan_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("source_scan_bool", True), STATUS_FAIL_BOUNDARY), ("private_read_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("private_root_read_bool", True), STATUS_FAIL_BOUNDARY), ("r2bp_gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), STATUS_FAIL_FACT), ("r2bp_gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), STATUS_FAIL_FACT), ("r2bp_readback_drop_fail", lambda r: r.__setitem__("public_readback_records", []), STATUS_FAIL_FACT), ("r2bp_stop_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(R2BP_STOP_TRUE[0], False), STATUS_FAIL_DECISION), ("r2bp_stop_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_DECISION)]
    for name, mut, status in muts:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == status)
    extra_source_muts = [("r2bo_execution_attestation_drift_fail", lambda r: r["r2bo_execution_audit_records"][0].__setitem__("private_r2be_material_read_attested_bool", False), STATUS_FAIL_FACT), ("r2bp_synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), STATUS_FAIL_FACT), ("r2bp_synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(r["synthetic_validator_records"][0]), STATUS_FAIL_FACT), ("r2bp_synthetic_rename_fail", lambda r: r["synthetic_validator_records"][0].__setitem__("validator_bucket", "renamed"), STATUS_FAIL_FACT)]
    for name, mut, status in extra_source_muts:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == status)
    report_muts = [("decision_selected_false_fail", lambda r: r["decision_records"][0].__setitem__("outcome_aligned_material_repair_public_design_preflight_selected_bool", False), "decision_selection_mismatch"), ("rationale_bucket_drift_fail", lambda r: r["decision_records"][0].__setitem__("rationale_bucket", "bad"), "decision_selection_mismatch"), ("direct_repair_selected_fail", lambda r: r["decision_records"][0].__setitem__("direct_material_repair_selected_bool", True), "decision_direct_material_repair_selected_bool"), ("direct_experiment_selected_fail", lambda r: r["decision_records"][0].__setitem__("direct_experiment_selected_bool", True), "decision_direct_experiment_selected_bool"), ("scale_selected_fail", lambda r: r["decision_records"][0].__setitem__("scale_selected_bool", True), "decision_scale_selected_bool"), ("closure_selected_fail", lambda r: r["decision_records"][0].__setitem__("closure_selected_bool", True), "decision_closure_selected_bool"), ("pivot_selected_fail", lambda r: r["decision_records"][0].__setitem__("pivot_selected_bool", True), "decision_pivot_selected_bool"), ("method_default_claim_selected_fail", lambda r: r["decision_records"][0].__setitem__("method_default_winner_signal_scale_claim_selected_bool", True), "decision_method_default_winner_signal_scale_claim_selected_bool"), ("stop_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("stop_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("stop_execution_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("execution_authorized_bool", True), "overauthorization_execution_authorized_bool"), ("stop_material_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"), ("stop_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"), ("stop_source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "overauthorization_source_scan_authorized_bool"), ("stop_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("signal_claim_authorized_bool", True), "overauthorization_signal_claim_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_validator_duplicate_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "public_readback_record_mismatch")]
    for name, mut, issue in report_muts:
        m = json.loads(json.dumps(passed)); mut(m); check(name, issue in validate_report(m))
    extra_report_muts = [("direct_repair_execution_selected_fail", lambda r: r["decision_records"][0].__setitem__("direct_material_repair_execution_selected_bool", True), "decision_direct_material_repair_execution_selected_bool"), ("closure_deferred_drop_fail", lambda r: r["decision_records"][0].__setitem__("close_support_route_deferred_bool", False), "decision_close_support_route_deferred_bool"), ("pivot_deferred_drop_fail", lambda r: r["decision_records"][0].__setitem__("pivot_deferred_bool", False), "decision_pivot_deferred_bool")]
    for name, mut, issue in extra_report_muts:
        m = json.loads(json.dumps(passed)); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 gold_spans exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
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
