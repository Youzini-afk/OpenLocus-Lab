# BEA-v1-HAAE-R2AB Real-File Material Public Audit Package

日期：2026-07-01

BEA-v1-HAAE-R2AB Real-File Material Public Audit Package 是对 R2AA public artifact
的 public-only audit。它不读取 private root，不 recompute，不 generate material，不 scan
source，也不计算 metrics。

```text
phase: BEA-v1-HAAE-R2AB Real-File Material Public Audit Package
status: haae_r2ab_real_file_material_public_audit_package_complete_r2ac_real_file_material_experiment_authorized
self-test: 15/15
source lock: HAAE-R2AA checkpoint f325b65
source status: haae_r2aa_actual_explicit_local_real_file_material_smoke_complete_r2ab_public_audit_authorized
R2AA self-test 24/24
R2Z source checkpoint: a763a84
target20
depth40
source_file_count_bucket count_21_to_50
source cap 500
row cap 20000
real-file material generation complete
no metrics
aggregate-only
R2AB-only
next phase: BEA-v1-HAAE-R2AC Actual Real-File Material Experiment
```

R2AB 只授权 R2AC 使用 explicit private root 读取 existing R2AA private material。R2AC
可以读取 existing R2AA private material 并且只计算 aggregate metrics。不授权 no new material generation/retrieval/runtime/source scan/CI/network/provider/clone/broad scan/default/method/scaling/raw publication。
