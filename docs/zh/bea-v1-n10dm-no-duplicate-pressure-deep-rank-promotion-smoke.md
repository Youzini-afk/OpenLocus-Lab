# BEA-v1-N10DM No-Duplicate-Pressure Deep-Rank Promotion Smoke

日期：2026-06-30

BEA-v1-N10DM 是针对 scoped N1 span rows 的 direct empirical same-source smoke。它只在 top10 duplicate pressure 不存在时激活 fixed deeper-rank promotion variants；否则保持 N10T order 不变。Gold 仅用于 scoring，绝不作为 policy input。

## 结果

```text
status: no_duplicate_pressure_deep_rank_promotion_smoke_complete_n10dn_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
variant count: 6
anchor file top10/top20: 34 / 44
anchor projected span top10/top20: 30 / 36
N10DN authorized: true
```

## Findings

六个 fixed variants 均已完成，包括 N10T anchor 与五个 no-duplicate-pressure promotions。Public metrics 只报告 aggregate/bucket counts：file reach、projected span reach、相对 anchor 的 delta、recovered reachable residuals、activation counts 与 harm counts。Candidate pool membership 不变，candidate add/remove/materialization counts 保持为零。

## Boundary

N10DM 不运行 retrieval/rerun/OpenLocus，不生成/materialize/add/remove candidates，不运行 selector/reranker logic，不改变 runtime/default behavior，也不作 heldout/generalization、method-winner 或 downstream claims。Public artifact 不包含 private paths、filenames、exact ranks、spans、snippets、lines、candidate lists 或 gold labels。

## Handoff

N10DM 只授权 `BEA-v1-N10DN No-Duplicate-Pressure Deep-Rank Promotion Public Package`。

## Artifact

- Script: `eval/bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke.py`
- Report: `artifacts/bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke/bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke_report.json`
