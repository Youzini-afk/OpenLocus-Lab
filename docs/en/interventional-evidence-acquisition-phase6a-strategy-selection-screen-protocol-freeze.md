# Interventional Evidence Acquisition Phase 6A Strategy-Selection Screen Protocol Freeze

Date: 2026-07-07

Status: `phase6a_strategy_selection_screen_protocol_freeze_no_claim`

Authorization: `design_only_no_execution`

## Scope

Phase 6A freezes the protocol for a possible later Phase 6B tiny strategy-selection screen. It is design-only: no ignored Phase 5B rows are read, no source is read, no tasks or repositories are created, no model is fit, and no screen is executed.

## Frozen Phase 6B screen shape

- Input source: existing ignored Phase 5B rows only, and only after Phase 6A is committed/CI-green and the Phase 6B boundary is explicitly invoked under the existing low-resource/no-claim constraints.
- Scale: tiny repo-heldout screen.
- Labels: the same seven frozen Phase 5B labels exactly:
  1. `bm25_then_read_top1`
  2. `bm25_then_read_next_unique_file`
  3. `symbol_regex_then_read_top1`
  4. `symbol_regex_then_read_next_unique_file`
  5. `read_related_test_when_available`
  6. `stop`
  7. `abstain`
- Split: repo-heldout, with no repository overlap between fit/check slices.
- Implementation: stdlib-only tiny screen, using pre-action aggregate/action fields only.
- Baselines: action-only table, shuffled repo-heldout control, and fixed-label controls.

## Evidence and public reporting boundary

Phase 6B, if invoked later under the existing low-resource/no-claim constraints, may only publish aggregate buckets. It must not publish raw row contents, raw task IDs, paths, ranges, hashes, snippets, run directories, manifests, per-repo details, per-task details, or singleton buckets.

Any future screen is only a no-claim stability check for whether a tiny stdlib-only policy shape is worth preserving as research machinery. It is not a release, readiness, promotion, or deployment claim.

## Hard stops

Stop before or during any future Phase 6B attempt if there is a Phase 6A private/source read, new task/repo creation, model fit during Phase 6A, execution during Phase 6A, repo overlap between slices, label drift, public private leak, singleton public bucket, nonzero `stop`/`abstain` success, post-outcome tuning, or new remote/provider work.

## Current status

Phase 6A is complete as a design-only protocol freeze. Phase 6B runner or screen work may proceed only after Phase 6A is committed/CI-green and the Phase 6B boundary is explicitly invoked under the existing low-resource/no-claim constraints.
