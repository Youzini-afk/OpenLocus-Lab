# BEA-v1-N9 Recovered Fixed-Pool Result Replication Package

Date: 2026-06-29

BEA-v1-N9 is a public replication and claim-boundary package for the recovered fixed-pool rank-order result. It reads only public N6XFR-E, N7, N8, N5, and N6F artifacts. It does not read or scan private storage, recompute outcomes, rerun retrieval, generate candidates, add arms, run selector/reranker logic, enter P5/BEA-v1-A, or promote runtime/default behavior.

## Result

```text
status: recovered_fixed_pool_result_replication_package_complete
self-test: 15 / 15
forbidden scan: pass
case count: 40
arm count: 4
public rows: 160
best arm: extra_depth_promote_before_primary_prefix_4
best top10 recovery: 25 / 40
best top20 recovery: 34 / 40
regressions: 0
threshold passed: true
```

## Replication chain

- N6XFR-E produced the recovered fixed-pool result over the recovered 40-case denominator.
- N7 audited the public N6XFR-E result and authorized independent recompute.
- N8 independently recomputed the same private rows and same four arms, matching N6XFR-E per-arm top-10, top-20, and regression counts.
- N9 packages the public replication chain and claim boundary without new empirical execution.

## Required private input for recompute

Recomputing the result still requires the same recovered N2 rank-pack rows in ignored project-private storage. Those rows are not committed, their path/name/content are not public, and N9 does not read them.

## Limitations

- Single recovered 40-case denominator.
- Private local rows are required for recompute.
- Not validated on a broader denominator.
- Not a runtime/default policy.
- Not a selector/reranker result.
- Not downstream-value evidence.
- Arm semantics depend on the rank<=20 primary / rank>20 extra-depth decomposition.

## Decision

N9 authorizes only `BEA-v1-N10 Broader Frozen Denominator Validation Preflight`. It does not authorize capture, private reads, recompute, retrieval, reruns, new-arm search, selector/reranker execution, P5, BEA-v1-A, runtime/default promotion, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n9_recovered_fixed_pool_result_replication_package.py`
- Report: `artifacts/bea_v1_n9_recovered_fixed_pool_result_replication_package/bea_v1_n9_recovered_fixed_pool_result_replication_package_report.json`
