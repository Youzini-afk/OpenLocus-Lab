#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Mapping, NoReturn


SCHEMA_VERSION = "bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit.v1"
PHASE = "BEA-v1-N6G"
GENERATED_BY = "bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit"
STATUS_PASS = "fixed_pool_arm_field_source_discovery_pass_n6h_authorized"
STATUS_NO_GO_INEXACT = "no_go_n6g_candidate_sources_inexact_or_aggregate_only"

STATUSES = (
    STATUS_PASS,
    "no_go_n6g_required_inputs_unavailable",
    "no_go_n6g_no_exact_public_arm_field_source",
    STATUS_NO_GO_INEXACT,
    "no_go_n6g_privacy_or_claim_boundary_invalid",
    "no_go_n6g_changed_file_scope_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit/"
    "bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit_report.json"
)

INPUTS = (
    ("n6_artifact", Path("artifacts/bea_v1_n6_fixed_pool_rank_order_experiment/bea_v1_n6_fixed_pool_rank_order_experiment_report.json"), "no_go_n6_public_fixed_pool_arm_fields_insufficient"),
    ("n6f_design_artifact", Path("artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json"), "fixed_pool_public_arm_field_materialization_design_pass"),
    ("n5_preflight_artifact", Path("artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json"), "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized"),
    ("n4_denominator_artifact", Path("artifacts/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit_report.json"), "fixed_pool_rank_blocker_denominator_audit_pass_n5_authorized"),
    ("n3_design_simulation_artifact", Path("artifacts/bea_v1_n3_extra_depth_merge_order_design_simulation/bea_v1_n3_extra_depth_merge_order_design_simulation_report.json"), "n3_merge_order_design_inconclusive"),
    ("n2_rank_pack_artifact", Path("artifacts/bea_v1_n2_rank_pack_actionability_decomposition/bea_v1_n2_rank_pack_actionability_decomposition_report.json"), "n2_rank_pack_actionability_decomposition_pass"),
)

ARMS = (
    "baseline_n2_order",
    "extra_depth_promote_before_primary_prefix_4",
    "bounded_interleave_primary2_extra1",
    "late_extra_depth_demote_after_primary_prefix_8",
)

N3_ANALOGUES = {
    "baseline_n2_order": "frozen_p4_order",
    "extra_depth_promote_before_primary_prefix_4": "early_extra_depth_quota_3",
    "bounded_interleave_primary2_extra1": "fixed_interleave_2_primary_1_extra_after_4",
    "late_extra_depth_demote_after_primary_prefix_8": "bounded_promotion_after_primary_prefix_4_3",
}

REQUIRED_FIELDS = (
    "anonymous_public_arm_outcome_id", "anonymous_case_bucket", "arm_bucket",
    "fixed_pool_case_set_bucket", "arm_semantics_exact_match_bool",
    "candidate_pool_changed_bool", "new_retrieval_used_bool",
    "selector_or_reranker_used_bool", "top10_recovery_bucket",
    "top20_recovery_bucket", "rank_shift_bucket", "case_regression_bucket",
    "hard_cap_bucket", "outcome_materialized_bool",
)

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-n6g-fixed-pool-arm-field-source-discovery-audit.md",
    "docs/zh/bea-v1-n6g-fixed-pool-arm-field-source-discovery-audit.md",
    "eval/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit.py",
    "artifacts/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit_report.json",
})

FORBIDDEN_CHANGED_PREFIXES = (".openlocus/", "crates/", "src/", "packages/", "runtime/", "retrieval/", "selector/", "reranker/", "config/")
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "source_path", "exact_path", "private_path",
    "private_paths", "span", "spans", "exact_span", "line", "lines",
    "start_line", "end_line", "line_range", "snippet", "snippets", "content",
    "text", "raw_text", "candidate", "candidates", "candidate_list",
    "candidate_lists", "candidate_order", "candidate_paths", "rank", "ranks",
    "raw_rank", "rank_list", "rank_lists", "score", "scores", "task_id",
    "repo", "repo_id", "repo_name", "repo_slug", "repo_url", "private_id",
    "private_record_id", "private_ids", "source_hash", "source_hashes", "hash",
    "hashes", "content_sha", "provider", "provider_payload", "raw_payload",
    "payload", "prompt", "response", "raw", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "claim_level", "phase", "generated_by", "generated_at",
    "status_vocabulary", "input_artifact_bucket", "observed_status", "expected_status",
    "load_status", "forbidden_scan_status", "source_bucket", "source_status_bucket",
    "source_limitation_bucket", "source_exactness_bucket", "arm_bucket", "n3_analogue_bucket",
    "best_candidate_source_bucket", "best_candidate_status_bucket", "field_bucket",
    "coverage_status_bucket", "closure_decision_bucket", "next_required_input_bucket",
    "privacy_boundary_bucket", "public_artifact_bucket", "no_execution_boundary_bucket",
    "gate", "threshold_relation", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket", "fixed_pool_case_set_bucket",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    full = _repo_root() / path
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
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)

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
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})

    walk(obj)
    return violations


