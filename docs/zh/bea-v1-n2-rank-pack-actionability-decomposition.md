# BEA-v1-N2 Rank/Pack Actionability Decomposition

日期：2026-06-26

BEA-v1-N2 是 BEA-v1-N1 之后的实证 decomposition 阶段。N1 已以 rank-blocked No-Go 关闭（`no_go_n1_inadequate_top10_actionable_denominator`）：D0 scheduler preservation 在 locked 272-record non-Python denominator 上通过，但 40 条 D1 span 机会全部位于 actionable top-10 pack 之外。

N2 追问：为什么 frozen P4 已在 final pool 中到达 gold file，却没有把 gold-file evidence 放进 top-10 pack。它**只做 decomposition**。它不实现或授权 P5、BEA-v1-A、selector/reranker 修改、runtime/default promotion、method-winner 声明、broad retrieval expansion 或 downstream-value 声明。

## 输入与 replay 合约

Evaluator 会验证 result checkpoint `e6772dc` / CI `28245155237` 的 closed N1 public artifact：

- status：`no_go_n1_inadequate_top10_actionable_denominator`；
- D0 locked denominator：272；
- frozen scheduler reach：baseline 0，P2 55，P3 55，P4 52；
- P4 treatment hard-cap violations：0；
- D1 total：40；
- D1 top-10 actionable：0；
- D1 rank-blocked：40；
- public forbidden scan：pass。

Network-enabled N2 不只依赖 N1 public artifact。它会在 `/tmp` 下重新生成 FD1 private decomposition，验证 private replay，重建 P4L locked denominator，并直接调用 `n1._run_frozen_p4_with_candidates(...)`，以保留 ordered final candidates 的私有 rank/score/method 字段。Private rank/pack rows 只写入 `/tmp`。

默认无网络 artifact 会诚实输出 `unavailable_with_reason`，不是实证结果。

## D2 denominator

`D2_total` 是 N1 rank-blocked 子集，需满足：

- gold line ranges 可私下重建；
- frozen P4 在 final pool 中某处到达 gold file；
- pre-refiner gold-file span 为 zero 或 inadequate overlap；
- first gold-file evidence 不在 top-10；
- candidate order/rank 可私下获得。

Adequacy gates：

- `D2_total >= 20`：adequate；
- `10 <= D2_total < 20`：exploratory；
- `D2_total < 10`：No-Go。

## 分析

对每条 D2 row，N2 私下计算精确诊断，并只公开 sanitized buckets：

- first gold-file rank bucket：`rank_11_20`、`rank_21_50`、`rank_51_100`、`rank_gt_100` 或 `rank_missing_or_invalid`；
- top20/top50/top100 rank-preserving recovery buckets；
- rank-preserving unique-file top-10 recovery bucket；
- duplicate pressure bucket；
- evidence materialization boolean；
- primary blocker bucket，必须且只能是 `pack_budget_only`、`duplicate_file_pack_waste`、`extra_depth_append_blocked`、`candidate_order_blocked`、`scheduler_cap_or_stop_blocked`、`evidence_materialization_blocked` 或 `mixed_or_unclassified` 之一。

Classification counts 必须等于 `D2_total`；否则 run fail-close。

## Design-only 授权

N2 最多只能授权后续 design work，不能授权 implementation。Design-only thresholds 为：

- pack-budget design：`top20_recovery_rate >= 0.50`；
- rank-preserving pack design：`unique_file_pack_recovery_at10 >= 0.25`；
- extra-depth merge-order design：`extra_depth_append_blocked_rate >= 0.50`；
- evidence materialization design：`evidence_materialization_blocked_rate >= 0.25`。

若一个或多个 threshold crossing，则 `design_authorized=true`，且 `design_authorized_scope` 为 `pack_budget_design_only`、`rank_preserving_pack_design_only`、`extra_depth_merge_order_design_only`、`evidence_materialization_design_only` 或 `mixed_design_audit_only`。Implementation、P5、BEA-v1-A、selector/reranker execution、runtime promotion 与 broad retrieval expansion 仍未获授权。

## Status vocabulary

- `unavailable_with_reason` — 默认无网络 artifact；不是实证结果。
- `fail_schema_contract` — infrastructure、parser、replay、D0 drift、classification 或 private-write failure 的 fail-closed 状态。
- `fail_forbidden_scan` — public artifact privacy scanner 检测到 forbidden content。
- `no_go_n2_n1_artifact_or_trace_unavailable` — 必需的 N1 artifact 或重新生成的 private traces 不可用。
- `no_go_n2_insufficient_rank_blocked_denominator` — `D2_total < 10`。
- `n2_rank_pack_decomposition_exploratory` — `10 <= D2_total < 20`。
- `n2_rank_pack_mechanism_inconclusive` — D2 adequate 且完成分类，但没有 design threshold crossed。
- `n2_rank_pack_actionability_decomposition_pass` — D2 adequate、D0/N1 preserved、所有 rows 已分类、scanner passed，且至少一个 design-only threshold crossed。

## 隐私边界

Public artifacts 只能包含 aggregate metrics 与经过 scanner 验证的 sanitized rows。不得包含 raw paths、exact ranks、exact spans、gold lines、snippets/content、raw candidate lists、repo/task ids、private trace paths、prompts/responses、provider payloads、scores 或 source-linkable hashes。

## 当前状态

实现已就绪，等待 manual network CI。本文档不声明最终 N2 empirical CI result。
