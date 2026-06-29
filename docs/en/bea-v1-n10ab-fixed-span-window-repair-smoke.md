# BEA-v1-N10AB Fixed Span-Window Repair Smoke

Date: 2026-06-29

BEA-v1-N10AB is the direct empirical fixed span-window repair smoke authorized by N10AA. It reads exactly the scoped recovered N1 span rows and evaluates the N10T/N10X best arm order with fixed symmetric span expansion variants.

## Result

```text
status: fixed_span_window_repair_smoke_pass_n10ac_authorized
self-test: 16 / 16
forbidden scan: pass
private span rows read: 213
baseline unexpanded top10 span overlap: 9
baseline unexpanded top20 span overlap: 10
top10 file-hit reference: 34
primary pm50 top10 expanded span overlap: 19
primary pm50 top20 expanded span overlap: 23
primary pm50 delta top10 vs unexpanded: 10
primary threshold: pm50 top10 expanded span overlap >= 11
original span hit lost count: 0
```

## Variant results

- `fixed_symmetric_span_expansion_pm20_lines`: top10 expanded span overlap 15, top20 19, delta +6, lost original hits 0.
- `fixed_symmetric_span_expansion_pm50_lines`: top10 expanded span overlap 19, top20 23, delta +10, lost original hits 0.
- `fixed_symmetric_span_expansion_pm100_lines`: top10 expanded span overlap 21, top20 25, delta +12, lost original hits 0.

## Boundary

N10AB uses fixed symmetric windows only. Gold is used only for evaluation, not for choosing window size, shifting windows, content-aware adjustment, path changes, candidate addition/removal, or arm selection. It does not run retrieval, rerun P4L/N1/N2/N3, execute OpenLocus, generate/materialize candidates, add/remove candidates, search new arms, run selector/reranker logic, enter P5/BEA-v1-A, run counterfactuals, promote runtime/default behavior, or make method-winner/downstream-value claims.

## Decision

The primary pm50 variant passes the N10AA threshold: 19 >= 11. N10AB authorizes only `BEA-v1-N10AC Fixed Span-Window Repair Smoke Result Audit`, public audit scope only. No runtime/default promotion or method/downstream claim is authorized.

## Artifact

- Script: `eval/bea_v1_n10ab_fixed_span_window_repair_smoke.py`
- Report: `artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json`
