# BEA-v1-P3-8M Empirical Frozen Event Fixture Acquisition Design

日期：2026-06-28

BEA-v1-P3-8M 是继 P3-8L 关闭 proxy fixture route 之后的 design-only phase。它只读取 P3-8L public artifact，不读取 private fixtures，不写 private files，不 import helpers 或 target evaluators，不执行 trace capture，不运行 retrieval，不 rerun P4L/N1/N2，不运行 support labeling，不执行 counterfactuals，也不调 policy。

## 结果

```text
status: empirical_fixture_acquisition_design_pass_p3_8n_authorized
self-test: 12 / 12
forbidden scan: pass
empirical source designs: 5
field requirement rows: 5
capture preconditions: 7
P3-8N empirical fixture acquisition preflight authorized: true
fixture generation authorized: false
trace capture execution authorized: false
private trace row write authorized: false
```

P3-8M 将 P3-8L 的决策转化为 5 个 surface-level acquisition-design records。每个 surface 都需要 true empirical frozen/materialized event fixtures。Proxy fixtures、committed aggregate summaries 与 contract templates 仍不得用于 mechanism work。

## 边界

该 phase 只做 schema and acquisition planning。它不生成 fixtures，也不授权 P3-8N 生成 fixtures。它也不授权 trace capture、private trace writes、retrieval、P4L/N1/N2 reruns、support labeling、counterfactuals、denominator audits、policy tuning、selector/reranker work、P5、BEA-v1-A、runtime/default promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## Handoff

P3-8M 只授权 **BEA-v1-P3-8N Empirical Fixture Acquisition Preflight**。P3-8N 是 preflight-only，不得执行 capture、生成 fixtures、写 private rows，或运行 retrieval/rerun/counterfactual/policy work。

## Artifact

- Script：`eval/bea_v1_p3_8m_empirical_fixture_acquisition_design.py`
- Report：`artifacts/bea_v1_p3_8m_empirical_fixture_acquisition_design/bea_v1_p3_8m_empirical_fixture_acquisition_design_report.json`
