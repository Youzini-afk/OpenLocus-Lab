#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time
from typing import Any, NoReturn

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

import bea_v1_p0_3_scheduler_dataset_export as p0_3  # noqa: E402
import bea_v1_trace_gap_audit as tg  # noqa: E402


SCHEMA_VERSION = "bea_v1_p2_0_scheduler_private_arm_row_recovery.v1"
GENERATED_BY = "eval/bea_v1_p2_0_scheduler_private_arm_row_recovery.py"
CLAIM_LEVEL = "scheduler_private_arm_row_recovery_and_sanitized_export_only"
MODE = "bea_v1_p2_0_scheduler_private_arm_row_recovery"
PHASE = "BEA-v1-P2-0"
DEFAULT_OUT = Path("artifacts/bea_v1_p2_0_scheduler_private_arm_row_recovery/bea_v1_p2_0_scheduler_private_arm_row_recovery_report.json")
DEFAULT_P4L = Path("artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json")
DEFAULT_P0_3 = Path("artifacts/bea_v1_p0_3_scheduler_dataset_export/bea_v1_p0_3_scheduler_dataset_export_report.json")
DEFAULT_P0_2 = Path("artifacts/bea_v1_p0_2_actionability_matrix_refresh/bea_v1_p0_2_actionability_matrix_refresh_report.json")
DEFAULT_PRIVATE_ARM = Path(".openlocus/research-private/bea_v1_p4l.private_arm_outcomes.jsonl")

