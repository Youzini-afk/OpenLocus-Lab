# BEA-v1-P3-6 Frozen Trace Logger Limited Hook Application Patch

日期：2026-06-28

BEA-v1-P3-6 是第一个允许修改 selected evaluator files 的 bounded phase，但只添加 default-off、logging-only hook shims。这些 shims 不会从 normal evaluator paths 调用，也不会 execute trace capture 或写 private rows。

## 结果

```text
status: frozen_trace_logger_limited_hook_application_patch_pass_p3_7_preflight_authorized
self-test: 15 / 15
forbidden scan: pass
hook wiring records: 5
default enabled count: 0
real capture execution count: 0
private writer count: 0
P3-7 capture execution preflight authorized: true
```

P3-6 为五个 trace surfaces 添加 keyword-only、default-disabled hook shims：support link、scheduler action cost、ordered-prefix stop、same-file redundancy 与 risk penalty。Enabled branches 只做 pure helper build/validate/sanitize/validate transformations；不写文件，不 append private rows，不运行 retrieval，不 rerun P4L/N1/N2，不运行 support labeling，也不执行 counterfactuals。

## 修改的 evaluator targets

- `eval/bea_v1_p0_3_scheduler_dataset_export.py`
- `eval/bea_v1_p0_4_support_link_input_design.py`
- `eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py`
- `eval/bea_v1_p1_2_private_label_intake_validator.py`

Helper module 未被修改。Runtime、retrieval、selector、reranker、source、crate、package 与 config files 均未被修改。

## 边界

P3-6 不添加 CLI flags、environment-variable enablement、private-path arguments、default paths 中的 hook calls、private writers 或 trace-capture execution。它只安装 inert shims，并生成 scanner-safe public review artifact。

## Handoff

P3-6 只授权 **BEA-v1-P3-7 Frozen Trace Logger Capture Execution Preflight**。P3-7 是 future explicitly enabled frozen trace-capture run 的 preflight-only；它不得 execute capture，不得写 private rows，不得运行 retrieval，不得 rerun P4L/N1/N2，不得运行 support labeling，不得运行 counterfactuals，不得调 policy，不得授权 P5/BEA-v1-A，也不得 promotion runtime/default behavior。

## Artifact

- Script：`eval/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch.py`
- Report：`artifacts/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch/bea_v1_p3_6_frozen_trace_logger_limited_hook_application_patch_report.json`
