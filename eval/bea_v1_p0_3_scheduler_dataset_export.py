#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
import time
from pathlib import Path
from typing import Any, Mapping, NoReturn

import sys

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

import bea_v1_trace_gap_audit as tg  # noqa: E402


SCHEMA_VERSION = "bea_v1_p0_3_scheduler_dataset_export.v1"
GENERATED_BY = "eval/bea_v1_p0_3_scheduler_dataset_export.py"
CLAIM_LEVEL = "bea_v1_p0_3_scheduler_dataset_export_only"
MODE = "bea_v1_p0_3_scheduler_dataset_export"
PHASE = "BEA-v1-P0-3"

DEFAULT_OUT = Path("artifacts/bea_v1_p0_3_scheduler_dataset_export/bea_v1_p0_3_scheduler_dataset_export_report.json")
DEFAULT_P4L = Path("artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json")
DEFAULT_P0_2 = Path("artifacts/bea_v1_p0_2_actionability_matrix_refresh/bea_v1_p0_2_actionability_matrix_refresh_report.json")

STATUSES = (
    "scheduler_dataset_export_contract_pass",
    "scheduler_dataset_export_full_pass",
    "no_go_scheduler_dataset_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

P4L_EXPECTED_STATUS = "bea_v1_p4l_locked_non_python_scheduler_validation_pass"
P0_2_EXPECTED_STATUS = "actionability_matrix_refresh_pass"
PRIVATE_ARM_SCHEMA = "bea_v1_p4l_private_arm_outcome.v1"
EXPECTED_PRIVATE_ARM_ROWS = 1088
BEA_V1_TRACE_LOGGER_DEFAULT_ENABLED = False


def _bea_v1_scheduler_action_cost_trace_hook(
    event: Mapping[str, Any], *, enabled: bool = BEA_V1_TRACE_LOGGER_DEFAULT_ENABLED
) -> dict[str, Any]:
    if not enabled:
        return {"trace_logger_enabled": False, "trace_capture_attempted": False, "private_trace_row_written": False}
    from bea_v1_frozen_trace_logger_helpers import (  # noqa: WPS433
        build_scheduler_action_cost_trace_capture_row_private,
        sanitize_scheduler_action_cost_trace_capture_row_public,
        validate_scheduler_action_cost_trace_capture_row_private,
        validate_scheduler_action_cost_trace_capture_row_public_projection,
    )

    private_row = build_scheduler_action_cost_trace_capture_row_private(event)
    private_validation = validate_scheduler_action_cost_trace_capture_row_private(private_row)
    public_row = sanitize_scheduler_action_cost_trace_capture_row_public(private_row)
    public_validation = validate_scheduler_action_cost_trace_capture_row_public_projection(public_row)
    return {
        "trace_logger_enabled": True,
        "trace_capture_attempted": False,
        "private_trace_row_written": False,
        "surface_bucket": "scheduler_action_cost",
        "private_validation_status": private_validation.get("validation_status"),
        "public_validation_status": public_validation.get("validation_status"),
        "public_projection": public_row,
    }


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        return {}, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (data, "pass") if isinstance(data, dict) else ({}, "parse_failed")


def _latency_bucket(value: float) -> str:
    if value <= 0:
        return "latency_unknown"
    if value <= 1.0:
        return "latency_le_1s"
    if value <= 2.5:
        return "latency_1_2p5s"
    if value <= 5.0:
        return "latency_2p5_5s"
    return "latency_gt_5s"


def _pool_bucket(value: int) -> str:
    if value <= 0:
        return "pool_unknown"
    if value <= 15:
        return "pool_le_15"
    if value <= 32:
        return "pool_16_32"
    if value <= 64:
        return "pool_33_64"
    return "pool_gt_64"


def _rank_bucket(value: int) -> str:
    if value <= 0:
        return "rank_missing_or_unreached"
    if value <= 10:
        return "rank_1_10"
    if value <= 20:
        return "rank_11_20"
    if value <= 50:
        return "rank_21_50"
    if value <= 100:
        return "rank_51_100"
    return "rank_gt_100"


def _extra_depth_bucket(value: int) -> str:
    if value <= 0:
        return "extra_depth_none"
    if value <= 3:
        return "extra_depth_1_3"
    if value <= 8:
        return "extra_depth_4_8"
    return "extra_depth_gt_8"


def _private_arm_manifest(p4l: dict[str, Any]) -> dict[str, Any]:
    rows = p4l.get("private_manifest_records", [])
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("schema_version") == PRIVATE_ARM_SCHEMA:
                return row
    return {}


def _read_private_arm_rows(path: Path | None) -> tuple[list[dict[str, Any]], str]:
    if path is None:
        return [], "not_supplied"
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


def _sanitize_private_arm_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        arm = str(row.get("arm_name", "") or "")
        latency = float(row.get("retrieval_latency_seconds", 0.0) or 0.0)
        pool = int(row.get("candidate_pool_size", 0) or 0)
        rank = int(row.get("first_gold_file_rank", 0) or 0)
        extra = int(row.get("extra_depth_actions_executed", 0) or 0)
        out.append({
            "anonymous_local_id": f"sd{ i:05d}",
            "dataset_row_kind": "private_arm_outcome_sanitized",
            "arm_name": arm,
            "state_bucket": "locked_non_python_file_miss_denominator",
            "action_arm": arm,
            "file_reach_bucket": "reached" if bool(row.get("gold_file_available", False)) else "not_reached",
            "first_gold_rank_bucket": _rank_bucket(rank),
            "latency_bucket": _latency_bucket(latency),
            "pool_size_bucket": _pool_bucket(pool),
            "hard_cap_bucket": "hard_cap_hit" if bool(row.get("hard_cap_hit", False)) else "hard_cap_not_hit",
            "unique_file_cap_bucket": "unique_file_cap_hit" if bool(row.get("unique_file_cap_hit", False)) else "unique_file_cap_not_hit",
            "extra_depth_action_bucket": _extra_depth_bucket(extra),
        })
    return out


def _arm_records(p4l: dict[str, Any]) -> list[dict[str, Any]]:
    rows = p4l.get("arm_metrics_records", [])
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    baseline = next((r for r in rows if isinstance(r, dict) and r.get("arm_name") == "baseline_current_candidate_pool"), {})
    base_reach = int(baseline.get("file_reach_count", 0) or 0) if isinstance(baseline, dict) else 0
    base_latency = float(baseline.get("mean_latency_seconds", 0.0) or 0.0) if isinstance(baseline, dict) else 0.0
    base_pool = float(baseline.get("mean_candidate_pool_size", 0.0) or 0.0) if isinstance(baseline, dict) else 0.0
    for row in rows:
        if not isinstance(row, dict):
            continue
        reach = int(row.get("file_reach_count", 0) or 0)
        latency = float(row.get("mean_latency_seconds", 0.0) or 0.0)
        pool = float(row.get("mean_candidate_pool_size", 0.0) or 0.0)
        out.append({
            "arm_name": str(row.get("arm_name", "") or ""),
            "dataset_row_kind": "arm_aggregate_sanitized",
            "denominator_count": int(row.get("denominator_count", 0) or 0),
            "file_reach_count": reach,
            "file_reach_rate_bucket": "reach_zero" if reach == 0 else "reach_nonzero",
            "delta_reach_vs_baseline": reach - base_reach,
            "mean_latency_bucket": _latency_bucket(latency),
            "latency_vs_baseline_bucket": "latency_lower_or_equal_baseline" if base_latency and latency <= base_latency else "latency_higher_than_baseline",
            "mean_pool_bucket": _pool_bucket(int(round(pool))),
            "pool_vs_baseline_bucket": "pool_lower_or_equal_baseline" if base_pool and pool <= base_pool else "pool_higher_than_baseline",
            "hard_cap_violation_count": int(row.get("hard_cap_violation_count", 0) or 0),
            "retrieval_error_count": int(row.get("retrieval_error_count", 0) or 0),
        })
    return out


def _subgroup_records(p4l: dict[str, Any]) -> list[dict[str, Any]]:
    rows = p4l.get("subgroup_records", [])
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        out.append({
            "anonymous_local_id": f"sg{i:03d}",
            "dataset_row_kind": "subgroup_denominator_sanitized",
            "source_bucket": str(row.get("source_frame", "") or ""),
            "language_bucket": str(row.get("language", "") or ""),
            "denominator_count_bucket": _pool_bucket(int(row.get("denominator_count", 0) or 0)),
        })
    return out


def _actionability_rows(p0_2: dict[str, Any]) -> list[dict[str, Any]]:
    rows = p0_2.get("refreshed_actionability_matrix_records", [])
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("trace_field") != "action_cost_trace":
            continue
        out.append({
            "failure_category": str(row.get("failure_category", "") or ""),
            "action_layer": str(row.get("action_layer", "") or ""),
            "cell_readiness_class": str(row.get("cell_readiness_class", "") or ""),
            "cell_blocker_reason": str(row.get("cell_blocker_reason", "") or ""),
            "authorized_next_step": str(row.get("authorized_next_step", "") or ""),
        })
    return out


def _summary(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in records)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    p4l, p4l_status = _load_json(args.p4l_artifact)
    p0_2, p0_2_status = _load_json(args.p0_2_artifact)
    private_rows, private_status = _read_private_arm_rows(args.private_arm_outcomes_jsonl)
    sanitized_private_rows = _sanitize_private_arm_rows(private_rows) if private_status == "pass" else []
    arm_rows = _arm_records(p4l)
    subgroup_rows = _subgroup_records(p4l)
    actionability_rows = _actionability_rows(p0_2)
    manifest = _private_arm_manifest(p4l)
    p4l_ok = p4l_status == "pass" and p4l.get("status") == P4L_EXPECTED_STATUS and p4l.get("forbidden_scan", {}).get("status") == "pass"
    p0_2_ok = p0_2_status == "pass" and p0_2.get("status") == P0_2_EXPECTED_STATUS and p0_2.get("forbidden_scan", {}).get("status") == "pass"
    aggregate_ok = len(arm_rows) == 4 and len(subgroup_rows) >= 2 and bool(actionability_rows)
    private_full = private_status == "pass" and len(private_rows) == EXPECTED_PRIVATE_ARM_ROWS and all(row.get("schema_version") == PRIVATE_ARM_SCHEMA for row in private_rows)
    if not (p4l_ok and p0_2_ok and aggregate_ok and all(c["passed"] for c in checks)):
        status = "no_go_scheduler_dataset_inputs_unavailable"
    elif private_full:
        status = "scheduler_dataset_export_full_pass"
    else:
        status = "scheduler_dataset_export_contract_pass"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status in {"scheduler_dataset_export_contract_pass", "scheduler_dataset_export_full_pass"} else "required_input_artifact_unavailable_or_unexpected_status",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": all(c["passed"] for c in checks),
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": [
            {"input_artifact": "p4l_locked_scheduler_validation", "load_status": p4l_status, "source_status": str(p4l.get("status", "") or ""), "source_schema": str(p4l.get("schema_version", "") or ""), "forbidden_scan_status": str(p4l.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p4l.get("forbidden_scan"), dict) else "not_reported")},
            {"input_artifact": "p0_2_actionability_matrix_refresh", "load_status": p0_2_status, "source_status": str(p0_2.get("status", "") or ""), "source_schema": str(p0_2.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_2.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_2.get("forbidden_scan"), dict) else "not_reported")},
        ],
        "private_arm_outcomes_input_status": private_status,
        "private_arm_outcomes_supplied": args.private_arm_outcomes_jsonl is not None,
        "private_arm_outcomes_expected_record_count": EXPECTED_PRIVATE_ARM_ROWS,
        "private_arm_outcomes_sanitized_record_count": len(sanitized_private_rows),
        "private_arm_outcomes_manifest_record": {
            "manifest_name": str(manifest.get("manifest_name", "") or ""),
            "schema_version": str(manifest.get("schema_version", "") or ""),
            "record_count": int(manifest.get("record_count", 0) or 0),
            "records_written": bool(manifest.get("records_written", False)),
            "path_publicly_serialized": bool(manifest.get("path_publicly_serialized", True)),
            "storage_class": str(manifest.get("storage_class", "") or ""),
        },
        "scheduler_arm_dataset_records": arm_rows,
        "scheduler_subgroup_dataset_records": subgroup_rows,
        "scheduler_private_arm_sanitized_records": sanitized_private_rows,
        "scheduler_actionability_join_records": actionability_rows,
        "scheduler_dataset_readiness_records": [
            {"dataset_surface": "aggregate_arm_metrics", "readiness": "available", "record_count": len(arm_rows)},
            {"dataset_surface": "subgroup_denominator_buckets", "readiness": "available", "record_count": len(subgroup_rows)},
            {"dataset_surface": "private_arm_outcome_rows", "readiness": "available" if private_full else "manifest_only_or_not_supplied", "record_count": len(sanitized_private_rows)},
        ],
        "arm_name_summary_records": _summary(arm_rows + sanitized_private_rows, "arm_name"),
        "private_latency_bucket_summary_records": _summary(sanitized_private_rows, "latency_bucket"),
        "private_pool_bucket_summary_records": _summary(sanitized_private_rows, "pool_size_bucket"),
        "gate_records": [
            {"gate": "p4l_artifact_available", "passed": p4l_ok, "threshold_relation": "boolean", "value": int(p4l_ok), "threshold_value": 1},
            {"gate": "p0_2_artifact_available", "passed": p0_2_ok, "threshold_relation": "boolean", "value": int(p0_2_ok), "threshold_value": 1},
            {"gate": "aggregate_scheduler_surface_available", "passed": aggregate_ok, "threshold_relation": "boolean", "value": int(aggregate_ok), "threshold_value": 1},
            {"gate": "private_arm_rows_full_export_available", "passed": private_full, "threshold_relation": "boolean_optional", "value": int(private_full), "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "scheduler_dataset_contract_exported_private_rows_optional" if status == "scheduler_dataset_export_contract_pass" else "scheduler_dataset_full_private_rows_exported" if status == "scheduler_dataset_export_full_pass" else "required_inputs_unavailable",
            "authorization": "support_link_input_design_or_private_arm_row_full_export_only",
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


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    sample_rows = [{
        "schema_version": PRIVATE_ARM_SCHEMA,
        "arm_name": "p4_latency_aware_action_scheduler_frozen",
        "denominator_index_private": 1,
        "gold_file_available": True,
        "first_gold_file_rank": 7,
        "candidate_pool_size": 28,
        "retrieval_latency_seconds": 2.1,
        "hard_cap_hit": False,
        "unique_file_cap_hit": False,
        "extra_depth_actions_executed": 3,
    }]
    sanitized = _sanitize_private_arm_rows(sample_rows)
    checks = [
        _check("status_vocab_nonempty", bool(STATUSES)),
        _check("latency_bucket_mid", _latency_bucket(2.1) == "latency_1_2p5s"),
        _check("pool_bucket_mid", _pool_bucket(28) == "pool_16_32"),
        _check("rank_bucket_top10", _rank_bucket(7) == "rank_1_10"),
        _check("private_sanitized_rows_hide_exact_rank", "first_gold_file_rank" not in sanitized[0]),
        _check("private_sanitized_rows_hide_denominator_index", "denominator_index_private" not in sanitized[0]),
        _check("scanner_accepts_sanitized_private_row", tg._scan_summary({"scheduler_private_arm_sanitized_records": sanitized})["status"] == "pass"),
        _check("scanner_rejects_private_key", tg._scan_summary({"private_record_id": 1})["status"] == "fail"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P0-3 scheduler dataset export")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p4l-artifact", type=Path, default=DEFAULT_P4L)
    parser.add_argument("--p0-2-artifact", type=Path, default=DEFAULT_P0_2)
    parser.add_argument("--private-arm-outcomes-jsonl", type=Path, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = _build_report(args, checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, arm_records={len(report['scheduler_arm_dataset_records'])})")


if __name__ == "__main__":
    main()
