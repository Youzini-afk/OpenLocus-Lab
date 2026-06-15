#!/usr/bin/env python3
"""P52C Diagnostic Local Verifier Scoring Simulator.

P52C is a deterministic, diagnostic-only scoring simulator over P52B/P52A/P52/P49/P48
features.  It computes fixed gold-free diagnostic score buckets and aggregate
retrospective correlations.  It does NOT produce verifier pass/fail, evidence
validity, admission/default/promotion, or quality-over-P25 claims.

Hard constraints:
* No LLM/remote calls; `remote_calls_by_p52c=0`, `llm_calls_by_p52c=0`.
* No prompt construction; `prompt_construction_by_p52c=false`.
* Source reads only through existing P52A bounded helpers; no new unsafe reads.
* No raw source/snippet/path/span/digest/query/task/candidate/provider in public artifacts.
* No per-task/per-candidate/pack item rows.
* Score construction is gold-free; gold/outcomes are used only inside the
  explicitly-marked `score_phase_diagnostic_correlation` after score buckets are fixed.
* Unavailable source/query/AST features are unavailable/null, not false/zero evidence.
* `local_verifier_score_available=false`; this is a diagnostic simulator, not a deployable
  verifier score.
* `verifier_score_not_admission=true`; `score_not_evidence=true`.
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
import p52_metadata_local_verifier_scaffold as p52
import p52a_source_materialization_prerequisite as p52a
import p52b_source_backed_local_verifier_feature_matrix as p52b

SCHEMA_VERSION = "p52c-local-verifier-scoring-simulator-v1"
GENERATED_BY = "eval/p52c_local_verifier_scoring_simulator.py"
STAGE = "P52C Diagnostic Local Verifier Scoring Simulator"

DEFAULT_OUT = Path("artifacts/p52c_local_verifier_scoring_simulator/p52c_local_verifier_scoring_simulator_report.json")
DEFAULT_DOC = Path("docs/en/p52c-local-verifier-scoring-simulator.md")

SCORE_BUCKETS = [
    "diagnostic_score_high",
    "diagnostic_score_medium",
    "diagnostic_score_low",
    "diagnostic_score_unavailable",
]

SCORE_BINS = ["<=-3", "-2_-1", "0_1", "2_3", ">=4"]

POSITIVE_COMPONENTS = [
    "source_read_success",
    "line_range_valid",
    "bounded_span_feature_available",
    "nonempty_span",
    "code_like_token",
    "signature_like_heuristic",
    "rrf_backing",
    "symbol_regex_fusion_span_overlap",
    "metadata_low_risk",
    "metadata_medium_risk",
]

NEGATIVE_COMPONENTS = [
    "digest_mismatch",
    "span_over_cap",
    "blank_only",
    "comment_only",
    "import_only",
    "generated_or_vendor_path_kind",
    "unknown_path_kind",
    "metadata_high_risk",
    "source_feature_high_risk",
    "source_feature_unavailable",
]

# Extend P52B forbidden/key safety lists.  Keep exact-key scans stable.
FORBIDDEN_PUBLIC_KEYS = set(p52b.FORBIDDEN_PUBLIC_KEYS) | {
    "repo_lock_path",
    "corpus_root",
    "raw_query",
    "query_terms",
    "identifier",
    "symbol_text",
    "provider",
    "provider_key",
    "base_url",
    "api_key",
    "digest",
    "digest_value",
    "candidate_score",
    "diagnostic_score_v0",
    "score_bucket",
}

P52C_SAFETY_FLAG_KEYS = set(p52b.P52B_SAFETY_FLAG_KEYS) | {
    # top-level P52C safety flags
    "remote_calls_by_p52c",
    "llm_calls_by_p52c",
    "prompt_construction_by_p52c",
    "source_reads_attempted_by_p52c",
    "source_reads_bounded_by_p52c",
    "score_not_evidence",
    "verifier_score_not_admission",
    "local_verifier_score_available",
    "p52c_score_availability",
    "p52c_diagnostic_score_v0",
    # metric block names and public sub-keys
    "score_availability",
    "diagnostic_score_distribution",
    "breakdowns",
    "score_phase_diagnostic_correlation",
    "diagnostic_score_high",
    "diagnostic_score_medium",
    "diagnostic_score_low",
    "diagnostic_score_unavailable",
    "not_source_backed",
    "score_candidate_denominator",
    "source_backed_score_candidate_denominator",
    "metadata_only_candidate_denominator",
    "score_unavailable_candidate_count",
    "score_unavailable_candidate_rate",
    "score_unavailable_reason_counts",
    "score_unavailable_reason_rates",
    "source_read_attempt_count",
    "source_read_success_count",
    "source_read_success_rate",
    "bounded_span_feature_candidate_denominator",
    "source_feature_available_count",
    "source_feature_available_rate",
    "diagnostic_score_bucket_counts",
    "diagnostic_score_bucket_rates",
    "score_bin_distribution",
    "component_coverage",
    "positive_component_rate_by_component",
    "negative_component_rate_by_component",
    "gold_file_rate_by_score_bucket",
    "gold_span_rate_by_score_bucket",
    "file_right_span_wrong_rate_by_score_bucket",
    "no_gold_rate_by_score_bucket",
    "existing_role_delta_by_score_bucket_if_available",
    "not_used_for_score_construction",
    "diagnostic_correlation_only",
    "p52c_report_source",
    "p52b_report_source",
    "p52a_report_source",
    "p52_report_source",
    "p49_report_source",
    "p50_report_source",
    "p48_report_source",
    "p52b_quality_gate_status",
    "p52a_quality_gate_status",
    "p52_quality_gate_status",
    "p50_quality_gate_status",
    "p49_pack_not_evidence",
    "p48_overlay_availability",
    "by_metadata_risk_bucket",
    "by_source_feature_bucket",
    "by_path_kind",
    "by_source_class",
    "by_agreement_class",
    "by_rrf_backing",
    "by_public_bucket",
    "by_public_risk_tag",
    "by_candidate_strategy",
    "by_pack_strategy",
    "metadata_risk_bucket",
    "source_feature_bucket",
    "public_risk_tag",
    "candidate_strategy",
    "pack_strategy",
    "source_backed",
    "metadata_only",
    "metadata_unavailable",
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


def _as_str(value: Any) -> str:
    return "" if value is None else str(value)


def _reject_forbidden_keys(obj: Any, prefix: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_str = str(key)
            if key_str in FORBIDDEN_PUBLIC_KEYS and key_str not in P52C_SAFETY_FLAG_KEYS:
                violations.append(prefix + key_str)
            else:
                violations.extend(_reject_forbidden_keys(value, prefix + key_str + "."))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            violations.extend(_reject_forbidden_keys(value, prefix + str(idx) + "."))
    return violations


def _read_optional_report(path: Path | None, report_name: str) -> dict[str, Any]:
    """Read optional upstream report and return only aggregate enum/status metadata."""
    return p52a._read_optional_report(path, report_name)


def _source_attempted(outcome: dict[str, Any]) -> bool:
    """A source read was attempted (root existed and candidate was checked)."""
    return bool(
        outcome.get("source_read_success")
        or outcome.get("path_invalid")
        or outcome.get("path_secret")
        or outcome.get("escape_reject")
        or outcome.get("source_read_success") is False
        and (
            outcome.get("missing_file")
            or outcome.get("file_too_large")
            or outcome.get("binary_or_decode")
            or outcome.get("secret_text")
            or outcome.get("budget_exceeded")
        )
    )


def _compute_score_components(
    outcome: dict[str, Any],
    features: dict[str, Any] | None,
    cand: dict[str, Any],
    risk_tags: list[str],
) -> tuple[bool, bool, bool, dict[str, Any]]:
    """Compute per-candidate score components.

    Returns (source_backed, metadata_only, unavailable, components).
    components maps a component name to {"value": bool|None, "applicable": bool}.
    Unavailable components have value=None.
    """
    path_kind = _as_str(cand.get("path_kind") or "unknown")
    metadata_bucket = p52._metadata_risk_bucket(cand, risk_tags)
    metadata_unavailable = metadata_bucket == "metadata_unavailable"
    metadata_available = not metadata_unavailable

    subtype = cand.get("subtype") or {}
    source_class = _as_str(subtype.get("source_class") or "other")
    agreement = _as_str(subtype.get("agreement_class") or "other")
    rrf = p49._has_rrf_backing(cand)
    symreg_span = source_class == "symbol_regex_fusion" and agreement == "span_overlap"

    source_backed = bool(
        outcome.get("source_read_success")
        and outcome.get("range_valid")
        and not outcome.get("span_over_cap")
        and features is not None
    )
    source_attempted = _source_attempted(outcome) or outcome.get("source_read_success") is not None
    source_root_unavailable = outcome.get("source_root_unavailable") is True

    # Source-feature bucket is informative for coverage; it is not itself the score.
    source_feature_bucket = ""
    if source_attempted or source_root_unavailable:
        source_feature_bucket = p52b._source_feature_bucket(outcome, features, cand, risk_tags)
    source_feature_computed = bool(source_feature_bucket)

    components: dict[str, Any] = {}

    # Positive components.
    components["source_read_success"] = {
        "value": True if source_backed else None,
        "applicable": source_backed,
    }
    components["line_range_valid"] = {
        "value": True if outcome.get("range_valid") else None,
        "applicable": source_attempted and not source_root_unavailable,
    }
    components["bounded_span_feature_available"] = {
        "value": True if features is not None else None,
        "applicable": source_attempted and not source_root_unavailable,
    }
    components["nonempty_span"] = {
        "value": True if features and features.get("span_nonempty") else None,
        "applicable": features is not None,
    }
    components["code_like_token"] = {
        "value": True
        if features
        and (
            features.get("span_contains_code_like_token")
            or features.get("span_contains_definition_keyword")
        )
        else None,
        "applicable": features is not None,
    }
    components["signature_like_heuristic"] = {
        "value": True if features and features.get("signature_like_line_heuristic") else None,
        "applicable": features is not None,
    }
    components["rrf_backing"] = {
        "value": True if rrf else None,
        "applicable": metadata_available,
    }
    components["symbol_regex_fusion_span_overlap"] = {
        "value": True if symreg_span else None,
        "applicable": metadata_available,
    }
    components["metadata_low_risk"] = {
        "value": True if metadata_bucket == "metadata_low_risk" else None,
        "applicable": metadata_available,
    }
    components["metadata_medium_risk"] = {
        "value": True if metadata_bucket == "metadata_medium_risk" else None,
        "applicable": metadata_available,
    }

    # Negative components.
    components["digest_mismatch"] = {
        "value": True if outcome.get("digest_mismatch") is True else None,
        "applicable": source_attempted and not source_root_unavailable,
    }
    components["span_over_cap"] = {
        "value": True if outcome.get("span_over_cap") is True else None,
        "applicable": source_attempted and not source_root_unavailable,
    }
    components["blank_only"] = {
        "value": True if features and features.get("span_blank_only") else None,
        "applicable": features is not None,
    }
    components["comment_only"] = {
        "value": True if features and features.get("span_comment_only_heuristic") else None,
        "applicable": features is not None,
    }
    components["import_only"] = {
        "value": True if features and features.get("import_only_heuristic") else None,
        "applicable": features is not None,
    }
    components["generated_or_vendor_path_kind"] = {
        "value": True if path_kind == "generated_or_vendor" else None,
        "applicable": metadata_available,
    }
    components["unknown_path_kind"] = {
        "value": True if path_kind == "unknown" else None,
        "applicable": metadata_available,
    }
    components["metadata_high_risk"] = {
        "value": True if metadata_bucket == "metadata_high_risk" else None,
        "applicable": metadata_available,
    }
    components["source_feature_high_risk"] = {
        "value": True if source_feature_bucket == "source_feature_high_risk" else None,
        "applicable": source_feature_computed and not source_root_unavailable,
    }
    components["source_feature_unavailable"] = {
        "value": True if source_feature_bucket == "source_feature_unavailable" else None,
        "applicable": source_feature_computed and not source_root_unavailable,
    }

    if metadata_unavailable:
        return False, False, True, components

    if source_backed:
        return True, False, False, components

    # Source is not available but candidate metadata exists -> metadata-only scoring.
    return False, True, False, components


def _bucket_from_score(score: int | None) -> str:
    if score is None:
        return "diagnostic_score_unavailable"
    if score >= 2:
        return "diagnostic_score_high"
    if score >= 0:
        return "diagnostic_score_medium"
    return "diagnostic_score_low"


def _score_bin_label(score: int | None) -> str:
    if score is None:
        return "unavailable"
    if score <= -3:
        return "<=-3"
    if score <= -1:
        return "-2_-1"
    if score <= 1:
        return "0_1"
    if score <= 3:
        return "2_3"
    return ">=4"


def _compute_scores(
    normalized_tasks: list[dict[str, Any]],
    outcomes_by_task_cand: dict[tuple[int, int], dict[str, Any]],
    features_by_task_cand: dict[tuple[int, int], dict[str, Any]],
) -> dict[str, Any]:
    """Compute fixed gold-free diagnostic score buckets and per-candidate metadata."""
    scored: list[dict[str, Any]] = []

    for task_idx, task in enumerate(normalized_tasks):
        risk_tags = task.get("task_risk_tags", [])
        for cand in task.get("_candidates", []):
            cid = cand.get("_id")
            if not isinstance(cid, int):
                continue
            outcome = outcomes_by_task_cand.get((task_idx, cid)) or {}
            features = features_by_task_cand.get((task_idx, cid))
            source_backed, metadata_only, unavailable, components = _compute_score_components(
                outcome, features, cand, risk_tags
            )

            score: int | None = None
            if not unavailable:
                s = 0
                for name in POSITIVE_COMPONENTS:
                    comp = components[name]
                    if comp["applicable"] and comp["value"] is True:
                        s += 1
                for name in NEGATIVE_COMPONENTS:
                    comp = components[name]
                    if comp["applicable"] and comp["value"] is True:
                        s -= 1
                score = s

            bucket = _bucket_from_score(score)
            bin_label = _score_bin_label(score)

            subtype = cand.get("subtype") or {}
            source_class = (
                str(subtype.get("source_class"))
                if isinstance(subtype, dict) and subtype.get("source_class") in p46.SUBTYPE_SOURCE_CLASSES
                else "other"
            )
            agreement_class = (
                str(subtype.get("agreement_class"))
                if isinstance(subtype, dict) and subtype.get("agreement_class") in p46.SUBTYPE_AGREEMENT_CLASSES
                else "other"
            )

            scored.append({
                "task_idx": task_idx,
                "cid": cid,
                "bucket": bucket,
                "score": score,
                "bin_label": bin_label,
                "source_backed": source_backed,
                "metadata_only": metadata_only,
                "unavailable": unavailable,
                "components": components,
                "metadata_bucket": p52._metadata_risk_bucket(cand, risk_tags),
                "source_feature_bucket": p52b._source_feature_bucket(outcome, features, cand, risk_tags)
                if (outcome.get("source_read_success") is not None or outcome.get("source_root_unavailable"))
                else "source_feature_unavailable",
                "path_kind": _as_str(cand.get("path_kind") or "unknown"),
                "source_class": source_class,
                "agreement_class": agreement_class,
                "rrf_backing": "rrf_yes" if p49._has_rrf_backing(cand) else "rrf_no",
                "candidate_strategy": _as_str(cand.get("source_strategy") or "unknown"),
            })

    return {"scored": scored}


def _score_availability(
    scored: list[dict[str, Any]],
    candidate_denominator: int,
    source_read_attempt_count: int,
    source_read_success_count: int,
    bounded_span_feature_candidate_denominator: int,
) -> dict[str, Any]:
    score_candidate_denominator = sum(1 for r in scored if not r["unavailable"])
    source_backed_count = sum(1 for r in scored if r["source_backed"])
    metadata_only_count = sum(1 for r in scored if r["metadata_only"])
    unavailable_count = sum(1 for r in scored if r["unavailable"])

    if candidate_denominator == 0:
        availability = "unavailable_missing_candidate_pool"
    elif source_read_attempt_count == 0:
        if metadata_only_count > 0:
            availability = "partial_metadata_only"
        else:
            availability = "unavailable_no_source_reads"
    elif source_backed_count == score_candidate_denominator and score_candidate_denominator > 0:
        availability = "available_source_backed"
    elif source_backed_count > 0 and metadata_only_count > 0:
        availability = "partial_source_backed"
    elif source_backed_count == 0 and metadata_only_count > 0:
        availability = "partial_metadata_only"
    else:
        availability = "unavailable_no_source_reads"

    reason_counts: dict[str, int] = defaultdict(int)
    for r in scored:
        if r["unavailable"]:
            reason_counts["metadata_unavailable"] += 1
    # When source reads were attempted but a candidate is not source-backed, it
    # is metadata-only, not unavailable, so no extra reason bucket is needed.

    return {
        "p52c_score_availability": availability,
        "candidate_denominator": candidate_denominator,
        "score_candidate_denominator": score_candidate_denominator,
        "source_backed_score_candidate_denominator": source_backed_count,
        "metadata_only_candidate_denominator": metadata_only_count,
        "score_unavailable_candidate_count": unavailable_count,
        "score_unavailable_candidate_rate": _rate(unavailable_count, candidate_denominator),
        "source_read_attempt_count": source_read_attempt_count,
        "source_read_success_count": source_read_success_count,
        "source_read_success_rate": _rate(source_read_success_count, source_read_attempt_count),
        "bounded_span_feature_candidate_denominator": bounded_span_feature_candidate_denominator,
        "source_feature_available_count": bounded_span_feature_candidate_denominator,
        "source_feature_available_rate": _rate(bounded_span_feature_candidate_denominator, candidate_denominator),
        "score_unavailable_reason_counts": dict(reason_counts),
        "score_unavailable_reason_rates": {k: _rate(v, candidate_denominator) for k, v in reason_counts.items()},
    }


def _diagnostic_score_distribution(scored: list[dict[str, Any]]) -> dict[str, Any]:
    score_candidate_denominator = sum(1 for r in scored if not r["unavailable"])
    bucket_counts: dict[str, int] = {b: 0 for b in SCORE_BUCKETS}
    bin_counts: dict[str, int] = dict.fromkeys(SCORE_BINS, 0)
    bin_counts["unavailable"] = 0
    for r in scored:
        bucket_counts[r["bucket"]] += 1
        if r["score"] is None:
            bin_counts["unavailable"] += 1
        else:
            bin_counts[_score_bin_label(r["score"])] += 1

    bucket_rates = {b: _rate(bucket_counts[b], score_candidate_denominator if b != "diagnostic_score_unavailable" else len(scored)) for b in SCORE_BUCKETS}
    # unavailable rate is over all candidates; others over scored candidates.
    bucket_rates = {
        b: _rate(bucket_counts[b], len(scored)) if b == "diagnostic_score_unavailable" else _rate(bucket_counts[b], score_candidate_denominator)
        for b in SCORE_BUCKETS
    }

    component_coverage: dict[str, Any] = {}
    positive_rates: dict[str, Any] = {}
    negative_rates: dict[str, Any] = {}

    all_components = POSITIVE_COMPONENTS + NEGATIVE_COMPONENTS
    for name in all_components:
        applicable = sum(1 for r in scored if r["components"][name]["applicable"])
        positive = sum(
            1
            for r in scored
            if r["components"][name]["applicable"] and r["components"][name]["value"] is True
        )
        # Availability string: if none applicable, it's unavailable for this dataset.
        if applicable == 0:
            availability = "unavailable_not_applicable_for_any_candidate"
        else:
            availability = "available"
        component_coverage[name] = {
            "availability": availability,
            "checkable_count": applicable,
            "checkable_rate": _rate(applicable, len(scored)),
        }
        if name in POSITIVE_COMPONENTS:
            positive_rates[name] = {
                "positive_count": positive,
                "positive_rate": _rate(positive, applicable),
            }
        else:
            negative_rates[name] = {
                "negative_count": positive,  # count of true negatives
                "negative_rate": _rate(positive, applicable),
            }

    return {
        "diagnostic_score_bucket_counts": bucket_counts,
        "diagnostic_score_bucket_rates": bucket_rates,
        "score_bin_distribution": bin_counts,
        "component_coverage": component_coverage,
        "positive_component_rate_by_component": positive_rates,
        "negative_component_rate_by_component": negative_rates,
        "score_candidate_denominator": score_candidate_denominator,
    }


def _breakdowns(
    scored: list[dict[str, Any]],
    normalized_tasks: list[dict[str, Any]],
    packs: dict[tuple[int, str], dict[str, Any]],
) -> dict[str, Any]:
    def make_bucket() -> dict[str, Any]:
        return {
            "candidate_count": 0,
            "source_backed_count": 0,
            "metadata_only_count": 0,
            "unavailable_count": 0,
            "diagnostic_score_high_count": 0,
            "diagnostic_score_medium_count": 0,
            "diagnostic_score_low_count": 0,
            "diagnostic_score_unavailable_count": 0,
        }

    breakdowns: dict[str, dict[str, dict[str, Any]]] = {
        "by_metadata_risk_bucket": defaultdict(make_bucket),
        "by_source_feature_bucket": defaultdict(make_bucket),
        "by_path_kind": defaultdict(make_bucket),
        "by_source_class": defaultdict(make_bucket),
        "by_agreement_class": defaultdict(make_bucket),
        "by_rrf_backing": defaultdict(make_bucket),
        "by_public_bucket": defaultdict(make_bucket),
        "by_public_risk_tag": defaultdict(make_bucket),
        "by_candidate_strategy": defaultdict(make_bucket),
        "by_pack_strategy": defaultdict(make_bucket),
    }

    for r in scored:
        task = normalized_tasks[r["task_idx"]]
        public_bucket = p25.sanitize_public_bucket(task.get("task_bucket", "unknown"))
        risk_tags = task.get("task_risk_tags", [])
        first_tag = risk_tags[0] if risk_tags else "other"

        dims: dict[str, str] = {
            "by_metadata_risk_bucket": r["metadata_bucket"],
            "by_source_feature_bucket": r["source_feature_bucket"],
            "by_path_kind": r["path_kind"],
            "by_source_class": r["source_class"],
            "by_agreement_class": r["agreement_class"],
            "by_rrf_backing": r["rrf_backing"],
            "by_public_bucket": public_bucket,
            "by_public_risk_tag": first_tag,
            "by_candidate_strategy": r["candidate_strategy"],
        }

        # Pack strategy membership is derived from in-memory P49 packs.
        strategies = {
            strategy
            for (tidx, strategy), pack in packs.items()
            if tidx == r["task_idx"] and any(c.get("_id") == r["cid"] for c in pack.get("selected", []))
        }

        for dim_name, dim_value in dims.items():
            b = breakdowns[dim_name][dim_value]
            b["candidate_count"] += 1
            if r["source_backed"]:
                b["source_backed_count"] += 1
            elif r["metadata_only"]:
                b["metadata_only_count"] += 1
            else:
                b["unavailable_count"] += 1
            b[f"{r['bucket']}_count"] += 1

        for strategy in strategies or {"not_in_any_pack"}:
            b = breakdowns["by_pack_strategy"][strategy]
            b["candidate_count"] += 1
            if r["source_backed"]:
                b["source_backed_count"] += 1
            elif r["metadata_only"]:
                b["metadata_only_count"] += 1
            else:
                b["unavailable_count"] += 1
            b[f"{r['bucket']}_count"] += 1

    def finalize_bucket(b: dict[str, Any]) -> dict[str, Any]:
        denom = b["candidate_count"]
        return {
            "candidate_count": denom,
            "source_backed_count": b["source_backed_count"],
            "source_backed_rate": _rate(b["source_backed_count"], denom),
            "metadata_only_count": b["metadata_only_count"],
            "metadata_only_rate": _rate(b["metadata_only_count"], denom),
            "unavailable_count": b["unavailable_count"],
            "unavailable_rate": _rate(b["unavailable_count"], denom),
            "diagnostic_score_high_count": b["diagnostic_score_high_count"],
            "diagnostic_score_high_rate": _rate(b["diagnostic_score_high_count"], denom),
            "diagnostic_score_medium_count": b["diagnostic_score_medium_count"],
            "diagnostic_score_medium_rate": _rate(b["diagnostic_score_medium_count"], denom),
            "diagnostic_score_low_count": b["diagnostic_score_low_count"],
            "diagnostic_score_low_rate": _rate(b["diagnostic_score_low_count"], denom),
            "diagnostic_score_unavailable_count": b["diagnostic_score_unavailable_count"],
            "diagnostic_score_unavailable_rate": _rate(b["diagnostic_score_unavailable_count"], denom),
        }

    result: dict[str, Any] = {}
    for dim_name, dim_map in breakdowns.items():
        result[dim_name] = {k: finalize_bucket(v) for k, v in sorted(dim_map.items())}
    return result


def _score_phase_diagnostic_correlation(
    normalized_tasks: list[dict[str, Any]],
    scored: list[dict[str, Any]],
) -> dict[str, Any]:
    by_bucket: dict[str, dict[str, Any]] = {
        b: {
            "candidate_count": 0,
            "gold_file_count": 0,
            "gold_span_count": 0,
            "file_right_span_wrong_count": 0,
            "no_gold_count": 0,
            "existing_role_delta_sum": 0.0,
            "existing_role_delta_count": 0,
        }
        for b in SCORE_BUCKETS
    }

    for r in scored:
        bucket = r["bucket"]
        task = normalized_tasks[r["task_idx"]]
        label = task.get("label", {})
        by_bucket[bucket]["candidate_count"] += 1

        # Find the candidate object for gold checks.
        cand = next(
            (c for c in task.get("_candidates", []) if c.get("_id") == r["cid"]),
            None,
        )
        if cand is None:
            continue

        if not task.get("has_gold"):
            by_bucket[bucket]["no_gold_count"] += 1
            continue

        in_file = p49._file_in_gold(cand, label)
        in_span = p49._span_overlaps_gold(cand, label)
        if in_file:
            by_bucket[bucket]["gold_file_count"] += 1
        if in_span:
            by_bucket[bucket]["gold_span_count"] += 1
        if in_file and not in_span:
            by_bucket[bucket]["file_right_span_wrong_count"] += 1

        # Existing-role delta: delta SpanF0.5 of llm_span_narrow vs candidate_baseline.
        outcomes = task.get("outcomes", {})
        base = outcomes.get("candidate_baseline") or {}
        narrow = outcomes.get("llm_span_narrow") or {}
        base_score = base.get("span_f0_5")
        narrow_score = narrow.get("span_f0_5")
        if isinstance(base_score, (int, float)) and isinstance(narrow_score, (int, float)):
            by_bucket[bucket]["existing_role_delta_sum"] += float(narrow_score) - float(base_score)
            by_bucket[bucket]["existing_role_delta_count"] += 1

    correlation: dict[str, Any] = {
        "not_used_for_score_construction": True,
        "diagnostic_correlation_only": True,
        "gold_file_rate_by_score_bucket": {},
        "gold_span_rate_by_score_bucket": {},
        "file_right_span_wrong_rate_by_score_bucket": {},
        "no_gold_rate_by_score_bucket": {},
        "existing_role_delta_by_score_bucket_if_available": {},
    }

    for b in SCORE_BUCKETS:
        block = by_bucket[b]
        denom = block["candidate_count"]
        correlation["gold_file_rate_by_score_bucket"][b] = {
            "count": block["gold_file_count"],
            "rate": _rate(block["gold_file_count"], denom),
        }
        correlation["gold_span_rate_by_score_bucket"][b] = {
            "count": block["gold_span_count"],
            "rate": _rate(block["gold_span_count"], denom),
        }
        correlation["file_right_span_wrong_rate_by_score_bucket"][b] = {
            "count": block["file_right_span_wrong_count"],
            "rate": _rate(block["file_right_span_wrong_count"], denom),
        }
        correlation["no_gold_rate_by_score_bucket"][b] = {
            "count": block["no_gold_count"],
            "rate": _rate(block["no_gold_count"], denom),
        }
        if block["existing_role_delta_count"] > 0:
            correlation["existing_role_delta_by_score_bucket_if_available"][b] = round(
                block["existing_role_delta_sum"] / block["existing_role_delta_count"], 6
            )
        else:
            correlation["existing_role_delta_by_score_bucket_if_available"][b] = None

    return correlation


def build_report(
    raw_records: list[dict[str, Any]],
    normalized_tasks: list[dict[str, Any]],
    *,
    self_test: bool,
    elapsed_ms: int,
    status: str,
    reason: str | None,
    input_source_count: int,
    insufficient_input_source_count: int,
    repo_lock_path: Path | None,
    source_root: Path | None,
    p52b_report_path: Path | None,
    p52a_report_path: Path | None,
    p52_report_path: Path | None,
    p49_report_path: Path | None,
    p50_report_path: Path | None,
    p48_report_path: Path | None,
) -> dict[str, Any]:
    repo_resolution, repo_meta = p52a._determine_repo_roots(normalized_tasks, repo_lock_path, source_root)

    candidate_pool_availability = (
        "available"
        if normalized_tasks and all(t.get("has_candidate_pool") for t in normalized_tasks)
        else "partial"
        if normalized_tasks and any(t.get("has_candidate_pool") for t in normalized_tasks)
        else "missing_candidate_pool"
    )
    gold_span_availability = (
        "available"
        if normalized_tasks and all(t.get("has_gold_spans") for t in normalized_tasks if t["has_gold"])
        else "partial"
        if normalized_tasks and any(t.get("has_gold_spans") for t in normalized_tasks if t["has_gold"])
        else "missing_gold_spans"
    )
    reach_metrics_available = (
        candidate_pool_availability != "missing_candidate_pool"
        and gold_span_availability != "missing_gold_spans"
    )
    p31_h1_handoff_detected = bool(
        normalized_tasks and any(t.get("has_candidate_pool") and t.get("has_gold_spans") for t in normalized_tasks)
    )
    p31_h1_handoff_detected_count = sum(
        1 for t in normalized_tasks if t.get("has_candidate_pool") and t.get("has_gold_spans")
    )
    p33b_handoff_detected = bool(normalized_tasks and any(t.get("subtypes") for t in normalized_tasks))
    p33b_handoff_detected_count = sum(1 for t in normalized_tasks if t.get("subtypes"))

    p52b_meta = _read_optional_report(p52b_report_path, "p52b")
    p52a_meta = _read_optional_report(p52a_report_path, "p52a")
    p52_meta = _read_optional_report(p52_report_path, "p52")
    p49_meta = _read_optional_report(p49_report_path, "p49")
    p50_meta = _read_optional_report(p50_report_path, "p50")
    p48_meta = _read_optional_report(p48_report_path, "p48")

    p52a._apply_global_candidate_cap(normalized_tasks)
    outcomes, outcomes_by_task_cand = p52a._compute_source_read_outcomes(normalized_tasks, repo_resolution)

    candidate_denominator = len(outcomes)
    task_denominator = len(normalized_tasks)
    bounded_span_candidates = sum(
        1 for o in outcomes
        if o.get("source_read_success") and o.get("range_valid") and not o.get("span_over_cap")
    )

    features_by_task_cand = p52b._compute_source_shape_features(
        normalized_tasks, repo_resolution, outcomes_by_task_cand
    )
    feature_candidates = len(features_by_task_cand)

    packs = p52a._compute_strategy_packs(normalized_tasks)

    source_materialization_metrics = p52a._source_materialization_metrics(outcomes, candidate_denominator)
    source_read_attempt_count = source_materialization_metrics.get("source_read_attempt_count") or 0
    source_read_success_count = source_materialization_metrics.get("source_read_success_count") or 0
    source_reads_attempted = source_read_attempt_count > 0

    score_result = _compute_scores(normalized_tasks, outcomes_by_task_cand, features_by_task_cand)
    scored = score_result["scored"]

    score_availability = _score_availability(
        scored,
        candidate_denominator,
        source_read_attempt_count,
        source_read_success_count,
        bounded_span_candidates,
    )
    score_distribution = _diagnostic_score_distribution(scored)
    breakdowns = _breakdowns(scored, normalized_tasks, packs)
    score_phase_correlation = _score_phase_diagnostic_correlation(normalized_tasks, scored)

    metric_blocks: dict[str, Any] = {
        "score_availability": score_availability,
        "diagnostic_score_distribution": score_distribution,
        "breakdowns": breakdowns,
        "score_phase_diagnostic_correlation": score_phase_correlation,
    }

    conclusion_lines: list[str] = []
    if status not in {"ok", "self_test_only"}:
        conclusion_lines.append(
            "P52C Diagnostic Local Verifier Scoring Simulator is ready; real per-task ephemeral P25 records are required."
        )
        if reason:
            conclusion_lines.append(reason)
    else:
        if self_test:
            conclusion_lines.append(
                f"Self-test-only diagnostic scoring simulator scored {candidate_denominator} synthetic candidates across {task_denominator} tasks; this is not quality evidence."
            )
        else:
            conclusion_lines.append(
                f"P52C computed diagnostic score buckets for {candidate_denominator} candidates across {task_denominator} real ephemeral P25 records."
            )
        conclusion_lines.append(
            "P52C scores are deterministic, gold-free diagnostic buckets only. "
            "They are not Evidence, do not produce a verifier pass/fail, do not admit candidates, "
            "and do not claim default/promotion. Source reads are bounded and aggregate-only when available."
        )
        conclusion_lines.append(
            f"Score availability: `{score_availability['p52c_score_availability']}`; "
            f"source-backed scored candidates: {score_availability['source_backed_score_candidate_denominator']}; "
            f"metadata-only scored candidates: {score_availability['metadata_only_candidate_denominator']}; "
            f"unavailable: {score_availability['score_unavailable_candidate_count']}."
        )

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "generated_by": GENERATED_BY,
        "stage": STAGE,
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
        "score_not_evidence": True,
        "verifier_score_not_admission": True,
        "materialized_candidate_not_evidence": True,
        "source_feature_not_evidence": True,
        "local_verifier_score_available": False,
        "remote_calls_by_p52c": 0,
        "llm_calls_by_p52c": 0,
        "prompt_construction_by_p52c": False,
        "source_reads_attempted_by_p52c": source_reads_attempted,
        "source_reads_bounded_by_p52c": True,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_source_stored": False,
        "raw_text_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_sent_to_provider": False,
        "raw_snippets_committed": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "private_labels_committed": False,
        "provider_keys_in_artifact": False,
        "gold_spans_in_artifact": False,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "elapsed_ms": elapsed_ms,
        "task_count": task_denominator,
        "positive_task_count": sum(1 for t in normalized_tasks if t["has_gold"]),
        "no_gold_task_count": sum(1 for t in normalized_tasks if not t["has_gold"]),
        "candidate_pool_availability": candidate_pool_availability,
        "gold_span_availability": gold_span_availability,
        "reach_metrics_available": reach_metrics_available,
        "p31_h1_handoff_detected": p31_h1_handoff_detected,
        "p31_h1_handoff_detected_count": p31_h1_handoff_detected_count,
        "p33b_handoff_detected": p33b_handoff_detected,
        "p33b_handoff_detected_count": p33b_handoff_detected_count,
        **p52b_meta,
        **p52a_meta,
        **p52_meta,
        **p49_meta,
        **p50_meta,
        **p48_meta,
        "metrics": metric_blocks,
        "conclusion": conclusion_lines,
        "validation": {"forbidden_key_scan_ok": True},
    }

    errors = validate_public_report(report)
    if errors:
        raise RuntimeError(f"P52C public report validation failed: {errors}")
    return report


def validate_public_report(report: dict[str, Any]) -> list[str]:
    """Validate schema, safety flags, and recursive forbidden-key scan."""
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version mismatch")
    if report.get("remote_calls_by_p52c") != 0:
        errors.append("remote_calls_by_p52c must be 0")
    if report.get("llm_calls_by_p52c") != 0:
        errors.append("llm_calls_by_p52c must be 0")
    if report.get("prompt_construction_by_p52c") is not False:
        errors.append("prompt_construction_by_p52c must be false")
    if report.get("source_reads_bounded_by_p52c") is not True:
        errors.append("source_reads_bounded_by_p52c must be true")

    expected_flags = {
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "score_not_evidence": True,
        "verifier_score_not_admission": True,
        "materialized_candidate_not_evidence": True,
        "source_feature_not_evidence": True,
        "local_verifier_score_available": False,
        "aggregate_only_public_artifact": True,
        "score_phase_only_metrics": True,
        "raw_prompts_stored": False,
        "raw_query_stored": False,
        "raw_responses_stored": False,
        "raw_source_stored": False,
        "raw_text_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "raw_snippets_sent_to_provider": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
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
    if isinstance(x, float):
        return f"{x:.4f}"
    if isinstance(x, int):
        return str(x)
    return "n/a"


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [f"# {STAGE}\n"]
    lines.extend([
        f"- Schema: `{report['schema_version']}`",
        f"- Generated: {report['generated_at']}",
        f"- Status: `{report['status']}`",
        f"- Self-test: {report['self_test']}",
        f"- Remote calls by P52C: {report['remote_calls_by_p52c']}",
        f"- LLM calls by P52C: {report['llm_calls_by_p52c']}",
        f"- Prompt construction by P52C: {report['prompt_construction_by_p52c']}",
        f"- Source reads attempted by P52C: {report['source_reads_attempted_by_p52c']}",
        f"- Source reads bounded by P52C: {report['source_reads_bounded_by_p52c']}",
        f"- Local verifier score available: {report['local_verifier_score_available']}",
        f"- Tasks: {report['task_count']} positive={report['positive_task_count']} no_gold={report['no_gold_task_count']}",
        f"- Candidate pool availability: `{report['candidate_pool_availability']}`",
        f"- P52B report source: `{report.get('p52b_report_source')}`",
        f"- P52A report source: `{report.get('p52a_report_source')}`",
        f"- P52 report source: `{report.get('p52_report_source')}`",
        f"- P49 report source: `{report.get('p49_report_source')}`\n",
    ])

    if report["status"] not in {"ok", "self_test_only"}:
        lines.extend(["## Status", report.get("status_reason") or "", "", "Run with `--self-test` or supply ephemeral P25-policy records and a repo root.", ""])
        return "\n".join(lines)

    lines.extend([
        "## Purpose\n",
        "P52C computes deterministic, gold-free diagnostic score buckets from P52B source-backed features, P52A materialization outcomes, and P52/P49 metadata. "
        "It is a SCORE-phase-only scoring simulator, not a verifier pass/fail phase, not Evidence, and not an admission/default/promotion stage.",
        "",
        "## Methodology\n",
        "- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).",
        "- Normalize candidates with P46/P49 helpers and resolve bounded repo roots with P52A helpers.",
        "- Recompute bounded source outcomes and source-shape features through existing P52A/P52B helpers.",
        "- Build the fixed gold-free formula `p52c_diagnostic_score_v0` from positive and negative components; unavailable components are not counted.",
        "- Emit only aggregate score buckets (`high`, `medium`, `low`, `unavailable`) and binned score distribution; no raw candidate scores are published.",
        "- Break down aggregated counts/rates by safe public dimensions (metadata/source-feature buckets, path kind, subtype axes, RRF backing, public bucket/risk tag, strategy, pack strategy).",
        "- Gold spans and existing P21 role outcomes are used only inside `score_phase_diagnostic_correlation` after score buckets are fixed.",
        "",
        "## Safety notes\n",
        "- P52C does not call an LLM, construct prompts, or make remote calls.",
        "- P52C does not produce a verifier pass/fail or local-verifier admission score.",
        "- P52C scores are not Evidence and do not prove P51/P53 quality.",
        "- Source reads are bounded and aggregate-only when available.",
        "- Raw source, snippets, paths, spans, digests, task/candidate identifiers, queries, and provider keys are never stored.",
        "",
    ])

    sa = report["metrics"]["score_availability"]
    lines.append("## Score availability\n")
    lines.append(f"- Availability enum: `{sa['p52c_score_availability']}`")
    lines.append(f"- Candidate denominator: {sa['candidate_denominator']}")
    lines.append(f"- Score candidate denominator: {sa['score_candidate_denominator']}")
    lines.append(f"- Source-backed score candidate denominator: {sa['source_backed_score_candidate_denominator']}")
    lines.append(f"- Metadata-only candidate denominator: {sa['metadata_only_candidate_denominator']}")
    lines.append(f"- Score unavailable count/rate: {sa['score_unavailable_candidate_count']} / {_fmt_scalar(sa['score_unavailable_candidate_rate'])}")
    lines.append(f"- Source read attempts/success: {sa['source_read_attempt_count']} / {sa['source_read_success_count']} ({_fmt_scalar(sa['source_read_success_rate'])})")
    lines.append(f"- Bounded-span feature candidate denominator: {sa['bounded_span_feature_candidate_denominator']}")
    lines.append("")

    dd = report["metrics"]["diagnostic_score_distribution"]
    lines.append("## Diagnostic score distribution\n")
    lines.append("| Bucket | Count | Rate |")
    lines.append("|---|---:|---:|")
    for b in SCORE_BUCKETS:
        lines.append(f"| {b} | {dd['diagnostic_score_bucket_counts'][b]} | {_fmt_scalar(dd['diagnostic_score_bucket_rates'][b])} |")
    lines.append("")
    lines.append("### Score bin distribution\n")
    lines.append("| Bin | Count |")
    lines.append("|---|---:|")
    for bin_label in SCORE_BINS:
        lines.append(f"| {bin_label} | {dd['score_bin_distribution'].get(bin_label, 0)} |")
    if dd["score_bin_distribution"].get("unavailable"):
        lines.append(f"| unavailable | {dd['score_bin_distribution']['unavailable']} |")
    lines.append("")

    lines.append("### Positive component rates\n")
    lines.append("| Component | Checkable | Positive Rate |")
    lines.append("|---|---|---:|")
    for name in POSITIVE_COMPONENTS:
        cov = dd["component_coverage"][name]
        rate = dd["positive_component_rate_by_component"][name]["positive_rate"]
        lines.append(f"| {name} | {cov['checkable_count']} | {_fmt_scalar(rate)} |")
    lines.append("")

    lines.append("### Negative component rates\n")
    lines.append("| Component | Checkable | Negative Rate |")
    lines.append("|---|---|---:|")
    for name in NEGATIVE_COMPONENTS:
        cov = dd["component_coverage"][name]
        rate = dd["negative_component_rate_by_component"][name]["negative_rate"]
        lines.append(f"| {name} | {cov['checkable_count']} | {_fmt_scalar(rate)} |")
    lines.append("")

    sp = report["metrics"]["score_phase_diagnostic_correlation"]
    lines.append("## SCORE-phase diagnostic correlation (not used for score construction)\n")
    lines.append("| Bucket | GoldFile Count | GoldFile | GoldSpan | FileRightSpanWrong | NoGold | ExistingRoleDelta |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    for b in SCORE_BUCKETS:
        lines.append(
            f"| {b} | {sp['gold_file_rate_by_score_bucket'][b]['count']} | "
            f"{_fmt_scalar(sp['gold_file_rate_by_score_bucket'][b]['rate'])} | "
            f"{_fmt_scalar(sp['gold_span_rate_by_score_bucket'][b]['rate'])} | "
            f"{_fmt_scalar(sp['file_right_span_wrong_rate_by_score_bucket'][b]['rate'])} | "
            f"{_fmt_scalar(sp['no_gold_rate_by_score_bucket'][b]['rate'])} | "
            f"{_fmt_scalar(sp['existing_role_delta_by_score_bucket_if_available'][b])} |"
        )
    lines.append("")

    lines.append("## Conclusion\n")
    for line in report["conclusion"]:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=STAGE)
    parser.add_argument("--self-test", action="store_true", help="Run deterministic synthetic self-test.")
    parser.add_argument("--input", nargs="+", type=Path, help="Paths to ephemeral P25-policy JSON record files.")
    parser.add_argument("--repo-lock", type=Path, default=None, help="Repo lock JSON mapping repo_id -> source path.")
    parser.add_argument("--source-root", type=Path, default=None, help="Optional fallback repo root for all tasks.")
    parser.add_argument("--p52b-report", type=Path, default=None, help="Optional P52B report for enum/status carry-forward.")
    parser.add_argument("--p52a-report", type=Path, default=None, help="Optional P52A report for enum/status carry-forward.")
    parser.add_argument("--p52-report", type=Path, default=None, help="Optional P52 report for enum/status carry-forward.")
    parser.add_argument("--p49-report", type=Path, default=None, help="Optional P49 report for enum/status carry-forward.")
    parser.add_argument("--p50-report", type=Path, default=None, help="Optional P50 report for enum/status carry-forward.")
    parser.add_argument("--p48-report", type=Path, default=None, help="Optional P48 report for enum/status carry-forward.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output JSON path.")
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC, help="Output markdown path.")
    args = parser.parse_args()

    start = time.monotonic()
    input_paths: list[Path] = []
    raw_input_records: list[dict[str, Any]] = []
    self_test_lock: Path | None = None
    self_test_root: Path | None = None

    if args.self_test:
        input_paths.append(Path("self_test"))
        raw_input_records, self_test_lock, self_test_root = p52a._make_self_test_inputs()
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
        "_p25_input_summary_marker": "Aggregate summary lacks per-task ephemeral records required for P52C diagnostic scoring.",
        "_p25_input_empty_marker": "Input artifact did not contain per-task ephemeral records.",
        "_p25_unsupported_schema_marker": "P52C requires p25-policy-records-ephemeral-v1 input schema.",
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

    normalized_tasks, raw_records = p52a._normalize_tasks(task_records)
    p52a._enrich_candidates_with_digest(raw_records, normalized_tasks)

    if status == "ok" and not normalized_tasks:
        status = "insufficient_task_detail"
        reason = "Records lacked required fields for P52C normalization."

    repo_lock_path = args.repo_lock or self_test_lock
    source_root = args.source_root or self_test_root

    elapsed_ms = int((time.monotonic() - start) * 1000)

    report = build_report(
        raw_records,
        normalized_tasks,
        self_test=args.self_test,
        elapsed_ms=elapsed_ms,
        status=status,
        reason=reason,
        input_source_count=1 if args.self_test else max(1, len(args.input or [])),
        insufficient_input_source_count=insufficient_count,
        repo_lock_path=repo_lock_path,
        source_root=source_root,
        p52b_report_path=args.p52b_report,
        p52a_report_path=args.p52a_report,
        p52_report_path=args.p52_report,
        p49_report_path=args.p49_report,
        p50_report_path=args.p50_report,
        p48_report_path=args.p48_report,
    )

    _write_json(args.out, report)
    md = build_markdown(report)
    args.doc.parent.mkdir(parents=True, exist_ok=True)
    args.doc.write_text(md, encoding="utf-8")

    print(f"P52C report written to {args.out}")
    print(f"P52C markdown written to {args.doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
