#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BC mechanism redesign public design preflight.

Public-only, non-executing redesign requirements package after R2BB. Reads only
public artifacts for locks; never reads private roots/material, generates
material, recomputes metrics, scans source/candidate/corpus, or runs runtime.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BC Evidence-Pair Support Mechanism Redesign Public Design Preflight"
SLUG = "bea_v1_haae_r2bc_evidence_pair_support_mechanism_redesign_public_design_preflight"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"

R2BB_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bb_evidence_pair_support_robustness_next_step_decision_package/bea_v1_haae_r2bb_evidence_pair_support_robustness_next_step_decision_package_report.json")
R2BA_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ba_evidence_pair_support_robustness_experiment_public_audit_package/bea_v1_haae_r2ba_evidence_pair_support_robustness_experiment_public_audit_package_report.json")
R2AZ_REPORT_PATH = Path("artifacts/bea_v1_haae_r2az_evidence_pair_support_explicit_local_robustness_experiment/bea_v1_haae_r2az_evidence_pair_support_explicit_local_robustness_experiment_report.json")

R2BB_CHECKPOINT = "a624728"
R2BB_STATUS = "haae_r2bb_evidence_pair_support_robustness_next_step_decision_complete_r2bc_mechanism_redesign_public_design_preflight_authorized"
R2BB_SELF_TEST_TOTAL = 34
R2BA_CHECKPOINT = "f8984bf"
R2BA_STATUS = "haae_r2ba_evidence_pair_support_robustness_experiment_public_audit_complete_r2bb_next_step_decision_authorized_negative_robustness_evidence"
R2BA_SELF_TEST_TOTAL = 34
R2AZ_CHECKPOINT = "72590e5"
R2AZ_STATUS = "haae_r2az_explicit_local_robustness_experiment_complete_r2ba_public_audit_authorized_artifact_likely"
R2AY_CHECKPOINT = "126dc18"
R2AX_CHECKPOINT = "f3add65"
R2AW_CHECKPOINT = "bc44454"
R2AN_CHECKPOINT = "93bba5f"
R2AT_CHECKPOINT = "0c9c108"
R2AP_CHECKPOINT = "87ea9de"

STATUS_PASS = "haae_r2bc_evidence_pair_support_mechanism_redesign_public_design_preflight_complete_r2bd_redesigned_material_generation_public_design_preflight_authorized"
STATUS_FAIL_SOURCE = "haae_r2bc_fail_closed_source_lock_or_decision_mismatch"
STATUS_FAIL_DESIGN = "haae_r2bc_fail_closed_redesign_requirement_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2bc_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bc_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BD Evidence-Pair Support Redesigned Material Generation Public Design Preflight"

