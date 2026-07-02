# BEA-v1-HAAE-R2B Scale Preflight Design

日期：2026-07-03

BEA-v1-HAAE-R2B Scale Preflight Design 是 R2A 之后的 public-only design/preflight。
它只检查已提交的公开 R14 fixture metadata 来选择下一个 bounded preflight package。
它不生成 material，不运行 experiments，不读取 private roots，不写 private rows，不
recompute R2 metrics，不生成 candidates，不 retrieval，不扫描 source corpus，不运行
OpenLocus，不 clone，不使用 network 或 CI，不执行 scheduler/HAAE layer，不运行
selector/reranker，不改变 runtime/default，不运行 BEA-v1-A/P5，也不提出
method-winner/scaling claim。

```text
phase: BEA-v1-HAAE-R2B Scale Preflight Design
status: haae_r2b_scale_preflight_design_complete_r2c_local_medium_material_smoke_preflight_authorized
self-test: 13/13
source lock: HAAE-R2A checkpoint 2ca1ac4
selected option: r14_medium_local_material_smoke
source fixture task-count: count_21_to_50
target task-count: count_10_to_20
selected subset policy: deterministic_public_manifest_prefix_cap_10_to_20
candidate-depth: count_20
private-row cap: count_le_5000
boundary: no private/material gen/execution/CI/network/BEA-v1-A/P5/method-winner
next phase: BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight
```

Selected design 只允许 local/manual、显式 opt-in，并且 public aggregate-only。R2C
仍然是 preflight/package 阶段，不是实际 material generation 或 experiment execution。

R2B 只授权 **BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight**。它不授权
R2C execution、private reads/writes、CI execution、material generation、retrieval、
candidate generation、scheduler/HAAE execution、selector/reranker、runtime/default
change、BEA-v1-A/P5、method-winner claim 或 scaling claim。
