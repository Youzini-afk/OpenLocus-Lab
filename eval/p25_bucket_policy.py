#!/usr/bin/env python3
"""P25 Bucket-Routed LLM Role Policy evaluator.

This evaluator consumes existing P21 rich-candidate per-task JSON reports or
synthetic self-test artifacts and compares five candidate policies for routing
LLM roles by public task bucket.

Safety constraints:
- No remote model calls; deterministic local evaluation only.
- Does not modify Rust core or EvidenceCore semantics.
- Artifacts never contain raw queries, raw snippets, prompts/responses, gold
  spans, private labels, provider keys, or provider-specific fields.
- Promotion/default recommendations are always false.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "p25-bucket-policy-v1"
GENERATED_BY = "eval/p25_bucket_policy.py"

POLICIES = [
    "candidate_baseline",
    "global_span_narrow",
    "global_filter",
    "global_abstain_filter",
    "bucket_routed_v0",
]

# Public bucket/risk keywords used for routing decisions.
POSITIVE_BUCKET_KEYS = {
    "positive",
    "likely_positive",
    "high_confidence",
    "exact_symbol",
    "config",
    "route_handler",
}
NEGATIVE_BUCKET_KEYS = {
    "negative",
    "dense_false_positive",
    "ambiguous",
    "hallucination_risk",
    "weak_candidates",
    "dense_quiver_trap",
    "stale-like",
    "hard_distractor",
}

PUBLIC_BUCKET_ALLOWLIST = {
    "positive",
    "negative",
    "ambiguous",
    "hard_distractor",
    "stale-like",
    "dense_quiver_trap",
    "exact_symbol_unique",
    "config",
    "route_handler",
    "other",
    "unknown",
}

PUBLIC_TAG_ALLOWLIST = {
    "exact_symbol_match",
    "exact_symbol",
    "unique_symbol",
    "symbol_anchor",
    "config",
    "route_handler",
    "positive",
    "likely_positive",
    "high_confidence",
    "negative",
    "ambiguous",
    "hallucination_risk",
    "same_name_disambiguation",
    "test_source_confusion",
    "same_name_symbol",
    "frontend_backend_confusion",
    "generated_vendor",
    "stale_index_like",
    "stale_index_confusion",
    "dense_false_positive",
    "quiver_not_implemented",
    "hard_distractor",
    "weak_candidates",
    "other",
}

STRATEGIES = {
    "candidate_baseline": "candidate_baseline",
    "llm_span_narrow": "llm_span_narrow",
    "llm_filter": "llm_filter",
    "llm_abstain_filter": "llm_abstain_filter",
}

DEFAULT_OUT = Path("artifacts/p25_bucket_policy/p25_bucket_policy_report.json")
DEFAULT_DOC = Path("docs/en/p25-bucket-routed-policy.md")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_summary_like(obj: dict[str, Any]) -> bool:
    """Heuristic: top-level items typical of aggregate summary artifacts."""
    schema = obj.get("schema_version", "")
    if isinstance(schema, str) and "summary" in schema.lower():
        return True
    if "by_model" in obj and "aggregate_by_strategy" in obj:
        return True
    if "bucket_summary" in obj and "by_model" in obj:
        return True
    if "aggregate_by_strategy" in obj and "records" not in obj:
        return True
    if "strategy_results" in obj and "records" not in obj and "tasks" not in obj and "task_results" not in obj and "per_task_results" not in obj:
        return True
    return False


def load_p21_inputs(input_paths: list[Path], *, require_ephemeral_schema: bool = True) -> list[dict[str, Any]]:
    """Load JSON artifacts and merge per-task records when available."""
    all_per_task: list[dict[str, Any]] = []
    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(f"P21 input not found: {path}")
        obj = json.loads(path.read_text(encoding="utf-8"))
        if is_summary_like(obj):
            # Aggregate summaries do not carry per-task records needed for
            # bucket routing. Keep a marker so the caller can refuse to
            # pretend it evaluated policy.
            all_per_task.append({"_p25_input_summary_marker": True, "path": str(path)})
            continue
        if isinstance(obj.get("records"), list) and obj.get("schema_version") == "p25-policy-records-ephemeral-v1":
            all_per_task.extend([row for row in obj.get("records", []) if isinstance(row, dict)])
            continue
        if require_ephemeral_schema:
            all_per_task.append({"_p25_unsupported_schema_marker": True, "path": str(path), "schema_version": obj.get("schema_version")})
            continue
        # P21 per-run reports may carry tasks under several shapes.
        candidates: list[list[dict[str, Any]]] = [
            obj.get("tasks", []),
            obj.get("task_results", []),
            obj.get("per_task_results", []),
        ]
        found: list[dict[str, Any]] = []
        for block in candidates:
            if isinstance(block, list):
                found = [row for row in block if isinstance(row, dict)]
                if found:
                    break
        # A remote per-run report may instead only have "decision_records".
        if not found and isinstance(obj.get("decision_records"), list):
            found = obj.get("decision_records", [])
        if found:
            all_per_task.extend(found)
        else:
            all_per_task.append({"_p25_input_empty_marker": True, "path": str(path)})
    return all_per_task


def sanitize_public_bucket(value: Any) -> str:
    token = str(value or "unknown")
    return token if token in PUBLIC_BUCKET_ALLOWLIST else "other"


def sanitize_public_tags(values: list[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        token = str(value)
        if token in PUBLIC_TAG_ALLOWLIST and token not in out:
            out.append(token)
    return out or ["other"]


def normalize_task(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Extract public task fields and per-strategy outcomes from a P21 record."""
    tid = raw.get("task_id") or raw.get("test_id")
    if not tid:
        return None

    task_bucket = sanitize_public_bucket(raw.get("task_bucket", "unknown"))
    risk_tags = raw.get("task_risk_tags") or []
    if isinstance(risk_tags, str):
        risk_tags = [risk_tags]
    if not isinstance(risk_tags, list):
        risk_tags = []
    risk_tags = sanitize_public_tags(risk_tags)
    if raw.get("score_group") == "positive":
        has_gold = True
    elif raw.get("score_group") == "no_gold":
        has_gold = False
    else:
        has_gold = bool(raw.get("has_gold", False))
    route_features_raw = raw.get("route_features")
    route_features = route_features_raw if isinstance(route_features_raw, dict) else {}

    def _extract(name: str) -> dict[str, Any]:
        src = raw.get(name)
        if isinstance(src, dict):
            return src
        # Accept nested under "strategies" or "outcomes".
        for key in ("strategies", "outcomes", "strategy_results", "results", "metrics"):
            container = raw.get(key) or {}
            if isinstance(container, dict) and name in container:
                s = container[name]
                if isinstance(s, dict):
                    return s
        return {}

    def _as_floats(src: dict[str, Any], *keys: str) -> dict[str, float | None]:
        out: dict[str, float | None] = {}
        for k in keys:
            v = src.get(k, src.get(k.replace("_", ""), None))
            try:
                out[k] = float(v)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                out[k] = None
        return out

    def _as_ints(src: dict[str, Any], *keys: str) -> dict[str, int | None]:
        out: dict[str, int | None] = {}
        for k in keys:
            v = src.get(k)
            try:
                out[k] = int(v)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                out[k] = None
        return out

    def _as_bool(src: dict[str, Any], *keys: str) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for k in keys:
            out[k] = bool(src.get(k, False))
        return out

    base = _extract("candidate_baseline")
    span = _extract("llm_span_narrow")
    filt = _extract("llm_filter")
    abst = _extract("llm_abstain_filter")

    base_floats = _as_floats(
        base, "file_recall_at_5", "span_f0_5", "primary_false_positive_rate",
        "no_gold_false_primary_rate"
    )
    span_floats = _as_floats(
        span, "file_recall_at_5", "span_f0_5", "primary_false_positive_rate",
        "no_gold_false_primary_rate"
    )
    filt_floats = _as_floats(
        filt, "file_recall_at_5", "span_f0_5", "primary_false_positive_rate",
        "no_gold_false_primary_rate"
    )
    abst_floats = _as_floats(
        abst, "file_recall_at_5", "span_f0_5", "primary_false_positive_rate",
        "no_gold_false_primary_rate", "abstain_rate"
    )

    base_ints = _as_ints(base, "added_gold_span", "added_false_span")
    span_ints = _as_ints(span, "added_gold_span", "added_false_span")
    filt_ints = _as_ints(filt, "added_gold_span", "added_false_span")
    abst_ints = _as_ints(abst, "added_gold_span", "added_false_span")

    abst_bools = _as_bool(abst, "abstained")

    return {
        "task_id": tid,
        "repo_id": raw.get("repo_id"),
        "task_bucket": task_bucket,
        "task_risk_tags": risk_tags,
        "has_gold": has_gold,
        "route_features": {
            "candidate_count": int(route_features.get("candidate_count") or 0),
            "candidate_support_exists": bool(route_features.get("candidate_support_exists", bool(route_features.get("candidate_count")))),
            "unique_symbol_anchor": bool(route_features.get("unique_symbol_anchor", False)),
        },
        "outcomes": {
            "candidate_baseline": {
                **base_floats,
                **base_ints,
                "abstained": False,
            },
            "llm_span_narrow": {
                **span_floats,
                **span_ints,
                "abstained": False,
            },
            "llm_filter": {
                **filt_floats,
                **filt_ints,
                "abstained": False,
            },
            "llm_abstain_filter": {
                **abst_floats,
                **abst_ints,
                **abst_bools,
            },
        },
    }


