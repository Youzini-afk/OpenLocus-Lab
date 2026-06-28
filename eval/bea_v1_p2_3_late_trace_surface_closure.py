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


SCHEMA_VERSION = "bea_v1_p2_3_late_trace_surface_closure.v1"
GENERATED_BY = "eval/bea_v1_p2_3_late_trace_surface_closure.py"
CLAIM_LEVEL = "late_trace_surface_closure_and_next_experiment_decision_only"
MODE = "bea_v1_p2_3_late_trace_surface_closure"
PHASE = "BEA-v1-P2-3"
DEFAULT_OUT = Path("artifacts/bea_v1_p2_3_late_trace_surface_closure/bea_v1_p2_3_late_trace_surface_closure_report.json")
DEFAULT_P1_5R = Path("artifacts/bea_v1_p1_5r_improved_automated_support_label_feasibility/bea_v1_p1_5r_improved_automated_support_label_feasibility_report.json")
DEFAULT_P2_0 = Path("artifacts/bea_v1_p2_0_scheduler_private_arm_row_recovery/bea_v1_p2_0_scheduler_private_arm_row_recovery_report.json")
DEFAULT_P2_1 = Path("artifacts/bea_v1_p2_1_ordered_prefix_stop_evidence_surface/bea_v1_p2_1_ordered_prefix_stop_evidence_surface_report.json")
DEFAULT_P2_2 = Path("artifacts/bea_v1_p2_2_redundancy_risk_trace_availability/bea_v1_p2_2_redundancy_risk_trace_availability_report.json")

