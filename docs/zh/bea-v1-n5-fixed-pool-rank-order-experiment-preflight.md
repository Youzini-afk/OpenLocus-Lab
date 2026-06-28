# BEA-v1-N5 Fixed-Pool Rank-Order Experiment Preflight

日期：2026-06-28

BEA-v1-N5 是面向 BEA-v1-N6 的 no-execution preflight。它只读取已提交的公开 N4、N2、N3 与 P4L artifacts；不读取 `.openlocus/private`，不运行 retrieval，不重跑 P4L/N1/N2/N3，不执行 selector/reranker，不调 policy，不改变 runtime，也不做 counterfactual。

## 结果

```text
status: fixed_pool_rank_order_experiment_preflight_pass_n6_authorized
self-test: 15 / 15
forbidden scan: pass
eligible fixed-pool cases: 40
rank window: rank_21_50
top20 recovery: not_recovered
top50/top100 recovery: recovered
blocker: extra_depth_append_blocked
fixed-pool order-transform arms: 4
N6 authorized: true
```

## 冻结的 N6 case set

本 preflight 冻结 exactly 40 条 N4 sanitized rank-blocker cases。聚合行如下：

```text
eligible_case_count=40
rank_window_bucket=rank_21_50
top20_recovery_bucket=not_recovered
top50_or_top100_recovery_bucket=recovered
blocker_bucket=extra_depth_append_blocked
fixed_pool_deeper_present_bool=true
private_or_source_linkage_required_bool=false
case_set_frozen_bool=true
```

如公开 per-case rows，只包含匿名 N5 case id、rank/window/pool/blocker/merge-order buckets，以及 language/source buckets。

## Fixed-pool arms

N6 只能执行以下四个 arms：

1. `baseline_n2_order`
2. `extra_depth_promote_before_primary_prefix_4`
3. `bounded_interleave_primary2_extra1`
4. `late_extra_depth_demote_after_primary_prefix_8`

每个 arm 都只能是 fixed-pool order-transform。Candidate pool 不得变化；new retrieval、selector/reranker execution、policy tuning 均为 false。

## Metrics 与 pass gate

Primary metric：`top10_recovery_count_over_40_fixed_cases`。

Secondary metrics：`top20_recovery_count`、`rank_window_shift_bucket`、`hard_cap_violation_count`、`case_regression_count`。

Pass threshold bucket 为 `top10_recovery_ge_16_and_regressions_le_2`。Baseline reference 为 `n2_baseline_order_zero_top10_over_40`。N5 不声明 method winner，也不授权 downstream claims。

## 决策

N5 只授权 **BEA-v1-N6 Fixed-Pool Rank-Order Experiment** 范围：使用已提交公开 N2/N3 fixed-pool fields，在 40 条 N4 sanitized rank-blocker cases 上执行预先声明的 fixed-pool order-transform arms。它不授权 new retrieval、reruns、selector/reranker execution、private reads、runtime/policy changes、counterfactuals、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n5_fixed_pool_rank_order_experiment_preflight.py`
- Report: `artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json`
