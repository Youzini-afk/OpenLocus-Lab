# BEA-v1-N10CI Independent Recompute of Winning Hybrid

日期：2026-06-29

BEA-v1-N10CI 在同一个 scoped N1 span rows 上独立 recompute N10CG winning hybrid strategy `short75_225_top3_all_pm200`。它不 import 或 call N10CG evaluator，也不复用 N10CG transform functions。

## 结果

```text
status: winning_hybrid_independent_recompute_pass_n10cj_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
top10/top20 span overlap: 25 / 31
cost10/cost20: 3300 / 6300
lost short75/225 hits: 0
N10CG code call count: 0
N10CJ authorized: true
```

## Independent semantics

N10CI 从 private N1 span rows 独立 recompute 相同 evidence order 与 candidate pool。对每个 evidence position：

- short original span（`<=10` lines）：expand before `75`、after `225`；
- top3 evidence positions：无论 span length 如何，使用 all-span pm200（`200 / 200`）；
- 其他情况：不 expansion。

Gold 只在 projection 后用于 evaluation。不会发生 candidate add/remove/reorder。

## Match to N10CG/N10CH

独立 aggregate 与 public N10CG/N10CH package 中的 `short75_225_top3_all_pm200` 完全匹配：`25 / 31`，cost10/cost20 `3300 / 6300`，lost short75/225 hits `0`。

## Boundary

这仍然只是 same-source N1 proxy evidence。N10CI 不授权 runtime/default promotion、heldout/generalization claims、retrieval/rerun、candidate generation/add/remove/reorder、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Handoff

N10CI 只授权 `BEA-v1-N10CJ Winning Hybrid Replication Package`，即不进行额外 private reads 的 public package。

## Artifact

- Script: `eval/bea_v1_n10ci_independent_recompute_winning_hybrid.py`
- Report: `artifacts/bea_v1_n10ci_independent_recompute_winning_hybrid/bea_v1_n10ci_independent_recompute_winning_hybrid_report.json`
