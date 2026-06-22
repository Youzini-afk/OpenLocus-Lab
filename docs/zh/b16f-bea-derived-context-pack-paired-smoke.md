# B16-F BEA-Derived Context Pack Live-Provider 下游 Paired Smoke（公开仅聚合 artifact）

> 本中文文档与英文文档 `docs/en/b16f-bea-derived-context-pack-paired-smoke.md`
> 一一对应。

## 范围与声明边界

B16-F 是第一个下游 live-provider paired smoke，将 **BEA v0.3-derived
context pack** 与 **same-budget BM25 context-pack 对照**（以及 sparse
对照）在有界合成 coding 任务上进行比较。主对比为 BEA v0.3 context
pack vs same-budget BM25 context pack；次对比为 BEA vs sparse 与 BM25 vs
sparse。

B16-F 使用八个固定白名单任务族。对于每个合成工作区，B16-F 构造
runtime-clean 候选特征（method source、rank、score/normalized score、
agreement count、span extent）。BM25 选择 same-budget BM25 prefix；BEA
应用冻结的 v0.3 风格策略，仅使用 runtime 可用特征。BEA selector **绝不**
读取 gold paths/lines/labels、任务答案、`correct_value` 或任何 per-task
结果。在合成公开 micro bug 任务上使用 live LLM provider（OpenAI 兼容）；
本地应用模型的结构化 edit action；运行真实 stdlib 测试；仅发布聚合行为
指标。

B16-F 明确**不是**下游 agent 价值证明，**不是** live agent 泛化证明，
**不是**外部基准测试结果，**不是**生产级 coding-agent 基准测试，**不
是**真实用户任务评估，**不是** method winner/default/promotion 声明，
**不是** calibration 声明，也**不是** runtime/retriever/pack/backend/
default-policy/EvidenceCore 语义改动。它**不**发布 prompt、response、
provider payload、base URL、API key、raw model 路由前缀、工作区路径、文
件路径、源码片段、patch/diff、测试输出、候选特征、BEA/BM25 action
trace、pack composition、raw event log 或 per-run 行。

- 声明级别（claim_level）：
  `bea_derived_context_pack_downstream_paired_smoke_only`。
- 模式（mode）：`public_aggregate_synthetic_task_family_matrix`；阶段
  （phase）为 `B16-F`。
- 状态枚举：成功时为
  `bea_derived_context_pack_paired_smoke_pass`；未启用远程时为
  `blocked_remote_not_enabled` / `unavailable_no_local_provider_env`；
  provider 调用失败时为 `provider_call_failed`；结构化 action 解析失败
  时为 `structured_action_parse_failed`；paired run 无法完成时为
  `paired_run_failed`；scanner 失败时为 `fail_forbidden_scan`。
- B16-F 是 **eval/诊断专用**。它**不是**基准测试结果，**不是**下游
  agent 价值声明，**不是** runtime-clean 通用算法声明，**不是** OOD
  时间性声明，**不是** QuIVer 系统声明，**不是** method winner/
  calibration/promotion/default/runtime/EvidenceCore 声明。

### BEA-3 -> B16-F 关系

```text
BEA-3 anchor/span/latency-aware retrieval policy smoke
  （仅检索侧；30 records x 9 arms；v0.3 在 file/MRR/success 上与 v0.2
   持平，仅有微小 span/quality-per-latency 信号）
-> B16-F BEA-derived context pack 下游 paired smoke
   （下游 live-provider；8 合成任务 x 3 arms = 默认 24 次 live 调用；
    BEA v0.3 context pack vs same-budget BM25 context pack vs sparse
    对照；相同的仅聚合安全模型；CI 通过不要求 BEA 改善）
```

B16-F 回应了 deep-research 指令的缺口：BEA 检索侧指标不够；BEA 必须在
live coding-agent 行为上测试。B16-F 仅通过在合成公开任务族矩阵上运行
微型 paired live LLM agent，搭配 BEA-derived vs same-budget BM25 context
pack，产出下游 live-provider paired smoke。

## Arms

B16-F 运行三个 paired arm，具有相同的 budget/tool 约束；仅 context
pack 不同：

