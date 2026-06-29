# BEA-v1-N10AV Exploratory Span-Window Variant Sweep Replication Package

日期：2026-06-29

BEA-v1-N10AV 是整合 N10AS、N10AT 与 N10AU 的 public-only replication package。它只读取 public artifacts。它不读取 private rows，不 recompute variants，不运行 extra sweeps，不引入 new variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成 candidates，也不作 runtime/default、heldout/generalization、N2-equivalent、method-winner 或 downstream-value claims。

## 结果

```text
status: exploratory_span_window_sweep_replication_package_complete_n10aw_authorized
self-test: 14 / 14
forbidden scan: pass
private reads: 0
variant recomputes: 0
N10AS -> N10AT -> N10AU chain complete: true
N10AU all 15 aggregate matches: true
```

## Frontier package

| Tier | Variant | top10/top20 | Cost proxy |
| --- | --- | --- | --- |
| low-cost frontier | `pm30` | 18 / 22 | 600 (`low`) |
| balanced frontier | `before25_after75` | 20 / 24 | 1000 (`medium`) |
| balanced frontier | `pm75` | 21 / 25 | 1500 (`medium`) |
| max-recall frontier | `pm200` | 25 / 30 | 4000 (`very_high`) |

该 package 只记录 scoped same-source exploratory frontier。它不会把 frontier 转换为 runtime/default recommendation，也不会形成 method/downstream claim。

## Next research options

N10AV 列出具体但非即时执行的选项：cost-sensitive window mechanism decomposition、selected frontier points 上的 default-off adapter variants，或仅在有 new source authorization or data 时进行 broader/heldout replay。唯一授权的下一步是 `BEA-v1-N10AW Exploratory Span-Window Follow-Up Selection Audit`，即 mechanism/cost-focused follow-up selection audit。

## Artifact

- Script: `eval/bea_v1_n10av_exploratory_span_window_sweep_replication_package.py`
- Report: `artifacts/bea_v1_n10av_exploratory_span_window_sweep_replication_package/bea_v1_n10av_exploratory_span_window_sweep_replication_package_report.json`
