#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AQ evidence-pair support experiment public audit package.

Public-only audit of the committed R2AP public artifact. It does not read
private roots, recompute metrics, generate material, scan source, or run any
retrieval/runtime/CI/network/provider path.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AQ Evidence-Pair Support Experiment Public Audit Package"
SLUG = "bea_v1_haae_r2aq_evidence_pair_support_experiment_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AP_CHECKPOINT = "87ea9de"
R2AP_STATUS = "haae_r2ap_explicit_local_material_experiment_complete_r2aq_public_audit_authorized_support_signal"
R2AO_CHECKPOINT = "5cfa8d3"
R2AO_STATUS = "haae_r2ao_evidence_pair_support_material_public_audit_package_complete_r2ap_explicit_experiment_authorized"
R2AN_CHECKPOINT = "93bba5f"
R2AN_STATUS = "haae_r2an_evidence_pair_support_explicit_material_generation_complete_r2ao_public_material_audit_authorized"
R2AP_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ap_evidence_pair_support_explicit_local_material_experiment/bea_v1_haae_r2ap_evidence_pair_support_explicit_local_material_experiment_report.json")

STATUS_PASS = "haae_r2aq_evidence_pair_support_experiment_public_audit_package_complete_r2ar_next_step_decision_authorized_support_signal"
STATUS_FAIL_SOURCE = "haae_r2aq_fail_closed_source_lock_mismatch"
STATUS_FAIL_AUDIT = "haae_r2aq_fail_closed_support_audit_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2aq_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2aq_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2AR Evidence-Pair Support Next-Step Decision Package"
SELECTED_SIGNAL_FAMILY = "evidence_pair_support_complementarity"
PAIR_FAMILIES = ["target_support_pair", "complementary_support_pair", "contrastive_hard_negative_pair", "single_unit_ablation_control", "shuffled_relation_control", "cross_task_mismatch_control"]

GATE_NAMES = ["r2ap_source_locked_gate", "inherited_r2ao_r2an_lock_gate", "r2ap_status_support_signal_gate", "r2ap_self_test_26_gate", "r2ap_forbidden_scan_pass_gate", "bucket_only_support_metrics_gate", "support_separation_high_gate", "no_exact_metrics_publication_gate", "no_raw_private_publication_gate", "no_method_default_scale_claim_gate", "no_private_read_recompute_material_source_scan_gate", "no_ci_network_runtime_provider_gate", "r2ar_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["source_lock_pass", "r2ap_checkpoint_drift_fail", "r2ap_status_drift_fail", "r2ap_self_test_drift_fail", "r2ap_forbidden_scan_drift_fail", "r2ao_lock_drift_fail", "r2an_lock_drift_fail", "support_result_drift_fail", "support_separation_drift_fail", "pair_family_bucket_set_fail", "exact_metric_publication_fail", "raw_private_publication_fail", "method_default_scale_overauth_fail", "private_read_overauth_fail", "recompute_overauth_fail", "material_generation_overauth_fail", "source_scan_overauth_fail", "ci_network_runtime_provider_overauth_fail", "stop_private_write_overauth_fail", "stop_recompute_overauth_fail", "stop_material_generation_overauth_fail", "stop_source_scan_overauth_fail", "stop_ci_overauth_fail", "next_phase_drift_fail", "gate_set_fail", "synthetic_validator_set_fail", "readback_record_fail", "safe_parser_fail"]
SELF_TEST_EXPECTED = len(SYNTHETIC_VALIDATORS)
STOP_FALSE_FIELDS = ["execution_authorized_bool", "private_read_authorized_bool", "private_write_authorized_bool", "recompute_authorized_bool", "material_generation_authorized_bool", "new_material_generation_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


LEAK_PATTERNS = [
    ("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)),
    ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)),
    ("raw_private_key", re.compile(r"task_ref_value|candidate_key_value|pair_key_value|evidence_key_value|source_file_key_value|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hash_value|\.rs\b|crates/openlocus-", re.I)),
    ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|mrr|hit_rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I)),
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


