# BEA-v1-N10AZ Cost-Aware Adapter Frontier Smoke Result Audit Package

日期：2026-06-29

BEA-v1-N10AZ 是 N10AY cost-aware adapter frontier smoke 的 public-only audit/package。它只读取 public N10AY/N10AX/N10AW/N10AV artifacts。它不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成或 materialize candidates，不 hook existing evaluators，也不改变 runtime/default behavior。

## 结果

```text
status: cost_aware_adapter_frontier_smoke_audit_package_complete_n10ba_authorized
self-test: 15 / 15
forbidden scan: pass
private reads in N10AZ: 0
recomputes in N10AZ: 0
N10BA authorized: true
```

## Audited adapter boundary

- N10AY status 为 pass。
- Adapter/helper import 为 true。
- Existing evaluator imported、called 或 hook-in 均为 false。
- Runtime/default hook 为 false。
- N10AY 使用 same scoped input row count：213。

## Audited frontier metrics

| Operating point | Variant | top10/top20 span overlap | Cost proxy | Candidate pool/order changed | Lost original hits |
| --- | --- | ---: | ---: | --- | ---: |
| low cost | pm30 | 18 / 22 | 600 (`low`) | false | 0 |
| balanced | before25_after75 | 20 / 24 | 1000 (`medium`) | false | 0 |
| balanced reference | pm75 | 21 / 25 | 1500 (`medium`) | false | 0 |
| max recall | pm200 | 25 / 30 | 4000 (`very_high`) | false | 0 |

## Claim boundary

Allowed claim：default-off eval-only adapter/helper path 复现 locked same-source N1 proxy frontier aggregates。Forbidden claims 保持 false：runtime/default promotion、heldout/generalization、N2-equivalent validation、method-winner/downstream value、selector/reranker、P5/BEA-v1-A、retrieval/rerun、candidate generation、new variants 与 adaptive tuning。

## Handoff

N10AZ 只授权 `BEA-v1-N10BA Cost-Aware Span-Window Selection Rule Smoke`：same scoped rows，不增加 new window sizes，只使用 predeclared operating points（`pm30` low-cost、`before25_after75` balanced、`pm200` max-recall），且不进行 adaptive per-case selection。N10AZ 不授权 runtime/default behavior 或 broader claims。

## Artifact

- Script: `eval/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package.py`
- Report: `artifacts/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package_report.json`
