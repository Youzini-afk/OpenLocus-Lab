# Interventional Evidence Acquisition Phase 9G Candidate Source-Pool Network-Fetch Protocol Freeze

Date: 2026-07-09

Status: `phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim`

Authorization: docs/report/validator-only protocol freeze

Public report: [`phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim_report.json`](../../artifacts/phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim/phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim_report.json)

## Scope

Phase 9G is a docs/report/validator-only protocol freeze. It freezes the future candidate-source-pool schema and the future Phase 9H network-fetch implementation contract after the Phase 9F public-source fetch/clone materialization repair/no-claim checkpoint. It does not fetch, clone, read, or materialize any repository or source. It does not read ignored `runs/` or private candidate pools/registries/manifests. It does not generate task rows, labels, outcomes, scoring rows, or evidence_success. It makes no method/product/performance/model/provider/training/runtime/default/scoring/outcome/evidence-success claim.

Phase 9G is gated on Phase 9F remote commit `c091b742`, CI run `28973602930`, CI success, and Phase 9F status `phase9f_public_source_fetch_clone_materialization_repair_no_claim`. It records that Phase 9F is repair/no-claim and is NOT proof that public fetch/clone or materialization works: Phase 9F observed zero buckets and `public_source_fetch_clone_executed=false`. Local same-tree git commits are not read or compared; the supplied confirmation values are matched against the frozen public gate constants only. Future execution under the Phase 9G contract requires Phase 9G commit and CI green.

## Frozen candidate-source-pool schema

The frozen future candidate-source-pool schema requires:

- Bounded public source pool only.
- License, access, default-branch, and currentness fields.
- Deterministic source order field.
- Retry/timeout/failure bucket fields.
- Clone target mapping under ignored `runs/` only.
- No credentials, auth-prompt, private-host, or local-fallback fields.
- No repo name, URL, owner, commit, path, hash, snippet, row ID, run-dir, per-source, or per-task fields.

## Frozen Phase 9H network-fetch implementation contract

The frozen future Phase 9H contract requires:

- Public-only HTTPS or git fetch/clone under explicit confirmation only.
- Fetch/clone into ignored `runs/` workspace only, never into tracked artifacts.
- No credentials, auth prompts, private hosts, or local fallback.
- Deterministic source order with no random shuffle.
- Bounded public source pool only.
- Fail closed on redirect ambiguity.
- Fail closed on auth prompt.
- Fail closed on private host.
- Fail closed on missing license, access, or default branch.
- Fail closed on hash or currentness mismatch.
- Fail closed on inaccessible source.
- Retry/timeout/failure buckets are aggregate-only.
- Clone target mapping under ignored `runs/` only.
- License/access/default-branch/currentness fields before any acceptance.
- Privacy redaction rules are aggregate-only.
- Aggregate public report only: no repo names, URLs, owners, commits, paths, snippets, hashes, row IDs, run dirs, or singleton buckets.
- Task-candidate target bucket 48-72, hard cap up to 96, per-source cap up to 8, minimum distinct sources at least 8.
- Stop or repair if zero materialization occurs after caps.
- Stop or repair if source diversity falls below the minimum after caps.
- No replacement or tuning based on labels, outcomes, evidence_success, model, or downstream-performance feedback.
- Task types limited to evidence-finding file-localizable code tasks.
- Provider/LLM tasks forbidden.
- No unit public per-source or per-task reporting.
- No hidden GitHub API substitute unless a future protocol explicitly allows or forbids it.
- Future strategy scoring requires another frozen boundary.

## No-claim boundary

Phase 9G makes no method, product, performance, training, provider, model, runtime, default, scoring, outcome, or evidence-success claim. The frozen contract is aggregate-bucketed only. Public output excludes repo names, source names, URLs, owners, commits, hashes, paths, snippets, task IDs, row IDs, manifest locations, run locations, per-source facts, per-task facts, and singleton buckets. Phase 9G does not imply that fetch/clone, materialization, or any evidence-acquisition method works; Phase 9F repair/no-claim is not proof of fetch/clone or materialization success.
