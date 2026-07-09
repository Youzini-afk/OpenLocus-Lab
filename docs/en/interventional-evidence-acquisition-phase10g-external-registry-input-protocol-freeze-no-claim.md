# Interventional Evidence Acquisition Phase 10G External Registry-Input Protocol Freeze + Phase 10F Closeout (No Execution, No Claim)

Date: 2026-07-09

Status: `phase10g_external_registry_input_protocol_freeze_no_execution_no_claim` (docs-only closeout + external-input protocol freeze; no execution, no claim; no validation/product/method/correctness/evidence-success claim).

Authorization: Phase 10G is allowed — by oracle gate — as a DOCS-ONLY CLOSEOUT plus EXTERNAL-INPUT PROTOCOL-FREEZE checkpoint only. It closes Phase 10F cleanly as repair/no-claim under the frozen Phase 10E candidate-source-registry construction/provision protocol, adds/clarifies guard language that no compliant registry source exists and no fallback path is authorized, and defines — as metadata/specification only — what a future compliant operator-provided external registry-input package must contain. Phase 10G performs NO execution. Phase 10 is separate from Phase 9; it is not a continuation, reinterpretation, repair, rerun, rescore, or strengthening of Phase 9R/9S. Phase 9 is closed.

Public report: [`phase10g_external_registry_input_protocol_freeze_no_execution_no_claim_report.json`](../../artifacts/phase10g_external_registry_input_protocol_freeze_no_execution_no_claim/phase10g_external_registry_input_protocol_freeze_no_execution_no_claim_report.json)

## Scope

Phase 10G is docs/report/validator only. It executes nothing. It closes Phase 10F as repair/no-claim under the frozen Phase 10E rules, freezes a future external registry-input package contract (metadata/specification only), and states that execution remains blocked until a compliant external package matching the 10G contract exists. The frozen Phase 10E protocol closed lists (registry schema fields, provenance fields, candidate descriptor fields, eligibility fields, exclusion reasons, auditability requirements, allowed construction/provision routes, hard stops, replacement rules, non-adaptive ordering rules, future execution validation checks, aggregate-only public reporting rules, anti-adaptation rules) are imported directly from the committed Phase 10E protocol-freeze module so Phase 10G references EXACTLY the frozen protocol (no re-declaration, no vocabulary/ordering/eligibility drift, no protocol edits after observation); the validator set-equality checks them against the imported constants. Phase 10G does NOT score, adjudicate, evaluate correctness/evidence_success, generate gold/benchmark labels, make any provider/LLM/model call, perform model fitting/training, generate tasks/packets, execute any downstream pipeline, or make runtime/default/product changes. It does NOT read Phase 9 private artifacts, labels, outcomes, source filters, priors, or sampling inputs as evidence.

Phase 10G does NOT fetch, clone, scrape, download, browse, or inspect source material, does NOT read repository files or materialize source contents, does NOT inspect public registries, does NOT infer candidates from memory, docs, URLs, package indexes, GitHub, search, or prior non-compliant sources, does NOT construct or validate a registry manifest in 10G, does NOT construct or intake-validate an external-input package in 10G, does NOT treat the absent external package as permission to create one, does NOT modify, weaken, reinterpret, or extend Phase 10E or Phase 10F, and does NOT add fallback channels, implicit eligibility expansion, or best-effort registry invention.

## Gate references

Phase 10G publishes exact commit/CI identifiers only for the immediate Phase 10F gate it closes. Older Phase 9 / 10A / 10B / 10C / 10D / 10E / hygiene checkpoints are carried forward only as status/bucket/scope provenance, not as exact commit/CI identifiers. Local same-tree git commits are not read or compared.

