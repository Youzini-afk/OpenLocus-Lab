# B16-E Broader Live-Provider 下游 Paired Smoke（公开仅聚合 artifact）

> 本中文文档与英文文档 `docs/en/b16e-broader-live-provider-paired-smoke.md`
> 一一对应。

## 范围与声明边界

B16-E 将 B16-D 从单一 less-trivial 合成 live-provider 任务族扩展为一个小型
异构合成**任务族矩阵**。目标是测试 context-pack treatment 信号是否能超越
B16-D 模板，同时保持阶段有界、仅聚合、手动 provider gating。

B16-E 使用四个固定白名单任务族，每个族有不同的决定性 cue，由 treatment pack
提供。在合成公开 micro bug 任务上使用 live LLM provider（OpenAI 兼容）；
本地应用模型的结构化 edit action；运行真实 stdlib 测试；仅发布聚合行为指
标。

B16-E 明确**不是**下游 agent 价值证明，**不是** live agent 泛化证明，**不
是**外部基准测试结果，**不是**生产级 coding-agent 基准测试，**不是**真
实用户任务评估，也**不是** promotion/default-policy/runtime/retriever/
pack/backend/EvidenceCore 语义改动。它**不**发布 prompt、response、
provider payload、base URL、API key、raw model 路由前缀、工作区路径、文
件路径、源码片段、patch/diff、测试输出、raw event log 或 per-run 行。

- 声明级别（claim_level）：
  `broader_live_provider_downstream_paired_smoke_only`。
- 模式（mode）：`public_aggregate_synthetic_task_family_matrix`；阶段
  （phase）为 `B16-E`。
- 状态枚举：成功时为
  `broader_live_provider_paired_smoke_pass`；未启用远程时为
  `blocked_remote_not_enabled` / `unavailable_no_local_provider_env`；
  provider 调用失败时为 `provider_call_failed`；结构化 action 解析失败
  时为 `structured_action_parse_failed`；paired run 无法完成时为
  `paired_run_failed`；scanner 失败时为 `fail_forbidden_scan`。
- B16-E 是 **eval/诊断专用**。它**不是**基准测试结果，**不是**下游
  agent 价值声明，**不是** runtime-clean 通用算法声明，**不是** OOD
  时间性声明，也**不是** QuIVer 系统声明。

### B16-D -> B16-E 关系

```text
B16-D less-trivial live-provider 下游 paired smoke
  （单一任务族；support relation；4 任务 / 8 调用）
-> B16-E broader live-provider 下游 paired smoke
   （四个任务族；异构决定性 cue；默认 8 任务 / 16 调用；
    相同的仅聚合安全模型；CI 通过不要求 treatment 改善）
```

B16-E **不是** B16。完整 B16 下游 coding-agent 评估阶段仍是有界规划/
可行性阶段。B16-E 仅通过在合成公开任务族矩阵上运行微型 paired live LLM
agent，产出更广的 live-provider 下游 smoke。

## 已提交 artifact vs 手动 CI live-provider 结果

**已提交 artifact** 位于
`artifacts/b16e_broader_live_provider_paired_smoke/b16e_broader_live_provider_paired_smoke_report.json`，
是**真实的本地报告**。若本地 provider env 不可用（默认状态），其状态
为 `blocked_remote_not_enabled` 或
`unavailable_no_local_provider_env`，所有 live-run 标志为 false（除
`aggregate_only_public_artifact=true` 和 `diagnostic_only=true`）。
只有显式本地 opt-in run（`--allow-remote` +
`OPENLOCUS_ALLOW_REMOTE=1` + provider env）或手动 CI
`real-provider-benchmark` workflow
（`stage=b16e_broader_live_provider_paired_smoke` +
`enable_remote_models=true`）才会产出 live
`broader_live_provider_paired_smoke_pass` artifact。

**手动 CI live-provider run：待执行。** 截至本提交，尚未触发针对
`b16e_broader_live_provider_paired_smoke` 的手动 CI
`real-provider-benchmark` run。触发后，CI 报告将上传为
`artifacts/real_provider_ci/b16e_broader_live_provider_paired_smoke_report.json`，
docs 将更新以反映 CI run 结果。未来的 live 结果可能为零、负或正 treatment
delta；不作价值/泛化/default 声明。

## 异构合成公开任务族矩阵设计

B16-E 在四个固定白名单任务族中生成确定性合成公开 micro bug 任务（默认 8
个；`--task-count` 范围 4-12，硬上限 12；默认 16 个 live 调用；最多 24
个 live 调用）。任务在四个族中循环以保持矩阵平衡。

### 任务族

每个族有不同的决定性 cue，由 treatment pack 提供：

