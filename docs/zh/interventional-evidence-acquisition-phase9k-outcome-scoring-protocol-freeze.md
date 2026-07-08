# 干预式证据获取 第 9K 阶段 结果获取 / 评分 / 裁定协议冻结

日期: 2026-07-09

状态: `phase9k_outcome_scoring_protocol_freeze_no_claim`

授权: 仅文档/报告/验证器协议冻结，用于未来结果获取、评分和裁定规则；无执行、无私有读取、无结果、无评分、无裁定、无金标准标注、无 evidence_success、无声明

公开报告: [`phase9k_outcome_scoring_protocol_freeze_no_claim_report.json`](../../artifacts/phase9k_outcome_scoring_protocol_freeze_no_claim/phase9k_outcome_scoring_protocol_freeze_no_claim_report.json)

## 范围

第 9K 阶段是仅文档/报告/验证器的协议冻结。它冻结未来结果获取、评分和裁定协议，该协议可能紧随第 9J 阶段标注输入行之后。它不获取、克隆、读取或物化任何仓库或源。它不读取被忽略的 `runs/`、私有候选池/注册表/清单、第 9H 阶段私有物化清单或第 9J 阶段私有标注输入行/清单。它不获取结果、不评分、不裁定、不生成金标准标注、基准标注、evidence_success、结果标注、标注真值或评分/评估行。它不做出任何方法/产品/性能/模型/提供者/训练/运行时/默认/评分/结果/evidence-success/标注真值声明。

第 9K 阶段以第 9H 阶段远程提交 `d997caab5487e66c544f657645d70c97f3b780e2`、CI 运行 `28976655118`、CI 成功、第 9H 阶段状态 `phase9h_candidate_source_pool_public_source_network_fetch_materialization_readiness_no_scoring_no_claim`、第 9I 阶段远程提交 `fe9eabba744ff00526fadd7184801c3721677fba`、CI 运行 `28979060368`、CI 成功、第 9I 阶段状态 `phase9i_materialized_inventory_to_task_annotation_protocol_freeze_no_execution_no_scoring_no_claim`、第 9I 阶段协议冻结、第 9J 阶段远程提交 `25140f4017acf139012fe917fd920ddba9839cc3`、CI 运行 `28980705743`、CI 成功、第 9J 阶段状态 `phase9j_annotation_input_rows_generated_no_scoring_no_claim` 以及第 9J 阶段标注输入行已生成为门控条件。第 9G 阶段（状态 `phase9g_candidate_source_pool_network_fetch_protocol_freeze_no_execution_no_scoring_no_claim`、CI 成功、协议冻结）和第 9F 阶段状态 `phase9f_public_source_fetch_clone_materialization_repair_no_claim` 作为分桶继承来源携带；其确切远程提交/CI 运行值有意不在第 9K 阶段报告/文档中发布，因此仅第 9H、第 9I 和第 9J 阶段的完整提交 SHA 和 CI 运行是公开门控引用。本地同树 git 提交不被读取或比较；提供的确认值仅与冻结的公开门控常量匹配。在第 9K 阶段协议下的未来执行需要第 9K 阶段提交和 CI 通过。

第 9K 阶段记录第 9J 阶段标注输入行仅为路由/前置条件元数据，不是基准真值。第 9K 阶段记录第 9H 阶段仅为源物化就绪，并非任何标注、结果、evidence_success、评分或评估有效的证明。第 9K 阶段不读取任何私有清单或标注输入行。

## 冻结的未来结果获取包模式

冻结的未来结果获取包模式仅要求以下字段（仅为路由/前置条件元数据，不是基准真值）：

- 任务资格路由/前置条件仅
- 证据定位要求
- 预期证据形式
- 结果获取前置条件
- 标注输入元数据引用

私有字段仅保留在被忽略的 `runs/` 下。仅允许公开聚合分桶；无确切计数。缺失结果作为不可用处理，而非失败或成功。无效结果在评分前以替换方式拒绝。不可用结果仅记录在聚合不可用分桶中。

## 冻结的未来评分协议

