# F1 反事实证据效用 Smoke（公开仅聚合 artifact）

## 范围与声明边界

F1 是 OpenLocus 研究轨中**首个反事实证据效用 smoke**。它检验深层研究
设想：evidence/support 应当被度量为一个 coding-agent 轨迹的**边际因果
效用**，而不仅是主观相关性。F1 在临时 `/tmp` 目录下对微型合成 Python
工作区真实执行 edit/test 循环，跨**六个反事实 context variant**，并从
聚合 per-variant 指标计算**五个边际效用 delta**。

F1 明确**不是** live LLM 下游 agent run，**不是**下游 agent 价值声明，
**不是**外部基准测试性能声明，**不是** live agent 泛化声明，**不是**
真实用户任务声明，**不是**真实 E/S 校准声明，**不是**提升，**不是**
default/policy 改动，也**不是** runtime/retriever/pack/backend/
EvidenceCore 语义改动。

agent 是**确定性 mock agent**（无 live LLM、无 provider 调用、无远程
调用），其行为依赖于所提供的 context pack。提交的 artifact 仅含聚合
数据：不含 task ID、工作区路径、文件路径、源码片段、patch/diff、测试
输出、raw event log、per-run 行、私有 ID，也不含超出确定性 mock 身份
以外的 provider/model 信息。

- 声明级别（claim_level）：`counterfactual_evidence_utility_smoke_only`。
- 状态（status）：成功时为 `counterfactual_evidence_utility_smoke_pass`；
  模式（mode）为 `public_aggregate_synthetic_micro_tasks`；阶段
  （phase）为 `F1`。
- F1 是 **eval/诊断专用**。它**不是**基准测试结果，**不是** live
  下游 agent 价值声明，**不是**真实 E/S 校准声明，**不是** runtime-clean
  通用算法声明，**不是** OOD 时间性声明，也**不是** QuIVer 系统声明。

### D5-A0 -> B16-A -> C5-A -> F1 关系

```text
D5-A0 自动 E/S 校准 smoke（仅 retrieval 聚合）
-> B16-A 最小确定性/mock 下游 paired-agent 实证 run
   （真实 edit/test 循环；确定性 mock agent；paired control/treatment
    arms；合成公开 micro 任务；仅聚合公开 artifact；
    无 live LLM、无 provider/远程调用、无下游 agent 价值声明）
-> C5-A ContextBench verified 检索性能 smoke
   （外部-benchmark-形态检索 smoke；有界 ContextBench verified subset；
    临时 /tmp clone + retrieval + score；aggregate-only 公共 artifact；
    无 provider 调用；无外部 benchmark 性能声明）
-> F1 反事实证据效用 smoke
   （六个反事实 context variant；确定性 mock agent；
    真实 edit/test 循环；五个边际效用 delta 从聚合 variant 指标计算；
    aggregate-only 公共 artifact；
    无 live LLM、无 provider/远程调用；不是真实 E/S 校准）
```

F1 **不是**真实 E/S 校准。它是一个确定性/mock 因果 smoke，在反事实
context variant 之间计算边际效用 delta。这些 delta 是因果形态的
（variant 对 variant），但 agent 是确定性的，任务是合成的，context 是
手工设计的。`true_e_s_calibration_claimed=false`、
`automated_e_s_full_calibration_claimed=false`、
`human_e_s_calibration_claimed=false`。

## 合成公开 micro bug 任务设计

F1 在代码中生成确定性合成公开 micro bug 任务规格（默认 24 个；可通
过 `--task-count` 在 4-100 范围内配置）。每个任务规格描述一个微型
Python 模块，含一行 bug（返回错误值）及一个断言正确值的 stdlib 测试。
修复是确定性的一行返回值替换。

对每个任务和 variant，F1 创建一个全新的 `/tmp` 工作区，包含：

- `target.py`：含一行 bug 的微型模块（返回错误值）。mock agent 在
  primary cue 存在时编辑此文件。
- `support.py`：helper 模块，含一个**非** target symbol 的支持符号。
  编辑此文件不影响测试结果（测试只导入 `target`）。
