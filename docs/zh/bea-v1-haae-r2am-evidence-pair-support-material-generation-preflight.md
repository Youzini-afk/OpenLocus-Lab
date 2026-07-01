# BEA-v1-HAAE-R2AM Evidence-Pair Support Material Generation Preflight

日期：2026-07-01

BEA-v1-HAAE-R2AM Evidence-Pair Support Material Generation Preflight 是 public-only material-generation preflight。它锁定 R2AL checkpoint `39800bf`、status `haae_r2al_new_signal_family_public_design_preflight_complete_r2am_material_generation_preflight_authorized`、R2AL self-test 28/28，以及 selected family `evidence_pair_support_complementarity`。

```text
phase: BEA-v1-HAAE-R2AM Evidence-Pair Support Material Generation Preflight
status: haae_r2am_evidence_pair_support_material_generation_preflight_complete_r2an_explicit_material_generation_authorized
self-test: 26/26
R2AN phase: BEA-v1-HAAE-R2AN Evidence-Pair Support Explicit Material Generation
mode: default mode no-op; explicit mode requires private output root, public corpus manifest, allow flag, confirm private output, confirm no experiment metrics
target_task_count=20
evidence_unit_depth_cap_per_task=40
support_pair_cap_per_task=120
contrast_control_pair_cap_per_task=80
total_pair_cap_per_task=200
source_file_cap=500
private_row_cap=20000
wall_clock_cap_minutes=20
source: bounded public source allowlist required; network/clone/provider forbidden
schema: bea_v1_haae_r2an_evidence_pair_support_material_generation_v1
groups: task_frame, source_manifest_private, evidence_unit_pool, evidence_pair_material, support_relation_material, contrast_control_material, outcome_eval_private, material_qa
pairs: target_support_pair, complementary_support_pair, contrastive_hard_negative_pair, single_unit_ablation_control, shuffled_relation_control, cross_task_mismatch_control
policy: gold private eval only; single-rank content/path signal forbidden; material QA only
next audit: BEA-v1-HAAE-R2AO Evidence-Pair Support Material Public Audit Package
claims: no method/default/scale/winner/validated-signal claims
```

R2AM 只授权这些 bounds 下的 explicit local R2AN material generation。R2AN 不得计算 experiment metrics，并且成功 material QA 后只能发布 aggregate public artifact。
