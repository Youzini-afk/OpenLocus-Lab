# BEA-v1-HAAE-R2P Path-Cue Robustness Material Generation

Date: 2026-07-01

BEA-v1-HAAE-R2P Path-Cue Robustness Material Generation has safe default mode
and explicit opt-in private material generation. It reads committed public R14
medium fixture rows only and writes private rows only under an explicit operator
root. It does not read old private roots, discover temporary roots, use network,
CI, OpenLocus runtime, retrieval, source scan, provider, scheduler, or selector
systems.

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

The public artifact is aggregate-only. It publishes no private root path,
basename, raw task, query, candidate path, label, score, hash, snippet, or exact
rank. R2P authorizes only the R2Q public audit package, not experiment metrics.
