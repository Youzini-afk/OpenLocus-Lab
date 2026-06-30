#!/usr/bin/env python3
"""BEA-v1-N10EG novel-first / guarded complementarity slicing."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10eg_novel_first_guard_complementarity_slicing"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EF_REPORT = ROOT / "artifacts" / "bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package" / "bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package_report.json"
PRIVATE_N10DZ_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10dz_normalized_bm25_expanded_canary" / "private_expanded_candidate_rows.jsonl"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"

EXPECTED_N10EF_STATUS = "normalized_bm25_novel_guard_experiment_package_complete_n10eg_authorized"
STATUS_COMPLETE = "novel_first_guard_complementarity_slicing_complete_n10eh_authorized"
STATUS_NO_PUBLIC = "no_go_n10eg_required_public_input_unavailable"
STATUS_NO_PRIVATE = "no_go_n10eg_required_private_inputs_unavailable"
STATUS_ACCOUNTING = "no_go_n10eg_complementarity_accounting_invalid"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_PUBLIC, STATUS_NO_PRIVATE, STATUS_ACCOUNTING, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

FORBIDDEN_KEYS = {"path", "paths", "filename", "filenames", "private_path", "private_filename", "query", "raw_query", "candidate", "candidates", "candidate_list", "candidate_order", "gold", "gold_path", "gold_paths", "span", "spans", "line", "lines", "snippet", "snippets", "content", "exact_rank", "raw_rank", "repo", "repo_root", "hash", "provider_payload", "raw_diff"}
FORBIDDEN_VALUE_PATTERNS = [re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"), re.compile(r"/workspace/|/tmp/|/home/"), re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt|go|java|pony)", re.I), re.compile(r"[0-9a-f]{32,}", re.I)]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10EG complementarity slicing")
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


def norm_ref(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip("/").lower()


def suffix_match(a: Any, b: Any) -> bool:
    aa, bb = norm_ref(a), norm_ref(b)
    return bool(aa and bb and (aa == bb or aa.endswith("/" + bb) or bb.endswith("/" + aa)))


def file_key(item: dict[str, Any]) -> str:
    return norm_ref(item.get("path"))


def hit(item: dict[str, Any], refs: list[Any]) -> bool:
    return any(suffix_match(item.get("path"), ref) for ref in refs)


def first_rank(order: list[dict[str, Any]], refs: list[Any]) -> int | None:
    for idx, item in enumerate(order, 1):
        if hit(item, refs):
            return idx
    return None


def is_novel(item: dict[str, Any], old_files: set[str]) -> bool:
    key = file_key(item)
    return bool(key and not any(suffix_match(key, old) for old in old_files))


def append_rest(prefix: list[dict[str, Any]], original: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids = {id(item) for item in prefix}
    return list(prefix) + [item for item in original if id(item) not in ids]


def full_novel(cands: list[dict[str, Any]], old: set[str]) -> list[dict[str, Any]]:
    prefix = ([item for item in cands if is_novel(item, old)] + [item for item in cands if not is_novel(item, old)])[:10]
    return append_rest(prefix, cands)


def guarded(cands: list[dict[str, Any]], old: set[str]) -> list[dict[str, Any]]:
    prefix = list(cands[:5])
    ids = {id(item) for item in prefix}
    seen = {file_key(item) for item in prefix if file_key(item)}
    for item in cands[5:]:
        key = file_key(item)
        if id(item) not in ids and is_novel(item, old) and key not in seen:
            prefix.append(item); ids.add(id(item)); seen.add(key)
            if len(prefix) >= 10:
                break
    return append_rest(prefix, cands)


def load_private_inputs() -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], str]:
    try:
        dz = [row for row in read_jsonl(PRIVATE_N10DZ_ROWS) if row.get("private_variant_bucket") == "normalized_bm25_top100_cap12"]
        n1 = {int(row.get("denominator_index_private", -1)): row for row in read_jsonl(PRIVATE_N1_ROWS)}
    except Exception:
        return [], {}, "missing_or_invalid"
    if len(dz) != 60:
        return dz, n1, "wrong_case_count"
    return dz, n1, "present"


def bucket_novel_count(count: int) -> str:
    if count == 0:
        return "novel_count_0"
    if count <= 5:
        return "novel_count_1_to_5"
    if count <= 10:
        return "novel_count_6_to_10"
    return "novel_count_gt_10"


def build_report() -> dict[str, Any]:
    n10ef, state = load_json(N10EF_REPORT)
    public_ok = state == "present" and isinstance(n10ef, dict) and n10ef.get("status") == EXPECTED_N10EF_STATUS
    dz_rows, n1_rows, private_status = load_private_inputs()
    private_ok = private_status == "present" and all(int(row.get("private_denominator_index", -1)) in n1_rows for row in dz_rows)
    base_hits: set[int] = set(); full_hits: set[int] = set(); guard_hits: set[int] = set()
    novel_buckets: dict[str, dict[str, int]] = {"full_new": {}, "guard_new": {}, "full_only": {}, "guard_only": {}, "full_miss": {}}
    if public_ok and private_ok:
        for row in dz_rows:
            cid = int(row.get("private_case_order", -1)); denom = int(row.get("private_denominator_index", -1))
            n1 = n1_rows[denom]; cands = list(row.get("private_candidate_rows") or [])[:100]; refs = list(n1.get("gold_paths") or [])
            old = {file_key(item) for item in (n1.get("p4_evidence") or []) if isinstance(item, dict) and file_key(item)}
            novel_bucket = bucket_novel_count(sum(1 for item in cands if is_novel(item, old)))
            orders = {"base": cands, "full": full_novel(cands, old), "guard": guarded(cands, old)}
            hits = {name: (rank is not None and rank <= 10) for name, order in orders.items() for rank in [first_rank(order, refs)]}
            if hits["base"]: base_hits.add(cid)
            if hits["full"]: full_hits.add(cid)
            if hits["guard"]: guard_hits.add(cid)
            memberships = {
                "full_new": hits["full"] and not hits["base"],
                "guard_new": hits["guard"] and not hits["base"],
                "full_only": hits["full"] and not hits["guard"],
                "guard_only": hits["guard"] and not hits["full"],
                "full_miss": not hits["full"],
            }
            for group, ok in memberships.items():
                if ok:
                    novel_buckets[group][novel_bucket] = novel_buckets[group].get(novel_bucket, 0) + 1

    if not public_ok:
        status = STATUS_NO_PUBLIC
    elif not private_ok:
        status = STATUS_NO_PRIVATE
    else:
        status = STATUS_COMPLETE if (len(base_hits), len(full_hits), len(guard_hits), len(full_hits | guard_hits), len(full_hits & guard_hits), len(full_hits - guard_hits), len(guard_hits - full_hits)) == (5, 11, 10, 13, 8, 3, 2) else STATUS_ACCOUNTING

    bucket_records: list[dict[str, Any]] = []
    idx = 0
    for group, counts in novel_buckets.items():
        for bucket in ["novel_count_0", "novel_count_1_to_5", "novel_count_6_to_10", "novel_count_gt_10"]:
            bucket_records.append({"anonymous_slice_bucket_id": f"n10egslice{idx:04d}", "slice_bucket": group, "feature_bucket": bucket, "case_count": int(counts.get(bucket, 0))})
            idx += 1

    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10eg_novel_first_guard_complementarity_slicing_v1",
        "phase_bucket": "BEA-v1-N10EG Novel-First / Guarded Complementarity Slicing",
        "status": status,
        "input_artifact_records": [{"anonymous_input_artifact_id": "n10eginput0000", "artifact_bucket": "n10ef_public_package", "load_status_bucket": state, "expected_status_bucket": EXPECTED_N10EF_STATUS, "actual_status_bucket": str((n10ef or {}).get("status", "unavailable")), "status_match_bool": public_ok, "public_artifact_bool": True}],
        "private_input_intake_records": [{"anonymous_private_input_id": "n10egpriv0000", "n10dz_top100_private_rows_available_bool": private_ok, "n10dz_top100_private_row_count": len(dz_rows), "same_scoped_n1_rows_available_bool": bool(n1_rows), "case_count": len(dz_rows), "private_status_bucket": private_status, "other_private_read_count": 0}],
        "complementarity_records": [{"anonymous_complementarity_id": "n10egcomp0000", "baseline_top10_count": len(base_hits), "full_novel_first_top10_count": len(full_hits), "guarded_top5_novel_distinct_top10_count": len(guard_hits), "full_guard_union_top10_count": len(full_hits | guard_hits), "full_guard_intersection_top10_count": len(full_hits & guard_hits), "full_only_top10_count": len(full_hits - guard_hits), "guard_only_top10_count": len(guard_hits - full_hits), "complementarity_signal_bool": len(full_hits | guard_hits) > max(len(full_hits), len(guard_hits))}],
        "slice_feature_bucket_records": bucket_records,
        "decision_records": [{"anonymous_decision_id": "n10egdecision0000", "decision_bucket": "complementarity_exists_but_fixed_combo_needed", "full_novel_first_still_best_single_rule_bool": True, "guarded_rule_unique_cases_bool": len(guard_hits - full_hits) > 0, "n10eh_authorized_bool": status == STATUS_COMPLETE, "n10eh_scope_bucket": "fixed_full_guard_combination_rules_same_rows_only"}],
        "claim_boundary_records": [{"anonymous_claim_id": "n10egclaim0000", "same_source_private_analysis_bool": True, "new_retrieval_bool": False, "recompute_retrieval_bool": False, "runtime_default_change_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "heldout_generalization_claim_bool": False}],
        "gate_records": [{"anonymous_gate_id": "n10eggate0000", "gate_bucket": "n10ef_public_input_present", "gate_passed_bool": public_ok}, {"anonymous_gate_id": "n10eggate0001", "gate_bucket": "private_rows_present", "gate_passed_bool": private_ok}, {"anonymous_gate_id": "n10eggate0002", "gate_bucket": "complementarity_counts_match", "gate_passed_bool": status == STATUS_COMPLETE}],
        "stop_go_records": [{"anonymous_stop_go_id": "n10egstop0000", "next_allowed_phase_bucket": "BEA-v1-N10EH Fixed Full/Guard Combination Repacking Experiment", "n10eh_fixed_combo_experiment_authorized_bool": status == STATUS_COMPLETE, "private_read_scope_bucket": "same_n10dz_top100_and_n1_rows_only", "new_retrieval_authorized_bool": False, "scaled_retrieval_authorized_bool": False, "runtime_default_authorized_bool": False, "selector_reranker_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_generalization_authorized_bool": False}],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass": report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB: report["status"] = STATUS_FAIL_SCHEMA
    return report


def run_self_test() -> bool:
    checks = []
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_ACCOUNTING in STATUS_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"]); checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("suffix", suffix_match("a/b/c.py", "b/c.py") and not suffix_match("a.py", "b.py")))
    checks.append(("novel_bucket", bucket_novel_count(11) == "novel_count_gt_10"))
    passed = sum(1 for _, ok in checks if ok)
    for name, ok in checks: print(f"[{ 'PASS' if ok else 'FAIL' }] {name}")
    print(f"self_test_passed={passed == len(checks)} ({passed}/{len(checks)} checks)")
    return passed == len(checks)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return 0 if run_self_test() else 1
    report = build_report()
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0 if report["status"] == STATUS_COMPLETE else 1


if __name__ == "__main__":
    raise SystemExit(main())
