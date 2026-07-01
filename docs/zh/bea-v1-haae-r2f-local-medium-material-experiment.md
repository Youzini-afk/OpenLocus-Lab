# BEA-v1-HAAE-R2F Local Medium Material Experiment

日期：2026-07-01

BEA-v1-HAAE-R2F Local Medium Material Experiment 从 operator-supplied R2D private
material root 计算 aggregate metrics。默认模式不读取 / 写入 private，并返回
`haae_r2f_unavailable_no_explicit_r2d_private_material_root`。

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

Explicit mode 要求 `--allow-private-medium-material-experiment`、
`--private-material-root <root>` 和 `--confirm-aggregate-only-publication`。Public
report 不发布 private path、basename、filename、task id、query、candidate、label、score、hash、snippet 或 exact per-task value。

显式 medium run 只读取 existing R2D private rows。三个 rank sources 的 public
aggregate buckets 都是：gold-file hit-rate bucket `rate_1`，same-top candidate rate bucket `rate_1`，top1/top5/top10 buckets `count_10_to_20`。这仍然只是
medium material experiment，不是 method-winner 或 default/runtime claim。

Boundary: no new candidates/retrieval/source scan/OpenLocus/runtime/scheduler/selector/CI/network/provider/default/BEA-v1-A/P5/method/scaling claim。
