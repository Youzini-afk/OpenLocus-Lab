# Interventional Evidence Acquisition Phase 10E Candidate-Source-Registry Construction Protocol Freeze (No Execution, No Claim)

Date: 2026-07-09

Status: `phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim` (protocol-freeze only, no execution, no claim).

Authorization: Phase 10E is a PROTOCOL-FREEZE-ONLY checkpoint defining how a compliant candidate source registry MAY be constructed or provided in a LATER, separately reviewed phase. Phase 10E itself does NOT construct, fetch, clone, read, select, filter, materialize, populate, or execute any registry or source candidate now. Phase 10 is separate from Phase 9; it is not a continuation, reinterpretation, repair, rerun, rescore, or strengthening of Phase 9R/9S. Phase 9 is closed.

Public report: [`phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim_report.json`](../../artifacts/phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim/phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim_report.json)

## Scope

Phase 10E defines ONLY how a compliant future candidate source registry is allowed to be constructed/provided. It defines required registry manifest/schema fields, provenance fields, eligibility fields, exclusion reasons, auditability requirements, and aggregate-only public reporting rules. It defines allowed future construction/provision routes without executing them. It defines hard stops, replacement rules, non-adaptive ordering rules, and validation checks for a future execution phase. Phase 10E makes no empirical, validation, correctness, scoring, product, method, performance, or generalization claims. Any actual registry construction/provision/execution requires a later separately reviewed phase after Phase 10E commit + CI green.

Phase 10E does NOT construct/edit/select/filter/provide/materialize/populate a candidate source registry, does NOT fetch/clone/read/scrape/inspect/sample source repositories/materials, does NOT rerun Phase 10C materialization or modify the frozen Phase 10B protocol, does NOT score/adjudicate/evaluate correctness/compute evidence_success/generate metrics/create validation evidence, does NOT add thresholds/fallbacks/exceptions/channel-specific rescue paths, does NOT treat `bucket_zero` as partial success, does NOT use Phase 9 artifacts as validation evidence, does NOT change runtime/default behavior, and does NOT make user-approval wording a protocol dependency.

## Gate references

Phase 10E publishes exact commit/CI identifiers only for the immediate Phase 10D gate. Older Phase 9 / 10A / 10B / 10C / hygiene checkpoints are carried forward only as status/bucket/scope provenance, not as exact commit/CI identifiers. Local same-tree git commits are not read or compared.

- Phase 9 status: closed.
- Phase 10A status: `phase10a_independent_validation_protocol_freeze_no_execution_no_claim`.
- Phase 10B status: `phase10b_fresh_fenced_input_construction_protocol_freeze_no_execution_no_materialization_no_claim`.
- Phase 10C result is repair/no-claim: accepted source bucket was `bucket_zero`, repair reason bucket was `bucket_no_eligible_channel_registry` (no compliant candidate source registry was available).
- Separate CI hygiene scope: CI infrastructure only, NOT part of empirical evidence/result.
- Phase 10D closeout/guard commit `acaa189`, CI run `29016304662` green, status `phase10d_10c_repair_closeout_guard_no_claim`. Phase 10D closed 10C as repair/no-claim and authorized ONLY Phase 10E candidate-source-registry construction protocol freeze (protocol freeze only, not construction/execution).

Older Phase 9 / 10A / 10B / 10C / hygiene exact commit/CI refs are intentionally NOT republished by Phase 10E (tighter privacy). Only the Phase 10D gate constants are exact references.

## Frozen candidate-source-registry construction protocol

The following are STRUCTURAL protocol-freeze definitions only. Phase 10E does not execute, construct, fetch, clone, read, select, filter, materialize, populate, score, adjudicate, or evaluate any registry or source candidate.

- **Allowed registry schema fields**: `registry_provenance`, `registry_construction_route`, `registry_source_channel_classes`, `registry_deterministic_order_rule`, `registry_minimum_eligible_sources`, `registry_caps`, `registry_no_phase9_private_reuse`, `registry_operator_clean_room_attestation`, `registry_construction_audit_log`, `registry_exclusion_audit_log`, `registry_replacement_audit_log`, `registry_aggregate_only_public_projection`.
- **Allowed registry provenance fields**: `registry_construction_route`, `registry_source_channel_classes`, `registry_deterministic_order_rule`, `registry_no_phase9_private_reuse`, `registry_operator_clean_room_attestation`.
- **Allowed candidate descriptor fields**: `normalized_public_project_identity`, `default_branch_name`, `public_metadata_stable_rank`, `channel_local_index`, `license_precheck`, `access_precheck`, `default_branch_precheck`, `currentness_precheck`, `content_integrity_precheck`.
- **Allowed registry eligibility fields**: `license_precheck`, `access_precheck`, `default_branch_precheck`, `currentness_precheck`, `content_integrity_precheck`.
- **Predeclared exclusion reasons**: `license_precheck_failed`, `access_precheck_failed`, `default_branch_precheck_failed`, `currentness_precheck_failed`, `content_integrity_precheck_failed`, `candidate_below_minimum_eligibility`, `candidate_duplicate_identity`, `candidate_not_from_allowed_channel_class`.
- **Predeclared auditability requirements**: `registry_construction_audit_log_required`, `registry_exclusion_audit_log_required`, `registry_replacement_audit_log_required`, `registry_deterministic_order_verified`, `registry_no_phase9_private_reuse_verified`, `registry_aggregate_only_public_projection_verified`.
- **Allowed future construction/provision routes**: `neutral_public_acquisition_channels_only`, `operator_provided_external_registry`.
- **Hard stops**: nonzero Phase 9 private reuse stops construction; adaptive tuning to observed outcome stops construction; post-hoc selection after source availability stops construction; nonzero randomness in ordering or selection stops construction; registry construction after observation stops construction; treatment of zero accepted as partial success stops construction.
- **Replacement rules**: replacement before labels/outcomes/scoring only; replacement only from frozen eligibility pool; replacement not based on observed outcome; replacement deterministic no randomness.
- **Non-adaptive ordering rules**: frozen channel order then frozen public metadata sort keys; no random shuffle; no post-hoc reordering after observation; deterministic sort keys predeclared.
- **Future execution validation checks**: `registry_schema_fields_valid`, `registry_provenance_fields_complete`, `registry_eligibility_fields_present`, `registry_exclusion_reasons_in_predeclared_set`, `registry_audit_log_complete`, `registry_deterministic_order_verified`, `registry_minimum_eligible_sources_met_or_repair`, `registry_no_phase9_private_reuse_verified`, `registry_aggregate_only_public_projection_verified`.
- **Aggregate-only public reporting rules**: registry contents not public; registry candidate details not public; only aggregate buckets public; exclusion reasons aggregate only; no per-source/per-task public facts.

