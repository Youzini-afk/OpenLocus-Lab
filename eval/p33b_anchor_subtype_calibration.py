#!/usr/bin/env python3
"""P33-B Anchor Subtype Calibration — deterministic diagnostic evaluator.

P33-B studies how symbol/regex anchor subtypes (symbol_only, regex_only,
symbol_regex_fusion) and their agreement/RRF-backing characteristics correlate
with candidate reach and span cost. It is diagnostic-only and SCORE-phase-only:
labels are loaded only after RUN and used only for aggregate metrics.

Inputs:
- ``--self-test`` generates synthetic private task records in memory.
- ``--input PATH [PATH ...]`` reads ephemeral P21/P31 SCORE-phase records that
  carry ``p33b_anchor_subtypes`` and ``p31_candidate_pools``.

Safety constraints:
- No remote model calls; ``remote_calls_by_p33b=0``.
- No EvidenceCore semantics change.
- Routing/admission are not influenced; labels are loaded only after RUN.
- Public artifacts are aggregate-only: no per-task rows, no raw queries,
  snippets, prompts, responses, candidate paths/spans, gold spans, private
  labels, route features, subtype rows, or provider fields.
- ``promotion_ready=false``, ``default_should_change=false``,
  ``evidencecore_semantics_changed=false``, ``candidate_not_fact=true``,
  ``score_phase_only_metrics=true``, ``aggregate_only_public_artifact=true``.
"""

from __future__ import annotations

import argparse
import hashlib
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

SCHEMA_VERSION = "p33b-anchor-subtype-calibration-v1"
GENERATED_BY = "eval/p33b_anchor_subtype_calibration.py"

DEFAULT_OUT = Path("artifacts/p33_anchor_precision_repair/p33b_anchor_subtype_calibration_report.json")
DEFAULT_DOC = Path("docs/en/p33b-anchor-subtype-calibration.md")

K = 5

SOURCE_CLASSES = ["symbol_only", "regex_only", "symbol_regex_fusion", "other"]
AGREEMENT_CLASSES = ["single_source", "same_file_only", "span_overlap", "disagree"]

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
    "p33b_anchor_subtypes",
    "raw_candidates",
    "route_features",
    "source_text",
    "excerpt",
    "authorization",
    "evidence_raw",
    "candidate_id",
    "candidate_index",
    "path",
    "start_line",
    "end_line",
    "content_sha",
}
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
    "input_sources",
    "input_source_count",
    "insufficient_input_source_count",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "candidate_not_fact",
    "remote_calls_by_p33b",
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
    "p33b_available",
    "p33b_input_available",
    "p33b_handoff_detected",
    "p33b_handoff_detected_count",
    "p33b_handoff_schema_version",
    "task_count",
    "positive_task_count",
    "no_gold_task_count",
    "positive_with_pools_count",
    "input_summary",
    "metrics",
    "conclusion",
    "validation",
    "bucket",
    "source_class",
    "agreement_class",
    "rank_bin",
    "candidate_count_bin",
    "span_width_bin",
    "rrf_backing",
    "source_strength",
    "match_quality",
    "risk_level",
    "diagnostic_class",
    "p33b_to_p32_handoff",
    "delta_vs_candidate_baseline",
    "coarse_task_level_attribution",
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
        return int(value)
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


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    """Recursively reject private keys that must not appear in public artifacts."""
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_PUBLIC_KEYS and key not in SAFETY_FLAG_KEYS:
                violations.append(prefix + key)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def normalize_label(raw: dict[str, Any]) -> dict[str, Any]:
    gold_spans: list[dict[str, Any]] = []
    for gs in raw.get("gold_spans") or []:
        if isinstance(gs, dict):
            gold_spans.append({
                "path": str(gs.get("path") or "").lower(),
                "start_line": int(gs.get("start_line") or 0),
                "end_line": int(gs.get("end_line") or 0),
            })
    return {
        "has_gold": bool(gold_spans),
        "gold_spans": gold_spans,
        "gold_files": {gs["path"] for gs in gold_spans},
    }


def is_file_reached(items: list[dict[str, Any]], label: dict[str, Any]) -> bool:
    files = {str(it.get("path") or "").lower() for it in items if it.get("path")}
    return bool(files & label.get("gold_files", set()))


def is_span_reached_by_any(items: list[dict[str, Any]], label: dict[str, Any]) -> bool:
    for it in items:
        path = str(it.get("path") or "").lower()
        start = int(it.get("start_line") or 0)
        end = int(it.get("end_line") or 0)
        for gs in label.get("gold_spans", []):
            if path == gs["path"] and end >= gs["start_line"] and start <= gs["end_line"]:
                return True
    return False


