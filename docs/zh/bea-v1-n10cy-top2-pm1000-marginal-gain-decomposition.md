# BEA-v1-N10CY Top2 pm1000 Marginal Gain Mechanism Decomposition

日期：2026-06-30

BEA-v1-N10CY 是 top2 high-window family 中从 pm400 到 pm800 到 pm1000 的 marginal gains 的 direct empirical same-source mechanism decomposition。它读取 same scoped N1 span rows，并且只比较三个 fixed policies：`short75_225_top2_all_pm400`、`short75_225_top2_all_pm800`、`short75_225_top2_all_pm1000`。

## 结果

```text
status: top2_pm1000_marginal_gain_decomposition_complete_n10cz_authorized
self-test: 14 / 14
forbidden scan: pass
private span rows read: 213
pm400: 27 / 33 at 4000 / 7000
pm800: 29 / 35 at 5600 / 8600
pm1000: 30 / 36 at 6400 / 9400
N10CZ authorized: true
```

## Marginal gains

- pm800 vs pm400：top10 +2，top20 +2。
- pm1000 vs pm800：top10 +1，top20 +1。
- pm1000 vs pm400：top10 +3，top20 +3。

Mechanism buckets 显示 pm800 的 gains 是 same-file before-gold cases，分布在 near-boundary buckets；pm1000 的增量 gain 是 101-300 boundary bucket 中的 same-file after-gold case。pm1000 vs pm400 总体 gains 为 2 个 before-gold 与 1 个 after-gold，均为 top1/top2 override cases 与 short-span-base cases。

## Remaining misses at pm1000

- file-not-in-top10：167
- same-file/no-span：4
- span-beyond-top10：12

Further local-window signal 与 rank/file-reach pivot signal 都仍然存在。本阶段不在两者之间做选择；它只授权 N10CZ oracle-scoped next exploration decision。

## Boundary

N10CY 不把 gold/outcome/miss-direction/content/file identity 用作 policy input。Gold 仅用于 post-hoc bucketed evaluation。它不 add/remove/reorder candidates，不引入 top3 override、medium/long gates、new rank/order arms 或 400/800/1000 之外的 new pm values。它不运行 retrieval/rerun/OpenLocus、selector/reranker logic、P5、BEA-v1-A、runtime/default promotion，也不作 heldout/generalization、method-winner 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition.py`
- Report: `artifacts/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition_report.json`
