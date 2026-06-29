# BEA-v1-N10AS Exploratory Span-Window Variant Sweep

Date: 2026-06-29

BEA-v1-N10AS is a same-source exploratory optimization over the existing N1 span-surface proxy. It reads exactly the scoped private N1 span rows and uses the known best N10T order (`span_extra_depth_promote_before_primary_prefix_4`). It does not sweep rank/order arms. It does not perform retrieval, reruns, OpenLocus execution, candidate generation/materialization, selector/reranker logic, P5/BEA-v1-A, runtime/default promotion, or downstream/method claims.

## Result

```text
status: exploratory_span_window_variant_sweep_complete_n10at_authorized
self-test: 13 / 13
forbidden scan: pass
private span rows read: 213
variant count: 15
baseline unexpanded top10/top20: 9 / 10
max-recall frontier point: pm200
recommended top10/top20 span overlap: 25 / 30
recommended delta top10 vs unexpanded: 16
recommended cost proxy bucket: very_high
N10AT authorized: true
```

## Sweep design

The sweep is fixed and predeclared: symmetric `pm0`, `pm10`, `pm20`, `pm30`, `pm50`, `pm75`, `pm100`, `pm150`, `pm200`, plus asymmetric `before75_after25`, `before100_after50`, `before150_after50`, `before25_after75`, `before50_after100`, and `before50_after150`.

The frontier is a trade-off curve, not a default-policy recommendation: `pm30` is the low-cost point (top10/top20 `18/22`), `before25_after75` and `pm75` are balanced points (`20/24` and `21/25`), and `pm200` is the max-recall point (`25/30`) with very-high cost proxy. The single recommendation field follows the predeclared exploratory rule: highest top-10 count among Pareto-frontier variants, tie-breaking by lower cost and then symmetric windows. No per-record adaptive window, gold-directed tuning, candidate addition/removal, or candidate reorder beyond the N10T best order is used.

## Claim boundary

N10AS is same-source only, N1 span-surface proxy only, not heldout, not N2-equivalent, not runtime/default, not a method winner, and not downstream-value evidence. It authorizes only `BEA-v1-N10AT Exploratory Span-Window Variant Sweep Audit Package`, a public audit/package. It does not authorize private reads, extra sweeps, heldout validation claims, runtime/default changes, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, adaptive tuning, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10as_exploratory_span_window_variant_sweep.py`
- Report: `artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json`
