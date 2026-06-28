# BEA-v1-N4 Fixed-Pool Rank-Blocker Denominator Audit

Date: 2026-06-28

BEA-v1-N4 audits committed public N1/N2/N3/P4L artifacts to decide whether the fixed-pool rank-blocker denominator is sufficient for a future fixed-pool, no-new-retrieval rank/order experiment preflight.

## Result

```text
status: fixed_pool_rank_blocker_denominator_audit_pass_n5_authorized
self-test: 12 / 12
forbidden scan: pass
sanitized rank cases: 40
fixed-pool deeper-present cases: 40
top-10 miss but deeper-present cases: 40
N5 preflight authorized: true
```

The audit uses only scanner-safe committed public artifacts. N2 provides 40 sanitized rank-blocked cases with `rank_21_50`, deeper-pool recovery at top-50/top-100, and `extra_depth_append_blocked`. N3 provides fixed-pool merge/order simulation signal over the same 40 anonymous case buckets. P4L confirms the locked 272-record denominator at aggregate level.

## Decision

The fixed-pool denominator is adequate for **BEA-v1-N5 Fixed-Pool Rank-Order Experiment Preflight** only. N5 remains preflight-only and must use existing fixed pools; N4 does not authorize new retrieval, reruns, selector/reranker execution, P5, BEA-v1-A, counterfactual execution, policy tuning, runtime/default promotion, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit.py`
- Report: `artifacts/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit_report.json`
