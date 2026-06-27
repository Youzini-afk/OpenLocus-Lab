# BEA-v1 Trace Gap Audit

日期：2026-06-27

BEA-v1-P0-1 是基于已提交 FD1、P1、FD2-A1、P4L、N2 与 N3 artifacts 的 scanner-validated trace-gap audit。它不运行新 retrieval，不调用 provider，不实现新 policy，也不授权 P5、BEA-v1-A、selector/reranker、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

本阶段目标是把 N3 之后的研究状态转成后续研究 agent 可复盘的显式 trace requirements。它遵守新的 artifact 规则：只要不暴露 raw paths、snippets、exact ranks、candidate lists、prompts、provider payloads、private paths 或 source-linkable private data，公开 artifact 可以包含 sanitized per-gap records。

## 输入

审计只读取已提交的 public artifacts：

- FD1 failure decomposition：`bea_fd1_decomposition_pass`。
- BEA-v1-P1 actionability audit：`no_go_retrieval_availability_limit`。
- FD2-A1 attribution replay：`bea_fd2a1_attribution_replay_pass`。
- P4L locked non-Python scheduler validation：`bea_v1_p4l_locked_non_python_scheduler_validation_pass`。
- N2 rank/pack decomposition：`n2_rank_pack_actionability_decomposition_pass`。
- N3 merge-order design simulation：`n3_merge_order_design_inconclusive`。

## 结果

```text
status: trace_gap_audit_pass
trace gaps audited: 12 FD1 categories
forbidden scan: pass
self-test: 5 / 5
```

Trace availability summary：

```text
sanitized_available:                         3
private_only_needs_public_export:            3
missing_label:                               3
missing_trace:                               2
aggregate_only_insufficient_for_deep_research: 1
```

Priority gap summary：

```text
P0 unresolved/public-export gaps: 8
P1 unresolved/public-export gaps: 1
```

## 主要发现

N2/N3 rank-pack 主线已经为 rank/pack 与 merge-order 复盘提供了 sanitized per-record rows，但更完整的 BEA-v1 机制面仍然 trace 不完整，深度研究 agent 不能只靠 aggregate 表完成复盘。

当前直接阻塞项是：

- `action_cost_trace`：scheduler 阶段已有 private manifest，但尚未导出为 sanitized per-record scheduler rows。
- `support_link_trace`：support counterfactual 需要 support/target relation labels，目前缺失。
- `same_file_redundancy_trace`：FD1 将 redundancy 标记为 missing trace。
- `risk_penalty_trace`：FD1 将 risk-removed-gold 标记为 missing trace。
- `ordered_prefix_stop_trace`：early-stop 诊断目前只有 aggregate 证据，不足以支持深度复盘。

## 授权的下一步

本阶段只授权 trace/data-surface 工作：

- 基于显式 trace-gap rows 刷新 actionability matrix；
- 导出 scanner-validated sanitized P4/P4L scheduler dataset；
- 设计 support-link labeling/counterfactual 输入；
- 在新 policy 实验前保留或导出 redundancy、risk-penalty 与 ordered-prefix stop trace 字段。

它不授权新 retrieval policy implementation、selector/reranker execution、P5、BEA-v1-A、runtime/default promotion、frozen P4 rerun、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## Artifact

- Script：`eval/bea_v1_trace_gap_audit.py`
- Report：`artifacts/bea_v1_trace_gap_audit/bea_v1_trace_gap_audit_report.json`

