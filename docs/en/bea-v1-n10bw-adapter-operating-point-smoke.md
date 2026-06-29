# BEA-v1-N10BW Adapter Operating-Point Smoke for cost80_before25_after75

Date: 2026-06-29

BEA-v1-N10BW is an empirical smoke using the existing default-off eval-only adapter path to reproduce the selected operating point `cost80_before25_after75`. The label means fixed ratio 25/75 at total cost proxy 80, i.e. before-window 20 and after-window 60. This is not runtime/default integration and does not hook existing evaluators.

## Result

```text
status: adapter_operating_point_smoke_pass_n10bx_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
operating point: cost80_before25_after75
before/after windows: 20 / 60
top10/top20 span overlap: 20 / 24
lost plateau core: 0
file-hit top10 count: 34
candidate pool/order changed: false / false
N10BX authorized: true
```

## Adapter boundary

N10BW imports the default-off eval-only adapter/helper path and does not import, call, or hook existing N10BS/N10BU evaluators. The adapter copy path is default-off; the smoke applies the fixed operating-point projection locally for the single predeclared operating point. It performs no runtime/default hook and no existing evaluator hook-in.

## Comparison

The adapter-produced operating-point aggregate matches N10BS/N10BT/N10BU public expectations: top10/top20 `20/24`, lost plateau core `0`, cost proxy `80`, file-hit top10 count `34`, and candidate pool/order unchanged.

## Handoff

N10BW authorizes only `BEA-v1-N10BX Adapter Operating-Point Package`, a public audit/package. It does not authorize runtime/default promotion, existing evaluator hook-in, new variants, adaptive tuning, broad private reads, retrieval/rerun, candidate generation, selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10bw_adapter_operating_point_smoke.py`
- Report: `artifacts/bea_v1_n10bw_adapter_operating_point_smoke/bea_v1_n10bw_adapter_operating_point_smoke_report.json`
