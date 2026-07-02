# BEA-v1-HAAE-R2AA Actual Explicit Local Real-File Material Smoke

日期：2026-07-03

BEA-v1-HAAE-R2AA Actual Explicit Local Real-File Material Smoke 是 bounded explicit
local/manual material generation phase。默认模式不执行 private read/write、source scan
或 candidate generation。

```text
phase: BEA-v1-HAAE-R2AA Actual Explicit Local Real-File Material Smoke
default status: haae_r2aa_unavailable_no_explicit_real_file_material_smoke_opt_in
pass status: haae_r2aa_actual_explicit_local_real_file_material_smoke_complete_r2ab_public_audit_authorized
self-test: 24/24
source lock: HAAE-R2Z checkpoint a763a84
source status: haae_r2z_real_file_candidate_material_preflight_complete_r2aa_actual_explicit_local_real_file_material_smoke_authorized
explicit opt-in required
operator public corpus manifest/allowlist
target_20
candidate_depth_40
source_file_count_bucket
source_file_cap_500
row_cap_20000
wall_clock_cap_20_minutes
gold private eval only
no experiment metrics
next phase: BEA-v1-HAAE-R2AB Real-File Material Public Audit Package
```

Explicit mode 需要 `--allow-real-file-material-smoke`、显式 private output root、用于
allowlisted public repo lock 的 `--operator-public-corpus-manifest`，以及
`--confirm-aggregate-only-publication`。Materializer 只扫描 allowlisted local public
corpus，只在 explicit root 下写 private rows，并且 public artifact 只发布 aggregate
buckets。不授权 network、clone、CI、provider call、retrieval/runtime/OpenLocus runtime、
scheduler、selector、BEA-v1-A/P5、default/runtime change、method claim、scaling claim 或
experiment metric。
