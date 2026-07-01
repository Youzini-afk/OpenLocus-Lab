# BEA-v1-HAAE-R2B Scale Preflight Design

Date: 2026-07-01

BEA-v1-HAAE-R2B Scale Preflight Design is a public-only design/preflight after
R2A. It inspects only committed public R14 fixture metadata to choose the next
bounded preflight package. It does not generate material, run experiments, read
private roots, write private rows, recompute R2 metrics, generate candidates,
retrieve, scan source corpus, run OpenLocus, clone, use network or CI, execute a
scheduler/HAAE layer, run a selector/reranker, change runtime/default behavior,
run BEA-v1-A/P5, or make a method-winner/scaling claim.

```text
phase: BEA-v1-HAAE-R2B Scale Preflight Design
status: haae_r2b_scale_preflight_design_complete_r2c_local_medium_material_smoke_preflight_authorized
self-test: 13/13
source lock: HAAE-R2A checkpoint 2ca1ac4
selected option: r14_medium_local_material_smoke
source fixture task-count: count_21_to_50
target task-count: count_10_to_20
selected subset policy: deterministic_public_manifest_prefix_cap_10_to_20
candidate-depth: count_20
private-row cap: count_le_5000
boundary: no private/material gen/execution/CI/network/BEA-v1-A/P5/method-winner
next phase: BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight
```

The selected design is local/manual only, explicit opt-in only, and public
aggregate-only. R2C is still a preflight/package phase, not actual material
generation or experiment execution.

R2B authorizes only **BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight**.
It does not authorize R2C execution, private reads/writes, CI execution, material
generation, retrieval, candidate generation, scheduler/HAAE execution,
selector/reranker, runtime/default change, BEA-v1-A/P5, method-winner claim, or
scaling claim.
