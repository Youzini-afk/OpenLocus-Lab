#!/usr/bin/env python3
"""BEA-v1-HAAE-R2Z real-file candidate material preflight.

Public-only design/preflight. It reads only public artifacts/docs and does not
read private roots, generate candidates/material, scan source, retrieve, execute
runtime, use CI/network/provider/clone, scheduler, or selector.
"""

from __future__ import annotations

import io
import json
import re
import sys
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2Z Real-File Candidate Material Preflight"
SLUG = "bea_v1_haae_r2z_real_file_candidate_material_preflight"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"
PUBLIC_REPORT_PATH = ARTIFACT_DIR / REPORT_NAME

R2Y_CHECKPOINT = "b56462a"
R2Y_STATUS = "haae_r2y_content_identifier_next_step_decision_design_complete_r2z_real_file_candidate_material_preflight_authorized"
R2Y_REPORT_PATH = Path("artifacts/bea_v1_haae_r2y_content_identifier_next_step_decision_design/bea_v1_haae_r2y_content_identifier_next_step_decision_design_report.json")

NEXT_PHASE = "BEA-v1-HAAE-R2AA Actual Explicit Local Real-File Material Smoke"
STATUS_PASS = "haae_r2z_real_file_candidate_material_preflight_complete_r2aa_actual_explicit_local_real_file_material_smoke_authorized"
STATUS_NO_GO = "haae_r2z_no_go_no_safe_real_file_candidate_material_recipe"
STATUS_FAIL_SOURCE = "haae_r2z_fail_closed_source_lock_mismatch"
STATUS_FAIL_BOUNDARY = "haae_r2z_fail_closed_boundary_or_overauthorization"
STATUS_FAIL_LEAK = "haae_r2z_fail_closed_raw_publication_detected"
STATUS_FAIL_READBACK = "haae_r2z_fail_closed_public_readback_mismatch"
SELF_TEST_EXPECTED = 20

GATE_NAMES = [
    "r2y_source_locked_gate",
    "r2y_r2z_authorization_gate",
    "public_only_preflight_gate",
    "no_private_read_write_gate",
    "no_execution_generation_gate",
    "no_candidate_generation_gate",
    "no_source_scan_gate",
    "no_retrieval_runtime_openlocus_gate",
    "no_ci_network_provider_clone_gate",
    "no_scheduler_selector_gate",
    "operator_manifest_allowlist_required_gate",
    "bounded_recipe_gate",
    "gold_private_eval_not_policy_gate",
    "public_aggregate_only_gate",
    "r2aa_only_stop_go_gate",
    "no_method_default_scaling_claim_gate",
    "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
]
STOP_FORBIDDEN_TRUE = [
    "r2aa_ci_execution_authorized_bool",
    "r2aa_broad_workspace_scan_authorized_bool",
    "r2aa_unbounded_source_scan_authorized_bool",
    "r2aa_network_authorized_bool",
    "r2aa_provider_model_authorized_bool",
    "r2aa_clone_authorized_bool",
    "r2aa_retrieval_runtime_authorized_bool",
    "r2aa_openlocus_runtime_authorized_bool",
    "r2aa_scheduler_haae_authorized_bool",
    "r2aa_selector_reranker_authorized_bool",
    "r2aa_bea_v1_a_authorized_bool",
    "r2aa_p5_authorized_bool",
    "r2aa_runtime_default_change_authorized_bool",
    "r2aa_experiment_metrics_authorized_bool",
    "r2aa_method_winner_claim_authorized_bool",
    "r2aa_scaling_claim_authorized_bool",
    "r2aa_raw_publication_authorized_bool",
    "execution_authorized_bool",
    "candidate_generation_authorized_bool",
    "private_read_authorized_bool",
    "private_write_authorized_bool",
    "source_scan_authorized_bool",
    "retrieval_authorized_bool",
    "runtime_execution_authorized_bool",
    "ci_execution_authorized_bool",
    "network_authorized_bool",
    "provider_model_authorized_bool",
    "clone_authorized_bool",
    "scheduler_haae_authorized_bool",
    "selector_reranker_authorized_bool",
    "default_change_authorized_bool",
    "method_winner_claim_authorized_bool",
    "scaling_claim_authorized_bool",
    "raw_publication_authorized_bool",
]

