# BEA-v1-P3-8F Frozen Event Fixture Materialization Preflight

日期：2026-06-28

BEA-v1-P3-8F 是 future frozen/materialized event fixture materialization 的 design/preflight phase。它不生成 fixture files，不写 project-private files，不写 private trace rows，不运行 P3-8 capture，不运行 retrieval，不 rerun P4L/N1/N2，不运行 support labeling，不执行 counterfactuals，不调 policy，不授权 selector/reranker/P5/BEA-v1-A work，也不 promotion runtime/default behavior。

## 结果

```text
status: frozen_event_fixture_materialization_preflight_pass_p3_8g_authorized
self-test: 11 / 11
forbidden scan: pass
fixture source mappings: 5 / 5
safe proxy source mappings: 5 / 5
private files written in P3-8F: 0
P3-8G proxy fixture materialization authorized: true
```

P3-8F 验证 P3-8 No-Go artifact、P3-7 pass artifact 与 P3-6 pass artifact，然后为每个 trace surface 映射 committed proxy/contract sources：

- `support_link`：来自 P1-3/P1-4 的 committed proxy label summaries，且 P1-5R 确认 source/context linkage 缺失。
- `scheduler_action_cost`：仅使用 committed P0-3 contract template，不是 arm-outcome evidence。
- `ordered_prefix_stop`：来自 P2-1 的 committed aggregate proxy evidence，不是 row-level stop trace。
- `same_file_redundancy`：仅使用 committed P0-6 contract template。
- `risk_penalty`：仅使用 committed P0-7 contract template。

这些是 **proxy fixture plans**，不是 honest empirical captured event fixtures。每个 surface 都显式记录 missing empirical fields。

## 边界

P3-8F 不 materialize fixtures，也不写 `.openlocus/research-private/`。它验证本 phase 期间 private file inventory 未变化。Public records 只包含 bucketed source mappings、proxy claim boundaries、schema completion summaries 与 future materialization plans。

## Handoff

P3-8F 只授权 **BEA-v1-P3-8G Frozen Event Fixture Materialization Smoke**：仅 proxy fixture files，不 trace capture。P3-8G 只能在自己的 phase 写 private fixture files；private trace rows、retrieval、P4L/N1/N2 reruns、support labeling、counterfactuals、denominator audits、policy tuning、selector/reranker/P5/BEA-v1-A work、runtime/default promotion、method-winner 声明与 downstream-value 声明仍未授权。

## Artifact

- Script：`eval/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight.py`
- Report：`artifacts/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight_report.json`
