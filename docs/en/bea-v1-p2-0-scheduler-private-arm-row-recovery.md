# BEA-v1-P2-0 Scheduler Private Arm-Row Recovery

Date: 2026-06-28

BEA-v1-P2-0 attempts to recover the existing P4L private arm-outcome JSONL surface and, when present and valid, feed it into the P0-3 scheduler/action-cost export contract. This is data-surface population only: it does not tune policy, rerank, implement, promote runtime defaults, or execute support counterfactuals.

## Result

```text
status: no_go_p2_0_private_arm_rows_unavailable
self-test: 11 / 11
forbidden scan: pass
P4L artifact: pass
locked denominator: exact match
private arm rows: unavailable locally
P0-3 full private-row export: not run
```

Row-dependent schema/replay/export gates are marked `not_evaluated` when private
rows are missing, so the No-Go is not misreported as schema or replay failure.

The committed P4L public artifact records a private manifest for 1,088 arm rows, but the project-private JSONL is not present in the local `.openlocus/research-private/` storage. P2-0 can validate an explicitly supplied private `/tmp` JSONL, but it does not guess or regenerate private rows by default.

## Pass contract when rows are present

To pass, P2-0 requires 1,088 rows with `schema_version=bea_v1_p4l_private_arm_outcome.v1`, the exact frozen P4L arm set, aggregate reproduction of P4L reach and hard-cap metrics, direct P0-3 `scheduler_dataset_export_full_pass`, and a public forbidden scan pass.

## Artifact

- Script: `eval/bea_v1_p2_0_scheduler_private_arm_row_recovery.py`
- Report: `artifacts/bea_v1_p2_0_scheduler_private_arm_row_recovery/bea_v1_p2_0_scheduler_private_arm_row_recovery_report.json`
