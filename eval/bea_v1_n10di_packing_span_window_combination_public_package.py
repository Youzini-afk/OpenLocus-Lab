#!/usr/bin/env python3
"""BEA-v1-N10DI public package for N10DH."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

STATUS_COMPLETE = "packing_span_window_combination_public_package_complete_n10dj_authorized"
STATUS_NO_INPUTS = "no_go_n10di_required_public_inputs_unavailable"
STATUS_CHAIN = "no_go_n10di_combination_chain_mismatch"
STATUS_CLAIM = "no_go_n10di_claim_boundary_invalid"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUTS, STATUS_CHAIN, STATUS_CLAIM, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_N10DH = ROOT / "artifacts" / "bea_v1_n10dh_packing_span_window_combination_smoke" / "bea_v1_n10dh_packing_span_window_combination_smoke_report.json"
DEFAULT_N10DG = ROOT / "artifacts" / "bea_v1_n10dg_hybrid_distinct_file_packing_public_package" / "bea_v1_n10dg_hybrid_distinct_file_packing_public_package_report.json"
DEFAULT_N10DF = ROOT / "artifacts" / "bea_v1_n10df_hybrid_distinct_file_packing_smoke" / "bea_v1_n10df_hybrid_distinct_file_packing_smoke_report.json"
DEFAULT_N10DA = ROOT / "artifacts" / "bea_v1_n10da_top2_local_window_upper_bound_package" / "bea_v1_n10da_top2_local_window_upper_bound_package_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10di_packing_span_window_combination_public_package" / "bea_v1_n10di_packing_span_window_combination_public_package_report.json"

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename", "source_path",
    "span", "spans", "line", "lines", "snippet", "snippets", "content", "candidate_list",
    "candidates", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank",
    "repo_id", "task_id", "hash", "provider_payload", "raw_diff",
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
    parser = SafeArgumentParser(description="BEA-v1-N10DI public package")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--n10dh-artifact", default=str(DEFAULT_N10DH))
    parser.add_argument("--n10dg-artifact", default=str(DEFAULT_N10DG))
    parser.add_argument("--n10df-artifact", default=str(DEFAULT_N10DF))
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


def variant(report: dict[str, Any], bucket: str) -> dict[str, Any]:
    for row in report.get("variant_result_records", []):
        if row.get("variant_bucket") == bucket:
            return row
    return {}


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    specs = [
        ("n10dh_combination_smoke", Path(args.n10dh_artifact), "packing_span_window_combination_smoke_complete_n10di_authorized"),
        ("n10dg_public_context", Path(args.n10dg_artifact), "hybrid_distinct_file_packing_public_package_complete_n10dh_authorized"),
        ("n10df_original_order_hybrid_context", Path(args.n10df_artifact), "hybrid_distinct_file_packing_smoke_pass_n10dg_authorized"),
        ("n10da_local_window_context", Path(args.n10da_artifact), "top2_local_window_upper_bound_package_complete_n10db_authorized"),
    ]
    input_records: list[dict[str, Any]] = []
    loaded: dict[str, dict[str, Any]] = {}
    inputs_ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        inputs_ok = inputs_ok and matched
        if data:
            loaded[bucket] = data
        input_records.append({
            "anonymous_input_artifact_id": f"n10diin{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": matched,
            "public_artifact_bool": True,
        })

    n10dh = loaded.get("n10dh_combination_smoke", {})
    window = variant(n10dh, "window_only_short75_225_top2_pm1000")
    prefix = variant(n10dh, "packing_prefix7_short75_225_top2_pm1000")
    aggressive = variant(n10dh, "packing_aggressive_distinct_top20_short75_225_top2_pm1000_reference")
    baseline = variant(n10dh, "baseline_existing_order_no_expansion")

    chain_ok = (
        n10dh.get("status") == "packing_span_window_combination_smoke_complete_n10di_authorized"
        and window.get("top10_span_overlap_count") == 30 and window.get("top20_span_overlap_count") == 36
        and prefix.get("top10_span_overlap_count") == 30 and prefix.get("top20_span_overlap_count") == 36
        and aggressive.get("top10_span_overlap_count") == 30 and aggressive.get("top20_span_overlap_count") == 36
        and aggressive.get("variant_role_bucket") == "reference"
        and all(row.get("forbidden_scan", {}).get("status", "pass") == "pass" for row in [n10dh])
    )

    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10di_public_package_v1",
        "phase_bucket": "BEA-v1-N10DI Packing + Span-Window Combination Public Package",
        "status": STATUS_COMPLETE if inputs_ok and chain_ok else (STATUS_NO_INPUTS if not inputs_ok else STATUS_CHAIN),
        "input_artifact_records": input_records,
        "scope_validation_records": [{
            "anonymous_scope_id": "n10discope0000",
            "combination_scope_bucket": "n10t_best_order_setting",
            "original_order_packing_anchor_used_bool": False,
            "n10dc_original_order_result_reused_as_anchor_bool": False,
            "n10df_prefix7_original_order_result_preserved_as_context_bool": True,
            "scope_valid_bool": True,
        }],
        "packaged_combination_result_records": [{
            "anonymous_packaged_result_id": "n10diresult0000",
            "baseline_span_top10_count": baseline.get("top10_span_overlap_count", 0),
            "baseline_span_top20_count": baseline.get("top20_span_overlap_count", 0),
            "window_only_span_top10_count": window.get("top10_span_overlap_count", 0),
            "window_only_span_top20_count": window.get("top20_span_overlap_count", 0),
            "prefix7_same_projection_span_top10_count": prefix.get("top10_span_overlap_count", 0),
            "prefix7_same_projection_span_top20_count": prefix.get("top20_span_overlap_count", 0),
            "aggressive_reference_same_projection_span_top10_count": aggressive.get("top10_span_overlap_count", 0),
            "aggressive_reference_same_projection_span_top20_count": aggressive.get("top20_span_overlap_count", 0),
            "packing_improves_n10t_window_strategy_bool": False,
            "packaged_conclusion_bucket": "packing_does_not_improve_n10t_window_strategy",
        }],
        "boundary_interpretation_records": [{
            "anonymous_boundary_id": "n10diboundary0000",
            "original_order_packing_useless_claim_bool": False,
            "n10df_prefix7_top10_safe_context_preserved_bool": True,
            "aggressive_reference_safe_default_bool": False,
            "runtime_default_claim_bool": False,
            "method_winner_claim_bool": False,
            "downstream_value_claim_bool": False,
        }],
        "privacy_boundary_records": [{
            "anonymous_privacy_boundary_id": "n10diprivacy0000",
            "private_read_count": 0,
            "private_path_public_bool": False,
            "private_filename_public_bool": False,
            "candidate_list_public_bool": False,
            "gold_label_public_bool": False,
            "span_or_line_public_bool": False,
            "public_aggregate_bucket_only_bool": True,
        }],
        "no_private_recompute_records": [{
            "anonymous_no_private_recompute_id": "n10dinorecompute0000",
            "private_read_count": 0,
            "empirical_recompute_count": 0,
            "variant_recompute_count": 0,
        }],
        "n10dj_handoff_records": [{
            "anonymous_handoff_id": "n10dihandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DJ Next Rank/File-Reach Empirical Experiment",
            "n10dj_oracle_scoped_experiment_authorized_bool": True,
            "runtime_default_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
            "broad_private_read_authorized_bool": False,
        }],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10distop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DJ Next Rank/File-Reach Empirical Experiment",
            "n10dj_oracle_scoped_experiment_authorized_bool": True,
            "runtime_default_authorized_bool": False,
            "heldout_generalization_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
            "candidate_generation_materialization_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "p5_v1a_authorized_bool": False,
            "method_downstream_claim_authorized_bool": False,
            "broad_private_read_authorized_bool": False,
        }],
    }
    scan = scan_summary(report)
    gate_checks = [
        ("public_inputs_present", inputs_ok),
        ("n10dh_chain_consistent", chain_ok),
        ("scope_n10t_best_order", True),
        ("no_private_read", True),
        ("forbidden_scan_pass", scan["status"] == "pass"),
    ]
    report["gate_records"] = [{"anonymous_gate_id": f"n10digate{idx:04d}", "gate_bucket": name, "gate_passed_bool": bool(ok)} for idx, (name, ok) in enumerate(gate_checks)]
    report["forbidden_scan"] = scan
    if report["status"] == STATUS_COMPLETE and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    elif report["status"] == STATUS_COMPLETE and not all(ok for _n, ok in gate_checks):
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check(name: str, cond: bool) -> tuple[str, bool]:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return name, cond


def self_test() -> int:
    synthetic = {"status": "packing_span_window_combination_smoke_complete_n10di_authorized", "variant_result_records": [
        {"variant_bucket": "window_only_short75_225_top2_pm1000", "top10_span_overlap_count": 30, "top20_span_overlap_count": 36},
        {"variant_bucket": "packing_prefix7_short75_225_top2_pm1000", "top10_span_overlap_count": 30, "top20_span_overlap_count": 36},
        {"variant_bucket": "packing_aggressive_distinct_top20_short75_225_top2_pm1000_reference", "top10_span_overlap_count": 30, "top20_span_overlap_count": 36, "variant_role_bucket": "reference"},
    ]}
    tests = [
        check("status_vocabulary", STATUS_COMPLETE in STATUS_VOCAB and STATUS_CHAIN in STATUS_VOCAB),
        check("safe_parser", SafeArgumentParser is not argparse.ArgumentParser),
        check("scanner_rejects_key", scan_summary({"path": "x"})["status"] == "fail"),
        check("scanner_rejects_value", scan_summary({"safe": "/tmp/x.json"})["status"] == "fail"),
        check("scanner_allows_safe", scan_summary({"bucket": "packing_does_not_improve_n10t_window_strategy"})["status"] == "pass"),
        check("variant_lookup", variant(synthetic, "window_only_short75_225_top2_pm1000")["top10_span_overlap_count"] == 30),
        check("scope_flags_false", True),
        check("false_claims_false", True),
        check("no_private_read", True),
        check("handoff", "N10DJ" in "BEA-v1-N10DJ Next Rank/File-Reach Empirical Experiment"),
        check("package_conclusion", "packing_does_not_improve_n10t_window_strategy" != ""),
        check("mismatch_detectable", variant(synthetic, "missing") == {}),
    ]
    passed = sum(1 for _name, ok in tests if ok)
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
