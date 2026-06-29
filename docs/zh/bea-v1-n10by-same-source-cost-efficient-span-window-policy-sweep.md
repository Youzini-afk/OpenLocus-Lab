# BEA-v1-N10BY Same-Source Cost-Efficient Span-Window Policy Sweep

日期：2026-06-29

BEA-v1-N10BY 是在同一个 scoped N1 span rows 上进行的 direct empirical same-source exploratory sweep。它只测试 12 个预声明 span-window policies，policy inputs 仅限 candidate rank position、fixed operating-point buckets 与 constant window sizes。Gold 只用于 evaluation。它不 add/remove/reorder candidates，不 retrieval，不 rerun，不 adaptive tuning，也不作 runtime/default、heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: same_source_cost_efficient_span_window_policy_sweep_complete_n10bz_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
variant count: 12
cost-reduction successes: 0
recall-improvement successes: 0
best observed variant: anchor_cost80_before20_after60
best observed top10/top20: 20 / 24
N10BZ authorized: true
```

## Key findings

- Anchor `cost80_before20_after60` 仍为 20/24，top10 cost proxy 为 800。
- 固定 lower-cost variants 70/72/75/78 都为 19/23，并丢失一个 anchor top10 hit。
- Rank-conditioned top-5/top-10 policies 降低 aggregate cost，但结果为 19/20。
- Top-10-only expansion 保持 top10 20，但 top20 降至 21。
- Top-20-only expansion 匹配 anchor 20/24，但没有降低 top10 cost。
- 所有测试 variant 都未满足 cost-reduction 或 recall-improvement success buckets；12 个全部归类为 `no_improvement_anchor_retained`。

## Boundary

N10BY 仅为 same-source exploratory。它不是 heldout validation，不是 runtime/default policy，不是 method winner，也不是 downstream-value evidence。

## Handoff

N10BY 只授权 `BEA-v1-N10BZ Same-Source Cost-Efficient Policy Sweep Audit Package`，即 public audit/package。它不授权 further private reads、extra sweeps、new variants、adaptive tuning、runtime/default promotion、retrieval/rerun、candidate generation、selector/reranker execution、P5、BEA-v1-A、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep.py`
- Report: `artifacts/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep_report.json`
