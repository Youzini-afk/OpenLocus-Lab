# BEA-v1-N10BH Cost-Aware Decisions vs Fixed-pm50 Comparator Audit Package

Date: 2026-06-29

BEA-v1-N10BH is a public-only audit/package for the N10BG fixed-pm50 comparator. It reads public artifacts only and does not read private rows, recompute metrics, add variants, tune adaptively, run retrieval/reruns/OpenLocus, generate/materialize candidates, or make runtime/default recommendations.

## Result

```text
status: pm50_comparator_package_complete_n10bi_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10BH: 0
recomputes in N10BH: 0
N10BI authorized: true
```

## Packaged pm50 comparison

Fixed pm50 comparator: top10/top20 `19 / 23`, cost proxy `1000`.

| Budget decision | Variant | top10/top20 | Delta vs pm50 | Cost delta vs pm50 | Lost original span hits | Dominance bucket |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| strict_budget / low_cost | pm30 | 18 / 22 | -1 / -1 | -400 | 1 | cost_saving_tradeoff_vs_pm50 |
| moderate_budget / balanced | before25_after75 | 20 / 24 | +1 / +1 | 0 | 0 | dominates_pm50 |
| recall_budget / max_recall | pm200 | 25 / 30 | +6 / +7 | +3000 | 0 | higher_recall_higher_cost_vs_pm50 |

The package confirms candidate pool/order remained unchanged, and all outputs are public aggregate/bucket counts.

## Handoff

N10BH authorizes only `BEA-v1-N10BI Asymmetric Window Direction Mechanism Decomposition`: same scoped rows, compare pm50 against `before25_after75`, analyze gained/lost buckets using before/after direction, and verify no gold/miss direction is used to choose per-record windows. It does not authorize new variants, adaptive/default behavior, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10bh_pm50_comparator_package.py`
- Report: `artifacts/bea_v1_n10bh_pm50_comparator_package/bea_v1_n10bh_pm50_comparator_package_report.json`
