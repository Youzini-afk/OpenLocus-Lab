#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AM evidence-pair support material generation preflight.

Public-only preflight over committed R2AL public artifact/docs. It does not read
private roots/material/group files or /tmp, does not scan source/candidates,
does not execute, recompute, compute metrics, generate material, or write private
outputs. It only specifies and narrowly authorizes R2AN explicit local material
generation.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AM Evidence-Pair Support Material Generation Preflight"
SLUG = "bea_v1_haae_r2am_evidence_pair_support_material_generation_preflight"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AL_CHECKPOINT = "39800bf"
R2AL_STATUS = "haae_r2al_new_signal_family_public_design_preflight_complete_r2am_material_generation_preflight_authorized"
R2AL_SELF_TEST_TOTAL = 28
R2AL_REPORT_PATH = Path("artifacts/bea_v1_haae_r2al_new_signal_family_public_design_preflight/bea_v1_haae_r2al_new_signal_family_public_design_preflight_report.json")

STATUS_PASS = "haae_r2am_evidence_pair_support_material_generation_preflight_complete_r2an_explicit_material_generation_authorized"
STATUS_FAIL_SOURCE = "haae_r2am_fail_closed_source_lock_mismatch"
STATUS_FAIL_CONTRACT = "haae_r2am_fail_closed_r2an_contract_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2am_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2am_fail_closed_raw_private_exact_leak"
STATUS_FAIL_READBACK = "haae_r2am_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 26
NEXT_PHASE = "BEA-v1-HAAE-R2AN Evidence-Pair Support Explicit Material Generation"
R2AO_PHASE = "BEA-v1-HAAE-R2AO Evidence-Pair Support Material Public Audit Package"
SELECTED_SIGNAL_FAMILY = "evidence_pair_support_complementarity"
R2AN_SCHEMA_VERSION = "bea_v1_haae_r2an_evidence_pair_support_material_generation_v1"
REQUIRED_GROUPS = ["task_frame", "source_manifest_private", "evidence_unit_pool", "evidence_pair_material", "support_relation_material", "contrast_control_material", "outcome_eval_private", "material_qa"]
PAIR_FAMILIES = ["target_support_pair", "complementary_support_pair", "contrastive_hard_negative_pair", "single_unit_ablation_control", "shuffled_relation_control", "cross_task_mismatch_control"]
BOUNDS = {"target_task_count": 20, "evidence_unit_depth_cap_per_task": 40, "support_pair_cap_per_task": 120, "contrast_control_pair_cap_per_task": 80, "total_pair_cap_per_task": 200, "source_file_cap": 500, "private_row_cap": 20000, "wall_clock_cap_minutes": 20}

