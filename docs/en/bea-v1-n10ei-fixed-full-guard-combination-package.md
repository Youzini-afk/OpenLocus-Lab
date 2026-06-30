# BEA-v1-N10EI Fixed Full/Guard Combination Package

Date: 2026-06-30

BEA-v1-N10EI packages N10EH without private reads or recomputation.

## Result

```text
status: fixed_full_guard_combination_package_complete_n10ej_authorized
self-test: 5 / 5
forbidden scan: pass
variant count: 7
full novel-first top10: 11
best combination top10: 11
N10EG union bound: 13
any variant beats full novel-first: false
any variant reaches union bound: false
```

## Meaning

N10EH confirms a negative but useful result: simple fixed combinations do not improve over full novel-first. The missing union cases require difference analysis, not more naive splicing.

## Handoff

N10EI authorizes only N10EJ full-only vs guard-only difference analysis over the same scoped rows. It does not authorize new/scaled retrieval, candidate generation, runtime/default changes, selector/reranker execution, method-winner claims, downstream claims, or heldout/generalization claims.

## Artifact

- Script: `eval/bea_v1_n10ei_fixed_full_guard_combination_package.py`
- Report: `artifacts/bea_v1_n10ei_fixed_full_guard_combination_package/bea_v1_n10ei_fixed_full_guard_combination_package_report.json`
