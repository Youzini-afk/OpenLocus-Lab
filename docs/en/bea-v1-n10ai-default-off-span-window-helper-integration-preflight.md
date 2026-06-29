# BEA-v1-N10AI Default-Off Span Window Helper Integration Preflight

Date: 2026-06-29

BEA-v1-N10AI is a static integration preflight only. It identifies the safe eval-only integration target for the N10AH helper and does not patch any hook, runtime path, existing evaluator, retrieval code, selector/reranker code, or configuration.

## Result

```text
status: default_off_span_window_helper_integration_preflight_pass_n10aj_authorized
self-test: 15 / 15
forbidden scan: pass
recommended hook target: future_eval_only_span_projection_adapter
existing runtime path: false
default-off interface defined: true
behavior risk: low
```

## Candidate hook points

- `n10ab_smoke_evaluator_expansion_loop`: eval-only but not recommended because patching the existing smoke evaluator has behavior-preservation risk.
- `n10x_span_overlap_evaluation_loop`: eval-only but not recommended because patching the existing validation evaluator has behavior-preservation risk.
- `future_eval_only_span_projection_adapter`: recommended. It is a new eval-only adapter target, not an existing runtime path and not an existing evaluator hook-in.

## Default-off interface

The N10AJ target must remain default-off and eval-only. It may expose a fixed-window projection adapter only behind an explicit evaluation call/flag, with no private read by default, no runtime/default enablement, no retrieval/rerun, no candidate generation, no selector/reranker behavior, no P5/BEA-v1-A path, and no method/downstream claim.

## Decision

N10AI authorizes only `BEA-v1-N10AJ Default-Off Eval-Only Span Projection Adapter Patch`. N10AI does not authorize existing evaluator hook-in, runtime/default enablement, private reads by default, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10ai_default_off_span_window_helper_integration_preflight.py`
- Report: `artifacts/bea_v1_n10ai_default_off_span_window_helper_integration_preflight/bea_v1_n10ai_default_off_span_window_helper_integration_preflight_report.json`
