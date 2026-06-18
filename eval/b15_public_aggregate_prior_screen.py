#!/usr/bin/env python3
"""B15 Public-Aggregate Prior / No-Go Screen (bounded).

This is a **bounded public-aggregate prior / no-go screen**, NOT a real
B15 PackPolicy validation. Real B15 (the frozen preregistration in
``eval/b15_context_pack_policy.py`` and
``docs/en/b15-context-pack-policy.md``) requires private / ephemeral
per-record pack atom flags, per-record binary outcomes, role-specific
paired outputs, runtime_state per record, model_profile paired blocks,
group membership for worst-group splits, randomized atom assignment +
balance stats, denominator-by-atom/role/model cells, and token-budget-
matched controls. None of those are present in any current public
artifact, so real B15 PackPolicy validation cannot be performed from
public aggregates alone.

What this screen DOES: read already-published public aggregates and
emit a **public-aggregate prior / no-go report** for B15:

* the published B2 contrastive-pack experiment doc (existence only;
  the screen does NOT parse B2's private per-task detail and uses B2
  ONLY as a ``low_n_single_model_aggregate_directional_prior``),
* the already-published B14 public-aggregate feasibility report
  (``artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json``),
* optionally, when present, the already-published B4-B9 / P21-G / P49
  public aggregate reports (guarded as ``unavailable`` when missing).

The screen preserves the public-artifact contract:

* **no** raw records, task IDs, repo IDs, candidate IDs, paths, spans,
  snippets, prompts, responses, gold spans, private labels, provider
  keys, base URLs, API keys, or digests are read or emitted;
* **no** provider calls (``new_provider_calls == 0``);
* **no** empirical PackPolicy learning, atom ablation, atom-effect
  estimation, role-pack-outcome computation, worst-group computation,
  token-budget parity computation, or winner declaration;
* **no** promotion / default / PackPolicy promotion / runtime-clean
  general algorithm claim / EvidenceCore change;
* ``pack_policy_learned=false``,
  ``atom_ablation_performed=false``,
  ``per_record_inputs_available=false``,
  ``metrics_evaluated=false``,
  ``candidate_policy_frozen=false``,
  ``atom_level_inference_possible=false``,
  ``role_specific_policy_possible=false``,
  ``calibration_possible=false``,
  ``new_live_runs_required=true``,
  ``b2_prior_usable=true``,
  ``b2_prior_claim_level=low_n_single_model_aggregate_directional_prior``.

CRITICAL: the screen MUST NOT compute fake atom-effect / role-pack-
outcome / worst-group-pack-outcome metrics from aggregate means.
Aggregate means (e.g. the B2 pack-layout aggregate SpanF0.5 / PFP) do
not contain per-record (atom_flag, outcome) pairs, so any atom-level
causal effect computed from them would be a fabrication. The screen
enumerates the specific missing per-record inputs that block real B15
and carries forward the B14 no-go status (and, when present, the B4-B9
/ P21-G / P49 public aggregate statuses) so a reader cannot mistake a
B15 no-go for B14 success or an authorized PackPolicy.

Run::

    python3 eval/b15_public_aggregate_prior_screen.py --self-test
    python3 eval/b15_public_aggregate_prior_screen.py \
        --out artifacts/b15_context_pack_policy/b15_public_aggregate_prior_screen_report.json
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

SCHEMA_VERSION = "b15-public-aggregate-prior-screen-v0"
GENERATED_BY = "b15_public_aggregate_prior_screen"
CLAIM_LEVEL = "bounded_public_aggregate_prior_screen_of_b2_b14_and_optional_aggregates"

# Input schemas (validated when present).
INPUT_B14_FEAS_SCHEMA = "b14-public-aggregate-feasibility-screen-v0"
INPUT_B4_B9_SCHEMA = "b4-b9-model-robust-evidence-conversion-v0"
INPUT_P21_G_EMBED_SCHEMA = "p21-g1e-embedding-context-v1"
INPUT_P49_SCAFFOLD_SCHEMA = "p49-contrastive-candidate-pack-scaffold-v1"

POLICY_UNDER_ANALYSIS = "balanced_v1"
BASELINE_FOR_DELTAS = "p25"

# B2 is the only directional prior available; it is single-model,
# low-N, aggregate-only, so it carries forward ONLY as a weak
# directional prior.
B2_PRIOR_CLAIM_LEVEL = "low_n_single_model_aggregate_directional_prior"

DEFAULT_B2_DOC = Path("docs/en/b2-contrastive-pack-quality-experiment.md")
DEFAULT_INPUT_B14 = Path(
    "artifacts/b14_uncertainty_calibration/"
    "b14_public_aggregate_feasibility_report.json"
)
DEFAULT_INPUT_B4_B9 = Path(
    "artifacts/b4_b9_model_robust_evidence_conversion/"
    "b4_b9_model_robust_evidence_conversion_report.json"
)
DEFAULT_INPUT_P21_G_EMBED = Path(
    "artifacts/p21_g/embedding_context_report.json"
)
DEFAULT_INPUT_P49 = Path(
    "artifacts/p49_contrastive_candidate_pack_scaffold/"
    "p49_contrastive_candidate_pack_scaffold_report.json"
)
DEFAULT_OUT = Path(
    "artifacts/b15_context_pack_policy/"
    "b15_public_aggregate_prior_screen_report.json"
)

# Verdicts emitted by this screen. The screen NEVER emits success /
# failure / partial as a PackPolicy verdict; it emits only prior / no-go
# statuses that make clear no empirical B15 PackPolicy validation
# happened. ``prior_screen_only`` is emitted when at least the B2
# directional prior is available; ``no_go_public_aggregate_only`` is
# emitted when the B2 prior is also missing.
ALLOWED_VERDICTS = (
    "no_go_public_aggregate_only",
    "prior_screen_only",
)

# Missing inputs that block real B15 from the public aggregates. Each
# entry is a self-contained reason so a reader cannot mistake the
# screen for a B15 PackPolicy result. Descriptions are kept under 256
# chars to satisfy the public forbidden-value scan (long_string guard).
MISSING_INPUTS = (
    {
        "gap_id": "no_per_record_pack_atom_flags_in_public_artifact",
        "description": (
            "real B15 needs per-record pack atom flags (which atoms were "
            "present in the pack sent to the model) for every record; "
            "the public B2 + B14 + B4-B9 + P21-G + P49 aggregates "
            "publish only aggregate counters, not per-record atom flags"
        ),
    },
    {
        "gap_id": "no_per_record_outcomes_in_public_artifact",
        "description": (
            "real B15 needs a per-record binary outcome (was the "
            "selected span / candidate correct) as the validation "
            "target; the public aggregates publish only aggregate gold "
            "span counts, not per-record binary outcomes"
        ),
    },
    {
        "gap_id": "no_role_specific_paired_outputs_in_public_artifact",
        "description": (
            "real B15 PackPolicy is role-indexed (span_narrow, "
            "filter_reject, request_more_context, "
            "source_test_disambiguation); the public aggregates do not "
            "publish role-specific paired outputs for the same record"
        ),
    },
    {
        "gap_id": "no_model_profile_paired_blocks_in_public_artifact",
        "description": (
            "real B15 model_profile abstraction requires paired blocks "
            "of the same record answered under different abstract "
            "capability profiles; the public aggregates publish only "
            "per-family rollups, not paired capability-profile blocks"
        ),
    },
    {
        "gap_id": "no_randomized_atom_assignment_in_public_artifact",
        "description": (
            "real B15 atom-effect estimation requires randomized atom "
            "on or off assignment per record; the public aggregates "
            "have no randomized atom assignment, so no causal atom "
            "effect can be estimated"
        ),
    },
    {
        "gap_id": "no_randomization_balance_stats_in_public_artifact",
        "description": (
            "real B15 randomization-balance gate requires per-arm "
            "covariate balance stats; the public aggregates publish no "
            "randomization balance stats"
        ),
    },
    {
        "gap_id": "no_denominator_by_atom_role_model_in_public_artifact",
        "description": (
            "real B15 denominator gate requires denominator counts per "
            "(atom, role, model_profile) cell; the public aggregates "
            "publish no such denominators, so no small-denominator "
            "guard is possible"
        ),
    },
    {
        "gap_id": "no_token_budget_matched_controls_in_public_artifact",
        "description": (
            "real B15 token-budget gate requires token-budget-matched "
            "control packs; the public aggregates publish no matched "
            "controls, so atom effects cannot be deconfounded from "
            "pack size"
        ),
    },
    {
        "gap_id": "no_fresh_validation_split_in_public_artifact",
        "description": (
            "real B15 must split per-record inputs into an atom-screen "
            "split and a fresh-validation split stratified by "
            "(model_family, repo, role); the public aggregates do not "
            "expose per-record membership, so no validation split can "
            "be constructed"
        ),
    },
    {
        "gap_id": "no_runtime_state_per_record_in_public_artifact",
        "description": (
            "real B15 PackPolicy is indexed by runtime_state per record "
            "(candidate pool shape, score distribution, schema-repair "
            "state); the public aggregates publish no per-record "
            "runtime_state, so no per-record PackPolicy row can be "
            "formed"
        ),
    },
    {
        "gap_id": "no_group_membership_for_worst_group_split_in_public_artifact",
        "description": (
            "real B15 worst-group reporting requires group membership "
            "for worst-group split (model_family x repo x role); the "
            "public aggregates publish no per-record group membership, "
            "so no worst-group split can be constructed"
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


def _base_report(self_test: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": _now(),
        "claim_level": CLAIM_LEVEL,
        "self_test": bool(self_test),
        "input_b14_feas_schema": INPUT_B14_FEAS_SCHEMA,
        "input_b4_b9_schema": INPUT_B4_B9_SCHEMA,
        "input_p21_g_embed_schema": INPUT_P21_G_EMBED_SCHEMA,
        "input_p49_scaffold_schema": INPUT_P49_SCAFFOLD_SCHEMA,
        "policy_under_analysis": POLICY_UNDER_ANALYSIS,
        "baseline_for_deltas": BASELINE_FOR_DELTAS,
        # Safety fields preserved verbatim. The screen makes NO
        # empirical PackPolicy learning claim; pack_policy_learned=false
        # and atom_ablation_performed=false are the disambiguating
        # fields (the B15 stage IS context pack policy, but no empirical
        # PackPolicy validation was performed by this screen).
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "pack_policy_learned": False,
        "atom_ablation_performed": False,
        "per_record_inputs_available": False,
        "policy_search_performed": False,
        "stage_is_context_pack_policy": True,  # B15 stage IS pack policy
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
        "pack_policy_promotion_declared": False,
        "winner_declared": False,
        # Bounded-screen stance.
        "is_full_b15_pack_policy_validation": False,
        "full_b15_possible_from_public_artifacts": False,
        "candidate_policy_frozen": False,
        "stages_evaluated": False,
        "metrics_defined": True,
        "gates_defined": True,
        "metrics_evaluated": False,
        "no_fake_atom_effects_from_aggregate_means": True,
        # B2 prior boundary (the only directional prior available).
        "b2_prior_usable": True,
        "b2_prior_claim_level": B2_PRIOR_CLAIM_LEVEL,
        # B15 inferences that CANNOT be made from public aggregates.
        "atom_level_inference_possible": False,
        "role_specific_policy_possible": False,
        "calibration_possible": False,
        "new_live_runs_required": True,
    }


def _finalize_safety(report: dict[str, Any]) -> None:
    """Run the forbidden-key/value scan on the public output."""
    violations = b6lite._walk_forbidden(report)
    integrity = report.setdefault("integrity", {})
    integrity["forbidden_public_key_scan_clean"] = not violations
    if violations:
        raise ValueError(
            "b15-public-aggregate-prior-screen public output would "
            f"contain forbidden keys/values; first violations: "
            f"{violations[:5]}"
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


def _validate_b4_b9(report: dict[str, Any]) -> None:
    """Validate the B4-B9 public aggregate input (when present)."""
    if report.get("schema_version") != INPUT_B4_B9_SCHEMA:
        raise ValueError(
            f"unexpected B4-B9 schema_version: "
            f"{report.get('schema_version')!r}"
        )
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError(
            "B4-B9 input must be aggregate_only_public_artifact=true"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError("B4-B9 input must have promotion_ready=false")
    if report.get("default_should_change") is not False:
        raise ValueError("B4-B9 input must have default_should_change=false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "B4-B9 input must have evidencecore_semantics_changed=false"
        )


def _validate_p21_g_embed(report: dict[str, Any]) -> None:
    """Validate the P21-G embedding context input (when present)."""
    if report.get("schema_version") != INPUT_P21_G_EMBED_SCHEMA:
        raise ValueError(
            f"unexpected P21-G embed schema_version: "
            f"{report.get('schema_version')!r}"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError("P21-G embed input must have promotion_ready=false")
    if report.get("default_should_change") is not False:
        raise ValueError(
            "P21-G embed input must have default_should_change=false"
        )
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "P21-G embed input must have evidencecore_semantics_changed=false"
        )


def _validate_p49(report: dict[str, Any]) -> None:
    """Validate the P49 contrastive pack scaffold input (when present)."""
    if report.get("schema_version") != INPUT_P49_SCAFFOLD_SCHEMA:
        raise ValueError(
            f"unexpected P49 scaffold schema_version: "
            f"{report.get('schema_version')!r}"
        )
    if report.get("aggregate_only_public_artifact") is not True:
        raise ValueError(
            "P49 scaffold input must be aggregate_only_public_artifact=true"
        )
    if report.get("promotion_ready") is not False:
        raise ValueError("P49 scaffold input must have promotion_ready=false")
    if report.get("default_should_change") is not False:
        raise ValueError("P49 scaffold input must have default_should_change=false")
    if report.get("evidencecore_semantics_changed") is not False:
        raise ValueError(
            "P49 scaffold input must have evidencecore_semantics_changed=false"
        )


def _carry_forward_b14(b14_feas: dict[str, Any]) -> dict[str, Any]:
    """Carry forward B14 no-go status (public fields only)."""
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


def _carry_forward_optional(
    name: str, report: dict[str, Any] | None
) -> dict[str, Any]:
    """Carry forward an optional public aggregate's status (or mark
    unavailable)."""
    if report is None:
        return {"available": False, "reason": "public_artifact_not_present"}
    return {
        "available": True,
        "schema_version": report.get("schema_version"),
        "promotion_ready": report.get("promotion_ready"),
        "default_should_change": report.get("default_should_change"),
        "evidencecore_semantics_changed": report.get(
            "evidencecore_semantics_changed"
        ),
        "aggregate_only_public_artifact": report.get(
            "aggregate_only_public_artifact"
        ),
        "policy_search_performed": report.get("policy_search_performed"),
        "candidate_not_fact": report.get("candidate_not_fact"),
        "quality_strategy_tuned": report.get("quality_strategy_tuned"),
        "new_provider_calls": report.get("new_provider_calls"),
    }


def _compute_integrity(
    b14_feas: dict[str, Any],
    b4_b9_summary: dict[str, Any],
    p21_g_embed_summary: dict[str, Any],
    p49_summary: dict[str, Any],
) -> dict[str, Any]:
    """Compute the integrity block from actual validated booleans.

    Fail-closed: every ``all_inputs_*`` field is ``true`` ONLY when
    every available input carries the corresponding boolean ``true``.
    If any available input lacks the field (e.g. P21-G does not set
    ``aggregate_only_public_artifact``), the field is set to ``false``
    with a reason, so the screen never overclaims that all inputs are
    aggregate-only. Missing optional inputs (``available=False``) do
    not lower a field.
    """
    # Collect available inputs and their raw booleans.
    b14_agg = b14_feas.get("aggregate_only_public_artifact")
    b14_promo = b14_feas.get("promotion_ready")
    b14_polsearch = b14_feas.get("policy_search_performed")
    b14_cand = b14_feas.get("candidate_not_fact")
    b14_dsc = b14_feas.get("default_should_change")
    b14_esc = b14_feas.get("evidencecore_semantics_changed")
    b14_qst = b14_feas.get("quality_strategy_tuned")
    b14_npc = b14_feas.get("new_provider_calls")

    optional_summaries = (
        ("b4_b9", b4_b9_summary),
        ("p21_g_embed", p21_g_embed_summary),
        ("p49", p49_summary),
    )

    def _all(field_name: str, b14_val: Any, expected: Any) -> tuple[bool, list[str]]:
        """Return (all_match, reasons). Fail-closed: any available
        optional input whose field is not the expected value causes
        false. None / missing values count as not-matching for true
        expectations."""
        reasons: list[str] = []
        if b14_val != expected:
            reasons.append(f"b14 has {field_name}={b14_val!r} (expected {expected!r})")
        for name, summary in optional_summaries:
            if not summary.get("available"):
                continue
            val = summary.get(field_name)
            if val != expected:
                reasons.append(
                    f"{name} has {field_name}={val!r} (expected {expected!r})"
                )
        return (len(reasons) == 0), reasons

    agg_ok, agg_reasons = _all(
        "aggregate_only_public_artifact", b14_agg, True
    )
    promo_ok, promo_reasons = _all("promotion_ready", b14_promo, False)
    polsearch_ok, polsearch_reasons = _all(
        "policy_search_performed", b14_polsearch, False
    )
    cand_ok, cand_reasons = _all("candidate_not_fact", b14_cand, True)
    dsc_ok, dsc_reasons = _all("default_should_change", b14_dsc, False)
    esc_ok, esc_reasons = _all(
        "evidencecore_semantics_changed", b14_esc, False
    )
    qst_ok, qst_reasons = _all("quality_strategy_tuned", b14_qst, False)
    npc_ok, npc_reasons = _all("new_provider_calls", b14_npc, 0)

    integrity: dict[str, Any] = {
        "all_inputs_aggregate_only_public_artifact": agg_ok,
        "all_inputs_promotion_ready_false": promo_ok,
        "all_inputs_policy_search_performed_false": polsearch_ok,
        "all_inputs_candidate_not_fact": cand_ok,
        "all_inputs_default_should_change_false": dsc_ok,
        "all_inputs_evidencecore_semantics_changed_false": esc_ok,
        "all_inputs_quality_strategy_tuned_false": qst_ok,
        "all_inputs_new_provider_calls_zero": npc_ok,
        "b14_input_full_b14_possible_false": (
            b14_feas.get("full_b14_possible_from_public_artifacts") is False
        ),
        "b14_input_verdict_is_no_go_or_insufficient": (
            b14_feas.get("verdict")
            in ("no_go_public_aggregate_only", "insufficient_data_public_aggregate_only")
        ),
        "optional_inputs_guarded_when_missing": True,
        "forbidden_public_key_scan_clean": True,
    }
    if not agg_ok:
        integrity["all_inputs_aggregate_only_public_artifact_reasons"] = agg_reasons
    if not promo_ok:
        integrity["all_inputs_promotion_ready_false_reasons"] = promo_reasons
    if not polsearch_ok:
        integrity["all_inputs_policy_search_performed_false_reasons"] = polsearch_reasons
    if not cand_ok:
        integrity["all_inputs_candidate_not_fact_reasons"] = cand_reasons
    if not dsc_ok:
        integrity["all_inputs_default_should_change_false_reasons"] = dsc_reasons
    if not esc_ok:
        integrity["all_inputs_evidencecore_semantics_changed_false_reasons"] = esc_reasons
    if not qst_ok:
        integrity["all_inputs_quality_strategy_tuned_false_reasons"] = qst_reasons
    if not npc_ok:
        integrity["all_inputs_new_provider_calls_zero_reasons"] = npc_reasons
    return integrity


def screen(
    b2_doc_present: bool,
    b14_feas: dict[str, Any],
    b4_b9: dict[str, Any] | None = None,
    p21_g_embed: dict[str, Any] | None = None,
    p49: dict[str, Any] | None = None,
    self_test: bool = False,
) -> dict[str, Any]:
    """Build the B15 public aggregate prior / no-go screen report.

    ``b2_doc_present`` flags whether the B2 contrastive-pack experiment
    doc exists (existence only; the screen does NOT parse B2's private
    per-task detail and uses B2 ONLY as a
    ``low_n_single_model_aggregate_directional_prior``).
    ``b14_feas`` is the parsed B14 public-aggregate feasibility report
    JSON. ``b4_b9`` / ``p21_g_embed`` / ``p49`` are optional parsed
    public aggregate reports; ``None`` means the public artifact is
    unavailable (guarded).
    """
    _validate_b14_feas(b14_feas)
    if b4_b9 is not None:
        _validate_b4_b9(b4_b9)
    if p21_g_embed is not None:
        _validate_p21_g_embed(p21_g_embed)
    if p49 is not None:
        _validate_p49(p49)

    report = _base_report(self_test)
    report["source_artifact_public_note"] = (
        "already-published aggregate-only public B2 contrastive-pack "
        "experiment doc (existence only) and B14 public aggregate "
        "feasibility report; no raw records, paths, prompts, "
        "responses, snippets, or private labels read by the screen"
    )

    report["input_b2_summary"] = {
        "available": bool(b2_doc_present),
        "claim_level": B2_PRIOR_CLAIM_LEVEL,
        "usable_as_atom_causality": False,
        "usable_as_role_specific_policy": False,
        "usable_as_calibrated_policy": False,
        "usable_as_cross_model_robustness": False,
        "usable_as_hard_distractor_general_rule": False,
        "usable_as_scores_provenance_general_win": False,
        "usable_as_default_change": False,
        "usable_as_promotion": False,
        "usable_as_evidencecore_change": False,
    }
    report["input_b14_summary"] = _carry_forward_b14(b14_feas)
    report["input_b4_b9_summary"] = _carry_forward_optional("b4_b9", b4_b9)
    report["input_p21_g_embed_summary"] = _carry_forward_optional(
        "p21_g_embed", p21_g_embed
    )
    report["input_p49_summary"] = _carry_forward_optional("p49", p49)

    # Verdict: prior_screen_only when the B2 directional prior is
    # available; no_go_public_aggregate_only otherwise. In both paths
    # the screen emits a no-empirical-PackPolicy verdict.
    b14_verdict_repr = repr(b14_feas.get("verdict"))
    if b2_doc_present:
        verdict = "prior_screen_only"
        verdict_reason = (
            "B2 is low_n_single_model_aggregate_directional_prior only; "
            "public aggregates lack per-record pack atom flags, "
            "outcomes, and randomized atom assignment. No empirical "
            "B15 PackPolicy learning; no atom ablation; B14 "
            + b14_verdict_repr + " not promoting"
        )
    else:
        verdict = "no_go_public_aggregate_only"
        verdict_reason = (
            "public aggregates lack the B2 prior and per-record inputs "
            "for real B15 PackPolicy validation. No empirical B15 "
            "PackPolicy learning; no atom ablation; B14 "
            + b14_verdict_repr + " not promoting"
        )

    report["verdict"] = verdict
    report["verdict_reason"] = verdict_reason
    report["allowed_verdicts"] = list(ALLOWED_VERDICTS)

    # Missing inputs (the specific gaps that block real B15).
    report["missing_inputs_for_real_b15"] = [dict(g) for g in MISSING_INPUTS]

    # Recommended next step (cautious, no auto-promotion).
    recommended_next_step = {
        "primary": "future_ephemeral_record_b15_pack_policy_validation",
        "secondary": "future_ephemeral_record_b14_calibration_first",
        "reason": (
            "Run real B15 against ephemeral per-record inputs (pack "
            "atom flags, outcomes, role paired outputs, model_profile "
            "paired blocks, randomized atom assignment, denominator "
            "cells, token-budget controls) when available; that path "
            "performs empirical validation"
        ),
        "next_step_authorizes_promotion": False,
        "next_step_authorizes_default_change": False,
        "next_step_authorizes_pack_policy_promotion": False,
        "next_step_authorizes_runtime_clean_algorithm": False,
        "next_step_authorizes_atom_ablation": False,
        "next_step_authorizes_empirical_pack_policy_validation": False,
    }

    report.update(
        {
            "testability": {
                "full_b15_possible_from_public_artifacts": False,
                "missing_inputs_for_full_b15": [
                    g["gap_id"] for g in MISSING_INPUTS
                ],
                "note": (
                    "Real B15 cannot be replayed from the current "
                    "public B2 + B14 + B4-B9 + P21-G + P49 aggregates. "
                    "The listed missing inputs are the specific "
                    "per-record fields required. Only this bounded "
                    "prior or no-go screen is publishable until "
                    "ephemeral records arrive."
                ),
            },
            "recommended_next_step": recommended_next_step,
            "integrity": _compute_integrity(
                b14_feas,
                report["input_b4_b9_summary"],
                report["input_p21_g_embed_summary"],
                report["input_p49_summary"],
            ),
            "safety_invariants": {
                "aggregate_only_public_artifact": True,
                "promotion_ready_false": True,
                "default_should_change_false": True,
                "no_evidencecore_semantics_change": True,
                "no_live_llm_calls_by_screen": True,
                "no_empirical_pack_policy_learning": True,
                "no_atom_ablation": True,
                "no_pack_policy_promotion": True,
                "no_threshold_tuning": True,
                "no_raw_records_read": True,
                "no_raw_paths_or_digests": True,
                "no_prompts_or_responses": True,
                "no_private_labels": True,
                "no_run_ids_emitted": True,
                "no_candidate_policy_frozen": True,
                "no_stages_evaluated": True,
                "no_winner_declared": True,
                "no_fake_atom_effects_from_aggregate_means": True,
                "b2_prior_usable_only_as_directional_prior": True,
                "atom_level_inference_possible_false": True,
                "role_specific_policy_possible_false": True,
                "calibration_possible_false": True,
                "new_live_runs_required_true": True,
            },
            "framing": {
                "promotion_readiness_claimed": False,
                "default_readiness_claimed": False,
                "pack_policy_promotion_claimed": False,
                "runtime_clean_general_algorithm_claimed": False,
                "empirical_pack_policy_learning_claimed": False,
                "atom_ablation_claimed": False,
                "candidate_policy_frozen_claimed": False,
                "winner_declared_claimed": False,
                "atom_level_causality_claimed": False,
                "role_specific_policy_claimed": False,
                "calibrated_policy_claimed": False,
                "cross_model_robustness_claimed": False,
                "hard_distractor_general_rule_claimed": False,
                "scores_provenance_general_win_claimed": False,
                "evidencecore_change_claimed": False,
                "signal_strength": (
                    "bounded_public_aggregate_prior_screen_only"
                ),
                "is_full_b15_pack_policy_validation": False,
                "recommended_next_step": (
                    "future_ephemeral_record_b15_pack_policy_validation"
                ),
            },
        }
    )

    _finalize_safety(report)
    return report


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


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


def _build_synthetic_b4_b9() -> dict[str, Any]:
    """Minimal synthetic B4-B9 public aggregate report."""
    return {
        "schema_version": INPUT_B4_B9_SCHEMA,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "llm_output_not_evidence": True,
        "not_evidence": True,
        "self_test": True,
        "status": "ok",
    }


def _build_synthetic_p21_g_embed() -> dict[str, Any]:
    """Minimal synthetic P21-G embedding context report."""
    return {
        "schema_version": INPUT_P21_G_EMBED_SCHEMA,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "candidate_not_fact": True,
        "not_promotion_evidence": True,
    }


def _build_synthetic_p49() -> dict[str, Any]:
    """Minimal synthetic P49 contrastive pack scaffold report."""
    return {
        "schema_version": INPUT_P49_SCAFFOLD_SCHEMA,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "not_quality_evidence": True,
    }


def _self_test_happy_path() -> dict[str, Any]:
    b14 = _build_synthetic_b14_feas()
    b4_b9 = _build_synthetic_b4_b9()
    p21_g = _build_synthetic_p21_g_embed()
    p49 = _build_synthetic_p49()
    report = screen(
        b2_doc_present=True,
        b14_feas=b14,
        b4_b9=b4_b9,
        p21_g_embed=p21_g,
        p49=p49,
        self_test=True,
    )
    assert report["schema_version"] == SCHEMA_VERSION, report["schema_version"]
    assert report["claim_level"] == CLAIM_LEVEL, report["claim_level"]
    # Safety fields preserved verbatim.
    for k, v in (
        ("aggregate_only_public_artifact", True),
        ("candidate_not_fact", True),
        ("promotion_ready", False),
        ("default_should_change", False),
        ("evidencecore_semantics_changed", False),
        ("pack_policy_learned", False),
        ("atom_ablation_performed", False),
        ("per_record_inputs_available", False),
        ("policy_search_performed", False),
        ("stage_is_context_pack_policy", True),
        ("quality_strategy_tuned", False),
        ("new_provider_calls", 0),
        ("candidate_policy_frozen", False),
        ("stages_evaluated", False),
        ("full_b15_possible_from_public_artifacts", False),
        ("winner_declared", False),
        ("promotion_declared", False),
        ("default_recommendation_declared", False),
        ("pack_policy_promotion_declared", False),
        ("metrics_defined", True),
        ("gates_defined", True),
        ("metrics_evaluated", False),
        ("no_fake_atom_effects_from_aggregate_means", True),
        ("b2_prior_usable", True),
        ("atom_level_inference_possible", False),
        ("role_specific_policy_possible", False),
        ("calibration_possible", False),
        ("new_live_runs_required", True),
    ):
        assert report[k] == v, (k, report[k])
    # B2 prior claim level.
    assert report["b2_prior_claim_level"] == B2_PRIOR_CLAIM_LEVEL, (
        report["b2_prior_claim_level"]
    )
    # prior_screen_only verdict when B2 prior is available.
    assert report["verdict"] == "prior_screen_only", report["verdict"]
    assert report["verdict"] in ALLOWED_VERDICTS, report["verdict"]
    assert (
        "low_n_single_model_aggregate_directional_prior"
        in report["verdict_reason"]
    ), report["verdict_reason"]
    assert (
        "no empirical b15" in report["verdict_reason"].lower()
    ), report["verdict_reason"]
    # B14 no-go carried forward.
    assert report["input_b14_summary"]["b14_feasibility_verdict"] == (
        "no_go_public_aggregate_only"
    ), report["input_b14_summary"]
    assert (
        report["input_b14_summary"]["b14_uncertainty_calibration_performed"]
        is False
    )
    # Optional inputs available in happy path.
    assert report["input_b4_b9_summary"]["available"] is True
    assert report["input_p21_g_embed_summary"]["available"] is True
    assert report["input_p49_summary"]["available"] is True
    # B2 prior usage boundaries (all false).
    b2 = report["input_b2_summary"]
    for k in (
        "usable_as_atom_causality",
        "usable_as_role_specific_policy",
        "usable_as_calibrated_policy",
        "usable_as_cross_model_robustness",
        "usable_as_hard_distractor_general_rule",
        "usable_as_scores_provenance_general_win",
        "usable_as_default_change",
        "usable_as_promotion",
        "usable_as_evidencecore_change",
    ):
        assert b2[k] is False, (k, b2[k])
    # All missing inputs enumerated.
    missing_ids = [g["gap_id"] for g in report["missing_inputs_for_real_b15"]]
    expected_missing = tuple(g["gap_id"] for g in MISSING_INPUTS)
    assert missing_ids == list(expected_missing), missing_ids
    # Required missing inputs are present (the task spec).
    required_gap_ids = {
        "no_per_record_pack_atom_flags_in_public_artifact",
        "no_per_record_outcomes_in_public_artifact",
        "no_role_specific_paired_outputs_in_public_artifact",
        "no_model_profile_paired_blocks_in_public_artifact",
        "no_randomized_atom_assignment_in_public_artifact",
        "no_randomization_balance_stats_in_public_artifact",
        "no_denominator_by_atom_role_model_in_public_artifact",
        "no_token_budget_matched_controls_in_public_artifact",
        "no_runtime_state_per_record_in_public_artifact",
        "no_group_membership_for_worst_group_split_in_public_artifact",
    }
    assert required_gap_ids.issubset(set(missing_ids)), (
        required_gap_ids - set(missing_ids)
    )
    # CRITICAL: no fake metric values.
    assert report["metrics_evaluated"] is False
    assert report["no_fake_atom_effects_from_aggregate_means"] is True
    # No atom-effect / role-pack-outcome value fields.
    for forbidden_field in (
        "atom_effect_per_atom_value",
        "role_pack_outcome_value",
        "runtime_state_pack_outcome_value",
        "model_profile_pack_outcome_value",
        "worst_group_pack_outcome_value",
        "cvar_20_pack_outcome_value",
        "token_budget_parity_value",
        "denominator_per_atom_role_model_value",
        "randomization_balance_per_arm_value",
    ):
        assert forbidden_field not in report, forbidden_field
    # Integrity block computed from actual validated booleans. The
    # synthetic P21-G fixture deliberately omits
    # aggregate_only_public_artifact, so the screen MUST fail-closed:
    # all_inputs_aggregate_only_public_artifact=false with a reason.
    integ = report["integrity"]
    assert integ["forbidden_public_key_scan_clean"] is True
    assert integ["optional_inputs_guarded_when_missing"] is True
    # P21-G lacks aggregate_only_public_artifact -> fail-closed false.
    assert integ["all_inputs_aggregate_only_public_artifact"] is False, integ
    assert "all_inputs_aggregate_only_public_artifact_reasons" in integ, integ
    reasons = integ["all_inputs_aggregate_only_public_artifact_reasons"]
    assert any("p21_g_embed" in r for r in reasons), reasons
    # Forbidden-key/value scan clean (re-asserted at top level too).
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    # No raw data carried.
    assert report["raw_paths_in_artifact"] is False
    assert report["private_labels_committed"] is False
    assert report["run_ids_in_artifact"] is False
    print("self-test happy path: ok")
    return report


def _self_test_integrity_all_clean_when_p21_g_has_field() -> None:
    """When the optional P21-G aggregate also carries
    aggregate_only_public_artifact=true, the integrity
    all_inputs_aggregate_only_public_artifact field flips to true (no
    reason list). Confirms fail-closed logic is symmetric."""
    b14 = _build_synthetic_b14_feas()
    b4_b9 = _build_synthetic_b4_b9()
    # Add the fields the integrity check examines so all inputs are
    # clean.
    for r in (b4_b9,):
        r.setdefault("policy_search_performed", False)
        r.setdefault("quality_strategy_tuned", False)
        r.setdefault("new_provider_calls", 0)
    p21_g = _build_synthetic_p21_g_embed()
    p21_g["aggregate_only_public_artifact"] = True
    p21_g["policy_search_performed"] = False
    p21_g["quality_strategy_tuned"] = False
    p21_g["new_provider_calls"] = 0
    p49 = _build_synthetic_p49()
    p49["policy_search_performed"] = False
    p49["quality_strategy_tuned"] = False
    p49["new_provider_calls"] = 0
    report = screen(
        b2_doc_present=True,
        b14_feas=b14,
        b4_b9=b4_b9,
        p21_g_embed=p21_g,
        p49=p49,
        self_test=True,
    )
    integ = report["integrity"]
    assert integ["all_inputs_aggregate_only_public_artifact"] is True, integ
    assert (
        "all_inputs_aggregate_only_public_artifact_reasons" not in integ
    ), integ
    assert integ["all_inputs_promotion_ready_false"] is True, integ
    assert integ["all_inputs_policy_search_performed_false"] is True, integ
    assert integ["all_inputs_candidate_not_fact"] is True, integ
    assert integ["all_inputs_default_should_change_false"] is True, integ
    assert integ["all_inputs_evidencecore_semantics_changed_false"] is True, integ
    assert integ["all_inputs_quality_strategy_tuned_false"] is True, integ
    assert integ["all_inputs_new_provider_calls_zero"] is True, integ
    print("self-test integrity all-clean when P21-G has field: ok")


def _self_test_integrity_fail_closed_on_bad_optional() -> None:
    """When an available optional input has a bad boolean, the
    integrity field is false with a reason naming the input."""
    b14 = _build_synthetic_b14_feas()
    p49 = _build_synthetic_p49()
    # Set a field the validator does NOT check, so the bad value
    # reaches the integrity computation.
    p49["policy_search_performed"] = True  # bad
    report = screen(
        b2_doc_present=True,
        b14_feas=b14,
        p49=p49,
        self_test=True,
    )
    integ = report["integrity"]
    assert integ["all_inputs_policy_search_performed_false"] is False, integ
    reasons = integ.get("all_inputs_policy_search_performed_false_reasons", [])
    assert any("p49" in r for r in reasons), reasons
    print("self-test integrity fail-closed on bad optional: ok")


def _self_test_no_b2_doc_branch() -> None:
    """When the B2 doc is not present, the screen emits
    no_go_public_aggregate_only."""
    b14 = _build_synthetic_b14_feas()
    report = screen(
        b2_doc_present=False,
        b14_feas=b14,
        self_test=True,
    )
    assert report["verdict"] == "no_go_public_aggregate_only", report["verdict"]
    assert "no empirical b15" in report[
        "verdict_reason"
    ].lower(), report["verdict_reason"]
    # b2_prior_usable stays true (B2 is the only directional prior; if
    # the doc is missing the screen still flags the prior as the claim
    # level that WOULD apply if B2 were present). The verdict captures
    # the unavailability.
    assert report["b2_prior_claim_level"] == B2_PRIOR_CLAIM_LEVEL
    assert report["input_b2_summary"]["available"] is False
    # Still no PackPolicy learning / atom ablation.
    assert report["pack_policy_learned"] is False
    assert report["atom_ablation_performed"] is False
    assert report["per_record_inputs_available"] is False
    assert report["atom_level_inference_possible"] is False
    assert report["role_specific_policy_possible"] is False
    assert report["calibration_possible"] is False
    assert report["new_live_runs_required"] is True
    assert report["metrics_evaluated"] is False
    print("self-test no-B2-doc branch: ok")


def _self_test_optional_inputs_unavailable() -> None:
    """When the optional B4-B9 / P21-G / P49 inputs are missing, the
    screen guards them as unavailable and still emits a valid verdict."""
    b14 = _build_synthetic_b14_feas()
    report = screen(
        b2_doc_present=True,
        b14_feas=b14,
        b4_b9=None,
        p21_g_embed=None,
        p49=None,
        self_test=True,
    )
    assert report["verdict"] == "prior_screen_only", report["verdict"]
    assert report["input_b4_b9_summary"]["available"] is False
    assert report["input_p21_g_embed_summary"]["available"] is False
    assert report["input_p49_summary"]["available"] is False
    assert (
        report["input_b4_b9_summary"]["reason"]
        == "public_artifact_not_present"
    )
    assert (
        report["integrity"]["optional_inputs_guarded_when_missing"] is True
    )
    # Forbidden scan still clean.
    assert report["integrity"]["forbidden_public_key_scan_clean"] is True
    print("self-test optional inputs unavailable: ok")


def _self_test_input_validation_blocks() -> None:
    """B14 input validation blocks."""
    b4_b9 = _build_synthetic_b4_b9()
    p21_g = _build_synthetic_p21_g_embed()
    p49 = _build_synthetic_p49()

    # Wrong B14 feas schema_version.
    bad = _build_synthetic_b14_feas()
    bad["schema_version"] = "wrong"
    try:
        screen(
            b2_doc_present=True,
            b14_feas=bad,
            b4_b9=b4_b9,
            p21_g_embed=p21_g,
            p49=p49,
            self_test=True,
        )
    except ValueError as exc:
        assert "unexpected B14 feas schema_version" in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject wrong B14 feas schema_version"
        )

    # B14 promotion_ready=true rejected.
    bad = _build_synthetic_b14_feas()
    bad["promotion_ready"] = True
    try:
        screen(
            b2_doc_present=True,
            b14_feas=bad,
            self_test=True,
        )
    except ValueError as exc:
        assert "promotion_ready=false" in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject B14 promotion_ready=true"
        )

    # B14 full_b14_possible=true rejected.
    bad = _build_synthetic_b14_feas()
    bad["full_b14_possible_from_public_artifacts"] = True
    try:
        screen(
            b2_doc_present=True,
            b14_feas=bad,
            self_test=True,
        )
    except ValueError as exc:
        assert "full_b14_possible_from_public_artifacts=false" in str(
            exc
        ), exc
    else:
        raise AssertionError(
            "screen should reject B14 full_b14_possible=true"
        )

    # B14 verdict=success rejected (must be no_go / insufficient_data).
    bad = _build_synthetic_b14_feas()
    bad["verdict"] = "success"
    try:
        screen(
            b2_doc_present=True,
            b14_feas=bad,
            self_test=True,
        )
    except ValueError as exc:
        assert "no_go / insufficient_data verdict" in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject B14 verdict=success"
        )

    # Wrong B4-B9 schema_version (when present).
    bad_b4_b9 = _build_synthetic_b4_b9()
    bad_b4_b9["schema_version"] = "wrong"
    try:
        screen(
            b2_doc_present=True,
            b14_feas=_build_synthetic_b14_feas(),
            b4_b9=bad_b4_b9,
            self_test=True,
        )
    except ValueError as exc:
        assert "unexpected B4-B9 schema_version" in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject wrong B4-B9 schema_version"
        )

    # Wrong P21-G schema (when present).
    bad_p21 = _build_synthetic_p21_g_embed()
    bad_p21["schema_version"] = "wrong"
    try:
        screen(
            b2_doc_present=True,
            b14_feas=_build_synthetic_b14_feas(),
            p21_g_embed=bad_p21,
            self_test=True,
        )
    except ValueError as exc:
        assert "unexpected P21-G embed schema_version" in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject wrong P21-G schema_version"
        )

    # Wrong P49 schema (when present).
    bad_p49 = _build_synthetic_p49()
    bad_p49["schema_version"] = "wrong"
    try:
        screen(
            b2_doc_present=True,
            b14_feas=_build_synthetic_b14_feas(),
            p49=bad_p49,
            self_test=True,
        )
    except ValueError as exc:
        assert "unexpected P49 scaffold schema_version" in str(exc), exc
    else:
        raise AssertionError(
            "screen should reject wrong P49 schema_version"
        )

    print("self-test input validation blocks: ok")


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
    _self_test_integrity_all_clean_when_p21_g_has_field()
    _self_test_integrity_fail_closed_on_bad_optional()
    _self_test_no_b2_doc_branch()
    _self_test_optional_inputs_unavailable()
    _self_test_input_validation_blocks()
    _self_test_forbidden_scan()
    return {
        "schema_version": SCHEMA_VERSION,
        "claim_level": CLAIM_LEVEL,
        "self_test_passed": True,
        "self_test_checks": {
            "happy_path": True,
            "integrity_all_clean_when_p21_g_has_field": True,
            "integrity_fail_closed_on_bad_optional": True,
            "no_b2_doc_branch": True,
            "optional_inputs_unavailable": True,
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
        "--b2-doc",
        type=Path,
        default=DEFAULT_B2_DOC,
        help=(
            "path to the B2 contrastive-pack experiment doc (default: "
            "docs/en/b2-contrastive-pack-quality-experiment.md). The "
            "screen checks existence only; it does NOT parse private "
            "per-task detail."
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
        "--input-b4-b9",
        type=Path,
        default=DEFAULT_INPUT_B4_B9,
        help=(
            "optional path to the B4-B9 public aggregate report JSON "
            "(default: artifacts/b4_b9_model_robust_evidence_conversion/"
            "b4_b9_model_robust_evidence_conversion_report.json; "
            "guarded as unavailable when missing)"
        ),
    )
    parser.add_argument(
        "--input-p21-g-embed",
        type=Path,
        default=DEFAULT_INPUT_P21_G_EMBED,
        help=(
            "optional path to the P21-G embedding context report JSON "
            "(default: artifacts/p21_g/embedding_context_report.json; "
            "guarded as unavailable when missing)"
        ),
    )
    parser.add_argument(
        "--input-p49",
        type=Path,
        default=DEFAULT_INPUT_P49,
        help=(
            "optional path to the P49 contrastive pack scaffold report "
            "JSON (default: artifacts/p49_contrastive_candidate_pack_scaffold/"
            "p49_contrastive_candidate_pack_scaffold_report.json; "
            "guarded as unavailable when missing)"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=(
            "path to write the B15 public aggregate prior screen report "
            "(default: artifacts/b15_context_pack_policy/"
            "b15_public_aggregate_prior_screen_report.json)"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run the B15 public aggregate prior screen self-test "
        "(synthetic fixture)",
    )
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    if args.self_test and (
        str(args.b2_doc) != str(DEFAULT_B2_DOC)
        or str(args.input_b14) != str(DEFAULT_INPUT_B14)
        or str(args.input_b4_b9) != str(DEFAULT_INPUT_B4_B9)
        or str(args.input_p21_g_embed) != str(DEFAULT_INPUT_P21_G_EMBED)
        or str(args.input_p49) != str(DEFAULT_INPUT_P49)
    ):
        parser.error(
            "--self-test ignores --b2-doc/--input-b14/--input-b4-b9/"
            "--input-p21-g-embed/--input-p49; do not pass both"
        )
    return args


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        result = run_self_tests()
        print(json.dumps(result, indent=2, sort_keys=True))
        print(
            "B15 public aggregate prior screen self-test: PASS",
            file=sys.stderr,
        )
        return 0
    if not args.input_b14.exists():
        print(
            f"B15 prior screen B14 input not found: {args.input_b14}",
            file=sys.stderr,
        )
        return 2
    b14_feas = json.loads(args.input_b14.read_text(encoding="utf-8"))
    b4_b9 = _load_optional_json(args.input_b4_b9)
    p21_g_embed = _load_optional_json(args.input_p21_g_embed)
    p49 = _load_optional_json(args.input_p49)
    b2_doc_present = args.b2_doc.exists()
    report = screen(
        b2_doc_present=b2_doc_present,
        b14_feas=b14_feas,
        b4_b9=b4_b9,
        p21_g_embed=p21_g_embed,
        p49=p49,
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
        "stage_is_context_pack_policy": report["stage_is_context_pack_policy"],
        "pack_policy_learned": report["pack_policy_learned"],
        "atom_ablation_performed": report["atom_ablation_performed"],
        "per_record_inputs_available": report["per_record_inputs_available"],
        "policy_search_performed": report["policy_search_performed"],
        "candidate_policy_frozen": report["candidate_policy_frozen"],
        "stages_evaluated": report["stages_evaluated"],
        "winner_declared": report["winner_declared"],
        "metrics_evaluated": report["metrics_evaluated"],
        "no_fake_atom_effects_from_aggregate_means": report[
            "no_fake_atom_effects_from_aggregate_means"
        ],
        "b2_prior_usable": report["b2_prior_usable"],
        "b2_prior_claim_level": report["b2_prior_claim_level"],
        "atom_level_inference_possible": report[
            "atom_level_inference_possible"
        ],
        "role_specific_policy_possible": report[
            "role_specific_policy_possible"
        ],
        "calibration_possible": report["calibration_possible"],
        "new_live_runs_required": report["new_live_runs_required"],
        "full_b15_possible_from_public_artifacts": report[
            "full_b15_possible_from_public_artifacts"
        ],
        "new_provider_calls": report["new_provider_calls"],
        "input_b2_available": report["input_b2_summary"]["available"],
        "input_b4_b9_available": report["input_b4_b9_summary"]["available"],
        "input_p21_g_embed_available": report["input_p21_g_embed_summary"][
            "available"
        ],
        "input_p49_available": report["input_p49_summary"]["available"],
        "missing_inputs_for_real_b15": [
            g["gap_id"] for g in report["missing_inputs_for_real_b15"]
        ],
        "out": str(args.out),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
