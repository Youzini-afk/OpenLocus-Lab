# BEA-v1-HAAE-R1E Bounded Private Experiment Material Generation

Date: 2026-07-03

BEA-v1-HAAE-R1E is the first tiny bounded phase allowed to generate real private
experiment material rows. It is local/manual only. It does not run in CI, does
not use network, clone, provider/model calls, OpenLocus runtime retrieval, or any
runtime/default change.

## Result

```text
status: haae_r1e_bounded_private_material_generation_complete_r2_small_experiment_authorized
default status: haae_r1e_unavailable_no_explicit_material_generation_opt_in
self-test: 16 / 16
forbidden scan: pass
source lock: HAAE-R1D checkpoint 9299b0a
source status: haae_r1d_schema_inventory_complete_no_go_bootstrap_placeholders_only
sample bound: 3-5 tasks, candidate depth <=20
required meaningful groups: task_identity, anchor_source, candidate_pool, rank_pack, evidence_core, outcome_metric
optional meaningful group: span_projection
placeholder-allowed groups: scheduler_action, arm_assignment, safety_probe_signal
```

Default mode is safe: no explicit opt-in means no private reads, no private
writes, and an unavailable artifact. Explicit mode requires
`--allow-private-material-generation`, `--private-output-root <temp-or-ignored-root>`,
`--sample-size <=5`, `--candidate-depth <=20`, and
`--confirm-private-rows-only`.

## Material generation

The evaluator uses the public R14 sanity fixture as the task source and reads the
matching labels only in explicit private mode. It scans a bounded local Rust
corpus declared by the R14 repo lock. It then builds deterministic local lexical
material without invoking OpenLocus runtime retrieval:

- BM25-like normalized lexical scoring.
- Symbol/exact-token overlap scoring.
- RRF-like merge traces.
- Bounded rank packs and evidence windows.
- Private outcome rows using the private label spans.

Raw task ids, queries, candidate paths, labels, spans, snippets, scores, and row
diagnostics are written only under the caller-supplied private root.

## Public boundary

The committed artifact is aggregate-only. It publishes only buckets and booleans:
source lock, mode, private-root boundary result, sample/depth bounds, recipe,
schema group row-count buckets, rank-source presence, evidence/outcome aggregate
buckets, public manifest safety, claim boundary, gates, synthetic validators,
stop/go, and forbidden scan.

It does not publish concrete private paths, filenames, repo ids, task ids,
queries, candidate names, spans, scores, hashes, labels, snippets, line ranges,
rows, or diagnostics.

## Stop/go

R1E authorizes only a small local HAAE-R2 experiment because the explicit run
passed the source lock, private-root boundary, local-only/no-network/no-clone
gate, sample/depth bounds, required schema-group material rows, BM25-like and
RRF-like trace gates, readback check, and public scanner.

It does not authorize CI execution, provider/model calls, broad replay, scoring
claims, selector/reranker execution, BEA-v1-A/P5, runtime/default changes, or a
method-winner claim.

## Artifact

- Helper: `eval/bea_v1_haae_r1e_bounded_private_experiment_material_generation.py`
- Report: `artifacts/bea_v1_haae_r1e_bounded_private_experiment_material_generation/bea_v1_haae_r1e_bounded_private_experiment_material_generation_report.json`