- `distractor.py`：相似符号的错误文件 distractor（mock agent 若收到
  wrong cue 可能编辑此文件）。
- `test_target.py`：导入 `target` 并断言正确值的 stdlib 测试；成功退出
  0，失败退出 1。

所有工作区文件都是写到 `/tmp` 下的真实 Python 文件。harness 真实编辑
文件并运行子进程测试。这些文件名和路径**绝不**出现在公开 artifact 中。

## 六个反事实 context variant

F1 对每个任务运行**六个反事实 context variant**。variant 之间仅 context
pack 不同；预算/工具约束和确定性 mock agent 都相同。

1. **`base_no_context`**：完全无文件 cue。确定性 mock agent 什么都不做
   -> 测试失败。solve_rate=0.0，wrong_file_edits=0，tool_calls=0，
   context_tokens=8。
2. **`primary_only`**：primary target/symbol/operation cue。确定性 mock
   agent 编辑正确的 target 文件 -> 测试通过。solve_rate=1.0，
   wrong_file_edits=0，tool_calls=1，context_tokens=24。
3. **`support_only`**：仅 support cue（无 primary）。确定性 mock agent
   编辑 `support.py`（错误文件；测试只导入 `target`） -> 测试失败。
   solve_rate=0.0，wrong_file_edits=1，tool_calls=1，context_tokens=20。
4. **`primary_plus_support`**：primary + support cue。确定性 mock agent
   先 inspect support（1 次 tool call，无编辑），然后正确编辑
   `target.py` -> 测试通过；比 primary 更丰富的 context。
   solve_rate=1.0，wrong_file_edits=0，tool_calls=2，context_tokens=40。
5. **`distractor_only`**：仅 wrong cue。确定性 mock agent 编辑
   `distractor.py`（错误文件） -> 测试失败；`wrong_file_edits` 增加。
   solve_rate=0.0，wrong_file_edits=1，tool_calls=1，context_tokens=16。
6. **`primary_plus_distractor`**：primary + distractor cue。确定性 mock
   agent 先 inspect distractor（1 次 tool call，无编辑），然后正确编辑
   `target.py`，再编辑 `distractor.py`（在正确首次编辑之后；测试仍通过，
   因 target 已修复） -> 测试通过；`wrong_file_edits` / `tool_calls` /
   `context_tokens` 比 primary 差。solve_rate=1.0，wrong_file_edits=1，
   tool_calls=2，context_tokens=32。

`primary_plus_distractor` 是第六个 variant（oracle 计划列出五个；F1
新增第六个以支持干净的 conditional distractor utility delta
`distractor_added_to_primary`）。docs 与 artifact
`input_summary.variant_count=6` 显式声明这一点。

## 五个边际效用 effect

F1 从聚合 variant 指标计算**五个边际效用 effect**。effect 名称刻意
是效用专属的，**不**使用 `E_primary` / `S_support` 这种像真实 E/S
校准的字段名：

- **`primary_context_vs_base`** = `primary_only` - `base_no_context`
- **`support_context_vs_base`** = `support_only` - `base_no_context`
- **`distractor_context_vs_base`** = `distractor_only` - `base_no_context`
- **`support_added_to_primary`** = `primary_plus_support` - `primary_only`
- **`distractor_added_to_primary`** = `primary_plus_distractor` - `primary_only`

每个 effect 为所有 rate/mean 指标输出 delta（不含 `run_count`，paired
设计下 variant 之间相同）：`solve_rate_delta`、`tests_pass_rate_delta`、
`correct_file_before_first_edit_rate_delta`、
`wrong_file_edits_mean_delta`、
`tool_calls_before_first_edit_mean_delta`、
`context_tokens_mean_delta`、`latency_ms_mean_delta`、
`cost_proxy_mean_delta`。

在确定性合成任务族上的预期边际 effect（solve_rate /
wrong_file_edits_mean / tool_calls_before_first_edit_mean /
context_tokens_mean delta）：

