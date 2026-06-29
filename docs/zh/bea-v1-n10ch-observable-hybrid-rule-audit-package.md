# BEA-v1-N10CH Observable Hybrid Span-Shape Rule Sweep Audit Package

日期：2026-06-29

BEA-v1-N10CH 是 N10CG positive observable hybrid span-shape rule sweep 的 public-only audit/package。它只读取 public artifacts，不进行 private reads、不 recompute，也不添加 new variants。

## 结果

```text
status: observable_hybrid_rule_package_complete_n10ci_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10CH: 0
recomputes in N10CH: 0
N10CI authorized: true
```

## Packaged facts

- N10CG 已完成，包含 12 个 predeclared variants。
- `anchor_short75_225`：`24 / 30`，cost10/cost20 `3000 / 6000`。
- `anchor_pm200_all_spans`：`25 / 30`，cost10/cost20 `4000 / 8000`。
- `short75_225_top3_all_pm200`：`25 / 31`，cost10/cost20 `3300 / 6300`，相对 pm200 节省 `700 / 1700`，lost short75 hits `0`，decision `recovers_pm200_at_lower_cost`。
- `short75_225_top5_all_pm200`：`25 / 31`，cost10/cost20 `3500 / 6500`，相对 pm200 节省 `500 / 1500`，lost short75 hits `0`，decision `recovers_pm200_at_lower_cost`。
- `short75_225_top10_all_pm200` 也达到 `25 / 31`，但没有节省 top10 cost，因此正确地不计为 success。
- Medium/long targeted expansions 保持 `24 / 30`，但没有进一步改善。

## Boundary

Policy inputs 仅为 observable span-length bucket 与 candidate-position bucket。Gold、outcome、miss direction、file identity 与 content 均未使用。Candidate pool/order 保持不变。这只是 same-source exploratory evidence：不是 heldout/generalization，不是 runtime/default，不是 retrieval/rerun，不是 candidate generation，不是 cluster/bridge，不是 adaptive tuning，也不是 method/downstream claim。

## Handoff

N10CH 只授权 N10CI 对新 candidate strategy `short75_225_top3_all_pm200` 进行 independent recompute 或 adapter smoke。它不授权 runtime/default promotion、heldout/generalization claims、retrieval/rerun、candidate generation/add/remove/reorder、cluster/bridge execution、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10ch_observable_hybrid_rule_audit_package.py`
- Report: `artifacts/bea_v1_n10ch_observable_hybrid_rule_audit_package/bea_v1_n10ch_observable_hybrid_rule_audit_package_report.json`
