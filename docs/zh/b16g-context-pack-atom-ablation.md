# B16-G Context-Pack Atom Ablation Live-Provider Smoke（公开仅聚合 artifact）

> 本中文文档与英文文档 `docs/en/b16g-context-pack-atom-ablation.md`
> 一一对应。

## 范围与声明边界

B16-G 解释 B16-F 的下游 tie：context pack 优于 sparse，但 BEA v0.3
并未优于 same-budget BM25。B16-G 运行 live-provider atom ablation，以
识别 target-file cue、decisive support cue、distractor cue 或其组合
是否驱动解决，测试在有界合成 coding 任务上。

B16-G 使用八个固定白名单任务族。对于每个合成工作区，B16-G 构造确定性
per-arm atom composition。atom composition（prompt 中包含哪些源码片段
和 cue）仅记录在 `/tmp` 下的私有 SCORE/event JSONL 中。在合成公开
micro bug 任务上使用 live LLM provider（OpenAI 兼容）；本地应用模型的
结构化 edit action；运行真实 stdlib 测试；仅发布聚合行为指标。

B16-G 明确**不是**下游 agent 价值证明，**不是** live agent 泛化证明，
**不是**外部基准测试结果，**不是**生产级 coding-agent 基准测试，**不
是**真实用户任务评估，**不是** method winner/default/promotion 声明，
**不是** calibration 声明，**不是** BEA 优越性声明，也**不是**
runtime/retriever/pack/backend/default-policy/EvidenceCore 语义改动。
它**不**发布 prompt、response、provider payload、base URL、API key、
raw model 路由前缀、工作区路径、文件路径、源码片段、patch/diff、测试
输出、atom composition、raw event log 或 per-run 行。

- 声明级别（claim_level）：
  `context_pack_atom_ablation_downstream_smoke_only`。
- 模式（mode）：`public_aggregate_synthetic_task_family_matrix`；阶段
  （phase）为 `B16-G`。
- 状态枚举：成功时为
  `context_pack_atom_ablation_smoke_pass`；未启用远程时为
  `blocked_remote_not_enabled` / `unavailable_no_local_provider_env`；
  provider 调用失败时为 `provider_call_failed`；结构化 action 解析失败
  时为 `structured_action_parse_failed`；paired run 无法完成时为
  `paired_run_failed`；scanner 失败时为 `fail_forbidden_scan`。
- B16-G 是 **eval/诊断专用**。它**不是**基准测试结果，**不是**下游
  agent 价值声明，**不是** runtime-clean 通用算法声明，**不是** OOD
  时间性声明，**不是** QuIVer 系统声明，**不是** method winner/
  calibration/promotion/default/runtime/EvidenceCore 声明，也**不是**
  BEA 优越性声明。

### B16-F -> B16-G 关系

```text
B16-F BEA-derived context pack 下游 paired smoke
  （3 arm：control_sparse、bm25_same_budget_context_pack、
   bea_v03_context_pack；8 任务 x 3 arm = 24 live 调用；
   context pack 优于 sparse，但 BEA 与 same-budget BM25 持平）
-> B16-G context-pack atom ablation 下游 smoke
   （5 arm：control_sparse、target_only、support_only、
    distractor_plus_support、target_plus_support；
    8 任务 x 5 arm = 默认 40 live 调用；
    解释哪些 atom 驱动解决；相同的仅聚合安全模型；CI 通过不要求任何
    atom 获胜）
```

B16-G 回应了 deep-research 指令的缺口：B16-F 显示 context pack 优于
sparse 但 BEA 并未优于 same-budget BM25。B16-G 将 context pack 分解为
atom，以解释哪些 atom（target file cue、support module cue、decisive
cue、distractor cue）驱动解决信号。

## Arms

B16-G 运行五个固定 arm，具有相同的 budget/tool 约束；仅 atom composition
不同：

1. **`control_sparse`**：仅任务 issue，最小 context；无 atom。agent 无法
   在无任何 cue 时确定正确值/操作。
2. **`target_only`**：target file cue + target symbol cue（target.py 源码
   + 符号名）。无 support module，无 decisive cue。测试 target file cue
   单独是否足够。
3. **`support_only`**：support module cue + decisive cue
   （support/config/cross_file 源码 + 族特定 decisive 关系）。无 target
   file cue，无 symbol cue。测试 support relation 单独是否足够。