1. **`control_sparse`**：仅任务 issue，最小 context；无 target file cue；
   无 decisive cue；candidate_count=0；小 token budget。agent 无法在
   无 decisive cue 时确定正确值/操作。
2. **`bm25_same_budget_context_pack`**：same-budget BM25 prefix pack。
   与 BEA arm 相同的 budget K。仅当 BM25 prefix 恰好包含 target.py 和
   support/config/cross_file.py 时才包含 target file cue + symbol cue
   + decisive cue。设计上，确定性候选特征使 BM25 prefix 排除
   target.py（较低 BM25 score），同时包含 distractor.py（最高 BM25
   score）和 support.py（第二高）。BM25 pack 因此提供 distractor（错误
   文件）+ support，但**不**提供 target file cue。
3. **`bea_v03_context_pack`**：冻结 BEA v0.3 anchor/span/latency 选中
   pack。与 BM25 相同的 budget K。BEA v0.3 使用 agreement anchor
   （target.py 在 bm25/regex/symbol 间 agreement=3）和 span tightness
   选择 target.py + support.py。BEA pack 因此提供 target file cue +
   symbol cue + decisive cue。

主公开 paired delta：BEA 减 same-budget BM25。次 delta：BEA 减 sparse
与 BM25 减 sparse。

## 已提交 artifact 与默认本地 run

已提交 artifact 位于
`artifacts/b16f_bea_derived_context_pack_paired_smoke/b16f_bea_derived_context_pack_paired_smoke_report.json`，
是公开仅聚合 smoke artifact。默认本地 no-env run 是真实的：无
`--allow-remote` 和所需 provider credential/model environment 时，
evaluator 输出 `blocked_remote_not_enabled` 或
`unavailable_no_local_provider_env`，live-run flag 为 false。它**不**是假通过。

手动 real-provider CI run（通过 `real-provider-benchmark.yml` stage
`b16f_bea_derived_context_pack_paired_smoke` 且
`enable_remote_models=true`、`task_count=8` 执行时）产生 24 次 live
provider 调用（8 任务 x 3 arms）。已提交 artifact 将在首次成功的手动
CI run 后更新为镜像该 run 的 sanitized aggregate report。

## 异构合成公开任务族矩阵设计

B16-F 在八个固定白名单任务族上生成确定性合成公开 micro bug 任务（默认
8 任务；`--task-count` 范围 4-12，硬上限 12；默认 24 次 live 调用 =
8 x 3 arms；最大 36 次 live 调用）。任务循环遍历八个族以保持矩阵
平衡。

### 任务族

每个族有不同的 decisive cue，由 BEA pack 通过
support/config/cross_file 模块作为 anchor 被包含而提供：

1. **`same_symbol_support_relation`** — target/distractor 共享符号，
   support relation 决定正确 edit。正确值 =
   `helper_constant * 2 + task_index`。
2. **`operation_ambiguity`** — target 符号可推断但操作有歧义（increment
   vs multiply）。正确操作为 multiply；正确值 = `base_value * 2`。
3. **`boundary_condition`** — 正确 edit 取决于 inclusive/exclusive 边界
   行为。正确值 = `limit_value - 1`。
4. **`helper_dependency_choice`** — 多个 helper 存在；正确 edit 需选择
   正确 helper relation。正确值 = `helper_b * 3`（非 `helper_a * 2`）。
5. **`config_or_test_mismatch`** — target.py 使用错误 config 值；正确
   值 = 来自 `config.py`（非 `support.py`）的 `config_value`。
6. **`distractor_file`** — distractor.py 有相同符号但错误值；target.py
   是正确文件。正确值 = `helper_constant + 5`。
7. **`nearby_wrong_function`** — target.py 有两个函数；bug 在其中一个，
   附近的函数有相似名。正确值 = `helper_constant * 2`。
8. **`cross_file_symbol`** — 正确值 = 来自另一模块（`cross_file.py`）
   的 helper。正确值 = `cross_value + 1`。

### 多文件工作区

对于每个 task 和 arm，B16-F 创建一个 fresh `/tmp` 工作区，包含四个
真实 Python 文件：`target.py`（有 bug 的函数）、`distractor.py`（同名
decoy）、`support.py`/`config.py`/`cross_file.py`（helper 常量）和
`test_target.py`（导入 target AND support；断言正确的族特定关系）。
harness 实际编辑文件并运行子进程测试。

