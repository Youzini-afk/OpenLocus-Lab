# BEA-v1-N10CY Top2 pm1000 Marginal Gain Mechanism Decomposition

Date: 2026-06-30

BEA-v1-N10CY is a direct empirical same-source mechanism decomposition of marginal gains from pm400 to pm800 to pm1000 in the top2 high-window family. It reads the same scoped N1 span rows and compares exactly three fixed policies: `short75_225_top2_all_pm400`, `short75_225_top2_all_pm800`, and `short75_225_top2_all_pm1000`.

## Result

```text
status: top2_pm1000_marginal_gain_decomposition_complete_n10cz_authorized
self-test: 14 / 14
forbidden scan: pass
private span rows read: 213
pm400: 27 / 33 at 4000 / 7000
pm800: 29 / 35 at 5600 / 8600
pm1000: 30 / 36 at 6400 / 9400
N10CZ authorized: true
```

## Marginal gains

- pm800 vs pm400: +2 top10 and +2 top20.
- pm1000 vs pm800: +1 top10 and +1 top20.
- pm1000 vs pm400: +3 top10 and +3 top20.

Mechanism buckets show the pm800 gains are same-file before-gold cases split across near-boundary buckets, while the pm1000 incremental gain is a same-file after-gold case in the 101-300 boundary bucket. Across pm1000 vs pm400, the gains are 2 before-gold and 1 after-gold, all top1/top2 override cases and short-span-base cases.

## Remaining misses at pm1000

- file-not-in-top10: 167
- same-file/no-span: 4
- span-beyond-top10: 12

Both further local-window signal and rank/file-reach pivot signal remain present. This phase does not choose between them; it authorizes only the N10CZ oracle-scoped next exploration decision.

## Boundary

N10CY does not use gold/outcome/miss-direction/content/file identity as policy input. Gold is used only for post-hoc bucketed evaluation. It does not add/remove/reorder candidates, introduce top3 override, medium/long gates, new rank/order arms, or new pm values beyond 400/800/1000. It does not run retrieval/rerun/OpenLocus, selector/reranker logic, P5, BEA-v1-A, runtime/default promotion, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition.py`
- Report: `artifacts/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition_report.json`
