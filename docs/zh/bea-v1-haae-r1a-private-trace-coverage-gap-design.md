# BEA-v1-HAAE-R1A Private Trace Coverage Gap Design

日期：2026-06-30

BEA-v1-HAAE-R1A 是响应 HAAE-R1 coverage gap（checkpoint `2ea77da`，状态
`haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots`）的
**public-only design** 阶段。它 **不是** 执行阶段：不读取 private，不 root
regeneration，不 replay/scoring/retrieval/candidate generation/HAAE-layer
execution/CI/network/clone。它明确 **不是** BEA-v1-A、不是 selector-only、不是
selector/reranker execution、不是 P5、不是 runtime/default promotion。

## 允许输入（仅 public）

- 已提交的 HAAE-R1 public aggregate report（确认全部 10 个 groups
  `not_present`）；
- 已提交的 HAAE-R0 public aggregate report（设计了 10 个 groups）；
- N10ET public aggregate report（收尾 design/decision）；
- HAAE-R1/R0/N10ET evaluator，仅用于 constants（绝不执行）；
- FD1、P4L、N1、N2、N10-series / mechanism synthesis 的 public
  artifacts/docs，用于分类 source option buckets；
- HAAE-R1/R0 EN/ZH docs、EN/ZH current-research-conclusions、EN/ZH
  research-log/summary 与 README public readback；
- git metadata：记录 HAAE-R1 结果的 `2ea77da` checkpoint。

禁止：遍历 ignored project-private namespaces、temporary private output namespaces、ignored roots、`target`、`runs`、clones；任何
private reads；任何 root regeneration；任何
replay/scoring/retrieval/candidate generation/HAAE-layer execution；任何 CI
rerun；任何 network；任何 clone/build/search；任何 BEA-v1-A/P5/selector/
runtime/default。

## HAAE-R1 source lock

```text
haae r1 checkpoint: 2ea77da
haae r1 status: haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots
haae r1 next allowed phase: BEA-v1-HAAE-R1A Private Trace Coverage Gap Design
haae r2 authorized by haae r1: false（haae_r2_feasibility_gated_offline_trace_join_design_authorized_bool）
haae r1 execution / replay / scoring / retrieval / candidate_generation: false
haae r1 coverage: unavailable（全部 10 个 groups not_present）
haae r0 checkpoint: 854fc2e（上游）
n10et checkpoint: 26d817e（上游）
haae r0 non-identity booleans: 全部为 true
haae r1 source locked: true
no_ci_rerun / no_retrieval / no_recompute / no_private_input_read: true
no_replay / no_scoring / no_candidate_generation / no_haae_layer_execution: true
no_root_regeneration / no_network_run / no_clone_build_search: true
```

## 结果

```text
status: haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized
self-test: 112 / 112
forbidden scan: pass
private input reads: 0
retrieval executions: 0
recomputes: 0
CI reruns: 0
candidate generations: 0
arm scorings: 0
openlocus executions: 0
replays: 0
haae layer executions: 0
root regenerations: 0
network runs: 0
clone/build/search: false
haae r1 source locked: true（checkpoint 2ea77da）
10 schema groups accounted: true
source option count: 10
bounded regeneration designs: 5
root manifest schema fields: 6
next allowed phase: BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package
```

## 10 个 schema groups coverage gap

| # | Group | Critical | HAAE-R1 Coverage | Source Option | Evidence Strength |
|---|---|---|---|---|---|
| 0 | task_identity | 是 | not_present | fd1_private_decomposition_manifest | strong |
| 1 | anchor_source | 否 | not_present | n10dw_normalized_bm25_recovery_mechanism | partial |
| 2 | candidate_pool | 是 | not_present | n10eo_private_diagnostic_rerun_mechanism | strong |
| 3 | rank_pack | 否 | not_present | n2_rank_pack_actionability_decomposition | strong |
| 4 | span_projection | 否 | not_present | n10aa_to_n10bn_span_window_repair_branch | strong |
| 5 | scheduler_action | 否 | not_present | p4l_private_arm_outcome_manifest | strong |
| 6 | evidence_core | 是 | not_present | fd1_private_decomposition_plus_n10er_citation | strong |
| 7 | arm_assignment | 是 | not_present | p4l_private_arm_outcome_5_arms | strong |
| 8 | outcome_metric | 是 | not_present | n10er_n10es_public_arm_aggregates | strong |
| 9 | safety_probe_signal | 否 | not_present | n10eq_n10er_n10es_n10et_safety_probe_lineage | strong |

