# BEA-v1-N10BF Cost-Aware Operating-Point Decision Smoke Audit Package

Date: 2026-06-29

BEA-v1-N10BF is a public-only audit/package for the N10BE budget-conditioned operating-point decision smoke. It reads public artifacts only. It does not read private rows, recompute metrics, add variants, tune adaptively, run retrieval/reruns/OpenLocus, generate/materialize candidates, or make runtime/default recommendations.

## Result

```text
status: cost_aware_budget_decision_package_complete_n10bg_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10BF: 0
recomputes in N10BF: 0
N10BG authorized: true
```

## Packaged budget decisions

| Budget bucket | Rule | Selected point | Variant | top10/top20 | Delta vs baseline | Cost proxy | Cost bucket |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| strict_budget | max cost <= 600 | low_cost | pm30 | 18 / 22 | +9 / +12 | 600 | low |
| moderate_budget | max cost <= 1000 | balanced | before25_after75 | 20 / 24 | +11 / +14 | 1000 | medium |
| recall_budget | max cost <= 4000 | max_recall | pm200 | 25 / 30 | +16 / +20 | 4000 | very_high |

The package confirms this remains a research decision only: no runtime/default recommendation, no new variants, no adaptive per-case selection, no heldout/generalization, no method-winner, and no downstream-value claim.

## Handoff

N10BF authorizes only `BEA-v1-N10BG Cost-Aware Decisions vs Fixed-pm50 Comparator`: same scoped N1 rows, no new variants, compare strict/moderate/recall decisions against the original fixed pm50 comparator using aggregate metrics and bucketed dominance outcomes. N10BF itself is public-only.

## Artifact

- Script: `eval/bea_v1_n10bf_cost_aware_budget_decision_package.py`
- Report: `artifacts/bea_v1_n10bf_cost_aware_budget_decision_package/bea_v1_n10bf_cost_aware_budget_decision_package_report.json`
