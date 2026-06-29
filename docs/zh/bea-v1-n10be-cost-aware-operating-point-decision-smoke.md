# BEA-v1-N10BE Cost-Aware Operating-Point Decision Smoke

日期：2026-06-29

BEA-v1-N10BE 是在 same scoped N1 span rows 上进行的 direct empirical research decision smoke。它只评估预声明的 budget buckets 与 named operating points。它不是 runtime/default recommendation，不是 method-winner claim，不是 heldout/generalization evidence，也不是 downstream-value evidence。

## 结果

```text
status: cost_aware_operating_point_decision_smoke_complete_n10bf_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
usable span rows: 213
N10BF authorized: true
```

## Budget decisions

| Budget bucket | Rule | Selected operating point | Variant | top10/top20 | Delta vs baseline | Cost proxy | Cost bucket |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| strict_budget | max cost <= 600 | low_cost | pm30 | 18 / 22 | +9 / +12 | 600 | low |
| moderate_budget | max cost <= 1000 | balanced | before25_after75 | 20 / 24 | +11 / +14 | 1000 | medium |
| recall_budget | max cost <= 4000 | max_recall | pm200 | 25 / 30 | +16 / +20 | 4000 | very_high |

Candidate pool 与 order 保持不变。Decision buckets 不使用 new window sizes，也没有 adaptive per-case selection。

## Boundary

N10BE 只是 same-source N1 span-surface proxy research decision smoke。它不推荐 runtime/default policy。它不授权 method-winner、downstream-value、heldout/generalization、retrieval/rerun、candidate generation/materialization、selector/reranker、P5/BEA-v1-A、new-variant 或 adaptive-selection claims。

## Handoff

N10BE 只授权 `BEA-v1-N10BF Cost-Aware Operating-Point Decision Smoke Audit Package`，这是 public package。它不授权额外 private reads、runtime/default recommendation、new variants、adaptive selection、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10be_cost_aware_operating_point_decision_smoke.py`
- Report: `artifacts/bea_v1_n10be_cost_aware_operating_point_decision_smoke/bea_v1_n10be_cost_aware_operating_point_decision_smoke_report.json`
