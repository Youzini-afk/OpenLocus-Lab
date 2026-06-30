#!/usr/bin/env python3
"""BEA-v1-N10EL independent audit/recompute of the N10EK winner."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10el_difference_aware_winner_audit_recompute"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EK_REPORT = ROOT / "artifacts" / "bea_v1_n10ek_fixed_difference_aware_combination_experiment" / "bea_v1_n10ek_fixed_difference_aware_combination_experiment_report.json"
PRIVATE_N10DZ_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10dz_normalized_bm25_expanded_canary" / "private_expanded_candidate_rows.jsonl"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"

EXPECTED_N10EK_STATUS = "fixed_difference_aware_combination_experiment_complete_audit_recompute_authorized"
STATUS_COMPLETE = "difference_aware_winner_audit_recompute_complete_n10em_authorized"
STATUS_NO_PUBLIC = "no_go_n10el_required_public_input_unavailable"
STATUS_NO_PRIVATE = "no_go_n10el_required_private_inputs_unavailable"
STATUS_MISMATCH = "no_go_n10el_recompute_mismatch"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_PUBLIC, STATUS_NO_PRIVATE, STATUS_MISMATCH, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

EXPECTED_COUNTS = {"top10": 13, "top20": 16, "top50": 20, "top100": 26, "lost_baseline_top10": 0}
THRESHOLD = 4

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
    parser = SafeArgumentParser(description="BEA-v1-N10EL independent winner audit/recompute")
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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def clean_ref(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def ref_suffix_match(left: Any, right: Any) -> bool:
    a, b = clean_ref(left), clean_ref(right)
    return bool(a and b and (a == b or a.endswith("/" + b) or b.endswith("/" + a)))


def record_file_id(record: dict[str, Any]) -> str:
    return clean_ref(record.get("path"))


def record_is_eval_hit(record: dict[str, Any], references: list[Any]) -> bool:
    return any(ref_suffix_match(record.get("path"), ref) for ref in references)


def first_eval_rank(sequence: list[dict[str, Any]], references: list[Any]) -> int | None:
    for rank, record in enumerate(sequence, 1):
        if record_is_eval_hit(record, references):
            return rank
    return None


def unseen_by_old_pool(record: dict[str, Any], old_pool_files: set[str]) -> bool:
    current = record_file_id(record)
    return bool(current and not any(ref_suffix_match(current, old) for old in old_pool_files))


def remaining_after(chosen: list[dict[str, Any]], source: list[dict[str, Any]]) -> list[dict[str, Any]]:
    used = {id(item) for item in chosen}
    return list(chosen) + [item for item in source if id(item) not in used]


def audit_full_order(rows: list[dict[str, Any]], old_pool_files: set[str]) -> list[dict[str, Any]]:
    novel = [item for item in rows if unseen_by_old_pool(item, old_pool_files)]
    known = [item for item in rows if not unseen_by_old_pool(item, old_pool_files)]
    return remaining_after((novel + known)[:10], rows)


def audit_guard_order(rows: list[dict[str, Any]], old_pool_files: set[str]) -> list[dict[str, Any]]:
    chosen = list(rows[:5])
    used = {id(item) for item in chosen}
    seen_files = {record_file_id(item) for item in chosen if record_file_id(item)}
    for item in rows[5:]:
        file_id = record_file_id(item)
        if id(item) not in used and unseen_by_old_pool(item, old_pool_files) and file_id not in seen_files:
            chosen.append(item)
            used.add(id(item))
            seen_files.add(file_id)
            if len(chosen) >= 10:
                break
    return remaining_after(chosen, rows)


def top5_novel_candidate_item_count(rows: list[dict[str, Any]], old_pool_files: set[str]) -> int:
    return sum(1 for item in rows[:5] if unseen_by_old_pool(item, old_pool_files))


def audit_winner_order(rows: list[dict[str, Any]], old_pool_files: set[str]) -> tuple[list[dict[str, Any]], str]:
    if top5_novel_candidate_item_count(rows, old_pool_files) >= THRESHOLD:
        return audit_guard_order(rows, old_pool_files), "guarded_top5_novel_distinct"
    return audit_full_order(rows, old_pool_files), "full_novel_first"


def top5_novel_bucket(count: int) -> str:
    if count <= 2:
        return "top5_novel_candidate_item_count_0_to_2"
    if count == 3:
        return "top5_novel_candidate_item_count_3"
    return "top5_novel_candidate_item_count_4_to_5"


def add_count(table: dict[str, int], bucket: str) -> None:
    table[bucket] = table.get(bucket, 0) + 1


def load_private_inputs() -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], str]:
    try:
        dz_rows = [row for row in read_jsonl(PRIVATE_N10DZ_ROWS) if row.get("private_variant_bucket") == "normalized_bm25_top100_cap12"]
        n1_rows = {int(row.get("denominator_index_private", -1)): row for row in read_jsonl(PRIVATE_N1_ROWS)}
    except Exception:
        return [], {}, "missing_or_invalid"
    if len(dz_rows) != 60:
        return dz_rows, n1_rows, "wrong_case_count"
    return dz_rows, n1_rows, "present"


def expected_from_n10ek(report: dict[str, Any] | None) -> dict[str, int]:
    if not isinstance(report, dict):
        return dict(EXPECTED_COUNTS)
    for row in report.get("variant_result_records", []):
        if isinstance(row, dict) and row.get("variant_bucket") == "diffaware_top5_novel_guard_else_full":
            return {
                "top10": int(row.get("top10_file_recovery_count", -1)),
                "top20": int(row.get("top20_file_recovery_count", -1)),
                "top50": int(row.get("top50_file_recovery_count", -1)),
                "top100": int(row.get("top100_file_recovery_count", -1)),
                "lost_baseline_top10": int(row.get("lost_baseline_top10_hits", -1)),
            }
    return dict(EXPECTED_COUNTS)


def build_report() -> dict[str, Any]:
    n10ek, state = load_json(N10EK_REPORT)
    public_ok = state == "present" and isinstance(n10ek, dict) and n10ek.get("status") == EXPECTED_N10EK_STATUS
    expected = expected_from_n10ek(n10ek)
    dz_rows, n1_rows, private_status = load_private_inputs()
    private_ok = private_status == "present" and all(int(row.get("private_denominator_index", -1)) in n1_rows for row in dz_rows)

    hits = {10: set(), 20: set(), 50: set(), 100: set()}
    baseline_hits: set[int] = set()
    buckets: dict[str, int] = {}
    arm_counts: dict[str, int] = {}

    if public_ok and private_ok:
        for row in dz_rows:
            case_id = int(row.get("private_case_order", -1))
            n1 = n1_rows[int(row.get("private_denominator_index", -1))]
            rows = list(row.get("private_candidate_rows") or [])[:100]
            references = list(n1.get("gold_paths") or [])
            old_pool_files = {record_file_id(item) for item in (n1.get("p4_evidence") or []) if isinstance(item, dict) and record_file_id(item)}
            add_count(buckets, top5_novel_bucket(top5_novel_candidate_item_count(rows, old_pool_files)))
            recomputed_order, selected_arm = audit_winner_order(rows, old_pool_files)
            add_count(arm_counts, selected_arm)
            base_rank = first_eval_rank(rows, references)
            if base_rank is not None and base_rank <= 10:
                baseline_hits.add(case_id)
            rank = first_eval_rank(recomputed_order, references)
            for limit in (10, 20, 50, 100):
                if rank is not None and rank <= limit:
                    hits[limit].add(case_id)

    observed = {
        "top10": len(hits[10]),
        "top20": len(hits[20]),
        "top50": len(hits[50]),
        "top100": len(hits[100]),
        "lost_baseline_top10": len(baseline_hits - hits[10]),
    }
    expected_observed_match = observed == expected == EXPECTED_COUNTS
    if not public_ok:
        status = STATUS_NO_PUBLIC
    elif not private_ok:
        status = STATUS_NO_PRIVATE
    else:
        status = STATUS_COMPLETE if expected_observed_match else STATUS_MISMATCH

    bucket_records = [
        {"anonymous_bucket_id": f"n10elbucket{idx:04d}", "bucket_type": "top5_novel_candidate_item_count", "bucket": bucket, "case_count": count}
        for idx, (bucket, count) in enumerate(sorted(buckets.items()))
    ]
    arm_records = [
        {"anonymous_arm_bucket_id": f"n10elarm{idx:04d}", "selected_arm_bucket": arm, "case_count": count}
        for idx, (arm, count) in enumerate(sorted(arm_counts.items()))
    ]
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10el_difference_aware_winner_audit_recompute_v1",
        "phase_bucket": "BEA-v1-N10EL Audit/Recompute of Difference-Aware Winner",
        "status": status,
        "input_artifact_records": [{"anonymous_input_artifact_id": "n10elinput0000", "artifact_bucket": "n10ek_difference_aware_experiment", "load_status_bucket": state, "expected_status_bucket": EXPECTED_N10EK_STATUS, "actual_status_bucket": str((n10ek or {}).get("status", "unavailable")), "status_match_bool": public_ok, "public_artifact_bool": True}],
        "private_input_intake_records": [{"anonymous_private_input_id": "n10elpriv0000", "n10dz_top100_private_rows_available_bool": private_ok, "n10dz_top100_private_row_count": len(dz_rows), "same_scoped_n1_rows_available_bool": bool(n1_rows), "case_count": len(dz_rows), "private_status_bucket": private_status, "other_private_read_count": 0}],
        "policy_contract_records": [{"anonymous_policy_id": "n10elpolicy0000", "winner_rule_bucket": "if_top5_novel_candidate_item_count_gte_4_then_guarded_else_full", "threshold_frozen_bool": True, "threshold_feature_bucket": "top5_novel_candidate_item_count", "threshold_operator_bucket": "greater_than_or_equal", "threshold_value": THRESHOLD, "gold_used_for_policy_bool": False, "old_pool_membership_used_for_policy_bool": True, "full_guard_outcome_membership_used_for_policy_bool": False, "n10ek_code_call_count": 0}],
        "observed_recompute_records": [{"anonymous_recompute_id": "n10elrecompute0000", "observed_top10_file_recovery_count": observed["top10"], "observed_top20_file_recovery_count": observed["top20"], "observed_top50_file_recovery_count": observed["top50"], "observed_top100_file_recovery_count": observed["top100"], "observed_lost_baseline_top10_hits": observed["lost_baseline_top10"]}],
        "expected_match_records": [{"anonymous_expected_id": "n10elexpected0000", "expected_top10_file_recovery_count": expected["top10"], "expected_top20_file_recovery_count": expected["top20"], "expected_top50_file_recovery_count": expected["top50"], "expected_top100_file_recovery_count": expected["top100"], "expected_lost_baseline_top10_hits": expected["lost_baseline_top10"], "expected_observed_counts_match_bool": expected_observed_match}],
        "aggregate_bucket_records": bucket_records,
        "selected_arm_bucket_records": arm_records,
        "claim_boundary_records": [{"anonymous_claim_id": "n10elclaim0000", "same_source_private_recompute_bool": True, "independent_reimplementation_bool": True, "new_retrieval_bool": False, "openlocus_binary_execution_bool": False, "candidate_generation_bool": False, "network_bool": False, "runtime_default_change_bool": False, "selector_reranker_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "heldout_generalization_claim_bool": False}],
        "gate_records": [{"anonymous_gate_id": "n10elgate0000", "gate_bucket": "n10ek_public_input_present", "gate_passed_bool": public_ok}, {"anonymous_gate_id": "n10elgate0001", "gate_bucket": "private_rows_present", "gate_passed_bool": private_ok}, {"anonymous_gate_id": "n10elgate0002", "gate_bucket": "expected_observed_counts_match", "gate_passed_bool": expected_observed_match}],
        "stop_go_records": [{"anonymous_stop_go_id": "n10elstop0000", "next_allowed_phase_bucket": "BEA-v1-N10EM Public Replication Package", "n10em_public_replication_package_authorized_bool": status == STATUS_COMPLETE, "post_package_decision_bucket": "decide_broader_sample_or_ci_validation", "private_read_scope_bucket": "same_n10dz_top100_and_n1_rows_only", "new_retrieval_authorized_bool": False, "scaled_retrieval_authorized_bool": False, "openlocus_binary_authorized_bool": False, "candidate_generation_authorized_bool": False, "network_authorized_bool": False, "runtime_default_authorized_bool": False, "selector_reranker_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_generalization_authorized_bool": False}],
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
    checks.append(("suffix", ref_suffix_match("a/b/c.py", "b/c.py") and not ref_suffix_match("a.py", "b.py")))
    checks.append(("threshold", THRESHOLD == 4 and top5_novel_bucket(4) == "top5_novel_candidate_item_count_4_to_5"))
    checks.append(("append_remaining", len(remaining_after([{"path": "a"}], [{"path": "b"}])) == 2))
    fixture = [{"path": str(i)} for i in range(5)]
    checks.append(("policy_switch", audit_winner_order(fixture, set())[1] == "guarded_top5_novel_distinct"))
    duplicate_fixture = [{"path": "novel.py"}, {"path": "novel.py"}, {"path": "n2.py"}, {"path": "n3.py"}, {"path": "old.py"}]
    checks.append(("item_count_not_distinct_file_count", top5_novel_candidate_item_count(duplicate_fixture, {"old.py"}) == 4))
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
