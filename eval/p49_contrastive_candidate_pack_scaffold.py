#!/usr/bin/env python3
"""P49 Contrastive Candidate Pack Scaffold.

P49 is a deterministic candidate-pack blueprint / pack-shape diagnostic.  It
consumes ephemeral P25-policy records (`p25-policy-records-ephemeral-v1`),
builds a small set of deterministic candidate-pack shapes from candidate metadata
only, and reports aggregate pack-shape contrast diagnostics.

Hard constraints:
* No LLM calls; `llm_calls_by_p49=0`.
* No remote calls; `remote_calls_by_p49=0`.
* No source reads; `source_reads_attempted_by_p49=false`.
* No EvidenceCore semantics change.
* No default promotion: `promotion_ready=false`, `default_should_change=false`,
  `evidencecore_semantics_changed=false`.
* Candidates are not facts; packs are not evidence.
* Public outputs are aggregate-only: no task IDs, candidate IDs, paths, spans,
  gold spans, private labels, snippets, prompts, responses, route features, or
  provider keys.
* Pack construction uses candidate metadata only.  Gold, outcomes, and costs are
  used only inside explicitly-marked SCORE-phase diagnostics after pack
  construction.
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
from typing import Any, Sequence

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))
import p25_bucket_policy as p25
import p46_candidate_reach_cost_map as p46

SCHEMA_VERSION = "p49-contrastive-candidate-pack-scaffold-v1"
GENERATED_BY = "eval/p49_contrastive_candidate_pack_scaffold.py"

METADATA_HARD_DISTRACTOR_PROXY_VERSION = "metadata_hard_distractor_proxy_v1"

DEFAULT_OUT = Path("artifacts/p49_contrastive_candidate_pack_scaffold/p49_contrastive_candidate_pack_scaffold_report.json")
DEFAULT_DOC = Path("docs/en/p49-contrastive-candidate-pack-scaffold.md")

PACK_STRATEGIES = [
    "topk_flat_pack_v0",
    "anchor_contrast_pack_v0",
    "conservative_anchor_pack_v0",
]

SLOT_NAMES = [
    "primary_anchor",
    "rrf_consensus",
    "same_file_neighbor",
    "same_file_contrast",
    "cross_file_anchor",
    "source_test_pair",
    "doc_config_pair",
    "hard_distractor",
    "rmc_trigger_candidate",
]

MAX_CANDIDATES_PER_PACK = 6
MAX_SAME_FILE_CANDIDATES = 3
MAX_HARD_DISTRACTORS = 1
LINE_BUDGET_PROXY_CAP = 120

# Exact keys that must never appear in the public artifact.
FORBIDDEN_PUBLIC_KEYS = {
    "task_id",
    "repo_id",
    "candidate_id",
    "path",
    "start_line",
    "end_line",
    "content_sha",
    "gold",
    "gold_spans",
    "label",
    "labels",
    "query",
    "prompt",
    "snippet",
    "response",
    "route_features",
    "source_text",
    "provider",
    "provider_key",
    "base_url",
    "api_key",
    "raw_candidates",
    "pack_items",
    "per_task",
    "records",
    "decision_records",
    "per_task_results",
}

# Keys that are explicitly allowed even if their names contain substrings that
# would otherwise look like forbidden keys.  This is a safety allowlist for the
# recursive key scan only.
P49_SAFETY_FLAG_KEYS = {
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
    "remote_calls_by_p49",
    "llm_calls_by_p49",
    "source_reads_attempted_by_p49",
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
    "candidate_pool_availability",
    "gold_span_availability",
    "reach_metrics_available",
    "p31_h1_handoff_detected",
    "p31_h1_handoff_detected_count",
    "p33b_handoff_detected",
    "p33b_handoff_detected_count",
    "p50_report_source",
    "p50_quality_gate_status",
    "p48_report_source",
    "p48_overlay_availability",
    "pack_strategies",
    "slot_names",
    "metrics",
    "conclusion",
    "validation",
    # metric sub-keys that are public by design
    "pack_build_denominator",
    "pack_build_rate",
    "pack_empty_rate",
    "mean_candidates_per_pack",
    "p50_candidates_per_pack",
    "p95_candidates_per_pack",
    "mean_line_budget_proxy",
    "p95_line_budget_proxy",
    "dedupe_drop_rate",
    "slot_fill_rate_by_slot",
    "slot_conflict_rate",
    "slot_conflict_availability",
    "slot_overflow_rate",
    "same_file_pair_rate",
    "cross_file_pair_rate",
    "source_test_pair_rate",
    "doc_config_pair_rate",
    "hard_distractor_rate",
    "anchor_rrf_agreement_rate",
    "symbol_regex_agreement_rate",
    "subtype_diversity_rate",
    "path_kind_diversity_rate",
    "channel_diversity_rate",
    "candidate_has_score_rate",
    "candidate_has_channels_rate",
    "candidate_has_subtype_rate",
    "candidate_has_rank_rate",
    "candidate_has_span_rate",
    "candidate_has_path_kind_rate",
    "public_provenance_complete_rate",
    "gold_file_in_pack_rate",
    "gold_span_in_pack_rate",
    "gold_span_in_primary_anchor_rate",
    "gold_span_in_contrast_slot_rate",
    "file_right_span_wrong_in_pack_rate",
    "no_gold_pack_nonempty_rate",
    "no_gold_hard_distractor_rate",
    "rmc_trigger_pack_rate",
    "not_used_for_pack_construction",
    "by_strategy",
    "by_bucket",
    "by_risk_tag",
    "breakdowns",
    "pack_build_metrics",
    "contrast_metrics",
    "provenance_completeness",
    "score_phase_diagnostics",
    "hard_distractor_repair_coverage",
    "metadata_hard_distractor_proxy_definition_version",
    "proxy_pack_count",
    "proxy_pack_rate",
    "available_count",
    "slot_fill_count",
    "slot_fill_rate",
    "overflow_blocked_count",
    "availability",
    "task_count",
    "positive_task_count",
    "no_gold_task_count",
    "pack_nonempty_count",
    "pack_with_hard_distractor_count",
    "pack_with_rmc_trigger_count",
    "gold_file_in_pack_count",
    "gold_span_in_pack_count",
    "gold_span_in_primary_anchor_count",
    "gold_span_in_contrast_slot_count",
    "file_right_span_wrong_in_pack_count",
    "no_gold_task_seen_count",
    "raw_candidate_count",
    "deduped_candidate_count",
    "dedupe_drop_count",
    "same_file_pair_count",
    "cross_file_pair_count",
    "source_test_pair_count",
    "doc_config_pair_count",
    "hard_distractor_count",
    "anchor_rrf_agreement_count",
    "symbol_regex_agreement_count",
    "subtype_diversity_count",
    "path_kind_diversity_count",
    "channel_diversity_count",
    "selected_candidate_count",
    "candidate_with_score_count",
    "candidate_with_channels_count",
    "candidate_with_subtype_count",
    "candidate_with_rank_count",
    "candidate_with_span_count",
    "candidate_with_path_kind_count",
    "public_provenance_complete_count",
    "path_kind_distribution",
    "source_class_distribution",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rate(num: int, den: int) -> float | None:
    if den <= 0:
        return None
    return round(num / den, 6)


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def _percentile(values: Sequence[int | float], p: float) -> float | None:
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


def _classify_path_kind(path: str) -> str:
    """Deterministic, aggregate-only path-kind classifier from path strings."""
    p = path.lower()
    filename = Path(p).name
    ext = Path(filename).suffix.lstrip(".")

    if "node_modules" in p or "vendor" in p or "dist" in p or "target" in p or ".git" in p or "generated" in p:
        return "generated_or_vendor"
    if "/test" in p or p.startswith("test/") or filename.startswith("test_") or "_test." in filename or filename.endswith("_test"):
        return "test"
    if ext in {"md", "rst", "txt", "markdown"} or "readme" in filename or "/docs/" in p:
        return "doc"
    if ext in {"toml", "json", "yaml", "yml", "ini", "cfg", "config"} or filename in {"pyproject.toml", "package.json", "cargo.toml", "config"}:
        return "config"
    if ext in {"py", "rs", "js", "ts", "tsx", "go", "java", "kt", "c", "cpp", "h", "hpp", "rb", "php", "swift", "scala", "cs"}:
        return "source"
    return "unknown"


def _span_width(start: int, end: int) -> int | None:
    if start <= 0 or end <= 0 or end < start:
        return None
    return end - start + 1


def _is_rmc_trigger(cand: dict[str, Any]) -> bool:
    """Geometry heuristic for an `rmc_trigger_candidate` slot.

    A candidate is considered RMC-trigger-shaped when it is not a plain source
    span or when its span is wider than a narrow linear window.  This is a
    private, deterministic heuristic used for pack-shape diagnostics only.
    """
    if cand.get("path_kind") in {"test", "config", "generated_or_vendor"}:
        return True
    sw = cand.get("span_width")
    if isinstance(sw, int) and sw > 5:
        return True
    return False


def _normalize_candidates(task: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize raw pool candidates into in-memory metadata-only records.

    The returned list is deduplicated by (path, start, end) for pack shape,
    leaving source-strategy provenance attached for diversity diagnostics.
    """
    pools = task.get("pools", {})
    if not isinstance(pools, dict):
        return []

    subtypes_by_cid: dict[str, dict[str, Any]] = {}
    for row in task.get("subtypes") or []:
        if isinstance(row, dict):
            cid = row.get("candidate_id")
            if isinstance(cid, str) and cid:
                vals = p46._sanitize_subtype_values(row)
                subtypes_by_cid[cid] = {
                    "source_class": vals["source_class"],
                    "agreement_class": vals["agreement_class"],
                    "rrf_backing": vals["rrf_backing"],
                    "span_width_bin": vals["span_width_bin"],
                    "rank_bin": vals["rank_bin"],
                    "candidate_count_bin": vals["candidate_count_bin"],
                }

    raw_count = 0
    by_key: dict[tuple[str, int, int], dict[str, Any]] = {}

    for source_strategy, items in pools.items():
        if not isinstance(items, list):
            continue
        for cand in items:
            if not isinstance(cand, dict):
                continue
            path = str(cand.get("path") or "").lower()
            if not path:
                continue
            start = _as_int(cand.get("start_line")) or 0
            end = _as_int(cand.get("end_line")) or 0
            raw_count += 1
            key = (path, start, end)

            rank = _as_int(cand.get("rank"))
            score = _as_float(cand.get("score"))
            channels = cand.get("channels")
            if isinstance(channels, str):
                channels = [channels]
            elif isinstance(channels, list):
                channels = [str(c) for c in channels]
            else:
                channels = []

            cid = str(cand.get("candidate_id") or "")
            subtype = subtypes_by_cid.get(cid) or {}

            if key in by_key:
                existing = by_key[key]
                existing["source_strategies"].add(str(source_strategy))
                existing["channels"] = list(set(existing["channels"]) | set(channels))
                if rank is not None and (existing["rank"] is None or rank < existing["rank"]):
                    existing["rank"] = rank
                    existing["score"] = score
                    existing["subtype"] = subtype if subtype else existing["subtype"]
                    existing["source_strategy"] = str(source_strategy)
                continue

            sw = _span_width(start, end)
            path_kind = _classify_path_kind(path)
            by_key[key] = {
                "_id": len(by_key),
                "rank": rank,
                "score": score,
                "channels": channels,
                "subtype": subtype,
                "source_strategy": str(source_strategy),
                "source_strategies": {str(source_strategy)},
                "span_width": sw,
                "path_kind": path_kind,
                # Private fields used only for internal same-file/spans checks.
                "_path": path,
                "_start": start,
                "_end": end,
            }

    candidates = sorted(by_key.values(), key=lambda c: (c["rank"] if c["rank"] is not None else 999, c["_id"]))
    return candidates


