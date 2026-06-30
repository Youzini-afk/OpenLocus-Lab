# BEA-v1-N10DN-R Corrected Deep-Rank Promotion Public Package

Date: 2026-06-30

BEA-v1-N10DN-R is a public-only package for the corrected N10DM-R suffix-safe deep-rank promotion smoke. It reads public artifacts only and performs no private reads and no recompute.

## Result

```text
status: corrected_deep_rank_promotion_public_package_complete_n10dor_authorized
self-test: 12 / 12
forbidden scan: pass
private reads in N10DN-R: 0
recomputes in N10DN-R: 0
anchor suffix-safe file top10/top20: 44 / 58
anchor projected span top10/top20: 39 / 49
positive variants: 0
harmful variants: 5
old negative conclusion still holds: true
```

## Package summary

N10DM-R corrected the matching rule to suffix-safe file reach. The corrected anchor is file `44 / 58` and projected span `39 / 49`. All five non-anchor no-duplicate-pressure deep-rank promotion variants remain harmful; the best interleave variants are below the anchor at file `40 / 58` and projected span `36 / 49`.

The package therefore keeps the deep-rank promotion line closed under suffix-safe matching and moves the mechanism route back to corrected candidate-pool absence/source analysis.

## Handoff

N10DN-R authorizes only `BEA-v1-N10DO-R Corrected Candidate-Pool Absence Source Mechanism Audit`. It does not authorize retrieval, rerun, candidate generation/materialization/add/remove, oracle insertion, selector/reranker execution, runtime/default changes, P5, BEA-v1-A, heldout/generalization claims, method-winner claims, downstream-value claims, or broad private reads.

## Artifact

- Script: `eval/bea_v1_n10dnr_corrected_deep_rank_promotion_public_package.py`
- Report: `artifacts/bea_v1_n10dnr_corrected_deep_rank_promotion_public_package/bea_v1_n10dnr_corrected_deep_rank_promotion_public_package_report.json`
