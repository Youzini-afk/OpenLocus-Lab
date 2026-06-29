# BEA-v1-N10CM Winning Hybrid Cost-Reduction Refinement Sweep

日期：2026-06-29

BEA-v1-N10CM 是针对 winning hybrid `short75_225_top3_all_pm200` 的 direct empirical same-source refinement sweep。它在 same scoped N1 span rows 上，仅用 fixed observable variants 测试是否能以更低成本保持 `25 / 31`，或进一步提升结果。

## 结果

```text
status: winning_hybrid_cost_reduction_refinement_sweep_complete_n10cn_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
variant count: 12
winning reference: 25 / 31 at cost10/cost20 3300 / 6300
preserves winning at lower cost: 1
improves winning: 0
near winning cost-saving tradeoffs: 7
N10CN authorized: true
```

## Key findings

- `short75_225_top2_all_pm200` 以更低成本保持 winning `25 / 31`：cost10/cost20 `3200 / 6200`，相对 winning top3 pm200 规则节省 `100 / 100`。
- 没有 variant 超过 winning `25 / 31` top10/top20 span-overlap 结果。
- 7 个 variants 是 near-winning cost-saving tradeoffs：`24 / 30`，且 lost winning top10 hit 为 1。
- 重复的 `short75_225_top3_all_pm200` rows 被显式标记为 `anchor_winning_top3_pm200` 的 duplicates。

## Boundary

N10CM 只使用 fixed observable variants：short spans 使用 before75/after225，selected top positions 覆盖为 symmetric pmX all-span expansion，gold 仅用于 evaluation。它不使用 gold/outcome/miss-direction/content/file identity 作为 policy input。Candidate pool/order 保持不变。

N10CM 不运行 retrieval/rerun/OpenLocus、candidate generation/add/remove/reorder、adaptive tuning、selector/reranker、P5、BEA-v1-A、runtime/default promotion，也不作 heldout/generalization、method-winner 或 downstream-value claims。

## Handoff

N10CM 只授权 `BEA-v1-N10CN Winning Hybrid Cost-Reduction Refinement Audit Package`，即不进行额外 private reads、recompute 或 new variants 的 public audit package。

## Artifact

- Script: `eval/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep.py`
- Report: `artifacts/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep_report.json`
