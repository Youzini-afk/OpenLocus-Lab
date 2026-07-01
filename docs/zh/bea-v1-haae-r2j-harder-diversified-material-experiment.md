# BEA-v1-HAAE-R2J Harder/Diversified Material Experiment

日期：2026-07-01

BEA-v1-HAAE-R2J Harder/Diversified Material Experiment 只在 operator 提供 explicit
private material root 时评估 existing R2I private material。默认模式不读取或写入
private。

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

显式 run 产生了 separation signal：`separation_signal_bool=true`，
`rank_spread_bucket=spread_medium`，`control_baseline_separation_bucket=non_control_better`。
Bucket-level result：`path_prior` 的 top1/top5/top10/top20 buckets 都是
`count_10_to_20`，并且是 `mrr_high`；`control_baseline` 的 top1 bucket 是
`count_0`，MRR 是 `mrr_low`。这只是 separation signal，不是 method winner/default/scaling claim。

R2J 不发现 roots，不写 private rows，不生成 candidates 或 material，不重新运行
retrieval/runtime/OpenLocus/source scan/CI/network/provider/scheduler/selector，也不发布
exact ranks、scores、paths、task ids、queries、candidate ids、snippets、labels、hashes 或
exact per-task values。
