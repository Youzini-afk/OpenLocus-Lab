# BEA-v1-N10BL Neighboring Asymmetry Direction-Sensitivity Package

Date: 2026-06-29

BEA-v1-N10BL is a public-only package for the N10BK fixed-cost neighboring asymmetry micro-sweep. It reads public artifacts only and does not read private rows, recompute metrics, add variants, change cost budgets, tune adaptively, run retrieval/reruns/OpenLocus, generate/materialize candidates, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: direction_sensitivity_package_complete_n10bm_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10BL: 0
recomputes in N10BL: 0
N10BM authorized: true
```

## Packaged direction sensitivity

All variants have fixed total cost proxy `100`.

| Variant | Direction bucket | top10/top20 | Delta vs pm50 | Lost pm50 top10 hits | Winner |
| --- | --- | ---: | ---: | ---: | --- |
| before0_after100 | after_heavy | 19 / 22 | 0 / -1 | 1 | false |
| before25_after75 | after_heavy | 20 / 24 | +1 / +1 | 0 | true |
| before50_after50 | balanced | 19 / 23 | 0 / 0 | 0 | false |
| before75_after25 | before_heavy | 18 / 22 | -1 / -1 | 2 | false |
| before100_after0 | before_heavy | 11 / 13 | -8 / -10 | 9 | false |

Winner: `before25_after75`; winner direction bucket: `after_heavy`; trend: `nonmonotonic_direction_sensitivity`.

## Handoff

N10BL authorizes only `BEA-v1-N10BM After-Heavy Local Asymmetry Refinement Sweep`: same scoped N1 rows, fixed total cost 100 only, and predeclared variants `before10_after90`, `before15_after85`, `before20_after80`, `before25_after75`, `before30_after70`, `before35_after65`, and `before40_after60`. It does not authorize other variants, adaptive per-row choice, new cost budgets, runtime/default behavior, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10bl_direction_sensitivity_package.py`
- Report: `artifacts/bea_v1_n10bl_direction_sensitivity_package/bea_v1_n10bl_direction_sensitivity_package_report.json`
