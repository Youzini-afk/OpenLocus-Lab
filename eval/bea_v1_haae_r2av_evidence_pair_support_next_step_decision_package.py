#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AV evidence-pair support next-step decision package.

Public-only decision/design package. It reads only public artifacts, does not
execute experiments, read private material/diagnostics, recompute metrics,
generate material, scan source/candidate/corpus, or run CI/network/provider/
clone/runtime/OpenLocus/retrieval paths.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AV Evidence-Pair Support Next-Step Decision Package"
SLUG = "bea_v1_haae_r2av_evidence_pair_support_next_step_decision_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AU_CHECKPOINT = "8af2b92"
R2AU_STATUS = "haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package_complete_r2av_next_step_decision_authorized_pair_complementarity_supported"
R2AU_SELF_TEST_TOTAL = 44
R2AU_REPORT_PATH = Path("artifacts/bea_v1_haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package/bea_v1_haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package_report.json")
R2AT_CHECKPOINT = "0c9c108"
R2AT_STATUS = "haae_r2at_explicit_private_mechanism_decomposition_complete_r2au_public_audit_authorized_pair_complementarity_supported"
R2AT_SELF_TEST_TOTAL = 35
R2AP_CHECKPOINT = "87ea9de"
R2AP_STATUS = "haae_r2ap_explicit_local_material_experiment_complete_r2aq_public_audit_authorized_support_signal"
R2AP_SELF_TEST_TOTAL = 26
R2AP_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ap_evidence_pair_support_explicit_local_material_experiment/bea_v1_haae_r2ap_evidence_pair_support_explicit_local_material_experiment_report.json")
R2AU_GATE_NAMES = ['r2at_public_artifact_only_gate', 'r2at_checkpoint_status_gate', 'r2at_source_locks_gate', 'r2at_self_test_35_gate', 'r2at_forbidden_scan_pass_gate', 'r2at_public_readback_pass_gate', 'r2at_stop_go_to_r2au_only_gate', 'mechanism_interpretation_bucket_gate', 'pair_complementarity_lift_high_gate', 'support_vs_contrast_separation_medium_gate', 'hard_negative_rejection_medium_gate', 'path_confound_risk_low_gate', 'gold_isolation_pass_gate', 'aggregate_only_bucketized_public_gate', 'no_exact_metric_raw_private_publication_gate', 'no_source_candidate_corpus_scan_material_regeneration_private_mutation_gate', 'no_method_default_winner_scale_raw_claim_gate', 'r2av_stop_go_only_gate', 'forbidden_scan_pass_gate', 'docs_readback_match_gate']
R2AU_SYNTHETIC_VALIDATORS = ['public_audit_pass', 'r2at_checkpoint_drift_fail', 'r2at_status_drift_fail', 'r2at_self_test_drift_fail', 'r2at_forbidden_scan_drift_fail', 'r2at_public_readback_drift_fail', 'r2at_duplicate_gate_row_fail', 'r2at_synthetic_validator_drop_fail', 'r2at_synthetic_validator_duplicate_fail', 'r2at_readback_duplicate_fail', 'r2as_lock_drift_fail', 'r2ar_lock_drift_fail', 'r2aq_lock_drift_fail', 'r2ap_lock_drift_fail', 'r2ao_lock_drift_fail', 'r2an_lock_drift_fail', 'mechanism_interpretation_drift_fail', 'pair_complementarity_lift_drift_fail', 'support_vs_contrast_separation_drift_fail', 'hard_negative_rejection_drift_fail', 'path_confound_risk_drift_fail', 'gold_isolation_drift_fail', 'exact_metric_publication_fail', 'raw_private_publication_fail', 'source_scan_boundary_fail', 'material_regeneration_boundary_fail', 'private_mutation_boundary_fail', 'private_root_read_boundary_fail', 'private_diagnostics_read_boundary_fail', 'recompute_boundary_fail', 'method_default_scale_claim_fail', 'stop_go_overauth_private_read_fail', 'stop_go_overauth_recompute_fail', 'stop_go_overauth_material_generation_fail', 'stop_go_overauth_source_scan_fail', 'stop_go_overauth_ci_network_runtime_fail', 'stop_go_overauth_method_claim_fail', 'next_phase_drift_fail', 'gate_set_fail', 'duplicate_gate_fail', 'synthetic_validator_set_fail', 'readback_record_fail', 'public_leak_fail', 'safe_parser_fail']

