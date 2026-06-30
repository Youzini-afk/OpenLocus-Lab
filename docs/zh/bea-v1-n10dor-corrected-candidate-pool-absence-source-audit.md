# BEA-v1-N10DO-R Corrected Candidate-Pool Absence / Source Mechanism Audit

日期：2026-06-30

BEA-v1-N10DO-R 使用 suffix-safe file matching 作为 primary rule，重新执行 candidate-pool absence/source audit。它读取 same scoped N1 span rows 以及 public N10DO/N10DM-R/N10DN-R/N10DL artifacts。它不运行 retrieval，不 rerun OpenLocus，不 generate/materialize/add/remove candidates，不插入 oracle candidates，不运行 selector/reranker，也不改变 runtime/default behavior。

## 结果

```text
status: corrected_candidate_pool_absence_source_audit_complete_n10dp_authorized
self-test: 12 / 12
forbidden scan: pass
private span rows read: 213
top10 file hit / miss: 44 / 169
top20 file hit: 58
rank11-20 reachable: 14
rank21-50 reachable: 14
absent from observed pool: 141
```

## Findings

- Suffix-safe matching 是 primary file-reach rule。
- 在 169 个 top10 file misses 中，141 个 gold file 不在 observed N1 pool 中。
- Same-pool movement 只能处理 ranks 11-50 中的 28 个 misses。
- Source/channel、retrieval method、score、language/repo/task 与 query/category fields 对 targeted policy use 来说 unavailable 或 incomplete。

## Handoff

N10DO-R 只授权 `BEA-v1-N10DP Oracle Candidate-Insertion Ceiling Smoke`。N10DO-R 本身不授权 retrieval、rerun、candidate generation、materialization、oracle insertion、selector/reranker execution、runtime/default changes、P5、BEA-v1-A、method-winner claims、downstream-value claims 或 heldout/generalization claims。

## Artifact

- Script: `eval/bea_v1_n10dor_corrected_candidate_pool_absence_source_audit.py`
- Report: `artifacts/bea_v1_n10dor_corrected_candidate_pool_absence_source_audit/bea_v1_n10dor_corrected_candidate_pool_absence_source_audit_report.json`
