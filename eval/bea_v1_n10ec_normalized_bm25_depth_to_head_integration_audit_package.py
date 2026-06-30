#!/usr/bin/env python3
"""BEA-v1-N10EC Normalized-BM25 Depth-to-Head Integration Audit Package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EB_REPORT = ROOT / "artifacts" / "bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke" / "bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke_report.json"

EXPECTED_N10EB_STATUS = "normalized_bm25_depth_to_head_integration_smoke_complete_n10ec_authorized"
STATUS_COMPLETE = "normalized_bm25_depth_to_head_integration_audit_package_complete_n10ed_authorized"
STATUS_NO_INPUT = "no_go_n10ec_required_public_input_unavailable"
STATUS_CHAIN_MISMATCH = "no_go_n10ec_n10eb_chain_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUT, STATUS_CHAIN_MISMATCH, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

EXPECTED_VARIANTS = {
    "baseline_bm25_order": (5, 11, 17, 26, "no_head_improvement"),
    "distinct_file_top10": (8, 11, 17, 26, "no_head_improvement"),
    "distinct_file_top20_then_top10": (8, 14, 17, 26, "top20_improvement_only"),
    "novel_file_first_top10": (11, 16, 20, 26, "depth_to_head_success"),
    "novel_file_first_top20_then_top10": (11, 18, 20, 26, "depth_to_head_success"),
    "top5_bm25_then_novel_fill_top10": (8, 13, 18, 26, "top20_improvement_only"),
    "top5_bm25_then_distinct_file_fill_top10": (8, 11, 17, 26, "no_head_improvement"),
    "top5_bm25_then_novel_distinct_fill_top10": (10, 13, 18, 26, "depth_to_head_success"),
}

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
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt|go|java|pony)", re.I),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10EC public audit package")
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


def variant_rows(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("variant_bucket")): row for row in report.get("variant_result_records", []) if isinstance(row, dict)}


def n10eb_chain_ok(report: dict[str, Any]) -> bool:
    if report.get("status") != EXPECTED_N10EB_STATUS:
        return False
    rows = variant_rows(report)
    if set(rows) != set(EXPECTED_VARIANTS):
        return False
    for variant, expected in EXPECTED_VARIANTS.items():
        row = rows[variant]
        actual = (
            int(row.get("top10_file_recovery_count", -1)),
            int(row.get("top20_file_recovery_count", -1)),
            int(row.get("top50_file_recovery_count", -1)),
            int(row.get("top100_file_recovery_count", -1)),
            str(row.get("decision_bucket", "")),
        )
        if actual != expected:
            return False
    decisions = report.get("depth_to_head_decision_records", [])
    if not decisions:
        return False
    decision = decisions[0]
    return (
        int(decision.get("depth_to_head_success_variant_count", -1)) == 3
        and int(decision.get("best_top10_file_recovery_count", -1)) == 11
        and str(decision.get("best_variant_bucket", "")) == "novel_file_first_top10"
    )


def build_report() -> dict[str, Any]:
    n10eb, state = load_json(N10EB_REPORT)
    input_ok = state == "present" and isinstance(n10eb, dict)
    chain_ok = bool(input_ok and n10eb_chain_ok(n10eb or {}))
    status = STATUS_COMPLETE if chain_ok else (STATUS_NO_INPUT if not input_ok else STATUS_CHAIN_MISMATCH)
    rows = variant_rows(n10eb or {})
    success_variants = [name for name, row in rows.items() if row.get("decision_bucket") == "depth_to_head_success"]
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package_v1",
        "phase_bucket": "BEA-v1-N10EC Normalized-BM25 Depth-to-Head Integration Audit Package",
        "status": status,
        "input_artifact_records": [{
            "anonymous_input_artifact_id": "n10ecinput0000",
            "artifact_bucket": "n10eb_depth_to_head_integration_smoke",
            "load_status_bucket": state,
            "expected_status_bucket": EXPECTED_N10EB_STATUS,
            "actual_status_bucket": str((n10eb or {}).get("status", "unavailable")),
            "status_match_bool": input_ok and (n10eb or {}).get("status") == EXPECTED_N10EB_STATUS,
            "public_artifact_bool": True,
        }],
        "public_package_summary_records": [{
            "anonymous_package_summary_id": "n10ecsummary0000",
            "public_only_package_bool": True,
            "private_read_count": 0,
            "retrieval_execution_count": 0,
            "openlocus_execution_count": 0,
            "recompute_count": 0,
            "variant_count_packaged": len(rows),
            "success_variant_count_packaged": len(success_variants),
        }],
        "packaged_variant_summary_records": [
            {
                "anonymous_packaged_variant_id": f"n10ecvariant{idx:04d}",
                "variant_bucket": variant,
                "top10_file_recovery_count": expected[0],
                "top20_file_recovery_count": expected[1],
                "top50_file_recovery_count": expected[2],
                "top100_file_recovery_count": expected[3],
                "decision_bucket": expected[4],
            }
            for idx, (variant, expected) in enumerate(EXPECTED_VARIANTS.items())
        ],
        "claim_boundary_records": [{
            "anonymous_claim_boundary_id": "n10ecclaim0000",
            "same_source_smoke_bool": True,
            "runtime_default_claim_bool": False,
            "scaled_retrieval_claim_bool": False,
            "heldout_generalization_claim_bool": False,
            "method_winner_claim_bool": False,
            "downstream_value_claim_bool": False,
        }],
        "n10ed_handoff_records": [{
            "anonymous_handoff_id": "n10echandoff0000",
            "next_allowed_phase_bucket": "BEA-v1-N10ED Novel-First Depth-to-Head Mechanism Analysis",
            "n10ed_mechanism_analysis_authorized_bool": status == STATUS_COMPLETE,
            "private_read_authorized_bool": status == STATUS_COMPLETE,
            "private_read_scope_bucket": "n10eb_mechanism_analysis_only" if status == STATUS_COMPLETE else "not_authorized",
            "new_retrieval_authorized_bool": False,
            "runtime_default_authorized_bool": False,
        }],
        "gate_records": [
            {"anonymous_gate_id": "n10ecgate0000", "gate_bucket": "n10eb_public_input_present", "gate_passed_bool": input_ok},
            {"anonymous_gate_id": "n10ecgate0001", "gate_bucket": "n10eb_chain_counts_match", "gate_passed_bool": chain_ok},
            {"anonymous_gate_id": "n10ecgate0002", "gate_bucket": "public_only_no_recompute", "gate_passed_bool": True},
        ],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10ecstop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10ED Novel-First Depth-to-Head Mechanism Analysis",
            "new_retrieval_authorized_bool": False,
            "scaled_retrieval_authorized_bool": False,
            "network_authorized_bool": False,
            "clone_authorized_bool": False,
            "provider_authorized_bool": False,
            "runtime_default_authorized_bool": False,
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
        parse_args(["--private", "/tmp/secret"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/private.json"})["status"] == "fail"))
    fake = {"status": EXPECTED_N10EB_STATUS, "variant_result_records": [], "depth_to_head_decision_records": []}
    checks.append(("chain_rejects_empty", not n10eb_chain_ok(fake)))
    fake_rows = []
    for variant, expected in EXPECTED_VARIANTS.items():
        fake_rows.append({"variant_bucket": variant, "top10_file_recovery_count": expected[0], "top20_file_recovery_count": expected[1], "top50_file_recovery_count": expected[2], "top100_file_recovery_count": expected[3], "decision_bucket": expected[4]})
    fake = {"status": EXPECTED_N10EB_STATUS, "variant_result_records": fake_rows, "depth_to_head_decision_records": [{"depth_to_head_success_variant_count": 3, "best_top10_file_recovery_count": 11, "best_variant_bucket": "novel_file_first_top10"}]}
    checks.append(("chain_accepts_expected", n10eb_chain_ok(fake)))
    checks.append(("expected_variant_count", len(EXPECTED_VARIANTS) == 8))
    checks.append(("success_variant_count", sum(1 for values in EXPECTED_VARIANTS.values() if values[4] == "depth_to_head_success") == 3))
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
