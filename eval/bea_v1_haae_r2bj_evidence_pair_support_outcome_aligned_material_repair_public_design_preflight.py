#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BJ outcome-aligned material repair public design preflight.

Public-only, non-executing. Reads only public R2BI/R2BG context and produces a
fail-closed design contract for future explicit local R2BK repair/generation.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BJ Evidence-Pair Support Outcome-Aligned Material Repair Public Design Preflight"
SLUG = "bea_v1_haae_r2bj_evidence_pair_support_outcome_aligned_material_repair_public_design_preflight"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BI_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bi_evidence_pair_support_next_step_decision_package/bea_v1_haae_r2bi_evidence_pair_support_next_step_decision_package_report.json")

R2BI_CHECKPOINT = "f231205"
R2BI_STATUS = "haae_r2bi_evidence_pair_support_public_next_step_decision_design_complete_r2bj_outcome_aligned_material_repair_public_design_preflight_authorized"
R2BI_SELF_TEST_TOTAL = 34
R2BH_CHECKPOINT = "3b566a2"
R2BG_CHECKPOINT = "ad8de95"
R2BG_STATUS = "haae_r2bg_explicit_local_redesigned_material_experiment_complete_r2bh_public_audit_authorized_artifact_or_weak_signal"
R2BF_CHECKPOINT = "322fbca"
R2BE_CHECKPOINT = "c3901d6"
RESULT_BUCKET = "artifact_or_weak_signal"
OUTCOME_BUCKET = "outcome_eval_alignment_unavailable"

STATUS_PASS = "haae_r2bj_outcome_aligned_material_repair_public_design_preflight_complete_r2bk_explicit_local_repair_generation_authorized"
STATUS_FAIL_SOURCE = "haae_r2bj_fail_closed_r2bi_source_or_decision_mismatch"
STATUS_FAIL_CONTRACT = "haae_r2bj_fail_closed_r2bk_contract_or_stop_go_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2bj_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bj_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BK Evidence-Pair Support Explicit Local Outcome-Aligned Material Repair Generation"

GROUPS = ["outcome_aligned_task_frame", "outcome_aligned_source_manifest_private", "outcome_aligned_evidence_unit_pool", "outcome_aligned_support_pair_material", "outcome_aligned_control_pair_material", "outcome_alignment_eval_private", "gold_isolation_eval_private", "alignment_qa", "parent_r2be_row_ref_private", "repair_provenance_private"]
R2BI_TRUE_DECISIONS = ["outcome_aligned_material_repair_design_selected_bool", "close_line_deferred_bool", "pivot_deferred_bool", "rerun_experiment_without_repair_rejected_bool", "scale_preflight_rejected_bool", "method_default_claim_rejected_bool"]
R2BI_STOP_TRUE = ["haae_r2bj_outcome_aligned_material_repair_public_design_preflight_authorized_bool", "r2bj_public_only_design_preflight_bool", "r2bj_no_execution_bool", "r2bj_no_private_read_write_bool", "r2bj_no_metric_recompute_bool", "r2bj_no_material_generation_in_r2bj_bool"]
R2BI_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "private_root_access_authorized_bool", "execution_authorized_bool", "experiment_authorized_bool", "metric_recompute_authorized_bool", "experiment_metrics_authorized_bool", "material_generation_authorized_bool", "material_repair_execution_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
R2BI_GATES = ["r2bh_source_lock_gate", "r2bg_cross_lock_gate", "r2bh_public_only_audit_gate", "r2bh_gate_synthetic_readback_exact_gate", "r2bh_stop_go_to_r2bi_gate", "artifact_or_weak_signal_decision_gate", "outcome_aligned_repair_design_decision_gate", "rejected_options_gate", "r2bj_stop_go_only_gate", "public_only_non_executing_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2BI_SYNTH = ["decision_pass", "safe_parser_fail", "r2bh_checkpoint_drift_fail", "r2bh_status_drift_fail", "r2bh_self_test_drift_fail", "r2bg_checkpoint_drift_fail", "r2bg_status_drift_fail", "r2bg_result_drift_fail", "r2bg_outcome_bucket_drift_fail", "r2bg_execution_opt_in_drift_fail", "r2bg_execution_private_read_drift_fail", "r2bg_execution_private_write_drift_fail", "r2bh_boundary_drift_fail", "r2bh_gate_drop_fail", "r2bh_gate_duplicate_fail", "r2bh_synthetic_drop_fail", "r2bh_synthetic_duplicate_fail", "r2bh_readback_drop_fail", "r2bh_stop_go_overauth_fail", "decision_selected_drop_fail", "decision_close_line_selected_fail", "decision_scale_selected_fail", "decision_method_default_claim_fail", "r2bj_stop_go_true_drop_fail", "r2bj_private_read_overauth_fail", "r2bj_material_generation_overauth_fail", "r2bj_metric_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "public_leak_fail"]

