# BEA-v1-N10EA Normalized-BM25 Expanded Canary Public Package

Date: 2026-06-30

BEA-v1-N10EA is a public-only package of N10DZ. It reads only the public N10DZ artifact and performs no private reads, retrieval, OpenLocus execution, or recompute.

## Result

```text
status: normalized_bm25_expanded_canary_public_package_complete_n10eb_authorized
self-test: 8 / 8
forbidden scan: pass
private reads: 0
retrieval executions: 0
recomputes: 0
primary top50/cap12 top10/top20/top50/top100: 5 / 11 / 17 / 17
depth top100/cap12 top10/top20/top50/top100: 5 / 11 / 17 / 26
```

## Interpretation

N10DZ is low-recovery by the head gate: the primary top50/cap12 setting recovered only `5/60` at top10, below the pass threshold of 10. It still shows a source signal at depth: top50 recovered `17/60`, and top100 recovered `26/60`. The top100 gain is depth-only and does not improve top10.

N10EA does not claim statistical generalization, runtime/default readiness, method winner status, or downstream value.

## Handoff

N10EA authorizes only `BEA-v1-N10EB Normalized-BM25 Depth-to-Head Integration Experiment`.

## Artifact

- Script: `eval/bea_v1_n10ea_normalized_bm25_expanded_canary_public_package.py`
- Report: `artifacts/bea_v1_n10ea_normalized_bm25_expanded_canary_public_package/bea_v1_n10ea_normalized_bm25_expanded_canary_public_package_report.json`
