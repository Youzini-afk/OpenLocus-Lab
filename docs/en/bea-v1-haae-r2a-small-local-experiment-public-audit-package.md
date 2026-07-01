# BEA-v1-HAAE-R2A Small Local Experiment Public Audit Package

Date: 2026-07-01

BEA-v1-HAAE-R2A Small Local Experiment Public Audit Package is a public-only
audit/package of the R2 aggregate artifact. It reads no private material,
performs no recompute, and runs no candidate generation, retrieval,
scheduler/HAAE execution, selector/reranker, runtime/default change, or
BEA-v1-A/P5 action.

## Result

```text
phase: BEA-v1-HAAE-R2A Small Local Experiment Public Audit Package
status: haae_r2a_public_audit_package_complete_r2b_scale_preflight_design_authorized
self-test: 10/10
forbidden scan: pass
source lock: HAAE-R2 checkpoint 0784be0
source status: haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized
next phase: BEA-v1-HAAE-R2B Scale Preflight Design
```

The audit locks the R2 artifact, checkpoint, status, gates, stop/go boundary, and
aggregate metrics. R2 reports `bm25_like`, `symbol_overlap`, and `rrf_like` all
at hit-rate bucket `rate_1`, pairwise same-top agreement bucket `rate_1`, and
sample bucket `count_2_to_5`.

## Boundary

This is a tiny-N audit package. The result is not a no method-winner claim and is
not a runtime/default decision. It confirms only that the small local R2 aggregate
artifact is internally consistent and safe to package publicly.

R2A authorizes only **BEA-v1-HAAE-R2B Scale Preflight Design**, a design phase for
how to expand material generation beyond three tasks. It does not authorize a
scale run, CI execution, private reads, recompute, candidate generation,
retrieval, scheduler/HAAE execution, selector/reranker, BEA-v1-A/P5,
runtime/default change, raw publication, or method-winner claim.

## Artifact

- Helper: `eval/bea_v1_haae_r2a_public_audit_package.py`
- Report: `artifacts/bea_v1_haae_r2a_small_local_experiment_public_audit_package/bea_v1_haae_r2a_small_local_experiment_public_audit_package_report.json`
