# BEA-v1-N10DH N10T-Order Packing + Span-Window Combination Smoke

日期：2026-06-30

BEA-v1-N10DH 是 direct empirical same-source experiment，用于在 N10T best-order setting 上组合 fixed packing 与 span-window projection。它只读取 same scoped N1 private span rows 以及 public N10DG/N10DF/span-window artifacts；不使用 N10DC original-order result 作为 anchor。它不执行 retrieval/rerun/OpenLocus，不进行 candidate generation/materialization/add/remove，不运行 selector/reranker，不改变 runtime/default，不进入 P5/BEA-v1-A，不做 adaptive per-record selection，也不作 heldout/generalization、method-winner 或 downstream-value claims。

## 结果

```text
status: packing_span_window_combination_smoke_complete_n10di_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
variant count: 7
N10DI authorized: true
```

## Scope anchor

N10DH 使用 N10T best-order setting：baseline file top10/top20 为 `34/44`，baseline span top10/top20 为 `9/10`，window-only short75/top2-pm1000 为 `30/36`。N10DC original-order anchors（`14/19`、`13/17`、prefix7 `16/17`）不作为 N10DH anchor。

## Variant metrics

| Variant | file top10/top20 | span top10/top20 | Delta vs window-only | Lost window-only top10 |
| --- | ---: | ---: | ---: | ---: |
| baseline_existing_order_no_expansion | 34 / 44 | 9 / 10 | -21 / -26 | 21 |
| window_only_short75_225_top2_pm1000 | 34 / 44 | 30 / 36 | 0 / 0 | 0 |
| packing_prefix7_no_expansion | 34 / 44 | 9 / 10 | -21 / -26 | 21 |
| packing_prefix7_short75_225 | 34 / 44 | 24 / 30 | -6 / -6 | 6 |
| packing_prefix7_short75_225_top2_pm400 | 34 / 44 | 27 / 33 | -3 / -3 | 3 |
| packing_prefix7_short75_225_top2_pm1000 | 34 / 44 | 30 / 36 | 0 / 0 | 0 |
| packing_aggressive_distinct_top20_short75_225_top2_pm1000_reference | 34 / 44 | 30 / 36 | 0 / 0 | 0 |

Prefix7 plus pm1000 匹配 window-only span result，但没有超越它。Aggressive reference 被明确标记为 `aggressive_reference_not_safe_default`，且在本 combination smoke 中也没有超过 window-only aggregate。

## Boundary

Top2 projection 在 fixed packing order 之后计算。Gold 仅用于 after-the-fact scoring。Candidate pool 不变；public artifact rows 仅为 aggregate-only，不包含 private paths、filenames、line numbers、snippets、gold labels、raw candidate lists 或 exact ranks。

## Artifact

- Script: `eval/bea_v1_n10dh_packing_span_window_combination_smoke.py`
- Report: `artifacts/bea_v1_n10dh_packing_span_window_combination_smoke/bea_v1_n10dh_packing_span_window_combination_smoke_report.json`
