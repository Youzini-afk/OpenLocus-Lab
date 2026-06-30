# BEA-v1-N10CV Top2 pm400 Marginal Gain Mechanism Decomposition

Date: 2026-06-30

BEA-v1-N10CV is a direct empirical same-source mechanism decomposition of the `short75_225_top2_all_pm400` gain from N10CT. It compares exactly three fixed policies (`pm275`, `pm300`, and `pm400`) over the same scoped N1 span rows. It does not introduce new pm values, top3 overrides, medium/long gates, candidate changes, adaptive tuning, runtime/default behavior, heldout claims, or method/downstream claims.

## Result

```text
status: top2_pm400_marginal_gain_decomposition_complete_n10cw_authorized
self-test: 14 / 14
forbidden scan: pass
private span rows read: 213
pm275: 26 / 32 at 3500 / 6500
pm300: 26 / 32 at 3600 / 6600
pm400: 27 / 33 at 4000 / 7000
N10CW authorized: true
```

## Marginal gain mechanism

pm400 gains one top10 case and one top20 case relative to pm300. The new case is bucketed as:

- distance-to-window bucket: `near_boundary_51_100`
- direction bucket: `same_file_before_gold`
- override bucket: `top2_override_case`
- span-shape bucket: `short_span_base_case`

Remaining top10 misses under pm400 are still dominated by file reach:

- `file_not_in_top10_remaining`: 167
- `same_file_no_span_overlap_remaining`: 7
- `span_overlap_beyond_top10_remaining`: 12

The remaining local miss signal justifies an N10CW high-window sweep, while rank/file promotion remains unauthorized in N10CV.

## Boundary

Gold is used only for post-hoc bucketed evaluation. N10CV publishes aggregate/bucket counts only: no paths, spans, line numbers, snippets, gold rows, candidate lists, or exact ranks. Candidate pool/order remains unchanged. N10CV does not authorize runtime/default behavior, heldout/generalization, retrieval/rerun, candidate generation/add/remove/reorder, top3 override, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Handoff

N10CV authorizes only `BEA-v1-N10CW Top2 Override High-Window Neighborhood Sweep` because remaining local miss signal exists.

## Artifact

- Script: `eval/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition.py`
- Report: `artifacts/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition_report.json`
