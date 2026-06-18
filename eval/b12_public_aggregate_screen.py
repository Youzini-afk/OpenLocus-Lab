#!/usr/bin/env python3
"""B12 Public Aggregate Mechanism Screen (bounded).

This is a **bounded public-aggregate mechanism screen**, NOT a full B12
per-record mechanism decomposition. Full B12 (the frozen preregistration in
``eval/b12_mechanism_decomposition.py`` and
``docs/en/b12-mechanism-decomposition.md``) requires per-record P21 outcomes,
ambiguous-subset membership, and the deterministic (B) / random (E) LLM-call
reduction ablation controls. None of those are present in the public B11
aggregate report, so the full B12 hypothesis support/refute criteria cannot be
applied here.

What this screen DOES: read the already-published B11 aggregate report
(``artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json``)
and emit a per-hypothesis *screen status* for H1-H4 derived strictly from
aggregate deltas. The screen preserves the public-artifact contract:

* **no** raw records, source, prompts, responses, snippets, digests, paths, or
  private labels are read or emitted;
* **no** provider calls (``new_provider_calls == 0``);
* **no** policy search, threshold tuning, or winner selection;
* **no** promotion / default / runtime-clean general algorithm claim.

The screen emits **per-hypothesis statuses**, never a single global
``supported`` verdict. Per the explorer/oracle finding, full B12 replay is
impossible from the current public artifacts; this screen is the strongest
honest conclusion that can be drawn from public aggregates alone.

Run::

    python3 eval/b12_public_aggregate_screen.py --self-test
    python3 eval/b12_public_aggregate_screen.py \
        --input artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import b6_lite_interpretable_policy_search as b6lite  # noqa: E402

SCHEMA_VERSION = "b12-public-aggregate-mechanism-screen-v0"
GENERATED_BY = "b12_public_aggregate_screen"
CLAIM_LEVEL = "bounded_public_aggregate_mechanism_screen_of_b11_aggregate"
INPUT_B11_SCHEMA = "b11-prospective-matrix-aggregate-report-v0"
POLICY_UNDER_ANALYSIS = "balanced_v1"
BASELINE_FOR_DELTAS = "p25"

# Predeclared criteria (mirror the frozen B12 preregistration thresholds so the
# screen applies the SAME numeric gates as full B12; only the input resolution
# is coarser — aggregate deltas instead of per-record ablation deltas).
APPROX_EQUAL_THRESHOLD = 0.02
H4_MODEL_FAMILY_SPREAD_THRESHOLD = 0.05

HYPOTHESES = (
    "H1_ambiguous_routing",
    "H2_llm_call_reduction",
    "H3_p25_fallback_sufficiency",
    "H4_model_specific",
)

# Testability gaps that block full B12 from the current public artifact. Each
# entry is a self-contained reason; the screen explicitly lists these so a
# reader cannot mistake a screen status for a full B12 verdict.
TESTABILITY_GAPS = (
    {
        "gap_id": "no_per_record_route_decisions_in_public_artifact",
        "description": (
            "public B11 aggregate reports route-decision counts only at the "
            "policy level; per-record ambiguous-vs-p25 decisions are absent, "
            "so H1 A greater than B, E, D per-record criteria cannot evaluate"
        ),
    },
    {
        "gap_id": "no_ambiguous_subset_membership_in_public_artifact",
        "description": (
            "the public aggregate does not identify which records fell into "
            "the ambiguous subset, so ablation variants B, C, E cannot be "
            "reconstructed by subset selection"
        ),
    },
    {
        "gap_id": "no_deterministic_call_reduction_variant_B_in_public_artifact",
        "description": (
            "variant B (P25 for all but skip LLM for ambiguous tasks via "
            "candidate_baseline) is not a published policy in the B11 "
            "matrix, so H1 A greater than B and H2 routing-vs-reduction "
            "comparisons cannot be made"
        ),
    },
    {
        "gap_id": "no_random_call_reduction_variant_E_in_public_artifact",
        "description": (
            "variant E (P25 for all but randomly skip the same number of "
            "LLM calls as A) is not published; without E the H2 A approx E "
            "criterion cannot be evaluated, so H2 causal mechanism remains "
            "inconclusive even though reduced_calls_observed holds"
        ),
    },
    {
        "gap_id": "no_weak_candidate_only_outcomes_in_public_artifact",
        "description": (
            "weak_candidate_only per-strategy outcomes (the substrate the "
            "ambiguous-routing rule selects) are not in the public "
            "aggregate, so the routing-rule contribution cannot be isolated"
        ),
    },
)

DEFAULT_INPUT = Path(
    "artifacts/b11_prospective_matrix/"
    "b11_prospective_matrix_aggregate_report.json"
)
DEFAULT_OUT = Path(
    "artifacts/b12_mechanism_decomposition/"
    "b12_public_aggregate_screen_report.json"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _round6(value: float) -> float:
    return round(float(value), 6)


def _abs_within(a: float, b: float, threshold: float) -> bool:
    return abs(a - b) <= threshold


def _base_report(self_test: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now(),
        "claim_level": CLAIM_LEVEL,
        "self_test": bool(self_test),
        "input_b11_schema_version": INPUT_B11_SCHEMA,
        "policy_under_analysis": POLICY_UNDER_ANALYSIS,
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        # Safety fields (must be preserved verbatim).
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        # Forbidden content never read or emitted.
        "candidate_ids_in_artifact": False,
        "task_ids_in_artifact": False,
        "raw_repo_ids_in_artifact": False,
        "run_ids_in_artifact": False,
        "raw_paths_in_artifact": False,
        "raw_line_ranges_in_artifact": False,
        "raw_digests_in_artifact": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_stored": False,
        "raw_snippets_committed": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "llm_output_not_evidence": True,
        "not_evidence": True,
        "promotion_declared": False,
        "default_recommendation_declared": False,
        "winner_declared": False,
        # Bounded-screen stance.
        "is_full_b12_mechanism_decomposition": False,
        "full_b12_replay_possible_from_public_artifact": False,
        "per_hypothesis_status_only_no_global_supported_verdict": True,
    }


def _finalize_safety(report: dict[str, Any]) -> None:
    """Run the forbidden-key/value scan on the public output."""
    violations = b6lite._walk_forbidden(report)
    integrity = report.setdefault("integrity", {})
    integrity["forbidden_public_key_scan_clean"] = not violations
    if violations:
        raise ValueError(
            "b12-public-aggregate-screen public output would contain "
            f"forbidden keys/values; first violations: {violations[:5]}"
        )


def _validate_b11_aggregate(report: dict[str, Any]) -> None:
    """Validate that the input B11 aggregate report is a public artifact."""
    if report.get("schema_version") != INPUT_B11_SCHEMA:
        raise ValueError(
            f"unexpected B11 schema_version: {report.get('schema_version')!r}"
        )
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError("B11 input must be aggregate_only_public_artifact=true")
    if report.get("promotion_ready") is not False:
        raise ValueError("B11 input must have promotion_ready=false")
    if report.get("policy_search_performed") is not False:
        raise ValueError("B11 input must have policy_search_performed=false")
    if report.get("candidate_not_fact") is not True:
        raise ValueError("B11 input must have candidate_not_fact=true")
    if report.get("baseline_for_deltas") != BASELINE_FOR_DELTAS:
        raise ValueError("B11 input must have baseline_for_deltas=p25")
    if report.get("policy_under_validation") != POLICY_UNDER_ANALYSIS:
        raise ValueError(
            "B11 input must have policy_under_validation=balanced_v1"
        )
    if report.get("default_should_change") is not False:
        raise ValueError("B11 input must have default_should_change=false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "B11 input must have evidencecore_semantics_changed=false"
        )
    if report.get("quality_strategy_tuned") is not False:
        raise ValueError("B11 input must have quality_strategy_tuned=false")
    if report.get("new_provider_calls") != 0:
        raise ValueError("B11 input must have new_provider_calls=0")
    deltas = report.get("deltas_balanced_v1_vs_p25")
    if not isinstance(deltas, dict):
        raise ValueError("B11 input missing deltas_balanced_v1_vs_p25 dict")
    for metric in ("gold_span", "span_f0_5", "model_calls"):
        if metric not in deltas:
            raise ValueError(f"B11 input deltas missing metric: {metric}")
    per_model = report.get("per_model_family")
    if not isinstance(per_model, dict) or not per_model:
        raise ValueError("B11 input missing per_model_family dict")


def _family_gold_deltas(b11: dict[str, Any]) -> dict[str, float]:
    """Extract per-model-family balanced_v1-vs-p25 gold_span deltas."""
    per_model = b11.get("per_model_family", {})
    out: dict[str, float] = {}
    for family, entry in per_model.items():
        if not isinstance(entry, dict):
            continue
        d = entry.get("delta_balanced_v1_vs_p25", {})
        out[family] = _as_float(d.get("gold_span", 0.0))
    return out


def _family_gold_spread(family_deltas: dict[str, float]) -> dict[str, Any]:
    """Worst-case spread across model families on the gold_span delta."""
    if not family_deltas:
        return {
            "min_delta": 0.0,
            "max_delta": 0.0,
            "spread": 0.0,
            "per_model_family": {},
        }
    vals = list(family_deltas.values())
    return {
        "min_delta": _round6(min(vals)),
        "max_delta": _round6(max(vals)),
        "spread": _round6(max(vals) - min(vals)),
        "per_model_family": {k: _round6(v) for k, v in family_deltas.items()},
    }


def _kimi_failure_slice(b11: dict[str, Any]) -> dict[str, Any]:
    """Surface the sanitized Kimi py_fastapi failure slice (already public)."""
    failure_slices = b11.get("failure_slices_sanitized", []) or []
    kimi_slice = None
    for entry in failure_slices:
        if (
            isinstance(entry, dict)
            and entry.get("model_family") == "kimi"
            and entry.get("repo_slice_id") == "py_fastapi"
        ):
            kimi_slice = entry
            break
    return {
        "kimi_py_fastapi_failure_present": kimi_slice is not None,
        "failure_slice": kimi_slice,
    }


def _screen_h1(b11: dict[str, Any]) -> dict[str, Any]:
    """H1 ambiguous routing screen.

    Full B12 H1 requires A>D, A>E, A>B per-record on gold_span AND span_f0_5.
    The public aggregate contains none of: per-record route decisions,
    ambiguous subset membership, ablation variants B and E. Therefore H1 is
    inconclusive at the public-aggregate level. This screen does NOT claim H1
    support.
    """
    return {
        "hypothesis": "H1_ambiguous_routing",
        "screen_status": "inconclusive_unavailable_ablation_controls",
        "screen_status_reason": (
            "full B12 H1 per-record criteria (A greater than D, E, B on "
            "gold_span and span_f0_5) need route decisions, ambiguous "
            "subset, and variants B and E; none are in the public B11 "
            "aggregate. Screen does NOT claim H1 support."
        ),
        "h1_support_claimed": False,
        "h1_refutation_claimed": False,
        "blocking_testability_gaps": [
            "no_per_record_route_decisions_in_public_artifact",
            "no_ambiguous_subset_membership_in_public_artifact",
            "no_deterministic_call_reduction_variant_B_in_public_artifact",
            "no_random_call_reduction_variant_E_in_public_artifact",
            "no_weak_candidate_only_outcomes_in_public_artifact",
        ],
    }


def _screen_h2(b11: dict[str, Any]) -> dict[str, Any]:
    """H2 LLM call reduction screen.

    The aggregate does show balanced_v1 reduced model_calls vs P25, so the
    descriptive observation `reduced_calls_observed` holds. But the causal
    mechanism (is it specifically call reduction, vs the routing rule, vs P25
    fallback) is inconclusive without ablation controls B (deterministic) and
    E (random). This screen does NOT claim H2 causal support.
    """
    deltas = b11.get("deltas_balanced_v1_vs_p25", {})
    model_calls_delta = _as_float(deltas.get("model_calls", 0.0))
    reduced_calls_observed = model_calls_delta < 0.0
    if reduced_calls_observed:
        reason = (
            "balanced_v1 vs P25 model_calls delta is negative, so "
            "reduced_calls_observed holds descriptively. But H2 causal "
            "claim (A approx E and A greater than D) cannot be evaluated "
            "without variant E. Screen does NOT claim H2 causal support."
        )
    else:
        reason = (
            "balanced_v1 vs P25 model_calls delta is not negative, so even "
            "the descriptive reduced_calls_observed condition is absent. "
            "H2 causal claim still cannot be evaluated without variant E. "
            "Screen does NOT claim H2 causal support."
        )
    return {
        "hypothesis": "H2_llm_call_reduction",
        "screen_status": (
            "reduced_calls_observed_causal_mechanism_inconclusive"
            if reduced_calls_observed
            else "no_reduced_calls_observed_causal_mechanism_inconclusive"
        ),
        "screen_status_reason": reason,
        "h2_support_claimed": False,
        "h2_causal_support_claimed": False,
        "reduced_calls_observed": bool(reduced_calls_observed),
        "model_calls_delta_balanced_v1_vs_p25": _round6(model_calls_delta),
        "blocking_testability_gaps": [
            "no_deterministic_call_reduction_variant_B_in_public_artifact",
            "no_random_call_reduction_variant_E_in_public_artifact",
            "no_per_record_route_decisions_in_public_artifact",
        ],
    }


def _screen_h3(b11: dict[str, Any]) -> dict[str, Any]:
    """H3 P25 fallback sufficiency screen.

    H3 full criteria require per-record D~=A on gold_span AND span_f0_5. The
    public aggregate only permits an overall-mean primary-parity check:
    balanced_v1 vs P25 gold_span and span_f0_5 deltas within +/-0.02. If both
    primary metrics are within parity, the screen status is
    `aggregate_primary_parity_supported` (consistent with H3 at the aggregate
    level). This is NOT a full H3 supported verdict: per-record fallback
    sufficiency cannot be concluded from aggregate deltas alone.
    """
    deltas = b11.get("deltas_balanced_v1_vs_p25", {})
    gold_delta = _as_float(deltas.get("gold_span", 0.0))
    spanf05_delta = _as_float(deltas.get("span_f0_5", 0.0))
    gold_within = _abs_within(gold_delta, 0.0, APPROX_EQUAL_THRESHOLD)
    spanf05_within = _abs_within(spanf05_delta, 0.0, APPROX_EQUAL_THRESHOLD)
    aggregate_primary_parity = gold_within and spanf05_within
    return {
        "hypothesis": "H3_p25_fallback_sufficiency",
        "screen_status": (
            "aggregate_primary_parity_supported_consistent_with_h3"
            if aggregate_primary_parity
            else "aggregate_primary_parity_not_supported"
        ),
        "screen_status_reason": (
            "balanced_v1 vs P25 gold_span and span_f0_5 deltas are within "
            "the approx-equality threshold, consistent with H3 at the "
            "AGGREGATE primary-parity level. NOT a full H3 verdict: "
            "per-record fallback sufficiency cannot be concluded from "
            "aggregate deltas alone."
        ),
        "h3_support_claimed": False,
        "h3_refutation_claimed": False,
        "aggregate_primary_parity_supported": bool(aggregate_primary_parity),
        "gold_span_delta_balanced_v1_vs_p25": _round6(gold_delta),
        "span_f0_5_delta_balanced_v1_vs_p25": _round6(spanf05_delta),
        "approx_equal_threshold": APPROX_EQUAL_THRESHOLD,
        "blocking_testability_gaps": [
            "no_per_record_route_decisions_in_public_artifact",
            "no_ambiguous_subset_membership_in_public_artifact",
            "no_weak_candidate_only_outcomes_in_public_artifact",
        ],
    }


def _screen_h4(b11: dict[str, Any]) -> dict[str, Any]:
    """H4 model-specific behavior screen.

    Full B12 H4 uses the worst-case model-family spread on the A-D gold_span
    delta, supported if spread > 0.05. The public aggregate exposes per-family
    balanced_v1-vs-p25 gold_span deltas, so the family-level spread criterion
    CAN be evaluated. If the spread is below 0.05, H4 is not_supported under
    the predeclared family-level criterion. However model x repo interaction
    remains inconclusive because the Kimi py_fastapi failure slice cannot be
    disentangled from model-family main effect without per-record data. The
    screen does NOT claim H4 is fully refuted.
    """
    family_deltas = _family_gold_deltas(b11)
    spread_info = _family_gold_spread(family_deltas)
    kimi_failure = _kimi_failure_slice(b11)
    spread = spread_info["spread"]
    family_level_not_supported = spread <= H4_MODEL_FAMILY_SPREAD_THRESHOLD
    if family_level_not_supported:
        reason = (
            "per-family gold_span delta spread is at or below the "
            "family-level threshold, so H4 is NOT supported under the "
            "gold-span criterion. NOT a full H4 refutation: Kimi "
            "py_fastapi failure leaves model x repo interaction "
            "inconclusive without per-record data."
        )
    else:
        reason = (
            "per-family gold_span delta spread exceeds the family-level "
            "threshold, so H4 receives aggregate family-spread support. "
            "This is NOT a full model-specific mechanism proof: model x "
            "repo interaction remains inconclusive without per-record data."
        )
    return {
        "hypothesis": "H4_model_specific",
        "screen_status": (
            "family_gold_spread_not_supported_model_repo_interaction_inconclusive"
            if family_level_not_supported
            else "family_gold_spread_supported_model_repo_interaction_inconclusive"
        ),
        "screen_status_reason": reason,
        "h4_support_claimed": False,
        "h4_full_refutation_claimed": False,
        "family_level_gold_spread_not_supported": bool(family_level_not_supported),
        "family_level_gold_spread_supported": not family_level_not_supported,
        "model_repo_interaction_inconclusive": bool(
            kimi_failure["kimi_py_fastapi_failure_present"]
        ),
        "family_gold_span_delta_spread": spread_info,
        "spread_threshold": H4_MODEL_FAMILY_SPREAD_THRESHOLD,
        "kimi_py_fastapi_failure_slice_present": kimi_failure[
            "kimi_py_fastapi_failure_present"
        ],
        "blocking_testability_gaps": [
            "no_per_record_route_decisions_in_public_artifact",
            "no_ambiguous_subset_membership_in_public_artifact",
            "no_weak_candidate_only_outcomes_in_public_artifact",
        ],
    }


def screen(b11_aggregate: dict[str, Any], self_test: bool = False) -> dict[str, Any]:
    """Build the B12 public aggregate mechanism screen report.

    ``b11_aggregate`` is the parsed B11 aggregate report JSON. ``self_test``
    flags that the report was produced from a synthetic fixture.
    """
    _validate_b11_aggregate(b11_aggregate)

    report = _base_report(self_test)
    report["source_artifact_public_note"] = (
        "already-published aggregate-only public B11 matrix aggregate "
        "report; no raw records, paths, prompts, responses, snippets, or "
        "private labels read by the screen"
    )

    # Carry the public-level B11 framing fields (no raw data).
    report["input_b11_summary"] = {
        "run_count": b11_aggregate.get("run_count"),
        "record_count_total": b11_aggregate.get("record_count_total"),
        "aggregate_verdict": b11_aggregate.get("aggregate_verdict"),
        "aggregate_verdict_reason": b11_aggregate.get("aggregate_verdict_reason"),
        "baseline_for_deltas": b11_aggregate.get("baseline_for_deltas"),
        "policy_under_validation": b11_aggregate.get("policy_under_validation"),
        "public_model_family_count": b11_aggregate.get(
            "public_model_family_count"
        ),
        "public_repo_slice_count": b11_aggregate.get("public_repo_slice_count"),
        "b10b_runtime_shadow_verdict": (
            b11_aggregate.get("b10b_runtime_shadow_summary", {}) or {}
        ).get("verdict"),
        "b10b_pending_due_denominator": (
            b11_aggregate.get("b10b_runtime_shadow_summary", {}) or {}
        ).get("pending_due_denominator"),
    }

    # Per-hypothesis screen statuses (NO single global supported verdict).
    h1 = _screen_h1(b11_aggregate)
    h2 = _screen_h2(b11_aggregate)
    h3 = _screen_h3(b11_aggregate)
    h4 = _screen_h4(b11_aggregate)
    hypothesis_results = {
        h["hypothesis"]: h for h in (h1, h2, h3, h4)
    }

    # Testability section: explicit list of controls missing for full B12.
    testability = {
        "full_b12_possible_from_public_artifact": False,
        "missing_controls_for_full_b12": list(TESTABILITY_GAPS),
        "note": (
            "Full B12 mechanism decomposition cannot be replayed from the "
            "current public B11 aggregate. The listed controls are the "
            "specific missing inputs. Until available via future "
            "ephemeral-record B12 replay, only this bounded aggregate "
            "screen is publishable."
        ),
    }

    # Recommended next step (cautious, no auto-promotion).
    recommended_next_step = {
        "primary": "future_ephemeral_record_b12_replay",
        "secondary": "b13_robust_policy_search_with_caution",
        "reason": (
            "Either run full B12 against ephemeral P21 records from B11 "
            "live runs once available, or proceed cautiously to B13 "
            "distributionally robust policy search understanding that "
            "balanced_v1 gains have NOT been causally decomposed."
        ),
        "next_step_authorizes_promotion": False,
        "next_step_authorizes_default_change": False,
        "next_step_authorizes_runtime_clean_algorithm": False,
    }

    report.update(
        {
            "hypotheses": list(HYPOTHESES),
            "predeclared_criteria": {
                "approx_equal_threshold": APPROX_EQUAL_THRESHOLD,
                "h4_model_family_spread_threshold": (
                    H4_MODEL_FAMILY_SPREAD_THRESHOLD
                ),
            },
            "hypothesis_results": hypothesis_results,
            "testability": testability,
            "recommended_next_step": recommended_next_step,
            "integrity": {
                "all_inputs_aggregate_only_public_artifact": True,
                "all_inputs_promotion_ready_false": True,
                "all_inputs_policy_search_performed_false": True,
                "all_inputs_candidate_not_fact": True,
                "all_inputs_default_should_change_false": True,
                "all_inputs_evidencecore_semantics_changed_false": True,
                "all_inputs_quality_strategy_tuned_false": True,
                "all_inputs_new_provider_calls_zero": True,
                "all_inputs_baseline_for_deltas_p25": True,
                "all_inputs_policy_under_validation_balanced_v1": True,
                "forbidden_public_key_scan_clean": True,
            },
            "safety_invariants": {
                "aggregate_only_public_artifact": True,
                "promotion_ready_false": True,
                "default_should_change_false": True,
                "no_evidencecore_semantics_change": True,
                "no_live_llm_calls_by_screen": True,
                "no_policy_search": True,
                "no_threshold_tuning": True,
                "no_raw_records_read": True,
                "no_raw_paths_or_digests": True,
                "no_prompts_or_responses": True,
                "no_private_labels": True,
                "no_run_ids_emitted": True,
                "no_global_supported_verdict_emitted": True,
                "per_hypothesis_screen_status_only": True,
            },
            "framing": {
                "promotion_readiness_claimed": False,
                "default_readiness_claimed": False,
                "runtime_clean_general_algorithm_claimed": False,
                "signal_strength": "bounded_public_aggregate_screen_only",
                "is_full_b12_mechanism_decomposition": False,
                "recommended_next_step": "future_ephemeral_record_b12_replay_or_b13_with_caution",
            },
        }
    )

    _finalize_safety(report)
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _build_synthetic_b11_aggregate() -> dict[str, Any]:
    """Build a minimal synthetic B11 aggregate report for self-test.

    Mirrors the real B11 aggregate report's public shape: aggregate deltas and
    per-model-family deltas only; no raw records, paths, prompts, etc.
    """
    return {
        "schema_version": INPUT_B11_SCHEMA,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        "aggregate_verdict": "partial_with_failure",
        "aggregate_verdict_reason": "self_test_synthetic",
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        "policy_under_validation": POLICY_UNDER_ANALYSIS,
        "run_count": 4,
        "record_count_total": 16,
        "public_model_family_count": 4,
        "public_repo_slice_count": 4,
        "deltas_balanced_v1_vs_p25": {
            "gold_span": -0.002604,
            "false_span": -0.054688,
            "span_f0_5": -0.001899,
            "primary_false_positive_rate": -0.020833,
            "model_calls": -0.354167,
        },
        "per_model_family": {
            "deepseek_flash": {
                "delta_balanced_v1_vs_p25": {"gold_span": 0.0},
            },
            "deepseek_pro": {
                "delta_balanced_v1_vs_p25": {"gold_span": 0.0},
            },
            "kimi": {
                "delta_balanced_v1_vs_p25": {"gold_span": -0.010417},
            },
            "qwen": {
                "delta_balanced_v1_vs_p25": {"gold_span": 0.0},
            },
        },
        "failure_slices_sanitized": [
            {
                "model_family": "kimi",
                "repo_slice_id": "py_fastapi",
                "verdict_reason": "failure_threshold_exceeded: failure_spanf05_delta",
            }
        ],
        "b10b_runtime_shadow_summary": {
            "verdict": "empirical_replay_support_pending",
            "pending_due_denominator": True,
        },
    }


def _self_test_happy_path() -> dict[str, Any]:
    b11 = _build_synthetic_b11_aggregate()
    report = screen(b11, self_test=True)
    assert report["schema_version"] == SCHEMA_VERSION, report["schema_version"]
    assert report["claim_level"] == CLAIM_LEVEL, report["claim_level"]
    # Safety fields preserved verbatim.
    for k, v in (
        ("aggregate_only_public_artifact", True),
        ("candidate_not_fact", True),
        ("promotion_ready", False),
        ("default_should_change", False),
        ("evidencecore_semantics_changed", False),
        ("policy_search_performed", False),
        ("quality_strategy_tuned", False),
        ("new_provider_calls", 0),
    ):
        assert report[k] == v, (k, report[k])
    # Per-hypothesis statuses present; NO global supported verdict.
    assert "hypothesis_results" in report
    for h in HYPOTHESES:
        assert h in report["hypothesis_results"], h
        assert "screen_status" in report["hypothesis_results"][h], h
    # H1: inconclusive (no ablation controls).
    h1 = report["hypothesis_results"]["H1_ambiguous_routing"]
    assert h1["screen_status"] == "inconclusive_unavailable_ablation_controls", h1
    assert h1["h1_support_claimed"] is False, h1
    # H2: reduced_calls_observed but causal inconclusive.
    h2 = report["hypothesis_results"]["H2_llm_call_reduction"]
    assert (
        h2["screen_status"]
        == "reduced_calls_observed_causal_mechanism_inconclusive"
    ), h2
    assert h2["reduced_calls_observed"] is True, h2
    assert h2["h2_causal_support_claimed"] is False, h2
    # H3: aggregate primary parity supported (gold -0.002604, span_f0_5 -0.001899).
    h3 = report["hypothesis_results"]["H3_p25_fallback_sufficiency"]
    assert (
        h3["screen_status"]
        == "aggregate_primary_parity_supported_consistent_with_h3"
    ), h3
    assert h3["aggregate_primary_parity_supported"] is True, h3
    assert h3["h3_support_claimed"] is False, h3
    # H4: family gold spread not supported (spread 0.010417 <= 0.05), but
    # model x repo interaction inconclusive (Kimi py_fastapi failure present).
    h4 = report["hypothesis_results"]["H4_model_specific"]
    assert (
        h4["screen_status"]
        == "family_gold_spread_not_supported_model_repo_interaction_inconclusive"
    ), h4
    assert h4["family_level_gold_spread_not_supported"] is True, h4
    assert h4["h4_full_refutation_claimed"] is False, h4
    assert h4["model_repo_interaction_inconclusive"] is True, h4
    spread = h4["family_gold_span_delta_spread"]["spread"]
    assert spread == 0.010417, spread
    # Testability section present with all 5 missing controls.
    testability = report["testability"]
    assert testability["full_b12_possible_from_public_artifact"] is False
    gap_ids = [g["gap_id"] for g in testability["missing_controls_for_full_b12"]]
    assert gap_ids == [
        "no_per_record_route_decisions_in_public_artifact",
        "no_ambiguous_subset_membership_in_public_artifact",
        "no_deterministic_call_reduction_variant_B_in_public_artifact",
        "no_random_call_reduction_variant_E_in_public_artifact",
        "no_weak_candidate_only_outcomes_in_public_artifact",
    ], gap_ids
    # Recommended next step: cautious, no auto-promotion.
    rns = report["recommended_next_step"]
    assert rns["primary"] == "future_ephemeral_record_b12_replay", rns
    assert rns["next_step_authorizes_promotion"] is False, rns
    # Forbidden-key/value scan clean.
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    # No raw data carried.
    assert report["raw_paths_in_artifact"] is False
    assert report["private_labels_committed"] is False
    assert report["run_ids_in_artifact"] is False
    print("self-test happy path: ok")
    return report


def _self_test_input_validation_blocks() -> None:
    # Wrong schema_version.
    bad = _build_synthetic_b11_aggregate()
    bad["schema_version"] = "wrong"
    try:
        screen(bad, self_test=True)
    except ValueError as exc:
        assert "unexpected B11 schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should have rejected wrong schema_version")

    # promotion_ready=true must be rejected.
    bad = _build_synthetic_b11_aggregate()
    bad["promotion_ready"] = True
    try:
        screen(bad, self_test=True)
    except ValueError as exc:
        assert "promotion_ready=false" in str(exc), exc
    else:
        raise AssertionError("screen should have rejected promotion_ready=true")

    # Missing deltas dict.
    bad = _build_synthetic_b11_aggregate()
    del bad["deltas_balanced_v1_vs_p25"]
    try:
        screen(bad, self_test=True)
    except ValueError as exc:
        assert "deltas_balanced_v1_vs_p25" in str(exc), exc
    else:
        raise AssertionError("screen should have rejected missing deltas")

    print("self-test input validation block: ok")


def _self_test_h3_parity_breaks() -> None:
    """When gold or span_f0_5 delta exceeds +/-0.02, H3 screen status flips."""
    b11 = _build_synthetic_b11_aggregate()
    b11["deltas_balanced_v1_vs_p25"]["gold_span"] = -0.05  # outside +/-0.02
    report = screen(b11, self_test=True)
    h3 = report["hypothesis_results"]["H3_p25_fallback_sufficiency"]
    assert (
        h3["screen_status"] == "aggregate_primary_parity_not_supported"
    ), h3
    assert h3["aggregate_primary_parity_supported"] is False, h3
    print("self-test H3 parity break: ok")


def _self_test_h4_spread_supported_branch() -> None:
    """When per-family spread exceeds 0.05, H4 family-level criterion flips to
    supported (but model x repo interaction remains inconclusive)."""
    b11 = _build_synthetic_b11_aggregate()
    # Push kimi delta to -0.08 so spread = 0 - (-0.08) = 0.08 > 0.05.
    b11["per_model_family"]["kimi"]["delta_balanced_v1_vs_p25"][
        "gold_span"
    ] = -0.08
    report = screen(b11, self_test=True)
    h4 = report["hypothesis_results"]["H4_model_specific"]
    assert (
        h4["screen_status"]
        == "family_gold_spread_supported_model_repo_interaction_inconclusive"
    ), h4
    assert h4["family_level_gold_spread_supported"] is True, h4
    assert h4["h4_support_claimed"] is False, h4  # screen never claims support
    print("self-test H4 spread-supported branch: ok")


def _self_test_forbidden_scan() -> None:
    """Forbidden-key scan catches injected raw paths / labels."""
    bad_report = {
        "task_id": "leak",
        "path": "src/foo.rs",
        "snippet": "fn main(){}",
        "gold_spans": [[1, 2]],
        "private_labels": "x",
    }
    hits = b6lite._walk_forbidden(bad_report)
    flat = " ".join(hits)
    assert "task_id" in flat
    assert "path" in flat
    assert "snippet" in flat
    assert "gold_spans" in flat
    assert "private_labels" in flat
    print("self-test forbidden scan: ok")


def run_self_tests() -> dict[str, Any]:
    _self_test_happy_path()
    _self_test_input_validation_blocks()
    _self_test_h3_parity_breaks()
    _self_test_h4_spread_supported_branch()
    _self_test_forbidden_scan()
    return {
        "schema_version": SCHEMA_VERSION,
        "claim_level": CLAIM_LEVEL,
        "self_test_passed": True,
        "self_test_checks": {
            "happy_path": True,
            "input_validation_blocks": True,
            "h3_parity_breaks": True,
            "h4_spread_supported_branch": True,
            "forbidden_scan": True,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=(
            "path to the B11 aggregate report JSON (default: the canonical "
            "artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json)"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=(
            "path to write the B12 public aggregate screen report "
            "(default: artifacts/b12_mechanism_decomposition/"
            "b12_public_aggregate_screen_report.json)"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the B12 public aggregate screen self-test (synthetic fixture)",
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if args.self_test and args.input is not None and str(args.input) != str(
        DEFAULT_INPUT
    ):
        parser.error("--self-test ignores --input; do not pass both")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_tests()
        print(json.dumps(result, indent=2, sort_keys=True))
        print("B12 public aggregate screen self-test: PASS", file=sys.stderr)
        return 0
    if not args.input.exists():
        print(
            f"B12 public aggregate screen input not found: {args.input}",
            file=sys.stderr,
        )
        return 2
    b11_aggregate = json.loads(args.input.read_text(encoding="utf-8"))
    report = screen(b11_aggregate, self_test=False)
    _write_json(args.out, report)
    summary = {
        "schema_version": report["schema_version"],
        "claim_level": report["claim_level"],
        "self_test": report["self_test"],
        "aggregate_only_public_artifact": report[
            "aggregate_only_public_artifact"
        ],
        "promotion_ready": report["promotion_ready"],
        "default_should_change": report["default_should_change"],
        "new_provider_calls": report["new_provider_calls"],
        "hypothesis_screen_statuses": {
            h: report["hypothesis_results"][h]["screen_status"]
            for h in HYPOTHESES
        },
        "full_b12_possible_from_public_artifact": report["testability"][
            "full_b12_possible_from_public_artifact"
        ],
        "recommended_next_step": report["framing"]["recommended_next_step"],
        "out": str(args.out),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