全部 10 个 groups 至少有一个 source option 为 `public_evidence_strong` 或
`public_evidence_partial`。9 个 groups 为 `public_evidence_strong`；1 个 group
（`anchor_source`）为 `public_evidence_partial`。

## Bounded regeneration design

5 个 bounded regeneration designs：

1. **explicit_opt_in_private_root_enumeration** —— regeneration 需显式 opt-in
   via `--allow-private-inventory --private-root <path>`。不隐式枚举 private
   roots。不遍历显式提供的 project-private root buckets 或 temporary private output buckets 之外的内容。
   有界深度，无 symlink 逃逸。
2. **fd1_private_decomposition_regeneration** —— 通过在显式 opt-in 下重放 FD1
   decomposition 来 regenerate FD1 private decomposition rows。只在 temporary private output bucket 中
   产生 private rows；public artifact 只带 manifest count buckets。Source
   groups：task_identity、evidence_core。
3. **p4l_private_arm_outcome_regeneration** —— 通过在 locked 272-record
   non-Python denominator 上重放 frozen P4 scheduler 来 regenerate P4L private
   arm-outcome rows。只在 temporary private output bucket 中产生 private arm-outcome rows。
   Source groups：scheduler_action、arm_assignment、outcome_metric。
4. **n10eo_private_diagnostic_rerun_regeneration** —— regenerate N10EO private
   diagnostic rerun。只在 temporary private output bucket 中产生 private diagnostic rows；public
   artifact 只带 aggregate mechanism buckets。Source groups：candidate_pool、
   rank_pack、safety_probe_signal。
5. **n10er_public_ci_replay_regeneration** —— 通过在显式 opt-in 并启用 network
   下重放 bounded public CI canary 来 regenerate N10ER public CI safety probe。
   Source groups：outcome_metric、safety_probe_signal。

## Root manifest schema design

6 个 manifest schema 字段：`anonymous_root_id`（opaque_id_bucket）、
`root_present_bool`（bool_bucket）、`file_count_bucket`（ordinal_bucket）、
`extension_distribution_bucket`（categorical_bucket）、
`group_coverage_map_bucket`（categorical_bucket）、`no_raw_release_bool`
（bool_bucket）。全部 aggregate-bucket-only；无 raw paths/filenames。

## Decision

**Pass** —— source lock 通过，HAAE-R1 unavailable/no roots 已确认，HAAE-R2
为 false，全部 10 个 groups 已覆盖，至少一个 source option 为
`public_evidence_strong`/`partial`（9 strong、1 partial），bounded
regeneration design 与 root manifest schema 已存在，docs/readback 通过，无
private/execution。**只** 授权 BEA-v1-HAAE-R1B Bounded Private Trace Root
Regeneration Preflight Package（design-only，不 execution/private read/
replay/scoring/retrieval/candidate generation）。

## Boundary

HAAE-R1A 明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker
execution、不是 P5、不是 runtime/default promotion、不是 HAAE-layer
execution、不是 replay、不是 scoring、不是 retrieval、不是 candidate
generation、不是 root regeneration。所有这类 claim-boundary 与 stop/go 字段
均为 `false`。

## Stop/go

Pass → **只** 授权 BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration
Preflight Package（design-only）：
`haae_r1b_bounded_private_trace_root_regeneration_preflight_authorized_bool=true`、
`haae_r1b_design_only_bool=true`、`haae_r1b_execution_authorized_bool=false`、
`haae_r1b_private_read_authorized_bool=false`、
`haae_r1b_replay_authorized_bool=false` 等。

No-go → closeout：explicit roots required；不授权后续阶段。

## Workflow

- Design helper：`eval/bea_v1_haae_r1a_private_trace_coverage_gap_design.py`
- helper 暴露 `--self-test`、`--validate-report`、`--out` 与
  `--haae-r1-report`。它只读取 HAAE-R1 public report 与 public docs；不执行、
  不读取 private、不 root regeneration。

## Artifact

- Helper：`eval/bea_v1_haae_r1a_private_trace_coverage_gap_design.py`
- Report：`artifacts/bea_v1_haae_r1a_private_trace_coverage_gap_design/bea_v1_haae_r1a_private_trace_coverage_gap_design_report.json`
