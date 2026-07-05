# OpenLocus v2 RPM-D1 Bounded Offline RPM-small Learning Smoke

日期：2026-07-04

公开报告：[`artifacts/rpm_d1_learning_smoke/rpm_d1_learning_smoke_report.json`](../../artifacts/rpm_d1_learning_smoke/rpm_d1_learning_smoke_report.json)

## 状态

RPM-D1 已作为 bounded offline pipeline/learning smoke 完成。最新重跑使用 RPM-D0B 输入，状态是 `rpm_d1_learning_smoke_complete_no_signal_no_training_claim`。它只证明 private trace 读取、schema validation、无泄漏 split、stdlib-only tiny learner、baseline comparison、diversity gate、aggregate reporting 和 stop/go 机制可运行。它**不**声称 RPM 有效，也**不**授权 RPM training、runtime/default、model scaling、provider/network/CI execution，或 method/scale/winner/default claims。

`eval/rpm_d1_learning_smoke.py` 提供：

- `--self-test`
- `--run-offline-learning-smoke --trace-jsonl <private-d0-or-d0b-jsonl> --confirm-private-input`
- `--run-offline-learning-smoke --confirm-private-input`，默认使用 `runs/` 下最新 ignored RPM-D0 或 RPM-D0B trace JSONL
- `--validate-report <path>`

## 执行摘要

RPM-D1 只有在提供 `--confirm-private-input` 后才读取 private RPM-D0 或 RPM-D0B JSONL。它用 `eval/rpm_trace_schema.py` 校验全部 rows，按 trace/episode id 分组，并执行 deterministic leave-one-episode-out split，同时断言 train/eval trace 不重叠。

本地 learner 是 stdlib-only deterministic decision stump。它只使用 D1 smoke 允许的 label-blind pre-action fields：task type、objective bucket、query shape bucket、repo size bucket、candidate count bucket、evidence coverage bucket、pre-action currentness bucket、ambiguity bucket、dirty state bucket、action type、retrieval budget bucket、source scan scope、candidate generation policy、pack_policy 和 eligible_actions_bucket。`stale_rejected` 这类 post-action currentness 结果明确不能进入 features，只能留在 observation/EvidenceCore linkage 中。Target 只在 action 之后从 outcome/observation 派生为 success vs failure-safe。Baseline 包括 majority baseline、fixed-action/action-only stump baseline，以及二者中的 best-baseline bucket。

## 结果和 diversity gate

原始 D0 trace 不足。D0B 重跑现在通过数据形状门槛：rows `count_21_to_50`、episodes `count_6_to_20`、three action types、two target classes，且无 train/eval overlap。在移除 post-action feature leakage 并改为对比 best baseline 后，模型仍是 `delta_non_positive`，所以 D1 结果是 no-signal，不是 training 或 performance claim。

## 隐私和发布边界

公开 artifact 仅包含 aggregate 信息。它不发布 private trace path、raw rows、task ids、queries、paths、snippets、hashes、labels、exact raw features、exact row values 或 private identifiers。报告只包含 schema validation status、feature coverage buckets、diversity buckets、split leakage status、model family、baseline comparison buckets、privacy scan 和 stop/go。

## Stop/go

由于 D0B 重跑没有超过 best baseline，RPM-D1 只授权：

- `rpm_d0b_trace_capture_expansion_or_frk_product_workflow_trace_capture`

如果未来 bounded trace set 意外通过 diversity 并出现 candidate signal，D1 也只能授权 `rpm_d2_larger_trace_capture_and_heldout_eval_design`。RPM-D1 明确不授权 RPM runtime/default、provider/network/CI、method/scale/winner/default claims、raw publication、broad source scan、candidate generation expansion、把 retrieval/pack rerun 当作 new algorithm、FRK-J/B/C、FRK-I variants、LDI-B easy continuation、HAAE-SG/T 或 R2BV static support repair。

## Validation

所需验证已通过：

- `python3 eval/rpm_trace_schema.py --self-test`
- `python3 eval/rpm_trace_schema.py --validate-report artifacts/rpm_trace_schema/rpm_trace_schema_report.json`
- `python3 eval/rpm_d0_trace_capture.py --validate-report artifacts/rpm_d0_trace_capture/rpm_d0_trace_capture_report.json`
- `python3 eval/rpm_d1_learning_smoke.py --self-test`
- `python3 eval/rpm_d1_learning_smoke.py --run-offline-learning-smoke --confirm-private-input`
- `python3 eval/rpm_d1_learning_smoke.py --validate-report artifacts/rpm_d1_learning_smoke/rpm_d1_learning_smoke_report.json`
- `python3 scripts/validate_docs_i18n.py`
- `git diff --check`
