#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BF redesigned material public audit package.

Public-only audit after R2BE. Reads only the R2BE public artifact; never reads
private roots/material, regenerates material, computes experiment metrics, or
scans source/candidate/corpus.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BF Evidence-Pair Support Redesigned Material Public Audit Package"
SLUG = "bea_v1_haae_r2bf_evidence_pair_support_redesigned_material_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BE_REPORT_PATH = Path("artifacts/bea_v1_haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation/bea_v1_haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation_report.json")

R2BE_CHECKPOINT = "c3901d6"
R2BE_STATUS = "haae_r2be_explicit_local_redesigned_material_generation_complete_r2bf_public_audit_authorized"
R2BE_SELF_TEST_TOTAL = 40
R2BD_CHECKPOINT = "fa6119b"
R2BD_STATUS = "haae_r2bd_evidence_pair_support_redesigned_material_generation_public_design_preflight_complete_r2be_explicit_local_redesigned_material_generation_authorized"
R2BD_SELF_TEST_TOTAL = 47
R2BC_CHECKPOINT = "2171b20"
R2BB_CHECKPOINT = "a624728"
R2BA_CHECKPOINT = "f8984bf"
R2AZ_CHECKPOINT = "72590e5"

STATUS_PASS = "haae_r2bf_evidence_pair_support_redesigned_material_public_audit_complete_r2bg_experiment_authorized"
STATUS_FAIL_SOURCE = "haae_r2bf_fail_closed_r2be_source_lock_or_status_mismatch"
STATUS_FAIL_AUDIT = "haae_r2bf_fail_closed_r2be_public_audit_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2bf_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bf_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BG Evidence-Pair Support Explicit Local Redesigned Material Experiment"

GROUPS = ["redesigned_task_frame", "redesigned_source_manifest_private", "redesigned_evidence_unit_pool", "redesigned_support_pair_material", "redesigned_control_pair_material", "redesigned_path_confound_material", "redesigned_gold_isolation_eval_private", "redesigned_material_qa"]
CONTROL_FAMILIES = ["matched_hard_negative_control", "same_source_family_control", "cross_task_semantic_mismatch_control", "path_token_matched_control", "query_only_control", "evidence_only_control", "support_relation_broken_control", "gold_blind_decoy_control", "source_family_balance_control"]
BOUNDS = {"target_tasks_bucket": "target_tasks_16_to_20", "private_rows_bucket": "private_rows_le_20000", "depth_bucket": "depth_le_40", "support_pairs_bucket": "support_pairs_le_120_per_task", "control_pairs_bucket": "control_pairs_le_120_per_task", "total_pairs_bucket": "total_pairs_le_240_per_task", "source_files_bucket": "source_files_le_500", "wall_clock_bucket": "wall_clock_le_20_minutes"}
R2BE_GATES = ["r2bd_source_lock_gate", "default_noop_or_explicit_opt_in_gate", "public_allowlist_gate", "root_safety_gate", "schema_group_exact_gate", "control_family_exact_gate", "bounds_gate", "gold_eval_only_gate", "no_metric_generation_gate", "aggregate_only_public_gate", "r2bf_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2BE_SYNTH = ["default_noop_pass", "explicit_synthetic_generation_pass", "safe_parser_fail", "missing_explicit_flag_fail", "bad_r2bd_checkpoint_fail", "bad_r2bd_status_fail", "bad_r2bd_source_locked_fail", "r2bd_schema_contract_drift_fail", "r2bd_stop_go_overauth_fail", "allowlist_missing_fail", "allowlist_tmp_rejected_fail", "output_root_in_repo_fail", "output_root_symlink_fail", "output_group_symlink_escape_fail", "nonempty_unowned_output_fail", "owned_rerun_pass", "source_locked_drift_fail", "source_inherited_checkpoint_drift_fail", "schema_group_missing_fail", "schema_group_extra_fail", "control_family_missing_fail", "control_family_extra_fail", "control_family_duplicate_fail", "bounds_drift_fail", "execution_mode_drift_fail", "execution_private_read_drift_fail", "allowlist_boundary_drift_fail", "root_publication_drift_fail", "gold_policy_drift_fail", "metrics_public_leak_fail", "publication_exact_public_fail", "stop_go_true_drop_fail", "stop_go_private_overauth_fail", "stop_go_metric_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "public_leak_fail"]
R2BE_STOP_TRUE = ["haae_r2bf_evidence_pair_support_redesigned_material_public_audit_authorized_bool", "r2bf_public_only_audit_bool", "r2bf_no_private_read_bool", "r2bf_no_metric_computation_bool"]
R2BE_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "experiment_metrics_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "external_validation_authorized_bool", "scale_preflight_authorized_bool", "scale_execution_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "validated_signal_claim_authorized_bool", "downstream_value_claim_authorized_bool", "raw_publication_authorized_bool"]

