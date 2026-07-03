# BEA-v1-FRK-B Fast Retrieval Kernel Prototype

Date: 2026-07-03

BEA-v1-FRK-B Fast Retrieval Kernel Prototype is a top-level FRK track phase, not an R2BV/R2BW/HAAE continuation. It builds a bounded local persistent fast retrieval index in explicit mode and publishes only aggregate bucketized public results.

```text
phase: BEA-v1-FRK-B Fast Retrieval Kernel Prototype
default status: frk_b_unavailable_no_explicit_local_prototype_opt_in
success status: frk_b_fast_retrieval_kernel_prototype_complete_frk_c_public_package_authorized
self-test: 44/44
source lock: FRK-A checkpoint efcfec6; status frk_a_benchmark_complete_frk_b_prototype_authorized
suite: R14-S sanity
index components: sparse_term_index; symbol_name_index; path_filename_config_index; ast_span_index
API: retrieve_fast
baselines: ripgrep_text_practical; same_budget_sparse_bm25; same_budget_rrf_hybrid; simple_path_symbol
excluded baseline: FastContext excluded
trace boundary: private per-query traces
public boundary: aggregate-only
next: BEA-v1-FRK-C Fast Retrieval Kernel Public Package
```

Explicit mode builds the index under ignored/private storage, validates each counted hit for EvidenceCore-like path/range/current content integrity, and keeps raw tasks, queries, candidates, spans, scores, ranks, hashes, and private trace paths out of the public report.
