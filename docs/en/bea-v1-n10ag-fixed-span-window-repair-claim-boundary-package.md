# BEA-v1-N10AG Fixed Span-Window Repair Claim-Boundary Audit Package

Date: 2026-06-29

BEA-v1-N10AG is a public-only claim-boundary package after N10AF. It reads committed public N10AB, N10AC, N10AD, N10AE, N10AF, N10X, and N10Z artifacts. It performs no private reads, no private scans, and no metric recomputation.

## Result

```text
status: fixed_span_window_repair_claim_boundary_package_complete_n10ah_authorized
self-test: 15 / 15
forbidden scan: pass
denominator: 213
baseline top10 span overlap: 9
pm50 top10 span overlap: 19
pm50 top20 span overlap: 23
pm50 delta top10: +10
pm50 original span-hit loss: 0
pm20 top10 span overlap: 15
pm100 top10 span overlap: 21
N10AD aggregate match: true
N10AD N10AB code call count: 0
N10AF positive-delta subgroups: 7
N10AF baseline-hit negative-delta subgroups: 0
```

## Locked claim boundary

Allowed claim: scoped N1 span-surface fixed-pool pm50 span-window repair smoke/robustness pass.

Forbidden claims remain forbidden: runtime/default promotion, method winner, downstream value, P5/BEA-v1-A, broad generalization, selector/reranker, retrieval/rerun, candidate generation, gold-as-policy, and adaptive tuning.

## Motivation chain

N10X showed the unexpanded span-level proxy was below threshold. N10Z decomposed the gap as same-file span-window misalignment. N10AA defined a fixed, gold-free pm50 repair. N10AB passed the direct smoke, N10AC audited it, N10AD independently recomputed it, N10AE packaged replication, and N10AF passed subgroup robustness.

## Decision

N10AG authorizes only `BEA-v1-N10AH Default-Off Implementation Feasibility Preflight`, with scope `default_off_implementation_feasibility_preflight_only`. It does not authorize actual runtime implementation, runtime/default promotion, private reads, retrieval/reruns, candidate generation/materialization, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package.py`
- Report: `artifacts/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package_report.json`
