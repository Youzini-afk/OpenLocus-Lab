# BEA-FD2-A：直接 FD1 目标 Setwise 采集冒烟

日期：2026-06-23（BEA-FD2-A 直接 FD1 目标 setwise 采集冒烟——在
BEA-v0.4-P3 停止角色代理路线之后的直接算法后续。它测试一个 setwise 选择器
是否能直接优化从已提交的 FD1 聚合产物派生的冻结 FD1 失败损失缩减，同时不使用
target/support 代理且不产生质量回退。）

BEA-FD2-A 不是 legacy role-proxy P4/P5，不是完整 v0.4 矩阵，不是 v0.31/v0.32 权重微调，
也不是新鲜的不相交验证。它是同一个 P1/P2/P3 成功配额帧上的一个有界
算法变更冒烟。

> `claim_level = bea_fd2a_direct_fd1_objective_setwise_smoke_only`。所有
> 无声明/无运行时变更标志为 false。`role_proxy_used=false` 和
> `target_support_proxy_used=false` 是绑定的自测不变式。

## 前序阶段绑定上下文

P1 失败：`target_proxy_available_rate=0.0`，support 退化为 1.0。P2 修复：
target 可用性修正为 1.0，但 support 坍缩为 0.0，选择相较 v0.3 几乎不变
（`0.105263`）。P3 修复：恢复了 support 可用性，但选择/质量无法在全帧上
保持。FD2-A 完全弃用角色代理——FD2-A 处理不使用角色代理分配逻辑。

## 固定臂（5 个）

1. `bm25_prefix_same_budget`
2. `rrf_same_budget`
3. `bea_v0_3_anchor_span_latency`（质量基线）
4. `fd1_coverage_only_same_budget`（相关性 + 覆盖/多样性，无 FD1 权重）
5. `fd1_loss_weighted_setwise_same_budget`（处理：增加冻结 FD1 权重）

无 P1/P2/P3 角色代理臂，无 seeded random，无 v0.2/v0 控制，无
dense/graph/QuIVer/provider 臂。预算 5；方法 bm25,regex,symbol；候选池
bm25/regex/symbol + 派生 RRF（按需）。

## FD1 权重派生（只读输入，评估前冻结）

FD2-A 仅读取已提交 FD1 产物的公开聚合 `category_metric_loss_records`
（`artifacts/bea_fd1_failure_decomposition/bea_fd1_failure_decomposition_report.json`）
作为只读输入。它按 FD1 类别聚合 `loss_sum`（跨 source_phase / benchmark /
baseline_arm / treatment_arm / metric），并将四个可派生类别归一化为总和 1.0：

- `gold_file_absent`（loss_sum ≈ 1097.33）→ 权重 ≈ 0.2539 → `file_reach`
- `correct_file_wrong_span`（loss_sum ≈ 548.24）→ 权重 ≈ 0.1268 → `span_precision`
- `budget_spent_on_low_marginal_gain`（loss_sum ≈ 1125.36）→ 权重 ≈ 0.2604 → `novelty_diminishing_returns`
- `latency_without_quality_gain`（loss_sum ≈ 1551.05）→ 权重 ≈ 0.3589 → `latency_cost`（惩罚）
- `redundant_same_file_candidates`（FD1 中 unavailable_missing_trace）→ 固定默认值 0.10 → `duplicate_penalty`（惩罚）

FD1 产物绝不被修改。选择期间不读取私有分解行、gold 标签或逐记录数据。权重
在派生时冻结，不从 FD2-A 结果中调优（无事后阈值搜索）。第五个类别使用固定
默认值，因为 FD1 将其标记为 `unavailable_missing_trace`；FD2-A 现在可以直接
从已接受的证据计算重复项。

## 处理目标

预算 5 下的贪心 setwise。得分 = coverage-only 基础优先级（相关性 +
覆盖/多样性，通过 v0.2 agreement + bm25_norm + diversity + overlap −
risk − duplication）+ FD1 损失加权目标：

```
fd1_objective = w_gold_file_absent * file_reach
              + w_correct_file_wrong_span * span_precision
              + w_budget_spent_on_low_marginal_gain * novelty_diminishing_returns
              - w_latency_without_quality_gain * latency_cost
              - w_redundant_same_file_candidates * duplicate_penalty
```

奖励组件（file_reach、span_precision、novelty）相加；惩罚组件
（latency_cost、duplicate_penalty）相减。`fd1_coverage_only_same_budget`
消融仅使用 coverage-only 基础优先级（无 FD1 权重），隔离 FD1 权重贡献。

## 运行时清洁不变式（绑定，自测）

- `role_proxy_used=false`，`target_support_proxy_used=false`（在机制级和
  报告级自测）。
- `private_decomposition_used_for_selection=false`，
  `gold_labels_used_for_selection=false`，`posthoc_threshold_search=false`。
- FD2-A 不导入任何 BEA-v0.4-P1/P2/P3 模块；处理不调用角色代理分配逻辑。
- 运行时清洁不变性：带有 gold/row_id/label 字段的污染候选产生相同选择。

## 帧（同一个 P1/P2/P3 成功配额帧）

38 条记录目标（ContextBench >=20，RepoQA >=10），带 BEA-2/3/4 强制排除窗口
和 BEA-5/P1/P2/P3 重叠披露。这不是新鲜不相交验证——它隔离了角色代理修复
失败的算法变更。若通过本可进入 heldout/不相交 FD2-B，但下面的 CI 结果并未通过。

## 门控

