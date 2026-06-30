# BEA-v1-N10CZ Top2 Local-Window Saturation Upper-Bound Smoke

日期：2026-06-30

BEA-v1-N10CZ 是当前 top2 local span-window family 的 direct empirical same-source upper-bound smoke。它测试非常大的 top2 windows 或 file-extent proxy 是否能在 pivot 到 rank/file reach 前超过 N10CY pm1000 结果。

## 结果

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

- 将 top2 symmetric override 增大到 pm1000 以上并不能继续提升 top10/top20 span overlap。
- Oracle-style `top2_file_extent_proxy` 明确标记为 `file_extent_proxy_not_runtime_policy`，且低于 pm1000。
- pm1000 及更大窗口下的剩余 misses 维持为 file-not-in-top10 `167`、same-file/no-span `4`、span-beyond-top10 `12`。
- 残差由 file reach 主导，但 N10CZ 本身不授权 rank/file experiment 或 promotion。

## Boundary

N10CZ 不将 gold/outcome/miss-direction/content/file identity 用作 policy input；gold 仅用于 evaluation。Candidate pool/order 保持不变。N10CZ 不运行 retrieval/rerun/OpenLocus、candidate generation/add/remove/reorder、top3 override、medium/long gates、rank/file promotion、selector/reranker logic、P5、BEA-v1-A、runtime/default promotion，也不作 heldout/generalization、method-winner 或 downstream-value claims。

## Handoff

N10CZ 只授权 `BEA-v1-N10DA Top2 Local-Window Upper-Bound Public Package`。N10CZ 不授权额外 local refinement，也不授权 rank/file experiment。

## Artifact

- Script: `eval/bea_v1_n10cz_top2_local_window_saturation_upper_bound.py`
- Report: `artifacts/bea_v1_n10cz_top2_local_window_saturation_upper_bound/bea_v1_n10cz_top2_local_window_saturation_upper_bound_report.json`