## Runtime-clean 候选特征与 BEA v0.3 策略

对于每个合成任务，B16-F 生成 6 个确定性 runtime-clean 候选特征。每个
候选包含：path、method、rank、score、normalized_score、methods set、
agreement count、start_line、end_line、span_extent。候选特征中不存在
gold paths、`correct_value`、task_family decisive cue 或任何私有答案。

设计：`target.py` agreement=3（所有 method 都返回它），MEDIUM BM25
score（故意低于 support），tight span。`distractor.py` agreement=1
（仅 bm25），HIGH BM25 score，tight span。
`support.py`/`config.py`/`cross_file.py` agreement=2（bm25+symbol），
第二高 BM25 score，tight span。这使得：

- **BEA v0.3**（budget=2）：选择 `target.py`（agreement=3，anchor
  eligible）+ `support.py`（agreement=2，anchor eligible，新文件）。
  BEA pack 包含 target + support → target file cue + decisive cue。
- **BM25 same-budget prefix**（K=2）：选择 `distractor.py`（最高 BM25
  score）+ `support.py`（第二高）。BM25 pack 排除 `target.py` → 无
  target file cue。LLM 可能编辑 `distractor.py`（错误文件）或无法确定
  正确值。
- **Sparse control**：无候选，无 cue。

BEA v0.3 冻结策略使用：agreement（权重 0.30）、bm25_norm（0.20）、
diversity（0.20）、query/path overlap（0.15）、span tightness（0.15）、
anchor file support（0.10）、anchor boost（0.35 用于 anchor slot）、
risk penalty（-0.25）、weak-support penalty（-0.20）、duplication
penalty（-0.30）、marginal-priority early stop（阈值 0.05）。所有权重
为冻结常量，**不**从结果调优。Anchor count = min(2, budget)。

### BEA runtime-clean 不变量

BEA selector 仅消费 runtime-clean 候选特征。它**绝不**读取 gold paths、
`correct_value`、task_family decisive cue 或任何私有答案。用错误值
污染 `correct_value` **不**会改变 BEA 选择，因为策略完全忽略该字段。
该不变量在 self-test 中验证。

## Live provider 约束

- 确切 provider credential/model env 名称只保留在 workflow/config wiring 中，不写入研究正文。
- 仅当 `--allow-remote`、remote opt-in gate、必要时的 workflow-dispatch gate，
  以及 provider credential/model configuration 均存在时才进行远程调用。
- artifact/docs 中无 raw base URL、API key、prompt、response、源码片段、
  patch/diff、stdout/stderr、工作区路径、候选特征、BEA action trace、
  pack composition 或 provider payload。
- live LLM prompt 可包含微小合成/公开源码片段（有 bug 的 target 模块
  + support 模块）和族特定 decisive cue（仅当 treatment pack 携带时）。
  prompt **绝不**持久化（仅写入 `/tmp` 下的私有 event JSONL）。
- 结构化 edit action schema 为白名单：action 必须为
  `replace_return_value`、`choose_helper_constant` 或 `no_op`；file
  必须为 `target.py`；无任意路径，无 shell。distractor 和 support 文件
  **不可**编辑。
- 若 provider 返回 `usage`，则 usage 诊断可包含聚合 prompt/completion/
  total token 计数；否则标记为不可用。
- Cost 仅为 `cost_proxy`（始终 0.0）；无 live 价格推断。
- 研究 docs/artifacts 记录不含路由前缀的规范化 model 显示名（例如
  `Kimi-K2.7-Code`，非 raw 路由前缀），除非记录确切 workflow/env
  白名单。

## 私有 artifact（仅 /tmp 下；绝不提交/上传）

对于每个 task x arm，B16-F 写入：

- **私有 SCORE JSONL**（每个 task x arm 一行 = 默认 24 行）：
  candidate_features（路径、score、rank、method、agreement、span）、
  bea_action_trace、bea_budget_trace、bea_stop_reason、
  selected_candidates（pack composition）、score_outcome（per-arm
  metrics）、latency_ms、tokens、provider_calls、failure_reason。
