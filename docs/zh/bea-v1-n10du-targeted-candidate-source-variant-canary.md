# BEA-v1-N10DU Targeted Candidate-Source Variant Canary

日期：2026-06-30

BEA-v1-N10DU 是对同一组 30 个 N10DR sampled absent-pool cases 的 bounded local diagnostic canary。它仅在 existing local clone repositories 上使用 local OpenLocus CLI retrieval 测试六个固定 channel/query variants。

## 结果

```text
status: targeted_candidate_source_variant_canary_pass_n10dv_authorized
self-test: 12 / 12
forbidden scan: pass
sampled cases: 30
variant count: 6
command count: 180
cases recovered by any variant: 10
best variant: identifier_normalized_bm25_only
best variant recovery top10/top20/top50: 8 / 9 / 10
```

## Variants

- `original_regex_only`
- `original_symbol_only`
- `original_bm25_only`
- `identifier_normalized_regex_only`
- `identifier_normalized_symbol_only`
- `identifier_normalized_bm25_only`

Query normalization 是 deterministic 且 gold-free 的：alphanumeric/underscore tokens、camel/snake splitting、short-token dropping、punctuation/path separator removal、first 12 tokens，以及 empty 时 fallback to original。

## Boundary

N10DU 仅使用 existing local clone repositories。它不进行 network access、git clone、provider call、selector/reranker execution、runtime/default change、P5、BEA-v1-A、candidate generation、candidate materialization、method-winner claim、downstream-value claim 或 heldout/generalization claim。Public output 仅为 aggregate/bucket。

## Handoff

N10DU 只授权 `BEA-v1-N10DV Targeted Candidate-Source Variant Canary Public Package`。

## Artifact

- Script: `eval/bea_v1_n10du_targeted_candidate_source_variant_canary.py`
- Report: `artifacts/bea_v1_n10du_targeted_candidate_source_variant_canary/bea_v1_n10du_targeted_candidate_source_variant_canary_report.json`
