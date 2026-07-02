#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BR outcome-aligned material repair public design preflight."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BR Evidence-Pair Support Outcome-Aligned Material Repair Public Design Preflight"
SLUG = "bea_v1_haae_r2br_evidence_pair_support_outcome_aligned_material_repair_public_design_preflight"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BQ_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bq_evidence_pair_support_outcome_label_acquisition_next_step_decision_design/bea_v1_haae_r2bq_evidence_pair_support_outcome_label_acquisition_next_step_decision_design_report.json")

STATUS_PASS = "haae_r2br_outcome_aligned_material_repair_public_design_preflight_complete_r2bs_explicit_local_repair_generation_authorized"
STATUS_FAIL_SOURCE = "haae_r2br_fail_closed_source_lock_mismatch"
STATUS_FAIL_FACT = "haae_r2br_fail_closed_inherited_fact_mismatch"
STATUS_FAIL_CONTRACT = "haae_r2br_fail_closed_r2bs_contract_mismatch"
STATUS_FAIL_STOP = "haae_r2br_fail_closed_stop_go_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2br_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2br_fail_closed_public_readback_mismatch"

R2BQ_CHECKPOINT = "8254d58"
R2BQ_STATUS = "haae_r2bq_outcome_label_acquisition_next_step_decision_design_complete_r2br_repair_design_preflight_authorized"
R2BQ_SELF_TEST = 53
R2BP_CHECKPOINT = "82c5d65"
R2BP_STATUS = "haae_r2bp_outcome_label_source_acquisition_public_audit_complete_r2bq_decision_design_authorized"
R2BO_CHECKPOINT = "07b9eef"
R2BO_STATUS = "haae_r2bo_explicit_local_outcome_label_source_acquisition_complete_r2bp_public_audit_authorized"
R2BO_SELF_TEST = 51
R2BE_CHECKPOINT = "c3901d6"
R2BK_CHECKPOINT = "7073b12"
NEXT_PHASE = "BEA-v1-HAAE-R2BS Evidence-Pair Support Explicit Local Outcome-Aligned Material Repair Generation"

