# Interventional Evidence Acquisition Phase 7A Fresh Public-Repo Validation Protocol Freeze

Date: 2026-07-07

Status: `phase7a_protocol_freeze_no_execution_no_claim`

Authorization: `design_only_no_execution`

## Scope

Phase 7A freezes the protocol for a possible later Phase 7B fresh public-repo validation. It is design-only: no repository fetch or clone, no task generation, no canary, no source reads, no private row or `runs/` reads, no model fit or training, no provider/network/LLM use, no runtime/default/product change, and no new retrieval family.

## Frozen Phase 7B envelope

- Fresh public repositories and tasks must not have been used in Phase 5B.
- Repository target: 8-12; hard maximum 16.
- Task target: 80-120; hard maximum 150; maximum 20 tasks per repository.
- Same seven labels: `bm25_then_read_top1`, `bm25_then_read_next_unique_file`, `symbol_regex_then_read_top1`, `symbol_regex_then_read_next_unique_file`, `read_related_test_when_available`, `stop`, `abstain`.
- Full-panel per task.
- Possible public statuses only: `stop_no_claim`, `repair_fresh_validation_contract_no_claim`, `fresh_public_repo_validation_positive_no_claim`.

## Freshness and replacement rules

Phase 7B must privately reject overlap with Phase 5B on repository URL/name/owner where available, pinned commit/SHA, task IDs, paths/ranges/hashes/materialization snippets, and too-close file-family buckets if privately detectable. Public output may expose only boolean/bucket overlap summaries.

Replacement is allowed only for pre-outcome invalidity: clone failure, pinned SHA unavailable, insufficient eligible files, or EvidenceCore materialization impossible before scoring. Replacement after seeing outcomes is forbidden.

## Evidence and reporting boundary

Candidate-found alone is not evidence. Counted success requires current source read, materialization, content digest, currentness reread, range match, and task tie. `stop`/`abstain` success must remain `bucket_zero`.

Any positive Phase 7B status would mean only nonzero aggregate EvidenceCore-valid local evidence acquisition under frozen actions while privacy/control checks held. It is not a method comparison, performance increase, chosen strategy, product/default/runtime/deployment, or training claim.

Future public reports must be aggregate-only: count buckets, label coverage buckets, evidence success buckets, best fixed local/acquisition baseline bucket, privacy summary, and EvidenceCore validation. Forbidden public output includes repository names/URLs/owners, exact commits/SHAs, exact paths/ranges/hashes/snippets, task IDs/row IDs, manifests/run directories, per-repo/per-task/per-fold details, singleton buckets, and claim wording.

## Current status

Phase 7A is complete as a protocol freeze only. Phase 7B runner, clone, task generation, or validation execution may proceed only after Phase 7A is committed/CI-green and the Phase 7B boundary is explicitly invoked under the existing low-resource/no-claim constraints.
