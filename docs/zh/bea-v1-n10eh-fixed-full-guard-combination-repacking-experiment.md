# BEA-v1-N10EH Fixed Full/Guard Combination Repacking Experiment

日期：2026-06-30

BEA-v1-N10EH 测试把 N10EG 的两个互补规则固定组合起来的 gold-free 方法。它使用同一份 scoped N10DZ top100 rows 和 N1 rows；不运行 new retrieval、candidate generation、runtime/default changes 或 selector/reranker logic。

## 结果

```text
status: fixed_full_guard_combination_repacking_experiment_complete_n10ei_authorized
self-test: 6 / 6
forbidden scan: pass
variant count: 7
full novel-first top10: 11
guarded top5 top10: 10
N10EG union upper bound: 13
best combination top10: 11
any variant beats full novel-first: false
any variant reaches union upper bound: false
```

## Interpretation

互补性是真的，但简单固定组合还不能变成更好的可执行规则。Full novel-first 仍是最强单规则，为 `11/60`；这批组合没有超过它，也没有达到 `13/60` 的 union upper bound。

这仍然有用：缺的两个 union cases 需要更具体的可观察差异分析，而不是简单拼规则。

## Handoff

N10EH 只授权 N10EI public package 和 N10EJ full/guard difference analysis over the same scoped rows。它不授权 new/scaled retrieval、candidate generation、runtime/default changes、selector/reranker execution、method-winner claims、downstream claims 或 heldout/generalization claims。

## Artifact

- Script: `eval/bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment.py`
- Report: `artifacts/bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment/bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment_report.json`
