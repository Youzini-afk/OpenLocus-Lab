# BEA-v1-HAAE-R2A Small Local Experiment Public Audit Package

日期：2026-07-01

BEA-v1-HAAE-R2A Small Local Experiment Public Audit Package 是对 R2 aggregate
artifact 的 public-only audit/package。它不读取 private material，不 recompute，也不
运行 candidate generation、retrieval、scheduler/HAAE execution、selector/reranker、
runtime/default change 或 BEA-v1-A/P5 action。

## 结果

```text
phase: BEA-v1-HAAE-R2A Small Local Experiment Public Audit Package
status: haae_r2a_public_audit_package_complete_r2b_scale_preflight_design_authorized
self-test: 10/10
forbidden scan: pass
source lock: HAAE-R2 checkpoint 0784be0
source status: haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized
next phase: BEA-v1-HAAE-R2B Scale Preflight Design
```

Audit 锁定 R2 artifact、checkpoint、status、gates、stop/go boundary 与 aggregate
metrics。R2 报告 `bm25_like`、`symbol_overlap`、`rrf_like` 的 hit-rate bucket 均为
`rate_1`，pairwise same-top agreement bucket 为 `rate_1`，sample bucket 为
`count_2_to_5`。

## Boundary

这是 tiny-N audit package。结果不是 no method-winner claim，也不是 runtime/default
decision。它只确认 small local R2 aggregate artifact 内部一致，并且可以安全公开
package。

R2A 只授权 **BEA-v1-HAAE-R2B Scale Preflight Design**，即设计如何把 material
generation 扩展到超过三个 tasks 的 design phase。它不授权 scale run、CI execution、
private reads、recompute、candidate generation、retrieval、scheduler/HAAE execution、
selector/reranker、BEA-v1-A/P5、runtime/default change、raw publication 或
method-winner claim。

## Artifact

- Helper：`eval/bea_v1_haae_r2a_public_audit_package.py`
- Report：`artifacts/bea_v1_haae_r2a_small_local_experiment_public_audit_package/bea_v1_haae_r2a_small_local_experiment_public_audit_package_report.json`
