# BEA-v1-HAAE-R2F Local Medium Material Experiment

Date: 2026-07-01

BEA-v1-HAAE-R2F Local Medium Material Experiment computes aggregate metrics from
an operator-supplied R2D private material root. Default mode performs no private
read/write and returns `haae_r2f_unavailable_no_explicit_r2d_private_material_root`.

```text
phase: BEA-v1-HAAE-R2F Local Medium Material Experiment
status: haae_r2f_local_medium_material_experiment_complete_r2g_public_audit_authorized
default status: haae_r2f_unavailable_no_explicit_r2d_private_material_root
self-test: 22/22
source lock: HAAE-R2E checkpoint b166d79
source status: haae_r2e_local_medium_material_audit_package_complete_r2f_medium_experiment_authorized
private input: explicit private material root
material source: existing R2D private material only
publication: aggregate-only metrics
rank sources: bm25_like/symbol_overlap/rrf_like
gold-file hit-rate bucket: rate_1
same-top candidate rate bucket: rate_1
top1/top5/top10 buckets: count_10_to_20
next phase: BEA-v1-HAAE-R2G Public Audit Package
```

Explicit mode requires `--allow-private-medium-material-experiment`,
`--private-material-root <root>`, and `--confirm-aggregate-only-publication`.
The public report does not publish the private path, basename, filename, task id,
query, candidate, label, score, hash, snippet, or exact per-task value.

The explicit medium run used only existing R2D private rows. For all three rank
sources, the public aggregate buckets are gold-file hit-rate bucket `rate_1`,
same-top candidate rate bucket `rate_1`, and top1/top5/top10 buckets `count_10_to_20`. This is still a medium material experiment, not a method-winner
or default/runtime claim.

Boundary: no new candidates/retrieval/source scan/OpenLocus/runtime/scheduler/selector/CI/network/provider/default/BEA-v1-A/P5/method/scaling claim.
