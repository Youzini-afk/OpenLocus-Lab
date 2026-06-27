#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
import time
from pathlib import Path
from typing import Any, NoReturn

import sys

_EVAL_DIR = Path(__file__).resolve().parent
if str(_EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(_EVAL_DIR))

import bea_v1_p1_actionability_audit as p1  # noqa: E402
import bea_v1_trace_gap_audit as tg  # noqa: E402


SCHEMA_VERSION = "bea_v1_p0_2_actionability_matrix_refresh.v1"
GENERATED_BY = "eval/bea_v1_p0_2_actionability_matrix_refresh.py"
CLAIM_LEVEL = "bea_v1_p0_2_actionability_matrix_refresh_only"
MODE = "bea_v1_p0_2_actionability_matrix_refresh"
PHASE = "BEA-v1-P0-2"

DEFAULT_OUT = Path("artifacts/bea_v1_p0_2_actionability_matrix_refresh/bea_v1_p0_2_actionability_matrix_refresh_report.json")
DEFAULT_P1 = Path("artifacts/bea_v1_p1_actionability_audit/bea_v1_p1_actionability_audit_report.json")
DEFAULT_TRACE_GAP = tg.DEFAULT_OUT

STATUSES = (
    "actionability_matrix_refresh_pass",
    "no_go_actionability_matrix_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

READINESS_CLASSES = (
    "ready_sanitized_trace",
    "blocked_private_export",
    "blocked_missing_label",
    "blocked_missing_trace",
    "blocked_aggregate_only",
    "not_applicable_by_layer",
)

BLOCKER_BY_TRACE = {
    "action_cost_trace": "requires_scheduler_sanitized_export",
    "support_link_trace": "requires_support_link_labeling",
    "same_file_redundancy_trace": "requires_same_file_redundancy_trace",
    "risk_penalty_trace": "requires_risk_penalty_trace",
    "ordered_prefix_stop_trace": "requires_ordered_prefix_stop_trace",
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


def _readiness(cell_class: str, trace_availability: str) -> str:
    if cell_class == "not_actionable_by_layer":
        return "not_applicable_by_layer"
    if trace_availability == "sanitized_available":
        return "ready_sanitized_trace"
    if trace_availability == "private_only_needs_public_export":
        return "blocked_private_export"
    if trace_availability == "missing_label":
        return "blocked_missing_label"
    if trace_availability == "missing_trace":
        return "blocked_missing_trace"
    return "blocked_aggregate_only"


def _next_step(cell_class: str, readiness: str, trace_next_step: str) -> str:
    if cell_class == "not_actionable_by_layer":
        return "no_action_for_non_actionable_cell"
    if readiness == "ready_sanitized_trace":
        return "reuse_existing_sanitized_rows"
    if readiness == "blocked_missing_label":
        return "design_labeling_input_before_counterfactual"
    return trace_next_step or "export_or_preserve_trace_before_new_policy_experiment"


def _p1_matrix_rows(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    rows = artifact.get("actionability_matrix_records", [])
    if isinstance(rows, list) and rows:
        return [r for r in rows if isinstance(r, dict)]
    return p1._build_actionability_matrix()


def _trace_rows_by_category(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = artifact.get("trace_gap_records", [])
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("category"):
                out[str(row["category"])] = row
    return out


def _artifact_record(key: str, artifact: dict[str, Any], load_status: str, row_field: str) -> dict[str, Any]:
    rows = artifact.get(row_field, [])
    return {
        "input_artifact": key,
        "load_status": load_status,
        "source_status": str(artifact.get("status", "") or ""),
        "source_schema": str(artifact.get("schema_version", "") or ""),
        "forbidden_scan_status": str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported"),
        "record_count": len(rows) if isinstance(rows, list) else 0,
    }


def _build_rows(p1_rows: list[dict[str, Any]], trace_by_category: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    refreshed: list[dict[str, Any]] = []
    deltas: list[dict[str, Any]] = []
    for row in sorted(p1_rows, key=lambda r: (str(r.get("failure_category", "")), str(r.get("action_layer", "")))):
        category = str(row.get("failure_category", "") or "")
        action_layer = str(row.get("action_layer", "") or "")
        trace = trace_by_category.get(category, {})
        trace_field = str(trace.get("trace_field", "") or "")
        trace_availability = str(trace.get("trace_availability", "") or "")
        cell_class = str(row.get("cell_class", "") or "")
        readiness = _readiness(cell_class, trace_availability)
        blocker = "" if readiness in {"ready_sanitized_trace", "not_applicable_by_layer"} else BLOCKER_BY_TRACE.get(trace_field, "requires_trace_surface_before_new_policy_experiment")
        refreshed.append({
            "failure_category": category,
            "action_layer": action_layer,
            "cell_class": cell_class,
            "is_direct_actionable": bool(row.get("is_direct_actionable", False)),
            "is_indirect_actionable": bool(row.get("is_indirect_actionable", False)),
            "is_candidate_unavailable": bool(row.get("is_candidate_unavailable", False)),
            "is_ceiling_unavailable": bool(row.get("is_ceiling_unavailable", False)),
            "trace_field": trace_field,
            "trace_availability": trace_availability,
            "trace_priority": str(trace.get("priority", "") or ""),
            "trace_risk_class": str(trace.get("risk_class", "") or ""),
            "trace_publication_boundary": str(trace.get("publication_boundary", "") or ""),
            "trace_minimum_public_shape": str(trace.get("minimum_public_shape", "") or ""),
            "trace_next_step": str(trace.get("next_step", "") or ""),
            "trace_evidence_basis": str(trace.get("evidence_basis", "") or ""),
            "cell_readiness_class": readiness,
            "cell_blocker_reason": blocker,
            "authorized_next_step": _next_step(cell_class, readiness, str(trace.get("next_step", "") or "")),
        })
        for delta_field in ("trace_field_added", "readiness_class_added", "next_step_added"):
            deltas.append({
                "failure_category": category,
                "action_layer": action_layer,
                "delta_field": delta_field,
                "causal_cell_class_changed": False,
            })
    return refreshed, deltas


def _summary(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in records)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _unique(records: list[dict[str, Any]], keys: tuple[str, ...]) -> bool:
    seen: set[tuple[Any, ...]] = set()
    for row in records:
        key = tuple(row.get(k) for k in keys)
        if key in seen:
            return False
        seen.add(key)
    return True


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    p1_artifact, p1_status = _load_json(args.p1_artifact)
    trace_artifact, trace_status = _load_json(args.trace_gap_artifact)
    p1_rows = _p1_matrix_rows(p1_artifact)
    trace_by_category = _trace_rows_by_category(trace_artifact)
    refreshed, deltas = _build_rows(p1_rows, trace_by_category)
    p1_ok = p1_status == "pass" and len(p1_rows) == 72 and _unique(p1_rows, ("failure_category", "action_layer"))
    trace_ok = trace_status == "pass" and trace_artifact.get("status") == "trace_gap_audit_pass" and trace_artifact.get("forbidden_scan", {}).get("status") == "pass"
    categories_p1 = {str(row.get("failure_category", "") or "") for row in p1_rows}
    categories_trace = set(trace_by_category)
    coverage_ok = categories_p1 == categories_trace and len(categories_p1) == 12
    matrix_ok = len(refreshed) == 72 and _unique(refreshed, ("failure_category", "action_layer"))
    causal_ok = all(not row["causal_cell_class_changed"] for row in deltas)
    status = "actionability_matrix_refresh_pass" if p1_ok and trace_ok and coverage_ok and matrix_ok and causal_ok and all(c["passed"] for c in checks) else "no_go_actionability_matrix_inputs_unavailable"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status == "actionability_matrix_refresh_pass" else "required_input_artifact_unavailable_or_unexpected_status",
        "status_vocabulary": list(STATUSES),
        "cell_readiness_vocabulary": list(READINESS_CLASSES),
        "self_test_passed": all(c["passed"] for c in checks),
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "source_join_records": [
            _artifact_record("p1_actionability_audit", p1_artifact, p1_status, "actionability_matrix_records"),
            _artifact_record("p0_1_trace_gap_audit", trace_artifact, trace_status, "trace_gap_records"),
        ],
        "refreshed_actionability_matrix_records": refreshed,
        "refresh_delta_records": deltas,
        "trace_availability_summary_records": _summary(refreshed, "trace_availability"),
        "trace_priority_summary_records": _summary(refreshed, "trace_priority"),
        "trace_field_summary_records": _summary(refreshed, "trace_field"),
        "cell_readiness_summary_records": _summary(refreshed, "cell_readiness_class"),
        "gate_records": [
            {"gate": "p1_actionability_matrix_available", "passed": p1_ok, "threshold_relation": "boolean", "value": int(p1_ok), "threshold_value": 1},
            {"gate": "p0_1_trace_gap_audit_available", "passed": trace_ok, "threshold_relation": "boolean", "value": int(trace_ok), "threshold_value": 1},
            {"gate": "trace_gap_category_coverage_complete", "passed": coverage_ok, "threshold_relation": "boolean", "value": int(coverage_ok), "threshold_value": 1},
            {"gate": "matrix_natural_key_unique", "passed": matrix_ok, "threshold_relation": "boolean", "value": int(matrix_ok), "threshold_value": 1},
            {"gate": "causal_matrix_not_mutated", "passed": causal_ok, "threshold_relation": "boolean", "value": int(causal_ok), "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "p1_causal_matrix_refreshed_with_p0_1_trace_readiness_without_policy_authorization" if status == "actionability_matrix_refresh_pass" else "required_inputs_unavailable",
            "authorization": "scheduler_dataset_export_and_support_trace_input_design_only",
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
    report["gate_records"].append({"gate": "forbidden_scan_pass", "passed": report["forbidden_scan"]["status"] == "pass", "threshold_relation": "boolean", "value": int(report["forbidden_scan"]["status"] == "pass"), "threshold_value": 1})
    return report


def _check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    sample = {"trace_field": "action_cost_trace", "cell_readiness_class": "blocked_private_export"}
    checks = [
        _check("status_vocab_nonempty", bool(STATUSES)),
        _check("readiness_vocab_exact", len(READINESS_CLASSES) == 6),
        _check("p1_matrix_builder_has_72_rows", len(p1._build_actionability_matrix()) == 72),
        _check("readiness_private_export", _readiness("direct_actionable", "private_only_needs_public_export") == "blocked_private_export"),
        _check("readiness_not_applicable", _readiness("not_actionable_by_layer", "missing_trace") == "not_applicable_by_layer"),
        _check("scanner_accepts_sample", tg._scan_summary(sample)["status"] == "pass"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P0-2 actionability matrix refresh")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p1-artifact", type=Path, default=DEFAULT_P1)
    parser.add_argument("--trace-gap-artifact", type=Path, default=DEFAULT_TRACE_GAP)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, cells={len(report['refreshed_actionability_matrix_records'])})")


if __name__ == "__main__":
    main()
