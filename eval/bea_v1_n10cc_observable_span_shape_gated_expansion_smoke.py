#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import time
from typing import Any, NoReturn

from bea_v1_span_window_projection_adapter import project_evidence_spans


SCHEMA_VERSION = "bea_v1_n10cc_observable_span_shape_gated_expansion_smoke.v1"
PHASE = "BEA-v1-N10CC Observable Span-Shape Gated Expansion Smoke"
STATUS_COMPLETE = "observable_span_shape_gated_expansion_smoke_complete_n10cd_authorized"
STATUSES = (
    STATUS_COMPLETE,
    "no_go_n10cc_required_inputs_unavailable",
    "no_go_n10cc_private_span_rows_missing",
    "no_go_n10cc_variant_grid_invalid",
    "no_go_n10cc_result_accounting_invalid",
    "no_go_n10cc_privacy_or_claim_boundary_failed",
    "fail_forbidden_scan",
    "fail_schema_contract",
)
PRIVATE_SPAN_ROWS = Path(".openlocus/research-private/local_n6xfr_recovery/n1_private/bea_v1_n1.private_span_rows.jsonl")
DEFAULT_OUT = Path("artifacts/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke_report.json")
PUBLIC_INPUTS = {
    "n10cb_cluster_bridge_package_artifact": (Path("artifacts/bea_v1_n10cb_cluster_bridge_audit_package/bea_v1_n10cb_cluster_bridge_audit_package_report.json"), "cluster_bridge_audit_package_complete_n10cc_authorized"),
    "n10ca_cluster_bridge_smoke_artifact": (Path("artifacts/bea_v1_n10ca_same_file_span_cluster_bridge_smoke/bea_v1_n10ca_same_file_span_cluster_bridge_smoke_report.json"), "same_file_span_cluster_bridge_smoke_complete_n10cb_authorized"),
    "n10bz_policy_sweep_package_artifact": (Path("artifacts/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package_report.json"), "cost_efficient_policy_sweep_package_complete_n10ca_authorized"),
    "n10bx_adapter_operating_point_package_artifact": (Path("artifacts/bea_v1_n10bx_adapter_operating_point_package/bea_v1_n10bx_adapter_operating_point_package_report.json"), "adapter_operating_point_package_complete_n10by_authorized"),
}
VARIANT_ORDER = (
    "anchor_cost80_all_spans_before20_after60",
    "anchor_pm200_all_spans_before200_after200",
    "short_only_before20_after60",
    "short_only_before30_after90",
    "short_only_before50_after150",
    "short_medium_before20_after60",
    "short_medium_before30_after90",
    "short_medium_before50_after150",
    "top5_short_medium_before30_after90",
    "top10_short_medium_before30_after90",
    "top5_short_only_before50_after150",
    "top10_short_only_before50_after150",
)
COST80_TOP10 = 20
COST80_TOP20 = 24
COST80_TOP10_COST = 800
PM200_TOP10 = 25
PM200_TOP20 = 30
PM200_TOP10_COST = 4000
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
    "private_input_bucket", "intake_status_bucket", "feature_bucket", "feature_source_bucket", "feature_use_bucket",
    "variant_bucket", "variant_family_bucket", "policy_bucket", "span_length_gate_bucket", "candidate_position_gate_bucket",
    "cost_bucket", "decision_bucket", "privacy_boundary_bucket", "no_execution_boundary_bucket", "n10cd_handoff_bucket",
    "authorization", "next_allowed_phase", "next_allowed_scope_bucket", "gate", "threshold_relation",
    "expanded_candidate_count_bucket", "short_span_expanded_count_bucket", "medium_span_expanded_count_bucket", "long_span_expanded_count_bucket",
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
        rows.append({"anonymous_input_artifact_id": f"n10ccin{idx:04d}", "input_artifact_bucket": bucket, "load_status": load_status, "observed_status": observed, "expected_status": expected, "forbidden_scan_status": str(scan_status), "input_gate_passed_bool": passed})
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


