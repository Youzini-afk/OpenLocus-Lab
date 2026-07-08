# Interventional Evidence Acquisition Phase 9K Outcome-Acquisition / Scoring / Adjudication Protocol Freeze

Date: 2026-07-09

Status: `phase9k_outcome_scoring_protocol_freeze_no_claim`

Authorization: docs/report/validator-only protocol freeze for future outcome-acquisition, scoring, and adjudication rules; no execution, no private reads, no outcomes, no scoring, no adjudication, no gold labels, no evidence_success, no claims

Public report: [`phase9k_outcome_scoring_protocol_freeze_no_claim_report.json`](../../artifacts/phase9k_outcome_scoring_protocol_freeze_no_claim/phase9k_outcome_scoring_protocol_freeze_no_claim_report.json)

## Scope

Phase 9K is a docs/report/validator-only protocol freeze. It freezes the future protocol for outcome acquisition, scoring, and adjudication that may follow the Phase 9J annotation-input rows. It does not fetch, clone, read, or materialize any repository or source. It does not read ignored `runs/`, private candidate pools/registries/manifests, the Phase 9H private materialized inventory, or the Phase 9J private annotation-input rows/manifests. It does not acquire outcomes, score, adjudicate, or generate gold labels, benchmark labels, evidence_success, result labels, annotation-truth, or scoring/evaluation rows. It makes no method/product/performance/model/provider/training/runtime/default/scoring/outcome/evidence-success/annotation-truth claim.

Phase 9K is gated on Phase 9H remote commit `d997caab5487e66c544f657645d70c97f3b780e2`, CI run `28976655118`, CI success, Phase 9H status `phase9h_candidate_source_pool_public_source_network_fetch_materialization_readiness_no_scoring_no_claim`, Phase 9I remote commit `fe9eabba744ff00526fadd7184801c3721677fba`, CI run `28979060368`, CI success, Phase 9I status `phase9i_materialized_inventory_to_task_annotation_protocol_freeze_no_execution_no_scoring_no_claim`, Phase 9I protocol freeze, Phase 9J remote commit `25140f4017acf139012fe917fd920ddba9839cc3`, CI run `28980705743`, CI success, Phase 9J status `phase9j_annotation_input_rows_generated_no_scoring_no_claim`, and Phase 9J annotation-input rows generated. Phase 9G (status `phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim`, CI success, protocol freeze) and Phase 9F status `phase9f_public_source_fetch_clone_materialization_repair_no_claim` are carried as bucketed inherited provenance; their exact remote commit/CI run values are intentionally not published in the Phase 9K report/docs, so only the Phase 9H, Phase 9I, and Phase 9J full commit SHAs and CI runs are public gate references. Local same-tree git commits are not read or compared; the supplied confirmation values are matched against the frozen public gate constants only. Future execution under the Phase 9K protocol requires Phase 9K commit and CI green.

Phase 9K records that Phase 9J annotation-input rows are routing/precondition metadata only, not benchmark truth. Phase 9K records that Phase 9H is source-materialization readiness only and is NOT proof that any annotation, outcome, evidence_success, scoring, or evaluation works. Phase 9K does not read any private inventory or annotation-input rows.

## Frozen future outcome-acquisition packet schema

The frozen future outcome-acquisition packet schema requires only these fields (routing/precondition metadata only, not benchmark truth):

- Task eligibility routing/precondition only
- Evidence-localization requirement
- Expected evidence form
- Outcome-acquisition precondition
- Annotation-input metadata reference

Private-only fields stay private under ignored `runs/` only. Allowed public aggregate buckets only; no exact counts. Missing outcomes are handled as unavailable, not as failure or success. Invalid outcomes are rejected before scoring with replacement only. Unavailable outcomes are recorded in an aggregate unavailability bucket only.

## Frozen future scoring protocol

The frozen future scoring protocol requires:

