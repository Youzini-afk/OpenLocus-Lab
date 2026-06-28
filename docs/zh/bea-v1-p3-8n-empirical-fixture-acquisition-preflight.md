# BEA-v1-P3-8N Empirical Fixture Acquisition Preflight

日期：2026-06-28

BEA-v1-P3-8N 是 empirical frozen/materialized event fixture acquisition 的 preflight-only phase。它只读取 P3-8M public artifact 与 gitignore metadata。它不读取 private fixture inventories，不读写 private files，不 import helper/P3-8/target evaluators，不执行 capture，不生成 fixtures，不运行 retrieval，不 rerun P4L/N1/N2，不运行 support labeling，不执行 counterfactuals，也不调 policy。

## 结果

```text
status: no_go_p3_8n_empirical_event_source_not_declared
self-test: 13 / 13
forbidden scan: pass
surface field spec records: 5
empirical event source declared: false
P3-8O source declaration design authorized: true
fixture generation authorized: false
trace capture execution authorized: false
private write authorized: false
```

P3-8M acquisition design 已存在且有效，project-private root 也通过 metadata 显示为 gitignored。但是尚未声明 empirical event source。因此 P3-8N 在 fixture generation、capture execution 或 private writes 之前 fail closed。

## 边界

P3-8N 不执行 private inventory read。它只验证 public input contract、privacy-root metadata、scanner/fail-closed rules、explicit enablement boundaries 与 per-surface empirical field specifications。缺少 empirical source declaration 会阻止任何 fixture generation 或 capture。

## Handoff

P3-8N 只授权 **BEA-v1-P3-8O Empirical Event Source Declaration Design**。P3-8O 是 design-only，不得生成 fixtures、执行 capture、写 private data、运行 retrieval/reruns/support/counterfactuals、调 policy 或 promotion runtime/default behavior。

## Artifact

- Script：`eval/bea_v1_p3_8n_empirical_fixture_acquisition_preflight.py`
- Report：`artifacts/bea_v1_p3_8n_empirical_fixture_acquisition_preflight/bea_v1_p3_8n_empirical_fixture_acquisition_preflight_report.json`
