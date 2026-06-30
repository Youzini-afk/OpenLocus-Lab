# BEA-v1-N10EC Normalized-BM25 Depth-to-Head Integration Audit Package

Date: 2026-06-30

BEA-v1-N10EC is a public-only package of N10EB. It reads only the N10EB public artifact and performs no private reads, retrieval, OpenLocus execution, or recompute.

## Result

```text
status: normalized_bm25_depth_to_head_integration_audit_package_complete_n10ed_authorized
self-test: 8 / 8
forbidden scan: pass
private reads: 0
retrieval executions: 0
recomputes: 0
packaged baseline top10/top20/top50/top100: 5 / 11 / 17 / 26
packaged best top10: 11
success variants: 3
```

N10EC packages the N10EB finding: putting normalized-BM25 files that are novel relative to the old N1 pool first converts the depth-only source signal into top10 recovery. The strongest top10 rules reach `11/60` with zero lost baseline top10 hits.

This remains a same-source smoke package, not runtime/default readiness, scaled retrieval, heldout/generalization, method-winner, or downstream evidence.

## Handoff

N10EC authorizes only `BEA-v1-N10ED Novel-First Depth-to-Head Mechanism Analysis`.

## Artifact

- Script: `eval/bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package.py`
- Report: `artifacts/bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package/bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package_report.json`