- **私有 event JSONL**（每个 task x arm 一行 = 默认 24 行）：prompt、
  response、parsed_action、patch、test_stdout、test_stderr、
  test_returncode、provider_metadata、failure_reason。

两者仅写入 `/tmp` 下（或 gitignored `runs/` 下的显式忽略私有路径）。
私有路径**绝不**在公开 artifact/docs/CI 中序列化。

## CLI

```bash
python3 -m py_compile eval/b16f_bea_derived_context_pack_paired_smoke.py
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py --self-test
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py \
    --out artifacts/b16f_bea_derived_context_pack_paired_smoke/\
b16f_bea_derived_context_pack_paired_smoke_report.json
# Live opt-in（仅当 provider credential/model environment 可用且安全时）：
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py \
    --allow-remote --task-count 8 \
    --out artifacts/b16f_bea_derived_context_pack_paired_smoke/\
b16f_bea_derived_context_pack_paired_smoke_report.json
```

默认模式（无 `--allow-remote` 或无 provider credential/model env）：若提供 `--out`，则
写入真实的 `unavailable_no_local_provider_env` 或
`blocked_remote_not_enabled` 聚合报告；无 provider 调用；live-run flag
为 false，但 `aggregate_only_public_artifact=true` 和
`diagnostic_only=true` 除外。

CLI 参数：`--self-test`、`--out`、`--allow-remote`、
`--require-workflow-dispatch`、`--task-count`、`--private-score-dir`、
`--private-event-dir`。未知/私有外观参数被拒绝，并输出不含私有路径或
basename 的通用 `invalid arguments` 消息（SafeArgumentParser 模式）。

`--self-test` 运行无网络 self-test，使用 fake provider response；覆盖
remote gating、env preservation、missing env unavailable 路径、provider
诊断 redaction、候选生成器（runtime-clean；无 gold 字段）、BEA v0.3 策略
（接受 target+support；忽略 gold 污染）、BM25 same-budget prefix（排除
target）、pack builder（control 缺 cue；BEA 有 cue；BM25 缺 target
cue）、所有八个族的 fake valid edit apply/test、invalid JSON count、
固定 provider error category、action path/action 限制（包括 distractor/
support 文件拒绝）、所有八个任务族、treatment/control decisive-cue 差
异、私有 SCORE/event writer（行写入 /tmp；有效 JSON；私有字段存在）、
records-shaped family matrix、scanner 禁止 key/value（包括 BEA 私有
key：candidate_features、selected_candidates、bea_action_trace、
bea_budget_trace、score_outcome）、no-claim flag 和 fail-closed
scanner 行为。

## Provider client helper

B16-F 复用 B16-C/D/E 的 `eval/provider_client.py`（未修改）。它是一个
最小的 OpenAI 兼容 chat helper，返回安全的 `ProviderCallResult` 对象，
仅暴露聚合计数（calls attempted/succeeded/failed、invalid_json、
timeout、latency、numeric provider `usage`（若存在）、固定 failure-
category enum token、HTTP status）。Raw prompt、message、response、
base URL、API key 和 provider payload **绝不**在公开诊断中返回。

## Artifact identity（默认已提交 artifact）

已提交 artifact 位于
`artifacts/b16f_bea_derived_context_pack_paired_smoke/b16f_bea_derived_context_pack_paired_smoke_report.json`，
是公开仅聚合 smoke artifact。Identity/边界字段：

- `schema_version` =
  `b16f_bea_derived_context_pack_paired_smoke.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`、`model_display_category`（规范化；无路由前缀）。
- Safe true flag（仅 live run 时；恰好这些，全为 true）：
  `downstream_agent_runs_performed`、`live_llm_agent`、
  `provider_calls_made`、`remote_provider_calls_made`、
  `paired_run_executed`、`synthetic_task_family_matrix_used`、
  `real_file_edits_performed`、`real_test_commands_executed`、
  `agent_behavior_metrics_evaluated`、
  `bea_v03_context_pack_executed`、
  `bm25_same_budget_context_pack_executed`、
  `private_score_records_written`、
  `private_event_records_written`、
  `aggregate_only_public_artifact`、`diagnostic_only`。
- 在 unavailable/blocked 状态时，live-run flag 为 false，但
  `aggregate_only_public_artifact=true` 和 `diagnostic_only=true` 除外。
