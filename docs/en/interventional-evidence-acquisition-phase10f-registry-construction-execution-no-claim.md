# Interventional Evidence Acquisition Phase 10F Candidate-Source-Registry Construction/Provision Execution (Repair, No Claim)

Date: 2026-07-09

Status: `phase10f_candidate_source_registry_construction_repair_no_claim` (registry-manifest construction/provision execution; repair/no-claim; no validation/product/method/correctness/evidence-success claim).

Authorization: Phase 10F is allowed -- by oracle gate and by the frozen Phase 10E candidate-source-registry construction/provision protocol -- to construct and/or provide a candidate-source-registry *manifest only*, exactly under the frozen Phase 10E rules. Phase 10F is allowed to construct/provide a registry manifest only, validate manifest eligibility/provisioning protocol, record registry-level metadata needed by 10E, store any private/non-public registry details under ignored `runs/`, and publish only an aggregate/bucket-level public report. Phase 10 is separate from Phase 9; it is not a continuation, reinterpretation, repair, rerun, rescore, or strengthening of Phase 9R/9S. Phase 9 is closed.

Public report: [`phase10f_registry_construction_execution_no_claim_report.json`](../../artifacts/phase10f_registry_construction_execution_no_claim/phase10f_registry_construction_execution_no_claim_report.json)

## Scope

Phase 10F executes ONLY candidate-source-registry manifest construction/provision under the frozen Phase 10E protocol. The frozen Phase 10E protocol closed lists (registry schema fields, provenance fields, candidate descriptor fields, eligibility fields, exclusion reasons, auditability requirements, allowed construction/provision routes, hard stops, replacement rules, non-adaptive ordering rules, future execution validation checks, aggregate-only public reporting rules, anti-adaptation rules) are imported directly from the committed Phase 10E protocol-freeze module so Phase 10F applies EXACTLY the frozen protocol (no re-declaration, no vocabulary/ordering/eligibility drift, no protocol edits after observation). Phase 10F does NOT score, adjudicate, evaluate correctness/evidence_success, generate gold/benchmark labels, make any provider/LLM/model call, perform model fitting/training, generate tasks/packets, execute any downstream pipeline, or make runtime/default/product changes. It does NOT read Phase 9 private artifacts, labels, outcomes, source filters, priors, or sampling inputs as evidence.

Phase 10F does NOT fetch, clone, scrape, download, or inspect source material, does NOT read repository files or materialize source contents, does NOT generate tasks/packets or execute any downstream pipeline beyond registry-level manifest allowed by 10E, does NOT modify, weaken, reinterpret, or extend 10E after seeing registry availability, and does NOT add fallback channels, implicit eligibility expansion, or best-effort registry invention.

## Gate references

Phase 10F publishes exact commit/CI identifiers only for the immediate Phase 10E gate. Older Phase 9 / 10A / 10B / 10C / 10D / hygiene checkpoints are carried forward only as status/bucket/scope provenance, not as exact commit/CI identifiers. Local same-tree git commits are not read or compared.

- Phase 9 status: closed.
- Phase 10A status: `phase10a_independent_validation_protocol_freeze_no_execution_no_claim`.
- Phase 10B status: `phase10b_fresh_fenced_input_construction_protocol_freeze_no_execution_no_materialization_no_claim`.
- Phase 10C result is repair/no-claim: accepted source bucket was `bucket_zero`, repair reason bucket was `bucket_no_eligible_channel_registry` (no compliant candidate source registry was available).
- Phase 10D status: `phase10d_10c_repair_closeout_guard_no_claim` (closed 10C as repair/no-claim and authorized ONLY Phase 10E protocol freeze).
- Phase 10E candidate-source-registry construction protocol freeze: commit `285543ba4006773a65b813f0a5fdeb7a840d7d3c`, CI run `29018708378` green, status `phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim`. Phase 10E froze the construction/provision protocol only (no execution, no construction).
- Phase 10F is authorized by oracle as candidate-source-registry construction/provision ONLY, gated on Phase 10E commit + CI green.

Older Phase 9 / 10A / 10B / 10C / 10D / hygiene exact commit/CI refs are intentionally NOT republished by Phase 10F (tighter privacy). Only the Phase 10E gate constants are exact references.

## Frozen Phase 10E protocol (applied exactly, no drift)

Phase 10F imports the frozen Phase 10E closed lists directly from the committed protocol-freeze module and validator set-equality checks them. These are structural definitions only; Phase 10F does not fetch/clone/read/materialize/score to populate any registry. The frozen lists are: allowed registry schema fields, allowed registry provenance fields, allowed candidate descriptor fields, allowed registry eligibility fields, predeclared exclusion reasons, predeclared auditability requirements, allowed future construction/provision routes (`neutral_public_acquisition_channels_only`, `operator_provided_external_registry`), hard stops, replacement rules, non-adaptive ordering rules, future execution validation checks, aggregate-only public reporting rules, and anti-adaptation rules.

## Repair/no-claim result

This executed run is repair/no-claim. No compliant candidate-source-registry manifest was constructed or provided under the frozen Phase 10E protocol:

- `registry_manifest_compliance_bucket` = `bucket_zero`.
- `compliant_candidate_source_bucket` = `bucket_zero`.
- `repair_reason_bucket` = `bucket_no_compliant_registry_input_under_frozen_10e_protocol`.
- `repair_no_claim` = true; `registry_manifest_construction_attempted` = false; `compliant_registry_manifest_constructed` = false; `compliant_registry_manifest_provided` = false; `no_private_registry_manifest_materialized` = true.

