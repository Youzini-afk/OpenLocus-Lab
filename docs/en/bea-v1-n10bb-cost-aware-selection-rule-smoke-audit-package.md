# BEA-v1-N10BB Cost-Aware Span-Window Selection Rule Smoke Audit Package

Date: 2026-06-29

BEA-v1-N10BB is a public-only audit/package for the N10BA cost-aware span-window selection rule smoke. It reads public artifacts only. It does not read private rows, recompute metrics, add variants, tune adaptively, run retrieval/reruns/OpenLocus, generate/materialize candidates, hook existing evaluators, or change runtime/default behavior.

## Result

```text
status: cost_aware_selection_rule_smoke_audit_package_complete_n10bc_authorized
self-test: 16 / 16
forbidden scan: pass
private reads in N10BB: 0
recomputes in N10BB: 0
N10BC authorized: true
```

## Packaged operating points

| Operating point | Variant | top10/top20 span overlap | Delta top10/top20 vs baseline | Cost proxy | Lost previous hits |
| --- | --- | ---: | ---: | ---: | ---: |
| low_cost | pm30 | 18 / 22 | +9 / +12 | 600 (`low`) | 0 |
| balanced | before25_after75 | 20 / 24 | +11 / +14 | 1000 (`medium`) | 0 |
| max_recall | pm200 | 25 / 30 | +16 / +20 | 4000 (`very_high`) | 0 |

All packaged operating points preserve candidate pool and order. The rule boundary remains named operating points only, not defaults; there is no adaptive per-case selection and no new variant.

## Adapter and claim boundary

N10BB confirms the N10BA adapter/helper-only path: no existing evaluator import/call/hook-in and no runtime/default hook. The package is same-source N1 span-surface proxy evidence only. It makes no heldout/generalization, N2-equivalent, runtime/default, method-winner, downstream-value, selector/reranker, P5/BEA-v1-A, retrieval/rerun, candidate-generation, new-variant, or adaptive-selection claim.

## Handoff

N10BB authorizes only `BEA-v1-N10BC Operating-Point Tradeoff Decomposition`: same scoped N1 span rows, no new variants, and public bucket/count output over low_cost, balanced, and max_recall operating points. N10BB itself is public-only and performs no private read or recompute.

## Artifact

- Script: `eval/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package.py`
- Report: `artifacts/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package_report.json`
