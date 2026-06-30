#!/usr/bin/env python3
"""BEA-v1-N10EF package for the N10EE novel-guard experiment."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EE_REPORT = ROOT / "artifacts" / "bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment" / "bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment_report.json"

EXPECTED_N10EE_STATUS = "normalized_bm25_novel_guard_fixed_repacking_experiment_complete_n10ef_authorized"
STATUS_COMPLETE = "normalized_bm25_novel_guard_experiment_package_complete_n10eg_authorized"
STATUS_NO_INPUT = "no_go_n10ef_required_public_input_unavailable"
STATUS_MISMATCH = "no_go_n10ef_packaged_result_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUT, STATUS_MISMATCH, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

EXPECTED = {
    "baseline_bm25_order": (5, 11, 17, 26, 0),
    "novel_file_first_top10": (11, 16, 20, 26, 0),
    "top5_bm25_then_novel_distinct_fill_top10": (10, 13, 18, 26, 0),
}

FORBIDDEN_KEYS = {"path", "paths", "filename", "filenames", "private_path", "private_filename", "query", "raw_query", "candidate", "candidates", "candidate_list", "candidate_order", "gold", "gold_path", "gold_paths", "span", "spans", "line", "lines", "snippet", "snippets", "content", "exact_rank", "raw_rank", "repo", "repo_root", "hash", "provider_payload", "raw_diff"}
FORBIDDEN_VALUE_PATTERNS = [re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"), re.compile(r"/workspace/|/tmp/|/home/"), re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt|go|java|pony)", re.I), re.compile(r"[0-9a-f]{32,}", re.I)]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10EF public package")
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


def build_report() -> dict[str, Any]:
    data, state = load_json(N10EE_REPORT)
    input_ok = state == "present" and isinstance(data, dict) and data.get("status") == EXPECTED_N10EE_STATUS
    if not input_ok:
        report = {"schema_version": "bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package_v1", "phase_bucket": "BEA-v1-N10EF Normalized-BM25 Novel-Guard Experiment Package", "status": STATUS_NO_INPUT, "input_artifact_records": [{"anonymous_input_artifact_id": "n10efinput0000", "load_status_bucket": state, "expected_status_bucket": EXPECTED_N10EE_STATUS, "actual_status_bucket": str((data or {}).get("status", "unavailable")), "status_match_bool": False}]}
        report["forbidden_scan"] = scan_summary(report)
        return report
    assert data is not None

    rows = {row["variant_bucket"]: row for row in data.get("variant_result_records", []) if isinstance(row, dict)}
    packaged_rows: list[dict[str, Any]] = []
    result_ok = True
    for idx, (variant, expected) in enumerate(EXPECTED.items()):
        row = rows.get(variant, {})
        actual = (row.get("top10_file_recovery_count"), row.get("top20_file_recovery_count"), row.get("top50_file_recovery_count"), row.get("top100_file_recovery_count"), row.get("lost_baseline_top10_hits"))
        match = actual == expected
        result_ok = result_ok and match
        packaged_rows.append({"anonymous_packaged_result_id": f"n10efresult{idx:04d}", "variant_bucket": variant, "top10_file_recovery_count": expected[0], "top20_file_recovery_count": expected[1], "top50_file_recovery_count": expected[2], "top100_file_recovery_count": expected[3], "lost_baseline_top10_hits": expected[4], "matches_n10ee_bool": match})

    summary = data.get("decision_summary_records", [{}])[0]
    summary_ok = summary.get("full_novel_first_beats_guarded_bool") is True and summary.get("best_guarded_variant_bucket") == "top5_bm25_then_novel_distinct_fill_top10"
    status = STATUS_COMPLETE if result_ok and summary_ok else STATUS_MISMATCH
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package_v1",
        "phase_bucket": "BEA-v1-N10EF Normalized-BM25 Novel-Guard Experiment Package",
        "status": status,
        "input_artifact_records": [{"anonymous_input_artifact_id": "n10efinput0000", "artifact_bucket": "n10ee_fixed_repacking_experiment", "load_status_bucket": state, "expected_status_bucket": EXPECTED_N10EE_STATUS, "actual_status_bucket": str(data.get("status")), "status_match_bool": True, "public_artifact_bool": True}],
        "packaged_result_records": packaged_rows,
        "tradeoff_summary_records": [{"anonymous_tradeoff_summary_id": "n10eftradeoff0000", "full_novel_first_best_top10_bool": True, "full_novel_first_top10_count": 11, "guarded_top5_novel_distinct_top10_count": 10, "guarded_recovery_delta_vs_full_novel_first": -1, "all_tracked_variants_zero_loss_bool": True, "interpretation_bucket": "guarded_rule_is_conservative_zero_loss_but_weaker"}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "n10efclaim0000", "same_source_package_only_bool": True, "private_read_bool": False, "recompute_bool": False, "new_retrieval_bool": False, "scaled_retrieval_bool": False, "runtime_default_change_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "heldout_generalization_claim_bool": False}],
        "gate_records": [{"anonymous_gate_id": "n10efgate0000", "gate_bucket": "n10ee_input_status_match", "gate_passed_bool": input_ok}, {"anonymous_gate_id": "n10efgate0001", "gate_bucket": "packaged_results_match", "gate_passed_bool": result_ok}, {"anonymous_gate_id": "n10efgate0002", "gate_bucket": "tradeoff_summary_match", "gate_passed_bool": summary_ok}, {"anonymous_gate_id": "n10efgate0003", "gate_bucket": "public_only_package", "gate_passed_bool": True}],
        "stop_go_records": [{"anonymous_stop_go_id": "n10efstop0000", "next_allowed_phase_bucket": "BEA-v1-N10EG Normalized-BM25 Novel-First Robustness / Failure Slicing Experiment", "n10eg_followup_experiment_authorized_bool": status == STATUS_COMPLETE, "private_read_authorized_bool": status == STATUS_COMPLETE, "private_read_scope_bucket": "same_n10dz_top100_and_n1_rows_only", "new_retrieval_authorized_bool": False, "scaled_retrieval_authorized_bool": False, "runtime_default_authorized_bool": False, "selector_reranker_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_generalization_authorized_bool": False}],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_MISMATCH in STATUS_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/private.json"})["status"] == "fail"))
    checks.append(("expected_tradeoff", EXPECTED["novel_file_first_top10"][0] - EXPECTED["top5_bm25_then_novel_distinct_fill_top10"][0] == 1))
    checks.append(("all_zero_loss", all(v[4] == 0 for v in EXPECTED.values())))
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
