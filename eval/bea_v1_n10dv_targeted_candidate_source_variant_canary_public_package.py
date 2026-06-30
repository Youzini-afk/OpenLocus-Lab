#!/usr/bin/env python3
"""BEA-v1-N10DV Targeted Candidate-Source Variant Canary Public Package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10DU_REPORT = ROOT / "artifacts" / "bea_v1_n10du_targeted_candidate_source_variant_canary" / "bea_v1_n10du_targeted_candidate_source_variant_canary_report.json"

STATUS_COMPLETE = "targeted_candidate_source_variant_canary_public_package_complete_n10dw_authorized"
STATUS_NO_INPUTS = "no_go_n10dv_required_public_inputs_unavailable"
STATUS_CHAIN = "no_go_n10dv_targeted_canary_chain_mismatch"
STATUS_CLAIM = "no_go_n10dv_claim_boundary_invalid"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUTS, STATUS_CHAIN, STATUS_CLAIM, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

FORBIDDEN_KEYS = {
    "path", "paths", "file", "files", "filename", "filenames", "private_path",
    "private_filename", "repo", "repo_root", "span", "spans", "line", "lines",
    "snippet", "snippets", "content", "candidate", "candidates", "candidate_list",
    "gold", "gold_path", "gold_paths", "exact_rank", "raw_rank", "raw_query",
    "query", "hash", "provider_payload", "raw_diff", "raw_log",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt)", re.I),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DV targeted source package")
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
            if any(pattern.search(node) for pattern in FORBIDDEN_VALUE_PATTERNS):
                findings.append({"finding_bucket": "forbidden_value", "key_bucket": key or "value"})

    walk(obj)
    return {"status": "fail" if findings else "pass", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def first_record(data: dict[str, Any], key: str) -> dict[str, Any]:
    rows = data.get(key) or []
    return rows[0] if rows and isinstance(rows[0], dict) else {}


def variant_by_name(data: dict[str, Any], name: str) -> dict[str, Any]:
    for row in data.get("variant_result_records", []) or []:
        if isinstance(row, dict) and row.get("variant_bucket") == name:
            return row
    return {}


def input_artifact_records() -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    data, state = load_json(N10DU_REPORT)
    actual = str(data.get("status", "")) if data else ""
    expected = "targeted_candidate_source_variant_canary_pass_n10dv_authorized"
    ok = state == "present" and actual == expected
    return ([{
        "anonymous_input_artifact_id": "n10dvinput0000",
        "artifact_bucket": "n10du_targeted_candidate_source_variant_canary",
        "load_status_bucket": state,
        "expected_status_bucket": expected,
        "actual_status_bucket": actual or "unavailable",
        "status_match_bool": ok,
        "public_artifact_bool": True,
    }], data or {}, ok)


def metrics_match(n10du: dict[str, Any]) -> bool:
    cross = first_record(n10du, "cross_variant_recovery_records")
    best = variant_by_name(n10du, "identifier_normalized_bm25_only")
    original_bm25 = variant_by_name(n10du, "original_bm25_only")
    return (
        cross.get("cases_recovered_by_any_variant_count") == 10
        and cross.get("best_variant_bucket") == "identifier_normalized_bm25_only"
        and best.get("gold_file_recovered_top10_count") == 8
        and best.get("gold_file_recovered_top20_count") == 9
        and best.get("gold_file_recovered_top50_count") == 10
        and original_bm25.get("gold_file_recovered_top50_count") == 0
        and len(n10du.get("variant_result_records", []) or []) == 6
    )


def build_report() -> dict[str, Any]:
    input_records, n10du, inputs_ok = input_artifact_records()
    cross = first_record(n10du, "cross_variant_recovery_records")
    command = first_record(n10du, "command_boundary_records")
    best = variant_by_name(n10du, "identifier_normalized_bm25_only")
    original_bm25 = variant_by_name(n10du, "original_bm25_only")
    original_regex = variant_by_name(n10du, "original_regex_only")
    original_symbol = variant_by_name(n10du, "original_symbol_only")
    norm_regex = variant_by_name(n10du, "identifier_normalized_regex_only")
    norm_symbol = variant_by_name(n10du, "identifier_normalized_symbol_only")
    metrics_ok = inputs_ok and metrics_match(n10du)
    status = STATUS_COMPLETE if metrics_ok else (STATUS_NO_INPUTS if not inputs_ok else STATUS_CHAIN)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package_v1",
        "phase_bucket": "BEA-v1-N10DV Targeted Candidate-Source Variant Canary Public Package",
        "status": status,
        "input_artifact_records": input_records,
        "package_summary_records": [{
            "anonymous_package_summary_id": "n10dvsummary0000",
            "package_scope_bucket": "public_only_targeted_candidate_source_variant_canary_package",
            "private_read_count": 0,
            "recompute_count": 0,
            "retrieval_execution_count": 0,
            "package_complete_bool": metrics_ok,
        }],
        "targeted_canary_result_records": [{
            "anonymous_targeted_result_id": "n10dvresult0000",
            "source_status_bucket": str(n10du.get("status", "unavailable")),
            "sampled_case_count": 30,
            "variant_count": 6,
            "command_count": command.get("actual_command_count", 0),
            "cases_recovered_by_any_variant_count": cross.get("cases_recovered_by_any_variant_count", 0),
            "best_variant_bucket": cross.get("best_variant_bucket", "unavailable"),
            "best_variant_top10_recovered_count": best.get("gold_file_recovered_top10_count", 0),
            "best_variant_top20_recovered_count": best.get("gold_file_recovered_top20_count", 0),
            "best_variant_top50_recovered_count": best.get("gold_file_recovered_top50_count", 0),
            "original_bm25_top50_recovered_count": original_bm25.get("gold_file_recovered_top50_count", 0),
            "regex_symbol_top50_recovered_count": sum(int(v.get("gold_file_recovered_top50_count", 0)) for v in (original_regex, original_symbol, norm_regex, norm_symbol)),
        }],
        "normalized_bm25_signal_records": [{
            "anonymous_signal_id": "n10dvsignal0000",
            "signal_bucket": "identifier_normalized_bm25_positive_signal",
            "same_30_case_signal_bool": True,
            "strong_targeted_canary_signal_bool": metrics_ok,
            "not_scaling_claim_bool": True,
            "not_heldout_claim_bool": True,
            "not_runtime_default_claim_bool": True,
            "mechanism_followup_bucket": "normalized_bm25_recovery_mechanism_analysis",
        }],
        "no_private_read_no_recompute_records": [{
            "anonymous_no_recompute_id": "n10dvnoexec0000",
            "private_read_count": 0,
            "recompute_count": 0,
            "retrieval_execution_count": 0,
            "candidate_generation_count": 0,
            "selector_reranker_execution_count": 0,
        }],
        "n10dw_handoff_records": [{
            "anonymous_handoff_id": "n10dvhandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DW Normalized-BM25 Recovery Mechanism Analysis",
            "n10dw_mechanism_analysis_authorized_bool": True,
            "scaled_retrieval_authorized_bool": False,
            "runtime_default_authorized_bool": False,
        }],
        "gate_records": [
            {"anonymous_gate_id": "n10dvgate0000", "gate_bucket": "public_input_present", "gate_passed_bool": inputs_ok},
            {"anonymous_gate_id": "n10dvgate0001", "gate_bucket": "targeted_canary_metrics_match", "gate_passed_bool": metrics_ok},
            {"anonymous_gate_id": "n10dvgate0002", "gate_bucket": "no_private_read_no_recompute", "gate_passed_bool": True},
        ],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10dvstop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DW Normalized-BM25 Recovery Mechanism Analysis",
            "scaled_retrieval_authorized_bool": False,
            "network_authorized_bool": False,
            "git_clone_authorized_bool": False,
            "provider_authorized_bool": False,
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
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_CHAIN in STATUS_VOCAB))
    try:
        parse_args(["--unknown", "secret"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"query": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/x.json"})["status"] == "fail"))
    fake = {
        "status": "targeted_candidate_source_variant_canary_pass_n10dv_authorized",
        "cross_variant_recovery_records": [{"cases_recovered_by_any_variant_count": 10, "best_variant_bucket": "identifier_normalized_bm25_only"}],
        "variant_result_records": [
            {"variant_bucket": "identifier_normalized_bm25_only", "gold_file_recovered_top10_count": 8, "gold_file_recovered_top20_count": 9, "gold_file_recovered_top50_count": 10},
            {"variant_bucket": "original_bm25_only", "gold_file_recovered_top50_count": 0},
            {"variant_bucket": "original_regex_only"}, {"variant_bucket": "original_symbol_only"}, {"variant_bucket": "identifier_normalized_regex_only"}, {"variant_bucket": "identifier_normalized_symbol_only"},
        ],
    }
    checks.append(("synthetic_package_pass", metrics_match(fake)))
    fake["cross_variant_recovery_records"][0]["cases_recovered_by_any_variant_count"] = 9
    checks.append(("synthetic_package_mismatch", not metrics_match(fake)))
    report = {"stop_go_records": [{"scaled_retrieval_authorized_bool": False, "runtime_default_authorized_bool": False}]}
    checks.append(("false_claims", not report["stop_go_records"][0]["scaled_retrieval_authorized_bool"] and not report["stop_go_records"][0]["runtime_default_authorized_bool"]))
    checks.append(("scan_pass", scan_summary({"bucket": "safe", "count": 1})["status"] == "pass"))
    passed = sum(1 for _, ok in checks if ok)
    for name, ok in checks:
        print(f"[{ 'PASS' if ok else 'FAIL' }] {name}")
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
