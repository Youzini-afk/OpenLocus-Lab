# BEA-v1-N10CD Observable Span-Shape Gated Expansion Audit Package

Date: 2026-06-29

BEA-v1-N10CD is a public-only audit/package for the N10CC observable span-shape gated expansion smoke. It reads public artifacts only. It performs no private reads, no recompute, no new variants, no adaptive tuning, no retrieval/rerun/OpenLocus execution, no candidate generation/add/remove/reorder, no cluster/bridge execution, and no runtime/default promotion.

## Result

```text
status: observable_span_shape_package_complete_n10ce_authorized
self-test: 15 / 15
forbidden scan: pass
private reads in N10CD: 0
recomputes in N10CD: 0
N10CE authorized: true
```

## Packaged N10CC facts

- N10CC completed with 12 predeclared variants.
- Policy inputs were only observable original evidence span-length bucket and candidate position bucket.
- Gold/outcome, file identity, content/snippets, and before/after direction were not used as policy inputs.
- Anchor `anchor_cost80_all_spans_before20_after60`: top10/top20 `20 / 24`, cost10 `800`, cost20 `1600`.
- Anchor `anchor_pm200_all_spans_before200_after200`: top10/top20 `25 / 30`, cost10 `4000`, cost20 `8000`.

Positive same-source variants:

| Variant | top10/top20 | cost10/cost20 | lost anchor | Decision |
| --- | ---: | ---: | ---: | --- |
| short_only_before50_after150 | 22 / 27 | 2000 / 4000 | 0 | recall_improves_anchor |
| short_medium_before50_after150 | 22 / 27 | 2000 / 4000 | 0 | recall_improves_anchor |
| top10_short_only_before50_after150 | 22 / 23 | 2000 / 2000 | 0 | recall_improves_anchor |
| anchor_pm200_all_spans_before200_after200 | 25 / 30 | 4000 / 8000 | 0 | recall_improves_anchor |

Summary: `cost_efficient_preserve_anchor_count=0`; `recall_improves_anchor_count=4`. This is a new same-source exploratory positive signal: large expansion gated by observable short span shape improves over cost80 at lower cost than pm200 all-spans, but it is not heldout/generalization evidence, not runtime/default behavior, and not a method-winner claim.

## Handoff

N10CD authorizes only `BEA-v1-N10CE Span-Shape Refinement Sweep`: continue refining the short-span gated large-expansion cost/benefit boundary on the same scoped N1 rows with fixed/predeclared variants only. It does not authorize runtime/default promotion, heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/reorder, cluster/bridge execution, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10cd_observable_span_shape_audit_package.py`
- Report: `artifacts/bea_v1_n10cd_observable_span_shape_audit_package/bea_v1_n10cd_observable_span_shape_audit_package_report.json`
