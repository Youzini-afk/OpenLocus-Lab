# BEA-v1-HAAE-R2AH Robustness Material Public Audit Package

Date: 2026-07-03

BEA-v1-HAAE-R2AH Robustness Material Public Audit Package is a public-only audit after R2AG checkpoint `a0ac3b3`. It read only committed R2AG public artifact and performs no private root read, no recompute material, no experiment metrics, and no source/candidate scan.

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

R2AH audits only the aggregate R2AG public report: source lock, material count/bound buckets, variant coverage, private manifest group-count buckets, rank policy no gold/path, public artifact privacy, no metrics, and stop/go. If all gates pass, it authorizes only R2AI for an explicit local robustness experiment over existing R2AG private material. R2AH does not authorize CI, network, new generation, default changes, method claims, scale claims, or raw publication.


R2AH readback marker: no experiment metrics in R2AH; R2AI aggregate-only experiment metrics authorized.
