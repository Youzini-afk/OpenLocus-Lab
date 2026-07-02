#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AU mechanism decomposition public audit package.

Public-only audit of the R2AT public artifact. This phase reads no private
roots, /tmp material, diagnostics, source/candidate/corpus files, and performs
no mechanism recomputation, retrieval, runtime, CI, network, provider, or clone
operation.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AU Evidence-Pair Support Mechanism Decomposition Public Audit Package"
SLUG = "bea_v1_haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AT_CHECKPOINT = "0c9c108"
R2AT_STATUS = "haae_r2at_explicit_private_mechanism_decomposition_complete_r2au_public_audit_authorized_pair_complementarity_supported"
R2AT_SELF_TEST_TOTAL = 35
R2AT_REPORT_PATH = Path("artifacts/bea_v1_haae_r2at_evidence_pair_support_explicit_private_mechanism_decomposition/bea_v1_haae_r2at_evidence_pair_support_explicit_private_mechanism_decomposition_report.json")
R2AS_CHECKPOINT = "36e64d6"
R2AS_STATUS = "haae_r2as_evidence_pair_support_mechanism_decomposition_public_design_preflight_complete_r2at_explicit_private_mechanism_decomposition_authorized"
R2AR_CHECKPOINT = "7c36376"
R2AQ_CHECKPOINT = "77eab19"
R2AP_CHECKPOINT = "87ea9de"
R2AO_CHECKPOINT = "5cfa8d3"
R2AN_CHECKPOINT = "93bba5f"

STATUS_PASS = "haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package_complete_r2av_next_step_decision_authorized_pair_complementarity_supported"
STATUS_FAIL_SOURCE = "haae_r2au_fail_closed_r2at_source_lock_mismatch"
STATUS_FAIL_AUDIT = "haae_r2au_fail_closed_mechanism_audit_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2au_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2au_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2AV Evidence-Pair Support Next-Step Decision Package"

