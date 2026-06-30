# BEA-v1-N10DU Targeted Candidate-Source Variant Canary

Date: 2026-06-30

BEA-v1-N10DU is a bounded local diagnostic canary over the same 30 N10DR sampled absent-pool cases. It tests six fixed channel/query variants using local OpenLocus CLI retrieval over existing local clone repositories only.

## Result

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

Query normalization is deterministic and gold-free: alphanumeric/underscore tokens, camel/snake splitting, short-token dropping, punctuation/path separator removal, first 12 tokens, and fallback to original if empty.

## Boundary

N10DU uses existing local clone repositories only. It performs no network access, git clone, provider call, selector/reranker execution, runtime/default change, P5, BEA-v1-A, candidate generation, candidate materialization, method-winner claim, downstream-value claim, or heldout/generalization claim. Public output is aggregate/bucket-only.

## Handoff

N10DU authorizes only `BEA-v1-N10DV Targeted Candidate-Source Variant Canary Public Package`.

## Artifact

- Script: `eval/bea_v1_n10du_targeted_candidate_source_variant_canary.py`
- Report: `artifacts/bea_v1_n10du_targeted_candidate_source_variant_canary/bea_v1_n10du_targeted_candidate_source_variant_canary_report.json`
