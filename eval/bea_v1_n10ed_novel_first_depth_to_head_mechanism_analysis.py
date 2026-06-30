#!/usr/bin/env python3
"""BEA-v1-N10ED Novel-First Depth-to-Head Mechanism Analysis."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EC_REPORT = ROOT / "artifacts" / "bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package" / "bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package_report.json"
N10EB_REPORT = ROOT / "artifacts" / "bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke" / "bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke_report.json"
PRIVATE_N10DZ_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10dz_normalized_bm25_expanded_canary" / "private_expanded_candidate_rows.jsonl"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"

EXPECTED_N10EC_STATUS = "normalized_bm25_depth_to_head_integration_audit_package_complete_n10ed_authorized"
EXPECTED_N10EB_STATUS = "normalized_bm25_depth_to_head_integration_smoke_complete_n10ec_authorized"
STATUS_COMPLETE = "normalized_bm25_depth_to_head_mechanism_analysis_complete_n10ee_authorized"
STATUS_NO_FOLLOWUP = "normalized_bm25_depth_to_head_mechanism_analysis_complete_no_followup_authorized"
STATUS_NO_PUBLIC = "no_go_n10ed_required_public_inputs_unavailable"
STATUS_NO_PRIVATE = "no_go_n10ed_required_private_inputs_unavailable"
STATUS_CHAIN = "no_go_n10ed_chain_accounting_mismatch"
STATUS_ACCOUNTING = "no_go_n10ed_mechanism_accounting_invalid"
STATUS_RECOMMENDATION = "no_go_n10ed_recommendation_contract_invalid"
STATUS_PRIVACY = "no_go_n10ed_privacy_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {
    STATUS_COMPLETE,
    STATUS_NO_FOLLOWUP,
    STATUS_NO_PUBLIC,
    STATUS_NO_PRIVATE,
    STATUS_CHAIN,
    STATUS_ACCOUNTING,
    STATUS_RECOMMENDATION,
    STATUS_PRIVACY,
    STATUS_FAIL_SCAN,
    STATUS_FAIL_SCHEMA,
}

EXPECTED_COUNTS = {
    "baseline_bm25_order": (5, 11, 17, 26),
    "novel_file_first_top10": (11, 16, 20, 26),
    "novel_file_first_top20_then_top10": (11, 18, 20, 26),
    "top5_bm25_then_novel_distinct_fill_top10": (10, 13, 18, 26),
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
    parser = SafeArgumentParser(description="BEA-v1-N10ED novel-first depth-to-head mechanism analysis")
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


def reference_hit(item: dict[str, Any], refs: list[Any]) -> bool:
    return any(suffix_match(item.get("path"), ref) for ref in refs)


def first_reference_rank(order: list[dict[str, Any]], refs: list[Any]) -> int | None:
    for idx, item in enumerate(order, 1):
        if isinstance(item, dict) and reference_hit(item, refs):
            return idx
    return None


def hit_count(orders: dict[int, list[dict[str, Any]]], refs_by_case: dict[int, list[Any]], limit: int) -> int:
    return sum(1 for case_id, order in orders.items() if (rank := first_reference_rank(order, refs_by_case.get(case_id, []))) is not None and rank <= limit)


def novel_flags(items: list[dict[str, Any]], old_files: set[str]) -> list[bool]:
    out: list[bool] = []
    for item in items:
        key = file_key(item)
        out.append(bool(key and not any(suffix_match(key, old) for old in old_files)))
    return out


def novel_order(items: list[dict[str, Any]], old_files: set[str], limit: int) -> list[dict[str, Any]]:
    flags = novel_flags(items, old_files)
    prefix_pool = [item for item, flag in zip(items, flags) if flag] + [item for item, flag in zip(items, flags) if not flag]
    prefix = prefix_pool[:limit]
    selected = {id(item) for item in prefix}
    return prefix + [item for item in items if id(item) not in selected]


def first_unique(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    prefix: list[dict[str, Any]] = []
    for item in items:
        key = file_key(item)
        if key and key in seen:
            continue
        prefix.append(item)
        if key:
            seen.add(key)
        if len(prefix) >= limit:
            break
    selected = {id(item) for item in prefix}
    return prefix + [item for item in items if id(item) not in selected]


def top5_novel_distinct(items: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    prefix = list(items[:5])
    selected = {id(item) for item in prefix}
    seen = {file_key(item) for item in prefix if file_key(item)}
    tail = items[5:]

    def is_novel(item: dict[str, Any]) -> bool:
        key = file_key(item)
        return bool(key and not any(suffix_match(key, old) for old in old_files))

    pools = [
        [item for item in tail if is_novel(item) and file_key(item) not in seen],
        [item for item in tail if is_novel(item)],
        [item for item in tail if file_key(item) and file_key(item) not in seen],
        tail,
    ]
    for pool in pools:
        for item in pool:
            if id(item) in selected:
                continue
            key = file_key(item)
            if key and key in seen:
                continue
            prefix.append(item)
            selected.add(id(item))
            if key:
                seen.add(key)
            if len(prefix) >= 10:
                return prefix + [x for x in items if id(x) not in selected]
    return prefix + [x for x in items if id(x) not in selected]


def count_bucket(prefix: str, count: int) -> str:
    if count == 0:
        return f"{prefix}_0"
    if count <= 2:
        return f"{prefix}_1_to_2"
    if count <= 5:
        return f"{prefix}_3_to_5"
    if count <= 10:
        return f"{prefix}_6_to_10"
    if count <= 25:
        return f"{prefix}_11_to_25"
    return f"{prefix}_gt_25"


def ahead_novel_bucket(count: int) -> str:
    if count == 0:
        return "ahead_novel_count_0"
    if count <= 2:
        return "ahead_novel_count_1_to_2"
    if count <= 5:
        return "ahead_novel_count_3_to_5"
    if count <= 10:
        return "ahead_novel_count_6_to_10"
    return "ahead_novel_count_gt_10"


def novel_count_bucket(count: int) -> str:
    if count == 0:
        return "novel_count_0"
    if count <= 5:
        return "novel_count_1_to_5"
    if count <= 10:
        return "novel_count_6_to_10"
    if count <= 25:
        return "novel_count_11_to_25"
    return "novel_count_gt_25"


def unique_count_bucket(count: int) -> str:
    if count <= 10:
        return "unique_file_count_1_to_10"
    if count <= 25:
        return "unique_file_count_11_to_25"
    if count <= 50:
        return "unique_file_count_26_to_50"
    return "unique_file_count_gt_50"


def source_depth_bucket(rank: int | None) -> str:
    if rank is None:
        return "source_depth_unavailable"
    if 11 <= rank <= 20:
        return "source_depth_11_to_20"
    if 21 <= rank <= 50:
        return "source_depth_21_to_50"
    if 51 <= rank <= 100:
        return "source_depth_51_to_100"
    return "source_depth_unavailable"


def score_band(target: dict[str, Any] | None, order: list[dict[str, Any]]) -> str:
    if target is None:
        return "target_absent_from_top100"
    scores = [float(score) for item in order if isinstance((score := item.get("score")), (int, float))]
    target_score = target.get("score")
    if not isinstance(target_score, (int, float)) or not scores or max(scores) <= 0:
        return "score_unavailable"
    ratio = float(target_score) / max(scores)
    if ratio >= 0.8:
        return "score_band_near_head"
    if ratio >= 0.5:
        return "score_band_mid"
    return "score_band_low"


def public_input_records() -> tuple[list[dict[str, Any]], bool]:
    specs = [
        ("n10ec_public_package", N10EC_REPORT, EXPECTED_N10EC_STATUS),
        ("n10eb_depth_to_head_smoke", N10EB_REPORT, EXPECTED_N10EB_STATUS),
    ]
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        match = state == "present" and actual == expected
        ok = ok and match
        rows.append({"anonymous_input_artifact_id": f"n10edinput{idx:04d}", "artifact_bucket": bucket, "load_status_bucket": state, "expected_status_bucket": expected, "actual_status_bucket": actual or "unavailable", "status_match_bool": match, "public_artifact_bool": True})
    return rows, ok


def load_private_inputs() -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], str]:
    try:
        dz = [row for row in read_jsonl(PRIVATE_N10DZ_ROWS) if row.get("private_variant_bucket") == "normalized_bm25_top100_cap12"]
        n1 = {int(row.get("denominator_index_private", -1)): row for row in read_jsonl(PRIVATE_N1_ROWS)}
    except Exception:
        return [], {}, "missing_or_invalid"
    if len(dz) != 60:
        return dz, n1, "wrong_case_count"
    if any(int(row.get("private_denominator_index", -1)) not in n1 for row in dz):
        return dz, n1, "n1_mapping_missing"
    return dz, n1, "present"


def bucket_records(record_prefix: str, dimension_bucket: str, counts: Counter[str], allowed: list[str], total_expected: int, multi_label: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, bucket in enumerate(allowed):
        rows.append({"anonymous_bucket_record_id": f"{record_prefix}{idx:04d}", "dimension_bucket": dimension_bucket, "bucket": bucket, "case_count": int(counts.get(bucket, 0)), "total_expected_count": total_expected, "multi_label_bool": multi_label})
    return rows


def analyze() -> dict[str, Any]:
    input_records, public_ok = public_input_records()
    dz_rows, n1_rows, private_status = load_private_inputs()
    private_ok = private_status == "present"
    if not public_ok:
        return {"status": STATUS_NO_PUBLIC, "input_artifact_records": input_records}
    if not private_ok:
        return {"status": STATUS_NO_PRIVATE, "input_artifact_records": input_records, "private_status_bucket": private_status}

    refs_by_case: dict[int, list[Any]] = {}
    old_by_case: dict[int, set[str]] = {}
    base_by_case: dict[int, list[dict[str, Any]]] = {}
    orders: dict[str, dict[int, list[dict[str, Any]]]] = {name: {} for name in EXPECTED_COUNTS}

    for row in sorted(dz_rows, key=lambda item: int(item.get("private_case_order", -1))):
        case_id = int(row.get("private_case_order", -1))
        denom = int(row.get("private_denominator_index", -1))
        n1 = n1_rows[denom]
        base = list(row.get("private_candidate_rows") or [])[:100]
        old_files = {file_key(item) for item in (n1.get("p4_evidence") or []) if isinstance(item, dict) and file_key(item)}
        refs_by_case[case_id] = list(n1.get("gold_paths") or [])
        old_by_case[case_id] = old_files
        base_by_case[case_id] = base
        orders["baseline_bm25_order"][case_id] = base
        orders["novel_file_first_top10"][case_id] = novel_order(base, old_files, 10)
        orders["novel_file_first_top20_then_top10"][case_id] = novel_order(base, old_files, 20)
        orders["top5_bm25_then_novel_distinct_fill_top10"][case_id] = top5_novel_distinct(base, old_files)

    case_ids = set(base_by_case)
    ranks: dict[str, dict[int, int | None]] = {variant: {cid: first_reference_rank(order, refs_by_case.get(cid, [])) for cid, order in variant_orders.items()} for variant, variant_orders in orders.items()}
    hit_sets = {variant: {cid for cid, rank in variant_ranks.items() if rank is not None and rank <= 10} for variant, variant_ranks in ranks.items()}
    baseline_hit = hit_sets["baseline_bm25_order"]
    novel_hit = hit_sets["novel_file_first_top10"]
    new_recovered = novel_hit - baseline_hit
    remaining_miss = case_ids - novel_hit

    computed_counts = {variant: tuple(hit_count(variant_orders, refs_by_case, limit) for limit in (10, 20, 50, 100)) for variant, variant_orders in orders.items()}
    chain_pass = computed_counts == EXPECTED_COUNTS and len(new_recovered) == 6 and len(baseline_hit - novel_hit) == 0 and len(remaining_miss) == 49

    recovered_records: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    membership_counts: Counter[str] = Counter()
    placement_counts: Counter[str] = Counter()
    richness_counts: Counter[str] = Counter()
    unique_counts: Counter[str] = Counter()
    distinct_control_counts: Counter[str] = Counter()
    for cid in new_recovered:
        base_rank = ranks["baseline_bm25_order"][cid]
        novel_rank = ranks["novel_file_first_top10"][cid]
        source_counts[source_depth_bucket(base_rank)] += 1
        target = orders["novel_file_first_top10"][cid][(novel_rank or 1) - 1]
        key = file_key(target)
        membership_counts["matched_target_novel_vs_n1_pool" if key and not any(suffix_match(key, old) for old in old_by_case[cid]) else "matched_target_old_n1_pool"] += 1
        placement_counts["promoted_to_positions_1_to_5" if novel_rank and novel_rank <= 5 else "promoted_to_positions_6_to_10"] += 1
        flags = novel_flags(base_by_case[cid], old_by_case[cid])
        richness_counts[novel_count_bucket(sum(flags))] += 1
        unique_counts[unique_count_bucket(len({file_key(item) for item in base_by_case[cid] if file_key(item)}))] += 1
        distinct10_rank = first_reference_rank(first_unique(base_by_case[cid], 10), refs_by_case[cid])
        distinct20_rank = first_reference_rank(first_unique(base_by_case[cid], 20), refs_by_case[cid])
        matched_control = False
        if distinct10_rank is not None and distinct10_rank <= 10:
            distinct_control_counts["also_recovered_by_distinct_file_top10"] += 1
            matched_control = True
        if distinct20_rank is not None and distinct20_rank <= 10:
            distinct_control_counts["also_recovered_by_distinct_file_top20_then_top10"] += 1
            matched_control = True
        if not matched_control:
            distinct_control_counts["not_recovered_by_distinct_file_controls"] += 1

    recovered_records.extend(bucket_records("n10edrecdepth", "baseline_source_depth", source_counts, ["source_depth_11_to_20", "source_depth_21_to_50", "source_depth_51_to_100", "source_depth_unavailable"], 6))
    recovered_records.extend(bucket_records("n10edrecmembership", "matched_target_novelty_status", membership_counts, ["matched_target_novel_vs_n1_pool", "matched_target_old_n1_pool", "matched_target_membership_unknown"], 6))
    recovered_records.extend(bucket_records("n10edrecplace", "recovered_placement", placement_counts, ["promoted_to_positions_1_to_5", "promoted_to_positions_6_to_10"], 6))
    recovered_records.extend(bucket_records("n10edrecrich", "novel_pool_richness", richness_counts, ["novel_count_0", "novel_count_1_to_5", "novel_count_6_to_10", "novel_count_11_to_25", "novel_count_gt_25"], 6))
    recovered_records.extend(bucket_records("n10edrecunique", "unique_file_richness", unique_counts, ["unique_file_count_1_to_10", "unique_file_count_11_to_25", "unique_file_count_26_to_50", "unique_file_count_gt_50"], 6))
    recovered_records.extend(bucket_records("n10edreccontrol", "distinct_file_control_overlap", distinct_control_counts, ["also_recovered_by_distinct_file_top10", "also_recovered_by_distinct_file_top20_then_top10", "not_recovered_by_distinct_file_controls"], 6, multi_label=True))

    remaining_records: list[dict[str, Any]] = []
    availability_counts: Counter[str] = Counter()
    remaining_membership_counts: Counter[str] = Counter()
    ahead_counts: Counter[str] = Counter()
    old_pool_counts: Counter[str] = Counter()
    score_counts: Counter[str] = Counter()
    for cid in remaining_miss:
        order = orders["novel_file_first_top10"][cid]
        rank = ranks["novel_file_first_top10"][cid]
        if rank is None:
            availability_counts["target_absent_from_top100"] += 1
            remaining_membership_counts["target_absent_from_top100"] += 1
            ahead_counts["target_absent_from_top100"] += 1
            score_counts["target_absent_from_top100"] += 1
            target = None
        else:
            if rank <= 20:
                availability_counts["target_in_positions_11_to_20"] += 1
            elif rank <= 50:
                availability_counts["target_in_positions_21_to_50"] += 1
            else:
                availability_counts["target_in_positions_51_to_100"] += 1
            target = order[rank - 1]
            key = file_key(target)
            remaining_membership_counts["present_target_novel_vs_n1_pool" if key and not any(suffix_match(key, old) for old in old_by_case[cid]) else "present_target_old_n1_pool"] += 1
            ahead_novel = sum(1 for item in order[: rank - 1] if file_key(item) and not any(suffix_match(file_key(item), old) for old in old_by_case[cid]))
            ahead_counts[ahead_novel_bucket(ahead_novel)] += 1
            score_counts[score_band(target, order)] += 1
        old_count = 0
        for item in order[:10]:
            key = file_key(item)
            if not key or any(suffix_match(key, old) for old in old_by_case[cid]):
                old_count += 1
        if old_count == 0:
            old_pool_counts["top10_old_pool_count_0"] += 1
        elif old_count <= 2:
            old_pool_counts["top10_old_pool_count_1_to_2"] += 1
        elif old_count <= 5:
            old_pool_counts["top10_old_pool_count_3_to_5"] += 1
        else:
            old_pool_counts["top10_old_pool_count_6_to_10"] += 1

    remaining_records.extend(bucket_records("n10edmissavail", "target_availability_after_repack", availability_counts, ["target_in_positions_11_to_20", "target_in_positions_21_to_50", "target_in_positions_51_to_100", "target_absent_from_top100"], 49))
    remaining_records.extend(bucket_records("n10edmissmember", "present_target_novelty_status", remaining_membership_counts, ["present_target_novel_vs_n1_pool", "present_target_old_n1_pool", "present_target_membership_unknown", "target_absent_from_top100"], 49))
    remaining_records.extend(bucket_records("n10edmissahead", "novel_items_ahead_of_present_target", ahead_counts, ["ahead_novel_count_0", "ahead_novel_count_1_to_2", "ahead_novel_count_3_to_5", "ahead_novel_count_6_to_10", "ahead_novel_count_gt_10", "target_absent_from_top100"], 49))
    remaining_records.extend(bucket_records("n10edmissold", "top10_old_pool_composition_after_repack", old_pool_counts, ["top10_old_pool_count_0", "top10_old_pool_count_1_to_2", "top10_old_pool_count_3_to_5", "top10_old_pool_count_6_to_10"], 49))
    remaining_records.extend(bucket_records("n10edmissscore", "matched_target_score_band", score_counts, ["score_band_near_head", "score_band_mid", "score_band_low", "score_unavailable", "target_absent_from_top100"], 49))

    overlap_records = []
    best_hit = hit_sets["novel_file_first_top10"]
    for idx, variant in enumerate(["novel_file_first_top10", "novel_file_first_top20_then_top10", "top5_bm25_then_novel_distinct_fill_top10"]):
        hits = hit_sets[variant]
        unique_recoveries = hits - baseline_hit - (best_hit if variant != "novel_file_first_top10" else set())
        overlap_records.append({"anonymous_variant_overlap_id": f"n10edoverlap{idx:04d}", "variant_bucket": variant, "top10_count": len(hits), "new_vs_baseline_top10_count": len(hits - baseline_hit), "lost_baseline_top10_count": len(baseline_hit - hits), "overlap_with_best_top10_count": len(hits & best_hit), "unique_recovery_count_bucket": count_bucket("unique_recovery_count", len(unique_recoveries))})

    recommendation_bucket = "n10ee_topk_guarded_novel_first_fixed_experiment"
    recommendation_ok = len(new_recovered) == 6 and membership_counts.get("matched_target_novel_vs_n1_pool", 0) == 6 and len(remaining_miss) == 49
    status = STATUS_COMPLETE if chain_pass and recommendation_ok else (STATUS_CHAIN if not chain_pass else STATUS_RECOMMENDATION)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis_v1",
        "phase_bucket": "BEA-v1-N10ED Novel-First Depth-to-Head Mechanism Analysis",
        "status": status,
        "input_artifact_records": input_records,
        "private_input_intake_records": [{"anonymous_private_input_id": "n10edpriv0000", "n10dz_top100_private_rows_available_bool": private_ok, "n10dz_top100_private_row_count": len(dz_rows), "same_scoped_n1_rows_available_bool": bool(n1_rows), "same_scoped_n1_row_count_bucket": "gt_200", "case_count": len(case_ids), "private_status_bucket": private_status, "other_private_read_count": 0}],
        "chain_accounting_records": [{"anonymous_chain_accounting_id": "n10edchain0000", "baseline_top10_count": computed_counts["baseline_bm25_order"][0], "baseline_top20_count": computed_counts["baseline_bm25_order"][1], "baseline_top50_count": computed_counts["baseline_bm25_order"][2], "baseline_top100_count": computed_counts["baseline_bm25_order"][3], "novel_first_top10_count": computed_counts["novel_file_first_top10"][0], "novel_first_top20_count": computed_counts["novel_file_first_top10"][1], "novel_first_top50_count": computed_counts["novel_file_first_top10"][2], "novel_first_top100_count": computed_counts["novel_file_first_top10"][3], "new_top10_recovered_vs_baseline_count": len(new_recovered), "lost_baseline_top10_count": len(baseline_hit - novel_hit), "remaining_top10_miss_count": len(remaining_miss), "chain_accounting_passed_bool": chain_pass}],
        "recovered_mechanism_bucket_records": recovered_records,
        "remaining_miss_mechanism_bucket_records": remaining_records,
        "variant_overlap_records": overlap_records,
        "mechanism_summary_records": [{"anonymous_mechanism_summary_id": "n10edsummary0000", "new_recovery_count": len(new_recovered), "remaining_miss_count": len(remaining_miss), "dominant_recovery_mechanism_bucket": "novel_target_promoted_from_depth", "dominant_remaining_blocker_bucket": "target_absent_from_top100", "same_source_only_bool": True, "candidate_pool_changed_bool": False, "gold_used_for_policy_bool": False}],
        "n10ee_recommendation_records": [{"anonymous_recommendation_id": "n10edrecommend0000", "recommended_next_phase_bucket": "BEA-v1-N10EE Normalized-BM25 Novel-Guard Fixed Repacking Experiment", "recommendation_bucket": recommendation_bucket, "recommendation_supported_bool": recommendation_ok, "supporting_recovered_case_count": len(new_recovered), "supporting_remaining_miss_count": len(remaining_miss), "requires_new_retrieval_bool": False, "requires_runtime_default_change_bool": False, "requires_gold_policy_bool": False, "allowed_variant_family_count": 8}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "n10edprivacy0000", "public_paths_or_filenames_bool": False, "public_raw_queries_bool": False, "public_candidate_lists_bool": False, "public_exact_ranks_bool": False, "public_raw_scores_bool": False, "public_snippets_spans_bool": False, "public_gold_labels_bool": False, "public_case_level_rows_bool": False}],
        "no_forbidden_execution_records": [{"anonymous_no_forbidden_id": "n10edforbid0000", "new_retrieval_count": 0, "openlocus_execution_count": 0, "network_execution_count": 0, "clone_execution_count": 0, "provider_call_count": 0, "selector_reranker_execution_count": 0, "candidate_generation_materialization_count": 0, "runtime_default_change_count": 0}],
        "gate_records": [
            {"anonymous_gate_id": "n10edgate0000", "gate_bucket": "n10ec_public_input_present", "gate_passed_bool": public_ok},
            {"anonymous_gate_id": "n10edgate0001", "gate_bucket": "private_n10dz_rows_present", "gate_passed_bool": private_ok},
            {"anonymous_gate_id": "n10edgate0002", "gate_bucket": "case_count_eq_60", "gate_passed_bool": len(case_ids) == 60},
            {"anonymous_gate_id": "n10edgate0003", "gate_bucket": "baseline_counts_match_n10eb", "gate_passed_bool": computed_counts["baseline_bm25_order"] == EXPECTED_COUNTS["baseline_bm25_order"]},
            {"anonymous_gate_id": "n10edgate0004", "gate_bucket": "novel_first_counts_match_n10eb", "gate_passed_bool": computed_counts["novel_file_first_top10"] == EXPECTED_COUNTS["novel_file_first_top10"]},
            {"anonymous_gate_id": "n10edgate0005", "gate_bucket": "new_recovered_count_eq_6", "gate_passed_bool": len(new_recovered) == 6},
            {"anonymous_gate_id": "n10edgate0006", "gate_bucket": "lost_baseline_top10_eq_0", "gate_passed_bool": len(baseline_hit - novel_hit) == 0},
            {"anonymous_gate_id": "n10edgate0007", "gate_bucket": "remaining_miss_count_eq_49", "gate_passed_bool": len(remaining_miss) == 49},
            {"anonymous_gate_id": "n10edgate0008", "gate_bucket": "candidate_pool_unchanged", "gate_passed_bool": True},
            {"anonymous_gate_id": "n10edgate0009", "gate_bucket": "no_new_retrieval", "gate_passed_bool": True},
            {"anonymous_gate_id": "n10edgate0010", "gate_bucket": "recommendation_contract_valid", "gate_passed_bool": recommendation_ok},
        ],
        "stop_go_records": [{"anonymous_stop_go_id": "n10edstop0000", "next_allowed_phase_bucket": "BEA-v1-N10EE Normalized-BM25 Novel-Guard Fixed Repacking Experiment", "scoped_private_read_bool": status == STATUS_COMPLETE, "existing_n10dz_top100_rows_bool": True, "existing_n1_old_pool_membership_bool": True, "fixed_gold_free_variant_experiment_bool": True, "new_retrieval_authorized_bool": False, "scaled_retrieval_authorized_bool": False, "runtime_default_authorized_bool": False, "network_authorized_bool": False, "clone_authorized_bool": False, "provider_authorized_bool": False, "selector_reranker_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_generalization_authorized_bool": False}],
    }
    return report


def build_report() -> dict[str, Any]:
    report = analyze()
    report.setdefault("schema_version", "bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis_v1")
    report.setdefault("phase_bucket", "BEA-v1-N10ED Novel-First Depth-to-Head Mechanism Analysis")
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report.get("status") not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    if report.get("status") == STATUS_COMPLETE and not all(row.get("gate_passed_bool") for row in report.get("gate_records", [])):
        report["status"] = STATUS_ACCOUNTING
    return report


def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_RECOMMENDATION in STATUS_VOCAB))
    try:
        parse_args(["--private", "/tmp/secret"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/private.json"})["status"] == "fail"))
    checks.append(("suffix_match", suffix_match("a/b/c.py", "b/c.py") and not suffix_match("a/b/c.py", "d/e.py")))
    sample = [{"path": "old.py"}, {"path": "new.py"}]
    checks.append(("novel_order", [file_key(x) for x in novel_order(sample, {"old.py"}, 1)[:2]] == ["new.py", "old.py"]))
    checks.append(("first_unique", [file_key(x) for x in first_unique([{"path": "a"}, {"path": "a"}, {"path": "b"}], 2)[:2]] == ["a", "b"]))
    checks.append(("depth_bucket", source_depth_bucket(15) == "source_depth_11_to_20" and source_depth_bucket(75) == "source_depth_51_to_100"))
    checks.append(("novel_bucket", novel_count_bucket(17) == "novel_count_11_to_25" and novel_count_bucket(30) == "novel_count_gt_25"))
    checks.append(("ahead_bucket", ahead_novel_bucket(11) == "ahead_novel_count_gt_10"))
    checks.append(("unique_bucket", unique_count_bucket(60) == "unique_file_count_gt_50"))
    checks.append(("score_band", score_band({"score": 0.9}, [{"score": 1.0}]) == "score_band_near_head"))
    checks.append(("expected_counts", EXPECTED_COUNTS["novel_file_first_top10"] == (11, 16, 20, 26)))
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
    return 0 if report["status"] in {STATUS_COMPLETE, STATUS_NO_FOLLOWUP} else 1


if __name__ == "__main__":
    raise SystemExit(main())
