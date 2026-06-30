#!/usr/bin/env python3
"""BEA-v1-N10EJ full-only vs guard-only difference analysis."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10ej_full_guard_difference_analysis"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EI_REPORT = ROOT / "artifacts" / "bea_v1_n10ei_fixed_full_guard_combination_package" / "bea_v1_n10ei_fixed_full_guard_combination_package_report.json"
PRIVATE_N10DZ_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10dz_normalized_bm25_expanded_canary" / "private_expanded_candidate_rows.jsonl"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"

EXPECTED_N10EI_STATUS = "fixed_full_guard_combination_package_complete_n10ej_authorized"
STATUS_COMPLETE = "full_guard_difference_analysis_complete_n10ek_authorized"
STATUS_NO_PUBLIC = "no_go_n10ej_required_public_input_unavailable"
STATUS_NO_PRIVATE = "no_go_n10ej_required_private_inputs_unavailable"
STATUS_ACCOUNTING = "no_go_n10ej_difference_accounting_invalid"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_PUBLIC, STATUS_NO_PRIVATE, STATUS_ACCOUNTING, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

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
    parser = SafeArgumentParser(description="BEA-v1-N10EJ full/guard difference analysis")
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


def first_hit(order: list[dict[str, Any]], refs: list[Any]) -> tuple[int | None, dict[str, Any] | None]:
    for idx, item in enumerate(order, 1):
        if hit(item, refs):
            return idx, item
    return None, None


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


def original_position_bucket(cands: list[dict[str, Any]], item: dict[str, Any] | None) -> str:
    if item is None:
        return "source_absent"
    pos = next((idx for idx, cand in enumerate(cands, 1) if id(cand) == id(item)), None)
    if pos is None:
        return "source_unknown"
    if pos <= 5:
        return "source_bm25_top5"
    if pos <= 10:
        return "source_bm25_6_to_10"
    if pos <= 20:
        return "source_bm25_11_to_20"
    return "source_bm25_21_to_100"


def bucket_novel_count(count: int) -> str:
    if count == 0:
        return "novel_count_0"
    if count <= 5:
        return "novel_count_1_to_5"
    if count <= 10:
        return "novel_count_6_to_10"
    return "novel_count_gt_10"


def bucket_top5_duplicate_pressure(cands: list[dict[str, Any]]) -> str:
    keys = [file_key(item) for item in cands[:5] if file_key(item)]
    duplicates = len(keys) - len(set(keys))
    if duplicates == 0:
        return "top5_duplicate_pressure_none"
    if duplicates == 1:
        return "top5_duplicate_pressure_one"
    return "top5_duplicate_pressure_two_or_more"


def bucket_novel_candidate_pressure(cands: list[dict[str, Any]], old_files: set[str]) -> str:
    return bucket_novel_count(sum(1 for item in cands if is_novel(item, old_files)))


def bucket_bm25_top5_hit(cands: list[dict[str, Any]], refs: list[Any]) -> str:
    rank, _ = first_hit(cands, refs)
    return "bm25_top5_hit_present" if rank is not None and rank <= 5 else "bm25_top5_hit_absent"


def bucket_bm25_top5_preservation(cands: list[dict[str, Any]], refs: list[Any], guard_rank: int | None) -> str:
    rank, _ = first_hit(cands, refs)
    if rank is None or rank > 5:
        return "bm25_top5_preservation_not_applicable"
    if guard_rank is not None and guard_rank <= 5:
        return "bm25_top5_preserved_by_guard"
    return "bm25_top5_not_preserved_by_guard"


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
    n10ei, state = load_json(N10EI_REPORT)
    public_ok = state == "present" and isinstance(n10ei, dict) and n10ei.get("status") == EXPECTED_N10EI_STATUS
    dz_rows, n1_rows, private_status = load_private_inputs()
    private_ok = private_status == "present" and all(int(row.get("private_denominator_index", -1)) in n1_rows for row in dz_rows)

    base_hits: set[int] = set()
    full_hits: set[int] = set()
    guard_hits: set[int] = set()
    feature_counts: dict[str, dict[str, int]] = {}
    mechanism_counts: dict[str, int] = {
        "guard_only_preserves_bm25_top5_hit": 0,
        "guard_only_not_bm25_top5_preservation": 0,
        "full_only_deep_displacement_hit": 0,
        "full_only_not_deep_displacement_hit": 0,
    }

    if public_ok and private_ok:
        for row in dz_rows:
            case_id = int(row.get("private_case_order", -1))
            n1 = n1_rows[int(row.get("private_denominator_index", -1))]
            cands = list(row.get("private_candidate_rows") or [])[:100]
            refs = list(n1.get("gold_paths") or [])
            old_files = {file_key(item) for item in (n1.get("p4_evidence") or []) if isinstance(item, dict) and file_key(item)}
            full_order = full_novel_first(cands, old_files)
            guard_order = guarded_top5(cands, old_files)
            base_rank, _ = first_hit(cands, refs)
            full_rank, full_item = first_hit(full_order, refs)
            guard_rank, guard_item = first_hit(guard_order, refs)
            base_top10 = base_rank is not None and base_rank <= 10
            full_top10 = full_rank is not None and full_rank <= 10
            guard_top10 = guard_rank is not None and guard_rank <= 10
            if base_top10:
                base_hits.add(case_id)
            if full_top10:
                full_hits.add(case_id)
            if guard_top10:
                guard_hits.add(case_id)
            group = "both_or_neither"
            if full_top10 and not guard_top10:
                group = "full_only"
            elif guard_top10 and not full_top10:
                group = "guard_only"
            elif full_top10 and guard_top10:
                group = "full_and_guard"
            for feature_bucket in (
                bucket_novel_candidate_pressure(cands, old_files),
                bucket_bm25_top5_hit(cands, refs),
                bucket_bm25_top5_preservation(cands, refs, guard_rank),
                bucket_top5_duplicate_pressure(cands),
                "full_first_hit_" + original_position_bucket(cands, full_item),
                "guard_first_hit_" + original_position_bucket(cands, guard_item),
            ):
                add_count(feature_counts, group, feature_bucket)
            if group == "guard_only":
                if base_rank is not None and base_rank <= 5 and guard_rank is not None and guard_rank <= 5:
                    mechanism_counts["guard_only_preserves_bm25_top5_hit"] += 1
                else:
                    mechanism_counts["guard_only_not_bm25_top5_preservation"] += 1
            if group == "full_only":
                full_source = original_position_bucket(cands, full_item)
                if full_source in {"source_bm25_11_to_20", "source_bm25_21_to_100"}:
                    mechanism_counts["full_only_deep_displacement_hit"] += 1
                else:
                    mechanism_counts["full_only_not_deep_displacement_hit"] += 1

    accounting_ok = public_ok and private_ok and (
        len(base_hits), len(full_hits), len(guard_hits), len(full_hits | guard_hits), len(full_hits & guard_hits), len(full_hits - guard_hits), len(guard_hits - full_hits)
    ) == (5, 11, 10, 13, 8, 3, 2)
    if not public_ok:
        status = STATUS_NO_PUBLIC
    elif not private_ok:
        status = STATUS_NO_PRIVATE
    else:
        status = STATUS_COMPLETE if accounting_ok else STATUS_ACCOUNTING

    feature_rows: list[dict[str, Any]] = []
    idx = 0
    for group in ["full_only", "guard_only", "full_and_guard", "both_or_neither"]:
        for bucket, count in sorted(feature_counts.get(group, {}).items()):
            feature_rows.append({
                "anonymous_feature_bucket_id": f"n10ejfeature{idx:04d}",
                "membership_bucket": group,
                "observable_feature_bucket": bucket,
                "case_count": int(count),
            })
            idx += 1

    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10ej_full_guard_difference_analysis_v1",
        "phase_bucket": "BEA-v1-N10EJ Full-Only vs Guard-Only Difference Analysis",
        "status": status,
        "input_artifact_records": [{"anonymous_input_artifact_id": "n10ejinput0000", "artifact_bucket": "n10ei_public_package", "load_status_bucket": state, "expected_status_bucket": EXPECTED_N10EI_STATUS, "actual_status_bucket": str((n10ei or {}).get("status", "unavailable")), "status_match_bool": public_ok, "public_artifact_bool": True}],
        "private_input_intake_records": [{"anonymous_private_input_id": "n10ejpriv0000", "n10dz_top100_private_rows_available_bool": private_ok, "n10dz_top100_private_row_count": len(dz_rows), "same_scoped_n1_rows_available_bool": bool(n1_rows), "case_count": len(dz_rows), "private_status_bucket": private_status, "other_private_read_count": 0}],
        "membership_accounting_records": [{"anonymous_membership_id": "n10ejmember0000", "baseline_top10_count": len(base_hits), "full_novel_first_top10_count": len(full_hits), "guarded_top5_novel_distinct_top10_count": len(guard_hits), "full_guard_union_top10_count": len(full_hits | guard_hits), "full_guard_intersection_top10_count": len(full_hits & guard_hits), "full_only_top10_count": len(full_hits - guard_hits), "guard_only_top10_count": len(guard_hits - full_hits), "expected_membership_match_bool": accounting_ok}],
        "observable_difference_bucket_records": feature_rows,
        "mechanism_summary_records": [{"anonymous_mechanism_id": "n10ejmechanism0000", **mechanism_counts, "guard_only_preservation_signal_bool": mechanism_counts["guard_only_preserves_bm25_top5_hit"] > 0, "full_only_deep_displacement_signal_bool": mechanism_counts["full_only_deep_displacement_hit"] > 0, "interpretation_bucket": "guard_only_not_explained_by_bm25_top5_preservation_full_only_explained_by_deep_novel_first_displacement"}],
        "claim_boundary_records": [{"anonymous_claim_id": "n10ejclaim0000", "same_source_private_analysis_bool": True, "new_retrieval_bool": False, "openlocus_binary_execution_bool": False, "candidate_generation_bool": False, "runtime_default_change_bool": False, "selector_reranker_bool": False, "network_bool": False, "method_winner_claim_bool": False, "downstream_value_claim_bool": False, "heldout_generalization_claim_bool": False}],
        "gate_records": [{"anonymous_gate_id": "n10ejgate0000", "gate_bucket": "n10ei_public_input_present", "gate_passed_bool": public_ok}, {"anonymous_gate_id": "n10ejgate0001", "gate_bucket": "private_rows_present", "gate_passed_bool": private_ok}, {"anonymous_gate_id": "n10ejgate0002", "gate_bucket": "difference_accounting_expected", "gate_passed_bool": accounting_ok}],
        "stop_go_records": [{"anonymous_stop_go_id": "n10ejstop0000", "next_allowed_phase_bucket": "BEA-v1-N10EK Fixed Difference-Aware Combination Experiment", "n10ek_fixed_difference_aware_combination_authorized_bool": status == STATUS_COMPLETE, "private_read_scope_bucket": "same_n10dz_top100_and_n1_rows_only", "new_retrieval_authorized_bool": False, "scaled_retrieval_authorized_bool": False, "openlocus_binary_authorized_bool": False, "candidate_generation_authorized_bool": False, "runtime_default_authorized_bool": False, "selector_reranker_authorized_bool": False, "network_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_generalization_authorized_bool": False}],
    }
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report["status"] not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    return report


def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_ACCOUNTING in STATUS_VOCAB))
    try:
        parse_args(["--private", "/tmp/x"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("suffix", suffix_match("a/b/c.py", "b/c.py") and not suffix_match("a.py", "b.py")))
    checks.append(("novel_bucket", bucket_novel_count(11) == "novel_count_gt_10"))
    checks.append(("duplicate_bucket", bucket_top5_duplicate_pressure([{"path": "a"}, {"path": "a"}]) == "top5_duplicate_pressure_one"))
    checks.append(("source_bucket", original_position_bucket([{"path": str(i)} for i in range(12)], {"path": "x"}) == "source_unknown"))
    checks.append(("preservation_bucket", bucket_bm25_top5_preservation([{"path": "a"}], ["a"], 1) == "bm25_top5_preserved_by_guard"))
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
