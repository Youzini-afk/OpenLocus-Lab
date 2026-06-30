# BEA-v1-N10DD Distinct-File Packing Rank/File-Reach Public Package

日期：2026-06-30

BEA-v1-N10DD 是 corrected N10DC distinct-file packing smoke 的 public-only package。它只读取 public artifacts，不进行 private reads，也不 recompute policy outcomes。

## 结果

```text
status: distinct_file_packing_rank_file_reach_package_complete_n10de_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10DD: 0
recomputes in N10DD: 0
N10DE authorized: true
```

## Packaged N10DC facts

N10DC 使用 corrected safe same/suffix private reference matching 进行 evaluation，并使用 topK-only packing semantics over existing candidate pool。

| Variant | File top10/top20 | Span top10/top20 | Delta top10 file/span | Lost baseline top10 span |
| --- | ---: | ---: | ---: | ---: |
| `baseline_existing_order` | 14 / 19 | 13 / 17 | 0 / 0 | 0 |
| `distinct_file_top10_greedy` | 19 / 20 | 16 / 18 | +5 / +3 | 1 |
| `distinct_file_top20_greedy_then_top10` | 19 / 47 | 16 / 24 | +5 / +3 | 1 |
| `max_per_file_1_top10` | 19 / 20 | 16 / 18 | +5 / +3 | 1 |
| `max_per_file_2_top10` | 16 / 19 | 15 / 17 | +2 / +2 | 0 |

Candidate generation、materialization、addition、removal 均为 0；candidate pool 保持不变。

## Tradeoff summary

- Aggressive one-file-per-file packing 将 top10 file reach 提升 +5，并提供最强 top20 file reach，但产生 1 个 baseline top10 span regression。
- Conservative `max_per_file_2_top10` 的 top10 file/span gain 较小（+2/+2），但 baseline top10 span regression 为 0。

## Handoff

N10DD 只授权 `BEA-v1-N10DE Regression-vs-Zero-Loss Mechanism Decomposition`。N10DE 只能读取 same scoped N1 rows 来分解该 tradeoff。N10DD 本身不进行 private read 或 recompute，也不授权 runtime/default changes、heldout/generalization、retrieval/rerun、candidate generation/materialization/add/remove、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10dd_distinct_file_packing_rank_file_reach_package.py`
- Report: `artifacts/bea_v1_n10dd_distinct_file_packing_rank_file_reach_package/bea_v1_n10dd_distinct_file_packing_rank_file_reach_package_report.json`
