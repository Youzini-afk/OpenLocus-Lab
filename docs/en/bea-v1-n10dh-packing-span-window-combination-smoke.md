# BEA-v1-N10DH N10T-Order Packing + Span-Window Combination Smoke

Date: 2026-06-30

BEA-v1-N10DH is a direct empirical same-source experiment combining fixed packing with span-window projection in the N10T best-order setting. It reads only the same scoped N1 private span rows and public N10DG/N10DF/span-window artifacts, and it does not reuse the N10DC original-order result as an anchor. It performs no retrieval/rerun/OpenLocus execution, candidate generation/materialization/add/remove, selector/reranker execution, runtime/default change, P5/BEA-v1-A work, adaptive per-record selection, heldout/generalization claim, method-winner claim, or downstream-value claim.

## Result

```text
status: packing_span_window_combination_smoke_complete_n10di_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
variant count: 7
N10DI authorized: true
```

## Scope anchor

N10DH uses the N10T best-order setting: baseline file top10/top20 is `34/44`, baseline span top10/top20 is `9/10`, and window-only short75/top2-pm1000 is `30/36`. N10DC original-order anchors (`14/19`, `13/17`, prefix7 `16/17`) are not used as N10DH anchors.

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

Prefix7 plus pm1000 matches the window-only span result, but does not improve it. The aggressive reference is explicitly labeled `aggressive_reference_not_safe_default` and also does not improve the window-only aggregate in this combination smoke.

## Boundary

Top2 projection is computed after the fixed packing order. Gold is used only for after-the-fact scoring. Candidate pool is unchanged; public artifact rows are aggregate-only and contain no private paths, filenames, line numbers, snippets, gold labels, raw candidate lists, or exact ranks.

## Artifact

- Script: `eval/bea_v1_n10dh_packing_span_window_combination_smoke.py`
- Report: `artifacts/bea_v1_n10dh_packing_span_window_combination_smoke/bea_v1_n10dh_packing_span_window_combination_smoke_report.json`
