# BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight

日期：2026-07-01

BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight 是下一步 explicit local
medium material generation smoke 的 public-only preflight/package。它不创建 private
root，不写 private rows，不生成 material，不运行 experiment，不 recompute metrics，不生成
candidates，不 retrieval，不进行超过 public fixture count 的 source scan，不运行
OpenLocus/runtime，不使用 network/clone/CI，不执行 scheduler/HAAE layer，不运行
selector/reranker，不改变 runtime/default，不运行 BEA-v1-A/P5，也不提出 method/scaling
claim。

```text
phase: BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight
status: haae_r2c_local_medium_material_smoke_preflight_complete_r2d_generation_smoke_authorized
self-test: 16/16
source lock: HAAE-R2B checkpoint dea8a2f
selected option: r14_medium_local_material_smoke
source fixture bucket: count_21_to_50
subset policy: deterministic_public_manifest_prefix_cap_10_to_20
target task bucket: count_10_to_20
candidate depth: count_20
private row cap: count_le_5000
boundary: no_private_material_gen_execution_ci_network_bea_v1_a_p5_method_winner
next phase: BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke
```

Operator command contract 只是 placeholder-only。它要求 explicit local manual command，
并包含 required flag buckets：allow-private-medium-material-generation、
private-output-root placeholder、source-fixture bucket、subset-policy、
target-task-count、candidate-depth、private-row-cap 和 confirm-private-rows-only。
不发布任何 concrete private output path。

R2C 只授权 R2D explicit local medium material generation smoke。R2D 可以在显式
private root 下生成 private rows，目标为 10-20 tasks、depth 20、cap 5000。Public
output 仍然只能 aggregate-only。CI/network/provider、experiment comparison、R2
recompute、retrieval runtime、scheduler/HAAE、selector/reranker、runtime/default、
BEA-v1-A/P5、method claim 与 scaling claim 均保持 false。
