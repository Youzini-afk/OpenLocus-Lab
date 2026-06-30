# BEA-v1-N10DQ Oracle Candidate-Insertion Ceiling Public Package

Date: 2026-06-30

BEA-v1-N10DQ is a public-only package of the N10DP oracle candidate-insertion ceiling smoke. It reads public artifacts only and performs no private reads, recomputation, or oracle insertion.

## Result

```text
status: oracle_candidate_ceiling_public_package_complete_n10dr_authorized
self-test: 11 / 11
forbidden scan: pass
private reads in N10DQ: 0
recomputes in N10DQ: 0
oracle insertion executions in N10DQ: 0
N10DR authorized: future oracle-scoped canary only
```

## Packaged ceiling

- Current suffix-safe anchor file reach: top10/top20 `44 / 58`.
- Affected absent-pool cases: `141`.
- Oracle rank1/rank5/rank10 insertion ceiling: top10/top20 `185 / 199`, increment `+141 / +141` over anchor.
- Oracle append-after-top10 ceiling: top10/top20 `44 / 199`, increment `+0 / +141`.
- Span metric boundary: `not_evaluated_no_oracle_span`.

## Boundary

This is an upper-bound value signal for candidate-source acquisition, not a feasible policy, retrieval result, source-acquisition result, method winner, downstream-value claim, heldout/generalization claim, or runtime/default recommendation.

## Handoff

N10DQ authorizes only `BEA-v1-N10DR Real Candidate-Source Canary` under a future oracle/orchestrator contract. N10DQ itself does not authorize retrieval, rerun, source acquisition execution, real candidate generation, selector/reranker execution, P5, BEA-v1-A, runtime/default changes, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10dq_oracle_candidate_ceiling_public_package.py`
- Report: `artifacts/bea_v1_n10dq_oracle_candidate_ceiling_public_package/bea_v1_n10dq_oracle_candidate_ceiling_public_package_report.json`
