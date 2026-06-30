# BEA-v1-N10DA Top2 Local-Window Upper-Bound Public Package

Date: 2026-06-30

BEA-v1-N10DA is a public-only package of the N10CZ top2 local-window saturation upper-bound smoke. It reads public artifacts only and performs no private reads, recompute, or new variants.

## Result

```text
status: top2_local_window_upper_bound_package_complete_n10db_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10DA: 0
recomputes in N10DA: 0
N10DB authorized: true
```

## Packaged facts

- N10CZ completed with status `top2_local_window_saturation_upper_bound_complete_n10da_authorized`.
- Variants packaged: `top2_pm1000`, `top2_pm1500`, `top2_pm2000`, `top2_pm5000`, and `top2_file_extent_proxy`.
- `top2_pm1000`, `top2_pm1500`, `top2_pm2000`, and `top2_pm5000` all remain top10/top20 `30 / 36`.
- `top2_file_extent_proxy` is explicitly `file_extent_proxy_not_runtime_policy` and is worse: `22 / 29`, losing 8 pm1000 top10 hits.
- Local-window saturated: true.
- Local-window upper-bound improves: false.
- File reach dominates residual: true.
- Remaining misses under pm1000 and larger pm variants: file-not-in-top10 `167`, same-file/no-span `4`, span-beyond-top10 `12`.

## Boundary

The local pm-growth line should stop. N10DA does not authorize private reads, recompute, new variants, local refinement, rank/file experiments, runtime/default enablement, heldout/generalization, retrieval/rerun, candidate generation/add/remove/reorder, top3 override, adaptive tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Handoff

N10DA authorizes only `BEA-v1-N10DB Rank/File Reach Branch Scoping or Experiment`, with the exact phase to be decided by oracle. The next research should address file/rank reach rather than more local pm growth.

## Artifact

- Script: `eval/bea_v1_n10da_top2_local_window_upper_bound_package.py`
- Report: `artifacts/bea_v1_n10da_top2_local_window_upper_bound_package/bea_v1_n10da_top2_local_window_upper_bound_package_report.json`
