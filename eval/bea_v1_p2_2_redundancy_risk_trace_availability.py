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


SCHEMA_VERSION = "bea_v1_p2_2_redundancy_risk_trace_availability.v1"
GENERATED_BY = "eval/bea_v1_p2_2_redundancy_risk_trace_availability.py"
CLAIM_LEVEL = "redundancy_risk_trace_availability_feasibility_audit_only"
MODE = "bea_v1_p2_2_redundancy_risk_trace_availability"
PHASE = "BEA-v1-P2-2"
DEFAULT_OUT = Path("artifacts/bea_v1_p2_2_redundancy_risk_trace_availability/bea_v1_p2_2_redundancy_risk_trace_availability_report.json")
DEFAULT_P0_6 = Path("artifacts/bea_v1_p0_6_same_file_redundancy_trace_surface/bea_v1_p0_6_same_file_redundancy_trace_surface_report.json")
DEFAULT_P0_7 = Path("artifacts/bea_v1_p0_7_risk_penalty_trace_surface/bea_v1_p0_7_risk_penalty_trace_surface_report.json")
DEFAULT_P0_1 = Path("artifacts/bea_v1_trace_gap_audit/bea_v1_trace_gap_audit_report.json")
DEFAULT_P0_2 = Path("artifacts/bea_v1_p0_2_actionability_matrix_refresh/bea_v1_p0_2_actionability_matrix_refresh_report.json")
DEFAULT_SAME_FILE_PRIVATE = Path(".openlocus/research-private/bea_v1_p0_6_same_file_redundancy_private_trace.jsonl")
DEFAULT_RISK_PRIVATE = Path(".openlocus/research-private/bea_v1_p0_7_risk_penalty_private_trace.jsonl")

STATUSES = (
    "redundancy_risk_trace_availability_pass",
    "same_file_redundancy_private_trace_pass",
    "risk_penalty_private_trace_pass",
    "partial_redundancy_or_risk_trace_available",
    "no_go_p2_2_redundancy_risk_traces_unavailable",
    "no_go_p2_2_private_trace_schema_invalid",
    "no_go_p2_2_required_inputs_unavailable",
    "fail_forbidden_scan",
    "fail_schema_contract",
)

SAME_SCHEMA = "bea_v1_p0_6_same_file_redundancy_private_trace.v1"
RISK_SCHEMA = "bea_v1_p0_7_risk_penalty_private_trace.v1"


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


def _safe_private_or_tmp(path: Path) -> bool:
    try:
        resolved = path.resolve()
        private_root = Path(".openlocus/research-private").resolve()
        tmp_root = Path("/tmp").resolve()
        return private_root == resolved or private_root in resolved.parents or tmp_root == resolved or tmp_root in resolved.parents
    except Exception:
        return False


def _read_jsonl(path: Path | None) -> tuple[list[dict[str, Any]], str]:
    if path is None:
        return [], "not_supplied"
    if not _safe_private_or_tmp(path):
        return [], "outside_allowed_private_or_tmp_root"
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


def _surface_ok(artifact: dict[str, Any], load_status: str, expected_statuses: set[str]) -> bool:
    return load_status == "pass" and artifact.get("status") in expected_statuses and artifact.get("forbidden_scan", {}).get("status") == "pass"


def _contract_count(artifact: dict[str, Any], key: str) -> int:
    rows = artifact.get(key, [])
    return len(rows) if isinstance(rows, list) else 0


def _manifest_count_zero(artifact: dict[str, Any]) -> bool:
    rows = artifact.get("private_trace_manifest_records", [])
    if not isinstance(rows, list) or not rows:
        return False
    return all(isinstance(row, dict) and int(row.get("record_count", 0) or 0) == 0 for row in rows)


def _trace_availability(artifact: dict[str, Any]) -> str:
    rows = artifact.get("trace_requirement_records", [])
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        return str(rows[0].get("trace_availability", "unknown") or "unknown")
    return "unknown"