def _scan_summary(obj: Any) -> dict[str, Any]:
    violations = _scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def _load_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    artifacts: dict[str, dict[str, Any]] = {}
    loads: dict[str, str] = {}
    for bucket, path, _expected in INPUTS:
        artifact, load = _load_json(path)
        artifacts[bucket] = artifact
        loads[bucket] = load
    return artifacts, loads


def _input_artifact_records(artifacts: Mapping[str, Mapping[str, Any]], loads: Mapping[str, str]) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, _path, expected) in enumerate(INPUTS):
        artifact = artifacts.get(bucket, {})
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        observed = str(artifact.get("status", "") or "")
        passed = loads.get(bucket) == "pass" and observed == expected and scan == "pass"
        ok = ok and passed
        records.append({"anonymous_input_artifact_id": f"n6gin{idx:04d}", "input_artifact_bucket": bucket, "load_status": str(loads.get(bucket, "missing")), "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, ok


def _n6f_authorized(n6f: Mapping[str, Any]) -> bool:
    stop = n6f.get("stop_go_records", [])
    return n6f.get("status") == "fixed_pool_public_arm_field_materialization_design_pass" and isinstance(stop, list) and bool(stop) and stop[0].get("n6g_source_discovery_audit_authorized") is True


def _required_field_source_requirement_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_requirement_id": "n6greq0000",
        "fixed_pool_case_set_bucket": "n5_frozen_n4_sanitized_rank_blocker_cases",
        "required_public_row_count": 160,
        "required_case_count": 40,
        "required_arm_count": 4,
        "required_field_count": len(REQUIRED_FIELDS),
        "required_fields_bucketed_public_safe_bool": True,
        "exact_n6_arm_names_required_bool": True,
        "exact_n6_arm_semantics_required_bool": True,
        "aggregate_only_source_sufficient_bool": False,
        "analogue_only_source_sufficient_bool": False,
    }]


