# BEA-v1-HAAE-R2AX Evidence-Pair Support Explicit Local Robustness Material Generation

日期：2026-07-03

BEA-v1-HAAE-R2AX Evidence-Pair Support Explicit Local Robustness Material Generation 包含 default mode 与 explicit mode。Default mode 不进行 private read/write/generation/scan/metrics，只写 unavailable aggregate-only public artifact。Explicit mode 需要 operator flags 指定 existing R2AN private material、private output root、no experiment metrics 与 aggregate-only public artifact。

```text
phase: BEA-v1-HAAE-R2AX Evidence-Pair Support Explicit Local Robustness Material Generation
default status: haae_r2ax_unavailable_no_explicit_local_robustness_material_generation_opt_in
explicit status: haae_r2ax_explicit_local_robustness_material_generation_complete_r2ay_public_audit_authorized
self-test: 31/31
source: R2AW checkpoint bc44454; R2AW status haae_r2aw_evidence_pair_support_robustness_material_generation_public_design_preflight_complete_r2ax_explicit_local_robustness_material_generation_authorized
source: R2AN checkpoint 93bba5f
default mode: no private read/write/generation/scan/metrics
explicit mode: explicit local robustness material generation; existing R2AN private material; private output root; no experiment metrics; aggregate-only public artifact
variants: single_unit_ablation; support_contrast_perturbation; hard_negative_strengthening; shuffled_pair_control; query_evidence_masking; path_token_confound_stress; cross_task_mismatch_control; gold_isolation_control
next: BEA-v1-HAAE-R2AY Evidence-Pair Support Robustness Material Public Audit Package
```

R2AX 只生成 private robustness material。不计算 hit rates、MRR、ranks、scores、success rates 或 interpretation metrics；不 scan source/candidate/corpus，也不运行 runtime/OpenLocus/retrieval。
