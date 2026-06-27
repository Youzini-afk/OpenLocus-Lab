# BEA-v1-P0-3 Scheduler Dataset Export

Date: 2026-06-27

BEA-v1-P0-3 exports the scheduler/action-cost data surface requested by P0-1 and P0-2. It is a records-only export over committed P4L and P0-2 artifacts, with optional support for sanitized private arm rows when the matching project-local private JSONL is supplied.

This phase does not run retrieval, does not call providers, does not execute a selector or reranker, does not tune thresholds, and does not implement a runtime policy.

## Result

```text
status: scheduler_dataset_export_contract_pass
self-test: 8 / 8
forbidden scan: pass
aggregate scheduler arms: 4
subgroup denominator rows: 12
private arm rows supplied: false
```

The committed public artifact contains a safe scheduler dataset contract and sanitized aggregate rows. The historical P4L private arm rows were created in a previous environment and are not present in this machine's project-local private directory, so the full per-arm private export remains optional and not satisfied in this run.

## Exported Surfaces

- `scheduler_arm_dataset_records`: sanitized aggregate P4L arm rows with reach deltas, latency buckets, pool buckets, hard-cap counts, and error counts.
- `scheduler_subgroup_dataset_records`: sanitized source/language denominator buckets.
- `scheduler_actionability_join_records`: P0-2 action-cost matrix cells that explain why scheduler rows are required before new policy experiments.
- `scheduler_private_arm_sanitized_records`: empty in this contract run; populated only when `--private-arm-outcomes-jsonl` points to the matching project-local private JSONL.

## Interpretation

P0-3 closes the aggregate scheduler/action-cost export surface and defines the full sanitized private-row contract. It confirms that the next practical fork is either:

- rerun or recover P4L private arm rows under `.openlocus/research-private/` and re-run P0-3 with `--private-arm-outcomes-jsonl`; or
- move to support-link input design, because P0-2 still has 18 `blocked_missing_label` cells.

P0-3 does not authorize P5, BEA-v1-A, selector/reranker execution, implementation, runtime/default promotion, broad retrieval expansion, frozen P4 rerun as a quality claim, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_p0_3_scheduler_dataset_export.py`
- Report: `artifacts/bea_v1_p0_3_scheduler_dataset_export/bea_v1_p0_3_scheduler_dataset_export_report.json`

