# Interventional Evidence Acquisition Phase 9F Public Source Fetch/Clone Materialization

Date: 2026-07-09

Status: `phase9f_public_source_fetch_clone_materialization_repair_no_claim`

Authorization: public source fetch/clone materialization only, under the frozen Phase 9E protocol

Public report: [`phase9f_public_source_fetch_clone_materialization_no_scoring_no_claim_report.json`](../../artifacts/phase9f_public_source_fetch_clone_materialization_no_scoring_no_claim/phase9f_public_source_fetch_clone_materialization_no_scoring_no_claim_report.json)

## Scope

Phase 9F is a bounded public source fetch/clone materialization runner only. It is gated on the frozen Phase 9E protocol and its public gate references: Phase 9E remote commit `7f4ad8a`, CI run `28972733319`, CI success, and status `phase9e_public_source_fetch_clone_materialization_protocol_freeze_no_execution_no_scoring_no_claim`. Local same-tree git commits are not read or compared; the supplied confirmation values are matched against the frozen public gate constants only.

Execution required all six explicit confirmations: `--confirm-phase9e-commit 7f4ad8a`, `--confirm-phase9e-ci 28972733319`, `--confirm-public-source-fetch-clone`, `--confirm-ignored-runs-workspace`, `--confirm-no-labels-outcomes-scoring-evidence-success`, and `--confirm-no-provider-llm-model-default-runtime-change`. Dry self-test and report validation do not fetch/clone, read ignored `runs/`, or read private candidate pools.

## Materialization boundary

Phase 9F may fetch/clone public-only source repositories into ignored `runs/phase9f_public_source_fetch_clone_materialization_no_scoring_no_claim/...` workspace only, never into tracked artifacts. Private candidate source pools, manifests, and materialization rows stay only under ignored `runs/`. Public-source inputs are not embedded in tracked source/docs/report; candidate source URLs, if any, are read from a private candidate pool under ignored `runs/` only.

Task candidates are inventory only. They are evidence-finding, file-localizable code-task candidates. They are not benchmark labels, outcomes, gold rows, success rows, or evidence-success evaluations. Materialization itself is not evidence success.

## Deterministic construction rules

Candidate construction uses deterministic source order with no random shuffle. Replacements occur only before labels/outcomes/scoring: the next deterministic candidate from the same source is considered first, then the next source if needed. Replacement does not use performance, evidence, model, or downstream feedback.

The Phase 9E caps remain exact: target task-candidate bucket 48-72, hard cap up to 96, per-source task cap up to 8, and minimum distinct sources at least 8. If diversity is below the minimum after caps, Phase 9F must stop or repair rather than pass. Required private materialization checks before accepting any candidate include public access, license/access/default-branch/currentness/hash/reread checks, and file-localizable evidence-finding task shape.

## Public result

The public report is aggregate-only. It contains schema_version, phase, status, Phase 9E gate references, confirmation summary, materialization summary, source diversity summary, privacy summary, validation summary, no-claim boundary, forbidden execution boundary, and a conservative recommendation.

The current public status is `phase9f_public_source_fetch_clone_materialization_repair_no_claim`. The public aggregate buckets show constructed inventory `bucket_zero`, materialized references `bucket_zero`, observed distinct sources `bucket_zero`, and source-reference currentness reread unavailable privately. This is a failed materialization attempt/checkpoint, not a pass.

Phase 9F did not embed any remote source URL in tracked source. No private candidate source pool was available under ignored `runs/`, and public fetch/clone could not materialize any source under the caps, so materialization remained zero after caps. The zero-materialization repair state is preserved rather than repaired in-place. No in-place tuning/cap or source selection occurred after the observed materialization failure. This is source-materialization readiness failure only, not evidence that any evidence-acquisition method succeeded or failed.

Private manifests remain only under ignored `runs/`; the public report excludes exact repo/source/task/path/hash/snippet/owner/URL/commit/manifest/run-dir/per-source/per-task facts and exact singleton buckets. The only commit/CI values in the public report are the Phase 9E public gate references (`7f4ad8a`, `28972733319`).

## No-claim boundary

Phase 9F performs no strategy scoring, labels, outcomes, evidence-success evaluation, model fitting/training, provider/LLM calls, runtime/default/product changes, or method/product/performance/training/provider/model/scoring/outcome/evidence-success/runtime/default claim. No provider/LLM/model/default/runtime change occurred.

Task rows, if any future boundary materializes them, remain candidate inventory only. They are not labels, outcomes, gold rows, success rows, or evidence_success. Materialization itself is not evidence_success. Future strategy scoring requires another frozen boundary.
