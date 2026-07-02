#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BL outcome-aligned material public audit package.

Public-only audit of the R2BK public artifact. It audits the controlled
unavailable result: outcome-alignment source labels were absent, so no R2BK
material was generated. It does not read private roots/material, compute
metrics, generate material, scan sources, or expose raw/private/exact values.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BL Evidence-Pair Support Outcome-Aligned Material Public Audit Package"
SLUG = "bea_v1_haae_r2bl_evidence_pair_support_outcome_aligned_material_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BK_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bk_evidence_pair_support_explicit_local_outcome_aligned_material_repair_generation/bea_v1_haae_r2bk_evidence_pair_support_explicit_local_outcome_aligned_material_repair_generation_report.json")

R2BK_CHECKPOINT = "7073b12"
R2BK_STATUS = "haae_r2bk_unavailable_outcome_alignment_source_labels_absent_no_material_generated"
R2BK_SELF_TEST_TOTAL = 43
R2BJ_CHECKPOINT = "cab3b84"
R2BI_CHECKPOINT = "f231205"
R2BH_CHECKPOINT = "3b566a2"
R2BG_CHECKPOINT = "ad8de95"
R2BF_CHECKPOINT = "322fbca"
R2BE_CHECKPOINT = "c3901d6"
R2BG_RESULT_BUCKET = "artifact_or_weak_signal"
R2BG_OUTCOME_BUCKET = "outcome_eval_alignment_unavailable"
GENERATION_BUCKET = "outcome_alignment_unavailable_no_material_generated"

STATUS_PASS = "haae_r2bl_outcome_aligned_material_public_audit_complete_r2bm_decision_design_authorized_unavailable_no_material_generated"
STATUS_FAIL_SOURCE = "haae_r2bl_fail_closed_r2bk_source_or_status_mismatch"
STATUS_FAIL_UNAVAILABLE = "haae_r2bl_fail_closed_unavailable_result_integrity_mismatch"
STATUS_FAIL_STOP_GO = "haae_r2bl_fail_closed_stop_go_overauthorization"
STATUS_FAIL_PRIVACY = "haae_r2bl_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bl_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BM Evidence-Pair Support Outcome Label Acquisition Public Decision Design Package"