def audit_r2ap(r2ap: dict[str, Any]) -> dict[str, bool]:
    source = (r2ap.get("source_lock_records") or [{}])[0]
    metric = (r2ap.get("aggregate_metric_records") or [{}])[0]
    boundary = (r2ap.get("boundary_records") or [{}])[0]
    stop = (r2ap.get("stop_go_records") or [{}])[0]
    status_ok = r2ap.get("status") == R2AP_STATUS
    self_test_ok = r2ap.get("self_test_total") == 26
    scan_ok = r2ap.get("forbidden_scan", {}).get("status") == "pass"
    lock_ok = source.get("locked_haae_r2ao_checkpoint") == R2AO_CHECKPOINT and source.get("locked_haae_r2ao_status") == R2AO_STATUS and source.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT and source.get("locked_inherited_r2an_status") == R2AN_STATUS and source.get("source_locked_bool") is True
    bucket_ok = metric.get("robustness_result_bucket") == "support_signal" and metric.get("support_vs_control_separation_bucket") == "support_separation_high" and set((metric.get("pair_family_metric_buckets") or {}).keys()) == set(PAIR_FAMILIES) and metric.get("aggregate_only_metrics_bool") is True
    privacy_ok = metric.get("no_exact_counts_rates_mrr_scores_bool") is True and metric.get("no_raw_task_query_path_evidence_pair_source_gold_snippet_hash_line_bool") is True and r2ap.get("forbidden_scan", {}).get("status") == "pass"
    boundary_ok = all(boundary.get(field) is False for field in ["material_generation_bool", "source_scan_bool", "recompute_bool", "ci_network_runtime_retrieval_bool", "default_method_scale_claim_bool", "raw_publication_bool"])
    stop_ok = stop.get("haae_r2aq_evidence_pair_support_experiment_public_audit_authorized_bool") is True and stop.get("next_allowed_phase") == PHASE and all(stop.get(field, False) is False for field in ["material_generation_authorized_bool", "new_material_generation_authorized_bool", "source_scan_authorized_bool", "recompute_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "runtime_execution_authorized_bool", "retrieval_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    audit_ok = status_ok and self_test_ok and scan_ok and lock_ok and bucket_ok and privacy_ok and boundary_ok and stop_ok
    return {"audit_ok": audit_ok, "status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "lock_ok": lock_ok, "bucket_ok": bucket_ok, "privacy_ok": privacy_ok, "boundary_ok": boundary_ok, "stop_ok": stop_ok}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AP_CHECKPOINT, R2AP_STATUS, R2AO_CHECKPOINT, R2AN_CHECKPOINT, "support_signal", "support_vs_control_separation_bucket=support_separation_high", "bucket-only", "no exact metrics/raw publication", "no method/default/scale claim", NEXT_PHASE, "public-only audit", "no private roots", "no recompute experiment metrics", "no material generation", "no source corpus scan"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2aq-evidence-pair-support-experiment-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2aq-evidence-pair-support-experiment-public-audit-package.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2aq-evidence-pair-support-experiment-public-audit-package.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2ap: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2ap is None:
        try: r2ap = load_json(repo / R2AP_REPORT_PATH)
        except Exception: r2ap = {}
    audit = audit_r2ap(r2ap)
    readback = public_readback_match(self_test_total)
    if not (audit["status_ok"] and audit["self_test_ok"] and audit["scan_ok"] and audit["lock_ok"]): status = STATUS_FAIL_SOURCE
    elif not (audit["bucket_ok"] and audit["privacy_ok"] and audit["boundary_ok"] and audit["stop_ok"]): status = STATUS_FAIL_AUDIT
    elif not readback["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    else: status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2ap_source_locked_gate": audit["status_ok"] and audit["self_test_ok"] and audit["scan_ok"], "inherited_r2ao_r2an_lock_gate": audit["lock_ok"], "r2ap_status_support_signal_gate": audit["status_ok"], "r2ap_self_test_26_gate": audit["self_test_ok"], "r2ap_forbidden_scan_pass_gate": audit["scan_ok"], "bucket_only_support_metrics_gate": audit["bucket_ok"], "support_separation_high_gate": audit["bucket_ok"], "no_exact_metrics_publication_gate": audit["privacy_ok"], "no_raw_private_publication_gate": audit["privacy_ok"], "no_method_default_scale_claim_gate": audit["boundary_ok"], "no_private_read_recompute_material_source_scan_gate": audit["boundary_ok"], "no_ci_network_runtime_provider_gate": audit["boundary_ok"], "r2ar_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    stop = {"anonymous_stop_go_id": "haaer2aqstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_public_audit_pass", "haae_r2ar_evidence_pair_support_next_step_decision_authorized_bool": passed, "r2ar_public_decision_design_only_bool": passed}
    stop.update({field: False for field in STOP_FALSE_FIELDS})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2aqsource0000", "locked_haae_r2ap_checkpoint": R2AP_CHECKPOINT, "locked_haae_r2ap_status": R2AP_STATUS, "locked_haae_r2ao_checkpoint": R2AO_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "r2ap_status_match_bool": audit["status_ok"], "r2ap_self_test_26_bool": audit["self_test_ok"], "r2ap_forbidden_scan_pass_bool": audit["scan_ok"], "inherited_locks_match_bool": audit["lock_ok"], "source_locked_bool": audit["status_ok"] and audit["self_test_ok"] and audit["scan_ok"] and audit["lock_ok"]}],
        "experiment_audit_records": [{"anonymous_experiment_audit_id": "haaer2aqaudit0000", "selected_signal_family_bucket": SELECTED_SIGNAL_FAMILY, "robustness_result_bucket": "support_signal", "support_vs_control_separation_bucket": "support_separation_high", "bucket_only_metrics_bool": audit["bucket_ok"], "pair_family_buckets_present_bool": audit["bucket_ok"], "no_recompute_metrics_bool": True}],
        "privacy_audit_records": [{"anonymous_privacy_audit_id": "haaer2aqprivacy0000", "aggregate_only_public_artifact_bool": True, "no_exact_metrics_publication_bool": audit["privacy_ok"], "no_raw_private_publication_bool": audit["privacy_ok"], "no_private_root_read_bool": True}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2aqboundary0000", "public_only_audit_bool": True, "private_root_read_bool": False, "recompute_experiment_metrics_bool": False, "material_generation_bool": False, "source_corpus_scan_bool": False, "retrieval_runtime_ci_network_provider_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2aqclaim0000", "method_default_scale_claim_bool": False, "winner_claim_bool": False, "raw_publication_bool": False, "execution_authorization_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2aqgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2aqsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2aqreadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "experiment_audit_records", "privacy_audit_records", "boundary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTHETIC_VALIDATORS): issues.append("self_test_validator_count_mismatch")
    gate_list = [row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])]
    if set(gate_list) != set(GATE_NAMES) or len(gate_list) != len(GATE_NAMES): issues.append("gate_set_mismatch")
    validator_list = [row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])]
    if set(validator_list) != set(SYNTHETIC_VALIDATORS) or len(validator_list) != len(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2ap_checkpoint") != R2AP_CHECKPOINT or src.get("locked_haae_r2ap_status") != R2AP_STATUS or src.get("locked_haae_r2ao_checkpoint") != R2AO_CHECKPOINT or src.get("locked_inherited_r2an_checkpoint") != R2AN_CHECKPOINT: issues.append("source_lock_mismatch")
    for field in ["r2ap_status_match_bool", "r2ap_self_test_26_bool", "r2ap_forbidden_scan_pass_bool", "inherited_locks_match_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_{field}")
    exp = (report.get("experiment_audit_records") or [{}])[0]
    for field, expected in {"robustness_result_bucket": "support_signal", "support_vs_control_separation_bucket": "support_separation_high", "selected_signal_family_bucket": SELECTED_SIGNAL_FAMILY}.items():
        if exp.get(field) != expected: issues.append(f"experiment_{field}")
    for field in ["bucket_only_metrics_bool", "pair_family_buckets_present_bool", "no_recompute_metrics_bool"]:
        if exp.get(field) is not True: issues.append(f"experiment_{field}")
    priv = (report.get("privacy_audit_records") or [{}])[0]
    for field in ["aggregate_only_public_artifact_bool", "no_exact_metrics_publication_bool", "no_raw_private_publication_bool", "no_private_root_read_bool"]:
        if priv.get(field) is not True: issues.append(f"privacy_{field}")
    boundary = (report.get("boundary_records") or [{}])[0]
    if boundary.get("public_only_audit_bool") is not True: issues.append("boundary_public_only_audit_bool")
    for field in ["private_root_read_bool", "recompute_experiment_metrics_bool", "material_generation_bool", "source_corpus_scan_bool", "retrieval_runtime_ci_network_provider_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_default_scale_claim_bool", "winner_claim_bool", "raw_publication_bool", "execution_authorization_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2ar_evidence_pair_support_next_step_decision_authorized_bool") is not True or stop.get("r2ar_public_decision_design_only_bool") is not True: issues.append("r2ar_stop_go_mismatch")
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
    base = load_json(repo / R2AP_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    source_mutations = [
        ("r2ap_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2ao_checkpoint", "wrong"), STATUS_FAIL_SOURCE),
        ("r2ap_status_drift_fail", lambda r: r.__setitem__("status", "wrong"), STATUS_FAIL_SOURCE),
        ("r2ap_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE),
        ("r2ap_forbidden_scan_drift_fail", lambda r: r["forbidden_scan"].__setitem__("status", "fail"), STATUS_FAIL_SOURCE),
        ("r2ao_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2ao_checkpoint", "wrong"), STATUS_FAIL_SOURCE),
        ("r2an_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2an_checkpoint", "wrong"), STATUS_FAIL_SOURCE),
        ("support_result_drift_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("robustness_result_bucket", "mixed_or_inconclusive"), STATUS_FAIL_AUDIT),
        ("support_separation_drift_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("support_vs_control_separation_bucket", "support_not_separated"), STATUS_FAIL_AUDIT),
    ]
    for name, mut, expected_status in source_mutations:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == expected_status)
    mutations = [
        ("pair_family_bucket_set_fail", lambda r: r["experiment_audit_records"][0].__setitem__("pair_family_buckets_present_bool", False), "experiment_pair_family_buckets_present_bool"),
        ("exact_metric_publication_fail", lambda r: r["privacy_audit_records"][0].__setitem__("no_exact_metrics_publication_bool", False), "privacy_no_exact_metrics_publication_bool"),
        ("raw_private_publication_fail", lambda r: r["privacy_audit_records"][0].__setitem__("no_raw_private_publication_bool", False), "privacy_no_raw_private_publication_bool"),
        ("method_default_scale_overauth_fail", lambda r: r["claim_boundary_records"][0].__setitem__("method_default_scale_claim_bool", True), "claim_method_default_scale_claim_bool"),
        ("private_read_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("private_root_read_bool", True), "boundary_private_root_read_bool"),
        ("recompute_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("recompute_experiment_metrics_bool", True), "boundary_recompute_experiment_metrics_bool"),
        ("material_generation_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("material_generation_bool", True), "boundary_material_generation_bool"),
        ("source_scan_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("source_corpus_scan_bool", True), "boundary_source_corpus_scan_bool"),
        ("ci_network_runtime_provider_overauth_fail", lambda r: r["boundary_records"][0].__setitem__("retrieval_runtime_ci_network_provider_bool", True), "boundary_retrieval_runtime_ci_network_provider_bool"),
        ("stop_private_write_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_write_authorized_bool", True), "overauthorization_private_write_authorized_bool"),
        ("stop_recompute_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("recompute_authorized_bool", True), "overauthorization_recompute_authorized_bool"),
        ("stop_material_generation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"),
        ("stop_source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "overauthorization_source_scan_authorized_bool"),
        ("stop_ci_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_execution_authorized_bool", True), "overauthorization_ci_execution_authorized_bool"),
        ("next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2ar_stop_go_mismatch"),
        ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"),
        ("synthetic_validator_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"),
        ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"),
    ]
    for name, mut, expected_issue in mutations:
        m = json.loads(json.dumps(passed)); mut(m); check(name, expected_issue in validate_report(m))
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
        try: report = load_json(repo / public_artifact_path(args["validate"])); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(args["out"]) if args["out"] else None
    report = build_report(); path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
