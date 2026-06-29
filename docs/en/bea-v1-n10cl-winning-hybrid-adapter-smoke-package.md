# BEA-v1-N10CL Winning Hybrid Adapter Smoke Public Package

Date: 2026-06-29

BEA-v1-N10CL is a public-only package for the N10CK default-off adapter smoke. It reads public artifacts only and performs no private reads, no recompute, and no new variants.

## Result

```text
status: winning_hybrid_adapter_package_complete_n10cm_authorized
self-test: 13 / 13
forbidden scan: pass
private reads in N10CL: 0
recomputes in N10CL: 0
N10CM authorized: true
```

## Packaged adapter smoke facts

- N10CK used the existing default-off eval-only adapter/helper path.
- Winning hybrid: `short75_225_top3_all_pm200`.
- Result: top10/top20 span overlap `25 / 31`, cost10/cost20 `3300 / 6300`, lost short75/225 hits `0`, file-hit top10 count `34`.
- Candidate pool/order unchanged.
- N10CK matched the N10CJ/N10CI/N10CG expected aggregate values.

## Default-off and hook boundary

N10CL packages the N10CK boundary: adapter default enabled `false`, private read by default `false`, policy default changed `false`, runtime config changed `false`, runtime default enabled `false`, existing evaluator hook-in `false`, runtime/retrieval/selector hook `false`, and adapter/helper modules not modified by N10CK.

## Handoff

N10CL authorizes only `BEA-v1-N10CM Winning Hybrid Next-Step Decision`: choose between continued mechanism exploration and a formal default-off variant evaluator for the winning hybrid. It does not authorize runtime/default enablement, existing evaluator hook-in, heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/reorder, adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10cl_winning_hybrid_adapter_smoke_package.py`
- Report: `artifacts/bea_v1_n10cl_winning_hybrid_adapter_smoke_package/bea_v1_n10cl_winning_hybrid_adapter_smoke_package_report.json`
