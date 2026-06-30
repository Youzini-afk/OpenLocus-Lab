# BEA-v1-N10EL Audit/Recompute of Difference-Aware Winner

日期：2026-06-30

BEA-v1-N10EL 在同一批 scoped N10DZ top100 private rows 和 N1 rows 上，独立重算 N10EK 的 winning fixed rule。它可以读取 N10EK public artifact 作为 expected aggregate values，但 policy transform 是独立重实现的，不 import 或调用 N10EK evaluator。

被审计的冻结 policy 是 exact N10EK 规则：如果 `top5_novel_candidate_item_count >= 4`，使用 `guarded_top5_novel_distinct`；否则使用 `full_novel_first`。这个 threshold 计数 top-5 candidate items，不是 distinct files。

N10EL 不运行 retrieval、OpenLocus binary execution、candidate generation、network、runtime/default changes 或 selector/reranker logic。

## 结果

```text
status: difference_aware_winner_audit_recompute_complete_n10em_authorized
self-test: 8 / 8
forbidden scan: pass
expected top10/top20/top50/top100: 13 / 16 / 20 / 26
observed top10/top20/top50/top100: 13 / 16 / 20 / 26
expected lost baseline top10: 0
observed lost baseline top10: 0
expected/observed counts match: true
n10ek code call count: 0
```

## Policy boundary

公开 artifact 明确记录 policy contract：

- `gold_used_for_policy_bool = false`
- `old_pool_membership_used_for_policy_bool = true`
- `full_guard_outcome_membership_used_for_policy_bool = false`
- `threshold_frozen_bool = true`
- threshold feature: `top5_novel_candidate_item_count`
- threshold operator/value: `>= 4`
- `n10ek_code_call_count = 0`

公开 artifact 仅包含 aggregate/bucket。不公开 paths、filenames、queries、candidates、gold labels、spans 或 exact ranks。

## Aggregate buckets

- `top5_novel_candidate_item_count_0_to_2`：41 cases
- `top5_novel_candidate_item_count_3`：2 cases
- `top5_novel_candidate_item_count_4_to_5`：17 cases
- selected `full_novel_first`：43 cases
- selected `guarded_top5_novel_distinct`：17 cases

## 含义

N10EK winner 在不使用 N10EK transform code 的前提下独立复现了 aggregate result。Gold 只用于评分，不用于 policy。Old-pool membership 被有意用来定义 novelty；full-only/guard-only outcome membership 不用于逐 case 选择。这仍然只是 same-source audit evidence；不是 runtime/default recommendation、method-winner claim、downstream claim 或 heldout/generalization claim。

## Handoff

N10EL 只授权 N10EM public replication package，随后决定是否进行 broader sample 或 CI validation。它不授权 new/scaled retrieval、OpenLocus binary execution、candidate generation、network、runtime/default changes、selector/reranker execution、method-winner claims、downstream claims 或 heldout/generalization claims。

## Artifact

- Script: `eval/bea_v1_n10el_difference_aware_winner_audit_recompute.py`
- Report: `artifacts/bea_v1_n10el_difference_aware_winner_audit_recompute/bea_v1_n10el_difference_aware_winner_audit_recompute_report.json`
