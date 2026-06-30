# BEA-v1-N10DN No-Duplicate-Pressure Deep-Rank Promotion Public Package

日期：2026-06-30

BEA-v1-N10DN 是 N10DM 的 public-only package/audit。它只读取 committed public artifacts，不进行 private reads、recompute、retrieval/rerun、candidate generation/materialization/add/remove、selector/reranker execution 或 runtime/default change。

## 结果

```text
status: no_duplicate_pressure_deep_rank_promotion_public_package_complete_n10do_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10DN: 0
recomputes in N10DN: 0
N10DO authorized: true
```

## Packaged N10DM facts

- N10T anchor file top10/top20：`34 / 44`。
- N10T projected span top10/top20：`30 / 36`。
- N10DM 评估了 6 个 variants；5 个 gated promotion variants 只在 top10 duplicate pressure 为 none 时激活。
- Positive variants：`0`。
- Harmful variants：`5`。
- 最好的非 anchor interleave variants 降至 file `29 / 44` 与 projected span `26 / 36`。
- Direct promotion 最多可恢复 `5` 个 rank11-20 residuals，但会丢失最多 `14` 个 anchor file top10 hits 与 `10` 个 anchor span top10 hits。

## 结论

除非出现新的 observable signal，否则 fixed deep-rank promotion line 已关闭。该 negative result 仍然有价值：reachable residuals 不足以支持 blind 或 duplicate-pressure-none gated deep-rank promotion，因为 anchor harm 大于 recovered residuals。

## Handoff

N10DN 只授权 `BEA-v1-N10DO Candidate-Pool Absence Source Acquisition Mechanism Audit`，聚焦 161 个 absent-from-pool residuals。它不授权 runtime/default、heldout/generalization、retrieval/rerun、candidate generation/materialization/add/remove、selector/reranker、P5、BEA-v1-A、adaptive tuning、method-winner claims、downstream-value claims、broad private reads 或 further fixed deep-rank promotion。

## Artifact

- Script: `eval/bea_v1_n10dn_no_duplicate_pressure_deep_rank_promotion_public_package.py`
- Report: `artifacts/bea_v1_n10dn_no_duplicate_pressure_deep_rank_promotion_public_package/bea_v1_n10dn_no_duplicate_pressure_deep_rank_promotion_public_package_report.json`
