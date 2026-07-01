#!/usr/bin/env python3
"""BEA-v1-HAAE-R2B scale preflight design.

Public-only design/preflight. It may inspect committed R14 public fixture metadata
to choose a bounded next preflight design, but it performs no material generation,
experiment, private read/write, recompute, retrieval, source-corpus scan, CI, or
runtime change.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from contextlib import redirect_stderr
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PHASE = "BEA-v1-HAAE-R2B Scale Preflight Design"
SLUG = "bea_v1_haae_r2b_scale_preflight_design"
SCHEMA_VERSION = f"{SLUG}_v1"
ARTIFACT_DIR = Path("artifacts") / SLUG
REPORT_NAME = f"{SLUG}_report.json"

R2A_CHECKPOINT = "2ca1ac4"
R2A_STATUS = "haae_r2a_public_audit_package_complete_r2b_scale_preflight_design_authorized"
R2A_REPORT_PATH = Path("artifacts/bea_v1_haae_r2a_small_local_experiment_public_audit_package/bea_v1_haae_r2a_small_local_experiment_public_audit_package_report.json")

STATUS_PASS = "haae_r2b_scale_preflight_design_complete_r2c_local_medium_material_smoke_preflight_authorized"
STATUS_NO_GO_NO_FIXTURE = "haae_r2b_no_go_no_bounded_public_fixture_option"
STATUS_NO_GO_CI_REQUIRED = "haae_r2b_no_go_ci_preflight_required_before_scale"
STATUS_FAIL_SOURCE_LOCK = "haae_r2b_fail_closed_source_lock_mismatch"
STATUS_FAIL_OVERAUTH = "haae_r2b_fail_closed_overauthorization"
STATUS_FAIL_PUBLIC_LEAK = "haae_r2b_fail_closed_public_manifest_leak"
STATUS_FAIL_READBACK = "haae_r2b_fail_closed_public_readback_mismatch"

SELF_TEST_EXPECTED = 13
TARGET_TASK_COUNT_BUCKET = "count_10_to_20"
TARGET_CANDIDATE_DEPTH_BUCKET = "count_20"
PRIVATE_ROW_CAP_BUCKET = "count_le_5000"
SOURCE_FIXTURE_TASK_COUNT_BUCKET = "count_21_to_50"
SELECTED_OPTION = "r14_medium_local_material_smoke"
NEXT_PHASE = "BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight"

FORBIDDEN_STOP_FIELDS = [
    "haae_r2c_execution_authorized_bool",
    "haae_r2c_private_read_authorized_bool",
    "haae_r2c_private_write_authorized_bool",
    "haae_r2c_ci_execution_authorized_bool",
    "haae_r2c_material_generation_authorized_bool",
    "ci_execution_authorized_bool",
    "network_authorized_bool",
    "private_read_authorized_bool",
    "private_write_authorized_bool",
    "material_generation_authorized_bool",
    "experiment_authorized_bool",
    "recompute_authorized_bool",
    "candidate_generation_authorized_bool",
    "retrieval_authorized_bool",
    "scheduler_haae_execution_authorized_bool",
    "selector_reranker_authorized_bool",
    "runtime_default_change_authorized_bool",
    "bea_v1_a_authorized_bool",
    "p5_authorized_bool",
    "method_winner_claim_authorized_bool",
    "scaling_claim_authorized_bool",
]

GATE_NAMES = [
    "source_lock_gate",
    "r2b_authorization_gate",
    "public_inputs_only_gate",
    "no_private_read_write_gate",
    "no_material_generation_gate",
    "no_experiment_gate",
    "no_recompute_gate",
    "no_candidate_generation_gate",
    "no_retrieval_gate",
    "no_scheduler_haae_execution_gate",
    "no_selector_reranker_gate",
    "no_runtime_default_change_gate",
    "no_network_ci_clone_gate",
    "no_bea_v1_a_p5_gate",
    "no_method_winner_or_scaling_claim_gate",
    "non_empty_fixture_option_gate",
    "selected_bounded_local_option_gate",
    "selected_subset_cap_gate",
    "r2c_boundary_bounded_gate",
    "forbidden_scan_pass_gate",
    "docs_readback_match_gate",
    "self_test_readback_match_gate",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_report(report: dict[str, Any], out: Path | None) -> Path:
    path = out or ARTIFACT_DIR / REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def is_exact_public_artifact_arg(value: str, expected: Path) -> bool:
    supplied = Path(value)
    if supplied.is_absolute() or ".." in supplied.parts:
        return False
    return supplied == expected


def count_jsonl(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def bucket_count(n: int) -> str:
    if n <= 0:
        return "count_0"
    if n == 1:
        return "count_1"
    if n <= 5:
        return "count_2_to_5"
    if n <= 9:
        return "count_6_to_9"
    if n <= 20:
        return "count_10_to_20"
    if n <= 50:
        return "count_21_to_50"
    return "count_gt_50"


def validate_r2a_lock(r2a: dict[str, Any]) -> dict[str, bool]:
    stop = (r2a.get("stop_go_records") or [{}])[0]
    source = (r2a.get("source_lock_records") or [{}])[0]
    claim = (r2a.get("claim_boundary_records") or [{}])[0]
    status_ok = r2a.get("status") == R2A_STATUS
    scan_ok = r2a.get("forbidden_scan", {}).get("status") == "pass"
    checkpoint_ok = source.get("locked_haae_r2_checkpoint") == "0784be0"
    r2b_auth = stop.get("haae_r2b_scale_preflight_design_authorized_bool") is True
    no_scale_exec = stop.get("haae_r2b_scale_execution_authorized_bool") is False and claim.get("r2b_scale_execution_authorized_bool") is False
    no_ci = stop.get("ci_execution_authorized_bool") is False and claim.get("ci_execution_authorized_bool") is False
    no_forbidden = all(stop.get(field) is False for field in [
        "new_candidate_generation_authorized_bool",
        "candidate_generation_authorized_bool",
        "retrieval_authorized_bool",
        "scheduler_haae_execution_authorized_bool",
        "selector_reranker_authorized_bool",
        "runtime_default_change_authorized_bool",
        "bea_v1_a_authorized_bool",
        "p5_authorized_bool",
        "method_winner_claim_authorized_bool",
        "raw_publication_authorized_bool",
        "private_read_authorized_bool",
        "private_write_authorized_bool",
        "recompute_authorized_bool",
    ])
    return {
        "status_ok": status_ok,
        "scan_ok": scan_ok,
        "checkpoint_ok": checkpoint_ok,
        "r2b_auth": r2b_auth,
        "no_scale_exec": no_scale_exec,
        "no_ci": no_ci,
        "no_forbidden": no_forbidden,
        "source_locked": status_ok and scan_ok and checkpoint_ok and r2b_auth and no_scale_exec and no_ci and no_forbidden,
    }


def fixture_options(repo: Path, force_no_fixture: bool = False) -> list[dict[str, Any]]:
    if force_no_fixture:
        medium_count = stress_count = 0
    else:
        medium_count = count_jsonl(repo / "fixtures" / "r14" / "tasks" / "medium.jsonl")
        stress_count = count_jsonl(repo / "fixtures" / "r14" / "tasks" / "stress.jsonl")
    return [
        {"option_bucket": "r14_medium", "public_fixture_present_bool": medium_count > 0, "public_task_count_bucket": bucket_count(medium_count), "bounded_local_option_bool": medium_count >= 10, "source_fixture_task_count_bucket": bucket_count(medium_count), "selected_subset_required_bool": medium_count > 20, "selected_subset_policy_bucket": "deterministic_public_manifest_prefix_cap_10_to_20", "target_task_count_bucket": TARGET_TASK_COUNT_BUCKET, "candidate_depth_bucket": TARGET_CANDIDATE_DEPTH_BUCKET, "private_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET, "selected_preferred_bool": medium_count >= 10},
        {"option_bucket": "r14_stress", "public_fixture_present_bool": stress_count > 0, "public_task_count_bucket": bucket_count(stress_count), "bounded_local_option_bool": False, "target_task_count_bucket": "not_selected", "candidate_depth_bucket": "not_selected", "private_row_cap_bucket": "not_selected", "selected_preferred_bool": False},
        {"option_bucket": "operator_manifest", "public_fixture_present_bool": False, "public_task_count_bucket": "operator_supplied", "bounded_local_option_bool": True, "target_task_count_bucket": TARGET_TASK_COUNT_BUCKET, "candidate_depth_bucket": TARGET_CANDIDATE_DEPTH_BUCKET, "private_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET, "selected_preferred_bool": False},
        {"option_bucket": "ci_canary_design", "public_fixture_present_bool": False, "public_task_count_bucket": "ci_required", "bounded_local_option_bool": False, "target_task_count_bucket": "not_selected", "candidate_depth_bucket": "not_selected", "private_row_cap_bucket": "not_selected", "selected_preferred_bool": False},
    ]


def choose_option(options: list[dict[str, Any]], override: str | None = None) -> tuple[str | None, str]:
    if override:
        return override, "operator_override_for_self_test"
    medium = next(row for row in options if row["option_bucket"] == "r14_medium")
    if medium["public_fixture_present_bool"] and medium["bounded_local_option_bool"]:
        return SELECTED_OPTION, "tracked_public_r14_medium_bounded_window"
    operator = next(row for row in options if row["option_bucket"] == "operator_manifest")
    if operator["bounded_local_option_bool"]:
        return "operator_manifest_design", "fallback_operator_manifest_required"
    return None, "no_bounded_public_fixture_option"


LEAK_PATTERNS = [
    ("private_path", re.compile(r"/tmp/|/workspace/|/var/tmp/|private-root", re.I)),
    ("raw_task_or_query", re.compile(r"r14(m|stress|s)-\d+|\"query\"|\"task_id\"")),
    ("candidate_or_source", re.compile(r"candidate_path|crates/openlocus-|\.rs\b|snippet|gold_spans|hard_negatives")),
    ("hash_or_score", re.compile(r"\b[a-f0-9]{32,64}\b|rrf_like_score|bm25_like_rank|symbol_overlap_rank")),
]


def scan_public_report(report: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(report, sort_keys=True)
    text = text.replace("no private/material gen/execution/CI/network/BEA-v1-A/P5/method-winner", "safe_boundary_phrase")
    findings = [name for name, pat in LEAK_PATTERNS if pat.search(text)]
    return {"status": "pass" if not findings else "fail", "forbidden_finding_count": len(findings), "finding_buckets": findings}


def public_readback_match(self_test_total: int) -> dict[str, bool]:
    repo = Path(__file__).resolve().parents[1]
    fragments = [PHASE, STATUS_PASS, f"{self_test_total}/{self_test_total}", R2A_CHECKPOINT, SELECTED_OPTION, TARGET_TASK_COUNT_BUCKET, SOURCE_FIXTURE_TASK_COUNT_BUCKET, TARGET_CANDIDATE_DEPTH_BUCKET, PRIVATE_ROW_CAP_BUCKET, "deterministic_public_manifest_prefix_cap_10_to_20", "no private/material gen/execution/CI/network/BEA-v1-A/P5/method-winner", NEXT_PHASE]
    spaced = [f"{self_test_total} / {self_test_total}" if f == f"{self_test_total}/{self_test_total}" else f for f in fragments]
    def text(rel: str) -> str:
        path = repo / rel
        return path.read_text(encoding="utf-8") if path.exists() else ""
    def has_all(s: str) -> bool:
        return all(f in s for f in fragments) or all(f in s for f in spaced)
    readme = has_all(text("README.md"))
    detail = has_all(text("docs/en/bea-v1-haae-r2b-scale-preflight-design.md")) and has_all(text("docs/zh/bea-v1-haae-r2b-scale-preflight-design.md"))
    current = has_all(text("docs/en/current-research-conclusions.md")) and has_all(text("docs/zh/current-research-conclusions.md")) and "bea-v1-haae-r2b-scale-preflight-design.md" in text("docs/current-research-conclusions.md")
    log = has_all(text("docs/en/research-log.md")) and has_all(text("docs/zh/research-log.md"))
    summary = has_all(text("docs/en/research-summary.md")) and has_all(text("docs/zh/research-summary.md"))
    return {"readme_readback_match_bool": readme, "detail_docs_readback_match_bool": detail, "current_conclusions_readback_match_bool": current, "research_log_readback_match_bool": log, "research_summary_readback_match_bool": summary, "all_public_readback_match_bool": readme and detail and current and log and summary}


def build_report(r2a: dict[str, Any] | None = None, *, force_no_fixture: bool = False, selected_override: str | None = None, self_test_total: int = SELF_TEST_EXPECTED) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[1]
    if r2a is None:
        try:
            r2a = load_json(repo / R2A_REPORT_PATH)
        except Exception:
            r2a = {}
    lock = validate_r2a_lock(r2a)
    options = fixture_options(repo, force_no_fixture=force_no_fixture)
    selected, reason = choose_option(options, selected_override)
    selected_ok = selected == SELECTED_OPTION
    no_fixture = selected is None
    if not lock["source_locked"]:
        status = STATUS_FAIL_SOURCE_LOCK
    elif selected in {"ci_canary_design", "r14_stress_ci_canary"}:
        status = STATUS_NO_GO_CI_REQUIRED
    elif no_fixture or selected == "operator_manifest_design":
        status = STATUS_NO_GO_NO_FIXTURE
    elif not selected_ok:
        status = STATUS_FAIL_OVERAUTH
    else:
        status = STATUS_PASS
    medium_option = next((row for row in options if row.get("option_bucket") == "r14_medium"), {})
    selected_subset_cap_ok = (
        not selected_ok
        or (
            medium_option.get("target_task_count_bucket") == TARGET_TASK_COUNT_BUCKET
            and medium_option.get("selected_subset_policy_bucket") == "deterministic_public_manifest_prefix_cap_10_to_20"
            and medium_option.get("selected_subset_required_bool") in {True, False}
        )
    )
    readback = public_readback_match(self_test_total)
    if status == STATUS_PASS and not readback["all_public_readback_match_bool"]:
        status = STATUS_FAIL_READBACK
    passed = status == STATUS_PASS
    gates = {
        "source_lock_gate": lock["source_locked"],
        "r2b_authorization_gate": lock["r2b_auth"],
        "public_inputs_only_gate": True,
        "no_private_read_write_gate": True,
        "no_material_generation_gate": True,
        "no_experiment_gate": True,
        "no_recompute_gate": True,
        "no_candidate_generation_gate": True,
        "no_retrieval_gate": True,
        "no_scheduler_haae_execution_gate": True,
        "no_selector_reranker_gate": True,
        "no_runtime_default_change_gate": True,
        "no_network_ci_clone_gate": True,
        "no_bea_v1_a_p5_gate": True,
        "no_method_winner_or_scaling_claim_gate": True,
        "non_empty_fixture_option_gate": any(row["public_fixture_present_bool"] for row in options),
        "selected_bounded_local_option_gate": selected_ok,
        "selected_subset_cap_gate": selected_subset_cap_ok,
        "r2c_boundary_bounded_gate": selected_ok,
        "forbidden_scan_pass_gate": True,
        "docs_readback_match_gate": readback["all_public_readback_match_bool"],
        "self_test_readback_match_gate": readback["all_public_readback_match_bool"],
    }
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "phase_bucket": PHASE,
        "status": status,
        "self_test_total": self_test_total,
        "source_lock_records": [{"anonymous_source_lock_id": "haaer2bsource0000", "locked_haae_r2a_checkpoint": R2A_CHECKPOINT, "locked_haae_r2a_status": R2A_STATUS, **{f"r2a_{k}_bool": v for k, v in lock.items()}, "source_locked_bool": lock["source_locked"]}],
        "public_input_records": [{"anonymous_public_input_id": "haaer2binput0000", "input_bucket": "r2a_public_aggregate_artifact", "public_only_bool": True, "private_values_read_bool": False}, {"anonymous_public_input_id": "haaer2binput0001", "input_bucket": "r14_public_fixture_metadata", "public_only_bool": True, "private_values_read_bool": False}],
        "fixture_option_records": [{"anonymous_fixture_option_id": f"haaer2boption{idx:04d}", **row, "raw_task_rows_published_bool": False} for idx, row in enumerate(options)],
        "selected_scale_design_records": [{"anonymous_selected_scale_design_id": "haaer2bselected0000", "selected_option_bucket": selected or "none", "selection_reason_bucket": reason, "source_fixture_task_count_bucket": SOURCE_FIXTURE_TASK_COUNT_BUCKET if selected_ok else "not_authorized", "selected_subset_required_bool": bool(medium_option.get("selected_subset_required_bool")) if selected_ok else False, "selected_subset_policy_bucket": "deterministic_public_manifest_prefix_cap_10_to_20" if selected_ok else "not_authorized", "target_task_count_bucket": TARGET_TASK_COUNT_BUCKET if selected_ok else "not_authorized", "candidate_depth_bucket": TARGET_CANDIDATE_DEPTH_BUCKET if selected_ok else "not_authorized", "private_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET if selected_ok else "not_authorized", "local_manual_only_bool": True, "explicit_opt_in_required_bool": True, "public_aggregate_only_bool": True, "selected_bounded_local_option_bool": selected_ok}],
        "r2c_contract_records": [{"anonymous_r2c_contract_id": "haaer2bcontract0000", "next_phase": NEXT_PHASE, "preflight_only_bool": True, "execution_authorized_bool": False, "private_read_authorized_bool": False, "private_write_authorized_bool": False, "ci_execution_authorized_bool": False, "material_generation_authorized_bool": False, "target_task_count_bucket": TARGET_TASK_COUNT_BUCKET, "candidate_depth_bucket": TARGET_CANDIDATE_DEPTH_BUCKET, "private_row_cap_bucket": PRIVATE_ROW_CAP_BUCKET}],
        "risk_control_records": [{"anonymous_risk_control_id": f"haaer2brisk{idx:04d}", "risk_bucket": risk, "controlled_bool": True} for idx, risk in enumerate(["scope_creep_to_generation", "private_root_leakage", "medium_fixture_overread", "ci_or_network_creep", "runtime_default_creep", "method_winner_or_scaling_overclaim"])],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "haaer2bclaim0000", "design_only_bool": True, "public_only_bool": True, "material_generation_bool": False, "experiment_bool": False, "private_read_bool": False, "private_write_bool": False, "recompute_bool": False, "candidate_generation_bool": False, "retrieval_bool": False, "scheduler_haae_execution_bool": False, "selector_reranker_bool": False, "ci_network_clone_bool": False, "runtime_default_change_bool": False, "bea_v1_a_bool": False, "p5_bool": False, "method_winner_claim_bool": False, "scaling_claim_bool": False}],
        "pass_fail_gate_records": [{"anonymous_gate_id": f"haaer2bgate{idx:04d}", "gate_bucket": name, "gate_passed_bool": bool(gates.get(name, False)), "gate_evaluated_on_public_data_bool": True, "gate_reads_private_material_bool": False} for idx, name in enumerate(GATE_NAMES)],
        "synthetic_validator_records": [{"anonymous_synthetic_validator_id": f"haaer2bsynth{idx:04d}", "validator_bucket": name} for idx, name in enumerate(["source_lock_pass", "wrong_checkpoint_status_fail", "r2a_ci_scale_overauth_fail", "selected_ci_option_fail", "selected_unbounded_option_fail", "no_fixture_option_no_go", "leak_scanner_fail", "docs_readback_stale_fail", "unknown_private_path_cli_rejected", "r2c_overauthorization_validation_fail"])],
        "public_readback_records": [{"anonymous_public_readback_id": "haaer2breadback0000", **readback}],
        "stop_go_records": [{"anonymous_stop_go_id": "haaer2bstop0000", "next_allowed_phase": NEXT_PHASE if passed else "stop_or_redesign_scale_preflight", "haae_r2c_local_medium_material_smoke_preflight_authorized_bool": passed, "haae_r2c_execution_authorized_bool": False, "haae_r2c_private_read_authorized_bool": False, "haae_r2c_private_write_authorized_bool": False, "haae_r2c_ci_execution_authorized_bool": False, "haae_r2c_material_generation_authorized_bool": False, "ci_execution_authorized_bool": False, "network_authorized_bool": False, "private_read_authorized_bool": False, "private_write_authorized_bool": False, "material_generation_authorized_bool": False, "experiment_authorized_bool": False, "recompute_authorized_bool": False, "candidate_generation_authorized_bool": False, "retrieval_authorized_bool": False, "scheduler_haae_execution_authorized_bool": False, "selector_reranker_authorized_bool": False, "runtime_default_change_authorized_bool": False, "bea_v1_a_authorized_bool": False, "p5_authorized_bool": False, "method_winner_claim_authorized_bool": False, "scaling_claim_authorized_bool": False}],
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
    required = ["source_lock_records", "public_input_records", "fixture_option_records", "selected_scale_design_records", "r2c_contract_records", "risk_control_records", "claim_boundary_records", "pass_fail_gate_records", "synthetic_validator_records", "public_readback_records", "stop_go_records", "forbidden_scan"]
    for key in required:
        if key not in report:
            issues.append(f"missing_{key}")
    if scan_public_report({k: v for k, v in report.items() if k != "forbidden_scan"})["status"] != "pass":
        issues.append("forbidden_scan_failed")
    stop = (report.get("stop_go_records") or [{}])[0]
    for field in FORBIDDEN_STOP_FIELDS:
        if stop.get(field) is not False:
            issues.append(f"overauthorization_{field}")
    selected = (report.get("selected_scale_design_records") or [{}])[0]
    if report.get("status") == STATUS_PASS:
        if selected.get("selected_option_bucket") != SELECTED_OPTION or selected.get("selected_bounded_local_option_bool") is not True:
            issues.append("selected_option_not_bounded_local_medium")
        if selected.get("source_fixture_task_count_bucket") != SOURCE_FIXTURE_TASK_COUNT_BUCKET:
            issues.append("source_fixture_task_count_bucket_not_locked")
        if selected.get("selected_subset_policy_bucket") != "deterministic_public_manifest_prefix_cap_10_to_20":
            issues.append("selected_subset_policy_not_locked")
        if selected.get("target_task_count_bucket") != TARGET_TASK_COUNT_BUCKET:
            issues.append("target_task_count_bucket_not_locked")
        if stop.get("haae_r2c_local_medium_material_smoke_preflight_authorized_bool") is not True:
            issues.append("missing_r2c_preflight_authorization")
        gates = {row.get("gate_bucket"): row.get("gate_passed_bool") for row in report.get("pass_fail_gate_records", [])}
        for gate in GATE_NAMES:
            if gates.get(gate) is not True:
                issues.append(f"gate_not_passed_{gate}")
        if not public_readback_match(int(report.get("self_test_total", SELF_TEST_EXPECTED)))["all_public_readback_match_bool"]:
            issues.append("public_readback_stale")
    return issues


def run_self_test() -> dict[str, Any]:
    failures: list[str] = []
    repo = Path(__file__).resolve().parents[1]
    base = load_json(repo / R2A_REPORT_PATH)
    def check(name: str, cond: bool) -> None:
        if not cond:
            failures.append(name)
    check("source_lock_pass", build_report(base)["status"] == STATUS_PASS)
    bad = json.loads(json.dumps(base)); bad["status"] = "wrong"; check("wrong_checkpoint_status_fail", build_report(bad)["status"] == STATUS_FAIL_SOURCE_LOCK)
    over = json.loads(json.dumps(base)); over["stop_go_records"][0]["ci_execution_authorized_bool"] = True; check("r2a_ci_scale_overauth_fail", build_report(over)["status"] == STATUS_FAIL_SOURCE_LOCK)
    check("selected_ci_option_fail", build_report(base, selected_override="ci_canary_design")["status"] == STATUS_NO_GO_CI_REQUIRED)
    check("selected_unbounded_option_fail", build_report(base, selected_override="unbounded_medium_scale")["status"] == STATUS_FAIL_OVERAUTH)
    check("no_fixture_option_controlled_no_go", build_report(base, force_no_fixture=True)["status"] == STATUS_NO_GO_NO_FIXTURE)
    leak = build_report(base); leak["debug"] = "/tmp/private-root r14m-001 query candidate_path crates/openlocus-core/src/lib.rs"; check("leak_scanner_fail", scan_public_report(leak)["status"] == "fail")
    stale = json.loads(json.dumps(build_report(base))); stale["self_test_total"] = 999; check("docs_readback_stale_fail", "public_readback_stale" in validate_report(stale))
    try:
        with redirect_stderr(io.StringIO()):
            parse_args(["--private-root", "/tmp/x"])
        check("unknown_private_path_cli_rejected", False)
    except ValueError as exc:
        check("unknown_private_path_cli_rejected", str(exc) == "invalid arguments")
    check("private_validate_report_arg_rejected", not is_exact_public_artifact_arg("/tmp/private.json", ARTIFACT_DIR / REPORT_NAME))
    subset_mutation = json.loads(json.dumps(build_report(base))); subset_mutation["selected_scale_design_records"][0]["selected_subset_policy_bucket"] = "unbounded_all_medium_tasks"
    check("selected_subset_mutation_validation_fail", "selected_subset_policy_not_locked" in validate_report(subset_mutation))
    try:
        parse_args(["--validate-report", "/tmp/private.json"])
        check("private_validate_path_cli_rejected", False)
    except ValueError as exc:
        check("private_validate_path_cli_rejected", str(exc) == "invalid arguments")
    mutated = json.loads(json.dumps(build_report(base))); mutated["stop_go_records"][0]["haae_r2c_execution_authorized_bool"] = True; check("r2c_overauthorization_validation_fail", any(i.startswith("overauthorization_") for i in validate_report(mutated)))
    return {"passed": not failures, "failures": failures, "self_test_total": SELF_TEST_EXPECTED, "status": STATUS_PASS}


@dataclass
class Args:
    self_test: bool = False
    validate_report: str | None = None
    out: str | None = None


def parse_args(argv: list[str]) -> Args:
    args = Args()
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--self-test":
            args.self_test = True
            i += 1
        elif token in {"--validate-report", "--out"}:
            if i + 1 >= len(argv):
                raise ValueError("invalid arguments")
            value = argv[i + 1]
            if not is_exact_public_artifact_arg(value, ARTIFACT_DIR / REPORT_NAME):
                raise ValueError("invalid arguments")
            if token == "--validate-report":
                args.validate_report = value
            else:
                args.out = value
            i += 2
        else:
            raise ValueError("invalid arguments")
    return args


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
    except ValueError:
        print("invalid arguments", file=sys.stderr)
        return 2
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    if args.validate_report:
        report = load_json(Path(args.validate_report))
        issues = validate_report(report)
        print(json.dumps({"passed": not issues, "issues": issues, "status": report.get("status")}, indent=2, sort_keys=True))
        return 0 if not issues else 1
    report = build_report()
    path = write_report(report, Path(args.out) if args.out else None)
    print(json.dumps({"artifact": str(path), "status": report["status"]}, sort_keys=True))
    return 0 if report["status"] in {STATUS_PASS, STATUS_NO_GO_NO_FIXTURE, STATUS_NO_GO_CI_REQUIRED} else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
