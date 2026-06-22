# B16-H File-Choice Atom Ablation Live-Provider Smoke（公开仅聚合 artifact）

> 本中文文档与英文文档 `docs/en/b16h-file-choice-atom-ablation.md`
> 一一对应。

## 范围与声明边界

B16-H 解决 B16-G 的主要 confound：B16-G 的结构化 action schema 和
prompt 强制编辑 `target.py`，因此 `support_only` 解决 8/8 并不能证明
support atom 单独能引导文件选择。B16-H 在保持安全结构化 action 和私有
trace 的同时移除了该 confound。

B16-H 移除文件选择 confound：

* prompt 不再说 "only use target.py"；
* 无全局 `ALLOWED_EDIT_FILES = {target.py}` 集合；
* validator 仅接受 per-task 安全文件集：target module、distractor
  module 以及 support/config/cross-file module（若存在）；
* 绝不接受任意路径；
* chosen file 仅记录在 `/tmp` 下的私有 event/SCORE JSONL 中；
* 公开仅暴露聚合文件选择率（selected_target_file_rate、
  selected_distractor_file_rate、selected_support_file_rate）。不发布
  实际文件名。

B16-H 使用八个固定白名单任务族（复用 B16-F/B16-G 以保持可比性）。在
合成公开 micro bug 任务上使用 live LLM provider（OpenAI 兼容）；本地
应用模型的结构化 edit action；运行真实 stdlib 测试；仅发布聚合行为
指标。

B16-H 明确**不是**下游 agent 价值证明，**不是** live agent 泛化证明，
**不是**外部基准测试结果，**不是**生产级 coding-agent 基准测试，**不
是**真实用户任务评估，**不是** method winner/default/promotion 声明，
**不是** calibration 声明，**不是** BEA 优越性声明，也**不是**
runtime/retriever/pack/backend/default-policy/EvidenceCore 语义改动。
它**不**发布 prompt、response、provider payload、base URL、API key、
raw model 路由前缀、工作区路径、文件路径、源码片段、patch/diff、测试
输出、atom composition、chosen file 名、raw event log 或 per-run 行。

- 声明级别（claim_level）：
  `file_choice_atom_ablation_downstream_smoke_only`。
- 模式（mode）：`public_aggregate_synthetic_task_family_matrix`；阶段
  （phase）为 `B16-H`。
- 状态枚举：成功时为
  `file_choice_atom_ablation_smoke_pass`；未启用远程时为
  `blocked_remote_not_enabled` / `unavailable_no_local_provider_env`；
  provider 调用失败时为 `provider_call_failed`；结构化 action 解析失败
  时为 `structured_action_parse_failed`；paired run 无法完成时为
  `paired_run_failed`；scanner 失败时为 `fail_forbidden_scan`。
- B16-H 是 **eval/诊断专用**。它**不是**基准测试结果，**不是**下游
  agent 价值声明，**不是** runtime-clean 通用算法声明，**不是** OOD
  时间性声明，**不是** QuIVer 系统声明，**不是** method winner/
  calibration/promotion/default/runtime/EvidenceCore 声明，也**不是**
  BEA 优越性声明。
- 文档对任何 sufficiency 发现标明 "在此有界合成 file-choice 切片上"。

### B16-G -> B16-H 关系

```text
B16-G context-pack atom ablation 下游 smoke
  （5 arm：control_sparse、target_only、support_only、
   distractor_plus_support、target_plus_support；
   8 任务 x 5 arm = 40 live 调用；
   CONFOUND：prompt/validator 强制 file=target.py，因此 support_only
   解决 8/8 并不能证明 support atom 单独能引导文件选择）
-> B16-H file-choice atom ablation 下游 smoke
   （5 arm：control_sparse、file_choice_target_only、
    file_choice_support_only、file_choice_distractor_plus_support、
    file_choice_target_plus_support；
    8 任务 x 5 arm = 默认 40 live 调用；
    CONFOUND 已移除：agent 在 per-task 安全文件中选择；
    chosen file 仅记录在私有 trace 中；公开 artifact 仅聚合文件选择率；
    CI 通过不要求任何 atom 获胜）
```

## Arms

B16-H 运行五个固定 arm，具有相同的 budget/tool 约束；仅 atom composition
不同（与 B16-G 相同，但带 `file_choice_` 前缀以标记 confound 移除）：

1. **`control_sparse`**：仅任务 issue，最小 context；无 atom。
2. **`file_choice_target_only`**：target file cue + target symbol cue；
   无 support module，无 decisive cue。
