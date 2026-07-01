# BEA-v1-HAAE-R2AC Actual Real-File Material Experiment

日期：2026-07-01

BEA-v1-HAAE-R2AC Actual Real-File Material Experiment 只在 operator 提供 explicit
private material root 时读取 existing R2AA private material。默认模式不读取 private，也
不写入 private。

```text
phase: BEA-v1-HAAE-R2AC Actual Real-File Material Experiment
default status: haae_r2ac_unavailable_no_explicit_r2aa_private_material_root
pass statuses: haae_r2ac_actual_real_file_material_experiment_complete_r2ad_public_audit_authorized_signal_present / haae_r2ac_actual_real_file_material_experiment_complete_r2ad_public_audit_authorized_weak_or_no_signal
self-test: 21/21
R2AB checkpoint: 52a23da
R2AB status: haae_r2ab_real_file_material_public_audit_package_complete_r2ac_real_file_material_experiment_authorized
R2AA checkpoint: f325b65
input: explicit private material root, existing R2AA material only
metrics: aggregate-only metrics
rank sources: query_identifier_overlap/symbol_name_overlap/lexical_bm25_like/content_identifier_fusion/control_baseline
metric buckets: task/candidate coverage, gold-file hit, top1/top5/top10/top20, MRR
diagnostics: pairwise aggregate diagnostics and real_file_material_signal_bucket
boundary: R2AD-only, no private writes/new candidate/material generation/source scan/retrieval/OpenLocus/runtime/CI/network/provider/clone
next phase: BEA-v1-HAAE-R2AD Actual Real-File Material Experiment Public Audit Package
```

R2AC 验证 R2AA manifest 和 required private groups，然后只计算 bucketed aggregate
metrics。它不发布 private root path、basename、file name、task id、query、raw path、
candidate value、snippet、label、hash、score、rank 或 per-task value。它不提出
method/default/scaling claim。

R2AC readback markers: haae_r2ac_actual_real_file_material_experiment_complete_r2ad_public_audit_authorized_signal_present; haae_r2ac_actual_real_file_material_experiment_complete_r2ad_public_audit_authorized_weak_or_no_signal; haae_r2ac_unavailable_no_explicit_r2aa_private_material_root; 21/21; 52a23da; haae_r2ab_real_file_material_public_audit_package_complete_r2ac_real_file_material_experiment_authorized; f325b65; explicit private material root; existing R2AA material only; aggregate-only metrics; query_identifier_overlap/symbol_name_overlap/lexical_bm25_like/content_identifier_fusion/control_baseline; task/candidate coverage; gold-file hit; top1/top5/top10/top20; MRR; pairwise aggregate diagnostics; real_file_material_signal_bucket; R2AD-only; no private writes/new candidate/material generation/source scan/retrieval/OpenLocus/runtime/CI/network/provider/clone; BEA-v1-HAAE-R2AD Actual Real-File Material Experiment Public Audit Package.

Result: `signal_present`. Symbol-name and content-identifier fusion rank sources are high-bucket (`mrr_high`, top1/top20 `count_11_to_20`), query and lexical sources are medium, and control_baseline remains low (`mrr_low`, top1 `count_0`). This is real-file material signal evidence, not a method/default/scaling claim.
