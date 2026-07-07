# Interventional Evidence Acquisition Phase 2 Comparison Design

Date: 2026-07-07

Status: `phase2_small_fair_local_comparison_no_claim`

Authorization: low-resource local pilot completed with private rows under ignored `runs/`. This document still does not authorize CI changes, model work, provider/network use, runtime/default changes, product promotion, or method-winner claims.

Latest result: public aggregate-only report [`phase2_small_fair_local_comparison_pilot_report.json`](../../artifacts/phase2_small_fair_local_comparison_pilot/phase2_small_fair_local_comparison_pilot_report.json), status `phase2_small_fair_local_comparison_no_claim`, recommendation `phase2_positive_screen_no_promotion`.

Follow-up holdout screen: [`phase3_independent_local_holdout_validation_screen_report.json`](../../artifacts/phase3_independent_local_holdout_validation_screen/phase3_independent_local_holdout_validation_screen_report.json), status `phase3_independent_local_holdout_validation_no_claim`, recommendation `phase3_holdout_positive_screen_no_promotion`. This validates the protocol on a fresh local holdout slice only; it is not method selection or promotion.

## What Phase 1 showed

Phase 1 was useful, but limited:

- Local scripts can safely run tiny experiments.
- Real current-source reads and hashes can be checked.
- Private rows stayed under ignored `runs/` storage.
- Public reports stayed aggregate-only.
- There is still no proof that any evidence-finding method is better than another.

Phase 1E was a diagnostic screen only. It did not rank policies or make a method claim.

## Next real question

If a fairer comparison is run later, can any small local evidence-finding strategy beat the best fixed local baseline on hard tasks?

The comparison must be against the best fixed local baseline, not only against `stop` or `abstain` controls.

## Proposed Phase 2 shape

The pilot used this shape:

- 24-40 hard tasks.
- Same seven local labels/families unless a separate decision changes them:
  - `bm25_then_read_top1`
  - `bm25_then_read_next_unique_file`
  - `symbol_regex_then_read_top1`
  - `symbol_regex_then_read_next_unique_file`
  - `read_related_test_when_available`
  - `stop`
  - `abstain`
- No LLM/provider/network actions.
- No model training.
- No runtime/default changes.
- No new retrieval families.
- Private rows only under ignored `runs/`.
- Public report aggregate-only.

## Fair comparison rules

- Predeclare the success threshold before running.
- Compare candidate strategies to the best fixed local baseline.
- Counted success requires an actual current-source read with range, content hash, currentness re-read, and range/content match.
- Candidate found does not count as evidence.
- `stop` and `abstain` must remain controls.
- Public reporting must avoid exact paths, ranges, hashes, snippets, task text, row IDs, run paths, private manifest paths, and exact singleton private counts.

## Stop/go outcomes

- `stop_no_claim`: no margin over the best fixed baseline.
- `repair_design_no_claim`: instrumentation, task mix, or privacy boundary is bad.
- `phase2_positive_screen_no_promotion`: positive screen only; still no product/default claim.
- No method winner unless a later independent validation confirms it.

The completed pilot selected `phase2_positive_screen_no_promotion`. This means only that the aggregate screen was positive enough to keep a future explicit decision possible. It is not a winner, lift, signal, product, or default claim.

## Forbidden list

Phase 2 design does not authorize:

- LLM/provider/network actions.
- Model training, model scaling, or RPM-D2 work.
- Runtime/default changes.
- New retrieval families.
- CI gates or required CI changes.
- Product/default promotion.
- OpenLocus v3 branding.
- Method-winner, signal/lift, or efficacy claims before execution and independent validation.
- Reopening closed HAAE-A2/v2, RPM-D2, FRK, LDI/static support, provider/network, runtime/default, or method-winner routes.

## Decision checkpoint

Before any Phase 2 execution, a separate explicit decision must approve the task set, success threshold, comparison rule, private-row schema, and public aggregate report shape.
