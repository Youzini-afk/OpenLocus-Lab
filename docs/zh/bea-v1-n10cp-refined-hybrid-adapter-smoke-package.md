# BEA-v1-N10CP Refined Hybrid Adapter Smoke Public Package

日期：2026-06-29

BEA-v1-N10CP 是 N10CO refined-hybrid adapter smoke 的 public-only package。它只读取 public artifacts，不进行 private reads、recompute 或 new variants。

## 结果

```text
status: refined_hybrid_adapter_package_complete_n10cq_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10CP: 0
recomputes in N10CP: 0
N10CQ authorized: true
```

## Packaged adapter-smoke facts

- N10CO 使用现有 default-off eval-only adapter/helper path。
- Refined hybrid `short75_225_top2_all_pm200`：top10/top20 `25 / 31`，cost10/cost20 `3200 / 6200`，lost winning top10 hits `0`，file-hit top10 count `34`。
- Candidate pool/order 保持不变。
- N10CO 与 N10CN/N10CM expected aggregates 完全匹配。
- Default-off boundary：adapter default enabled `false`，private read by default `false`，policy default changed `false`，runtime config changed `false`，runtime default enabled `false`。
- 没有使用 existing evaluator、runtime、retrieval 或 selector hook；adapter/helper modules 未被 N10CO 修改。

## Boundary

N10CP 仅为 same-source N1 proxy packaging。它不授权 runtime/default enablement、existing evaluator hook-in、heldout/generalization、retrieval/rerun、candidate generation/add/remove/reorder、adaptive tuning、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Handoff

N10CP 只授权 `BEA-v1-N10CQ Refined Hybrid Next-Step Decision`：在 continued cost/quality exploration 与 refined hybrid 的 formal default-off variant evaluator 之间选择下一步。

## Artifact

- Script: `eval/bea_v1_n10cp_refined_hybrid_adapter_smoke_package.py`
- Report: `artifacts/bea_v1_n10cp_refined_hybrid_adapter_smoke_package/bea_v1_n10cp_refined_hybrid_adapter_smoke_package_report.json`
