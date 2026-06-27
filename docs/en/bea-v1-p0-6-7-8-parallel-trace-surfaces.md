# BEA-v1-P0-6/7/8 Parallel Trace Surfaces

Date: 2026-06-27

BEA-v1-P0-6/7/8 closes three remaining P0 trace-surface contracts in parallel: same-file redundancy, risk-penalty removal, and ordered-prefix stop decisions. The phase reads P0-1/P0-2 artifacts and emits scanner-validated public contracts only; no private trace rows are supplied in this run.

## Result

```text
P0-6 status: same_file_redundancy_trace_surface_contract_pass
P0-7 status: risk_penalty_trace_surface_contract_pass
P0-8 status: ordered_prefix_stop_trace_surface_contract_pass
self-test: 5 / 5
forbidden scan: pass for all three reports
contract records: 6 per trace surface
```

## Interpretation

- P0-6 defines the same-file redundancy surface required for duplicate pressure and marginal pack utility review.
- P0-7 defines the risk-penalty surface required to diagnose gold removal by risk policy without treating risk as relevance.
- P0-8 defines the ordered-prefix stop surface required for early-stop diagnosis; `stop_decision_trace` is kept only as an alias to avoid splitting the existing P0-1/P0-2 vocabulary.

These reports are contract artifacts, not populated private trace exports. They make the missing private trace schemas explicit and keep the P0-2 blockers honest until project-local private rows exist.

## Boundary

P0-6/7/8 authorize only trace-surface review or private trace validation. They do not authorize P5, BEA-v1-A, selector/reranker execution, implementation, runtime/default promotion, broad retrieval expansion, method-winner claims, downstream-value claims, or policy tuning.

## Artifacts

- Script: `eval/bea_v1_p0_6_7_8_parallel_trace_surfaces.py`
- P0-6 report: `artifacts/bea_v1_p0_6_same_file_redundancy_trace_surface/bea_v1_p0_6_same_file_redundancy_trace_surface_report.json`
- P0-7 report: `artifacts/bea_v1_p0_7_risk_penalty_trace_surface/bea_v1_p0_7_risk_penalty_trace_surface_report.json`
- P0-8 report: `artifacts/bea_v1_p0_8_ordered_prefix_stop_trace_surface/bea_v1_p0_8_ordered_prefix_stop_trace_surface_report.json`

