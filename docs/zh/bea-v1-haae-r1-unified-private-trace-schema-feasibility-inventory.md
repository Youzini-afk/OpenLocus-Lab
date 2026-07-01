# BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory

日期：2026-06-30

BEA-v1-HAAE-R1 是由 HAAE-R0（checkpoint `854fc2e`）设计的 unified private
trace schema 的 **feasibility inventory**。它 **不是** replay、scoring、
retrieval、candidate-generation 或 HAAE-layer execution 阶段。它对 10 个
HAAE-R0 schema groups 是否能从显式提供的 project-private root buckets 中填充
进行盘点，**只输出 aggregate buckets**。

## 模式

- **默认 / no-private 模式**（不传 `--allow-private-inventory`）：HAAE-R1
  **不** 读取 private roots。它生成 `unavailable` public artifact（未提供
  explicit private roots）或仅运行 `--self-test`。默认模式下不进行任何 private
  filesystem 访问。
- **Real inventory 模式**（`--allow-private-inventory --private-root <path>`，
  可重复）：唯一允许的 private 操作是枚举显式提供的 project-private root buckets
  （无 symlink 逃逸、有界深度、不遍历显式提供 root buckets 之外的内容），
  按 extension/type/schema bucket 识别候选文件，以及解析 schemas/JSON keys 以
  流式输出 row-count buckets、column presence buckets、type compatibility
  buckets、missingness buckets 与 anonymous join-shape availability buckets。

HAAE-R1 **绝不** 发布 paths、filenames、basenames、repo names、task ids、
queries、candidates、spans、snippets、hashes、exact ranks/scores、labels 或
row values。每条 record 都是 aggregate-bucket-only。safe parser 通用拒绝未知
参数，不回显参数值。

## HAAE-R0 source lock

```text
haae r0 checkpoint: 854fc2e
haae r0 status: haae_r0_design_schema_preflight_complete_haae_r1_authorized
haae r0 next allowed phase: BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory
haae r1 authorized by haae r0: true（haae_r1_unified_private_trace_schema_feasibility_inventory_authorized_bool）
haae r1 execution authorized by haae r0: false（haae_r1_execution_authorized_bool）
haae r1 replay / scoring / retrieval / candidate_generation authorized: false
n10et checkpoint: 26d817e（上游）
n10et status: n10et_public_safety_probe_design_decision_complete_haae_r0_authorized
haae r0 non-identity booleans: 全部为 true（not_bea_v1_a、not_selector_only、
  not_selector_reranker_execution、not_p5、not_runtime_default_promotion）
haae r0 source locked: true
no_ci_rerun / no_retrieval / no_recompute / no_private_input_read: true
no_replay / no_scoring / no_candidate_generation / no_haae_layer_execution: true
```

## 结果

```text
status: haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots
self-test: 121 / 121
forbidden scan: pass
private read count bucket: count_0（默认模式）
retrieval executions: 0
recomputes: 0
CI reruns: 0
candidate generations: 0
arm scorings: 0
openlocus executions: 0
replays: 0
haae layer executions: 0
haae r0 source locked: true（checkpoint 854fc2e）
10 schema groups accounted: true
critical groups: task_identity, candidate_pool, evidence_core, arm_assignment, outcome_metric
```

（默认 / no-private 模式生成 `unavailable_no_explicit_private_roots` artifact。
Real inventory 需显式 `--allow-private-inventory --private-root <path>` opt-in，
并会根据 coverage 生成 `pass` / `controlled_no_go` artifact。上面的 status 反映
默认模式。）

## 10 个 schema groups 已覆盖

| # | Group | Critical | Columns |
|---|---|---|---|
| 0 | task_identity | 是 | anonymous_task_id, repo_bucket, language_bucket |
| 1 | anchor_source | 否 | anchor_kind_bucket, acquisition_cost_bucket |
| 2 | candidate_pool | 是 | candidate_count_bucket, depth_distribution_bucket |
| 3 | rank_pack | 否 | topk_pack_bucket, novel_vs_old_pool_bucket |
| 4 | span_projection | 否 | span_window_bucket, span_overlap_bucket |
| 5 | scheduler_action | 否 | scheduled_action_bucket, action_cost_bucket |
| 6 | evidence_core | 是 | path_bucket, line_range_bucket, content_sha_bucket, score_bucket, why_bucket, channels_bucket |
| 7 | arm_assignment | 是 | arm_bucket, budget_bucket |
| 8 | outcome_metric | 是 | citation_validity_bucket, file_recovery_topk_bucket, lost_baseline_top10_bucket |
| 9 | safety_probe_signal | 否 | full_guard_diffaware_loss_bucket, risk_bucket_signal |

全部 10 个 groups 都在 `schema_group_feasibility_records` 中被覆盖。5 个 critical
groups 是 `task_identity`、`candidate_pool`、`evidence_core`、`arm_assignment`、
`outcome_metric`。

## Coverage buckets

