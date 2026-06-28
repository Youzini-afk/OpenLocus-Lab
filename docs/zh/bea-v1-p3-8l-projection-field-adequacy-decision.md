# BEA-v1-P3-8L Projection Field Adequacy and Empirical Fixture Requirement Decision

日期：2026-06-28

BEA-v1-P3-8L 是 proxy fixture route 的 decision-only closure phase。它只读取 P3-8K public artifact，不读取 private fixtures，不 import helpers 或 target evaluators，不执行 capture，不运行 retrieval，不 rerun P4L/N1/N2，不运行 support labeling，不执行 counterfactuals，也不调 policy。

## 结果

```text
status: proxy_route_closure_empirical_fixtures_required
self-test: 11 / 11
forbidden scan: pass
proxy route closed: true
P3-8M empirical fixture acquisition design authorized: true
trace capture execution authorized: false
private trace row write authorized: false
```

P3-8L 接受 P3-8K 的结论：proxy public projections 对 logger-smoke audit 来说 shape-valid，但不是 empirical trace evidence。它们不足以支持 denominator audits、counterfactuals 或 mechanism-evidence claims。

## 决策

Proxy route 对 mechanism work 已关闭。后续若要进入 mechanism work、denominator audits、counterfactuals 或 trace-capture claims，必须先获得 true empirical frozen/materialized event fixtures。Committed aggregate proxies、contract templates 与 proxy fixtures 都不能替代 empirical fixtures。

## Handoff

P3-8L 只授权 **BEA-v1-P3-8M Empirical Frozen Event Fixture Acquisition Design**。P3-8M 是 design-only，不授权 capture execution、private trace writes、retrieval、P4L/N1/N2 reruns、support labeling、counterfactuals、policy tuning、selector/reranker work、P5、BEA-v1-A、runtime/default promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## Artifact

- Script：`eval/bea_v1_p3_8l_projection_field_adequacy_decision.py`
- Report：`artifacts/bea_v1_p3_8l_projection_field_adequacy_decision/bea_v1_p3_8l_projection_field_adequacy_decision_report.json`
