# BEA-v1-P3-8O Empirical Event Source Declaration Design

日期：2026-06-28

BEA-v1-P3-8O 是 design-only phase，用于定义未来 real empirical event source declaration schema 与 validation rules。它承接 P3-8N 因缺少 empirical event source declaration 而产生的 No-Go。

## 结果

```text
status: empirical_event_source_declaration_design_pass_p3_8p_authorized
self-test: 14 / 14
forbidden scan: pass
future declaration fields: 14
surface source requirement records: 5
validation rules: 11
P3-8P declaration intake preflight authorized: true
fixture generation authorized: false
trace capture execution authorized: false
private write authorized: false
```

该 design 只允许两种未来 source modes：`existing_materialized_event_log` 与 `explicit_future_capture_mode_plan`。Proxy fixtures、committed aggregate proxies 与 contract templates 都被明确拒绝作为 empirical event sources。

## 边界

P3-8O 不读写 private files，不 import helpers 或 target evaluators，不执行 capture，不生成 fixtures，不运行 retrieval，不 rerun P4L/N1/N2，不运行 support labeling，不执行 counterfactuals，不调 policy，也不 promotion runtime/default behavior。Public artifact 只使用 bucketed schema 与 rule summaries。

## Handoff

P3-8O 只授权 **BEA-v1-P3-8P Empirical Event Source Declaration Intake Preflight**。P3-8P 仍是 preflight-only：不生成 fixtures，不执行 capture，也不写 private data。

## Artifact

- Script：`eval/bea_v1_p3_8o_empirical_event_source_declaration_design.py`
- Report：`artifacts/bea_v1_p3_8o_empirical_event_source_declaration_design/bea_v1_p3_8o_empirical_event_source_declaration_design_report.json`
