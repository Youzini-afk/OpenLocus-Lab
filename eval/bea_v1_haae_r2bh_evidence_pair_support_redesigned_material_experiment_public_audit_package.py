#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BH redesigned material experiment public audit package.

Public-only audit of the committed R2BG public artifact. R2BH reads no private
roots, recomputes no metrics, generates no material, scans no source/candidate
corpus, and runs no OpenLocus/runtime/retrieval/CI/network/provider path.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BH Evidence-Pair Support Redesigned Material Experiment Public Audit Package"
SLUG = "bea_v1_haae_r2bh_evidence_pair_support_redesigned_material_experiment_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2BG_CHECKPOINT = "ad8de95"
R2BG_STATUS = "haae_r2bg_explicit_local_redesigned_material_experiment_complete_r2bh_public_audit_authorized_artifact_or_weak_signal"
R2BG_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bg_evidence_pair_support_explicit_local_redesigned_material_experiment/bea_v1_haae_r2bg_evidence_pair_support_explicit_local_redesigned_material_experiment_report.json")
R2BG_SELF_TEST_TOTAL = 36
RESULT_BUCKET = "artifact_or_weak_signal"
OUTCOME_ALIGNMENT_BUCKET = "outcome_eval_alignment_unavailable"
R2BG_GATES = ["r2bf_source_lock_gate", "r2be_public_artifact_lock_gate", "default_noop_or_explicit_opt_in_gate", "root_safety_gate", "r2be_private_manifest_group_schema_gate", "control_family_exact_gate", "no_material_generation_gate", "no_source_candidate_corpus_scan_gate", "no_runtime_openlocus_retrieval_gate", "aggregate_bucket_metrics_only_gate", "public_privacy_gate", "r2bh_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2BG_SYNTHETIC_VALIDATORS = ["default_noop_pass", "explicit_synthetic_artifact_or_weak_pass", "safe_parser_fail", "missing_explicit_arg_fail", "r2bf_checkpoint_drift_fail", "r2bf_status_drift_fail", "r2bf_self_test_drift_fail", "r2bf_stop_go_overauth_fail", "r2be_public_status_drift_fail", "root_in_repo_fail", "root_missing_manifest_fail", "root_group_missing_fail", "root_group_symlink_fail", "root_unexpected_group_fail", "manifest_schema_fail", "manifest_source_lock_drift_fail", "control_family_missing_fail", "material_generation_flag_fail", "source_scan_flag_fail", "runtime_flag_fail", "execution_mode_drift_fail", "execution_private_read_drift_fail", "execution_private_write_overauth_fail", "metric_bucketization_fail", "status_metric_alignment_fail", "privacy_raw_publication_fail", "privacy_ids_publication_fail", "public_leak_fail", "stop_go_true_drop_fail", "stop_go_private_overauth_fail", "stop_go_scale_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_readback_fail", "readback_record_fail"]

STATUS_PASS = "haae_r2bh_redesigned_material_experiment_public_audit_complete_r2bi_next_step_decision_authorized_artifact_or_weak_signal"
STATUS_FAIL_SOURCE = "haae_r2bh_fail_closed_r2bg_source_lock_mismatch"
STATUS_FAIL_AUDIT = "haae_r2bh_fail_closed_r2bg_audit_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2bh_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bh_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BI Evidence-Pair Support Public Next-Step Decision Design Package"

GATE_NAMES = [
    "r2bg_source_locked_gate",
    "r2bg_status_artifact_or_weak_gate",
    "r2bg_self_test_36_gate",
    "r2bg_forbidden_scan_pass_gate",
    "outcome_alignment_unavailable_gate",
    "aggregate_bucket_only_gate",
    "privacy_boundary_gate",
    "execution_boundary_gate",
    "gate_set_integrity_gate",
    "synthetic_set_integrity_gate",
    "readback_integrity_gate",
    "r2bi_stop_go_only_gate",
    "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
]

SYNTHETIC_VALIDATORS = [
    "source_lock_pass",
    "r2bg_checkpoint_drift_fail",
    "r2bg_status_drift_fail",
    "r2bg_self_test_drift_fail",
    "r2bg_forbidden_scan_drift_fail",
    "result_bucket_drift_fail",
    "outcome_alignment_drift_fail",
    "aggregate_bucket_only_drift_fail",
    "exact_metrics_public_fail",
    "raw_private_rows_public_fail",
    "ids_public_fail",
    "private_root_public_fail",
    "execution_material_generation_drift_fail",
    "execution_source_scan_drift_fail",
    "execution_runtime_drift_fail",
    "execution_mode_bucket_drift_fail",
    "execution_explicit_opt_in_drift_fail",
    "execution_private_read_drift_fail",
    "stop_go_next_phase_drift_fail",
    "stop_go_private_execution_overauth_fail",
    "stop_go_material_generation_overauth_fail",
    "stop_go_scale_overauth_fail",
    "stop_go_method_claim_overauth_fail",
    "gate_set_fail",
    "duplicate_gate_fail",
    "synthetic_set_fail",
    "duplicate_synthetic_fail",
    "readback_record_fail",
    "duplicate_readback_fail",
    "r2bg_gate_set_drift_fail",
    "r2bg_synthetic_set_drift_fail",
    "r2bg_readback_duplicate_fail",
    "r2bg_readback_missing_fail",
    "public_leak_fail",
    "safe_parser_fail",
]
SELF_TEST_EXPECTED = len(SYNTHETIC_VALIDATORS)

STOP_FALSE_FIELDS = [
    "private_read_authorized_bool",
    "private_write_authorized_bool",
    "execution_authorized_bool",
    "metric_recompute_authorized_bool",
    "material_generation_authorized_bool",
    "source_scan_authorized_bool",
    "candidate_scan_authorized_bool",
    "corpus_scan_authorized_bool",
    "openlocus_runtime_authorized_bool",
    "runtime_execution_authorized_bool",
    "retrieval_authorized_bool",
    "ci_execution_authorized_bool",
    "network_authorized_bool",
    "provider_model_authorized_bool",
    "clone_authorized_bool",
    "scale_preflight_authorized_bool",
    "scale_claim_authorized_bool",
    "method_claim_authorized_bool",
    "default_claim_authorized_bool",
    "winner_claim_authorized_bool",
    "validated_signal_claim_authorized_bool",
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


def audit_r2bg(r2bg: dict[str, Any]) -> dict[str, bool]:
    source = (r2bg.get("source_lock_records") or [{}])[0]
    metric = (r2bg.get("aggregate_metric_records") or [{}])[0]
    execution = (r2bg.get("execution_mode_records") or [{}])[0]
    privacy = (r2bg.get("privacy_boundary_records") or [{}])[0]
    stop = (r2bg.get("stop_go_records") or [{}])[0]
    status_ok = r2bg.get("status") == R2BG_STATUS
    self_test_ok = r2bg.get("self_test_total") == R2BG_SELF_TEST_TOTAL
    scan_ok = r2bg.get("forbidden_scan", {}).get("status") == "pass"
    source_chain_ok = source.get("locked_haae_r2bf_checkpoint") == "322fbca" and source.get("locked_haae_r2be_checkpoint") == "c3901d6" and source.get("source_locked_bool") is True
    result_ok = metric.get("redesigned_experiment_result_bucket") == RESULT_BUCKET
    alignment_ok = metric.get("outcome_eval_alignment_bucket") == OUTCOME_ALIGNMENT_BUCKET
    aggregate_ok = metric.get("aggregate_bucket_metrics_only_bool") is True and metric.get("no_exact_metrics_bool") is True
    privacy_ok = (
        privacy.get("aggregate_bucket_only_publication_bool") is True
        and privacy.get("exact_counts_rates_scores_ranks_mrr_public_bool") is False
        and privacy.get("private_root_path_public_bool") is False
        and privacy.get("raw_private_rows_public_bool") is False
        and privacy.get("task_query_source_evidence_pair_ids_public_bool") is False
    )
    execution_ok = (
        execution.get("execution_mode_bucket") == "explicit_local_experiment"
        and execution.get("explicit_opt_in_bool") is True
        and execution.get("private_read_bool") is True
        and execution.get("private_write_bool") is False
        and
        execution.get("material_generation_bool") is False
        and execution.get("runtime_openlocus_retrieval_bool") is False
        and execution.get("source_candidate_corpus_scan_bool") is False
    )
    stop_ok = stop.get("haae_r2bh_evidence_pair_support_redesigned_material_experiment_public_audit_authorized_bool") is True and stop.get("next_allowed_phase") == PHASE and stop.get("r2bh_public_only_audit_bool") is True and stop.get("r2bh_no_metric_recompute_bool") is True and stop.get("r2bh_no_private_read_bool") is True
    gate_rows = r2bg.get("pass_fail_gate_records", [])
    gate_list = [row.get("gate_bucket") for row in gate_rows]
    gate_ok = set(gate_list) == set(R2BG_GATES) and len(gate_list) == len(R2BG_GATES) and len(gate_list) == len(set(gate_list)) and all(row.get("gate_passed_bool") is True for row in gate_rows)
    synth_rows = r2bg.get("synthetic_validator_records", [])
    synth_list = [row.get("validator_bucket") for row in synth_rows]
    synthetic_ok = set(synth_list) == set(R2BG_SYNTHETIC_VALIDATORS) and len(synth_list) == len(R2BG_SYNTHETIC_VALIDATORS) and len(synth_list) == len(set(synth_list))
    readback_rows = r2bg.get("public_readback_records", [])
    readback_ok = len(readback_rows) == 1 and readback_rows[0].get("all_public_readback_match_bool") is True
    exact_integrity_ok = gate_ok and synthetic_ok and readback_ok
    source_ok = status_ok and self_test_ok and scan_ok and source_chain_ok and result_ok and alignment_ok and aggregate_ok and privacy_ok and execution_ok and stop_ok and exact_integrity_ok
    return {"source_ok": bool(source_ok), "status_ok": bool(status_ok), "self_test_ok": bool(self_test_ok), "scan_ok": bool(scan_ok), "source_chain_ok": bool(source_chain_ok), "result_ok": bool(result_ok), "alignment_ok": bool(alignment_ok), "aggregate_ok": bool(aggregate_ok), "privacy_ok": bool(privacy_ok), "execution_ok": bool(execution_ok), "stop_ok": bool(stop_ok), "gate_ok": bool(gate_ok), "synthetic_ok": bool(synthetic_ok), "readback_ok": bool(readback_ok), "exact_integrity_ok": bool(exact_integrity_ok)}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BG_CHECKPOINT, R2BG_STATUS, "R2BG self-test 36/36", RESULT_BUCKET, OUTCOME_ALIGNMENT_BUCKET, "support rows/control rows exist", "no evaluable outcome alignment", "no signal claim", "R2BG gate/synthetic/readback exact integrity", "R2BG explicit_local_experiment execution integrity", "public-only audit/package", "read only R2BG public artifact", "no private roots", "no metric recompute", "no material generation", "no source/candidate/corpus scan", "aggregate-only", NEXT_PHASE]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2bh-evidence-pair-support-redesigned-material-experiment-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2bh-evidence-pair-support-redesigned-material-experiment-public-audit-package.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2bh-evidence-pair-support-redesigned-material-experiment-public-audit-package.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2bg: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2bg is None:
        try: r2bg = load_json(repo / R2BG_REPORT_PATH)
        except Exception: r2bg = {}
    audit = audit_r2bg(r2bg)
    readback = public_readback_match(self_test_total)
    if not (audit["status_ok"] and audit["self_test_ok"] and audit["scan_ok"] and audit["source_chain_ok"]): status = STATUS_FAIL_SOURCE
    elif not (audit["result_ok"] and audit["alignment_ok"] and audit["aggregate_ok"] and audit["privacy_ok"] and audit["execution_ok"] and audit["stop_ok"] and audit["exact_integrity_ok"]): status = STATUS_FAIL_AUDIT
    elif not readback["all_public_readback_match_bool"]: status = STATUS_FAIL_READBACK
    else: status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2bg_source_locked_gate": audit["status_ok"] and audit["self_test_ok"], "r2bg_status_artifact_or_weak_gate": audit["result_ok"], "r2bg_self_test_36_gate": audit["self_test_ok"], "r2bg_forbidden_scan_pass_gate": audit["scan_ok"], "outcome_alignment_unavailable_gate": audit["alignment_ok"], "aggregate_bucket_only_gate": audit["aggregate_ok"], "privacy_boundary_gate": audit["privacy_ok"], "execution_boundary_gate": audit["execution_ok"], "gate_set_integrity_gate": audit["gate_ok"], "synthetic_set_integrity_gate": audit["synthetic_ok"], "readback_integrity_gate": audit["readback_ok"], "r2bi_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    stop = {"anonymous_stop_go_id": "haaer2bhstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_public_audit_pass", "haae_r2bi_public_next_step_decision_design_authorized_bool": passed, "r2bi_public_decision_design_only_bool": passed}
    stop.update({field: False for field in STOP_FALSE_FIELDS})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bhsource0000", "locked_haae_r2bg_checkpoint": R2BG_CHECKPOINT, "locked_haae_r2bg_status": R2BG_STATUS, "r2bg_status_match_bool": audit["status_ok"], "r2bg_self_test_36_bool": audit["self_test_ok"], "r2bg_forbidden_scan_pass_bool": audit["scan_ok"], "r2bg_public_source_chain_match_bool": audit["source_chain_ok"], "source_locked_bool": audit["status_ok"] and audit["self_test_ok"] and audit["scan_ok"] and audit["source_chain_ok"]}],
        "weak_signal_audit_records": [{"anonymous_weak_signal_audit_id": "haaer2bhaudit0000", "redesigned_experiment_result_bucket": RESULT_BUCKET, "outcome_eval_alignment_bucket": OUTCOME_ALIGNMENT_BUCKET, "support_rows_control_rows_exist_bool": True, "no_evaluable_outcome_alignment_bool": True, "no_signal_claim_bool": True, "artifact_or_weak_signal_public_decision_bool": True}],
        "r2bg_boundary_audit_records": [{"anonymous_r2bg_boundary_audit_id": "haaer2bhboundaryaudit0000", "aggregate_bucket_metrics_only_bool": audit["aggregate_ok"], "privacy_boundary_match_bool": audit["privacy_ok"], "execution_boundary_match_bool": audit["execution_ok"], "gate_integrity_match_bool": audit["gate_ok"], "synthetic_integrity_match_bool": audit["synthetic_ok"], "readback_integrity_match_bool": audit["readback_ok"], "gate_synthetic_readback_exact_integrity_bool": audit["exact_integrity_ok"]}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2bhboundary0000", "public_only_audit_package_bool": True, "private_root_read_bool": False, "metric_recompute_bool": False, "material_generation_bool": False, "source_candidate_corpus_scan_bool": False, "openlocus_runtime_retrieval_ci_network_provider_bool": False, "raw_private_row_path_task_query_source_evidence_pair_id_publication_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2bhclaim0000", "signal_claim_bool": False, "method_default_winner_scale_claim_bool": False, "exact_metric_publication_bool": False, "new_private_execution_authorized_bool": False, "material_generation_authorized_bool": False, "scale_ci_method_default_authorized_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bhgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bhsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bhreadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "weak_signal_audit_records", "r2bg_boundary_audit_records", "boundary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTHETIC_VALIDATORS): issues.append("self_test_validator_count_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    gate_list = [row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])]
    if set(gate_list) != set(GATE_NAMES) or len(gate_list) != len(GATE_NAMES): issues.append("gate_set_mismatch")
    validator_list = [row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])]
    if set(validator_list) != set(SYNTHETIC_VALIDATORS) or len(validator_list) != len(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2bg_checkpoint") != R2BG_CHECKPOINT or src.get("locked_haae_r2bg_status") != R2BG_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2bg_status_match_bool", "r2bg_self_test_36_bool", "r2bg_forbidden_scan_pass_bool", "r2bg_public_source_chain_match_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_{field}")
    weak = (report.get("weak_signal_audit_records") or [{}])[0]
    for field, expected in {"redesigned_experiment_result_bucket": RESULT_BUCKET, "outcome_eval_alignment_bucket": OUTCOME_ALIGNMENT_BUCKET}.items():
        if weak.get(field) != expected: issues.append(f"weak_{field}")
    for field in ["support_rows_control_rows_exist_bool", "no_evaluable_outcome_alignment_bool", "no_signal_claim_bool", "artifact_or_weak_signal_public_decision_bool"]:
        if weak.get(field) is not True: issues.append(f"weak_{field}")
    audit = (report.get("r2bg_boundary_audit_records") or [{}])[0]
    for field in ["aggregate_bucket_metrics_only_bool", "privacy_boundary_match_bool", "execution_boundary_match_bool", "gate_integrity_match_bool", "synthetic_integrity_match_bool", "readback_integrity_match_bool", "gate_synthetic_readback_exact_integrity_bool"]:
        if audit.get(field) is not True: issues.append(f"r2bg_audit_{field}")
    boundary = (report.get("boundary_records") or [{}])[0]
    if boundary.get("public_only_audit_package_bool") is not True: issues.append("boundary_public_only_audit_package_bool")
    for field in ["private_root_read_bool", "metric_recompute_bool", "material_generation_bool", "source_candidate_corpus_scan_bool", "openlocus_runtime_retrieval_ci_network_provider_bool", "raw_private_row_path_task_query_source_evidence_pair_id_publication_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["signal_claim_bool", "method_default_winner_scale_claim_bool", "exact_metric_publication_bool", "new_private_execution_authorized_bool", "material_generation_authorized_bool", "scale_ci_method_default_authorized_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE or stop.get("haae_r2bi_public_next_step_decision_design_authorized_bool") is not True or stop.get("r2bi_public_decision_design_only_bool") is not True: issues.append("r2bi_stop_go_mismatch")
    for field in STOP_FALSE_FIELDS:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
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
    base = load_json(repo / R2BG_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    source_mutations = [("r2bg_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bf_checkpoint", "wrong")), ("r2bg_status_drift_fail", lambda r: r.__setitem__("status", "wrong")), ("r2bg_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0)), ("r2bg_forbidden_scan_drift_fail", lambda r: r["forbidden_scan"].__setitem__("status", "fail")), ("result_bucket_drift_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("redesigned_experiment_result_bucket", "signal_present")), ("outcome_alignment_drift_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("outcome_eval_alignment_bucket", "available")), ("execution_mode_bucket_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("execution_mode_bucket", "default_no_explicit_opt_in")), ("execution_explicit_opt_in_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("explicit_opt_in_bool", False)), ("execution_private_read_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_read_bool", False)), ("r2bg_gate_set_drift_fail", lambda r: r["pass_fail_gate_records"].pop()), ("r2bg_synthetic_set_drift_fail", lambda r: r["synthetic_validator_records"].pop()), ("r2bg_readback_duplicate_fail", lambda r: r["public_readback_records"].append(r["public_readback_records"][0])), ("r2bg_readback_missing_fail", lambda r: r.__setitem__("public_readback_records", []))]
    for name, mut in source_mutations:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] in {STATUS_FAIL_SOURCE, STATUS_FAIL_AUDIT})
    mutations = [("aggregate_bucket_only_drift_fail", lambda r: r["r2bg_boundary_audit_records"][0].__setitem__("aggregate_bucket_metrics_only_bool", False), "r2bg_audit_aggregate_bucket_metrics_only_bool"), ("exact_metrics_public_fail", lambda r: r["claim_boundary_records"][0].__setitem__("exact_metric_publication_bool", True), "claim_exact_metric_publication_bool"), ("raw_private_rows_public_fail", lambda r: r["boundary_records"][0].__setitem__("raw_private_row_path_task_query_source_evidence_pair_id_publication_bool", True), "boundary_raw_private_row_path_task_query_source_evidence_pair_id_publication_bool"), ("ids_public_fail", lambda r: r["claim_boundary_records"][0].__setitem__("raw_publication_bool", True), "claim_raw_publication_bool"), ("private_root_public_fail", lambda r: r["boundary_records"][0].__setitem__("private_root_read_bool", True), "boundary_private_root_read_bool"), ("execution_material_generation_drift_fail", lambda r: r["boundary_records"][0].__setitem__("material_generation_bool", True), "boundary_material_generation_bool"), ("execution_source_scan_drift_fail", lambda r: r["boundary_records"][0].__setitem__("source_candidate_corpus_scan_bool", True), "boundary_source_candidate_corpus_scan_bool"), ("execution_runtime_drift_fail", lambda r: r["boundary_records"][0].__setitem__("openlocus_runtime_retrieval_ci_network_provider_bool", True), "boundary_openlocus_runtime_retrieval_ci_network_provider_bool"), ("stop_go_next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "r2bi_stop_go_mismatch"), ("stop_go_private_execution_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("stop_go_material_generation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"), ("stop_go_scale_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_preflight_authorized_bool", True), "overauthorization_scale_preflight_authorized_bool"), ("stop_go_method_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("method_claim_authorized_bool", True), "overauthorization_method_claim_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(r["pass_fail_gate_records"][0]), "gate_set_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(r["synthetic_validator_records"][0]), "synthetic_validator_set_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(r["public_readback_records"][0]), "public_readback_record_mismatch"), ("public_leak_fail", lambda r: r.__setitem__("debug", "/tmp/private-root task_id exact_count_value"), "forbidden_scan_failed")]
    for name, mut, expected in mutations:
        m = json.loads(json.dumps(passed)); mut(m); check(name, expected in validate_report(m))
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
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
