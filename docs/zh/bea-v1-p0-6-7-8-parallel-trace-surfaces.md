# BEA-v1-P0-6/7/8 Parallel Trace Surfaces

日期：2026-06-27

BEA-v1-P0-6/7/8 并行关闭三个剩余 P0 trace-surface contracts：same-file redundancy、risk-penalty removal 与 ordered-prefix stop decisions。本阶段读取 P0-1/P0-2 artifacts，并只输出 scanner-validated public contracts；本轮没有提供 private trace rows。

## 结果

```text
P0-6 status: same_file_redundancy_trace_surface_contract_pass
P0-7 status: risk_penalty_trace_surface_contract_pass
P0-8 status: ordered_prefix_stop_trace_surface_contract_pass
self-test: 5 / 5
forbidden scan: 三个 reports 均 pass
contract records: 每个 trace surface 6 条
```

## 解释

- P0-6 定义 same-file redundancy surface，用于 duplicate pressure 与 marginal pack utility review。
- P0-7 定义 risk-penalty surface，用于诊断 gold 被 risk policy 移除，同时避免把 risk 当作 relevance。
- P0-8 定义 ordered-prefix stop surface，用于 early-stop diagnosis；`stop_decision_trace` 只作为 alias 保留，避免分裂现有 P0-1/P0-2 词表。

这些 reports 是 contract artifacts，不是已填充的 private trace exports。它们显式化缺失的 private trace schemas，并在项目内 private rows 出现前保持 P0-2 blockers 诚实。

## 边界

P0-6/7/8 只授权 trace-surface review 或 private trace validation。不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime/default promotion、broad retrieval expansion、method-winner 声明、downstream-value 声明或 policy tuning。

## Artifacts

- Script：`eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py`
- P0-6 report：`artifacts/bea_v1_p0_6_same_file_redundancy_trace_surface/bea_v1_p0_6_same_file_redundancy_trace_surface_report.json`
- P0-7 report：`artifacts/bea_v1_p0_7_risk_penalty_trace_surface/bea_v1_p0_7_risk_penalty_trace_surface_report.json`
- P0-8 report：`artifacts/bea_v1_p0_8_ordered_prefix_stop_trace_surface/bea_v1_p0_8_ordered_prefix_stop_trace_surface_report.json`

