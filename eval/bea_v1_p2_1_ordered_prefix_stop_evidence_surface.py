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

import bea_v1_trace_gap_audit as tg  # noqa: E402


SCHEMA_VERSION = "bea_v1_p2_1_ordered_prefix_stop_evidence_surface.v1"
GENERATED_BY = "eval/bea_v1_p2_1_ordered_prefix_stop_evidence_surface.py"
CLAIM_LEVEL = "ordered_prefix_stop_evidence_surface_only"
MODE = "bea_v1_p2_1_ordered_prefix_stop_evidence_surface"
PHASE = "BEA-v1-P2-1"
DEFAULT_OUT = Path("artifacts/bea_v1_p2_1_ordered_prefix_stop_evidence_surface/bea_v1_p2_1_ordered_prefix_stop_evidence_surface_report.json")
DEFAULT_P0_8 = Path("artifacts/bea_v1_p0_8_ordered_prefix_stop_trace_surface/bea_v1_p0_8_ordered_prefix_stop_trace_surface_report.json")
DEFAULT_P0_1 = Path("artifacts/bea_v1_trace_gap_audit/bea_v1_trace_gap_audit_report.json")
DEFAULT_P0_2 = Path("artifacts/bea_v1_p0_2_actionability_matrix_refresh/bea_v1_p0_2_actionability_matrix_refresh_report.json")
DEFAULT_PRIVATE_TRACE = Path(".openlocus/research-private/bea_v1_p0_8_ordered_prefix_stop_private_trace.jsonl")

OPTIONAL_SOURCE_DEFAULTS = (
    ("bea3_anchor_span_latency", Path("artifacts/bea3_anchor_span_latency/bea3_anchor_span_latency_report.json"), "BEA-3"),
    ("bea4_external_scale_smoke", Path("artifacts/bea4_external_scale_smoke/bea4_external_scale_smoke_report.json"), "BEA-4"),
    ("bea5_frozen_policy_robustness", Path("artifacts/bea5_frozen_policy_robustness/bea5_frozen_policy_robustness_report.json"), "BEA-5"),
    ("bea_fd1_failure_decomposition", Path("artifacts/bea_fd1_failure_decomposition/bea_fd1_failure_decomposition_report.json"), "BEA-FD1"),
    ("bea_v04_p1_setwise_role_proxy", Path("artifacts/bea_v04_p1_setwise_role_proxy/bea_v04_p1_setwise_role_proxy_smoke_report.json"), "BEA-v0.4-P1"),
    ("bea_v04_p2_target_role_proxy_repair", Path("artifacts/bea_v04_p2_target_role_proxy_repair/bea_v04_p2_target_role_proxy_repair_smoke_report.json"), "BEA-v0.4-P2"),
    ("bea_v04_p3_support_complementarity_repair", Path("artifacts/bea_v04_p3_support_complementarity_repair/bea_v04_p3_support_complementarity_repair_smoke_report.json"), "BEA-v0.4-P3"),
)

