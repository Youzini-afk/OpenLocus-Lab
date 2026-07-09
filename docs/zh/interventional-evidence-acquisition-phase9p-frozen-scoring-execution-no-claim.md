# Interventional Evidence Acquisition Phase 9P 冻结评分执行（无声明）

日期：2026-07-09

状态：`phase9p_frozen_scoring_executed_denominator_nonzero_scored_nonzero_adjudication_not_executed_separate_frozen_boundary_required_no_evidence_success_no_claim`

授权：精确执行冻结的 Phase 9O 评分/分母/裁决协议，附带全部显式确认；仅在被忽略的 `runs/` 下读取 Phase 9N 私有 outcome-observable 数据包（仅获取状态 + 路由前置元数据，不含代码片段/observables/源内容）；应用冻结的分母资格判定与纳入/排除规则；仅发布分桶聚合评分桶；不执行裁决，不计算 correctness，不计算 evidence_success，不作任何声明

公开报告：[`phase9p_frozen_scoring_execution_no_claim_report.json`](../../artifacts/phase9p_frozen_scoring_execution_no_claim/phase9p_frozen_scoring_execution_no_claim_report.json)

## 范围

Phase 9P 仅执行冻结的 Phase 9O 评分协议。在全部显式确认下，它仅在被忽略的 `runs/` 下读取 Phase 9N 私有 outcome-observable 数据包（数据包仅携带获取状态与路由前置元数据，不含代码片段、不含 observables、不含源内容），应用冻结的 Phase 9O 分母资格判定，应用冻结的纳入/排除规则，并以分桶聚合方式计算冻结的评分指标桶。

它不执行裁决：冻结的 Phase 9O 裁决规则 `future_adjudication_requires_separate_frozen_boundary_after_scoring` 要求在评分之后设立一个独立的未来冻结边界，而该边界在 Phase 9P 中不存在。它不计算 correctness、evidence_success、gold/benchmark 标签、result 标签或 annotation-truth。它不读取 Phase 9H 私有 materialized 源、Phase 9J 私有 annotation-input 行或 Phase 9L 私有 outcome 数据包。它不将 Phase 9J 行作为 benchmark 真值（Phase 9N 数据包仅携带获取状态，不是 benchmark 真值）。它不对 Phase 9L unavailable 数据包评分。它不执行 provider/LLM/model 裁决、模型拟合/训练、网络 fetch/clone/source 刷新或 runtime/default/product 变更。

此处的“评分”仅是将获取可用性分桶为聚合桶——不是 correctness 评分，不是 evidence_success，不是 pass/fail，不是 method/product/performance 成功。私有评分行仅写入被忽略的 `runs/` 下。公开报告仅发布分桶聚合：不含精确计数/比率，不含 id/observable/代码片段/路径/源身份/run 目录/singleton 桶。

## 门禁引用

Phase 9P 的门禁基于 Phase 9O 远程提交 `fa812361e1a121b7c3c8e6d2a540d4916975d090`、CI run `28986131071`、CI 成功、Phase 9O 状态 `phase9o_scoring_denominator_adjudication_protocol_freeze_no_execution_no_private_read_no_scoring_no_claim` 以及 Phase 9O 协议冻结；并基于 Phase 9N 远程提交 `282a5037a106da55b6df67a33c42bb3ad7142836`、CI run `28985320043`、CI 成功、Phase 9N 状态 `phase9n_frozen_route_executed_valid_acquired_nonzero_aggregate_availability_no_scoring_no_adjudication_no_claim` 以及 Phase 9N 公开事实 `acquired_valid_bucket` = `bucket_nonzero_redacted`（允许考虑 Phase 9P 评分的非零可用性门禁）。Phase 9M、Phase 9L、Phase 9K、Phase 9H、Phase 9I、Phase 9J、Phase 9G 与 Phase 9F 仅作为分桶继承来源携带，其精确远程提交/CI run 值有意不在 Phase 9P 报告/文档中发布（更严格的隐私）。本地同树 git 提交不被读取或比较；所提供的确认值仅与冻结的公开门禁常量匹配。

## 精确应用的冻结协议

