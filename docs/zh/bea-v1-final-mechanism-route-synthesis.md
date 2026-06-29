# BEA-v1 Final Mechanism Route Synthesis

日期：2026-06-29

BEA-v1 Final Mechanism Route Synthesis 在 N6XFR-D 之后关闭当前 autonomous BEA-v1 mechanism route。它不是新实验，也不是新的 control-plane chain。它只读取 committed public artifacts，不执行 OpenLocus、retrieval、rerun、build、candidate generation、materialization、selector/reranker、counterfactual、private read 或 policy/runtime change。

## 结果

```text
status: bea_v1_mechanism_route_synthesis_complete_blocked_on_external_empirical_inputs
self-test: 14 / 14
forbidden scan: pass
route closures: 4 / 4
next allowed phase: await_external_empirical_inputs_or_new_research_directive
autonomous next experiment authorized: false
```

## Empirical anchors

- P4L 在 locked non-Python denominator 上验证 frozen P4 scheduler：baseline reach 为 0 / 272，frozen scheduler reach 为 52 / 272。
- N1 显示 40-case span-refiner opportunity 被 rank 阻塞：top-10 actionable 为 0 / 40，rank-blocked 为 40 / 40。
- N2 将这 40 条 rank-blocked cases 定位为 extra-depth append / merge-order blocking。
- N3 测试简单 deterministic merge-order designs；best recovered 为 10 / 40，低于 20-case pass gate，因此 simple merge-order designs 不足。
- N4 确认 fixed-pool rank-blocker denominator adequate，并为 fixed-pool preflight 冻结 40 个 eligible cases。

## Closed routes

1. **P1 support-label route**：P1-3 产出 intake-valid automated proxy labels，但 P1-4 判断 evidence 过低，P1-5R 又发现没有 private context linkage。解锁需要 real private source/context linkage for support labels。
2. **P2/P3 trace-surface route**：P2-0 没有 P4L private arm rows，P2-1 只有 aggregate-only ordered-prefix stop evidence，P2-2 没有 same-file/risk traces，P2-3 关闭 late trace route，P3-8PS 没有发现 existing empirical event source。解锁需要 empirical frozen event source declaration 与 materialized fixtures。
3. **Fixed-pool rank-order route**：N5 preflight 已由 N4 denominator 授权，但 N6 发现缺少 exact public per-case arm outcome fields，N6F 定义 160-row schema，N6G 未发现 exact public source。解锁需要 exact public 160-row N6 arm outcomes。
4. **Full-frozen reconstruction route**：N6XR 没有 bounded replay mapping，N6X-FR preflight 被 missing prerequisites 阻塞，N6XFR-B 发现 build/network 与 private-input blockers，N6XFR-C 恢复 release binary，N6XFR-D 发现 private reconstruction input candidates 为零。解锁需要 FD1/P4L/N-series private reconstruction inputs。

## 结论

在当前 public 与 local inputs 下，这条路线已经耗尽。这不是努力失败，也不是证明 method 不可行；它是 data-source boundary。未来工作需要上述 real external inputs 之一，而不是再增加 schema-only autonomous phase。

## Artifact

- Script: `eval/bea_v1_final_mechanism_route_synthesis.py`
- Report: `artifacts/bea_v1_final_mechanism_route_synthesis/bea_v1_final_mechanism_route_synthesis_report.json`
