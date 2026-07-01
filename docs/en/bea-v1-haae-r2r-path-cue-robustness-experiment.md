# BEA-v1-HAAE-R2R Path-Cue Robustness Experiment

Date: 2026-07-01

BEA-v1-HAAE-R2R Path-Cue Robustness Experiment is complete as an explicit
private-material-root experiment. Default mode still performs no private reads or
writes.

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

Explicit mode reads only existing R2P private material. It computes bucketed
top-k, hit-rate, MRR, median first-gold-rank, missing-outcome, and path-prior
variant robustness records. It publishes no exact rates, ranks, paths, tokens,
task IDs, queries, candidates, labels, scores, hashes, or per-task values.

Result: the original path-prior signal is not robust. It is high on the original
path-cue material, but the bucketized top10/top20 signal drops under
path-scrambled, extension-preserved, directory-depth-preserved, and
strengthened-control variants. This supports `path_cue_artifact_likely`, not a
method-winner or default/runtime claim.
