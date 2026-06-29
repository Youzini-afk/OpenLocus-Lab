# BEA-v1-N8 Independent Recompute Same Private Rows Same Four Arms

日期：2026-06-29

BEA-v1-N8 使用同一个 scoped private N2 rows 与同四个 N5 arms，对 recovered fixed-pool rank-order experiment 做 independent recompute。Transform logic 直接在 N8 中实现；不 import 或调用 N6XFR-E evaluator。Public artifact 只报告 buckets、counts 与 booleans。

## 结果

```text
status: independent_recompute_same_private_rows_pass_n9_authorized
self-test: 14 / 14
forbidden scan: pass
private rank-pack rows read: 40
other private files read: 0
arms recomputed: 4
best arm: extra_depth_promote_before_primary_prefix_4
best top10 recovery: 25 / 40
best top20 recovery: 34 / 40
regressions: 0
per-arm comparison to N6XFR-E: match
threshold reproduced: true
```

## Recompute boundary

N8 只读取一个 scoped private input bucket，不读取其他 private files。它不公开 private input path、file name、candidate lists、gold paths、exact ranks、source identifiers、snippets、hashes 或 provider payloads。它不执行 retrieval、不 rerun、不做 candidate generation/materialization、不执行 selector/reranker、不运行 P5、不进入 BEA-v1-A、不做 counterfactual，也不做 runtime/default change。

## Independent arms

四个 arms 均以 fixed-pool order-transform semantics 重新计算，provenance rule bucket 为 `original_rank_le_20_primary_rank_gt_20_extra_depth_no_gold_signal`：

- `baseline_n2_order`：top-10 为 0/40，top-20 为 0/40。
- `extra_depth_promote_before_primary_prefix_4`：top-10 为 25/40，top-20 为 34/40。
- `bounded_interleave_primary2_extra1`：top-10 为 10/40，top-20 为 14/40。
- `late_extra_depth_demote_after_primary_prefix_8`：top-10 为 0/40，top-20 为 0/40。

所有 per-arm top-10/top-20/regression counts 均与 N6XFR-E 匹配。N5 threshold 被复现：top-10 recovery 至少 16/40，且 regressions 为 0。

## 决策

N8 只授权 `BEA-v1-N9 Recovered Fixed-Pool Result Replication Package`。它不授权 P5、BEA-v1-A、selector/reranker execution、retrieval expansion、additional reruns、runtime/default promotion、policy changes、counterfactuals、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms.py`
- Report: `artifacts/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms_report.json`
