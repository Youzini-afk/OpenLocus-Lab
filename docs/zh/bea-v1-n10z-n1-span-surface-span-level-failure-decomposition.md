# BEA-v1-N10Z N1 Span-Surface Span-Level Failure Decomposition

日期：2026-06-29

BEA-v1-N10Z 是对 N10X below-threshold span-level result 的 direct empirical decomposition。它只读取 scoped recovered N1 span rows，并只使用 N10X best arm `span_extra_depth_promote_before_primary_prefix_4`，保持 same N10T fixed-pool ordering semantics。

## 结果

```text
status: n1_span_surface_span_level_failure_decomposition_complete_n10aa_authorized
self-test: 14 / 14
forbidden scan: pass
private span rows read: 213
best arm scope: span_extra_depth_promote_before_primary_prefix_4
top10 file-hit count: 34
top10 span-overlap count: 9
file-hit but no top10 span-overlap count: 25
span-reachable total: 12
```

## Decomposition

在 25 个 top-10 same-file hits 但 top-10 内没有 overlap private gold span 的 cases 中：

- `same_file_before_gold`: 17
- `same_file_after_gold`: 8
- `same_file_disjoint_unknown_order`: 0
- `same_file_malformed_or_missing_span`: 0
- `gold_line_schema_malformed`: 0
- `no_same_file_top10_despite_file_hit_in_record_bug`: 0

在 12 个 fixed pool 内存在任意 span overlap 的 rows 中：

- `span_overlap_rank_1_10`: 9
- `span_overlap_rank_11_20`: 1
- `span_overlap_rank_21_50`: 2
- `span_overlap_rank_gt_50`: 0
- `span_overlap_not_ranked_or_missing`: 0

## Repair signal

same-file/no-overlap buckets 主导 top-10 gap：25/25 misses 是 same-file spans 位于 gold span window 之前或之后。这支持 span-window repair preflight，但不支持立即执行 repair。

## Boundary

N10Z 只公开 bucket counts。它不公开 private paths、file names、contents、gold lines、spans、snippets、candidate lists、exact ranks、source hashes、provider payloads 或 raw rows。它不运行 retrieval，不 rerun P4L/N1/N2/N3，不执行 OpenLocus，不 generate/materialize candidates，不 add/remove candidates，不 search new arms，不运行 selector/reranker logic，不执行 support labeling，不进入 P5/BEA-v1-A，不运行 counterfactuals，不推广 runtime/default behavior，也不提出 method-winner/downstream-value 声明。

## 决策

N10Z 只授权 `BEA-v1-N10AA Span-Window Repair Preflight`，且仅为 design/preflight。Repair execution、retrieval/reruns、runtime/default promotion、P5、BEA-v1-A、selector/reranker execution、method-winner claims 与 downstream-value claims 均仍未授权。

## Artifact

- Script: `eval/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition.py`
- Report: `artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json`
