#!/usr/bin/env python3
"""P31 Candidate Reach Ceiling Study — deterministic diagnostic evaluator.

P31 measures how often candidate evidence alone reaches the gold label before
any routing or admission decision is applied. It is diagnostic-only and
SCORE-phase-only: it never consumes labels during routing, never changes
EvidenceCore semantics, and never calls remote providers.

Input:
- ``--self-test`` generates synthetic private task records in memory.
- ``--input PATH [PATH ...]`` reads ephemeral P25/P30 SCORE-phase records.
  P31 will use candidate evidence lists if the ephemeral record carries them;
  otherwise it reports ``candidate_pool_availability="missing_candidate_pool"``
  and falls back to outcome-only aggregate metrics.

Safety constraints:
- No remote model calls; ``remote_calls_by_p31=0``.
- No EvidenceCore semantics change.
- Routing/admission are not influenced; labels are loaded only after RUN.
- Public artifacts are aggregate-only: no per-task rows, no raw queries,
  snippets, prompts, responses, candidate paths/spans, gold spans, private
  labels, or provider fields.
- ``promotion_ready=false``, ``default_should_change=false``,
  ``evidencecore_semantics_changed=false``, ``candidate_not_fact=true``,
  ``score_phase_only_metrics=true``, ``aggregate_only_public_artifact=true``.
"""

from __future__ import annotations

import argparse
import copy
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

SCHEMA_VERSION = "p31-candidate-reach-ceiling-report-v1"
GENERATED_BY = "eval/p31_candidate_reach_ceiling.py"

DEFAULT_OUT = Path("artifacts/p31_candidate_reach_ceiling/p31_candidate_reach_ceiling_report.json")
DEFAULT_DOC = Path("docs/en/p31-candidate-reach-ceiling.md")

K_VALUES = [1, 3, 5, 10, 20]
TRANSFORMED_STRATEGIES = [
    "llm_span_narrow",
    "llm_filter",
    "llm_abstain_filter",
    "symbol_regex_union",
    "rrf_primary",
    "bucket_routed_v0",
    "admission_v3",
    "admission_v3_h1",
    "admission_v3_h2",
]
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
    "candidates",
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
    "input_paths",
    "input_sources",
    "insufficient_input_paths",
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "candidate_not_fact",
    "remote_calls_by_p31",
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
    "elapsed_ms",
    "p31_h1_handoff_detected",
    "p31_h1_handoff_detected_count",
    "candidate_pool_availability",
    "candidate_pool_detected_count",
    "gold_span_availability",
    "positive_with_gold_spans_count",
    "positive_without_gold_spans_count",
    "reach_metrics_available",
    "outcome_metrics_available",
    "candidate_pool_detected_count",
    "task_count",
    "positive_task_count",
    "no_gold_task_count",
    "metrics",
    "failure_funnel",
    "strategy_miss_given_gold_present",
    "filter_kill_gold_rate",
    "admission_false_primary_rate",
    "admission_false_span_per_no_gold_task",
    "evidencecore_reject_rate",
    "conclusion",
    "validation",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return bool(value)


def _as_float(src: dict[str, Any], *keys: str) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for k in keys:
        try:
            out[k] = float(src[k])  # type: ignore[arg-type]
        except (TypeError, KeyError, ValueError):
            out[k] = None
    return out


def _as_int(src: dict[str, Any], *keys: str) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    for k in keys:
        try:
            out[k] = int(src[k])  # type: ignore[arg-type]
        except (TypeError, KeyError, ValueError):
            out[k] = None
    return out


def _extract_outcome(raw: dict[str, Any], name: str) -> dict[str, Any]:
    src = raw.get(name)
    if isinstance(src, dict):
        return src
    for key in ("strategies", "outcomes", "strategy_results", "results", "metrics"):
        container = raw.get(key) or {}
        if isinstance(container, dict) and name in container:
            s = container[name]
            if isinstance(s, dict):
                return s
    return {}


def _extract_evidence_list(raw: dict[str, Any], strategy: str) -> list[dict[str, Any]] | None:
    """Return evidence items for a strategy if explicitly stored; otherwise None."""
    # Candidate evidence may be stored under strategy_outcome.evidence or under
    # per-task candidate_pool[strategy].
    src = _extract_outcome(raw, strategy)
    if isinstance(src.get("evidence"), list):
        return list(src["evidence"])
    pool = raw.get("candidate_pool") or raw.get("candidates")
    if isinstance(pool, dict):
        items = pool.get(strategy)
        if isinstance(items, list):
            return list(items)
        if strategy == "candidate_baseline" and isinstance(pool.get("baseline"), list):
            return list(pool["baseline"])
    return None


def _evidence_overlaps_span(ev: dict[str, Any], start: int, end: int) -> bool:
    try:
        ev_start = int(ev.get("start_line") or ev.get("start") or 0)
        ev_end = int(ev.get("end_line") or ev.get("end") or ev_start)
    except (TypeError, ValueError):
        return False
    return ev_end >= start and ev_start <= end


def _evidence_exact_span(ev: dict[str, Any], start: int, end: int) -> bool:
    try:
        ev_start = int(ev.get("start_line") or ev.get("start") or 0)
        ev_end = int(ev.get("end_line") or ev.get("end") or ev_start)
    except (TypeError, ValueError):
        return False
    return ev_start == start and ev_end == end