- Phase 9 status: closed.
- Phase 10A status: `phase10a_independent_validation_protocol_freeze_no_execution_no_claim`.
- Phase 10B status: `phase10b_fresh_fenced_input_construction_protocol_freeze_no_execution_no_materialization_no_claim`.
- Phase 10C result is repair/no-claim: accepted source bucket was `bucket_zero`, repair reason bucket was `bucket_no_eligible_channel_registry` (no compliant candidate source registry was available).
- Phase 10D status: `phase10d_10c_repair_closeout_guard_no_claim` (closed 10C as repair/no-claim and authorized ONLY Phase 10E protocol freeze).
- Phase 10E status: `phase10e_candidate_source_registry_protocol_freeze_no_execution_no_claim` (protocol-freeze only for future registry construction; status carried forward, exact commit/CI not republished by 10G).
- Phase 10F candidate-source-registry construction/provision execution: commit `969f8acde65a27ab3b512db269150d814483d49c`, CI run `29022117575` green, status `phase10f_candidate_source_registry_construction_repair_no_claim`. Phase 10F is repair/no-claim: no compliant registry manifest was constructed or provided under the frozen Phase 10E protocol; no compliant registry input/source exists; no fallback authorized; no fetch/clone/source read/materialization/task generation/scoring/adjudication/correctness/evidence_success.
- Phase 10G is authorized by oracle as docs-only closeout + external registry-input protocol freeze ONLY, gated on Phase 10F commit + CI green.

Older Phase 9 / 10A / 10B / 10C / 10D / 10E / hygiene exact commit/CI refs are intentionally NOT republished by Phase 10G (tighter privacy). Only the Phase 10F gate constants are exact references.

## Frozen Phase 10E protocol (inherited, applied exactly, no drift)

Phase 10G imports the frozen Phase 10E closed lists directly from the committed protocol-freeze module and the validator set-equality checks them. These are structural definitions only; Phase 10G does not fetch/clone/read/materialize/score to populate any registry. The frozen lists are: allowed registry schema fields, allowed registry provenance fields, allowed candidate descriptor fields, allowed registry eligibility fields, predeclared exclusion reasons, predeclared auditability requirements, allowed future construction/provision routes (`neutral_public_acquisition_channels_only`, `operator_provided_external_registry`), hard stops, replacement rules, non-adaptive ordering rules, future execution validation checks, aggregate-only public reporting rules, and anti-adaptation rules.

## Phase 10F closeout (repair/no-claim)

Phase 10G closes Phase 10F cleanly as repair/no-claim under the frozen Phase 10E protocol:

- `phase10f_closed_as_repair_no_claim` = true.
- `phase10f_closeout_bucket` = `bucket_phase10f_closed_repair_no_claim_under_frozen_10e_protocol`.
- `phase10f_no_compliant_registry_manifest_constructed_or_provided` = true.
- `phase10f_no_compliant_registry_input_or_source_exists` = true.
- `phase10f_no_fallback_authorized` = true.
- `phase10f_repair_no_claim_under_frozen_10e_protocol` = true.

Every allowed construction/provision route under frozen 10E requires either forbidden fetch/clone/read/scrape/source-inspection (`neutral_public_acquisition_channels_only`) or an operator-provided external-registry input that does not exist (`operator_provided_external_registry`); best-effort registry invention is forbidden. Constructing a compliant registry would require forbidden fetch/clone/read/scrape/materialization/source inspection. Therefore Phase 10F stops as repair/no-claim, and Phase 10G closes it as such — without broadening scope, weakening rules, inventing a registry, or authorizing a fallback path. This is an honest checkpoint, not a failure to be tuned or padded.

## Guard language

Phase 10G adds/clarifies the following guard language:

- No compliant registry source exists under the frozen Phase 10E protocol (`no_compliant_registry_source_exists` = true; `no_compliant_registry_source_bucket` = `bucket_no_compliant_registry_source_exists`).
- No fallback path is authorized (`no_fallback_path_authorized` = true; `no_fallback_bucket` = `bucket_no_fallback_path_authorized`).
- Execution remains blocked until a compliant external package matching the 10G contract exists (`execution_remains_blocked_until_compliant_external_package_matches_contract` = true; `execution_blocked_bucket` = `bucket_execution_blocked_until_compliant_external_package_matching_10g_contract_exists`).
- The absent external package is NOT treated as permission to create one (`does_not_treat_absent_external_package_as_permission_to_create_one` = true).

