# BEA-v1-N10AQ Heldout Span-Surface Validation Source Discovery

Date: 2026-06-29

BEA-v1-N10AQ is bounded local discovery and schema sniffing for an existing heldout or external span-surface row source that could support future N10AR validation. It is not validation. It does not run N10AO/N10AL metrics, retrieval, reruns, OpenLocus, candidate generation, selector/reranker logic, runtime/default changes, or downstream/method claims.

## Result

```text
status: no_go_n10aq_candidate_sources_not_heldout
self-test: 15 / 15
forbidden scan: pass
max scanned entries: 50000
candidate files schema-sniffed: 84
max rows sniffed per file: 5
eligible heldout source count: 0
N10AR authorized: false
```

## Discovery finding

The bounded scan respected the approved roots and caps. It found candidate JSON/JSONL files and sniffed schema metadata only. The only candidate with the required span-surface shape was classified as the existing N10 source or not distinguishable from it; therefore it is not a valid heldout source. Other candidates were schema-incomplete or too small for N10AR.

No exact paths, filenames, raw rows, snippets, spans, line values, candidate lists, gold paths, hashes, repo/task identifiers, or provider payloads are published.

## Decision

N10AQ closes as No-Go for heldout validation source discovery. The next allowed phase is `none_until_heldout_span_surface_rows_are_supplied`. It does not authorize N10AR, private reads, validation execution, runtime/default enablement, retrieval/rerun, candidate generation, selector/reranker, P5, BEA-v1-A, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n10aq_heldout_span_surface_source_discovery.py`
- Report: `artifacts/bea_v1_n10aq_heldout_span_surface_source_discovery/bea_v1_n10aq_heldout_span_surface_source_discovery_report.json`