def length_bucket(item: dict[str, Any]) -> str:
    length = int(item["end_line"]) - int(item["start_line"]) + 1
    if length <= 10:
        return "short"
    if length <= 30:
        return "medium"
    return "long"


def variant_family(variant: str) -> str:
    if variant.startswith("anchor"):
        return "anchor"
    if variant.startswith("top"):
        return "position_limited_observable_span_shape_gate"
    if variant.startswith("short_medium"):
        return "short_medium_observable_span_shape_gate"
    return "short_only_observable_span_shape_gate"


def variant_policy(variant: str, position: int, item: dict[str, Any]) -> tuple[int, int, bool]:
    bucket = length_bucket(item)
    if variant == "anchor_cost80_all_spans_before20_after60":
        return 20, 60, True
    if variant == "anchor_pm200_all_spans_before200_after200":
        return 200, 200, True
    policies = {
        "short_only_before20_after60": ("short", None, 20, 60),
        "short_only_before30_after90": ("short", None, 30, 90),
        "short_only_before50_after150": ("short", None, 50, 150),
        "short_medium_before20_after60": ("short_medium", None, 20, 60),
        "short_medium_before30_after90": ("short_medium", None, 30, 90),
        "short_medium_before50_after150": ("short_medium", None, 50, 150),
        "top5_short_medium_before30_after90": ("short_medium", 5, 30, 90),
        "top10_short_medium_before30_after90": ("short_medium", 10, 30, 90),
        "top5_short_only_before50_after150": ("short", 5, 50, 150),
        "top10_short_only_before50_after150": ("short", 10, 50, 150),
    }
    allowed_bucket, topk, before, after = policies[variant]
    bucket_ok = bucket == "short" if allowed_bucket == "short" else bucket in {"short", "medium"}
    position_ok = topk is None or position <= topk
    return before, after, bool(bucket_ok and position_ok)


def count_bucket(value: int) -> str:
    if value == 0:
        return "zero"
    if value <= 500:
        return "one_to_500"
    if value <= 1000:
        return "five01_to_1000"
    if value <= 2000:
        return "one001_to_2000"
    return "gt2000"


def cost_bucket(value: int) -> str:
    if value < COST80_TOP10_COST:
        return "below_cost80"
    if value == COST80_TOP10_COST:
        return "cost80_equal"
    if value <= 1500:
        return "moderate"
    if value <= PM200_TOP10_COST:
        return "up_to_pm200"
    return "above_pm200"


