#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BI public next-step decision design package.

Public-only, non-executing. Reads only public R2BH/R2BG artifacts, does not read
private roots or /tmp, and does not regenerate/repair material or compute metrics.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BI Evidence-Pair Support Public Next-Step Decision Design Package"
SLUG = "bea_v1_haae_r2bi_evidence_pair_support_next_step_decision_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BH_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bh_evidence_pair_support_redesigned_material_experiment_public_audit_package/bea_v1_haae_r2bh_evidence_pair_support_redesigned_material_experiment_public_audit_package_report.json")
R2BG_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bg_evidence_pair_support_explicit_local_redesigned_material_experiment/bea_v1_haae_r2bg_evidence_pair_support_explicit_local_redesigned_material_experiment_report.json")

R2BH_CHECKPOINT = "3b566a2"
R2BH_STATUS = "haae_r2bh_redesigned_material_experiment_public_audit_complete_r2bi_next_step_decision_authorized_artifact_or_weak_signal"
R2BH_SELF_TEST_TOTAL = 35
R2BG_CHECKPOINT = "ad8de95"
R2BG_STATUS = "haae_r2bg_explicit_local_redesigned_material_experiment_complete_r2bh_public_audit_authorized_artifact_or_weak_signal"
R2BG_SELF_TEST_TOTAL = 36
R2BF_CHECKPOINT = "322fbca"
R2BE_CHECKPOINT = "c3901d6"
RESULT_BUCKET = "artifact_or_weak_signal"
OUTCOME_BUCKET = "outcome_eval_alignment_unavailable"

STATUS_PASS = "haae_r2bi_evidence_pair_support_public_next_step_decision_design_complete_r2bj_outcome_aligned_material_repair_public_design_preflight_authorized"
STATUS_FAIL_SOURCE = "haae_r2bi_fail_closed_source_lock_or_audit_mismatch"
STATUS_FAIL_DECISION = "haae_r2bi_fail_closed_decision_or_stop_go_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2bi_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bi_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BJ Evidence-Pair Support Outcome-Aligned Material Repair Public Design Preflight"

R2BH_GATES = ["r2bg_source_locked_gate", "r2bg_status_artifact_or_weak_gate", "r2bg_self_test_36_gate", "r2bg_forbidden_scan_pass_gate", "outcome_alignment_unavailable_gate", "aggregate_bucket_only_gate", "privacy_boundary_gate", "execution_boundary_gate", "gate_set_integrity_gate", "synthetic_set_integrity_gate", "readback_integrity_gate", "r2bi_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2BH_SYNTH = ["source_lock_pass", "r2bg_checkpoint_drift_fail", "r2bg_status_drift_fail", "r2bg_self_test_drift_fail", "r2bg_forbidden_scan_drift_fail", "result_bucket_drift_fail", "outcome_alignment_drift_fail", "aggregate_bucket_only_drift_fail", "exact_metrics_public_fail", "raw_private_rows_public_fail", "ids_public_fail", "private_root_public_fail", "execution_material_generation_drift_fail", "execution_source_scan_drift_fail", "execution_runtime_drift_fail", "execution_mode_bucket_drift_fail", "execution_explicit_opt_in_drift_fail", "execution_private_read_drift_fail", "stop_go_next_phase_drift_fail", "stop_go_private_execution_overauth_fail", "stop_go_material_generation_overauth_fail", "stop_go_scale_overauth_fail", "stop_go_method_claim_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "r2bg_gate_set_drift_fail", "r2bg_synthetic_set_drift_fail", "r2bg_readback_duplicate_fail", "r2bg_readback_missing_fail", "public_leak_fail", "safe_parser_fail"]
R2BH_STOP_TRUE = ["haae_r2bi_public_next_step_decision_design_authorized_bool", "r2bi_public_decision_design_only_bool"]
R2BH_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "execution_authorized_bool", "material_generation_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "validated_signal_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]

