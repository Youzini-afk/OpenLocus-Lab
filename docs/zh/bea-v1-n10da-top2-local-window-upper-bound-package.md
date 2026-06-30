# BEA-v1-N10DA Top2 Local-Window Upper-Bound Public Package

日期：2026-06-30

BEA-v1-N10DA 是 N10CZ top2 local-window saturation upper-bound smoke 的 public-only package。它只读取 public artifacts，不进行 private reads、recompute 或 new variants。

## 结果

```text
status: top2_local_window_upper_bound_package_complete_n10db_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10DA: 0
recomputes in N10DA: 0
N10DB authorized: true
```

## Packaged facts

- N10CZ 已以 `top2_local_window_saturation_upper_bound_complete_n10da_authorized` 完成。
- 打包的 variants：`top2_pm1000`、`top2_pm1500`、`top2_pm2000`、`top2_pm5000` 与 `top2_file_extent_proxy`。
- `top2_pm1000`、`top2_pm1500`、`top2_pm2000` 与 `top2_pm5000` 全部保持 top10/top20 `30 / 36`。
- `top2_file_extent_proxy` 明确是 `file_extent_proxy_not_runtime_policy`，且结果更差：`22 / 29`，lost pm1000 top10 hits 为 8。
- Local-window saturated：true。
- Local-window upper-bound improves：false。
- File reach dominates residual：true。
- pm1000 与更大 pm variants 下的 remaining misses：file-not-in-top10 `167`，same-file/no-span `4`，span-beyond-top10 `12`。

## Boundary

Local pm-growth line 应停止。N10DA 不授权 private reads、recompute、new variants、local refinement、rank/file experiments、runtime/default enablement、heldout/generalization、retrieval/rerun、candidate generation/add/remove/reorder、top3 override、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Handoff

N10DA 只授权 `BEA-v1-N10DB Rank/File Reach Branch Scoping or Experiment`，具体阶段由 oracle 决定。下一步研究应处理 file/rank reach，而不是继续 local pm growth。

## Artifact

- Script: `eval/bea_v1_n10da_top2_local_window_upper_bound_package.py`
- Report: `artifacts/bea_v1_n10da_top2_local_window_upper_bound_package/bea_v1_n10da_top2_local_window_upper_bound_package_report.json`
