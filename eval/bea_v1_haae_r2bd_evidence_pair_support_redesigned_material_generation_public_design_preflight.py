#!/usr/bin/env python3
"""BEA-v1-HAAE-R2BD redesigned material generation public design preflight.

Public-only, non-executing. Converts R2BC redesign requirements into a
fail-closed contract for future explicit local redesigned material generation.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2BD Evidence-Pair Support Redesigned Material Generation Public Design Preflight"
SLUG = "bea_v1_haae_r2bd_evidence_pair_support_redesigned_material_generation_public_design_preflight"
SCHEMA_VERSION = f"{SLUG}_public_report_v1"
PUBLIC_REPORT_PATH = Path("artifacts") / SLUG / f"{SLUG}_report.json"
R2BC_REPORT_PATH = Path("artifacts/bea_v1_haae_r2bc_evidence_pair_support_mechanism_redesign_public_design_preflight/bea_v1_haae_r2bc_evidence_pair_support_mechanism_redesign_public_design_preflight_report.json")
R2BA_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ba_evidence_pair_support_robustness_experiment_public_audit_package/bea_v1_haae_r2ba_evidence_pair_support_robustness_experiment_public_audit_package_report.json")
R2AZ_REPORT_PATH = Path("artifacts/bea_v1_haae_r2az_evidence_pair_support_explicit_local_robustness_experiment/bea_v1_haae_r2az_evidence_pair_support_explicit_local_robustness_experiment_report.json")

R2BC_CHECKPOINT = "2171b20"
R2BC_STATUS = "haae_r2bc_evidence_pair_support_mechanism_redesign_public_design_preflight_complete_r2bd_redesigned_material_generation_public_design_preflight_authorized"
R2BC_SELF_TEST_TOTAL = 37
R2BB_CHECKPOINT = "a624728"
R2BB_STATUS = "haae_r2bb_evidence_pair_support_robustness_next_step_decision_complete_r2bc_mechanism_redesign_public_design_preflight_authorized"
R2BB_SELF_TEST_TOTAL = 34
R2BA_CHECKPOINT = "f8984bf"
R2BA_STATUS = "haae_r2ba_evidence_pair_support_robustness_experiment_public_audit_complete_r2bb_next_step_decision_authorized_negative_robustness_evidence"
R2BA_SELF_TEST_TOTAL = 34
R2AZ_CHECKPOINT = "72590e5"
R2AZ_STATUS = "haae_r2az_explicit_local_robustness_experiment_complete_r2ba_public_audit_authorized_artifact_likely"
R2AY_CHECKPOINT = "126dc18"
R2AX_CHECKPOINT = "f3add65"
R2AW_CHECKPOINT = "bc44454"
R2AN_CHECKPOINT = "93bba5f"
R2AT_CHECKPOINT = "0c9c108"
R2AP_CHECKPOINT = "87ea9de"

STATUS_PASS = "haae_r2bd_evidence_pair_support_redesigned_material_generation_public_design_preflight_complete_r2be_explicit_local_redesigned_material_generation_authorized"
STATUS_FAIL_SOURCE = "haae_r2bd_fail_closed_source_lock_or_redesign_mismatch"
STATUS_FAIL_CONTRACT = "haae_r2bd_fail_closed_future_r2be_contract_mismatch"
STATUS_FAIL_PRIVACY = "haae_r2bd_fail_closed_public_privacy_leak"
STATUS_FAIL_READBACK = "haae_r2bd_fail_closed_public_readback_mismatch"
NEXT_PHASE = "BEA-v1-HAAE-R2BE Evidence-Pair Support Explicit Local Redesigned Material Generation"

SCHEMA_GROUPS = ["redesigned_task_frame", "redesigned_source_manifest_private", "redesigned_evidence_unit_pool", "redesigned_support_pair_material", "redesigned_control_pair_material", "redesigned_path_confound_material", "redesigned_gold_isolation_eval_private", "redesigned_material_qa"]
CONTROL_FAMILIES = ["matched_hard_negative_control", "same_source_family_control", "cross_task_semantic_mismatch_control", "path_token_matched_control", "query_only_control", "evidence_only_control", "support_relation_broken_control", "gold_blind_decoy_control", "source_family_balance_control"]
BOUNDS = {"target_tasks_bucket": "target_tasks_16_to_20", "private_rows_bucket": "private_rows_le_20000", "depth_bucket": "depth_le_40", "support_pairs_bucket": "support_pairs_le_120_per_task", "control_pairs_bucket": "control_pairs_le_120_per_task", "total_pairs_bucket": "total_pairs_le_240_per_task", "source_files_bucket": "source_files_le_500", "wall_clock_bucket": "wall_clock_le_20_minutes"}
NEGATIVE = {"r2az_result_bucket": "artifact_likely", "support_control_separation_bucket": "support_control_separation_collapsed", "control_rejection_bucket": "control_rejection_failed", "path_confound_risk_bucket": "path_confound_risk_elevated", "support_signal_bucket": "support_signal_bucket_low"}
R2BC_GATES = ["r2bb_source_lock_decision_gate", "r2ba_negative_audit_lock_gate", "r2az_bucket_lock_gate", "inherited_source_lock_gate", "control_family_exact_set_gate", "path_confound_mitigation_gate", "gold_isolation_policy_gate", "support_control_gate_design_gate", "future_generation_contract_bounds_gate", "public_only_non_executing_gate", "r2bd_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
R2BC_SYNTH = ["preflight_pass", "safe_parser_fail", "r2bb_checkpoint_drift_fail", "r2bb_status_drift_fail", "r2bb_self_test_drift_fail", "r2bb_forbidden_scan_fail", "r2bb_decision_drop_fail", "r2bb_scale_overselect_fail", "r2bb_boundary_drift_fail", "r2bb_gate_drop_fail", "r2bb_gate_duplicate_fail", "r2bb_synthetic_drop_fail", "r2bb_readback_drop_fail", "r2bb_stop_go_overauth_fail", "r2ba_status_drift_fail", "r2az_bucket_drift_fail", "source_inherited_lock_drift_fail", "context_bucket_drift_fail", "privacy_boundary_overauth_fail", "control_family_missing_fail", "control_family_duplicate_fail", "path_mitigation_drop_fail", "gold_isolation_drop_fail", "support_control_gate_drop_fail", "future_bounds_drift_fail", "future_control_family_missing_fail", "future_execution_overauth_fail", "stop_go_true_drop_fail", "stop_go_private_read_overauth_fail", "stop_go_explicit_generation_overauth_fail", "stop_go_downstream_claim_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "public_leak_fail"]
R2BC_STOP_TRUE = ["haae_r2bd_evidence_pair_support_redesigned_material_generation_public_design_preflight_authorized_bool", "r2bd_public_only_generation_design_preflight_bool", "mechanism_redesign_requirements_complete_bool", "current_support_route_robustness_rejected_bool", "negative_robustness_evidence_locked_bool", "future_explicit_opt_in_generation_design_only_bool", "no_private_read_bool", "no_metric_recompute_bool", "no_material_generation_bool", "no_method_default_scale_validated_signal_claim_bool"]
R2BC_STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "experiment_execution_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "external_validation_authorized_bool", "scale_preflight_authorized_bool", "scale_execution_authorized_bool", "explicit_private_generation_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "validated_signal_claim_authorized_bool", "downstream_value_claim_authorized_bool", "raw_publication_authorized_bool"]

GATES = ["r2bc_source_lock_gate", "r2bc_redesign_requirement_gate", "negative_evidence_lock_gate", "future_schema_group_exact_gate", "future_control_family_exact_gate", "future_bounds_exact_gate", "future_source_allowlist_gate", "future_root_safety_gate", "future_gold_isolation_gate", "future_no_metric_gate", "future_publication_gate", "r2be_stop_go_only_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTH = ["preflight_pass", "safe_parser_fail", "r2bc_checkpoint_drift_fail", "r2bc_full_source_lock_drift_fail", "r2bc_status_drift_fail", "r2bc_self_test_drift_fail", "r2bc_forbidden_scan_fail", "r2bc_control_family_drop_fail", "r2bc_bound_drift_fail", "r2bc_gold_policy_drift_fail", "r2bc_privacy_boundary_drift_fail", "r2bc_synthetic_drop_fail", "r2bc_synthetic_duplicate_fail", "r2bc_stop_go_overauth_fail", "r2ba_lock_drift_fail", "r2az_negative_bucket_drift_fail", "source_inherited_lock_drift_fail", "source_locked_bool_fail", "negative_evidence_bucket_drift_fail", "privacy_boundary_overauth_fail", "r2bc_audit_record_drift_fail", "schema_group_missing_fail", "schema_group_extra_fail", "schema_group_duplicate_fail", "control_family_missing_fail", "control_family_extra_fail", "control_family_duplicate_fail", "bound_drift_fail", "schema_exact_flag_fail", "control_exact_flag_fail", "bounds_locked_flag_fail", "allowlist_weakening_fail", "root_safety_weakening_fail", "gold_isolation_weakening_fail", "no_metric_weakening_fail", "publication_weakening_fail", "stop_go_true_drop_fail", "stop_go_private_read_overauth_fail", "stop_go_metric_overauth_fail", "stop_go_scale_overauth_fail", "stop_go_implicit_tmp_overauth_fail", "gate_set_fail", "duplicate_gate_fail", "synthetic_set_fail", "duplicate_synthetic_fail", "readback_record_fail", "public_leak_fail"]
SELF_TEST_EXPECTED = len(SYNTH)
STOP_TRUE = ["haae_r2be_evidence_pair_support_explicit_local_redesigned_material_generation_authorized_bool", "r2be_scoped_explicit_opt_in_material_generation_bool", "r2be_requires_operator_provided_public_source_allowlist_bool", "r2be_requires_explicit_private_output_root_bool", "r2be_requires_root_ownership_and_symlink_safety_bool", "r2be_redesigned_schema_bounds_locked_bool", "r2be_no_experiment_metrics_bool", "r2be_aggregate_only_publication_required_bool", "negative_robustness_evidence_locked_bool", "current_support_route_robustness_rejected_bool", "no_method_default_scale_validated_signal_claim_bool"]
STOP_FALSE = ["private_read_authorized_bool", "private_write_authorized_bool", "material_generation_authorized_bool", "experiment_execution_authorized_bool", "metric_recompute_authorized_bool", "source_scan_authorized_bool", "candidate_scan_authorized_bool", "corpus_scan_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "retrieval_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "external_validation_authorized_bool", "scale_preflight_authorized_bool", "scale_execution_authorized_bool", "default_claim_authorized_bool", "method_claim_authorized_bool", "winner_claim_authorized_bool", "validated_signal_claim_authorized_bool", "downstream_value_claim_authorized_bool", "raw_publication_authorized_bool", "broad_private_read_authorized_bool", "implicit_private_root_discovery_authorized_bool", "implicit_tmp_discovery_authorized_bool"]
LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|root basename|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"", re.I)), ("raw_private_key", re.compile(r"private_task_ref|private_pair_ref|private_evidence_unit_ref|source_ref|filepath_value|source_filename_value|directory_value|snippet_value|line_number_value|gold_label_value|hard_negative_value|hash_value|\.rs\b|crates/openlocus-", re.I)), ("exact_metric", re.compile(r"exact_count_value|exact_rate_value|exact_score_value|private_score_value|exact_top_k_value|\bmrr\b|hit-rate|\b\d+\.\d+\b|\b[a-f0-9]{32,64}\b", re.I))]

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
    repo = Path(__file__).resolve().parents[1]; p = Path(value); resolved = p if p.is_absolute() else repo / p
    if resolved != repo / PUBLIC_REPORT_PATH: raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH

def audit_r2bc(r2bc: dict[str, Any]) -> dict[str, bool]:
    src = (r2bc.get("source_lock_records") or [{}])[0]; req = (r2bc.get("redesign_requirement_records") or [{}])[0]; fam = (r2bc.get("control_family_requirement_records") or [{}])[0]; fut = (r2bc.get("future_generation_contract_records") or [{}])[0]; gold = (r2bc.get("gold_isolation_policy_records") or [{}])[0]; path = (r2bc.get("path_confound_mitigation_records") or [{}])[0]; sup = (r2bc.get("support_control_gate_records") or [{}])[0]; stop = (r2bc.get("stop_go_records") or [{}])[0]; privacy = (r2bc.get("privacy_boundary_records") or [{}])[0]
    gates = [r.get("gate_bucket") for r in r2bc.get("pass_fail_gate_records", [])]; synth = [r.get("validator_bucket") for r in r2bc.get("synthetic_validator_records", [])]; read = r2bc.get("public_readback_records", [])
    source_ok = (
        r2bc.get("status") == R2BC_STATUS
        and r2bc.get("self_test_total") == R2BC_SELF_TEST_TOTAL
        and r2bc.get("forbidden_scan", {}).get("status") == "pass"
        and src.get("locked_haae_r2bb_checkpoint") == R2BB_CHECKPOINT
        and src.get("locked_haae_r2bb_status") == R2BB_STATUS
        and src.get("locked_haae_r2bb_self_test_total") == R2BB_SELF_TEST_TOTAL
        and src.get("locked_haae_r2ba_checkpoint") == R2BA_CHECKPOINT
        and src.get("locked_haae_r2ba_status") == R2BA_STATUS
        and src.get("locked_haae_r2ba_self_test_total") == R2BA_SELF_TEST_TOTAL
        and src.get("locked_haae_r2az_checkpoint") == R2AZ_CHECKPOINT
        and src.get("locked_haae_r2az_status") == R2AZ_STATUS
        and src.get("locked_inherited_r2ay_checkpoint") == R2AY_CHECKPOINT
        and src.get("locked_inherited_r2ax_checkpoint") == R2AX_CHECKPOINT
        and src.get("locked_inherited_r2aw_checkpoint") == R2AW_CHECKPOINT
        and src.get("locked_inherited_r2an_checkpoint") == R2AN_CHECKPOINT
        and src.get("locked_inherited_r2at_checkpoint") == R2AT_CHECKPOINT
        and src.get("locked_inherited_r2ap_checkpoint") == R2AP_CHECKPOINT
        and src.get("source_locked_bool") is True
    )
    privacy_ok = privacy.get("public_only_non_executing_bool") is True and all(privacy.get(f) is False for f in ["private_read_bool", "private_write_bool", "material_generation_bool", "metric_recompute_bool", "source_candidate_corpus_scan_bool", "runtime_retrieval_ci_network_provider_clone_bool", "raw_exact_private_publication_bool"])
    redesign_ok = req.get("existing_support_complementarity_insufficient_after_robustness_failure_bool") is True and req.get("robust_signal_claimed_bool") is False and set(fam.get("required_control_family_buckets", [])) == set(CONTROL_FAMILIES) and len(fam.get("required_control_family_buckets", [])) == len(CONTROL_FAMILIES)
    bounds_ok = all(fut.get(k) == v for k, v in BOUNDS.items()) and set(fut.get("required_control_family_buckets", [])) == set(CONTROL_FAMILIES) and fut.get("execution_authorization_bool") is False
    policy_ok = gold.get("gold_eval_only_bool") is True and gold.get("public_only_pass_fail_bucket_bool") is True and path.get("elevated_confound_fails_robust_signal_gates_bool") is True and sup.get("any_core_failure_means_artifact_weak_inconclusive_not_support_signal_bool") is True
    integrity_ok = set(gates) == set(R2BC_GATES) and len(gates) == len(R2BC_GATES) and len(gates) == len(set(gates)) and set(synth) == set(R2BC_SYNTH) and len(synth) == len(R2BC_SYNTH) and len(synth) == len(set(synth)) and len(read) == 1 and read[0].get("all_public_readback_match_bool") is True
    stop_ok = stop.get("next_allowed_phase") == PHASE and all(stop.get(f) is True for f in R2BC_STOP_TRUE) and all(stop.get(f, False) is False for f in R2BC_STOP_FALSE)
    return {"source_ok": source_ok, "privacy_ok": privacy_ok, "redesign_ok": redesign_ok, "bounds_ok": bounds_ok, "policy_ok": policy_ok, "integrity_ok": integrity_ok, "stop_ok": stop_ok, "audit_ok": source_ok and privacy_ok and redesign_ok and bounds_ok and policy_ok and integrity_ok and stop_ok}

def audit_r2ba_r2az(r2ba: dict[str, Any] | None, r2az: dict[str, Any] | None) -> bool:
    if not r2ba or not r2az: return False
    m = (r2az.get("aggregate_metric_records") or [{}])[0]
    return r2ba.get("status") == R2BA_STATUS and r2ba.get("self_test_total") == R2BA_SELF_TEST_TOTAL and r2az.get("status") == R2AZ_STATUS and m.get("robustness_result_bucket") == "artifact_likely" and m.get("support_vs_control_robustness_separation_bucket") == "support_control_separation_collapsed" and m.get("shuffled_cross_task_control_rejection_bucket") == "control_rejection_failed" and m.get("path_token_confound_risk_bucket") == "path_confound_risk_elevated" and m.get("support_signal_retention_bucket") == "support_signal_bucket_low"

def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2BC_CHECKPOINT, R2BC_STATUS, R2BB_CHECKPOINT, R2BA_CHECKPOINT, R2AZ_CHECKPOINT, "future R2BE private schema groups", "redesigned_task_frame", "redesigned_control_pair_material", "matched_hard_negative_control", "path_token_matched_control", "target_tasks_16_to_20", "operator-provided public source allowlist", "root ownership and symlink safety", "gold eval-only", "material generation only; no robustness metrics", "aggregate-only publication", NEXT_PHASE]
    spaced = [f"{total} / {total}" if x == f"{total}/{total}" else x for x in fragments]
    def read(rel: str) -> str:
        p = repo / rel; return p.read_text(encoding="utf-8") if p.exists() else ""
    def ok(text: str) -> bool: return all(f in text for f in fragments) or all(f in text for f in spaced)
    root = read("docs/current-research-conclusions.md")
    out = {"readme_readback_match_bool": ok(read("README.md")), "detail_docs_readback_match_bool": ok(read("docs/en/bea-v1-haae-r2bd-evidence-pair-support-redesigned-material-generation-public-design-preflight.md")) and ok(read("docs/zh/bea-v1-haae-r2bd-evidence-pair-support-redesigned-material-generation-public-design-preflight.md")), "current_conclusions_readback_match_bool": ok(root) and ok(read("docs/en/current-research-conclusions.md")) and ok(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2bd-evidence-pair-support-redesigned-material-generation-public-design-preflight.md" in root, "research_log_readback_match_bool": ok(read("docs/en/research-log.md")) and ok(read("docs/zh/research-log.md")), "research_summary_readback_match_bool": ok(read("docs/en/research-summary.md")) and ok(read("docs/zh/research-summary.md"))}
    out["all_public_readback_match_bool"] = all(out.values()); return out

def contract_records() -> dict[str, Any]:
    return {
        "future_r2be_schema_contract_records": [{"anonymous_schema_contract_id": "haaer2bdschema0000", "required_private_group_buckets": SCHEMA_GROUPS, "schema_group_set_exact_bool": True}],
        "future_r2be_control_family_contract_records": [{"anonymous_control_contract_id": "haaer2bdcontrol0000", "required_control_family_buckets": CONTROL_FAMILIES, "control_family_set_exact_bool": True}],
        "future_r2be_bounds_contract_records": [{"anonymous_bounds_contract_id": "haaer2bdbounds0000", **BOUNDS, "bounds_locked_bool": True}],
        "future_r2be_source_allowlist_contract_records": [{"anonymous_allowlist_contract_id": "haaer2bdallow0000", "operator_provided_public_source_allowlist_required_bool": True, "implicit_source_discovery_rejected_bool": True, "tmp_scanning_rejected_bool": True, "repo_wide_source_candidate_corpus_scan_rejected_bool": True, "network_provider_clone_retrieval_rejected_bool": True, "unbounded_corpus_traversal_rejected_bool": True, "outside_allowlist_source_files_rejected_bool": True, "rows_without_allowlist_provenance_bucket_rejected_bool": True, "public_artifact_paths_filenames_forbidden_bool": True}],
        "future_r2be_root_safety_contract_records": [{"anonymous_root_contract_id": "haaer2bdroot0000", "explicit_operator_flag_required_bool": True, "private_output_root_outside_repo_required_bool": True, "root_not_repo_workspace_bool": True, "root_not_nested_under_repo_bool": True, "root_not_symlink_bool": True, "no_symlink_group_dirs_files_bool": True, "path_traversal_rejected_bool": True, "overwrite_only_with_matching_owned_manifest_bool": True, "owner_manifest_written_verified_bool": True, "group_dirs_owned_by_current_run_bool": True, "owned_group_symlink_escape_rejected_bool": True, "unowned_existing_groups_rejected_bool": True, "missing_ownership_manifest_on_overwrite_rejected_bool": True, "public_artifact_no_root_path_basename_bool": True}],
        "future_r2be_gold_isolation_contract_records": [{"anonymous_gold_contract_id": "haaer2bdgold0000", "gold_eval_only_bool": True, "gold_used_for_source_material_selection_bool": False, "gold_used_for_pair_control_construction_bool": False, "gold_used_for_retrieval_ranking_source_scan_candidate_generation_bool": False, "public_only_aggregate_pass_fail_bucket_bool": True}],
        "future_r2be_no_metric_contract_records": [{"anonymous_no_metric_contract_id": "haaer2bdnometric0000", "material_generation_only_bool": True, "robustness_metrics_bool": False, "hit_rates_mrr_ranks_scores_rates_bool": False, "support_control_separation_metrics_bool": False, "interpretation_mechanism_scores_bool": False, "experiment_outcomes_bool": False, "material_qa_aggregates_only_bool": True}],
        "future_r2be_publication_contract_records": [{"anonymous_publication_contract_id": "haaer2bdpub0000", "aggregate_only_publication_bool": True, "schema_presence_buckets_allowed_bool": True, "group_presence_booleans_allowed_bool": True, "count_range_buckets_allowed_bool": True, "control_family_coverage_bucket_allowed_bool": True, "bounds_satisfied_booleans_allowed_bool": True, "root_safety_booleans_allowed_bool": True, "gold_isolation_booleans_allowed_bool": True, "no_metric_booleans_allowed_bool": True, "forbidden_scan_status_allowed_bool": True, "raw_private_rows_forbidden_bool": True, "raw_diagnostics_forbidden_bool": True, "task_query_source_evidence_pair_ids_forbidden_bool": True, "snippets_gold_labels_hashes_paths_filenames_forbidden_bool": True, "exact_counts_rates_ranks_scores_mrr_topk_forbidden_bool": True}],
    }

def build_report(r2bc: dict[str, Any] | None = None, r2ba: dict[str, Any] | None = None, r2az: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2bc is None:
        try: r2bc = load_json(repo / R2BC_REPORT_PATH)
        except Exception: r2bc = {}
    if r2ba is None:
        try: r2ba = load_json(repo / R2BA_REPORT_PATH)
        except Exception: r2ba = None
    if r2az is None:
        try: r2az = load_json(repo / R2AZ_REPORT_PATH)
        except Exception: r2az = None
    audit = audit_r2bc(r2bc); neg_ok = audit_r2ba_r2az(r2ba, r2az); rb = public_readback_match(self_test_total); contracts = contract_records()
    status = STATUS_FAIL_SOURCE if not audit["source_ok"] else (STATUS_FAIL_CONTRACT if not (audit["audit_ok"] and neg_ok) else (STATUS_FAIL_READBACK if not rb["all_public_readback_match_bool"] else STATUS_PASS))
    passed = status == STATUS_PASS
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2bdstop0000", "next_allowed_phase": NEXT_PHASE if passed else "not_authorized_until_public_design_preflight_pass"}; stop.update({f: passed for f in STOP_TRUE}); stop.update({f: False for f in STOP_FALSE})
    gatevals = {"r2bc_source_lock_gate": audit["source_ok"], "r2bc_redesign_requirement_gate": audit["redesign_ok"], "negative_evidence_lock_gate": neg_ok, "future_schema_group_exact_gate": True, "future_control_family_exact_gate": True, "future_bounds_exact_gate": True, "future_source_allowlist_gate": True, "future_root_safety_gate": True, "future_gold_isolation_gate": True, "future_no_metric_gate": True, "future_publication_gate": True, "r2be_stop_go_only_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": rb["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bdsource0000", "locked_haae_r2bc_checkpoint": R2BC_CHECKPOINT, "locked_haae_r2bc_status": R2BC_STATUS, "locked_haae_r2bc_self_test_total": R2BC_SELF_TEST_TOTAL, "locked_haae_r2bb_checkpoint": R2BB_CHECKPOINT, "locked_haae_r2bb_status": R2BB_STATUS, "locked_haae_r2bb_self_test_total": R2BB_SELF_TEST_TOTAL, "locked_haae_r2ba_checkpoint": R2BA_CHECKPOINT, "locked_haae_r2ba_status": R2BA_STATUS, "locked_haae_r2ba_self_test_total": R2BA_SELF_TEST_TOTAL, "locked_haae_r2az_checkpoint": R2AZ_CHECKPOINT, "locked_haae_r2az_status": R2AZ_STATUS, "locked_inherited_r2ay_checkpoint": R2AY_CHECKPOINT, "locked_inherited_r2ax_checkpoint": R2AX_CHECKPOINT, "locked_inherited_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT, "source_locked_bool": audit["source_ok"]}],
        "r2bc_redesign_audit_records": [{"anonymous_redesign_audit_id": "haaer2bdaudit0000", "r2bc_public_only_boundary_bool": audit["privacy_ok"], "r2bc_control_families_exact_bool": audit["redesign_ok"], "r2bc_future_design_only_bounds_bool": audit["bounds_ok"], "r2bc_gold_isolation_bool": audit["policy_ok"], "r2bc_stop_go_only_to_r2bd_bool": audit["stop_ok"], "r2bc_gate_synthetic_readback_exact_bool": audit["integrity_ok"]}],
        "negative_evidence_lock_records": [{"anonymous_negative_evidence_id": "haaer2bdnegative0000", **NEGATIVE, "negative_evidence_locked_bool": neg_ok}],
        "privacy_boundary_records": [{"anonymous_privacy_boundary_id": "haaer2bdprivacy0000", "public_only_non_executing_bool": True, "private_root_material_read_bool": False, "private_material_write_bool": False, "material_generation_bool": False, "metric_compute_recompute_bool": False, "source_candidate_corpus_scan_bool": False, "runtime_retrieval_ci_network_provider_clone_bool": False, "raw_exact_private_publication_bool": False, "method_default_scale_validated_downstream_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bdgate{i:04d}", "gate_bucket": g, "gate_passed_bool": bool(gatevals.get(g, False)), "gate_public_artifact_bool": True} for i, g in enumerate(GATES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bdsynth{i:04d}", "validator_bucket": v} for i, v in enumerate(SYNTH)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2bdreadback0000", **rb}],
        "stop_go_records": [stop]}
    report.update(contracts)
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
    for f, e in {"locked_haae_r2bc_checkpoint": R2BC_CHECKPOINT, "locked_haae_r2bc_status": R2BC_STATUS, "locked_haae_r2bc_self_test_total": R2BC_SELF_TEST_TOTAL, "locked_haae_r2bb_checkpoint": R2BB_CHECKPOINT, "locked_haae_r2bb_status": R2BB_STATUS, "locked_haae_r2bb_self_test_total": R2BB_SELF_TEST_TOTAL, "locked_haae_r2ba_checkpoint": R2BA_CHECKPOINT, "locked_haae_r2ba_status": R2BA_STATUS, "locked_haae_r2ba_self_test_total": R2BA_SELF_TEST_TOTAL, "locked_haae_r2az_checkpoint": R2AZ_CHECKPOINT, "locked_haae_r2az_status": R2AZ_STATUS, "locked_inherited_r2ay_checkpoint": R2AY_CHECKPOINT, "locked_inherited_r2ax_checkpoint": R2AX_CHECKPOINT, "locked_inherited_r2aw_checkpoint": R2AW_CHECKPOINT, "locked_inherited_r2an_checkpoint": R2AN_CHECKPOINT, "locked_inherited_r2at_checkpoint": R2AT_CHECKPOINT, "locked_inherited_r2ap_checkpoint": R2AP_CHECKPOINT}.items():
        if src.get(f) != e: issues.append(f"source_{f}")
    if src.get("source_locked_bool") is not True: issues.append("source_locked_bool")
    audit = (report.get("r2bc_redesign_audit_records") or [{}])[0]
    for f in ["r2bc_public_only_boundary_bool", "r2bc_control_families_exact_bool", "r2bc_future_design_only_bounds_bool", "r2bc_gold_isolation_bool", "r2bc_stop_go_only_to_r2bd_bool", "r2bc_gate_synthetic_readback_exact_bool"]:
        if audit.get(f) is not True: issues.append(f"r2bc_audit_{f}")
    neg = (report.get("negative_evidence_lock_records") or [{}])[0]
    for f, e in NEGATIVE.items():
        if neg.get(f) != e: issues.append(f"negative_{f}")
    if neg.get("negative_evidence_locked_bool") is not True: issues.append("negative_evidence_locked_bool")
    privacy = (report.get("privacy_boundary_records") or [{}])[0]
    if privacy.get("public_only_non_executing_bool") is not True: issues.append("privacy_public_only_non_executing_bool")
    for f in ["private_root_material_read_bool", "private_material_write_bool", "material_generation_bool", "metric_compute_recompute_bool", "source_candidate_corpus_scan_bool", "runtime_retrieval_ci_network_provider_clone_bool", "raw_exact_private_publication_bool", "method_default_scale_validated_downstream_claim_bool"]:
        if privacy.get(f) is not False: issues.append(f"privacy_{f}")
    schema = (report.get("future_r2be_schema_contract_records") or [{}])[0].get("required_private_group_buckets", [])
    if set(schema) != set(SCHEMA_GROUPS) or len(schema) != len(SCHEMA_GROUPS): issues.append("schema_group_set_mismatch")
    if (report.get("future_r2be_schema_contract_records") or [{}])[0].get("schema_group_set_exact_bool") is not True: issues.append("schema_group_exact_flag")
    fam = (report.get("future_r2be_control_family_contract_records") or [{}])[0].get("required_control_family_buckets", [])
    if set(fam) != set(CONTROL_FAMILIES) or len(fam) != len(CONTROL_FAMILIES): issues.append("control_family_set_mismatch")
    if (report.get("future_r2be_control_family_contract_records") or [{}])[0].get("control_family_set_exact_bool") is not True: issues.append("control_family_exact_flag")
    bounds = (report.get("future_r2be_bounds_contract_records") or [{}])[0]
    for k, v in BOUNDS.items():
        if bounds.get(k) != v: issues.append(f"bound_{k}")
    if bounds.get("bounds_locked_bool") is not True: issues.append("bounds_locked_flag")
    allow = (report.get("future_r2be_source_allowlist_contract_records") or [{}])[0]
    if any(allow.get(f) is not True for f in ["operator_provided_public_source_allowlist_required_bool", "implicit_source_discovery_rejected_bool", "tmp_scanning_rejected_bool", "repo_wide_source_candidate_corpus_scan_rejected_bool", "network_provider_clone_retrieval_rejected_bool", "unbounded_corpus_traversal_rejected_bool", "outside_allowlist_source_files_rejected_bool", "rows_without_allowlist_provenance_bucket_rejected_bool", "public_artifact_paths_filenames_forbidden_bool"]): issues.append("allowlist_contract_weakening")
    root = (report.get("future_r2be_root_safety_contract_records") or [{}])[0]
    if any(v is not True for k, v in root.items() if k != "anonymous_root_contract_id"): issues.append("root_safety_contract_weakening")
    gold = (report.get("future_r2be_gold_isolation_contract_records") or [{}])[0]
    if gold.get("gold_eval_only_bool") is not True or any(gold.get(f) is not False for f in ["gold_used_for_source_material_selection_bool", "gold_used_for_pair_control_construction_bool", "gold_used_for_retrieval_ranking_source_scan_candidate_generation_bool"]): issues.append("gold_contract_weakening")
    nomet = (report.get("future_r2be_no_metric_contract_records") or [{}])[0]
    if nomet.get("material_generation_only_bool") is not True or nomet.get("material_qa_aggregates_only_bool") is not True or any(nomet.get(f) is not False for f in ["robustness_metrics_bool", "hit_rates_mrr_ranks_scores_rates_bool", "support_control_separation_metrics_bool", "interpretation_mechanism_scores_bool", "experiment_outcomes_bool"]): issues.append("no_metric_contract_weakening")
    pub = (report.get("future_r2be_publication_contract_records") or [{}])[0]
    if pub.get("aggregate_only_publication_bool") is not True or pub.get("raw_private_rows_forbidden_bool") is not True or pub.get("exact_counts_rates_ranks_scores_mrr_topk_forbidden_bool") is not True: issues.append("publication_contract_weakening")
    stop = (report.get("stop_go_records") or [{}])[0]
    if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("r2be_stop_go_mismatch")
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


def run_self_test_hardened() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    bc = load_json(repo / R2BC_REPORT_PATH)
    ba = load_json(repo / R2BA_REPORT_PATH)
    az = load_json(repo / R2AZ_REPORT_PATH)

    def check(name: str, ok: bool) -> None:
        if not ok:
            failures.append(name)

    passed = build_report(bc, ba, az)
    check("preflight_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try:
        parse_args(["--bad"])
        check("safe_parser_fail", False)
    except ValueError:
        check("safe_parser_fail", True)

    source_mutations = [
        ("r2bc_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bb_checkpoint", "bad"), STATUS_FAIL_SOURCE),
        ("r2bc_full_source_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bb_status", "bad"), STATUS_FAIL_SOURCE),
        ("r2bc_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE),
        ("r2bc_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE),
        ("r2bc_forbidden_scan_fail", lambda r: r["forbidden_scan"].__setitem__("status", "fail"), STATUS_FAIL_SOURCE),
        ("r2bc_control_family_drop_fail", lambda r: r["control_family_requirement_records"][0]["required_control_family_buckets"].pop(), STATUS_FAIL_CONTRACT),
        ("r2bc_bound_drift_fail", lambda r: r["future_generation_contract_records"][0].__setitem__("target_tasks_bucket", "bad"), STATUS_FAIL_CONTRACT),
        ("r2bc_gold_policy_drift_fail", lambda r: r["gold_isolation_policy_records"][0].__setitem__("gold_eval_only_bool", False), STATUS_FAIL_CONTRACT),
        ("r2bc_privacy_boundary_drift_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("private_read_bool", True), STATUS_FAIL_CONTRACT),
        ("r2bc_synthetic_drop_fail", lambda r: r["synthetic_validator_records"].pop(), STATUS_FAIL_CONTRACT),
        ("r2bc_synthetic_duplicate_fail", lambda r: r["synthetic_validator_records"].append(r["synthetic_validator_records"][0]), STATUS_FAIL_CONTRACT),
        ("r2bc_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_CONTRACT),
    ]
    for name, mutate, expected_status in source_mutations:
        mutated = json.loads(json.dumps(bc))
        mutate(mutated)
        check(name, build_report(mutated, ba, az)["status"] == expected_status)

    mutated_ba = json.loads(json.dumps(ba))
    mutated_ba["status"] = "bad"
    check("r2ba_lock_drift_fail", build_report(bc, mutated_ba, az)["status"] == STATUS_FAIL_CONTRACT)
    mutated_az = json.loads(json.dumps(az))
    mutated_az["aggregate_metric_records"][0]["robustness_result_bucket"] = "bad"
    check("r2az_negative_bucket_drift_fail", build_report(bc, ba, mutated_az)["status"] == STATUS_FAIL_CONTRACT)

    report_mutations = [
        ("source_inherited_lock_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_inherited_r2at_checkpoint", "bad"), "source_locked_inherited_r2at_checkpoint"),
        ("source_locked_bool_fail", lambda r: r["source_lock_records"][0].__setitem__("source_locked_bool", False), "source_locked_bool"),
        ("negative_evidence_bucket_drift_fail", lambda r: r["negative_evidence_lock_records"][0].__setitem__("support_signal_bucket", "bad"), "negative_support_signal_bucket"),
        ("privacy_boundary_overauth_fail", lambda r: r["privacy_boundary_records"][0].__setitem__("material_generation_bool", True), "privacy_material_generation_bool"),
        ("r2bc_audit_record_drift_fail", lambda r: r["r2bc_redesign_audit_records"][0].__setitem__("r2bc_gate_synthetic_readback_exact_bool", False), "r2bc_audit_r2bc_gate_synthetic_readback_exact_bool"),
        ("schema_group_missing_fail", lambda r: r["future_r2be_schema_contract_records"][0]["required_private_group_buckets"].pop(), "schema_group_set_mismatch"),
        ("schema_group_extra_fail", lambda r: r["future_r2be_schema_contract_records"][0]["required_private_group_buckets"].append("extra"), "schema_group_set_mismatch"),
        ("schema_group_duplicate_fail", lambda r: r["future_r2be_schema_contract_records"][0]["required_private_group_buckets"].append(SCHEMA_GROUPS[0]), "schema_group_set_mismatch"),
        ("control_family_missing_fail", lambda r: r["future_r2be_control_family_contract_records"][0]["required_control_family_buckets"].pop(), "control_family_set_mismatch"),
        ("control_family_extra_fail", lambda r: r["future_r2be_control_family_contract_records"][0]["required_control_family_buckets"].append("extra"), "control_family_set_mismatch"),
        ("control_family_duplicate_fail", lambda r: r["future_r2be_control_family_contract_records"][0]["required_control_family_buckets"].append(CONTROL_FAMILIES[0]), "control_family_set_mismatch"),
        ("bound_drift_fail", lambda r: r["future_r2be_bounds_contract_records"][0].__setitem__("target_tasks_bucket", "bad"), "bound_target_tasks_bucket"),
        ("schema_exact_flag_fail", lambda r: r["future_r2be_schema_contract_records"][0].__setitem__("schema_group_set_exact_bool", False), "schema_group_exact_flag"),
        ("control_exact_flag_fail", lambda r: r["future_r2be_control_family_contract_records"][0].__setitem__("control_family_set_exact_bool", False), "control_family_exact_flag"),
        ("bounds_locked_flag_fail", lambda r: r["future_r2be_bounds_contract_records"][0].__setitem__("bounds_locked_bool", False), "bounds_locked_flag"),
        ("allowlist_weakening_fail", lambda r: r["future_r2be_source_allowlist_contract_records"][0].__setitem__("implicit_source_discovery_rejected_bool", False), "allowlist_contract_weakening"),
        ("root_safety_weakening_fail", lambda r: r["future_r2be_root_safety_contract_records"][0].__setitem__("root_not_symlink_bool", False), "root_safety_contract_weakening"),
        ("gold_isolation_weakening_fail", lambda r: r["future_r2be_gold_isolation_contract_records"][0].__setitem__("gold_used_for_pair_control_construction_bool", True), "gold_contract_weakening"),
        ("no_metric_weakening_fail", lambda r: r["future_r2be_no_metric_contract_records"][0].__setitem__("robustness_metrics_bool", True), "no_metric_contract_weakening"),
        ("publication_weakening_fail", lambda r: r["future_r2be_publication_contract_records"][0].__setitem__("raw_private_rows_forbidden_bool", False), "publication_contract_weakening"),
        ("stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"),
        ("stop_go_private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"),
        ("stop_go_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"),
        ("stop_go_scale_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_execution_authorized_bool", True), "overauthorization_scale_execution_authorized_bool"),
        ("stop_go_implicit_tmp_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("implicit_tmp_discovery_authorized_bool", True), "overauthorization_implicit_tmp_discovery_authorized_bool"),
        ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"),
        ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(r["pass_fail_gate_records"][0]), "gate_duplicate_mismatch"),
        ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"),
        ("duplicate_synthetic_fail", lambda r: r["synthetic_validator_records"].append(r["synthetic_validator_records"][0]), "synthetic_validator_duplicate_mismatch"),
        ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch"),
    ]
    for name, mutate, expected_issue in report_mutations:
        mutated = json.loads(json.dumps(passed))
        mutate(mutated)
        check(name, expected_issue in validate_report(mutated))

    leak = json.loads(json.dumps(passed))
    leak["debug"] = "/tmp/private-root r14m-001 private_pair_ref exact_score_value"
    check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def run_self_test() -> dict[str, Any]:
    failures: list[str] = []; repo = Path(__file__).resolve().parents[1]; bc = load_json(repo / R2BC_REPORT_PATH); ba = load_json(repo / R2BA_REPORT_PATH); az = load_json(repo / R2AZ_REPORT_PATH)
    def check(n: str, c: bool) -> None:
        if not c: failures.append(n)
    passed = build_report(bc, ba, az); check("preflight_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    try: parse_args(["--bad"]); check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    muts = [("r2bc_checkpoint_drift_fail", lambda r: r["source_lock_records"][0].__setitem__("locked_haae_r2bb_checkpoint", "bad"), STATUS_FAIL_SOURCE), ("r2bc_status_drift_fail", lambda r: r.__setitem__("status", "bad"), STATUS_FAIL_SOURCE), ("r2bc_self_test_drift_fail", lambda r: r.__setitem__("self_test_total", 0), STATUS_FAIL_SOURCE), ("r2bc_forbidden_scan_fail", lambda r: r["forbidden_scan"].__setitem__("status", "fail"), STATUS_FAIL_SOURCE), ("r2bc_control_family_drop_fail", lambda r: r["control_family_requirement_records"][0]["required_control_family_buckets"].pop(), STATUS_FAIL_CONTRACT), ("r2bc_bound_drift_fail", lambda r: r["future_generation_contract_records"][0].__setitem__("target_tasks_bucket", "bad"), STATUS_FAIL_CONTRACT), ("r2bc_gold_policy_drift_fail", lambda r: r["gold_isolation_policy_records"][0].__setitem__("gold_eval_only_bool", False), STATUS_FAIL_CONTRACT), ("r2bc_stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), STATUS_FAIL_CONTRACT)]
    for n, mut, st in muts:
        m = json.loads(json.dumps(bc)); mut(m); check(n, build_report(m, ba, az)["status"] == st)
    m = json.loads(json.dumps(ba)); m["status"] = "bad"; check("r2ba_lock_drift_fail", build_report(bc, m, az)["status"] == STATUS_FAIL_CONTRACT)
    m = json.loads(json.dumps(az)); m["aggregate_metric_records"][0]["robustness_result_bucket"] = "bad"; check("r2az_negative_bucket_drift_fail", build_report(bc, ba, m)["status"] == STATUS_FAIL_CONTRACT)
    report_mut = [("schema_group_missing_fail", lambda r: r["future_r2be_schema_contract_records"][0]["required_private_group_buckets"].pop(), "schema_group_set_mismatch"), ("schema_group_extra_fail", lambda r: r["future_r2be_schema_contract_records"][0]["required_private_group_buckets"].append("extra"), "schema_group_set_mismatch"), ("schema_group_duplicate_fail", lambda r: r["future_r2be_schema_contract_records"][0]["required_private_group_buckets"].append(SCHEMA_GROUPS[0]), "schema_group_set_mismatch"), ("control_family_missing_fail", lambda r: r["future_r2be_control_family_contract_records"][0]["required_control_family_buckets"].pop(), "control_family_set_mismatch"), ("control_family_extra_fail", lambda r: r["future_r2be_control_family_contract_records"][0]["required_control_family_buckets"].append("extra"), "control_family_set_mismatch"), ("control_family_duplicate_fail", lambda r: r["future_r2be_control_family_contract_records"][0]["required_control_family_buckets"].append(CONTROL_FAMILIES[0]), "control_family_set_mismatch"), ("bound_drift_fail", lambda r: r["future_r2be_bounds_contract_records"][0].__setitem__("target_tasks_bucket", "bad"), "bound_target_tasks_bucket"), ("allowlist_weakening_fail", lambda r: r["future_r2be_source_allowlist_contract_records"][0].__setitem__("implicit_source_discovery_rejected_bool", False), "allowlist_contract_weakening"), ("root_safety_weakening_fail", lambda r: r["future_r2be_root_safety_contract_records"][0].__setitem__("root_not_symlink_bool", False), "root_safety_contract_weakening"), ("gold_isolation_weakening_fail", lambda r: r["future_r2be_gold_isolation_contract_records"][0].__setitem__("gold_used_for_pair_control_construction_bool", True), "gold_contract_weakening"), ("no_metric_weakening_fail", lambda r: r["future_r2be_no_metric_contract_records"][0].__setitem__("robustness_metrics_bool", True), "no_metric_contract_weakening"), ("publication_weakening_fail", lambda r: r["future_r2be_publication_contract_records"][0].__setitem__("raw_private_rows_forbidden_bool", False), "publication_contract_weakening"), ("stop_go_true_drop_fail", lambda r: r["stop_go_records"][0].__setitem__(STOP_TRUE[0], False), f"stop_true_{STOP_TRUE[0]}"), ("stop_go_private_read_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("private_read_authorized_bool", True), "overauthorization_private_read_authorized_bool"), ("stop_go_metric_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("metric_recompute_authorized_bool", True), "overauthorization_metric_recompute_authorized_bool"), ("stop_go_scale_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("scale_preflight_authorized_bool", True), "overauthorization_scale_preflight_authorized_bool"), ("stop_go_implicit_tmp_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("implicit_tmp_discovery_authorized_bool", True), "overauthorization_implicit_tmp_discovery_authorized_bool"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("duplicate_gate_fail", lambda r: r["pass_fail_gate_records"].append(dict(r["pass_fail_gate_records"][0])), "gate_duplicate_mismatch"), ("synthetic_set_fail", lambda r: r["synthetic_validator_records"].pop(), "synthetic_validator_set_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]
    for n, mut, issue in report_mut:
        m = json.loads(json.dumps(passed)); mut(m); check(n, issue in validate_report(m))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 private_pair_ref exact_score_value"; check("public_leak_fail", scan_public_report(leak)["status"] == "fail")
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}

def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except Exception: print("invalid arguments", file=sys.stderr); return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        res = run_self_test_hardened(); print(json.dumps(res, indent=2, sort_keys=True)); return 0 if res["passed"] else 1
    if args["validate"]:
        try: report = load_json(repo / public_artifact_path(str(args["validate"]))) ; issues = validate_report(report)
        except Exception: report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(str(args["out"])) if args["out"] else None
    report = build_report(); path = write_report(report, out); print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True)); return 0 if report["status"] == STATUS_PASS else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
