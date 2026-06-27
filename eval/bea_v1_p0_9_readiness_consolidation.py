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


SCHEMA_VERSION = "bea_v1_p0_9_readiness_consolidation.v1"
GENERATED_BY = "eval/bea_v1_p0_9_readiness_consolidation.py"
CLAIM_LEVEL = "bea_v1_p0_9_readiness_consolidation_only"
MODE = "bea_v1_p0_9_readiness_consolidation"
PHASE = "BEA-v1-P0-9"
DEFAULT_OUT = Path("artifacts/bea_v1_p0_9_readiness_consolidation/bea_v1_p0_9_readiness_consolidation_report.json")

INPUTS = (
    ("p0_1_trace_gap_audit", "artifacts/bea_v1_trace_gap_audit/bea_v1_trace_gap_audit_report.json", "trace_gap_audit_pass", "trace_gap_audit"),
    ("p0_2_actionability_matrix_refresh", "artifacts/bea_v1_p0_2_actionability_matrix_refresh/bea_v1_p0_2_actionability_matrix_refresh_report.json", "actionability_matrix_refresh_pass", "matrix_refresh"),
    ("p0_3_scheduler_dataset_export", "artifacts/bea_v1_p0_3_scheduler_dataset_export/bea_v1_p0_3_scheduler_dataset_export_report.json", "scheduler_dataset_export_contract_pass", "contract_only"),
    ("p0_4_support_link_input_design", "artifacts/bea_v1_p0_4_support_link_input_design/bea_v1_p0_4_support_link_input_design_report.json", "support_link_input_design_pass", "contract_only"),
    ("p0_5_support_link_labeling_harness", "artifacts/bea_v1_p0_5_support_link_labeling_harness/bea_v1_p0_5_support_link_labeling_harness_report.json", "support_link_labeling_harness_contract_pass", "contract_only"),
    ("p0_6_same_file_redundancy_trace_surface", "artifacts/bea_v1_p0_6_same_file_redundancy_trace_surface/bea_v1_p0_6_same_file_redundancy_trace_surface_report.json", "same_file_redundancy_trace_surface_contract_pass", "contract_only"),
    ("p0_7_risk_penalty_trace_surface", "artifacts/bea_v1_p0_7_risk_penalty_trace_surface/bea_v1_p0_7_risk_penalty_trace_surface_report.json", "risk_penalty_trace_surface_contract_pass", "contract_only"),
    ("p0_8_ordered_prefix_stop_trace_surface", "artifacts/bea_v1_p0_8_ordered_prefix_stop_trace_surface/bea_v1_p0_8_ordered_prefix_stop_trace_surface_report.json", "ordered_prefix_stop_trace_surface_contract_pass", "contract_only"),
)