def _pack_line_budget_proxy(selected: list[dict[str, Any]]) -> int:
    total = 0
    for c in selected:
        sw = c.get("span_width")
        if isinstance(sw, int):
            total += sw
        else:
            total += 1
    return min(total, LINE_BUDGET_PROXY_CAP)


def _overlaps(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a["_path"] == b["_path"] and a["_end"] >= b["_start"] - 1 and a["_start"] <= b["_end"] + 1


def _build_topk_flat_pack_v0(candidates: list[dict[str, Any]], task: dict[str, Any] | None) -> dict[str, Any]:
    selected = candidates[:MAX_CANDIDATES_PER_PACK]
    return {
        "selected": selected,
        "slots_filled": set(),
        "slots_overflow": len(candidates) > MAX_CANDIDATES_PER_PACK,
        "line_budget_proxy": _pack_line_budget_proxy(selected),
        "metadata_hard_distractor_proxy_version": METADATA_HARD_DISTRACTOR_PROXY_VERSION,
    }


def _select_next(
    candidates: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    predicate: Any,
    *,
    require_not_selected: bool = True,
) -> dict[str, Any] | None:
    taken = {c["_id"] for c in selected}
    for c in candidates:
        if require_not_selected and c["_id"] in taken:
            continue
        if predicate(c):
            return c
    return None


def _build_anchor_contrast_pack_v0(candidates: list[dict[str, Any]], task: dict[str, Any] | None) -> dict[str, Any]:
    if not candidates:
        return {"selected": [], "slots_filled": set(), "slots_overflow": False, "line_budget_proxy": 0, "metadata_hard_distractor_proxy_version": METADATA_HARD_DISTRACTOR_PROXY_VERSION}
    anchor = candidates[0]
    selected = [anchor]
    slots_filled: set[str] = {"primary_anchor"}
    same_file_count = 1  # anchor counts against the same-file cap

    # RRF consensus: a top-3 RRF-backed candidate.
    c = _select_next(candidates, selected, lambda x: x.get("rank") is not None and x["rank"] <= 3 and _has_rrf_backing(x))
    if c:
        selected.append(c)
        slots_filled.add("rrf_consensus")

    # Same-file neighbor (overlapping/adjacent to anchor).
    if same_file_count < MAX_SAME_FILE_CANDIDATES:
        c = _select_next(candidates, selected, lambda x: x["_path"] == anchor["_path"] and _overlaps(x, anchor) and x["_id"] != anchor["_id"])
        if c:
            selected.append(c)
            slots_filled.add("same_file_neighbor")
            same_file_count += 1

    # Cross-file anchor.
    c = _select_next(candidates, selected, lambda x: x["_path"] != anchor["_path"])
    if c:
        selected.append(c)
        slots_filled.add("cross_file_anchor")

    # Hard distractor (limited to one) using metadata-only proxy.
    c = _select_next(
        candidates,
        selected,
        lambda x: _is_metadata_hard_distractor_proxy_v1(x, anchor, task),
    )
    hard_count = sum(
        1
        for x in selected
        if _is_metadata_hard_distractor_proxy_v1(x, anchor, task)
    )
    if c and hard_count < MAX_HARD_DISTRACTORS and len(selected) < MAX_CANDIDATES_PER_PACK:
        selected.append(c)
        slots_filled.add("hard_distractor")

    # Same-file contrast (non-overlapping).
    if same_file_count < MAX_SAME_FILE_CANDIDATES:
        c = _select_next(
            candidates,
            selected,
            lambda x: x["_path"] == anchor["_path"] and not _overlaps(x, anchor) and x["_id"] != anchor["_id"],
        )
        if c:
            selected.append(c)
            slots_filled.add("same_file_contrast")
            same_file_count += 1

    # Source/test pair augmentation.
    anchor_kind = anchor.get("path_kind")
    if anchor_kind == "source":
        c = _select_next(candidates, selected, lambda x: x.get("path_kind") == "test")
        if c and len(selected) < MAX_CANDIDATES_PER_PACK:
            selected.append(c)
            slots_filled.add("source_test_pair")
    elif anchor_kind == "test":
        c = _select_next(candidates, selected, lambda x: x.get("path_kind") == "source")
        if c and len(selected) < MAX_CANDIDATES_PER_PACK:
            selected.append(c)
            slots_filled.add("source_test_pair")

    # Doc/config pair augmentation.
    has_doc = any(x.get("path_kind") == "doc" for x in selected)
    has_config = any(x.get("path_kind") == "config" for x in selected)
    if not (has_doc and has_config):
        needed = "doc" if not has_doc else "config"
        c = _select_next(candidates, selected, lambda x: x.get("path_kind") == needed)
        if c and len(selected) < MAX_CANDIDATES_PER_PACK:
            selected.append(c)
            slots_filled.add("doc_config_pair")

    # RMC trigger candidate.
    c = _select_next(candidates, selected, _is_rmc_trigger)
    if c and len(selected) < MAX_CANDIDATES_PER_PACK:
        selected.append(c)
        slots_filled.add("rmc_trigger_candidate")

    # Fill remaining budget deterministically with metadata-diverse candidates.
    for c in candidates:
        if len(selected) >= MAX_CANDIDATES_PER_PACK:
            break
        if c["_id"] in {x["_id"] for x in selected}:
            continue
        selected.append(c)

    overflow = len(candidates) > MAX_CANDIDATES_PER_PACK
    return {
        "selected": selected,
        "slots_filled": slots_filled,
        "slots_overflow": overflow,
        "line_budget_proxy": _pack_line_budget_proxy(selected),
        "metadata_hard_distractor_proxy_version": METADATA_HARD_DISTRACTOR_PROXY_VERSION,
    }


def _build_conservative_anchor_pack_v0(candidates: list[dict[str, Any]], task: dict[str, Any] | None) -> dict[str, Any]:
    if not candidates:
        return {"selected": [], "slots_filled": set(), "slots_overflow": False, "line_budget_proxy": 0, "metadata_hard_distractor_proxy_version": METADATA_HARD_DISTRACTOR_PROXY_VERSION}
    anchor = candidates[0]
    selected = [anchor]
    slots_filled: set[str] = {"primary_anchor"}
    same_file_count = 1

    c = _select_next(candidates, selected, lambda x: x.get("rank") is not None and x["rank"] <= 3 and _has_rrf_backing(x))
    if c:
        selected.append(c)
        slots_filled.add("rrf_consensus")

    if same_file_count < MAX_SAME_FILE_CANDIDATES:
        c = _select_next(candidates, selected, lambda x: x["_path"] == anchor["_path"] and _overlaps(x, anchor) and x["_id"] != anchor["_id"])
        if c:
            selected.append(c)
            slots_filled.add("same_file_neighbor")
            same_file_count += 1

    c = _select_next(candidates, selected, lambda x: x["_path"] != anchor["_path"])
    if c:
        selected.append(c)
        slots_filled.add("cross_file_anchor")

    # Conservative anchor also adds a metadata-only hard-distractor slot when available.
    c = _select_next(
        candidates,
        selected,
        lambda x: _is_metadata_hard_distractor_proxy_v1(x, anchor, task),
    )
    hard_count = sum(
        1
        for x in selected
        if _is_metadata_hard_distractor_proxy_v1(x, anchor, task)
    )
    if c and hard_count < MAX_HARD_DISTRACTORS and len(selected) < MAX_CANDIDATES_PER_PACK:
        selected.append(c)
        slots_filled.add("hard_distractor")

    c = _select_next(candidates, selected, _is_rmc_trigger)
    if c and len(selected) < MAX_CANDIDATES_PER_PACK:
        selected.append(c)
        slots_filled.add("rmc_trigger_candidate")

    for c in candidates:
        if len(selected) >= MAX_CANDIDATES_PER_PACK:
            break
        if c["_id"] in {x["_id"] for x in selected}:
            continue
        selected.append(c)

    overflow = len(candidates) > MAX_CANDIDATES_PER_PACK
    return {
        "selected": selected,
        "slots_filled": slots_filled,
        "slots_overflow": overflow,
        "line_budget_proxy": _pack_line_budget_proxy(selected),
        "metadata_hard_distractor_proxy_version": METADATA_HARD_DISTRACTOR_PROXY_VERSION,
    }


def _has_affinity(cand: dict[str, Any], anchor: dict[str, Any]) -> bool:
    return cand.get("path_kind") == anchor.get("path_kind")


def _is_metadata_hard_distractor_proxy_v1(
    cand: dict[str, Any],
    anchor: dict[str, Any],
    task: dict[str, Any] | None,
) -> bool:
    """Metadata-only RUN proxy for a hard distractor.

    This proxy never uses labels, gold, outcomes, query/source text, or
    provider outputs.  It uses only candidate metadata and public task risk tags
    already present in the ephemeral P25/P46 normalized record:

    * rank/score closeness (a plausible wrong alternative near the top)
    * channels/provenance (disagreement with anchor channel set)
    * P33B subtype source/agreement class (different source class or disagree)
    * RRF backing (non-RRF competitor or RRF-backing mismatch)
    * path_kind contrast (source/test/doc/config, not just unknown/generated)
    * span width bin contrast (different geometry class)
    * same-file non-overlapping or cross-file competitor shape
    * public task_bucket / task_risk_tags context

    Strong affinity signals (same file+overlap, same path_kind, same source
    class, shared channels, both RRF-backed) reduce the chance that a candidate
    is a distractor.  A candidate needs at least two weak contrast signals to
    be considered a plausible hard distractor, and unknown/generated path_kind
    is only one weak signal among several, not the whole definition.
    """
    if cand.get("_id") == anchor.get("_id"):
        return False

    c_subtype = cand.get("subtype") or {}
    a_subtype = anchor.get("subtype") or {}
    c_channels = set(cand.get("channels", []))
    a_channels = set(anchor.get("channels", []))

    # Strong affinity signals (negative evidence for distractor status).
    affinity = 0
    if cand.get("_path") == anchor.get("_path") and _overlaps(cand, anchor):
        affinity += 1
    if cand.get("path_kind") == anchor.get("path_kind"):
        affinity += 1
    c_src = c_subtype.get("source_class") if isinstance(c_subtype, dict) else None
    a_src = a_subtype.get("source_class") if isinstance(a_subtype, dict) else None
    if c_src and a_src and c_src == a_src:
        affinity += 1
    if c_channels and a_channels and c_channels & a_channels:
        affinity += 1
    if _has_rrf_backing(cand) and _has_rrf_backing(anchor):
        affinity += 1

    # Too much affinity to be a plausible distractor.
    if affinity >= 3:
        return False

    signals = 0

    # Rank/score closeness: plausible wrong alternative near the top.
    c_rank = cand.get("rank")
    a_rank = anchor.get("rank")
    if isinstance(c_rank, int) and isinstance(a_rank, int):
        if abs(c_rank - a_rank) <= 2 or c_rank <= 3:
            signals += 1
    c_score = cand.get("score")
    a_score = anchor.get("score")
    if isinstance(c_score, (int, float)) and isinstance(a_score, (int, float)):
        if abs(c_score - a_score) <= 0.15:
            signals += 1

    # Path-kind contrast (source/test/doc/config, not only unknown/generated).
    if cand.get("path_kind") != anchor.get("path_kind"):
        signals += 1

    # Channel/provenance disagreement.
    if c_channels and a_channels and not (c_channels & a_channels):
        signals += 1

    # P33B subtype source/agreement disagreement.
    if c_src and a_src and c_src != a_src:
        signals += 1
    c_agr = c_subtype.get("agreement_class") if isinstance(c_subtype, dict) else None
    a_agr = a_subtype.get("agreement_class") if isinstance(a_subtype, dict) else None
    if c_agr == "disagree" or a_agr == "disagree":
        signals += 1

    # RRF backing contrast (non-RRF competitor or RRF mismatch).
    if _has_rrf_backing(cand) != _has_rrf_backing(anchor):
        signals += 1

    # Span width geometry contrast.
    c_span = c_subtype.get("span_width_bin") if isinstance(c_subtype, dict) else None
    a_span = a_subtype.get("span_width_bin") if isinstance(a_subtype, dict) else None
    if c_span and a_span and c_span != a_span:
        signals += 1

    # Same-file non-overlapping or cross-file competitor shape.
    if cand.get("_path") != anchor.get("_path"):
        signals += 1
    elif not _overlaps(cand, anchor):
        signals += 1

    # Public task risk context (aggregate-only, no task ID leakage).
    if task:
        risk_tags = {str(t).lower() for t in task.get("task_risk_tags", [])}
        if risk_tags & {"high_confidence", "config", "negative", "weak_candidates", "ambiguous"}:
            signals += 1

    # Unknown/generated path_kind is one weak signal, not the whole definition.
    if cand.get("path_kind") in {"generated_or_vendor", "unknown"}:
        signals += 1

    # Require at least two weak signals to avoid inflation by a single axis.
    return signals >= 2


def _has_rrf_backing(cand: dict[str, Any]) -> bool:
    if "rrf_primary" in cand.get("source_strategies", set()):
        return True
    st = cand.get("subtype") or {}
    rrf = st.get("rrf_backing") if isinstance(st, dict) else None
    return rrf is True or rrf == "rrf_yes"


def _has_symbol_regex_agreement(cand: dict[str, Any]) -> bool:
    ss = cand.get("source_strategies", set())
    if "symbol_primary" in ss and "regex_primary" in ss:
        return True
    st = cand.get("subtype") or {}
    return str(st.get("source_class")) == "symbol_regex_fusion"


def _build_pack(candidates: list[dict[str, Any]], strategy: str, task: dict[str, Any] | None) -> dict[str, Any]:
    if strategy == "topk_flat_pack_v0":
        return _build_topk_flat_pack_v0(candidates, task)
    if strategy == "anchor_contrast_pack_v0":
        return _build_anchor_contrast_pack_v0(candidates, task)
    if strategy == "conservative_anchor_pack_v0":
        return _build_conservative_anchor_pack_v0(candidates, task)
    raise ValueError(f"unknown pack strategy: {strategy}")


def _span_overlaps_gold(cand: dict[str, Any], label: dict[str, Any]) -> bool:
    for gs in label.get("gold_spans", []):
        if not isinstance(gs, dict):
            continue
        g_path = str(gs.get("path") or "").lower()
        g_start = _as_int(gs.get("start_line")) or 0
        g_end = _as_int(gs.get("end_line")) or 0
        if not g_path or g_start <= 0 or g_end < g_start:
            continue
        if cand["_path"] == g_path and cand["_end"] >= g_start and cand["_start"] <= g_end:
            return True
    return False


def _file_in_gold(cand: dict[str, Any], label: dict[str, Any]) -> bool:
    return cand["_path"] in label.get("gold_files", set())


def _compute_task_pack(task: dict[str, Any], strategy: str) -> dict[str, Any]:
    candidates = _normalize_candidates(task)
    raw_count = 0
    pools = task.get("pools", {})
    if isinstance(pools, dict):
        for items in pools.values():
            if isinstance(items, list):
                raw_count += len(items)
    pack = _build_pack(candidates, strategy, task)
    return {
        "candidates": candidates,
        "raw_candidate_count": raw_count,
        "deduped_candidate_count": len(candidates),
        "dedupe_drop_count": raw_count - len(candidates),
        "selected": pack["selected"],
        "slots_filled": pack["slots_filled"],
        "slots_overflow": pack["slots_overflow"],
        "line_budget_proxy": pack["line_budget_proxy"],
        "has_candidates": bool(candidates),
        "metadata_hard_distractor_proxy_version": pack.get("metadata_hard_distractor_proxy_version"),
    }


def _compute_strategy_metrics(
    tasks: list[dict[str, Any]],
    packs: list[dict[str, Any]],
    strategy: str,
) -> dict[str, Any]:
    denom = sum(1 for p in packs if p["has_candidates"])
    empty = sum(1 for p in packs if p["has_candidates"] and not p["selected"])
    nonempty = denom - empty

    candidate_counts: list[int] = []
    line_budgets: list[int] = []
    raw_total = 0
    deduped_total = 0
    dedupe_drops = 0

    same_file_pair_count = 0
    cross_file_pair_count = 0
    source_test_pair_count = 0
    doc_config_pair_count = 0
    hard_distractor_count = 0
    anchor_rrf_agreement_count = 0
    symbol_regex_agreement_count = 0
    subtype_diversity_count = 0
    path_kind_diversity_count = 0
    channel_diversity_count = 0

    # Hard-distractor repair coverage (metadata-only proxy, RUN phase).
    proxy_hard_distractor_pack_count = 0
    proxy_hard_distractor_available_count = 0
    hard_distractor_slot_fill_count = 0
    hard_distractor_overflow_blocked_count = 0

    selected_candidate_count = 0
    candidate_with_score_count = 0
    candidate_with_channels_count = 0
    candidate_with_subtype_count = 0
    candidate_with_rank_count = 0
    candidate_with_span_count = 0
    candidate_with_path_kind_count = 0
    public_provenance_complete_count = 0

    path_kind_dist: dict[str, int] = defaultdict(int)
    source_class_dist: dict[str, int] = defaultdict(int)

    # SCORE-phase only.
    gold_file_in_pack_count = 0
    gold_span_in_pack_count = 0
    gold_span_in_primary_anchor_count = 0
    gold_span_in_contrast_slot_count = 0
    file_right_span_wrong_in_pack_count = 0
    no_gold_task_seen_count = 0
    no_gold_pack_nonempty_count = 0
    no_gold_hard_distractor_count = 0
    pack_with_rmc_trigger_count = 0

    slot_fill_counts: dict[str, int] = {s: 0 for s in SLOT_NAMES}
    # Breakdowns.
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

    for task, pack in zip(tasks, packs):
        if not pack["has_candidates"]:
            continue
        raw_total += pack["raw_candidate_count"]
        deduped_total += pack["deduped_candidate_count"]
        dedupe_drops += pack["dedupe_drop_count"]
        selected = pack["selected"]
        n = len(selected)
        candidate_counts.append(n)
        line_budgets.append(pack["line_budget_proxy"])

        bucket = task.get("task_bucket", "unknown")
        risk_tags = task.get("task_risk_tags") or ["other"]

        bb = by_bucket[bucket]
        bb["task_count"] += 1
        if task["has_gold"]:
            bb["positive_task_count"] += 1
        else:
            bb["no_gold_task_count"] += 1
        if selected:
            bb["pack_nonempty_count"] += 1

        for tag in risk_tags:
            bt = by_risk_tag[tag]
            bt["task_count"] += 1
            if task["has_gold"]:
                bt["positive_task_count"] += 1
            else:
                bt["no_gold_task_count"] += 1
            if selected:
                bt["pack_nonempty_count"] += 1

        if not selected:
            continue

        if any(c.get("path_kind") in {"generated_or_vendor", "unknown"} for c in selected):
            hard_distractor_count += 1
            bb["pack_with_hard_distractor_count"] += 1
            for tag in risk_tags:
                by_risk_tag[tag]["pack_with_hard_distractor_count"] += 1

        if any(_is_rmc_trigger(c) for c in selected):
            pack_with_rmc_trigger_count += 1

        # Pack-shape contrast diagnostics.
        anchor = selected[0]
        other_kinds = {c.get("path_kind") for c in selected if c["_id"] != anchor["_id"]}

        # Hard-distractor repair coverage (metadata-only proxy, RUN phase).
        proxy_available = 0
        if pack.get("candidates"):
            proxy_available = sum(
                1
                for c in pack["candidates"]
                if c["_id"] != anchor["_id"] and _is_metadata_hard_distractor_proxy_v1(c, anchor, task)
            )
        if proxy_available > 0:
            proxy_hard_distractor_available_count += 1
        if any(
            _is_metadata_hard_distractor_proxy_v1(c, anchor, task)
            for c in selected
            if c["_id"] != anchor["_id"]
        ):
            proxy_hard_distractor_pack_count += 1
        if "hard_distractor" in pack["slots_filled"]:
            hard_distractor_slot_fill_count += 1
        elif proxy_available > 0 and len(selected) >= MAX_CANDIDATES_PER_PACK:
            hard_distractor_overflow_blocked_count += 1

        if any(c["_path"] == anchor["_path"] and c["_id"] != anchor["_id"] for c in selected):
            same_file_pair_count += 1
        if any(c["_path"] != anchor["_path"] for c in selected):
            cross_file_pair_count += 1
        if any(c.get("path_kind") == "source" for c in selected) and any(c.get("path_kind") == "test" for c in selected):
            source_test_pair_count += 1
        if any(c.get("path_kind") == "doc" for c in selected) and any(c.get("path_kind") == "config" for c in selected):
            doc_config_pair_count += 1

        if _has_rrf_backing(anchor):
            anchor_rrf_agreement_count += 1
        if _has_symbol_regex_agreement(anchor):
            symbol_regex_agreement_count += 1

        subtypes = {str(c.get("subtype", {}).get("source_class")) for c in selected if c.get("subtype", {}).get("source_class")}
        if len(subtypes) > 1:
            subtype_diversity_count += 1
        all_kinds = {c.get("path_kind") for c in selected}
        if len(all_kinds) > 1:
            path_kind_diversity_count += 1
        all_channels: set[str] = set()
        for c in selected:
            all_channels.update(c.get("channels", []))
        if len(all_channels) > 1:
            channel_diversity_count += 1

        # Provenance completeness.
        for c in selected:
            selected_candidate_count += 1
            path_kind_dist[c.get("path_kind")] += 1
            sc = c.get("subtype", {}).get("source_class") if isinstance(c.get("subtype"), dict) else None
            if sc not in p46.SUBTYPE_SOURCE_CLASSES:
                sc = "other"
            source_class_dist[str(sc)] += 1
            has_score = c.get("score") is not None
            has_channels = bool(c.get("channels"))
            has_subtype = bool(c.get("subtype"))
            has_rank = c.get("rank") is not None
            has_span = c.get("span_width") is not None
            has_path_kind = c.get("path_kind") is not None and c.get("path_kind") != "unknown"
            if has_score:
                candidate_with_score_count += 1
            if has_channels:
                candidate_with_channels_count += 1
            if has_subtype:
                candidate_with_subtype_count += 1
            if has_rank:
                candidate_with_rank_count += 1
            if has_span:
                candidate_with_span_count += 1
            if has_path_kind:
                candidate_with_path_kind_count += 1
            if has_score and has_channels and has_subtype and has_rank and has_span and has_path_kind:
                public_provenance_complete_count += 1

        # Slot diagnostics.
        for slot in pack["slots_filled"]:
            slot_fill_counts[slot] += 1
        # Slot-conflict detection is intentionally unavailable until a real
        # deterministic conflict rule is implemented; do not publish fake zeroes.

        # SCORE-phase diagnostics (gold-aware, not used for pack construction).
        if not task["has_gold"]:
            no_gold_task_seen_count += 1
            if selected:
                no_gold_pack_nonempty_count += 1
            if any(c.get("path_kind") in {"generated_or_vendor", "unknown"} for c in selected):
                no_gold_hard_distractor_count += 1
        elif task.get("has_gold_spans"):
            label = task.get("label", {})
            gold_file_hit = any(_file_in_gold(c, label) for c in selected)
            gold_span_hit = any(_span_overlaps_gold(c, label) for c in selected)
            if gold_file_hit:
                gold_file_in_pack_count += 1
            if gold_span_hit:
                gold_span_in_pack_count += 1
            if selected and _span_overlaps_gold(anchor, label):
                gold_span_in_primary_anchor_count += 1
            if any(_span_overlaps_gold(c, label) for c in selected[1:]):
                gold_span_in_contrast_slot_count += 1
            if gold_file_hit and not gold_span_hit:
                file_right_span_wrong_in_pack_count += 1

    pos_gold_denom = sum(1 for t, p in zip(tasks, packs) if t["has_gold"] and t.get("has_gold_spans") and p["has_candidates"])
    no_gold_denom = sum(1 for t, p in zip(tasks, packs) if not t["has_gold"] and p["has_candidates"])

    pack_build_metrics = {
        "pack_build_denominator": denom,
        "pack_build_rate": _rate(nonempty, denom),
        "pack_empty_rate": _rate(empty, denom),
        "mean_candidates_per_pack": _avg([float(x) for x in candidate_counts]) if candidate_counts else None,
        "p50_candidates_per_pack": _percentile(candidate_counts, 0.5),
        "p95_candidates_per_pack": _percentile(candidate_counts, 0.95),
        "mean_line_budget_proxy": _avg([float(x) for x in line_budgets]) if line_budgets else None,
        "p95_line_budget_proxy": _percentile(line_budgets, 0.95),
        "dedupe_drop_rate": _rate(dedupe_drops, raw_total),
        "slot_fill_rate_by_slot": {slot: _rate(slot_fill_counts[slot], denom) for slot in SLOT_NAMES},
        "slot_conflict_rate": None,
        "slot_conflict_availability": "unavailable_not_implemented",
        "slot_overflow_rate": _rate(sum(1 for p in packs if p["slots_overflow"]), denom),
    }

    contrast_metrics = {
        "same_file_pair_rate": _rate(same_file_pair_count, nonempty),
        "cross_file_pair_rate": _rate(cross_file_pair_count, nonempty),
        "source_test_pair_rate": _rate(source_test_pair_count, nonempty),
        "doc_config_pair_rate": _rate(doc_config_pair_count, nonempty),
        "hard_distractor_rate": _rate(hard_distractor_count, nonempty),
        "anchor_rrf_agreement_rate": _rate(anchor_rrf_agreement_count, nonempty),
        "symbol_regex_agreement_rate": _rate(symbol_regex_agreement_count, nonempty),
        "subtype_diversity_rate": _rate(subtype_diversity_count, nonempty),
        "path_kind_diversity_rate": _rate(path_kind_diversity_count, nonempty),
        "channel_diversity_rate": _rate(channel_diversity_count, nonempty),
    }

    provenance_completeness = {
        "candidate_has_score_rate": _rate(candidate_with_score_count, selected_candidate_count),
        "candidate_has_channels_rate": _rate(candidate_with_channels_count, selected_candidate_count),
        "candidate_has_subtype_rate": _rate(candidate_with_subtype_count, selected_candidate_count),
        "candidate_has_rank_rate": _rate(candidate_with_rank_count, selected_candidate_count),
        "candidate_has_span_rate": _rate(candidate_with_span_count, selected_candidate_count),
        "candidate_has_path_kind_rate": _rate(candidate_with_path_kind_count, selected_candidate_count),
        "public_provenance_complete_rate": _rate(public_provenance_complete_count, selected_candidate_count),
    }

    score_phase_diagnostics = {
        "not_used_for_pack_construction": True,
        "gold_file_in_pack_rate": _rate(gold_file_in_pack_count, pos_gold_denom),
        "gold_span_in_pack_rate": _rate(gold_span_in_pack_count, pos_gold_denom),
        "gold_span_in_primary_anchor_rate": _rate(gold_span_in_primary_anchor_count, pos_gold_denom),
        "gold_span_in_contrast_slot_rate": _rate(gold_span_in_contrast_slot_count, pos_gold_denom),
        "file_right_span_wrong_in_pack_rate": _rate(file_right_span_wrong_in_pack_count, pos_gold_denom),
        "no_gold_pack_nonempty_rate": _rate(no_gold_pack_nonempty_count, no_gold_denom),
        "no_gold_hard_distractor_rate": _rate(no_gold_hard_distractor_count, no_gold_denom),
        "rmc_trigger_pack_rate": _rate(pack_with_rmc_trigger_count, nonempty),
    }

    # Breakdowns are aggregate counts/rates only.
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

    hard_distractor_repair_coverage = {
        "metadata_hard_distractor_proxy_definition_version": METADATA_HARD_DISTRACTOR_PROXY_VERSION,
        "proxy_pack_count": proxy_hard_distractor_pack_count,
        "proxy_pack_rate": _rate(proxy_hard_distractor_pack_count, nonempty),
        "available_count": proxy_hard_distractor_available_count,
        "slot_fill_count": hard_distractor_slot_fill_count,
        "slot_fill_rate": _rate(hard_distractor_slot_fill_count, nonempty),
        "overflow_blocked_count": hard_distractor_overflow_blocked_count,
    }

    return {
        "pack_build_metrics": _nullify_missing(pack_build_metrics),
        "contrast_metrics": _nullify_missing(contrast_metrics),
        "provenance_completeness": _nullify_missing(provenance_completeness),
        "score_phase_diagnostics": _nullify_missing(score_phase_diagnostics),
        "hard_distractor_repair_coverage": _nullify_missing(hard_distractor_repair_coverage),
        "path_kind_distribution": dict(path_kind_dist),
        "source_class_distribution": dict(source_class_dist),
        "breakdowns": {
            "by_bucket": dict(by_bucket),
            "by_risk_tag": dict(by_risk_tag),
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


def _read_optional_report(path: Path | None, report_name: str) -> dict[str, Any]:
    """Read optional upstream report and return only aggregate enum/status metadata.

    Never publishes the original file path, only an enum source marker.
    """
    source_key = f"{report_name}_report_source"
    status_key = f"{report_name}_quality_gate_status"
    overlay_key = f"{report_name}_overlay_availability"
    if path is None or not path.exists():
        return {
            source_key: "not_provided",
            status_key: "not_provided",
            overlay_key: "not_provided",
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            source_key: "invalid_json",
            status_key: "not_provided",
            overlay_key: "not_provided",
        }
    result: dict[str, Any] = {source_key: "provided_report"}
    status = data.get("quality_gate_status", "not_provided")
    if not isinstance(status, str):
        status = "not_provided"
    result[status_key] = status
    if report_name == "p48":
        overlay = data.get("route_simulation", {}).get("p48_p25_rmc_overlay_v0", {}).get("availability")
        result[overlay_key] = overlay if isinstance(overlay, str) else "not_provided"
    else:
        result[overlay_key] = "not_provided"
    return result


def validate_public_report(report: dict[str, Any]) -> list[str]:
    """Validate schema, safety flags, and recursive forbidden-key scan."""
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p49") != 0:
        errors.append("remote_calls_by_p49 must be 0")
    if report.get("llm_calls_by_p49") != 0:
        errors.append("llm_calls_by_p49 must be 0")
    if report.get("source_reads_attempted_by_p49") is not False:
        errors.append("source_reads_attempted_by_p49 must be false")

    expected_flags = {
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "pack_not_evidence": True,
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
    }
    for flag, expected in expected_flags.items():
        if report.get(flag) is not expected:
            errors.append(f"{flag} must be {expected}")

    if report.get("metadata_hard_distractor_proxy_definition_version") != METADATA_HARD_DISTRACTOR_PROXY_VERSION:
        errors.append("metadata_hard_distractor_proxy_definition_version missing or wrong")

    if report.get("self_test") and report.get("not_quality_evidence") is not True:
        errors.append("self_test must set not_quality_evidence=true")

    for forbidden in ("tasks", "records", "per_task_results", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    errors.extend(_reject_forbidden_keys(report))
    return errors


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    """Recursively reject exact keys that must not appear in public artifacts."""
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P49_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def build_report(
    tasks: list[dict[str, Any]],
    *,
    self_test: bool,
    elapsed_ms: int,
    status: str,
    reason: str | None,
    input_source_count: int,
    insufficient_input_source_count: int,
    p50_report_path: Path | None,
    p48_report_path: Path | None,
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
    p31_h1_handoff_detected_count = sum(
        1 for t in tasks if t.get("has_candidate_pool") and t.get("has_gold_spans")
    )
    p33b_handoff_detected = bool(tasks and any(t.get("subtypes") for t in tasks))
    p33b_handoff_detected_count = sum(1 for t in tasks if t.get("subtypes"))

    p50_meta = _read_optional_report(p50_report_path, "p50")
    p48_meta = _read_optional_report(p48_report_path, "p48")

    by_strategy: dict[str, Any] = {}
    for strategy in PACK_STRATEGIES:
        packs = [_compute_task_pack(t, strategy) for t in tasks]
        by_strategy[strategy] = _compute_strategy_metrics(tasks, packs, strategy)

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P49 Contrastive Candidate Pack Scaffold is ready; real per-task ephemeral P25 records are required."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(
                f"Self-test-only scaffold built candidate packs for {len(tasks)} synthetic tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P49 built candidate-pack shape diagnostics for {len(tasks)} real ephemeral P25 records."
            )
        conclusion_lines.append(
            "Pack construction used candidate metadata only (rank, score, channels, subtype axes, path-kind). "
            "Gold and outcome costs were used only for explicitly-marked SCORE-phase diagnostics."
        )
        conclusion_lines.append(
            "P49 does not call an LLM, does not create evidence, does not admit candidate spans, "
            "does not read source files, does not validate content_sha, and does not change defaults."
        )
        conclusion_lines.append(
            "P49 does not prove P51 will improve quality."
        )
        for strategy in PACK_STRATEGIES:
            denom = by_strategy[strategy]["pack_build_metrics"]["pack_build_denominator"]
            rate = by_strategy[strategy]["pack_build_metrics"]["pack_build_rate"]
            conclusion_lines.append(
                f"{strategy}: pack_build_denominator={denom}, pack_build_rate={rate}."
            )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P49 Contrastive Candidate Pack Scaffold",
        "status": status,
        "status_reason": reason,
        "self_test": self_test,
        "not_quality_evidence": bool(self_test),
        "real_evaluation": bool(status == "ok" and not self_test),
        "input_sources": ["self_test"] if self_test else ["p25-policy-records-ephemeral-v1"],
        "input_source_count": input_source_count,
        "insufficient_input_source_count": insufficient_input_source_count,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "pack_not_evidence": True,
        "remote_calls_by_p49": 0,
        "llm_calls_by_p49": 0,
        "source_reads_attempted_by_p49": False,
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
        "pack_strategies": list(PACK_STRATEGIES),
        "slot_names": list(SLOT_NAMES),
        "task_count": len(tasks),
        "positive_task_count": sum(1 for t in tasks if t["has_gold"]),
        "no_gold_task_count": sum(1 for t in tasks if not t["has_gold"]),
        "candidate_pool_availability": candidate_pool_availability,
        "gold_span_availability": gold_span_availability,
        "reach_metrics_available": reach_metrics_available,
        "p31_h1_handoff_detected": p31_h1_handoff_detected,
        "p31_h1_handoff_detected_count": p31_h1_handoff_detected_count,
        "p33b_handoff_detected": p33b_handoff_detected,
        "p33b_handoff_detected_count": p33b_handoff_detected_count,
        "metadata_hard_distractor_proxy_definition_version": METADATA_HARD_DISTRACTOR_PROXY_VERSION,
        **p50_meta,
        **p48_meta,
        "metrics": {"by_strategy": by_strategy},
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P49 public report validation failed: {errors}")
    return report


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = ["# P49 Contrastive Candidate Pack Scaffold\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Hard-distractor proxy: `{report.get('metadata_hard_distractor_proxy_definition_version')}`",
        f"- Remote calls by P49: {report['remote_calls_by_p49']}",
        f"- LLM calls by P49: {report['llm_calls_by_p49']}",
        f"- Source reads by P49: {report['source_reads_attempted_by_p49']}",
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}",
        f"- Candidate pool availability: `{report['candidate_pool_availability']}`",
        f"- Gold span availability: `{report['gold_span_availability']}`",
        f"- Reach metrics available: {report['reach_metrics_available']}",
        f"- P50 report source: `{report.get('p50_report_source')}`",
        f"- P48 report source: `{report.get('p48_report_source')}`\n",
    ])

    if report["status"] not in {"ok", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records.", ""])
        return "\n".join(lines)

    lines.extend([
        "## Purpose\n",
        "P49 builds deterministic candidate-pack shapes from candidate metadata only and reports "
        "aggregate pack-shape diagnostics. It is a SCORE-phase-only scaffold, not a policy improvement phase.",
        "",
        "## Methodology\n",
        "- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).",
        "- Normalize raw candidate pools into metadata-only records (rank, score, channels, subtype axes, path-kind).",
        "- Deduplicate candidates by path/span/strategy-affinity privately; never publish identifiers.",
        "- Build three deterministic pack shapes per task: top-k flat, anchor-contrast, and conservative-anchor.",
        "- Pack construction uses metadata only and never gold/outcome/cost signals.",
        "- The `hard_distractor` slot is filled using a metadata-only RUN proxy (`metadata_hard_distractor_proxy_v1`). The proxy is defined over candidate rank, score, path-kind contrast, channel/provenance disagreement, P33B subtype source/agreement class, RRF backing, span-width geometry, same-file/cross-file competitor shape, and public task-bucket/risk tags. Labels, gold, and source text are never used.",
        "- After packs are built, compute SCORE-phase diagnostics using gold spans and outcome costs; these are clearly marked "
        "`not_used_for_pack_construction=true`.",
        "- Output is aggregate-only: counts, rates, and distributions by pack strategy, public task bucket, and public risk tag.",
        "",
        "## Safety notes\n",
        "- P49 does not call an LLM.",
        "- P49 does not create evidence.",
        "- P49 does not admit candidate spans.",
        "- P49 does not read source files.",
        "- P49 does not validate content_sha.",
        "- P49 does not change defaults.",
        "- P49 does not prove that future candidate-pack designs will improve quality.",
        "- Pack slots are candidate metadata only; they are not evidence, not validated, and do not represent LLM-ready quality.",
        "",
        "## Pack build summary\n",
        "| Strategy | Denominator | BuildRate | EmptyRate | MeanCands | P95Cands | MeanLines | P95Lines | DedupeDropRate | OverflowRate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for strategy in PACK_STRATEGIES:
        m = report["metrics"]["by_strategy"][strategy]["pack_build_metrics"]
        lines.append(
            f"| {strategy} | {m['pack_build_denominator']} | {_fmt_scalar(m['pack_build_rate'])} | "
            f"{_fmt_scalar(m['pack_empty_rate'])} | {_fmt_scalar(m['mean_candidates_per_pack'])} | "
            f"{_fmt_scalar(m['p95_candidates_per_pack'])} | {_fmt_scalar(m['mean_line_budget_proxy'])} | "
            f"{_fmt_scalar(m['p95_line_budget_proxy'])} | {_fmt_scalar(m['dedupe_drop_rate'])} | "
            f"{_fmt_scalar(m['slot_overflow_rate'])} |"
        )
    lines.append("")

    lines.append("## Contrast metrics\n")
    lines.append(
        "| Strategy | SameFilePair | CrossFilePair | SourceTestPair | DocConfigPair | HardDistractor | "
        "RRFAgreement | SymbolRegexAgreement | SubtypeDiversity | PathKindDiversity | ChannelDiversity |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for strategy in PACK_STRATEGIES:
        m = report["metrics"]["by_strategy"][strategy]["contrast_metrics"]
        lines.append(
            f"| {strategy} | {_fmt_scalar(m['same_file_pair_rate'])} | {_fmt_scalar(m['cross_file_pair_rate'])} | "
            f"{_fmt_scalar(m['source_test_pair_rate'])} | {_fmt_scalar(m['doc_config_pair_rate'])} | "
            f"{_fmt_scalar(m['hard_distractor_rate'])} | {_fmt_scalar(m['anchor_rrf_agreement_rate'])} | "
            f"{_fmt_scalar(m['symbol_regex_agreement_rate'])} | {_fmt_scalar(m['subtype_diversity_rate'])} | "
            f"{_fmt_scalar(m['path_kind_diversity_rate'])} | {_fmt_scalar(m['channel_diversity_rate'])} |"
        )
    lines.append("")

    lines.append("## Provenance completeness\n")
    lines.append(
        "| Strategy | Score | Channels | Subtype | Rank | Span | PathKind | Complete |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for strategy in PACK_STRATEGIES:
        m = report["metrics"]["by_strategy"][strategy]["provenance_completeness"]
        lines.append(
            f"| {strategy} | {_fmt_scalar(m['candidate_has_score_rate'])} | "
            f"{_fmt_scalar(m['candidate_has_channels_rate'])} | {_fmt_scalar(m['candidate_has_subtype_rate'])} | "
            f"{_fmt_scalar(m['candidate_has_rank_rate'])} | {_fmt_scalar(m['candidate_has_span_rate'])} | "
            f"{_fmt_scalar(m['candidate_has_path_kind_rate'])} | {_fmt_scalar(m['public_provenance_complete_rate'])} |"
        )
    lines.append("")

    lines.append("## Hard-distractor repair coverage (metadata-only proxy)\n")
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

    lines.append("## SCORE-phase diagnostics (not used for pack construction)\n")

    lines.append(
        "| Strategy | GoldFileInPack | GoldSpanInPack | GoldSpanInAnchor | GoldSpanInContrast | "
        "FileRightSpanWrong | NoGoldPackNonempty | NoGoldHardDistractor | RMCTriggerPack |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for strategy in PACK_STRATEGIES:
        m = report["metrics"]["by_strategy"][strategy]["score_phase_diagnostics"]
        lines.append(
            f"| {strategy} | {_fmt_scalar(m['gold_file_in_pack_rate'])} | "
            f"{_fmt_scalar(m['gold_span_in_pack_rate'])} | {_fmt_scalar(m['gold_span_in_primary_anchor_rate'])} | "
            f"{_fmt_scalar(m['gold_span_in_contrast_slot_rate'])} | {_fmt_scalar(m['file_right_span_wrong_in_pack_rate'])} | "
            f"{_fmt_scalar(m['no_gold_pack_nonempty_rate'])} | {_fmt_scalar(m['no_gold_hard_distractor_rate'])} | "
            f"{_fmt_scalar(m['rmc_trigger_pack_rate'])} |"
        )
    lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def _assert_self_test_invariants(report: dict[str, Any]) -> None:
    """Self-test assertions: hard-distractor proxy coverage and privacy."""
    assert report["task_count"] >= 3, "self-test should cover at least 3 tasks"
    by_strategy = report["metrics"]["by_strategy"]
    for strategy in PACK_STRATEGIES:
        m = by_strategy[strategy]
        assert m["pack_build_metrics"]["pack_build_denominator"] > 0, f"{strategy}: pack_build_denominator must be positive"
        h = m["hard_distractor_repair_coverage"]
        assert h["metadata_hard_distractor_proxy_definition_version"] == METADATA_HARD_DISTRACTOR_PROXY_VERSION, f"{strategy}: definition version mismatch"
        assert h["available_count"] >= 0, f"{strategy}: available_count must be non-negative"
        assert h["proxy_pack_count"] <= h["available_count"], f"{strategy}: proxy_pack_count cannot exceed available_count"
        assert h["slot_fill_count"] <= h["proxy_pack_count"], f"{strategy}: slot_fill_count cannot exceed proxy_pack_count"
        assert h["overflow_blocked_count"] >= 0, f"{strategy}: overflow_blocked_count must be non-negative"

    # At least one strategy must have a proxy hard-distractor available.
    assert any(
        by_strategy[s]["hard_distractor_repair_coverage"]["available_count"] > 0
        for s in PACK_STRATEGIES
    ), "self-test must include at least one task where a proxy hard-distractor is available"

    # At least one strategy must fill the hard-distractor slot.
    assert any(
        by_strategy[s]["hard_distractor_repair_coverage"]["slot_fill_count"] > 0
        for s in PACK_STRATEGIES
    ), "self-test must include at least one hard-distractor slot fill"

    # Privacy: no forbidden keys in public report.
    violations = _reject_forbidden_keys(report)
    assert not violations, f"self-test public report leaked forbidden keys: {violations[:5]}"


def _fmt_scalar(x: Any) -> str:
    return f"{x:.4f}" if isinstance(x, (int, float)) else "n/a"


def main() -> int:
    parser = argparse.ArgumentParser(description="P49 Contrastive Candidate Pack Scaffold")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--p50-report", type=Path, default=None, help="Optional P50 report for gate carry-forward.")
    parser.add_argument("--p48-report", type=Path, default=None, help="Optional P48 report for overlay carry-forward.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    if args.self_test:
        raw_records = p46.make_self_test_records()
    elif args.input:
        raw_records = p25.load_p21_inputs(list(args.input), require_ephemeral_schema=True)
    else:
        parser.error("Specify --self-test or --input PATH [PATH ...]")

    start = time.monotonic()
    status = "self_test_only" if args.self_test else "ok"
    reason: str | None = None
    insufficient_count = 0
    task_records: list[dict[str, Any]] = []

    marker_reasons = {
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P49 pack diagnostics.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P49 requires p25-policy-records-ephemeral-v1 input schema.",
    }
    for rec in raw_records:
        marker = next((m for m in marker_reasons if rec.get(m)), None)
        if marker:
            status = "insufficient_task_detail"
            reason = marker_reasons[marker]
            insufficient_count += 1
            continue
        task_records.append(rec)

    if not task_records and status == "ok":
        status = "insufficient_task_detail"
        reason = "No per-task records found."

    normalized_tasks = [nt for nt in (p46.normalize_task(raw) for raw in task_records) if nt]

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P49 normalization."

    elapsed_ms = int((time.monotonic() - start) * 1000)

    report = build_report(
        normalized_tasks,
        self_test=args.self_test,
        elapsed_ms=elapsed_ms,
        status=status,
        reason=reason,
        input_source_count=1 if args.self_test else max(1, len(args.input or [])),
        insufficient_input_source_count=insufficient_count,
        p50_report_path=args.p50_report,
        p48_report_path=args.p48_report,
    )

    if args.self_test:
        _assert_self_test_invariants(report)

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P49 report written to {args.out}")
    print(f"P49 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
