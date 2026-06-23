# BEA-v0.4-P3：支持/互补代理修复冒烟

日期：2026-06-23（BEA-v0.4-P3 支持/互补代理修复冒烟——P1/P2 之后最后一个
有界角色代理修复阶段，回答运行时清洁的支持/互补特征能否在以修复后 P2 目标
锚点为条件的前提下，产生非退化的支持可用性、选择目标+支持配对、相对
P1/P2/v0.3 实质性改变集合选择，并避免质量回归）

BEA-v0.4-P3 **仅为支持/互补修复证据**，不是 v0.4 证明，不是完整 v0.4 矩阵，
不是 benchmark/leaderboard/性能，不是胜者，不是校准，不是晋升，不是默认/策略
变更，不是 runtime/retriever/pack/backend/EvidenceCore 语义变更，也不是新鲜
不相交验证。它不修改 P1/P2 结果文件/artifact；冻结 P1 与 P2 代理原样复用为
`setwise_complementarity_v0_4_p1` 与 `setwise_complementarity_v0_4_p2_target_repair`
对照臂。它不事后调优 v0.3 或 v0.4 权重，不运行完整 v0.4 矩阵，不扩展
dense/graph/QuIVer/provider 范围。这是最后一个有界角色代理修复冒烟；无 P4/P5。

> `claim_level = bea_v04_p3_support_complementarity_repair_smoke_only`。所有
> 无声明/无运行时变更标志为 false。
> `algorithm_changed_during_bea_v04_p3=false`、
> `weights_tuned_during_bea_v04_p3=false`、
> `v03_tuned_during_bea_v04_p3=false`、`p1_artifact_modified=false`、
> `p2_artifact_modified=false`、`v04_full_matrix_claimed=false`。

## 问题

运行时清洁的**支持/互补**特征能否在以修复后 P2 目标锚点为条件的前提下，
产生非退化的支持可用性、选择目标+支持配对、相对 P1/P2/v0.3 实质性改变
集合选择，并避免质量回归？

## P2 根因与 P3 修复

P2 产生有效 No-Go（状态 `no_go_target_proxy_still_unavailable`）：目标可用性
修复为 `1.0` 且目标选中 `1.0`，但支持可用性坍缩为 `0.0`，选择几乎未变
（`selection_diff_p2_vs_v03=0.105263`、`selection_diff_p2_vs_p1=0.0`）；质量
安全保持。P2 根因：P2 将接近最佳的候选吸收进目标角色
（`target_near_best`，与最高内在目标分数相差 `0.15` 以内），未给支持角色
留下候选。

P3 修复（确定性、运行时清洁、无 gold/私有标签）：

- P3 复用 P2 修复后目标锚点（内在查询匹配分数），并将目标角色仅保留给
  **锚点**（top-1，若满足 P2 目标阈值 `>= 0.40`）。这释放了 P2 吸收进目标的
  接近最佳候选。
- P3 支持角色是**更丰富的互补分数**，相对目标锚点：不同文件 + 目录/包关系 +
  方法来源互补 + 排名互补 + span 局部性/紧致度 + 非目标重复 + 跨文件同包/模块
  前缀 + 检索输出已有的符号式名称重叠 + 目标-支持配对多样性，阈值 `>= 0.25`。
  这既避免 P1 的支持=一切（仅不同文件贡献 `0.15`，不足以达到阈值），也避免
  P2 的支持=空无（更多信号 + 更低阈值达到区间）。

## 必需臂（7 个；无 v0.2，无 seeded_random，无 synergy-only，无完整矩阵臂）

`bea_v0_3_anchor_span_latency`、`setwise_complementarity_v0_4_p1`（冻结旧代理）、
`setwise_complementarity_v0_4_p2_target_repair`（冻结 P2 对照）、
`support_complementarity_repair_only_same_budget`、
`setwise_complementarity_v0_4_p3_support_repair`（P3 处理臂）、
`bm25_prefix_same_budget`、`rrf_same_budget`。

处理臂：`setwise_complementarity_v0_4_p3_support_repair`。
质量基线：`bea_v0_3_anchor_span_latency`。

## 允许的支持/互补信号

修复后 P2 目标锚点；查询/路径 token 关系；候选文件不同于目标文件；候选目录/包
与目标路径的关系；方法来源互补；排名互补；span 局部性/紧致度；候选非目标重复；
跨文件但同包/模块前缀；检索输出已有的符号式名称重叠；目标-支持配对多样性。
无 gold/私有标签，无人工逐行检查，无 provider/LLM 调用，无 dense/graph/QuIVer，
无逐仓库调优，无事后阈值搜索。

## 数据集 / 协议

