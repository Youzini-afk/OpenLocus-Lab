# BEA-v1-N10BJ Asymmetric Window Direction Mechanism Package

Date: 2026-06-29

BEA-v1-N10BJ is a public-only package for the N10BI pm50 vs `before25_after75` direction decomposition. It reads public artifacts only and does not read private rows, recompute metrics, add variants, tune adaptively, run retrieval/reruns/OpenLocus, generate/materialize candidates, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: asymmetric_window_mechanism_package_complete_n10bk_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BJ: 0
recomputes in N10BJ: 0
N10BK authorized: true
```

## Packaged mechanism facts

- Fixed symmetric `pm50`: top10/top20 `19 / 23`, cost proxy `1000`.
- Asymmetric `before25_after75`: top10/top20 `20 / 24`, cost proxy `1000`.
- Net gain: `+1 / +1`.
- Top10 gained cases: `1`; top10 lost cases: `0`.
- Gained buckets: `before_gold_gap=1`, `after_gold_gap=0`, `already_overlap=0`, `other=0`.
- Lost buckets: all `0`.

The package confirms the no-gold policy boundary: fixed global windows, no per-row adaptation, and no gold/miss-direction signal used to choose per-record windows.

## Handoff

N10BJ authorizes only `BEA-v1-N10BK Neighboring Asymmetry Micro-Sweep`: same scoped N1 rows, same cost proxy `1000` only, and the predeclared variants `before0_after100`, `before25_after75`, `before50_after50`, `before75_after25`, and `before100_after0`. N10BK is for direction sensitivity mapping, not choosing a default. N10BJ does not authorize new cost budgets, adaptive per-row choices, runtime/default behavior, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10bj_asymmetric_window_mechanism_package.py`
- Report: `artifacts/bea_v1_n10bj_asymmetric_window_mechanism_package/bea_v1_n10bj_asymmetric_window_mechanism_package_report.json`
