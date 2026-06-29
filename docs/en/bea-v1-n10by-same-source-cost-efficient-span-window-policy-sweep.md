# BEA-v1-N10BY Same-Source Cost-Efficient Span-Window Policy Sweep

Date: 2026-06-29

BEA-v1-N10BY is a direct empirical same-source exploratory sweep over the same scoped N1 span rows. It tests exactly 12 predeclared span-window policies using only candidate rank position, fixed operating-point buckets, and constant window sizes. Gold is used only for evaluation. It does not add/remove/reorder candidates, retrieve, rerun, tune adaptively, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

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

- The anchor `cost80_before20_after60` remains 20/24 with top10 cost proxy 800.
- The fixed lower-cost variants at 70/72/75/78 all produce 19/23 and lose one anchor top10 hit.
- Rank-conditioned top-5/top-10 policies reduce aggregate cost but produce 19/20.
- Top-10-only expansion preserves top10 20 but drops top20 to 21.
- Top-20-only expansion matches the anchor 20/24 but does not reduce top10 cost.
- No tested variant satisfies the cost-reduction or recall-improvement success buckets; all 12 are classified as `no_improvement_anchor_retained`.

## Boundary

N10BY is same-source exploratory only. It is not heldout validation, not runtime/default policy, not a method winner, and not downstream-value evidence.

## Handoff

N10BY authorizes only `BEA-v1-N10BZ Same-Source Cost-Efficient Policy Sweep Audit Package`, a public audit/package. It does not authorize further private reads, extra sweeps, new variants, adaptive tuning, runtime/default promotion, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep.py`
- Report: `artifacts/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep_report.json`
