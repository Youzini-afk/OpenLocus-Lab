# BEA-v1-N10DV Targeted Candidate-Source Variant Canary Public Package

日期：2026-06-30

BEA-v1-N10DV 是 N10DU targeted candidate-source variant canary 的 public-only package。它只读取 public N10DU artifact，不进行 private reads、recomputation 或 retrieval。

## 结果

```text
status: targeted_candidate_source_variant_canary_public_package_complete_n10dw_authorized
self-test: 8 / 8
forbidden scan: pass
private reads in N10DV: 0
recomputes in N10DV: 0
N10DW authorized: true
```

## Packaged N10DU signal

- Same-30-case targeted canary pass。
- N10DU 测试了 6 个 fixed variants，并执行了 180 个 local commands。
- Best variant：`identifier_normalized_bm25_only`。
- Best variant recovered gold file top10/top20/top50：`8 / 9 / 10`。
- Cases recovered by any variant：`10`。
- Original BM25 以及所有 regex/symbol variants recovered `0`。

## Boundary

这是强 same-30-case targeted canary signal，不是 scaling，不是 heldout，不是 method winner，不是 downstream evidence，也不是 runtime/default behavior。

## Handoff

N10DV 只授权 `BEA-v1-N10DW Normalized-BM25 Recovery Mechanism Analysis`。它不授权 scaled retrieval、network、git clone、provider calls、candidate generation/materialization、selector/reranker execution、runtime/default changes、P5、BEA-v1-A、method/downstream claims、heldout/generalization claims 或 broad private reads。

## Artifact

- Script: `eval/bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package.py`
- Report: `artifacts/bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package/bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package_report.json`
