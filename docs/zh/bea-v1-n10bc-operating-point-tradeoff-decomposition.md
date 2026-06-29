# BEA-v1-N10BC Operating-Point Tradeoff Decomposition

日期：2026-06-29

BEA-v1-N10BC 是在 same scoped N1 span rows 上进行的 direct empirical decomposition。它只分析 N10BB 授权的三个 named operating points：`low_cost=pm30`、`balanced=before25_after75` 与 `max_recall=pm200`。它不使用 new window sizes，不进行 adaptive per-case selection，不涉及 runtime/default behavior，不运行 retrieval/rerun/OpenLocus，不生成或 materialize candidates，也不运行 selector/reranker/P5/BEA-v1-A。

## 结果

```text
status: operating_point_tradeoff_decomposition_complete_n10bd_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
usable span rows: 213
N10BD authorized: true
```

## Operating-point progression

| Step | Variant | Cumulative top10/top20 | Marginal top10/top20 | Marginal cost | Cost per new top10 bucket | Lost previous hits |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| baseline | baseline | 9 / 10 | +9 / +10 | 0 | baseline | 0 |
| low_cost | pm30 | 18 / 22 | +9 / +12 | 600 | low | 0 |
| balanced | before25_after75 | 20 / 24 | +2 / +2 | 400 | medium | 0 |
| max_recall | pm200 | 25 / 30 | +5 / +6 | 3000 | very_high | 0 |

## Mechanism buckets for new top10 hits

| Step | before-gold gap | after-gold gap | already-reachable-late-rank | other |
| --- | ---: | ---: | ---: | ---: |
| baseline -> low_cost | 8 | 1 | 0 | 0 |
| low_cost -> balanced | 2 | 0 | 0 | 0 |
| balanced -> max_recall | 3 | 2 | 0 | 0 |

N10BC 发现 max-recall gains 仍然是与 lower-cost operating points 相同的 before/after gold-window gap mechanism，而不是 qualitatively new mechanism。Candidate pool 与 candidate order 保持不变。

## Boundary

N10BC 只是 same-source N1 span-surface proxy decomposition。它不作 heldout/generalization、N2-equivalent、runtime/default、method-winner、downstream-value、selector/reranker、P5/BEA-v1-A、retrieval/rerun、candidate-generation、new-variant 或 adaptive-selection claim。

## Handoff

N10BC 只授权 `BEA-v1-N10BD Operating-Point Tradeoff Decomposition Audit Package`，这是 public package。它不授权 private reads、runtime/default promotion、new variants、adaptive selection、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10bc_operating_point_tradeoff_decomposition.py`
- Report: `artifacts/bea_v1_n10bc_operating_point_tradeoff_decomposition/bea_v1_n10bc_operating_point_tradeoff_decomposition_report.json`
