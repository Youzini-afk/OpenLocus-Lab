# BEA-v1-N10DG Hybrid Distinct-File Packing Public Package

Date: 2026-06-30

BEA-v1-N10DG is a public-only package/audit of the N10DF hybrid distinct-file packing smoke. It reads public N10DC/N10DE/N10DF artifacts only and performs no private reads, no recompute, and no new variants.

## Result

```text
status: hybrid_distinct_file_packing_public_package_complete_n10dh_authorized
self-test: 12 / 12
forbidden scan: pass
private reads in N10DG: 0
recomputes in N10DG: 0
N10DH authorized: true
```

## Packaged conclusion

- `prefix7_then_distinct_fill_top10` is a promising top10-safe packing hybrid: it matches aggressive top10 span recovery (`16`) with zero baseline top10 span loss.
- It is not a default winner and does not match aggressive top20 reach: prefix7 top20 span/file is `17 / 19`, while aggressive top20 span/file is `24 / 47`.
- Candidate pool is preserved; no gold is used for policy selection.

## Boundary

N10DG does not authorize runtime/default behavior, selector/reranker execution, candidate generation, retrieval/rerun, broad private reads, P5, BEA-v1-A, method-winner claims, downstream-value claims, or heldout/generalization claims.

## Handoff

N10DG authorizes only `BEA-v1-N10DH Packing Plus Span-Window or Top20 Reach Repair Experiment`, scoped by the next oracle contract.

## Artifact

- Script: `eval/bea_v1_n10dg_hybrid_distinct_file_packing_public_package.py`
- Report: `artifacts/bea_v1_n10dg_hybrid_distinct_file_packing_public_package/bea_v1_n10dg_hybrid_distinct_file_packing_public_package_report.json`