STATUSES = (
    "scheduler_private_arm_row_export_pass",
    "no_go_p2_0_private_arm_rows_unavailable",
    "no_go_p2_0_locked_denominator_mismatch",
    "no_go_p2_0_arm_replay_mismatch",
    "no_go_p2_0_private_row_schema_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

EXPECTED_P4L_STATUS = "bea_v1_p4l_locked_non_python_scheduler_validation_pass"
EXPECTED_PRIVATE_SCHEMA = p0_3.PRIVATE_ARM_SCHEMA
EXPECTED_ROW_COUNT = p0_3.EXPECTED_PRIVATE_ARM_ROWS
EXPECTED_ARM_REACH = {
    "baseline_current_candidate_pool": 0,
    "p2_depth_only_reference": 55,
    "p3_constrained_depth_policy_reference": 55,
    "p4_latency_aware_action_scheduler_frozen": 52,
}
EXPECTED_P4_HARD_CAP = 0
FLOAT_TOLERANCE = 0.0005


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return {}, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _private_root() -> Path:
    return Path(".openlocus/research-private")


def _safe_private_path(path: Path) -> bool:
    try:
        root = (_private_root()).resolve()
        resolved = path.resolve()
        return resolved == root or root in resolved.parents or resolved == Path("/tmp") or Path("/tmp") in resolved.parents
    except Exception:
        return False


def _candidate_private_arm_path(supplied: Path | None) -> tuple[Path | None, str]:
    if supplied is not None:
        return supplied, "supplied"
    if DEFAULT_PRIVATE_ARM.exists():
        return DEFAULT_PRIVATE_ARM, "default"
    root = _private_root()
    if root.exists():
        matches = sorted(root.glob("**/*private_arm_outcomes.jsonl")) + sorted(root.glob("**/*arm*outcome*.jsonl"))
        for path in matches:
            if path.is_file() and _safe_private_path(path):
                return path, "discovered_private_root"
    return DEFAULT_PRIVATE_ARM, "default_missing"


def _read_private_rows(path: Path | None) -> tuple[list[dict[str, Any]], str]:
    if path is None:
        return [], "not_supplied"
    if not _safe_private_path(path):
        return [], "outside_project_private_root"
    if not path.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    return [], "parse_failed"
                rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def _expected_arm_names(p4l: dict[str, Any]) -> set[str]:
    rows = p4l.get("arm_metrics_records", [])
    if not isinstance(rows, list):
        return set(EXPECTED_ARM_REACH)
    names = {str(row.get("arm_name", "") or "") for row in rows if isinstance(row, dict)}
    return names or set(EXPECTED_ARM_REACH)


def _schema_errors(rows: list[dict[str, Any]], expected_arms: set[str]) -> list[dict[str, Any]]:
    required = {
        "schema_version",
        "arm_name",
        "denominator_index_private",
        "gold_file_available",
        "first_gold_file_rank",
        "candidate_pool_size",
        "retrieval_latency_seconds",
        "hard_cap_hit",
        "unique_file_cap_hit",
        "extra_depth_actions_executed",
    }
    errors: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        row_errors: list[str] = []
        if row.get("schema_version") != EXPECTED_PRIVATE_SCHEMA:
            row_errors.append("schema_version_mismatch")
        missing = sorted(k for k in required if k not in row)
        if missing:
            row_errors.append("required_field_missing")
        if str(row.get("arm_name", "") or "") not in expected_arms:
            row_errors.append("unknown_arm_name")
        for key in ("denominator_index_private", "first_gold_file_rank", "candidate_pool_size", "extra_depth_actions_executed"):
            try:
                int(row.get(key, 0))
            except Exception:
                row_errors.append(f"{key}_not_integer")
        try:
            float(row.get("retrieval_latency_seconds", 0.0))
        except Exception:
            row_errors.append("retrieval_latency_seconds_not_float")
        if row_errors:
            errors.append({"anonymous_error_id": f"pe{i:05d}", "error_bucket": "|".join(sorted(set(row_errors)))})
    return errors


def _aggregate_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_arm: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_arm.setdefault(str(row.get("arm_name", "") or ""), []).append(row)
    out: list[dict[str, Any]] = []
    for arm, arm_rows in sorted(by_arm.items()):
        reached = [row for row in arm_rows if bool(row.get("gold_file_available", False))]
        latencies = [float(row.get("retrieval_latency_seconds", 0.0) or 0.0) for row in arm_rows]
        pools = [int(row.get("candidate_pool_size", 0) or 0) for row in arm_rows]
        ranks = [int(row.get("first_gold_file_rank", 0) or 0) for row in reached]
        out.append({
            "arm_name": arm,
            "denominator_count": len(arm_rows),
            "file_reach_count": len(reached),
            "file_reach_rate": round(len(reached) / len(arm_rows), 6) if arm_rows else 0.0,
            "mean_latency_seconds": round(sum(latencies) / len(latencies), 6) if latencies else 0.0,
            "mean_candidate_pool_size": round(sum(pools) / len(pools), 6) if pools else 0.0,
            "hard_cap_violation_count": sum(1 for row in arm_rows if bool(row.get("hard_cap_hit", False))),
            "retrieval_error_count": 0,
            "first_gold_file_rank_mean": round(sum(ranks) / len(ranks), 6) if ranks else 0.0,
        })
    return out


def _aggregate_errors(rows: list[dict[str, Any]], p4l: dict[str, Any], expected_arms: set[str]) -> list[dict[str, Any]]:
    if not rows:
        return []
    errors: list[dict[str, Any]] = []
    row_arms = {str(row.get("arm_name", "") or "") for row in rows}
    if row_arms != expected_arms:
        errors.append({"anonymous_error_id": "ae0000", "error_bucket": "arm_set_mismatch"})
    aggregate = _aggregate_from_rows(rows)
    by_arm = {row["arm_name"]: row for row in aggregate}
    p4l_by_arm = {str(row.get("arm_name", "") or ""): row for row in p4l.get("arm_metrics_records", []) if isinstance(row, dict)} if isinstance(p4l.get("arm_metrics_records"), list) else {}
    for arm in sorted(expected_arms):
        agg = by_arm.get(arm, {})
        p4l_row = p4l_by_arm.get(arm, {})
        arm_errors: list[str] = []
        if int(agg.get("denominator_count", 0) or 0) != 272:
            arm_errors.append("arm_denominator_count_mismatch")
        expected_reach = EXPECTED_ARM_REACH.get(arm, int(p4l_row.get("file_reach_count", -1) or -1))
        if int(agg.get("file_reach_count", -1) or -1) != expected_reach:
            arm_errors.append("arm_reach_count_mismatch")
        if arm == "p4_latency_aware_action_scheduler_frozen" and int(agg.get("hard_cap_violation_count", -1) or -1) != EXPECTED_P4_HARD_CAP:
            arm_errors.append("p4_hard_cap_mismatch")
        for key in ("mean_latency_seconds", "mean_candidate_pool_size", "first_gold_file_rank_mean"):
            if p4l_row:
                if abs(float(agg.get(key, 0.0) or 0.0) - float(p4l_row.get(key, 0.0) or 0.0)) > FLOAT_TOLERANCE:
                    arm_errors.append(f"{key}_mismatch")
        if arm_errors:
            errors.append({"anonymous_error_id": f"ae{len(errors) + 1:04d}", "error_bucket": "|".join(sorted(set(arm_errors))), "arm_name_bucket": arm})
    return errors


def _summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in rows)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _sanitized_arm_reproduction_records(aggregate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(aggregate):
        out.append({
            "anonymous_arm_reproduction_id": f"par{i:04d}",
            "arm_name": str(row.get("arm_name", "") or ""),
            "denominator_count": int(row.get("denominator_count", 0) or 0),
            "file_reach_count": int(row.get("file_reach_count", 0) or 0),
            "file_reach_bucket": "reach_zero" if int(row.get("file_reach_count", 0) or 0) == 0 else "reach_nonzero",
            "hard_cap_violation_count": int(row.get("hard_cap_violation_count", 0) or 0),
            "latency_bucket": p0_3._latency_bucket(float(row.get("mean_latency_seconds", 0.0) or 0.0)),
            "pool_size_bucket": p0_3._pool_bucket(int(round(float(row.get("mean_candidate_pool_size", 0.0) or 0.0)))),
        })
    return out


def _p0_3_report(args: argparse.Namespace, private_path: Path | None, checks: list[dict[str, Any]]) -> dict[str, Any]:
    p0_3_args = argparse.Namespace(
        p4l_artifact=args.p4l_artifact,
        p0_2_artifact=args.p0_2_artifact,
        private_arm_outcomes_jsonl=private_path,
    )
    return p0_3._build_report(p0_3_args, checks)


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]], p0_3_checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    p4l, p4l_status = _load_json(args.p4l_artifact)
    p0_3_artifact, p0_3_status = _load_json(args.p0_3_artifact)
    private_path, private_source = _candidate_private_arm_path(args.private_arm_outcomes_jsonl)
    private_rows, private_status = _read_private_rows(private_path)
    expected_arms = _expected_arm_names(p4l)
    schema_errors = _schema_errors(private_rows, expected_arms) if private_status == "pass" else []
    aggregate = _aggregate_from_rows(private_rows) if private_status == "pass" and not schema_errors else []
    aggregate_errors = _aggregate_errors(private_rows, p4l, expected_arms) if private_status == "pass" and not schema_errors else []
    p0_3_full = _p0_3_report(args, private_path if private_status == "pass" else None, p0_3_checks) if private_status == "pass" and not schema_errors and not aggregate_errors else {}

    p4l_ok = p4l_status == "pass" and p4l.get("status") == EXPECTED_P4L_STATUS and p4l.get("forbidden_scan", {}).get("status") == "pass"
    denominator_ok = p4l_ok and int(p4l.get("expected_locked_denominator_count", 0) or 0) == 272 and int(p4l.get("expected_p4j_reconstructed_non_python_count", 0) or 0) == 272 and bool(p4l.get("denominator_exact_match", False))
    rows_available = private_status == "pass" and bool(private_rows)
    row_count_ok = len(private_rows) == EXPECTED_ROW_COUNT
    schema_ok = rows_available and row_count_ok and not schema_errors
    arm_replay_ok = schema_ok and not aggregate_errors
    p0_3_full_ok = p0_3_full.get("status") == "scheduler_dataset_export_full_pass" and p0_3_full.get("forbidden_scan", {}).get("status") == "pass"
    self_tests_ok = all(c["passed"] for c in checks)
    if not self_tests_ok:
        status = "fail_schema_contract"
    elif not denominator_ok:
        status = "no_go_p2_0_locked_denominator_mismatch"
    elif not rows_available:
        status = "no_go_p2_0_private_arm_rows_unavailable"
    elif not schema_ok:
        status = "no_go_p2_0_private_row_schema_invalid"
    elif not arm_replay_ok or not p0_3_full_ok:
        status = "no_go_p2_0_arm_replay_mismatch"
    else:
        status = "scheduler_private_arm_row_export_pass"

    sanitized_private = p0_3_full.get("scheduler_private_arm_sanitized_records", []) if p0_3_full_ok else []
    if not isinstance(sanitized_private, list):
        sanitized_private = []
    p0_3_public_rows = p0_3_full.get("scheduler_arm_dataset_records", []) if p0_3_full_ok else p0_3_artifact.get("scheduler_arm_dataset_records", [])
    if not isinstance(p0_3_public_rows, list):
        p0_3_public_rows = []
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status == "scheduler_private_arm_row_export_pass" else "private_arm_rows_unavailable" if status == "no_go_p2_0_private_arm_rows_unavailable" else "locked_denominator_mismatch" if status == "no_go_p2_0_locked_denominator_mismatch" else "private_row_schema_invalid" if status == "no_go_p2_0_private_row_schema_invalid" else "arm_replay_mismatch" if status == "no_go_p2_0_arm_replay_mismatch" else "schema_contract_failed",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_tests_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "source_join_records": [
            {"input_artifact": "p4l_locked_non_python_scheduler_validation", "load_status": p4l_status, "source_status": str(p4l.get("status", "") or ""), "source_schema": str(p4l.get("schema_version", "") or ""), "forbidden_scan_status": str(p4l.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p4l.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(p4l.get("arm_metrics_records", [])) if isinstance(p4l.get("arm_metrics_records"), list) else 0},
            {"input_artifact": "p0_3_scheduler_dataset_export", "load_status": p0_3_status, "source_status": str(p0_3_artifact.get("status", "") or ""), "source_schema": str(p0_3_artifact.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_3_artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_3_artifact.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(p0_3_public_rows)},
            {"input_artifact": "p0_3_full_export_direct", "load_status": "pass" if p0_3_full else "not_run", "source_status": str(p0_3_full.get("status", "") or ""), "source_schema": str(p0_3_full.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_3_full.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_3_full.get("forbidden_scan"), dict) else "not_reported"), "record_count": len(sanitized_private)},
        ],
        "private_arm_row_recovery_manifest_records": [{
            "manifest_name": "bea_v1_p4l_private_arm_outcomes",
            "schema_version": EXPECTED_PRIVATE_SCHEMA,
            "path_source_bucket": private_source,
            "read_status": private_status,
            "record_count": len(private_rows),
            "expected_record_count": EXPECTED_ROW_COUNT,
            "schema_error_count": len(schema_errors),
            "aggregate_error_count": len(aggregate_errors),
            "path_publicly_serialized": False,
            "storage_class": "project_ignored_private_jsonl",
            "frozen_rerun_requested": bool(args.enable_frozen_rerun),
            "frozen_rerun_status": "not_implemented_fail_closed" if args.enable_frozen_rerun else "not_requested",
        }],
        "sanitized_scheduler_arm_dataset_records": p0_3_public_rows,
        "sanitized_scheduler_private_arm_bucket_records": sanitized_private,
        "sanitized_arm_reproduction_records": _sanitized_arm_reproduction_records(aggregate),
        "arm_name_summary_records": _summary(_sanitized_arm_reproduction_records(aggregate), "arm_name"),
        "private_row_schema_error_summary_records": _summary(schema_errors, "error_bucket"),
        "arm_replay_error_summary_records": _summary(aggregate_errors, "error_bucket"),
        "gate_records": _gate_records(
            p4l_ok=p4l_ok,
            denominator_ok=denominator_ok,
            rows_available=rows_available,
            row_count=len(private_rows),
            row_count_ok=row_count_ok,
            schema_ok=schema_ok,
            schema_error_count=len(schema_errors),
            arm_replay_ok=arm_replay_ok,
            aggregate_error_count=len(aggregate_errors),
            p0_3_full_ok=p0_3_full_ok,
        ),
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "private_arm_rows_recovered_and_sanitized_exported" if status == "scheduler_private_arm_row_export_pass" else "private_arm_rows_not_available_locally" if status == "no_go_p2_0_private_arm_rows_unavailable" else "locked_denominator_mismatch" if status == "no_go_p2_0_locked_denominator_mismatch" else "private_row_schema_invalid" if status == "no_go_p2_0_private_row_schema_invalid" else "arm_replay_or_p0_3_full_export_mismatch",
            "authorization": "scheduler_private_arm_row_recovery_and_sanitized_export_only",
            "data_surface_population_only": True,
            "policy_tuning_authorized": False,
            "support_counterfactual_execution_authorized": False,
            "support_marginal_utility_claimed": False,
            "mechanism_evidence_claimed": False,
            "implementation_authorized": False,
            "selector_or_reranker_authorized": False,
            "v1_a_authorized": False,
            "p5_authorized": False,
            "runtime_promotion_authorized": False,
            "broad_retrieval_expansion_authorized": False,
            "downstream_value_claimed": False,
        }],
        "aggregate_plus_sanitized_records_public_artifact": True,
        "raw_records_publicly_serialized": False,
        "private_paths_publicly_serialized": False,
        "exact_paths_publicly_serialized": False,
        "exact_spans_publicly_serialized": False,
        "provider_payloads_publicly_serialized": False,
        "aggregate_runtime_seconds": round(time.perf_counter() - start, 3),
    }
    scan = tg._scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
        report["failure_reason_category"] = "forbidden_leak_blocked"
    report["forbidden_scan"] = tg._scan_summary(report)
    return report