- Always-false no-claim flag：
  `downstream_agent_value_proven`、
  `live_agent_generalization_claimed`、`promotion_ready`、
  `default_should_change`、
  `external_benchmark_performance_claimed`、`real_user_task_claimed`、
  `runtime_behavior_changed`、`retriever_changed`、
  `pack_builder_changed`、`backend_changed`、
  `default_policy_changed`、`evidencecore_semantics_changed`、
  `method_winner_claimed`、`calibration_claimed`。
- `input_summary`：`synthetic_task_count`、`run_count_per_arm`、
  `total_runs`、`arms`（`[control_sparse,
  bm25_same_budget_context_pack, bea_v03_context_pack]`）、
  `task_families`（八个白名单族名）、`paired_design`（`true`）、
  `workspace_isolation`（`fresh_tmp_per_task_arm`）、
  `transient_workspace_outputs_only`（`true`）、
  `designed_causal_subset`（`true`）、`task_family_matrix`（`true`）、
  `primary_contrast`（
  `bea_v03_context_pack_vs_bm25_same_budget_context_pack`）。
- `arm_results`：固定 record 列表
  `{arm, metrics, provider_summary, failure_category_counts}`。
  Metrics：`run_count`、`solve_rate`、`tests_pass_rate`、
  `patch_apply_rate`、`invalid_json_rate`、`no_op_rate`、
  `provider_failure_rate`、`context_tokens_mean`、
  `prompt_tokens_total`、`completion_tokens_total`、
  `latency_seconds_mean`、`cost_proxy_total`、
  `correct_file_before_first_edit_rate`、`wrong_file_edit_rate`。
- `paired_deltas`：固定 record 列表
  `{baseline_arm, treatment_arm, metric, delta}`。三个对比：
  BEA vs BM25（主）、BEA vs sparse（次）、BM25 vs sparse（次）。
- `task_family_results`：固定 record 列表
  `{task_family, arm, run_count, solve_rate, tests_pass_rate,
  correct_file_before_first_edit_rate, wrong_file_edit_rate}`。
  仅出现白名单族名。无 task ID。
- `family_signal_summary`：仅主对比（BEA vs BM25）的聚合计数：
  `families_evaluated`、`families_with_positive_solve_delta`、
  `families_with_zero_solve_delta`、
  `families_with_negative_solve_delta`。
- `honest_signals`：`context_pack_signal_observed`（bool）、
  `primary_solve_rate_delta`（number）、
  `primary_tests_pass_rate_delta`（number）、
  `primary_wrong_file_edit_rate_delta`（number）、
  `families_evaluated`（int）、`families_with_positive_solve_delta`
  （int）、`families_with_zero_solve_delta`（int）、
  `families_with_negative_solve_delta`（int）。这些是诊断 smoke
  结果，**绝不**是 promotion/default/value 声明。
- `private_score_manifest`：仅聚合
  `{records_written, record_count, schema_version, manifest_hash,
  storage_class, path_publicly_serialized=false}`。
- `private_event_manifest`：仅聚合
  `{records_written, record_count, schema_version, manifest_hash,
  storage_class, path_publicly_serialized=false}`。
- `self_test_checks_total`、`self_test_checks_passed` 和 `self_test_passed`
  计数（公开 artifact 不发布逐项 self-test 名称，以避免 scanner/audit 噪声）。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

## CI 通过标准

CI 通过意味着：

```text
live run 完成 + 隐私 scan 通过 + artifact 诚实
```

CI 通过**不**要求 BEA 改善。零或负 BEA-vs-BM25 delta 若诚实记录则是
有效实证结果。三个 arm 全部解决或全部失败是有效实证结果。某些族可能
显示正 BEA-vs-BM25 delta，其他显示零或负；都是有效实证结果。

## 禁止 scanner（公开，fail-closed）

