# BEA-v1-N10EK Fixed Difference-Aware Combination Experiment

日期：2026-06-30

BEA-v1-N10EK 在同一批 scoped N10DZ top100 private rows 和 N1 rows 上，测试一小组固定 difference-aware full/guard combination rules。这些规则只使用 policy-time observable buckets，例如 novel-count pressure、top5 duplicate pressure、top5 novelty pressure、BM25-top5 preservation proxy 和 deep-novel pressure。它们不会用 full-only/guard-only membership、gold labels 或 hit outcomes 来逐 case 选择。

本实验不运行 retrieval、OpenLocus binary execution、candidate generation、network、runtime/default changes 或 selector/reranker logic。

## 结果

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

公开 artifact 只暴露聚合 buckets。不公开 paths、filenames、queries、candidates、gold labels、spans 或 exact ranks。

- 全部 60 cases 都在 `novel_count_gt_10`。
- Top5 duplicate pressure：31 none，16 one-duplicate，13 two-or-more。
- Top5 novelty pressure：41 个在 `0_to_2`，2 个在 `3`，17 个在 `4_to_5`。
- Deep-novel pressure：17 high，43 broad-only。
- Top5 preservation proxy：54 present，6 absent。

## 含义

不同于早先的简单 full/guard 拼接，一个固定 observable rule 在该 same sample 上达到之前的 13-case union bound：当 top5 novelty pressure high（`>=4`）时使用 guarded top5 novel-distinct order，否则使用 full novel-first。这仍然只是 same-source experimental evidence。它不是 runtime/default recommendation，不是 method-winner claim，也不是 downstream 或 heldout evidence。

## Handoff

因为一个 fixed difference-aware variant 超过 full novel-first 并达到 N10EG union bound，N10EK 只授权同一批 rows 上的 audit/recompute follow-up。它不授权 new/scaled retrieval、OpenLocus binary execution、candidate generation、network、runtime/default changes、selector/reranker execution、method-winner claims、downstream claims 或 heldout/generalization claims。

## Artifact

- Script: `eval/bea_v1_n10ek_fixed_difference_aware_combination_experiment.py`
- Report: `artifacts/bea_v1_n10ek_fixed_difference_aware_combination_experiment/bea_v1_n10ek_fixed_difference_aware_combination_experiment_report.json`
