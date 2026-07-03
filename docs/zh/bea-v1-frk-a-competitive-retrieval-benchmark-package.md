# BEA-v1-FRK-A Competitive Retrieval Benchmark Package

日期：2026-07-03

BEA-v1-FRK-A Competitive Retrieval Benchmark Package 是 top-level FRK pivot benchmark，不是 R2BV 的子阶段。它在 R14-S sanity suite 上建立 bounded local empirical comparison。

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

Explicit benchmark mode 将 private per-query traces 写入 ignored/private storage。Public report 是 aggregate-only 且 bucketized，包含 EvidenceCore citation validity buckets，不包含 raw candidate lists、scores、ranks、spans、snippets、private roots 或 private task identifiers。