严格禁止输出 scanner 在写入公开 JSON 前 fail-closed 运行。拒绝任何位置
的禁止 dict key（`prompt`、`prompts`、`message`、`messages`、
`response`、`responses`、`raw_response`、`request`、`request_body`、
`provider_payload`、`url`、`base_url`、`endpoint`、`api_key`、`token`、
`secret`、`authorization`、`bearer`、`workspace`、`workspace_path`、
`path`、`file`、`target_file`、`target_module`、`distractor_module`、
`support_module`、`test_module`、`snippet`、`code`、`source`、
`patch`、`diff`、`test_output`、`stdout`、`stderr`、`event_log`、
`stack_trace`、`content_sha`、`task_id`、`per_run`、`model_id_raw`、
`model_id`、`candidate_features`、`selected_candidates`、
`bea_action_trace`、`bea_budget_trace`、`bea_stop_reason`、
`score_outcome`、`accepted_candidates`、`action_trace`、
`budget_trace`、`phase_run_id`、`provider_metadata` 等）和 value 模式：
任何 URL（无 URL 白名单）、32+ 字符 hex digest、secret-like 字符串、
带文件扩展名的 path-like 字符串、`/tmp/` 工作区路径 value、`task_N`
task 标识符 value、patch/diff 标记、stack trace、多行字符串、raw JSON
片段、raw line range、raw model 路由前缀和 self-test sentinel。

scanner 仅对最终公开聚合 artifact 运行。内部 per-run event log 和
SCORE 行（包含 path/patch/test stdout/stderr/候选特征/BEA action
trace）仅保留在 `/tmp` 下，**绝不**对公开契约 scan，**绝不**提交。

## Self-test

- Artifact identity 字段（schema、claim、status enum、mode、phase、
  generated_by、primary_contrast、arms count=3、families count=8、
  默认 task count=8、max live calls=36）。
- Always-false no-claim flag（全部 14 个 false）。
- Live-run flag gating（unavailable report：live-run flag false；live
  report：live-run flag true）。
- 八个任务族生成（全部八个存在；8 任务平衡；族特定确定性正确值）。
- 每族多文件工作区（target/distractor/support/test；同名 distractor；
  修复前测试失败）。
- 候选生成器（6 候选；target agreement=3；distractor agreement=1；
  support agreement=2；distractor BM25 > target BM25；无 gold 字段）。
- BEA v0.3 策略（接受 2 候选；接受 target 作为 anchor；接受 support；
  **不**先接受 distractor；action/budget trace 非空；stop reason 设置；
  mechanism summary 存在；gold 污染下选择不变）。
- BM25 same-budget prefix（计数匹配 K；包含 distractor；排除 target）。
- Pack builder（control 缺所有 cue；BEA 有 target/symbol/decisive cue；
  BM25 缺 target file cue；same budget K 匹配；BEA 比 control 丰富）。
- 每族 decisive cue text（非空；无 raw 路由前缀）。
- 每族 fake valid BEA response（正确文件 edit；无错误文件；测试通过；
  solve=true；provider 调用成功；task_family/arm 记录）。
- Fake invalid JSON response（解析失败）：无 edit；测试失败；run result
  中无 raw response。
- 私有 SCORE/event writer（各 9 行写入 /tmp；有效 JSON；私有字段存在：
  candidate_features、selected_candidates、score_outcome、prompt、
  response、test_stdout）。
- Edit action 限制：禁止文件拒绝；禁止 action 拒绝；distractor.py 拒绝；
  support.py 拒绝；缺少 symbol 拒绝；非 int new_return_value 拒绝；
  非对象拒绝；valid action 接受；`choose_helper_constant` 接受；
  `no_op` 接受。
- 聚合 metrics + paired delta（3 对比 x N metrics；主对比存在；BEA
  解决/BM25 失败时 primary solve_rate delta 正；次对比存在）+ family
  results（全部八个族；每族三个 arm）+ family signal summary + honest
  signals（正 delta 时 context_pack_signal_observed true；零 delta 时
  false）。
- Model 显示规范化（剥离路由前缀；空返回 `unavailable`；剥离不安全
  字符）。
- Env preservation self-test（probe 恢复 env；无网络 probe 不清除 live
  provider gate/env state）。
- 私有 manifest hash 稳定（SCORE 和 event manifest hash 稳定且不同）。
- Scanner 拒绝：工作区路径、文件路径、源码片段、patch 标记、测试输出、
  task_id key、raw event log、stack trace、content_sha key、hex
  digest、provider auth 字段、endpoint URL 字段、raw 路由前缀、URL
  value、prompt key、response key、messages key、provider_payload key、
  candidate_features key、selected_candidates key、bea_action_trace key、
  bea_budget_trace key、score_outcome key、sentinel canary。
