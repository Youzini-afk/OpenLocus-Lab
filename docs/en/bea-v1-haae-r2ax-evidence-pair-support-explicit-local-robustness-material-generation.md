# BEA-v1-HAAE-R2AX Evidence-Pair Support Explicit Local Robustness Material Generation

Date: 2026-07-01

BEA-v1-HAAE-R2AX Evidence-Pair Support Explicit Local Robustness Material Generation has a default mode and an explicit mode. In default mode it performs no private read/write/generation/scan/metrics and writes only an unavailable aggregate-only public artifact. Explicit mode requires operator flags for existing R2AN private material, a private output root, no experiment metrics, and aggregate-only public artifact.

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

R2AX generates private robustness material only. It does not compute hit rates, MRR, ranks, scores, success rates, or interpretation metrics; it does not scan source/candidate/corpus or run runtime/OpenLocus/retrieval.
