# BEA-v1-P3-0 Frozen Upstream Trace-Capture Harness Design

日期：2026-06-28

BEA-v1-P3-0 为 P2-3 阻塞的五个 late surfaces 设计 frozen upstream trace-capture harness：support link、scheduler/action-cost、ordered-prefix stop、same-file redundancy 与 risk penalty。本阶段仅做 schema 与 instrumentation planning。

## 结果

```text
status: frozen_upstream_trace_capture_harness_design_pass
self-test: 12 / 12
forbidden scan: pass
trace schema records: 5
instrumentation point records: 5
P3-1 preflight authorized: true
trace capture execution authorized: false
```

P3-0 不执行 trace capture、retrieval、P4L/N1/N2 reruns、counterfactuals、policy changes、selector/reranker work、P5、BEA-v1-A、implementation 或 runtime/default promotion。任何缺失的 logger target 都会标记为需要 future frozen trace logger，而不是假装已经实现。

## 决策

唯一授权的下一步是 **P3-1 Frozen Upstream Trace-Capture Harness Dry-Run Preflight**。该下一阶段仍是独立 preflight phase，不是 trace capture execution。

## Artifact

- Script：`eval/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design.py`
- Report：`artifacts/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design_report.json`
