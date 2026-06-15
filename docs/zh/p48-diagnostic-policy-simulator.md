# P48 诊断策略模拟器 / 请求更多上下文覆盖层

- Schema: `p48-diagnostic-policy-simulator-v1`
- 生成报告：见 `docs/en/p48-diagnostic-policy-simulator.md`

## 说明

P48 是 P47「请求更多上下文」跨度几何门在 P25 `bucket_routed_v0` 与 P30-H4B `admission_v3_h4b` 路由策略上的确定性 SCORE 阶段覆盖模拟。它仅输出聚合指标，不生成证据、不提升默认策略、不改变 Rust/EvidenceCore。

更多细节请参阅英文报告。
