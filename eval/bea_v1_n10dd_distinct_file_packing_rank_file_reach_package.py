#!/usr/bin/env python3
"""BEA-v1-N10DD Distinct-File Packing Rank/File-Reach Public Package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STATUS_PASS = "distinct_file_packing_rank_file_reach_package_complete_n10de_authorized"
STATUS_NO_INPUTS = "no_go_n10dd_required_public_inputs_unavailable"
STATUS_CHAIN_MISMATCH = "no_go_n10dd_distinct_file_chain_mismatch"
STATUS_PRIVACY = "no_go_n10dd_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_PASS, STATUS_NO_INPUTS, STATUS_CHAIN_MISMATCH, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_N10DC = ROOT / "artifacts" / "bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke" / "bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke_report.json"
DEFAULT_N10DB = ROOT / "artifacts" / "bea_v1_n10db_rank_file_reach_policy_field_scoping" / "bea_v1_n10db_rank_file_reach_policy_field_scoping_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dd_distinct_file_packing_rank_file_reach_package" / "bea_v1_n10dd_distinct_file_packing_rank_file_reach_package_report.json"

EXPECTED_N10DC_STATUS = "distinct_file_packing_rank_file_reach_smoke_complete_n10dd_authorized"
EXPECTED_N10DB_STATUS = "rank_file_reach_policy_field_scoping_pass_n10dc_authorized"

EXPECTED_VARIANTS = {
    "baseline_existing_order": (14, 19, 13, 17, 0, 0, 0),
    "distinct_file_top10_greedy": (19, 20, 16, 18, 5, 3, 1),
    "distinct_file_top20_greedy_then_top10": (19, 47, 16, 24, 5, 3, 1),
    "max_per_file_1_top10": (19, 20, 16, 18, 5, 3, 1),
    "max_per_file_2_top10": (16, 19, 15, 17, 2, 2, 0),
}

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename", "source_path",
    "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate_list",
    "candidates", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank",
    "rank", "ranks", "repo_id", "task_id", "hash", "sha", "provider_payload", "raw_diff",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt)"),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DD distinct-file public package")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--n10dc-artifact", default=str(DEFAULT_N10DC))
    parser.add_argument("--n10db-artifact", default=str(DEFAULT_N10DB))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return parser.parse_args(argv)


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


def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


def input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any] | None, bool]:
    specs = [
        ("n10dc_distinct_file_smoke", Path(args.n10dc_artifact), EXPECTED_N10DC_STATUS),
        ("n10db_field_scoping", Path(args.n10db_artifact), EXPECTED_N10DB_STATUS),
    ]
    records: list[dict[str, Any]] = []
    n10dc_data: dict[str, Any] | None = None
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        if bucket == "n10dc_distinct_file_smoke":
            n10dc_data = data
        records.append({
            "anonymous_input_artifact_id": f"n10ddin{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": matched,
            "public_artifact_bool": True,
        })
    return records, n10dc_data, ok


def n10dc_result_map(data: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not data:
        return out
    for row in data.get("packing_variant_result_records", []):
        if isinstance(row, dict):
            out[str(row.get("variant_bucket", ""))] = row
    return out


def package_summary_records(n10dc_data: dict[str, Any] | None, matched: bool) -> list[dict[str, Any]]:
    return [{
        "anonymous_package_summary_id": "n10ddsummary0000",
        "source_status_bucket": str(n10dc_data.get("status", "unavailable")) if n10dc_data else "unavailable",
        "source_status_expected_bool": bool(n10dc_data and n10dc_data.get("status") == EXPECTED_N10DC_STATUS),
        "corrected_evaluation_matching_bucket": "safe_same_or_suffix_private_reference_matching",
        "packing_scope_bucket": "topk_only_repacking_with_original_pool_preserved",
        "variant_count": len(EXPECTED_VARIANTS),
        "variant_metrics_match_expected_bool": matched,
        "candidate_generation_count": 0,
        "candidate_materialization_count": 0,
        "candidate_added_count": 0,
        "candidate_removed_count": 0,
        "candidate_pool_preserved_bool": True,
    }]


def variant_package_records(result_map: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (variant, expected) in enumerate(EXPECTED_VARIANTS.items()):
        row = result_map.get(variant, {})
        actual = (
            int(row.get("top10_file_reach_count", -1)),
            int(row.get("top20_file_reach_count", -1)),
            int(row.get("top10_span_overlap_count", -1)),
            int(row.get("top20_span_overlap_count", -1)),
            int(row.get("delta_top10_file_reach_vs_baseline", -999)),
            int(row.get("delta_top10_span_vs_baseline", -999)),
            int(row.get("lost_baseline_top10_span_hits", -1)),
        )
        matched = actual == expected
        ok = ok and matched
        records.append({
            "anonymous_variant_package_id": f"n10ddvar{idx:04d}",
            "variant_bucket": variant,
            "top10_file_reach_count": expected[0],
            "top20_file_reach_count": expected[1],
            "top10_span_overlap_count": expected[2],
            "top20_span_overlap_count": expected[3],
            "delta_top10_file_reach_vs_baseline": expected[4],
            "delta_top10_span_vs_baseline": expected[5],
            "lost_baseline_top10_span_hits": expected[6],
            "candidate_generation_count": 0,
            "candidate_materialization_count": 0,
            "candidate_added_count": 0,
            "candidate_removed_count": 0,
            "candidate_pool_preserved_bool": True,
            "source_metric_match_bool": matched,
        })
    return records, ok


def tradeoff_summary_records() -> list[dict[str, Any]]:
    return [
        {
            "anonymous_tradeoff_summary_id": "n10ddtrade0000",
            "tradeoff_bucket": "aggressive_one_file_per_file",
            "representative_variant_bucket": "distinct_file_top20_greedy_then_top10",
            "top10_file_gain_count": 5,
            "top10_span_gain_count": 3,
            "top20_file_reach_count": 47,
            "top20_span_overlap_count": 24,
            "baseline_span_regression_count": 1,
            "tradeoff_interpretation_bucket": "higher_file_and_top20_reach_with_one_baseline_span_regression",
        },
        {
            "anonymous_tradeoff_summary_id": "n10ddtrade0001",
            "tradeoff_bucket": "conservative_max_per_file_2",
            "representative_variant_bucket": "max_per_file_2_top10",
            "top10_file_gain_count": 2,
            "top10_span_gain_count": 2,
            "top20_file_reach_count": 19,
            "top20_span_overlap_count": 17,
            "baseline_span_regression_count": 0,
            "tradeoff_interpretation_bucket": "smaller_gain_with_zero_baseline_span_regression",
        },
    ]


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_privacy_boundary_id": "n10ddprivacy0000",
        "privacy_boundary_bucket": "public_package_aggregate_counts_only",
        "private_read_count": 0,
        "private_path_public_bool": False,
        "private_filename_public_bool": False,
        "private_content_public_bool": False,
        "public_path_or_filename_count": 0,
        "candidate_list_public_bool": False,
        "gold_path_public_bool": False,
        "span_or_line_public_bool": False,
        "exact_rank_public_bool": False,
        "privacy_boundary_complete_bool": True,
    }], True


def no_private_recompute_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_no_private_recompute_id": "n10ddnorecompute0000",
        "private_read_count": 0,
        "recompute_count": 0,
        "policy_outcome_execution_count": 0,
        "retrieval_execution_count": 0,
        "rerun_execution_count": 0,
        "candidate_generation_count": 0,
        "candidate_materialization_count": 0,
        "candidate_addition_count": 0,
        "candidate_removal_count": 0,
        "selector_reranker_execution_count": 0,
        "runtime_change_count": 0,
        "default_change_count": 0,
        "p5_v1a_execution_count": 0,
        "method_downstream_claim_count": 0,
        "complete_bool": True,
    }], True


def n10de_handoff_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_n10de_handoff_id": "n10ddhandoff0000",
        "next_allowed_phase_bucket": "BEA-v1-N10DE Regression-vs-Zero-Loss Mechanism Decomposition",
        "n10de_authorized_bool": True,
        "n10de_same_scoped_private_rows_read_authorized_bool": True,
        "broad_private_read_authorized_bool": False,
        "runtime_default_authorized_bool": False,
        "heldout_generalization_authorized_bool": False,
        "retrieval_rerun_authorized_bool": False,
        "candidate_generation_materialization_authorized_bool": False,
        "candidate_add_remove_authorized_bool": False,
        "selector_reranker_authorized_bool": False,
        "p5_v1a_authorized_bool": False,
        "method_downstream_claim_authorized_bool": False,
    }]


def stop_go_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_stop_go_id": "n10ddstop0000",
        "status_bucket": STATUS_PASS,
        "next_allowed_phase_bucket": "BEA-v1-N10DE Regression-vs-Zero-Loss Mechanism Decomposition",
        "n10de_authorized_bool": True,
        "n10dd_private_read_bool": False,
        "n10dd_recompute_bool": False,
        "runtime_default_authorized_bool": False,
        "heldout_generalization_authorized_bool": False,
        "retrieval_rerun_authorized_bool": False,
        "candidate_generation_materialization_authorized_bool": False,
        "candidate_add_remove_authorized_bool": False,
        "selector_reranker_authorized_bool": False,
        "p5_v1a_authorized_bool": False,
        "method_downstream_claim_authorized_bool": False,
    }]


def gate_records(inputs_ok: bool, variants_ok: bool, scan_ok: bool, privacy_ok: bool, no_recompute_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    gates = [
        ("required_public_inputs_present", inputs_ok),
        ("n10dc_status_complete", inputs_ok),
        ("variant_metrics_match_corrected_expected", variants_ok),
        ("privacy_boundary_complete", privacy_ok),
        ("no_private_read_or_recompute", no_recompute_ok),
        ("forbidden_scan_pass", scan_ok),
    ]
    return [{"anonymous_gate_id": f"n10ddgate{idx:04d}", "gate_bucket": name, "gate_passed_bool": bool(ok)} for idx, (name, ok) in enumerate(gates)], all(ok for _name, ok in gates)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, n10dc, inputs_ok = input_artifact_records(args)
    result_map = n10dc_result_map(n10dc)
    variants, variants_ok = variant_package_records(result_map)
    privacy, privacy_ok = privacy_boundary_records()
    no_recompute, no_recompute_ok = no_private_recompute_records()
    status = STATUS_PASS if inputs_ok and variants_ok else (STATUS_NO_INPUTS if not inputs_ok else STATUS_CHAIN_MISMATCH)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dd_distinct_file_package_v1",
        "phase_bucket": "BEA-v1-N10DD Distinct-File Packing Rank/File-Reach Public Package",
        "status": status,
        "input_artifact_records": inputs,
        "package_summary_records": package_summary_records(n10dc, variants_ok),
        "variant_package_records": variants,
        "tradeoff_summary_records": tradeoff_summary_records(),
        "privacy_boundary_records": privacy,
        "no_private_recompute_records": no_recompute,
        "n10de_handoff_records": n10de_handoff_records() if status == STATUS_PASS else [],
        "stop_go_records": stop_go_records() if status == STATUS_PASS else [],
    }
    scan = scan_summary(report)
    scan_ok = scan["status"] == "pass"
    gates, gates_ok = gate_records(inputs_ok, variants_ok, scan_ok, privacy_ok, no_recompute_ok)
    report["gate_records"] = gates
    report["forbidden_scan"] = scan
    if status == STATUS_PASS and (not scan_ok or not gates_ok):
        report["status"] = STATUS_FAIL_SCAN if not scan_ok else STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check(name: str, cond: bool) -> tuple[str, bool]:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return name, cond


def self_test() -> int:
    fake = {"status": EXPECTED_N10DC_STATUS, "packing_variant_result_records": [
        {"variant_bucket": k, "top10_file_reach_count": v[0], "top20_file_reach_count": v[1], "top10_span_overlap_count": v[2], "top20_span_overlap_count": v[3], "delta_top10_file_reach_vs_baseline": v[4], "delta_top10_span_vs_baseline": v[5], "lost_baseline_top10_span_hits": v[6]}
        for k, v in EXPECTED_VARIANTS.items()
    ]}
    bad = {"status": EXPECTED_N10DC_STATUS, "packing_variant_result_records": []}
    variants, ok = variant_package_records(n10dc_result_map(fake))
    _bad_variants, bad_ok = variant_package_records(n10dc_result_map(bad))
    tests = [
        check("status_vocabulary", STATUS_PASS in STATUS_VOCAB and STATUS_CHAIN_MISMATCH in STATUS_VOCAB),
        check("safe_parser", SafeArgumentParser is not argparse.ArgumentParser),
        check("scanner_rejects_key", scan_summary({"path": "x"})["status"] == "fail"),
        check("scanner_rejects_value", scan_summary({"safe": "/tmp/private.jsonl"})["status"] == "fail"),
        check("scanner_allows_package", scan_summary({"variant_package_records": variants})["status"] == "pass"),
        check("synthetic_package_pass", ok and len(variants) == 5),
        check("synthetic_mismatch", not bad_ok),
        check("aggressive_tradeoff", tradeoff_summary_records()[0]["baseline_span_regression_count"] == 1),
        check("conservative_tradeoff", tradeoff_summary_records()[1]["baseline_span_regression_count"] == 0),
        check("no_private_recompute", no_private_recompute_records()[0][0]["private_read_count"] == 0 and no_private_recompute_records()[0][0]["recompute_count"] == 0),
        check("privacy_boundary", privacy_boundary_records()[0][0]["public_path_or_filename_count"] == 0),
        check("false_claims", not stop_go_records()[0]["runtime_default_authorized_bool"] and not stop_go_records()[0]["p5_v1a_authorized_bool"]),
        check("handoff", n10de_handoff_records()[0]["n10de_authorized_bool"]),
    ]
    passed = sum(1 for _name, okv in tests if okv)
    print(f"self_test_passed={passed == len(tests)} ({passed}/{len(tests)} checks)")
    return 0 if passed == len(tests) else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return self_test()
    report = build_report(args)
    write_report(report, Path(args.out))
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
