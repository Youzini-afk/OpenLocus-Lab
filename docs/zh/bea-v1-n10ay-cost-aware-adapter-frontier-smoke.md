# BEA-v1-N10AY Cost-Aware Adapter Frontier Smoke

日期：2026-06-29

BEA-v1-N10AY 是使用 default-off eval-only adapter path 对锁定 cost-sensitive frontier tiers 进行的 direct empirical smoke。它读取 same scoped N1 span rows 以及 public N10AX/N10AW/N10AV/N10AU/N10AS artifacts。它只导入 adapter/helper path，不导入或调用 existing validated evaluators，也不 hook runtime/default behavior。

## 结果

```text
status: cost_aware_adapter_frontier_smoke_pass_n10az_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
adapter imported: true
existing evaluator imported/called: false
runtime/default hook: false
```

## Adapter frontier results

| Variant | top10/top20 span overlap | Cost proxy | Match locked aggregate | Lost original hits |
| --- | ---: | ---: | --- | ---: |
| pm30 | 18 / 22 | 600 (`low`) | true | 0 |
| before25_after75 | 20 / 24 | 1000 (`medium`) | true | 0 |
| pm75 | 21 / 25 | 1500 (`medium`) | true | 0 |
| pm200 | 25 / 30 | 4000 (`very_high`) | true | 0 |

该 smoke 确认 eval-only adapter path 可以复现四个 predeclared frontier variants 的锁定 N10AW/N10AV frontier aggregates。Candidate pool 与 order 均保持不变。

## Boundaries

N10AY 只是 same-source N1 span-surface proxy evidence。它不是 heldout validation，不是 N2-equivalent validation，不是 runtime/default change，不是 selector/reranker result，不是 method-winner claim，也不是 downstream-value evidence。

## Handoff

N10AY 只授权 `BEA-v1-N10AZ Cost-Aware Adapter Frontier Smoke Result Audit Package`，该阶段为 public-only。它不授权 additional private reads、existing evaluator hook-in、runtime/default promotion、new variants、adaptive tuning、retrieval/rerun、candidate generation/materialization、selector/reranker execution、P5、BEA-v1-A、method-winner claims、downstream-value claims 或 heldout/generalization claims。

## Artifact

- Script: `eval/bea_v1_n10ay_cost_aware_adapter_frontier_smoke.py`
- Report: `artifacts/bea_v1_n10ay_cost_aware_adapter_frontier_smoke/bea_v1_n10ay_cost_aware_adapter_frontier_smoke_report.json`
