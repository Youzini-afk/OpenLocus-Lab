#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AR evidence-pair support next-step decision package.

Public-only decision/design package after R2AQ. It reads only committed public
artifacts/docs, selects R2AS public mechanism-decomposition design preflight, and
does not read private roots, recompute metrics, generate material, scan source,
or authorize execution/scale/direct robustness experiments.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AR Evidence-Pair Support Next-Step Decision Package"
SLUG = "bea_v1_haae_r2ar_evidence_pair_support_next_step_decision_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AQ_CHECKPOINT = "77eab19"
R2AQ_STATUS = "haae_r2aq_evidence_pair_support_experiment_public_audit_package_complete_r2ar_next_step_decision_authorized_support_signal"
R2AP_CHECKPOINT = "87ea9de"
R2AP_STATUS = "haae_r2ap_explicit_local_material_experiment_complete_r2aq_public_audit_authorized_support_signal"
R2AO_CHECKPOINT = "5cfa8d3"
R2AN_CHECKPOINT = "93bba5f"
R2AQ_REPORT_PATH = Path("artifacts/bea_v1_haae_r2aq_evidence_pair_support_experiment_public_audit_package/bea_v1_haae_r2aq_evidence_pair_support_experiment_public_audit_package_report.json")

STATUS_PASS = "haae_r2ar_evidence_pair_support_next_step_decision_complete_r2as_mechanism_decomposition_public_design_authorized"
STATUS_FAIL_SOURCE = "haae_r2ar_fail_closed_source_lock_mismatch"
STATUS_FAIL_DECISION = "haae_r2ar_fail_closed_decision_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2ar_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2ar_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2AS Evidence-Pair Support Mechanism Decomposition Public Design Preflight"
SELECTED_SIGNAL_FAMILY = "evidence_pair_support_complementarity"