4. **`distractor_plus_support`**：distractor file cue + support module
   cue + decisive cue（distractor.py + support 源码 + decisive 关系）。
   无 target file cue，无 symbol cue。distractor 是错误文件；测试当
   distractor cue 出现而非 target cue 时 agent 是否编辑 distractor.py
   （错误文件）。
5. **`target_plus_support`**：target file cue + target symbol cue +
   support module cue + decisive cue（target.py + support 源码 +
   decisive 关系）。这是"full pack" arm；测试 full pack 是否解决。

主对比：

- `target_plus_support` vs `distractor_plus_support`（target file cue
  在 support 存在时重要）。
- `target_plus_support` vs `support_only`（target file cue 在 support
  之上重要）。
- `target_only` vs `support_only`（哪个 atom 单独足够）。

次对比：每个 context arm vs `control_sparse`。

## 已提交 artifact 与手动 CI 结果

已提交 artifact 位于
`artifacts/b16g_context_pack_atom_ablation/b16g_context_pack_atom_ablation_report.json`，
是公开仅聚合 smoke artifact，并已镜像手动 CI run `27947247773` 的
sanitized aggregate report。

手动 CI run `27947247773` 摘要：

- 8 任务 x 5 arms = 40 次 live provider calls。
- 私有 SCORE/event manifest 各 `record_count=40`，
  `storage_class=tmp_private`，`path_publicly_serialized=false`。
- forbidden scan pass；`self_test_checks_passed=221/221`。
- `control_sparse` solve/test=0.0；`target_only` solve/test=0.0。
- `support_only`、`distractor_plus_support`、`target_plus_support` 均
  solve/test=1.0。
- 主对比：`target_plus_support` vs `distractor_plus_support` 的 solve/test
  delta=0.0；`target_plus_support` vs `support_only` 的 solve/test delta=0.0；
  `target_only` vs `support_only` 的 solve/test delta=-1.0。
- 机制计数：`support_atom_sufficient_count=8`，
  `target_atom_required_count=0`，`distractor_hurts_count=0`，
  `all_arms_solved_count=0`，`sparse_solved_count=0`。

解释：在这个有界合成 live-provider 切片上，decisive support atom 对所有
任务都足够；target cue 单独不足以解题；当 decisive support cue 存在时，
distractor cue 没有造成伤害。这解释了 B16-F 中 same-budget BM25 pack 为什么
能与 BEA 打平：在该任务面上，decisive 信息由 support atom 携带，而不是
target-file cue。该结果是 atom-ablation smoke，不是下游价值证明，也不是 BEA
优越性声明。

默认本地 no-env path 仍然真实：无 `--allow-remote` 和所需 provider
credential/model env 时，evaluator 输出 blocked 或 unavailable 聚合报告，
live-run flag 为 false。它**不**是假通过。

## 异构合成公开任务族矩阵设计

B16-G 复用 B16-F 的八个固定白名单任务族以保持可比性（默认 8 任务；
`--task-count` 范围 4-12，硬上限 12；默认 40 live 调用 = 8 x 5 arm；
最大 60 live 调用）。任务循环遍历八个族以保持矩阵平衡。

### 任务族

与 B16-F 相同的八个族：`same_symbol_support_relation`、
`operation_ambiguity`、`boundary_condition`、
`helper_dependency_choice`、`config_or_test_mismatch`、
`distractor_file`、`nearby_wrong_function`、`cross_file_symbol`。每个族
有不同的 decisive cue，由 support module 携带。

### 多文件工作区

对于每个 task 和 arm，B16-G 创建一个 fresh `/tmp` 工作区，包含四个
真实 Python 文件：`target.py`（有 bug 的函数）、`distractor.py`（同名
decoy）、`support.py`/`config.py`/`cross_file.py`（helper 常量）和
`test_target.py`（导入 target AND support；断言正确的族特定关系）。
harness 实际编辑文件并运行子进程测试。

## Atom pack builder

每个 arm 获得确定性 atom 集合（prompt 中包含的源码片段和 cue）。atom
composition 仅写入 `/tmp` 下的私有 SCORE/event JSONL。公开 pack 描述符
仅携带 booleans/counts/token 估计。

Atom 语义：

- `target_file_cue`：prompt 包含 target.py 源码 + "edit target.py"。
- `target_symbol_cue`：prompt 包含确切符号名。
- `support_module_cue`：prompt 包含 support/config/cross_file 源码。
- `decisive_cue`：prompt 包含族特定 decisive 关系。
- `distractor_file_cue`：prompt 包含 distractor.py 源码（错误文件）。

Arm composition：

