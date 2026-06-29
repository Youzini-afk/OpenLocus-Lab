# BEA-v1-N10BG Cost-Aware Decisions vs Fixed-pm50 Comparator

Date: 2026-06-29

BEA-v1-N10BG compares the three budget-conditioned span-window decisions against the original fixed `pm50` point over the same scoped N1 span rows. This is a research comparator smoke only: it is not a runtime/default recommendation, not heldout validation, and not a method-winner or downstream-value claim.

## Result

```text
status: cost_aware_decisions_vs_fixed_pm50_comparator_complete_n10bh_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
fixed pm50 comparator: 19 / 23, cost 1000
N10BH authorized: true
```

## Comparator findings

| Budget bucket | Decision | Variant | top10/top20 | Delta vs pm50 | Cost delta vs pm50 | Dominance bucket |
| --- | --- | --- | ---: | ---: | ---: | --- |
| strict_budget | low_cost | pm30 | 18 / 22 | -1 / -1 | -400 | cost_saving_tradeoff_vs_pm50 |
| moderate_budget | balanced | before25_after75 | 20 / 24 | +1 / +1 | 0 | dominates_pm50 |
| recall_budget | max_recall | pm200 | 25 / 30 | +6 / +7 | +3000 | higher_recall_higher_cost_vs_pm50 |

The useful new signal is that `before25_after75` beats the original symmetric `pm50` at the same cost proxy. `pm30` is a cheaper small-loss option, while `pm200` buys more recall at much higher cost.

## Boundary

N10BG does not add variants, tune per case, change candidate pools/order, run retrieval/reruns, or recommend runtime/default behavior. It authorizes only N10BH public comparator package; the next research question is why the asymmetric `before25_after75` point beats symmetric `pm50`.

## Artifact

- Script: `eval/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator.py`
- Report: `artifacts/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator_report.json`
