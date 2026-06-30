#!/usr/bin/env python3
"""BEA-v1-N10EK fixed difference-aware combination experiment."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10ek_fixed_difference_aware_combination_experiment"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EJ_REPORT = ROOT / "artifacts" / "bea_v1_n10ej_full_guard_difference_analysis" / "bea_v1_n10ej_full_guard_difference_analysis_report.json"
PRIVATE_N10DZ_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10dz_normalized_bm25_expanded_canary" / "private_expanded_candidate_rows.jsonl"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"

EXPECTED_N10EJ_STATUS = "full_guard_difference_analysis_complete_n10ek_authorized"
STATUS_COMPLETE_NO_BEAT = "fixed_difference_aware_combination_experiment_complete_n10el_package_authorized"
STATUS_COMPLETE_BEAT = "fixed_difference_aware_combination_experiment_complete_audit_recompute_authorized"
STATUS_NO_PUBLIC = "no_go_n10ek_required_public_input_unavailable"
STATUS_NO_PRIVATE = "no_go_n10ek_required_private_inputs_unavailable"
STATUS_ACCOUNTING = "no_go_n10ek_variant_accounting_invalid"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE_NO_BEAT, STATUS_COMPLETE_BEAT, STATUS_NO_PUBLIC, STATUS_NO_PRIVATE, STATUS_ACCOUNTING, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

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
    parser = SafeArgumentParser(description="BEA-v1-N10EK fixed difference-aware combination experiment")
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


def full_novel_first(cands: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    prefix = ([item for item in cands if is_novel(item, old_files)] + [item for item in cands if not is_novel(item, old_files)])[:10]
    return append_rest(prefix, cands)


def guarded_top5(cands: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    prefix = list(cands[:5])
    ids = {id(item) for item in prefix}
    seen = {file_key(item) for item in prefix if file_key(item)}
    for item in cands[5:]:
        key = file_key(item)
        if id(item) not in ids and is_novel(item, old_files) and key not in seen:
            prefix.append(item)
            ids.add(id(item))
            seen.add(key)
            if len(prefix) >= 10:
                break
    return append_rest(prefix, cands)


def full8_guard2(cands: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    full = full_novel_first(cands, old_files)
    guard = guarded_top5(cands, old_files)
    prefix = list(full[:8])
    ids = {id(item) for item in prefix}
    for item in guard:
        if id(item) not in ids:
            prefix.append(item)
            ids.add(id(item))
            if len(prefix) >= 10:
                break
    return append_rest(prefix, cands)


def guard3_full7(cands: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    full = full_novel_first(cands, old_files)
    guard = guarded_top5(cands, old_files)
    prefix = list(guard[:3])
    ids = {id(item) for item in prefix}
    for item in full:
        if id(item) not in ids:
            prefix.append(item)
            ids.add(id(item))
            if len(prefix) >= 10:
                break
    return append_rest(prefix, cands)


def count_top5_duplicate(cands: list[dict[str, Any]]) -> int:
    keys = [file_key(item) for item in cands[:5] if file_key(item)]
    return len(keys) - len(set(keys))


def count_novel(cands: list[dict[str, Any]], old_files: set[str], limit: int | None = None) -> int:
    items = cands if limit is None else cands[:limit]
    return sum(1 for item in items if is_novel(item, old_files))


def has_deep_novel_pressure(cands: list[dict[str, Any]], old_files: set[str]) -> bool:
    return count_novel(cands, old_files) > 10 and count_novel(cands, old_files, 10) >= 8


def has_top5_preservation_proxy(cands: list[dict[str, Any]], old_files: set[str]) -> bool:
    return count_top5_duplicate(cands) > 0 or any(not is_novel(item, old_files) for item in cands[:5])


def dup_guard_else_full(cands: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    return guarded_top5(cands, old_files) if count_top5_duplicate(cands) > 0 else full_novel_first(cands, old_files)


def top5_novel_guard_else_full(cands: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    return guarded_top5(cands, old_files) if count_novel(cands, old_files, 5) >= 4 else full_novel_first(cands, old_files)


def top5_preserve_proxy_guard_else_full(cands: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    return guarded_top5(cands, old_files) if has_top5_preservation_proxy(cands, old_files) else full_novel_first(cands, old_files)


def deep_pressure_full8_else_guard(cands: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    return full8_guard2(cands, old_files) if has_deep_novel_pressure(cands, old_files) else guarded_top5(cands, old_files)


def deep_pressure_full_else_guard(cands: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    return full_novel_first(cands, old_files) if has_deep_novel_pressure(cands, old_files) else guarded_top5(cands, old_files)


def dup_or_low_top5_novel_guard_else_full(cands: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    if count_top5_duplicate(cands) > 0 or count_novel(cands, old_files, 5) <= 2:
        return guarded_top5(cands, old_files)
    return full_novel_first(cands, old_files)


VARIANTS: dict[str, Callable[[list[dict[str, Any]], set[str]], list[dict[str, Any]]]] = {
    "full_novel_first": full_novel_first,
    "guarded_top5_novel_distinct": guarded_top5,
    "diffaware_dup_guard_else_full": dup_guard_else_full,
    "diffaware_top5_novel_guard_else_full": top5_novel_guard_else_full,
    "diffaware_preserve_proxy_guard_else_full": top5_preserve_proxy_guard_else_full,
    "diffaware_deep_pressure_full8_else_guard": deep_pressure_full8_else_guard,
    "diffaware_deep_pressure_full_else_guard": deep_pressure_full_else_guard,
    "diffaware_dup_or_low_top5_novel_guard_else_full": dup_or_low_top5_novel_guard_else_full,
    "diffaware_full8_guard2": full8_guard2,
    "diffaware_guard3_full7": guard3_full7,
}


def bucket_novel_count(count: int) -> str:
    if count == 0:
        return "novel_count_0"
    if count <= 5:
        return "novel_count_1_to_5"
    if count <= 10:
        return "novel_count_6_to_10"
    return "novel_count_gt_10"


def bucket_top5_duplicate_pressure(cands: list[dict[str, Any]]) -> str:
    duplicates = count_top5_duplicate(cands)
    if duplicates == 0:
        return "top5_duplicate_pressure_none"
    if duplicates == 1:
        return "top5_duplicate_pressure_one"
    return "top5_duplicate_pressure_two_or_more"


def bucket_top5_novel_pressure(cands: list[dict[str, Any]], old_files: set[str]) -> str:
    count = count_novel(cands, old_files, 5)
    if count <= 2:
        return "top5_novel_pressure_0_to_2"
    if count == 3:
        return "top5_novel_pressure_3"
    return "top5_novel_pressure_4_to_5"


def bucket_depth_novel_pressure(cands: list[dict[str, Any]], old_files: set[str]) -> str:
    if has_deep_novel_pressure(cands, old_files):
        return "depth_novel_pressure_high"
    if count_novel(cands, old_files) > 10:
        return "depth_novel_pressure_broad_only"
    return "depth_novel_pressure_low"


def bucket_preservation_proxy(cands: list[dict[str, Any]], old_files: set[str]) -> str:
    return "top5_preservation_proxy_present" if has_top5_preservation_proxy(cands, old_files) else "top5_preservation_proxy_absent"


def add_count(table: dict[str, dict[str, int]], group: str, bucket: str) -> None:
    table.setdefault(group, {})[bucket] = table.setdefault(group, {}).get(bucket, 0) + 1


def load_private_inputs() -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], str]:
    try:
        dz = [row for row in read_jsonl(PRIVATE_N10DZ_ROWS) if row.get("private_variant_bucket") == "normalized_bm25_top100_cap12"]
        n1 = {int(row.get("denominator_index_private", -1)): row for row in read_jsonl(PRIVATE_N1_ROWS)}
    except Exception:
        return [], {}, "missing_or_invalid"
    if len(dz) != 60:
        return dz, n1, "wrong_case_count"
    return dz, n1, "present"


def build_report() -> dict[str, Any]:
    n10ej, state = load_json(N10EJ_REPORT)
    public_ok = state == "present" and isinstance(n10ej, dict) and n10ej.get("status") == EXPECTED_N10EJ_STATUS
    dz_rows, n1_rows, private_status = load_private_inputs()
    private_ok = private_status == "present" and all(int(row.get("private_denominator_index", -1)) in n1_rows for row in dz_rows)
    hits_by_variant: dict[str, dict[int, set[int]]] = {name: {10: set(), 20: set(), 50: set(), 100: set()} for name in VARIANTS}
    feature_counts: dict[str, dict[str, int]] = {}
    baseline_hits: set[int] = set()

    if public_ok and private_ok:
        for row in dz_rows:
            case_id = int(row.get("private_case_order", -1))
            n1 = n1_rows[int(row.get("private_denominator_index", -1))]
            cands = list(row.get("private_candidate_rows") or [])[:100]
            refs = list(n1.get("gold_paths") or [])
            old_files = {file_key(item) for item in (n1.get("p4_evidence") or []) if isinstance(item, dict) and file_key(item)}
            bm25_rank = first_rank(cands, refs)
            if bm25_rank is not None and bm25_rank <= 10:
                baseline_hits.add(case_id)
            for bucket in (
                bucket_novel_count(count_novel(cands, old_files)),
                bucket_top5_duplicate_pressure(cands),
                bucket_top5_novel_pressure(cands, old_files),
                bucket_preservation_proxy(cands, old_files),
                bucket_depth_novel_pressure(cands, old_files),
            ):
                add_count(feature_counts, "all_cases", bucket)
            for variant, func in VARIANTS.items():
                rank = first_rank(func(cands, old_files), refs)
                for limit in (10, 20, 50, 100):
                    if rank is not None and rank <= limit:
                        hits_by_variant[variant][limit].add(case_id)

    full_top10 = len(hits_by_variant["full_novel_first"][10])
    guard_top10 = len(hits_by_variant["guarded_top5_novel_distinct"][10])
    union_bound = 13
    variant_rows: list[dict[str, Any]] = []
    for idx, variant in enumerate(VARIANTS):
        top10 = hits_by_variant[variant][10]
        variant_rows.append({
            "anonymous_variant_id": f"n10ekvariant{idx:04d}",
            "variant_bucket": variant,
            "top10_file_recovery_count": len(top10),
            "top20_file_recovery_count": len(hits_by_variant[variant][20]),
            "top50_file_recovery_count": len(hits_by_variant[variant][50]),
            "top100_file_recovery_count": len(hits_by_variant[variant][100]),
            "lost_baseline_top10_hits": len(baseline_hits - top10),
            "beats_full_novel_first_bool": len(top10) > full_top10,
            "matches_full_novel_first_bool": len(top10) == full_top10,
            "approaches_union_bound_bool": len(top10) >= 12,
            "reaches_union_bound_bool": len(top10) >= union_bound,
        })
    best_top10 = max((row["top10_file_recovery_count"] for row in variant_rows), default=0)
    best_variants = [row["variant_bucket"] for row in variant_rows if row["top10_file_recovery_count"] == best_top10]
    any_beats_full = any(row["beats_full_novel_first_bool"] for row in variant_rows)
    any_approaches_union = any(row["approaches_union_bound_bool"] for row in variant_rows)
    expected_ok = public_ok and private_ok and full_top10 == 11 and guard_top10 == 10 and best_top10 >= 11
    if not public_ok:
        status = STATUS_NO_PUBLIC
    elif not private_ok:
        status = STATUS_NO_PRIVATE
    elif not expected_ok:
        status = STATUS_ACCOUNTING
    else:
        status = STATUS_COMPLETE_BEAT if any_beats_full else STATUS_COMPLETE_NO_BEAT

    feature_rows: list[dict[str, Any]] = []
    feature_idx = 0
    for group, counts in feature_counts.items():
        for bucket, count in sorted(counts.items()):
            feature_rows.append({"anonymous_feature_bucket_id": f"n10ekfeature{feature_idx:04d}", "case_scope_bucket": group, "observable_feature_bucket": bucket, "case_count": int(count)})
            feature_idx += 1

    conclusion = "difference_aware_fixed_rules_still_do_not_exploit_complementarity" if not any_beats_full else "difference_aware_fixed_rule_beats_full_requires_audit_recompute"
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10ek_fixed_difference_aware_combination_experiment_v1",
        "phase_bucket": "BEA-v1-N10EK Fixed Difference-Aware Combination Experiment",
        "status": status,
        "input_artifact_records": [{"anonymous_input_artifact_id": "n10ekinput0000", "artifact_bucket": "n10ej_difference_analysis", "load_status_bucket": state, "expected_status_bucket": EXPECTED_N10EJ_STATUS, "actual_status_bucket": str((n10ej or {}).get("status", "unavailable")), "status_match_bool": public_ok, "public_artifact_bool": True}],
        "private_input_intake_records": [{"anonymous_private_input_id": "n10ekpriv0000", "n10dz_top100_private_rows_available_bool": private_ok, "n10dz_top100_private_row_count": len(dz_rows), "same_scoped_n1_rows_available_bool": bool(n1_rows), "case_count": len(dz_rows), "private_status_bucket": private_status, "other_private_read_count": 0}],
        "variant_result_records": variant_rows,
        "observable_feature_bucket_records": feature_rows,
        "experiment_summary_records": [{"anonymous_summary_id": "n10eksummary0000", "variant_count": len(VARIANTS), "baseline_top10_count": len(baseline_hits), "full_novel_first_top10_count": full_top10, "guarded_top5_novel_distinct_top10_count": guard_top10, "best_variant_count": len(best_variants), "best_variant_bucket": best_variants[0] if best_variants else "none", "best_top10_file_recovery_count": best_top10, "n10eg_union_bound_count": union_bound, "any_variant_beats_full_novel_first_bool": any_beats_full, "any_variant_approaches_union_bound_bool": any_approaches_union, "any_variant_reaches_union_bound_bool": any(row["reaches_union_bound_bool"] for row in variant_rows), "conclusion_bucket": conclusion}],
        "claim_boundary_records": [{"anonymous_claim_id": "n10ekclaim0000", "same_source_private_experiment_bool": True, "uses_only_policy_time_observable_features_bool": True, "new_retrieval_bool": False, "openlocus_binary_execution_bool": False, "candidate_generation_bool": False, "runtime_default_change_bool": False, "selector_reranker_bool": False, "network_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "heldout_generalization_claim_bool": False}],
        "gate_records": [{"anonymous_gate_id": "n10ekgate0000", "gate_bucket": "n10ej_public_input_present", "gate_passed_bool": public_ok}, {"anonymous_gate_id": "n10ekgate0001", "gate_bucket": "private_rows_present", "gate_passed_bool": private_ok}, {"anonymous_gate_id": "n10ekgate0002", "gate_bucket": "baseline_accounting_expected", "gate_passed_bool": expected_ok}],
        "stop_go_records": [{"anonymous_stop_go_id": "n10ekstop0000", "next_allowed_phase_bucket": "BEA-v1-N10EL Fixed Difference-Aware Combination Package" if not any_beats_full else "BEA-v1-N10EL Audit/Recompute of Difference-Aware Winner", "n10el_package_authorized_bool": status == STATUS_COMPLETE_NO_BEAT, "audit_recompute_authorized_bool": status == STATUS_COMPLETE_BEAT, "private_read_scope_bucket": "same_n10dz_top100_and_n1_rows_only", "broader_sample_or_ci_after_package_bool": status == STATUS_COMPLETE_NO_BEAT, "feature_search_after_package_bool": status == STATUS_COMPLETE_NO_BEAT, "new_retrieval_authorized_bool": False, "scaled_retrieval_authorized_bool": False, "openlocus_binary_authorized_bool": False, "candidate_generation_authorized_bool": False, "runtime_default_authorized_bool": False, "selector_reranker_authorized_bool": False, "network_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_generalization_authorized_bool": False}],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_COMPLETE_NO_BEAT in STATUS_VOCAB and STATUS_COMPLETE_BEAT in STATUS_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("suffix", suffix_match("a/b/c.py", "b/c.py") and not suffix_match("a.py", "b.py")))
    checks.append(("variant_count", len(VARIANTS) == 10 and "full_novel_first" in VARIANTS and "guarded_top5_novel_distinct" in VARIANTS))
    checks.append(("novel_bucket", bucket_novel_count(11) == "novel_count_gt_10"))
    checks.append(("duplicate_bucket", bucket_top5_duplicate_pressure([{"path": "a"}, {"path": "a"}]) == "top5_duplicate_pressure_one"))
    checks.append(("top5_novel_pressure", bucket_top5_novel_pressure([{"path": "a"}, {"path": "b"}], set()) == "top5_novel_pressure_0_to_2"))
    checks.append(("append_rest", len(append_rest([{"path": "a"}], [{"path": "b"}])) == 2))
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
    return 0 if report["status"] in {STATUS_COMPLETE_NO_BEAT, STATUS_COMPLETE_BEAT} else 1


if __name__ == "__main__":
    raise SystemExit(main())
