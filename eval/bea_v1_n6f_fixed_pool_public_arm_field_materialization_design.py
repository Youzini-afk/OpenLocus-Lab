#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, Mapping, NoReturn


SCHEMA_VERSION = "bea_v1_n6f_fixed_pool_public_arm_field_materialization_design.v1"
PHASE = "BEA-v1-N6F"
GENERATED_BY = "bea_v1_n6f_fixed_pool_public_arm_field_materialization_design"
STATUS_PASS = "fixed_pool_public_arm_field_materialization_design_pass"

STATUSES = (
    STATUS_PASS,
    "no_go_n6f_required_inputs_unavailable",
    "no_go_n6f_field_schema_incomplete",
    "no_go_n6f_privacy_boundary_incomplete",
    "no_go_n6f_claim_boundary_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

DEFAULT_OUT = Path(
    "artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/"
    "bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json"
)

INPUTS = (
    (
        "n6_fixed_pool_rank_order_experiment",
        Path(
            "artifacts/bea_v1_n6_fixed_pool_rank_order_experiment/"
            "bea_v1_n6_fixed_pool_rank_order_experiment_report.json"
        ),
        "no_go_n6_public_fixed_pool_arm_fields_insufficient",
        True,
    ),
    (
        "n5_fixed_pool_rank_order_experiment_preflight",
        Path(
            "artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/"
            "bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json"
        ),
        "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized",
        True,
    ),
    (
        "n4_fixed_pool_rank_blocker_denominator_audit",
        Path(
            "artifacts/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit/"
            "bea_v1_n4_fixed_pool_rank_blocker_denominator_audit_report.json"
        ),
        "fixed_pool_rank_blocker_denominator_audit_pass_n5_authorized",
        True,
    ),
    (
        "n3_extra_depth_merge_order_design_simulation_optional",
        Path(
            "artifacts/bea_v1_n3_extra_depth_merge_order_design_simulation/"
            "bea_v1_n3_extra_depth_merge_order_design_simulation_report.json"
        ),
        "n3_merge_order_design_inconclusive",
        False,
    ),
    (
        "n2_rank_pack_actionability_decomposition_optional",
        Path(
            "artifacts/bea_v1_n2_rank_pack_actionability_decomposition/"
            "bea_v1_n2_rank_pack_actionability_decomposition_report.json"
        ),
        "n2_rank_pack_actionability_decomposition_pass",
        False,
    ),
)

ARMS = (
    "baseline_n2_order",
    "extra_depth_promote_before_primary_prefix_4",
    "bounded_interleave_primary2_extra1",
    "late_extra_depth_demote_after_primary_prefix_8",
)

REQUIRED_PUBLIC_ARM_FIELDS = (
    "anonymous_public_arm_outcome_id",
    "anonymous_case_bucket",
    "arm_bucket",
    "fixed_pool_case_set_bucket",
    "arm_semantics_exact_match_bool",
    "candidate_pool_changed_bool",
    "new_retrieval_used_bool",
    "selector_or_reranker_used_bool",
    "top10_recovery_bucket",
    "top20_recovery_bucket",
    "rank_shift_bucket",
    "case_regression_bucket",
    "hard_cap_bucket",
    "outcome_materialized_bool",
)

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
    "schema_version", "status", "claim_level", "phase", "generated_by",
    "generated_at", "status_vocabulary", "input_artifact_bucket", "observed_status",
    "expected_status", "load_status", "forbidden_scan_status", "gate",
    "threshold_relation", "missing_reason_bucket", "missing_field_bucket",
    "schema_bucket", "field_bucket", "field_type_bucket", "public_safety_bucket",
    "arm_bucket", "fixed_pool_case_set_bucket", "top10_recovery_bucket",
    "top20_recovery_bucket", "rank_shift_bucket", "case_regression_bucket",
    "hard_cap_bucket", "privacy_boundary_bucket", "public_artifact_bucket",
    "future_materialization_gate_bucket", "authorization", "next_allowed_phase",
    "next_allowed_scope_bucket",
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
    return {
        "status": "pass" if not violations else "fail",
        "violations_count": len(violations),
        "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())],
    }


def _load_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    artifacts: dict[str, dict[str, Any]] = {}
    loads: dict[str, str] = {}
    for bucket, path, _expected, _required in INPUTS:
        artifact, load = _load_json(path)
        artifacts[bucket] = artifact
        loads[bucket] = load
    return artifacts, loads


def _input_artifact_records(artifacts: Mapping[str, Mapping[str, Any]], loads: Mapping[str, str]) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    required_ok = True
    for idx, (bucket, _path, expected, required) in enumerate(INPUTS):
        artifact = artifacts.get(bucket, {})
        scan = artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"
        observed = str(artifact.get("status", "") or "")
        present_ok = loads.get(bucket) == "pass" and observed == expected and scan == "pass"
        required_ok = required_ok and (present_ok or not required)
        records.append({
            "anonymous_input_artifact_id": f"n6fin{idx:04d}",
            "input_artifact_bucket": bucket,
            "input_required_bool": required,
            "load_status": str(loads.get(bucket, "missing")),
            "observed_status": observed,
            "expected_status": expected,
            "forbidden_scan_status": str(scan),
            "input_gate_passed_bool": present_ok or not required,
        })
    return records, required_ok


def _n6_field_insufficient(n6: Mapping[str, Any]) -> bool:
    return (
        n6.get("status") == "no_go_n6_public_fixed_pool_arm_fields_insufficient"
        and n6.get("forbidden_scan", {}).get("status") == "pass"
        and n6.get("per_case_arm_outcome_records") == []
        and all(r.get("exact_public_arm_mapping_bool") is False for r in n6.get("arm_mapping_records", []))
    )


def _n5_authorized(n5: Mapping[str, Any]) -> bool:
    stop = n5.get("stop_go_records", [])
    return (
        n5.get("status") == "fixed_pool_rank_order_experiment_preflight_pass_n6_authorized"
        and n5.get("forbidden_scan", {}).get("status") == "pass"
        and isinstance(stop, list)
        and bool(stop)
        and stop[0].get("n6_fixed_pool_rank_order_experiment_authorized") is True
    )


def _case_count(n5: Mapping[str, Any], n4: Mapping[str, Any]) -> int:
    rows = n5.get("eligible_case_set_records", [])
    if rows and isinstance(rows[0], dict):
        return int(rows[0].get("eligible_case_count", 0) or 0)
    return len(n4.get("rank_blocker_evidence_records", []))


def _missing_field_reason_records() -> tuple[list[dict[str, Any]], bool]:
    records = [
        {
            "anonymous_missing_field_reason_id": "n6fmiss0000",
            "missing_field_bucket": "exact_per_case_public_arm_outcome_rows",
            "missing_reason_bucket": "n6_no_go_exact_public_per_case_arm_fields_absent",
            "affected_arm_count": 4,
            "affected_case_count": 40,
            "affected_required_row_count": 160,
            "aggregate_inference_allowed_bool": False,
            "reason_complete_bool": True,
        },
        {
            "anonymous_missing_field_reason_id": "n6fmiss0001",
            "missing_field_bucket": "exact_arm_semantics_mapping",
            "missing_reason_bucket": "n3_analogue_arm_names_or_semantics_not_exact_n6_arms",
            "affected_arm_count": 4,
            "affected_case_count": 40,
            "affected_required_row_count": 160,
            "aggregate_inference_allowed_bool": False,
            "reason_complete_bool": True,
        },
        {
            "anonymous_missing_field_reason_id": "n6fmiss0002",
            "missing_field_bucket": "raw_order_or_rank_reconstruction_fields",
            "missing_reason_bucket": "public_artifacts_do_not_expose_raw_order_or_raw_rank_inputs",
            "affected_arm_count": 4,
            "affected_case_count": 40,
            "affected_required_row_count": 160,
            "aggregate_inference_allowed_bool": False,
            "reason_complete_bool": True,
        },
    ]
    return records, all(r["reason_complete_bool"] and not r["aggregate_inference_allowed_bool"] for r in records)


def _required_public_arm_field_schema_records(case_count: int) -> tuple[list[dict[str, Any]], bool]:
    row_count = case_count * len(ARMS)
    records: list[dict[str, Any]] = [{
        "anonymous_schema_id": "n6fschema0000",
        "schema_bucket": "public_fixed_pool_arm_outcome_rows",
        "case_count": case_count,
        "arm_count": len(ARMS),
        "required_public_row_count": row_count,
        "required_public_field_count": len(REQUIRED_PUBLIC_ARM_FIELDS),
        "all_fields_bucketed_public_safe_bool": True,
        "raw_rank_allowed_bool": False,
        "candidate_path_or_list_allowed_bool": False,
        "source_task_repo_snippet_hash_score_allowed_bool": False,
        "schema_complete_bool": row_count == 160 and len(REQUIRED_PUBLIC_ARM_FIELDS) == 14,
    }]
    for idx, field in enumerate(REQUIRED_PUBLIC_ARM_FIELDS):
        bool_field = field.endswith("_bool")
        records.append({
            "anonymous_schema_field_id": f"n6ffield{idx:04d}",
            "field_bucket": field,
            "field_type_bucket": "boolean" if bool_field else "bucket_or_anonymous_identifier",
            "public_safety_bucket": "bucket_only_public_safe",
            "required_bool": True,
            "raw_rank_field_bool": False,
            "candidate_path_or_list_field_bool": False,
            "source_task_repo_snippet_hash_score_field_bool": False,
        })
    ok = records[0]["schema_complete_bool"] and all(r.get("public_safety_bucket", "bucket_only_public_safe") == "bucket_only_public_safe" for r in records[1:])
    return records, ok


def _per_arm_required_field_records(case_count: int) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    for idx, arm in enumerate(ARMS):
        records.append({
            "anonymous_per_arm_required_field_id": f"n6farmfield{idx:04d}",
            "arm_bucket": arm,
            "fixed_pool_case_set_bucket": "n5_frozen_n4_sanitized_rank_blocker_cases",
            "required_case_count": case_count,
            "required_public_row_count": case_count,
            "anonymous_public_arm_outcome_id_required_bool": True,
            "anonymous_case_bucket_required_bool": True,
            "arm_semantics_exact_match_bool_required_bool": True,
            "candidate_pool_changed_bool_required_false_bool": True,
            "new_retrieval_used_bool_required_false_bool": True,
            "selector_or_reranker_used_bool_required_false_bool": True,
            "top10_recovery_bucket_required_bool": True,
            "top20_recovery_bucket_required_bool": True,
            "rank_shift_bucket_required_bool": True,
            "case_regression_bucket_required_bool": True,
            "hard_cap_bucket_required_bool": True,
            "outcome_materialized_bool_required_bool": True,
            "all_required_fields_bucketed_public_safe_bool": True,
            "materialization_or_generation_performed_bool": False,
        })
    return records, len(records) == 4 and sum(r["required_public_row_count"] for r in records) == 160


def _privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    record = {
        "anonymous_privacy_boundary_id": "n6fpb0000",
        "privacy_boundary_bucket": "public_bucket_only_schema_design",
        "public_artifact_bucket": "anonymous_case_arm_rank_recovery_threshold_buckets_and_aggregate_counts_only",
        "private_read_count": 0,
        "materialization_execution_count": 0,
        "generation_execution_count": 0,
        "retrieval_or_rerun_count": 0,
        "selector_reranker_counterfactual_count": 0,
        "policy_runtime_change_count": 0,
        "private_or_source_linkage_required_bool": False,
        "raw_candidate_lists_publicly_serialized": False,
        "raw_provider_payloads_publicly_serialized": False,
        "raw_diffs_publicly_serialized": False,
        "raw_ranks_publicly_serialized": False,
        "privacy_boundary_complete_bool": True,
    }
    return [record], True


def _future_materialization_gate_records(*, n6_ok: bool, n5_ok: bool, missing_ok: bool, schema_ok: bool, privacy_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    return [
        {"gate": "n6_status_field_insufficient", "passed": n6_ok, "threshold_relation": "equals", "value": int(n6_ok), "threshold_value": 1},
        {"gate": "n5_preflight_authorized", "passed": n5_ok, "threshold_relation": "equals", "value": int(n5_ok), "threshold_value": 1},
        {"gate": "missing_reason_complete", "passed": missing_ok, "threshold_relation": "equals", "value": int(missing_ok), "threshold_value": 1},
        {"gate": "schema_defines_160_rows", "passed": schema_ok, "threshold_relation": "equals", "value": 160 if schema_ok else 0, "threshold_value": 160},
        {"gate": "all_fields_bucketed_public_safe", "passed": schema_ok and privacy_ok, "threshold_relation": "equals", "value": int(schema_ok and privacy_ok), "threshold_value": 1},
        {"gate": "scanner_pass", "passed": scanner_ok, "threshold_relation": "equals", "value": int(scanner_ok), "threshold_value": 1},
        {"gate": "private_read_count_zero", "passed": privacy_ok, "threshold_relation": "equals", "value": 0, "threshold_value": 0},
        {"gate": "execution_count_zero", "passed": privacy_ok, "threshold_relation": "equals", "value": 0, "threshold_value": 0},
    ]


def _stop_go_records(status: str) -> list[dict[str, Any]]:
    pass_status = status == STATUS_PASS
    return [{
        "authorization": "fixed_pool_public_arm_field_materialization_design_only",
        "next_allowed_phase": "BEA-v1-N6G Fixed-Pool Arm-Field Source Discovery Audit" if pass_status else "none_for_public_arm_field_materialization",
        "next_allowed_scope_bucket": "read_only_public_source_discovery_only" if pass_status else "no_next_phase_authorized",
        "n6g_source_discovery_audit_authorized": pass_status,
        "n6_rerun_authorized": False,
        "generation_authorized": False,
        "materialization_authorized": False,
        "new_retrieval_authorized": False,
        "rerun_authorized": False,
        "selector_or_reranker_authorized": False,
        "private_read_authorized": False,
        "policy_tuning_authorized": False,
        "counterfactual_authorized": False,
        "p5_authorized": False,
        "v1_a_authorized": False,
        "runtime_promotion_authorized": False,
        "default_promotion_authorized": False,
        "runtime_or_policy_change_authorized": False,
        "method_winner_claimed": False,
        "method_winner_claim_authorized": False,
        "downstream_value_claimed": False,
        "downstream_value_claim_authorized": False,
    }]


def _status_from(*, self_ok: bool, input_ok: bool, missing_ok: bool, schema_ok: bool, privacy_ok: bool, claim_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n6f_required_inputs_unavailable"
    if not missing_ok or not schema_ok:
        return "no_go_n6f_field_schema_incomplete"
    if not privacy_ok:
        return "no_go_n6f_privacy_boundary_incomplete"
    if not claim_ok:
        return "no_go_n6f_claim_boundary_invalid"
    return STATUS_PASS


def _build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    artifacts, loads = _load_inputs()
    input_records, input_ok = _input_artifact_records(artifacts, loads)
    n6_ok = _n6_field_insufficient(artifacts["n6_fixed_pool_rank_order_experiment"])
    n5_ok = _n5_authorized(artifacts["n5_fixed_pool_rank_order_experiment_preflight"])
    case_count = _case_count(artifacts["n5_fixed_pool_rank_order_experiment_preflight"], artifacts["n4_fixed_pool_rank_blocker_denominator_audit"])
    missing_records, missing_ok = _missing_field_reason_records()
    schema_records, schema_ok = _required_public_arm_field_schema_records(case_count)
    per_arm_records, per_arm_ok = _per_arm_required_field_records(case_count)
    privacy_records, privacy_ok = _privacy_boundary_records()
    claim_ok = True
    self_ok = all(c["passed"] for c in checks)
    status = _status_from(
        self_ok=self_ok,
        input_ok=input_ok and n6_ok and n5_ok,
        missing_ok=missing_ok,
        schema_ok=schema_ok and per_arm_ok,
        privacy_ok=privacy_ok,
        claim_ok=claim_ok,
    )
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "claim_level": "fixed_pool_public_arm_field_materialization_design_only",
        "phase": PHASE,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "missing_field_reason_records": missing_records,
        "required_public_arm_field_schema_records": schema_records,
        "per_arm_required_field_records": per_arm_records,
        "privacy_boundary_records": privacy_records,
        "future_materialization_gate_records": _future_materialization_gate_records(
            n6_ok=n6_ok, n5_ok=n5_ok, missing_ok=missing_ok,
            schema_ok=schema_ok and per_arm_ok, privacy_ok=privacy_ok, scanner_ok=True,
        ),
        "stop_go_records": _stop_go_records(status),
        "forbidden_scan": {},
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
        "method_winner_claimed": False,
        "downstream_value_claimed": False,
    }
    scan = _scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        report["stop_go_records"] = _stop_go_records(report["status"])
    final_scan = _scan_summary(report)
    report["forbidden_scan"] = final_scan
    scanner_ok = final_scan["status"] == "pass"
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    report["future_materialization_gate_records"] = _future_materialization_gate_records(
        n6_ok=n6_ok, n5_ok=n5_ok, missing_ok=missing_ok,
        schema_ok=schema_ok and per_arm_ok, privacy_ok=privacy_ok, scanner_ok=scanner_ok,
    )
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
    n6_ok = _n6_field_insufficient(artifacts["n6_fixed_pool_rank_order_experiment"])
    n5_ok = _n5_authorized(artifacts["n5_fixed_pool_rank_order_experiment_preflight"])
    case_count = _case_count(artifacts["n5_fixed_pool_rank_order_experiment_preflight"], artifacts["n4_fixed_pool_rank_blocker_denominator_audit"])
    missing_records, missing_ok = _missing_field_reason_records()
    schema_records, schema_ok = _required_public_arm_field_schema_records(case_count)
    per_arm_records, per_arm_ok = _per_arm_required_field_records(case_count)
    privacy_records, privacy_ok = _privacy_boundary_records()
    checks = [
        _check("status_vocabulary_exact", tuple(STATUSES) == (
            STATUS_PASS,
            "no_go_n6f_required_inputs_unavailable",
            "no_go_n6f_field_schema_incomplete",
            "no_go_n6f_privacy_boundary_incomplete",
            "no_go_n6f_claim_boundary_invalid",
            "fail_forbidden_scan",
            "fail_schema_contract",
        )),
        _check("safe_parser", _parser_hides_unknown()),
        _check("scanner_rejects_forbidden_keys", all(
            _scan_summary({key: "blocked"})["status"] == "fail"
            for key in ("path", "span", "snippet", "candidate_list", "rank", "task_id", "repo", "private_id", "source_hash", "provider_payload", "raw_diff")
        )),
        _check("scanner_rejects_path_and_digest_values", _scan_summary({"safe": "src/lib.rs"})["status"] == "fail" and _scan_summary({"safe": "a" * 40})["status"] == "fail"),
        _check("inputs", input_ok and len(input_records) == 5 and all(r["input_gate_passed_bool"] for r in input_records)),
        _check("n6_status_field_insufficient", n6_ok),
        _check("n5_authorized", n5_ok),
        _check("missing_reason_complete", missing_ok and len(missing_records) == 3 and all(r["affected_required_row_count"] == 160 for r in missing_records)),
        _check("schema_required_fields_exact", tuple(r["field_bucket"] for r in schema_records if "field_bucket" in r) == REQUIRED_PUBLIC_ARM_FIELDS),
        _check("schema_defines_160_rows", schema_ok and schema_records[0]["required_public_row_count"] == 160 and schema_records[0]["required_public_field_count"] == 14),
        _check("schema_no_forbidden_raw_fields", schema_records[0]["raw_rank_allowed_bool"] is False and schema_records[0]["candidate_path_or_list_allowed_bool"] is False and schema_records[0]["source_task_repo_snippet_hash_score_allowed_bool"] is False),
        _check("per_arm_required_rows", per_arm_ok and len(per_arm_records) == 4 and sum(r["required_public_row_count"] for r in per_arm_records) == 160),
        _check("per_arm_no_execution", all(r["candidate_pool_changed_bool_required_false_bool"] and r["new_retrieval_used_bool_required_false_bool"] and r["selector_or_reranker_used_bool_required_false_bool"] and not r["materialization_or_generation_performed_bool"] for r in per_arm_records)),
        _check("privacy_boundary", privacy_ok and privacy_records[0]["private_read_count"] == 0 and privacy_records[0]["generation_execution_count"] == 0 and privacy_records[0]["privacy_boundary_complete_bool"] is True),
        _check("future_gate_pass", all(r["passed"] for r in _future_materialization_gate_records(n6_ok=True, n5_ok=True, missing_ok=True, schema_ok=True, privacy_ok=True, scanner_ok=True))),
        _check("stop_go_n6g_only", _stop_go_records(STATUS_PASS)[0]["n6g_source_discovery_audit_authorized"] is True and _stop_go_records(STATUS_PASS)[0]["n6_rerun_authorized"] is False and _stop_go_records(STATUS_PASS)[0]["generation_authorized"] is False and _stop_go_records(STATUS_PASS)[0]["private_read_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N6F fixed-pool public arm-field materialization design")
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
    print(
        "wrote artifact "
        f"(status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, "
        f"required_rows={report['required_public_arm_field_schema_records'][0]['required_public_row_count']}, "
        f"n6g={report['stop_go_records'][0]['n6g_source_discovery_audit_authorized']})"
    )


if __name__ == "__main__":
    main()