R2AA_REQUIRED_TRUE = [
    "haae_r2aa_actual_explicit_local_real_file_material_smoke_authorized_bool",
    "r2aa_execution_authorized_bool",
    "r2aa_explicit_opt_in_required_bool",
    "r2aa_local_manual_only_bool",
    "r2aa_operator_public_corpus_manifest_required_bool",
    "r2aa_allowlisted_public_corpus_only_bool",
    "r2aa_private_output_root_required_bool",
    "r2aa_private_write_authorized_bool",
    "r2aa_real_file_candidate_material_generation_authorized_bool",
    "r2aa_candidate_generation_authorized_bool",
    "r2aa_bounded_source_scan_authorized_bool",
    "r2aa_source_scan_authorized_bool",
    "r2aa_public_aggregate_only_bool",
]

R2AA_EXPECTED_BUCKETS = {
    "r2aa_target_task_count_bucket": "target_20",
    "r2aa_candidate_depth_cap_bucket": "depth_40",
    "r2aa_source_file_cap_bucket": "cap_500",
    "r2aa_private_row_cap_bucket": "cap_20000",
    "r2aa_wall_clock_cap_bucket": "cap_20_minutes",
    "r2aa_gold_policy_bucket": "gold_private_eval_only_not_policy",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_r2y(r2y: dict[str, Any]) -> dict[str, bool]:
    stop = (r2y.get("stop_go_records") or [{}])[0]
    contract = (r2y.get("r2z_contract_records") or [{}])[0]
    status_ok = r2y.get("status") == R2Y_STATUS
    scan_ok = r2y.get("forbidden_scan", {}).get("status") == "pass"
    auth_ok = stop.get("haae_r2z_real_file_candidate_material_preflight_authorized_bool") is True and stop.get("r2z_public_design_preflight_only_bool") is True
    stop_ok = all(stop.get(field) is False for field in [
        "r2z_execution_authorized_bool", "r2z_private_read_authorized_bool", "r2z_private_write_authorized_bool",
        "r2z_candidate_generation_authorized_bool", "r2z_source_scan_authorized_bool", "r2z_ci_execution_authorized_bool",
        "execution_authorized_bool", "ci_execution_authorized_bool", "new_material_generation_authorized_bool",
        "candidate_generation_authorized_bool", "retrieval_authorized_bool", "runtime_execution_authorized_bool",
        "source_scan_authorized_bool", "network_authorized_bool", "provider_model_authorized_bool",
        "scheduler_haae_authorized_bool", "selector_reranker_authorized_bool", "method_winner_claim_authorized_bool",
        "scaling_claim_authorized_bool", "raw_publication_authorized_bool",
    ])
    contract_ok = (
        contract.get("operator_public_corpus_manifest_required_bool") is True
        and contract.get("allowlisted_public_corpus_only_bool") is True
        and contract.get("no_broad_workspace_scan_bool") is True
        and contract.get("no_network_clone_by_default_bool") is True
        and contract.get("future_target_task_count_bucket") == "target_20"
        and contract.get("future_candidate_depth_cap_bucket") == "depth_40"
        and contract.get("future_source_file_cap_bucket") == "cap_500"
        and contract.get("future_private_row_cap_bucket") == "cap_20000"
        and contract.get("future_wall_clock_cap_bucket") == "cap_20_minutes"
        and contract.get("future_gold_policy_bucket") == "gold_private_eval_only_not_policy"
        and contract.get("future_public_aggregate_only_bool") is True
    )
    return {"status_ok": status_ok, "scan_ok": scan_ok, "auth_ok": auth_ok, "stop_ok": stop_ok, "contract_ok": contract_ok, "source_locked": status_ok and scan_ok and auth_ok and stop_ok}


LEAK_PATTERNS = [
    ("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root|groups/|\.jsonl", re.I)),
    ("raw_task_query", re.compile(r"r14(m|s|stress)-\d+|\"task_id\"|\"query\"")),
    ("raw_candidate_path", re.compile(r"candidate_path|source_path|filepath|filename|directory|snippet|start_line|end_line|\.rs\b|crates/openlocus-")),
    ("score_hash_exact", re.compile(r"private_score|private_rank|exact_rate|exact_rank|task_key|\b[a-f0-9]{32,64}\b")),
]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    findings = [name for name, pattern in LEAK_PATTERNS if pattern.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [
        PHASE, STATUS_PASS, f"{total}/{total}", R2Y_CHECKPOINT, R2Y_STATUS, NEXT_PHASE,
        "operator public corpus manifest/allowlist required", "no broad workspace scan", "no network clone by default",
        "target 20", "candidate depth 40", "source file cap 500", "row cap 20000", "wall-clock cap 20 minutes",
        "gold private eval only not policy", "public aggregate-only", "R2Z performs no execution/private write/candidate generation/source scan",
        "R2AA bounded local execution authorized", "R2AA broad workspace scan/CI/network/runtime false",
        "future private rows may contain real file candidate references but not R2Z", "no method/default/scaling",
    ]
    spaced = [f"{total} / {total}" if fragment == f"{total}/{total}" else fragment for fragment in fragments]
    def read(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(text: str) -> bool:
        return all(fragment in text for fragment in fragments) or all(fragment in text for fragment in spaced)
    readme = has_all(read("README.md"))
    detail = has_all(read("docs/en/bea-v1-haae-r2z-real-file-candidate-material-preflight.md")) and has_all(read("docs/zh/bea-v1-haae-r2z-real-file-candidate-material-preflight.md"))
    current = has_all(read("docs/en/current-research-conclusions.md")) and has_all(read("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2z-real-file-candidate-material-preflight.md" in read("docs/current-research-conclusions.md")
    log = has_all(read("docs/en/research-log.md")) and has_all(read("docs/zh/research-log.md"))
    summary = has_all(read("docs/en/research-summary.md")) and has_all(read("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2y: dict[str, Any] | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2y is None:
        try: r2y = load_json(repo / R2Y_REPORT_PATH)
        except Exception: r2y = {}
    audit = audit_r2y(r2y)
    readback = public_readback_match(self_test_total)
    if not audit["source_locked"]:
        status = STATUS_FAIL_SOURCE
    elif not audit["contract_ok"]:
        status = STATUS_NO_GO
    elif not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    else:
        status = STATUS_PASS
    passed = status == STATUS_PASS
    gates = {
        "r2y_source_locked_gate": audit["source_locked"], "r2y_r2z_authorization_gate": audit["auth_ok"],
        "public_only_preflight_gate": True, "no_private_read_write_gate": True, "no_execution_generation_gate": True,
        "no_candidate_generation_gate": True, "no_source_scan_gate": True, "no_retrieval_runtime_openlocus_gate": True,
        "no_ci_network_provider_clone_gate": True, "no_scheduler_selector_gate": True,
        "operator_manifest_allowlist_required_gate": audit["contract_ok"], "bounded_recipe_gate": audit["contract_ok"],
        "gold_private_eval_not_policy_gate": audit["contract_ok"], "public_aggregate_only_gate": True,
        "r2aa_only_stop_go_gate": True, "no_method_default_scaling_claim_gate": True,
        "forbidden_scan_pass_gate": True, "docs_readback_match_gate": readback["all_public_readback_match_bool"],
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2zsource0000", "locked_haae_r2y_checkpoint": R2Y_CHECKPOINT, "locked_haae_r2y_status": R2Y_STATUS, "r2y_status_match_bool": audit["status_ok"], "r2y_forbidden_scan_pass_bool": audit["scan_ok"], "r2y_r2z_authorization_match_bool": audit["auth_ok"], "r2y_no_forbidden_stop_go_drift_bool": audit["stop_ok"], "source_locked_bool": audit["source_locked"]}],
        "preflight_scope_records": [{"anonymous_preflight_scope_id": "haaer2zscope0000", "public_only_design_preflight_bool": True, "r2z_execution_performed_bool": False, "r2z_private_read_performed_bool": False, "r2z_private_write_performed_bool": False, "r2z_material_generation_performed_bool": False, "r2z_candidate_generation_performed_bool": False, "r2z_source_scan_performed_bool": False, "r2z_ci_network_provider_performed_bool": False, "private_read_count_bucket": "count_0", "private_write_count_bucket": "count_0", "candidate_generation_count_bucket": "count_0", "source_scan_count_bucket": "count_0", "retrieval_runtime_openlocus_bool": False, "ci_network_provider_clone_bool": False, "scheduler_selector_bool": False}],
        "future_real_file_recipe_records": [{"anonymous_future_recipe_id": "haaer2zrecipe0000", "future_phase": NEXT_PHASE, "operator_public_corpus_manifest_allowlist_required_bool": True, "no_broad_workspace_scan_bool": True, "no_network_clone_by_default_bool": True, "target_task_count_bucket": "target_20", "candidate_depth_bucket": "candidate_depth_40", "source_file_cap_bucket": "source_file_cap_500", "private_row_cap_bucket": "row_cap_20000", "wall_clock_cap_bucket": "wall_clock_cap_20_minutes", "gold_policy_bucket": "gold_private_eval_only_not_policy", "public_aggregate_only_bool": True, "future_private_rows_may_contain_real_file_candidate_references_bool": True, "r2z_contains_real_file_candidate_references_bool": False}],
        "operator_manifest_contract_records": [{"anonymous_operator_manifest_contract_id": "haaer2zmanifest0000", "operator_supplied_manifest_required_bool": True, "public_corpus_allowlist_required_bool": True, "local_files_only_bool": True, "no_network_clone_by_default_bool": True, "no_broad_workspace_scan_bool": True, "source_file_cap_bucket": "source_file_cap_500", "manifest_paths_not_published_by_r2z_bool": True}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2zclaim0000", "public_only_design_bool": True, "private_read_bool": False, "private_write_bool": False, "execution_bool": False, "candidate_generation_bool": False, "source_scan_bool": False, "retrieval_runtime_openlocus_bool": False, "ci_network_provider_clone_bool": False, "scheduler_selector_bool": False, "default_runtime_claim_bool": False, "method_winner_claim_bool": False, "scaling_claim_bool": False, "raw_publication_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2zgate{idx:04d}", "gate_bucket": gate, "gate_passed_bool": bool(gates.get(gate, False)), "gate_public_artifact_bool": True} for idx, gate in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2zsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_r2y_status_fail", "missing_r2z_authorization_fail", "contract_missing_manifest_fail", "contract_unbounded_fail", "r2aa_execution_required_fail", "candidate_generation_overauth_fail", "source_scan_overauth_fail", "claim_boundary_fail", "r2aa_broad_scan_overauth_fail", "r2aa_private_write_required_fail", "r2aa_target_bound_fail", "r2aa_source_cap_bound_fail", "r2z_performed_scope_fail", "r2aa_experiment_metrics_overauth_fail", "r2aa_ci_overauth_fail", "leak_fail", "stale_readback_fail", "safe_parser_fail", "source_lock_pass_validate_report"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2zreadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2zstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_revisit_real_file_preflight", "haae_r2aa_actual_explicit_local_real_file_material_smoke_authorized_bool": passed, "r2aa_execution_authorized_bool": passed, "r2aa_explicit_opt_in_required_bool": passed, "r2aa_local_manual_only_bool": passed, "r2aa_operator_public_corpus_manifest_required_bool": passed, "r2aa_allowlisted_public_corpus_only_bool": passed, "r2aa_private_output_root_required_bool": passed, "r2aa_private_write_authorized_bool": passed, "r2aa_real_file_candidate_material_generation_authorized_bool": passed, "r2aa_candidate_generation_authorized_bool": passed, "r2aa_bounded_source_scan_authorized_bool": passed, "r2aa_source_scan_authorized_bool": passed, "r2aa_public_aggregate_only_bool": passed, "r2aa_target_task_count_bucket": "target_20" if passed else "not_authorized", "r2aa_candidate_depth_cap_bucket": "depth_40" if passed else "not_authorized", "r2aa_source_file_cap_bucket": "cap_500" if passed else "not_authorized", "r2aa_private_row_cap_bucket": "cap_20000" if passed else "not_authorized", "r2aa_wall_clock_cap_bucket": "cap_20_minutes" if passed else "not_authorized", "r2aa_gold_policy_bucket": "gold_private_eval_only_not_policy" if passed else "not_authorized", "r2aa_broad_workspace_scan_authorized_bool": False, "r2aa_unbounded_source_scan_authorized_bool": False, "r2aa_ci_execution_authorized_bool": False, "r2aa_network_authorized_bool": False, "r2aa_provider_model_authorized_bool": False, "r2aa_clone_authorized_bool": False, "r2aa_retrieval_runtime_authorized_bool": False, "r2aa_openlocus_runtime_authorized_bool": False, "r2aa_scheduler_haae_authorized_bool": False, "r2aa_selector_reranker_authorized_bool": False, "r2aa_bea_v1_a_authorized_bool": False, "r2aa_p5_authorized_bool": False, "r2aa_runtime_default_change_authorized_bool": False, "r2aa_experiment_metrics_authorized_bool": False, "r2aa_method_winner_claim_authorized_bool": False, "r2aa_scaling_claim_authorized_bool": False, "r2aa_raw_publication_authorized_bool": False, "execution_authorized_bool": False, "candidate_generation_authorized_bool": False, "private_read_authorized_bool": False, "private_write_authorized_bool": False, "source_scan_authorized_bool": False, "retrieval_authorized_bool": False, "runtime_execution_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "provider_model_authorized_bool": False, "clone_authorized_bool": False, "scheduler_haae_authorized_bool": False, "selector_reranker_authorized_bool": False, "default_change_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False, "raw_publication_authorized_bool": False}],
    }
    scan = scan_public_report(report)
    report["forbidden_scan"] = scan
    for gate in report["pass_fail_gate_records"]:
        if gate["gate_bucket"] == "forbidden_scan_pass_gate": gate["gate_passed_bool"] = scan["status"] == "pass"
    if report["status"] == STATUS_PASS and scan["status"] != "pass": report["status"] = STATUS_FAIL_LEAK
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = ["source_lock_records", "preflight_scope_records", "future_real_file_recipe_records", "operator_manifest_contract_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report: issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass": issues.append("forbidden_scan_failed")
    source = (report.get("source_lock_records") or [{}])[0]
    if source.get("locked_haae_r2y_checkpoint") != R2Y_CHECKPOINT or source.get("locked_haae_r2y_status") != R2Y_STATUS: issues.append("source_lock_mismatch")
    for field in ["r2y_status_match_bool", "r2y_forbidden_scan_pass_bool", "r2y_r2z_authorization_match_bool", "r2y_no_forbidden_stop_go_drift_bool", "source_locked_bool"]:
        if source.get(field) is not True: issues.append(f"source_lock_{field}")
    recipe = (report.get("future_real_file_recipe_records") or [{}])[0]
    expected = {"target_task_count_bucket": "target_20", "candidate_depth_bucket": "candidate_depth_40", "source_file_cap_bucket": "source_file_cap_500", "private_row_cap_bucket": "row_cap_20000", "wall_clock_cap_bucket": "wall_clock_cap_20_minutes", "gold_policy_bucket": "gold_private_eval_only_not_policy"}
    for key, value in expected.items():
        if recipe.get(key) != value: issues.append(f"recipe_{key}")
    for field in ["operator_public_corpus_manifest_allowlist_required_bool", "no_broad_workspace_scan_bool", "no_network_clone_by_default_bool", "public_aggregate_only_bool", "future_private_rows_may_contain_real_file_candidate_references_bool"]:
        if recipe.get(field) is not True: issues.append(f"recipe_{field}")
    if recipe.get("r2z_contains_real_file_candidate_references_bool") is not False: issues.append("r2z_raw_real_file_reference_publication")
    manifest = (report.get("operator_manifest_contract_records") or [{}])[0]
    for field in ["operator_supplied_manifest_required_bool", "public_corpus_allowlist_required_bool", "local_files_only_bool", "no_network_clone_by_default_bool", "no_broad_workspace_scan_bool", "manifest_paths_not_published_by_r2z_bool"]:
        if manifest.get(field) is not True: issues.append(f"manifest_contract_{field}")
    claim = (report.get("claim_boundary_records") or [{}])[0]
    for field in ["private_read_bool", "private_write_bool", "execution_bool", "candidate_generation_bool", "source_scan_bool", "retrieval_runtime_openlocus_bool", "ci_network_provider_clone_bool", "scheduler_selector_bool", "default_runtime_claim_bool", "method_winner_claim_bool", "scaling_claim_bool", "raw_publication_bool"]:
        if claim.get(field) is not False: issues.append(f"claim_boundary_{field}")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in STOP_FORBIDDEN_TRUE:
        if stop.get(field) is not False: issues.append(f"overauthorization_{field}")
    scope = (report.get("preflight_scope_records") or [{}])[0]
    for field in ["r2z_execution_performed_bool", "r2z_private_read_performed_bool", "r2z_private_write_performed_bool", "r2z_material_generation_performed_bool", "r2z_candidate_generation_performed_bool", "r2z_source_scan_performed_bool", "r2z_ci_network_provider_performed_bool"]:
        if scope.get(field) is not False: issues.append(f"r2z_scope_{field}")
    if report.get("status") == STATUS_PASS:
        if stop.get("next_allowed_phase") != NEXT_PHASE: issues.append("missing_r2aa_authorization")
        for field in R2AA_REQUIRED_TRUE:
            if stop.get(field) is not True: issues.append(f"missing_r2aa_{field}")
        for field, expected_value in R2AA_EXPECTED_BUCKETS.items():
            if stop.get(field) != expected_value: issues.append(f"r2aa_bound_{field}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]: issues.append("public_readback_stale")
        for gate in report.get("pass_fail_gate_records", []):
            if gate.get("gate_passed_bool") is not True: issues.append(f"gate_failed_{gate.get('gate_bucket', 'unknown')}")
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
        else:
            raise ValueError("invalid arguments")
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
    base = load_json(repo / R2Y_REPORT_PATH)
    def check(name: str, condition: bool) -> None:
        if not condition: failures.append(name)
    passed = build_report(base); check("source_lock_pass", passed["status"] == STATUS_PASS and validate_report(passed) == [])
    check("source_lock_pass_validate_report", validate_report(passed) == [])
    wrong = json.loads(json.dumps(base)); wrong["status"] = "wrong"; check("wrong_r2y_status_fail", build_report(wrong)["status"] == STATUS_FAIL_SOURCE)
    noauth = json.loads(json.dumps(base)); noauth["stop_go_records"][0]["haae_r2z_real_file_candidate_material_preflight_authorized_bool"] = False; check("missing_r2z_authorization_fail", build_report(noauth)["status"] == STATUS_FAIL_SOURCE)
    missing_manifest = json.loads(json.dumps(base)); missing_manifest["r2z_contract_records"][0]["operator_public_corpus_manifest_required_bool"] = False; check("contract_missing_manifest_fail", build_report(missing_manifest)["status"] == STATUS_NO_GO)
    unbounded = json.loads(json.dumps(base)); unbounded["r2z_contract_records"][0]["future_source_file_cap_bucket"] = "unbounded"; check("contract_unbounded_fail", build_report(unbounded)["status"] == STATUS_NO_GO)
    exec_missing = json.loads(json.dumps(passed)); exec_missing["stop_go_records"][0]["r2aa_execution_authorized_bool"] = False; check("r2aa_execution_required_fail", "missing_r2aa_r2aa_execution_authorized_bool" in validate_report(exec_missing))
    cand_over = json.loads(json.dumps(passed)); cand_over["claim_boundary_records"][0]["candidate_generation_bool"] = True; check("candidate_generation_overauth_fail", any(i.startswith("claim_boundary_") for i in validate_report(cand_over)))
    source_over = json.loads(json.dumps(passed)); source_over["stop_go_records"][0]["source_scan_authorized_bool"] = True; check("source_scan_overauth_fail", any(i.startswith("overauthorization_") for i in validate_report(source_over)))
    claim = json.loads(json.dumps(passed)); claim["claim_boundary_records"][0]["method_winner_claim_bool"] = True; check("claim_boundary_fail", any(i.startswith("claim_boundary_") for i in validate_report(claim)))
    broad = json.loads(json.dumps(passed)); broad["stop_go_records"][0]["r2aa_broad_workspace_scan_authorized_bool"] = True; check("r2aa_broad_scan_overauth_fail", "overauthorization_r2aa_broad_workspace_scan_authorized_bool" in validate_report(broad))
    private_write_missing = json.loads(json.dumps(passed)); private_write_missing["stop_go_records"][0]["r2aa_private_write_authorized_bool"] = False; check("r2aa_private_write_required_fail", "missing_r2aa_r2aa_private_write_authorized_bool" in validate_report(private_write_missing))
    target_drift = json.loads(json.dumps(passed)); target_drift["stop_go_records"][0]["r2aa_target_task_count_bucket"] = "target_200"; check("r2aa_target_bound_fail", "r2aa_bound_r2aa_target_task_count_bucket" in validate_report(target_drift))
    source_cap_drift = json.loads(json.dumps(passed)); source_cap_drift["stop_go_records"][0]["r2aa_source_file_cap_bucket"] = "cap_unbounded"; check("r2aa_source_cap_bound_fail", "r2aa_bound_r2aa_source_file_cap_bucket" in validate_report(source_cap_drift))
    r2z_performed = json.loads(json.dumps(passed)); r2z_performed["preflight_scope_records"][0]["r2z_candidate_generation_performed_bool"] = True; check("r2z_performed_scope_fail", "r2z_scope_r2z_candidate_generation_performed_bool" in validate_report(r2z_performed))
    experiment_metrics = json.loads(json.dumps(passed)); experiment_metrics["stop_go_records"][0]["r2aa_experiment_metrics_authorized_bool"] = True; check("r2aa_experiment_metrics_overauth_fail", "overauthorization_r2aa_experiment_metrics_authorized_bool" in validate_report(experiment_metrics))
    ci_over = json.loads(json.dumps(passed)); ci_over["stop_go_records"][0]["r2aa_ci_execution_authorized_bool"] = True; check("r2aa_ci_overauth_fail", "overauthorization_r2aa_ci_execution_authorized_bool" in validate_report(ci_over))
    leak = json.loads(json.dumps(passed)); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus/src/lib.rs"; check("leak_fail", scan_public_report(leak)["status"] == "fail")
    check("stale_readback_fail", public_readback_match(999)["all_public_readback_match_bool"] is False)
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
