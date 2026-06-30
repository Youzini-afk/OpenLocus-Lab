# BEA-v1-N10EO Difference-Aware CI Regression Failure Analysis

日期：2026-06-30

BEA-v1-N10EO 解释为什么 BEA-v1-N10EN broader-sample public CI canary 发生 regression。它读取已提交的 N10EN aggregate artifact，锁定 canary run 28449370879 的 source result，使用匹配的 private diagnostic rerun 做 per-task mechanism analysis，并输出 aggregate-only report。它不从 aggregate counts alone 反推机制。不发布 clones/candidates/labels/tasks/paths/queries/ranks/per-task outcomes。

## 锁定的 N10EN source result

```text
status: difference_aware_winner_ci_canary_outcome_regression
baseline 39/40/40/40
full     37/40/40/40  lost 2
guard    39/40/40/40  lost 0
diffaware 37/40/40/40 lost 2
selected arms: full=49 guard=9
task_with_gold=40
citation 3636/3636
```

## 结果

```text
status: n10eo_failure_analysis_pass_mechanism_identified
diagnostic_source: private_diagnostic_rerun
forbidden scan: pass
primary mechanism: novel_first_displaced_baseline_gold_from_top10
```

## Regression 机制

Difference-aware rule 在 `top5_novel_candidate_item_count >= 4` 时选择 `guarded`（9 个 task，均在 4_to_5 novelty bucket），否则选择 `full`（49 个 task，在 0_to_2 与 3 bucket）。在 49 个 `full`-selected task 中的 2 个上，`full` 的 novel-first 重排将 baseline gold file 移出了 top-10。

这 2 个 task 的 gold 在 baseline 中已经很靠前，位于 rank 1-5。`full` 将少量 novel candidates（top5 novel count 0-2）提升到这个 baseline hit 之前，把它推到 rank 11-20。`guard`（保留原 top-5，仅追加 distinct novel files）保留了两者。gold candidate 仍在 `full` order 的 top-10 之外可用（`candidate_available_beyond_top10`），所以损失是重排位移，不是 candidate 缺失失败。

由于 `diffaware` 在这 2 个 task 上选择了 `full`，regression 镜像了 `full` 的损失。Guard 本会保留两者（`diffaware_selected_full_and_guard_would_preserve = 2`）。

## Aggregate diagnostic buckets

### Category 1: top-5 novelty buckets

| Bucket | Tasks | Gold | Selected full | Selected guard | Baseline top10 | Full top10 | Guard top10 | Diffaware top10 | Full lost | Diffaware 选 full 但 guard 会保留 |
|---|---|---|---|---|---|---|---|---|---|---|
| 0_to_2 | 47 | 40 | 47 | 0 | 39 | 37 | 39 | 37 | 2 | 2 |
| 3 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 4_to_5 | 9 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 |

### Category 2: full-vs-guard outcome buckets

| Bucket | Count |
|---|---|
| full_better_than_guard | 0 |
| guard_better_than_full | 2 |
| full_equals_guard_both_hit | 37 |
| full_equals_guard_both_miss | 1 |
| full_lost_guard_preserved_baseline | 2 |
| guard_lost_full_preserved_baseline | 0 |
| both_lost_baseline | 0 |
| neither_lost_baseline | 37 |

### Category 3: lost-baseline mechanism buckets

| Mechanism | Count |
|---|---|
| novel_first_displaced_baseline_gold_from_top10 | 2 |
| baseline_gold_rank_6_to_10_displaced | 0 |
| candidate_available_beyond_top10 | 2 |
| old_pool_proxy_misclassified_gold_as_novel_or_old | 0 |
| distinct_file_packing_changed_gold_file_position | 0 |
| duplicate_file_or_same_file_competition | 0 |
| baseline_gold_rank_1_to_5_displaced | 2 |
| candidate_missing_from_arm_order | 0 |
| score_phase_label_only_issue | 0 |
| other_or_unclassified | 0 |

### Category 4: arm-selection counterfactuals

| Counterfactual | Count |
|---|---|
| diffaware_selected_full_and_full_lost | 2 |
| diffaware_selected_full_and_guard_would_preserve | 2 |
| diffaware_selected_full_and_guard_same | 37 |
| diffaware_selected_guard_and_guard_preserved | 0 |
| diffaware_selected_guard_and_full_would_improve | 0 |

### Category 5: privacy/validity summary

Citation validity 3636/3636（全部 implemented）。Privacy scan 通过。不上传 raw per-task diagnostics、candidates、labels、queries、paths 或 ranks。仅 aggregate-buckets artifact。

## Boundary

N10EO 仅授权从锁定 N10EN artifact 加匹配的 private diagnostic rerun 进行 aggregate-bucket failure analysis。不授权 runtime/default changes、method-winner claims、downstream claims、scaled retrieval、selector/reranker、provider/model network、raw artifact publication 或对 frozen rule 的任何更改。Regression 是有效的 research result；不授权回退 rule 或推广替代方案。

Next allowed phase：**BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism
Response**。N10EP 只能基于 N10EO aggregate mechanism buckets 做 analysis/design。
它不授权 threshold tuning、新 policy experiments、frozen rule change、推广
guard/full/diffaware、runtime/default change、method-winner claim、downstream/scaled
retrieval 或 raw diagnostics publication。

## Artifact

- Helper：`eval/bea_v1_n10eo_difference_aware_ci_regression_failure_analysis.py`
- Report：`artifacts/bea_v1_n10eo_difference_aware_ci_regression_failure_analysis/bea_v1_n10eo_difference_aware_ci_regression_failure_analysis_report.json`