STATUSES = (
    "ordered_prefix_stop_evidence_surface_pass",
    "ordered_prefix_stop_private_trace_pass",
    "no_go_p2_1_ordered_prefix_only_aggregate",
    "no_go_p2_1_ordered_prefix_inputs_unavailable",
    "no_go_p2_1_ordered_prefix_schema_invalid",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

PRIVATE_TRACE_SCHEMA = "bea_v1_p0_8_ordered_prefix_stop_private_trace.v1"
P0_8_STATUSES = {"ordered_prefix_stop_trace_surface_contract_pass", "ordered_prefix_stop_trace_surface_private_rows_pass"}
AGGREGATE_METRICS = {"action_steps", "candidate_count_read", "evidence_budget_used"}


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
        root = _private_root().resolve()
        resolved = path.resolve()
        return resolved == root or root in resolved.parents
    except Exception:
        return False


def _read_private_trace(path: Path | None) -> tuple[list[dict[str, Any]], str]:
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


def _bucket(value: Any, default: str = "unknown_not_reported") -> str:
    text = str(value or "").strip()
    return text if text else default


def _metric_bucket(metric: str) -> str:
    if metric == "action_steps":
        return "ordered_prefix_action_steps_aggregate"
    if metric == "candidate_count_read":
        return "ordered_prefix_candidate_read_aggregate"
    if metric == "evidence_budget_used":
        return "ordered_prefix_budget_used_aggregate"
    return "ordered_prefix_aggregate_metric"


def _coverage_bucket(*values: str) -> str:
    if any(v and not v.startswith("unknown") for v in values):
        return "p0_8_contract_field_present_or_derived"
    return "p0_8_contract_field_missing_private_trace"


def _make_row(
    *, idx: int,
    source: str,
    phase: str,
    failure: str,
    arm: str = "unknown_not_reported",
    contrast: str = "unknown_not_reported",
    stop_policy: str = "ordered_prefix_stop_evidence",
    signal: str = "aggregate_stop_signal",
    no_reference: bool = True,
    level: str = "aggregate_only",
    prefix_position: str = "unknown_missing_private_trace",
    prefix_cost: str = "unknown_missing_private_trace",
    budget_remaining: str = "unknown_missing_private_trace",
    marginal_gain: str = "unknown_missing_private_trace",
    counterfactual_continue: str = "unknown_missing_private_trace",
    trace_completeness: str = "aggregate_only_private_trace_missing",
) -> dict[str, Any]:
    return {
        "anonymous_stop_evidence_id": f"opse{idx:05d}",
        "source_artifact_bucket": source,
        "source_phase_bucket": phase,
        "failure_category_bucket": _bucket(failure, "unknown_failure_category"),
        "arm_bucket": _bucket(arm),
        "contrast_bucket": _bucket(contrast),
        "stop_policy_bucket": _bucket(stop_policy),
        "early_stop_signal_bucket": _bucket(signal),
        "no_early_stop_reference_available_bool": bool(no_reference),
        "aggregate_or_row_level_bucket": level,
        "prefix_position_bucket": _bucket(prefix_position, "unknown_missing_private_trace"),
        "prefix_cost_bucket": _bucket(prefix_cost, "unknown_missing_private_trace"),
        "budget_remaining_bucket": _bucket(budget_remaining, "unknown_missing_private_trace"),
        "marginal_gain_bucket": _bucket(marginal_gain, "unknown_missing_private_trace"),
        "counterfactual_continue_bucket": _bucket(counterfactual_continue, "unknown_missing_private_trace"),
        "trace_completeness_bucket": _bucket(trace_completeness),
        "p0_8_contract_field_coverage_bucket": _coverage_bucket(prefix_position, prefix_cost, budget_remaining, marginal_gain, counterfactual_continue),
    }


def _rows_from_p0_8(p0_8: dict[str, Any], start: int) -> list[dict[str, Any]]:
    rows = p0_8.get("ordered_prefix_stop_trace_contract_records", [])
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(_make_row(
            idx=start + len(out),
            source="p0_8_ordered_prefix_stop_trace_surface",
            phase="BEA-v1-P0-8",
            failure=str(row.get("failure_category", "early_stop_too_early") or "early_stop_too_early"),
            arm=str(row.get("arm_name", "unknown_not_exported") or "unknown_not_exported"),
            contrast="p0_8_contract_surface",
            stop_policy=str(row.get("stop_reason", "unknown_missing_private_trace") or "unknown_missing_private_trace"),
            signal="contract_requires_ordered_prefix_stop_trace",
            no_reference=True,
            level="aggregate_contract_only",
            prefix_position=str(row.get("prefix_position_bucket", "unknown_missing_private_trace") or "unknown_missing_private_trace"),
            prefix_cost=str(row.get("prefix_cost_bucket", "unknown_missing_private_trace") or "unknown_missing_private_trace"),
            budget_remaining=str(row.get("budget_remaining_bucket", "unknown_missing_private_trace") or "unknown_missing_private_trace"),
            marginal_gain=str(row.get("marginal_gain_bucket", "unknown_missing_private_trace") or "unknown_missing_private_trace"),
            counterfactual_continue=str(row.get("counterfactual_continue_bucket", "unknown_missing_private_trace") or "unknown_missing_private_trace"),
            trace_completeness="contract_surface_private_trace_missing",
        ))
    return out


def _rows_from_fd1(fd1: dict[str, Any], start: int) -> list[dict[str, Any]]:
    rows = fd1.get("availability_records", [])
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict) or row.get("category") != "early_stop_too_early":
            continue
        out.append(_make_row(
            idx=start + len(out),
            source="bea_fd1_failure_decomposition",
            phase=str(row.get("source_phase", "BEA-FD1") or "BEA-FD1"),
            failure="early_stop_too_early",
            arm="failure_decomposition_availability",
            contrast=str(row.get("benchmark", "unknown_benchmark") or "unknown_benchmark"),
            stop_policy="early_stop_failure_category_available",
            signal=str(row.get("category_availability", "available") or "available"),
            no_reference=True,
            level="aggregate_availability_only",
        ))
    return out