def normalize_task(raw: dict[str, Any]) -> dict[str, Any] | None:
    tid = raw.get("task_id")
    if not tid:
        return None

    task_bucket = str(raw.get("task_bucket") or "unknown")
    risk_tags = raw.get("task_risk_tags") or []
    if isinstance(risk_tags, str):
        risk_tags = [risk_tags]
    if not isinstance(risk_tags, list):
        risk_tags = []

    score_group = str(raw.get("score_group") or "no_gold")
    label_raw = raw.get("p31_score_gold") or raw.get("label") or {}
    label = normalize_label(label_raw)
    if score_group == "positive":
        label["has_gold"] = True

    pools = raw.get("p31_candidate_pools") or raw.get("candidate_pool") or {}
    union_items: list[dict[str, Any]] = list(pools.get("symbol_regex_union") or [])

    subtypes: list[dict[str, Any]] = []
    for row in raw.get("p33b_anchor_subtypes") or []:
        if isinstance(row, dict):
            subtypes.append(row)

    outcomes: dict[str, Any] = {}
    for strategy in ("candidate_baseline", "symbol_regex_union"):
        src = raw.get(strategy)
        if isinstance(src, dict):
            outcomes[strategy] = {
                "file_recall_at_5": _as_float(src.get("file_recall_at_5")),
                "span_f0_5": _as_float(src.get("span_f0_5")),
                "primary_false_positive_rate": _as_float(src.get("primary_false_positive_rate")),
                "added_gold_span": _as_int(src.get("added_gold_span")),
                "added_false_span": _as_int(src.get("added_false_span")),
            }

    return {
        "task_id": tid,
        "repo_id": raw.get("repo_id"),
        "task_bucket": task_bucket,
        "task_risk_tags": [str(t) for t in risk_tags if isinstance(t, (str, int, float))],
        "has_gold": bool(label.get("has_gold", False)),
        "has_gold_spans": bool(label.get("gold_spans")),
        "label": label,
        "union_items": union_items,
        "subtypes": subtypes,
        "has_union_pool": bool(union_items),
        "outcomes": outcomes,
        "risk_level": _risk_level_from_bucket_tags(task_bucket, risk_tags),
        "p31_h1_handoff_detected": bool(raw.get("p31_candidate_pools") and raw.get("p31_score_gold")),
        "p33b_handoff_detected": bool(raw.get("p33b_anchor_subtypes") and raw.get("p33b_anchor_subtypes_schema")),
    }


def _risk_level_from_bucket_tags(bucket: str, tags: list[Any]) -> int:
    b = str(bucket).lower()
    tags_set = {str(t).lower() for t in tags}
    if b == "negative" or "hard_distractor" in tags_set or "dense_false_positive" in tags_set:
        return 2
    if b == "ambiguous":
        return 1
    return 0


def _source_strength(source_class: str) -> int:
    return {
        "regex_only": 0,
        "symbol_only": 1,
        "symbol_regex_fusion": 2,
        "other": 0,
    }.get(source_class, 0)


def _match_quality(agreement_class: str, rrf_backing: bool) -> int:
    if agreement_class == "span_overlap":
        return 3 if rrf_backing else 2
    if agreement_class == "same_file_only":
        return 1
    return 0


def subtype_bucket_name(row: dict[str, Any], risk_level: int) -> str:
    src = row.get("source_class") or "other"
    agr = row.get("agreement_class") or "single_source"
    rrf = "rrf_yes" if row.get("rrf_backing") else "rrf_no"
    return f"{src}__{agr}__{rrf}__r{risk_level}"


def assign_buckets(t: dict[str, Any]) -> set[str]:
    """Assign a task to aggregate anchor subtype buckets from pre-SCORE features."""
    buckets: set[str] = set()
    for row in t.get("subtypes") or []:
        buckets.add(subtype_bucket_name(row, t["risk_level"]))
    return buckets


def candidate_matches_row(candidate: dict[str, Any], row: dict[str, Any]) -> bool:
    """Privately match union candidate to its subtype row."""
    candidate_id = candidate.get("candidate_id")
    row_id = row.get("candidate_id")
    if candidate_id and row_id:
        return str(candidate_id) == str(row_id)
    return False


def _row_matches_bucket(row: dict[str, Any], source_class: str, agreement_class: str, rrf_backing: bool) -> bool:
    return (
        row.get("source_class") == source_class
        and row.get("agreement_class") == agreement_class
        and bool(row.get("rrf_backing")) == rrf_backing
    )


def _reached_spans(items: list[dict[str, Any]], label: dict[str, Any]) -> set[tuple[str, int, int]]:
    reached: set[tuple[str, int, int]] = set()
    for it in items:
        path = str(it.get("path") or "").lower()
        start = int(it.get("start_line") or 0)
        end = int(it.get("end_line") or 0)
        for gs in label.get("gold_spans", []):
            if path == gs["path"] and end >= gs["start_line"] and start <= gs["end_line"]:
                reached.add((gs["path"], gs["start_line"], gs["end_line"]))
    return reached


def _diagnostic_class(m: dict[str, Any]) -> str:
    if m["task_count"] < 10 or m["positive_count"] < 10:
        return "insufficient_denominator"
    gr = m.get("gold_span_reach", {}).get("rate")
    fp = m.get("mean_primary_false_positive_rate")
    if gr is not None and gr >= 0.8 and (fp is None or fp <= 0.05):
        return "budget_candidate_observed"
    if m.get("added_false_span", 0) == 0 and m.get("added_gold_span", 0) == 0:
        return "supporting_only_observed"
    if fp is not None and fp >= 0.30:
        return "blocked_high_false_cost"
    fpg = m.get("false_per_gold")
    if fpg is not None and fpg > 1.0:
        return "needs_budget_guard"
    return "needs_budget_guard"


