# BEA-v1-FRK-A Competitive Retrieval Benchmark Package

Date: 2026-07-03

BEA-v1-FRK-A Competitive Retrieval Benchmark Package is a top-level FRK pivot benchmark, not a child of R2BV. It establishes a bounded local empirical comparison on the R14-S sanity suite.

```text
phase: BEA-v1-FRK-A Competitive Retrieval Benchmark Package
default status: frk_a_unavailable_no_explicit_local_benchmark_opt_in
success status: frk_a_benchmark_complete_frk_b_prototype_authorized
self-test: 42/42
suite: R14-S sanity
baselines: ripgrep_text_practical; same_budget_sparse_bm25; same_budget_rrf_hybrid; current_openlocus_retrieval; simple_path_symbol
excluded baseline: FastContext excluded
trace boundary: private per-query traces
public boundary: aggregate-only
next: BEA-v1-FRK-B Fast Retrieval Kernel Prototype
```

Explicit benchmark mode writes private per-query traces under ignored/private storage. The public report is aggregate-only and bucketized, with EvidenceCore citation validity buckets and no raw candidate lists, scores, ranks, spans, snippets, private roots, or private task identifiers.