CONTROL_FAMILIES = ["matched_hard_negative_control", "same_source_family_control", "cross_task_semantic_mismatch_control", "path_token_matched_control", "query_only_control", "evidence_only_control", "support_relation_broken_control", "gold_blind_decoy_control", "source_family_balance_control"]
BUCKETS = {"r2az_result_bucket": "artifact_likely", "support_control_separation_bucket": "support_control_separation_collapsed", "control_rejection_bucket": "control_rejection_failed", "path_confound_risk_bucket": "path_confound_risk_elevated", "support_signal_bucket": "support_signal_bucket_low"}
R2BB_GATES = ["r2ba_source_lock_gate", "r2ba_bucket_evidence_gate", "r2ba_public_boundary_gate", "r2ba_gate_synthetic_readback_exact_gate", "r2ba_stop_go_exact_gate", "optional_r2az_cross_audit_gate", "mechanism_redesign_decision_gate", "current_route_robustness_rejection_gate", "no_scale_external_material_continuation_gate", "r2bc_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2BB_SYNTH = ["decision_pass", "safe_parser_fail", "r2ba_checkpoint_drift_fail", "r2ba_status_drift_fail", "r2ba_self_test_drift_fail", "r2ba_forbidden_scan_fail", "r2ba_boundary_drift_fail", "r2ba_bucket_result_drift_fail", "r2ba_bucket_support_control_drift_fail", "r2ba_bucket_control_rejection_drift_fail", "r2ba_bucket_path_confound_drift_fail", "r2ba_bucket_support_signal_drift_fail", "r2ba_gate_drop_fail", "r2ba_gate_duplicate_fail", "r2ba_synthetic_drop_fail", "r2ba_synthetic_duplicate_fail", "r2ba_readback_drop_fail", "r2ba_readback_duplicate_fail", "r2ba_stop_go_true_drop_fail", "r2ba_stop_go_private_read_overauth_fail", "r2ba_stop_go_material_overauth_fail", "r2ba_stop_go_claim_overauth_fail", "r2az_cross_audit_drift_fail", "decision_mechanism_redesign_drop_fail", "decision_scale_selected_fail", "decision_current_route_continue_fail", "r2bc_stop_go_true_drop_fail", "r2bc_stop_go_private_read_overauth_fail", "r2bc_stop_go_scale_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "readback_record_fail", "public_leak_fail"]
R2BB_STOP_TRUE = ["haae_r2bc_evidence_pair_support_mechanism_redesign_public_design_preflight_authorized_bool", "r2bc_public_only_design_preflight_bool", "current_support_route_robustness_rejected_bool", "negative_robustness_evidence_locked_bool", "no_private_read_bool", "no_metric_recompute_bool", "no_material_generation_bool", "no_method_default_scale_claim_bool"]
R2BB_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "experiment_execution_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "external_validation_authorized_bool", "scale_preflight_authorized_bool", "scale_execution_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "validated_signal_claim_authorized_bool", "raw_publication_authorized_bool"]

GATES = ["r2bb_source_lock_decision_gate", "r2ba_negative_audit_lock_gate", "r2az_bucket_lock_gate", "inherited_source_lock_gate", "control_family_exact_set_gate", "path_confound_mitigation_gate", "gold_isolation_policy_gate", "support_control_gate_design_gate", "future_generation_contract_bounds_gate", "public_only_non_executing_gate", "r2bd_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["preflight_pass", "safe_parser_fail", "r2bb_checkpoint_drift_fail", "r2bb_status_drift_fail", "r2bb_self_test_drift_fail", "r2bb_forbidden_scan_fail", "r2bb_decision_drop_fail", "r2bb_scale_overselect_fail", "r2bb_boundary_drift_fail", "r2bb_gate_drop_fail", "r2bb_gate_duplicate_fail", "r2bb_synthetic_drop_fail", "r2bb_readback_drop_fail", "r2bb_stop_go_overauth_fail", "r2ba_status_drift_fail", "r2az_bucket_drift_fail", "source_inherited_lock_drift_fail", "context_bucket_drift_fail", "privacy_boundary_overauth_fail", "control_family_missing_fail", "control_family_duplicate_fail", "path_mitigation_drop_fail", "gold_isolation_drop_fail", "support_control_gate_drop_fail", "future_bounds_drift_fail", "future_control_family_missing_fail", "future_execution_overauth_fail", "stop_go_true_drop_fail", "stop_go_private_read_overauth_fail", "stop_go_explicit_generation_overauth_fail", "stop_go_downstream_claim_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)

