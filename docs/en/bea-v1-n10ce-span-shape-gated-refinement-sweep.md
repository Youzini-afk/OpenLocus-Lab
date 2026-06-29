# BEA-v1-N10CE Span-Shape Gated Refinement Sweep

Date: 2026-06-29

BEA-v1-N10CE is a direct empirical same-source refinement of the N10CC short-span gated expansion signal. It reads the same scoped N1 span rows and uses only observable original span-length and candidate-position buckets as policy inputs. Gold is used only for evaluation.

## Result

```text
status: span_shape_gated_refinement_sweep_complete_n10cf_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
variant count: 12
cheaper-preserves-short-anchor variants: 0
recall-improves-short-anchor variants: 2
N10CF authorized: true
```

## Key findings

Anchors:

- `anchor_cost80_all_spans_before20_after60`: `20 / 24`, cost10/cost20 `800 / 1600`.
- `anchor_short_only_before50_after150`: `22 / 27`, cost10/cost20 `2000 / 4000`.
- `anchor_pm200_all_spans_before200_after200`: `25 / 30`, cost10/cost20 `4000 / 8000`.

Refinement results show a smooth short-span cost/recall ladder:

- `short_only_before30_after90`: `20 / 24`, cost10 `1200`.
- `short_only_before40_after120`: `21 / 25`, cost10 `1600`.
- `short_only_before45_after135`: `21 / 26`, cost10 `1800`.
- `short_only_before50_after150`: `22 / 27`, cost10 `2000`.
- `short_only_before60_after180`: `23 / 27`, cost10 `2400`, decision `recall_improves_short_anchor`.
- `short_only_before75_after225`: `24 / 30`, cost10 `3000`, decision `recall_improves_short_anchor`.
- `short_medium_before40_after120`: `21 / 25`, cost10 `1600`.

No variant preserved the short50/150 anchor at a lower cost. Two variants improved the short anchor before pm200 cost: `short_only_before60_after180` and `short_only_before75_after225`.

## Boundary

N10CE did not use gold/outcome/miss direction/file identity/content as policy inputs. It did not reorder, add, or remove candidates; did not run retrieval/rerun/OpenLocus; did not execute cluster/bridge logic; and did not tune adaptively. This is same-source exploratory research only, not heldout evidence, not runtime/default behavior, and not a method/downstream claim.

## Handoff

N10CE authorizes only `BEA-v1-N10CF Span-Shape Gated Refinement Audit Package`, a public audit/package. It does not authorize private reads, new variants, runtime/default promotion, heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/reorder, cluster/bridge execution, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10ce_span_shape_gated_refinement_sweep.py`
- Report: `artifacts/bea_v1_n10ce_span_shape_gated_refinement_sweep/bea_v1_n10ce_span_shape_gated_refinement_sweep_report.json`