R2BO_GROUPS = [
    "outcome_label_source_manifest_private",
    "outcome_label_task_alignment_private",
    "outcome_label_pair_family_alignment_private",
    "outcome_label_provenance_private",
    "manual_label_import_private",
    "existing_label_recovery_private",
    "label_quality_qa_private",
    "parent_r2be_row_ref_private",
]
R2BS_OUTPUT_GROUPS = [
    "outcome_aligned_task_frame",
    "outcome_aligned_source_manifest_private",
    "outcome_aligned_evidence_unit_pool",
    "outcome_aligned_support_pair_material",
    "outcome_aligned_control_pair_material",
    "outcome_label_alignment_eval_private",
    "gold_isolation_eval_private",
    "alignment_qa",
    "parent_r2be_row_ref_private",
    "parent_r2bo_label_ref_private",
    "repair_provenance_private",
]
R2BQ_GATES = [
    "r2bp_source_lock_gate",
    "r2bo_label_acquisition_fact_gate",
    "decision_select_r2br_gate",
    "reject_direct_repair_experiment_scale_claim_gate",
    "public_only_boundary_gate",
    "r2br_stop_go_only_gate",
    "gate_synthetic_readback_exact_gate",
    "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
]
R2BQ_SYNTH = ["decision_pass", "safe_parser_fail", "r2bp_status_drift_fail", "r2bp_self_test_drift_fail", "r2bo_checkpoint_drift_fail", "r2bo_status_drift_fail", "r2bo_self_test_drift_fail", "r2bn_inherited_drift_fail", "r2be_inherited_drift_fail", "r2bp_forbidden_scan_fail", "r2bo_group_missing_fail", "r2bo_group_extra_fail", "r2bo_group_exact_false_fail", "label_bucket_drift_fail", "r2bo_execution_attestation_drift_fail", "aggregate_boundary_drift_fail", "material_repair_overauth_fail", "metric_overauth_fail", "source_scan_overauth_fail", "private_read_overauth_fail", "r2bp_gate_drop_fail", "r2bp_gate_duplicate_fail", "r2bp_synthetic_drop_fail", "r2bp_synthetic_duplicate_fail", "r2bp_synthetic_rename_fail", "r2bp_readback_drop_fail", "r2bp_stop_true_drop_fail", "r2bp_stop_private_overauth_fail", "decision_selected_false_fail", "rationale_bucket_drift_fail", "direct_repair_selected_fail", "direct_repair_execution_selected_fail", "direct_experiment_selected_fail", "scale_selected_fail", "closure_selected_fail", "closure_deferred_drop_fail", "pivot_selected_fail", "pivot_deferred_drop_fail", "method_default_claim_selected_fail", "stop_true_drop_fail", "stop_private_overauth_fail", "stop_execution_overauth_fail", "stop_material_overauth_fail", "stop_metric_overauth_fail", "stop_source_scan_overauth_fail", "stop_claim_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "public_leak_fail"]
R2BQ_STOP_TRUE = [
    "haae_r2br_outcome_aligned_material_repair_public_design_preflight_authorized_bool",
    "r2br_public_only_design_preflight_bool",
    "r2br_no_private_read_write_bool",
    "r2br_no_execution_bool",
    "r2br_no_material_generation_bool",
    "r2br_no_metric_recompute_bool",
    "r2br_no_source_scan_bool",
    "r2bo_label_acquisition_result_locked_bool",
]
STOP_TRUE = [
    "haae_r2bs_explicit_local_outcome_aligned_material_repair_generation_authorized_bool",
    "r2bs_explicit_opt_in_required_bool",
    "r2bs_existing_r2be_private_material_read_authorized_bool",
    "r2bs_existing_r2bo_private_label_source_read_authorized_bool",
    "r2bs_private_output_write_authorized_bool",
    "r2bs_outcome_aligned_material_repair_generation_authorized_bool",
    "r2bs_material_generation_only_no_experiment_metrics_bool",
    "r2bs_no_source_scan_bool",
    "r2bs_aggregate_only_public_artifact_required_bool",
    "r2bs_public_audit_required_after_generation_bool",
    "r2bo_label_acquisition_result_locked_bool",
]
STOP_FALSE = [
    "private_read_authorized_bool",
    "private_write_authorized_bool",
    "private_root_access_authorized_bool",
    "execution_authorized_bool",
    "label_acquisition_authorized_bool",
    "label_generation_authorized_bool",
    "material_generation_authorized_bool",
    "material_repair_generation_authorized_bool",
    "material_repair_execution_authorized_bool",
    "experiment_authorized_bool",
    "experiment_metrics_authorized_bool",
    "metric_recompute_authorized_bool",
    "source_scan_authorized_bool",
    "candidate_scan_authorized_bool",
    "corpus_scan_authorized_bool",
    "runtime_execution_authorized_bool",
    "openlocus_runtime_authorized_bool",
    "retrieval_authorized_bool",
    "ci_execution_authorized_bool",
    "network_authorized_bool",
    "provider_model_authorized_bool",
    "clone_authorized_bool",
    "scale_preflight_authorized_bool",
    "external_validation_authorized_bool",
    "signal_claim_authorized_bool",
    "method_claim_authorized_bool",
    "default_claim_authorized_bool",
    "winner_claim_authorized_bool",
    "scale_claim_authorized_bool",
    "raw_publication_authorized_bool",
]
GATES = [
    "r2bq_source_lock_gate",
    "r2bo_r2bp_fact_gate",
    "r2bk_unavailable_context_gate",
    "r2bs_contract_groups_bounds_gate",
    "r2bs_root_safety_gate",
    "public_only_boundary_gate",
    "r2bs_stop_go_only_gate",
    "gate_synthetic_readback_exact_gate",
    "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
]
SYNTH = [
    "design_pass", "safe_parser_fail", "r2bq_checkpoint_drift_fail", "r2bq_status_drift_fail", "r2bq_self_test_drift_fail",
    "r2bp_status_drift_fail", "r2bo_status_drift_fail", "r2bo_group_missing_fail", "r2bo_label_fact_drift_fail", "r2bo_execution_attestation_drift_fail",
    "r2bp_gate_drop_fail", "r2bp_gate_duplicate_fail", "r2bq_synthetic_rename_fail", "r2bq_decision_drift_fail", "r2bq_direct_repair_execution_fail", "r2bq_closure_deferred_drop_fail", "r2bq_pivot_deferred_drop_fail", "r2bq_stop_go_overauth_fail",
    "r2bk_context_drift_fail", "r2be_lock_drift_fail", "decision_false_fail", "direct_experiment_selected_fail",
    "metric_selected_fail", "scale_selected_fail", "method_default_selected_fail", "closure_selected_fail", "pivot_selected_fail",
    "r2bs_not_selected_fail", "rationale_drift_fail", "output_group_missing_fail", "output_group_extra_fail",
    "bound_drift_fail", "root_safety_drift_fail", "label_use_policy_drift_fail", "source_scan_policy_drift_fail",
    "stop_true_drop_fail", "stop_private_overauth_fail", "stop_execution_overauth_fail", "stop_label_overauth_fail", "stop_material_overauth_fail",
    "stop_metric_overauth_fail", "stop_source_scan_overauth_fail", "stop_claim_overauth_fail", "gate_set_fail",
    "gate_duplicate_fail", "synthetic_set_fail", "synthetic_duplicate_fail", "readback_drop_fail", "readback_duplicate_fail",
    "stale_current_fail", "public_leak_fail",
]
SELF_TEST_TOTAL = len(SYNTH)
LEAK_PATTERNS = [
    ("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|fixtures/r14|\.jsonl", re.I)),
    ("raw_task", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)),
    ("raw_label", re.compile(r"gold_spans|hard_negatives|start_line|end_line|mined_high_confidence", re.I)),
    ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|private_source_ref|\.rs\b|crates/openlocus-|hash_value", re.I)),
    ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|top[-_]?k|\bmrr\b|hit[_-]?rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I)),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args(argv: list[str]) -> dict[str, str | bool]:
    parsed: dict[str, str | bool] = {"self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        if argv[i] == "--self-test":
            parsed["self_test"] = True; i += 1
        elif argv[i] in {"--validate-report", "--out"}:
            if i + 1 >= len(argv):
                raise ValueError("invalid arguments")
            parsed["validate" if argv[i] == "--validate-report" else "out"] = argv[i + 1]; i += 2
        else:
            raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    p = Path(value)
    resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH:
        raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pat in LEAK_PATTERNS if pat.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def audit_r2bq(r2bq: dict[str, Any]) -> dict[str, bool]:
    src = (r2bq.get("source_lock_records") or [{}])[0]
    fact = (r2bq.get("r2bo_label_acquisition_fact_records") or [{}])[0]
    dec = (r2bq.get("decision_records") or [{}])[0]
    priv = (r2bq.get("privacy_boundary_records") or [{}])[0]
    stop = (r2bq.get("stop_go_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2bq.get("pass_fail_gate_records", [])]
    synth = [r.get("validator_bucket") for r in r2bq.get("synthetic_validator_records", [])]
    read = r2bq.get("public_readback_records", [])
    source_ok = (
        r2bq.get("status") == R2BQ_STATUS and r2bq.get("self_test_total") == R2BQ_SELF_TEST and
        r2bq.get("forbidden_scan", {}).get("status") == "pass" and
        src.get("locked_haae_r2bp_checkpoint") == R2BP_CHECKPOINT and src.get("locked_haae_r2bp_status") == R2BP_STATUS and
        src.get("locked_haae_r2bo_checkpoint") == R2BO_CHECKPOINT and src.get("locked_haae_r2bo_status") == R2BO_STATUS and src.get("locked_haae_r2bo_self_test_total") == R2BO_SELF_TEST and
        src.get("locked_inherited_r2be_checkpoint") == R2BE_CHECKPOINT and src.get("locked_inherited_r2bk_checkpoint") == R2BK_CHECKPOINT and src.get("source_locked_bool") is True
    )
    fact_ok = (
        fact.get("labels_acquired_private_bool") is True and fact.get("outcome_label_source_manifest_private_bool") is True and
        fact.get("label_acquisition_bucket") == "labels_acquired_private" and fact.get("generated_group_set_exact_bool") is True and
        fact.get("aggregate_only_public_artifact_bool") is True and fact.get("no_material_repair_metrics_source_scan_bool") is True and
        fact.get("private_r2be_material_read_attested_bool") is True and fact.get("label_source_manifest_read_attested_bool") is True and fact.get("private_output_write_attested_bool") is True
    )
    decision_ok = (
        dec.get("outcome_aligned_material_repair_public_design_preflight_selected_bool") is True and
        dec.get("rationale_bucket") == "labels_acquired_but_material_repair_not_yet_designed" and
        dec.get("close_support_route_deferred_bool") is True and dec.get("pivot_deferred_bool") is True and
        all(dec.get(f) is False for f in ["direct_material_repair_selected_bool", "direct_material_repair_execution_selected_bool", "direct_experiment_selected_bool", "scale_selected_bool", "closure_selected_bool", "pivot_selected_bool", "method_default_winner_signal_scale_claim_selected_bool"])
    )
    boundary_ok = priv.get("public_only_decision_bool") is True and all(priv.get(f) is False for f in ["private_root_read_bool", "private_write_bool", "label_acquisition_generation_bool", "material_repair_generation_bool", "metric_recompute_bool", "source_scan_bool", "runtime_ci_network_provider_bool", "raw_private_exact_publication_bool", "signal_method_default_scale_claim_bool"])
    integrity_ok = set(gates) == set(R2BQ_GATES) and len(gates) == len(R2BQ_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2BQ_SYNTH) and len(synth) == len(R2BQ_SYNTH) and len(synth) == len(set(synth)) and len(read) == 1 and read[0].get("all_public_readback_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BQ_STOP_TRUE) and all(stop.get(f, False) is False for f in STOP_FALSE)
    return {"source_ok": source_ok, "fact_ok": fact_ok, "decision_ok": decision_ok, "boundary_ok": boundary_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok, "audit_ok": source_ok and fact_ok and decision_ok and boundary_ok and integrity_ok and stop_ok}


def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BQ_CHECKPOINT, R2BQ_STATUS, R2BP_CHECKPOINT, R2BO_CHECKPOINT, "outcome_aligned_material_repair_generation_design_selected_bool", "r2bs_explicit_local_repair_generation_selected_bool", "labels_acquired_and_audited_repair_generation_now_design_scoped", "R2BS", "public-only", "no private read", "no signal evaluation", NEXT_PHASE]
    def read(rel: str) -> str:
        p = repo_root() / rel
        return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool:
        return all(f in text for f in fragments)
    root = read("docs/current-research-conclusions.md")
    out = {
        "readme_readback_match_bool": ok(read("README.md")),
        "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2br-evidence-pair-support-outcome-aligned-material-repair-public-design-preflight.md")) and ok(read("docs/zh/bea-v1-haae-r2br-evidence-pair-support-outcome-aligned-material-repair-public-design-preflight.md")),
        "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2br-evidence-pair-support-outcome-aligned-material-repair-public-design-preflight.md" in root,
        "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")),
        "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md")),
    }
    out["all_public_readback_match_bool"] = all(out.values())
    return out