每个 group 的 coverage 被分为：`full`（所有 columns 都存在且有 rows）、
`sufficient`（critical groups 至少一半 columns 存在，或 non-critical groups
任意 columns 存在）、`partial`（部分 columns 存在但低于 sufficient 阈值）、
`missing`（虽然有 rows 但无 columns 存在）、`not_present`（未观察到 rows）。
Row counts 分为 `count_0`、`count_1_to_10`、`count_11_to_100`、
`count_101_to_1000`、`count_1001_plus`。

## Pass / no-go / unavailable

- **Pass**（`haae_r1_feasibility_inventory_pass_haae_r2_authorized`）：全部 10
  个 groups 至少 partial **且** 5 个 critical groups full 或 sufficient。
- **Controlled no-go**
  （`haae_r1_feasibility_inventory_controlled_no_go_haae_r1a_authorized`）：
  有效 inventory 但不足（至少一个 group partial 但未达到 sufficient，或某个
  critical group missing/insufficient）。
- **Unavailable**
  （`haae_r1_feasibility_inventory_unavailable_no_locked_source` /
  `..._no_explicit_private_roots`）：未锁定 HAAE-R0 source，或默认模式下未
  提供 explicit private roots。

Fail-closed statuses：`fail_haae_r0_source_lock_mismatch`、
`fail_forbidden_scan`、`fail_schema_contract`、`fail_contract_violation`、
`fail_private_boundary_violation`、`fail_forbidden_operation`。

## Public artifact records

Artifact 包含：`source_lock_records`、`private_root_inventory_records`、
`schema_group_feasibility_records`（10 个 groups）、
`schema_column_feasibility_records`、`cross_group_join_feasibility_records`、
`public_aggregation_feasibility_records`、`coverage_summary_records`、
`synthetic_validator_records`（3 个 embedded synthetic full/partial/missing
fixtures）、`risk_control_records`（6 个 controls）、`public_package_records`、
`claim_boundary_records`、`pass_fail_gate_records`（27 个 audit gates）、
`stop_go_records` 与 `forbidden_scan`。

## Public aggregation feasibility

4 个 HAAE-R0 public aggregation contracts（`task_count_aggregate`、
`arm_aggregate`、`risk_bucket_aggregate`、`citation_aggregate`）各带一个
`feasibility_bucket`（`feasible` / `not_feasible`），取决于所有 source groups
是否至少有 partial coverage。不发布 raw aggregation values。

## 不进行 replay / scoring / retrieval / candidate generation / HAAE-layer execution

HAAE-R1 只是 feasibility inventory。它不进行 **任何** replay、**不** scoring、
**不** retrieval、**不** candidate generation、**不** arm scoring、**不**
OpenLocus execution、**不** HAAE-layer execution。synthetic validators 仅在
process 内运行于 embedded synthetic fixtures（非真实数据、非 replay、非
retrieval、非 candidate generation）。

## Boundary

HAAE-R1 明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker
execution、不是 P5、不是 runtime/default promotion、不是 HAAE-layer execution、
不是 replay、不是 scoring、不是 retrieval、不是 candidate generation。所有
这类 claim-boundary 与 stop/go 字段均为 `false`。HAAE-R0 non-identity booleans
（`haae_r0_not_bea_v1_a_bool`、`haae_r0_not_selector_only_bool`、
`haae_r0_not_selector_reranker_execution_bool`、`haae_r0_not_p5_bool`、
`haae_r0_not_runtime_default_promotion_bool`）全部为 `true`。

## Stop/go

- **Pass** → **只** 授权 BEA-v1-HAAE-R2 Feasibility-Gated Offline Trace Join
  Design（design-only，不 execution/replay/scoring/retrieval/candidate
  generation）：`haae_r2_feasibility_gated_offline_trace_join_design_authorized_bool=true`，
  `haae_r2_execution_authorized_bool=false`。
- **No-go** → **只** 授权 BEA-v1-HAAE-R1A Private Trace Coverage Gap Design
  （design-only，不 execution）：
  `haae_r1a_private_trace_coverage_gap_design_authorized_bool=true`，
  `haae_r1a_execution_authorized_bool=false`。

它 **不** 授权：任何 execution、rerun、retrieval、recompute、candidate
generation、arm scoring、OpenLocus execution、replay、HAAE-layer execution、
threshold tuning、新 policy experiments、frozen-rule changes、guard/full/
diffaware promotion、runtime/default changes、method-winner claims、
downstream/scaled retrieval、raw diagnostic publication、CI variant execution、
selector/reranker、BEA-v1-A、P5、provider/model network 或 network runs。所有
这类 stop/go 字段均为 `false`。

HAAE-R0 schema preflight 的详细事实来源是
[`docs/zh/bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md`](bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md)
与 [`current-research-conclusions.md`](current-research-conclusions.md)。

## Workflow

- Feasibility-inventory helper：
  `eval/bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory.py`
- helper 暴露 `--self-test`、`--validate-report`、`--out`、
  `--allow-private-inventory` 与 `--private-root`（可重复）。默认模式生成
  unavailable/no-explicit-roots artifact，不读取任何 private roots。

## Artifact

- Helper：`eval/bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory.py`
- Report：`artifacts/bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory/bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory_report.json`
