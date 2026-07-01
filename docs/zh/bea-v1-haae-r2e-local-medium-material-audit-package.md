# BEA-v1-HAAE-R2E Local Medium Material Audit Package

日期：2026-07-01

BEA-v1-HAAE-R2E Local Medium Material Audit Package 是对 R2D public aggregate
artifact 的 public-only audit。它不读取 private root，不扫描临时目录，也不访问
private material。

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

R2E 只授权 R2F local medium material experiment。R2F 必须由 operator 提供 explicit
private root，只读取 existing R2D private material，并只计算 aggregate experiment
metrics。没有 no new material/candidate generation/retrieval/runtime/source scan/CI/network/scheduler/HAAE/selector/BEA-v1-A/P5/default/method/scaling claim。
