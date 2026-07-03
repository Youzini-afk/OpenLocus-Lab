# BEA-v1-FRK-E Downstream Utility Probe

Date: 2026-07-03

BEA-v1-FRK-E Downstream Utility Probe is a top-level executable FRK phase. It compares same-budget packs with label-independent proxy construction and private label scoring only after pack construction.

```text
phase: BEA-v1-FRK-E Downstream Utility Probe
default status: frk_e_unavailable_no_explicit_downstream_utility_probe_opt_in
success status: frk_e_downstream_utility_probe_complete_frk_f_failure_decomposition_or_proxy_expansion_authorized
no-go status: frk_e_no_go_no_proxy_lift_over_best_baseline
self-test: 50/50
source lock: FRK-D checkpoint f156849; status frk_d_incremental_update_benchmark_complete_frk_e_downstream_utility_probe_authorized
variants: bm25_like_baseline_pack; rrf_like_baseline_pack; frk_b_retrieve_fast_raw_pack; frk_c_rankpack_builder_pack
proxies: correct-file-before-first-edit proxy; evidence-before-edit proxy; wrong-file risk; empty/abstain risk; evidence budget efficiency
trace boundary: private traces
public boundary: aggregate-only
next: BEA-v1-FRK-F Failure Decomposition
```

The public report never includes raw task IDs, queries, paths, spans, snippets, candidate rows, pack rows, scores, ranks, hashes/currentness values, exact counts/rates/latencies, private roots, or trace paths.