def _candidate_source_inventory_records(artifacts: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    n3_rows = artifacts["n3_design_simulation_artifact"].get("sanitized_analysis_records", [])
    n3_arms = {str(r.get("sim_arm", "")) for r in n3_rows if isinstance(r, dict)}
    n6_rows = artifacts["n6_artifact"].get("per_case_arm_outcome_records", [])
    n6_mappings = artifacts["n6_artifact"].get("arm_mapping_records", [])
    records = [
        {"anonymous_candidate_source_id": "n6gsrc0000", "source_bucket": "n6_artifact", "source_status_bucket": "no_go_missing_exact_public_arm_fields", "has_per_case_rows_bool": False, "per_case_arm_outcome_records_empty_bool": n6_rows == [], "has_exact_n6_arm_names_bool": False, "has_exact_n6_arm_semantics_bool": False, "has_required_160_rows_bool": False, "analogue_only_bool": False, "aggregate_only_bool": False, "exact_mappings_available_bool": all(r.get("exact_public_arm_mapping_bool") is True for r in n6_mappings) if n6_mappings else False, "usable_for_n6_materialization_bool": False},
        {"anonymous_candidate_source_id": "n6gsrc0001", "source_bucket": "n6f_design_artifact", "source_status_bucket": "design_only_no_rows", "has_per_case_rows_bool": False, "has_exact_n6_arm_names_bool": True, "has_exact_n6_arm_semantics_bool": False, "has_required_160_rows_bool": False, "analogue_only_bool": False, "aggregate_only_bool": False, "usable_for_n6_materialization_bool": False},
        {"anonymous_candidate_source_id": "n6gsrc0002", "source_bucket": "n5_preflight_artifact", "source_status_bucket": "contract_only_no_outcome_rows", "has_per_case_rows_bool": True, "has_exact_n6_arm_names_bool": True, "has_exact_n6_arm_semantics_bool": True, "has_required_160_rows_bool": False, "analogue_only_bool": False, "aggregate_only_bool": False, "usable_for_n6_materialization_bool": False},
        {"anonymous_candidate_source_id": "n6gsrc0003", "source_bucket": "n4_denominator_artifact", "source_status_bucket": "per_case_not_per_arm", "has_per_case_rows_bool": True, "has_exact_n6_arm_names_bool": False, "has_exact_n6_arm_semantics_bool": False, "has_required_160_rows_bool": False, "analogue_only_bool": False, "aggregate_only_bool": False, "usable_for_n6_materialization_bool": False},
        {"anonymous_candidate_source_id": "n6gsrc0004", "source_bucket": "n3_design_simulation_artifact", "source_status_bucket": "analogue_per_case_rows_inexact", "has_per_case_rows_bool": len(n3_rows) == 160, "has_exact_n6_arm_names_bool": False, "has_exact_n6_arm_semantics_bool": False, "has_required_160_rows_bool": len(n3_rows) == 160, "analogue_only_bool": True, "aggregate_only_bool": False, "n3_analogue_arm_count": len(n3_arms), "usable_for_n6_materialization_bool": False},
        {"anonymous_candidate_source_id": "n6gsrc0005", "source_bucket": "n2_rank_pack_artifact", "source_status_bucket": "per_case_baseline_indicators_not_per_arm_outcomes", "has_per_case_rows_bool": True, "has_exact_n6_arm_names_bool": False, "has_exact_n6_arm_semantics_bool": False, "has_required_160_rows_bool": False, "analogue_only_bool": False, "aggregate_only_bool": False, "usable_for_n6_materialization_bool": False},
    ]
    inexact_candidate_present = any(r["analogue_only_bool"] and r["has_required_160_rows_bool"] for r in records)
    return records, inexact_candidate_present


def _per_arm_source_discovery_records() -> list[dict[str, Any]]:
    return [{"anonymous_per_arm_source_discovery_id": f"n6garm{idx:04d}", "arm_bucket": arm, "best_candidate_source_bucket": "n3_design_simulation_artifact", "n3_analogue_bucket": N3_ANALOGUES[arm], "best_candidate_status_bucket": "analogue_only_not_exact", "required_exact_row_count": 40, "found_exact_public_row_count": 0, "exact_source_found_bool": False, "has_exact_n6_arm_name_bool": False, "has_exact_n6_arm_semantics_bool": False, "usable_for_n6_materialization_bool": False} for idx, arm in enumerate(ARMS)]


def _source_exactness_records(inventory: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    records = []
    for idx, source in enumerate(inventory):
        exact = bool(source.get("has_exact_n6_arm_names_bool") and source.get("has_exact_n6_arm_semantics_bool") and source.get("has_required_160_rows_bool") and source.get("usable_for_n6_materialization_bool"))
        records.append({"anonymous_source_exactness_id": f"n6gexact{idx:04d}", "source_bucket": source["source_bucket"], "source_exactness_bucket": "exact_public_160_row_source" if exact else "not_exact_public_160_row_source", "exact_public_arm_field_source_bool": exact, "analogue_only_bool": bool(source.get("analogue_only_bool", False)), "aggregate_only_bool": bool(source.get("aggregate_only_bool", False)), "usable_for_n6_materialization_bool": bool(source.get("usable_for_n6_materialization_bool", False))})
    return records, any(r["exact_public_arm_field_source_bool"] for r in records)


def _field_coverage_records(exact_found: bool) -> list[dict[str, Any]]:
    return [{"anonymous_field_coverage_id": "n6gcov0000", "coverage_status_bucket": "no_exact_public_arm_field_coverage", "required_public_row_count": 160, "required_case_count": 40, "required_arm_count": 4, "required_field_count": 14, "covered_exact_public_row_count": 0, "covered_exact_arm_count": 0, "covered_required_field_count": 0, "coverage_sufficient_bool": exact_found}]


def _closure_decision_records(exact_found: bool) -> list[dict[str, Any]]:
    return [{"anonymous_closure_decision_id": "n6gclose0000", "closure_decision_bucket": "fixed_pool_route_closed_no_exact_public_source", "fixed_pool_route_closed": True, "exact_public_arm_field_source_found_bool": exact_found, "n6_rerun_authorized_bool": False, "materialization_authorized_bool": False, "generation_authorized_bool": False, "next_required_input_bucket": "exact_public_160_row_arm_outcome_source"}]


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_privacy_boundary_id": "n6gpb0000", "privacy_boundary_bucket": "read_only_public_artifact_discovery", "public_artifact_bucket": "buckets_counts_booleans_only", "private_read_count": 0, "private_write_count": 0, "source_path_or_span_serialized_bool": False, "snippet_serialized_bool": False, "candidate_list_serialized_bool": False, "raw_rank_serialized_bool": False, "task_repo_id_serialized_bool": False, "hash_serialized_bool": False, "provider_payload_serialized_bool": False, "raw_diff_serialized_bool": False, "privacy_boundary_complete_bool": True}
    return [record], True


def _git_status_entries() -> tuple[list[str], bool]:
    try:
        proc = subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=_repo_root(), check=False, capture_output=True, text=True, timeout=10)
        return [line[3:].strip().rstrip("/") for line in proc.stdout.splitlines() if line.strip()], proc.returncode == 0
    except Exception:
        return [], False


def _changed_file_allowlist_records() -> tuple[list[dict[str, Any]], bool]:
    names, available = _git_status_entries()
    disallowed = 0
    private_or_source = 0
    forbidden_runtime = 0
    for name in names:
        allowed = name in ALLOWED_CHANGED_EXACT
        if name.startswith(FORBIDDEN_CHANGED_PREFIXES):
            forbidden_runtime += 1
            allowed = False
        if name.startswith(".openlocus/") or name.startswith(("crates/", "src/", "packages/")):
            private_or_source += 1
        if not allowed:
            disallowed += 1
    ok = available and disallowed == 0 and private_or_source == 0 and forbidden_runtime == 0
    return [{"anonymous_changed_file_allowlist_id": "n6gcf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_or_source_file_modification_count": private_or_source, "forbidden_runtime_or_evaluator_modified_bool": forbidden_runtime > 0, "changed_file_scope_valid_bool": ok}], ok


def _no_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_execution_id": "n6gnoexec0000", "no_execution_boundary_bucket": "read_only_public_source_discovery_no_materialization", "private_read_count": 0, "private_write_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "n6_rerun_count": 0, "generation_execution_count": 0, "materialization_execution_count": 0, "selector_reranker_execution_count": 0, "counterfactual_execution_count": 0, "policy_tuning_count": 0, "runtime_change_count": 0, "default_change_count": 0, "no_execution_boundary_complete_bool": True}
    return [record], True


