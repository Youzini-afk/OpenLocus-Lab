# BEA-v1-N10CM Winning Hybrid Cost-Reduction Refinement Sweep

Date: 2026-06-29

BEA-v1-N10CM is a direct empirical same-source refinement sweep for the winning hybrid `short75_225_top3_all_pm200`. It tests whether the `25 / 31` result can be preserved at lower cost, or improved, using only fixed observable variants over the same scoped N1 span rows.

## Result

```text
status: winning_hybrid_cost_reduction_refinement_sweep_complete_n10cn_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
variant count: 12
winning reference: 25 / 31 at cost10/cost20 3300 / 6300
preserves winning at lower cost: 1
improves winning: 0
near winning cost-saving tradeoffs: 7
N10CN authorized: true
```

## Key findings

- `short75_225_top2_all_pm200` preserves the winning `25 / 31` result at lower cost: cost10/cost20 `3200 / 6200`, saving `100 / 100` versus the winning top3 pm200 rule.
- No variant improves beyond the winning `25 / 31` top10/top20 span-overlap result.
- Seven variants are near-winning cost-saving tradeoffs at `24 / 30` with one lost winning top10 hit.
- Duplicate `short75_225_top3_all_pm200` rows are handled explicitly as duplicates of `anchor_winning_top3_pm200`.

## Boundary

N10CM uses only fixed observable variants: short spans use before75/after225, selected top positions override to symmetric pmX all-span expansion, and gold is used only for evaluation. It does not use gold/outcome/miss-direction/content/file identity as policy input. Candidate pool/order is unchanged.

N10CM does not run retrieval/rerun/OpenLocus, candidate generation/add/remove/reorder, adaptive tuning, selector/reranker, P5, BEA-v1-A, runtime/default promotion, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Handoff

N10CM authorizes only `BEA-v1-N10CN Winning Hybrid Cost-Reduction Refinement Audit Package`, a public audit package with no additional private reads, recompute, or new variants.

## Artifact

- Script: `eval/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep.py`
- Report: `artifacts/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep_report.json`