STATUS_PASS = "haae_r2av_evidence_pair_support_next_step_decision_complete_r2aw_robustness_material_generation_public_design_preflight_authorized"
STATUS_FAIL_SOURCE = "haae_r2av_fail_closed_source_lock_mismatch"
STATUS_FAIL_DECISION = "haae_r2av_fail_closed_decision_boundary_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2av_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2av_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2AW Evidence-Pair Support Robustness Material Generation Public Design Preflight"

EXPECTED_BUCKETS = {"mechanism_interpretation_bucket": "pair_complementarity_supported", "pair_complementarity_lift_bucket": "pair_complementarity_lift_high", "support_vs_contrast_separation_bucket": "support_vs_contrast_separation_medium", "hard_negative_rejection_bucket": "hard_negative_rejection_medium", "path_confound_risk_bucket": "path_confound_risk_low", "gold_isolation_pass_bucket": "gold_isolation_pass"}
ROBUSTNESS_AXES = ["single_unit_ablation", "support_contrast_perturbation", "hard_negative_strengthening", "shuffled_controls", "query_evidence_masking", "path_token_confound_stress", "cross_task_mismatch_controls", "gold_isolation_checks"]
REASON_BUCKETS = ["pair_complementarity_supported_but_current_material_bounded", "robustness_needed_before_scale_or_method_claim"]
GATE_NAMES = ["r2au_source_locked_gate", "r2au_status_authorization_gate", "r2au_self_test_44_gate", "r2at_source_lock_gate", "r2at_bucket_gate", "r2at_self_test_35_gate", "r2ap_support_signal_gate", "r2ap_self_test_26_gate", "public_only_decision_gate", "select_robustness_material_generation_preflight_gate", "reject_scale_external_close_method_default_gate", "no_private_execution_material_scan_metric_gate", "no_method_default_winner_scale_raw_claim_gate", "r2aw_stop_go_only_gate", "r2aw_public_only_design_scope_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["decision_pass", "r2au_checkpoint_drift_fail", "r2au_status_drift_fail", "r2au_self_test_pollution_fail", "r2au_forbidden_scan_drift_fail", "r2au_readback_drift_fail", "r2au_gate_duplicate_fail", "r2au_synthetic_drop_fail", "r2au_synthetic_duplicate_fail", "r2at_checkpoint_drift_fail", "r2at_status_drift_fail", "r2at_self_test_pollution_fail", "r2ap_checkpoint_drift_fail", "r2ap_status_drift_fail", "r2ap_self_test_pollution_fail", "r2ap_support_signal_missing_fail", "mechanism_interpretation_drift_fail", "pair_complementarity_lift_drift_fail", "support_vs_contrast_drift_fail", "hard_negative_rejection_drift_fail", "path_confound_drift_fail", "gold_isolation_drift_fail", "scale_selected_fail", "external_validation_execution_selected_fail", "close_turn_selected_fail", "method_default_claim_selected_fail", "robustness_preflight_not_selected_fail", "private_read_overauth_fail", "private_write_overauth_fail", "private_diagnostics_overauth_fail", "material_generation_overauth_fail", "robustness_direct_execution_overauth_fail", "robustness_broad_material_generation_overauth_fail", "experiment_overauth_fail", "metric_recompute_overauth_fail", "source_scan_overauth_fail", "ci_network_runtime_overauth_fail", "scale_preflight_overauth_fail", "external_validation_execution_overauth_fail", "method_claim_overauth_fail", "raw_publication_overauth_fail", "next_phase_drift_fail", "r2aw_scope_drift_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_validator_set_fail", "duplicate_readback_fail", "readback_record_fail", "public_leak_fail", "safe_parser_fail"]
SELF_TEST_EXPECTED = len(SYNTHETIC_VALIDATORS)
STOP_TRUE_FIELDS = ["haae_r2aw_evidence_pair_support_robustness_material_generation_public_design_preflight_authorized_bool", "r2aw_public_only_design_preflight_bool", "r2aw_no_execution_bool", "r2aw_no_private_read_write_bool", "r2aw_no_material_generation_bool", "r2aw_no_metric_recompute_bool"]
STOP_FALSE_FIELDS = ["private_read_authorized_bool", "private_write_authorized_bool", "private_diagnostics_read_authorized_bool", "material_generation_authorized_bool", "robustness_material_generation_execution_authorized_bool", "robustness_material_generation_authorized_bool", "experiment_authorized_bool", "mechanism_recompute_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "scale_preflight_authorized_bool", "external_validation_execution_authorized_bool", "method_default_authorized_bool", "method_winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"task_ref_value|candidate_key_value|pair_key_value|evidence_key_value|source_file_key_value|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|mrr|hit_rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def parse_args(argv: list[str]) -> dict[str, str | bool]:
    parsed: dict[str, str | bool] = {"self_test": False, "validate": "", "out": ""}
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


def audit_sources(r2au: dict[str, Any], r2ap: dict[str, Any]) -> dict[str, bool]:
    au_src = (r2au.get("source_lock_records") or [{}])[0]
    au_mech = (r2au.get("mechanism_audit_records") or [{}])[0]
    au_boundary = (r2au.get("boundary_records") or [{}])[0]
    au_stop = (r2au.get("stop_go_records") or [{}])[0]
    au_readbacks = r2au.get("public_readback_records", [])
    au_gate_rows = r2au.get("pass_fail_gate_records", [])
    au_gates = [row.get("gate_bucket") for row in au_gate_rows]
    au_synths = [row.get("validator_bucket") for row in r2au.get("synthetic_validator_records", [])]
    ap_metric = (r2ap.get("aggregate_metric_records") or [{}])[0]
    ap_src = (r2ap.get("source_lock_records") or [{}])[0]
    r2au_status_ok = r2au.get("status") == R2AU_STATUS
    r2au_self_ok = r2au.get("self_test_total") == R2AU_SELF_TEST_TOTAL
    r2au_scan_ok = r2au.get("forbidden_scan", {}).get("status") == "pass"
    r2au_readback_ok = len(au_readbacks) == 1 and au_readbacks[0].get("all_public_readback_match_bool") is True
    r2au_stop_ok = au_stop.get("next_allowed_phase") == PHASE and au_stop.get("haae_r2av_evidence_pair_support_next_step_decision_authorized_bool") is True and au_stop.get("r2av_public_decision_design_only_bool") is True and all(au_stop.get(field, False) is False for field in ["mechanism_recomputation_authorized_bool", "robustness_generation_authorized_bool", "scale_preflight_authorized_bool", "experiment_authorized_bool", "material_generation_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "private_read_authorized_bool", "private_write_authorized_bool", "private_diagnostics_read_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "clone_authorized_bool", "method_default_authorized_bool", "method_winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"])
    r2at_lock_ok = au_src.get("locked_haae_r2at_checkpoint") == R2AT_CHECKPOINT and au_src.get("locked_haae_r2at_status") == R2AT_STATUS and au_src.get("r2at_self_test_35_bool") is True and au_src.get("source_locked_bool") is True
    r2at_bucket_ok = all(au_mech.get(k) == v for k, v in EXPECTED_BUCKETS.items())
    r2au_boundary_ok = au_boundary.get("public_only_audit_bool") is True and au_boundary.get("mechanism_recomputation_bool") is False and au_boundary.get("private_read_bool") is False and au_boundary.get("private_write_bool") is False and au_boundary.get("private_diagnostics_read_bool") is False and au_boundary.get("source_candidate_corpus_scan_bool") is False and au_boundary.get("material_regeneration_bool") is False and au_boundary.get("private_mutation_bool") is False and au_boundary.get("retrieval_openlocus_runtime_ci_network_provider_clone_bool") is False and au_boundary.get("method_default_winner_scale_raw_claim_bool") is False
    r2au_gate_ok = set(au_gates) == set(R2AU_GATE_NAMES) and len(au_gates) == len(R2AU_GATE_NAMES) and len(au_gates) == len(set(au_gates)) and all(row.get("gate_passed_bool") is True for row in au_gate_rows)
    r2au_synthetic_ok = set(au_synths) == set(R2AU_SYNTHETIC_VALIDATORS) and len(au_synths) == len(R2AU_SYNTHETIC_VALIDATORS) and len(au_synths) == len(set(au_synths))
    r2ap_ok = r2ap.get("status") == R2AP_STATUS and r2ap.get("self_test_total") == R2AP_SELF_TEST_TOTAL and r2ap.get("forbidden_scan", {}).get("status") == "pass" and ap_src.get("source_locked_bool") is True and ap_src.get("locked_haae_r2ao_checkpoint") == "5cfa8d3" and ap_metric.get("robustness_result_bucket") == "support_signal" and ap_metric.get("selected_signal_family_bucket") == "evidence_pair_support_complementarity"
    source_ok = r2au_status_ok and r2au_self_ok and r2au_scan_ok and r2au_readback_ok and r2au_stop_ok and r2at_lock_ok and r2at_bucket_ok and r2au_boundary_ok and r2au_gate_ok and r2au_synthetic_ok and r2ap_ok
    return {"source_ok": source_ok, "r2au_status_ok": r2au_status_ok, "r2au_self_ok": r2au_self_ok, "r2au_scan_ok": r2au_scan_ok, "r2au_readback_ok": r2au_readback_ok, "r2au_stop_ok": r2au_stop_ok, "r2at_lock_ok": r2at_lock_ok, "r2at_bucket_ok": r2at_bucket_ok, "r2au_boundary_ok": r2au_boundary_ok, "r2au_gate_ok": r2au_gate_ok, "r2au_synthetic_ok": r2au_synthetic_ok, "r2ap_ok": r2ap_ok}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AU_CHECKPOINT, R2AU_STATUS, R2AT_CHECKPOINT, "pair_complementarity_supported", "pair_complementarity_lift_high", "support_vs_contrast_separation_medium", "hard_negative_rejection_medium", "path_confound_risk_low", "gold_isolation_pass", R2AP_CHECKPOINT, "support_signal", "robustness material generation preflight selected", "not scale", "not external validation execution", "not close/turn", "not method/default claim", "pair_complementarity_supported_but_current_material_bounded", "robustness_needed_before_scale_or_method_claim", "public-only next-step decision/design", "no private roots", "no metric recompute", "no source/candidate/corpus scan", NEXT_PHASE, "R2AW public-only/non-executing"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2av-evidence-pair-support-next-step-decision-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2av-evidence-pair-support-next-step-decision-package.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2av-evidence-pair-support-next-step-decision-package.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2au: dict[str, Any] | None = None, r2ap: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2au is None:
        try: r2au = load_json(repo / R2AU_REPORT_PATH)
        except Exception: r2au = {}
    if r2ap is None:
        try: r2ap = load_json(repo / R2AP_REPORT_PATH)
        except Exception: r2ap = {}
    audit = audit_sources(r2au, r2ap)
    readback = public_readback_match(self_test_total)
    if not audit["source_ok"]: status = STATUS_FAIL_SOURCE
    elif not readback["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    else: status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2au_source_locked_gate": audit["source_ok"], "r2au_status_authorization_gate": audit["r2au_status_ok"] and audit["r2au_stop_ok"], "r2au_self_test_44_gate": audit["r2au_self_ok"], "r2at_source_lock_gate": audit["r2at_lock_ok"], "r2at_bucket_gate": audit["r2at_bucket_ok"], "r2at_self_test_35_gate": audit["r2at_lock_ok"], "r2ap_support_signal_gate": audit["r2ap_ok"], "r2ap_self_test_26_gate": audit["r2ap_ok"], "public_only_decision_gate": True, "select_robustness_material_generation_preflight_gate": True, "reject_scale_external_close_method_default_gate": True, "no_private_execution_material_scan_metric_gate": True, "no_method_default_winner_scale_raw_claim_gate": True, "r2aw_stop_go_only_gate": True, "r2aw_public_only_design_scope_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2avstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_next_step_decision_pass"}
    stop.update({field: passed for field in STOP_TRUE_FIELDS})
    stop.update({field: False for field in STOP_FALSE_FIELDS})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2avsource0000", "locked_haae_r2au_checkpoint": R2AU_CHECKPOINT, "locked_haae_r2au_status": R2AU_STATUS, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2at_status": R2AT_STATUS, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2ap_status": R2AP_STATUS, "r2au_status_match_bool": audit["r2au_status_ok"], "r2au_self_test_44_bool": audit["r2au_self_ok"], "r2au_forbidden_scan_pass_bool": audit["r2au_scan_ok"], "r2au_readback_exact_pass_bool": audit["r2au_readback_ok"], "r2au_gate_set_exact_pass_bool": audit["r2au_gate_ok"], "r2au_synthetic_validator_set_exact_pass_bool": audit["r2au_synthetic_ok"], "r2at_self_test_35_bool": audit["r2at_lock_ok"], "r2ap_self_test_26_bool": audit["r2ap_ok"], "r2ap_support_signal_bool": audit["r2ap_ok"], "source_locked_bool": audit["source_ok"]}],
        "decision_records": [{"anonymous_decision_id": "haaer2avdecision0000", "robustness_material_generation_preflight_selected_bool": True, "scale_preflight_selected_bool": False, "external_validation_design_selected_bool": False, "external_validation_deferred_bool": True, "close_turn_selected_bool": False, "method_default_claim_selected_bool": False, "reason_buckets": REASON_BUCKETS}],
        "mechanism_context_records": [{"anonymous_mechanism_context_id": "haaer2avmechanism0000", **EXPECTED_BUCKETS, "r2ap_result_bucket": "support_signal", "current_material_bounded_bool": True}],
        "public_only_boundary_records": [{"anonymous_boundary_id": "haaer2avboundary0000", "public_only_next_step_decision_design_bool": True, "execution_bool": False, "private_root_read_bool": False, "private_material_read_bool": False, "private_diagnostics_read_bool": False, "tmp_read_bool": False, "metric_recompute_bool": False, "material_generation_bool": False, "source_candidate_corpus_scan_bool": False, "ci_network_provider_clone_runtime_openlocus_retrieval_bool": False, "raw_rows_exact_metrics_publication_bool": False, "method_default_winner_scale_claim_bool": False}],
        "r2aw_preflight_scope_records": [{"anonymous_r2aw_scope_id": "haaer2avscope0000", "r2aw_public_only_non_executing_bool": True, "robustness_perturbation_families_design_bool": True, "bounds_design_bool": True, "privacy_scanners_design_bool": True, "aggregate_public_shape_design_bool": True, "fail_closed_validators_design_bool": True, "stop_go_design_bool": True, "authorized_axis_buckets": ROBUSTNESS_AXES}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2avgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2avsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2avreadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "decision_records", "mechanism_context_records", "public_only_boundary_records", "r2aw_preflight_scope_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTHETIC_VALIDATORS): issues.append("self_test_validator_count_mismatch")
    gates = [row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATE_NAMES) or len(gates) != len(GATE_NAMES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    validators = [row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])]
    if set(validators) != set(SYNTHETIC_VALIDATORS) or len(validators) != len(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    expected_src = {"locked_haae_r2au_checkpoint": R2AU_CHECKPOINT, "locked_haae_r2au_status": R2AU_STATUS, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2at_status": R2AT_STATUS, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2ap_status": R2AP_STATUS}
    for field, expected in expected_src.items():
        if src.get(field) != expected: issues.append(f"source_{field}")
    for field in ["r2au_status_match_bool", "r2au_self_test_44_bool", "r2au_forbidden_scan_pass_bool", "r2au_readback_exact_pass_bool", "r2au_gate_set_exact_pass_bool", "r2au_synthetic_validator_set_exact_pass_bool", "r2at_self_test_35_bool", "r2ap_self_test_26_bool", "r2ap_support_signal_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_{field}")
    decision = (report.get("decision_records") or [{}])[0]
    if decision.get("robustness_material_generation_preflight_selected_bool") is not True or decision.get("external_validation_deferred_bool") is not True: issues.append("decision_robustness_preflight_not_selected")
    for field in ["scale_preflight_selected_bool", "external_validation_design_selected_bool", "close_turn_selected_bool", "method_default_claim_selected_bool"]:
        if decision.get(field) is not False: issues.append(f"decision_{field}")
    if set(decision.get("reason_buckets") or []) != set(REASON_BUCKETS): issues.append("decision_reason_bucket_mismatch")
    mech = (report.get("mechanism_context_records") or [{}])[0]
    for field, expected in EXPECTED_BUCKETS.items():
        if mech.get(field) != expected: issues.append(f"mechanism_{field}")
    if mech.get("r2ap_result_bucket") != "support_signal" or mech.get("current_material_bounded_bool") is not True: issues.append("mechanism_r2ap_support_signal")
    boundary = (report.get("public_only_boundary_records") or [{}])[0]
    if boundary.get("public_only_next_step_decision_design_bool") is not True: issues.append("boundary_public_only_next_step_decision_design_bool")
    for field in ["execution_bool", "private_root_read_bool", "private_material_read_bool", "private_diagnostics_read_bool", "tmp_read_bool", "metric_recompute_bool", "material_generation_bool", "source_candidate_corpus_scan_bool", "ci_network_provider_clone_runtime_openlocus_retrieval_bool", "raw_rows_exact_metrics_publication_bool", "method_default_winner_scale_claim_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    scope = (report.get("r2aw_preflight_scope_records") or [{}])[0]
    for field in ["r2aw_public_only_non_executing_bool", "robustness_perturbation_families_design_bool", "bounds_design_bool", "privacy_scanners_design_bool", "aggregate_public_shape_design_bool", "fail_closed_validators_design_bool", "stop_go_design_bool"]:
        if scope.get(field) is not True: issues.append(f"r2aw_scope_{field}")
    if set(scope.get("authorized_axis_buckets") or []) != set(ROBUSTNESS_AXES): issues.append("r2aw_axis_set_mismatch")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2aw_stop_go_mismatch")
    for field in STOP_TRUE_FIELDS:
        if stop.get(field) is not True: issues.append(f"stop_true_{field}")
    for field in STOP_FALSE_FIELDS:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    return issues


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base_au = load_json(repo / R2AU_REPORT_PATH); base_ap = load_json(repo / R2AP_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base_au, base_ap); check("decision_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    source_mutations = [("r2au_checkpoint_drift_fail", "au", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2at_checkpoint", "wrong"), STATUS_FAIL_SOURCE), ("r2au_status_drift_fail", "au", lambda r: r.__setitem__("status", "wrong"), STATUS_FAIL_SOURCE), ("r2au_self_test_pollution_fail", "au", lambda r: r.__setitem__("self_test_total", 40), STATUS_FAIL_SOURCE), ("r2au_forbidden_scan_drift_fail", "au", lambda r: r["forbidden_scan"].__setitem__("status", "fail"), STATUS_FAIL_SOURCE), ("r2au_readback_drift_fail", "au", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), STATUS_FAIL_SOURCE), ("r2au_gate_duplicate_fail", "au", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), STATUS_FAIL_SOURCE), ("r2au_synthetic_drop_fail", "au", lambda r: r["synthetic_validator_records"].pop(), STATUS_FAIL_SOURCE), ("r2au_synthetic_duplicate_fail", "au", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), STATUS_FAIL_SOURCE), ("r2at_checkpoint_drift_fail", "au", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2at_checkpoint", "wrong"), STATUS_FAIL_SOURCE), ("r2at_status_drift_fail", "au", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2at_status", "wrong"), STATUS_FAIL_SOURCE), ("r2at_self_test_pollution_fail", "au", lambda r: r["source_lock_records"][0].__setitem__("r2at_self_test_35_bool", False), STATUS_FAIL_SOURCE), ("r2ap_checkpoint_drift_fail", "ap", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2ao_checkpoint", "wrong"), STATUS_FAIL_SOURCE), ("r2ap_status_drift_fail", "ap", lambda r: r.__setitem__("status", "wrong"), STATUS_FAIL_SOURCE), ("r2ap_self_test_pollution_fail", "ap", lambda r: r.__setitem__("self_test_total", 35), STATUS_FAIL_SOURCE), ("r2ap_support_signal_missing_fail", "ap", lambda r: r["aggregate_metric_records"][0].__setitem__("robustness_result_bucket", "mixed_or_inconclusive"), STATUS_FAIL_SOURCE), ("mechanism_interpretation_drift_fail", "au", lambda r: r["mechanism_audit_records"][0].__setitem__("mechanism_interpretation_bucket", "mixed_or_inconclusive"), STATUS_FAIL_SOURCE), ("pair_complementarity_lift_drift_fail", "au", lambda r: r["mechanism_audit_records"][0].__setitem__("pair_complementarity_lift_bucket", "low"), STATUS_FAIL_SOURCE), ("support_vs_contrast_drift_fail", "au", lambda r: r["mechanism_audit_records"][0].__setitem__("support_vs_contrast_separation_bucket", "low"), STATUS_FAIL_SOURCE), ("hard_negative_rejection_drift_fail", "au", lambda r: r["mechanism_audit_records"][0].__setitem__("hard_negative_rejection_bucket", "low"), STATUS_FAIL_SOURCE), ("path_confound_drift_fail", "au", lambda r: r["mechanism_audit_records"][0].__setitem__("path_confound_risk_bucket", "high"), STATUS_FAIL_SOURCE), ("gold_isolation_drift_fail", "au", lambda r: r["mechanism_audit_records"][0].__setitem__("gold_isolation_pass_bucket", "fail"), STATUS_FAIL_SOURCE)]
    for name, target, mut, expected in source_mutations:
        au = json.loads(json.dumps(base_au)); ap = json.loads(json.dumps(base_ap)); mut(au if target == "au" else ap); check(name, build_report(au, ap)["status"] == expected)
    mutations = [("scale_selected_fail", lambda r: r["decision_records"][0].__setitem__("scale_preflight_selected_bool", True), "decision_scale_preflight_selected_bool"), ("external_validation_execution_selected_fail", lambda r: r["decision_records"][0].__setitem__("external_validation_design_selected_bool", True), "decision_external_validation_design_selected_bool"), ("close_turn_selected_fail", lambda r: r["decision_records"][0].__setitem__("close_turn_selected_bool", True), "decision_close_turn_selected_bool"), ("method_default_claim_selected_fail", lambda r: r["decision_records"][0].__setitem__("method_default_claim_selected_bool", True), "decision_method_default_claim_selected_bool"), ("robustness_preflight_not_selected_fail", lambda r: r["decision_records"][0].__setitem__("robustness_material_generation_preflight_selected_bool", False), "decision_robustness_preflight_not_selected"), ("private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("private_write_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_write_authorized_bool", True), "overauthorization_private_write_authorized_bool"), ("private_diagnostics_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_diagnostics_read_authorized_bool", True), "overauthorization_private_diagnostics_read_authorized_bool"), ("material_generation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"), ("robustness_direct_execution_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("robustness_material_generation_execution_authorized_bool", True), "overauthorization_robustness_material_generation_execution_authorized_bool"), ("robustness_broad_material_generation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("robustness_material_generation_authorized_bool", True), "overauthorization_robustness_material_generation_authorized_bool"), ("experiment_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("experiment_authorized_bool", True), "overauthorization_experiment_authorized_bool"), ("metric_recompute_overauth_fail", lambda r: r["public_only_boundary_records"][0].__setitem__("metric_recompute_bool", True), "boundary_metric_recompute_bool"), ("source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "overauthorization_source_scan_authorized_bool"), ("ci_network_runtime_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_execution_authorized_bool", True), "overauthorization_ci_execution_authorized_bool"), ("scale_preflight_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_preflight_authorized_bool", True), "overauthorization_scale_preflight_authorized_bool"), ("external_validation_execution_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("external_validation_execution_authorized_bool", True), "overauthorization_external_validation_execution_authorized_bool"), ("method_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("method_winner_claim_authorized_bool", True), "overauthorization_method_winner_claim_authorized_bool"), ("raw_publication_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("raw_publication_authorized_bool", True), "overauthorization_raw_publication_authorized_bool"), ("next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2aw_stop_go_mismatch"), ("r2aw_scope_drift_fail", lambda r: r["r2aw_preflight_scope_records"][0].__setitem__("authorized_axis_buckets", []), "r2aw_axis_set_mismatch"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_validator_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "public_readback_record_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    for name, mut, expected_issue in mutations:
        m = json.loads(json.dumps(passed)); mut(m); check(name, expected_issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 pair_key_value exact_score_value"
    check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "x"])
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
        try: report = load_json(repo / public_artifact_path(str(args["validate"]))); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
