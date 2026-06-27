# BEA-v1-N3 Extra-Depth Merge-Order Design Simulation

日期：2026-06-27

BEA-v1-N3 是基于 closed BEA-v1-N2 D2=40 private candidate rows 的离线确定性 design simulation。它追问：一个冻结、非学习、非 gold、仅改变 merge order 的策略，能否在同一 candidate pool 与 budget 下，把 N2 的 extra-depth gold-file candidates 从 rank 21-50 移入 actionable top-10 pack。

N3 **仅是 design/simulation**。它不实现或授权 P5、BEA-v1-A、selector/reranker execution、provider calls、新 retrieval、broad retrieval expansion、runtime/default promotion、frozen P4 promotion、method-winner 声明或 downstream-value 声明。

## Closed N2 输入合约

Evaluator 会验证 result checkpoint `ce47caf`、source checkpoint `7c90213`、empirical CI `28272769423` 的 closed N2 public artifact：

- status：`n2_rank_pack_actionability_decomposition_pass`；
- D2：40；
- primary blocker `extra_depth_append_blocked`：40；
- first gold-file rank bucket `rank_21_50`：40；
- top20 recovery：0；
- top50/top100 recovery：40/40；
- unique-file top10 recovery：0；
- evidence materializable：40；
- forbidden scan：pass。

Network-enabled N3 使用 N2/N1 helpers 在 `/tmp` 下重新生成 private ordered rows 并重建 private D2 rows。它**不**重新运行完整 P4L four-arm scheduler validation。默认无网络 artifact 会诚实输出 `unavailable_with_reason`。

## D3 denominator

`D3_total` 等于 closed N2 D2 design denominator，预期精确为 40：

- 属于 closed N2 D2；
- frozen P4 在 final pool 中某处到达 gold file；
- first gold-file rank bucket 为 `rank_21_50`；
- gold file 不在 top-10；
- gold file 在 top-50 内；
- evidence materializable；
- candidate order 与 channel/source metadata 可私下获得。

若 D3 不能精确重建，N3 必须输出 No-Go 或 fail-schema，而不是近似机制声明。

## 预声明 simulation arms

所有 arms 只能按 source/channel/phase/original order 重排现有 frozen P4 candidates。Policy 不使用 gold labels、snippets/content relevance scoring、learned weights、新 retrieval 或新 files。

1. `frozen_p4_order` — baseline diagnostic。
2. `fixed_interleave_2_primary_1_extra_after_4` — 保留前 4 个 original candidates，然后按 2 primary : 1 extra-depth 合并剩余候选。
3. `early_extra_depth_quota_3` — 为 first extra-depth candidates 预留 3 个 top-10 slots，并保持顺序。
4. `bounded_promotion_after_primary_prefix_4_3` — 固定前 4 个 primary candidates，然后把前 3 个 extra-depth candidates 插入到剩余 primary candidates 前。

## Pass criteria

`n3_merge_order_design_simulation_pass` 要求：closed N2 artifact valid、`D3_total==40`、scanner pass、candidate pool unchanged、无 retrieval expansion、无 selector/reranker/P5/v1-A/provider path，且至少一个非 baseline 预声明 arm 满足：

- `top10_gold_file_recovery_rate >= 0.50`；
- hard-cap violation count 为 0；
- recovered evidence materializable rate >= 0.95；
- original top-10 file retention rate >= 0.50。

若只有在不可接受的 retention/materialization/hard-cap tradeoff 下才达到 recovery，则为 `n3_merge_order_tradeoff_no_go`；没有 arm 达到 recovery threshold，则为 `n3_merge_order_design_inconclusive`。

## 公开/私有边界

Public artifacts 只能包含 aggregate metrics 与经过 scanner 验证的 sanitized rows。Sanitized row fields 必须且只能是：`anonymous_local_id`、`denominator`、`source_bucket`、`language_bucket`、`baseline_first_gold_rank_bucket`、`sim_arm`、`top10_recovery_bucket`、`evidencecore_materializable`、`original_top10_retention_bucket`、`duplicate_pressure_delta_bucket`、`hard_cap_violation`。

禁止公开：raw paths、exact ranks、exact spans、gold lines、snippets/content、candidate lists、scores、task IDs、可识别 repo names、source-linkable hashes、private trace paths、prompts/responses 和 provider payloads。

## Status vocabulary

- `unavailable_with_reason`
- `fail_schema_contract`
- `fail_forbidden_scan`
- `no_go_n3_n2_artifact_or_trace_unavailable`
- `no_go_n3_insufficient_design_denominator`
- `no_go_n3_incomplete_closed_n2_reconstruction`
- `n3_merge_order_design_exploratory`
- `n3_merge_order_design_inconclusive`
- `n3_merge_order_tradeoff_no_go`
- `n3_merge_order_design_simulation_pass`

## 当前状态

实现已就绪，等待 manual network CI。本文档不声明最终 N3 empirical CI results。
