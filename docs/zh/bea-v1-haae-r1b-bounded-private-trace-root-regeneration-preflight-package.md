# BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package

日期：2026-06-30

BEA-v1-HAAE-R1B 是由 HAAE-R1A coverage gap design（checkpoint `e54d1b4`，状态
`haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized`）开启的
**public-only、design-only preflight package**。

R1B **不是** 执行阶段。它不得：读取 private data、写入 private data、regenerate
roots、执行 replay/scoring/retrieval/candidate generation/HAAE layers、运行
CI/network/clone/build/search，或授权 BEA-v1-A/P5/selector/runtime/default。它明确
**不是** BEA-v1-A、不是 selector-only、不是 selector/reranker execution、不是 P5、
不是 runtime/default promotion。

## 允许 public 输入

- 已提交的 HAAE-R1A public aggregate report（授权 R1B 的 coverage gap design）；
- HAAE-R1/R0/N10ET public aggregate reports（上游 locks）；
- HAAE-R1A/R1/R0/N10ET evaluator，仅用于 constants（绝不执行）；
- R1A 使用的 public aggregate artifacts/docs（FD1、P4L、N1、N2、N10-series /
  mechanism synthesis）用于 recipe 分类；
- README/current-research-conclusions/research-log/research-summary public
  readback；
- git metadata：记录 HAAE-R1A 结果的 `e54d1b4` checkpoint。

## HAAE-R1A source lock

```text
haae r1a checkpoint: e54d1b4
haae r1a status: haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized
haae r1a next allowed phase: BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package
haae r1b authorized by haae r1a: true（haae_r1b_bounded_private_trace_root_regeneration_preflight_authorized_bool）
haae r1b design only: true
haae r1b execution / private_read / replay / scoring / retrieval / candidate_generation: false
haae r0 non-identity booleans: 全部为 true
haae r1a source locked: true
no_ci_rerun / no_retrieval / no_recompute / no_private_input_read: true
no_replay / no_scoring / no_candidate_generation / no_haae_layer_execution: true
no_root_regeneration / no_network_run / no_clone_build_search: true
```

## 结果

```text
status: haae_r1b_bounded_private_trace_root_regeneration_preflight_package_complete_r1c_smoke_authorized
self-test: 108 / 108
forbidden scan: pass
private input reads: 0
root regenerations: 0
replays: 0
haae layer executions: 0
network runs: 0
clone/build/search: false
haae r1a source locked: true（checkpoint e54d1b4）
recipe catalog covers all 10 groups: true
operator checklist present: true
private output contract present: true
public manifest schema present: true
r1c bounded contract present: true
next allowed phase: BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke
```

## Recipe catalog（10 个 recipes，覆盖全部 10 个 HAAE-R0 schema groups）

| # | Group | Recipe | Kind |
|---|---|---|---|
| 0 | task_identity | fd1_decomposition_replay_recipe | decomposition_replay |
| 1 | anchor_source | normalized_bm25_anchor_recovery_recipe | public_aggregate_derivation |
| 2 | candidate_pool | n10eo_diagnostic_rerun_recipe | diagnostic_rerun |
| 3 | rank_pack | n2_rank_pack_decomposition_recipe | public_aggregate_derivation |
| 4 | span_projection | span_window_repair_branch_recipe | public_aggregate_derivation |
| 5 | scheduler_action | p4l_scheduler_replay_recipe | scheduler_replay |
| 6 | evidence_core | fd1_plus_n10er_evidence_core_recipe | hybrid_decomposition_replay_plus_public_aggregate |
| 7 | arm_assignment | p4l_arm_outcome_5_arms_recipe | arm_outcome_replay |
| 8 | outcome_metric | n10er_n10es_outcome_metric_recipe | public_aggregate_derivation |
| 9 | safety_probe_signal | safety_probe_lineage_recipe | public_aggregate_derivation |

## Operator checklist（5 个 safe operators）

1. **explicit_opt_in_private_root_enumeration** —— 在显式 opt-in 下枚举显式提供的
   private root buckets。有界深度，无 symlink 逃逸。
2. **fd1_decomposition_replay_operator** —— 重放 FD1 decomposition 以 regenerate
   private rows。Private output only；public manifest count buckets only。
3. **p4l_scheduler_replay_operator** —— 重放 frozen P4 scheduler 以 regenerate
   private arm-outcome rows。Private output only；public manifest count only。
4. **public_aggregate_derivation_operator** —— 从现有 public artifacts 推导 public
   aggregate buckets。不读取 private，不 replay。
5. **public_manifest_writer_operator** —— 从 private output 写 public manifest
   （仅 aggregate count buckets）。无 raw release。

## Private output contract

3 个 contracts：`private_output_only`（private rows 只写入显式 opt-in
output）、`public_manifest_count_only`（public artifact 只带 count buckets）、
`bounded_recipe_only`（R1C recipes 受 R1B catalog 约束；不进行 unbounded
replay/retrieval/candidate generation）。

## Public manifest schema

5 个字段：`anonymous_recipe_id`（opaque_id）、`private_row_count_bucket`
（ordinal）、`group_coverage_map_bucket`（categorical）、`manifest_hash_bucket`
（opaque_hash）、`no_raw_release_bool`（bool）。全部 aggregate-bucket-only。

## R1C bounded contract

R1C 是 bounded private trace root regeneration smoke。它要求显式 opt-in、只产生
private output、只发布 public manifest count buckets，并受 R1B recipe catalog 约束。
Unbounded replay/retrieval/candidate generation/scoring/selector/BEA-v1-A/P5/runtime
全部为 false。R1C 单独实现/审查；R1B 本身不执行任何操作。

## Boundary

HAAE-R1B 明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker
execution、不是 P5、不是 runtime/default promotion、不是 HAAE-layer execution、
不是 replay、不是 scoring、不是 retrieval、不是 candidate generation、不是 root
regeneration。所有这类 claim-boundary 与 stop/go 字段均为 `false`。

## Stop/go

Pass → **只** 授权 BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke
（design-only，单独实现/审查）：
`haae_r1c_bounded_private_trace_root_regeneration_smoke_authorized_bool=true`、
`haae_r1c_design_only_bool=true`、`haae_r1c_execution_authorized_bool=false`、
`haae_r1c_bounded_recipe_only_bool=true`、
`haae_r1c_unbounded_replay_authorized_bool=false` 等。

## Workflow

- Preflight helper：
  `eval/bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package.py`
- helper 暴露 `--self-test`、`--validate-report`、`--out` 与
  `--haae-r1a-report`。它只读取 HAAE-R1A public report 与 public docs；不执行、
  不读取 private、不 root regeneration。

## Artifact

- Helper：`eval/bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package.py`
- Report：`artifacts/bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package/bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package_report.json`
