# BEA-v1-HAAE-R2BD Evidence-Pair Support Redesigned Material Generation Public Design Preflight

Date: 2026-07-03

BEA-v1-HAAE-R2BD Evidence-Pair Support Redesigned Material Generation Public Design Preflight is public-only and non-executing. It converts R2BC redesign requirements into a fail-closed contract for future R2BE explicit local redesigned material generation.

```text
phase: BEA-v1-HAAE-R2BD Evidence-Pair Support Redesigned Material Generation Public Design Preflight
status: haae_r2bd_evidence_pair_support_redesigned_material_generation_public_design_preflight_complete_r2be_explicit_local_redesigned_material_generation_authorized
self-test: 47/47
source: R2BC checkpoint 2171b20; R2BC status haae_r2bc_evidence_pair_support_mechanism_redesign_public_design_preflight_complete_r2bd_redesigned_material_generation_public_design_preflight_authorized
locks: R2BB checkpoint a624728; R2BA checkpoint f8984bf; R2AZ checkpoint 72590e5
future R2BE private schema groups: redesigned_task_frame; redesigned_source_manifest_private; redesigned_evidence_unit_pool; redesigned_support_pair_material; redesigned_control_pair_material; redesigned_path_confound_material; redesigned_gold_isolation_eval_private; redesigned_material_qa
controls: matched_hard_negative_control; same_source_family_control; cross_task_semantic_mismatch_control; path_token_matched_control; query_only_control; evidence_only_control; support_relation_broken_control; gold_blind_decoy_control; source_family_balance_control
bounds: target_tasks_16_to_20; private_rows_le_20000; depth_le_40; support_pairs_le_120_per_task; control_pairs_le_120_per_task; total_pairs_le_240_per_task; source_files_le_500; wall_clock_le_20_minutes
source allowlist: operator-provided public source allowlist required
root safety: root ownership and symlink safety required
gold: gold eval-only
metrics: material generation only; no robustness metrics
publication: aggregate-only publication
next: BEA-v1-HAAE-R2BE Evidence-Pair Support Explicit Local Redesigned Material Generation
```

R2BD does not authorize experiments, metrics, scale, source scans, runtime/retrieval, or claims. R2BE authorization is scoped to explicit opt-in private material generation only.
