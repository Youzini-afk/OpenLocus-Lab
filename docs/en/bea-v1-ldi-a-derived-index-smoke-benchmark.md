# BEA-v1-LDI-A Derived Index Smoke Benchmark

Date: 2026-07-03

BEA-v1-LDI-A Derived Index Smoke Benchmark is a local deterministic derived metadata index smoke on R14-S. Derived metadata != Evidence: counted hits must rematerialize current source path/range/hash, while public output remains aggregate-only.

```text
phase: BEA-v1-LDI-A Derived Index Smoke Benchmark
default status: ldi_a_unavailable_no_explicit_derived_index_smoke_opt_in
go status: ldi_a_derived_index_smoke_complete_ldi_b_local_llm_or_tag_expansion_authorized
no-go status: ldi_a_stop_derived_index_route_baseline_sufficient
no-lift status: ldi_a_no_go_no_lift_over_best_baseline
self-test: 48/48
source: FRK-F checkpoint 63528e8; status frk_f_stop_current_frk_b_c_pack_route_baseline_sufficient
variants: bm25_like_baseline; rrf_like_baseline; path_symbol_baseline; frk_b_retrieve_fast_baseline; ldi_derived_index_variant
derived metadata: symbol names; file/path role tags; function/type/module role buckets; comment/doc keywords; normalized aliases; AST-ish span type; phrase expansion
public boundary: aggregate-only
```

Explicit mode writes private traces under ignored/private storage and uses private R14 labels only for scoring after retrieval. No provider, network, LLM, FastContext, runtime/default/method/scale, raw tags, paths, tasks, queries, scores, ranks, or hashes are published.
