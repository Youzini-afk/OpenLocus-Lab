# BEA-v1-N10DI Packing + Span-Window Combination Public Package

日期：2026-06-30

BEA-v1-N10DI 是 N10DH 的 public-only audit/package。它只读取 public artifacts，不进行 private reads、recompute 或 new variants。

## 结果

```text
status: packing_span_window_combination_public_package_complete_n10dj_authorized
self-test: 12 / 12
forbidden scan: pass
private reads in N10DI: 0
recomputes in N10DI: 0
N10DJ authorized: true
```

## Packaged conclusion

N10DI 验证 N10DH 的范围是 `n10t_best_order_setting`：

- `original_order_packing_anchor_used_bool=false`
- `n10dc_original_order_result_reused_as_anchor_bool=false`

在该 N10T-best-order setting 中：

- window-only `short75_225_top2_pm1000`：`30 / 36`
- prefix7 + same projection：`30 / 36`
- aggressive reference + same projection：`30 / 36`，且仍是 `aggressive_reference_not_safe_default`

结论：`packing_does_not_improve_n10t_window_strategy`。

这**不**表示 original-order packing 没有用。N10DF prefix7 结果在 original-order packing setting 中仍是 top10-safe，但那是 context evidence，不是 N10DH anchor。

## Handoff

N10DI 只授权 `BEA-v1-N10DJ Next Rank/File-Reach Empirical Experiment`，且必须由 oracle-scoped contract 限定。它不授权 runtime/default changes、heldout/generalization claims、retrieval/rerun、candidate generation/materialization、selector/reranker execution、P5、BEA-v1-A、method/downstream claims 或 broad private reads。

## Artifact

- Script: `eval/bea_v1_n10di_packing_span_window_combination_public_package.py`
- Report: `artifacts/bea_v1_n10di_packing_span_window_combination_public_package/bea_v1_n10di_packing_span_window_combination_public_package_report.json`