```text
primary_context_vs_base:    solve +1.0, wrong   +0.0, tools +1.0, ctx +16.0
support_context_vs_base:    solve  0.0, wrong   +1.0, tools +1.0, ctx +12.0
distractor_context_vs_base: solve  0.0, wrong   +1.0, tools +1.0, ctx  +8.0
support_added_to_primary:   solve  0.0, wrong   +0.0, tools +1.0, ctx +16.0
distractor_added_to_primary:solve  0.0, wrong   +1.0, tools +1.0, ctx  +8.0
```

解读：

- **primary context** 是唯一相对 base 有正 solve_rate delta 的 context
  variant。它因果地把 mock agent 的行为从 no-op 改为正确的 target 编辑。
- **support context 单独**不解题（它编辑错误文件），但仍产生 wrong-file
  编辑和 tool call。它相对 base 的边际效用在 cost 指标上为负。
- **distractor context 单独**不解题，并产生 wrong-file 编辑和 tool call。
  它相对 base 的边际效用在 cost 指标上为负。
- 把 **support 加到 primary** 不改变正确性（仍解题），但增加 tool call
  和 context token（cost 侧的边际变化，对该合成族无正确性收益）。
- 把 **distractor 加到 primary** 不改变正确性（仍解题，因为 primary 胜
  出），但增加 wrong-file 编辑、tool call 和 context token（cost 指标上
  的负 conditional distractor 效用）。

这是一个合成因果设计，**不是**对所有 retrieval support candidate 的通
用声明。

## Theory mapping（不是真实 E/S 校准）

artifact 携带一个 `theory_mapping` 块，记录边际 effect 如何对应 E-utility
和 S-conditional utility smoke proxy：

- `primary_context_vs_base` -> `e_utility_smoke_proxy`
- `support_context_vs_base` -> `e_utility_smoke_proxy_support_variant`
- `distractor_context_vs_base` -> `e_utility_smoke_proxy_distractor_variant`
- `support_added_to_primary` -> `s_conditional_utility_smoke_proxy`
- `distractor_added_to_primary` -> `s_conditional_distractor_utility_smoke_proxy`

但 F1 明确**不是**真实 E/S 校准：
`true_e_s_calibration_claimed=false`、
`automated_e_s_full_calibration_claimed=false`、
`human_e_s_calibration_claimed=false`。theory mapping 仅为命名/解释辅助；
边际 delta 是从合成任务上的确定性 mock 聚合指标计算的，**不是**从真实
人工/手动 E/S 标签或真实 E/S rubric 评分计算的。

## 确定性 mock agent

mock agent 完全确定且依赖 pack：

1. 若 pack 含 `target_file` cue（primary cue 存在）：
   - 若 `support_file` 也存在：inspect support（1 次 tool call，无编辑），
     然后正确编辑 `target.py`。
   - 若 `wrong_cue_file` 也存在：inspect distractor（1 次 tool call，
     无编辑），然后正确编辑 `target.py`，再编辑 `distractor.py`
     （在正确首次编辑**之后**的 wrong file 编辑；测试仍通过，因
     `target.py` 已修复）。
   - 否则：正确编辑 `target.py`。
2. 若 pack 含 `support_file` cue（无 primary）：编辑 `support.py`
   （错误文件）；测试仍失败。
3. 若 pack 含 `wrong_cue_file` cue（无 primary）：编辑 `distractor.py`
   （错误文件）；测试失败。
4. 否则 -> 什么都不做（测试失败；无编辑）。

编辑（或 no-op）后，agent 运行真实子进程测试命令
（`python3 <workspace>/test_target.py`）并记录通过/失败结果。per-run
**event log**（含文件路径、编辑内容、测试 stdout/stderr）仅保留在内存
中，**绝不**写入公开 artifact。仅返回聚合指标。

## CLI

```bash
python3 -m py_compile eval/f1_counterfactual_evidence_utility_smoke.py
python3 eval/f1_counterfactual_evidence_utility_smoke.py --self-test
python3 eval/f1_counterfactual_evidence_utility_smoke.py \
    --out artifacts/f1_counterfactual_evidence_utility/\
f1_counterfactual_evidence_utility_report.json
# 覆盖确定性任务数（范围 4-100）：
python3 eval/f1_counterfactual_evidence_utility_smoke.py \
    --task-count 48 \
    --out /tmp/f1_smoke_report.json
```

