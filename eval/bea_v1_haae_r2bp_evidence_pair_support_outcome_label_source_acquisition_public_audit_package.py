#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BP outcome-label source acquisition public audit package."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BP Evidence-Pair Support Outcome Label Source Acquisition Public Audit Package"
SLUG = "bea_v1_haae_r2bp_evidence_pair_support_outcome_label_source_acquisition_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BO_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bo_evidence_pair_support_explicit_local_outcome_label_source_acquisition/bea_v1_haae_r2bo_evidence_pair_support_explicit_local_outcome_label_source_acquisition_report.json")

R2BO_CHECKPOINT = "07b9eef"
R2BO_STATUS = "haae_r2bo_explicit_local_outcome_label_source_acquisition_complete_r2bp_public_audit_authorized"
R2BO_SELF_TEST_TOTAL = 51
R2BN_CHECKPOINT = "af901f6"
R2BN_STATUS = "haae_r2bn_outcome_label_acquisition_public_design_preflight_complete_r2bo_explicit_local_label_source_acquisition_authorized"
R2BN_SELF_TEST_TOTAL = 55
R2BM_CHECKPOINT = "219c890"
R2BL_CHECKPOINT = "41aef9e"
R2BK_CHECKPOINT = "7073b12"
R2BE_CHECKPOINT = "c3901d6"

STATUS_PASS = "haae_r2bp_outcome_label_source_acquisition_public_audit_complete_r2bq_decision_design_authorized"
STATUS_FAIL_SOURCE = "haae_r2bp_fail_closed_r2bo_source_lock_mismatch"
STATUS_FAIL_EXECUTION = "haae_r2bp_fail_closed_r2bo_execution_integrity_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2bp_fail_closed_r2bo_boundary_or_privacy_mismatch"
STATUS_FAIL_STOP_GO = "haae_r2bp_fail_closed_r2bo_stop_go_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2bp_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bp_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BQ Evidence-Pair Support Outcome Label Source Acquisition Next-Step Decision Design Package"

R2BO_GROUPS = ["outcome_label_source_manifest_private", "outcome_label_task_alignment_private", "outcome_label_pair_family_alignment_private", "outcome_label_provenance_private", "manual_label_import_private", "existing_label_recovery_private", "label_quality_qa_private", "parent_r2be_row_ref_private"]
R2BO_GATES = ["r2bn_source_lock_gate", "default_noop_or_explicit_opt_in_gate", "explicit_argument_gate", "r2be_input_root_safety_gate", "label_source_manifest_safety_gate", "private_output_root_safety_gate", "input_schema_group_exact_gate", "output_schema_group_exact_gate", "label_source_policy_gate", "bounds_gate", "no_material_repair_metric_scan_gate", "aggregate_only_public_gate", "r2bp_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2BO_SYNTH = ["default_noop_pass", "explicit_synthetic_success_pass", "safe_parser_fail", "missing_allow_flag_fail", "missing_r2be_root_fail", "missing_label_manifest_fail", "missing_output_root_fail", "bad_r2bn_checkpoint_fail", "bad_r2bn_status_fail", "r2bn_stop_go_overauth_fail", "input_root_in_repo_fail", "input_root_missing_fail", "input_root_symlink_fail", "input_group_missing_fail", "input_group_extra_fail", "input_group_symlink_fail", "label_manifest_missing_fail", "label_manifest_tmp_rejected_fail", "label_manifest_traversal_rejected_fail", "label_manifest_symlink_fail", "label_manifest_schema_invalid_fail", "output_root_in_repo_fail", "nested_roots_fail", "output_root_symlink_fail", "nonempty_unowned_output_fail", "owned_rerun_pass", "output_group_symlink_escape_fail", "source_locked_drift_fail", "explicit_status_drift_fail", "explicit_group_exact_drift_fail", "explicit_execution_private_read_drift_fail", "explicit_execution_label_manifest_read_drift_fail", "explicit_execution_private_write_drift_fail", "explicit_root_safety_drift_fail", "output_group_missing_fail", "output_group_extra_fail", "bounds_drift_fail", "material_repair_overauth_fail", "metric_overauth_fail", "source_scan_overauth_fail", "publication_raw_label_overauth_fail", "stop_go_true_drop_fail", "stop_go_private_overauth_fail", "stop_go_material_overauth_fail", "stop_go_metric_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "public_leak_fail"]
GATES = ["r2bo_source_lock_gate", "r2bo_explicit_execution_gate", "r2bo_group_exact_gate", "r2bo_label_acquisition_bucket_gate", "r2bo_bounds_gate", "r2bo_privacy_publication_gate", "r2bo_no_material_repair_metric_scan_gate", "r2bo_gate_synthetic_readback_exact_gate", "r2bo_stop_go_to_r2bp_only_gate", "public_only_audit_gate", "r2bq_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["audit_pass", "safe_parser_fail", "r2bo_status_drift_fail", "r2bo_checkpoint_drift_fail", "r2bo_self_test_drift_fail", "r2bn_source_lock_drift_fail", "r2bn_status_drift_fail", "r2be_inherited_lock_drift_fail", "explicit_execution_bucket_drift_fail", "explicit_opt_in_drift_fail", "private_r2be_read_drift_fail", "label_manifest_read_drift_fail", "private_output_write_drift_fail", "label_acquisition_bool_drift_fail", "group_exact_drift_fail", "group_missing_fail", "group_extra_fail", "label_acquisition_bucket_drift_fail", "bounds_drift_fail", "privacy_aggregate_drop_fail", "privacy_private_root_overauth_fail", "privacy_raw_label_overauth_fail", "material_repair_overauth_fail", "metric_overauth_fail", "source_scan_overauth_fail", "runtime_overauth_fail", "r2bo_gate_drop_fail", "r2bo_gate_duplicate_fail", "r2bo_synthetic_drop_fail", "r2bo_synthetic_duplicate_fail", "r2bo_readback_drop_fail", "r2bo_stop_true_drop_fail", "r2bo_stop_private_overauth_fail", "r2bo_stop_material_overauth_fail", "r2bo_stop_metric_overauth_fail", "execution_private_read_attestation_drift_fail", "execution_label_manifest_attestation_drift_fail", "execution_private_output_attestation_drift_fail", "r2bq_stop_true_drop_fail", "r2bq_private_overauth_fail", "r2bq_execution_overauth_fail", "r2bq_material_overauth_fail", "r2bq_metric_overauth_fail", "r2bq_claim_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)

