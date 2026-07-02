# BEA-v1-HAAE-R2AA Actual Explicit Local Real-File Material Smoke

Date: 2026-07-03

BEA-v1-HAAE-R2AA Actual Explicit Local Real-File Material Smoke is a bounded
explicit local/manual material generation phase. Default mode performs no private
read/write, source scan, or candidate generation.

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

Explicit mode requires `--allow-real-file-material-smoke`, an explicit private
output root, `--operator-public-corpus-manifest` for the allowlisted public repo
lock, and `--confirm-aggregate-only-publication`. The materializer scans only the
allowlisted local public corpus, writes private rows under the explicit root, and
publishes only aggregate buckets. No network, clone, CI, provider call,
retrieval/runtime/OpenLocus runtime, scheduler, selector, BEA-v1-A/P5,
default/runtime change, method claim, scaling claim, or experiment metric is
authorized.
