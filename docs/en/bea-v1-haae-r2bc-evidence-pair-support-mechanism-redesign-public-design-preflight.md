# BEA-v1-HAAE-R2BC Evidence-Pair Support Mechanism Redesign Public Design Preflight

Date: 2026-07-01

BEA-v1-HAAE-R2BC Evidence-Pair Support Mechanism Redesign Public Design Preflight is a public-only, non-executing redesign requirements package after R2BB. It does not read private roots/material, generate material, recompute metrics, scan source/candidate/corpus, run runtime/retrieval/CI/network/provider/clone, or publish raw/exact/private values.

```text
phase: BEA-v1-HAAE-R2BC Evidence-Pair Support Mechanism Redesign Public Design Preflight
status: haae_r2bc_evidence_pair_support_mechanism_redesign_public_design_preflight_complete_r2bd_redesigned_material_generation_public_design_preflight_authorized
self-test: 37/37
source: R2BB checkpoint a624728; R2BB status haae_r2bb_evidence_pair_support_robustness_next_step_decision_complete_r2bc_mechanism_redesign_public_design_preflight_authorized
locks: R2BA checkpoint f8984bf; R2BA status haae_r2ba_evidence_pair_support_robustness_experiment_public_audit_complete_r2bb_next_step_decision_authorized_negative_robustness_evidence; R2AZ checkpoint 72590e5; R2AZ status haae_r2az_explicit_local_robustness_experiment_complete_r2ba_public_audit_authorized_artifact_likely; R2AY checkpoint 126dc18; R2AX checkpoint f3add65; R2AW checkpoint bc44454; R2AN checkpoint 93bba5f; R2AT checkpoint 0c9c108; R2AP checkpoint 87ea9de
package: redesign requirements package
hypothesis: existing support/complementarity insufficient after robustness failure; robust signal not claimed
controls: matched_hard_negative_control; same_source_family_control; cross_task_semantic_mismatch_control; path_token_matched_control; query_only_control; evidence_only_control; support_relation_broken_control; gold_blind_decoy_control; source_family_balance_control
path policy: elevated confound fails robust-signal gates
gold policy: gold eval-only
bounds: target_tasks_16_to_20; private_rows_le_20000; depth_le_40; support_pairs_le_120_per_task; control_pairs_le_120_per_task; total_pairs_le_240_per_task; source_files_le_500; wall_clock_le_20_minutes
next: BEA-v1-HAAE-R2BD Evidence-Pair Support Redesigned Material Generation Public Design Preflight
```

The next phase is also public-only and non-executing. R2BC does not authorize explicit private generation or experiments.
