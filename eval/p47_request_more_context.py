#!/usr/bin/env python3
"""P47 Request-More-Context / Span-Geometry Diagnostic: deterministic SCORE-phase span-geometry evaluator."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))
import p46_candidate_reach_cost_map as p46
import p25_bucket_policy as p25

SCHEMA_VERSION = "p47-request-more-context-v1"
GENERATED_BY = "eval/p47_request_more_context.py"

DEFAULT_OUT = Path("artifacts/p47_request_more_context/p47_request_more_context_report.json")
DEFAULT_DOC = Path("docs/en/p47-request-more-context.md")

K_VALUES = [1, 3, 5, 10, 20]

REACH_STRATEGIES = [
    "candidate_baseline", "rrf_primary", "symbol_primary", "regex_primary",
    "symbol_regex_union", "llm_span_narrow", "llm_filter", "llm_abstain_filter",
]

VARIANTS = [
    "raw_candidate_span", "neighbor_window_small", "neighbor_window_medium",
    "request_more_context_gate_v0", "ast_symbol_trim_unavailable",
]

GAP_TYPES = ["adjacent_or_overlap", "same_file_near", "same_file_far", "candidate_absent"]

P47_SAFETY_FLAG_KEYS = set(p46.SAFETY_FLAG_KEYS) | {
    "source_reads_attempted", "source_read_availability", "source_read_availability_note",
    "ast_trim_availability", "ast_trim_availability_note",
    "small_window", "medium_window", "medium_max_width", "variants", "k_values",
    "variant_metrics_available", "gap_breakdown_available",
    "variant_map", "gap_type_breakdown", "hypothetical_upper_bound",
    "by_strategy", "by_variant", "by_k", "gap_rates", "strategy_availability",
    "reason", "note", "width_cap_count",
    "context_requests_accepted", "context_requests_rejected_raw_preserved",
    "context_request_total", "context_request_accept_rate", "expanded_candidate_count",
}

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in p46.FORBIDDEN_PUBLIC_KEYS and key_str not in P47_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations

def _percentile(values: Sequence[float | int], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n == 1:
        return float(s[0])
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(s[int(k)])
    return float(s[f] * (c - k) + s[c] * (k - f))

def _span_width(ev: dict[str, Any]) -> int:
    start = int(ev.get("start_line") or 0)
    end = int(ev.get("end_line") or 0)
    if start <= 0 or end <= 0 or end < start:
        return 0
    return end - start + 1

def _raw_span(ev: dict[str, Any]) -> dict[str, Any]:
    start = int(ev.get("start_line") or 0)
    end = int(ev.get("end_line") or 0)
    if end < start:
        end = start
    return {
        "path": str(ev.get("path") or "").lower(),
        "start_line": start,
        "end_line": end,
    }

def _expand_span(ev: dict[str, Any], window: int) -> dict[str, Any]:
    raw = _raw_span(ev)
    raw["start_line"] = max(1, raw["start_line"] - window)
    raw["end_line"] = raw["end_line"] + window
    return raw

def _request_more_context_gate_v0(
    ev: dict[str, Any],
    rank: int,
    task: dict[str, Any],
) -> tuple[bool, str]:
    # Conservative gate: no gold labels; uses rank, bucket, tags, subtypes, route features.
    if rank > 5:
        return False, "rank_above_5"

    bucket = task.get("task_bucket", "unknown")
    if bucket in {"negative", "no_gold", "dense_quiver_trap", "hard_distractor", "ambiguous"}:
        return False, "negative_or_no_gold_bucket"

    tags_lower = {str(t).lower() for t in task.get("task_risk_tags", [])}
    dangerous_tags = {
        "negative",
        "high_noise",
        "hard_distractor",
        "dense_false_positive",
        "dense_quiver_trap",
        "hallucination_risk",
        "ambiguous",
    }
    if tags_lower & dangerous_tags:
        return False, "dangerous_risk_tag"

    subtypes = task.get("subtypes") or []
    top: dict[str, Any] | None = None
    top_rank: int | None = None
    for row in subtypes:
        if not isinstance(row, dict):
            continue
        r = row.get("rank")
        if isinstance(r, int) and (top_rank is None or r < top_rank):
            top_rank = r
            top = row

    if top is not None:
        vals = p46._sanitize_subtype_values(top)
        if vals["source_class"] == "regex_only":
            return False, "dangerous_subtype_regex_only"
        if vals["agreement_class"] in {"disagree", "single_source"}:
            return False, "dangerous_subtype_agreement"
        if (
            vals["source_class"] == "symbol_regex_fusion"
            and vals["agreement_class"] == "span_overlap"
            and vals["rrf_backing"] == "rrf_yes"
        ):
            return True, "favorable_subtype"

    rf = (task.get("route_context") or {}).get("route_features", {})
    if rf.get("exact_unique_symbol_anchor") or rf.get("unique_symbol_anchor"):
        return True, "symbol_anchor_support"
    if rf.get("symbol_regex_agree_span") or rf.get("rrf_anchor_agree_span"):
        return True, "span_agreement_signal"

    return False, "conservative_fallback"

def _gap_type(
    raw: dict[str, Any],
    task: dict[str, Any],
    small_window: int,
    medium_window: int,
) -> str:
    if not raw or not raw.get("path"):
        return "candidate_absent"
    gold_spans = p46._gold_spans(task["label"])
    if not gold_spans:
        return "candidate_absent"
    path = str(raw.get("path")).lower()
    same_file = [g for g in gold_spans if g[0] == path]
    if not same_file:
        return "candidate_absent"
    start = int(raw.get("start_line") or 0)
    end = int(raw.get("end_line") or 0)
    if start <= 0 or end <= 0:
        return "candidate_absent"

    for _, gs, ge in same_file:
        if end >= gs and start <= ge:
            return "adjacent_or_overlap"
        if end < gs and gs - end <= small_window:
            return "adjacent_or_overlap"
        if start > ge and start - ge <= small_window:
            return "adjacent_or_overlap"

    min_dist = min(
        min(abs(start - ge), abs(end - gs)) for _, gs, ge in same_file
    )
    if min_dist <= medium_window:
        return "same_file_near"
    return "same_file_far"

def _compute_variant_metrics(
    tasks: list[dict[str, Any]],
    strategy: str,
    variant: str,
    k: int,
    *,
    small_window: int,
    medium_window: int,
    medium_max_width: int,
) -> dict[str, Any]:
    if variant == "ast_symbol_trim_unavailable":
        return {"availability": "unavailable_no_source_root", "reason": "No repository checkout root is used; AST/source trim is unavailable by design."}

    all_tasks = [t for t in tasks if strategy in t.get("pools", {})]
    if not all_tasks:
        return {"availability": "missing_pool"}

    positive_tasks = [t for t in all_tasks if t["has_gold"] and t.get("has_gold_spans")]
    no_gold_tasks = [t for t in all_tasks if not t["has_gold"]]
    positive_denom = len(positive_tasks)
    no_gold_denom = len(no_gold_tasks)

    file_num = 0
    span_num = 0
    absent_num = 0
    frsw_num = 0
    repair_num = 0
    raw_file_count = 0
    no_gold_expanded_num = 0

    raw_budget = 0
    expanded_budget = 0
    candidate_count = 0
    width_cap_count = 0
    context_requests_accepted = 0
    context_requests_rejected_raw_preserved = 0
    expanded_candidate_count = 0

    raw_widths: list[int] = []
    expanded_widths: list[int] = []

    is_gate = variant == "request_more_context_gate_v0"

    for t in all_tasks:
        pool = t["pools"][strategy]
        items = pool[:k]
        raw_items: list[dict[str, Any]] = []
        var_items: list[dict[str, Any]] = []
        task_has_expansion = False
        is_positive = t["has_gold"] and t.get("has_gold_spans")

        for rank, ev in enumerate(items, start=1):
            raw = _raw_span(ev)
            raw_items.append(raw)
            raw_w = _span_width(raw)
            raw_budget += raw_w
            raw_widths.append(raw_w)
            candidate_count += 1

            if is_gate:
                accept, _reason = _request_more_context_gate_v0(ev, rank, t)
                if accept:
                    context_requests_accepted += 1
                    expanded_candidate_count += 1
                    var_span = _expand_span(ev, small_window)
                    expanded = True
                else:
                    context_requests_rejected_raw_preserved += 1
                    var_span = raw
                    expanded = False
            elif variant == "neighbor_window_small":
                var_span = _expand_span(ev, small_window)
                expanded = True
            elif variant == "neighbor_window_medium":
                if raw_w > medium_max_width:
                    var_span = raw
                    width_cap_count += 1
                    expanded = False
                else:
                    var_span = _expand_span(ev, medium_window)
                    expanded = True
            else:
                var_span = raw
                expanded = False

            var_items.append(var_span)
            var_w = _span_width(var_span)
            expanded_budget += var_w
            expanded_widths.append(var_w)
            if expanded:
                task_has_expansion = True

        if is_positive:
            raw_file_reach = p46._is_file_reached(raw_items, t["label"])
            raw_span_reach = p46._is_span_reached(raw_items, t["label"])
            if raw_file_reach:
                raw_file_count += 1
                if not raw_span_reach:
                    frsw_num += 1
                    if p46._is_span_reached(var_items, t["label"]):
                        repair_num += 1
            if p46._is_file_reached(var_items, t["label"]):
                file_num += 1
            else:
                absent_num += 1
            if p46._is_span_reached(var_items, t["label"]):
                span_num += 1
        else:
            # No-gold exposure counting.
            if is_gate:
                if task_has_expansion:
                    no_gold_expanded_num += 1
            elif variant != "raw_candidate_span" and task_has_expansion:
                no_gold_expanded_num += 1
            # raw_candidate_span intentionally contributes 0 expanded exposure.

    overfetch_ratio: float | None = None
    if raw_budget > 0:
        overfetch_ratio = round((expanded_budget - raw_budget) / raw_budget, 6)

    context_request_total = context_requests_accepted + context_requests_rejected_raw_preserved

    result: dict[str, Any] = {
        "availability": "available",
        "task_count": len(all_tasks),
        "positive_task_count": positive_denom,
        "no_gold_task_count": no_gold_denom,
        "candidate_count": candidate_count,
        "width_cap_count": width_cap_count,
        "gold_file_reach": {"numerator": file_num, "denominator": positive_denom, "rate": p46._rate(file_num, positive_denom)},
        "gold_span_reach": {"numerator": span_num, "denominator": positive_denom, "rate": p46._rate(span_num, positive_denom)},
        "candidate_absent_rate": {"numerator": absent_num, "denominator": positive_denom, "rate": p46._rate(absent_num, positive_denom)},
        "file_right_span_wrong_rate": {"numerator": frsw_num, "denominator": raw_file_count, "rate": p46._rate(frsw_num, raw_file_count)},
        "file_right_span_wrong_repair_rate": {"numerator": repair_num, "denominator": frsw_num, "rate": p46._rate(repair_num, frsw_num)},
        "span_expansion_gold_gain": {"numerator": repair_num, "denominator": positive_denom, "rate": p46._rate(repair_num, positive_denom)},
        "no_gold_expanded_candidate_rate": {"numerator": no_gold_expanded_num, "denominator": no_gold_denom, "rate": p46._rate(no_gold_expanded_num, no_gold_denom)},
        "raw_line_budget": raw_budget,
        "expanded_line_budget": expanded_budget,
        "mean_expanded_lines_per_candidate": p46._avg([float(w) for w in expanded_widths]) if expanded_widths else None,
        "p95_expanded_lines_per_candidate": _percentile(expanded_widths, 0.95),
        "expansion_overfetch_ratio": overfetch_ratio,
    }

    if is_gate:
        result.update({
            "context_requests_accepted": context_requests_accepted,
            "context_requests_rejected_raw_preserved": context_requests_rejected_raw_preserved,
            "context_request_total": context_request_total,
            "context_request_accept_rate": p46._rate(context_requests_accepted, context_request_total),
            "expanded_candidate_count": expanded_candidate_count,
        })

    return result

def compute_variant_map(
    tasks: list[dict[str, Any]],
    *,
    small_window: int,
    medium_window: int,
    medium_max_width: int,
) -> dict[str, Any]:
    by_strategy: dict[str, Any] = {}
    availability: dict[str, str] = {}

    for strategy in REACH_STRATEGIES:
        has_pool = any(strategy in t.get("pools", {}) for t in tasks)
        if not has_pool:
            availability[strategy] = "missing_pool"
            by_strategy[strategy] = {"availability": "missing_pool"}
            continue

        by_variant: dict[str, Any] = {}
        for variant in VARIANTS:
            if variant == "ast_symbol_trim_unavailable":
                by_variant[variant] = {"availability": "unavailable_no_source_root", "reason": "No repository checkout root is used; AST/source trim is unavailable by design."}
                continue
            by_k: dict[int, dict[str, Any]] = {}
            for k in K_VALUES:
                by_k[k] = _compute_variant_metrics(
                    tasks,
                    strategy,
                    variant,
                    k,
                    small_window=small_window,
                    medium_window=medium_window,
                    medium_max_width=medium_max_width,
                )
            by_variant[variant] = {"availability": "available", "by_k": by_k}

        by_strategy[strategy] = {"availability": "available", "by_variant": by_variant}
        availability[strategy] = "available"

    return {
        "by_strategy": by_strategy,
        "strategy_availability": availability,
        "variant_metrics_available": any(a == "available" for a in availability.values()),
    }

def compute_gap_type_breakdown(
    tasks: list[dict[str, Any]],
    *,
    small_window: int,
    medium_window: int,
) -> dict[str, Any]:
    by_strategy: dict[str, Any] = {}
    availability: dict[str, str] = {}

    for strategy in REACH_STRATEGIES:
        counts: dict[str, int] = defaultdict(int)
        denom = 0
        for t in tasks:
            if not (t["has_gold"] and t.get("has_gold_spans")):
                continue
            pool = t.get("pools", {}).get(strategy, [])
            if not pool:
                continue
            denom += 1
            top = pool[0]
            counts[_gap_type(top, t, small_window, medium_window)] += 1

        if denom == 0:
            availability[strategy] = "missing_positive_pool"
            by_strategy[strategy] = {"availability": "missing_positive_pool"}
        else:
            availability[strategy] = "available"
            gap_rates = {gt: {"numerator": counts[gt], "denominator": denom, "rate": p46._rate(counts[gt], denom)} for gt in GAP_TYPES}
            by_strategy[strategy] = {
                "availability": "available",
                "task_count": denom,
                "gap_rates": gap_rates,
            }

    return {
        "by_strategy": by_strategy,
        "strategy_availability": availability,
        "gap_breakdown_available": any(a == "available" for a in availability.values()),
    }

def compute_hypothetical_upper_bound(
    tasks: list[dict[str, Any]],
    *,
    small_window: int,
    k: int = 5,
) -> dict[str, Any]:
    # Hypothetical upper bound: not evidence.
    by_strategy: dict[str, Any] = {}
    for strategy in REACH_STRATEGIES:
        all_tasks = [t for t in tasks if strategy in t.get("pools", {})]
        if not all_tasks:
            by_strategy[strategy] = {"availability": "missing_pool"}
            continue

        positive_tasks = [t for t in all_tasks if t["has_gold"] and t.get("has_gold_spans")]
        positive_denom = len(positive_tasks)
        file_num = 0
        span_num = 0
        candidate_count = 0
        raw_budget = 0
        expanded_budget = 0

        for t in all_tasks:
            items = t["pools"][strategy][:k]
            for ev in items:
                candidate_count += 1
                raw = _raw_span(ev)
                raw_budget += _span_width(raw)
                expanded = _expand_span(ev, small_window)
                expanded_budget += _span_width(expanded)
            if t in positive_tasks:
                var_items = [_expand_span(ev, small_window) for ev in items]
                if p46._is_file_reached(var_items, t["label"]):
                    file_num += 1
                if p46._is_span_reached(var_items, t["label"]):
                    span_num += 1

        overfetch_ratio: float | None = None
        if raw_budget > 0:
            overfetch_ratio = round((expanded_budget - raw_budget) / raw_budget, 6)

        by_strategy[strategy] = {
            "availability": "available",
            "task_count": len(all_tasks),
            "positive_task_count": positive_denom,
            "candidate_count": candidate_count,
            "gold_file_reach": {"numerator": file_num, "denominator": positive_denom, "rate": p46._rate(file_num, positive_denom)},
            "gold_span_reach": {"numerator": span_num, "denominator": positive_denom, "rate": p46._rate(span_num, positive_denom)},
            "raw_line_budget": raw_budget,
            "expanded_line_budget": expanded_budget,
            "expansion_overfetch_ratio": overfetch_ratio,
            "context_requests_accepted": candidate_count,
            "context_requests_rejected_raw_preserved": 0,
            "context_request_total": candidate_count,
            "context_request_accept_rate": 1.0 if candidate_count > 0 else None,
            "expanded_candidate_count": candidate_count,
            "note": (
                "Hypothetical upper bound if the gate accepted every top-{} candidate using small_window expansion. "
                "This is not evidence and is not a real evaluation."
            ).format(k),
        }

    return {
        "k": k,
        "by_strategy": by_strategy,
        "note": "Hypothetical upper-bound section; not evidence.",
    }

def validate_public_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p47") != 0:
        errors.append("remote_calls_by_p47 must be 0")

    expected_flags = {
        "promotion_ready": False, "default_should_change": False, "evidencecore_semantics_changed": False,
        "candidate_not_fact": True, "run_phase_public_only": True, "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True, "source_reads_attempted": False, "raw_prompts_stored": False,
        "raw_query_stored": False, "raw_responses_stored": False, "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False, "raw_text_stored": False, "private_labels_committed": False,
        "provider_keys_in_artifact": False, "gold_spans_in_artifact": False,
    }
    for flag, expected in expected_flags.items():
        if report.get(flag) is not expected:
            errors.append(f"{flag} must be {expected}")

    if report.get("self_test") and report.get("not_quality_evidence") is not True:
        errors.append("self_test must set not_quality_evidence=true")

    for forbidden in ("tasks", "task_results", "per_task_results", "records", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    errors.extend(_reject_forbidden_keys(report))
    return errors

def build_report(
    tasks: list[dict[str, Any]],
    input_paths: list[Path],
    self_test: bool,
    elapsed_ms: int,
    status: str,
    reason: str | None,
    insufficient_paths: list[str] | None,
    *,
    small_window: int,
    medium_window: int,
    medium_max_width: int,
) -> dict[str, Any]:
    candidate_pool_availability = (
        "available" if tasks and all(t.get("has_candidate_pool") for t in tasks)
        else "partial" if tasks and any(t.get("has_candidate_pool") for t in tasks)
        else "missing_candidate_pool"
    )
    gold_span_availability = (
        "available" if tasks and all(t.get("has_gold_spans") for t in tasks if t["has_gold"])
        else "partial" if tasks and any(t.get("has_gold_spans") for t in tasks if t["has_gold"])
        else "missing_gold_spans"
    )
    reach_metrics_available = (
        candidate_pool_availability != "missing_candidate_pool"
        and gold_span_availability != "missing_gold_spans"
    )
    p31_h1_handoff_detected = bool(
        tasks and any(t.get("has_candidate_pool") and t.get("has_gold_spans") for t in tasks)
    )
    p33b_handoff_detected = bool(tasks and any(t.get("subtypes") for t in tasks))

    variant_metrics = compute_variant_map(
        tasks,
        small_window=small_window,
        medium_window=medium_window,
        medium_max_width=medium_max_width,
    )
    gap_breakdown = compute_gap_type_breakdown(
        tasks,
        small_window=small_window,
        medium_window=medium_window,
    )
    hypothetical = compute_hypothetical_upper_bound(
        tasks,
        small_window=small_window,
        k=5,
    )

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P47 Request-More-Context / Span-Geometry scaffold is ready; real per-task ephemeral P25 records are required."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(
                f"Self-test-only scaffold evaluated {len(tasks)} synthetic tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P47 span-geometry evaluation scored {len(tasks)} real ephemeral P25 records."
            )
        conclusion_lines.append(
            "P47 is SCORE-phase-only. Candidate pools and private gold spans were used only for aggregate metrics after RUN."
        )
        if reach_metrics_available:
            raw5 = variant_metrics["by_strategy"].get("candidate_baseline", {}).get("by_variant", {}).get("raw_candidate_span", {}).get("by_k", {}).get(5, {})
            gate5 = variant_metrics["by_strategy"].get("candidate_baseline", {}).get("by_variant", {}).get("request_more_context_gate_v0", {}).get("by_k", {}).get(5, {})
            conclusion_lines.append(
                f"Baseline@5 raw GoldSpanReach={_fmt_rate(raw5.get('gold_span_reach'))}, "
                f"gate GoldSpanReach={_fmt_rate(gate5.get('gold_span_reach'))}."
            )
        else:
            conclusion_lines.append(
                "Candidate pools or gold spans are missing; span-geometry metrics are unavailable and not faked."
            )
        conclusion_lines.append(
            "No source files were read and no AST/source trim was attempted."
        )
        conclusion_lines.append("No policy is promotion-ready or default-ready.")
        conclusion_lines.append(
            "The `hypothetical_upper_bound` section is explicitly not evidence."
        )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P47 Request-More-Context / Span-Geometry Diagnostic",
        "status": status,
        "status_reason": reason,
        "self_test": self_test,
        "not_quality_evidence": bool(self_test),
        "real_evaluation": bool(status == "ok" and not self_test),
        "input_sources": ["self_test"] if self_test else ["p25-policy-records-ephemeral-v1"],
        "input_source_count": len(input_paths),
        "insufficient_input_source_count": len(insufficient_paths or []),
        "promotion_ready": False, "default_should_change": False,
        "evidencecore_semantics_changed": False, "candidate_not_fact": True,
        "remote_calls_by_p47": 0, "run_phase_public_only": True,
        "labels_loaded_after_run": bool(any(t["has_gold"] for t in tasks)),
        "score_phase_only_metrics": True, "aggregate_only_public_artifact": True,
        "source_reads_attempted": False,
        "source_read_availability": "not_attempted_first_tranche",
        "source_read_availability_note": "P47 never reads source files; span geometry is computed from public candidate metadata only.",
        "ast_trim_availability": "unavailable_no_source_root",
        "ast_trim_availability_note": "AST/source trim is not implemented because no repository checkout root is used.",
        "raw_prompts_stored": False, "raw_query_stored": False, "raw_responses_stored": False,
        "raw_snippets_committed": False, "raw_snippets_sent_to_provider": False, "raw_text_stored": False,
        "private_labels_committed": False, "provider_keys_in_artifact": False, "gold_spans_in_artifact": False,
        "elapsed_ms": elapsed_ms, "small_window": small_window, "medium_window": medium_window,
        "medium_max_width": medium_max_width, "variants": list(VARIANTS), "k_values": list(K_VALUES),
        "task_count": len(tasks),
        "positive_task_count": sum(1 for t in tasks if t["has_gold"]),
        "no_gold_task_count": sum(1 for t in tasks if not t["has_gold"]),
        "positive_with_pools_count": sum(1 for t in tasks if t["has_gold"] and t.get("has_candidate_pool")),
        "positive_with_gold_spans_count": sum(1 for t in tasks if t["has_gold"] and t.get("has_gold_spans")),
        "candidate_pool_availability": candidate_pool_availability,
        "gold_span_availability": gold_span_availability,
        "reach_metrics_available": reach_metrics_available,
        "p31_h1_handoff_detected": p31_h1_handoff_detected,
        "p31_h1_handoff_detected_count": sum(1 for t in tasks if t.get("has_candidate_pool") and t.get("has_gold_spans")),
        "p33b_handoff_detected": p33b_handoff_detected,
        "p33b_handoff_detected_count": sum(1 for t in tasks if t.get("subtypes")),
        "variant_metrics_available": variant_metrics.get("variant_metrics_available", False),
        "gap_breakdown_available": gap_breakdown.get("gap_breakdown_available", False),
        "metrics": {"variant_map": variant_metrics, "gap_type_breakdown": gap_breakdown, "hypothetical_upper_bound": hypothetical},
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P47 public report validation failed: {errors}")
    return report

def _fmt_rate(x: Any) -> str:
    r = x.get("rate") if isinstance(x, dict) else None
    return f"{r:.4f}" if isinstance(r, (int, float)) else "n/a"

def _fmt_int(x: Any) -> str:
    return str(x) if isinstance(x, int) else "n/a"

def _fmt_scalar(x: Any) -> str:
    return f"{x:.4f}" if isinstance(x, (int, float)) else "n/a"

def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = ["# P47 Request-More-Context / Span-Geometry Diagnostic\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P47: {report['remote_calls_by_p47']}",
        f"- Source reads attempted: {report['source_reads_attempted']}",
        f"- Source read availability: `{report['source_read_availability']}`",
        f"- AST trim availability: `{report['ast_trim_availability']}`",
        f"- Candidate pool availability: `{report['candidate_pool_availability']}`",
        f"- Gold span availability: `{report['gold_span_availability']}`",
        f"- Reach metrics available: {report['reach_metrics_available']}",
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}\n",
    ])

    if report["status"] not in {"ok", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records.", ""])
        return "\n".join(lines)

    lines.extend([
        "## Purpose\n",
        "P47 measures whether enlarging candidate line ranges captures gold spans without reading source files "
        "or changing Rust/EvidenceCore semantics. It is a diagnostic-only, SCORE-phase follow-on that uses "
        "ephemeral metadata from P25/P46.",
        "",
        "## Methodology\n",
        "- Variants: raw candidate span, ±small neighbor window, ±medium neighbor window with width cap, conservative request-more-context gate, and AST/source-trim (unavailable).",
        "- Metrics are aggregate only: reach, absent rate, file-right-span-wrong, repair-after-expansion, line budgets, and gap-type breakdowns.",
        "- No source files are read; no remote model calls are made.",
        "- Gold spans are used only after RUN for aggregate SCORE-phase metrics.",
        "",
        "## Current placeholder findings\n",
        f"- This report is `{report['status']}`; do not use it as quality evidence.",
        f"- Reach metrics available: {report['reach_metrics_available']}.",
        f"- Source reads: `{report['source_reads_attempted']}`; AST/source trim: `{report['ast_trim_availability']}`.",
        "",
    ])

    lines.append("## Variant metrics by strategy and K\n")
    lines.append(
        "| Strategy | Variant | K | GoldFileReach | GoldSpanReach | CandidateAbsent | FRSW | FRSWRepair | GoldGain | NoGoldExpanded | LineBudget | MeanLines | P95Lines | Overfetch |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for strategy in REACH_STRATEGIES:
        block = report["metrics"]["variant_map"]["by_strategy"].get(strategy, {})
        if block.get("availability") != "available":
            lines.append(f"| {strategy} | n/a | - | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        for variant in VARIANTS:
            var_block = block["by_variant"].get(variant, {})
            if variant == "ast_symbol_trim_unavailable":
                lines.append(f"| {strategy} | {variant} | - | `{var_block.get('availability', 'unavailable')}` | - | - | - | - | - | - | - | - | - | - |")
                continue
            if var_block.get("availability") != "available":
                lines.append(f"| {strategy} | {variant} | - | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
                continue
            for k in K_VALUES:
                by_k = var_block["by_k"].get(k, {})
                lines.append(
                    f"| {strategy} | {variant} | {k} | {_fmt_rate(by_k.get('gold_file_reach'))} | "
                    f"{_fmt_rate(by_k.get('gold_span_reach'))} | {_fmt_rate(by_k.get('candidate_absent_rate'))} | "
                    f"{_fmt_rate(by_k.get('file_right_span_wrong_rate'))} | {_fmt_rate(by_k.get('file_right_span_wrong_repair_rate'))} | "
                    f"{_fmt_rate(by_k.get('span_expansion_gold_gain'))} | {_fmt_rate(by_k.get('no_gold_expanded_candidate_rate'))} | "
                    f"{_fmt_int(by_k.get('expanded_line_budget'))} | {_fmt_scalar(by_k.get('mean_expanded_lines_per_candidate'))} | "
                    f"{_fmt_scalar(by_k.get('p95_expanded_lines_per_candidate'))} | {_fmt_scalar(by_k.get('expansion_overfetch_ratio'))} |"
                )
    lines.append("")

    lines.append("## Request-more-context gate summary @5\n")
    lines.append("| Strategy | Accepted | Rejected (raw kept) | AcceptRate | ExpandedCandidates |")
    lines.append("|---|---:|---:|---:|---:|")
    for strategy in REACH_STRATEGIES:
        block = report["metrics"]["variant_map"]["by_strategy"].get(strategy, {})
        if block.get("availability") != "available":
            lines.append(f"| {strategy} | n/a | n/a | n/a | n/a |")
            continue
        gate_block = block["by_variant"].get("request_more_context_gate_v0", {})
        if gate_block.get("availability") != "available":
            lines.append(f"| {strategy} | n/a | n/a | n/a | n/a |")
            continue
        by5 = gate_block.get("by_k", {}).get(5, {})
        lines.append(
            f"| {strategy} | {_fmt_int(by5.get('context_requests_accepted'))} | "
            f"{_fmt_int(by5.get('context_requests_rejected_raw_preserved'))} | {_fmt_scalar(by5.get('context_request_accept_rate'))} | "
            f"{_fmt_int(by5.get('expanded_candidate_count'))} |"
        )

    lines.append("")

    lines.append("## Hypothetical upper bound (gate accepts every top-5 candidate)\n")
    lines.append("> This section is explicitly **not evidence**. It shows the small-window expansion upper bound on the same candidate set.\n")
    lines.append("| Strategy | CandidateCount | GoldFileReach | GoldSpanReach | LineBudget | Overfetch | AcceptRate |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    hyp = report["metrics"]["hypothetical_upper_bound"]
    for strategy in REACH_STRATEGIES:
        by_s = hyp["by_strategy"].get(strategy, {})
        if by_s.get("availability") != "available":
            lines.append(f"| {strategy} | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        lines.append(
            f"| {strategy} | {_fmt_int(by_s.get('candidate_count'))} | {_fmt_rate(by_s.get('gold_file_reach'))} | "
            f"{_fmt_rate(by_s.get('gold_span_reach'))} | {_fmt_int(by_s.get('expanded_line_budget'))} | "
            f"{_fmt_scalar(by_s.get('expansion_overfetch_ratio'))} | {_fmt_scalar(by_s.get('context_request_accept_rate'))} |"
        )
    lines.append("")

    lines.append("## Gap type breakdown (top candidate)\n")
    lines.append("| Strategy | Adjacent/Overlap | SameFileNear | SameFileFar | CandidateAbsent |")
    lines.append("|---|---:|---:|---:|---:|")
    gap = report["metrics"]["gap_type_breakdown"]
    for strategy in REACH_STRATEGIES:
        block = gap["by_strategy"].get(strategy, {})
        if block.get("availability") != "available":
            lines.append(f"| {strategy} | n/a | n/a | n/a | n/a |")
            continue
        rates = block.get("gap_rates", {})
        lines.append(
            f"| {strategy} | {_fmt_rate(rates.get('adjacent_or_overlap'))} | {_fmt_rate(rates.get('same_file_near'))} | "
            f"{_fmt_rate(rates.get('same_file_far'))} | {_fmt_rate(rates.get('candidate_absent'))} |"
        )
    lines.append("")

    lines.extend([
        "## Safety notes\n",
        "- No remote model calls were made during P47 evaluation.",
        "- No source files were read and no AST/source trim was attempted.",
        "- This report contains only aggregate counts/rates by strategy, variant, and gap type.",
        "- No task IDs, candidate IDs, paths, spans, gold spans, private labels, route features, snippets, prompts, responses, or provider keys are stored.",
        "- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, "
        "`candidate_not_fact=true`, `remote_calls_by_p47=0`, `source_reads_attempted=false`, "
        "`score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`.",
        "",
    ])
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser(description="P47 Request-More-Context / Span-Geometry Diagnostic")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    parser.add_argument("--small-window", type=int, default=3, help="Small neighbor window in lines.")
    parser.add_argument("--medium-window", type=int, default=10, help="Medium neighbor window in lines.")
    parser.add_argument("--medium-max-width", type=int, default=50, help="Maximum raw span width eligible for medium window.")
    args = parser.parse_args()

    if args.small_window < 0 or args.medium_window < 0 or args.medium_max_width < 0:
        parser.error("Window sizes and width cap must be non-negative.")

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_records: list[dict[str, Any]] = []

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_records = p46.make_self_test_records()
    elif args.input:
        input_paths = list(args.input)
        raw_records = p25.load_p21_inputs(input_paths, require_ephemeral_schema=True)
    else:
        parser.error("Specify --self-test or --input PATH [PATH ...]")

    status = "self_test_only" if args.self_test else "ok"
    reason: str | None = None
    insufficient_paths: list[str] = []
    task_records: list[dict[str, Any]] = []

    marker_reasons = {
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P47 span-geometry analysis.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P47 requires p25-policy-records-ephemeral-v1 input schema.",
    }
    for rec in raw_records:
        marker = next((m for m in marker_reasons if rec.get(m)), None)
        if marker:
            status = "insufficient_task_detail"
            reason = marker_reasons[marker]
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        task_records.append(rec)

    if not task_records and status == "ok":
        status = "insufficient_task_detail"
        reason = "No per-task records found."

    normalized_tasks = [nt for nt in (p46.normalize_task(raw) for raw in task_records) if nt]

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P47 normalization."

    elapsed_ms = int((time.monotonic() - start) * 1000)

    report = build_report(
        normalized_tasks,
        input_paths,
        self_test=args.self_test,
        elapsed_ms=elapsed_ms,
        status=status,
        reason=reason,
        insufficient_paths=insufficient_paths,
        small_window=args.small_window,
        medium_window=args.medium_window,
        medium_max_width=args.medium_max_width,
    )

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P47 report written to {args.out}")
    print(f"P47 markdown written to {args.doc}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