冻结的未来评分协议要求：

- 评分指标和分母在结果可见性前冻结。
- 包含/排除规则在结果可见性前冻结。
- 失败分桶预先声明，仅聚合。
- 结果可见性后无阈值或指标调整。
- 除预先声明的聚合分桶外无事后子组挖掘。
- 第 9K 阶段无评分执行。
- 未来评分需要在结果获取后的单独冻结边界。
- 仅聚合公开报告；无私有评分细节。

预先声明的失败分桶：结果不可用失败、结果无效失败、包含失败、指标/分母失败。

## 冻结的未来裁定协议

冻结的未来裁定协议要求：

- 裁定独立性要求；评分者彼此盲评。
- 如果使用人工标注，最低评分者数量至少为三。
- 分歧类别在裁定前预先声明。
- 平局打破流程在裁定前预先声明。
- 独立结果先获取，裁定在后。
- 裁定规则不是裁定真值。
- 第 9K 阶段无裁定执行。
- 未来裁定需要在评分后的单独冻结边界。
- 仅聚合公开报告；无私有裁定细节。

分歧类别：完全一致、部分分歧、完全分歧、平局需要裁定。

## 真值边界

第 9K 阶段明确真值边界：

- 标注输入元数据仅为路由/前置条件，不是基准真值。
- 资格不等于正确性。
- 预期证据形式不等于金标准证据。
- 结果前置条件不等于结果。
- 裁定规则不等于裁定真值。

## 从第 9H 阶段继承的聚合上限/分桶

冻结的协议精确继承第 9H 阶段的聚合上限/分桶：

- 目标清单分桶：48-72
- 硬上限分桶：最多 96
- 每源上限分桶：最多 8
- 最少不同源分桶：至少 8

## 未来私有输入/输出位置

未来私有输入/输出（第 9H 阶段私有物化清单、第 9J 阶段私有标注输入行、未来结果获取行、未来评分行、未来裁定行）仅保留在被忽略的 `runs/` 下。第 9K 阶段不读取它们。未来第 9L 阶段仅在第 9K 阶段提交和 CI 通过以及明确确认后才可读取第 9J 阶段私有标注输入行。

## 未来第 9L 阶段门控条件

未来第 9L 阶段执行需要以下全部条件：

- 确认第 9K 阶段提交和 CI 通过
- 确认第 9H、第 9I、第 9J 阶段提交和 CI
- 确认第 9K 阶段协议冻结
- 确认读取第 9J 阶段私有标注输入行
- 确认被忽略的 runs 工作空间
- 确认仅私有输出
- 确认在单独边界前无评分/evidence_success
- 确认无提供者/LLM/模型/默认/运行时变更
- 确认仅聚合公开报告

第 9L 阶段仅在第 9K 阶段提交和 CI 通过后才可读取第 9J 阶段私有标注输入行。未来门控需要第 9K 阶段提交+CI 通过和明确确认/边界，而非用户批准。考虑第 9L 阶段仅结果获取，如果复杂性需要则稍后第 9M 阶段评分/裁定。

## 无声明边界

第 9K 阶段不做出任何方法、产品、性能、训练、提供者、模型、运行时、默认、评分、结果、evidence-success 或标注真值声明。冻结的协议仅聚合分桶。公开输出排除仓库名、源名、URL、所有者、提交（白名单的第 9H/9I/9J 门控常量除外）、哈希、路径、代码片段、任务 ID、行 ID、清单位置、运行位置、每源事实、每任务事实和单例分桶。第 9K 阶段不暗示标注、结果获取、evidence_success、评分、裁定或任何证据获取方法有效；第 9H 阶段源物化就绪不是标注、结果、evidence_success 或评分成功的证明。第 9K 阶段不是执行，不是证据/方法/产品成功。

保守建议为: `future_outcome_acquisition_scoring_adjudication_require_separate_frozen_boundary_phase9l_requires_phase9k_commit_ci_green_and_explicit_confirmations_boundary_no_user_approval_no_evidence_success_no_method_product_claim`。
