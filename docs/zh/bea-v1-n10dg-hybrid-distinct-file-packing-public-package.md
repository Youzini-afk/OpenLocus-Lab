# BEA-v1-N10DG Hybrid Distinct-File Packing Public Package

日期：2026-06-30

BEA-v1-N10DG 是 N10DF hybrid distinct-file packing smoke 的 public-only package/audit。它只读取 public N10DC/N10DE/N10DF artifacts，不进行 private reads、recompute 或 new variants。

## 结果

```text
status: hybrid_distinct_file_packing_public_package_complete_n10dh_authorized
self-test: 12 / 12
forbidden scan: pass
private reads in N10DG: 0
recomputes in N10DG: 0
N10DH authorized: true
```

## Packaged conclusion

- `prefix7_then_distinct_fill_top10` 是一个 promising top10-safe packing hybrid：它匹配 aggressive top10 span recovery（`16`），且 baseline top10 span loss 为 0。
- 它不是 default winner，也不匹配 aggressive top20 reach：prefix7 top20 span/file 是 `17 / 19`，而 aggressive top20 span/file 是 `24 / 47`。
- Candidate pool 保持不变；policy selection 不使用 gold。

## Boundary

N10DG 不授权 runtime/default behavior、selector/reranker execution、candidate generation、retrieval/rerun、broad private reads、P5、BEA-v1-A、method-winner claims、downstream-value claims 或 heldout/generalization claims。

## Handoff

N10DG 只授权 `BEA-v1-N10DH Packing Plus Span-Window or Top20 Reach Repair Experiment`，具体范围由下一份 oracle contract 限定。

## Artifact

- Script: `eval/bea_v1_n10dg_hybrid_distinct_file_packing_public_package.py`
- Report: `artifacts/bea_v1_n10dg_hybrid_distinct_file_packing_public_package/bea_v1_n10dg_hybrid_distinct_file_packing_public_package_report.json`
