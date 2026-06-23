# BEA-v0.4-P2：目标角色代理修复冒烟

日期：2026-06-23（BEA-v0.4-P2 目标角色代理修复冒烟——BEA-v0.4-P1 的有界延续，
修复 P1 的具体失败 `target_proxy_available_rate=0.0`，回答运行时清洁的修复后
目标角色代理特征能否产生非零目标可用性，并在不发生灾难性质量回归的前提下，
相对 BEA v0.3 与冻结 P1 代理实质性改变集合选择）

BEA-v0.4-P2 **仅为目标角色修复证据**，不是 v0.4 证明，不是完整 v0.4 矩阵，
不是 benchmark/leaderboard/性能，不是胜者，不是校准，不是晋升，不是默认/策略变更，
不是 runtime/retriever/pack/backend/EvidenceCore 语义变更，也不是新鲜不相交验证。
它不修改 P1 结果文件/artifact；冻结 P1 代理原样复用为
`setwise_complementarity_v0_4_p1` 对照臂。它不事后调优 v0.3 或 v0.4 权重，不运行
完整 v0.4 矩阵，不扩展 dense/graph/QuIVer/provider 范围。

> `claim_level = bea_v04_p2_target_proxy_repair_smoke_only`。所有无声明/无运行时变更
> 标志为 false。`algorithm_changed_during_bea_v04_p2=false`、
> `weights_tuned_during_bea_v04_p2=false`、`v03_tuned_during_bea_v04_p2=false`、
> `p1_artifact_modified=false`、`v04_full_matrix_claimed=false`。

## 问题

运行时清洁的**修复后**目标角色代理特征能否产生非零目标可用性，并在不发生灾难性
质量损失的前提下，相对 BEA v0.3 与冻结 P1 代理实质性改变集合选择？

## P1 根因与 P2 修复

P1 产生有效 No-Go / 弱负向（状态 `no_go_proxy_unavailable`，CI run `28017063082`）：
`target_proxy_available_rate=0.0`、`support_proxy_available_rate=1.0`、
`setwise_selection_diff_rate_vs_v03=0.105263`。Explorer 定位了两个根因，二者均以
确定性运行时清洁特征修复（无 gold/私有标签）：

- P1 目标门控要求精确同 span 多方法一致（`agreement >= 2`）加紧致 span/路径重叠。
  真实候选极少满足同 span 一致>=2，因此目标可用性坍缩为 0.0。P2 取消硬性
  `agreement >= 2` 门控，改用**内在查询匹配分数**（查询/路径 token 重叠 + span
  紧致度 + bm25/symbol 存在 + 连续一致性 + 路径深度局部性）赋值目标角色，阈值
  `>= 0.40` 且 top-N 封顶（与最高值相差 `0.15` 以内）。
- P1 支持门控在批量赋值时对空 `accepted_paths/dirs` 求值，因此每个候选都是"新文件"，
  支持可用性退化为 1.0。P2 改为**相对目标锚点**赋值支持（不同文件/目录 + 不同方法
  来源 + span 紧致度 + 查询重叠），而非对空已接受集合求值。

## 必需臂（6 个；按计划省略 seeded_random）

`bm25_prefix_same_budget`、`bea_v0_3_anchor_span_latency`、
`setwise_complementarity_v0_4_p1`（冻结旧代理）、
`target_role_repair_only_same_budget`、
`setwise_complementarity_v0_4_p2_target_repair`、`rrf_same_budget`。

处理臂：`setwise_complementarity_v0_4_p2_target_repair`。
质量基线：`bea_v0_3_anchor_span_latency`。

## 允许的修复信号

查询 token；候选路径/basename token；已有 symbol-ish 检索输出；方法 rank/source 一致性；
span 紧致度/局部性；文件/类型/路径启发式；来源多样性与重复文件状态。无 gold/私有标签，
无 provider/LLM 调用，无 dense/graph/QuIVer，无 per-repo 调优，无人工逐行检查，
无事后阈值搜索。

## 数据集 / 协议

同 P1 开发帧，成功配额，失败即关闭门控：
- `records_successful >= 30`
- `contextbench_successful >= 20`
- `repoqa_successful >= 10`

固定协议：预算 5、方法 `bm25,regex,symbol`、原始尝试上限 ContextBench 480 / RepoQA 240。
强制排除窗口：BEA-2/3/4（ContextBench [40,160)、RepoQA [20,80)）。BEA-5 重叠已披露
但不排除。BEA-v0.4-P1 重叠已披露但不排除：P2 复用 P1 帧并在一个进程中重新运行候选池
与臂；不从 P1 聚合推断。P1+P2 记录重叠可能。这是 P2 目标角色修复证据，不是新鲜
不相交验证。

如果新鲜不相交产量不可行，实现将失败关闭为 `unavailable_with_reason`。

## 硬门控

角色代理可行性（修复后）：
- `target_proxy_available_rate_p2 >= 0.30`
- `support_proxy_available_rate_p2 >= 0.30`
- `target_proxy_selected_rate_p2 >= 0.20`
- `unknown_only_record_rate_p2 <= 0.30`

行为：
- `selection_diff_rate_p2_vs_v03 >= 0.25`
- `selection_diff_rate_p2_vs_p1 >= 0.20`
- `mean_duplicate_file_count_v04_p2 <= mean_duplicate_file_count_v03`
- `mean_candidate_source_diversity_v04_p2 >= mean_candidate_source_diversity_v03`

质量安全：
- `file_recall@10_v04_p2 >= v03 - 0.05`
- `mrr_v04_p2 >= v03 - 0.05`
- `span_f0.5@10_v04_p2 >= v03 - 0.02`
- `latency_seconds_v04_p2 <= v03 * 1.25`

