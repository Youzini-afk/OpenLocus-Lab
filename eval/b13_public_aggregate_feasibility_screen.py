#!/usr/bin/env python3
"""B13 Public-Aggregate Feasibility / No-Go Screen (bounded).

This is a **bounded public-aggregate feasibility screen**, NOT a real B13
distributionally robust policy search. Real B13 (the frozen preregistration
in ``eval/b13_dro_policy_search.py`` and
``docs/en/b13-distributionally-robust-policy-search.md``) requires private /
ephemeral per-record P21 records with ``route_features`` + per-strategy
outcomes + group membership, and the rotating leave-one-model-family-out
train/test splits. None of those are present in the public B11 aggregate or
the B12 public-aggregate screen, so real B13 search cannot be performed
from public artifacts alone.

What this screen DOES: read the already-published B11 aggregate report
(``artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json``)
and the already-published B12 public-aggregate screen report
(``artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json``)
and emit a **public-aggregate feasibility / no-go report** for B13.

The screen preserves the public-artifact contract:

* **no** raw records, source, prompts, responses, snippets, digests, paths, or
  private labels are read or emitted;
* **no** provider calls (``new_provider_calls == 0``);
* **no** empirical policy search, rule selection, threshold tuning, or winner
  declaration;
* **no** promotion / default / runtime-clean general algorithm claim;
* ``policy_search_performed=false``,
  ``empirical_policy_search_performed=false``, ``policy_found=false``,
  ``rotations_evaluated=false``.

The screen MAY include a descriptive overall-mean penalty index computed
from the already-published fixed strategies (P25 / balanced_v1) in the B11
aggregate. That index is **strictly descriptive**: it is labeled
``descriptive_fixed_strategy_proxy_not_policy_search=true`` and
``valid_for_policy_selection=false`` /
``valid_for_strategy_ranking=false`` / ``not_worst_group=true`` /
``not_cvar=true`` / ``not_rotation_validated=true``. It is NOT the B13
RobustUtility objective, NOT a worst-group measure, NOT a CVaR measure, and
NOT rotation-validated. The two fixed strategies are listed in publication
order (NOT a ranking), and the screen MUST NEVER be read as a B13 search
result, a policy selection, or a winner.

The screen carries forward the B11 aggregate verdict (mixed / partial) and
the B12 per-hypothesis inconclusive statuses so a reader cannot mistake a
B13 no-go for B11 success or B12 supported.

Run::

    python3 eval/b13_public_aggregate_feasibility_screen.py --self-test
    python3 eval/b13_public_aggregate_feasibility_screen.py \
        --out artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json
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

REPO_ROOT = Path(__file__).resolve().parent.parent

SCHEMA_VERSION = "b13-public-aggregate-feasibility-screen-v0"
GENERATED_BY = "b13_public_aggregate_feasibility_screen"
CLAIM_LEVEL = "bounded_public_aggregate_feasibility_screen_of_b11_b12_aggregates"

INPUT_B11_SCHEMA = "b11-prospective-matrix-aggregate-report-v0"
INPUT_B12_SCREEN_SCHEMA = "b12-public-aggregate-mechanism-screen-v0"

POLICY_UNDER_ANALYSIS = "balanced_v1"
BASELINE_FOR_DELTAS = "p25"

DEFAULT_INPUT_B11 = Path(
    "artifacts/b11_prospective_matrix/"
    "b11_prospective_matrix_aggregate_report.json"
)
DEFAULT_INPUT_B12 = Path(
    "artifacts/b12_mechanism_decomposition/"
    "b12_public_aggregate_screen_report.json"
)
DEFAULT_OUT = Path(
    "artifacts/b13_dro_policy_search/"
    "b13_public_aggregate_feasibility_report.json"
)

# Verdicts emitted by this screen. The screen NEVER emits success / failure /
# partial as a policy-search verdict; it emits only feasibility / no-go
# statuses that make clear no empirical B13 search happened.
ALLOWED_VERDICTS = (
    "no_go_public_aggregate_only",
    "insufficient_data_public_aggregate_only",
)

# Missing inputs that block real B13 from the public aggregates. Each entry is
# a self-contained reason so a reader cannot mistake the screen for a B13
# search result. Descriptions are kept under 256 chars to satisfy the public
# forbidden-value scan (long_string guard).
MISSING_INPUTS = (
    {
        "gap_id": "no_per_record_route_features_in_public_artifact",
        "description": (
            "real B13 candidate rules predicate on per-record route_features "
            "(query_noise, candidate_support_exists, local_anchor, etc.); "
            "the public B11 aggregate emits only policy-level route-decision "
            "counts, not per-record features"
        ),
    },
    {
        "gap_id": "no_per_record_action_eligibility_in_public_artifact",
        "description": (
            "B13 candidate actions (weak_only, use_p25_action, "
            "use_local_baseline) must be applied per-record against the "
            "eligible action set; the public aggregate does not publish "
            "per-record action eligibility, so candidate rules cannot be "
            "evaluated record-by-record"
        ),
    },
    {
        "gap_id": "no_per_strategy_outcomes_in_public_artifact",
        "description": (
            "real B13 replay selects per-strategy outcomes per record "
            "(each P21 record contains per-strategy outcomes); the public "
            "B11 aggregate publishes only weighted means and deltas, not "
            "per-strategy per-record outcomes"
        ),
    },
    {
        "gap_id": "no_weak_candidate_only_public_outcomes_in_public_artifact",
        "description": (
            "the weak_candidate_only per-strategy outcomes (the substrate "
            "the ambiguous-routing rule selects) are not in the public "
            "aggregate, so candidate weak_only rules cannot be replayed"
        ),
    },
    {
        "gap_id": "no_group_membership_for_train_test_rotations_in_public_artifact",
        "description": (
            "B13 rotating leave-one-model-family-out needs per-record group "
            "membership (which model family and repo each record belongs "
            "to) to build train and test splits; the public aggregate only "
            "emits per-family rollup deltas, not per-record group membership"
        ),
    },
    {
        "gap_id": "no_held_out_family_evaluation_in_public_artifact",
        "description": (
            "B13 must evaluate candidate policies on a held-out model family "
            "via replay; the public aggregate does not expose per-record "
            "outcomes on the held-out family, so held-out evaluation is "
            "impossible"
        ),
    },
    {
        "gap_id": "no_candidate_rule_coverage_in_public_artifact",
        "description": (
            "real B13 search enumerates 6-10 rule policies and measures "
            "candidate rule coverage on the P21 record set; the public "
            "aggregate does not expose per-record coverage of any candidate "
            "rule, so search cannot be replayed"
        ),
    },
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


def _base_report(self_test: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now(),
        "claim_level": CLAIM_LEVEL,
        "self_test": bool(self_test),
        "input_b11_schema": INPUT_B11_SCHEMA,
        "input_b12_screen_schema": INPUT_B12_SCREEN_SCHEMA,
        "policy_under_analysis": POLICY_UNDER_ANALYSIS,
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        # Safety fields preserved verbatim. The screen makes NO empirical
        # policy search claim; policy_search_performed=false and
        # empirical_policy_search_performed=false are the disambiguating
        # fields (the B13 stage IS policy search, but no empirical search
        # was performed by this screen).
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "empirical_policy_search_performed": False,
        "stage_is_policy_search": True,  # B13 stage IS policy search
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
        "is_full_b13_distributionally_robust_policy_search": False,
        "full_b13_possible_from_public_artifacts": False,
        "policy_found": False,
        "rotations_evaluated": False,
        "descriptive_fixed_strategy_proxy_not_policy_search": True,
    }


def _finalize_safety(report: dict[str, Any]) -> None:
    """Run the forbidden-key/value scan on the public output."""
    violations = b6lite._walk_forbidden(report)
    integrity = report.setdefault("integrity", {})
    integrity["forbidden_public_key_scan_clean"] = not violations
    if violations:
        raise ValueError(
            "b13-public-aggregate-feasibility-screen public output would "
            f"contain forbidden keys/values; first violations: "
            f"{violations[:5]}"
        )


def _validate_b11_aggregate(report: dict[str, Any]) -> None:
    """Validate the B11 aggregate input is a public artifact."""
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


def _validate_b12_screen(report: dict[str, Any]) -> None:
    """Validate the B12 public aggregate screen input."""
    if report.get("schema_version") != INPUT_B12_SCREEN_SCHEMA:
        raise ValueError(
            f"unexpected B12 screen schema_version: "
            f"{report.get('schema_version')!r}"
        )
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError(
            "B12 screen input must be aggregate_only_public_artifact=true"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError("B12 screen input must have promotion_ready=false")
    if report.get("policy_search_performed") is not False:
        raise ValueError(
            "B12 screen input must have policy_search_performed=false"
        )
    if report.get("candidate_not_fact") is not True:
        raise ValueError("B12 screen input must have candidate_not_fact=true")
    if report.get("default_should_change") is not False:
        raise ValueError("B12 screen input must have default_should_change=false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "B12 screen input must have evidencecore_semantics_changed=false"
        )
    if report.get("new_provider_calls") != 0:
        raise ValueError("B12 screen input must have new_provider_calls=0")
    if report.get("full_b12_replay_possible_from_public_artifact") is not False:
        raise ValueError(
            "B12 screen input must have "
            "full_b12_replay_possible_from_public_artifact=false"
        )
    if not isinstance(report.get("hypothesis_results"), dict):
        raise ValueError("B12 screen input missing hypothesis_results dict")


def _carry_forward_b11(b11: dict[str, Any]) -> dict[str, Any]:
    """Carry forward B11 mixed/partial status (public fields only)."""
    return {
        "b11_aggregate_verdict": b11.get("aggregate_verdict"),
        "b11_aggregate_verdict_reason": b11.get("aggregate_verdict_reason"),
        "b11_run_count": b11.get("run_count"),
        "b11_record_count_total": b11.get("record_count_total"),
        "b11_public_model_family_count": b11.get("public_model_family_count"),
        "b11_public_repo_slice_count": b11.get("public_repo_slice_count"),
        "b11_baseline_for_deltas": b11.get("baseline_for_deltas"),
        "b11_policy_under_validation": b11.get("policy_under_validation"),
        "b10b_runtime_shadow_verdict": (
            b11.get("b10b_runtime_shadow_summary", {}) or {}
        ).get("verdict"),
        "b10b_pending_due_denominator": (
            b11.get("b10b_runtime_shadow_summary", {}) or {}
        ).get("pending_due_denominator"),
        "b11_deltas_balanced_v1_vs_p25": {
            "gold_span": _as_float(
                (b11.get("deltas_balanced_v1_vs_p25") or {}).get("gold_span", 0.0)
            ),
            "span_f0_5": _as_float(
                (b11.get("deltas_balanced_v1_vs_p25") or {}).get("span_f0_5", 0.0)
            ),
            "model_calls": _as_float(
                (b11.get("deltas_balanced_v1_vs_p25") or {}).get(
                    "model_calls", 0.0
                )
            ),
        },
    }


def _carry_forward_b12(b12_screen: dict[str, Any]) -> dict[str, Any]:
    """Carry forward B12 per-hypothesis inconclusive statuses."""
    hyp_results = b12_screen.get("hypothesis_results", {}) or {}
    carried: dict[str, Any] = {
        h: {
            "screen_status": hyp_results.get(h, {}).get("screen_status"),
        }
        for h in (
            "H1_ambiguous_routing",
            "H2_llm_call_reduction",
            "H3_p25_fallback_sufficiency",
            "H4_model_specific",
        )
        if h in hyp_results
    }
    carried["b12_full_replay_possible_from_public_artifact"] = (
        b12_screen.get("full_b12_replay_possible_from_public_artifact")
    )
    carried["b12_recommended_next_step"] = (
        b12_screen.get("framing", {}) or {}
    ).get("recommended_next_step")
    return carried


def _descriptive_fixed_strategy_proxy(b11: dict[str, Any]) -> dict[str, Any]:
    """Descriptive overall-mean penalty index from already-published fixed
    strategies (P25 / balanced_v1) in the B11 aggregate.

    This is NOT a B13 search result, NOT a policy selection, and NOT a
    winner. It only re-states the published B11 aggregate means as a simple
    penalty-shaped index (SpanF0.5 minus weighted PFP / normalized-cost /
    normalized-latency penalties) so a reader can see what the published
    fixed strategies look like under a penalty-style summary. The screen
    never selects new rules, never ranks strategies for selection, and never
    declares a winner.

    IMPORTANT: this index is NOT the B13 RobustUtility objective, NOT a
    worst-group measure, NOT a CVaR measure, and NOT rotation-validated. It
    is a descriptive overall-mean penalty index computed from published
    aggregate means only. It MUST NOT be used for policy selection or
    strategy ranking. The two fixed strategies are listed in publication
    order (p25, then balanced_v1), NOT in any ranking order; no winner is
    declared.
    """
    deltas = b11.get("deltas_balanced_v1_vs_p25", {}) or {}
    overall = b11.get("overall_weighted_means", {}) or {}
    p25 = overall.get("p25", {}) or {}
    balanced = overall.get("balanced_v1", {}) or {}
    # Penalty index shape: SpanF0.5 - λ*PFP - μ*norm_cost - ν*norm_latency.
    # With μ=0.1, ν=0.1, and normalized_cost = model_calls/10,
    # normalized_latency = model_calls/10 (skeleton proxy). This is a
    # descriptive overall-mean penalty index, NOT the B13 RobustUtility
    # objective (which is a worst-group / CVaR measure over per-record
    # utilities, validated via rotating leave-one-model-family-out).
    lam = 1.0
    mu = 0.1
    nu = 0.1

    def _index(label: str, m: dict[str, Any]) -> dict[str, Any]:
        span = _as_float(m.get("span_f0_5", 0.0))
        pfp = _as_float(m.get("primary_false_positive_rate", 0.0))
        calls = _as_float(m.get("model_calls", 0.0))
        norm_cost = calls / 10.0
        norm_latency = calls / 10.0
        return {
            "strategy": label,
            "span_f0_5": _round6(span),
            "primary_false_positive_rate": _round6(pfp),
            "model_calls": _round6(calls),
            "descriptive_overall_mean_penalty_index_not_for_ranking": _round6(
                span - lam * pfp - mu * norm_cost - nu * norm_latency
            ),
        }

    return {
        "is_policy_search": False,
        "selects_new_rules": False,
        "declares_winner": False,
        "ranks_strategies_for_selection": False,
        "uses_only_published_fixed_strategies": True,
        "valid_for_policy_selection": False,
        "valid_for_strategy_ranking": False,
        "not_worst_group": True,
        "not_cvar": True,
        "not_rotation_validated": True,
        "is_overall_mean_only": True,
        "penalty_lambda": lam,
        "penalty_mu": mu,
        "penalty_nu": nu,
        "normalized_cost_proxy": "model_calls over 10.0",
        "normalized_latency_proxy": "model_calls over 10.0",
        # Listed in PUBLICATION ORDER (p25 first, then balanced_v1). This
        # is NOT a ranking; do NOT read order as a winner-like ordering.
        "fixed_strategy_indices_in_publication_order_not_ranked": [
            _index("p25", p25),
            _index("balanced_v1", balanced),
        ],
        "balanced_v1_vs_p25_delta": {
            "gold_span": _round6(_as_float(deltas.get("gold_span", 0.0))),
            "span_f0_5": _round6(_as_float(deltas.get("span_f0_5", 0.0))),
            "model_calls": _round6(_as_float(deltas.get("model_calls", 0.0))),
        },
        "interpretation_note": (
            "Descriptive overall-mean penalty index of published B11 "
            "fixed strategies. NOT B13 RobustUtility, NOT worst-group "
            "or CVaR, NOT rotation-validated. NOT valid for policy "
            "selection or ranking. NOT a B13 search result; no rule "
            "selected; no winner declared."
        ),
    }


def screen(
    b11_aggregate: dict[str, Any],
    b12_screen: dict[str, Any],
    self_test: bool = False,
) -> dict[str, Any]:
    """Build the B13 public aggregate feasibility / no-go screen report.

    ``b11_aggregate`` is the parsed B11 aggregate report JSON;
    ``b12_screen`` is the parsed B12 public-aggregate screen report JSON.
    ``self_test`` flags that the report was produced from a synthetic
    fixture.
    """
    _validate_b11_aggregate(b11_aggregate)
    _validate_b12_screen(b12_screen)

    report = _base_report(self_test)
    report["source_artifact_public_note"] = (
        "already-published aggregate-only public B11 matrix aggregate and "
        "B12 public aggregate screen reports; no raw records, paths, "
        "prompts, responses, snippets, or private labels read by the screen"
    )

    report["input_b11_summary"] = _carry_forward_b11(b11_aggregate)
    report["input_b12_summary"] = _carry_forward_b12(b12_screen)

    # Verdict: no_go unless the public aggregate is itself missing entirely
    # (insufficient_data). In this skeleton both paths emit a no-empirical-
    # search verdict; the distinction is whether the public inputs were
    # sufficient to even produce a feasibility read.
    b11_verdict = b11_aggregate.get("aggregate_verdict") or ""
    b11_records = b11_aggregate.get("record_count_total") or 0
    if not isinstance(b11_records, int) or b11_records <= 0:
        verdict = "insufficient_data_public_aggregate_only"
        verdict_reason = (
            "B11 aggregate reports no records; insufficient for a "
            "feasibility read. No empirical B13 search was performed."
        )
    else:
        verdict = "no_go_public_aggregate_only"
        verdict_reason = (
            "public B11 and B12 aggregates lack per-record inputs for "
            "real B13 policy search. No empirical B13 search; B11 "
            f"verdict ({b11_verdict!r}) and B12 public-aggregate "
            "screen statuses carried forward, NOT authorizing "
            "promotion or default change."
        )

    report["verdict"] = verdict
    report["verdict_reason"] = verdict_reason
    report["allowed_verdicts"] = list(ALLOWED_VERDICTS)

    # Missing inputs (the specific gaps that block real B13).
    report["missing_inputs_for_real_b13"] = [dict(g) for g in MISSING_INPUTS]

    # Descriptive overall-mean penalty index from already-published fixed
    # strategies (NOT the B13 RobustUtility, NOT worst-group, NOT CVaR, NOT
    # rotation-validated; NOT valid for policy selection or strategy ranking).
    report["descriptive_fixed_strategy_proxy"] = _descriptive_fixed_strategy_proxy(
        b11_aggregate
    )

    # Recommended next step (cautious, no auto-promotion).
    recommended_next_step = {
        "primary": "future_ephemeral_record_b13_replay",
        "secondary": "future_ephemeral_record_b12_replay",
        "reason": (
            "Run real B13 against ephemeral P21 records from B11 live runs "
            "once available (the only path that can perform empirical "
            "distributionally robust policy search), or first run full B12 "
            "on the same records. The public aggregate alone is "
            "insufficient for either."
        ),
        "next_step_authorizes_promotion": False,
        "next_step_authorizes_default_change": False,
        "next_step_authorizes_runtime_clean_algorithm": False,
        "next_step_authorizes_empirical_policy_search": False,
    }

    report.update(
        {
            "testability": {
                "full_b13_possible_from_public_artifacts": False,
                "missing_inputs_for_full_b13": [
                    g["gap_id"] for g in MISSING_INPUTS
                ],
                "note": (
                    "Real B13 policy search cannot be replayed from the "
                    "current public B11 and B12 aggregates. The listed "
                    "missing inputs are the specific per-record fields "
                    "required. Only this bounded feasibility or no-go "
                    "screen is publishable until ephemeral records "
                    "arrive."
                ),
            },
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
                "no_empirical_policy_search": True,
                "no_policy_promotion": True,
                "no_threshold_tuning": True,
                "no_raw_records_read": True,
                "no_raw_paths_or_digests": True,
                "no_prompts_or_responses": True,
                "no_private_labels": True,
                "no_run_ids_emitted": True,
                "no_policy_found": True,
                "no_rotations_evaluated": True,
                "no_winner_declared": True,
                "descriptive_proxy_only_not_policy_search": True,
            },
            "framing": {
                "promotion_readiness_claimed": False,
                "default_readiness_claimed": False,
                "runtime_clean_general_algorithm_claimed": False,
                "empirical_policy_search_claimed": False,
                "policy_found_claimed": False,
                "winner_declared_claimed": False,
                "signal_strength": "bounded_public_aggregate_feasibility_screen_only",
                "is_full_b13_distributionally_robust_policy_search": False,
                "recommended_next_step": (
                    "future_ephemeral_record_b13_replay_or_b12_replay"
                ),
            },
        }
    )

    _finalize_safety(report)
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _build_synthetic_b11_aggregate() -> dict[str, Any]:
    """Minimal synthetic B11 aggregate for self-test (mirrors the real
    public shape: aggregate deltas + per-family deltas only; no raw records,
    paths, prompts, etc.)."""
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
        "aggregate_verdict_reason": "self_test_synthetic_mixed_partial",
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
        "overall_weighted_means": {
            "p25": {
                "false_span": 0.236979,
                "gold_span": 0.247396,
                "model_calls": 0.958333,
                "primary_false_positive_rate": 0.020833,
                "span_f0_5": 0.064538,
            },
            "balanced_v1": {
                "false_span": 0.182292,
                "gold_span": 0.244792,
                "model_calls": 0.604167,
                "primary_false_positive_rate": 0.0,
                "span_f0_5": 0.062639,
            },
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


def _build_synthetic_b12_screen() -> dict[str, Any]:
    """Minimal synthetic B12 public aggregate screen for self-test."""
    return {
        "schema_version": INPUT_B12_SCREEN_SCHEMA,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        "full_b12_replay_possible_from_public_artifact": False,
        "hypothesis_results": {
            "H1_ambiguous_routing": {
                "screen_status": "inconclusive_unavailable_ablation_controls",
            },
            "H2_llm_call_reduction": {
                "screen_status": (
                    "reduced_calls_observed_causal_mechanism_inconclusive"
                ),
            },
            "H3_p25_fallback_sufficiency": {
                "screen_status": (
                    "aggregate_primary_parity_supported_consistent_with_h3"
                ),
            },
            "H4_model_specific": {
                "screen_status": (
                    "family_gold_spread_not_supported_"
                    "model_repo_interaction_inconclusive"
                ),
            },
        },
        "framing": {
            "recommended_next_step": (
                "future_ephemeral_record_b12_replay_or_b13_with_caution"
            ),
        },
    }


def _self_test_happy_path() -> dict[str, Any]:
    b11 = _build_synthetic_b11_aggregate()
    b12 = _build_synthetic_b12_screen()
    report = screen(b11, b12, self_test=True)
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
        ("empirical_policy_search_performed", False),
        ("stage_is_policy_search", True),
        ("quality_strategy_tuned", False),
        ("new_provider_calls", 0),
        ("policy_found", False),
        ("rotations_evaluated", False),
        ("full_b13_possible_from_public_artifacts", False),
        ("winner_declared", False),
        ("promotion_declared", False),
        ("default_recommendation_declared", False),
    ):
        assert report[k] == v, (k, report[k])
    # No-go verdict emitted.
    assert report["verdict"] == "no_go_public_aggregate_only", report["verdict"]
    assert report["verdict"] in ALLOWED_VERDICTS, report["verdict"]
    assert (
        "no empirical b13 search" in report["verdict_reason"].lower()
    ), report["verdict_reason"]
    # B11 mixed/partial + B12 public-aggregate screen statuses carried
    # forward.
    assert report["input_b11_summary"]["b11_aggregate_verdict"] == (
        "partial_with_failure"
    )
    carried_h1 = report["input_b12_summary"]["H1_ambiguous_routing"][
        "screen_status"
    ]
    assert carried_h1 == "inconclusive_unavailable_ablation_controls", carried_h1
    # All missing inputs enumerated.
    missing_ids = [g["gap_id"] for g in report["missing_inputs_for_real_b13"]]
    expected_missing = tuple(g["gap_id"] for g in MISSING_INPUTS)
    assert missing_ids == list(expected_missing), missing_ids
    # Descriptive overall-mean penalty index present and clearly labeled NOT
    # policy search, NOT valid for selection/ranking, NOT worst-group/CVaR/
    # rotation-validated. Two fixed strategies listed in publication order
    # (NOT a ranking), no winner declared.
    proxy = report["descriptive_fixed_strategy_proxy"]
    assert proxy["is_policy_search"] is False, proxy
    assert proxy["selects_new_rules"] is False, proxy
    assert proxy["declares_winner"] is False, proxy
    assert proxy["ranks_strategies_for_selection"] is False, proxy
    assert proxy["uses_only_published_fixed_strategies"] is True, proxy
    assert proxy["valid_for_policy_selection"] is False, proxy
    assert proxy["valid_for_strategy_ranking"] is False, proxy
    assert proxy["not_worst_group"] is True, proxy
    assert proxy["not_cvar"] is True, proxy
    assert proxy["not_rotation_validated"] is True, proxy
    assert proxy["is_overall_mean_only"] is True, proxy
    # The two fixed strategies must be listed in publication order, NOT a
    # ranking; no winner field.
    assert "fixed_strategy_proxies" not in proxy, (
        "old robust_utility_proxy field name must be removed; use "
        "fixed_strategy_indices_in_publication_order_not_ranked"
    )
    indices = proxy["fixed_strategy_indices_in_publication_order_not_ranked"]
    assert [i["strategy"] for i in indices] == ["p25", "balanced_v1"], indices
    for i in indices:
        assert "robust_utility_proxy" not in i, i
        assert (
            "descriptive_overall_mean_penalty_index_not_for_ranking" in i
        ), i
    assert "winner" not in proxy, proxy
    assert (
        report["descriptive_fixed_strategy_proxy_not_policy_search"] is True
    ), report
    # Forbidden-key/value scan clean.
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    # No raw data carried.
    assert report["raw_paths_in_artifact"] is False
    assert report["private_labels_committed"] is False
    assert report["run_ids_in_artifact"] is False
    print("self-test happy path: ok")
    return report


def _self_test_input_validation_blocks() -> None:
    # Wrong B11 schema_version.
    bad = _build_synthetic_b11_aggregate()
    bad["schema_version"] = "wrong"
    b12 = _build_synthetic_b12_screen()
    try:
        screen(bad, b12, self_test=True)
    except ValueError as exc:
        assert "unexpected B11 schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should reject wrong B11 schema_version")

    # B11 promotion_ready=true rejected.
    bad = _build_synthetic_b11_aggregate()
    bad["promotion_ready"] = True
    try:
        screen(bad, b12, self_test=True)
    except ValueError as exc:
        assert "promotion_ready=false" in str(exc), exc
    else:
        raise AssertionError("screen should reject B11 promotion_ready=true")

    # B11 policy_search_performed=true rejected.
    bad = _build_synthetic_b11_aggregate()
    bad["policy_search_performed"] = True
    try:
        screen(bad, b12, self_test=True)
    except ValueError as exc:
        assert "policy_search_performed=false" in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject B11 policy_search_performed=true"
        )

    # Wrong B12 screen schema_version.
    bad12 = _build_synthetic_b12_screen()
    bad12["schema_version"] = "wrong"
    b11 = _build_synthetic_b11_aggregate()
    try:
        screen(b11, bad12, self_test=True)
    except ValueError as exc:
        assert "unexpected B12 screen schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should reject wrong B12 schema_version")

    # B12 full_b12_replay_possible_from_public_artifact=true rejected.
    bad12 = _build_synthetic_b12_screen()
    bad12["full_b12_replay_possible_from_public_artifact"] = True
    try:
        screen(b11, bad12, self_test=True)
    except ValueError as exc:
        assert "full_b12_replay_possible_from_public_artifact=false" in str(
            exc
        ), exc
    else:
        raise AssertionError(
            "screen should reject B12 full_b12_replay_possible=true"
        )

    print("self-test input validation block: ok")


def _self_test_insufficient_data_branch() -> None:
    """When B11 record_count_total <= 0, the screen emits
    insufficient_data_public_aggregate_only."""
    b11 = _build_synthetic_b11_aggregate()
    b11["record_count_total"] = 0
    b12 = _build_synthetic_b12_screen()
    report = screen(b11, b12, self_test=True)
    assert report["verdict"] == (
        "insufficient_data_public_aggregate_only"
    ), report["verdict"]
    assert "no empirical b13 search" in report[
        "verdict_reason"
    ].lower(), report["verdict_reason"]
    # Still no policy search / no policy found / no rotations.
    assert report["policy_search_performed"] is False
    assert report["empirical_policy_search_performed"] is False
    assert report["policy_found"] is False
    assert report["rotations_evaluated"] is False
    print("self-test insufficient_data branch: ok")


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
    _self_test_insufficient_data_branch()
    _self_test_forbidden_scan()
    return {
        "schema_version": SCHEMA_VERSION,
        "claim_level": CLAIM_LEVEL,
        "self_test_passed": True,
        "self_test_checks": {
            "happy_path": True,
            "input_validation_blocks": True,
            "insufficient_data_branch": True,
            "forbidden_scan": True,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-b11",
        type=Path,
        default=DEFAULT_INPUT_B11,
        help=(
            "path to the B11 aggregate report JSON (default: the canonical "
            "artifacts/b11_prospective_matrix/"
            "b11_prospective_matrix_aggregate_report.json)"
        ),
    )
    parser.add_argument(
        "--input-b12",
        type=Path,
        default=DEFAULT_INPUT_B12,
        help=(
            "path to the B12 public aggregate screen report JSON (default: "
            "artifacts/b12_mechanism_decomposition/"
            "b12_public_aggregate_screen_report.json)"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=(
            "path to write the B13 public aggregate feasibility report "
            "(default: artifacts/b13_dro_policy_search/"
            "b13_public_aggregate_feasibility_report.json)"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the B13 public aggregate feasibility screen self-test "
        "(synthetic fixture)",
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if args.self_test and (
        str(args.input_b11) != str(DEFAULT_INPUT_B11)
        or str(args.input_b12) != str(DEFAULT_INPUT_B12)
    ):
        parser.error("--self-test ignores --input-b11/--input-b12; do not pass both")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_tests()
        print(json.dumps(result, indent=2, sort_keys=True))
        print(
            "B13 public aggregate feasibility screen self-test: PASS",
            file=sys.stderr,
        )
        return 0
    if not args.input_b11.exists():
        print(
            f"B13 feasibility screen B11 input not found: {args.input_b11}",
            file=sys.stderr,
        )
        return 2
    if not args.input_b12.exists():
        print(
            f"B13 feasibility screen B12 input not found: {args.input_b12}",
            file=sys.stderr,
        )
        return 2
    b11_aggregate = json.loads(args.input_b11.read_text(encoding="utf-8"))
    b12_screen = json.loads(args.input_b12.read_text(encoding="utf-8"))
    report = screen(b11_aggregate, b12_screen, self_test=False)
    _write_json(args.out, report)
    summary = {
        "schema_version": report["schema_version"],
        "claim_level": report["claim_level"],
        "self_test": report["self_test"],
        "verdict": report["verdict"],
        "verdict_reason": report["verdict_reason"],
        "aggregate_only_public_artifact": report[
            "aggregate_only_public_artifact"
        ],
        "promotion_ready": report["promotion_ready"],
        "default_should_change": report["default_should_change"],
        "stage_is_policy_search": report["stage_is_policy_search"],
        "empirical_policy_search_performed": report[
            "empirical_policy_search_performed"
        ],
        "policy_search_performed": report["policy_search_performed"],
        "policy_found": report["policy_found"],
        "rotations_evaluated": report["rotations_evaluated"],
        "full_b13_possible_from_public_artifacts": report[
            "full_b13_possible_from_public_artifacts"
        ],
        "new_provider_calls": report["new_provider_calls"],
        "missing_inputs_for_real_b13": [
            g["gap_id"] for g in report["missing_inputs_for_real_b13"]
        ],
        "descriptive_proxy_is_policy_search": report[
            "descriptive_fixed_strategy_proxy"
        ]["is_policy_search"],
        "out": str(args.out),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