1. **`same_symbol_support_relation`** — target/distractor 共享符号，
   support relation 决定正确编辑。正确值 =
   `helper_constant * 2 + task_index`。
2. **`operation_ambiguity`** — target 符号可推断但操作有歧义
   （increment vs multiply）。正确操作是 multiply；正确值 =
   `base_value * 2`。
3. **`boundary_condition`** — 正确编辑取决于 inclusive/exclusive 边界行
   为。正确值 = `limit_value - 1`（exclusive upper bound）。
4. **`helper_dependency_choice`** — 存在多个 helper，正确编辑需要选择
   正确的 helper 关系。正确值 = `helper_b * 3`（非 `helper_a * 2`）。

### 多文件工作区

对每个任务和 arm，B16-E 创建一个全新 `/tmp` 工作区，含四个真实 Python 文
件：

- `target.py`：buggy 函数（与 distractor 同符号）。
- `distractor.py`：同名 decoy 符号。
- `support.py`：定义决定性 cue 所需的 helper constant。
- `test_target.py`：导入 `target` AND `support`；断言正确的族特定关
  系。

harness 真实编辑文件并运行子进程测试。

## Paired arm 设计

B16-E 运行 paired `control_sparse` vs `treatment_context_pack` arms，
预算/工具约束相同；仅 context pack 不同。

- **control_sparse**：最小描述；无 target file cue；无决定性 cue；小
  token 预算。agent 无法在缺少决定性 cue 时确定正确值/操作。
- **treatment_context_pack**：target file cue、target symbol cue、族特
  定决定性 cue 及 exact edit constraint；较大 token 预算。

treatment pack 旨在为 live LLM 提供每个族确定正确值/操作所需的决定性
cue。这是因果 pack 效果 smoke，**不是** live agent 价值声明。

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
  段（buggy target 模块 + support 模块）和族特定决定性 cue。prompt
  **绝不**持久化。
- 结构化 edit action schema 为白名单：action 必须为
  `replace_return_value`、`choose_helper_constant` 或 `no_op`；file 必
  须为 `target.py`；无任意路径，无 shell。distractor 和 support 文件
  不可编辑。
- 若 provider 返回 `usage`，usage 诊断可包含聚合
  prompt/completion/total token 计数；否则标记不可用。
- cost 仅为 `cost_proxy`（恒为 0.0）；无 live 价格推断。
- 研究 docs/artifacts 记录规范化 model 显示名，不带路由前缀（如
  `Kimi-K2.7-Code`，而非 raw 路由前缀），除非记录确切的 workflow/env
  白名单。

## CLI