def _validate_private_rows(rows: list[dict[str, Any]], *, surface: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    schema = SAME_SCHEMA if surface == "same_file_redundancy" else RISK_SCHEMA
    required = (
        {"schema_version", "action_layer", "action_arm", "duplicate_pressure_bucket", "same_file_candidate_count_bucket", "topk_file_diversity_bucket", "gold_file_displacement_bucket", "marginal_utility_bucket"}
        if surface == "same_file_redundancy"
        else {"schema_version", "action_layer", "action_arm", "risk_class", "risk_policy_bucket", "removed_gold_bucket", "replacement_bucket", "topk_effect_bucket", "counterfactual_keep_bucket"}
    )
    valid: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        row_errors: list[str] = []
        if row.get("schema_version") != schema:
            row_errors.append("schema_version_mismatch")
        for key in required:
            if key not in row or row.get(key) in (None, ""):
                row_errors.append(f"{key}_missing")
        if row_errors:
            errors.append({"anonymous_error_id": f"{surface[:2]}e{i:04d}", "surface_bucket": surface, "error_bucket": "|".join(sorted(row_errors))})
        else:
            valid.append(row)
    return valid, errors


def _sanitize_private_rows(rows: list[dict[str, Any]], *, surface: str, start: int = 0) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if surface == "same_file_redundancy":
            out.append({
                "anonymous_trace_availability_id": f"rrta{start + i:04d}",
                "surface_bucket": surface,
                "action_layer_bucket": str(row.get("action_layer", "") or ""),
                "action_arm_bucket": str(row.get("action_arm", "") or ""),
                "duplicate_pressure_bucket": str(row.get("duplicate_pressure_bucket", "") or ""),
                "same_file_candidate_count_bucket": str(row.get("same_file_candidate_count_bucket", "") or ""),
                "topk_effect_or_diversity_bucket": str(row.get("topk_file_diversity_bucket", "") or ""),
                "gold_effect_bucket": str(row.get("gold_file_displacement_bucket", "") or ""),
                "marginal_or_counterfactual_bucket": str(row.get("marginal_utility_bucket", "") or ""),
                "trace_row_level_bucket": "private_trace_bucketed_row_valid",
            })
        else:
            out.append({
                "anonymous_trace_availability_id": f"rrta{start + i:04d}",
                "surface_bucket": surface,
                "action_layer_bucket": str(row.get("action_layer", "") or ""),
                "action_arm_bucket": str(row.get("action_arm", "") or ""),
                "risk_class_bucket": str(row.get("risk_class", "") or ""),
                "risk_policy_bucket": str(row.get("risk_policy_bucket", "") or ""),
                "removed_gold_bucket": str(row.get("removed_gold_bucket", "") or ""),
                "replacement_bucket": str(row.get("replacement_bucket", "") or ""),
                "topk_effect_or_diversity_bucket": str(row.get("topk_effect_bucket", "") or ""),
                "marginal_or_counterfactual_bucket": str(row.get("counterfactual_keep_bucket", "") or ""),
                "trace_row_level_bucket": "private_trace_bucketed_row_valid",
            })
    return out


def _summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key, "") or "") for row in rows)
    return [{key: name, "count": count} for name, count in sorted(counts.items())]


def _status_from_availability(*, self_tests_ok: bool, required_ok: bool, contracts_ok: bool, has_errors: bool, same_has: bool, risk_has: bool) -> str:
    if not self_tests_ok:
        return "fail_schema_contract"
    if not required_ok or not contracts_ok:
        return "no_go_p2_2_required_inputs_unavailable"
    if has_errors:
        return "no_go_p2_2_private_trace_schema_invalid"
    if same_has and risk_has:
        return "redundancy_risk_trace_availability_pass"
    if same_has:
        return "same_file_redundancy_private_trace_pass"
    if risk_has:
        return "risk_penalty_private_trace_pass"
    return "no_go_p2_2_redundancy_risk_traces_unavailable"


