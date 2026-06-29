# BEA-v1-N10CG Observable Hybrid Span-Shape Rule Sweep

Date: 2026-06-29

BEA-v1-N10CG is a direct empirical same-source sweep testing whether fixed observable hybrid span-shape rules can close the gap between `short75/225` and pm200 all-spans. It reads the same scoped N1 span rows only and uses only original span-length bucket and candidate-position bucket as policy inputs.

## Result

```text
status: observable_hybrid_span_shape_rule_sweep_complete_n10ch_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
variant count: 12
recovers pm200 at lower cost: 2
improves short frontier below pm200: 0
N10CH authorized: true
```

## Key findings

Anchors:

- `anchor_short75_225`: `24 / 30`, cost10/cost20 `3000 / 6000`.
- `anchor_pm200_all_spans`: `25 / 30`, cost10/cost20 `4000 / 8000`.

Two fixed observable hybrid variants recover or exceed the pm200 aggregate at lower cost:

- `short75_225_top3_all_pm200`: `25 / 31`, cost10/cost20 `3300 / 6300`, savings vs pm200 `700 / 1700`.
- `short75_225_top5_all_pm200`: `25 / 31`, cost10/cost20 `3500 / 6500`, savings vs pm200 `500 / 1500`.

Other medium/long hybrid variants retained the `24 / 30` short75/225 anchor at cost10/cost20 `3000 / 6000`. `short75_225_top10_all_pm200` reached `25 / 31` but did not reduce top10 cost below pm200, so it is not counted as lower-cost recovery.

## Boundary

Policy inputs were limited to original span-length buckets (`short`, `medium`, `long`) and candidate-position buckets (`top3`, `top5`, `top10`, or all positions). N10CG did not use gold/outcome/miss direction/file identity/content as policy inputs; did not reorder/add/remove candidates; did not run retrieval/rerun/OpenLocus; did not run cluster/bridge logic; and did not tune adaptively. This is same-source exploratory evidence only, not heldout/generalization evidence, not runtime/default behavior, and not a method/downstream claim.

## Handoff

N10CG authorizes only `BEA-v1-N10CH Observable Hybrid Span-Shape Rule Sweep Audit Package`, a public audit/package. It does not authorize private reads, new variants, runtime/default promotion, heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/reorder, cluster/bridge execution, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep.py`
- Report: `artifacts/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep_report.json`
