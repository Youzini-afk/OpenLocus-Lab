# BEA-v1-HAAE-R2U Content-Identifier Evidence Material Generation Smoke

日期：2026-07-01

BEA-v1-HAAE-R2U Content-Identifier Evidence Material Generation Smoke 已完成为 standalone
bounded material generator。Default mode 不读取 private、不写 private，也不生成 material。

```text
phase: BEA-v1-HAAE-R2U Content-Identifier Evidence Material Generation Smoke
default status: haae_r2u_unavailable_no_explicit_content_identifier_material_generation_opt_in
pass status: haae_r2u_content_identifier_material_generation_complete_r2v_public_audit_authorized
self-test: 24/24
source lock: HAAE-R2T checkpoint bc58cf7
source status: haae_r2t_non_path_cue_pivot_decision_complete_r2u_content_identifier_material_generation_authorized
explicit opt-in: required
target 20; candidate depth 40; row cap 20000
rank sources: query_identifier_overlap/symbol_name_overlap/content_snippet_overlap/identifier_normalized_bm25_like/hard_negative_quality_control/content_identifier_fusion/control_baseline
policy: no path tokens/extensions/directories; gold private only; gold labels not used for ranking
next phase: BEA-v1-HAAE-R2V Content-Identifier Material Public Audit Package
```

显式 run 只在 explicit operator root 下写 private rows，并 materialize target 20、
candidate depth 40，以及全部七个 content/identifier rank sources。Public artifact 为
aggregate-only，不包含 raw task IDs、queries、paths、candidates、labels、scores、
snippets、hashes 或 private root values。
