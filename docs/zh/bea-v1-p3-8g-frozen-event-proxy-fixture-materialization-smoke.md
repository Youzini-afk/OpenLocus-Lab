# BEA-v1-P3-8G Frozen Event Proxy Fixture Materialization Smoke

日期：2026-06-28

BEA-v1-P3-8G 基于 P3-8F safe proxy source mappings materialize proxy fixture files。这些文件只是 proxy fixture inputs；不是 captured trace rows，也不是 empirical P3-8 frozen trace fixtures。

## 结果

```text
status: frozen_event_proxy_fixture_materialization_smoke_pass_p3_8h_authorized
self-test: 15 / 15
forbidden scan: pass
private proxy fixture files written: 2
proxy fixture events: 5
P3-8H compatibility preflight authorized: true
```

P3-8G 正好写入两个 project-private ignored files；public 中只用
`p3_8g_proxy_fixture_manifest_private` 与 `p3_8g_proxy_fixture_events_private`
两个 bucket 表达。Public artifact 不公开 exact private filenames 或 paths。

它不写 default P3-8 fixture filenames。五个 surfaces 各有一条 proxy event，字段值均为 bucketed proxy-safe values，并显式记录 missing empirical field buckets。它不 materialize real hits、ranks、paths、candidates、queue identifiers、design identifiers 或 provider payloads。

## 边界

P3-8G 不运行 P3-8 capture、retrieval、P4L/N1/N2 reruns、support labeling、counterfactuals、policy tuning、selector/reranker work、P5、BEA-v1-A、runtime/default promotion 或 broad retrieval。它不修改 P3-8 evaluator、helper module、target evaluators 或 runtime/retrieval files。

Public artifact 只包含 bucketed summaries。Private proxy files 被故意 ignore，不能 commit。

## Compatibility

当前 P3-8 schema **不接受** 这些 proxy fixtures 作为 empirical frozen trace fixtures。因此 P3-8G 只授权 **BEA-v1-P3-8H Proxy Fixture Compatibility Preflight — no capture execution**，用于在不 trace capture 的前提下做 proxy-mode acceptance/rejection decision。

## Artifact

- Script：`eval/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.py`
- Report：`artifacts/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke_report.json`
