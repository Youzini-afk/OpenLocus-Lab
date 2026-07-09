# Interventional Evidence Acquisition Phase 10B Fresh/Fenced Input-Construction Protocol Freeze (No Execution, No Materialization, No Claim)

Date: 2026-07-09

Status: `phase10b_fresh_fenced_input_construction_protocol_freeze_no_execution_no_materialization_no_claim`

Authorization: Phase 10B is a docs/report/validator-only protocol-freeze checkpoint for fresh/fenced input construction for the NEW independent Phase 10 validation line. Phase 10 is separate from Phase 9; it is not a continuation, reinterpretation, repair, rerun, rescore, or strengthening of Phase 9R/9S. Phase 10B freezes the concrete input-construction protocol without instantiating any of it.

Public report: [`phase10b_input_protocol_freeze_no_execution_no_materialization_no_claim_report.json`](../../artifacts/phase10b_input_protocol_freeze_no_execution_no_materialization_no_claim/phase10b_input_protocol_freeze_no_execution_no_materialization_no_claim_report.json)

## Scope

Phase 10B is docs/report/validator only. It does not execute, discover, fetch, clone, sample, generate real packets/tasks, score, adjudicate, evaluate correctness/evidence_success, or read private/source artifacts. It does not fetch, clone, read, or materialize any repository or source; does not read ignored `runs/`, any private Phase 9 artifacts, or any private Phase 10A artifacts; does not discover public sources; does not read source code from candidate validation targets; does not generate tasks, draw samples, or generate real packets; does not make any provider/LLM/model call; does not introduce metrics/thresholds/rates/counts beyond coarse fixed status/boundary fields; and does not use low-resource autonomy to start empirical work.

## Gate references

Phase 10B is gated on Phase 9 closed at commit `1d71f6a`, CI run `28999245247`, CI success, Phase 9 closed; and Phase 10A committed at `67e8d984601d82a2a97992bb83fda06b09e06be0`, CI run `29002587099`, CI success, Phase 10A status `phase10a_independent_validation_protocol_freeze_no_execution_no_claim`. These are the only exact public gate references published by Phase 10B. Older Phase 9 exact commit/CI refs are intentionally NOT republished by Phase 10B (tighter privacy). Local same-tree git commits are not read or compared; only the gate constants are exact references.

## Frozen input-construction protocol (defined only, not instantiated)

Phase 10B freezes the following concrete input-construction rules for future Phase 10C, without instantiating any of them:

- **Source eligibility rules**: publicly accessible without authentication, source archive materializable before use, declared or publicly auditable license present, default branch or equivalent revision resolvable, in-scope language or file mix detectable from public metadata, not Phase 9 artifact or Phase 9 derived material, not private prior phase or manual named seed material.
- **Freshness/fencing definition**: inputs must be fresh (not reused from Phase 9), fenced from Phase 9 private artifacts, independent replication packet generation required, no Phase 9 priors/sources/labels/outcomes as input, freshness verified before any sampling or packet generation, fencing violation is a hard stop.
- **Independence-from-Phase-9 checks**: Phase 9 artifacts cannot be used as validation evidence, Phase 9 source filters/priors cannot be reused, Phase 9 labels/outcomes cannot be reused as inputs, Phase 9 sampling inputs cannot be reused, clean-room operator must not use memory of Phase 9 private material.
- **Deterministic source ordering/selection rules**: predeclared seed label (version only, randomness forbidden), stable channel then stable public metadata order, predeclared deterministic sort keys, replacement before sampling only, replacement reasons limited to availability or eligibility, performance-based replacement forbidden, no actual sampling draw in Phase 10B.
- **Caps and abort limits**: structural protocol caps (candidate inspection cap total 48, accepted source target cap 12, accepted source minimum cap 8, per-channel cap 16) are coarse fixed boundary fields, NOT success metrics. Abort on quota/ordering drift, eligibility drift, fencing violation, Phase 9 contamination, or privacy violation.
- **Private/public artifact split**: public output aggregate or boundary only, private material under ignored `runs/` only, no repo/source/url/owner/commit beyond whitelisted gate refs, no paths/snippets/line ranges/identifiers/run locations, no per-source/per-task/per-packet facts, no singleton buckets.
- **Independent replication packet schema**: schema definition only, no packets generated in Phase 10B. Packets must contain public source identity and fenced acquisition metadata only, must not contain Phase 9 artifacts or private rows/observables, must be independently generated in future Phase 10C, and must support aggregate-only public reporting.
- **Privacy scanner rules**: reject private-shaped keys/values, singleton buckets, claim wording, placeholder wording, user-approval wording, exact count fields, long unapproved numeric run IDs. Gate exact values allowed only at exact gate paths.

## Future 10C handoff gates (defined only)

Phase 10C requires: Phase 10B commit, Phase 10B CI green, a separate boundary review after Phase 10B commit + CI green before Phase 10C, and an explicit execution and materialization boundary. Phase 10B does NOT authorize Phase 10C execution. Actual discovery/fetch/materialization is earliest possible in Phase 10C.

## No-claim boundary

Phase 10B makes no method, product, performance, training, provider, model, runtime, default, scoring, outcome, evidence-success, correctness, generalization, or validation claim. Phase 10B is a protocol-freeze checkpoint only, not evidence/method/product/correctness/validation success.

The conservative recommendation is: `phase10b_fresh_fenced_input_construction_protocol_freeze_only_for_new_independent_validation_line_phase9_closed_at_recorded_commit_and_ci_phase10a_gate_passed_at_recorded_commit_and_ci_phase10b_makes_no_evidence_method_product_performance_correctness_or_generalization_claims_phase10b_does_not_execute_discover_fetch_clone_sample_or_materialize_phase10b_does_not_read_private_or_source_artifacts_phase10b_does_not_reuse_phase9_artifacts_as_validation_evidence_future_input_construction_requires_fresh_fenced_inputs_independent_from_phase9_source_eligibility_freshness_fencing_and_deterministic_ordering_rules_frozen_caps_and_abort_limits_frozen_as_structural_protocol_limits_not_success_metrics_replication_packet_schema_defined_only_no_packets_generated_in_phase10b_private_public_artifact_split_frozen_aggregate_only_public_reporting_privacy_scanner_rules_frozen_phase10c_requires_separate_boundary_review_after_phase10b_commit_and_ci_green_no_private_reads_no_source_reads_no_discovery_no_fetch_clone_no_task_generation_no_sampling_draw_no_packet_generation_no_scoring_adjudication_correctness_or_evidence_success_evaluation_no_metrics_thresholds_rates_counts_beyond_coarse_fixed_status_boundary_fields_no_product_method_performance_correctness_generalization_claim`.
