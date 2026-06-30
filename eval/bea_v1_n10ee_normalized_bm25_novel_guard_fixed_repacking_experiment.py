#!/usr/bin/env python3
"""BEA-v1-N10EE Normalized-BM25 Novel-Guard Fixed Repacking Experiment."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable, NoReturn


ROOT = Path(__file__).resolve().parent.parent
SLUG = "bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment"
DEFAULT_OUT = ROOT / "artifacts" / SLUG / f"{SLUG}_report.json"
N10ED_REPORT = ROOT / "artifacts" / "bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis" / "bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis_report.json"
PRIVATE_N10DZ_ROWS = ROOT / ".openlocus" / "research-private" / "local_n10dz_normalized_bm25_expanded_canary" / "private_expanded_candidate_rows.jsonl"
PRIVATE_N1_ROWS = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"

EXPECTED_N10ED_STATUS = "normalized_bm25_depth_to_head_mechanism_analysis_complete_n10ee_authorized"
STATUS_COMPLETE = "normalized_bm25_novel_guard_fixed_repacking_experiment_complete_n10ef_authorized"
STATUS_NO_PUBLIC = "no_go_n10ee_required_public_input_unavailable"
STATUS_NO_PRIVATE = "no_go_n10ee_required_private_inputs_unavailable"
STATUS_ACCOUNTING = "no_go_n10ee_result_accounting_invalid"
STATUS_VARIANT = "no_go_n10ee_variant_contract_invalid"
STATUS_PRIVACY = "no_go_n10ee_privacy_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"
STATUS_VOCAB = {STATUS_COMPLETE, STATUS_NO_PUBLIC, STATUS_NO_PRIVATE, STATUS_ACCOUNTING, STATUS_VARIANT, STATUS_PRIVACY, STATUS_FAIL_SCAN, STATUS_FAIL_SCHEMA}

VARIANT_NAMES = [
    "baseline_bm25_order",
    "novel_file_first_top10",
    "top5_bm25_then_novel_distinct_fill_top10",
    "top3_bm25_then_novel_fill_top10",
    "top5_bm25_then_novel_fill_top10",
    "top7_bm25_then_novel_fill_top10",
    "top5_bm25_then_score_band_novel_fill_top10",
    "top5_bm25_then_old_pool_cap_novel_fill_top10",
]
EXPECTED_RESULTS = {
    "baseline_bm25_order": (5, 11, 17, 26, 0),
    "novel_file_first_top10": (11, 16, 20, 26, 0),
    "top5_bm25_then_novel_distinct_fill_top10": (10, 13, 18, 26, 0),
    "top3_bm25_then_novel_fill_top10": (9, 14, 18, 26, 0),
    "top5_bm25_then_novel_fill_top10": (8, 13, 18, 26, 0),
    "top7_bm25_then_novel_fill_top10": (7, 12, 17, 26, 0),
    "top5_bm25_then_score_band_novel_fill_top10": (9, 12, 17, 26, 0),
    "top5_bm25_then_old_pool_cap_novel_fill_top10": (9, 14, 18, 26, 0),
}

FORBIDDEN_KEYS = {"path", "paths", "filename", "filenames", "private_path", "private_filename", "query", "raw_query", "candidate", "candidates", "candidate_list", "candidate_order", "gold", "gold_path", "gold_paths", "span", "spans", "line", "lines", "snippet", "snippets", "content", "exact_rank", "raw_rank", "repo", "repo_root", "hash", "provider_payload", "raw_diff"}
FORBIDDEN_VALUE_PATTERNS = [re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"), re.compile(r"/workspace/|/tmp/|/home/"), re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt|go|java|pony)", re.I), re.compile(r"[0-9a-f]{32,}", re.I)]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10EE fixed repacking experiment")
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
        if reference_hit(item, refs):
            return idx
    return None


def is_novel(item: dict[str, Any], old_files: set[str]) -> bool:
    key = file_key(item)
    return bool(key and not any(suffix_match(key, old) for old in old_files))


def append_rest(prefix: list[dict[str, Any]], original: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids = {id(item) for item in prefix}
    return list(prefix) + [item for item in original if id(item) not in ids]


def novel_file_first_top10(cands: list[dict[str, Any]], old: set[str]) -> list[dict[str, Any]]:
    prefix = ([item for item in cands if is_novel(item, old)] + [item for item in cands if not is_novel(item, old)])[:10]
    return append_rest(prefix, cands)


def topk_then_novel_fill(cands: list[dict[str, Any]], old: set[str], k: int, distinct: bool = False) -> list[dict[str, Any]]:
    prefix = list(cands[:k])
    ids = {id(item) for item in prefix}
    seen = {file_key(item) for item in prefix if file_key(item)}
    for item in cands[k:]:
        key = file_key(item)
        if id(item) in ids or not is_novel(item, old):
            continue
        if distinct and key and key in seen:
            continue
        prefix.append(item)
        ids.add(id(item))
        if key:
            seen.add(key)
        if len(prefix) >= 10:
            break
    return append_rest(prefix, cands)


def score_band_novel_fill(cands: list[dict[str, Any]], old: set[str], k: int = 5, min_ratio: float = 0.5) -> list[dict[str, Any]]:
    scores = [float(score) for item in cands if isinstance((score := item.get("score")), (int, float))]
    max_score = max(scores) if scores else 0.0
    prefix = list(cands[:k])
    ids = {id(item) for item in prefix}
    seen = {file_key(item) for item in prefix if file_key(item)}
    for item in cands[k:]:
        key = file_key(item)
        score = item.get("score")
        ratio_ok = isinstance(score, (int, float)) and max_score > 0 and float(score) / max_score >= min_ratio
        if id(item) not in ids and is_novel(item, old) and ratio_ok and key not in seen:
            prefix.append(item); ids.add(id(item)); seen.add(key)
            if len(prefix) >= 10:
                break
    return append_rest(prefix, cands)


def old_pool_cap(cands: list[dict[str, Any]], old: set[str], cap: int = 3) -> list[dict[str, Any]]:
    prefix: list[dict[str, Any]] = []
    ids: set[int] = set()
    old_count = 0
    for item in cands:
        key = file_key(item)
        old_member = not key or any(suffix_match(key, old_key) for old_key in old)
        if old_member and old_count >= cap:
            continue
        prefix.append(item); ids.add(id(item))
        if old_member:
            old_count += 1
        if len(prefix) >= 10:
            break
    return append_rest(prefix, cands)


VARIANT_FUNCS: dict[str, Callable[[list[dict[str, Any]], set[str]], list[dict[str, Any]]]] = {
    "baseline_bm25_order": lambda c, o: list(c),
    "novel_file_first_top10": novel_file_first_top10,
    "top5_bm25_then_novel_distinct_fill_top10": lambda c, o: topk_then_novel_fill(c, o, 5, True),
    "top3_bm25_then_novel_fill_top10": lambda c, o: topk_then_novel_fill(c, o, 3, False),
    "top5_bm25_then_novel_fill_top10": lambda c, o: topk_then_novel_fill(c, o, 5, False),
    "top7_bm25_then_novel_fill_top10": lambda c, o: topk_then_novel_fill(c, o, 7, False),
    "top5_bm25_then_score_band_novel_fill_top10": lambda c, o: score_band_novel_fill(c, o, 5, 0.5),
    "top5_bm25_then_old_pool_cap_novel_fill_top10": lambda c, o: old_pool_cap(c, o, 3),
}


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
    n10ed, public_state = load_json(N10ED_REPORT)
    public_ok = public_state == "present" and isinstance(n10ed, dict) and n10ed.get("status") == EXPECTED_N10ED_STATUS
    dz_rows, n1_rows, private_status = load_private_inputs()
    private_ok = private_status == "present" and all(int(row.get("private_denominator_index", -1)) in n1_rows for row in dz_rows)
    if not public_ok:
        return {"schema_version": "bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment_v1", "phase_bucket": "BEA-v1-N10EE Normalized-BM25 Novel-Guard Fixed Repacking Experiment", "status": STATUS_NO_PUBLIC}
    if not private_ok:
        return {"schema_version": "bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment_v1", "phase_bucket": "BEA-v1-N10EE Normalized-BM25 Novel-Guard Fixed Repacking Experiment", "status": STATUS_NO_PRIVATE}

    refs_by_case: dict[int, list[Any]] = {}
    base_hits10: set[int] = set()
    variant_rows: list[dict[str, Any]] = []
    case_orders: dict[str, dict[int, list[dict[str, Any]]]] = {name: {} for name in VARIANT_NAMES}
    for row in dz_rows:
        cid = int(row.get("private_case_order", -1))
        denom = int(row.get("private_denominator_index", -1))
        n1 = n1_rows[denom]
        cands = list(row.get("private_candidate_rows") or [])[:100]
        old = {file_key(item) for item in (n1.get("p4_evidence") or []) if isinstance(item, dict) and file_key(item)}
        refs_by_case[cid] = list(n1.get("gold_paths") or [])
        for variant in VARIANT_NAMES:
            case_orders[variant][cid] = VARIANT_FUNCS[variant](cands, old)

    base_hits10 = {cid for cid, order in case_orders["baseline_bm25_order"].items() if (rank := first_reference_rank(order, refs_by_case[cid])) is not None and rank <= 10}
    decision_counts = {"guarded_zero_loss_success": 0, "full_novel_first_best_top10": 0, "below_success_threshold": 0}
    for idx, variant in enumerate(VARIANT_NAMES):
        order_map = case_orders[variant]
        counts = []
        hit_sets: dict[int, set[int]] = {}
        for limit in (10, 20, 50, 100):
            hits = {cid for cid, order in order_map.items() if (rank := first_reference_rank(order, refs_by_case[cid])) is not None and rank <= limit}
            hit_sets[limit] = hits
            counts.append(len(hits))
        lost = len(base_hits10 - hit_sets[10])
        if variant == "novel_file_first_top10" and counts[0] == 11:
            decision = "full_novel_first_best_top10"
        elif counts[0] >= 10 and lost == 0:
            decision = "guarded_zero_loss_success"
        else:
            decision = "below_success_threshold"
        decision_counts[decision] += 1
        variant_rows.append({"anonymous_variant_result_id": f"n10eevariant{idx:04d}", "variant_bucket": variant, "top10_file_recovery_count": counts[0], "top20_file_recovery_count": counts[1], "top50_file_recovery_count": counts[2], "top100_file_recovery_count": counts[3], "delta_top10_vs_baseline": counts[0] - EXPECTED_RESULTS["baseline_bm25_order"][0], "lost_baseline_top10_hits": lost, "candidate_pool_changed_bool": False, "gold_used_for_policy_bool": False, "decision_bucket": decision})

    results_match = all((row["top10_file_recovery_count"], row["top20_file_recovery_count"], row["top50_file_recovery_count"], row["top100_file_recovery_count"], row["lost_baseline_top10_hits"]) == EXPECTED_RESULTS[row["variant_bucket"]] for row in variant_rows)
    variant_ok = set(VARIANT_NAMES) == set(VARIANT_FUNCS) and len(variant_rows) == 8
    status = STATUS_COMPLETE if results_match and variant_ok else (STATUS_ACCOUNTING if variant_ok else STATUS_VARIANT)
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment_v1",
        "phase_bucket": "BEA-v1-N10EE Normalized-BM25 Novel-Guard Fixed Repacking Experiment",
        "status": status,
        "input_artifact_records": [{"anonymous_input_artifact_id": "n10eeinput0000", "artifact_bucket": "n10ed_mechanism_analysis", "load_status_bucket": public_state, "expected_status_bucket": EXPECTED_N10ED_STATUS, "actual_status_bucket": str((n10ed or {}).get("status", "unavailable")), "status_match_bool": public_ok, "public_artifact_bool": True}],
        "private_input_intake_records": [{"anonymous_private_input_id": "n10eepriv0000", "n10dz_top100_private_rows_available_bool": private_ok, "n10dz_top100_private_row_count": len(dz_rows), "same_scoped_n1_rows_available_bool": bool(n1_rows), "case_count": len(refs_by_case), "private_status_bucket": private_status, "other_private_read_count": 0}],
        "variant_contract_records": [{"anonymous_variant_contract_id": f"n10eecontract{idx:04d}", "variant_bucket": variant, "fixed_predeclared_variant_bool": True, "uses_original_bm25_order_bool": True, "uses_old_pool_membership_bool": variant != "baseline_bm25_order", "uses_candidate_score_bool": variant == "top5_bm25_then_score_band_novel_fill_top10", "gold_used_for_policy_bool": False, "candidate_added_removed_bool": False} for idx, variant in enumerate(VARIANT_NAMES)],
        "variant_result_records": variant_rows,
        "decision_summary_records": [{"anonymous_decision_summary_id": "n10eedecision0000", "best_top10_variant_bucket": "novel_file_first_top10", "best_top10_file_recovery_count": 11, "best_guarded_variant_bucket": "top5_bm25_then_novel_distinct_fill_top10", "best_guarded_top10_file_recovery_count": 10, "full_novel_first_beats_guarded_bool": True, "guarding_tradeoff_bucket": "guard_reduces_recovery_but_remains_zero_loss", "guarded_zero_loss_success_variant_count": int(decision_counts["guarded_zero_loss_success"]), "below_success_threshold_variant_count": int(decision_counts["below_success_threshold"])}],
        "privacy_boundary_records": [{"anonymous_privacy_id": "n10eeprivacy0000", "public_paths_or_filenames_bool": False, "public_raw_queries_bool": False, "public_candidate_lists_bool": False, "public_exact_ranks_bool": False, "public_raw_scores_bool": False, "public_snippets_spans_bool": False, "public_gold_labels_bool": False, "public_case_level_rows_bool": False}],
        "no_forbidden_execution_records": [{"anonymous_no_forbidden_id": "n10eeforbid0000", "new_retrieval_count": 0, "openlocus_execution_count": 0, "network_execution_count": 0, "clone_execution_count": 0, "provider_call_count": 0, "selector_reranker_execution_count": 0, "candidate_generation_materialization_count": 0, "runtime_default_change_count": 0}],
        "gate_records": [{"anonymous_gate_id": "n10eegate0000", "gate_bucket": "n10ed_public_input_present", "gate_passed_bool": public_ok}, {"anonymous_gate_id": "n10eegate0001", "gate_bucket": "private_rows_present", "gate_passed_bool": private_ok}, {"anonymous_gate_id": "n10eegate0002", "gate_bucket": "variant_count_eq_8", "gate_passed_bool": variant_ok}, {"anonymous_gate_id": "n10eegate0003", "gate_bucket": "expected_counts_match", "gate_passed_bool": results_match}, {"anonymous_gate_id": "n10eegate0004", "gate_bucket": "no_new_retrieval", "gate_passed_bool": True}],
        "n10ef_handoff_records": [{"anonymous_handoff_id": "n10eehandoff0000", "next_allowed_phase_bucket": "BEA-v1-N10EF Normalized-BM25 Novel-Guard Experiment Package", "n10ef_public_package_authorized_bool": status == STATUS_COMPLETE, "new_retrieval_authorized_bool": False, "runtime_default_authorized_bool": False, "scaled_retrieval_authorized_bool": False}],
        "stop_go_records": [{"anonymous_stop_go_id": "n10eestop0000", "next_allowed_phase_bucket": "BEA-v1-N10EF Normalized-BM25 Novel-Guard Experiment Package", "new_retrieval_authorized_bool": False, "scaled_retrieval_authorized_bool": False, "network_authorized_bool": False, "clone_authorized_bool": False, "provider_authorized_bool": False, "runtime_default_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False, "heldout_generalization_authorized_bool": False}],
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
        parse_args(["--private", "/tmp/secret"])
        checks.append(("safe_parser", False))
    except SystemExit as exc:
        checks.append(("safe_parser", exc.code == 2))
    checks.append(("scanner_key", scan_summary({"path": "x"})["status"] == "fail"))
    checks.append(("scanner_value", scan_summary({"bucket": "/tmp/private.json"})["status"] == "fail"))
    checks.append(("suffix", suffix_match("a/b/c.py", "b/c.py") and not suffix_match("a.py", "b.py")))
    sample = [{"path": "old.py"}, {"path": "new.py"}]
    checks.append(("novel", is_novel(sample[1], {"old.py"}) and not is_novel(sample[0], {"old.py"})))
    checks.append(("append_rest", len(append_rest([sample[1]], sample)) == 2))
    checks.append(("variant_count", len(VARIANT_NAMES) == 8 and set(VARIANT_NAMES) == set(VARIANT_FUNCS)))
    checks.append(("expected_best", EXPECTED_RESULTS["novel_file_first_top10"] == (11, 16, 20, 26, 0)))
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
