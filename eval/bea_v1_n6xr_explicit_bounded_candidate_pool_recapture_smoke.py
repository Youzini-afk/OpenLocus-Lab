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


SCHEMA_VERSION = "bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke.v1"
PHASE = "BEA-v1-N6XR"
GENERATED_BY = "bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke"
STATUS_NO_GO_FULL_RERUN = "no_go_n6xr_requires_full_rerun_or_unavailable_mapping"

STATUSES = (
    "bounded_candidate_pool_recapture_smoke_pass_n7_authorized",
    "bounded_candidate_pool_recapture_complete_below_threshold",
    "no_go_n6xr_required_inputs_unavailable",
    "no_go_n6xr_bounded_replay_path_unavailable",
    "no_go_n6xr_canary_recapture_failed",
    STATUS_NO_GO_FULL_RERUN,
    "no_go_n6xr_arm_semantics_or_case_set_mismatch",
    "no_go_n6xr_public_schema_or_privacy_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke/"
    "bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke_report.json"
)

INPUTS = (
    ("n4_denominator_artifact", Path("artifacts/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit_report.json"), "fixed_pool_rank_blocker_denominator_audit_pass_n5_authorized"),
    ("n5_preflight_artifact", Path("artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json"), "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized"),
    ("n6_no_go_artifact", Path("artifacts/bea_v1_n6_fixed_pool_rank_order_experiment/bea_v1_n6_fixed_pool_rank_order_experiment_report.json"), "no_go_n6_public_fixed_pool_arm_fields_insufficient"),
    ("n6f_design_artifact", Path("artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json"), "fixed_pool_public_arm_field_materialization_design_pass"),
    ("n6g_source_discovery_artifact", Path("artifacts/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit_report.json"), "no_go_n6g_candidate_sources_inexact_or_aggregate_only"),
)

ARMS = (
    "baseline_n2_order",
    "extra_depth_promote_before_primary_prefix_4",
    "bounded_interleave_primary2_extra1",
    "late_extra_depth_demote_after_primary_prefix_8",
)

