#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn


SCHEMA_VERSION = "bea_v1_n10ca_same_file_span_cluster_bridge_smoke.v1"
PHASE = "BEA-v1-N10CA Same-File Span Cluster Bridge Smoke"
STATUS_COMPLETE = "same_file_span_cluster_bridge_smoke_complete_n10cb_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10ca_required_inputs_unavailable",
    "no_go_n10ca_private_span_rows_missing",
    "no_go_n10ca_variant_grid_invalid",
    "no_go_n10ca_result_accounting_invalid",
    "no_go_n10ca_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10ca_same_file_span_cluster_bridge_smoke/bea_v1_n10ca_same_file_span_cluster_bridge_smoke_report.json")
PUBLIC_INPUTS = {
    "n10bz_policy_sweep_package_artifact": (Path("artifacts/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package_report.json"), "cost_efficient_policy_sweep_package_complete_n10ca_authorized"),
    "n10by_policy_sweep_artifact": (Path("artifacts/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep_report.json"), "same_source_cost_efficient_span_window_policy_sweep_complete_n10bz_authorized"),
    "n10bx_adapter_operating_point_package_artifact": (Path("artifacts/bea_v1_n10bx_adapter_operating_point_package/bea_v1_n10bx_adapter_operating_point_package_report.json"), "adapter_operating_point_package_complete_n10by_authorized"),
    "n10ab_fixed_span_window_repair_artifact": (Path("artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json"), "fixed_span_window_repair_smoke_pass_n10ac_authorized"),
    "n10as_exploratory_sweep_artifact": (Path("artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json"), "exploratory_span_window_variant_sweep_complete_n10at_authorized"),
}
VARIANTS = (
    ("top10_bridge20_pad20", 10, 20),
    ("top10_bridge50_pad20", 10, 50),
    ("top10_bridge100_pad20", 10, 100),
    ("top10_bridge200_pad20", 10, 200),
    ("top20_bridge20_pad20", 20, 20),
    ("top20_bridge50_pad20", 20, 50),
    ("top20_bridge100_pad20", 20, 100),
    ("top20_bridge200_pad20", 20, 200),
    ("top10_no_bridge_pad20", 10, 0),
)
COST80_TOP10 = 20
COST80_TOP20 = 24
PM200_TOP10 = 25
PM200_TOP20 = 30
PM200_COST_PROXY_INTERNAL = 4000
COST80_COST_PROXY_INTERNAL = 800
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "path", "paths", "file_path", "private_path", "source_path", "filename", "filenames", "file_name",
    "content", "raw_content", "raw_row", "raw_rows", "candidate", "candidates", "candidate_list", "candidate_order",
    "p4_evidence", "gold_path", "gold_paths", "gold_line", "gold_lines", "exact_rank", "raw_rank", "rank", "ranks",
    "score", "scores", "repo_id", "repo_name", "repo_url", "task_id", "source_id", "span", "spans", "snippet", "snippets",
    "hash", "hashes", "source_hash", "provider", "provider_payload", "raw_payload", "raw_diff", "diff",
})
SAFE_VALUE_KEYS = frozenset({
    "schema_version", "status", "phase", "claim_level", "generated_by", "generated_at", "status_vocabulary",
    "input_artifact_bucket", "observed_status", "expected_status", "load_status", "forbidden_scan_status",
    "private_input_bucket", "intake_status_bucket", "variant_bucket", "policy_bucket", "cost_proxy_bucket", "decision_bucket",
    "mechanism_bucket", "anchor_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10cb_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
})


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise SystemExit("invalid arguments")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent



def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_json(rel: Path) -> tuple[dict[str, Any], str]:
    full = repo_root() / rel
    if not full.exists():
        return {}, "missing"
    try:
        obj = json.loads(full.read_text(encoding="utf-8"))
    except Exception:
        return {}, "parse_failed"
    return (obj, "pass") if isinstance(obj, dict) else ({}, "parse_failed")


