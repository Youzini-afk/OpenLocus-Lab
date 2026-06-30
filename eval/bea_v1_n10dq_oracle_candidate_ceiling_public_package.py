#!/usr/bin/env python3
"""BEA-v1-N10DQ Oracle Candidate-Insertion Ceiling Public Package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dq_oracle_candidate_ceiling_public_package" / "bea_v1_n10dq_oracle_candidate_ceiling_public_package_report.json"
PUBLIC_INPUTS = {
    "n10dp_oracle_ceiling_smoke": (
        ROOT / "artifacts" / "bea_v1_n10dp_oracle_candidate_insertion_ceiling_smoke" / "bea_v1_n10dp_oracle_candidate_insertion_ceiling_smoke_report.json",
        "oracle_candidate_insertion_ceiling_smoke_complete_n10dq_authorized",
    ),
    "n10dor_corrected_absence_audit": (
        ROOT / "artifacts" / "bea_v1_n10dor_corrected_candidate_pool_absence_source_audit" / "bea_v1_n10dor_corrected_candidate_pool_absence_source_audit_report.json",
        "corrected_candidate_pool_absence_source_audit_complete_n10dp_authorized",
    ),
    "n10dnr_corrected_deep_rank_package": (
        ROOT / "artifacts" / "bea_v1_n10dnr_corrected_deep_rank_promotion_public_package" / "bea_v1_n10dnr_corrected_deep_rank_promotion_public_package_report.json",
        "corrected_deep_rank_promotion_public_package_complete_n10dor_authorized",
    ),
}

STATUS_COMPLETE = "oracle_candidate_ceiling_public_package_complete_n10dr_authorized"
STATUS_NO_INPUTS = "no_go_n10dq_required_public_inputs_unavailable"
STATUS_CHAIN = "no_go_n10dq_oracle_ceiling_chain_mismatch"
STATUS_CLAIM = "no_go_n10dq_claim_boundary_invalid"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUTS, STATUS_CHAIN, STATUS_CLAIM, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename",
    "source_path", "span", "spans", "line", "lines", "snippet", "snippets",
    "content", "candidate_list", "candidates", "gold_path", "gold_paths",
    "gold_line", "gold_lines", "exact_rank", "raw_rank", "repo_id", "task_id",
    "hash", "provider_payload", "raw_diff",
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
    parser = SafeArgumentParser(description="BEA-v1-N10DQ oracle ceiling public package")
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
            findings.append({"bucket": "forbidden_key", "key_bucket": key})
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for item in node:
                walk(item, key)
        elif isinstance(node, str):
            for pat in FORBIDDEN_VALUE_PATTERNS:
                if pat.search(node):
                    findings.append({"bucket": "forbidden_value", "key_bucket": key or "value"})
                    break

    walk(obj)
    return {"status": "fail" if findings else "pass", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    loaded: dict[str, dict[str, Any]] = {}
    ok = True
    for idx, (bucket, (path, expected_status)) in enumerate(PUBLIC_INPUTS.items()):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        match = state == "present" and actual == expected_status
        ok = ok and match
        if data:
            loaded[bucket] = data
        records.append({
            "anonymous_input_artifact_id": f"n10dqin{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected_status,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": match,
            "public_artifact_bool": True,
        })
    return records, loaded, ok


def find_oracle_results(n10dp: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("oracle_variant_bucket")): row for row in n10dp.get("oracle_ceiling_result_records", []) if isinstance(row, dict)}


def package_ok(results: dict[str, dict[str, Any]]) -> bool:
    expected = {
        "oracle_insert_gold_file_at_rank1": (185, 199),
        "oracle_insert_gold_file_at_rank5": (185, 199),
        "oracle_insert_gold_file_at_rank10": (185, 199),
        "oracle_append_gold_file_after_top10": (44, 199),
    }
    for name, (top10, top20) in expected.items():
        row = results.get(name, {})
        if row.get("upper_bound_top10_file_reach") != top10 or row.get("upper_bound_top20_file_reach") != top20:
            return False
        if row.get("oracle_span_overlap_status_bucket") != "not_evaluated_no_oracle_span":
            return False
    return True


def build_report() -> dict[str, Any]:
    input_records, loaded, inputs_ok = input_artifact_records()
    n10dp = loaded.get("n10dp_oracle_ceiling_smoke", {})
    results = find_oracle_results(n10dp)
    metrics_ok = package_ok(results)
    status = STATUS_COMPLETE if inputs_ok and metrics_ok else (STATUS_NO_INPUTS if not inputs_ok else STATUS_CHAIN)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dq_oracle_candidate_ceiling_public_package_v1",
        "phase_bucket": "BEA-v1-N10DQ Oracle Candidate-Insertion Ceiling Public Package",
        "status": status,
        "input_artifact_records": input_records,
        "package_summary_records": [{
            "anonymous_package_summary_id": "n10dqsummary0000",
            "package_scope_bucket": "public_only_oracle_ceiling_package",
            "private_read_count": 0,
            "recompute_count": 0,
            "oracle_insertion_execution_count": 0,
            "anchor_top10_file_reach": 44,
            "anchor_top20_file_reach": 58,
            "affected_absent_pool_cases": 141,
            "package_complete_bool": inputs_ok and metrics_ok,
        }],
        "oracle_ceiling_summary_records": [
            {"anonymous_ceiling_id": "n10dqceil0000", "oracle_variant_group_bucket": "rank1_rank5_rank10_within_top10", "top10_file_ceiling": 185, "top20_file_ceiling": 199, "increment_top10_over_anchor": 141, "increment_top20_over_anchor": 141, "non_policy_upper_bound_bool": True},
            {"anonymous_ceiling_id": "n10dqceil0001", "oracle_variant_group_bucket": "append_after_top10", "top10_file_ceiling": 44, "top20_file_ceiling": 199, "increment_top10_over_anchor": 0, "increment_top20_over_anchor": 141, "non_policy_upper_bound_bool": True},
        ],
        "span_boundary_records": [{
            "anonymous_span_boundary_id": "n10dqspan0000",
            "span_metric_status_bucket": "not_evaluated_no_oracle_span",
            "span_overlap_faked_bool": False,
            "file_reach_primary_for_ceiling_bool": True,
        }],
        "non_policy_boundary_records": [{
            "anonymous_non_policy_id": "n10dqnonpolicy0000",
            "upper_bound_value_signal_bool": True,
            "feasible_policy_claim_bool": False,
            "retrieval_source_result_claim_bool": False,
            "runtime_default_claim_bool": False,
            "method_winner_claim_bool": False,
            "downstream_value_claim_bool": False,
            "heldout_generalization_claim_bool": False,
        }],
        "no_private_read_no_recompute_records": [{
            "anonymous_no_recompute_id": "n10dqnoexec0000",
            "private_read_count": 0,
            "recompute_count": 0,
            "oracle_insertion_count": 0,
            "retrieval_execution_count": 0,
            "real_candidate_generation_count": 0,
            "selector_reranker_execution_count": 0,
        }],
        "next_handoff_records": [{
            "anonymous_handoff_id": "n10dqhandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DR Real Candidate-Source Canary",
            "next_scope_bucket": "oracle_orchestrator_contract_required_before_execution",
            "n10dr_canary_authorized_for_future_contract_bool": True,
            "candidate_generation_authorized_in_n10dq_bool": False,
            "retrieval_authorized_in_n10dq_bool": False,
        }],
        "gate_records": [
            {"anonymous_gate_id": "n10dqgate0000", "gate_bucket": "public_inputs_present", "gate_passed_bool": inputs_ok},
            {"anonymous_gate_id": "n10dqgate0001", "gate_bucket": "oracle_ceiling_metrics_match", "gate_passed_bool": metrics_ok},
            {"anonymous_gate_id": "n10dqgate0002", "gate_bucket": "no_private_read_no_recompute", "gate_passed_bool": True},
        ],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10dqstop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DR Real Candidate-Source Canary",
            "next_phase_requires_oracle_contract_bool": True,
            "runtime_default_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "candidate_generation_authorized_in_n10dq_bool": False,
            "retrieval_rerun_authorized_in_n10dq_bool": False,
            "source_acquisition_executed_bool": False,
        }],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_self_test() -> int:
    tests: list[tuple[str, bool]] = []
    tests.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_FAIL_SCAN in STATUS_VOCAB))
    try:
        parse_args(["--unexpected", "secret"])
        tests.append(("safe_parser", False))
    except SystemExit as exc:
        tests.append(("safe_parser", exc.code == 2))
    tests.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    tests.append(("scanner_safe", scan_summary({"bucket": "aggregate_only"})["status"] == "pass"))
    fake = {"oracle_insert_gold_file_at_rank1": {"upper_bound_top10_file_reach": 185, "upper_bound_top20_file_reach": 199, "oracle_span_overlap_status_bucket": "not_evaluated_no_oracle_span"}, "oracle_insert_gold_file_at_rank5": {"upper_bound_top10_file_reach": 185, "upper_bound_top20_file_reach": 199, "oracle_span_overlap_status_bucket": "not_evaluated_no_oracle_span"}, "oracle_insert_gold_file_at_rank10": {"upper_bound_top10_file_reach": 185, "upper_bound_top20_file_reach": 199, "oracle_span_overlap_status_bucket": "not_evaluated_no_oracle_span"}, "oracle_append_gold_file_after_top10": {"upper_bound_top10_file_reach": 44, "upper_bound_top20_file_reach": 199, "oracle_span_overlap_status_bucket": "not_evaluated_no_oracle_span"}}
    tests.append(("package_pass", package_ok(fake)))
    fake["oracle_append_gold_file_after_top10"]["upper_bound_top10_file_reach"] = 45
    tests.append(("package_mismatch", not package_ok(fake)))
    report = build_report()
    tests.append(("no_private_read", report["no_private_read_no_recompute_records"][0]["private_read_count"] == 0))
    tests.append(("false_claims", report["non_policy_boundary_records"][0]["feasible_policy_claim_bool"] is False and report["stop_go_records"][0]["runtime_default_authorized_bool"] is False))
    tests.append(("span_not_evaluated", report["span_boundary_records"][0]["span_metric_status_bucket"] == "not_evaluated_no_oracle_span"))
    tests.append(("handoff", report["next_handoff_records"][0]["next_allowed_phase_bucket"] == "BEA-v1-N10DR Real Candidate-Source Canary"))
    tests.append(("scan_report", report["forbidden_scan"]["status"] == "pass"))
    passed = sum(1 for _, ok in tests if ok)
    for name, ok in tests:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"self_test_passed={passed == len(tests)} ({passed}/{len(tests)} checks)")
    return 0 if passed == len(tests) else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return run_self_test()
    report = build_report()
    write_report(report, Path(args.out))
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] == STATUS_COMPLETE else 1


if __name__ == "__main__":
    raise SystemExit(main())
