#!/usr/bin/env python3
"""P59 Contrastive Pack Coverage & Counterfactual Study v0.

P59 is a deterministic, no-live-LLM, no-provider, aggregate-only diagnostic
that rebuilds P49 contrastive candidate packs in memory and measures whether
the frozen packs contain the prerequisite contrastive information a later LLM
role would need, BEFORE any LLM spend.  It is a pre-spend prerequisite
diagnostic, NOT a quality evaluator, NOT admission, NOT Evidence, and NOT a
default/promotion gate.

RUN phase is gold-free: only candidate metadata and deterministic pack rules are
used.  SCORE phase loads private labels only after packs are frozen and is
explicitly flagged `not_used_for_pack_construction=true`.

Hard constraints:
* No LLM calls; `llm_calls_by_p59=0`.
* No remote calls; `remote_calls_by_p59=0`.
* No provider config reads; `provider_config_read_by_p59=false`.
* No prompt construction; `prompt_construction_by_p59=false`.
* No source reads; `source_reads_attempted_by_p59=false`.
* No EvidenceCore semantics change.
* No default/promotion: `promotion_ready=false`, `default_should_change=false`,
  `evidencecore_semantics_changed=false`.
* Candidates are not facts; packs are not evidence; coverage is not quality.
* Public outputs are aggregate-only: no task IDs, candidate IDs, paths, spans,
  gold spans, private labels, snippets, prompts, responses, route features, or
  provider keys.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))
import p49_contrastive_candidate_pack_scaffold as p49
import p46_candidate_reach_cost_map as p46
import p25_bucket_policy as p25

SCHEMA_VERSION = "p59-contrastive-pack-coverage-counterfactual-v0"
GENERATED_BY = "p59_contrastive_pack_coverage_counterfactual"
STAGE = "P59 Contrastive Pack Coverage & Counterfactual Study v0"

METADATA_HARD_DISTRACTOR_PROXY_VERSION = p49.METADATA_HARD_DISTRACTOR_PROXY_VERSION
MIN_SPAN_NARROW_GOLD_PRESENT_RATE = 0.5
MIN_FILTER_HARD_DISTRACTOR_PRESENT_RATE = 0.5

DEFAULT_OUT = Path("artifacts/p59_contrastive_pack_coverage_counterfactual/p59_contrastive_pack_coverage_counterfactual_report.json")
DEFAULT_DOC = Path("docs/en/p59-contrastive-pack-coverage-counterfactual.md")

PACK_STRATEGIES = p49.PACK_STRATEGIES
SLOT_NAMES = p49.SLOT_NAMES

ALLOWED_STATUS = {
    "blocked_safety",
    "insufficient_records",
    "diagnostic_coverage_partial",
    "diagnostic_coverage_available",
    "self_test_only",
}

# Exact keys that must never appear in the public artifact.  Safety flags and
# intentionally public metric names are allowlisted in P59_SAFETY_FLAG_KEYS.
FORBIDDEN_PUBLIC_KEYS = {
    "task_id",
    "repo_id",
    "candidate_id",
    "path",
    "start_line",
    "end_line",
    "content_sha",
    "digest",
    "hash",
    "gold",
    "gold_spans",
    "label",
    "labels",
    "private_label",
    "private_labels",
    "query",
    "raw_query",
    "prompt",
    "response",
    "snippet",
    "source_text",
    "raw_source",
    "route_features",
    "provider",
    "provider_key",
    "base_url",
    "api_key",
    "api_token",
    "endpoint",
    "candidate_pool",
    "raw_candidates",
    "candidates",
    "pack_items",
    "per_task",
    "tasks",
    "records",
    "decision_records",
    "per_task_results",
    "evidence",
    "Evidence",
}

P59_SAFETY_FLAG_KEYS = {
    # top-level schema and safety flags
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
    "pack_not_evidence",
    "coverage_not_quality_evidence",
    "counterfactual_not_quality_claim",
    "remote_calls_by_p59",
    "llm_calls_by_p59",
    "provider_config_read_by_p59",
    "prompt_construction_by_p59",
    "source_reads_attempted_by_p59",
    "aggregate_only_public_artifact",
    "score_phase_only_metrics",
    "run_phase_gold_free",
    "gold_used_for_pack_construction",
    "labels_loaded_after_pack_build",
    "hard_distractor_labels_not_used_for_pack_construction",
    "metadata_hard_distractor_proxy_definition_version",
    "raw_prompts_stored",
    "raw_query_stored",
    "raw_responses_stored",
    "raw_snippets_stored",
    "raw_snippets_committed",
    "raw_snippets_sent_to_provider",
    "raw_text_stored",
    "raw_source_stored",
    "raw_paths_in_artifact",
    "raw_line_ranges_in_artifact",
    "raw_digests_in_artifact",
    "provider_keys_in_artifact",
    "gold_spans_in_artifact",
    "private_labels_committed",
    "elapsed_ms",
    # summary and availability keys
    "task_count",
    "positive_task_count",
    "no_gold_task_count",
    "candidate_pool_availability",
    "gold_span_availability",
    "reach_metrics_available",
    "p31_h1_handoff_detected",
    "p31_h1_handoff_detected_count",
    "p33b_handoff_detected",
    "p33b_handoff_detected_count",
    "pack_strategies",
    "slot_names",
    "metrics",
    "conclusion",
    "validation",
    "upstream_carry_forward",
    # metric block names
    "by_strategy",
    "denominators",
    "contrastive_information_coverage",
    "provenance_completeness",
    "path_kind_flag_coverage",
    "subtype_shape_metadata_coverage",
    "source_backed_shape_metadata_coverage",
    "score_phase_gold_coverage",
    "hard_distractor_repair_coverage",
    "score_phase_hard_distractor_coverage",
    "actionability_thresholds",
    "counterfactual_actionability",
    "breakdowns",
    "by_public_bucket",
    "by_public_risk_tag",
    "by_pack_strategy",
    # denominator and count keys
    "task_count",
    "positive_task_count",
    "no_gold_task_count",
    "candidate_pool_task_denominator",
    "pack_build_denominator",
    "pack_nonempty_count",
    "pack_nonempty_rate",
    "positive_with_gold_span_denominator",
    "no_gold_pack_denominator",
    "selected_candidate_denominator",
    "span_narrow_counterfactual_denominator",
    "filter_counterfactual_denominator",
    # contrastive coverage keys
    "same_file_competitor_pack_count",
    "same_file_competitor_pack_rate",
    "hard_distractor_pack_count",
    "hard_distractor_pack_rate",
    "source_test_competitor_pack_count",
    "source_test_competitor_pack_rate",
    "docs_source_competitor_pack_count",
    "docs_source_competitor_pack_rate",
    "cross_file_competitor_pack_count",
    "cross_file_competitor_pack_rate",
    "path_kind_diverse_pack_count",
    "path_kind_diverse_pack_rate",
    "channel_diverse_pack_count",
    "channel_diverse_pack_rate",
    "subtype_diverse_pack_count",
    "subtype_diverse_pack_rate",
    # provenance keys
    "candidate_has_score_count",
    "candidate_has_score_rate",
    "candidate_has_channels_count",
    "candidate_has_channels_rate",
    "candidate_has_rank_count",
    "candidate_has_rank_rate",
    "candidate_has_span_count",
    "candidate_has_span_rate",
    "candidate_has_path_kind_count",
    "candidate_has_path_kind_rate",
    "public_provenance_complete_count",
    "public_provenance_complete_rate",
    # path-kind flag keys
    "candidate_has_source_flag_rate",
    "candidate_has_test_flag_rate",
    "candidate_has_doc_flag_rate",
    "candidate_has_config_flag_rate",
    "pack_has_source_candidate_rate",
    "pack_has_test_candidate_rate",
    "pack_has_doc_candidate_rate",
    "pack_has_config_candidate_rate",
    # subtype shape keys
    "candidate_has_subtype_rate",
    "candidate_has_source_class_rate",
    "candidate_has_agreement_class_rate",
    "candidate_has_rrf_backing_rate",
    "candidate_has_span_width_bin_rate",
    "candidate_has_rank_bin_rate",
    "candidate_has_candidate_count_bin_rate",
    "subtype_shape_complete_rate",
    # source-backed shape keys
    "source_backed_shape_metadata_availability",
    "candidate_has_source_backed_shape_metadata_rate",
    "pack_has_source_backed_shape_metadata_rate",
    "source_backed_shape_not_verified_by_p59",
    # score-phase gold coverage keys
    "not_used_for_pack_construction",
    "gold_candidate_coverage_count",
    "gold_candidate_coverage_rate",
    "gold_file_coverage_count",
    "gold_file_coverage_rate",
    "gold_span_overlap_coverage_count",
    "gold_span_overlap_coverage_rate",
    "gold_candidate_in_primary_anchor_count",
    "gold_candidate_in_primary_anchor_rate",
    "gold_candidate_in_contrast_slot_count",
    "gold_candidate_in_contrast_slot_rate",
    "file_right_span_wrong_count",
    "file_right_span_wrong_rate",
    # counterfactual keys
    "precondition_only_not_quality_claim",
    "span_narrow_requires_gold_candidate",
    "span_narrow_gold_candidate_present_count",
    "span_narrow_gold_candidate_present_rate",
    "span_narrow_impossible_without_gold_candidate_count",
    "span_narrow_impossible_without_gold_candidate_rate",
    "filter_requires_hard_distractor",
    "filter_hard_distractor_present_count",
    "filter_hard_distractor_present_rate",
    "filter_rejection_contrast_missing_count",
    "filter_rejection_contrast_missing_rate",
    "joint_span_narrow_and_filter_preconditions_count",
    "joint_span_narrow_and_filter_preconditions_rate",
    "llm_spend_actionability_bucket",
    # hard-distractor repair coverage keys
    "metadata_hard_distractor_proxy_definition_version",
    "proxy_pack_count",
    "proxy_pack_rate",
    "available_count",
    "slot_fill_count",
    "slot_fill_rate",
    "overflow_blocked_count",
    # score-phase hard-distractor coverage keys
    "coverage_availability",
    "denominator",
    "hard_distractor_present_count",
    "hard_distractor_present_rate",
    "hard_distractor_missing_count",
    "hard_distractor_missing_rate",
    # actionability thresholds
    "min_span_narrow_gold_present_rate",
    "min_filter_hard_distractor_present_rate",
    "span_narrow_threshold_denominator",
    "filter_threshold_denominator",
    # breakdown helper keys
    "pack_with_hard_distractor_count",
    "pack_with_hard_distractor_rate",
    "source_backed_shape_metadata_present_candidate_count",
    "source_backed_shape_metadata_present_pack_count",
    "positive_with_gold_span_and_pack_count",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value == int(value):
        return int(value)
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


def _percentile(values: list[int | float], p: float) -> float | None:
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


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    """Recursively reject exact keys that must not appear in public artifacts."""
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P59_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _scan_values_for_leaks(obj: Any, prefix: str = "") -> list[str]:
    """Reject absolute paths, URLs, and API-key-like strings in values."""
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            violations.extend(_scan_values_for_leaks(value, prefix + str(key) + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_scan_values_for_leaks(value, prefix + str(idx) + "."))
    elif isinstance(obj, str):
        text = obj.strip()
        if len(text) > 1 and (text.startswith("/") or text.startswith("\\")):
            violations.append(prefix + " looks like an absolute path")
        elif "://" in text:
            violations.append(prefix + " looks like a URL")
        elif re.search(r"sk-[A-Za-z0-9_-]{20,}", text):
            violations.append(prefix + " looks like an API key")
    return violations


def _read_optional_report(path: Path | None, report_name: str) -> dict[str, Any]:
    """Read optional upstream report and return only aggregate enum/status metadata."""
    source_key = f"{report_name}_report_source"
    status_key = f"{report_name}_status"
    if path is None or not path.exists():
        return {
            source_key: "not_provided",
            status_key: "not_provided",
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            source_key: "invalid_json",
            status_key: "invalid_json",
        }
    result: dict[str, Any] = {source_key: "provided_report"}
    status = data.get("status")
    if not isinstance(status, str):
        status = "not_provided"
    result[status_key] = status
    return result


_GOLD_LABEL_KEYS = {
    "label",
    "labels",
    "p31_score_gold",
    "gold",
    "gold_spans",
    "has_gold",
    "score_group",
}


def _build_construction_tasks(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the RUN-phase gold-free construction view directly from raw records.

    Any raw key that carries gold/label information is stripped from a shallow
    copy before normalization, so the construction view cannot contain
    gold spans, labels, or has_gold state.  Only candidate metadata and public
    task-bucket tags are retained.
    """
    construction_tasks: list[dict[str, Any]] = []
    for raw in raw_records:
        stripped = {k: v for k, v in raw.items() if k not in _GOLD_LABEL_KEYS}
        nt = p46.normalize_task(stripped)
        if nt:
            construction_tasks.append(nt)
    return construction_tasks


