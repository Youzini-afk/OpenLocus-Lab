# B16-I Non-Decisive Support / Target-Support Conjunction Live-Provider Smoke（公开仅聚合 artifact）

> 本中文文档与英文文档 `docs/en/b16i-target-support-conjunction.md`
> 一一对应。

## 范围与声明边界

B16-I 测试 B16-H 暴露的机制。B16-H 移除了文件选择 confound，但
support-only 仍然解决了所有任务，因为 support cue 过于 decisive。B16-I
重新设计 live-provider 合成任务，使 support 单独是非 decisive 的：target
binding 和 support rule 都应需要。

B16-I 有五个固定 arm，覆盖从 B16-F/B16-G/B16-H 复用的相同八个合成任务
族。在合成公开 micro bug 任务上使用 live LLM provider（OpenAI 兼容）；本地
应用模型的结构化 edit action；运行真实 stdlib 测试；仅发布聚合行为指标。

B16-I 明确**不是**下游 agent 价值证明，**不是** live agent 泛化证明，
**不是**外部基准测试结果，**不是**生产级 coding-agent 基准测试，**不
是**真实用户任务评估，**不是** method winner/default/promotion 声明，
**不是** calibration 声明，**不是** BEA 优越性声明，也**不是**
runtime/retriever/pack/backend/default-policy/EvidenceCore 语义改动。它
**不**发布 prompt、response、provider payload、base URL、API key、raw
model 路由前缀、工作区路径、文件路径、源码片段、patch/diff、测试输出、
atom composition、support rule text、exact answer、chosen file 名、raw
event log 或 per-run 行。

- 声明级别（claim_level）：
  `target_support_conjunction_downstream_smoke_only`。
- 模式（mode）：`public_aggregate_synthetic_task_family_matrix`；阶段
  （phase）为 `B16-I`。
- 状态枚举：成功时为
  `target_support_conjunction_smoke_pass`；未启用远程时为
  `blocked_remote_not_enabled` / `unavailable_no_local_provider_env`；
  provider 调用失败时为 `provider_call_failed`；结构化 action 解析失败
  时为 `structured_action_parse_failed`；paired run 无法完成时为
  `paired_run_failed`；scanner 失败时为 `fail_forbidden_scan`。
- B16-I 是 **eval/诊断专用**。允许的声明：在设计为需要 target-support
  conjunction 的合成 file-choice 任务上的有界 live-provider 行为。禁止：
  下游价值证明、BEA 优越性、method/default/winner、基准性能、真实用户
  任务声明、calibration、promotion、runtime/retriever/pack/backend/
  default-policy/EvidenceCore 改动。

### B16-H -> B16-I 关系

```text
B16-H file-choice atom ablation 下游 smoke
  （5 arm：control_sparse、file_choice_target_only、
   file_choice_support_only、file_choice_distractor_plus_support、
   file_choice_target_plus_support；
   8 任务 x 5 arm = 40 live 调用；
   CONFOUND 已移除：agent 在 per-task 安全文件中选择；
   但 support cue 过于 decisive：support_only 解决了 8/8）
-> B16-I non-decisive support / target-support conjunction 下游 smoke
   （5 arm：control_sparse、file_choice_target_only、
    file_choice_nondecisive_support_only、
    file_choice_distractor_plus_nondecisive_support、
    file_choice_target_plus_support；
    8 任务 x 5 arm = 默认 40 live 调用；
    support cue 非决定性：给出 formula/invariant/rule，仍需要 target
    binding；target_plus_support 是 conjunction arm，应为唯一可靠解决
    的 context arm）
```

## Arms

1. **`control_sparse`**：仅任务 issue，最小 context；无 atom。
2. **`file_choice_target_only`**：target file cue + target symbol cue；
   无 support module，无 support rule。识别 target file/symbol 但缺少
   rule/value。
3. **`file_choice_nondecisive_support_only`**：support module cue +
   非决定性 support rule（formula/invariant/dependency/config relation，
   仍需要 target binding）；无 target file cue，无 symbol cue。support
   atom **不**包含确切最终答案、确切 target-file 指令或 target-symbol
   edit 指令。
4. **`file_choice_distractor_plus_nondecisive_support`**：distractor
   file cue + support module cue + 非决定性 support rule；无 target
   file；wrong-file binding。给出 rule 加错误 binding。