def compute_bucket_metrics(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate subtype-bucket diagnostics at K=5."""
    bucket_to_tasks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in tasks:
        for b in assign_buckets(t):
            bucket_to_tasks[b].append(t)

    all_buckets: set[str] = set()
    for src in SOURCE_CLASSES:
        for agr in AGREEMENT_CLASSES:
            for rrf in (False, True):
                for risk in (0, 1, 2):
                    all_buckets.add(f"{src}__{agr}__{'rrf_yes' if rrf else 'rrf_no'}__r{risk}")

    result: dict[str, Any] = {}
    for bucket in sorted(all_buckets):
        group = bucket_to_tasks.get(bucket, [])
        if not group:
            result[bucket] = {"availability": "missing_bucket", "task_count": 0}
            continue
        parts = bucket.split("__")
        m: dict[str, Any] = {
            "task_count": len(group),
            "positive_count": sum(1 for t in group if t["has_gold"]),
            "no_gold_count": sum(1 for t in group if not t["has_gold"]),
            "source_class": parts[0],
            "agreement_class": parts[1],
            "rrf_backing": parts[2] == "rrf_yes",
            "risk_level": int(parts[3][1:]),
        }
        m.update(_metrics_for_bucket(group, parts[0], parts[1], parts[2] == "rrf_yes"))
        m["diagnostic_class"] = _diagnostic_class(m)
        result[bucket] = m
    return result


def _metrics_for_bucket(group: list[dict[str, Any]], source_class: str, agreement_class: str, rrf_backing: bool) -> dict[str, Any]:
    positive = [t for t in group if t["has_gold"] and t.get("has_gold_spans")]

    have_candidate: list[dict[str, Any]] = []
    missing_join_count = 0
    for t in positive:
        rows = [row for row in (t.get("subtypes") or []) if _row_matches_bucket(row, source_class, agreement_class, rrf_backing)]
        if not rows:
            continue
        joined = any(candidate_matches_row(ev, row) for ev in t["union_items"] for row in rows)
        if joined:
            have_candidate.append(t)
        else:
            missing_join_count += 1

    file_num = span_num = frsw_num = unique_span_num = 0
    for t in have_candidate:
        filtered = [
            ev for ev in t["union_items"]
            for row in t["subtypes"]
            if candidate_matches_row(ev, row) and _row_matches_bucket(row, source_class, agreement_class, rrf_backing)
        ]
        truncated = filtered[:K]
        file_reach = is_file_reached(truncated, t["label"])
        span_reach = is_span_reached_by_any(truncated, t["label"])
        if file_reach:
            file_num += 1
        if span_reach:
            span_num += 1
        if file_reach and not span_reach:
            frsw_num += 1

        other = [ev for ev in t["union_items"] if ev not in filtered]
        bucket_spans = _reached_spans(truncated, t["label"])
        other_spans = _reached_spans(other, t["label"])
        if bucket_spans - other_spans:
            unique_span_num += 1

    denom = len(have_candidate)

    gold_spans = 0
    false_spans = 0
    span_f_values: list[float] = []
    pfp_values: list[float] = []
    for t in group:
        out = t["outcomes"].get("symbol_regex_union", {})
        gold_spans += out.get("added_gold_span") or 0
        false_spans += out.get("added_false_span") or 0
        if out.get("span_f0_5") is not None:
            span_f_values.append(out["span_f0_5"])
        if out.get("primary_false_positive_rate") is not None:
            pfp_values.append(out["primary_false_positive_rate"])

    baseline_file_reach = baseline_span_reach = baseline_file_denom = 0
    for t in have_candidate:
        baseline_items = t["union_items"][:K]
        br_file = is_file_reached(baseline_items, t["label"])
        br_span = is_span_reached_by_any(baseline_items, t["label"])
        baseline_file_denom += 1
        if br_file:
            baseline_file_reach += 1
        if br_span:
            baseline_span_reach += 1

    span_reach_rate = _rate(span_num, denom)
    baseline_span_rate = _rate(baseline_span_reach, baseline_file_denom)
    file_rate = _rate(file_num, denom)
    baseline_file_rate = _rate(baseline_file_reach, baseline_file_denom)

    return {
        "availability": "available" if denom > 0 else "not_measured",
        "coarse_task_level_attribution": True,
        "gold_file_reach": {"numerator": file_num, "denominator": denom, "rate": file_rate},
        "gold_span_reach": {"numerator": span_num, "denominator": denom, "rate": span_reach_rate},
        "file_right_span_wrong_rate": {"numerator": frsw_num, "denominator": file_num, "rate": _rate(frsw_num, file_num)},
        "unique_subtype_span_reach": {"numerator": unique_span_num, "denominator": denom, "rate": _rate(unique_span_num, denom)},
        "added_gold_span": gold_spans,
        "added_false_span": false_spans,
        "false_per_gold": _ratio(false_spans, gold_spans) if gold_spans > 0 else None,
        "gold_per_false": _ratio(gold_spans, false_spans) if false_spans > 0 else None,
        "net_span_value_1x": gold_spans - false_spans,
        "net_span_value_2x": gold_spans - (2 * false_spans),
        "subtype_join_availability": "available" if missing_join_count == 0 else "partial",
        "missing_candidate_join_count": missing_join_count,
        "matched_candidate_task_count": denom,
        "mean_span_f0_5": round(sum(span_f_values) / len(span_f_values), 6) if span_f_values else None,
        "mean_primary_false_positive_rate": round(sum(pfp_values) / len(pfp_values), 6) if pfp_values else None,
        "delta_vs_candidate_baseline": {
            "gold_file_reach_diff": (file_rate or 0.0) - (baseline_file_rate or 0.0) if file_rate is not None or baseline_file_rate is not None else None,
            "gold_span_reach_diff": (span_reach_rate or 0.0) - (baseline_span_rate or 0.0) if span_reach_rate is not None or baseline_span_rate is not None else None,
            "baseline_gold_file_reach": {"numerator": baseline_file_reach, "denominator": baseline_file_denom, "rate": baseline_file_rate},
        },
    }


def compute_calibration_matrix(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """3D calibration over source_strength, match_quality, risk_level."""
    cells: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for t in tasks:
        seen: set[tuple[int, int, int]] = set()
        for row in t.get("subtypes") or []:
            ss = _source_strength(row.get("source_class") or "other")
            mq = _match_quality(row.get("agreement_class") or "single_source", bool(row.get("rrf_backing")))
            rl = t["risk_level"]
            key = (ss, mq, rl)
            if key not in seen:
                seen.add(key)
                cells[key].append(t)

    matrix: dict[str, Any] = {}
    monotonic: dict[str, Any] = {
        "file_reach_non_increasing_with_risk": [],
        "span_reach_non_increasing_with_risk": [],
    }
    for ss in range(3):
        for mq in range(4):
            for rl in range(3):
                group = cells.get((ss, mq, rl), [])
                key = f"s{ss}_m{mq}_r{rl}"
                if not group:
                    matrix[key] = {"availability": "empty", "task_count": 0}
                    continue
                m: dict[str, Any] = {
                    "task_count": len(group),
                    "positive_count": sum(1 for t in group if t["has_gold"]),
                    "no_gold_count": sum(1 for t in group if not t["has_gold"]),
                    "source_strength": ss,
                    "match_quality": mq,
                    "risk_level": rl,
                }
                m.update(_metrics_for_calibration_cell(group, ss, mq))
                m["diagnostic_class"] = _diagnostic_class(m)
                matrix[key] = m

    for ss in range(3):
        for mq in range(4):
            file_rates = []
            span_rates = []
            for rl in range(3):
                m = matrix.get(f"s{ss}_m{mq}_r{rl}", {})
                if m.get("availability") == "available":
                    file_rates.append((rl, m.get("gold_file_reach", {}).get("rate")))
                    span_rates.append((rl, m.get("gold_span_reach", {}).get("rate")))
            for i in range(1, len(file_rates)):
                pr, pv = file_rates[i - 1]
                cr, cv = file_rates[i]
                if pv is not None and cv is not None and cv > pv + 1e-6:
                    monotonic["file_reach_non_increasing_with_risk"].append(f"s{ss}_m{mq}: r{pr}->r{cr}")
            for i in range(1, len(span_rates)):
                pr, pv = span_rates[i - 1]
                cr, cv = span_rates[i]
                if pv is not None and cv is not None and cv > pv + 1e-6:
                    monotonic["span_reach_non_increasing_with_risk"].append(f"s{ss}_m{mq}: r{pr}->r{cr}")
    return {"cells": matrix, "monotonic_sanity": monotonic}


def _metrics_for_calibration_cell(group: list[dict[str, Any]], source_strength: int, match_quality: int) -> dict[str, Any]:
    positive = [t for t in group if t["has_gold"] and t.get("has_gold_spans")]

    have_candidate: list[dict[str, Any]] = []
    missing_join_count = 0
    for t in positive:
        rows = [
            row for row in (t.get("subtypes") or [])
            if _source_strength(row.get("source_class") or "other") == source_strength
            and _match_quality(row.get("agreement_class") or "single_source", bool(row.get("rrf_backing"))) == match_quality
        ]
        if not rows:
            continue
        joined = any(candidate_matches_row(ev, row) for ev in t["union_items"] for row in rows)
        if joined:
            have_candidate.append(t)
        else:
            missing_join_count += 1

    file_num = span_num = frsw_num = 0
    for t in have_candidate:
        filtered = [
            ev for ev in t["union_items"]
            for row in t["subtypes"]
            if candidate_matches_row(ev, row)
            and _source_strength(row.get("source_class") or "other") == source_strength
            and _match_quality(row.get("agreement_class") or "single_source", bool(row.get("rrf_backing"))) == match_quality
        ]
        truncated = filtered[:K]
        file_reach = is_file_reached(truncated, t["label"])
        span_reach = is_span_reached_by_any(truncated, t["label"])
        if file_reach:
            file_num += 1
        if span_reach:
            span_num += 1
        if file_reach and not span_reach:
            frsw_num += 1
    denom = len(have_candidate)

    gold_spans = 0
    false_spans = 0
    span_f_values: list[float] = []
    pfp_values: list[float] = []
    for t in group:
        out = t["outcomes"].get("symbol_regex_union", {})
        gold_spans += out.get("added_gold_span") or 0
        false_spans += out.get("added_false_span") or 0
        if out.get("span_f0_5") is not None:
            span_f_values.append(out["span_f0_5"])
        if out.get("primary_false_positive_rate") is not None:
            pfp_values.append(out["primary_false_positive_rate"])

    return {
        "availability": "available" if denom > 0 else "not_measured",
        "coarse_task_level_attribution": True,
        "gold_file_reach": {"numerator": file_num, "denominator": denom, "rate": _rate(file_num, denom)},
        "gold_span_reach": {"numerator": span_num, "denominator": denom, "rate": _rate(span_num, denom)},
        "file_right_span_wrong_rate": {"numerator": frsw_num, "denominator": file_num, "rate": _rate(frsw_num, file_num)},
        "added_gold_span": gold_spans,
        "added_false_span": false_spans,
        "false_per_gold": _ratio(false_spans, gold_spans) if gold_spans > 0 else None,
        "gold_per_false": _ratio(gold_spans, false_spans) if false_spans > 0 else None,
        "net_span_value_1x": gold_spans - false_spans,
        "net_span_value_2x": gold_spans - (2 * false_spans),
        "subtype_join_availability": "available" if missing_join_count == 0 else "partial",
        "missing_candidate_join_count": missing_join_count,
        "matched_candidate_task_count": denom,
        "mean_span_f0_5": round(sum(span_f_values) / len(span_f_values), 6) if span_f_values else None,
        "mean_primary_false_positive_rate": round(sum(pfp_values) / len(pfp_values), 6) if pfp_values else None,
    }


def compute_p33b_to_p32_handoff(bucket_metrics: dict[str, Any]) -> dict[str, Any]:
    budget_candidate: list[str] = []
    supporting_only: list[str] = []
    needs_budget: list[str] = []
    blocked: list[str] = []
    for bucket, m in bucket_metrics.items():
        if m.get("availability") != "available" or m.get("task_count", 0) == 0:
            continue
        dc = m.get("diagnostic_class")
        if dc == "budget_candidate_observed":
            budget_candidate.append(bucket)
        elif dc == "supporting_only_observed":
            supporting_only.append(bucket)
        elif dc == "blocked_high_false_cost":
            blocked.append(bucket)
        else:
            needs_budget.append(bucket)
    return {
        "frozen_policy": False,
        "budget_candidate_buckets": {
            "budget_candidate_observed": sorted(budget_candidate),
            "supporting_only_observed": sorted(supporting_only),
            "needs_budget_guard": sorted(needs_budget),
            "blocked_high_false_cost": sorted(blocked),
        },
    }


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p33b") != 0:
        errors.append("remote_calls_by_p33b must be 0")
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

    for forbidden in ("tasks", "task_results", "per_task_results", "records", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    def _validate_bucket_block(prefix: str, bucket_metrics: dict[str, Any], extra_metrics: tuple[str, ...] = ("unique_subtype_span_reach",)) -> None:
        for bucket, m in bucket_metrics.items():
            if m.get("availability") != "available":
                continue
            metric_names = ("gold_file_reach", "gold_span_reach", "file_right_span_wrong_rate") + extra_metrics
            for metric_name in metric_names:
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

            for ratio_name in ("false_per_gold", "gold_per_false"):
                val = m.get(ratio_name)
                if val is not None and (math.isinf(val) or math.isnan(val)):
                    errors.append(f"{prefix} {bucket} {ratio_name} must not be infinite/NaN")

    _validate_bucket_block("bucket", report.get("metrics", {}).get("bucket_taxonomy", {}))
    _validate_bucket_block("cell", report.get("metrics", {}).get("calibration_matrix", {}).get("cells", {}), extra_metrics=())

    errors.extend(_reject_forbidden_keys(report))
    return errors


def make_self_test_records() -> list[dict[str, Any]]:
    def cid(path: str, start: int, end: int, rank: int) -> str:
        return hashlib.sha256(f"{path}:{start}:{end}:{rank}".encode("utf-8")).hexdigest()[:16]

    def pool(items: list[tuple[str, int, int]]) -> list[dict[str, Any]]:
        return [
            {"rank": i + 1, "path": p, "start_line": s, "end_line": e, "candidate_id": cid(p, s, e, i + 1)}
            for i, (p, s, e) in enumerate(items)
        ]

    tasks: list[dict[str, Any]] = []

    tasks.append({
        "task_id": "p33b-st-001",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["high_confidence"],
        "score_group": "positive",
        "route_features": {"candidate_count": 3, "rrf_backed_by_anchor": True},
        "p31_candidate_pools": {
            "symbol_regex_union": pool([("src/app.py", 10, 15)]),
            "candidate_baseline": pool([("src/app.py", 10, 15)]),
            "symbol_primary": pool([("src/app.py", 10, 15)]),
            "regex_primary": pool([("src/app.py", 10, 15)]),
        },
        "p31_score_gold": {"has_gold": True, "score_group": "positive", "gold_spans": [{"path": "src/app.py", "start_line": 10, "end_line": 15}]},
        "p33b_anchor_subtypes": [{
            "candidate_id": cid("src/app.py", 10, 15, 1),
            "rank": 1, "source_class": "symbol_regex_fusion", "agreement_class": "span_overlap",
            "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short", "rrf_backing": True,
        }],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
        "p33b_anchor_subtype_handoff": True,
        "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.30, "primary_false_positive_rate": 0.0, "added_gold_span": 1, "added_false_span": 0},
        "symbol_regex_union": {"file_recall_at_5": 1.0, "span_f0_5": 0.30, "primary_false_positive_rate": 0.0, "added_gold_span": 1, "added_false_span": 0},
    })

    tasks.append({
        "task_id": "p33b-st-002",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["symbol_anchor"],
        "score_group": "positive",
        "route_features": {"candidate_count": 2, "rrf_backed_by_anchor": False},
        "p31_candidate_pools": {
            "symbol_regex_union": pool([("src/app.py", 1, 5)]),
            "candidate_baseline": pool([("src/app.py", 1, 5)]),
            "symbol_primary": pool([("src/app.py", 1, 5)]),
        },
        "p31_score_gold": {"has_gold": True, "score_group": "positive", "gold_spans": [{"path": "src/app.py", "start_line": 10, "end_line": 15}]},
        "p33b_anchor_subtypes": [{
            "candidate_id": cid("src/app.py", 1, 5, 1),
            "rank": 1, "source_class": "symbol_only", "agreement_class": "single_source",
            "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short", "rrf_backing": False,
        }],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
        "p33b_anchor_subtype_handoff": True,
        "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.10, "primary_false_positive_rate": 0.20, "added_gold_span": 0, "added_false_span": 2},
        "symbol_regex_union": {"file_recall_at_5": 1.0, "span_f0_5": 0.10, "primary_false_positive_rate": 0.20, "added_gold_span": 0, "added_false_span": 2},
    })

    tasks.append({
        "task_id": "p33b-st-003",
        "repo_id": "js_express",
        "task_bucket": "negative",
        "task_risk_tags": ["negative", "dense_false_positive"],
        "score_group": "no_gold",
        "route_features": {"candidate_count": 2, "rrf_backed_by_anchor": False},
        "p31_candidate_pools": {
            "symbol_regex_union": pool([("src/noise.py", 1, 5)]),
            "candidate_baseline": pool([("src/noise.py", 1, 5)]),
        },
        "p31_score_gold": {"has_gold": False, "score_group": "no_gold", "gold_spans": []},
        "p33b_anchor_subtypes": [{
            "candidate_id": cid("src/noise.py", 1, 5, 1),
            "rank": 1, "source_class": "regex_only", "agreement_class": "single_source",
            "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short", "rrf_backing": False,
        }],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
        "p33b_anchor_subtype_handoff": True,
        "candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.50, "added_gold_span": 0, "added_false_span": 5},
        "symbol_regex_union": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.50, "added_gold_span": 0, "added_false_span": 5},
    })

    tasks.append({
        "task_id": "p33b-st-004",
        "repo_id": "js_express",
        "task_bucket": "ambiguous",
        "task_risk_tags": ["ambiguous"],
        "score_group": "positive",
        "route_features": {"candidate_count": 1, "rrf_backed_by_anchor": False},
        "p31_candidate_pools": {
            "symbol_regex_union": pool([("src/ambig.py", 50, 55)]),
            "candidate_baseline": pool([("src/ambig.py", 50, 55)]),
            "regex_primary": pool([("src/ambig.py", 50, 55)]),
        },
        "p31_score_gold": {"has_gold": True, "score_group": "positive", "gold_spans": [{"path": "src/ambig.py", "start_line": 20, "end_line": 25}]},
        "p33b_anchor_subtypes": [{
            "candidate_id": cid("src/ambig.py", 50, 55, 1),
            "rank": 1, "source_class": "regex_only", "agreement_class": "disagree",
            "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short", "rrf_backing": False,
        }],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
        "p33b_anchor_subtype_handoff": True,
        "candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
        "symbol_regex_union": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
    })

    tasks.append({
        "task_id": "p33b-st-005",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["high_confidence"],
        "score_group": "positive",
        "route_features": {"candidate_count": 4, "rrf_backed_by_anchor": True},
        "p31_candidate_pools": {
            "symbol_regex_union": pool([("src/app.py", 10, 15), ("src/helper.py", 1, 3)]),
            "candidate_baseline": pool([("src/app.py", 10, 15), ("src/helper.py", 1, 3)]),
            "rrf_primary": pool([("src/app.py", 10, 15)]),
        },
        "p31_score_gold": {"has_gold": True, "score_group": "positive", "gold_spans": [{"path": "src/app.py", "start_line": 10, "end_line": 15}]},
        "p33b_anchor_subtypes": [
            {"rank": 1, "source_class": "symbol_only", "agreement_class": "same_file_only",
             "candidate_id": cid("src/app.py", 10, 15, 1), "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short", "rrf_backing": True},
            {"rank": 2, "source_class": "regex_only", "agreement_class": "disagree",
             "candidate_id": cid("src/helper.py", 1, 3, 2), "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short", "rrf_backing": False},
        ],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
        "p33b_anchor_subtype_handoff": True,
        "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.28, "primary_false_positive_rate": 0.08, "added_gold_span": 1, "added_false_span": 2},
        "symbol_regex_union": {"file_recall_at_5": 1.0, "span_f0_5": 0.28, "primary_false_positive_rate": 0.08, "added_gold_span": 1, "added_false_span": 2},
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
    p31_h1 = any(t.get("p31_h1_handoff_detected") for t in tasks)
    p33b_h1 = any(t.get("p33b_handoff_detected") for t in tasks)
    positive = [t for t in tasks if t["has_gold"]]
    positive_with_union = [t for t in positive if t.get("has_union_pool")]
    p33b_available = p31_h1 and p33b_h1 and bool(positive_with_union)

    bucket_taxonomy: dict[str, Any] = {}
    calibration_matrix: dict[str, Any] = {"cells": {}, "monotonic_sanity": {}}
    p32_handoff: dict[str, Any] = {"frozen_policy": False, "budget_candidate_buckets": {}}
    if p33b_available:
        bucket_taxonomy = compute_bucket_metrics(tasks)
        calibration_matrix = compute_calibration_matrix(tasks)
        p32_handoff = compute_p33b_to_p32_handoff(bucket_taxonomy)

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append("P33-B Anchor Subtype Calibration scaffold is ready; real P21 ephemeral records carrying p33b_anchor_subtypes are required.")
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(f"Self-test-only scaffold evaluated {len(tasks)} synthetic tasks; not quality evidence.")
        else:
            conclusion_lines.append(f"P33-B evaluated {len(tasks)} real ephemeral records.")
        if p33b_available:
            avail = sum(1 for m in bucket_taxonomy.values() if m.get("availability") == "available")
            total = len(bucket_taxonomy)
            conclusion_lines.append(
                f"P33-B handoff detected; {avail}/{total} subtype buckets have sufficient data. "
                "Diagnostics are aggregate-only, coarse task-level attribution, and do not prescribe policy."
            )
        else:
            conclusion_lines.append(
                "P33-B input missing subtype handoff, union pool, or gold spans; only availability status reported, no fake zeros."
            )
        conclusion_lines.append("No Rust core, EvidenceCore, default strategy, or remote change is made by P33-B.")
        conclusion_lines.append("P33-B is SCORE-phase-only; labels are loaded after RUN.")

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P33-B Anchor Subtype Calibration",
        "status": status,
        "status_reason": reason,
        "self_test": self_test,
        "not_quality_evidence": bool(self_test),
        "real_evaluation": bool(status == "ok" and not self_test),
        "input_sources": ["self_test"] if self_test else ["p25-policy-records-ephemeral-v1"],
        "input_source_count": len(input_paths),
        "insufficient_input_source_count": len(insufficient_paths or []),
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "remote_calls_by_p33b": 0,
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
        "p31_h1_handoff_detected": p31_h1,
        "p31_h1_handoff_detected_count": sum(1 for t in tasks if t.get("p31_h1_handoff_detected")),
        "p33b_handoff_detected": p33b_h1,
        "p33b_handoff_detected_count": sum(1 for t in tasks if t.get("p33b_handoff_detected")),
        "p33b_handoff_schema_version": "p33b-anchor-subtypes-v1" if p33b_h1 else None,
        "p33b_available": p33b_available,
        "p33b_input_available": bool(tasks),
        "task_count": len(tasks),
        "positive_task_count": len(positive),
        "no_gold_task_count": len(tasks) - len(positive),
        "positive_with_pools_count": len(positive_with_union),
        "input_summary": {
            "p31_h1_handoff_detected": p31_h1,
            "p33b_handoff_detected": p33b_h1,
            "record_count": len(tasks),
        },
        "metrics": {
            "bucket_taxonomy": bucket_taxonomy,
            "calibration_matrix": calibration_matrix,
            "p33b_to_p32_handoff": p32_handoff,
        },
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    violations = _reject_forbidden_keys(report)
    if violations:
        raise RuntimeError(f"P33-B public report contains forbidden keys: {violations}")
    return report


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# P33-B Anchor Subtype Calibration\n")
    lines.append(f"- Schema: `{report['schema_version']}`")
    lines.append(f"- Generated: {report['generated_at']}")
    lines.append(f"- Status: `{report['status']}`")
    lines.append(f"- Self-test: {report['self_test']}")
    lines.append(f"- Remote calls by P33-B: {report['remote_calls_by_p33b']}")
    lines.append(f"- P31-H1 handoff detected: {report['p31_h1_handoff_detected']}")
    lines.append(f"- P33-B handoff detected: {report['p33b_handoff_detected']}")
    lines.append(f"- P33-B available: {report['p33b_available']}\n")

    if report["status"] not in {"ok", "self_test_only"}:
        lines.append("## Status")
        if report.get("status_reason"):
            lines.append(report["status_reason"])
        lines.append("")
        return "\n".join(lines)

    lines.append(f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}")
    lines.append(f"- Positive tasks with union pool: {report['positive_with_pools_count']}")
    lines.append(f"- Input summary: P31-H1={report['input_summary']['p31_h1_handoff_detected']}, P33-B={report['input_summary']['p33b_handoff_detected']}")
    lines.append("")

    def fmt_rate(m: dict[str, Any] | None) -> str:
        if not isinstance(m, dict):
            return "n/a"
        r = m.get("rate")
        return f"{r:.4f}" if isinstance(r, (int, float)) else "n/a"

    def fmt_int(x: Any) -> str:
        return str(x) if isinstance(x, int) else "n/a"

    lines.append("## Subtype bucket diagnostics@5\n")
    lines.append("| Bucket | tasks | pos | no_gold | GoldFileReach | GoldSpanReach | FRSW | UniqueSpan | false/gold | net1x | diagnostic_class |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for bucket, m in report["metrics"]["bucket_taxonomy"].items():
        if m.get("availability") != "available":
            lines.append(f"| {bucket} | {m.get('task_count', 0)} | - | - | n/a | n/a | n/a | n/a | n/a | n/a | {m.get('availability', 'n/a')} |")
            continue
        fpg = m.get("false_per_gold")
        fpg_str = f"{fpg:.4f}" if isinstance(fpg, (int, float)) and not math.isinf(fpg) else "n/a"
        lines.append(
            f"| {bucket} | {m['task_count']} | {m['positive_count']} | {m['no_gold_count']} | "
            f"{fmt_rate(m.get('gold_file_reach'))} | {fmt_rate(m.get('gold_span_reach'))} | "
            f"{fmt_rate(m.get('file_right_span_wrong_rate'))} | {fmt_rate(m.get('unique_subtype_span_reach'))} | "
            f"{fpg_str} | {fmt_int(m.get('net_span_value_1x'))} | {m['diagnostic_class']} |"
        )
    lines.append("")

    cal = report["metrics"]["calibration_matrix"]
    lines.append("## Calibration matrix@5\n")
    lines.append(
        "Calibration axes: ``s`` = source strength (0=regex_only, 1=symbol_only, 2=symbol_regex_fusion); "
        "``m`` = match quality (0=disagree, 1=same_file_only, 2=span_overlap_unbacked, 3=span_overlap_rrf_backed); "
        "``r`` = risk level (0=low/positive, 1=ambiguous, 2=negative/high risk)."
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

    p32 = report["metrics"]["p33b_to_p32_handoff"]
    lines.append("## P33-B-to-P32 handoff (budget candidates, not frozen policy)\n")
    for cls, buckets in p32["budget_candidate_buckets"].items():
        lines.append(f"- `{cls}`: {', '.join(buckets) if buckets else '(none)'}")
    lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")

    lines.append("## Safety notes\n")
    lines.append("- No remote model calls were made during P33-B evaluation.")
    lines.append("- Labels are loaded only after RUN for aggregate SCORE-phase metrics.")
    lines.append("- This report contains only aggregate subtype diagnostics and public task metadata.")
    lines.append("- Span cost attribution is coarse task-level attribution from symbol_regex_union outcomes, not per-candidate causation.")
    lines.append("- Raw queries, snippets, prompts, responses, candidate paths/spans, gold spans, private labels, route features, subtype rows, and provider fields are not stored.")
    lines.append(
        "- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, "
        "`candidate_not_fact=true`, `remote_calls_by_p33b=0`, `score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P33-B Anchor Subtype Calibration")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P21/P31 JSON record files.")
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
            reason = "Aggregate summary lacks per-task ephemeral records required for P33-B anchor subtype calibration."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        if rec.get("_p25_input_empty_marker"):
            status = "insufficient_task_detail"
            reason = "Input artifact did not contain per-task ephemeral records."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        if rec.get("_p25_unsupported_schema_marker"):
            status = "insufficient_task_detail"
            reason = "P33-B requires p25-policy-records-ephemeral-v1 input schema or equivalent per-task records."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        task_records.append(rec)

    if not task_records and status == "ok":
        status = "insufficient_task_detail"
        reason = "No per-task records found."

    normalized_tasks = [nt for nt in (normalize_task(raw) for raw in task_records) if nt]

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P33-B normalization."

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
        for e in errors:
            print(f"Validation error: {e}", file=sys.stderr)
        return 1
    print("P33-B report validation ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