同 P1/P2 开发帧，成功配额，失败即关闭门控：
- `records_successful >= 30`
- `contextbench_successful >= 20`
- `repoqa_successful >= 10`

固定协议：预算 5，方法 `bm25,regex,symbol`，原始尝试上限 ContextBench 480 /
RepoQA 240。强制排除窗口：BEA-2/3/4（ContextBench [40,160)，RepoQA [20,80)）。
BEA-5 重叠披露，不排除。BEA-v0.4-P1 与 BEA-v0.4-P2 重叠披露，不排除：P3 复用
P1/P2 帧并复用 P2 修复后目标锚点；不从 P1/P2 聚合推断。P1+P2+P3 记录重叠可能。
这是 P3 支持/互补修复证据，不是新鲜不相交验证。

若新鲜不相交产出不可行，实现失败关闭为 `unavailable_with_reason`。

## 硬门控

代理可行性（修复后）：
- `target_proxy_available_rate_p3 >= 0.70`
- `target_proxy_selected_rate_p3 >= 0.70`
- `support_proxy_available_rate_p3 >= 0.30` 且 `<= 0.90`
- `support_proxy_selected_rate_p3 >= 0.20`
- `target_support_pair_available_rate_p3 >= 0.25`
- `target_support_pair_selected_rate_p3 >= 0.20`
- `unknown_only_record_rate_p3 <= 0.30`

非退化：
- `mean_support_candidates_per_record_p3 >= 1.0` 且 `<= 8.0`
- `same_file_support_rate_p3 <= 0.50`

行为：
- `selection_diff_rate_p3_vs_v03 >= 0.25`
- `selection_diff_rate_p3_vs_p2 >= 0.20`
- `selection_diff_rate_p3_vs_p1 >= 0.20`
- `mean_duplicate_file_count_v04_p3 <= mean_duplicate_file_count_v03`
- `mean_candidate_source_diversity_v04_p3 >= mean_candidate_source_diversity_v03`

质量安全：
- `file_recall@10_v04_p3 >= v03 - 0.05`
- `mrr_v04_p3 >= v03 - 0.05`
- `span_f0.5@10_v04_p3 >= v03 - 0.02`
- `latency_seconds_v04_p3 <= v03 * 1.25`

至少一个相对 v0.3 的方向性改进：更低 duplicate_file_rate 或更低
label_file_absent_rate 或更低 correct_file_wrong_span_rate 或更低
latency_without_quality_gain 或更低 budget_spent_on_low_marginal_gain 或更高
quality_per_latency。

## 状态

`bea_v04_p3_support_complementarity_repair_pass`、
`partial_support_proxy_signal`、
`no_go_support_proxy_still_unavailable`、
`no_go_support_proxy_degenerate`、`no_go_no_selection_change`、
`no_go_quality_regression`、`unavailable_with_reason`、
`fail_forbidden_scan`、`fail_schema_contract`。

## 公开 artifact 表（仅记录、自然键）

- `source_run_records`：`(source_phase, source_ci_run_id)`
- `arm_metric_records`：`(arm, metric)`
- `arm_delta_records`：`(baseline_arm, treatment_arm, metric)`
- `role_proxy_summary_records`：`(role_proxy, summary_field)`
- `setwise_behavior_records`：`(behavior_field,)`
- `support_complementarity_records`：`(support_field,)`
- `failure_family_records`：`(failure_family, policy_arm, availability)`
- `win_tie_loss_records`：`(baseline_arm, treatment_arm, metric)`
- `availability_records`：`(category, availability)`
- `benchmark_attempt_records`：`(benchmark,)`
- `manifests`：`(manifest_name,)` 仅记录表，包含名为
  `private_score_manifest`、`private_decision_manifest`、
  `private_role_proxy_manifest`、`private_support_feature_manifest`、
  `private_pair_feature_manifest` 的条目；仅聚合
  计数/哈希/存储/path_publicly_serialized=false
- `forbidden_scan`：扫描摘要
- `hard_gate_records`：仅记录聚合门控值 + 布尔
- `failure_category_count_records`：仅记录失败类别计数

无公开记录 ID、仓库 URL、提交、路径、查询、gold 标签、span、代码片段、候选
文件、决策顺序、分数组件或逐记录角色标签。无顶层 manifest 字典镜像，无
`hard_gates`/`failure_category_counts` 等动态字典。

## 私有 `/tmp` JSONL 文件

