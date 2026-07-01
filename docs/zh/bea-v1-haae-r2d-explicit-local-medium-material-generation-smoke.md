# BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke

日期：2026-07-01

BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke 是 R2C 授权的
explicit local/manual material generation smoke。默认模式不读取 private、不写入
private，并产生 `haae_r2d_unavailable_no_explicit_medium_material_generation_opt_in`。

```text
phase: BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke
status: haae_r2d_explicit_local_medium_material_generation_smoke_complete_r2e_material_audit_authorized
default status: haae_r2d_unavailable_no_explicit_medium_material_generation_opt_in
self-test: 19/19
source lock: HAAE-R2C checkpoint 68000b2
explicit opt-in: required
subset policy: deterministic_public_manifest_prefix_cap_10_to_20
public fixture bucket: count_21_to_50
target bucket: count_10_to_20
candidate depth: count_20
private row cap: count_le_5000
private write bucket: count_le_5000
private read validation bucket: count_1_to_10
public aggregate-only: true
no raw publication: true
next phase: BEA-v1-HAAE-R2E Local Medium Material Audit Package
```

Explicit mode 要求 `--allow-private-medium-material-generation`、显式 private output
root 和 `--confirm-private-rows-only`。Private rows 只写入该 root。Public artifact
只发布 aggregate buckets。

边界：no experiment comparison、no R2 recompute、
no runtime/retrieval/source scan beyond fixture、no CI/network/provider、
no scheduler/HAAE/selector、no BEA-v1-A/P5/runtime/default，以及
no method/scaling claim。
