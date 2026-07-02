# BEA-v1-HAAE-R2E Local Medium Material Audit Package

Date: 2026-07-03

BEA-v1-HAAE-R2E Local Medium Material Audit Package is a public-only audit of the
R2D public aggregate artifact. It does not read a private root, does not scan
temporary directories, and does not access private material.

```text
phase: BEA-v1-HAAE-R2E Local Medium Material Audit Package
status: haae_r2e_local_medium_material_audit_package_complete_r2f_medium_experiment_authorized
self-test: 18/18
source lock: HAAE-R2D checkpoint c4e454a
source status: haae_r2d_explicit_local_medium_material_generation_smoke_complete_r2e_material_audit_authorized
audit mode: public-only audit
private access: no private root read
task bucket: count_10_to_20
source fixture bucket: count_21_to_50
subset policy: deterministic_public_manifest_prefix_cap_10_to_20
candidate depth: count_20
private row cap: count_le_5000
total private row bucket: count_le_5000
rank sources: bm25_like/symbol_overlap/rrf_like
next phase: R2F local medium material experiment
```

R2E authorizes only R2F local medium material experiment. R2F must use an
operator-supplied explicit private root, read existing R2D private material only,
and compute aggregate experiment metrics. There is no new material/candidate generation/retrieval/runtime/source scan/CI/network/scheduler/HAAE/selector/BEA-v1-A/P5/default/method/scaling claim.
