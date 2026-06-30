# BEA-v1-N10DB Rank/File-Reach Policy Field Scoping

日期：2026-06-30

BEA-v1-N10DB 是 rank/file-reach policy fields 的短 empirical scoping phase。它只检查 same scoped N1 span rows 以及 public N10DA/N10CZ/N10T/N10X artifacts。它不执行 rank/file policy，不计算 policy outcomes，不 add/remove/reorder candidates，不运行 retrieval/reruns/OpenLocus，不使用 selector/reranker logic，不进入 P5/BEA-v1-A，也不改变 runtime/default behavior。

## 结果

```text
status: rank_file_reach_policy_field_scoping_pass_n10dc_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
policy outcome computations: 0
selected policy family: file_dedup_distinct_file_packing
N10DC authorized: true
```

## Field scoping findings

- `p4_evidence` 在 213 条 scoped rows 上以 ordered evidence list 形式存在。
- Candidate file identifiers 在私有侧存在，可作为 gold-free policy input，但 public artifact 不序列化 paths 或 filenames。
- Span boundary fields 存在，可供未来 evaluation context 使用，但 public artifact 不公开 spans 或 line values。
- Score/method/channel/source fields 不是完整的 candidate-level policy fields，因此 source/channel interleave 与 score/method ordering 不推荐用于 N10DC。
- Candidate pool length 足以进行 rank/file reach scoping：176 条 rows 至少有 20 个 evidence items。
- Gold fields 仅确认 future evaluation availability；N10DB 不用它们进行 policy selection 或 outcome computation。

## Duplicate pressure

现有 top-k 列表存在明显 duplicate-file pressure：

| Bucket | Top10 rows | Top20 rows |
| --- | ---: | ---: |
| none | 44 | 25 |
| low | 67 | 24 |
| medium | 69 | 40 |
| high | 33 | 124 |

这支持下一步选择 `file_dedup_distinct_file_packing` scoped smoke。

## Handoff

N10DB 只授权 `BEA-v1-N10DC Distinct-File Packing Rank/File-Reach Smoke`：same scoped rows、same candidate pool、gold-free file-dedup packing variants、no candidate generation，并且只输出 public aggregate。Preview variants 为 `baseline_existing_order`、`distinct_file_top10_greedy`、`distinct_file_top20_greedy_then_top10`、`max_per_file_1_top10` 与 `max_per_file_2_top10`；N10DB 只记录它们，不执行。

N10DB 不授权 retrieval/rerun、candidate generation/materialization、selector/reranker execution、P5、BEA-v1-A、runtime/default changes、heldout/generalization claims、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10db_rank_file_reach_policy_field_scoping.py`
- Report: `artifacts/bea_v1_n10db_rank_file_reach_policy_field_scoping/bea_v1_n10db_rank_file_reach_policy_field_scoping_report.json`
