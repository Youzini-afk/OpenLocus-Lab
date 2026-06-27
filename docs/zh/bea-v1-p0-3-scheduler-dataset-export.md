# BEA-v1-P0-3 Scheduler Dataset Export

日期：2026-06-27

BEA-v1-P0-3 导出 P0-1 与 P0-2 要求的 scheduler/action-cost data surface。它是基于已提交 P4L 与 P0-2 artifacts 的 records-only export；如果提供匹配的项目内 private JSONL，也支持导出 sanitized private arm rows。

本阶段不运行 retrieval，不调用 provider，不执行 selector 或 reranker，不调 threshold，也不实现 runtime policy。

## 结果

```text
status: scheduler_dataset_export_contract_pass
self-test: 8 / 8
forbidden scan: pass
aggregate scheduler arms: 4
subgroup denominator rows: 12
private arm rows supplied: false
```

已提交的 public artifact 包含安全的 scheduler dataset contract 与 sanitized aggregate rows。历史 P4L private arm rows 是在之前环境生成的，本机项目内 private directory 中不存在，因此本轮没有满足 full per-arm private export；该 full export 保持 optional。

## 导出面

- `scheduler_arm_dataset_records`：sanitized aggregate P4L arm rows，包含 reach deltas、latency buckets、pool buckets、hard-cap counts 与 error counts。
- `scheduler_subgroup_dataset_records`：sanitized source/language denominator buckets。
- `scheduler_actionability_join_records`：P0-2 action-cost matrix cells，用于解释为什么新 policy 实验前必须先有 scheduler rows。
- `scheduler_private_arm_sanitized_records`：本轮 contract run 为空；只有当 `--private-arm-outcomes-jsonl` 指向匹配的项目内 private JSONL 时才填充。

## 解释

P0-3 补齐了 aggregate scheduler/action-cost export surface，并定义了 full sanitized private-row contract。它确认下一步实践分叉是：

- 在 `.openlocus/research-private/` 下重跑或恢复 P4L private arm rows，并用 `--private-arm-outcomes-jsonl` 重跑 P0-3；或
- 转向 support-link input design，因为 P0-2 仍有 18 个 `blocked_missing_label` cells。

P0-3 不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime/default promotion、broad retrieval expansion、作为质量声明的 frozen P4 rerun、method-winner 声明或 downstream-value 声明。

## Artifact

- Script：`eval/bea_v1_p0_3_scheduler_dataset_export.py`
- Report：`artifacts/bea_v1_p0_3_scheduler_dataset_export/bea_v1_p0_3_scheduler_dataset_export_report.json`

