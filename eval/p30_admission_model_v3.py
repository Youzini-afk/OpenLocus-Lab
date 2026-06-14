#!/usr/bin/env python3
"""P30 Admission Model V3 — deterministic explainable admission evaluator.

P30 is research-only. It consumes ephemeral P25-policy records produced by the
P21 rich-candidate handoff (schema ``p25-policy-records-ephemeral-v1``) and
checks whether a deterministic explainable admission scorecard can choose among
a small set of safe actions per task.

Safety constraints
------------------
* No remote model calls; ``external_calls=0``.
* No EvidenceCore semantics change.
* Routing uses only pre-SCORE public/observable features:
  ``task_bucket``, ``task_risk_tags``, and public ``route_features``.
  ``score_group``, ``has_gold``, gold spans, private labels, and outcome
  metrics are used only for aggregate scoring after actions are chosen.
* Public artifacts never contain raw queries, snippets, prompts, responses,
  gold spans, private labels, provider keys, or provider-specific fields.
* ``promotion_ready=false``, ``default_should_change=false``,
  ``evidencecore_semantics_changed=false``, ``candidate_not_fact=true``.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Make standalone invocation from the repo root work without treating eval/ as a package.
_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))
import p25_bucket_policy as p25

SCHEMA_VERSION = "p30-admission-v3-report-v1"
GENERATED_BY = "eval/p30_admission_model_v3.py"

DEFAULT_OUT = Path("artifacts/p30_admission_v3/p30_admission_v3_report.json")
DEFAULT_DOC = Path("docs/en/p30-admission-model-v3.md")

H3_SCHEMA_VERSION = "p30-h3-action-span-cost-report-v1"
DEFAULT_H3_OUT = Path("artifacts/p30_admission_v3/p30_h3_span_cost_report.json")
DEFAULT_H3_DOC = Path("docs/en/p30-h3-span-cost-accounting.md")


def _default_h3_out_for(out_path: Path) -> Path:
    """Keep H3 beside the selected P30 JSON report unless explicitly set."""
    if out_path == DEFAULT_OUT:
        return DEFAULT_H3_OUT
    return out_path.with_name("p30_h3_span_cost_report.json")


def _default_h3_doc_for(doc_path: Path) -> Path:
    """Keep H3 markdown beside the selected P30 markdown unless explicitly set."""
    if doc_path == DEFAULT_DOC:
        return DEFAULT_H3_DOC
    return doc_path.with_name("p30-h3-span-cost-accounting.md")

# Actions that the admission model is allowed to emit.  They are semantic
# choices; per-record outcomes are looked up from the task's outcome table.
P30_ACTIONS = {
    "abstain",
    "admit_symbol_regex_union",
    "admit_rrf_primary",
    "admit_llm_span_narrow",
    "apply_llm_filter",
    "supporting_only",
    "weak_candidate_only",
}

POLICIES = [
    "candidate_baseline",
    "llm_span_narrow",
    "llm_filter",
    "llm_abstain_filter",
    "bucket_routed_v0",
    "admission_v3",
    "admission_v3_h1",
    "admission_v3_h2",
]

# Mapping from emitted action to the outcome key used for aggregate scoring.
# If the key is absent in a real P25 record, the evaluator falls back to a
# safe conservative surrogate (see _lookup_outcome).
ACTION_OUTCOME_MAP: dict[str, str] = {
    "abstain": "llm_abstain_filter",
    "admit_symbol_regex_union": "symbol_regex_union",
    "admit_rrf_primary": "rrf_primary",
    "admit_llm_span_narrow": "llm_span_narrow",
    "apply_llm_filter": "llm_filter",
    "supporting_only": "supporting_only",
    "weak_candidate_only": "weak_candidate_only",
}

# Public bucket/risk keywords (kept in sync with p25).  These are observable at
# RUN time from public task metadata.
NEGATIVE_BUCKET_NAMES = {
    "negative",
    "dense_false_positive",
    "dense_quiver_trap",
    "ambiguous",
    "hallucination_risk",
    "weak_candidates",
    "hard_distractor",
    "stale-like",
}

POSITIVE_BUCKET_NAMES = {
    "positive",
    "likely_positive",
    "high_confidence",
    "exact_symbol",
    "exact_symbol_unique",
    "config",
    "route_handler",
}

FORBIDDEN_PUBLIC_KEYS = {
    "query",
    "raw_query",
    "snippet",
    "prompt",
    "response",
    "gold",
    "gold_spans",
    "private_labels",
    "label_path",
    "base_url",
    "api_key",
    "api_token",
    "api_secret",
    "endpoint",
    "provider_key",
    "embedding_api_key",
    "llm_api_key",
}

# Public RUN-phase route features allowed to influence admission. Any other keys
# are silently ignored and counted.
ROUTE_FEATURE_ALLOWLIST = {
    "candidate_count",
    "candidate_support_exists",
    "unique_symbol_anchor",
    "exact_unique_symbol_anchor",
    "symbol_anchor",
    "regex_anchor",
    "local_anchor",
    "symbol_regex_agree_file",
    "symbol_regex_agree_span",
    "rrf_anchor_agree_file",
    "rrf_anchor_agree_span",
    "rrf_backed_by_anchor",
    "query_noise",
    "llm_span_narrow_valid",
    "llm_span_within_candidate",
    "dense_support_present",
    "graph_support_present",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _filter_route_features(raw: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Return only allowlisted RUN-phase route features plus count of ignored keys."""
    allowed: dict[str, Any] = {}
    ignored = 0
    for key, value in raw.items():
        if key in ROUTE_FEATURE_ALLOWLIST:
            allowed[key] = value
        else:
            ignored += 1
    return allowed, ignored


def _as_float(src: dict[str, Any], *keys: str) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for k in keys:
        v = src.get(k, src.get(k.replace("_", ""), None))
        try:
            out[k] = float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            out[k] = None
    return out


def _as_int(src: dict[str, Any], *keys: str) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    for k in keys:
        v = src.get(k)
        try:
            out[k] = int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            out[k] = None
    return out


def _extract_strategy(raw: dict[str, Any], name: str) -> dict[str, Any]:
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


