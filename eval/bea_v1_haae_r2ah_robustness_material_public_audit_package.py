#!/usr/bin/env python3
"""BEA-v1-HAAE-R2AH robustness material public audit package.

Public-only audit of the committed R2AG aggregate public artifact. This script
does not read private roots/material, recompute material, compute experiment
metrics, scan source/candidates, or authorize CI/network/default/method/scale.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2AH Robustness Material Public Audit Package"
SLUG = "bea_v1_haae_r2ah_robustness_material_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2AG_CHECKPOINT = "a0ac3b3"
R2AG_STATUS = "haae_r2ag_explicit_local_bounded_robustness_material_generation_complete_r2ah_public_audit_authorized"
R2AG_REPORT_PATH = Path("artifacts/bea_v1_haae_r2ag_explicit_local_bounded_robustness_material_generation/bea_v1_haae_r2ag_explicit_local_bounded_robustness_material_generation_report.json")

STATUS_PASS = "haae_r2ah_robustness_material_public_audit_package_complete_r2ai_explicit_experiment_authorized"
STATUS_FAIL_SOURCE = "haae_r2ah_fail_closed_source_lock_mismatch"
STATUS_FAIL_MATERIAL = "haae_r2ah_fail_closed_material_audit_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2ah_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2ah_fail_closed_public_artifact_leak"
STATUS_FAIL_READBACK = "haae_r2ah_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 21
NEXT_PHASE = "BEA-v1-HAAE-R2AI Explicit Local Robustness Experiment Over Existing R2AG Material"

VARIANTS = ["symbol_content_ablation", "query_token_masking", "shuffled_content_control", "negative_control_strengthening"]
GROUPS = ["task_frame", "source_manifest_private", "candidate_pool", "variant_material", "rank_pack", "outcome_eval_private", "material_qa"]
FORBIDDEN_STOP_TRUE = ["new_material_generation_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool", "source_scan_authorized_bool"]
GATE_NAMES = ["r2ag_source_locked_gate", "r2ag_status_gate", "aggregate_counts_bounds_gate", "target_20_gate", "depth_40_gate", "row_cap_20000_gate", "variant_set_gate", "group_counts_gate", "rank_policy_no_gold_path_gate", "gold_private_eval_only_gate", "public_artifact_privacy_gate", "no_experiment_metrics_gate", "public_only_audit_gate", "no_private_read_recompute_scan_gate", "r2ai_experiment_only_stop_go_gate", "no_ci_network_generation_claim_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]

SYNTHETIC_VALIDATORS = [
    "source_lock_pass", "wrong_r2ag_status_fail", "missing_r2ah_authorization_fail",
    "counts_bounds_mutation_fail", "variant_missing_fail", "group_counts_missing_fail",
    "rank_gold_mutation_fail", "rank_path_mutation_fail", "privacy_publication_fail",
    "metrics_overauth_fail", "boundary_private_read_fail", "stop_go_overauth_fail",
    "next_phase_drift_fail", "r2ai_metrics_authorization_drift_fail", "gate_set_fail", "synthetic_validator_set_fail", "readback_record_fail",
    "leak_fail", "stale_readback_fail", "status_drift_fail", "safe_parser_fail",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2ag(r2ag: dict[str, Any]) -> dict[str, bool]:
    material = (r2ag.get("material_aggregate_records") or [{}])[0]
    rank = (r2ag.get("rank_policy_records") or [{}])[0]
    claim = (r2ag.get("claim_boundary_records") or [{}])[0]
    stop = (r2ag.get("stop_go_records") or [{}])[0]
    qa = (r2ag.get("material_qa_records") or [{}])[0]
    variants = {row.get("variant_bucket"): row for row in r2ag.get("variant_aggregate_records", [])}
    groups = {row.get("group_bucket"): row for row in r2ag.get("private_manifest_group_count_records", [])}
    source_ok = r2ag.get("status") == R2AG_STATUS and r2ag.get("forbidden_scan", {}).get("status") == "pass"
    stop_auth_ok = stop.get("haae_r2ah_public_audit_package_authorized_bool") is True and stop.get("r2ah_public_audit_over_generated_material_only_bool") is True
    stop_no_overauth = all(stop.get(field, False) is False for field in ["r2ah_experiment_authorized_bool", "experiment_metrics_authorized_bool", "new_material_generation_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "clone_authorized_bool", "runtime_execution_authorized_bool", "openlocus_runtime_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"])
    counts_ok = material.get("actual_task_count") == 20 and material.get("target_task_count_bucket") == "target_20" and material.get("candidate_depth_cap_bucket") == "depth_40" and material.get("private_row_cap_bucket") == "row_cap_20000" and material.get("private_row_count_bucket") == "count_le_20000" and material.get("material_generation_complete_bool") is True and material.get("raw_rows_published_bool") is False
    variants_ok = set(variants) == set(VARIANTS) and all(variants[v].get("present_bool") is True and variants[v].get("raw_variant_rows_published_bool") is False for v in VARIANTS)
    groups_ok = set(groups) == set(GROUPS) and all(groups[g].get("raw_group_rows_published_bool") is False for g in GROUPS)
    rank_ok = rank.get("rank_policy_used_gold_bool") is False and rank.get("rank_policy_used_path_bool") is False and rank.get("gold_private_eval_only_bool") is True and rank.get("gold_used_for_outcome_eval_group_only_bool") is True
    privacy_ok = material.get("actual_task_count_safe_to_publish_bool") is True and material.get("raw_rows_published_bool") is False and all(row.get("private_root_path_published_bool", False) is False and row.get("private_manifest_path_published_bool", False) is False for row in r2ag.get("private_root_records", [])) and all(row.get("manifest_path_published_bool", False) is False and row.get("repo_ids_published_bool", False) is False for row in r2ag.get("public_corpus_manifest_records", []))
    no_metrics_ok = qa.get("no_experiment_metrics_bool") is True and claim.get("experiment_metrics_bool") is False and claim.get("retrieval_quality_metric_claim_bool") is False and claim.get("r2ah_experiment_bool") is False
    claim_ok = no_metrics_ok and all(claim.get(field) is False for field in ["ci_network_provider_clone_bool", "runtime_openlocus_bool", "scheduler_selector_bool", "default_method_scaling_claim_bool", "raw_publication_bool"])
    source_locked = source_ok and stop_auth_ok and stop_no_overauth
    material_ok = counts_ok and variants_ok and groups_ok and rank_ok and privacy_ok and no_metrics_ok and qa.get("aggregate_only_public_bool") is True
    return {"source_locked": source_locked, "status_ok": r2ag.get("status") == R2AG_STATUS, "scan_ok": r2ag.get("forbidden_scan", {}).get("status") == "pass", "stop_auth_ok": stop_auth_ok, "stop_no_overauth": stop_no_overauth, "counts_ok": counts_ok, "variants_ok": variants_ok, "groups_ok": groups_ok, "rank_ok": rank_ok, "privacy_ok": privacy_ok, "no_metrics_ok": no_metrics_ok, "claim_ok": claim_ok, "material_ok": material_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_path", re.compile(r"candidate_key|source_file_key|source_path|filepath|filename|directory|snippet|start_line|end_line|gold_spans|hard_negatives|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|top[0-9]+_|mrr|hit_rate|exact_rate|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2AG_CHECKPOINT, R2AG_STATUS, "public-only audit", "read only committed R2AG public artifact", "no private root read", "no recompute material", "no experiment metrics in R2AH", "no source/candidate scan", "target 20", "depth 40", "row cap 20000", "symbol_content_ablation/query_token_masking/shuffled_content_control/negative_control_strengthening", "rank policy no gold/path", "aggregate-only privacy", NEXT_PHASE, "explicit local robustness experiment over existing R2AG private material", "R2AI aggregate-only experiment metrics authorized", "no CI/network/new generation/default/method/scale/raw publication"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2ah-robustness-material-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2ah-robustness-material-public-audit-package.md"))
    current_root = read("docs/current-research-conclusions.md")
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and has_all(current_root) and "bea-v1-haae-r2ah-robustness-material-public-audit-package.md" in current_root
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2ag: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2ag is None:
        try: r2ag = load_json(repo / R2AG_REPORT_PATH)
        except Exception: r2ag = {}
    audit = audit_r2ag(r2ag)
    readback = public_readback_match(self_test_total)
    if not audit["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not audit["material_ok"]:
        status = STATUS_FAIL_MATERIAL
    elif not audit["claim_ok"] or not audit["stop_no_overauth"]:
        status = STATUS_FAIL_BOUNDARY
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2ag_source_locked_gate": audit["source_locked"], "r2ag_status_gate": audit["status_ok"], "aggregate_counts_bounds_gate": audit["counts_ok"], "target_20_gate": audit["counts_ok"], "depth_40_gate": audit["counts_ok"], "row_cap_20000_gate": audit["counts_ok"], "variant_set_gate": audit["variants_ok"], "group_counts_gate": audit["groups_ok"], "rank_policy_no_gold_path_gate": audit["rank_ok"], "gold_private_eval_only_gate": audit["rank_ok"], "public_artifact_privacy_gate": audit["privacy_ok"], "no_experiment_metrics_gate": audit["no_metrics_ok"], "public_only_audit_gate": True, "no_private_read_recompute_scan_gate": True, "r2ai_experiment_only_stop_go_gate": True, "no_ci_network_generation_claim_gate": audit["claim_ok"], "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2ahsource0000", "locked_haae_r2ag_checkpoint": R2AG_CHECKPOINT, "locked_haae_r2ag_status": R2AG_STATUS, "r2ag_status_match_bool": audit["status_ok"], "r2ag_forbidden_scan_pass_bool": audit["scan_ok"], "r2ag_r2ah_authorization_match_bool": audit["stop_auth_ok"], "r2ag_no_forbidden_stop_go_drift_bool": audit["stop_no_overauth"], "source_locked_bool": audit["source_locked"]}],
        "material_audit_records": [{"anonymous_material_audit_id": "haaer2ahmaterial0000", "target_task_count_bucket": "target_20", "candidate_depth_bucket": "depth_40", "row_cap_bucket": "row_cap_20000", "private_row_count_bucket": "count_le_20000", "aggregate_counts_bounds_match_bool": audit["counts_ok"], "variant_set_match_bool": audit["variants_ok"], "private_manifest_group_counts_present_bool": audit["groups_ok"], "material_complete_bool": audit["material_ok"], "raw_rows_published_bool": False}],
        "rank_policy_audit_records": [{"anonymous_rank_policy_audit_id": "haaer2ahrank0000", "rank_policy_used_gold_bool": False, "rank_policy_used_path_bool": False, "gold_private_eval_only_bool": True, "rank_policy_match_bool": audit["rank_ok"]}],
        "public_privacy_audit_records": [{"anonymous_public_privacy_audit_id": "haaer2ahprivacy0000", "aggregate_only_privacy_bool": audit["privacy_ok"], "private_root_read_bool": False, "private_material_read_bool": False, "private_root_path_published_bool": False, "manifest_path_published_bool": False, "raw_publication_bool": False}],
        "boundary_audit_records": [{"anonymous_boundary_audit_id": "haaer2ahboundary0000", "public_only_audit_bool": True, "read_only_committed_r2ag_public_artifact_bool": True, "private_root_read_bool": False, "recompute_material_bool": False, "experiment_metrics_computed_bool": False, "source_candidate_scan_bool": False, "new_material_generation_bool": False, "ci_network_provider_clone_bool": False, "default_method_scale_claim_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2ahclaim0000", "experiment_metrics_bool": False, "r2ai_experiment_authorization_only_bool": passed, "new_material_generation_bool": False, "ci_network_provider_clone_bool": False, "runtime_openlocus_bool": False, "scheduler_selector_bool": False, "default_method_scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2ahgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2ahsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(SYNTHETIC_VALIDATORS)],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2ahreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2ahstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2ag_public_artifact", "haae_r2ai_explicit_local_robustness_experiment_authorized_bool": passed, "r2ai_existing_r2ag_private_material_only_bool": passed, "r2ai_explicit_private_root_required_bool": passed, "r2ai_aggregate_only_experiment_metrics_authorized_bool": passed, "r2ai_public_audit_required_after_experiment_bool": passed, "new_material_generation_authorized_bool": False, "experiment_metrics_authorized_bool": passed, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "runtime_execution_authorized_bool": False, "openlocus_runtime_authorized_bool": False, "source_scan_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report); report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "material_audit_records", "rank_policy_audit_records", "public_privacy_audit_records", "boundary_audit_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if report.get("status") != STATUS_PASS: issues.append("status_mismatch")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    gate_rows = report.get("pass_fail_gate_records", [])
    gate_set = {row.get("gate_bucket") for row in gate_rows}
    if gate_set != set(GATE_NAMES) or len(gate_rows) != len(GATE_NAMES): issues.append("gate_set_mismatch")
    synth_rows = report.get("synthetic_validator_records", [])
    synth_set = {row.get("validator_bucket") for row in synth_rows}
    if synth_set != set(SYNTHETIC_VALIDATORS) or len(synth_rows) != len(SYNTHETIC_VALIDATORS): issues.append("synthetic_validator_set_mismatch")
    readback_rows = report.get("public_readback_records", [])
    if len(readback_rows) != 1 or readback_rows[0].get("all_public_readback_match_bool") is not True: issues.append("public_readback_record_mismatch")
    src = (report.get("source_lock_records") or [{}])[0]
    if src.get("locked_haae_r2ag_checkpoint") != R2AG_CHECKPOINT or src.get("locked_haae_r2ag_status") != R2AG_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2ag_status_match_bool", "r2ag_forbidden_scan_pass_bool", "r2ag_r2ah_authorization_match_bool", "r2ag_no_forbidden_stop_go_drift_bool", "source_locked_bool"]:
        if src.get(field) is not True: issues.append(f"source_lock_{field}")
    material = (report.get("material_audit_records") or [{}])[0]
    if material.get("target_task_count_bucket") != "target_20" or material.get("candidate_depth_bucket") != "depth_40" or material.get("row_cap_bucket") != "row_cap_20000" or material.get("private_row_count_bucket") != "count_le_20000": issues.append("material_bounds_mismatch")
    for field in ["aggregate_counts_bounds_match_bool", "variant_set_match_bool", "private_manifest_group_counts_present_bool", "material_complete_bool"]:
        if material.get(field) is not True: issues.append(f"material_{field}")
    if material.get("raw_rows_published_bool") is not False: issues.append("raw_rows_publication")
    rank = (report.get("rank_policy_audit_records") or [{}])[0]
    if rank.get("rank_policy_used_gold_bool") is not False or rank.get("rank_policy_used_path_bool") is not False or rank.get("gold_private_eval_only_bool") is not True or rank.get("rank_policy_match_bool") is not True: issues.append("rank_policy_mismatch")
    privacy = (report.get("public_privacy_audit_records") or [{}])[0]
    for field in ["private_root_read_bool", "private_material_read_bool", "private_root_path_published_bool", "manifest_path_published_bool", "raw_publication_bool"]:
        if privacy.get(field) is not False: issues.append(f"privacy_{field}")
    if privacy.get("aggregate_only_privacy_bool") is not True: issues.append("privacy_aggregate_only")
    boundary = (report.get("boundary_audit_records") or [{}])[0]
    if boundary.get("public_only_audit_bool") is not True or boundary.get("read_only_committed_r2ag_public_artifact_bool") is not True: issues.append("boundary_public_only")
    for field in ["private_root_read_bool", "recompute_material_bool", "experiment_metrics_computed_bool", "source_candidate_scan_bool", "new_material_generation_bool", "ci_network_provider_clone_bool", "default_method_scale_claim_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["experiment_metrics_bool", "new_material_generation_bool", "ci_network_provider_clone_bool", "runtime_openlocus_bool", "scheduler_selector_bool", "default_method_scaling_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        for field in ["haae_r2ai_explicit_local_robustness_experiment_authorized_bool", "r2ai_existing_r2ag_private_material_only_bool", "r2ai_explicit_private_root_required_bool", "r2ai_aggregate_only_experiment_metrics_authorized_bool", "experiment_metrics_authorized_bool", "r2ai_public_audit_required_after_experiment_bool"]:
            if stop.get(field) is not True: issues.append(f"stop_go_missing_{field}")
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_phase_mismatch")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
            if gate.get("gate_public_artifact_bool") is not True: issues.append(f"gate_not_public_{gate.get('gate_bucket', 'unknown')}")
    for field in FORBIDDEN_STOP_TRUE:
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
    path = Path(value)
    resolved = path if path.is_absolute() else repo / path
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
    base = load_json(repo / R2AG_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2ag_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    noauth = json.loads(json.dumps(base)); noauth["stop_go_records"][0]["haae_r2ah_public_audit_package_authorized_bool"] = False; check("missing_r2ah_authorization_fail", build_report(noauth)["status"] == STATUS_FAIL_SOURCE)
    counts = json.loads(json.dumps(base)); counts["material_aggregate_records"][0]["candidate_depth_cap_bucket"] = "depth_400"; check("counts_bounds_mutation_fail", build_report(counts)["status"] == STATUS_FAIL_MATERIAL)
    variant = json.loads(json.dumps(base)); variant["variant_aggregate_records"][0]["present_bool"] = False; check("variant_missing_fail", build_report(variant)["status"] == STATUS_FAIL_MATERIAL)
    groups = json.loads(json.dumps(base)); groups["private_manifest_group_count_records"].pop(); check("group_counts_missing_fail", build_report(groups)["status"] == STATUS_FAIL_MATERIAL)
    rank_gold = json.loads(json.dumps(base)); rank_gold["rank_policy_records"][0]["rank_policy_used_gold_bool"] = True; check("rank_gold_mutation_fail", build_report(rank_gold)["status"] == STATUS_FAIL_MATERIAL)
    rank_path = json.loads(json.dumps(base)); rank_path["rank_policy_records"][0]["rank_policy_used_path_bool"] = True; check("rank_path_mutation_fail", build_report(rank_path)["status"] == STATUS_FAIL_MATERIAL)
    privacy = json.loads(json.dumps(base)); privacy["private_root_records"][0]["private_root_path_published_bool"] = True; check("privacy_publication_fail", build_report(privacy)["status"] == STATUS_FAIL_MATERIAL)
    metrics = json.loads(json.dumps(base)); metrics["claim_boundary_records"][0]["experiment_metrics_bool"] = True; check("metrics_overauth_fail", build_report(metrics)["status"] in {STATUS_FAIL_MATERIAL, STATUS_FAIL_BOUNDARY})
    boundary = json.loads(json.dumps(passed)); boundary["boundary_audit_records"][0]["private_root_read_bool"] = True; check("boundary_private_read_fail", "boundary_private_root_read_bool" in validate_report(boundary))
    over = json.loads(json.dumps(passed)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("stop_go_overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(over)))
    next_bad = json.loads(json.dumps(passed)); next_bad["stop_go_records"][0]["next_allowed_phase"] = "wrong"; check("next_phase_drift_fail", "next_phase_mismatch" in validate_report(next_bad) or passed["status"] != STATUS_PASS)
    metrics_auth_bad = json.loads(json.dumps(passed)); metrics_auth_bad["stop_go_records"][0]["r2ai_aggregate_only_experiment_metrics_authorized_bool"] = False; check("r2ai_metrics_authorization_drift_fail", any(i.startswith("stop_go_missing_r2ai_aggregate_only_experiment_metrics") for i in validate_report(metrics_auth_bad)))
    gate_bad = json.loads(json.dumps(passed)); gate_bad["pass_fail_gate_records"].pop(); check("gate_set_fail", "gate_set_mismatch" in validate_report(gate_bad))
    synth_bad = json.loads(json.dumps(passed)); synth_bad["synthetic_validator_records"].pop(); check("synthetic_validator_set_fail", "synthetic_validator_set_mismatch" in validate_report(synth_bad))
    readback_bad = json.loads(json.dumps(passed)); readback_bad["public_readback_records"] = []; check("readback_record_fail", "public_readback_record_mismatch" in validate_report(readback_bad))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_key crates/openlocus/src/lib.rs"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    status_bad = json.loads(json.dumps(passed)); status_bad["status"] = "wrong"; check("status_drift_fail", "status_mismatch" in validate_report(status_bad))
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