- `control_sparse`：无。
- `target_only`：target_file_cue + target_symbol_cue（无 support，无
  decisive）。
- `support_only`：support_module_cue + decisive_cue（无 target
  file/symbol）。
- `distractor_plus_support`：distractor_file_cue + support_module_cue +
  decisive_cue（无 target file；wrong-file cue）。
- `target_plus_support`：target_file_cue + target_symbol_cue +
  support_module_cue + decisive_cue（full pack）。

## Live provider 约束

- 确切 provider credential/model env 名称只保留在 workflow/config wiring 中，不写入研究正文。
- 仅当 `--allow-remote`、remote opt-in gate、必要时的 workflow-dispatch gate，
  以及 provider credential/model configuration 均存在时才进行远程调用。
- artifact/docs 中无 raw base URL、API key、prompt、response、源码片段、
  patch/diff、stdout/stderr、工作区路径、atom composition 或 provider
  payload。
- live LLM prompt 可包含微小合成/公开源码片段（target.py /
  distractor.py / support module）和族特定 decisive cue（仅当 pack
  携带时）。prompt **绝不**持久化（仅写入 `/tmp` 下的私有 event
  JSONL）。
- 结构化 edit action schema 为白名单：action 必须为
  `replace_return_value`、`choose_helper_constant` 或 `no_op`；file
  必须为 `target.py`；无任意路径，无 shell。distractor 和 support 文件
  **不可**编辑。
- 若 provider 返回 `usage`，则 usage 诊断可包含聚合 prompt/completion/
  total token 计数；否则标记为不可用。
- Cost 仅为 `cost_proxy`（始终 0.0）；无 live 价格推断。
- 研究 docs/artifacts 记录不含路由前缀的规范化 model 显示名（例如
  `Kimi-K2.7-Code`，非 raw 路由前缀）。

## 私有 artifact（仅 /tmp 下；绝不提交/上传）

对于每个 task x arm，B16-G 写入：

- **私有 SCORE JSONL**（每个 task x arm 一行 = 默认 40 行）：
  atom_composition、score_outcome（per-arm metrics）、latency_ms、
  tokens、provider_calls、failure_reason。
- **私有 event JSONL**（每个 task x arm 一行 = 默认 40 行）：prompt、
  response、parsed_action、patch、test_stdout、test_stderr、
  test_returncode、provider_metadata、failure_reason。

两者仅写入 `/tmp` 下（或 gitignored `runs/` 下的显式忽略私有路径）。
私有路径**绝不**在公开 artifact/docs/CI 中序列化。

## CLI

