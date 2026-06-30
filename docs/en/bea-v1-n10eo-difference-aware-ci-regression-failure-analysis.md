# BEA-v1-N10EO Difference-Aware CI Regression Failure Analysis

Date: 2026-06-30

BEA-v1-N10EO explains why the BEA-v1-N10EN broader-sample public CI canary
regressed. It reads the committed N10EN aggregate artifact, locks the source
result from canary run 28449370879, uses a matching private diagnostic rerun for
per-task mechanism analysis, and emits an aggregate-only report. It does not
infer mechanisms from aggregate counts alone. No clones/candidates/labels/tasks/
paths/queries/ranks/per-task outcomes are published.

## Locked N10EN source result

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

## Result

```text
status: n10eo_failure_analysis_pass_mechanism_identified
diagnostic_source: private_diagnostic_rerun
forbidden scan: pass
primary mechanism: novel_first_displaced_baseline_gold_from_top10
```

## Regression mechanism

The difference-aware rule selects `guarded` when `top5_novel_candidate_item_count
>= 4` (9 tasks, all in the 4-to-5 novelty bucket) and `full` otherwise (49 tasks,
in the 0-to-2 and 3 buckets). On 2 of the 49 `full`-selected tasks, `full`'s
novel-first reordering displaced the baseline gold file from the top-10.

The gold in those 2 tasks was already strong in the baseline, at ranks 1-5.
`full` promoted low-novelty candidates (0-2 novel top5 candidates) ahead of that
baseline hit, pushing it to ranks 11-20. `guard` (keep original top-5, append
distinct novel files only) preserved both because it protects the original top5.
The gold candidate remained available in the `full` order beyond top-10
(`candidate_available_beyond_top10`), so the loss is a reordering displacement,
not a missing-candidate failure.

Since `diffaware` chose `full` on exactly those 2 tasks, the regression mirrors
`full`'s loss. Guard would have preserved both
(`diffaware_selected_full_and_guard_would_preserve = 2`).

## Aggregate diagnostic buckets

### Category 1: top-5 novelty buckets

| Bucket | Tasks | Gold | Selected full | Selected guard | Baseline top10 | Full top10 | Guard top10 | Diffaware top10 | Full lost | Diffaware chose full but guard would preserve |
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

Citation validity 3636/3636 (all implemented). Privacy scan pass. No raw
per-task diagnostics, candidates, labels, queries, paths, or ranks uploaded.
Aggregate-buckets-only artifact.

## Boundary

N10EO authorizes only aggregate-bucket failure analysis from the locked N10EN
artifact plus the matching private diagnostic rerun. It does not authorize runtime/default changes, method-winner claims,
downstream claims, scaled retrieval, selector/reranker, provider/model network,
raw artifact publication, or any change to the frozen rule. The regression is a
valid research result; it does not authorize reverting the rule or promoting an
alternative.

Next allowed phase: **BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism
Response**. N10EP may only analyze/design from N10EO aggregate mechanism buckets.
It may not tune thresholds, run new policy experiments, change the frozen rule,
promote guard/full/diffaware, change runtime/default behavior, claim method
winner, run downstream/scaled retrieval, or publish raw diagnostics.

## Artifact

- Helper: `eval/bea_v1_n10eo_difference_aware_ci_regression_failure_analysis.py`
- Report: `artifacts/bea_v1_n10eo_difference_aware_ci_regression_failure_analysis/bea_v1_n10eo_difference_aware_ci_regression_failure_analysis_report.json`