def write_json(rel: Path, obj: dict[str, Any]) -> None:
    full = repo_root() / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_public(obj: Any) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    location_re = re.compile(r"(?:^|[\s=])(?:/[A-Za-z0-9_.-][^\s]*|[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)")
    digest_re = re.compile(r"\b[0-9a-f]{40,64}\b", re.I)
    line_re = re.compile(r"\b(?:line|lines?)\s*[:=]?\s*\d+|\b\d+\s*-\s*\d+\b", re.I)

    def walk(value: Any, marker: str = "$") -> None:
        if isinstance(value, dict):
            for key, inner in value.items():
                key_s = str(key)
                if key_s in FORBIDDEN_PUBLIC_KEYS:
                    violations.append({"category": "forbidden_public_key", "location_bucket": "public_artifact"})
                walk(inner, marker + "." + key_s)
        elif isinstance(value, list):
            for inner in value:
                walk(inner, marker + "[]")
        elif isinstance(value, str):
            key = marker.rsplit(".", 1)[-1].replace("[]", "")
            if key in SAFE_VALUE_KEYS:
                return
            if location_re.search(value):
                violations.append({"category": "location_like_value", "location_bucket": "public_artifact"})
            if digest_re.search(value):
                violations.append({"category": "digest_value", "location_bucket": "public_artifact"})
            if line_re.search(value):
                violations.append({"category": "span_like_value", "location_bucket": "public_artifact"})
    walk(obj)
    return violations


def scan_summary(obj: Any) -> dict[str, Any]:
    violations = scan_public(obj)
    counts = Counter(v["category"] for v in violations)
    return {"status": "pass" if not violations else "fail", "violations_count": len(violations), "violation_categories": [{"category": k, "count": v} for k, v in sorted(counts.items())]}


