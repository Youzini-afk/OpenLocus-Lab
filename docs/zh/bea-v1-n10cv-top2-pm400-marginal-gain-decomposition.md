# BEA-v1-N10CV Top2 pm400 Marginal Gain Mechanism Decomposition

日期：2026-06-30

BEA-v1-N10CV 是对 N10CT 中 `short75_225_top2_all_pm400` 增益的 direct empirical same-source mechanism decomposition。它在 same scoped N1 span rows 上只比较三个 fixed policies（`pm275`、`pm300`、`pm400`）。它不引入 new pm values、top3 overrides、medium/long gates、candidate changes、adaptive tuning、runtime/default behavior、heldout claims 或 method/downstream claims。

## 结果

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

相对 pm300，pm400 增加 1 个 top10 case 与 1 个 top20 case。该新增 case 的 bucket 为：

- distance-to-window bucket：`near_boundary_51_100`
- direction bucket：`same_file_before_gold`
- override bucket：`top2_override_case`
- span-shape bucket：`short_span_base_case`

pm400 下剩余 top10 misses 仍主要受 file reach 限制：

- `file_not_in_top10_remaining`: 167
- `same_file_no_span_overlap_remaining`: 7
- `span_overlap_beyond_top10_remaining`: 12

剩余 local miss signal 支持 N10CW high-window sweep，但 N10CV 不授权 rank/file promotion。

## Boundary

Gold 仅用于 post-hoc bucketed evaluation。N10CV 只公开 aggregate/bucket counts：不公开 paths、spans、line numbers、snippets、gold rows、candidate lists 或 exact ranks。Candidate pool/order 保持不变。N10CV 不授权 runtime/default behavior、heldout/generalization、retrieval/rerun、candidate generation/add/remove/reorder、top3 override、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Handoff

由于存在 remaining local miss signal，N10CV 只授权 `BEA-v1-N10CW Top2 Override High-Window Neighborhood Sweep`。

## Artifact

- Script: `eval/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition.py`
- Report: `artifacts/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition_report.json`
