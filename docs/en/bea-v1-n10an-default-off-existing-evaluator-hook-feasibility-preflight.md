# BEA-v1-N10AN Default-Off Existing-Evaluator Hook Feasibility Preflight

Date: 2026-06-29

BEA-v1-N10AN is a public/static preflight. It decides whether the next code step should hook the eval-only adapter into existing validated evaluators. It reads public N10AM/N10AL/N10AJ artifacts and statically inspects the adapter/helper plus N10AB/N10X/N10T evaluator text. It does not import or execute candidate evaluators, read private rows, patch hooks, or change runtime/default behavior.

## Result

```text
status: default_off_existing_evaluator_hook_feasibility_preflight_pass_n10ao_authorized
self-test: 14 / 14
forbidden scan: pass
selected strategy: new_adapter_enabled_variant_evaluator
direct existing-evaluator hook recommended: false
modify existing validated evaluator: false
runtime path hook: false
eval-only: true
default-off required: true
private reads: 0
candidate evaluator imports: 0
candidate evaluator executions: 0
hook patches: 0
```

## Static finding

The candidate surfaces `n10ab_fixed_span_window_repair_smoke`, `n10x_span_level_utility_validation`, and `n10t_span_surface_proxy_validation` were inspected statically only. Each has medium mutation risk if patched directly. The preflight therefore rejects direct hook-in and selects a new adapter-enabled variant evaluator for N10AO.

## Decision

N10AN authorizes only `BEA-v1-N10AO Default-Off Adapter-Enabled Variant Evaluator Patch`: add a new eval-only variant evaluator importing the adapter, require an explicit default-off flag, allow the same scoped N1 span rows only when explicitly enabled, and do not modify existing N10T/N10X/N10AB evaluators. N10AN does not authorize existing evaluator hook-in, runtime/default enablement, retrieval/rerun, candidate generation, new arms/window tuning, selector/reranker, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight.py`
- Report: `artifacts/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight_report.json`
