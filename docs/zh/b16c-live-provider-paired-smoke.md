# B16-C Live-Provider 下游 Paired Smoke（公开仅聚合 artifact）

> 本中文文档与英文文档 `docs/en/b16c-live-provider-paired-smoke.md` 一一对应。

## 范围与声明边界

B16-C 是**首个使用 live LLM provider**（OpenAI 兼容）的 B16 风格下游
agent 实证 run，在合成公开 micro bug 任务上运行。它在本地应用模型的
结构化 edit action，运行真实 stdlib 测试，并仅发布聚合行为指标。

B16-C 明确**不是**下游 agent 价值证明，**不是** live agent 泛化证明，
**不是**生产级 coding-agent 基准测试，**不是**真实用户任务评估，**不
是**外部基准测试评估，也**不是** promotion/default-policy/runtime/
retriever/pack/backend/EvidenceCore 语义改动。它**不**发布 prompt、
response、provider payload、base URL、API key、raw model 路由前缀、
工作区路径、文件路径、源码片段、patch/diff、测试输出、raw event log
或 per-run 行。

- 声明级别（claim_level）：`live_provider_downstream_paired_smoke_only`。
- 模式（mode）：`public_aggregate_synthetic_micro_tasks`；阶段
  （phase）为 `B16-C`。
- 状态枚举：成功时为 `live_provider_paired_smoke_pass`；无本地
  provider env 时为 `unavailable_no_local_provider_env`；未启用远程
  时为 `blocked_remote_not_enabled`；provider 调用失败时为
  `provider_call_failed`；结构化 action 解析失败时为
  `structured_action_parse_failed`；paired run 无法完成时为
  `paired_run_failed`；scanner 失败时为 `fail_forbidden_scan`。
- B16-C 是 **eval/诊断专用**。它**不是**基准测试结果，**不是**下游
  agent 价值声明，**不是** runtime-clean 通用算法声明，**不是** OOD
  时间性声明，也**不是** QuIVer 系统声明。

### B16-A / B16-B -> B16-C 关系

```text
B16-A 最小确定性/mock 下游 paired run（无 live LLM）
-> B16-B less-separable 确定性/mock paired stress（无 live LLM）
-> B16-C live-provider 下游 paired smoke（live LLM，真实 provider）
   （合成公开 micro 任务；每个 task+arm 全新 /tmp 工作区；
    真实文件编辑 + 真实子进程测试；仅当 --allow-remote +
    OPENLOCUS_ALLOW_REMOTE=1 + env 时启用 live LLM provider；
    不提交 raw prompt/response/payload）
```

B16-C **不是** B16。完整 B16 下游 coding-agent 评估阶段仍是需要真实
基准测试任务上 live paired agent run 的有界规划/可行性阶段。B16-C 仅通
过在合成公开 micro 任务上运行微型 paired live LLM agent，产出首个
live-provider 下游 smoke。

## 已提交 artifact vs 手动 CI live-provider 结果

**已提交 artifact** 位于
`artifacts/b16c_live_provider_paired_smoke/b16c_live_provider_paired_smoke_report.json`，
是**真实的本地报告**。若本地 provider env 不可用（默认状态），其状态
为 `unavailable_no_local_provider_env` 或
`blocked_remote_not_enabled`，所有 live-run 标志为 false（除
`aggregate_only_public_artifact=true` 和 `diagnostic_only=true`）。
只有显式本地 opt-in run（`--allow-remote` +
`OPENLOCUS_ALLOW_REMOTE=1` + provider env）或手动 CI
`real-provider-benchmark` workflow（`stage=
b16c_live_provider_paired_smoke` + `enable_remote_models=true`）才会
产出 live `live_provider_paired_smoke_pass` artifact。

**手动 CI live-provider run：待执行。** 截至本提交，尚未触发针对
`b16c_live_provider_paired_smoke` 的手动 CI
`real-provider-benchmark` run。触发后，CI 报告将上传为
`artifacts/real_provider_ci/b16c_live_provider_paired_smoke_report.json`，
docs 将更新以反映 CI run 结果。

## 合成公开 micro bug 任务设计

B16-C 在代码中生成确定性合成公开 micro bug 任务规格（默认 2 个；
`--task-count` 范围 2-8，硬上限 8）。每个任务规格描述一个微型 Python
模块，含一行 bug（返回错误值）及一个断言正确值的 stdlib 测试。修复是
确定性的一行返回值替换。

对每个任务和 arm，B16-C 创建一个全新 `/tmp` 工作区，含 `target.py`
（buggy）、`distractor.py`（错误文件 distractor）、`test_target.py`
（stdlib 测试）。所有工作区文件都是写到 `/tmp` 下的真实 Python 文件。
harness 真实编辑文件并运行子进程测试。