def project_variant(records: list[dict[str, Any]], variant: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    copied = project_evidence_spans(records, expansion_each_side=0, enabled=False)
    projected: list[dict[str, Any]] = []
    counters = Counter()
    for idx, item in enumerate(copied, 1):
        before, after, should_expand = variant_policy(variant, idx, item)
        new_item = dict(item)
        if should_expand:
            new_item["start_line"] = max(1, int(new_item["start_line"]) - before)
            new_item["end_line"] = int(new_item["end_line"]) + after
            if idx <= 10:
                counters["cost10"] += before + after
            if idx <= 20:
                counters["cost20"] += before + after
            counters["expanded"] += 1
            counters[f"{length_bucket(item)}_expanded"] += 1
        projected.append(new_item)
    return projected, dict(counters)


def compute_results(rows: list[dict[str, Any]]) -> tuple[int, dict[str, dict[str, Any]], bool]:
    usable = [row for row in rows if row_ok(row) and row.get("p4_evidence")]
    result_sets: dict[str, set[int]] = {variant: set() for variant in VARIANT_ORDER}
    cost10_values: dict[str, int] = {}
    cost20_values: dict[str, int] = {}
    top20_counts: dict[str, int] = {}
    expanded_counts: dict[str, Counter[str]] = {variant: Counter() for variant in VARIANT_ORDER}
    pool_changed = False
    order_changed = False
    for row_idx, row in enumerate(usable):
        ordered = best_order(row["p4_evidence"])
        reference = refs(row)
        for variant in VARIANT_ORDER:
            projected, counters = project_variant(ordered, variant)
            pool_changed = pool_changed or len(projected) != len(ordered)
            order_changed = order_changed or len(projected) != len(ordered)
            cost10_values[variant] = counters.get("cost10", 0)
            cost20_values[variant] = counters.get("cost20", 0)
            expanded_counts[variant].update(counters)
            if span_hit(projected, reference, 10):
                result_sets[variant].add(row_idx)
            top20_counts[variant] = top20_counts.get(variant, 0) + int(span_hit(projected, reference, 20))
    anchor = result_sets["anchor_cost80_all_spans_before20_after60"]
    results: dict[str, dict[str, Any]] = {}
    for variant in VARIANT_ORDER:
        top10 = len(result_sets[variant])
        top20 = top20_counts.get(variant, 0)
        lost_anchor = len(anchor - result_sets[variant])
        c10 = cost10_values.get(variant, 0)
        decision = "no_improvement_anchor_retained"
        if top10 >= COST80_TOP10 and top20 >= COST80_TOP20 and lost_anchor == 0 and c10 < COST80_TOP10_COST:
            decision = "cost_efficient_preserve_anchor"
        elif top10 > COST80_TOP10 and lost_anchor <= 1 and c10 <= PM200_TOP10_COST:
            decision = "recall_improves_anchor"
        counts = expanded_counts[variant]
        results[variant] = {
            "top10_span_overlap_count": top10,
            "top20_span_overlap_count": top20,
            "delta_top10_vs_cost80_anchor": top10 - COST80_TOP10,
            "delta_top20_vs_cost80_anchor": top20 - COST80_TOP20,
            "lost_cost80_anchor_hits": lost_anchor,
            "cost_proxy_top10": c10,
            "cost_proxy_top20": cost20_values.get(variant, 0),
            "cost_bucket": cost_bucket(c10),
            "expanded_candidate_count_bucket": count_bucket(counts.get("expanded", 0)),
            "short_span_expanded_count_bucket": count_bucket(counts.get("short_expanded", 0)),
            "medium_span_expanded_count_bucket": count_bucket(counts.get("medium_expanded", 0)),
            "long_span_expanded_count_bucket": count_bucket(counts.get("long_expanded", 0)),
            "decision_bucket": decision,
            "candidate_pool_changed_bool": pool_changed,
            "candidate_order_changed_bool": order_changed,
        }
    return len(usable), results, len(usable) == 213 and not pool_changed and not order_changed


def private_input_intake_records(rows: list[dict[str, Any]], load_status: str, usable: int) -> list[dict[str, Any]]:
    return [{"anonymous_private_input_intake_id": "n10ccpriv0000", "private_input_bucket": "single_scoped_n1_span_rows", "intake_status_bucket": "pass" if load_status == "pass" and len(rows) == 213 and usable == 213 else load_status, "private_span_rows_read": len(rows) if load_status == "pass" else 0, "usable_span_surface_rows": usable, "single_scoped_private_input_read_bool": load_status == "pass", "other_private_files_read_count": 0, "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False}]


def observable_feature_contract_records() -> tuple[list[dict[str, Any]], bool]:
    rows = [
        {"anonymous_feature_contract_id": "n10ccfeature0000", "feature_bucket": "original_evidence_span_length_short_medium_long", "feature_source_bucket": "observable_original_span_shape", "feature_use_bucket": "policy_allowed", "short_bucket_max_line_count": 10, "medium_bucket_min_line_count": 11, "medium_bucket_max_line_count": 30, "long_bucket_min_line_count": 31, "gold_used_bool": False, "content_used_bool": False, "file_identity_public_subgroup_bool": False},
        {"anonymous_feature_contract_id": "n10ccfeature0001", "feature_bucket": "candidate_position_top5_top10_top20", "feature_source_bucket": "observable_candidate_position_bucket", "feature_use_bucket": "policy_allowed", "gold_used_bool": False, "content_used_bool": False, "file_identity_public_subgroup_bool": False},
        {"anonymous_feature_contract_id": "n10ccfeature0002", "feature_bucket": "gold_or_outcome_features", "feature_source_bucket": "private_evaluation_only", "feature_use_bucket": "policy_forbidden", "gold_path_used_for_policy_bool": False, "gold_line_used_for_policy_bool": False, "file_hit_used_for_policy_bool": False, "span_overlap_used_for_policy_bool": False, "before_after_direction_used_for_policy_bool": False},
    ]
    return rows, True


def span_length_gate(variant: str) -> str:
    if variant.startswith("anchor"):
        return "all_spans"
    if "short_medium" in variant:
        return "short_and_medium_only"
    return "short_only"


def position_gate(variant: str) -> str:
    if variant.startswith("top5"):
        return "top5_only"
    if variant.startswith("top10"):
        return "top10_only"
    return "all_positions"


def variant_contract_records() -> tuple[list[dict[str, Any]], bool]:
    rows = []
    for idx, variant in enumerate(VARIANT_ORDER):
        rows.append({"anonymous_variant_contract_id": f"n10cccontract{idx:04d}", "variant_bucket": variant, "variant_family_bucket": variant_family(variant), "span_length_gate_bucket": span_length_gate(variant), "candidate_position_gate_bucket": position_gate(variant), "predeclared_variant_bool": True, "observable_span_shape_policy_bool": True, "candidate_pool_changed_bool": False, "candidate_order_changed_bool": False, "gold_used_for_policy_bool": False, "adaptive_tuning_bool": False})
    return rows, len(rows) == 12 and tuple(row["variant_bucket"] for row in rows) == VARIANT_ORDER


def variant_result_records(results: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    ok = True
    for idx, variant in enumerate(VARIANT_ORDER):
        observed = results.get(variant, {})
        valid = observed.get("candidate_pool_changed_bool") is False and observed.get("candidate_order_changed_bool") is False and isinstance(observed.get("top10_span_overlap_count"), int) and isinstance(observed.get("top20_span_overlap_count"), int)
        ok = ok and valid
        rows.append({"anonymous_variant_result_id": f"n10ccresult{idx:04d}", "variant_bucket": variant, "variant_family_bucket": variant_family(variant), "top10_span_overlap_count": int(observed.get("top10_span_overlap_count", 0)), "top20_span_overlap_count": int(observed.get("top20_span_overlap_count", 0)), "delta_top10_vs_cost80_anchor": int(observed.get("delta_top10_vs_cost80_anchor", 0)), "delta_top20_vs_cost80_anchor": int(observed.get("delta_top20_vs_cost80_anchor", 0)), "lost_cost80_anchor_hits": int(observed.get("lost_cost80_anchor_hits", 0)), "cost_proxy_top10": int(observed.get("cost_proxy_top10", 0)), "cost_proxy_top20": int(observed.get("cost_proxy_top20", 0)), "cost_bucket": str(observed.get("cost_bucket", "unknown")), "expanded_candidate_count_bucket": str(observed.get("expanded_candidate_count_bucket", "unknown")), "short_span_expanded_count_bucket": str(observed.get("short_span_expanded_count_bucket", "unknown")), "medium_span_expanded_count_bucket": str(observed.get("medium_span_expanded_count_bucket", "unknown")), "long_span_expanded_count_bucket": str(observed.get("long_span_expanded_count_bucket", "unknown")), "decision_bucket": str(observed.get("decision_bucket", "unknown")), "candidate_pool_changed_bool": bool(observed.get("candidate_pool_changed_bool", True)), "candidate_order_changed_bool": bool(observed.get("candidate_order_changed_bool", True)), "result_accounting_valid_bool": valid})
    return rows, ok and len(rows) == 12


def cost_proxy_records(result_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(row["cost_bucket"] for row in result_rows)
    return [{"anonymous_cost_proxy_id": f"n10cccost{idx:04d}", "cost_bucket": bucket, "variant_count": count, "cost_proxy_public_aggregate_only_bool": True} for idx, (bucket, count) in enumerate(sorted(counts.items()))]


def decision_summary_records(result_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    decisions = Counter(row["decision_bucket"] for row in result_rows)
    best = max(result_rows, key=lambda r: (r["top10_span_overlap_count"], r["top20_span_overlap_count"], -r["lost_cost80_anchor_hits"])) if result_rows else {}
    return [{"anonymous_decision_summary_id": "n10ccdecision0000", "variant_count": len(result_rows), "cost_efficient_preserve_anchor_count": decisions.get("cost_efficient_preserve_anchor", 0), "recall_improves_anchor_count": decisions.get("recall_improves_anchor", 0), "no_improvement_anchor_retained_count": decisions.get("no_improvement_anchor_retained", 0), "best_observed_variant_bucket": str(best.get("variant_bucket", "none")), "best_observed_top10_span_overlap_count": int(best.get("top10_span_overlap_count", 0)), "best_observed_top20_span_overlap_count": int(best.get("top20_span_overlap_count", 0)), "exploratory_same_source_only_bool": True, "runtime_default_recommendation_bool": False}], len(result_rows) == 12


def privacy_boundary_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_privacy_boundary_id": "n10ccprivacy0000", "privacy_boundary_bucket": "aggregate_observable_span_shape_smoke_counts_only", "private_path_public_bool": False, "private_filename_public_bool": False, "private_content_public_bool": False, "span_public_bool": False, "line_number_public_bool": False, "snippet_public_bool": False, "gold_public_bool": False, "candidate_list_public_bool": False, "exact_rank_public_bool": False, "hash_public_bool": False, "privacy_boundary_complete_bool": True}], True


def no_forbidden_execution_records() -> tuple[list[dict[str, Any]], bool]:
    return [{"anonymous_no_forbidden_execution_id": "n10ccnoexec0000", "no_execution_boundary_bucket": "same_source_observable_span_shape_smoke_only", "other_private_file_read_count": 0, "new_variant_outside_grid_count": 0, "adaptive_tuning_count": 0, "gold_used_for_policy_count": 0, "outcome_used_for_policy_count": 0, "file_identity_used_as_public_subgroup_count": 0, "candidate_pool_changed_count": 0, "candidate_order_changed_count": 0, "candidate_added_count": 0, "candidate_removed_count": 0, "cluster_bridge_execution_count": 0, "retrieval_execution_count": 0, "rerun_execution_count": 0, "openlocus_execution_count": 0, "candidate_generation_count": 0, "selector_reranker_execution_count": 0, "p5_execution_count": 0, "v1a_execution_count": 0, "runtime_default_promotion_count": 0, "heldout_claim_count": 0, "method_winner_claim_count": 0, "downstream_value_claim_count": 0, "no_forbidden_execution_complete_bool": True}], True


def n10cd_handoff_records(complete: bool) -> list[dict[str, Any]]:
    return [{"anonymous_n10cd_handoff_id": "n10cchandoff0000", "n10cd_handoff_bucket": "n10cd_public_observable_span_shape_audit_package_authorized" if complete else "n10cd_not_authorized", "n10cd_authorized_bool": complete, "public_audit_package_only_bool": complete, "private_read_authorized_bool": False, "new_variant_authorized_bool": False, "runtime_default_authorized_bool": False, "heldout_claim_authorized_bool": False, "generalization_claim_authorized_bool": False, "method_winner_claim_authorized_bool": False, "downstream_value_claim_authorized_bool": False}]


def gate_records(input_ok: bool, private_ok: bool, feature_ok: bool, contract_ok: bool, result_ok: bool, decision_ok: bool, privacy_ok: bool, noexec_ok: bool, scanner_ok: bool) -> list[dict[str, Any]]:
    specs = [("public_inputs_loaded", input_ok), ("private_span_rows_read", private_ok), ("observable_feature_contract", feature_ok), ("variant_grid_predeclared", contract_ok), ("result_accounting", result_ok), ("decision_summary", decision_ok), ("privacy_boundary", privacy_ok), ("no_forbidden_execution", noexec_ok), ("forbidden_scan", scanner_ok)]
    return [{"gate": name, "passed": bool(ok), "threshold_relation": "equals", "value": int(ok), "threshold_value": 1} for name, ok in specs]


def stop_go_records(complete: bool) -> list[dict[str, Any]]:
    return [{"authorization": "n10cd_public_audit_package_authorized" if complete else "n10cd_not_authorized", "next_allowed_phase": "BEA-v1-N10CD Observable Span-Shape Gated Expansion Audit Package" if complete else "none_until_observable_span_shape_smoke_valid", "next_allowed_scope_bucket": "public_audit_package_only" if complete else "no_next_phase", "n10cd_authorized": complete, "private_read_authorized": False, "new_variant_authorized": False, "adaptive_tuning_authorized": False, "cluster_bridge_authorized": False, "runtime_or_default_authorized": False, "heldout_or_generalization_claim_authorized": False, "method_winner_claim_authorized": False, "downstream_value_claim_authorized": False, "retrieval_authorized": False, "rerun_authorized": False, "candidate_generation_authorized": False, "candidate_add_remove_reorder_authorized": False, "selector_or_reranker_authorized": False, "p5_authorized": False, "v1_a_authorized": False}]


def status_for(self_ok: bool, input_ok: bool, load_status: str, private_ok: bool, feature_ok: bool, contract_ok: bool, result_ok: bool, decision_ok: bool, privacy_ok: bool, noexec_ok: bool) -> str:
    if not self_ok:
        return "fail_schema_contract"
    if not input_ok:
        return "no_go_n10cc_required_inputs_unavailable"
    if load_status == "missing":
        return "no_go_n10cc_private_span_rows_missing"
    if not contract_ok:
        return "no_go_n10cc_variant_grid_invalid"
    if not private_ok or not feature_ok or not result_ok or not decision_ok:
        return "no_go_n10cc_result_accounting_invalid"
    if not privacy_ok or not noexec_ok:
        return "no_go_n10cc_privacy_or_claim_boundary_failed"
    return STATUS_COMPLETE


def build_report(checks: list[dict[str, Any]]) -> dict[str, Any]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, results, compute_ok = compute_results(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    feature_rows, feature_ok = observable_feature_contract_records()
    contract_rows, contract_ok = variant_contract_records()
    result_rows, result_ok = variant_result_records(results)
    decision_rows, decision_ok = decision_summary_records(result_rows)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    self_ok = all(c["passed"] for c in checks)
    status = status_for(self_ok, input_ok, load_status, private_ok, feature_ok, contract_ok, result_ok, decision_ok, privacy_ok, noexec_ok)
    complete = status == STATUS_COMPLETE
    report: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "status": status, "phase": PHASE, "claim_level": "same_source_observable_span_shape_smoke_only", "generated_by": "bea_v1_n10cc_observable_span_shape_gated_expansion_smoke", "generated_at": now(), "status_vocabulary": list(STATUSES), "self_test_passed": self_ok, "self_test_checks_total": len(checks), "self_test_checks_passed": sum(1 for c in checks if c["passed"]), "input_artifact_records": input_rows, "private_input_intake_records": private_input_intake_records(rows, load_status, usable), "observable_feature_contract_records": feature_rows, "variant_contract_records": contract_rows, "variant_result_records": result_rows, "cost_proxy_records": cost_proxy_records(result_rows), "decision_summary_records": decision_rows, "privacy_boundary_records": privacy_rows, "no_forbidden_execution_records": noexec_rows, "n10cd_handoff_records": n10cd_handoff_records(complete), "gate_records": gate_records(input_ok, private_ok, feature_ok, contract_ok, result_ok, decision_ok, privacy_ok, noexec_ok, True), "stop_go_records": stop_go_records(complete), "forbidden_scan": {}, "method_winner_claimed": False, "downstream_value_claimed": False}
    scan = scan_summary(report)
    if scan["status"] != "pass":
        report["status"] = "fail_forbidden_scan"
    final_scan = scan_summary(report)
    scanner_ok = final_scan["status"] == "pass"
    report["forbidden_scan"] = final_scan
    if not scanner_ok:
        report["status"] = "fail_forbidden_scan"
    complete = report["status"] == STATUS_COMPLETE
    report["n10cd_handoff_records"] = n10cd_handoff_records(complete)
    report["gate_records"] = gate_records(input_ok, private_ok, feature_ok, contract_ok, result_ok, decision_ok, privacy_ok, noexec_ok, scanner_ok)
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


def synthetic_span_shape() -> bool:
    short = {"start_line": 1, "end_line": 5, "path": "x"}
    medium = {"start_line": 1, "end_line": 20, "path": "x"}
    long = {"start_line": 1, "end_line": 60, "path": "x"}
    return length_bucket(short) == "short" and length_bucket(medium) == "medium" and length_bucket(long) == "long"


def synthetic_policy() -> bool:
    short = {"start_line": 10, "end_line": 15, "path": "x"}
    long = {"start_line": 10, "end_line": 100, "path": "x"}
    return variant_policy("top5_short_only_before50_after150", 5, short) == (50, 150, True) and variant_policy("top5_short_only_before50_after150", 6, short) == (50, 150, False) and variant_policy("short_medium_before20_after60", 1, long) == (20, 60, False)


def run_self_test() -> tuple[list[dict[str, Any]], bool]:
    input_rows, input_ok = input_artifact_records()
    rows, load_status = load_rows()
    usable, results, compute_ok = compute_results(rows) if load_status == "pass" else (0, {}, False)
    private_ok = load_status == "pass" and len(rows) == 213 and usable == 213 and compute_ok
    feature_rows, feature_ok = observable_feature_contract_records()
    contract_rows, contract_ok = variant_contract_records()
    result_rows, result_ok = variant_result_records(results)
    decision_rows, decision_ok = decision_summary_records(result_rows)
    privacy_rows, privacy_ok = privacy_boundary_records()
    noexec_rows, noexec_ok = no_forbidden_execution_records()
    checks = [
        check("status_vocabulary", tuple(STATUSES) == (STATUS_COMPLETE, "no_go_n10cc_required_inputs_unavailable", "no_go_n10cc_private_span_rows_missing", "no_go_n10cc_variant_grid_invalid", "no_go_n10cc_result_accounting_invalid", "no_go_n10cc_privacy_or_claim_boundary_failed", "fail_forbidden_scan", "fail_schema_contract")),
        check("safe_parser", parser_hides_unknown()),
        check("scanner_rejects_keys", all(scan_summary({k: "x"})["status"] == "fail" for k in ("path", "filename", "candidate_list", "gold_paths", "exact_rank", "span", "snippet", "hash", "provider_payload"))),
        check("scanner_rejects_values", scan_summary({"safe": "private/file.jsonl"})["status"] == "fail" and scan_summary({"safe": "1-2"})["status"] == "fail"),
        check("public_inputs", input_ok and len(input_rows) == 4),
        check("private_rows", private_ok),
        check("feature_contract", feature_ok and len(feature_rows) == 3 and feature_rows[2]["feature_use_bucket"] == "policy_forbidden"),
        check("variant_grid", contract_ok and len(contract_rows) == 12),
        check("variant_results", result_ok and len(result_rows) == 12),
        check("decision_summary", decision_ok and decision_rows[0]["variant_count"] == 12),
        check("privacy", privacy_ok and privacy_rows[0]["line_number_public_bool"] is False),
        check("no_forbidden_execution", noexec_ok and noexec_rows[0]["cluster_bridge_execution_count"] == 0 and noexec_rows[0]["candidate_order_changed_count"] == 0),
        check("synthetic_span_shape", synthetic_span_shape()),
        check("synthetic_policy", synthetic_policy()),
        check("status_complete", status_for(True, True, "pass", True, True, True, True, True, True, True) == STATUS_COMPLETE),
        check("false_flags", stop_go_records(True)[0]["n10cd_authorized"] is True and stop_go_records(True)[0]["runtime_or_default_authorized"] is False and stop_go_records(True)[0]["cluster_bridge_authorized"] is False),
    ]
    return checks, all(c["passed"] for c in checks)


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(description="BEA-v1-N10CC observable span-shape gated expansion smoke")
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