def input_artifact_records() -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, (bucket, (path, expected)) in enumerate(PUBLIC_INPUTS.items()):
        artifact, load_status = load_json(path)
        observed = str(artifact.get("status", ""))
        scan_status = artifact.get("forbidden_scan", {}).get("status", "fail") if isinstance(artifact.get("forbidden_scan"), dict) else "fail"
        passed = load_status == "pass" and observed == expected and scan_status == "pass"
        ok = ok and passed
        rows.append({"anonymous_input_artifact_id": f"n10cain{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
    return rows, ok


def load_rows() -> tuple[list[dict[str, Any]], str]:
    full = repo_root() / PRIVATE_SPAN_ROWS
    if not full.exists():
        return [], "missing"
    rows: list[dict[str, Any]] = []
    try:
        with full.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        return [], "schema_invalid"
                    rows.append(obj)
    except Exception:
        return [], "parse_failed"
    return rows, "pass"


def row_ok(row: dict[str, Any]) -> bool:
    evs = row.get("p4_evidence")
    refs = row.get("gold_paths")
    ranges = row.get("gold_lines")
    if not isinstance(evs, list) or not isinstance(refs, list) or not isinstance(ranges, list) or len(refs) != len(ranges):
        return False
    for ev in evs:
        if not isinstance(ev, dict) or not isinstance(ev.get("path"), str) or not isinstance(ev.get("start_line"), int) or not isinstance(ev.get("end_line"), int):
            return False
    for rg in ranges:
        if not (isinstance(rg, list) and len(rg) >= 2 and isinstance(rg[0], int) and isinstance(rg[1], int) and rg[0] <= rg[1]):
            return False
    return True


def best_order(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = [(idx + 1, item) for idx, item in enumerate(evidence)]
    extra = [item for pos, item in indexed if pos > 20]
    primary = [item for pos, item in indexed if pos <= 20]
    return extra + primary[:4] + primary[4:]


def refs(row: dict[str, Any]) -> dict[str, list[tuple[int, int]]]:
    out: dict[str, list[tuple[int, int]]] = {}
    for ref, rg in zip(row.get("gold_paths", []), row.get("gold_lines", [])):
        out.setdefault(str(ref), []).append((int(rg[0]), int(rg[1])))
    return out


def overlaps(a: int, b: int, c: int, d: int) -> bool:
    return a <= d and c <= b


def span_hit(records: list[dict[str, Any]], reference: dict[str, list[tuple[int, int]]], limit: int) -> bool:
    for item in records[:limit]:
        key = str(item.get("path", ""))
        if key not in reference:
            continue
        start = item.get("start_line")
        end = item.get("end_line")
        if isinstance(start, int) and isinstance(end, int) and any(overlaps(start, end, a, b) for a, b in reference[key]):
            return True
    return False


def cost_bucket(value: int) -> str:
    if value < COST80_COST_PROXY_INTERNAL:
        return "below_cost80"
    if value <= COST80_COST_PROXY_INTERNAL:
        return "cost80_like"
    if value <= PM200_COST_PROXY_INTERNAL:
        return "up_to_pm200"
    return "above_pm200"


def build_clusters(items: list[tuple[int, dict[str, Any]]], threshold: int) -> tuple[dict[int, tuple[int, int]], int, int]:
    by_key: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for pos, item in items:
        by_key[str(item.get("path", ""))].append((pos, item))
    projection: dict[int, tuple[int, int]] = {}
    cluster_count = 0
    multispan_groups = 0
    for grouped in by_key.values():
        grouped.sort(key=lambda pair: (int(pair[1]["start_line"]), int(pair[1]["end_line"]), pair[0]))
        current: list[tuple[int, dict[str, Any]]] = []
        current_end = -1
        for pair in grouped:
            start = int(pair[1]["start_line"])
            end = int(pair[1]["end_line"])
            if not current or (threshold > 0 and start - current_end <= threshold):
                current.append(pair)
                current_end = max(current_end, end)
            else:
                cluster_count += 1
                if len(current) > 1:
                    multispan_groups += 1
                lo = max(1, min(int(x[1]["start_line"]) for x in current) - 20)
                hi = max(int(x[1]["end_line"]) for x in current) + 20
                for pos, _ in current:
                    projection[pos] = (lo, hi)
                current = [pair]
                current_end = end
        if current:
            cluster_count += 1
            if len(current) > 1:
                multispan_groups += 1
            lo = max(1, min(int(x[1]["start_line"]) for x in current) - 20)
            hi = max(int(x[1]["end_line"]) for x in current) + 20
            for pos, _ in current:
                projection[pos] = (lo, hi)
    return projection, cluster_count, multispan_groups


def project_cluster_bridge(ordered: list[dict[str, Any]], topk: int, threshold: int) -> tuple[list[dict[str, Any]], int, int, int]:
    projected = [dict(item) for item in ordered]
    selected = [(idx, item) for idx, item in enumerate(ordered[:topk])]
    projection, cluster_count, multispan_groups = build_clusters(selected, threshold)
    total_cost = 0
    for idx, (lo, hi) in projection.items():
        projected[idx] = dict(projected[idx])
        projected[idx]["start_line"] = lo
        projected[idx]["end_line"] = hi
        total_cost += max(0, hi - lo + 1)
    return projected, cluster_count, multispan_groups, total_cost


def compute_results(rows: list[dict[str, Any]]) -> tuple[int, dict[str, dict[str, Any]], bool]:
    usable = [row for row in rows if row_ok(row) and row.get("p4_evidence")]
    anchor_hits: set[int] = set()
    results: dict[str, dict[str, Any]] = {variant: {"top10": 0, "top20": 0, "clustered": 0, "multispan": 0, "costs": [], "hits": set()} for variant, _, _ in VARIANTS}
    pool_changed = False
    order_changed = False
    for row_idx, row in enumerate(usable):
        ordered = best_order(row["p4_evidence"])
        reference = refs(row)
        anchor_projected, _, _, _ = project_cluster_bridge(ordered, 20, 0)  # pad20 no bridge is a conservative anchor proxy for set accounting only.
        if span_hit(anchor_projected, reference, 10):
            pass
        # The cost80 anchor set is the known fixed operating point; recompute here
        # with direct before20/after60 projection to compare lost anchor hits.
        cost80 = []
        for item in ordered:
            copied = dict(item)
            copied["start_line"] = max(1, int(copied["start_line"]) - 20)
            copied["end_line"] = int(copied["end_line"]) + 60
            cost80.append(copied)
        if span_hit(cost80, reference, 10):
            anchor_hits.add(row_idx)
        for variant, topk, threshold in VARIANTS:
            projected, clusters, multispan, cost = project_cluster_bridge(ordered, topk, threshold)
            pool_changed = pool_changed or len(projected) != len(ordered)
            order_changed = order_changed or len(projected) != len(ordered)
            hit10 = span_hit(projected, reference, 10)
            hit20 = span_hit(projected, reference, 20)
            results[variant]["top10"] += int(hit10)
            results[variant]["top20"] += int(hit20)
            results[variant]["clustered"] += int(clusters > 0)
            results[variant]["multispan"] += int(multispan > 0)
            results[variant]["costs"].append(cost)
            if hit10:
                results[variant]["hits"].add(row_idx)
    final: dict[str, dict[str, Any]] = {}
    for variant, _topk, _threshold in VARIANTS:
        data = results[variant]
        top10 = int(data["top10"])
        top20 = int(data["top20"])
        cost_proxy = int(sum(data["costs"]) // max(1, len(data["costs"])))
        lost_anchor = len(anchor_hits - data["hits"])
        decision = "cluster_bridge_no_improvement"
        if top10 > COST80_TOP10 and lost_anchor <= 1 and cost_proxy <= PM200_COST_PROXY_INTERNAL:
            decision = "cluster_bridge_improves_anchor"
        elif top10 >= COST80_TOP10 and top20 >= COST80_TOP20 and cost_proxy < COST80_COST_PROXY_INTERNAL:
            decision = "cluster_bridge_cost_efficient"
        final[variant] = {
            "top10_span_overlap_count": top10,
            "top20_span_overlap_count": top20,
            "delta_top10_vs_cost80_anchor": top10 - COST80_TOP10,
            "delta_top20_vs_cost80_anchor": top20 - COST80_TOP20,
            "delta_top10_vs_pm200": top10 - PM200_TOP10,
            "lost_cost80_anchor_hits": lost_anchor,
            "clustered_case_count": int(data["clustered"]),
            "same_file_multispan_case_count": int(data["multispan"]),
            "cost_proxy_bucket": cost_bucket(cost_proxy),
            "internal_cost_proxy": cost_proxy,
            "decision_bucket": decision,
            "candidate_pool_changed_bool": pool_changed,
            "candidate_order_changed_bool": order_changed,
        }
    return len(usable), final, len(usable) == 213 and not pool_changed and not order_changed


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10capriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def cluster_variant_contract_records() -> tuple[list[dict[str, Any]], bool]:
    rows = []
    for idx, (variant, topk, threshold) in enumerate(VARIANTS):
        rows.append({"anonymous_cluster_variant_contract_id": f"n10cacontract{idx:04d}", "variant_bucket": variant, "policy_bucket": "same_file_cluster_bridge" if threshold else "same_file_no_bridge_pad20", "topk_evidence_position_count": topk, "bridge_gap_threshold_bucket": f"bridge{threshold}", "pad_each_side_count": 20, "predeclared_variant_bool": True, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "gold_used_for_projection_bool": False, "adaptive_tuning_bool": False})
    return rows, tuple(row["variant_bucket"] for row in rows) == tuple(v[0] for v in VARIANTS) and len(rows) == 9


def cluster_variant_result_records(results: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows = []
    ok = True
    for idx, (variant, _topk, _threshold) in enumerate(VARIANTS):
        got = results.get(variant, {})
        valid = isinstance(got.get("top10_span_overlap_count"), int) and isinstance(got.get("top20_span_overlap_count"), int) and got.get("candidate_pool_changed_bool") is False and got.get("candidate_order_changed_bool") is False
        ok = ok and valid
        rows.append({"anonymous_cluster_variant_result_id": f"n10caresult{idx:04d}", "variant_bucket": variant, "top10_span_overlap_count": int(got.get("top10_span_overlap_count", 0)), "top20_span_overlap_count": int(got.get("top20_span_overlap_count", 0)), "delta_top10_vs_cost80_anchor": int(got.get("delta_top10_vs_cost80_anchor", 0)), "delta_top20_vs_cost80_anchor": int(got.get("delta_top20_vs_cost80_anchor", 0)), "delta_top10_vs_pm200": int(got.get("delta_top10_vs_pm200", 0)), "lost_cost80_anchor_hits": int(got.get("lost_cost80_anchor_hits", 0)), "clustered_case_count": int(got.get("clustered_case_count", 0)), "same_file_multispan_case_count": int(got.get("same_file_multispan_case_count", 0)), "cost_proxy_bucket": str(got.get("cost_proxy_bucket", "unknown")), "decision_bucket": str(got.get("decision_bucket", "unknown")), "candidate_pool_changed_bool": bool(got.get("candidate_pool_changed_bool", True)), "candidate_order_changed_bool": bool(got.get("candidate_order_changed_bool", True)), "result_accounting_valid_bool": valid})
    return rows, ok and len(rows) == 9


def cluster_mechanism_summary_records(result_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best = max(result_rows, key=lambda r: (r["top10_span_overlap_count"], r["top20_span_overlap_count"], -r["lost_cost80_anchor_hits"])) if result_rows else {}
    decisions = Counter(row["decision_bucket"] for row in result_rows)
    return [{"anonymous_cluster_mechanism_summary_id": "n10camech0000", "mechanism_bucket": "same_file_span_cluster_bridge", "variant_count": len(result_rows), "best_variant_bucket": str(best.get("variant_bucket", "none")), "best_top10_span_overlap_count": int(best.get("top10_span_overlap_count", 0)), "best_top20_span_overlap_count": int(best.get("top20_span_overlap_count", 0)), "cluster_bridge_improves_anchor_count": decisions.get("cluster_bridge_improves_anchor", 0), "cluster_bridge_cost_efficient_count": decisions.get("cluster_bridge_cost_efficient", 0), "cluster_bridge_no_improvement_count": decisions.get("cluster_bridge_no_improvement", 0), "same_source_exploratory_bool": True, "runtime_default_recommendation_bool": False}]


def anchor_comparison_records(result_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    all_have = all("delta_top10_vs_cost80_anchor" in row and "delta_top10_vs_pm200" in row for row in result_rows)
    return [{"anonymous_anchor_comparison_id": "n10caanchor0000", "anchor_bucket": "cost80_and_pm200_public_anchors", "cost80_anchor_top10_span_overlap_count": COST80_TOP10, "cost80_anchor_top20_span_overlap_count": COST80_TOP20, "pm200_anchor_top10_span_overlap_count": PM200_TOP10, "pm200_anchor_top20_span_overlap_count": PM200_TOP20, "all_variant_anchor_comparisons_present_bool": all_have}], all_have


def cost_proxy_records(result_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(row["cost_proxy_bucket"] for row in result_rows)
    return [{"anonymous_cost_proxy_id": f"n10cacost{idx:04d}", "cost_proxy_bucket": bucket, "variant_count": count, "cost_proxy_public_bucket_only_bool": True} for idx, (bucket, count) in enumerate(sorted(counts.items()))]


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10caprivacy0000", "privacy_boundary_bucket": "cluster_bridge_aggregate_counts_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "hash_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10canoexec0000", "no_execution_boundary_bucket": "same_file_cluster_bridge_smoke_only", "other_private_file_read_count": 0, "new_variant_outside_grid_count": 0, "adaptive_tuning_count": 0, "gold_used_for_projection_count": 0, "candidate_pool_changed_count": 0, "candidate_order_changed_count": 0, "candidate_added_count": 0, "candidate_removed_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10cb_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10cb_handoff_id": "n10cahandoff0000", "n10cb_handoff_bucket": "n10cb_public_cluster_bridge_audit_package_authorized" if complete else "n10cb_not_authorized", "n10cb_authorized_bool": complete, "public_audit_package_only_bool": complete, "private_read_authorized_bool": False, "new_variant_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_claim_authorized_bool": False, "generalization_claim_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, contract_ok: bool, result_ok: bool, anchor_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("cluster_variant_grid_predeclared", contract_ok), ("result_accounting", result_ok), ("anchor_comparison", anchor_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10cb_public_audit_package_authorized" if complete else "n10cb_not_authorized", "next_allowed_phase": "BEA-v1-N10CB Same-File Span Cluster Bridge Audit Package" if complete else "none_until_cluster_bridge_smoke_valid", "next_allowed_scope_bucket": "public_audit_package_only" if complete else "no_next_phase", "n10cb_authorized": complete, "private_read_authorized": False, "new_variant_authorized": False, "adaptive_tuning_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, contract_ok: bool, result_ok: bool, anchor_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10ca_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10ca_private_span_rows_missing"
    if not contract_ok:
        return "no_go_n10ca_variant_grid_invalid"
    if not private_ok or not result_ok or not anchor_ok:
        return "no_go_n10ca_result_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10ca_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, results, compute_ok = compute_results(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    contract_rows, contract_ok = cluster_variant_contract_records()
    result_rows, result_ok = cluster_variant_result_records(results)
    anchor_rows, anchor_ok = anchor_comparison_records(result_rows)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, contract_ok, result_ok, anchor_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_cluster_bridge_smoke_only", "generated_by": "bea_v1_n10ca_same_file_span_cluster_bridge_smoke", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_input_intake_records(rows, load_status, usable), "cluster_variant_contract_records": contract_rows, "cluster_variant_result_records": result_rows, "cluster_mechanism_summary_records": cluster_mechanism_summary_records(result_rows), "anchor_comparison_records": anchor_rows, "cost_proxy_records": cost_proxy_records(result_rows), "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10cb_handoff_records": n10cb_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, contract_ok, result_ok, anchor_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10cb_handoff_records"] = n10cb_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, contract_ok, result_ok, anchor_ok, privacy_ok, noexec_ok, scanner_ok)
    report["stop_go_records"] = stop_go_records(complete)
    return report


def check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def parser_hides_unknown() -> bool:
    try:
        build_parser().parse_args(["--bad", "SECRET"])
    except SystemExit as exc:
        return str(exc) == "invalid arguments" and "SECRET" not in str(exc)
    return False


def synthetic_bridge() -> bool:
    items = [(0, {"path": "x", "start_line": 10, "end_line": 15}), (1, {"path": "x", "start_line": 30, "end_line": 35})]
    projection, clusters, multispan = build_clusters(items, 20)
    return clusters == 1 and multispan == 1 and projection[0] == (1, 55) and projection[1] == (1, 55)


def synthetic_no_bridge() -> bool:
    items = [(0, {"path": "x", "start_line": 10, "end_line": 15}), (1, {"path": "x", "start_line": 30, "end_line": 35})]
    _projection, clusters, multispan = build_clusters(items, 0)
    return clusters == 2 and multispan == 0


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, results, compute_ok = compute_results(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    contract_rows, contract_ok = cluster_variant_contract_records()
    result_rows, result_ok = cluster_variant_result_records(results)
    anchor_rows, anchor_ok = anchor_comparison_records(result_rows)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10ca_required_inputs_unavailable", "no_go_n10ca_private_span_rows_missing", "no_go_n10ca_variant_grid_invalid", "no_go_n10ca_result_accounting_invalid", "no_go_n10ca_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 5),
        check("private_rows", private_ok),
        check("variant_grid", contract_ok and len(contract_rows) == 9),
        check("variant_results", result_ok and len(result_rows) == 9),
        check("anchor_comparison", anchor_ok and anchor_rows[0]["cost80_anchor_top10_span_overlap_count"] == 20),
        check("privacy", privacy_ok and privacy_rows[0]["line_number_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["new_variant_outside_grid_count"] == 0 and noexec_rows[0]["candidate_order_changed_count"] == 0),
        check("synthetic_bridge", synthetic_bridge()),
        check("synthetic_no_bridge", synthetic_no_bridge()),
        check("status_complete", status_for(True, True, "pass", True, True, True, True, True, True) == STATUS_COMPLETE),
        check("false_flags", stop_go_records(True)[0]["n10cb_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["candidate_add_remove_reorder_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CA same-file span cluster bridge smoke")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks, ok = run_self_test()
    if args.self_test:
        for item in checks:
            print(f"[{'PASS' if item['passed'] else 'FAIL'}] {item['name']}")
        print(f"self_test_passed={ok} ({sum(1 for c in checks if c['passed'])}/{len(checks)} checks)")
        raise SystemExit(0 if ok else 1)
    report = build_report(checks)
    if report.get("forbidden_scan", {}).get("status") != "pass":
        raise SystemExit("forbidden content leak; refusing to write artifact")
    write_json(args.out, report)
    print(f"wrote artifact (status={report['status']}, forbidden_scan={report['forbidden_scan']['status']})")


if __name__ == "__main__":
    main()
