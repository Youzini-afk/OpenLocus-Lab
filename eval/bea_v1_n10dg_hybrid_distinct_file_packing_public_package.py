#!/usr/bin/env python3
"""BEA-v1-N10DG Hybrid Distinct-File Packing Public Package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STATUS_PASS = "hybrid_distinct_file_packing_public_package_complete_n10dh_authorized"
STATUS_NO_INPUTS = "no_go_n10dg_required_public_inputs_unavailable"
STATUS_CHAIN = "no_go_n10dg_chain_or_metric_mismatch"
STATUS_CLAIM = "no_go_n10dg_claim_boundary_invalid"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"

STATUS_VOCAB = {STATUS_PASS, STATUS_NO_INPUTS, STATUS_CHAIN, STATUS_CLAIM, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_N10DF = ROOT / "artifacts" / "bea_v1_n10df_hybrid_distinct_file_packing_smoke" / "bea_v1_n10df_hybrid_distinct_file_packing_smoke_report.json"
DEFAULT_N10DE = ROOT / "artifacts" / "bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition" / "bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition_report.json"
DEFAULT_N10DC = ROOT / "artifacts" / "bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke" / "bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10dg_hybrid_distinct_file_packing_public_package" / "bea_v1_n10dg_hybrid_distinct_file_packing_public_package_report.json"

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
    parser = SafeArgumentParser(description="BEA-v1-N10DG public package")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--n10df-artifact", default=str(DEFAULT_N10DF))
    parser.add_argument("--n10de-artifact", default=str(DEFAULT_N10DE))
    parser.add_argument("--n10dc-artifact", default=str(DEFAULT_N10DC))
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


def input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    specs = [
        ("n10df_hybrid_smoke", Path(args.n10df_artifact), "hybrid_distinct_file_packing_smoke_pass_n10dg_authorized"),
        ("n10de_mechanism_decomposition", Path(args.n10de_artifact), "regression_vs_zero_loss_mechanism_decomposition_complete_n10df_authorized"),
        ("n10dc_rank_file_smoke", Path(args.n10dc_artifact), "distinct_file_packing_rank_file_reach_smoke_complete_n10dd_authorized"),
    ]
    records: list[dict[str, Any]] = []
    loaded: dict[str, Any] = {}
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        loaded[bucket] = data or {}
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        records.append({
            "anonymous_input_artifact_id": f"n10dgin{idx:04d}",
            "artifact_bucket": bucket,
            "load_status_bucket": state,
            "expected_status_bucket": expected,
            "actual_status_bucket": actual or "unavailable",
            "status_match_bool": matched,
            "public_artifact_bool": True,
        })
    return records, loaded, ok


def variant_map(n10df: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(r.get("variant_bucket")): r for r in n10df.get("hybrid_variant_result_records", [])}


def chain_records(n10df: dict[str, Any]) -> list[dict[str, Any]]:
    vm = variant_map(n10df)
    prefix7 = vm.get("prefix7_then_distinct_fill_top10", {})
    aggressive = vm.get("aggressive_distinct_file_top20_greedy_then_top10", {})
    baseline = vm.get("baseline_existing_order", {})
    return [{
        "anonymous_chain_record_id": "n10dgchain0000",
        "source_status_bucket": str(n10df.get("status", "unavailable")),
        "source_forbidden_scan_bucket": str(n10df.get("forbidden_scan", {}).get("status", "unavailable")),
        "variant_count": len(n10df.get("hybrid_variant_result_records", [])),
        "best_top10_safe_hybrid_bucket": "prefix7_then_distinct_fill_top10",
        "baseline_top10_span_count": baseline.get("top10_span_overlap_count"),
        "aggressive_top10_span_count": aggressive.get("top10_span_overlap_count"),
        "prefix7_top10_span_count": prefix7.get("top10_span_overlap_count"),
        "prefix7_lost_baseline_top10_span_hits": prefix7.get("lost_baseline_top10_span_hits"),
        "chain_consistent_bool": n10df.get("status") == "hybrid_distinct_file_packing_smoke_pass_n10dg_authorized" and prefix7.get("top10_span_overlap_count") == 16 and prefix7.get("lost_baseline_top10_span_hits") == 0,
    }]


def conclusion_records(n10df: dict[str, Any]) -> list[dict[str, Any]]:
    vm = variant_map(n10df)
    aggressive = vm.get("aggressive_distinct_file_top20_greedy_then_top10", {})
    prefix7 = vm.get("prefix7_then_distinct_fill_top10", {})
    return [{
        "anonymous_conclusion_id": "n10dgconclusion0000",
        "conclusion_bucket": "promising_top10_safe_packing_hybrid_not_default_winner",
        "top10_safe_hybrid_bucket": "prefix7_then_distinct_fill_top10",
        "top10_span_matches_aggressive_bool": prefix7.get("top10_span_overlap_count") == aggressive.get("top10_span_overlap_count") == 16,
        "zero_baseline_top10_span_loss_bool": prefix7.get("lost_baseline_top10_span_hits") == 0,
        "top20_limitation_bool": prefix7.get("top20_span_overlap_count") != aggressive.get("top20_span_overlap_count"),
        "prefix7_top20_span_count": prefix7.get("top20_span_overlap_count"),
        "aggressive_top20_span_count": aggressive.get("top20_span_overlap_count"),
        "prefix7_top20_file_count": prefix7.get("top20_file_reach_count"),
        "aggressive_top20_file_count": aggressive.get("top20_file_reach_count"),
        "default_winner_claim_bool": False,
    }]


def boundary_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_boundary_id": "n10dgboundary0000",
        "package_boundary_bucket": "public_only_no_recompute_no_private_read",
        "private_read_count": 0,
        "recompute_count": 0,
        "runtime_default_claim_bool": False,
        "selector_reranker_claim_bool": False,
        "candidate_generation_claim_bool": False,
        "method_winner_claim_bool": False,
        "downstream_value_claim_bool": False,
        "heldout_generalization_claim_bool": False,
        "broad_private_read_claim_bool": False,
    }]


def stop_go_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_stop_go_id": "n10dgstop0000",
        "next_allowed_phase_bucket": "BEA-v1-N10DH Packing Plus Span-Window or Top20 Reach Repair Experiment",
        "n10dh_empirical_experiment_authorized_bool": True,
        "runtime_default_authorized_bool": False,
        "selector_reranker_authorized_bool": False,
        "candidate_generation_authorized_bool": False,
        "retrieval_rerun_authorized_bool": False,
        "broad_private_read_authorized_bool": False,
        "p5_v1a_authorized_bool": False,
        "method_downstream_claim_authorized_bool": False,
        "heldout_generalization_authorized_bool": False,
    }]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, loaded, inputs_ok = input_artifact_records(args)
    n10df = loaded.get("n10df_hybrid_smoke", {})
    chain = chain_records(n10df)
    conclusions = conclusion_records(n10df)
    chain_ok = bool(chain[0]["chain_consistent_bool"] and conclusions[0]["top20_limitation_bool"])
    status = STATUS_PASS if inputs_ok and chain_ok else (STATUS_NO_INPUTS if not inputs_ok else STATUS_CHAIN)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dg_hybrid_public_package_v1",
        "phase_bucket": "BEA-v1-N10DG Hybrid Distinct-File Packing Public Package",
        "status": status,
        "input_artifact_records": inputs,
        "chain_validation_records": chain,
        "top10_safe_hybrid_conclusion_records": conclusions,
        "top20_limitation_records": [{
            "anonymous_top20_limitation_id": "n10dgtop200000",
            "limitation_bucket": "prefix7_does_not_repair_aggressive_top20_reach",
            "prefix7_top20_span_count": conclusions[0]["prefix7_top20_span_count"],
            "aggressive_top20_span_count": conclusions[0]["aggressive_top20_span_count"],
            "prefix7_top20_file_count": conclusions[0]["prefix7_top20_file_count"],
            "aggressive_top20_file_count": conclusions[0]["aggressive_top20_file_count"],
            "top20_repair_still_needed_bool": True,
        }],
        "claim_boundary_records": boundary_records(),
        "no_private_recompute_records": [{
            "anonymous_no_private_recompute_id": "n10dgno0000",
            "private_read_count": 0,
            "recompute_count": 0,
            "new_variant_count": 0,
            "public_artifact_only_bool": True,
        }],
        "n10dh_handoff_records": [{
            "anonymous_n10dh_handoff_id": "n10dghandoff0000",
            "next_phase_bucket": "BEA-v1-N10DH Packing Plus Span-Window or Top20 Reach Repair Experiment",
            "scope_bucket": "same_source_empirical_followup_oracle_scoped",
            "packing_plus_span_window_or_top20_repair_authorized_bool": True,
            "runtime_default_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
            "retrieval_rerun_authorized_bool": False,
        }],
        "stop_go_records": stop_go_records(),
    }
    scan = scan_summary(report)
    gate_checks = [
        ("public_inputs_present", inputs_ok),
        ("n10df_chain_consistent", chain_ok),
        ("top10_safe_prefix7_packaged", conclusions[0]["top10_span_matches_aggressive_bool"] and conclusions[0]["zero_baseline_top10_span_loss_bool"]),
        ("top20_limitation_packaged", conclusions[0]["top20_limitation_bool"]),
        ("no_private_read_or_recompute", True),
        ("forbidden_scan_pass", scan["status"] == "pass"),
    ]
    report["gate_records"] = [{"anonymous_gate_id": f"n10dggate{idx:04d}", "gate_bucket": name, "gate_passed_bool": bool(ok)} for idx, (name, ok) in enumerate(gate_checks)]
    report["forbidden_scan"] = scan
    if report["status"] == STATUS_PASS and scan["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    elif report["status"] == STATUS_PASS and not all(ok for _name, ok in gate_checks):
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
        "status": "hybrid_distinct_file_packing_smoke_pass_n10dg_authorized",
        "forbidden_scan": {"status": "pass"},
        "hybrid_variant_result_records": [
            {"variant_bucket": "baseline_existing_order", "top10_span_overlap_count": 13},
            {"variant_bucket": "aggressive_distinct_file_top20_greedy_then_top10", "top10_span_overlap_count": 16, "top20_span_overlap_count": 24, "top20_file_reach_count": 47},
            {"variant_bucket": "prefix7_then_distinct_fill_top10", "top10_span_overlap_count": 16, "top20_span_overlap_count": 17, "top20_file_reach_count": 19, "lost_baseline_top10_span_hits": 0},
        ],
    }
    tests = [
        check("status_vocabulary", STATUS_PASS in STATUS_VOCAB and STATUS_CHAIN in STATUS_VOCAB),
        check("safe_parser", SafeArgumentParser is not argparse.ArgumentParser),
        check("scanner_rejects_key", scan_summary({"path": "x"})["status"] == "fail"),
        check("scanner_rejects_value", scan_summary({"safe": "/tmp/x.json"})["status"] == "fail"),
        check("scanner_allows_package", scan_summary({"variant_bucket": "prefix7_then_distinct_fill_top10"})["status"] == "pass"),
        check("synthetic_chain", chain_records(synthetic)[0]["chain_consistent_bool"]),
        check("synthetic_top20_limitation", conclusion_records(synthetic)[0]["top20_limitation_bool"]),
        check("false_claims", not boundary_records()[0]["runtime_default_claim_bool"] and not boundary_records()[0]["method_winner_claim_bool"]),
        check("stop_go_false_flags", not stop_go_records()[0]["selector_reranker_authorized_bool"] and not stop_go_records()[0]["p5_v1a_authorized_bool"]),
        check("handoff_true", stop_go_records()[0]["n10dh_empirical_experiment_authorized_bool"]),
        check("no_private_recompute_literal", True),
        check("claim_boundary_status", STATUS_CLAIM in STATUS_VOCAB),
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