## Future external-input package contract (metadata/specification only)

Phase 10G defines — as metadata/specification only — what a future compliant operator-provided external registry-input package MUST contain. No package matching this contract exists in Phase 10G; the contract is defined only, and no package is constructed or intake-validated in 10G. The validator enforces the contract as an exact closed list and rejects missing/extra future fields (the self-test exercises this schema enforcement on synthetic fixtures only).

The required future external-input package contract fields (closed list):

- `operator_assertion_package_externally_provided` — operator assertion that the package was externally provided;
- `registry_manifest_file` — registry manifest file;
- `provenance_statement` — provenance statement;
- `license_usage_permissions` — license/usage permissions;
- `immutable_checksums` — immutable checksums;
- `operator_declared_acquisition_method` — acquisition method declared by operator;
- `explicit_no_project_side_fetch_clone_scrape_source_discovery` — explicit statement that no project-side fetch/clone/scrape/source discovery was used;
- `offline_local_availability_for_later_bounded_validation` — offline/local availability for later bounded validation.

Future package intake validation checks are defined only (NOT executed in 10G): `package_presence_check_only`, `declared_provenance_check_only`, `schema_check_only`, `checksums_check_only`, `permissions_check_only`. These are the prospective checks a later Phase 10H MAY run if and only if an operator provides a complete offline registry-input package matching the 10G contract.

## Anti-adaptation rules

The Phase 10G protocol is prospective, not tuned to the observed Phase 10C `bucket_zero` / `bucket_no_eligible_channel_registry` outcome or the Phase 10F `bucket_zero` / `bucket_no_compliant_registry_input_under_frozen_10e_protocol` outcome.

- Phase 10C and Phase 10F are mentioned ONLY as gate/provenance facts and failure modes to guard against, not as optimization feedback.
- The frozen Phase 10E protocol is applied exactly (imported closed lists, set-equality validated; no drift, no post-hoc edit after seeing registry/package availability).
- No rule is justified by "because 10F found no compliant registry" unless framed as a general compliance/audit requirement.
- No new threshold/fallback/channel exception is introduced to avoid the observed repair reason.
- The absent external package is not treated as permission to create one.
- No fallback path is authorized for the absent external package.
- Execution remains blocked until a compliant external package matches the contract.
- Future execution must use the frozen 10E protocol and the 10G external-input contract as written, with no post-hoc selection after seeing source/package availability, and no fallback path is authorized.

## Phase 10G boundary

- Phase 10G is docs-only closeout plus external-input protocol freeze.
- Phase 10G closes Phase 10F as repair/no-claim under the frozen 10E protocol.
- Phase 10G makes no new evidence claims (only Phase 10F closeout status and a future external-input package contract as metadata/specification only).
- Phase 10G does not fetch/clone/read/scrape/inspect/sample/download source material.
- Phase 10G does not materialize source contents.
- Phase 10G does not inspect public registries.
- Phase 10G does not infer candidates from memory, docs, URLs, package indexes, GitHub, search, or prior non-compliant sources.
- Phase 10G does not generate tasks or packets or execute any downstream pipeline.
- Phase 10G does not score/adjudicate/run correctness/evidence_success.
- Phase 10G does not construct or validate a registry manifest.
- Phase 10G does not construct or intake-validate an external-input package.
- Phase 10G does not modify, weaken, reinterpret, or extend Phase 10E or Phase 10F.
- Phase 10G does not authorize a fallback path.
- Phase 10G does not treat the absent external package as permission to create one.
- Phase 10G does not treat zero compliance as partial success.
- Phase 10G does not make user-approval wording a protocol dependency.

## Next phase

