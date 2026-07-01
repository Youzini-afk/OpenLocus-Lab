# BEA-v1-HAAE-R2AN Evidence-Pair Support Explicit Material Generation

日期：2026-07-01

BEA-v1-HAAE-R2AN Evidence-Pair Support Explicit Material Generation 由 R2AM checkpoint `b243924`、status `haae_r2am_evidence_pair_support_material_generation_preflight_complete_r2an_explicit_material_generation_authorized`、R2AM self-test 26/26，以及 selected family `evidence_pair_support_complementarity` 授权。

Default status 为 `haae_r2an_unavailable_no_explicit_material_generation_opt_in`：default mode no-op，no private read/write、no source scan、no material generation。Explicit success status 为 `haae_r2an_evidence_pair_support_explicit_material_generation_complete_r2ao_public_material_audit_authorized`。

```text
phase: BEA-v1-HAAE-R2AN Evidence-Pair Support Explicit Material Generation
self-test: 27/27
explicit mode requires: private output root; public corpus manifest; allow flag; confirm private output; confirm no experiment metrics
target_task_count=20
evidence_unit_depth_cap_per_task=40
support_pair_cap_per_task=120
contrast_control_pair_cap_per_task=80
total_pair_cap_per_task=200
source_file_cap=500
private_row_cap=20000
wall_clock_cap_minutes=20
schema: bea_v1_haae_r2an_evidence_pair_support_material_generation_v1
policy: gold private eval only; single-rank content/path signal forbidden; pair/setwise oriented; material QA only
publication: aggregate-only public artifact
next: BEA-v1-HAAE-R2AO Evidence-Pair Support Material Public Audit Package
```

Explicit mode 写入 private groups：`task_frame`、`source_manifest_private`、`evidence_unit_pool`、`evidence_pair_material`、`support_relation_material`、`contrast_control_material`、`outcome_eval_private`、`material_qa`。Public artifact 只发布 bucketed aggregate records，不发布 raw task ids、queries、evidence/pair identifiers、source filenames、paths、line numbers、snippets、hashes、gold labels、exact row counts 或 metrics。
