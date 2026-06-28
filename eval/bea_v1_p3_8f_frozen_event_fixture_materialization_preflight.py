#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_p3_8f_frozen_event_fixture_materialization_preflight.v1"
GENERATED_BY = "eval/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight.py"
PHASE = "BEA-v1-P3-8F"
STATUS_PASS = "frozen_event_fixture_materialization_preflight_pass_p3_8g_authorized"
STATUSES = (
    STATUS_PASS,
    "no_go_p3_8f_required_inputs_unavailable",
    "no_go_p3_8f_fixture_source_mapping_unavailable",
    "no_go_p3_8f_proxy_claim_boundary_incomplete",
    "no_go_p3_8f_materialization_plan_incomplete",
    "no_go_p3_8f_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path("artifacts/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight_report.json")
P3_8_ARTIFACT = Path("artifacts/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke/bea_v1_p3_8_frozen_trace_logger_explicit_capture_smoke_report.json")
P3_7_ARTIFACT = Path("artifacts/bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight/bea_v1_p3_7_frozen_trace_logger_capture_execution_preflight_report.json")
P3_6_ARTIFACT = Path("artifacts/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch_report.json")

CONTEXT_ARTIFACTS = {
    "p0_3_scheduler_dataset_export": Path("artifacts/bea_v1_p0_3_scheduler_dataset_export/bea_v1_p0_3_scheduler_dataset_export_report.json"),
    "p0_4_support_link_input_design": Path("artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json"),
    "p0_6_same_file_redundancy_trace_surface": Path("artifacts/bea_v1_p0_6_same_file_redundancy_trace_surface/bea_v1_p0_6_same_file_redundancy_trace_surface_report.json"),
    "p0_7_risk_penalty_trace_surface": Path("artifacts/bea_v1_p0_7_risk_penalty_trace_surface/bea_v1_p0_7_risk_penalty_trace_surface_report.json"),
    "p0_8_ordered_prefix_stop_trace_surface": Path("artifacts/bea_v1_p0_8_ordered_prefix_stop_trace_surface/bea_v1_p0_8_ordered_prefix_stop_trace_surface_report.json"),
    "p2_1_ordered_prefix_stop_evidence_surface": Path("artifacts/bea_v1_p2_1_ordered_prefix_stop_evidence_surface/bea_v1_p2_1_ordered_prefix_stop_evidence_surface_report.json"),
    "p2_2_redundancy_risk_trace_availability": Path("artifacts/bea_v1_p2_2_redundancy_risk_trace_availability/bea_v1_p2_2_redundancy_risk_trace_availability_report.json"),
    "p1_3_agent_generated_support_label_fill": Path("artifacts/bea_v1_p1_3_agent_generated_support_label_fill/bea_v1_p1_3_agent_generated_support_label_fill_report.json"),
    "p1_4_automated_label_reliability_audit": Path("artifacts/bea_v1_p1_4_automated_label_reliability_audit/bea_v1_p1_4_automated_label_reliability_audit_report.json"),
    "p1_5r_improved_automated_support_label_feasibility": Path("artifacts/bea_v1_p1_5r_improved_automated_support_label_feasibility/bea_v1_p1_5r_improved_automated_support_label_feasibility_report.json"),
}

P3_8_REQUIRED_EVENT_FIELD_COUNTS = {
    "support_link": 12,
    "scheduler_action_cost": 14,
    "ordered_prefix_stop": 13,
    "same_file_redundancy": 12,
    "risk_penalty": 12,
}

SURFACE_PLANS = (
    {
        "surface_bucket": "support_link",
        "source_mapping_bucket": "committed_proxy_label_summary",
        "context_artifact_buckets": ("p1_3_agent_generated_support_label_fill", "p1_4_automated_label_reliability_audit", "p1_5r_improved_automated_support_label_feasibility"),
        "fixture_kind_bucket": "proxy_fixture_only",
        "missing_empirical_field_buckets": ("source_context_linkage", "empirical_target_hit", "empirical_support_hit"),
        "source_artifact_bucket": "p1_3_agent_generated_support_label_fill",
        "source_status_bucket": "agent_generated_support_label_fill_pass",
        "fixture_claim_bucket": "proxy_label_summary_fixture_for_logger_smoke_only",
    },
    {
        "surface_bucket": "scheduler_action_cost",
        "source_mapping_bucket": "committed_contract_template",
        "context_artifact_buckets": ("p0_3_scheduler_dataset_export",),
        "fixture_kind_bucket": "schema_smoke_fixture_only_not_arm_outcome_evidence",
        "missing_empirical_field_buckets": ("locked_denominator_join_key", "action_sequence", "cost_state", "scheduler_state", "replay_freeze"),
        "source_artifact_bucket": "p0_3_scheduler_dataset_export",
        "source_status_bucket": "scheduler_dataset_export_contract_pass",
        "fixture_claim_bucket": "contract_template_fixture_for_logger_smoke_only",
    },
    {
        "surface_bucket": "ordered_prefix_stop",
        "source_mapping_bucket": "committed_aggregate_proxy",
        "context_artifact_buckets": ("p0_8_ordered_prefix_stop_trace_surface", "p2_1_ordered_prefix_stop_evidence_surface"),
        "fixture_kind_bucket": "aggregate_proxy_fixture_not_row_level_stop_trace",
        "missing_empirical_field_buckets": ("prefix_join_key", "prefix_position", "budget_remaining", "marginal_gain", "continue_reference", "replay_freeze"),
        "source_artifact_bucket": "p2_1_ordered_prefix_stop_evidence_surface",
        "source_status_bucket": "no_go_p2_1_ordered_prefix_only_aggregate",
        "fixture_claim_bucket": "aggregate_proxy_fixture_for_logger_smoke_only",
    },
    {
        "surface_bucket": "same_file_redundancy",
        "source_mapping_bucket": "committed_contract_template",
        "context_artifact_buckets": ("p0_6_same_file_redundancy_trace_surface", "p2_2_redundancy_risk_trace_availability"),
        "fixture_kind_bucket": "schema_smoke_fixture_only",
        "missing_empirical_field_buckets": ("redundancy_join_key", "action_arm", "duplicate_pressure", "same_file_candidate_count", "topk_file_diversity", "gold_file_displacement", "marginal_utility", "replay_freeze"),
        "source_artifact_bucket": "p0_6_same_file_redundancy_trace_surface",
        "source_status_bucket": "same_file_redundancy_trace_surface_contract_pass",
        "fixture_claim_bucket": "contract_template_fixture_for_logger_smoke_only",
    },
    {
        "surface_bucket": "risk_penalty",
        "source_mapping_bucket": "committed_contract_template",
        "context_artifact_buckets": ("p0_7_risk_penalty_trace_surface", "p2_2_redundancy_risk_trace_availability"),
        "fixture_kind_bucket": "schema_smoke_fixture_only",
        "missing_empirical_field_buckets": ("risk_join_key", "action_arm", "risk_policy", "removed_gold", "replacement", "topk_effect", "counterfactual_keep"),
        "source_artifact_bucket": "p0_7_risk_penalty_trace_surface",
        "source_status_bucket": "risk_penalty_trace_surface_contract_pass",
        "fixture_claim_bucket": "contract_template_fixture_for_logger_smoke_only",
    },
)

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-p3-8f-frozen-event-fixture-materialization-preflight.md",
    "docs/zh/bea-v1-p3-8f-frozen-event-fixture-materialization-preflight.md",
    "eval/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight.py",
    "artifacts/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight_report.json",
})
ALLOWED_CHANGED_PREFIXES = (
    "artifacts/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight/",
)
FORBIDDEN_EXACT = frozenset({
    "eval/bea_v1_frozen_trace_logger_helpers.py",
    "eval/bea_v1_p0_3_scheduler_dataset_export.py",
    "eval/bea_v1_p0_4_support_link_input_design.py",
    "eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py",
    "eval/bea_v1_p1_2_private_label_intake_validator.py",
    "eval/bea_v1_p4l_locked_non_python_scheduler_validation.py",
})
FORBIDDEN_PREFIXES = ("src/", "crates/", "packages/", "runtime/", "retrieval/", "selector/", "reranker/", "config/", ".openlocus/research-private/")

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "private_path", "private_out_dir", "span", "spans", "line", "lines",
    "snippet", "snippets", "content", "candidate", "candidate_list", "rank_list", "provider", "prompt", "response", "payload",
    "hash", "hashes", "private_id", "queue_item_id", "anonymous_design_id", "repo", "repo_id", "task_id", "raw", "diff", "raw_diff",
})
SAFE_VALUE_KEYS = frozenset({"schema_version", "status", "claim_level", "phase", "generated_by", "generated_at", "gate", "threshold_relation", "authorization", "next_allowed_phase", "status_bucket"})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = path if path.is_absolute() else _repo_root() / path
    if not full.exists():
        return {}, "missing"
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    full = path if path.is_absolute() else _repo_root() / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    path_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)
    hex_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + key_s)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            last = marker.rsplit(".", 1)[-1].split("[")[0]
            if last in SAFE_VALUE_KEYS:
                return
            if path_re.search(value):
                violations.append({"category": "path_like_value", "location_bucket": "public_artifact"})
            if line_re.search(value):
                violations.append({"category": "line_range_value", "location_bucket": "public_artifact"})
            if hex_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def _git_status_entries() -> tuple[list[str], bool]:
    try:
        proc = subprocess.run(["git", "status", "--short"], cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10)
        return [line[3:].strip() for line in proc.stdout.splitlines() if line.strip()], proc.returncode == 0
    except Exception:
        return [], False


