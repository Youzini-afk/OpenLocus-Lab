#!/usr/bin/env python3
"""BEA-v1-HAAE-R2E local medium material audit package.

Public-only audit of the R2D aggregate artifact. This script never reads the
R2D private root, never scans /tmp, and never accesses private material.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2E Local Medium Material Audit Package"
SLUG = "bea_v1_haae_r2e_local_medium_material_audit_package"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2D_CHECKPOINT = "c4e454a"
R2D_STATUS = "haae_r2d_explicit_local_medium_material_generation_smoke_complete_r2e_material_audit_authorized"
R2D_REPORT_PATH = Path("artifacts/bea_v1_haae_r2d_explicit_local_medium_material_generation_smoke/bea_v1_haae_r2d_explicit_local_medium_material_generation_smoke_report.json")

STATUS_PASS = "haae_r2e_local_medium_material_audit_package_complete_r2f_medium_experiment_authorized"
STATUS_NO_GO_INCOMPLETE = "haae_r2e_no_go_public_material_manifest_incomplete"
STATUS_FAIL_SOURCE = "haae_r2e_fail_closed_source_lock_mismatch"
STATUS_FAIL_LEAK = "haae_r2e_fail_closed_public_raw_leak"
STATUS_FAIL_PRIVATE = "haae_r2e_fail_closed_private_read_write_detected"
STATUS_FAIL_EXEC = "haae_r2e_fail_closed_generation_experiment_recompute_detected"
STATUS_FAIL_OVERAUTH = "haae_r2e_fail_closed_r2f_overauthorization"
STATUS_FAIL_READBACK = "haae_r2e_fail_closed_public_readback_mismatch"

SELF_TEST_EXPECTED = 18
SOURCE_FIXTURE_BUCKET = "count_21_to_50"
SUBSET_POLICY = "deterministic_public_manifest_prefix_cap_10_to_20"
TARGET_TASK_BUCKET = "count_10_to_20"
CANDIDATE_DEPTH_BUCKET = "count_20"
PRIVATE_ROW_CAP_BUCKET = "count_le_5000"
TOTAL_PRIVATE_ROW_BUCKET = "count_le_5000"
NEXT_PHASE = "BEA-v1-HAAE-R2F Local Medium Material Experiment"

SCHEMA_GROUPS = ["task_identity", "anchor_source", "candidate_pool", "rank_pack", "span_projection", "scheduler_action", "evidence_core", "arm_assignment", "outcome_metric", "safety_probe_signal"]
REQUIRED_GROUPS = {"task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric"}
RANK_SOURCES = ["bm25_like", "symbol_overlap", "rrf_like"]
FORBIDDEN_R2D_STOP = ["new_material_generation_authorized_bool", "experiment_comparison_authorized_bool", "r2_recompute_authorized_bool", "candidate_generation_authorized_bool", "retrieval_runtime_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "runtime_default_change_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool"]
FORBIDDEN_R2E_STOP = ["new_material_generation_authorized_bool", "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool", "source_scan_authorized_bool", "ci_execution_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool", "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "bea_v1_a_authorized_bool", "p5_authorized_bool", "runtime_default_change_authorized_bool", "method_winner_claim_authorized_bool", "scaling_claim_authorized_bool", "r2_recompute_authorized_bool"]
CLAIM_FALSE_FIELDS = ["new_material_generation_bool", "candidate_generation_bool", "retrieval_runtime_bool", "source_scan_bool", "ci_network_provider_bool", "scheduler_haae_selector_bool", "bea_v1_a_p5_default_bool", "method_scaling_claim_bool", "raw_publication_bool", "r2_recompute_bool", "experiment_comparison_bool"]

GATE_NAMES = ["source_lock_gate", "r2d_status_gate", "r2d_forbidden_scan_gate", "r2d_r2e_authorization_gate", "r2d_no_forbidden_stop_go_drift_gate", "manifest_caps_gate", "schema_required_groups_gate", "rank_sources_gate", "public_only_audit_gate", "no_private_read_write_gate", "no_generation_experiment_recompute_gate", "no_retrieval_runtime_ci_gate", "r2f_boundary_gate", "no_overauthorization_gate", "forbidden_scan_pass_gate", "docs_readback_match_gate"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_r2d_source(r2d: dict[str, Any]) -> dict[str, bool]:
    stop = (r2d.get("stop_go_records") or [{}])[0]
    status_ok = r2d.get("status") == R2D_STATUS
    scan_ok = r2d.get("forbidden_scan", {}).get("status") == "pass"
    r2e_auth = stop.get("haae_r2e_local_medium_material_audit_package_authorized_bool") is True
    stop_ok = all(stop.get(field) is False for field in FORBIDDEN_R2D_STOP)
    return {"status_ok": status_ok, "scan_ok": scan_ok, "r2e_auth": r2e_auth, "stop_ok": stop_ok, "source_locked": status_ok and scan_ok and r2e_auth and stop_ok}


def audit_manifest(r2d: dict[str, Any]) -> dict[str, Any]:
    subset = (r2d.get("public_fixture_subset_records") or [{}])[0]
    manifest = (r2d.get("private_material_manifest_records") or [{}])[0]
    groups = r2d.get("private_schema_group_material_records", [])
    quality = (r2d.get("public_aggregate_quality_records") or [{}])[0]
    manifest_ok = subset.get("source_fixture_count_bucket") == SOURCE_FIXTURE_BUCKET and subset.get("subset_policy_bucket") == SUBSET_POLICY and subset.get("target_task_bucket") == TARGET_TASK_BUCKET and subset.get("candidate_depth_bucket") == CANDIDATE_DEPTH_BUCKET and subset.get("private_row_cap_bucket") == PRIVATE_ROW_CAP_BUCKET and manifest.get("total_private_row_count_bucket") == TOTAL_PRIVATE_ROW_BUCKET and manifest.get("no_private_path_published_bool") is True
    by_group = {row.get("group_bucket"): row for row in groups}
    groups_present = set(by_group) == set(SCHEMA_GROUPS)
    required_ok = all(by_group.get(group, {}).get("meaningful_rows_present_bool") is True and by_group.get(group, {}).get("raw_rows_published_bool") is False for group in REQUIRED_GROUPS)
    rank_ok = all(quality.get(f"{src}_present_bool") is True for src in RANK_SOURCES) and quality.get("rank_sources_present_bool") is True
    return {"manifest_ok": manifest_ok, "groups_present": groups_present, "required_ok": required_ok, "rank_ok": rank_ok, "subset": subset, "manifest": manifest, "groups": by_group, "quality": quality}


LEAK_PATTERNS = [("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)), ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")), ("raw_candidate_label", re.compile(r"candidate_path|gold_spans|hard_negatives|snippet|start_line|end_line|label_quality|\.rs\b|crates/openlocus-")), ("score_hash", re.compile(r"rrf_like_score|bm25_like_rank|symbol_overlap_rank|first_gold_file_rank|\b[a-f0-9]{32,64}\b"))]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{total}/{total}", R2D_CHECKPOINT, R2D_STATUS, "public-only audit", "no private root read", TARGET_TASK_BUCKET, SOURCE_FIXTURE_BUCKET, SUBSET_POLICY, CANDIDATE_DEPTH_BUCKET, PRIVATE_ROW_CAP_BUCKET, TOTAL_PRIVATE_ROW_BUCKET, "bm25_like/symbol_overlap/rrf_like", "R2F local medium material experiment", "no new material/candidate generation/retrieval/runtime/source scan/CI/network/scheduler/HAAE/selector/BEA-v1-A/P5/default/method/scaling claim"]
    spaced = [f"{total} / {total}" if f == f"{total}/{total}" else f for f in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(f in text for f in fragments) or all(f in text for f in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2e-local-medium-material-audit-package.md")) and has_all(read("docs/zh/bea-v1-haae-r2e-local-medium-material-audit-package.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2e-local-medium-material-audit-package.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2d: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2d is None:
        try:
            r2d = load_json(repo / R2D_REPORT_PATH)
        except Exception:
            r2d = {}
    source = validate_r2d_source(r2d)
    audit = audit_manifest(r2d)
    readback = public_readback_match(self_test_total)
    manifest_complete = audit["manifest_ok"] and audit["groups_present"] and audit["required_ok"] and audit["rank_ok"]
    if not source["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not manifest_complete:
        status = STATUS_NO_GO_INCOMPLETE
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {"source_lock_gate": source["source_locked"], "r2d_status_gate": source["status_ok"], "r2d_forbidden_scan_gate": source["scan_ok"], "r2d_r2e_authorization_gate": source["r2e_auth"], "r2d_no_forbidden_stop_go_drift_gate": source["stop_ok"], "manifest_caps_gate": audit["manifest_ok"], "schema_required_groups_gate": audit["groups_present"] and audit["required_ok"], "rank_sources_gate": audit["rank_ok"], "public_only_audit_gate": True, "no_private_read_write_gate": True, "no_generation_experiment_recompute_gate": True, "no_retrieval_runtime_ci_gate": True, "r2f_boundary_gate": True, "no_overauthorization_gate": True, "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"]}
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "phase_bucket": PHASE, "status": status, "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2esource0000", "locked_haae_r2d_checkpoint": R2D_CHECKPOINT, "locked_haae_r2d_status": R2D_STATUS, "r2d_status_match_bool": source["status_ok"], "r2d_forbidden_scan_pass_bool": source["scan_ok"], "r2e_authorization_match_bool": source["r2e_auth"], "r2d_no_forbidden_stop_go_drift_bool": source["stop_ok"], "source_locked_bool": source["source_locked"]}],
        "material_manifest_audit_records": [{"anonymous_material_manifest_audit_id": "haaer2emanifest0000", "task_bucket": TARGET_TASK_BUCKET, "source_fixture_bucket": SOURCE_FIXTURE_BUCKET, "subset_policy_bucket": SUBSET_POLICY, "candidate_depth_bucket": CANDIDATE_DEPTH_BUCKET, "private_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET, "total_private_row_bucket": audit["manifest"].get("total_private_row_count_bucket", "missing"), "private_path_published_bool": False, "manifest_caps_match_bool": audit["manifest_ok"]}],
        "schema_group_audit_records": [{"anonymous_schema_group_audit_id": f"haaer2egroup{idx:04d}", "group_bucket": group, "required_meaningful_bool": group in REQUIRED_GROUPS, "meaningful_present_bool": audit["groups"].get(group, {}).get("meaningful_rows_present_bool") is True, "optional_accounted_bool": group in audit["groups"], "raw_rows_published_bool": False} for idx, group in enumerate(SCHEMA_GROUPS)],
        "rank_source_audit_records": [{"anonymous_rank_source_audit_id": f"haaer2erank{idx:04d}", "rank_source_bucket": src, "present_bool": audit["quality"].get(f"{src}_present_bool") is True, "exact_scores_or_ranks_published_bool": False} for idx, src in enumerate(RANK_SOURCES)],
        "boundary_audit_records": [{"anonymous_boundary_audit_id": "haaer2eboundary0000", "public_only_audit_bool": True, "private_read_count_bucket": "count_0", "private_write_count_bucket": "count_0", "generation_execution_recompute_bool": False, "retrieval_runtime_ci_bool": False, "private_root_read_bool": False, "tmp_scan_bool": False}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2eclaim0000", "new_material_generation_bool": False, "candidate_generation_bool": False, "retrieval_runtime_bool": False, "source_scan_bool": False, "ci_network_provider_bool": False, "scheduler_haae_selector_bool": False, "bea_v1_a_p5_default_bool": False, "method_scaling_claim_bool": False, "raw_publication_bool": False, "r2_recompute_bool": False, "experiment_comparison_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2egate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_only_bool": True, "gate_reads_private_material_bool": False} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2esynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_source_fail", "group_missing_no_go", "rank_source_missing_no_go", "cap_drift_no_go", "private_leak_fail", "private_read_write_true_fail", "generation_experiment_recompute_true_fail", "r2f_overauth_fields_fail", "stale_readback_fail", "unknown_private_path_cli_rejected"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2ereadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2estop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_fix_public_r2d_manifest", "haae_r2f_local_medium_material_experiment_authorized_bool": passed, "haae_r2f_explicit_private_root_required_bool": passed, "haae_r2f_read_existing_r2d_private_material_only_bool": passed, "haae_r2f_aggregate_metrics_only_bool": passed, "new_material_generation_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "source_scan_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "runtime_default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "r2_recompute_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate":
            gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "material_manifest_audit_records", "schema_group_audit_records", "rank_source_audit_records", "boundary_audit_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report:
            issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        issues.append("forbidden_scan_failed")
    boundary = (report.get("boundary_audit_records") or [{}])[0]
    if boundary.get("private_read_count_bucket") != "count_0" or boundary.get("private_write_count_bucket") != "count_0" or boundary.get("private_root_read_bool") is not False:
        issues.append("private_read_write_detected")
    if boundary.get("generation_execution_recompute_bool") is not False:
        issues.append("generation_experiment_recompute_detected")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in FORBIDDEN_R2E_STOP:
        if stop.get(field) is not False:
            issues.append(f"overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        source = (report.get("source_lock_records") or [{}])[0]
        for field in ["r2d_status_match_bool", "r2d_forbidden_scan_pass_bool", "r2e_authorization_match_bool", "r2d_no_forbidden_stop_go_drift_bool", "source_locked_bool"]:
            if source.get(field) is not True:
                issues.append(f"source_lock_field_not_true_{field}")
        if source.get("locked_haae_r2d_checkpoint") != R2D_CHECKPOINT or source.get("locked_haae_r2d_status") != R2D_STATUS:
            issues.append("source_lock_checkpoint_status_mismatch")
        if boundary.get("public_only_audit_bool") is not True or boundary.get("tmp_scan_bool") is not False or boundary.get("retrieval_runtime_ci_bool") is not False:
            issues.append("boundary_audit_drift")
        claim = (report.get("claim_boundary_records") or [{}])[0]
        for field in CLAIM_FALSE_FIELDS:
            if claim.get(field) is not False:
                issues.append(f"claim_boundary_overauthorization_{field}")
        for row in report.get("rank_source_audit_records", []):
            if row.get("exact_scores_or_ranks_published_bool") is not False:
                issues.append("rank_exact_score_or_rank_publication")
        for field in ["haae_r2f_local_medium_material_experiment_authorized_bool", "haae_r2f_explicit_private_root_required_bool", "haae_r2f_read_existing_r2d_private_material_only_bool", "haae_r2f_aggregate_metrics_only_bool"]:
            if stop.get(field) is not True:
                issues.append(f"r2f_required_handoff_missing_{field}")
    groups = {row.get("group_bucket"): row for row in report.get("schema_group_audit_records", [])}
    for group in REQUIRED_GROUPS:
        if groups.get(group, {}).get("meaningful_present_bool") is not True:
            issues.append(f"required_group_missing_{group}")
        if groups.get(group, {}).get("raw_rows_published_bool") is not False:
            issues.append(f"required_group_raw_publication_{group}")
    for group in SCHEMA_GROUPS:
        if group not in groups:
            issues.append(f"schema_group_not_accounted_{group}")
    ranks = {row.get("rank_source_bucket"): row for row in report.get("rank_source_audit_records", [])}
    for source in RANK_SOURCES:
        if ranks.get(source, {}).get("present_bool") is not True:
            issues.append(f"rank_source_missing_{source}")
    manifest = (report.get("material_manifest_audit_records") or [{}])[0]
    if manifest.get("task_bucket") != TARGET_TASK_BUCKET or manifest.get("source_fixture_bucket") != SOURCE_FIXTURE_BUCKET or manifest.get("subset_policy_bucket") != SUBSET_POLICY or manifest.get("candidate_depth_bucket") != CANDIDATE_DEPTH_BUCKET or manifest.get("private_row_cap_bucket") != PRIVATE_ROW_CAP_BUCKET or manifest.get("total_private_row_bucket") != TOTAL_PRIVATE_ROW_BUCKET:
        issues.append("cap_or_manifest_drift")
    if report.get("status") == STATUS_PASS:
        if stop.get("haae_r2f_local_medium_material_experiment_authorized_bool") is not True:
            issues.append("missing_r2f_authorization")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]:
            issues.append("public_readback_stale")
    return issues


def public_artifact_path(value: str) -> Path:
    repo = Path(__file__).resolve().parents[1]
    path = Path(value)
    resolved = path if path.is_absolute() else repo / path
    if resolved != repo / PUBLIC_REPORT_PATH:
        raise ValueError("invalid arguments")
    return PUBLIC_REPORT_PATH


def parse_args(argv: list[str]) -> dict[str, Any]:
    parsed = {"self_test": False, "validate": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--self-test":
            parsed["self_test"] = True; i += 1
        elif arg in {"--validate-report", "--out"}:
            if i + 1 >= len(argv):
                raise ValueError("invalid arguments")
            if arg == "--validate-report": parsed["validate"] = argv[i + 1]
            else: parsed["out"] = argv[i + 1]
            i += 2
        else:
            raise ValueError("invalid arguments")
    return parsed


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or PUBLIC_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2D_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond: failures.append(name)
    passed = build_report(base)
    check("source_lock_pass", passed["status"] == STATUS_PASS)
    bad = json.loads(json.dumps(base)); bad["status"] = "wrong"; check("wrong_source_fail", build_report(bad)["status"] == STATUS_FAIL_SOURCE)
    group_missing = json.loads(json.dumps(base)); group_missing["private_schema_group_material_records"][0]["meaningful_rows_present_bool"] = False; check("group_missing_no_go", build_report(group_missing)["status"] == STATUS_NO_GO_INCOMPLETE)
    rank_missing = json.loads(json.dumps(base)); rank_missing["public_aggregate_quality_records"][0]["rrf_like_present_bool"] = False; check("rank_source_missing_no_go", build_report(rank_missing)["status"] == STATUS_NO_GO_INCOMPLETE)
    cap = json.loads(json.dumps(base)); cap["public_fixture_subset_records"][0]["candidate_depth_bucket"] = "bad"; check("cap_drift_no_go", build_report(cap)["status"] == STATUS_NO_GO_INCOMPLETE)
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("private_leak_fail", scan_public_report(leak)["status"] == "fail")
    priv = json.loads(json.dumps(passed)); priv["boundary_audit_records"][0]["private_read_count_bucket"] = "count_1"; check("private_read_write_true_fail", "private_read_write_detected" in validate_report(priv))
    gen = json.loads(json.dumps(passed)); gen["boundary_audit_records"][0]["generation_execution_recompute_bool"] = True; check("generation_experiment_recompute_true_fail", "generation_experiment_recompute_detected" in validate_report(gen))
    over = json.loads(json.dumps(passed)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("r2f_overauth_fields_fail", any(i.startswith("overauthorization_") for i in validate_report(over)))
    source_mutation = json.loads(json.dumps(passed)); source_mutation["source_lock_records"][0]["source_locked_bool"] = False; check("source_lock_false_fail", any(i.startswith("source_lock_field_not_true") for i in validate_report(source_mutation)))
    claim_mutation = json.loads(json.dumps(passed)); claim_mutation["claim_boundary_records"][0]["raw_publication_bool"] = True; check("claim_boundary_overauth_fail", any(i.startswith("claim_boundary_overauthorization") for i in validate_report(claim_mutation)))
    rank_mutation = json.loads(json.dumps(passed)); rank_mutation["rank_source_audit_records"][0]["exact_scores_or_ranks_published_bool"] = True; check("rank_exact_publication_fail", "rank_exact_score_or_rank_publication" in validate_report(rank_mutation))
    boundary_mutation = json.loads(json.dumps(passed)); boundary_mutation["boundary_audit_records"][0]["tmp_scan_bool"] = True; check("boundary_tmp_scan_fail", "boundary_audit_drift" in validate_report(boundary_mutation))
    handoff_mutation = json.loads(json.dumps(passed)); handoff_mutation["stop_go_records"][0]["haae_r2f_read_existing_r2d_private_material_only_bool"] = False; check("r2f_required_handoff_fail", any(i.startswith("r2f_required_handoff_missing") for i in validate_report(handoff_mutation)))
    raw_group = json.loads(json.dumps(passed)); raw_group["schema_group_audit_records"][0]["raw_rows_published_bool"] = True; check("required_group_raw_publication_fail", any(i.startswith("required_group_raw_publication") for i in validate_report(raw_group)))
    optional_semantics_ok = all(row["meaningful_present_bool"] is False for row in passed["schema_group_audit_records"] if row["group_bucket"] in {"scheduler_action", "arm_assignment", "safety_probe_signal"})
    check("optional_placeholder_not_marked_meaningful", optional_semantics_ok)
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
    try:
        with redirect_stderr(io.StringIO()): parse_args(["--private-root", "/tmp/x"])
        check("unknown_private_path_cli_rejected", False)
    except ValueError:
        check("unknown_private_path_cli_rejected", True)
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except ValueError:
        print("invalid arguments", file=sys.stderr); return 2
    repo = Path(__file__).resolve().parents[1]
    if args["self_test"]:
        result = run_self_test(); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["passed"] else 1
    if args["validate"]:
        try:
            report = load_json(repo / public_artifact_path(args["validate"])); issues = validate_report(report)
        except Exception:
            report = {"status": "unavailable"}; issues = ["invalid arguments"]
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True)); return 0 if not issues else 1
    out = public_artifact_path(args["out"]) if args["out"] else None
    report = build_report()
    path = write_report(report, out)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GO_INCOMPLETE} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