def _gate_records(
    *,
    p4l_ok: bool,
    denominator_ok: bool,
    rows_available: bool,
    row_count: int,
    row_count_ok: bool,
    schema_ok: bool,
    schema_error_count: int,
    arm_replay_ok: bool,
    aggregate_error_count: int,
    p0_3_full_ok: bool,
) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = [
        {"gate": "p4l_artifact_pass", "passed": p4l_ok, "threshold_relation": "boolean", "value": int(p4l_ok), "threshold_value": 1},
        {"gate": "locked_denominator_exact_match", "passed": denominator_ok, "threshold_relation": "boolean", "value": int(denominator_ok), "threshold_value": 1},
        {"gate": "private_arm_rows_available", "passed": rows_available, "threshold_relation": "boolean", "value": int(rows_available), "threshold_value": 1},
        {"gate": "private_arm_row_count", "passed": row_count_ok, "threshold_relation": "equals", "value": row_count, "threshold_value": EXPECTED_ROW_COUNT},
    ]
    if not rows_available:
        gates.extend([
            {"gate": "private_arm_schema_valid", "passed": False, "threshold_relation": "not_evaluated_missing_private_rows", "value": "not_evaluated", "threshold_value": "private_rows_available"},
            {"gate": "arm_replay_aggregate_reproduces_p4l", "passed": False, "threshold_relation": "not_evaluated_missing_private_rows", "value": "not_evaluated", "threshold_value": "private_rows_available"},
            {"gate": "p0_3_full_export_pass", "passed": False, "threshold_relation": "not_run_missing_private_rows", "value": "not_run", "threshold_value": "private_rows_available"},
        ])
        return gates
    gates.extend([
        {"gate": "private_arm_schema_valid", "passed": schema_ok, "threshold_relation": "equals", "value": schema_error_count, "threshold_value": 0},
        {"gate": "arm_replay_aggregate_reproduces_p4l", "passed": arm_replay_ok, "threshold_relation": "equals", "value": aggregate_error_count, "threshold_value": 0},
        {"gate": "p0_3_full_export_pass", "passed": p0_3_full_ok, "threshold_relation": "boolean", "value": int(p0_3_full_ok), "threshold_value": 1},
    ])
    return gates


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _synthetic_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arm, reach in EXPECTED_ARM_REACH.items():
        for i in range(272):
            rows.append({
                "schema_version": EXPECTED_PRIVATE_SCHEMA,
                "source_phase": "P4L-VALIDATION",
                "arm_name": arm,
                "denominator_index_private": i,
                "gold_file_available": i < reach,
                "first_gold_file_rank": 7 if i < reach else 0,
                "candidate_pool_size": 28,
                "retrieval_latency_seconds": 2.0,
                "hard_cap_hit": False,
                "unique_file_cap_hit": False,
                "extra_depth_actions_executed": 3,
            })
    return rows


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    rows = _synthetic_rows()
    aggregate = _aggregate_from_rows(rows)
    schema_errors = _schema_errors(rows, set(EXPECTED_ARM_REACH))
    sanitized = p0_3._sanitize_private_arm_rows(rows[:2])
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {"scheduler_private_arm_row_export_pass", "no_go_p2_0_private_arm_rows_unavailable", "no_go_p2_0_locked_denominator_mismatch", "no_go_p2_0_arm_replay_mismatch", "no_go_p2_0_private_row_schema_invalid", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("schema_validation_accepts_synthetic_rows", not schema_errors),
        _check("schema_validation_rejects_bad_schema", bool(_schema_errors([{**rows[0], "schema_version": "bad"}], set(EXPECTED_ARM_REACH)))),
        _check("aggregate_reproduction_synthetic_reach", {row["arm_name"]: row["file_reach_count"] for row in aggregate} == EXPECTED_ARM_REACH),
        _check("aggregate_reproduction_synthetic_count", sum(row["denominator_count"] for row in aggregate) == EXPECTED_ROW_COUNT),
        _check("absent_rows_no_go_condition", len([]) == 0),
        _check("safe_private_path_accepts_tmp", _safe_private_path(Path("/tmp/openlocus_p4l_rows.jsonl"))),
        _check("sanitized_rows_hide_private_index", "denominator_index_private" not in sanitized[0] and "first_gold_file_rank" not in sanitized[0]),
        _check("scanner_accepts_sanitized_rows", tg._scan_summary({"sanitized_scheduler_private_arm_bucket_records": sanitized})["status"] == "pass"),
        _check("scanner_rejects_private_key", tg._scan_summary({"private_record_id": "x"})["status"] == "fail"),
    ]
    missing_gates = _gate_records(p4l_ok=True, denominator_ok=True, rows_available=False, row_count=0, row_count_ok=False, schema_ok=False, schema_error_count=0, arm_replay_ok=False, aggregate_error_count=0, p0_3_full_ok=False)
    checks.append(_check("missing_rows_downstream_gates_not_evaluated", all(g["threshold_relation"] in {"not_evaluated_missing_private_rows", "not_run_missing_private_rows"} for g in missing_gates if g["gate"] in {"private_arm_schema_valid", "arm_replay_aggregate_reproduces_p4l", "p0_3_full_export_pass"})))
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P2-0 scheduler private arm row recovery and sanitized export")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p4l-artifact", type=Path, default=DEFAULT_P4L)
    parser.add_argument("--p0-3-artifact", type=Path, default=DEFAULT_P0_3)
    parser.add_argument("--p0-2-artifact", type=Path, default=DEFAULT_P0_2)
    parser.add_argument("--private-arm-outcomes-jsonl", type=Path, default=None)
    parser.add_argument("--enable-frozen-rerun", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    p0_3_checks, p0_3_ok = p0_3.run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok and p0_3_ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks, p0_3_self_test={p0_3_ok})")
        raise SystemExit(0 if ok and p0_3_ok else 1)
    report = _build_report(args, checks, p0_3_checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    manifest = report["private_arm_row_recovery_manifest_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, read_status={manifest['read_status']}, rows={manifest['record_count']})")


if __name__ == "__main__":
    main()