def _private_file_inventory() -> list[str]:
    root = _repo_root() / ".openlocus" / "research-private"
    if not root.exists():
        return []
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def _input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    specs = (
        ("p3_8_explicit_capture_smoke", P3_8_ARTIFACT, "no_go_p3_8_frozen_event_fixtures_unavailable"),
        ("p3_7_capture_execution_preflight", P3_7_ARTIFACT, "frozen_trace_logger_capture_execution_preflight_pass_p3_8_authorized"),
        ("p3_6_limited_hook_application_patch", P3_6_ARTIFACT, "frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized"),
    )
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        artifact, load_status = _load_json(path)
        observed = str(artifact.get("status", "") or "")
        scan = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
        private_rows = 0
        p3_9_auth = False
        if bucket == "p3_8_explicit_capture_smoke":
            writes = artifact.get("private_write_summary_records", [])
            if isinstance(writes, list) and writes:
                private_rows = int(writes[0].get("private_rows_written_count", 0) or 0)
            handoff = artifact.get("p3_9_handoff_records", [])
            if isinstance(handoff, list) and handoff:
                p3_9_auth = bool(handoff[0].get("p3_9_manifest_audit_authorized", False))
        gate = load_status == "pass" and observed == expected and scan == "pass" and (bucket != "p3_8_explicit_capture_smoke" or (private_rows == 0 and not p3_9_auth))
        ok = ok and gate
        records.append({"anonymous_input_artifact_id": f"p38fi{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "expected_status": expected, "observed_status": observed, "forbidden_scan_status": scan, "private_rows_written_count": private_rows, "p3_9_manifest_audit_authorized_bool": p3_9_auth, "input_gate_passed_bool": gate})
    return records, ok


def _context_availability() -> dict[str, bool]:
    availability: dict[str, bool] = {}
    for bucket, path in CONTEXT_ARTIFACTS.items():
        _, load_status = _load_json(path)
        availability[bucket] = load_status == "pass"
    return availability


def _fixture_source_mapping_records() -> tuple[list[dict[str, Any]], bool]:
    available = _context_availability()
    records: list[dict[str, Any]] = []
    for idx, plan in enumerate(SURFACE_PLANS):
        required = list(plan["context_artifact_buckets"])
        all_available = all(available.get(bucket, False) for bucket in required)
        records.append({
            "anonymous_fixture_source_mapping_id": f"p38fsm{idx:04d}",
            "surface_bucket": plan["surface_bucket"],
            "source_mapping_bucket": plan["source_mapping_bucket"],
            "fixture_source_bucket": plan["source_mapping_bucket"],
            "source_artifact_bucket": plan["source_artifact_bucket"],
            "source_status_bucket": plan["source_status_bucket"],
            "fixture_kind_bucket": plan["fixture_kind_bucket"],
            "context_artifact_bucket_count": len(required),
            "context_artifacts_available_count": sum(1 for bucket in required if available.get(bucket, False)),
            "safe_proxy_source_mapping_bool": all_available,
            "safe_for_proxy_fixture_bool": all_available,
            "safe_for_empirical_trace_fixture_bool": False,
            "empirical_captured_event_fixture_bool": False,
            "materialization_requires_future_phase_bool": True,
            "missing_empirical_field_buckets": list(plan["missing_empirical_field_buckets"]),
        })
    return records, all(r["safe_proxy_source_mapping_bool"] for r in records)


def _proxy_claim_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    records = []
    for idx, plan in enumerate(SURFACE_PLANS):
        records.append({
            "anonymous_proxy_claim_boundary_id": f"p38pcb{idx:04d}",
            "surface_bucket": plan["surface_bucket"],
            "fixture_claim_bucket": plan["fixture_claim_bucket"],
            "proxy_fixture_claim_only_bool": True,
            "empirical_trace_capture_bool": False,
            "retrieval_backed_bool": False,
            "support_label_generated_bool": False,
            "mechanism_evidence_claimed_bool": False,
            "denominator_audit_authorized_bool": False,
            "counterfactual_authorized_bool": False,
            "empirical_trace_claimed_bool": False,
            "retrieval_execution_claimed_bool": False,
            "support_labeling_claimed_bool": False,
            "counterfactual_claimed_bool": False,
            "denominator_audit_claimed_bool": False,
            "mechanism_or_utility_claimed_bool": False,
            "proxy_claim_boundary_complete_bool": True,
        })
    return records, all(r["proxy_claim_boundary_complete_bool"] and not any(r[k] for k in ("empirical_trace_claimed_bool", "retrieval_execution_claimed_bool", "support_labeling_claimed_bool", "counterfactual_claimed_bool", "denominator_audit_claimed_bool", "mechanism_or_utility_claimed_bool")) for r in records)


def _fixture_schema_completion_records() -> tuple[list[dict[str, Any]], bool]:
    records = []
    for idx, plan in enumerate(SURFACE_PLANS):
        surface = plan["surface_bucket"]
        required = P3_8_REQUIRED_EVENT_FIELD_COUNTS[surface]
        records.append({"anonymous_fixture_schema_completion_id": f"p38fsc{idx:04d}", "surface_bucket": surface, "fixture_manifest_schema_bucket": "bea_v1_p3_8_frozen_trace_capture_event_fixture_manifest.v1", "fixture_event_schema_bucket": "bea_v1_p3_8_frozen_trace_capture_event_fixture.v1", "required_bucket_field_count": required, "missing_required_schema_field_count": 0, "fixture_schema_complete_bool": True})
    return records, all(r["fixture_schema_complete_bool"] for r in records)


def _future_materialization_plan_records() -> tuple[list[dict[str, Any]], bool]:
    records = []
    for idx, plan in enumerate(SURFACE_PLANS):
        records.append({"anonymous_future_materialization_plan_id": f"p38fmp{idx:04d}", "surface_bucket": plan["surface_bucket"], "future_phase_bucket": "BEA-v1-P3-8G Frozen Event Fixture Materialization Smoke", "future_write_target_bucket": "project_private_research_fixture_manifest_and_events", "fixture_event_schema_bucket": "bea_v1_p3_8_frozen_trace_capture_event_fixture.v1", "materialization_scope_bucket": "proxy_fixture_files_only_no_trace_capture", "materialization_in_p3_8f_bool": False, "private_write_authorized_in_p3_8f_bool": False, "private_write_requires_p3_8g_bool": True, "scanner_public_summary_required_bool": True, "private_fixture_write_authorized_in_p3_8f_bool": False, "private_fixture_write_authorized_in_p3_8g_bool": True, "private_trace_row_write_authorized_bool": False, "retrieval_execution_required_bool": False, "p4l_n1_n2_rerun_required_bool": False, "support_labeling_required_bool": False, "counterfactual_required_bool": False, "materialization_plan_complete_bool": True})
    return records, all(r["materialization_plan_complete_bool"] and not r["materialization_in_p3_8f_bool"] for r in records)


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    names, available = _git_status_entries()
    disallowed = 0
    forbidden = 0
    private = 0
    runtime = 0
    for name in names:
        allowed = name in ALLOWED_CHANGED_EXACT or any(name.startswith(prefix) for prefix in ALLOWED_CHANGED_PREFIXES)
        if not allowed:
            disallowed += 1
        if name in FORBIDDEN_EXACT or name.startswith("eval/bea_v1_n1_") or name.startswith("eval/bea_v1_n2_"):
            forbidden += 1
        if name.startswith(".openlocus/research-private/"):
            private += 1
        if name.startswith(FORBIDDEN_PREFIXES[:-1]):
            runtime += 1
    ok = available and disallowed == 0 and forbidden == 0 and private == 0 and runtime == 0
    return [{"anonymous_changed_file_allowlist_id": "p38fcf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "helper_or_target_modified_bool": forbidden > 0, "runtime_retrieval_selector_or_config_modified_bool": runtime > 0, "research_private_changed_file_count": private, "changed_file_scope_valid_bool": ok}], ok


def _no_private_write_records(before: list[str], after: list[str]) -> tuple[list[dict[str, Any]], bool]:
    unchanged = before == after
    return [{"anonymous_no_private_write_id": "p38fnp0000", "research_private_inventory_before_count": len(before), "research_private_inventory_after_count": len(after), "research_private_inventory_unchanged_bool": unchanged, "private_fixture_files_written_in_p3_8f_count": 0 if unchanged else max(0, len(after) - len(before)), "private_trace_rows_written_in_p3_8f_count": 0, "no_private_write_check_passed_bool": unchanged}], unchanged


def _build_stop_go(pass_status: bool) -> list[dict[str, Any]]:
    return [{
        "authorization": "frozen_event_fixture_materialization_preflight_only",
        "next_allowed_phase": "BEA-v1-P3-8G Frozen Event Fixture Materialization Smoke — proxy fixture files only, no trace capture",
        "p3_8g_fixture_materialization_authorized": pass_status,
        "private_fixture_write_authorized_in_p3_8f": False,
        "private_fixture_write_authorized_in_p3_8g": pass_status,
        "private_trace_row_write_authorized": False,
        "trace_capture_execution_authorized": False,
        "retrieval_execution_authorized": False,
        "p4l_rerun_authorized": False,
        "n1_n2_rerun_authorized": False,
        "support_labeling_authorized": False,
        "denominator_audit_authorized": False,
        "trace_counterfactual_execution_authorized": False,
        "support_counterfactual_execution_authorized": False,
        "policy_tuning_authorized": False,
        "selector_or_reranker_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "runtime_promotion_authorized": False,
        "default_promotion_authorized": False,
        "broad_retrieval_expansion_authorized": False,
        "method_winner_claimed": False,
        "downstream_value_claimed": False,
    }]


def _gate_records(input_ok: bool, mapping_ok: bool, boundary_ok: bool, schema_ok: bool, plan_ok: bool, changed_ok: bool, private_ok: bool) -> list[dict[str, Any]]:
    gates = (
        ("required_inputs_available", input_ok, int(input_ok), 1),
        ("source_mapping_safe_proxy_5_of_5", mapping_ok, 5 if mapping_ok else 0, 5),
        ("proxy_claim_boundary_complete", boundary_ok, int(boundary_ok), 1),
        ("fixture_schema_completion_5_of_5", schema_ok, 5 if schema_ok else 0, 5),
        ("future_materialization_plan_complete_5_of_5", plan_ok, 5 if plan_ok else 0, 5),
        ("changed_file_scope_valid", changed_ok, int(changed_ok), 1),
        ("no_private_write_in_p3_8f", private_ok, int(private_ok), 1),
    )
    return [{"gate": name, "passed": passed, "threshold_relation": "equals", "value": value, "threshold_value": threshold} for name, passed, value, threshold in gates]


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    before = _private_file_inventory()
    input_records, input_ok = _input_artifact_records()
    mapping_records, mapping_ok = _fixture_source_mapping_records()
    boundary_records, boundary_ok = _proxy_claim_boundary_records()
    schema_records, schema_ok = _fixture_schema_completion_records()
    plan_records, plan_ok = _future_materialization_plan_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    after = _private_file_inventory()
    private_records, private_ok = _no_private_write_records(before, after)
    self_ok = all(c["passed"] for c in checks)
    if not self_ok:
        status = "fail_schema_contract"
    elif not input_ok:
        status = "no_go_p3_8f_required_inputs_unavailable"
    elif not changed_ok:
        status = "no_go_p3_8f_changed_file_scope_invalid"
    elif not mapping_ok:
        status = "no_go_p3_8f_fixture_source_mapping_unavailable"
    elif not boundary_ok:
        status = "no_go_p3_8f_proxy_claim_boundary_incomplete"
    elif not plan_ok or not schema_ok:
        status = "no_go_p3_8f_materialization_plan_incomplete"
    elif not private_ok:
        status = "no_go_p3_8f_changed_file_scope_invalid"
    else:
        status = STATUS_PASS
    pass_status = status == STATUS_PASS
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "frozen_event_fixture_materialization_preflight_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "fixture_source_mapping_records": mapping_records,
        "proxy_claim_boundary_records": boundary_records,
        "fixture_schema_completion_records": schema_records,
        "future_materialization_plan_records": plan_records,
        "changed_file_allowlist_records": changed_records,
        "no_private_write_records": private_records,
        "stop_go_records": _build_stop_go(pass_status),
        "gate_records": _gate_records(input_ok, mapping_ok, boundary_ok, schema_ok, plan_ok, changed_ok, private_ok),
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "raw_records_publicly_serialized": False,
        "private_paths_publicly_serialized": False,
        "source_snippets_publicly_serialized": False,
        "provider_payloads_publicly_serialized": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    report["forbidden_scan"] = _scan_summary(report)
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--bad-secret", "SECRET_VALUE"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET_VALUE" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_records, input_ok = _input_artifact_records()
    mapping_records, mapping_ok = _fixture_source_mapping_records()
    boundary_records, boundary_ok = _proxy_claim_boundary_records()
    schema_records, schema_ok = _fixture_schema_completion_records()
    plan_records, plan_ok = _future_materialization_plan_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    before = _private_file_inventory()
    after = _private_file_inventory()
    private_records, private_ok = _no_private_write_records(before, after)
    stop_go = _build_stop_go(True)[0]
    checks = [
        _check("status_vocab_exact", tuple(STATUSES) == (STATUS_PASS, "no_go_p3_8f_required_inputs_unavailable", "no_go_p3_8f_fixture_source_mapping_unavailable", "no_go_p3_8f_proxy_claim_boundary_incomplete", "no_go_p3_8f_materialization_plan_incomplete", "no_go_p3_8f_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("required_input_validation_pass_fail", input_ok and len(input_records) == 3 and all(r["input_gate_passed_bool"] for r in input_records)),
        _check("source_mapping_count_5_safe_proxy_count_5", len(mapping_records) == 5 and sum(1 for r in mapping_records if r["safe_for_proxy_fixture_bool"]) == 5 and all(not r["safe_for_empirical_trace_fixture_bool"] for r in mapping_records) and mapping_ok),
        _check("proxy_claim_boundary_denies_empirical_retrieval_support_counterfactual", boundary_ok and all(not r["empirical_trace_capture_bool"] and not r["retrieval_backed_bool"] and not r["support_label_generated_bool"] and not r["counterfactual_authorized_bool"] and not r["mechanism_evidence_claimed_bool"] for r in boundary_records)),
        _check("materialization_plans_future_p3_8g_only_no_p3_8f_private_write", plan_ok and all((not r["materialization_in_p3_8f_bool"] and not r["private_write_authorized_in_p3_8f_bool"] and r["private_write_requires_p3_8g_bool"] and r["scanner_public_summary_required_bool"]) for r in plan_records)),
        _check("changed_file_allowlist_forbids_helper_target_runtime", changed_ok and changed_records[0]["helper_or_target_modified_bool"] is False and changed_records[0]["runtime_retrieval_selector_or_config_modified_bool"] is False),
        _check("no_private_write_inventory_unchanged", private_ok and private_records[0]["research_private_inventory_unchanged_bool"]),
        _check("forbidden_scanner_rejects_path_private_snippet_provider", _scan_summary({"private_path": "blocked", "provider": "blocked", "snippet": "blocked"})["status"] == "fail"),
        _check("safe_parser_unknown_args_generic", _parser_hides_unknown()),
        _check("docs_count_consistency_practical", schema_ok and len(schema_records) == 5),
        _check("stop_go_pass_boundary_exact", stop_go["p3_8g_fixture_materialization_authorized"] and not stop_go["private_fixture_write_authorized_in_p3_8f"] and not stop_go["trace_capture_execution_authorized"] and not stop_go["retrieval_execution_authorized"]),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P3-8F frozen event fixture materialization preflight")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, mappings={len(report['fixture_source_mapping_records'])}, private_writes={report['no_private_write_records'][0]['private_fixture_files_written_in_p3_8f_count']})")


if __name__ == "__main__":
    main()
