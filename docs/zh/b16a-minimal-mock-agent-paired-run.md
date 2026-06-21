# B16-A 最小 Mock 下游 Paired Run（公开仅聚合 artifact）

## 范围与声明边界

B16-A 是**首个非仅控制面的 B16 风格下游 agent 实证 run**。它在临时
`/tmp` 目录下对微型合成 Python 工作区真实执行 edit/test 循环，并产出行为
指标。agent 是**确定性 mock agent**（无 live LLM、无 provider 调用、无远
程调用），其行为依赖于所提供的 context pack。

B16-A 明确**不是** live LLM 下游 agent run，**不是**下游 agent 价值声
明，**不是**外部基准测试性能声明，**不是** live agent 泛化声明，**不
是**真实用户任务声明，**不是**提升，**不是** default/policy 改动，也
**不是** runtime/retriever/pack/backend/EvidenceCore 语义改动。

B16-A **不**声明下游 agent 价值，**不**提升任何 candidate，**不**改变
runtime/retriever/pack/backend/default-policy/EvidenceCore 语义，**不**
声明 live agent 泛化，**不**声明外部基准测试性能，**不**声明真实用户任
务。提交的 artifact 仅含聚合数据：不含 task ID、工作区路径、文件路径、
源码片段、patch/diff、测试输出、raw event log、per-run 行、私有 ID，
也不含超出确定性 mock 身份以外的 provider/model 信息。

- 声明级别（claim_level）：`deterministic_mock_downstream_paired_smoke_only`。
- 状态（status）：成功时为 `mock_downstream_paired_smoke_pass`；模式
  （mode）为 `public_aggregate_synthetic_micro_tasks`；阶段（phase）为
  `B16-A`。
- B16-A 是 **eval/诊断专用**。它**不是**基准测试结果，**不是** live
  下游 agent 价值声明，**不是** runtime-clean 通用算法声明，**不是**
  OOD 时间性声明，也**不是** QuIVer 系统声明。

### D5-A0 -> B16-A 关系

```text
D5-A0 自动 E/S 校准 smoke（仅 retrieval 聚合）
-> B16-A 最小确定性/mock 下游 paired-agent 实证 run
   （真实 edit/test 循环；确定性 mock agent；paired control/treatment
    arms；合成公开 micro 任务；仅聚合公开 artifact；
    无 live LLM、无 provider/远程调用、无下游 agent 价值声明）
```

B16-A **不是** B16。完整的 B16 下游 coding-agent 评估阶段仍是需要真实
provider 调用的 live paired agent run 的有界规划/可行性阶段。B16-A 仅通
过在合成公开 micro 任务上运行确定性 mock agent，产出首个实证下游
agent 形态 smoke。它**不**解锁 B16 live agent 价值、
default/policy/公开发布或任何提升声明。

## 合成公开 micro bug 任务设计

B16-A 在代码中生成确定性合成公开 micro bug 任务规格（默认 24 个；可通
过 `--task-count` 在 4-32 范围内配置）。每个任务规格描述一个微型 Python
模块，含一行 bug（返回错误值）及一个断言正确值的 stdlib 测试。修复是确
定性的一行返回值替换。

对每个任务和 arm，B16-A 创建一个全新的 `/tmp` 工作区，包含：

- `target.py`：含一行 bug 的微型模块（返回错误值）。
- `distractor.py`：相似符号的错误文件 distractor（mock agent 若收到
  wrong cue 可能编辑此文件）。
- `test_target.py`：导入 `target` 并断言正确值的 stdlib 测试；成功退出
  0，失败退出 1。

所有工作区文件都是写到 `/tmp` 下的真实 Python 文件。harness 真实编辑文
件并运行子进程测试。

## Paired arm 设计

B16-A 运行 paired control/treatment arms，预算/工具约束相同；仅 context
pack 不同。

- **control arm**：bare/wrong-cue pack。对设计子集（偶数索引任务），
  control pack 携带指向 distractor 的 **wrong-cue file**；对其余任务，
  **完全无文件 cue**。确定性 mock agent 因此编辑错误文件（或什么都不做）
  且测试失败。
- **treatment arm**：更丰富的 evidence pack，含 **target file**、
  **target symbol**、**operation hint** cue。确定性 mock agent 编辑正确
  的 target 文件且测试通过。

treatment pack 对设计子集**因果地改变**确定性 mock agent 的行为。这是
因果 pack 效果 smoke，**不是** live agent 价值声明。

## 确定性 mock agent

mock agent 完全确定且依赖 pack：

1. 若 pack 含 `target_file` cue -> 用正确修复编辑该文件（测试将通过）。
2. 若 pack 含 `wrong_cue_file` cue -> 编辑错误文件（测试仍失败；
   `wrong_file_edits=1`）。
