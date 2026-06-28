# BEA-v1-P3-0 Frozen Upstream Trace-Capture Harness Design

Date: 2026-06-28

BEA-v1-P3-0 designs a frozen upstream trace-capture harness for the five late surfaces blocked by P2-3: support link, scheduler/action-cost, ordered-prefix stop, same-file redundancy, and risk penalty. This phase is schema and instrumentation planning only.

## Result

```text
status: frozen_upstream_trace_capture_harness_design_pass
self-test: 12 / 12
forbidden scan: pass
trace schema records: 5
instrumentation point records: 5
P3-1 preflight authorized: true
trace capture execution authorized: false
```

P3-0 does not execute trace capture, retrieval, P4L/N1/N2 reruns, counterfactuals, policy changes, selector/reranker work, P5, BEA-v1-A, implementation, or runtime/default promotion. Any missing logger target is marked as requiring a future frozen trace logger rather than being treated as already implemented.

## Decision

The only authorized next step is **P3-1 Frozen Upstream Trace-Capture Harness Dry-Run Preflight**. That next phase is still a separate preflight phase, not trace capture execution.

## Artifact

- Script: `eval/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design.py`
- Report: `artifacts/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design/bea_v1_p3_0_frozen_upstream_trace_capture_harness_design_report.json`
