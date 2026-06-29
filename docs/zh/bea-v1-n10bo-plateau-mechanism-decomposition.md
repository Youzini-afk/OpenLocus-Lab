# BEA-v1-N10BO Plateau Mechanism Decomposition

日期：2026-06-29

BEA-v1-N10BO 是对 N10BM after-heavy plateau 的 direct empirical decomposition。它读取 same scoped N1 span rows，并且只评估 5 个 plateau variants：`before20_after80`、`before25_after75`、`before30_after70`、`before35_after65` 与 `before40_after60`。它不添加 plateau 之外的 windows，不进行 adaptive tuning，不改变 cost budgets，不运行 retrieval/reruns/OpenLocus，不生成 candidates，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: plateau_mechanism_decomposition_complete_n10bp_authorized
self-test: 18 / 18
forbidden scan: pass
private span rows read: 213
plateau variants: 5
N10BP authorized: true
```

## Plateau overlap

五个 plateau variants 都产生相同的 public aggregate reach：

```text
top10 span overlap: 20
top20 span overlap: 24
top10 common across all plateau variants: 20
top20 common across all plateau variants: 24
top10 union across plateau variants: 20
top20 union across plateau variants: 24
top10 case-swap count: 0
top20 case-swap count: 0
lost pm50 top10 max count: 0
```

因此该 plateau 是 genuinely stable plateau，而不是 case-swapping plateau。

## Direction buckets

对于所有 plateau variants 的 common top10 recovered set：

```text
before_gold_gap: 10
after_gold_gap: 1
already_overlap: 9
other: 0
unique top10 cases per plateau variant: 0
```

所有输出仅为 public aggregate/bucket counts；不公开 paths、spans、line numbers、snippets、gold values、candidate lists 或 exact ranks。

## Handoff

N10BO 只授权 `BEA-v1-N10BP Plateau Mechanism Package`，即本 decomposition 的 public package。它不授权 private reads、new variants、adaptive per-row choice、new cost budgets、runtime/default behavior、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10bo_plateau_mechanism_decomposition.py`
- Report: `artifacts/bea_v1_n10bo_plateau_mechanism_decomposition/bea_v1_n10bo_plateau_mechanism_decomposition_report.json`
