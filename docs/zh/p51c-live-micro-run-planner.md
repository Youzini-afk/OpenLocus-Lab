# P51-C0 实时 LLM 微运行规划器 / 显式选择加入门禁

- Schema: `p51c-live-micro-run-planner-v0`
- 生成时间: （由运行时填充）
- 状态: 详见报告
- 自测: 是/否
- 仅规划器: 是
- P51-C 实时调用已禁用: 是
- P51-C 远程调用: 0
- P51-C LLM 调用: 0
- P51-C 提供商请求: 0
- P51-C 是否构造提示词: 否
- 提供商花费授权标志: 否
- 实时运行授权标志: 否

## 目的

P51-C0 是一个仅作规划用途的显式选择加入门禁。它用于校验未来是否可以手动启动 P51-C 实时 LLM 微运行，但本身不会调用任何模型或远程服务，不会构造提示词，不会读取源码，不会接纳 Evidence，也不会授权花费。

## 方法

- 要求显式传入 `--p51c-live-opt-in` 和匹配的 `--ack-not-evidence` 字符串。
- 仅读取上游聚合报告（`--p61-report`、`--p51b-report`）。
- 确认 P61 状态为 `micro_run_preconditions_met`，且未授权提供商花费、该决定不是授权、并要求单独的人工或 workflow_dispatch 决定。
- 确认 P51-B 合约就绪、源码支持的候选资格、角色输出模式有效、以及 redaction 前置条件已满足。
- 校验请求的预算上限不超过 P51-B 干跑合约上限，且计划调用次数恰好为 1。
- 确认输出模式为 `json_schema_strict` 或 `tool_call`，数据集和仓库在允许列表内。
- 仅输出聚合规划配置，使用 `repo_scope='public_ci_smoke_allowlist'`，不暴露原始仓库身份、路径、区间、提示词、响应、提供商、模型或密钥。

## 安全说明

- P51-C0 不调用 LLM，也不调用任何远程 provider。
- P51-C0 不构造提示词，不读取源文件，不访问 ephemeral 记录。
- P51-C0 不发布任务 ID、候选 ID、仓库 ID、路径、区间、行范围、摘要、查询、片段、提示词、响应、provider、model、URL 或 API key。
- P51-C0 输出仅为聚合信息，并明确标注为不是质量证据、不是授权、不是 Evidence、不是默认/推广/实时就绪。

## 输入摘要

- P61 报告是否提供、状态、前置条件是否满足
- P51-B 报告是否提供、状态、`p51b_live_gate_ready` 标志、合格候选数、合格包数、蓝图数、源码支持资格、模式有效率、redaction 前置条件与一致性

## 门禁检查结果

- 显式 opt-in 是否存在
- ack 字符串是否与 `I_UNDERSTAND_P51C_NOT_EVIDENCE` 匹配
- 数据集是否在允许列表 (`self_test` | `ci_smoke`)
- 仓库是否在允许列表 (`py_flask` | `js_express` | `go_gin` | `rust_ripgrep`)
- 输出模式是否允许 (`json_schema_strict` | `tool_call`)
- P61 前置条件是否满足
- P51-B 合约是否就绪
- 预算上限是否被尊重

## 预算检查

- max_remote_calls_total 必须为 1
- max_request_chars <= 16000
- max_output_chars <= 4000
- max_candidates_per_request <= 6
- max_total_lines_per_request <= 360
- timeout_seconds <= 60

## 规划配置

- p51c_live_opt_in
- ack_not_evidence
- dataset
- repo_scope: `public_ci_smoke_allowlist`
- llm_output_mode
- 各项预算上限

## 结论

P51-C0 报告只是一种聚合前置条件信号。它不授权实时 LLM 花费，不修改默认策略，不推广任何策略，也不改变 EvidenceCore。真正的 P51-C 实时 LLM 微运行仍需要单独的人工或 workflow_dispatch 决定。