3. 否则 -> 什么都不做（测试失败；无编辑）。

编辑（或 no-op）后，agent 运行真实子进程测试命令
（`python3 <workspace>/test_target.py`）并记录通过/失败结果。per-run
**event log**（含文件路径、编辑内容、测试 stdout/stderr）仅保留在内存
中，**绝不**写入公开 artifact。仅返回聚合指标。

## CLI

```bash
python3 -m py_compile eval/b16a_minimal_mock_agent_paired_run.py
python3 eval/b16a_minimal_mock_agent_paired_run.py --self-test
python3 eval/b16a_minimal_mock_agent_paired_run.py \
    --out artifacts/b16a_minimal_mock_agent_paired_run/\
b16a_minimal_mock_agent_paired_run_report.json
# 覆盖确定性任务数（范围 4-32）：
python3 eval/b16a_minimal_mock_agent_paired_run.py \
    --task-count 12 \
    --out /tmp/b16a_smoke_report.json
```

默认模式：写入提交的公开仅聚合 artifact（若省略 `--out` 则使用默认输出
路径）。默认模式生成确定性合成公开 micro bug 任务，为每个 task+arm 创建
全新 `/tmp` 工作区，运行确定性 mock agent（真实文件编辑 + 真实子进程测
试），计算聚合行为指标，并仅写入公开聚合 artifact。raw event log/
patch/测试输出仅留在 `/tmp`，绝不提交或上传。

CLI 参数：`--self-test`、`--out`、`--task-count`。未知/私有外观参数被以
通用 `invalid arguments` 消息拒绝，不回显私有路径或基名
（SafeArgumentParser 模式）。

`--self-test` 运行真实 `/tmp` 工作区 edit/test 循环，无需外部 provider；
覆盖真实文件编辑、真实测试子进程执行、arm pack 差异、mock 行为对 pack
cue 的依赖、聚合数学、scanner 拒绝（路径、片段、patch、测试输出、
task_id、event log、堆栈跟踪、content_sha、provider auth/endpoint、
secret sentinel、URL、行范围）、no-claim flag 不变量、fail-closed 生成
及 CLI 参数面。

### 守卫要求

1. 默认模式在代码中生成确定性合成公开 micro bug 任务（无需外部数据集）。
2. 每个 task+arm 获得全新 `/tmp` 工作区；arm 与任务间无共享状态。
3. mock agent 执行真实文件编辑并运行真实子进程测试（stdlib Python）。
4. per-run event log（路径、patch、测试输出）仅留在 `/tmp`，绝不提交或
   上传（`transient_workspace_outputs_only=true`）。
5. 提交的 artifact 仅含聚合 counts/rates/means；无 per-run 行、无路径、
   无文件路径、无源码片段、无 patch/diff、无测试输出、无 event log、
   无 task ID、无 content hash、无 secret。
6. 严格 fail-closed forbidden scanner 在写入 JSON artifact 前立即运行
   （`_enforce_no_forbidden`）。
7. self-test 失败拒绝成功生成 artifact
   （`_refuse_on_self_test_failure`）。

## Artifact 身份（默认提交 artifact）

提交的 artifact 位于
`artifacts/b16a_minimal_mock_agent_paired_run/b16a_minimal_mock_agent_paired_run_report.json`，
是公开仅聚合 smoke artifact。身份/边界字段：

- `schema_version` = `b16a_minimal_mock_agent_paired_run.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`
- Safe true flags（仅这些，全为 true）：
  `downstream_agent_runs_performed`、`deterministic_mock_agent`、
  `synthetic_micro_tasks_used`、`paired_arms_evaluated`、
  `real_file_edits_performed`、`real_test_commands_executed`、
  `agent_behavior_metrics_evaluated`、`aggregate_only_public_artifact`、
  `diagnostic_only`。
- No-claim / no-runtime-change flags（全为 false）：
  `live_llm_agent`、`provider_calls_made`、`remote_calls_made`、
  `downstream_agent_value_proven`、`promotion_ready`、
  `default_should_change`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `external_benchmark_performance_claimed`、
  `live_agent_generalization_claimed`、`real_user_task_claimed`。
- `input_summary`：`synthetic_task_count`、`run_count_per_arm`、
  `total_runs`、`arms`（`[control, treatment]`）、`paired_design`
  （`true`）、`workspace_isolation`（`fresh_tmp_per_task_arm`）、
  `transient_workspace_outputs_only`（`true`）、
  `designed_causal_subset`（`true`）。
