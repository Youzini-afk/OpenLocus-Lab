# BEA-v1-HAAE-R2AZ Evidence-Pair Support Explicit Local Robustness Experiment

日期：2026-07-01

BEA-v1-HAAE-R2AZ Evidence-Pair Support Explicit Local Robustness Experiment 支持 default/no-op mode 与 explicit opt-in mode。Default/no-op mode reads no private root，不写 private output，不计算 metrics。Explicit opt-in mode 读取 existing R2AX private robustness material，并且只计算 bucketized aggregate robustness metrics。 Result: `artifact_likely`; `support_control_separation_collapsed`, `control_rejection_failed`, `path_confound_risk_elevated`, and `support_signal_bucket_low`.

```text
phase: BEA-v1-HAAE-R2AZ Evidence-Pair Support Explicit Local Robustness Experiment
default status: haae_r2az_unavailable_no_explicit_local_robustness_experiment_opt_in
explicit result status: haae_r2az_explicit_local_robustness_experiment_complete_r2ba_public_audit_authorized_artifact_likely
self-test: 27/27
source: R2AY checkpoint 126dc18; R2AY status haae_r2ay_evidence_pair_support_robustness_material_public_audit_complete_r2az_experiment_authorized
source locks: R2AX checkpoint f3add65; R2AW checkpoint bc44454; R2AN checkpoint 93bba5f; R2AT checkpoint 0c9c108; R2AP checkpoint 87ea9de
mode: default/no-op mode reads no private root
explicit: explicit opt-in mode; existing R2AX private robustness material; bucketized aggregate robustness metrics
boundary: no material generation; no source/candidate/corpus scan; no runtime/OpenLocus/retrieval
next: BEA-v1-HAAE-R2BA Evidence-Pair Support Robustness Experiment Public Audit Package
```

Public output 仅 aggregate-only，并排除 private root paths、basenames、task IDs、queries、private evidence/pair/source keys、raw rows、snippets、gold labels、exact counts/rates/ranks/scores/hit rates/MRR/top-k。

R2AZ readback marker: BEA-v1-HAAE-R2AZ Evidence-Pair Support Explicit Local Robustness Experiment; haae_r2az_unavailable_no_explicit_local_robustness_experiment_opt_in; haae_r2az_explicit_local_robustness_experiment_complete_r2ba_public_audit_authorized_artifact_likely; self-test `27/27`; R2AY checkpoint `126dc18`; R2AY status `haae_r2ay_evidence_pair_support_robustness_material_public_audit_complete_r2az_experiment_authorized`; R2AX checkpoint `f3add65`; R2AW checkpoint `bc44454`; R2AN checkpoint `93bba5f`; R2AT checkpoint `0c9c108`; R2AP checkpoint `87ea9de`; default/no-op mode; reads no private root; explicit opt-in mode; existing R2AX private robustness material; bucketized aggregate robustness metrics; artifact_likely; support_control_separation_collapsed; control_rejection_failed; path_confound_risk_elevated; support_signal_bucket_low; no material generation; no source/candidate/corpus scan; no runtime/OpenLocus/retrieval; BEA-v1-HAAE-R2BA Evidence-Pair Support Robustness Experiment Public Audit Package.