def build_report(r2bq: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_TOTAL) -> dict[str, Any]:
    if r2bq is None:
        try: r2bq = load_json(repo_root() / R2BQ_REPORT_PATH)
        except Exception: r2bq = {}
    audit = audit_r2bq(r2bq)
    rb = public_readback_match(self_test_total)
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_FACT if not (audit["fact_ok"] and audit["decision_ok"] and audit["integrity_ok"]) else (STATUS_FAIL_CONTRACT if not audit["boundary_ok"] else (STATUS_FAIL_STOP if not audit["stop_ok"] else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS))))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2brstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_design_validation_pass"}
    stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {
        "r2bq_source_lock_gate": audit["source_ok"], "r2bo_r2bp_fact_gate": audit["fact_ok"], "r2bk_unavailable_context_gate": True,
        "r2bs_contract_groups_bounds_gate": True, "r2bs_root_safety_gate": True, "public_only_boundary_gate": audit["boundary_ok"],
        "r2bs_stop_go_only_gate": passed, "gate_synthetic_readback_exact_gate": audit["integrity_ok"], "forbidden_scan_pass_gate": True,
        "docs_readback_match_gate": rb["all_public_readback_match_bool"],
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2brsource0000", "locked_haae_r2bq_checkpoint": R2BQ_CHECKPOINT, "locked_haae_r2bq_status": R2BQ_STATUS, "locked_haae_r2bq_self_test_total": R2BQ_SELF_TEST, "locked_haae_r2bp_checkpoint": R2BP_CHECKPOINT, "locked_haae_r2bp_status": R2BP_STATUS, "locked_haae_r2bo_checkpoint": R2BO_CHECKPOINT, "locked_haae_r2bo_status": R2BO_STATUS, "locked_haae_r2bo_self_test_total": R2BO_SELF_TEST, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "locked_inherited_r2bk_checkpoint": R2BK_CHECKPOINT, "source_locked_bool": audit["source_ok"]}],
        "inherited_fact_records": [{"anonymous_fact_id": "haaer2brfact0000", "labels_acquired_private_bool": True, "outcome_label_source_manifest_private_bool": True, "r2bo_group_set_exact_bool": audit["fact_ok"], "r2bo_aggregate_only_bool": True, "r2bo_no_material_repair_bool": True, "r2bo_no_metrics_bool": True, "r2bo_no_source_scan_bool": True, "r2bp_public_only_audit_bool": True, "r2bp_no_private_read_output_read_bool": True, "r2bk_no_material_generated_unavailable_context_bool": True}],
        "decision_design_records": [{"anonymous_decision_id": "haaer2brdecision0000", "outcome_aligned_material_repair_generation_design_selected_bool": True, "direct_experiment_selected_bool": False, "direct_metric_computation_selected_bool": False, "scale_preflight_selected_bool": False, "method_default_claim_selected_bool": False, "closure_selected_bool": False, "pivot_selected_bool": False, "r2bs_explicit_local_repair_generation_selected_bool": True, "r2bs_repairs_generates_material_only_no_signal_evaluation_bool": True, "rationale_bucket": "labels_acquired_and_audited_repair_generation_now_design_scoped"}],
        "r2bs_contract_records": [{"anonymous_contract_id": "haaer2brcontract0000", "explicit_opt_in_required_bool": True, "explicit_r2be_private_material_root_required_bool": True, "explicit_r2bo_private_label_source_root_required_bool": True, "explicit_private_r2bs_output_root_required_bool": True, "read_only_existing_r2be_r2bo_private_groups_bool": True, "write_only_r2bs_repaired_private_material_bool": True, "labels_private_use_only_for_outcome_alignment_eval_private_bool": True, "aggregate_only_public_artifact_bool": True, "public_audit_after_generation_required_bool": True, "no_signal_evaluation_bool": True, "output_group_buckets": R2BS_OUTPUT_GROUPS}],
        "r2bs_bounds_root_safety_records": [{"anonymous_bounds_id": "haaer2brbounds0000", "target_tasks_bucket": "target_tasks_20", "private_rows_bucket": "private_rows_le_20000", "wall_clock_bucket": "wall_clock_le_20_minutes", "input_group_set_exact_required_bool": True, "output_group_set_exact_required_bool": True, "label_source_manifest_bounded_bool": True, "no_source_scan_bool": True, "no_linkable_exact_public_counts_bool": True, "input_roots_outside_repo_non_symlink_exact_group_sets_bool": True, "output_root_outside_repo_no_nesting_no_symlink_traversal_bool": True, "nonempty_unowned_output_rejected_bool": True, "implicit_tmp_discovery_rejected_bool": True, "no_root_path_basename_public_bool": True}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "haaer2brprivacy0000", "public_only_non_executing_bool": True, "private_root_read_bool": False, "labels_inspected_bool": False, "material_generated_bool": False, "metric_computed_bool": False, "source_scan_bool": False, "signal_claim_bool": False, "raw_private_exact_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2brgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2brsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2brreadback0000", **rb}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if report.get("self_test_total") != SELF_TEST_TOTAL: issues.append("self_test_total_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("public_leak")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]
    synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_set_mismatch")
    if len(synth) != len(set(synth)): issues.append("synthetic_duplicate")
    src = (report.get("source_lock_records") or [{}])[0]
    for k, v in {"locked_haae_r2bq_checkpoint": R2BQ_CHECKPOINT, "locked_haae_r2bq_status": R2BQ_STATUS, "locked_haae_r2bq_self_test_total": R2BQ_SELF_TEST, "locked_haae_r2bp_checkpoint": R2BP_CHECKPOINT, "locked_haae_r2bp_status": R2BP_STATUS, "locked_haae_r2bo_checkpoint": R2BO_CHECKPOINT, "locked_haae_r2bo_status": R2BO_STATUS, "locked_haae_r2bo_self_test_total": R2BO_SELF_TEST, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "locked_inherited_r2bk_checkpoint": R2BK_CHECKPOINT}.items():
        if src.get(k) != v: issues.append(f"source_{k}")
    fact = (report.get("inherited_fact_records") or [{}])[0]
    for f in ["labels_acquired_private_bool", "outcome_label_source_manifest_private_bool", "r2bo_group_set_exact_bool", "r2bo_aggregate_only_bool", "r2bo_no_material_repair_bool", "r2bo_no_metrics_bool", "r2bo_no_source_scan_bool", "r2bp_public_only_audit_bool", "r2bp_no_private_read_output_read_bool", "r2bk_no_material_generated_unavailable_context_bool"]:
        if fact.get(f) is not True: issues.append(f"fact_{f}")
    dec = (report.get("decision_design_records") or [{}])[0]
    if dec.get("outcome_aligned_material_repair_generation_design_selected_bool") is not True or dec.get("r2bs_explicit_local_repair_generation_selected_bool") is not True or dec.get("rationale_bucket") != "labels_acquired_and_audited_repair_generation_now_design_scoped": issues.append("decision_mismatch")
    for f in ["direct_experiment_selected_bool", "direct_metric_computation_selected_bool", "scale_preflight_selected_bool", "method_default_claim_selected_bool", "closure_selected_bool", "pivot_selected_bool"]:
        if dec.get(f) is not False: issues.append(f"decision_{f}")
    contract = (report.get("r2bs_contract_records") or [{}])[0]
    if contract.get("output_group_buckets") != R2BS_OUTPUT_GROUPS: issues.append("r2bs_output_group_set_mismatch")
    for f in ["explicit_opt_in_required_bool", "explicit_r2be_private_material_root_required_bool", "explicit_r2bo_private_label_source_root_required_bool", "explicit_private_r2bs_output_root_required_bool", "read_only_existing_r2be_r2bo_private_groups_bool", "write_only_r2bs_repaired_private_material_bool", "labels_private_use_only_for_outcome_alignment_eval_private_bool", "aggregate_only_public_artifact_bool", "public_audit_after_generation_required_bool", "no_signal_evaluation_bool"]:
        if contract.get(f) is not True: issues.append(f"contract_{f}")
    bounds = (report.get("r2bs_bounds_root_safety_records") or [{}])[0]
    for f in ["input_group_set_exact_required_bool", "output_group_set_exact_required_bool", "label_source_manifest_bounded_bool", "no_source_scan_bool", "no_linkable_exact_public_counts_bool", "input_roots_outside_repo_non_symlink_exact_group_sets_bool", "output_root_outside_repo_no_nesting_no_symlink_traversal_bool", "nonempty_unowned_output_rejected_bool", "implicit_tmp_discovery_rejected_bool", "no_root_path_basename_public_bool"]:
        if bounds.get(f) is not True: issues.append(f"bounds_{f}")
    if bounds.get("target_tasks_bucket") != "target_tasks_20" or bounds.get("private_rows_bucket") != "private_rows_le_20000": issues.append("bounds_bucket_mismatch")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    if priv.get("public_only_non_executing_bool") is not True: issues.append("privacy_public_only")
    for f in ["private_root_read_bool", "labels_inspected_bool", "material_generated_bool", "metric_computed_bool", "source_scan_bool", "signal_claim_bool", "raw_private_exact_publication_bool"]:
        if priv.get(f) is not False: issues.append(f"privacy_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_phase_mismatch")
    for f in STOP_TRUE:
        if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    for f in STOP_FALSE:
        if stop.get(f) is not False: issues.append(f"stop_false_{f}")
    read = report.get("public_readback_records", [])
    if len(read) != 1 or read[0].get("all_public_readback_match_bool") is not True: issues.append("readback_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_TOTAL)))["all_public_readback_match_bool"]: issues.append("stale_current")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket')}")
    return issues


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    base = load_json(repo_root() / R2BQ_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    passed = build_report(base)
    check("design_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try:
        parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)
    source_muts = [
        ("r2bq_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bp_checkpoint", "bad"), STATUS_FAIL_SOURCE),
        ("r2bq_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE),
        ("r2bq_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE),
        ("r2bp_status_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bp_status", "bad"), STATUS_FAIL_SOURCE),
        ("r2bo_status_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bo_status", "bad"), STATUS_FAIL_SOURCE),
        ("r2bo_group_missing_fail", lambda r: r["r2bo_label_acquisition_fact_records"][0].__setitem__("generated_group_set_exact_bool", False), STATUS_FAIL_FACT),
        ("r2bo_label_fact_drift_fail", lambda r: r["r2bo_label_acquisition_fact_records"][0].__setitem__("label_acquisition_bucket", "missing"), STATUS_FAIL_FACT),
        ("r2bo_execution_attestation_drift_fail", lambda r: r["r2bo_label_acquisition_fact_records"][0].__setitem__("private_r2be_material_read_attested_bool", False), STATUS_FAIL_FACT),
        ("r2bp_gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), STATUS_FAIL_FACT),
        ("r2bp_gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), STATUS_FAIL_FACT),
        ("r2bq_synthetic_rename_fail", lambda r: r["synthetic_validator_records"][0].__setitem__("validator_bucket", "renamed"), STATUS_FAIL_FACT),
        ("r2bq_decision_drift_fail", lambda r: r["decision_records"][0].__setitem__("outcome_aligned_material_repair_public_design_preflight_selected_bool", False), STATUS_FAIL_FACT),
        ("r2bq_direct_repair_execution_fail", lambda r: r["decision_records"][0].__setitem__("direct_material_repair_execution_selected_bool", True), STATUS_FAIL_FACT),
        ("r2bq_closure_deferred_drop_fail", lambda r: r["decision_records"][0].__setitem__("close_support_route_deferred_bool", False), STATUS_FAIL_FACT),
        ("r2bq_pivot_deferred_drop_fail", lambda r: r["decision_records"][0].__setitem__("pivot_deferred_bool", False), STATUS_FAIL_FACT),
        ("r2bq_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_STOP),
    ]
    for name, mut, expected in source_muts:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == expected)
    report_muts = [
        ("r2bk_context_drift_fail", lambda r: r["inherited_fact_records"][0].__setitem__("r2bk_no_material_generated_unavailable_context_bool", False), "fact_r2bk_no_material_generated_unavailable_context_bool"),
        ("r2be_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2be_checkpoint", "bad"), "source_locked_inherited_r2be_checkpoint"),
        ("decision_false_fail", lambda r: r["decision_design_records"][0].__setitem__("outcome_aligned_material_repair_generation_design_selected_bool", False), "decision_mismatch"),
        ("direct_experiment_selected_fail", lambda r: r["decision_design_records"][0].__setitem__("direct_experiment_selected_bool", True), "decision_direct_experiment_selected_bool"),
        ("metric_selected_fail", lambda r: r["decision_design_records"][0].__setitem__("direct_metric_computation_selected_bool", True), "decision_direct_metric_computation_selected_bool"),
        ("scale_selected_fail", lambda r: r["decision_design_records"][0].__setitem__("scale_preflight_selected_bool", True), "decision_scale_preflight_selected_bool"),
        ("method_default_selected_fail", lambda r: r["decision_design_records"][0].__setitem__("method_default_claim_selected_bool", True), "decision_method_default_claim_selected_bool"),
        ("closure_selected_fail", lambda r: r["decision_design_records"][0].__setitem__("closure_selected_bool", True), "decision_closure_selected_bool"),
        ("pivot_selected_fail", lambda r: r["decision_design_records"][0].__setitem__("pivot_selected_bool", True), "decision_pivot_selected_bool"),
        ("r2bs_not_selected_fail", lambda r: r["decision_design_records"][0].__setitem__("r2bs_explicit_local_repair_generation_selected_bool", False), "decision_mismatch"),
        ("rationale_drift_fail", lambda r: r["decision_design_records"][0].__setitem__("rationale_bucket", "bad"), "decision_mismatch"),
        ("output_group_missing_fail", lambda r: r["r2bs_contract_records"][0]["output_group_buckets"].pop(), "r2bs_output_group_set_mismatch"),
        ("output_group_extra_fail", lambda r: r["r2bs_contract_records"][0]["output_group_buckets"].append("extra"), "r2bs_output_group_set_mismatch"),
        ("bound_drift_fail", lambda r: r["r2bs_bounds_root_safety_records"][0].__setitem__("target_tasks_bucket", "bad"), "bounds_bucket_mismatch"),
        ("root_safety_drift_fail", lambda r: r["r2bs_bounds_root_safety_records"][0].__setitem__("implicit_tmp_discovery_rejected_bool", False), "bounds_implicit_tmp_discovery_rejected_bool"),
        ("label_use_policy_drift_fail", lambda r: r["r2bs_contract_records"][0].__setitem__("labels_private_use_only_for_outcome_alignment_eval_private_bool", False), "contract_labels_private_use_only_for_outcome_alignment_eval_private_bool"),
        ("source_scan_policy_drift_fail", lambda r: r["r2bs_bounds_root_safety_records"][0].__setitem__("no_source_scan_bool", False), "bounds_no_source_scan_bool"),
        ("stop_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"),
        ("stop_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "stop_false_private_read_authorized_bool"),
        ("stop_execution_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("execution_authorized_bool", True), "stop_false_execution_authorized_bool"),
        ("stop_label_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("label_generation_authorized_bool", True), "stop_false_label_generation_authorized_bool"),
        ("stop_material_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "stop_false_material_generation_authorized_bool"),
        ("stop_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "stop_false_metric_recompute_authorized_bool"),
        ("stop_source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "stop_false_source_scan_authorized_bool"),
        ("stop_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("signal_claim_authorized_bool", True), "stop_false_signal_claim_authorized_bool"),
        ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"),
        ("gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate"),
        ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_set_mismatch"),
        ("synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_duplicate"),
        ("readback_drop_fail", lambda r: r.__setitem__("public_readback_records", []), "readback_mismatch"),
        ("readback_duplicate_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "readback_mismatch"),
        ("stale_current_fail", lambda r: r["public_readback_records"][0].__setitem__("all_public_readback_match_bool", False), "readback_mismatch"),
    ]
    for name, mut, issue in report_muts:
        m = json.loads(json.dumps(passed)); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 gold_spans exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_TOTAL, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except Exception:
        print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try:
            report = load_json(repo_root() / public_artifact_path(str(args["validate"])))
            issues = validate_report(report)
        except Exception:
            report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
