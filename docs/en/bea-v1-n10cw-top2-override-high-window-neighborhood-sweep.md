# BEA-v1-N10CW Top2 Override High-Window Neighborhood Sweep

Date: 2026-06-30

BEA-v1-N10CW is a direct empirical same-source sweep around the top2 all-span override window. It tests whether increasing only the top2 symmetric override beyond pm400 yields additional local-window gains. The base rule remains fixed: short spans use before75/after225, top2 positions use symmetric pmX override, and candidate pool/order is unchanged.

## Result

```text
status: top2_override_high_window_neighborhood_sweep_complete_n10cx_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
variant count: 8
pm400 reference: 27 / 33 at 4000 / 7000
max observed: 30 / 36 at pm1000
local saturation: false
N10CX authorized: true
```

## Variant findings

| Variant | top10/top20 | cost10/cost20 | Decision bucket |
| --- | ---: | ---: | --- |
| pm300 | 26 / 32 | 3600 / 6600 | high_window_saturated |
| pm350 | 26 / 32 | 3800 / 6800 | high_window_saturated |
| pm400 | 27 / 33 | 4000 / 7000 | high_window_saturated |
| pm450 | 28 / 34 | 4200 / 7200 | high_window_improves_pm400 |
| pm500 | 28 / 34 | 4400 / 7400 | high_window_improves_pm400 |
| pm600 | 28 / 34 | 4800 / 7800 | high_window_improves_pm400 |
| pm800 | 29 / 35 | 5600 / 8600 | high_window_improves_pm400 |
| pm1000 | 30 / 36 | 6400 / 9400 | high_window_improves_pm400 |

Remaining misses at pm1000: file-not-in-top10 `167`, same-file/no-span `4`, and span-beyond-top10 `12`.

## Boundary

N10CW uses exactly the eight predeclared pm values and no other variants. It does not use gold/outcome/miss-direction/content/file identity as policy input. It does not run retrieval/rerun/OpenLocus, candidate generation/add/remove/reorder, top3 override, medium/long gates, new rank/order arms, adaptive per-record tuning, selector/reranker execution, P5, BEA-v1-A, runtime/default promotion, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Handoff

N10CW authorizes only `BEA-v1-N10CX Top2 Override High-Window Neighborhood Public Package`.

## Artifact

- Script: `eval/bea_v1_n10cw_top2_override_high_window_neighborhood_sweep.py`
- Report: `artifacts/bea_v1_n10cw_top2_override_high_window_neighborhood_sweep/bea_v1_n10cw_top2_override_high_window_neighborhood_sweep_report.json`