STOP_TRUE = ["haae_r2bd_evidence_pair_support_redesigned_material_generation_public_design_preflight_authorized_bool", "r2bd_public_only_generation_design_preflight_bool", "mechanism_redesign_requirements_complete_bool", "current_support_route_robustness_rejected_bool", "negative_robustness_evidence_locked_bool", "future_explicit_opt_in_generation_design_only_bool", "no_private_read_bool", "no_metric_recompute_bool", "no_material_generation_bool", "no_method_default_scale_validated_signal_claim_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "experiment_execution_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "external_validation_authorized_bool", "scale_preflight_authorized_bool", "scale_execution_authorized_bool", "explicit_private_generation_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "validated_signal_claim_authorized_bool", "downstream_value_claim_authorized_bool", "raw_publication_authorized_bool"]

LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|source_ref|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|exact_top_k_value|\bmrr\b|hit_rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

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

def audit_r2bb(r2bb: dict[str, Any]) -> dict[str, bool]:
    src = (r2bb.get("source_lock_records") or [{}])[0]; dec = (r2bb.get("decision_records") or [{}])[0]; boundary = (r2bb.get("public_only_boundary_records") or [{}])[0]; aud = (r2bb.get("r2ba_audit_records") or [{}])[0]; stop = (r2bb.get("stop_go_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2bb.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2bb.get("synthetic_validator_records", [])]; read = r2bb.get("public_readback_records", [])
    source_ok = r2bb.get("status") == R2BB_STATUS and r2bb.get("self_test_total") == R2BB_SELF_TEST_TOTAL and r2bb.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2ba_checkpoint") == R2BA_CHECKPOINT and src.get("locked_haae_r2ba_status") == R2BA_STATUS and src.get("locked_haae_r2ba_self_test_total") == R2BA_SELF_TEST_TOTAL and src.get("locked_haae_r2az_checkpoint") == R2AZ_CHECKPOINT and src.get("locked_haae_r2az_status") == R2AZ_STATUS and src.get("locked_inherited_r2ay_checkpoint") == R2AY_CHECKPOINT and src.get("locked_inherited_r2ax_checkpoint") == R2AX_CHECKPOINT and src.get("locked_inherited_r2aw_checkpoint") == R2AW_CHECKPOINT and src.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT and src.get("locked_inherited_r2at_checkpoint") == R2AT_CHECKPOINT and src.get("locked_inherited_r2ap_checkpoint") == R2AP_CHECKPOINT and src.get("source_locked_bool") is True
    decision_ok = dec.get("mechanism_redesign_preflight_selected_bool") is True and dec.get("current_evidence_pair_support_route_rejected_as_robust_signal_bool") is True and dec.get("negative_robustness_evidence_locked_bool") is True and dec.get("no_method_default_runtime_scale_winner_validated_signal_downstream_value_claim_bool") is True and all(dec.get(f) is False for f in ["scale_preflight_selected_bool", "external_robustness_execution_selected_bool", "new_material_generation_selected_bool", "current_route_continuation_selected_bool"])
    boundary_ok = boundary.get("public_only_decision_design_bool") is True and all(boundary.get(f) is False for f in ["private_read_bool", "private_write_bool", "material_generation_bool", "metric_recompute_bool", "source_candidate_corpus_scan_bool", "runtime_retrieval_ci_network_provider_clone_bool", "raw_or_exact_private_publication_bool"])
    bucket_ok = all(aud.get(k) == v for k, v in BUCKETS.items()) and aud.get("negative_robustness_evidence_confirmed_bool") is True
    integrity_ok = set(gates) == set(R2BB_GATES) and len(gates) == len(R2BB_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2BB_SYNTH) and len(synth) == len(R2BB_SYNTH) and len(synth) == len(set(synth)) and len(read) == 1 and read[0].get("all_public_readback_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BB_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BB_STOP_FALSE)
    return {"source_ok": source_ok, "decision_ok": decision_ok, "boundary_ok": boundary_ok, "bucket_ok": bucket_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok, "audit_ok": source_ok and decision_ok and boundary_ok and bucket_ok and integrity_ok and stop_ok}

def audit_r2ba_r2az(r2ba: dict[str, Any] | None, r2az: dict[str, Any] | None) -> bool:
    if not r2ba or not r2az: return False
    m = (r2az.get("aggregate_metric_records") or [{}])[0]
    return r2ba.get("status") == R2BA_STATUS and r2ba.get("self_test_total") == R2BA_SELF_TEST_TOTAL and r2az.get("status") == R2AZ_STATUS and m.get("robustness_result_bucket") == "artifact_likely" and m.get("support_vs_control_robustness_separation_bucket") == "support_control_separation_collapsed" and m.get("shuffled_cross_task_control_rejection_bucket") == "control_rejection_failed" and m.get("path_token_confound_risk_bucket") == "path_confound_risk_elevated" and m.get("support_signal_retention_bucket") == "support_signal_bucket_low"

def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BB_CHECKPOINT, R2BB_STATUS, R2BA_CHECKPOINT, R2BA_STATUS, R2AZ_CHECKPOINT, R2AZ_STATUS, R2AY_CHECKPOINT, R2AX_CHECKPOINT, R2AW_CHECKPOINT, R2AN_CHECKPOINT, R2AT_CHECKPOINT, R2AP_CHECKPOINT, "redesign requirements package", "existing support/complementarity insufficient after robustness failure", "robust signal not claimed", "matched_hard_negative_control", "path_token_matched_control", "gold eval-only", "elevated confound fails robust-signal gates", "target_tasks_16_to_20", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bc-evidence-pair-support-mechanism-redesign-public-design-preflight.md")) and ok(read("docs/zh/bea-v1-haae-r2bc-evidence-pair-support-mechanism-redesign-public-design-preflight.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bc-evidence-pair-support-mechanism-redesign-public-design-preflight.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def design_records() -> dict[str, Any]:
    return {
        "redesign_requirement_records": [{"anonymous_requirement_id": "haaer2bcreq0000", "existing_support_complementarity_insufficient_after_robustness_failure_bool": True, "mechanism_redesign_motivated_bool": True, "robust_signal_claimed_bool": False, "redesign_requirements_package_bool": True}],
        "control_family_requirement_records": [{"anonymous_control_family_id": "haaer2bccontrol0000", "required_control_family_buckets": CONTROL_FAMILIES, "control_family_set_exact_bool": True}],
        "path_confound_mitigation_records": [{"anonymous_path_mitigation_id": "haaer2bcpath0000", "path_token_normalization_or_masking_required_bool": True, "same_directory_source_family_matched_controls_required_bool": True, "path_token_matched_negatives_required_bool": True, "source_family_balance_buckets_required_bool": True, "public_aggregate_confound_risk_bucket_required_bool": True, "elevated_confound_fails_robust_signal_gates_bool": True}],
        "gold_isolation_policy_records": [{"anonymous_gold_policy_id": "haaer2bcgold0000", "gold_eval_only_bool": True, "gold_used_for_material_selection_bool": False, "gold_used_for_support_pair_construction_bool": False, "gold_used_for_control_construction_bool": False, "gold_used_for_retrieval_ranking_source_scan_candidate_generation_bool": False, "public_only_pass_fail_bucket_bool": True}],
        "support_control_gate_records": [{"anonymous_support_control_gate_id": "haaer2bcgatepolicy0000", "support_retention_not_low_required_bool": True, "support_control_separation_not_collapsed_required_bool": True, "hard_negative_rejection_not_failed_required_bool": True, "shuffled_cross_task_control_rejection_not_failed_required_bool": True, "path_confound_risk_not_elevated_required_bool": True, "gold_isolation_pass_required_bool": True, "variant_control_coverage_complete_required_bool": True, "any_core_failure_means_artifact_weak_inconclusive_not_support_signal_bool": True}],
        "future_generation_contract_records": [{"anonymous_future_contract_id": "haaer2bcfuture0000", "target_tasks_bucket": "target_tasks_16_to_20", "private_rows_bucket": "private_rows_le_20000", "depth_bucket": "depth_le_40", "support_pairs_bucket": "support_pairs_le_120_per_task", "control_pairs_bucket": "control_pairs_le_120_per_task", "total_pairs_bucket": "total_pairs_le_240_per_task", "source_files_bucket": "source_files_le_500", "wall_clock_bucket": "wall_clock_le_20_minutes", "required_control_family_buckets": CONTROL_FAMILIES, "execution_authorization_bool": False, "design_only_bounds_bool": True}],
    }

def build_report(r2bb: dict[str, Any] | None = None, r2ba: dict[str, Any] | None = None, r2az: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2bb is None:
        try: r2bb = load_json(repo / R2BB_REPORT_PATH)
        except Exception: r2bb = {}
    if r2ba is None:
        try: r2ba = load_json(repo / R2BA_REPORT_PATH)
        except Exception: r2ba = None
    if r2az is None:
        try: r2az = load_json(repo / R2AZ_REPORT_PATH)
        except Exception: r2az = None
    audit = audit_r2bb(r2bb); inherited_ok = audit_r2ba_r2az(r2ba, r2az); rb = public_readback_match(self_test_total)
    design = design_records()
    design_ok = inherited_ok
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_DESIGN if not (audit["audit_ok"] and design_ok) else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bcstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_redesign_preflight_pass"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bb_source_lock_decision_gate": audit["source_ok"] and audit["decision_ok"], "r2ba_negative_audit_lock_gate": inherited_ok, "r2az_bucket_lock_gate": inherited_ok and audit["bucket_ok"], "inherited_source_lock_gate": audit["source_ok"], "control_family_exact_set_gate": True, "path_confound_mitigation_gate": True, "gold_isolation_policy_gate": True, "support_control_gate_design_gate": True, "future_generation_contract_bounds_gate": True, "public_only_non_executing_gate": True, "r2bd_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bcsource0000", "locked_haae_r2bb_checkpoint": R2BB_CHECKPOINT, "locked_haae_r2bb_status": R2BB_STATUS, "locked_haae_r2bb_self_test_total": R2BB_SELF_TEST_TOTAL, "locked_haae_r2ba_checkpoint": R2BA_CHECKPOINT, "locked_haae_r2ba_status": R2BA_STATUS, "locked_haae_r2ba_self_test_total": R2BA_SELF_TEST_TOTAL, "locked_haae_r2az_checkpoint": R2AZ_CHECKPOINT, "locked_haae_r2az_status": R2AZ_STATUS, "locked_inherited_r2ay_checkpoint": R2AY_CHECKPOINT, "locked_inherited_r2ax_checkpoint": R2AX_CHECKPOINT, "locked_inherited_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "source_locked_bool": audit["source_ok"] and inherited_ok}],
        "r2bb_context_audit_records": [{"anonymous_context_audit_id": "haaer2bbaudit0000", "r2bb_decision_exact_bool": audit["decision_ok"], "r2bb_public_boundary_bool": audit["boundary_ok"], "r2bb_gate_synthetic_readback_exact_bool": audit["integrity_ok"], "r2bb_stop_go_exact_bool": audit["stop_ok"], **BUCKETS}],
        "privacy_boundary_records": [{"anonymous_privacy_boundary_id": "haaer2bcprivacy0000", "public_only_non_executing_bool": True, "private_read_bool": False, "private_write_bool": False, "material_generation_bool": False, "metric_recompute_bool": False, "source_candidate_corpus_scan_bool": False, "runtime_retrieval_ci_network_provider_clone_bool": False, "raw_exact_private_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bcgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bcsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bcreadback0000", **rb}],
        "stop_go_records": [stop]}
    report.update(design)
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
    for f, e in {"locked_haae_r2bb_checkpoint": R2BB_CHECKPOINT, "locked_haae_r2bb_status": R2BB_STATUS, "locked_haae_r2bb_self_test_total": R2BB_SELF_TEST_TOTAL, "locked_haae_r2ba_checkpoint": R2BA_CHECKPOINT, "locked_haae_r2ba_status": R2BA_STATUS, "locked_haae_r2ba_self_test_total": R2BA_SELF_TEST_TOTAL, "locked_haae_r2az_checkpoint": R2AZ_CHECKPOINT, "locked_haae_r2az_status": R2AZ_STATUS, "locked_inherited_r2ay_checkpoint": R2AY_CHECKPOINT, "locked_inherited_r2ax_checkpoint": R2AX_CHECKPOINT, "locked_inherited_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    ctx = (report.get("r2bb_context_audit_records") or [{}])[0]
    for f in ["r2bb_decision_exact_bool", "r2bb_public_boundary_bool", "r2bb_gate_synthetic_readback_exact_bool", "r2bb_stop_go_exact_bool"]:
        if ctx.get(f) is not True: issues.append(f"r2bb_context_{f}")
    for f, e in BUCKETS.items():
        if ctx.get(f) != e: issues.append(f"r2bb_context_{f}")
    privacy = (report.get("privacy_boundary_records") or [{}])[0]
    if privacy.get("public_only_non_executing_bool") is not True: issues.append("privacy_public_only_non_executing_bool")
    for f in ["private_read_bool", "private_write_bool", "material_generation_bool", "metric_recompute_bool", "source_candidate_corpus_scan_bool", "runtime_retrieval_ci_network_provider_clone_bool", "raw_exact_private_publication_bool"]:
        if privacy.get(f) is not False: issues.append(f"privacy_{f}")
    req = (report.get("redesign_requirement_records") or [{}])[0]
    if req.get("existing_support_complementarity_insufficient_after_robustness_failure_bool") is not True or req.get("robust_signal_claimed_bool") is not False: issues.append("redesign_requirement_mismatch")
    fam = (report.get("control_family_requirement_records") or [{}])[0].get("required_control_family_buckets", [])
    if set(fam) != set(CONTROL_FAMILIES) or len(fam) != len(CONTROL_FAMILIES): issues.append("control_family_set_mismatch")
    path = (report.get("path_confound_mitigation_records") or [{}])[0]
    for f in ["path_token_normalization_or_masking_required_bool", "same_directory_source_family_matched_controls_required_bool", "path_token_matched_negatives_required_bool", "source_family_balance_buckets_required_bool", "public_aggregate_confound_risk_bucket_required_bool", "elevated_confound_fails_robust_signal_gates_bool"]:
        if path.get(f) is not True: issues.append("gate_failed_path_confound_mitigation_gate")
    gold = (report.get("gold_isolation_policy_records") or [{}])[0]
    if gold.get("gold_eval_only_bool") is not True or gold.get("public_only_pass_fail_bucket_bool") is not True or any(gold.get(f) is not False for f in ["gold_used_for_material_selection_bool", "gold_used_for_support_pair_construction_bool", "gold_used_for_control_construction_bool", "gold_used_for_retrieval_ranking_source_scan_candidate_generation_bool"]): issues.append("gate_failed_gold_isolation_policy_gate")
    support = (report.get("support_control_gate_records") or [{}])[0]
    for f in ["support_retention_not_low_required_bool", "support_control_separation_not_collapsed_required_bool", "hard_negative_rejection_not_failed_required_bool", "shuffled_cross_task_control_rejection_not_failed_required_bool", "path_confound_risk_not_elevated_required_bool", "gold_isolation_pass_required_bool", "variant_control_coverage_complete_required_bool", "any_core_failure_means_artifact_weak_inconclusive_not_support_signal_bool"]:
        if support.get(f) is not True: issues.append("gate_failed_support_control_gate_design_gate")
    fut = (report.get("future_generation_contract_records") or [{}])[0]
    for f, e in {"target_tasks_bucket": "target_tasks_16_to_20", "private_rows_bucket": "private_rows_le_20000", "depth_bucket": "depth_le_40", "support_pairs_bucket": "support_pairs_le_120_per_task", "control_pairs_bucket": "control_pairs_le_120_per_task", "total_pairs_bucket": "total_pairs_le_240_per_task", "source_files_bucket": "source_files_le_500", "wall_clock_bucket": "wall_clock_le_20_minutes"}.items():
        if fut.get(f) != e: issues.append(f"future_{f}")
    if fut.get("execution_authorization_bool") is not False or fut.get("design_only_bounds_bool") is not True: issues.append("future_execution_boundary_mismatch")
    if set(fut.get("required_control_family_buckets", [])) != set(CONTROL_FAMILIES) or len(fut.get("required_control_family_buckets", [])) != len(CONTROL_FAMILIES): issues.append("future_control_family_set_mismatch")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bd_stop_go_mismatch")
    for f in STOP_TRUE:
        if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    for f in STOP_FALSE:
        if stop.get(f) is not False: issues.append(f"overauthorization_{f}")
    rb = report.get("public_readback_records", [])
    if len(rb) != 1 or rb[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{g.get('gate_bucket', 'unknown')}")
    return issues

def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; repo = Path(__file__).resolve().parents[1]; bb = load_json(repo / R2BB_REPORT_PATH); ba = load_json(repo / R2BA_REPORT_PATH); az = load_json(repo / R2AZ_REPORT_PATH)
    def check(n: str, c: bool) -> None:
        if not c: failures.append(n)
    passed = build_report(bb, ba, az); check("preflight_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    muts = [("r2bb_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2ba_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2bb_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE), ("r2bb_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE), ("r2bb_forbidden_scan_fail", lambda r: r["forbidden_scan"].__setitem__("status", "fail"), STATUS_FAIL_SOURCE), ("r2bb_decision_drop_fail", lambda r: r["decision_records"][0].__setitem__("mechanism_redesign_preflight_selected_bool", False), STATUS_FAIL_DESIGN), ("r2bb_scale_overselect_fail", lambda r: r["decision_records"][0].__setitem__("scale_preflight_selected_bool", True), STATUS_FAIL_DESIGN), ("r2bb_boundary_drift_fail", lambda r: r["public_only_boundary_records"][0].__setitem__("private_read_bool", True), STATUS_FAIL_DESIGN), ("r2bb_gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), STATUS_FAIL_DESIGN), ("r2bb_gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), STATUS_FAIL_DESIGN), ("r2bb_synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), STATUS_FAIL_DESIGN), ("r2bb_readback_drop_fail", lambda r: r.__setitem__("public_readback_records", []), STATUS_FAIL_DESIGN), ("r2bb_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_DESIGN)]
    for n, mut, st in muts:
        m = json.loads(json.dumps(bb)); mut(m); check(n, build_report(m, ba, az)["status"] == st)
    m = json.loads(json.dumps(ba)); m["status"] = "bad"; check("r2ba_status_drift_fail", build_report(bb, m, az)["status"] == STATUS_FAIL_DESIGN)
    m = json.loads(json.dumps(az)); m["aggregate_metric_records"][0]["robustness_result_bucket"] = "bad"; check("r2az_bucket_drift_fail", build_report(bb, ba, m)["status"] == STATUS_FAIL_DESIGN)
    report_mut = [
        ("source_inherited_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2at_checkpoint", "bad"), "source_locked_inherited_r2at_checkpoint"),
        ("context_bucket_drift_fail", lambda r: r["r2bb_context_audit_records"][0].__setitem__("support_signal_bucket", "bad"), "r2bb_context_support_signal_bucket"),
        ("privacy_boundary_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("private_read_bool", True), "privacy_private_read_bool"),
        ("control_family_missing_fail", lambda r: r["control_family_requirement_records"][0]["required_control_family_buckets"].pop(), "control_family_set_mismatch"),
        ("control_family_duplicate_fail", lambda r: r["control_family_requirement_records"][0]["required_control_family_buckets"].append(CONTROL_FAMILIES[0]), "control_family_set_mismatch"),
        ("path_mitigation_drop_fail", lambda r: r["path_confound_mitigation_records"][0].__setitem__("path_token_normalization_or_masking_required_bool", False), "gate_failed_path_confound_mitigation_gate"),
        ("gold_isolation_drop_fail", lambda r: r["gold_isolation_policy_records"][0].__setitem__("gold_eval_only_bool", False), "gate_failed_gold_isolation_policy_gate"),
        ("support_control_gate_drop_fail", lambda r: r["support_control_gate_records"][0].__setitem__("support_retention_not_low_required_bool", False), "gate_failed_support_control_gate_design_gate"),
        ("future_bounds_drift_fail", lambda r: r["future_generation_contract_records"][0].__setitem__("target_tasks_bucket", "bad"), "future_target_tasks_bucket"),
        ("future_control_family_missing_fail", lambda r: r["future_generation_contract_records"][0]["required_control_family_buckets"].pop(), "future_control_family_set_mismatch"),
        ("future_execution_overauth_fail", lambda r: r["future_generation_contract_records"][0].__setitem__("execution_authorization_bool", True), "future_execution_boundary_mismatch"),
        ("stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"),
        ("stop_go_private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"),
        ("stop_go_explicit_generation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("explicit_private_generation_authorized_bool", True), "overauthorization_explicit_private_generation_authorized_bool"),
        ("stop_go_downstream_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("downstream_value_claim_authorized_bool", True), "overauthorization_downstream_value_claim_authorized_bool"),
        ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"),
        ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_set_mismatch"),
        ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"),
        ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_validator_set_mismatch"),
        ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"),
    ]
    for n, mut, issue in report_mut:
        m = json.loads(json.dumps(passed)); mut(m); check(n, issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        res = run_self_test(); print(json.dumps(res, indent=2, sort_keys=True)); return 0 if res["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo / public_artifact_path(str(args["validate"]))); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] == STATUS_PASS else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
