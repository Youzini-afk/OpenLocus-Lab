# BEA-v1-N10BP Plateau Mechanism Package

Date: 2026-06-29

BEA-v1-N10BP is a public-only package of the N10BO plateau mechanism decomposition. It reads public artifacts only and does not read private rows, recompute metrics, add variants, tune adaptively, change cost budgets, run retrieval/reruns/OpenLocus, generate/materialize candidates, or make runtime/default, heldout/generalization, method-winner, or downstream-value claims.

## Result

```text
status: plateau_mechanism_package_complete_n10bq_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BP: 0
recomputes in N10BP: 0
N10BQ authorized: true
```

## Packaged plateau facts

All plateau variants have top10/top20 `20 / 24`:

- `before20_after80`
- `before25_after75`
- `before30_after70`
- `before35_after65`
- `before40_after60`

Common-core package:

```text
top10 common: 20
top10 union: 20
top20 common: 24
top20 union: 24
case swaps: 0
unique cases: 0
lost pm50 max: 0
stability bucket: genuinely_stable_plateau
```

Common top10 direction buckets:

```text
before_gold_gap: 10
after_gold_gap: 1
already_overlap: 9
other: 0
```

Candidate pool/order is unchanged, and outputs remain public bucket/count only.

## Handoff

N10BP authorizes only `BEA-v1-N10BQ Plateau Cost-Minimization Sweep`: same scoped N1 rows, fixed ratio family from the stable plateau only (`20/80`, `25/75`, `30/70`, `35/65`, `40/60`), total costs `60/80/100/120`, 20 predeclared variants, and public aggregate/bucket metrics. It does not authorize adaptive tuning, new ratios outside the family, runtime/default behavior, heldout/generalization claims, method/downstream claims, retrieval/rerun, candidate generation, selector/reranker execution, P5, or BEA-v1-A.

## Artifact

- Script: `eval/bea_v1_n10bp_plateau_mechanism_package.py`
- Report: `artifacts/bea_v1_n10bp_plateau_mechanism_package/bea_v1_n10bp_plateau_mechanism_package_report.json`
