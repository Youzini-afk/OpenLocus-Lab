# BEA-v1-HAAE-R2AF Real-File Signal Robustness Material Preflight

Date: 2026-07-01

BEA-v1-HAAE-R2AF Real-File Signal Robustness Material Preflight is a public-only design/preflight package after R2AE checkpoint `4be50bc`. It reads only committed public R2AE artifact/docs. It performs no private reads/writes, no execution, no source scan, and no candidate/material generation in R2AF.

```text
phase: BEA-v1-HAAE-R2AF Real-File Signal Robustness Material Preflight
status: haae_r2af_real_file_signal_robustness_material_preflight_complete_r2ag_material_generation_authorized
self-test: 26/26
source lock: HAAE-R2AE checkpoint 4be50bc
source status: haae_r2ae_real_file_signal_robustness_scale_decision_complete_r2af_robustness_material_preflight_authorized
R2AG design: target 20 existing R2AA task frame if available; depth 40; row cap 20000
R2AG variants: symbol/content ablation; query-token masking; shuffled content control; negative/control strengthening
R2AG boundary: explicit private root; bounded public corpus manifest; aggregate-only public artifact; no metrics in R2AG beyond material QA
authorization: authorize only R2AG material generation; no R2AH experiment; no CI/scale/default/method claim
R2AF boundary: no private reads/writes; no execution; no source scan; no candidate/material generation
```

## Decision

R2AF packages the robustness-material design needed before any further real-file signal claim. The next authorized phase is **BEA-v1-HAAE-R2AG Explicit Local Bounded Robustness Material Generation** only. R2AG must use an explicit private root, prefer the existing R2AA task frame with target 20 if available, cap candidate depth at depth 40, cap private rows at row cap 20000, and publish only an aggregate-only public artifact backed by a bounded public corpus manifest.

The required variant suite tests real-file signal robustness without path/gold leakage: symbol/content ablation, query-token masking, shuffled content control, and negative/control strengthening. R2AG may perform material QA only; no metrics in R2AG beyond material QA are authorized. R2AF does not authorize an R2AH experiment, CI, scale, runtime/default changes, method claims, source scan, execution, or candidate/material generation in R2AF.

 R2AG local execution authorized; R2AG private write authorized; R2AG bounded source scan authorized; R2AG candidate/material generation authorized; broad source scan, CI, network/provider/clone, experiment metrics, default/method/scale claims remain forbidden.
