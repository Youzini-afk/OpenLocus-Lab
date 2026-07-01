# BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke

日期：2026-06-30

BEA-v1-HAAE-R1C 是**第一个允许 explicit-opt-in 创建 private HAAE trace-root
artifact 的阶段**，但仅作为 root/output/manifest pipeline 的 **bounded
smoke**。锁定来源：HAAE-R1B commit/artifact `8830492`。R1C 不得运行
FD1/P4L/N10EO/N10ER replay、retrieval、scoring、candidate generation、
selector、BEA-v1-A/P5/runtime/default。

## 模式

- **默认 / no-private 模式**（不传 `--allow-private-root-regeneration-smoke`）：
  不进行任何 private reads 或 writes，生成状态
  `haae_r1c_unavailable_no_explicit_opt_in`。
- **Explicit opt-in 模式** 要求全部提供：
  - `--allow-private-root-regeneration-smoke`
  - `--recipe <allowed_recipe_bucket>`（三选一：
    `bootstrap_private_manifest_root_smoke`、
    `operator_supplied_existing_root_manifest_smoke`、
    `public_aggregate_source_option_manifest_smoke`）
  - `--private-output-root <path>`（不得是 public tracked 的
    docs/artifacts/eval 位置；不得是 symlink；不得包含 path traversal；有界深度）
  - `--confirm-private-output-only`
  - 可选 `--private-input-root <path>`（仅 existing-root recipe）

output root 会被校验：必须显式、不得是 public tracked、不得是 symlink、
不得允许 path traversal、有界深度与有界 write set。绝不发布 concrete
path/basename/filename。

## 允许 recipes

1. **`bootstrap_private_manifest_root_smoke`**（默认 explicit-opt-in recipe）：
   创建显式 private output root，只写 manifest/control 文件和
   empty/schema-category placeholders，**零** raw
   task/query/candidate/span/score rows。Public artifact 只带 bucketized
   manifest。
2. **`operator_supplied_existing_root_manifest_smoke`**（可选）：显式
   input/output roots，仅 metadata/schema inventory，无 row values，public
   aggregate buckets only。
3. **`public_aggregate_source_option_manifest_smoke`**（可选）：public-only
   projection，无 private input。

## Deferred（R1C 中禁止）recipes

4 个 deferred replay recipes：
`fd1_decomposition_replay_recipe`、`p4l_scheduler_replay_recipe`、
`n10eo_diagnostic_rerun_recipe`、`n10er_public_ci_replay_recipe`。全部标记为
deferred，`replay_authorized_bool=false`。

## HAAE-R1B source lock

```text
haae r1b checkpoint: 8830492
haae r1b status: haae_r1b_bounded_private_trace_root_regeneration_preflight_package_complete_r1c_smoke_authorized
haae r1b next allowed phase: BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke
haae r1c authorized by haae r1b: true
haae r1c design only: true
haae r1c execution / private_read / replay / scoring / retrieval / candidate_generation: false
haae r1c bounded_recipe_only: true
haae r1c unbounded_replay / unbounded_retrieval / unbounded_candidate_generation: false
haae r0 non-identity booleans: 全部为 true
haae r1b source locked: true
```

## 结果（默认 no-private 模式）

```text
status: haae_r1c_bounded_private_manifest_root_smoke_complete_r1d_inventory_authorized
self-test: 105 / 105
forbidden scan: pass
private input reads: 0
private writes: 1
retrieval executions: 0
replays: 0
fd1/p4l/n10eo/n10er replays: 0
haae layer executions: 0
clone/build/search: false
haae r1b source locked: true（checkpoint 8830492）
10 schema groups accounted: true
4 deferred recipes: true
next allowed phase: BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke
```

## 10 个 schema group manifest records

全部 10 个 HAAE-R0 schema groups 都有 manifest records，`raw_row_count=0`、
`placeholder_kind_bucket=empty_schema_category`：task_identity、anchor_source、
candidate_pool、rank_pack、span_projection、scheduler_action、evidence_core、
arm_assignment、outcome_metric、safety_probe_signal。

## Boundary

R1C 明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker
execution、不是 P5、不是 runtime/default promotion、不是 HAAE-layer
execution、不是 replay、不是 scoring、不是 retrieval、不是 candidate
generation。R1C 不得运行 FD1/P4L/N10EO/N10ER replay。成功的 R1C 只授权
R1D schema inventory，而不授权这些执行。所有这类
claim-boundary 与 stop/go 字段均为 `false`。

## Stop/go

成功的 R1C bootstrap smoke 只授权 **BEA-v1-HAAE-R1D Explicit Private Root
Schema Inventory Smoke**。默认 / no-opt-in 模式仍不授权下一阶段。所有 execution、rerun、
replay、retrieval、recompute、candidate generation、arm scoring、
OpenLocus execution、HAAE-layer execution、FD1/P4L/N10EO/N10ER replay、
threshold tuning、新 policy experiments、frozen-rule changes、guard/full/
diffaware promotion、runtime/default changes、method-winner claims、
downstream/scaled retrieval、raw diagnostic publication、CI variant
execution、selector/reranker、BEA-v1-A、P5、provider/model network、
network-run 字段均为 `false`。

## Workflow

- Smoke helper：`eval/bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke.py`
- helper 暴露 `--self-test`、`--validate-report`、`--out`、
  `--haae-r1b-report`、`--allow-private-root-regeneration-smoke`、`--recipe`、
  `--private-output-root`、`--confirm-private-output-only` 与
  `--private-input-root`。默认模式生成 unavailable artifact，不进行任何
  private reads 或 writes；本次提交结果使用 explicit bootstrap smoke 模式，公开只发布 aggregate manifest。

## Artifact

- Helper：`eval/bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke.py`
- Report：`artifacts/bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke/bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke_report.json`
