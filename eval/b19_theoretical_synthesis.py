#!/usr/bin/env python3
"""B19 Theoretical Synthesis (Model-Robust Selective Evidence Conversion).

B19 is the **theoretical synthesis** of the B10-B18 Breakthrough Sprint.
It is **synthesis-only**: it does NOT run any provider, does NOT change
retrieval / default / EvidenceCore, and does NOT claim promotion. It
synthesizes B10 / B10B / B11 / B12 / B13 / B14 / B15 / B16 / B17 / B18
into a single paper-style algorithm report for the candidate algorithm
concept **Model-Robust Selective Evidence Conversion**.

This file ships three modes:

* ``--self-test`` (read-only): builds the expected algorithm concept +
  synthesis report in memory and compares them to the on-disk
  artifacts, failing on drift. It also verifies: required formal
  sections present, all no-promotion flags false, the B11 official
  matrix deltas are exact, the public-output forbidden-key scan is
  clean, the B19 docs links exist, and the report content hash
  (drift guard) matches.
* ``--regenerate-artifacts``: the ONLY path that mutates checked-in
  artifacts. It (re)writes the canonical B19 synthesis report JSON
  from the current build function and then re-runs the self-test to
  confirm the on-disk artifact matches the in-memory build.
* ``--input <path>``: a stub that requires ``--out`` and returns
  ``verdict="not_implemented"``. B19 is synthesis-only; there is no
  per-record input path. The stub exists so callers cannot silently
  mistake B19 for an empirical evaluation.

Aggregate-only public artifact: no task_id / repo_id / candidate_id /
path / span / snippet / prompt / response / gold_spans / content_sha /
provider_key / base_url / api_key / raw records / raw paths / raw
spans / raw snippets / prompts / responses / gold labels.

Run::

    python3 eval/b19_theoretical_synthesis.py --self-test
    python3 eval/b19_theoretical_synthesis.py --regenerate-artifacts
    python3 eval/b19_theoretical_synthesis.py --self-test
    python3 eval/b19_theoretical_synthesis.py \\
        --input path/to/anything.json --out /tmp/b19_input_stub.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_FILE_DIR = Path(__file__).resolve().parent
if str(_FILE_DIR) not in sys.path:
    sys.path.insert(0, str(_FILE_DIR))

import b6_lite_interpretable_policy_search as b6lite  # noqa: E402  (forbidden scan)

REPO_ROOT = _FILE_DIR.parent

SCHEMA_VERSION = "b19-theoretical-synthesis-report-v0"
GENERATED_BY = "b19_theoretical_synthesis"
CLAIM_LEVEL = "theoretical_synthesis_of_b10_through_b18"
ALGORITHM_CONCEPT = "Model-Robust Selective Evidence Conversion"

ARTIFACT_DIR = REPO_ROOT / "artifacts" / "b19_theoretical_synthesis"
REPORT_PATH = ARTIFACT_DIR / "b19_theoretical_synthesis_report.json"

# B19 docs links that MUST exist on disk after this commit. The self-test
# verifies each of these resolves (relative to docs/en and docs/zh).
REQUIRED_DOCS_BASENAMES = (
    "b19-theoretical-synthesis.md",
)

# Source-stage synthesized reports pinned by this synthesis. These are
# the public aggregate artifacts that B19 carries forward. The self-test
# verifies each is present on disk. The relative paths are kept here for
# the on-disk pin check only; the PUBLIC report emits only slash-free
# spec_ids (see SYNTHESIZED_SOURCE_SPEC_IDS) so the forbidden-value
# scan never sees path-like strings.
SYNTHESIZED_SOURCE_ARTIFACTS = (
    "artifacts/b10_runtime_feature_audit/balanced_policy_v1_benchmark_routed.algorithm.json",
    "artifacts/b10b_runtime_shadow_replay/b10b_runtime_shadow_replay_report.json",
    "artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json",
    "artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json",
    "artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json",
    "artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json",
    "artifacts/b15_context_pack_policy/b15_public_aggregate_prior_screen_report.json",
    "artifacts/b16_downstream_agent_evaluation/b16_public_aggregate_feasibility_report.json",
    "artifacts/b17_quiver_systems_track/b17_public_systems_diagnostic_screen_report.json",
    "artifacts/b18_ood_temporal_evaluation/b18_public_ood_temporal_screen_report.json",
)

# Slash-free spec identifiers published in the public report (one per
# synthesized source artifact). These are safe to publish and the
# forbidden-value scan accepts them.
SYNTHESIZED_SOURCE_SPEC_IDS = (
    "b10_balanced_policy_v1_benchmark_routed_spec",
    "b10b_runtime_shadow_replay_report",
    "b11_prospective_matrix_aggregate_report",
    "b12_public_aggregate_mechanism_screen_report",
    "b13_public_aggregate_feasibility_report",
    "b14_public_aggregate_feasibility_report",
    "b15_public_aggregate_prior_screen_report",
    "b16_public_aggregate_feasibility_report",
    "b17_public_systems_diagnostic_screen_report",
    "b18_public_ood_temporal_screen_report",
)

# B11 official integrated matrix deltas (balanced_v1 vs p25), frozen exact
# values from
# artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json.
# These are the ONLY empirical numbers B19 carries forward verbatim, and the
# self-test asserts them byte-for-byte against the source artifact.
B11_DELTAS_BALANCED_V1_VS_P25 = {
    "gold_span": -0.002604,
    "span_f0_5": -0.001899,
    "false_span": -0.054688,
    "primary_false_positive_rate": -0.020833,
    "model_calls": -0.354167,
}

# Formal sections required in the synthesis report. The self-test asserts
# each key is present and non-empty.
REQUIRED_FORMAL_SECTIONS = (
    "problem_statement",
    "algorithm_sketch_pseudocode",
    "evidence_boundary",
    "policy_learning_loop",
    "adapter_boundary",
    "evaluation_protocol",
    "current_empirical_evidence",
    "no_go_gaps",
    "promotion_blockers",
    "next_research_program",
)

# All flags that MUST be false for B19. The self-test asserts each is
# literally boolean False in the on-disk report.
MUST_BE_FALSE_FLAGS = (
    "promotion_ready",
    "default_should_change",
    "evidencecore_semantics_changed",
    "runtime_clean_policy_supported",
    "downstream_agent_value_proven",
    "ood_temporal_supported",
    "quiver_systems_supported",
    "is_new_experiment",
    "ran_providers",
    "changed_retrieval_default_evidencecore",
    "policy_search_performed",
    "quality_strategy_tuned",
    "retrieval_policy_changed",
    "winner_declared",
    "backend_quality_promoted",
    "pack_policy_learned",
    "atom_ablation_performed",
    "uncertainty_calibration_performed",
    "ann_backend_bakeoff_performed",
    "quiver_graph_implemented",
    "ood_temporal_evaluation_performed",
    "metrics_evaluated",
    "private_labels_committed",
    "raw_prompts_stored",
    "raw_responses_stored",
    "raw_snippets_committed",
    "raw_paths_in_artifact",
    "raw_digests_in_artifact",
    "gold_spans_in_artifact",
    "task_ids_in_artifact",
    "candidate_ids_in_artifact",
    "repo_ids_in_artifact",
    "run_ids_in_artifact",
)

MUST_BE_TRUE_FLAGS = (
    "aggregate_only_public_artifact",
    "candidate_not_fact",
    "not_evidence",
    "llm_output_not_evidence",
    "is_synthesis_only",
    "new_provider_calls_zero",
    "forbidden_public_scan_clean",
    "report_drift_guarded",
    "docs_links_exist",
    "synthesized_source_artifacts_pinned",
)

# Volatile / self-referential keys excluded from the content hash (drift
# guard). The hash is over the substantive content only so regeneration is
# deterministic, and the hash itself is excluded to avoid a self-reference.
_VOLATILE_KEYS = {"generated_at", "report_content_sha256"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _canonical_content_hash(obj: Any) -> str:
    """SHA-256 over the canonical sorted-keys JSON, excluding volatile keys."""

    def _strip(o: Any) -> Any:
        if isinstance(o, dict):
            return {k: _strip(v) for k, v in o.items() if k not in _VOLATILE_KEYS}
        if isinstance(o, list):
            return [_strip(v) for v in o]
        return o

    payload = json.dumps(_strip(obj), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _algorithm_concept_block() -> dict[str, Any]:
    return {
        "algorithm_concept": ALGORITHM_CONCEPT,
        "one_line": (
            "A model-robust, runtime-clean, evidence-gated policy that "
            "selectively converts high-reach / high-false-cost local "
            "candidate pools into current-source EvidenceCore spans by "
            "decoupling recall from admission, routing LLM roles "
            "selectively, and optimizing worst-group utility across "
            "model adapters."
        ),
        "inputs": [
            "query",
            "local_candidate_pool",
            "runtime_observable_uncertainty",
            "model_capability_profile",
            "latency_cost_budget",
        ],
        "outputs_actions": [
            "local_only",
            "weak_or_supporting",
            "llm_span_narrow",
            "llm_filter",
            "abstain",
            "request_more_context",
            "evidencecore_materialization",
        ],
        "core_principles": [
            "recall_admission_decoupling",
            "llm_role_selective_routing",
            "algorithm_model_adapter_separation",
            "runtime_observable_features_only_for_runtime_clean_policy",
            "worst_group_and_cross_model_robust_optimization",
            "candidate_must_materialize_into_current_source_evidencecore",
        ],
        "action_terminal_constraint": (
            "Every selected action must terminate in a current-source "
            "EvidenceCore materialization (path + start_line + end_line + "
            "content_sha + score + why + channels) or in an explicit "
            "abstain / request-more-context signal. No action may emit a "
            "candidate, LLM output, or supporting view as Evidence."
        ),
    }


def _synthesized_evidence_block() -> dict[str, Any]:
    """Per-stage synthesis of B10-B18. Carries forward ONLY already-published
    public-aggregate findings; introduces NO new empirical claims."""

    return {
        "B10": {
            "stage": "runtime_feature_audit_and_balanced_policy_v1_freeze",
            "finding": (
                "balanced_policy_v1_benchmark_routed was benchmark-routed, "
                "not runtime-clean. The _ambiguous_like branch reads the "
                "benchmark public labels task_bucket / task_risk_tags, so a "
                "runtime-feature-only mode would never fire the "
                "ambiguous_query_weak_only rule. "
                "runtime_clean=false, "
                "runtime_feature_only_mode_supported=false."
            ),
            "claim_level": "benchmark_routed_algorithm_spec_only",
            "promotion_ready": False,
        },
        "B10B": {
            "stage": "runtime_shadow_replay_ambiguous_branch_only",
            "finding": (
                "Provided a mechanics-validated runtime-shadow scaffold and "
                "CI integration. Empirical support is pending because the "
                "label-driven ambiguous denominator stayed below the 10-record "
                "hard gate in all B11 runs (max observed "
                "label_driven_ambiguous_denominator_qn0=3). Verdict on the "
                "synthetic fixture: mechanics_only_synthetic_fixture; on CI "
                "records: empirical_replay_support_pending."
            ),
            "claim_level": "ambiguous_branch_runtime_shadow_only",
            "promotion_ready": False,
        },
        "B11": {
            "stage": "prospective_blind_validation_official_integrated_matrix",
            "finding": (
                "Official integrated matrix: 32/32 final cells, 384 records, "
                "aggregate verdict partial_with_failure (success 8 / partial "
                "23 / failure 1). Balanced v1 vs P25 deltas preserve near-parity "
                "SpanF0.5 / gold_span while reducing false_span, PFP, and "
                "model_calls. Strengthens the algorithm-candidate signal but is "
                "NOT promotion."
            ),
            "claim_level": "derived_aggregate_of_b11_prospective_validation_reports",
            "aggregate_verdict": "partial_with_failure",
            "deltas_balanced_v1_vs_p25": dict(B11_DELTAS_BALANCED_V1_VS_P25),
            "b10b_runtime_shadow_status": "empirical_replay_support_pending_due_denominator",
            "promotion_ready": False,
        },
        "B12": {
            "stage": "mechanism_decomposition_public_aggregate_screen",
            "finding": (
                "The public aggregate cannot identify mechanism. Full B12 "
                "per-record replay is impossible from the public B11 "
                "aggregate: it lacks per-record route decisions, ambiguous-"
                "subset membership, deterministic call-reduction variant B, "
                "random call-reduction variant E, and weak_candidate_only "
                "per-strategy outcomes. Emits per-hypothesis screen statuses "
                "only, never a single global supported verdict."
            ),
            "claim_level": "bounded_public_aggregate_mechanism_screen_of_b11_aggregate",
            "promotion_ready": False,
        },
        "B13": {
            "stage": "distributionally_robust_policy_search_public_aggregate_screen",
            "finding": (
                "The public aggregate cannot run real DRO search. Real B13 "
                "requires per-record group / action outcomes and rotating "
                "leave-one-model-family-out rotations over per-record records, "
                "none of which are present in the public B11 aggregate. "
                "verdict=no_go_public_aggregate_only."
            ),
            "claim_level": "bounded_public_aggregate_feasibility_screen_of_b11_b12_aggregates",
            "verdict": "no_go_public_aggregate_only",
            "promotion_ready": False,
        },
        "B14": {
            "stage": "uncertainty_calibration_public_aggregate_feasibility_screen",
            "finding": (
                "Cannot calibrate uncertainty from public aggregates. Real B14 "
                "requires per-record uncertainty scores, per-record binary "
                "outcomes, paired cross-model outputs, schema-repair per-call "
                "rows, and candidate score distributions. The public B11 "
                "aggregate carries only weighted means. "
                "verdict=no_go_public_aggregate_only."
            ),
            "claim_level": "bounded_public_aggregate_feasibility_screen_of_b11_b12_b13_aggregates",
            "verdict": "no_go_public_aggregate_only",
            "promotion_ready": False,
        },
        "B15": {
            "stage": "context_pack_policy_public_aggregate_prior_screen",
            "finding": (
                "Cannot learn a Context Pack Policy from public aggregates. "
                "Real B15 requires per-record pack atom flags, per-record "
                "outcomes, role-specific paired outputs, model_profile paired "
                "blocks, randomized atom assignment, balance stats, and "
                "token-budget-matched controls. The current value of B15 is "
                "preregistration / prior screen only (B2 usable only as a "
                "low_n_single_model_aggregate_directional_prior)."
            ),
            "claim_level": "bounded_public_aggregate_prior_screen_of_b2_b14_and_optional_aggregates",
            "verdict": "prior_screen_only",
            "promotion_ready": False,
        },
        "B16": {
            "stage": "downstream_agent_evaluation_public_aggregate_feasibility_screen",
            "finding": (
                "Downstream agent value is unproven. Real B16 requires paired "
                "live downstream agent runs, per-run patches/diffs, test "
                "execution results, solve labels, first-file-before-first-"
                "edit events, wrong-file-edit annotations, tool-call/token/"
                "latency/cost rows, isolated workspace proof, randomized arm "
                "order, and a task oracle/hidden-test manifest. Retrieval "
                "improvements are NOT downstream agent improvements. "
                "verdict=no_go_public_aggregate_only."
            ),
            "claim_level": "bounded_public_aggregate_feasibility_screen_of_b11_b12_b13_b14_b15_aggregates",
            "verdict": "no_go_public_aggregate_only",
            "promotion_ready": False,
        },
        "B17": {
            "stage": "quiver_systems_track_public_systems_diagnostic_screen",
            "finding": (
                "QuIVer systems track is no-go because the QuIVer graph / "
                "vector backend is missing. The existing R33 / R34 / R36 / R24 "
                "and real-provider P3 / P4 diagnostics are diagnostic-only "
                "carry-forward: they do NOT implement a QuIVer / Vamana graph "
                "backend, do NOT contain an HNSW run, and do NOT contain a "
                "candidate-set equivalence matrix across backends. This is a "
                "systems-only future track. verdict=no_go_quiver_graph_missing."
            ),
            "claim_level": "bounded_public_systems_diagnostic_carry_forward_screen_of_r33_r34_r36_real_p3_p4_r24",
            "verdict": "no_go_quiver_graph_missing",
            "promotion_ready": False,
        },
        "B18": {
            "stage": "ood_temporal_evaluation_public_aggregate_no_go_screen",
            "finding": (
                "OOD / temporal evaluation is no-go from the public aggregate. "
                "Real B18 requires per-record temporal / repo / language / "
                "model_family / adversarial axes with a real time axis and "
                "commit chronology. The public B11 aggregate carries only "
                "weighted means and a sanitized failure slice list; the R15 / "
                "R20 / R26 repo locks are synthetic static snapshots. "
                "verdict=no_go_public_aggregate_only."
            ),
            "claim_level": "bounded_public_aggregate_no_go_screen_of_b11_r15_r20_r26",
            "verdict": "no_go_public_aggregate_only",
            "promotion_ready": False,
        },
    }


def _formal_sections_block() -> dict[str, Any]:
    pseudocode = (
        "function CONVERT(query, local_candidate_pool, runtime_uncertainty,\n"
        "                 model_profile, latency_cost_budget):\n"
        "    # 1. RUN-phase routing uses ONLY runtime-observable features.\n"
        "    feats = observe_runtime_features(local_candidate_pool, query)\n"
        "    if not feats.all_present:\n"
        "        return ACTION_REQUEST_MORE_CONTEXT\n"
        "    # 2. Recall / admission decoupling: reach comes from local\n"
        "    #    candidates; admission is a separate decision.\n"
        "    recall_pool = local_candidate_pool\n"
        "    # 3. Worst-group / cross-model robust action selection.\n"
        "    action = robust_select(\n"
        "        features=feats,\n"
        "        uncertainty=runtime_uncertainty,\n"
        "        model_profile=model_profile,\n"
        "        budget=latency_cost_budget,\n"
        "        objective=RobustUtility_worst_group,\n"
        "        adapter=model_adapter,  # NOT part of algorithm_spec\n"
        "    )\n"
        "    # 4. LLM role is SELECTIVE: span_narrow / filter only when the\n"
        "    #    runtime predicate fires and budget permits.\n"
        "    if action in {LLM_SPAN_NARROW, LLM_FILTER}:\n"
        "        llm_view = model_adapter.call(action, recall_pool, budget)\n"
        "        llm_view.not_evidence = True\n"
        "    # 5. Candidate must materialize into current-source EvidenceCore.\n"
        "    evidence = materialize_current_source_evidencecore(action, recall_pool, llm_view)\n"
        "    if evidence is None:\n"
        "        return ACTION_ABSTAIN or ACTION_REQUEST_MORE_CONTEXT\n"
        "    return evidence  # EvidenceCore: path, start_line, end_line,\n"
        "                     # content_sha, score, why, channels"
    )

    return {
        "problem_statement": (
            "Local candidate pools (RRF, symbol/regex, dense) reach the gold "
            "file/span often but carry high false-span and primary-false-"
            "positive cost. A single global LLM pass is unsafe across mixed "
            "task buckets, and a benchmark-routed policy cannot be promoted "
            "because it depends on labels unavailable at runtime. The problem "
            "is to convert high-reach / high-false-cost candidates into low-"
            "false-cost, citation-valid EvidenceCore spans without weakening "
            "the evidence contract, without making any one model's behavior "
            "the OpenLocus algorithm, and without mistaking an in-"
            "distribution average for cross-model / OOD / temporal "
            "generalization."
        ),
        "algorithm_sketch_pseudocode": pseudocode,
        "evidence_boundary": (
            "Every selected action terminates in a current-source "
            "EvidenceCore materialization (path + start_line + end_line + "
            "content_sha + score + why + channels) or in an explicit abstain "
            "/ request-more-context signal. LLM outputs are not_evidence=true "
            "candidate/supporting channels only; they can narrow, filter, or "
            "disambiguate, but they can never become Evidence, never produce "
            "gold labels, never produce citation verdicts, and never produce "
            "promotion verdicts. The current-source read is the final fact "
            "authority; stale / mismatched content_sha candidates are rejected."
        ),
        "policy_learning_loop": (
            "The loop is: freeze an algorithm_spec that uses only runtime-"
            "observable features -> run a preregistered prospective validation "
            "with no retuning (B11) -> decompose mechanism via per-record "
            "replay (B12, needs per-record data) -> search a worst-group / "
            "cross-model robust policy (B13, needs per-record group/action "
            "outcomes) -> calibrate a model-independent uncertainty score "
            "(B14, needs per-record (uncertainty, outcome) pairs) -> learn a "
            "frozen PackPolicy from per-record atom effects (B15, needs "
            "per-record atom flags) -> evaluate downstream agent value (B16, "
            "needs paired agent runs) -> evaluate OOD / temporal "
            "generalization (B18, needs per-record time axis). Every loop "
            "iteration that lacks the required per-record inputs emits a "
            "no-go / prior-screen / insufficient_data verdict and does NOT "
            "auto-promote. Promotion is a separate, future, evidence-gated "
            "decision; it is never the output of the loop itself."
        ),
        "adapter_boundary": (
            "algorithm_spec is model-independent: it references only runtime-"
            "observable route_features and abstract model_profile capability "
            "slots (cost_class, latency_class, supports_reliable_span_narrow, "
            "family_slots). model_adapter (model identity + output mode + "
            "provider credentials / endpoints / secrets) is an EXCLUDED "
            "adapter layer, not part of the algorithm spec. Output mode "
            "(tool_call / json_schema_strict) is a model-adapter configuration "
            "parameter, not an OpenLocus algorithm variable. A noisy adapter "
            "cannot become a quality conclusion about the algorithm, and an "
            "algorithm-quality claim cannot be smuggled in as an adapter "
            "leaderboard."
        ),
        "evaluation_protocol": (
            "Prospective, preregistered, no-retuning validation. Success / "
            "partial / failure criteria are frozen BEFORE any live runs on "
            "explicit overall and worst-group thresholds (delta gold_span, "
            "delta SpanF0.5, delta PFP, delta false_spans, delta LLM_calls) "
            "plus a worst-group RobustUtility = min_group(SpanF0.5 - "
            "lambda*PFP - mu*normalized_cost - nu*normalized_latency). "
            "Validation uses rotating leave-one-model-family-out rotations "
            "and stratified fresh-validation splits. Per-record replay is the "
            "evidence boundary for mechanism (B12), DRO (B13), calibration "
            "(B14), pack policy (B15), downstream agent value (B16), QuIVer "
            "systems (B17), and OOD / temporal (B18). Public artifacts are "
            "aggregate-only; per-record records stay under runner temp."
        ),
        "current_empirical_evidence": {
            "strongest_signal": (
                "B11 official integrated matrix (32/32, 384 records): "
                "balanced_v1 vs p25 deltas preserve near-parity SpanF0.5 / "
                "gold_span while reducing false_span, PFP, and model_calls "
                "on average."
            ),
            "deltas_balanced_v1_vs_p25": dict(B11_DELTAS_BALANCED_V1_VS_P25),
            "aggregate_verdict": "partial_with_failure",
            "verdict_counts": {"success": 8, "partial": 23, "failure": 1},
            "b10b_runtime_shadow_status": "empirical_replay_support_pending_due_denominator",
            "summary": (
                "The current empirical evidence strengthens the algorithm-"
                "candidate signal but does NOT prove a runtime-clean general "
                "algorithm. The B10B runtime-shadow predicate is empirical-"
                "pending (label-driven denominator < 10 in all B11 runs). B11 "
                "is mixed / partial; one Kimi py_fastapi slice exceeded the "
                "failure_spanf05_delta threshold."
            ),
        },
        "no_go_gaps": [
            {
                "stage": "B12",
                "gap": "public aggregate cannot identify mechanism",
                "missing": [
                    "per_record_route_decisions",
                    "ambiguous_subset_membership",
                    "deterministic_call_reduction_variant_B",
                    "random_call_reduction_variant_E",
                    "weak_candidate_only_per_strategy_outcomes",
                ],
            },
            {
                "stage": "B13",
                "gap": "public aggregate cannot run real DRO search",
                "missing": [
                    "per_record_group_outcomes",
                    "per_record_action_outcomes",
                    "rotating_leave_one_model_family_out_rotations_over_per_record_records",
                ],
            },
            {
                "stage": "B14",
                "gap": "cannot calibrate uncertainty from public aggregates",
                "missing": [
                    "per_record_uncertainty_scores",
                    "per_record_binary_outcomes",
                    "paired_cross_model_outputs",
                    "schema_repair_per_call_rows",
                    "candidate_score_distributions",
                ],
            },
            {
                "stage": "B15",
                "gap": "cannot learn Context Pack Policy from public aggregates",
                "missing": [
                    "per_record_pack_atom_flags",
                    "per_record_outcomes",
                    "role_specific_paired_outputs",
                    "model_profile_paired_blocks",
                    "randomized_atom_assignment",
                    "randomization_balance_stats",
                    "token_budget_matched_controls",
                ],
            },
            {
                "stage": "B16",
                "gap": "downstream agent value unproven",
                "missing": [
                    "paired_live_downstream_agent_runs",
                    "per_run_patches_or_diffs",
                    "test_execution_results",
                    "solve_labels",
                    "first_file_before_first_edit_events",
                    "wrong_file_edit_annotations",
                    "tool_calls_tokens_latency_cost_per_run",
                    "isolated_workspace_proof",
                    "randomized_arm_order",
                    "task_oracle_or_hidden_test_manifest",
                ],
            },
            {
                "stage": "B17",
                "gap": "QuIVer systems track no-go: graph / vector backend missing",
                "missing": [
                    "quiver_or_vamana_graph_backend_implementation",
                    "hnsw_backend_run",
                    "candidate_set_equivalence_matrix_across_backends",
                    "shared_frozen_candidate_quality_manifest",
                ],
            },
            {
                "stage": "B18",
                "gap": "OOD / temporal no-go from public aggregate",
                "missing": [
                    "per_record_records",
                    "time_axis",
                    "commit_chronology",
                    "per_repo_per_language_cells",
                    "model_family_x_repo_matrix",
                    "adversarial_holdout_outcomes",
                    "temporal_holdout_outcomes",
                ],
            },
        ],
        "promotion_blockers": [
            "B10 runtime_clean=false: the frozen balanced_policy_v1 is benchmark-routed, not runtime-clean.",
            "B10B runtime_shadow_ambiguous_supported=false on all B11 runs (label-driven denominator < 10 hard gate).",
            "B11 aggregate_verdict=partial_with_failure (one Kimi py_fastapi slice exceeded failure_spanf05_delta).",
            "B12/B13/B14/B15/B16/B17/B18 are public-aggregate no-go or screen-only; none authorizes promotion.",
            "No per-record mechanism, DRO, calibration, pack-policy, downstream-agent, QuIVer, or OOD/temporal evidence exists in any current public artifact.",
            "Promotion is a separate future evidence-gated decision; the B10-B18 sprint does NOT produce it.",
        ],
        "next_research_program": [
            "Replace the benchmark-routed ambiguous branch with pure runtime features (query_noise, candidate_support_exists, anchor disagreement) and run B10B on real CI ephemeral records until the 10-record hard gate passes.",
            "Collect per-record route / action / group outcomes so B12 mechanism decomposition and B13 DRO search can run for real.",
            "Collect per-record (uncertainty, binary outcome) pairs so B14 can calibrate a model-independent uncertainty score.",
            "Collect per-record pack atom flags + role + runtime_state + model_profile so B15 can learn a frozen PackPolicy.",
            "Stand up a fixed downstream agent harness with isolated fresh workspaces, randomized arm order, and patch/test outcome capture so B16 can prove (or refute) downstream value.",
            "Implement a QuIVer / Vamana graph backend and a shared frozen candidate-quality manifest so B17 can run a real systems bakeoff.",
            "Collect per-record temporal / repo / language / model_family / adversarial axes with a real time axis and commit chronology so B18 can run a real OOD / temporal evaluation under the no-retuning protocol.",
            "Only after the above, open a separate promotion preregistration; the synthesis itself never authorizes promotion.",
        ],
    }


def _forbidden_scan(report: dict[str, Any]) -> list[str]:
    """B19-specific public-output forbidden scan.

    B19 is a paper-style synthesis: its formal sections are intentionally
    long prose. The shared ``b6_lite._walk_forbidden`` helper flags any
    string > 256 chars as a privacy guard against embedded snippets /
    responses, which is the wrong semantic here. B19 instead enforces:

    * no forbidden KEYS (task_id / repo_id / candidate_id / path /
      snippet / prompt / response / gold_spans / content_sha / digest /
      provider_key / base_url / api_key / api_token / api_secret /
      private_labels / score_group / ...);
    * no hash-like VALUES (32+ hex chars) that would indicate an
    accidentally embedded digest / content_sha.

    Long prose strings are explicitly allowed because B19 IS the
    synthesis prose.
    """

    forbidden_keys = b6lite.FORBIDDEN_PUBLIC_KEYS
    # report_content_sha256 is the B19 self-hash drift guard (computed over
    # the report's own content). It is NOT an embedded source digest, so it
    # is whitelisted from the digest-like value check by key name.
    digest_exempt_keys = {"report_content_sha256"}
    digest_like = b6lite.re.compile(r"[A-Fa-f0-9]{32,}")
    violations: list[str] = []

    def _walk(obj: Any, path: str = "$", parent_key: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if str(key) in forbidden_keys:
                    violations.append(f"{path}.{key}:forbidden_key")
                _walk(value, f"{path}.{key}", str(key))
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                _walk(value, f"{path}[{idx}]", parent_key)
        elif isinstance(obj, str):
            if parent_key in digest_exempt_keys:
                return
            if digest_like.search(obj):
                violations.append(f"{path}:digest_like_value")

    _walk(report)
    return violations


def build_report(generated_at: str | None = None) -> dict[str, Any]:
    """Build the canonical B19 theoretical-synthesis report."""

    concept = _algorithm_concept_block()
    synthesized = _synthesized_evidence_block()
    formal = _formal_sections_block()

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "generated_at": generated_at or _now(),
        "claim_level": CLAIM_LEVEL,
        "algorithm_concept": ALGORITHM_CONCEPT,
        "is_synthesis_only": True,
        "is_new_experiment": False,
        "ran_providers": False,
        "new_provider_calls": 0,
        "new_provider_calls_zero": True,
        "changed_retrieval_default_evidencecore": False,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "not_evidence": True,
        "llm_output_not_evidence": True,
        "synthesized_stages": [
            "B10",
            "B10B",
            "B11",
            "B12",
            "B13",
            "B14",
            "B15",
            "B16",
            "B17",
            "B18",
        ],
        "synthesized_source_artifacts_pinned": True,
        "synthesized_source_spec_ids": list(SYNTHESIZED_SOURCE_SPEC_IDS),
        # No-promotion flags.
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "runtime_clean_policy_supported": False,
        "downstream_agent_value_proven": False,
        "ood_temporal_supported": False,
        "quiver_systems_supported": False,
        # Carry-forward safety invariants (kept false for clarity).
        "policy_search_performed": False,
        "quality_strategy_tuned": False,
        "retrieval_policy_changed": False,
        "winner_declared": False,
        "backend_quality_promoted": False,
        "pack_policy_learned": False,
        "atom_ablation_performed": False,
        "uncertainty_calibration_performed": False,
        "ann_backend_bakeoff_performed": False,
        "quiver_graph_implemented": False,
        "ood_temporal_evaluation_performed": False,
        "metrics_evaluated": False,
        "private_labels_committed": False,
        "raw_prompts_stored": False,
        "raw_responses_stored": False,
        "raw_snippets_committed": False,
        "raw_paths_in_artifact": False,
        "raw_digests_in_artifact": False,
        "gold_spans_in_artifact": False,
        "task_ids_in_artifact": False,
        "candidate_ids_in_artifact": False,
        "repo_ids_in_artifact": False,
        "run_ids_in_artifact": False,
        # Content.
        "algorithm_concept_block": concept,
        "synthesized_evidence": synthesized,
        "formal_sections": formal,
        "b11_deltas_balanced_v1_vs_p25": dict(B11_DELTAS_BALANCED_V1_VS_P25),
        "no_fake_metrics_beyond_b10_b18": True,
        "forbidden_public_scan_clean": True,
        "report_drift_guarded": True,
        "docs_links_exist": True,
        "required_docs_basenames": list(REQUIRED_DOCS_BASENAMES),
    }

    # Compute the drift-guard hash over the substantive content (excluding
    # volatile keys) and embed it. The self-test recomputes and compares.
    report["report_content_sha256"] = _canonical_content_hash(report)
    return report


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _verify_b11_deltas_against_source() -> dict[str, float]:
    """Read the B11 source aggregate and assert the deltas match exactly."""

    src = REPO_ROOT / SYNTHESIZED_SOURCE_ARTIFACTS[2]
    _assert(src.is_file(), f"B11 source artifact missing: {src}")
    data = json.loads(src.read_text(encoding="utf-8"))
    src_deltas = data.get("deltas_balanced_v1_vs_p25", {})
    for key, expected in B11_DELTAS_BALANCED_V1_VS_P25.items():
        actual = src_deltas.get(key)
        _assert(
            actual == expected,
            f"B11 delta {key}: expected {expected}, source has {actual!r}",
        )
    return src_deltas


def _verify_docs_links_exist() -> None:
    for base in REQUIRED_DOCS_BASENAMES:
        for lang_dir in ("en", "zh"):
            p = REPO_ROOT / "docs" / lang_dir / base
            _assert(
                p.is_file(),
                f"B19 docs link missing: {p.relative_to(REPO_ROOT)}",
            )


def _verify_synthesized_source_artifacts_pinned() -> None:
    for rel in SYNTHESIZED_SOURCE_ARTIFACTS:
        p = REPO_ROOT / rel
        _assert(
            p.is_file(),
            f"Synthesized source artifact missing: {p.relative_to(REPO_ROOT)}",
        )


def _verify_report_invariants(report: dict[str, Any]) -> None:
    # Required formal sections.
    formal = report.get("formal_sections", {})
    for section in REQUIRED_FORMAL_SECTIONS:
        _assert(section in formal, f"Missing formal section: {section}")
        _assert(
            bool(formal[section]),
            f"Empty formal section: {section}",
        )

    # All no-promotion flags must be literal False.
    for flag in MUST_BE_FALSE_FLAGS:
        _assert(
            report.get(flag) is False,
            f"Flag {flag} must be False, got {report.get(flag)!r}",
        )

    # All must-be-true flags must be literal True.
    for flag in MUST_BE_TRUE_FLAGS:
        _assert(
            report.get(flag) is True,
            f"Flag {flag} must be True, got {report.get(flag)!r}",
        )

    # B11 deltas present and exact.
    deltas = report.get("b11_deltas_balanced_v1_vs_p25", {})
    for key, expected in B11_DELTAS_BALANCED_V1_VS_P25.items():
        _assert(
            deltas.get(key) == expected,
            f"Report B11 delta {key}: expected {expected}, got {deltas.get(key)!r}",
        )

    # Cross-check deltas against the source artifact.
    _verify_b11_deltas_against_source()

    # Synthesized stages.
    expected_stages = ["B10", "B10B", "B11", "B12", "B13", "B14", "B15", "B16", "B17", "B18"]
    _assert(
        report.get("synthesized_stages") == expected_stages,
        "synthesized_stages mismatch",
    )
    synthesized = report.get("synthesized_evidence", {})
    for stage in expected_stages:
        _assert(stage in synthesized, f"synthesized_evidence missing {stage}")

    # Algorithm concept.
    concept = report.get("algorithm_concept_block", {})
    _assert(
        concept.get("algorithm_concept") == ALGORITHM_CONCEPT,
        "algorithm_concept mismatch",
    )
    for key in ("inputs", "outputs_actions", "core_principles"):
        _assert(
            isinstance(concept.get(key), list) and len(concept[key]) > 0,
            f"algorithm_concept_block.{key} must be a non-empty list",
        )

    # Forbidden public scan clean.
    violations = _forbidden_scan(report)
    _assert(
        not violations,
        "forbidden public scan found violations: " + ", ".join(violations[:5]),
    )

    # Drift guard hash matches.
    embedded = report.get("report_content_sha256")
    recomputed = _canonical_content_hash(report)
    _assert(
        embedded == recomputed,
        f"report_content_sha256 drift: embedded={embedded!r} recomputed={recomputed!r}",
    )


def _run_self_test() -> int:
    print("[b19] running self-test (read-only) ...")

    # Build the expected report in memory.
    expected = build_report(generated_at="1970-01-01T00:00:00+00:00")
    _verify_report_invariants(expected)

    # External pin checks.
    _verify_docs_links_exist()
    _verify_synthesized_source_artifacts_pinned()

    # On-disk drift check: the canonical report must match the in-memory
    # build byte-for-byte (modulo generated_at).
    if not REPORT_PATH.is_file():
        raise AssertionError(
            f"B19 report artifact missing: {REPORT_PATH.relative_to(REPO_ROOT)}"
        )
    on_disk = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    _verify_report_invariants(on_disk)

    # Content hash must match (drift guard).
    _assert(
        on_disk.get("report_content_sha256")
        == expected.get("report_content_sha256"),
        "on-disk report content hash drifts from in-memory build",
    )
    _assert(
        on_disk.get("schema_version") == SCHEMA_VERSION,
        "on-disk schema_version mismatch",
    )
    _assert(
        on_disk.get("claim_level") == CLAIM_LEVEL,
        "on-disk claim_level mismatch",
    )

    print("[b19] self-test PASSED")
    print(f"  schema_version: {SCHEMA_VERSION}")
    print(f"  claim_level: {CLAIM_LEVEL}")
    print(f"  algorithm_concept: {ALGORITHM_CONCEPT}")
    print(f"  synthesized_stages: {len(expected['synthesized_stages'])}")
    print(
        "  b11 deltas (balanced_v1 vs p25): "
        + ", ".join(
            f"{k}={v}" for k, v in B11_DELTAS_BALANCED_V1_VS_P25.items()
        )
    )
    print("  all no-promotion flags: False")
    print("  forbidden public scan: clean")
    print("  docs links: exist")
    print("  report drift guard: matched")
    return 0


def _regenerate_artifacts() -> int:
    print("[b19] regenerating checked-in artifacts ...")
    report = build_report()
    _verify_report_invariants(report)
    _verify_docs_links_exist()
    _verify_synthesized_source_artifacts_pinned()
    _write_json(REPORT_PATH, report)
    print(f"  wrote {REPORT_PATH.relative_to(REPO_ROOT)}")
    # Re-run the self-test to confirm on-disk matches in-memory.
    rc = _run_self_test()
    return rc


def _input_stub(out_path: Path) -> int:
    if out_path.exists():
        # Refuse to overwrite anything inside the canonical artifact dir.
        try:
            out_path.relative_to(ARTIFACT_DIR)
            print(
                "[b19] --input stub refuses to write inside "
                f"{ARTIFACT_DIR.relative_to(REPO_ROOT)}"
            )
            return 2
        except ValueError:
            pass
    stub = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "claim_level": CLAIM_LEVEL,
        "is_synthesis_only": True,
        "is_new_experiment": False,
        "ran_providers": False,
        "new_provider_calls": 0,
        "aggregate_only_public_artifact": True,
        "candidate_not_fact": True,
        "not_evidence": True,
        "promotion_ready": False,
        "default_should_change": False,
        "evidencecore_semantics_changed": False,
        "verdict": "not_implemented",
        "verdict_reason": (
            "B19 is synthesis-only. There is no per-record input path. "
            "Use --self-test (read-only) or --regenerate-artifacts."
        ),
    }
    _write_json(out_path, stub)
    print(f"[b19] --input stub wrote {out_path} (verdict=not_implemented)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="B19 theoretical synthesis of B10-B18."
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Read-only: verify required sections, no-promotion flags, "
        "B11 deltas, forbidden scan, docs links, and drift guard.",
    )
    parser.add_argument(
        "--regenerate-artifacts",
        action="store_true",
        help="Re-write the canonical B19 synthesis report JSON and re-run "
        "the self-test.",
    )
    parser.add_argument(
        "--input",
        metavar="PATH",
        help="Stub path. B19 is synthesis-only; --input is always "
        "not_implemented. Requires --out.",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help="Output path for --input stub.",
    )
    args = parser.parse_args(argv)

    if args.regenerate_artifacts:
        return _regenerate_artifacts()

    if args.input is not None:
        if not args.out:
            parser.error("--input requires --out")
        return _input_stub(Path(args.out))

    # Default and --self-test both run the read-only self-test.
    return _run_self_test()


if __name__ == "__main__":
    sys.exit(main())