3. **`file_choice_support_only`**：support module cue + decisive cue；无
   target file cue，无 symbol cue。
4. **`file_choice_distractor_plus_support`**：distractor file cue +
   support module cue + decisive cue；无 target file；wrong-file cue。
5. **`file_choice_target_plus_support`**：target file cue + target
   symbol cue + support module cue + decisive cue（full pack）。

主对比：

- `file_choice_target_plus_support` vs
  `file_choice_support_only`
- `file_choice_target_plus_support` vs
  `file_choice_distractor_plus_support`
- `file_choice_target_only` vs `file_choice_support_only`

次对比：每个 context arm vs `control_sparse`。

## 文件选择 confound 移除（关键 harness 改动）

与 B16-G（强制 `ALLOWED_EDIT_FILES = {target.py}` 且 prompt 说 "only use
target.py"）不同，B16-H：

- 通过 `_safe_edit_files(task)` 计算 per-task 安全文件集：target
  module + distractor module + support/config/cross-file module。
- prompt 列出 per-task 安全文件集，让 agent 选择编辑哪个文件。它**不**
  说 "only use target.py"。
- validator 检查文件是否在 per-task 安全文件集中，而非全局集合。agent
  可以编辑 distractor.py 或 support module（不会解决任务）。
- chosen file 仅记录在 `/tmp` 下的私有 SCORE/event JSONL 中（作为
  `chosen_file`）。
- 公开 artifact 仅暴露聚合文件选择率：`selected_target_file_rate`、
  `selected_distractor_file_rate`、`selected_support_file_rate`。不
  发布实际文件名。

这就是文件选择 confound 移除。B16-H 现在可以确定 support atom 单独
是否足以引导文件选择（而非仅在文件被强制时足以解决）。

## 已提交 artifact 与默认本地 run

已提交 artifact 位于
`artifacts/b16h_file_choice_atom_ablation/b16h_file_choice_atom_ablation_report.json`，
是公开仅聚合 smoke artifact。默认本地 no-env run 是真实的：无
`--allow-remote` 和所需 provider credential/model environment 时，evaluator 输出
`blocked_remote_not_enabled` 或 `unavailable_no_local_provider_env`，live-run
flag 为 false。它**不**是假通过。

手动 real-provider CI run（通过 `real-provider-benchmark.yml` stage
`b16h_file_choice_atom_ablation` 且 `enable_remote_models=true`、
`task_count=8` 执行时）产生 40 次 live provider 调用（8 任务 x 5
arm）。已提交 artifact 将在首次成功的手动 CI run 后更新为镜像该 run
的 sanitized aggregate report。

## 聚合 metrics

公开 artifact 包含仅聚合 record：

- `arm_results`（per-arm metrics）
- `paired_deltas`（7 对比：3 主 + 4 次）
- `task_family_results`
- `mechanism_summary_records`
- `private_score_manifest`
- `private_event_manifest`
- `forbidden_scan`

Metrics 包括：solve_rate、tests_pass_rate、patch_apply_rate、
correct_file_before_first_edit_rate、wrong_file_edit_rate、
selected_target_file_rate、selected_distractor_file_rate、
selected_support_file_rate、no_op_rate、invalid_json_rate、
provider_failure_rate、context_tokens_mean、prompt_tokens_total、
completion_tokens_total、latency_seconds_mean、cost_proxy_total。

机制摘要 record（仅计数）：

- `support_only_sufficient_with_file_choice_count`：
  `file_choice_support_only` 解决的任务数（support atom 单独在 agent
  必须选择文件时也足够）。
- `target_atom_required_with_file_choice_count`：
  `file_choice_target_only` 解决但 `file_choice_support_only` 未解决
  的任务数（target atom 对文件选择是必需的）。
- `distractor_hurts_with_file_choice_count`：
  `file_choice_distractor_plus_support` 未解决但
  `file_choice_target_plus_support` 解决的任务数（distractor cue 在
  文件选择下导致失败）。
- `wrong_file_selection_count`：agent 在所有 context arm 中选择非
  target 文件（distractor 或 support）的任务数。
- `all_arms_solved_count`：所有 5 个 arm 解决的任务数。
- `sparse_solved_count`：control_sparse 解决的任务数。

## 私有 artifact（仅 /tmp 下；绝不提交/上传）

对于每个 task x arm，B16-H 写入：

- **私有 SCORE JSONL**（每个 task x arm 一行 = 默认 40 行）：
  atom_composition、chosen_file、score_outcome（per-arm metrics）、
  latency_ms、tokens、provider_calls、failure_reason。
