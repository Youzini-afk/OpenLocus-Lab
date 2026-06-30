# BEA-v1-N10EK Fixed Difference-Aware Combination Experiment

Date: 2026-06-30

BEA-v1-N10EK tests a small fixed set of difference-aware full/guard combination rules over the same scoped N10DZ top100 private rows and N1 rows. The rules use only policy-time observable buckets such as novel-count pressure, top5 duplicate pressure, top5 novelty pressure, a BM25-top5 preservation proxy, and deep-novel pressure. They do not use full-only/guard-only membership, gold labels, or hit outcomes to choose per case.

The experiment does not run retrieval, OpenLocus binary execution, candidate generation, network, runtime/default changes, or selector/reranker logic.

## Result

```text
status: fixed_difference_aware_combination_experiment_complete_audit_recompute_authorized
self-test: 9 / 9
forbidden scan: pass
variant count: 10
baseline top10: 5
full novel-first top10: 11
guarded top5 novel-distinct top10: 10
best variant: diffaware_top5_novel_guard_else_full
best top10/top20/top50/top100: 13 / 16 / 20 / 26
N10EG union bound: 13
any variant beats full novel-first: true
any variant reaches union bound: true
```

## Observable-feature buckets

The public artifact exposes only aggregate buckets. It does not publish paths, filenames, queries, candidates, gold labels, spans, or exact ranks.

- All 60 cases are in `novel_count_gt_10`.
- Top5 duplicate pressure: 31 none, 16 one-duplicate, 13 two-or-more.
- Top5 novelty pressure: 41 in `0_to_2`, 2 in `3`, and 17 in `4_to_5`.
- Deep-novel pressure: 17 high and 43 broad-only.
- Top5 preservation proxy: 54 present and 6 absent.

## Meaning

Unlike the earlier simple full/guard splices, one fixed observable rule reaches the prior 13-case union bound on this same sample: use the guarded top5 novel-distinct order when top5 novelty pressure is high (`>=4`), otherwise use full novel-first. This is still same-source experimental evidence only. It is not a runtime/default recommendation, not a method-winner claim, and not downstream or heldout evidence.

## Handoff

Because a fixed difference-aware variant beats full novel-first and reaches the N10EG union bound, N10EK authorizes only an audit/recompute follow-up over the same rows. It does not authorize new/scaled retrieval, OpenLocus binary execution, candidate generation, network, runtime/default changes, selector/reranker execution, method-winner claims, downstream claims, or heldout/generalization claims.

## Artifact

- Script: `eval/bea_v1_n10ek_fixed_difference_aware_combination_experiment.py`
- Report: `artifacts/bea_v1_n10ek_fixed_difference_aware_combination_experiment/bea_v1_n10ek_fixed_difference_aware_combination_experiment_report.json`
