# BEA-v0.4-P1：集合角色代理冒烟

日期：2026-06-23（BEA-v0.4-P1 集合角色代理冒烟——在新鲜小规模外部冒烟切片上，
将评估本地的确定性角色代理集合选择策略与 BEA v0.3 及同预算对照组进行比较；
回答角色代理集合选择是否改变 v0.3 行为并在不发生灾难性质量回归的前提下减少
FD1 失败家族）

BEA-v0.4-P1 **仅为 P1 冒烟证据**，不是 v0.4 证明/性能/胜者/默认/校准/下游价值。
它不实现完整 v0.4 矩阵。不运行 B16-K，不调优 v0.31 权重，不触碰
runtime/default/EvidenceCore，不扩展 dense/graph/QuIVer/provider 范围。

> `claim_level = bea_v04_p1_setwise_role_proxy_smoke_only`。所有无声明/
> 无运行时变更标志为 false。`algorithm_changed_during_bea_v04_p1=false`、
> `weights_tuned_during_bea_v04_p1=false`、`v04_full_matrix_claimed=false`。

## 问题

确定性角色代理集合选择能否改变 BEA v0.3 行为，并在不发生灾难性质量损失的前提下
减少 FD1 失败家族？

## 必需臂（6 个；RRF 因廉价且稳定而包含）

`bm25_prefix_same_budget`、`bea_v0_3_anchor_span_latency`、
`role_proxy_only_same_budget`、`setwise_complementarity_v0_4_p1`、
`seeded_random_same_budget`、`rrf_same_budget`。

处理臂：`setwise_complementarity_v0_4_p1`。
质量基线：`bea_v0_3_anchor_span_latency`。

## 角色代理固定枚举（确定性、运行时清洁）

`target_proxy`、`support_proxy`、`unknown`。不使用任何 gold/私有标签。
信号来源：方法一致性、BM25/RRF/regex/symbol 来源、查询/路径 token 重叠、
AST/路径角色启发式、span 紧致度、同文件/跨文件关系、来源多样性。

## v0.4 P1 集合选择规则（冻结、无事后调优）

- 如果可用，至少选择一个 `target_proxy`（预留目标槽位）。
- 优先选择来自不同文件/符号家族的 `support_proxy`。
- 惩罚重复同文件选择（强惩罚）。
- 奖励新颖性/来源多样性/span 紧致度。
- 冻结权重：target=0.40、support_cross_file=0.20、
  source_diversity=0.15、span_tight=0.10、novelty=0.10、
  dup_file_penalty=-0.35、weak_support_penalty=-0.15。

## 数据集 / 协议

新鲜小规模外部冒烟（成功配额），失败即关闭门控：
- `records_successful >= 30`
- `contextbench_successful >= 20`
- `repoqa_successful >= 10`

固定协议：预算 5、方法 `bm25,regex,symbol`、原始尝试上限
ContextBench 480 / RepoQA 240。强制排除窗口：BEA-2/3/4
（ContextBench [40,160)、RepoQA [20,80)）。BEA-5 重叠已披露但不排除
（BEA-5 在同一完整帧上使用成功配额且未消耗全部帧）。BEA-0/BEA-1 尽力披露。
这是 P1 冒烟证据，不是新鲜不相交验证。

如果新鲜不相交产量不可行，实现将失败关闭为
`unavailable_with_reason`。离线 BEA-4/5 反事实重放作为未来扩展文档化
（私有轨迹缺少完整候选列表，因此无法在同一候选上重新运行 v0.4 P1 选择）。

## 硬门控

角色代理可行性：
- `role_proxy_assignment_rate >= 0.70`
- `target_proxy_available_rate >= 0.50`
- `support_proxy_available_rate >= 0.30`
- `unknown_only_record_rate <= 0.30`

行为：
- `setwise_selection_diff_rate_vs_v03 >= 0.25`
- `mean_duplicate_file_count_v04 <= mean_duplicate_file_count_v03`
- `mean_candidate_source_diversity_v04 >= mean_candidate_source_diversity_v03`

