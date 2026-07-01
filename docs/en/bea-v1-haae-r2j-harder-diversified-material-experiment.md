# BEA-v1-HAAE-R2J Harder/Diversified Material Experiment

Date: 2026-07-01

BEA-v1-HAAE-R2J Harder/Diversified Material Experiment evaluates existing R2I
private material only when an operator supplies an explicit private material
root. Default mode performs no private read or write.

```text
phase: BEA-v1-HAAE-R2J Harder/Diversified Material Experiment
default status: haae_r2j_unavailable_no_explicit_r2i_private_material_root
pass status: haae_r2j_harder_diversified_material_experiment_complete_r2k_public_audit_authorized
non-separating status: haae_r2j_harder_diversified_material_experiment_complete_no_go_non_separating
self-test: 21/21
source lock: HAAE-R2I checkpoint 16d1349
source status: haae_r2i_harder_diversified_local_material_generation_complete_r2j_experiment_authorized
explicit private material root: required
input: existing R2I material only
output: aggregate-only metrics
rank sources: bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline
diagnostics: separation diagnostics
method_winner_bool=false
boundary: no method winner/default/scaling claim
next phase: BEA-v1-HAAE-R2K Public Audit Package
```

The explicit run produced a separation signal: `separation_signal_bool=true`,
`rank_spread_bucket=spread_medium`, and `control_baseline_separation_bucket=non_control_better`.
Bucket-level result: `path_prior` reaches top1/top5/top10/top20 buckets
`count_10_to_20` with `mrr_high`; `control_baseline` has top1 bucket `count_0`
and `mrr_low`. This is only a separation signal, not a method winner/default/scaling claim.

R2J does not discover roots, write private rows, generate candidates or material,
rerun retrieval/runtime/OpenLocus/source scan/CI/network/provider/scheduler/selector,
or publish exact ranks, scores, paths, task ids, queries, candidate ids, snippets,
labels, hashes, or exact per-task values.
