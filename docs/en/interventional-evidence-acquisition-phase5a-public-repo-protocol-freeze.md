# Interventional Evidence Acquisition Phase 5A Public-Repo Protocol Freeze

Date: 2026-07-07

Status: `phase5a_public_repo_protocol_freeze_no_claim`

Authorization: `design_protocol_only_no_execution`

## Scope

Phase 5A freezes the protocol for a possible Phase 5B public-repo validation. It is design/protocol only: no repository fetch, no task generation, no private rows, no source reads, no CI/workflow change, and no Phase 5B runner implementation.

Phase 4E remains candidate-preserving but no-claim. Phase 5A does not convert that screen into a winner, lift, product, default, runtime, or readiness claim.

## Frozen Phase 5B envelope

- Task target: 120 hard tasks; valid range 100-150; hard maximum 150.
- Seven labels imply a hard maximum of 1050 private rows.
- Repository target: 10-12 public GitHub repositories; hard maximum 16.
- Before any Phase 5B execution, freeze repository URLs, commit SHAs, strata, and replacement rules.
- Allowed Phase 5B network use: public GitHub repository fetch for frozen URLs/SHAs only.
- Forbidden: LLM/provider calls, search APIs, remote model calls, model training, runtime/default changes, new retrieval families, staged runs, and post-outcome tuning.

## Frozen seven labels

The Phase 5B action labels are exactly:

1. `bm25_then_read_top1`
2. `bm25_then_read_next_unique_file`
3. `symbol_regex_then_read_top1`
4. `symbol_regex_then_read_next_unique_file`
5. `read_related_test_when_available`
6. `stop`
7. `abstain`

## Evidence and reporting rule

Candidate-found alone is not evidence. Counted success requires current-source read, materialization, hash/currentness verification, and task tie.

The public report must be aggregate-only: no raw task IDs, paths, ranges, hashes, snippets, run directories, manifests, singleton buckets, or per-task details. It may compare against the best fixed local/acquisition baseline, but must not say winner, lift, product, default, or runtime change.

## Hard-stop oracle

Stop/fail the Phase 5B route if any of these occur:

- fewer than 100 valid tasks;
- more than 150 tasks;
- more than 1050 private rows;
- staged runs or post-outcome tuning;
- public private leak or singleton public bucket;
- nonzero success for `stop` or `abstain`;
- no current-source validation for counted evidence;
- new provider, LLM, training, runtime/default, or retrieval-family work.

## Current status

Phase 5A is complete as a protocol freeze only. The next possible step, if separately implemented later, is Phase 5B execution under these frozen rules. No evidence claim is made here.
