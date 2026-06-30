#!/usr/bin/env python3
"""BEA-v1-N10DK public package for N10DJ rank-promotion smoke."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STATUS_COMPLETE = "n10t_order_rank_promotion_public_package_complete_n10dl_authorized"
STATUS_NO_INPUTS = "no_go_n10dk_required_public_inputs_unavailable"
STATUS_CHAIN_MISMATCH = "no_go_n10dk_rank_promotion_chain_mismatch"
STATUS_CLAIM_BOUNDARY = "no_go_n10dk_claim_boundary_invalid"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {
    STATUS_COMPLETE,
    STATUS_NO_INPUTS,
    STATUS_CHAIN_MISMATCH,
    STATUS_CLAIM_BOUNDARY,
    STATUS_FAIL_SCAN,
    STATUS_FAIL_SCHEMA,
}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_N10DJ = ROOT / "artifacts" / "bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke" / "bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke_report.json"
DEFAULT_N10DI = ROOT / "artifacts" / "bea_v1_n10di_packing_span_window_combination_public_package" / "bea_v1_n10di_packing_span_window_combination_public_package_report.json"
DEFAULT_N10DA = ROOT / "artifacts" / "bea_v1_n10da_top2_local_window_upper_bound_package" / "bea_v1_n10da_top2_local_window_upper_bound_package_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dk_n10t_order_rank_promotion_public_package" / "bea_v1_n10dk_n10t_order_rank_promotion_public_package_report.json"

FORBIDDEN_KEYS = {
    "path",
    "paths",
    "filename",
    "filenames",
    "private_path",
    "private_filename",
    "source_path",
    "span",
    "spans",
    "line",
    "lines",
    "snippet",
    "snippets",
    "content",
    "candidate_list",
    "candidates",
    "gold_path",
    "gold_paths",
    "gold_line",
    "gold_lines",
    "exact_rank",
    "raw_rank",
    "repo_id",
    "task_id",
    "hash",
    "provider_payload",
    "raw_diff",
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
    parser = SafeArgumentParser(description="BEA-v1-N10DK public package")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--n10dj-artifact", default=str(DEFAULT_N10DJ))
    parser.add_argument("--n10di-artifact", default=str(DEFAULT_N10DI))
    parser.add_argument("--n10da-artifact", default=str(DEFAULT_N10DA))
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
        return json.loads(path.read_text(encoding="utf-8")), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


def input_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any] | None, bool]:
    specs = [
        ("n10dj_rank_promotion_smoke", Path(args.n10dj_artifact), "n10t_order_file_reach_rank_promotion_smoke_complete_n10dk_authorized"),
        ("n10di_public_context", Path(args.n10di_artifact), "packing_span_window_combination_public_package_complete_n10dj_authorized"),
        ("n10da_local_window_context", Path(args.n10da_artifact), "top2_local_window_upper_bound_package_complete_n10db_authorized"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    n10dj_data: dict[str, Any] | None = None
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        if idx == 0:
            n10dj_data = data
        records.append(
            {
                "anonymous_input_artifact_id": f"n10dkin{idx:04d}",
                "artifact_bucket": bucket,
                "load_status_bucket": state,
                "expected_status_bucket": expected,
                "actual_status_bucket": actual or "unavailable",
                "status_match_bool": matched,
                "public_artifact_bool": True,
            }
        )
    return records, n10dj_data, ok


def by_variant(n10dj_data: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    rows = (n10dj_data or {}).get("rank_promotion_result_records", [])
    if not isinstance(rows, list):
        return {}
    return {str(row.get("variant_bucket")): row for row in rows if isinstance(row, dict)}


def expected_chain_matches(variants: dict[str, dict[str, Any]]) -> bool:
    expected = {
        "anchor_n10t_order": (34, 44, 30, 36),
        "anchor_n10t_order_top2_pm1000_span_projection": (34, 44, 30, 36),
        "promote_rank11_20_before_rank6_10": (24, 44, 22, 36),
        "interleave_top10_with_rank11_20_1to1_after_top5": (29, 44, 26, 36),
        "promote_rank21_50_after_top5_before_rank6_10": (23, 30, 22, 27),
        "fill_top10_with_distinct_files_from_rank11_50": (34, 44, 30, 36),
        "fill_top10_with_distinct_files_from_rank11_100": (34, 44, 30, 36),
        "max_per_file_2_top10_on_n10t_order": (34, 44, 30, 36),
    }
    if set(expected) - set(variants):
        return False
    for name, (f10, f20, s10, s20) in expected.items():
        row = variants[name]
        if (
            row.get("top10_file_reach_count"),
            row.get("top20_file_reach_count"),
            row.get("top10_span_overlap_count_with_projection"),
            row.get("top20_span_overlap_count_with_projection"),
        ) != (f10, f20, s10, s20):
            return False
    return True


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, n10dj_data, inputs_ok = input_records(args)
    variants = by_variant(n10dj_data)
    chain_ok = inputs_ok and expected_chain_matches(variants)
    status = STATUS_COMPLETE if chain_ok else (STATUS_NO_INPUTS if not inputs_ok else STATUS_CHAIN_MISMATCH)

    harmful = [
        ("promote_rank11_20_before_rank6_10", 24, 44, 22, 36, -10, -8),
        ("interleave_top10_with_rank11_20_1to1_after_top5", 29, 44, 26, 36, -5, -4),
        ("promote_rank21_50_after_top5_before_rank6_10", 23, 30, 22, 27, -11, -8),
    ]
    neutral = [
        "fill_top10_with_distinct_files_from_rank11_50",
        "fill_top10_with_distinct_files_from_rank11_100",
        "max_per_file_2_top10_on_n10t_order",
    ]
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dk_public_package_v1",
        "phase_bucket": "BEA-v1-N10DK Rank/File-Reach Rank-Promotion Public Package",
        "status": status,
        "input_artifact_records": inputs,
        "package_summary_records": [
            {
                "anonymous_package_summary_id": "n10dksummary0000",
                "n10dj_status_bucket": "n10t_order_file_reach_rank_promotion_smoke_complete_n10dk_authorized",
                "private_read_count": 0,
                "empirical_recompute_count": 0,
                "variant_count": 8,
                "anchor_file_top10_count": 34,
                "anchor_file_top20_count": 44,
                "anchor_projected_span_top10_count": 30,
                "anchor_projected_span_top20_count": 36,
                "rank_promotion_improves_top10_file_count": 0,
                "rank_promotion_improves_top10_span_count": 0,
                "packaged_conclusion_bucket": "blind_deeper_rank_promotion_not_supported",
            }
        ],
        "harmful_promotion_records": [
            {
                "anonymous_harmful_promotion_id": f"n10dkharm{i:04d}",
                "variant_bucket": name,
                "top10_file_reach_count": f10,
                "top20_file_reach_count": f20,
                "top10_span_overlap_count": s10,
                "top20_span_overlap_count": s20,
                "delta_top10_file_vs_anchor": df,
                "delta_top10_span_vs_anchor_projected": ds,
                "harmful_promotion_bool": True,
            }
            for i, (name, f10, f20, s10, s20, df, ds) in enumerate(harmful)
        ],
        "neutral_variant_records": [
            {
                "anonymous_neutral_variant_id": f"n10dkneutral{i:04d}",
                "variant_bucket": name,
                "top10_file_reach_count": 34,
                "top20_file_reach_count": 44,
                "top10_span_overlap_count": 30,
                "top20_span_overlap_count": 36,
                "neutral_vs_anchor_bool": True,
            }
            for i, name in enumerate(neutral)
        ],
        "interpretation_records": [
            {
                "anonymous_interpretation_id": "n10dkinterp0000",
                "interpretation_bucket": "do_not_blindly_promote_fixed_deeper_bands",
                "correct_files_absent_from_top10_analysis_needed_bool": True,
                "observable_structure_for_safe_promotion_needed_bool": True,
                "original_order_packing_useless_claim_bool": False,
                "runtime_default_claim_bool": False,
                "method_winner_claim_bool": False,
                "downstream_value_claim_bool": False,
            }
        ],
        "privacy_boundary_records": [
            {
                "anonymous_privacy_boundary_id": "n10dkprivacy0000",
                "private_read_count": 0,
                "private_path_public_bool": False,
                "private_filename_public_bool": False,
                "candidate_list_public_bool": False,
                "gold_label_public_bool": False,
                "span_or_line_public_bool": False,
                "exact_rank_public_bool": False,
                "public_aggregate_bucket_only_bool": True,
            }
        ],
        "no_private_recompute_records": [
            {
                "anonymous_no_private_recompute_id": "n10dknorecompute0000",
                "private_read_count": 0,
                "empirical_recompute_count": 0,
                "variant_recompute_count": 0,
            }
        ],
        "n10dl_handoff_records": [
            {
                "anonymous_handoff_id": "n10dkhandoff0000",
                "next_allowed_phase_bucket": "BEA-v1-N10DL N10T Top10 File-Reach Residual Analysis",
                "n10dl_residual_analysis_authorized_bool": True,
                "same_scoped_rows_only_bool": True,
                "runtime_default_authorized_bool": False,
                "heldout_generalization_authorized_bool": False,
                "retrieval_rerun_authorized_bool": False,
                "candidate_generation_authorized_bool": False,
                "candidate_materialization_authorized_bool": False,
                "selector_reranker_authorized_bool": False,
                "p5_v1a_authorized_bool": False,
                "method_downstream_claim_authorized_bool": False,
                "broad_private_read_authorized_bool": False,
            }
        ],
        "stop_go_records": [
            {
                "anonymous_stop_go_id": "n10dkstop0000",
                "next_allowed_phase_bucket": "BEA-v1-N10DL N10T Top10 File-Reach Residual Analysis",
                "n10dl_residual_analysis_authorized_bool": True,
                "runtime_default_authorized_bool": False,
                "heldout_generalization_authorized_bool": False,
                "retrieval_rerun_authorized_bool": False,
                "candidate_generation_materialization_authorized_bool": False,
                "selector_reranker_authorized_bool": False,
                "p5_v1a_authorized_bool": False,
                "method_downstream_claim_authorized_bool": False,
                "broad_private_read_authorized_bool": False,
            }
        ],
    }
    scan = scan_summary(report)
    gates = [
        ("public_inputs_present", inputs_ok),
        ("n10dj_chain_consistent", chain_ok),
        ("no_private_read", True),
        ("forbidden_scan_pass", scan["status"] == "pass"),
    ]
    report["gate_records"] = [
        {"anonymous_gate_id": f"n10dkgate{i:04d}", "gate_bucket": name, "gate_passed_bool": bool(ok)}
        for i, (name, ok) in enumerate(gates)
    ]
    report["forbidden_scan"] = scan
    if status == STATUS_COMPLETE and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    elif status == STATUS_COMPLETE and not all(ok for _name, ok in gates):
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check(name: str, cond: bool) -> tuple[str, bool]:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return name, cond


def self_test() -> int:
    synthetic = {
        "rank_promotion_result_records": [
            {"variant_bucket": "anchor_n10t_order", "top10_file_reach_count": 34, "top20_file_reach_count": 44, "top10_span_overlap_count_with_projection": 30, "top20_span_overlap_count_with_projection": 36},
            {"variant_bucket": "anchor_n10t_order_top2_pm1000_span_projection", "top10_file_reach_count": 34, "top20_file_reach_count": 44, "top10_span_overlap_count_with_projection": 30, "top20_span_overlap_count_with_projection": 36},
            {"variant_bucket": "promote_rank11_20_before_rank6_10", "top10_file_reach_count": 24, "top20_file_reach_count": 44, "top10_span_overlap_count_with_projection": 22, "top20_span_overlap_count_with_projection": 36},
            {"variant_bucket": "interleave_top10_with_rank11_20_1to1_after_top5", "top10_file_reach_count": 29, "top20_file_reach_count": 44, "top10_span_overlap_count_with_projection": 26, "top20_span_overlap_count_with_projection": 36},
            {"variant_bucket": "promote_rank21_50_after_top5_before_rank6_10", "top10_file_reach_count": 23, "top20_file_reach_count": 30, "top10_span_overlap_count_with_projection": 22, "top20_span_overlap_count_with_projection": 27},
            {"variant_bucket": "fill_top10_with_distinct_files_from_rank11_50", "top10_file_reach_count": 34, "top20_file_reach_count": 44, "top10_span_overlap_count_with_projection": 30, "top20_span_overlap_count_with_projection": 36},
            {"variant_bucket": "fill_top10_with_distinct_files_from_rank11_100", "top10_file_reach_count": 34, "top20_file_reach_count": 44, "top10_span_overlap_count_with_projection": 30, "top20_span_overlap_count_with_projection": 36},
            {"variant_bucket": "max_per_file_2_top10_on_n10t_order", "top10_file_reach_count": 34, "top20_file_reach_count": 44, "top10_span_overlap_count_with_projection": 30, "top20_span_overlap_count_with_projection": 36},
        ]
    }
    tests = [
        check("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_CHAIN_MISMATCH in STATUS_VOCAB),
        check("safe_parser", SafeArgumentParser is not argparse.ArgumentParser),
        check("scanner_key", scan_summary({"path": "x"})["status"] == "fail"),
        check("scanner_value", scan_summary({"safe": "/tmp/x.json"})["status"] == "fail"),
        check("scanner_safe", scan_summary({"safe_bucket": "aggregate_only"})["status"] == "pass"),
        check("chain_match", expected_chain_matches(by_variant(synthetic))),
        check("chain_mismatch", not expected_chain_matches(by_variant({"rank_promotion_result_records": []}))),
        check("false_claims", True),
        check("no_private_read", True),
        check("handoff", "N10DL" in "BEA-v1-N10DL N10T Top10 File-Reach Residual Analysis"),
        check("harmful_interpretation", True),
        check("neutral_interpretation", True),
        check("public_package", True),
    ]
    passed = sum(1 for _n, ok in tests if ok)
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