默认模式：写入提交的公开仅聚合 artifact（若省略 `--out` 则使用默认输出
路径）。默认模式生成确定性合成公开 micro bug 任务，为每个 task+variant
创建全新 `/tmp` 工作区，运行确定性 mock agent（真实文件编辑 + 真实子进程
测试），计算聚合行为指标和边际效用 delta，并仅写入公开聚合 artifact。
raw event log/patch/测试输出仅留在 `/tmp`，绝不提交或上传。

CLI 参数：`--self-test`、`--out`、`--task-count`。未知/私有外观参数被以
通用 `invalid arguments` 消息拒绝，不回显私有路径或基名
（SafeArgumentParser 模式）。

`--self-test` 运行真实 `/tmp` 工作区 edit/test 循环，无需外部 provider；
覆盖真实文件编辑、真实测试子进程执行、全部六个 variant pack 设计、
mock 行为对 pack cue 的依赖、聚合数学、全部五个边际 effect 计算、
theory-mapping 不变量、scanner 拒绝（路径、片段、patch、测试输出、
task_id、event log、堆栈跟踪、content_sha、provider auth/endpoint、
secret sentinel、URL、行范围、多行、raw JSON）、no-claim flag 不变量、
fail-closed 生成及 CLI 参数面。

### 守卫要求

1. 默认模式在代码中生成确定性合成公开 micro bug 任务（无需外部数据集）。
2. 每个 task+variant 获得全新 `/tmp` 工作区；variant 与任务间无共享状态。
3. mock agent 执行真实文件编辑并运行真实子进程测试（stdlib Python）。
4. per-run event log（路径、patch、测试输出）仅留在 `/tmp`，绝不提交或
   上传（`transient_workspace_outputs_only=true`）。
5. 提交的 artifact 仅含聚合 counts/rates/means 和聚合边际 delta；无
   per-run 行、无路径、无文件路径、无源码片段、无 patch/diff、无测试
   输出、无 event log、无 task ID、无 content hash、无 secret、无
   context pack 内容。
6. 严格 fail-closed forbidden scanner 在写入 JSON artifact 前立即运行
   （`_enforce_no_forbidden`）。
7. self-test 失败拒绝成功生成 artifact
   （`_refuse_on_self_test_failure`）。

## Artifact 身份（默认提交 artifact）

提交的 artifact 位于
`artifacts/f1_counterfactual_evidence_utility/f1_counterfactual_evidence_utility_report.json`，
是公开仅聚合 smoke artifact。身份/边界字段：

- `schema_version` = `f1_counterfactual_evidence_utility_smoke.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`
- Safe true flags（仅这些，全为 true）：
  `counterfactual_context_variants_executed`、`deterministic_mock_agent`、
  `real_file_edits_performed`、`subprocess_tests_executed`、
  `marginal_utility_metrics_computed`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- No-claim / no-runtime-change flags（全为 false）：
  `live_llm_agent`、`provider_calls_made`、
  `remote_provider_calls_made`、`downstream_agent_value_proven`、
  `live_agent_generalization_claimed`、`real_user_task_claimed`、
  `true_e_s_calibration_claimed`、
  `automated_e_s_full_calibration_claimed`、
  `human_e_s_calibration_claimed`、
  `external_benchmark_performance_claimed`、`promotion_ready`、
  `default_should_change`、`runtime_behavior_changed`、
  `retriever_changed`、`pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`。
- `input_summary`：`synthetic_task_count`、`run_count_per_variant`、
  `total_runs`、`variants`（六个固定 variant 标签）、`variant_count`
  （6）、`effects`（五个固定 effect 标签）、`effect_count`（5）、
  `counterfactual_design`（`true`）、
  `workspace_isolation`（`fresh_tmp_per_task_variant`）、
  `transient_workspace_outputs_only`（`true`）。
