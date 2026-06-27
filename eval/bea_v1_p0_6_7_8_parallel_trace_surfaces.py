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


DEFAULT_TRACE_GAP = Path("artifacts/bea_v1_trace_gap_audit/bea_v1_trace_gap_audit_report.json")
DEFAULT_P0_2 = Path("artifacts/bea_v1_p0_2_actionability_matrix_refresh/bea_v1_p0_2_actionability_matrix_refresh_report.json")

CONFIGS: dict[str, dict[str, Any]] = {
    "p0_6": {
        "phase": "BEA-v1-P0-6",
        "trace_field": "same_file_redundancy_trace",
        "category": "redundant_same_file_candidates",
        "schema_version": "bea_v1_p0_6_same_file_redundancy_trace_surface.v1",
        "claim_level": "bea_v1_p0_6_same_file_redundancy_trace_surface_only",
        "mode": "bea_v1_p0_6_same_file_redundancy_trace_surface",
        "status_pass": "same_file_redundancy_trace_surface_contract_pass",
        "status_private": "same_file_redundancy_trace_surface_private_rows_pass",
        "status_no_go": "no_go_same_file_redundancy_trace_inputs_unavailable",
        "out": Path("artifacts/bea_v1_p0_6_same_file_redundancy_trace_surface/bea_v1_p0_6_same_file_redundancy_trace_surface_report.json"),
        "record_key": "same_file_redundancy_trace_contract_records",
        "summary_key": "same_file_redundancy_summary_records",
        "private_schema": "bea_v1_p0_6_same_file_redundancy_private_trace.v1",
        "authorization": "same_file_redundancy_trace_surface_or_private_trace_validation_only",
        "fields": {
            "source_language_bucket": "unknown_not_exported",
            "duplicate_pressure_bucket": "unknown_missing_private_trace",
            "action_arm": "unknown_not_exported",
            "topk_file_diversity_bucket": "unknown_missing_private_trace",
            "same_file_candidate_count_bucket": "unknown_missing_private_trace",
            "gold_file_displacement_bucket": "unknown_missing_private_trace",
            "marginal_utility_bucket": "unknown_missing_private_trace",
        },
    },
    "p0_7": {
        "phase": "BEA-v1-P0-7",
        "trace_field": "risk_penalty_trace",
        "category": "risk_penalty_removed_gold",
        "schema_version": "bea_v1_p0_7_risk_penalty_trace_surface.v1",
        "claim_level": "bea_v1_p0_7_risk_penalty_trace_surface_only",
        "mode": "bea_v1_p0_7_risk_penalty_trace_surface",
        "status_pass": "risk_penalty_trace_surface_contract_pass",
        "status_private": "risk_penalty_trace_surface_private_rows_pass",
        "status_no_go": "no_go_risk_penalty_trace_inputs_unavailable",
        "out": Path("artifacts/bea_v1_p0_7_risk_penalty_trace_surface/bea_v1_p0_7_risk_penalty_trace_surface_report.json"),
        "record_key": "risk_penalty_trace_contract_records",
        "summary_key": "risk_penalty_summary_records",
        "private_schema": "bea_v1_p0_7_risk_penalty_private_trace.v1",
        "authorization": "risk_penalty_trace_surface_or_private_trace_validation_only",
        "fields": {
            "risk_class": "mechanism_blind_spot",
            "risk_policy_bucket": "risk_penalty_unknown",
            "removed_gold_bucket": "unknown_removed_state",
            "replacement_bucket": "unknown_replacement",
            "action_arm": "unknown_not_exported",
            "counterfactual_keep_bucket": "unknown_missing_private_trace",
            "topk_effect_bucket": "unknown_missing_private_trace",
        },
    },
    "p0_8": {
        "phase": "BEA-v1-P0-8",
        "trace_field": "ordered_prefix_stop_trace",
        "category": "early_stop_too_early",
        "schema_version": "bea_v1_p0_8_ordered_prefix_stop_trace_surface.v1",
        "claim_level": "bea_v1_p0_8_ordered_prefix_stop_trace_surface_only",
        "mode": "bea_v1_p0_8_ordered_prefix_stop_trace_surface",
        "status_pass": "ordered_prefix_stop_trace_surface_contract_pass",
        "status_private": "ordered_prefix_stop_trace_surface_private_rows_pass",
        "status_no_go": "no_go_ordered_prefix_stop_trace_inputs_unavailable",
        "out": Path("artifacts/bea_v1_p0_8_ordered_prefix_stop_trace_surface/bea_v1_p0_8_ordered_prefix_stop_trace_surface_report.json"),
        "record_key": "ordered_prefix_stop_trace_contract_records",
        "summary_key": "ordered_prefix_stop_summary_records",
        "private_schema": "bea_v1_p0_8_ordered_prefix_stop_private_trace.v1",
        "authorization": "ordered_prefix_stop_trace_surface_or_private_trace_validation_only",
        "aliases": ["stop_decision_trace"],
        "fields": {
            "arm_name": "unknown_not_exported",
            "stop_reason": "unknown_missing_private_trace",
            "prefix_cost_bucket": "unknown_missing_private_trace",
            "marginal_gain_bucket": "unknown_missing_private_trace",
            "prefix_position_bucket": "unknown_missing_private_trace",
            "budget_remaining_bucket": "unknown_missing_private_trace",
            "counterfactual_continue_bucket": "unknown_missing_private_trace",
        },
    },
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


def _summary(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in records)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _trace_gap_row(trace_gap: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    rows = trace_gap.get("trace_gap_records", [])
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if isinstance(row, dict) and row.get("trace_field") == cfg["trace_field"] and row.get("category") == cfg["category"]:
            return row
    return {}


def _matrix_rows(p0_2: dict[str, Any], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows = p0_2.get("refreshed_actionability_matrix_records", [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict) and row.get("trace_field") == cfg["trace_field"] and row.get("failure_category") == cfg["category"]]


def _contract_records(rows: list[dict[str, Any]], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(sorted(rows, key=lambda r: str(r.get("action_layer", "")))):
        base = {
            "anonymous_contract_id": f"{cfg['phase'].lower().replace('bea-v1-', '').replace('-', '')}_{i:04d}",
            "row_kind": "trace_surface_contract_unpopulated",
            "failure_category": cfg["category"],
            "action_layer": str(row.get("action_layer", "") or ""),
            "trace_field": cfg["trace_field"],
            "cell_readiness_class": str(row.get("cell_readiness_class", "") or ""),
            "cell_blocker_reason": str(row.get("cell_blocker_reason", "") or ""),
            "private_schema_required": cfg["private_schema"],
            "trace_basis": "contract_from_p0_1_p0_2_no_private_rows_supplied",
            "publication_boundary": "scanner_validated_sanitized_rows_without_source_linkable_payloads",
        }
        base.update(cfg["fields"])
        out.append(base)
    return out


def _private_manifest(cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "manifest_name": f"{cfg['mode']}_private_trace_input",
        "schema_version": cfg["private_schema"],
        "record_count": 0,
        "records_written": False,
        "path_publicly_serialized": False,
        "storage_class": "project_ignored_private_jsonl_optional",
    }


def _build_report(cfg: dict[str, Any], args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    trace_gap, trace_status = _load_json(args.trace_gap_artifact)
    p0_2, p0_2_status = _load_json(args.p0_2_artifact)
    gap_row = _trace_gap_row(trace_gap, cfg)
    matrix = _matrix_rows(p0_2, cfg)
    records = _contract_records(matrix, cfg)
    trace_ok = trace_status == "pass" and trace_gap.get("status") == "trace_gap_audit_pass" and trace_gap.get("forbidden_scan", {}).get("status") == "pass" and bool(gap_row)
    p0_2_ok = p0_2_status == "pass" and p0_2.get("status") == "actionability_matrix_refresh_pass" and p0_2.get("forbidden_scan", {}).get("status") == "pass"
    matrix_ok = len(matrix) in {3, 6} and bool(records)
    contract_ok = all(c["passed"] for c in checks) and trace_ok and p0_2_ok and matrix_ok
    status = cfg["status_pass"] if contract_ok else cfg["status_no_go"]
    report: dict[str, Any] = {
        "schema_version": cfg["schema_version"],
        "generated_by": "eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py",
        "generated_at": _now_iso(),
        "claim_level": cfg["claim_level"],
        "status": status,
        "mode": cfg["mode"],
        "phase": cfg["phase"],
        "trace_field": cfg["trace_field"],
        "trace_aliases": cfg.get("aliases", []),
        "failure_reason_category": "" if contract_ok else "required_input_artifact_unavailable_or_unexpected_status",
        "status_vocabulary": [cfg["status_pass"], cfg["status_private"], cfg["status_no_go"], "fail_forbidden_scan", "fail_schema_contract"],
        "self_test_passed": all(c["passed"] for c in checks),
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": [
            {"input_artifact": "p0_1_trace_gap_audit", "load_status": trace_status, "source_status": str(trace_gap.get("status", "") or ""), "source_schema": str(trace_gap.get("schema_version", "") or ""), "forbidden_scan_status": str(trace_gap.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(trace_gap.get("forbidden_scan"), dict) else "not_reported")},
            {"input_artifact": "p0_2_actionability_matrix_refresh", "load_status": p0_2_status, "source_status": str(p0_2.get("status", "") or ""), "source_schema": str(p0_2.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_2.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_2.get("forbidden_scan"), dict) else "not_reported")},
        ],
        "trace_requirement_records": [{
            "failure_category": cfg["category"],
            "trace_field": cfg["trace_field"],
            "trace_availability": str(gap_row.get("trace_availability", "") or ""),
            "trace_evidence_basis": str(gap_row.get("evidence_basis", "") or ""),
            "minimum_public_shape": str(gap_row.get("minimum_public_shape", "") or ""),
            "publication_boundary": str(gap_row.get("publication_boundary", "") or ""),
        }],
        cfg["record_key"]: records,
        cfg["summary_key"]: _summary(records, "action_layer"),
        "private_trace_manifest_records": [_private_manifest(cfg)],
        "gate_records": [
            {"gate": "p0_1_trace_gap_artifact_available", "passed": trace_ok, "threshold_relation": "boolean", "value": int(trace_ok), "threshold_value": 1},
            {"gate": "p0_2_matrix_artifact_available", "passed": p0_2_ok, "threshold_relation": "boolean", "value": int(p0_2_ok), "threshold_value": 1},
            {"gate": "trace_contract_records_buildable", "passed": matrix_ok, "threshold_relation": "nonzero", "value": len(records), "threshold_value": 1},
            {"gate": "private_trace_rows_full_valid", "passed": False, "threshold_relation": "boolean_optional", "value": 0, "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "trace_surface_contract_ready_without_private_rows" if contract_ok else "required_inputs_unavailable",
            "authorization": cfg["authorization"],
            "implementation_authorized": False,
            "selector_or_reranker_authorized": False,
            "v1_a_authorized": False,
            "p5_authorized": False,
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
    sample = _contract_records([{"action_layer": "file_selector", "cell_readiness_class": "blocked_missing_trace", "cell_blocker_reason": "requires_trace"}], CONFIGS["p0_7"])[0]
    checks = [
        _check("three_configs_present", set(CONFIGS) == {"p0_6", "p0_7", "p0_8"}),
        _check("sample_has_no_raw_payload", all(k not in sample for k in ("path", "candidate", "rank", "score", "snippet", "private_record_id"))),
        _check("sample_scanner_pass", tg._scan_summary({"records": [sample]})["status"] == "pass"),
        _check("scanner_rejects_forbidden_key", tg._scan_summary({"private_record_id": "x"})["status"] == "fail"),
        _check("p0_8_alias_present", "stop_decision_trace" in CONFIGS["p0_8"].get("aliases", [])),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P0-6/P0-7/P0-8 parallel trace surfaces")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--phase", choices=["all", *CONFIGS.keys()], default="all")
    parser.add_argument("--trace-gap-artifact", type=Path, default=DEFAULT_TRACE_GAP)
    parser.add_argument("--p0-2-artifact", type=Path, default=DEFAULT_P0_2)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for check in checks:
            print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    selected = CONFIGS if args.phase == "all" else {args.phase: CONFIGS[args.phase]}
    for key, cfg in selected.items():
        report = _build_report(cfg, args, checks)
        if report.get("forbidden_scan", {}).get("status") != "pass":
            raise SystemExit(f"{key}: forbidden content leak; refusing to write artifact")
        _write_json(cfg["out"], report)
        print(f"wrote {key} artifact (status={report['status']}, records={len(report[cfg['record_key']])})")


if __name__ == "__main__":
    main()
