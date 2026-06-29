# BEA-v1-N10BP Plateau Mechanism Package

日期：2026-06-29

BEA-v1-N10BP 是 N10BO plateau mechanism decomposition 的 public-only package。它只读取 public artifacts，不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不改变 cost budgets，不运行 retrieval/reruns/OpenLocus，不生成或 materialize candidates，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: plateau_mechanism_package_complete_n10bq_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BP: 0
recomputes in N10BP: 0
N10BQ authorized: true
```

## Packaged plateau facts

所有 plateau variants 的 top10/top20 均为 `20 / 24`：

- `before20_after80`
- `before25_after75`
- `before30_after70`
- `before35_after65`
- `before40_after60`

Common-core package：

```text
top10 common: 20
top10 union: 20
top20 common: 24
top20 union: 24
case swaps: 0
unique cases: 0
lost pm50 max: 0
stability bucket: genuinely_stable_plateau
```

Common top10 direction buckets：

```text
before_gold_gap: 10
after_gold_gap: 1
already_overlap: 9
other: 0
```

Candidate pool/order 未改变，输出保持 public bucket/count only。

## Handoff

N10BP 只授权 `BEA-v1-N10BQ Plateau Cost-Minimization Sweep`：same scoped N1 rows，仅 stable plateau 的 fixed ratio family（`20/80`、`25/75`、`30/70`、`35/65`、`40/60`），total costs `60/80/100/120`，20 个预声明 variants，以及 public aggregate/bucket metrics。它不授权 adaptive tuning、family 外的新 ratios、runtime/default behavior、heldout/generalization claims、method/downstream claims、retrieval/rerun、candidate generation、selector/reranker execution、P5 或 BEA-v1-A。

## Artifact

- Script: `eval/bea_v1_n10bp_plateau_mechanism_package.py`
- Report: `artifacts/bea_v1_n10bp_plateau_mechanism_package/bea_v1_n10bp_plateau_mechanism_package_report.json`
