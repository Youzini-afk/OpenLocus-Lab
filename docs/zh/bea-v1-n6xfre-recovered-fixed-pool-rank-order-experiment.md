# BEA-v1-N6XFR-E Recovered Fixed-Pool Rank-Order Experiment

日期：2026-06-29

BEA-v1-N6XFR-E 使用本地恢复的 private N2 rank-pack rows 重新打开 fixed-pool rank-order route。它是新的 public phase，不改写 N6 历史。Evaluator 只读取 recovered private row content 来计算 fixed-pool order-transform outcomes，然后只公开 scanner-safe 的 N6F public buckets 与 aggregate counts。

## 结果

```text
status: recovered_fixed_pool_rank_order_experiment_pass_n7_authorized
self-test: 14 / 14
forbidden scan: pass
private rank-pack rows read: 40
fixed arms: 4
private outcome rows computed: 160
public sanitized arm outcome rows: 160
best top10 recovery: 25 / 40
threshold: top10 >= 16 and regressions <= 2
N7 audit authorized: true
runtime/default promotion authorized: false
```

## Arms

四个 N5 arms 均以 fixed-pool order transforms only 方式评估：

- `baseline_n2_order`
- `extra_depth_promote_before_primary_prefix_4`
- `bounded_interleave_primary2_extra1`
- `late_extra_depth_demote_after_primary_prefix_8`

Evaluator 使用不含 gold signal 的 deterministic recovered-row provenance rule：原始 ranks 1-20 为 primary，ranks > 20 为 extra-depth evidence。所有 transforms 都保留 bucket 内原始顺序，不增加 candidates、不删除 candidates、不运行 retrieval，也不使用 selector/reranker。

## Metrics

| Arm | Top-10 recovery | Top-20 recovery | Regressions | Status |
|---|---:|---:|---:|---|
| baseline_n2_order | 0 / 40 | 0 / 40 | 0 | below threshold |
| extra_depth_promote_before_primary_prefix_4 | 25 / 40 | 34 / 40 | 0 | passes threshold |
| bounded_interleave_primary2_extra1 | 10 / 40 | 14 / 40 | 0 | below threshold |
| late_extra_depth_demote_after_primary_prefix_8 | 0 / 40 | 0 / 40 | 0 | below threshold |

N5 pass threshold 仍为 top-10 recovery 至少 16 / 40，且 regressions 不超过 2。Recovered experiment 通过 `extra_depth_promote_before_primary_prefix_4` 达到 25 / 40，且 regressions 为 0。

## 决策

N6XFR-E 只授权 `BEA-v1-N7 Recovered Fixed-Pool Rank-Order Result Audit`。它不授权 runtime/default promotion、policy changes、retrieval/reruns、candidate-pool generation/materialization、selector/reranker execution、P5、BEA-v1-A、counterfactuals、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment.py`
- Report: `artifacts/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment_report.json`
