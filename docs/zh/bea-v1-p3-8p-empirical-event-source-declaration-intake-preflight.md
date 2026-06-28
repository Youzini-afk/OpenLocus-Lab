# BEA-v1-P3-8P Empirical Event Source Declaration Intake Preflight

日期：2026-06-28

BEA-v1-P3-8P 验证是否显式提供了 real empirical event source declaration，以及该 declaration 是否 schema-valid。默认本地运行不执行 broad private scan；由于没有提供 declaration，因此 fail closed。

## 结果

```text
status: no_go_p3_8p_empirical_source_declaration_missing
self-test: 13 / 13
forbidden scan: pass
declaration supplied: false
P3-8Q fixture acquisition plan preflight authorized: false
fixture generation authorized: false
trace capture execution authorized: false
private write authorized: false
```

P3-8P 绑定 P3-8O declaration-design artifact。它可以通过 `--declaration-json` 验证显式提供的 declaration，但不会搜索 `.openlocus`，不会公开序列化 exact declaration path 或 filename，也不会写 private files。

## 边界

该 phase 只执行 declaration intake preflight。它不生成 fixtures，不执行 capture，不读取 broad private inventories，不写 private rows，不 import helpers 或 target evaluators，不运行 retrieval，不 rerun P4L/N1/N2，不运行 support labeling，不执行 counterfactuals，不调 policy，也不 promotion runtime/default behavior。

## Handoff

在默认 No-Go 运行中，P3-8Q 未获授权。如果未来显式 declaration 通过所有 schema、surface coverage、source mode、privacy 与 claim-boundary gates，则只会授权 **BEA-v1-P3-8Q Empirical Fixture Acquisition Plan Preflight**；该 preflight 仍不允许 fixture generation，也不允许 capture execution。

## Artifact

- Script：`eval/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight.py`
- Report：`artifacts/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight_report.json`