- Scoring metrics and denominators frozen before outcome visibility.
- Inclusion/exclusion rules frozen before outcome visibility.
- Failure buckets predeclared, aggregate only.
- No threshold or metric tuning after outcome visibility.
- No post-hoc subgroup mining except predeclared aggregate buckets.
- No scoring execution in Phase 9K.
- Future scoring requires a separate frozen boundary after outcome acquisition.
- Aggregate public report only; no private scoring details.

Predeclared failure buckets: outcome unavailable failure, outcome invalid failure, inclusion failure, metric/denominator failure.

## Frozen future adjudication protocol

The frozen future adjudication protocol requires:

- Adjudication independence required; raters blind to each other.
- Minimum rater count at least three if human annotations are used.
- Disagreement categories predeclared before adjudication.
- Tie-break flow predeclared before adjudication.
- Independent outcomes acquired first, adjudication second.
- Adjudication rule is not adjudicated truth.
- No adjudication execution in Phase 9K.
- Future adjudication requires a separate frozen boundary after scoring.
- Aggregate public report only; no private adjudication details.

Disagreement categories: full agreement, partial disagreement, full disagreement, tie requires adjudication.

## Truth-boundary

Phase 9K makes the truth-boundary explicit:

- Annotation-input metadata is routing/precondition only, not benchmark truth.
- Eligibility is not correctness.
- Expected evidence form is not gold evidence.
- Outcome precondition is not outcome.
- Adjudication rule is not adjudicated truth.

## Inherited aggregate caps/buckets from Phase 9H

The frozen protocol inherits the Phase 9H aggregate caps/buckets exactly:

- Target inventory bucket: 48-72
- Hard cap bucket: up to 96
- Per-source cap bucket: up to 8
- Minimum distinct sources bucket: at least 8

## Future private input/output locations

Future private inputs/outputs (Phase 9H private materialized inventory, Phase 9J private annotation-input rows, future outcome-acquisition rows, future scoring rows, future adjudication rows) stay only under ignored `runs/`. Phase 9K does not read them. Future Phase 9L may read Phase 9J private annotation-input rows only after Phase 9K commit and CI green and explicit confirmations.

## Future Phase 9L gate conditions

Future Phase 9L execution requires all of the following:

- Confirm Phase 9K commit and CI green
- Confirm Phase 9H, Phase 9I, Phase 9J commit and CI
- Confirm Phase 9K protocol freeze
- Confirm read Phase 9J private annotation-input rows
- Confirm ignored runs workspace
- Confirm private-output-only
- Confirm no scoring/evidence_success until a separate boundary
- Confirm no provider/LLM/model/default/runtime change
- Confirm aggregate public report only

Phase 9L may read Phase 9J private annotation-input rows only after Phase 9K commit and CI green. The future gate requires Phase 9K commit+CI green and explicit confirmations/boundary, not user approval. Consider Phase 9L outcome acquisition only, and later Phase 9M scoring/adjudication if complexity warrants.

## No-claim boundary

Phase 9K makes no method, product, performance, training, provider, model, runtime, default, scoring, outcome, evidence-success, or annotation-truth claim. The frozen protocol is aggregate-bucketed only. Public output excludes repo names, source names, URLs, owners, commits (except the whitelisted Phase 9H/9I/9J gate constants), hashes, paths, snippets, task IDs, row IDs, manifest locations, run locations, per-source facts, per-task facts, and singleton buckets. Phase 9K does not imply that annotation, outcome acquisition, evidence_success, scoring, adjudication, or any evidence-acquisition method works; Phase 9H source-materialization readiness is not proof of annotation, outcome, evidence_success, or scoring success. Phase 9K is not execution and not evidence/method/product success.

The conservative recommendation is: `future_outcome_acquisition_scoring_adjudication_require_separate_frozen_boundary_phase9l_requires_phase9k_commit_ci_green_and_explicit_confirmations_boundary_no_user_approval_no_evidence_success_no_method_product_claim`.