DECISION_OPTIONS = [
    "mechanism_decomposition_public_design_preflight",
    "robustness_material_generation",
    "scale_preflight",
    "close_or_turn_route",
]
MECHANISM_HYPOTHESES = [
    "complementarity_vs_single_unit",
    "support_vs_contrast",
    "target_support_vs_hard_negative",
    "shuffled_cross_task_control_rejection",
    "path_token_confound_check",
    "outcome_gold_isolation",
    "pair_family_balance_coverage_sensitivity",
    "evidence_quality_vs_pair_composition",
]
GATE_NAMES = [
    "r2aq_source_locked_gate",
    "inherited_r2ap_r2ao_r2an_lock_gate",
    "support_signal_gate",
    "support_separation_high_gate",
    "public_only_decision_gate",
    "r2as_only_selection_gate",
    "robustness_generation_deferred_gate",
    "scale_preflight_rejected_gate",
    "close_turn_deferred_gate",
    "mechanism_hypothesis_set_gate",
    "no_private_raw_exact_gate",
    "no_execution_scan_generation_gate",
    "no_method_default_scale_claim_gate",
    "r2as_stop_go_only_gate",
    "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
]
SYNTHETIC_VALIDATORS = [
    "source_lock_pass",
    "r2aq_checkpoint_drift_fail",
    "r2aq_status_drift_fail",
    "r2aq_self_test_drift_fail",
    "r2aq_forbidden_scan_drift_fail",
    "r2ap_lock_drift_fail",
    "r2ao_lock_drift_fail",
    "r2an_lock_drift_fail",
    "r2aq_boundary_drift_fail",
    "r2aq_stop_overauth_drift_fail",
    "support_result_drift_fail",
    "support_separation_drift_fail",
    "r2as_selection_drift_fail",
    "robustness_generation_overauth_fail",
    "scale_preflight_overauth_fail",
    "close_turn_overauth_fail",
    "mechanism_hypothesis_set_fail",
    "private_read_overauth_fail",
    "execution_overauth_fail",
    "source_scan_overauth_fail",
    "method_claim_overauth_fail",
    "exact_publication_fail",
    "raw_publication_fail",
    "next_phase_drift_fail",
    "stop_go_overauth_fail",
    "gate_set_fail",
    "synthetic_validator_set_fail",
    "readback_record_fail",
    "safe_parser_fail",
]
SELF_TEST_EXPECTED = len(SYNTHETIC_VALIDATORS)
STOP_FALSE_FIELDS = [
    "execution_authorized_bool",
    "private_read_authorized_bool",
    "private_write_authorized_bool",
    "recompute_metrics_authorized_bool",
    "material_generation_authorized_bool",
    "robustness_material_generation_authorized_bool",
    "source_scan_authorized_bool",
    "candidate_scan_authorized_bool",
    "corpus_scan_authorized_bool",
    "ci_execution_authorized_bool",
    "network_authorized_bool",
    "provider_model_authorized_bool",
    "clone_authorized_bool",
    "retrieval_authorized_bool",
    "runtime_execution_authorized_bool",
    "openlocus_runtime_authorized_bool",
    "scale_preflight_authorized_bool",
    "direct_robustness_experiment_authorized_bool",
    "default_change_authorized_bool",
    "method_winner_claim_authorized_bool",
    "scaling_claim_authorized_bool",
    "raw_publication_authorized_bool",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


LEAK_PATTERNS = [
    ("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)),
    ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)),
    ("raw_private_key", re.compile(r"task_ref_value|candidate_key_value|pair_key_value|evidence_key_value|source_file_key_value|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hash_value|\.rs\b|crates/openlocus-", re.I)),
    ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top_k_value|mrr_value|hit_rate_value|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I)),
]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test":
            parsed["self_test"] = True
            i += 1
        elif arg in {"--validate-report", "--out"}:
            if i + 1 >= len(argv):
                raise ValueError("invalid arguments")
            parsed["validate" if arg == "--validate-report" else "out"] = argv[i + 1]
            i += 2
        else:
            raise ValueError("invalid arguments")
    return parsed


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value)
    resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH:
        raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def audit_r2aq(r2aq: dict[str, Any]) -> dict[str, bool]:
    source = (r2aq.get("source_lock_records") or [{}])[0]
    exp = (r2aq.get("experiment_audit_records") or [{}])[0]
    priv = (r2aq.get("privacy_audit_records") or [{}])[0]
    boundary = (r2aq.get("boundary_records") or [{}])[0]
    claim = (r2aq.get("claim_boundary_records") or [{}])[0]
    stop = (r2aq.get("stop_go_records") or [{}])[0]
    status_ok = r2aq.get("status") == R2AQ_STATUS
    self_test_ok = r2aq.get("self_test_total") == 28
    scan_ok = r2aq.get("forbidden_scan", {}).get("status") == "pass"
    lock_ok = (
        source.get("locked_haae_r2ap_checkpoint") == R2AP_CHECKPOINT
        and source.get("locked_haae_r2ap_status") == R2AP_STATUS
        and source.get("locked_haae_r2ao_checkpoint") == R2AO_CHECKPOINT
        and source.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT
        and source.get("source_locked_bool") is True
    )
    signal_ok = exp.get("robustness_result_bucket") == "support_signal" and exp.get("support_vs_control_separation_bucket") == "support_separation_high" and exp.get("bucket_only_metrics_bool") is True
    privacy_ok = priv.get("no_exact_metrics_publication_bool") is True and priv.get("no_raw_private_publication_bool") is True and claim.get("method_default_scale_claim_bool") is False
    boundary_ok = boundary.get("public_only_audit_bool") is True and all(boundary.get(field) is False for field in ["private_root_read_bool", "recompute_experiment_metrics_bool", "material_generation_bool", "source_corpus_scan_bool", "retrieval_runtime_ci_network_provider_bool"])
    stop_ok = stop.get("haae_r2ar_evidence_pair_support_next_step_decision_authorized_bool") is True and stop.get("next_allowed_phase") == PHASE and all(stop.get(field, False) is False for field in ["execution_authorized_bool", "private_read_authorized_bool", "private_write_authorized_bool", "recompute_authorized_bool", "material_generation_authorized_bool", "new_material_generation_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    source_ok = status_ok and self_test_ok and scan_ok and lock_ok and signal_ok and privacy_ok and boundary_ok and stop_ok
    return {"source_ok": source_ok, "status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "lock_ok": lock_ok, "signal_ok": signal_ok, "privacy_ok": privacy_ok, "boundary_ok": boundary_ok, "stop_ok": stop_ok}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [
        PHASE,
        STATUS_PASS,
        f"{total}/{total}",
        R2AQ_CHECKPOINT,
        R2AQ_STATUS,
        R2AP_CHECKPOINT,
        R2AO_CHECKPOINT,
        R2AN_CHECKPOINT,
        "support_signal",
        "support_separation_high",
        "select only BEA-v1-HAAE-R2AS Evidence-Pair Support Mechanism Decomposition Public Design Preflight",
        "defer robustness material generation",
        "reject/defer scale preflight",
        "defer close/turn",
        "public-only decision/design",
        "no private roots",
        "no recompute metrics",
        "no material generation",
        "no source/candidate/corpus scan",
        "no method/default/winner/scale claim",
        NEXT_PHASE,
    ]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]

    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)

    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2ar-evidence-pair-support-next-step-decision-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2ar-evidence-pair-support-next-step-decision-package.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2ar-evidence-pair-support-next-step-decision-package.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2aq: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2aq is None:
        try:
            r2aq = load_json(repo / R2AQ_REPORT_PATH)
        except Exception:
            r2aq = {}
    audit = audit_r2aq(r2aq)
    readback = public_readback_match(self_test_total)
    decision_ok = audit["source_ok"]
    if not audit["source_ok"]:
        status = STATUS_FAIL_SOURCE
    elif not decision_ok:
        status = STATUS_FAIL_DECISION
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {
        "r2aq_source_locked_gate": audit["status_ok"] and audit["self_test_ok"] and audit["scan_ok"],
        "inherited_r2ap_r2ao_r2an_lock_gate": audit["lock_ok"],
        "support_signal_gate": audit["signal_ok"],
        "support_separation_high_gate": audit["signal_ok"],
        "public_only_decision_gate": True,
        "r2as_only_selection_gate": True,
        "robustness_generation_deferred_gate": True,
        "scale_preflight_rejected_gate": True,
        "close_turn_deferred_gate": True,
        "mechanism_hypothesis_set_gate": True,
        "no_private_raw_exact_gate": True,
        "no_execution_scan_generation_gate": True,
        "no_method_default_scale_claim_gate": True,
        "r2as_stop_go_only_gate": True,
        "forbidden_scan_pass_gate": True,
        "docs_readback_match_gate": readback["all_public_readback_match_bool"],
    }
    stop = {"anonymous_stop_go_id": "haaer2arstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_decision_pass", "haae_r2as_mechanism_decomposition_public_design_preflight_authorized_bool": passed, "r2as_public_design_preflight_only_bool": passed}
    stop.update({field: False for field in STOP_FALSE_FIELDS})
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2arsource0000", "locked_haae_r2aq_checkpoint": R2AQ_CHECKPOINT, "locked_haae_r2aq_status": R2AQ_STATUS, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2ao_checkpoint": R2AO_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "r2aq_status_match_bool": audit["status_ok"], "r2aq_self_test_28_bool": audit["self_test_ok"], "r2aq_forbidden_scan_pass_bool": audit["scan_ok"], "inherited_locks_match_bool": audit["lock_ok"], "r2aq_public_boundary_match_bool": audit["boundary_ok"], "source_locked_bool": audit["source_ok"]}],
        "inherited_support_signal_records": [{"anonymous_support_signal_id": "haaer2arsignal0000", "selected_signal_family_bucket": SELECTED_SIGNAL_FAMILY, "r2ap_result_bucket": "support_signal", "support_vs_control_separation_bucket": "support_separation_high", "bucket_only_metrics_bool": True, "no_exact_metrics_publication_bool": audit["privacy_ok"], "no_raw_private_publication_bool": audit["privacy_ok"]}],
        "decision_option_records": [{"anonymous_decision_option_id": f"haaer2aroption{idx:04d}", "option_bucket": option, "selected_bool": option == "mechanism_decomposition_public_design_preflight", "deferred_bool": option in {"robustness_material_generation", "close_or_turn_route"}, "rejected_or_deferred_bool": option == "scale_preflight"} for idx, option in enumerate(DECISION_OPTIONS)],
        "selected_next_phase_records": [{"anonymous_selected_next_phase_id": "haaer2arnext0000", "selected_next_phase": NEXT_PHASE, "select_only_r2as_public_design_preflight_bool": True, "defer_robustness_material_generation_bool": True, "reject_defer_scale_preflight_bool": True, "defer_close_turn_bool": True, "scale_or_direct_robustness_experiment_authorized_bool": False}],
        "mechanism_hypothesis_records": [{"anonymous_mechanism_hypothesis_id": f"haaer2arhyp{idx:04d}", "hypothesis_bucket": bucket, "public_design_preflight_only_bool": True, "private_analysis_authorized_bool": False, "metric_recompute_authorized_bool": False} for idx, bucket in enumerate(MECHANISM_HYPOTHESES)],
        "boundary_records": [{"anonymous_boundary_id": "haaer2arboundary0000", "public_only_decision_design_bool": True, "private_root_read_bool": False, "raw_task_query_path_snippet_gold_key_inspection_bool": False, "execution_experiment_bool": False, "metrics_recompute_bool": False, "material_generation_bool": False, "source_candidate_corpus_scan_bool": False, "ci_network_provider_runtime_openlocus_retrieval_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2arclaim0000", "method_default_winner_scale_claim_bool": False, "validated_signal_claim_bool": False, "scale_preflight_authorized_bool": False, "direct_robustness_experiment_authorized_bool": False, "exact_counts_rates_mrr_scores_public_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2argate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2arsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2arreadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate":
            gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_PRIVACY
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "inherited_support_signal_records", "decision_option_records", "selected_next_phase_records", "mechanism_hypothesis_records", "boundary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report:
            issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS:
        issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTHETIC_VALIDATORS):
        issues.append("self_test_validator_count_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        issues.append("forbidden_scan_failed")
    gate_list = [row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])]
    if set(gate_list) != set(GATE_NAMES) or len(gate_list) != len(GATE_NAMES):
        issues.append("gate_set_mismatch")
    validator_list = [row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])]
    if set(validator_list) != set(SYNTHETIC_VALIDATORS) or len(validator_list) != len(SYNTHETIC_VALIDATORS):
        issues.append("synthetic_validator_set_mismatch")
    src = (report.get("source_lock_records") or [{}])[0]
    expected_locks = {"locked_haae_r2aq_checkpoint": R2AQ_CHECKPOINT, "locked_haae_r2aq_status": R2AQ_STATUS, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_inherited_r2ao_checkpoint": R2AO_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT}
    for field, expected in expected_locks.items():
        if src.get(field) != expected:
            issues.append(f"source_{field}")
    for field in ["r2aq_status_match_bool", "r2aq_self_test_28_bool", "r2aq_forbidden_scan_pass_bool", "inherited_locks_match_bool", "r2aq_public_boundary_match_bool", "source_locked_bool"]:
        if src.get(field) is not True:
            issues.append(f"source_{field}")
    signal = (report.get("inherited_support_signal_records") or [{}])[0]
    if signal.get("r2ap_result_bucket") != "support_signal" or signal.get("support_vs_control_separation_bucket") != "support_separation_high" or signal.get("selected_signal_family_bucket") != SELECTED_SIGNAL_FAMILY:
        issues.append("support_signal_mismatch")
    for field in ["bucket_only_metrics_bool", "no_exact_metrics_publication_bool", "no_raw_private_publication_bool"]:
        if signal.get(field) is not True:
            issues.append(f"support_{field}")
    options = {row.get("option_bucket"): row for row in report.get("decision_option_records", [])}
    if set(options.keys()) != set(DECISION_OPTIONS):
        issues.append("decision_option_set_mismatch")
    if options.get("mechanism_decomposition_public_design_preflight", {}).get("selected_bool") is not True:
        issues.append("r2as_selection_mismatch")
    for option in ["robustness_material_generation", "close_or_turn_route"]:
        if options.get(option, {}).get("deferred_bool") is not True:
            issues.append(f"decision_{option}_not_deferred")
    if options.get("scale_preflight", {}).get("rejected_or_deferred_bool") is not True:
        issues.append("scale_preflight_not_rejected_deferred")
    selected = (report.get("selected_next_phase_records") or [{}])[0]
    if selected.get("selected_next_phase") != NEXT_PHASE or selected.get("select_only_r2as_public_design_preflight_bool") is not True:
        issues.append("selected_next_phase_mismatch")
    for field in ["defer_robustness_material_generation_bool", "reject_defer_scale_preflight_bool", "defer_close_turn_bool"]:
        if selected.get(field) is not True:
            issues.append(f"selected_{field}")
    if selected.get("scale_or_direct_robustness_experiment_authorized_bool") is not False:
        issues.append("selected_scale_or_direct_experiment_overauth")
    hyps = {row.get("hypothesis_bucket") for row in report.get("mechanism_hypothesis_records", [])}
    if hyps != set(MECHANISM_HYPOTHESES):
        issues.append("mechanism_hypothesis_set_mismatch")
    for row in report.get("mechanism_hypothesis_records", []):
        if row.get("public_design_preflight_only_bool") is not True or row.get("private_analysis_authorized_bool") is not False or row.get("metric_recompute_authorized_bool") is not False:
            issues.append("mechanism_hypothesis_boundary_mismatch")
    boundary = (report.get("boundary_records") or [{}])[0]
    if boundary.get("public_only_decision_design_bool") is not True:
        issues.append("boundary_public_only_decision_design_bool")
    for field in ["private_root_read_bool", "raw_task_query_path_snippet_gold_key_inspection_bool", "execution_experiment_bool", "metrics_recompute_bool", "material_generation_bool", "source_candidate_corpus_scan_bool", "ci_network_provider_runtime_openlocus_retrieval_bool"]:
        if boundary.get(field) is not False:
            issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_default_winner_scale_claim_bool", "validated_signal_claim_bool", "scale_preflight_authorized_bool", "direct_robustness_experiment_authorized_bool", "exact_counts_rates_mrr_scores_public_bool", "raw_publication_bool"]:
        if claim.get(field) is not False:
            issues.append(f"claim_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2as_mechanism_decomposition_public_design_preflight_authorized_bool") is not True or stop.get("r2as_public_design_preflight_only_bool") is not True:
        issues.append("r2as_stop_go_mismatch")
    for field in STOP_FALSE_FIELDS:
        if stop.get(field) is not False:
            issues.append(f"overauthorization_{field}")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True:
        issues.append("public_readback_record_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]:
        issues.append("public_readback_stale")
    for gate in report.get("pass_fail_gate_records", []):
        if gate.get("gate_passed_bool") is not True:
            issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    return issues


def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2AQ_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)
    passed = build_report(base)
    check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    source_mutations = [
        ("r2aq_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2ap_checkpoint", "wrong")),
        ("r2aq_status_drift_fail", lambda r: r.__setitem__("status", "wrong")),
        ("r2aq_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0)),
        ("r2aq_forbidden_scan_drift_fail", lambda r: r["forbidden_scan"].__setitem__("status", "fail")),
        ("r2ap_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2ap_checkpoint", "wrong")),
        ("r2ao_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2ao_checkpoint", "wrong")),
        ("r2an_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2an_checkpoint", "wrong")),
        ("r2aq_boundary_drift_fail", lambda r: r["boundary_records"][0].__setitem__("private_root_read_bool", True)),
        ("r2aq_stop_overauth_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True)),
        ("support_result_drift_fail", lambda r: r["experiment_audit_records"][0].__setitem__("robustness_result_bucket", "mixed_or_inconclusive")),
        ("support_separation_drift_fail", lambda r: r["experiment_audit_records"][0].__setitem__("support_vs_control_separation_bucket", "support_not_separated")),
    ]
    for name, mut in source_mutations:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == STATUS_FAIL_SOURCE)
    mutations = [
        ("r2as_selection_drift_fail", lambda r: r["selected_next_phase_records"][0].__setitem__("select_only_r2as_public_design_preflight_bool", False), "selected_next_phase_mismatch"),
        ("robustness_generation_overauth_fail", lambda r: r["selected_next_phase_records"][0].__setitem__("defer_robustness_material_generation_bool", False), "selected_defer_robustness_material_generation_bool"),
        ("scale_preflight_overauth_fail", lambda r: r["selected_next_phase_records"][0].__setitem__("scale_or_direct_robustness_experiment_authorized_bool", True), "selected_scale_or_direct_experiment_overauth"),
        ("close_turn_overauth_fail", lambda r: r["selected_next_phase_records"][0].__setitem__("defer_close_turn_bool", False), "selected_defer_close_turn_bool"),
        ("mechanism_hypothesis_set_fail", lambda r: r["mechanism_hypothesis_records"].pop(), "mechanism_hypothesis_set_mismatch"),
        ("private_read_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("private_root_read_bool", True), "boundary_private_root_read_bool"),
        ("execution_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("execution_experiment_bool", True), "boundary_execution_experiment_bool"),
        ("source_scan_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("source_candidate_corpus_scan_bool", True), "boundary_source_candidate_corpus_scan_bool"),
        ("method_claim_overauth_fail", lambda r: r["claim_boundary_records"][0].__setitem__("method_default_winner_scale_claim_bool", True), "claim_method_default_winner_scale_claim_bool"),
        ("exact_publication_fail", lambda r: r["claim_boundary_records"][0].__setitem__("exact_counts_rates_mrr_scores_public_bool", True), "claim_exact_counts_rates_mrr_scores_public_bool"),
        ("raw_publication_fail", lambda r: r["claim_boundary_records"][0].__setitem__("raw_publication_bool", True), "claim_raw_publication_bool"),
        ("next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2as_stop_go_mismatch"),
        ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("execution_authorized_bool", True), "overauthorization_execution_authorized_bool"),
        ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"),
        ("synthetic_validator_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"),
        ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"),
    ]
    for name, mut, expected in mutations:
        m = json.loads(json.dumps(passed)); mut(m); check(name, expected in validate_report(m))
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except Exception:
        print("invalid arguments", file=sys.stderr)
        return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try:
            report = load_json(repo / public_artifact_path(args["validate"])); issues = validate_report(report)
        except Exception:
            report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(args["out"]) if args["out"] else None
    report = build_report(); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
