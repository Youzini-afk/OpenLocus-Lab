# BEA-v1-N10BK Neighboring Asymmetry Micro-Sweep

Date: 2026-06-29

BEA-v1-N10BK is a direct empirical same-cost direction-sensitivity micro-sweep over the same scoped N1 span rows. It uses only the predeclared total-cost-100 window variants and does not add variants, change cost budgets, choose per-row windows adaptively, run retrieval/reruns/OpenLocus, generate candidates, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

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

The top10 trend is nonmonotonic across direction shifts. The best same-cost point remains `before25_after75`, an after-heavy asymmetric window.

## Boundary

All variants are fixed globally and predeclared. No gold or miss-direction signal is used to choose per-record windows. Candidate pool/order remains unchanged.

## Handoff

N10BK authorizes only `BEA-v1-N10BL Neighboring Asymmetry Direction-Sensitivity Package`, a public package. It does not authorize private reads, new variants, adaptive choice, new cost budgets, runtime/default behavior, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10bk_neighboring_asymmetry_micro_sweep.py`
- Report: `artifacts/bea_v1_n10bk_neighboring_asymmetry_micro_sweep/bea_v1_n10bk_neighboring_asymmetry_micro_sweep_report.json`
