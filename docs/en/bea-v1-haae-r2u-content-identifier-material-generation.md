# BEA-v1-HAAE-R2U Content-Identifier Evidence Material Generation Smoke

Date: 2026-07-03

BEA-v1-HAAE-R2U Content-Identifier Evidence Material Generation Smoke is complete
as a standalone bounded material generator. Default mode performs no private
read, write, or material generation.

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

The explicit run writes private rows only under an explicit operator root and
materializes target 20, candidate depth 40, and all seven content/identifier rank
sources. The public artifact is aggregate-only and contains no raw task IDs,
queries, paths, candidates, labels, scores, snippets, hashes, or private root
values.