至少一个方向性改进 vs v0.3：更低 duplicate_file_rate 或更低 label_file_absent_rate
或更低 correct_file_wrong_span_rate 或更低 latency_without_quality_gain 或更低
budget_spent_on_low_marginal_gain 或更高 quality_per_latency。

## 状态

`bea_v04_p2_target_proxy_repair_pass`、`partial_target_proxy_signal`、
`no_go_target_proxy_still_unavailable`、`no_go_no_selection_change`、
`no_go_quality_regression`、`unavailable_with_reason`、
`fail_forbidden_scan`、`fail_schema_contract`。

## 公开产物表（仅记录、自然键）

- `source_run_records`：`(source_phase, source_ci_run_id)`
- `arm_metric_records`：`(arm, metric)`
- `arm_delta_records`：`(baseline_arm, treatment_arm, metric)`
- `role_proxy_summary_records`：`(role_proxy, summary_field)`
- `setwise_behavior_records`：`(behavior_field,)`
- `target_proxy_repair_records`：`(repair_field,)`
- `failure_family_records`：`(failure_family, policy_arm, availability)`
- `win_tie_loss_records`：`(baseline_arm, treatment_arm, metric)`
- `availability_records`：`(category, availability)`
- `benchmark_attempt_records`：`(benchmark,)`
- `manifests`：`(manifest_name,)` records-only 表，包含名为
  `private_score_manifest`、`private_decision_manifest`、
  `private_role_proxy_manifest`、`private_target_feature_manifest` 的记录；
  仅聚合 count/hash/storage/path_publicly_serialized=false
- `forbidden_scan`：扫描摘要
- `hard_gate_records`：records-only 聚合门控值 + 布尔值
- `failure_category_count_records`：records-only 失败类别计数

无公开记录 ID、仓库 URL、提交、路径、查询、gold 标签、span、片段、候选文件、
决策顺序、分数组件或每条记录角色标签。

## 私有 `/tmp` JSONL 文件

四个私有 JSONL 文件仅写入 `/tmp` 且永不上传：score 行（每记录每策略臂一条；
`record_count == records_successful * len(fixed_arms)`）、decision 行（每个 P2
accepted action 一条；期望数量记录在 `source_run_records`）、role-proxy 行
（P2 修复后赋值，每候选一条）、target-feature 行
（P2 target-feature 诊断，每候选一条）。公开 artifact 仅携带 manifest 摘要
（count + hash + storage class；`path_publicly_serialized=false`）。若私有写入
不完整，实现失败关闭。

## 失败家族枚举（12 个，与 BEA-FD1 相同）

`label_file_absent`、`label_span_absent`、`correct_file_wrong_span`、
`redundant_same_file_candidates`、`too_many_anchor_slots`、
`missing_support_candidate`、`support_selected_without_target`、
`target_selected_without_support`、`risk_penalty_removed_gold`、
`early_stop_too_early`、`budget_spent_on_low_marginal_gain`、
`latency_without_quality_gain`。

## 验证

```text
python3 -m py_compile eval/bea_v04_p2_target_role_proxy_repair_smoke.py  => PASS
python3 eval/bea_v04_p2_target_role_proxy_repair_smoke.py --self-test  => PASS (335/335 checks)
python3 eval/bea_v04_p2_target_role_proxy_repair_smoke.py \
  --out artifacts/bea_v04_p2_target_role_proxy_repair/\
bea_v04_p2_target_role_proxy_repair_smoke_report.json  => PASS
  (status: unavailable_with_reason, 无网络默认 artifact,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea_v04_p2=false,
   weights_tuned_during_bea_v04_p2=false,
   v03_tuned_during_bea_v04_p2=false,
   p1_artifact_modified=false,
   v04_full_matrix_claimed=false,
   self_test_checks_total=335, self_test_checks_passed=335)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

Manual CI run `28020331024` 通过 fail-closed workflow，并取代默认无网络 artifact。
结果是有效的 P2 No-Go：status `no_go_target_proxy_still_unavailable`，
records_successful=38（ContextBench 20、RepoQA 18），attempted=46，excluded=8，
forbidden_scan=pass，private SCORE rows=228，decision rows=190，role-proxy rows=760，
target-feature rows=760。

P2 修复了 P1 的 target-role proxy 可用性失败：target proxy availability 从 0.0
升至 1.0，target-selected rate 为 1.0。但该修复暴露了新的 blocker：support proxy
availability 从 1.0 降为 0.0，P2-vs-P1 selection difference 仍为 0.0，
P2-vs-v0.3 selection difference 仍只有 0.105263（低于 0.25）。相对 v0.3 没有
灾难性质量退化（file_recall@10 和 MRR delta 为 0.0，span_f0.5@10 -0.003036，
latency +0.001789s，quality_per_latency -0.000857），但 P2 不足以支持进入完整
v0.4 矩阵。

## 注意事项

- BEA-v0.4-P2 仅为评估/诊断。不是 benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value 声明。不是 v0.4 证明。不是完整 v0.4 矩阵。
  不是新鲜不相交验证。
- P2 仅修复目标角色代理特征。它不运行完整 v0.4 矩阵，不调优 v0.3，不进行事后阈值搜索。
  v0.3 算法/权重冻结；`v03_tuned_during_bea_v04_p2=false`；
  `p1_artifact_modified=false`。
- 角色代理为确定性运行时清洁，无 gold/私有标签，无 provider/LLM 调用。
- 新鲜冒烟协议披露 BEA-5 与 BEA-v0.4-P1 重叠（不是新鲜不相交验证）。
- 私有 score/decision/role-proxy/target-feature JSONL 文件仅写入 `/tmp` 且永不上传。