## Paired arm 设计

B16-C 运行 paired `control_sparse` vs `treatment_context_pack` arms，
预算/工具约束相同；仅 context pack 不同。

- **control_sparse**：最小描述；无 target file cue；小 token 预算。
- **treatment_context_pack**：更丰富的 evidence pack，含 target file
  cue、symbol cue 及紧凑文件摘要；较大 token 预算。

treatment pack 旨在为 live LLM 提供更多关于 target file/symbol 的上
下文。这是因果 pack 效果 smoke，**不是** live agent 价值声明。

## Live LLM provider 约束

- Env vars：
  - `OPENLOCUS_LLM_BASE_URL`
  - `OPENLOCUS_LLM_API_KEY`
  - `OPENLOCUS_LLM_MODEL`
  - `OPENLOCUS_ALLOW_REMOTE=1`
  - `OPENLOCUS_LLM_WORKFLOW_DISPATCH=1`（当设置
    `--require-workflow-dispatch` 时用于 CI/手动 workflow run）。
- 仅当 `--allow-remote` AND `OPENLOCUS_ALLOW_REMOTE=1` AND（当
  `--require-workflow-dispatch` 时）`OPENLOCUS_LLM_WORKFLOW_DISPATCH=1`
  AND `OPENLOCUS_LLM_BASE_URL` / `OPENLOCUS_LLM_API_KEY` /
  `OPENLOCUS_LLM_MODEL` 全部设置时才进行远程调用。
- artifact/docs 中无 raw base URL、API key、prompt、response、源码片
  段、patch/diff、stdout/stderr、工作区路径或 provider payload。
- live LLM prompt 仅在 treatment pack 携带时包含微型合成/公开源码片
  段（buggy target 模块）和紧凑文件摘要。prompt **绝不**持久化。
- 结构化 edit action schema 为白名单：action 必须为
  `replace_return_value` 或 `no_op`；file 必须为 `target.py`；无任意
  路径，无 shell。
- 若 provider 返回 `usage`，usage 诊断可包含聚合
  prompt/completion/total token 计数；否则标记不可用。
- cost 仅为 `cost_proxy`（恒为 0.0）；无 live 价格推断。
- 研究 docs/artifacts 记录规范化 model 显示名，不带 provider routing
  prefix（例如 `Kimi-K2.7-Code`），除非记录确切的 workflow/env 白名单。

## CLI

```bash
python3 -m py_compile eval/provider_client.py eval/b16c_live_provider_paired_smoke.py
python3 eval/provider_client.py --self-test
python3 eval/b16c_live_provider_paired_smoke.py --self-test
python3 eval/b16c_live_provider_paired_smoke.py \
    --out artifacts/b16c_live_provider_paired_smoke/\
b16c_live_provider_paired_smoke_report.json
# Live opt-in（仅当 provider env 可用且安全时）：
OPENLOCUS_ALLOW_REMOTE=1 OPENLOCUS_LLM_WORKFLOW_DISPATCH=1 \
    python3 eval/b16c_live_provider_paired_smoke.py \
    --allow-remote --task-count 2 \
    --out artifacts/b16c_live_provider_paired_smoke/\
b16c_live_provider_paired_smoke_report.json
```

默认模式（无 `--allow-remote` 或无 provider env）：若提供 `--out`，则
写入真实的 `unavailable_no_local_provider_env` 或
`blocked_remote_not_enabled` 聚合报告；无 provider 调用；live-run 标
志为 false（除 `aggregate_only_public_artifact=true` 和
`diagnostic_only=true`）。

CLI 参数：`--self-test`、`--out`、`--allow-remote`、
`--require-workflow-dispatch`、`--task-count`。未知/私有外观参数被以通
用 `invalid arguments` 消息拒绝，不回显私有路径或基名
（SafeArgumentParser 模式）。

`--self-test` 使用 fake provider response 运行无网络 self-test；覆盖
remote gating、missing env unavailable 路径、provider 诊断 redaction、
fake valid edit apply/test、invalid JSON count、固定 provider 错误类
别、action path/action 限制、真实 edit+test 执行、scanner forbidden
keys/values、no-claim flags 及 fail-closed scanner 行为。

## Provider client helper

`eval/provider_client.py` 是 B16-C 使用的最小 OpenAI 兼容 chat
helper。它返回安全的 `ProviderCallResult` 对象，仅暴露聚合计数
（calls attempted/succeeded/failed、invalid_json、timeout、latency、
若 provider 返回 `usage` 的数值 usage、固定 failure-category 枚举
token、HTTP status）。raw prompt、message、response、base URL、
API key 及 provider payload **绝不**在公开诊断中返回。安全失败类别是
固定枚举；raw 异常文本被抑制。

