# BEA-v1-HAAE-R2AD Actual Real-File Material Experiment Public Audit Package

Date: 2026-07-03

BEA-v1-HAAE-R2AD Actual Real-File Material Experiment Public Audit Package is a public-only audit/package of the R2AC public aggregate artifact. It reads no private root or private material and does not recompute metrics from private material.

```text
phase: BEA-v1-HAAE-R2AD Actual Real-File Material Experiment Public Audit Package
status: haae_r2ad_actual_real_file_material_experiment_public_audit_package_complete_r2ae_signal_robustness_scale_decision_authorized
self-test: 15/15
R2AC checkpoint: 6f189e4
R2AC status: haae_r2ac_actual_real_file_material_experiment_complete_r2ad_public_audit_authorized_signal_present
R2AC self-test 21/21
R2AB checkpoint: 52a23da
R2AA checkpoint: f325b65
result: signal_present
metrics: aggregate-only bucket metrics
privacy: no raw leak
signal readback: symbol_name_overlap/content_identifier_fusion high bucket; query/lexical medium; control low
claim boundary: method/default/scaling false
next phase: BEA-v1-HAAE-R2AE Real-File Signal Robustness/Scale Decision
handoff scope: public decision/preflight only; not direct CI/scale/execution
```

R2AD does not read `/tmp` or any private material, recompute metrics, generate candidates/material, scan source, call retrieval/OpenLocus/runtime, or use CI/network/provider/clone. It authorizes only the next public decision/preflight phase.
