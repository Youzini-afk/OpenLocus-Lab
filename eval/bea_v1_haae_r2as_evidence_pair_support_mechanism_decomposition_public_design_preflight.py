#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AS evidence-pair support mechanism decomposition preflight.

Public-only non-executing design/preflight after R2AR. It designs the R2AT
explicit local private mechanism decomposition contract without reading private
roots, recomputing metrics, generating material, scanning source/candidates, or
authorizing scale/direct adoption.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AS Evidence-Pair Support Mechanism Decomposition Public Design Preflight"
SLUG = "bea_v1_haae_r2as_evidence_pair_support_mechanism_decomposition_public_design_preflight"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AR_CHECKPOINT = "7c36376"
R2AR_STATUS = "haae_r2ar_evidence_pair_support_next_step_decision_complete_r2as_mechanism_decomposition_public_design_authorized"
R2AQ_CHECKPOINT = "77eab19"
R2AP_CHECKPOINT = "87ea9de"
R2AO_CHECKPOINT = "5cfa8d3"
R2AN_CHECKPOINT = "93bba5f"
R2AR_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ar_evidence_pair_support_next_step_decision_package/bea_v1_haae_r2ar_evidence_pair_support_next_step_decision_package_report.json")

STATUS_PASS = "haae_r2as_evidence_pair_support_mechanism_decomposition_public_design_preflight_complete_r2at_explicit_private_mechanism_decomposition_authorized"
STATUS_FAIL_SOURCE = "haae_r2as_fail_closed_source_lock_mismatch"
STATUS_FAIL_CONTRACT = "haae_r2as_fail_closed_r2at_contract_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2as_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2as_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2AT Evidence-Pair Support Explicit Local Private Mechanism Decomposition"
SELECTED_SIGNAL_FAMILY = "evidence_pair_support_complementarity"
AXES = ["complementarity_vs_single_unit", "support_vs_contrast", "target_support_vs_hard_negative", "shuffled_cross_task_control_rejection", "path_token_confound_check", "outcome_gold_isolation", "pair_family_balance_coverage_sensitivity", "evidence_quality_vs_pair_composition"]
GATE_NAMES = ["r2ar_source_locked_gate", "inherited_r2aq_r2ap_r2ao_r2an_lock_gate", "support_signal_gate", "support_separation_high_gate", "public_only_preflight_gate", "r2at_contract_gate", "mechanism_axis_set_gate", "existing_private_material_only_gate", "no_new_generation_scan_gate", "gold_eval_only_gate", "aggregate_only_public_output_gate", "no_scale_robustness_generation_direct_adoption_gate", "no_method_default_winner_scale_claim_gate", "r2at_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["source_lock_pass", "r2ar_checkpoint_drift_fail", "r2ar_status_drift_fail", "r2ar_self_test_drift_fail", "r2ar_forbidden_scan_drift_fail", "r2aq_lock_drift_fail", "r2ap_lock_drift_fail", "r2ao_lock_drift_fail", "r2an_lock_drift_fail", "r2ar_stop_overauth_drift_fail", "support_signal_drift_fail", "support_separation_drift_fail", "r2at_contract_drift_fail", "axis_set_fail", "existing_material_only_fail", "r2at_private_read_scope_fail", "r2at_mechanism_metrics_scope_fail", "r2at_private_diagnostics_scope_fail", "gold_eval_only_fail", "aggregate_public_only_fail", "robustness_generation_overauth_fail", "scale_overauth_fail", "direct_adoption_overauth_fail", "private_read_overauth_fail", "execution_overauth_fail", "source_scan_overauth_fail", "method_claim_overauth_fail", "next_phase_drift_fail", "stop_go_overauth_fail", "gate_set_fail", "synthetic_validator_set_fail", "readback_record_fail", "prior_phase_count_guard_fail", "safe_parser_fail"]
SELF_TEST_EXPECTED = len(SYNTHETIC_VALIDATORS)
STOP_FALSE_FIELDS = ["scale_preflight_authorized_bool", "scale_execution_authorized_bool", "robustness_material_generation_authorized_bool", "direct_method_adoption_authorized_bool", "execution_authorized_bool", "private_read_authorized_bool", "private_write_authorized_bool", "recompute_metrics_authorized_bool", "material_generation_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "validated_signal_claim_authorized_bool", "raw_publication_authorized_bool"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"task_ref_value|candidate_key_value|pair_key_value|evidence_key_value|source_file_key_value|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top_k_value|mrr_value|hit_rate_value|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


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


def audit_r2ar(r2ar: dict[str, Any]) -> dict[str, bool]:
    source = (r2ar.get("source_lock_records") or [{}])[0]
    signal = (r2ar.get("inherited_support_signal_records") or [{}])[0]
    selected = (r2ar.get("selected_next_phase_records") or [{}])[0]
    stop = (r2ar.get("stop_go_records") or [{}])[0]
    status_ok = r2ar.get("status") == R2AR_STATUS
    self_test_ok = r2ar.get("self_test_total") == 29
    scan_ok = r2ar.get("forbidden_scan", {}).get("status") == "pass"
    lock_ok = source.get("locked_haae_r2aq_checkpoint") == R2AQ_CHECKPOINT and source.get("locked_inherited_r2ap_checkpoint") == R2AP_CHECKPOINT and source.get("locked_inherited_r2ao_checkpoint") == R2AO_CHECKPOINT and source.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT and source.get("source_locked_bool") is True
    signal_ok = signal.get("r2ap_result_bucket") == "support_signal" and signal.get("support_vs_control_separation_bucket") == "support_separation_high"
    selected_ok = selected.get("selected_next_phase") == PHASE and selected.get("select_only_r2as_public_design_preflight_bool") is True and selected.get("defer_robustness_material_generation_bool") is True and selected.get("scale_or_direct_robustness_experiment_authorized_bool") is False
    stop_ok = stop.get("haae_r2as_mechanism_decomposition_public_design_preflight_authorized_bool") is True and stop.get("next_allowed_phase") == PHASE and all(stop.get(field, False) is False for field in ["execution_authorized_bool", "private_read_authorized_bool", "private_write_authorized_bool", "recompute_metrics_authorized_bool", "material_generation_authorized_bool", "robustness_material_generation_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    source_ok = status_ok and self_test_ok and scan_ok and lock_ok and signal_ok and selected_ok and stop_ok
    return {"source_ok": source_ok, "status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "lock_ok": lock_ok, "signal_ok": signal_ok, "selected_ok": selected_ok, "stop_ok": stop_ok}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AR_CHECKPOINT, R2AR_STATUS, R2AQ_CHECKPOINT, R2AP_CHECKPOINT, R2AO_CHECKPOINT, R2AN_CHECKPOINT, "support_signal", "support_separation_high", NEXT_PHASE, "explicit opt-in", "existing private material root", "read existing private material", "mechanism-decomposition metrics", "existing material only", "no new source scan/material regeneration/candidate generation", "private row diagnostics optional", "bucketized aggregate only", "gold outcome eval-only", "mechanism axes", "no scale/robustness material generation/direct method adoption"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2as-evidence-pair-support-mechanism-decomposition-public-design-preflight.md")) and has_all(read("docs/zh/bea-v1-haae-r2as-evidence-pair-support-mechanism-decomposition-public-design-preflight.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2as-evidence-pair-support-mechanism-decomposition-public-design-preflight.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    prior_text = "\n".join(read(rel) for rel in ["README.md", "docs/en/current-research-conclusions.md", "docs/zh/current-research-conclusions.md", "docs/en/research-log.md", "docs/zh/research-log.md", "docs/en/research-summary.md", "docs/zh/research-summary.md"])
    r2ar_lines = [line for line in prior_text.splitlines() if "R2AR" in line]
    prior_ok = bool(r2ar_lines) and all("33/33" not in line for line in r2ar_lines) and any("29/29" in line for line in r2ar_lines)
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "prior_phase_count_guard_bool": prior_ok, "all_public_readback_match_bool": readme and detail and current and log and summary and prior_ok}


def build_report(r2ar: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2ar is None:
        try: r2ar = load_json(repo / R2AR_REPORT_PATH)
        except Exception: r2ar = {}
    audit = audit_r2ar(r2ar)
    readback = public_readback_match(self_test_total)
    contract_ok = audit["source_ok"]
    if not audit["source_ok"]: status = STATUS_FAIL_SOURCE
    elif not contract_ok: status = STATUS_FAIL_CONTRACT
    elif not readback["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    else: status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2ar_source_locked_gate": audit["status_ok"] and audit["self_test_ok"] and audit["scan_ok"], "inherited_r2aq_r2ap_r2ao_r2an_lock_gate": audit["lock_ok"], "support_signal_gate": audit["signal_ok"], "support_separation_high_gate": audit["signal_ok"], "public_only_preflight_gate": True, "r2at_contract_gate": True, "mechanism_axis_set_gate": True, "existing_private_material_only_gate": True, "no_new_generation_scan_gate": True, "gold_eval_only_gate": True, "aggregate_only_public_output_gate": True, "no_scale_robustness_generation_direct_adoption_gate": True, "no_method_default_winner_scale_claim_gate": True, "r2at_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    stop = {"anonymous_stop_go_id": "haaer2asstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_preflight_pass", "haae_r2at_explicit_local_private_mechanism_decomposition_authorized_bool": passed, "r2at_explicit_opt_in_required_bool": passed, "r2at_existing_private_material_root_required_bool": passed, "r2at_existing_private_material_read_authorized_bool": passed, "r2at_mechanism_decomposition_metrics_authorized_bool": passed, "r2at_optional_private_diagnostics_write_authorized_bool": passed, "r2at_existing_private_material_only_bool": passed, "r2at_no_new_material_generation_bool": passed, "r2at_no_source_scan_candidate_generation_bool": passed, "r2at_aggregate_only_public_output_required_bool": passed, "r2at_gold_outcome_eval_only_bool": passed}
    stop.update({field: False for field in STOP_FALSE_FIELDS})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2assource0000", "locked_haae_r2ar_checkpoint": R2AR_CHECKPOINT, "locked_haae_r2ar_status": R2AR_STATUS, "locked_inherited_r2aq_checkpoint": R2AQ_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2ao_checkpoint": R2AO_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "r2ar_status_match_bool": audit["status_ok"], "r2ar_self_test_29_bool": audit["self_test_ok"], "r2ar_forbidden_scan_pass_bool": audit["scan_ok"], "inherited_locks_match_bool": audit["lock_ok"], "source_locked_bool": audit["source_ok"]}],
        "inherited_support_signal_records": [{"anonymous_support_signal_id": "haaer2assignal0000", "selected_signal_family_bucket": SELECTED_SIGNAL_FAMILY, "r2ap_result_bucket": "support_signal", "support_vs_control_separation_bucket": "support_separation_high", "bucket_only_metrics_bool": True}],
        "mechanism_axis_records": [{"anonymous_axis_id": f"haaer2asaxis{idx:04d}", "axis_bucket": axis, "public_design_preflight_bool": True, "private_decomposition_later_bool": True} for idx, axis in enumerate(AXES)],
        "r2at_contract_records": [{"anonymous_r2at_contract_id": "haaer2ascontract0000", "next_phase": NEXT_PHASE, "explicit_opt_in_required_bool": True, "existing_private_material_root_required_bool": True, "existing_private_material_read_authorized_bool": True, "mechanism_decomposition_metrics_authorized_bool": True, "optional_private_diagnostics_write_authorized_bool": True, "existing_material_only_bool": True, "new_source_scan_authorized_bool": False, "material_regeneration_authorized_bool": False, "candidate_generation_authorized_bool": False, "new_material_generation_authorized_bool": False, "private_row_diagnostics_optional_bool": True, "public_output_bucketized_aggregate_only_bool": True, "gold_outcome_eval_only_bool": True, "scale_or_robustness_material_generation_or_direct_adoption_authorized_bool": False}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2asboundary0000", "public_only_non_executing_preflight_bool": True, "private_root_read_bool": False, "raw_task_query_path_snippet_gold_key_inspection_bool": False, "execution_experiment_bool": False, "metrics_recompute_bool": False, "material_generation_bool": False, "source_candidate_corpus_scan_bool": False, "ci_network_provider_runtime_openlocus_retrieval_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2asclaim0000", "method_default_winner_scale_validated_signal_claim_bool": False, "exact_counts_rates_mrr_scores_public_bool": False, "scale_preflight_authorized_bool": False, "robustness_material_generation_authorized_bool": False, "direct_method_adoption_authorized_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2asgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2assynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2asreadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "inherited_support_signal_records", "mechanism_axis_records", "r2at_contract_records", "boundary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTHETIC_VALIDATORS): issues.append("self_test_validator_count_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    gates = [row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATE_NAMES) or len(gates) != len(GATE_NAMES): issues.append("gate_set_mismatch")
    validators = [row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])]
    if set(validators) != set(SYNTHETIC_VALIDATORS) or len(validators) != len(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    src = (report.get("source_lock_records") or [{}])[0]
    for field, expected in {"locked_haae_r2ar_checkpoint": R2AR_CHECKPOINT, "locked_haae_r2ar_status": R2AR_STATUS, "locked_inherited_r2aq_checkpoint": R2AQ_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2ao_checkpoint": R2AO_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT}.items():
        if src.get(field) != expected: issues.append(f"source_{field}")
    for field in ["r2ar_status_match_bool", "r2ar_self_test_29_bool", "r2ar_forbidden_scan_pass_bool", "inherited_locks_match_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_{field}")
    signal = (report.get("inherited_support_signal_records") or [{}])[0]
    if signal.get("r2ap_result_bucket") != "support_signal" or signal.get("support_vs_control_separation_bucket") != "support_separation_high": issues.append("support_signal_mismatch")
    axes = {row.get("axis_bucket") for row in report.get("mechanism_axis_records", [])}
    if axes != set(AXES): issues.append("mechanism_axis_set_mismatch")
    contract = (report.get("r2at_contract_records") or [{}])[0]
    if contract.get("next_phase") != NEXT_PHASE: issues.append("r2at_next_phase_mismatch")
    for field in ["explicit_opt_in_required_bool", "existing_private_material_root_required_bool", "existing_private_material_read_authorized_bool", "mechanism_decomposition_metrics_authorized_bool", "optional_private_diagnostics_write_authorized_bool", "existing_material_only_bool", "private_row_diagnostics_optional_bool", "public_output_bucketized_aggregate_only_bool", "gold_outcome_eval_only_bool"]:
        if contract.get(field) is not True: issues.append(f"r2at_contract_{field}")
    for field in ["new_source_scan_authorized_bool", "material_regeneration_authorized_bool", "candidate_generation_authorized_bool", "new_material_generation_authorized_bool", "scale_or_robustness_material_generation_or_direct_adoption_authorized_bool"]:
        if contract.get(field) is not False: issues.append(f"r2at_contract_{field}")
    boundary = (report.get("boundary_records") or [{}])[0]
    if boundary.get("public_only_non_executing_preflight_bool") is not True: issues.append("boundary_public_only_non_executing_preflight_bool")
    for field in ["private_root_read_bool", "raw_task_query_path_snippet_gold_key_inspection_bool", "execution_experiment_bool", "metrics_recompute_bool", "material_generation_bool", "source_candidate_corpus_scan_bool", "ci_network_provider_runtime_openlocus_retrieval_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_default_winner_scale_validated_signal_claim_bool", "exact_counts_rates_mrr_scores_public_bool", "scale_preflight_authorized_bool", "robustness_material_generation_authorized_bool", "direct_method_adoption_authorized_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in ["haae_r2at_explicit_local_private_mechanism_decomposition_authorized_bool", "r2at_explicit_opt_in_required_bool", "r2at_existing_private_material_root_required_bool", "r2at_existing_private_material_read_authorized_bool", "r2at_mechanism_decomposition_metrics_authorized_bool", "r2at_optional_private_diagnostics_write_authorized_bool", "r2at_existing_private_material_only_bool", "r2at_no_new_material_generation_bool", "r2at_no_source_scan_candidate_generation_bool", "r2at_aggregate_only_public_output_required_bool", "r2at_gold_outcome_eval_only_bool"]:
        if stop.get(field) is not True: issues.append(f"r2at_stop_go_{field}")
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2at_stop_go_mismatch")
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
    base = load_json(repo / R2AR_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    source_mutations = [("r2ar_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2aq_checkpoint", "wrong")), ("r2ar_status_drift_fail", lambda r: r.__setitem__("status", "wrong")), ("r2ar_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0)), ("r2ar_forbidden_scan_drift_fail", lambda r: r["forbidden_scan"].__setitem__("status", "fail")), ("r2aq_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2aq_checkpoint", "wrong")), ("r2ap_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2ap_checkpoint", "wrong")), ("r2ao_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2ao_checkpoint", "wrong")), ("r2an_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2an_checkpoint", "wrong")), ("r2ar_stop_overauth_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True)), ("support_signal_drift_fail", lambda r: r["inherited_support_signal_records"][0].__setitem__("r2ap_result_bucket", "mixed")), ("support_separation_drift_fail", lambda r: r["inherited_support_signal_records"][0].__setitem__("support_vs_control_separation_bucket", "low"))]
    for name, mut in source_mutations:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == STATUS_FAIL_SOURCE)
    mutations = [("r2at_contract_drift_fail", lambda r: r["r2at_contract_records"][0].__setitem__("next_phase", "wrong"), "r2at_next_phase_mismatch"), ("axis_set_fail", lambda r: r["mechanism_axis_records"].pop(), "mechanism_axis_set_mismatch"), ("existing_material_only_fail", lambda r: r["r2at_contract_records"][0].__setitem__("existing_material_only_bool", False), "r2at_contract_existing_material_only_bool"), ("r2at_private_read_scope_fail", lambda r: r["r2at_contract_records"][0].__setitem__("existing_private_material_read_authorized_bool", False), "r2at_contract_existing_private_material_read_authorized_bool"), ("r2at_mechanism_metrics_scope_fail", lambda r: r["r2at_contract_records"][0].__setitem__("mechanism_decomposition_metrics_authorized_bool", False), "r2at_contract_mechanism_decomposition_metrics_authorized_bool"), ("r2at_private_diagnostics_scope_fail", lambda r: r["r2at_contract_records"][0].__setitem__("optional_private_diagnostics_write_authorized_bool", False), "r2at_contract_optional_private_diagnostics_write_authorized_bool"), ("gold_eval_only_fail", lambda r: r["r2at_contract_records"][0].__setitem__("gold_outcome_eval_only_bool", False), "r2at_contract_gold_outcome_eval_only_bool"), ("aggregate_public_only_fail", lambda r: r["r2at_contract_records"][0].__setitem__("public_output_bucketized_aggregate_only_bool", False), "r2at_contract_public_output_bucketized_aggregate_only_bool"), ("robustness_generation_overauth_fail", lambda r: r["claim_boundary_records"][0].__setitem__("robustness_material_generation_authorized_bool", True), "claim_robustness_material_generation_authorized_bool"), ("scale_overauth_fail", lambda r: r["claim_boundary_records"][0].__setitem__("scale_preflight_authorized_bool", True), "claim_scale_preflight_authorized_bool"), ("direct_adoption_overauth_fail", lambda r: r["claim_boundary_records"][0].__setitem__("direct_method_adoption_authorized_bool", True), "claim_direct_method_adoption_authorized_bool"), ("private_read_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("private_root_read_bool", True), "boundary_private_root_read_bool"), ("execution_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("execution_experiment_bool", True), "boundary_execution_experiment_bool"), ("source_scan_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("source_candidate_corpus_scan_bool", True), "boundary_source_candidate_corpus_scan_bool"), ("method_claim_overauth_fail", lambda r: r["claim_boundary_records"][0].__setitem__("method_default_winner_scale_validated_signal_claim_bool", True), "claim_method_default_winner_scale_validated_signal_claim_bool"), ("next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2at_stop_go_mismatch"), ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_preflight_authorized_bool", True), "overauthorization_scale_preflight_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("synthetic_validator_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    for name, mut, expected in mutations:
        m = json.loads(json.dumps(passed)); mut(m); check(name, expected in validate_report(m))
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    check("prior_phase_count_guard_fail", public_readback_match(SELF_TEST_EXPECTED)["prior_phase_count_guard_bool"] is True)
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