The next possible phase is Phase 10H external registry-input intake validation ONLY if an operator later provides a complete offline registry-input package matching the 10G contract. Phase 10H may validate package presence, declared provenance, schema, checksums, and permissions. Phase 10H still must not fetch/clone/read external source or score/adjudicate unless a later boundary authorizes. Until such a package exists and a later boundary authorizes, execution remains blocked. No registry manifest is constructed or validated in 10G. No user approval wording is used.

## Privacy boundary

Public output is aggregate/boundary-only. Source-specific details (repo names, URLs, owners, commits, paths, snippets, line ranges, packet IDs, run dirs, per-source/per-task/per-packet facts, candidate identities, candidate registry contents, registry manifest locations, registry construction/exclusion audit logs, external package contents/checksums/provenance, singleton buckets) are kept private under ignored `runs/` only. In this docs/protocol-freeze run no private details were materialized and no package was read. Only the gate-reference values are exact public values, allowed only at their exact gate paths (the immediate Phase 10F commit/CI).

## No-claim boundary

Phase 10G makes no method, product, performance, training, provider, model, runtime, default, scoring, outcome, evidence-success, correctness, generalization, validation, materialization-succeeded, independent-validation-passed, OpenLocus-works, Phase-10/10E/10F/10G-confirms, registry-construction-succeeded, registry-provision-succeeded, external-package-exists, external-package-validated, or empirical claim. Phase 10G records ONLY Phase 10F closeout status and a future external-input package contract (metadata/specification only). Phase 10G is docs-only closeout + external-input protocol freeze (no execution, no claim), not evidence/method/product/correctness/validation success.

The conservative recommendation is: `phase10g_external_registry_input_protocol_freeze_and_phase10f_closeout_only_phase9_closed_inherited_phase10a_gate_inherited_phase10b_gate_inherited_phase10c_executed_frozen_10b_route_once_repair_no_claim_zero_accepted_sources_phase10d_closeout_guard_gate_inherited_phase10e_protocol_freeze_gate_inherited_phase10f_registry_construction_execution_gate_inherited_ci_green_closed_as_repair_no_claim_under_frozen_10e_protocol_phase10g_authorized_by_oracle_docs_only_closeout_and_external_registry_input_protocol_freeze_only_phase10g_applies_frozen_phase10e_protocol_exactly_no_drift_phase10g_is_docs_only_closeout_and_external_input_protocol_freeze_only_not_execution_phase10g_is_not_validation_product_method_correctness_evidence_success_phase10g_does_not_fetch_clone_read_scrape_inspect_sample_or_download_source_material_phase10g_does_not_materialize_source_contents_phase10g_does_not_generate_tasks_or_packets_or_execute_downstream_pipeline_phase10g_does_not_score_adjudicate_or_run_correctness_evidence_success_phase10g_does_not_construct_or_validate_a_registry_manifest_phase10g_does_not_construct_or_intake_validate_an_external_input_package_phase10g_does_not_authorize_a_fallback_path_phase10g_does_not_treat_absent_external_package_as_permission_to_create_one_phase10g_does_not_modify_weaken_reinterpret_or_extend_phase10e_or_phase10f_phase10g_protocol_is_prospective_not_tuned_to_observed_outcome_phase10g_closes_phase10f_as_repair_no_claim_under_frozen_10e_protocol_no_compliant_registry_source_exists_under_frozen_10e_protocol_no_fallback_path_authorized_execution_remains_blocked_until_compliant_external_package_matching_10g_contract_exists_no_registry_manifest_constructed_or_validated_in_phase10g_no_external_input_package_constructed_or_intake_validated_in_phase10g_future_package_contract_is_metadata_specification_only_no_package_exists_future_phase10h_intake_validation_only_if_operator_provides_complete_offline_package_matching_10g_contract_phase10h_must_not_fetch_clone_read_source_or_score_adjudicate_unless_later_boundary_authorizes_boundary_review_after_phase10g_commit_and_ci_green_no_user_approval_wording_no_method_product_correctness_evidence_success_claim`.
