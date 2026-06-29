# BEA-v1-N10BQ Plateau Cost-Minimization Sweep

Date: 2026-06-29

BEA-v1-N10BQ is a direct empirical cost-minimization sweep over the same scoped N1 span rows. It uses only the stable plateau ratio family (`20/80`, `25/75`, `30/70`, `35/65`, `40/60`) and four predeclared total costs (`60`, `80`, `100`, `120`) for 20 fixed variants. It does not add ranking/order arms, tune adaptively, run retrieval/reruns/OpenLocus, generate candidates, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: plateau_cost_minimization_sweep_complete_n10br_authorized
self-test: 17 / 17
forbidden scan: pass
private span rows read: 213
variant count: 20
minimum cost preserving plateau: 80
chosen research operating point: cost80_before25_after75
N10BR authorized: true
```

## Cost summary

Plateau-preserved means top10 >= 20, top20 >= 24, and lost plateau-core top10 hits = 0.

| Total cost | Best top10/top20 | Preserved variants | Plateau preserved |
| ---: | ---: | ---: | --- |
| 60 | 19 / 23 | 0 | false |
| 80 | 20 / 24 | 1 | true |
| 100 | 20 / 24 | 5 | true |
| 120 | 20 / 24 | 5 | true |

At cost 80, only `before25_after75` preserves the plateau. At cost 60, no ratio preserves it. At costs 100 and 120, all five stable-plateau ratios preserve it.

## Boundary

This is a research sweep, not a runtime/default recommendation. It uses fixed global windows, no per-row adaptive choice, no gold-based window choice, no new ratio outside the plateau family, and no new cost outside the four predeclared costs.

## Handoff

N10BQ authorizes only `BEA-v1-N10BR Plateau Cost-Minimization Package`, a public package of this cost-minimization result.

## Artifact

- Script: `eval/bea_v1_n10bq_plateau_cost_minimization_sweep.py`
- Report: `artifacts/bea_v1_n10bq_plateau_cost_minimization_sweep/bea_v1_n10bq_plateau_cost_minimization_sweep_report.json`
