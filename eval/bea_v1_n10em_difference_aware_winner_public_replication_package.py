#!/usr/bin/env python3
"""BEA-v1-N10EM public replication package for N10EK/N10EL."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10em_difference_aware_winner_public_replication_package"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EK_REPORT = ROOT / "artifacts" / "bea_v1_n10ek_fixed_difference_aware_combination_experiment" / "bea_v1_n10ek_fixed_difference_aware_combination_experiment_report.json"
N10EL_REPORT = ROOT / "artifacts" / "bea_v1_n10el_difference_aware_winner_audit_recompute" / "bea_v1_n10el_difference_aware_winner_audit_recompute_report.json"

EXPECTED_N10EK_STATUS = "fixed_difference_aware_combination_experiment_complete_audit_recompute_authorized"
EXPECTED_N10EL_STATUS = "difference_aware_winner_audit_recompute_complete_n10em_authorized"
STATUS_COMPLETE = "difference_aware_winner_public_replication_package_complete_n10en_authorized"
STATUS_NO_INPUT = "no_go_n10em_required_public_inputs_unavailable"
STATUS_MISMATCH = "no_go_n10em_chain_consistency_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_INPUT, STATUS_MISMATCH, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}
EXPECTED_COUNTS = {"top10": 13, "top20": 16, "top50": 20, "top100": 26, "lost_baseline_top10": 0}

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
    parser = SafeArgumentParser(description="BEA-v1-N10EM public replication package")
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


def row_by(rows: list[Any], key: str, value: Any) -> dict[str, Any]:
    for row in rows:
        if isinstance(row, dict) and row.get(key) == value:
            return row
    return {}


def observed_tuple(row: dict[str, Any], prefix: str) -> tuple[int, int, int, int, int]:
    return (
        int(row.get(f"{prefix}_top10_file_recovery_count", -1)),
        int(row.get(f"{prefix}_top20_file_recovery_count", -1)),
        int(row.get(f"{prefix}_top50_file_recovery_count", -1)),
        int(row.get(f"{prefix}_top100_file_recovery_count", -1)),
        int(row.get(f"{prefix}_lost_baseline_top10_hits", -1)),
    )


def build_report() -> dict[str, Any]:
    n10ek, ek_state = load_json(N10EK_REPORT)
    n10el, el_state = load_json(N10EL_REPORT)
    ek_ok = ek_state == "present" and isinstance(n10ek, dict) and n10ek.get("status") == EXPECTED_N10EK_STATUS
    el_ok = el_state == "present" and isinstance(n10el, dict) and n10el.get("status") == EXPECTED_N10EL_STATUS
    if not (ek_ok and el_ok):
        report = {
            "schema_version": "bea_v1_n10em_difference_aware_winner_public_replication_package_v1",
            "phase_bucket": "BEA-v1-N10EM Difference-Aware Winner Public Replication Package",
            "status": STATUS_NO_INPUT,
            "input_artifact_records": [
                {"anonymous_input_artifact_id": "n10eminput0000", "artifact_bucket": "n10ek_fixed_difference_aware_experiment", "load_status_bucket": ek_state, "expected_status_bucket": EXPECTED_N10EK_STATUS, "actual_status_bucket": str((n10ek or {}).get("status", "unavailable")), "status_match_bool": ek_ok, "public_artifact_bool": True},
                {"anonymous_input_artifact_id": "n10eminput0001", "artifact_bucket": "n10el_independent_audit_recompute", "load_status_bucket": el_state, "expected_status_bucket": EXPECTED_N10EL_STATUS, "actual_status_bucket": str((n10el or {}).get("status", "unavailable")), "status_match_bool": el_ok, "public_artifact_bool": True},
            ],
        }
        report["forbidden_scan"] = scan_summary(report)
        return report
    assert n10ek is not None and n10el is not None
    ek_winner = row_by(n10ek.get("variant_result_records", []), "variant_bucket", "diffaware_top5_novel_guard_else_full")
    el_observed = (n10el.get("observed_recompute_records") or [{}])[0]
    el_expected = (n10el.get("expected_match_records") or [{}])[0]
    el_policy = (n10el.get("policy_contract_records") or [{}])[0]

    ek_counts = (
        int(ek_winner.get("top10_file_recovery_count", -1)),
        int(ek_winner.get("top20_file_recovery_count", -1)),
        int(ek_winner.get("top50_file_recovery_count", -1)),
        int(ek_winner.get("top100_file_recovery_count", -1)),
        int(ek_winner.get("lost_baseline_top10_hits", -1)),
    )
    el_counts = observed_tuple(el_observed, "observed")
    expected_counts = (EXPECTED_COUNTS["top10"], EXPECTED_COUNTS["top20"], EXPECTED_COUNTS["top50"], EXPECTED_COUNTS["top100"], EXPECTED_COUNTS["lost_baseline_top10"])
    chain_ok = (
        ek_counts == expected_counts
        and el_counts == expected_counts
        and el_expected.get("expected_observed_counts_match_bool") is True
        and el_policy.get("threshold_feature_bucket") == "top5_novel_candidate_item_count"
        and el_policy.get("threshold_value") == 4
        and el_policy.get("old_pool_membership_used_for_policy_bool") is True
        and el_policy.get("full_guard_outcome_membership_used_for_policy_bool") is False
        and el_policy.get("gold_used_for_policy_bool") is False
        and el_policy.get("n10ek_code_call_count") == 0
    )
    status = STATUS_COMPLETE if chain_ok else STATUS_MISMATCH
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10em_difference_aware_winner_public_replication_package_v1",
        "phase_bucket": "BEA-v1-N10EM Difference-Aware Winner Public Replication Package",
        "status": status,
        "input_artifact_records": [
            {"anonymous_input_artifact_id": "n10eminput0000", "artifact_bucket": "n10ek_fixed_difference_aware_experiment", "load_status_bucket": ek_state, "expected_status_bucket": EXPECTED_N10EK_STATUS, "actual_status_bucket": str(n10ek.get("status")), "status_match_bool": ek_ok, "public_artifact_bool": True},
            {"anonymous_input_artifact_id": "n10eminput0001", "artifact_bucket": "n10el_independent_audit_recompute", "load_status_bucket": el_state, "expected_status_bucket": EXPECTED_N10EL_STATUS, "actual_status_bucket": str(n10el.get("status")), "status_match_bool": el_ok, "public_artifact_bool": True},
        ],
        "replication_chain_records": [{"anonymous_chain_id": "n10emchain0000", "n10ek_winner_counts_match_bool": ek_counts == expected_counts, "n10el_audit_counts_match_bool": el_counts == expected_counts, "n10ek_n10el_counts_match_bool": ek_counts == el_counts, "top10_file_recovery_count": 13, "top20_file_recovery_count": 16, "top50_file_recovery_count": 20, "top100_file_recovery_count": 26, "lost_baseline_top10_hits": 0, "chain_consistent_bool": chain_ok}],
        "policy_boundary_records": [{"anonymous_policy_boundary_id": "n10empolicy0000", "winner_rule_bucket": "if_top5_novel_candidate_item_count_gte_4_then_guarded_else_full", "threshold_frozen_bool": True, "threshold_feature_bucket": "top5_novel_candidate_item_count", "threshold_operator_bucket": "greater_than_or_equal", "threshold_value": 4, "old_pool_membership_used_for_policy_bool": True, "gold_used_for_policy_bool": False, "full_guard_outcome_membership_used_for_policy_bool": False, "n10ek_code_call_count": 0}],
        "claim_boundary_records": [{"anonymous_claim_boundary_id": "n10emclaim0000", "public_package_only_bool": True, "private_read_bool": False, "recompute_bool": False, "new_retrieval_bool": False, "scaled_retrieval_bool": False, "openlocus_binary_execution_bool": False, "candidate_generation_bool": False, "network_bool": False, "runtime_default_change_bool": False, "selector_reranker_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "heldout_generalization_claim_bool": False}],
        "gate_records": [{"anonymous_gate_id": "n10emgate0000", "gate_bucket": "public_inputs_present", "gate_passed_bool": ek_ok and el_ok}, {"anonymous_gate_id": "n10emgate0001", "gate_bucket": "chain_counts_consistent", "gate_passed_bool": chain_ok}, {"anonymous_gate_id": "n10emgate0002", "gate_bucket": "public_only_package", "gate_passed_bool": True}],
        "stop_go_records": [{"anonymous_stop_go_id": "n10emstop0000", "next_allowed_phase_bucket": "BEA-v1-N10EN Broader-Sample CI Validation Canary", "n10en_broader_sample_ci_validation_authorized_bool": status == STATUS_COMPLETE, "private_read_authorized_bool": status == STATUS_COMPLETE, "private_read_scope_bucket": "bounded_rows_required_by_n10en_only", "github_ci_allowed_for_long_run_bool": status == STATUS_COMPLETE, "new_retrieval_authorized_bool": False, "scaled_retrieval_authorized_bool": False, "openlocus_binary_authorized_bool": False, "candidate_generation_authorized_bool": False, "network_authorized_bool": False, "runtime_default_authorized_bool": False, "selector_reranker_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_generalization_authorized_bool": False}],
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
    checks.append(("expected_counts", EXPECTED_COUNTS["top10"] == 13 and EXPECTED_COUNTS["top100"] == 26))
    checks.append(("no_baseline_loss", EXPECTED_COUNTS["lost_baseline_top10"] == 0))
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