## Artifact 身份（默认提交 artifact）

提交的 artifact 位于
`artifacts/b16c_live_provider_paired_smoke/b16c_live_provider_paired_smoke_report.json`，
是公开仅聚合 smoke artifact。身份/边界字段：

- `schema_version` = `b16c_live_provider_paired_smoke.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`、`model_display_category`（规范化；无 provider routing prefix）。
- Safe true flags（仅 live run 时；仅这些，全为 true）：
  `downstream_agent_runs_performed`、`live_llm_agent`、
  `provider_calls_made`、`remote_provider_calls_made`、
  `paired_run_executed`、`synthetic_micro_tasks_used`、
  `real_file_edits_performed`、`real_test_commands_executed`、
  `agent_behavior_metrics_evaluated`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- unavailable/blocked 状态下，live-run 标志为 false（除
  `aggregate_only_public_artifact=true` 和 `diagnostic_only=true`；
  `synthetic_micro_tasks_used=false` 因无 run）。
- Always-false no-claim flags：
  `downstream_agent_value_proven`、
  `live_agent_generalization_claimed`、`promotion_ready`、
  `default_should_change`、
  `external_benchmark_performance_claimed`、`real_user_task_claimed`、
  `runtime_behavior_changed`、`retriever_changed`、
  `pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`。
- `input_summary`：`synthetic_task_count`、`run_count_per_arm`、
  `total_runs`、`arms`（`[control_sparse, treatment_context_pack]`）、
  `paired_design`（`true`）、`workspace_isolation`
  （`fresh_tmp_per_task_arm`）、`transient_workspace_outputs_only`
  （`true`）、`designed_causal_subset`（`true`）。
- `arm_results`：固定记录列表
  `{arm, metrics, provider_summary, failure_category_counts}`。
- `paired_deltas`：固定记录列表
  `{baseline_arm, treatment_arm, metric, delta}`。
- `self_test_summary` + `self_test_checks` + `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

## 聚合指标

per-arm 聚合指标（records-shaped；无 per-run 行）：

- `run_count`、`solve_rate`、`tests_pass_rate`、
  `correct_file_before_first_edit_rate`、`wrong_file_edits_mean`、
  `tool_calls_before_first_edit_mean`、`context_tokens_mean`、
  `latency_ms_mean`、`cost_proxy_mean`（恒为 0.0）。

`provider_summary`（per-arm 聚合）：`calls_attempted`、
`calls_succeeded`、`calls_failed`、`invalid_json_count`、
`timeout_count`、`failure_category_counts`（仅固定枚举 token）、
`usage_available`、`prompt_tokens_total`、
`completion_tokens_total`、`total_tokens_total`、`latency_ms_total`。

`paired_deltas`：treatment-minus-control delta 作为固定记录
`{baseline_arm, treatment_arm, metric, delta}`（不含 `run_count`，
paired 设计下两者相同）。

## Forbidden scanner（公开，fail-closed）

严格 forbidden 输出 scanner 在写入公开 JSON 前 fail-closed 运行。拒绝
forbidden dict key 在任何位置出现（`prompt`、`prompts`、`message`、
`messages`、`response`、`responses`、`raw_response`、`request`、
`request_body`、`provider_payload`、`url`、`base_url`、`endpoint`、
`api_key`、`token`、`secret`、`authorization`、`bearer`、`workspace`、
`workspace_path`、`path`、`file`、`target_file`、`target_module`、
`distractor_module`、`test_module`、`snippet`、`code`、`source`、
`patch`、`diff`、`test_output`、`stdout`、`stderr`、`event_log`、
`stack_trace`、`content_sha`、`task_id`、`per_run`、`model_id_raw`、
`model_id` 等）及 value 模式：任意 URL（无 URL 允许列表）、32+ 字符
hex digest、secret-like 字符串、带文件扩展名的 path-like 字符串、
`/tmp/` 工作区路径 value、`task_N` 任务标识 value、patch/diff 标记、
堆栈跟踪、多行字符串、raw JSON 片段、raw 行范围、raw model routing
prefix 及 self-test sentinel。

scanner 仅对最终公开聚合 artifact 运行。内部 per-run event log（含路
径/patch/测试 stdout/stderr）仅保留在内存中，绝不对公开契约扫描，绝
不提交。

## Self-tests

- Artifact 身份字段（schema、claim、status 枚举、mode、phase、
  generated_by）。
- Always-false no-claim flags（12 个全为 false）。
- Live-run flag gating（unavailable report：live-run flags false；
  live report：live-run flags true）。
- 合成任务生成（确定性计数、符号、正确值）。
- Pack builder（control_sparse vs treatment_context_pack 差异；
  treatment 比 control 更丰富）。
- 真实工作区 + 真实编辑 + 真实测试（fake valid provider response）：
  修复前测试失败；fake valid edit 应用正确文件；测试通过；solve=true；
  真实文件编辑已应用；provider call 摘要反映成功。
- Fake invalid JSON response（parse failure）：无编辑；测试失败；run
  result 中无 raw response。
- Edit action 限制：disallowed file 被拒；disallowed action 被拒；
  missing symbol 被拒；non-int new_return_value 被拒；non-object 被
  拒；valid action 被接受；no_op action 被接受。
- 聚合指标 + delta（records-shaped；不含 run_count）。
- Model display 规范化（剥离 provider routing prefix；空返回 `unavailable`；剥离
  不安全字符）。
- scanner 拒绝：工作区路径、文件路径、源码片段、patch 标记、测试输
  出、task_id key、raw event log、堆栈跟踪、content_sha key、hex
  digest、provider auth field、endpoint URL field、raw model routing
  prefix、URL value、prompt key、response key、messages key、
  provider_payload key、sentinel canary。
- scanner 允许：arm 名称、metric 记录、model display category、
  failure category token。
- fail-closed 生成：干净公开 report 不 raise；泄漏公开 report raise
  SystemExit；self-test 失败拒绝生成 artifact。
- 公开 artifact 自扫描干净（无任何 forbidden key）。
- CLI 参数面：`--self-test`、`--out`、`--allow-remote`、
  `--require-workflow-dispatch`、`--task-count` 是仅有的选项（加上
  `-h`/`--help`）；默认任务数在范围内。
- remote gating：`allow_remote=False` 时 blocked；env 缺失时
  unavailable；`provider_client._check_remote_enabled` 枚举 token。
- Env restoration regression：self-test 会精确恢复 provider env，避免在
  live CI provider call 前清掉 live gate。

## 验证

```text
python3 -m py_compile eval/provider_client.py eval/b16c_live_provider_paired_smoke.py  => PASS
python3 eval/provider_client.py --self-test                            => PASS (33/33 checks)
python3 eval/b16c_live_provider_paired_smoke.py --self-test            => PASS (119/119 checks)
python3 eval/b16c_live_provider_paired_smoke.py \
  --out artifacts/b16c_live_provider_paired_smoke/\
