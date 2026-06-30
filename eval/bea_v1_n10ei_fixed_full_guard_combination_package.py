#!/usr/bin/env python3
"""BEA-v1-N10EI public package for N10EH fixed full/guard combinations."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10ei_fixed_full_guard_combination_package"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EH_REPORT = ROOT / "artifacts" / "bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment" / "bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment_report.json"

EXPECTED_N10EH_STATUS = "fixed_full_guard_combination_repacking_experiment_complete_n10ei_authorized"
STATUS_COMPLETE = "fixed_full_guard_combination_package_complete_n10ej_authorized"
STATUS_NO_INPUT = "no_go_n10ei_required_public_input_unavailable"
STATUS_MISMATCH = "no_go_n10ei_packaged_result_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUT, STATUS_MISMATCH, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

EXPECTED = {
    "full_novel_first": 11,
    "guarded_top5_novel_distinct": 10,
    "guard5_then_fullfill": 8,
    "full5_then_guardfill": 10,
    "alternate_full_guard": 9,
    "union_original_order": 8,
    "union_full_order": 11,
}

FORBIDDEN_KEYS = {
    "path", "paths", "filename", "filenames", "private_path", "private_filename", "query", "raw_query",
    "candidate", "candidates", "candidate_list", "candidate_order", "gold", "gold_path", "gold_paths",
    "span", "spans", "line", "lines", "snippet", "snippets", "content", "exact_rank", "raw_rank",
    "repo", "repo_root", "hash", "provider_payload", "raw_diff",
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
    parser = SafeArgumentParser(description="BEA-v1-N10EI public package")
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
    n10eh, state = load_json(N10EH_REPORT)
    input_ok = state == "present" and isinstance(n10eh, dict) and n10eh.get("status") == EXPECTED_N10EH_STATUS
    if not input_ok:
        report = {
            "schema_version": "bea_v1_n10ei_fixed_full_guard_combination_package_v1",
            "phase_bucket": "BEA-v1-N10EI Fixed Full/Guard Combination Package",
            "status": STATUS_NO_INPUT,
            "input_artifact_records": [{
                "anonymous_input_artifact_id": "n10eiinput0000",
                "artifact_bucket": "n10eh_fixed_combo_experiment",
                "load_status_bucket": state,
                "expected_status_bucket": EXPECTED_N10EH_STATUS,
                "actual_status_bucket": str((n10eh or {}).get("status", "unavailable")),
                "status_match_bool": False,
            }],
        }
        report["forbidden_scan"] = scan_summary(report)
        return report
    assert n10eh is not None

    rows = {row.get("variant_bucket"): row for row in n10eh.get("variant_result_records", []) if isinstance(row, dict)}
    packaged_rows: list[dict[str, Any]] = []
    match = True
    for idx, (variant, expected_top10) in enumerate(EXPECTED.items()):
        row = rows.get(variant, {})
        actual_top10 = row.get("top10_file_recovery_count")
        ok = actual_top10 == expected_top10
        match = match and ok
        packaged_rows.append({
            "anonymous_packaged_variant_id": f"n10eivariant{idx:04d}",
            "variant_bucket": variant,
            "top10_file_recovery_count": expected_top10,
            "top20_file_recovery_count": int(row.get("top20_file_recovery_count", -1)),
            "top50_file_recovery_count": int(row.get("top50_file_recovery_count", -1)),
            "top100_file_recovery_count": int(row.get("top100_file_recovery_count", -1)),
            "beats_full_novel_first_bool": bool(row.get("beats_full_novel_first_bool", False)),
            "reaches_n10eg_union_bound_bool": bool(row.get("reaches_n10eg_union_bound_bool", False)),
            "matches_n10eh_bool": ok,
        })

    summary = n10eh.get("experiment_summary_records", [{}])[0]
    summary_ok = (
        summary.get("best_top10_file_recovery_count") == 11
        and summary.get("any_variant_beats_full_novel_first_bool") is False
        and summary.get("any_variant_reaches_union_bound_bool") is False
    )
    status = STATUS_COMPLETE if match and summary_ok else STATUS_MISMATCH
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10ei_fixed_full_guard_combination_package_v1",
        "phase_bucket": "BEA-v1-N10EI Fixed Full/Guard Combination Package",
        "status": status,
        "input_artifact_records": [{
            "anonymous_input_artifact_id": "n10eiinput0000",
            "artifact_bucket": "n10eh_fixed_combo_experiment",
            "load_status_bucket": state,
            "expected_status_bucket": EXPECTED_N10EH_STATUS,
            "actual_status_bucket": str(n10eh.get("status")),
            "status_match_bool": True,
            "public_artifact_bool": True,
        }],
        "packaged_variant_records": packaged_rows,
        "summary_records": [{
            "anonymous_summary_id": "n10eisummary0000",
            "variant_count": len(EXPECTED),
            "full_novel_first_top10_count": 11,
            "best_combination_top10_count": 11,
            "n10eg_union_bound_count": 13,
            "any_variant_beats_full_novel_first_bool": False,
            "any_variant_reaches_union_bound_bool": False,
            "conclusion_bucket": "simple_combinations_do_not_exceed_full_novel_first",
        }],
        "claim_boundary_records": [{
            "anonymous_claim_boundary_id": "n10eiclaim0000",
            "public_package_only_bool": True,
            "private_read_bool": False,
            "recompute_bool": False,
            "new_retrieval_bool": False,
            "scaled_retrieval_bool": False,
            "candidate_generation_bool": False,
            "runtime_default_change_bool": False,
            "selector_reranker_bool": False,
            "method_winner_claim_bool": False,
            "downstream_value_claim_bool": False,
            "heldout_generalization_claim_bool": False,
        }],
        "gate_records": [
            {"anonymous_gate_id": "n10eigate0000", "gate_bucket": "n10eh_public_input_present", "gate_passed_bool": input_ok},
            {"anonymous_gate_id": "n10eigate0001", "gate_bucket": "packaged_variants_match", "gate_passed_bool": match},
            {"anonymous_gate_id": "n10eigate0002", "gate_bucket": "summary_match", "gate_passed_bool": summary_ok},
        ],
        "stop_go_records": [{
            "anonymous_stop_go_id": "n10eistop0000",
            "next_allowed_phase_bucket": "BEA-v1-N10EJ Full-Only vs Guard-Only Difference Analysis",
            "n10ej_difference_analysis_authorized_bool": status == STATUS_COMPLETE,
            "private_read_authorized_bool": status == STATUS_COMPLETE,
            "private_read_scope_bucket": "same_n10dz_top100_and_n1_rows_only",
            "new_retrieval_authorized_bool": False,
            "scaled_retrieval_authorized_bool": False,
            "candidate_generation_authorized_bool": False,
            "runtime_default_authorized_bool": False,
            "selector_reranker_authorized_bool": False,
            "method_winner_claim_authorized_bool": False,
            "downstream_value_claim_authorized_bool": False,
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
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_MISMATCH in STATUS_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("expected_count", len(EXPECTED) == 7 and EXPECTED["full_novel_first"] == 11))
    checks.append(("conclusion", max(EXPECTED.values()) == 11 and 13 > max(EXPECTED.values())))
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
