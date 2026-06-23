# BEA-FD2-A1:直接 FD1 目标失败归因重放

日期:2026-06-23(BEA-FD2-A No-Go 之后的失败机制归因重放。它不是新的
选择/获取阶段,不是 FD2-B,不是 P4/P5,也不是 v0.31/v0.32 调参。它解释
*为什么* 直接聚合 FD1 损失加权在同一个有界 FD2-A 帧上选出了更差的证据集。)

> `claim_level = bea_fd2a1_failure_attribution_replay_only`。所有 no-claim /
> no-runtime-change 标志为 false。`role_proxy_used=false` 与
> `target_support_proxy_used=false` 继承自 FD2-A 扫描器规则。
> `provider_calls_made=false` 为绑定不变量。

## 绑定上下文

- BEA-FD2-A 结果检查点:`df82ddb`;本地检查点:`709b0cb`;CI 运行
  `28025382422`;状态 `no_go_no_fd1_loss_reduction`。
- FD2-A 强烈改变了选择,但聚合 FD1 损失恶化,且 file_recall/MRR 相对
  冻结 v0.3 与 coverage-only 均退化。
- FD2-A1 原样重跑 FD2-A(策略/权重/阈值/臂/预算/方法/帧不变),使用
  `/tmp` 下的私有 trace 目录,解析 FD2-A 私有 trace,并将退化仅归因到
  聚合机制桶。

## 机制桶(8 个)

FD2-A 退化仅归因到聚合桶。一条记录可落入多个桶;计数为聚合。

1. `gold_file_displacement` — v0.3 保留了金标文件,但 FD2-A 把它替换
   掉了(可操作)。
2. `correct_file_rank_worsened` — 两个臂都保留了金标文件,但 FD2-A 用
   完预算且 MRR 相对 v0.3 无改善(可操作)。
3. `correct_file_span_worsened` — 两个臂都保留了金标文件,但 FD2-A 丢
   失了正确 span(可操作)。
4. `redundancy_overcorrection` — v0.3 保留了重复项,FD2-A 抑制了它们,
   但 FD2-A 仍退化(去重过度纠正;可操作)。
5. `latency_category_non_actionable_or_dominating` — FD2-A 延迟恶化,或
   `latency_cost` 目标分量占主导(可操作)。
6. `aggregate_weight_category_collision` — FD1 二元类别反向变动(一个改
   善而另一个恶化)→ 冻结权重冲突(可操作)。
7. `candidate_availability_limit` — 去重候选池低于 `2*budget`(结构性可
   用性限制;No-Go 主导)。
8. `diffuse_or_unclassified` — 退化但无任何可操作桶命中,或未退化
   (无可操作机制可归因;No-Go 主导兜底桶)。

## 数据策略

- 用同一个固定 38 条帧与 `/tmp` 下的私有 trace 目录确定性重跑 FD2-A。
  FD2-A 策略/权重/阈值/臂/预算/方法**不变**。
- 解析 FD2-A 私有 score(190)、decision(190)、FD1-objective
  feature(190)、post-hoc decomposition(950)、objective config(1)trace。
- 仅读取已提交的 FD2-A 公共工件与 FD1 聚合工件作为重放匹配上下文
  (只读;绝不修改)。
- 不从 FD2-A 结果调权重/阈值/策略。不新增记录/检索方法/臂/留出验证。

## 公共工件契约

仅聚合、仅记录。不含私有记录 ID、路径、查询、代码片段、span、候选键、
选择顺序、objective-config 载荷、或私有 trace 路径。仅含计数、比率、
哈希、schema 名称与聚合指标。

必需公共表(仅记录,自然键):

- `source_run_records`:`(source_phase, source_ci_run_id)` — 重放匹配上下文
  (期望 vs 重放计数、已提交状态、源检查点/CI-run/schema/hash)。
- `pairwise_outcome_delta_records`:`(baseline_arm, treatment_arm, metric)`
  — 从已提交 FD2-A 公共 `arm_delta_records` 重新打包。
- `mechanism_bucket_records`:`(mechanism_bucket,)` — 每桶计数、归因比率、
  退化比率、is_actionable、is_no_go_dominating。
- `component_delta_records`:`(component, baseline_arm, treatment_arm)`
  — 从已提交 FD2-A 公共 `ablation_delta_records` 重新打包。
- `counterfactual_availability_records`:`(counterfactual_bucket,)` —
  池中存在更优候选或被 v0.3/coverage 选中的记录聚合计数。
- `category_collision_records`:`(collision_pair,)` — 每个 FD1 类别冲突对
  的聚合计数。
- `gate_records`:`(gate,)` — fail-closed 门。
- `private_manifest_records`:`(manifest_name,)` — 路径绝不序列化;仅
  计数/哈希/存储类。
- `failure_category_count_records`:`(failure_category,)`。
- `framing`、`forbidden_scan`。

## CI 门(fail-closed)

手动 CI 工作流 `bea-fd2a1-failure-attribution-replay.yml` 仅在
`workflow_dispatch` 且 `enable_external_benchmark_network=true` 时运行。
真实重放需要公共网络访问 + 已提交 FD1 工件 + 已构建的 OpenLocus 二进制。
不使用 provider secrets/vars/model env。私有 JSONL/JSON 文件**绝不**上传。

Fail-closed 校验(仅真实运行):

- `records_attributed == 38`。
- 私有 trace 计数精确:score 190、decision 190、FD1-objective feature
  190、post-hoc decomposition 950、objective config 1。
