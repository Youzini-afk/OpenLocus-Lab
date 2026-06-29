# BEA-v1-N10CP Refined Hybrid Adapter Smoke Public Package

Date: 2026-06-29

BEA-v1-N10CP is a public-only package for the N10CO refined-hybrid adapter smoke. It reads public artifacts only and performs no private reads, no recompute, and no new variants.

## Result

```text
status: refined_hybrid_adapter_package_complete_n10cq_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10CP: 0
recomputes in N10CP: 0
N10CQ authorized: true
```

## Packaged adapter-smoke facts

- N10CO used the existing default-off eval-only adapter/helper path.
- Refined hybrid `short75_225_top2_all_pm200`: top10/top20 `25 / 31`, cost10/cost20 `3200 / 6200`, lost winning top10 hits `0`, file-hit top10 count `34`.
- Candidate pool/order remained unchanged.
- N10CO matched N10CN/N10CM expected aggregates exactly.
- Default-off boundary: adapter default enabled `false`, private read by default `false`, policy default changed `false`, runtime config changed `false`, and runtime default enabled `false`.
- No existing evaluator, runtime, retrieval, or selector hook was used; adapter/helper modules were not modified by N10CO.

## Boundary

N10CP is same-source N1 proxy packaging only. It does not authorize runtime/default enablement, existing evaluator hook-in, heldout/generalization, retrieval/rerun, candidate generation/add/remove/reorder, adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Handoff

N10CP authorizes only `BEA-v1-N10CQ Refined Hybrid Next-Step Decision`: choose between continued cost/quality exploration or a formal default-off variant evaluator for the refined hybrid.

## Artifact

- Script: `eval/bea_v1_n10cp_refined_hybrid_adapter_smoke_package.py`
- Report: `artifacts/bea_v1_n10cp_refined_hybrid_adapter_smoke_package/bea_v1_n10cp_refined_hybrid_adapter_smoke_package_report.json`