```bash
python3 -m py_compile eval/b16g_context_pack_atom_ablation.py
python3 eval/b16g_context_pack_atom_ablation.py --self-test
python3 eval/b16g_context_pack_atom_ablation.py \
    --out artifacts/b16g_context_pack_atom_ablation/\
b16g_context_pack_atom_ablation_report.json
# Live opt-in（仅当 provider credential/model environment 可用且安全时）：
python3 eval/b16g_context_pack_atom_ablation.py \
    --allow-remote --task-count 8 \
    --out artifacts/b16g_context_pack_atom_ablation/\
b16g_context_pack_atom_ablation_report.json
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

## Provider client helper

B16-G 复用 B16-C/D/E/F 的 `eval/provider_client.py`（未修改）。它是一个
最小的 OpenAI 兼容 chat helper，返回安全的 `ProviderCallResult` 对象，
仅暴露聚合计数（calls attempted/succeeded/failed、invalid_json、
timeout、latency、numeric provider `usage`（若存在）、固定 failure-
category enum token、HTTP status）。Raw prompt、message、response、
base URL、API key 和 provider payload **绝不**在公开诊断中返回。

## Artifact identity（默认已提交 artifact）

已提交 artifact 位于
`artifacts/b16g_context_pack_atom_ablation/b16g_context_pack_atom_ablation_report.json`，
是公开仅聚合 smoke artifact。Identity/边界字段：

- `schema_version` = `b16g_context_pack_atom_ablation.v1`
- `generated_by`、`generated_at`、`claim_level`、`status`、`mode`、
  `phase`、`model_display_category`（规范化；无路由前缀）。
- Safe true flag（仅 live run 时；恰好这些，全为 true）：
  `downstream_agent_runs_performed`、`live_llm_agent`、
  `provider_calls_made`、`remote_provider_calls_made`、
  `paired_run_executed`、`synthetic_task_family_matrix_used`、
  `real_file_edits_performed`、`real_test_commands_executed`、
  `agent_behavior_metrics_evaluated`、`atom_ablation_executed`、
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
  `method_winner_claimed`、`calibration_claimed`、
  `bea_superiority_claimed`。
- `input_summary`：`synthetic_task_count`、`run_count_per_arm`、
  `total_runs`、`arms`（`[control_sparse, target_only, support_only,
  distractor_plus_support, target_plus_support]`）、
  `task_families`（八个白名单族名）、`paired_design`（`true`）、
  `workspace_isolation`（`fresh_tmp_per_task_arm`）、
  `transient_workspace_outputs_only`（`true`）、
  `designed_causal_subset`（`true`）、`task_family_matrix`（`true`）、
  `primary_contrasts`（3 对比）、`secondary_contrasts`（4 对比）。
- `arm_results`：固定 record 列表
  `{arm, metrics, provider_summary, failure_category_counts}`。
  Metrics：`run_count`、`solve_rate`、`tests_pass_rate`、
  `patch_apply_rate`、`correct_file_before_first_edit_rate`、
  `wrong_file_edit_rate`、`no_op_rate`、`invalid_json_rate`、
  `provider_failure_rate`、`context_tokens_mean`、
  `prompt_tokens_total`、`completion_tokens_total`、
  `latency_seconds_mean`、`cost_proxy_total`。
- `paired_deltas`：固定 record 列表
  `{baseline_arm, treatment_arm, metric, delta}`。7 对比（3 主 + 4 次）
  x 13 metrics。
- `task_family_results`：固定 record 列表
  `{task_family, arm, run_count, solve_rate, tests_pass_rate}`。
  仅出现白名单族名。无 task ID。
- `mechanism_summary_records`：仅聚合计数：
  `support_atom_sufficient_count`（support_only 解决的任务数）、
  `target_atom_required_count`（target_only 解决但 support_only 未解决
  的任务数）、`distractor_hurts_count`（distractor_plus_support 未解决但
  target_plus_support 解决的任务数）、`all_arms_solved_count`、
  `sparse_solved_count`。
- `honest_signals`：`target_file_signal_observed`（bool）、
  `support_atom_signal_observed`（bool）、
  `support_atom_sufficient_count`（int）、`target_atom_required_count`
  （int）、`distractor_hurts_count`（int）、`all_arms_solved_count`
  （int）、`sparse_solved_count`（int）、per-arm solve rate。这些是诊断
  smoke 结果，**绝不**是 promotion/default/value/BEA-优越性声明。
- `private_score_manifest`：仅聚合
  `{records_written, record_count, schema_version, manifest_hash,
  storage_class, path_publicly_serialized=false}`。
- `private_event_manifest`：仅聚合
  `{records_written, record_count, schema_version, manifest_hash,
  storage_class, path_publicly_serialized=false}`。
- `self_test_checks_total`、`self_test_checks_passed` 和
  `self_test_passed`（仅计数；无详细 check 列表）。
- `forbidden_scan` 摘要（写入 JSON 前 fail-closed）。

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
`candidate_features`、`selected_candidates` 等）和 value 模式：任何
URL（无 URL 白名单）、32+ 字符 hex digest、secret-like 字符串、带文件
扩展名的 path-like 字符串、`/tmp/` 工作区路径 value、`task_N` task
标识符 value、patch/diff 标记、stack trace、多行字符串、raw JSON 片段、
raw line range、raw model 路由前缀和 self-test sentinel。

scanner 仅对最终公开聚合 artifact 运行。内部 per-run event log 和
SCORE 行（包含 path/patch/test stdout/stderr/atom composition）仅保留在
`/tmp` 下，**绝不**对公开契约 scan，**绝不**提交。

## Self-test

B16-G 保持 self-test 聚焦（仅计数公开摘要；详细 check 列表**不**发布到
公开 artifact）。self-test 覆盖：

- Artifact identity 字段（schema、claim、status enum、mode、phase、
  generated_by、arms count=5、families count=8、默认 task count=8、
  max live calls=60、primary/secondary 对比计数）。
- Always-false no-claim flag（全部 15 个 false，包括
  `bea_superiority_claimed`）。
- Live-run flag gating。
- 八个任务族生成（全部八个存在；8 任务平衡）。
- 每族多文件工作区（target/distractor/support/test；修复前测试失败）。
- Pack builder atom per arm（control 无 atom；target_only 有
  target+symbol；support_only 有 support+decisive；
  distractor_plus_support 有 distractor+support+decisive；
  target_plus_support 有全部四个 atom）。
- Atom composition 私有列表（per arm 正确 atom 计数和名称）。
- 私有 SCORE/event writer + fake response（tps 解决；dps 错误值；
  control no_op；invalid JSON；各 4 行写入 /tmp；有效 JSON；私有字段
  存在：atom_composition、score_outcome、prompt、response）。
- Edit action 限制（禁止文件/action 拒绝；distractor.py 拒绝；no_op
  接受）。
- 聚合 metrics + paired delta（7 对比 x 13 metrics；主对比存在；
  primary solve_rate delta 正）+ mechanism summary（5 record：
  support_atom_sufficient_count、target_atom_required_count、
  distractor_hurts_count、all_arms_solved_count、sparse_solved_count）
  + honest signals + family results（全部八个族；每族五个 arm）。
- Model 显示规范化（剥离路由前缀；空返回 `unavailable`；剥离不安全
  字符）。
- Env preservation self-test（probe 恢复 env；无网络 probe 不清除 live
  provider credential/model env）。
- 私有 manifest hash 稳定（SCORE 和 event manifest hash 稳定且不同）。
- Scanner 拒绝（工作区路径、文件路径、源码片段、patch 标记、
  prompt/response key、atom_composition key、score_outcome key、
  phase_run_id key、provider_metadata key、raw 路由前缀、URL value、
  sentinel canary）。
- Scanner 允许（arm 名、task family 名、paired_deltas、
  mechanism_records、model 显示类别、私有 manifest、honest signals）。
- Fail-closed 生成（clean 公开 report 不 raise；leaked report raise
  SystemExit；self-test 失败拒绝 artifact 生成）。
- 公开 artifact self-scan clean。
- CLI 参数表面。
- Remote gating。
- 五 arm 结构（control 第一、target_only 第二、support_only 第三、
  distractor_plus_support 第四、target_plus_support 第五；默认 total
  runs = 40）。

## 验证

```text
python3 -m py_compile eval/b16g_context_pack_atom_ablation.py  => PASS
python3 eval/b16g_context_pack_atom_ablation.py --self-test  => PASS (221/221 checks)
python3 eval/b16g_context_pack_atom_ablation.py \
  --out artifacts/b16g_context_pack_atom_ablation/\