5. **`file_choice_target_plus_support`**：target file cue + target
   symbol cue + support module cue + 非决定性 support rule。这是
   conjunction arm——给出 target binding 和 support rule，应为唯一
   可靠解决的 context arm。

主对比：

- `file_choice_target_plus_support` vs `file_choice_target_only`
- `file_choice_target_plus_support` vs
  `file_choice_nondecisive_support_only`
- `file_choice_target_plus_support` vs
  `file_choice_distractor_plus_nondecisive_support`

次对比：

- `file_choice_target_only` vs
  `file_choice_nondecisive_support_only`
- 每个 context arm vs `control_sparse`

## 非决定性 support cue 设计

support atom 给出 formula/invariant/dependency/config relation，仍需要
TARGET BINDING 才能应用。它**不**包含：

- 确切最终答案（如 "Correct value: 42"）；
- 确切 target-file 指令（如 "edit target.py"）；
- target-symbol edit 指令（如 "function foo should return 42"）。

相反，它说类似 "the correct return value is derived as helper_constant *
2 + task_index ... You must determine which file applies this relation."
的话。target_plus_support arm 额外给出 target binding（哪个文件+哪个
符号），使完整 cue 成为决定性的。

## 文件选择 confound 移除（从 B16-H 沿用）

文件选择在 per-task 安全文件集（target module + distractor module +
support/config/cross-file module）上保持启用。chosen file 仅记录在
`/tmp` 下的私有 SCORE/event JSONL 中。公开仅暴露聚合文件选择率。

## 已提交 artifact 与默认本地 run

已提交 artifact 位于
`artifacts/b16i_target_support_conjunction/b16i_target_support_conjunction_report.json`，
是公开仅聚合 smoke artifact。默认本地 no-env run 是真实的：无
`--allow-remote` 和所需 provider credential/model environment 时，evaluator 输出
`blocked_remote_not_enabled` 或 `unavailable_no_local_provider_env`，live-run
flag 为 false。它**不**是假通过。

## 私有 artifact（仅 /tmp 下；绝不提交/上传）

对于每个 task x arm，B16-I 写入：

- **私有 SCORE JSONL**（每个 task x arm 一行 = 默认 40 行）：
  atom_composition、chosen_file、score_outcome、latency_ms、tokens、
  provider_calls、failure_reason。
- **私有 event JSONL**（每个 task x arm 一行 = 默认 40 行）：prompt、
  response、parsed_action、chosen_file、patch、test_stdout、
  test_stderr、test_returncode、provider_metadata、failure_reason。

两者仅写入 `/tmp` 下（或 gitignored `runs/` 下的显式忽略私有路径）。
私有路径**绝不**在公开 artifact/docs/CI 中序列化。

## 公开 artifact

仅聚合 record：`arm_results`、`paired_deltas`、`task_family_results`、
`mechanism_summary_records`、`honest_signals`、私有 manifest、
`forbidden_scan`、no-claim flag。仅计数 self-test 字段：
`self_test_checks_total` 和 `self_test_checks_passed`。无
`self_test_summary` 和无 `self_test_checks` 列表。

Metrics 包括：solve_rate、tests_pass_rate、patch_apply_rate、
correct_file_before_first_edit_rate、wrong_file_edit_rate、
selected_target_file_rate、selected_distractor_file_rate、
selected_support_file_rate、no_op_rate、invalid_json_rate、
provider_failure_rate、context_tokens_mean、prompt_tokens_total、
completion_tokens_total、latency_seconds_mean、cost_proxy_total。

机制摘要 record（仅计数）：

- `target_support_conjunction_required_count`：target_plus_support 解决
  但 target_only 和 support_only 都未解决的任务数（conjunction 是必需
  的）。
- `support_only_sufficient_count`：support_only 解决的任务数。
- `target_only_sufficient_count`：target_only 解决的任务数。
- `distractor_hurts_count`：distractor_plus_support 未解决但
  target_plus_support 解决的任务数。
- `wrong_file_selection_count`：任何 context arm 选择非 target 文件的
  任务数。
- `all_arms_solved_count`：所有 5 个 arm 解决的任务数。
- `sparse_solved_count`：control_sparse 解决的任务数。

## CLI

