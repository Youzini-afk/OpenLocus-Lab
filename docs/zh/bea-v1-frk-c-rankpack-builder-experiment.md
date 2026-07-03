# BEA-v1-FRK-C RankPack Builder Experiment

日期：2026-07-03

BEA-v1-FRK-C RankPack Builder Experiment 是 concrete executable FRK experiment。它使用 FRK-B `retrieve_fast` candidate pools，并在 pack construction 之后才用 private R14-S labels 比较固定 RankPack construction arms。

```text
phase: BEA-v1-FRK-C RankPack Builder Experiment
default status: frk_c_unavailable_no_explicit_rankpack_experiment_opt_in
success status: frk_c_rankpack_builder_experiment_complete_frk_d_incremental_update_benchmark_authorized
self-test: 45/45
source lock: FRK-B checkpoint 11f9cf8; status frk_b_fast_retrieval_kernel_prototype_complete_frk_c_public_package_authorized
pack arms: raw_score_order_pack; file_dedup_pack; ast_span_priority_pack; path_symbol_balanced_pack; diversity_budget_pack
candidate source: FRK-B retrieve_fast
trace boundary: private per-query RankPack traces
public boundary: aggregate-only
next: BEA-v1-FRK-D Incremental Update Benchmark
```

Public report 只包含 bucketized aggregate metrics，不包含 raw task IDs、queries、paths、spans、snippets、candidate rows、pack rows、scores、ranks、hashes 或 trace paths。
