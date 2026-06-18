#!/usr/bin/env python3
"""B16 Public-Aggregate Feasibility / No-Go Screen (bounded).

This is a **bounded public-aggregate feasibility screen**, NOT a real B16
downstream coding-agent evaluation. Real B16 (the frozen preregistration
in ``eval/b16_downstream_agent_evaluation.py`` and
``docs/en/b16-downstream-agent-evaluation.md``) requires private /
ephemeral per-run paired agent outputs: paired live downstream agent
runs, per-run agent event logs, per-run patches/diffs, per-run test
execution results, per-run solve labels, per-run first-file-before-edit
events, per-run wrong-file-edit annotations, per-run tool-call/token/
latency/cost rows, per-run isolated fresh workspace proof, per-run
randomized arm order, and a task oracle/hidden-test manifest. None of
those are present in the public B11 matrix aggregate, the B12 public
screen, the B13 public feasibility report, the B14 public feasibility
report, or the B15 public prior-screen report, so real B16 downstream
agent evaluation cannot be performed from public aggregates alone.

What this screen DOES: read the already-published B11 matrix aggregate
report
(``artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json``),
the already-published B12 public-aggregate screen report, the B13
public-aggregate feasibility report, the B14 public-aggregate
feasibility report, and the B15 public-aggregate prior-screen report,
and emit a **public-aggregate feasibility / no-go report** for B16.

The screen preserves the public-artifact contract:

* **no** raw records, task IDs, repo IDs, candidate IDs, paths, spans,
  snippets, prompts, responses, diffs, patches, test execution results,
  solve labels, first-file-before-edit events, wrong-file-edit
  annotations, tool-call/token/latency/cost rows, agent event logs,
  gold spans, private labels, provider keys, base URLs, API keys, or
  digests are read or emitted;
* **no** provider calls (``new_provider_calls == 0``);
* **no** live downstream agent runs, no patch execution, no
  agent-behavior metrics, no solve-rate evaluation, no tool-call/token/
  latency/cost computation, no retrieval-variant promotion, no winner
  declaration;
* ``downstream_agent_runs_performed=false``,
  ``patch_execution_performed=false``,
  ``agent_behavior_metrics_evaluated=false``,
  ``solve_rate_evaluated=false``,
  ``per_record_inputs_available=false``,
  ``metrics_evaluated=false``.

CRITICAL: the screen MUST NOT compute fake solve-rate /
correct-file-before-first-edit / wrong-file-edits / tool-call / token /
latency / cost metrics from retrieval aggregates. The B11/B12/B13/B14/
B15 artifacts are retrieval/context candidate research; they do NOT
contain per-run paired agent outputs, so any downstream agent metric
computed from them would be a fabrication. The screen enumerates the
specific missing per-run inputs that block real B16 and carries forward
the B11 partial_with_failure and the B12/B13/B14/B15 no-go or
screen-only statuses so a reader cannot mistake a B16 no-go for B11
success, B12 supported, B13 authorized, B14 calibrated, or B15
PackPolicy learning.

Important claim boundary: the B10-B15 retrieval/context candidate
research does NOT prove downstream coding-agent value. Retrieval
improvements are NOT downstream agent improvements. This screen makes
no claim that retrieval, B15 PackPolicy, or any retrieval-variant
candidate improves a downstream coding agent, changes a default,
promotes a retrieval variant, or changes EvidenceCore semantics.

Run::

    python3 eval/b16_public_aggregate_feasibility_screen.py --self-test
    python3 eval/b16_public_aggregate_feasibility_screen.py \
        --out artifacts/b16_downstream_agent_evaluation/b16_public_aggregate_feasibility_report.json
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

SCHEMA_VERSION = "b16-public-aggregate-feasibility-screen-v0"
GENERATED_BY = "b16_public_aggregate_feasibility_screen"
CLAIM_LEVEL = (
    "bounded_public_aggregate_feasibility_screen_of_b11_b12_b13_b14_b15_aggregates"
)

INPUT_B11_SCHEMA = "b11-prospective-matrix-aggregate-report-v0"
INPUT_B12_SCREEN_SCHEMA = "b12-public-aggregate-mechanism-screen-v0"
INPUT_B13_FEAS_SCHEMA = "b13-public-aggregate-feasibility-screen-v0"
INPUT_B14_FEAS_SCHEMA = "b14-public-aggregate-feasibility-screen-v0"
INPUT_B15_PRIOR_SCHEMA = "b15-public-aggregate-prior-screen-v0"

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
DEFAULT_INPUT_B14 = Path(
    "artifacts/b14_uncertainty_calibration/"
    "b14_public_aggregate_feasibility_report.json"
)
DEFAULT_INPUT_B15 = Path(
    "artifacts/b15_context_pack_policy/"
    "b15_public_aggregate_prior_screen_report.json"
)
DEFAULT_OUT = Path(
    "artifacts/b16_downstream_agent_evaluation/"
    "b16_public_aggregate_feasibility_report.json"
)

# Verdicts emitted by this screen. The screen NEVER emits success /
# failure / partial as a downstream-agent verdict; it emits only
# feasibility / no-go statuses that make clear no empirical B16
# downstream agent evaluation happened.
ALLOWED_VERDICTS = (
    "no_go_public_aggregate_only",
    "insufficient_data_public_aggregate_only",
)

# Missing inputs that block real B16 from the public aggregates. Each
# entry is a self-contained reason so a reader cannot mistake the
# screen for a B16 downstream agent result. Descriptions are kept under
# 256 chars to satisfy the public forbidden-value scan (long_string
# guard) and avoid the path-separator pattern.
MISSING_INPUTS = (
    {
        "gap_id": "no_live_paired_agent_runs_in_public_artifact",
        "description": (
            "real B16 needs paired live downstream agent runs of the "
            "same task under two arms; the public B11 B12 B13 B14 B15 "
            "aggregates publish only retrieval context research with "
            "no downstream agent runs"
        ),
    },
    {
        "gap_id": "no_agent_event_logs_in_public_artifact",
        "description": (
            "real B16 needs per-run agent event logs capturing tool "
            "calls and first-file-before-edit timing; the public "
            "aggregates contain no agent event logs"
        ),
    },
    {
        "gap_id": "no_patches_or_diffs_in_public_artifact",
        "description": (
            "real B16 needs per-run patches or diffs the agent produced "
            "to verify the edit landed in the right file; the public "
            "aggregates contain no patches or diffs"
        ),
    },
    {
        "gap_id": "no_test_execution_results_in_public_artifact",
        "description": (
            "real B16 needs per-run test execution results to label "
            "whether the agent solved the task; the public aggregates "
            "contain no test execution results"
        ),
    },
    {
        "gap_id": "no_solve_labels_in_public_artifact",
        "description": (
            "real B16 needs per-run solve labels as the primary outcome "
            "target; the public aggregates publish only retrieval gold "
            "span counts, not downstream solve labels"
        ),
    },
    {
        "gap_id": "no_first_file_before_first_edit_event_in_public_artifact",
        "description": (
            "real B16 needs the first-file-before-first-edit event per "
            "run to measure correct-file-before-first-edit; the public "
            "aggregates contain no first-file-before-first-edit events"
        ),
    },
    {
        "gap_id": "no_wrong_file_edit_annotations_in_public_artifact",
        "description": (
            "real B16 needs per-run wrong-file-edit annotations to "
            "measure wrong-file-edits; the public aggregates contain "
            "no wrong-file-edit annotations"
        ),
    },
    {
        "gap_id": (
            "no_tool_calls_tokens_latency_cost_per_run_in_public_artifact"
        ),
        "description": (
            "real B16 needs per-run tool-call token latency cost rows; "
            "the public aggregates publish no per-run tool-call token "
            "latency or cost rows"
        ),
    },
    {
        "gap_id": "no_randomized_arm_order_in_public_artifact",
        "description": (
            "real B16 needs randomized arm order per task to "
            "deconfound arm from run order; the public aggregates "
            "contain no randomized arm order"
        ),
    },
    {
        "gap_id": "no_isolated_workspace_proof_in_public_artifact",
        "description": (
            "real B16 needs per-run isolated fresh workspace proof so "
            "runs do not leak state; the public aggregates contain no "
            "isolated fresh workspace proof"
        ),
    },
    {
        "gap_id": "no_task_oracle_or_hidden_test_manifest_in_public_artifact",
        "description": (
            "real B16 needs a task oracle or hidden-test manifest to "
            "label solve and tests-pass; the public aggregates contain "
            "no task oracle or hidden-test manifest"
        ),
    },
    {
        "gap_id": "no_operational_parity_proof_in_public_artifact",
        "description": (
            "real B16 needs operational parity proof that arms share "
            "the same budget tools prompt except the retrieval variant "
            "with no cross-run memory; the public aggregates contain "
            "no operational parity proof"
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
        "input_b14_feas_schema": INPUT_B14_FEAS_SCHEMA,
        "input_b15_prior_schema": INPUT_B15_PRIOR_SCHEMA,
        "policy_under_analysis": POLICY_UNDER_ANALYSIS,
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        # Safety fields preserved verbatim. The screen makes NO empirical
        # downstream agent evaluation claim; downstream_agent_runs_performed
        # = false and solve_rate_evaluated=false are the disambiguating
        # fields (the B16 stage IS downstream agent evaluation, but no
        # empirical downstream agent runs were performed by this screen).
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "retrieval_variant_promoted": False,
        "stage_is_downstream_agent_evaluation": True,
        "downstream_agent_runs_performed": False,
        "patch_execution_performed": False,
        "agent_behavior_metrics_evaluated": False,
        "solve_rate_evaluated": False,
        "per_record_inputs_available": False,
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
        "raw_patches_diffs_stored": False,
        "raw_test_results_stored": False,
        "raw_solve_labels_stored": False,
        "raw_agent_event_logs_stored": False,
        "private_labels_committed": False,
        "gold_spans_in_artifact": False,
        "llm_output_not_evidence": True,
        "not_evidence": True,
        "promotion_declared": False,
        "default_recommendation_declared": False,
        "retrieval_variant_promotion_declared": False,
        "winner_declared": False,
        # Bounded-screen stance.
        "is_full_b16_downstream_agent_evaluation": False,
        "full_b16_possible_from_public_artifacts": False,
        "metrics_defined": True,
        "gates_defined": True,
        "metrics_evaluated": False,
        "no_fake_downstream_metrics_from_retrieval_aggregates": True,
    }


def _finalize_safety(report: dict[str, Any]) -> None:
    """Run the forbidden-key/value scan on the public output."""
    violations = b6lite._walk_forbidden(report)
    integrity = report.setdefault("integrity", {})
    integrity["forbidden_public_key_scan_clean"] = not violations
    if violations:
        raise ValueError(
            "b16-public-aggregate-feasibility-screen public output would "
            f"contain forbidden keys/values; first violations: "
            f"{violations[:5]}"
        )


# ---------------------------------------------------------------------------
# Input validators
# ---------------------------------------------------------------------------


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


def _validate_b14_feas(report: dict[str, Any]) -> None:
    """Validate the B14 public aggregate feasibility screen input."""
    if report.get("schema_version") != INPUT_B14_FEAS_SCHEMA:
        raise ValueError(
            f"unexpected B14 feas schema_version: "
            f"{report.get('schema_version')!r}"
        )
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError(
            "B14 feas input must be aggregate_only_public_artifact=true"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError("B14 feas input must have promotion_ready=false")
    if report.get("policy_search_performed") is not False:
        raise ValueError(
            "B14 feas input must have policy_search_performed=false"
        )
    if report.get("candidate_not_fact") is not True:
        raise ValueError("B14 feas input must have candidate_not_fact=true")
    if report.get("default_should_change") is not False:
        raise ValueError("B14 feas input must have default_should_change=false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "B14 feas input must have evidencecore_semantics_changed=false"
        )
    if report.get("new_provider_calls") != 0:
        raise ValueError("B14 feas input must have new_provider_calls=0")
    if report.get("full_b14_possible_from_public_artifacts") is not False:
        raise ValueError(
            "B14 feas input must have "
            "full_b14_possible_from_public_artifacts=false"
        )
    if report.get("verdict") not in (
        "no_go_public_aggregate_only",
        "insufficient_data_public_aggregate_only",
    ):
        raise ValueError(
            "B14 feas input must have a no_go / insufficient_data verdict"
        )
    if not isinstance(report.get("missing_inputs_for_real_b14"), list):
        raise ValueError(
            "B14 feas input missing missing_inputs_for_real_b14 list"
        )


def _validate_b15_prior(report: dict[str, Any]) -> None:
    """Validate the B15 public aggregate prior-screen input."""
    if report.get("schema_version") != INPUT_B15_PRIOR_SCHEMA:
        raise ValueError(
            f"unexpected B15 prior schema_version: "
            f"{report.get('schema_version')!r}"
        )
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError(
            "B15 prior input must be aggregate_only_public_artifact=true"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError("B15 prior input must have promotion_ready=false")
    if report.get("policy_search_performed") is not False:
        raise ValueError(
            "B15 prior input must have policy_search_performed=false"
        )
    if report.get("candidate_not_fact") is not True:
        raise ValueError("B15 prior input must have candidate_not_fact=true")
    if report.get("default_should_change") is not False:
        raise ValueError("B15 prior input must have default_should_change=false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "B15 prior input must have evidencecore_semantics_changed=false"
        )
    if report.get("new_provider_calls") != 0:
        raise ValueError("B15 prior input must have new_provider_calls=0")
    if report.get("full_b15_possible_from_public_artifacts") is not False:
        raise ValueError(
            "B15 prior input must have "
            "full_b15_possible_from_public_artifacts=false"
        )
    if report.get("verdict") not in (
        "no_go_public_aggregate_only",
        "prior_screen_only",
    ):
        raise ValueError(
            "B15 prior input must have a no_go or prior_screen_only verdict"
        )
    if not isinstance(report.get("missing_inputs_for_real_b15"), list):
        raise ValueError(
            "B15 prior input missing missing_inputs_for_real_b15 list"
        )


# ---------------------------------------------------------------------------
# Carry-forward summaries
# ---------------------------------------------------------------------------


def _carry_forward_b11(b11: dict[str, Any]) -> dict[str, Any]:
    """Carry forward B11 partial_with_failure status (public fields only)."""
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


def _carry_forward_b14(b14_feas: dict[str, Any]) -> dict[str, Any]:
    """Carry forward B14 no-go status."""
    return {
        "b14_feasibility_verdict": b14_feas.get("verdict"),
        "b14_full_b14_possible_from_public_artifacts": (
            b14_feas.get("full_b14_possible_from_public_artifacts")
        ),
        "b14_uncertainty_calibration_performed": (
            b14_feas.get("uncertainty_calibration_performed")
        ),
        "b14_calibrated_model_claim": b14_feas.get("calibrated_model_claim"),
        "b14_per_record_inputs_available": (
            b14_feas.get("per_record_inputs_available")
        ),
        "b14_uncertainty_score_found": b14_feas.get("uncertainty_score_found"),
        "b14_rotations_evaluated": b14_feas.get("rotations_evaluated"),
        "b14_metrics_evaluated": b14_feas.get("metrics_evaluated"),
        "b14_missing_inputs_for_real_b14_count": len(
            b14_feas.get("missing_inputs_for_real_b14") or []
        ),
        "b14_recommended_next_step": (
            (b14_feas.get("recommended_next_step") or {}).get("primary")
        ),
    }


def _carry_forward_b15(b15_prior: dict[str, Any]) -> dict[str, Any]:
    """Carry forward B15 prior-screen-only status."""
    return {
        "b15_prior_verdict": b15_prior.get("verdict"),
        "b15_full_b15_possible_from_public_artifacts": (
            b15_prior.get("full_b15_possible_from_public_artifacts")
        ),
        "b15_pack_policy_learned": b15_prior.get("pack_policy_learned"),
        "b15_atom_ablation_performed": b15_prior.get("atom_ablation_performed"),
        "b15_per_record_inputs_available": (
            b15_prior.get("per_record_inputs_available")
        ),
        "b15_candidate_policy_frozen": b15_prior.get("candidate_policy_frozen"),
        "b15_stages_evaluated": b15_prior.get("stages_evaluated"),
        "b15_winner_declared": b15_prior.get("winner_declared"),
        "b15_b2_prior_usable": b15_prior.get("b2_prior_usable"),
        "b15_b2_prior_claim_level": b15_prior.get("b2_prior_claim_level"),
        "b15_atom_level_inference_possible": (
            b15_prior.get("atom_level_inference_possible")
        ),
        "b15_role_specific_policy_possible": (
            b15_prior.get("role_specific_policy_possible")
        ),
        "b15_calibration_possible": b15_prior.get("calibration_possible"),
        "b15_new_live_runs_required": b15_prior.get("new_live_runs_required"),
        "b15_missing_inputs_for_real_b15_count": len(
            b15_prior.get("missing_inputs_for_real_b15") or []
        ),
    }


# ---------------------------------------------------------------------------
# Integrity
# ---------------------------------------------------------------------------


def _compute_integrity(
    b11: dict[str, Any],
    b12: dict[str, Any],
    b13: dict[str, Any],
    b14: dict[str, Any],
    b15: dict[str, Any],
) -> dict[str, Any]:
    """Compute the integrity block from actual validated booleans.

    Fail-closed: every ``all_inputs_*`` field is ``true`` ONLY when
    every input carries the corresponding boolean ``true`` (or the
    expected value). If any input lacks the field or carries the wrong
    value, the field is set to ``false`` with a reason.
    """
    inputs = (
        ("b11", b11),
        ("b12", b12),
        ("b13", b13),
        ("b14", b14),
        ("b15", b15),
    )

    def _all(field_name: str, expected: Any) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        for name, report in inputs:
            val = report.get(field_name)
            if val != expected:
                reasons.append(
                    f"{name} has {field_name}={val!r} (expected {expected!r})"
                )
        return (len(reasons) == 0), reasons

    agg_ok, agg_reasons = _all("aggregate_only_public_artifact", True)
    promo_ok, promo_reasons = _all("promotion_ready", False)
    polsearch_ok, polsearch_reasons = _all("policy_search_performed", False)
    cand_ok, cand_reasons = _all("candidate_not_fact", True)
    dsc_ok, dsc_reasons = _all("default_should_change", False)
    esc_ok, esc_reasons = _all("evidencecore_semantics_changed", False)
    qst_ok, qst_reasons = _all("quality_strategy_tuned", False)
    npc_ok, npc_reasons = _all("new_provider_calls", 0)

    integrity: dict[str, Any] = {
        "all_inputs_aggregate_only_public_artifact": agg_ok,
        "all_inputs_promotion_ready_false": promo_ok,
        "all_inputs_policy_search_performed_false": polsearch_ok,
        "all_inputs_candidate_not_fact": cand_ok,
        "all_inputs_default_should_change_false": dsc_ok,
        "all_inputs_evidencecore_semantics_changed_false": esc_ok,
        "all_inputs_quality_strategy_tuned_false": qst_ok,
        "all_inputs_new_provider_calls_zero": npc_ok,
        # B11 partial_with_failure carried forward.
        "b11_aggregate_verdict_is_partial_with_failure": (
            b11.get("aggregate_verdict") == "partial_with_failure"
        ),
        # B12 screen only.
        "b12_full_replay_possible_false": (
            b12.get("full_b12_replay_possible_from_public_artifact") is False
        ),
        # B13/B14 no-go or insufficient.
        "b13_input_verdict_is_no_go_or_insufficient": (
            b13.get("verdict")
            in ("no_go_public_aggregate_only", "insufficient_data_public_aggregate_only")
        ),
        "b13_input_full_b13_possible_false": (
            b13.get("full_b13_possible_from_public_artifacts") is False
        ),
        "b14_input_verdict_is_no_go_or_insufficient": (
            b14.get("verdict")
            in ("no_go_public_aggregate_only", "insufficient_data_public_aggregate_only")
        ),
        "b14_input_full_b14_possible_false": (
            b14.get("full_b14_possible_from_public_artifacts") is False
        ),
        # B15 prior-screen only (no_go or prior_screen_only).
        "b15_input_verdict_is_no_go_or_prior_screen_only": (
            b15.get("verdict")
            in ("no_go_public_aggregate_only", "prior_screen_only")
        ),
        "b15_input_full_b15_possible_false": (
            b15.get("full_b15_possible_from_public_artifacts") is False
        ),
        "b15_input_pack_policy_learned_false": (
            b15.get("pack_policy_learned") is False
        ),
        "b15_input_atom_ablation_performed_false": (
            b15.get("atom_ablation_performed") is False
        ),
        "forbidden_public_key_scan_clean": True,
    }
    if not agg_ok:
        integrity["all_inputs_aggregate_only_public_artifact_reasons"] = agg_reasons
    if not promo_ok:
        integrity["all_inputs_promotion_ready_false_reasons"] = promo_reasons
    if not polsearch_ok:
        integrity["all_inputs_policy_search_performed_false_reasons"] = (
            polsearch_reasons
        )
    if not cand_ok:
        integrity["all_inputs_candidate_not_fact_reasons"] = cand_reasons
    if not dsc_ok:
        integrity["all_inputs_default_should_change_false_reasons"] = dsc_reasons
    if not esc_ok:
        integrity["all_inputs_evidencecore_semantics_changed_false_reasons"] = (
            esc_reasons
        )
    if not qst_ok:
        integrity["all_inputs_quality_strategy_tuned_false_reasons"] = qst_reasons
    if not npc_ok:
        integrity["all_inputs_new_provider_calls_zero_reasons"] = npc_reasons
    return integrity


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------


def screen(
    b11_aggregate: dict[str, Any],
    b12_screen: dict[str, Any],
    b13_feas: dict[str, Any],
    b14_feas: dict[str, Any],
    b15_prior: dict[str, Any],
    self_test: bool = False,
) -> dict[str, Any]:
    """Build the B16 public aggregate feasibility / no-go screen report.

    ``b11_aggregate`` is the parsed B11 matrix aggregate report JSON;
    ``b12_screen`` is the parsed B12 public-aggregate screen report JSON;
    ``b13_feas`` is the parsed B13 public-aggregate feasibility report JSON;
    ``b14_feas`` is the parsed B14 public-aggregate feasibility report JSON;
    ``b15_prior`` is the parsed B15 public-aggregate prior-screen report
    JSON. ``self_test`` flags that the report was produced from a
    synthetic fixture.
    """
    _validate_b11_aggregate(b11_aggregate)
    _validate_b12_screen(b12_screen)
    _validate_b13_feas(b13_feas)
    _validate_b14_feas(b14_feas)
    _validate_b15_prior(b15_prior)

    report = _base_report(self_test)
    report["source_artifact_public_note"] = (
        "already-published aggregate-only public B11 B12 B13 B14 B15 "
        "reports; no raw records, paths, prompts, responses, snippets, "
        "diffs, patches, test results, solve labels, agent event logs, "
        "or private labels read by the screen"
    )

    report["input_b11_summary"] = _carry_forward_b11(b11_aggregate)
    report["input_b12_summary"] = _carry_forward_b12(b12_screen)
    report["input_b13_summary"] = _carry_forward_b13(b13_feas)
    report["input_b14_summary"] = _carry_forward_b14(b14_feas)
    report["input_b15_summary"] = _carry_forward_b15(b15_prior)

    # Verdict: no_go unless the public aggregate is itself missing entirely
    # (insufficient_data). In this skeleton both paths emit a
    # no-empirical-downstream-agent-evaluation verdict; the distinction
    # is whether the public inputs were sufficient to even produce a
    # feasibility read.
    b11_verdict = b11_aggregate.get("aggregate_verdict") or ""
    b11_records = b11_aggregate.get("record_count_total") or 0
    if not isinstance(b11_records, int) or b11_records <= 0:
        verdict = "insufficient_data_public_aggregate_only"
        verdict_reason = (
            "B11 aggregate reports no records; insufficient for a "
            "feasibility read. No empirical B16 downstream agent "
            "evaluation was performed."
        )
    else:
        verdict = "no_go_public_aggregate_only"
        verdict_reason = (
            "public B11 B12 B13 B14 B15 aggregates are retrieval context "
            "research only; they lack per-run paired agent outputs for "
            "real B16. No empirical B16 runs; no solve rate computed; "
            "B11 verdict "
            + repr(b11_verdict)
            + " NOT authorizing downstream value."
        )

    report["verdict"] = verdict
    report["verdict_reason"] = verdict_reason
    report["allowed_verdicts"] = list(ALLOWED_VERDICTS)

    # Missing inputs (the specific gaps that block real B16).
    report["missing_inputs_for_real_b16"] = [dict(g) for g in MISSING_INPUTS]

    # Recommended next step (cautious, no auto-promotion).
    recommended_next_step = {
        "primary": "future_ephemeral_record_b16_downstream_agent_evaluation",
        "secondary": "future_ephemeral_record_b15_pack_policy_validation_first",
        "reason": (
            "Run B16 against ephemeral per-run paired agent outputs "
            "(event logs, patches, test results, solve labels, first-"
            "file events, wrong-file annotations, tool-call token "
            "latency cost rows, isolated workspace proof, randomized "
            "arm order, task oracle manifest)"
        ),
        "next_step_authorizes_promotion": False,
        "next_step_authorizes_default_change": False,
        "next_step_authorizes_retrieval_variant_promotion": False,
        "next_step_authorizes_runtime_clean_algorithm": False,
        "next_step_authorizes_downstream_agent_runs": False,
        "next_step_authorizes_patch_execution": False,
        "next_step_authorizes_solve_rate_evaluation": False,
        "next_step_authorizes_empirical_downstream_agent_evaluation": False,
    }

    report.update(
        {
            "testability": {
                "full_b16_possible_from_public_artifacts": False,
                "missing_inputs_for_full_b16": [
                    g["gap_id"] for g in MISSING_INPUTS
                ],
                "note": (
                    "Real B16 cannot be replayed from the public B11 B12 "
                    "B13 B14 B15 aggregates. The listed missing inputs "
                    "are the per-run fields required. The public "
                    "aggregates are retrieval context research only; "
                    "they do NOT prove downstream agent value."
                ),
            },
            "recommended_next_step": recommended_next_step,
            "integrity": _compute_integrity(
                b11_aggregate,
                b12_screen,
                b13_feas,
                b14_feas,
                b15_prior,
            ),
            "safety_invariants": {
                "aggregate_only_public_artifact": True,
                "promotion_ready_false": True,
                "default_should_change_false": True,
                "evidencecore_semantics_changed_false": True,
                "retrieval_variant_promoted_false": True,
                "stage_is_downstream_agent_evaluation": True,
                "downstream_agent_runs_performed_false": True,
                "patch_execution_performed_false": True,
                "agent_behavior_metrics_evaluated_false": True,
                "solve_rate_evaluated_false": True,
                "per_record_inputs_available_false": True,
                "no_evidencecore_semantics_change": True,
                "no_live_llm_calls_by_screen": True,
                "no_live_downstream_agent_runs": True,
                "no_patch_execution": True,
                "no_agent_behavior_metrics_evaluation": True,
                "no_solve_rate_evaluation": True,
                "no_retrieval_variant_promotion": True,
                "no_threshold_tuning": True,
                "no_raw_records_read": True,
                "no_raw_paths_or_digests": True,
                "no_prompts_or_responses": True,
                "no_patches_or_diffs": True,
                "no_test_execution_results": True,
                "no_solve_labels": True,
                "no_agent_event_logs": True,
                "no_private_labels": True,
                "no_run_ids_emitted": True,
                "no_candidate_retrieval_variant_frozen": True,
                "no_stages_evaluated": True,
                "no_winner_declared": True,
                "no_retrieval_variant_promotion": True,
                "no_fake_downstream_metrics_from_retrieval_aggregates": True,
                "retrieval_improvements_do_not_imply_agent_improvements": True,
                "b15_pack_policy_does_not_imply_agent_improvements": True,
            },
            "framing": {
                "promotion_readiness_claimed": False,
                "default_readiness_claimed": False,
                "retrieval_variant_promotion_claimed": False,
                "runtime_clean_general_algorithm_claimed": False,
                "empirical_downstream_agent_evaluation_claimed": False,
                "downstream_agent_runs_claimed": False,
                "patch_execution_claimed": False,
                "agent_behavior_metrics_claimed": False,
                "solve_rate_claimed": False,
                "winner_declared_claimed": False,
                "candidate_retrieval_variant_frozen_claimed": False,
                "retrieval_improvements_imply_agent_improvements_claimed": False,
                "b15_pack_policy_implies_agent_improvements_claimed": False,
                "signal_strength": (
                    "bounded_public_aggregate_feasibility_screen_only"
                ),
                "is_full_b16_downstream_agent_evaluation": False,
                "recommended_next_step": (
                    "future_ephemeral_record_b16_downstream_agent_evaluation"
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


def _build_synthetic_b14_feas() -> dict[str, Any]:
    """Minimal synthetic B14 public aggregate feasibility report."""
    return {
        "schema_version": INPUT_B14_FEAS_SCHEMA,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        "full_b14_possible_from_public_artifacts": False,
        "uncertainty_calibration_performed": False,
        "calibrated_model_claim": False,
        "per_record_inputs_available": False,
        "uncertainty_score_found": False,
        "rotations_evaluated": False,
        "metrics_evaluated": False,
        "verdict": "no_go_public_aggregate_only",
        "missing_inputs_for_real_b14": [
            {"gap_id": "no_per_record_uncertainty_scores_in_public_artifact"},
        ],
        "recommended_next_step": {
            "primary": "future_ephemeral_record_b14_calibration",
        },
    }


def _build_synthetic_b15_prior() -> dict[str, Any]:
    """Minimal synthetic B15 public aggregate prior-screen report."""
    return {
        "schema_version": INPUT_B15_PRIOR_SCHEMA,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "new_provider_calls": 0,
        "full_b15_possible_from_public_artifacts": False,
        "pack_policy_learned": False,
        "atom_ablation_performed": False,
        "per_record_inputs_available": False,
        "candidate_policy_frozen": False,
        "stages_evaluated": False,
        "winner_declared": False,
        "b2_prior_usable": True,
        "b2_prior_claim_level": (
            "low_n_single_model_aggregate_directional_prior"
        ),
        "atom_level_inference_possible": False,
        "role_specific_policy_possible": False,
        "calibration_possible": False,
        "new_live_runs_required": True,
        "verdict": "prior_screen_only",
        "missing_inputs_for_real_b15": [
            {"gap_id": "no_per_record_pack_atom_flags_in_public_artifact"},
        ],
    }


def _self_test_happy_path() -> dict[str, Any]:
    b11 = _build_synthetic_b11_aggregate()
    b12 = _build_synthetic_b12_screen()
    b13 = _build_synthetic_b13_feas()
    b14 = _build_synthetic_b14_feas()
    b15 = _build_synthetic_b15_prior()
    report = screen(b11, b12, b13, b14, b15, self_test=True)
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
        ("stage_is_downstream_agent_evaluation", True),
        ("downstream_agent_runs_performed", False),
        ("patch_execution_performed", False),
        ("agent_behavior_metrics_evaluated", False),
        ("solve_rate_evaluated", False),
        ("per_record_inputs_available", False),
        ("retrieval_variant_promoted", False),
        ("quality_strategy_tuned", False),
        ("new_provider_calls", 0),
        ("full_b16_possible_from_public_artifacts", False),
        ("winner_declared", False),
        ("promotion_declared", False),
        ("default_recommendation_declared", False),
        ("retrieval_variant_promotion_declared", False),
        ("metrics_defined", True),
        ("gates_defined", True),
        ("metrics_evaluated", False),
        ("no_fake_downstream_metrics_from_retrieval_aggregates", True),
    ):
        assert report[k] == v, (k, report[k])
    # No-go verdict emitted.
    assert report["verdict"] == "no_go_public_aggregate_only", report["verdict"]
    assert report["verdict"] in ALLOWED_VERDICTS, report["verdict"]
    assert (
        "no empirical b16" in report["verdict_reason"].lower()
    ), report["verdict_reason"]
    # B11 partial_with_failure + B12 screen + B13/B14 no-go + B15
    # prior-screen-only carried forward.
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
    assert report["input_b14_summary"]["b14_feasibility_verdict"] == (
        "no_go_public_aggregate_only"
    ), report["input_b14_summary"]
    assert report["input_b15_summary"]["b15_prior_verdict"] == (
        "prior_screen_only"
    ), report["input_b15_summary"]
    assert (
        report["input_b15_summary"]["b15_pack_policy_learned"] is False
    )
    assert (
        report["input_b15_summary"]["b15_atom_ablation_performed"] is False
    )
    # All missing inputs enumerated.
    missing_ids = [g["gap_id"] for g in report["missing_inputs_for_real_b16"]]
    expected_missing = tuple(g["gap_id"] for g in MISSING_INPUTS)
    assert missing_ids == list(expected_missing), missing_ids
    # Required missing inputs are present (the task spec).
    required_gap_ids = {
        "no_live_paired_agent_runs_in_public_artifact",
        "no_agent_event_logs_in_public_artifact",
        "no_patches_or_diffs_in_public_artifact",
        "no_test_execution_results_in_public_artifact",
        "no_solve_labels_in_public_artifact",
        "no_first_file_before_first_edit_event_in_public_artifact",
        "no_wrong_file_edit_annotations_in_public_artifact",
        "no_tool_calls_tokens_latency_cost_per_run_in_public_artifact",
        "no_randomized_arm_order_in_public_artifact",
        "no_isolated_workspace_proof_in_public_artifact",
        "no_task_oracle_or_hidden_test_manifest_in_public_artifact",
        "no_operational_parity_proof_in_public_artifact",
    }
    assert required_gap_ids.issubset(set(missing_ids)), (
        required_gap_ids - set(missing_ids)
    )
    # CRITICAL: no fake metric values. metrics_evaluated=false.
    assert report["metrics_evaluated"] is False
    assert report["no_fake_downstream_metrics_from_retrieval_aggregates"] is True
    # No solve_rate / correct_file / wrong_file / tool_call / token /
    # latency / cost value fields.
    for forbidden_field in (
        "solve_rate_value",
        "correct_file_before_first_edit_value",
        "wrong_file_edits_value",
        "tool_calls_before_first_edit_value",
        "context_tokens_value",
        "tests_pass_value",
        "latency_value",
        "cost_value",
    ):
        assert forbidden_field not in report, forbidden_field
    # Forbidden-key/value scan clean.
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    # No raw data carried.
    assert report["raw_paths_in_artifact"] is False
    assert report["raw_patches_diffs_stored"] is False
    assert report["raw_test_results_stored"] is False
    assert report["raw_solve_labels_stored"] is False
    assert report["raw_agent_event_logs_stored"] is False
    assert report["private_labels_committed"] is False
    assert report["run_ids_in_artifact"] is False
    # Integrity: all inputs clean (synthetic fixtures carry every
    # required boolean).
    integ = report["integrity"]
    assert integ["all_inputs_aggregate_only_public_artifact"] is True, integ
    assert integ["all_inputs_promotion_ready_false"] is True, integ
    assert integ["all_inputs_policy_search_performed_false"] is True, integ
    assert integ["all_inputs_candidate_not_fact"] is True, integ
    assert integ["all_inputs_default_should_change_false"] is True, integ
    assert integ["all_inputs_evidencecore_semantics_changed_false"] is True, integ
    assert integ["all_inputs_quality_strategy_tuned_false"] is True, integ
    assert integ["all_inputs_new_provider_calls_zero"] is True, integ
    assert integ["b11_aggregate_verdict_is_partial_with_failure"] is True, integ
    assert integ["b13_input_verdict_is_no_go_or_insufficient"] is True, integ
    assert integ["b14_input_verdict_is_no_go_or_insufficient"] is True, integ
    assert (
        integ["b15_input_verdict_is_no_go_or_prior_screen_only"] is True
    ), integ
    assert integ["b15_input_pack_policy_learned_false"] is True, integ
    assert integ["b15_input_atom_ablation_performed_false"] is True, integ
    print("self-test happy path: ok")
    return report


def _self_test_integrity_fail_closed_on_bad_b11_verdict() -> None:
    """When the B11 aggregate verdict drifts away from the preregistered
    B11 outcome, the B16 carry-forward integrity field flips to false
    (fail-closed)."""
    b11 = _build_synthetic_b11_aggregate()
    b12 = _build_synthetic_b12_screen()
    b13 = _build_synthetic_b13_feas()
    b14 = _build_synthetic_b14_feas()
    b15 = _build_synthetic_b15_prior()
    b11_bad = _build_synthetic_b11_aggregate()
    b11_bad["aggregate_verdict"] = "success"
    report = screen(b11_bad, b12, b13, b14, b15, self_test=True)
    integ = report["integrity"]
    assert integ["b11_aggregate_verdict_is_partial_with_failure"] is False, integ
    print("self-test integrity fail-closed on bad B11 verdict: ok")


def _self_test_insufficient_data_branch() -> None:
    """When B11 record_count_total <= 0, the screen emits
    insufficient_data_public_aggregate_only."""
    b11 = _build_synthetic_b11_aggregate()
    b11["record_count_total"] = 0
    b12 = _build_synthetic_b12_screen()
    b13 = _build_synthetic_b13_feas()
    b14 = _build_synthetic_b14_feas()
    b15 = _build_synthetic_b15_prior()
    report = screen(b11, b12, b13, b14, b15, self_test=True)
    assert report["verdict"] == (
        "insufficient_data_public_aggregate_only"
    ), report["verdict"]
    assert "no empirical b16" in report[
        "verdict_reason"
    ].lower(), report["verdict_reason"]
    # Still no downstream agent runs / patch / solve.
    assert report["downstream_agent_runs_performed"] is False
    assert report["patch_execution_performed"] is False
    assert report["agent_behavior_metrics_evaluated"] is False
    assert report["solve_rate_evaluated"] is False
    assert report["per_record_inputs_available"] is False
    assert report["metrics_evaluated"] is False
    print("self-test insufficient_data branch: ok")


def _self_test_input_validation_blocks() -> None:
    """Input validation blocks for each upstream artifact."""
    b12 = _build_synthetic_b12_screen()
    b13 = _build_synthetic_b13_feas()
    b14 = _build_synthetic_b14_feas()
    b15 = _build_synthetic_b15_prior()

    # Wrong B11 schema_version.
    bad = _build_synthetic_b11_aggregate()
    bad["schema_version"] = "wrong"
    try:
        screen(bad, b12, b13, b14, b15, self_test=True)
    except ValueError as exc:
        assert "unexpected B11 schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should reject wrong B11 schema_version")

    # B11 promotion_ready=true rejected.
    bad = _build_synthetic_b11_aggregate()
    bad["promotion_ready"] = True
    try:
        screen(bad, b12, b13, b14, b15, self_test=True)
    except ValueError as exc:
        assert "promotion_ready=false" in str(exc), exc
    else:
        raise AssertionError("screen should reject B11 promotion_ready=true")

    # Wrong B12 screen schema_version.
    bad12 = _build_synthetic_b12_screen()
    bad12["schema_version"] = "wrong"
    b11 = _build_synthetic_b11_aggregate()
    try:
        screen(b11, bad12, b13, b14, b15, self_test=True)
    except ValueError as exc:
        assert "unexpected B12 screen schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should reject wrong B12 schema_version")

    # B12 full_b12_replay_possible=true rejected.
    bad12 = _build_synthetic_b12_screen()
    bad12["full_b12_replay_possible_from_public_artifact"] = True
    try:
        screen(b11, bad12, b13, b14, b15, self_test=True)
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
        screen(b11, b12, bad13, b14, b15, self_test=True)
    except ValueError as exc:
        assert "unexpected B13 feas schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should reject wrong B13 schema_version")

    # B13 full_b13_possible=true rejected.
    bad13 = _build_synthetic_b13_feas()
    bad13["full_b13_possible_from_public_artifacts"] = True
    try:
        screen(b11, b12, bad13, b14, b15, self_test=True)
    except ValueError as exc:
        assert "full_b13_possible_from_public_artifacts=false" in str(
            exc
        ), exc
    else:
        raise AssertionError(
            "screen should reject B13 full_b13_possible=true"
        )

    # B13 verdict=success rejected.
    bad13 = _build_synthetic_b13_feas()
    bad13["verdict"] = "success"
    try:
        screen(b11, b12, bad13, b14, b15, self_test=True)
    except ValueError as exc:
        assert "no_go / insufficient_data verdict" in str(exc), exc
    else:
        raise AssertionError("screen should reject B13 verdict=success")

    # Wrong B14 feas schema_version.
    bad14 = _build_synthetic_b14_feas()
    bad14["schema_version"] = "wrong"
    try:
        screen(b11, b12, b13, bad14, b15, self_test=True)
    except ValueError as exc:
        assert "unexpected B14 feas schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should reject wrong B14 schema_version")

    # B14 full_b14_possible=true rejected.
    bad14 = _build_synthetic_b14_feas()
    bad14["full_b14_possible_from_public_artifacts"] = True
    try:
        screen(b11, b12, b13, bad14, b15, self_test=True)
    except ValueError as exc:
        assert "full_b14_possible_from_public_artifacts=false" in str(
            exc
        ), exc
    else:
        raise AssertionError(
            "screen should reject B14 full_b14_possible=true"
        )

    # Wrong B15 prior schema_version.
    bad15 = _build_synthetic_b15_prior()
    bad15["schema_version"] = "wrong"
    try:
        screen(b11, b12, b13, b14, bad15, self_test=True)
    except ValueError as exc:
        assert "unexpected B15 prior schema_version" in str(exc), exc
    else:
        raise AssertionError("screen should reject wrong B15 schema_version")

    # B15 full_b15_possible=true rejected.
    bad15 = _build_synthetic_b15_prior()
    bad15["full_b15_possible_from_public_artifacts"] = True
    try:
        screen(b11, b12, b13, b14, bad15, self_test=True)
    except ValueError as exc:
        assert "full_b15_possible_from_public_artifacts=false" in str(
            exc
        ), exc
    else:
        raise AssertionError(
            "screen should reject B15 full_b15_possible=true"
        )

    # B15 verdict=success rejected.
    bad15 = _build_synthetic_b15_prior()
    bad15["verdict"] = "success"
    try:
        screen(b11, b12, b13, b14, bad15, self_test=True)
    except ValueError as exc:
        assert "no_go or prior_screen_only verdict" in str(exc), exc
    else:
        raise AssertionError("screen should reject B15 verdict=success")

    # NOTE: pack_policy_learned is NOT directly validated by the
    # validator (the validator checks the B15 verdict and
    # full_b15_possible). The carry-forward surfaces pack_policy_learned
    # as-is. The integrity computation fails closed when the carried-
    # forward summary reports pack_policy_learned != False. Confirm the
    # fail-closed path: feed a B15 with pack_policy_learned=True
    # through validation (verdict still prior_screen_only,
    # full_b15_possible still False). The screen MUST still emit a
    # clean report but the integrity will fail-closed on
    # b15_input_pack_policy_learned_false.
    bad15 = _build_synthetic_b15_prior()
    bad15["pack_policy_learned"] = True
    report = screen(b11, b12, b13, b14, bad15, self_test=True)
    # The screen surface carry-forward should reflect the bad input.
    assert (
        report["input_b15_summary"]["b15_pack_policy_learned"] is True
    )
    # Integrity fail-closed.
    assert (
        report["integrity"]["b15_input_pack_policy_learned_false"] is False
    ), report["integrity"]

    print("self-test input validation blocks: ok")


def _self_test_forbidden_scan() -> None:
    """Forbidden-key scan catches injected raw paths / labels /
    downstream-agent artifacts."""
    bad_report = {
        "task_id": "leak",
        "path": "src/foo.rs",
        "snippet": "fn main(){}",
        "patch": "patch content",
        "solve_label": "True",
        "gold_spans": [[1, 2]],
        "private_labels": "x",
    }
    hits = b6lite._walk_forbidden(bad_report)
    flat = " ".join(hits)
    # b6lite FORBIDDEN_PUBLIC_KEYS catches these key names.
    assert "task_id" in flat
    assert "path" in flat
    assert "snippet" in flat
    assert "gold_spans" in flat
    assert "private_labels" in flat
    print("self-test forbidden scan: ok")


def run_self_tests() -> dict[str, Any]:
    _self_test_happy_path()
    _self_test_integrity_fail_closed_on_bad_b11_verdict()
    _self_test_insufficient_data_branch()
    _self_test_input_validation_blocks()
    _self_test_forbidden_scan()
    return {
        "schema_version": SCHEMA_VERSION,
        "claim_level": CLAIM_LEVEL,
        "self_test_passed": True,
        "self_test_checks": {
            "happy_path": True,
            "integrity_fail_closed_on_bad_b11_verdict": True,
            "insufficient_data_branch": True,
            "input_validation_blocks": True,
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
        "--input-b14",
        type=Path,
        default=DEFAULT_INPUT_B14,
        help=(
            "path to the B14 public aggregate feasibility report JSON "
            "(default: artifacts/b14_uncertainty_calibration/"
            "b14_public_aggregate_feasibility_report.json)"
        ),
    )
    parser.add_argument(
        "--input-b15",
        type=Path,
        default=DEFAULT_INPUT_B15,
        help=(
            "path to the B15 public aggregate prior-screen report JSON "
            "(default: artifacts/b15_context_pack_policy/"
            "b15_public_aggregate_prior_screen_report.json)"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=(
            "path to write the B16 public aggregate feasibility report "
            "(default: artifacts/b16_downstream_agent_evaluation/"
            "b16_public_aggregate_feasibility_report.json)"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the B16 public aggregate feasibility screen self-test "
        "(synthetic fixture)",
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if args.self_test and (
        str(args.input_b11) != str(DEFAULT_INPUT_B11)
        or str(args.input_b12) != str(DEFAULT_INPUT_B12)
        or str(args.input_b13) != str(DEFAULT_INPUT_B13)
        or str(args.input_b14) != str(DEFAULT_INPUT_B14)
        or str(args.input_b15) != str(DEFAULT_INPUT_B15)
    ):
        parser.error(
            "--self-test ignores --input-b11/--input-b12/--input-b13/"
            "--input-b14/--input-b15; do not pass both"
        )
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_tests()
        print(json.dumps(result, indent=2, sort_keys=True))
        print(
            "B16 public aggregate feasibility screen self-test: PASS",
            file=sys.stderr,
        )
        return 0
    for label, path in (
        ("B11", args.input_b11),
        ("B12", args.input_b12),
        ("B13", args.input_b13),
        ("B14", args.input_b14),
        ("B15", args.input_b15),
    ):
        if not path.exists():
            print(
                f"B16 feasibility screen {label} input not found: {path}",
                file=sys.stderr,
            )
            return 2
    b11_aggregate = json.loads(args.input_b11.read_text(encoding="utf-8"))
    b12_screen = json.loads(args.input_b12.read_text(encoding="utf-8"))
    b13_feas = json.loads(args.input_b13.read_text(encoding="utf-8"))
    b14_feas = json.loads(args.input_b14.read_text(encoding="utf-8"))
    b15_prior = json.loads(args.input_b15.read_text(encoding="utf-8"))
    report = screen(
        b11_aggregate=b11_aggregate,
        b12_screen=b12_screen,
        b13_feas=b13_feas,
        b14_feas=b14_feas,
        b15_prior=b15_prior,
        self_test=False,
    )
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
        "stage_is_downstream_agent_evaluation": report[
            "stage_is_downstream_agent_evaluation"
        ],
        "downstream_agent_runs_performed": report[
            "downstream_agent_runs_performed"
        ],
        "patch_execution_performed": report["patch_execution_performed"],
        "agent_behavior_metrics_evaluated": report[
            "agent_behavior_metrics_evaluated"
        ],
        "solve_rate_evaluated": report["solve_rate_evaluated"],
        "per_record_inputs_available": report["per_record_inputs_available"],
        "retrieval_variant_promoted": report["retrieval_variant_promoted"],
        "metrics_evaluated": report["metrics_evaluated"],
        "no_fake_downstream_metrics_from_retrieval_aggregates": report[
            "no_fake_downstream_metrics_from_retrieval_aggregates"
        ],
        "full_b16_possible_from_public_artifacts": report[
            "full_b16_possible_from_public_artifacts"
        ],
        "new_provider_calls": report["new_provider_calls"],
        "b11_aggregate_verdict": report["input_b11_summary"][
            "b11_aggregate_verdict"
        ],
        "b13_feasibility_verdict": report["input_b13_summary"][
            "b13_feasibility_verdict"
        ],
        "b14_feasibility_verdict": report["input_b14_summary"][
            "b14_feasibility_verdict"
        ],
        "b15_prior_verdict": report["input_b15_summary"]["b15_prior_verdict"],
        "b15_pack_policy_learned": report["input_b15_summary"][
            "b15_pack_policy_learned"
        ],
        "missing_inputs_for_real_b16": [
            g["gap_id"] for g in report["missing_inputs_for_real_b16"]
        ],
        "out": str(args.out),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
