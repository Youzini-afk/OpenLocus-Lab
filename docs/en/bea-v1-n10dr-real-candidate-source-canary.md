# BEA-v1-N10DR Real Candidate-Source Canary

Date: 2026-06-30

BEA-v1-N10DR is a bounded local candidate-source canary. It runs the local OpenLocus CLI against existing local clone repositories only, using the scoped N1 private span rows and a deterministic 30-case absent-pool sample. It performs no network access, git clone, provider call, selector/reranker execution, runtime/default change, P5, or BEA-v1-A action.

## Result

```text
status: real_candidate_source_canary_complete_no_recovery
self-test: 12 / 12
forbidden scan: pass
sampled cases: 30
executed cases: 30
local repos available: 30
retrieval command successes: 28
gold file recovered top10/top20/top50: 0 / 0 / 0
N10DS authorized: true
```

## Canary design

- Sample source: corrected suffix-safe absent-pool residuals.
- Target sample: 10 tiny-pool, 10 moderate-pool, and 10 rich-wrong-pool cases.
- Sampling: deterministic, stable private row order; no random sampling.
- Retrieval command boundary: local OpenLocus CLI retrieval with `regex,bm25,symbol`, max results `50`, JSON output, existing clone repository as working directory.
- Private outputs: three ignored project-private output files were written for candidate rows, manifest, and bucketed logs.

## Findings

- No sampled case recovered the gold file in the top50 returned candidates.
- Recovery by pool richness was `0/10` for tiny, `0/10` for moderate, and `0/10` for rich-wrong buckets.
- This does not change the full-denominator anchor and does not prove broader source failure; it only says this bounded local canary found no recovery.

## Boundary

N10DR is a local canary, not a scaled retrieval result, method winner, downstream-value claim, heldout/generalization claim, or runtime/default recommendation. Public outputs contain aggregate/bucket records only and no private paths, filenames, candidate lists, snippets, spans/lines, gold labels, exact ranks, or raw rows.

## Handoff

N10DR authorizes only `BEA-v1-N10DS Real Candidate-Source Canary Audit Package`. It does not authorize scaled retrieval, network access, git clone, provider calls, candidate generation/materialization, selector/reranker execution, runtime/default changes, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10dr_real_candidate_source_canary.py`
- Report: `artifacts/bea_v1_n10dr_real_candidate_source_canary/bea_v1_n10dr_real_candidate_source_canary_report.json`
