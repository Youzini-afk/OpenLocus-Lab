# BEA-v1-FRK-B Fast Retrieval Kernel Prototype

日期：2026-07-03

BEA-v1-FRK-B Fast Retrieval Kernel Prototype 是 top-level FRK track phase，不是 R2BV/R2BW/HAAE continuation。它在 explicit mode 中构建 bounded local persistent fast retrieval index，并且 public results 只发布 aggregate bucketized 信息。

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

Explicit mode 在 ignored/private storage 下构建 index，验证每个 counted hit 的 EvidenceCore-like path/range/current content integrity，并且 public report 不包含 raw tasks、queries、candidates、spans、scores、ranks、hashes 或 private trace paths。
