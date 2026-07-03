# BEA-v1-LDI-A Derived Index Smoke Benchmark

日期：2026-07-03

BEA-v1-LDI-A Derived Index Smoke Benchmark 是 R14-S 上的 local deterministic derived metadata index smoke。Derived metadata != Evidence：counted hits 必须 rematerialize current source path/range/hash，同时 public output 保持 aggregate-only。

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

Explicit mode 将 private traces 写入 ignored/private storage，并且仅在 retrieval 后使用 private R14 labels 进行 scoring。不发布 provider、network、LLM、FastContext、runtime/default/method/scale、raw tags、paths、tasks、queries、scores、ranks 或 hashes。
