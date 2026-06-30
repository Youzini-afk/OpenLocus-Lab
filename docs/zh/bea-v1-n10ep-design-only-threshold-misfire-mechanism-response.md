# BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism Response

日期：2026-06-30

BEA-v1-N10EP 是一个 **public-artifact-only design packaging** 阶段，位于
N10EO checkpoint `6f8eeda` 之后。它将 N10EO aggregate mechanism buckets 重新
表达为 *design-only* response：描述前向 design options（N10EQ score/guard
safety probe、N10ER public CI small variant，以及 stop-design-only-insufficient
选项），记录约束这些选项的 risk controls，并给出保守的 stop/go 决策。N10EP
**不执行任何操作**。

允许输入（仅 public）：已提交的 N10EO public aggregate artifact、N10EN public
aggregate artifact、N10EM public artifact/docs/evaluator contract，以及 public
docs/code metadata。禁止输入：`/tmp/n10eo_diag_rerun`、`orders.private.json`、
private labels JSONL、raw candidates/orders/paths/queries/tasks/repos、per-task
diagnostics、cloned repo contents，以及任何新的 retrieval/CI variants/policy
execution。N10EP 不读取 N10EO 使用过的任何 private diagnostic inputs，只消费
public aggregate bucket 值。

## N10EO source lock

```text
checkpoint: 6f8eeda
status: n10eo_failure_analysis_pass_mechanism_identified
next_allowed_phase: BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism Response
source_locked: true（status、primary mechanism、aggregate counts、mechanism
  buckets、full/guard outcome、low-novelty bucket loss 均匹配）
```

## 结果

```text
status: n10ep_design_response_pass_n10eq_authorized
self-test: 69 / 69
forbidden scan: pass
design-only: true
aggregate-buckets-only: true
next allowed phase: BEA-v1-N10EQ Score/Guard Safety Probe Design
```

## Mechanism response summary（public aggregate 值）

冻结的 difference-aware rule 为
`if top5_novel_candidate_item_count >= 4 then guarded else full`。在 N10EN
public CI canary 上，该 rule 在 49 个 `full`-selected task 中的 2 个上发生
misfire：`full` 的 novel-first 重排将已在 rank 1-5 的 baseline gold 推到 rank
11-20。`guard` 本会保留两者。

| Aggregate | 值 |
|---|---|
| baseline / full / guard / diffaware top10 | 39 / 37 / 39 / 37 |
| full_lost / guard_lost / diffaware_lost | 2 / 0 / 2 |
| guard_better_than_full | 2 |
| full_lost_guard_preserved | 2 |
| baseline_gold_rank_1_to_5_displaced | 2 |
| candidate_available_beyond_top10 | 2 |
| novel_first_displaced_baseline_gold_from_top10 | 2 |
| low_novelty_bucket_loss（0_to_2 bucket） | 2 |
| diffaware_full_guard_would_preserve | 2 |

两次损失都落在 low-novelty（`top5_novel_candidate_item_count_0_to_2`）bucket：
`full` 将少量 novel candidates 提升到已很强的 baseline hit 之前。gold candidate
仍在 top-10 之外可用，所以损失是重排位移，不是 candidate 缺失失败。

## Design options（design-only，不执行）

### N10EQ — Score/Guard Safety Probe Design

设计一个 score/guard safety probe，给定冻结的 arm order 和
`top5_novel_candidate_item_count` 特征，标记 `full` novel-first arm 可能将
已很强的 baseline gold file（rank 1-5）推到 rank 11-20 的 task。该 probe 只使用
N10EO 的 aggregate-bucket diagnostics；不读取 per-task
candidates/labels/paths/ranks。该 design **被授权进入下一阶段**（design-only，
执行仍未授权）。

### N10ER — Public CI Small Variant Design

设计一个小的 public CI variant，在略微不同的 manifest-listed public sample 上
重跑冻结的 difference-aware rule，以确认 threshold-misfire 是否复现或仅是 2-case
artifact。该 design 仅限 public-CI，并复用 N10EN bounded canary scope。在保守
默认下，该 design **已打包但尚未被授权**进入下一阶段（使用
`--authorize-n10er-design` 可同时授权 N10EQ 与 N10ER design；无论哪种，执行都
未授权）。

### Stop — Design-Only Insufficient

仅基于 2 个 aggregate misfire case 的 design-only 分析不足以解决
threshold-misfire。不基于 2 个 case 就把任何 design 提升为执行；任何 rule
change、promotion 或 execution 都需要进一步的 bounded public evidence。

## Risk controls

| Risk | Mitigation |
|---|---|
| aggregate overinterpretation from two cases | design-only response；无 promotion 或 rule change；显式记录 stop_design_only_insufficient 选项 |
| hindsight threshold tuning | threshold_tuning_authorized_bool=false；frozen rule 不变；任何 threshold design 必须使用 held-out public evidence |
| guard promotion from two cases | guard_full_diffaware_promotion_authorized_bool=false；不推广任何 arm；改为 design-only N10EQ safety probe |
| public CI variant as method winner | method_winner_claim_authorized_bool=false；N10ER 是 design-only，未执行，即使之后运行也不是 method winner |
| private diagnostic leakage | N10EP 只读取 public aggregate artifacts；forbidden_scan 阻断 raw per-task/paths/orders/labels 键与 private rerun 路径 |
| runtime/default creep | runtime_default_change_authorized_bool=false；任何 safety probe 保持 opt-in/eval-only；无 runtime 或 default 变更 |

## Boundary

N10EP 只授权基于 N10EO public aggregate artifact 的 **design-only** response
packaging。它明确 **不** 授权：threshold tuning、新 policy experiments、
frozen-rule 变更、推广 guard/full/diffaware、runtime/default 变更、method-winner
claims、downstream/scaled retrieval、selector/reranker、provider/model network、
raw diagnostic publication、CI variant execution 或对 frozen rule 的任何更改。
这些 claim-boundary 字段全部为 `false`。保守的 stop/go 只授权 N10EQ design
（不执行）；默认下 N10ER design 已打包但未授权。不读取任何 private diagnostic
inputs。

Next allowed phase：**BEA-v1-N10EQ Score/Guard Safety Probe Design**
（design-only，不执行）。

## Artifact

- Helper：`eval/bea_v1_n10ep_design_only_threshold_misfire_mechanism_response.py`
- Report：`artifacts/bea_v1_n10ep_design_only_threshold_misfire_mechanism_response/bea_v1_n10ep_design_only_threshold_misfire_mechanism_response_report.json`
