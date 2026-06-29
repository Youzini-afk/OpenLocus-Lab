# BEA-v1-N10AJ Default-Off Eval-Only Span Projection Adapter Patch

Date: 2026-06-29

BEA-v1-N10AJ adds a new eval-only span projection adapter and validates it with synthetic/public-fixture checks only. It does not modify N10T, N10X, N10AB, N1/N2/N3/P4L evaluators, runtime/retrieval/selector/reranker/config files, or the helper module.

## Result

```text
status: default_off_eval_only_span_projection_adapter_patch_pass_n10ak_authorized
self-test: 16 / 16
forbidden scan: pass
adapter functions: 2
synthetic projections: 8
private reads: 0
filesystem IO: 0
existing evaluator hook-in: false
runtime/default config changed: false
```

## Adapter API

- `project_evidence_span_record(record, *, expansion_each_side, enabled=False)` returns a non-mutating copy of one evidence span record. With `enabled=False`, the copy is unchanged. With `enabled=True`, only `start_line` and `end_line` are expanded via the N10AH helper.
- `project_evidence_spans(records, *, expansion_each_side, enabled=False)` projects a sequence while preserving count and order.

The adapter imports `expand_evidence_span_record` from the pure N10AH helper. It requires no path, content, gold, private storage, filesystem IO, retrieval, runtime configuration, adaptive tuning, or selector/reranker behavior. Expansion is fixed and supplied by the caller.

## Synthetic checks

N10AJ validates disabled unchanged/non-mutating behavior, enabled pm20/pm50 expansion, min-line clamp, order/count preservation, no path/content/gold requirement, invalid-input propagation, adapter no-IO static safety, and changed-file allowlist compliance.

## Decision

N10AJ authorizes only `BEA-v1-N10AK Eval-Only Adapter Public Fixture Integration Audit Package`. It does not authorize existing evaluator hook-in, runtime/default enablement, private reads by default, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Adapter: `eval/bea_v1_span_window_projection_adapter.py`
- Script: `eval/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch.py`
- Report: `artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json`