R2BK_GATES = ["r2bj_source_lock_gate", "default_noop_or_explicit_opt_in_gate", "explicit_flags_gate", "r2be_input_root_safety_gate", "r2bk_output_root_safety_gate", "r2be_input_group_exact_gate", "r2bk_output_group_exact_gate", "gold_eval_alignment_only_gate", "no_experiment_metrics_gate", "no_source_scan_gate", "aggregate_only_public_gate", "r2bl_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2BK_SYNTH = ["default_noop_pass", "explicit_synthetic_generation_pass", "outcome_alignment_unavailable_fail_closed", "unavailable_stop_go_true_drop_fail", "unavailable_material_generated_overauth_fail", "unavailable_generated_content_audit_overauth_fail", "unavailable_generated_group_exact_overauth_fail", "unavailable_generated_group_material_overauth_fail", "safe_parser_fail", "missing_explicit_flag_fail", "missing_input_root_fail", "missing_output_root_fail", "bad_r2bj_checkpoint_fail", "bad_r2bj_status_fail", "bad_r2bj_self_test_fail", "bad_r2bj_stop_go_overauth_fail", "bad_r2bj_schema_drop_fail", "input_root_in_repo_fail", "input_root_missing_fail", "input_group_missing_fail", "input_group_extra_fail", "input_group_symlink_fail", "output_root_in_repo_fail", "nested_roots_fail", "output_root_symlink_fail", "nonempty_unowned_output_fail", "owned_rerun_pass", "output_group_symlink_escape_fail", "generated_group_missing_fail", "generated_group_extra_fail", "gold_policy_drift_fail", "metric_policy_drift_fail", "source_scan_policy_drift_fail", "public_leak_fail", "stop_go_true_drop_fail", "stop_go_private_overauth_fail", "stop_go_metric_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_drop_fail", "readback_duplicate_fail"]
GATES = ["r2bk_source_lock_gate", "r2bk_unavailable_status_gate", "r2bk_no_material_generated_gate", "r2bk_no_metric_gate", "r2bk_no_source_scan_gate", "r2bk_gate_synthetic_readback_exact_gate", "r2bk_stop_go_to_r2bl_only_gate", "public_only_audit_gate", "aggregate_publication_gate", "r2bm_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["audit_pass", "safe_parser_fail", "r2bk_checkpoint_drift_fail", "r2bk_status_drift_fail", "r2bk_self_test_drift_fail", "r2bj_lock_drift_fail", "r2bg_result_drift_fail", "r2bg_outcome_drift_fail", "unavailable_fact_drift_fail", "generation_bucket_drift_fail", "generated_group_overclaim_fail", "material_generated_overclaim_fail", "metric_overauth_fail", "source_scan_overauth_fail", "r2bk_execution_signal_interpretation_fail", "r2bk_no_metric_signal_interpretation_fail", "r2bk_private_rows_public_fail", "r2bk_private_ids_public_fail", "r2bk_input_implicit_root_fail", "r2bk_input_public_root_fail", "r2bk_gate_drop_fail", "r2bk_gate_duplicate_fail", "r2bk_synthetic_drop_fail", "r2bk_synthetic_duplicate_fail", "r2bk_readback_drop_fail", "r2bk_stop_go_true_drop_fail", "r2bk_no_source_scan_true_drop_fail", "r2bk_stop_go_overauth_fail", "r2bk_experiment_overauth_fail", "r2bm_stop_go_true_drop_fail", "r2bm_private_overauth_fail", "r2bm_material_overauth_fail", "r2bm_metric_overauth_fail", "r2bm_claim_overauth_fail", "publication_aggregate_drop_fail", "publication_private_root_overauth_fail", "publication_exact_metric_overauth_fail", "audit_r2bg_result_drift_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)

R2BK_STOP_TRUE = ["haae_r2bl_outcome_aligned_material_public_audit_authorized_bool", "r2bl_public_only_audit_bool", "r2bl_no_private_read_bool", "r2bl_no_metric_computation_bool", "r2bl_no_material_generation_bool", "r2bl_no_source_scan_bool", "r2bl_audit_controlled_unavailable_result_bool"]
R2BK_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "material_repair_authorized_bool", "material_repair_execution_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool", "material_generated_bool", "r2bl_generated_material_content_audit_bool"]
STOP_TRUE = ["haae_r2bm_outcome_label_acquisition_public_decision_design_authorized_bool", "r2bm_public_only_decision_design_bool", "r2bm_no_execution_bool", "r2bm_no_private_read_write_bool", "r2bm_no_material_generation_bool", "r2bm_no_metric_recompute_bool", "controlled_unavailable_result_locked_bool", "outcome_alignment_source_labels_absent_locked_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "execution_authorized_bool", "experiment_authorized_bool", "metric_recompute_authorized_bool", "experiment_metrics_authorized_bool", "material_generation_authorized_bool", "material_repair_execution_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|private_source_ref|source_ref|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|\bmrr\b|hit[_-]?rate|\brank\b|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

def repo_root() -> Path: return Path(__file__).resolve().parents[1]
def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8"))
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
    p = Path(value); resolved = p if p.is_absolute() else repo_root() / p
    if resolved != repo_root() / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def audit_r2bk(r2bk: dict[str, Any]) -> dict[str, bool]:
    src = (r2bk.get("source_lock_records") or [{}])[0]; gen = (r2bk.get("generated_group_records") or [{}])[0]; exec_rec = (r2bk.get("execution_mode_records") or [{}])[0]; no_metric = (r2bk.get("no_metric_records") or [{}])[0]; stop = (r2bk.get("stop_go_records") or [{}])[0]; pub = (r2bk.get("publication_records") or [{}])[0]; input_root = (r2bk.get("input_root_safety_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2bk.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2bk.get("synthetic_validator_records", [])]; read = r2bk.get("public_readback_records", [])
    source_ok = r2bk.get("status") == R2BK_STATUS and r2bk.get("self_test_total") == R2BK_SELF_TEST_TOTAL and r2bk.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bj_checkpoint") == R2BJ_CHECKPOINT and src.get("locked_inherited_r2bi_checkpoint") == R2BI_CHECKPOINT and src.get("locked_inherited_r2bh_checkpoint") == R2BH_CHECKPOINT and src.get("locked_inherited_r2bg_checkpoint") == R2BG_CHECKPOINT and src.get("locked_inherited_r2bf_checkpoint") == R2BF_CHECKPOINT and src.get("locked_inherited_r2be_checkpoint") == R2BE_CHECKPOINT and src.get("r2bg_result_bucket") == R2BG_RESULT_BUCKET and src.get("r2bg_outcome_bucket") == R2BG_OUTCOME_BUCKET and src.get("source_locked_bool") is True
    unavailable_ok = exec_rec.get("execution_mode_bucket") == "explicit_local_outcome_alignment_unavailable" and gen.get("generation_bucket") == GENERATION_BUCKET and gen.get("generated_group_set_exact_bool") is False and gen.get("material_generated_bool") is False
    boundary_ok = exec_rec.get("material_repair_generation_bool") is False and exec_rec.get("experiment_metric_bool") is False and exec_rec.get("source_candidate_corpus_scan_bool") is False and exec_rec.get("signal_interpretation_bool") is False and no_metric.get("experiment_metrics_bool") is False and no_metric.get("success_rates_mrr_hits_ranks_scores_bool") is False and no_metric.get("signal_interpretation_bool") is False and pub.get("private_rows_public_bool") is False and pub.get("private_ids_paths_queries_gold_exact_values_public_bool") is False and input_root.get("input_root_safety_pass_bool") is True and input_root.get("implicit_root_discovery_bool") is False and input_root.get("public_root_path_or_basename_bool") is False
    integrity_ok = set(gates) == set(R2BK_GATES) and len(gates) == len(R2BK_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2BK_SYNTH) and len(synth) == len(R2BK_SYNTH) and len(synth) == len(set(synth)) and len(read) == 1 and read[0].get("all_public_readback_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BK_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BK_STOP_FALSE)
    return {"source_ok": source_ok, "unavailable_ok": unavailable_ok, "boundary_ok": boundary_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok, "audit_ok": source_ok and unavailable_ok and boundary_ok and integrity_ok and stop_ok}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BK_CHECKPOINT, R2BK_STATUS, "outcome_alignment_source_labels_absent", GENERATION_BUCKET, "generated_group_set_exact_bool=false", "material_generated_bool=false", "controlled unavailable result", "public-only audit", "no private read", "no metric recompute", "no material generation", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(x in text for x in fragments) or all(x in text for x in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bl-evidence-pair-support-outcome-aligned-material-public-audit-package.md")) and ok(read("docs/zh/bea-v1-haae-r2bl-evidence-pair-support-outcome-aligned-material-public-audit-package.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bl-evidence-pair-support-outcome-aligned-material-public-audit-package.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(r2bk: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2bk is None:
        try: r2bk = load_json(repo_root() / R2BK_REPORT_PATH)
        except Exception: r2bk = {}
    audit = audit_r2bk(r2bk); rb = public_readback_match(self_test_total)
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_UNAVAILABLE if not (audit["unavailable_ok"] and audit["boundary_ok"] and audit["integrity_ok"]) else (STATUS_FAIL_STOP_GO if not audit["stop_ok"] else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS)))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2blstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_public_audit_pass"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bk_source_lock_gate": audit["source_ok"], "r2bk_unavailable_status_gate": audit["unavailable_ok"], "r2bk_no_material_generated_gate": audit["unavailable_ok"], "r2bk_no_metric_gate": audit["boundary_ok"], "r2bk_no_source_scan_gate": audit["boundary_ok"], "r2bk_gate_synthetic_readback_exact_gate": audit["integrity_ok"], "r2bk_stop_go_to_r2bl_only_gate": audit["stop_ok"], "public_only_audit_gate": True, "aggregate_publication_gate": True, "r2bm_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2blsource0000", "locked_haae_r2bk_checkpoint": R2BK_CHECKPOINT, "locked_haae_r2bk_status": R2BK_STATUS, "locked_haae_r2bk_self_test_total": R2BK_SELF_TEST_TOTAL, "locked_inherited_r2bj_checkpoint": R2BJ_CHECKPOINT, "locked_inherited_r2bi_checkpoint": R2BI_CHECKPOINT, "locked_inherited_r2bh_checkpoint": R2BH_CHECKPOINT, "locked_inherited_r2bg_checkpoint": R2BG_CHECKPOINT, "locked_inherited_r2bf_checkpoint": R2BF_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "source_locked_bool": audit["source_ok"]}],
        "r2bk_unavailable_audit_records": [{"anonymous_audit_id": "haaer2blaudit0000", "outcome_alignment_source_labels_absent_bool": True, "generation_bucket": GENERATION_BUCKET, "generated_group_set_exact_bool": False, "material_generated_bool": False, "controlled_unavailable_result_bool": audit["unavailable_ok"], "r2bg_result_bucket": R2BG_RESULT_BUCKET, "r2bg_outcome_bucket": R2BG_OUTCOME_BUCKET}],
        "r2bk_integrity_audit_records": [{"anonymous_integrity_id": "haaer2blintegrity0000", "r2bk_gate_synthetic_readback_exact_bool": audit["integrity_ok"], "r2bk_stop_go_only_to_r2bl_bool": audit["stop_ok"], "r2bk_no_private_read_metrics_material_scan_claim_bool": audit["boundary_ok"]}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "haaer2blprivacy0000", "public_only_audit_bool": True, "no_private_root_cli_entrypoint_bool": True, "private_root_read_bool": False, "private_material_read_bool": False, "material_generation_bool": False, "metric_recompute_bool": False, "source_scan_bool": False, "raw_private_exact_publication_bool": False}],
        "publication_records": [{"anonymous_publication_id": "haaer2blpub0000", "aggregate_only_public_artifact_bool": True, "private_root_path_public_bool": False, "task_query_raw_public_bool": False, "exact_metric_public_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2blgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2blsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2blreadback0000", **rb}], "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if report.get("self_test_total") != SELF_TEST_EXPECTED: issues.append("self_test_validator_count_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if len(synth) != len(set(synth)): issues.append("synthetic_validator_duplicate_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    expected = {"locked_haae_r2bk_checkpoint": R2BK_CHECKPOINT, "locked_haae_r2bk_status": R2BK_STATUS, "locked_haae_r2bk_self_test_total": R2BK_SELF_TEST_TOTAL, "locked_inherited_r2bj_checkpoint": R2BJ_CHECKPOINT, "locked_inherited_r2bi_checkpoint": R2BI_CHECKPOINT, "locked_inherited_r2bh_checkpoint": R2BH_CHECKPOINT, "locked_inherited_r2bg_checkpoint": R2BG_CHECKPOINT, "locked_inherited_r2bf_checkpoint": R2BF_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT}
    for f, e in expected.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    aud = (report.get("r2bk_unavailable_audit_records") or [{}])[0]
    if aud.get("outcome_alignment_source_labels_absent_bool") is not True: issues.append("outcome_alignment_source_labels_absent")
    if aud.get("generation_bucket") != GENERATION_BUCKET or aud.get("generated_group_set_exact_bool") is not False or aud.get("material_generated_bool") is not False or aud.get("controlled_unavailable_result_bool") is not True: issues.append("unavailable_result_mismatch")
    if aud.get("r2bg_result_bucket") != R2BG_RESULT_BUCKET: issues.append("audit_r2bg_result_bucket")
    if aud.get("r2bg_outcome_bucket") != R2BG_OUTCOME_BUCKET: issues.append("audit_r2bg_outcome_bucket")
    integ = (report.get("r2bk_integrity_audit_records") or [{}])[0]
    for f in ["r2bk_gate_synthetic_readback_exact_bool", "r2bk_stop_go_only_to_r2bl_bool", "r2bk_no_private_read_metrics_material_scan_claim_bool"]:
        if integ.get(f) is not True: issues.append(f"integrity_{f}")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    for f in ["public_only_audit_bool", "no_private_root_cli_entrypoint_bool"]:
        if priv.get(f) is not True: issues.append(f"privacy_{f}")
    for f in ["private_root_read_bool", "private_material_read_bool", "material_generation_bool", "metric_recompute_bool", "source_scan_bool", "raw_private_exact_publication_bool"]:
        if priv.get(f) is not False: issues.append(f"privacy_{f}")
    pub = (report.get("publication_records") or [{}])[0]
    if pub.get("aggregate_only_public_artifact_bool") is not True: issues.append("publication_aggregate_only_public_artifact_bool")
    for f in ["private_root_path_public_bool", "task_query_raw_public_bool", "exact_metric_public_bool"]:
        if pub.get(f) is not False: issues.append(f"publication_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bm_stop_go_mismatch")
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
    failures: list[str] = []; base = load_json(repo_root() / R2BK_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    passed = build_report(base); check("audit_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    muts = [("r2bk_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bj_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2bk_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE), ("r2bk_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE), ("r2bj_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2be_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2bg_result_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("r2bg_result_bucket", "signal"), STATUS_FAIL_SOURCE), ("r2bg_outcome_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("r2bg_outcome_bucket", "available"), STATUS_FAIL_SOURCE), ("unavailable_fact_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("execution_mode_bucket", "explicit_local_generation"), STATUS_FAIL_UNAVAILABLE), ("generation_bucket_drift_fail", lambda r: r["generated_group_records"][0].__setitem__("generation_bucket", "generated"), STATUS_FAIL_UNAVAILABLE), ("generated_group_overclaim_fail", lambda r: r["generated_group_records"][0].__setitem__("generated_group_set_exact_bool", True), STATUS_FAIL_UNAVAILABLE), ("material_generated_overclaim_fail", lambda r: r["generated_group_records"][0].__setitem__("material_generated_bool", True), STATUS_FAIL_UNAVAILABLE), ("metric_overauth_fail", lambda r: r["no_metric_records"][0].__setitem__("experiment_metrics_bool", True), STATUS_FAIL_UNAVAILABLE), ("source_scan_overauth_fail", lambda r: r["execution_mode_records"][0].__setitem__("source_candidate_corpus_scan_bool", True), STATUS_FAIL_UNAVAILABLE), ("r2bk_execution_signal_interpretation_fail", lambda r: r["execution_mode_records"][0].__setitem__("signal_interpretation_bool", True), STATUS_FAIL_UNAVAILABLE), ("r2bk_no_metric_signal_interpretation_fail", lambda r: r["no_metric_records"][0].__setitem__("signal_interpretation_bool", True), STATUS_FAIL_UNAVAILABLE), ("r2bk_private_rows_public_fail", lambda r: r["publication_records"][0].__setitem__("private_rows_public_bool", True), STATUS_FAIL_UNAVAILABLE), ("r2bk_private_ids_public_fail", lambda r: r["publication_records"][0].__setitem__("private_ids_paths_queries_gold_exact_values_public_bool", True), STATUS_FAIL_UNAVAILABLE), ("r2bk_input_implicit_root_fail", lambda r: r["input_root_safety_records"][0].__setitem__("implicit_root_discovery_bool", True), STATUS_FAIL_UNAVAILABLE), ("r2bk_input_public_root_fail", lambda r: r["input_root_safety_records"][0].__setitem__("public_root_path_or_basename_bool", True), STATUS_FAIL_UNAVAILABLE), ("r2bk_gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop(), STATUS_FAIL_UNAVAILABLE), ("r2bk_gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), STATUS_FAIL_UNAVAILABLE), ("r2bk_synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), STATUS_FAIL_UNAVAILABLE), ("r2bk_synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), STATUS_FAIL_UNAVAILABLE), ("r2bk_readback_drop_fail", lambda r: r.__setitem__("public_readback_records", []), STATUS_FAIL_UNAVAILABLE), ("r2bk_stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__("haae_r2bl_outcome_aligned_material_public_audit_authorized_bool", False), STATUS_FAIL_STOP_GO), ("r2bk_no_source_scan_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__("r2bl_no_source_scan_bool", False), STATUS_FAIL_STOP_GO), ("r2bk_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_STOP_GO), ("r2bk_experiment_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("experiment_authorized_bool", True), STATUS_FAIL_STOP_GO)]
    for name, mut, status in muts:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == status)
    report_muts = [("r2bm_stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("r2bm_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("r2bm_material_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("material_generation_authorized_bool", True), "overauthorization_material_generation_authorized_bool"), ("r2bm_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"), ("r2bm_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("signal_claim_authorized_bool", True), "overauthorization_signal_claim_authorized_bool"), ("publication_aggregate_drop_fail", lambda r: r["publication_records"][0].__setitem__("aggregate_only_public_artifact_bool", False), "publication_aggregate_only_public_artifact_bool"), ("publication_private_root_overauth_fail", lambda r: r["publication_records"][0].__setitem__("private_root_path_public_bool", True), "publication_private_root_path_public_bool"), ("publication_exact_metric_overauth_fail", lambda r: r["publication_records"][0].__setitem__("exact_metric_public_bool", True), "publication_exact_metric_public_bool"), ("audit_r2bg_result_drift_fail", lambda r: r["r2bk_unavailable_audit_records"][0].__setitem__("r2bg_result_bucket", "signal"), "audit_r2bg_result_bucket"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_validator_duplicate_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "public_readback_record_mismatch")]
    for name, mut, issue in report_muts:
        m = json.loads(json.dumps(passed)); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo_root() / public_artifact_path(str(args["validate"]))) ; issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] == STATUS_PASS else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