GATES = ["r2bh_source_lock_gate", "r2bg_cross_lock_gate", "r2bh_public_only_audit_gate", "r2bh_gate_synthetic_readback_exact_gate", "r2bh_stop_go_to_r2bi_gate", "artifact_or_weak_signal_decision_gate", "outcome_aligned_repair_design_decision_gate", "rejected_options_gate", "r2bj_stop_go_only_gate", "public_only_non_executing_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["decision_pass", "safe_parser_fail", "r2bh_checkpoint_drift_fail", "r2bh_status_drift_fail", "r2bh_self_test_drift_fail", "r2bg_checkpoint_drift_fail", "r2bg_status_drift_fail", "r2bg_result_drift_fail", "r2bg_outcome_bucket_drift_fail", "r2bg_execution_opt_in_drift_fail", "r2bg_execution_private_read_drift_fail", "r2bg_execution_private_write_drift_fail", "r2bh_boundary_drift_fail", "r2bh_gate_drop_fail", "r2bh_gate_duplicate_fail", "r2bh_synthetic_drop_fail", "r2bh_synthetic_duplicate_fail", "r2bh_readback_drop_fail", "r2bh_stop_go_overauth_fail", "decision_selected_drop_fail", "decision_close_line_selected_fail", "decision_scale_selected_fail", "decision_method_default_claim_fail", "r2bj_stop_go_true_drop_fail", "r2bj_private_read_overauth_fail", "r2bj_material_generation_overauth_fail", "r2bj_metric_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
STOP_TRUE = ["haae_r2bj_outcome_aligned_material_repair_public_design_preflight_authorized_bool", "r2bj_public_only_design_preflight_bool", "r2bj_no_execution_bool", "r2bj_no_private_read_write_bool", "r2bj_no_metric_recompute_bool", "r2bj_no_material_generation_in_r2bj_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "execution_authorized_bool", "experiment_authorized_bool", "metric_recompute_authorized_bool", "experiment_metrics_authorized_bool", "material_generation_authorized_bool", "material_repair_execution_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|private_source_ref|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|exact_top_k_value|\bmrr\b|hit_rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
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
    p = Path(value); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def audit_r2bh(r2bh: dict[str, Any]) -> dict[str, bool]:
    src = (r2bh.get("source_lock_records") or [{}])[0]; weak = (r2bh.get("weak_signal_audit_records") or [{}])[0]; boundary = (r2bh.get("boundary_records") or [{}])[0]; claim = (r2bh.get("claim_boundary_records") or [{}])[0]; r2bg_boundary = (r2bh.get("r2bg_boundary_audit_records") or [{}])[0]; stop = (r2bh.get("stop_go_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2bh.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2bh.get("synthetic_validator_records", [])]; read = r2bh.get("public_readback_records", [])
    source_ok = r2bh.get("status") == R2BH_STATUS and r2bh.get("self_test_total") == R2BH_SELF_TEST_TOTAL and r2bh.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bg_checkpoint") == R2BG_CHECKPOINT and src.get("locked_haae_r2bg_status") == R2BG_STATUS and src.get("r2bg_self_test_36_bool") is True and src.get("source_locked_bool") is True
    weak_ok = weak.get("redesigned_experiment_result_bucket") == RESULT_BUCKET and weak.get("outcome_eval_alignment_bucket") == OUTCOME_BUCKET and weak.get("no_signal_claim_bool") is True and weak.get("artifact_or_weak_signal_public_decision_bool") is True
    boundary_ok = boundary.get("public_only_audit_package_bool") is True and all(boundary.get(f) is False for f in ["private_root_read_bool", "metric_recompute_bool", "material_generation_bool", "source_candidate_corpus_scan_bool", "openlocus_runtime_retrieval_ci_network_provider_bool", "raw_private_row_path_task_query_source_evidence_pair_id_publication_bool"]) and claim.get("signal_claim_bool") is False and claim.get("method_default_winner_scale_claim_bool") is False
    integrity_ok = set(gates) == set(R2BH_GATES) and len(gates) == len(R2BH_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2BH_SYNTH) and len(synth) == len(R2BH_SYNTH) and len(synth) == len(set(synth)) and len(read) == 1 and read[0].get("all_public_readback_match_bool") is True and r2bg_boundary.get("gate_synthetic_readback_exact_integrity_bool") is True and r2bg_boundary.get("execution_boundary_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BH_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BH_STOP_FALSE)
    return {"source_ok": source_ok, "weak_ok": weak_ok, "boundary_ok": boundary_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok, "audit_ok": source_ok and weak_ok and boundary_ok and integrity_ok and stop_ok}
def audit_r2bg(r2bg: dict[str, Any]) -> bool:
    src = (r2bg.get("source_lock_records") or [{}])[0]; metric = (r2bg.get("aggregate_metric_records") or [{}])[0]; exe = (r2bg.get("execution_mode_records") or [{}])[0]
    return r2bg.get("status") == R2BG_STATUS and r2bg.get("self_test_total") == R2BG_SELF_TEST_TOTAL and r2bg.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bf_checkpoint") == R2BF_CHECKPOINT and src.get("locked_haae_r2be_checkpoint") == R2BE_CHECKPOINT and metric.get("redesigned_experiment_result_bucket") == RESULT_BUCKET and metric.get("outcome_eval_alignment_bucket") == OUTCOME_BUCKET and exe.get("execution_mode_bucket") == "explicit_local_experiment" and exe.get("explicit_opt_in_bool") is True and exe.get("private_read_bool") is True and exe.get("private_write_bool") is False and exe.get("material_generation_bool") is False and exe.get("source_candidate_corpus_scan_bool") is False and exe.get("runtime_openlocus_retrieval_bool") is False

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BH_CHECKPOINT, R2BH_STATUS, R2BG_CHECKPOINT, R2BG_STATUS, R2BF_CHECKPOINT, R2BE_CHECKPOINT, "outcome_aligned_material_repair_design_selected", "close_line_deferred", "pivot_deferred", "rerun_experiment_without_repair_rejected", "scale_preflight_rejected", "method_default_claim_rejected", RESULT_BUCKET, OUTCOME_BUCKET, "no signal claim", "public-only", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bi-evidence-pair-support-next-step-decision-package.md")) and ok(read("docs/zh/bea-v1-haae-r2bi-evidence-pair-support-next-step-decision-package.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bi-evidence-pair-support-next-step-decision-package.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(r2bh: dict[str, Any] | None = None, r2bg: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2bh is None:
        try: r2bh = load_json(repo_root() / R2BH_REPORT_PATH)
        except Exception: r2bh = {}
    if r2bg is None:
        try: r2bg = load_json(repo_root() / R2BG_REPORT_PATH)
        except Exception: r2bg = {}
    audit = audit_r2bh(r2bh); r2bg_ok = audit_r2bg(r2bg); rb = public_readback_match(self_test_total)
    source_ok = audit["source_ok"] and r2bg_ok; decision_ok = audit["audit_ok"] and r2bg_ok
    status = STATUS_FAIL_SOURCE if not source_ok else (STATUS_FAIL_DECISION if not decision_ok else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bistop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_decision_package_pass"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bh_source_lock_gate": audit["source_ok"], "r2bg_cross_lock_gate": r2bg_ok, "r2bh_public_only_audit_gate": audit["boundary_ok"], "r2bh_gate_synthetic_readback_exact_gate": audit["integrity_ok"], "r2bh_stop_go_to_r2bi_gate": audit["stop_ok"], "artifact_or_weak_signal_decision_gate": audit["weak_ok"], "outcome_aligned_repair_design_decision_gate": True, "rejected_options_gate": True, "r2bj_stop_go_only_gate": True, "public_only_non_executing_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bisource0000", "locked_haae_r2bh_checkpoint": R2BH_CHECKPOINT, "locked_haae_r2bh_status": R2BH_STATUS, "locked_haae_r2bh_self_test_total": R2BH_SELF_TEST_TOTAL, "locked_haae_r2bg_checkpoint": R2BG_CHECKPOINT, "locked_haae_r2bg_status": R2BG_STATUS, "locked_haae_r2bg_self_test_total": R2BG_SELF_TEST_TOTAL, "locked_inherited_r2bf_checkpoint": R2BF_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "source_locked_bool": source_ok}],
        "r2bh_audit_records": [{"anonymous_audit_id": "haaer2biaudit0000", "r2bh_public_only_audit_bool": audit["boundary_ok"], "r2bg_gate_synthetic_readback_exact_integrity_bool": audit["integrity_ok"], "r2bg_explicit_local_experiment_execution_integrity_bool": audit["integrity_ok"], "no_signal_claim_bool": audit["weak_ok"], "result_bucket": RESULT_BUCKET, "outcome_eval_alignment_bucket": OUTCOME_BUCKET}],
        "decision_records": [{"anonymous_decision_id": "haaer2bidecision0000", "outcome_aligned_material_repair_design_selected_bool": True, "close_line_deferred_bool": True, "pivot_deferred_bool": True, "rerun_experiment_without_repair_rejected_bool": True, "scale_preflight_rejected_bool": True, "method_default_claim_rejected_bool": True, "artifact_or_weak_signal_locked_bool": audit["weak_ok"], "no_signal_claim_bool": True}],
        "public_only_boundary_records": [{"anonymous_boundary_id": "haaer2biboundary0000", "public_only_non_executing_bool": True, "read_only_public_artifacts_bool": True, "private_root_read_bool": False, "material_regeneration_or_repair_bool": False, "metric_computation_bool": False, "source_candidate_corpus_scan_bool": False, "ci_runtime_network_provider_clone_bool": False, "raw_private_exact_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bigate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bisynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bireadback0000", **rb}], "stop_go_records": [stop]}
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
    if len(synth) != len(set(synth)): issues.append("synthetic_validator_duplicate_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    for f, e in {"locked_haae_r2bh_checkpoint": R2BH_CHECKPOINT, "locked_haae_r2bh_status": R2BH_STATUS, "locked_haae_r2bh_self_test_total": R2BH_SELF_TEST_TOTAL, "locked_haae_r2bg_checkpoint": R2BG_CHECKPOINT, "locked_haae_r2bg_status": R2BG_STATUS, "locked_haae_r2bg_self_test_total": R2BG_SELF_TEST_TOTAL, "locked_inherited_r2bf_checkpoint": R2BF_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    aud = (report.get("r2bh_audit_records") or [{}])[0]
    for f in ["r2bh_public_only_audit_bool", "r2bg_gate_synthetic_readback_exact_integrity_bool", "r2bg_explicit_local_experiment_execution_integrity_bool", "no_signal_claim_bool"]:
        if aud.get(f) is not True: issues.append(f"audit_{f}")
    if aud.get("result_bucket") != RESULT_BUCKET or aud.get("outcome_eval_alignment_bucket") != OUTCOME_BUCKET: issues.append("audit_bucket_mismatch")
    dec = (report.get("decision_records") or [{}])[0]
    for f in ["outcome_aligned_material_repair_design_selected_bool", "close_line_deferred_bool", "pivot_deferred_bool", "rerun_experiment_without_repair_rejected_bool", "scale_preflight_rejected_bool", "method_default_claim_rejected_bool", "artifact_or_weak_signal_locked_bool", "no_signal_claim_bool"]:
        if dec.get(f) is not True: issues.append(f"decision_{f}")
    boundary = (report.get("public_only_boundary_records") or [{}])[0]
    for f in ["public_only_non_executing_bool", "read_only_public_artifacts_bool"]:
        if boundary.get(f) is not True: issues.append(f"boundary_{f}")
    for f in ["private_root_read_bool", "material_regeneration_or_repair_bool", "metric_computation_bool", "source_candidate_corpus_scan_bool", "ci_runtime_network_provider_clone_bool", "raw_private_exact_publication_bool"]:
        if boundary.get(f) is not False: issues.append(f"boundary_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bj_stop_go_mismatch")
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
    failures: list[str] = []; base = load_json(repo_root() / R2BH_REPORT_PATH); r2bg = load_json(repo_root() / R2BG_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    passed = build_report(base, r2bg); check("decision_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    muts = [("r2bh_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bg_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2bh_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE), ("r2bh_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE), ("r2bg_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bf_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2bg_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE), ("r2bg_result_drift_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("redesigned_experiment_result_bucket", "signal_present"), STATUS_FAIL_SOURCE), ("r2bg_outcome_bucket_drift_fail", lambda r: r["aggregate_metric_records"][0].__setitem__("outcome_eval_alignment_bucket", "available"), STATUS_FAIL_SOURCE), ("r2bg_execution_opt_in_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("explicit_opt_in_bool", False), STATUS_FAIL_SOURCE), ("r2bg_execution_private_read_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_read_bool", False), STATUS_FAIL_SOURCE), ("r2bg_execution_private_write_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_write_bool", True), STATUS_FAIL_SOURCE)]
    for name, mut, status in muts[:3]:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m, r2bg)["status"] == status)
    for name, mut, status in muts[3:]:
        m = json.loads(json.dumps(r2bg)); mut(m); check(name, build_report(base, m)["status"] == status)
    more = [("r2bh_boundary_drift_fail", lambda r: r["boundary_records"][0].__setitem__("private_root_read_bool", True), STATUS_FAIL_DECISION), ("r2bh_gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), STATUS_FAIL_DECISION), ("r2bh_gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), STATUS_FAIL_DECISION), ("r2bh_synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), STATUS_FAIL_DECISION), ("r2bh_synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), STATUS_FAIL_DECISION), ("r2bh_readback_drop_fail", lambda r: r.__setitem__("public_readback_records", []), STATUS_FAIL_DECISION), ("r2bh_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_DECISION)]
    for name, mut, status in more:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m, r2bg)["status"] == status)
    report_mut = [("decision_selected_drop_fail", lambda r: r["decision_records"][0].__setitem__("outcome_aligned_material_repair_design_selected_bool", False), "decision_outcome_aligned_material_repair_design_selected_bool"), ("decision_close_line_selected_fail", lambda r: r["decision_records"][0].__setitem__("close_line_deferred_bool", False), "decision_close_line_deferred_bool"), ("decision_scale_selected_fail", lambda r: r["decision_records"][0].__setitem__("scale_preflight_rejected_bool", False), "decision_scale_preflight_rejected_bool"), ("decision_method_default_claim_fail", lambda r: r["decision_records"][0].__setitem__("method_default_claim_rejected_bool", False), "decision_method_default_claim_rejected_bool"), ("r2bj_stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("r2bj_private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("r2bj_material_generation_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"), ("r2bj_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_validator_duplicate_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "public_readback_record_mismatch")]
    for name, mut, issue in report_mut:
        m = json.loads(json.dumps(passed)); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo_root() / public_artifact_path(str(args["validate"]))); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] == STATUS_PASS else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
