# BEA-v1-N10AX Cost-Sensitive Frontier Claim Package

日期：2026-06-29

BEA-v1-N10AX 是 N10AW cost-sensitive mechanism decomposition 以及 N10AV/N10AU/N10AS frontier evidence 的 public-only claim package。它只读取 public artifacts。它不读取 private rows，不 recompute metrics，不添加 variants，不进行 adaptive tuning，不运行 retrieval/reruns/OpenLocus，不生成或 materialize candidates，不 hook existing evaluators，也不改变 runtime/default behavior。

## 结果

```text
status: cost_sensitive_frontier_claim_package_complete_n10ay_authorized
self-test: 14 / 14
forbidden scan: pass
private reads: 0
recomputes: 0
new variants: 0
N10AY authorized: true
```

## Packaged frontier tiers

| Tier | top10/top20 span overlap | Cost bucket | Lost previous hits |
| --- | ---: | --- | ---: |
| baseline | 9 / 10 | zero | 0 |
| pm30 | 18 / 22 | low | 0 |
| before25_after75 | 20 / 24 | medium | 0 |
| pm75 | 21 / 25 | medium | 0 |
| pm200 | 25 / 30 | very_high | 0 |

## Packaged mechanism claim

Marginal gains 仍然是 before/after gold-window gap recovery：

- baseline -> pm30：+9，其中 8 个 before-gold-gap、1 个 after-gold-gap。
- pm30 -> before25_after75：+2，其中 2 个 before-gold-gap。
- before25_after75 -> pm75：+1，其中 1 个 after-gold-gap。
- pm75 -> pm200：+4，其中 3 个 before-gold-gap、1 个 after-gold-gap。

因此 N10AX 打包 N10AW interpretation：pm200 max-recall tier 是同一 before/after miss pattern 的更宽窗口恢复，而不是质变的 pm200 mechanism。

## Claim boundary

Allowed claim：scoped same-source N1 span-surface proxy cost-sensitive frontier summary。Forbidden claims 保持 false：heldout/generalization、N2-equivalent validation、runtime/default promotion、method winner、downstream value、selector/reranker、P5/BEA-v1-A、retrieval/rerun、candidate generation 与 adaptive tuning。

## Handoff

N10AX 只授权 `BEA-v1-N10AY Cost-Aware Adapter Frontier Smoke`：使用 same scoped N1 rows 且只导入 adapter/helper 的 direct empirical follow-up。N10AX 本身不授权 runtime/default changes 或 broader claims。

## Artifact

- Script: `eval/bea_v1_n10ax_cost_sensitive_frontier_claim_package.py`
- Report: `artifacts/bea_v1_n10ax_cost_sensitive_frontier_claim_package/bea_v1_n10ax_cost_sensitive_frontier_claim_package_report.json`