```bash
python3 -m py_compile eval/b16i_target_support_conjunction.py
python3 eval/b16i_target_support_conjunction.py --self-test
python3 eval/b16i_target_support_conjunction.py \
    --out artifacts/b16i_target_support_conjunction/\
b16i_target_support_conjunction_report.json
# Live opt-in（仅当 provider credential/model environment 可用且安全时）：
python3 eval/b16i_target_support_conjunction.py \
    --allow-remote --task-count 8 \
    --out artifacts/b16i_target_support_conjunction/\
b16i_target_support_conjunction_report.json
```

## CI 通过标准

CI 通过意味着：live run 完成 + 隐私 scan 通过 + artifact 诚实。CI 通过
**不**要求 conjunction 成立。任何对比的零或负 delta 若诚实记录则是有效
实证结果。

## 禁止 scanner（公开，fail-closed）

严格禁止输出 scanner 在写入公开 JSON 前 fail-closed 运行。拒绝禁止 dict
key，包括 `prompt`、`response`、`chosen_file`、`file_choice`、
`support_rule_text`、`exact_answer`、`atom_composition`、`score_outcome`、
`phase_run_id`、`provider_metadata` 以及所有 path/file/snippet/patch/
test/secret 标识符。value 模式：任何 URL、32+ 字符 hex digest、secret-like
字符串、带文件扩展名的 path-like 字符串、`/tmp/` 工作区路径 value、
patch/diff 标记、stack trace、多行字符串、raw JSON 片段、raw line range、
raw model 路由前缀和 self-test sentinel。

## Self-test

306 self-test check（仅计数公开摘要；详细 check 列表**不**发布到公开
artifact）。覆盖：artifact identity、no-claim flag、live-run flag gating、
八个任务族、workspace builder、安全文件集、pack builder atom、atom
composition、非决定性 support cue text（无确切答案/无 target-file 指令/
decisive cue 确实包含答案）、文件选择 validator（拒绝 evil.py；接受
per-task 安全文件）、chosen-file 分类、私有 SCORE/event writer + fake
response、聚合 metrics + 文件选择率 + paired delta（8 对比 x 17 metrics）
+ 机制摘要（7 record）+ honest signals + family results、model 显示规范
化、env preservation、私有 manifest hash、scanner 拒绝（包括
support_rule_text、exact_answer、chosen_file、file_choice）、scanner 允许、
fail-closed 生成、公开 artifact self-scan clean、CLI 参数表面、remote
gating、五 arm 结构。

## 验证

```text
python3 -m py_compile eval/b16i_target_support_conjunction.py  => PASS
python3 eval/b16i_target_support_conjunction.py --self-test  => PASS (306/306 checks)
python3 eval/b16i_target_support_conjunction.py \
  --out artifacts/b16i_target_support_conjunction/\
b16i_target_support_conjunction_report.json               => PASS
  (status: blocked_remote_not_enabled,
   forbidden_scan: pass, self_test_passed: true,
   mode: public_aggregate_synthetic_task_family_matrix, phase: B16-I,
   model_display_category: unavailable,
   live_llm_agent: false, provider_calls_made: false,
   remote_provider_calls_made: false, paired_run_executed: false,
   synthetic_task_family_matrix_used: false,
   target_support_conjunction_executed: false,
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

## 注意事项

- B16-I 是公开仅聚合 non-decisive support / target-support conjunction
  下游 smoke artifact。它是 eval/诊断专用。它**不**改变 runtime、
  retriever、pack、backend 或 default policy；它**不**改变 EvidenceCore
  语义。
- B16-I 仅当 `--allow-remote` + remote opt-in gate + provider
  env 都设置时使用 **live LLM provider**（OpenAI 兼容）。默认本地
  no-env 路径保持真实（`blocked_remote_not_enabled`）。它**不**是假
  通过。
- B16-I **不**证明下游 agent 价值。
  `downstream_agent_value_proven=false`。
- B16-I **不**声称 BEA 优越性。
  `bea_superiority_claimed=false`。
- B16-I **不**发布 prompt、response、support rule text、exact answer、
  chosen file 名、atom composition 或 per-run 行。
- sufficiency 发现限于 "在此有界合成 file-choice 切片上"。
- 所有 no-claim/no-runtime-change flag 保持 false；诊断 flag 保持 true；
  live-run flag 仅在 live run 实际执行时为 true。