def _rows_from_metric_artifact(source: str, phase: str, artifact: dict[str, Any], start: int) -> list[dict[str, Any]]:
    rows = artifact.get("benchmark_arm_metric_records", [])
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        metric = str(row.get("metric", "") or "")
        if metric not in AGGREGATE_METRICS:
            continue
        out.append(_make_row(
            idx=start + len(out),
            source=source,
            phase=phase,
            failure="early_stop_too_early_or_budget_prefix_proxy",
            arm=str(row.get("arm", "unknown_arm") or "unknown_arm"),
            contrast=str(row.get("benchmark", "unknown_benchmark") or "unknown_benchmark"),
            stop_policy=_metric_bucket(metric),
            signal="aggregate_prefix_cost_proxy",
            no_reference=True,
            level="aggregate_metric_only",
            prefix_cost="aggregate_cost_bucket_available" if metric in {"action_steps", "evidence_budget_used"} else "unknown_missing_private_trace",
            trace_completeness="aggregate_metric_no_private_trace",
        ))
    return out


def _rows_from_delta_artifact(source: str, phase: str, artifact: dict[str, Any], start: int) -> list[dict[str, Any]]:
    rows = artifact.get("arm_delta_records", [])
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        metric = str(row.get("metric", "") or "")
        if metric not in AGGREGATE_METRICS:
            continue
        out.append(_make_row(
            idx=start + len(out),
            source=source,
            phase=phase,
            failure="early_stop_too_early_or_budget_prefix_proxy",
            arm=str(row.get("treatment_arm", "unknown_arm") or "unknown_arm"),
            contrast=str(row.get("baseline_arm", "unknown_baseline") or "unknown_baseline"),
            stop_policy=_metric_bucket(metric),
            signal="aggregate_delta_prefix_cost_proxy",
            no_reference=False,
            level="aggregate_metric_only",
            prefix_cost="aggregate_cost_delta_bucket_available" if metric in {"action_steps", "evidence_budget_used"} else "unknown_missing_private_trace",
            marginal_gain="aggregate_delta_available",
            trace_completeness="aggregate_delta_no_private_trace",
        ))
    return out


def _validate_private_trace_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        row_errors: list[str] = []
        if row.get("schema_version") != PRIVATE_TRACE_SCHEMA:
            row_errors.append("schema_version_mismatch")
        for key in ("failure_category", "arm_name", "prefix_position_bucket", "prefix_cost_bucket", "budget_remaining_bucket", "marginal_gain_bucket", "counterfactual_continue_bucket"):
            if not row.get(key):
                row_errors.append(f"{key}_missing")
        if row_errors:
            errors.append({"anonymous_error_id": f"pte{i:04d}", "error_bucket": "|".join(sorted(row_errors))})
    return errors


