# BEA-v1-N7 Recovered Fixed-Pool Rank-Order Result Audit

日期：2026-06-29

BEA-v1-N7 是对 N6XFR-E recovered fixed-pool rank-order experiment 的 public-artifact-only audit。它只读取 committed public N6XFR-E report 以及 supporting public N5/N6F contracts。它不读取 private rows，不检查 ignored/private storage，不 recompute outcomes，不运行 OpenLocus，不 rerun retrieval，不生成 candidates，也不修改 N6XFR-E artifact。

## 结果

```text
status: recovered_fixed_pool_rank_order_result_audit_pass_n8_authorized
self-test: 14 / 14
forbidden scan: pass
case count: 40
arm count: 4
public arm outcome rows: 160
best arm: extra_depth_promote_before_primary_prefix_4
best top10 recovery: 25 / 40
best regression count: 0
threshold: top10 >= 16 and regressions <= 2
N8 authorized: true
```

## Audit findings

- N6XFR-E source status 为 `recovered_fixed_pool_rank_order_experiment_pass_n7_authorized`，且 forbidden scan 通过。
- Public outcome schema 对全部 160 rows 均匹配 N6F 的 14-field schema。
- 四个 arms 都使用 fixed-pool order-transform semantics，provenance rule bucket 为 `original_rank_le_20_primary_rank_gt_20_extra_depth_no_gold_signal`。
- 在本 audit boundary 中，candidate-pool changed count、new-retrieval count、selector/reranker count、gold-used-for-ordering count、hard-cap violations 与 private-read count 均为零。
- Best arm 是 `extra_depth_promote_before_primary_prefix_4`，top-10 recovery 为 25/40，regressions 为 0；N5 threshold 通过。

## 决策

N7 只授权 `BEA-v1-N8 Independent Recompute Same Private Rows Same Four Arms`。N8 仅为 audit/recompute scope。N7 不授权 P5、BEA-v1-A、selector/reranker execution、retrieval expansion、N8 scope 之外的 reruns、runtime/default promotion、policy changes、counterfactuals、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit.py`
- Report: `artifacts/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit_report.json`
