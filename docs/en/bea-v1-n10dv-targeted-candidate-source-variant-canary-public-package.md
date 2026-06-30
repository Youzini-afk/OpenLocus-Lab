# BEA-v1-N10DV Targeted Candidate-Source Variant Canary Public Package

Date: 2026-06-30

BEA-v1-N10DV is a public-only package of the N10DU targeted candidate-source variant canary. It reads the public N10DU artifact only and performs no private reads, recomputation, or retrieval.

## Result

```text
status: targeted_candidate_source_variant_canary_public_package_complete_n10dw_authorized
self-test: 8 / 8
forbidden scan: pass
private reads in N10DV: 0
recomputes in N10DV: 0
N10DW authorized: true
```

## Packaged N10DU signal

- Same-30-case targeted canary pass.
- Six fixed variants were tested with 180 local commands in N10DU.
- Best variant: `identifier_normalized_bm25_only`.
- Best variant recovered gold file top10/top20/top50: `8 / 9 / 10`.
- Cases recovered by any variant: `10`.
- Original BM25 and all regex/symbol variants recovered `0`.

## Boundary

This is a strong same-30-case targeted canary signal, not scaling, not heldout, not a method winner, not downstream evidence, and not runtime/default behavior.

## Handoff

N10DV authorizes only `BEA-v1-N10DW Normalized-BM25 Recovery Mechanism Analysis`. It does not authorize scaled retrieval, network, git clone, provider calls, candidate generation/materialization, selector/reranker execution, runtime/default changes, P5, BEA-v1-A, method/downstream claims, heldout/generalization claims, or broad private reads.

## Artifact

- Script: `eval/bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package.py`
- Report: `artifacts/bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package/bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package_report.json`
