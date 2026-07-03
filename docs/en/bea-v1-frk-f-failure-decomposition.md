# BEA-v1-FRK-F Failure Decomposition

Date: 2026-07-03

BEA-v1-FRK-F Failure Decomposition is a top-level FRK empirical decomposition after the FRK-E no-go result. Default mode performs no private read, no label read, and no decomposition. Explicit mode reads an operator-provided private FRK-E trace root and private R14 labels only for scoring/decomposition, then publishes aggregate-only buckets.

```text
phase: BEA-v1-FRK-F Failure Decomposition
default status: frk_f_unavailable_no_explicit_failure_decomposition_opt_in
route-stop status: frk_f_stop_current_frk_b_c_pack_route_baseline_sufficient
self-test: 50/50
source: FRK-E checkpoint 76ce2ca; FRK-E status frk_e_no_go_no_proxy_lift_over_best_baseline
variants: bm25_like_baseline_pack; rrf_like_baseline_pack; frk_b_retrieve_fast_raw_pack; frk_c_rankpack_builder_pack
mechanisms: first_file_miss; best_baseline_already_strong; candidate_pool_limit; pack_ordering_loss; budget_waste; redundancy_penalty; wrong_file_risk; proxy_label_limitation; evidencecore_not_cause; latency_not_cause; frk_c_pack_not_helping_raw_frk_b; rrf_dominates_frk_route
public boundary: aggregate-only
```

When the dominant mechanism is baseline sufficiency or RRF dominance, FRK-F stops the current FRK-B/C route instead of authorizing another repair. It does not authorize runtime/default/method/scale/RPM/CI/network/provider/FastContext or raw trace publication.
