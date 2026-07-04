# OpenLocus v2 RPM-D1 Bounded Offline RPM-small Learning Smoke

Date: 2026-07-04

Public report: [`artifacts/rpm_d1_learning_smoke/rpm_d1_learning_smoke_report.json`](../../artifacts/rpm_d1_learning_smoke/rpm_d1_learning_smoke_report.json)

## Status

RPM-D1 is complete as a bounded offline pipeline/learning smoke only. The status is `rpm_d1_learning_smoke_complete_insufficient_real_trace_diversity_no_training_claim` with current RPM-D0 input. It proves the private-trace loading, schema validation, leakage-safe split, stdlib-only tiny learner, baseline comparison, diversity gating, aggregate reporting, and stop/go mechanics. It does **not** claim that RPM works and does **not** authorize RPM training, runtime/default use, model scaling, provider/network/CI execution, or method/scale/winner/default claims.

`eval/rpm_d1_learning_smoke.py` provides:

- `--self-test`
- `--run-offline-learning-smoke --trace-jsonl <private-d0-jsonl> --confirm-private-input`
- `--run-offline-learning-smoke --confirm-private-input` to use the latest ignored `runs/rpm_d0_private_*/rpm_d0_state_action_traces.jsonl`
- `--validate-report <path>`

## Execution summary

RPM-D1 reads private RPM-D0 JSONL only after `--confirm-private-input`. It validates all rows with `eval/rpm_trace_schema.py`, groups rows by trace/episode id, and evaluates a deterministic leave-one-episode-out split with an assertion that no train/eval trace overlap occurs.

The local learner is a stdlib-only deterministic decision stump. It uses only label-blind pre-action fields allowed for the D1 smoke: task type, objective bucket, query shape bucket, repo size bucket, candidate count bucket, evidence coverage bucket, pre-action currentness bucket, ambiguity bucket, dirty state bucket, action type, retrieval budget bucket, source scan scope, candidate generation policy, pack policy, and eligible actions bucket. Post-action currentness results such as stale rejection are explicitly excluded from features and remain only in observation/EvidenceCore linkage. The target is derived only after the action from outcome/observation as success vs failure-safe. Baselines include the majority baseline and a fixed-action/action-only stump baseline.

## Result and diversity gate

The current D0 trace has aggregate buckets `count_6_to_20` rows, `count_2_to_5` episodes, `count_2_to_5` action types, and a minority outcome bucket of `count_1`. The required diversity gates are at least 30 real rows, 10 episodes, 3 action types, two outcome classes with at least 5 rows each, at least 3 held-out episodes, no train/eval trace overlap, and a model bucketed margin over majority. Current D0 fails the real-row, episode, action-type, class-balance, and model-vs-majority signal gates. The D1 result is therefore a controlled insufficient-diversity smoke, not a training or performance claim.

## Privacy and publication boundary

The public artifact is aggregate-only. It does not publish the private trace path, raw rows, task ids, queries, paths, snippets, hashes, labels, exact raw features, exact row values, or private identifiers. The report includes only schema validation status, feature coverage buckets, diversity buckets, split leakage status, model family, baseline comparison buckets, privacy scan, and stop/go.

## Stop/go

Because diversity is insufficient and no bucketed signal is claimed, RPM-D1 authorizes only:

- `rpm_d0b_trace_capture_expansion_or_frk_product_workflow_trace_capture`

If a future bounded trace set unexpectedly passes diversity and shows candidate signal, D1 may authorize only `rpm_d2_larger_trace_capture_and_heldout_eval_design`. RPM-D1 explicitly does not authorize RPM runtime/default, provider/network/CI, method/scale/winner/default claims, raw publication, broad source scan, candidate generation expansion, retrieval/pack rerun as a new algorithm, FRK-J/B/C, FRK-I variants, LDI-B easy continuation, HAAE-SG/T, or R2BV static support repair.

## Validation

Required validation passed:

- `python3 eval/rpm_trace_schema.py --self-test`
- `python3 eval/rpm_trace_schema.py --validate-report artifacts/rpm_trace_schema/rpm_trace_schema_report.json`
- `python3 eval/rpm_d0_trace_capture.py --validate-report artifacts/rpm_d0_trace_capture/rpm_d0_trace_capture_report.json`
- `python3 eval/rpm_d1_learning_smoke.py --self-test`
- `python3 eval/rpm_d1_learning_smoke.py --run-offline-learning-smoke --confirm-private-input`
- `python3 eval/rpm_d1_learning_smoke.py --validate-report artifacts/rpm_d1_learning_smoke/rpm_d1_learning_smoke_report.json`
- `python3 scripts/validate_docs_i18n.py`
- `git diff --check`