质量安全：
- `file_recall@10_v04 >= v03 - 0.05`
- `mrr_v04 >= v03 - 0.05`
- `span_f0.5@10_v04 >= v03 - 0.02`
- `latency_seconds_v04 <= v03 * 1.25`

至少一个方向性改进 vs v0.3：更低 duplicate_file_rate 或更低
gold_file_absent_rate 或更低 correct_file_wrong_span_rate 或更高
quality_per_latency。

## 状态

`bea_v04_p1_smoke_pass`、`partial_directional_signal`、
`no_go_proxy_unavailable`、`no_go_no_selection_change`、
`no_go_quality_regression`、`unavailable_with_reason`、
`offline_counterfactual_replay`、`fail_forbidden_scan`、
`fail_schema_contract`。

## 公开产物表（仅记录、自然键）

- `source_run_records`：`(source_phase, source_ci_run_id)`
- `arm_metric_records`：`(arm, metric)`
- `arm_delta_records`：`(baseline_arm, treatment_arm, metric)`
- `role_proxy_summary_records`：`(role_proxy, summary_field)`
- `setwise_behavior_records`：`(behavior_field,)`
- `failure_family_records`：`(failure_family, policy_arm, availability)`
- `win_tie_loss_records`：`(baseline_arm, treatment_arm, metric)`
- `availability_records`：`(category, availability)`
- `benchmark_attempt_records`：`(benchmark,)`
- `private_score_manifest`、`private_decision_manifest`、
  `private_role_proxy_manifest`：仅聚合（count/hash/storage/
  path_publicly_serialized=false）
- `forbidden_scan`：扫描摘要
- `hard_gate_records`：records-only 聚合门控值 + 布尔值
- `failure_category_count_records`：records-only 失败类别计数

无公开记录 ID、仓库 URL、提交、路径、查询、gold 标签、
span、片段、候选文件、决策顺序、分数组件或每条记录角色标签。

## 失败家族枚举（12 个，与 BEA-FD1 相同）

`gold_file_absent`、`gold_span_absent`、`correct_file_wrong_span`、
`redundant_same_file_candidates`、`too_many_anchor_slots`、
`missing_support_candidate`、`support_selected_without_target`、
`target_selected_without_support`、`risk_penalty_removed_gold`、
`early_stop_too_early`、`budget_spent_on_low_marginal_gain`、
`latency_without_quality_gain`。

可用 vs 不可用类别与 BEA-FD1 一致。v0.4 P1 为
`redundant_same_file_candidates` 增加了角色代理感知分类（通过集合行为可用），
而 support-target 类别在私有轨迹携带角色标签之前仍为
`unavailable_no_support_label`。

## 验证

```text
python3 -m py_compile eval/bea_v04_p1_setwise_role_proxy_smoke.py  => PASS
python3 eval/bea_v04_p1_setwise_role_proxy_smoke.py --self-test  => PASS (269/269 checks)
python3 eval/bea_v04_p1_setwise_role_proxy_smoke.py \
  --out artifacts/bea_v04_p1_setwise_role_proxy/\
bea_v04_p1_setwise_role_proxy_smoke_report.json  => PASS
  (status: unavailable_with_reason, no-network artifact,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea_v04_p1=false,
   weights_tuned_during_bea_v04_p1=false,
   v04_full_matrix_claimed=false,
   self_test_checks_total=269, self_test_checks_passed=269)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 注意事项

- BEA-v0.4-P1 仅为评估/诊断。不是 benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value 声明。不是 v0.4 证明。不是完整 v0.4 矩阵。
- v0.3 算法/权重冻结；`algorithm_changed_during_bea_v04_p1=false`。
- 角色代理为确定性运行时清洁，无 gold/私有标签。
- 新鲜冒烟协议披露 BEA-5 重叠（不是新鲜不相交验证）。如果新鲜产量不可行，
  状态为 `unavailable_with_reason`。
- 手动 CI（启用网络）是产生真实冒烟证据的必要条件；
  默认无网络产物真实地为 `unavailable_with_reason`。
- 私有 score/decision/role-proxy JSONL 文件仅写入 `/tmp` 且永不上传。
