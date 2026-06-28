# BEA-v1-N4 Fixed-Pool Rank-Blocker Denominator Audit

日期：2026-06-28

BEA-v1-N4 审计 committed public N1/N2/N3/P4L artifacts，判断 fixed-pool rank-blocker denominator 是否足以支持未来 fixed-pool、no-new-retrieval rank/order experiment preflight。

## 结果

```text
status: fixed_pool_rank_blocker_denominator_audit_pass_n5_authorized
self-test: 12 / 12
forbidden scan: pass
sanitized rank cases: 40
fixed-pool deeper-present cases: 40
top-10 miss but deeper-present cases: 40
N5 preflight authorized: true
```

该 audit 只使用 scanner-safe committed public artifacts。N2 提供 40 条 sanitized rank-blocked cases，均为 `rank_21_50`、top-50/top-100 deeper-pool recovery，且 blocker 为 `extra_depth_append_blocked`。N3 在同一批 anonymous case buckets 上提供 fixed-pool merge/order simulation signal。P4L 在 aggregate 层确认 locked 272-record denominator。

## 决策

该 fixed-pool denominator 只足以授权 **BEA-v1-N5 Fixed-Pool Rank-Order Experiment Preflight**。N5 仍然是 preflight-only，且必须使用 existing fixed pools；N4 不授权 new retrieval、reruns、selector/reranker execution、P5、BEA-v1-A、counterfactual execution、policy tuning、runtime/default promotion、method-winner 声明或 downstream-value 声明。

## Artifact

- Script：`eval/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit.py`
- Report：`artifacts/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit/bea_v1_n4_fixed_pool_rank_blocker_denominator_audit_report.json`
