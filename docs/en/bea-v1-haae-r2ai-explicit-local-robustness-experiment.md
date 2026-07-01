# BEA-v1-HAAE-R2AI Explicit Local Robustness Experiment

Date: 2026-07-01

BEA-v1-HAAE-R2AI Explicit Local Robustness Experiment Over Existing R2AG Material is complete with source lock R2AH checkpoint `83d7997`, status `haae_r2ah_robustness_material_public_audit_package_complete_r2ai_explicit_experiment_authorized`, and inherited R2AG checkpoint `a0ac3b3`, status `haae_r2ag_explicit_local_bounded_robustness_material_generation_complete_r2ah_public_audit_authorized`.

```text
phase: BEA-v1-HAAE-R2AI Explicit Local Robustness Experiment Over Existing R2AG Material
default status: haae_r2ai_unavailable_no_explicit_existing_r2ag_material_opt_in
explicit pass status: haae_r2ai_explicit_local_robustness_experiment_complete_r2aj_public_audit_authorized_brittle_or_artifact
self-test: 26/26
default mode no private read/write/source scan/material generation/metrics
explicit existing R2AG private material root
read only existing R2AG private group files: task_frame,candidate_pool,variant_material,rank_pack,outcome_eval_private,material_qa
source_manifest_private optional schema/count only
publication: aggregate-only bucketized robustness metrics by variant/policy axis
status buckets: robust_signal / brittle_or_artifact / mixed_or_inconclusive
privacy: no exact public ranks/scores/counts/rates/MRR/task/query/path
next: BEA-v1-HAAE-R2AJ Robustness Experiment Public Audit Package
stop/go: R2AJ public audit only
```

Explicit mode requires `--allow-r2ai-robustness-experiment --existing-r2ag-private-material-root <root> --confirm-aggregate-only-publication`. The existing root must be outside the public repo, must not be a symlink or escape through group files, and must contain the R2AG private manifest and required group files. R2AI does not generate material and does not scan source/candidates.


 R2AI result marker: robustness_status_bucket brittle_or_artifact; control_response_bucket controls_match_or_exceed_signal; variant top-k/MRR buckets are aggregate-only; no method/default/scaling claim.


R2AI result: explicit experiment complete with robustness_status_bucket `brittle_or_artifact`; all reported variant top-k/MRR values are aggregate buckets, and control variants match the high signal buckets, so this is not a robust-signal/default/method/scaling claim.