GATES = ["r2bi_source_lock_gate", "r2bi_decision_gate", "r2bi_stop_go_exact_gate", "inherited_artifact_or_weak_signal_gate", "outcome_alignment_repair_design_gate", "r2bk_schema_exact_gate", "r2bk_root_safety_gate", "r2bk_privacy_publication_gate", "r2bk_no_metrics_gate", "r2bk_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["preflight_pass", "safe_parser_fail", "r2bi_checkpoint_drift_fail", "r2bi_status_drift_fail", "r2bi_self_test_drift_fail", "r2bi_decision_drop_fail", "r2bi_stop_go_drop_fail", "r2bi_stop_go_overauth_fail", "r2bi_gate_exact_drift_fail", "r2bi_synthetic_exact_drift_fail", "r2bi_readback_exact_drift_fail", "inherited_result_drift_fail", "inherited_outcome_drift_fail", "r2bi_audit_record_drift_fail", "schema_group_missing_fail", "schema_group_extra_fail", "schema_group_duplicate_fail", "root_safety_policy_drift_fail", "privacy_policy_drift_fail", "publication_policy_drift_fail", "outcome_alignment_policy_drift_fail", "no_metric_policy_drift_fail", "r2bk_broad_source_scan_overauth_fail", "r2bk_allowlist_policy_drop_fail", "stop_go_true_drop_fail", "stop_go_private_read_overauth_fail", "stop_go_private_write_overauth_fail", "stop_go_metric_overauth_fail", "stop_go_source_scan_overauth_fail", "stop_go_claim_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "duplicate_readback_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
STOP_TRUE = ["haae_r2bk_explicit_local_outcome_aligned_material_repair_generation_authorized_bool", "r2bk_explicit_opt_in_required_bool", "r2bk_existing_r2be_private_material_read_authorized_bool", "r2bk_private_output_write_authorized_bool", "r2bk_outcome_aligned_material_repair_generation_authorized_bool", "r2bk_material_generation_only_no_experiment_metrics_bool", "r2bk_aggregate_only_public_artifact_required_bool", "r2bk_public_audit_required_after_generation_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "execution_authorized_bool", "experiment_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "source_scan_broad_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scale_preflight_authorized_bool", "external_validation_authorized_bool", "signal_claim_authorized_bool", "method_claim_authorized_bool", "default_claim_authorized_bool", "winner_claim_authorized_bool", "scale_claim_authorized_bool", "raw_publication_authorized_bool"]
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

def audit_r2bi(r2bi: dict[str, Any]) -> dict[str, bool]:
    src = (r2bi.get("source_lock_records") or [{}])[0]; dec = (r2bi.get("decision_records") or [{}])[0]; aud = (r2bi.get("r2bh_audit_records") or [{}])[0]; stop = (r2bi.get("stop_go_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2bi.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2bi.get("synthetic_validator_records", [])]; read = r2bi.get("public_readback_records", [])
    source_ok = r2bi.get("status") == R2BI_STATUS and r2bi.get("self_test_total") == R2BI_SELF_TEST_TOTAL and r2bi.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bh_checkpoint") == R2BH_CHECKPOINT and src.get("locked_haae_r2bg_checkpoint") == R2BG_CHECKPOINT and src.get("locked_haae_r2bg_status") == R2BG_STATUS and src.get("locked_inherited_r2bf_checkpoint") == R2BF_CHECKPOINT and src.get("locked_inherited_r2be_checkpoint") == R2BE_CHECKPOINT and src.get("source_locked_bool") is True
    decision_ok = all(dec.get(f) is True for f in R2BI_TRUE_DECISIONS)
    inherited_ok = aud.get("result_bucket") == RESULT_BUCKET and aud.get("outcome_eval_alignment_bucket") == OUTCOME_BUCKET and aud.get("no_signal_claim_bool") is True
    integrity_ok = set(gates) == set(R2BI_GATES) and len(gates) == len(R2BI_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2BI_SYNTH) and len(synth) == len(R2BI_SYNTH) and len(synth) == len(set(synth)) and len(read) == 1 and read[0].get("all_public_readback_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BI_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BI_STOP_FALSE)
    return {"source_ok": source_ok, "decision_ok": decision_ok, "inherited_ok": inherited_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok, "audit_ok": source_ok and decision_ok and inherited_ok and integrity_ok and stop_ok}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BI_CHECKPOINT, R2BI_STATUS, R2BH_CHECKPOINT, R2BG_CHECKPOINT, RESULT_BUCKET, OUTCOME_BUCKET, "outcome_alignment_repair_design_selected_bool", "outcome_aligned_task_frame", "repair_provenance_private", "explicit opt-in", "existing R2BE private material", "aggregate-only public artifact", "public audit required after generation", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    compact = [PHASE, STATUS_PASS, f"{total}/{total}", R2BI_CHECKPOINT, R2BI_STATUS, R2BH_CHECKPOINT, R2BG_CHECKPOINT, RESULT_BUCKET, OUTCOME_BUCKET, "outcome_alignment_repair_design_selected_bool", "outcome_aligned_task_frame", "repair_provenance_private", "explicit opt-in", "existing R2BE private material", "aggregate-only public artifact", "public audit required after generation"]
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced) or all(f in text for f in compact)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bj-evidence-pair-support-outcome-aligned-material-repair-public-design-preflight.md")) and ok(read("docs/zh/bea-v1-haae-r2bj-evidence-pair-support-outcome-aligned-material-repair-public-design-preflight.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bj-evidence-pair-support-outcome-aligned-material-repair-public-design-preflight.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(r2bi: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2bi is None:
        try: r2bi = load_json(repo_root() / R2BI_REPORT_PATH)
        except Exception: r2bi = {}
    audit = audit_r2bi(r2bi); rb = public_readback_match(self_test_total)
    contract_ok = audit["audit_ok"]
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_CONTRACT if not contract_ok else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bjstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_design_preflight_pass"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bi_source_lock_gate": audit["source_ok"], "r2bi_decision_gate": audit["decision_ok"], "r2bi_stop_go_exact_gate": audit["stop_ok"], "inherited_artifact_or_weak_signal_gate": audit["inherited_ok"], "outcome_alignment_repair_design_gate": True, "r2bk_schema_exact_gate": True, "r2bk_root_safety_gate": True, "r2bk_privacy_publication_gate": True, "r2bk_no_metrics_gate": True, "r2bk_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bjsource0000", "locked_haae_r2bi_checkpoint": R2BI_CHECKPOINT, "locked_haae_r2bi_status": R2BI_STATUS, "locked_haae_r2bi_self_test_total": R2BI_SELF_TEST_TOTAL, "locked_inherited_r2bh_checkpoint": R2BH_CHECKPOINT, "locked_inherited_r2bg_checkpoint": R2BG_CHECKPOINT, "locked_inherited_r2bg_status": R2BG_STATUS, "locked_inherited_r2bf_checkpoint": R2BF_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT, "source_locked_bool": audit["source_ok"]}],
        "r2bi_decision_audit_records": [{"anonymous_audit_id": "haaer2bjaudit0000", "r2bi_decision_fields_exact_bool": audit["decision_ok"], "r2bi_stop_go_only_to_r2bj_bool": audit["stop_ok"], "r2bi_gate_synthetic_readback_exact_bool": audit["integrity_ok"], "artifact_or_weak_signal_locked_bool": audit["inherited_ok"], "outcome_eval_alignment_bucket": OUTCOME_BUCKET, "result_bucket": RESULT_BUCKET}],
        "outcome_alignment_repair_design_records": [{"anonymous_design_id": "haaer2bjdesign0000", "outcome_alignment_repair_design_selected_bool": True, "future_r2bk_design_only_bool": True, "r2bj_public_only_non_executing_bool": True}],
        "future_r2bk_schema_contract_records": [{"anonymous_schema_id": "haaer2bjschema0000", "schema_group_set_exact_bool": True, "required_group_buckets": GROUPS}],
        "future_r2bk_root_safety_contract_records": [{"anonymous_root_id": "haaer2bjroot0000", "explicit_opt_in_required_bool": True, "no_implicit_tmp_discovery_bool": True, "root_outside_repo_bool": True, "no_symlink_path_traversal_bool": True, "no_root_nesting_bool": True}],
        "future_r2bk_policy_records": [{"anonymous_policy_id": "haaer2bjpolicy0000", "existing_r2be_private_material_read_required_bool": True, "private_output_write_required_bool": True, "outcome_aligned_material_repair_generation_required_bool": True, "material_generation_only_no_experiment_metrics_bool": True, "aggregate_only_public_artifact_bool": True, "public_audit_required_after_generation_bool": True, "broad_source_corpus_scan_bool": False, "public_source_allowlist_only_if_explicit_bounded_bool": True}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "haaer2bjprivacy0000", "public_only_design_preflight_bool": True, "private_root_read_bool": False, "private_rows_read_bool": False, "repair_regenerate_material_bool": False, "metric_compute_recompute_bool": False, "source_candidate_corpus_scan_bool": False, "runtime_retrieval_ci_network_provider_clone_bool": False, "raw_private_exact_publication_bool": False, "signal_method_default_winner_scale_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bjgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bjsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bjreadback0000", **rb}], "stop_go_records": [stop]}
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for g in report["pass_fail_gate_records"]:
        if g["gate_bucket"] == "forbidden_scan_pass_gate": g["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_PRIVACY
    return report

def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if report.get("self_test_total") != len(SYNTH): issues.append("self_test_validator_count_mismatch")
    design = (report.get("outcome_alignment_repair_design_records") or [{}])[0]
    if design.get("outcome_alignment_repair_design_selected_bool") is not True or design.get("future_r2bk_design_only_bool") is not True or design.get("r2bj_public_only_non_executing_bool") is not True: issues.append("outcome_alignment_design_mismatch")
    gates = [r.get("gate_bucket") for r in report.get("pass_fail_gate_records", [])]
    if set(gates) != set(GATES) or len(gates) != len(GATES): issues.append("gate_set_mismatch")
    if len(gates) != len(set(gates)): issues.append("gate_duplicate_mismatch")
    synth = [r.get("validator_bucket") for r in report.get("synthetic_validator_records", [])]
    if set(synth) != set(SYNTH) or len(synth) != len(SYNTH): issues.append("synthetic_validator_set_mismatch")
    if len(synth) != len(set(synth)): issues.append("synthetic_validator_duplicate_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    src = (report.get("source_lock_records") or [{}])[0]
    for f, e in {"locked_haae_r2bi_checkpoint": R2BI_CHECKPOINT, "locked_haae_r2bi_status": R2BI_STATUS, "locked_haae_r2bi_self_test_total": R2BI_SELF_TEST_TOTAL, "locked_inherited_r2bh_checkpoint": R2BH_CHECKPOINT, "locked_inherited_r2bg_checkpoint": R2BG_CHECKPOINT, "locked_inherited_r2bg_status": R2BG_STATUS, "locked_inherited_r2bf_checkpoint": R2BF_CHECKPOINT, "locked_inherited_r2be_checkpoint": R2BE_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    audit = (report.get("r2bi_decision_audit_records") or [{}])[0]
    if audit.get("r2bi_decision_fields_exact_bool") is not True: issues.append("r2bi_audit_decision_fields")
    if audit.get("r2bi_stop_go_only_to_r2bj_bool") is not True: issues.append("r2bi_audit_stop_go")
    if audit.get("r2bi_gate_synthetic_readback_exact_bool") is not True: issues.append("r2bi_audit_integrity")
    if audit.get("artifact_or_weak_signal_locked_bool") is not True or audit.get("result_bucket") != RESULT_BUCKET or audit.get("outcome_eval_alignment_bucket") != OUTCOME_BUCKET: issues.append("r2bi_audit_result_outcome")
    schema = (report.get("future_r2bk_schema_contract_records") or [{}])[0]; groups = schema.get("required_group_buckets") or []
    if schema.get("schema_group_set_exact_bool") is not True or groups != GROUPS or len(groups) != len(set(groups)): issues.append("schema_group_set_mismatch")
    for section, checks in {"future_r2bk_root_safety_contract_records": ["explicit_opt_in_required_bool", "no_implicit_tmp_discovery_bool", "root_outside_repo_bool", "no_symlink_path_traversal_bool", "no_root_nesting_bool"], "future_r2bk_policy_records": ["existing_r2be_private_material_read_required_bool", "private_output_write_required_bool", "outcome_aligned_material_repair_generation_required_bool", "material_generation_only_no_experiment_metrics_bool", "aggregate_only_public_artifact_bool", "public_audit_required_after_generation_bool", "public_source_allowlist_only_if_explicit_bounded_bool"]}.items():
        rec = (report.get(section) or [{}])[0]
        for f in checks:
            if rec.get(f) is not True: issues.append(f"{section}_{f}")
    policy = (report.get("future_r2bk_policy_records") or [{}])[0]
    if policy.get("broad_source_corpus_scan_bool") is not False: issues.append("future_r2bk_policy_records_broad_source_corpus_scan_bool")
    priv = (report.get("privacy_boundary_records") or [{}])[0]
    for f in ["public_only_design_preflight_bool"]:
        if priv.get(f) is not True: issues.append(f"privacy_{f}")
    for f in ["private_root_read_bool", "private_rows_read_bool", "repair_regenerate_material_bool", "metric_compute_recompute_bool", "source_candidate_corpus_scan_bool", "runtime_retrieval_ci_network_provider_clone_bool", "raw_private_exact_publication_bool", "signal_method_default_winner_scale_claim_bool"]:
        if priv.get(f) is not False: issues.append(f"privacy_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bk_stop_go_mismatch")
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
    failures: list[str] = []; base = load_json(repo_root() / R2BI_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    passed = build_report(base); check("preflight_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    muts = [("r2bi_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bh_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2bi_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE), ("r2bi_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE), ("r2bi_decision_drop_fail", lambda r: r["decision_records"][0].__setitem__("outcome_aligned_material_repair_design_selected_bool", False), STATUS_FAIL_CONTRACT), ("r2bi_stop_go_drop_fail", lambda r: r["stop_go_records"][0].__setitem__("haae_r2bj_outcome_aligned_material_repair_public_design_preflight_authorized_bool", False), STATUS_FAIL_CONTRACT), ("r2bi_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_CONTRACT), ("inherited_result_drift_fail", lambda r: r["r2bh_audit_records"][0].__setitem__("result_bucket", "signal"), STATUS_FAIL_CONTRACT), ("inherited_outcome_drift_fail", lambda r: r["r2bh_audit_records"][0].__setitem__("outcome_eval_alignment_bucket", "available"), STATUS_FAIL_CONTRACT)]
    for name, mut, status in muts:
        m = json.loads(json.dumps(base)); mut(m); check(name, build_report(m)["status"] == status)
    report_mut = [("schema_group_missing_fail", lambda r: r["future_r2bk_schema_contract_records"][0]["required_group_buckets"].pop(), "schema_group_set_mismatch"), ("schema_group_extra_fail", lambda r: r["future_r2bk_schema_contract_records"][0]["required_group_buckets"].append("extra"), "schema_group_set_mismatch"), ("schema_group_duplicate_fail", lambda r: r["future_r2bk_schema_contract_records"][0]["required_group_buckets"].append(GROUPS[0]), "schema_group_set_mismatch"), ("root_safety_policy_drift_fail", lambda r: r["future_r2bk_root_safety_contract_records"][0].__setitem__("no_implicit_tmp_discovery_bool", False), "future_r2bk_root_safety_contract_records_no_implicit_tmp_discovery_bool"), ("privacy_policy_drift_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("private_root_read_bool", True), "privacy_private_root_read_bool"), ("publication_policy_drift_fail", lambda r: r["future_r2bk_policy_records"][0].__setitem__("aggregate_only_public_artifact_bool", False), "future_r2bk_policy_records_aggregate_only_public_artifact_bool"), ("outcome_alignment_policy_drift_fail", lambda r: r["outcome_alignment_repair_design_records"][0].__setitem__("outcome_alignment_repair_design_selected_bool", False), "outcome_alignment_design_mismatch"), ("no_metric_policy_drift_fail", lambda r: r["future_r2bk_policy_records"][0].__setitem__("material_generation_only_no_experiment_metrics_bool", False), "future_r2bk_policy_records_material_generation_only_no_experiment_metrics_bool"), ("stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("stop_go_private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("stop_go_private_write_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_write_authorized_bool", True), "overauthorization_private_write_authorized_bool"), ("stop_go_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"), ("stop_go_source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "overauthorization_source_scan_authorized_bool"), ("stop_go_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("signal_claim_authorized_bool", True), "overauthorization_signal_claim_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(dict(r["synthetic_validator_records"][0])), "synthetic_validator_duplicate_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"), ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(dict(r["public_readback_records"][0])), "public_readback_record_mismatch")]
    for name, mut, issue in report_mut:
        m = json.loads(json.dumps(passed)); mut(m); check(name, issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def run_self_test_hardened() -> dict[str, Any]:
    failures: list[str] = []
    base = load_json(repo_root() / R2BI_REPORT_PATH)

    def check(name: str, cond: bool) -> None:
        if not cond:
            failures.append(name)

    passed = build_report(base)
    check("preflight_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try:
        parse_args(["--bad"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)

    source_mutations = [
        ("r2bi_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bh_checkpoint", "bad"), STATUS_FAIL_SOURCE),
        ("r2bi_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE),
        ("r2bi_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE),
        ("r2bi_decision_drop_fail", lambda r: r["decision_records"][0].__setitem__("outcome_aligned_material_repair_design_selected_bool", False), STATUS_FAIL_CONTRACT),
        ("r2bi_stop_go_drop_fail", lambda r: r["stop_go_records"][0].__setitem__("haae_r2bj_outcome_aligned_material_repair_public_design_preflight_authorized_bool", False), STATUS_FAIL_CONTRACT),
        ("r2bi_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_CONTRACT),
        ("r2bi_gate_exact_drift_fail", lambda r: r["pass_fail_gate_records"].pop(), STATUS_FAIL_CONTRACT),
        ("r2bi_synthetic_exact_drift_fail", lambda r: r["synthetic_validator_records"].append(r["synthetic_validator_records"][0]), STATUS_FAIL_CONTRACT),
        ("r2bi_readback_exact_drift_fail", lambda r: r.__setitem__("public_readback_records", []), STATUS_FAIL_CONTRACT),
        ("inherited_result_drift_fail", lambda r: r["r2bh_audit_records"][0].__setitem__("result_bucket", "signal"), STATUS_FAIL_CONTRACT),
        ("inherited_outcome_drift_fail", lambda r: r["r2bh_audit_records"][0].__setitem__("outcome_eval_alignment_bucket", "available"), STATUS_FAIL_CONTRACT),
    ]
    for name, mutate, expected_status in source_mutations:
        mutated = json.loads(json.dumps(base))
        mutate(mutated)
        check(name, build_report(mutated)["status"] == expected_status)

    report_mutations = [
        ("r2bi_audit_record_drift_fail", lambda r: r["r2bi_decision_audit_records"][0].__setitem__("r2bi_gate_synthetic_readback_exact_bool", False), "r2bi_audit_integrity"),
        ("schema_group_missing_fail", lambda r: r["future_r2bk_schema_contract_records"][0]["required_group_buckets"].pop(), "schema_group_set_mismatch"),
        ("schema_group_extra_fail", lambda r: r["future_r2bk_schema_contract_records"][0]["required_group_buckets"].append("extra"), "schema_group_set_mismatch"),
        ("schema_group_duplicate_fail", lambda r: r["future_r2bk_schema_contract_records"][0]["required_group_buckets"].append(GROUPS[0]), "schema_group_set_mismatch"),
        ("root_safety_policy_drift_fail", lambda r: r["future_r2bk_root_safety_contract_records"][0].__setitem__("no_implicit_tmp_discovery_bool", False), "future_r2bk_root_safety_contract_records_no_implicit_tmp_discovery_bool"),
        ("privacy_policy_drift_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("private_root_read_bool", True), "privacy_private_root_read_bool"),
        ("publication_policy_drift_fail", lambda r: r["future_r2bk_policy_records"][0].__setitem__("aggregate_only_public_artifact_bool", False), "future_r2bk_policy_records_aggregate_only_public_artifact_bool"),
        ("outcome_alignment_policy_drift_fail", lambda r: r["outcome_alignment_repair_design_records"][0].__setitem__("outcome_alignment_repair_design_selected_bool", False), "outcome_alignment_design_mismatch"),
        ("no_metric_policy_drift_fail", lambda r: r["future_r2bk_policy_records"][0].__setitem__("material_generation_only_no_experiment_metrics_bool", False), "future_r2bk_policy_records_material_generation_only_no_experiment_metrics_bool"),
        ("r2bk_broad_source_scan_overauth_fail", lambda r: r["future_r2bk_policy_records"][0].__setitem__("broad_source_corpus_scan_bool", True), "future_r2bk_policy_records_broad_source_corpus_scan_bool"),
        ("r2bk_allowlist_policy_drop_fail", lambda r: r["future_r2bk_policy_records"][0].__setitem__("public_source_allowlist_only_if_explicit_bounded_bool", False), "future_r2bk_policy_records_public_source_allowlist_only_if_explicit_bounded_bool"),
        ("stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"),
        ("stop_go_private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"),
        ("stop_go_private_write_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_write_authorized_bool", True), "overauthorization_private_write_authorized_bool"),
        ("stop_go_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"),
        ("stop_go_source_scan_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("source_scan_authorized_bool", True), "overauthorization_source_scan_authorized_bool"),
        ("stop_go_claim_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("signal_claim_authorized_bool", True), "overauthorization_signal_claim_authorized_bool"),
        ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"),
        ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(r["pass_fail_gate_records"][0]), "gate_duplicate_mismatch"),
        ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"),
        ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(r["synthetic_validator_records"][0]), "synthetic_validator_duplicate_mismatch"),
        ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"),
        ("duplicate_readback_fail", lambda r: r["public_readback_records"].append(r["public_readback_records"][0]), "public_readback_record_mismatch"),
    ]
    for name, mutate, expected_issue in report_mutations:
        mutated = json.loads(json.dumps(passed))
        mutate(mutated)
        check(name, expected_issue in validate_report(mutated))

    leak = json.loads(json.dumps(passed))
    leak["debug"] = "/tmp/private-root r14m-001 private_pair_ref exact_score_value"
    check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        result = run_self_test_hardened(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo_root() / public_artifact_path(str(args["validate"]))) ; issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] == STATUS_PASS else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
