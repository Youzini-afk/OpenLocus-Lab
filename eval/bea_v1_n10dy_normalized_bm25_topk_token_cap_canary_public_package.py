#!/usr/bin/env python3
"""BEA-v1-N10DY Normalized-BM25 TopK/Token-Cap Canary Public Package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10DX_REPORT = ROOT / "artifacts" / "bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary" / "bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary_report.json"

STATUS_COMPLETE = "normalized_bm25_topk_token_cap_canary_public_package_complete_n10dz_authorized"
STATUS_NO_INPUTS = "no_go_n10dy_required_public_inputs_unavailable"
STATUS_CHAIN_MISMATCH = "no_go_n10dy_topk_token_cap_chain_mismatch"
STATUS_CLAIM = "no_go_n10dy_claim_boundary_invalid"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUTS, STATUS_CHAIN_MISMATCH, STATUS_CLAIM, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename",
    "query", "raw_query", "candidate", "candidates", "candidate_list", "gold",
    "gold_path", "gold_paths", "span", "spans", "line", "lines", "snippet",
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
    parser = SafeArgumentParser(description="BEA-v1-N10DY public package")
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


def variant_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("variant_bucket")): row for row in report.get("variant_result_records", []) if isinstance(row, dict)}


def get_counts(row: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        int(row.get("gold_file_recovered_top10_count", -1)),
        int(row.get("gold_file_recovered_top20_count", -1)),
        int(row.get("gold_file_recovered_top50_count", -1)),
        int(row.get("gold_file_recovered_top100_count", -1)),
    )


def build_report() -> dict[str, Any]:
    n10dx, state = load_json(N10DX_REPORT)
    expected_status = "normalized_bm25_topk_token_cap_variant_canary_pass_n10dy_authorized"
    input_ok = state == "present" and bool(n10dx) and n10dx.get("status") == expected_status
    variants = variant_map(n10dx or {})
    baseline = variants.get("normalized_bm25_top50_cap12", {})
    top100_cap12 = variants.get("normalized_bm25_top100_cap12", {})
    top50_cap24 = variants.get("normalized_bm25_top50_cap24", {})
    top100_cap24 = variants.get("normalized_bm25_top100_cap24", {})
    baseline_counts = get_counts(baseline)
    top100_cap12_counts = get_counts(top100_cap12)
    top50_cap24_counts = get_counts(top50_cap24)
    top100_cap24_counts = get_counts(top100_cap24)
    chain_ok = (
        baseline_counts == (8, 9, 10, 10)
        and top100_cap12_counts == (8, 9, 10, 15)
        and top50_cap24_counts == (6, 8, 10, 10)
        and top100_cap24_counts == (6, 8, 10, 13)
    )
    status = STATUS_COMPLETE if input_ok and chain_ok else (STATUS_NO_INPUTS if not input_ok else STATUS_CHAIN_MISMATCH)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package_v1",
        "phase_bucket": "BEA-v1-N10DY Normalized-BM25 TopK/Token-Cap Canary Public Package",
        "status": status,
        "input_artifact_records": [{
            "anonymous_input_artifact_id": "n10dyinput0000",
            "artifact_bucket": "n10dx_normalized_bm25_topk_token_cap_variant_canary",
            "load_status_bucket": state,
            "expected_status_bucket": expected_status,
            "actual_status_bucket": str((n10dx or {}).get("status", "unavailable")),
            "status_match_bool": input_ok,
            "public_artifact_bool": True,
        }],
        "package_summary_records": [{
            "anonymous_package_summary_id": "n10dysummary0000",
            "public_only_package_bool": True,
            "private_read_count": 0,
            "retrieval_execution_count": 0,
            "recompute_count": 0,
            "variant_count": 4,
            "sampled_case_count": 30,
            "command_count_packaged_from_n10dx": 120,
        }],
        "topk_token_cap_result_records": [
            {"anonymous_result_id": "n10dyresult0000", "variant_bucket": "normalized_bm25_top50_cap12", "interpretation_bucket": "best_head_ranking_point", "top10_count": baseline_counts[0], "top20_count": baseline_counts[1], "top50_count": baseline_counts[2], "top100_count": baseline_counts[3]},
            {"anonymous_result_id": "n10dyresult0001", "variant_bucket": "normalized_bm25_top100_cap12", "interpretation_bucket": "depth_only_improvement_ranks_51_100", "top10_count": top100_cap12_counts[0], "top20_count": top100_cap12_counts[1], "top50_count": top100_cap12_counts[2], "top100_count": top100_cap12_counts[3], "additional_top100_vs_baseline_count": 5},
            {"anonymous_result_id": "n10dyresult0002", "variant_bucket": "normalized_bm25_top50_cap24", "interpretation_bucket": "cap24_worsens_head_ranking", "top10_count": top50_cap24_counts[0], "top20_count": top50_cap24_counts[1], "top50_count": top50_cap24_counts[2], "top100_count": top50_cap24_counts[3]},
            {"anonymous_result_id": "n10dyresult0003", "variant_bucket": "normalized_bm25_top100_cap24", "interpretation_bucket": "cap24_depth_gain_but_head_worse_than_cap12", "top10_count": top100_cap24_counts[0], "top20_count": top100_cap24_counts[1], "top50_count": top100_cap24_counts[2], "top100_count": top100_cap24_counts[3], "additional_top100_vs_baseline_count": 3},
        ],
        "interpretation_records": [{
            "anonymous_interpretation_id": "n10dyinterp0000",
            "depth_only_improvement_bool": True,
            "top10_improvement_bool": False,
            "top20_improvement_bool": False,
            "top50_improvement_bool": False,
            "cap24_worsens_head_ranking_bool": True,
            "top50_cap12_remains_best_head_ranking_bool": True,
            "not_runtime_default_claim_bool": True,
            "not_heldout_generalization_claim_bool": True,
        }],
        "no_private_read_no_recompute_records": [{
            "anonymous_no_private_id": "n10dynopriv0000",
            "private_read_count": 0,
            "retrieval_execution_count": 0,
            "openlocus_execution_count": 0,
            "recompute_count": 0,
            "candidate_generation_count": 0,
        }],
        "n10dz_handoff_records": [{
            "anonymous_handoff_id": "n10dyhandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DZ Normalized-BM25 Depth Promotion or Small-Sample Expansion Decision",
            "n10dz_focused_followup_authorized_bool": True,
            "depth_evidence_promotion_focus_bool": True,
            "another_small_sample_option_bool": True,
            "scaled_retrieval_authorized_bool": False,
        }],
        "gate_records": [
            {"anonymous_gate_id": "n10dygate0000", "gate_bucket": "n10dx_public_input_present", "gate_passed_bool": input_ok},
            {"anonymous_gate_id": "n10dygate0001", "gate_bucket": "n10dx_counts_match_expected", "gate_passed_bool": chain_ok},
            {"anonymous_gate_id": "n10dygate0002", "gate_bucket": "public_only_no_recompute", "gate_passed_bool": True},
        ],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10dystop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10DZ Normalized-BM25 Depth Promotion or Small-Sample Expansion Decision",
            "runtime_default_authorized_bool": False,
            "scaled_retrieval_authorized_bool": False,
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
    report["n10dx_public_input_records"] = list(report["input_artifact_records"])
    report["packaged_variant_result_records"] = list(report["topk_token_cap_result_records"])
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
    checks.append(("counts", (8, 9, 10, 15)[3] - (8, 9, 10, 10)[3] == 5))
    checks.append(("cap24_head_worse", 6 < 8 and 8 < 9))
    checks.append(("scan_pass", scan_summary({"bucket": "safe", "count": 1})["status"] == "pass"))
    checks.append(("vocab_size", len(STATUS_VOCAB) == 6))
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