- Scanner 允许：arm 名、task family 名、paired_deltas record、family
  results record、model 显示类别、honest signal 字段、
  private_score_manifest、private_event_manifest、failure category
  token、primary_contrast。
- Fail-closed 生成：clean 公开 report 不 raise；leaked 公开 report
  raise SystemExit；self-test 失败拒绝 artifact 生成。
- 公开 artifact self-scan clean（无任何禁止 key）。
- CLI 参数表面：`--self-test`、`--out`、`--allow-remote`、
  `--require-workflow-dispatch`、`--task-count`、`--private-score-dir`、
  `--private-event-dir` 是唯一选项（加 `-h`/`--help`）；默认 task
  count 在范围内。
- Remote gating：`allow_remote=False` 时 blocked；env 缺失时
  unavailable。
- 三 arm 结构：control 第一、BM25 第二、BEA 第三；默认 total runs = 24。

## 验证

```text
python3 -m py_compile eval/b16f_bea_derived_context_pack_paired_smoke.py  => PASS
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py --self-test  => PASS (352/352 checks)
python3 eval/b16f_bea_derived_context_pack_paired_smoke.py \
  --out artifacts/b16f_bea_derived_context_pack_paired_smoke/\
b16f_bea_derived_context_pack_paired_smoke_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-F,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   synthetic_task_family_matrix_used: false,
   bea_v03_context_pack_executed: false,
   bm25_same_budget_context_pack_executed: false,
   private_score_records_written: false,
   private_event_records_written: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   default_should_change: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false, real_user_task_claimed: false,
   method_winner_claimed: false, calibration_claimed: false)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

本地 no-env 验证路径是真实的且 blocked/unavailable。

## 注意事项

- B16-F 是公开仅聚合 BEA-derived context pack 下游 paired smoke
  artifact。它是 eval/诊断专用。它**不**改变 runtime、retriever、pack、
  backend 或 default policy；它**不**改变 EvidenceCore 语义。它**不**
  是基准测试结果，**不**是下游 agent 价值声明，**不**是 runtime-clean
  通用算法声明，**不**是 OOD 时间性声明，**不**是 QuIVer 系统声明，
  **不**是 method winner/calibration/promotion/default/runtime/
  EvidenceCore 声明。
- B16-F 仅当 `--allow-remote` + remote opt-in gate + provider
  credential/model env 都设置时使用 **live LLM provider**（OpenAI 兼容）。默认本地
  no-env 路径保持真实（`blocked_remote_not_enabled`）。它**不**是假
  通过。
- B16-F **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- B16-F **不**声称 live agent 泛化。
  `live_agent_generalization_claimed=false`。
- B16-F **不**发布 prompt、response、provider payload、base URL、API
  key、raw model 路由前缀、工作区路径、文件路径、源码片段、patch/diff、
  测试输出、候选特征、BEA action trace、pack composition、raw event
  log 或 per-run 行。per-run event log、prompt、response、候选特征、
  BEA action trace 和测试输出仅保留在 `/tmp` 下，**绝不**提交或上传。
- BEA v0.3 context pack selector 仅使用 runtime-clean 候选特征。它
  **绝不**读取 gold path、`correct_value`、task_family decisive cue
  或任何私有答案。这通过 gold-tainting 不变量在 self-test 中验证。
- 已提交 artifact 仅包含 records-shaped 容器中的聚合计数/率/均值。无
  raw model 路由前缀发出；仅记录规范化的 `model_display_category`。
- `honest_signals` 和 `family_signal_summary` 是诊断 smoke 结果，
  **绝不**是 promotion/default/value 声明。零或负 BEA-vs-BM25 delta
  是有效实证结果。某些族可能显示正 delta，其他显示零或负；都是有效
  实证结果。
- 所有 no-claim/no-runtime-change flag 保持 false；诊断 flag
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  live-run flag 仅在 live run 实际执行时为 true。
- 无 runtime/retriever/pack/model/backend/default-policy 文件被修改。
  无 promotion/default/runtime 声明改变。
