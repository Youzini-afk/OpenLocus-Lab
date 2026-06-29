# BEA-v1-N10CF Span-Shape Gated Refinement Audit Package

Date: 2026-06-29

BEA-v1-N10CF is a public-only audit/package for the N10CE span-shape gated refinement sweep. It reads public artifacts only and performs no private reads, no recompute, and no new variants.

## Result

```text
status: span_shape_refinement_package_complete_n10cg_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10CF: 0
recomputes in N10CF: 0
N10CG authorized: true
```

## Packaged refinement facts

- N10CE completed with 12 predeclared variants.
- Policy inputs were only observable original span-length bucket and candidate-position bucket.
- Gold/outcome/miss direction/file identity/content were not used as policy inputs.
- Cost80 all-spans anchor: `20 / 24`, cost10/cost20 `800 / 1600`.
- Short50/150 anchor: `22 / 27`, cost10/cost20 `2000 / 4000`.
- pm200 all-spans global best: `25 / 30`, cost10/cost20 `4000 / 8000`.

Short-only ladder:

| Variant | top10/top20 | cost10/cost20 | Decision |
| --- | ---: | ---: | --- |
| short_only_before30_after90 | 20 / 24 | 1200 / 2400 | anchor_retained_no_improvement |
| short_only_before40_after120 | 21 / 25 | 1600 / 3200 | anchor_retained_no_improvement |
| short_only_before45_after135 | 21 / 26 | 1800 / 3600 | anchor_retained_no_improvement |
| short_only_before50_after150 | 22 / 27 | 2000 / 4000 | anchor_retained_no_improvement |
| short_only_before60_after180 | 23 / 27 | 2400 / 4800 | recall_improves_short_anchor |
| short_only_before75_after225 | 24 / 30 | 3000 / 6000 | recall_improves_short_anchor |

`short_only_before75_after225` is the best short-span-gated frontier point, but not the global best; pm200 remains the global same-source top10/top20 maximum. No cheaper variant preserved the short50/150 anchor. `recall_improves_short_anchor_count=2` for 60/180 and 75/225.

## Boundary

This package is same-source N1 proxy evidence only. It is not heldout/generalization evidence, not runtime/default behavior, not retrieval/rerun, not candidate generation, not cluster/bridge, not adaptive tuning, not a selector/reranker result, not P5/BEA-v1-A, and not a method/downstream claim.

## Handoff

N10CF authorizes only `BEA-v1-N10CG Span-Shape Mechanism Follow-up`: investigate the gap between short75/225 (`24 / 30`) and pm200 (`25 / 30`) or opportunities to preserve `24 / 30` cheaper, using fixed/predeclared observable rules on the same scoped rows.

## Artifact

- Script: `eval/bea_v1_n10cf_span_shape_refinement_audit_package.py`
- Report: `artifacts/bea_v1_n10cf_span_shape_refinement_audit_package/bea_v1_n10cf_span_shape_refinement_audit_package_report.json`