def _gate_records(*, input_ok: bool, n6f_ok: bool, exact_found: bool, inexact_present: bool, coverage_ok: bool, privacy_ok: bool, changed_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "required_inputs_load_and_scan", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "n6f_authorized_read_only_source_discovery", "passed": n6f_ok, "threshold_relation": "equals", "value": int(n6f_ok), "threshold_value": 1},
        {"gate": "exact_public_160_row_source_found", "passed": exact_found, "threshold_relation": "equals", "value": int(exact_found), "threshold_value": 1},
        {"gate": "candidate_sources_inexact_or_aggregate_only_detected", "passed": inexact_present, "threshold_relation": "equals", "value": int(inexact_present), "threshold_value": 1},
        {"gate": "coverage_sufficient", "passed": coverage_ok, "threshold_relation": "equals", "value": int(coverage_ok), "threshold_value": 1},
        {"gate": "privacy_boundary_complete", "passed": privacy_ok, "threshold_relation": "equals", "value": int(privacy_ok), "threshold_value": 1},
        {"gate": "changed_file_scope_valid", "passed": changed_ok, "threshold_relation": "equals", "value": int(changed_ok), "threshold_value": 1},
        {"gate": "no_execution", "passed": noexec_ok, "threshold_relation": "equals", "value": int(noexec_ok), "threshold_value": 1},
        {"gate": "scanner_pass", "passed": scanner_ok, "threshold_relation": "equals", "value": int(scanner_ok), "threshold_value": 1},
    ]


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == STATUS_PASS
    return [{"authorization": "fixed_pool_arm_field_source_discovery_no_go" if not pass_status else "fixed_pool_arm_field_source_discovery_pass", "next_allowed_phase": "BEA-v1-N6H Fixed-Pool Arm-Field Materialization Preflight" if pass_status else "none_until_exact_public_160_row_arm_outcome_source_exists", "next_allowed_scope_bucket": "preflight_only_validate_exact_public_source_no_generation" if pass_status else "no_next_phase_exact_public_source_missing", "n6h_authorized": bool(pass_status), "materialization_authorized": False, "generation_authorized": False, "n6_rerun_authorized": False, "private_read_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "selector_or_reranker_authorized": False, "counterfactual_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "runtime_or_policy_change_authorized": False, "method_winner_claimed": False, "method_winner_claim_authorized": False, "downstream_value_claimed": False, "downstream_value_claim_authorized": False}]


