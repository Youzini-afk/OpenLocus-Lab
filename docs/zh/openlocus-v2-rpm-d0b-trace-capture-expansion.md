# OpenLocus v2 RPM-D0B Trace Capture Expansion

日期：2026-07-04

公开报告：[`artifacts/rpm_d0b_trace_capture_expansion/rpm_d0b_trace_capture_expansion_report.json`](../../artifacts/rpm_d0b_trace_capture_expansion/rpm_d0b_trace_capture_expansion_report.json)

## 状态

RPM-D0B 已作为 expanded private trace-capture phase 完成。它回应 RPM-D1 对原始 D0 trace set 的结论：real-trace diversity 不足。公开状态为 `rpm_d0b_trace_capture_expansion_complete_d1_rerun_authorized`。

本阶段**不**训练 RPM，**不**声称 RPM 有效，也**不**授权 D2/model scaling、runtime/default behavior、provider/network/CI execution、method/scale/winner/default claims、raw publication、broad source scan、candidate expansion，或把 retrieval/pack rerun 当作 new algorithm。

`eval/rpm_d0b_trace_capture_expansion.py` 提供：

- `--self-test`
- `--run-local-trace-capture --confirm-private-output`
- `--validate-report artifacts/rpm_d0b_trace_capture_expansion/rpm_d0b_trace_capture_expansion_report.json`

## 执行摘要

D0B 在执行前预先声明 12 个固定 bounded local episodes。每个 episode 执行三个真实本地 OpenLocus-style actions：bounded retrieval、current source read 和 EvidenceCore citation validation。所需 RPM schema action types 均覆盖：`bounded_retrieval`、`read_current_source`、`validate_evidence`。

只有提供 `--confirm-private-output` 后，本阶段才会在 ignored `runs/` storage 下写入 private rows。每一行都通过 Phase 1 RPM trace schema 校验。Retrieval no-hit rows 和 stale/currentness negative controls 作为 failure-safe outcome rows 记录；bounded CLI miss 不会被当作脚本失败。

## Diversity 和 negative controls

Private trace set 的 aggregate buckets 覆盖 36 rows、12 episodes 和 three action types。公开输出确认至少 30 rows、至少 10 episodes、全部 required action types、至少 5 条 success-bucket rows、至少 5 条 failure-bucket rows、stale/currentness negative-control coverage、retrieval failure-safe coverage，以及 label timing isolation。

Labels 和 outcomes 只在 action 之后 join。State/action features 保持 label-blind，并且不包含 post-action currentness results。

## 隐私和发布边界

公开 artifact 仅为 aggregate-only。它不公开 private trace paths、task ids、private refs、exact queries 或 patterns、raw paths、snippets、hashes、labels、exact row values、raw rows 或 private evidence filenames。公开报告只包含 aggregate row/episode/action/outcome/observation/failure/currentness/label buckets、diversity gate readback、schema/privacy validation 和 stop/go。

## Stop/go

由于所有 D0B gates 均通过，D0B 只授权：

- `rpm_d1_bounded_offline_rpm_small_learning_smoke_rerun`

如果未来某次 D0B run 有任何 gate 失败，脚本只授权 `targeted_d0b_repair_only`。不授权 D2/model scaling、runtime/default、provider/network/CI、training、method/scale/winner/default、raw/broad source scan、candidate expansion、retrieval-pack rerun、FRK-J/B/C、FRK-I variants、LDI-B easy continuation、HAAE-SG/T 或 R2BV static support repair。

## Validation

本阶段所需验证包括：

- `python3 eval/rpm_trace_schema.py --self-test`
- `python3 eval/rpm_trace_schema.py --validate-report artifacts/rpm_trace_schema/rpm_trace_schema_report.json`
- `python3 eval/rpm_d0_trace_capture.py --validate-report artifacts/rpm_d0_trace_capture/rpm_d0_trace_capture_report.json`
- `python3 eval/rpm_d1_learning_smoke.py --validate-report artifacts/rpm_d1_learning_smoke/rpm_d1_learning_smoke_report.json`
- `python3 eval/rpm_d0b_trace_capture_expansion.py --self-test`
- `python3 eval/rpm_d0b_trace_capture_expansion.py --run-local-trace-capture --confirm-private-output`
- `python3 eval/rpm_d0b_trace_capture_expansion.py --validate-report artifacts/rpm_d0b_trace_capture_expansion/rpm_d0b_trace_capture_expansion_report.json`
- optional D1 rerun with `--trace-jsonl <private-d0b-jsonl> --confirm-private-input`
- `python3 scripts/validate_docs_i18n.py`
- `git diff --check`
