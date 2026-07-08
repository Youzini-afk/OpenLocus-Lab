# Interventional Evidence Acquisition Phase 9D Task-Candidate Materialization

Date: 2026-07-09

Status: `repair_task_materialization_no_claim`

Authorization: `phase9d_task_candidate_materialization_no_scoring_no_claim`

Public report: [`phase9d_task_candidate_materialization_no_scoring_no_claim_report.json`](../../artifacts/phase9d_task_candidate_materialization_no_scoring_no_claim/phase9d_task_candidate_materialization_no_scoring_no_claim_report.json)

## Scope

Phase 9D is a bounded low-resource task-candidate construction and private source-reference materialization phase only. It is gated on the Phase 9C public report/status `phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim` and the Phase 9C docs/report CI references.

Execution required both explicit confirmations: `--confirm-phase9b-private-registry-read` and `--confirm-private-output`. Dry self-test and report validation do not read the Phase 9B private registry or source repositories.

## Materialization boundary

Phase 9D may read the ignored Phase 9B private accepted-source registry only under the explicit private-registry-read confirmation. It may write private manifests and materialization rows only under ignored `runs/phase9d_task_candidate_materialization_no_scoring_no_claim/...` and only under the explicit private-output confirmation.

Task candidates are inventory only. They are evidence-finding, file-localizable code-task candidates. They are not benchmark labels, outcomes, gold rows, success rows, or evidence-success evaluations. Materialization itself is not evidence success.

## Deterministic construction rules

Candidate construction preserves Phase 9B private registry order and uses no random shuffle. Replacements occur only before labels/outcomes/scoring: the next deterministic candidate from the same source is considered first, then the next source if needed. Replacement does not use performance, evidence, model, or downstream feedback.

The Phase 9C caps remain exact: target task-candidate bucket 48-72, hard cap up to 96, per-source task cap up to 8, and minimum distinct sources at least 8. If diversity is below the minimum after caps, Phase 9D must stop or repair rather than pass.

## Public result

The public report is aggregate-only. It contains phase/status/schema, Phase 9C gate refs, private-read authorization attestation, task-candidate inventory summary, materialization summary, diversity summary, no-claim boundary, privacy summary, validation summary, and a conservative recommendation.

The current public status is `repair_task_materialization_no_claim`. The public aggregate buckets show constructed inventory `bucket_zero`, materialized references `bucket_zero`, observed distinct sources `bucket_zero`, and source-reference currentness reread unavailable privately. This is a failed materialization attempt/checkpoint, not a pass.

Phase 9D did not fetch or clone public repositories. It only attempted direct materialization from the already-ignored Phase 9B private accepted-source registry under the explicit private-registry-read confirmation. The zero-materialization repair state is preserved rather than repaired in-place. Future public source fetch/clone for materialization requires a separate frozen boundary and explicit confirmation.

This materialization failure is not evidence that any evidence-acquisition method succeeded or failed. It is only a source-materialization readiness failure. Private manifests remain only under ignored `runs/`; the public report excludes exact repo/source/task/path/hash/snippet/owner/URL/commit/manifest/run-dir/per-source/per-task facts.

## No-claim boundary

Phase 9D performs no strategy scoring, labels, outcomes, evidence-success evaluation, model fitting/training, RPM-D2/model scaling, provider/LLM calls, runtime/default/product changes, or method/product/performance/training/provider/model/scoring/outcome/evidence-success/runtime/default claims.

Task rows, if any future boundary materializes them, remain candidate inventory only. They are not labels, outcomes, gold rows, success rows, or evidence_success. Materialization itself is not evidence_success.
