# BEA-v1-FRK-D Incremental Update Benchmark

日期：2026-07-03

BEA-v1-FRK-D Incremental Update Benchmark 是 top-level executable FRK benchmark。它创建 private temporary corpus snapshot，只在该 snapshot 中应用 deterministic mutations，对比 incremental update、cold rebuild 和 stale negative control，并且只发布 aggregate-only buckets。

```text
phase: BEA-v1-FRK-D Incremental Update Benchmark
default status: frk_d_unavailable_no_explicit_incremental_update_benchmark_opt_in
success status: frk_d_incremental_update_benchmark_complete_frk_e_downstream_utility_probe_authorized
self-test: 52/52
source lock: FRK-C checkpoint 2218554; status frk_c_rankpack_builder_experiment_complete_frk_d_incremental_update_benchmark_authorized
mutations: symbol/alias insertion; path-term relevant edit; AST-span movement; stale-candidate trap; unaffected sentinel
arms: cold_rebuild_after_update; incremental_update_path; stale_index_negative_control
trace boundary: private traces
public boundary: aggregate-only
next: BEA-v1-FRK-E Downstream Utility Probe
```

Public report 不包含 raw task IDs、queries、paths、spans、snippets、candidates、packs、scores、ranks、hashes、exact latencies、private roots 或 temporary paths。