```bash
python3 -m py_compile eval/b16e_broader_live_provider_paired_smoke.py
python3 eval/b16e_broader_live_provider_paired_smoke.py --self-test
python3 eval/b16e_broader_live_provider_paired_smoke.py \
    --out artifacts/b16e_broader_live_provider_paired_smoke/\
b16e_broader_live_provider_paired_smoke_report.json
# Live opt-in（仅当 provider env 可用且安全时）：
OPENLOCUS_ALLOW_REMOTE=1 OPENLOCUS_LLM_WORKFLOW_DISPATCH=1 \
    python3 eval/b16e_broader_live_provider_paired_smoke.py \
    --allow-remote --task-count 8 \
    --out artifacts/b16e_broader_live_provider_paired_smoke/\
b16e_broader_live_provider_paired_smoke_report.json
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
remote gating、env preservation、missing env unavailable 路径、provider
诊断 redaction、四个族的 fake valid edit apply/test、invalid JSON
count、固定 provider 错误类别、action path/action 限制（包括
distractor/support 文件拒绝）、四个任务族、treatment/control 决定性
cue 差异、records-shaped 族矩阵、scanner forbidden keys/values、
no-claim flags 及 fail-closed scanner 行为。

## Provider client helper

B16-E 复用 B16-C/D 的 `eval/provider_client.py`（不变）。它是最小
OpenAI 兼容 chat helper，返回安全的 `ProviderCallResult` 对象，仅暴露
聚合计数（calls attempted/succeeded/failed、invalid_json、timeout、
latency、若 provider 返回 `usage` 的数值 usage、固定 failure-category
枚举 token、HTTP status）。raw prompt、message、response、base URL、
API key 及 provider payload **绝不**在公开诊断中返回。

## Artifact 身份（默认提交 artifact）

提交的 artifact 位于
`artifacts/b16e_broader_live_provider_paired_smoke/b16e_broader_live_provider_paired_smoke_report.json`，
是公开仅聚合 smoke artifact。身份/边界字段：

- `schema_version` =
  `b16e_broader_live_provider_paired_smoke.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`、`model_display_category`（规范化；无路由前缀）。
- Safe true flags（仅 live run 时；仅这些，全为 true）：
  `downstream_agent_runs_performed`、`live_llm_agent`、
  `provider_calls_made`、`remote_provider_calls_made`、
  `paired_run_executed`、`synthetic_task_family_matrix_used`、
  `real_file_edits_performed`、`real_test_commands_executed`、
  `agent_behavior_metrics_evaluated`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- unavailable/blocked 状态下，live-run 标志为 false（除
  `aggregate_only_public_artifact=true` 和 `diagnostic_only=true`；
  `synthetic_task_family_matrix_used=false` 因无 run）。
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
  `task_families`（四个白名单族名）、`paired_design`（`true`）、
  `workspace_isolation`（`fresh_tmp_per_task_arm`）、
  `transient_workspace_outputs_only`（`true`）、
  `designed_causal_subset`（`true`）、`task_family_matrix`（`true`）。
- `arm_results`：固定记录列表
  `{arm, metrics, provider_summary, failure_category_counts}`。
- `paired_deltas`：固定记录列表
  `{baseline_arm, treatment_arm, metric, delta}`。
- `task_family_results`：固定记录列表
  `{task_family, arm, run_count, solve_rate, tests_pass_rate,
  correct_file_before_first_edit_rate, wrong_file_edits_mean}`。
  仅白名单族名出现。无 task ID。
- `family_signal_summary`：仅聚合计数
  （`families_evaluated`、`families_with_positive_solve_delta`、
  `families_with_zero_solve_delta`、
  `families_with_negative_solve_delta`）。
- `honest_signals`：`context_pack_signal_observed`（bool）、
  `overall_treatment_solve_rate_delta`（number）、
  `overall_treatment_tests_pass_rate_delta`（number）、
  `families_evaluated`（int）、`families_with_positive_solve_delta`
  （int）、`families_with_zero_solve_delta`（int）、
  `families_with_negative_solve_delta`（int）。这些是诊断 smoke 结
  果，**绝不**是 promotion/default/value 声明。
- `self_test_summary` + `self_test_checks` + `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

## CI 通过标准

CI 通过意味着：

```text
live run completed + privacy scan passed + artifact is honest
```

CI 通过**不**要求 treatment 改善。零或负 treatment delta 是有效的实
证结果（如实记录即可）。两 arm 都解决或都失败也是有效的实证结果。
某些族可能显示正 delta，其他显示零或负；所有都是有效的实证结果。

## Forbidden scanner（公开，fail-closed）

严格 forbidden 输出 scanner 在写入公开 JSON 前 fail-closed 运行。拒绝
forbidden dict key 在任何位置出现（`prompt`、`prompts`、`message`、
`messages`、`response`、`responses`、`raw_response`、`request`、
`request_body`、`provider_payload`、`url`、`base_url`、`endpoint`、
`api_key`、`token`、`secret`、`authorization`、`bearer`、`workspace`、
`workspace_path`、`path`、`file`、`target_file`、`target_module`、
`distractor_module`、`support_module`、`test_module`、`snippet`、
`code`、`source`、`patch`、`diff`、`test_output`、`stdout`、`stderr`、
`event_log`、`stack_trace`、`content_sha`、`task_id`、`per_run`、
`model_id_raw`、`model_id` 等）及 value 模式：任意 URL（无 URL 允许列
表）、32+ 字符 hex digest、secret-like 字符串、带文件扩展名的
path-like 字符串、`/tmp/` 工作区路径 value、`task_N` 任务标识
value、patch/diff 标记、堆栈跟踪、多行字符串、raw JSON 片段、raw 行
范围、raw model 路由前缀及 self-test sentinel。

scanner 仅对最终公开聚合 artifact 运行。内部 per-run event log（含路
径/patch/测试 stdout/stderr）仅保留在内存中，绝不对公开契约扫描，绝
不提交。

## Self-tests

- Artifact 身份字段（schema、claim、status 枚举、mode、phase、
  generated_by）。
- Always-false no-claim flags（12 个全为 false）。
- Live-run flag gating（unavailable report：live-run flags false；
  live report：live-run flags true）。
- 四任务族生成（四族均存在；8 任务平衡；族特定确定性正确值）。
- 每族多文件工作区（target/distractor/support/test；同符号
  distractor；修复前测试失败）。
- Pack builder（control 缺少 target file cue AND 决定性 cue；
  treatment 含 target file cue、symbol cue、决定性 cue、exact edit
  constraint；treatment 比 control 更丰富）。