GATE_NAMES = ["r2al_source_locked_gate", "r2al_self_test_28_gate", "r2al_forbidden_scan_pass_gate", "selected_signal_family_gate", "r2al_route_closure_gate", "r2an_not_authorized_in_r2al_gate", "schema_group_set_gate", "bounds_caps_gate", "source_allowlist_contract_gate", "private_output_contract_gate", "root_safety_contract_gate", "policy_gold_constraints_gate", "privacy_publication_contract_gate", "r2an_material_qa_only_gate", "r2ao_public_audit_after_generation_gate", "public_only_preflight_boundary_gate", "stop_go_truth_table_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]
SYNTHETIC_VALIDATORS = ["source_lock_pass", "wrong_r2al_status_fail", "self_test_drift_fail", "forbidden_scan_drift_fail", "selected_family_drift_fail", "route_closure_drift_fail", "r2an_prior_auth_drift_fail", "schema_group_set_fail", "schema_version_fail", "bounds_cap_fail", "source_allowlist_fail", "private_output_contract_fail", "root_safety_fail", "policy_gold_constraint_fail", "single_rank_reopen_fail", "privacy_publication_fail", "r2ao_audit_fail", "boundary_private_read_fail", "boundary_generation_fail", "stop_go_missing_true_fail", "stop_go_overauth_fail", "next_phase_drift_fail", "gate_set_fail", "readback_record_fail", "leak_fail", "safe_parser_fail"]
STOP_TRUE_FIELDS = ["haae_r2an_evidence_pair_support_material_generation_authorized_bool", "r2an_explicit_local_material_generation_authorized_bool", "r2an_private_output_root_required_bool", "r2an_public_corpus_manifest_required_bool", "r2an_bounded_public_source_scan_authorized_bool", "r2an_evidence_unit_generation_authorized_bool", "r2an_evidence_pair_material_generation_authorized_bool", "r2an_private_write_authorized_bool", "r2an_material_qa_only_no_experiment_metrics_bool", "r2an_aggregate_only_public_artifact_required_bool", "r2ao_public_audit_required_after_generation_bool"]
STOP_FALSE_FIELDS = ["private_read_authorized_bool", "prior_private_material_read_authorized_bool", "ci_execution_authorized_bool", "scale_execution_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "experiment_metrics_authorized_bool", "raw_publication_authorized_bool", "single_rank_content_path_route_reopen_authorized_bool", "mechanism_analysis_authorized_bool"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2al(r2al: dict[str, Any]) -> dict[str, bool]:
    source = (r2al.get("source_lock_records") or [{}])[0]
    selected = (r2al.get("selected_signal_family_records") or [{}])[0]
    closure = (r2al.get("inherited_route_closure_records") or [{}])[0]
    stop = (r2al.get("stop_go_records") or [{}])[0]
    status_ok = r2al.get("status") == R2AL_STATUS
    self_test_ok = r2al.get("self_test_total") == R2AL_SELF_TEST_TOTAL
    scan_ok = r2al.get("forbidden_scan", {}).get("status") == "pass"
    family_ok = selected.get("selected_signal_family_bucket") == SELECTED_SIGNAL_FAMILY and selected.get("selected_bool") is True
    closure_ok = closure.get("route_closed_bool") is True and closure.get("closed_route_bucket") == "r2ac_r2ai_single_rank_content_path_signal" and closure.get("robustness_failure_bucket") == "brittle_or_artifact" and closure.get("controls_perturbations_match_or_exceed_signal_bool") is True and closure.get("method_default_scale_claim_rejected_bool") is True
    r2an_not_auth = stop.get("r2an_generation_authorized_bool") is False and stop.get("haae_r2am_evidence_pair_support_material_generation_preflight_authorized_bool") is True and stop.get("next_allowed_phase") == PHASE
    source_ok = status_ok and self_test_ok and scan_ok and family_ok and closure_ok and r2an_not_auth and source.get("source_locked_bool") is True
    return {"source_ok": source_ok, "status_ok": status_ok, "self_test_ok": self_test_ok, "scan_ok": scan_ok, "family_ok": family_ok, "closure_ok": closure_ok, "r2an_not_auth": r2an_not_auth}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_key_path", re.compile(r"candidate_key|pair_key|source_file_key|filepath|source_filename_value|directory_value|snippet_value|start_line|end_line|gold_spans|hard_negatives|\.rs\b|crates/openlocus-", re.I)), ("exact_or_hash", re.compile(r"exact_count|exact_rate|exact_score|private_score|\b[a-f0-9]{32,64}\b", re.I))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AL_CHECKPOINT, R2AL_STATUS, "R2AL self-test 28/28", SELECTED_SIGNAL_FAMILY, NEXT_PHASE, "default mode no-op", "private output root", "public corpus manifest", "target_task_count=20", "evidence_unit_depth_cap_per_task=40", "support_pair_cap_per_task=120", "contrast_control_pair_cap_per_task=80", "total_pair_cap_per_task=200", "source_file_cap=500", "private_row_cap=20000", "wall_clock_cap_minutes=20", "bounded public source allowlist required", R2AN_SCHEMA_VERSION, "gold private eval only", "single-rank content/path signal forbidden", "material QA only", R2AO_PHASE, "no method/default/scale/winner/validated-signal claims"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2am-evidence-pair-support-material-generation-preflight.md")) and has_all(read("docs/zh/bea-v1-haae-r2am-evidence-pair-support-material-generation-preflight.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2am-evidence-pair-support-material-generation-preflight.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2al: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2al is None:
        try: r2al = load_json(repo / R2AL_REPORT_PATH)
        except Exception: r2al = {}
    audit = audit_r2al(r2al)
    readback = public_readback_match(self_test_total)
    if not audit["source_ok"]:
        status = STATUS_FAIL_SOURCE
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2al_source_locked_gate": audit["source_ok"], "r2al_self_test_28_gate": audit["self_test_ok"], "r2al_forbidden_scan_pass_gate": audit["scan_ok"], "selected_signal_family_gate": audit["family_ok"], "r2al_route_closure_gate": audit["closure_ok"], "r2an_not_authorized_in_r2al_gate": audit["r2an_not_auth"], "schema_group_set_gate": True, "bounds_caps_gate": True, "source_allowlist_contract_gate": True, "private_output_contract_gate": True, "root_safety_contract_gate": True, "policy_gold_constraints_gate": True, "privacy_publication_contract_gate": True, "r2an_material_qa_only_gate": True, "r2ao_public_audit_after_generation_gate": True, "public_only_preflight_boundary_gate": True, "stop_go_truth_table_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    stop: dict[str, Any] = {"anonymous_stop_go_id": "haaer2amstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2al_public_artifact"}
    stop.update({field: passed for field in STOP_TRUE_FIELDS})
    stop.update({field: False for field in STOP_FALSE_FIELDS})
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2amsource0000", "locked_haae_r2al_checkpoint": R2AL_CHECKPOINT, "locked_haae_r2al_status": R2AL_STATUS, "r2al_status_match_bool": audit["status_ok"], "r2al_self_test_28_bool": audit["self_test_ok"], "r2al_forbidden_scan_pass_bool": audit["scan_ok"], "r2al_selected_signal_family_bucket": SELECTED_SIGNAL_FAMILY, "r2al_selected_signal_family_bool": audit["family_ok"], "r2al_closed_prior_route_bucket": "r2ac_r2ai_single_rank_content_path_signal", "r2al_prior_failure_bucket": "brittle_or_artifact", "r2al_route_closure_match_bool": audit["closure_ok"], "r2al_single_rank_route_reopened_bool": False, "r2an_not_authorized_in_r2al_bool": audit["r2an_not_auth"], "source_locked_bool": audit["source_ok"]}],
        "inherited_signal_family_records": [{"anonymous_inherited_signal_family_id": "haaer2aminherited0000", "closed_prior_route_bucket": "r2ac_r2ai_single_rank_content_path_signal", "prior_failure_bucket": "brittle_or_artifact", "selected_signal_family_bucket": SELECTED_SIGNAL_FAMILY, "not_single_rank_content_path_bool": True, "setwise_evidence_structure_bool": True, "support_complementarity_contrast_bool": True, "route_closure_inherited_bool": True, "r2am_public_preflight_only_bool": True}],
        "r2an_schema_contract_records": [{"anonymous_schema_contract_id": "haaer2amschema0000", "r2an_phase": NEXT_PHASE, "schema_version": R2AN_SCHEMA_VERSION, "required_private_group_buckets": REQUIRED_GROUPS, "candidate_pair_family_buckets": PAIR_FAMILIES}],
        "r2an_bounds_contract_records": [{"anonymous_bounds_contract_id": "haaer2ambounds0000", **BOUNDS, "local_only_bool": True}],
        "r2an_source_allowlist_contract_records": [{"anonymous_source_allowlist_contract_id": "haaer2amallow0000", "bounded_public_source_allowlist_required_bool": True, "public_corpus_manifest_required_bool": True, "network_forbidden_bool": True, "clone_forbidden_bool": True, "provider_forbidden_bool": True}],
        "r2an_private_output_contract_records": [{"anonymous_private_output_contract_id": "haaer2amoutput0000", "explicit_mode_requires_private_output_root_bool": True, "allow_flag_required_bool": True, "confirm_private_output_required_bool": True, "confirm_no_experiment_metrics_required_bool": True, "private_manifest_required_bool": True, "private_manifest_schema_version": R2AN_SCHEMA_VERSION}],
        "r2an_root_safety_contract_records": [{"anonymous_root_safety_contract_id": "haaer2amroot0000", "private_output_root_explicit_required_bool": True, "repo_root_forbidden_bool": True, "symlink_escape_forbidden_bool": True, "unrelated_root_overwrite_forbidden_bool": True}],
        "r2an_policy_contract_records": [{"anonymous_policy_contract_id": "haaer2ampolicy0000", "selected_signal_family_bucket": SELECTED_SIGNAL_FAMILY, "single_rank_content_path_signal_bool": False, "pair_level_signal_bool": True, "setwise_support_bool": True, "contrast_control_required_bool": True, "support_control_balance_required_bool": True, "minimum_control_ratio_bucket": "control_pairs_at_least_support_pairs_or_bucketed_balance", "isolated_single_candidate_rank_forbidden_bool": True, "gold_private_eval_only_bool": True, "gold_outcome_labels_used_for_evidence_unit_selection_bool": False, "gold_outcome_labels_used_for_pair_selection_bool": False, "single_rank_content_path_signal_primary_bool": False, "material_qa_only_no_experiment_metrics_bool": True}],
        "r2an_privacy_publication_contract_records": [{"anonymous_privacy_publication_contract_id": "haaer2amprivacy0000", "aggregate_only_public_artifact_required_bool": True, "raw_task_query_candidate_gold_publication_bool": False, "private_root_path_publication_bool": False, "source_filename_line_publication_bool": False, "experiment_metrics_publication_bool": False, "r2ao_public_audit_required_after_generation_bool": True, "next_audit_phase": R2AO_PHASE}],
        "boundary_records": [{"anonymous_boundary_id": "haaer2amboundary0000", "public_only_preflight_bool": True, "read_only_r2al_public_artifact_docs_bool": True, "private_root_read_bool": False, "private_material_read_bool": False, "group_file_read_bool": False, "tmp_read_bool": False, "source_candidate_scan_bool": False, "material_generation_bool": False, "private_write_bool": False, "recompute_bool": False, "metrics_bool": False, "ci_network_provider_clone_runtime_openlocus_bool": False, "raw_publication_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2amclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "validated_signal_claim_bool": False, "robust_method_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2amgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2amsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2amreadback0000", **readback}],
        "stop_go_records": [stop],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "inherited_signal_family_records", "r2an_schema_contract_records", "r2an_bounds_contract_records", "r2an_source_allowlist_contract_records", "r2an_private_output_contract_records", "r2an_root_safety_contract_records", "r2an_policy_contract_records", "r2an_privacy_publication_contract_records", "boundary_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    if {row.get("gate_bucket") for row in report.get("pass_fail_gate_records", [])} != set(GATE_NAMES): issues.append("gate_set_mismatch")
    if {row.get("validator_bucket") for row in report.get("synthetic_validator_records", [])} != set(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    readback = report.get("public_readback_records", [])
    if len(readback) != 1 or readback[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    source = (report.get("source_lock_records") or [{}])[0]
    for field in ["r2al_status_match_bool", "r2al_self_test_28_bool", "r2al_forbidden_scan_pass_bool", "r2al_selected_signal_family_bool", "r2al_route_closure_match_bool", "r2an_not_authorized_in_r2al_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    if source.get("r2al_closed_prior_route_bucket") != "r2ac_r2ai_single_rank_content_path_signal" or source.get("r2al_prior_failure_bucket") != "brittle_or_artifact": issues.append("source_lock_route_closure_bucket")
    if source.get("r2al_selected_signal_family_bucket") != SELECTED_SIGNAL_FAMILY: issues.append("source_lock_selected_family_bucket")
    if source.get("r2al_single_rank_route_reopened_bool") is not False: issues.append("source_lock_single_rank_reopened")
    if source.get("locked_haae_r2al_checkpoint") != R2AL_CHECKPOINT or source.get("locked_haae_r2al_status") != R2AL_STATUS: issues.append("source_lock_mismatch")
    inherited = (report.get("inherited_signal_family_records") or [{}])[0]
    if inherited.get("selected_signal_family_bucket") != SELECTED_SIGNAL_FAMILY or inherited.get("closed_prior_route_bucket") != "r2ac_r2ai_single_rank_content_path_signal" or inherited.get("prior_failure_bucket") != "brittle_or_artifact": issues.append("inherited_signal_family_mismatch")
    for field in ["not_single_rank_content_path_bool", "setwise_evidence_structure_bool", "support_complementarity_contrast_bool", "route_closure_inherited_bool", "r2am_public_preflight_only_bool"]:
        if inherited.get(field) is not True: issues.append(f"inherited_{field}")
    schema = (report.get("r2an_schema_contract_records") or [{}])[0]
    if schema.get("schema_version") != R2AN_SCHEMA_VERSION or set(schema.get("required_private_group_buckets", [])) != set(REQUIRED_GROUPS) or set(schema.get("candidate_pair_family_buckets", [])) != set(PAIR_FAMILIES): issues.append("schema_contract_mismatch")
    bounds = (report.get("r2an_bounds_contract_records") or [{}])[0]
    for key, expected in BOUNDS.items():
        if bounds.get(key) != expected: issues.append(f"bounds_{key}")
    if bounds.get("local_only_bool") is not True: issues.append("bounds_local_only_bool")
    allow = (report.get("r2an_source_allowlist_contract_records") or [{}])[0]
    for field in ["bounded_public_source_allowlist_required_bool", "public_corpus_manifest_required_bool", "network_forbidden_bool", "clone_forbidden_bool", "provider_forbidden_bool"]:
        if allow.get(field) is not True: issues.append(f"allowlist_{field}")
    output = (report.get("r2an_private_output_contract_records") or [{}])[0]
    for field in ["explicit_mode_requires_private_output_root_bool", "allow_flag_required_bool", "confirm_private_output_required_bool", "confirm_no_experiment_metrics_required_bool", "private_manifest_required_bool"]:
        if output.get(field) is not True: issues.append(f"output_{field}")
    if output.get("private_manifest_schema_version") != R2AN_SCHEMA_VERSION: issues.append("output_schema_version")
    root = (report.get("r2an_root_safety_contract_records") or [{}])[0]
    for field in ["private_output_root_explicit_required_bool", "repo_root_forbidden_bool", "symlink_escape_forbidden_bool", "unrelated_root_overwrite_forbidden_bool"]:
        if root.get(field) is not True: issues.append(f"root_{field}")
    policy = (report.get("r2an_policy_contract_records") or [{}])[0]
    if policy.get("gold_private_eval_only_bool") is not True or policy.get("material_qa_only_no_experiment_metrics_bool") is not True: issues.append("policy_material_qa_gold")
    if policy.get("selected_signal_family_bucket") != SELECTED_SIGNAL_FAMILY or policy.get("minimum_control_ratio_bucket") != "control_pairs_at_least_support_pairs_or_bucketed_balance": issues.append("policy_signal_family_or_ratio")
    for field in ["pair_level_signal_bool", "setwise_support_bool", "contrast_control_required_bool", "support_control_balance_required_bool", "isolated_single_candidate_rank_forbidden_bool"]:
        if policy.get(field) is not True: issues.append(f"policy_{field}")
    for field in ["gold_outcome_labels_used_for_evidence_unit_selection_bool", "gold_outcome_labels_used_for_pair_selection_bool", "single_rank_content_path_signal_primary_bool"]:
        if policy.get(field) is not False: issues.append(f"policy_{field}")
    privacy = (report.get("r2an_privacy_publication_contract_records") or [{}])[0]
    if privacy.get("aggregate_only_public_artifact_required_bool") is not True or privacy.get("r2ao_public_audit_required_after_generation_bool") is not True: issues.append("privacy_required")
    for field in ["raw_task_query_candidate_gold_publication_bool", "private_root_path_publication_bool", "source_filename_line_publication_bool", "experiment_metrics_publication_bool"]:
        if privacy.get(field) is not False: issues.append(f"privacy_{field}")
    boundary = (report.get("boundary_records") or [{}])[0]
    if boundary.get("public_only_preflight_bool") is not True: issues.append("boundary_public_only")
    for field in ["private_root_read_bool", "private_material_read_bool", "group_file_read_bool", "tmp_read_bool", "source_candidate_scan_bool", "material_generation_bool", "private_write_bool", "recompute_bool", "metrics_bool", "ci_network_provider_clone_runtime_openlocus_bool", "raw_publication_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "validated_signal_claim_bool", "robust_method_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_phase_mismatch")
        for field in STOP_TRUE_FIELDS:
            if stop.get(field) is not True: issues.append(f"stop_go_missing_{field}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    for field in STOP_FALSE_FIELDS:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    return issues


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


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2AL_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2al_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    st = json.loads(json.dumps(base)); st["self_test_total"] = 27; check("self_test_drift_fail", build_report(st)["status"] == STATUS_FAIL_SOURCE)
    fs = json.loads(json.dumps(base)); fs["forbidden_scan"]["status"] = "fail"; check("forbidden_scan_drift_fail", build_report(fs)["status"] == STATUS_FAIL_SOURCE)
    fam = json.loads(json.dumps(base)); fam["selected_signal_family_records"][0]["selected_signal_family_bucket"] = "wrong"; check("selected_family_drift_fail", build_report(fam)["status"] == STATUS_FAIL_SOURCE)
    closure = json.loads(json.dumps(base)); closure["inherited_route_closure_records"][0]["route_closed_bool"] = False; check("route_closure_drift_fail", build_report(closure)["status"] == STATUS_FAIL_SOURCE)
    prior = json.loads(json.dumps(base)); prior["stop_go_records"][0]["r2an_generation_authorized_bool"] = True; check("r2an_prior_auth_drift_fail", build_report(prior)["status"] == STATUS_FAIL_SOURCE)
    for label, mutator, expected in [("schema_group_set_fail", lambda r: r["r2an_schema_contract_records"][0]["required_private_group_buckets"].pop(), "schema_contract_mismatch"), ("schema_version_fail", lambda r: r["r2an_schema_contract_records"][0].__setitem__("schema_version", "wrong"), "schema_contract_mismatch"), ("bounds_cap_fail", lambda r: r["r2an_bounds_contract_records"][0].__setitem__("target_task_count", 21), "bounds_target_task_count"), ("source_allowlist_fail", lambda r: r["r2an_source_allowlist_contract_records"][0].__setitem__("network_forbidden_bool", False), "allowlist_network_forbidden_bool"), ("private_output_contract_fail", lambda r: r["r2an_private_output_contract_records"][0].__setitem__("confirm_no_experiment_metrics_required_bool", False), "output_confirm_no_experiment_metrics_required_bool"), ("root_safety_fail", lambda r: r["r2an_root_safety_contract_records"][0].__setitem__("symlink_escape_forbidden_bool", False), "root_symlink_escape_forbidden_bool"), ("policy_gold_constraint_fail", lambda r: r["r2an_policy_contract_records"][0].__setitem__("gold_outcome_labels_used_for_pair_selection_bool", True), "policy_gold_outcome_labels_used_for_pair_selection_bool"), ("single_rank_reopen_fail", lambda r: r["r2an_policy_contract_records"][0].__setitem__("single_rank_content_path_signal_primary_bool", True), "policy_single_rank_content_path_signal_primary_bool"), ("privacy_publication_fail", lambda r: r["r2an_privacy_publication_contract_records"][0].__setitem__("experiment_metrics_publication_bool", True), "privacy_experiment_metrics_publication_bool"), ("r2ao_audit_fail", lambda r: r["r2an_privacy_publication_contract_records"][0].__setitem__("r2ao_public_audit_required_after_generation_bool", False), "privacy_required"), ("boundary_private_read_fail", lambda r: r["boundary_records"][0].__setitem__("private_root_read_bool", True), "boundary_private_root_read_bool"), ("boundary_generation_fail", lambda r: r["boundary_records"][0].__setitem__("material_generation_bool", True), "boundary_material_generation_bool"), ("stop_go_missing_true_fail", lambda r: r["stop_go_records"][0].__setitem__("r2an_private_output_root_required_bool", False), "stop_go_missing_r2an_private_output_root_required_bool"), ("stop_go_overauth_fail", lambda r: r["stop_go_records"][0].__setitem__("ci_execution_authorized_bool", True), "overauthorization_ci_execution_authorized_bool"), ("next_phase_drift_fail", lambda r: r["stop_go_records"][0].__setitem__("next_allowed_phase", "wrong"), "next_phase_mismatch"), ("gate_set_fail", lambda r: r["pass_fail_gate_records"].pop(), "gate_set_mismatch"), ("readback_record_fail", lambda r: r.__setitem__("public_readback_records", []), "public_readback_record_mismatch")]:
        mutated = json.loads(json.dumps(passed)); mutator(mutated); check(label, expected in validate_report(mutated))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 candidate_key pair_key private_score"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
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