冻结的 Phase 9O 协议闭列表（分母资格判定、纳入/排除规则、评分指标定义、裁决规则、缺失/无效/unavailable 处理、隐私/发布、未来 Phase 9P 门禁、防 p-hacking 护栏）直接从已提交的 Phase 9O 协议冻结模块加载，因此 Phase 9P 精确应用冻结协议——不重新声明、不漂移。不引入新指标、阈值或子组；outcome 可见后不编辑协议；私有读取后不修复分母。

- **分母资格：** 分母是满足预冻结判定谓词的 Phase 9N 私有数据包集合（由 Phase 9N 受控 run 期间单一 Phase 9M 冻结路由生成；获取状态为 acquired；有效性状态为 valid；expected evidence form 匹配白名单；source-grounding 检查通过；数据包 schema 校验通过；非 unavailable/invalid/replacement-needed/malformed/duplicate/outside route/cap/order）。
- **纳入/排除：** 仅纳入合格的 valid acquired 数据包；在评分前排除 unavailable、invalid、replacement-needed、schema-invalid、duplicate 与 out-of-route/cap/order 数据包。unavailable 排除映射到 `unavailable_excluded_bucket`；所有其他排除映射到 `invalid_excluded_bucket`。
- **评分指标桶（仅聚合）：** `denominator_bucket`、`scored_bucket`、`adjudicated_bucket`、`invalid_excluded_bucket`、`unavailable_excluded_bucket`、`correctness_bucket`——精确为冻结的 Phase 9O 评分指标定义，作为分桶聚合应用。无精确计数/比率，无 winner/effect/lift 语言。
- **裁决：** 在 Phase 9P 中不执行。冻结规则 `future_adjudication_requires_separate_frozen_boundary_after_scoring` 要求在评分后设立独立未来冻结边界，而此处不存在。`adjudicated_bucket` = `bucket_zero`；`correctness_bucket` = `bucket_zero`。
- **缺失/无效/unavailable 处理：** 非 failure/success/partial；在评分前排除；仅分桶聚合。
- **隐私/发布边界：** 仅公开桶；无精确计数/observable/路径/代码片段/行范围/源/任务/行/数据包 ID/run 位置；无 singleton 桶。

所有闭列表由校验器针对 Phase 9O 冻结常量进行集合相等性校验。词汇漂移（缺失/多余/改写成员）被拒绝。

## 执行结果

在全部显式确认下，Phase 9P 读取了被忽略 `runs/` 下的 Phase 9N 私有 outcome-observable 数据包，精确应用了冻结的 Phase 9O 评分协议，并发布了分桶聚合报告。公开桶为：`denominator_bucket` = `bucket_nonzero_redacted`、`scored_bucket` = `bucket_nonzero_redacted`、`adjudicated_bucket` = `bucket_zero`、`invalid_excluded_bucket` = `bucket_zero`、`unavailable_excluded_bucket` = `bucket_zero`、`correctness_bucket` = `bucket_zero`。分母非零，因此未走失败/修复路径。裁决与 correctness 未执行（需要独立的未来冻结边界）。私有评分行仅在被忽略的 `runs/` 下。

## 失败行为

若 Phase 9O 或 Phase 9N 门禁缺失/未通过、Phase 9N 数据包缺失/不可读/schema 无效、分母为零，或评分无法按冻结协议精确应用，Phase 9P 以修复/无声明公开报告停止，并在被忽略的 `runs/` 下记录私有停止原因；读取数据后不更改协议。

## 无声明边界

Phase 9P 不作任何 method、product、performance、training、provider、model、runtime、default、scoring-success、outcome、evidence-success、annotation-truth、adjudication 或 correctness 声明。冻结评分执行仅是分桶聚合的可用性到评分映射——不是 evidence/method/product 成功，不是 correctness，不是裁决真值。correctness 与裁决仍为未来定义，需要在评分后设立独立冻结边界。

保守建议为：`phase9p_executes_frozen_scoring_bucketing_only_denominator_nonzero_adjudication_not_executed_requires_separate_frozen_boundary_after_scoring_no_evidence_success_no_correctness_no_method_product_claim`。