- `arm_metrics`：per-arm 字典（`control`、`treatment`），含
  `run_count`、`solve_rate`、`tests_pass_rate`、
  `correct_file_before_first_edit_rate`、`wrong_file_edits_mean`、
  `tool_calls_before_first_edit_mean`、`context_tokens_mean`、
  `latency_ms_mean`、`cost_proxy_mean`。无 per-run 行、无路径、无
  patch、无测试输出。
- `deltas_treatment_minus_control`：所有 rate/mean 指标的
  treatment-minus-control delta（不含 `run_count`，paired 设计下两者
  相同）。
- `self_test_summary` + `self_test_checks` + `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

## 聚合指标

per-arm 聚合指标（无 per-run 行）：

- `run_count`：arm 中的 run 数（= 合成任务数）。
- `solve_rate`：测试通过且正确文件在首次编辑前/时被编辑的 run 比例。
- `tests_pass_rate`：agent 动作后测试通过的 run 比例。
- `correct_file_before_first_edit_rate`：首次编辑在正确 target 文件上的
  run 比例。
- `wrong_file_edits_mean`：每个 run 的错误文件编辑数均值。
- `tool_calls_before_first_edit_mean`：首次编辑前的 tool 调用数均值。
- `context_tokens_mean`：确定性 context-token 计数均值（control pack
  较小；treatment pack 更丰富）。
- `latency_ms_mean`：测试子进程的真实墙钟延迟均值（毫秒）。
- `cost_proxy_mean`：成本代理均值（确定性 mock agent 恒为 0.0；无
  provider 调用）。

所有 rate/mean 指标均输出 treatment-minus-control delta（不含
`run_count`）。因为是合成公开任务，确切的合成任务/run 计数可接受。

## Forbidden scanner（公开，fail-closed）

严格 forbidden 输出 scanner 在写入公开 JSON 前 fail-closed 运行。拒绝
forbidden dict key（`task_id`、`task_index`、`workspace_path`、
`workspace`、`file`、`filename`、`filepath`、`target_file`、
`wrong_cue_file`、`target_module`、`distractor_module`、`test_module`、
`path`、`span`、`start_line`、`end_line`、`content_sha`、
`content_hash`、`snippet`、`code`、`source_code`、`patch`、`diff`、
`test_output`、`test_log`、`test_stdout`、`test_stderr`、`stdout`、
`stderr`、`event_log`、`events`、`log`、`trace`、`raw_event`、
`stack_trace`、`traceback`、`api_key`、`base_url`、`provider_key`、
`secret`、`token`、`credential`、`rows`、`per_run`、`predictions`、
`candidates` 等）在任何位置出现，并拒绝 value 模式：任意 URL（无 URL
允许列表）、32+ 字符 hex digest、secret-like 字符串
（api_key/base_url/provider_key/secret/password/credential）、带文件扩展
名的 path-like 字符串、`/tmp/` 工作区路径 value、`task_N` 任务标识
value、patch/diff 标记（`---`、`+++`、`@@`）、堆栈跟踪
（`Traceback (most recent call last)`）、多行字符串、raw JSON 片段、
raw 行范围 `12-34`，以及 self-test sentinel。

scanner 仅对最终公开聚合 artifact 运行。内部 per-run event log（含路
径/patch/测试 stdout/stderr）仅保留在内存中，绝不对公开契约扫描，绝不
提交。

## Self-tests

- Artifact 身份字段（schema、claim、status、mode、phase、generated_by）。
- Safe true flags（9 个全为 true）；no-claim / no-runtime-change false
  flags（15 个全为 false）。
- 合成任务生成：确定性计数、符号、正确值、buggy 值。
- Pack builder：control 偶数索引含 wrong-cue file；control 奇数索引无
  文件 cue；treatment 含 target file/symbol/operation hint cue；
  treatment pack 比 control 更丰富；control pack 缺少 target file cue。
- 真实工作区创建：target/distractor/test 文件存在于磁盘。
- 真实测试子进程：修复前测试失败（bug 存在）。
- mock agent 行为（依赖 pack）：treatment 编辑正确文件、无错误文件编辑、
  测试通过、solve=true、真实文件编辑已应用；control wrong-cue 编辑错
  误文件、wrong_file_edits=1、测试失败、solve=false、distractor 文件
  实际被编辑；control no-cue 什么都不做、测试失败、solve=false。
- mock 行为对 pack cue 的依赖：target_file cue 驱动正确文件编辑；
  wrong_cue_file 驱动错误文件编辑；treatment solve rate 高于 control。
- 聚合指标数学：run_count、solve_rate、tests_pass_rate、
  correct_file_rate、wrong_file_edits_mean、tool_calls_mean、
  cost_proxy_mean=0。
- delta 计算：solve_rate delta 为正、wrong_file_edits_mean delta 为负、
  run_count 不在 delta 中。
- forbidden scanner 拒绝：工作区路径、文件路径、源码片段、patch 标记、
  测试输出、task_id key、task_id value、raw event log、堆栈跟踪、
  content_sha key、hex digest value、provider auth field、endpoint URL
  field、sentinel canary、URL value、forbidden field name as value、行范
  围 value。
- forbidden scanner 允许：arm 名称（control/treatment）、指标值、工作区
  隔离 token。
- fail-closed 生成：干净公开 report 不 raise；泄漏公开 report raise
  SystemExit；self-test 失败拒绝生成 artifact；失败 self-test 不携带成
  功状态。
- 公开 artifact 自扫描干净（无任何 forbidden key）。
- CLI 参数面：`--self-test`、`--out`、`--task-count` 是仅有的选项（加上
  `-h`/`--help`）；默认任务数在范围内。

## 验证

```text
python3 -m py_compile eval/b16a_minimal_mock_agent_paired_run.py    => PASS
python3 eval/b16a_minimal_mock_agent_paired_run.py --self-test      => PASS (104/104 checks)
python3 eval/b16a_minimal_mock_agent_paired_run.py \
  --out artifacts/b16a_minimal_mock_agent_paired_run/\