R2BO_STOP_TRUE = ["haae_r2bp_outcome_label_source_acquisition_public_audit_authorized_bool", "r2bp_public_only_audit_bool", "r2bp_no_private_read_bool", "r2bp_no_metric_computation_bool", "r2bp_no_material_generation_bool", "r2bp_audit_label_acquisition_result_bool"]
R2BO_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "label_acquisition_authorized_bool", "label_generation_authorized_bool", "material_generation_authorized_bool", "material_repair_generation_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
STOP_TRUE = ["haae_r2bq_outcome_label_source_acquisition_next_step_decision_design_authorized_bool", "r2bq_public_only_decision_design_bool", "r2bq_no_private_read_write_bool", "r2bq_no_execution_bool", "r2bq_no_material_repair_generation_bool", "r2bq_no_metric_recompute_bool", "r2bo_label_acquisition_result_locked_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "execution_authorized_bool", "label_acquisition_authorized_bool", "label_generation_authorized_bool", "material_generation_authorized_bool", "material_repair_execution_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|groups/|fixtures/r14|\.jsonl", re.I)), ("raw_task", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_label", re.compile(r"gold_spans|hard_negatives|rationale|start_line|end_line|mined_high_confidence", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|private_source_ref|\.rs\b|crates/openlocus-|hash_value", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|top[-_]?k|\bmrr\b|hit[_-]?rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

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

def audit_r2bo(r2bo: dict[str, Any]) -> dict[str, bool]:
    src = (r2bo.get("source_lock_records") or [{}])[0]; exe = (r2bo.get("execution_mode_records") or [{}])[0]; grp = (r2bo.get("acquisition_group_records") or [{}])[0]; bounds = (r2bo.get("bounds_records") or [{}])[0]; priv = (r2bo.get("privacy_boundary_records") or [{}])[0]; root = (r2bo.get("root_safety_records") or [{}])[0]; stop = (r2bo.get("stop_go_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2bo.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2bo.get("synthetic_validator_records", [])]; read = r2bo.get("public_readback_records", [])
    source_ok = r2bo.get("status") == R2BO_STATUS and r2bo.get("self_test_total") == R2BO_SELF_TEST_TOTAL and r2bo.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bn_checkpoint") == R2BN_CHECKPOINT and src.get("locked_haae_r2bn_status") == R2BN_STATUS and src.get("locked_haae_r2bn_self_test_total") == R2BN_SELF_TEST_TOTAL and src.get("locked_inherited_r2bm_checkpoint") == R2BM_CHECKPOINT and src.get("locked_inherited_r2bl_checkpoint") == R2BL_CHECKPOINT and src.get("locked_inherited_r2bk_checkpoint") == R2BK_CHECKPOINT and src.get("locked_inherited_r2be_checkpoint") == R2BE_CHECKPOINT and src.get("source_locked_bool") is True
    execution_ok = exe.get("execution_mode_bucket") == "explicit_local_label_source_acquisition" and exe.get("explicit_opt_in_bool") is True and exe.get("private_r2be_material_read_bool") is True and exe.get("label_source_manifest_read_bool") is True and exe.get("private_output_write_bool") is True and exe.get("label_source_acquisition_bool") is True and exe.get("material_repair_generation_bool") is False and exe.get("experiment_metric_bool") is False and exe.get("source_candidate_corpus_scan_bool") is False
    group_ok = grp.get("generated_group_set_exact_bool") is True and grp.get("label_acquisition_bucket") == "labels_acquired_private" and grp.get("required_group_buckets") == R2BO_GROUPS
    boundary_ok = bounds.get("bounds_satisfied_bool") is True and bounds.get("private_rows_bucket") == "private_rows_le_20000" and bounds.get("target_tasks_bucket") == "target_tasks_20" and root.get("no_root_path_or_basename_public_bool") is True and all(priv.get(f) is False for f in ["private_root_path_public_bool", "task_query_path_span_label_public_bool", "exact_count_rate_score_public_bool", "material_repair_generation_bool", "experiment_metrics_bool", "source_scan_bool", "runtime_ci_network_provider_bool", "signal_method_default_scale_claim_bool"]) and priv.get("aggregate_only_public_artifact_bool") is True
    integrity_ok = set(gates) == set(R2BO_GATES) and len(gates) == len(R2BO_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2BO_SYNTH) and len(synth) == len(R2BO_SYNTH) and len(synth) == len(set(synth)) and len(read) == 1 and read[0].get("all_public_readback_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BO_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BO_STOP_FALSE)
    return {"source_ok": source_ok, "execution_ok": execution_ok, "group_ok": group_ok, "boundary_ok": boundary_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok, "audit_ok": source_ok and execution_ok and group_ok and boundary_ok and integrity_ok and stop_ok}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BO_CHECKPOINT, R2BO_STATUS, "R2BO public artifact", "explicit local outcome-label source acquisition", "labels_acquired_private", "outcome_label_source_manifest_private", "aggregate-only", "no private read", "no material repair", "no experiment metrics", "no source scan", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bp-evidence-pair-support-outcome-label-source-acquisition-public-audit-package.md")) and ok(read("docs/zh/bea-v1-haae-r2bp-evidence-pair-support-outcome-label-source-acquisition-public-audit-package.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bp-evidence-pair-support-outcome-label-source-acquisition-public-audit-package.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(r2bo: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2bo is None:
        try: r2bo = load_json(repo_root() / R2BO_REPORT_PATH)
        except Exception: r2bo = {}
    audit = audit_r2bo(r2bo); rb = public_readback_match(self_test_total)
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_EXECUTION if not (audit["execution_ok"] and audit["group_ok"] and audit["integrity_ok"]) else (STATUS_FAIL_BOUNDARY if not audit["boundary_ok"] else (STATUS_FAIL_STOP_GO if not audit["stop_ok"] else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS))))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bpstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_public_audit_pass"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bo_source_lock_gate": audit["source_ok"], "r2bo_explicit_execution_gate": audit["execution_ok"], "r2bo_group_exact_gate": audit["group_ok"], "r2bo_label_acquisition_bucket_gate": audit["group_ok"], "r2bo_bounds_gate": audit["boundary_ok"], "r2bo_privacy_publication_gate": audit["boundary_ok"], "r2bo_no_material_repair_metric_scan_gate": audit["boundary_ok"], "r2bo_gate_synthetic_readback_exact_gate": audit["integrity_ok"], "r2bo_stop_go_to_r2bp_only_gate": audit["stop_ok"], "public_only_audit_gate": True, "r2bq_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bpsource0000", "locked_haae_r2bo_checkpoint": R2BO_CHECKPOINT, "locked_haae_r2bo_status": R2BO_STATUS, "locked_haae_r2bo_self_test_total": R2BO_SELF_TEST_TOTAL, "locked_haae_r2bn_checkpoint": R2BN_CHECKPOINT, "locked_haae_r2bn_status": R2BN_STATUS, "locked_inherited_r2bm_checkpoint": R2BM_CHECKPOINT, "locked_inherited_r2bl_checkpoint": R2BL_CHECKPOINT, "locked_inherited_r2bk_checkpoint": R2BK_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "source_locked_bool": audit["source_ok"]}],
        "r2bo_execution_audit_records": [{"anonymous_execution_audit_id": "haaer2bpexec0000", "execution_mode_bucket": "explicit_local_label_source_acquisition", "explicit_opt_in_bool": audit["execution_ok"], "private_r2be_material_read_attested_bool": True, "label_source_manifest_read_attested_bool": True, "private_output_write_attested_bool": True, "label_acquisition_bucket": "labels_acquired_private", "status_execution_consistency_bool": audit["execution_ok"] and audit["group_ok"]}],
        "r2bo_group_audit_records": [{"anonymous_group_audit_id": "haaer2bpgroup0000", "generated_group_set_exact_bool": audit["group_ok"], "required_group_buckets": R2BO_GROUPS, "bounds_satisfied_bool": audit["boundary_ok"], "private_rows_bucket": "private_rows_le_20000", "target_tasks_bucket": "target_tasks_20"}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "haaer2bpprivacy0000", "public_only_audit_bool": True, "read_only_r2bo_public_artifact_bool": True, "private_root_read_bool": False, "private_output_read_bool": False, "label_reacquisition_bool": False, "material_repair_generation_bool": False, "metric_recompute_bool": False, "source_scan_bool": False, "runtime_ci_network_bool": False, "raw_private_exact_publication_bool": False, "aggregate_only_public_artifact_bool": True}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bpgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bpsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bpreadback0000", **rb}], "stop_go_records": [stop]}
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
    expected = {"locked_haae_r2bo_checkpoint": R2BO_CHECKPOINT, "locked_haae_r2bo_status": R2BO_STATUS, "locked_haae_r2bo_self_test_total": R2BO_SELF_TEST_TOTAL, "locked_haae_r2bn_checkpoint": R2BN_CHECKPOINT, "locked_haae_r2bn_status": R2BN_STATUS, "locked_inherited_r2bm_checkpoint": R2BM_CHECKPOINT, "locked_inherited_r2bl_checkpoint": R2BL_CHECKPOINT, "locked_inherited_r2bk_checkpoint": R2BK_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT}
    for f, e in expected.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    exe = (report.get("r2bo_execution_audit_records") or [{}])[0]
    if exe.get("execution_mode_bucket") != "explicit_local_label_source_acquisition" or exe.get("explicit_opt_in_bool") is not True or exe.get("status_execution_consistency_bool") is not True or exe.get("label_acquisition_bucket") != "labels_acquired_private": issues.append("execution_audit_mismatch")
    for f in ["private_r2be_material_read_attested_bool", "label_source_manifest_read_attested_bool", "private_output_write_attested_bool"]:
        if exe.get(f) is not True: issues.append(f"execution_audit_{f}")
    grp = (report.get("r2bo_group_audit_records") or [{}])[0]
    if grp.get("required_group_buckets") != R2BO_GROUPS or grp.get("generated_group_set_exact_bool") is not True or grp.get("bounds_satisfied_bool") is not True: issues.append("group_bounds_mismatch")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    for f in ["public_only_audit_bool", "read_only_r2bo_public_artifact_bool", "aggregate_only_public_artifact_bool"]:
        if priv.get(f) is not True: issues.append(f"privacy_{f}")
    for f in ["private_root_read_bool", "private_output_read_bool", "label_reacquisition_bool", "material_repair_generation_bool", "metric_recompute_bool", "source_scan_bool", "runtime_ci_network_bool", "raw_private_exact_publication_bool"]:
        if priv.get(f) is not False: issues.append(f"privacy_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bq_stop_go_mismatch")
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
    failures: list[str] = []; base = load_json(repo_root() / R2BO_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    passed = build_report(base); check("audit_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    muts = [("r2bo_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE), ("r2bo_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bn_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2bo_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE), ("r2bn_source_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2bm_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2bn_status_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bn_status", "bad"), STATUS_FAIL_SOURCE), ("r2be_inherited_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2be_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("explicit_execution_bucket_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("execution_mode_bucket", "default"), STATUS_FAIL_EXECUTION), ("explicit_opt_in_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("explicit_opt_in_bool", False), STATUS_FAIL_EXECUTION), ("private_r2be_read_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_r2be_material_read_bool", False), STATUS_FAIL_EXECUTION), ("label_manifest_read_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("label_source_manifest_read_bool", False), STATUS_FAIL_EXECUTION), ("private_output_write_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_output_write_bool", False), STATUS_FAIL_EXECUTION), ("label_acquisition_bool_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("label_source_acquisition_bool", False), STATUS_FAIL_EXECUTION), ("group_exact_drift_fail", lambda r: r["acquisition_group_records"][0].__setitem__("generated_group_set_exact_bool", False), STATUS_FAIL_EXECUTION), ("group_missing_fail", lambda r: r["acquisition_group_records"][0]["required_group_buckets"].pop(), STATUS_FAIL_EXECUTION), ("group_extra_fail", lambda r: r["acquisition_group_records"][0]["required_group_buckets"].append("extra"), STATUS_FAIL_EXECUTION), ("label_acquisition_bucket_drift_fail", lambda r: r["acquisition_group_records"][0].__setitem__("label_acquisition_bucket", "none"), STATUS_FAIL_EXECUTION), ("bounds_drift_fail", lambda r: r["bounds_records"][0].__setitem__("bounds_satisfied_bool", False), STATUS_FAIL_BOUNDARY), ("privacy_aggregate_drop_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("aggregate_only_public_artifact_bool", False), STATUS_FAIL_BOUNDARY), ("privacy_private_root_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("private_root_path_public_bool", True), STATUS_FAIL_BOUNDARY), ("privacy_raw_label_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("task_query_path_span_label_public_bool", True), STATUS_FAIL_BOUNDARY), ("material_repair_overauth_fail", lambda r: r["execution_mode_records"][0].__setitem__("material_repair_generation_bool", True), STATUS_FAIL_EXECUTION), ("metric_overauth_fail", lambda r: r["execution_mode_records"][0].__setitem__("experiment_metric_bool", True), STATUS_FAIL_EXECUTION), ("source_scan_overauth_fail", lambda r: r["execution_mode_records"][0].__setitem__("source_candidate_corpus_scan_bool", True), STATUS_FAIL_EXECUTION), ("runtime_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("runtime_ci_network_provider_bool", True), STATUS_FAIL_BOUNDARY), ("r2bo_gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), STATUS_FAIL_EXECUTION), ("r2bo_gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), STATUS_FAIL_EXECUTION), ("r2bo_synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), STATUS_FAIL_EXECUTION), ("r2bo_synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), STATUS_FAIL_EXECUTION), ("r2bo_readback_drop_fail", lambda r: r.__setitem__("public_readback_records", []), STATUS_FAIL_EXECUTION), ("r2bo_stop_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(R2BO_STOP_TRUE[0], False), STATUS_FAIL_STOP_GO), ("r2bo_stop_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_STOP_GO), ("r2bo_stop_material_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), STATUS_FAIL_STOP_GO), ("r2bo_stop_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), STATUS_FAIL_STOP_GO)]
    for name, mut, status in muts:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == status)
    report_muts = [("execution_private_read_attestation_drift_fail", lambda r: r["r2bo_execution_audit_records"][0].__setitem__("private_r2be_material_read_attested_bool", False), "execution_audit_private_r2be_material_read_attested_bool"), ("execution_label_manifest_attestation_drift_fail", lambda r: r["r2bo_execution_audit_records"][0].__setitem__("label_source_manifest_read_attested_bool", False), "execution_audit_label_source_manifest_read_attested_bool"), ("execution_private_output_attestation_drift_fail", lambda r: r["r2bo_execution_audit_records"][0].__setitem__("private_output_write_attested_bool", False), "execution_audit_private_output_write_attested_bool"), ("r2bq_stop_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("r2bq_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("r2bq_execution_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("execution_authorized_bool", True), "overauthorization_execution_authorized_bool"), ("r2bq_material_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"), ("r2bq_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"), ("r2bq_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("signal_claim_authorized_bool", True), "overauthorization_signal_claim_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_validator_duplicate_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "public_readback_record_mismatch")]
    for name, mut, issue in report_muts:
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
