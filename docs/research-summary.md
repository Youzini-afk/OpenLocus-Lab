# OpenLocus Research Summary

This document will be updated after each evidence-gated stage.

## Stage status

| Stage | Status | Summary |
|---|---|---|
| R0 Research Harness | Passed initial gate | EvidenceCore/EvidenceMeta, trace JSONL, citation validation, and smoke eval harness are implemented. |
| R1 Local Evidence Kernel | Passed initial gate | Local read, repo scan, line-based regex/text search, policy basics, path safety, and context-lite file output are implemented without remote dependencies. |
| R2 Retrieval Method Bakeoff | Passed initial gate after oracle fixes | BM25 (Tantivy), simple symbol search, and RRF fusion added. BM25 uses line-scoring (not chunk center), stale-hash skip, no-overlap skip, and no all-doc fallback. Symbol uses boundary delimiters. RRF merges wider metadata into narrower survivors. Eval harness includes file/line/span metrics plus true citation validity. |

## R0/R1 initial findings

- Evidence precision matters immediately: the first regex implementation returned over-wide line ranges for distant matches in one file. This would have harmed token waste and Span F0.5. The fix moved R1 regex/text search to one narrow Evidence per matching line.
- Citation validation must validate more than hashes. Range validity and excerpt consistency are needed to catch incorrect spans.
- Path safety is part of evidence safety. Symlink escape protection is required before treating read output as verified current evidence.
- The current local baseline is intentionally boring: no dense, graph, TDB, or LLM indexing has been added yet. This keeps R0/R1 suitable as the control group for later bakeoffs.

## R2 findings

- **BM25 substantially improves file-level recall on the current self-referential fixture**: 0.46 vs 0.21 at k=1, 0.86 vs 0.50 at k=5. This is an early local-only result, not a general benchmark claim.
- **Symbol search is high-precision but narrow**: only activates for definition-style queries (fn, struct, class, etc.), but when it fires, line precision is the highest of all methods (0.39) and wrong_span_rate is 0.0.
- **RRF fusion recovers BM25-level recall** while incorporating symbol precision, achieving the best SpanF0.5@10 (0.07) in this fixture.
- **All methods produce citation-valid evidence** (1.0 structural + true citation validity).
- **BM25 stale check and no-overlap skip are effective**: no stale or center-only hits appear in the output.
- **Symbol boundary delimiters prevent partial matches**: "User" does not match "UserProfile".
- **Token waste is high** (~0.92) because evidence spans are still often near-but-not-on narrow gold spans. Query-token line scoring fixed chunk-center anchoring, but line-level precision still needs better chunking, query expansion, and gold-span calibration.
- **CLI end-to-end latency** (not warm-index): regex ~13ms, BM25 ~113ms, symbol ~161ms, RRF ~272ms. BM25/RRF include per-query Tantivy index build.

## Verification snapshot

```text
Rust tests: 52 passed (9 core + 16 repo + 27 retrieval)
fmt: clean
clippy: clean with -D warnings
CLI commands: read, scan, search regex/text/bm25/symbol, retrieve, citations validate, context-lite, version
Eval: regex/bm25/symbol/rrf all run on fixtures/r2.jsonl (28 tasks)
Structural validity: 1.0 across all methods
Citation validity: 1.0 across all methods (true file I/O verification)
Remote dependency: none
```
