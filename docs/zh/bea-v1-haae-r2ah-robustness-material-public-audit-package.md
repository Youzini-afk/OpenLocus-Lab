# BEA-v1-HAAE-R2AH Robustness Material Public Audit Package

日期：2026-07-01

BEA-v1-HAAE-R2AH Robustness Material Public Audit Package 是 R2AG checkpoint `a0ac3b3` 之后的 public-only audit。它 read only committed R2AG public artifact，并且 no private root read、no recompute material、no experiment metrics、no source/candidate scan。

```text
phase: BEA-v1-HAAE-R2AH Robustness Material Public Audit Package
status: haae_r2ah_robustness_material_public_audit_package_complete_r2ai_explicit_experiment_authorized
self-test: 21/21
source lock: HAAE-R2AG checkpoint a0ac3b3
source status: haae_r2ag_explicit_local_bounded_robustness_material_generation_complete_r2ah_public_audit_authorized
audit: public-only audit; read only committed R2AG public artifact
boundary: no private root read; no recompute material; no experiment metrics; no source/candidate scan
material: target 20; depth 40; row cap 20000
variants: symbol_content_ablation/query_token_masking/shuffled_content_control/negative_control_strengthening
policy: rank policy no gold/path; aggregate-only privacy
next: BEA-v1-HAAE-R2AI Explicit Local Robustness Experiment Over Existing R2AG Material
stop/go: explicit local robustness experiment over existing R2AG private material; R2AI aggregate-only experiment metrics authorized; no CI/network/new generation/default/method/scale/raw publication
```

R2AH 只审计 aggregate R2AG public report：source lock、material count/bound buckets、variant coverage、private manifest group-count buckets、rank policy no gold/path、public artifact privacy、no metrics 和 stop/go。所有 gates 通过时，它只授权 R2AI 对 existing R2AG private material 做 explicit local robustness experiment。R2AH 不授权 CI、network、new generation、default changes、method claims、scale claims 或 raw publication。


R2AH readback marker: no experiment metrics in R2AH; R2AI aggregate-only experiment metrics authorized.