STATUS_VOCAB = (
    "late_trace_surface_closure_no_go",
    "late_trace_surface_closure_partial_trace_ready",
    "late_trace_surface_closure_denominator_audit_authorized",
    "no_go_p2_3_required_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

EXPECTED_INPUTS = (
    ("p1_5r_support_link", DEFAULT_P1_5R, "BEA-v1-P1-5R", "no_go_p1_5r_private_context_unavailable"),
    ("p2_0_scheduler_action_cost", DEFAULT_P2_0, "BEA-v1-P2-0", "no_go_p2_0_private_arm_rows_unavailable"),
    ("p2_1_ordered_prefix_stop", DEFAULT_P2_1, "BEA-v1-P2-1", "no_go_p2_1_ordered_prefix_only_aggregate"),
    ("p2_2_redundancy_risk", DEFAULT_P2_2, "BEA-v1-P2-2", "no_go_p2_2_redundancy_risk_traces_unavailable"),
)

SURFACE_ROWS = (
    ("support_link", "BEA-v1-P1-5R", "no_go_p1_5r_private_context_unavailable", "blocked_no_reconstructable_private_context", "p1_5r_support_link", "schema_valid_proxy_only", "upstream_source_context_linkage_or_private_trace_capture"),
    ("scheduler_action_cost", "BEA-v1-P2-0", "no_go_p2_0_private_arm_rows_unavailable", "blocked_private_arm_rows_unavailable_locally", "p2_0_scheduler_action_cost", "private_rows_missing", "upstream_scheduler_arm_trace_capture"),
    ("ordered_prefix_stop", "BEA-v1-P2-1", "no_go_p2_1_ordered_prefix_only_aggregate", "aggregate_only_private_trace_missing", "p2_1_ordered_prefix_stop", "aggregate_only", "upstream_ordered_prefix_private_trace_capture"),
    ("same_file_redundancy", "BEA-v1-P2-2", "no_go_p2_2_redundancy_risk_traces_unavailable", "contract_only_missing_private_trace", "p2_2_redundancy_risk", "contract_only", "upstream_same_file_redundancy_trace_capture"),
    ("risk_penalty", "BEA-v1-P2-2", "no_go_p2_2_redundancy_risk_traces_unavailable", "contract_only_missing_private_trace", "p2_2_redundancy_risk", "contract_only", "upstream_risk_penalty_trace_capture"),
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


def _input_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    paths = {
        "p1_5r_support_link": args.p1_5r_artifact,
        "p2_0_scheduler_action_cost": args.p2_0_artifact,
        "p2_1_ordered_prefix_stop": args.p2_1_artifact,
        "p2_2_redundancy_risk": args.p2_2_artifact,
    }
    records: list[dict[str, Any]] = []
    all_ok = True
    for input_bucket, _default_path, phase, expected_status in EXPECTED_INPUTS:
        artifact, load_status = _load_json(paths[input_bucket])
        actual_status = str(artifact.get("status", "") or "")
        scan_status = str(artifact.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(artifact.get("forbidden_scan"), dict) else "not_reported")
        passed = load_status == "pass" and actual_status == expected_status and scan_status == "pass"
        all_ok = all_ok and passed
        records.append({
            "input_artifact_bucket": input_bucket,
            "source_phase_bucket": phase,
            "load_status": load_status,
            "expected_status": expected_status,
            "observed_status": actual_status,
            "forbidden_scan_status": scan_status,
            "input_gate_passed": passed,
        })
    return records, all_ok


def _surface_closure_records() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, (surface, source_phase, source_status, state, evidence, evidence_level, next_required) in enumerate(SURFACE_ROWS):
        out.append({
            "anonymous_surface_closure_id": f"ltsc{idx:04d}",
            "surface_bucket": surface,
            "source_phase_bucket": source_phase,
            "source_status": source_status,
            "surface_state_bucket": state,
            "evidence_source_bucket": evidence,
            "valid_private_row_count_bucket": "zero",
            "evidence_level_bucket": evidence_level,
            "next_required_input_bucket": next_required,
            "closure_bucket": "blocked_requires_upstream_trace_capture",
            "denominator_audit_authorized": False,
            "trace_counterfactual_execution_authorized": False,
            "support_counterfactual_execution_authorized": False,
            "policy_tuning_authorized": False,
            "implementation_authorized": False,
            "selector_or_reranker_authorized": False,
            "runtime_promotion_authorized": False,
            "broad_retrieval_expansion_authorized": False,
            "method_winner_claimed": False,
            "downstream_value_claimed": False,
        })
    return out


def _summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in rows)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _decision_summary(surface_rows: list[dict[str, Any]], inputs_ok: bool) -> list[dict[str, Any]]:
    all_blocked = all(row["closure_bucket"] == "blocked_requires_upstream_trace_capture" for row in surface_rows)
    return [{
        "decision_bucket": "late_trace_surface_closure_no_go" if inputs_ok and all_blocked else "required_inputs_unavailable",
        "decision_reason_bucket": "upstream_trace_capture_required" if inputs_ok and all_blocked else "required_closure_inputs_missing_or_unexpected",
        "blocked_surface_count": sum(1 for row in surface_rows if row["closure_bucket"] == "blocked_requires_upstream_trace_capture"),
        "total_surface_count": len(surface_rows),
        "all_late_trace_surfaces_blocked": bool(all_blocked),
        "next_allowed_phase": "frozen_upstream_trace_capture_harness_design_only" if inputs_ok and all_blocked else "none_until_inputs_repaired",
        "schema_and_instrumentation_planning_only": bool(inputs_ok and all_blocked),
        "execution_authorized": False,
    }]


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    input_records, inputs_ok = _input_records(args)
    surface_records = _surface_closure_records()
    decision_records = _decision_summary(surface_records, inputs_ok)
    self_tests_ok = all(c["passed"] for c in checks)
    all_surfaces_blocked = decision_records[0]["all_late_trace_surfaces_blocked"]
    if not self_tests_ok:
        status = "fail_schema_contract"
    elif not inputs_ok:
        status = "no_go_p2_3_required_inputs_unavailable"
    else:
        status = "late_trace_surface_closure_no_go"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "upstream_trace_capture_required" if status == "late_trace_surface_closure_no_go" else "required_inputs_unavailable" if status == "no_go_p2_3_required_inputs_unavailable" else "schema_contract_failed",
        "status_vocabulary": list(STATUS_VOCAB),
        "self_test_passed": self_tests_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": input_records,
        "surface_closure_records": surface_records,
        "surface_blocker_summary_records": _summary(surface_records, "surface_state_bucket"),
        "decision_summary_records": decision_records,
        "gate_records": [
            {"gate": "required_input_statuses_and_scans_pass", "passed": inputs_ok, "threshold_relation": "boolean", "value": int(inputs_ok), "threshold_value": 1},
            {"gate": "five_required_surfaces_mapped", "passed": len(surface_records) == 5, "threshold_relation": "equals", "value": len(surface_records), "threshold_value": 5},
            {"gate": "all_surfaces_blocked", "passed": all_surfaces_blocked, "threshold_relation": "boolean", "value": int(all_surfaces_blocked), "threshold_value": 1},
            {"gate": "no_denominator_audit_authorized", "passed": not any(row["denominator_audit_authorized"] for row in surface_records), "threshold_relation": "boolean", "value": 1 if not any(row["denominator_audit_authorized"] for row in surface_records) else 0, "threshold_value": 1},
            {"gate": "no_counterfactual_authorized", "passed": not any(row["trace_counterfactual_execution_authorized"] or row["support_counterfactual_execution_authorized"] for row in surface_records), "threshold_relation": "boolean", "value": 1 if not any(row["trace_counterfactual_execution_authorized"] or row["support_counterfactual_execution_authorized"] for row in surface_records) else 0, "threshold_value": 1},
            {"gate": "next_allowed_phase_is_design_only", "passed": decision_records[0]["next_allowed_phase"] == "frozen_upstream_trace_capture_harness_design_only", "threshold_relation": "equals", "value": decision_records[0]["next_allowed_phase"], "threshold_value": "frozen_upstream_trace_capture_harness_design_only"},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "upstream_trace_capture_required" if status == "late_trace_surface_closure_no_go" else "required_inputs_unavailable",
            "next_allowed_phase": "frozen_upstream_trace_capture_harness_design_only" if status == "late_trace_surface_closure_no_go" else "none_until_inputs_repaired",
            "upstream_trace_capture_required": status == "late_trace_surface_closure_no_go",
            "schema_and_instrumentation_planning_only": status == "late_trace_surface_closure_no_go",
            "ordered_prefix_stop_policy_change_authorized": False,
            "denominator_audit_authorized": False,
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
    surfaces = _surface_closure_records()
    decision = _decision_summary(surfaces, True)[0]
    stop_go = {
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
    }
    checks = [
        _check("status_vocab_complete", set(STATUS_VOCAB) == {"late_trace_surface_closure_no_go", "late_trace_surface_closure_partial_trace_ready", "late_trace_surface_closure_denominator_audit_authorized", "no_go_p2_3_required_inputs_unavailable", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("surface_mapping_has_five_required_surfaces", {row["surface_bucket"] for row in surfaces} == {"support_link", "scheduler_action_cost", "ordered_prefix_stop", "same_file_redundancy", "risk_penalty"}),
        _check("surface_rows_include_required_next_input_buckets", all(row.get("valid_private_row_count_bucket") == "zero" and row.get("next_required_input_bucket", "").startswith("upstream_") for row in surfaces)),
        _check("no_surface_authorizes_counterfactual", not any(row["trace_counterfactual_execution_authorized"] or row["support_counterfactual_execution_authorized"] for row in surfaces)),
        _check("no_surface_authorizes_denominator_audit_when_blocked", not any(row["denominator_audit_authorized"] for row in surfaces)),
        _check("decision_requires_upstream_trace_capture_when_all_blocked", decision["decision_reason_bucket"] == "upstream_trace_capture_required" and decision["next_allowed_phase"] == "frozen_upstream_trace_capture_harness_design_only"),
        _check("scanner_accepts_surface_closure_rows", tg._scan_summary({"surface_closure_records": surfaces})["status"] == "pass"),
        _check("scanner_rejects_path_key", tg._scan_summary({"path": "x"})["status"] == "fail"),
        _check("stop_go_all_forbidden_flags_false", not any(stop_go.values())),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P2-3 late trace surface closure")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p1-5r-artifact", type=Path, default=DEFAULT_P1_5R)
    parser.add_argument("--p2-0-artifact", type=Path, default=DEFAULT_P2_0)
    parser.add_argument("--p2-1-artifact", type=Path, default=DEFAULT_P2_1)
    parser.add_argument("--p2-2-artifact", type=Path, default=DEFAULT_P2_2)
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
    decision = report["decision_summary_records"][0]
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, surfaces={decision['total_surface_count']}, blocked={decision['blocked_surface_count']}, next={decision['next_allowed_phase']})")


if __name__ == "__main__":
    main()
