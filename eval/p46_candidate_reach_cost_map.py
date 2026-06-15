#!/usr/bin/env python3
"""P46 Candidate Reach × Cost / Candidate-to-Evidence Materialization Gate.

P46 is a deterministic, SCORE-phase-only diagnostic evaluator.  It consumes the
same ephemeral P25-policy records (`p25-policy-records-ephemeral-v1`) that feed
P25, P30, P31, and P33-B, and builds a public aggregate map of:

1. Candidate reach vs. span cost per strategy and per K.
2. Candidate materialization diagnostics from lightweight pool metadata.
3. Reach/cost breakdowns by public task bucket, risk tags, and P33-B subtype axes.
4. Policy-route snapshots for `bucket_routed_v0` and `admission_v3_h4b` when the
   necessary route features/outcomes are present.

Hard constraints:
* No remote calls; `remote_calls_by_p46=0`.
* No EvidenceCore semantics change.
* RUN phase cannot read labels; this evaluator loads private labels only after RUN
  and uses them only for aggregate SCORE-phase metrics.
* Public outputs are aggregate-only: no task IDs, candidate IDs, paths, spans,
  gold spans, private labels, route features, snippets, prompts, responses, or
  provider URLs/keys.
* `promotion_ready=false`, `default_should_change=false`,
  `evidencecore_semantics_changed=false`, `candidate_not_fact=true`.
* If data is missing, report `availability=missing_*`; do not fabricate zeros.
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

try:
    import p30_admission_model_v3 as p30
except Exception:  # pragma: no cover
    p30 = None  # type: ignore[assignment]

SCHEMA_VERSION = "p46-candidate-reach-cost-map-v1"
GENERATED_BY = "eval/p46_candidate_reach_cost_map.py"

DEFAULT_OUT = Path("artifacts/p46_candidate_reach_cost_map/p46_candidate_reach_cost_map_report.json")
DEFAULT_DOC = Path("docs/en/p46-candidate-reach-cost-map.md")

K_VALUES = [1, 3, 5, 10, 20]

REACH_STRATEGIES = [
    "candidate_baseline",
    "rrf_primary",
    "symbol_primary",
    "regex_primary",
    "symbol_regex_union",
    "llm_span_narrow",
    "llm_filter",
    "llm_abstain_filter",
]

TRANSFORMED_STRATEGIES = [
    "llm_span_narrow",
    "llm_filter",
    "llm_abstain_filter",
    "symbol_regex_union",
    "rrf_primary",
    "bucket_routed_v0",
    "admission_v3_h4b",
]

OUTCOME_STRATEGIES = [
    "candidate_baseline",
    "rrf_primary",
    "symbol_primary",
    "regex_primary",
    "symbol_regex_union",
    "llm_span_narrow",
    "llm_filter",
    "llm_abstain_filter",
    "supporting_only",
    "weak_candidate_only",
]

SUBTYPE_SOURCE_CLASSES = {"symbol_only", "regex_only", "symbol_regex_fusion", "other"}
SUBTYPE_AGREEMENT_CLASSES = {"single_source", "same_file_only", "span_overlap", "disagree"}
SUBTYPE_SPAN_WIDTH_BINS = {"point", "short", "long", "unknown"}
SUBTYPE_RANK_BINS = {"top3", "top5", "top10", "unknown"}
SUBTYPE_COUNT_BINS = {"small", "medium", "large", "unknown"}
SUBTYPE_AXES = ["source_class", "agreement_class", "rrf_backing", "span_width_bin", "rank_bin", "candidate_count_bin"]

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
    "p33b_anchor_subtypes_schema",
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
    "remote_calls_by_p46",
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
    "task_count",
    "positive_task_count",
    "no_gold_task_count",
    "positive_with_pools_count",
    "positive_with_gold_spans_count",
    "candidate_pool_availability",
    "gold_span_availability",
    "subtype_breakdown_availability",
    "materialization_availability",
    "reach_metrics_available",
    "outcome_metrics_available",
    "policy_route_availability",
    "p31_h1_handoff_detected",
    "p31_h1_handoff_detected_count",
    "p33b_handoff_detected",
    "p33b_handoff_detected_count",
    "p33b_handoff_schema_version",
    "reach_strategies",
    "transformed_strategies",
    "outcome_strategies",
    "metrics",
    "conclusion",
    "validation",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def _ratio(num: int, den: int) -> float | None:
    if den <= 0 or num < 0:
        return None
    return round(num / den, 6)


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    """Recursively reject private keys that must not appear in public artifacts."""
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def normalize_label(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract only private-in-memory gold metadata used for aggregate scoring."""
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


