# BEA-v1-N10CO Default-Off Adapter Smoke for Refined Hybrid

日期：2026-06-29

BEA-v1-N10CO 是一个 implementation smoke，使用现有 default-off eval-only adapter/helper path 来复现 refined hybrid `short75_225_top2_all_pm200`。它不是 runtime/default promotion，也不 hook existing validated evaluators。

## 结果

```text
status: refined_hybrid_adapter_smoke_pass_n10cp_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
refined hybrid: short75_225_top2_all_pm200
top10/top20 span overlap: 25 / 31
cost10/cost20: 3200 / 6200
lost winning top10 hits: 0
file-hit top10 count: 34
N10CP authorized: true
```

## Adapter smoke contract

- Short spans 使用 before75/after225。
- Top2 positions 覆盖为 all-span pm200 before200/after200，不受 span length 影响。
- 其他情况下 spans 不扩展。
- Candidate pool/order 保持不变。
- Gold 仅用于 aggregate evaluation。

## Boundary

Adapter 保持 default-off：adapter default enabled `false`，private read by default `false`，runtime default enabled `false`，runtime config changed `false`，policy default changed `false`。N10CO 不修改 adapter/helper modules，不 hook existing evaluators，也不运行 retrieval/rerun/OpenLocus、candidate generation/add/remove/reorder、adaptive tuning、selector/reranker、P5、BEA-v1-A；不作 heldout/generalization、method-winner 或 downstream-value claims。

## Handoff

N10CO 只授权 `BEA-v1-N10CP Refined Hybrid Adapter Smoke Package`，即不进行额外 private reads 或 runtime/default changes 的 public adapter-smoke package。

## Artifact

- Script: `eval/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke.py`
- Report: `artifacts/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke_report.json`
