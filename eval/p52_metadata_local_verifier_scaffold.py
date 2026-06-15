#!/usr/bin/env python3
"""P52 Metadata-Only Local Verifier Scaffold.

P52 inventories metadata-verifier feature availability and risk buckets before
any source-read or LLM span-narrow phase.  It consumes the same ephemeral
P25-policy records that feed P46/P49, normalizes candidates into metadata-only
records, classifies each candidate into a metadata-risk bucket, and publishes
aggregate availability/risk diagnostics only.

Hard constraints:
* No LLM calls; `llm_calls_by_p52=0`.
* No remote calls; `remote_calls_by_p52=0`.
* No source reads; `source_reads_attempted_by_p52=false`.
* No prompt construction; `prompt_construction_by_p52=false`.
* No EvidenceCore semantics change; `evidencecore_semantics_changed=false`.
* No default promotion: `promotion_ready=false`, `default_should_change=false`.
* Candidate metadata is not evidence; `candidate_not_fact=true`.
* The local verifier is not evidence; `verifier_not_evidence=true`.
* This is a metadata verifier only; `metadata_verifier_only=true`.
* Source-text verification is unavailable; `source_text_verification_unavailable=true`.
* Local verifier score is unavailable; `local_verifier_score_available=false`.
* Public outputs are aggregate-only; `aggregate_only_public_artifact=true`.
* Gold/outcomes are used only inside explicitly-marked SCORE-phase diagnostics
  after metadata feature extraction/risk bucket assignment.
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
import p46_candidate_reach_cost_map as p46
import p49_contrastive_candidate_pack_scaffold as p49

SCHEMA_VERSION = "p52-metadata-local-verifier-scaffold-v1"
GENERATED_BY = "eval/p52_metadata_local_verifier_scaffold.py"

DEFAULT_OUT = Path("artifacts/p52_metadata_local_verifier_scaffold/p52_metadata_local_verifier_scaffold_report.json")
DEFAULT_DOC = Path("docs/en/p52-metadata-local-verifier-scaffold.md")

SPAN_TOO_WIDE = 50
SPAN_BOUNDED = 20

RISK_BUCKETS = {
    "metadata_low_risk",
    "metadata_medium_risk",
    "metadata_high_risk",
    "metadata_unavailable",
}

FORBIDDEN_PUBLIC_KEYS = set(p49.FORBIDDEN_PUBLIC_KEYS) | {
    "query_terms",
    "identifier",
    "symbol_text",
    "verifier_pass",
    "verifier_fail",
    "evidence_ready",
    "llm_ready",
    "source_valid",
    "gold",
    "gold_spans",
    "label",
    "labels",
}

P52_SAFETY_FLAG_KEYS = set(p49.P49_SAFETY_FLAG_KEYS) | {
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
    "verifier_not_evidence",
    "metadata_verifier_only",
    "remote_calls_by_p52",
    "llm_calls_by_p52",
    "source_reads_attempted_by_p52",
    "prompt_construction_by_p52",
    "source_text_verification_unavailable",
    "local_verifier_score_available",
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
    "source_required_features_availability",
    "p31_h1_handoff_detected",
    "p31_h1_handoff_detected_count",
    "p33b_handoff_detected",
    "p33b_handoff_detected_count",
    "p49_report_source",
    "p50_report_source",
    "p48_report_source",
    "p50_quality_gate_status",
    "p49_pack_not_evidence",
    "p48_overlay_availability",
    "metrics",
    "conclusion",
    "validation",
    # metric sub-keys that are public by design
    "metadata_feature_availability",
    "metadata_checkable_features",
    "source_required_verifiers",
    "query_required_verifiers",
    "metadata_gate_v0",
    "pack_level",
    "score_phase_diagnostics",
    "task_wide",
    "by_pack_strategy",
    "by_path_kind",
    "by_source_class",
    "by_agreement_class",
    "by_rrf_backing",
    "by_risk_tag",
    "by_metadata_risk_bucket",
    "outcome_correlations",
    "candidate_denominator",
    "candidate_has_path_kind_rate",
    "candidate_has_span_width_rate",
    "candidate_has_score_rate",
    "candidate_has_channels_rate",
    "candidate_has_subtype_rate",
    "candidate_has_rank_rate",
    "candidate_has_source_strategy_rate",
    "metadata_complete_rate",
    "rrf_backing_checkable_rate",
    "symbol_regex_agreement_checkable_rate",
    "path_kind_checkable_rate",
    "span_width_reasonableness_checkable_rate",
    "rmc_trigger_checkable_rate",
    "exact_identifier_in_span",
    "query_terms_in_span",
    "signature_match",
    "ast_node_kind",
    "comment_only_flag",
    "source_text_span_width_verified",
    "content_sha_verified",
    "line_range_verified_against_current_file",
    "identifier_density",
    "term_density",
    "import_only_flag",
    "test_assertion_context",
    "raw_query_terms_available",
    "query_term_match",
    "intent_identifier_match",
    "availability",
    "checkable_count",
    "checkable_rate",
    "null_count",
    "null_rate",
    "value",
    "risk_bucket_counts",
    "risk_bucket_rates",
    "pack_denominator",
    "pack_with_low_risk_anchor_count",
    "pack_with_low_risk_anchor_rate",
    "pack_with_high_risk_distractor_count",
    "pack_with_high_risk_distractor_rate",
    "pack_all_candidates_metadata_available_count",
    "pack_all_candidates_metadata_available_rate",
    "pack_any_source_required_feature_unavailable_count",
    "pack_any_source_required_feature_unavailable_rate",
    "pack_metadata_gate_diversity_count",
    "pack_metadata_gate_diversity_rate",
    "metadata_low_risk",
    "metadata_medium_risk",
    "metadata_high_risk",
    "metadata_unavailable",
    "metadata_low_risk_count",
    "metadata_medium_risk_count",
    "metadata_high_risk_count",
    "metadata_unavailable_count",
    "gold_file_count",
    "gold_span_count",
    "file_right_span_wrong_count",
    "gold_file_rate",
    "gold_span_rate",
    "file_right_span_wrong_rate",
    "no_gold_high_risk_candidate_rate",
    "no_gold_high_risk_candidate_count",
    "no_gold_candidate_denominator",
    "not_used_for_feature_construction",
    "diagnostic_correlation_availability",
    "rrf_yes",
    "rrf_no",
    "source_class",
    "agreement_class",
    "rrf_backing",
    "span_overlap",
    "single_source",
    "same_file_only",
    "disagree",
    "symbol_regex_fusion",
    "regex_only",
    "symbol_only",
    "other",
    "source",
    "test",
    "config",
    "doc",
    "unknown",
    "generated_or_vendor",
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


def _read_optional_report(path: Path | None, report_name: str) -> dict[str, Any]:
    """Read optional upstream report and return only aggregate enum/status metadata."""
    source_key = f"{report_name}_report_source"
    status_key = f"{report_name}_quality_gate_status"
    pack_not_evidence_key = "p49_pack_not_evidence"
    overlay_key = "p48_overlay_availability"
    not_provided = {
        source_key: "not_provided",
        status_key: "not_provided",
    }
    if path is None or not path.exists():
        if report_name == "p48":
            not_provided[overlay_key] = "not_provided"
        if report_name == "p49":
            not_provided[pack_not_evidence_key] = "not_provided"
        return not_provided
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        result = {source_key: "invalid_json", status_key: "not_provided"}
        if report_name == "p48":
            result[overlay_key] = "not_provided"
        if report_name == "p49":
            result[pack_not_evidence_key] = "not_provided"
        return result

    result: dict[str, Any] = {source_key: "provided_report"}
    status = data.get("status") or data.get("quality_gate_status") or "not_provided"
    if not isinstance(status, str):
        status = "not_provided"
    result[status_key] = status
    if report_name == "p48":
        overlay = data.get("route_simulation", {}).get("p48_p25_rmc_overlay_v0", {}).get("availability")
        result[overlay_key] = overlay if isinstance(overlay, str) else "not_provided"
    if report_name == "p49":
        pne = data.get("pack_not_evidence")
        result[pack_not_evidence_key] = bool(pne) if isinstance(pne, bool) else "not_provided"
    return result


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P52_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _normalize_candidates(task: dict[str, Any]) -> list[dict[str, Any]]:
    """Wrap P49 normalizer so callers see a stable internal representation."""
    return p49._normalize_candidates(task)


def _build_pack(candidates: list[dict[str, Any]], strategy: str) -> dict[str, Any]:
    """Wrap P49 pack builder."""
    return p49._build_pack(candidates, strategy)


def _candidate_subtype_value(cand: dict[str, Any], key: str, default: str = "other") -> str:
    st = cand.get("subtype") or {}
    if not isinstance(st, dict):
        return default
    value = st.get(key)
    if value is None:
        return default
    return str(value)


def _metadata_complete(cand: dict[str, Any]) -> bool:
    if cand.get("path_kind") in {None, "unknown"}:
        return False
    if cand.get("span_width") is None:
        return False
    if cand.get("score") is None:
        return False
    if not cand.get("channels"):
        return False
    if not cand.get("subtype"):
        return False
    if cand.get("rank") is None:
        return False
    if not cand.get("source_strategy"):
        return False
    return True


def _metadata_unavailable(cand: dict[str, Any]) -> bool:
    if cand.get("path_kind") in {None, "unknown"}:
        return True
    if cand.get("span_width") is None:
        return True
    if cand.get("rank") is None:
        return True
    return False


def _metadata_risk_bucket(cand: dict[str, Any], risk_tags: list[str]) -> str:
    path_kind = cand.get("path_kind")
    span_width = cand.get("span_width")
    rank = cand.get("rank")
    source_class = _candidate_subtype_value(cand, "source_class", "other")
    agreement_class = _candidate_subtype_value(cand, "agreement_class", "other")
    rrf_backing = p49._has_rrf_backing(cand)

    tags_lower = {str(t).lower() for t in (risk_tags or [])}

    if _metadata_unavailable(cand):
        return "metadata_unavailable"

    high_reasons = (
        source_class == "regex_only"
        or agreement_class == "disagree"
        or (agreement_class == "single_source" and not rrf_backing)
        or path_kind in {"generated_or_vendor", "unknown"}
        or (isinstance(span_width, int) and span_width > SPAN_TOO_WIDE)
        or bool(tags_lower & {"negative", "high_noise", "ambiguous"})
    )
    if high_reasons:
        return "metadata_high_risk"

    low_reasons = (
        source_class == "symbol_regex_fusion"
        and agreement_class == "span_overlap"
        and rrf_backing
        and isinstance(rank, int)
        and rank <= 3
        and path_kind == "source"
        and isinstance(span_width, int)
        and span_width <= SPAN_BOUNDED
    )
    if low_reasons:
        return "metadata_low_risk"

    return "metadata_medium_risk"


def _compute_feature_availability(
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    denom = len(candidates)
    if denom == 0:
        return {
            "candidate_denominator": 0,
            "candidate_has_path_kind_rate": None,
            "candidate_has_span_width_rate": None,
            "candidate_has_score_rate": None,
            "candidate_has_channels_rate": None,
            "candidate_has_subtype_rate": None,
            "candidate_has_rank_rate": None,
            "candidate_has_source_strategy_rate": None,
            "metadata_complete_rate": None,
        }

    has_path_kind = sum(
        1 for c in candidates if c.get("path_kind") is not None and c.get("path_kind") != "unknown"
    )
    has_span = sum(1 for c in candidates if c.get("span_width") is not None)
    has_score = sum(1 for c in candidates if c.get("score") is not None)
    has_channels = sum(1 for c in candidates if bool(c.get("channels")))
    has_subtype = sum(1 for c in candidates if bool(c.get("subtype")))
    has_rank = sum(1 for c in candidates if c.get("rank") is not None)
    has_source_strategy = sum(1 for c in candidates if bool(c.get("source_strategy")))
    complete = sum(1 for c in candidates if _metadata_complete(c))

    return {
        "candidate_denominator": denom,
        "candidate_has_path_kind_rate": _rate(has_path_kind, denom),
        "candidate_has_span_width_rate": _rate(has_span, denom),
        "candidate_has_score_rate": _rate(has_score, denom),
        "candidate_has_channels_rate": _rate(has_channels, denom),
        "candidate_has_subtype_rate": _rate(has_subtype, denom),
        "candidate_has_rank_rate": _rate(has_rank, denom),
        "candidate_has_source_strategy_rate": _rate(has_source_strategy, denom),
        "metadata_complete_rate": _rate(complete, denom),
    }


def _compute_checkable_features(
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    denom = len(candidates)
    if denom == 0:
        return {
            "candidate_denominator": 0,
            "rrf_backing_checkable_rate": None,
            "symbol_regex_agreement_checkable_rate": None,
            "path_kind_checkable_rate": None,
            "span_width_reasonableness_checkable_rate": None,
            "rmc_trigger_checkable_rate": None,
        }

    rrf = sum(1 for c in candidates if p49._has_rrf_backing(c))
    sym_regex = sum(1 for c in candidates if p49._has_symbol_regex_agreement(c))
    path_ok = sum(
        1 for c in candidates if c.get("path_kind") is not None and c.get("path_kind") != "unknown"
    )
    span_ok = sum(
        1
        for c in candidates
        if isinstance(c.get("span_width"), int) and 1 <= c["span_width"] <= SPAN_TOO_WIDE
    )
    rmc = sum(1 for c in candidates if p49._is_rmc_trigger(c))

    return {
        "candidate_denominator": denom,
        "rrf_backing_checkable_rate": _rate(rrf, denom),
        "symbol_regex_agreement_checkable_rate": _rate(sym_regex, denom),
        "path_kind_checkable_rate": _rate(path_ok, denom),
        "span_width_reasonableness_checkable_rate": _rate(span_ok, denom),
        "rmc_trigger_checkable_rate": _rate(rmc, denom),
    }


def _compute_source_required_verifiers(
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    denom = len(candidates)
    source_features = [
        "exact_identifier_in_span",
        "query_terms_in_span",
        "signature_match",
        "ast_node_kind",
        "comment_only_flag",
        "source_text_span_width_verified",
        "content_sha_verified",
        "line_range_verified_against_current_file",
        "identifier_density",
        "term_density",
        "import_only_flag",
        "test_assertion_context",
    ]
    block: dict[str, Any] = {
        "availability": "unavailable_source_read_not_wired",
        "candidate_denominator": denom,
    }
    for feature in source_features:
        block[feature] = {
            "availability": "unavailable_source_read_not_wired",
            "checkable_count": None,
            "checkable_rate": None,
            "unavailable_count": denom,
            "unavailable_rate": 1.0 if denom > 0 else None,
            "value": None,
        }
    return block


def _compute_query_required_verifiers() -> dict[str, Any]:
    return {
        "raw_query_terms_available": False,
        "query_term_match": {
            "availability": "unavailable_raw_query_not_public",
            "value": None,
        },
        "intent_identifier_match": {
            "availability": "unavailable_raw_query_not_public",
            "value": None,
        },
    }


class _CandidateRiskAccumulator:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {b: 0 for b in RISK_BUCKETS}
        self.by_strategy: dict[str, dict[str, int]] = defaultdict(lambda: {b: 0 for b in RISK_BUCKETS})
        self.by_path_kind: dict[str, dict[str, int]] = defaultdict(
            lambda: {b: 0 for b in RISK_BUCKETS}
        )
        self.by_source_class: dict[str, dict[str, int]] = defaultdict(
            lambda: {b: 0 for b in RISK_BUCKETS}
        )
        self.by_agreement_class: dict[str, dict[str, int]] = defaultdict(
            lambda: {b: 0 for b in RISK_BUCKETS}
        )
        self.by_rrf: dict[str, dict[str, int]] = defaultdict(
            lambda: {b: 0 for b in RISK_BUCKETS}
        )
        self.by_risk_tag: dict[str, dict[str, int]] = defaultdict(
            lambda: {b: 0 for b in RISK_BUCKETS}
        )
        self.by_slot: dict[str, dict[str, int]] = defaultdict(
            lambda: {b: 0 for b in RISK_BUCKETS}
        )

    def add(
        self,
        bucket: str,
        strategy: str,
        slot: str,
        cand: dict[str, Any],
        risk_tags: list[str],
    ) -> None:
        self.counts[bucket] += 1
        self.by_strategy[strategy][bucket] += 1
        pk = str(cand.get("path_kind") or "unknown")
        self.by_path_kind[pk][bucket] += 1
        sc = _candidate_subtype_value(cand, "source_class", "other")
        self.by_source_class[sc][bucket] += 1
        ac = _candidate_subtype_value(cand, "agreement_class", "other")
        self.by_agreement_class[ac][bucket] += 1
        rrf = "rrf_yes" if p49._has_rrf_backing(cand) else "rrf_no"
        self.by_rrf[rrf][bucket] += 1
        for tag in risk_tags or ["other"]:
            self.by_risk_tag[str(tag)][bucket] += 1
        self.by_slot[slot][bucket] += 1


def _build_strategy_packs(
    tasks: list[dict[str, Any]],
) -> tuple[dict[tuple[int, str], dict[str, Any]], list[list[dict[str, Any]]]]:
    """Build P49 packs per task/strategy and return per-task candidate lists."""
    per_task_candidates: list[list[dict[str, Any]]] = []
    packs: dict[tuple[int, str], dict[str, Any]] = {}
    for idx, task in enumerate(tasks):
        candidates = _normalize_candidates(task)
        per_task_candidates.append(candidates)
        for strategy in p49.PACK_STRATEGIES:
            packs[(idx, strategy)] = _build_pack(candidates, strategy)
    return packs, per_task_candidates


def _slot_for_index(strategy: str, selected: list[dict[str, Any]], index: int) -> str:
    """Best-effort slot label used only for aggregate diagnostics.

    P49 does not publish a per-candidate slot map, so this is recomputed from the
    deterministic builder shape.  The first selected candidate is always the
    primary anchor.  RRF consensus and RMC trigger slots are heuristics; any
    candidate not matching a named slot is reported as "pack_fill".
    """
    if not selected:
        return "none"
    if index == 0:
        return "primary_anchor"
    if index >= len(selected):
        return "none"
    cand = selected[index]

    # topk_flat_pack fills no named slots.
    if strategy == "topk_flat_pack_v0":
        return "pack_fill"

    anchor = selected[0]
    labels: list[str] = []
    if p49._has_rrf_backing(cand) and isinstance(cand.get("rank"), int) and cand["rank"] <= 3:
        labels.append("rrf_consensus")
    if cand["_path"] == anchor["_path"]:
        if p49._overlaps(cand, anchor):
            labels.append("same_file_neighbor")
        elif cand["_id"] != anchor["_id"]:
            labels.append("same_file_contrast")
    else:
        labels.append("cross_file_anchor")
    if cand.get("path_kind") == "test" and anchor.get("path_kind") == "source":
        labels.append("source_test_pair")
    if cand.get("path_kind") == "source" and anchor.get("path_kind") == "test":
        labels.append("source_test_pair")
    if p49._is_rmc_trigger(cand):
        labels.append("rmc_trigger_candidate")
    if cand.get("path_kind") in {"generated_or_vendor", "unknown"}:
        labels.append("hard_distractor")
    return labels[0] if labels else "pack_fill"


def _accumulate_risk_and_features(
    tasks: list[dict[str, Any]],
    packs: dict[tuple[int, str], dict[str, Any]],
    accumulator: _CandidateRiskAccumulator,
) -> dict[str, dict[str, Any]]:
    """Compute per-strategy feature/checkable blocks and risk buckets."""
    selected_by_strategy: dict[str, list[dict[str, Any]]] = {
        strategy: [] for strategy in p49.PACK_STRATEGIES
    }

    for (task_idx, strategy), pack in packs.items():
        task = tasks[task_idx]
        risk_tags = task.get("task_risk_tags", [])
        selected = pack.get("selected", [])
        for idx, cand in enumerate(selected):
            bucket = _metadata_risk_bucket(cand, risk_tags)
            slot = _slot_for_index(strategy, selected, idx)
            accumulator.add(bucket, strategy, slot, cand, risk_tags)
        selected_by_strategy[strategy].extend(selected)

    by_strategy_features = {
        strategy: _compute_feature_availability(selected_by_strategy[strategy])
        for strategy in p49.PACK_STRATEGIES
    }
    by_strategy_checkable = {
        strategy: _compute_checkable_features(selected_by_strategy[strategy])
        for strategy in p49.PACK_STRATEGIES
    }

    return {
        "by_strategy_features": by_strategy_features,
        "by_strategy_checkable": by_strategy_checkable,
    }


def _build_risk_bucket_block(
    accumulator: _CandidateRiskAccumulator,
) -> dict[str, Any]:
    total = sum(accumulator.counts.values())
    rates = {f"{b}_rate": _rate(accumulator.counts[b], total) for b in RISK_BUCKETS}

    def collapse(dim: dict[str, dict[str, int]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, counts in sorted(dim.items()):
            subtotal = sum(counts.values())
            out[key] = {
                "candidate_count": subtotal,
                **{b: counts[b] for b in RISK_BUCKETS},
                **{f"{b}_rate": _rate(counts[b], subtotal) for b in RISK_BUCKETS},
            }
        return out

    return {
        "risk_bucket_counts": {b: accumulator.counts[b] for b in RISK_BUCKETS},
        "risk_bucket_rates": rates,
        "candidate_denominator": total,
        "by_pack_strategy": collapse(accumulator.by_strategy),
        "by_path_kind": collapse(accumulator.by_path_kind),
        "by_source_class": collapse(accumulator.by_source_class),
        "by_agreement_class": collapse(accumulator.by_agreement_class),
        "by_rrf_backing": collapse(accumulator.by_rrf),
        "by_risk_tag": collapse(accumulator.by_risk_tag),
        "by_pack_slot": collapse(accumulator.by_slot),
    }


def _build_pack_level_metrics(
    tasks: list[dict[str, Any]],
    packs: dict[tuple[int, str], dict[str, Any]],
) -> dict[str, Any]:
    overall = {
        "pack_denominator": 0,
        "pack_with_low_risk_anchor_count": 0,
        "pack_with_high_risk_distractor_count": 0,
        "pack_all_candidates_metadata_available_count": 0,
        "pack_any_source_required_feature_unavailable_count": 0,
        "pack_metadata_gate_diversity_count": 0,
    }
    by_strategy: dict[str, dict[str, Any]] = {
        strategy: {
            "pack_denominator": 0,
            "pack_with_low_risk_anchor_count": 0,
            "pack_with_high_risk_distractor_count": 0,
            "pack_all_candidates_metadata_available_count": 0,
            "pack_any_source_required_feature_unavailable_count": 0,
            "pack_metadata_gate_diversity_count": 0,
        }
        for strategy in p49.PACK_STRATEGIES
    }

    for (task_idx, strategy), pack in packs.items():
        task = tasks[task_idx]
        risk_tags = task.get("task_risk_tags", [])
        selected = pack.get("selected", [])
        if not selected:
            continue
        overall["pack_denominator"] += 1
        by_strategy[strategy]["pack_denominator"] += 1

        buckets = [_metadata_risk_bucket(c, risk_tags) for c in selected]
        anchor_bucket = buckets[0]
        non_anchor_buckets = buckets[1:]

        if anchor_bucket == "metadata_low_risk":
            overall["pack_with_low_risk_anchor_count"] += 1
            by_strategy[strategy]["pack_with_low_risk_anchor_count"] += 1

        if any(b == "metadata_high_risk" for b in non_anchor_buckets):
            overall["pack_with_high_risk_distractor_count"] += 1
            by_strategy[strategy]["pack_with_high_risk_distractor_count"] += 1

        if all(_metadata_complete(c) for c in selected):
            overall["pack_all_candidates_metadata_available_count"] += 1
            by_strategy[strategy]["pack_all_candidates_metadata_available_count"] += 1

        # Source-required features are not wired in P52 (metadata-only), so any
        # nonempty pack has at least one unavailable source-required feature.
        overall["pack_any_source_required_feature_unavailable_count"] += 1
        by_strategy[strategy]["pack_any_source_required_feature_unavailable_count"] += 1

        if len(set(buckets)) > 1:
            overall["pack_metadata_gate_diversity_count"] += 1
            by_strategy[strategy]["pack_metadata_gate_diversity_count"] += 1

    def finalize(block: dict[str, Any]) -> dict[str, Any]:
        denom = block["pack_denominator"]
        return {
            "pack_denominator": denom,
            "pack_with_low_risk_anchor_count": block["pack_with_low_risk_anchor_count"],
            "pack_with_low_risk_anchor_rate": _rate(block["pack_with_low_risk_anchor_count"], denom),
            "pack_with_high_risk_distractor_count": block["pack_with_high_risk_distractor_count"],
            "pack_with_high_risk_distractor_rate": _rate(
                block["pack_with_high_risk_distractor_count"], denom
            ),
            "pack_all_candidates_metadata_available_count": block[
                "pack_all_candidates_metadata_available_count"
            ],
            "pack_all_candidates_metadata_available_rate": _rate(
                block["pack_all_candidates_metadata_available_count"], denom
            ),
            "pack_any_source_required_feature_unavailable_count": block[
                "pack_any_source_required_feature_unavailable_count"
            ],
            "pack_any_source_required_feature_unavailable_rate": _rate(
                block["pack_any_source_required_feature_unavailable_count"], denom
            ),
            "pack_metadata_gate_diversity_count": block["pack_metadata_gate_diversity_count"],
            "pack_metadata_gate_diversity_rate": _rate(
                block["pack_metadata_gate_diversity_count"], denom
            ),
        }

    return {
        "task_wide": finalize(overall),
        "by_pack_strategy": {strategy: finalize(by_strategy[strategy]) for strategy in p49.PACK_STRATEGIES},
    }


def _build_score_phase_diagnostics(
    tasks: list[dict[str, Any]],
    packs: dict[tuple[int, str], dict[str, Any]],
) -> dict[str, Any]:
    positive_with_gold = [
        (idx, t)
        for idx, t in enumerate(tasks)
        if t.get("has_gold") and t.get("has_gold_spans")
    ]
    no_gold = [t for t in tasks if not t.get("has_gold")]

    if not positive_with_gold:
        availability = "missing_gold_spans"
    else:
        availability = "available"

    by_bucket_counts: dict[str, dict[str, int]] = {
        b: {"candidate_count": 0, "gold_file_count": 0, "gold_span_count": 0, "file_right_span_wrong_count": 0}
        for b in RISK_BUCKETS
    }

    for task_idx, task in positive_with_gold:
        label = task.get("label", {})
        risk_tags = task.get("task_risk_tags", [])
        for strategy in p49.PACK_STRATEGIES:
            pack = packs.get((task_idx, strategy))
            if not pack:
                continue
            for cand in pack.get("selected", []):
                bucket = _metadata_risk_bucket(cand, risk_tags)
                by_bucket_counts[bucket]["candidate_count"] += 1
                if p49._file_in_gold(cand, label):
                    by_bucket_counts[bucket]["gold_file_count"] += 1
                if p49._span_overlaps_gold(cand, label):
                    by_bucket_counts[bucket]["gold_span_count"] += 1
                if p49._file_in_gold(cand, label) and not p49._span_overlaps_gold(cand, label):
                    by_bucket_counts[bucket]["file_right_span_wrong_count"] += 1

    by_bucket: dict[str, Any] = {}
    for b in RISK_BUCKETS:
        counts = by_bucket_counts[b]
        denom = counts["candidate_count"]
        by_bucket[b] = {
            "candidate_count": denom,
            "gold_file_count": counts["gold_file_count"],
            "gold_file_rate": _rate(counts["gold_file_count"], denom),
            "gold_span_count": counts["gold_span_count"],
            "gold_span_rate": _rate(counts["gold_span_count"], denom),
            "file_right_span_wrong_count": counts["file_right_span_wrong_count"],
            "file_right_span_wrong_rate": _rate(counts["file_right_span_wrong_count"], denom),
        }

    no_gold_high_risk_count = 0
    no_gold_candidate_denominator = 0
    for task in no_gold:
        risk_tags = task.get("task_risk_tags", [])
        # Count once per unique candidate across all strategies to avoid
        # over-weighting repeated pack membership.
        seen_ids: set[int] = set()
        candidates = _normalize_candidates(task)
        for cand in candidates:
            cid = cand.get("_id")
            if not isinstance(cid, int):
                continue
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            no_gold_candidate_denominator += 1
            bucket = _metadata_risk_bucket(cand, risk_tags)
            if bucket == "metadata_high_risk":
                no_gold_high_risk_count += 1

    return {
        "not_used_for_feature_construction": True,
        "diagnostic_correlation_availability": availability,
        "by_metadata_risk_bucket": by_bucket,
        "no_gold_high_risk_candidate_count": no_gold_high_risk_count,
        "no_gold_candidate_denominator": no_gold_candidate_denominator,
        "no_gold_high_risk_candidate_rate": _rate(
            no_gold_high_risk_count, no_gold_candidate_denominator
        ),
        "outcome_correlations": {"availability": "unavailable_outcome_not_attached"},
    }


def build_report(
    tasks: list[dict[str, Any]],
    *,
    self_test: bool,
    elapsed_ms: int,
    status: str,
    reason: str | None,
    input_source_count: int,
    insufficient_input_source_count: int,
    p49_report_path: Path | None,
    p50_report_path: Path | None,
    p48_report_path: Path | None,
) -> dict[str, Any]:
    candidate_pool_availability = (
        "available"
        if tasks and all(t.get("has_candidate_pool") for t in tasks)
        else "partial"
        if tasks and any(t.get("has_candidate_pool") for t in tasks)
        else "missing_candidate_pool"
    )
    gold_span_availability = (
        "available"
        if tasks and all(t.get("has_gold_spans") for t in tasks if t["has_gold"])
        else "partial"
        if tasks and any(t.get("has_gold_spans") for t in tasks if t["has_gold"])
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

    p49_meta = _read_optional_report(p49_report_path, "p49")
    p50_meta = _read_optional_report(p50_report_path, "p50")
    p48_meta = _read_optional_report(p48_report_path, "p48")

    # Build P49 packs in-memory for pack-level metrics and slot/risk diagnostics.
    packs, per_task_candidates = _build_strategy_packs(tasks)

    # Task-wide metadata feature availability over all unique normalized candidates.
    all_candidates: list[dict[str, Any]] = []
    for candidates in per_task_candidates:
        all_candidates.extend(candidates)
    task_wide_feature_availability = _compute_feature_availability(all_candidates)
    task_wide_checkable_features = _compute_checkable_features(all_candidates)

    accumulator = _CandidateRiskAccumulator()
    strategy_blocks = _accumulate_risk_and_features(tasks, packs, accumulator)

    metadata_gate_v0 = _build_risk_bucket_block(accumulator)
    pack_level = _build_pack_level_metrics(tasks, packs)
    score_phase_diagnostics = _build_score_phase_diagnostics(tasks, packs)

    source_required_task_wide = _compute_source_required_verifiers(all_candidates)
    source_required_by_strategy: dict[str, Any] = {
        strategy: _compute_source_required_verifiers([])
        for strategy in p49.PACK_STRATEGIES
    }
    for strategy in p49.PACK_STRATEGIES:
        selected: list[dict[str, Any]] = []
        for task_idx, _ in enumerate(tasks):
            selected.extend(packs[(task_idx, strategy)].get("selected", []))
        source_required_by_strategy[strategy] = _compute_source_required_verifiers(selected)

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P52 Metadata-Only Local Verifier Scaffold is ready; real per-task ephemeral P25 records are required."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(
                f"Self-test-only verifier inventoried metadata features for {len(tasks)} synthetic tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P52 inventoried metadata-verifier features for {len(tasks)} real ephemeral P25 records."
            )
        conclusion_lines.append(
            "Feature extraction used candidate metadata only (rank, score, channels, subtype axes, path-kind, span width). "
            "Gold spans and outcomes were used only for explicitly-marked SCORE-phase diagnostic correlations."
        )
        conclusion_lines.append(
            "P52 does not verify source text, does not read files, does not call an LLM, does not construct prompts, "
            "does not validate EvidenceCore, does not produce evidence, and does not produce a verifier pass/fail score."
        )
        conclusion_lines.append(
            "P52 metadata gates are candidate-risk diagnostics only and do not prove P51/P53 quality."
        )
        conclusion_lines.append(
            f"Metadata-complete rate (task-wide): {task_wide_feature_availability.get('metadata_complete_rate')}; "
            f"source-required features availability: unavailable_source_read_not_wired."
        )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": "P52 Metadata-Only Local Verifier Scaffold",
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
        "verifier_not_evidence": True,
        "metadata_verifier_only": True,
        "remote_calls_by_p52": 0,
        "llm_calls_by_p52": 0,
        "source_reads_attempted_by_p52": False,
        "prompt_construction_by_p52": False,
        "source_text_verification_unavailable": True,
        "local_verifier_score_available": False,
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
        "candidate_pool_availability": candidate_pool_availability,
        "gold_span_availability": gold_span_availability,
        "reach_metrics_available": reach_metrics_available,
        "p31_h1_handoff_detected": p31_h1_handoff_detected,
        "p31_h1_handoff_detected_count": p31_h1_handoff_detected_count,
        "p33b_handoff_detected": p33b_handoff_detected,
        "p33b_handoff_detected_count": p33b_handoff_detected_count,
        "source_required_features_availability": "unavailable_source_read_not_wired",
        **p49_meta,
        **p50_meta,
        **p48_meta,
        "metrics": {
            "metadata_feature_availability": {
                "task_wide": task_wide_feature_availability,
                "by_pack_strategy": strategy_blocks["by_strategy_features"],
            },
            "metadata_checkable_features": {
                "task_wide": task_wide_checkable_features,
                "by_pack_strategy": strategy_blocks["by_strategy_checkable"],
            },
            "source_required_verifiers": {
                "task_wide": source_required_task_wide,
                "by_pack_strategy": source_required_by_strategy,
            },
            "query_required_verifiers": _compute_query_required_verifiers(),
            "metadata_gate_v0": metadata_gate_v0,
            "pack_level": pack_level,
            "score_phase_diagnostics": score_phase_diagnostics,
        },
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P52 public report validation failed: {errors}")
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    """Validate schema, safety flags, and recursive forbidden-key scan."""
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p52") != 0:
        errors.append("remote_calls_by_p52 must be 0")
    if report.get("llm_calls_by_p52") != 0:
        errors.append("llm_calls_by_p52 must be 0")
    if report.get("source_reads_attempted_by_p52") is not False:
        errors.append("source_reads_attempted_by_p52 must be false")
    if report.get("prompt_construction_by_p52") is not False:
        errors.append("prompt_construction_by_p52 must be false")

    expected_flags = {
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "verifier_not_evidence": True,
        "metadata_verifier_only": True,
        "source_text_verification_unavailable": True,
        "local_verifier_score_available": False,
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

    if report.get("self_test") and report.get("not_quality_evidence") is not True:
        errors.append("self_test must set not_quality_evidence=true")

    for forbidden in ("tasks", "records", "per_task_results", "decision_records"):
        if forbidden in report:
            errors.append(f"public report must not contain {forbidden}")

    errors.extend(_reject_forbidden_keys(report))
    return errors


def _fmt_scalar(x: Any) -> str:
    return f"{x:.4f}" if isinstance(x, (int, float)) else "n/a"


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = ["# P52 Metadata-Only Local Verifier Scaffold\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P52: {report['remote_calls_by_p52']}",
        f"- LLM calls by P52: {report['llm_calls_by_p52']}",
        f"- Source reads by P52: {report['source_reads_attempted_by_p52']}",
        f"- Prompt construction by P52: {report['prompt_construction_by_p52']}",
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}",
        f"- Candidate pool availability: `{report['candidate_pool_availability']}`",
        f"- Gold span availability: `{report['gold_span_availability']}`",
        f"- Reach metrics available: {report['reach_metrics_available']}",
        f"- Source-required features availability: `{report['source_required_features_availability']}`",
        f"- P49 report source: `{report.get('p49_report_source')}`",
        f"- P49 pack not evidence: `{report.get('p49_pack_not_evidence')}`",
        f"- P50 report source: `{report.get('p50_report_source')}`",
        f"- P50 quality gate status: `{report.get('p50_quality_gate_status')}`",
        f"- P48 report source: `{report.get('p48_report_source')}`",
        f"- P48 overlay availability: `{report.get('p48_overlay_availability')}`\n",
    ])

    if report["status"] not in {"ok", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records.", ""])
        return "\n".join(lines)

    lines.extend([
        "## Purpose\n",
        "P52 inventories metadata-verifier feature availability and candidate-risk buckets before any source-read or LLM span-narrow phase. "
        "It is a SCORE-phase-only scaffold, not a verifier pass/fail phase.",
        "",
        "## Methodology\n",
        "- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).",
        "- Normalize raw candidate pools into metadata-only records using P46/P49 helpers.",
        "- Compute metadata feature availability, checkable metadata signals, and unavailable source/query verifier fields.",
        "- Classify every candidate into a metadata-risk bucket using only public metadata (path-kind, span width, rank, subtype axes, risk tags).",
        "- Rebuild P49 pack strategies in-memory and report aggregate pack-level risk diagnostics.",
        "- After metadata extraction, compute SCORE-phase diagnostic correlations with gold spans/outcomes where available; these are marked `not_used_for_feature_construction=true`.",
        "- Output is aggregate-only: counts, rates, and distributions by pack strategy, public task bucket, and risk tag.",
        "",
        "## Safety notes\n",
        "- P52 does not verify source text.",
        "- P52 does not read files.",
        "- P52 does not call an LLM.",
        "- P52 does not construct prompts.",
        "- P52 does not validate EvidenceCore.",
        "- P52 does not produce evidence.",
        "- P52 does not produce a verifier pass/fail score.",
        "- P52 metadata gates are candidate-risk diagnostics only.",
        "- P52 does not prove P51/P53 quality.",
        "",
    ])

    task_wide = report["metrics"]["metadata_feature_availability"]["task_wide"]
    lines.append("## Metadata feature availability (task-wide)\n")
    lines.append(
        "| Denom | PathKind | SpanWidth | Score | Channels | Subtype | Rank | SourceStrategy | Complete |"
    )
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {task_wide['candidate_denominator']} | {_fmt_scalar(task_wide['candidate_has_path_kind_rate'])} | "
        f"{_fmt_scalar(task_wide['candidate_has_span_width_rate'])} | {_fmt_scalar(task_wide['candidate_has_score_rate'])} | "
        f"{_fmt_scalar(task_wide['candidate_has_channels_rate'])} | {_fmt_scalar(task_wide['candidate_has_subtype_rate'])} | "
        f"{_fmt_scalar(task_wide['candidate_has_rank_rate'])} | {_fmt_scalar(task_wide['candidate_has_source_strategy_rate'])} | "
        f"{_fmt_scalar(task_wide['metadata_complete_rate'])} |"
    )
    lines.append("")

    lines.append("## Metadata checkable features (task-wide)\n")
    lines.append("| Denom | RRF | SymReg | PathKind | SpanReasonable | RMCTrigger |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    twc = report["metrics"]["metadata_checkable_features"]["task_wide"]
    lines.append(
        f"| {twc['candidate_denominator']} | {_fmt_scalar(twc['rrf_backing_checkable_rate'])} | "
        f"{_fmt_scalar(twc['symbol_regex_agreement_checkable_rate'])} | {_fmt_scalar(twc['path_kind_checkable_rate'])} | "
        f"{_fmt_scalar(twc['span_width_reasonableness_checkable_rate'])} | {_fmt_scalar(twc['rmc_trigger_checkable_rate'])} |"
    )
    lines.append("")

    lines.append("## Metadata gate v0 risk buckets\n")
    gate = report["metrics"]["metadata_gate_v0"]
    lines.append("| Bucket | Count | Rate |")
    lines.append("|---|---:|---:|")
    for b in RISK_BUCKETS:
        lines.append(f"| {b} | {gate['risk_bucket_counts'][b]} | {_fmt_scalar(gate['risk_bucket_rates'][f'{b}_rate'])} |")
    lines.append("")

    lines.append("## Pack-level risk diagnostics\n")
    pack = report["metrics"]["pack_level"]["task_wide"]
    lines.append("| Denom | LowRiskAnchor | HighRiskDistractor | AllMetadataAvail | SourceRequiredUnavailable | GateDiversity |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {pack['pack_denominator']} | {_fmt_scalar(pack['pack_with_low_risk_anchor_rate'])} | "
        f"{_fmt_scalar(pack['pack_with_high_risk_distractor_rate'])} | {_fmt_scalar(pack['pack_all_candidates_metadata_available_rate'])} | "
        f"{_fmt_scalar(pack['pack_any_source_required_feature_unavailable_rate'])} | {_fmt_scalar(pack['pack_metadata_gate_diversity_rate'])} |"
    )
    lines.append("")

    lines.append("## SCORE-phase diagnostic correlations (not used for feature construction)\n")
    score = report["metrics"]["score_phase_diagnostics"]
    lines.append(f"- Diagnostic correlation availability: `{score['diagnostic_correlation_availability']}`")
    lines.append("")
    lines.append("| Bucket | Candidates | GoldFile | GoldSpan | FileRightSpanWrong |")
    lines.append("|---:|---:|---:|---:|---:|")
    for b in RISK_BUCKETS:
        block = score["by_metadata_risk_bucket"][b]
        lines.append(
            f"| {b} | {block['candidate_count']} | {_fmt_scalar(block['gold_file_rate'])} | "
            f"{_fmt_scalar(block['gold_span_rate'])} | {_fmt_scalar(block['file_right_span_wrong_rate'])} |"
        )
    lines.append("")
    lines.append(
        f"- No-gold high-risk candidate rate: {_fmt_scalar(score['no_gold_high_risk_candidate_rate'])} "
        f"({score['no_gold_high_risk_candidate_count']}/{score['no_gold_candidate_denominator']})"
    )
    lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="P52 Metadata-Only Local Verifier Scaffold")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--p49-report", type=Path, default=None, help="Optional P49 report for enum/status carry-forward.")
    parser.add_argument("--p50-report", type=Path, default=None, help="Optional P50 report for enum/status carry-forward.")
    parser.add_argument("--p48-report", type=Path, default=None, help="Optional P48 report for enum/status carry-forward.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_input_records: list[dict[str, Any]] = []

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_input_records = p46.make_self_test_records()
    elif args.input:
        input_paths = list(args.input)
        raw_input_records = p25.load_p21_inputs(input_paths, require_ephemeral_schema=True)
    else:
        parser.error("Specify --self-test or --input PATH [PATH ...]")

    status = "self_test_only" if args.self_test else "ok"
    reason: str | None = None
    insufficient_count = 0
    task_records: list[dict[str, Any]] = []

    marker_reasons = {
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P52 metadata verification.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P52 requires p25-policy-records-ephemeral-v1 input schema.",
    }
    for rec in raw_input_records:
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
        reason = "Records lacked required fields for P52 normalization."

    elapsed_ms = int((time.monotonic() - start) * 1000)

    report = build_report(
        normalized_tasks,
        self_test=args.self_test,
        elapsed_ms=elapsed_ms,
        status=status,
        reason=reason,
        input_source_count=1 if args.self_test else max(1, len(args.input or [])),
        insufficient_input_source_count=insufficient_count,
        p49_report_path=args.p49_report,
        p50_report_path=args.p50_report,
        p48_report_path=args.p48_report,
    )

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P52 report written to {args.out}")
    print(f"P52 markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