- 每族决定性 cue 文本（非空；无 raw 路由前缀）。
- 每族 fake valid provider response（treatment）：正确文件编辑；无
  错误文件；测试通过；solve=true；provider call 成功；task_family
  记录。
- Fake invalid JSON response（parse failure）：无编辑；测试失败；run
  result 中无 raw response。
- Edit action 限制：disallowed file 被拒；disallowed action 被拒；
  distractor.py 被拒；support.py 被拒；missing symbol 被拒；
  non-int new_return_value 被拒；non-object 被拒；valid action 被
  接受；`choose_helper_constant` 被接受；`no_op` 被接受。
- 聚合指标 + 族结果（records-shaped；四族；每族两 arm）+ 族信号摘要
  + honest signals（正 delta 时 context_pack_signal_observed true；
  零 delta 时 false）。
- Model display 规范化（剥离路由前缀；空返回 `unavailable`；剥离
  不安全字符）。
- env preservation self-test（probe 恢复 env；无网络 probe 不清除
  live provider env）。
- scanner 拒绝：工作区路径、文件路径、源码片段、patch 标记、测试输
  出、task_id key、raw event log、堆栈跟踪、content_sha key、hex
  digest、provider auth field、endpoint URL field、raw 路由前缀、
  URL value、prompt key、response key、messages key、
  provider_payload key、sentinel canary。
- scanner 允许：arm 名称、task family 名称、metric 记录、族结果记录、
  model display category、honest signal 字段、failure category
  token。
- fail-closed 生成：干净公开 report 不 raise；泄漏公开 report raise
  SystemExit；self-test 失败拒绝生成 artifact。
- 公开 artifact 自扫描干净（无任何 forbidden key）。
- CLI 参数面：`--self-test`、`--out`、`--allow-remote`、
  `--require-workflow-dispatch`、`--task-count` 是仅有的选项（加上
  `-h`/`--help`）；默认任务数在范围内。
- remote gating：`allow_remote=False` 时 blocked；env 缺失时
  unavailable。

## 验证

```text
python3 -m py_compile eval/b16e_broader_live_provider_paired_smoke.py  => PASS
python3 eval/b16e_broader_live_provider_paired_smoke.py --self-test  => PASS (188/188 checks)
python3 eval/b16e_broader_live_provider_paired_smoke.py \
  --out artifacts/b16e_broader_live_provider_paired_smoke/\
b16e_broader_live_provider_paired_smoke_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-E,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   synthetic_task_family_matrix_used: false,
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
provider env。live `broader_live_provider_paired_smoke_pass` artifact
需要显式本地 opt-in run 或手动 CI `real-provider-benchmark` workflow
（`stage=b16e_broader_live_provider_paired_smoke` +
`enable_remote_models=true`）。**手动 CI live-provider run：待执行。**

## 注意事项

- B16-E 是公开仅聚合 broader live-provider 下游 paired smoke
  artifact。它是 eval/诊断专用。它**不**改变 runtime、retriever、
  pack、backend 或 default policy；它**不**改变 EvidenceCore 语义。
  它**不是**基准测试结果，**不是**下游 agent 价值声明，**不是**
  runtime-clean 通用算法声明，**不是** OOD 时间性声明，也**不是**
  QuIVer 系统声明。
- B16-E 仅在 `--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider
  env 全部设置时使用 **live LLM provider**（OpenAI 兼容）。提交的
  artifact 是真实的：若本地无 provider env，其状态为
  `blocked_remote_not_enabled` /
  `unavailable_no_local_provider_env`，live-run 标志为 false。它**不
  是** fake pass。
- B16-E **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- B16-E **不**声明 live agent 泛化。
  `live_agent_generalization_claimed=false`。
- B16-E **不**发布 prompt、response、provider payload、base URL、
  API key、raw model 路由前缀、工作区路径、文件路径、源码片段、
  patch/diff、测试输出、raw event log 或 per-run 行。per-run event
  log、prompt、response 和测试输出仅留在 `/tmp`，**绝不**提交或上
  传。
- 提交的 artifact 仅含 records-shaped 容器中的聚合
  counts/rates/means。不发布 raw model 路由前缀；仅记录规范化的
  `model_display_category`。
- `honest_signals` 和 `family_signal_summary` 是诊断 smoke 结果，
  **绝不**是 promotion/default/value 声明。零或负 treatment delta
  是有效的实证结果。某些族可能显示正 delta，其他显示零或负；所有都
  是有效的实证结果。
- 所有无声明 / 无运行时变更标志保持 false；诊断标志
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  live-run 标志**仅**在 live run 实际执行时为 true。
- 未修改任何 runtime/retriever/pack/model/backend/default-policy 文
  件。无 promotion/default/runtime 声明变更。
