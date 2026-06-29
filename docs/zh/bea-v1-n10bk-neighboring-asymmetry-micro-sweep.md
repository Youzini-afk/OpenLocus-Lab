# BEA-v1-N10BK Neighboring Asymmetry Micro-Sweep

日期：2026-06-29

BEA-v1-N10BK 是在 same scoped N1 span rows 上进行的 direct empirical same-cost direction-sensitivity micro-sweep。它只使用预声明 total-cost-100 window variants，不添加 variants，不改变 cost budgets，不进行 per-row adaptive window choice，不运行 retrieval/reruns/OpenLocus，不生成 candidates，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: neighboring_asymmetry_micro_sweep_complete_n10bl_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
variant count: 5
winner: before25_after75
winner direction bucket: after_heavy
trend: nonmonotonic_direction_sensitivity
```

## Same-cost variant metrics

| Variant | Direction bucket | top10/top20 | Delta vs pm50 | Delta vs before25_after75 | Lost pm50 top10 hits |
| --- | --- | ---: | ---: | ---: | ---: |
| before0_after100 | after_heavy | 19 / 22 | 0 / -1 | -1 / -2 | 1 |
| before25_after75 | after_heavy | 20 / 24 | +1 / +1 | 0 / 0 | 0 |
| before50_after50 | balanced | 19 / 23 | 0 / 0 | -1 / -1 | 0 |
| before75_after25 | before_heavy | 18 / 22 | -1 / -1 | -2 / -2 | 2 |
| before100_after0 | before_heavy | 11 / 13 | -8 / -10 | -9 / -11 | 9 |

Top10 trend 在 direction shifts 上是 nonmonotonic。最佳 same-cost point 仍是 `before25_after75`，即 after-heavy asymmetric window。

## Boundary

所有 variants 都是 fixed global 且预声明。Gold 或 miss-direction signal 不用于选择 per-record windows。Candidate pool/order 保持不变。

## Handoff

N10BK 只授权 `BEA-v1-N10BL Neighboring Asymmetry Direction-Sensitivity Package`，即 public package。它不授权 private reads、new variants、adaptive choice、new cost budgets、runtime/default behavior、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10bk_neighboring_asymmetry_micro_sweep.py`
- Report: `artifacts/bea_v1_n10bk_neighboring_asymmetry_micro_sweep/bea_v1_n10bk_neighboring_asymmetry_micro_sweep_report.json`
