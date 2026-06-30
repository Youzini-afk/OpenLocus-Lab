# BEA-v1-N10EH Fixed Full/Guard Combination Repacking Experiment

Date: 2026-06-30

BEA-v1-N10EH tests fixed, gold-free ways to combine the two complementary N10EG rules. It uses the same scoped N10DZ top100 rows and N1 rows; it does not run new retrieval, candidate generation, runtime/default changes, or selector/reranker logic.

## Result

```text
status: fixed_full_guard_combination_repacking_experiment_complete_n10ei_authorized
self-test: 6 / 6
forbidden scan: pass
variant count: 7
full novel-first top10: 11
guarded top5 top10: 10
N10EG union upper bound: 13
best combination top10: 11
any variant beats full novel-first: false
any variant reaches union upper bound: false
```

## Interpretation

The complementarity is real, but simple fixed combinations do not turn it into a better executable rule. Full novel-first remains the best single rule at `11/60`; the tested combinations do not exceed it and do not reach the union upper bound of `13/60`.

This is still useful: it says the missing two union cases need a more specific observable difference analysis, not simple rule splicing.

## Handoff

N10EH authorizes only N10EI public package and N10EJ full/guard difference analysis over the same scoped rows. It does not authorize new/scaled retrieval, candidate generation, runtime/default changes, selector/reranker execution, method-winner claims, downstream claims, or heldout/generalization claims.

## Artifact

- Script: `eval/bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment.py`
- Report: `artifacts/bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment/bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment_report.json`
