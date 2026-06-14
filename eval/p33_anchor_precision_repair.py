#!/usr/bin/env python3
"""P33 Reach-Preserving Precision Anchor Repair — deterministic diagnostic scaffold.

P33 studies how local anchor signals (symbol, regex, RRF anchor agreement, query
noise, public bucket/tags) correlate with candidate reach and span cost. It is
diagnostic-only and SCORE-phase-only: it does not change Rust core, EvidenceCore,
or default strategies; it makes no remote calls; and labels are loaded only after
RUN for aggregate metrics.

Inputs:
- ``--self-test`` generates synthetic private task records in memory.
- ``--input PATH [PATH ...]`` reads P21/P31-H1/P30 ephemeral SCORE records. P33
  needs ``p31_candidate_pools``, ``p31_score_gold``, ``route_features``, and
  public ``task_bucket``/``task_risk_tags``. When candidate pools or gold spans
  are missing, buckets are reported as ``availability=missing_pool`` or
  ``status=not_measured`` rather than fabricating zeros.

Public artifacts are aggregate-only: no per-task rows, task IDs, raw queries,
snippets, prompts, responses, candidate paths/spans, gold spans, route features,
private labels, or provider fields.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))
import p25_bucket_policy as p25
from p31_candidate_reach_ceiling import is_file_reached, is_span_reached_by_any

SCHEMA_VERSION = "p33-anchor-precision-repair-report-v1"
GENERATED_BY = "eval/p33_anchor_precision_repair.py"

DEFAULT_OUT = Path("artifacts/p33_anchor_precision_repair/p33_anchor_precision_repair_report.json")
DEFAULT_DOC = Path("docs/en/p33-anchor-precision-repair.md")

K = 5
REACH_STRATEGIES = [
    "candidate_baseline",
    "rrf_primary",
    "symbol_regex_union",
    "llm_span_narrow",
    "llm_filter",
    "llm_abstain_filter",
]

# Aggregate bucket names based on pre-SCORE public/observable features.
BUCKET_NAMES: list[str] = [
    "exact_unique_symbol_anchor",
    "unique_symbol_anchor",
    "symbol_anchor_only",
    "regex_anchor_only",
    "symbol_regex_agree_span",
    "symbol_regex_agree_file",
    "symbol_regex_disagree",
    "rrf_anchor_agree_span",
    "rrf_anchor_agree_file",
    "rrf_unbacked",
    "positive_bucket",
    "ambiguous_bucket",
    "negative_bucket",
    "hard_distractor_tag",
    "dense_false_positive_tag",
    "query_noise_low",
    "query_noise_medium",
    "query_noise_high",
    "symbol_regex_agree_span_low_risk",
    "symbol_regex_agree_file_only",
    "symbol_only",
    "regex_only",
    "rrf_span_backed",
    "rrf_file_backed_only",
    "negative_or_ambiguous_with_anchor",
]

# Keys that must never appear in the public JSON artifact.
FORBIDDEN_PUBLIC_KEYS = {
    "query",
    "raw_query",
    "snippet",
    "prompt",
    "response",
    "gold",
    "gold_spans",
    "label",
    "labels",
    "private_labels",
    "private_label",
    "label_path",
    "task_id",
    "base_url",
    "api_key",
    "api_token",
    "api_secret",
    "endpoint",
    "provider_key",
    "embedding_api_key",
    "llm_api_key",
    "candidate_path",
    "candidate_paths",
    "candidate_span",
    "candidate_spans",
    "candidate_pool",
    "p31_candidate_pools",
    "p31_score_gold",
    "raw_candidates",
    "route_features",
    "source_text",
    "excerpt",
    "authorization",
    "evidence_raw",
    "path",
    "start_line",
    "end_line",
    "content_sha",
    "score",
    "channels",
    "rank",
}

# Safety/report metadata keys that are allowed despite sharing names with concepts
# above, because they are boolean flags or aggregate identifiers.
SAFETY_FLAG_KEYS = {
    "schema_version",
    "generated_at",
    "generated_by",
    "stage",
    "status",
    "status_reason",
    "self_test",
    "not_quality_evidence",
    "real_evaluation",
    "input_paths",
    "input_sources",
    "insufficient_input_paths",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "candidate_not_fact",
    "remote_calls_by_p33",
    "run_phase_public_only",
    "labels_loaded_after_run",
    "score_phase_only_metrics",
    "aggregate_only_public_artifact",
    "raw_prompts_stored",
    "raw_query_stored",
    "raw_responses_stored",
    "raw_snippets_committed",
    "raw_snippets_sent_to_provider",
    "raw_text_stored",
    "private_labels_committed",
    "provider_keys_in_artifact",
    "gold_spans_in_artifact",
    "p31_h1_handoff_detected",
    "p31_h1_handoff_detected_count",
    "p33_available",
    "p33_input_available",
    "p33_reason",
    "elapsed_ms",
    "task_count",
    "positive_task_count",
    "no_gold_task_count",
    "positive_with_pools_count",
    "metrics",
    "bucket_taxonomy",
    "calibration_matrix",
    "p33_to_p32_handoff",
    "diagnostic_class",
    "validation",
    "reach_metrics_available",
    "outcome_metrics_available",
    "anchor_strength",
    "risk_level",
    "rrf_backing_level",
    "bucket",
    "strategy",
    "combination",
    "direction",
    "pair",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_float(value: Any) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value == int(value):
            return int(value)
        return None
    try:
        v = int(value)
        return v
    except (TypeError, ValueError):
        return None


def _rate(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def _ratio(num: int, den: int) -> float | None:
    if den <= 0 or num < 0:
        return None
    return round(num / den, 6)


def _strategy_has_pool(t: dict[str, Any], strategy: str) -> bool:
    return strategy in (t.get("candidate_pool") or {})


def normalize_label(raw: dict[str, Any]) -> dict[str, Any]:
    gold_spans: list[dict[str, Any]] = []
    for gs in raw.get("gold_spans") or []:
        if isinstance(gs, dict):
            gold_spans.append(gs)
    gold_files = {str(gs.get("path") or gs.get("file") or "").lower() for gs in gold_spans if gs.get("path") or gs.get("file")}
    return {"has_gold": bool(gold_spans), "gold_spans": gold_spans, "gold_files": gold_files}


def normalize_task(raw: dict[str, Any]) -> dict[str, Any] | None:
    tid = raw.get("task_id") or raw.get("test_id")
    if not tid:
        return None

    task_bucket = p25.sanitize_public_bucket(raw.get("task_bucket", "unknown"))
    risk_tags = raw.get("task_risk_tags") or []
    if isinstance(risk_tags, str):
        risk_tags = [risk_tags]
    if not isinstance(risk_tags, list):
        risk_tags = []
    risk_tags = p25.sanitize_public_tags(risk_tags)

    label = normalize_label(raw.get("p31_score_gold") or raw.get("label") or {})
    score_group = raw.get("score_group")
    if score_group == "positive":
        label["has_gold"] = True
    elif score_group == "no_gold":
        label["has_gold"] = False

    pools = raw.get("p31_candidate_pools")
    candidate_pool: dict[str, list[dict[str, Any]]] = {}
    if isinstance(pools, dict):
        for strategy in REACH_STRATEGIES:
            items = pools.get(strategy)
            if isinstance(items, list):
                candidate_pool[strategy] = list(items)

    route_features = raw.get("route_features") or {}

    outcomes: dict[str, Any] = {}
    for strategy in REACH_STRATEGIES:
        src = raw.get(strategy)
        if isinstance(src, dict):
            outcomes[strategy] = {
                "file_recall_at_5": _as_float(src.get("file_recall_at_5")),
                "span_f0_5": _as_float(src.get("span_f0_5")),
                "primary_false_positive_rate": _as_float(src.get("primary_false_positive_rate")),
                "added_gold_span": _as_int(src.get("added_gold_span")),
                "added_false_span": _as_int(src.get("added_false_span")),
                "abstained": bool(src.get("abstained", False)),
            }

    return {
        "task_id": tid,
        "repo_id": raw.get("repo_id"),
        "task_bucket": task_bucket,
        "task_risk_tags": risk_tags,
        "has_gold": bool(label.get("has_gold", False)),
        "has_gold_spans": bool(label.get("gold_spans")),
        "label": label,
        "candidate_pool": candidate_pool,
        "has_candidate_pool": bool(candidate_pool),
        "route_features": route_features,
        "outcomes": outcomes,
        "p31_h1_handoff_detected": bool(raw.get("p31_candidate_pools") and raw.get("p31_score_gold")),
    }


def _has_route_feature(t: dict[str, Any], name: str) -> bool:
    return bool((t.get("route_features") or {}).get(name))


def _noise_level(t: dict[str, Any]) -> str:
    qn = _as_float((t.get("route_features") or {}).get("query_noise"))
    if qn is None:
        return "unknown"
    if qn <= 0.0:
        return "low"
    if qn >= 1.0:
        return "high"
    return "medium"


def assign_buckets(t: dict[str, Any]) -> set[str]:
    """Assign a task to aggregate anchor taxonomy buckets from pre-SCORE features."""
    rf = t.get("route_features") or {}
    tags = set(t.get("task_risk_tags") or [])
    bucket = t.get("task_bucket", "unknown")
    buckets: set[str] = set()

    # Anchor primitives
    exact_unique = bool(rf.get("exact_unique_symbol_anchor"))
    unique_sym = bool(rf.get("unique_symbol_anchor")) or "unique_symbol" in tags
    sym_anchor = bool(rf.get("symbol_anchor")) or "symbol_anchor" in tags or "exact_symbol" in tags
    regex_anchor = bool(rf.get("regex_anchor")) or "regex_anchor" in tags
    sr_agree_file = bool(rf.get("symbol_regex_agree_file"))
    sr_agree_span = bool(rf.get("symbol_regex_agree_span"))
    rrf_anchor_file = bool(rf.get("rrf_anchor_agree_file"))
    rrf_anchor_span = bool(rf.get("rrf_anchor_agree_span"))
    rrf_backed = bool(rf.get("rrf_backed_by_anchor"))

    if exact_unique:
        buckets.add("exact_unique_symbol_anchor")
    if unique_sym:
        buckets.add("unique_symbol_anchor")
    if sym_anchor and not regex_anchor:
        buckets.add("symbol_anchor_only")
    if regex_anchor and not sym_anchor:
        buckets.add("regex_anchor_only")
    if sr_agree_span:
        buckets.add("symbol_regex_agree_span")
    elif sr_agree_file:
        buckets.add("symbol_regex_agree_file")
    elif sym_anchor and regex_anchor:
        buckets.add("symbol_regex_disagree")
    if rrf_anchor_span:
        buckets.add("rrf_anchor_agree_span")
    elif rrf_anchor_file:
        buckets.add("rrf_anchor_agree_file")
    elif not rrf_backed:
        buckets.add("rrf_unbacked")

    # Public bucket classes
    if bucket == "positive":
        buckets.add("positive_bucket")
    if bucket == "ambiguous":
        buckets.add("ambiguous_bucket")
    if bucket == "negative":
        buckets.add("negative_bucket")
    if "hard_distractor" in tags:
        buckets.add("hard_distractor_tag")
    if "dense_false_positive" in tags:
        buckets.add("dense_false_positive_tag")

    # Query noise
    noise = _noise_level(t)
    if noise == "low":
        buckets.add("query_noise_low")
    elif noise == "medium":
        buckets.add("query_noise_medium")
    elif noise == "high":
        buckets.add("query_noise_high")

    # Composites
    low_risk = bucket in {"positive"} and "hard_distractor" not in tags and "dense_false_positive" not in tags
    if sr_agree_span and low_risk:
        buckets.add("symbol_regex_agree_span_low_risk")
    if sr_agree_file and not sr_agree_span:
        buckets.add("symbol_regex_agree_file_only")
    if sym_anchor and not regex_anchor:
        buckets.add("symbol_only")
    if regex_anchor and not sym_anchor:
        buckets.add("regex_only")
    if rrf_anchor_span:
        buckets.add("rrf_span_backed")
    elif rrf_anchor_file:
        buckets.add("rrf_file_backed_only")
    if bucket in {"negative", "ambiguous"} and (sym_anchor or regex_anchor or rrf_backed):
        buckets.add("negative_or_ambiguous_with_anchor")

    return buckets


def score_group(task: dict[str, Any]) -> str:
    return "positive" if task["has_gold"] else "no_gold"


def compute_bucket_metrics(tasks: list[dict[str, Any]], strategy: str = "symbol_regex_union") -> dict[str, Any]:
    """Aggregate bucket-level diagnostics at K=5 for a chosen strategy."""
    bucket_to_tasks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in tasks:
        for b in assign_buckets(t):
            bucket_to_tasks[b].append(t)

    result: dict[str, Any] = {}
    for bucket in BUCKET_NAMES:
        group = bucket_to_tasks.get(bucket, [])
        if not group:
            result[bucket] = {"availability": "missing_bucket", "task_count": 0}
            continue
        m: dict[str, Any] = {
            "task_count": len(group),
            "positive_count": sum(1 for t in group if t["has_gold"]),
            "no_gold_count": sum(1 for t in group if not t["has_gold"]),
        }
        m.update(_metrics_for_strategy(group, strategy))
        m["diagnostic_class"] = _diagnostic_class(m)
        result[bucket] = m
    return result


def _diagnostic_class(m: dict[str, Any]) -> str:
    """Diagnostic classification based on observed aggregate signals only."""
    if m["task_count"] < 10 or m["positive_count"] < 10:
        return "insufficient_denominator"
    # Positive reach and low false cost -> safe primary candidate observation
    gr = m.get("gold_span_reach", {}).get("rate")
    fp = m.get("mean_primary_false_positive_rate")
    if gr is not None and gr >= 0.8 and (fp is None or fp <= 0.05):
        return "primary_candidate_safe_observed"
    if m.get("added_false_span", 0) == 0 and m.get("added_gold_span", 0) == 0:
        return "supporting_only_observed"
    if fp is not None and fp >= 0.30:
        return "blocked_high_false_cost"
    if m.get("false_per_gold") is not None and m.get("false_per_gold", 0) > 1.0:
        return "needs_budget_guard"
    return "needs_budget_guard"


def _metrics_for_strategy(group: list[dict[str, Any]], strategy: str) -> dict[str, Any]:
    """Aggregate metrics for a group of tasks evaluated against a candidate strategy."""
    positive = [t for t in group if t["has_gold"] and t.get("has_gold_spans")]
    have_pool = [t for t in positive if _strategy_has_pool(t, strategy)]

    file_num = span_num = frsw_num = 0
    for t in have_pool:
        items = t.get("candidate_pool", {}).get(strategy, [])[:K]
        file_reach = is_file_reached(items, t["label"])
        span_reach = is_span_reached_by_any(items, t["label"])
        if file_reach:
            file_num += 1
        if span_reach:
            span_num += 1
        if file_reach and not span_reach:
            frsw_num += 1
    denom = len(have_pool)

    # Outcome aggregates over the same strategy when present.
    gold_spans = 0
    false_spans = 0
    span_f_values: list[float] = []
    pfp_values: list[float] = []
    for t in group:
        out = t["outcomes"].get(strategy, {})
        if isinstance(out.get("added_gold_span"), int):
            gold_spans += out["added_gold_span"]
        if isinstance(out.get("added_false_span"), int):
            false_spans += out["added_false_span"]
        if out.get("span_f0_5") is not None:
            span_f_values.append(out["span_f0_5"])
        if out.get("primary_false_positive_rate") is not None:
            pfp_values.append(out["primary_false_positive_rate"])

    return {
        "availability": "available" if denom > 0 else "not_measured",
        "strategy": strategy,
        "gold_file_reach": {"numerator": file_num, "denominator": denom, "rate": _rate(file_num, denom)},
        "gold_span_reach": {"numerator": span_num, "denominator": denom, "rate": _rate(span_num, denom)},
        "file_right_span_wrong_rate": {"numerator": frsw_num, "denominator": file_num, "rate": _rate(frsw_num, file_num)},
        "added_gold_span": gold_spans,
        "added_false_span": false_spans,
        "false_per_gold": _ratio(false_spans, gold_spans) if gold_spans > 0 else None,
        "gold_per_false": _ratio(gold_spans, false_spans) if false_spans > 0 else None,
        "net_span_value_1x": gold_spans - false_spans,
        "net_span_value_2x": gold_spans - (2 * false_spans),
        "mean_span_f0_5": round(sum(span_f_values) / len(span_f_values), 6) if span_f_values else None,
        "mean_primary_false_positive_rate": round(sum(pfp_values) / len(pfp_values), 6) if pfp_values else None,
    }


def _anchor_strength(t: dict[str, Any]) -> int:
    """Encode local anchor strength: none/symbol_or_regex_only/file_agreement/span_agreement/exact_unique_symbol_span_agreement."""
    rf = t.get("route_features") or {}
    if rf.get("exact_unique_symbol_anchor"):
        return 4
    if rf.get("symbol_regex_agree_span") or rf.get("rrf_anchor_agree_span"):
        return 3
    if rf.get("symbol_regex_agree_file") or rf.get("rrf_anchor_agree_file"):
        return 2
    if rf.get("symbol_anchor") or rf.get("regex_anchor"):
        return 1
    return 0


def _risk_level(t: dict[str, Any]) -> int:
    bucket = t.get("task_bucket", "unknown")
    tags = set(t.get("task_risk_tags") or [])
    if bucket == "negative" or "hard_distractor" in tags or "dense_false_positive" in tags:
        return 2
    if bucket == "ambiguous":
        return 1
    return 0


def _rrf_backing_level(t: dict[str, Any]) -> int:
    """Encode RRF backing: none/file-only/span."""
    rf = t.get("route_features") or {}
    if rf.get("rrf_anchor_agree_span"):
        return 2
    if rf.get("rrf_anchor_agree_file") or rf.get("rrf_backed_by_anchor"):
        return 1
    return 0


def compute_calibration_matrix(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """3D calibration matrix over anchor_strength, risk_level, rrf_backing_level."""
    cells: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for t in tasks:
        cells[(_anchor_strength(t), _risk_level(t), _rrf_backing_level(t))].append(t)

    matrix: dict[str, Any] = {}
    monotonic_checks: dict[str, Any] = {"file_reach_non_increasing_with_risk": [], "span_reach_non_increasing_with_risk": []}
    for a in range(5):
        for r in range(3):
            for s in range(3):
                group = cells.get((a, r, s), [])
                key = f"a{a}_r{r}_s{s}"
                if not group:
                    matrix[key] = {"availability": "empty", "task_count": 0}
                    continue
                m: dict[str, Any] = {
                    "task_count": len(group),
                    "positive_count": sum(1 for t in group if t["has_gold"]),
                    "no_gold_count": sum(1 for t in group if not t["has_gold"]),
                    "anchor_strength": a,
                    "risk_level": r,
                    "rrf_backing_level": s,
                }
                m.update(_metrics_for_strategy(group, "symbol_regex_union"))
                m["diagnostic_class"] = _diagnostic_class(m)
                matrix[key] = m

    # Naive monotonic sanity: file/span reach should not increase with risk within same anchor/support.
    for a in range(5):
        for s in range(3):
            file_rates = []
            span_rates = []
            for r in range(3):
                m = matrix.get(f"a{a}_r{r}_s{s}", {})
                if m.get("availability") == "available":
                    file_rates.append((r, m.get("gold_file_reach", {}).get("rate")))
                    span_rates.append((r, m.get("gold_span_reach", {}).get("rate")))
            for i in range(1, len(file_rates)):
                prev_r, prev_v = file_rates[i - 1]
                cur_r, cur_v = file_rates[i]
                if prev_v is not None and cur_v is not None and cur_v > prev_v + 1e-6:
                    monotonic_checks["file_reach_non_increasing_with_risk"].append(f"a{a}_s{s}: r{prev_r}->{cur_r}")
            for i in range(1, len(span_rates)):
                prev_r, prev_v = span_rates[i - 1]
                cur_r, cur_v = span_rates[i]
                if prev_v is not None and cur_v is not None and cur_v > prev_v + 1e-6:
                    monotonic_checks["span_reach_non_increasing_with_risk"].append(f"a{a}_s{s}: r{prev_r}->{cur_r}")
    return {"cells": matrix, "monotonic_sanity": monotonic_checks}


def compute_p33_to_p32_handoff(bucket_metrics: dict[str, Any]) -> dict[str, Any]:
    """Aggregate budget-candidate suggestions for P32, not a frozen policy."""
    primary_safe: list[str] = []
    supporting_only: list[str] = []
    needs_budget: list[str] = []
    blocked: list[str] = []
    for bucket, m in bucket_metrics.items():
        if m.get("availability") != "available" or m.get("task_count", 0) == 0:
            continue
        dc = m.get("diagnostic_class")
        if dc == "primary_candidate_safe_observed":
            primary_safe.append(bucket)
        elif dc == "supporting_only_observed":
            supporting_only.append(bucket)
        elif dc == "blocked_high_false_cost":
            blocked.append(bucket)
        else:
            needs_budget.append(bucket)
    return {
        "frozen_policy": False,
        "budget_candidate_buckets": {
            "primary_candidate_safe_observed": sorted(primary_safe),
            "supporting_only_observed": sorted(supporting_only),
            "needs_budget_guard": sorted(needs_budget),
            "blocked_high_false_cost": sorted(blocked),
        },
    }


def _reject_forbidden_keys(obj: Any, path: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = str(key).lower()
            if key_lower in {k.lower() for k in FORBIDDEN_PUBLIC_KEYS} and key not in SAFETY_FLAG_KEYS:
                violations.append(f"{path}.{key}" if path else str(key))
            violations.extend(_reject_forbidden_keys(value, f"{path}.{key}" if path else str(key)))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, f"{path}[{idx}]"))
    return violations


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p33") != 0:
        errors.append("remote_calls_by_p33 must be 0")
    if report.get("promotion_ready") is not False:
        errors.append("promotion_ready must be false")
    if report.get("default_should_change") is not False:
        errors.append("default_should_change must be false")
    if report.get("evidencecore_semantics_changed") is not False:
        errors.append("evidencecore_semantics_changed must be false")
    if report.get("candidate_not_fact") is not True:
        errors.append("candidate_not_fact must be true")
    if report.get("score_phase_only_metrics") is not True:
        errors.append("score_phase_only_metrics must be true")
    if report.get("aggregate_only_public_artifact") is not True:
        errors.append("aggregate_only_public_artifact must be true")
    if report.get("self_test") and report.get("not_quality_evidence") is not True:
        errors.append("self_test must set not_quality_evidence=true")

    # No per-task public rows.
    for forbidden in ("tasks", "task_results", "per_task_results", "records", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    def _validate_bucket_block(prefix: str, bucket_metrics: dict[str, Any]) -> None:
        for bucket, m in bucket_metrics.items():
            if m.get("availability") != "available":
                continue
            for metric_name in ("gold_file_reach", "gold_span_reach", "file_right_span_wrong_rate"):
                mm = m.get(metric_name, {})
                rate = mm.get("rate")
                num = mm.get("numerator")
                den = mm.get("denominator")
                if rate is not None and not (0.0 <= rate <= 1.0 + 1e-9):
                    errors.append(f"{prefix} {bucket} {metric_name} rate out of range: {rate}")
                if not isinstance(num, int) or num < 0:
                    errors.append(f"{prefix} {bucket} {metric_name} numerator invalid: {num}")
                if not isinstance(den, int) or den < 0:
                    errors.append(f"{prefix} {bucket} {metric_name} denominator invalid: {den}")
                if den is not None and num is not None and num > den:
                    errors.append(f"{prefix} {bucket} {metric_name} numerator exceeds denominator")

            # File-right-span-wrong denominator equals gold-file-reach numerator.
            gr = m.get("gold_file_reach", {})
            frsw = m.get("file_right_span_wrong_rate", {})
            if frsw.get("denominator") is not None and gr.get("numerator") is not None:
                if frsw["denominator"] != gr["numerator"]:
                    errors.append(f"{prefix} {bucket} file_right_span_wrong denominator must equal gold_file_reach numerator")

            added_gold = m.get("added_gold_span")
            added_false = m.get("added_false_span")
            if not isinstance(added_gold, int) or added_gold < 0:
                errors.append(f"{prefix} {bucket} added_gold_span invalid")
            if not isinstance(added_false, int) or added_false < 0:
                errors.append(f"{prefix} {bucket} added_false_span invalid")

            # Cost ratios must not be Infinity/NaN; None is allowed for missing denominators.
            for ratio_name in ("false_per_gold", "gold_per_false"):
                val = m.get(ratio_name)
                if val is not None and (math.isinf(val) or math.isnan(val)):
                    errors.append(f"{prefix} {bucket} {ratio_name} must not be infinite/NaN")

    _validate_bucket_block("bucket", report.get("metrics", {}).get("bucket_taxonomy", {}))
    _validate_bucket_block("baseline", report.get("metrics", {}).get("baseline_comparison", {}))

    # Forbidden-key scan.
    errors.extend(_reject_forbidden_keys(report))
    return errors


def make_self_test_records() -> list[dict[str, Any]]:
    """Synthetic private records covering anchor taxonomy buckets."""
    def pool(items: list[tuple[str, int, int]]) -> list[dict[str, Any]]:
        return [{"rank": i + 1, "path": p, "start_line": s, "end_line": e} for i, (p, s, e) in enumerate(items)]

    def make(
        tid: str,
        repo: str,
        bucket: str,
        tags: list[str],
        rf: dict[str, Any],
        pools: dict[str, list[dict[str, Any]]],
        gold_spans: list[dict[str, Any]],
        outcomes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        score_group = "positive" if gold_spans else "no_gold"
        return {
            "task_id": tid,
            "repo_id": repo,
            "task_bucket": bucket,
            "task_risk_tags": tags,
            "score_group": score_group,
            "route_features": rf,
            "p31_candidate_pools": pools,
            "p31_score_gold": {"has_gold": bool(gold_spans), "score_group": score_group, "gold_spans": gold_spans},
            **(outcomes or {}),
        }

    tasks: list[dict[str, Any]] = []

    # Exact unique symbol anchor, positive, reaches gold.
    tasks.append(make(
        "p33-st-001", "py_flask", "positive", ["high_confidence"],
        {
            "exact_unique_symbol_anchor": True,
            "unique_symbol_anchor": True,
            "symbol_anchor": True,
            "regex_anchor": True,
            "symbol_regex_agree_span": True,
            "symbol_regex_agree_file": True,
            "rrf_anchor_agree_span": True,
            "rrf_anchor_agree_file": True,
            "rrf_backed_by_anchor": True,
            "query_noise": 0.0,
            "candidate_count": 3,
            "candidate_support_exists": True,
        },
        {
            "candidate_baseline": pool([("src/app.py", 10, 15)]),
            "symbol_regex_union": pool([("src/app.py", 10, 15)]),
            "rrf_primary": pool([("src/app.py", 10, 15)]),
        },
        [{"path": "src/app.py", "start_line": 10, "end_line": 15}],
        {
            "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.30, "primary_false_positive_rate": 0.0, "added_gold_span": 1, "added_false_span": 0},
            "symbol_regex_union": {"file_recall_at_5": 1.0, "span_f0_5": 0.30, "primary_false_positive_rate": 0.0, "added_gold_span": 1, "added_false_span": 0},
        },
    ))

    # Symbol anchor only, file reach but span wrong.
    tasks.append(make(
        "p33-st-002", "py_flask", "positive", ["symbol_anchor"],
        {
            "symbol_anchor": True,
            "regex_anchor": False,
            "symbol_regex_agree_span": False,
            "symbol_regex_agree_file": False,
            "rrf_anchor_agree_span": False,
            "rrf_anchor_agree_file": False,
            "rrf_backed_by_anchor": False,
            "query_noise": 0.0,
            "candidate_count": 2,
            "candidate_support_exists": True,
        },
        {
            "candidate_baseline": pool([("src/app.py", 1, 5)]),
            "symbol_regex_union": pool([("src/app.py", 1, 5)]),
        },
        [{"path": "src/app.py", "start_line": 10, "end_line": 15}],
        {
            "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.10, "primary_false_positive_rate": 0.20, "added_gold_span": 0, "added_false_span": 2},
            "symbol_regex_union": {"file_recall_at_5": 1.0, "span_f0_5": 0.10, "primary_false_positive_rate": 0.20, "added_gold_span": 0, "added_false_span": 2},
        },
    ))

    # Negative bucket with dense false positive tag, no gold, high false spans.
    tasks.append(make(
        "p33-st-003", "js_express", "negative", ["negative", "dense_false_positive"],
        {
            "symbol_anchor": False,
            "regex_anchor": False,
            "symbol_regex_agree_span": False,
            "symbol_regex_agree_file": False,
            "rrf_anchor_agree_span": False,
            "rrf_anchor_agree_file": False,
            "rrf_backed_by_anchor": False,
            "query_noise": 1.0,
            "candidate_count": 2,
            "candidate_support_exists": True,
            "dense_support_present": True,
        },
        {
            "candidate_baseline": pool([("src/noise.py", 1, 5)]),
        },
        [],
        {"candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.50, "added_gold_span": 0, "added_false_span": 5}},
    ))

    # Regex anchor only, ambiguous bucket, no reach.
    tasks.append(make(
        "p33-st-004", "js_express", "ambiguous", ["ambiguous"],
        {
            "symbol_anchor": False,
            "regex_anchor": True,
            "symbol_regex_agree_span": False,
            "symbol_regex_agree_file": False,
            "rrf_anchor_agree_span": False,
            "rrf_anchor_agree_file": False,
            "rrf_backed_by_anchor": False,
            "query_noise": 0.5,
            "candidate_count": 1,
            "candidate_support_exists": True,
        },
        {
            "candidate_baseline": pool([("src/ambig.py", 50, 55)]),
        },
        [{"path": "src/ambig.py", "start_line": 20, "end_line": 25}],
        {"candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "added_gold_span": 0, "added_false_span": 0}},
    ))

    # Outcome-only task to exercise fallback/missing pool path.
    tasks.append({
        "task_id": "p33-st-005",
        "repo_id": "js_express",
        "task_bucket": "ambiguous",
        "task_risk_tags": ["ambiguous"],
        "score_group": "positive",
        "route_features": {"symbol_anchor": False, "query_noise": 0.0},
        "p31_score_gold": {"has_gold": True, "score_group": "positive", "gold_spans": [{"path": "src/ambig.py", "start_line": 20, "end_line": 25}]},
        "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.18, "primary_false_positive_rate": 0.12, "added_gold_span": 1, "added_false_span": 2},
    })

    return tasks


def build_report(
    tasks: list[dict[str, Any]],
    input_paths: list[Path],
    self_test: bool,
    elapsed_ms: int,
    status: str,
    reason: str | None,
    insufficient_paths: list[str] | None,
) -> dict[str, Any]:
    p31_h1_handoff_detected = any(t.get("p31_h1_handoff_detected") for t in tasks)
    positive = [t for t in tasks if t["has_gold"]]
    positive_with_pools = [t for t in positive if t.get("has_candidate_pool")]
    p33_available = p31_h1_handoff_detected and bool(positive_with_pools)

    anchor_strategy = "symbol_regex_union"
    baseline_strategy = "candidate_baseline"

    bucket_taxonomy: dict[str, Any] = {}
    baseline_comparison: dict[str, Any] = {}
    calibration_matrix: dict[str, Any] = {"cells": {}, "monotonic_sanity": {}}
    p32_handoff: dict[str, Any] = {"frozen_policy": False, "budget_candidate_buckets": {}}
    if p33_available:
        bucket_taxonomy = compute_bucket_metrics(tasks, strategy=anchor_strategy)
        baseline_comparison = compute_bucket_metrics(tasks, strategy=baseline_strategy)
        calibration_matrix = compute_calibration_matrix(tasks)
        p32_handoff = compute_p33_to_p32_handoff(bucket_taxonomy)

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append("P33 Anchor Precision Repair scaffold is ready; real P21/P31-H1 ephemeral records are required.")
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(f"Self-test-only scaffold evaluated {len(tasks)} synthetic tasks; not quality evidence.")
        else:
            conclusion_lines.append(f"P33 evaluated {len(tasks)} real ephemeral records.")
        if p33_available:
            available_buckets = sum(1 for m in bucket_taxonomy.values() if m.get("availability") == "available")
            conclusion_lines.append(
                f"P33-H1 handoff detected; {available_buckets}/{len(BUCKET_NAMES)} anchor taxonomy buckets have sufficient data. "
                "Diagnostics are aggregate-only and do not prescribe policy."
            )
        else:
            conclusion_lines.append(
                "P33 input missing candidate pools or gold spans; only availability status is reported, no fake zeros."
            )
        conclusion_lines.append("No Rust core, EvidenceCore, default strategy, or remote change is made by P33.")
        conclusion_lines.append("P33 is SCORE-phase-only; labels are loaded after RUN.")

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P33 Reach-Preserving Precision Anchor Repair",
        "status": status,
        "status_reason": reason,
        "self_test": self_test,
        "not_quality_evidence": bool(self_test),
        "real_evaluation": bool(status == "ok" and not self_test),
        "input_paths": [str(p) for p in input_paths] if self_test else [],
        "input_sources": ["self_test"] if self_test else ["p25-policy-records-ephemeral-v1"],
        "insufficient_input_paths": insufficient_paths or [],
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "remote_calls_by_p33": 0,
        "run_phase_public_only": True,
        "labels_loaded_after_run": True,
        "score_phase_only_metrics": True,
        "aggregate_only_public_artifact": True,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_text_stored": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "p31_h1_handoff_detected": p31_h1_handoff_detected,
        "p31_h1_handoff_detected_count": sum(1 for t in tasks if t.get("p31_h1_handoff_detected")),
        "p33_available": p33_available,
        "p33_input_available": bool(tasks),
        "p33_reason": reason,
        "elapsed_ms": elapsed_ms,
        "task_count": len(tasks),
        "positive_task_count": len(positive),
        "no_gold_task_count": sum(1 for t in tasks if not t["has_gold"]),
        "positive_with_pools_count": len(positive_with_pools),
        "metrics": {
            "bucket_taxonomy": bucket_taxonomy,
            "baseline_comparison": baseline_comparison,
            "calibration_matrix": calibration_matrix,
            "p33_to_p32_handoff": p32_handoff,
        },
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    violations = _reject_forbidden_keys(report)
    if violations:
        raise RuntimeError(f"P33 public report contains forbidden keys: {violations}")
    return report


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# P33 Reach-Preserving Precision Anchor Repair\n")
    lines.append(f"- Schema: `{report['schema_version']}`")
    lines.append(f"- Generated: {report['generated_at']}")
    lines.append(f"- Status: `{report['status']}`")
    lines.append(f"- Self-test: {report['self_test']}")
    lines.append(f"- Remote calls by P33: {report['remote_calls_by_p33']}")
    lines.append(f"- P31-H1 handoff detected: {report['p31_h1_handoff_detected']}")
    lines.append(f"- P33 available: {report['p33_available']}\n")

    if report["status"] not in {"ok", "self_test_only"}:
        lines.append("## Status")
        if report.get("status_reason"):
            lines.append(report["status_reason"])
        lines.append("")
        return "\n".join(lines)

    lines.append(f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}")
    lines.append(f"- Positive tasks with pools: {report['positive_with_pools_count']}\n")

    def fmt_rate(m: dict[str, Any] | None) -> str:
        if not isinstance(m, dict):
            return "n/a"
        r = m.get("rate")
        return f"{r:.4f}" if isinstance(r, (int, float)) else "n/a"

    def fmt_int(x: Any) -> str:
        return str(x) if isinstance(x, int) else "n/a"

    lines.append("## Bucket taxonomy diagnostics@5\n")
    lines.append("| Bucket | tasks | pos | no_gold | GoldFileReach | GoldSpanReach | FRSW | false/gold | net1x | diagnostic_class |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for bucket, m in report["metrics"]["bucket_taxonomy"].items():
        if m.get("availability") != "available":
            lines.append(f"| {bucket} | {m.get('task_count', 0)} | - | - | n/a | n/a | n/a | n/a | n/a | {m.get('availability', 'n/a')} |")
            continue
        fpg = m.get("false_per_gold")
        fpg_str = f"{fpg:.4f}" if isinstance(fpg, (int, float)) and fpg != float("inf") else ("inf" if fpg == float("inf") else "n/a")
        lines.append(
            f"| {bucket} | {m['task_count']} | {m['positive_count']} | {m['no_gold_count']} | "
            f"{fmt_rate(m.get('gold_file_reach'))} | {fmt_rate(m.get('gold_span_reach'))} | "
            f"{fmt_rate(m.get('file_right_span_wrong_rate'))} | {fpg_str} | {m['net_span_value_1x']} | {m['diagnostic_class']} |"
        )
    lines.append("")

    base = report["metrics"]["baseline_comparison"]
    lines.append("## Baseline comparison (`candidate_baseline`)@5\n")
    lines.append("| Bucket | tasks | pos | no_gold | GoldFileReach | GoldSpanReach | FRSW | false/gold | net1x | diagnostic_class |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for bucket, m in base.items():
        if m.get("availability") != "available":
            lines.append(f"| {bucket} | {m.get('task_count', 0)} | - | - | n/a | n/a | n/a | n/a | n/a | {m.get('availability', 'n/a')} |")
            continue
        fpg = m.get("false_per_gold")
        fpg_str = f"{fpg:.4f}" if isinstance(fpg, (int, float)) and fpg != float("inf") else "n/a"
        lines.append(
            f"| {bucket} | {m['task_count']} | {m['positive_count']} | {m['no_gold_count']} | "
            f"{fmt_rate(m.get('gold_file_reach'))} | {fmt_rate(m.get('gold_span_reach'))} | "
            f"{fmt_rate(m.get('file_right_span_wrong_rate'))} | {fpg_str} | {m['net_span_value_1x']} | {m['diagnostic_class']} |"
        )
    lines.append("")

    cal = report["metrics"]["calibration_matrix"]
    lines.append("## Calibration matrix@5\n")
    lines.append(
        "Calibration axes: ``a`` = anchor strength (0=none, 1=symbol_or_regex_only, "
        "2=file_agreement, 3=span_agreement, 4=exact_unique_symbol_span_agreement); "
        "``r`` = risk level (0=low/positive, 1=ambiguous, 2=negative/high risk); "
        "``s`` = RRF backing level (0=none, 1=file-only, 2=span)."
    )
    lines.append("")
    lines.append("| Cell | tasks | GoldFileReach | GoldSpanReach | FRSW | net1x | diagnostic_class |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for key, m in cal["cells"].items():
        if m.get("availability") != "available":
            lines.append(f"| {key} | {m.get('task_count', 0)} | n/a | n/a | n/a | n/a | {m.get('availability', 'n/a')} |")
            continue
        lines.append(
            f"| {key} | {m['task_count']} | {fmt_rate(m.get('gold_file_reach'))} | {fmt_rate(m.get('gold_span_reach'))} | "
            f"{fmt_rate(m.get('file_right_span_wrong_rate'))} | {fmt_int(m.get('net_span_value_1x'))} | {m['diagnostic_class']} |"
        )
    lines.append("")

    if cal.get("monotonic_sanity"):
        for check_name, violations in cal["monotonic_sanity"].items():
            if violations:
                lines.append(f"- **{check_name}** violations: {', '.join(violations)}")
        lines.append("")

    p32 = report["metrics"]["p33_to_p32_handoff"]
    lines.append("## P33-to-P32 handoff (budget candidates, not frozen policy)\n")
    for cls, buckets in p32["budget_candidate_buckets"].items():
        lines.append(f"- `{cls}`: {', '.join(buckets) if buckets else '(none)'}")
    lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")

    lines.append("## Safety notes\n")
    lines.append("- No remote model calls were made during P33 evaluation.")
    lines.append("- Labels are loaded only after RUN for aggregate SCORE-phase metrics.")
    lines.append("- This report contains only aggregate bucket diagnostics and public task metadata.")
    lines.append("- Raw queries, snippets, prompts, responses, candidate paths/spans, gold spans, private labels, route features, and provider fields are not stored.")
    lines.append(
        "- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, "
        "`candidate_not_fact=true`, `remote_calls_by_p33=0`, `score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P33 Reach-Preserving Precision Anchor Repair")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P21/P31/P30 JSON record files.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_records: list[dict[str, Any]] = []

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_records = make_self_test_records()
    elif args.input:
        input_paths = list(args.input)
        raw_records = p25.load_p21_inputs(input_paths, require_ephemeral_schema=True)
    else:
        parser.error("Specify --self-test or --input PATH [PATH ...]")

    status = "self_test_only" if args.self_test else "ok"
    reason: str | None = None
    insufficient_paths: list[str] = []
    task_records: list[dict[str, Any]] = []

    for rec in raw_records:
        if rec.get("_p25_input_summary_marker"):
            status = "insufficient_task_detail"
            reason = "Aggregate summary lacks per-task ephemeral records required for P33 anchor repair diagnostics."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        if rec.get("_p25_input_empty_marker"):
            status = "insufficient_task_detail"
            reason = "Input artifact did not contain per-task ephemeral records."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        if rec.get("_p25_unsupported_schema_marker"):
            status = "insufficient_task_detail"
            reason = "P33 real evaluation requires p25-policy-records-ephemeral-v1 input schema or equivalent per-task records."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        task_records.append(rec)

    if not task_records and status == "ok":
        status = "insufficient_task_detail"
        reason = "No per-task records found."

    normalized_tasks = [nt for nt in (normalize_task(raw) for raw in task_records) if nt]

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P33 normalization."

    elapsed_ms = int((time.monotonic() - start) * 1000)

    report = build_report(
        normalized_tasks,
        input_paths,
        self_test=args.self_test,
        elapsed_ms=elapsed_ms,
        status=status,
        reason=reason,
        insufficient_paths=insufficient_paths,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    errors = validate_report(report)
    if errors:
        raise RuntimeError(f"P33 report validation failed: {errors}")

    print(f"P33 report written to {args.out}")
    print(f"P33 markdown written to {args.doc}")
    print("P33 report validation ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
