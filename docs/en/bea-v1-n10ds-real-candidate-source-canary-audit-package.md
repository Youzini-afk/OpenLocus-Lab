# BEA-v1-N10DS Real Candidate-Source Canary Audit Package

Date: 2026-06-30

BEA-v1-N10DS is a public-only audit/package of the N10DR bounded local candidate-source canary. It reads only the public N10DR artifact and performs no private reads, recomputation, retrieval, or candidate generation.

## Result

```text
status: real_candidate_source_canary_audit_package_complete_n10dt_authorized
self-test: 10 / 10
forbidden scan: pass
private reads in N10DS: 0
recomputes in N10DS: 0
N10DT authorized: true
```

## Packaged canary facts

- N10DR sampled and executed `30` cases with `30` local repositories available.
- Local retrieval command successes: `28`.
- Nonzero-candidate cases: `20`.
- Gold file recovered top10/top20/top50: `0 / 0 / 0`.
- Tiny, moderate, and rich-wrong pool buckets each recovered `0 / 10` cases.

## Interpretation

This is a valid negative canary, not an infrastructure failure. The bounded local source produced no recovery on the sampled corrected absent-pool residuals, so the source should not be scaled directly without failure-mechanism analysis.

## Handoff

N10DS authorizes only `BEA-v1-N10DT Real Candidate-Source Canary Failure Mechanism Analysis`. It does not authorize scaled retrieval, network access, git clone, candidate generation/materialization, selector/reranker execution, runtime/default changes, P5, BEA-v1-A, method-winner claims, downstream-value claims, heldout/generalization claims, or broad private reads.

## Artifact

- Script: `eval/bea_v1_n10ds_real_candidate_source_canary_audit_package.py`
- Report: `artifacts/bea_v1_n10ds_real_candidate_source_canary_audit_package/bea_v1_n10ds_real_candidate_source_canary_audit_package_report.json`