- `variant_metrics`：per-variant 字典（六个 variant），含
  `run_count`、`solve_rate`、`tests_pass_rate`、
  `correct_file_before_first_edit_rate`、`wrong_file_edits_mean`、
  `tool_calls_before_first_edit_mean`、`context_tokens_mean`、
  `latency_ms_mean`、`cost_proxy_mean`。无 per-run 行、无路径、无
  patch、无测试输出。
- `marginal_effects`：per-effect 字典（五个 effect），含
  `<metric>_delta`（所有 rate/mean 指标，不含 `run_count`）。
- `theory_mapping`：把 effect 映射到 E-utility / S-conditional utility
  smoke proxy 标签；携带 `true_e_s_calibration_claimed=false`、
  `automated_e_s_full_calibration_claimed=false`、
  `human_e_s_calibration_claimed=false`。
- `self_test_summary` + `self_test_checks` + `self_test_passed`。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

## 聚合指标

per-variant 聚合指标（无 per-run 行）：

- `run_count`：variant 中的 run 数（= 合成任务数）。
- `solve_rate`：测试通过且正确文件在首次编辑前/时被编辑的 run 比例。
- `tests_pass_rate`：agent 动作后测试通过的 run 比例。
- `correct_file_before_first_edit_rate`：首次编辑在正确 target 文件上的
  run 比例。
- `wrong_file_edits_mean`：每个 run 的错误文件编辑数均值。
- `tool_calls_before_first_edit_mean`：首次编辑前的 tool 调用数均值。
- `context_tokens_mean`：确定性 context-token 计数均值（base pack 最小；
  primary+support pack 最丰富）。
- `latency_ms_mean`：测试子进程的真实墙钟延迟均值（毫秒）。
- `cost_proxy_mean`：成本代理均值（确定性 mock agent 恒为 0.0；无
  provider 调用）。

边际 effect delta 为所有 rate/mean 指标（不含 `run_count`）输出。因为
是合成公开任务，确切的合成任务/run 计数可接受。

## Forbidden scanner（公开，fail-closed）

严格 forbidden 输出 scanner 在写入公开 JSON 前 fail-closed 运行。拒绝
forbidden dict key（`task_id`、`task_index`、`workspace_path`、
`workspace`、`file`、`filename`、`filepath`、`target_file`、
`wrong_cue_file`、`support_file`、`target_module`、`support_module`、
`distractor_module`、`test_module`、`path`、`span`、`start_line`、
`end_line`、`content_sha`、`content_hash`、`snippet`、`code`、
`source_code`、`patch`、`diff`、`test_output`、`test_log`、
`test_stdout`、`test_stderr`、`stdout`、`stderr`、`event_log`、
`events`、`log`、`trace`、`raw_event`、`stack_trace`、`traceback`、
`api_key`、`base_url`、`provider_key`、`secret`、`token`、`credential`、
`rows`、`per_run`、`predictions`、`candidates`、`content`、`source`、
`text`、`body` 等）出现在任意位置，并拒绝 value 模式：任意 URL（无 URL
允许列表）、32+ 字符 hex digest、secret-like 字符串
（api_key/base_url/provider_key/secret/password/credential）、带文件扩展
名的 path-like 字符串、`/tmp/` 工作区路径值、`task_N` 任务标识
value、patch/diff 标记（`---`、`+++`、`@@`）、堆栈跟踪
（`Traceback (most recent call last)`）、多行字符串、raw JSON 片段、
raw 行范围 `12-34`，以及 self-test sentinel。

scanner 仅对最终公开聚合 artifact 运行。内部 per-run event log（含路
径/patch/测试 stdout/stderr）仅保留在内存中，绝不对公开契约扫描，绝不
提交。

## Self-tests

- Artifact 身份字段（schema、claim、status、mode、phase、generated_by）。
- Safe true flags（7 个全为 true）；no-claim / no-runtime-change false
  flags（18 个全为 false）。
- 合成任务生成：确定性计数、符号、正确值、buggy 值。
- Pack builder：base 无文件 cue；primary 含 target file/symbol/
  operation cue；support 仅含 support_file cue；primary_plus_support
  含 target 和 support；distractor 仅含 wrong_cue_file；
  primary_plus_distractor 含 target 和 wrong_cue；primary+support
  和 primary+distractor 比 primary 更丰富；variant_count=6；
  effect_count=5。