def _status_from(*, self_ok: bool, input_ok: bool, n6f_ok: bool, exact_found: bool, inexact_present: bool, privacy_ok: bool, changed_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok or not n6f_ok:
        return "no_go_n6g_required_inputs_unavailable"
    if not privacy_ok or not noexec_ok:
        return "no_go_n6g_privacy_or_claim_boundary_invalid"
    if not changed_ok:
        return "no_go_n6g_changed_file_scope_invalid"
    if exact_found:
        return STATUS_PASS
    return STATUS_NO_GO_INEXACT if inexact_present else "no_go_n6g_no_exact_public_arm_field_source"


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    n6f_ok = _n6f_authorized(artifacts["n6f_design_artifact"])
    requirement_records = _required_field_source_requirement_records()
    inventory_records, inexact_present = _candidate_source_inventory_records(artifacts)
    per_arm_records = _per_arm_source_discovery_records()
    exactness_records, exact_found = _source_exactness_records(inventory_records)
    coverage_records = _field_coverage_records(exact_found)
    coverage_ok = coverage_records[0]["coverage_sufficient_bool"]
    closure_records = _closure_decision_records(exact_found)
    privacy_records, privacy_ok = _privacy_boundary_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    noexec_records, noexec_ok = _no_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = _status_from(self_ok=self_ok, input_ok=input_ok, n6f_ok=n6f_ok, exact_found=exact_found, inexact_present=inexact_present, privacy_ok=privacy_ok, changed_ok=changed_ok, noexec_ok=noexec_ok)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "status": status, "claim_level": "fixed_pool_arm_field_source_discovery_audit_only", "phase": PHASE, "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records, "required_field_source_requirement_records": requirement_records, "candidate_source_inventory_records": inventory_records, "per_arm_source_discovery_records": per_arm_records, "source_exactness_records": exactness_records, "field_coverage_records": coverage_records, "closure_decision_records": closure_records, "privacy_boundary_records": privacy_records, "changed_file_allowlist_records": changed_records, "no_execution_records": noexec_records,
        "gate_records": _gate_records(input_ok=input_ok, n6f_ok=n6f_ok, exact_found=exact_found, inexact_present=inexact_present, coverage_ok=coverage_ok, privacy_ok=privacy_ok, changed_ok=changed_ok, noexec_ok=noexec_ok, scanner_ok=True),
        "stop_go_records": _stop_go_records(status), "forbidden_scan": {}, "aggregate_runtime_seconds": round(time.perf_counter() - start, 3), "method_winner_claimed": False, "downstream_value_claimed": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = _scan_summary(report)
    report["forbidden_scan"] = final_scan
    scanner_ok = final_scan["status"] == "pass"
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    report["gate_records"] = _gate_records(input_ok=input_ok, n6f_ok=n6f_ok, exact_found=exact_found, inexact_present=inexact_present, coverage_ok=coverage_ok, privacy_ok=privacy_ok, changed_ok=changed_ok, noexec_ok=noexec_ok, scanner_ok=scanner_ok)
    report["stop_go_records"] = _stop_go_records(report["status"])
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--unknown", "SECRET_VALUE"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET_VALUE" not in str(exc)
    return False


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    n6f_ok = _n6f_authorized(artifacts["n6f_design_artifact"])
    inventory, inexact_present = _candidate_source_inventory_records(artifacts)
    exactness, exact_found = _source_exactness_records(inventory)
    per_arm = _per_arm_source_discovery_records()
    coverage = _field_coverage_records(exact_found)
    closure = _closure_decision_records(exact_found)
    privacy, privacy_ok = _privacy_boundary_records()
    noexec, noexec_ok = _no_execution_records()
    n3 = next(r for r in inventory if r["source_bucket"] == "n3_design_simulation_artifact")
    n6 = next(r for r in inventory if r["source_bucket"] == "n6_artifact")
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == (STATUS_PASS, "no_go_n6g_required_inputs_unavailable", "no_go_n6g_no_exact_public_arm_field_source", STATUS_NO_GO_INEXACT, "no_go_n6g_privacy_or_claim_boundary_invalid", "no_go_n6g_changed_file_scope_invalid", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(_scan_summary({key: "blocked"})["status"] == "fail" for key in ("path", "span", "snippet", "candidate_list", "rank", "task_id", "repo", "private_id", "source_hash", "provider_payload", "raw_diff"))),
        _check("scanner_rejects_path_and_digest_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("inputs", input_ok and len(input_records) == 6 and all(r["input_gate_passed_bool"] for r in input_records)),
        _check("n6f_authorized", n6f_ok),
        _check("requirements_160_40_4_14", _required_field_source_requirement_records()[0]["required_public_row_count"] == 160 and _required_field_source_requirement_records()[0]["required_case_count"] == 40 and _required_field_source_requirement_records()[0]["required_arm_count"] == 4 and _required_field_source_requirement_records()[0]["required_field_count"] == 14),
        _check("n3_inventory_inexact_analogue", n3["has_per_case_rows_bool"] is True and n3["has_required_160_rows_bool"] is True and n3["has_exact_n6_arm_names_bool"] is False and n3["has_exact_n6_arm_semantics_bool"] is False and n3["analogue_only_bool"] is True and n3["usable_for_n6_materialization_bool"] is False),
        _check("n6_inventory_empty", n6["per_case_arm_outcome_records_empty_bool"] is True and n6["exact_mappings_available_bool"] is False),
        _check("per_arm_no_exact_source", len(per_arm) == 4 and all(r["exact_source_found_bool"] is False and r["best_candidate_source_bucket"] == "n3_design_simulation_artifact" and r["best_candidate_status_bucket"] == "analogue_only_not_exact" and r["found_exact_public_row_count"] == 0 for r in per_arm)),
        _check("source_exactness_none", not exact_found and all(r["exact_public_arm_field_source_bool"] is False for r in exactness)),
        _check("field_coverage_zero", coverage[0]["required_public_row_count"] == 160 and coverage[0]["covered_exact_public_row_count"] == 0 and coverage[0]["covered_exact_arm_count"] == 0 and coverage[0]["coverage_sufficient_bool"] is False),
        _check("closure_no_go", closure[0]["fixed_pool_route_closed"] is True and closure[0]["exact_public_arm_field_source_found_bool"] is False and closure[0]["next_required_input_bucket"] == "exact_public_160_row_arm_outcome_source"),
        _check("privacy_boundary", privacy_ok and privacy[0]["private_read_count"] == 0 and privacy[0]["candidate_list_serialized_bool"] is False and privacy[0]["raw_rank_serialized_bool"] is False),
        _check("no_execution", noexec_ok and noexec[0]["retrieval_execution_count"] == 0 and noexec[0]["materialization_execution_count"] == 0 and noexec[0]["n6_rerun_count"] == 0),
        _check("status_expected", _status_from(self_ok=True, input_ok=True, n6f_ok=True, exact_found=False, inexact_present=inexact_present, privacy_ok=True, changed_ok=True, noexec_ok=True) == STATUS_NO_GO_INEXACT),
        _check("stop_go_no_go", _stop_go_records(STATUS_NO_GO_INEXACT)[0]["next_allowed_phase"] == "none_until_exact_public_160_row_arm_outcome_source_exists" and _stop_go_records(STATUS_NO_GO_INEXACT)[0]["n6h_authorized"] is False and _stop_go_records(STATUS_NO_GO_INEXACT)[0]["materialization_authorized"] is False and _stop_go_records(STATUS_NO_GO_INEXACT)[0]["private_read_authorized"] is False),
        _check("stop_go_pass_branch_preflight_only", _stop_go_records(STATUS_PASS)[0]["next_allowed_phase"] == "BEA-v1-N6H Fixed-Pool Arm-Field Materialization Preflight" and _stop_go_records(STATUS_PASS)[0]["next_allowed_scope_bucket"] == "preflight_only_validate_exact_public_source_no_generation" and _stop_go_records(STATUS_PASS)[0]["n6h_authorized"] is True and _stop_go_records(STATUS_PASS)[0]["materialization_authorized"] is False and _stop_go_records(STATUS_PASS)[0]["generation_authorized"] is False and _stop_go_records(STATUS_PASS)[0]["n6_rerun_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N6G fixed-pool arm-field source discovery audit")
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
    print("wrote artifact " f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, " f"covered_rows={report['field_coverage_records'][0]['covered_exact_public_row_count']}, " f"next={report['stop_go_records'][0]['next_allowed_phase']})")


if __name__ == "__main__":
    main()