GATES = ["r2be_source_lock_gate", "r2be_explicit_mode_gate", "r2be_allowlist_boundary_gate", "r2be_schema_group_exact_gate", "r2be_control_family_exact_gate", "r2be_bounds_gate", "r2be_gold_isolation_gate", "r2be_no_metric_gate", "r2be_publication_boundary_gate", "r2be_gate_synthetic_readback_exact_gate", "r2be_stop_go_exact_gate", "r2bf_public_only_boundary_gate", "r2bg_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["audit_pass", "safe_parser_fail", "r2be_checkpoint_drift_fail", "r2be_status_drift_fail", "r2be_self_test_drift_fail", "r2be_forbidden_scan_fail", "r2be_source_lock_drift_fail", "r2be_execution_mode_drift_fail", "r2be_private_read_drift_fail", "r2be_allowlist_boundary_drift_fail", "r2be_schema_group_drop_fail", "r2be_schema_group_duplicate_fail", "r2be_control_family_drop_fail", "r2be_control_family_duplicate_fail", "r2be_bounds_drift_fail", "r2be_gold_policy_drift_fail", "r2be_metric_overauth_fail", "r2be_publication_leak_fail", "r2be_gate_drop_fail", "r2be_gate_duplicate_fail", "r2be_synthetic_drop_fail", "r2be_synthetic_duplicate_fail", "r2be_readback_drop_fail", "r2be_stop_go_true_drop_fail", "r2be_stop_go_private_overauth_fail", "r2be_stop_go_metric_overauth_fail", "source_locked_record_false_fail", "source_inherited_checkpoint_drift_fail", "audit_root_attestation_drift_fail", "audit_group_presence_drift_fail", "r2bg_stop_go_true_drop_fail", "r2bg_stop_go_private_overauth_fail", "r2bg_stop_go_scale_overauth_fail", "public_only_boundary_drift_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
STOP_TRUE = ["haae_r2bg_evidence_pair_support_explicit_local_redesigned_material_experiment_authorized_bool", "r2bg_explicit_opt_in_required_bool", "r2bg_existing_r2be_private_material_read_authorized_bool", "r2bg_aggregate_metrics_only_bool", "r2bg_no_material_generation_bool", "r2bg_no_source_candidate_corpus_scan_bool", "r2bg_public_audit_required_after_experiment_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "external_validation_authorized_bool", "scale_preflight_authorized_bool", "scale_execution_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "validated_signal_claim_authorized_bool", "downstream_value_claim_authorized_bool", "raw_publication_authorized_bool"]
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|source_ref|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|top[-_]?k|\bmrr\b|hit-rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

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

def audit_r2be(r2be: dict[str, Any]) -> dict[str, bool]:
    src = (r2be.get("source_lock_records") or [{}])[0]; exe = (r2be.get("execution_mode_records") or [{}])[0]; allow = (r2be.get("allowlist_records") or [{}])[0]; root = (r2be.get("root_safety_records") or [{}])[0]; groups = (r2be.get("generated_group_records") or [{}])[0]; fam = (r2be.get("control_family_records") or [{}])[0]; bounds = (r2be.get("bounds_records") or [{}])[0]; gold = (r2be.get("gold_isolation_records") or [{}])[0]; nomet = (r2be.get("no_metric_records") or [{}])[0]; pub = (r2be.get("publication_records") or [{}])[0]; stop = (r2be.get("stop_go_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2be.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2be.get("synthetic_validator_records", [])]; rb = r2be.get("public_readback_records", [])
    source_ok = r2be.get("status") == R2BE_STATUS and r2be.get("self_test_total") == R2BE_SELF_TEST_TOTAL and r2be.get("forbidden_scan", {}).get("status") == "pass" and src.get("locked_haae_r2bd_checkpoint") == R2BD_CHECKPOINT and src.get("locked_haae_r2bd_status") == R2BD_STATUS and src.get("locked_haae_r2bd_self_test_total") == R2BD_SELF_TEST_TOTAL and src.get("locked_haae_r2bc_checkpoint") == R2BC_CHECKPOINT and src.get("locked_haae_r2bb_checkpoint") == R2BB_CHECKPOINT and src.get("locked_haae_r2ba_checkpoint") == R2BA_CHECKPOINT and src.get("locked_haae_r2az_checkpoint") == R2AZ_CHECKPOINT and src.get("source_locked_bool") is True
    mode_ok = exe.get("execution_mode_bucket") == "explicit_local_generation" and exe.get("explicit_opt_in_bool") is True and exe.get("material_generation_bool") is True and exe.get("private_write_bool") is True and exe.get("private_read_bool") is False and exe.get("source_candidate_corpus_scan_bool") is False and exe.get("experiment_metric_bool") is False
    allow_ok = allow.get("allowlist_valid_bool") is True and allow.get("operator_provided_public_source_allowlist_required_bool") is True and allow.get("implicit_source_discovery_bool") is False and allow.get("tmp_scan_bool") is False and allow.get("repo_wide_scan_bool") is False
    root_ok = root.get("root_safety_pass_bool") is True and root.get("owner_manifest_written_bool") is True and root.get("public_root_path_or_basename_bool") is False
    schema_ok = groups.get("generated_group_set_exact_bool") is True and set(groups.get("required_group_buckets", [])) == set(GROUPS) and len(groups.get("required_group_buckets", [])) == len(GROUPS)
    family_ok = fam.get("control_family_set_exact_bool") is True and set(fam.get("required_control_family_buckets", [])) == set(CONTROL_FAMILIES) and len(fam.get("required_control_family_buckets", [])) == len(CONTROL_FAMILIES)
    bounds_ok = bounds.get("bounds_satisfied_bool") is True and all(bounds.get(k) == v for k, v in BOUNDS.items())
    gold_ok = gold.get("gold_eval_only_bool") is True and all(gold.get(f) is False for f in ["gold_used_for_pair_control_construction_bool", "gold_used_for_ranking_bool", "gold_used_for_source_selection_bool"])
    metric_ok = nomet.get("material_generation_only_bool") is True and all(nomet.get(f) is False for f in ["experiment_metrics_bool", "hit_rates_mrr_ranks_scores_rates_bool", "robustness_metrics_bool"])
    pub_ok = pub.get("aggregate_only_public_report_bool") is True and all(pub.get(f) is False for f in ["exact_counts_rates_scores_public_bool", "paths_filenames_hashes_public_bool", "private_rows_public_bool", "task_query_source_evidence_pair_ids_public_bool"])
    integrity_ok = set(gates) == set(R2BE_GATES) and len(gates) == len(R2BE_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2BE_SYNTH) and len(synth) == len(R2BE_SYNTH) and len(synth) == len(set(synth)) and len(rb) == 1 and rb[0].get("all_public_readback_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BE_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BE_STOP_FALSE)
    return {"source_ok": source_ok, "mode_ok": mode_ok, "allow_ok": allow_ok, "root_ok": root_ok, "schema_ok": schema_ok, "family_ok": family_ok, "bounds_ok": bounds_ok, "gold_ok": gold_ok, "metric_ok": metric_ok, "publication_ok": pub_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok, "audit_ok": all([source_ok, mode_ok, allow_ok, root_ok, schema_ok, family_ok, bounds_ok, gold_ok, metric_ok, pub_ok, integrity_ok, stop_ok])}

def public_readback_match(total: int) -> dict[str, bool]:
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BE_CHECKPOINT, R2BE_STATUS, "public-only audit", "read only R2BE public artifact", "explicit local generation", "all_required_groups_present", "matched_hard_negative_control", "path_token_matched_control", "bounds satisfied", "gold isolation", "no experiment metrics", "aggregate-only publication", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo_root() / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bf-evidence-pair-support-redesigned-material-public-audit-package.md")) and ok(read("docs/zh/bea-v1-haae-r2bf-evidence-pair-support-redesigned-material-public-audit-package.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bf-evidence-pair-support-redesigned-material-public-audit-package.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def build_report(r2be: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    if r2be is None:
        try: r2be = load_json(repo_root() / R2BE_REPORT_PATH)
        except Exception: r2be = {}
    audit = audit_r2be(r2be); rb = public_readback_match(self_test_total)
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_AUDIT if not audit["audit_ok"] else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bfstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_public_audit_pass"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2be_source_lock_gate": audit["source_ok"], "r2be_explicit_mode_gate": audit["mode_ok"], "r2be_allowlist_boundary_gate": audit["allow_ok"], "r2be_schema_group_exact_gate": audit["schema_ok"], "r2be_control_family_exact_gate": audit["family_ok"], "r2be_bounds_gate": audit["bounds_ok"], "r2be_gold_isolation_gate": audit["gold_ok"], "r2be_no_metric_gate": audit["metric_ok"], "r2be_publication_boundary_gate": audit["publication_ok"], "r2be_gate_synthetic_readback_exact_gate": audit["integrity_ok"], "r2be_stop_go_exact_gate": audit["stop_ok"], "r2bf_public_only_boundary_gate": True, "r2bg_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bfsource0000", "locked_haae_r2be_checkpoint": R2BE_CHECKPOINT, "locked_haae_r2be_status": R2BE_STATUS, "locked_haae_r2be_self_test_total": R2BE_SELF_TEST_TOTAL, "locked_haae_r2bd_checkpoint": R2BD_CHECKPOINT, "locked_haae_r2bc_checkpoint": R2BC_CHECKPOINT, "locked_haae_r2bb_checkpoint": R2BB_CHECKPOINT, "locked_haae_r2ba_checkpoint": R2BA_CHECKPOINT, "locked_haae_r2az_checkpoint": R2AZ_CHECKPOINT, "source_locked_bool": audit["source_ok"]}],
        "r2be_material_audit_records": [{"anonymous_material_audit_id": "haaer2bfaudit0000", "r2be_explicit_local_generation_bool": audit["mode_ok"], "allowlist_boundary_pass_bool": audit["allow_ok"], "root_safety_public_attestation_pass_bool": audit["root_ok"], "schema_group_exact_bool": audit["schema_ok"], "control_family_exact_bool": audit["family_ok"], "bounds_satisfied_bool": audit["bounds_ok"], "gold_isolation_bool": audit["gold_ok"], "no_experiment_metrics_bool": audit["metric_ok"], "aggregate_only_publication_bool": audit["publication_ok"], "group_presence_bucket": "all_required_groups_present"}],
        "privacy_boundary_records": [{"anonymous_privacy_boundary_id": "haaer2bfprivacy0000", "public_only_audit_bool": True, "read_only_r2be_public_artifact_bool": True, "private_root_read_bool": False, "private_material_read_bool": False, "material_regeneration_bool": False, "experiment_metric_computation_bool": False, "source_candidate_corpus_scan_bool": False, "runtime_retrieval_ci_network_provider_clone_bool": False, "raw_private_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bfgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bfsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bfreadback0000", **rb}], "stop_go_records": [stop]}
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
    for f, e in {"locked_haae_r2be_checkpoint": R2BE_CHECKPOINT, "locked_haae_r2be_status": R2BE_STATUS, "locked_haae_r2be_self_test_total": R2BE_SELF_TEST_TOTAL, "locked_haae_r2bd_checkpoint": R2BD_CHECKPOINT, "locked_haae_r2bc_checkpoint": R2BC_CHECKPOINT, "locked_haae_r2bb_checkpoint": R2BB_CHECKPOINT, "locked_haae_r2ba_checkpoint": R2BA_CHECKPOINT, "locked_haae_r2az_checkpoint": R2AZ_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    audit = (report.get("r2be_material_audit_records") or [{}])[0]
    for f in ["r2be_explicit_local_generation_bool", "allowlist_boundary_pass_bool", "root_safety_public_attestation_pass_bool", "schema_group_exact_bool", "control_family_exact_bool", "bounds_satisfied_bool", "gold_isolation_bool", "no_experiment_metrics_bool", "aggregate_only_publication_bool"]:
        if audit.get(f) is not True: issues.append(f"audit_{f}")
    if audit.get("group_presence_bucket") != "all_required_groups_present": issues.append("audit_group_presence_bucket")
    boundary = (report.get("privacy_boundary_records") or [{}])[0]
    if boundary.get("public_only_audit_bool") is not True or boundary.get("read_only_r2be_public_artifact_bool") is not True: issues.append("public_only_boundary_mismatch")
    for f in ["private_root_read_bool", "private_material_read_bool", "material_regeneration_bool", "experiment_metric_computation_bool", "source_candidate_corpus_scan_bool", "runtime_retrieval_ci_network_provider_clone_bool", "raw_private_publication_bool"]:
        if boundary.get(f) is not False: issues.append(f"privacy_{f}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2bg_stop_go_mismatch")
    for f in STOP_TRUE:
        if stop.get(f) is not True: issues.append(f"stop_true_{f}")
    for f in STOP_FALSE:
        if stop.get(f) is not False: issues.append(f"overauthorization_{f}")
    rb = report.get("public_readback_records", [])
    if len(rb) != 1 or rb[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
    for g in report.get("pass_fail_gate_records", []):
        if g.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{g.get('gate_bucket', 'unknown')}")
    return issues

def write_report(report: dict[str, Any], out: Path | None = None) -> Path:
    path = out or PUBLIC_REPORT_PATH; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    def check(n: str, c: bool) -> None:
        if not c: failures.append(n)
    r2be = load_json(repo_root() / R2BE_REPORT_PATH); passed = build_report(r2be); check("audit_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    source_mut = [("r2be_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bd_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2be_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE), ("r2be_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE), ("r2be_forbidden_scan_fail", lambda r: r["forbidden_scan"].__setitem__("status", "fail"), STATUS_FAIL_SOURCE), ("r2be_source_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("source_locked_bool", False), STATUS_FAIL_SOURCE)]
    for n, mut, st in source_mut:
        m = json.loads(json.dumps(r2be)); mut(m); check(n, build_report(m)["status"] == st)
    audit_mut = [("r2be_execution_mode_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("execution_mode_bucket", "default")), ("r2be_private_read_drift_fail", lambda r: r["execution_mode_records"][0].__setitem__("private_read_bool", True)), ("r2be_allowlist_boundary_drift_fail", lambda r: r["allowlist_records"][0].__setitem__("tmp_scan_bool", True)), ("r2be_schema_group_drop_fail", lambda r: r["generated_group_records"][0]["required_group_buckets"].pop()), ("r2be_schema_group_duplicate_fail", lambda r: r["generated_group_records"][0]["required_group_buckets"].append(GROUPS[0])), ("r2be_control_family_drop_fail", lambda r: r["control_family_records"][0]["required_control_family_buckets"].pop()), ("r2be_control_family_duplicate_fail", lambda r: r["control_family_records"][0]["required_control_family_buckets"].append(CONTROL_FAMILIES[0])), ("r2be_bounds_drift_fail", lambda r: r["bounds_records"][0].__setitem__("target_tasks_bucket", "bad")), ("r2be_gold_policy_drift_fail", lambda r: r["gold_isolation_records"][0].__setitem__("gold_used_for_ranking_bool", True)), ("r2be_metric_overauth_fail", lambda r: r["no_metric_records"][0].__setitem__("experiment_metrics_bool", True)), ("r2be_publication_leak_fail", lambda r: r["publication_records"][0].__setitem__("exact_counts_rates_scores_public_bool", True)), ("r2be_gate_drop_fail", lambda r: r["pass_fail_gate_records"].pop()), ("r2be_gate_duplicate_fail", lambda r: r["pass_fail_gate_records"].append(r["pass_fail_gate_records"][0])), ("r2be_synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop()), ("r2be_synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(r["synthetic_validator_records"][0])), ("r2be_readback_drop_fail", lambda r: r.__setitem__("public_readback_records", [])), ("r2be_stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(R2BE_STOP_TRUE[0], False)), ("r2be_stop_go_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True)), ("r2be_stop_go_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True))]
    for n, mut in audit_mut:
        m = json.loads(json.dumps(r2be)); mut(m); check(n, build_report(m)["status"] == STATUS_FAIL_AUDIT)
    report_mut = [("source_locked_record_false_fail", lambda r: r["source_lock_records"][0].__setitem__("source_locked_bool", False), "source_locked_bool"), ("source_inherited_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2az_checkpoint", "bad"), "source_locked_haae_r2az_checkpoint"), ("audit_root_attestation_drift_fail", lambda r: r["r2be_material_audit_records"][0].__setitem__("root_safety_public_attestation_pass_bool", False), "audit_root_safety_public_attestation_pass_bool"), ("audit_group_presence_drift_fail", lambda r: r["r2be_material_audit_records"][0].__setitem__("group_presence_bucket", "missing"), "audit_group_presence_bucket"), ("r2bg_stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("r2bg_stop_go_private_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("r2bg_stop_go_scale_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_preflight_authorized_bool", True), "overauthorization_scale_preflight_authorized_bool"), ("public_only_boundary_drift_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("private_root_read_bool", True), "privacy_private_root_read_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(r["pass_fail_gate_records"][0]), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(r["synthetic_validator_records"][0]), "synthetic_validator_duplicate_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    for n, mut, issue in report_mut:
        m = json.loads(json.dumps(passed)); mut(m); check(n, issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    if args["self_test"]:
        res = run_self_test(); print(json.dumps(res, indent=2, sort_keys=True)); return 0 if res["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo_root() / public_artifact_path(str(args["validate"]))); issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] == STATUS_PASS else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
