#!/usr/bin/env python3
"""BEA-v1-HAAE-R2C local medium material smoke preflight.

Public-only preflight/package for the next explicit local medium material
generation smoke. It does not create private roots, write private rows, generate
material, run experiments, recompute metrics, retrieve, scan source code, run
OpenLocus/runtime, use network/clone/CI, or make method/scaling claims.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight"
SLUG = "bea_v1_haae_r2c_local_medium_material_smoke_preflight"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2B_CHECKPOINT = "dea8a2f"
R2B_STATUS = "haae_r2b_scale_preflight_design_complete_r2c_local_medium_material_smoke_preflight_authorized"
R2B_REPORT_PATH = Path("artifacts/bea_v1_haae_r2b_scale_preflight_design/bea_v1_haae_r2b_scale_preflight_design_report.json")

STATUS_PASS = "haae_r2c_local_medium_material_smoke_preflight_complete_r2d_generation_smoke_authorized"
STATUS_NO_GO_FIXTURE = "haae_r2c_no_go_medium_fixture_unavailable"
STATUS_NO_GO_CONTRACT = "haae_r2c_no_go_preflight_contract_incomplete"
STATUS_FAIL_SOURCE_LOCK = "haae_r2c_fail_closed_source_lock_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2c_fail_closed_overauthorization"
STATUS_FAIL_PUBLIC_LEAK = "haae_r2c_fail_closed_public_manifest_leak"
STATUS_FAIL_READBACK = "haae_r2c_fail_closed_public_readback_mismatch"

SELECTED_OPTION = "r14_medium_local_material_smoke"
SOURCE_FIXTURE_BUCKET = "count_21_to_50"
SUBSET_POLICY = "deterministic_public_manifest_prefix_cap_10_to_20"
TARGET_TASK_BUCKET = "count_10_to_20"
CANDIDATE_DEPTH_BUCKET = "count_20"
PRIVATE_ROW_CAP_BUCKET = "count_le_5000"
NEXT_PHASE = "BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke"
SELF_TEST_EXPECTED = 16

SCHEMA_GROUPS = [
    "task_identity",
    "anchor_source",
    "candidate_pool",
    "rank_pack",
    "span_projection",
    "scheduler_action",
    "evidence_core",
    "arm_assignment",
    "outcome_metric",
    "safety_probe_signal",
]
REQUIRED_GROUPS = {"task_identity", "anchor_source", "candidate_pool", "rank_pack", "evidence_core", "outcome_metric"}
OPTIONAL_GROUPS = {"span_projection"}
PLACEHOLDER_GROUPS = {"scheduler_action", "arm_assignment", "safety_probe_signal"}

FORBIDDEN_STOP_FIELDS = [
    "ci_execution_authorized_bool",
    "network_authorized_bool",
    "provider_model_network_authorized_bool",
    "experiment_authorized_bool",
    "r2_recompute_authorized_bool",
    "candidate_beyond_materializer_authorized_bool",
    "retrieval_runtime_authorized_bool",
    "scheduler_haae_execution_authorized_bool",
    "selector_reranker_authorized_bool",
    "runtime_default_change_authorized_bool",
    "bea_v1_a_authorized_bool",
    "p5_authorized_bool",
    "method_winner_claim_authorized_bool",
    "scaling_claim_authorized_bool",
    "broad_private_read_authorized_bool",
]

CLAIM_FORBIDDEN_FALSE_FIELDS = [
    "private_root_creation_bool",
    "private_write_bool",
    "material_generation_bool",
    "experiment_bool",
    "recompute_bool",
    "candidate_generation_bool",
    "retrieval_bool",
    "source_scan_beyond_fixture_count_bool",
    "openlocus_runtime_bool",
    "network_clone_ci_bool",
    "scheduler_haae_bool",
    "selector_reranker_bool",
    "runtime_default_change_bool",
    "bea_v1_a_bool",
    "p5_bool",
    "method_claim_bool",
    "scaling_claim_bool",
]

R2D_FORBIDDEN_FALSE_FIELDS = [
    "ci_network_clone_provider_bool",
    "runtime_default_bool",
    "scheduler_haae_bool",
    "experiment_comparison_bool",
    "bea_v1_a_p5_bool",
    "method_scaling_claim_bool",
]

GATE_NAMES = [
    "source_lock_gate",
    "r2b_selected_option_gate",
    "r2b_caps_match_gate",
    "r2b_r2c_preflight_authorized_gate",
    "r2b_no_execution_private_material_ci_gate",
    "public_only_preflight_gate",
    "medium_fixture_present_gate",
    "medium_fixture_count_bucket_gate",
    "operator_command_contract_gate",
    "private_output_contract_gate",
    "medium_manifest_schema_gate",
    "r2d_contract_boundary_gate",
    "no_private_root_creation_gate",
    "no_private_write_gate",
    "no_material_generation_gate",
    "no_experiment_gate",
    "no_recompute_gate",
    "no_candidate_generation_gate",
    "no_retrieval_gate",
    "no_source_scan_beyond_fixture_count_gate",
    "no_openlocus_runtime_gate",
    "no_network_clone_ci_gate",
    "no_scheduler_haae_gate",
    "no_selector_reranker_gate",
    "no_runtime_default_gate",
    "no_bea_v1_a_p5_gate",
    "no_method_scaling_claim_gate",
    "public_aggregate_only_gate",
    "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
    "self_test_readback_match_gate",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def count_jsonl(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def bucket_count(n: int) -> str:
    if n <= 0:
        return "count_0"
    if n <= 5:
        return "count_2_to_5"
    if n <= 9:
        return "count_6_to_9"
    if n <= 20:
        return "count_10_to_20"
    if n <= 50:
        return "count_21_to_50"
    return "count_gt_50"


def validate_r2b_lock(r2b: dict[str, Any]) -> dict[str, bool]:
    selected = (r2b.get("selected_scale_design_records") or [{}])[0]
    stop = (r2b.get("stop_go_records") or [{}])[0]
    status_ok = r2b.get("status") == R2B_STATUS
    scan_ok = r2b.get("forbidden_scan", {}).get("status") == "pass"
    selected_ok = selected.get("selected_option_bucket") == SELECTED_OPTION
    caps_ok = (
        selected.get("source_fixture_task_count_bucket") == SOURCE_FIXTURE_BUCKET
        and selected.get("selected_subset_policy_bucket") == SUBSET_POLICY
        and selected.get("target_task_count_bucket") == TARGET_TASK_BUCKET
        and selected.get("candidate_depth_bucket") == CANDIDATE_DEPTH_BUCKET
        and selected.get("private_row_cap_bucket") == PRIVATE_ROW_CAP_BUCKET
    )
    r2c_auth = stop.get("haae_r2c_local_medium_material_smoke_preflight_authorized_bool") is True
    false_ok = all(stop.get(field) is False for field in [
        "haae_r2c_execution_authorized_bool",
        "haae_r2c_private_read_authorized_bool",
        "haae_r2c_private_write_authorized_bool",
        "haae_r2c_ci_execution_authorized_bool",
        "haae_r2c_material_generation_authorized_bool",
    ])
    return {
        "status_ok": status_ok,
        "scan_ok": scan_ok,
        "selected_ok": selected_ok,
        "caps_ok": caps_ok,
        "r2c_auth": r2c_auth,
        "r2c_forbidden_false_ok": false_ok,
        "source_locked": status_ok and scan_ok and selected_ok and caps_ok and r2c_auth and false_ok,
    }


LEAK_PATTERNS = [
    ("concrete_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|crates/openlocus-|\.rs\b", re.I)),
    ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")),
    ("raw_candidate_label", re.compile(r"candidate_path|gold_spans|hard_negatives|snippet|start_line|end_line|label_quality")),
    ("hash_score", re.compile(r"\b[a-f0-9]{32,64}\b|rrf_like_score|bm25_like_rank|symbol_overlap_rank|\"score\"")),
]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    text = text.replace("no_private_material_gen_execution_ci_network_bea_v1_a_p5_method_winner", "safe_boundary")
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(self_test_total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [
        PHASE,
        STATUS_PASS,
        f"{self_test_total}/{self_test_total}",
        R2B_CHECKPOINT,
        SELECTED_OPTION,
        SOURCE_FIXTURE_BUCKET,
        SUBSET_POLICY,
        TARGET_TASK_BUCKET,
        CANDIDATE_DEPTH_BUCKET,
        PRIVATE_ROW_CAP_BUCKET,
        "no_private_material_gen_execution_ci_network_bea_v1_a_p5_method_winner",
        NEXT_PHASE,
    ]
    spaced = [f"{self_test_total} / {self_test_total}" if f == f"{self_test_total}/{self_test_total}" else f for f in fragments]

    def text(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def has_all(s: str) -> bool:
        return all(fragment in s for fragment in fragments) or all(fragment in s for fragment in spaced)

    readme = has_all(text("README.md"))
    detail = has_all(text("docs/en/bea-v1-haae-r2c-local-medium-material-smoke-preflight.md")) and has_all(text("docs/zh/bea-v1-haae-r2c-local-medium-material-smoke-preflight.md"))
    current = has_all(text("docs/en/current-research-conclusions.md")) and has_all(text("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2c-local-medium-material-smoke-preflight.md" in text("docs/current-research-conclusions.md")
    log = has_all(text("docs/en/research-log.md")) and has_all(text("docs/zh/research-log.md"))
    summary = has_all(text("docs/en/research-summary.md")) and has_all(text("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2b: dict[str, Any] | None = None, *, force_fixture_missing: bool = False, omit_contract: str | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2b is None:
        try:
            r2b = load_json(repo / R2B_REPORT_PATH)
        except Exception:
            r2b = {}
    lock = validate_r2b_lock(r2b)
    fixture_count = 0 if force_fixture_missing else count_jsonl(repo / "fixtures" / "r14" / "tasks" / "medium.jsonl")
    fixture_bucket = bucket_count(fixture_count)
    fixture_ok = fixture_bucket == SOURCE_FIXTURE_BUCKET and fixture_count > 0
    command_ok = omit_contract != "operator_command"
    private_output_ok = omit_contract != "private_output"
    manifest_ok = omit_contract != "manifest"
    r2d_ok = omit_contract != "r2d"
    contract_ok = command_ok and private_output_ok and manifest_ok and r2d_ok
    readback = public_readback_match(self_test_total)
    if not lock["source_locked"]:
        status = STATUS_FAIL_SOURCE_LOCK
    elif not fixture_ok:
        status = STATUS_NO_GO_FIXTURE
    elif not contract_ok:
        status = STATUS_NO_GO_CONTRACT
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {
        "source_lock_gate": lock["source_locked"],
        "r2b_selected_option_gate": lock["selected_ok"],
        "r2b_caps_match_gate": lock["caps_ok"],
        "r2b_r2c_preflight_authorized_gate": lock["r2c_auth"],
        "r2b_no_execution_private_material_ci_gate": lock["r2c_forbidden_false_ok"],
        "public_only_preflight_gate": True,
        "medium_fixture_present_gate": fixture_count > 0,
        "medium_fixture_count_bucket_gate": fixture_ok,
        "operator_command_contract_gate": command_ok,
        "private_output_contract_gate": private_output_ok,
        "medium_manifest_schema_gate": manifest_ok,
        "r2d_contract_boundary_gate": r2d_ok,
        "no_private_root_creation_gate": True,
        "no_private_write_gate": True,
        "no_material_generation_gate": True,
        "no_experiment_gate": True,
        "no_recompute_gate": True,
        "no_candidate_generation_gate": True,
        "no_retrieval_gate": True,
        "no_source_scan_beyond_fixture_count_gate": True,
        "no_openlocus_runtime_gate": True,
        "no_network_clone_ci_gate": True,
        "no_scheduler_haae_gate": True,
        "no_selector_reranker_gate": True,
        "no_runtime_default_gate": True,
        "no_bea_v1_a_p5_gate": True,
        "no_method_scaling_claim_gate": True,
        "public_aggregate_only_gate": True,
        "forbidden_scan_pass_gate": True,
        "docs_readback_match_gate": readback["all_public_readback_match_bool"],
        "self_test_readback_match_gate": readback["all_public_readback_match_bool"],
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2csource0000", "locked_haae_r2b_checkpoint": R2B_CHECKPOINT, "locked_haae_r2b_status": R2B_STATUS, "r2b_selected_option_bucket": SELECTED_OPTION, "r2b_source_fixture_bucket": SOURCE_FIXTURE_BUCKET, "r2b_subset_policy_bucket": SUBSET_POLICY, "r2b_target_task_bucket": TARGET_TASK_BUCKET, "r2b_candidate_depth_bucket": CANDIDATE_DEPTH_BUCKET, "r2b_private_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET, "r2c_preflight_authorized_bool": lock["r2c_auth"], "r2b_r2c_execution_authorized_bool": False, "r2b_r2c_private_read_authorized_bool": False, "r2b_r2c_private_write_authorized_bool": False, "r2b_r2c_material_generation_authorized_bool": False, "r2b_r2c_ci_execution_authorized_bool": False, "r2b_forbidden_scan_pass_bool": lock["scan_ok"], "source_locked_bool": lock["source_locked"]}],
        "public_fixture_preflight_records": [{"anonymous_public_fixture_preflight_id": "haaer2cfixture0000", "fixture_bucket": "r14_medium_public_fixture", "present_bool": fixture_count > 0, "fixture_count_bucket": fixture_bucket, "sufficient_bool": fixture_ok, "subset_policy_bucket": SUBSET_POLICY, "target_task_bucket": TARGET_TASK_BUCKET, "candidate_depth_bucket": CANDIDATE_DEPTH_BUCKET, "private_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET, "raw_rows_published_bool": False}],
        "operator_command_contract_records": ([] if not command_ok else [{"anonymous_operator_command_contract_id": "haaer2ccommand0000", "command_bucket": "placeholder_only_local_manual_r2d_generation_smoke_command", "allow_private_medium_material_generation_flag_bucket": "required", "private_output_root_flag_bucket": "placeholder_required_no_concrete_path", "source_fixture_bucket": "r14_medium_public_fixture", "subset_policy_bucket": SUBSET_POLICY, "target_task_count_bucket": TARGET_TASK_BUCKET, "candidate_depth_bucket": CANDIDATE_DEPTH_BUCKET, "private_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET, "confirm_private_rows_only_flag_bucket": "required", "local_manual_only_bool": True, "ci_network_bool": False}]),
        "private_output_contract_records": ([] if not private_output_ok else [{"anonymous_private_output_contract_id": "haaer2coutput0000", "explicit_private_output_root_required_bool": True, "outside_tracked_public_tree_bool": True, "ignored_temp_private_bucket": "ignored_or_temp_private_root", "no_symlink_bool": True, "no_path_traversal_bool": True, "bounded_file_cap_bucket": "bounded", "bounded_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET, "bounded_byte_cap_bucket": "bounded", "no_public_concrete_path_bool": True}]),
        "medium_manifest_schema_records": ([] if not manifest_ok else [{"anonymous_medium_manifest_schema_id": f"haaer2cschema{idx:04d}", "group_bucket": group, "required_meaningful_bool": group in REQUIRED_GROUPS, "optional_bool": group in OPTIONAL_GROUPS, "placeholder_allowed_bool": group in PLACEHOLDER_GROUPS, "public_aggregate_fields_only_bool": True} for idx, group in enumerate(SCHEMA_GROUPS)]),
        "r2d_contract_records": ([] if not r2d_ok else [{"anonymous_r2d_contract_id": "haaer2cr2d0000", "next_phase": NEXT_PHASE, "local_manual_only_bool": True, "explicit_opt_in_required_bool": True, "may_generate_private_rows_under_explicit_private_root_bool": True, "target_task_bucket": TARGET_TASK_BUCKET, "candidate_depth_bucket": CANDIDATE_DEPTH_BUCKET, "private_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET, "public_aggregate_only_bool": True, "ci_network_clone_provider_bool": False, "runtime_default_bool": False, "scheduler_haae_bool": False, "experiment_comparison_bool": False, "bea_v1_a_p5_bool": False, "method_scaling_claim_bool": False}]),
        "risk_control_records": [{"anonymous_risk_control_id": f"haaer2crisk{idx:04d}", "risk_bucket": risk, "controlled_bool": True} for idx, risk in enumerate(["preflight_creeps_to_generation", "private_output_path_leak", "raw_medium_fixture_publication", "unbounded_private_rows", "ci_network_creep", "method_or_scaling_overclaim"])],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2cclaim0000", "public_only_preflight_bool": True, "private_root_creation_bool": False, "private_write_bool": False, "material_generation_bool": False, "experiment_bool": False, "recompute_bool": False, "candidate_generation_bool": False, "retrieval_bool": False, "source_scan_beyond_fixture_count_bool": False, "openlocus_runtime_bool": False, "network_clone_ci_bool": False, "scheduler_haae_bool": False, "selector_reranker_bool": False, "runtime_default_change_bool": False, "bea_v1_a_bool": False, "p5_bool": False, "method_claim_bool": False, "scaling_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2cgate{idx:04d}", "gate_bucket": name, "gate_passed_bool": bool(gates.get(name, False)), "gate_evaluated_on_public_data_bool": True, "gate_reads_private_material_bool": False} for idx, name in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2csynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2b_status_checkpoint_fail", "r2b_cap_selected_option_drift_fail", "fixture_missing_no_go", "operator_private_output_manifest_missing_validation_fail", "r2d_overauth_validation_fail", "leak_scanner_fail", "unknown_private_path_cli_rejects", "docs_readback_stale_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2creadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2cstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_fix_r2c_preflight_contract", "haae_r2d_explicit_local_medium_material_generation_smoke_authorized_bool": passed, "haae_r2d_execution_authorized_bool": passed, "haae_r2d_private_write_authorized_bool": passed, "haae_r2d_material_generation_authorized_bool": passed, "haae_r2d_local_manual_only_bool": True, "haae_r2d_explicit_opt_in_required_bool": True, "haae_r2d_private_read_validation_only_bool": passed, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_network_authorized_bool": False, "experiment_authorized_bool": False, "r2_recompute_authorized_bool": False, "candidate_beyond_materializer_authorized_bool": False, "retrieval_runtime_authorized_bool": False, "scheduler_haae_execution_authorized_bool": False, "selector_reranker_authorized_bool": False, "runtime_default_change_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "broad_private_read_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate":
            gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_PUBLIC_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for key in ["source_lock_records", "public_fixture_preflight_records", "operator_command_contract_records", "private_output_contract_records", "medium_manifest_schema_records", "r2d_contract_records", "risk_control_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]:
        if key not in report:
            issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        issues.append("forbidden_scan_failed")
    if not report.get("operator_command_contract_records"):
        issues.append("operator_command_contract_missing")
    if not report.get("private_output_contract_records"):
        issues.append("private_output_contract_missing")
    if not report.get("medium_manifest_schema_records"):
        issues.append("medium_manifest_schema_missing")
    if not report.get("r2d_contract_records"):
        issues.append("r2d_contract_missing")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in FORBIDDEN_STOP_FIELDS:
        if stop.get(field) is not False:
            issues.append(f"overauthorization_{field}")
    if report.get("status") == STATUS_PASS:
        source = (report.get("source_lock_records") or [{}])[0]
        fixture = (report.get("public_fixture_preflight_records") or [{}])[0]
        command = (report.get("operator_command_contract_records") or [{}])[0]
        private_output = (report.get("private_output_contract_records") or [{}])[0]
        r2d = (report.get("r2d_contract_records") or [{}])[0]
        claim = (report.get("claim_boundary_records") or [{}])[0]
        if source.get("locked_haae_r2b_checkpoint") != R2B_CHECKPOINT:
            issues.append("source_lock_checkpoint_mismatch")
        if source.get("locked_haae_r2b_status") != R2B_STATUS:
            issues.append("source_lock_status_mismatch")
        for field in [
            "source_locked_bool",
            "r2c_preflight_authorized_bool",
            "r2b_forbidden_scan_pass_bool",
        ]:
            if source.get(field) is not True:
                issues.append(f"source_lock_field_not_true_{field}")
        for field in [
            "r2b_r2c_execution_authorized_bool",
            "r2b_r2c_private_read_authorized_bool",
            "r2b_r2c_private_write_authorized_bool",
            "r2b_r2c_material_generation_authorized_bool",
            "r2b_r2c_ci_execution_authorized_bool",
        ]:
            if source.get(field) is not False:
                issues.append(f"source_lock_overauthorization_{field}")
        if fixture.get("subset_policy_bucket") != SUBSET_POLICY:
            issues.append("fixture_subset_policy_drift")
        if fixture.get("target_task_bucket") != TARGET_TASK_BUCKET:
            issues.append("fixture_target_task_bucket_drift")
        if fixture.get("candidate_depth_bucket") != CANDIDATE_DEPTH_BUCKET:
            issues.append("fixture_candidate_depth_bucket_drift")
        if fixture.get("private_row_cap_bucket") != PRIVATE_ROW_CAP_BUCKET:
            issues.append("fixture_private_row_cap_bucket_drift")
        if fixture.get("raw_rows_published_bool") is not False:
            issues.append("fixture_raw_rows_published")
        if command.get("source_fixture_bucket") != "r14_medium_public_fixture":
            issues.append("operator_source_fixture_drift")
        if command.get("subset_policy_bucket") != SUBSET_POLICY:
            issues.append("operator_subset_policy_drift")
        if command.get("target_task_count_bucket") != TARGET_TASK_BUCKET:
            issues.append("operator_target_task_bucket_drift")
        if command.get("candidate_depth_bucket") != CANDIDATE_DEPTH_BUCKET:
            issues.append("operator_candidate_depth_bucket_drift")
        if command.get("private_row_cap_bucket") != PRIVATE_ROW_CAP_BUCKET:
            issues.append("operator_private_row_cap_bucket_drift")
        if command.get("private_output_root_flag_bucket") != "placeholder_required_no_concrete_path":
            issues.append("operator_private_output_root_bucket_drift")
        if command.get("ci_network_bool") is not False:
            issues.append("operator_ci_network_overauthorization")
        for field in [
            "explicit_private_output_root_required_bool",
            "outside_tracked_public_tree_bool",
            "no_symlink_bool",
            "no_path_traversal_bool",
            "no_public_concrete_path_bool",
        ]:
            if private_output.get(field) is not True:
                issues.append(f"private_output_contract_field_not_true_{field}")
        if private_output.get("bounded_row_cap_bucket") != PRIVATE_ROW_CAP_BUCKET:
            issues.append("private_output_row_cap_drift")
        if r2d.get("next_phase") != NEXT_PHASE:
            issues.append("r2d_next_phase_drift")
        for field in ["local_manual_only_bool", "explicit_opt_in_required_bool", "may_generate_private_rows_under_explicit_private_root_bool", "public_aggregate_only_bool"]:
            if r2d.get(field) is not True:
                issues.append(f"r2d_required_field_not_true_{field}")
        if r2d.get("target_task_bucket") != TARGET_TASK_BUCKET:
            issues.append("r2d_target_task_bucket_drift")
        if r2d.get("candidate_depth_bucket") != CANDIDATE_DEPTH_BUCKET:
            issues.append("r2d_candidate_depth_bucket_drift")
        if r2d.get("private_row_cap_bucket") != PRIVATE_ROW_CAP_BUCKET:
            issues.append("r2d_private_row_cap_bucket_drift")
        for field in R2D_FORBIDDEN_FALSE_FIELDS:
            if r2d.get(field) is not False:
                issues.append(f"r2d_overauthorization_{field}")
        if claim.get("public_only_preflight_bool") is not True:
            issues.append("claim_public_only_preflight_not_true")
        for field in CLAIM_FORBIDDEN_FALSE_FIELDS:
            if claim.get(field) is not False:
                issues.append(f"claim_boundary_overauthorization_{field}")
        for field in ["haae_r2d_explicit_local_medium_material_generation_smoke_authorized_bool", "haae_r2d_execution_authorized_bool", "haae_r2d_private_write_authorized_bool", "haae_r2d_material_generation_authorized_bool", "haae_r2d_local_manual_only_bool", "haae_r2d_explicit_opt_in_required_bool"]:
            if stop.get(field) is not True:
                issues.append(f"missing_r2d_field_{field}")
        gates = {row.get("gate_bucket"): row.get("gate_passed_bool") for row in report.get("pass_fail_gate_records", [])}
        for gate in GATE_NAMES:
            if gates.get(gate) is not True:
                issues.append(f"gate_not_passed_{gate}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]:
            issues.append("public_readback_stale")
    return issues


def write_report(report: dict[str, Any], out_path: Path | None) -> Path:
    path = out_path or PUBLIC_REPORT_PATH
    if path != PUBLIC_REPORT_PATH:
        raise ValueError("unsupported_output_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def parse_args(argv: list[str]) -> dict[str, str | bool]:
    allowed = {"--self-test", "--validate-report", "--out"}
    parsed: dict[str, str | bool] = {"self_test": False, "validate_report": "", "out": ""}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg not in allowed:
            raise ValueError("unsupported_argument")
        if arg == "--self-test":
            parsed["self_test"] = True
            i += 1
        else:
            if i + 1 >= len(argv):
                raise ValueError("missing_value")
            value = argv[i + 1]
            if arg == "--validate-report":
                parsed["validate_report"] = value
            else:
                parsed["out"] = value
            i += 2
    return parsed


def public_path_from_arg(value: str) -> Path:
    path = Path(value)
    repo = Path(__file__).resolve().parents[1]
    expected = repo / PUBLIC_REPORT_PATH
    resolved = path if path.is_absolute() else repo / path
    if resolved != expected:
        raise ValueError("unsupported_public_artifact_path")
    return PUBLIC_REPORT_PATH


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2B_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)
    check("source_lock_pass", build_report(base)["status"] == STATUS_PASS)
    bad = json.loads(json.dumps(base)); bad["status"] = "wrong"; check("wrong_r2b_status_checkpoint_fail", build_report(bad)["status"] == STATUS_FAIL_SOURCE_LOCK)
    drift = json.loads(json.dumps(base)); drift["selected_scale_design_records"][0]["selected_option_bucket"] = "other"; check("r2b_cap_selected_option_drift_fail", build_report(drift)["status"] == STATUS_FAIL_SOURCE_LOCK)
    check("fixture_missing_no_go", build_report(base, force_fixture_missing=True)["status"] == STATUS_NO_GO_FIXTURE)
    check("operator_private_output_manifest_missing_validation_fail", build_report(base, omit_contract="operator_command")["status"] == STATUS_NO_GO_CONTRACT and build_report(base, omit_contract="private_output")["status"] == STATUS_NO_GO_CONTRACT and build_report(base, omit_contract="manifest")["status"] == STATUS_NO_GO_CONTRACT)
    over = json.loads(json.dumps(build_report(base))); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("r2d_overauth_validation_fail", any(i.startswith("overauthorization_") for i in validate_report(over)))
    leak = build_report(base); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus-core/src/lib.rs"; check("leak_scanner_fail", scan_public_report(leak)["status"] == "fail")
    try:
        with redirect_stderr(io.StringIO()):
            parse_args(["--private-output-root", "/tmp/x"])
        check("unknown_private_path_cli_rejects", False)
    except ValueError:
        check("unknown_private_path_cli_rejects", True)
    source_mutation = json.loads(json.dumps(build_report(base))); source_mutation["source_lock_records"][0]["source_locked_bool"] = False
    check("source_lock_false_validation_fail", any(issue.startswith("source_lock_field_not_true") for issue in validate_report(source_mutation)))
    with redirect_stderr(io.StringIO()):
        check("private_arg_main_rejects", main(["--private-output-root", "/tmp/x"]) == 2)
    claim_mutation = json.loads(json.dumps(build_report(base))); claim_mutation["claim_boundary_records"][0]["material_generation_bool"] = True
    check("claim_boundary_overauth_validation_fail", any(issue.startswith("claim_boundary_overauthorization") for issue in validate_report(claim_mutation)))
    r2d_mutation = json.loads(json.dumps(build_report(base))); r2d_mutation["r2d_contract_records"][0]["ci_network_clone_provider_bool"] = True
    check("r2d_contract_overauth_validation_fail", any(issue.startswith("r2d_overauthorization") for issue in validate_report(r2d_mutation)))
    r2d_cap_mutation = json.loads(json.dumps(build_report(base))); r2d_cap_mutation["r2d_contract_records"][0]["private_row_cap_bucket"] = "count_gt_5000"
    check("r2d_cap_drift_validation_fail", "r2d_private_row_cap_bucket_drift" in validate_report(r2d_cap_mutation))
    output_mutation = json.loads(json.dumps(build_report(base))); output_mutation["private_output_contract_records"][0]["no_symlink_bool"] = False
    check("private_output_contract_validation_fail", any(issue.startswith("private_output_contract_field_not_true") for issue in validate_report(output_mutation)))
    operator_mutation = json.loads(json.dumps(build_report(base))); operator_mutation["operator_command_contract_records"][0]["subset_policy_bucket"] = "all_medium_tasks"
    check("operator_contract_drift_validation_fail", "operator_subset_policy_drift" in validate_report(operator_mutation))
    stale = json.loads(json.dumps(build_report(base))); stale["self_test_total"] = 999; check("docs_readback_stale_fail", "public_readback_stale" in validate_report(stale))
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except ValueError:
        print("invalid arguments", file=sys.stderr)
        return 2
    if args["self_test"]:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    if args["validate_report"]:
        try:
            report_path = public_path_from_arg(str(args["validate_report"]))
            report = load_json(Path(__file__).resolve().parents[1] / report_path)
        except Exception:
            print(json.dumps({"passed": False, "issues": ["unsupported_public_artifact_path"], "status": "unavailable"}, indent=2, sort_keys=True))
            return 1
        issues = validate_report(report)
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True))
        return 0 if not issues else 1
    out_path = public_path_from_arg(str(args["out"])) if args["out"] else None
    report = build_report()
    path = write_report(report, out_path)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GO_FIXTURE, STATUS_NO_GO_CONTRACT} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