## Anti-adaptation rules

The Phase 10E protocol is frozen as a PROSPECTIVE construction/provision rule, not tuned to repair the observed Phase 10C `bucket_zero` / `bucket_no_eligible_channel_registry` outcome.

- Phase 10C is mentioned ONLY as a gate/provenance fact and failure mode to guard against, not as optimization feedback.
- Candidate source eligibility, ordering, replacement, exclusion, and audit rules are deterministic and predeclared.
- No rule is justified by "because 10C found zero accepted sources" unless framed as a general compliance/audit requirement.
- No new threshold/fallback/channel exception is introduced specifically to avoid `bucket_no_eligible_channel_registry`.
- Future execution must use the frozen 10E protocol as written, with no post-hoc selection after seeing source availability.

## Phase 10E boundary

- Phase 10E performs no execution.
- Phase 10E makes no new evidence claims.
- Phase 10E does not construct/edit/select/filter/supply/materialize/populate a candidate registry.
- Phase 10E does not fetch/clone/read/scrape/inspect/sample source material.
- Phase 10E does not rerun Phase 10C materialization.
- Phase 10E does not change the frozen Phase 10B protocol.
- Phase 10E does not score/adjudicate/run correctness/evidence_success.
- Phase 10E does not add thresholds/fallbacks/exceptions/channel-specific rescue paths.
- Phase 10E does not treat `bucket_zero` as partial success.
- Phase 10E does not make user-approval wording a protocol dependency.

## Next phase

Any actual candidate-source-registry construction/provision/execution requires a later separately reviewed phase after Phase 10E commit + CI green. Future execution must use the frozen 10E protocol as written, with no post-hoc selection after seeing source availability. No user approval wording is used.

## Privacy boundary

Public output is aggregate/boundary-only. Source-specific details (repo names, URLs, owners, commits, paths, snippets, line ranges, packet IDs, run dirs, per-source/per-task/per-packet facts, candidate identities, candidate registry contents, registry manifest locations, registry construction/exclusion audit logs, singleton buckets) are kept private under ignored `runs/` only. Only the gate-reference values are exact public values, allowed only at their exact gate paths.

## No-claim boundary

Phase 10E makes no method, product, performance, training, provider, model, runtime, default, scoring, outcome, evidence-success, correctness, generalization, validation, materialization-succeeded, independent-validation-passed, OpenLocus-works, Phase-10/10C/10D/10E-confirms, registry-construction-succeeded, registry-provision-succeeded, or empirical claim. Phase 10E is protocol-freeze only, not evidence/method/product/correctness/validation success.

The conservative recommendation is: `phase10e_candidate_source_registry_construction_protocol_freeze_only_phase9_closed_inherited_phase10a_gate_inherited_phase10b_gate_inherited_phase10c_executed_frozen_10b_route_once_repair_no_claim_zero_accepted_sources_phase10d_closeout_guard_gate_inherited_authorized_10e_protocol_freeze_only_phase10e_is_protocol_freeze_only_for_future_registry_construction_phase10e_does_not_construct_edit_select_filter_supply_materialize_or_populate_candidate_registry_phase10e_does_not_fetch_clone_read_scrape_inspect_or_sample_source_material_phase10e_does_not_rerun_10c_materialization_or_change_frozen_10b_protocol_phase10e_does_not_score_adjudicate_or_run_correctness_evidence_success_phase10e_does_not_add_thresholds_fallbacks_exceptions_or_channel_rescue_paths_phase10e_does_not_treat_bucket_zero_as_partial_success_phase10e_protocol_is_prospective_not_tuned_to_10c_zero_outcome_phase10e_10c_referenced_only_as_gate_and_failure_mode_not_optimization_feedback_candidate_eligibility_ordering_replacement_exclusion_audit_deterministic_and_predeclared_no_threshold_fallback_or_channel_exception_for_observed_repair_reason_future_execution_uses_frozen_10e_protocol_no_post_hoc_selection_after_source_availability_hygiene_commit_is_ci_infrastructure_only_not_empirical_evidence_future_registry_construction_or_provision_or_execution_requires_separate_phase_after_10e_commit_and_ci_green_boundary_review_after_phase10e_commit_and_ci_green_no_user_approval_wording_no_method_product_correctness_evidence_success_claim`.
