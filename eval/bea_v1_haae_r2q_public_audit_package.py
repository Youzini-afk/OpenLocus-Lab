#!/usr/bin/env python3
"""BEA-v1-HAAE-R2Q path-cue robustness material public audit package."""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2Q Path-Cue Robustness Material Public Audit Package"
SLUG = "bea_v1_haae_r2q_public_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2P_CHECKPOINT = "1f721dd"
R2P_STATUS = "haae_r2p_path_cue_robustness_material_generation_complete_r2q_public_audit_authorized"
R2O_CHECKPOINT = "4ffc9eb"
R2P_REPORT_PATH = Path("artifacts/bea_v1_haae_r2p_path_cue_robustness_material_generation/bea_v1_haae_r2p_path_cue_robustness_material_generation_report.json")
STATUS_PASS = "haae_r2q_public_audit_package_complete_r2r_local_robustness_experiment_authorized"
STATUS_FAIL_SOURCE = "haae_r2q_fail_closed_source_lock_mismatch"
STATUS_FAIL_MATERIAL = "haae_r2q_fail_closed_material_property_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2q_fail_closed_claim_boundary_mismatch"
STATUS_FAIL_LEAK = "haae_r2q_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2q_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 18
NEXT_PHASE = "BEA-v1-HAAE-R2R Path-Cue Robustness Experiment"
VARIANTS = ["original", "path_scrambled", "extension_bucket_preserved", "directory_depth_preserved", "control_baseline_strengthened"]
RANK_SOURCES = ["path_prior", "path_scrambled_prior", "extension_bucket_prior", "directory_depth_prior", "control_baseline_strengthened", "rrf_variant_fusion"]
REQUIRED_GROUPS = {"task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric", "span_projection"}
CLAIM_FALSE_FIELDS = ["experiment_metrics_bool", "old_private_root_read_bool", "retrieval_runtime_bool", "source_scan_outside_fixture_bool", "ci_network_provider_clone_bool", "scheduler_haae_selector_bool", "bea_v1_a_p5_default_bool", "method_scaling_claim_bool", "raw_publication_bool"]
STOP_FALSE_FIELDS = ["experiment_metrics_authorized_bool", "new_material_generation_authorized_bool", "candidate_generation_beyond_material_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_outside_fixture_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool"]
GATE_NAMES = ["r2p_source_locked_gate", "r2p_status_gate", "r2p_r2q_authorization_gate", "explicit_opt_in_readback_gate", "private_write_nonzero_gate", "target_20_gate", "candidate_depth_40_gate", "variant_coverage_gate", "rank_source_coverage_gate", "required_schema_groups_meaningful_gate", "gold_private_only_gate", "ranking_gold_false_gate", "no_experiment_metrics_gate", "aggregate_only_gate", "root_safety_gate", "public_only_audit_gate", "r2r_only_authorization_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2p(r2p: dict[str, Any]) -> dict[str, bool]:
    src = (r2p.get("source_lock_records") or [{}])[0]
    mode = (r2p.get("execution_mode_records") or [{}])[0]
    fixture = (r2p.get("fixture_subset_records") or [{}])[0]
    quality = (r2p.get("quality_control_records") or [{}])[0]
    gold = (r2p.get("gold_policy_records") or [{}])[0]
    root = (r2p.get("root_safety_records") or [{}])[0]
    claim = (r2p.get("claim_boundary_records") or [{}])[0]
    stop = (r2p.get("stop_go_records") or [{}])[0]
    variants = {row.get("variant_bucket"): row for row in r2p.get("variant_material_records", [])}
    ranks = {row.get("rank_source_bucket"): row for row in r2p.get("rank_source_material_records", [])}
    groups = {row.get("group_bucket"): row for row in r2p.get("schema_group_material_records", [])}
    status_ok = r2p.get("status") == R2P_STATUS
    scan_ok = r2p.get("forbidden_scan", {}).get("status") == "pass"
    source_ok = src.get("locked_haae_r2o_checkpoint") == R2O_CHECKPOINT and src.get("source_locked_bool") is True
    auth_ok = stop.get("haae_r2q_public_audit_package_authorized_bool") is True and stop.get("r2q_public_only_audit_bool") is True
    stop_ok = all(stop.get(field) is False for field in STOP_FALSE_FIELDS)
    claim_ok = all(claim.get(field) is False for field in CLAIM_FALSE_FIELDS)
    explicit_ok = mode.get("explicit_opt_in_bool") is True and mode.get("generation_performed_bool") is True
    write_ok = mode.get("private_write_bucket") not in {None, "count_0"}
    fixture_ok = fixture.get("target_task_count_bucket") == "target_20_tasks" and fixture.get("candidate_depth_cap_bucket") == "candidate_depth_40" and fixture.get("raw_fixture_rows_published_bool") is False
    variants_ok = set(variants) == set(VARIANTS) and all(variants[v].get("present_bool") is True and variants[v].get("raw_variant_rows_published_bool") is False for v in VARIANTS)
    ranks_ok = set(ranks) == set(RANK_SOURCES) and all(ranks[s].get("present_bool") is True and ranks[s].get("exact_ranks_scores_public_bool") is False for s in RANK_SOURCES)
    groups_ok = all(groups.get(g, {}).get("meaningful_rows_present_bool") is True and groups.get(g, {}).get("raw_rows_published_bool") is False for g in REQUIRED_GROUPS)
    gold_ok = gold.get("gold_labels_private_only_bool") is True and gold.get("coverage_validation_only_bool") is True and gold.get("ranking_policy_uses_gold_bool") is False and gold.get("raw_gold_values_published_bool") is False
    no_metrics_ok = quality.get("no_experiment_metrics_computed_bool") is True and claim.get("experiment_metrics_bool") is False
    aggregate_ok = quality.get("public_aggregate_only_bool") is True
    root_ok = root.get("root_boundary_pass_bool") is True and root.get("no_path_publication_bool") is True and root.get("no_old_private_root_read_bool") is True and root.get("no_root_discovery_bool") is True
    material_ok = explicit_ok and write_ok and fixture_ok and variants_ok and ranks_ok and groups_ok and gold_ok and no_metrics_ok and aggregate_ok and root_ok
    return {"status_ok": status_ok, "scan_ok": scan_ok, "source_ok": source_ok, "auth_ok": auth_ok, "stop_ok": stop_ok, "claim_ok": claim_ok, "explicit_ok": explicit_ok, "write_ok": write_ok, "fixture_ok": fixture_ok, "variants_ok": variants_ok, "ranks_ok": ranks_ok, "groups_ok": groups_ok, "gold_ok": gold_ok, "no_metrics_ok": no_metrics_ok, "aggregate_ok": aggregate_ok, "root_ok": root_ok, "material_ok": material_ok, "source_locked": status_ok and scan_ok and source_ok and auth_ok and stop_ok and claim_ok}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|source_path|variant_path|\"gold_spans\"|\"hard_negatives\"|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash_exact", re.compile(r"private_score|private_rank|hit_rate|top10|top5|top1|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2P_CHECKPOINT, R2P_STATUS, "explicit opt-in", "private write nonzero", "target 20", "depth 40", "5 variants", "6 rank sources", "gold private only", "ranking gold false", "no experiment metrics", NEXT_PHASE, "no new material generation/CI/retrieval/runtime/source scan/default/method/scaling"]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2q-path-cue-robustness-material-public-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2q-path-cue-robustness-material-public-audit-package.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2q-path-cue-robustness-material-public-audit-package.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2p: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2p is None:
        try: r2p = load_json(repo / R2P_REPORT_PATH)
        except Exception: r2p = {}
    audit = audit_r2p(r2p)
    readback = public_readback_match(self_test_total)
    if not audit["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not audit["material_ok"]:
        status = STATUS_FAIL_MATERIAL
    elif not audit["claim_ok"] or not audit["stop_ok"]:
        status = STATUS_FAIL_BOUNDARY
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"r2p_source_locked_gate": audit["source_locked"], "r2p_status_gate": audit["status_ok"], "r2p_r2q_authorization_gate": audit["auth_ok"], "explicit_opt_in_readback_gate": audit["explicit_ok"], "private_write_nonzero_gate": audit["write_ok"], "target_20_gate": audit["fixture_ok"], "candidate_depth_40_gate": audit["fixture_ok"], "variant_coverage_gate": audit["variants_ok"], "rank_source_coverage_gate": audit["ranks_ok"], "required_schema_groups_meaningful_gate": audit["groups_ok"], "gold_private_only_gate": audit["gold_ok"], "ranking_gold_false_gate": audit["gold_ok"], "no_experiment_metrics_gate": audit["no_metrics_ok"], "aggregate_only_gate": audit["aggregate_ok"], "root_safety_gate": audit["root_ok"], "public_only_audit_gate": True, "r2r_only_authorization_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2qsource0000", "locked_haae_r2p_checkpoint": R2P_CHECKPOINT, "locked_haae_r2p_status": R2P_STATUS, "locked_r2p_source_r2o_checkpoint": R2O_CHECKPOINT, "r2p_status_match_bool": audit["status_ok"], "r2p_forbidden_scan_pass_bool": audit["scan_ok"], "r2p_r2q_authorization_match_bool": audit["auth_ok"], "r2p_no_forbidden_stop_go_drift_bool": audit["stop_ok"], "source_locked_bool": audit["source_locked"]}],
        "material_property_audit_records": [{"anonymous_material_property_audit_id": "haaer2qmaterial0000", "explicit_opt_in_bool": audit["explicit_ok"], "private_write_nonzero_bool": audit["write_ok"], "target_task_count_bucket": "target_20_tasks", "candidate_depth_bucket": "candidate_depth_40", "required_schema_groups_meaningful_bool": audit["groups_ok"], "no_experiment_metrics_bool": audit["no_metrics_ok"], "aggregate_only_bool": audit["aggregate_ok"], "root_safety_pass_bool": audit["root_ok"], "material_properties_match_bool": audit["material_ok"]}],
        "variant_audit_records": [{"anonymous_variant_audit_id": f"haaer2qvariant{idx:04d}", "variant_bucket": variant, "present_bool": audit["variants_ok"], "raw_variant_rows_published_bool": False} for idx, variant in enumerate(VARIANTS)],
        "rank_source_audit_records": [{"anonymous_rank_source_audit_id": f"haaer2qrank{idx:04d}", "rank_source_bucket": source, "present_bool": audit["ranks_ok"], "exact_ranks_scores_published_bool": False} for idx, source in enumerate(RANK_SOURCES)],
        "schema_group_audit_records": [{"anonymous_schema_group_audit_id": f"haaer2qgroup{idx:04d}", "group_bucket": group, "meaningful_bool": audit["groups_ok"], "raw_rows_published_bool": False} for idx, group in enumerate(sorted(REQUIRED_GROUPS))],
        "gold_policy_audit_records": [{"anonymous_gold_policy_audit_id": "haaer2qgold0000", "gold_private_only_bool": audit["gold_ok"], "ranking_gold_false_bool": audit["gold_ok"], "raw_gold_values_published_bool": False}],
        "boundary_audit_records": [{"anonymous_boundary_audit_id": "haaer2qboundary0000", "public_only_audit_bool": True, "private_root_read_bool": False, "private_material_read_bool": False, "recompute_bool": False, "experiment_metrics_bool": False, "material_generation_bool": False, "retrieval_runtime_source_scan_bool": False, "ci_network_provider_bool": False, "scheduler_selector_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2qclaim0000", "method_winner_claim_bool": False, "default_runtime_claim_bool": False, "scaling_claim_bool": False, "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_bool": False, "scheduler_selector_bool": False, "bea_v1_a_p5_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2qgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2qsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2p_status_fail", "missing_variant_fail", "missing_rank_fail", "missing_group_fail", "gold_policy_fail", "metrics_fail", "root_safety_fail", "overauth_fail", "leak_fail", "stale_readback_fail", "safe_parser_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2qreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2qstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_reaudit_r2p_public_artifact", "haae_r2r_path_cue_robustness_experiment_authorized_bool": passed, "r2r_local_explicit_private_root_required_bool": passed, "r2r_reads_existing_r2p_private_material_only_bool": passed, "r2r_aggregate_metrics_only_bool": passed, "new_material_generation_authorized_bool": False, "ci_execution_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "material_property_audit_records", "variant_audit_records", "rank_source_audit_records", "schema_group_audit_records", "gold_policy_audit_records", "boundary_audit_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2p_checkpoint") != R2P_CHECKPOINT or source.get("locked_haae_r2p_status") != R2P_STATUS or source.get("locked_r2p_source_r2o_checkpoint") != R2O_CHECKPOINT: issues.append("source_lock_mismatch")
    for field in ["r2p_status_match_bool", "r2p_forbidden_scan_pass_bool", "r2p_r2q_authorization_match_bool", "r2p_no_forbidden_stop_go_drift_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    material = (report.get("material_property_audit_records") or [{}])[0]
    for field in ["explicit_opt_in_bool", "private_write_nonzero_bool", "required_schema_groups_meaningful_bool", "no_experiment_metrics_bool", "aggregate_only_bool", "root_safety_pass_bool", "material_properties_match_bool"]:
        if material.get(field) is not True: issues.append(f"material_property_{field}")
    if material.get("target_task_count_bucket") != "target_20_tasks" or material.get("candidate_depth_bucket") != "candidate_depth_40": issues.append("material_bounds_mismatch")
    variants = {row.get("variant_bucket"): row for row in report.get("variant_audit_records", [])}
    if set(variants) != set(VARIANTS): issues.append("variant_set_mismatch")
    for variant in VARIANTS:
        row = variants.get(variant, {})
        if row.get("present_bool") is not True or row.get("raw_variant_rows_published_bool") is not False: issues.append(f"variant_{variant}_mismatch")
    ranks = {row.get("rank_source_bucket"): row for row in report.get("rank_source_audit_records", [])}
    if set(ranks) != set(RANK_SOURCES): issues.append("rank_source_set_mismatch")
    for source_name in RANK_SOURCES:
        row = ranks.get(source_name, {})
        if row.get("present_bool") is not True or row.get("exact_ranks_scores_published_bool") is not False: issues.append(f"rank_source_{source_name}_mismatch")
    groups = {row.get("group_bucket"): row for row in report.get("schema_group_audit_records", [])}
    if set(groups) != REQUIRED_GROUPS: issues.append("schema_group_set_mismatch")
    for group in REQUIRED_GROUPS:
        row = groups.get(group, {})
        if row.get("meaningful_bool") is not True or row.get("raw_rows_published_bool") is not False: issues.append(f"schema_group_{group}_mismatch")
    gold = (report.get("gold_policy_audit_records") or [{}])[0]
    if gold.get("gold_private_only_bool") is not True or gold.get("ranking_gold_false_bool") is not True or gold.get("raw_gold_values_published_bool") is not False: issues.append("gold_policy_mismatch")
    boundary = (report.get("boundary_audit_records") or [{}])[0]
    if boundary.get("public_only_audit_bool") is not True: issues.append("boundary_not_public_only")
    for field in ["private_root_read_bool", "private_material_read_bool", "recompute_bool", "experiment_metrics_bool", "material_generation_bool", "retrieval_runtime_source_scan_bool", "ci_network_provider_bool", "scheduler_selector_bool"]:
        if boundary.get(field) is not False: issues.append(f"boundary_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["method_winner_claim_bool", "default_runtime_claim_bool", "scaling_claim_bool", "new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_bool", "scheduler_selector_bool", "bea_v1_a_p5_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("next_allowed_phase_mismatch")
        for field in ["haae_r2r_path_cue_robustness_experiment_authorized_bool", "r2r_local_explicit_private_root_required_bool", "r2r_reads_existing_r2p_private_material_only_bool", "r2r_aggregate_metrics_only_bool"]:
            if stop.get(field) is not True: issues.append(f"stop_go_{field}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
    for field in ["new_material_generation_authorized_bool", "ci_execution_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "raw_publication_authorized_bool"]:
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
            if arg == "--validate-report": parsed["validate"] = argv[i + 1]
            else: parsed["out"] = argv[i + 1]
            i += 2
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
    base = load_json(repo / R2P_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS)
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2p_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    missing_variant = json.loads(json.dumps(base)); missing_variant["variant_material_records"] = missing_variant["variant_material_records"][:-1]; check("missing_variant_fail", build_report(missing_variant)["status"] == STATUS_FAIL_MATERIAL)
    missing_rank = json.loads(json.dumps(base)); missing_rank["rank_source_material_records"][0]["present_bool"] = False; check("missing_rank_fail", build_report(missing_rank)["status"] == STATUS_FAIL_MATERIAL)
    missing_group = json.loads(json.dumps(base)); missing_group["schema_group_material_records"][0]["meaningful_rows_present_bool"] = False; check("missing_group_fail", build_report(missing_group)["status"] == STATUS_FAIL_MATERIAL)
    gold_bad = json.loads(json.dumps(base)); gold_bad["gold_policy_records"][0]["ranking_policy_uses_gold_bool"] = True; check("gold_policy_fail", build_report(gold_bad)["status"] == STATUS_FAIL_MATERIAL)
    metrics_bad = json.loads(json.dumps(base)); metrics_bad["quality_control_records"][0]["no_experiment_metrics_computed_bool"] = False; check("metrics_fail", build_report(metrics_bad)["status"] == STATUS_FAIL_MATERIAL)
    root_bad = json.loads(json.dumps(base)); root_bad["root_safety_records"][0]["root_boundary_pass_bool"] = False; check("root_safety_fail", build_report(root_bad)["status"] == STATUS_FAIL_MATERIAL)
    source_drift = json.loads(json.dumps(passed)); source_drift["source_lock_records"][0]["r2p_forbidden_scan_pass_bool"] = False; check("source_field_drift_fail", "source_lock_r2p_forbidden_scan_pass_bool" in validate_report(source_drift))
    variant_drift = json.loads(json.dumps(passed)); variant_drift["variant_audit_records"][0]["present_bool"] = False; check("variant_bool_drift_fail", any(i.startswith("variant_") for i in validate_report(variant_drift)))
    rank_drift = json.loads(json.dumps(passed)); rank_drift["rank_source_audit_records"][0]["exact_ranks_scores_published_bool"] = True; check("rank_bool_drift_fail", any(i.startswith("rank_source_") for i in validate_report(rank_drift)))
    boundary_drift = json.loads(json.dumps(passed)); boundary_drift["boundary_audit_records"][0]["private_material_read_bool"] = True; check("boundary_drift_fail", "boundary_private_material_read_bool" in validate_report(boundary_drift))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    over = json.loads(json.dumps(passed)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(over)))
    next_drift = json.loads(json.dumps(passed)); next_drift["stop_go_records"][0]["next_allowed_phase"] = "wrong"; check("next_phase_drift_fail", "next_allowed_phase_mismatch" in validate_report(next_drift))
    gate_drift = json.loads(json.dumps(passed)); gate_drift["pass_fail_gate_records"][0]["gate_passed_bool"] = False; check("gate_drift_fail", any(i.startswith("gate_failed_") for i in validate_report(gate_drift)))
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("safe_parser_fail", False)
    except ValueError: check("safe_parser_fail", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try: args = parse_args(argv)
    except ValueError:
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
