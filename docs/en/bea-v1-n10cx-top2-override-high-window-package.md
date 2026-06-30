# BEA-v1-N10CX Top2 Override High-Window Sweep Public Package

Date: 2026-06-30

BEA-v1-N10CX is a public-only package of the N10CW top2 override high-window neighborhood sweep. It reads public artifacts only and performs no private reads, no recompute, and no new variants.

## Result

```text
status: top2_override_high_window_package_complete_n10cy_authorized
self-test: 12 / 12
forbidden scan: pass
private reads in N10CX: 0
recomputes in N10CX: 0
N10CY authorized: true
```

## Packaged high-window sweep

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

Maximum observed top10/top20 is `30 / 36`; the minimum pm value for the max top10 is `1000`; local saturation is `false`. Remaining misses at pm1000 are file-not-in-top10 `167`, same-file/no-span `4`, and span-beyond-top10 `12`.

## Boundary

N10CX confirms there were no candidate pool/order changes, no top3 override, and no medium/long gates. It does not authorize runtime/default behavior, heldout/generalization, retrieval/rerun, candidate generation/add/remove/reorder, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Handoff

N10CX authorizes only `BEA-v1-N10CY Top2 High-Window Next Mechanism Decision`, scoped by the next oracle as either pm1000 marginal-gain decomposition or rank/file-reach pivot.

## Artifact

- Script: `eval/bea_v1_n10cx_top2_override_high_window_package.py`
- Report: `artifacts/bea_v1_n10cx_top2_override_high_window_package/bea_v1_n10cx_top2_override_high_window_package_report.json`
