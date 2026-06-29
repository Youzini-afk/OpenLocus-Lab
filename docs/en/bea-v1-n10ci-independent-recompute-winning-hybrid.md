# BEA-v1-N10CI Independent Recompute of Winning Hybrid

Date: 2026-06-29

BEA-v1-N10CI independently recomputes the N10CG winning hybrid strategy `short75_225_top3_all_pm200` over the same scoped N1 span rows. It does not import or call the N10CG evaluator and does not reuse N10CG transform functions.

## Result

```text
status: winning_hybrid_independent_recompute_pass_n10cj_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
top10/top20 span overlap: 25 / 31
cost10/cost20: 3300 / 6300
lost short75/225 hits: 0
N10CG code call count: 0
N10CJ authorized: true
```

## Independent semantics

N10CI recomputes the same evidence order and candidate pool from the private N1 span rows. For each evidence position:

- short original span (`<=10` lines): expand before `75`, after `225`;
- top3 evidence positions: use all-span pm200 (`200 / 200`) regardless of span length;
- otherwise: no expansion.

Gold is used only for evaluation after projection. Candidate add/remove/reorder does not occur.

## Match to N10CG/N10CH

The independent aggregate exactly matches the public N10CG/N10CH package for `short75_225_top3_all_pm200`: `25 / 31`, cost10/cost20 `3300 / 6300`, and lost short75/225 hits `0`.

## Boundary

This remains same-source N1 proxy evidence only. N10CI does not authorize runtime/default promotion, heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/reorder, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Handoff

N10CI authorizes only `BEA-v1-N10CJ Winning Hybrid Replication Package`, a public package with no additional private reads.

## Artifact

- Script: `eval/bea_v1_n10ci_independent_recompute_winning_hybrid.py`
- Report: `artifacts/bea_v1_n10ci_independent_recompute_winning_hybrid/bea_v1_n10ci_independent_recompute_winning_hybrid_report.json`