- **私有 event JSONL**（每个 task x arm 一行 = 默认 40 行）：prompt、
  response、parsed_action、chosen_file、patch、test_stdout、
  test_stderr、test_returncode、provider_metadata、failure_reason。

两者仅写入 `/tmp` 下（或 gitignored `runs/` 下的显式忽略私有路径）。
私有路径**绝不**在公开 artifact/docs/CI 中序列化。

## CLI

```bash
python3 -m py_compile eval/b16h_file_choice_atom_ablation.py
python3 eval/b16h_file_choice_atom_ablation.py --self-test
python3 eval/b16h_file_choice_atom_ablation.py \
    --out artifacts/b16h_file_choice_atom_ablation/\
b16h_file_choice_atom_ablation_report.json
# Live opt-in（仅当 provider credential/model environment 可用且安全时）：
python3 eval/b16h_file_choice_atom_ablation.py \
    --allow-remote --task-count 8 \
    --out artifacts/b16h_file_choice_atom_ablation/\
b16h_file_choice_atom_ablation_report.json
```

默认模式（无 `--allow-remote` 或无 provider credential/model env）：若提供 `--out`，则
写入真实的 `unavailable_no_local_provider_env` 或
`blocked_remote_not_enabled` 聚合报告；无 provider 调用；live-run flag
为 false，但 `aggregate_only_public_artifact=true` 和
`diagnostic_only=true` 除外。

CLI 参数：`--self-test`、`--out`、`--allow-remote`、
`--require-workflow-dispatch`、`--task-count`、`--private-score-dir`、
`--private-event-dir`。未知/私有外观参数被拒绝，并输出通用
`invalid arguments` 消息（SafeArgumentParser 模式）。

## Provider client helper

B16-H 复用 B16-C/D/E/F/G 的 `eval/provider_client.py`（未修改）。最小
OpenAI 兼容 chat helper，返回安全的 `ProviderCallResult`，仅暴露聚合
计数。Raw prompt、message、response、base URL、API key 和 provider
payload **绝不**在公开诊断中返回。

## CI 通过标准

CI 通过意味着：

```text
live run 完成 + 隐私 scan 通过 + artifact 诚实
```

CI 通过**不**要求任何 atom 获胜。任何对比的零或负 delta 若诚实记录
则是有效实证结果。五个 arm 全部解决或全部失败是有效实证结果。

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
`model_id`、`atom_composition`、`atom_trace`、`action_trace`、
`score_outcome`、`phase_run_id`、`provider_metadata`、
`chosen_file`、`file_choice`、`candidate_features`、
`selected_candidates` 等）和 value 模式：任何 URL（无 URL 白名单）、
32+ 字符 hex digest、secret-like 字符串、带文件扩展名的 path-like
字符串（包括 `target.py`、`distractor.py`）、`/tmp/` 工作区路径 value、
`task_N` task 标识符 value、patch/diff 标记、stack trace、多行字符串、
raw JSON 片段、raw line range、raw model 路由前缀和 self-test sentinel。

scanner 仅对最终公开聚合 artifact 运行。内部 per-run event log 和
SCORE 行（包含 path/patch/test stdout/stderr/atom composition/chosen
file）仅保留在 `/tmp` 下，**绝不**对公开契约 scan，**绝不**提交。

## Self-test

B16-H 保持 self-test 聚焦（仅计数公开摘要；详细 check 列表**不**发布到
公开 artifact）。self-test 覆盖：

- Artifact identity 字段（schema、claim、status enum、mode、phase、
  generated_by、arms count=5、families count=8、默认 task count=8、
  max live calls=60、primary/secondary 对比计数、
  `file_choice_confound_removed` flag、无全局 `ALLOWED_EDIT_FILES`
  集合）。
- Always-false no-claim flag（全部 15 个 false，包括
  `bea_superiority_claimed`）。
- Live-run flag gating。
- 八个任务族生成（全部八个存在；8 任务平衡）。
- 每族多文件工作区 + 安全文件集（target + distractor + support 都在
  安全集中）。
- Pack builder atom per arm。
- Atom composition 私有列表。
- 文件选择 validator（拒绝 `evil.py`；接受 `target.py`、
  `distractor.py`、`support.py`、config 族 `config.py`、cross_file 族
  `cross_file.py`；拒绝禁止 action；接受 `no_op`）。
- Chosen-file 分类（target/distractor/support/none）。
- 私有 SCORE/event writer + fake response（tps 解决选 target；so 错误选
  distractor；control no_op；invalid JSON；各 4 行；有效 JSON；私有字段
  存在：atom_composition、chosen_file、score_outcome、prompt、
  response）。