b16a_minimal_mock_agent_paired_run_report.json                     => PASS
  (status: mock_downstream_paired_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_micro_tasks, phase: B16-A,
   synthetic_task_count: 24, total_runs: 48,
   control: solve_rate=0.0, tests_pass_rate=0.0,
     correct_file_before_first_edit_rate=0.0,
     wrong_file_edits_mean=0.5,
   treatment: solve_rate=1.0, tests_pass_rate=1.0,
     correct_file_before_first_edit_rate=1.0,
     wrong_file_edits_mean=0.0,
   deltas_treatment_minus_control: solve_rate=+1.0,
     wrong_file_edits_mean=-0.5,
   live_llm_agent: false, provider_calls_made: false,
   remote_calls_made: false,
   downstream_agent_value_proven: false,
   promotion_ready: false,
   default_should_change: false,
   retriever_changed: false,
   pack_builder_changed: false,
   backend_changed: false,
   default_policy_changed: false,
   evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false,
   real_user_task_claimed: false)
python3 scripts/validate_docs_i18n.py                           => PASS
git diff --check                                               => PASS
```

## 注意事项

- B16-A 是公开仅聚合最小 mock 下游 paired smoke artifact。它是
  eval/诊断专用。它**不**改变 runtime、retriever、pack、backend 或
  default policy；它**不**改变 EvidenceCore 语义。它**不是**基准测试
  结果，**不是** live 下游 agent 价值声明，**不是** runtime-clean 通用
  算法声明，**不是** OOD 时间性声明，也**不是** QuIVer 系统声明。
- B16-A 使用**确定性 mock agent**（无 live LLM、无 provider 调用、无远
  程调用）。mock agent 的行为按设计依赖 pack：treatment pack 含 target
  file/symbol/operation cue，而 control pack 缺少 target cue 或携带
  wrong-cue file。这是因果 pack 效果 smoke，**不是** live agent 价值声
  明。
- B16-A 在代码中生成**确定性合成公开 micro bug 任务**。这些**不是**真
  实用户任务，也**不是**外部基准测试任务。因为是合成公开任务，确切的
  任务/run 计数可接受。
- B16-A 在每个 task+arm 的全新 `/tmp` 工作区中执行**真实文件编辑**和
  **真实子进程测试**（stdlib Python）。per-run event log、patch 和测试
  输出仅留在 `/tmp`，**绝不**提交或上传。提交的 artifact 仅含聚合
  counts/rates/means。
- B16-A **不**证明下游 agent 价值。treatment-vs-control delta 是设计
  pack cue 的确定性 mock 产物，**不是** treatment pack 改善 live 下游
  agent 的证据。`downstream_agent_value_proven=false`。
- B16-A **不**声明 live agent 泛化。确定性 mock agent 按构造平凡地泛化
  到合成任务族；这**不是** live agent 泛化声明。
  `live_agent_generalization_claimed=false`。
- 所有 no-claim / no-runtime-change flags 保持 false；诊断 flag
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  确定性 mock run flag（`downstream_agent_runs_performed`、
  `deterministic_mock_agent`、`synthetic_micro_tasks_used`、
  `paired_arms_evaluated`、`real_file_edits_performed`、
  `real_test_commands_executed`、`agent_behavior_metrics_evaluated`）是
  仅有的额外 true flag。
- 未修改任何 runtime/retriever/pack/model/backend/default-policy 文
  件。无 promotion/default/runtime 声明变更。
