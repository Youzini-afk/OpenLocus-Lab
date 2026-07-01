# BEA-v1-HAAE-R2R Path-Cue Robustness Experiment

日期：2026-07-01

BEA-v1-HAAE-R2R Path-Cue Robustness Experiment 已作为 explicit
private-material-root experiment 完成。Default mode 仍然不读取 private，也不写 private。

```text
phase: BEA-v1-HAAE-R2R Path-Cue Robustness Experiment
default status: haae_r2r_unavailable_no_explicit_r2p_private_material_root
result status: haae_r2r_path_cue_robustness_experiment_complete_r2s_public_audit_authorized_artifact_likely
self-test: 30/30
source lock: HAAE-R2Q checkpoint a9f5477
source status: haae_r2q_public_audit_package_complete_r2r_local_robustness_experiment_authorized
input: explicit private material root; existing R2P material only
metrics: aggregate-only metrics by variant×rank_source
robustness: path_prior robustness
interpretations: robust_candidate_signal/path_cue_artifact_likely/mixed_or_inconclusive
result interpretation: path_cue_artifact_likely
path_prior_original_top10_bucket: count_11_to_20
path_prior_original_top20_bucket: count_11_to_20
drop buckets after path cue perturbation: count_11_to_20
variant_spread_bucket: spread_high
boundary: no method/default/scaling
next phase: BEA-v1-HAAE-R2S Public Audit Package
```

Explicit mode 只读取 existing R2P private material。它计算 bucketed top-k、hit-rate、
MRR、median first-gold-rank、missing-outcome 和 path-prior variant robustness records。
它不发布 exact rates、ranks、paths、tokens、task IDs、queries、candidates、labels、
scores、hashes 或 per-task values。

结果：original path-prior signal 不稳健。它在 original path-cue material 上高，
但 path-scrambled、extension-preserved、directory-depth-preserved 和
strengthened-control variants 下的 bucketized top10/top20 signal 都下降。这支持
`path_cue_artifact_likely`，不是 method-winner 或 default/runtime claim。
