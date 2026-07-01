# BEA-v1-HAAE-R2 Small Local Lexical Material Experiment

Date: 2026-07-01

BEA-v1-HAAE-R2 is a tiny local experiment over existing R1E private material. It
does not create or rematerialize candidates. It does not scan source code, run
OpenLocus retrieval, clone, use network, call a provider/model, execute a
scheduler or HAAE layer, run a selector/reranker, or change runtime defaults.

## Result

```text
status: haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized
default status: haae_r2_unavailable_no_explicit_r1e_private_material_root
self-test: 15/15
forbidden scan: pass
source lock: HAAE-R1E checkpoint 0135e1f
source status: haae_r1e_bounded_private_material_generation_complete_r2_small_experiment_authorized
private read bucket: count_1_to_10 material groups
private write bucket: count_0
rank sources compared: bm25_like, symbol_overlap, rrf_like
```

Default mode is safe: no explicit private-material-root opt-in means no private
reads, no private writes, and status
`haae_r2_unavailable_no_explicit_r1e_private_material_root`.

Explicit mode requires `--allow-private-material-experiment`,
`--private-material-root <existing-r1e-private-material-root>`, and
`--confirm-aggregate-publication-only`. The supplied root is read only. The root
path or basename is never published.

## Experiment

The evaluator reads the existing R1E material groups and joins only in memory. It
uses precomputed `rank_pack` rows and `outcome_metric` rows to compute aggregate
metrics for three existing rank sources:

- `bm25_like`
- `symbol_overlap`
- `rrf_like`

The public report records only buckets: group presence, private row-count
buckets, rank-source trace presence, hit-rate buckets, first-hit position buckets,
and pairwise agreement buckets. It publishes no task ids, queries, candidate
paths, snippets, labels, raw ranks, scores, hashes, filenames, or raw rows.

## Stop/go

R2 authorizes only **BEA-v1-HAAE-R2A Public Audit Package**. It does not authorize
R3 scale preflight, new candidate generation, rematerialization, broad retrieval,
scheduler/HAAE-layer execution, selector/reranker execution, provider/model or
network use, BEA-v1-A/P5, runtime/default changes, raw publication, or a
method-winner claim.

## Artifact

- Helper: `eval/bea_v1_haae_r2_small_local_lexical_material_experiment.py`
- Report: `artifacts/bea_v1_haae_r2_small_local_lexical_material_experiment/bea_v1_haae_r2_small_local_lexical_material_experiment_report.json`
