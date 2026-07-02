#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AW robustness material generation public design preflight.

Public-only, non-executing design preflight for future R2AX explicit local
robustness material generation. It reads only public artifacts and never reads
private roots, /tmp, source/candidate/corpus, diagnostics, or runtime systems.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AW Evidence-Pair Support Robustness Material Generation Public Design Preflight"
SLUG = "bea_v1_haae_r2aw_evidence_pair_support_robustness_material_generation_public_design_preflight"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"

R2AV_CHECKPOINT = "c0e4b4f"
R2AV_STATUS = "haae_r2av_evidence_pair_support_next_step_decision_complete_r2aw_robustness_material_generation_public_design_preflight_authorized"
R2AV_SELF_TEST_TOTAL = 50
R2AV_REPORT_PATH = Path("artifacts/bea_v1_haae_r2av_evidence_pair_support_next_step_decision_package/bea_v1_haae_r2av_evidence_pair_support_next_step_decision_package_report.json")
R2AU_CHECKPOINT = "8af2b92"
R2AU_SELF_TEST_TOTAL = 44
R2AU_REPORT_PATH = Path("artifacts/bea_v1_haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package/bea_v1_haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package_report.json")
R2AT_CHECKPOINT = "0c9c108"
R2AT_SELF_TEST_TOTAL = 35
R2AP_CHECKPOINT = "87ea9de"
R2AP_SELF_TEST_TOTAL = 26
R2AP_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ap_evidence_pair_support_explicit_local_material_experiment/bea_v1_haae_r2ap_evidence_pair_support_explicit_local_material_experiment_report.json")
R2AN_CHECKPOINT = "93bba5f"
NEXT_PHASE = "BEA-v1-HAAE-R2AX Evidence-Pair Support Explicit Local Robustness Material Generation"
STATUS_PASS = "haae_r2aw_evidence_pair_support_robustness_material_generation_public_design_preflight_complete_r2ax_explicit_local_robustness_material_generation_authorized"
STATUS_FAIL_SOURCE = "haae_r2aw_fail_closed_source_lock_mismatch"
STATUS_FAIL_DESIGN = "haae_r2aw_fail_closed_design_boundary_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2aw_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2aw_fail_closed_public_readback_mismatch"

