# BEA-v1-HAAE-R2P Path-Cue Robustness Material Generation

日期：2026-07-03

BEA-v1-HAAE-R2P Path-Cue Robustness Material Generation 具有 safe default mode
和 explicit opt-in private material generation。它只读取 committed public R14
medium fixture rows，并且只在 explicit operator root 下写 private rows。它不读取 old
private roots，不发现 temporary roots，不使用 network、CI、OpenLocus runtime、
retrieval、source scan、provider、scheduler 或 selector systems。

```text
phase: BEA-v1-HAAE-R2P Path-Cue Robustness Material Generation
default status: haae_r2p_unavailable_no_explicit_path_cue_robustness_material_generation_opt_in
pass status: haae_r2p_path_cue_robustness_material_generation_complete_r2q_public_audit_authorized
self-test: 22/22
source lock: HAAE-R2O checkpoint 4ffc9eb
source status: haae_r2o_robustness_preflight_design_complete_r2p_path_cue_robustness_material_generation_authorized
explicit opt-in: required
target 20 tasks; candidate depth 40; row cap 20000
variants: original/path_scrambled/extension_bucket_preserved/directory_depth_preserved/control_baseline_strengthened
rank sources: path_prior/path_scrambled_prior/extension_bucket_prior/directory_depth_prior/control_baseline_strengthened/rrf_variant_fusion
gold policy: gold labels private only; ranking policy ignores gold labels
boundary: no experiment metrics in R2P
next phase: BEA-v1-HAAE-R2Q Public Audit Package
```

Public artifact 是 aggregate-only。它不发布 private root path、basename、raw task、
query、candidate path、label、score、hash、snippet 或 exact rank。R2P 只授权 R2Q
public audit package，不授权 experiment metrics。
