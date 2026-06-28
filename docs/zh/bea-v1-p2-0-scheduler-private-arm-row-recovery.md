# BEA-v1-P2-0 Scheduler Private Arm-Row Recovery

日期：2026-06-28

BEA-v1-P2-0 尝试恢复既有 P4L private arm-outcome JSONL surface；当该 surface 存在且有效时，将其输入 P0-3 scheduler/action-cost export contract。这只是 data-surface population：不进行 policy tuning、rerank、implementation、runtime default promotion，也不执行 support counterfactual。

## 结果

```text
status: no_go_p2_0_private_arm_rows_unavailable
self-test: 11 / 11
forbidden scan: pass
P4L artifact: pass
locked denominator: exact match
private arm rows: unavailable locally
P0-3 full private-row export: not run
```

当 private rows 缺失时，row-dependent schema/replay/export gates 会标记为
`not_evaluated`，因此该 No-Go 不会被误写成 schema 或 replay failure。

已提交的 P4L public artifact 记录了 1,088 条 arm rows 的 private manifest，但本地 `.openlocus/research-private/` storage 中没有对应 project-private JSONL。P2-0 可以验证显式提供的 private `/tmp` JSONL，但默认不猜测也不重新生成 private rows。

## Rows 存在时的 pass contract

若要 pass，P2-0 要求 1,088 rows、`schema_version=bea_v1_p4l_private_arm_outcome.v1`、精确 frozen P4L arm set、P4L reach 和 hard-cap metrics 可聚合复现、direct P0-3 `scheduler_dataset_export_full_pass`，并且 public forbidden scan pass。

## Artifact

- Script：`eval/bea_v1_p2_0_scheduler_private_arm_row_recovery.py`
- Report：`artifacts/bea_v1_p2_0_scheduler_private_arm_row_recovery/bea_v1_p2_0_scheduler_private_arm_row_recovery_report.json`