def _build_report(args: argparse.Namespace, checks: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter()
    p0_6, p0_6_load = _load_json(args.p0_6_artifact)
    p0_7, p0_7_load = _load_json(args.p0_7_artifact)
    p0_1, p0_1_load = _load_json(args.p0_1_artifact)
    p0_2, p0_2_load = _load_json(args.p0_2_artifact)
    same_rows, same_read = _read_jsonl(args.same_file_private_trace_jsonl)
    risk_rows, risk_read = _read_jsonl(args.risk_penalty_private_trace_jsonl)
    same_valid, same_errors = _validate_private_rows(same_rows, surface="same_file_redundancy") if same_read == "pass" else ([], [])
    risk_valid, risk_errors = _validate_private_rows(risk_rows, surface="risk_penalty") if risk_read == "pass" else ([], [])
    all_errors = same_errors + risk_errors
    sanitized = _sanitize_private_rows(same_valid, surface="same_file_redundancy", start=0) + _sanitize_private_rows(risk_valid, surface="risk_penalty", start=len(same_valid))

    p0_6_ok = _surface_ok(p0_6, p0_6_load, {"same_file_redundancy_trace_surface_contract_pass", "same_file_redundancy_trace_surface_private_rows_pass"})
    p0_7_ok = _surface_ok(p0_7, p0_7_load, {"risk_penalty_trace_surface_contract_pass", "risk_penalty_trace_surface_private_rows_pass"})
    p0_1_ok = p0_1_load == "pass" and p0_1.get("status") == "trace_gap_audit_pass" and p0_1.get("forbidden_scan", {}).get("status") == "pass"
    p0_2_ok = p0_2_load == "pass" and p0_2.get("status") == "actionability_matrix_refresh_pass" and p0_2.get("forbidden_scan", {}).get("status") == "pass"
    required_ok = p0_6_ok and p0_7_ok and p0_1_ok and p0_2_ok
    contracts_ok = _contract_count(p0_6, "same_file_redundancy_trace_contract_records") == 6 and _contract_count(p0_7, "risk_penalty_trace_contract_records") == 6
    manifests_zero = _manifest_count_zero(p0_6) and _manifest_count_zero(p0_7)
    missing_confirmed = _trace_availability(p0_6) == "missing_trace" and _trace_availability(p0_7) == "missing_trace"
    same_has = len(same_valid) >= 1
    risk_has = len(risk_valid) >= 1
    self_tests_ok = all(c["passed"] for c in checks)
    status = _status_from_availability(
        self_tests_ok=self_tests_ok,
        required_ok=required_ok,
        contracts_ok=contracts_ok,
        has_errors=bool(all_errors),
        same_has=same_has,
        risk_has=risk_has,
    )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now_iso(),
        "claim_level": CLAIM_LEVEL,
        "status": status,
        "mode": MODE,
        "phase": PHASE,
        "failure_reason_category": "traces_unavailable" if status == "no_go_p2_2_redundancy_risk_traces_unavailable" else "private_trace_schema_invalid" if status == "no_go_p2_2_private_trace_schema_invalid" else "required_inputs_unavailable" if status == "no_go_p2_2_required_inputs_unavailable" else "" if status in {"redundancy_risk_trace_availability_pass", "same_file_redundancy_private_trace_pass", "risk_penalty_private_trace_pass", "partial_redundancy_or_risk_trace_available"} else "schema_contract_failed",
        "status_vocabulary": list(STATUSES),
        "self_test_passed": self_tests_ok,
        "self_test_checks_total": len(checks),
        "self_test_checks_passed": sum(1 for c in checks if c["passed"]),
        "input_artifact_records": [
            {"input_artifact": "p0_6_same_file_redundancy_trace_surface", "load_status": p0_6_load, "source_status": str(p0_6.get("status", "") or ""), "source_schema": str(p0_6.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_6.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_6.get("forbidden_scan"), dict) else "not_reported")},
            {"input_artifact": "p0_7_risk_penalty_trace_surface", "load_status": p0_7_load, "source_status": str(p0_7.get("status", "") or ""), "source_schema": str(p0_7.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_7.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_7.get("forbidden_scan"), dict) else "not_reported")},
            {"input_artifact": "p0_1_trace_gap_audit", "load_status": p0_1_load, "source_status": str(p0_1.get("status", "") or ""), "source_schema": str(p0_1.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_1.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_1.get("forbidden_scan"), dict) else "not_reported")},
            {"input_artifact": "p0_2_actionability_matrix_refresh", "load_status": p0_2_load, "source_status": str(p0_2.get("status", "") or ""), "source_schema": str(p0_2.get("schema_version", "") or ""), "forbidden_scan_status": str(p0_2.get("forbidden_scan", {}).get("status", "not_reported") if isinstance(p0_2.get("forbidden_scan"), dict) else "not_reported")},
        ],
        "private_trace_manifest_records": [
            {"surface_bucket": "same_file_redundancy", "schema_version": SAME_SCHEMA, "read_status": same_read, "record_count": len(same_rows), "valid_record_count": len(same_valid), "error_count": len(same_errors), "path_publicly_serialized": False, "storage_class": "project_ignored_private_or_explicit_tmp_jsonl"},
            {"surface_bucket": "risk_penalty", "schema_version": RISK_SCHEMA, "read_status": risk_read, "record_count": len(risk_rows), "valid_record_count": len(risk_valid), "error_count": len(risk_errors), "path_publicly_serialized": False, "storage_class": "project_ignored_private_or_explicit_tmp_jsonl"},
        ],
        "availability_summary_records": [
            {"surface_bucket": "same_file_redundancy", "contract_record_count": _contract_count(p0_6, "same_file_redundancy_trace_contract_records"), "p0_contract_private_manifest_zero": _manifest_count_zero(p0_6), "private_trace_read_status": same_read, "valid_private_trace_count": len(same_valid), "availability_bucket": "private_trace_available" if same_has else "contract_only_private_trace_unavailable"},
            {"surface_bucket": "risk_penalty", "contract_record_count": _contract_count(p0_7, "risk_penalty_trace_contract_records"), "p0_contract_private_manifest_zero": _manifest_count_zero(p0_7), "private_trace_read_status": risk_read, "valid_private_trace_count": len(risk_valid), "availability_bucket": "private_trace_available" if risk_has else "contract_only_private_trace_unavailable"},
        ],
        "trace_gap_confirmation_records": [
            {"surface_bucket": "same_file_redundancy", "trace_field_bucket": "same_file_redundancy_trace", "failure_category_bucket": "redundant_same_file_candidates", "p0_trace_availability_bucket": _trace_availability(p0_6), "trace_evidence_basis_bucket": str((p0_6.get("trace_requirement_records", [{}]) or [{}])[0].get("trace_evidence_basis", "unknown") if isinstance(p0_6.get("trace_requirement_records"), list) and p0_6.get("trace_requirement_records") else "unknown")},
            {"surface_bucket": "risk_penalty", "trace_field_bucket": "risk_penalty_trace", "failure_category_bucket": "risk_penalty_removed_gold", "p0_trace_availability_bucket": _trace_availability(p0_7), "trace_evidence_basis_bucket": str((p0_7.get("trace_requirement_records", [{}]) or [{}])[0].get("trace_evidence_basis", "unknown") if isinstance(p0_7.get("trace_requirement_records"), list) and p0_7.get("trace_requirement_records") else "unknown")},
        ],
        "sanitized_private_trace_bucket_records": sanitized,
        "private_trace_error_summary_records": _summary(all_errors, "error_bucket"),
        "gate_records": [
            {"gate": "required_artifacts_load_and_scan", "passed": required_ok, "threshold_relation": "boolean", "value": int(required_ok), "threshold_value": 1},
            {"gate": "p0_6_contract_records_six", "passed": _contract_count(p0_6, "same_file_redundancy_trace_contract_records") == 6, "threshold_relation": "equals", "value": _contract_count(p0_6, "same_file_redundancy_trace_contract_records"), "threshold_value": 6},
            {"gate": "p0_7_contract_records_six", "passed": _contract_count(p0_7, "risk_penalty_trace_contract_records") == 6, "threshold_relation": "equals", "value": _contract_count(p0_7, "risk_penalty_trace_contract_records"), "threshold_value": 6},
            {"gate": "p0_private_manifest_counts_zero", "passed": manifests_zero, "threshold_relation": "boolean", "value": int(manifests_zero), "threshold_value": 1},
            {"gate": "p0_trace_gap_missing_trace_confirmed", "passed": missing_confirmed, "threshold_relation": "boolean", "value": int(missing_confirmed), "threshold_value": 1},
            {"gate": "same_file_valid_private_rows", "passed": same_has, "threshold_relation": "greater_or_equal", "value": len(same_valid), "threshold_value": 1},
            {"gate": "risk_penalty_valid_private_rows", "passed": risk_has, "threshold_relation": "greater_or_equal", "value": len(risk_valid), "threshold_value": 1},
        ],
        "stop_go_records": [{
            "stop_go_decision": status,
            "stop_go_reason": "both_private_trace_surfaces_unavailable" if status == "no_go_p2_2_redundancy_risk_traces_unavailable" else "private_trace_schema_invalid" if status == "no_go_p2_2_private_trace_schema_invalid" else "required_inputs_unavailable" if status == "no_go_p2_2_required_inputs_unavailable" else "at_least_one_private_trace_surface_available",
            "authorization": "redundancy_risk_trace_availability_feasibility_audit_only",
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
    same = {"schema_version": SAME_SCHEMA, "action_layer": "file_selector", "action_arm": "arm", "duplicate_pressure_bucket": "high", "same_file_candidate_count_bucket": "many", "topk_file_diversity_bucket": "low", "gold_file_displacement_bucket": "unknown", "marginal_utility_bucket": "unknown"}
    risk = {"schema_version": RISK_SCHEMA, "action_layer": "file_selector", "action_arm": "arm", "risk_class": "mechanism_blind_spot", "risk_policy_bucket": "risk_penalty_unknown", "removed_gold_bucket": "unknown", "replacement_bucket": "unknown", "topk_effect_bucket": "unknown", "counterfactual_keep_bucket": "unknown"}
    same_valid, same_errors = _validate_private_rows([same], surface="same_file_redundancy")
    risk_valid, risk_errors = _validate_private_rows([risk], surface="risk_penalty")
    checks = [
        _check("status_vocab_complete", set(STATUSES) == {"redundancy_risk_trace_availability_pass", "same_file_redundancy_private_trace_pass", "risk_penalty_private_trace_pass", "partial_redundancy_or_risk_trace_available", "no_go_p2_2_redundancy_risk_traces_unavailable", "no_go_p2_2_private_trace_schema_invalid", "no_go_p2_2_required_inputs_unavailable", "fail_forbidden_scan", "fail_schema_contract"}),
        _check("same_file_schema_accepts_fixture", len(same_valid) == 1 and not same_errors),
        _check("risk_schema_accepts_fixture", len(risk_valid) == 1 and not risk_errors),
        _check("schema_rejects_bad_fixture", bool(_validate_private_rows([{**same, "schema_version": "bad"}], surface="same_file_redundancy")[1])),
        _check("sanitized_rows_hide_forbidden_payloads", "path" not in _sanitize_private_rows([same], surface="same_file_redundancy")[0]),
        _check("scanner_accepts_sanitized", tg._scan_summary({"sanitized_private_trace_bucket_records": _sanitize_private_rows([risk], surface="risk_penalty")})["status"] == "pass"),
        _check("scanner_rejects_path_key", tg._scan_summary({"path": "x"})["status"] == "fail"),
        _check("empty_private_file_is_not_partial", _status_from_availability(self_tests_ok=True, required_ok=True, contracts_ok=True, has_errors=False, same_has=False, risk_has=False) == "no_go_p2_2_redundancy_risk_traces_unavailable"),
    ]
    return checks, all(c["passed"] for c in checks)


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit(f"argument_error: {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA v1 P2-2 redundancy/risk trace availability feasibility audit")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--p0-6-artifact", type=Path, default=DEFAULT_P0_6)
    parser.add_argument("--p0-7-artifact", type=Path, default=DEFAULT_P0_7)
    parser.add_argument("--p0-1-artifact", type=Path, default=DEFAULT_P0_1)
    parser.add_argument("--p0-2-artifact", type=Path, default=DEFAULT_P0_2)
    parser.add_argument("--same-file-private-trace-jsonl", type=Path, default=DEFAULT_SAME_FILE_PRIVATE)
    parser.add_argument("--risk-penalty-private-trace-jsonl", type=Path, default=DEFAULT_RISK_PRIVATE)
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']}, same_valid={report['private_trace_manifest_records'][0]['valid_record_count']}, risk_valid={report['private_trace_manifest_records'][1]['valid_record_count']})")


if __name__ == "__main__":
    main()
