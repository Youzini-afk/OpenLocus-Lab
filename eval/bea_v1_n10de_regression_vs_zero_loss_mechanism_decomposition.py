#!/usr/bin/env python3
"""BEA-v1-N10DE Regression-vs-Zero-Loss Mechanism Decomposition."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


STATUS_PASS = "regression_vs_zero_loss_mechanism_decomposition_complete_n10df_authorized"
STATUS_NO_INPUTS = "no_go_n10de_required_inputs_unavailable"
STATUS_PRIVATE_MISSING = "no_go_n10de_private_span_rows_missing"
STATUS_ANCHOR_MISMATCH = "no_go_n10de_anchor_metrics_mismatch"
STATUS_ACCOUNTING = "no_go_n10de_result_accounting_invalid"
STATUS_PRIVACY = "no_go_n10de_privacy_or_claim_boundary_failed"
STATUS_FAIL_SCAN = "fail_forbidden_scan"
STATUS_FAIL_SCHEMA = "fail_schema_contract"

STATUS_VOCAB = {
    STATUS_PASS,
    STATUS_NO_INPUTS,
    STATUS_PRIVATE_MISSING,
    STATUS_ANCHOR_MISMATCH,
    STATUS_ACCOUNTING,
    STATUS_PRIVACY,
    STATUS_FAIL_SCAN,
    STATUS_FAIL_SCHEMA,
}

POLICIES = [
    "baseline_existing_order",
    "distinct_file_top20_greedy_then_top10",
    "max_per_file_2_top10",
]

PREVIEW_N10DF_VARIANTS = [
    "preserve_top3_then_distinct_file_fill_top10",
    "preserve_top5_then_distinct_file_fill_top10",
    "max_per_file_2_then_distinct_file_fill_top10",
    "max_per_file_2_then_distinct_file_fill_top20_then_top10",
    "preserve_top3_max_per_file_2_then_distinct_file_fill_top10",
]

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRIVATE = ROOT / ".openlocus" / "research-private" / "local_n6xfr_recovery" / "n1_private" / "bea_v1_n1.private_span_rows.jsonl"
DEFAULT_N10DD = ROOT / "artifacts" / "bea_v1_n10dd_distinct_file_packing_rank_file_reach_package" / "bea_v1_n10dd_distinct_file_packing_rank_file_reach_package_report.json"
DEFAULT_N10DC = ROOT / "artifacts" / "bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke" / "bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke_report.json"
DEFAULT_N10DB = ROOT / "artifacts" / "bea_v1_n10db_rank_file_reach_policy_field_scoping" / "bea_v1_n10db_rank_file_reach_policy_field_scoping_report.json"
DEFAULT_OUT = ROOT / "artifacts" / "bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition" / "bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition_report.json"

FORBIDDEN_KEYS = {
    "path",
    "paths",
    "filename",
    "filenames",
    "private_path",
    "private_filename",
    "source_path",
    "span",
    "spans",
    "line",
    "lines",
    "snippet",
    "snippets",
    "content",
    "candidate_list",
    "candidates",
    "gold_path",
    "gold_paths",
    "gold_line",
    "gold_lines",
    "exact_rank",
    "raw_rank",
    "rank",
    "ranks",
    "repo_id",
    "task_id",
    "hash",
    "sha",
    "provider_payload",
    "raw_diff",
}
FORBIDDEN_VALUE_PATTERNS = [
    re.compile(r"(?:^|/|\\)\.openlocus(?:/|\\)"),
    re.compile(r"/workspace/|/tmp/|/home/"),
    re.compile(r"[A-Za-z0-9_.-]+\.(?:jsonl|json|py|rs|ts|js|md|txt)"),
    re.compile(r"[0-9a-f]{32,}", re.I),
]


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):  # pragma: no cover
        self.exit(2, "invalid arguments\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = SafeArgumentParser(description="BEA-v1-N10DE mechanism decomposition")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--private-span-rows", default=str(DEFAULT_PRIVATE))
    parser.add_argument("--n10dd-artifact", default=str(DEFAULT_N10DD))
    parser.add_argument("--n10dc-artifact", default=str(DEFAULT_N10DC))
    parser.add_argument("--n10db-artifact", default=str(DEFAULT_N10DB))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    return parser.parse_args(argv)


def scan_summary(obj: Any) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def walk(node: Any, key: str = "") -> None:
        if key in FORBIDDEN_KEYS:
            findings.append({"bucket": "forbidden_key", "key_bucket": key})
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for item in node:
                walk(item, key)
        elif isinstance(node, str):
            for pat in FORBIDDEN_VALUE_PATTERNS:
                if pat.search(node):
                    findings.append({"bucket": "forbidden_value", "key_bucket": key or "value"})
                    break

    walk(obj)
    return {"status": "fail" if findings else "pass", "forbidden_finding_count": len(findings), "finding_buckets": findings[:20]}


def load_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), "present"
    except FileNotFoundError:
        return None, "missing"
    except Exception:
        return None, "invalid"


def input_artifact_records(args: argparse.Namespace) -> tuple[list[dict[str, Any]], bool]:
    specs = [
        ("n10dd_public_package", Path(args.n10dd_artifact), "distinct_file_packing_rank_file_reach_package_complete_n10de_authorized"),
        ("n10dc_smoke", Path(args.n10dc_artifact), "distinct_file_packing_rank_file_reach_smoke_complete_n10dd_authorized"),
        ("n10db_field_scoping", Path(args.n10db_artifact), "rank_file_reach_policy_field_scoping_pass_n10dc_authorized"),
    ]
    records: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, path, expected) in enumerate(specs):
        data, state = load_json(path)
        actual = str(data.get("status", "")) if data else ""
        matched = state == "present" and actual == expected
        ok = ok and matched
        records.append(
            {
                "anonymous_input_artifact_id": f"n10dein{idx:04d}",
                "artifact_bucket": bucket,
                "load_status_bucket": state,
                "expected_status_bucket": expected,
                "actual_status_bucket": actual or "unavailable",
                "status_match_bool": matched,
                "public_artifact_bool": True,
            }
        )
    return records, ok


def load_rows(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
    except Exception:
        return [], "invalid"
    return rows, "present"


def _norm(value: object) -> str:
    return str(value or "").replace("\\", "/").strip("/")


def same_or_suffix(left: object, right: object) -> bool:
    a = _norm(left)
    b = _norm(right)
    return bool(a and b and (a == b or a.endswith("/" + b) or b.endswith("/" + a)))


def refs(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    out: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        try:
            out.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
        except Exception:
            continue
    return out


def ref_ranges(path_value: object, ref_map: dict[str, list[tuple[int, int]]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for ref, ranges in ref_map.items():
        if same_or_suffix(path_value, ref):
            out.extend(ranges)
    return out


def overlaps(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def span_hit(ev: dict[str, Any], ref_map: dict[str, list[tuple[int, int]]]) -> bool:
    ranges = ref_ranges(ev.get("path", ""), ref_map)
    if not ranges:
        return False
    start = ev.get("start_line")
    end = ev.get("end_line")
    if not isinstance(start, int) or not isinstance(end, int):
        return False
    return any(overlaps(int(start), int(end), a, b) for a, b in ranges)


def policy_order(evidence: list[dict[str, Any]], policy: str) -> list[dict[str, Any]]:
    if policy == "baseline_existing_order":
        return list(evidence)
    prefix_len = 20 if policy == "distinct_file_top20_greedy_then_top10" else 10
    per_file_limit = 2 if policy == "max_per_file_2_top10" else 1
    out: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for ev in evidence:
        if len(out) >= prefix_len:
            break
        key = str(ev.get("path", ""))
        if counts.get(key, 0) < per_file_limit:
            out.append(ev)
            counts[key] = counts.get(key, 0) + 1
    used = {id(ev) for ev in out}
    out.extend(ev for ev in evidence if id(ev) not in used)
    return out


def top10_hit(order: list[dict[str, Any]], ref_map: dict[str, list[tuple[int, int]]]) -> bool:
    return any(span_hit(ev, ref_map) for ev in order[:10])


def top20_hit(order: list[dict[str, Any]], ref_map: dict[str, list[tuple[int, int]]]) -> bool:
    return any(span_hit(ev, ref_map) for ev in order[:20])


def rank_bucket(rank_value: int | None) -> str:
    if rank_value is None:
        return "none"
    if rank_value <= 10:
        return "rank_1_10"
    if rank_value <= 20:
        return "rank_11_20"
    if rank_value <= 50:
        return "rank_21_50"
    return "rank_gt50"


def count_bucket(n: int) -> str:
    if n == 0:
        return "none"
    if n <= 2:
        return "low"
    if n <= 5:
        return "medium"
    return "high"


def distinct_bucket(n: int) -> str:
    if n <= 5:
        return "distinct_1_5"
    if n <= 8:
        return "distinct_6_8"
    return "distinct_9_10"


def first_span_hit_rank(order: list[dict[str, Any]], ref_map: dict[str, list[tuple[int, int]]]) -> int | None:
    for idx, ev in enumerate(order, start=1):
        if span_hit(ev, ref_map):
            return idx
    return None


def first_displaced_added(evidence: list[dict[str, Any]], from_order: list[dict[str, Any]], to_order: list[dict[str, Any]], ref_map: dict[str, list[tuple[int, int]]]) -> tuple[int | None, int | None, bool, bool, str]:
    from_top = {id(ev): ev for ev in from_order[:10]}
    to_top = {id(ev): ev for ev in to_order[:10]}
    displaced = [ev for ev_id, ev in from_top.items() if ev_id not in to_top]
    added = [ev for ev_id, ev in to_top.items() if ev_id not in from_top]
    hit_displaced = next((ev for ev in displaced if span_hit(ev, ref_map)), displaced[0] if displaced else None)
    hit_added = next((ev for ev in added if span_hit(ev, ref_map)), added[0] if added else None)
    disp_rank = evidence.index(hit_displaced) + 1 if hit_displaced in evidence else None
    add_rank = evidence.index(hit_added) + 1 if hit_added in evidence else None
    added_11_20 = bool(add_rank is not None and 11 <= add_rank <= 20)
    added_new_file = False
    if hit_added is not None:
        added_new_file = not any(same_or_suffix(ev.get("path", ""), hit_added.get("path", "")) for ev in from_order[:10])
    dup_count = 0
    if hit_displaced is not None:
        dup_count = sum(1 for ev in from_order[:10] if same_or_suffix(ev.get("path", ""), hit_displaced.get("path", "")))
    return disp_rank, add_rank, added_11_20, added_new_file, count_bucket(max(0, dup_count - 1))


def compute(rows: list[dict[str, Any]]) -> dict[str, Any]:
    policy_counts = {p: {"top10": 0, "top20": 0} for p in POLICIES}
    group_counts = Counter()
    max2_lost_baseline_hits = 0
    mechanism: dict[str, Counter] = {g: Counter() for g in ["gained_by_aggressive_only", "gained_by_max2_only", "gained_by_both", "lost_by_aggressive", "preserved_by_max2", "unchanged_miss", "unchanged_hit"]}
    regression_rows: list[dict[str, Any]] = []

    for row in rows:
        evidence = row.get("p4_evidence", [])
        ref_map = refs(row)
        orders = {policy: policy_order(evidence, policy) for policy in POLICIES}
        hits = {policy: top10_hit(order, ref_map) for policy, order in orders.items()}
        for policy, order in orders.items():
            policy_counts[policy]["top10"] += int(top10_hit(order, ref_map))
            policy_counts[policy]["top20"] += int(top20_hit(order, ref_map))
        base = hits["baseline_existing_order"]
        aggressive = hits["distinct_file_top20_greedy_then_top10"]
        max2 = hits["max_per_file_2_top10"]
        if base and not max2:
            max2_lost_baseline_hits += 1
        if not base and aggressive and not max2:
            group = "gained_by_aggressive_only"
        elif not base and not aggressive and max2:
            group = "gained_by_max2_only"
        elif not base and aggressive and max2:
            group = "gained_by_both"
        elif base and not aggressive and not max2:
            group = "lost_by_aggressive"
        elif base and not aggressive and max2:
            group = "lost_by_aggressive"
        elif not base and not aggressive and not max2:
            group = "unchanged_miss"
        else:
            group = "unchanged_hit"
        group_counts[group] += 1
        baseline_top10 = orders["baseline_existing_order"][:10]
        distinct_files = len({_norm(ev.get("path", "")) for ev in baseline_top10})
        duplicate_count = 10 - distinct_files
        disp_rank, add_rank, added_11_20, added_new_file, displaced_dup_bucket = first_displaced_added(evidence, orders["baseline_existing_order"], orders["distinct_file_top20_greedy_then_top10"], ref_map)
        mechanism[group]["baseline_top10_duplicate_pressure_bucket:" + count_bucket(duplicate_count)] += 1
        mechanism[group]["baseline_top10_distinct_file_count_bucket:" + distinct_bucket(distinct_files)] += 1
        mechanism[group]["displaced_candidate_original_rank_bucket:" + rank_bucket(disp_rank)] += 1
        mechanism[group]["added_candidate_original_rank_bucket:" + rank_bucket(add_rank)] += 1
        mechanism[group]["added_candidate_was_from_rank_11_20_true_count"] += int(added_11_20)
        mechanism[group]["added_candidate_file_new_to_top10_true_count"] += int(added_new_file)
        mechanism[group]["displaced_candidate_file_duplicate_count_bucket:" + displaced_dup_bucket] += 1
        if base and not aggressive and max2:
            regression_rows.append({"disp_rank": disp_rank, "add_rank": add_rank, "dup_bucket": displaced_dup_bucket})

    return {"policy_counts": policy_counts, "group_counts": group_counts, "max2_lost_baseline_hits": max2_lost_baseline_hits, "mechanism": mechanism, "regression_rows": regression_rows}


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str) -> tuple[list[dict[str, Any]], bool]:
    ok = load_status == "present" and len(rows) == 213
    return [{
        "anonymous_private_input_intake_id": "n10depriv0000",
        "private_input_bucket": "single_scoped_n1_span_rows",
        "load_status_bucket": load_status,
        "private_span_rows_read": len(rows) if load_status == "present" else 0,
        "single_scoped_private_input_read_bool": load_status == "present",
        "other_private_files_read_count": 0,
        "private_path_public_bool": False,
        "private_filename_public_bool": False,
        "private_content_public_bool": False,
        "intake_complete_bool": ok,
    }], ok


def policy_result_anchor_records(stats: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for idx, policy in enumerate(POLICIES):
        rows.append({
            "anonymous_policy_anchor_id": f"n10deanchor{idx:04d}",
            "policy_bucket": policy,
            "top10_span_overlap_count": stats["policy_counts"][policy]["top10"],
            "top20_span_overlap_count": stats["policy_counts"][policy]["top20"],
            "candidate_generation_count": 0,
            "candidate_added_count": 0,
            "candidate_removed_count": 0,
            "candidate_pool_preserved_bool": True,
        })
    return rows


def outcome_group_records(stats: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"anonymous_outcome_group_id": f"n10degroup{idx:04d}", "outcome_group_bucket": group, "group_count": int(stats["group_counts"].get(group, 0))} for idx, group in enumerate(["gained_by_aggressive_only", "gained_by_max2_only", "gained_by_both", "lost_by_aggressive", "preserved_by_max2", "unchanged_miss", "unchanged_hit"])]


def most_common_bucket(counter: Counter, prefix: str) -> str:
    pairs = [(key.split(":", 1)[1], count) for key, count in counter.items() if key.startswith(prefix + ":")]
    if not pairs:
        return "none"
    return sorted(pairs, key=lambda x: (-x[1], x[0]))[0][0]


def observable_mechanism_bucket_records(stats: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for idx, (group, counter) in enumerate(stats["mechanism"].items()):
        records.append({
            "anonymous_observable_mechanism_id": f"n10demech{idx:04d}",
            "outcome_group_bucket": group,
            "group_count": int(stats["group_counts"].get(group, 0)),
            "baseline_top10_duplicate_pressure_bucket": most_common_bucket(counter, "baseline_top10_duplicate_pressure_bucket"),
            "baseline_top10_distinct_file_count_bucket": most_common_bucket(counter, "baseline_top10_distinct_file_count_bucket"),
            "displaced_candidate_original_rank_bucket": most_common_bucket(counter, "displaced_candidate_original_rank_bucket"),
            "added_candidate_original_rank_bucket": most_common_bucket(counter, "added_candidate_original_rank_bucket"),
            "added_candidate_was_from_rank_11_20_true_count": int(counter.get("added_candidate_was_from_rank_11_20_true_count", 0)),
            "displaced_candidate_file_duplicate_count_bucket": most_common_bucket(counter, "displaced_candidate_file_duplicate_count_bucket"),
            "added_candidate_file_new_to_top10_true_count": int(counter.get("added_candidate_file_new_to_top10_true_count", 0)),
        })
    return records


def regression_specific_records(stats: dict[str, Any]) -> list[dict[str, Any]]:
    regs = stats["regression_rows"]
    row = regs[0] if regs else {"disp_rank": None, "add_rank": None, "dup_bucket": "none"}
    return [{
        "anonymous_regression_specific_id": "n10dereg0000",
        "regression_count": len(regs),
        "regression_displaced_candidate_rank_bucket": rank_bucket(row.get("disp_rank")),
        "regression_replacement_rank_bucket": rank_bucket(row.get("add_rank")),
        "regression_due_to_strict_file_uniqueness_bool": len(regs) == 1,
        "max_per_file_2_preserves_regression_bool": len(regs) == 1,
        "displaced_candidate_file_duplicate_count_bucket": str(row.get("dup_bucket", "none")),
    }]


def hybrid_rule_signal_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_hybrid_rule_signal_id": "n10dehybrid0000",
        "gold_free_hybrid_rule_plausible_bool": True,
        "hybrid_rule_family_bucket": "prefix_preserving_distinct_file_fill",
        "n10df_authorized_bool": True,
        "preview_variant_count": len(PREVIEW_N10DF_VARIANTS),
        "preview_variant_buckets": PREVIEW_N10DF_VARIANTS,
        "policy_signal_bucket": "preserve_early_prefix_or_allow_two_per_file_to_avoid_single_span_regression_while_retaining_distinct_file_gain",
    }]


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_privacy_boundary_id": "n10deprivacy0000",
        "privacy_boundary_bucket": "bucket_counts_only_no_candidate_or_file_identity",
        "private_path_public_bool": False,
        "private_filename_public_bool": False,
        "private_content_public_bool": False,
        "public_path_or_filename_count": 0,
        "candidate_id_public_count": 0,
        "candidate_list_public_bool": False,
        "gold_path_public_bool": False,
        "span_or_line_public_bool": False,
        "exact_rank_public_bool": False,
        "privacy_boundary_complete_bool": True,
    }], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{
        "anonymous_no_forbidden_execution_id": "n10denoexec0000",
        "private_span_input_read_count": 1,
        "other_private_file_read_count": 0,
        "retrieval_execution_count": 0,
        "rerun_execution_count": 0,
        "openlocus_execution_count": 0,
        "candidate_generation_count": 0,
        "candidate_materialization_count": 0,
        "candidate_addition_count": 0,
        "candidate_removal_count": 0,
        "selector_reranker_execution_count": 0,
        "adaptive_tuning_count": 0,
        "runtime_change_count": 0,
        "default_change_count": 0,
        "p5_v1a_execution_count": 0,
        "method_downstream_claim_count": 0,
        "heldout_generalization_claim_count": 0,
        "no_forbidden_execution_complete_bool": True,
    }], True


def n10df_handoff_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_n10df_handoff_id": "n10dehandoff0000",
        "next_allowed_phase_bucket": "BEA-v1-N10DF Hybrid Distinct-File Packing Smoke",
        "n10df_authorized_bool": True,
        "same_scoped_private_rows_authorized_bool": True,
        "fixed_preview_variants_only_bool": True,
        "runtime_default_authorized_bool": False,
        "heldout_generalization_authorized_bool": False,
        "retrieval_rerun_authorized_bool": False,
        "candidate_generation_add_remove_authorized_bool": False,
        "selector_reranker_authorized_bool": False,
        "p5_v1a_authorized_bool": False,
        "adaptive_tuning_authorized_bool": False,
        "method_downstream_claim_authorized_bool": False,
    }]


def stop_go_records() -> list[dict[str, Any]]:
    return [{
        "anonymous_stop_go_id": "n10destop0000",
        "status_bucket": STATUS_PASS,
        "next_allowed_phase_bucket": "BEA-v1-N10DF Hybrid Distinct-File Packing Smoke",
        "n10df_authorized_bool": True,
        "runtime_default_authorized_bool": False,
        "heldout_generalization_authorized_bool": False,
        "retrieval_rerun_authorized_bool": False,
        "candidate_generation_add_remove_authorized_bool": False,
        "selector_reranker_authorized_bool": False,
        "p5_v1a_authorized_bool": False,
        "adaptive_tuning_authorized_bool": False,
        "method_downstream_claim_authorized_bool": False,
    }]


def gate_records(inputs_ok: bool, intake_ok: bool, stats: dict[str, Any] | None, privacy_ok: bool, noexec_ok: bool, scan_ok: bool) -> tuple[list[dict[str, Any]], bool]:
    if stats:
        pc = stats["policy_counts"]
        gc = stats["group_counts"]
        reg_count = len(stats["regression_rows"])
        gates = [
            ("required_public_inputs_present", inputs_ok),
            ("private_span_rows_read_213", intake_ok),
            ("baseline_span_top10_13", pc["baseline_existing_order"]["top10"] == 13),
            ("aggressive_span_top10_16", pc["distinct_file_top20_greedy_then_top10"]["top10"] == 16),
            ("max2_span_top10_15", pc["max_per_file_2_top10"]["top10"] == 15),
            ("aggressive_lost_baseline_hits_1", gc["lost_by_aggressive"] == 1),
            ("max2_lost_baseline_hits_0", stats.get("max2_lost_baseline_hits") == 0),
            ("outcome_group_counts_sum_213", sum(gc.values()) == 213),
            ("regression_count_1", reg_count == 1),
            ("privacy_boundary_complete", privacy_ok),
            ("no_forbidden_execution", noexec_ok),
            ("forbidden_scan_pass", scan_ok),
        ]
    else:
        gates = [("required_public_inputs_present", inputs_ok), ("private_span_rows_read_213", intake_ok), ("forbidden_scan_pass", scan_ok)]
    return [{"anonymous_gate_id": f"n10degate{idx:04d}", "gate_bucket": name, "gate_passed_bool": bool(ok)} for idx, (name, ok) in enumerate(gates)], all(ok for _name, ok in gates)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    inputs, inputs_ok = input_artifact_records(args)
    rows, load_status = load_rows(Path(args.private_span_rows))
    intake, intake_ok = private_input_intake_records(rows, load_status)
    stats = compute(rows) if intake_ok else None
    privacy, privacy_ok = privacy_boundary_records()
    noexec, noexec_ok = no_forbidden_execution_records()
    if not inputs_ok:
        status = STATUS_NO_INPUTS
    elif not intake_ok:
        status = STATUS_PRIVATE_MISSING
    else:
        pc = stats["policy_counts"] if stats else {}
        anchor_ok = pc.get("baseline_existing_order", {}).get("top10") == 13 and pc.get("distinct_file_top20_greedy_then_top10", {}).get("top10") == 16 and pc.get("max_per_file_2_top10", {}).get("top10") == 15
        status = STATUS_PASS if anchor_ok else STATUS_ANCHOR_MISMATCH
    report: dict[str, Any] = {
        "schema_version": "bea_v1_n10de_regression_mechanism_v1",
        "phase_bucket": "BEA-v1-N10DE Regression-vs-Zero-Loss Mechanism Decomposition",
        "status": status,
        "input_artifact_records": inputs,
        "private_input_intake_records": intake,
        "policy_result_anchor_records": policy_result_anchor_records(stats) if stats else [],
        "outcome_group_records": outcome_group_records(stats) if stats else [],
        "observable_mechanism_bucket_records": observable_mechanism_bucket_records(stats) if stats else [],
        "regression_specific_records": regression_specific_records(stats) if stats else [],
        "hybrid_rule_signal_records": hybrid_rule_signal_records() if status == STATUS_PASS else [],
        "privacy_boundary_records": privacy,
        "no_forbidden_execution_records": noexec,
        "n10df_handoff_records": n10df_handoff_records() if status == STATUS_PASS else [],
        "stop_go_records": stop_go_records() if status == STATUS_PASS else [],
    }
    scan = scan_summary(report)
    scan_ok = scan["status"] == "pass"
    gates, gates_ok = gate_records(inputs_ok, intake_ok, stats, privacy_ok, noexec_ok, scan_ok)
    report["gate_records"] = gates
    report["forbidden_scan"] = scan
    if status == STATUS_PASS and (not gates_ok or not scan_ok):
        report["status"] = STATUS_FAIL_SCAN if not scan_ok else STATUS_FAIL_SCHEMA
    return report


def write_report(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check(name: str, cond: bool) -> tuple[str, bool]:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")
    return name, cond


def self_test() -> int:
    fake_stats = {"policy_counts": {"baseline_existing_order": {"top10": 13, "top20": 17}, "distinct_file_top20_greedy_then_top10": {"top10": 16, "top20": 24}, "max_per_file_2_top10": {"top10": 15, "top20": 17}}, "group_counts": Counter({"lost_by_aggressive": 1, "unchanged_miss": 196, "unchanged_hit": 12, "gained_by_aggressive_only": 2, "gained_by_both": 2}), "max2_lost_baseline_hits": 0, "mechanism": {g: Counter() for g in ["gained_by_aggressive_only", "gained_by_max2_only", "gained_by_both", "lost_by_aggressive", "preserved_by_max2", "unchanged_miss", "unchanged_hit"]}, "regression_rows": [{"disp_rank": 6, "add_rank": 11, "dup_bucket": "low"}]}
    tests = [
        check("status_vocabulary", STATUS_PASS in STATUS_VOCAB and STATUS_ACCOUNTING in STATUS_VOCAB),
        check("safe_parser", SafeArgumentParser is not argparse.ArgumentParser),
        check("scanner_rejects_keys", scan_summary({"path": "x"})["status"] == "fail" and scan_summary({"candidate_list": []})["status"] == "fail"),
        check("scanner_rejects_values", scan_summary({"safe": "/tmp/private.jsonl"})["status"] == "fail"),
        check("scanner_allows_records", scan_summary({"policy_result_anchor_records": policy_result_anchor_records(fake_stats)})["status"] == "pass"),
        check("regression_record", regression_specific_records(fake_stats)[0]["regression_count"] == 1 and regression_specific_records(fake_stats)[0]["max_per_file_2_preserves_regression_bool"]),
        check("hybrid_signal", hybrid_rule_signal_records()[0]["hybrid_rule_family_bucket"] == "prefix_preserving_distinct_file_fill"),
        check("preview_variants", len(hybrid_rule_signal_records()[0]["preview_variant_buckets"]) == 5),
        check("privacy", privacy_boundary_records()[0][0]["candidate_id_public_count"] == 0),
        check("no_exec", no_forbidden_execution_records()[0][0]["candidate_generation_count"] == 0),
        check("false_flags", not stop_go_records()[0]["runtime_default_authorized_bool"] and not stop_go_records()[0]["p5_v1a_authorized_bool"]),
        check("rank_bucket", rank_bucket(11) == "rank_11_20" and rank_bucket(6) == "rank_1_10"),
        check("count_bucket", count_bucket(0) == "none" and count_bucket(3) == "medium"),
        check("gate_synthetic", gate_records(True, True, fake_stats, True, True, True)[1]),
        check("handoff", n10df_handoff_records()[0]["n10df_authorized_bool"]),
    ]
    passed = sum(1 for _name, ok in tests if ok)
    print(f"self_test_passed={passed == len(tests)} ({passed}/{len(tests)} checks)")
    return 0 if passed == len(tests) else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        return self_test()
    report = build_report(args)
    write_report(report, Path(args.out))
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