b16c_live_provider_paired_smoke_report.json                           => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_micro_tasks, phase: B16-C,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   default_should_change: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false, real_user_task_claimed: false)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

提交的 artifact 是真实的本地 unavailable/blocked 报告，因为本地无
provider env。live `live_provider_paired_smoke_pass` artifact 需要显式
本地 opt-in run 或手动 CI `real-provider-benchmark` workflow
（`stage=b16c_live_provider_paired_smoke` +
`enable_remote_models=true`）。**手动 CI live-provider run：待执行。**

## 注意事项

- B16-C 是公开仅聚合 live-provider 下游 paired smoke artifact。它是
  eval/诊断专用。它**不**改变 runtime、retriever、pack、backend 或
  default policy；它**不**改变 EvidenceCore 语义。它**不是**基准测试
  结果，**不是**下游 agent 价值声明，**不是** runtime-clean 通用算法
  声明，**不是** OOD 时间性声明，也**不是** QuIVer 系统声明。
- B16-C 仅在 `--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider
  env 全部设置时使用 **live LLM provider**（OpenAI 兼容）。提交的
  artifact 是真实的：若本地无 provider env，其状态为
  `blocked_remote_not_enabled` /
  `unavailable_no_local_provider_env`，live-run 标志为 false。它**不
  是** fake pass。
- B16-C **不**证明下游 agent 价值。treatment-vs-control delta（当
  live run 完成时）是 smoke 信号，**不是** treatment pack 改善 live
  下游 agent 的证据。`downstream_agent_value_proven=false`。
- B16-C **不**声明 live agent 泛化。微型合成公开 micro 任务族按构造
  平凡；这**不是** live agent 泛化声明。
  `live_agent_generalization_claimed=false`。
- B16-C **不**发布 prompt、response、provider payload、base URL、
  API key、raw model 路由前缀、工作区路径、文件路径、源码片段、
  patch/diff、测试输出、raw event log 或 per-run 行。per-run event
  log、prompt、response 和测试输出仅留在 `/tmp`，**绝不**提交或上
  传。
- 提交的 artifact 仅含 records-shaped 容器中的聚合
  counts/rates/means。不发布 raw model 路由前缀；仅记录规范化的
  `model_display_category`。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  live-run 标志**仅**在 live run 实际执行时为 true。
- 未修改任何 runtime/retriever/pack/model/backend/default-policy 文
  件。无 promotion/default/runtime 声明变更。
