# BEA-v1-N10CT Top2 Override Window Neighborhood Sweep

Date: 2026-06-30

BEA-v1-N10CT is a direct empirical same-source sweep around the N10CR/N10CS positive `top2_pm300_short75_225` result. It reads only the same scoped N1 span rows and public N10CS/N10CR/N10CP artifacts. It does not run retrieval/reruns/OpenLocus, generate/add/remove/reorder candidates, add rank/order arms, use top3 overrides, add medium/long gates, tune adaptively, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: top2_override_window_neighborhood_sweep_complete_n10cu_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
variant count: 9
minimum pm for 26/32: 275
max observed top10/top20: 27 / 33
N10CU authorized: true
```

## Variant findings

All variants use the same base rule: short spans receive before75/after225, and top2 positions receive a symmetric all-span pmX override.

| Variant | top10/top20 | cost10/cost20 | Decision |
| --- | ---: | ---: | --- |
| short75_225_top2_all_pm200 | 25 / 31 | 3200 / 6200 | no_improvement_pm300_retained |
| short75_225_top2_all_pm225 | 25 / 31 | 3300 / 6300 | no_improvement_pm300_retained |
| short75_225_top2_all_pm250 | 25 / 31 | 3400 / 6400 | no_improvement_pm300_retained |
| short75_225_top2_all_pm275 | 26 / 32 | 3500 / 6500 | preserves_pm300_at_lower_cost |
| short75_225_top2_all_pm300 | 26 / 32 | 3600 / 6600 | no_improvement_pm300_retained |
| short75_225_top2_all_pm325 | 26 / 32 | 3700 / 6700 | no_improvement_pm300_retained |
| short75_225_top2_all_pm350 | 26 / 32 | 3800 / 6800 | no_improvement_pm300_retained |
| short75_225_top2_all_pm375 | 26 / 32 | 3900 / 6900 | no_improvement_pm300_retained |
| short75_225_top2_all_pm400 | 27 / 33 | 4000 / 7000 | improves_pm300 |

The minimum pm window that preserves the 26/32 result is pm275. The largest tested window, pm400, improves to 27/33.

## Boundary

N10CT is same-source N1 proxy evidence only. Policy inputs are fixed windows and candidate position; gold/outcome/miss-direction/content/file identity are not policy inputs. Candidate pool/order is unchanged. The result does not authorize runtime/default behavior, heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/reorder, top3 overrides, medium/long extra gates, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Handoff

N10CT authorizes only `BEA-v1-N10CU Top2 Override Neighborhood Public Package`, a public package with no private reads, recompute, or new variants.

## Artifact

- Script: `eval/bea_v1_n10ct_top2_override_window_neighborhood_sweep.py`
- Report: `artifacts/bea_v1_n10ct_top2_override_window_neighborhood_sweep/bea_v1_n10ct_top2_override_window_neighborhood_sweep_report.json`