def make_self_test_tasks() -> list[dict[str, Any]]:
    """Synthetic per-task decision table for deterministic self-test."""
    tasks: list[dict[str, Any]] = [
        # Positive / high-confidence primary evidence
        {
            "task_id": "p25-001",
            "repo_id": "py_flask",
            "task_bucket": "positive",
            "task_risk_tags": ["high_confidence", "primary_evidence"],
            "has_gold": True,
            "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.31,
                                   "primary_false_positive_rate": 0.05,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 1, "added_false_span": 1},
            "llm_span_narrow": {"file_recall_at_5": 1.0, "span_f0_5": 0.40,
                                "primary_false_positive_rate": 0.0,
                                "no_gold_false_primary_rate": 0.0,
                                "added_gold_span": 1, "added_false_span": 0},
            "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.25,
                           "primary_false_positive_rate": 0.0,
                           "no_gold_false_primary_rate": 0.0,
                           "added_gold_span": 0, "added_false_span": 0},
            "llm_abstain_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.20,
                                   "primary_false_positive_rate": 0.0,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 0, "added_false_span": 0,
                                   "abstained": True},
        },
        {
            "task_id": "p25-002",
            "repo_id": "py_flask",
            "task_bucket": "positive",
            "task_risk_tags": ["likely_positive", "route_handler"],
            "has_gold": True,
            "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.20,
                                   "primary_false_positive_rate": 0.10,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 1, "added_false_span": 2},
            "llm_span_narrow": {"file_recall_at_5": 1.0, "span_f0_5": 0.28,
                                "primary_false_positive_rate": 0.0,
                                "no_gold_false_primary_rate": 0.0,
                                "added_gold_span": 1, "added_false_span": 1},
            "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.18,
                           "primary_false_positive_rate": 0.0,
                           "no_gold_false_primary_rate": 0.0,
                           "added_gold_span": 0, "added_false_span": 0},
            "llm_abstain_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.15,
                                   "primary_false_positive_rate": 0.0,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 0, "added_false_span": 0,
                                   "abstained": True},
        },
        # Exact symbol + unique anchor -> skip LLM, baseline keeps it safe
        {
            "task_id": "p25-003",
            "repo_id": "py_flask",
            "task_bucket": "exact_symbol_unique",
            "task_risk_tags": ["exact_symbol", "unique_symbol"],
            "has_gold": True,
            "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.45,
                                   "primary_false_positive_rate": 0.0,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 1, "added_false_span": 0},
            "llm_span_narrow": {"file_recall_at_5": 1.0, "span_f0_5": 0.42,
                                "primary_false_positive_rate": 0.0,
                                "no_gold_false_primary_rate": 0.0,
                                "added_gold_span": 1, "added_false_span": 0},
            "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.35,
                           "primary_false_positive_rate": 0.0,
                           "no_gold_false_primary_rate": 0.0,
                           "added_gold_span": 0, "added_false_span": 0},
            "llm_abstain_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.33,
                                   "primary_false_positive_rate": 0.0,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 0, "added_false_span": 0,
                                   "abstained": True},
        },
        # Config / route-like positive without strong symbol
        {
            "task_id": "p25-004",
            "repo_id": "js_express",
            "task_bucket": "config",
            "task_risk_tags": ["config", "positive"],
            "has_gold": True,
            "candidate_baseline": {"file_recall_at_5": 0.8, "span_f0_5": 0.10,
                                   "primary_false_positive_rate": 0.20,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 1, "added_false_span": 4},
            "llm_span_narrow": {"file_recall_at_5": 0.8, "span_f0_5": 0.12,
                                "primary_false_positive_rate": 0.05,
                                "no_gold_false_primary_rate": 0.0,
                                "added_gold_span": 1, "added_false_span": 2},
            "llm_filter": {"file_recall_at_5": 0.8, "span_f0_5": 0.05,
                           "primary_false_positive_rate": 0.0,
                           "no_gold_false_primary_rate": 0.0,
                           "added_gold_span": 0, "added_false_span": 0},
            "llm_abstain_filter": {"file_recall_at_5": 0.8, "span_f0_5": 0.04,
                                   "primary_false_positive_rate": 0.0,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 0, "added_false_span": 0,
                                   "abstained": True},
        },
        # Negative / no-gold buckets
        {
            "task_id": "p25-005",
            "repo_id": "js_express",
            "task_bucket": "negative",
            "task_risk_tags": ["no_gold", "negative"],
            "has_gold": False,
            "candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                   "primary_false_positive_rate": 0.40,
                                   "no_gold_false_primary_rate": 0.40,
                                   "added_gold_span": 0, "added_false_span": 4},
            "llm_span_narrow": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                "primary_false_positive_rate": 0.30,
                                "no_gold_false_primary_rate": 0.30,
                                "added_gold_span": 0, "added_false_span": 3},
            "llm_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                           "primary_false_positive_rate": 0.10,
                           "no_gold_false_primary_rate": 0.10,
                           "added_gold_span": 0, "added_false_span": 1},
            "llm_abstain_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                   "primary_false_positive_rate": 0.05,
                                   "no_gold_false_primary_rate": 0.05,
                                   "added_gold_span": 0, "added_false_span": 0,
                                   "abstained": True},
        },
        {
            "task_id": "p25-006",
            "repo_id": "js_express",
            "task_bucket": "negative",
            "task_risk_tags": ["no_gold", "negative"],
            "has_gold": False,
            "candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                   "primary_false_positive_rate": 0.60,
                                   "no_gold_false_primary_rate": 0.60,
                                   "added_gold_span": 0, "added_false_span": 6},
            "llm_span_narrow": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                "primary_false_positive_rate": 0.45,
                                "no_gold_false_primary_rate": 0.45,
                                "added_gold_span": 0, "added_false_span": 5},
            "llm_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                           "primary_false_positive_rate": 0.20,
                           "no_gold_false_primary_rate": 0.20,
                           "added_gold_span": 0, "added_false_span": 2},
            "llm_abstain_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                   "primary_false_positive_rate": 0.10,
                                   "no_gold_false_primary_rate": 0.10,
                                   "added_gold_span": 0, "added_false_span": 1,
                                   "abstained": True},
        },
        # Dense false positive
        {
            "task_id": "p25-007",
            "repo_id": "js_express",
            "task_bucket": "dense_quiver_trap",
            "task_risk_tags": ["dense_false_positive"],
            "has_gold": True,
            "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.12,
                                   "primary_false_positive_rate": 0.50,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 1, "added_false_span": 6},
            "llm_span_narrow": {"file_recall_at_5": 1.0, "span_f0_5": 0.08,
                                "primary_false_positive_rate": 0.35,
                                "no_gold_false_primary_rate": 0.0,
                                "added_gold_span": 1, "added_false_span": 5},
            "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.05,
                           "primary_false_positive_rate": 0.05,
                           "no_gold_false_primary_rate": 0.0,
                           "added_gold_span": 0, "added_false_span": 1},
            "llm_abstain_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.02,
                                   "primary_false_positive_rate": 0.0,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 0, "added_false_span": 0,
                                   "abstained": True},
        },
        {
            "task_id": "p25-008",
            "repo_id": "js_express",
            "task_bucket": "dense_quiver_trap",
            "task_risk_tags": ["dense_false_positive", "hard_distractor"],
            "has_gold": False,
            "candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                   "primary_false_positive_rate": 0.80,
                                   "no_gold_false_primary_rate": 0.80,
                                   "added_gold_span": 0, "added_false_span": 8},
            "llm_span_narrow": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                "primary_false_positive_rate": 0.70,
                                "no_gold_false_primary_rate": 0.70,
                                "added_gold_span": 0, "added_false_span": 7},
            "llm_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                           "primary_false_positive_rate": 0.30,
                           "no_gold_false_primary_rate": 0.30,
                           "added_gold_span": 0, "added_false_span": 3},
            "llm_abstain_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                   "primary_false_positive_rate": 0.25,
                                   "no_gold_false_primary_rate": 0.25,
                                   "added_gold_span": 0, "added_false_span": 2,
                                   "abstained": True},
        },
        # Ambiguous buckets
        {
            "task_id": "p25-009",
            "repo_id": "py_flask",
            "task_bucket": "ambiguous",
            "task_risk_tags": ["ambiguous", "weak_candidates"],
            "has_gold": True,
            "candidate_baseline": {"file_recall_at_5": 0.6, "span_f0_5": 0.05,
                                   "primary_false_positive_rate": 0.30,
                                   "no_gold_false_positive_rate": 0.0,
                                   "added_gold_span": 1, "added_false_span": 4},
            "llm_span_narrow": {"file_recall_at_5": 0.6, "span_f0_5": 0.03,
                                "primary_false_positive_rate": 0.25,
                                "no_gold_false_primary_rate": 0.0,
                                "added_gold_span": 0, "added_false_span": 3},
            "llm_filter": {"file_recall_at_5": 0.6, "span_f0_5": 0.02,
                           "primary_false_positive_rate": 0.10,
                           "no_gold_false_primary_rate": 0.0,
                           "added_gold_span": 0, "added_false_span": 1},
            "llm_abstain_filter": {"file_recall_at_5": 0.6, "span_f0_5": 0.0,
                                   "primary_false_positive_rate": 0.05,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 0, "added_false_span": 0,
                                   "abstained": True},
        },
        {
            "task_id": "p25-010",
            "repo_id": "py_flask",
            "task_bucket": "ambiguous",
            "task_risk_tags": ["ambiguous", "hallucination_risk"],
            "has_gold": False,
            "candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                   "primary_false_positive_rate": 0.55,
                                   "no_gold_false_primary_rate": 0.55,
                                   "added_gold_span": 0, "added_false_span": 5},
            "llm_span_narrow": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                "primary_false_positive_rate": 0.45,
                                "no_gold_false_primary_rate": 0.45,
                                "added_gold_span": 0, "added_false_span": 4},
            "llm_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                           "primary_false_positive_rate": 0.15,
                           "no_gold_false_primary_rate": 0.15,
                           "added_gold_span": 0, "added_false_span": 1},
            "llm_abstain_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0,
                                   "primary_false_positive_rate": 0.10,
                                   "no_gold_false_primary_rate": 0.10,
                                   "added_gold_span": 0, "added_false_span": 0,
                                   "abstained": True},
        },
        # Weak candidates positive
        {
            "task_id": "p25-011",
            "repo_id": "py_flask",
            "task_bucket": "ambiguous",
            "task_risk_tags": ["weak_candidates"],
            "has_gold": True,
            "candidate_baseline": {"file_recall_at_5": 0.4, "span_f0_5": 0.0,
                                   "primary_false_positive_rate": 0.25,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 0, "added_false_span": 3},
            "llm_span_narrow": {"file_recall_at_5": 0.4, "span_f0_5": 0.0,
                                "primary_false_positive_rate": 0.20,
                                "no_gold_false_primary_rate": 0.0,
                                "added_gold_span": 0, "added_false_span": 2},
            "llm_filter": {"file_recall_at_5": 0.4, "span_f0_5": 0.0,
                           "primary_false_positive_rate": 0.05,
                           "no_gold_false_primary_rate": 0.0,
                           "added_gold_span": 0, "added_false_span": 0},
            "llm_abstain_filter": {"file_recall_at_5": 0.4, "span_f0_5": 0.0,
                                   "primary_false_positive_rate": 0.0,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 0, "added_false_span": 0,
                                   "abstained": True},
        },
        # Fallback candidate baseline for unknown bucket
        {
            "task_id": "p25-012",
            "repo_id": "js_express",
            "task_bucket": "unknown",
            "task_risk_tags": ["other"],
            "has_gold": True,
            "candidate_baseline": {"file_recall_at_5": 0.5, "span_f0_5": 0.15,
                                   "primary_false_positive_rate": 0.15,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 1, "added_false_span": 2},
            "llm_span_narrow": {"file_recall_at_5": 0.5, "span_f0_5": 0.16,
                                "primary_false_positive_rate": 0.10,
                                "no_gold_false_primary_rate": 0.0,
                                "added_gold_span": 1, "added_false_span": 1},
            "llm_filter": {"file_recall_at_5": 0.5, "span_f0_5": 0.12,
                           "primary_false_positive_rate": 0.05,
                           "no_gold_false_primary_rate": 0.0,
                           "added_gold_span": 0, "added_false_span": 0},
            "llm_abstain_filter": {"file_recall_at_5": 0.5, "span_f0_5": 0.10,
                                   "primary_false_positive_rate": 0.05,
                                   "no_gold_false_primary_rate": 0.0,
                                   "added_gold_span": 0, "added_false_span": 0,
                                   "abstained": True},
        },
    ]
    for task in tasks:
        tags = task.get("task_risk_tags") or []
        task["route_features"] = {
            "candidate_count": 3,
            "candidate_support_exists": True,
            "unique_symbol_anchor": "unique_symbol" in tags,
        }
    return [nt for nt in (normalize_task(t) for t in tasks) if nt is not None]