def normalize_task(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Extract public fields and all strategy outcomes used by P30."""
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

    # Labels are loaded for scoring only; never used for routing.
    if raw.get("score_group") == "positive":
        has_gold = True
    elif raw.get("score_group") == "no_gold":
        has_gold = False
    else:
        has_gold = bool(raw.get("has_gold", False))

    route_features_raw = raw.get("route_features")
    route_features, route_features_ignored = _filter_route_features(
        route_features_raw if isinstance(route_features_raw, dict) else {}
    )

    float_keys = (
        "file_recall_at_5",
        "span_f0_5",
        "primary_false_positive_rate",
        "no_gold_false_primary_rate",
        "abstain_rate",
    )
    int_keys = ("added_gold_span", "added_false_span")

    def build(name: str) -> dict[str, Any]:
        src = _extract_strategy(raw, name)
        return {**_as_float(src, *float_keys), **_as_int(src, *int_keys), "abstained": bool(src.get("abstained", False))}

    outcomes: dict[str, Any] = {
        "candidate_baseline": build("candidate_baseline"),
        "llm_span_narrow": build("llm_span_narrow"),
        "llm_filter": build("llm_filter"),
        "llm_abstain_filter": build("llm_abstain_filter"),
        "symbol_regex_union": build("symbol_regex_union"),
        "rrf_primary": build("rrf_primary"),
        "supporting_only": build("supporting_only"),
        "weak_candidate_only": build("weak_candidate_only"),
    }

    # Route features are observable at RUN time and must not leak private labels.
    def rf_bool(key: str, default: bool = False) -> bool:
        return bool(route_features.get(key, default))

    def rf_float(key: str, default: float = 0.0) -> float:
        try:
            return float(route_features.get(key, default))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    tags_lower = {t.lower() for t in risk_tags}

    return {
        "task_id": tid,
        "repo_id": raw.get("repo_id"),
        "task_bucket": task_bucket,
        "task_risk_tags": risk_tags,
        "has_gold": has_gold,
        "route_features": {
            "candidate_count": int(route_features.get("candidate_count") or 0),
            "candidate_support_exists": bool(
                route_features.get("candidate_support_exists", bool(route_features.get("candidate_count")))
            ),
            "unique_symbol_anchor": rf_bool("unique_symbol_anchor"),
            "exact_unique_symbol_anchor": rf_bool("exact_unique_symbol_anchor"),
            "symbol_anchor": rf_bool("symbol_anchor") or "symbol_anchor" in tags_lower or "exact_symbol" in tags_lower,
            "regex_anchor": rf_bool("regex_anchor") or "regex_anchor" in tags_lower,
            "local_anchor": rf_bool("local_anchor", False),
            "symbol_regex_agree_file": rf_bool("symbol_regex_agree_file"),
            "symbol_regex_agree_span": rf_bool("symbol_regex_agree_span"),
            "rrf_anchor_agree_file": rf_bool("rrf_anchor_agree_file"),
            "rrf_anchor_agree_span": rf_bool("rrf_anchor_agree_span"),
            "rrf_backed_by_anchor": rf_bool("rrf_backed_by_anchor"),
            "query_noise": rf_float("query_noise"),
            "llm_span_narrow_valid": rf_bool("llm_span_narrow_valid"),
            "llm_span_within_candidate": rf_bool("llm_span_within_candidate"),
            "dense_support_present": rf_bool("dense_support_present"),
            "graph_support_present": rf_bool("graph_support_present"),
        },
        "outcomes": outcomes,
        "_route_features_ignored_count": route_features_ignored,
    }


def _outcome_is_usable(outcome: dict[str, Any]) -> bool:
    """An outcome is usable only if it contains at least one non-None metric."""
    for k in ("file_recall_at_5", "span_f0_5", "primary_false_positive_rate", "added_gold_span", "added_false_span"):
        if outcome.get(k) is not None:
            return True
    return False


def _lookup_outcome(task: dict[str, Any], action: str, allowed_outcome_keys: set[str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (outcome, fallback_info) for *action*.

    Primary-admit actions without a usable stored outcome fall back to the
    measured candidate_baseline. Explicit non-primary actions (abstain,
    supporting_only, weak_candidate_only) without a usable stored outcome use a
    zero-primary surrogate.
    """
    key = ACTION_OUTCOME_MAP.get(action, action)
    outcomes = task["outcomes"]
    if (
        (allowed_outcome_keys is None or key in allowed_outcome_keys)
        and isinstance(outcomes, dict)
        and isinstance(outcomes.get(key), dict)
        and _outcome_is_usable(outcomes[key])
    ):
        return dict(outcomes[key]), {"action": action, "key": key, "missing": False, "fallback_to": None}
    base = outcomes.get("candidate_baseline", {}) if isinstance(outcomes, dict) else {}
    if action in ("supporting_only", "weak_candidate_only", "abstain"):
        return (
            {
                "file_recall_at_5": 0.0,
                "span_f0_5": 0.0,
                "primary_false_positive_rate": 0.0,
                "no_gold_false_primary_rate": 0.0,
                "added_gold_span": 0,
                "added_false_span": 0,
                "abstained": action == "abstain",
            },
            {"action": action, "key": key, "missing": True, "fallback_to": "zero_primary"},
        )
    base_out = dict(base)
    base_out.setdefault("abstained", False)
    return base_out, {"action": action, "key": key, "missing": True, "fallback_to": "candidate_baseline"}


def bucket_labels(task: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    if task.get("task_bucket"):
        labels.add(str(task["task_bucket"]))
    for tag in task.get("task_risk_tags", []):
        if isinstance(tag, str):
            labels.add(tag)
    return labels


def route_admission_v3(task: dict[str, Any]) -> dict[str, Any]:
    """Explainable monotonic scorecard/hard-guard routing.

    Uses only public task_bucket, task_risk_tags, and route_features.
    Never uses score_group, has_gold, gold, or outcome metrics.
    """
    rf = task["route_features"]
    labels = bucket_labels(task)
    qn = float(rf.get("query_noise") or 0.0)

    score = 0
    reasons: list[str] = []

    def add(points: int, reason: str) -> None:
        nonlocal score
        score += points
        if points != 0:
            reasons.append(f"{reason}({'+' if points > 0 else ''}{points})")

    if rf.get("exact_unique_symbol_anchor"):
        add(2, "exact_unique_symbol_anchor")
    elif rf.get("unique_symbol_anchor"):
        add(1, "unique_symbol_anchor")

    if rf.get("symbol_anchor"):
        add(1, "symbol_anchor")
    if rf.get("regex_anchor"):
        add(1, "regex_anchor")
    if rf.get("local_anchor"):
        add(1, "local_anchor")
    if rf.get("rrf_backed_by_anchor"):
        add(1, "rrf_backed_by_anchor")

    if qn > 0.5:
        add(-2, "high_query_noise")
    elif qn > 0.25:
        add(-1, "moderate_query_noise")

    if rf.get("llm_span_narrow_valid"):
        add(1, "llm_span_narrow_valid")
    if rf.get("llm_span_within_candidate"):
        add(1, "llm_span_within_candidate")

    if "dense_false_positive" in labels or "dense_quiver_trap" in labels:
        add(-3, "dense_false_positive_tag")
    if "negative" in labels:
        add(-3, "negative_tag")
    if "ambiguous" in labels:
        add(-2, "ambiguous_tag")
    if "hallucination_risk" in labels:
        add(-2, "hallucination_risk_tag")
    if "weak_candidates" in labels:
        add(-1, "weak_candidates_tag")
    if "hard_distractor" in labels:
        add(-1, "hard_distractor_tag")

    if task["task_bucket"] in {"negative", "dense_quiver_trap"}:
        add(-2, f"bucket_{task['task_bucket']}")
    elif task["task_bucket"] == "ambiguous":
        add(-2, "bucket_ambiguous")
    elif task["task_bucket"] in POSITIVE_BUCKET_NAMES:
        add(1, f"bucket_{task['task_bucket']}")

    action: str
    rule: str

    # Hard guards first: negative/dense-false-positive/ambiguous buckets.
    if task["task_bucket"] in {"negative", "dense_quiver_trap", "hard_distractor"} or score <= -4:
        if rf.get("dense_support_present") or rf.get("graph_support_present"):
            action = "supporting_only"
            rule = "negative_or_penalized_supporting_only"
        else:
            action = "abstain" if score <= -5 else "apply_llm_filter"
            rule = "negative_hard_guard" if score <= -5 else "negative_llm_filter"
    elif task["task_bucket"] == "ambiguous":
        if rf.get("dense_support_present") or rf.get("graph_support_present"):
            action = "supporting_only"
            rule = "ambiguous_supporting_only"
        else:
            action = "apply_llm_filter"
            rule = "ambiguous_filter"
    elif rf.get("exact_unique_symbol_anchor") and qn <= 0.2:
        action = "admit_symbol_regex_union"
        rule = "exact_unique_symbol_anchor_low_noise"
    elif (rf.get("symbol_anchor") or rf.get("regex_anchor")) and rf.get("local_anchor") and qn <= 0.3:
        action = "admit_symbol_regex_union"
        rule = "symbol_regex_local_anchor"
    elif rf.get("rrf_backed_by_anchor") and rf.get("local_anchor") and qn <= 0.4:
        action = "admit_rrf_primary"
        rule = "rrf_backed_by_local_anchor"
    elif rf.get("llm_span_narrow_valid") and rf.get("llm_span_within_candidate") and qn <= 0.4:
        action = "admit_llm_span_narrow"
        rule = "llm_span_narrow_valid_within_candidate"
    elif "weak_candidates" in labels or score <= 0 and not rf.get("local_anchor"):
        action = "weak_candidate_only"
        rule = "weak_candidate_or_low_local_signal"
    else:
        action = "abstain"
        rule = "fallback_abstain_for_uncertain_signal"

    return {
        "action": action,
        "score": score,
        "scorecard_reasons": reasons,
        "rule": rule,
    }


LEGACY_OUTCOME_KEYS = {
    "candidate_baseline",
    "llm_span_narrow",
    "llm_filter",
    "llm_abstain_filter",
}


def route_admission_v3_h1(task: dict[str, Any]) -> dict[str, Any]:
    """Handoff-enriched P30 scorecard.

    This intentionally reuses the P30 scorecard, but evaluates it with enriched
    pre-SCORE route features and local-anchor measured outcomes produced by the
    P21 handoff.  It is a handoff repair A/B lane, not a new promotion policy.
    """
    return route_admission_v3(task)


def route_admission_v3_h2(task: dict[str, Any]) -> dict[str, Any]:
    """Strict local-anchor admission policy (P30-H2).

    H2 does not add new channels; it uses the same enriched pre-SCORE
    route_features and measured local-anchor outcomes as admission_v3_h1, but
    applies stricter guards:

    * Primary-admit only when span-level or exact-unique-symbol agreement is
      present, the bucket is positive, and query noise is low.
    * Hard-negative/dense/hard-distractor tasks get no primary admit.
    * Ambiguous/hallucination-risk tasks get no primary admit.
    * File-only agreement is demoted to weak_candidate_only.
    * Remaining local anchors become weak candidates; dense/graph support
      becomes supporting; otherwise abstain.
    """
    rf = task["route_features"]
    labels = bucket_labels(task)
    labels_lower = {label.lower() for label in labels}
    qn = float(rf.get("query_noise") or 0.0)
    positive_bucket = task["task_bucket"] in POSITIVE_BUCKET_NAMES

    score = 0
    reasons: list[str] = []

    def add(points: int, reason: str) -> None:
        nonlocal score
        score += points
        if points != 0:
            reasons.append(f"{reason}({'+' if points > 0 else ''}{points})")

    # Positive local-anchor signals.
    if rf.get("exact_unique_symbol_anchor"):
        add(2, "exact_unique_symbol_anchor")
    if rf.get("symbol_anchor"):
        add(1, "symbol_anchor")
    if rf.get("regex_anchor"):
        add(1, "regex_anchor")
    if rf.get("local_anchor"):
        add(1, "local_anchor")
    if rf.get("symbol_regex_agree_file"):
        add(1, "symbol_regex_agree_file")
    if rf.get("symbol_regex_agree_span"):
        add(1, "symbol_regex_agree_span")
    if rf.get("rrf_anchor_agree_file"):
        add(1, "rrf_anchor_agree_file")
    if rf.get("rrf_anchor_agree_span"):
        add(1, "rrf_anchor_agree_span")
    if rf.get("rrf_backed_by_anchor"):
        add(1, "rrf_backed_by_anchor")

    # LLM span narrowing is a positive signal only when anchored.
    if rf.get("llm_span_narrow_valid"):
        add(1, "llm_span_narrow_valid")
    if rf.get("llm_span_within_candidate"):
        add(1, "llm_span_within_candidate")

    # Query-noise penalty.
    if qn > 0.5:
        add(-2, "high_query_noise")
    elif qn > 0.25:
        add(-1, "moderate_query_noise")

    # Public risk-tag penalties (kept in sync with admission_v3 for comparability).
    if "dense_false_positive" in labels_lower or "dense_quiver_trap" in labels_lower:
        add(-3, "dense_false_positive_tag")
    if "negative" in labels_lower:
        add(-3, "negative_tag")
    if "ambiguous" in labels_lower:
        add(-2, "ambiguous_tag")
    if "hallucination_risk" in labels_lower:
        add(-2, "hallucination_risk_tag")
    if "weak_candidates" in labels_lower:
        add(-1, "weak_candidates_tag")
    if "hard_distractor" in labels_lower:
        add(-1, "hard_distractor_tag")

    # Bucket-level scorecard contribution.
    if task["task_bucket"] in {"negative", "dense_quiver_trap"}:
        add(-2, f"bucket_{task['task_bucket']}")
    elif task["task_bucket"] == "ambiguous":
        add(-2, "bucket_ambiguous")
    elif positive_bucket:
        add(1, f"bucket_{task['task_bucket']}")

    negative_tags = {"negative", "hard_distractor", "dense_false_positive"}
    ambiguous_tags = {"ambiguous", "hallucination_risk"}
    no_negative_tags = not bool(labels_lower & negative_tags)
    dense_or_graph = bool(rf.get("dense_support_present") or rf.get("graph_support_present"))
    strong_span_agree = bool(rf.get("symbol_regex_agree_span") or rf.get("rrf_anchor_agree_span"))
    anchor_agree_for_llm = bool(
        rf.get("symbol_regex_agree_span")
        or rf.get("rrf_anchor_agree_span")
        or rf.get("exact_unique_symbol_anchor")
    )

    action: str
    rule: str

    # 1. Hard negative/dense/hard-distractor guard: no primary admit.
    if (
        task["task_bucket"] in {"negative", "dense_quiver_trap", "hard_distractor"}
        or labels_lower & negative_tags
    ):
        if dense_or_graph:
            action = "supporting_only"
            rule = "negative_dense_supporting_only"
        else:
            action = "apply_llm_filter"
            rule = "negative_dense_apply_llm_filter"

    # 2. Ambiguous/hallucination guard: no primary admit.
    elif task["task_bucket"] == "ambiguous" or labels_lower & ambiguous_tags:
        if strong_span_agree and qn <= 0.2:
            action = "weak_candidate_only"
            rule = "ambiguous_weak_candidate_span_agreement"
        elif dense_or_graph:
            action = "supporting_only"
            rule = "ambiguous_supporting_only"
        else:
            action = "apply_llm_filter"
            rule = "ambiguous_apply_llm_filter"

    # 3. Exact unique symbol admission.
    elif (
        rf.get("exact_unique_symbol_anchor")
        and rf.get("symbol_anchor")
        and qn <= 0.1
        and no_negative_tags
    ):
        action = "admit_symbol_regex_union"
        rule = "exact_unique_symbol_anchor_low_noise"

    # 4. Symbol+regex span agreement; file-only is not enough.
    elif rf.get("symbol_regex_agree_span") and positive_bucket and qn <= 0.2 and no_negative_tags:
        action = "admit_symbol_regex_union"
        rule = "symbol_regex_agree_span_positive_low_noise"
    elif (
        rf.get("symbol_regex_agree_file")
        and positive_bucket
        and qn <= 0.2
        and no_negative_tags
    ):
        action = "weak_candidate_only"
        rule = "symbol_regex_file_only_weak_candidate"

    # 5. RRF span agreement; file-only is not enough.
    elif rf.get("rrf_anchor_agree_span") and positive_bucket and qn <= 0.2 and no_negative_tags:
        action = "admit_rrf_primary"
        rule = "rrf_anchor_agree_span_positive_low_noise"
    elif rf.get("rrf_anchor_agree_file") and positive_bucket and qn <= 0.2 and no_negative_tags:
        action = "weak_candidate_only"
        rule = "rrf_file_only_weak_candidate"

    # 6. LLM span narrowing, only when backed by span/exact-symbol agreement.
    elif (
        rf.get("llm_span_narrow_valid")
        and rf.get("llm_span_within_candidate")
        and anchor_agree_for_llm
        and positive_bucket
        and qn <= 0.2
        and no_negative_tags
    ):
        action = "admit_llm_span_narrow"
        rule = "llm_span_narrow_with_anchor_agreement"

    # 7. Remaining local anchor signals are too weak for a primary admit.
    elif rf.get("local_anchor"):
        action = "weak_candidate_only"
        rule = "local_anchor_weak_candidate"

    # 8. Dense/graph support without a strong local anchor.
    elif dense_or_graph:
        action = "supporting_only"
        rule = "dense_graph_supporting_only"

    # 9. Default abstain.
    else:
        action = "abstain"
        rule = "fallback_abstain_for_uncertain_signal"

    return {
        "action": action,
        "score": score,
        "scorecard_reasons": reasons,
        "rule": rule,
    }


def _avg(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _score_band(score: int) -> str:
    if score >= 3:
        return "high_admit"
    if score >= 1:
        return "medium_admit"
    if score >= -1:
        return "neutral"
    if score >= -3:
        return "penalty"
    return "hard_guard"


def _aggregate_admission_v3_impl(
    tasks: list[dict[str, Any]],
    router: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    allowed_outcome_keys: set[str] | None = None,
) -> dict[str, Any]:
    """Aggregate metrics for an admission_v3-family policy."""
    if not tasks:
        return {
            "task_count": 0,
            "positive_task_count": 0,
            "no_gold_task_count": 0,
            "SpanF0.5": None,
            "primary_false_positive_rate": None,
            "no_gold_false_primary_rate": None,
            "added_gold_span": 0,
            "added_false_span": 0,
            "filter_gold_kill_rate": None,
            "abstain_rate": None,
            "policy_action_counts": {},
            "success_layers": {},
            "score_bands": {},
            "selective_risk_proxy": None,
            "outcome_fallback": {
                "missing_action_outcome_count": 0,
                "fallback_action_counts": {},
                "fallback_strategy_counts": {},
                "note": "no tasks evaluated",
            },
        }

    routings = [router(t) for t in tasks]
    actions = [r["action"] for r in routings]

    task_count = len(tasks)
    positive_count = sum(1 for t in tasks if t.get("has_gold"))
    no_gold_count = task_count - positive_count

    span_f0_5s: list[float] = []
    pfps: list[float] = []
    no_gold_pfps: list[float] = []
    added_gold_sum = 0
    added_false_sum = 0
    filter_killed_gold = 0
    abstain_count = 0
    candidate_success_count = 0
    model_success_count = 0
    admission_success_count = 0
    evidence_success_count = 0

    bins: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "positive_count": 0,
            "no_gold_count": 0,
            "action_counts": defaultdict(int),
            "span_f0_5": [],
            "pfp": [],
        }
    )

    fallback_counts: dict[str, int] = defaultdict(int)
    fallback_action_counts: dict[str, int] = defaultdict(int)
    missing_action_outcome_count = 0

    for task, routing in zip(tasks, routings):
        action = routing["action"]
        outcome, fallback = _lookup_outcome(task, action, allowed_outcome_keys)
        baseline = task["outcomes"]["candidate_baseline"]

        if fallback["missing"]:
            missing_action_outcome_count += 1
            fallback_counts[fallback["fallback_to"] or "unknown"] += 1
            fallback_action_counts[action] += 1

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

        is_gold = bool(task.get("has_gold"))
        if not is_gold:
            ngp = outcome.get("no_gold_false_primary_rate")
            if ngp is None and pfp is not None:
                ngp = pfp
            if ngp is not None:
                no_gold_pfps.append(ngp)

        if is_gold and baseline.get("added_gold_span", 0) > 0 and ag == 0:
            filter_killed_gold += 1

        if action == "abstain" or outcome.get("abstained"):
            abstain_count += 1

        baseline_fr = baseline.get("file_recall_at_5", 0.0) or 0.0
        candidate_success = baseline_fr > 0 or baseline.get("added_gold_span", 0) > 0
        if candidate_success:
            candidate_success_count += 1

        if action in ("admit_symbol_regex_union", "admit_rrf_primary", "admit_llm_span_narrow"):
            model_success = ag > 0 or (sf is not None and sf > baseline.get("span_f0_5", 0.0))
        elif action == "apply_llm_filter":
            killed_gold = baseline.get("added_gold_span", 0) > 0 and ag == 0
            model_success = not killed_gold and (
                outcome.get("primary_false_positive_rate", 1.0) <= baseline.get("primary_false_positive_rate", 1.0)
            )
        elif action in ("supporting_only", "weak_candidate_only", "abstain"):
            killed_gold = baseline.get("added_gold_span", 0) > 0 and ag == 0
            model_success = not killed_gold and af == 0
        else:
            model_success = False
        if model_success:
            model_success_count += 1

        outcome_pfp = outcome.get("primary_false_positive_rate")
        if outcome_pfp is None:
            outcome_pfp = baseline.get("primary_false_positive_rate", 1.0)
        admission = outcome_pfp <= baseline.get("primary_false_positive_rate", 1.0)
        if admission:
            admission_success_count += 1

        ev = candidate_success and (
            (sf is not None and sf >= baseline.get("span_f0_5", 0.0))
            or (ag > 0 and af == 0 and action != "candidate_baseline")
        )
        if ev:
            evidence_success_count += 1

        band = _score_band(routing["score"])
        b = bins[band]
        b["count"] += 1
        if is_gold:
            b["positive_count"] += 1
        else:
            b["no_gold_count"] += 1
        b["action_counts"][action] += 1
        if sf is not None:
            b["span_f0_5"].append(sf)
        if pfp is not None:
            b["pfp"].append(pfp)

    action_counts: dict[str, int] = defaultdict(int)
    for action in actions:
        action_counts[action] += 1

    span_avg = _avg(span_f0_5s)
    pfp_avg = _avg(pfps)
    ng_pfp_avg = _avg(no_gold_pfps)

    calibration: dict[str, Any] = {}
    for band, b in sorted(bins.items()):
        calibration[band] = {
            "count": b["count"],
            "positive_count": b["positive_count"],
            "no_gold_count": b["no_gold_count"],
            "fraction_positive": (b["positive_count"] / b["count"] if b["count"] else None),
            "action_counts": dict(b["action_counts"]),
            "SpanF0.5": _avg(b["span_f0_5"]),
            "primary_false_positive_rate": _avg(b["pfp"]),
        }

    coverage = 1.0 - (abstain_count / task_count if task_count else 0.0)
    selective_risk = (pfp_avg or 0.0) * coverage

    return {
        "task_count": task_count,
        "positive_task_count": positive_count,
        "no_gold_task_count": no_gold_count,
        "SpanF0.5": span_avg,
        "primary_false_positive_rate": pfp_avg,
        "no_gold_false_primary_rate": ng_pfp_avg,
        "added_gold_span": added_gold_sum,
        "added_false_span": added_false_sum,
        "filter_gold_kill_rate": (filter_killed_gold / positive_count if positive_count else None),
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
        "score_bands": calibration,
        "selective_risk_proxy": selective_risk,
        "outcome_fallback": {
            "missing_action_outcome_count": missing_action_outcome_count,
            "fallback_action_counts": dict(fallback_action_counts),
            "fallback_strategy_counts": dict(fallback_counts),
            "note": (
                "admission_v3 actions without a measured outcome in the ephemeral record "
                "fall back to candidate_baseline for primary-admit actions or a zero-primary "
                "surrogate for abstain/supporting_only/weak_candidate_only. "
                "Real evaluation requires ephemeral records that include measured outcomes "
                "for the actions the model selects."
            ),
        },
        "quality_comparable": missing_action_outcome_count == 0,
        "blocked_by_missing_action_outcomes": missing_action_outcome_count > 0,
        "selected_action_fallback_rate": (
            missing_action_outcome_count / task_count if task_count else 0.0
        ),
    }


def aggregate_admission_v3(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate legacy admission_v3 metrics.

    Legacy P30 is scored as if only the original P21/P25 outcomes were present,
    so enriched local-anchor outcomes do not silently erase the old fallback
    behavior.  This keeps the H1 handoff repair comparison honest.
    """
    return _aggregate_admission_v3_impl(tasks, route_admission_v3, allowed_outcome_keys=LEGACY_OUTCOME_KEYS)


def aggregate_admission_v3_h1(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate metrics for the P30-H1 handoff-enriched admission policy."""
    return _aggregate_admission_v3_impl(tasks, route_admission_v3_h1)


def aggregate_admission_v3_h2(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate metrics for the P30-H2 strict local-anchor admission policy.

    H2 uses the full set of enriched local-anchor measured outcomes; it does not
    fall back to legacy outcome keys.  It should be fallback-free on P30-H1
    records that include outcomes for every action it can select.
    """
    return _aggregate_admission_v3_impl(tasks, route_admission_v3_h2)


def compute_policy_metrics(tasks: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    """Return aggregate metrics for one of the compared policies."""
    if policy == "admission_v3":
        return aggregate_admission_v3(tasks)
    if policy == "admission_v3_h1":
        return aggregate_admission_v3_h1(tasks)
    if policy == "admission_v3_h2":
        return aggregate_admission_v3_h2(tasks)
    # Reuse p25 aggregation for the baseline comparison policies.
    return p25.aggregate_policy(tasks, policy)


def _add_deltas_and_action_rates(metrics_by_policy: dict[str, Any]) -> None:
    baseline = metrics_by_policy.get("candidate_baseline", {})
    routed = metrics_by_policy.get("bucket_routed_v0", {})

    def delta(policy: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        out["delta_SpanF0.5"] = _delta(policy.get("SpanF0.5"), ref.get("SpanF0.5"))
        out["delta_primary_false_positive_rate"] = _delta(policy.get("primary_false_positive_rate"), ref.get("primary_false_positive_rate"))
        out["delta_added_gold_span"] = (policy.get("added_gold_span") or 0) - (ref.get("added_gold_span") or 0)
        out["delta_added_false_span"] = (policy.get("added_false_span") or 0) - (ref.get("added_false_span") or 0)
        return out

    for policy, metrics in metrics_by_policy.items():
        metrics["delta_vs_candidate_baseline"] = delta(metrics, baseline)
        metrics["delta_vs_bucket_routed_v0"] = delta(metrics, routed)
        counts = metrics.get("policy_action_counts", {})
        tc = metrics.get("task_count") or 0
        metrics["action_rates"] = {a: (c / tc if tc else None) for a, c in counts.items()}


def _delta(a: Any, b: Any) -> float | None:
    if a is None or b is None:
        return None
    return float(a) - float(b)


# H3 action-specific span-cost accounting helpers.

def _action_kind(action: str) -> str:
    if action in {
        "admit_symbol_regex_union",
        "admit_rrf_primary",
        "admit_llm_span_narrow",
        # P25 bucket-routed role action: emits narrowed span candidates.
        "llm_span_narrow",
    }:
        return "primary"
    if action in {
        "abstain",
        "apply_llm_filter",
        "supporting_only",
        "weak_candidate_only",
        # P25 bucket-routed role actions: filter/abstain-like gates.
        "llm_filter",
        "llm_abstain_filter",
    }:
        return "non_primary"
    return "unclassified"


def _action_false_budget(action_kind: str, added_gold: int) -> int:
    """Diagnostic false-span budget for an action aggregate.

    Accounting-only; not a production cost model. Primary admissions are
    expected to be at least 1:1 gold:false. Non-primary actions are expected
    to add zero primary false spans. Unclassified baseline strategies are
    expected to be net-neutral.
    """
    if action_kind == "primary":
        return added_gold
    if action_kind == "non_primary":
        return 0
    return added_gold


def _gather_policy_actions_for_h3(tasks: list[dict[str, Any]], policy: str) -> list[str]:
    """Return the action selected for each task under *policy*."""
    if policy == "admission_v3":
        return [route_admission_v3(t)["action"] for t in tasks]
    if policy == "admission_v3_h1":
        return [route_admission_v3_h1(t)["action"] for t in tasks]
    if policy == "admission_v3_h2":
        return [route_admission_v3_h2(t)["action"] for t in tasks]
    return p25.gather_policy_action(tasks, policy)


def compute_action_span_cost_accounting(
    tasks: list[dict[str, Any]],
    policy: str,
) -> dict[str, Any]:
    """Compute deterministic action-specific span-cost accounting for *policy*."""
    if not tasks:
        return {
            "task_count": 0,
            "positive_task_count": 0,
            "no_gold_task_count": 0,
            "primary_false_span_cost": 0,
            "non_primary_false_span_cost": 0,
            "unclassified_false_span_cost": 0,
            "budget_violation_count": 0,
            "budget_violation_rate": None,
            "budget_violation_reasons": {},
            "worst_actions_by_false_cost": [],
            "worst_actions_by_gold_kill": [],
            "action_span_cost_table": {},
        }

    actions = _gather_policy_actions_for_h3(tasks, policy)
    task_count = len(tasks)
    positive_count = sum(1 for t in tasks if t.get("has_gold"))
    no_gold_count = task_count - positive_count

    bins: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "selected_count": 0,
            "positive_count": 0,
            "no_gold_count": 0,
            "action_added_gold_span": 0,
            "action_added_false_span": 0,
            "selected_baseline_added_gold_span": 0,
            "selected_baseline_added_false_span": 0,
            "span_f0_5_deltas": [],
            "pfp_deltas": [],
            "gold_kill_count": 0,
            "false_reduction_count": 0,
        }
    )

    for task, action in zip(tasks, actions):
        outcome, _ = _lookup_outcome(task, action)
        baseline = task["outcomes"]["candidate_baseline"]
        is_gold = bool(task.get("has_gold"))

        b = bins[action]
        b["selected_count"] += 1
        if is_gold:
            b["positive_count"] += 1
        else:
            b["no_gold_count"] += 1

        sf = outcome.get("span_f0_5")
        baseline_sf = baseline.get("span_f0_5")
        if sf is not None and baseline_sf is not None:
            b["span_f0_5_deltas"].append(float(sf) - float(baseline_sf))

        pfp = outcome.get("primary_false_positive_rate")
        baseline_pfp = baseline.get("primary_false_positive_rate")
        if pfp is not None and baseline_pfp is not None:
            b["pfp_deltas"].append(float(pfp) - float(baseline_pfp))

        ag = outcome.get("added_gold_span") or 0
        af = outcome.get("added_false_span") or 0
        baseline_ag = baseline.get("added_gold_span") or 0
        baseline_af = baseline.get("added_false_span") or 0
        b["action_added_gold_span"] += ag
        b["action_added_false_span"] += af
        b["selected_baseline_added_gold_span"] += baseline_ag
        b["selected_baseline_added_false_span"] += baseline_af

        if is_gold and baseline_ag > 0 and ag == 0:
            b["gold_kill_count"] += 1

        if not is_gold and baseline_af > af:
            b["false_reduction_count"] += 1

    action_span_cost_table: dict[str, Any] = {}
    primary_false_span_cost = 0
    non_primary_false_span_cost = 0
    unclassified_false_span_cost = 0
    budget_violation_count = 0
    budget_violation_reasons: dict[str, int] = defaultdict(int)

    for action, b in sorted(bins.items()):
        kind = _action_kind(action)
        selected_count = b["selected_count"]
        selected_rate = selected_count / task_count if task_count else None
        action_added_gold = b["action_added_gold_span"]
        action_added_false = b["action_added_false_span"]

        budget_limit = _action_false_budget(kind, action_added_gold)
        budget_violated = action_added_false > budget_limit
        budget_reason: str | None = None
        if budget_violated:
            if kind == "primary":
                budget_reason = (
                    f"primary action false cost ({action_added_false}) exceeds gold ({action_added_gold})"
                )
            elif kind == "non_primary":
                budget_reason = (
                    f"non-primary action has false cost ({action_added_false})"
                )
            else:
                budget_reason = (
                    f"unclassified action false cost ({action_added_false}) exceeds gold ({action_added_gold})"
                )
            budget_violation_count += selected_count
            budget_violation_reasons[budget_reason] += selected_count

        if kind == "primary":
            primary_false_span_cost += action_added_false
        elif kind == "non_primary":
            non_primary_false_span_cost += action_added_false
        else:
            unclassified_false_span_cost += action_added_false

        action_span_cost_table[action] = {
            "action_kind": kind,
            "selected_count": selected_count,
            "selected_rate": selected_rate,
            "action_added_gold_span": action_added_gold,
            "action_added_false_span": action_added_false,
            "false_per_gold": (
                action_added_false / action_added_gold if action_added_gold else None
            ),
            "gold_per_false": (
                action_added_gold / action_added_false if action_added_false else None
            ),
            "net_span_value_1x": action_added_gold - action_added_false,
            "net_span_value_2x": action_added_gold - (2 * action_added_false),
            "selected_baseline_added_gold_span": b["selected_baseline_added_gold_span"],
            "selected_baseline_added_false_span": b["selected_baseline_added_false_span"],
            "delta_added_gold_span_vs_baseline": action_added_gold - b["selected_baseline_added_gold_span"],
            "delta_added_false_span_vs_baseline": action_added_false - b["selected_baseline_added_false_span"],
            "mean_delta_span_f0_5_vs_baseline": _avg(b["span_f0_5_deltas"]),
            "mean_delta_primary_false_positive_rate_vs_baseline": _avg(b["pfp_deltas"]),
            "gold_kill_count": b["gold_kill_count"],
            "gold_kill_rate": (
                b["gold_kill_count"] / b["positive_count"] if b["positive_count"] else None
            ),
            "false_reduction_count": b["false_reduction_count"],
            "false_reduction_rate": (
                b["false_reduction_count"] / b["no_gold_count"] if b["no_gold_count"] else None
            ),
            "budget_limit": budget_limit,
            "budget_violated": budget_violated,
            "budget_violation_reason": budget_reason,
        }

    worst_actions_by_false_cost = sorted(
        [
            {
                "action": action,
                "action_kind": info["action_kind"],
                "selected_count": info["selected_count"],
                "action_added_false_span": info["action_added_false_span"],
                "action_added_gold_span": info["action_added_gold_span"],
                "false_per_gold": info["false_per_gold"],
            }
            for action, info in action_span_cost_table.items()
        ],
        key=lambda x: x["action_added_false_span"],
        reverse=True,
    )[:5]

    worst_actions_by_gold_kill = sorted(
        [
            {
                "action": action,
                "action_kind": info["action_kind"],
                "selected_count": info["selected_count"],
                "gold_kill_count": info["gold_kill_count"],
                "gold_kill_rate": info["gold_kill_rate"],
            }
            for action, info in action_span_cost_table.items()
        ],
        key=lambda x: x["gold_kill_count"],
        reverse=True,
    )[:5]

    return {
        "task_count": task_count,
        "positive_task_count": positive_count,
        "no_gold_task_count": no_gold_count,
        "primary_false_span_cost": primary_false_span_cost,
        "non_primary_false_span_cost": non_primary_false_span_cost,
        "unclassified_false_span_cost": unclassified_false_span_cost,
        "budget_violation_count": budget_violation_count,
        "budget_violation_rate": (
            budget_violation_count / task_count if task_count else None
        ),
        "budget_violation_reasons": dict(budget_violation_reasons),
        "worst_actions_by_false_cost": worst_actions_by_false_cost,
        "worst_actions_by_gold_kill": worst_actions_by_gold_kill,
        "action_span_cost_table": action_span_cost_table,
    }


def build_h3_action_span_cost_report(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the P30-H3 action-specific span-cost accounting report.

    H3 is accounting-only: it does not change admission routes, EvidenceCore
    semantics, or default strategies. It derives action-specific false-span cost
    from existing policies (bucket_routed_v0, admission_v3_h1, admission_v3_h2,
    and baseline comparison policies) using only aggregate outcome deltas.
    """
    policy_costs: dict[str, Any] = {}
    if tasks:
        for policy in POLICIES:
            policy_costs[policy] = compute_action_span_cost_accounting(tasks, policy)

    task_count = len(tasks)
    positive_count = sum(1 for t in tasks if t.get("has_gold"))
    return {
        "schema_version": H3_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P30-H3 action-specific span-cost accounting",
        "score_phase_only_accounting": True,
        "diagnostic_only": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "external_calls": 0,
        "run_phase_public_only": True,
        "labels_loaded_after_run": True,
        "task_count": task_count,
        "positive_task_count": positive_count,
        "no_gold_task_count": task_count - positive_count,
        "budget_policy": {
            "primary_false_budget_per_gold": 1.0,
            "non_primary_false_budget": 0,
            "unclassified_false_budget_per_gold": 1.0,
            "note": (
                "Accounting-only diagnostic budget. Primary admission actions are expected to keep "
                "added_false_span <= added_gold_span. Non-primary actions are expected to add zero "
                "false spans. Unclassified baseline strategy actions are expected to be net-neutral."
            ),
        },
        "policy_action_accounting": policy_costs,
        "conclusion": [
            "P30-H3 is accounting-only, not a new admission route or policy.",
            "It derives action-specific span cost from existing policies without changing routes, EvidenceCore semantics, or default strategies.",
            "Budget violations flag actions whose false-span cost exceeds a diagnostic threshold, not a production cost constraint.",
            "High non_primary_false_span_cost indicates weak/supporting/filter actions still carry primary false-span risk and need tighter route guards.",
        ],
    }


def build_h3_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# P30-H3 Action-Specific Span-Cost Accounting\n")
    lines.append(f"- Schema: `{report['schema_version']}`")
    lines.append(f"- Generated: {report['generated_at']}")
    lines.append(f"- Tasks: {report['task_count']} (+{report['positive_task_count']} / no_gold {report['no_gold_task_count']})")
    lines.append(
        "- Status: `score_phase_only_accounting=true`, `diagnostic_only=true`, "
        "`promotion_ready=false`, `default_should_change=false`.\n"
    )

    lines.append("## Budget policy (accounting-only)\n")
    bp = report["budget_policy"]
    lines.append(f"- Primary-admit actions: `added_false_span <= added_gold_span` (budget={bp['primary_false_budget_per_gold']} false/gold).")
    lines.append(f"- Non-primary actions: `added_false_span == {bp['non_primary_false_budget']}`.")
    lines.append(f"- Unclassified baseline strategies: `added_false_span <= added_gold_span` (budget={bp['unclassified_false_budget_per_gold']} false/gold).")
    lines.append(f"- {bp['note']}\n")

    lines.append("## Policy-level span-cost summary\n")
    lines.append(
        "| Policy | tasks | primary_false_cost | non_primary_false_cost | unclassified_false_cost | "
        "budget_violations | budget_violation_rate |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for policy in POLICIES:
        a = report["policy_action_accounting"].get(policy, {})

        def fmt(x: Any) -> str:
            return f"{x:.4f}" if isinstance(x, (int, float)) else (str(x) if x is not None else "n/a")

        lines.append(
            f"| {policy} | {a.get('task_count', 0)} | {a.get('primary_false_span_cost', 0)} | "
            f"{a.get('non_primary_false_span_cost', 0)} | {a.get('unclassified_false_span_cost', 0)} | "
            f"{a.get('budget_violation_count', 0)} | {fmt(a.get('budget_violation_rate'))} |"
        )
    lines.append("")

    for policy in POLICIES:
        a = report["policy_action_accounting"].get(policy, {})
        table = a.get("action_span_cost_table", {})
        if not table:
            continue
        lines.append(f"## Action span-cost table: {policy}\n")
        lines.append(
            "| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | "
            "net_1x | net_2x | gold_kill | false_reduction | budget_violated |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

        def fmt(x: Any) -> str:
            return f"{x:.4f}" if isinstance(x, (int, float)) else (str(x) if x is not None else "n/a")

        for action, info in sorted(table.items()):
            lines.append(
                f"| {action} | {info['action_kind']} | {info['selected_count']} | "
                f"{fmt(info['selected_rate'])} | {info['action_added_gold_span']} | "
                f"{info['action_added_false_span']} | {fmt(info['false_per_gold'])} | "
                f"{fmt(info['gold_per_false'])} | {info['net_span_value_1x']} | "
                f"{info['net_span_value_2x']} | {info['gold_kill_count']} | "
                f"{info['false_reduction_count']} | {info['budget_violated']} |"
            )
        lines.append("")

        worst_false = a.get("worst_actions_by_false_cost", [])
        if worst_false:
            lines.append(f"### Worst actions by false cost: {policy}\n")
            lines.append("| Action | kind | selected | added_false | added_gold | false/gold |")
            lines.append("|---|---:|---:|---:|---:|---:|")
            for row in worst_false:
                def fmt(x: Any) -> str:
                    return f"{x:.4f}" if isinstance(x, (int, float)) else (str(x) if x is not None else "n/a")
                lines.append(
                    f"| {row['action']} | {row['action_kind']} | {row['selected_count']} | "
                    f"{row['action_added_false_span']} | {row['action_added_gold_span']} | "
                    f"{fmt(row['false_per_gold'])} |"
                )
            lines.append("")

        worst_kill = a.get("worst_actions_by_gold_kill", [])
        if worst_kill:
            lines.append(f"### Worst actions by gold kill: {policy}\n")
            lines.append("| Action | kind | selected | gold_kill | gold_kill_rate |")
            lines.append("|---|---:|---:|---:|---:|")
            for row in worst_kill:
                def fmt(x: Any) -> str:
                    return f"{x:.4f}" if isinstance(x, (int, float)) else (str(x) if x is not None else "n/a")
                lines.append(
                    f"| {row['action']} | {row['action_kind']} | {row['selected_count']} | "
                    f"{row['gold_kill_count']} | {fmt(row['gold_kill_rate'])} |"
                )
            lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")

    lines.append("## Safety notes\n")
    lines.append("- P30-H3 is score-phase accounting over fixed existing policies; it does not route or admit tasks.")
    lines.append("- No remote model calls are made during H3 accounting.")
    lines.append("- No raw queries, snippets, prompts, responses, gold spans, private labels, provider keys, or per-task records are emitted.")
    lines.append("- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `external_calls=0`.")
    lines.append("")
    return "\n".join(lines)


def _reject_forbidden_keys(obj: Any, path: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = str(key).lower()
            if key in FORBIDDEN_PUBLIC_KEYS or key_lower in {k.lower() for k in FORBIDDEN_PUBLIC_KEYS}:
                violations.append(f"{path}.{key}" if path else str(key))
            violations.extend(_reject_forbidden_keys(value, f"{path}.{key}" if path else str(key)))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, f"{path}[{idx}]"))
    return violations


def make_self_test_records() -> list[dict[str, Any]]:
    """Sanitized self-test records for deterministic offline validation."""
    # Gold-task outcomes: baseline adds gold and some false spans.
    gold_outcomes = {
        "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.20, "primary_false_positive_rate": 0.10, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 2},
        "llm_span_narrow": {"file_recall_at_5": 1.0, "span_f0_5": 0.32, "primary_false_positive_rate": 0.05, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 1},
        "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.12, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
        "llm_abstain_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.10, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0, "abstained": True},
        "symbol_regex_union": {"file_recall_at_5": 1.0, "span_f0_5": 0.40, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 0},
        "rrf_primary": {"file_recall_at_5": 1.0, "span_f0_5": 0.22, "primary_false_positive_rate": 0.08, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 2},
        "supporting_only": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
        "weak_candidate_only": {"file_recall_at_5": 0.2, "span_f0_5": 0.0, "primary_false_positive_rate": 0.05, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 1},
    }
    # No-gold-task outcomes: no gold spans, only false spans.
    no_gold_outcomes = {
        "candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.40, "no_gold_false_primary_rate": 0.40, "added_gold_span": 0, "added_false_span": 4},
        "llm_span_narrow": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.30, "no_gold_false_primary_rate": 0.30, "added_gold_span": 0, "added_false_span": 3},
        "llm_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.10, "no_gold_false_primary_rate": 0.10, "added_gold_span": 0, "added_false_span": 1},
        "llm_abstain_filter": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.05, "no_gold_false_primary_rate": 0.05, "added_gold_span": 0, "added_false_span": 0, "abstained": True},
        "symbol_regex_union": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
        "rrf_primary": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.35, "no_gold_false_primary_rate": 0.35, "added_gold_span": 0, "added_false_span": 5},
        "supporting_only": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
        "weak_candidate_only": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.05, "no_gold_false_primary_rate": 0.05, "added_gold_span": 0, "added_false_span": 1},
    }

    def make(task_id: str, repo_id: str, bucket: str, tags: list[str], has_gold: bool, **rf: Any) -> dict[str, Any]:
        outcomes = copy.deepcopy(gold_outcomes if has_gold else no_gold_outcomes)
        return {
            "task_id": task_id,
            "repo_id": repo_id,
            "task_bucket": bucket,
            "task_risk_tags": tags,
            "score_group": "positive" if has_gold else "no_gold",
            "route_features": {
                "candidate_count": 3,
                "candidate_support_exists": True,
                **rf,
            },
            "outcomes": outcomes,
        }

    return [
        make("p30-001", "py_flask", "exact_symbol_unique", ["exact_symbol", "unique_symbol", "high_confidence"], True,
             exact_unique_symbol_anchor=True, symbol_anchor=True, local_anchor=True, query_noise=0.0),
        make("p30-002", "py_flask", "positive", ["symbol_anchor", "route_handler"], True,
             symbol_anchor=True, local_anchor=True, query_noise=0.1),
        make("p30-003", "js_express", "positive", ["regex_anchor", "likely_positive"], True,
             regex_anchor=True, local_anchor=True, query_noise=0.1),
        make("p30-004", "py_flask", "positive", ["high_confidence"], True,
             rrf_backed_by_anchor=True, local_anchor=True, query_noise=0.1),
        make("p30-005", "js_express", "positive", ["likely_positive"], True,
             llm_span_narrow_valid=True, llm_span_within_candidate=True, query_noise=0.2),
        make("p30-006", "js_express", "config", ["config", "positive"], True,
             local_anchor=True, query_noise=0.3),
        make("p30-007", "js_express", "negative", ["negative"], False,
             query_noise=0.6),
        make("p30-008", "js_express", "negative", ["negative"], False,
             query_noise=0.8),
        make("p30-009", "py_flask", "dense_quiver_trap", ["dense_false_positive"], True,
             dense_support_present=True, query_noise=0.5),
        make("p30-010", "js_express", "dense_quiver_trap", ["dense_false_positive", "hard_distractor"], False,
             graph_support_present=True, query_noise=0.5),
        make("p30-011", "py_flask", "ambiguous", ["ambiguous", "weak_candidates"], True,
             query_noise=0.4),
        make("p30-012", "js_express", "ambiguous", ["ambiguous", "hallucination_risk"], False,
             query_noise=0.45),
        make("p30-013", "py_flask", "ambiguous", ["weak_candidates"], True,
             query_noise=0.3),
        make("p30-014", "js_express", "unknown", ["other"], True,
             query_noise=0.5),
    ]


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
    h3_action_span_cost_accounting: dict[str, Any] = {}

    if status in {"ok", "self_test_only"}:
        for policy in POLICIES:
            policy_comparison[policy] = compute_policy_metrics(tasks, policy)
        _add_deltas_and_action_rates(policy_comparison)
        h3_action_span_cost_accounting = build_h3_action_span_cost_report(tasks)
        if self_test:
            for task in tasks:
                routing = route_admission_v3(task)
                routing_h1 = route_admission_v3_h1(task)
                routing_h2 = route_admission_v3_h2(task)
                per_task_routing.append({
                    "task_id": task["task_id"],
                    "repo_id": task.get("repo_id"),
                    "task_bucket": task.get("task_bucket"),
                    "task_risk_tags": task.get("task_risk_tags"),
                    "admission_v3_action": routing["action"],
                    "admission_v3_score": routing["score"],
                    "admission_v3_h1_action": routing_h1["action"],
                    "admission_v3_h1_score": routing_h1["score"],
                    "admission_v3_h2_action": routing_h2["action"],
                    "admission_v3_h2_score": routing_h2["score"],
                })

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P30 Admission Model V3 scaffold is ready; real per-task P25 ephemeral policy records are required."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        baseline = policy_comparison["candidate_baseline"]
        admission = policy_comparison["admission_v3"]
        if self_test:
            conclusion_lines.append(
                f"Self-test-only scaffold evaluated {baseline['task_count']} synthetic tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P30 admission evaluation scored {baseline['task_count']} real P25 ephemeral records."
            )
        conclusion_lines.append(
            "admission_v3 uses an explainable monotonic scorecard over pre-SCORE observable task_bucket, "
            "task_risk_tags, and route_features; it does not use score_group, has_gold, gold, or outcome metrics during routing."
        )
        h1 = policy_comparison["admission_v3_h1"]
        h2 = policy_comparison["admission_v3_h2"]
        conclusion_lines.append(
            f"Baseline SpanF0.5={baseline.get('SpanF0.5')}, PFP={baseline.get('primary_false_positive_rate')}; "
            f"admission_v3 SpanF0.5={admission.get('SpanF0.5')}, PFP={admission.get('primary_false_positive_rate')}."
        )
        conclusion_lines.append(
            f"admission_v3_h1 (handoff enriched) SpanF0.5={h1.get('SpanF0.5')}, PFP={h1.get('primary_false_positive_rate')}, "
            f"quality_comparable={h1.get('quality_comparable')}, "
            f"selected_action_fallback_rate={h1.get('selected_action_fallback_rate')}."
        )
        conclusion_lines.append(
            f"admission_v3_h2 (strict local anchor) SpanF0.5={h2.get('SpanF0.5')}, PFP={h2.get('primary_false_positive_rate')}, "
            f"quality_comparable={h2.get('quality_comparable')}, "
            f"selected_action_fallback_rate={h2.get('selected_action_fallback_rate')}."
        )
        conclusion_lines.append("No policy is promotion-ready or default-ready.")
        conclusion_lines.append(
            "admission_v3_h1 is a handoff-enrichment diagnostic over P30-H1 records with local-anchor measured outcomes; "
            "a non-zero fallback rate on legacy admission_v3 preserves the old missing-outcome behavior for comparison."
        )
        conclusion_lines.append(
            "admission_v3_h2 is a stricter local-anchor policy over the same P30-H1 records; it should be fallback-free "
            "whenever enriched local-anchor outcomes are present for every selected action."
        )
        conclusion_lines.append(
            "Next: compare admission_v3_h1 and admission_v3_h2 to P25 real smoke and P22/P23 guard surfaces in ephemeral remote runs."
        )

    total_route_features_ignored = sum(t.get("_route_features_ignored_count", 0) for t in tasks)
    if total_route_features_ignored:
        conclusion_lines.append(
            f"Ignored {total_route_features_ignored} non-allowlisted route_features keys; routing used allowlisted features only."
        )

    missing_outcomes_v3 = policy_comparison.get("admission_v3", {}).get("outcome_fallback", {}).get(
        "missing_action_outcome_count", 0
    )
    missing_outcomes_h1 = policy_comparison.get("admission_v3_h1", {}).get("outcome_fallback", {}).get(
        "missing_action_outcome_count", 0
    )
    missing_outcomes_h2 = policy_comparison.get("admission_v3_h2", {}).get("outcome_fallback", {}).get(
        "missing_action_outcome_count", 0
    )
    if missing_outcomes_v3:
        conclusion_lines.append(
            f"admission_v3 relied on fallback outcomes for {missing_outcomes_v3} action selections; "
            "real runs should include measured outcomes for every selected action."
        )
    if missing_outcomes_h1:
        conclusion_lines.append(
            f"admission_v3_h1 relied on fallback outcomes for {missing_outcomes_h1} action selections; "
            "H1 handoff records are missing enriched local-anchor outcomes."
        )
    if missing_outcomes_h2:
        conclusion_lines.append(
            f"admission_v3_h2 relied on fallback outcomes for {missing_outcomes_h2} action selections; "
            "H2 strict local-anchor routing required outcomes that were not present in the input records."
        )

    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P30 Admission Model V3 deterministic evaluator",
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
        "external_calls": 0,
        "run_phase_public_only": True,
        "labels_loaded_after_run": True,
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
        "route_features_ignored_count": total_route_features_ignored,
        "elapsed_ms": elapsed_ms,
        "policy_comparison": policy_comparison,
        "h3_action_span_cost_accounting": h3_action_span_cost_accounting,
        "admission_v3": {
            "routing_rules": [
                "exact_unique_symbol_anchor + low query_noise -> admit_symbol_regex_union",
                "symbol_anchor or regex_anchor + local_anchor + low/moderate query noise -> admit_symbol_regex_union",
                "rrf_backed_by_anchor + local_anchor + moderate query noise -> admit_rrf_primary",
                "llm_span_narrow_valid + within_candidate + moderate query noise -> admit_llm_span_narrow",
                "negative/dense_quiver_trap/hard_distractor or deeply penalized score -> abstain or apply_llm_filter",
                "ambiguous bucket with dense/graph supporting signal -> supporting_only; without -> apply_llm_filter",
                "weak_candidates or weak local signal -> weak_candidate_only",
            ],
            "scorecard_features": [
                "exact_unique_symbol_anchor",
                "symbol_anchor",
                "regex_anchor",
                "local_anchor",
                "symbol_regex_agree_file/span",
                "rrf_anchor_agree_file/span",
                "rrf_backed_by_anchor",
                "query_noise",
                "llm_span_narrow_valid",
                "llm_span_within_candidate",
                "negative/ambiguous/dense_false_positive/weak_candidates/hard_distractor tags and buckets",
                "dense_support_present",
                "graph_support_present",
            ],
            "per_task_routing": per_task_routing,
        },
        "admission_v3_h2": {
            "routing_rules": [
                "negative/dense_quiver_trap/hard_distractor bucket or negative/hard_distractor/dense_false_positive tag -> supporting_only if dense/graph support; else apply_llm_filter",
                "ambiguous/hallucination_risk bucket or tag -> weak_candidate_only if strong span agreement and query_noise <= 0.2; supporting_only if dense/graph support; else apply_llm_filter",
                "exact_unique_symbol_anchor + symbol_anchor + query_noise <= 0.1 -> admit_symbol_regex_union",
                "symbol_regex_agree_span + positive bucket + query_noise <= 0.2 + no negative tags -> admit_symbol_regex_union",
                "symbol_regex_agree_file only + positive bucket + query_noise <= 0.2 + no negative tags -> weak_candidate_only",
                "rrf_anchor_agree_span + positive bucket + query_noise <= 0.2 + no negative tags -> admit_rrf_primary",
                "rrf_anchor_agree_file only + positive bucket + query_noise <= 0.2 + no negative tags -> weak_candidate_only",
                "llm_span_narrow_valid + within_candidate + (symbol_regex_agree_span or rrf_anchor_agree_span or exact_unique_symbol_anchor) + positive bucket + query_noise <= 0.2 + no negative tags -> admit_llm_span_narrow",
                "remaining local_anchor -> weak_candidate_only",
                "dense_support_present or graph_support_present -> supporting_only",
                "otherwise -> abstain",
            ],
            "scorecard_features": [
                "exact_unique_symbol_anchor",
                "symbol_anchor",
                "regex_anchor",
                "local_anchor",
                "symbol_regex_agree_file",
                "symbol_regex_agree_span",
                "rrf_anchor_agree_file",
                "rrf_anchor_agree_span",
                "rrf_backed_by_anchor",
                "query_noise",
                "llm_span_narrow_valid",
                "llm_span_within_candidate",
                "negative/hard_distractor/dense_false_positive tags and buckets",
                "ambiguous/hallucination_risk tags and buckets",
                "dense_support_present",
                "graph_support_present",
            ],
            "per_task_routing": per_task_routing if self_test else [],
        },
        "conclusion": conclusion_lines,
    }

    violations = _reject_forbidden_keys(report)
    if violations:
        raise RuntimeError(f"P30 public report contains forbidden keys: {violations}")
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    """Lightweight safety/schema validation for the public report."""
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("external_calls") != 0:
        errors.append("external_calls must be 0")
    if report.get("promotion_ready") is not False:
        errors.append("promotion_ready must be false")
    if report.get("default_should_change") is not False:
        errors.append("default_should_change must be false")
    if report.get("evidencecore_semantics_changed") is not False:
        errors.append("evidencecore_semantics_changed must be false")
    if report.get("candidate_not_fact") is not True:
        errors.append("candidate_not_fact must be true")
    if report.get("self_test") and report.get("not_quality_evidence") is not True:
        errors.append("self_test must set not_quality_evidence=true")
    if report.get("status") == "ok":
        if report.get("self_test") and report.get("real_policy_evaluation") is not False:
            errors.append("self_test must set real_policy_evaluation=false")
        if not report.get("self_test") and report.get("real_policy_evaluation") is not True:
            errors.append("ok real run must set real_policy_evaluation=true")
    if report.get("status") in {"ok", "self_test_only"}:
        h3 = report.get("h3_action_span_cost_accounting")
        if not isinstance(h3, dict):
            errors.append("missing h3_action_span_cost_accounting section")
        elif h3.get("schema_version") != H3_SCHEMA_VERSION:
            errors.append("h3_action_span_cost_accounting schema_version mismatch")
        elif h3.get("diagnostic_only") is not True:
            errors.append("h3_action_span_cost_accounting must set diagnostic_only=true")
    errors.extend(_reject_forbidden_keys(report))
    return errors


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# P30 Admission Model V3 Report\n")
    lines.append(f"- Schema: `{report['schema_version']}`")
    lines.append(f"- Generated: {report['generated_at']}")
    lines.append(f"- Status: `{report['status']}`")
    lines.append(f"- Self-test: {report['self_test']}")
    lines.append(f"- External calls: {report['external_calls']}\n")

    if report["status"] not in {"ok", "self_test_only"}:
        lines.append("## Status")
        if report.get("status_reason"):
            lines.append(report["status_reason"])
        lines.append("")
        lines.append(
            "The evaluator scaffold is ready. Run with `--self-test` or supply P25 ephemeral policy records "
            "(schema `p25-policy-records-ephemeral-v1`) produced by P21/P25 handoff."
        )
        lines.append("")
        return "\n".join(lines)

    lines.append("## Policies compared\n")
    lines.append("| Policy | Description |")
    lines.append("|---|---|")
    lines.append("| candidate_baseline | No LLM; use local candidate baseline. |")
    lines.append("| llm_span_narrow | Always run LLM span narrowing. |")
    lines.append("| llm_filter | Always run LLM filtering. |")
    lines.append("| llm_abstain_filter | Always run abstaining LLM filter. |")
    lines.append("| bucket_routed_v0 | P25 bucket-routed role policy (imported baseline). |")
    lines.append(
        "| admission_v3 | Explainable monotonic scorecard with hard guards; "
        "actions: abstain, admit_symbol_regex_union, admit_rrf_primary, admit_llm_span_narrow, "
        "apply_llm_filter, supporting_only, weak_candidate_only. |"
    )
    lines.append(
        "| admission_v3_h1 | Same scorecard as admission_v3, evaluated against P30-H1 handoff records "
        "that include pre-SCORE local-anchor features and measured local-anchor outcomes "
        "(symbol_regex_union, rrf_primary, supporting_only, weak_candidate_only). |"
    )
    lines.append(
        "| admission_v3_h2 | Stricter local-anchor policy over the same P30-H1 records; "
        "demotes file-only agreement and unanchored LLM spans to weak/supporting/abstain, "
        "and requires span-level/exact-unique-symbol agreement for primary admissions. |"
    )
    lines.append("")

    lines.append("## Aggregate results\n")
    lines.append(
        "| Policy | tasks | +tasks | no_gold | SpanF0.5 | PFP | no_gold PFP | added_gold | added_false | "
        "filter_kill_rate | abstain_rate | selective_risk |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for policy in POLICIES:
        m = report["policy_comparison"][policy]

        def fmt(x: Any) -> str:
            return f"{x:.4f}" if isinstance(x, (int, float)) else (str(x) if x is not None else "n/a")

        lines.append(
            f"| {policy} | {m['task_count']} | {m['positive_task_count']} | {m['no_gold_task_count']} | "
            f"{fmt(m['SpanF0.5'])} | {fmt(m['primary_false_positive_rate'])} | "
            f"{fmt(m['no_gold_false_primary_rate'])} | {m['added_gold_span']} | {m['added_false_span']} | "
            f"{fmt(m['filter_gold_kill_rate'])} | {fmt(m['abstain_rate'])} | "
            f"{fmt(m.get('selective_risk_proxy'))} |"
        )
    lines.append("")

    lines.append("## Quality comparability\n")
    lines.append("| Policy | quality_comparable | blocked_by_missing_action_outcomes | selected_action_fallback_rate |")
    lines.append("|---|---:|---:|---:|")
    for policy in ("admission_v3", "admission_v3_h1", "admission_v3_h2"):
        m = report["policy_comparison"].get(policy, {})
        qc = m.get("quality_comparable")
        blocked = m.get("blocked_by_missing_action_outcomes")
        rate = m.get("selected_action_fallback_rate")
        def fmt(x: Any) -> str:
            return f"{x:.4f}" if isinstance(x, (int, float)) else (str(x) if x is not None else "n/a")
        lines.append(
            f"| {policy} | {qc} | {blocked} | {fmt(rate)} |"
        )
    lines.append("")

    lines.append("## Deltas vs candidate baseline\n")
    lines.append("| Policy | SpanF0.5 | PFP | added_gold | added_false |")
    lines.append("|---|---:|---:|---:|---:|")
    for policy in POLICIES:
        d = report["policy_comparison"][policy]["delta_vs_candidate_baseline"]
        def fmt(x: Any) -> str:
            return f"{x:.4f}" if isinstance(x, (int, float)) else "n/a"
        lines.append(
            f"| {policy} | {fmt(d['delta_SpanF0.5'])} | {fmt(d['delta_primary_false_positive_rate'])} | "
            f"{d['delta_added_gold_span']} | {d['delta_added_false_span']} |"
        )
    lines.append("")

    lines.append("## Deltas vs bucket_routed_v0\n")
    lines.append("| Policy | SpanF0.5 | PFP | added_gold | added_false |")
    lines.append("|---|---:|---:|---:|---:|")
    for policy in POLICIES:
        d = report["policy_comparison"][policy]["delta_vs_bucket_routed_v0"]
        def fmt(x: Any) -> str:
            return f"{x:.4f}" if isinstance(x, (int, float)) else "n/a"
        lines.append(
            f"| {policy} | {fmt(d['delta_SpanF0.5'])} | {fmt(d['delta_primary_false_positive_rate'])} | "
            f"{d['delta_added_gold_span']} | {d['delta_added_false_span']} |"
        )
    lines.append("")

    lines.append("## admission_v3 action distribution\n")
    counts = report["policy_comparison"]["admission_v3"].get("policy_action_counts", {})
    rates = report["policy_comparison"]["admission_v3"].get("action_rates", {})
    lines.append("| Action | Count | Rate |")
    lines.append("|---:|---:|---:|")
    for action in sorted(P30_ACTIONS):
        lines.append(f"| {action} | {counts.get(action, 0)} | {rates.get(action, 'n/a')} |")
    lines.append("")

    lines.append("## admission_v3_h1 action distribution\n")
    counts_h1 = report["policy_comparison"]["admission_v3_h1"].get("policy_action_counts", {})
    rates_h1 = report["policy_comparison"]["admission_v3_h1"].get("action_rates", {})
    lines.append("| Action | Count | Rate |")
    lines.append("|---:|---:|---:|")
    for action in sorted(P30_ACTIONS):
        lines.append(f"| {action} | {counts_h1.get(action, 0)} | {rates_h1.get(action, 'n/a')} |")
    lines.append("")

    lines.append("## admission_v3_h2 action distribution\n")
    counts_h2 = report["policy_comparison"]["admission_v3_h2"].get("policy_action_counts", {})
    rates_h2 = report["policy_comparison"]["admission_v3_h2"].get("action_rates", {})
    lines.append("| Action | Count | Rate |")
    lines.append("|---:|---:|---:|")
    for action in sorted(P30_ACTIONS):
        lines.append(f"| {action} | {counts_h2.get(action, 0)} | {rates_h2.get(action, 'n/a')} |")
    lines.append("")

    lines.append("## Score bands (admission_v3)\n")
    lines.append(
        "Bands are scorecard score ranges, not held-out calibrated probabilities. "
        "They show how aggregate metrics vary with the deterministic scorecard score.\n"
    )
    bins = report["policy_comparison"]["admission_v3"].get("score_bands", {})
    if bins:
        lines.append("| Band | count | +count | no_gold | frac_positive | SpanF0.5 | PFP |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for band, b in sorted(bins.items()):
            def fmt(x: Any) -> str:
                return f"{x:.4f}" if isinstance(x, (int, float)) else (str(x) if x is not None else "n/a")
            lines.append(
                f"| {band} | {b['count']} | {b['positive_count']} | {b['no_gold_count']} | "
                f"{fmt(b['fraction_positive'])} | {fmt(b['SpanF0.5'])} | {fmt(b['primary_false_positive_rate'])} |"
            )
    lines.append("")

    lines.append("## Outcome fallback caveat\n")
    fb = report["policy_comparison"]["admission_v3"].get("outcome_fallback", {})
    fb_h1 = report["policy_comparison"]["admission_v3_h1"].get("outcome_fallback", {})
    fb_h2 = report["policy_comparison"]["admission_v3_h2"].get("outcome_fallback", {})
    lines.append(
        f"- Missing action outcomes for admission_v3: {fb.get('missing_action_outcome_count', 0)}"
    )
    lines.append(
        f"- Missing action outcomes for admission_v3_h1: {fb_h1.get('missing_action_outcome_count', 0)}"
    )
    lines.append(
        f"- Missing action outcomes for admission_v3_h2: {fb_h2.get('missing_action_outcome_count', 0)}"
    )
    lines.append(
        f"- Fallback strategy counts (admission_v3): {fb.get('fallback_strategy_counts', {})}"
    )
    lines.append(
        f"- Fallback strategy counts (admission_v3_h1): {fb_h1.get('fallback_strategy_counts', {})}"
    )
    lines.append(
        f"- Fallback strategy counts (admission_v3_h2): {fb_h2.get('fallback_strategy_counts', {})}"
    )
    lines.append(
        "- If an action selected by admission_v3 has no measured outcome in the input record, "
        "the evaluator falls back to `candidate_baseline` for primary-admit actions or a zero-primary "
        "surrogate for `abstain`/`supporting_only`/`weak_candidate_only`. Real evaluation should use "
        "ephemeral records that include outcomes for every action the model can select."
    )
    lines.append(
        "- admission_v3_h1 is designed to have zero missing outcomes when P21 writes P30-H1 enriched "
        "handoff records; a non-zero value here indicates the input records lack the required local-anchor outcomes."
    )
    lines.append(
        "- admission_v3_h2 is designed to be fallback-free on P30-H1 records because it selects only "
        "from the local-anchor measured outcomes already included in the handoff; a non-zero value here "
        "indicates the input records are missing outcomes for actions H2 selects."
    )
    lines.append("")

    lines.append("## Routing rules (admission_v3)\n")
    for rule in report["admission_v3"]["routing_rules"]:
        lines.append(f"- {rule}")
    lines.append("")

    lines.append("## Routing rules (admission_v3_h2)\n")
    for rule in report["admission_v3_h2"]["routing_rules"]:
        lines.append(f"- {rule}")
    lines.append("")

    if report.get("self_test"):
        lines.append("## Per-task routing (self-test only)\n")
        lines.append(
            "| task_id | repo_id | task_bucket | task_risk_tags | "
            "v3_action | v3_score | h1_action | h1_score | h2_action | h2_score |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for row in report["admission_v3"]["per_task_routing"]:
            tags = ", ".join(row.get("task_risk_tags") or [])
            lines.append(
                f"| {row['task_id']} | {row.get('repo_id') or ''} | {row.get('task_bucket') or ''} | "
                f"{tags} | {row['admission_v3_action']} | {row['admission_v3_score']} | "
                f"{row['admission_v3_h1_action']} | {row['admission_v3_h1_score']} | "
                f"{row['admission_v3_h2_action']} | {row['admission_v3_h2_score']} |"
            )
        lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")

    lines.append("## Safety notes\n")
    lines.append("- No remote model calls were made during admission evaluation.")
    lines.append("- Routing uses only RUN-phase public task metadata; labels/gold are used only for aggregate scoring after actions are fixed.")
    lines.append("- This report contains only public task metadata, strategy/action names, and aggregate metrics.")
    lines.append("- Raw queries, snippets, prompts, responses, gold spans, private labels, provider keys, and provider fields are not stored.")
    lines.append("- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `external_calls=0`.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P30 Admission Model V3 deterministic evaluator")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to P25 ephemeral policy record JSON files.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    parser.add_argument(
        "--h3-out",
        type=Path,
        help="Output JSON path for the P30-H3 action span-cost accounting report. Defaults beside --out.",
    )
    parser.add_argument(
        "--h3-doc",
        type=Path,
        help="Output markdown path for the P30-H3 action span-cost accounting report. Defaults beside --doc.",
    )
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
            reason = "Aggregate summary lacks per-task ephemeral policy records required for admission evaluation."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        if rec.get("_p25_input_empty_marker"):
            status = "insufficient_task_detail"
            reason = "Input artifact did not contain per-task ephemeral policy records."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        if rec.get("_p25_unsupported_schema_marker"):
            status = "insufficient_task_detail"
            reason = "P30 real evaluation requires p25-policy-records-ephemeral-v1 input schema."
            insufficient_paths.append(rec.get("path", "unknown"))
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
        reason = "Records lacked candidate_baseline outcome fields required for admission evaluation."

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

    h3_report = report.get("h3_action_span_cost_accounting")
    if h3_report:
        h3_out = args.h3_out or _default_h3_out_for(args.out)
        h3_doc = args.h3_doc or _default_h3_doc_for(args.doc)
        h3_out.parent.mkdir(parents=True, exist_ok=True)
        _write_json(h3_out, h3_report)
        h3_doc.parent.mkdir(parents=True, exist_ok=True)
        h3_doc.write_text(build_h3_markdown(h3_report), encoding="utf-8")
        print(f"P30-H3 span-cost report written to {h3_out}")
        print(f"P30-H3 span-cost doc written to {h3_doc}")

    errors = validate_report(report)
    if errors:
        raise RuntimeError(f"P30 report validation failed: {errors}")

    print(f"P30 report written to {args.out}")
    print(f"P30 markdown written to {args.doc}")
    print("P30 report validation ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
