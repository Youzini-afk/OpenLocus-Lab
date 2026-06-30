# BEA-v1-N10DI Packing + Span-Window Combination Public Package

Date: 2026-06-30

BEA-v1-N10DI is a public-only audit/package of N10DH. It reads public artifacts only and performs no private reads, no recompute, and no new variants.

## Result

```text
status: packing_span_window_combination_public_package_complete_n10dj_authorized
self-test: 12 / 12
forbidden scan: pass
private reads in N10DI: 0
recomputes in N10DI: 0
N10DJ authorized: true
```

## Packaged conclusion

N10DI validates that N10DH was scoped to the `n10t_best_order_setting`:

- `original_order_packing_anchor_used_bool=false`
- `n10dc_original_order_result_reused_as_anchor_bool=false`

Within that N10T-best-order setting:

- window-only `short75_225_top2_pm1000`: `30 / 36`
- prefix7 + same projection: `30 / 36`
- aggressive reference + same projection: `30 / 36`, and still `aggressive_reference_not_safe_default`

Conclusion: `packing_does_not_improve_n10t_window_strategy`.

This does **not** claim original-order packing is useless. The N10DF prefix7 result remains top10-safe in the original-order packing setting, but that is contextual evidence, not the N10DH anchor.

## Handoff

N10DI authorizes only `BEA-v1-N10DJ Next Rank/File-Reach Empirical Experiment` under an oracle-scoped contract. It does not authorize runtime/default changes, heldout/generalization claims, retrieval/rerun, candidate generation/materialization, selector/reranker execution, P5, BEA-v1-A, method/downstream claims, or broad private reads.

## Artifact

- Script: `eval/bea_v1_n10di_packing_span_window_combination_public_package.py`
- Report: `artifacts/bea_v1_n10di_packing_span_window_combination_public_package/bea_v1_n10di_packing_span_window_combination_public_package_report.json`