- 真实工作区创建：target/support/distractor/test 文件存在于磁盘。
- 真实测试子进程：修复前测试失败（bug 存在）。
- 每个 variant 的 mock agent 行为：base no-op 测试失败；primary
  编辑正确文件测试通过 solve；support 编辑错误文件测试失败；
  primary_plus_support inspect support 编辑正确文件测试通过，2 次
  tool call；distractor 编辑错误文件测试失败，wrong_edits>base；
  primary_plus_distractor inspect distractor 编辑正确文件再编辑
  distractor 测试通过，wrong_edits>primary。
- mock 行为对 pack cue 的依赖：target_file cue 驱动正确文件编辑；
  wrong_cue_file 驱动错误文件编辑；primary solve rate 高于 base；
  support_only 和 distractor_only 不解题但编辑错误文件；
  primary_plus_distractor 仍解题。
- 聚合指标数学：run_count、solve_rate、tests_pass_rate、
  correct_file_rate、wrong_file_edits_mean、tool_calls_mean、
  cost_proxy_mean=0。
- 边际 effect：primary_context_vs_base solve_rate_delta 为正；
  support_context_vs_base 与 distractor_context_vs_base 的 solve_rate
  delta 为零但 wrong_file_edits_delta 为正；
  support_added_to_primary 的 solve_rate_delta 为零但 tool_calls 与
  context_tokens delta 为正；distractor_added_to_primary 的
  solve_rate_delta 为零但 wrong_file_edits、tool_calls 与
  context_tokens delta 为正；run_count 不在 delta 中。
- theory mapping：标记 E-utility proxy、S-conditional proxy、
  S-conditional distractor proxy；true/automated/human E/S calibration
  claimed 全为 false。
- forbidden scanner 拒绝：工作区路径、文件路径（target.py、
  support.py、distractor.py、test_target.py）、源码片段、context 文本、
  patch 标记、测试输出、task_id key、task_id value、raw event log、
  堆栈跟踪、content_sha key、hex digest value、provider auth field、
  endpoint URL field、sentinel canary、URL value、forbidden field name
  as value、行范围 value、多行 value、raw JSON 片段。
- forbidden scanner 允许：variant 名称（全部六个）、effect 名称（全部
  五个）、指标值、delta 指标值、工作区隔离 token、theory-mapping proxy
  token。
- fail-closed 生成：干净公开 report 不 raise；泄漏公开 report raise
  SystemExit；self-test 失败拒绝生成 artifact；失败 self-test 不携带成
  功状态。
- 公开 artifact 自扫描干净（无任何 forbidden key）。
- CLI 参数面：`--self-test`、`--out`、`--task-count` 是仅有的选项（加上
  `-h`/`--help`）；默认任务数在范围内。

## 验证