- 私有 trace 解析失败:零。
- `forbidden_scan.status == pass`。
- `replay_protocol_match == true`(解析计数匹配期望且匹配已提交;已提交
  状态为 No-Go;records_successful == 38)。
- `provider_calls_made == false`。
- 全部 8 个机制桶存在;桶分配总和 >= records_attributed(记录可落入
  多个桶)。
- 仅记录的公共形状;每个公共记录表的自然键唯一性。
- 无禁用顶层字段(私有/逐记录/声明/动态字典镜像/self-test 详情)。

允许状态(真实运行):`bea_fd2a1_attribution_replay_pass` |
`no_go_mechanism_diffuse` | `no_go_candidate_availability_limit`。
`unavailable_with_reason` 仅对默认无网络工件有效；`no_go_replay_mismatch`、
`fail_forbidden_scan` 和 `fail_schema_contract` 是失败状态，不是 CI-valid 结果。

## 状态

- `bea_fd2a1_attribution_replay_pass` — 重放匹配;>=60% 的退化记录落入
  一或两个可操作桶;非候选可用性主导;非扩散主导。
- `no_go_mechanism_diffuse` — 退化扩散(可操作浓度 < 0.60),或无记录退
  化(无可归因)。
- `no_go_candidate_availability_limit` — 候选可用性桶占据退化记录的多数。
- `no_go_replay_mismatch` — 私有 trace 计数/已提交状态/records_successful
  不匹配已提交 FD2-A 结果；这不是 CI-valid 结果。
- `unavailable_with_reason` — 默认无网络工件(如实;非假通过)。
- `fail_forbidden_scan` / `fail_schema_contract` — schema/泄漏失败；不是
  CI-valid 结果。

## FD2-A1 之后的停止/进行规则

仅当满足以下条件时,才进入设计新目标:

- >=60% 的 FD2-A 退化落入一或两个可操作机制桶,且
- 反事实聚合表显示池中存在更优候选或被 v0.3/coverage 选中,且
- 由此得到的修正是结构性的,而非"试试新权重"。

若失败扩散、由候选可用性主导、重放不匹配、或仅靠事后调参可修,则为
No-Go。

## 校验

```text
python3 -m py_compile eval/bea_fd2a1_failure_attribution_replay.py  => PASS
python3 eval/bea_fd2a1_failure_attribution_replay.py --self-test  => PASS (404/404 checks)
python3 eval/bea_fd2a1_failure_attribution_replay.py \
  --out artifacts/bea_fd2a1_failure_attribution/bea_fd2a1_failure_attribution_replay_report.json  => PASS
  (默认无网络 status: unavailable_with_reason, forbidden_scan=pass)
gh workflow run bea-fd2a1-failure-attribution-replay.yml \
  -f enable_external_benchmark_network=true  => PASS (run 28027342996,
  status: bea_fd2a1_attribution_replay_pass, records_attributed=38,
  主导桶: latency_category_non_actionable_or_dominating=38/38)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Manual CI 结果

Manual CI run `28027342996` 10m42s 绿色完成，`status = bea_fd2a1_attribution_replay_pass`。
重放匹配已提交 FD2-A 结果，并归因全部 38 条成功/退化记录：

- records_attributed：38
- records_regressed：38
- 私有 trace 计数：score 190、decision 190、FD1-objective feature 190、post-hoc decomposition 950、objective config 1
- forbidden_scan：pass
- 主导机制桶：`latency_category_non_actionable_or_dominating` = 38/38 条记录（rate 1.0）
- 次级桶：`redundancy_overcorrection` = 4/38，`gold_file_displacement` = 3/38，`aggregate_weight_category_collision` = 3/38
- 候选可用性不是限制：`candidate_availability_limit` = 0/38，且 38/38 记录在 budget 和 2×budget 以上的池中都有更好候选。

解释：FD2-A 失败是因为冻结 FD1 objective 把决定性权重放在一个 candidate-level selection 阶段不可操作的 latency-loss 类别上。Treatment 确实改变了 selection，但 latency 类别在所有退化记录上都触发；同时较小的 gold-file displacement 与 redundancy-overcorrection 进一步伤害 file recall/MRR。这个结果只支持设计新的结构性 objective：去掉或解耦不可操作的 latency 压力，并保护 file-recall/gold-file utility；它不支持从失败的 FD2-A objective 进入 FD2-B，不支持复活 role proxy，也不支持 v0.31/v0.32 权重微调。

## 注意事项

- BEA-FD2-A1 仅为 eval/diagnostic。不是 benchmark/leaderboard/性能/
  方法赢家/校准/晋升/默认/运行时/EvidenceCore/下游价值声明。
- 默认无网络路径仍如实地为 `unavailable_with_reason`，且
  `provider_calls_made=false`、`records_attributed=0`；它**不是**假通过。
  已提交 artifact 现在记录 manual CI 重放结果。
- 真实重放使用公共网络 + 已提交 FD1 工件 + 已构建 OpenLocus 二进制；它
  在 `/tmp` 下原样重跑 FD2-A 并解析生成的私有 trace。私有 trace **绝不**
  提交或上传。
- FD2-A 策略/权重/阈值在 FD2-A1 中**不变**;重放原样复用
  `bea_fd2a_direct_fd1_objective_setwise_smoke`。
- 这是同一个 P1/P2/P3 成功配额帧,重叠已披露;它不是新的留出/不相交
  验证,也不是 FD2-B。