def _rows_from_private_trace(rows: list[dict[str, Any]], start: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(_make_row(
            idx=start + len(out),
            source="p0_8_private_ordered_prefix_stop_trace",
            phase=str(row.get("source_phase", "BEA-v1-P0-8") or "BEA-v1-P0-8"),
            failure=str(row.get("failure_category", "early_stop_too_early") or "early_stop_too_early"),
            arm=str(row.get("arm_name", "unknown_arm") or "unknown_arm"),
            contrast=str(row.get("contrast_bucket", "private_trace_row") or "private_trace_row"),
            stop_policy=str(row.get("stop_policy_bucket", row.get("stop_reason", "ordered_prefix_stop_private_trace")) or "ordered_prefix_stop_private_trace"),
            signal=str(row.get("early_stop_signal_bucket", "row_level_ordered_prefix_stop_trace") or "row_level_ordered_prefix_stop_trace"),
            no_reference=bool(row.get("no_early_stop_reference_available_bool", False)),
            level="row_level_private_trace_bucketed",
            prefix_position=str(row.get("prefix_position_bucket", "") or ""),
            prefix_cost=str(row.get("prefix_cost_bucket", "") or ""),
            budget_remaining=str(row.get("budget_remaining_bucket", "") or ""),
            marginal_gain=str(row.get("marginal_gain_bucket", "") or ""),
            counterfactual_continue=str(row.get("counterfactual_continue_bucket", "") or ""),
            trace_completeness="private_trace_bucketed_row_validated",
        ))
    return out


def _source_rows(source_defs: list[tuple[str, Path, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for source, path, phase in source_defs:
        artifact, status = _load_json(path)
        before = len(rows)
        if status == "pass":
            if source == "bea_fd1_failure_decomposition":
                rows.extend(_rows_from_fd1(artifact, len(rows)))
            else:
                rows.extend(_rows_from_metric_artifact(source, phase, artifact, len(rows)))
                rows.extend(_rows_from_delta_artifact(source, phase, artifact, len(rows)))
        manifests.append({
            "source_artifact_bucket": source,
            "source_phase_bucket": phase,
            "load_status": status,
            "source_status": str(artifact.get("status", "not_reported") or "not_reported"),
            "sanitized_rows_extracted": len(rows) - before,
        })
    return rows, manifests


def _rate(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0.0


def _readiness(rows: list[dict[str, Any]], private_trace_valid_count: int) -> dict[str, Any]:
    total = len(rows)
    prefix_position_count = sum(1 for row in rows if not str(row.get("prefix_position_bucket", "")).startswith("unknown"))
    prefix_cost_budget_count = sum(1 for row in rows if not str(row.get("prefix_cost_bucket", "")).startswith("unknown") or not str(row.get("budget_remaining_bucket", "")).startswith("unknown"))
    marginal_continue_count = sum(1 for row in rows if not str(row.get("marginal_gain_bucket", "")).startswith("unknown") or not str(row.get("counterfactual_continue_bucket", "")).startswith("unknown"))
    aggregate_count = sum(1 for row in rows if "aggregate" in str(row.get("aggregate_or_row_level_bucket", "")))
    row_level_or_prefix_rate = _rate(prefix_position_count, total)
    prefix_cost_budget_rate = _rate(prefix_cost_budget_count, total)
    marginal_continue_rate = _rate(marginal_continue_count, total)
    aggregate_only_rate = _rate(aggregate_count, total)
    pass_thresholds = (
        private_trace_valid_count > 0
        or (
            row_level_or_prefix_rate >= 0.50
            and prefix_cost_budget_rate >= 0.50
            and marginal_continue_rate >= 0.25
            and aggregate_only_rate <= 0.50
        )
    )
    return {
        "label_count": total,
        "private_trace_valid_count": private_trace_valid_count,
        "row_level_or_prefix_position_count": prefix_position_count,
        "row_level_or_prefix_position_rate": row_level_or_prefix_rate,
        "prefix_cost_or_budget_count": prefix_cost_budget_count,
        "prefix_cost_or_budget_rate": prefix_cost_budget_rate,
        "marginal_gain_or_continue_count": marginal_continue_count,
        "marginal_gain_or_continue_rate": marginal_continue_rate,
        "aggregate_only_count": aggregate_count,
        "aggregate_only_rate": aggregate_only_rate,
        "private_trace_readiness_passed": bool(pass_thresholds),
    }


def _summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in rows)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _reindex_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        item = dict(row)
        item["anonymous_stop_evidence_id"] = f"opse{i:05d}"
        out.append(item)
    return out


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    p0_8, p0_8_status = _load_json(args.p0_8_artifact)
    p0_1, p0_1_status = _load_json(args.p0_1_artifact)
    p0_2, p0_2_status = _load_json(args.p0_2_artifact)
    source_defs = list(OPTIONAL_SOURCE_DEFAULTS)
    source_rows, source_manifests = _source_rows(source_defs)
    rows = _rows_from_p0_8(p0_8, 0) if p0_8_status == "pass" else []
    rows.extend(source_rows)
    private_trace_rows, private_trace_status = _read_private_trace(args.private_trace_jsonl)
    private_errors = _validate_private_trace_rows(private_trace_rows) if private_trace_status == "pass" else []
    valid_private_rows = private_trace_rows if private_trace_status == "pass" and not private_errors else []
    rows.extend(_rows_from_private_trace(valid_private_rows, len(rows)))
    rows = _reindex_rows(rows)
    source_coverage = len({row["source_artifact_bucket"] for row in rows})
    early_stop_rows = sum(1 for row in rows if "early_stop" in row["failure_category_bucket"])
    readiness = _readiness(rows, len(valid_private_rows))

    p0_8_ok = p0_8_status == "pass" and p0_8.get("status") in P0_8_STATUSES and p0_8.get("forbidden_scan", {}).get("status") == "pass"
    p0_1_ok = p0_1_status == "pass" and p0_1.get("status") == "trace_gap_audit_pass" and p0_1.get("forbidden_scan", {}).get("status") == "pass"
    p0_2_ok = p0_2_status == "pass" and p0_2.get("status") == "actionability_matrix_refresh_pass" and p0_2.get("forbidden_scan", {}).get("status") == "pass"
    optional_loaded = sum(1 for manifest in source_manifests if manifest["load_status"] == "pass")
    rows_ok = len(rows) > 0 and early_stop_rows > 0
    coverage_ok = source_coverage >= 2
    schema_ok = private_trace_status != "pass" or not private_errors
    self_tests_ok = all(c["passed"] for c in checks)
    if not self_tests_ok:
        status = "fail_schema_contract"
    elif not schema_ok:
        status = "no_go_p2_1_ordered_prefix_schema_invalid"
    elif not (p0_8_ok and p0_1_ok and p0_2_ok and optional_loaded >= 1 and rows_ok):
        status = "no_go_p2_1_ordered_prefix_inputs_unavailable"
    elif readiness["private_trace_readiness_passed"] and len(valid_private_rows) > 0:
        status = "ordered_prefix_stop_private_trace_pass"
    elif readiness["private_trace_readiness_passed"] and coverage_ok:
        status = "ordered_prefix_stop_evidence_surface_pass"
    else:
        status = "no_go_p2_1_ordered_prefix_only_aggregate"

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "aggregate_only_private_trace_not_ready" if status == "no_go_p2_1_ordered_prefix_only_aggregate" else "inputs_unavailable" if status == "no_go_p2_1_ordered_prefix_inputs_unavailable" else "schema_invalid" if status == "no_go_p2_1_ordered_prefix_schema_invalid" else "" if status in {"ordered_prefix_stop_evidence_surface_pass", "ordered_prefix_stop_private_trace_pass"} else "schema_contract_failed",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_tests_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": [
            {"input_artifact": "p0_8_ordered_prefix_stop_trace_surface", "load_status": p0_8_status, "source_status": str(p0_8.get("status", "") or ""), "source_schema": str(p0_8.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_8.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_8.get("forbidden_scan"), dict) else "not_reported")},
            {"input_artifact": "p0_1_trace_gap_audit", "load_status": p0_1_status, "source_status": str(p0_1.get("status", "") or ""), "source_schema": str(p0_1.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_1.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_1.get("forbidden_scan"), dict) else "not_reported")},
            {"input_artifact": "p0_2_actionability_matrix_refresh", "load_status": p0_2_status, "source_status": str(p0_2.get("status", "") or ""), "source_schema": str(p0_2.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_2.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_2.get("forbidden_scan"), dict) else "not_reported")},
        ],
        "optional_source_load_records": source_manifests,
        "private_trace_manifest_records": [{
            "manifest_name": "bea_v1_p0_8_ordered_prefix_stop_private_trace",
            "schema_version": PRIVATE_TRACE_SCHEMA,
            "read_status": private_trace_status,
            "record_count": len(private_trace_rows),
            "valid_record_count": len(valid_private_rows),
            "error_count": len(private_errors),
            "path_publicly_serialized": False,
            "storage_class": "project_ignored_private_jsonl_optional",
        }],
        "sanitized_stop_evidence_records": rows,
        "source_artifact_summary_records": _summary(rows, "source_artifact_bucket"),
        "failure_category_summary_records": _summary(rows, "failure_category_bucket"),
        "aggregate_or_row_level_summary_records": _summary(rows, "aggregate_or_row_level_bucket"),
        "trace_completeness_summary_records": _summary(rows, "trace_completeness_bucket"),
        "private_trace_error_summary_records": _summary(private_errors, "error_bucket"),
        "ordered_prefix_readiness_records": [{
            **readiness,
            "source_artifact_coverage_count": source_coverage,
            "early_stop_failure_category_row_count": early_stop_rows,
            "sanitized_stop_evidence_row_count": len(rows),
        }],
        "gate_records": [
            {"gate": "p0_8_contract_available_pass", "passed": p0_8_ok, "threshold_relation": "boolean", "value": int(p0_8_ok), "threshold_value": 1},
            {"gate": "p0_1_trace_gap_available_pass", "passed": p0_1_ok, "threshold_relation": "boolean", "value": int(p0_1_ok), "threshold_value": 1},
            {"gate": "p0_2_matrix_available_pass", "passed": p0_2_ok, "threshold_relation": "boolean", "value": int(p0_2_ok), "threshold_value": 1},
            {"gate": "committed_early_stop_source_loads", "passed": optional_loaded >= 1, "threshold_relation": "greater_or_equal", "value": optional_loaded, "threshold_value": 1},
            {"gate": "sanitized_stop_evidence_rows_nonzero", "passed": len(rows) > 0, "threshold_relation": "greater_than", "value": len(rows), "threshold_value": 0},
            {"gate": "early_stop_failure_category_rows_nonzero", "passed": early_stop_rows > 0, "threshold_relation": "greater_than", "value": early_stop_rows, "threshold_value": 0},
            {"gate": "source_artifact_coverage_count", "passed": coverage_ok, "threshold_relation": "greater_or_equal", "value": source_coverage, "threshold_value": 2},
            {"gate": "private_trace_readiness", "passed": bool(readiness["private_trace_readiness_passed"]), "threshold_relation": "boolean", "value": int(readiness["private_trace_readiness_passed"]), "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "aggregate_ordered_prefix_evidence_extracted_private_trace_not_ready" if status == "no_go_p2_1_ordered_prefix_only_aggregate" else "private_ordered_prefix_trace_ready" if status == "ordered_prefix_stop_private_trace_pass" else "ordered_prefix_surface_ready" if status == "ordered_prefix_stop_evidence_surface_pass" else "required_inputs_or_schema_unavailable",
            "authorization": "ordered_prefix_stop_evidence_surface_extraction_only",
            "ordered_prefix_stop_policy_change_authorized": False,
            "trace_counterfactual_execution_authorized": False,
            "support_counterfactual_execution_authorized": False,
            "policy_tuning_authorized": False,
            "implementation_authorized": False,
            "selector_or_reranker_authorized": False,
            "p5_authorized": False,
            "v1_a_authorized": False,
            "runtime_promotion_authorized": False,
            "broad_retrieval_expansion_authorized": False,
            "method_winner_claimed": False,
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
    aggregate = [_make_row(idx=0, source="fixture", phase="test", failure="early_stop_too_early")]
    private = [{
        "schema_version": PRIVATE_TRACE_SCHEMA,
        "failure_category": "early_stop_too_early",
        "arm_name": "arm",
        "prefix_position_bucket": "prefix_1_3",
        "prefix_cost_bucket": "cost_low",
        "budget_remaining_bucket": "budget_some",
        "marginal_gain_bucket": "gain_none",
        "counterfactual_continue_bucket": "continue_would_help_unknown",
    }]
    private_rows = _rows_from_private_trace(private, 0)
    duplicated = [_make_row(idx=0, source="fixture_a", phase="test", failure="early_stop_too_early"), _make_row(idx=0, source="fixture_b", phase="test", failure="early_stop_too_early")]
    reindexed = _reindex_rows(duplicated)
    readiness_agg = _readiness(aggregate, 0)
    readiness_private = _readiness(private_rows, 1)
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {"ordered_prefix_stop_evidence_surface_pass", "ordered_prefix_stop_private_trace_pass", "no_go_p2_1_ordered_prefix_only_aggregate", "no_go_p2_1_ordered_prefix_inputs_unavailable", "no_go_p2_1_ordered_prefix_schema_invalid", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("private_trace_schema_accepts_fixture", not _validate_private_trace_rows(private)),
        _check("private_trace_schema_rejects_bad_fixture", bool(_validate_private_trace_rows([{**private[0], "schema_version": "bad"}]))),
        _check("aggregate_only_readiness_fails", readiness_agg["private_trace_readiness_passed"] is False and readiness_agg["aggregate_only_rate"] == 1.0),
        _check("private_trace_readiness_passes", readiness_private["private_trace_readiness_passed"] is True),
        _check("scanner_accepts_sanitized_row", tg._scan_summary({"sanitized_stop_evidence_records": aggregate})["status"] == "pass"),
        _check("scanner_rejects_path_key", tg._scan_summary({"path": "x"})["status"] == "fail"),
        _check("anonymous_stop_ids_unique_after_reindex", len({row["anonymous_stop_evidence_id"] for row in reindexed}) == len(reindexed) and reindexed[1]["anonymous_stop_evidence_id"] == "opse00001"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P2-1 ordered-prefix stop evidence surface")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p0-8-artifact", type=Path, default=DEFAULT_P0_8)
    parser.add_argument("--p0-1-artifact", type=Path, default=DEFAULT_P0_1)
    parser.add_argument("--p0-2-artifact", type=Path, default=DEFAULT_P0_2)
    parser.add_argument("--private-trace-jsonl", type=Path, default=DEFAULT_PRIVATE_TRACE)
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
    readiness = report["ordered_prefix_readiness_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, rows={readiness['sanitized_stop_evidence_row_count']}, sources={readiness['source_artifact_coverage_count']}, private_ready={readiness['private_trace_readiness_passed']})")


if __name__ == "__main__":
    main()
