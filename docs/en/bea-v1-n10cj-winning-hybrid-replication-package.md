# BEA-v1-N10CJ Winning Hybrid Public Replication Package

Date: 2026-06-29

BEA-v1-N10CJ is a public-only replication package for the N10CG/N10CH/N10CI winning hybrid chain. It reads public artifacts only and performs no private reads, no recompute, and no new variants.

## Result

```text
status: winning_hybrid_replication_package_complete_n10ck_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10CJ: 0
recomputes in N10CJ: 0
N10CK authorized: true
```

## Replicated winning hybrid

Winning hybrid: `short75_225_top3_all_pm200`.

- N10CG result: `25 / 31`, cost10/cost20 `3300 / 6300`, savings vs pm200 `700 / 1700`, lost short75/225 hits `0`.
- N10CI independent recompute: exact match at `25 / 31`, cost10/cost20 `3300 / 6300`, lost short75/225 hits `0`.
- Candidate pool/order unchanged.
- N10CI did not import, call, or reuse N10CG evaluator code; N10CG code call count was `0`.

## Policy rule boundary

The policy rule uses only observable original span-length bucket and candidate-position bucket: short-span broad expansion plus top3 all-span pm200. It does not use gold, outcome, miss direction, file identity, or content as policy inputs.

## Claim boundary

This remains same-source N1 proxy evidence only. It is not heldout/generalization evidence, not runtime/default behavior, not retrieval/rerun, not candidate generation, not adaptive tuning, not P5/BEA-v1-A, and not a method/downstream claim.

## Handoff

N10CJ authorizes only `BEA-v1-N10CK Default-Off Adapter Smoke for Winning Hybrid`. It does not authorize runtime/default enablement, existing evaluator hook-in, heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/reorder, adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10cj_winning_hybrid_replication_package.py`
- Report: `artifacts/bea_v1_n10cj_winning_hybrid_replication_package/bea_v1_n10cj_winning_hybrid_replication_package_report.json`
