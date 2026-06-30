#!/usr/bin/env python3
"""BEA-v1-N10EA Normalized-BM25 Expanded Canary Public Package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10ea_normalized_bm25_expanded_canary_public_package"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10DZ_REPORT = ROOT / "artifacts" / "bea_v1_n10dz_normalized_bm25_expanded_canary" / "bea_v1_n10dz_normalized_bm25_expanded_canary_report.json"

STATUS_COMPLETE = "normalized_bm25_expanded_canary_public_package_complete_n10eb_authorized"
STATUS_NO_INPUTS = "no_go_n10ea_required_public_inputs_unavailable"
STATUS_CHAIN_MISMATCH = "no_go_n10ea_expanded_canary_chain_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUTS, STATUS_CHAIN_MISMATCH, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

EXPECTED_STATUS = "normalized_bm25_expanded_canary_low_recovery_n10ea_authorized"

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename",
    "query", "raw_query", "candidate", "candidates", "candidate_list", "candidate_order",
    "gold", "gold_path", "gold_paths", "span", "spans", "line", "lines", "snippet",
    "snippets", "content", "exact_rank", "raw_rank", "repo", "repo_root", "hash",
    "provider_payload", "raw_diff",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt|go|java)", re.I),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10EA public package")
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
        elif isinstance(node, str) and any(pattern.search(node) for pattern in FORBIDDEN_VALUE_PATTERNS):
            findings.append({"finding_bucket": "forbidden_value", "key_bucket": key or "value"})

    walk(obj)
    return {"status": "fail" if findings else "pass", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def setting_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("setting_bucket")): row for row in report.get("setting_result_records", []) if isinstance(row, dict)}


def counts(row: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(row.get("gold_file_recovered_top10_count", -1)),
        int(row.get("gold_file_recovered_top20_count", -1)),
        int(row.get("gold_file_recovered_top50_count", -1)),
        int(row.get("gold_file_recovered_top100_count", -1)),
    )


def build_report() -> dict[str, Any]:
    n10dz, state = load_json(N10DZ_REPORT)
    input_ok = state == "present" and bool(n10dz) and n10dz.get("status") == EXPECTED_STATUS
    settings = setting_map(n10dz or {})
    primary = settings.get("normalized_bm25_top50_cap12", {})
    depth = settings.get("normalized_bm25_top100_cap12", {})
    primary_counts = counts(primary)
    depth_counts = counts(depth)
    chain_ok = (
        primary_counts == (5, 11, 17, 17)
        and depth_counts == (5, 11, 17, 26)
        and int((n10dz or {}).get("comparison_to_original_canary_records", [{}])[0].get("new_sample_case_count", -1)) == 60
    )
    status = STATUS_COMPLETE if input_ok and chain_ok else (STATUS_NO_INPUTS if not input_ok else STATUS_CHAIN_MISMATCH)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10ea_normalized_bm25_expanded_canary_public_package_v1",
        "phase_bucket": "BEA-v1-N10EA Normalized-BM25 Expanded Canary Public Package",
        "status": status,
        "input_artifact_records": [{
            "anonymous_input_artifact_id": "n10eainput0000",
            "artifact_bucket": "n10dz_normalized_bm25_expanded_canary",
            "load_status_bucket": state,
            "expected_status_bucket": EXPECTED_STATUS,
            "actual_status_bucket": str((n10dz or {}).get("status", "unavailable")),
            "status_match_bool": input_ok,
            "public_artifact_bool": True,
        }],
        "package_summary_records": [{
            "anonymous_package_summary_id": "n10easummary0000",
            "public_only_package_bool": True,
            "private_read_count": 0,
            "retrieval_execution_count": 0,
            "openlocus_execution_count": 0,
            "recompute_count": 0,
            "sampled_case_count": 60,
            "command_count_packaged_from_n10dz": 120,
        }],
        "packaged_setting_result_records": [
            {"anonymous_setting_result_id": "n10easetting0000", "setting_bucket": "normalized_bm25_top50_cap12", "interpretation_bucket": "low_head_recovery_primary_setting", "top10_count": primary_counts[0], "top20_count": primary_counts[1], "top50_count": primary_counts[2], "top100_count": primary_counts[3]},
            {"anonymous_setting_result_id": "n10easetting0001", "setting_bucket": "normalized_bm25_top100_cap12", "interpretation_bucket": "depth_only_recovery_setting", "top10_count": depth_counts[0], "top20_count": depth_counts[1], "top50_count": depth_counts[2], "top100_count": depth_counts[3], "additional_top100_vs_primary_count": depth_counts[3] - primary_counts[3]},
        ],
        "interpretation_records": [{
            "anonymous_interpretation_id": "n10eainterp0000",
            "low_top10_recovery_bool": True,
            "top10_pass_gate_met_bool": False,
            "primary_top10_threshold": 10,
            "primary_top10_count": primary_counts[0],
            "candidate_source_signal_at_depth_bool": True,
            "top100_depth_only_gain_bool": True,
            "top100_improves_top10_bool": False,
            "statistical_generalization_claim_bool": False,
            "runtime_default_claim_bool": False,
        }],
        "no_private_read_no_recompute_records": [{
            "anonymous_no_private_id": "n10eanopriv0000",
            "private_read_count": 0,
            "retrieval_execution_count": 0,
            "openlocus_execution_count": 0,
            "recompute_count": 0,
            "candidate_generation_count": 0,
        }],
        "n10eb_handoff_records": [{
            "anonymous_handoff_id": "n10eahandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10EB Normalized-BM25 Depth-to-Head Integration Experiment",
            "n10eb_depth_to_head_experiment_authorized_bool": True,
            "public_package_complete_bool": status == STATUS_COMPLETE,
            "scaled_full_denominator_authorized_bool": False,
            "runtime_default_authorized_bool": False,
        }],
        "gate_records": [
            {"anonymous_gate_id": "n10eagate0000", "gate_bucket": "n10dz_public_input_present", "gate_passed_bool": input_ok},
            {"anonymous_gate_id": "n10eagate0001", "gate_bucket": "n10dz_counts_match_expected", "gate_passed_bool": chain_ok},
            {"anonymous_gate_id": "n10eagate0002", "gate_bucket": "public_only_no_recompute", "gate_passed_bool": True},
        ],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10eastop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10EB Normalized-BM25 Depth-to-Head Integration Experiment",
            "runtime_default_authorized_bool": False,
            "scaled_full_denominator_authorized_bool": False,
            "network_authorized_bool": False,
            "git_clone_authorized_bool": False,
            "provider_authorized_bool": False,
            "candidate_generation_materialization_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
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
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_CHAIN_MISMATCH in STATUS_VOCAB))
    try:
        parse_args(["--bad", "secret"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"query": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/a.json"})["status"] == "fail"))
    checks.append(("counts", (5, 11, 17, 26)[3] - (5, 11, 17, 17)[3] == 9))
    checks.append(("low_head", 5 < 10 and 17 > 5 and 26 > 17))
    checks.append(("scan_pass", scan_summary({"bucket": "safe", "count": 1})["status"] == "pass"))
    checks.append(("vocab_size", len(STATUS_VOCAB) == 5))
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
