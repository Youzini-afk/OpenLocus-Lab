# Interventional Evidence Acquisition Phase 9H Candidate Source-Pool Public-Source Network-Fetch Materialization

Date: 2026-07-09

Status: `phase9h_candidate_source_pool_public_source_network_fetch_materialization_readiness_no_scoring_no_claim`

Authorization: candidate source-pool public-source network-fetch materialization only, under the frozen Phase 9G candidate-source-pool network-fetch protocol

Public report: [`phase9h_candidate_source_pool_public_source_network_fetch_materialization_no_scoring_no_claim_report.json`](../../artifacts/phase9h_candidate_source_pool_public_source_network_fetch_materialization_no_scoring_no_claim/phase9h_candidate_source_pool_public_source_network_fetch_materialization_no_scoring_no_claim_report.json)

## Scope

Phase 9H is a bounded candidate source-pool public-source network-fetch materialization runner only. It is gated on the frozen Phase 9G candidate-source-pool network-fetch protocol and its public gate references: Phase 9G remote commit `130b6732`, CI run `28974306775`, CI success, and status `phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim`. The Phase 9F public gate references (remote commit `c091b742`, CI run `28973602930`, CI success, Phase 9F status `phase9f_public_source_fetch_clone_materialization_repair_no_claim`) are also carried forward. Local same-tree git commits are not read or compared; the supplied confirmation values are matched against the frozen public gate constants only.

Execution required all nine explicit confirmations: `--confirm-phase9g-commit 130b6732`, `--confirm-phase9g-ci 28974306775`, `--confirm-public-source-network-fetch`, `--confirm-ignored-runs-workspace`, `--confirm-allow-public-github-api-transport`, `--confirm-no-private-or-local-fallback`, `--confirm-no-labels-outcomes-scoring-evidence-success`, `--confirm-no-provider-llm-model-default-runtime-change`, and `--confirm-aggregate-public-report-only`. Dry self-test and report validation do not fetch/clone, hit network, read ignored `runs/`, read private candidate pools, or read materialized sources.

## Transport boundary

Phase 9H uses unauthenticated public GitHub API transport only, declared in the aggregate transport bucket. Allowed: unauthenticated public GitHub REST/API metadata fetch, tree/content fetch, and public raw content fetch. Forbidden: hidden GitHub API fallback, authenticated API/tokens/credentials/auth prompts, private repos, using API to bypass privacy/currentness/license/default-branch checks, transport comparison claims. If API rate limits require auth, Phase 9H stops repair/no-claim. Redirect ambiguity is fail-closed: redirects are followed only to known public GitHub hosts. No credentials, auth prompts, private hosts, or local fallback are used.

## Materialization boundary

Phase 9H may fetch public-only source repositories via unauthenticated public GitHub API transport into ignored `runs/phase9h_candidate_source_pool_public_source_network_fetch_materialization_no_scoring_no_claim/...` workspace only, never into tracked artifacts. Private candidate source pools, manifests, and materialization rows stay only under ignored `runs/`. Public-source inputs are not embedded in tracked source/docs/report; candidate source identities, if any, are read from or created as a private candidate pool under ignored `runs/` only.

Task candidates are inventory/readiness rows only. They are evidence-finding, file-localizable, code-task-shaped. They are not benchmark labels, outcomes, gold rows, success rows, or evidence-success evaluations. Materialization itself is not evidence success. Readiness means source-materialization readiness only. It is not evidence success, method success, benchmark success, scoring success, or product readiness.

## Deterministic construction rules

Candidate construction uses deterministic source order with no random shuffle. Replacements occur only before labels/outcomes/scoring: the next deterministic candidate from the same source is considered first, then the next source if needed. Replacement does not use performance, evidence, model, or downstream feedback.

The Phase 9G caps remain exact: max source candidates considered 16, target accepted materialized candidate bucket 48-72, hard candidate/materialization attempt cap 96, per-source accepted candidate cap 8, minimum accepted distinct public sources 8, per-source transport attempts initial attempt + one fixed retry only. No dynamic cap changes occur after observing success/failure. If diversity is below the minimum after caps, Phase 9H must stop or repair rather than pass. Required private materialization checks before accepting any candidate include public access, license/access/default-branch/currentness/hash/reread checks, and file-localizable evidence-finding task shape.

## Public result

The public report is aggregate-only. It contains schema_version, phase, status, Phase 9F and Phase 9G gate references, confirmation summary, candidate-source-pool schema summary, transport summary bucketed only, materialization summary bucketed only, source diversity summary bucketed only, retry/timeout/failure buckets aggregate only, privacy summary, no-claim boundary all false, forbidden execution boundary all false, validation summary, and a conservative recommendation.

The current public status is `phase9h_candidate_source_pool_public_source_network_fetch_materialization_readiness_no_scoring_no_claim`. The public aggregate buckets show constructed inventory `bucket_target_48_to_72`, materialized references `bucket_target_48_to_72`, observed distinct sources `bucket_minimum_met_low`, transport attempt `bucket_minimum_met_low`, transport success `bucket_minimum_met_low`, retry attempt `bucket_minimum_met_low`, timeout failure `bucket_zero`, rate-limit stop no-auth false, and redirect ambiguity fail-closed false. This is source-materialization readiness only, not evidence that any evidence-acquisition method succeeded or failed.

Phase 9H did not embed any remote source URL or repo name in tracked source. A private candidate source pool was created under ignored `runs/` during confirmed execution using unauthenticated public GitHub search API discovery; source identities stay private under ignored `runs/`. Unauthenticated public GitHub API transport (trees API + raw content fetch) was used to materialize source files into ignored `runs/` workspace only. Private manifests/materialization rows stayed only under ignored `runs/`; the public report is aggregate-only. The public report excludes exact repo/source/task/path/hash/snippet/owner/URL/commit/manifest/run-dir/per-source/per-task facts and singleton buckets. The only commit/CI values in the public report are the Phase 9F and Phase 9G public gate references.

## No-claim boundary

Phase 9H performs no strategy scoring, labels, outcomes, evidence-success evaluation, model fitting/training, provider/LLM calls, runtime/default/product changes, or method/product/performance/training/provider/model/scoring/outcome/evidence-success/runtime/default claim. No provider/LLM/model/default/runtime change occurred.

Task rows remain candidate inventory only. They are not labels, outcomes, gold rows, success rows, or evidence_success. Materialization itself is not evidence_success. Future strategy scoring requires another frozen boundary.
