# P51-B LLM 按需调用合约 / 干跑载荷校验器

- Schema: `p51b-llm-opt-in-contract-v1`
- 生成时间: （由运行时填充）
- 状态: 详见报告
- 自测: 是/否
- P51-B 远程调用: 0
- P51-B LLM 调用: 0
- P51-B 提供商请求: 0
- P51-B 是否构造提示词: 否
- 仅干跑载荷校验: 是
- P51-B 实时调用已禁用: 是

## 目的

P51-B 定义了一份未来的 LLM 按需调用合约，并对干跑载荷模式进行校验。它不会调用任何模型或远程服务，不会构造提示词，也不会持久化原始请求、输出、片段或响应。

## 方法

- 加载 ephemeral P25 策略记录（或确定性自测记录）。
- 使用 P46/P49 归一化函数处理候选；仅使用公开元数据和 P51 确定性过滤来决定候选资格，不使用 gold 或评测结果。
- 仅以枚举/状态形式消费上游聚合报告（P51/P52C/P49/P52B/P52A/P52/P50/P48）。
- 从合格候选构建请求信封蓝图元数据：候选数量、行/字符预算、未来上限冲突等；不构造任何提示字符串。
- 在内存中对合成角色输出模式进行失败安全校验（要求 `not_evidence=true`、角色属于枚举、拒绝未知字段、候选引用与行列增量在限定范围内）。
- 输出聚合就绪诊断与仅含未来上限的合约清单；不发布 provider、model、URL 或 API key。

## 安全说明

- P51-B 不调用 LLM，也不调用任何远程 provider。
- P51-B 不构造提示词。
- P51-B 不存储原始请求信封、提示词、输出、响应、片段、源文本、查询、路径、区间或摘要。
- P51-B 不发布 provider、model、base URL 或 API key。
- P51-B 输出不是 Evidence，不是质量证据，不代表实时就绪，也不主张默认/推广。
- 角色输出模式校验仅使用内存中的合成固定装置。

## 合约清单

- 合约 schema 版本: `p51b-llm-opt-in-contract-v1`
- 支持角色: span_narrow、filter、abstain
- 支持输出模式: json_object、json_schema_strict、tool_call
- 实时调用通道可用性: `disabled_p51b`
- 允许的远程模式: `future_remote_opt_in_only`
- 未来上限: max_provider_calls_future_cap=1、max_candidates_per_request=6、max_lines_per_candidate=120、max_total_lines_per_request=360、max_request_chars_future_cap=16000、max_output_chars_future_cap=4000、timeout_seconds_future_cap=60、retry_policy_future_cap={max_retries: 1, retry_on_schema_error: true}、schema_repair_retry_future_cap=1

## 资格

- 候选分母、合格候选数/率、合格包数/率
- 按角色聚合合格数: span_narrow、filter、abstain
- 不合格原因计数/率
- 资格可用性枚举: available_source_backed | partial_metadata_only | unavailable_missing_candidate_pool | unavailable_missing_upstream_contract
- source_backed_live_eligibility_available: 布尔值

## 请求信封蓝图

- request_envelope_blueprint_count
- mean/p95 candidates_per_envelope、line_budget、context_char_budget
- max_budget_violation_count/rate
- redaction_required_count/rate（基于源支持不可用或路径类型风险的聚合启发式，不基于原始文本）
- secret_scan_availability: `aggregate_metadata_only`
- request_envelope_not_prompt: true
- raw_request_envelopes_stored: false

## 角色输出模式校验

- role_output_schema_self_test_count
- role_output_schema_valid_count/rate = 1.0（所有合法样例均通过）
- role_output_schema_invalid_reject_count/rate > 0（非法样例被拒绝）
- unknown_field、not_evidence_missing、line_delta_out_of_bounds、candidate_ref_out_of_bounds 拒绝计数

## 未来实时门控就绪

- p51b_live_gate_ready: true/false
- p51b_live_gate_ready_reason: contract_valid_dry_run_only | missing_candidate_pool | no_eligible_envelopes | schema_validation_failed

## 结论

- 这只是一份干跑合约，不是 Evidence，不是质量证据，不做实时调用，不构造提示词，不存储原始载荷，不主张默认或推广策略变更。
