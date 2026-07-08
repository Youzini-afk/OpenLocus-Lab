# Interventional Evidence Acquisition Phase 9I Materialized Inventory to Task Annotation Protocol Freeze

Date: 2026-07-09

Status: `phase9i_materialized_inventory_to_task_annotation_protocol_freeze_no_execution_no_scoring_no_claim`

Authorization: docs/report/validator-only protocol freeze for future conversion of Phase 9H private materialized source inventory into task annotation/outcome-acquisition inputs; no execution, no labels, no outcomes, no scoring, no evidence_success, no claims

Public report: [`phase9i_materialized_inventory_to_task_annotation_protocol_freeze_no_execution_no_scoring_no_claim_report.json`](../../artifacts/phase9i_materialized_inventory_to_task_annotation_protocol_freeze_no_execution_no_scoring_no_claim/phase9i_materialized_inventory_to_task_annotation_protocol_freeze_no_execution_no_scoring_no_claim_report.json)

## Scope

Phase 9I is a docs/report/validator-only protocol freeze. It freezes the future protocol for converting the Phase 9H private materialized source inventory into future task annotation / outcome-acquisition inputs. It does not fetch, clone, read, or materialize any repository or source. It does not read ignored `runs/`, private candidate pools/registries/manifests, or the Phase 9H private materialized inventory. It does not generate task annotations (labels), outcomes, gold rows, evidence_success, or scoring/evaluation rows. It makes no method/product/performance/model/provider/training/runtime/default/scoring/outcome/evidence-success claim.

Phase 9I is gated on Phase 9H remote commit `d997caab5487e66c544f657645d70c97f3b780e2`, CI run `28976655118`, CI success, and Phase 9H status `phase9h_candidate_source_pool_public_source_network_fetch_materialization_readiness_no_scoring_no_claim`. Phase 9G (status `phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim`, CI success, protocol freeze) and Phase 9F status `phase9f_public_source_fetch_clone_materialization_repair_no_claim` are carried as bucketed inherited provenance; the exact Phase 9G remote commit/CI run values are intentionally not published in the Phase 9I report/docs, so only the Phase 9H full commit SHA and CI run are public gate references. Local same-tree git commits are not read or compared; the supplied confirmation values are matched against the frozen public gate constants only. Future execution under the Phase 9I protocol requires Phase 9I commit and CI green.

Phase 9I records that Phase 9H is source-materialization readiness only and is NOT proof that any annotation, outcome, evidence_success, scoring, or evaluation works. Phase 9H did not generate task annotations, outcomes, gold rows, evidence_success, or scoring rows; it produced only private materialized inventory rows under ignored `runs/`. Phase 9I does not read that private inventory.

## Frozen future annotation types

The frozen future protocol allows only these annotation types (neutral word "annotation" is used rather than "labels" wherever possible):

- Task eligibility annotation
- Evidence-localization requirement
- Expected evidence form
- Outcome-acquisition preconditions
- Adjudication rules
- Rejection/replacement rules before scoring

## Frozen future annotation protocol

The frozen future protocol requires:

- Convert private Phase 9H materialized inventory to future task annotation inputs only.
- Task eligibility annotation only under explicit future confirmation.
- Evidence-localization requirement only for file-localizable code tasks.
- Expected evidence form must match Phase 9H inventory shape.
- Outcome-acquisition preconditions must be set before any outcome acquisition.
- Adjudication rules must be frozen before any annotation execution.
- Rejection/replacement rules before scoring only.
- No annotation execution in Phase 9I.
- No outcomes, gold rows, evidence_success, or scoring/evaluation rows in Phase 9I.
- No provider/LLM/model/default/runtime change in Phase 9I.
- Private Phase 9H inventory read only after Phase 9I commit and CI green and explicit confirmation.
- Future annotation execution requires a separate Phase 9J boundary.
- Aggregate public report only: no private inventory or annotation details.
- No singleton public buckets.

## Inherited aggregate caps/buckets from Phase 9H

The frozen protocol inherits the Phase 9H aggregate caps/buckets exactly:

- Target inventory bucket: 48-72
- Hard cap bucket: up to 96
- Per-source cap bucket: up to 8
- Minimum distinct sources bucket: at least 8

## Future private input/output locations

Future private inputs/outputs (Phase 9H private materialized inventory, future annotation rows, future outcome-acquisition rows) stay only under ignored `runs/`. Phase 9I does not read them. Future Phase 9J may read Phase 9H private inventory only after Phase 9I commit and CI green and explicit confirmations.

## Future Phase 9J gate conditions

Future Phase 9J execution requires all of the following confirmations:

- Confirm Phase 9H commit and CI green
- Confirm Phase 9I protocol freeze
- Confirm read Phase 9H private materialized inventory
- Confirm ignored runs workspace
- Confirm private-output-only
- Confirm no scoring/evidence_success
- Confirm no provider/LLM/model/default/runtime change
- Confirm aggregate public report only

Phase 9J may read Phase 9H private inventory only after Phase 9I commit and CI green. Phase 9J remains no-scoring and no-evidence_success until a separate frozen boundary.

## No-claim boundary

Phase 9I makes no method, product, performance, training, provider, model, runtime, default, scoring, outcome, or evidence-success claim. The frozen protocol is aggregate-bucketed only. Public output excludes repo names, source names, URLs, owners, commits, hashes, paths, snippets, task IDs, row IDs, manifest locations, run locations, per-source facts, per-task facts, and singleton buckets. Phase 9I does not imply that annotation, outcome acquisition, evidence_success, scoring, or any evidence-acquisition method works; Phase 9H source-materialization readiness is not proof of annotation, outcome, evidence_success, or scoring success. Phase 9I is not execution and not evidence/method/product success.

The conservative recommendation is: `future_annotation_execution_requires_separate_phase9j_boundary_and_explicit_private_phase9h_inventory_read_confirmation`.