EXPECTED_BUCKETS = {"mechanism_interpretation_bucket": "pair_complementarity_supported", "pair_complementarity_lift_bucket": "pair_complementarity_lift_high", "support_vs_contrast_separation_bucket": "support_vs_contrast_separation_medium", "hard_negative_rejection_bucket": "hard_negative_rejection_medium", "path_confound_risk_bucket": "path_confound_risk_low", "gold_isolation_pass_bucket": "gold_isolation_pass"}
VARIANTS = ["single_unit_ablation", "support_contrast_perturbation", "hard_negative_strengthening", "shuffled_pair_control", "query_evidence_masking", "path_token_confound_stress", "cross_task_mismatch_control", "gold_isolation_control"]
GROUPS = ["task_frame", "source_manifest_private", "base_evidence_unit_pool", "base_evidence_pair_material", "robustness_variant_material", "ablation_control_material", "hard_negative_control_material", "shuffled_mismatch_control_material", "outcome_eval_private", "material_qa", "source_material_manifest", "parent_r2an_row_ref_private"]
BOUNDS = {"target_tasks": "20", "evidence_unit_depth_cap_per_task": "40", "support_pair_cap_per_task": "120", "contrast_control_pair_cap_per_task": "80", "private_row_cap": "20000", "source_file_cap": "500_inherited_no_broad_scan", "wall_clock_cap": "20min", "ci_network_provider_runtime_bool": "false"}
R2AV_GATES = ["r2au_source_locked_gate", "r2au_status_authorization_gate", "r2au_self_test_44_gate", "r2at_source_lock_gate", "r2at_bucket_gate", "r2at_self_test_35_gate", "r2ap_support_signal_gate", "r2ap_self_test_26_gate", "public_only_decision_gate", "select_robustness_material_generation_preflight_gate", "reject_scale_external_close_method_default_gate", "no_private_execution_material_scan_metric_gate", "no_method_default_winner_scale_raw_claim_gate", "r2aw_stop_go_only_gate", "r2aw_public_only_design_scope_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2AV_SYNTH = ["decision_pass", "r2au_checkpoint_drift_fail", "r2au_status_drift_fail", "r2au_self_test_pollution_fail", "r2au_forbidden_scan_drift_fail", "r2au_readback_drift_fail", "r2au_gate_duplicate_fail", "r2au_synthetic_drop_fail", "r2au_synthetic_duplicate_fail", "r2at_checkpoint_drift_fail", "r2at_status_drift_fail", "r2at_self_test_pollution_fail", "r2ap_checkpoint_drift_fail", "r2ap_status_drift_fail", "r2ap_self_test_pollution_fail", "r2ap_support_signal_missing_fail", "mechanism_interpretation_drift_fail", "pair_complementarity_lift_drift_fail", "support_vs_contrast_drift_fail", "hard_negative_rejection_drift_fail", "path_confound_drift_fail", "gold_isolation_drift_fail", "scale_selected_fail", "external_validation_execution_selected_fail", "close_turn_selected_fail", "method_default_claim_selected_fail", "robustness_preflight_not_selected_fail", "private_read_overauth_fail", "private_write_overauth_fail", "private_diagnostics_overauth_fail", "material_generation_overauth_fail", "robustness_direct_execution_overauth_fail", "robustness_broad_material_generation_overauth_fail", "experiment_overauth_fail", "metric_recompute_overauth_fail", "source_scan_overauth_fail", "ci_network_runtime_overauth_fail", "scale_preflight_overauth_fail", "external_validation_execution_overauth_fail", "method_claim_overauth_fail", "raw_publication_overauth_fail", "next_phase_drift_fail", "r2aw_scope_drift_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_validator_set_fail", "duplicate_readback_fail", "readback_record_fail", "public_leak_fail", "safe_parser_fail"]
GATES = ["r2av_source_locked_gate", "r2av_self_test_readback_gate", "r2av_gate_synthetic_exact_integrity_gate", "inherited_r2au_r2at_r2ap_r2an_lock_gate", "r2at_mechanism_bucket_gate", "r2ap_support_signal_gate", "public_only_non_executing_gate", "r2ax_design_selected_gate", "variant_axis_set_gate", "bounds_set_gate", "future_private_group_set_gate", "root_safety_design_gate", "material_generation_only_no_metrics_gate", "no_scan_runtime_claim_gate", "r2ax_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["design_pass", "r2av_checkpoint_drift_fail", "r2av_status_drift_fail", "r2av_self_test_pollution_fail", "r2av_readback_duplicate_fail", "r2av_gate_drop_fail", "r2av_gate_duplicate_fail", "r2av_synthetic_drop_fail", "r2av_synthetic_duplicate_fail", "r2au_checkpoint_drift_fail", "r2au_self_test_pollution_fail", "r2at_checkpoint_drift_fail", "r2at_self_test_pollution_fail", "r2ap_checkpoint_drift_fail", "r2ap_self_test_pollution_fail", "r2an_checkpoint_drift_fail", "r2at_bucket_drift_fail", "r2ap_support_signal_drift_fail", "variant_axis_drift_fail", "future_group_drift_fail", "bounds_drift_fail", "root_safety_drift_fail", "private_read_overauth_fail", "private_write_overauth_fail", "implicit_discovery_overauth_fail", "diagnostics_read_overauth_fail", "material_generation_overauth_fail", "robustness_generation_overauth_fail", "robustness_execution_overauth_fail", "experiment_overauth_fail", "metric_recompute_overauth_fail", "mechanism_recompute_overauth_fail", "source_scan_overauth_fail", "source_scan_broad_overauth_fail", "bounded_manifest_source_read_overauth_fail", "candidate_scan_overauth_fail", "corpus_scan_overauth_fail", "ci_network_provider_runtime_overauth_fail", "scale_overauth_fail", "external_validation_overauth_fail", "method_default_overauth_fail", "winner_claim_overauth_fail", "raw_publication_overauth_fail", "stop_true_field_drop_fail", "next_phase_drift_fail", "claim_boundary_drift_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_validator_set_fail", "duplicate_readback_fail", "readback_record_fail", "public_leak_fail", "safe_parser_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
STOP_TRUE = ["haae_r2ax_evidence_pair_support_explicit_local_robustness_material_generation_authorized_bool", "r2ax_explicit_opt_in_required_bool", "r2ax_existing_r2an_private_material_read_authorized_bool", "r2ax_private_output_write_authorized_bool", "r2ax_robustness_material_generation_authorized_bool", "r2ax_material_generation_only_no_experiment_metrics_bool", "r2ax_aggregate_only_public_artifact_required_bool", "r2ax_public_audit_required_after_generation_bool"]
STOP_FALSE = ["default_private_implicit_discovery_authorized_bool", "implicit_private_root_discovery_authorized_bool", "private_read_authorized_bool", "private_write_authorized_bool", "private_diagnostics_read_authorized_bool", "material_generation_authorized_bool", "robustness_material_generation_execution_authorized_bool", "experiment_authorized_bool", "metric_recompute_authorized_bool", "mechanism_recompute_authorized_bool", "source_scan_authorized_bool", "source_scan_broad_authorized_bool", "r2ax_bounded_public_manifest_source_read_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "new_candidate_generation_authorized_bool", "new_base_material_generation_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "scale_preflight_authorized_bool", "external_validation_execution_authorized_bool", "method_default_authorized_bool", "method_winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]


def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"task_ref_value|candidate_key_value|pair_key_value|evidence_key_value|source_file_key_value|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|mrr|hit_rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]
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
    repo = Path(__file__).resolve().parents[1]; path = Path(value); resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def audit_sources(r2av: dict[str, Any], r2au: dict[str, Any], r2ap: dict[str, Any]) -> dict[str, bool]:
    av_src = (r2av.get("source_lock_records") or [{}])[0]; av_dec = (r2av.get("decision_records") or [{}])[0]; av_mech = (r2av.get("mechanism_context_records") or [{}])[0]; av_stop = (r2av.get("stop_go_records") or [{}])[0]
    av_gates = [r.get("gate_bucket") for r in r2av.get("pass_fail_gate_records", [])]; av_synth = [r.get("validator_bucket") for r in r2av.get("synthetic_validator_records", [])]; av_read = r2av.get("public_readback_records", [])
    au_src = (r2au.get("source_lock_records") or [{}])[0]; ap_src = (r2ap.get("source_lock_records") or [{}])[0]; ap_metric = (r2ap.get("aggregate_metric_records") or [{}])[0]
    av_lock = r2av.get("status") == R2AV_STATUS and r2av.get("self_test_total") == R2AV_SELF_TEST_TOTAL and r2av.get("forbidden_scan", {}).get("status") == "pass" and av_src.get("locked_haae_r2au_checkpoint") == R2AU_CHECKPOINT and av_src.get("locked_inherited_r2at_checkpoint") == R2AT_CHECKPOINT and av_src.get("locked_inherited_r2ap_checkpoint") == R2AP_CHECKPOINT and av_src.get("source_locked_bool") is True
    av_integrity = len(av_read) == 1 and av_read[0].get("all_public_readback_match_bool") is True and set(av_gates) == set(R2AV_GATES) and len(av_gates) == len(R2AV_GATES) and len(av_gates) == len(set(av_gates)) and set(av_synth) == set(R2AV_SYNTH) and len(av_synth) == len(R2AV_SYNTH) and len(av_synth) == len(set(av_synth))
    decision_ok = av_dec.get("robustness_material_generation_preflight_selected_bool") is True and av_dec.get("scale_preflight_selected_bool") is False and av_dec.get("external_validation_design_selected_bool") is False and av_dec.get("close_turn_selected_bool") is False and av_dec.get("method_default_claim_selected_bool") is False and av_stop.get("next_allowed_phase") == PHASE and av_stop.get("haae_r2aw_evidence_pair_support_robustness_material_generation_public_design_preflight_authorized_bool") is True and all(av_stop.get(f, False) is False for f in ["private_read_authorized_bool", "private_write_authorized_bool", "private_diagnostics_read_authorized_bool", "material_generation_authorized_bool", "robustness_material_generation_authorized_bool", "robustness_material_generation_execution_authorized_bool", "experiment_authorized_bool", "metric_recompute_authorized_bool", "mechanism_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "scale_preflight_authorized_bool", "external_validation_execution_authorized_bool", "method_default_authorized_bool", "method_winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"])
    buckets_ok = all(av_mech.get(k) == v for k, v in EXPECTED_BUCKETS.items())
    inherited_ok = r2au.get("self_test_total") == R2AU_SELF_TEST_TOTAL and au_src.get("locked_haae_r2at_checkpoint") == R2AT_CHECKPOINT and au_src.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT and au_src.get("r2at_self_test_35_bool") is True and r2ap.get("self_test_total") == R2AP_SELF_TEST_TOTAL and ap_src.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT and ap_metric.get("robustness_result_bucket") == "support_signal" and ap_metric.get("selected_signal_family_bucket") == "evidence_pair_support_complementarity"
    return {"source_ok": av_lock and av_integrity and decision_ok and buckets_ok and inherited_ok, "av_lock": av_lock, "av_integrity": av_integrity, "decision_ok": decision_ok, "buckets_ok": buckets_ok, "inherited_ok": inherited_ok}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AV_CHECKPOINT, R2AV_STATUS, R2AU_CHECKPOINT, R2AT_CHECKPOINT, R2AP_CHECKPOINT, R2AN_CHECKPOINT, "pair_complementarity_supported", "pair_complementarity_lift_high", "support_vs_contrast_separation_medium", "hard_negative_rejection_medium", "path_confound_risk_low", "gold_isolation_pass", "support_signal", "R2AX explicit local robustness material generation", "public-only/non-executing", "single_unit_ablation", "support_contrast_perturbation", "hard_negative_strengthening", "shuffled_pair_control", "query_evidence_masking", "path_token_confound_stress", "cross_task_mismatch_control", "gold_isolation_control", "target_tasks=20", "private_row_cap=20000", "existing R2AN private material", "explicit opt-in", "explicit private output root", "no implicit /tmp discovery"]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    readme = ok(read("README.md")); detail = ok(read("docs/en/bea-v1-haae-r2aw-evidence-pair-support-robustness-material-generation-public-design-preflight.md")) and ok(read("docs/zh/bea-v1-haae-r2aw-evidence-pair-support-robustness-material-generation-public-design-preflight.md"))
    current_root = read("docs/current-research-conclusions.md"); current = ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and ok(current_root) and "bea-v1-haae-r2aw-evidence-pair-support-robustness-material-generation-public-design-preflight.md" in current_root
    log = ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")); summary = ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2av: dict[str, Any] | None = None, r2au: dict[str, Any] | None = None, r2ap: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2av is None:
        try: r2av = load_json(repo / R2AV_REPORT_PATH)
        except Exception: r2av = {}
    if r2au is None:
        try: r2au = load_json(repo / R2AU_REPORT_PATH)
        except Exception: r2au = {}
    if r2ap is None:
        try: r2ap = load_json(repo / R2AP_REPORT_PATH)
        except Exception: r2ap = {}
    audit = audit_sources(r2av, r2au, r2ap); readback = public_readback_match(self_test_total)
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_READBACK if not readback["all_public_readback_match_bool"] else STATUS_PASS)
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2awstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_public_design_preflight_pass"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gates = {"r2av_source_locked_gate": audit["av_lock"], "r2av_self_test_readback_gate": audit["av_integrity"], "r2av_gate_synthetic_exact_integrity_gate": audit["av_integrity"], "inherited_r2au_r2at_r2ap_r2an_lock_gate": audit["inherited_ok"], "r2at_mechanism_bucket_gate": audit["buckets_ok"], "r2ap_support_signal_gate": audit["inherited_ok"], "public_only_non_executing_gate": True, "r2ax_design_selected_gate": True, "variant_axis_set_gate": True, "bounds_set_gate": True, "future_private_group_set_gate": True, "root_safety_design_gate": True, "material_generation_only_no_metrics_gate": True, "no_scan_runtime_claim_gate": True, "r2ax_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2awsource0000", "locked_haae_r2av_checkpoint": R2AV_CHECKPOINT, "locked_haae_r2av_status": R2AV_STATUS, "locked_inherited_r2au_checkpoint": R2AU_CHECKPOINT, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "r2av_self_test_50_bool": audit["av_lock"], "r2av_readback_gate_synthetic_exact_bool": audit["av_integrity"], "r2au_self_test_44_bool": audit["inherited_ok"], "r2at_self_test_35_bool": audit["inherited_ok"], "r2ap_self_test_26_bool": audit["inherited_ok"], "source_locked_bool": audit["source_ok"]}],
        "inherited_support_mechanism_result_records": [{"anonymous_result_id": "haaer2awresult0000", **EXPECTED_BUCKETS, "r2ap_result_bucket": "support_signal", "selected_signal_family_bucket": "evidence_pair_support_complementarity"}],
        "decision_records": [{"anonymous_decision_id": "haaer2awdecision0000", "r2ax_explicit_local_robustness_material_generation_selected_bool": True, "scale_preflight_deferred_bool": True, "direct_experiment_deferred_bool": True, "external_validation_execution_deferred_bool": True, "close_turn_deferred_bool": True, "method_default_claim_deferred_bool": True}],
        "robustness_material_design_records": [{"anonymous_design_id": "haaer2awdesign0000", "variant_axis_buckets": VARIANTS, "bounds": BOUNDS, "future_r2ax_private_group_buckets": GROUPS, "material_generation_only_no_experiment_metrics_bool": True, "derive_from_existing_r2an_material_only_bool": True}],
        "source_root_safety_design_records": [{"anonymous_root_safety_id": "haaer2awroot0000", "explicit_opt_in_required_bool": True, "explicit_existing_r2an_private_input_root_required_bool": True, "explicit_private_output_root_required_bool": True, "roots_outside_repo_required_bool": True, "implicit_tmp_discovery_bool": False, "symlink_path_traversal_allowed_bool": False, "overwrite_without_ownership_manifest_allowed_bool": False, "private_root_path_public_bool": False}],
        "public_only_boundary_records": [{"anonymous_boundary_id": "haaer2awboundary0000", "public_only_non_executing_bool": True, "private_root_read_bool": False, "tmp_read_bool": False, "material_generation_bool": False, "source_candidate_corpus_scan_bool": False, "metric_recompute_bool": False, "ci_network_provider_clone_runtime_openlocus_retrieval_bool": False, "raw_private_exact_publication_bool": False, "method_default_winner_scale_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2awgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gates.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2awsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2awreadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "inherited_support_mechanism_result_records", "decision_records", "robustness_material_design_records", "source_root_safety_design_records", "public_only_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTH): issues.append("self_test_validator_count_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    validators = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(validators) != set(SYNTH) or len(validators) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    for f, e in {"locked_haae_r2av_checkpoint": R2AV_CHECKPOINT, "locked_haae_r2av_status": R2AV_STATUS, "locked_inherited_r2au_checkpoint": R2AU_CHECKPOINT, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    for f in ["r2av_self_test_50_bool", "r2av_readback_gate_synthetic_exact_bool", "r2au_self_test_44_bool", "r2at_self_test_35_bool", "r2ap_self_test_26_bool", "source_locked_bool"]:
        if src.get(f) is not True: issues.append(f"source_{f}")
    result = (report.get("inherited_support_mechanism_result_records") or [{}])[0]
    for f, e in EXPECTED_BUCKETS.items():
        if result.get(f) != e: issues.append(f"result_{f}")
    if result.get("r2ap_result_bucket") != "support_signal" or result.get("selected_signal_family_bucket") != "evidence_pair_support_complementarity": issues.append("result_r2ap_support_signal")
    decision = (report.get("decision_records") or [{}])[0]
    if decision.get("r2ax_explicit_local_robustness_material_generation_selected_bool") is not True: issues.append("decision_r2ax_not_selected")
    for f in ["scale_preflight_deferred_bool", "direct_experiment_deferred_bool", "external_validation_execution_deferred_bool", "close_turn_deferred_bool", "method_default_claim_deferred_bool"]:
        if decision.get(f) is not True: issues.append(f"decision_{f}")
    design = (report.get("robustness_material_design_records") or [{}])[0]
    if design.get("variant_axis_buckets") != VARIANTS: issues.append("variant_axis_set_mismatch")
    if design.get("future_r2ax_private_group_buckets") != GROUPS: issues.append("future_group_set_mismatch")
    if design.get("bounds") != BOUNDS: issues.append("bounds_set_mismatch")
    if design.get("material_generation_only_no_experiment_metrics_bool") is not True or design.get("derive_from_existing_r2an_material_only_bool") is not True: issues.append("design_material_scope_mismatch")
    root = (report.get("source_root_safety_design_records") or [{}])[0]
    for f in ["explicit_opt_in_required_bool", "explicit_existing_r2an_private_input_root_required_bool", "explicit_private_output_root_required_bool", "roots_outside_repo_required_bool"]:
        if root.get(f) is not True: issues.append(f"root_{f}")
    for f in ["implicit_tmp_discovery_bool", "symlink_path_traversal_allowed_bool", "overwrite_without_ownership_manifest_allowed_bool", "private_root_path_public_bool"]:
        if root.get(f) is not False: issues.append(f"root_{f}")
    boundary = (report.get("public_only_boundary_records") or [{}])[0]
    if boundary.get("public_only_non_executing_bool") is not True: issues.append("boundary_public_only_non_executing_bool")
    for f in ["private_root_read_bool", "tmp_read_bool", "material_generation_bool", "source_candidate_corpus_scan_bool", "metric_recompute_bool", "ci_network_provider_clone_runtime_openlocus_retrieval_bool", "raw_private_exact_publication_bool", "method_default_winner_scale_claim_bool"]:
        if boundary.get(f) is not False: issues.append(f"boundary_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2ax_stop_go_mismatch")
    for f in STOP_TRUE:
        if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    for f in STOP_FALSE:
        if stop.get(f) is not False: issues.append(f"overauthorization_{f}")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{g.get('gate_bucket', 'unknown')}")
    return issues


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; repo = Path(__file__).resolve().parents[1]
    base_av = load_json(repo / R2AV_REPORT_PATH); base_au = load_json(repo / R2AU_REPORT_PATH); base_ap = load_json(repo / R2AP_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    passed = build_report(base_av, base_au, base_ap); check("design_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    source_mut = [("r2av_checkpoint_drift_fail", "av", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2au_checkpoint", "wrong")), ("r2av_status_drift_fail", "av", lambda r: r.__setitem__("status", "wrong")), ("r2av_self_test_pollution_fail", "av", lambda r: r.__setitem__("self_test_total", 46)), ("r2av_readback_duplicate_fail", "av", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0]))), ("r2av_gate_drop_fail", "av", lambda r: r["pass_fail_gate_records"].pop()), ("r2av_gate_duplicate_fail", "av", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0]))), ("r2av_synthetic_drop_fail", "av", lambda r: r["synthetic_validator_records"].pop()), ("r2av_synthetic_duplicate_fail", "av", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0]))), ("r2au_checkpoint_drift_fail", "au", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2at_checkpoint", "wrong")), ("r2au_self_test_pollution_fail", "au", lambda r: r.__setitem__("self_test_total", 40)), ("r2at_checkpoint_drift_fail", "au", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2at_checkpoint", "wrong")), ("r2at_self_test_pollution_fail", "au", lambda r: r["source_lock_records"][0].__setitem__("r2at_self_test_35_bool", False)), ("r2ap_checkpoint_drift_fail", "ap", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2an_checkpoint", "wrong")), ("r2ap_self_test_pollution_fail", "ap", lambda r: r.__setitem__("self_test_total", 44)), ("r2an_checkpoint_drift_fail", "au", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2an_checkpoint", "wrong")), ("r2at_bucket_drift_fail", "av", lambda r: r["mechanism_context_records"][0].__setitem__("mechanism_interpretation_bucket", "mixed")), ("r2ap_support_signal_drift_fail", "ap", lambda r: r["aggregate_metric_records"][0].__setitem__("robustness_result_bucket", "mixed"))]
    for name, target, mut in source_mut:
        av = json.loads(json.dumps(base_av)); au = json.loads(json.dumps(base_au)); ap = json.loads(json.dumps(base_ap)); mut({"av": av, "au": au, "ap": ap}[target]); check(name, build_report(av, au, ap)["status"] == STATUS_FAIL_SOURCE)
    mutations = [("variant_axis_drift_fail", lambda r: r["robustness_material_design_records"][0].__setitem__("variant_axis_buckets", []), "variant_axis_set_mismatch"), ("future_group_drift_fail", lambda r: r["robustness_material_design_records"][0].__setitem__("future_r2ax_private_group_buckets", []), "future_group_set_mismatch"), ("bounds_drift_fail", lambda r: r["robustness_material_design_records"][0].__setitem__("bounds", {}), "bounds_set_mismatch"), ("root_safety_drift_fail", lambda r: r["source_root_safety_design_records"][0].__setitem__("implicit_tmp_discovery_bool", True), "root_implicit_tmp_discovery_bool"), ("private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("private_write_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_write_authorized_bool", True), "overauthorization_private_write_authorized_bool"), ("implicit_discovery_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("implicit_private_root_discovery_authorized_bool", True), "overauthorization_implicit_private_root_discovery_authorized_bool"), ("diagnostics_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_diagnostics_read_authorized_bool", True), "overauthorization_private_diagnostics_read_authorized_bool"), ("material_generation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"), ("robustness_generation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("r2ax_robustness_material_generation_authorized_bool", False), "stop_true_r2ax_robustness_material_generation_authorized_bool"), ("robustness_execution_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("robustness_material_generation_execution_authorized_bool", True), "overauthorization_robustness_material_generation_execution_authorized_bool"), ("experiment_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("experiment_authorized_bool", True), "overauthorization_experiment_authorized_bool"), ("metric_recompute_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"), ("mechanism_recompute_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("mechanism_recompute_authorized_bool", True), "overauthorization_mechanism_recompute_authorized_bool"), ("source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "overauthorization_source_scan_authorized_bool"), ("source_scan_broad_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_broad_authorized_bool", True), "overauthorization_source_scan_broad_authorized_bool"), ("bounded_manifest_source_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("r2ax_bounded_public_manifest_source_read_authorized_bool", True), "overauthorization_r2ax_bounded_public_manifest_source_read_authorized_bool"), ("candidate_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("candidate_scan_authorized_bool", True), "overauthorization_candidate_scan_authorized_bool"), ("corpus_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("corpus_scan_authorized_bool", True), "overauthorization_corpus_scan_authorized_bool"), ("ci_network_provider_runtime_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_execution_authorized_bool", True), "overauthorization_ci_execution_authorized_bool"), ("scale_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_preflight_authorized_bool", True), "overauthorization_scale_preflight_authorized_bool"), ("external_validation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("external_validation_execution_authorized_bool", True), "overauthorization_external_validation_execution_authorized_bool"), ("method_default_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("method_default_authorized_bool", True), "overauthorization_method_default_authorized_bool"), ("winner_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("method_winner_claim_authorized_bool", True), "overauthorization_method_winner_claim_authorized_bool"), ("raw_publication_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("raw_publication_authorized_bool", True), "overauthorization_raw_publication_authorized_bool"), ("stop_true_field_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2ax_stop_go_mismatch"), ("claim_boundary_drift_fail", lambda r: r["public_only_boundary_records"][0].__setitem__("method_default_winner_scale_claim_bool", True), "boundary_method_default_winner_scale_claim_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_validator_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "public_readback_record_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    for name, mut, issue in mutations:
        m = json.loads(json.dumps(passed)); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 pair_key_value exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "x"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
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