def _extract_pools(raw: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Load P31-H1 candidate pools if present; otherwise legacy candidate_pool."""
    pools = raw.get("p31_candidate_pools")
    if isinstance(pools, dict):
        return {str(k): list(v) for k, v in pools.items() if isinstance(v, list)}
    pools = raw.get("candidate_pool")
    if isinstance(pools, dict):
        return {str(k): list(v) for k, v in pools.items() if isinstance(v, list)}
    return {}


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


def _extract_route_features(raw: dict[str, Any]) -> dict[str, Any]:
    rf = raw.get("route_features")
    return rf if isinstance(rf, dict) else {}


def normalize_task(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize ephemeral P25 record into P46 private in-memory task."""
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

    if raw.get("score_group") == "positive":
        has_gold = True
    elif raw.get("score_group") == "no_gold":
        has_gold = False
    else:
        has_gold = bool(raw.get("has_gold", False))

    label_raw = raw.get("p31_score_gold") or raw.get("label") or {}
    label = normalize_label(label_raw)
    if has_gold:
        label["has_gold"] = True

    pools = _extract_pools(raw)
    has_candidate_pool = bool(pools)

    outcomes: dict[str, Any] = {}
    for strategy in OUTCOME_STRATEGIES:
        src = _extract_outcome(raw, strategy)
        added_gold = _as_int(src.get("added_gold_span"))
        added_false = _as_int(src.get("added_false_span"))
        cost_available = added_gold is not None and added_false is not None
        outcomes[strategy] = {
            "outcome_present": bool(src),
            "cost_available": cost_available,
            "file_recall_at_5": _as_float(src.get("file_recall_at_5")),
            "span_f0_5": _as_float(src.get("span_f0_5")),
            "primary_false_positive_rate": _as_float(src.get("primary_false_positive_rate")),
            "no_gold_false_primary_rate": _as_float(src.get("no_gold_false_primary_rate")),
            "added_gold_span": added_gold,
            "added_false_span": added_false,
            "abstained": bool(src.get("abstained", False)),
        }

    subtypes: list[dict[str, Any]] = []
    for row in raw.get("p33b_anchor_subtypes") or []:
        if isinstance(row, dict):
            subtypes.append(row)

    return {
        "task_id": tid,
        "repo_id": raw.get("repo_id"),
        "task_bucket": task_bucket,
        "task_risk_tags": risk_tags,
        "has_gold": has_gold,
        "has_gold_spans": bool(label["gold_spans"]),
        "label": label,
        "pools": pools,
        "has_candidate_pool": has_candidate_pool,
        "outcomes": outcomes,
        "subtypes": subtypes,
        "route_context": _route_context(raw, task_bucket, risk_tags),
    }


def _route_context(raw: dict[str, Any], task_bucket: str, risk_tags: list[str]) -> dict[str, Any]:
    """Build the route-feature dict consumed by P25/P30 routing functions."""
    rf = _extract_route_features(raw)
    tags_lower = {str(t).lower() for t in risk_tags}
    return {
        "task_bucket": task_bucket,
        "task_risk_tags": risk_tags,
        "route_features": {
            "candidate_count": int(rf.get("candidate_count") or 0),
            "candidate_support_exists": bool(rf.get("candidate_support_exists", bool(rf.get("candidate_count")))),
            "unique_symbol_anchor": bool(rf.get("unique_symbol_anchor", False)),
            "exact_unique_symbol_anchor": bool(rf.get("exact_unique_symbol_anchor", False)),
            "symbol_anchor": bool(rf.get("symbol_anchor", False)) or "symbol_anchor" in tags_lower or "exact_symbol" in tags_lower,
            "regex_anchor": bool(rf.get("regex_anchor", False)) or "regex_anchor" in tags_lower,
            "local_anchor": bool(rf.get("local_anchor", False)),
            "symbol_regex_agree_file": bool(rf.get("symbol_regex_agree_file", False)),
            "symbol_regex_agree_span": bool(rf.get("symbol_regex_agree_span", False)),
            "rrf_anchor_agree_file": bool(rf.get("rrf_anchor_agree_file", False)),
            "rrf_anchor_agree_span": bool(rf.get("rrf_anchor_agree_span", False)),
            "rrf_backed_by_anchor": bool(rf.get("rrf_backed_by_anchor", False)),
            "query_noise": _as_float(rf.get("query_noise")) or 0.0,
            "llm_span_narrow_valid": bool(rf.get("llm_span_narrow_valid", False)),
            "llm_span_within_candidate": bool(rf.get("llm_span_within_candidate", False)),
            "dense_support_present": bool(rf.get("dense_support_present", False)),
            "graph_support_present": bool(rf.get("graph_support_present", False)),
        },
        "_p33b_anchor_subtypes": subtypes if isinstance((subtypes := raw.get("p33b_anchor_subtypes")), list) else [],
        "_p33b_handoff_detected": bool(
            isinstance(raw.get("p33b_anchor_subtypes"), list)
            and len(raw.get("p33b_anchor_subtypes", [])) > 0
            and isinstance(raw.get("p33b_anchor_subtypes_schema"), str)
        ),
    }


def _gold_files(label: dict[str, Any]) -> set[str]:
    return label.get("gold_files", set())


def _gold_spans(label: dict[str, Any]) -> set[tuple[str, int, int]]:
    out: set[tuple[str, int, int]] = set()
    for gs in label.get("gold_spans", []):
        path = gs.get("path", "")
        start = gs.get("start_line", 0)
        end = gs.get("end_line", 0)
        if path:
            out.add((path, start, end))
    return out


def _is_file_reached(items: list[dict[str, Any]], label: dict[str, Any]) -> bool:
    files = {str(ev.get("path") or "").lower() for ev in items if ev.get("path")}
    return bool(files & _gold_files(label))


def _spans_of(items: list[dict[str, Any]]) -> set[tuple[str, int, int]]:
    out: set[tuple[str, int, int]] = set()
    for ev in items:
        try:
            path = str(ev.get("path") or "").lower()
            start = int(ev.get("start_line") or 0)
            end = int(ev.get("end_line") or 0)
        except (TypeError, ValueError):
            continue
        if path:
            out.add((path, start, end))
    return out


def _is_span_reached(items: list[dict[str, Any]], label: dict[str, Any]) -> bool:
    gold_spans = _gold_spans(label)
    if not gold_spans:
        return False
    for ev in items:
        try:
            path = str(ev.get("path") or "").lower()
            start = int(ev.get("start_line") or 0)
            end = int(ev.get("end_line") or 0)
        except (TypeError, ValueError):
            continue
        for gp, gs, ge in gold_spans:
            if path == gp and end >= gs and start <= ge:
                return True
    return False


def _has_valid_path(ev: dict[str, Any]) -> bool:
    path = str(ev.get("path") or "")
    if not path:
        return False
    if path.startswith("/"):
        return False
    if ".." in Path(path).parts:
        return False
    return True


def _has_valid_range(ev: dict[str, Any]) -> bool:
    try:
        start = int(ev.get("start_line") or 0)
        end = int(ev.get("end_line") or 0)
    except (TypeError, ValueError):
        return False
    return 1 <= start <= end


def compute_reach_cost_map(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate reach/cost metrics per strategy and K from candidate pools."""
    positive_tasks = [t for t in tasks if t["has_gold"] and t.get("has_gold_spans")]
    by_strategy: dict[str, Any] = {}
    availability: dict[str, str] = {}

    for strategy in REACH_STRATEGIES:
        has_pool = any(strategy in t.get("pools", {}) for t in positive_tasks)
        if not has_pool:
            availability[strategy] = "missing_pool"
            by_strategy[strategy] = {"availability": "missing_pool"}
            continue
        availability[strategy] = "available"
        by_k: dict[int, dict[str, Any]] = {}
        for k in K_VALUES:
            file_num = span_num = absent_num = frsw_num = unique_num = denom = 0
            for t in positive_tasks:
                if strategy not in t.get("pools", {}):
                    continue
                denom += 1
                items = t["pools"][strategy][:k]
                file_reach = _is_file_reached(items, t["label"])
                span_reach = _is_span_reached(items, t["label"])
                if file_reach:
                    file_num += 1
                else:
                    absent_num += 1
                if span_reach:
                    span_num += 1
                if file_reach and not span_reach:
                    frsw_num += 1
                # Unique span reach for this strategy vs. all others available.
                other_items: list[dict[str, Any]] = []
                for other in REACH_STRATEGIES:
                    if other != strategy and other in t.get("pools", {}):
                        other_items.extend(t["pools"][other][:k])
                other_span = _is_span_reached(other_items, t["label"])
                if span_reach and not other_span:
                    unique_num += 1
            by_k[k] = {
                "gold_file_reach": {"numerator": file_num, "denominator": denom, "rate": _rate(file_num, denom)},
                "gold_span_reach": {"numerator": span_num, "denominator": denom, "rate": _rate(span_num, denom)},
                "unique_gold_span_reach": {"numerator": unique_num, "denominator": denom, "rate": _rate(unique_num, denom)},
                "candidate_absent_rate": {"numerator": absent_num, "denominator": denom, "rate": _rate(absent_num, denom)},
                "file_right_span_wrong_rate": {"numerator": frsw_num, "denominator": file_num, "rate": _rate(frsw_num, file_num)},
            }
        by_strategy[strategy] = {"availability": "available", "by_k": by_k}

    reach_metrics_available = any(a == "available" for a in availability.values())
    return {
        "by_strategy": by_strategy,
        "strategy_availability": availability,
        "reach_metrics_available": reach_metrics_available,
    }


def _outcome_cost_block(tasks: list[dict[str, Any]], strategy: str) -> dict[str, Any]:
    task_count = len(tasks)
    positive_count = sum(1 for t in tasks if t["has_gold"])
    no_gold_count = task_count - positive_count

    added_gold: int | None = None
    added_false: int | None = None
    span_f: list[float] = []
    pfp: list[float] = []
    ng_pfp: list[float] = []
    present_count = 0
    cost_available_count = 0

    for t in tasks:
        out = t["outcomes"].get(strategy, {})
        if not out.get("outcome_present"):
            continue
        present_count += 1
        if out.get("cost_available"):
            cost_available_count += 1
            ag = out.get("added_gold_span")
            af = out.get("added_false_span")
            if ag is not None:
                added_gold = (added_gold or 0) + ag
            if af is not None:
                added_false = (added_false or 0) + af
        sf = out.get("span_f0_5")
        if sf is not None:
            span_f.append(sf)
        p = out.get("primary_false_positive_rate")
        if p is not None:
            pfp.append(p)
        if not t["has_gold"]:
            ng = out.get("no_gold_false_primary_rate")
            if ng is None and p is not None:
                ng = p
            if ng is not None:
                ng_pfp.append(ng)

    availability = "available" if present_count > 0 else ("missing_outcomes" if task_count > 0 else "missing_outcomes")
    return {
        "availability": availability,
        "task_count": task_count,
        "positive_task_count": positive_count,
        "no_gold_task_count": no_gold_count,
        "outcome_present_count": present_count,
        "outcome_missing_count": task_count - present_count,
        "cost_available_count": cost_available_count,
        "cost_missing_count": task_count - cost_available_count,
        "added_gold_span": added_gold,
        "added_false_span": added_false,
        "false_per_gold": _ratio(added_false or 0, added_gold or 0) if added_gold else None,
        "gold_per_false": _ratio(added_gold or 0, added_false or 0) if added_false else None,
        "net_span_value_1x": (added_gold or 0) - (added_false or 0) if added_gold is not None or added_false is not None else None,
        "net_span_value_2x": (added_gold or 0) - (2 * (added_false or 0)) if added_gold is not None or added_false is not None else None,
        "mean_span_f0_5": _avg(span_f),
        "mean_primary_false_positive_rate": _avg(pfp),
        "mean_no_gold_false_primary_rate": _avg(ng_pfp),
    }


def compute_outcome_cost_map(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate span-cost/outcome metrics per base/transformed strategy."""
    by_strategy: dict[str, Any] = {}
    for strategy in OUTCOME_STRATEGIES:
        by_strategy[strategy] = _outcome_cost_block(tasks, strategy)
    return {
        "by_strategy": by_strategy,
        "outcome_metrics_available": any(
            b.get("availability") == "available" for b in by_strategy.values()
        ),
    }


def compute_materialization_diagnostics(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate candidate materialization diagnostics from pool metadata.

    Because ephemeral P25 records do not carry a checkout root, actual source
    file reads default to "materialization_unavailable".  If a record provides
    a private `_repo_root` field in the route_context, the evaluator performs a
    safe deterministic validation and moves items to the appropriate bucket.
    """    
    by_strategy: dict[str, Any] = {}
    overall_seen = 0

    for strategy in REACH_STRATEGIES:
        seen = 0
        materialized_valid = 0
        rejected_invalid_path = 0
        rejected_invalid_range = 0
        rejected_stale_sha = 0
        rejected_missing_file = 0
        rejected_other = 0
        has_pool = False
        source_read_possible = False
        for t in tasks:
            pool = t.get("pools", {}).get(strategy, [])
            if not isinstance(pool, list):
                continue
            if pool:
                has_pool = True
            repo = (t.get("route_context") or {}).get("_repo_root")
            if isinstance(repo, (str, Path)):
                source_read_possible = True
                repo_root = Path(repo).resolve()
            else:
                repo_root = None
            for ev in pool:
                seen += 1
                overall_seen += 1
                if not _has_valid_path(ev):
                    rejected_invalid_path += 1
                    continue
                if not _has_valid_range(ev):
                    rejected_invalid_range += 1
                    continue
                if repo_root is not None:
                    try:
                        rel = Path(str(ev.get("path") or ""))
                        if rel.is_absolute() or ".." in rel.parts:
                            rejected_invalid_path += 1
                            continue
                        full = (repo_root / rel).resolve()
                        if not full.is_relative_to(repo_root):
                            rejected_invalid_path += 1
                            continue
                        if not full.exists() or not full.is_file() or full.is_symlink():
                            rejected_missing_file += 1
                            continue
                        sha = ev.get("content_sha")
                        if sha:
                            content = full.read_bytes()
                            actual = hashlib.sha256(content).hexdigest()
                            if actual != str(sha):
                                rejected_stale_sha += 1
                                continue
                        materialized_valid += 1
                    except Exception:
                        rejected_other += 1
        if not has_pool:
            by_strategy[strategy] = {"availability": "missing_pool"}
            continue
        if source_read_possible:
            availability = "available"
            rate = _rate(materialized_valid, seen)
        else:
            availability = "source_read_unavailable"
            rate = None
        by_strategy[strategy] = {
            "availability": availability,
            "candidates_seen": seen,
            "materialized_valid": materialized_valid,
            "rejected_invalid_path": rejected_invalid_path,
            "rejected_invalid_range": rejected_invalid_range,
            "rejected_stale_sha_content_sha_mismatch": rejected_stale_sha,
            "rejected_missing_file": rejected_missing_file,
            "rejected_other": rejected_other,
            "materialization_rate": rate,
        }

    overall = {
        "availability": "source_read_unavailable",
        "candidates_seen": overall_seen,
        "materialized_valid": 0,
        "rejected_invalid_path": 0,
        "rejected_invalid_range": 0,
        "rejected_stale_sha_content_sha_mismatch": 0,
        "rejected_missing_file": 0,
        "rejected_other": 0,
        "materialization_rate": None,
        "note": "Source-file materialization validation is currently not wired by default. P46 reports source_read_unavailable unless the ephemeral record explicitly carries a private checkout root.",
    }
    if any(s.get("availability") == "available" for s in by_strategy.values()):
        overall["availability"] = "available"
        total_seen = sum(s.get("candidates_seen", 0) for s in by_strategy.values() if "candidates_seen" in s)
        total_valid = sum(s.get("materialized_valid", 0) for s in by_strategy.values() if "materialized_valid" in s)
        overall["candidates_seen"] = total_seen
        overall["materialized_valid"] = total_valid
        overall["materialization_rate"] = _rate(total_valid, total_seen)

    return {
        "materialization_availability": overall["availability"],
        "overall": overall,
        "by_strategy": by_strategy,
    }


def _sanitize_subtype_values(row: dict[str, Any]) -> dict[str, str]:
    """Allowlist P33-B subtype axis values so public keys cannot leak raw strings."""
    src = str(row.get("source_class") or "other")
    if src not in SUBTYPE_SOURCE_CLASSES:
        src = "other"
    agr = str(row.get("agreement_class") or "single_source")
    if agr not in SUBTYPE_AGREEMENT_CLASSES:
        agr = "other"
    rrf = "rrf_yes" if row.get("rrf_backing") else "rrf_no"
    span = str(row.get("span_width_bin") or "unknown")
    if span not in SUBTYPE_SPAN_WIDTH_BINS:
        span = "unknown"
    rank = str(row.get("rank_bin") or "unknown")
    if rank not in SUBTYPE_RANK_BINS:
        rank = "unknown"
    count = str(row.get("candidate_count_bin") or "unknown")
    if count not in SUBTYPE_COUNT_BINS:
        count = "unknown"
    return {
        "source_class": src,
        "agreement_class": agr,
        "rrf_backing": rrf,
        "span_width_bin": span,
        "rank_bin": rank,
        "candidate_count_bin": count,
    }


def _bucket_key_for_subtype(row: dict[str, Any]) -> str:
    vals = _sanitize_subtype_values(row)
    return f"{vals['source_class']}__{vals['agreement_class']}__{vals['rrf_backing']}"


def _axis_values(t: dict[str, Any]) -> dict[str, set[str]]:
    """Collect public subtype axis bucket names attached to a task."""
    values: dict[str, set[str]] = defaultdict(set)
    combo: set[str] = set()
    for row in t.get("subtypes") or []:
        if not isinstance(row, dict):
            continue
        vals = _sanitize_subtype_values(row)
        for axis in SUBTYPE_AXES:
            values[axis].add(vals[axis])
        combo.add(_bucket_key_for_subtype(row))
    values["subtype_combination"] = combo
    return values


def _reach_k_per_group(
    tasks: list[dict[str, Any]],
    strategy: str,
    k: int,
) -> dict[str, Any]:
    file_num = span_num = absent_num = frsw_num = denom = 0
    positive = [t for t in tasks if t["has_gold"] and t.get("has_gold_spans") and strategy in t.get("pools", {})]
    denom = len(positive)
    for t in positive:
        items = t["pools"][strategy][:k]
        file_reach = _is_file_reached(items, t["label"])
        span_reach = _is_span_reached(items, t["label"])
        if file_reach:
            file_num += 1
        else:
            absent_num += 1
        if span_reach:
            span_num += 1
        if file_reach and not span_reach:
            frsw_num += 1
    return {
        "gold_file_reach": {"numerator": file_num, "denominator": denom, "rate": _rate(file_num, denom)},
        "gold_span_reach": {"numerator": span_num, "denominator": denom, "rate": _rate(span_num, denom)},
        "candidate_absent_rate": {"numerator": absent_num, "denominator": denom, "rate": _rate(absent_num, denom)},
        "file_right_span_wrong_rate": {"numerator": frsw_num, "denominator": file_num, "rate": _rate(frsw_num, file_num)},
    }


def compute_subtype_breakdowns(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate reach/cost by P33-B subtype axes when subtype metadata is present."""
    tasks_with_subtypes = [t for t in tasks if t.get("subtypes")]
    if not tasks_with_subtypes:
        return {
            "availability": "missing_subtype_data",
            "by_subtype_combination": {},
            "by_axis": {},
        }

    # Group tasks by combination key.
    combo_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    axis_groups: dict[str, dict[str, list[dict[str, Any]]]] = {axis: defaultdict(list) for axis in SUBTYPE_AXES}
    for t in tasks_with_subtypes:
        values = _axis_values(t)
        for key in values.get("subtype_combination", set()):
            combo_groups[key].append(t)
        for axis, vals in values.items():
            if axis == "subtype_combination":
                continue
            for val in vals:
                axis_groups[axis][val].append(t)

    by_combo: dict[str, Any] = {}
    for key, group in sorted(combo_groups.items()):
        by_combo[key] = {
            "task_count": len(group),
            "positive_task_count": sum(1 for t in group if t["has_gold"]),
            "no_gold_task_count": sum(1 for t in group if not t["has_gold"]),
            "outcome_cost": _outcome_cost_block(group, "symbol_regex_union"),
            "reach_at_5": {
                "candidate_baseline": _reach_k_per_group(group, "candidate_baseline", 5),
                "symbol_regex_union": _reach_k_per_group(group, "symbol_regex_union", 5),
            },
        }

    by_axis: dict[str, Any] = {}
    for axis, groups in axis_groups.items():
        by_axis[axis] = {}
        for val, group in sorted(groups.items()):
            by_axis[axis][val] = {
                "task_count": len(group),
                "positive_task_count": sum(1 for t in group if t["has_gold"]),
                "no_gold_task_count": sum(1 for t in group if not t["has_gold"]),
                "outcome_cost": _outcome_cost_block(group, "symbol_regex_union"),
                "reach_at_5": {
                    "candidate_baseline": _reach_k_per_group(group, "candidate_baseline", 5),
                    "symbol_regex_union": _reach_k_per_group(group, "symbol_regex_union", 5),
                },
            }

    return {
        "availability": "available",
        "task_count_with_subtypes": len(tasks_with_subtypes),
        "by_subtype_combination": by_combo,
        "by_axis": by_axis,
    }


def compute_public_bucket_breakdowns(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate reach/cost by public task bucket and risk tags."""
    bucket_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    tag_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in tasks:
        bucket_groups[t.get("task_bucket", "unknown")].append(t)
        for tag in t.get("task_risk_tags", []):
            tag_groups[tag].append(t)

    by_bucket: dict[str, Any] = {}
    for bucket, group in sorted(bucket_groups.items()):
        by_bucket[bucket] = {
            "task_count": len(group),
            "positive_task_count": sum(1 for t in group if t["has_gold"]),
            "no_gold_task_count": sum(1 for t in group if not t["has_gold"]),
            "outcome_cost": _outcome_cost_block(group, "symbol_regex_union"),
            "reach_at_5": {
                "candidate_baseline": _reach_k_per_group(group, "candidate_baseline", 5),
                "symbol_regex_union": _reach_k_per_group(group, "symbol_regex_union", 5),
            },
        }

    by_tag: dict[str, Any] = {}
    for tag, group in sorted(tag_groups.items()):
        by_tag[tag] = {
            "task_count": len(group),
            "positive_task_count": sum(1 for t in group if t["has_gold"]),
            "no_gold_task_count": sum(1 for t in group if not t["has_gold"]),
            "outcome_cost": _outcome_cost_block(group, "symbol_regex_union"),
            "reach_at_5": {
                "candidate_baseline": _reach_k_per_group(group, "candidate_baseline", 5),
                "symbol_regex_union": _reach_k_per_group(group, "symbol_regex_union", 5),
            },
        }

    return {"by_task_bucket": by_bucket, "by_risk_tag": by_tag}


def compute_unique_reach(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-strategy unique gold-span reach at K=5."""
    positive_tasks = [t for t in tasks if t["has_gold"] and t.get("has_gold_spans")]
    k = 5
    by_strategy: dict[str, Any] = {}
    for strategy in REACH_STRATEGIES:
        if not any(strategy in t.get("pools", {}) for t in positive_tasks):
            by_strategy[strategy] = {"availability": "missing_pool"}
            continue
        span_num = unique_num = denom = 0
        for t in positive_tasks:
            if strategy not in t.get("pools", {}):
                continue
            denom += 1
            items = t["pools"][strategy][:k]
            span_reach = _is_span_reached(items, t["label"])
            other_items: list[dict[str, Any]] = []
            for other in REACH_STRATEGIES:
                if other != strategy and other in t.get("pools", {}):
                    other_items.extend(t["pools"][other][:k])
            other_span = _is_span_reached(other_items, t["label"])
            if span_reach:
                span_num += 1
                if not other_span:
                    unique_num += 1
        by_strategy[strategy] = {
            "availability": "available",
            "gold_span_reach": {"numerator": span_num, "denominator": denom, "rate": _rate(span_num, denom)},
            "unique_gold_span_reach": {"numerator": unique_num, "denominator": denom, "rate": _rate(unique_num, denom)},
            "unique_span_reach_share": _rate(unique_num, span_num) if span_num else None,
        }
    return by_strategy


def _lookup_outcome(t: dict[str, Any], strategy: str) -> dict[str, Any]:
    return t.get("outcomes", {}).get(strategy, {})


def _policy_action_info_factory() -> dict[str, Any]:
    return {
        "task_count": 0,
        "positive_count": 0,
        "no_gold_count": 0,
        "outcome_present_count": 0,
        "outcome_missing_count": 0,
        "cost_present_count": 0,
        "cost_missing_count": 0,
        "added_gold": 0,
        "added_false": 0,
    }


def _build_action_span_cost_table(
    action_info: dict[str, dict[str, Any]],
    total_selected: int,
) -> dict[str, Any]:
    total_outcome_present = sum(b.get("outcome_present_count", 0) for b in action_info.values())
    total_cost_present = sum(b.get("cost_present_count", 0) for b in action_info.values())
    total_outcome_missing = total_selected - total_outcome_present
    total_cost_missing = total_selected - total_cost_present

    if total_cost_missing == 0:
        policy_availability = "available"
    elif total_cost_present > 0:
        policy_availability = "partial_missing_cost_fields"
    else:
        policy_availability = "missing_cost_fields"

    action_span_cost: dict[str, Any] = {}
    for action, b in action_info.items():
        if b["task_count"] == 0:
            continue
        if b["cost_missing_count"] == 0:
            action_availability = "available"
        elif b["cost_present_count"] == 0:
            action_availability = "missing_cost_fields"
        else:
            action_availability = "partial_missing_cost_fields"

        added_gold: int | None = b["added_gold"] if b["cost_present_count"] > 0 else None
        added_false: int | None = b["added_false"] if b["cost_present_count"] > 0 else None
        action_span_cost[action] = {
            "availability": action_availability,
            "task_count": b["task_count"],
            "positive_task_count": b["positive_count"],
            "no_gold_task_count": b["no_gold_count"],
            "outcome_present_count": b["outcome_present_count"],
            "outcome_missing_count": b["outcome_missing_count"],
            "cost_present_count": b["cost_present_count"],
            "cost_missing_count": b["cost_missing_count"],
            "added_gold_span": added_gold,
            "added_false_span": added_false,
            "false_per_gold": _ratio(added_false or 0, added_gold or 0) if added_gold else None,
            "gold_per_false": _ratio(added_gold or 0, added_false or 0) if added_false else None,
            "net_span_value_1x": (added_gold or 0) - (added_false or 0) if added_gold is not None or added_false is not None else None,
            "net_span_value_2x": (added_gold or 0) - (2 * (added_false or 0)) if added_gold is not None or added_false is not None else None,
        }

    return {
        "availability": policy_availability,
        "selected_task_count": total_selected,
        "selected_with_outcome_count": total_outcome_present,
        "selected_missing_outcome_count": total_outcome_missing,
        "outcome_fallback_rate": _rate(total_outcome_missing, total_selected),
        "selected_with_cost_count": total_cost_present,
        "selected_missing_cost_count": total_cost_missing,
        "cost_fallback_rate": _rate(total_cost_missing, total_selected),
        "action_counts": {action: info["task_count"] for action, info in action_info.items()},
        "action_span_cost": action_span_cost,
    }


def compute_policy_routes(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate bucket_routed_v0 and admission_v3_h4b route outcomes.

    A selected action only contributes numeric span cost when the ephemeral record
    contains both ``added_gold_span`` and ``added_false_span``.  Missing outcomes or
    partial numeric fields are counted separately and never zero-filled.
    """
    result: dict[str, Any] = {}

    if not tasks:
        result["bucket_routed_v0"] = {"availability": "missing tasks"}
        result["admission_v3_h4b"] = {"availability": "missing tasks"}
        return result

    # bucket_routed_v0
    try:
        calibrated_negative = p25.choose_negative_strategy(tasks)
        actions: list[str] = []
        by_action: dict[str, dict[str, Any]] = defaultdict(_policy_action_info_factory)
        for t in tasks:
            route_ctx = t.get("route_context", {})
            action: str = p25.route_bucket_routed_v0(route_ctx, calibrated_negative)
            actions.append(action)
            b = by_action[action]
            b["task_count"] += 1
            if t["has_gold"]:
                b["positive_count"] += 1
            else:
                b["no_gold_count"] += 1
            out = _lookup_outcome(t, action)
            if out.get("outcome_present"):
                b["outcome_present_count"] += 1
            else:
                b["outcome_missing_count"] += 1
            if out.get("cost_available"):
                b["cost_present_count"] += 1
                b["added_gold"] += out.get("added_gold_span") or 0
                b["added_false"] += out.get("added_false_span") or 0
            else:
                b["cost_missing_count"] += 1
        result["bucket_routed_v0"] = _build_action_span_cost_table(by_action, len(actions))
        result["bucket_routed_v0"]["fixed_negative_strategy"] = calibrated_negative
    except Exception:
        result["bucket_routed_v0"] = {"availability": "route_error"}

    # admission_v3_h4b
    if p30 is None:
        result["admission_v3_h4b"] = {"availability": "missing_admission_module"}
    else:
        try:
            action_map = p30.ACTION_OUTCOME_MAP
            actions = []
            by_action = defaultdict(_policy_action_info_factory)
            for t in tasks:
                route_ctx = t.get("route_context", {})
                routing = p30.route_admission_v3_h4b(route_ctx)
                action: str = routing["action"]
                actions.append(action)
                outcome_key: str = str(action_map.get(action, action))
                out = _lookup_outcome(t, outcome_key)
                b = by_action[action]
                b["task_count"] += 1
                if t["has_gold"]:
                    b["positive_count"] += 1
                else:
                    b["no_gold_count"] += 1
                if out.get("outcome_present"):
                    b["outcome_present_count"] += 1
                else:
                    b["outcome_missing_count"] += 1
                if out.get("cost_available"):
                    b["cost_present_count"] += 1
                    b["added_gold"] += out.get("added_gold_span") or 0
                    b["added_false"] += out.get("added_false_span") or 0
                else:
                    b["cost_missing_count"] += 1
            result["admission_v3_h4b"] = _build_action_span_cost_table(by_action, len(actions))
        except Exception:
            result["admission_v3_h4b"] = {"availability": "route_error"}

    return result


def make_self_test_records() -> list[dict[str, Any]]:
    """Deterministic synthetic ephemeral P25-policy records."""
    def pool(paths: list[tuple[str, int, int]]) -> list[dict[str, Any]]:
        return [
            {"rank": i + 1, "path": p, "start_line": s, "end_line": e, "candidate_id": f"cid_{i+1}"}
            for i, (p, s, e) in enumerate(paths)
        ]

    def gold(path: str, start: int, end: int) -> dict[str, Any]:
        return {"has_gold": True, "gold_spans": [{"path": path, "start_line": start, "end_line": end}]}

    tasks: list[dict[str, Any]] = []

    # 1. Positive high-confidence with rich pools.
    tasks.append({
        "task_id": "p46-st-001",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["high_confidence"],
        "score_group": "positive",
        "route_features": {
            "candidate_count": 3,
            "candidate_support_exists": True,
            "exact_unique_symbol_anchor": True,
            "symbol_anchor": True,
            "local_anchor": True,
            "symbol_regex_agree_span": True,
            "rrf_backed_by_anchor": True,
            "query_noise": 0.0,
            "llm_span_narrow_valid": True,
            "llm_span_within_candidate": True,
        },
        "p31_candidate_pools": {
            "candidate_baseline": pool([("src/app.py", 10, 15)]),
            "rrf_primary": pool([("src/app.py", 10, 15)]),
            "symbol_primary": pool([("src/app.py", 10, 15)]),
            "regex_primary": [],
            "symbol_regex_union": pool([("src/app.py", 10, 15)]),
            "llm_span_narrow": pool([("src/app.py", 10, 15)]),
            "llm_filter": pool([("src/app.py", 10, 15)]),
            "llm_abstain_filter": [],
        },
        "p31_score_gold": gold("src/app.py", 10, 15),
        "p33b_anchor_subtypes": [{
            "candidate_id": "cid_1", "rank": 1, "source_class": "symbol_regex_fusion",
            "agreement_class": "span_overlap", "rank_bin": "top3",
            "candidate_count_bin": "small", "span_width_bin": "short", "rrf_backing": True,
        }],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
        "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.30, "primary_false_positive_rate": 0.10, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 1},
        "rrf_primary": {"file_recall_at_5": 1.0, "span_f0_5": 0.28, "primary_false_positive_rate": 0.08, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 2},
        "symbol_primary": {"file_recall_at_5": 1.0, "span_f0_5": 0.25, "primary_false_positive_rate": 0.05, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 0},
        "regex_primary": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
        "symbol_regex_union": {"file_recall_at_5": 1.0, "span_f0_5": 0.35, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 0},
        "llm_span_narrow": {"file_recall_at_5": 1.0, "span_f0_5": 0.32, "primary_false_positive_rate": 0.05, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 1},
        "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.20, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
        "llm_abstain_filter": {"abstained": True},
    })

    # 2. File right, span wrong.
    tasks.append({
        "task_id": "p46-st-002",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["symbol_anchor"],
        "score_group": "positive",
        "route_features": {
            "candidate_count": 2,
            "candidate_support_exists": True,
            "symbol_anchor": True,
            "local_anchor": True,
            "query_noise": 0.1,
        },
        "p31_candidate_pools": {
            "candidate_baseline": pool([("src/app.py", 1, 5), ("src/app.py", 50, 55)]),
            "symbol_regex_union": pool([("src/app.py", 50, 55)]),
            "rrf_primary": pool([("src/app.py", 1, 5)]),
            "llm_span_narrow": pool([("src/app.py", 50, 55)]),
            "llm_filter": pool([("src/app.py", 1, 5)]),
        },
        "p31_score_gold": gold("src/app.py", 10, 15),
        "p33b_anchor_subtypes": [{
            "candidate_id": "cid_1", "rank": 1, "source_class": "symbol_only",
            "agreement_class": "single_source", "rank_bin": "top3",
            "candidate_count_bin": "small", "span_width_bin": "short", "rrf_backing": False,
        }],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
        "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.10, "primary_false_positive_rate": 0.20, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 2},
        "symbol_regex_union": {"file_recall_at_5": 1.0, "span_f0_5": 0.15, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 1},
        "rrf_primary": {"file_recall_at_5": 1.0, "span_f0_5": 0.05, "primary_false_positive_rate": 0.15, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 3},
        "llm_span_narrow": {"file_recall_at_5": 1.0, "span_f0_5": 0.12, "primary_false_positive_rate": 0.10, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 1},
        "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
    })

    # 3. No-gold task.
    tasks.append({
        "task_id": "p46-st-003",
        "repo_id": "js_express",
        "task_bucket": "negative",
        "task_risk_tags": ["negative"],
        "score_group": "no_gold",
        "route_features": {
            "candidate_count": 2,
            "candidate_support_exists": True,
            "query_noise": 0.6,
        },
        "p31_candidate_pools": {
            "candidate_baseline": pool([("src/noise.py", 1, 5)]),
            "symbol_regex_union": pool([("src/noise.py", 1, 5)]),
        },
        "p31_score_gold": {"has_gold": False, "gold_spans": []},
        "candidate_baseline": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.40, "no_gold_false_primary_rate": 0.40, "added_gold_span": 0, "added_false_span": 4},
        "symbol_regex_union": {"file_recall_at_5": 0.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
        "llm_filter": {"abstained": True},
        "llm_abstain_filter": {"abstained": True},
    })

    # 4. Outcome-only task (no pool) to exercise availability paths.
    tasks.append({
        "task_id": "p46-st-004",
        "repo_id": "js_express",
        "task_bucket": "ambiguous",
        "task_risk_tags": ["ambiguous"],
        "score_group": "positive",
        "route_features": {"candidate_count": 0, "candidate_support_exists": False, "query_noise": 0.4},
        "p31_score_gold": gold("src/ambig.py", 20, 25),
        "candidate_baseline": {"file_recall_at_5": 1.0, "span_f0_5": 0.18, "primary_false_positive_rate": 0.12, "no_gold_false_primary_rate": 0.0, "added_gold_span": 1, "added_false_span": 2},
        "llm_filter": {"file_recall_at_5": 1.0, "span_f0_5": 0.0, "primary_false_positive_rate": 0.0, "no_gold_false_primary_rate": 0.0, "added_gold_span": 0, "added_false_span": 0},
    })

    return tasks


def validate_public_report(report: dict[str, Any]) -> list[str]:
    """Validate safety flags, no banned keys, and metric invariants."""
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p46") != 0:
        errors.append("remote_calls_by_p46 must be 0")
    for flag, expected in (
        ("promotion_ready", False),
        ("default_should_change", False),
        ("evidencecore_semantics_changed", False),
        ("candidate_not_fact", True),
        ("run_phase_public_only", True),
        ("labels_loaded_after_run", True),
        ("score_phase_only_metrics", True),
        ("aggregate_only_public_artifact", True),
    ):
        if report.get(flag) is not expected:
            errors.append(f"{flag} must be {expected}")
    if report.get("self_test") and report.get("not_quality_evidence") is not True:
        errors.append("self_test must set not_quality_evidence=true")

    # Rate/range validation helpers.
    def check_rate_block(prefix: str, block: Any) -> None:
        if not isinstance(block, dict):
            return
        rate = block.get("rate")
        num = block.get("numerator")
        den = block.get("denominator")
        if rate is not None and not (0.0 <= rate <= 1.0 + 1e-9):
            errors.append(f"{prefix} rate out of range: {rate}")
        if num is not None and not isinstance(num, int):
            errors.append(f"{prefix} numerator invalid: {num}")
        if den is not None and not isinstance(den, int):
            errors.append(f"{prefix} denominator invalid: {den}")
        if isinstance(num, int) and isinstance(den, int) and num > den:
            errors.append(f"{prefix} numerator exceeds denominator")

    def walk(prefix: str, obj: Any) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, dict) and isinstance(value.get("rate"), (int, float, type(None))):
                    check_rate_block(f"{prefix}.{key}", value)
                walk(f"{prefix}.{key}", value)

    walk("metrics", report.get("metrics"))

    # Strategy-level invariant: candidate_absent rate = 1 - gold_file_reach.
    for strategy, block in (report.get("metrics", {}).get("reach_cost_map", {}).get("by_strategy", {}) or {}).items():
        if not isinstance(block, dict):
            continue
        for k in K_VALUES:
            by_k = block.get("by_k", {}).get(k, {})
            gf = by_k.get("gold_file_reach", {}).get("rate")
            ca = by_k.get("candidate_absent_rate", {}).get("rate")
            if gf is not None and ca is not None and abs(ca - (1.0 - gf)) > 1e-6:
                errors.append(f"reach_cost_map.{strategy}@K={k} candidate_absent must equal 1 - gold_file_reach")
            fr = by_k.get("file_right_span_wrong_rate", {})
            if fr.get("denominator") is not None and by_k.get("gold_file_reach", {}).get("numerator") is not None:
                if fr["denominator"] != by_k["gold_file_reach"]["numerator"]:
                    errors.append(f"reach_cost_map.{strategy}@K={k} frsw denominator must equal gold_file_reach numerator")

    # No per-task public rows.
    for forbidden in ("tasks", "task_results", "per_task_results", "records", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    # Banned-key scan.
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
) -> dict[str, Any]:
    candidate_pool_availability = "available" if tasks and all(t.get("has_candidate_pool") for t in tasks) else "partial" if any(t.get("has_candidate_pool") for t in tasks) else "missing_candidate_pool"
    gold_span_availability = "available" if tasks and all(t.get("has_gold_spans") for t in tasks if t["has_gold"]) else "partial" if any(t.get("has_gold_spans") for t in tasks if t["has_gold"]) else "missing_gold_spans"
    subtype_breakdown_availability = "available" if any(t.get("subtypes") for t in tasks) else "missing_subtype_data"
    reach_metrics_available = (candidate_pool_availability != "missing_candidate_pool" and gold_span_availability != "missing_gold_spans")

    p31_h1 = any(t.get("has_candidate_pool") and t.get("has_gold_spans") for t in tasks)
    p33b_h1 = any(t.get("subtypes") for t in tasks)

    outcome_cost = compute_outcome_cost_map(tasks)
    reach_cost = compute_reach_cost_map(tasks)
    materialization = compute_materialization_diagnostics(tasks)
    public_breakdowns = compute_public_bucket_breakdowns(tasks)
    subtype_breakdowns = compute_subtype_breakdowns(tasks)
    unique_reach = compute_unique_reach(tasks)
    policy_routes = compute_policy_routes(tasks)

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P46 Candidate Reach × Cost / Materialization Gate scaffold is ready; real per-task ephemeral P25 records are required."
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
                f"P46 reach × cost evaluation scored {len(tasks)} real ephemeral P25 records."
            )
        conclusion_lines.append(
            "P46 is SCORE-phase-only. Candidate pools and private gold spans were used only for aggregate metrics after RUN."
        )
        if reach_metrics_available:
            k5 = reach_cost["by_strategy"].get("candidate_baseline", {}).get("by_k", {}).get(5, {})
            conclusion_lines.append(
                f"Baseline@5 GoldFileReach={k5.get('gold_file_reach', {}).get('rate')}, "
                f"GoldSpanReach={k5.get('gold_span_reach', {}).get('rate')}, "
                f"CandidateAbsentRate={k5.get('candidate_absent_rate', {}).get('rate')}, "
                f"FileRightSpanWrongRate={k5.get('file_right_span_wrong_rate', {}).get('rate')}."
            )
        else:
            conclusion_lines.append(
                "Candidate pools or gold spans are missing; reach metrics are unavailable and not faked."
            )
        conclusion_lines.append(
            f"Materialization diagnostics: {materialization.get('materialization_availability')}. "
            "Source-file materialization validation is currently not wired by default; "
            "P46 reports source_read_unavailable unless the ephemeral record explicitly carries a private checkout root."
        )
        conclusion_lines.append(
            f"Outcome cost map available for {sum(1 for b in outcome_cost['by_strategy'].values() if b.get('availability') == 'available')} strategies."
        )
        if p33b_h1:
            conclusion_lines.append(
                f"P33-B subtype breakdowns cover {subtype_breakdowns.get('task_count_with_subtypes', 0)} tasks."
            )
        conclusion_lines.append("No policy is promotion-ready or default-ready.")
        conclusion_lines.append("Next: P47/P48 should consume this aggregate map to test evidence-materialization gates and budget-aware admission thresholds.")

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P46 Candidate Reach × Cost / Candidate-to-Evidence Materialization Gate",
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
        "remote_calls_by_p46": 0,
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
        "elapsed_ms": elapsed_ms,
        "task_count": len(tasks),
        "positive_task_count": sum(1 for t in tasks if t["has_gold"]),
        "no_gold_task_count": sum(1 for t in tasks if not t["has_gold"]),
        "positive_with_pools_count": sum(1 for t in tasks if t["has_gold"] and t.get("has_candidate_pool")),
        "positive_with_gold_spans_count": sum(1 for t in tasks if t["has_gold"] and t.get("has_gold_spans")),
        "candidate_pool_availability": candidate_pool_availability,
        "gold_span_availability": gold_span_availability,
        "subtype_breakdown_availability": subtype_breakdown_availability,
        "materialization_availability": materialization.get("materialization_availability", "missing"),
        "reach_metrics_available": reach_metrics_available,
        "outcome_metrics_available": outcome_cost.get("outcome_metrics_available", False),
        "policy_route_availability": any(
            v.get("availability") in {"available", "partial_fallback"}
            for v in policy_routes.values()
        ),
        "p31_h1_handoff_detected": p31_h1,
        "p31_h1_handoff_detected_count": sum(1 for t in tasks if t.get("has_candidate_pool") and t.get("has_gold_spans")),
        "p33b_handoff_detected": p33b_h1,
        "p33b_handoff_detected_count": sum(1 for t in tasks if t.get("subtypes")),
        "p33b_handoff_schema_version": "p33b-anchor-subtypes-v1" if p33b_h1 else None,
        "reach_strategies": list(REACH_STRATEGIES),
        "transformed_strategies": list(TRANSFORMED_STRATEGIES),
        "outcome_strategies": list(OUTCOME_STRATEGIES),
        "metrics": {
            "outcome_cost_map": outcome_cost,
            "reach_cost_map": reach_cost,
            "unique_reach": unique_reach,
            "materialization_diagnostics": materialization,
            "public_bucket_breakdowns": public_breakdowns,
            "subtype_breakdowns": subtype_breakdowns,
            "policy_routes": policy_routes,
        },
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P46 public report validation failed: {errors}")
    return report


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# P46 Candidate Reach × Cost / Candidate-to-Evidence Materialization Gate\n")
    lines.append(f"- Schema: `{report['schema_version']}`")
    lines.append(f"- Generated: {report['generated_at']}")
    lines.append(f"- Status: `{report['status']}`")
    lines.append(f"- Self-test: {report['self_test']}")
    lines.append(f"- Remote calls by P46: {report['remote_calls_by_p46']}")
    lines.append(f"- Candidate pool availability: `{report['candidate_pool_availability']}`")
    lines.append(f"- Gold span availability: `{report['gold_span_availability']}`")
    lines.append(f"- Reach metrics available: {report['reach_metrics_available']}")
    lines.append(f"- Materialization availability: `{report['materialization_availability']}`")
    lines.append(
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} "
        f"no_gold={report['no_gold_task_count']}\n"
    )

    if report["status"] not in {"ok", "self_test_only"}:
        lines.append("## Status")
        if report.get("status_reason"):
            lines.append(report["status_reason"])
        lines.append("")
        lines.append("Run with `--self-test` or supply ephemeral P25-policy records.")
        lines.append("")
        return "\n".join(lines)

    def fmt_rate(x: Any) -> str:
        if isinstance(x, dict):
            r = x.get("rate")
            return f"{r:.4f}" if isinstance(r, (int, float)) else "n/a"
        return "n/a"

    def fmt_counts(x: Any) -> str:
        if isinstance(x, dict):
            return f"{x.get('numerator', 'n/a')}/{x.get('denominator', 'n/a')}"
        return "n/a"

    def fmt_int(x: Any) -> str:
        return str(x) if isinstance(x, int) else "n/a"

    lines.append("## Purpose\n")
    lines.append(
        "P46 measures how much candidate evidence reaches private gold spans (`reach`) and how much "
        "span-level false risk each strategy incurs (`cost`).  It is a SCORE-phase-only diagnostic that "
        "uses the P31-H1 candidate-pool handoff and P33-B subtype handoff, but never emits per-task rows."
    )
    lines.append("")
    lines.append("## Methodology\n")
    lines.append("- Reads `p25-policy-records-ephemeral-v1` records produced by `p21_llm_rich_candidate.py`.")
    lines.append("- Computes aggregate reach@K (GoldFile, GoldSpan, UniqueGoldSpan) per strategy.")
    lines.append("- Computes outcome span-cost metrics (added_gold_span, added_false_span, false/gold, net value 1x/2x, SpanF0.5, PFP).")
    lines.append("- Includes candidate materialization diagnostics from pool metadata; source-file validation defaults to unavailable unless a checkout root is provided.")
    lines.append("- Breaks down reach/cost by public task bucket, risk tag, and P33-B subtype axes when available.")
    lines.append("- Replays `bucket_routed_v0` and `admission_v3_h4b` routing decisions to expose route span cost.")
    lines.append("")
    lines.append("## Current placeholder findings\n")
    lines.append(f"- This report is `{report['status']}`; do not use it as quality evidence.")
    lines.append(f"- Reach metrics available: {report['reach_metrics_available']}.")
    lines.append(f"- Materialization source-read availability: `{report['materialization_availability']}`.")
    lines.append(f"- Policy route evaluation: {report['policy_route_availability']}.")
    lines.append("")

    lines.append("## Outcome cost map by strategy\n")
    lines.append(
        "| Strategy | tasks | +task | no_gold | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | mean SpanF0.5 | mean PFP |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for strategy in OUTCOME_STRATEGIES:
        b = report["metrics"]["outcome_cost_map"]["by_strategy"].get(strategy, {})
        if b.get("availability") != "available":
            lines.append(f"| {strategy} | {b.get('task_count', 0)} | - | - | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        fpg = b.get("false_per_gold")
        gpf = b.get("gold_per_false")
        fpg_str = f"{fpg:.4f}" if isinstance(fpg, (int, float)) and not math.isinf(fpg) else "n/a"
        gpf_str = f"{gpf:.4f}" if isinstance(gpf, (int, float)) and not math.isinf(gpf) else "n/a"
        sf = b.get("mean_span_f0_5")
        pfp = b.get("mean_primary_false_positive_rate")
        sf_str = f"{sf:.4f}" if isinstance(sf, (int, float)) else "n/a"
        pfp_str = f"{pfp:.4f}" if isinstance(pfp, (int, float)) else "n/a"
        lines.append(
            f"| {strategy} | {b['task_count']} | {b['positive_task_count']} | {b['no_gold_task_count']} | "
            f"{fmt_int(b.get('added_gold_span'))} | {fmt_int(b.get('added_false_span'))} | {fpg_str} | {gpf_str} | "
            f"{fmt_int(b.get('net_span_value_1x'))} | {fmt_int(b.get('net_span_value_2x'))} | {sf_str} | {pfp_str} |"
        )
    lines.append("")

    if report.get("reach_metrics_available"):
        lines.append("## Reach × cost map by strategy and K\n")
        lines.append(
            "| Strategy | K | GoldFileReach | GoldSpanReach | UniqueGoldSpanReach | CandidateAbsent | FileRightSpanWrong |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for strategy in REACH_STRATEGIES:
            block = report["metrics"]["reach_cost_map"]["by_strategy"].get(strategy, {})
            if block.get("availability") != "available":
                lines.append(f"| {strategy} | - | n/a | n/a | n/a | n/a | n/a |")
                continue
            for k in K_VALUES:
                by_k = block["by_k"].get(k, {})
                lines.append(
                    f"| {strategy} | {k} | {fmt_rate(by_k.get('gold_file_reach'))} | "
                    f"{fmt_rate(by_k.get('gold_span_reach'))} | {fmt_rate(by_k.get('unique_gold_span_reach'))} | "
                    f"{fmt_rate(by_k.get('candidate_absent_rate'))} | {fmt_rate(by_k.get('file_right_span_wrong_rate'))} |"
                )
        lines.append("")

        lines.append("## Unique span reach@5\n")
        lines.append("| Strategy | GoldSpanReach | UniqueGoldSpanReach | UniqueShare |")
        lines.append("|---|---:|---:|---:|")
        for strategy in REACH_STRATEGIES:
            u = report["metrics"]["unique_reach"].get(strategy, {})
            if u.get("availability") != "available":
                lines.append(f"| {strategy} | n/a | n/a | n/a |")
                continue
            share = u.get("unique_span_reach_share")
            share_str = f"{share:.4f}" if isinstance(share, (int, float)) else "n/a"
            lines.append(
                f"| {strategy} | {fmt_rate(u.get('gold_span_reach'))} | {fmt_rate(u.get('unique_gold_span_reach'))} | {share_str} |"
            )
        lines.append("")

    lines.append("## Materialization diagnostics\n")
    mat = report["metrics"]["materialization_diagnostics"]
    lines.append(f"- Overall availability: `{mat.get('materialization_availability')}`")
    overall = mat.get("overall", {})
    lines.append(
        f"- Overall: candidates_seen={overall.get('candidates_seen', 0)}, "
        f"materialized_valid={overall.get('materialized_valid', 0)}, "
        f"materialization_rate={overall.get('materialization_rate') if overall.get('materialization_rate') is not None else 'n/a'}"
    )
    lines.append(
        "- Note: Source-file materialization validation is currently not wired by default. "
        "P46 reports `source_read_unavailable` unless the ephemeral record explicitly carries a private checkout root."
    )
    lines.append("")

    lines.append("### Materialization by strategy\n")
    lines.append("| Strategy | availability | seen | valid | invalid_path | invalid_range | stale_sha | missing_file | other | rate |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for strategy in REACH_STRATEGIES:
        b = mat["by_strategy"].get(strategy, {})
        if b.get("availability") == "missing_pool":
            lines.append(f"| {strategy} | missing_pool | - | - | - | - | - | - | - | n/a |")
            continue
        rate = b.get("materialization_rate")
        rate_str = f"{rate:.4f}" if isinstance(rate, (int, float)) else "n/a"
        lines.append(
            f"| {strategy} | {b.get('availability')} | {b.get('candidates_seen', 0)} | {b.get('materialized_valid', 0)} | "
            f"{b.get('rejected_invalid_path', 0)} | {b.get('rejected_invalid_range', 0)} | "
            f"{b.get('rejected_stale_sha_content_sha_mismatch', 0)} | {b.get('rejected_missing_file', 0)} | "
            f"{b.get('rejected_other', 0)} | {rate_str} |"
        )
    lines.append("")

    lines.append("## Public bucket breakdown@5 (symbol_regex_union)\n")
    lines.append("| Bucket | tasks | pos | no_gold | GoldFileReach | GoldSpanReach | added_gold | added_false | net_1x |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for bucket, b in sorted(report["metrics"]["public_bucket_breakdowns"]["by_task_bucket"].items()):
        oc = b.get("outcome_cost", {})
        reach = b.get("reach_at_5", {}).get("symbol_regex_union", {})
        lines.append(
            f"| {bucket} | {b['task_count']} | {b['positive_task_count']} | {b['no_gold_task_count']} | "
            f"{fmt_rate(reach.get('gold_file_reach'))} | {fmt_rate(reach.get('gold_span_reach'))} | "
            f"{fmt_int(oc.get('added_gold_span'))} | {fmt_int(oc.get('added_false_span'))} | {fmt_int(oc.get('net_span_value_1x'))} |"
        )
    lines.append("")

    if report.get("subtype_breakdown_availability") == "available":
        lines.append("## P33-B subtype combination breakdown@5 (symbol_regex_union)\n")
        lines.append(
            "| Combination | tasks | pos | no_gold | GoldFileReach | GoldSpanReach | added_gold | added_false | net_1x |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for combo, b in sorted(report["metrics"]["subtype_breakdowns"]["by_subtype_combination"].items()):
            oc = b.get("outcome_cost", {})
            reach = b.get("reach_at_5", {}).get("symbol_regex_union", {})
            lines.append(
                f"| {combo} | {b['task_count']} | {b['positive_task_count']} | {b['no_gold_task_count']} | "
                f"{fmt_rate(reach.get('gold_file_reach'))} | {fmt_rate(reach.get('gold_span_reach'))} | "
                f"{fmt_int(oc.get('added_gold_span'))} | {fmt_int(oc.get('added_false_span'))} | {fmt_int(oc.get('net_span_value_1x'))} |"
            )
        lines.append("")

    lines.append("## Policy route snapshots\n")
    for policy in ("bucket_routed_v0", "admission_v3_h4b"):
        block = report["metrics"]["policy_routes"].get(policy, {})
        avail = block.get("availability")
        lines.append(f"### {policy} (`{avail}`)\n")
        lines.append(
            f"- selected_task_count={block.get('selected_task_count', 0)}, "
            f"selected_with_outcome={block.get('selected_with_outcome_count', 0)}, "
            f"selected_missing_outcome={block.get('selected_missing_outcome_count', 0)}, "
            f"outcome_fallback_rate={block.get('outcome_fallback_rate') if block.get('outcome_fallback_rate') is not None else 'n/a'}, "
            f"selected_with_cost={block.get('selected_with_cost_count', 0)}, "
            f"selected_missing_cost={block.get('selected_missing_cost_count', 0)}, "
            f"cost_fallback_rate={block.get('cost_fallback_rate') if block.get('cost_fallback_rate') is not None else 'n/a'}"
        )
        if avail in {"available", "partial_missing_cost_fields", "partial_fallback"}:
            lines.append("| Action | availability | selected | cost_present | cost_missing | added_gold | added_false | false/gold | net_1x |")
            lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
            for action, info in sorted(block.get("action_span_cost", {}).items()):
                fpg = info.get("false_per_gold")
                fpg_str = f"{fpg:.4f}" if isinstance(fpg, (int, float)) and not math.isinf(fpg) else "n/a"
                lines.append(
                    f"| {action} | {info.get('availability')} | {info['task_count']} | "
                    f"{info.get('cost_present_count')} | {info.get('cost_missing_count')} | "
                    f"{fmt_int(info.get('added_gold_span'))} | {fmt_int(info.get('added_false_span'))} | "
                    f"{fpg_str} | {fmt_int(info.get('net_span_value_1x'))} |"
                )
        else:
            lines.append("Policy route unavailable; no fake zeros reported.")
        lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")

    lines.append("## Safety notes\n")
    lines.append("- No remote model calls were made during P46 evaluation.")
    lines.append("- This report contains only aggregate counts/rates by strategy, public bucket, risk tag, and subtype axis.")
    lines.append("- No task IDs, candidate IDs, paths, spans, gold spans, private labels, route features, snippets, prompts, responses, or provider keys are stored.")
    lines.append(
        "- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, "
        "`candidate_not_fact=true`, `remote_calls_by_p46=0`, `score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P46 Candidate Reach × Cost / Materialization Gate")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
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
            reason = "Aggregate summary lacks per-task ephemeral records required for P46 reach × cost analysis."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        if rec.get("_p25_input_empty_marker"):
            status = "insufficient_task_detail"
            reason = "Input artifact did not contain per-task ephemeral records."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        if rec.get("_p25_unsupported_schema_marker"):
            status = "insufficient_task_detail"
            reason = "P46 requires p25-policy-records-ephemeral-v1 input schema."
            insufficient_paths.append(rec.get("path", "unknown"))
            continue
        task_records.append(rec)

    if not task_records and status == "ok":
        status = "insufficient_task_detail"
        reason = "No per-task records found."

    normalized_tasks = [nt for nt in (normalize_task(raw) for raw in task_records) if nt]

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P46 normalization."

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

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P46 report written to {args.out}")
    print(f"P46 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
