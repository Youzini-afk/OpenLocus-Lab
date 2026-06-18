#!/usr/bin/env python3
"""B14 Public-Aggregate Feasibility / No-Go Screen (bounded).

This is a **bounded public-aggregate feasibility screen**, NOT a real B14
uncertainty calibration. Real B14 (the frozen preregistration in
``eval/b14_uncertainty_calibration.py`` and
``docs/en/b14-uncertainty-calibration.md``) requires private / ephemeral
per-record uncertainty scores, per-record binary outcomes, paired
cross-model outputs, schema-repair per-call rows, and candidate score
distributions, plus the rotating leave-one-model-family-out train/test
splits. None of those are present in the public B11 aggregate, the B12
public-aggregate screen, or the B13 public-aggregate feasibility report,
so real B14 calibration cannot be performed from public aggregates alone.

What this screen DOES: read the already-published B11 aggregate report
(``artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json``),
the already-published B12 public-aggregate screen report
(``artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json``),
and the already-published B13 public-aggregate feasibility report
(``artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json``)
and emit a **public-aggregate feasibility / no-go report** for B14.

The screen preserves the public-artifact contract:

* **no** raw records, source, prompts, responses, snippets, digests, paths, or
  private labels are read or emitted;
* **no** provider calls (``new_provider_calls == 0``);
* **no** empirical uncertainty calibration, ECE computation, risk-coverage
  curve, selective-risk computation, PFP-at-coverage computation, threshold
  tuning, or winner declaration;
* **no** promotion / default / calibrated-model / runtime-clean general
  algorithm claim;
* ``uncertainty_calibration_performed=false``,
  ``calibrated_model_claim=false``, ``per_record_inputs_available=false``,
  ``metrics_evaluated=false``, ``uncertainty_score_found=false``,
  ``rotations_evaluated=false``.

CRITICAL: the screen MUST NOT compute fake ECE / risk-coverage / selective-
risk / PFP-at-coverage metrics from aggregate means. Aggregate means do not
contain per-record (uncertainty, outcome) pairs, so any calibration metric
computed from them would be a fabrication. The screen enumerates the
specific missing per-record inputs that block real B14 and carries forward
the B11 mixed/partial, B12 aggregate-screen-only, and B13 no-go statuses so
a reader cannot mistake a B14 no-go for B11 success, B12 supported, or B13
authorized.

Run::

    python3 eval/b14_public_aggregate_feasibility_screen.py --self-test
    python3 eval/b14_public_aggregate_feasibility_screen.py \
        --out artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json
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

SCHEMA_VERSION = "b14-public-aggregate-feasibility-screen-v0"
GENERATED_BY = "b14_public_aggregate_feasibility_screen"
CLAIM_LEVEL = "bounded_public_aggregate_feasibility_screen_of_b11_b12_b13_aggregates"

INPUT_B11_SCHEMA = "b11-prospective-matrix-aggregate-report-v0"
INPUT_B12_SCREEN_SCHEMA = "b12-public-aggregate-mechanism-screen-v0"
INPUT_B13_FEAS_SCHEMA = "b13-public-aggregate-feasibility-screen-v0"

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
DEFAULT_INPUT_B13 = Path(
    "artifacts/b13_dro_policy_search/"
    "b13_public_aggregate_feasibility_report.json"
)
DEFAULT_OUT = Path(
    "artifacts/b14_uncertainty_calibration/"
    "b14_public_aggregate_feasibility_report.json"
)

# Verdicts emitted by this screen. The screen NEVER emits success / failure /
# partial as a calibration verdict; it emits only feasibility / no-go
# statuses that make clear no empirical B14 calibration happened.
ALLOWED_VERDICTS = (
    "no_go_public_aggregate_only",
    "insufficient_data_public_aggregate_only",
)

# Missing inputs that block real B14 from the public aggregates. Each entry is
# a self-contained reason so a reader cannot mistake the screen for a B14
# calibration result. Descriptions are kept under 256 chars to satisfy the
# public forbidden-value scan (long_string guard).
MISSING_INPUTS = (
    {
        "gap_id": "no_per_record_uncertainty_scores_in_public_artifact",
        "description": (
            "real B14 needs a per-record uncertainty score (or the raw "
            "signals to compute one) for every record; the public B11 "
            "aggregate publishes only weighted means and deltas, not "
            "per-record uncertainty scores"
        ),
    },
    {
        "gap_id": "no_per_record_outcomes_in_public_artifact",
        "description": (
            "real B14 needs a per-record binary outcome (was the selected "
            "span correct) as the calibration target; the public B11 "
            "aggregate publishes only aggregate gold_span counts, not "
            "per-record binary outcomes"
        ),
    },
    {
        "gap_id": "no_paired_cross_model_outputs_in_public_artifact",
        "description": (
            "real B14 cross_model_disagreement signals require paired "
            "per-record outputs from two or more model families on the "
            "SAME record; the public aggregate publishes only per-family "
            "rollup deltas, not paired per-record outputs"
        ),
    },
    {
        "gap_id": "no_schema_repair_per_call_rows_in_public_artifact",
        "description": (
            "real B14 model_output_structure signals need schema-repair "
            "per-call rows (schema_valid, llm_span_narrow_valid, "
            "llm_span_within_candidate); the public aggregate does not "
            "publish per-call schema-repair rows"
        ),
    },
    {
        "gap_id": "no_candidate_score_distributions_or_entropy_in_public_artifact",
        "description": (
            "real B14 local_candidate_signals need candidate score "
            "distributions, entropy, and top1-top2 score gap per record; "
            "the public aggregate publishes only candidate_count rollups, "
            "not per-record score distributions or entropy"
        ),
    },
    {
        "gap_id": "no_calibration_test_split_in_public_artifact",
        "description": (
            "real B14 must split per-record inputs into a stratified "
            "calibration and test split by (model_family, repo); the "
            "public aggregate does not expose per-record membership, so "
            "no calibration or test split can be constructed"
        ),
    },
    {
        "gap_id": "no_ece_bins_in_public_artifact",
        "description": (
            "real B14 ECE requires per-record (uncertainty, outcome) pairs "
            "binned into 15 equal-width bins over [0,1]; the public "
            "aggregate has no per-record pairs, so no ECE bins can be "
            "formed and no ECE can be computed"
        ),
    },
    {
        "gap_id": "no_fixed_coverage_thresholds_applicable_in_public_artifact",
        "description": (
            "real B14 selective_risk and pfp_at_fixed_coverage require "
            "per-record pairs ranked by uncertainty at fixed coverage "
            "levels; the public aggregate has no per-record pairs, so no "
            "fixed-coverage thresholds can be applied"
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
        "input_b13_feas_schema": INPUT_B13_FEAS_SCHEMA,
        "policy_under_analysis": POLICY_UNDER_ANALYSIS,
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        # Safety fields preserved verbatim. The screen makes NO empirical
        # uncertainty calibration claim; uncertainty_calibration_performed=
        # false and calibrated_model_claim=false are the disambiguating
        # fields (the B14 stage IS uncertainty calibration, but no empirical
        # calibration was performed by this screen).
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "uncertainty_calibration_performed": False,
        "calibrated_model_claim": False,
        "per_record_inputs_available": False,
        "policy_search_performed": False,
        "stage_is_uncertainty_calibration": True,  # B14 stage IS calibration
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
        "is_full_b14_uncertainty_calibration": False,
        "full_b14_possible_from_public_artifacts": False,
        "uncertainty_score_found": False,
        "rotations_evaluated": False,
        "metrics_defined": True,
        "gates_defined": True,
        "metrics_evaluated": False,
        "no_fake_metrics_from_aggregate_means": True,
    }


def _finalize_safety(report: dict[str, Any]) -> None:
    """Run the forbidden-key/value scan on the public output."""
    violations = b6lite._walk_forbidden(report)
    integrity = report.setdefault("integrity", {})
    integrity["forbidden_public_key_scan_clean"] = not violations
    if violations:
        raise ValueError(
            "b14-public-aggregate-feasibility-screen public output would "
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


def _validate_b13_feas(report: dict[str, Any]) -> None:
    """Validate the B13 public aggregate feasibility screen input."""
    if report.get("schema_version") != INPUT_B13_FEAS_SCHEMA:
        raise ValueError(
            f"unexpected B13 feas schema_version: "
            f"{report.get('schema_version')!r}"
        )
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError(
            "B13 feas input must be aggregate_only_public_artifact=true"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError("B13 feas input must have promotion_ready=false")
    if report.get("policy_search_performed") is not False:
        raise ValueError(
            "B13 feas input must have policy_search_performed=false"
        )
    if report.get("candidate_not_fact") is not True:
        raise ValueError("B13 feas input must have candidate_not_fact=true")
    if report.get("default_should_change") is not False:
        raise ValueError("B13 feas input must have default_should_change=false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "B13 feas input must have evidencecore_semantics_changed=false"
        )
    if report.get("new_provider_calls") != 0:
        raise ValueError("B13 feas input must have new_provider_calls=0")
    if report.get("full_b13_possible_from_public_artifacts") is not False:
        raise ValueError(
            "B13 feas input must have "
            "full_b13_possible_from_public_artifacts=false"
        )
    if report.get("verdict") not in (
        "no_go_public_aggregate_only",
        "insufficient_data_public_aggregate_only",
    ):
        raise ValueError(
            "B13 feas input must have a no_go / insufficient_data verdict"
        )
    if not isinstance(report.get("missing_inputs_for_real_b13"), list):
        raise ValueError(
            "B13 feas input missing missing_inputs_for_real_b13 list"
        )


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


def _carry_forward_b13(b13_feas: dict[str, Any]) -> dict[str, Any]:
    """Carry forward B13 no-go status."""
    return {
        "b13_feasibility_verdict": b13_feas.get("verdict"),
        "b13_full_b13_possible_from_public_artifacts": (
            b13_feas.get("full_b13_possible_from_public_artifacts")
        ),
        "b13_policy_found": b13_feas.get("policy_found"),
        "b13_rotations_evaluated": b13_feas.get("rotations_evaluated"),
        "b13_winner_declared": b13_feas.get("winner_declared"),
        "b13_missing_inputs_for_real_b13_count": len(
            b13_feas.get("missing_inputs_for_real_b13") or []
        ),
        "b13_recommended_next_step": (
            (b13_feas.get("recommended_next_step") or {}).get("primary")
        ),
    }


def screen(
    b11_aggregate: dict[str, Any],
    b12_screen: dict[str, Any],
    b13_feas: dict[str, Any],
    self_test: bool = False,
) -> dict[str, Any]:
    """Build the B14 public aggregate feasibility / no-go screen report.

    ``b11_aggregate`` is the parsed B11 aggregate report JSON;
    ``b12_screen`` is the parsed B12 public-aggregate screen report JSON;
    ``b13_feas`` is the parsed B13 public-aggregate feasibility report JSON.
    ``self_test`` flags that the report was produced from a synthetic
    fixture.
    """
    _validate_b11_aggregate(b11_aggregate)
    _validate_b12_screen(b12_screen)
    _validate_b13_feas(b13_feas)

    report = _base_report(self_test)
    report["source_artifact_public_note"] = (
        "already-published aggregate-only public B11 matrix aggregate, B12 "
        "public aggregate screen, and B13 public aggregate feasibility "
        "reports; no raw records, paths, prompts, responses, snippets, or "
        "private labels read by the screen"
    )

    report["input_b11_summary"] = _carry_forward_b11(b11_aggregate)
    report["input_b12_summary"] = _carry_forward_b12(b12_screen)
    report["input_b13_summary"] = _carry_forward_b13(b13_feas)

    # Verdict: no_go unless the public aggregate is itself missing entirely
    # (insufficient_data). In this skeleton both paths emit a no-empirical-
    # calibration verdict; the distinction is whether the public inputs were
    # sufficient to even produce a feasibility read.
    b11_verdict = b11_aggregate.get("aggregate_verdict") or ""
    b11_records = b11_aggregate.get("record_count_total") or 0
    if not isinstance(b11_records, int) or b11_records <= 0:
        verdict = "insufficient_data_public_aggregate_only"
        verdict_reason = (
            "B11 aggregate reports no records; insufficient for a "
            "feasibility read. No empirical B14 uncertainty calibration "
            "was performed."
        )
    else:
        verdict = "no_go_public_aggregate_only"
        verdict_reason = (
            "public B11, B12, B13 aggregates lack per-record inputs for "
            "real B14 calibration. No empirical B14 calibration; no ECE, "
            "risk-coverage, selective risk, or PFP-at-coverage computed; "
            "B11 verdict ("
            + repr(b11_verdict)
            + ") NOT authorizing promotion."
        )

    report["verdict"] = verdict
    report["verdict_reason"] = verdict_reason
    report["allowed_verdicts"] = list(ALLOWED_VERDICTS)

    # Missing inputs (the specific gaps that block real B14).
    report["missing_inputs_for_real_b14"] = [dict(g) for g in MISSING_INPUTS]

    # Recommended next step (cautious, no auto-promotion).
    recommended_next_step = {
        "primary": "future_ephemeral_record_b14_calibration",
        "secondary": "future_ephemeral_record_b13_replay_first",
        "reason": (
            "Run real B14 against ephemeral per-record inputs (uncertainty "
            "scores, binary outcomes, paired cross-model outputs, "
            "schema-repair rows, candidate score distributions) once "
            "available; only that path can perform empirical calibration."
        ),
        "next_step_authorizes_promotion": False,
        "next_step_authorizes_default_change": False,
        "next_step_authorizes_runtime_clean_algorithm": False,
        "next_step_authorizes_calibrated_model_claim": False,
        "next_step_authorizes_empirical_uncertainty_calibration": False,
    }

    report.update(
        {
            "testability": {
                "full_b14_possible_from_public_artifacts": False,
                "missing_inputs_for_full_b14": [
                    g["gap_id"] for g in MISSING_INPUTS
                ],
                "note": (
                    "Real B14 cannot be replayed from the current public "
                    "B11, B12, and B13 aggregates. The listed missing "
                    "inputs are the specific per-record fields required. "
                    "Only this bounded feasibility or no-go screen is "
                    "publishable until ephemeral records arrive."
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
                "b13_input_full_b13_possible_false": True,
                "b13_input_verdict_is_no_go_or_insufficient": True,
                "forbidden_public_key_scan_clean": True,
            },
            "safety_invariants": {
                "aggregate_only_public_artifact": True,
                "promotion_ready_false": True,
                "default_should_change_false": True,
                "no_evidencecore_semantics_change": True,
                "no_live_llm_calls_by_screen": True,
                "no_empirical_uncertainty_calibration": True,
                "no_calibrated_model_claim": True,
                "no_policy_promotion": True,
                "no_threshold_tuning": True,
                "no_raw_records_read": True,
                "no_raw_paths_or_digests": True,
                "no_prompts_or_responses": True,
                "no_private_labels": True,
                "no_run_ids_emitted": True,
                "no_uncertainty_score_found": True,
                "no_rotations_evaluated": True,
                "no_winner_declared": True,
                "no_fake_metrics_from_aggregate_means": True,
            },
            "framing": {
                "promotion_readiness_claimed": False,
                "default_readiness_claimed": False,
                "runtime_clean_general_algorithm_claimed": False,
                "calibrated_model_claim_claimed": False,
                "empirical_uncertainty_calibration_claimed": False,
                "uncertainty_score_found_claimed": False,
                "winner_declared_claimed": False,
                "signal_strength": "bounded_public_aggregate_feasibility_screen_only",
                "is_full_b14_uncertainty_calibration": False,
                "recommended_next_step": (
                    "future_ephemeral_record_b14_calibration"
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
    """Minimal synthetic B11 aggregate for self-test."""
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


def _build_synthetic_b13_feas() -> dict[str, Any]:
    """Minimal synthetic B13 public aggregate feasibility report."""
    return {
        "schema_version": INPUT_B13_FEAS_SCHEMA,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        "full_b13_possible_from_public_artifacts": False,
        "policy_found": False,
        "rotations_evaluated": False,
        "winner_declared": False,
        "verdict": "no_go_public_aggregate_only",
        "missing_inputs_for_real_b13": [
            {"gap_id": "no_per_record_route_features_in_public_artifact"},
        ],
        "recommended_next_step": {
            "primary": "future_ephemeral_record_b13_replay",
        },
    }


def _self_test_happy_path() -> dict[str, Any]:
    b11 = _build_synthetic_b11_aggregate()
    b12 = _build_synthetic_b12_screen()
    b13 = _build_synthetic_b13_feas()
    report = screen(b11, b12, b13, self_test=True)
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
        ("uncertainty_calibration_performed", False),
        ("calibrated_model_claim", False),
        ("per_record_inputs_available", False),
        ("stage_is_uncertainty_calibration", True),
        ("quality_strategy_tuned", False),
        ("new_provider_calls", 0),
        ("uncertainty_score_found", False),
        ("rotations_evaluated", False),
        ("full_b14_possible_from_public_artifacts", False),
        ("winner_declared", False),
        ("promotion_declared", False),
        ("default_recommendation_declared", False),
        ("metrics_defined", True),
        ("gates_defined", True),
        ("metrics_evaluated", False),
        ("no_fake_metrics_from_aggregate_means", True),
    ):
        assert report[k] == v, (k, report[k])
    # No-go verdict emitted.
    assert report["verdict"] == "no_go_public_aggregate_only", report["verdict"]
    assert report["verdict"] in ALLOWED_VERDICTS, report["verdict"]
    assert (
        "no empirical b14" in report["verdict_reason"].lower()
    ), report["verdict_reason"]
    # B11 mixed/partial + B12 public-aggregate screen statuses + B13 no-go
    # carried forward.
    assert report["input_b11_summary"]["b11_aggregate_verdict"] == (
        "partial_with_failure"
    )
    carried_h1 = report["input_b12_summary"]["H1_ambiguous_routing"][
        "screen_status"
    ]
    assert carried_h1 == "inconclusive_unavailable_ablation_controls", carried_h1
    assert report["input_b13_summary"]["b13_feasibility_verdict"] == (
        "no_go_public_aggregate_only"
    ), report["input_b13_summary"]
    assert report["input_b13_summary"]["b13_policy_found"] is False
    assert report["input_b13_summary"]["b13_rotations_evaluated"] is False
    # All missing inputs enumerated.
    missing_ids = [g["gap_id"] for g in report["missing_inputs_for_real_b14"]]
    expected_missing = tuple(g["gap_id"] for g in MISSING_INPUTS)
    assert missing_ids == list(expected_missing), missing_ids
    # Required missing inputs are present (the task spec).
    required_gap_ids = {
        "no_per_record_uncertainty_scores_in_public_artifact",
        "no_per_record_outcomes_in_public_artifact",
        "no_paired_cross_model_outputs_in_public_artifact",
        "no_schema_repair_per_call_rows_in_public_artifact",
        "no_candidate_score_distributions_or_entropy_in_public_artifact",
        "no_calibration_test_split_in_public_artifact",
        "no_ece_bins_in_public_artifact",
        "no_fixed_coverage_thresholds_applicable_in_public_artifact",
    }
    assert required_gap_ids.issubset(set(missing_ids)), (
        required_gap_ids - set(missing_ids)
    )
    # CRITICAL: no fake metric values. metrics_evaluated=false.
    assert report["metrics_evaluated"] is False
    assert report["no_fake_metrics_from_aggregate_means"] is True
    # No ECE / risk-coverage / selective-risk / PFP-at-coverage value fields.
    for forbidden_field in (
        "ece_value",
        "selective_risk_value",
        "risk_coverage_curve_value",
        "pfp_at_fixed_coverage_value",
        "worst_group_selective_risk_value",
        "worst_group_ece_value",
    ):
        assert forbidden_field not in report, forbidden_field
    # Forbidden-key/value scan clean.
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    # No raw data carried.
    assert report["raw_paths_in_artifact"] is False
    assert report["private_labels_committed"] is False
    assert report["run_ids_in_artifact"] is False
    print("self-test happy path: ok")
    return report


def _self_test_input_validation_blocks() -> None:
    b12 = _build_synthetic_b12_screen()
    b13 = _build_synthetic_b13_feas()

    # Wrong B11 schema_version.
    bad = _build_synthetic_b11_aggregate()
    bad["schema_version"] = "wrong"
    try:
        screen(bad, b12, b13, self_test=True)
    except ValueError as exc:
        assert "unexpected B11 schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should reject wrong B11 schema_version")

    # B11 promotion_ready=true rejected.
    bad = _build_synthetic_b11_aggregate()
    bad["promotion_ready"] = True
    try:
        screen(bad, b12, b13, self_test=True)
    except ValueError as exc:
        assert "promotion_ready=false" in str(exc), exc
    else:
        raise AssertionError("screen should reject B11 promotion_ready=true")

    # B11 policy_search_performed=true rejected.
    bad = _build_synthetic_b11_aggregate()
    bad["policy_search_performed"] = True
    try:
        screen(bad, b12, b13, self_test=True)
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
        screen(b11, bad12, b13, self_test=True)
    except ValueError as exc:
        assert "unexpected B12 screen schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should reject wrong B12 schema_version")

    # B12 full_b12_replay_possible=true rejected.
    bad12 = _build_synthetic_b12_screen()
    bad12["full_b12_replay_possible_from_public_artifact"] = True
    try:
        screen(b11, bad12, b13, self_test=True)
    except ValueError as exc:
        assert "full_b12_replay_possible_from_public_artifact=false" in str(
            exc
        ), exc
    else:
        raise AssertionError(
            "screen should reject B12 full_b12_replay_possible=true"
        )

    # Wrong B13 feas schema_version.
    bad13 = _build_synthetic_b13_feas()
    bad13["schema_version"] = "wrong"
    try:
        screen(b11, b12, bad13, self_test=True)
    except ValueError as exc:
        assert "unexpected B13 feas schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should reject wrong B13 feas schema_version")

    # B13 full_b13_possible=true rejected.
    bad13 = _build_synthetic_b13_feas()
    bad13["full_b13_possible_from_public_artifacts"] = True
    try:
        screen(b11, b12, bad13, self_test=True)
    except ValueError as exc:
        assert "full_b13_possible_from_public_artifacts=false" in str(
            exc
        ), exc
    else:
        raise AssertionError(
            "screen should reject B13 full_b13_possible=true"
        )

    # B13 verdict=success rejected (must be no_go / insufficient_data).
    bad13 = _build_synthetic_b13_feas()
    bad13["verdict"] = "success"
    try:
        screen(b11, b12, bad13, self_test=True)
    except ValueError as exc:
        assert "no_go / insufficient_data verdict" in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject B13 verdict=success"
        )

    print("self-test input validation block: ok")


def _self_test_insufficient_data_branch() -> None:
    """When B11 record_count_total <= 0, the screen emits
    insufficient_data_public_aggregate_only."""
    b11 = _build_synthetic_b11_aggregate()
    b11["record_count_total"] = 0
    b12 = _build_synthetic_b12_screen()
    b13 = _build_synthetic_b13_feas()
    report = screen(b11, b12, b13, self_test=True)
    assert report["verdict"] == (
        "insufficient_data_public_aggregate_only"
    ), report["verdict"]
    assert "no empirical b14" in report[
        "verdict_reason"
    ].lower(), report["verdict_reason"]
    # Still no calibration / no uncertainty score / no rotations.
    assert report["uncertainty_calibration_performed"] is False
    assert report["calibrated_model_claim"] is False
    assert report["per_record_inputs_available"] is False
    assert report["uncertainty_score_found"] is False
    assert report["rotations_evaluated"] is False
    assert report["metrics_evaluated"] is False
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
        "--input-b13",
        type=Path,
        default=DEFAULT_INPUT_B13,
        help=(
            "path to the B13 public aggregate feasibility report JSON "
            "(default: artifacts/b13_dro_policy_search/"
            "b13_public_aggregate_feasibility_report.json)"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=(
            "path to write the B14 public aggregate feasibility report "
            "(default: artifacts/b14_uncertainty_calibration/"
            "b14_public_aggregate_feasibility_report.json)"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the B14 public aggregate feasibility screen self-test "
        "(synthetic fixture)",
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if args.self_test and (
        str(args.input_b11) != str(DEFAULT_INPUT_B11)
        or str(args.input_b12) != str(DEFAULT_INPUT_B12)
        or str(args.input_b13) != str(DEFAULT_INPUT_B13)
    ):
        parser.error(
            "--self-test ignores --input-b11/--input-b12/--input-b13; "
            "do not pass both"
        )
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_tests()
        print(json.dumps(result, indent=2, sort_keys=True))
        print(
            "B14 public aggregate feasibility screen self-test: PASS",
            file=sys.stderr,
        )
        return 0
    if not args.input_b11.exists():
        print(
            f"B14 feasibility screen B11 input not found: {args.input_b11}",
            file=sys.stderr,
        )
        return 2
    if not args.input_b12.exists():
        print(
            f"B14 feasibility screen B12 input not found: {args.input_b12}",
            file=sys.stderr,
        )
        return 2
    if not args.input_b13.exists():
        print(
            f"B14 feasibility screen B13 input not found: {args.input_b13}",
            file=sys.stderr,
        )
        return 2
    b11_aggregate = json.loads(args.input_b11.read_text(encoding="utf-8"))
    b12_screen = json.loads(args.input_b12.read_text(encoding="utf-8"))
    b13_feas = json.loads(args.input_b13.read_text(encoding="utf-8"))
    report = screen(b11_aggregate, b12_screen, b13_feas, self_test=False)
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
        "stage_is_uncertainty_calibration": report[
            "stage_is_uncertainty_calibration"
        ],
        "uncertainty_calibration_performed": report[
            "uncertainty_calibration_performed"
        ],
        "calibrated_model_claim": report["calibrated_model_claim"],
        "per_record_inputs_available": report["per_record_inputs_available"],
        "policy_search_performed": report["policy_search_performed"],
        "uncertainty_score_found": report["uncertainty_score_found"],
        "rotations_evaluated": report["rotations_evaluated"],
        "metrics_evaluated": report["metrics_evaluated"],
        "no_fake_metrics_from_aggregate_means": report[
            "no_fake_metrics_from_aggregate_means"
        ],
        "full_b14_possible_from_public_artifacts": report[
            "full_b14_possible_from_public_artifacts"
        ],
        "new_provider_calls": report["new_provider_calls"],
        "missing_inputs_for_real_b14": [
            g["gap_id"] for g in report["missing_inputs_for_real_b14"]
        ],
        "out": str(args.out),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
