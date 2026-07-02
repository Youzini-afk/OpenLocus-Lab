# BEA-v1-HAAE-R2AT Evidence-Pair Support Explicit Local Private Mechanism Decomposition

Date: 2026-07-03

BEA-v1-HAAE-R2AT Evidence-Pair Support Explicit Local Private Mechanism Decomposition follows R2AS checkpoint `36e64d6`, status `haae_r2as_evidence_pair_support_mechanism_decomposition_public_design_preflight_complete_r2at_explicit_private_mechanism_decomposition_authorized`.

```text
phase: BEA-v1-HAAE-R2AT Evidence-Pair Support Explicit Local Private Mechanism Decomposition
status default: haae_r2at_unavailable_no_explicit_private_mechanism_decomposition_opt_in
status explicit prefix: haae_r2at_explicit_private_mechanism_decomposition_complete_r2au_public_audit_authorized
self-test: 35/35
source locks: R2AS 36e64d6; R2AR 7c36376; R2AQ 77eab19; R2AP 87ea9de; R2AO 5cfa8d3; R2AN 93bba5f
inherited result: support_signal; support_separation_high
default mode no-op: no private read, no private write, no metrics, no diagnostics
explicit mode requires: explicit opt-in; existing R2AN private material root; confirm aggregate-only public output
read only existing R2AN private material groups: task_frame, source_manifest_private, evidence_unit_pool, evidence_pair_material, support_relation_material, contrast_control_material, outcome_eval_private, material_qa
public metric buckets: axis coverage bucket; task coverage bucket; pair-family coverage bucket; single-unit ablation bucket; pair-complementarity lift bucket; support-vs-contrast separation bucket; hard-negative rejection bucket; shuffled/cross-task degradation bucket; path-confound risk bucket; gold-isolation pass bucket; family concentration/sensitivity bucket; evidence-quality sensitivity bucket; mechanism interpretation bucket
mechanism interpretation bucket values: pair_complementarity_supported, support_relation_supported, control_artifact_risk, path_confound_risk, mixed_or_inconclusive
next: BEA-v1-HAAE-R2AU Evidence-Pair Support Mechanism Decomposition Public Audit Package
boundary: No robustness generation, scale preflight, new experiment, source/candidate/corpus scan; no source/candidate/corpus scan; no material regeneration; gold outcome eval-only
```

R2AT does not scan source/candidate/corpus files, regenerate material/evidence/pairs/candidates, mutate R2AN material, use gold outside eval, publish exact metrics, publish root paths/basenames, or publish task/query/path/snippet/line/evidence-key/pair-key/source-ref/gold/hard-negative/hash/raw diagnostics. Optional diagnostics, when requested, are private-only.

Explicit result: `pair_complementarity_supported`; pair_complementarity_lift_high; support_vs_contrast_separation_medium; hard_negative_rejection_medium; path_confound_risk_low; gold_isolation_pass; mechanism decomposition result only, not method/default/scale claim.