- 分母：records_successful >=30，ContextBench >=20，RepoQA >=10。
- 固定预算/方法/臂。
- 行为：选择差异 vs v0.3 >=0.25；vs coverage-only >=0.15；重复计数 <= v0.3；
  源多样性 >= v0.3。
- FD1 机制：复合 FD1 损失相较 v0.3 和 coverage-only 均改善；至少一个主导
  类别改善。
- 质量安全：file_recall@10 >= v0.3-0.03；MRR >= v0.3-0.05；
  span_f0.5@10 >= v0.3-0.02；latency <= v0.3*1.15。

## 公开产物表（仅记录，自然键）

- `source_run_records`：`(source_phase, source_ci_run_id)`
- `arm_metric_records`：`(arm, metric)`
- `arm_delta_records`：`(baseline_arm, treatment_arm, metric)`
- `win_tie_loss_records`：`(baseline_arm, treatment_arm, metric)`
- `fd1_category_loss_records`：`(policy_arm, fd1_category)`
- `fd1_category_rate_records`：`(policy_arm, fd1_category)`
- `fd1_objective_component_records`：`(component,)`
- `ablation_delta_records`：`(component, baseline_arm, treatment_arm)`
- `setwise_behavior_records`：`(behavior_field,)`
- `benchmark_attempt_records`：`(benchmark,)`
- `hard_gate_records`：`(gate,)`
- `failure_category_count_records`：`(failure_category,)`
- `manifests`：`(manifest_name,)` — 路径永不序列化；仅计数/哈希/存储类
- `framing`、`forbidden_scan`

无公开记录 ID、路径、仓库、查询、gold 标签、span、代码片段、候选文件、
决策顺序、逐记录特征、FD1 私有分解行、角色代理标签或 objective-config
文件路径。

## 私有产物（仅在 `/tmp` 下）

- 私有 SCORE JSONL（记录 × 5 臂）
- 私有决策 JSONL（处理选择顺序/特征）
- 私有 FD1 目标特征 JSONL（逐候选运行时清洁组件）
- 私有事后分解 JSONL（记录 × 臂 × 类别归因）
- 私有 objective-config JSON（冻结 FD1 权重 + 源产物哈希）

## 状态

`bea_fd2a_direct_fd1_objective_pass` | `partial_fd1_objective_signal` |
`no_go_no_selection_change` | `no_go_no_fd1_loss_reduction` |
`no_go_objective_ablation_only` | `no_go_quality_regression` |
`unavailable_with_reason` | `fail_forbidden_scan` | `fail_schema_contract`

## 验证

```text
python3 -m py_compile eval/bea_fd2a_direct_fd1_objective_setwise_smoke.py  => PASS
python3 eval/bea_fd2a_direct_fd1_objective_setwise_smoke.py --self-test  => PASS (373/373 检查)
python3 eval/bea_fd2a_direct_fd1_objective_setwise_smoke.py \
  --out artifacts/bea_fd2a_direct_fd1_objective/bea_fd2a_direct_fd1_objective_setwise_smoke_report.json  => PASS
  (status: unavailable_with_reason, 无网络产物,
   provider_calls=0, forbidden_scan=pass,
   role_proxy_used=false, target_support_proxy_used=false,
   fd1_artifact_modified=false, records_successful=0,
   self_test_checks_total=373, self_test_checks_passed=373)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Manual CI 结果

Manual CI run `28025382422` 9m06s 绿色完成，产出有效的 bounded No-Go 结果：

- status：`no_go_no_fd1_loss_reduction`
- records_successful：38（ContextBench 20，RepoQA 18）
- records_attempted_total：46；records_excluded：8
- private manifests：SCORE 190，decision 190，FD1-objective feature 190，post-hoc decomposition 950，objective config 1
- forbidden_scan：pass
- selection_diff_rate_fd1lw_vs_v03：0.710526（通过）
- selection_diff_rate_fd1lw_vs_coverage：0.684211（通过）
- composite FD1 loss：v0.3 0.397802，coverage-only 0.748783，FD1-weighted 0.756181（两个机制 gate 均失败）
- 质量：file_recall@10 0.684211 vs v0.3 0.763158（质量安全失败），MRR 0.516228 vs v0.3 0.569737（质量安全失败），span_f0.5@10 与 latency gate 通过

解释：FD1-weighted setwise objective 强烈改变了选择，但增加了 available FD1 composite loss，并且相对 frozen v0.3 与 coverage-only 退化 file recall/MRR。这是负向算法结果，不是 pass，也不支持进入 FD2-B。

## 停止规则

通过仅赢得 heldout/不相交 FD2-B；它不是 v0.4 证明或默认变更。失败时：
不扩展，不调优 v0.31/v0.32，不复活角色代理。

## 注意事项

- BEA-FD2-A 仅为评估/诊断。不是基准/排行榜/性能/方法优胜/校准/提升/默认/
  运行时/EvidenceCore/下游价值声明。
- 默认无网络产物诚实地为 `unavailable_with_reason`，`provider_calls=0`，
  `records_successful=0`；它不是伪造的通过。
- FD1 权重从已提交的 FD1 聚合损失记录派生；如果 FD1 产物缺失或无损失记录，
  运行为 `unavailable_with_reason`（`fd1_artifact_missing` /
  `fd1_loss_records_missing`）。
- `redundant_same_file_candidates` 使用固定默认权重（0.10），因为 FD1 将其
  标记为 `unavailable_missing_trace`；FD2-A 现在可以直接计算重复计数，因此
  此类别在 FD2-A 自己的事后分解中变为 `available`。
- 这是同一个 P1/P2/P3 成功配额帧，带披露的重叠；不是新鲜不相交验证。
