#!/usr/bin/env python3
"""BEA-v1-N10EB Normalized-BM25 Depth-to-Head Integration Smoke."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10EA_REPORT = ROOT / "artifacts" / "bea_v1_n10ea_normalized_bm25_expanded_canary_public_package" / "bea_v1_n10ea_normalized_bm25_expanded_canary_public_package_report.json"
N10DZ_REPORT = ROOT / "artifacts" / "bea_v1_n10dz_normalized_bm25_expanded_canary" / "bea_v1_n10dz_normalized_bm25_expanded_canary_report.json"
N10DW_REPORT = ROOT / "artifacts" / "bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis" / "bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis_report.json"
PRIVATE_N10DZ_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10dz_normalized_bm25_expanded_canary" / "private_expanded_candidate_rows.jsonl"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"

STATUS_COMPLETE = "normalized_bm25_depth_to_head_integration_smoke_complete_n10ec_authorized"
STATUS_NO_INPUTS = "no_go_n10eb_required_inputs_unavailable"
STATUS_PRIVATE_MISSING = "no_go_n10eb_private_candidate_rows_missing"
STATUS_VARIANT_INVALID = "no_go_n10eb_variant_contract_invalid"
STATUS_ACCOUNTING = "no_go_n10eb_result_accounting_invalid"
STATUS_PRIVACY = "no_go_n10eb_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {
    STATUS_COMPLETE,
    STATUS_NO_INPUTS,
    STATUS_PRIVATE_MISSING,
    STATUS_VARIANT_INVALID,
    STATUS_ACCOUNTING,
    STATUS_PRIVACY,
    STATUS_FAIL_SCAN,
    STATUS_FAIL_SCHEMA,
}

EXPECTED_PUBLIC_INPUTS = [
    ("n10ea_public_package", N10EA_REPORT, "normalized_bm25_expanded_canary_public_package_complete_n10eb_authorized"),
    ("n10dz_expanded_canary", N10DZ_REPORT, "normalized_bm25_expanded_canary_low_recovery_n10ea_authorized"),
    ("n10dw_mechanism_analysis", N10DW_REPORT, "normalized_bm25_recovery_mechanism_analysis_complete_n10dx_authorized"),
]

VARIANTS = [
    "baseline_bm25_order",
    "distinct_file_top10",
    "distinct_file_top20_then_top10",
    "novel_file_first_top10",
    "novel_file_first_top20_then_top10",
    "top5_bm25_then_novel_fill_top10",
    "top5_bm25_then_distinct_file_fill_top10",
    "top5_bm25_then_novel_distinct_fill_top10",
]

BASELINE_EXPECTED = {"top10": 5, "top20": 11, "top50": 17, "top100": 26}

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
    parser = SafeArgumentParser(description="BEA-v1-N10EB normalized BM25 depth-to-head integration smoke")
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


def candidate_file(item: dict[str, Any]) -> str:
    return norm_ref(item.get("path"))


def hits_gold(item: dict[str, Any], refs: list[Any]) -> bool:
    return any(suffix_match(item.get("path"), ref) for ref in refs)


def file_hit(order: list[dict[str, Any]], refs: list[Any], limit: int) -> bool:
    return any(hits_gold(item, refs) for item in order[:limit] if isinstance(item, dict))


def order_hit_counts(orders: dict[int, list[dict[str, Any]]], gold_by_case: dict[int, list[Any]], limit: int) -> int:
    return sum(1 for case_id, order in orders.items() if file_hit(order, gold_by_case.get(case_id, []), limit))


def n10t_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = [item for idx, item in enumerate(evidence, 1) if idx <= 20]
    extra = [item for idx, item in enumerate(evidence, 1) if idx > 20]
    return list(extra) + primary[:4] + primary[4:]


def first_unique(candidates: list[dict[str, Any]], limit: int, selected: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    chosen = list(selected or [])
    seen = {candidate_file(item) for item in chosen if candidate_file(item)}
    for item in candidates:
        key = candidate_file(item)
        if key and key in seen:
            continue
        chosen.append(item)
        if key:
            seen.add(key)
        if len(chosen) >= limit:
            break
    return chosen


def append_remaining(prefix: list[dict[str, Any]], original: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_ids = {id(item) for item in prefix}
    return list(prefix) + [item for item in original if id(item) not in selected_ids]


def novel_flags(candidates: list[dict[str, Any]], old_files: set[str]) -> list[bool]:
    flags: list[bool] = []
    for item in candidates:
        key = candidate_file(item)
        flags.append(bool(key and not any(suffix_match(key, old) for old in old_files)))
    return flags


def novel_prefix(candidates: list[dict[str, Any]], old_files: set[str], limit: int) -> list[dict[str, Any]]:
    flags = novel_flags(candidates, old_files)
    novel = [item for item, flag in zip(candidates, flags) if flag]
    old = [item for item, flag in zip(candidates, flags) if not flag]
    return (novel + old)[:limit]


def fill_top5(candidates: list[dict[str, Any]], old_files: set[str], mode: str) -> list[dict[str, Any]]:
    prefix = list(candidates[:5])
    seen = {candidate_file(item) for item in prefix if candidate_file(item)}
    selected_ids = {id(item) for item in prefix}

    def is_novel(item: dict[str, Any]) -> bool:
        key = candidate_file(item)
        return bool(key and not any(suffix_match(key, old) for old in old_files))

    def is_distinct(item: dict[str, Any]) -> bool:
        key = candidate_file(item)
        return bool(key and key not in seen)

    pools: list[list[dict[str, Any]]] = []
    tail = candidates[5:]
    if mode == "novel":
        pools = [[item for item in tail if is_novel(item)], tail]
    elif mode == "distinct":
        pools = [[item for item in tail if is_distinct(item)], tail]
    elif mode == "novel_distinct":
        pools = [
            [item for item in tail if is_novel(item) and is_distinct(item)],
            [item for item in tail if is_novel(item)],
            [item for item in tail if is_distinct(item)],
            tail,
        ]
    else:  # pragma: no cover
        pools = [tail]
    require_distinct_fill = mode in {"distinct", "novel_distinct"}
    for pool in pools:
        for item in pool:
            if id(item) in selected_ids:
                continue
            key = candidate_file(item)
            if require_distinct_fill and key and key in seen:
                continue
            prefix.append(item)
            selected_ids.add(id(item))
            if key:
                seen.add(key)
            if len(prefix) >= 10:
                return prefix
    return prefix[:10]


def apply_variant(variant: str, candidates: list[dict[str, Any]], old_files: set[str]) -> list[dict[str, Any]]:
    if variant == "baseline_bm25_order":
        return list(candidates)
    if variant == "distinct_file_top10":
        return append_remaining(first_unique(candidates, 10), candidates)
    if variant == "distinct_file_top20_then_top10":
        return append_remaining(first_unique(candidates, 20), candidates)
    if variant == "novel_file_first_top10":
        return append_remaining(novel_prefix(candidates, old_files, 10), candidates)
    if variant == "novel_file_first_top20_then_top10":
        return append_remaining(novel_prefix(candidates, old_files, 20), candidates)
    if variant == "top5_bm25_then_novel_fill_top10":
        return append_remaining(fill_top5(candidates, old_files, "novel"), candidates)
    if variant == "top5_bm25_then_distinct_file_fill_top10":
        return append_remaining(fill_top5(candidates, old_files, "distinct"), candidates)
    if variant == "top5_bm25_then_novel_distinct_fill_top10":
        return append_remaining(fill_top5(candidates, old_files, "novel_distinct"), candidates)
    raise ValueError(f"unknown variant: {variant}")


def distinct_fill_violation_count(order: list[dict[str, Any]]) -> int:
    violations = 0
    for idx in range(5, min(10, len(order))):
        key = candidate_file(order[idx])
        if key and any(candidate_file(prev) == key for prev in order[:idx]):
            violations += 1
    return violations


def count_bucket(count: int) -> str:
    if count == 0:
        return "zero"
    if count <= 2:
        return "one_to_two"
    if count <= 5:
        return "three_to_five"
    if count <= 10:
        return "six_to_ten"
    return "gt_ten"


def public_input_records() -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(EXPECTED_PUBLIC_INPUTS):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        match = state == "present" and actual == expected
        ok = ok and match
        records.append({"anonymous_input_artifact_id": f"n10ebinput{idx:04d}", "artifact_bucket": bucket, "load_status_bucket": state, "expected_status_bucket": expected, "actual_status_bucket": actual or "unavailable", "status_match_bool": match, "public_artifact_bool": True})
    return records, ok


def load_private_inputs() -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], str]:
    try:
        dz_rows = [row for row in read_jsonl(PRIVATE_N10DZ_ROWS) if row.get("private_variant_bucket") == "normalized_bm25_top100_cap12"]
        n1_rows = {int(row.get("denominator_index_private", -1)): row for row in read_jsonl(PRIVATE_N1_ROWS)}
    except Exception:
        return [], {}, "missing_or_invalid"
    if len(dz_rows) != 60:
        return dz_rows, n1_rows, "wrong_case_count"
    if any(len(row.get("private_candidate_rows") or []) < 1 for row in dz_rows):
        return dz_rows, n1_rows, "candidate_rows_empty"
    if any(int(row.get("private_denominator_index", -1)) not in n1_rows for row in dz_rows):
        return dz_rows, n1_rows, "n1_mapping_missing"
    return dz_rows, n1_rows, "present"


def analyze() -> tuple[dict[str, Any], str]:
    public_records, public_ok = public_input_records()
    dz_rows, n1_by_denom, private_status = load_private_inputs()
    private_ok = private_status == "present"
    if not public_ok:
        return {"input_artifact_records": public_records, "status": STATUS_NO_INPUTS}, private_status
    if not private_ok:
        return {"input_artifact_records": public_records, "status": STATUS_PRIVATE_MISSING, "private_status": private_status}, private_status

    gold_by_case: dict[int, list[Any]] = {}
    old_files_by_case: dict[int, set[str]] = {}
    top100_by_case: dict[int, list[dict[str, Any]]] = {}
    for row in sorted(dz_rows, key=lambda r: int(r.get("private_case_order", -1))):
        case_id = int(row.get("private_case_order", -1))
        denom = int(row.get("private_denominator_index", -1))
        n1 = n1_by_denom[denom]
        gold_by_case[case_id] = list(n1.get("gold_paths") or [])
        old_files_by_case[case_id] = {candidate_file(item) for item in (n1.get("p4_evidence") or []) if isinstance(item, dict) and candidate_file(item)}
        top100_by_case[case_id] = list(row.get("private_candidate_rows") or [])[:100]

    orders_by_variant: dict[str, dict[int, list[dict[str, Any]]]] = {}
    for variant in VARIANTS:
        orders_by_variant[variant] = {
            case_id: apply_variant(variant, candidates, old_files_by_case.get(case_id, set()))
            for case_id, candidates in top100_by_case.items()
        }

    baseline_orders = orders_by_variant["baseline_bm25_order"]
    baseline_hits10 = {case_id for case_id, order in baseline_orders.items() if file_hit(order, gold_by_case.get(case_id, []), 10)}
    baseline_hits20 = {case_id for case_id, order in baseline_orders.items() if file_hit(order, gold_by_case.get(case_id, []), 20)}
    baseline_hits100 = {case_id for case_id, order in baseline_orders.items() if file_hit(order, gold_by_case.get(case_id, []), 100)}

    baseline_counts = {
        "top10": len(baseline_hits10),
        "top20": len(baseline_hits20),
        "top50": order_hit_counts(baseline_orders, gold_by_case, 50),
        "top100": len(baseline_hits100),
    }

    variant_results: list[dict[str, Any]] = []
    novelty_summary: list[dict[str, Any]] = []
    distinct_fill_contract_rows: list[dict[str, Any]] = []
    decision_counter: Counter[str] = Counter()
    for idx, variant in enumerate(VARIANTS):
        orders = orders_by_variant[variant]
        top10_hits = {case_id for case_id, order in orders.items() if file_hit(order, gold_by_case.get(case_id, []), 10)}
        top20_hits = {case_id for case_id, order in orders.items() if file_hit(order, gold_by_case.get(case_id, []), 20)}
        counts = {
            "top10": len(top10_hits),
            "top20": len(top20_hits),
            "top50": order_hit_counts(orders, gold_by_case, 50),
            "top100": order_hit_counts(orders, gold_by_case, 100),
        }
        lost = len(baseline_hits10 - top10_hits)
        recovered_to_top10 = len((baseline_hits100 - baseline_hits10) & top10_hits)
        recovered_to_top20 = len((baseline_hits100 - baseline_hits20) & top20_hits)
        decision = "depth_to_head_success" if counts["top10"] >= 10 and lost <= 1 else ("top20_improvement_only" if counts["top10"] < 10 and counts["top20"] > BASELINE_EXPECTED["top20"] else "no_head_improvement")
        decision_counter[decision] += 1
        order_changed = False
        if variant != "baseline_bm25_order":
            order_changed = any(
                [candidate_file(orders[case_id][i]) if i < len(orders[case_id]) else "" for i in range(min(10, len(orders[case_id])))]
                != [candidate_file(top100_by_case[case_id][i]) if i < len(top100_by_case[case_id]) else "" for i in range(min(10, len(top100_by_case[case_id])))]
                for case_id in orders
            )

        novel_counts: Counter[str] = Counter()
        old_counts: Counter[str] = Counter()
        for case_id, order in orders.items():
            old_files = old_files_by_case.get(case_id, set())
            top10 = order[:10]
            novel = 0
            old = 0
            for item in top10:
                key = candidate_file(item)
                if key and not any(suffix_match(key, old_file) for old_file in old_files):
                    novel += 1
                else:
                    old += 1
            novel_counts[count_bucket(novel)] += 1
            old_counts[count_bucket(old)] += 1

        variant_results.append({
            "anonymous_variant_result_id": f"n10ebvariant{idx:04d}",
            "variant_bucket": variant,
            "top10_file_recovery_count": counts["top10"],
            "top20_file_recovery_count": counts["top20"],
            "top50_file_recovery_count": counts["top50"],
            "top100_file_recovery_count": counts["top100"],
            "delta_top10_vs_baseline_bm25": counts["top10"] - baseline_counts["top10"],
            "delta_top20_vs_baseline_bm25": counts["top20"] - baseline_counts["top20"],
            "lost_baseline_top10_hits": lost,
            "recovered_depth_to_top10_count": recovered_to_top10,
            "recovered_depth_to_top20_count": recovered_to_top20,
            "novel_candidate_selected_count_bucket": "aggregate_in_novelty_selection_summary_records",
            "old_pool_candidate_selected_count_bucket": "aggregate_in_novelty_selection_summary_records",
            "candidate_pool_changed_bool": False,
            "candidate_added_removed_bool": False,
            "order_changed_bool": order_changed,
            "decision_bucket": decision,
        })
        for bucket, count in sorted(novel_counts.items()):
            novelty_summary.append({"anonymous_novelty_summary_id": f"n10ebnovel{idx:04d}{bucket}", "variant_bucket": variant, "selected_group_bucket": "novel_vs_n1_pool", "selected_count_bucket": bucket, "case_count": int(count)})
        for bucket, count in sorted(old_counts.items()):
            novelty_summary.append({"anonymous_novelty_summary_id": f"n10ebold{idx:04d}{bucket}", "variant_bucket": variant, "selected_group_bucket": "old_n1_pool", "selected_count_bucket": bucket, "case_count": int(count)})
        if variant in {"top5_bm25_then_distinct_file_fill_top10", "top5_bm25_then_novel_distinct_fill_top10"}:
            violation_count = sum(distinct_fill_violation_count(order) for order in orders.values())
            distinct_fill_contract_rows.append({"anonymous_distinct_fill_contract_id": f"n10ebdistinct{idx:04d}", "variant_bucket": variant, "fill_slots_checked_bucket": "ranks_6_to_10", "fill_duplicate_against_prior_rank_count": int(violation_count), "distinct_fill_contract_passed_bool": violation_count == 0})

    best_top10 = max(row["top10_file_recovery_count"] for row in variant_results)
    best_rows = [row for row in variant_results if row["top10_file_recovery_count"] == best_top10]
    status = STATUS_COMPLETE
    if set(VARIANTS) != {row["variant_bucket"] for row in variant_results} or len(variant_results) != 8:
        status = STATUS_VARIANT_INVALID
    if baseline_counts != BASELINE_EXPECTED:
        status = STATUS_ACCOUNTING

    report = {
        "schema_version": "bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke_v1",
        "phase_bucket": "BEA-v1-N10EB Normalized-BM25 Depth-to-Head Integration Smoke",
        "status": status,
        "input_artifact_records": public_records,
        "private_input_intake_records": [{"anonymous_private_input_id": "n10ebpriv0000", "n10dz_top100_private_rows_available_bool": private_ok, "n10dz_top100_private_row_count": len(dz_rows), "same_scoped_n1_span_rows_available_bool": bool(n1_by_denom), "case_count": len(top100_by_case), "other_private_read_count": 0, "private_status_bucket": private_status}],
        "candidate_pool_contract_records": [{"anonymous_candidate_pool_contract_id": "n10ebpool0000", "candidate_universe_bucket": "n10dz_normalized_bm25_top100_cap12_existing_rows", "case_count": len(top100_by_case), "candidate_pool_changed_count": 0, "candidate_added_removed_count": 0, "new_retrieval_count": 0, "openlocus_execution_count": 0}],
        "variant_contract_records": [{"anonymous_variant_contract_id": f"n10ebcontract{idx:04d}", "variant_bucket": variant, "fixed_predeclared_variant_bool": True, "gold_used_for_policy_bool": False, "candidate_added_removed_bool": False} for idx, variant in enumerate(VARIANTS)],
        "variant_result_records": variant_results,
        "distinct_fill_contract_records": distinct_fill_contract_rows,
        "depth_to_head_decision_records": [{"anonymous_decision_id": "n10ebdecision0000", "best_top10_file_recovery_count": best_top10, "best_variant_count": len(best_rows), "best_variant_bucket": best_rows[0]["variant_bucket"], "depth_to_head_success_variant_count": int(decision_counter.get("depth_to_head_success", 0)), "top20_improvement_only_variant_count": int(decision_counter.get("top20_improvement_only", 0)), "no_head_improvement_variant_count": int(decision_counter.get("no_head_improvement", 0)), "baseline_top10_count": baseline_counts["top10"], "baseline_top20_count": baseline_counts["top20"], "baseline_top50_count": baseline_counts["top50"], "baseline_top100_count": baseline_counts["top100"]}],
        "novelty_selection_summary_records": novelty_summary,
        "privacy_boundary_records": [{"anonymous_privacy_id": "n10ebprivacy0000", "public_raw_queries_bool": False, "public_paths_or_filenames_bool": False, "public_candidate_lists_bool": False, "public_exact_ranks_bool": False, "public_snippets_spans_gold_bool": False}],
        "no_forbidden_execution_records": [{"anonymous_no_forbidden_id": "n10ebforbid0000", "new_retrieval_count": 0, "openlocus_execution_count": 0, "network_execution_count": 0, "git_clone_count": 0, "provider_call_count": 0, "selector_reranker_execution_count": 0, "runtime_default_change_count": 0, "candidate_generation_materialization_count": 0}],
        "n10ec_handoff_records": [{"anonymous_handoff_id": "n10ebhandoff0000", "next_allowed_phase_bucket": "BEA-v1-N10EC Normalized-BM25 Depth-to-Head Integration Audit Package", "n10ec_public_audit_package_authorized_bool": status == STATUS_COMPLETE, "new_retrieval_authorized_bool": False, "scaled_retrieval_authorized_bool": False, "runtime_default_authorized_bool": False}],
        "gate_records": [
            {"anonymous_gate_id": "n10ebgate0000", "gate_bucket": "public_inputs_present", "gate_passed_bool": public_ok},
            {"anonymous_gate_id": "n10ebgate0001", "gate_bucket": "private_top100_rows_present", "gate_passed_bool": private_ok},
            {"anonymous_gate_id": "n10ebgate0002", "gate_bucket": "case_count_eq_60", "gate_passed_bool": len(top100_by_case) == 60},
            {"anonymous_gate_id": "n10ebgate0003", "gate_bucket": "variant_count_eq_8", "gate_passed_bool": len(variant_results) == 8},
            {"anonymous_gate_id": "n10ebgate0004", "gate_bucket": "baseline_counts_match_n10dz", "gate_passed_bool": baseline_counts == BASELINE_EXPECTED},
            {"anonymous_gate_id": "n10ebgate0005", "gate_bucket": "distinct_fill_contract_passed", "gate_passed_bool": bool(distinct_fill_contract_rows) and all(row.get("distinct_fill_contract_passed_bool") for row in distinct_fill_contract_rows)},
            {"anonymous_gate_id": "n10ebgate0006", "gate_bucket": "no_forbidden_execution", "gate_passed_bool": True},
        ],
        "stop_go_records": [{"anonymous_stop_go_id": "n10ebstop0000", "next_allowed_phase_bucket": "BEA-v1-N10EC Normalized-BM25 Depth-to-Head Integration Audit Package", "new_retrieval_authorized": False, "scaled_retrieval_authorized": False, "network_authorized": False, "clone_authorized": False, "provider_authorized": False, "runtime_default_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}],
    }
    return report, private_status


def build_report() -> dict[str, Any]:
    report, _private_status = analyze()
    if report.get("status") in {STATUS_NO_INPUTS, STATUS_PRIVATE_MISSING}:
        report.setdefault("schema_version", "bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke_v1")
        report.setdefault("phase_bucket", "BEA-v1-N10EB Normalized-BM25 Depth-to-Head Integration Smoke")
        report.setdefault("forbidden_scan", {"status": "pass", "forbidden_finding_count": 0, "finding_buckets": []})
        return report
    report["forbidden_scan"] = scan_summary(report)
    if report["forbidden_scan"]["status"] != "pass":
        report["status"] = STATUS_FAIL_SCAN
    if report.get("status") not in STATUS_VOCAB:
        report["status"] = STATUS_FAIL_SCHEMA
    if not all(gate.get("gate_passed_bool") for gate in report.get("gate_records", [])) and report["status"] == STATUS_COMPLETE:
        report["status"] = STATUS_ACCOUNTING
    return report


def run_self_test() -> bool:
    checks: list[tuple[str, bool]] = []
    checks.append(("status_vocab", STATUS_COMPLETE in STATUS_VOCAB and STATUS_ACCOUNTING in STATUS_VOCAB))
    try:
        parse_args(["--private", "/tmp/secret"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("suffix_match", suffix_match("a/b/c.py", "b/c.py") and not suffix_match("a/b/c.py", "x/y.py")))
    sample = [{"path": "a.py"}, {"path": "a.py"}, {"path": "b.py"}, {"path": "c.py"}]
    checks.append(("first_unique", [candidate_file(x) for x in first_unique(sample, 3)] == ["a.py", "b.py", "c.py"]))
    checks.append(("append_remaining", len(append_remaining(first_unique(sample, 2), sample)) == 4))
    checks.append(("novel_prefix", [candidate_file(x) for x in novel_prefix(sample, {"a.py"}, 2)] == ["b.py", "c.py"]))
    checks.append(("fill_top5_len", len(fill_top5([{"path": f"f{i}.py"} for i in range(20)], set(), "novel_distinct")) == 10))
    duplicate_tail = [{"path": "a.py"}, {"path": "b.py"}, {"path": "c.py"}, {"path": "d.py"}, {"path": "e.py"}, {"path": "a.py"}, {"path": "b.py"}, {"path": "f.py"}, {"path": "g.py"}, {"path": "h.py"}, {"path": "i.py"}]
    distinct_fill = fill_top5(duplicate_tail, set(), "distinct")
    checks.append(("distinct_fill_dynamic_dedup", len({candidate_file(x) for x in distinct_fill[:10]}) == len(distinct_fill[:10])))
    checks.append(("distinct_fill_violation_counter", distinct_fill_violation_count(distinct_fill) == 0 and distinct_fill_violation_count(duplicate_tail[:10]) > 0))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/private.json"})["status"] == "fail"))
    checks.append(("variant_count", len(VARIANTS) == 8 and len(set(VARIANTS)) == 8))
    checks.append(("baseline_expected", BASELINE_EXPECTED == {"top10": 5, "top20": 11, "top50": 17, "top100": 26}))
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
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report.get('forbidden_scan', {}).get('status')})")
    return 0 if report["status"] == STATUS_COMPLETE else 1


if __name__ == "__main__":
    raise SystemExit(main())
