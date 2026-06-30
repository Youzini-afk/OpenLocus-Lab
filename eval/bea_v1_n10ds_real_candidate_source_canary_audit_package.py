#!/usr/bin/env python3
"""BEA-v1-N10DS Real Candidate-Source Canary Audit Package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10ds_real_candidate_source_canary_audit_package"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10DR_REPORT = ROOT / "artifacts" / "bea_v1_n10dr_real_candidate_source_canary" / "bea_v1_n10dr_real_candidate_source_canary_report.json"

STATUS_COMPLETE = "real_candidate_source_canary_audit_package_complete_n10dt_authorized"
STATUS_NO_INPUTS = "no_go_n10ds_required_public_inputs_unavailable"
STATUS_CHAIN = "no_go_n10ds_canary_chain_mismatch"
STATUS_CLAIM = "no_go_n10ds_claim_boundary_invalid"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {
    STATUS_COMPLETE,
    STATUS_NO_INPUTS,
    STATUS_CHAIN,
    STATUS_CLAIM,
    STATUS_FAIL_SCAN,
    STATUS_FAIL_SCHEMA,
}

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename",
    "source_path", "span", "spans", "line", "lines", "snippet", "snippets",
    "content", "candidate_list", "candidates", "gold_path", "gold_paths",
    "gold_line", "gold_lines", "exact_rank", "raw_rank", "repo_id", "task_id",
    "hash", "provider_payload", "raw_diff", "raw_log",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt)"),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DS real canary audit package")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return parser.parse_args(argv)


def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


def scan_summary(obj: Any) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS:
            findings.append({"finding_bucket": "forbidden_key", "key_bucket": key})
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for item in node:
                walk(item, key)
        elif isinstance(node, str):
            for pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(node):
                    findings.append({"finding_bucket": "forbidden_value", "key_bucket": key or "value"})
                    break

    walk(obj)
    return {"status": "fail" if findings else "pass", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def first_record(data: dict[str, Any], key: str) -> dict[str, Any]:
    rows = data.get(key) or []
    return rows[0] if rows and isinstance(rows[0], dict) else {}


def bucket_count(data: dict[str, Any], key: str, bucket_key: str, count_key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in data.get(key, []) or []:
        if isinstance(row, dict):
            out[str(row.get(bucket_key, "unknown"))] = int(row.get(count_key, 0))
    return out


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    data, state = load_json(N10DR_REPORT)
    actual = str(data.get("status", "")) if data else ""
    expected = "real_candidate_source_canary_complete_no_recovery"
    ok = state == "present" and actual == expected
    return ([{
        "anonymous_input_artifact_id": "n10dsinput0000",
        "artifact_bucket": "n10dr_real_candidate_source_canary",
        "load_status_bucket": state,
        "expected_status_bucket": expected,
        "actual_status_bucket": actual or "unavailable",
        "status_match_bool": ok,
        "public_artifact_bool": True,
    }], data or {}, ok)


def metrics_match(n10dr: dict[str, Any]) -> bool:
    result = first_record(n10dr, "candidate_source_result_records")
    execution = first_record(n10dr, "private_execution_summary_records")
    pools = {str(r.get("pool_richness_bucket")): r for r in n10dr.get("pool_richness_recovery_records", []) if isinstance(r, dict)}
    return (
        result.get("sampled_case_count") == 30
        and result.get("executed_case_count") == 30
        and execution.get("local_repo_available_count") == 30
        and execution.get("retrieval_command_success_count") == 28
        and result.get("gold_file_recovered_top10_count") == 0
        and result.get("gold_file_recovered_top20_count") == 0
        and result.get("gold_file_recovered_top50_count") == 0
        and all((pools.get(bucket, {}).get("gold_file_recovered_top50_count") == 0 and pools.get(bucket, {}).get("sampled_case_count") == 10) for bucket in ("tiny_pool_absence", "moderate_pool_absence", "rich_wrong_pool_absence"))
    )


def build_report() -> dict[str, Any]:
    input_records, n10dr, inputs_ok = input_artifact_records()
    result = first_record(n10dr, "candidate_source_result_records")
    execution = first_record(n10dr, "private_execution_summary_records")
    candidate_counts = bucket_count(n10dr, "candidate_count_bucket_records", "candidate_count_bucket", "case_count")
    nonzero_candidate_cases = sum(v for k, v in candidate_counts.items() if k != "zero")
    error_counts = bucket_count(n10dr, "error_bucket_records", "error_bucket", "case_count")
    metrics_ok = inputs_ok and metrics_match(n10dr)
    status = STATUS_COMPLETE if metrics_ok else (STATUS_NO_INPUTS if not inputs_ok else STATUS_CHAIN)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10ds_real_candidate_source_canary_audit_package_v1",
        "phase_bucket": "BEA-v1-N10DS Real Candidate-Source Canary Audit Package",
        "status": status,
        "input_artifact_records": input_records,
        "package_summary_records": [{
            "anonymous_package_summary_id": "n10dssummary0000",
            "package_scope_bucket": "public_only_real_candidate_source_canary_audit_package",
            "private_read_count": 0,
            "recompute_count": 0,
            "retrieval_execution_count": 0,
            "package_complete_bool": metrics_ok,
        }],
        "canary_result_records": [{
            "anonymous_canary_result_id": "n10dsresult0000",
            "source_status_bucket": str(n10dr.get("status", "unavailable")),
            "sampled_case_count": result.get("sampled_case_count", 0),
            "executed_case_count": result.get("executed_case_count", 0),
            "local_repo_available_count": execution.get("local_repo_available_count", 0),
            "retrieval_command_success_count": execution.get("retrieval_command_success_count", 0),
            "nonzero_candidate_case_count": nonzero_candidate_cases,
            "gold_file_recovered_top10_count": result.get("gold_file_recovered_top10_count", 0),
            "gold_file_recovered_top20_count": result.get("gold_file_recovered_top20_count", 0),
            "gold_file_recovered_top50_count": result.get("gold_file_recovered_top50_count", 0),
            "tiny_pool_top50_recovered_count": 0,
            "moderate_pool_top50_recovered_count": 0,
            "rich_wrong_pool_top50_recovered_count": 0,
            "nonzero_exit_error_count": error_counts.get("nonzero_exit", 0),
            "zero_candidate_case_count": candidate_counts.get("zero", 0),
        }],
        "negative_result_interpretation_records": [{
            "anonymous_interpretation_id": "n10dsinterp0000",
            "valid_negative_canary_bool": True,
            "infrastructure_failure_bool": False,
            "bounded_local_canary_no_recovery_bool": True,
            "do_not_scale_source_directly_bool": True,
            "full_denominator_improvement_claim_bool": False,
            "next_mechanism_bucket": "failure_mechanism_analysis",
            "interpretation_bucket": "valid_negative_canary_not_infrastructure_failure",
        }],
        "no_private_read_no_recompute_records": [{
            "anonymous_no_recompute_id": "n10dsnoexec0000",
            "private_read_count": 0,
            "recompute_count": 0,
            "retrieval_execution_count": 0,
            "candidate_generation_count": 0,
            "selector_reranker_execution_count": 0,
        }],
        "n10dt_handoff_records": [{
            "anonymous_handoff_id": "n10dshandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DT Real Candidate-Source Canary Failure Mechanism Analysis",
            "n10dt_failure_mechanism_analysis_authorized_bool": True,
            "scaled_retrieval_authorized_bool": False,
            "runtime_default_authorized_bool": False,
        }],
        "gate_records": [
            {"anonymous_gate_id": "n10dsgate0000", "gate_bucket": "public_input_present", "gate_passed_bool": inputs_ok},
            {"anonymous_gate_id": "n10dsgate0001", "gate_bucket": "canary_metrics_match_expected_negative", "gate_passed_bool": metrics_ok},
            {"anonymous_gate_id": "n10dsgate0002", "gate_bucket": "no_private_read_no_recompute", "gate_passed_bool": True},
        ],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10dsstop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DT Real Candidate-Source Canary Failure Mechanism Analysis",
            "scaled_retrieval_authorized_bool": False,
            "network_authorized_bool": False,
            "git_clone_authorized_bool": False,
            "candidate_generation_materialization_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "runtime_default_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "broad_private_read_authorized_bool": False,
        }],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_FAIL_SCHEMA in STATUS_VOCAB))
    try:
        parse_args(["--bad", "secret-value"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/private.json"})["status"] == "fail"))
    synthetic = {
        "status": "real_candidate_source_canary_complete_no_recovery",
        "candidate_source_result_records": [{"sampled_case_count": 30, "executed_case_count": 30, "gold_file_recovered_top10_count": 0, "gold_file_recovered_top20_count": 0, "gold_file_recovered_top50_count": 0}],
        "private_execution_summary_records": [{"local_repo_available_count": 30, "retrieval_command_success_count": 28}],
        "pool_richness_recovery_records": [
            {"pool_richness_bucket": "tiny_pool_absence", "sampled_case_count": 10, "gold_file_recovered_top50_count": 0},
            {"pool_richness_bucket": "moderate_pool_absence", "sampled_case_count": 10, "gold_file_recovered_top50_count": 0},
            {"pool_richness_bucket": "rich_wrong_pool_absence", "sampled_case_count": 10, "gold_file_recovered_top50_count": 0},
        ],
    }
    checks.append(("metrics_match", metrics_match(synthetic)))
    synthetic["candidate_source_result_records"][0]["gold_file_recovered_top50_count"] = 1
    checks.append(("metrics_mismatch", not metrics_match(synthetic)))
    report = build_report()
    checks.append(("report_records", all(k in report for k in ("input_artifact_records", "canary_result_records", "negative_result_interpretation_records", "stop_go_records"))))
    checks.append(("false_flags", not report["stop_go_records"][0]["scaled_retrieval_authorized_bool"] and not report["stop_go_records"][0]["runtime_default_authorized_bool"]))
    checks.append(("scan_report", report["forbidden_scan"]["status"] == "pass"))
    checks.append(("status_expected", report["status"] in STATUS_VOCAB))
    passed = 0
    for name, ok in checks:
        print(f"[{ 'PASS' if ok else 'FAIL' }] {name}")
        passed += int(ok)
    print(f"self_test_passed={passed == len(checks)} ({passed}/{len(checks)} checks)")
    return passed == len(checks)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return 0 if run_self_test() else 1
    report = build_report()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] == STATUS_COMPLETE else 1


if __name__ == "__main__":
    raise SystemExit(main())