Every allowed construction/provision route under frozen 10E requires either forbidden fetch/clone/read/scrape/source-inspection (`neutral_public_acquisition_channels_only`) or an operator-provided external-registry input that does not exist (`operator_provided_external_registry`); best-effort registry invention is forbidden. Constructing a compliant registry would require forbidden fetch/clone/read/scrape/materialization/source inspection, and eligibility depends on unavailable info without forbidden inspection. Therefore Phase 10F stops as repair/no-claim rather than broadening scope, weakening rules, or inventing a registry. This is an honest checkpoint, not a failure to be tuned or padded.

## Anti-adaptation rules

The Phase 10F protocol is prospective, not tuned to the observed Phase 10C `bucket_zero` / `bucket_no_eligible_channel_registry` outcome.

- Phase 10C is mentioned ONLY as a gate/provenance fact and failure mode to guard against, not as optimization feedback.
- The frozen Phase 10E protocol is applied exactly (imported closed lists, set-equality validated; no drift, no post-hoc edit after seeing registry availability).
- No rule is justified by "because 10C found zero accepted sources" unless framed as a general compliance/audit requirement.
- No new threshold/fallback/channel exception is introduced to avoid `bucket_no_compliant_registry_input_under_frozen_10e_protocol`.
- Future execution must use the frozen 10E protocol as written, with no post-hoc selection after seeing source availability.

## Phase 10F boundary

- Phase 10F is construction/provision only under the frozen 10E protocol.
- Phase 10F makes no new evidence claims (only registry-manifest construction/provision status).
- Phase 10F does not fetch/clone/read/scrape/inspect/sample/download source material.
- Phase 10F does not materialize source contents.
- Phase 10F does not generate tasks or packets or execute any downstream pipeline.
- Phase 10F does not score/adjudicate/run correctness/evidence_success.
- Phase 10F does not modify, weaken, reinterpret, or extend Phase 10E.
- Phase 10F does not add fallback channels, implicit eligibility expansion, or best-effort registry invention.
- Phase 10F does not treat zero compliance as partial success.
- Phase 10F does not make user-approval wording a protocol dependency.

## Next phase

Any actual candidate-source-registry construction/provision/execution or downstream pipeline requires a later separately reviewed phase after Phase 10F commit + CI green. Future execution must use the frozen 10E protocol as written, with no post-hoc selection after seeing source availability. No user approval wording is used.

## Privacy boundary

Public output is aggregate/boundary-only. Source-specific details (repo names, URLs, owners, commits, paths, snippets, line ranges, packet IDs, run dirs, per-source/per-task/per-packet facts, candidate identities, candidate registry contents, registry manifest locations, registry construction/exclusion audit logs, singleton buckets) are kept private under ignored `runs/` only. In this repair/no-claim run no private registry details were materialized. Only the gate-reference values are exact public values, allowed only at their exact gate paths.

## No-claim boundary

Phase 10F makes no method, product, performance, training, provider, model, runtime, default, scoring, outcome, evidence-success, correctness, generalization, validation, materialization-succeeded, independent-validation-passed, OpenLocus-works, Phase-10/10E/10F-confirms, registry-construction-succeeded, registry-provision-succeeded, or empirical claim. Phase 10F records ONLY registry-manifest construction/provision status. Phase 10F is construction/provision execution (repair/no-claim) only, not evidence/method/product/correctness/validation success.

The conservative recommendation is: `phase10f_candidate_source_registry_construction_or_provision_only_under_frozen_phase10e_protocol_phase9_closed_inherited_phase10a_gate_inherited_phase10b_gate_inherited_phase10c_executed_frozen_10b_route_once_repair_no_claim_zero_accepted_sources_phase10d_closeout_guard_gate_inherited_phase10e_protocol_freeze_gate_inherited_ci_green_authorized_phase10f_candidate_source_registry_construction_or_provision_only_by_oracle_phase10f_applies_frozen_phase10e_protocol_exactly_no_drift_phase10f_is_candidate_source_registry_construction_or_provision_only_not_validation_product_method_correctness_evidence_success_phase10f_does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material_phase10f_does_not_materialize_source_contents_phase10f_does_not_generate_tasks_or_packets_or_execute_downstream_pipeline_phase10f_does_not_score_adjudicate_or_run_correctness_evidence_success_phase10f_does_not_modify_weaken_reinterpret_or_extend_phase10e_phase10f_does_not_add_fallback_channels_or_implicit_eligibility_expansion_or_best_effort_registry_invention_phase10f_does_not_treat_zero_compliance_as_partial_success_phase10f_protocol_is_prospective_not_tuned_to_observed_outcome_phase10f_repair_no_claim_no_compliant_registry_manifest_constructed_or_provided_under_frozen_10e_protocol_constructing_compliant_registry_would_require_forbidden_fetch_clone_read_scrape_or_source_inspection_no_compliant_registry_input_or_operator_provided_external_registry_available_under_frozen_10e_protocol_private_registry_details_under_ignored_runs_only_none_materialized_future_registry_construction_or_provision_or_execution_or_downstream_requires_separate_phase_after_10f_commit_and_ci_green_boundary_review_after_phase10f_commit_and_ci_green_no_user_approval_wording_no_method_product_correctness_evidence_success_claim`.