```text
python3 -m py_compile eval/f1_counterfactual_evidence_utility_smoke.py  => PASS
python3 eval/f1_counterfactual_evidence_utility_smoke.py --self-test  => PASS (162/162 checks)
python3 eval/f1_counterfactual_evidence_utility_smoke.py \
  --out artifacts/f1_counterfactual_evidence_utility/\
f1_counterfactual_evidence_utility_report.json  => PASS
  (status: counterfactual_evidence_utility_smoke_pass,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_micro_tasks, phase: F1,
   variant_count: 6, effect_count: 5,
   synthetic_task_count: 24, total_runs: 144,
   base_no_context: solve_rate=0.0, tests_pass_rate=0.0,
     wrong_file_edits_mean=0.0, tool_calls_before_first_edit_mean=0.0,
     context_tokens_mean=8.0,
   primary_only: solve_rate=1.0, tests_pass_rate=1.0,
     wrong_file_edits_mean=0.0, tool_calls_before_first_edit_mean=1.0,
     context_tokens_mean=24.0,
   support_only: solve_rate=0.0, tests_pass_rate=0.0,
     wrong_file_edits_mean=1.0, tool_calls_before_first_edit_mean=1.0,
     context_tokens_mean=20.0,
   primary_plus_support: solve_rate=1.0, tests_pass_rate=1.0,
     wrong_file_edits_mean=0.0, tool_calls_before_first_edit_mean=2.0,
     context_tokens_mean=40.0,
   distractor_only: solve_rate=0.0, tests_pass_rate=0.0,
     wrong_file_edits_mean=1.0, tool_calls_before_first_edit_mean=1.0,
     context_tokens_mean=16.0,
   primary_plus_distractor: solve_rate=1.0, tests_pass_rate=1.0,
     wrong_file_edits_mean=1.0, tool_calls_before_first_edit_mean=2.0,
     context_tokens_mean=32.0,
   marginal_effects:
     primary_context_vs_base: solve_rate_delta=+1.0,
       wrong_file_edits_mean_delta=+0.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+16.0,
     support_context_vs_base: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+1.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+12.0,
     distractor_context_vs_base: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+1.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+8.0,
     support_added_to_primary: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+0.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+16.0,
     distractor_added_to_primary: solve_rate_delta=+0.0,
       wrong_file_edits_mean_delta=+1.0,
       tool_calls_before_first_edit_mean_delta=+1.0,
       context_tokens_mean_delta=+8.0,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false,
   downstream_agent_value_proven: false,
   true_e_s_calibration_claimed: false,
   automated_e_s_full_calibration_claimed: false,
   human_e_s_calibration_claimed: false,
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
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 注意事项

- F1 是公开仅聚合反事实证据效用 smoke artifact。它是
  eval/诊断专用。它**不**改变 runtime、retriever、pack、backend 或
  default policy；它**不**改变 EvidenceCore 语义。它**不是**
  benchmark 结果、**不是** live 下游 agent 价值声明、**不是**真实 E/S
  校准声明、**不是** runtime-clean 通用算法声明、**不是** OOD 时间性
  声明、也**不是** QuIVer 系统声明。
- F1 使用**确定性 mock agent**（无 live LLM、无 provider 调用、无远
  程调用）。mock agent 的行为按设计依赖 pack：primary pack 含 target
  file/symbol/operation cue，support pack 携带 support cue，distractor
  pack 携带 wrong-cue file。这是因果 pack 效果 smoke，**不是** live
  agent 价值声明。
- F1 在代码中生成**确定性合成公开 micro bug 任务**。这些**不是**真
  实用户任务，也**不是**外部基准测试任务。因为是合成公开任务，确切的
  任务/run 计数可接受。
- F1 在每个 task+variant 的全新 `/tmp` 工作区中执行**真实文件编辑**和
  **真实子进程测试**（stdlib Python）。per-run event log、patch 和测试
  输出仅留在 `/tmp`，**绝不**提交或上传。提交的 artifact 仅含聚合
  counts/rates/means 和聚合边际 effect delta。
- F1 **不**证明下游 agent 价值。边际 effect delta 是设计 pack cue
  的确定性 mock 产物，**不是**任何 context variant 改善 live 下游
  agent 的证据。`downstream_agent_value_proven=false`。
- F1 **不**声明 live agent 泛化。确定性 mock agent 按构造平凡地泛化
  到合成任务族；这**不是** live agent 泛化声明。
  `live_agent_generalization_claimed=false`。
- F1 **不是**真实 E/S 校准。theory mapping 标签仅为命名/解释辅助；
  边际 delta 是从合成任务上的确定性 mock 聚合指标计算的，**不是**从
  真实人工/手动 E/S 标签或真实 E/S rubric 评分计算的。
  `true_e_s_calibration_claimed=false`、
  `automated_e_s_full_calibration_claimed=false`、
  `human_e_s_calibration_claimed=false`。
- 所有 no-claim / no-runtime-change flags 保持 false；诊断 flag
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  确定性 mock run flag（`counterfactual_context_variants_executed`、
  `deterministic_mock_agent`、`real_file_edits_performed`、
  `subprocess_tests_executed`、`marginal_utility_metrics_computed`）是
  仅有的额外 true flag。
- 未修改任何 runtime/retriever/pack/model/backend/default-policy 文
  件。无 promotion/default/runtime 声明变更。