def bucket_labels(task: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    if task.get("task_bucket"):
        labels.add(str(task["task_bucket"]))
    for tag in task.get("task_risk_tags", []):
        if isinstance(tag, str):
            labels.add(tag)
    return labels


def choose_negative_strategy(tasks: list[dict[str, Any]]) -> str:
    """A priori negative-bucket policy.

    Do not calibrate from the same scored task set; that would leak labels into
    routing. Dense/ambiguous buckets are handled explicitly in routing below.
    """
    return "llm_abstain_filter"


def route_bucket_routed_v0(task: dict[str, Any], calibrated_negative: str) -> str:
    labels = bucket_labels(task)
    route_features = task.get("route_features") or {}
    support_exists = bool(route_features.get("candidate_support_exists")) or int(route_features.get("candidate_count") or 0) > 0

    exact_unique = (
        ("exact_symbol" in labels or "exact_symbol_unique" in labels or "exact_symbol_match" in labels)
        and ("unique" in labels or "unique_symbol" in labels or "symbol_anchor" in labels)
    )
    if exact_unique:
        return "candidate_baseline"

    is_positive = bool(labels & POSITIVE_BUCKET_KEYS)
    is_negative = bool(labels & NEGATIVE_BUCKET_KEYS)

    if is_positive and support_exists:
        return "llm_span_narrow"

    if is_negative:
        # Baseline default heuristics per spec, overridable by calibration.
        if "dense_false_positive" in labels or "dense_quiver_trap" in labels or "ambiguous" in labels:
            return "llm_filter"
        return "llm_abstain_filter"

    return "candidate_baseline"


def gather_policy_action(tasks: list[dict[str, Any]], policy: str) -> list[str]:
    actions: list[str] = []
    if policy == "bucket_routed_v0":
        calibrated = choose_negative_strategy(tasks)
        for task in tasks:
            actions.append(route_bucket_routed_v0(task, calibrated))
    elif policy == "candidate_baseline":
        actions.extend(["candidate_baseline"] * len(tasks))
    elif policy in ("global_span_narrow", "llm_span_narrow"):
        actions.extend(["llm_span_narrow"] * len(tasks))
    elif policy in ("global_filter", "llm_filter"):
        actions.extend(["llm_filter"] * len(tasks))
    elif policy in ("global_abstain_filter", "llm_abstain_filter"):
        actions.extend(["llm_abstain_filter"] * len(tasks))
    return actions


def aggregate_policy(
    tasks: list[dict[str, Any]],
    policy: str,
) -> dict[str, Any]:
    actions = gather_policy_action(tasks, policy)

    task_count = len(tasks)
    positive_task_count = sum(1 for t in tasks if t.get("has_gold"))
    no_gold_task_count = task_count - positive_task_count

    file_recalls: list[float] = []
    span_f0_5s: list[float] = []
    pfps: list[float] = []
    added_gold_sum = 0
    added_false_sum = 0
    no_gold_fp_sum = 0.0
    no_gold_fp_count = 0
    filter_killed_gold = 0
    abstain_count = 0
    candidate_success_count = 0
    model_success_count = 0
    admission_success_count = 0
    evidence_success_count = 0

    for task, action in zip(tasks, actions):
        outcome = task["outcomes"][action]
        baseline = task["outcomes"]["candidate_baseline"]

        fr = outcome.get("file_recall_at_5")
        if fr is not None:
            file_recalls.append(fr)
        sf = outcome.get("span_f0_5")
        if sf is not None:
            span_f0_5s.append(sf)
        pfp = outcome.get("primary_false_positive_rate")
        if pfp is not None:
            pfps.append(pfp)
        ag = outcome.get("added_gold_span") or 0
        af = outcome.get("added_false_span") or 0
        added_gold_sum += ag
        added_false_sum += af

        if not task.get("has_gold", False):
            ngp = outcome.get("no_gold_false_primary_rate")
            if ngp is None and pfp is not None:
                ngp = pfp
            if ngp is not None:
                no_gold_fp_sum += ngp
                no_gold_fp_count += 1

        if action in ("llm_filter", "llm_abstain_filter"):
            if baseline.get("added_gold_span", 0) > 0 and ag == 0:
                filter_killed_gold += 1

        if action == "llm_abstain_filter" and outcome.get("abstained", False):
            abstain_count += 1

        # Success layers (best-effort proxies based on available strategy deltas).
        baseline_fr = baseline.get("file_recall_at_5", 0.0) or 0.0
        candidate_success = baseline_fr > 0 or baseline.get("added_gold_span", 0) > 0
        if candidate_success:
            candidate_success_count += 1

        model_success = False
        if action == "candidate_baseline":
            model_success = candidate_success
        elif action == "llm_span_narrow":
            model_success = (ag > 0 or outcome.get("span_f0_5", 0.0) > baseline.get("span_f0_5", 0.0))
        else:
            # Filter/abstain considered successful if they suppress false primary
            # without killing gold vs. baseline.
            killed_gold = baseline.get("added_gold_span", 0) > 0 and ag == 0
            model_success = (not killed_gold) and (
                outcome.get("primary_false_positive_rate", 1.0) <= baseline.get("primary_false_positive_rate", 1.0)
            )
        if model_success:
            model_success_count += 1

        # Admission success: no new false primary relative to baseline estimate.
        admit = (
            outcome.get("primary_false_positive_rate", baseline.get("primary_false_positive_rate", 1.0))
            <= baseline.get("primary_false_positive_rate", 1.0)
        )
        if admit:
            admission_success_count += 1

        # Evidence success: final span quality matches or exceeds baseline.
        ev = candidate_success and (
            (outcome.get("span_f0_5", 0.0) >= baseline.get("span_f0_5", 0.0))
            or (action != "candidate_baseline" and ag > 0 and af == 0)
        )
        if ev:
            evidence_success_count += 1

    action_counts: dict[str, int] = defaultdict(int)
    for action in actions:
        action_counts[action] += 1

    def avg(vals: list[float]) -> float | None:
        return sum(vals) / len(vals) if vals else None

    pfp_avg = avg(pfps)
    filter_gold_kill_rate: float | None = None
    if positive_task_count:
        filter_gold_kill_rate = filter_killed_gold / positive_task_count

    return {
        "task_count": task_count,
        "positive_task_count": positive_task_count,
        "no_gold_task_count": no_gold_task_count,
        "FileRecall@5": avg(file_recalls),
        "SpanF0.5": avg(span_f0_5s),
        "added_gold_span": added_gold_sum,
        "added_false_span": added_false_sum,
        "primary_false_positive_rate": pfp_avg,
        "no_gold_false_primary_rate": (no_gold_fp_sum / no_gold_fp_count if no_gold_fp_count else None),
        "filter_gold_kill_rate": filter_gold_kill_rate,
        "abstain_rate": (abstain_count / task_count if task_count else None),
        "policy_action_counts": dict(action_counts),
        "success_layers": {
            "candidate_success": {
                "count": candidate_success_count,
                "rate": candidate_success_count / task_count if task_count else None,
            },
            "model_success": {
                "count": model_success_count,
                "rate": model_success_count / task_count if task_count else None,
            },
            "admission_success": {
                "count": admission_success_count,
                "rate": admission_success_count / task_count if task_count else None,
            },
            "evidence_success": {
                "count": evidence_success_count,
                "rate": evidence_success_count / task_count if task_count else None,
            },
        },
    }


def build_report(
    tasks: list[dict[str, Any]],
    input_paths: list[Path],
    self_test: bool,
    elapsed_ms: int,
    status: str,
    reason: str | None,
    insufficient_paths: list[str] | None = None,
) -> dict[str, Any]:
    policy_comparison: dict[str, Any] = {}
    per_task_routing: list[dict[str, Any]] = []

    if status in {"ok", "self_test_only"}:
        calibrated_negative = choose_negative_strategy(tasks)
        for policy in POLICIES:
            policy_comparison[policy] = aggregate_policy(tasks, policy)
        if self_test:
            for task in tasks:
                route = route_bucket_routed_v0(task, calibrated_negative)
                per_task_routing.append({
                    "task_id": task["task_id"],
                    "repo_id": task.get("repo_id"),
                    "task_bucket": task.get("task_bucket"),
                    "task_risk_tags": task.get("task_risk_tags"),
                    "bucket_routed_v0_action": route,
                })

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P25 policy evaluator scaffold is ready; real per-task P21 rich-candidate artifacts are required."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        baseline = policy_comparison["candidate_baseline"]
        routed = policy_comparison["bucket_routed_v0"]
        if self_test:
            conclusion_lines.append(
                f"Self-test-only scaffold evaluated {baseline['task_count']} synthetic tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P25 policy evaluation scored {baseline['task_count']} real per-task P21 records."
            )
        cal = choose_negative_strategy(tasks)
        conclusion_lines.append(
            f"Bucket-routed v0 uses a priori negative strategy '{cal}' and routes span_narrow to likely-positive tasks."
        )
        bfr = routed.get("FileRecall@5")
        bsp = routed.get("SpanF0.5")
        bfp = routed.get("primary_false_positive_rate")
        ifr = baseline.get("FileRecall@5")
        isp = baseline.get("SpanF0.5")
        conclusion_lines.append(
            f"Baseline FileRecall@5={ifr}, SpanF0.5={isp}; routed FileRecall@5={bfr}, SpanF0.5={bsp}, PFP={bfp}."
        )
        conclusion_lines.append("No policy is promotion-ready or default-ready.")

    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P25 bucket-routed LLM role policy evaluator",
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
        "external_calls": 0,
        "run_phase_public_only": True,
        "labels_loaded_after_run": True,
        "candidate_not_fact": True,
        "llm_direct_evidence_allowed": False,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_text_stored": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "elapsed_ms": elapsed_ms,
        "policy_comparison": policy_comparison,
        "bucket_routed_v0": {
            "fixed_negative_strategy": (
                choose_negative_strategy(tasks) if status in {"ok", "self_test_only"} else None
            ),
            "per_task_routing": per_task_routing,
            "routing_rules": [
                "exact_symbol + unique symbol/symbol anchor -> candidate_baseline (skip LLM)",
                "positive/likely_positive/high_confidence/config/route_handler with support -> llm_span_narrow",
                "negative/dense_false_positive/ambiguous/hallucination_risk/weak_candidates -> fixed filter/abstain",
                "otherwise -> candidate_baseline",
            ],
        },
        "conclusion": conclusion_lines,
    }
    return report


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# P25 Bucket-Routed LLM Role Policy Report\n")
    lines.append(f"- Schema: `{report['schema_version']}`")
    lines.append(f"- Generated: {report['generated_at']}")
    lines.append(f"- Status: `{report['status']}`")
    lines.append(f"- Self-test: {report['self_test']}\n")

    if report["status"] not in {"ok", "self_test_only"}:
        lines.append("## Status")
        if report.get("status_reason"):
            lines.append(report["status_reason"])
        lines.append("")
        lines.append(
            "The evaluator scaffold is ready. Run with `--self-test` or supply P21 "
            "per-task rich-candidate JSON reports that include per-task strategy outcomes."
        )
        lines.append("")
        return "\n".join(lines)

    lines.append("## Policies compared\n")
    lines.append("| Policy | Description |")
    lines.append("|---|---|")
    lines.append("| candidate_baseline | No LLM; use local candidate baseline strategy. |")
    lines.append("| global_span_narrow | Run `llm_span_narrow` on every task. |")
    lines.append("| global_filter | Run `llm_filter` on every task. |")
    lines.append("| global_abstain_filter | Run `llm_abstain_filter` on every task. |")
    lines.append(
        "| bucket_routed_v0 | Route by public `task_bucket`/`task_risk_tags`: "
        "span_narrow on positive/high-confidence buckets, filter/abstain on negative/dense-false-positive buckets, "
        "skip LLM for exact-symbol+unique-anchor tasks, fallback otherwise. |"
    )
    lines.append("")

    lines.append("## Aggregate results\n")
    header = (
        "| Policy | tasks | +tasks | no_gold | FileRecall@5 | SpanF0.5 | added_gold | added_false | "
        "PFP | no_gold PFP | filter_kill_rate | abstain_rate |"
    )
    lines.append(header)
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for policy in POLICIES:
        m = report["policy_comparison"][policy]
        def fmt(x: Any) -> str:
            return f"{x:.4f}" if isinstance(x, (int, float)) else (str(x) if x is not None else "n/a")
        lines.append(
            f"| {policy} | {m['task_count']} | {m['positive_task_count']} | {m['no_gold_task_count']} | "
            f"{fmt(m['FileRecall@5'])} | {fmt(m['SpanF0.5'])} | {m['added_gold_span']} | {m['added_false_span']} | "
            f"{fmt(m['primary_false_positive_rate'])} | {fmt(m['no_gold_false_primary_rate'])} | "
            f"{fmt(m['filter_gold_kill_rate'])} | {fmt(m['abstain_rate'])} |"
        )
    lines.append("")

    lines.append("## Success layers\n")
    lines.append("| Policy | candidate_success | model_success | admission_success | evidence_success |")
    lines.append("|---|---:|---:|---:|---:|")
    for policy in POLICIES:
        sl = report["policy_comparison"][policy]["success_layers"]
        def rate(sl_: dict[str, Any]) -> str:
            return f"{sl_['count']} ({sl_['rate']:.2%})"
        lines.append(
            f"| {policy} | {rate(sl['candidate_success'])} | {rate(sl['model_success'])} | "
            f"{rate(sl['admission_success'])} | {rate(sl['evidence_success'])} |"
        )
    lines.append("")

    lines.append("## bucket_routed_v0 routing rules\n")
    for rule in report["bucket_routed_v0"]["routing_rules"]:
        lines.append(f"- {rule}")
    lines.append(f"- Fixed negative strategy: `{report['bucket_routed_v0']['fixed_negative_strategy']}`\n")

    if report.get("self_test"):
        lines.append("## Per-task routing (self-test only)\n")
        lines.append("| task_id | repo_id | task_bucket | task_risk_tags | action |")
        lines.append("|---|---|---|---|---|")
        for row in report["bucket_routed_v0"]["per_task_routing"]:
            tags = ", ".join(row.get("task_risk_tags") or [])
            lines.append(
                f"| {row['task_id']} | {row.get('repo_id') or ''} | {row.get('task_bucket') or ''} | "
                f"{tags} | {row['bucket_routed_v0_action']} |"
            )
        lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")

    lines.append("## Safety notes\n")
    lines.append("- No remote model calls were made during policy evaluation.")
    lines.append("- This report contains only public task metadata, strategy names, and aggregate metrics.")
    lines.append("- Raw queries, snippets, prompts, responses, gold spans, private labels, provider keys, and provider fields are not stored.")
    lines.append("- `promotion_ready=false`, `default_should_change=false`, `external_calls=0`.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P25 Bucket-Routed LLM Role Policy evaluator")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to P21 rich-candidate JSON reports/summaries.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_input_records: list[dict[str, Any]] = []

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_input_records = make_self_test_tasks()
    elif args.input:
        input_paths = list(args.input)
        raw_input_records = load_p21_inputs(input_paths, require_ephemeral_schema=True)
    else:
        parser.error("Specify --self-test or --input PATH [PATH ...]")

    # Detect summary-only or empty inputs.
    status = "self_test_only" if args.self_test else "ok"
    reason: str | None = None
    insufficient_paths: list[str] = []
    non_task_records: list[dict[str, Any]] = []
    task_records: list[dict[str, Any]] = []
    for rec in raw_input_records:
        if rec.get("_p25_input_summary_marker"):
            status = "insufficient_task_detail"
            reason = "Aggregate summary lacks per-task rich-candidate records required for bucket routing."
            insufficient_paths.append(rec.get("path", "unknown"))
            non_task_records.append(rec)
            continue
        if rec.get("_p25_input_empty_marker"):
            status = "insufficient_task_detail"
            reason = "Input artifact did not contain per-task rich-candidate records."
            insufficient_paths.append(rec.get("path", "unknown"))
            non_task_records.append(rec)
            continue
        if rec.get("_p25_unsupported_schema_marker"):
            status = "insufficient_task_detail"
            reason = "P25 real evaluation requires p25-policy-records-ephemeral-v1 input schema."
            insufficient_paths.append(rec.get("path", "unknown"))
            non_task_records.append(rec)
            continue
        task_records.append(rec)

    if not task_records and status == "ok":
        status = "insufficient_task_detail"
        reason = "No per-task records found."

    normalized_tasks = [nt for nt in (normalize_task(raw) for raw in task_records) if nt]

    usable = [
        t for t in normalized_tasks
        if t["outcomes"]["candidate_baseline"].get("file_recall_at_5") is not None
        or t["outcomes"]["candidate_baseline"].get("added_gold_span") is not None
    ]
    if status == "ok" and not usable:
        status = "insufficient_task_detail"
        reason = "Records lacked candidate_baseline outcome fields required for policy evaluation."

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

    write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P25 report written to {args.out}")
    print(f"P25 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
