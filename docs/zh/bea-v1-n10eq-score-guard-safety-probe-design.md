# BEA-v1-N10EQ Score/Guard Safety Probe Design

日期：2026-06-30

BEA-v1-N10EQ 是一个 **public-artifact-only design** 阶段，位于 N10EP
checkpoint `0a54b49` 之后。它 *设计*（不执行）一个前向 score/guard safety
probe，给定冻结的 arm order 与公开的 N10EO aggregate mechanism buckets，会标记
`full` novel-first arm 可能将已很强的 baseline gold file（rank 1-5）推到 rank
11-20 的 task。保守的 stop/go 只授权 **N10ER bounded public CI score/guard
safety probe contract**（design-only handoff）；它 **不** 授权 N10ER 执行。

允许输入（仅 public）：N10EP、N10EO、N10EN、N10EM 的 public artifacts/docs/
evaluator contracts。禁止输入：private diagnostic rerun、private orders/labels、
raw candidates/paths/queries/tasks/repos、per-task diagnostics、cloned repo
contents、CI temp dirs，以及任何新的 retrieval output。N10EQ 不读取这些，只消费
public aggregate bucket 值。

## N10EP source lock

```text
checkpoint: 0a54b49
status: n10ep_design_response_pass_n10eq_authorized
n10eq_design_only_authorized: true
n10eq_execution_authorized: false
next_phase: BEA-v1-N10EQ Score/Guard Safety Probe Design
source_locked: true
```

## Mechanism lock（从 N10EO public aggregate 重新推导）

```text
n10eo checkpoint: 6f8eeda
primary mechanism: novel_first_displaced_baseline_gold_from_top10
novel_first_displaced = 2
baseline_gold_rank_1_to_5_displaced = 2
candidate_available_beyond_top10 = 2
guard_better_than_full = 2
full_lost_guard_preserved = 2
low_novelty_bucket_loss = 2
diffaware_full_guard_would_preserve = 2
mechanism_locked: true
```

两次锁定的 misfire 都落在 low-novelty（`top5_novel_candidate_item_count_0_to_2`）
bucket：`full` 将少量 novel candidates 提升到已很强的 baseline gold hit 之前。
`guard` 本会保留两者。

## 结果

```text
status: n10eq_score_guard_safety_probe_design_pass_n10er_contract_authorized
self-test: 98 / 98
forbidden scan: pass
design-only: true
aggregate-buckets-only: true
n10er_contract_authorized_bool: true
n10er_execution_authorized_bool: false
next allowed phase: BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe
```

## Future probe features（design-only，7 个特征）

每个特征都仅从 **public aggregate buckets** 推导；不直接读取 per-task
candidates/labels/paths/ranks/gold，不调 threshold。

| Feature | 对应 misfire 数 | 推导来源 |
|---|---|---|
| `top5_novel_candidate_item_count_bucket` | 2 | public aggregate novelty buckets（冻结 0_to_2 / 3 / 4_to_5） |
| `baseline_prefix_strength` | 2 | public aggregate baseline hit buckets |
| `baseline_gold_proxy` | 2 | public aggregate baseline hit buckets（bucket-level 代理，非 gold labels） |
| `full_displacement_risk` | 2 | public aggregate 组合（low-novelty + strong-prefix） |
| `guard_preservation_ref` | 2 | public aggregate guard outcome buckets（参考，非 promotion） |
| `candidate_available_beyond_top10` | 2 | public aggregate mechanism buckets |
| `arm_selection` | 2 | frozen rule 仅可观测 |

## Probe input/output contracts

**Input contract**：N10EQ 自身只读取 public artifacts。如果 N10ER 被单独授权，它可以在 execution time 私下产生/读取 bounded public-CI arm orders、raw candidate lists、retrieval output、per-task diagnostic state，以及 orders frozen 之后的 score-phase labels。这些只作为 private execution-time inputs；raw orders/candidates/labels/paths/queries/tasks/repos 永不公开，gold 也永不用于 policy selection。

**Output contract**：probe 仅输出 **aggregate-bucket safety flags**（per-bucket
displacement-risk counts、guard-preservation reference counts、arm-selection
counts）。它 **不** 输出基于 raw candidates/paths/ranks 的 per-task flags、
per-task gold presence、threshold-tuned values、method-winner claims 或
runtime/default changes。输出经 scanner 校验隐私。

## N10ER pass/fail gates（design-only）

1. N10ER 可以使用 private bounded-CI execution inputs，但 public output 必须 aggregate-only，且 raw publication 为 0。
2. Displacement-risk 输出仅 aggregate-bucket（无 per-task raw 输出）。
3. 不调 threshold（冻结 threshold >= 4 不变）。
4. 不 claim method winner（不推广 guard/full/diffaware）。
5. 不改 runtime/default（safety probe 保持 opt-in/eval-only）。
6. 在 held-out manifest-listed public sample（非锁定的 N10EN sample）上做
   reproducibility 检查；通过要求 aggregate 报告且无 promotion。

所有 gate 都在 aggregate buckets 上评估；不使用 gold 作为 policy。

## Risk controls（7 个，全部已控制）

| Risk | Mitigation |
|---|---|
| aggregate overinterpretation from two cases | bucket-level 代理；held-out public sample gate 阻断 locked-sample 复用 |
| hindsight threshold tuning in probe design | 特征可观测地使用冻结 buckets；threshold_tuning_bool=false；N10ER gate 阻断 tuning |
| guard promotion from two cases | guard_preservation_ref 是参考而非 promotion；promotion_authorized_bool=false |
| private diagnostic leakage into probe features | 每个特征仅从 public aggregates 推导；reads_per_task_data_bool=false；scanner 阻断 raw 键 |
| runtime/default creep via safety probe | runtime_default_change_bool=false；N10ER gate 阻断 runtime/default 变更 |
| N10ER execution creep from contract authorization | contract_authorized=true 但 execution_authorized=false；stop/go 分离 contract 与执行 |
| feature proxy treated as gold | 代理是 bucket-level aggregate 推断；N10ER 可私下使用 score-phase labels，但 gold_used_for_policy_bool=false |

## Boundary

N10EQ 只授权基于 public aggregate artifacts 的 score/guard safety probe
**设计**，以及 **N10ER bounded public CI contract handoff**（design-only）。
它 **不** 授权：N10ER 执行、N10EQ 执行、threshold tuning、新 policy
experiments、frozen-rule 变更、推广 guard/full/diffaware、runtime/default
变更、method-winner claims、downstream/scaled retrieval、selector/reranker、
provider/model network、raw diagnostic publication、CI variant execution 或对
frozen rule 的任何更改。这些 claim-boundary 字段全部为 `false`。
`n10er_contract_authorized_bool=true` 但 `n10er_execution_authorized_bool=false`。

Next allowed phase：**BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe**
（contract 已授权，执行未授权）。

## Artifact

- Helper：`eval/bea_v1_n10eq_score_guard_safety_probe_design.py`
- Report：`artifacts/bea_v1_n10eq_score_guard_safety_probe_design/bea_v1_n10eq_score_guard_safety_probe_design_report.json`