STATUSES = (
    "readiness_consolidation_pass_no_experiment_authorized",
    "readiness_consolidation_pass_labeling_authorized_only",
    "no_go_readiness_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)


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


def _count_rows(data: dict[str, Any], suffixes: tuple[str, ...]) -> int:
    total = 0
    for key, value in data.items():
        if any(key.endswith(suffix) for suffix in suffixes) and isinstance(value, list):
            total += len(value)
    return total


def _input_records() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, raw_path, expected, readiness in INPUTS:
        data, load_status = _load_json(Path(raw_path))
        scan_status = data.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(data.get("forbidden_scan"), dict) else "not_reported"
        status = str(data.get("status", "") or "")
        rows.append({
            "input_artifact": name,
            "load_status": load_status,
            "source_status": status,
            "expected_status": expected,
            "source_schema": str(data.get("schema_version", "") or ""),
            "forbidden_scan_status": str(scan_status),
            "readiness_kind": readiness,
            "status_matches_expected": load_status == "pass" and status == expected,
            "contract_or_analysis_record_count": _count_rows(data, ("records",)),
        })
    return rows


def _decision_records(inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    all_loaded = all(row["status_matches_expected"] and row["forbidden_scan_status"] == "pass" for row in inputs)
    contract_count = sum(1 for row in inputs if row["readiness_kind"] == "contract_only")
    populated_private_count = 0
    return [
        {
            "decision_id": "next_support_labeling",
            "decision": "authorized_private_labeling_only" if all_loaded else "blocked_inputs_unavailable",
            "required_ready_surfaces": "p0_4_p0_5",
            "required_private_rows": "not_required_to_start_labeling",
            "counterfactual_execution_authorized": False,
            "policy_tuning_authorized": False,
        },
        {
            "decision_id": "next_support_counterfactual",
            "decision": "blocked_missing_private_support_labels",
            "required_ready_surfaces": "p0_4_p0_5_private_labels_full_valid",
            "required_private_rows": "support_link_private_labels",
            "counterfactual_execution_authorized": False,
            "policy_tuning_authorized": False,
        },
        {
            "decision_id": "next_trace_counterfactuals",
            "decision": "blocked_missing_private_trace_rows",
            "required_ready_surfaces": "p0_6_p0_7_p0_8_private_rows_full_valid",
            "required_private_rows": "redundancy_risk_stop_private_traces",
            "counterfactual_execution_authorized": False,
            "policy_tuning_authorized": False,
        },
        {
            "decision_id": "next_policy_or_runtime_experiment",
            "decision": "blocked_contracts_are_not_mechanism_evidence",
            "contract_only_surface_count": contract_count,
            "populated_private_surface_count": populated_private_count,
            "counterfactual_execution_authorized": False,
            "policy_tuning_authorized": False,
        },
    ]


def _summary(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in records)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    inputs = _input_records()
    all_inputs_ok = all(row["status_matches_expected"] and row["forbidden_scan_status"] == "pass" for row in inputs)
    decisions = _decision_records(inputs)
    status = "readiness_consolidation_pass_labeling_authorized_only" if all_inputs_ok and all(c["passed"] for c in checks) else "no_go_readiness_inputs_unavailable"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "" if status.startswith("readiness_consolidation_pass") else "required_input_artifact_unavailable_or_unexpected_status",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": all(c["passed"] for c in checks),
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": inputs,
        "readiness_summary_records": _summary(inputs, "readiness_kind"),
        "scan_summary_records": _summary(inputs, "forbidden_scan_status"),
        "next_experiment_decision_records": decisions,
        "gate_records": [
            {"gate": "all_p0_inputs_loaded", "passed": all(row["load_status"] == "pass" for row in inputs), "threshold_relation": "boolean", "value": int(all(row["load_status"] == "pass" for row in inputs)), "threshold_value": 1},
            {"gate": "all_p0_statuses_expected", "passed": all(row["status_matches_expected"] for row in inputs), "threshold_relation": "boolean", "value": int(all(row["status_matches_expected"] for row in inputs)), "threshold_value": 1},
            {"gate": "all_p0_scanners_pass", "passed": all(row["forbidden_scan_status"] == "pass" for row in inputs), "threshold_relation": "boolean", "value": int(all(row["forbidden_scan_status"] == "pass" for row in inputs)), "threshold_value": 1},
            {"gate": "private_rows_populated_for_counterfactual", "passed": False, "threshold_relation": "boolean_required_for_counterfactual", "value": 0, "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "p0_contracts_consolidated_private_labeling_only" if status.startswith("readiness_consolidation_pass") else "required_inputs_unavailable",
            "authorization": "private_labeling_and_private_trace_validation_only",
            "support_labeling_authorized": status.startswith("readiness_consolidation_pass"),
            "support_counterfactual_execution_authorized": False,
            "trace_counterfactual_execution_authorized": False,
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
    sample = {"decision_id": "x", "decision": "blocked_contracts_are_not_mechanism_evidence"}
    checks = [
        _check("input_manifest_count", len(INPUTS) == 8),
        _check("status_vocab_nonempty", bool(STATUSES)),
        _check("scanner_accepts_decision_sample", tg._scan_summary({"next_experiment_decision_records": [sample]})["status"] == "pass"),
        _check("scanner_rejects_private_key", tg._scan_summary({"private_record_id": "x"})["status"] == "fail"),
        _check("p0_6_to_p0_8_present", all(any(row[0].startswith(f"p0_{i}") for row in INPUTS) for i in (6, 7, 8))),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P0-9 readiness consolidation")
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
    report = _build_report(args, checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    _write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, inputs={len(report['input_artifact_records'])})")


if __name__ == "__main__":
    main()
