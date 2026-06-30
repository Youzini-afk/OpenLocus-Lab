# BEA-v1-N10DC Distinct-File Packing Rank/File-Reach Smoke

日期：2026-06-30

BEA-v1-N10DC 是 scoped N1 span rows 上的 direct empirical same-source rank/file-reach smoke。它使用 private candidate file identifiers 作为 gold-free observable policy feature，保持 original candidate pool 不变，并且只在该 pool 内 repack/reorder views。它不 generate、add、remove 或 materialize candidates。

## 结果

```text
status: distinct_file_packing_rank_file_reach_smoke_complete_n10dd_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
candidate generation/add/remove: 0 / 0 / 0
N10DD authorized: true
```

## Variant results

| Variant | Top10 file | Top20 file | Top10 span | Top20 span | Duplicate pressure reduced rows | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `baseline_existing_order` | 14 | 19 | 13 | 17 | 0 | baseline_existing_order |
| `distinct_file_top10_greedy` | 19 | 20 | 16 | 18 | 152 | span_regression_or_no_file_gain |
| `distinct_file_top20_greedy_then_top10` | 19 | 47 | 16 | 24 | 152 | span_regression_or_no_file_gain |
| `max_per_file_1_top10` | 19 | 20 | 16 | 18 | 152 | span_regression_or_no_file_gain |
| `max_per_file_2_top10` | 16 | 19 | 15 | 17 | 93 | improves_file_reach_without_span_regression |

Distinct-file packing 将 top10 file reach 从 baseline `14` 提升到 `19`，top10 span 从 `13` 提升到 `16`，但 one-file-per-file variants 会丢 1 个 baseline top10 span hit。top10-only variant 的 file/span top20 为 `20/18`；top20-then-top10 variant 显示更高的 top20 reach，为 `47/24`。更稳的 `max_per_file_2_top10` 增益较小但零丢失：file `16/19`、span `15/17`。这仍然只是 same-source N1 proxy result，不是 runtime/default recommendation。

## Boundary

N10DC 只使用现有 `p4_evidence` pool。Candidate pool 保持不变；candidate generation、materialization、addition、removal 均为 0。Gold 仅用于 evaluation，不用于 packing。Public artifacts 只包含 aggregate counts/buckets，不包含 private paths、filenames、spans、lines、snippets、gold rows、candidate lists 或 exact ranks。

## Handoff

N10DC 只授权 `BEA-v1-N10DD Distinct-File Packing Rank/File-Reach Public Package`。它不授权 runtime/default changes、heldout/generalization claims、retrieval/rerun、candidate generation/materialization/add/remove、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke.py`
- Report: `artifacts/bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke/bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke_report.json`