- 聚合 metrics + 文件选择率（selected_target_file_rate、
  selected_distractor_file_rate、selected_support_file_rate 均存在）
  + paired delta（7 对比 x 17 metrics；3 主对比均存在）+ mechanism
  summary（6 record：
  support_only_sufficient_with_file_choice_count、
  target_atom_required_with_file_choice_count、
  distractor_hurts_with_file_choice_count、
  wrong_file_selection_count、all_arms_solved_count、
  sparse_solved_count）+ honest signals + family results。
- Model 显示规范化。
- Env preservation self-test。
- 私有 manifest hash 稳定且不同。
- Scanner 拒绝（包括 `chosen_file`、`file_choice`、
  `target.py`/`distractor.py` value 泄漏）。
- Scanner 允许（arm 名、paired_deltas、mechanism_records、model 显示
  类别、私有 manifest、文件选择率、honest signals）。
- Fail-closed 生成。
- 公开 artifact self-scan clean（无任何禁止 key，包括 `chosen_file`
  和 `file_choice`）。
- CLI 参数表面。
- Remote gating。
- 五 arm 结构；默认 total runs = 40。

## 验证

```text
python3 -m py_compile eval/b16h_file_choice_atom_ablation.py  => PASS
python3 eval/b16h_file_choice_atom_ablation.py --self-test  => PASS (266/266 checks)
python3 eval/b16h_file_choice_atom_ablation.py \
  --out artifacts/b16h_file_choice_atom_ablation/\
b16h_file_choice_atom_ablation_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-H,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   synthetic_task_family_matrix_used: false,
   file_choice_atom_ablation_executed: false,
   private_score_records_written: false,
   private_event_records_written: false,
   downstream_agent_value_proven: false, promotion_ready: false,
   default_should_change: false, retriever_changed: false,
   pack_builder_changed: false, backend_changed: false,
   default_policy_changed: false, evidencecore_semantics_changed: false,
   runtime_behavior_changed: false,
   external_benchmark_performance_claimed: false,
   live_agent_generalization_claimed: false, real_user_task_claimed: false,
   method_winner_claimed: false, calibration_claimed: false,
   bea_superiority_claimed: false)
python3 scripts/validate_docs_i18n.py                                  => PASS
git diff --check                                                       => PASS
```

本地 no-env 验证路径是真实的且 blocked/unavailable。

## 注意事项

- B16-H 是公开仅聚合 file-choice atom ablation 下游 smoke artifact。
  它是 eval/诊断专用。它**不**改变 runtime、retriever、pack、backend
  或 default policy；它**不**改变 EvidenceCore 语义。它**不**是基准
  测试结果，**不**是下游 agent 价值声明，**不**是 runtime-clean 通用
  算法声明，**不**是 OOD 时间性声明，**不**是 QuIVer 系统声明，**不**
  是 method winner/calibration/promotion/default/runtime/EvidenceCore
  声明，也**不**是 BEA 优越性声明。
- B16-H 仅当 `--allow-remote` + remote opt-in gate + provider
  env 都设置时使用 **live LLM provider**（OpenAI 兼容）。默认本地
  no-env 路径保持真实（`blocked_remote_not_enabled`）。它**不**是假
  通过。
- B16-H **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- B16-H **不**声称 live agent 泛化。
  `live_agent_generalization_claimed=false`。
- B16-H **不**声称 BEA 优越性。
  `bea_superiority_claimed=false`。B16-H 解释文件选择下的 atom；它**不**
  声称 BEA 改善 agent 或应成为 default。
- B16-H **不**发布 prompt、response、provider payload、base URL、API
  key、raw model 路由前缀、工作区路径、文件路径、源码片段、patch/diff、
  测试输出、atom composition、chosen file 名、raw event log 或 per-run
  行。
- sufficiency 发现措辞有界："在此有界合成 file-choice 切片上"。任何
  `support_only_sufficient` 计数仅适用于此有界合成 file-choice 切片，
  不适用于一般下游 agent 价值。
- `honest_signals` 和 `mechanism_summary_records` 是诊断 smoke 结果，
  **绝不**是 promotion/default/value/BEA-优越性声明。任何对比的零或
  负 delta 是有效实证结果。
- 所有 no-claim/no-runtime-change flag 保持 false；诊断 flag
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  live-run flag 仅在 live run 实际执行时为 true。
- 无 runtime/retriever/pack/model/backend/default-policy 文件被修改。
  无 promotion/default/runtime 声明改变。
