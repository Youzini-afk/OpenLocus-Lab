# BEA-v1-N10BO Plateau Mechanism Decomposition

Date: 2026-06-29

BEA-v1-N10BO is a direct empirical decomposition of the N10BM after-heavy plateau. It reads the same scoped N1 span rows and evaluates only the five plateau variants: `before20_after80`, `before25_after75`, `before30_after70`, `before35_after65`, and `before40_after60`. It does not add windows outside the plateau, tune adaptively, change cost budgets, run retrieval/reruns/OpenLocus, generate candidates, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: plateau_mechanism_decomposition_complete_n10bp_authorized
self-test: 18 / 18
forbidden scan: pass
private span rows read: 213
plateau variants: 5
N10BP authorized: true
```

## Plateau overlap

All five plateau variants produce the same public aggregate reach:

```text
top10 span overlap: 20
top20 span overlap: 24
top10 common across all plateau variants: 20
top20 common across all plateau variants: 24
top10 union across plateau variants: 20
top20 union across plateau variants: 24
top10 case-swap count: 0
top20 case-swap count: 0
lost pm50 top10 max count: 0
```

The plateau is therefore a genuinely stable plateau, not a case-swapping plateau.

## Direction buckets

For the common top10 recovered set across plateau variants:

```text
before_gold_gap: 10
after_gold_gap: 1
already_overlap: 9
other: 0
unique top10 cases per plateau variant: 0
```

All outputs are public aggregate/bucket counts only; no paths, spans, line numbers, snippets, gold values, candidate lists, or exact ranks are published.

## Handoff

N10BO authorizes only `BEA-v1-N10BP Plateau Mechanism Package`, a public package of this decomposition. It does not authorize private reads, new variants, adaptive per-row choice, new cost budgets, runtime/default behavior, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10bo_plateau_mechanism_decomposition.py`
- Report: `artifacts/bea_v1_n10bo_plateau_mechanism_decomposition/bea_v1_n10bo_plateau_mechanism_decomposition_report.json`
