# BEA-v1-N6 Fixed-Pool Rank-Order Experiment

日期：2026-06-28

BEA-v1-N6 是 N5 授权的 fixed-pool rank-order experiment，但本地 public-artifact 运行是有效 No-Go。N6 只读取 committed public N5、N4、N2、N3 与 P4L artifacts；不读取 `.openlocus/private`，不运行 retrieval，不重跑 P4L/N1/N2/N3，不执行 selector/reranker，不调 policy，不改变 runtime，也不做 counterfactual。

## 结果

```text
status: no_go_n6_public_fixed_pool_arm_fields_insufficient
self-test: 16 / 16
forbidden scan: pass
fixed case set consistent: true
N5 arms checked: 4
exact public per-case arm mappings: 0 / 4
per-case arm outcome rows evaluated: 0
N7 result audit authorized: false
```

## 为什么 N6 是 No-Go

N5 授权了四个 exact fixed-pool arms：

1. `baseline_n2_order`
2. `extra_depth_promote_before_primary_prefix_4`
3. `bounded_interleave_primary2_extra1`
4. `late_extra_depth_demote_after_primary_prefix_8`

Committed public artifacts 不包含这些 exact N6 arms 的 exact per-case top-10 recovery/regression outcomes。N2 提供 baseline indicators，但没有 raw rank/order fields。N3 有类似 design arms 的 public per-case rows，但名称和语义都不是 exact N5/N6 arms。因此 N6 拒绝把 N3 analogues 映射成 N6 results，也拒绝从 aggregate counts 推断 arm outcomes。

## Arm mapping boundary

Evaluator 为每个 N5 arm 记录 inexact public mapping：

- `baseline_n2_order` 的 analogue bucket 是 `frozen_p4_order`，但 exact public N6 per-case outcomes 不可用。
- `extra_depth_promote_before_primary_prefix_4` 的 analogue bucket 是 `early_extra_depth_quota_3`，但 exact public N6 per-case outcomes 不可用。
- `bounded_interleave_primary2_extra1` 的 analogue bucket 是 `fixed_interleave_2_primary_1_extra_after_4`，但 exact public N6 per-case outcomes 不可用。
- `late_extra_depth_demote_after_primary_prefix_8` 的 analogue bucket 是 `bounded_promotion_after_primary_prefix_4_3`，但 exact public N6 per-case outcomes 不可用。

四个 arms 都标记为 `no_result_not_evaluated`；`per_case_arm_outcome_records` 存在且为空列表。

## 决策

N6 不授权 N7 result audit。下一阶段为 `none_until_public_fixed_pool_arm_fields_exist`。它也不授权 new retrieval、reruns、selector/reranker execution、private reads、runtime/policy changes、counterfactuals、P5、BEA-v1-A、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n6_fixed_pool_rank_order_experiment.py`
- Report: `artifacts/bea_v1_n6_fixed_pool_rank_order_experiment/bea_v1_n6_fixed_pool_rank_order_experiment_report.json`
