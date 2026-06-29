# BEA-v1-N10AO Default-Off Adapter-Enabled Variant Evaluator Patch

Date: 2026-06-29

BEA-v1-N10AO adds a new eval-only variant evaluator. It imports the N10AJ span projection adapter, stays default-off, and reads the scoped N1 span rows only when explicitly enabled. It does not modify existing N10T/N10X/N10AB/N1/N2/N3/P4L evaluators, runtime, retrieval, selector/reranker, or configuration code.

The public artifact was generated with explicit scoped enablement for this phase. Default mode remains disabled: no private read, no metric recompute, and no adapter projection by default.

## Result

```text
status: default_off_adapter_enabled_variant_evaluator_pass_n10ap_authorized
self-test: 16 / 16
forbidden scan: pass
explicit enablement used: true
default enabled: false
private read by default: false
private span rows read: 213
baseline top10/top20 span overlap: 9 / 10
pm50 top10/top20 span overlap: 19 / 23
delta top10 vs baseline: 10
original span-hit lost: 0
candidate pool changed: false
order changed: false
```

## Boundary

- New eval-only variant evaluator only.
- Imports the adapter, not N10AB/N10AD/N10T/N10X/N1/N2/N3/P4L evaluators.
- Requires explicit scoped enablement to read private rows and run the adapter projection.
- Uses fixed pm50 projection; no new arms, window tuning, retrieval, rerun, selector/reranker, runtime/default change, P5, or BEA-v1-A.
- Public output contains aggregate counts only; no private paths, filenames, spans, line values, candidate lists, gold paths, snippets, hashes, or raw rows.

## Decision

N10AO authorizes only `BEA-v1-N10AP Adapter-Enabled Variant Evaluator Result Audit Package`, a public audit/package. N10AO does not authorize additional private reads, existing evaluator hook-in, modifying existing validated evaluators, runtime/default enablement, retrieval/rerun, candidate generation, new arms/window tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator.py`
- Report: `artifacts/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator_report.json`
