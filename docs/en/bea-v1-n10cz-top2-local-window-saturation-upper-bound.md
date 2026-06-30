# BEA-v1-N10CZ Top2 Local-Window Saturation Upper-Bound Smoke

Date: 2026-06-30

BEA-v1-N10CZ is a direct empirical same-source upper-bound smoke for the current top2 local span-window family. It tests whether very large top2 windows or a file-extent proxy can improve beyond the N10CY pm1000 result before pivoting to rank/file reach.

## Result

```text
status: top2_local_window_saturation_upper_bound_complete_n10da_authorized
self-test: 13 / 13
forbidden scan: pass
private span rows read: 213
top2_pm1000: 30 / 36
top2_pm1500: 30 / 36
top2_pm2000: 30 / 36
top2_pm5000: 30 / 36
top2_file_extent_proxy: 22 / 29
local window saturated: true
file reach dominates residual: true
N10DA authorized: true
```

## Findings

- Increasing top2 symmetric override beyond pm1000 does not improve top10/top20 span overlap.
- The oracle-style `top2_file_extent_proxy` is explicitly labeled `file_extent_proxy_not_runtime_policy` and underperforms pm1000.
- Remaining misses under pm1000 and larger windows stay at file-not-in-top10 `167`, same-file/no-span `4`, and span-beyond-top10 `12`.
- The residual is dominated by file reach, but N10CZ itself does not authorize a rank/file experiment or promotion.

## Boundary

N10CZ uses no gold/outcome/miss-direction/content/file identity as policy input; gold is evaluation-only. Candidate pool/order is unchanged. N10CZ does not run retrieval/rerun/OpenLocus, candidate generation/add/remove/reorder, top3 override, medium/long gates, rank/file promotion, selector/reranker logic, P5, BEA-v1-A, runtime/default promotion, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Handoff

N10CZ authorizes only `BEA-v1-N10DA Top2 Local-Window Upper-Bound Public Package`. N10CZ authorizes neither additional local refinement nor a rank/file experiment.

## Artifact

- Script: `eval/bea_v1_n10cz_top2_local_window_saturation_upper_bound.py`
- Report: `artifacts/bea_v1_n10cz_top2_local_window_saturation_upper_bound/bea_v1_n10cz_top2_local_window_saturation_upper_bound_report.json`
