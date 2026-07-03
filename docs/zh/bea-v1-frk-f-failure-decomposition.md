# BEA-v1-FRK-F Failure Decomposition

日期：2026-07-03

BEA-v1-FRK-F Failure Decomposition 是 FRK-E no-go result 之后的 top-level FRK empirical decomposition。Default mode 不进行 private read、label read 或 decomposition。Explicit mode 读取 operator-provided private FRK-E trace root，并仅为 scoring/decomposition 使用 private R14 labels，public artifact 只发布 aggregate-only buckets。

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

当 dominant mechanism 是 baseline sufficiency 或 RRF dominance 时，FRK-F 会停止 current FRK-B/C route，而不是授权另一个 repair。它不授权 runtime/default/method/scale/RPM/CI/network/provider/FastContext 或 raw trace publication。
