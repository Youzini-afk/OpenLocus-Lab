# BEA-v1-N10BR Plateau Cost-Minimization Package

Date: 2026-06-29

BEA-v1-N10BR is a public-only package for the N10BQ plateau cost-minimization sweep. It reads public artifacts only and does not read private rows, recompute metrics, add variants, tune adaptively, run retrieval/reruns/OpenLocus, generate/materialize candidates, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: cost_minimization_package_complete_n10bs_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BR: 0
recomputes in N10BR: 0
N10BS authorized: true
```

## Packaged cost-minimization facts

N10BQ evaluated 20 predeclared variants: five stable-plateau ratios (`20/80` through `40/60`) times four total costs (`60`, `80`, `100`, `120`).

| Cost | Best top10/top20 | Preserved variants | Package fact |
| ---: | ---: | ---: | --- |
| 60 | 19 / 23 | 0 | lost plateau core = 1 |
| 80 | 20 / 24 | 1 | `cost80_before25_after75`, lost_core=0, lost_pm50=0 |
| 100 | 20 / 24 | 5 | all five plateau ratios preserve |
| 120 | 20 / 24 | 5 | all five plateau ratios preserve |

Minimum cost preserving the plateau is `80`. The chosen research operating point is `cost80_before25_after75`. This is explicitly not a runtime/default recommendation and not a method-winner claim.

## Handoff

N10BR authorizes only `BEA-v1-N10BS Boundary-Cost Refinement Sweep`: same scoped N1 span rows, fixed ratio `25/75` only, total costs `65`, `70`, `75`, `80`, `85`, `90`, and `95`, no new ratios, no adaptive tuning, no ranking/order changes, and public aggregate output only.

## Artifact

- Script: `eval/bea_v1_n10br_cost_minimization_package.py`
- Report: `artifacts/bea_v1_n10br_cost_minimization_package/bea_v1_n10br_cost_minimization_package_report.json`