def _extract_labels(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract gold/label information from the original raw records.

    This is the SCORE-phase label load.  It must be called only after packs are
    frozen from the gold-free construction view.
    """
    labels: list[dict[str, Any]] = []
    for raw in raw_records:
        t = p46.normalize_task(raw)
        if t is None:
            labels.append({"has_gold": False, "has_gold_spans": False, "label": {}})
        else:
            labels.append({
                "has_gold": bool(t.get("has_gold")),
                "has_gold_spans": bool(t.get("has_gold_spans")),
                "label": t.get("label", {}),
            })
    return labels


def _build_frozen_packs(
    construction_tasks: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """RUN phase: build and freeze all per-strategy packs from the gold-free view.

    No label/gold data is used here.  Each frozen pack stores the selected
    candidate metadata plus the public task-bucket tags needed for breakdowns.
    """
    frozen: dict[str, list[dict[str, Any]]] = {}
    for strategy in PACK_STRATEGIES:
        packs: list[dict[str, Any]] = []
        for task in construction_tasks:
            candidates = p49._normalize_candidates(task)
            pack = p49._build_pack(candidates, strategy, task)
            packs.append({
                "selected": pack["selected"],
                "slots_filled": pack["slots_filled"],
                "has_candidates": bool(candidates),
                "bucket": task.get("task_bucket", "unknown"),
                "risk_tags": task.get("task_risk_tags") or ["other"],
                "task": task,
            })
        frozen[strategy] = packs
    return frozen


def _pack_has_same_file_competitor(selected: list[dict[str, Any]]) -> bool:
    if not selected:
        return False
    anchor = selected[0]
    return any(c["_path"] == anchor["_path"] and c["_id"] != anchor["_id"] for c in selected)


def _pack_has_source_test(selected: list[dict[str, Any]]) -> bool:
    kinds = {c.get("path_kind") for c in selected}
    return "source" in kinds and "test" in kinds


def _pack_has_doc_source(selected: list[dict[str, Any]]) -> bool:
    kinds = {c.get("path_kind") for c in selected}
    return "doc" in kinds and "source" in kinds


def _pack_has_hard_distractor(selected: list[dict[str, Any]], task: dict[str, Any] | None = None) -> bool:
    if not selected:
        return False
    anchor = selected[0]
    return any(
        c["_id"] != anchor["_id"] and p49._is_metadata_hard_distractor_proxy_v1(c, anchor, task)
        for c in selected
    )


def _pack_has_cross_file(selected: list[dict[str, Any]]) -> bool:
    if not selected:
        return False
    anchor = selected[0]
    return any(c["_path"] != anchor["_path"] for c in selected)


def _pack_has_path_kind_diversity(selected: list[dict[str, Any]]) -> bool:
    kinds = {c.get("path_kind") for c in selected}
    return len(kinds) > 1


def _pack_has_channel_diversity(selected: list[dict[str, Any]]) -> bool:
    all_channels: set[str] = set()
    for c in selected:
        all_channels.update(c.get("channels", []))
    return len(all_channels) > 1


def _pack_has_subtype_diversity(selected: list[dict[str, Any]]) -> bool:
    classes = {str(c.get("subtype", {}).get("source_class")) for c in selected if c.get("subtype", {}).get("source_class")}
    return len(classes) > 1


def _subtype_shape_complete(cand: dict[str, Any]) -> bool:
    st = cand.get("subtype")
    if not isinstance(st, dict):
        return False
    checks = [
        st.get("source_class") in p46.SUBTYPE_SOURCE_CLASSES,
        st.get("agreement_class") in p46.SUBTYPE_AGREEMENT_CLASSES,
        st.get("rrf_backing") is not None,
        st.get("span_width_bin") in p46.SUBTYPE_SPAN_WIDTH_BINS,
        st.get("rank_bin") in p46.SUBTYPE_RANK_BINS,
        st.get("candidate_count_bin") in p46.SUBTYPE_COUNT_BINS,
    ]
    return all(checks)


def _candidate_has_subtype(cand: dict[str, Any]) -> bool:
    return bool(cand.get("subtype"))


def _candidate_has_source_class(cand: dict[str, Any]) -> bool:
    st = cand.get("subtype")
    return isinstance(st, dict) and st.get("source_class") in p46.SUBTYPE_SOURCE_CLASSES


def _candidate_has_agreement_class(cand: dict[str, Any]) -> bool:
    st = cand.get("subtype")
    return isinstance(st, dict) and st.get("agreement_class") in p46.SUBTYPE_AGREEMENT_CLASSES


def _candidate_has_rrf_backing(cand: dict[str, Any]) -> bool:
    st = cand.get("subtype")
    return isinstance(st, dict) and st.get("rrf_backing") is not None


def _candidate_has_span_width_bin(cand: dict[str, Any]) -> bool:
    st = cand.get("subtype")
    return isinstance(st, dict) and st.get("span_width_bin") in p46.SUBTYPE_SPAN_WIDTH_BINS


def _candidate_has_rank_bin(cand: dict[str, Any]) -> bool:
    st = cand.get("subtype")
    return isinstance(st, dict) and st.get("rank_bin") in p46.SUBTYPE_RANK_BINS


def _candidate_has_candidate_count_bin(cand: dict[str, Any]) -> bool:
    st = cand.get("subtype")
    return isinstance(st, dict) and st.get("candidate_count_bin") in p46.SUBTYPE_COUNT_BINS


def _compute_strategy_metrics(
    packs: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    strategy: str,
) -> dict[str, Any]:
    """Compute aggregate metrics for a single pack strategy from frozen packs.

    `packs` must be the frozen gold-free pack selections built by the RUN phase.
    `labels` must be the SCORE-phase labels extracted only after pack construction.
    """
    if len(packs) != len(labels):
        raise ValueError("packs and labels must be aligned")

    # SCORE-phase denominators: derived from the separated labels only.
    task_count = len(labels)
    positive_task_count = sum(1 for lab in labels if lab.get("has_gold"))
    no_gold_task_count = task_count - positive_task_count
    candidate_pool_task_denominator = sum(1 for p in packs if p["has_candidates"])
    pack_build_denominator = candidate_pool_task_denominator
    pack_nonempty_count = sum(1 for p in packs if p["has_candidates"] and p["selected"])
    pack_nonempty_rate = _rate(pack_nonempty_count, pack_build_denominator)
    positive_with_gold_span_denominator = sum(
        1 for lab, p in zip(labels, packs)
        if lab.get("has_gold") and lab.get("has_gold_spans") and p["has_candidates"]
    )
    no_gold_pack_denominator = sum(
        1 for lab, p in zip(labels, packs) if not lab.get("has_gold") and p["has_candidates"]
    )

    denominators = {
        "task_count": task_count,
        "positive_task_count": positive_task_count,
        "no_gold_task_count": no_gold_task_count,
        "candidate_pool_task_denominator": candidate_pool_task_denominator,
        "pack_build_denominator": pack_build_denominator,
        "pack_nonempty_count": pack_nonempty_count,
        "pack_nonempty_rate": pack_nonempty_rate,
        "positive_with_gold_span_denominator": positive_with_gold_span_denominator,
        "no_gold_pack_denominator": no_gold_pack_denominator,
    }

    # Contrastive information coverage (gold-free).
    same_file = 0
    hard_dist = 0
    source_test = 0
    docs_source = 0
    cross_file = 0
    path_kind_diverse = 0
    channel_diverse = 0
    subtype_diverse = 0

    # Provenance completeness.
    selected_candidate_count = 0
    cand_score = 0
    cand_channels = 0
    cand_rank = 0
    cand_span = 0
    cand_path_kind = 0
    cand_provenance_complete = 0

    # Path-kind flag coverage.
    cand_source = 0
    cand_test = 0
    cand_doc = 0
    cand_config = 0
    pack_source = 0
    pack_test = 0
    pack_doc = 0
    pack_config = 0

    # Subtype shape metadata.
    cand_subtype = 0
    cand_source_class = 0
    cand_agreement_class = 0
    cand_rrf_backing = 0
    cand_span_width = 0
    cand_rank_bin = 0
    cand_count_bin = 0
    cand_subtype_complete = 0

    # Source-backed shape metadata.
    source_backed_complete_candidates = 0
    source_backed_complete_packs = 0

    # SCORE-phase gold coverage.
    gold_candidate_coverage = 0
    gold_file_coverage = 0
    gold_span_overlap = 0
    gold_in_anchor = 0
    gold_in_contrast = 0
    file_right_span_wrong = 0

    # Counterfactual actionability.
    span_narrow_denom = 0
    span_narrow_gold_present = 0
    filter_denom = 0
    filter_hard_present = 0
    joint_preconditions = 0

    # Hard-distractor repair coverage (RUN phase, metadata-only proxy).
    proxy_hard_distractor_pack_count = 0
    proxy_hard_distractor_available_count = 0
    hard_distractor_slot_fill_count = 0
    hard_distractor_overflow_blocked_count = 0

    # SCORE-phase hard-distractor coverage (label-backed denominator only).
    score_phase_hard_distractor_denom = 0
    score_phase_hard_distractor_present = 0

    # Breakdown helpers.
    by_bucket: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "task_count": 0,
            "positive_task_count": 0,
            "no_gold_task_count": 0,
            "pack_nonempty_count": 0,
            "pack_with_hard_distractor_count": 0,
        }
    )
    by_risk_tag: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "task_count": 0,
            "positive_task_count": 0,
            "no_gold_task_count": 0,
            "pack_nonempty_count": 0,
            "pack_with_hard_distractor_count": 0,
        }
    )

    for pack, lab in zip(packs, labels):
        if not pack["has_candidates"]:
            continue
        selected = pack["selected"]
        nonempty = bool(selected)
        bucket = pack.get("bucket", "unknown")
        risk_tags = pack.get("risk_tags") or ["other"]
        task = pack.get("task")

        bb = by_bucket[bucket]
        bb["task_count"] += 1
        if lab.get("has_gold"):
            bb["positive_task_count"] += 1
        else:
            bb["no_gold_task_count"] += 1
        if nonempty:
            bb["pack_nonempty_count"] += 1
        if _pack_has_hard_distractor(selected, task):
            bb["pack_with_hard_distractor_count"] += 1

        for tag in risk_tags:
            bt = by_risk_tag[tag]
            bt["task_count"] += 1
            if lab.get("has_gold"):
                bt["positive_task_count"] += 1
            else:
                bt["no_gold_task_count"] += 1
            if nonempty:
                bt["pack_nonempty_count"] += 1
            if _pack_has_hard_distractor(selected, task):
                bt["pack_with_hard_distractor_count"] += 1

        if nonempty:
            if _pack_has_same_file_competitor(selected):
                same_file += 1
            if _pack_has_hard_distractor(selected, task):
                hard_dist += 1
            if _pack_has_source_test(selected):
                source_test += 1
            if _pack_has_doc_source(selected):
                docs_source += 1
            if _pack_has_cross_file(selected):
                cross_file += 1
            if _pack_has_path_kind_diversity(selected):
                path_kind_diverse += 1
            if _pack_has_channel_diversity(selected):
                channel_diverse += 1
            if _pack_has_subtype_diversity(selected):
                subtype_diverse += 1

            # Hard-distractor repair coverage (RUN phase, metadata-only proxy).
            candidates = p49._normalize_candidates(task) if task else []
            anchor = selected[0]
            proxy_available = sum(
                1
                for c in candidates
                if c["_id"] != anchor["_id"] and p49._is_metadata_hard_distractor_proxy_v1(c, anchor, task)
            ) if candidates else 0
            if proxy_available > 0:
                proxy_hard_distractor_available_count += 1
            if any(
                p49._is_metadata_hard_distractor_proxy_v1(c, anchor, task)
                for c in selected
                if c["_id"] != anchor["_id"]
            ):
                proxy_hard_distractor_pack_count += 1
            if "hard_distractor" in pack.get("slots_filled", set()):
                hard_distractor_slot_fill_count += 1
            elif proxy_available > 0 and len(selected) >= p49.MAX_CANDIDATES_PER_PACK:
                hard_distractor_overflow_blocked_count += 1

            # Path-kind pack flags.
            kinds = {c.get("path_kind") for c in selected}
            if "source" in kinds:
                pack_source += 1
            if "test" in kinds:
                pack_test += 1
            if "doc" in kinds:
                pack_doc += 1
            if "config" in kinds:
                pack_config += 1

            if any(_subtype_shape_complete(c) for c in selected):
                source_backed_complete_packs += 1

        for c in selected:
            selected_candidate_count += 1
            if c.get("score") is not None:
                cand_score += 1
            if c.get("channels"):
                cand_channels += 1
            if c.get("rank") is not None:
                cand_rank += 1
            if c.get("span_width") is not None:
                cand_span += 1
            if c.get("path_kind") is not None and c.get("path_kind") != "unknown":
                cand_path_kind += 1
            if (
                c.get("score") is not None
                and c.get("channels")
                and c.get("rank") is not None
                and c.get("span_width") is not None
                and c.get("path_kind") is not None
                and c.get("path_kind") != "unknown"
            ):
                cand_provenance_complete += 1

            pk = c.get("path_kind")
            if pk == "source":
                cand_source += 1
            elif pk == "test":
                cand_test += 1
            elif pk == "doc":
                cand_doc += 1
            elif pk == "config":
                cand_config += 1

            if _candidate_has_subtype(c):
                cand_subtype += 1
            if _candidate_has_source_class(c):
                cand_source_class += 1
            if _candidate_has_agreement_class(c):
                cand_agreement_class += 1
            if _candidate_has_rrf_backing(c):
                cand_rrf_backing += 1
            if _candidate_has_span_width_bin(c):
                cand_span_width += 1
            if _candidate_has_rank_bin(c):
                cand_rank_bin += 1
            if _candidate_has_candidate_count_bin(c):
                cand_count_bin += 1
            if _subtype_shape_complete(c):
                cand_subtype_complete += 1
                source_backed_complete_candidates += 1

        # SCORE-phase diagnostics (labels used only after pack construction).
        if lab.get("has_gold") and lab.get("has_gold_spans"):
            label = lab.get("label", {})
            gold_file_hit = any(p49._file_in_gold(c, label) for c in selected)
            gold_span_hit = any(p49._span_overlaps_gold(c, label) for c in selected)
            if gold_span_hit:
                gold_candidate_coverage += 1
                gold_span_overlap += 1
            if gold_file_hit:
                gold_file_coverage += 1
            if selected:
                anchor = selected[0]
                if p49._span_overlaps_gold(anchor, label):
                    gold_in_anchor += 1
                if any(p49._span_overlaps_gold(c, label) for c in selected[1:]):
                    gold_in_contrast += 1
            if gold_file_hit and not gold_span_hit:
                file_right_span_wrong += 1

            span_narrow_denom += 1
            if gold_span_hit:
                span_narrow_gold_present += 1
            if gold_span_hit and _pack_has_hard_distractor(selected, task):
                joint_preconditions += 1

            # SCORE-phase hard-distractor coverage (label-backed denominator only).
            score_phase_hard_distractor_denom += 1
            if _pack_has_hard_distractor(selected, task):
                score_phase_hard_distractor_present += 1

        # Filter counterfactual denominator is tasks with a built pack.
        filter_denom += 1
        if _pack_has_hard_distractor(selected, task):
            filter_hard_present += 1


    # Source-backed shape metadata availability.
    if selected_candidate_count == 0:
        source_backed_availability = "unavailable_aggregate_only"
    elif cand_subtype_complete == selected_candidate_count:
        source_backed_availability = "available"
    elif cand_subtype_complete > 0:
        source_backed_availability = "partial"
    else:
        source_backed_availability = "unavailable_not_in_input"

    contrastive = {
        "same_file_competitor_pack_count": same_file,
        "same_file_competitor_pack_rate": _rate(same_file, pack_nonempty_count),
        "hard_distractor_pack_count": hard_dist,
        "hard_distractor_pack_rate": _rate(hard_dist, pack_nonempty_count),
        "source_test_competitor_pack_count": source_test,
        "source_test_competitor_pack_rate": _rate(source_test, pack_nonempty_count),
        "docs_source_competitor_pack_count": docs_source,
        "docs_source_competitor_pack_rate": _rate(docs_source, pack_nonempty_count),
        "cross_file_competitor_pack_count": cross_file,
        "cross_file_competitor_pack_rate": _rate(cross_file, pack_nonempty_count),
        "path_kind_diverse_pack_count": path_kind_diverse,
        "path_kind_diverse_pack_rate": _rate(path_kind_diverse, pack_nonempty_count),
        "channel_diverse_pack_count": channel_diverse,
        "channel_diverse_pack_rate": _rate(channel_diverse, pack_nonempty_count),
        "subtype_diverse_pack_count": subtype_diverse,
        "subtype_diverse_pack_rate": _rate(subtype_diverse, pack_nonempty_count),
    }

    provenance = {
        "selected_candidate_denominator": selected_candidate_count,
        "candidate_has_score_count": cand_score,
        "candidate_has_score_rate": _rate(cand_score, selected_candidate_count),
        "candidate_has_channels_count": cand_channels,
        "candidate_has_channels_rate": _rate(cand_channels, selected_candidate_count),
        "candidate_has_rank_count": cand_rank,
        "candidate_has_rank_rate": _rate(cand_rank, selected_candidate_count),
        "candidate_has_span_count": cand_span,
        "candidate_has_span_rate": _rate(cand_span, selected_candidate_count),
        "candidate_has_path_kind_count": cand_path_kind,
        "candidate_has_path_kind_rate": _rate(cand_path_kind, selected_candidate_count),
        "public_provenance_complete_count": cand_provenance_complete,
        "public_provenance_complete_rate": _rate(cand_provenance_complete, selected_candidate_count),
    }

    path_kind_flags = {
        "candidate_has_source_flag_rate": _rate(cand_source, selected_candidate_count),
        "candidate_has_test_flag_rate": _rate(cand_test, selected_candidate_count),
        "candidate_has_doc_flag_rate": _rate(cand_doc, selected_candidate_count),
        "candidate_has_config_flag_rate": _rate(cand_config, selected_candidate_count),
        "pack_has_source_candidate_rate": _rate(pack_source, pack_nonempty_count),
        "pack_has_test_candidate_rate": _rate(pack_test, pack_nonempty_count),
        "pack_has_doc_candidate_rate": _rate(pack_doc, pack_nonempty_count),
        "pack_has_config_candidate_rate": _rate(pack_config, pack_nonempty_count),
    }

    subtype_shape = {
        "candidate_has_subtype_rate": _rate(cand_subtype, selected_candidate_count),
        "candidate_has_source_class_rate": _rate(cand_source_class, selected_candidate_count),
        "candidate_has_agreement_class_rate": _rate(cand_agreement_class, selected_candidate_count),
        "candidate_has_rrf_backing_rate": _rate(cand_rrf_backing, selected_candidate_count),
        "candidate_has_span_width_bin_rate": _rate(cand_span_width, selected_candidate_count),
        "candidate_has_rank_bin_rate": _rate(cand_rank_bin, selected_candidate_count),
        "candidate_has_candidate_count_bin_rate": _rate(cand_count_bin, selected_candidate_count),
        "subtype_shape_complete_rate": _rate(cand_subtype_complete, selected_candidate_count),
    }

    source_backed_shape = {
        "source_backed_shape_metadata_availability": source_backed_availability,
        "candidate_has_source_backed_shape_metadata_rate": _rate(source_backed_complete_candidates, selected_candidate_count),
        "pack_has_source_backed_shape_metadata_rate": _rate(source_backed_complete_packs, pack_nonempty_count),
        "source_backed_shape_not_verified_by_p59": True,
    }

    score_gold = {
        "not_used_for_pack_construction": True,
        "gold_candidate_coverage_count": gold_candidate_coverage,
        "gold_candidate_coverage_rate": _rate(gold_candidate_coverage, positive_with_gold_span_denominator),
        "gold_file_coverage_count": gold_file_coverage,
        "gold_file_coverage_rate": _rate(gold_file_coverage, positive_with_gold_span_denominator),
        "gold_span_overlap_coverage_count": gold_span_overlap,
        "gold_span_overlap_coverage_rate": _rate(gold_span_overlap, positive_with_gold_span_denominator),
        "gold_candidate_in_primary_anchor_count": gold_in_anchor,
        "gold_candidate_in_primary_anchor_rate": _rate(gold_in_anchor, positive_with_gold_span_denominator),
        "gold_candidate_in_contrast_slot_count": gold_in_contrast,
        "gold_candidate_in_contrast_slot_rate": _rate(gold_in_contrast, positive_with_gold_span_denominator),
        "file_right_span_wrong_count": file_right_span_wrong,
        "file_right_span_wrong_rate": _rate(file_right_span_wrong, positive_with_gold_span_denominator),
    }

    hard_distractor_repair_coverage = {
        "metadata_hard_distractor_proxy_definition_version": METADATA_HARD_DISTRACTOR_PROXY_VERSION,
        "proxy_pack_count": proxy_hard_distractor_pack_count,
        "proxy_pack_rate": _rate(proxy_hard_distractor_pack_count, pack_nonempty_count),
        "available_count": proxy_hard_distractor_available_count,
        "slot_fill_count": hard_distractor_slot_fill_count,
        "slot_fill_rate": _rate(hard_distractor_slot_fill_count, pack_nonempty_count),
        "overflow_blocked_count": hard_distractor_overflow_blocked_count,
    }

    score_phase_hard_distractor_coverage = {
        "not_used_for_pack_construction": True,
        "coverage_availability": "available" if score_phase_hard_distractor_denom > 0 else "unavailable",
        "denominator": score_phase_hard_distractor_denom,
        "hard_distractor_present_count": score_phase_hard_distractor_present,
        "hard_distractor_present_rate": _rate(score_phase_hard_distractor_present, score_phase_hard_distractor_denom),
        "hard_distractor_missing_count": score_phase_hard_distractor_denom - score_phase_hard_distractor_present,
        "hard_distractor_missing_rate": _rate(
            score_phase_hard_distractor_denom - score_phase_hard_distractor_present, score_phase_hard_distractor_denom
        ),
    }

    actionability_thresholds = {
        "min_span_narrow_gold_present_rate": MIN_SPAN_NARROW_GOLD_PRESENT_RATE,
        "min_filter_hard_distractor_present_rate": MIN_FILTER_HARD_DISTRACTOR_PRESENT_RATE,
        "span_narrow_threshold_denominator": span_narrow_denom,
        "filter_threshold_denominator": filter_denom,
    }

    span_narrow_impossible = span_narrow_denom - span_narrow_gold_present
    filter_missing = filter_denom - filter_hard_present

    if span_narrow_denom > 0 and filter_denom > 0:
        gold_present_rate = span_narrow_gold_present / span_narrow_denom
        hard_present_rate = filter_hard_present / filter_denom
        if gold_present_rate >= MIN_SPAN_NARROW_GOLD_PRESENT_RATE and hard_present_rate >= MIN_FILTER_HARD_DISTRACTOR_PRESENT_RATE:
            actionability_bucket = "actionable"
        elif gold_present_rate < MIN_SPAN_NARROW_GOLD_PRESENT_RATE and hard_present_rate < MIN_FILTER_HARD_DISTRACTOR_PRESENT_RATE:
            actionability_bucket = "blocked_missing_both"
        elif gold_present_rate < MIN_SPAN_NARROW_GOLD_PRESENT_RATE:
            actionability_bucket = "blocked_missing_gold_candidate"
        elif hard_present_rate < MIN_FILTER_HARD_DISTRACTOR_PRESENT_RATE:
            actionability_bucket = "blocked_missing_hard_distractor"
        else:
            actionability_bucket = "partial"
    else:
        actionability_bucket = "insufficient_denominator"

    counterfactual = {
        "precondition_only_not_quality_claim": True,
        "span_narrow_requires_gold_candidate": True,
        "span_narrow_counterfactual_denominator": span_narrow_denom,
        "span_narrow_gold_candidate_present_count": span_narrow_gold_present,
        "span_narrow_gold_candidate_present_rate": _rate(span_narrow_gold_present, span_narrow_denom),
        "span_narrow_impossible_without_gold_candidate_count": span_narrow_impossible,
        "span_narrow_impossible_without_gold_candidate_rate": _rate(span_narrow_impossible, span_narrow_denom),
        "filter_requires_hard_distractor": True,
        "filter_counterfactual_denominator": filter_denom,
        "filter_hard_distractor_present_count": filter_hard_present,
        "filter_hard_distractor_present_rate": _rate(filter_hard_present, filter_denom),
        "filter_rejection_contrast_missing_count": filter_missing,
        "filter_rejection_contrast_missing_rate": _rate(filter_missing, filter_denom),
        "joint_span_narrow_and_filter_preconditions_count": joint_preconditions,
        "joint_span_narrow_and_filter_preconditions_rate": _rate(joint_preconditions, span_narrow_denom),
        "llm_spend_actionability_bucket": actionability_bucket,
    }

    # Breakdowns.
    for bucket, counts in by_bucket.items():
        counts["pack_nonempty_rate"] = _rate(counts["pack_nonempty_count"], counts["task_count"])
        counts["pack_with_hard_distractor_rate"] = _rate(
            counts["pack_with_hard_distractor_count"], counts["pack_nonempty_count"]
        )
    for tag, counts in by_risk_tag.items():
        counts["pack_nonempty_rate"] = _rate(counts["pack_nonempty_count"], counts["task_count"])
        counts["pack_with_hard_distractor_rate"] = _rate(
            counts["pack_with_hard_distractor_count"], counts["pack_nonempty_count"]
        )

    by_pack_strategy: dict[str, Any] = {
        strategy: {
            "task_count": denominators["task_count"],
            "positive_task_count": denominators["positive_task_count"],
            "no_gold_task_count": denominators["no_gold_task_count"],
            "pack_nonempty_count": denominators["pack_nonempty_count"],
            "pack_with_hard_distractor_count": hard_dist,
            "pack_with_hard_distractor_rate": _rate(hard_dist, pack_nonempty_count),
        }
    }

    return {
        "denominators": _nullify_missing(denominators),
        "contrastive_information_coverage": _nullify_missing(contrastive),
        "provenance_completeness": _nullify_missing(provenance),
        "path_kind_flag_coverage": _nullify_missing(path_kind_flags),
        "subtype_shape_metadata_coverage": _nullify_missing(subtype_shape),
        "source_backed_shape_metadata_coverage": _nullify_missing(source_backed_shape),
        "score_phase_gold_coverage": _nullify_missing(score_gold),
        "hard_distractor_repair_coverage": _nullify_missing(hard_distractor_repair_coverage),
        "score_phase_hard_distractor_coverage": _nullify_missing(score_phase_hard_distractor_coverage),
        "actionability_thresholds": _nullify_missing(actionability_thresholds),
        "counterfactual_actionability": _nullify_missing(counterfactual),
        "breakdowns": {
            "by_public_bucket": dict(by_bucket),
            "by_public_risk_tag": dict(by_risk_tag),
            "by_pack_strategy": by_pack_strategy,
        },
    }


def _nullify_missing(obj: dict[str, Any]) -> dict[str, Any]:
    """Preserve explicit nulls instead of fabricated zeros for missing rates."""
    out: dict[str, Any] = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            out[k] = _nullify_missing(v)
        else:
            out[k] = v if v is not None else None
    return out


def validate_public_report(report: dict[str, Any]) -> list[str]:
    """Validate schema, safety flags, and recursive forbidden-key scan."""
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("generated_by") != GENERATED_BY:
        errors.append("generated_by mismatch")
    if report.get("stage") != STAGE:
        errors.append("stage mismatch")
    if report.get("status") not in ALLOWED_STATUS:
        errors.append(f"status must be one of {ALLOWED_STATUS}")

    # Numeric safety counters.
    for flag in ("remote_calls_by_p59", "llm_calls_by_p59"):
        if report.get(flag) != 0:
            errors.append(f"{flag} must be 0")

    # Boolean safety flags.
    expected_true = {
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "pack_not_evidence": True,
        "coverage_not_quality_evidence": True,
        "counterfactual_not_quality_claim": True,
        "not_quality_evidence": True,
        "remote_calls_by_p59": 0,
        "llm_calls_by_p59": 0,
        "provider_config_read_by_p59": False,
        "prompt_construction_by_p59": False,
        "source_reads_attempted_by_p59": False,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "run_phase_gold_free": True,
        "gold_used_for_pack_construction": False,
        "labels_loaded_after_pack_build": True,
        "hard_distractor_labels_not_used_for_pack_construction": True,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_text_stored": False,
        "raw_source_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
    }
    for flag, expected in expected_true.items():
        if report.get(flag) is not expected:
            errors.append(f"{flag} must be {expected}")

    if report.get("metadata_hard_distractor_proxy_definition_version") != METADATA_HARD_DISTRACTOR_PROXY_VERSION:
        errors.append("metadata_hard_distractor_proxy_definition_version missing or wrong")

    # No top-level per-task rows.
    for forbidden in ("tasks", "records", "per_task_results", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    # Forbidden key and value scans.
    errors.extend(_reject_forbidden_keys(report))
    errors.extend(_scan_values_for_leaks(report))

    # Rate and numerator/denominator invariants.
    def _walk(prefix: str, obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                _walk(f"{prefix}.{k}", v)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                _walk(f"{prefix}[{idx}]", item)
        elif isinstance(obj, (int, float)):
            if obj is not None and not (0.0 <= float(obj) <= 1.0 + 1e-9):
                errors.append(f"{prefix} rate out of range: {obj}")

    # Check known rate keys by walking metric blocks and checking keys ending in _rate.
    def _check_rates(obj: Any, prefix: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_prefix = f"{prefix}.{k}"
                if k.endswith("_rate") and isinstance(v, (int, float)):
                    if not (0.0 <= float(v) <= 1.0 + 1e-9):
                        errors.append(f"{new_prefix} out of range: {v}")
                _check_rates(v, new_prefix)
        elif isinstance(obj, list):
            for idx, v in enumerate(obj):
                _check_rates(v, f"{prefix}[{idx}]")

    _check_rates(report.get("metrics"), "metrics")

    # Counterfactual arithmetic invariants.
    for strategy, block in (report.get("metrics", {}).get("by_strategy", {}) or {}).items():
        cf = block.get("counterfactual_actionability", {})
        denom = cf.get("span_narrow_counterfactual_denominator")
        present = cf.get("span_narrow_gold_candidate_present_count")
        impossible = cf.get("span_narrow_impossible_without_gold_candidate_count")
        if isinstance(denom, int) and isinstance(present, int) and isinstance(impossible, int):
            if present + impossible != denom:
                errors.append(f"{strategy} span_narrow counts do not sum to denominator")
        fdenom = cf.get("filter_counterfactual_denominator")
        f_present = cf.get("filter_hard_distractor_present_count")
        f_missing = cf.get("filter_rejection_contrast_missing_count")
        if isinstance(fdenom, int) and isinstance(f_present, int) and isinstance(f_missing, int):
            if f_present + f_missing != fdenom:
                errors.append(f"{strategy} filter counts do not sum to denominator")

        # Hard-distractor repair coverage count conservation.
        hd = block.get("hard_distractor_repair_coverage", {})
        avail = hd.get("available_count")
        proxy_pack = hd.get("proxy_pack_count")
        slot_fill = hd.get("slot_fill_count")
        overflow = hd.get("overflow_blocked_count")
        if isinstance(avail, int) and isinstance(proxy_pack, int) and isinstance(slot_fill, int) and isinstance(overflow, int):
            if proxy_pack > avail:
                errors.append(f"{strategy} proxy_pack_count cannot exceed available_count")
            if slot_fill > proxy_pack:
                errors.append(f"{strategy} slot_fill_count cannot exceed proxy_pack_count")
            if overflow > avail:
                errors.append(f"{strategy} overflow_blocked_count cannot exceed available_count")
        if hd.get("metadata_hard_distractor_proxy_definition_version") != METADATA_HARD_DISTRACTOR_PROXY_VERSION:
            errors.append(f"{strategy} missing metadata_hard_distractor_proxy_definition_version")

        # Score-phase hard-distractor coverage count conservation.
        sc = block.get("score_phase_hard_distractor_coverage", {})
        sc_denom = sc.get("denominator")
        sc_present = sc.get("hard_distractor_present_count")
        sc_missing = sc.get("hard_distractor_missing_count")
        if isinstance(sc_denom, int) and isinstance(sc_present, int) and isinstance(sc_missing, int):
            if sc_present + sc_missing != sc_denom:
                errors.append(f"{strategy} score_phase_hard_distractor counts do not sum to denominator")
        if sc.get("not_used_for_pack_construction") is not True:
            errors.append(f"{strategy} score_phase_hard_distractor_coverage must be not_used_for_pack_construction")

        # Actionability thresholds and denominator recording.
        thresholds = block.get("actionability_thresholds", {})
        if thresholds.get("min_span_narrow_gold_present_rate") != MIN_SPAN_NARROW_GOLD_PRESENT_RATE:
            errors.append(f"{strategy} min_span_narrow_gold_present_rate mismatch")
        if thresholds.get("min_filter_hard_distractor_present_rate") != MIN_FILTER_HARD_DISTRACTOR_PRESENT_RATE:
            errors.append(f"{strategy} min_filter_hard_distractor_present_rate mismatch")
        if thresholds.get("span_narrow_threshold_denominator") != denom:
            errors.append(f"{strategy} span_narrow_threshold_denominator must equal counterfactual denominator")
        if thresholds.get("filter_threshold_denominator") != fdenom:
            errors.append(f"{strategy} filter_threshold_denominator must equal counterfactual denominator")

        # If actionable, threshold/denominator consistency and definition version present.
        bucket = cf.get("llm_spend_actionability_bucket")
        if bucket == "actionable":
            if thresholds.get("span_narrow_threshold_denominator", 0) <= 0:
                errors.append(f"{strategy} actionable but span_narrow_threshold_denominator is not positive")
            if thresholds.get("filter_threshold_denominator", 0) <= 0:
                errors.append(f"{strategy} actionable but filter_threshold_denominator is not positive")
            if hd.get("metadata_hard_distractor_proxy_definition_version") != METADATA_HARD_DISTRACTOR_PROXY_VERSION:
                errors.append(f"{strategy} actionable but metadata_hard_distractor_proxy_definition_version missing")

    return errors


def _determine_status(
    construction_tasks: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    self_test: bool,
    validation_errors: list[str] | None,
) -> tuple[str, str | None]:
    if validation_errors:
        return "blocked_safety", "P59 public report validation failed safety/contract checks."
    if self_test:
        return "self_test_only", "Self-test-only deterministic pack coverage diagnostic; not quality evidence."
    if not labels:
        return "insufficient_records", "No per-task ephemeral records were available for P59 pack coverage."
    if not any(t.get("has_candidate_pool") for t in construction_tasks):
        return "insufficient_records", "Ephemeral records did not contain candidate pools required for pack rebuild."
    return "diagnostic_coverage_available", "Aggregate diagnostic coverage available from rebuilt P49 packs."



def build_report(
    construction_tasks: list[dict[str, Any]],
    task_records: list[dict[str, Any]],
    *,
    self_test: bool,
    elapsed_ms: int,
    input_source_count: int,
    insufficient_input_source_count: int,
    optional_reports: dict[str, Any],
) -> dict[str, Any]:
    if len(construction_tasks) != len(task_records):
        raise ValueError("construction_tasks and task_records must be aligned")

    # RUN phase: build and freeze all packs from the gold-free construction view.
    # No gold/label data is loaded or used here.
    frozen_packs = _build_frozen_packs(construction_tasks)

    # SCORE phase: only after packs are frozen, load labels from the original
    # raw records.
    labels = _extract_labels(task_records)

    if len(construction_tasks) != len(labels):
        raise ValueError("construction_tasks and labels must be aligned after extraction")

    candidate_pool_availability = (
        "available" if construction_tasks and all(t.get("has_candidate_pool") for t in construction_tasks)
        else "partial" if construction_tasks and any(t.get("has_candidate_pool") for t in construction_tasks)
        else "missing_candidate_pool"
    )
    gold_span_availability = (
        "available" if labels and all(lab.get("has_gold_spans") for lab in labels if lab.get("has_gold"))
        else "partial" if labels and any(lab.get("has_gold_spans") for lab in labels if lab.get("has_gold"))
        else "missing_gold_spans"
    )
    reach_metrics_available = (
        candidate_pool_availability != "missing_candidate_pool"
        and gold_span_availability != "missing_gold_spans"
    )
    p31_h1_handoff_detected = bool(
        construction_tasks and any(
            t.get("has_candidate_pool") and lab.get("has_gold_spans")
            for t, lab in zip(construction_tasks, labels)
        )
    )
    p31_h1_handoff_detected_count = sum(
        1 for t, lab in zip(construction_tasks, labels)
        if t.get("has_candidate_pool") and lab.get("has_gold_spans")
    )
    p33b_handoff_detected = bool(construction_tasks and any(t.get("subtypes") for t in construction_tasks))
    p33b_handoff_detected_count = sum(1 for t in construction_tasks if t.get("subtypes"))

    by_strategy: dict[str, Any] = {}
    for strategy in PACK_STRATEGIES:
        by_strategy[strategy] = _compute_strategy_metrics(frozen_packs[strategy], labels, strategy)

    conclusion_lines: list[str] = []
    status, reason = _determine_status(construction_tasks, labels, self_test, None)
    if status not in {"diagnostic_coverage_available", "self_test_only"}:
        conclusion_lines.append(
            "P59 Contrastive Pack Coverage & Counterfactual Study v0 is ready; real per-task ephemeral P25 records are required."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(
                f"Self-test-only deterministic pack coverage diagnostic rebuilt P49 packs for {len(labels)} synthetic tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P59 rebuilt candidate packs for {len(labels)} real ephemeral P25 records and measured aggregate contrastive coverage."
            )
        conclusion_lines.append(
            "Pack construction was gold-free and used only candidate metadata; labels were loaded only after packs were frozen."
        )
        conclusion_lines.append(
            "P59 does not call an LLM, does not create evidence, does not admit candidate spans, "
            "does not read source files, does not validate content_sha, and does not change defaults."
        )
        conclusion_lines.append(
            "P59 reports only aggregate preconditions for later LLM spend; it does not claim that packs are high-quality or that an LLM will succeed."
        )
        for strategy in PACK_STRATEGIES:
            denom = by_strategy[strategy]["denominators"]["pack_build_denominator"]
            nonempty = by_strategy[strategy]["denominators"]["pack_nonempty_count"]
            conclusion_lines.append(
                f"{strategy}: pack_build_denominator={denom}, pack_nonempty_count={nonempty}."
            )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": STAGE,
        "status": status,
        "status_reason": reason,
        "self_test": self_test,
        "not_quality_evidence": True,
        "real_evaluation": bool(status == "diagnostic_coverage_available" and not self_test),
        "input_sources": ["self_test"] if self_test else ["p25-policy-records-ephemeral-v1"],
        "input_source_count": input_source_count,
        "insufficient_input_source_count": insufficient_input_source_count,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "pack_not_evidence": True,
        "coverage_not_quality_evidence": True,
        "counterfactual_not_quality_claim": True,
        "remote_calls_by_p59": 0,
        "llm_calls_by_p59": 0,
        "provider_config_read_by_p59": False,
        "prompt_construction_by_p59": False,
        "source_reads_attempted_by_p59": False,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "run_phase_gold_free": True,
        "gold_used_for_pack_construction": False,
        "labels_loaded_after_pack_build": True,
        "hard_distractor_labels_not_used_for_pack_construction": True,
        "metadata_hard_distractor_proxy_definition_version": METADATA_HARD_DISTRACTOR_PROXY_VERSION,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_text_stored": False,
        "raw_source_stored": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "elapsed_ms": elapsed_ms,
        "pack_strategies": list(PACK_STRATEGIES),
        "slot_names": list(SLOT_NAMES),
        "task_count": len(labels),
        "positive_task_count": sum(1 for lab in labels if lab.get("has_gold")),
        "no_gold_task_count": sum(1 for lab in labels if not lab.get("has_gold")),
        "candidate_pool_availability": candidate_pool_availability,
        "gold_span_availability": gold_span_availability,
        "reach_metrics_available": reach_metrics_available,
        "p31_h1_handoff_detected": p31_h1_handoff_detected,
        "p31_h1_handoff_detected_count": p31_h1_handoff_detected_count,
        "p33b_handoff_detected": p33b_handoff_detected,
        "p33b_handoff_detected_count": p33b_handoff_detected_count,
        "upstream_carry_forward": optional_reports,
        "metrics": {"by_strategy": by_strategy},
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P59 public report validation failed: {errors}")
    return report


def _fmt_scalar(x: Any) -> str:
    if isinstance(x, float):
        return f"{x:.4f}"
    if isinstance(x, int):
        return str(x)
    if x is None:
        return "n/a"
    return str(x)


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [f"# {STAGE}\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Hard-distractor proxy: `{report.get('metadata_hard_distractor_proxy_definition_version')}`",
        f"- Hard-distractor labels not used for pack construction: {report.get('hard_distractor_labels_not_used_for_pack_construction')}",
        f"- Remote calls by P59: {report['remote_calls_by_p59']}",
        f"- LLM calls by P59: {report['llm_calls_by_p59']}",
        f"- Provider config read by P59: {report['provider_config_read_by_p59']}",
        f"- Prompt construction by P59: {report['prompt_construction_by_p59']}",
        f"- Source reads attempted by P59: {report['source_reads_attempted_by_p59']}",
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}",
        f"- Candidate pool availability: `{report['candidate_pool_availability']}`",
        f"- Gold span availability: `{report['gold_span_availability']}`",
        f"- Reach metrics available: {report['reach_metrics_available']}",
        "",
    ])

    if report["status"] not in {"diagnostic_coverage_available", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records.", ""])
        return "\n".join(lines)

    lines.extend([
        "## Purpose\n",
        "P59 rebuilds deterministic P49 candidate packs in memory and reports whether the frozen packs contain the prerequisite contrastive information a later LLM role would need, **before** any LLM spend. "
        "It is a pre-spend prerequisite diagnostic, not a quality evaluator, not admission, not Evidence, and not a default/promotion gate.",
        "",
        "## Methodology\n",
        "- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).",
        "- Rebuild P49 packs deterministically using candidate metadata only; no gold/labels are used during pack construction.",
        "- Measure gold-free contrastive coverage: same-file competitors, hard distractors, source/test pairs, doc/source pairs, cross-file competitors, path-kind/channel/subtype diversity.",
        "- Hard-distractor coverage uses the P49 metadata-only RUN proxy (`metadata_hard_distractor_proxy_v1`). The proxy uses candidate rank, score, path-kind, channel, subtype, RRF backing, span-width, and public task-bucket/risk tags; labels, gold, and source text are never used.",
        "- Report RUN-phase `hard_distractor_repair_coverage` (proxy-based) and SCORE-phase `score_phase_hard_distractor_coverage` (label-backed denominator, `not_used_for_pack_construction=true`).",
        "- Record `actionability_thresholds` with the minimum rates and actual denominators used by the P61-compatible `llm_spend_actionability_bucket` enum.",
        "- After packs are frozen, load labels only for the explicitly-marked SCORE-phase coverage and counterfactual diagnostics.",
        "- Output is aggregate-only: counts, rates, and coverage breakdowns by public task bucket, public risk tag, and pack strategy.",
        "",
        "## Safety notes\n",
        "- P59 does not call an LLM.",
        "- P59 does not create evidence.",
        "- P59 does not admit candidate spans.",
        "- P59 does not read source files.",
        "- P59 does not validate content_sha.",
        "- P59 does not change defaults.",
        "- P59 does not claim that packs are high-quality or that a future LLM will succeed.",
        "- Pack slots are candidate metadata only; they are not evidence, not validated, and do not represent LLM-ready quality.",
        "",
    ])

    lines.append("## Pack coverage summary\n")
    lines.append(
        "| Strategy | Denominator | Nonempty | NonemptyRate | GoldSpanCoverage | GoldFileCoverage | FileRightSpanWrong | HardDistractorRate | CrossFileRate | SameFileRate | SourceTestRate | DocSourceRate |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for strategy in PACK_STRATEGIES:
        m = report["metrics"]["by_strategy"][strategy]
        d = m["denominators"]
        g = m["score_phase_gold_coverage"]
        c = m["contrastive_information_coverage"]
        lines.append(
            f"| {strategy} | {d['pack_build_denominator']} | {d['pack_nonempty_count']} | "
            f"{_fmt_scalar(d['pack_nonempty_rate'])} | {_fmt_scalar(g['gold_span_overlap_coverage_rate'])} | "
            f"{_fmt_scalar(g['gold_file_coverage_rate'])} | {_fmt_scalar(g['file_right_span_wrong_rate'])} | "
            f"{_fmt_scalar(c['hard_distractor_pack_rate'])} | {_fmt_scalar(c['cross_file_competitor_pack_rate'])} | "
            f"{_fmt_scalar(c['same_file_competitor_pack_rate'])} | {_fmt_scalar(c['source_test_competitor_pack_rate'])} | "
            f"{_fmt_scalar(c['docs_source_competitor_pack_rate'])} |"
        )
    lines.append("")

    lines.append("## Hard-distractor repair coverage (RUN phase, metadata-only proxy)\n")
    lines.append(
        "| Strategy | ProxyPackCount | ProxyPackRate | AvailableCount | SlotFillCount | SlotFillRate | OverflowBlocked | Definition |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|")
    for strategy in PACK_STRATEGIES:
        m = report["metrics"]["by_strategy"][strategy]["hard_distractor_repair_coverage"]
        lines.append(
            f"| {strategy} | {m['proxy_pack_count']} | {_fmt_scalar(m['proxy_pack_rate'])} | "
            f"{m['available_count']} | {m['slot_fill_count']} | {_fmt_scalar(m['slot_fill_rate'])} | "
            f"{m['overflow_blocked_count']} | `{m['metadata_hard_distractor_proxy_definition_version']}` |"
        )
    lines.append("")

    lines.append("## SCORE-phase hard-distractor coverage (label-backed, not used for pack construction)\n")
    lines.append(
        "| Strategy | Availability | Denominator | PresentCount | PresentRate | MissingCount | MissingRate |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for strategy in PACK_STRATEGIES:
        m = report["metrics"]["by_strategy"][strategy]["score_phase_hard_distractor_coverage"]
        lines.append(
            f"| {strategy} | {m['coverage_availability']} | {m['denominator']} | "
            f"{m['hard_distractor_present_count']} | {_fmt_scalar(m['hard_distractor_present_rate'])} | "
            f"{m['hard_distractor_missing_count']} | {_fmt_scalar(m['hard_distractor_missing_rate'])} |"
        )
    lines.append("")

    lines.append("## Counterfactual actionability\n")
    lines.append(
        "| Strategy | SpanNarrowDenom | GoldPresent | Impossible | FilterDenom | HardPresent | MissingContrast | Joint | MinGoldRate | MinHardRate | Actionability |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for strategy in PACK_STRATEGIES:
        m = report["metrics"]["by_strategy"][strategy]["counterfactual_actionability"]
        t = report["metrics"]["by_strategy"][strategy]["actionability_thresholds"]
        lines.append(
            f"| {strategy} | {m['span_narrow_counterfactual_denominator']} | "
            f"{m['span_narrow_gold_candidate_present_count']} | {m['span_narrow_impossible_without_gold_candidate_count']} | "
            f"{m['filter_counterfactual_denominator']} | {m['filter_hard_distractor_present_count']} | "
            f"{m['filter_rejection_contrast_missing_count']} | {m['joint_span_narrow_and_filter_preconditions_count']} | "
            f"{t['min_span_narrow_gold_present_rate']} | {t['min_filter_hard_distractor_present_rate']} | "
            f"`{m['llm_spend_actionability_bucket']}` |"
        )
    lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def make_self_test_records() -> list[dict[str, Any]]:
    """Deterministic synthetic ephemeral P25-policy records for P59 self-test."""
    def pool(
        items: list[tuple[str, int, int, str, dict[str, Any] | None]],
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for i, (path, start, end, kind, extra) in enumerate(items):
            row: dict[str, Any] = {
                "rank": i + 1,
                "path": path,
                "start_line": start,
                "end_line": end,
                "candidate_id": f"cid_{i+1}",
                "score": 0.9 - i * 0.05,
                "channels": ["candidate_baseline"],
            }
            if extra:
                row.update(extra)
            out.append(row)
        return out

    def gold(path: str, start: int, end: int) -> dict[str, Any]:
        return {"has_gold": True, "gold_spans": [{"path": path, "start_line": start, "end_line": end}]}

    def subtypes(cids: list[str]) -> list[dict[str, Any]]:
        return [
            {
                "candidate_id": cid,
                "rank": 1,
                "source_class": "symbol_regex_fusion",
                "agreement_class": "span_overlap",
                "rank_bin": "top3",
                "candidate_count_bin": "small",
                "span_width_bin": "short",
                "rrf_backing": True,
            }
            for cid in cids
        ]

    tasks: list[dict[str, Any]] = []

    # 1. Pack with gold candidate + hard distractor.
    tasks.append({
        "task_id": "p59-st-001",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["high_confidence"],
        "score_group": "positive",
        "route_features": {"candidate_count": 3, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/app.py", 10, 15, "source", None),
                ("node_modules/noise.py", 1, 5, "generated_or_vendor", None),
                ("src/other.py", 20, 25, "source", None),
            ]),
        },
        "p31_score_gold": gold("src/app.py", 10, 15),
        "p33b_anchor_subtypes": subtypes(["cid_1"]),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 2. Pack lacking gold candidate.
    tasks.append({
        "task_id": "p59-st-002",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["symbol_anchor"],
        "score_group": "positive",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/app.py", 1, 5, "source", None),
                ("src/other.py", 20, 25, "source", None),
            ]),
        },
        "p31_score_gold": gold("src/app.py", 100, 105),
        "p33b_anchor_subtypes": subtypes(["cid_1"]),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 3. Pack with gold candidate but no hard distractor (strong affinity peers only).
    tasks.append({
        "task_id": "p59-st-003",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["symbol_anchor"],
        "score_group": "positive",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/app.py", 10, 15, "source", None),
                ("src/app.py", 12, 17, "source", None),
            ]),
        },
        "p31_score_gold": gold("src/app.py", 10, 15),
        "p33b_anchor_subtypes": [
            {"candidate_id": "cid_1", "rank": 1, "source_class": "symbol_regex_fusion", "agreement_class": "span_overlap", "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short", "rrf_backing": True},
            {"candidate_id": "cid_2", "rank": 2, "source_class": "symbol_regex_fusion", "agreement_class": "span_overlap", "rank_bin": "top3", "candidate_count_bin": "small", "span_width_bin": "short", "rrf_backing": True},
        ],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 4. Same-file competitor.
    tasks.append({
        "task_id": "p59-st-004",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["symbol_anchor"],
        "score_group": "positive",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/app.py", 10, 15, "source", None),
                ("src/app.py", 20, 25, "source", None),
            ]),
        },
        "p31_score_gold": gold("src/app.py", 10, 15),
        "p33b_anchor_subtypes": subtypes(["cid_1"]),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 5. Source/test competitor.
    tasks.append({
        "task_id": "p59-st-005",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["high_confidence"],
        "score_group": "positive",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/app.py", 10, 15, "source", None),
                ("tests/test_app.py", 1, 5, "test", None),
            ]),
        },
        "p31_score_gold": gold("src/app.py", 10, 15),
        "p33b_anchor_subtypes": subtypes(["cid_1"]),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 6. Docs/source competitor.
    tasks.append({
        "task_id": "p59-st-006",
        "repo_id": "py_flask",
        "task_bucket": "positive",
        "task_risk_tags": ["config"],
        "score_group": "positive",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/app.py", 10, 15, "source", None),
                ("docs/readme.md", 1, 5, "doc", None),
            ]),
        },
        "p31_score_gold": gold("src/app.py", 10, 15),
        "p33b_anchor_subtypes": subtypes(["cid_1"]),
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 7. Missing score/channel/subtype metadata.
    tasks.append({
        "task_id": "p59-st-007",
        "repo_id": "js_express",
        "task_bucket": "positive",
        "task_risk_tags": ["weak_candidates"],
        "score_group": "positive",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": [
                {"rank": 1, "path": "src/app.js", "start_line": 10, "end_line": 15, "candidate_id": "cid_1"},
                {"rank": 2, "path": "src/other.js", "start_line": 20, "end_line": 25, "candidate_id": "cid_2"},
            ],
        },
        "p31_score_gold": gold("src/app.js", 10, 15),
        "p33b_anchor_subtypes": [],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    # 8. No-gold task with hard distractor.
    tasks.append({
        "task_id": "p59-st-008",
        "repo_id": "js_express",
        "task_bucket": "negative",
        "task_risk_tags": ["negative"],
        "score_group": "no_gold",
        "route_features": {"candidate_count": 2, "candidate_support_exists": True},
        "p31_candidate_pools": {
            "candidate_baseline": pool([
                ("src/noise.js", 1, 5, "source", None),
                ("node_modules/noise.js", 1, 5, "generated_or_vendor", None),
            ]),
        },
        "p31_score_gold": {"has_gold": False, "gold_spans": []},
        "p33b_anchor_subtypes": [],
        "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
    })

    return tasks


def _assert_self_test_invariants(report: dict[str, Any]) -> None:
    """Self-test assertions: counterfactual arithmetic, hard-distractor proxy coverage, and privacy."""
    # Overall task counts.
    assert report["task_count"] >= 8, "self-test should cover at least 8 tasks"
    assert report["positive_task_count"] >= 7, "self-test should include positive tasks"
    assert report["no_gold_task_count"] >= 1, "self-test should include a no-gold task"
    assert report["metadata_hard_distractor_proxy_definition_version"] == METADATA_HARD_DISTRACTOR_PROXY_VERSION
    assert report["hard_distractor_labels_not_used_for_pack_construction"] is True

    # At least one strategy must show expected contrasts.
    by_strategy = report["metrics"]["by_strategy"]
    any_impossible = False
    any_missing_contrast = False
    for strategy in PACK_STRATEGIES:
        m = by_strategy[strategy]
        d = m["denominators"]
        assert d["pack_build_denominator"] > 0, f"{strategy}: pack_build_denominator must be positive"
        assert d["pack_nonempty_count"] > 0, f"{strategy}: pack_nonempty_count must be positive"

        cf = m["counterfactual_actionability"]
        assert (
            cf["span_narrow_gold_candidate_present_count"] + cf["span_narrow_impossible_without_gold_candidate_count"]
            == cf["span_narrow_counterfactual_denominator"]
        ), f"{strategy}: span_narrow counts must sum to denominator"
        assert (
            cf["filter_hard_distractor_present_count"] + cf["filter_rejection_contrast_missing_count"]
            == cf["filter_counterfactual_denominator"]
        ), f"{strategy}: filter counts must sum to denominator"

        if cf["span_narrow_impossible_without_gold_candidate_count"] > 0:
            any_impossible = True
        if cf["filter_rejection_contrast_missing_count"] > 0:
            any_missing_contrast = True

        # Hard-distractor repair coverage invariants.
        hd = m["hard_distractor_repair_coverage"]
        assert hd["metadata_hard_distractor_proxy_definition_version"] == METADATA_HARD_DISTRACTOR_PROXY_VERSION
        assert hd["available_count"] >= 0
        assert hd["proxy_pack_count"] <= hd["available_count"]
        assert hd["slot_fill_count"] <= hd["proxy_pack_count"]
        assert hd["overflow_blocked_count"] >= 0

        # Score-phase hard-distractor coverage invariants.
        sc = m["score_phase_hard_distractor_coverage"]
        assert sc["not_used_for_pack_construction"] is True
        if sc["denominator"] > 0:
            assert sc["hard_distractor_present_count"] + sc["hard_distractor_missing_count"] == sc["denominator"]
            assert sc["coverage_availability"] == "available"
        else:
            assert sc["coverage_availability"] == "unavailable"

        # Actionability thresholds must match the recorded threshold block.
        thresholds = m["actionability_thresholds"]
        assert thresholds["min_span_narrow_gold_present_rate"] == MIN_SPAN_NARROW_GOLD_PRESENT_RATE
        assert thresholds["min_filter_hard_distractor_present_rate"] == MIN_FILTER_HARD_DISTRACTOR_PRESENT_RATE
        assert thresholds["span_narrow_threshold_denominator"] == cf["span_narrow_counterfactual_denominator"]
        assert thresholds["filter_threshold_denominator"] == cf["filter_counterfactual_denominator"]

    # Synthetic data must exercise the regression buckets.
    assert any_impossible, "self-test must include at least one positive task whose pack lacks a gold-overlapping candidate"
    assert any_missing_contrast, "self-test must include at least one task whose pack lacks a hard distractor"

    # Coverage buckets should transition between 0 and positive values.
    c = by_strategy["anchor_contrast_pack_v0"]["contrastive_information_coverage"]
    assert c["hard_distractor_pack_count"] > 0, "self-test should include a hard distractor"
    assert c["source_test_competitor_pack_count"] > 0, "self-test should include a source/test pair"
    assert c["docs_source_competitor_pack_count"] > 0, "self-test should include a doc/source pair"
    assert c["same_file_competitor_pack_count"] > 0, "self-test should include a same-file competitor"
    assert c["cross_file_competitor_pack_count"] > 0, "self-test should include a cross-file competitor"

    # Provenance should drop for missing metadata case.
    prov = by_strategy["anchor_contrast_pack_v0"]["provenance_completeness"]
    assert prov["public_provenance_complete_rate"] is not None and prov["public_provenance_complete_rate"] < 1.0, \
        "self-test should include incomplete provenance"

    # Source-backed shape availability should be partial (some tasks have subtype metadata, one does not).
    sbs = by_strategy["anchor_contrast_pack_v0"]["source_backed_shape_metadata_coverage"]
    assert sbs["source_backed_shape_metadata_availability"] == "partial", "self-test should show partial source-backed shape metadata"

    # Privacy: no forbidden keys in public report.
    violations = _reject_forbidden_keys(report)
    assert not violations, f"self-test public report leaked forbidden keys: {violations[:5]}"


def _test_label_change_invariance() -> None:
    """Same candidate metadata with changed labels -> identical frozen packs and RUN metrics."""
    tasks = make_self_test_records()
    construction_tasks = _build_construction_tasks(tasks)
    labels_a = _extract_labels(tasks)
    # Build a second label set where all gold spans are shifted; labels do not
    # affect RUN-phase pack construction.
    labels_b = [
        {
            "has_gold": lab.get("has_gold"),
            "has_gold_spans": lab.get("has_gold_spans"),
            "label": {
                "gold_files": {"shifted_file.py"},
                "gold_spans": [{"path": "shifted_file.py", "start_line": 1, "end_line": 2}],
            },
        }
        for lab in labels_a
    ]
    frozen_a = _build_frozen_packs(construction_tasks)
    frozen_b = _build_frozen_packs(construction_tasks)
    assert frozen_a == frozen_b, "frozen packs must be identical regardless of labels"
    for strategy in PACK_STRATEGIES:
        run_metrics_a = _compute_strategy_metrics(frozen_a[strategy], labels_a, strategy)
        run_metrics_b = _compute_strategy_metrics(frozen_b[strategy], labels_b, strategy)
        # RUN metrics (hard_distractor_repair_coverage) are label-free.
        assert (
            run_metrics_a["hard_distractor_repair_coverage"] == run_metrics_b["hard_distractor_repair_coverage"]
        ), f"{strategy}: RUN hard-distractor repair metrics must not change with labels"


def _test_actionability_boundary() -> None:
    """Exercise actionable, blocked, and small-N actionability buckets."""
    def build_pack_metadata(has_gold_span: bool, has_hard_distractor: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        task: dict[str, Any] = {
            "task_id": "boundary",
            "repo_id": "test",
            "task_bucket": "positive",
            "task_risk_tags": [],
            "score_group": "positive",
            "route_features": {"candidate_count": 2, "candidate_support_exists": True},
            "p31_candidate_pools": {
                "candidate_baseline": [
                    {
                        "rank": 1,
                        "path": "src/a.py",
                        "start_line": 10,
                        "end_line": 15,
                        "candidate_id": "cid_1",
                        "score": 0.9,
                        "channels": ["candidate_baseline"],
                        "path_kind": "source",
                    },
                    {
                        "rank": 2,
                        "path": "src/b.py" if has_hard_distractor else "src/a.py",
                        "start_line": 20 if has_hard_distractor else 12,
                        "end_line": 25 if has_hard_distractor else 17,
                        "candidate_id": "cid_2",
                        "score": 0.8,
                        "channels": ["candidate_baseline"],
                        "path_kind": "test" if has_hard_distractor else "source",
                    },
                ],
            },
            "p31_score_gold": {
                "has_gold": True,
                "gold_spans": [{"path": "src/a.py", "start_line": 10, "end_line": 15}] if has_gold_span else [],
            },
            "p33b_anchor_subtypes": [],
            "p33b_anchor_subtypes_schema": "p33b-anchor-subtypes-v1",
        }
        return [task], []

    # Actionable: both gold span and hard distractor present.
    tasks, _ = build_pack_metadata(has_gold_span=True, has_hard_distractor=True)
    ct = _build_construction_tasks(tasks)
    labels = _extract_labels(tasks)
    frozen = _build_frozen_packs(ct)
    m = _compute_strategy_metrics(frozen["anchor_contrast_pack_v0"], labels, "anchor_contrast_pack_v0")
    assert m["counterfactual_actionability"]["llm_spend_actionability_bucket"] == "actionable", "expected actionable"

    # Blocked: gold span present but no hard distractor.
    tasks, _ = build_pack_metadata(has_gold_span=True, has_hard_distractor=False)
    ct = _build_construction_tasks(tasks)
    labels = _extract_labels(tasks)
    frozen = _build_frozen_packs(ct)
    m = _compute_strategy_metrics(frozen["anchor_contrast_pack_v0"], labels, "anchor_contrast_pack_v0")
    assert m["counterfactual_actionability"]["llm_spend_actionability_bucket"] == "blocked_missing_hard_distractor"

    # Insufficient denominator when no gold span is available.
    tasks, _ = build_pack_metadata(has_gold_span=False, has_hard_distractor=False)
    ct = _build_construction_tasks(tasks)
    labels = _extract_labels(tasks)
    frozen = _build_frozen_packs(ct)
    m = _compute_strategy_metrics(frozen["anchor_contrast_pack_v0"], labels, "anchor_contrast_pack_v0")
    bucket = m["counterfactual_actionability"]["llm_spend_actionability_bucket"]
    assert bucket == "insufficient_denominator" or bucket.startswith("blocked")

    # Small-N / insufficient denominator.
    ct = _build_construction_tasks([])
    labels = _extract_labels([])
    frozen = _build_frozen_packs(ct)
    m = _compute_strategy_metrics(frozen["anchor_contrast_pack_v0"], labels, "anchor_contrast_pack_v0")
    assert m["counterfactual_actionability"]["llm_spend_actionability_bucket"] == "insufficient_denominator"


def _test_privacy_negative() -> None:
    """A public report with a banned key must fail validation."""
    report = build_report(
        [], [], self_test=True, elapsed_ms=1, input_source_count=1, insufficient_input_source_count=0, optional_reports={}
    )
    report["tasks"] = [{"id": "leak"}]
    errors = validate_public_report(report)
    assert any("tasks" in e for e in errors), "validation should reject a report containing top-level 'tasks'"


def _test_count_conservation() -> None:
    """Numerators and denominators must conserve for hard-distractor repair coverage."""
    tasks = make_self_test_records()
    construction_tasks = _build_construction_tasks(tasks)
    labels = _extract_labels(tasks)
    frozen = _build_frozen_packs(construction_tasks)
    for strategy in PACK_STRATEGIES:
        m = _compute_strategy_metrics(frozen[strategy], labels, strategy)
        hd = m["hard_distractor_repair_coverage"]
        assert hd["proxy_pack_count"] <= hd["available_count"]
        assert hd["slot_fill_count"] <= hd["proxy_pack_count"]
        sc = m["score_phase_hard_distractor_coverage"]
        if sc["denominator"] > 0:
            assert sc["hard_distractor_present_count"] + sc["hard_distractor_missing_count"] == sc["denominator"]
        cf = m["counterfactual_actionability"]
        assert cf["span_narrow_gold_candidate_present_count"] + cf["span_narrow_impossible_without_gold_candidate_count"] == cf["span_narrow_counterfactual_denominator"]
        assert cf["filter_hard_distractor_present_count"] + cf["filter_rejection_contrast_missing_count"] == cf["filter_counterfactual_denominator"]


def _run_self_test_boundary_checks() -> None:
    """Run additional boundary/contract tests during self-test mode."""
    _test_label_change_invariance()
    _test_actionability_boundary()
    _test_privacy_negative()
    _test_count_conservation()


def main() -> int:
    parser = argparse.ArgumentParser(description="P59 Contrastive Pack Coverage & Counterfactual Study v0")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--p49-report", type=Path, default=None, help="Optional P49 aggregate report for status carry-forward.")
    parser.add_argument("--p52b-report", type=Path, default=None, help="Optional P52B aggregate report for status carry-forward.")
    parser.add_argument("--p52c-report", type=Path, default=None, help="Optional P52C aggregate report for status carry-forward.")
    parser.add_argument("--p48-report", type=Path, default=None, help="Optional P48 aggregate report for status carry-forward.")
    parser.add_argument("--p50-report", type=Path, default=None, help="Optional P50 aggregate report for status carry-forward.")
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

    status = "self_test_only" if args.self_test else "diagnostic_coverage_available"
    reason: str | None = None
    insufficient_count = 0
    task_records: list[dict[str, Any]] = []

    marker_reasons = {
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P59 pack coverage.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P59 requires p25-policy-records-ephemeral-v1 input schema.",
    }
    for rec in raw_records:
        marker = next((m for m in marker_reasons if rec.get(m)), None)
        if marker:
            status = "insufficient_records"
            reason = marker_reasons[marker]
            insufficient_count += 1
            continue
        task_records.append(rec)

    if not task_records and status == "diagnostic_coverage_available":
        status = "insufficient_records"
        reason = "No per-task records found."

    construction_tasks = _build_construction_tasks(task_records)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    optional_reports: dict[str, Any] = {}
    for name, path in [
        ("p49", args.p49_report),
        ("p52b", args.p52b_report),
        ("p52c", args.p52c_report),
        ("p48", args.p48_report),
        ("p50", args.p50_report),
    ]:
        optional_reports.update(_read_optional_report(path, name))

    report = build_report(
        construction_tasks,
        task_records,
        self_test=args.self_test,
        elapsed_ms=elapsed_ms,
        input_source_count=1 if args.self_test else max(1, len(args.input or [])),
        insufficient_input_source_count=insufficient_count,
        optional_reports=optional_reports,
    )

    if args.self_test:
        _assert_self_test_invariants(report)
        _run_self_test_boundary_checks()

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P59 report written to {args.out}")
    print(f"P59 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
