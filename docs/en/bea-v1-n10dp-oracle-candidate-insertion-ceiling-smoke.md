# BEA-v1-N10DP Oracle Candidate-Insertion Ceiling Smoke

Date: 2026-06-30

BEA-v1-N10DP is a non-policy upper-bound smoke. It estimates the file-reach ceiling if a future source could add one anonymous gold-file candidate for cases where the gold file is absent from the observed pool. It does not run retrieval, rerun OpenLocus, generate or materialize real candidates, run selector/reranker logic, or change runtime/default behavior.

## Result

```text
status: oracle_candidate_insertion_ceiling_smoke_complete_n10dq_authorized
self-test: 12 / 12
forbidden scan: pass
private span rows read: 213
current suffix-safe top10/top20 file reach: 44 / 58
affected absent-pool cases: 141
rank1/rank5/rank10 oracle top10 file ceiling: 185 / 213
rank1/rank5/rank10 oracle top20 file ceiling: 199 / 213
append-after-top10 oracle top10/top20 ceiling: 44 / 199
span overlap status: not_evaluated_no_oracle_span
```

## Interpretation

Placing one anonymous oracle gold-file candidate within top10 for the 141 absent-pool cases raises top10 file reach from `44` to `185`. Appending after top10 leaves top10 unchanged but raises top20 file reach to `199`. Span utility is not evaluated because there is no real oracle span candidate, and N10DP does not fake span overlap.

## Boundary

This is an oracle ceiling, not a feasible policy or runtime/default recommendation. Public outputs are aggregate/bucket-only and contain no private paths, file names, spans, lines, snippets, gold labels, candidate lists, exact ranks, or raw rows.

## Handoff

N10DP authorizes only `BEA-v1-N10DQ Oracle Candidate-Insertion Ceiling Public Package`. It does not authorize retrieval, source acquisition, real candidate generation, selector/reranker execution, runtime/default changes, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10dp_oracle_candidate_insertion_ceiling_smoke.py`
- Report: `artifacts/bea_v1_n10dp_oracle_candidate_insertion_ceiling_smoke/bea_v1_n10dp_oracle_candidate_insertion_ceiling_smoke_report.json`