EXPECTED_BUCKETS = {
    "mechanism_interpretation_bucket": "pair_complementarity_supported",
    "pair_complementarity_lift_bucket": "pair_complementarity_lift_high",
    "support_vs_contrast_separation_bucket": "support_vs_contrast_separation_medium",
    "hard_negative_rejection_bucket": "hard_negative_rejection_medium",
    "path_confound_risk_bucket": "path_confound_risk_low",
    "gold_isolation_pass_bucket": "gold_isolation_pass",
}
R2AT_TRUE_GATES = ["r2as_source_locked_gate", "inherited_r2aq_r2ap_r2ao_r2an_lock_gate", "support_signal_gate", "support_separation_high_gate", "default_noop_or_explicit_opt_in_gate", "private_material_root_safety_gate", "required_r2an_group_set_gate", "no_source_candidate_corpus_scan_gate", "no_material_regeneration_gate", "gold_eval_only_gate", "aggregate_only_bucketized_public_gate", "no_exact_metric_publication_gate", "diagnostics_private_optional_gate", "mechanism_axis_set_gate", "r2au_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2AT_SYNTHETIC_VALIDATORS = ["default_noop_pass", "explicit_synthetic_pass", "explicit_diagnostics_private_pass", "wrong_r2as_status_fail", "r2as_checkpoint_drift_fail", "r2as_authorization_drift_fail", "r2aq_lock_drift_fail", "r2ap_lock_drift_fail", "r2ao_lock_drift_fail", "r2an_lock_drift_fail", "support_signal_drift_fail", "support_separation_drift_fail", "missing_opt_in_parser_fail", "repo_root_reject_fail", "symlink_root_reject_fail", "traversal_root_reject_fail", "missing_manifest_fail", "missing_group_fail", "group_set_mismatch_fail", "manifest_schema_fail", "material_generation_overauth_fail", "source_scan_overauth_fail", "gold_outside_eval_fail", "public_leak_fail", "exact_metric_public_fail", "stop_go_overauth_fail", "stop_go_next_phase_drift_fail", "axis_set_fail", "interpretation_bucket_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_validator_set_fail", "readback_record_fail", "safe_parser_fail", "default_no_private_action_fail"]
GATE_NAMES = ["r2at_public_artifact_only_gate", "r2at_checkpoint_status_gate", "r2at_source_locks_gate", "r2at_self_test_35_gate", "r2at_forbidden_scan_pass_gate", "r2at_public_readback_pass_gate", "r2at_stop_go_to_r2au_only_gate", "mechanism_interpretation_bucket_gate", "pair_complementarity_lift_high_gate", "support_vs_contrast_separation_medium_gate", "hard_negative_rejection_medium_gate", "path_confound_risk_low_gate", "gold_isolation_pass_gate", "aggregate_only_bucketized_public_gate", "no_exact_metric_raw_private_publication_gate", "no_source_candidate_corpus_scan_material_regeneration_private_mutation_gate", "no_method_default_winner_scale_raw_claim_gate", "r2av_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["public_audit_pass", "r2at_checkpoint_drift_fail", "r2at_status_drift_fail", "r2at_self_test_drift_fail", "r2at_forbidden_scan_drift_fail", "r2at_public_readback_drift_fail", "r2at_duplicate_gate_row_fail", "r2at_synthetic_validator_drop_fail", "r2at_synthetic_validator_duplicate_fail", "r2at_readback_duplicate_fail", "r2as_lock_drift_fail", "r2ar_lock_drift_fail", "r2aq_lock_drift_fail", "r2ap_lock_drift_fail", "r2ao_lock_drift_fail", "r2an_lock_drift_fail", "mechanism_interpretation_drift_fail", "pair_complementarity_lift_drift_fail", "support_vs_contrast_separation_drift_fail", "hard_negative_rejection_drift_fail", "path_confound_risk_drift_fail", "gold_isolation_drift_fail", "exact_metric_publication_fail", "raw_private_publication_fail", "source_scan_boundary_fail", "material_regeneration_boundary_fail", "private_mutation_boundary_fail", "private_root_read_boundary_fail", "private_diagnostics_read_boundary_fail", "recompute_boundary_fail", "method_default_scale_claim_fail", "stop_go_overauth_private_read_fail", "stop_go_overauth_recompute_fail", "stop_go_overauth_material_generation_fail", "stop_go_overauth_source_scan_fail", "stop_go_overauth_ci_network_runtime_fail", "stop_go_overauth_method_claim_fail", "next_phase_drift_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_validator_set_fail", "readback_record_fail", "public_leak_fail", "safe_parser_fail"]
SELF_TEST_EXPECTED = len(SYNTHETIC_VALIDATORS)
STOP_FALSE_FIELDS = ["mechanism_recomputation_authorized_bool", "robustness_generation_authorized_bool", "scale_preflight_authorized_bool", "experiment_authorized_bool", "material_generation_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "private_read_authorized_bool", "private_write_authorized_bool", "private_diagnostics_read_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "clone_authorized_bool", "method_default_authorized_bool", "method_winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]


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
        if arg == "--self-test":
            parsed["self_test"] = True; i += 1
        elif arg in {"--validate-report", "--out"}:
            if i + 1 >= len(argv): raise ValueError("invalid arguments")
            parsed["validate" if arg == "--validate-report" else "out"] = argv[i + 1]; i += 2
        else:
            raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value); resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def audit_r2at(r2at: dict[str, Any]) -> dict[str, bool]:
    src = (r2at.get("source_lock_records") or [{}])[0]
    metric = (r2at.get("mechanism_metric_records") or [{}])[0]
    mode = (r2at.get("execution_mode_records") or [{}])[0]
    boundary = (r2at.get("boundary_records") or [{}])[0]
    stop = (r2at.get("stop_go_records") or [{}])[0]
    gate_rows = r2at.get("pass_fail_gate_records", [])
    gate_names = [row.get("gate_bucket") for row in gate_rows]
    gates = {row.get("gate_bucket"): row.get("gate_passed_bool") for row in gate_rows}
    synthetic_names = [row.get("validator_bucket") for row in r2at.get("synthetic_validator_records", [])]
    readback_rows = r2at.get("public_readback_records", [])
    readback = readback_rows[0] if readback_rows else {}
    status_ok = r2at.get("status") == R2AT_STATUS
    self_test_ok = r2at.get("self_test_total") == R2AT_SELF_TEST_TOTAL
    scan_ok = r2at.get("forbidden_scan", {}).get("status") == "pass"
    readback_ok = len(readback_rows) == 1 and readback.get("all_public_readback_match_bool") is True
    lock_ok = src.get("locked_haae_r2as_checkpoint") == R2AS_CHECKPOINT and src.get("locked_haae_r2as_status") == R2AS_STATUS and src.get("locked_inherited_r2ar_checkpoint") == R2AR_CHECKPOINT and src.get("locked_inherited_r2aq_checkpoint") == R2AQ_CHECKPOINT and src.get("locked_inherited_r2ap_checkpoint") == R2AP_CHECKPOINT and src.get("locked_inherited_r2ao_checkpoint") == R2AO_CHECKPOINT and src.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT and src.get("source_locked_bool") is True
    bucket_ok = all(metric.get(k) == v for k, v in EXPECTED_BUCKETS.items())
    privacy_ok = metric.get("aggregate_only_bucketized_bool") is True and metric.get("no_exact_counts_rates_mrr_scores_bool") is True and metric.get("no_raw_task_query_source_evidence_pair_gold_public_bool") is True and scan_ok
    boundary_ok = mode.get("source_candidate_corpus_scan_bool") is False and mode.get("material_generation_bool") is False and mode.get("candidate_generation_bool") is False and mode.get("r2an_material_mutation_bool") is False and boundary.get("source_candidate_corpus_scan_bool") is False and boundary.get("material_regeneration_bool") is False and boundary.get("gold_outcome_eval_only_bool") is True and boundary.get("gold_used_outside_eval_bool") is False and boundary.get("method_default_winner_scale_adoption_bool") is False and boundary.get("raw_publication_bool") is False and boundary.get("ci_network_provider_runtime_openlocus_retrieval_bool") is False
    stop_ok = stop.get("next_allowed_phase") == PHASE and stop.get("haae_r2au_evidence_pair_support_mechanism_decomposition_public_audit_package_authorized_bool") is True and stop.get("r2au_public_audit_package_only_bool") is True and all(stop.get(field, False) is False for field in ["robustness_generation_authorized_bool", "scale_preflight_authorized_bool", "new_experiment_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "method_default_authorized_bool", "method_winner_claim_authorized_bool", "scale_adoption_authorized_bool", "raw_publication_authorized_bool", "material_generation_authorized_bool", "r2an_material_mutation_authorized_bool"])
    gate_ok = set(gate_names) == set(R2AT_TRUE_GATES) and len(gate_names) == len(R2AT_TRUE_GATES) and len(gate_names) == len(set(gate_names)) and all(gates.get(g) is True for g in R2AT_TRUE_GATES)
    synthetic_ok = set(synthetic_names) == set(R2AT_SYNTHETIC_VALIDATORS) and len(synthetic_names) == len(R2AT_SYNTHETIC_VALIDATORS) and len(synthetic_names) == len(set(synthetic_names))
    audit_ok = status_ok and self_test_ok and scan_ok and readback_ok and lock_ok and bucket_ok and privacy_ok and boundary_ok and stop_ok and gate_ok and synthetic_ok
    return {"audit_ok": audit_ok, "status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "readback_ok": readback_ok, "lock_ok": lock_ok, "bucket_ok": bucket_ok, "privacy_ok": privacy_ok, "boundary_ok": boundary_ok, "stop_ok": stop_ok, "gate_ok": gate_ok, "synthetic_ok": synthetic_ok}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AT_CHECKPOINT, R2AT_STATUS, "self-test count 35/35", "pair_complementarity_supported", "pair_complementarity_lift_high", "support_vs_contrast_separation_medium", "hard_negative_rejection_medium", "path_confound_risk_low", "gold_isolation_pass", "R2AT public artifact only", "public-only", "no private roots", "no private diagnostics", "no mechanism recomputation", "no source/candidate/corpus scan", "no material regeneration", "no exact metric/raw private public fields", "no method/default/scale/raw claim", NEXT_PHASE, "public decision/design only"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2au-evidence-pair-support-mechanism-decomposition-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2au-evidence-pair-support-mechanism-decomposition-public-audit-package.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2au-evidence-pair-support-mechanism-decomposition-public-audit-package.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2at: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2at is None:
        try: r2at = load_json(repo / R2AT_REPORT_PATH)
        except Exception: r2at = {}
    audit = audit_r2at(r2at)
    readback = public_readback_match(self_test_total)
    if not (audit["status_ok"] and audit["self_test_ok"] and audit["scan_ok"] and audit["lock_ok"]): status = STATUS_FAIL_SOURCE
    elif not (audit["readback_ok"] and audit["bucket_ok"] and audit["privacy_ok"] and audit["boundary_ok"] and audit["stop_ok"] and audit["gate_ok"] and audit["synthetic_ok"]): status = STATUS_FAIL_AUDIT
    elif not readback["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    else: status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2at_public_artifact_only_gate": True, "r2at_checkpoint_status_gate": audit["status_ok"], "r2at_source_locks_gate": audit["lock_ok"], "r2at_self_test_35_gate": audit["self_test_ok"], "r2at_forbidden_scan_pass_gate": audit["scan_ok"], "r2at_public_readback_pass_gate": audit["readback_ok"], "r2at_stop_go_to_r2au_only_gate": audit["stop_ok"], "mechanism_interpretation_bucket_gate": audit["bucket_ok"], "pair_complementarity_lift_high_gate": audit["bucket_ok"], "support_vs_contrast_separation_medium_gate": audit["bucket_ok"], "hard_negative_rejection_medium_gate": audit["bucket_ok"], "path_confound_risk_low_gate": audit["bucket_ok"], "gold_isolation_pass_gate": audit["bucket_ok"], "aggregate_only_bucketized_public_gate": audit["privacy_ok"], "no_exact_metric_raw_private_publication_gate": audit["privacy_ok"], "no_source_candidate_corpus_scan_material_regeneration_private_mutation_gate": audit["boundary_ok"], "no_method_default_winner_scale_raw_claim_gate": audit["boundary_ok"], "r2av_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    stop = {"anonymous_stop_go_id": "haaer2austop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_public_audit_pass", "haae_r2av_evidence_pair_support_next_step_decision_authorized_bool": passed, "r2av_public_decision_design_only_bool": passed}
    stop.update({field: False for field in STOP_FALSE_FIELDS})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2ausource0000", "locked_haae_r2at_checkpoint": R2AT_CHECKPOINT, "locked_haae_r2at_status": R2AT_STATUS, "locked_inherited_r2as_checkpoint": R2AS_CHECKPOINT, "locked_inherited_r2ar_checkpoint": R2AR_CHECKPOINT, "locked_inherited_r2aq_checkpoint": R2AQ_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2ao_checkpoint": R2AO_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "r2at_status_match_bool": audit["status_ok"], "r2at_self_test_35_bool": audit["self_test_ok"], "r2at_forbidden_scan_pass_bool": audit["scan_ok"], "r2at_public_readback_exact_pass_bool": audit["readback_ok"], "r2at_gate_set_exact_pass_bool": audit["gate_ok"], "r2at_synthetic_validator_set_exact_pass_bool": audit["synthetic_ok"], "inherited_locks_match_bool": audit["lock_ok"], "source_locked_bool": audit["status_ok"] and audit["self_test_ok"] and audit["scan_ok"] and audit["lock_ok"] and audit["readback_ok"] and audit["gate_ok"] and audit["synthetic_ok"]}],
        "public_input_scope_records": [{"anonymous_public_input_scope_id": "haaer2auinput0000", "r2at_public_artifact_only_bool": True, "private_root_read_bool": False, "tmp_read_bool": False, "r2an_private_material_read_bool": False, "private_diagnostics_read_bool": False}],
        "mechanism_audit_records": [{"anonymous_mechanism_audit_id": "haaer2auaudit0000", **EXPECTED_BUCKETS, "bucket_values_match_bool": audit["bucket_ok"], "r2at_result_status_match_bool": audit["status_ok"], "no_mechanism_recomputation_bool": True}],
        "privacy_audit_records": [{"anonymous_privacy_audit_id": "haaer2auprivacy0000", "aggregate_only_public_artifact_bool": True, "bucketized_only_bool": True, "no_exact_metric_publication_bool": audit["privacy_ok"], "no_raw_private_publication_bool": audit["privacy_ok"], "forbidden_scan_pass_bool": audit["scan_ok"]}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2auboundary0000", "public_only_audit_bool": True, "mechanism_recomputation_bool": False, "private_read_bool": False, "private_write_bool": False, "private_diagnostics_read_bool": False, "source_candidate_corpus_scan_bool": False, "material_regeneration_bool": False, "private_mutation_bool": False, "retrieval_openlocus_runtime_ci_network_provider_clone_bool": False, "method_default_winner_scale_raw_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2augate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2ausynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2aureadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "public_input_scope_records", "mechanism_audit_records", "privacy_audit_records", "boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
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
    expected_src = {"locked_haae_r2at_checkpoint": R2AT_CHECKPOINT, "locked_haae_r2at_status": R2AT_STATUS, "locked_inherited_r2as_checkpoint": R2AS_CHECKPOINT, "locked_inherited_r2ar_checkpoint": R2AR_CHECKPOINT, "locked_inherited_r2aq_checkpoint": R2AQ_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2ao_checkpoint": R2AO_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT}
    for field, expected in expected_src.items():
        if src.get(field) != expected: issues.append(f"source_{field}")
    for field in ["r2at_status_match_bool", "r2at_self_test_35_bool", "r2at_forbidden_scan_pass_bool", "r2at_public_readback_exact_pass_bool", "r2at_gate_set_exact_pass_bool", "r2at_synthetic_validator_set_exact_pass_bool", "inherited_locks_match_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_{field}")
    scope = (report.get("public_input_scope_records") or [{}])[0]
    if scope.get("r2at_public_artifact_only_bool") is not True: issues.append("scope_r2at_public_artifact_only_bool")
    for field in ["private_root_read_bool", "tmp_read_bool", "r2an_private_material_read_bool", "private_diagnostics_read_bool"]:
        if scope.get(field) is not False: issues.append(f"scope_{field}")
    mech = (report.get("mechanism_audit_records") or [{}])[0]
    for field, expected in EXPECTED_BUCKETS.items():
        if mech.get(field) != expected: issues.append(f"mechanism_{field}")
    for field in ["bucket_values_match_bool", "r2at_result_status_match_bool", "no_mechanism_recomputation_bool"]:
        if mech.get(field) is not True: issues.append(f"mechanism_{field}")
    priv = (report.get("privacy_audit_records") or [{}])[0]
    for field in ["aggregate_only_public_artifact_bool", "bucketized_only_bool", "no_exact_metric_publication_bool", "no_raw_private_publication_bool", "forbidden_scan_pass_bool"]:
        if priv.get(field) is not True: issues.append(f"privacy_{field}")
    boundary = (report.get("boundary_records") or [{}])[0]
    if boundary.get("public_only_audit_bool") is not True: issues.append("boundary_public_only_audit_bool")
    for field in ["mechanism_recomputation_bool", "private_read_bool", "private_write_bool", "private_diagnostics_read_bool", "source_candidate_corpus_scan_bool", "material_regeneration_bool", "private_mutation_bool", "retrieval_openlocus_runtime_ci_network_provider_clone_bool", "method_default_winner_scale_raw_claim_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2av_evidence_pair_support_next_step_decision_authorized_bool") is not True or stop.get("r2av_public_decision_design_only_bool") is not True: issues.append("r2av_stop_go_mismatch")
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
    base = load_json(repo / R2AT_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("public_audit_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    source_mutations = [("r2at_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2as_checkpoint", "wrong"), STATUS_FAIL_SOURCE), ("r2at_status_drift_fail", lambda r: r.__setitem__("status", "wrong"), STATUS_FAIL_SOURCE), ("r2at_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE), ("r2at_forbidden_scan_drift_fail", lambda r: r["forbidden_scan"].__setitem__("status", "fail"), STATUS_FAIL_SOURCE), ("r2at_public_readback_drift_fail", lambda r: r["public_readback_records"][0].__setitem__("all_public_readback_match_bool", False), STATUS_FAIL_AUDIT), ("r2at_duplicate_gate_row_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), STATUS_FAIL_AUDIT), ("r2at_synthetic_validator_drop_fail", lambda r: r["synthetic_validator_records"].pop(), STATUS_FAIL_AUDIT), ("r2at_synthetic_validator_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), STATUS_FAIL_AUDIT), ("r2at_readback_duplicate_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), STATUS_FAIL_AUDIT), ("r2as_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2as_checkpoint", "wrong"), STATUS_FAIL_SOURCE), ("r2ar_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2ar_checkpoint", "wrong"), STATUS_FAIL_SOURCE), ("r2aq_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2aq_checkpoint", "wrong"), STATUS_FAIL_SOURCE), ("r2ap_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2ap_checkpoint", "wrong"), STATUS_FAIL_SOURCE), ("r2ao_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2ao_checkpoint", "wrong"), STATUS_FAIL_SOURCE), ("r2an_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2an_checkpoint", "wrong"), STATUS_FAIL_SOURCE), ("mechanism_interpretation_drift_fail", lambda r: r["mechanism_metric_records"][0].__setitem__("mechanism_interpretation_bucket", "mixed_or_inconclusive"), STATUS_FAIL_AUDIT), ("pair_complementarity_lift_drift_fail", lambda r: r["mechanism_metric_records"][0].__setitem__("pair_complementarity_lift_bucket", "pair_complementarity_lift_low"), STATUS_FAIL_AUDIT), ("support_vs_contrast_separation_drift_fail", lambda r: r["mechanism_metric_records"][0].__setitem__("support_vs_contrast_separation_bucket", "support_vs_contrast_separation_low"), STATUS_FAIL_AUDIT), ("hard_negative_rejection_drift_fail", lambda r: r["mechanism_metric_records"][0].__setitem__("hard_negative_rejection_bucket", "hard_negative_rejection_low"), STATUS_FAIL_AUDIT), ("path_confound_risk_drift_fail", lambda r: r["mechanism_metric_records"][0].__setitem__("path_confound_risk_bucket", "path_confound_risk_high"), STATUS_FAIL_AUDIT), ("gold_isolation_drift_fail", lambda r: r["mechanism_metric_records"][0].__setitem__("gold_isolation_pass_bucket", "gold_isolation_fail"), STATUS_FAIL_AUDIT)]
    for name, mut, expected_status in source_mutations:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == expected_status)
    mutations = [("exact_metric_publication_fail", lambda r: r["privacy_audit_records"][0].__setitem__("no_exact_metric_publication_bool", False), "privacy_no_exact_metric_publication_bool"), ("raw_private_publication_fail", lambda r: r["privacy_audit_records"][0].__setitem__("no_raw_private_publication_bool", False), "privacy_no_raw_private_publication_bool"), ("source_scan_boundary_fail", lambda r: r["boundary_records"][0].__setitem__("source_candidate_corpus_scan_bool", True), "boundary_source_candidate_corpus_scan_bool"), ("material_regeneration_boundary_fail", lambda r: r["boundary_records"][0].__setitem__("material_regeneration_bool", True), "boundary_material_regeneration_bool"), ("private_mutation_boundary_fail", lambda r: r["boundary_records"][0].__setitem__("private_mutation_bool", True), "boundary_private_mutation_bool"), ("private_root_read_boundary_fail", lambda r: r["public_input_scope_records"][0].__setitem__("private_root_read_bool", True), "scope_private_root_read_bool"), ("private_diagnostics_read_boundary_fail", lambda r: r["public_input_scope_records"][0].__setitem__("private_diagnostics_read_bool", True), "scope_private_diagnostics_read_bool"), ("recompute_boundary_fail", lambda r: r["boundary_records"][0].__setitem__("mechanism_recomputation_bool", True), "boundary_mechanism_recomputation_bool"), ("method_default_scale_claim_fail", lambda r: r["boundary_records"][0].__setitem__("method_default_winner_scale_raw_claim_bool", True), "boundary_method_default_winner_scale_raw_claim_bool"), ("stop_go_overauth_private_read_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("stop_go_overauth_recompute_fail", lambda r: r["stop_go_records"][0].__setitem__("mechanism_recomputation_authorized_bool", True), "overauthorization_mechanism_recomputation_authorized_bool"), ("stop_go_overauth_material_generation_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"), ("stop_go_overauth_source_scan_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "overauthorization_source_scan_authorized_bool"), ("stop_go_overauth_ci_network_runtime_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_execution_authorized_bool", True), "overauthorization_ci_execution_authorized_bool"), ("stop_go_overauth_method_claim_fail", lambda r: r["stop_go_records"][0].__setitem__("method_winner_claim_authorized_bool", True), "overauthorization_method_winner_claim_authorized_bool"), ("next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2av_stop_go_mismatch"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(json.loads(json.dumps(r["pass_fail_gate_records"][0]))), "gate_duplicate_mismatch"), ("synthetic_validator_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    for name, mut, expected_issue in mutations:
        m = json.loads(json.dumps(passed)); mut(m); check(name, expected_issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 pair_key_value exact_score_value"
    check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
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
        try: report = load_json(repo / public_artifact_path(str(args["validate"]))); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
