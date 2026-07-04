# OpenLocus v2 RPM-D0 Trace Capture

日期：2026-07-04

公开报告：[`artifacts/rpm_d0_trace_capture/rpm_d0_trace_capture_report.json`](../../artifacts/rpm_d0_trace_capture/rpm_d0_trace_capture_report.json)

## 状态

RPM-D0 已作为可执行的本地 trace-capture phase 完成。它不是 RPM training phase。

`eval/rpm_d0_trace_capture.py` 提供：

- `--self-test`
- `--run-local-trace-capture --confirm-private-output`
- `--validate-report <path>`

## 执行摘要

RPM-D0 在执行前选择 bounded committed/local task set，然后执行真实的本地 OpenLocus EvidenceCore action。它至少捕获两类 action：

- 通过本地 OpenLocus CLI `read` 命令执行 `read_current_source`。
- 通过本地 OpenLocus CLI `citations validate` 命令执行 `validate_evidence`。

Rows 作为 private state/action records 记录。对每个 task，先准备 state features，且不使用 label/outcome；随后执行本地 action 并记录 observation；最后才 join private outcome bucket。Private rows 通过 `eval/rpm_trace_schema.py` 的严格 Phase 1 RPM trace schema 校验。

## 隐私和发布边界

Private trace rows 以 JSONL 写入 ignored `runs/` storage。公开 artifact 仅包含 aggregate buckets：task/episode/step buckets、action coverage buckets、EvidenceCore currentness buckets、label timing/isolation buckets、outcome buckets、schema validation status、private storage class/count proof，以及 privacy leak scan status。公开内容不包含 raw paths、queries、task ids、snippets、hashes、labels、prompts/responses、exact private row values、provider payloads 或 raw rows。

## Stop/go

由于 coverage 足够且 schema validation 通过，RPM-D0 只授权：

- `rpm_d1_bounded_offline_rpm_small_learning_smoke`

RPM-D0 明确不授权 RPM training、FRK-J/B/C、FRK-I selector variants、LDI-B easy continuation、HAAE-SG/T、R2BV static support repair、provider/network/CI/runtime default、method/scale/winner/default claims、raw publication、broad source scan、candidate expansion，或把 retrieval/pack rerun 当作 new algorithm。

## Validation

所需验证已通过：

- `python3 eval/rpm_trace_schema.py --self-test`
- `python3 eval/rpm_trace_schema.py --validate-report artifacts/rpm_trace_schema/rpm_trace_schema_report.json`
- `python3 eval/rpm_d0_trace_capture.py --self-test`
- `python3 eval/rpm_d0_trace_capture.py --run-local-trace-capture --confirm-private-output`
- `python3 eval/rpm_d0_trace_capture.py --validate-report artifacts/rpm_d0_trace_capture/rpm_d0_trace_capture_report.json`