def normalize_label(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract only private-in-memory label metadata used for aggregate scoring."""
    gold_spans: list[dict[str, Any]] = []
    for gs in raw.get("gold_spans") or []:
        if isinstance(gs, dict):
            gold_spans.append(gs)
    gold_files = {str(gs.get("path") or gs.get("file") or "").lower() for gs in gold_spans if gs.get("path") or gs.get("file")}
    return {
        "has_gold": bool(gold_spans),
        "gold_spans": gold_spans,
        "gold_files": gold_files,
    }


def _extract_p31_candidate_pools(raw: dict[str, Any]) -> dict[str, list[dict[str, Any]]] | None:
    """Return P31-H1 candidate pools if present."""
    pools = raw.get("p31_candidate_pools")
    if not isinstance(pools, dict):
        return None
    out: dict[str, list[dict[str, Any]]] = {}
    for strategy in ["candidate_baseline", "llm_span_narrow", "llm_filter", "llm_abstain_filter", "symbol_regex_union", "rrf_primary"]:
        items = pools.get(strategy)
        if isinstance(items, list):
            out[strategy] = list(items)
    return out if out else None


def _extract_p31_score_gold(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Return P31-H1 private SCORE-phase gold metadata if present."""
    sg = raw.get("p31_score_gold")
    if not isinstance(sg, dict):
        return None
    gold_spans: list[dict[str, Any]] = []
    for gs in sg.get("gold_spans") or []:
        if isinstance(gs, dict):
            gold_spans.append(gs)
    return {
        "has_gold": bool(gold_spans),
        "gold_spans": gold_spans,
        "gold_files": {str(gs.get("path") or gs.get("file") or "").lower() for gs in gold_spans if gs.get("path") or gs.get("file")},
    }


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

    # Gold spans: prefer P31-H1 private SCORE metadata, then legacy/self-test label.
    label = _extract_p31_score_gold(raw) or normalize_label(raw.get("label") or {})
    p31_h1_handoff_detected = bool(raw.get("p31_candidate_pools") and raw.get("p31_score_gold"))

    if raw.get("score_group") == "positive":
        has_gold_label = True
    elif raw.get("score_group") == "no_gold":
        has_gold_label = False
    else:
        has_gold_label = bool(raw.get("has_gold", False))

    # If no explicit gold metadata, fall back to score_group / has_gold flags.
    if not label["has_gold"] and has_gold_label is not None:
        label["has_gold"] = has_gold_label

    outcomes: dict[str, Any] = {}
    for strategy in ["candidate_baseline"] + TRANSFORMED_STRATEGIES:
        src = _extract_outcome(raw, strategy)
        outcomes[strategy] = {**_as_float(src, "file_recall_at_5", "span_f0_5", "primary_false_positive_rate", "no_gold_false_primary_rate"), **_as_int(src, "added_gold_span", "added_false_span"), "abstained": bool(src.get("abstained", False))}

    # Evidence pools: prefer P31-H1, then legacy formats.
    candidate_pool = _extract_p31_candidate_pools(raw)
    has_pool = candidate_pool is not None
    if not has_pool:
        candidate_pool = {}
        for key in ("candidate_baseline", "symbol_regex_union", "rrf_primary", "llm_span_narrow", "llm_filter", "llm_abstain_filter"):
            ev = _extract_evidence_list(raw, key)
            if ev is not None:
                candidate_pool[key] = ev
                has_pool = True

    return {
        "task_id": tid,
        "repo_id": raw.get("repo_id"),
        "task_bucket": task_bucket,
        "task_risk_tags": risk_tags,
        "has_gold": has_gold_label,
        "has_gold_spans": bool(label["gold_spans"]),
        "label": label,
        "outcomes": outcomes,
        "candidate_pool": candidate_pool,
        "has_candidate_pool": has_pool,
        "p31_h1_handoff_detected": p31_h1_handoff_detected,
    }


def compute_reach_for_task(task: dict[str, Any], strategy: str, k: int) -> dict[str, Any]:
    """Return per-task reach booleans for candidate evidence up to rank k."""
    items = task.get("candidate_pool", {}).get(strategy, [])[:k]
    label = task["label"]
    result = {
        "has_candidates": bool(items),
        "file_reach": False,
        "span_reach": False,
        "span_exact_reach": False,
        "file_right_span_wrong": False,
    }
    if not label["has_gold"] or not items:
        return result

    gold_files = label["gold_files"]
    for ev in items:
        ev_path = str(ev.get("path") or ev.get("file") or "").lower()
        if ev_path and ev_path in gold_files:
            result["file_reach"] = True
            for gs in label["gold_spans"]:
                try:
                    gs_start = int(gs.get("start_line") or gs.get("start") or 0)
                    gs_end = int(gs.get("end_line") or gs.get("end") or gs_start)
                except (TypeError, ValueError):
                    continue
                if _evidence_overlaps_span(ev, gs_start, gs_end):
                    result["span_reach"] = True
                if _evidence_exact_span(ev, gs_start, gs_end):
                    result["span_exact_reach"] = True
        if result["span_reach"]:
            break

    if result["file_reach"] and not result["span_reach"]:
        result["file_right_span_wrong"] = True
    return result


def _rate(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def _avg_rate(values: list[tuple[int, int]]) -> float | None:
    nums = [n for n, d in values if d > 0]
    dens = [d for n, d in values if d > 0]
    if not dens:
        return None
    return round(sum(nums) / sum(dens), 6)


def compute_reach_metrics(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate reach metrics across K values from candidate evidence pools."""
    positive_tasks = [t for t in tasks if t["has_gold"] and t.get("has_gold_spans")]
    all_tasks_with_pool = [t for t in tasks if t.get("has_candidate_pool")]

    by_k: dict[int, dict[str, Any]] = {}
    for k in K_VALUES:
        file_num = span_num = exact_num = absent_num = frsw_num = 0
        positive_with_pool = 0
        for t in positive_tasks:
            if not t.get("has_candidate_pool"):
                continue
            positive_with_pool += 1
            r = compute_reach_for_task(t, "candidate_baseline", k)
            if r["file_reach"]:
                file_num += 1
            else:
                # Gold file absent from candidates at rank k equals candidate-absent-for-gold.
                absent_num += 1
            if r["span_reach"]:
                span_num += 1
            if r["span_exact_reach"]:
                exact_num += 1
            if r["file_right_span_wrong"]:
                frsw_num += 1

        by_k[k] = {
            "gold_file_reach": {"numerator": file_num, "denominator": positive_with_pool, "rate": _rate(file_num, positive_with_pool)},
            "gold_span_reach": {"numerator": span_num, "denominator": positive_with_pool, "rate": _rate(span_num, positive_with_pool)},
            "gold_span_exact_reach": {"numerator": exact_num, "denominator": positive_with_pool, "rate": _rate(exact_num, positive_with_pool)},
            "candidate_absent_rate": {"numerator": absent_num, "denominator": positive_with_pool, "rate": _rate(absent_num, positive_with_pool)},
            "file_right_span_wrong_rate": {"numerator": frsw_num, "denominator": file_num, "rate": _rate(frsw_num, file_num)},
        }
    return {"by_k": by_k}


def compute_strategy_miss_given_gold_present(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """For transformed strategies, miss rate when both baseline and strategy pools are available."""
    positive_tasks = [t for t in tasks if t["has_gold"] and t.get("has_gold_spans") and t.get("has_candidate_pool")]
    by_strategy: dict[str, Any] = {}
    for strategy in TRANSFORMED_STRATEGIES:
        by_k: dict[int, dict[str, Any]] = {}
        for k in K_VALUES:
            miss_num = denom = 0
            for t in positive_tasks:
                if strategy not in t.get("candidate_pool", {}):
                    continue
                baseline = compute_reach_for_task(t, "candidate_baseline", k)
                if not baseline["span_reach"]:
                    continue
                denom += 1
                transformed = compute_reach_for_task(t, strategy, k)
                if not transformed["span_reach"]:
                    miss_num += 1
            by_k[k] = {
                "numerator": miss_num,
                "denominator": denom,
                "rate": _rate(miss_num, denom),
            }
        by_strategy[strategy] = by_k
    return by_strategy


def compute_filter_kill_gold_rate(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Out of positive tasks, how often filter dropped all gold evidence vs baseline."""
    positive_tasks = [t for t in tasks if t["has_gold"]]
    num = 0
    denom = 0
    for t in positive_tasks:
        base = t["outcomes"].get("candidate_baseline", {})
        filt = t["outcomes"].get("llm_filter", {})
        base_gold = base.get("added_gold_span") if base.get("added_gold_span") is not None else base.get("file_recall_at_5")
        filt_gold = filt.get("added_gold_span") if filt.get("added_gold_span") is not None else filt.get("file_recall_at_5")
        if filt.get("abstained"):
            # Filter explicitly abstained; count as a kill if baseline had gold.
            if base_gold is not None and base_gold > 0:
                num += 1
                denom += 1
            continue
        if base_gold is None or filt_gold is None:
            continue
        denom += 1
        if base_gold > 0 and filt_gold <= 0:
            num += 1
    return {"numerator": num, "denominator": denom, "rate": _rate(num, denom)}


def compute_admission_false_primary_rate(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Report selected-admission false-primary availability and outcome PFP incidence.

    Current P25/P30 ephemeral records contain strategy outcomes but not public
    selected admission/no-gold action rows. Returning a true admission false
    primary rate would overstate what the data supports, so the primary metric is
    explicitly marked not-measured and the per-strategy PFP incidence is reported
    only as a fallback diagnostic.
    """
    strategy_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"numerator": 0, "denominator": 0})
    for t in tasks:
        for strategy in TRANSFORMED_STRATEGIES:
            out = t["outcomes"].get(strategy, {})
            if out.get("primary_false_positive_rate") is not None:
                strategy_counts[strategy]["denominator"] += 1
                if out["primary_false_positive_rate"] > 0:
                    strategy_counts[strategy]["numerator"] += 1
    return {
        "status": "not_measured",
        "reason": "selected_admission_action_rows_unavailable",
        "numerator": 0,
        "denominator": 0,
        "rate": None,
        "outcome_pfp_incidence_by_strategy": {k: {"numerator": v["numerator"], "denominator": v["denominator"], "rate": _rate(v["numerator"], v["denominator"])} for k, v in strategy_counts.items()},
    }


def compute_admission_false_span_per_no_gold_task(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Average added false span per no-gold task across strategies with outcomes."""
    no_gold_tasks = [t for t in tasks if not t["has_gold"]]
    total_false = 0
    total_tasks = 0
    by_strategy: dict[str, dict[str, Any]] = defaultdict(lambda: {"false_spans": 0, "tasks": 0})
    for t in no_gold_tasks:
        for strategy in TRANSFORMED_STRATEGIES:
            out = t["outcomes"].get(strategy, {})
            if out.get("added_false_span") is not None:
                total_false += out["added_false_span"]
                total_tasks += 1
                by_strategy[strategy]["false_spans"] += out["added_false_span"]
                by_strategy[strategy]["tasks"] += 1
    return {
        "total_false_spans": total_false,
        "total_no_gold_tasks": total_tasks,
        "rate": round(total_false / total_tasks, 6) if total_tasks else None,
        "by_strategy": {k: {"false_spans": v["false_spans"], "tasks": v["tasks"], "rate": round(v["false_spans"] / v["tasks"], 6) if v["tasks"] else None} for k, v in by_strategy.items()},
    }


def compute_evidencecore_reject_rate(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    has_rejected = any(
        t["outcomes"].get(s, {}).get("evidencecore_rejected") is not None
        or t["outcomes"].get(s, {}).get("rejected") is not None
        for t in tasks
        for s in ["candidate_baseline"] + TRANSFORMED_STRATEGIES
    )
    if not has_rejected:
        return {"status": "not_measured", "rate": None, "numerator": 0, "denominator": 0}
    num = 0
    denom = 0
    for t in tasks:
        for s in ["candidate_baseline"] + TRANSFORMED_STRATEGIES:
            out = t["outcomes"].get(s, {})
            rej = out.get("evidencecore_rejected") if out.get("evidencecore_rejected") is not None else out.get("rejected")
            if rej is not None:
                denom += 1
                if _as_bool(rej):
                    num += 1
    return {"status": "measured", "rate": _rate(num, denom), "numerator": num, "denominator": denom}


def compute_failure_funnel(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate failure funnel at K=5. Counts are over positive tasks and sum to positive_task_count."""
    positive_tasks = [t for t in tasks if t["has_gold"] and t.get("has_gold_spans")]
    buckets: dict[str, Any] = {
        "evaluated": len(positive_tasks),
        "has_candidate_pool": sum(1 for t in positive_tasks if t.get("has_candidate_pool")),
        "no_candidate_pool": sum(1 for t in positive_tasks if not t.get("has_candidate_pool")),
        "pool_but_no_candidate_at_5": 0,
        "candidate_present_no_file": 0,
        "file_reach_no_span": 0,
        "span_reached": 0,
        "span_exact_reached": 0,
        "model_output_loses_gold": 0,
    }
    for t in positive_tasks:
        if not t.get("has_candidate_pool"):
            continue
        r = compute_reach_for_task(t, "candidate_baseline", 5)
        if not r["has_candidates"]:
            buckets["pool_but_no_candidate_at_5"] += 1
            continue
        if not r["file_reach"]:
            buckets["candidate_present_no_file"] += 1
            continue
        if not r["span_reach"]:
            buckets["file_reach_no_span"] += 1
            continue
        buckets["span_reached"] += 1
        if r["span_exact_reach"]:
            buckets["span_exact_reached"] += 1
        # If candidate baseline reaches gold at K=5 but transformed admission loses it.
        baseline_reach = r
        lost = False
        for strategy in ("admission_v3", "admission_v3_h1", "admission_v3_h2", "bucket_routed_v0", "llm_filter", "llm_abstain_filter"):
            tr = compute_reach_for_task(t, strategy, 5)
            if tr["file_reach"] and tr["span_reach"]:
                continue
            # Missing pool for transformed strategy is not counted as a loss.
            if strategy in t.get("candidate_pool", {}):
                lost = True
                break
        if lost:
            buckets["model_output_loses_gold"] += 1

    funnel_sums_to_positive_tasks = (
        buckets["no_candidate_pool"]
        + buckets["pool_but_no_candidate_at_5"]
        + buckets["candidate_present_no_file"]
        + buckets["file_reach_no_span"]
        + buckets["span_reached"]
        == buckets["evaluated"]
    )
    return {"buckets": buckets, "funnel_sums_to_positive_tasks": funnel_sums_to_positive_tasks}


def compute_outcome_fallback_metrics(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Outcome-only metrics when candidate evidence pools are missing."""
    by_strategy: dict[str, Any] = {}
    for strategy in ["candidate_baseline"] + TRANSFORMED_STRATEGIES:
        file_recall_values: list[tuple[int, int]] = []
        span_f_values: list[float] = []
        pfp_values: list[float] = []
        for t in tasks:
            out = t["outcomes"].get(strategy, {})
            if out.get("file_recall_at_5") is not None:
                file_recall_values.append((int(round(out["file_recall_at_5"])), 1))
            if out.get("span_f0_5") is not None:
                span_f_values.append(out["span_f0_5"])
            if out.get("primary_false_positive_rate") is not None:
                pfp_values.append(out["primary_false_positive_rate"])
        by_strategy[strategy] = {
            "file_recall_at_5_rate": _avg_rate(file_recall_values),
            "mean_span_f0_5": round(sum(span_f_values) / len(span_f_values), 6) if span_f_values else None,
            "mean_primary_false_positive_rate": round(sum(pfp_values) / len(pfp_values), 6) if pfp_values else None,
        }
    return by_strategy


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
    if report.get("remote_calls_by_p31") != 0:
        errors.append("remote_calls_by_p31 must be 0")
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
    if report.get("status") == "ok":
        if report.get("self_test") and report.get("real_policy_evaluation") is not False:
            errors.append("self_test must set real_policy_evaluation=false")
        if not report.get("self_test") and report.get("real_policy_evaluation") is not True:
            errors.append("ok real run must set real_policy_evaluation=true")

    # Validate metric rates and counts.
    metrics = report.get("metrics", {})
    for k in K_VALUES:
        block = metrics.get("reach", {}).get("by_k", {}).get(k, {})
        for metric_name, m in block.items():
            if not isinstance(m, dict):
                continue
            rate = m.get("rate")
            num = m.get("numerator")
            den = m.get("denominator")
            if rate is not None and not (0.0 <= rate <= 1.0 + 1e-9):
                errors.append(f"{metric_name}@K={k} rate out of range: {rate}")
            if not isinstance(num, int) or num < 0:
                errors.append(f"{metric_name}@K={k} numerator invalid: {num}")
            if not isinstance(den, int) or den < 0:
                errors.append(f"{metric_name}@K={k} denominator invalid: {den}")
            if den is not None and num is not None and num > den:
                errors.append(f"{metric_name}@K={k} numerator exceeds denominator")

    # Candidate absent equals 1 - file reach for positive tasks with pool.
    for k in K_VALUES:
        block = metrics.get("reach", {}).get("by_k", {}).get(k, {})
        file_reach = block.get("gold_file_reach", {}).get("rate")
        absent = block.get("candidate_absent_rate", {}).get("rate")
        if file_reach is not None and absent is not None:
            if abs(absent - (1.0 - file_reach)) > 1e-6:
                errors.append(f"candidate_absent@K={k} must equal 1 - gold_file_reach for positive tasks")

    # No per-task public rows.
    for forbidden in ("tasks", "task_results", "per_task_results", "records", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    errors.extend(_reject_forbidden_keys(report))
    return errors


def make_self_test_records() -> list[dict[str, Any]]:
    """Synthetic in-memory private tasks with candidate pools and outcomes."""
    def make_candidates(paths: list[tuple[str, int, int]], gold_path: str | None = None, gold_span: tuple[int, int] | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for path, start, end in paths:
            out.append({"path": path, "start_line": start, "end_line": end})
        return out

    def gold_label(path: str, start: int, end: int) -> dict[str, Any]:
        return {"has_gold": True, "gold_spans": [{"path": path, "start_line": start, "end_line": end}], "gold_files": {path.lower()}}

    tasks: list[dict[str, Any]] = []

    # 1. Gold span reached exactly at K=1.
    tasks.append({
        "task_id": "p31-st-001",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["high_confidence"],
        "score_group": "positive",
        "candidate_pool": {
            "candidate_baseline": make_candidates([("src/app.py", 10, 15)], gold_path="src/app.py", gold_span=(10, 15)),
            "llm_span_narrow": make_candidates([("src/app.py", 10, 12)]),
            "llm_filter": make_candidates([("src/app.py", 10, 15)]),
            "llm_abstain_filter": [],
            "symbol_regex_union": make_candidates([("src/app.py", 10, 15)]),
            "rrf_primary": make_candidates([("src/app.py", 10, 15)]),
        },
        "outcomes": {
            "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.30, "primary_false_positive_rate": 0.10, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 1},
            "llm_span_narrow": {"file_recall_at_5": 1.0, "span_f0_5": 0.25, "primary_false_positive_rate": 0.05, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 0},
            "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.20, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
            "llm_abstain_filter": {"abstained": True},
            "symbol_regex_union": {"file_recall_at_5": 1.0, "span_f0_5": 0.35, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 0},
            "rrf_primary": {"file_recall_at_5": 1.0, "span_f0_5": 0.28, "primary_false_positive_rate": 0.08, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 2},
        },
        "label": gold_label("src/app.py", 10, 15),
    })

    # 2. File reach but span wrong.
    tasks.append({
        "task_id": "p31-st-002",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["symbol_anchor"],
        "score_group": "positive",
        "candidate_pool": {
            "candidate_baseline": make_candidates([("src/app.py", 1, 5), ("src/app.py", 50, 55)]),
            "llm_span_narrow": make_candidates([("src/app.py", 50, 55)]),
            "llm_filter": make_candidates([("src/app.py", 1, 5)]),
            "symbol_regex_union": make_candidates([("src/app.py", 50, 55)]),
            "rrf_primary": make_candidates([("src/app.py", 1, 5)]),
        },
        "outcomes": {
            "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.10, "primary_false_positive_rate": 0.20, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 2},
            "llm_span_narrow": {"file_recall_at_5": 1.0, "span_f0_5": 0.12, "primary_false_positive_rate": 0.10, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 1},
            "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
            "llm_abstain_filter": {"abstained": True},
            "symbol_regex_union": {"file_recall_at_5": 1.0, "span_f0_5": 0.15, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 1},
            "rrf_primary": {"file_recall_at_5": 1.0, "span_f0_5": 0.05, "primary_false_positive_rate": 0.15, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 3},
        },
        "label": gold_label("src/app.py", 10, 15),
    })

    # 3. No candidate reaches gold file.
    tasks.append({
        "task_id": "p31-st-003",
        "repo_id": "js_express",
        "task_bucket": "negative",
        "task_risk_tags": ["hard_distractor"],
        "score_group": "positive",
        "candidate_pool": {
            "candidate_baseline": make_candidates([("src/wrong.py", 1, 5), ("src/distractor.py", 10, 15)]),
            "llm_filter": [],
            "llm_abstain_filter": [],
        },
        "outcomes": {
            "candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.30, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 3},
            "llm_filter": {"abstained": True},
            "llm_abstain_filter": {"abstained": True},
        },
        "label": gold_label("src/right.py", 10, 15),
    })

    # 4. No-gold task.
    tasks.append({
        "task_id": "p31-st-004",
        "repo_id": "js_express",
        "task_bucket": "negative",
        "task_risk_tags": ["negative"],
        "score_group": "no_gold",
        "candidate_pool": {
            "candidate_baseline": make_candidates([("src/noise.py", 1, 5)]),
            "llm_filter": [],
            "llm_abstain_filter": [],
        },
        "outcomes": {
            "candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.40, "no_gold_false_primary_rate": 0.40, "added_gold_span": 0, "added_false_span": 4},
            "llm_filter": {"abstained": True},
            "llm_abstain_filter": {"abstained": True},
        },
        "label": {"has_gold": False, "gold_spans": [], "gold_files": set()},
    })

    # 5. Outcome-only task (no candidate pool) to exercise fallback path.
    tasks.append({
        "task_id": "p31-st-005",
        "repo_id": "js_express",
        "task_bucket": "ambiguous",
        "task_risk_tags": ["ambiguous"],
        "score_group": "positive",
        "outcomes": {
            "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.18, "primary_false_positive_rate": 0.12, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 2},
            "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
        },
        "label": gold_label("src/ambig.py", 20, 25),
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
    candidate_pool_availability = "available" if tasks and all(t.get("has_candidate_pool") for t in tasks) else "partial" if any(t.get("has_candidate_pool") for t in tasks) else "missing_candidate_pool"
    positive_with_gold_spans = sum(1 for t in tasks if t["has_gold"] and t.get("has_gold_spans"))
    positive_without_gold_spans = sum(1 for t in tasks if t["has_gold"] and not t.get("has_gold_spans"))
    gold_span_availability = "available" if tasks and all(t.get("has_gold_spans") for t in tasks if t["has_gold"]) else "partial" if any(t.get("has_gold_spans") for t in tasks if t["has_gold"]) else "missing_gold_spans"
    p31_h1_handoff_detected = any(t.get("p31_h1_handoff_detected") for t in tasks)
    reach_metrics_available = (candidate_pool_availability != "missing_candidate_pool" and gold_span_availability != "missing_gold_spans")
    outcome_metrics_available = bool(tasks)

    reach: dict[str, Any] = {"by_k": {k: {} for k in K_VALUES}}
    strategy_miss: dict[str, Any] = {}
    if reach_metrics_available:
        reach = compute_reach_metrics(tasks)
        strategy_miss = compute_strategy_miss_given_gold_present(tasks)

    filter_kill = compute_filter_kill_gold_rate(tasks) if outcome_metrics_available else {"numerator": 0, "denominator": 0, "rate": None}
    admission_fp = compute_admission_false_primary_rate(tasks) if outcome_metrics_available else {"numerator": 0, "denominator": 0, "rate": None, "by_strategy": {}}
    admission_false_span = compute_admission_false_span_per_no_gold_task(tasks) if outcome_metrics_available else {"total_false_spans": 0, "total_no_gold_tasks": 0, "rate": None, "by_strategy": {}}
    evidencecore_reject = compute_evidencecore_reject_rate(tasks)
    failure_funnel = compute_failure_funnel(tasks)
    outcome_fallback = compute_outcome_fallback_metrics(tasks) if outcome_metrics_available else {}

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P31 Candidate Reach Ceiling scaffold is ready; real per-task ephemeral records are required for reach metrics."
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
                f"P31 reach ceiling evaluation scored {len(tasks)} real ephemeral records."
            )
        if reach_metrics_available:
            k5 = reach["by_k"][5]
            conclusion_lines.append(
                f"Reach@5: GoldFile={k5['gold_file_reach']['rate']}, GoldSpan={k5['gold_span_reach']['rate']}, "
                f"ExactSpan={k5['gold_span_exact_reach']['rate']}, CandidateAbsent={k5['candidate_absent_rate']['rate']}, "
                f"FileRightSpanWrong={k5['file_right_span_wrong_rate']['rate']}."
            )
            conclusion_lines.append(
                "Reach metrics measure whether candidate evidence alone reaches the gold before routing/admission; "
                "they are not a promotion claim and are independent of any policy decision."
            )
        else:
            conclusion_lines.append(
                "Candidate evidence pools or embedded gold spans are missing from input records; only outcome-only fallback metrics are available."
            )
        conclusion_lines.append(
            "P31 is diagnostic-only and SCORE-phase-only; it does not influence routing or admission."
        )
        conclusion_lines.append(
            f"FilterKillGoldRate={filter_kill['rate']}; AdmissionFalsePrimaryRate={admission_fp.get('status', admission_fp.get('rate'))}; "
            f"AdmissionFalseSpanPerNoGoldTask={admission_false_span['rate']}; EvidenceCoreRejectRate={evidencecore_reject.get('status')}."
        )
        conclusion_lines.append("No policy is promotion-ready or default-ready.")
        conclusion_lines.append(
            "Next: run P31 against ephemeral records that include candidate evidence pools "
            "and compare reach ceilings across candidate_baseline, transformed strategies, and admission policies."
        )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P31 Candidate Reach Ceiling Study",
        "status": status,
        "status_reason": reason,
        "self_test": self_test,
        "not_quality_evidence": bool(self_test),
        "real_policy_evaluation": bool(status == "ok" and not self_test),
        "input_paths": [str(p) for p in input_paths] if self_test else [],
        "input_sources": ["self_test"] if self_test else ["p25-policy-records-ephemeral-v1"],
        "insufficient_input_paths": insufficient_paths or [],
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "remote_calls_by_p31": 0,
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
        "candidate_pool_availability": candidate_pool_availability,
        "candidate_pool_detected_count": sum(1 for t in tasks if t.get("has_candidate_pool")),
        "gold_span_availability": gold_span_availability,
        "positive_with_gold_spans_count": positive_with_gold_spans,
        "positive_without_gold_spans_count": positive_without_gold_spans,
        "reach_metrics_available": reach_metrics_available,
        "outcome_metrics_available": outcome_metrics_available,
        "elapsed_ms": elapsed_ms,
        "task_count": len(tasks),
        "positive_task_count": sum(1 for t in tasks if t["has_gold"]),
        "no_gold_task_count": sum(1 for t in tasks if not t["has_gold"]),
        "metrics": {
            "reach": reach,
            "strategy_miss_given_gold_present": strategy_miss,
            "filter_kill_gold_rate": filter_kill,
            "admission_false_primary_rate": admission_fp,
            "admission_false_span_per_no_gold_task": admission_false_span,
            "evidencecore_reject_rate": evidencecore_reject,
            "failure_funnel": failure_funnel,
            "outcome_only_fallback": outcome_fallback,
        },
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    violations = _reject_forbidden_keys(report)
    if violations:
        raise RuntimeError(f"P31 public report contains forbidden keys: {violations}")
    return report


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# P31 Candidate Reach Ceiling Study\n")
    lines.append(f"- Schema: `{report['schema_version']}`")
    lines.append(f"- Generated: {report['generated_at']}")
    lines.append(f"- Status: `{report['status']}`")
    lines.append(f"- Self-test: {report['self_test']}")
    lines.append(f"- Remote calls by P31: {report['remote_calls_by_p31']}")
    lines.append(f"- P31-H1 handoff detected: {report.get('p31_h1_handoff_detected', False)}\n")

    if report["status"] not in {"ok", "self_test_only"}:
        lines.append("## Status")
        if report.get("status_reason"):
            lines.append(report["status_reason"])
        lines.append("")
        lines.append(
            "The evaluator scaffold is ready. Run with `--self-test` or supply ephemeral P25/P30 SCORE-phase records."
        )
        lines.append("")
        return "\n".join(lines)

    lines.append(f"- Candidate pool availability: `{report['candidate_pool_availability']}`")
    lines.append(f"- Reach metrics available: {report['reach_metrics_available']}")
    lines.append(
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} "
        f"positive_with_gold_spans={report.get('positive_with_gold_spans_count', 0)} "
        f"no_gold={report['no_gold_task_count']}\n"
    )

    lines.append("## Reach metrics by K\n")
    lines.append(
        "| K | GoldFileReach | GoldSpanReach | GoldSpanExactReach | CandidateAbsent | FileRightSpanWrong |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|")

    def fmt_rate(m: dict[str, Any] | None) -> str:
        if not isinstance(m, dict):
            return "n/a"
        r = m.get("rate")
        return f"{r:.4f}" if isinstance(r, (int, float)) else "n/a"

    def fmt_counts(m: dict[str, Any] | None) -> str:
        if not isinstance(m, dict):
            return "n/a"
        return f"{m.get('numerator', 'n/a')}/{m.get('denominator', 'n/a')}"

    for k in K_VALUES:
        block = report["metrics"]["reach"]["by_k"].get(k) or {}
        lines.append(
            f"| {k} | {fmt_rate(block.get('gold_file_reach'))} | {fmt_rate(block.get('gold_span_reach'))} | "
            f"{fmt_rate(block.get('gold_span_exact_reach'))} | {fmt_rate(block.get('candidate_absent_rate'))} | "
            f"{fmt_rate(block.get('file_right_span_wrong_rate'))} |"
        )
    lines.append("")

    lines.append("## Reach numerators/denominators by K\n")
    lines.append(
        "| K | GoldFile | GoldSpan | GoldSpanExact | CandidateAbsent | FileRightSpanWrong |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|")
    for k in K_VALUES:
        block = report["metrics"]["reach"]["by_k"].get(k) or {}
        lines.append(
            f"| {k} | {fmt_counts(block.get('gold_file_reach'))} | {fmt_counts(block.get('gold_span_reach'))} | "
            f"{fmt_counts(block.get('gold_span_exact_reach'))} | {fmt_counts(block.get('candidate_absent_rate'))} | "
            f"{fmt_counts(block.get('file_right_span_wrong_rate'))} |"
        )
    lines.append("")

    lines.append("## P31-H1 handoff\n")
    if report.get("p31_h1_handoff_detected"):
        lines.append(
            "P31-H1 ephemeral handoff detected. Candidate pools and private SCORE-phase gold spans "
            "were read from the input records. Pool items are lightweight (`rank`, `path`, `start_line`, "
            "`end_line`, optional `content_sha`/`score`/`channels`); no snippets or provider fields are stored."
        )
    else:
        lines.append(
            "P31-H1 ephemeral handoff not detected. Reach metrics require `p31_candidate_pools` and "
            "`p31_score_gold` fields produced by `eval/p21_llm_rich_candidate.py --p25-policy-records-out`. "
            "When these fields are absent, P31 falls back to outcome-only metrics."
        )
    lines.append("")

    lines.append("## Strategy miss given gold present@K=5\n")
    lines.append("| Strategy | miss | denominator | rate |")
    lines.append("|---|---:|---:|---:|")
    miss = report["metrics"].get("strategy_miss_given_gold_present", {})
    for strategy in TRANSFORMED_STRATEGIES:
        m = miss.get(strategy, {}).get(5, {"numerator": 0, "denominator": 0, "rate": None})
        r = m.get("rate")
        rate_str = f"{r:.4f}" if isinstance(r, (int, float)) else "n/a"
        lines.append(f"| {strategy} | {m['numerator']} | {m['denominator']} | {rate_str} |")
    lines.append("")

    lines.append("## Action/strategy diagnostics\n")
    fk = report["metrics"]["filter_kill_gold_rate"]
    afp = report["metrics"]["admission_false_primary_rate"]
    afs = report["metrics"]["admission_false_span_per_no_gold_task"]
    ecr = report["metrics"]["evidencecore_reject_rate"]
    lines.append(f"- FilterKillGoldRate: {fk['rate'] if fk['rate'] is not None else 'n/a'} ({fk['numerator']}/{fk['denominator']})")
    afp_label = afp.get("status") if afp.get("status") else (afp["rate"] if afp["rate"] is not None else "n/a")
    lines.append(f"- AdmissionFalsePrimaryRate: {afp_label} ({afp['numerator']}/{afp['denominator']})")
    if afp.get("status") == "not_measured":
        lines.append(f"  - Reason: {afp.get('reason')}")
    lines.append(f"- AdmissionFalseSpanPerNoGoldTask: {afs['rate'] if afs['rate'] is not None else 'n/a'} ({afs['total_false_spans']}/{afs['total_no_gold_tasks']})")
    lines.append(f"- EvidenceCoreRejectRate: `{ecr.get('status')}` {ecr.get('rate') if ecr.get('rate') is not None else ''}")
    lines.append("")

    lines.append("## Failure funnel at K=5\n")
    funnel = report["metrics"]["failure_funnel"]
    buckets = funnel["buckets"]
    lines.append("| Stage | Count |")
    lines.append("|---|---:|")
    for key, value in buckets.items():
        lines.append(f"| {key} | {value} |")
    lines.append(f"- funnel_sums_to_positive_tasks: {funnel['funnel_sums_to_positive_tasks']}")
    lines.append("")

    if not report["reach_metrics_available"]:
        lines.append("## Outcome-only fallback metrics\n")
        lines.append("| Strategy | file_recall_at_5 | mean SpanF0.5 | mean PFP |")
        lines.append("|---|---:|---:|---:|")
        for strategy, m in report["metrics"]["outcome_only_fallback"].items():
            def fmt(x: Any) -> str:
                return f"{x:.4f}" if isinstance(x, (int, float)) else "n/a"
            lines.append(f"| {strategy} | {fmt(m['file_recall_at_5_rate'])} | {fmt(m['mean_span_f0_5'])} | {fmt(m['mean_primary_false_positive_rate'])} |")
        lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")

    lines.append("## Safety notes\n")
    lines.append("- No remote model calls were made during P31 evaluation.")
    lines.append("- Labels are loaded only after RUN for aggregate SCORE-phase metrics.")
    lines.append("- This report contains only aggregate metrics and public task metadata.")
    lines.append("- Raw queries, snippets, prompts, responses, gold spans, private labels, candidate paths/spans, and provider fields are not stored.")
    lines.append(
        "- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, "
        "`candidate_not_fact=true`, `remote_calls_by_p31=0`, `score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P31 Candidate Reach Ceiling Study")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25/P30 JSON record files.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_input_records: list[dict[str, Any]] = []

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_input_records = make_self_test_records()
    elif args.input:
        input_paths = list(args.input)
        raw_input_records = p25.load_p21_inputs(input_paths, require_ephemeral_schema=True)
    else:
        parser.error("Specify --self-test or --input PATH [PATH ...]")

    status = "self_test_only" if args.self_test else "ok"
    reason: str | None = None
    insufficient_paths: list[str] = []
    task_records: list[dict[str, Any]] = []

    for rec in raw_input_records:
        if rec.get("_p25_input_summary_marker"):
            status = "insufficient_task_detail"
            reason = "Aggregate summary lacks per-task ephemeral records required for P31 reach metrics."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        if rec.get("_p25_input_empty_marker"):
            status = "insufficient_task_detail"
            reason = "Input artifact did not contain per-task ephemeral records."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        if rec.get("_p25_unsupported_schema_marker"):
            status = "insufficient_task_detail"
            reason = "P31 real evaluation requires p25-policy-records-ephemeral-v1 input schema or equivalent per-task records."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        task_records.append(rec)

    if not task_records and status == "ok":
        status = "insufficient_task_detail"
        reason = "No per-task records found."

    normalized_tasks = [nt for nt in (normalize_task(raw) for raw in task_records) if nt]

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P31 normalization."

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
    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    errors = validate_report(report)
    if errors:
        raise RuntimeError(f"P31 report validation failed: {errors}")

    print(f"P31 report written to {args.out}")
    print(f"P31 markdown written to {args.doc}")
    print("P31 report validation ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
