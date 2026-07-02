# BEA-v1-HAAE-R2I Harder/Diversified Local Material Generation Smoke

日期：2026-07-03

BEA-v1-HAAE-R2I Harder/Diversified Local Material Generation Smoke 是 R2H 授权的
bounded local/manual material generation smoke。默认模式不读取、写入或生成 private。

```text
phase: BEA-v1-HAAE-R2I Harder/Diversified Local Material Generation Smoke
default status: haae_r2i_unavailable_no_explicit_harder_diversified_material_generation_opt_in
pass status: haae_r2i_harder_diversified_local_material_generation_complete_r2j_experiment_authorized
self-test: 21/21
source lock: HAAE-R2H checkpoint 3db7366
source status: haae_r2h_next_step_design_decision_complete_r2i_harder_diversified_material_generation_authorized
explicit opt-in: required
target: target 20 tasks
candidate depth: candidate depth 40
private row cap: private row cap 10000
rank sources: bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline
experiment metrics: no experiment metrics in R2I
next phase: BEA-v1-HAAE-R2J Harder/Diversified Material Experiment
```

Explicit mode 只在显式 operator root 下写 private rows。Public output 仅为 aggregate-only，
不包含 raw task、query、candidate path、label、score、hash、snippet、private path 或
exact per-task value。R2I 只授权 R2J；R2J 必须读取 existing R2I material，并且只计算
aggregate metrics。