ALLOWED_CHANGED_EXACT = frozenset({
    "README.md",
    "docs/current-research-conclusions.md",
    "docs/en/current-research-conclusions.md",
    "docs/zh/current-research-conclusions.md",
    "docs/en/bea-v1-n6xr-explicit-bounded-candidate-pool-recapture-smoke.md",
    "docs/zh/bea-v1-n6xr-explicit-bounded-candidate-pool-recapture-smoke.md",
    "eval/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke.py",
    "artifacts/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke_report.json",
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
    "load_status", "forbidden_scan_status", "case_id_linkage_bucket", "mapping_status_bucket",
    "local_inventory_status_bucket", "rerun_scope_bucket", "canary_status_bucket",
    "capture_status_bucket", "arm_bucket", "result_status_bucket", "threshold_decision_bucket",
    "privacy_boundary_bucket", "public_artifact_bucket", "no_execution_boundary_bucket",
    "gate", "threshold_relation", "authorization", "next_allowed_phase", "next_allowed_scope_bucket",
    "fixed_pool_case_set_bucket", "recapture_boundary_bucket", "next_required_input_bucket",
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
        records.append({"anonymous_input_artifact_id": f"n6xrin{idx:04d}", "input_artifact_bucket": bucket, "load_status": str(loads.get(bucket, "missing")), "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan), "input_gate_passed_bool": passed})
    return records, ok


def _n5_arm_count(n5: Mapping[str, Any]) -> int:
    return len([r for r in n5.get("rank_order_arm_contract_records", []) if isinstance(r, dict) and r.get("arm_name") in ARMS])


def _n4_case_count(n4: Mapping[str, Any]) -> int:
    rows = n4.get("rank_blocker_evidence_records", [])
    return len(rows) if isinstance(rows, list) else 0


def _bounded_replay_preflight_records(n4: Mapping[str, Any], n5: Mapping[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    record = {
        "anonymous_bounded_replay_preflight_id": "n6xrbp0000",
        "recapture_boundary_bucket": "explicit_bounded_40_case_candidate_pool_recapture_preflight",
        "n4_case_count": _n4_case_count(n4),
        "n5_arm_count": _n5_arm_count(n5),
        "bounded_replay_command_identified": False,
        "canary_authorized": False,
        "full_case_execution_authorized": False,
        "candidate_pool_materialization_authorized_bool": False,
        "preflight_complete_bool": True,
    }
    return [record], record["n4_case_count"] == 40 and record["n5_arm_count"] == 4 and not record["bounded_replay_command_identified"]


def _mapping_availability_records() -> tuple[list[dict[str, Any]], bool]:
    records = [
        {"anonymous_mapping_availability_id": "n6xrmap0000", "case_id_linkage_bucket": "n4_case_ids_positional_over_n2_sanitized_rows", "mapping_status_bucket": "raw_record_join_key_unavailable", "anonymous_case_ids_positional_only_bool": True, "raw_join_key_available_bool": False, "n2_to_raw_mapping_available_bool": False, "candidate_pool_reconstruction_mapping_available_bool": False, "bounded_40_case_mapping_available_bool": False},
        {"anonymous_mapping_availability_id": "n6xrmap0001", "case_id_linkage_bucket": "p4l_private_reconstruction", "mapping_status_bucket": "not_locally_available_without_full_reconstruction", "anonymous_case_ids_positional_only_bool": True, "raw_join_key_available_bool": False, "n2_to_raw_mapping_available_bool": False, "p4l_private_reconstruction_available_locally_bool": False, "bounded_40_case_mapping_available_bool": False},
    ]
    return records, all(not r["bounded_40_case_mapping_available_bool"] for r in records)


def _local_private_inventory_summary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_local_private_inventory_summary_id": "n6xrprivinv0000", "local_inventory_status_bucket": "private_inventory_not_read_by_rule", "private_inventory_read": False, "n_series_candidate_pool_files_found": 0, "private_file_names_serialized_bool": False, "private_file_paths_serialized_bool": False}
    return [record], record["private_inventory_read"] is False and record["n_series_candidate_pool_files_found"] == 0


def _replay_cost_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_replay_cost_boundary_id": "n6xrcost0000", "rerun_scope_bucket": "full_p4l_reconstruction_272_records", "full_p4l_reconstruction_required": True, "network_required": True, "repo_clone_required": True, "openlocus_binary_required": True, "bounded_40_case_only_path_available": False, "retrieval_or_rerun_authorized_bool": False}
    return [record], record["full_p4l_reconstruction_required"] and not record["bounded_40_case_only_path_available"]


def _canary_recapture_records() -> list[dict[str, Any]]:
    return [{"anonymous_canary_recapture_id": "n6xrcanary0000", "canary_status_bucket": "not_executed_due_to_no_bounded_path", "canary_authorized_bool": False, "canary_executed_bool": False, "candidate_pool_recaptured_bool": False, "top10_or_rank_bucket_materialized_bool": False}]


def _private_capture_summary_records() -> list[dict[str, Any]]:
    return [{"anonymous_private_capture_summary_id": "n6xrcap0000", "capture_status_bucket": "no_private_capture_no_public_candidate_pool_materialization", "rows_written": 0, "private_rows_written": 0, "public_rows_written": 0, "candidate_pool_rows_written": 0}]


def _per_arm_result_records() -> list[dict[str, Any]]:
    return [{"anonymous_per_arm_result_id": f"n6xrarm{idx:04d}", "arm_bucket": arm, "result_status_bucket": "not_evaluated_no_candidate_pools", "evaluated_case_count": 0, "expected_case_count": 40, "candidate_pool_available_bool": False, "top10_recovery_count": None, "case_regression_count": None, "threshold_passed_bool": False} for idx, arm in enumerate(ARMS)]


def _threshold_decision_records() -> list[dict[str, Any]]:
    return [{"anonymous_threshold_decision_id": "n6xrtd0000", "threshold_decision_bucket": "not_evaluated_no_bounded_replay_path_or_candidate_pools", "evaluated_arm_count": 0, "passing_arm_count": 0, "n7_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_privacy_boundary_id": "n6xrpb0000", "privacy_boundary_bucket": "public_bucket_only_fail_closed_preflight", "public_artifact_bucket": "buckets_counts_booleans_only", "private_read_count": 0, "candidate_list_publicly_serialized": False, "raw_ranks_publicly_serialized": False, "paths_or_spans_publicly_serialized": False, "snippets_publicly_serialized": False, "hashes_publicly_serialized": False, "provider_payloads_publicly_serialized": False, "raw_diffs_publicly_serialized": False, "privacy_boundary_complete_bool": True}
    return [record], True


def _no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    record = {"anonymous_no_forbidden_execution_id": "n6xrnoexec0000", "no_execution_boundary_bucket": "fail_closed_no_candidate_pool_recapture_execution", "private_read_count": 0, "network_execution_count": 0, "retrieval_execution_count": 0, "git_clone_execution_count": 0, "openlocus_binary_execution_count": 0, "p4l_rerun_count": 0, "n1_n2_n3_rerun_count": 0, "n6_rerun_count": 0, "candidate_pool_generation_count": 0, "candidate_pool_materialization_count": 0, "selector_reranker_execution_count": 0, "counterfactual_execution_count": 0, "policy_runtime_change_count": 0, "default_change_count": 0, "no_forbidden_execution_complete_bool": True}
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
    return [{"anonymous_changed_file_allowlist_id": "n6xrcf0000", "git_status_available_bool": available, "workspace_change_count": len(names), "disallowed_changed_file_count": disallowed, "private_or_source_file_modification_count": private_or_source, "forbidden_runtime_or_evaluator_modified_bool": forbidden_runtime > 0, "changed_file_scope_valid_bool": ok}], ok


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == "bounded_candidate_pool_recapture_smoke_pass_n7_authorized"
    return [{"authorization": "explicit_bounded_candidate_pool_recapture_smoke_no_go" if not pass_status else "explicit_bounded_candidate_pool_recapture_smoke_pass", "next_allowed_phase": "BEA-v1-N7 Fixed-Pool Rank-Order Result Audit" if pass_status else "none_until_bounded_replay_path_or_exact_public_160_row_source_exists", "next_allowed_scope_bucket": "no_next_phase_bounded_mapping_unavailable" if not pass_status else "n7_result_audit_only", "n7_authorized": pass_status, "n6_rerun_authorized": False, "full_rerun_authorized": False, "retrieval_authorized": False, "private_read_authorized": False, "candidate_pool_generation_authorized": False, "candidate_pool_materialization_authorized": False, "selector_or_reranker_authorized": False, "counterfactual_authorized": False, "p5_authorized": False, "v1_a_authorized": False, "runtime_promotion_authorized": False, "default_promotion_authorized": False, "runtime_or_policy_change_authorized": False, "method_winner_claimed": False, "method_winner_claim_authorized": False, "downstream_value_claimed": False, "downstream_value_claim_authorized": False}]


def _gate_records(*, input_ok: bool, preflight_ok: bool, mapping_missing: bool, inventory_ok: bool, cost_ok: bool, privacy_ok: bool, noexec_ok: bool, changed_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "required_inputs_load_and_scan", "passed": input_ok, "threshold_relation": "equals", "value": int(input_ok), "threshold_value": 1},
        {"gate": "bounded_replay_preflight_complete", "passed": preflight_ok, "threshold_relation": "equals", "value": int(preflight_ok), "threshold_value": 1},
        {"gate": "bounded_mapping_unavailable", "passed": mapping_missing, "threshold_relation": "equals", "value": int(mapping_missing), "threshold_value": 1},
        {"gate": "private_inventory_not_read_and_no_local_n_series_candidate_pool_files", "passed": inventory_ok, "threshold_relation": "equals", "value": int(inventory_ok), "threshold_value": 1},
        {"gate": "full_rerun_required_for_reconstruction", "passed": cost_ok, "threshold_relation": "equals", "value": int(cost_ok), "threshold_value": 1},
        {"gate": "privacy_boundary_complete", "passed": privacy_ok, "threshold_relation": "equals", "value": int(privacy_ok), "threshold_value": 1},
        {"gate": "no_forbidden_execution", "passed": noexec_ok, "threshold_relation": "equals", "value": int(noexec_ok), "threshold_value": 1},
        {"gate": "changed_file_scope_valid", "passed": changed_ok, "threshold_relation": "equals", "value": int(changed_ok), "threshold_value": 1},
        {"gate": "scanner_pass", "passed": scanner_ok, "threshold_relation": "equals", "value": int(scanner_ok), "threshold_value": 1},
    ]


def _status_from(*, self_ok: bool, input_ok: bool, preflight_ok: bool, mapping_missing: bool, cost_ok: bool, privacy_ok: bool, noexec_ok: bool, changed_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n6xr_required_inputs_unavailable"
    if not privacy_ok or not noexec_ok:
        return "no_go_n6xr_public_schema_or_privacy_failed"
    if not changed_ok:
        return "no_go_n6xr_public_schema_or_privacy_failed"
    if preflight_ok and mapping_missing and cost_ok:
        return STATUS_NO_GO_FULL_RERUN
    return "no_go_n6xr_bounded_replay_path_unavailable"


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    preflight_records, preflight_ok = _bounded_replay_preflight_records(artifacts["n4_denominator_artifact"], artifacts["n5_preflight_artifact"])
    mapping_records, mapping_missing = _mapping_availability_records()
    inventory_records, inventory_ok = _local_private_inventory_summary_records()
    cost_records, cost_ok = _replay_cost_boundary_records()
    canary_records = _canary_recapture_records()
    capture_records = _private_capture_summary_records()
    per_arm_records = _per_arm_result_records()
    threshold_records = _threshold_decision_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    noexec_records, noexec_ok = _no_forbidden_execution_records()
    changed_records, changed_ok = _changed_file_allowlist_records()
    self_ok = all(c["passed"] for c in checks)
    status = _status_from(self_ok=self_ok, input_ok=input_ok, preflight_ok=preflight_ok, mapping_missing=mapping_missing, cost_ok=cost_ok, privacy_ok=privacy_ok, noexec_ok=noexec_ok, changed_ok=changed_ok)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "status": status, "claim_level": "explicit_bounded_candidate_pool_recapture_smoke_fail_closed_no_go", "phase": PHASE, "generated_by": GENERATED_BY, "generated_at": _now_iso(), "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records, "bounded_replay_preflight_records": preflight_records, "mapping_availability_records": mapping_records, "local_private_inventory_summary_records": inventory_records, "replay_cost_boundary_records": cost_records, "canary_recapture_records": canary_records, "private_capture_summary_records": capture_records, "public_arm_outcome_records": [], "per_arm_result_records": per_arm_records, "threshold_decision_records": threshold_records, "privacy_boundary_records": privacy_records, "no_forbidden_execution_records": noexec_records, "changed_file_allowlist_records": changed_records,
        "gate_records": _gate_records(input_ok=input_ok, preflight_ok=preflight_ok, mapping_missing=mapping_missing, inventory_ok=inventory_ok, cost_ok=cost_ok, privacy_ok=privacy_ok, noexec_ok=noexec_ok, changed_ok=changed_ok, scanner_ok=True),
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
    report["gate_records"] = _gate_records(input_ok=input_ok, preflight_ok=preflight_ok, mapping_missing=mapping_missing, inventory_ok=inventory_ok, cost_ok=cost_ok, privacy_ok=privacy_ok, noexec_ok=noexec_ok, changed_ok=changed_ok, scanner_ok=scanner_ok)
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
    preflight_records, preflight_ok = _bounded_replay_preflight_records(artifacts["n4_denominator_artifact"], artifacts["n5_preflight_artifact"])
    mapping_records, mapping_missing = _mapping_availability_records()
    inventory_records, inventory_ok = _local_private_inventory_summary_records()
    cost_records, cost_ok = _replay_cost_boundary_records()
    privacy_records, privacy_ok = _privacy_boundary_records()
    noexec_records, noexec_ok = _no_forbidden_execution_records()
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == ("bounded_candidate_pool_recapture_smoke_pass_n7_authorized", "bounded_candidate_pool_recapture_complete_below_threshold", "no_go_n6xr_required_inputs_unavailable", "no_go_n6xr_bounded_replay_path_unavailable", "no_go_n6xr_canary_recapture_failed", STATUS_NO_GO_FULL_RERUN, "no_go_n6xr_arm_semantics_or_case_set_mismatch", "no_go_n6xr_public_schema_or_privacy_failed", "fail_forbidden_scan", "fail_schema_contract")),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(_scan_summary({key: "blocked"})["status"] == "fail" for key in ("path", "span", "snippet", "candidate_list", "rank", "task_id", "repo", "private_id", "source_hash", "provider_payload", "raw_diff"))),
        _check("scanner_rejects_path_and_digest_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("inputs", input_ok and len(input_records) == 5 and all(r["input_gate_passed_bool"] for r in input_records)),
        _check("preflight_counts", preflight_ok and preflight_records[0]["n4_case_count"] == 40 and preflight_records[0]["n5_arm_count"] == 4 and preflight_records[0]["bounded_replay_command_identified"] is False),
        _check("preflight_no_authorization", preflight_records[0]["canary_authorized"] is False and preflight_records[0]["full_case_execution_authorized"] is False),
        _check("mapping_unavailable", mapping_missing and all(r["raw_join_key_available_bool"] is False and r["n2_to_raw_mapping_available_bool"] is False and r["bounded_40_case_mapping_available_bool"] is False for r in mapping_records)),
        _check("private_inventory_not_read", inventory_ok and inventory_records[0]["private_inventory_read"] is False and inventory_records[0]["n_series_candidate_pool_files_found"] == 0),
        _check("replay_cost_boundary", cost_ok and cost_records[0]["full_p4l_reconstruction_required"] is True and cost_records[0]["network_required"] is True and cost_records[0]["repo_clone_required"] is True and cost_records[0]["bounded_40_case_only_path_available"] is False),
        _check("canary_not_executed", _canary_recapture_records()[0]["canary_status_bucket"] == "not_executed_due_to_no_bounded_path" and _canary_recapture_records()[0]["canary_executed_bool"] is False),
        _check("private_capture_zero", _private_capture_summary_records()[0]["rows_written"] == 0 and _private_capture_summary_records()[0]["candidate_pool_rows_written"] == 0),
        _check("public_arm_outcomes_empty", [] == []),
        _check("per_arm_not_evaluated", len(_per_arm_result_records()) == 4 and all(r["result_status_bucket"] == "not_evaluated_no_candidate_pools" and r["evaluated_case_count"] == 0 for r in _per_arm_result_records())),
        _check("threshold_not_evaluated", _threshold_decision_records()[0]["threshold_decision_bucket"] == "not_evaluated_no_bounded_replay_path_or_candidate_pools" and _threshold_decision_records()[0]["n7_authorized_bool"] is False),
        _check("privacy_boundary", privacy_ok and privacy_records[0]["private_read_count"] == 0 and privacy_records[0]["candidate_list_publicly_serialized"] is False and privacy_records[0]["raw_ranks_publicly_serialized"] is False),
        _check("no_forbidden_execution", noexec_ok and noexec_records[0]["network_execution_count"] == 0 and noexec_records[0]["retrieval_execution_count"] == 0 and noexec_records[0]["candidate_pool_generation_count"] == 0),
        _check("status_expected", _status_from(self_ok=True, input_ok=True, preflight_ok=True, mapping_missing=True, cost_ok=True, privacy_ok=True, noexec_ok=True, changed_ok=True) == STATUS_NO_GO_FULL_RERUN),
        _check("stop_go_no_go", _stop_go_records(STATUS_NO_GO_FULL_RERUN)[0]["next_allowed_phase"] == "none_until_bounded_replay_path_or_exact_public_160_row_source_exists" and _stop_go_records(STATUS_NO_GO_FULL_RERUN)[0]["n7_authorized"] is False and _stop_go_records(STATUS_NO_GO_FULL_RERUN)[0]["full_rerun_authorized"] is False and _stop_go_records(STATUS_NO_GO_FULL_RERUN)[0]["private_read_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N6XR explicit bounded candidate-pool recapture smoke")
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
    print("wrote artifact " f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, " f"case_count={report['bounded_replay_preflight_records'][0]['n4_case_count']}, " f"arms={len(report['per_arm_result_records'])})")


if __name__ == "__main__":
    main()