b16g_context_pack_atom_ablation_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-G,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   synthetic_task_family_matrix_used: false,
   atom_ablation_executed: false,
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

- B16-G 是公开仅聚合 context-pack atom ablation 下游 smoke artifact。
  它是 eval/诊断专用。它**不**改变 runtime、retriever、pack、backend
  或 default policy；它**不**改变 EvidenceCore 语义。它**不**是基准
  测试结果，**不**是下游 agent 价值声明，**不**是 runtime-clean 通用
  算法声明，**不**是 OOD 时间性声明，**不**是 QuIVer 系统声明，**不**
  是 method winner/calibration/promotion/default/runtime/EvidenceCore
  声明，也**不**是 BEA 优越性声明。
- B16-G 仅当 `--allow-remote` + remote opt-in gate + provider
  credential/model env 都设置时使用 **live provider**。默认本地 no-env
  路径保持真实（`blocked_remote_not_enabled`）。它**不**是假通过。
- B16-G **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- B16-G **不**声称 live agent 泛化。
  `live_agent_generalization_claimed=false`。
- B16-G **不**声称 BEA 优越性。
  `bea_superiority_claimed=false`。B16-G 解释 atom；它**不**声称 BEA
  改善 agent 或应成为 default。
- B16-G **不**发布 prompt、response、provider payload、base URL、API
  key、raw model 路由前缀、工作区路径、文件路径、源码片段、patch/diff、
  测试输出、atom composition、raw event log 或 per-run 行。per-run
  event log、prompt、response、atom composition 和测试输出仅保留在
  `/tmp` 下，**绝不**提交或上传。
- `honest_signals` 和 `mechanism_summary_records` 是诊断 smoke 结果，
  **绝不**是 promotion/default/value/BEA-优越性声明。任何对比的零或
  负 delta 是有效实证结果。
- 所有 no-claim/no-runtime-change flag 保持 false；诊断 flag
  （`aggregate_only_public_artifact`、`diagnostic_only`）保持 true；
  live-run flag 仅在 live run 实际执行时为 true。
- 无 runtime/retriever/pack/model/backend/default-policy 文件被修改。
  无 promotion/default/runtime 声明改变。
