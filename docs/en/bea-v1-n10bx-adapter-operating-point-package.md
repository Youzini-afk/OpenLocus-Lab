# BEA-v1-N10BX Adapter Operating-Point Package

Date: 2026-06-29

BEA-v1-N10BX is a public-only package for the N10BW adapter operating-point smoke. It reads public artifacts only. It performs no private reads, no recompute, no retrieval/rerun/OpenLocus execution, no candidate generation, no existing evaluator hook-in, and no runtime/default promotion.

## Result

```text
status: adapter_operating_point_package_complete_n10by_authorized
self-test: 14 / 14
forbidden scan: pass
private reads in N10BX: 0
recomputes in N10BX: 0
N10BY authorized: true
```

## Packaged adapter operating point

N10BX packages that N10BW used the default-off eval-only adapter/helper path to reproduce `cost80_before25_after75` exactly:

- N10BW private span rows read: `213` (N10BX reads none)
- before/after windows: `20 / 60`
- cost proxy: `80`
- top10/top20 span overlap: `20 / 24`
- lost plateau core: `0`
- file-hit top10 count: `34`
- candidate pool/order changed: `false / false`
- existing evaluator hook/runtime default: `false / false`
- N10BS/N10BT/N10BU expected values matched: `true`

## Handoff

N10BX authorizes only `BEA-v1-N10BY Cost-Aware Operating-Point Exploratory Optimization`: same-source exploratory work over the scoped N1 span rows, focused on either reducing cost below 80 without losing 20/24 or increasing top10/top20 beyond 20/24 at modest cost. It does not authorize runtime/default promotion, existing evaluator hook-in, heldout/generalization claims, method-winner claims, downstream-value claims, retrieval/rerun, candidate generation, selector/reranker execution, P5, or BEA-v1-A.

## Artifact

- Script: `eval/bea_v1_n10bx_adapter_operating_point_package.py`
- Report: `artifacts/bea_v1_n10bx_adapter_operating_point_package/bea_v1_n10bx_adapter_operating_point_package_report.json`