五个私有 JSONL 文件仅在 `/tmp` 下写入且永不上传：分数行（每个策略臂每条记录
一行；`record_count == records_successful * len(fixed_arms)`）、决策行（每个
P3 接受动作一行；预期计数记录于 `source_run_records`）、角色代理行（P3 修复后
赋值，每个候选一行）、支持特征行（P3 支持/互补诊断，每个候选一行）、配对特征行
（每条记录一行，目标-支持配对诊断）。公开 artifact 仅携带 manifest 摘要
（计数 + 哈希 + 存储类；`path_publicly_serialized=false`）。若私有写入不完整，
实现失败关闭。

## 失败家族枚举（12 个，同 BEA-FD1）

`label_file_absent`、`label_span_absent`、`correct_file_wrong_span`、
`redundant_same_file_candidates`、`too_many_anchor_slots`、
`missing_support_candidate`、`support_selected_without_target`、
`target_selected_without_support`、`risk_penalty_removed_gold`、
`early_stop_too_early`、`budget_spent_on_low_marginal_gain`、
`latency_without_quality_gain`。

## 验证

```text
python3 -m py_compile eval/bea_v04_p3_support_complementarity_repair_smoke.py  => PASS
python3 eval/bea_v04_p3_support_complementarity_repair_smoke.py --self-test  => PASS (400/400 检查)
python3 eval/bea_v04_p3_support_complementarity_repair_smoke.py \
  --out artifacts/bea_v04_p3_support_complementarity_repair/\
bea_v04_p3_support_complementarity_repair_smoke_report.json  => PASS
  （状态：unavailable_with_reason，无网络默认 artifact，
   provider_calls=0，forbidden_scan=pass，
   algorithm_changed_during_bea_v04_p3=false、
   weights_tuned_during_bea_v04_p3=false、
   v03_tuned_during_bea_v04_p3=false、
   p1_artifact_modified=false、p2_artifact_modified=false、
   v04_full_matrix_claimed=false、
   self_test_checks_total=400、self_test_checks_passed=400）
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

默认无网络 artifact 诚实地返回 `unavailable_with_reason`
（`network_mode=disabled_opt_in`）。真实冒烟证据来自 manual CI run
`28022595796`。

## Manual CI 结果

Manual CI run `28022595796` 通过 fail-closed workflow，并产生有效 P3 No-Go：
status `no_go_support_proxy_degenerate`，records_successful=38（ContextBench
20、RepoQA 18），attempted=46，excluded=8，forbidden_scan=pass，self-test
400/400。私有 manifest 仅写入 `/tmp`：score rows=266，decision rows=190，
role-proxy rows=760，support-feature rows=760，pair-feature rows=38。

P3 过度修复了 P2 的 support-collapse 失败：target proxy available/selected
rate 都为 1.0，support proxy available/selected rate 都为 1.0，target-support
pair available/selected rate 都为 1.0。但 support proxy 已退化：
`support_proxy_available_rate_p3=1.0` 超过 <=0.90 gate，且
`mean_support_candidates_per_record_p3=18.289474` 超过 <=8.0 gate。P3
确实相对 v0.3/P2/P1 实质改变 selection（diff rate 0.5 / 0.394737 /
0.394737），但质量相对 v0.3 退化：file_recall@10 0.710526 vs 0.763158
（delta -0.052632），MRR 0.414474 vs 0.569737（delta -0.155263），
span_f0.5@10 0.035311 vs 0.038842，latency +0.001730s，
quality_per_latency 0.015992 vs 0.016856。

决定：P3 是最后一个有界 role-proxy repair。不要运行 P4/P5，不要从当前
role-proxy 设计进入完整 v0.4 矩阵，也不要做 v0.31/v0.32 权重微调。下一步
算法工作必须转向直接 FD1-objective setwise acquisition，而不是继续修代理。

## 注意事项

- BEA-v0.4-P3 仅为 eval/诊断。不是 benchmark/leaderboard/性能/胜者/校准/晋升/
  默认/runtime/EvidenceCore/下游价值声明。不是 v0.4 证明。不是完整 v0.4 矩阵。
  不是新鲜不相交验证。
- P3 仅修复支持/互补代理特征，以冻结 P2 修复后目标锚点为条件。它不运行完整
  v0.4 矩阵，不调优 v0.3，不进行事后阈值搜索。v0.3 算法/权重冻结；
  `v03_tuned_during_bea_v04_p3=false`；`p1_artifact_modified=false`；
  `p2_artifact_modified=false`。
- 角色代理为确定性运行时清洁，无 gold/私有标签，无 provider/LLM 调用。
- 新鲜冒烟协议披露 BEA-5、BEA-v0.4-P1 与 BEA-v0.4-P2 重叠（不是新鲜不相交
  验证）。
- 私有分数/决策/角色代理/支持特征/配对特征 JSONL 文件仅在 `/tmp` 下写入且
  永不上传。
