# OpenLocus Research Summary

For the current research-conclusion synthesis, see
[`docs/en/current-research-conclusions.md`](current-research-conclusions.md)
or the index page [`docs/current-research-conclusions.md`](../current-research-conclusions.md).

当前研究结论总报告见
[`docs/zh/current-research-conclusions.md`](../zh/current-research-conclusions.md)，
入口索引见 [`docs/current-research-conclusions.md`](../current-research-conclusions.md)。

This document will be updated after each evidence-gated stage. The detailed
chronological notes below are preserved for traceability; the current high-level
research conclusion is summarized first.

## 历史状态更新 —— 2026-06-20（D4-series rollup / D5-H 阻塞）

最新 checkpoint 是 D4-series harness rollup（`b7c65dd`，`add D4 harness rollup`）。
它是公开纯汇总 artifact（`eval/d4_series_rollup.py` ->
`artifacts/d4_series_rollup/d4_series_rollup_report.json`），字段为
`schema_version=d4_series_rollup.v1`、
`claim_level=d4_series_harness_rollup_only`、
`status=d5_blocked_no_real_human_manual_labels`。

C4 外部 benchmark readiness 序列已完成到 C4.5：ContextBench schema/readiness 与
verified row-mapping smoke、SWE-Explore row-mapping 及负向 line-budget shape 观察、
CORE-Bench source-readiness no-go、RepoQA source/schema-contract readiness。这些是
readiness 与边界结果，**不是**外部 benchmark performance claim。

Step 6 / D 系列 dual-rubric 控制面已完成到 D4 rollup：

```text
D1 deterministic dual-rubric scaffold
-> D2 public aggregate mappability + private proxy smoke
-> D3 true E/S label protocol preregistration
-> D4a execution gate / dry-run
-> D4b true-label bundle harness
-> D4c annotation packet builder harness
-> D4d human annotation runbook/checklist
-> D4e filled-packet -> D4b bundle converter harness
-> D4f D4b bundle validation / gate-check harness
-> D4-series rollup / D5 blocked status
```

D 系列结果只是控制面就绪。它**没有**采集真实人工/手工 labels，**没有**在真实人工
label bundle 上执行转换或校验，**没有**计算 calibration/agreement/CI 指标，也**没有**
解锁 D5-H / 人工参考校准。这个历史 D4-rollup 状态已由下方 D5-A0 实证转折接续：
缺少人工/手工标签不再阻塞自动/程序化 D5-A 路径。

当前 no-claim flags 仍为 false：`promotion_ready=false`、
`default_should_change=false`、`evidencecore_semantics_changed=false`、
`runtime_clean_general_algorithm_claimed=false`、`downstream_agent_value_proven=false`、
`true_e_s_calibration_claimed=false`，且没有 external benchmark performance claim。
当前活跃下一步不再是 E1 控制面 preregistration，而是下方记录的 D5-A 自动实证路径。

## 当前状态更新 —— 2026-06-20（D5-A0 自动 E/S 校准 smoke）

D4-series rollup 之后，研究轨迹被修正：控制面阶段在此停止，D5-A0 产出控制面
之后的首个实证 smoke。D5-H / 人工参考 / 人工校准审计在真实人工/手动 true E/S
标签采集前仍属 out of scope/不可用；D5-A 自动/程序化实证路径已激活并继续。
D5-A0
（`eval/d5a_automated_es_calibration.py` ->
`artifacts/d5a_automated_es_calibration/d5a_automated_es_calibration_report.json`，
schema `d5a_automated_es_calibration.v1`、
`claim_level=automated_e_s_calibration_smoke_only`、
`status=automated_es_calibration_smoke_pass`、
`mode=public_aggregate_r14_retrieval_smoke`、phase `D5-A0`）从已提交的
r14 sanity span 标签（gold spans + hard negatives）在真实 OpenLocus
retrieval 输出（regex、bm25、symbol、rrf）上派生**自动 E 标签**与**确定性
S-proxy 标签**。它按方法调用 `eval/run_retrieval.py`，将输出写入临时
`/tmp/d5a_retrieval_*`（绝不提交），仅将聚合 counts/rates 写入已提交
artifact。157/157 自测检查通过；四种方法全部成功；共标记 3152 个 candidate。

这是 smoke-only。它**不**声明 true E/S 校准，**不**采集新人工/手动标签，
**不**审计人工参考标签，**不**通过任何公开发布门，**不**提升任何
candidate，也**不**解锁 D5-H / 人工参考 / 人工校准声明或 default/policy/公开发布
声明。自动 E/S 标签是从已提交 span 标签
（最初为 span-recall 指标采集，而非为 true E/S 评分准则采集）派生的；
它们**不是**真实人工/手动 E/S 分数，也**不是** D3 dual-rubric E/S 分
数。D5-A0 不解锁 default/policy/公开发布或人工校准声明；D5-H / 人工参考 /
人工校准审计在人工标签到位前仍属 out of scope。所有无声明 /
无运行时变更标志保持 false（`promotion_ready=false`、
`default_should_change=false`、`retriever_changed=false`、
`pack_builder_changed=false`、`model_calls_changed=false`、
`backend_changed=false`、`default_policy_changed=false`、
`evidencecore_semantics_changed=false`、
`runtime_clean_general_algorithm_claimed=false`、
`downstream_agent_value_proven=false`、
`external_benchmark_performance_claimed=false`、
`human_e_s_calibration_claimed=false`、
`automated_e_s_calibration_claimed=false`、
`d5_human_reference_calibration_unblocked=false`、
`automated_d5a_path_active=true`）。未修改
runtime/retriever/pack/model/backend/default-policy 文件。详见
[D5-A0 详细报告](d5a-automated-es-calibration.md)。

## 当前状态更新 —— 2026-06-20（B16-A 最小 mock 下游 paired run）

继 D5-A0 之后，B16-A 产出首个**非仅控制面**的 B16 风格下游 agent 实证
run。B16-A（`eval/b16a_minimal_mock_agent_paired_run.py` ->
`artifacts/b16a_minimal_mock_agent_paired_run/b16a_minimal_mock_agent_paired_run_report.json`，
schema `b16a_minimal_mock_agent_paired_run.v1`、
`claim_level=deterministic_mock_downstream_paired_smoke_only`、
`status=mock_downstream_paired_smoke_pass`、
`mode=public_aggregate_synthetic_micro_tasks`、阶段 `B16-A`）在代码中生成
确定性合成公开 micro bug 任务，为每个 task+arm 创建全新 `/tmp` 工作区，
含真实微型 Python 模块 + stdlib 测试，运行**确定性 mock agent**（无
live LLM、无 provider 调用、无远程调用），执行**真实文件编辑**和**真实
子进程测试**，并在 paired control/treatment arms 上计算聚合行为指标
（solve_rate、tests_pass_rate、correct_file_before_first_edit_rate、
wrong_file_edits_mean、tool_calls_before_first_edit_mean、
context_tokens_mean、latency_ms_mean、cost_proxy_mean）。treatment pack
因果地改变 mock agent 的行为（treatment solve_rate=1.0 vs control
solve_rate=0.0）。105/105 self-test checks 通过；24 个任务；48 个总
run。

这是 smoke-only。它**不**声明下游 agent 价值，**不**声明 live agent
泛化，**不**声明外部基准测试性能，**不**声明真实用户任务，**不**提升
任何 candidate，也**不**改变 runtime/retriever/pack/backend/
default-policy/EvidenceCore 语义。per-run event log、patch 和测试输出
仅留在 `/tmp`，**绝不**提交或上传。提交的 artifact 仅含聚合数据。所有
无声明 / 无运行时变更标志保持 false（`live_llm_agent=false`、
`provider_calls_made=false`、`remote_calls_made=false`、
`downstream_agent_value_proven=false`、`promotion_ready=false`、
`default_should_change=false`、`runtime_behavior_changed=false`、
`retriever_changed=false`、`pack_builder_changed=false`、
`backend_changed=false`、`default_policy_changed=false`、
`evidencecore_semantics_changed=false`、
`external_benchmark_performance_claimed=false`、
`live_agent_generalization_claimed=false`、
`real_user_task_claimed=false`）。确定性 mock run 标志
（`downstream_agent_runs_performed`、`deterministic_mock_agent`、
`synthetic_micro_tasks_used`、`paired_arms_evaluated`、
`real_file_edits_performed`、`real_test_commands_executed`、
`agent_behavior_metrics_evaluated`、`aggregate_only_public_artifact`、
`diagnostic_only`）是仅有的额外 true 标志。未修改任何
 runtime/retriever/pack/model/backend/default-policy 文件。详见
 [B16-A 详细报告](b16a-minimal-mock-agent-paired-run.md)。

## 当前状态更新 —— 2026-06-21（B16-B less-separable mock downstream paired stress）

> 中文译本待补充。以下为英文原文，避免内容丢失。

Following B16-A, B16-B extends the deterministic/mock downstream
paired-agent empirical run from deliberately separable micro bugs to a
harder **less-separable multi-cue stress** task family. B16-B
(`eval/b16b_less_separable_mock_paired_run.py` ->
`artifacts/b16b_less_separable_mock_paired_run/b16b_less_separable_mock_paired_run_report.json`,
schema `b16b_less_separable_mock_paired_run.v1`,
`claim_level=deterministic_mock_downstream_paired_stress_only`,
`status=mock_downstream_paired_stress_pass`,
`mode=public_aggregate_synthetic_stress_tasks`, phase `B16-B`)
generates deterministic synthetic public less-separable stress tasks
in code, creates a fresh `/tmp` workspace per task+arm with real
multi-file Python modules (target.py with decoy symbol, distractor.py
with same symbol, support.py with offset constant, test_target.py) +
stdlib tests, runs a **deterministic mock agent** (no live LLM, no
provider calls, no remote calls) that performs **real file edits** and
runs **real subprocess tests**, and computes aggregate behavior metrics
over paired control_sparse/treatment_multi_cue arms. Solving requires
combining four cues (target_file + target_symbol + operation_hint +
support_relation); missing any cue causes a deterministic wrong action.
The treatment multi-cue pack causally alters the mock agent's behavior
(treatment solve_rate=1.0 vs control solve_rate=0.0). 147/147 self-test
checks pass; 24 tasks; 48 total runs. Treatment is perfect by
construction; docs describe this as a harness/stress result, NOT a
live agent result.

This is stress-only. It does NOT claim downstream agent value, does
NOT claim live agent generalization, does NOT claim external benchmark
performance, does NOT claim a real user task, does NOT promote any
candidate, and does NOT change runtime/retriever/pack/backend/
default-policy/EvidenceCore semantics. It emits NO `winner`,
`best_arm`, `recommended_default`, `preferred_policy`, or `promotion`
recommendation field. The committed artifact is aggregate-only. All
no-claim / no-runtime-change flags remain false
(`live_llm_agent=false`, `provider_calls_made=false`,
`remote_provider_calls_made=false`,
`downstream_agent_value_proven=false`,
`live_agent_generalization_claimed=false`,
`promotion_ready=false`, `default_should_change=false`,
`runtime_behavior_changed=false`, `retriever_changed=false`,
`pack_builder_changed=false`, `backend_changed=false`,
`default_policy_changed=false`,
`evidencecore_semantics_changed=false`,
`external_benchmark_performance_claimed=false`). The
deterministic-mock-stress-run flags are the only additional true
flags. No runtime/retriever/pack/model/backend/default-policy files
were modified. See the
[B16-B detailed report](b16b-less-separable-mock-paired-run.md).

## 当前状态更新 —— 2026-06-21（B16-C live-provider 下游 paired smoke）

继 B16-A/B16-B（确定性/mock）之后，B16-C 产出首个 **live-provider**
B16 风格下游 agent 实证 run。B16-C
（`eval/b16c_live_provider_paired_smoke.py` + 共享
`eval/provider_client.py` ->
`artifacts/b16c_live_provider_paired_smoke/b16c_live_provider_paired_smoke_report.json`，
schema `b16c_live_provider_paired_smoke.v1`、
`claim_level=live_provider_downstream_paired_smoke_only`、
`mode=public_aggregate_synthetic_micro_tasks`、阶段 `B16-C`）在代码中
生成确定性合成公开 micro bug 任务，为每个 task+arm 创建全新 `/tmp` 工
作区，仅当 `--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider
env 全部设置时运行 **live LLM agent**（OpenAI 兼容），本地应用模型的
结构化 edit action（仅白名单 `target.py`；action 仅
`replace_return_value` / `no_op`），运行真实子进程测试，并在 paired
`control_sparse` / `treatment_context_pack` arms 上计算聚合行为指标。
手动 CI run `27900913599`（`real-provider-benchmark`，
`stage=b16c_live_provider_paired_smoke`，`enable_remote_models=true`）完成
`status=live_provider_paired_smoke_pass`；已提交 artifact 现在镜像该
sanitized aggregate CI report。该 run 执行 2 个合成任务 / 4 次 live provider
call，4/4 calls 成功，invalid_json_count=0，并通过 workflow privacy
validator。两个 arm 都解出两个平凡 micro 任务（`control_sparse`
solve_rate=1.0；`treatment_context_pack` solve_rate=1.0），因此
treatment-minus-control solve-rate delta 为 0.0。33/33 provider-client
self-test checks 通过；119/119 B16-C self-test checks 通过。

这是 smoke-only。它**不**声明下游 agent 价值，**不**声明 live agent
泛化，**不**声明外部基准测试性能，**不**声明真实用户任务，**不**提升
任何 candidate，也**不**改变 runtime/retriever/pack/backend/
default-policy/EvidenceCore 语义。per-run prompt、response、event
log、patch 和测试输出仅留在 `/tmp`，**绝不**提交或上传。提交的
artifact 仅含聚合数据，使用 records-shaped `arm_results` 和
`paired_deltas`。所有无声明 / 无运行时变更标志保持 false
（`downstream_agent_value_proven=false`、
`live_agent_generalization_claimed=false`、`promotion_ready=false`、
`default_should_change=false`、
`external_benchmark_performance_claimed=false`、
`real_user_task_claimed=false`、`runtime_behavior_changed=false`、
`retriever_changed=false`、`pack_builder_changed=false`、
`backend_changed=false`、`default_policy_changed=false`、
`evidencecore_semantics_changed=false`）。live-run 标志
（`downstream_agent_runs_performed`、`live_llm_agent`、
`provider_calls_made`、`remote_provider_calls_made`、
`paired_run_executed`、`synthetic_micro_tasks_used`、
`real_file_edits_performed`、`real_test_commands_executed`、
`agent_behavior_metrics_evaluated`）**仅**在 live run 实际执行时为
true，否则为 false。不发布 raw model 路由前缀；仅记录规范化的
`model_display_category`。较早的 C5-C CI run `27905321437` 因上传绿色
`unavailable_with_reason` 被视为 fail-open bug；workflow 现在会让 network-enabled
unavailable report 失败。未修改任何
runtime/retriever/pack/model/backend/default-policy 文件。B16-C upload surface
仅包含 sanitized aggregate report；`plan.json` 等通用 `real-provider` artifacts
已从 B16-C artifact upload 中排除。详见
[B16-C 详细报告](b16c-live-provider-paired-smoke.md)。

## 当前状态更新 —— 2026-06-21（B16-D less-trivial live-provider 下游 paired smoke）

继 B16-C 之后，B16-D 是更难的 live-provider paired smoke，任务族更不
平凡。B16-D
（`eval/b16d_less_trivial_live_provider_paired_smoke.py`，复用 B16-C 的
`eval/provider_client.py`）->
`artifacts/b16d_less_trivial_live_provider_paired_smoke/b16d_less_trivial_live_provider_paired_smoke_report.json`，
schema `b16d_less_trivial_live_provider_paired_smoke.v1`、
`claim_level=less_trivial_live_provider_downstream_paired_smoke_only`、
`mode=public_aggregate_synthetic_less_trivial_tasks`、阶段 `B16-D`）
生成确定性 less-trivial 多文件任务（target.py + distractor.py +
support.py + test_target.py；同符号 distractor；需要 support
relation；正确值 = `helper_constant * 2 + task_index`），为每个
task+arm 创建全新 `/tmp` 工作区，仅当 `--allow-remote` +
`OPENLOCUS_ALLOW_REMOTE=1` + provider env 全部设置时运行 **live LLM
agent**（OpenAI 兼容），本地应用模型的结构化 edit action（仅白名单
`target.py`；action `replace_return_value` /
`choose_helper_constant` / `no_op`；distractor/support 不可编辑），
运行真实子进程测试，并在 paired `control_sparse` /
`treatment_context_pack` arms 上计算聚合行为指标。treatment 含
target file cue、target symbol cue、support-relation cue 及 exact
edit constraint；control 缺少决定性 cue。手动 CI run `27901644438`
（`real-provider-benchmark`，`stage=b16d_less_trivial_live_provider_paired_smoke`，
`enable_remote_models=true`）完成
`live_provider_less_trivial_paired_smoke_pass` 并通过 privacy validation。
已提交 artifact 现在镜像该 sanitized aggregate CI report：4 个合成任务 / 8 次
live provider calls，11/11 provider calls succeeded，invalid JSON count 0，
control solve_rate=0.5，treatment solve_rate=1.0，treatment-minus-control
solve_rate delta `+0.5`，tests_pass_rate delta `+0.5`，且
`context_pack_signal_observed=true`。默认本地 no-provider-env 路径仍真实
输出 `blocked_remote_not_enabled` 且 live-run 标志为 false。138/138 self-test
checks 通过。

这是 smoke-only。它**不**声明下游 agent 价值，**不**声明 live agent
泛化，**不**声明外部基准测试性能，**不**声明真实用户任务，**不**提升
任何 candidate，也**不**改变 runtime/retriever/pack/backend/
default-policy/EvidenceCore 语义。CI 通过意味着 live run completed +
privacy scan passed + artifact is honest；CI 通过**不**要求 treatment
改善（零/负 delta 有效）。per-run prompt、response、event log、
patch 和测试输出仅留在 `/tmp`，**绝不**提交或上传。honest signal
字段（`context_pack_signal_observed`、
`treatment_solve_rate_delta`、`treatment_wrong_file_edits_delta`）
是诊断 smoke 结果，**绝不**是 promotion/default/value 声明。所有无
声明 / 无运行时变更标志保持 false。live-run 标志**仅**在 live run
实际执行时为 true，否则为 false。不发布 raw model 路由前缀；仅记录
规范化的 `model_display_category`。未修改任何
runtime/retriever/pack/model/backend/default-policy 文件。正向 treatment delta 是
微型合成 smoke 信号，不是下游价值或泛化证明。详见
[B16-D 详细报告](b16d-less-trivial-live-provider-paired-smoke.md)。

## 当前状态更新 —— 2026-06-21（B16-E broader live-provider 下游 paired smoke）

继 B16-D 之后，B16-E 将 live-provider paired smoke 从单一任务族扩展为含
四个固定族的异构合成任务族矩阵。B16-E
（`eval/b16e_broader_live_provider_paired_smoke.py`，复用
`eval/provider_client.py`）->
`artifacts/b16e_broader_live_provider_paired_smoke/b16e_broader_live_provider_paired_smoke_report.json`，
schema `b16e_broader_live_provider_paired_smoke.v1`、
`claim_level=broader_live_provider_downstream_paired_smoke_only`、
`mode=public_aggregate_synthetic_task_family_matrix`、阶段 `B16-E`）
在四个族（`same_symbol_support_relation`、`operation_ambiguity`、
`boundary_condition`、`helper_dependency_choice`）中生成 8 个确定性任务，
为每个 task+arm 创建全新 `/tmp` 工作区，仅当 `--allow-remote` +
`OPENLOCUS_ALLOW_REMOTE=1` + provider env 时运行 **live LLM agent**
（OpenAI 兼容），本地应用模型的结构化 edit action（仅白名单
`target.py`），运行真实子进程测试，并在 paired `control_sparse` /
`treatment_context_pack` arms 上计算聚合行为指标 + 族级记录。手动 CI run `27902925812`（`real-provider-benchmark`，
`stage=b16e_broader_live_provider_paired_smoke`，
`enable_remote_models=true`）完成
`broader_live_provider_paired_smoke_pass` 并通过 privacy validation。已提交
artifact 现在镜像该 sanitized aggregate CI report：8 个合成任务 / 16 次 live
provider calls；21/21 provider calls succeeded；invalid JSON count 0；
forbidden scan pass；control_sparse solve_rate=0.125、tests_pass_rate=0.125；
treatment_context_pack solve_rate=1.0、tests_pass_rate=1.0；
treatment-minus-control solve/test delta `+0.875`；4/4 families had positive
solve-rate delta；`context_pack_signal_observed=true`。188/188 self-test checks
通过。

这是 smoke-only。它**不**声明下游 agent 价值，**不**声明 live agent
泛化，**不**声明外部基准测试性能，**不**声明真实用户任务，**不**提升
任何 candidate，也**不**改变 runtime/retriever/pack/backend/
default-policy/EvidenceCore 语义。CI 通过意味着 live run completed +
privacy scan passed + artifact is honest；CI 通过**不**要求 treatment
改善（零/负 delta 有效）。`honest_signals` 和 `family_signal_summary`
是诊断 smoke 结果，**绝不**是 promotion/default/value 声明。所有无
声明 / 无运行时变更标志保持 false。live-run 标志**仅**在 live run
实际执行时为 true，否则为 false。不发布 raw model 路由前缀；仅记录
规范化的 `model_display_category`。未修改任何
runtime/retriever/pack/model/backend/default-policy 文件。详见
[B16-E 详细报告](b16e-broader-live-provider-paired-smoke.md)。

## 当前状态更新 —— 2026-06-21（D5-A2 heldout 特征验证 smoke）

D5-A2 验证 D5-A1 的 retrieval-derived 特征 bucket 是否在新鲜 heldout
外部检索样本上复现。D5-A2
（`eval/d5a2_heldout_feature_validation.py`，向后兼容复用
C5-A/C5-C/C5-D/C5-E 原语；均未修改）->
`artifacts/d5a2_heldout_feature_validation/d5a2_heldout_feature_validation_report.json`，
schema `d5a2_heldout_feature_validation.v1`、
`claim_level=heldout_retrieval_feature_validation_smoke_only`、
`status=heldout_feature_validation_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`、
`mode=heldout_contextbench_repoqa_feature_validation`、阶段 `D5-A2`）
加载 D5-A1 已提交 artifact 作为预注册特征源（缺失/schema 不匹配/不安全
声明 flag 时 fail-closed），运行新鲜 heldout ContextBench verified
Python 行 21-40（抓取 40，评估切片 [20,40)）与 RepoQA Python needle
11-20（解析 20，评估切片 [10,20)），方法 bm25/regex/symbol，计算相同
固定 retrieval-derived utility proxy（与 F1-C/F1-D 不变），并检查 4 项
检索特征验证（bm25_vs_empty 量级/符号稳定性；regex/symbol_vs_bm25 符
号稳定性）。验证结果（固定 allowlist）：
`retrieval_feature_validation_supported`、
`retrieval_feature_validation_mixed`、
`retrieval_feature_validation_not_supported`、
`unavailable_with_reason`。仅 records 形态列表（`d5a1_input_record`、
`heldout_benchmark_method_records`、`validation_records`、
`validation_summary_records`）；无 per-unit metric 数组，无 row/needle
ID，无 winner/default/calibration 声明。811/118 self-test 检查通过。本地 heldout run 与手动 CI run `27915252367` 已通过：status `heldout_feature_validation_pass`，forbidden
scan pass，`validation_outcome=retrieval_feature_validation_supported`，
contextbench_rows_fetched=20，repoqa_needles_seen=10，network_calls=2，
provider_calls=0；所有 4 个 D5-A1 检索特征在 heldout 数据上复现
（bm25_vs_empty heldout +0.727961 正 supported；bm25 符号稳定性
heldout file_recall +0.6 正 supported；regex/symbol_vs_bm25 heldout
-0.977961 负 supported）。

这是 heldout 特征验证，**不是**校准。它**不是**校准、**不是**已校准
模型声明、**不是** policy/default 推荐、**不是** benchmark 结果、**不
是**下游 utility、**不是** true E/S 校准、**不是**外部基准测试性能声明、
**不是** leaderboard 条目、**不是**方法 winner、**不是** promotion/
default/runtime/retriever/pack/backend/EvidenceCore 语义变更。它仅验证
D5-A1 的检索特征稳定性；它 **不**验证 live-provider/下游对齐。所有无
声明 / 无运行时变更标志保持 false。
`heldout_feature_validation_executed=true` 仅在真实 heldout run 实际执行
时。详见 [D5-A2 详细报告](d5a2-heldout-feature-validation.md)。

## 当前状态更新 —— 2026-06-21（D5-A1 自动化校准特征表）

D5-A1 从实证 smoke 推进到 **校准就绪弱监督特征**，通过机器读取已提交
的聚合 artifact。D5-A1
（`eval/d5a1_automated_calibration_feature_table.py`，向后兼容复用
F1-D scanner 原语；均未修改）->
`artifacts/d5a1_automated_calibration_feature_table/d5a1_automated_calibration_feature_table_report.json`，
schema `d5a1_automated_calibration_feature_table.v1`、
`claim_level=automated_calibration_feature_extraction_only`、
`status=automated_calibration_feature_table_pass|fail_input_contract|fail_forbidden_scan`、
`mode=committed_aggregate_feature_extraction`、阶段 `D5-A1`）
机器读取已提交聚合 artifact（F1-D、F1-C、C5-C、C5-F、B16-E 必需；
D5-A0、B16-D 可选，若存在且 claim-safe），fail-closed 验证其 schema
与声明 flag，提取数值聚合信号（来自 F1-D 的检索稳健性；来自 C5-C+C5-F
的外部基准一致/分歧；来自 B16-E 的 live provider delta），并计算确定
性校准特征/bucket 记录（量级 bucket、符号稳定性 bucket、live provider
delta bucket、family 分布 bucket、跨信号对齐标签）与就绪 bucket
（`ready_for_manual_review`、`needs_more_live_downstream`、
`retrieval_only_insufficient`、`conflicting_signals`、
`insufficient_signal`）。推荐的下一步测量仅测量
（`manual_reference_audit`、`heldout_benchmark_scale`、
`live_downstream_scale`），**不是** policy/default/method winner。仅
records 形态列表（`input_artifact_records`、`signal_records`、
`calibration_feature_records`、`readiness_bucket_records`、
`recommended_next_measurement_records`）；无 per-unit metric 数组，无
原始输入 artifact 路径/内容，无 B16 任务文本，无
winner/best/default/calibrated-model/policy-recommendation 字段，无
E/S 校准记法。126/126 self-test 检查通过。本地特征提取 run 已通过：
status `automated_calibration_feature_table_pass`，forbidden scan pass，
7 个输入 artifact 加载（5 必需 + 2 可选），9 信号，7 特征，5 bucket
记录，2 测量；
cross_signal_alignment=`retrieval_robust_positive_plus_live_positive`，
readiness_bucket=`ready_for_manual_review`。

这是仅特征提取，**不是**校准。它**不是**校准、**不是**已校准模型声
明、**不是** policy/default 推荐、**不是** benchmark 结果、**不是**下
游 utility、**不是** true E/S 校准、**不是**外部基准测试性能声明、**不
是** leaderboard 条目、**不是**方法 winner、**不是**正式置信区间、**不
是** promotion/default/runtime/retriever/pack/backend/EvidenceCore 语义
变更。所有无声明 / 无运行时变更标志保持 false。
`automated_calibration_feature_extraction_performed=true` 仅在特征提取
实际执行时。详见
[D5-A1 详细报告](d5a1-automated-calibration-feature-table.md)。

## 当前状态更新 —— 2026-06-21（F1-D 跨基准检索 utility 稳健性 smoke）

F1-D 将 F1-C 从点估计扩展到 **诊断性 paired-bootstrap 置信/符号稳定性估
计**。F1-D
（`eval/f1d_cross_benchmark_retrieval_robustness.py`，向后兼容复用
F1-C/C5-C/C5-E/C5-A/C5-D 原语；均未修改）->
`artifacts/f1d_cross_benchmark_retrieval_robustness/f1d_cross_benchmark_retrieval_robustness_report.json`，
schema `f1d_cross_benchmark_retrieval_robustness.v1`、
`claim_level=cross_benchmark_retrieval_utility_robustness_smoke_only`、
`status=cross_benchmark_retrieval_robustness_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`、
`mode=bounded_contextbench_repoqa_retrieval_robustness`、阶段 `F1-D`）
对两个基准（ContextBench verified 20 行 + RepoQA 10 needle Python）
**重新运行真实有界外部数据**，在聚合前拦截 per-unit score 指标（仅在
内存或 `/tmp` 中），计算固定 retrieval-derived utility proxy
（`utility = file_recall@10 + 0.25*mrr + 0.5*span_f0.5@10 - miss_penalty`，
其中 `miss_penalty=0.25 if file_recall@10 == 0 else 0`；与 F1-C 不
变）、跨基准加权均值（按样本计数）以及 5 个固定 effect
（`bm25_vs_empty`、`regex_vs_empty`、`symbol_vs_empty`、
`regex_vs_bm25`、`symbol_vs_bm25`）跨 5 个 metric
（`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`、
`retrieval_utility`）的 paired bootstrap 置信/符号稳定性统计 = 25 条
bootstrap effect 记录，字段为 `effect_name`、`metric`、`point_estimate`、
`bootstrap_mean`、`ci_p05`、`ci_p50`、`ci_p95`、
`sign_positive_fraction`、`sign_negative_fraction`、
`sign_zero_fraction`、`sample_units`、`bootstrap_replicates`、
`bootstrap_seed`。跨基准重采样保持基准样本计数（ContextBench 20，
RepoQA 10）；paired effect 保持 treatment-baseline 配对。
`empty_retrieval` 是显式零上下文基线（无 retrieval run；所有指标/效用
为 0）。仅 records 形态（`benchmark_method_means`、
`cross_benchmark_method_means`、`bootstrap_effect_records`、
`input_summary`、`bootstrap_summary`）；无 per-unit metric 数组；无
F1-C 容器名；无动态 dict 镜像；无 winner/best/default 字段；无 E/S 校
准记法；ContextBench 与 RepoQA 失败类别保持分离。Bootstrap replicate
默认 1000（硬上限 2000），固定 seed 20240621。185/185 self-test 检查通
过。本地真实网络 run 与手动 CI run `27913035117` 已通过：20 行 ContextBench 抓取，10 个 RepoQA
needle 见到，status
`cross_benchmark_retrieval_robustness_pass`，forbidden scan pass，
provider_calls=0，bootstrap_record_count=25；点估计与 F1-C delta 一致
（`bm25_vs_empty` retrieval_utility = +0.465035，`regex_vs_bm25` =
-0.715035）；`bm25_vs_empty` retrieval_utility bootstrap
CI=[+0.298938, +0.464512, +0.624026]，sign_positive=1.0；
`regex_vs_bm25` retrieval_utility CI=[-0.874026, -0.714511,
-0.548938]，sign_negative=1.0。

这是 smoke-only。bootstrap 统计是诊断性稳健性估计，**不是**正式外部
基准置信区间。它**不是**下游效用，**不是** true E/S 校准，**不是**外
部基准测试性能声明，**不是** leaderboard 条目，**不是**方法 winner，
**不是**正式置信区间，**不是** promotion/default/runtime/retriever/
pack/backend/EvidenceCore 语义变更。所有无声明 / 无运行时变更标志保持
false。`retrieval_utility_robustness_smoke=true` 与
`bootstrap_computed=true` 仅在真实网络 run 实际执行时。详见
[F1-D 详细报告](f1d-cross-benchmark-retrieval-robustness.md)。

## 当前状态更新 —— 2026-06-21（F1-C 跨基准 retrieval-derived utility smoke）

F1-C 是 **跨基准测试** retrieval-derived utility smoke。F1-C
（`eval/f1c_cross_benchmark_retrieval_utility.py`，向后兼容复用
C5-C/C5-E/C5-A/C5-D 原语；均未修改）->
`artifacts/f1c_cross_benchmark_retrieval_utility/f1c_cross_benchmark_retrieval_utility_report.json`，
schema `f1c_cross_benchmark_retrieval_utility.v1`、
`claim_level=cross_benchmark_retrieval_derived_utility_smoke_only`、
`status=cross_benchmark_retrieval_utility_pass|partial_with_exclusions|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`、
`mode=bounded_contextbench_repoqa_retrieval_utility`、阶段 `F1-C`）
对两个基准（ContextBench verified 20 行 + RepoQA 10 needle Python）
**重新运行真实有界外部数据**，按 benchmark/method 计算固定
retrieval-derived utility proxy
（`utility = file_recall@10 + 0.25*mrr + 0.5*span_f0.5@10 - miss_penalty`，
其中 `miss_penalty=0.25 if file_recall@10 == 0 else 0`）、跨基准加权
均值（按样本计数）以及 5 个固定 counterfactual effects
（`bm25_vs_empty`、`regex_vs_empty`、`symbol_vs_empty`、
`regex_vs_bm25`、`symbol_vs_bm25`）。`empty_retrieval` 是显式零上下文
基线（无 retrieval run；所有指标/效用为 0）。仅 records-shaped；无动态
dict 镜像；无 winner/best/default 字段；无 E/S 校准记法；
ContextBench 与 RepoQA 失败类别保持分离。167/167 self-test checks 通过。
本地真实网络 run 与手动 CI run `27911651758` 已通过：20 行 ContextBench 抓取，10 个 RepoQA needle
见到，status `cross_benchmark_retrieval_utility_pass`，forbidden scan
pass，provider_calls=0；bm25 跨基准加权均值 file_recall@10=0.4 /
mrr=0.218477 / span_f0.5@10=0.020831 / success_rate=1.0 /
retrieval_utility=0.465035；`bm25_vs_empty` retrieval_utility
delta=+0.465035；`regex_vs_bm25` 与 `symbol_vs_bm25`
retrieval_utility delta=-0.715035。

这是 smoke-only。它**不是**下游效用，**不是** true E/S 校准，**不
是**外部基准测试性能声明，**不是** leaderboard 条目，**不是**方法
winner，**不是** promotion/default/runtime/retriever/pack/backend/
EvidenceCore 语义变更。所有无声明 / 无运行时变更标志保持 false。
`retrieval_derived_counterfactual_utility_smoke=true` 仅在真实网络
run 实际执行时。详见
[F1-C 详细报告](f1c-cross-benchmark-retrieval-utility.md)。

## 当前状态更新 —— 2026-06-21（F1-B retrieval-derived counterfactual utility smoke）

F1-B 将 F1 从纯合成 context variants 推进到 **retrieval-derived**
counterfactual utility。F1-B（`eval/f1b_retrieval_derived_counterfactual_utility_smoke.py`，
向后兼容导入 C5-A helpers）->
`artifacts/f1b_retrieval_derived_counterfactual_utility/f1b_retrieval_derived_counterfactual_utility_report.json`，
schema `f1b_retrieval_derived_counterfactual_utility_smoke.v1`、
`claim_level=retrieval_derived_counterfactual_utility_smoke_only`、
`mode=public_aggregate_contextbench_retrieval_counterfactual`、阶段
`F1-B`）使用真实 ContextBench verified rows、临时 /tmp repo clones、
真实 OpenLocus retrieval（bm25,regex,symbol）及 `eval/score.py` 指标
计算聚合 counterfactual candidate-set 效用 delta。五个 variants
（`baseline_empty_candidate_set`、`bm25_topk`、`regex_topk`、
`symbol_topk`、`bm25_plus_symbol_topk`）和四个 effects
（`bm25_candidates_vs_empty`、`regex_candidates_vs_empty`、
`symbol_candidates_vs_empty`、`symbol_added_to_bm25`）。指标：
`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`。
Records-shaped `variant_results`、`counterfactual_effects`、
`method_inputs`。无 provider 调用。无 winner/best/default 字段。
无 E/S 校准记法。95/95 self-test checks 通过。
手动 CI run `27903995230` 已通过：5 行抓取/成功，forbidden scan pass，
`bm25_topk` file_recall@10=0.4 / mrr=0.225 /
span_f0.5@10=0.015905 / success_rate=1.0，`regex_topk` 与
`symbol_topk` file_recall@10=0.0，`symbol_added_to_bm25` delta=0.0。

这是 smoke-only。它**不是**下游效用，**不是** true E/S 校准，**不
是**外部基准测试性能声明，**不是** leaderboard 条目，**不是**
promotion/default/runtime/retriever/pack/backend/EvidenceCore 语义变
更。所有无声明 / 无运行时变更标志保持 false。
`retrieval_derived_counterfactual_utility_smoke=true` 仅在真实网络
run 实际执行时。详见
[F1-B 详细报告](f1b-retrieval-derived-counterfactual-utility.md)。

## 当前状态更新 —— 2026-06-21（C5-A ContextBench verified 检索性能 smoke）

继 D5-A0 与 B16-A 之后，C5-A 产出第一个外部-benchmark-形态的检索性能
smoke。C5-A
（`eval/c5_contextbench_verified_performance_smoke.py` ->
`artifacts/c5_contextbench_verified_performance_smoke/c5_contextbench_verified_performance_smoke_report.json`，
schema `c5_contextbench_verified_performance_smoke.v1`、
`claim_level=external_benchmark_retrieval_performance_smoke_only`、
`status=pass|partial|unavailable_with_reason`、
`mode=contextbench_verified_retrieval_performance_smoke`、阶段
`C5-A`）从 HF datasets-server `/rows` 读取有界 ContextBench verified
subset（默认 5 行；硬上限 20；仅 stdlib `urllib`），将 `gold_context`
JSON 解析为临时 `gold_paths`/`gold_lines`（`content` 字段**绝不**读取或
持久化），将 `problem_statement` sanitizer 为检索 query（仅内存中；
first paragraph / first sentence / raw），在每行
`TemporaryDirectory` 下通过 `git clone --filter=blob:none --no-checkout`
然后 `git checkout` 克隆 `repo_url` 到 `base_commit`（有界超时），在
`TemporaryDirectory` 下生成临时 task/label JSONL，通过
`eval/run_retrieval.py` 运行 OpenLocus 检索（`--method bm25 --cwd
<repo_root>`，无 provider 调用），运行 `eval/score.py` 并解析 aggregate
metrics，仅写入 aggregate 计数/比率/均值到提交的 artifact。113/113
self-test 检查通过；5 行抓取，5 行成功，0 行失败。

这是 smoke-only。它**不**声称外部 benchmark 结果、**不**声称 leaderboard
条目、**不**声称性能、**不**声称 promotion、**不**声称默认变更、**不**
声称 runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不**声称
下游 agent 价值。原始 ContextBench 行、queries、repo URL/名称、base
commit、gold paths/spans/contents、生成的 task/label/run JSONL、evidence
行、克隆仓库与 stdout/stderr 仅保留在 `/tmp` 下，**绝不**提交或上传。
提交的 artifact 是 aggregate-only。所有无声明 / 无运行时变更标志保持
false（`external_benchmark_performance_claimed=false`、
`downstream_agent_value_proven=false`、`promotion_ready=false`、
`default_should_change=false`、`runtime_behavior_changed=false`、
`retriever_changed=false`、`pack_builder_changed=false`、
`backend_changed=false`、`default_policy_changed=false`、
`evidencecore_semantics_changed=false`、`provider_calls_made=false`、
`remote_provider_calls_made=false`）。Safe true 标志（仅当实际为真时为
true：`external_benchmark_rows_read`、
`repositories_materialized_transiently`、`openlocus_retrieval_executed`、
`score_py_metrics_computed`、`performance_smoke`、
`aggregate_only_public_artifact`、`diagnostic_only`）是仅有的额外 true
标志。如果网络 smoke 无法完成（网络/HF/GitHub 失败、克隆超时、检索失败、
打分失败），artifact 记录真实的 `unavailable_with_reason`，带有真实的
`failure_reason_category`（无 stale/fake pass）。未修改任何
runtime/retriever/pack/model/backend/default-policy 文件。详见
[C5-A 详细报告](c5-contextbench-verified-performance-smoke.md)。

## 当前状态更新 —— 2026-06-21（C5-B ContextBench verified 检索方法矩阵 smoke）

继 C5-A 之后，C5-B 产出首个外部-benchmark-形态检索性能 smoke 的有界多方法
矩阵扩展。C5-B
（`eval/c5b_contextbench_verified_method_matrix_smoke.py` ->
`artifacts/c5b_contextbench_verified_method_matrix/c5b_contextbench_verified_method_matrix_report.json`，
schema `c5b_contextbench_verified_method_matrix_smoke.v1`、
`claim_level=external_benchmark_retrieval_method_matrix_smoke_only`、
`status=pass|partial|unavailable_with_reason|fail_schema_contract|fail_forbidden_scan`、
`mode=contextbench_verified_retrieval_method_matrix_smoke`、阶段 `C5-B`）从
HF datasets-server `/rows` 读取有界 ContextBench verified subset **一次**
（每方法默认 5 行；硬上限 10；跨所有方法共享；仅 stdlib `urllib`），将
`gold_context` JSON 解析为临时 `gold_paths`/`gold_lines`（`content` 字段
**绝不**读取或持久化），将 `problem_statement` sanitizer 为检索 query（仅
内存中；first paragraph / first sentence / raw），在每行
`TemporaryDirectory` 下通过 `git clone --filter=blob:none --no-checkout`
然后 `git checkout` 克隆 `repo_url` 到 `base_commit`（有界超时），在
`TemporaryDirectory` 下生成临时 task/label JSONL，通过
`eval/run_retrieval.py` 跨请求方法矩阵运行 OpenLocus 检索（默认
`bm25,regex,symbol`；允许 `bm25,regex,text,symbol`；固定
`baseline_method=bm25`；`--method <method> --cwd <repo_root>`，无 provider
调用），每方法运行 `eval/score.py` 并解析 aggregate metrics，并**仅**将
每方法 aggregate 记录 + 与固定 `bm25` baseline 的仅 aggregate delta 写入
提交的 artifact。161/161 self-test 检查通过；抓取 5 行（跨方法共享），3 个
方法请求（bm25, regex, symbol），3 个方法成功，0 个方法失败。

这是 smoke-only。它**不**声称外部 benchmark 结果、**不**声称 leaderboard
条目、**不**声称性能、**不**声称 promotion、**不**声称默认变更、**不**
声称 runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不**声称
下游 agent 价值。它**不**输出 `winner`、`best_method`、
`recommended_default` 或任何暗示策略/默认决策的字段。`baseline_method`
固定为 `bm25`、`baseline_is_policy_candidate=false`、
`default_should_change=false`。原始 ContextBench 行、queries、repo URL/名称、
base commit、gold paths/spans/contents、生成的 task/label/run JSONL、
evidence 行、克隆仓库、每行 metrics、行级 hash 与 stdout/stderr 仅保留在
`/tmp` 下，**绝不**提交或上传。提交的 artifact 是 aggregate-only。所有
无声明 / 无运行时变更标志保持 false
（`external_benchmark_performance_claimed=false`、
`leaderboard_entry_claimed=false`、
`downstream_agent_value_proven=false`、`promotion_ready=false`、
`default_should_change=false`、`baseline_is_policy_candidate=false`、
`runtime_behavior_changed=false`、`retriever_changed=false`、
`pack_builder_changed=false`、`backend_changed=false`、
`default_policy_changed=false`、`evidencecore_semantics_changed=false`、
`provider_calls_made=false`、`remote_provider_calls_made=false`）。Safe
true 标志（仅当实际为真时为 true：`external_benchmark_rows_read`、
`repositories_materialized_transiently`、`openlocus_retrieval_executed`、
`score_py_metrics_computed`、`method_matrix_smoke`、
`aggregate_only_public_artifact`、`diagnostic_only`）是仅有的额外 true
标志。如果网络 smoke 无法完成（网络/HF/GitHub 失败、克隆超时、检索失败、
打分失败），artifact 记录真实的 `unavailable_with_reason`，带真实的
`failure_reason_category`（无 stale/fake pass）。未修改任何
runtime/retriever/pack/model/backend/default-policy 文件。见
[C5-B 详细报告](c5b-contextbench-verified-method-matrix-smoke.md)。

## 当前状态更新 —— 2026-06-21（C5-C ContextBench verified 方法矩阵 scale smoke）

继 D5-A0、B16-A、C5-A 与 C5-B 之后，C5-C 产出首个外部-benchmark-形态的
检索方法矩阵 scale smoke。C5-C
（`eval/c5c_contextbench_verified_method_matrix_scale_smoke.py` ->
`artifacts/c5c_contextbench_verified_method_matrix_scale/c5c_contextbench_verified_method_matrix_scale_report.json`，
schema `c5c_contextbench_verified_method_matrix_scale_smoke.v1`、
`claim_level=external_benchmark_retrieval_method_matrix_scale_smoke_only`、
`status=contextbench_method_matrix_scale_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan`、
`mode=contextbench_verified_bounded_scale_method_matrix`、阶段
`C5-C`）将 C5-B 从 5 行方法矩阵扩展为有界 20 行方法矩阵 scale smoke。它从
HF datasets-server `/rows` **一次性**读取有界 20 行 ContextBench verified
subset（跨全部 3 个方法共享；硬上限 20；仅 stdlib `urllib`），在临时
`/tmp` 目录下通过 `git clone --filter=blob:none --no-checkout` 然后
`git checkout` 检出引用仓库到 `base_commit`（每方法+每行一次），跨请求方法
矩阵运行 OpenLocus 检索（默认 `bm25,regex,symbol`；C5-C 仅允许
`bm25,regex,symbol`；**不**允许 `text`；固定 `baseline_method=bm25`；无
provider 调用），通过 `eval/score.py` 对每种方法针对 benchmark label spans
打分，并仅提交一个 aggregate 公共报告，其中包含每方法记录（列表，**非**以
方法名为 key 的 dict）、可选的每方法 `aggregate_runtime_seconds`、仅
aggregate 的与固定 `bm25` baseline 的 delta，以及一个 `input_summary`
块。179/179 self-test 检查通过。手动 CI run `27905621090` 在 workflow 对
network-enabled run 改为 fail-closed 后通过：20 行抓取，3/3 方法成功，0 方法
失败；bm25 产出 file_recall@10=0.35、mrr=0.143107、span_f0.5@10=0.020838、
success_rate=1.0；regex 与 symbol 在此有界 smoke 上 file_recall@10=0.0、
mrr=0.0。

这是 smoke-only。它**不**声称外部 benchmark 结果、**不**声称 leaderboard
条目、**不**声称性能、**不**声称 promotion、**不**声称默认变更、**不**声称
runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不**声称下游
agent 价值。它**不**输出 `winner`、`best_method`、`recommended_default`
或任何暗示策略/默认决策的字段。原始 ContextBench 行、queries、repo URL/
名称、base commit、gold paths/spans/contents、生成的 task/label/run JSONL、
evidence 行、克隆仓库与 stdout/stderr 仅保留在 `/tmp` 下，**绝不**提交或
上传。提交的 artifact 是 aggregate-only。所有无声明 / 无运行时变更标志保持
false（`external_benchmark_performance_claimed=false`、
`leaderboard_entry_claimed=false`、
`downstream_agent_value_proven=false`、`promotion_ready=false`、
`default_should_change=false`、`baseline_is_policy_candidate=false`、
`runtime_behavior_changed=false`、`retriever_changed=false`、
`pack_builder_changed=false`、`backend_changed=false`、
`default_policy_changed=false`、`evidencecore_semantics_changed=false`、
`provider_calls_made=false`、`remote_provider_calls_made=false`）。Safe true
标志（仅当实际为真时为 true：`retrieval_scale_smoke_performed`、
`openlocus_retrieval_executed`、`score_py_metrics_computed`、
`aggregate_only_public_artifact`、`diagnostic_only`）是仅有的额外 true
标志。如果网络 smoke 无法完成（网络/HF/GitHub 失败、克隆超时、检索失败、
打分失败），artifact 记录真实的 `unavailable_with_reason`，带真实的
`failure_reason_category`（无 stale/fake pass）。未修改任何
runtime/retriever/pack/model/backend/default-policy 文件。见
[C5-C 详细报告](c5c-contextbench-method-matrix-scale-smoke.md)。

## 当前状态更新 —— 2026-06-21（C5-D RepoQA BM25 检索性能 smoke）

继 D5-A0、B16-A、C5-A、C5-B 与 C5-C 之后，C5-D 产出首个 RepoQA 形态的
检索性能 smoke。C5-D
（`eval/c5d_repoqa_bm25_retrieval_smoke.py` ->
`artifacts/c5d_repoqa_bm25_retrieval_smoke/c5d_repoqa_bm25_retrieval_smoke_report.json`，
schema `c5d_repoqa_retrieval_performance_smoke.v1`、
`claim_level=repoqa_retrieval_performance_smoke_only`、
`status=repoqa_retrieval_smoke_pass|partial|unavailable_asset_download_failed|unavailable_no_python_needles|unavailable_repo_clone_failed|fail_forbidden_scan|fail_schema_contract`、
`mode=repoqa_bounded_bm25_retrieval_smoke`、阶段 `C5-D`）从
`evalplus/repoqa_release` 下载 EvalPlus RepoQA release asset
`repoqa-2024-06-23.json.gz` 到内存字节（临时；**绝不**写入工作区），在内存
中解压，解析有界 RepoQA Python needle subset（默认 5 needle；硬上限 10；
**无**静默全语言回退），在临时 `/tmp` 目录下通过
`git clone --filter=blob:none --no-checkout` 然后 `git checkout` 检出引用
仓库到其 `commit_sha`，运行 OpenLocus `bm25` 检索（仅 bm25；无 provider
调用），通过 `eval/score.py` 对 `needle.path`/`start_line`/`end_line`
打分，并仅提交一个 aggregate 公共报告。219/219 self-test 检查通过；5
needle seen，5 needle successful，0 needle failed。
手动 CI run `27906775008` 已通过，aggregate metrics 与本地一致；已提交 artifact
现在镜像该 sanitized CI report：file_recall@10=0.6、mrr=0.46、
span_f0.5@10=0.041634、success_rate=1.0、forbidden scan pass，且 provider_calls=0。

这是 smoke-only。它**不**声称外部 benchmark 结果、**不**声称 leaderboard
条目、**不**声称性能、**不**声称 promotion、**不**声称默认变更、**不**声称
runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不**声称下游
agent 价值。它**不**输出 `winner`、`best_method`、`recommended_default`
或任何暗示策略/默认决策的字段。Release asset、原始 repo 记录、repo 名称/
URL、commit SHA、entrypoint 路径、topics、content、dependency、needle 名称/
描述/路径/start/end lines、生成的 task/label/run JSONL、evidence 行、克隆
仓库与 stdout/stderr 仅保留在 `/tmp` 或内存中，**绝不**提交或上传。提交
的 artifact 是 aggregate-only。所有无声明 / 无运行时变更标志保持 false
（`external_benchmark_performance_claimed=false`、
`leaderboard_entry_claimed=false`、
`downstream_agent_value_proven=false`、`promotion_ready=false`、
`default_should_change=false`、`runtime_behavior_changed=false`、
`retriever_changed=false`、`pack_builder_changed=false`、
`backend_changed=false`、`default_policy_changed=false`、
`evidencecore_semantics_changed=false`、`provider_calls_made=false`、
`remote_provider_calls_made=false`）。Safe true 标志（仅当实际为真时为
true：`repoqa_retrieval_smoke_performed`、`asset_downloaded_transiently`、
`repoqa_needles_parsed_in_memory`、
`repositories_materialized_transiently`、`openlocus_retrieval_executed`、
`score_py_metrics_computed`、`aggregate_only_public_artifact`、
`diagnostic_only`）是仅有的额外 true 标志。如果网络 smoke 无法完成
（asset 下载失败、无 Python needle、repo 克隆失败、检索失败、打分失败），
artifact 记录真实的 `unavailable_*`，带真实的
`failure_reason_category`（无 stale/fake pass）。未修改任何
runtime/retriever/pack/model/backend/default-policy 文件。见
[C5-D 详细报告](c5d-repoqa-bm25-retrieval-smoke.md)。


## 当前状态更新 —— 2026-06-21（C5-E RepoQA 方法矩阵检索 smoke）

继 D5-A0、B16-A、C5-A、C5-B、C5-C 与 C5-D 之后，C5-E 产出首个 RepoQA 形态
的检索方法矩阵 smoke。C5-E
（`eval/c5e_repoqa_method_matrix_smoke.py` ->
`artifacts/c5e_repoqa_method_matrix_smoke/c5e_repoqa_method_matrix_smoke_report.json`，
schema `c5e_repoqa_method_matrix_smoke.v1`、
`claim_level=repoqa_retrieval_method_matrix_smoke_only`、
`status=repoqa_method_matrix_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`、
`mode=repoqa_bounded_method_matrix_smoke`、阶段 `C5-E`）将 C5-D 从单方法
`bm25` 扩展为 `bm25,regex,symbol` 有界方法矩阵。它下载 EvalPlus RepoQA
release asset `repoqa-2024-06-23.json.gz` 到内存字节（临时；**绝不**写入
工作区），解析有界 RepoQA Python needle subset（每方法默认 5 needle；
硬上限 10；**无**静默全语言回退），在临时 `/tmp` 目录下（每方法+每 needle
一次）检出引用仓库到其 `commit_sha`，跨请求方法矩阵运行 OpenLocus 检索
（默认 `bm25,regex,symbol`；仅允许 `bm25,regex,symbol`；**不**允许
`text`；固定 `baseline_method=bm25`；无 provider 调用），通过
`eval/score.py` 对每种方法针对 `needle.path`/`start_line`/`end_line`
打分，并仅提交一个 aggregate 公共报告，其中包含每方法记录（列表，**非**
以方法名为 key 的 dict）、每方法 `aggregate_runtime_seconds`，以及仅
aggregate 的与固定 `bm25` baseline 的 delta。228/228 self-test 检查通过；
5 needle seen，3/3 方法成功，0 方法失败。
手动 CI run `27907731742` 已通过，aggregate metrics 与本地一致；已提交
artifact 现在镜像该 sanitized CI report。CI runtime 为 bm25=9.416s、
regex=6.969s、symbol=11.436s；provider_calls=0 且 forbidden_scan=pass。

这是 smoke-only。它**不**声称外部 benchmark 结果、**不**声称 leaderboard
条目、**不**声称性能、**不**声称 promotion、**不**声称默认变更、**不**声称
runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不**声称下游
agent 价值。它**不**输出 `winner`、`best_method`、`recommended_default`
或任何暗示策略/默认决策的字段。Release asset、原始 repo 记录、repo 名称/
URL、commit SHA、entrypoint 路径、topics、content、dependency、needle 名称/
描述/路径/start/end lines、生成的 task/label/run JSONL、evidence 行、克隆
仓库与 stdout/stderr 仅保留在 `/tmp` 或内存中，**绝不**提交或上传。提交
的 artifact 是 aggregate-only。所有无声明 / 无运行时变更标志保持 false。
Safe true 标志（仅当实际为真时为 true：
`repoqa_method_matrix_smoke_performed`、`asset_downloaded_transiently`、
`repoqa_needles_parsed_in_memory`、
`repositories_materialized_transiently`、`openlocus_retrieval_executed`、
`score_py_metrics_computed`、`aggregate_only_public_artifact`、
`diagnostic_only`）是仅有的额外 true 标志。如果网络 smoke 无法完成，
artifact 记录真实的 `unavailable_with_reason`，带真实的
`failure_reason_category`（无 stale/fake pass）。未修改任何
runtime/retriever/pack/model/backend/default-policy 文件。见
[C5-E 详细报告](c5e-repoqa-method-matrix-smoke.md)。

## 当前状态更新 —— 2026-06-21（C5-F RepoQA 10-needle 方法矩阵 scale smoke）

C5-F 将 C5-E 从每方法 5 个 RepoQA Python needle 扩展到每方法 10 个 needle，同时保持 C5-E 不变。C5-F（`eval/c5f_repoqa_method_matrix_scale_smoke.py` -> `artifacts/c5f_repoqa_method_matrix_scale/c5f_repoqa_method_matrix_scale_report.json`，schema `c5f_repoqa_method_matrix_scale_smoke.v1`、`claim_level=repoqa_retrieval_method_matrix_scale_smoke_only`、`status=repoqa_method_matrix_scale_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan|fail_schema_contract`、`mode=repoqa_bounded_10_needle_method_matrix_scale_smoke`、阶段 `C5-F`）在 `bm25,regex,symbol` 上运行 RepoQA 方法矩阵，默认/硬上限每方法 10 个 Python needle，固定 `baseline_method=bm25`，无 provider 调用，仅 aggregate records 和 deltas。191/191 self-test checks 通过；手动 CI run `27909885489` 看到 10 个 needle、3/3 方法成功、forbidden scan pass、provider_calls=0。Aggregate metrics：bm25 file_recall@10=0.5 / mrr=0.369216 / span_f0.5@10=0.020817 / success_rate=1.0；regex 与 symbol file_recall@10=0.0 / mrr=0.0 / span_f0.5@10=0.0 / success_rate=1.0。

这是 smoke-only。它不声明外部 benchmark 结果、leaderboard 条目、性能、promotion、默认变更、方法 winner、runtime/retriever/pack/backend/EvidenceCore 语义变更或下游 agent 价值。它不输出 `winner`、`best_method`、`recommended_default` 或 policy/default recommendation 字段。Raw RepoQA row/repo/needle values 和 generated files 均保持临时。详见 [C5-F 详细报告](c5f-repoqa-method-matrix-scale-smoke.md)。

## 当前状态更新 —— 2026-06-21（F1 反事实证据效用 smoke）

继 D5-A0、B16-A 与 C5-A 之后，F1 产出首个反事实证据效用 smoke。F1
（`eval/f1_counterfactual_evidence_utility_smoke.py` ->
`artifacts/f1_counterfactual_evidence_utility/f1_counterfactual_evidence_utility_report.json`，
schema `f1_counterfactual_evidence_utility_smoke.v1`、
`claim_level=counterfactual_evidence_utility_smoke_only`、
`status=counterfactual_evidence_utility_smoke_pass`、
`mode=public_aggregate_synthetic_micro_tasks`、阶段 `F1`）在代码中
生成确定性合成公开 micro bug 任务，为每个 task+variant 创建全新
`/tmp` 工作区，含真实微型 Python 模块 + stdlib 测试，运行**确定性
mock agent**（无 live LLM、无 provider 调用、无远程调用），在**六个
反事实 context variant**（`base_no_context`、`primary_only`、
`support_only`、`primary_plus_support`、`distractor_only`、
`primary_plus_distractor`）下执行**真实文件编辑**和**真实子进程测
试**，按 variant 计算聚合行为指标，并从聚合 variant 指标计算**五个
边际效用 delta**（`primary_context_vs_base`、
`support_context_vs_base`、`distractor_context_vs_base`、
`support_added_to_primary`、`distractor_added_to_primary`）。这些
delta 是因果形态的（variant 对 variant），使用刻意避开
`E_primary` / `S_support` 字段名形态的效用专属名称。一个
`theory_mapping` 块记录 `primary_context_vs_base` 对应 E-utility
smoke proxy，`support_added_to_primary` / `distractor_added_to_primary`
对应 S-conditional utility smoke proxy，但 F1 明确**不是**真实 E/S
校准（`true_e_s_calibration_claimed=false`、
`automated_e_s_full_calibration_claimed=false`、
`human_e_s_calibration_claimed=false`）。162/162 self-test 检查通
过；24 个任务；6 个 variant；共 144 次 run。

这是 smoke-only。它**不**声明下游 agent 价值，**不**声明 live agent
泛化，**不**声明外部基准测试性能，**不**声明真实用户任务，**不**
声明真实 E/S 校准，**不**提升任何 candidate，也**不**改变
runtime/retriever/pack/backend/default-policy/EvidenceCore 语义。
per-run event log、patch 和测试输出仅留在 `/tmp`，**绝不**提交或上
传。提交的 artifact 仅含聚合数据。所有无声明 / 无运行时变更标志保持
false（`live_llm_agent=false`、`provider_calls_made=false`、
`remote_provider_calls_made=false`、
`downstream_agent_value_proven=false`、`promotion_ready=false`、
`default_should_change=false`、`runtime_behavior_changed=false`、
`retriever_changed=false`、`pack_builder_changed=false`、
`backend_changed=false`、`default_policy_changed=false`、
`evidencecore_semantics_changed=false`、
`external_benchmark_performance_claimed=false`、
`live_agent_generalization_claimed=false`、
`real_user_task_claimed=false`、
`true_e_s_calibration_claimed=false`、
`automated_e_s_full_calibration_claimed=false`、
`human_e_s_calibration_claimed=false`）。确定性 mock run 标志
（`counterfactual_context_variants_executed`、
`deterministic_mock_agent`、`real_file_edits_performed`、
`subprocess_tests_executed`、`marginal_utility_metrics_computed`、
`aggregate_only_public_artifact`、`diagnostic_only`）是仅有的额外
true 标志。未修改任何 runtime/retriever/pack/model/
backend/default-policy 文件。详见
[F1 详细报告](f1-counterfactual-evidence-utility.md)。

## 当前状态更新 —— 2026-06-20（C4.1 外部 benchmark adapter / schema 就绪）

C4.1 是一个**有界的外部 benchmark adapter / schema 就绪**阶段，**不是**外部
benchmark 性能评估，**不是** benchmark 结果，也**不是** promotion 或默认策略
变更。它新增一个 evaluator（`eval/c4_external_benchmark_adapters.py`）与一个
canonical aggregate-only 公共 artifact
（`artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`，
schema `c4_external_benchmark_adapters.v1`，
`claim_level=adapter_schema_readiness_only`）。该 evaluator 实现了
ContextBench（`Contextbench/ContextBench`；`default/train` 1136、
`contextbench_verified/train` 500；license `unknown_dataset_license`，行级再分发
禁用）与 SWE-Explore（`SWE-Explore-Bench/SWE-Explore-Bench`；`default/train`
848；license `cc-by-nc-nd-4.0`，行级再分发与派生 label 发布均禁用）的内置已知
source/schema 元数据，将 `public_task` 与 `private_label`（行级 payload，永不
序列化）分离的合成内存行 adapter，仅用于合成 self-test / 私有内存校验的 line
range 归一化，针对所有公共 JSON 输出的严格 fail-closed forbidden scanner，仅通过
stdlib `urllib`（无新依赖）的有界 HF datasets-server schema smoke，以及排除时
间戳/网络/原始行/本地路径的确定性 `spec_hash`
（`9de6609359aa8de4cfe7ca50b1388ebc51d9ee2f016bb3bc6c34e253da5ef153`）。行级
benchmark 内容未被持久化到任何公共 artifact 或 doc。

验证：`python3 -m py_compile eval/c4_external_benchmark_adapters.py` PASS；
`python3 eval/c4_external_benchmark_adapters.py --self-test` PASS（9 组）；默
认 canonical artifact 生成 PASS（`forbidden_scan: pass`）；ContextBench（
`forbidden_scan: pass`、`new_network_calls: 4`）与 SWE-Explore（
`forbidden_scan: pass`、`new_network_calls: 3`）的真实 schema smoke PASS。
`/tmp` smoke 输出遵循与已提交 artifact 相同的 aggregate-only 边界。

所有 no-claim 标志保持 false：`promotion_ready=false`、
`default_should_change=false`、`evidencecore_semantics_changed=false`、
`runtime_clean_general_algorithm_claimed=false`、
`downstream_agent_value_proven=false`、`ood_temporal_supported=false`、
`quiver_systems_supported=false`。schema smoke 仅确认公共 HF datasets-server
schema 端点可达且可解析；它**不**确认 benchmark 质量、label 正确性或对任何下
游评估的适用性。合成 self-test 行不提供任何经验支持。详见
[`docs/zh/c4-external-benchmark-adapters.md`](c4-external-benchmark-adapters.md)。
下方 2026-06-16 的状态（Candidate-to-Evidence Conversion 阶段、P25
bucket_routed_v0 参考策略、B19 Model-Robust Selective Evidence Conversion 综合
候选）原样保留。

## 当前状态更新 —— 2026-06-16

OpenLocus is now in the **Candidate-to-Evidence Conversion** phase. The current
research question is no longer which retrieval channel is globally strongest;
it is how to convert high-reach, high-false-cost candidate pools into low
false-cost, citation-valid Evidence without weakening `EvidenceCore`.

The latest completed chain is:

```text
P46 reach/cost map
-> P47 request_more_context geometry diagnostic
-> P50 fixed-suite / anti-overfit gate
-> P48 request_more_context overlay simulator
-> P49 contrastive candidate pack scaffold
-> P52 metadata-only local verifier scaffold
-> P52A source materialization prerequisite
-> P52B source-backed local verifier feature matrix
-> P51 deterministic LLM span-narrow scaffold
-> P52C diagnostic local-verifier scoring simulator
-> P51-B LLM opt-in contract / dry-run payload validator
-> P57 generalization gate
-> P58 source-backed verifier calibration
-> P59 contrastive pack coverage & counterfactual study
-> P60 RMC policy v2 v0 comparison matrix
-> P61 pre-spend gate v0
-> P51-C0 live LLM micro-run planner / explicit opt-in gate
-> P62 generalization matrix aggregator v0
-> P63 cross-run slice collector / matrix runner v0
```

Key current conclusions:

```text
P25 bucket_routed_v0 remains the strongest reference policy.
symbol_regex_union remains the main candidate-reach lever, not a primary admission rule.
request_more_context is now a first-class diagnostic action, not Evidence.
P52A/P52B establish bounded local source materialization and source-shape diagnostics.
P52C adds fixed gold-free diagnostic score buckets, not verifier pass/fail.
P51/P51-B define future LLM span-narrow/filter entry points, but still no live LLM calls.
P57 adds a deterministic aggregate-only generalization-readiness gate after P51-B.
P58 adds aggregate source-backed verifier calibration as deterministic planning-hint buckets; it is not a verifier pass/fail, not admission, not Evidence, and not default/promotion/live readiness.
P59 adds a deterministic pre-spend diagnostic that rebuilds P49 packs and measures whether they contain the prerequisite contrastive information a later LLM role would need; it is not a quality evaluator, not admission, not Evidence, and not default/promotion/live readiness.
P60 adds a deterministic RMC policy comparison matrix that selects only the next diagnostic action; it reports aggregate routing counts and SCORE-phase gold-reach/false-cost diagnostics, but is not evidence, not admission, and does not select a winner or recommend a default.
P61 adds a deterministic aggregate-only pre-spend readiness gate that reports whether a future P51-C live LLM micro-run is worth considering; it is not authorization, not Evidence, and not default/promotion/live readiness.
P62 adds a deterministic aggregate-only generalization matrix aggregator that combines sanitized multi-slice aggregate report sets; it deduplicates identical signatures internally, publishes only counts, and is not quality evidence, not repo/dataset identity proof, and not default/promotion/live readiness.
P63 adds a deterministic offline aggregate-only cross-run slice collector and orchestrator that validates local artifact directories and runs P62 -> P57 -> P61; it does not fetch artifacts, call providers, or expose identities, and is not a fetcher, not quality evidence, not provider spend authorization, not repo/dataset diversity proof, and not default/promotion/live readiness.
P59B repairs the P59 hard-distractor/actionability precondition with a gold-free metadata_hard_distractor_proxy_v1; it does not relax P61 and does not use labels to construct packs.
P51-B now includes an explicit redaction-policy precondition, allowing P61 to distinguish "redaction is required and satisfied" from "redaction is missing" without constructing prompts or payloads.
promotion_ready=false and default_should_change=false.
EvidenceCore semantics are unchanged.
```

Recent validation completed after P52C/P51-B/P61:

```text
local deterministic regression: passed
p61 self_test: passed
p62 self_test: passed
p63 self_test: passed
p21_llm_rich self_test CI: 27601393249 green
p21_llm_rich ci_smoke CI: 27601488191 green
p21_llm_rich ci_smoke repo_id=js_express: 27601639934 green
```

Real cross-run P63 dry-run progression:

```text
initial manual P63 cross-run collection over four ci_smoke max_tasks=6 round_robin_public_buckets runs:
  py_flask      27637929480 green
  js_express    27637930877 green
  go_gin        27637932300 green
  rust_ripgrep  27637933749 green

P63 accepted sanitized slice dirs: 4/4
P62 distinct eligible slices: 4
P57 status: diagnostic_matrix_complete
P57 observed task aggregate: 24 tasks, positive=9, no_gold=15
P61 status: blocked_missing_actionability
P61 blocker: P59 actionability bucket = blocked_missing_hard_distractor

after P59B hard-distractor proxy repair and P51-B redaction-precondition repair,
manual P63 cross-run collection over four fresh ci_smoke max_tasks=6 round_robin_public_buckets runs:
  py_flask      27643271948 green
  js_express    27643273360 green
  go_gin        27643274763 green
  rust_ripgrep  27643276402 green

P63 accepted sanitized slice dirs: 4/4
P62 distinct eligible slices: 4
P57 status: diagnostic_matrix_complete
P61 status: micro_run_preconditions_met
P61 reason: all_required_preconditions_present
P51-B redaction policy status: required_defined_satisfied
```

Breakthrough Sprint B1 live LLM rich-candidate run:

```text
matrix:
  repos: py_flask, js_express, go_gin, rust_ripgrep
  tasks: 6 per repo, 24 total per output mode
  model: Kimi-K2.7-Code
  stage: p21_llm_rich

tool_call runs:
  py_flask      27674929320 green
  js_express    27674930653 green
  go_gin        27674932153 green
  rust_ripgrep  27674933629 green

json_schema_strict runs:
  py_flask      27675200878 green
  js_express    27675202356 green
  go_gin        27675203807 green
  rust_ripgrep  27675205460 green
```

The strongest B1 result is `llm_span_narrow` in tool-call mode: over 24 tasks it
increased added gold from 8 to 9, reduced added false spans from 43 to 5,
improved mean SpanF0.5 from 0.1099 to 0.2849, and reduced mean primary false
positive rate from 0.1250 to 0.0625. The same model under `json_schema_strict`
was schema-stable but slower and left more false spans (`8` vs `5` for
`llm_span_narrow`). This is the first post-gate live quality result showing that
rich candidate LLM span narrowing can convert high-noise candidate pools into
substantially lower-false-cost spans. It is not Evidence, not promotion, and not
a default change. See [`b1-live-llm-rich-candidate-run.md`](b1-live-llm-rich-candidate-run.md).

The first matrix proved that P62 -> P57 -> P61 could move beyond the single-slice
`insufficient_matrix` condition and exposed a concrete P59 hard-distractor
blocker. P59B repaired that blocker with a gold-free metadata hard-distractor
proxy, and the subsequent matrix reached `micro_run_preconditions_met`. This
still **does not** authorize live LLM spend: it is only a precondition signal.
Opening P51-C remains a separate explicit workflow/human decision with its own
provider-spend controls, prompt/payload privacy gates, and small micro-run plan.

The validation covered the deterministic P52C/P51-B/P61/P62 self-tests, docs i18n mirror,
workflow Python heredoc compilation, diff checks, artifact privacy gates,
self-test no-source-root behavior, default `ci_smoke` source-backed behavior, and
a small `js_express` cross-repo slice. It did **not** run the full nightly/weekly
matrix, full repo-language generalization, or a live P51-C LLM opt-in call.

Current detailed reports added in this phase:

- [`p61-pre-spend-gate.md`](p61-pre-spend-gate.md)
- [`p62-generalization-matrix-aggregator.md`](p62-generalization-matrix-aggregator.md)
- [`p63-cross-run-slice-collector.md`](p63-cross-run-slice-collector.md)
- [`p60-rmc-policy-v2.md`](p60-rmc-policy-v2.md)
- [`p52c-local-verifier-scoring-simulator.md`](p52c-local-verifier-scoring-simulator.md)
- [`p51b-llm-opt-in-contract.md`](p51b-llm-opt-in-contract.md)
- [`p51-llm-span-narrow-2-diagnostic.md`](p51-llm-span-narrow-2-diagnostic.md)
- [`p52b-source-backed-local-verifier-feature-matrix.md`](p52b-source-backed-local-verifier-feature-matrix.md)
- [`p52a-source-materialization-prerequisite.md`](p52a-source-materialization-prerequisite.md)

Recommended next step: proceed to B2/B3, not more precondition scaffolding. B2
should compare contrastive pack variants with real LLM quality metrics, and B3
should test request_more_context as a quality-improving strategy using the B1
span-narrow/filter signal. B1 is positive but small; it justifies targeted
expansion, not promotion/default changes.

Breakthrough Sprint B2 contrastive-pack quality experiment:

```text
layouts:
  topk_plain_v0
  topk_scores_provenance_v0
  contrastive_competitor_v0
  hard_distractor_contrast_v0

matrix:
  4 repos x 6 tasks x 4 layouts = 96 live tasks
  model: Kimi-K2.7-Code
  output: tool_call
```

B2 showed that contrastive structure is not automatically better. For
`llm_span_narrow`, `topk_plain_v0` kept the best PFP (`0.0625`) and full gold
retention (`9` added gold, `6` added false). `hard_distractor_contrast_v0`
reduced false spans from `6` to `5`, but killed two gold spans and doubled mean
PFP to `0.1250`. `topk_scores_provenance_v0` had the highest mean SpanF0.5
(`0.2829`) but increased false spans and latency. The immediate conclusion is to
route contrastive/hard-distractor packs selectively to filter/no-gold/hard-
distractor buckets, not to use them as a universal span-narrow pack. See
[`b2-contrastive-pack-quality-experiment.md`](b2-contrastive-pack-quality-experiment.md).

Breakthrough Sprint B1C cross-model rerun:

```text
matrix:
  4 repos x 6 tasks x topk_plain_v0
  Kimi-K2.7-Code tool_call
  Qwen3.6-27B tool_call + json_schema_strict
  GLM-5.2 tool_call + json_schema_strict
```

Kimi tool_call remains the primary reference: 24/24 schema-valid calls, zero
fallbacks, 9 added gold, 5 added false, mean SpanF0.5 0.2825, mean PFP 0.0625.
GLM-5.2 is viable under `json_schema_strict` (23/24 schema-valid, 7 added gold,
7 added false, mean SpanF0.5 0.2192) but tool_call remains noisy. Qwen3.6-27B
adds 27B dense model coverage, but both output modes hit rate-limit/fallback
noise, so this run is plumbing/rate-limit evidence rather than quality evidence.
See [`b1c-cross-model-rich-candidate-rerun.md`](b1c-cross-model-rich-candidate-rerun.md).

Breakthrough Sprint B3 request-more-context quality experiment:

```text
matrix:
  4 repos x 6 tasks
  model: Kimi-K2.7-Code
  output: tool_call
  treatments: P25, RMC-local, RMC-LLM, RMC-hybrid
```

B3 was a high-value negative result. Fixed RMC routing did not beat P25. P25
over the plain pack reached 8 added gold / 7 added false, mean SpanF0.5 0.0890,
and mean PFP 0.0417. Both `rmc_llm_pack_routed_v0` and `rmc_hybrid_v0` reached 7
added gold / 8 added false, mean SpanF0.5 0.0820, and mean PFP 0.0833.
`rmc_local_conservative_v0` avoided PFP but collapsed recall (4 gold / 18 false,
mean SpanF0.5 0.0226). The algorithmic conclusion is that RMC needs searched or
bucket-specific routing; fixed rules are too crude. See
[`b3-rmc-quality-experiment.md`](b3-rmc-quality-experiment.md).

Breakthrough Sprint B6-lite interpretable policy search:

```text
matrix:
  4 repos x 6 tasks
  model: Kimi-K2.7-Code
  stage: b6_lite_policy_search
```

B6-lite searched a small rule grammar over paired plain/hard-distractor P21
records. It found lower-false-cost hypotheses, but not robust policies. The best
aggregate searched candidate with P25-like gold was
`ambiguous_query_weak_only_default_use_p25_action` (8 gold / 6 false / PFP 0.0),
but it appeared on the frontier in only one repo and still used 12 LLM actions.
The conservative
`negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action`
achieved 5 gold / 2 false and positive net span value, but lower SpanF0.5. B6
therefore supports a B6B combined-matrix search with proper leave-one-repo-out;
it does not justify a default change. See
[`b6-lite-interpretable-policy-search.md`](b6-lite-interpretable-policy-search.md).

B6B combined-matrix policy search:

```text
run: 27689938744 green
matrix: 4 public repo slices x 6 tasks
claim: leave_one_repo_diagnostic_only
```

B6B trained the same small interpretable grammar on three repo slices and scored
the frozen policies on the held-out slice, then aggregated only public counts.
It found two lower-false-cost families worth follow-up. The strongest P25-like
candidate, `ambiguous_query_weak_only_default_use_p25_action`, preserved P25's
held-out added gold/SpanF0.5 in aggregate while reducing false spans (7 gold / 5
false vs P25's 7 / 8) and PFP (0.0 vs 0.0833). The conservative
`negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action`
reduced false further (4 gold / 1 false) but lost too much gold for deep-quality
use. Neither is a default; both require a fresh validation run on more repos and
model-robust checks. See
[`b6b-combined-policy-search.md`](b6b-combined-policy-search.md).

B6C frozen-policy fresh validation:

```text
run: 27706742419 green
matrix: 4 public repo slices x 6 tasks
model: Kimi-K2.7-Code tool_call
claim: frozen_policy_fresh_validation
search_performed: false
```

B6C froze the two B6B candidate policies before evaluation and validated them on
fresh paired records. The main policy candidate,
`ambiguous_query_weak_only_default_use_p25_action`, preserved P25's added gold
and mean SpanF0.5 while reducing false spans (8 gold / 5 false vs P25's 8 / 6),
removing observed PFP, and halving effective LLM actions (12 vs 24). The
conservative candidate reached 5 gold / 1 false with positive net span value but
lost too much gold for the deep-quality path. B6C supports a balanced-policy
hypothesis, not a default change. See
[`b6c-frozen-policy-validation.md`](b6c-frozen-policy-validation.md).

B6E expanded frozen-policy validation reused the same evaluator and frozen policy
spec on a larger fresh task matrix:

```text
run: 27717886432 green
matrix: 4 public repo slices x 12 tasks = 48 comparable tasks
model: Kimi-K2.7-Code tool_call
claim: frozen_policy_fresh_validation
search_performed: false
```

The main balanced-policy candidate again preserved P25's added gold and mean
SpanF0.5 while reducing false spans (13 gold / 14 false vs P25's 13 / 17),
removing observed PFP, and reducing estimated LLM actions (31 vs 47). This
strengthens the B6C balanced-policy hypothesis within the same four-repo public
universe. It is not repo-generalization, not cross-model validation, and not a
default change.

B6F repo-generalization smoke reused the same frozen policy spec on a different
set of four public repo slices:

```text
run: 27735809672 green
matrix: 4 new public repo slices x 12 tasks = 48 comparable tasks
model: Kimi-K2.7-Code tool_call
claim: frozen_policy_fresh_validation
search_performed: false
```

The main balanced-policy candidate again preserved P25's added gold and mean
SpanF0.5 while reducing false spans (8 gold / 20 false vs P25's 8 / 24),
removing observed PFP, and reducing estimated LLM actions (31 vs 47). This is the
first repo-generalization smoke supporting the balanced-policy hypothesis. It is
still single-model and low-n.

B8-lite medium-matrix aggregate rollup:

```text
sources: B6E 27717886432 + B6F 27735809672
scope: 8 public repo slices, 96 comparable tasks
new provider calls: 0
policy search performed: false
```

The derived rollup keeps the frozen-policy trend intact: the main balanced
candidate matches P25's added gold and weighted mean SpanF0.5 while reducing
false spans from 41 to 34, eliminating observed PFP, and reducing estimated LLM
actions from 94 to 62. This strengthens the balanced-policy candidate, but it is
a derived single-model aggregate, not a new live validation run or default
change. See [`b8-lite-medium-matrix-combiner.md`](b8-lite-medium-matrix-combiner.md).

B6D cross-adapter frozen-policy validation:

```text
run: 27716082836 green
adapter: GLM-5.2 json_schema_strict
status: not_quality_interpretable
schema_valid_rate: 0.75
infra_failure_rate: 0.25
direction_consistency: not_determinable
```

B6D completed successfully as a workflow and aggregate-report path, but it did
not produce quality-interpretable cross-adapter evidence. The GLM adapter health
was below threshold, so policy-family quality metrics remain null and no claim is
made about whether the B6C frozen policy transfers to GLM. Output mode is treated
as an adapter/profile configuration, not as a universal algorithm variable. See
[`b6d-cross-adapter-frozen-validation.md`](b6d-cross-adapter-frozen-validation.md).

B9A adapter-health screen:

```text
matrix:
  GLM-5.2 and Qwen3.6-27B
  tool_call and json_schema_strict adapter profiles
  2 public repo slices per adapter profile
  max_tasks=6, sequentially triggered jobs
```

B9A is not a quality leaderboard. It treats output mode as a model-adapter
configuration parameter and reports only adapter health. Qwen3.6-27B
`json_schema_strict` passed the small health screen (`schema_valid_rate=1.0`,
`infra_failure_rate=0.0`) and is a candidate for cautious low-volume follow-up.
GLM-5.2 `json_schema_strict` improved over tool-call behavior but remained below
quality-interpretable thresholds (`schema_valid_rate=0.833`,
`infra_failure_rate=0.333`). GLM tool-call and Qwen tool-call remain too noisy
for critical-path validation. See [`b9a-adapter-health-report.md`](b9a-adapter-health-report.md).

B9B Qwen low-volume quality follow-up:

```text
model: Qwen3.6-27B
adapter: json_schema_strict
matrix: 4 public repo slices x 6 tasks
execution: sequential jobs
schema_valid_rate: 1.0
infra_failure_rate: 0.0
```

Qwen json_schema_strict produced quality-interpretable live rich-candidate
results under the low-volume sequential discipline. `llm_span_narrow` reached 7
added gold / 4 added false, false_per_gold 0.571, mean SpanF0.5 0.2831, and mean
PFP 0.0625. This promotes Qwen from plumbing-only to a secondary
quality-interpretable adapter candidate for cautious low-volume follow-up, but it
is not a default model or output-mode leaderboard result. See
[`b9b-qwen-low-volume-quality-follow-up.md`](b9b-qwen-low-volume-quality-follow-up.md).

B9C Qwen frozen-policy validation:

```text
run: 27744695226 green
adapter: Qwen3.6-27B json_schema_strict
status: ok
quality_interpretable: true
direction_consistency: consistent_with_kimi
```

B9C reused the B6C frozen balanced policy under the health-stable Qwen adapter.
The balanced policy preserved P25's added gold and mean SpanF0.5 while reducing
false spans from 5 to 4, removing observed PFP, and cutting estimated LLM actions
from 24 to 12. This is a low-n smoke, but it is the first secondary-adapter
support for the balanced-policy direction. See
[`b9c-qwen-frozen-policy-validation.md`](b9c-qwen-frozen-policy-validation.md).

B9D DeepSeek/GLM participation screen:

```text
DeepSeek-V4-Flash tool_call/json_schema_strict:
  schema_valid_rate=1.0, infra_failure_rate=0.0
  span_narrow: 4 gold / 3 false on 12 tasks

DeepSeek-V4-Pro tool_call/json_schema_strict:
  schema_valid_rate=1.0, infra_failure_rate=0.0
  span_narrow: 2 gold / 1 false on 12 tasks

GLM-5.2:
  still noisy from B9A/B6D; keep opt-in exploratory only
```

B9D is not a model leaderboard. It gives participation recommendations:
DeepSeek Flash/Pro are healthy enough for future exploratory involvement, GLM
remains supported but not critical-path, Qwen json_schema_strict remains the best
current secondary validation adapter, and Kimi tool_call remains the primary
reference. See [`b9d-deepseek-glm-participation-screen.md`](b9d-deepseek-glm-participation-screen.md).

B4/B9 model-robust evidence conversion digest:

```text
inputs:
  B1, B1C, B2, B3 live aggregate quality cells
outputs:
  algorithm_spec vs model_adapter separation
  matched-baseline treatment deltas where available
  low-n claim levels, not universal algorithm claims
```

B4/B9 deliberately prevents the Kimi result from becoming the OpenLocus
algorithm. `span_narrow_topk_plain_v0` is only a `low_n_directional_signal` on
the two matched Kimi adapter deltas; GLM-5.2 json_schema_strict is secondary
observed cross-family validation because no matched baseline delta is available.
B9B/B9C later upgrade Qwen json_schema_strict to secondary low-volume support,
but the original B4/B9 aggregate remains unchanged. Fixed RMC variants remain
`not_supported`. See
[`b4-b9-model-robust-evidence-conversion.md`](b4-b9-model-robust-evidence-conversion.md).

B10 运行期特征审计 + balanced policy v1 冻结：

```text
algorithm_spec_id: balanced_policy_v1_benchmark_routed
claim_level: benchmark_routed_algorithm_spec_only
source frozen candidate: ambiguous_query_weak_only_default_use_p25_action
frozen spec hash matched: true
runtime_clean: false
runtime_feature_only_mode_supported: false
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
model_adapter / output_mode / provider 凭证: 被排除的 adapter 层
```

B10 把 B6C 主 balanced candidate 冻结为 algorithm spec
`balanced_policy_v1_benchmark_routed`，并审计该 spec 实际读取的每一条 routing feature 的
provenance。`ambiguous_or_query_noise` 即 `_ambiguous_like or _query_noise`：
`_ambiguous_like` 读取 benchmark 公开标签 `task_bucket`/`task_risk_tags`，`_query_noise`
读取确定性 runtime feature `route_features.query_noise`。默认 `use_p25_action` 委托给
`p25.route_bucket_routed_v0`，继承 P25 route_features（`candidate_count`、
`candidate_support_exists`）。P25 exact/unique 短路当前由 bucket labels 驱动，而不是读取
runtime `unique_symbol_anchor` route feature。`runtime_clean=false`，因为
`_ambiguous_like` 分支依赖 `task_bucket`/`task_risk_tags`，runtime-feature-only 模式下
`ambiguous_query_weak_only` 规则永不触发。路由不使用任何 score-private 字段
（`score_private_dependencies_for_routing=[]`）；`has_gold`/`score_group`/`outcome_metrics`
仅用于聚合打分。这是 benchmark-routed 研究 algorithm spec only——不是 runtime-feature-only
policy、不是 default 变更、不是 promotion。下一步是 `balanced_policy_v1_runtime_shadow`：
用纯 runtime features（`query_noise`、`candidate_support_exists`、anchor disagreement）
替换 ambiguous bucket/tag 分支，并对该 spec 做 action-agreement replay。详见
[`b10-runtime-feature-audit.md`](b10-runtime-feature-audit.md)。

B10B runtime-shadow replay（仅 ambiguous 分支）：

```text
algorithm_spec_id: balanced_policy_v1_runtime_shadow_ambiguous_branch
claim_level: ambiguous_branch_runtime_shadow_only
full_runtime_clean_policy: false
ambiguous_branch_runtime_shadow_only: true
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
quality_strategy_tuned: false
runtime_calls_by_replay: 0
model_calls_by_replay: 0
replay_source: synthetic_fixture
runtime_shadow_ambiguous_supported: false
support_claim: mechanics_only_synthetic_fixture
support_claim_reason: synthetic_fixture_only
```

B10B 是 B10 冻结之后的下一步。它不跑模型、不搜索、不调整策略质量、不默认化。它只测试
一个固定预先声明的、仅依赖 runtime feature 的 shadow predicate，能否在同批记录上复现
冻结 `balanced_policy_v1_benchmark_routed` 的 **ambiguous 分支**动作。shadow predicate
只读取 runtime `route_features`（`query_noise`、`candidate_support_exists`、
`local_anchor`、`rrf_backed_by_anchor`），绝不读取 `task_bucket`/`task_risk_tags`/
`has_gold`/`score_group`/outcome metrics；`runtime_shadow_ambiguous = query_noise OR
(candidate_support_exists AND anchor_disagreement_proxy)`，其中
`anchor_disagreement_proxy = local_anchor AND NOT rrf_backed_by_anchor`。如果任意所需
runtime feature 缺失，该记录被标记为 missing，shadow action 不会被静默默认为 false；若
所有记录均缺失所需 feature，状态为 `insufficient_runtime_features`。强化后的 evaluator 还
携带：10 个 predeclared acceptance gates（其中
`label_driven_ambiguous_min_denominator: 10` 是 HARD gate，**不是** escape clause）、
分层 agreement metrics（`target_weak_only_recall`、`target_use_p25_specificity`、
`shadow_weak_only_precision`、`label_driven_ambiguous_recall_qn0`、
`query_noise_only_recall_qn1`）、silent-failure 检查（`all_shadow_ambiguous`、
`all_shadow_non_ambiguous`、`base_rate_only_suspected`、`no_silent_failure`）、直接实现的
Cohen's kappa（不依赖 numpy/sklearn）、不一致子集上的 4 分区 outcome-equivalence 审计
（`outcome_audit`，仅审计 —— outcome 绝不回馈到路由）、verdict 框架
（`runtime_shadow_ambiguous_supported` + `support_claim` + `support_claim_reason`）、
`replay_source` 参数（`synthetic_fixture` vs `ci_ephemeral_records`），以及用于 CI 集成的
CLI `--records <path>` 模式。leakage guard 现在除了修改
`task_bucket`/`task_risk_tags`/`has_gold`/`score_group` 之外，还会修改 `outcome_metrics`。
公开 report 仅聚合，不含任何禁用公开键或原始 path/digest/provider 字符串。**B10B 不证明
runtime-clean balanced policy**；在 synthetic fixture 上的当前 verdict 为
`runtime_shadow_ambiguous_supported=false`、
`support_claim="mechanics_only_synthetic_fixture"`、
`replay_source="synthetic_fixture"` —— 即 **mechanics-validated scaffold、empirical
validation 待补**，而非 empirical-support claim。默认 `use_p25_action` 仍委托给 P25
benchmark-routed 行为，因此这只是仅 ambiguous 分支的 runtime-shadow。B11 应被 framing 为
**exploratory prospective stress test**，**不是** “supported validation”，直到 B10B 在
真实 CI ephemeral 记录上运行且通过所有 predeclared gate。详见
[`b10b-runtime-shadow-replay.md`](b10b-runtime-shadow-replay.md)。

B11 prospective blind validation：

```text
algorithm_spec_id: balanced_policy_v1_benchmark_routed (frozen, B10)
claim_level: prospective_validation_preregistration
new_repos_new_tasks_after_freeze: true
retuning_after_live_runs: false (forbidden by preregistration)
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
quality_strategy_tuned: false
live_llm_runs_require_workflow_dispatch: true
```

B11 是冻结的 balanced policy `balanced_policy_v1_benchmark_routed` 的第一次真正
**prospective** validation。此前的 validation（B6C/B6E/B6F/B8-lite/B9C）共享同一套 task
生成与研究 universe；B11 使用 2026-06-18 policy freeze 之后生成的新 repos 与新 tasks，
不对 policies、thresholds 或 success criteria 做任何 retuning。preregistration 在任何
live runs 之前冻结 artifacts（B10 spec、B10B shadow predicate、
`rmc_local_conservative_v0`、`p25.route_bucket_routed_v0`、B10B 10 个 gate 与 verdict
框架）以及所有 success/failure/partial criteria；任何 post-hoc analysis 必须标注为
exploratory。

Scope 分为 minimum viable 首轮（8 repos，5 languages，~120 tasks，4 models，每个
model family 4-6 小时 CI）与有前景时的 full round（12-16 repos，300-500 tasks）。
Minimum viable 的 8 个 repos 为 `py_fastapi`、`py_pytest`、`ts_vite`、`ts_hono`、
`go_chi`、`go_prometheus`、`rust_deno`、`java_spring_petclinic` —— 全部为新，均未用于
B6B/B6C/B6E/B6F/B8-lite。

B11 覆盖 4 个 model families：Kimi（`Kimi-K2.7-Code`，`tool_call`，reference）、
Qwen（`Qwen3.6-27B`，`json_schema_strict`，secondary）、DeepSeek Flash
（`DeepSeek-V4-Flash`，`json_schema_strict`，recall）与 DeepSeek Pro
（`DeepSeek-V4-Pro`，`json_schema_strict`，conservative）。GLM-5.2 因按 B9A/B6D 噪声大
被排除。Output mode 是 model-adapter 配置参数，**不是** OpenLocus algorithm 变量。比较
4 个 policies：Local baseline（无 LLM）、P25 `p25.route_bucket_routed_v0`、Balanced v1
`balanced_policy_v1_benchmark_routed` 与 Conservative
`rmc_local_conservative_v0`。

Predeclared success/failure/partial criteria 在 `Δgold_span`、`ΔSpanF0.5`、`ΔPFP`、
`Δfalse_spans`、`ΔLLM_calls`（Balanced v1 vs P25）上使用显式 overall 与 worst-group
thresholds，另加 `RobustUtility` =
`min_group(SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency)` 聚合，参数
`λ=1.0`、`μ=0.1`、`ν=0.1`。B10B integration：B10B `--records` 在每次 B11 run 之后于 CI 中
运行（已通过 commit `2cbdd0c` 集成），给 B10B 带来首次 empirical validation
（`replay_source="ci_ephemeral_records"`）。B11 是 prospective stress test，**不是**
promotion step：即使成功，`promotion_ready=false`。plan、CI workflow 定义与
report-aggregator skeleton 可自主完成；实际 live LLM runs 需要用户 `workflow_dispatch`
触发且 `enable_remote_models=true`。详见
[`b11-prospective-blind-validation.md`](b11-prospective-blind-validation.md)。

B11 official integrated matrix 结果（2026-06-18）：

```text
algorithm_spec_id: balanced_policy_v1_benchmark_routed（冻结，B10）
claim_level: derived_aggregate_of_b11_prospective_validation_reports
matrix_status: 32/32 runs 完成（两次 transient provider_status 已重试）
record_count_total: 384
verdict_counts: {success: 8, partial: 23, failure: 1}
aggregate_verdict: partial_with_failure
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
quality_strategy_tuned: false
new_provider_calls_by_combiner: 0
aggregate_only_public_artifact: true
```

B11 official integrated matrix 在 8 个 public repo slice（`py_fastapi`、
`py_pytest`、`ts_vite`、`ts_hono`、`go_chi`、`go_prometheus`、`rust_deno`、
`java_spring_petclinic`）与 4 个 model family（`kimi`、`qwen`、
`deepseek_flash`、`deepseek_pro`）上完成 32/32 runs。两次 transient
`provider_status` 失败已重试；本聚合只滚动合并已下载的 aggregate-only public
B11/B10B artifacts（不读取任何 raw records、paths、prompts、responses、snippets
或 private labels）。

384 条记录的 overall weighted means
（`local_baseline` / `p25` / `balanced_v1` / `conservative`）：

```text
gold_span   : 0.377604 / 0.247396 / 0.244792 / 0.125000
false_span  : 1.203125 / 0.236979 / 0.182292 / 0.236979
span_f0_5   : 0.062197 / 0.064538 / 0.062639 / 0.023611
PFP         : 0.083333 / 0.020833 / 0.000000 / 0.000000
model_calls : 0.0      / 0.958333 / 0.604167 / 0.000000
```

balanced_v1 相对 P25 的 overall deltas：`Δgold_span -0.002604`、
`Δfalse_span -0.054688`、`ΔSpanF0.5 -0.001899`、`ΔPFP -0.020833`、
`Δmodel_calls -0.354167`。即 balanced_v1 在保持与 P25 近乎一致的
`SpanF0.5`/`gold_span` 的同时，减少了 false spans、PFP 与 model calls。
按 model family（balanced_v1 vs P25，每个 family 96 条记录加权）：
`deepseek_flash` partial 6 / success 2（`Δfalse_span -0.052083`、
`ΔPFP -0.010417`）、`deepseek_pro` partial 5 / success 3（`Δfalse_span
-0.083333`、`ΔPFP -0.031250`）、`kimi` partial 5 / success 2 / failure 1
（`Δgold_span -0.010417`、`ΔSpanF0.5 -0.007595`、`Δfalse_span -0.072917`、
`ΔPFP -0.031250`）、`qwen` partial 7 / success 1（`Δfalse_span -0.010417`、
`ΔPFP -0.010417`）。唯一失败为 Kimi `py_fastapi` slice，其
`failure_spanf05_delta` 阈值被超出。B10B runtime-shadow replay 在每次 B11 run
之后运行（32/32 报告）；所有 run 的 `runtime_shadow_ambiguous_supported` 均
为 `false`，`support_claim="empirical_replay_support_pending"`，原因为
`insufficient_label_driven_denominator`（观测到的最大
`label_driven_ambiguous_denominator_qn0=3`，远低于 10 条记录的 hard gate），
因此 B10B predicate 仍为 empirical-pending，**不是** runtime-clean general
algorithm 的证明。

Framing：B11 为 **mixed/partial**。该结果加强了 algorithm-candidate 信号
（balanced_v1 平均上保持近乎一致的 SpanF0.5/gold，同时减少 false spans、PFP
与 model calls），但**并未**证明一个 runtime-clean 的 general algorithm。无
promotion、无 default change、无 EvidenceCore semantics 变化。建议下一步：B12
mechanism decomposition，以识别哪些条件驱动 Kimi 失败与 mixed partials。聚合
artifact：
`artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`
（由 `eval/b11_matrix_combiner.py` 生成）。详见
[`b11-prospective-blind-validation.md`](b11-prospective-blind-validation.md)。

B12 mechanism decomposition：

```text
algorithm_spec_id: b12_mechanism_decomposition_v0
claim_level: mechanism_decomposition_v0
replay_only: true（evaluator 内无 live LLM calls）
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
quality_strategy_tuned: false
```

B12 是继 B11 之后的 **mechanism decomposition** 阶段。目标是通过 5 个 ablation
variants 与 4 个 predeclared hypotheses 理解**为什么**冻结的 balanced policy
`balanced_policy_v1_benchmark_routed`（B10）有效（若 B11 证实其泛化）。5 个
ablation variants 为：**A**（full balanced；`ambiguous→weak_only, else P25`）、
**B**（deterministic LLM reduction；P25 for all 但对 ambiguous tasks 跳过 LLM）、
**C**（ambiguous weak_only only；按构造 ≡A，因 balanced policy 只有一条 routing
rule）、**D**（P25 default only；baseline）、**E**（random LLM reduction；P25 for all
但随机跳过与 A 同样数量的 LLM calls）。4 个 hypotheses 为：**H1**（ambiguous
routing —— 增益来自 `ambiguous→weak_only` rule）、**H2**（LLM call reduction ——
增益来自任何 LLM-call reduction）、**H3**（P25 fallback sufficiency —— routing rule
无益）、**H4**（model-specific —— effect sizes 在 model families 间显著变化）。A≡C
equivalence 在前向显式声明（**不是** post-hoc 发现）：balanced policy 只有一条
routing rule，因此 A 与 C 产生相同 per-record outcome，在每个 hypothesis test 中
Variant C 都合并入 A。

B12 为 replay-only：每条 P21 record 已含 per-strategy outcomes，故每个 ablation
variant 通过从现有 records 选取对应 per-strategy outcome 即可计算。B12 evaluator
不产生新 LLM calls。若 P21 records 不可用，B12 需要新的 live ablation runs
（`workflow_dispatch` + `enable_remote_models=true`）。Predeclared support/refute
criteria 在 `gold_span` 与 `span_f0_5` delta 上使用显式 thresholds："≈" 表示
±0.02 以内，">" 表示严格大于 0.02；H4 在 `A - D` `gold_span` delta 上使用 0.05 的
最坏 model-family spread threshold。B12 verdict 框架发出
`supported`/`refuted`/`partial`/`insufficient_data`/`not_implemented` 之一。C1
private-record adapter 落地后，B12 evaluator 的 `--input` 路径已经是真实 replay：
它通过 `eval/c1_private_records.py` 消费 CI-private P21 payload，归一化 runtime
features / benchmark route labels / SCORE-phase outcome fields，并只发出 aggregate-only
public report。它仍然不产生 live LLM calls，且不暴露 task IDs、raw repo IDs、paths、
spans、content hashes、prompts、responses、snippets、provider URLs 或 provider keys。B12
是 mechanism decomposition，**不是** promotion step：`promotion_ready=false`、
`default_should_change=false`、`evidencecore_semantics_changed=false`。详见
[`b12-mechanism-decomposition.md`](b12-mechanism-decomposition.md)。

C2 B12 CI canary（2026-06-19）：C1 shared private-record adapter 落地后，一个真实
CI canary（`py_fastapi × Kimi × round_robin_public_buckets × 12 tasks`，run
`27816890557`）验证了 B12 会消费 private P21 per-record records，并且只发出 aggregate
public report。B12 report 使用 `replay_source="ci_ephemeral_records"`，`21/21`
records complete，`balanced_branch_count=4`、`p25_llm_eligible_count=10`、
`actual_call_avoided_count=4`、`random_selected_count=4`。Canary verdict：`partial`
（H1 `refuted`、H2 `refuted`、H3 `supported`、H4 因 single-model-family slice 为
`insufficient_data`）。这只是 canary-level evidence；完整 B12 matrix over B11
repo/model cells 仍是下一步。

C2/B12 official matrix aggregate（2026-06-19）：

```text
schema_version: b12-mechanism-matrix-aggregate-report-v0
claim_level: derived_aggregate_of_b12_mechanism_decomposition_reports
aggregate_only_public_artifact: true
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
runtime_clean_policy_supported: false
new_provider_calls: 0
candidate_not_fact: true
cell_count_target: 32
analyzable_cell_count: 28
excluded_cell_count: 4
aggregate_verdict: partial_with_coverage_exclusions
```

**C2/B12 official matrix aggregate** 把 28 个 analyzable 的 per-run
`b12-mechanism-decomposition-report-v0` 公共 aggregate 报告（每个 included
repo×model cell 一份）合并为一份 derived aggregate（`eval/b12_matrix_combiner.py`
→ `artifacts/b12_mechanism_decomposition/b12_matrix_aggregate_report.json`）。它
是有界的：只读取已下载的 aggregate-only 公共 B12 报告，不进行 provider calls、不进行
policy search、不进行 threshold tuning。覆盖：`28/32` cells analyzable，`4` 个
`ts_vite` cells 因 `coverage_insufficient_no_remote_llm_snippet` 被排除（即使
`max_tasks=24` 也未 exercise remote LLM snippets；这是覆盖缺口，**不是** B12 mechanism
failure）。Records：共 `336`（每 cell `12`）。Verdict counts：`partial: 28`。Hypothesis
status counts：H1 `supported: 3 / refuted: 25`、H2 `supported: 8 / refuted: 20`、H3
`supported: 28`、H4 `insufficient_data: 28`（每个 cell 都是 single-model-family slice，
故 H4 需跨 cell 的 multi-model aggregation；H4 insufficient_data **不**阻断 H1-H3 verdict）。
Record-weighted A（full balanced）deltas vs D（P25 default）：`Δgold_span 0.0`、
`ΔSpanF0.5 0.0`、`Δfalse_span -0.029762`、`ΔPFP -0.014881`、`Δmodel_calls -0.333333`；
vs E（random call reduction）：`Δgold_span -0.044643`、`ΔSpanF0.5 0.001569`、
`Δfalse_span -0.592262`、`ΔPFP -0.026786`、`Δmodel_calls 0.0`；vs B（deterministic call
reduction）：`Δgold_span 0.0`、`ΔSpanF0.5 0.0`、`Δfalse_span -0.130952`、`ΔPFP -0.035714`、
`Δmodel_calls 0.0`。Weighted mean robust utility (A)：`0.054155`。Replay count totals：
`balanced_branch_count=112`、`p25_llm_eligible_count=324`、
`actual_call_avoided_count=112`、`random_selected_count=112`。Overall verdict：
`partial_with_coverage_exclusions` —— **不是**全局 `supported` verdict，**不** promotion、
**不** default change、**不** runtime-clean general algorithm claim。详见
[`b12-mechanism-decomposition.md`](b12-mechanism-decomposition.md)。

B12 public aggregate mechanism screen（2026-06-18）：

```text
schema_version: b12-public-aggregate-mechanism-screen-v0
claim_level: bounded_public_aggregate_mechanism_screen_of_b11_aggregate
is_full_b12_mechanism_decomposition: false
full_b12_possible_from_public_artifact: false
per_hypothesis_status_only_no_global_supported_verdict: true
aggregate_only_public_artifact: true
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
quality_strategy_tuned: false
new_provider_calls: 0
```

新增一个有界的 **public-aggregate mechanism screen**（`eval/b12_public_aggregate_screen.py`
→ `artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`）。
这**不是**完整的 B12 per-record replay。explorer/oracle 的结论是：从当前的 public
B11 aggregate 无法完成 full B12 replay —— 它缺少 per-record route decisions、
ambiguous-subset membership、deterministic call-reduction variant B、random
call-reduction variant E 以及 `weak_candidate_only` per-strategy outcomes。该
screen 因此发出**逐 hypothesis 的 screen status**，从不发出单一全局 `supported`
verdict，并对 B11 aggregate deltas 应用**相同的**冻结数值门槛（±0.02
approx-equality、0.05 H4 family-spread）。它只读取已发布的 B11 aggregate
报告；不读取或发布任何 raw records、paths、prompts、responses、snippets 或
private labels。

B11 official matrix aggregate（32 runs / 384 records）的逐 hypothesis screen
结果：**H1** `inconclusive_unavailable_ablation_controls`（无 per-record route
decisions、无 ambiguous subset、无 variants B/E；**不**声称 H1 support）。
**H2** `reduced_calls_observed_causal_mechanism_inconclusive`（`Δmodel_calls
-0.354167`，描述性观察到 reduced calls，但缺少 variant E 无法归因 causal
mechanism；**不**声称 H2 causal support）。**H3**
`aggregate_primary_parity_supported_consistent_with_h3`（`Δgold_span -0.002604`
与 `ΔSpanF0.5 -0.001899` 均在 ±0.02 内；与 H3 在 aggregate 层面一致，但**不是**
完整的 H3 supported verdict —— 从 aggregate deltas 无法得出 per-record fallback
sufficiency 结论）。**H4**
`family_gold_spread_not_supported_model_repo_interaction_inconclusive`（per-family
gold_span delta spread `0.010417` —— deepseek_flash 0.0、deepseek_pro 0.0、
kimi -0.010417、qwen 0.0 —— at or below 0.05 family-level threshold，因此 H4 在
predeclared family-level gold-span spread criterion 下 **not supported**；**不是**
完整的 H4 refutation，因为 Kimi `py_fastapi` failure slice 在无 per-record 数据时
使 model×repo interaction 仍 inconclusive）。建议下一步：future ephemeral-record
B12 replay，或 B13 robust policy search **谨慎进行**（B13 不得被视为由 B12
supported verdict 授权）。详见
[`b12-mechanism-decomposition.md`](b12-mechanism-decomposition.md)。

B13 distributionally robust policy search：

```text
algorithm_spec_id: b13_dro_policy_search_v0
claim_level: distributionally_robust_policy_search_v0
replay_and_search_only: true（evaluator 内无 live LLM calls）
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
stage_is_policy_search: true（B13 stage 即 policy search）
empirical_policy_search_performed: false（skeleton 不执行 empirical search）
policy_search_performed: false（synthetic/stub 报告；用 stage_is_policy_search=true
                               标注 stage）
quality_strategy_tuned: false
algorithm_spec_has_no_model_names: true（B13 special invariant）
```

B13 是继 B12 之后的 **distributionally robust policy search** 阶段。目标是
找到一个含 6-10 条 rules 的 policy，仅使用 runtime-observable
features，优化 **worst-group utility**（而非平均值）或
`CVaR_20%`，并通过 rotating leave-one-model-family-out 验证。The rule
grammar is restricted to `route_features` only
（`query_noise`、`candidate_support_exists`、`local_anchor`、
`rrf_backed_by_anchor`、`candidate_count`、`symbol_regex_agree_file`、
`symbol_regex_agree_span`、`rrf_anchor_agree_file`、`rrf_anchor_agree_span`、
`dense_support_present`）：**禁止** benchmark-private labels（`task_bucket`、
`task_risk_tags`），**禁止** score-private fields（`has_gold`、`score_group`、
`outcome_metrics`），且 `algorithm_spec` 中**禁止** 原始 model names（B13 使用
`model_profile` capabilities like `supports_reliable_span_narrow`、
`cost_class`、`latency_class`；spec 发出抽象 `family_slots`
`family_a`/`family_b`/`family_c`/`family_d` 而非 "Kimi"/"Qwen"/
"DeepSeek"）。Allowed actions 为 LLM-free：`weak_only`、`use_p25_action`、
`use_local_baseline`。优化目标为
`RobustUtility = SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency`
（`λ=1.0`、`μ=0.1`、`ν=0.1`，`CVaR α=0.20`）。search method 为 bounded
grid + greedy refinement（pure Python；无 numpy/sklearn/scipy），上限
`MAX_RULES=10`、`MAX_SEARCH_ITERATIONS=1000`。验证使用 3 个 rotating
leave-one-model-family-out rotations（`loo_family_a`、`loo_family_b`、
`loo_family_c_and_d`）；全部 3 个必须通过（worst-group `RobustUtility` 在 B10
的 ±0.02 以内或严格更优）。B13 **是** policy-search *stage*
（`stage_is_policy_search=true`），但当前 skeleton **不**执行 empirical
policy search（`empirical_policy_search_performed=false`），synthetic / stub
报告设置 `policy_search_performed=false`、`policy_found=false`、
`rotations_evaluated=false`、`rotations_defined=true`、`rotation_count=3`、
`winner_declared=false`，使该公共 artifact 不会被误读为
empirical B13 run；synthetic / stub 报告仅发出 rotation *定义*（无
per-rotation 的 `passes=true` / `test_worst_group_utility` /
`delta_vs_b10_reference`），skeleton verdict 框架仅发出
`insufficient_data`（synthetic fixture）或 `not_implemented`
（ci_ephemeral_records stub）——`success` / `failure` / `partial` 保留给未来
`policy_search_performed=true` 的 empirical 路径，该路径在当前 skeleton 中
**不**存在。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts
比对，drift 即失败；不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的
mutating 路径。结果**不**被 promoted（`promotion_ready=false`、
`default_should_change=false`）。B13 需要 B11 live
runs 的 P21 records（4 model families × 8 repos）；`--input` 路径为 stub
（verdict `not_implemented`；真实 search 延后）。bounded public-aggregate
feasibility / no-go screen（`eval/b13_public_aggregate_feasibility_screen.py`）
读取已发布的 B11 aggregate + B12 public screen，在
`artifacts/b13_dro_policy_search/` 下发出
`verdict=no_go_public_aggregate_only`（或
`insufficient_data_public_aggregate_only`）；它从不声称 empirical policy
search，从不选择 rule，从不声明 winner。B13 结果作为 research
candidates 输入 B14（uncertainty calibration）与 B16（downstream agent
evaluation）。B13 是 B10-B19 Breakthrough Sprint 中最后一个 "immediate
priority" item；其余 items（B14-B19）为 second priority 或 parallel tracks。详见
[`b13-distributionally-robust-policy-search.md`](b13-distributionally-robust-policy-search.md)。

B14 uncertainty calibration：

```text
algorithm_spec_id: b14_uncertainty_calibration_v0
claim_level: uncertainty_calibration_v0
replay_and_calibration_only: true（evaluator 内无 live LLM calls）
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
stage_is_uncertainty_calibration: true（B14 stage 即为 uncertainty calibration）
uncertainty_calibration_performed: false（skeleton 不执行 empirical calibration）
calibrated_model_claim: false（不声称任何 model 被 calibrated）
per_record_inputs_available: false（skeleton；无真实 per-record inputs）
policy_search_performed: false
quality_strategy_tuned: false
metrics_evaluated: false（skeleton；不从 aggregate means 伪造 metric values）
no_fake_metrics_from_aggregate_means: true
algorithm_spec_has_no_model_names: true（B14 special invariant）
```

B14 是继 B13 之后的 **uncertainty calibration** 阶段。目标是针对 balanced-
policy candidate 进行 **model-independent uncertainty calibration**：从 local
candidate signals、model output structure 与 cross-model disagreement 构建每条
记录的 uncertainty score（绝不针对特定 model name 进行校准），再用 risk-
coverage、selective risk、ECE 与 PFP-at-fixed-coverage 指标评估该 score，并
附 worst-group 报告与 rotating leave-one-model-family-out 验证。signal
families 受限：**无** benchmark-private labels（`task_bucket`、
`task_risk_tags`）、**无** score-private fields（`has_gold`、`score_group`、
`outcome_metrics`）、**无**原始 model names 在 `algorithm_spec` 中（B14 使用
抽象 `family_slots` `family_a`/`family_b`/`family_c`/`family_d`）。frozen
coverage levels 为 `[0.50, 0.70, 0.90, 0.95, 0.99]`；ECE bin 定义为 `[0, 1]`
上 15 个 equal-width bins；split protocol 按 (model_family, repo) 分层，
`calibration_fraction=0.50` / `test_fraction=0.50`（recalibration 仅在
calibration split 上；test split held out 并仅报告一次）。predeclared
success/partial/failure criteria 使用 test split 上 ECE（≤ 0.05）、coverage=0.90
处 selective risk（≤ 0.10）、coverage=0.90 处 worst-group selective risk
（≤ 0.15）与 0.02 approx-equality / strictly-greater rotation threshold，并
附 `CVaR_20%` worst-group tail average。B14 **是** uncertainty-calibration
*stage*（`stage_is_uncertainty_calibration=true`），但当前 skeleton **不**执行
任何 empirical uncertainty calibration
（`uncertainty_calibration_performed=false`）；synthetic / stub 报告设置
`calibrated_model_claim=false`、`per_record_inputs_available=false`、
`uncertainty_score_found=false`、`rotations_evaluated=false`、
`rotations_defined=true`、`rotation_count=3`、`winner_declared=false`、
`metrics_evaluated=false`、`no_fake_metrics_from_aggregate_means=true`，使该
公共 artifact 不会被误读为 empirical B14 calibration。**CRITICAL**：skeleton
**绝不可**从 aggregate means 计算伪造的 ECE / risk-coverage / selective-risk /
PFP-at-coverage 指标；synthetic fixture 仅验证 metric NAMES 与 gates（无
per-record (uncertainty, outcome) pairs，无 computed metric values）。synthetic
/ stub 报告仅发出 rotation *定义*（无 per-rotation 的 `passes=true` /
`test_ece` / `test_selective_risk` / `test_risk_coverage_curve` /
`test_pfp_at_fixed_coverage` / `delta_vs_reference`）；skeleton verdict 框架仅
发出 `insufficient_data`（synthetic fixture）或 `not_implemented`
（ci_ephemeral_records stub）——`success` / `failure` / `partial` 保留给未来
`uncertainty_calibration_performed=true` 的 empirical 路径，该路径在当前
skeleton 中**不**存在。`--self-test` 为只读（将内存中期望 artifacts 与
on-disk artifacts 比对，drift 即失败，不写入）；`--regenerate-artifacts` 为
唯一会修改 checked-in artifacts 的路径。`--input` stub 要求显式 `--out`，并拒绝写入 checked-in B14 report。bounded public-aggregate feasibility / no-go screen
（`eval/b14_public_aggregate_feasibility_screen.py`）读取已发布的 B11
aggregate + B12 public screen + B13 public feasibility，在
`artifacts/b14_uncertainty_calibration/` 下发出
`verdict=no_go_public_aggregate_only`（或
`insufficient_data_public_aggregate_only`）；它从不声称 empirical
calibration，从不计算 metric，从不选择 uncertainty score，也从不声明 winner。
真实的 B14 calibration 无法仅凭公共 aggregates 完成：它需要 per-record
uncertainty scores、per-record binary outcomes、paired cross-model outputs、
schema-repair per-call rows 与 candidate score distributions，这些在当前公共
artifacts 中均不存在。B14 结果作为 research candidates 仅输入 B16（downstream
agent evaluation）与未来 selective-abstention policy 工作。详见
[`b14-uncertainty-calibration.md`](b14-uncertainty-calibration.md)。

B15 context pack policy：

```text
algorithm_spec_id: b15_context_pack_policy_v0
claim_level: context_pack_policy_v0
replay_and_validation_only: true（evaluator 内部无 live LLM 调用）
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
stage_is_context_pack_policy: true（B15 stage IS context pack policy）
pack_policy_learned: false（skeleton 不进行 PackPolicy learning）
atom_ablation_performed: false（skeleton 不进行 empirical atom ablation）
per_record_inputs_available: false（skeleton；无 real per-record inputs）
policy_search_performed: false
quality_strategy_tuned: false
new_provider_calls: 0
candidate_policy_frozen: false
stages_evaluated: false
stages_defined: true
stage_count: 4
winner_declared: false
metrics_evaluated: false（skeleton；不从 aggregate means 计算伪造 atom-effect values）
no_fake_atom_effects_from_aggregate_means: true
algorithm_spec_has_no_model_names: true（B15 special invariant）
```

B15 是继 B14 之后的 **context pack policy** 阶段。目标是产出一个 **frozen、
preregistered 的 PackPolicy**，将 `(role, runtime_state, model_profile)`
映射到一组确定的 **atom set**（context pack 应当暴露的 pack-layout atoms），
并基于 B11/B13 live runs 的 per-record pack atom flags + per-record outcomes
+ role + runtime_state + model_profile + group membership 进行验证。B15 是
一个 **bounded planning / feasibility 阶段**，**不是** empirical atom-level
ablation。Roles 为 FROZEN（`span_narrow`、`filter_reject`、
`request_more_context`、`source_test_disambiguation`）；atom registry 为
FROZEN（`signature`、`matched_lines`、`raw_snippet`、`neighbor_context`、
`scores`、`provenance`、`hard_distractor`、`same_file_competitor`、
`path_kind_flag`）；runtime_state 契约 label-free 且 model-name-free；
model_profile 抽象使用 abstract capability slots（`profile_slot_a`..
`profile_slot_d`）+ capability descriptors —— `algorithm_spec` 中**无** raw
model names（B15 使用抽象 `abstract_profile_slots`，从不使用
`kimi`/`qwen`/`deepseek`/`glm`）。experimental structure FROZEN 为 4 个
stages：`no_llm_feasibility` →
`fractional_factorial_live_atom_screen`（atom registry 上的 resolution-IV
fraction，非完整 2^9 factorial）→ `freeze_candidate_policy` →
`fresh_validation`（按 `(model_family, repo, role)` stratified，
`atom_screen_fraction=0.50` / `fresh_validation_fraction=0.50`，held out 且
reported once）。Hard gates（FROZEN）：`privacy_gate`、`leakage_gate`、
`adapter_health_gate`、`randomization_balance_gate`、`denominator_gate`（每
cell 最小 30）、`token_budget_gate`、`promotion_false_gate`。Metric
registry（FROZEN，9 个 names）：`atom_effect_per_atom`、`role_pack_outcome`、
`runtime_state_pack_outcome`、`model_profile_pack_outcome`、
`worst_group_pack_outcome`、`cvar_20_pack_outcome`、`token_budget_parity`、
`denominator_per_atom_role_model`、`randomization_balance_per_arm` —— 每个
metric 都需要 per-record (atom_flag, outcome, role, runtime_state,
model_profile) tuples；**没有** metric 可从 aggregate means 计算。
Predeclared success/partial/failure criteria 使用 fresh-validation split 上
per-role pack-outcome 提升（≥ 0.02）、worst-group pack-outcome regress
（≤ 0.15）、denominator（每 cell ≥ 30）、randomization balance
（imbalance ≤ 0.05）、token-budget match tolerance（0.10）以及
`CVaR_20%` worst-group tail average 的显式 thresholds。B15 **是**
context-pack-policy *stage*（`stage_is_context_pack_policy=true`），但当前
skeleton **不**进行 empirical PackPolicy learning
（`pack_policy_learned=false`），也**不**进行 empirical atom ablation
（`atom_ablation_performed=false`）；synthetic / stub 报告设置
`per_record_inputs_available=false`、`candidate_policy_frozen=false`、
`stages_evaluated=false`、`stages_defined=true`、`stage_count=4`、
`winner_declared=false`、`metrics_evaluated=false`、
`no_fake_atom_effects_from_aggregate_means=true`，使该公共 artifact 不会被
误读为 empirical B15 PackPolicy 结果。**CRITICAL**：skeleton **绝不可**从
aggregate means 计算伪造的 atom-effect / role-pack-outcome /
worst-group-pack-outcome 指标；synthetic fixture 仅验证 metric NAMES 与
gates（无 per-record (atom_flag, outcome) pairs，无 computed metric values）。
synthetic / stub 报告仅发出 stage *定义*（无 per-stage 的 `passes=true` /
`atom_effect_per_atom` / `role_pack_outcome` / `worst_group_pack_outcome`）；
skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或
`not_implemented`（ci_ephemeral_records stub）——`success` / `failure` /
`partial` 保留给未来 `atom_ablation_performed=true` /
`pack_policy_learned=true` 的 empirical 路径，该路径在当前 skeleton 中**不**
存在。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，
drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一
会修改 checked-in artifacts 的路径；`--input` stub 要求显式 `--out`，并拒绝
写入 checked-in B15 report。bounded public-aggregate prior / no-go screen
（`eval/b15_public_aggregate_prior_screen.py`）读取已发布的 B2 contrastive-pack
experiment（仅检查存在性）、B14 public-aggregate feasibility report，以及
当存在时的 B4-B9 / P21-G / P49 公共 aggregates，在
`artifacts/b15_context_pack_policy/` 下发出
`verdict=prior_screen_only`（或当 B2 缺失时 `no_go_public_aggregate_only`）；
它从不声称 empirical PackPolicy learning，从不计算 atom-effect metric，从不
冻结 candidate policy，也从不声明 winner。已发布的 B2 contrastive-pack
experiment 是 single-model、low-N（每个 layout 24 tasks）、aggregate-only 的
pack-layout 比较；它**仅**可作为
`low_n_single_model_aggregate_directional_prior`（`b2_prior_usable=true`、
`b2_prior_claim_level=low_n_single_model_aggregate_directional_prior`），
**不能**作为 atom-level causality、role-specific PackPolicy、calibrated
policy、cross-model robustness、hard-distractor 通用规则、scores/provenance
通用胜利、default change、promotion 或 EvidenceCore change。真实的 B15
PackPolicy validation 无法仅凭公共 aggregates 完成：它需要 per-record pack
atom flags、per-record outcomes、role-specific paired outputs、model_profile
paired blocks、group membership、randomized atom assignment、randomization
balance stats、denominator-by-atom/role/model cells 以及 token-budget-matched
controls，这些在当前公共 artifacts 中均不存在。B15 结果作为 research
candidates 输入 B16（downstream agent evaluation）与未来 context-pack routing
工作。详见 [`b15-context-pack-policy.md`](b15-context-pack-policy.md)。

B16 downstream coding-agent evaluation：

```text
algorithm_spec_id: b16_downstream_agent_evaluation_v0
claim_level: downstream_agent_evaluation_v0
replay_and_validation_only: true (no live LLM calls and no live downstream agent runs inside evaluator)
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
retrieval_variant_promoted: false
stage_is_downstream_agent_evaluation: true（B16 stage IS downstream agent evaluation）
downstream_agent_runs_performed: false（skeleton 不执行 live agent runs）
patch_execution_performed: false（skeleton 不执行 patch execution）
agent_behavior_metrics_evaluated: false（skeleton 不评估 agent behavior metrics）
solve_rate_evaluated: false（skeleton 不评估 solve rate）
per_record_inputs_available: false（skeleton；无真实 per-run inputs）
policy_search_performed: false
quality_strategy_tuned: false
new_provider_calls: 0
candidate_retrieval_variant_frozen: false
stages_evaluated: false
stages_defined: true
stage_count: 4
winner_declared: false
metrics_evaluated: false（skeleton；无 fake solve-rate 或 downstream metrics from retrieval aggregates）
no_fake_downstream_metrics_from_retrieval_aggregates: true
```

B16 是继 B15 之后的 **downstream coding-agent evaluation** 阶段。目标是产出一个 **frozen、preregistered 的 paired within-task randomized controlled trial**，衡量 candidate retrieval/context variant 是否能改进下游 coding agent（而非仅 retrieval aggregates），基于真实、paired、isolated-workspace 的 agent runs。B16 是一个 **bounded planning / feasibility 阶段**，**不是** live downstream agent evaluation。Arms 为 FROZEN 的 primary（`control_current_retrieval_v0`、`balanced_v1_retrieval_candidate`）、exploratory（`candidate_pack_policy_v0`，仅当真实 B15 candidate 存在时才包含 —— B15 skeleton 不产出 candidate，故此 arm 默认 EXCLUDED）与 debugging-only（`gold_context_ceiling`，从不 promoted）。Task types 为 FROZEN（`bug_localization`、`small_code_edit`、`test_selection`、`multi_file_feature`、`refactor_impact`）。paired RCT 强制 paired within-task randomization、isolated fresh workspace per run、randomized arm order、除 retrieval/context variant 外相同的 budget/tools/prompt，以及 no cross-run memory。Hard gates（FROZEN）：`feasibility_gate`、`denominator_gate`（每 (task_type, arm) cell 最小 30）、`leakage_gate`、`operational_parity_gate`（token-budget match tolerance 0.10、latency match tolerance 0.15、除 retrieval variant 外相同 tools/budget/prompt、isolated fresh workspace、randomized arm order、no cross-run memory）、`privacy_gate`、`promotion_false_gate`。Metric registry（FROZEN，8 个 names）：`solve_rate`、`correct_file_before_first_edit`、`wrong_file_edits`、`tool_calls_before_first_edit`、`context_tokens`、`tests_pass`、`latency`、`cost` —— 每个 metric 都需要 per-run paired agent outputs（event logs、patches/diffs、test execution results、solve labels、first-file-before-first-edit events、wrong-file-edit annotations、tool-call/token/latency/cost rows、isolated workspace proof、randomized arm order、task oracle/hidden-test manifest）；**没有** metric 可从 retrieval aggregates 计算。Predeclared success/partial/failure criteria 使用 fresh-validation split 上 solve-rate 提升的显式 thresholds（≥ 0.02）、correct-file-before-first-edit 提升（≥ 0.02）、wrong-file-edits 回归（≤ 0.15）、denominator（≥ 30 per cell）、randomization balance（≤ 0.05 imbalance）、operational parity（token-budget 0.10、latency 0.15）、cost reported per arm，加上 `CVaR_20%` worst-group tail average。B16 **是** downstream-agent-evaluation *stage*（`stage_is_downstream_agent_evaluation=true`），但当前 skeleton 不执行任何 live downstream agent runs（`downstream_agent_runs_performed=false`）、不执行 patch execution（`patch_execution_performed=false`）、不评估 agent-behavior metrics（`agent_behavior_metrics_evaluated=false`），也不评估 solve rate（`solve_rate_evaluated=false`）；synthetic / stub 报告设置 `per_record_inputs_available=false`、`candidate_retrieval_variant_frozen=false`、`stages_evaluated=false`、`stages_defined=true`、`stage_count=4`、`winner_declared=false`、`metrics_evaluated=false`、`no_fake_downstream_metrics_from_retrieval_aggregates=true`，使该公共 artifact 不会被误读为 empirical B16 downstream agent 结果。**CRITICAL**：skeleton **绝不可**从 retrieval aggregates 计算伪造的 solve-rate / correct-file-before-first-edit / wrong-file-edits / tool-call / token / latency / cost 指标；synthetic fixture 仅验证 metric NAMES 与 gates（无 per-run paired agent outputs，无 computed metric values）。synthetic / stub 报告仅发出 stage *定义*（无 per-stage 的 `passes=true` / `solve_rate` / `correct_file_before_first_edit` / `wrong_file_edits`）；skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或 `not_implemented`（ci_ephemeral_records stub）——`success` / `failure` / `partial` 保留给未来 `downstream_agent_runs_performed=true` / `solve_rate_evaluated=true` 的 empirical 路径，该路径在当前 skeleton 中**不**存在。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的路径；`--input` stub 要求显式 `--out`，并拒绝写入 `artifacts/b16_downstream_agent_evaluation/` 内的任何路径。bounded public-aggregate feasibility / no-go screen（`eval/b16_public_aggregate_feasibility_screen.py`）读取已发布的 B11 matrix + B12 + B13 + B14 + B15 公共 screens，并在 `artifacts/b16_downstream_agent_evaluation/` 下发出 `verdict=no_go_public_aggregate_only`（或 `insufficient_data_public_aggregate_only`）；它从不声称 downstream agent value，从不从 retrieval aggregates 计算 downstream metric，从不 freeze candidate retrieval variant，从不 promote retrieval variant，也从不声明 winner。B10-B15 retrieval/context candidate research 是 retrieval research；它**不**证明 downstream coding-agent value。Retrieval improvements **不是** downstream agent improvements；B15 PackPolicy **不是** downstream agent improvement。真实 B16 downstream agent evaluation 无法仅凭公共 aggregates 完成：它需要 paired live downstream agent runs、per-run agent event logs、per-run patches/diffs、per-run test execution results、per-run solve labels、per-run first-file-before-first-edit events、per-run wrong-file-edit annotations、per-run tool-call/token/latency/cost rows、per-run isolated fresh workspace proof、per-run randomized arm order 与 task oracle/hidden-test manifest，这些在当前公共 artifacts 中均不存在。B11 `partial_with_failure` 与 B12/B13/B14/B15 no-go 或 screen-only statuses 原样 carry forward。详见 [`b16-downstream-agent-evaluation.md`](b16-downstream-agent-evaluation.md)。

---

## B17 QuIVer Systems Track

```text
algorithm_spec_id: b17_quiver_systems_track_v0
claim_level: quiver_systems_track_v0
replay_and_validation_only: true（evaluator 内无 live LLM calls 且无 live ANN backend bakeoff）
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
retrieval_policy_changed: false
backend_quality_promoted: false
stage_is_quiver_systems_track: true（B17 stage IS quiver systems track）
quiver_graph_implemented: false（skeleton 不实现 QuIVer 或 Vamana graph）
ann_backend_bakeoff_performed: false（skeleton 不执行 ANN backend bakeoff）
candidate_set_equivalence_validated: false（skeleton 不验证 candidate-set equivalence）
metrics_evaluated: false（skeleton；不从 diagnostics 计算伪造的 ANN metrics）
new_provider_calls: 0
all_stages_pass: false
stages_evaluated: false
stages_defined: true
stage_count: 4
winner_declared: false
no_fake_ann_metrics_from_diagnostics: true
```

B17 是继 B16 之后的 **QuIVer systems track** 阶段。目标是产出一个 **frozen、preregistered 的 backend bakeoff**，在 **frozen candidate-quality policy** 下对比 ANN backend candidates 的 backend systems metrics（latency、memory、build time、update cost、index size），使 backend quality 不会在对比 systems 数据时被静默放宽。B17 是一个 **bounded planning / diagnostic 阶段**，**不是** QuIVer production backend，**不是** ANN quality promotion，**不是** default change，**不是** EvidenceCore semantics change。Candidate backends 为 FROZEN 的 reference（`flat_f32_reference`）、candidate（`hnsw_candidate`、`bq_topk_f32_rerank_candidate`、`quiver_vamana_prototype` —— QuIVer/Vamana graph backend 终极目标，**未实现**）与 optional-store（`tdb_vector_candidate`，仅 store/backend candidate，**非** Evidence source，默认 EXCLUDED）。Candidate-set equivalence constraints 为 FROZEN（`candidate_set_overlap_at_k` ≥ 0.90 at K=[10,50,100]、`gold_retention_delta` tolerance 0.05、`primary_false_positive_delta` guard 0.05、`span_f0_5_delta` tolerance 0.05、`citation_validity` = 1.0、`stale_evidencecore_rejection_required`、`no_default_expansion_required`）。Hard gates（FROZEN）：`quiver_graph_implementation_gate`、`backend_parity_gate`、`candidate_set_equivalence_gate`、`evidencecore_materialization_gate`、`stale_citation_gate`、`privacy_gate`、`promotion_false_gate`。Metric registry（FROZEN，11 个 names）：`candidate_set_overlap_at_k`、`gold_retention_delta`、`span_f0_5_delta`、`primary_false_positive_delta`、`p50_latency`、`p95_latency`、`hot_memory`、`build_time`、`update_cost`、`index_size`、`recall_tolerance_violation_count` —— 每个 metric 都需要 per-backend systems bakeoff inputs（index build records、search latency records、hot memory records、index size records、update cost records、candidate-set-at-K records、gold retention records、span F0.5 records、PFP records、citation validity records、stale rejection records、EvidenceCore rejection records、recall tolerance violation records、randomized run order proof、isolated index workspace proof、shared frozen candidate-quality manifest）；**没有** metric 可从现有 R33/R34/R36/R24 diagnostics 计算。B17 **是** quiver-systems-track *stage*（`stage_is_quiver_systems_track=true`），但当前 skeleton 不执行 ANN backend bakeoff（`ann_backend_bakeoff_performed=false`）、不验证 candidate-set equivalence（`candidate_set_equivalence_validated=false`）、不实现 QuIVer/Vamana graph（`quiver_graph_implemented=false`）、不 promote backend quality（`backend_quality_promoted=false`）；synthetic-fixture / `--input` stub 报告设置 `promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`retrieval_policy_changed=false`、`metrics_evaluated=false`、`new_provider_calls=0`、`no_fake_ann_metrics_from_diagnostics=true`，使该公共 artifact 不会被误读为 empirical B17 systems bakeoff 结果。**CRITICAL**：skeleton **绝不可**从现有 R33/R34/R36/R24 diagnostics 计算伪造的 candidate_set_overlap_at_k / gold_retention_delta / span_f0_5_delta / primary_false_positive_delta / p50_latency / p95_latency / hot_memory / build_time / update_cost / index_size / recall_tolerance_violation_count 指标；synthetic fixture 仅验证 metric NAMES 与 gates（无 per-backend systems bakeoff inputs，无 computed metric values）。synthetic / stub 报告仅发出 stage *定义*（无 per-stage 的 `passes=true` / `candidate_set_overlap_at_k` / `gold_retention_delta` / `p50_latency` / `hot_memory` / `build_time` / `index_size`）；skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或 `not_implemented`（ci_ephemeral_records stub）——`success` / `failure` / `partial` 保留给未来 `ann_backend_bakeoff_performed=true` / `candidate_set_equivalence_validated=true` / `quiver_graph_implemented=true` 的 empirical 路径，该路径在当前 skeleton 中**不**存在。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的路径；`--input` stub 要求显式 `--out`，并拒绝写入 `artifacts/b17_quiver_systems_track/` 内的任何路径。bounded public-systems diagnostic carry-forward / no-go screen（`eval/b17_public_systems_diagnostic_screen.py`）读取已发布的 R33 readiness + R34/R36 anchor-proto + real-provider P3/P4 quiver diagnostics + 可选 R24 QuIVer/TDB/dense probe，并在 `artifacts/b17_quiver_systems_track/` 下发出 `verdict=no_go_quiver_graph_missing`（或 `diagnostic_carry_forward_only`）；它从不声称 QuIVer implementation，从不从 diagnostics 计算 ANN metric，从不 promote backend，从不修改 retrieval policy，也从不声明 winner。现有 R33/R34/R36/R24 diagnostics 是 **diagnostic-only carry-forward** —— 它们**不**是 quality proof，**不**是 promotion evidence；它们**不**实现 QuIVer/Vamana graph backend、**不**包含 HNSW run、**不**包含 candidate-set equivalence matrix across backends。详见 [`b17-quiver-systems-track.md`](b17-quiver-systems-track.md)。

 B18 OOD / temporal evaluation：

 ```text
 algorithm_spec_id: b18_ood_temporal_evaluation_v0
 claim_level: ood_temporal_evaluation_v0
 replay_and_validation_only: true (no live LLM calls and no live OOD or temporal evaluation inside evaluator)
 promotion_ready: false
 default_should_change: false
 evidencecore_semantics_changed: false
 retrieval_policy_changed: false
 backend_quality_promoted: false
 stage_is_ood_temporal_evaluation: true (B18 stage IS OOD and temporal evaluation)
 ood_temporal_evaluation_performed: false (skeleton performs no OOD or temporal evaluation)
 metrics_evaluated: false (skeleton; no fake OOD or temporal metrics from aggregate means)
 policy_search_performed: false (no-retuning protocol)
 quality_strategy_tuned: false (no-retuning protocol)
 real_ood_temporal_supported: false
 new_provider_calls: 0
 all_axes_pass: false
 axes_evaluated: false
 axes_defined: true
 axis_count: 5
 winner_declared: false
 no_fake_ood_metrics_from_aggregate_means: true
 ```

 B18 是继 B17 之后的 **OOD（out-of-distribution）/ temporal evaluation** 阶段。目标是产出一个 **frozen、preregistered 的 OOD / temporal evaluation**，在 **no-retuning protocol** 下（no policy search、no quality strategy tuning、no retrieval policy change、no EvidenceCore semantics change、no default change、no promotion）跨五个 FROZEN split axes——`temporal_split`、`repo_split`、`language_split`、`model_family_split`、`adversarial_split`——评估 retrieval / candidate / Evidence pipeline，使 in-distribution average 不会被误读为 OOD / temporal generalization。B18 是一个 **bounded preregistration + public-aggregate no-go screen 阶段**，**不是** 真正的 OOD / temporal evaluation，**不是** policy search，**不是** quality strategy tuning，**不是** default change，**不是** EvidenceCore semantics change，**不是** promotion。Split axes 为 FROZEN（`temporal_split`、`repo_split`、`language_split`、`model_family_split`、`adversarial_split`）。No-retuning protocol 为 FROZEN（`no_retuning_protocol=true`、`no_policy_search=true`、`no_quality_strategy_tuning=true`、`no_retrieval_policy_change=true`、`no_evidencecore_semantics_change=true`、`no_default_change=true`、`no_promotion=true`）。Hard gates（FROZEN）：`per_record_data_gate`、`time_axis_gate`、`commit_chronology_gate`、`no_retuning_gate`、`adversarial_holdout_gate`、`temporal_holdout_gate`、`evidencecore_materialization_gate`、`stale_citation_gate`、`privacy_gate`、`promotion_false_gate`。Metric registry（FROZEN，13 个 names）：`ood_generalization_gap`、`temporal_holdout_delta`、`repo_holdout_metric`、`language_holdout_metric`、`model_family_holdout_metric`、`adversarial_robustness_score`、`worst_group_metric`、`cvar_tail_metric`、`per_cell_denominator`、`temporal_split_integrity`、`no_retuning_proof_metric`、`citation_validity`、`stale_evidencecore_rejection_rate` —— 每个 metric 都需要 per-record OOD / temporal inputs（per-record records、per-record time index、per-record commit chronology、per-record repo / language / model_family axes、per-record task category、per-record adversarial holdout membership、per-record temporal holdout membership、per-record outcome label、per-record citation validity、per-record stale rejection、per-record EvidenceCore rejection、per-record randomized run order proof、per-record no-retuning proof、shared frozen evaluation protocol manifest）；**没有** metric 可从 B11 aggregate means 或 R15 / R20 / R26 repo locks 计算。B18 **是** ood-temporal-evaluation *stage*（`stage_is_ood_temporal_evaluation=true`），但当前 skeleton 不执行真正的 OOD / temporal evaluation（`ood_temporal_evaluation_performed=false`）、不做 metrics evaluation（`metrics_evaluated=false`）、不做 policy search（`policy_search_performed=false`）、不做 quality strategy tuning（`quality_strategy_tuned=false`）、不 promote（`promotion_ready=false`）；synthetic-fixture / `--input` stub 报告设置 `promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`retrieval_policy_changed=false`、`metrics_evaluated=false`、`new_provider_calls=0`、`no_fake_ood_metrics_from_aggregate_means=true`，使该公共 artifact 不会被误读为 empirical B18 OOD / temporal 结果。**CRITICAL**：skeleton **绝不可**从现有 B11 aggregate means 或 R15 / R20 / R26 repo locks 计算伪造的 ood_generalization_gap / temporal_holdout_delta / repo_holdout_metric / language_holdout_metric / model_family_holdout_metric / adversarial_robustness_score / worst_group_metric / cvar_tail_metric / per_cell_denominator / temporal_split_integrity / no_retuning_proof_metric / citation_validity / stale_evidencecore_rejection_rate 指标；B11 aggregate 仅带 public model-family means + repo slice list + sanitized failure slices，但 **无** per-record、per-time-index、per-repo-per-language cell、model_family x repo matrix、adversarial holdout outcome、temporal holdout outcome，且 R15 / R20 / R26 repo locks 是 synthetic / static snapshots，无真实 commit chronology 或 time axis。synthetic / stub 报告仅发出 stage *定义*（无 per-stage 的 `passes=true` / `ood_generalization_gap` / `temporal_holdout_delta` / `worst_group_metric` / `cvar_tail_metric` / `per_cell_denominator`）；skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或 `not_implemented`（ci_ephemeral_records stub）——`success` / `failure` / `partial` 保留给未来 `ood_temporal_evaluation_performed=true` / `metrics_evaluated=true` 的 empirical 路径，该路径在当前 skeleton 中**不**存在。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的路径；`--input` stub 要求显式 `--out`，并拒绝写入 `artifacts/b18_ood_temporal_evaluation/` 内的任何路径。bounded public-aggregate no-go screen（`--public-screen --out <path>`，亦从 `--regenerate-artifacts` 运行）读取已发布的 B11 prospective matrix aggregate report 以及可选的 R15 / R20 / R26 repos.lock.jsonl 文件与 dataset manifests，并在 `artifacts/b18_ood_temporal_evaluation/` 下发出 `verdict=no_go_public_aggregate_only`（或 `public_aggregate_carry_forward_only`）；它从不声称 OOD / temporal evaluation，从不从 aggregate means 计算 OOD / temporal metric，从不 promote retrieval variant，从不修改 retrieval policy，也从不声明 winner。现有 B11 / R15 / R20 / R26 aggregates 是 **aggregate-only / metadata-only carry-forward** —— 它们**不**是 OOD / temporal proof，**不**是 promotion evidence；它们**不**包含 per-record records、time axis、commit chronology、per-repo-per-language cells、model_family x repo matrix、adversarial holdout outcomes 或 temporal holdout outcomes。详见 [`b18-ood-temporal-evaluation.md`](b18-ood-temporal-evaluation.md)。

B19 理论综合（Model-Robust Selective Evidence Conversion）：

```text
algorithm_concept: Model-Robust Selective Evidence Conversion
schema_version: b19-theoretical-synthesis-report-v0
claim_level: theoretical_synthesis_of_b10_through_b18
is_synthesis_only: true
is_new_experiment: false
ran_providers: false
new_provider_calls: 0
changed_retrieval_default_evidencecore: false
aggregate_only_public_artifact: true
synthesized_stages: B10, B10B, B11, B12, B13, B14, B15, B16, B17, B18
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
runtime_clean_policy_supported: false
downstream_agent_value_proven: false
ood_temporal_supported: false
quiver_systems_supported: false
forbidden_public_scan_clean: true
report_drift_guarded: true
```

B19 是 B10-B18 Breakthrough Sprint 的 **理论综合**。它是 **仅综合**：**不**运行任何 provider，**不**修改 retrieval / default / EvidenceCore，**不**声明 promotion。它把 B10 / B10B / B11 / B12 / B13 / B14 / B15 / B16 / B17 / B18 综合成一份关于候选算法概念 **Model-Robust Selective Evidence Conversion** 的论文式算法报告 —— 一个 model-robust、runtime-clean、evidence-gated 的策略，通过把 recall 与 admission 解耦、选择性路由 LLM 角色、并在跨 model adapter 上优化 worst-group utility，将高召回 / 高错误代价的本地候选池选择性地转换为 current-source `EvidenceCore` spans。

输入：query、local candidate pool、runtime-observable uncertainty、model capability profile、latency/cost budget。输出/动作：local-only、weak/supporting、LLM span-narrow、LLM filter、abstain、request-more-context，然后 `EvidenceCore` 物化。核心原则：recall/admission 解耦；LLM 角色选择性路由；算法/model-adapter 分离；仅运行期可观测特征（用于 runtime-clean 策略）；worst-group / 跨模型鲁棒优化；候选必须物化进 current-source `EvidenceCore`。正式章节覆盖问题陈述、算法草稿/伪代码、证据边界、策略学习循环、adapter 边界、评估协议、当前 empirical 证据、no-go gaps、promotion blockers 与下一步研究计划。

逐字 carry forward（在 B10-B18 之外**无**新 claim）：

- **B10** —— `balanced_policy_v1_benchmark_routed` 是 benchmark-routed，**不**是 runtime-clean（`runtime_clean=false`）。
- **B10B** —— mechanics-validated 的 runtime-shadow scaffold + CI 集成；empirical support pending（在所有 B11 runs 中 label-driven denominator < 10）。
- **B11** —— official integrated matrix 32/32、384 records、aggregate verdict `partial_with_failure`；balanced_v1 vs p25 deltas：`Δgold_span -0.002604`、`ΔSpanF0.5 -0.001899`、`Δfalse_span -0.054688`、`ΔPFP -0.020833`、`Δmodel_calls -0.354167`。加强了 algorithm-candidate signal，但**不** promotion。
- **B12** —— public aggregate 无法识别机制；需要 per-record strategy/action outcomes。
- **B13** —— public aggregate 无法运行真实 DRO search；需要 per-record group/action outcomes。
- **B14** —— 无法从 public aggregates 校准 uncertainty；需要 per-record/model-output 结构。
- **B15** —— 无法从 public aggregates 学习 Context Pack Policy；当前价值仅是 preregistration/prior screen。
- **B16** —— downstream agent value 未被证明；需要固定 agent harness 与 patch/test outcomes。
- **B17** —— QuIVer systems track no-go：QuIVer graph/vector backend 缺失；仅 systems 的未来 track。
- **B18** —— OOD/temporal 从 public aggregate 是 no-go；需要 per-record temporal/repo/language/model/adversarial axes。

B19 公共 artifact（`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`，schema `b19-theoretical-synthesis-report-v0`）是 aggregate-only，运行一个 B19 专用的 forbidden-key scan（干净），嵌入一个 self-hash drift guard，并逐字节 carry forward B11 deltas。`eval/b19_theoretical_synthesis.py` 的 `--self-test` 验证 required sections、所有 no-promotion flags 为 false、B11 deltas 精确、forbidden scan 干净、docs links 存在、drift guard 匹配。无伪造 metrics；在 B10-B18 之外无新 claim。详见 [`b19-theoretical-synthesis.md`](b19-theoretical-synthesis.md)。

---

## 当前状态更新 —— 2026-06-13

The research program has moved beyond the original local-only benchmark stages
into controlled real-provider CI experiments. The current conclusion is not a
promotion decision; it is a sharper research boundary:

```text
RRF remains the recall base.
symbol/regex remain precision anchors.
query_noise_plus_rrf_agree_min remains the strongest guard candidate.
real dense embeddings have candidate/file-level signal but are unstable as global dense.
P20-LS-A blocks low-context/query-only LLM aliases, not rich-context LLM retrieval.
P21-G should prioritize cross-model context injection effects, richer code context, quality, latency, and cost.
Dense/QuIVer/LLM-derived/graph remain supporting/diagnostic/candidate only.
promotion_ready=false and current_default_should_change=false.
```

Most important recent finding: **L1/L2 and P20-LS-A exposed the weakness of
under-contextualized model retrieval**. L1/L2 showed dense-only/global dense risk
with `BAAI/bge-m3` and the conservative `path_plus_symbol` view at
`60 tasks / 1000 records / 2000 files`: four large-repo slices all had
`primary_false_positive_rate=1.0`, very low `SpanF0.5`, and unstable file recall.
P20-LS-A showed the same pattern for low-context/query-only LLM aliases: schema
and guardrails passed, but quality failed. This blocks dense-only/global dense
and low-context aliases from primary/default use, and shifts the next phase to
P21-G: context atoms, context packs, model profiles, roles, layouts, richer
snippets/candidate metadata, and explicit latency/cost accounting.

Current detailed conclusion reports:

- [`docs/zh/current-research-conclusions.md`](../zh/current-research-conclusions.md) /
  [`docs/en/current-research-conclusions.md`](current-research-conclusions.md)
- [`docs/zh/real-provider-ci-large-scale.md`](../zh/real-provider-ci-large-scale.md) /
  [`docs/en/real-provider-ci-large-scale.md`](real-provider-ci-large-scale.md)
- [`p20-llm-large-scale.md`](p20-llm-large-scale.md)
- [`p21-g-cross-model-context-injection.md`](p21-g-cross-model-context-injection.md)
- [`real-provider-ci-scale-p8-p9.md`](real-provider-ci-scale-p8-p9.md)
- [`real-provider-p7-summary.md`](real-provider-p7-summary.md)

Next research direction: freeze the L2 suite, attribute false positives, then
run P21-G cross-model context-injection experiments on public/opt-in corpora:
context atom screening, context pack ladders, LLM rerank/filter/span-narrow over
local candidates, inventory-grounded aliases, and prompt/context/layout matrices. Continue excluding
secrets, ignored files, provider keys, and private labels/gold answers, but do
not let context minimization dominate quality.

## P25 Bucket-Routed LLM Role Policy (2026-06-14)

A deterministic P25 policy evaluator (`eval/p25_bucket_policy.py`) is now
available. The committed report is a sanitized synthetic self-test scaffold
(`status=self_test_only`, `not_quality_evidence=true`), not a quality result.
Real P25 evaluation now requires ephemeral SCORE-phase records produced by
`eval/p21_llm_rich_candidate.py --p25-policy-records-out`; those records stay
under runner temp and are not uploaded, while P25 uploads aggregate metrics
only. The evaluator compares five policies: `candidate_baseline`,
`global_span_narrow`, `global_filter`, `global_abstain_filter`, and
`bucket_routed_v0`. The bucket-routed policy routes `llm_span_narrow` to
likely-positive/high-confidence buckets, routes `llm_filter`/`llm_abstain_filter`
to negative/dense-false-positive/ambiguous buckets using a fixed a-priori
negative strategy, skips LLM calls when an exact-symbol-plus-unique-anchor signal
is available, and falls back to the candidate baseline otherwise. Aggregate P21
summaries and non-ephemeral schemas are rejected with
`status=insufficient_task_detail`; no policy is promotion-ready or default-ready. See
[`docs/p25-bucket-routed-policy.md`](p25-bucket-routed-policy.md).

The first real P25 remote smoke then ran six successful aggregate policy runs
(`Flash/Kimi/GLM × py_flask/js_express`, 18 bucket-sampled tasks each) via the
safe P21→P25 ephemeral SCORE handoff. `bucket_routed_v0` strongly reduced false
spans (`108 -> 28`) and mean PFP (`-0.0926`), while losing some gold spans
(`24 -> 21`). Mean SpanF0.5 delta was only slightly positive (`+0.0026`) and
repo/model-dependent. This makes P25 useful as a false-primary reducer component
for P30 Admission V3, not a default/promotion candidate. Remote summary:
[`docs/p25-bucket-routed-policy-remote-smoke.md`](p25-bucket-routed-policy-remote-smoke.md).

## P30 Admission Model V3 (2026-06-14)

P30 adds a deterministic explainable admission model evaluator
(`eval/p30_admission_model_v3.py`) as a research-only follow-on to P25.
The committed artifact is a sanitized synthetic self-test scaffold
(`status=self_test_only`, `not_quality_evidence=true`) and is not a quality
result. P30 consumes the same ephemeral `p25-policy-records-ephemeral-v1`
records produced by `eval/p21_llm_rich_candidate.py --p25-policy-records-out`,
rejects aggregate summaries and non-ephemeral schemas, and routes only from
RUN-phase public/observable features (`task_bucket`, `task_risk_tags`,
`route_features`). Labels, gold, `score_group`, and outcome metrics are used
only for aggregate scoring after actions are chosen.

Allowed admission actions are: `abstain`, `admit_symbol_regex_union`,
`admit_rrf_primary`, `admit_llm_span_narrow`, `apply_llm_filter`,
`supporting_only`, and `weak_candidate_only`. The `admission_v3` scorecard
uses monotonic feature scores and hard guards around query noise,
exact/unique symbol anchors, symbol/regex/local anchors, RRF-backed-by-anchor
signals, LLM span-narrow validity/within-candidate, and negative/ambiguous/
dense-false-positive buckets. Dense and graph signals are allowed only as
supporting features; they cannot invent primary evidence.

The evaluator compares `candidate_baseline`, `llm_span_narrow`, `llm_filter`,
`llm_abstain_filter`, `bucket_routed_v0` (reused from P25), and
`admission_v3`. Aggregates include task count, SpanF0.5, PFP, added gold/false
spans, filter gold kill rate, abstain rate, action counts, score bands,
selective risk proxy, deltas versus the candidate baseline and
`bucket_routed_v0`, and explicit outcome-fallback counters for actions that do
not have measured outcomes in a given ephemeral record. Public output is
recursively scanned for forbidden keys
(raw query/snippet/prompt/response/gold/gold_spans/private label/provider key
fields). `promotion_ready=false`, `default_should_change=false`,
`evidencecore_semantics_changed=false`, `candidate_not_fact=true`,
`external_calls=0`.

P30 is intentionally not a promotion candidate. The next validation step is to
run the evaluator against real P25 ephemeral smoke records and compare the
scorecard to P25 `bucket_routed_v0` and the P22/P23 evidence-seeking guard
surfaces. See [`docs/p30-admission-model-v3.md`](p30-admission-model-v3.md).

The first real P30 remote smoke ran six successful workflow runs
(`Flash/Kimi/GLM × py_flask/js_express`, 18 bucket-sampled tasks each). On this
smoke, `admission_v3` matched `bucket_routed_v0`'s mean PFP reduction versus
baseline (`-0.0833`) but was more conservative and lower quality: baseline
`27/102` gold/false, `bucket_routed_v0` `19/39`, and `admission_v3` `17/41`.
Mean SpanF0.5 delta was `+0.0010` for `bucket_routed_v0` versus `-0.0102` for
`admission_v3`. Non-zero fallback counts show the current ephemeral handoff does
not yet provide enough measured local-anchor outcomes/features for P30's richer
admission actions. Conclusion: no promotion; extend the handoff with measured
`symbol_regex_union` / `rrf_primary` outcomes and safe route features before
rerunning P30. Remote report:
[`docs/p30-admission-model-v3-remote-smoke.md`](p30-admission-model-v3-remote-smoke.md).

P30-H1 repaired that handoff: P21 now writes ephemeral measured outcomes for
`symbol_regex_union`, `rrf_primary`, `supporting_only`, and `weak_candidate_only`,
and only pre-SCORE safe route features; P30 reports `admission_v3_h1` as the same
scorecard evaluated over enriched handoff records. Six real runs confirmed H1
fixed measurement fallback (`missing_action_outcome_count=0` for H1), but it did
not improve quality. P25 `bucket_routed_v0` remained stronger (`20/37`
gold/false, mean ΔSpanF0.5 `+0.0020`) than `admission_v3_h1` (`111/117`, mean
ΔSpanF0.5 `-0.0350`). The bottleneck moved from missing handoff to scorecard
quality: `symbol_regex_union` admission is too broad and needs stricter
agreement/bucket guards. Report: [`docs/p30-h1-remote-smoke.md`](p30-h1-remote-smoke.md).

P30-H2 tightened local-anchor admission (`symbol_regex_union` requires exact
unique symbol or span agreement; `rrf_primary` requires RRF/anchor span agreement;
file-only agreement is downgraded). Six real runs showed H2 remained
quality-comparable and fallback-free, but did not improve quality: P25
`bucket_routed_v0` was `16/36` gold/false with mean ΔSpanF0.5 `-0.0052`, H1 was
`111/117` with `-0.0346`, and H2 was `15/90` with `-0.0370`. The bottleneck is no
longer only primary admission breadth: weak/supporting/filter actions still carry
span-level false cost. Next P30 work should add action-specific span-cost budgets
and non-primary cost accounting before further route tuning. Report:
[`docs/p30-h2-remote-smoke.md`](p30-h2-remote-smoke.md).

P30-H3 implemented action-specific span-cost accounting as a score-phase-only,
diagnostic follow-on. It does not introduce a new admission route or policy; it
derives per-action cost from existing policies (`bucket_routed_v0`,
`admission_v3_h1`, `admission_v3_h2`, and baseline comparison policies). H3
reports, per action, selected count/rate, added gold/false spans, false/gold and
gold/false ratios, net span value at 1x and 2x weighting, deltas versus baseline,
mean ΔSpanF0.5 and mean ΔPFP, gold-kill rate and false-reduction rate, and
budget-violation flags. Policy-level summaries include primary/non-primary/
unclassified false-span cost, budget violation count/rate/reasons, and worst
actions by false cost and gold kill. The dedicated artifact is
`artifacts/p30_admission_v3/p30_h3_span_cost_report.json` with schema
`p30-h3-action-span-cost-report-v1`, and the doc is
[`docs/p30-h3-span-cost-accounting.md`](p30-h3-span-cost-accounting.md).
`promotion_ready=false`, `default_should_change=false`, `diagnostic_only=true`,
`score_phase_only_accounting=true`.

第一轮真实 P30-H3 smoke 已完成 6 个成功 runs（108 个任务）。baseline 为
`27/102` added gold/false spans；P25 `bucket_routed_v0` 仍是最强 reference，
为 `19/45`；P30-H1 为 `111/118`；P30-H2 为 `15/90`。H3 显示 P30-H1/H2 的
false-span 成本主要来自 primary local-admit actions，尤其是
`admit_symbol_regex_union` 和 H2 的 `admit_rrf_primary`；`supporting_only` 的主要成本是杀掉 gold、造成 recall loss，而不是新增 false spans。见
[`p30-h3-remote-smoke.md`](p30-h3-remote-smoke.md)。

## P31 Candidate Reach Ceiling Study (2026-06-14)

P31（`eval/p31_candidate_reach_ceiling.py`）是一个确定性、无远程调用的诊断性后续工具，
用于测量候选证据本身在没有任何路由或准入决策前覆盖 gold label 的频率。
它仅用于 SCORE 阶段：labels 只在 RUN 之后加载，并仅用于聚合指标。

输入与 P25/P30 相同，是 `p25-policy-records-ephemeral-v1` 临时 records。
P31-H1 扩展了 P21 rich-candidate 临时 handoff：records 现在携带轻量级候选池
（`p31_candidate_pools`）与仅 SCORE 阶段使用的 private gold spans（`p31_score_gold`），
并标记 `p31_h1_candidate_reach_handoff=true`、schema `p31-h1-candidate-reach-handoff-v1`。
池内条目仅保留 `rank`、`path`、`start_line`、`end_line`，以及可选的 `content_sha`、
`score`、`channels`；不含 snippet、原始 query/prompt/response 或 provider 字段。
当 H1 候选池缺失时，P31 只计算 outcome-only fallback 指标，并报告
`candidate_pool_availability=missing_candidate_pool`、`reach_metrics_available=false`，
而不是伪造零值。当候选池与 gold spans 均存在时，报告 K=1/3/5/10/20 的
`GoldFileReach@K`、`GoldSpanReach@K`、`GoldSpanExactReach@K`、
`CandidateAbsentRate@K` 和 `FileRightSpanWrongRate@K`。

P31-H2 增加 strategy-level reach matrix：对 `candidate_baseline`、`rrf_primary`、
`symbol_regex_union`、`llm_span_narrow`、`llm_filter`、`llm_abstain_filter`
分别报告 reach。此外还提供按公共 repo/task bucket 的聚合 reach、
unique reach share、pairwise file/span overlap 与 Jaccard span、
双向 marginal gain，以及固定策略组合的并集 reach。缺失策略池会报告
`availability=missing_pool`，而不是零值。

其他聚合诊断包括：与 `candidate_baseline` 对比的 `ModelMissGivenGoldPresent@K`
（覆盖 `llm_span_narrow`、`llm_filter`、`llm_abstain_filter`、`symbol_regex_union`、
`rrf_primary`、`bucket_routed_v0`、`admission_v3` 及 H1/H2）；从可用 per-action/per-strategy
outcome 字段推导的 `FilterKillGoldRate`、`AdmissionFalsePrimaryRate`、
`AdmissionFalseSpanPerNoGoldTask`；若不存在 rejection 字段则 `EvidenceCoreRejectRate` 为 `not_measured`。
同时输出 K=5 的聚合 failure funnel，并满足 `funnel_sums_to_positive_tasks=true`。

公开产物仅限聚合指标与公共任务元数据：不含 per-task 行、原始 query/snippet/prompt/response、
candidate paths/spans、gold spans、private labels 或 provider 字段。
安全标志锁定：`promotion_ready=false`、`default_should_change=false`、
`evidencecore_semantics_changed=false`、`candidate_not_fact=true`、
`remote_calls_by_p31=0`、`score_phase_only_metrics=true`、
`aggregate_only_public_artifact=true`。报告：
[`docs/p31-candidate-reach-ceiling.md`](p31-candidate-reach-ceiling.md)。


第一轮真实 P31-H1 reach smoke 已完成 6 个成功 runs。所有 runs 都检测到 H1 handoff，且 reach metrics 均可用。K=5 时 candidate baseline 在文件和 span 级别都只覆盖 `24/48` 个 positive tasks（`0.5000`），`FileRightSpanWrongRate@5=0/24`。这说明本轮 smoke 的第一瓶颈是 candidate absence。相同 runs 中 P25 `bucket_routed_v0` 仍是更好的 false-span reference（added gold/false `20/46`），优于 P30-H1（`111/117`）和 P30-H2（`15/90`）。见 [`p31-h1-remote-smoke.md`](p31-h1-remote-smoke.md)。

真实 P31-H2 strategy reach matrix 显示 `symbol_regex_union` 是当前主要 candidate-reach lever：K=5 时，`candidate_baseline` 覆盖 `24/48` 个 spans，`rrf_primary` 覆盖 `21/48`，而 `symbol_regex_union` 覆盖 `42/48`，并贡献 `18/48` 个 unique span hits。`candidate_baseline` 与 `rrf_primary` 或 `llm_span_narrow` 组合仍停在 `24/48`；与 `symbol_regex_union` 组合则达到 `42/48`。因此下一步 candidate-generation 侧应优先 P33 anchor repair/calibration，同时 P32/P30-H4 必须在 `symbol_regex_union` primary admission 前加入 action budget。见 [`p31-h2-strategy-reach-remote-smoke.md`](p31-h2-strategy-reach-remote-smoke.md)。

第一轮真实 P33 anchor precision smoke 已完成 6 个成功 runs。它没有发现任何 primary-safe observed anchor bucket。最强 calibration cell（`a3_r0_s2`：span agreement、low-risk、RRF-span-backed）保留了 P31-H2 的 reach ceiling（`42/48` positive spans），但 false cost 很高（`false_per_gold≈8.69`、`net_span_value_2x=-786`）。`symbol_regex_agree_span` 仍是高 reach 但高成本（`21/21` positive span reach，`false_per_gold=4.0`）；`symbol_regex_disagree` 和 `regex_only` 更差。见 [`p33-anchor-precision-repair-remote-smoke.md`](p33-anchor-precision-repair-remote-smoke.md)。

## P33 Reach-Preserving Precision Anchor Repair (2026-06-14)

P33（`eval/p33_anchor_precision_repair.py`）是 P31 之后一个确定性、无远程调用的诊断性工具，
用于研究 RUN 阶段可观测的 anchor 信号（symbol、regex、RRF anchor agreement、query noise、
公共 bucket、risk tags）与候选覆盖及 span cost 之间的关系。它复用与 P31 相同的
`p25-policy-records-ephemeral-v1` 临时 records，包括 `p31_candidate_pools`、
`p31_score_gold` 和 `route_features`；labels 只在 RUN 之后加载，并仅用于 SCORE 阶段聚合指标。

anchor taxonomy v1 包括原始 anchor 桶（`exact_unique_symbol`、`unique_symbol`、
`symbol_only`、`regex_only`、`symbol_regex_agree_span/file`、`symbol_regex_disagree`、
`rrf_agree_span/file`、`rrf_unbacked`）、公共 bucket/tag 桶、query-noise 等级，
以及有界组合桶。每个桶报告 task count、reach@5、span cost（added gold/false、false/gold、
net value）、平均 SpanF0.5、平均 primary false-positive rate，以及 diagnostic class。
同时输出三维校准矩阵：`anchor_strength` 表示 0=无 anchor、1=仅有 symbol/regex、
2=文件级 agreement、3=span 级 agreement、4=exact_unique_symbol_span_agreement；
`rrf_backing_level` 表示 0=无 RRF backing、1=仅文件级、2=span 级（不再使用泛化的
dense/graph support）。矩阵包含单调性检查，以及 `p33_to_p32_handoff` 的 budget
candidate buckets（`frozen_policy=false`）。缺失池会报告 `availability=missing_pool`
或 `not_measured`，而不是零值。

公开产物仅限聚合指标：不含 per-task 行、task IDs、query、snippet、prompt、response、
route features、candidate paths/spans、gold spans、private labels 或 provider 字段。
安全标志锁定：`promotion_ready=false`、`default_should_change=false`、
`evidencecore_semantics_changed=false`、`candidate_not_fact=true`、
`remote_calls_by_p33=0`、`score_phase_only_metrics=true`、
`aggregate_only_public_artifact=true`。报告：
[`docs/p33-anchor-precision-repair.md`](p33-anchor-precision-repair.md)。

## Stage status

| Stage | Status | Summary |
|---|---|---|
| R0 Research Harness | Passed initial gate | EvidenceCore/EvidenceMeta, trace JSONL, citation validation, and smoke eval harness are implemented. |
| R1 Local Evidence Kernel | Passed initial gate | Local read, repo scan, line-based regex/text search, policy basics, path safety, and context-lite file output are implemented without remote dependencies. |
| R2 Retrieval Method Bakeoff | Passed oracle review | BM25 (Tantivy), simple symbol search, and RRF fusion added. BM25 uses line-scoring, stale-hash skip, no-overlap skip. Symbol uses boundary delimiters. RRF merges wider metadata into narrower survivors. Eval harness reports file/line/span metrics and citation validity; Rust CLI validator provides hash/excerpt-backed citation validation. |
| R3 Level0 Storage Scaffold | Passed Level0 conformance | Store traits + StoreHit materialization gate + ConservativeChunkStore + TDB Level0 placeholder. Materialization rejects empty sha / stale / invalid hits, produces citation-valid Evidence from single file read (TOCTOU-safe). |
| R4 Level0 Derived Safety | Passed oracle review | DerivedIndexView model + deterministic rule generator + policy/citation/freshness gates + JSONL store. data_level hard-gated ≤1. Secret-like tokens filtered. High-risk kinds disabled. View IDs include policy_mode/generator_version. Stale mutation detected. JSONL parse errors surfaced. No quality claim. |
| R5 Level0 Graph Scaffold | Passed oracle review | GraphEdge carries source_content_sha/source_language. Materialization via StoreHit → openlocus_store::materialize_evidence (not hand-built). Invalid ranges rejected (not clamped). build_graph validates paths/sha, builds safe_records only. Depth=1 only. Channel::Graph. Citation-valid evidence. Not a precise semantic/call graph. |
| R6 Level0 Fast Context | Passed oracle review | 4-turn deterministic loop (lexical → symbol → graph → RRF fusion). EvidencePack-compatible output with trace_id. ActionRecord per-channel replay. Token budget (chars/4). Unknown channel gate. Final citation validation drops invalid. Orchestration scaffold only, not learned agent. |
| R7 Persistent BM25 Index + Warm SLO | Passed Level0 smoke (after oracle review gates) | Persistent Tantivy index at .openlocus/index/tantivy/ with mandatory manifest at .openlocus/index/manifest.json. schema_version=r7-bm25-v1. Search/open refuse if manifest is missing or policy_hash/schema mismatches. validate_path on every hit before file read. Empty content_sha → skip. Strict range (1≤start≤end≤total_lines, no clamp). build_index filters unsafe paths. PersistentBm25Index keeps the Index/searcher open and is reused by bench warm. Warm open=1ms, query p50=1ms. Bench invalid_citations uses real citation validation (hash/range/excerpt/freshness). 32/32 safety checks passed. Level0 implementation notes only; not a general performance claim. |
| R8 AST Chunking + Symbol Extraction | Passed Level0 smoke (40/40 checks) | Tree-sitter AST-bounded chunking and symbol extraction as experimental opt-in (--chunk-strategy ast). AST symbol Evidence uses Channel::TreeSitter, narrow header spans, current-file verification. Fallback to line windows for unsupported languages/parse errors. Manifest schema r8-bm25-v2 with chunk_strategy and ast_stats. R7 manifests loadable. Line remains default. |
| R9 AST vs Line Quality Bakeoff | Safety checks passed (21/21); quality gate false (FileRecall@5 regression) | eval/ast_quality_bakeoff.py compares persistent BM25 line vs ast on R2 fixture. Latest run: AST improves SpanF0.5@10 (+0.025), FileRecall@1 (+0.143), token_waste (−0.022), wrong_span_rate (−0.087), but regresses FileRecall@5 (−0.071). Citation_validity and structural_validity 1.0 for both. Latency is comparable/noisy in this tiny CLI benchmark. AST remains experimental/opt-in; line remains default. Negative result on gate is valid; fixture is small and self-referential. |
| R10 Incremental Index + Dirty Summary + Synthetic SLO | Passed Level0 smoke (37→48 incremental checks + synthetic SLO) | Dirty summary (dirty_index) computes manifest-vs-current scan: clean, requires_update, requires_rebuild, added/modified/deleted files with counts. Added detection uses ALL manifest paths (indexed+skipped); skipped→nonempty is modified not added. File-level update (update_index) via --dirty or --path: delete-by-term + re-add, commit once, manifest file write uses tmp+rename (not single transaction with Tantivy commit). Safety gates: missing manifest, policy/schema/strategy mismatch → refuse update (load failures also caught). Context-lite writes dirty-summary.json file. eval/incremental_index_smoke.py 48 safety checks. eval/synthetic_slo_bench.py: 1000-file synthetic repo, build_ms, dirty p50, persistent_cli_search p95, one-file update p50 (true modification each iteration), 0 invalid citations. Level0 synthetic only; not a general performance claim. TDB deferred to R11. |
| R11 TDB Level0 Adapter Probe | Passed Level0 smoke (21/21 adapter checks; 29/29 total store tests with --features tdb) | Feature-gated TriviumDB 0.7.0 adapter behind `tdb` Cargo feature. TdbChunkStore opens Database<f32> with dim=1, stores chunk metadata as JSON payloads (schema `tdb_chunk_v1`). Build discipline copies ConservativeChunkStore: validate_path, TOCTOU-safe sha, skip stale/traversal/empty. Capabilities honest: metadata+chunks only, no lexical/vector/graph. Marker-based purge safety. Materialization via StoreHit → materialize_evidence(). Default build unchanged; TDB is NOT a default dependency. Placeholder preserved. Level0 probe only; no retrieval quality claim. |
| R12 Real-Repo Incremental Robustness Bench | Passed hard safety checks (149/149); latency and catastrophic growth guard are report-only | eval/real_repo_incremental_bench.py tests R10 incremental update on temp copy of OpenLocus repo. Per-run unique markers avoid self-contamination. Positive gates require path+marker conjunction in cited excerpt (not disjunction). Branch delete/rename-old markers are proven indexed before removal. Latency compare uses twin repo copies with same mutation. Growth catastrophic guard (max(3×rebuild, rebuild+64MiB)); observed 20-cycle growth ~1.10×; does not prove long-term bounded growth. sys.exit(1) on safety failure only; latency/growth gates report-only. |
| R13 Remote Embedding / LLM-Derived Indexing Safety Scaffold | Passed Level0 safety (45/45 checks) | New crate `openlocus-provider` with EmbeddingProvider trait, MockEmbeddingProvider (deterministic blake3-based vectors, dimensions=32), DisabledEmbeddingProvider. Policy gate: remote denied by default, data_level ≤1 AND ≤metadata.max_data_level, secret scanning blocks SECRET/TOKEN/PASSWORD/API_KEY/sk_/ghp_/AKIA. Dense JSONL store at .openlocus/embeddings/vectors.jsonl stores EmbeddingRecord (vectors present, no raw text). Audit JSONL at .openlocus/audit/embeddings.jsonl (no raw text/vector/query). CLI uses query_sha/query_len (no raw query). Search produces StoreHits → materialize_evidence(Channel::Dense). Short file ranges: end_line=min(total_lines,8). Audit events: query_embed/allow/block/provider_unavailable (not cache_hit). CLI: provider status/audit, dense build/search/purge. 45/45 safety checks. Integration/safety only; not real semantic retrieval. |
| R14 Scaled Evidence Benchmark Foundation | Safety foundation passed (0 critical leakage; fail-closed architecture) | Scaled benchmark program with S/M/L/X tiers. R14-S: 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks, 48 labels, 47 hard negatives. Fail-closed safety: runner/scorer isolation (run=public tasks only, score=labels only), isolated temp roots per repo group, isolated `.openlocus/policy.toml` from repo lock, unknown repo_id refusal, citation validity must be 1.0 with Rust hash/range validation, runtime canary retrieval, repo lock content manifest re-verification (normalized SHA-256 per file sorted). Span-overlap hard_negative_hit_rate@10 + negative_nonempty_rate@10. eval/r14_generate_dataset.py, eval/r14_benchmark.py (strict RUN/SCORE phases), eval/r14_leakage_check.py (8 static checks, 0 critical), eval/r14_smoke.py (HARD FAIL, no best-effort). R14-S is a safety foundation, not a quality conclusion. R14-M partial. R14-L/X not populated (running --tier L/X fails). Graph precision is future feature track. |
| R15 External Multi-Repo Benchmark Expansion | Safety foundation passed (112/112 smoke checks) | 9 independent external repos across 5 languages, 166 medium tasks, 270 hard negatives. Regex FileRecall@1=0.852, BM25=0.548 on R15-M. BM25 negative_nonempty_rate@10=0.645. Mined benchmark expansion, not quality conclusion. |
| R16 Multi-Method Quality Bakeoff | All safety gates passed across R14-S/R15-M/R15-stress | Cross-matrix bakeoff of regex/bm25/symbol/rrf. RRF wins R15-M recall (0.933/0.993/0.959) but inherits BM25 negative false positives (0.645/0.684). Symbol best span precision (0.310 SpanF0.5, 0.052 hard_neg, 0.000 neg_nonempty). No method promoted to default. Lexical/symbol/RRF only; no provider/dense/LLM claims. |
| R17 Query Intent Router / Negative Guard | All source safety gates passed; citation inherited from validated predictions | Eval-layer router/guard experiment. query_only_router_v0 eliminates R15-M negative_nonempty (0.645→0.000) with acceptable recall regression (FileRecall@1 -0.037). rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty with zero recall regression. R15-stress negative_nonempty reduces but not eliminated (0.158/0.474). No Rust core changes. No LLM/dense claims. |
| R18 Threshold/Guard Calibration Sweep | All source safety gates passed; citation inherited from validated predictions; baseline consistency checked | Eval-layer calibration sweep over 46 strategies with 8 thresholds. Train-selected `rrf_guarded_by_symbol_regex` preserves RRF recall on R15-M/holdout and drops medium negative_nonempty to 0.000, but remains weak on stress (0.474 vs symbol 0.105). Separate query-noise+agreement strategies reach stress 0.000 as observations, not promotions. Pareto frontier computed. No core changes. No LLM/dense claims. |
| R19 Large/Stress Guard Generalization | All source safety gates passed; citation inherited from validated predictions; baseline consistency checked | Eval-layer generalization validation on R15-L (294 weak/mined tasks) and R15-stress. rrf_guarded_by_symbol_regex generalizes to R15-L (recall preserved, neg_nonempty 0.917→0.042) but fails stress (0.474 vs symbol 0.105). query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated (0.000). R15-L labels are weak/mined; generalization smoke only, not promotion evidence. promotion_ready=false always. No core changes. No LLM/dense claims. |
| R20 Auto-Wide Retrieval Failure-Surface Benchmark | Static validation passed (19/19 checks, 0 critical errors) | Generated/mined/weak failure-surface dataset for retrieval failure discovery, NOT promotion evidence. 741 tasks across 25 categories and 9 R15 repos. Public tasks contain only task_id/repo_id/query/public_version/source_tier. Private labels carry all judgement fields (query_category, expected_behavior, oracle_type, risk_tags, gold_spans, hard_distractors, must_not_primary, etc.). label_quality: mined_high_confidence/mined/weak only (no human_reviewed). Static validator enforces schema, enum, coverage, anti-leakage, manifest SHA, overlap constraints. No runner/scorer matrix yet. R21 will use it. Dataset + static validator only; no Rust core changes. |
| R21 Auto-Wide Strategy Matrix | 0 critical safety issues; citation_validity=1.0 all 10 strategies; promotion_ready=false | Eval-layer strategy matrix across 10 strategies on R20 auto-wide failure-surface dataset (741 tasks, 9 repos, 25 categories). All strategies have non-zero no_gold_nonempty_rate (0.167-0.495). BM25/RRF are no-gold-heavy (both 0.495). Symbol precision-best but abstains most (0.517). rrf_guarded_by_symbol kills 22.8% recall. query_noise_plus_rrf_agree_min best R21 guard balance (no_gold_nonempty_rate 0.221, FileRecall@1 0.693 preserved). Composite/guard strategies built from base predictions and also Rust citation-validated before cleanup; no labels in RUN. R20 labels weak/mined; not promotion evidence. No Rust core changes. No LLM/dense claims. |
| R22/R27 Failure Attribution | 13 failure clusters computed; 206 bucket regressions; promotion_ready=false | Analysis-only score phase: consumes R21 artifacts + R20 labels, produces failure clusters + expanded metrics. RRF_INHERITED_BM25_FALSE_POSITIVE=110, GUARD_RECALL_KILL=67 (symbol guard), SYMBOL_EXTRACTION_MISS=91, REGEX_NORMALIZATION_BUG=1, BENCHMARK_ORACLE_SUSPECT=62. Unrun strategies (dense/TDB/graph/AST) count=0 with recommended_next_tests. EVIDENCECORE_REJECTION metric_unavailable. 206 bucket regressions; promotion_blocked_by_bucket_regression=true. No retrieval re-run. No Rust core changes. No LLM/dense claims. |
| R23 Guard Parameter Sweep | 51 strategies swept; all blocked by bucket regression; promotion_ready=false | Eval-layer guard parameter sweep consuming R21 artifacts + R20 labels; does NOT change Rust core. 51 strategies across 8 dimensions (query_noise_threshold, rrf_score_threshold, regex/symbol/regex_or_symbol_agreement, top1_top2_gap_threshold, identifier_density_threshold, candidate_channel_count_threshold) plus 15 combined strategies. R21 artifacts manifest is verified fail-closed for every recorded path, sha256, byte count, and JSONL line count. All 51 strategies have bucket regressions. Combined query_noise_1+regex_or_symbol_agree is best R23 guard balance (no_gold_nonempty_rate 0.221 vs RRF 0.495, FileRecall@1 0.693 preserved, zero guard_recall_kill). Agreement guards reduce false positives without recall cost (0.279 no_gold_nonempty at zero kill). RRF score threshold >0.02 causes sharp recall cliff. Gap threshold kills too much recall even at 0.005. No strategy eliminates false positives without unacceptable recall loss. Curves: risk_coverage, recall_vs_negative, recall_vs_false_primary, precision_vs_abstain. 6877 total bucket regressions. promotion_ready=false. not_promotion_evidence=true. No LLM/dense claims. |
| R24 QuIVer/TDB/Dense Probe | Availability + mock dense candidate-channel probe; quiver_implemented=false; promotion_ready=false | NOT a QuIVer bakeoff. QuIVer is not implemented (scan confirms no impl in Rust crates; quiver_implemented=false). TDB is a feature-gated metadata/chunk store placeholder (available=false in default build). Dense mock is available as candidate-channel safety/quality-smoke (not semantic quality). Dense real is unavailable. R24 runs dense mock build/search on R20 auto-wide tasks in isolated repo roots, preserves embeddings/audit between build/search, validates citations fail-closed, and scores against R20 labels. Dense mock produced 5,264 citation-valid candidates but poor/noisy behavior (FileRecall@1 0.024, MRR 0.073, primary_false_positive_rate 0.878) plus 99 explicit candidate rejections. Canary hardening is non-vacuous: 8 non-empty dense stores checked, path/query canaries returned evidence, raw canary/query leakage=0. dense_mock_plus_rrf confirms dense contribution but increases noise (primary_false_positive_rate 0.923, hard_distractor_hit_rate 0.215). QuIVer diagnostic fields report unavailable/not_measured with reason quiver_not_implemented; no numeric 0 output as quality result. tdb_stale_leak_count is not_applicable. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0. |
| R25 Graph+Dense Ablation | Net-negative for both graph_basic and dense_mock; default expansion blocked; promotion_ready=false | Eval-layer ablation of graph_basic and dense_mock on R20 auto-wide (741 tasks). graph_basic: net-negative (0 gold, 435 false spans → blocked). dense_mock: net-negative (2 gold, 20,273 false → blocked). rrf_plus_graph dilutes RRF (FileRecall@1 0.693→0.497). rrf_plus_dense_mock also dilutes (0.693→0.134). graph_pollution_ratio=0.0. Citation validity remains 1.0: graph/dense/composites are revalidated in R25; no_graph inherits R21 validation after R25 verifies the R21 artifact manifest before baseline use. R25 source-leak canary is regex-only with seeded self-test, not a dense-path canary. QuIVer/TDB unavailable/not_measured. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0. |
| R26 Auto-Stress-1000 | Static validation passed (19/19 checks, 0 critical errors); NOT promotion evidence | Weak/mined/deterministic stress dataset for retrieval failure discovery. 1100 tasks across exact target counts for 10 stress categories and 9 R20 repos. Uses the same external repo set as R20 and derives some queries from existing R20 tasks/labels where useful. Public tasks contain only test_id/repo_id/query/public_version/source; category/risk/judgement fields live only in private labels. Private labels carry all judgement fields. No canary tokens. Deterministic seed 42. Validator fail-closes on exact category counts, public/private schema separation, task/label query consistency, span path/range validity, SHA-256 artifact checks, and repo content manifest SHA lock recomputation. Runner/scorer matrix now provided by R29. Designed to maximize failure discovery; NOT promotion evidence. Negative/abstain cases dominate (60%). No Rust core changes. No LLM/dense claims. |
| R28 Promotion Candidate Report | promotion_ready=false; current default should not change | Conservative synthesis of R21/R23/R24/R25/R26 reports over the R20/R26 failure-surface datasets. RRF remains best recall channel, symbol remains precision anchor, query_noise_plus_rrf_agree_min is promising but not stable enough due to R23 bucket regressions and unrun R26 retrieval matrix, graph/dense expansions are blocked by R25 added_false_span > added_gold_span, QuIVer/TDB have no independent quality evidence, dense_mock is noise/safety probe only. Default recommendation: no_change_current_evidence_gated_local_retrieval. Next required tests: run R26 strategy matrix, add human-verified labels, implement real embedding/QuIVer only after runner gates exist. |
| R29 R26 Auto-Stress Strategy Matrix | promotion_ready=false; not_promotion_evidence=true; failure-surface only | Eval-layer strategy matrix across 16 strategies (4 base + 6 composite/guard + 6 graph/dense/composite) on R26 auto-stress (1100 tasks, 10 stress categories, 9 repos). Strict RUN/SCORE separation: run phase loads only public tasks + repo lock, never labels; score phase loads labels only. R26 provenance validated before run. Citation validity must be 1.0 for all strategies. 14 required failure clusters computed. Span contribution analysis for graph/dense/composites vs fresh RRF baseline. Bucket regressions across source_category/expected_behavior/oracle_type/repo_id/risk_tags. Private field scan on all JSONL artifacts. 5 unavailable strategies report reason only (no fake numeric quality). dense_mock is candidate-channel safety smoke, not semantic quality. QuIVer not implemented. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0. |
| R30 Baseline Freeze | Completed; no promotion | Frozen R29/R26 stress matrix as the comparison baseline. When raw R29 runtime artifacts were absent from checkout, R30 explicitly used committed R29 docs/manifests and recorded missing artifact status rather than fabricating original predictions. Subsequent experiments report `delta_vs_r29_*` fields against this frozen baseline. |
| R31 Real Embedding Provider Smoke | Completed; safety gates first | Implemented OpenAI-compatible real embedding provider plumbing, remote-default-deny gates, audit/no-raw-text policy, provider request headers, optional `dimensions` field support, and local mock plus real-provider smoke. Real provider access was validated, but R31 made no quality claim. |
| R32 Embedding View Bakeoff Harness | Completed; supporting-only | Added view bakeoff harness for multiple embedding views with RUN/SCORE separation. Default is local/mock; real remote runs are explicit/manual and currently remote-safe `path_plus_symbol` only. Reports FileRecall, SpanF0.5, PFP, citation validity, provider calls, and `delta_vs_r29_baseline`. Dense output remains candidate/supporting-only. |
| R33 QuIVer Readiness Diagnostics | Completed; diagnostic-only | Added BQ2/sign-magnitude diagnostics over real embeddings: BQ overlap, BQ-vs-f32 MRR, sign entropy, angular gap, centroid/shard variance. QuIVer graph/Vamana is still not implemented; R33 emits diagnostic evidence only, no ANN quality claim. |
| R34-R36 QuIVer/BQ + Anchor Prototype | Completed; no default expansion | Added offline/real-provider prototype comparisons: flat f32, BQ top-k + f32 rerank, source/test split, per-view/language ideas, and regex/symbol anchor variants. Early tiny results were optimistic, but public corpus and L1 slice runs showed added_false often exceeds added_gold. QuIVer/dense remain supporting-only. |
| R37-R38 LLM-Derived Views + Stress | Completed; not Evidence | Real LLM provider smoke succeeded. LLM output is used only for derived views/stress/failure discovery with `not_evidence=true`; it does not generate Evidence, gold labels, citation verdicts, or promotion verdicts. Private labels are not uploaded in CI. |
| R39-R40 Symbol/Regex Repair Bakeoff | Completed; needs larger validation | Offline repair bakeoff showed `regex_hybrid_normalized` and symbol extraction repair are promising recall-safe directions. They still need fixed-suite validation for bucket regressions before any default-path consideration. |
| R41-R42 Graph Role + Admission v2 | Completed; research-only | Reframed graph as supporting/rerank/explainer, not default expansion. Added admission_v2 rule research with actions like admit_primary/admit_supporting/weak_candidate/abstain, but no learned/default admission change. |
| R43-R45 Integrated Long-Run Report | Completed; promotion_ready=false | Consolidated R30-R42 outputs into real-model matrix summary, failure clusters, and promotion candidate report. Conclusion: RRF recall base, symbol precision anchor, query-noise guard best current candidate, dense/QuIVer/LLM-derived/graph all non-default. |
| P1-P7 Real Provider Bring-up | Completed; real providers usable | Ran real embedding and LLM smoke locally/CI with gitignored `.env.local` and GitHub `production` environment. SiliconFlow embedding and OpenAI-compatible LLM access were validated. P2/P3/P4/P5/P6/P7 produced first real-provider summaries; no provider URL/key committed. |
| P8/P9 Real-Provider CI Scale-Up | Completed; first public CI slices | Added `real-provider-benchmark.yml` manual workflow with `environment: production`, guarded secrets, input validation, and no private label upload. Ran small public corpus, model bakeoff (`bge-m3`, Qwen 0.6B/4B/8B), and multilingual smoke. Result: file-level signal exists, but SpanF0.5 remains low and model size did not dominate in first slices. |
| L1/L2 Real-Provider Large-Repo Slices | Completed; strong dense-only/global-dense block | Ran controlled large-repo slices across Django, Kubernetes, Next.js, and Deno. L1 showed file-recall variability and P4 false-span growth. L2 (`60 tasks / 1000 records / 2000 files`) had PFP=1.0 on all four repos, very low SpanF0.5, and unstable FileRecall. Conclusion: dense-only/global dense must remain supporting/candidate-only; next phase should freeze L2, attribute false positives, and test constrained dense. |
| P10-P14 Constrained Dense Research | Planned | Proposed next phase: freeze `real_provider_l2_v1`, attribute L2 false positives, simulate constrained candidate pools locally, run small remote constrained variants, then rerun fixed L2 only if added_gold exceeds added_false and PFP drops. No EvidenceCore changes and no promotion. |
| P20-LS LLM Large-Scale Eval Harness | P20-LS-A completed; low-context alias blocked | Bounded eval-only harness (`eval/p20_llm_large_scale.py`) for LLM-derived query aliases and stress-label generation. Remote runs require `workflow_dispatch + enable_remote_models=true + OPENLOCUS_ALLOW_REMOTE=1`. P20-LS-A ran `Kimi-K2.7-Code` on self-test plus 9 real CI corpus runs (220 real provider calls). All LS0/LS1 safety gates passed, no raw source/private labels/prompts uploaded, but 0/9 real runs passed quality: added_gold_span=289 vs added_false_span=8312 (~28.8:1 false:gold), avg fabricated_identifier_rate≈0.459. Narrow decision: stop scaling low-context/query-only LLM aliases. This is not a verdict on rich-context LLM retrieval; it motivates context-grounded rerank/filter/span-narrow experiments. No EvidenceCore changes; promotion_ready=false; default_should_change=false. |
| P21-G Cross-Model Context Injection Research | P21-G3L-R GLM tool_call confirmed under low concurrency | Research pivot from minimal-context baselines to cross-model context-injection effects. P21-G1E found rich embedding views have file/span signal but naked dense false spans dominate. P21-G2E found constrained dense (`dense_atom_signature_rrf_file_constrained`) has modest supporting value but dense remains non-primary. P21-G3L found LLM span narrowing has promising but model/repo-specific signal; filter/abstain often kill gold. P21-G3L-R added provider-level output modes (`prompt_only`, `json_object`, `json_schema_strict`, `tool_call`), fallback diagnostics, and one no-fallback schema repair retry. GLM 4-mode comparison found `tool_call` best (avg SpanNarrow Δ +0.0677), `prompt_only` blocked, `json_object` insufficient, `json_schema_strict` mixed. A sequential low-concurrency `tool_call` rerun removed 429 noise and improved GLM SpanNarrow avg Δ to +0.1361 across py_flask/js_express. Next: bucketed GLM/Kimi/Flash `span_narrow` with `tool_call` for GLM; filter/abstain remain non-default. EvidenceCore remains final authority. |
| P21-G3B Bucketed LLM Role Study | Bucketed smoke completed; global LLM roles blocked | Public task generation now exposes safe `task_bucket/task_risk_tags` and P21 runners support `round_robin_public_buckets`, so RUN can sample mixed buckets without labels/gold. First true bucketed LLM role smoke ran 6 runs (Flash/Kimi/GLM × py_flask/js_express, 18 tasks each, provider concurrency ≤6). Bucket coverage now includes abstain/weak/no_gold/ambiguous/dense_false_positive buckets. Result: all LLM roles reduce PFP materially, but often by killing gold spans; global `span_narrow` is positive on py_flask but negative on js_express mixed buckets; `filter`/`abstain` are useful as false-positive reducers only in specific buckets, not as defaults. Next: build a rule-based policy that routes `span_narrow` only to likely-positive/high-confidence tasks and `filter/abstain` only to negative/dense_false_positive/ambiguous buckets. |
| P22/P23 Evidence-Seeking Policy Surface | Decision surfaces frozen; bottlenecks decomposed | P22/P23 moves from channel bakeoffs to strategy-surface analysis. It freezes two capped local surfaces with hashes and no remote/model calls: `r20_positive` (120 positive tasks across 9 repos) and `r26_guard` (120 no-gold stress tasks across 9 repos). R20 shows RRF is still the reach base (`Reach@5=0.975`, `SpanReach@5=0.95`) but symbol has best local SpanF0.5 (`0.3169`) and `symbol_regex_union` is the best precision/reach experimental baseline candidate for P25/P30. R26 shows BM25/RRF create noisy false primary (`NoGoldFP=0.2833`) while symbol/regex/union/guard abstain, so guard stress must be evaluated separately from positive reach. Reports: `docs/p22-p23-policy-surface.md`, per-surface docs/artifacts under `docs/` and `artifacts/p22_p23/`. |
| P25 Bucket-Routed LLM Role Policy evaluator | Self-test scaffold ready; real evaluation requires ephemeral P21/P25 handoff | `eval/p25_bucket_policy.py` is deterministic and no-remote. It routes by public `task_bucket`/`task_risk_tags` and compares candidate_baseline, global span/filter/abstain, and bucket_routed_v0. Aggregate summaries/non-ephemeral schemas are rejected. First real smoke reduced false spans but also some gold spans; useful as P30 false-primary reducer, not default. Report: `docs/p25-bucket-routed-policy.md`. |
| P30 Admission Model V3 | Self-test scaffold ready; real evaluation requires ephemeral P21/P25 handoff | `eval/p30_admission_model_v3.py` is deterministic, explainable, no-remote. Routes only from public task_bucket/task_risk_tags/route_features; allowed actions are abstain/admit_symbol_regex_union/admit_rrf_primary/admit_llm_span_narrow/apply_llm_filter/supporting_only/weak_candidate_only. Compares baselines plus admission_v3, reports score bands/selective_risk/deltas, and recursively scans public output for forbidden keys. Not promotion-ready; next step compare to P25 real smoke and P22/P23 guards. Report: `docs/p30-admission-model-v3.md`. |
| P31 Candidate Reach Ceiling Study | Scaffold ready; diagnostic-only, SCORE-phase-only | `eval/p31_candidate_reach_ceiling.py` measures whether candidate evidence alone reaches the gold label at K=1/3/5/10/20 before any routing or admission. Deterministic, no-remote, aggregate-only. Falls back to outcome-only metrics when candidate pools are missing, clearly marked `missing_candidate_pool`/`reach_metrics_available=false`. Reports reach@K, span-exact reach, candidate absent rate, file-right-span-wrong rate, strategy miss given gold present, filter/admission diagnostics, and K=5 failure funnel. `promotion_ready=false`, `remote_calls_by_p31=0`. Report: `docs/p31-candidate-reach-ceiling.md`. |
| P33 Reach-Preserving Precision Anchor Repair | Scaffold ready; diagnostic-only, SCORE-phase-only | `eval/p33_anchor_precision_repair.py` 研究 pre-SCORE anchor 信号与覆盖/span cost 的关系。消费 P21/P31-H1 临时 records，聚合 anchor taxonomy v1、三维校准矩阵和 P32 budget candidate handoff。公开产物仅限聚合指标，不含 per-task 行、route features 或 private 字段。`promotion_ready=false`，`remote_calls_by_p33=0`。报告：`docs/p33-anchor-precision-repair.md`。 |
| P33-B Anchor Subtype Calibration | Scaffold ready; diagnostic-only, SCORE-phase-only | `eval/p33b_anchor_subtype_calibration.py` 消费 P21/P33-B 临时 handoff，并聚合 per-candidate anchor subtype 诊断（按 agreement/RRF/risk 分桶的 `symbol_only`、`regex_only`、`symbol_regex_fusion`）以及三维校准矩阵。公开产物仅限聚合指标，不含 per-task 行、route features、subtype rows 或 private 字段。`promotion_ready=false`，`remote_calls_by_p33b=0`。报告：`docs/p33b-anchor-subtype-calibration.md`。 |

## P33-B Anchor Subtype Calibration（2026-06-15）

P33-B 在 P21 临时 handoff 中增加 per-candidate anchor subtype 元数据
（`p33b_anchor_subtypes`，schema `p33b-anchor-subtypes-v1`），用于测量
`symbol_only`、`regex_only`、`symbol_regex_fusion` 三种 source class，
以及 agreement class（`single_source`、`same_file_only`、`span_overlap`、
`disagree`）和 RRF-backing 状态在 `symbol_regex_union` 扩展内部的
reach/cost 轮廓。handoff 同时携带 `symbol_primary` 和 `regex_primary`
pool 供 P31 reach 研究使用。

`eval/p33b_anchor_subtype_calibration.py` 是确定性、无远程调用的。它在 SCORE
phase 将 subtype 行与 union 候选对齐，报告有限的 subtype-bucket 诊断
（GoldFile/SpanReach@5、FRSW、unique span reach、粗粒度 task-level span cost
归因、相对 candidate_baseline 的 delta）以及覆盖 source_strength、
match_quality、risk_level 的三维校准矩阵与单调性检查。缺少 subtype handoff
时，`availability` 报告 empty/missing 原因而非伪造零值。
`p33b_to_p32_handoff` 按 diagnostic class 分组 budget candidates，
`frozen_policy=false`。

公开产物仅限聚合指标，明确禁止 per-task 行、task ID、candidate paths/spans、
subtype rows、route features、labels 与 provider 字段。安全标记锁定：
`promotion_ready=false`、`default_should_change=false`、
`evidencecore_semantics_changed=false`、`candidate_not_fact=true`、
`remote_calls_by_p33b=0`、`score_phase_only_metrics=true`、
`aggregate_only_public_artifact=true`。报告：`docs/p33b-anchor-subtype-calibration.md`。

真实 P33-B subtype smoke 完成 6 个成功 runs（108 个 task observations，36 positive，72 no-gold）。它确认：更细的 subtype 拆分仍然没有产生 primary-safe bucket。`span_overlap` 是最好的粗粒度 agreement class（`false_per_gold≈1.78`，`GoldSpanReach=1.0`），但在 2x false-span penalty 下仍是 net-negative；`symbol_regex_fusion` reach 高，但 added gold/false 为 `24/66`；`disagree` 和 `single_source` 被 false-span cost 主导。这些 subtype bucket 应该作为 P32/P30-H4 budget 输入，而不是 primary admission。见 [`p33b-anchor-subtype-remote-smoke.md`](p33b-anchor-subtype-remote-smoke.md)。

## P32 / P30-H4 预算覆盖层（2026-06-15）

`eval/p30_admission_model_v3.py` 现已加入 `admission_v3_h4` 策略，即 P32/P30-H4 确定性预算覆盖层。H4 仅消费 RUN-phase 公开特征（`task_bucket`、`task_risk_tags`、`route_features`）以及私有 P33-B subtype handoff（`p33b_anchor_subtypes`、`p33b_anchor_subtypes_schema`），并基于 P33-B 结论测试 budgeted demotion，而非 primary promotion。

路由规则保守：negative/dense/ambiguous 任务过滤或弃权；低危公开 bucket 中 `span_overlap` 若带 RRF backing 则归为 `supporting_only`，否则 `weak_candidate_only`；`same_file_only` 仅在明确 positive bucket 中归为 `weak_candidate_only`；`disagree`/`single_source` 除非公开 bucket 强 positive 且 query noise 低，否则过滤。exact/unique-symbol 信号被视为 budget 诊断性非 primary。缺失 subtype 元数据时退化到类 `bucket_routed_v0` 的保守回退。H4 不会仅基于 subtype 证据选择 `admit_symbol_regex_union`、`admit_rrf_primary` 或 `admit_llm_span_narrow`。

私有 handoff 字段会被复制到归一化后的内存任务中供 SCORE-phase 使用，但不会出现在 P30 公开产物中。报告标志锁定：`h4_budget_overlay=true`、`promotion_ready=false`、`default_should_change=false`；当存在 P33-B 记录时，`h4_available=true` / `p33b_handoff_detected=true`。H4 与 H1/H2 一样报告 `quality_comparable`、`blocked_by_missing_action_outcomes` 和 `selected_action_fallback_rate`；real-provider CI gate 要求 H4 存在，并在 `p21_llm_rich` 真实记录上质量可比且 selected-action fallback 为零。见 [`p32-p30-h4-budget-overlay.md`](p32-p30-h4-budget-overlay.md)。

真实 P30-H4 remote smoke 完成 6 个成功 runs，并显示 all-demotion overlay 过度保守：H4 quality-comparable 且 fallback-free，但产生 `0/0` added gold/false spans，mean SpanF0.5 为 `0.0000`。相同 runs 中 P25 `bucket_routed_v0` 仍是最佳 reference（added gold/false `27/34`，mean SpanF0.5 `0.0768`）。因此 H4 下一步应转向 budgeted selective re-admission 或 `request_more_context` variants，而不是 all-demotion。见 [`p32-p30-h4-remote-smoke.md`](p32-p30-h4-remote-smoke.md)。

## P32 / P30-H4B 选择性 Re-Admission（2026-06-15）

`eval/p30_admission_model_v3.py` 现已加入 `admission_v3_h4b` 策略，即 P32/P30-H4B 选择性 primary re-admission 诊断。H4B 与 H4 消费相同的 RUN-phase 公开特征和私有 P33-B subtype handoff，但使用极窄的严格门测试是否有一小部分任务可安全地重新 primary admit；绝大多数任务被 hard-guard 或降级。

严格门仅在以下全部满足时允许 `admit_symbol_regex_union`：最优子类型为 `symbol_regex_fusion` + `span_overlap` + `rrf_backing`；`local_anchor` 和 `symbol_regex_agree_span` 为真；`query_noise <= 0.1`；公开 bucket/tag 属于低危 positive 集合；且 `exact_unique_symbol_anchor` 或 `rrf_anchor_agree_span` 至少一个为真。若同时还有 `rrf_backed_by_anchor` 和 `rrf_anchor_agree_span`，H4B 可选择 `admit_rrf_primary`。所有 negative/dense/ambiguous/hallucination/high-noise、缺失 handoff，以及最优子类型为 `regex_only`/`same_file_only`/`disagree`/`single_source` 的任务都路由到 `apply_llm_filter`、`supporting_only` 或 `weak_candidate_only`。

公开产物包括 `h4b_available`、`h4b_budget_overlay=true`、`h4b_selective_readmission=true`、`h4b_primary_opportunity_count`、策略级 `rule_counts`、`false_per_gold`、`net_span_value_2x`、`span_cost_summary` 以及 H1/H2 风格的质量可比性。合成 self-test 中 H4B 质量可比且 fallback-free，触发少量严格 primary opportunity。真实 H4B smoke 验证了 selective re-admission 方向，但还没有追上 P25：H4B 从 H4A 全刹车中恢复（added gold/false `0/0 -> 24/41`），而 P25 仍更好（`25/30`，mean SpanF0.5 `0.0683`；H4B `0.0433`）。见 [`p32-p30-h4b-selective-readmission.md`](p32-p30-h4b-selective-readmission.md) 和 [`p32-p30-h4b-remote-smoke.md`](p32-p30-h4b-remote-smoke.md)。

## R0/R1 initial findings

- Evidence precision matters immediately: the first regex implementation returned over-wide line ranges for distant matches in one file. This would have harmed token waste and Span F0.5. The fix moved R1 regex/text search to one narrow Evidence per matching line.
- Citation validation must validate more than hashes. Range validity and excerpt consistency are needed to catch incorrect spans.
- Path safety is part of evidence safety. Symlink escape protection is required before treating read output as verified current evidence.
- The current local baseline is intentionally boring: no dense, graph, TDB, or LLM indexing has been added yet. This keeps R0/R1 suitable as the control group for later bakeoffs.

## R2 findings

- **BM25 substantially improves file-level recall on the current self-referential fixture**: 0.39 vs 0.21 at k=1, 0.86 vs 0.36 at k=5.
- **Symbol search is high-precision but narrow**: only activates for definition-style queries, but when it fires, line precision is the highest of all methods (0.39) and wrong_span_rate is 0.0.
- **RRF fusion approaches BM25-level recall** while incorporating symbol precision, achieving 0.82 FileRecall@5 and 0.057 SpanF0.5@10 on the current fixture.
- **All methods produce structurally citation-valid evidence in the Python scorer**; aggregated current R2 output was also validated by the Rust CLI citation validator with `0` invalid citations (hash/range/excerpt checked).
- **Token waste is high** (~0.92) because evidence spans are often near-but-not-on narrow gold spans.
- **CLI end-to-end latency** (not warm-index): regex ~13ms, BM25 ~113ms, symbol ~161ms, RRF ~272ms.

## R3 findings

- **Materialization gate is essential and works**: empty sha rejected, stale hits rejected, invalid ranges rejected, TOCTOU-safe (sha + excerpt from same bytes), produced Evidence is citation-valid.
- **TOCTOU safety matters**: reading file bytes once and deriving both sha and excerpt from that single read prevents a modification between reads from producing inconsistent evidence.
- **ConservativeChunkStore validates paths and skips bad records**: traversal paths rejected, stale content_sha skipped, empty files produce no invalid chunks.
- **TDB placeholder provides clean Level0 surface**: returns available=false, success=false with descriptive errors, never panics.
- **This is a Level0 storage scaffold**, not a full storage bakeoff or TDB comparison.

## R4 findings

- **Safety scaffold works**: all gates are functional and block by default. High-risk kinds blocked, data_level hard-gated at ≤1 for Level0, experimental opt-in required, no remote calls.
- **Deterministic view IDs include policy_mode and generator_version**: same source/kind/generator/data_level/policy_mode/generator_version always produces the same ID; change in any produces different ID.
- **No raw full code at data_level ≤ 1**: derived text contains only metadata (line range, language, first identifier). Prevents accidental exposure in derived artifacts.
- **Secret-like tokens are aggressively filtered**: identifiers containing SECRET/TOKEN/PASSWORD/API_KEY/PRIVATE_KEY, or with prefixes sk_/ghp_/AKIA, or long high-entropy mixed strings are not emitted in tags or aliases.
- **JSONL parse errors are surfaced** (not silently skipped): `derived validate` reports parse_errors count.
- **Stale mutation is detected**: building views, modifying a source file, then validating correctly reports stale views.
- **DerivedIndexView is NOT Evidence**: cannot bypass StoreHit/materialize_evidence gate. Any future derived search must materialize source evidence.
- **This is a Level0 safety scaffold only. No quality claim about derived view relevance or usefulness.**

## R5 findings

- **StoreHit materialization gate is essential**: graph edges are converted to StoreHit and delegated to `openlocus_store::materialize_evidence()`. This ensures consistency with all other materialization paths and prevents hand-built Evidence from bypassing validation.
- **GraphEdge carries build-time sha and language**: source_content_sha and source_language allow the materializer to detect stale edges and reject invalid ranges (not clamp them).
- **build_graph validates paths and current sha**: safe_records with validated path and current sha are used for all edge builders (imports, tests, configures). Stale and path-unsafe records are counted and skipped, producing no edges.
- **Simple line-based import parsing works for Rust/Python repos**: mod/use, import/from lines are easy to parse and resolve against the path_set.
- **Config edges are noisy but bounded**: Cargo.toml/package.json link broadly to nearby source files in the fixture. This favors recall but can create many false positives; no general precision/recall claim is made.
- **Depth=1 only; depth>1 returns clear error**: not silently expanded.
- **graph inspect wraps output with artifact marker**: `artifact="graph_edges_not_evidence"` makes it clear these are not citation-valid Evidence.
- **This is a Level0 deterministic scaffold only. Not a precise call graph, type graph, or dependency graph.**

## R6 findings

- **4-turn deterministic loop works as orchestration scaffold**: lexical → symbol → graph → RRF fusion produces multi-channel evidence without any LLM planner.
- **Symbol turn is conditionally activated**: skipped when query lacks identifier-like tokens, avoiding wasted computation.
- **Token budget enforced**: `--budget N` uses chars/4 approximation; evidence trimmed from bottom if cumulative tokens exceed budget. `--max-evidence` is separate count cap.
- **Unknown channel gate**: channels outside regex/text/bm25/symbol/graph are rejected with clear error.
- **Final citation validation**: evidence filtered through `is_citation_valid` before output; invalid dropped and counted in `diagnostics.invalid_citations_dropped`.
- **EvidencePack-compatible output**: `pack` field with trace_id, budget_used. `evidence` field preserved for direct access.
- **ActionRecord per-channel replay**: each turn/channel recorded with query, result_count, latency_ms, optional error. Written to `.openlocus/traces/fast-context-<trace_id>.json`.
- **Confidence derived from top RRF score**: low confidence (<0.1) triggers a missing_question.
- **Orchestration scaffold only, not learned agent.** No adaptive re-querying, no feedback loops, no LLM planning.

## R7 findings

- **Persistent Tantivy BM25 index with manifest works**: build creates .openlocus/index/tantivy/ + .openlocus/index/manifest.json. status/validate/search/purge CLI commands all functional.
- **Manifest and policy gates enforced**: search_persistent_bm25 and PersistentBm25Index::open require the manifest and check manifest policy_hash/schema against current Policy/schema; refuse search if manifest is missing or mismatched. validate_index reports policy_hash_matches=false. Eval confirms: policy change after build → search refuses, validate detects mismatch; manifest deletion → search refuses.
- **Stale/deleted hits are skipped, not emitted**: search_persistent_bm25 re-reads every hit's current file, computes content_sha, and skips mismatches. No stale VerifiedCurrent evidence is ever produced.
- **Empty content_sha bypass prevented**: Hits with empty index_content_sha are skipped (invalid_hits_skipped++), cannot bypass stale check.
- **validate_path on every Tantivy hit**: Before reading a file from a Tantivy hit's path, validate_path is called. Invalid paths → skip. build_index also filters unsafe FileRecord paths.
- **Strict range validation, no clamping**: Chunk ranges must satisfy 1 ≤ start ≤ end ≤ total_lines. Invalid ranges → skip (invalid_hits_skipped++), not clamped.
- **Manifest enables fast staleness detection**: status_index quickly checks all indexed files' current sha against manifest entries. validate_index reports specific stale/deleted/path_unsafe files.
- **Policy exclusion works end-to-end**: .env and *.pem files are excluded by scan_repo, never indexed, and never appear in persistent search output.
- **Warm benchmark is honest**: PersistentBm25Index::open opens the Index/searcher once; same handle reused for all queries with no per-query Index::open. index_open_ms measures open cost only (1ms). index_build_ms reported separately if build was needed. invalid_citations uses real citation validation (hash/range/excerpt/freshness check), not just range.
- **Warm query latency**: On the current small self-referential workspace snapshot, warm queries take 1-2ms per query after index is opened. Open cost is 1ms.
- **Safety is preserved**: Every persistent search hit is re-verified against the current filesystem. The Tantivy stored body is never used as the final excerpt.
- **Purge is safe**: Only deletes known R7 artifact paths under .openlocus/index/. Canonicalizes paths and refuses to delete if index_dir escapes repo root.
- **This is a Level0 implementation only. No incremental update; build is always full rebuild. Warm SLO numbers are from a small self-referential codebase; not a general performance claim. R7 Level0 passed only after oracle review gates.**

## R8 findings

- **Tree-sitter AST-bounded chunking is functional as an experimental scaffold**: `openlocus-ast` crate parses Rust, Python, JavaScript, and TypeScript using Tree-sitter 0.25.x. AST chunk boundaries align with logical code structures (functions, classes, structs, etc.) rather than arbitrary line windows. Oversized nodes are split into line windows; gaps are covered by fallback line windows; no overlapping chunks.
- **AST symbol extraction produces narrow, citation-valid Evidence**: `extract_ast_symbols` extracts definition nodes with header/signature spans (max 10 lines, usually signature/header only rather than full bodies). Symbol names are extracted from Tree-sitter node fields. AST symbol Evidence uses Channel::TreeSitter and is verified against the current filesystem (hash/excerpt/freshness).
- **Fallback is correct**: Unsupported languages (e.g., Go) fall back to line-window chunking. Parse errors also fall back to line windows. No data loss. Fallback stats are visible in manifest ast_stats.
- **Opt-in, not default**: `--chunk-strategy ast` is experimental; line-window remains the default. No quality claim about AST chunking superiority until eval computes it.
- **Manifest schema r8-bm25-v2**: Includes chunk_strategy and ast_stats fields. R7 manifests (r7-bm25-v1) still loadable with default chunk_strategy=line_window_v1. Unrecognized schema versions refuse with rebuild instruction.
- **Schema/strategy mismatch refusal**: search/validate/status refuse if manifest chunk_strategy is unrecognized. R7 manifests without chunk_strategy are loaded as line_window_v1 for compatibility; R8-written manifests always include chunk_strategy. No silent search of unverifiable strategy.
- **CLI symbol search modes**: `openlocus search symbol <name> --mode regex|ast|auto`. Default auto: AST first for supported files, regex fallback for unsupported/no results. Regex mode preserves existing behavior.
- **R7 persistent smoke still passes**: Default line build continues to work with all 32 safety checks passing.
- **AST smoke eval passes 40/40 checks**: Including AST build/status/validate/search, parser-error visibility, stale mutation, narrow AST symbol header, symbol search modes, citation validation, schema mismatch, policy exclusion, default line build compatibility.
- **This is a Level0 experimental scaffold. AST chunking quality lift is NOT proven. Tree-sitter parser edge cases may exist. AST symbol extraction does not handle all symbol patterns (re-exports, aliased imports). No incremental update for AST index.**

## R9 findings

- **AST vs line persistent BM25 bakeoff completed on R2 fixture (28 tasks)**: `eval/ast_quality_bakeoff.py` runs both strategies through purge/build/search/score and produces a combined report with delta, quality gate, and safety checks.
- **AST improves SpanF0.5@10 (+0.025, latest run ~63% relative)** and FileRecall@1 (+0.143, 36% relative): AST-bounded chunks align better with logical code structures, producing more targeted evidence spans and better top-1 file retrieval.
- **AST regresses FileRecall@5 (−0.071 in the latest run)**: More granular AST chunks can dilute BM25 scores across multiple chunks per file, reducing the chance that any single chunk ranks a file into top-5. This is the quality gate failure.
- **AST reduces token waste (−0.022) and wrong_span_rate (−0.087 in the latest run)**: Narrower evidence spans waste fewer tokens and overlap gold spans more often.
- **Quality gate is false** (FileRecall@5 regression). **Safety checks all pass** (21/21). Citation_validity and structural_validity are 1.0 for both strategies.
- **Latency is comparable** (ratio ~1.0). Both strategies have similar per-query latency on this fixture.
- **AST remains experimental/opt-in; line remains default.** The fixture is too small and self-referential to generalise. A larger, diverse codebase eval would be needed for a definitive quality comparison.
- **Negative result is valid**: the bakeoff correctly captures a real trade-off between span precision (AST better) and broad file recall at k>1 (line more conservative).

## R10 findings

- **Incremental update works correctly**: dirty_index detects added/modified/deleted files; update_index applies batch changes (delete-by-term + re-add + commit + manifest file write via tmp+rename). Post-update status shows clean. 48/48 incremental smoke checks passed.
- **Dirty summary is accurate and safe**: distinguishes requires_update (file changes) from requires_rebuild (policy/schema/strategy mismatch or corrupt manifest). Policy-excluded added files do not dirty. Skipped entries (empty files, read errors) with unchanged sha are clean; skipped→nonempty is reported as modified (not added). Status never says clean if validate would fail.
- **Safety gates enforced on update**: missing manifest, policy hash mismatch, schema mismatch, and unrecognized chunk strategy all refuse update with clear error messages requiring rebuild. Manifest load failures are also caught gracefully.
- **Tantivy delete-by-term prevents duplicate docs**: `Term::from_field_text(path_field, path)` correctly removes all chunks for a path before re-adding. Deletes are tombstones until merge (documented, not a bug).
- **Context-lite dirty summary written to file**: R10 writes actual dirty index status to `.openlocus/context/dirty-summary.json`. The `ContextLitePack.dirty_summary` struct field remains `None` (the file is the surface, not the struct field).
- **Synthetic SLO benchmark (1000 files)**: latest run build_ms=147, dirty_status p50≈44ms/p95≈48ms, persistent_cli_search p95≈15ms, bench_warm open-once query p95=0ms, one-file update p50≈115ms/p95≈117ms (true modification each iteration), 0 invalid citations. Level0 synthetic only; not a general performance claim. `persistent_cli_search` is CLI-measured; `bench_warm` is the Rust CLI's internal open-once query timing over a synthetic dataset.
- **TDB deferred to R11**: R10 focused on incremental index; TDB moves to R11.
- **Not a single transaction**: Tantivy commit and manifest file write are separate; a crash between may leave a safe but inconsistent state requiring rebuild or re-update.

## R11 findings

- **TriviumDB 0.7.0 compiles and works as an optional dependency**: Feature-gated behind `tdb = ["dep:triviumdb"]`. Default build does not compile TDB. `cargo test --workspace` passes without TDB. `cargo test -p openlocus-store --features tdb` passes with 29/29 tests.
- **TdbChunkStore is a Level0 adapter probe**: Opens `Database<f32>` with `dim=1`, stores chunk metadata as JSON payloads (schema `tdb_chunk_v1`). The `[0.0]` vector is a smoke probe, NOT vector quality. Capabilities honestly report metadata+chunks only, no lexical/vector/graph.
- **Build discipline preserved**: validate_path, TOCTOU-safe sha, skip stale/traversal/empty — same as ConservativeChunkStore.
- **Marker-based purge safety**: Adapter writes an `.openlocus_marker` file; purge verifies marker before deletion and refuses without it.
- **Materialization conformance enforced**: TDB chunk records → StoreHit → materialize_evidence(). Stale, empty-sha, and invalid-range hits correctly rejected.
- **No default dependency on TDB**: TDB is NOT a default backend. It does not replace Tantivy persistent BM25 or the conservative store. Placeholder preserved.
- **No retrieval quality claim**: This is a Level0 wiring/persistence probe. No comparison against Tantivy BM25 or conservative store quality.

## R12 findings

- **Real-repo incremental update passes this Level0 sample**: On a temp copy of the OpenLocus repository (mixed Rust, Python, TypeScript, Markdown), incremental update correctly handles sampled modify, add, delete, rename, policy-excluded, and batch workloads. No stale VerifiedCurrent evidence produced.
- **All hard safety checks pass**: 149/149 hard safety checks pass (dirty detection, update success, clean after update, validate valid, collected marker-search citations invalid_count=0, no stale VerifiedCurrent for deleted/old paths).
- **Per-run unique markers avoid self-contamination**: Fixed markers appeared in copied docs/scripts causing false positives. Per-run suffixes (8-hex chars) and pre-build assert prevent this.
- **Positive gates use path+marker conjunction**: `evidence_has_path_and_marker` requires both path fragment AND marker in the cited excerpt of the same evidence item. Previous disjunction (path OR marker) could pass from unrelated evidence.
- **Citation validity maintained for collected marker-search evidence**: total_invalid_citations=0 across all workloads. Collected evidence validated through `openlocus citations validate` with validator returncode==0.
- **Latency comparison uses twin repo copies**: Both update and rebuild start from same state with same mutation applied. Incremental update ~42% faster on this sample. Gate is report-only; does not cause exit failure.
- **Growth is a catastrophic guard, not bounded proof**: 20 cycles observed growth ~1.11×; catastrophic guard passed (max(3×rebuild, rebuild+64MiB)). Does not prove long-term bounded growth.
- **Level0 one real-repo sample only**: OpenLocus temp copy is one data point. Not a general performance or robustness claim.

## Historical verification snapshot

This snapshot is preserved from the earlier local-first stages. It is not the
latest complete real-provider CI status; see the current-status section and the
L1/L2 reports above for recent remote-provider runs.

```text
Rust tests: 243 passed (193 existing + 50 new in openlocus-provider); 29 passed (store with --features tdb)
fmt: clean
clippy: clean with -D warnings (default and --features tdb)
CLI commands: read, scan, search regex/text/bm25/symbol, retrieve, fast-context, citations validate, context-lite, store status/build/purge, derived build/validate/inspect/purge, graph build/inspect, impact, tests, index build/status/dirty/validate/update/purge, search bm25 --index persistent (policy gate enforced), search symbol --mode regex|ast|auto, index build --chunk-strategy line|ast, bench warm (honest: open-once + real citation validation), provider status/audit, dense build/search/purge, version
Eval: regex/bm25/symbol/rrf on fixtures/r2.jsonl; storage_level0_smoke; derived_level0_safety (21/21 checks passed); graph_level0_smoke (21/21 checks passed); fast_context_level0_smoke (19/19 checks passed); persistent_index_smoke (32/32 checks passed, incl. policy/manifest gates + strict validation + honest bench); ast_chunking_smoke (40/40 checks passed); ast_quality_bakeoff (21/21 safety checks passed, quality_gate_passed=false due to FileRecall@5 regression); incremental_index_smoke (48/48 checks passed, incl. dirty summary + skipped empty file + file-level update + policy/schema/strategy gates + citation validation); synthetic_slo_bench (1000 files, build_ms, dirty p50/p95, persistent_cli_search p95, bench_warm open-once query p95, one-file update p50/p95, 0 invalid citations, Level0 synthetic only); real_repo_incremental_bench (modify/add/delete/rename/policy_exclude/batch/latency_compare/growth_cycles on OpenLocus temp copy, total_invalid_citations=0, no stale VerifiedCurrent violations, Level0 one real-repo sample only); provider_dense_safety (45/45 checks passed, incl. remote/outbound defaults, experimental gate, vector/audit no raw text, secret blocking, stale rejection, disabled/unknown provider audit events, query_sha not raw query, short file range, citation validity)
Structural validity: 1.0 across all methods
Citation validity: Python scorer reports 1.0 across methods (`path_range_only` unless Python blake3 is installed); Rust CLI citation validator confirmed current aggregated R2 evidence has `0` invalid citations with hash/range/excerpt checks
Remote dependency: none
TDB dependency: optional only (behind `tdb` feature; not in default build)
LLM dependency: none (rule extractor only)
Graph: deterministic, local-only, depth=1 only
Fast-context: 4-turn deterministic loop, EvidencePack output, ActionRecord replay, token budget, unknown channel gate, final citation validation, no LLM, remote_calls=0
Persistent index: r8-bm25-v2, mandatory manifest + policy gate enforced, validate_path per hit, empty sha skip, strict range no clamp, chunk_strategy line|ast, ast_stats in manifest, warm open=1ms p50=1ms, 32/32 R7 safety checks + 40/40 R8 AST safety checks + 48/48 R10 incremental safety checks
Incremental update: dirty summary (added/modified/deleted), skipped entries tracked (not falsely added), file-level update (--dirty, --path), manifest file write via tmp+rename (not single transaction with Tantivy commit), Tantivy delete-by-term, policy/schema/strategy mismatch + load failure refusal
TDB adapter: Level0 probe, feature-gated, dim=1 smoke, metadata+chunks only, marker-based purge, materialization conformance, no default dependency, no retrieval quality claim
Real-repo bench: Level0 one real-repo sample (OpenLocus temp copy), per-run unique markers avoid self-contamination, cited-excerpt path+marker conjunction gates, branch old/delete markers proven indexed before removal, sampled modify/add/delete/rename/policy_exclude/batch workloads pass, latency_compare uses twin repos (report-only gate), growth_cycles catastrophic guard (observed 20-cycle ~1.10×, does not prove long-term bounded), total_invalid_citations=0, citations_validator_ok=true, no stale VerifiedCurrent violations, sys.exit(1) on safety failure only
Provider/dense scaffold: MockEmbeddingProvider deterministic blake3 vectors dim=32, gate enforces data_level≤1 AND data_level≤metadata.max_data_level, secret scanning blocks SECRET/TOKEN/PASSWORD/API_KEY/sk_/ghp_/AKIA, audit uses query_embed/allow/block/provider_unavailable (not cache_hit), CLI uses query_sha/query_len (no raw query), short file end_line=min(total_lines,8), vector store has vectors but no raw text, audit has no raw text/vector/query, 45/45 safety checks, integration/safety only — not real semantic retrieval
R14 benchmark foundation: 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks (sanity), 48 labels, 47 hard negatives; fail-closed safety (runner/scorer isolation, isolated temp roots, isolated policy.toml from repo lock, unknown repo_id refusal, citation validity=1.0 via Rust validator, runtime canary retrieval, repo lock manifest re-verification); span-overlap hard_negative_hit_rate@10 + negative_nonempty_rate@10; R14-S is safety foundation, not quality conclusion; graph precision is future feature track
R15 external multi-repo expansion: 9 independent external repos (fast-context-mcp, grok2api, infinite-canvas, gemini-web2api, windsurf2api, kiro2, triviumdb, smartsearch, codex2api) across 5 languages (Rust, Python, Go, JS, TS); 166 medium tasks, 270 hard negatives; multi-language symbol extraction; absolute source paths; isolated roots with repo_id-specific allowlist source-file copying (no whole-repo copy, no symlinks/artifacts); runtime `.openlocus` traces cleaned/audited between queries; strict Rust citation validation before cleanup; exact/single repo_id-prefix scoring path matching; regex FileRecall@1=0.852, BM25 FileRecall@1=0.548; BM25 negative_nonempty_rate@10=0.645; 112/112 smoke checks passed; mined benchmark expansion, not quality conclusion
R16 multi-method quality bakeoff: cross-matrix bakeoff of regex/bm25/symbol/rrf across R14-S/R15-M/R15-stress; all safety gates passed (safety_passed=true, citation_validity=1.0, citation_hash_checked=true, canary_retrieval.passed=true); RRF wins R15-M recall (FileRecall@1 0.933, @5/10 0.993, MRR 0.959) but inherits BM25 negative_nonempty false positives (0.645 R15-M, 0.684 stress); symbol best span precision (0.310 SpanF0.5, 0.052 hard_neg, 0.000 neg_nonempty on R15-M); no method promoted to universal default; lexical/symbol/RRF only; no provider/dense/LLM claims; no remote calls
R17 query intent router / negative guard: eval-layer experiment; does NOT change Rust core; query_only_router_v0 eliminates R15-M negative_nonempty (0.645→0.000) with acceptable recall regression (FileRecall@1 0.904 vs 0.941); rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty with zero recall regression; R15-stress negative_nonempty reduces but not eliminated (0.158/0.474); citation safety inherited from validated source predictions; baseline prediction/report consistency checked; no LLM/dense claims; remote_calls=0
R18 threshold/guard calibration sweep: eval-layer sweep over 46 strategies with 8 thresholds on R15-M and R15-stress; train-selected rrf_guarded_by_symbol_regex preserves RRF recall on R15-M/holdout and drops medium negative_nonempty to 0.000, but remains weak on stress (0.474 vs symbol 0.105); separate query_noise_plus_rrf_agree_min strategies reach stress 0.000 as observations, not promotions; Pareto frontier computed; no core changes; no LLM/dense claims; remote_calls=0
R19 large/stress guard generalization: eval-layer generalization validation on R15-L (294 weak/mined tasks) and R15-stress; rrf_guarded_by_symbol_regex generalizes to R15-L (recall preserved, neg_nonempty 0.917→0.042) but fails stress (0.474 vs symbol 0.105); query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated (0.000); R15-L labels are weak/mined; generalization smoke only, not promotion evidence; promotion_ready=false always; no core changes; no LLM/dense claims; remote_calls=0
R25 graph+dense ablation: eval-layer ablation of graph_basic and dense_mock on R20 auto-wide (741 tasks); graph_basic net-negative (0 gold, 435 false spans → blocked); dense_mock net-negative (2 gold, 20,273 false → blocked); rrf_plus_graph dilutes RRF (FileRecall@1 0.693→0.497); rrf_plus_dense_mock dilutes (0.693→0.134); graph_pollution_ratio=0.0; citation validity remains 1.0 with graph/dense/composites revalidated and no_graph inherited from R21 after manifest verification; source-leak canary is regex-only with seeded self-test, not dense-path canary; QuIVer/TDB unavailable/not_measured; no Rust core changes; no LLM/dense real/QuIVer quality claims; remote_calls=0; promotion_ready=false
R26 auto-stress-1000: weak/mined/deterministic stress dataset for retrieval failure discovery; 1100 tasks across exact target counts for 10 stress categories (negative_nonexistent 150, ambiguous_vague 150, hard_distractor 200, semantic_trap 150, same_name_symbol 100, frontend_backend_confusion 75, test_source_confusion 75, generated_vendor_trap 50, stale_index_like 50, dense_quiver_specific_trap 100); 9 R20 repos; same external repo set as R20 plus some R20 task/label-derived queries; deterministic seed 42; no canary tokens; public tasks contain only test_id/repo_id/query/public_version/source; private labels carry category/risk/judgement fields; 19/19 fail-closed static validation checks passed including task/label query consistency, span path/range validity, and repo content manifest SHA lock recomputation; NOT promotion evidence; negative/abstain cases dominate (60%); no runner/scorer matrix yet; no Rust core changes; no LLM/dense claims; remote_calls=0

R28 promotion candidate report: conservative synthesis of R21/R23/R24/R25/R26 reports over R20/R26 failure-surface datasets with promotion_ready=false; current default should not change; best_recall_channel=rrf; best_precision_anchor=symbol; best_dense_candidate=none_available_for_default; quiver_recommendation=hold; graph/dense default expansion blocked; key blockers are R20 weak/mined labels, R26 deterministic/metamorphic/mined/stress labels with no retrieval matrix, R23 guard bucket regressions, QuIVer not implemented, dense real unavailable, and no broad human-verified stress tier
```

## R13 findings

- **Safe scaffold works**: All 45 safety checks pass. Remote is denied by default. Experimental opt-in is required. Secret scanning blocks token-like inputs. Audit contains no raw text or vectors. Vector store contains embedding vectors but no raw text/code snippet.
- **Mock provider is deterministic and normalized**: Same inputs always produce the same unit-length vector via blake3 hash. Different inputs produce different vectors. No network dependency.
- **Materialization gate is essential**: Dense search produces StoreHits which must be materialized through `materialize_evidence()`. Stale hits (content_sha mismatch) are correctly rejected.
- **Metadata-only views prevent code leakage**: Dense store builds views from path/language/basename/path-tokens only. No code snippets at data_level=0. Vector store and audit log do not contain raw code text.
- **Short file ranges are valid**: end_line=min(total_lines, 8) ensures materialize_evidence can verify ranges. Short files produce valid evidence.
- **Query text never leaks**: CLI JSON uses query_sha/query_len. Trace events use query_sha. Audit never stores raw query text. Blocked secret queries do not appear in traces.
- **Audit events use accurate names**: `query_embed` for query embedding, `allow`/`block`/`provider_unavailable` for decisions. Not `cache_hit` (no real cache behavior in R13). Cache key builder/stability only; no cache-hit behavior yet.
- **This is a safety scaffold only. No real semantic quality claim.** Mock vectors are deterministic blake3-based and do not capture semantic similarity. Dense mock search is integration/safety only.

## R14 findings

- **Scaled benchmark program established with fail-closed safety**: R14 defines S/M/L/X tiers. R14-S is populated with 4 logical repo groups from one OpenLocus workspace snapshot, 48 tasks, 48 labels, 47 hard negatives. Runner/scorer are strictly isolated. Citation validity must be 1.0.
- **Anti-leakage design is strictly enforced**: Public tasks contain no gold paths/lines. Labels are in separate private files with canary tokens. Path-component matching prevents false positives (e.g., 'openlocus-retrieval' does not match 'eval/'). Runtime canary retrieval is executed inside isolated benchmark roots.
- **Hard negatives are first-class with span-overlap metrics**: 47 hard negatives in R14-S. `hard_negative_hit_rate@10` requires span overlap unless a hard negative is explicitly file-level. `negative_nonempty_rate@10` measures false positive rate on negative tasks.
- **Citation validity is fail-closed, not a soft gate**: validity must be 1.0. No path-only fallback. Every citation must be hash+range+path valid.
- **Repo lock content manifest is verified by recomputation**: Normalized SHA-256 per file sorted. Mismatch = CRITICAL fail closed.
- **R14-S is a safety foundation, not a quality conclusion**: Validates the pipeline is fail-closed. Does not support quality claims.
- **Previous R14 graph precision is a future feature track**: Not the current R14 definition.
- **R14-M is partial; R14-L/X are not populated**: M uses the same 4 logical repo groups (target is 8+ independent repo groups/repositories). L/X require additional repos. Running --tier L or --tier X will fail with clear message.

## R15 findings

- **External multi-repo benchmark works with fail-closed safety**: 9 independent external repos across 5 languages (Rust, Python, Go, JavaScript, TypeScript), 166 medium-tier tasks, 270 hard negatives. Isolated roots allowlist-copy only manifest/source files under repo_id-specific folders; symlinks/artifacts are not copied. Unknown repo_id fail-closed. Canary retrieval zero hits.
- **Regex outperforms BM25 on exact-symbol queries**: FileRecall@1 is 0.852 (regex) vs 0.548 (bm25) on R15-M. This is because many tasks target exact symbol names where regex matches precisely. BM25 has high negative_nonempty_rate@10 (0.645 vs 0.000 for regex).
- **Hard negative hit rate is non-trivial (~0.23-0.29)**: Structurally plausible but incorrect results are common, as expected with mined hard negatives from the same repo. Hard-negative/gold span overlap is statically blocked.
- **Multi-language symbol extraction is functional but heuristic**: Rust/Python/Go/JS/TS regex-based patterns work for common cases. May miss unusual patterns (Go methods, Python decorators, JS arrows).
- **Anti-leakage holds across external repos**: 0 critical leakage issues. Absolute source path verification. Multi-language manifest verification. Task/label/manifest consistency checks. Canary tokens planted and runtime canary retrieval returns zero hits.
- **This is a mined benchmark expansion, not a quality conclusion.** Labels are mined with varying confidence; not human-verified. External local repos are workspace snapshots; not modified.

## R16 findings

- **Cross-matrix quality bakeoff across R14-S/R15-M/R15-stress**: eval/r16_quality_bakeoff.py runs all three matrices with four methods (regex, BM25, symbol, RRF), verifies safety gates, and produces aggregate report. All safety gates passed; citation_validity=1.0 across all methods/matrices; citation hash checked; canary retrieval passed; no remote calls.
- **RRF wins R15-M recall/MRR** (FileRecall@1 0.933, @5/10 0.993, MRR 0.959) but inherits BM25 negative false positive behavior (negative_nonempty@10 0.645 on R15-M, 0.684 on stress). Not safe as default for precision-sensitive tasks without negative gating or query intent routing.
- **Symbol has best span precision/hard-negative profile on R15-M** (SpanF0.5 0.310, hard_negative_hit_rate 0.052, negative_nonempty 0.000) but lower recall than RRF. Ideal as precision anchor, not sole retriever.
- **Regex strong on mined exact-symbol external tasks** (R15-M FileRecall@1 0.852, negative_nonempty 0.000) but reflects task distribution and exact-string bias, not a general natural-language conclusion.
- **BM25 strong in R14-S but weak and false-positive-heavy in R15-M/stress**: Needs query intent routing or threshold/negative guard.
- **No method promoted to universal default from R16**: Next research should be query intent router / negative guard / method fusion policy, not raw channel addition.
- **This is a lexical/symbol/RRF quality bakeoff. No provider/dense/LLM quality claims are made.**

## R17 findings

- **rrf_guarded_by_symbol_regex eliminates R15-M negative_nonempty with zero recall/MRR regression**: A simple evidence-presence guard that only returns RRF evidence when symbol or regex also found evidence perfectly filters R15-M negative tasks. This is the strongest result for a negative guard on R15-M.
- **query_only_router_v0 eliminates R15-M negative_nonempty with acceptable recall regression**: FileRecall@1 drops from 0.941 to 0.904 (delta -0.037), MRR from 0.963 to 0.918 (delta -0.044). SpanF0.5 improves from 0.253 to 0.315. The router uses noise marker detection, compound snake_case fabrication detection, and vague multi-word query detection.
- **R15-stress negative_nonempty reduces but is not eliminated**: query_only_router_v0 drops from 0.684 to 0.158; rrf_guarded drops to 0.474. Common-word queries where regex still returns false positives prevent full elimination.
- **task_type_assisted_router is an upper-bound reference**: Uses benchmark metadata (task_type) not available at runtime. Achieves 0.258 on R15-M and 0.316 on R15-stress.
- **No core default promotion**: R15-stress negative_nonempty remains above 0 for all strategies. Both R15-M and R15-stress negative_nonempty must improve without unacceptable recall/MRR regression before any core default change.
- **Eval-layer research only; does NOT change Rust core. No LLM/dense claims.**

## R18 findings

- **Train-selected candidate is useful but not stress-safe**: `rrf_guarded_by_symbol_regex` preserves RRF FileRecall@1/MRR on full R15-M (0.941/0.963) and holdout (0.844/0.900), while reducing medium negative_nonempty to 0.000. Stress remains weak: 0.474 negative_nonempty versus symbol 0.105.
- **The query noise guard is the key differentiator for stress**: rrf_guarded_by_symbol_regex alone leaves stress at 0.474 because regex returns false positives for common-word stress queries. The query noise guard identifies these as vague/noise and routes to empty.
- **Stress-zero strategies are observations, not promotions**: `query_noise_plus_rrf_agree_min` variants reach 0.000 stress negative_nonempty on the 19-task stress set, but this is too small and mined to justify default promotion.
- **Threshold sweep reveals sharp recall cliff at 0.05**: Most RRF top scores are either very high or very low; thresholds above 0.03 reject nearly all evidence.
- **Pareto frontier on R15-M shows recall vs hard-negative trade-off**: symbol (0.052 hard_neg, 0.807 recall) vs rrf_guarded (0.259 hard_neg, 0.941 recall) vs query_only_router_v0 (0.237 hard_neg, 0.904 recall).
- **No core default promotion in R18**: Threshold/guard choices are calibrated on mined R15 data and require larger/human-verified validation before promotion.
- **Eval-layer calibration only; does NOT change Rust core. No LLM/dense claims.**

## R19 findings

- **rrf_guarded_by_symbol_regex generalizes to R15-L**: FileRecall@1 preserved (0.911 vs RRF 0.911), negative_nonempty drops from 0.917 to 0.042. R15-L labels are weak/mined; generalization smoke only.
- **rrf_guarded fails stress**: Stress negative_nonempty is 0.474, above symbol baseline 0.105. The selected candidate does NOT improve stress beyond symbol. Query noise guard is needed.
- **query_noise_plus_rrf_agree_min_0.0 stress-zero observation repeated**: Achieves 0.000 stress negative_nonempty and 0.000 R15-L negative_nonempty. R15-L FileRecall@1 is 0.904 (delta -0.007 vs RRF). Observation, not promotion.
- **R15-L labels are weak/mined (270 mined, 24 weak)**: Generalization smoke only, not promotion evidence. R15-stress has only 19 tasks.
- **No core default promotion from R19**: promotion_ready is always false. Requires human-verified labels and larger stress dataset.
- **Eval-layer generalization validation only; does NOT change Rust core. No LLM/dense claims.**

## R20 findings

- **Failure-surface dataset generation works**: 741 tasks across 25 required categories and 9 R15 repos, with deterministic generation from fixed seed=42.
- **Public/private separation is clean**: Public tasks contain only task_id, repo_id, query, public_version, source_tier. No gold/expected/oracle/risk/judgement fields leak. All judgement fields are in separate private labels.
- **Category coverage is complete**: All 25 required categories have >= 5 tasks. positive_exact_symbol (180) and positive_regex_anchor (90) dominate due to per-repo symbol extraction.
- **Label quality distribution**: mined_high_confidence: 315, mined: 168, weak: 258. No human_reviewed (forbidden in R20).
- **Expected behavior distribution**: primary_evidence: 374, abstain: 177, weak_candidates: 90, no_primary: 45, supporting_only: 55.
- **Oracle type distribution**: deterministic: 438, stress: 148, mined: 110, metamorphic: 36, differential: 9.
- **Static validation passes all 14 check categories**: no private field leaks, task/label ID bijection, enum validity, required label schema, gold_span consistency, overlap constraints, span path/range validation, manifest SHA verification, coverage minimums, dataset manifest flags.
- **Metamorphic/stress categories** (dirty_overlay, deleted_file, renamed_file, branch_switch_like) encode expected behavior for R21/R26 but do NOT mutate source in R20.
- **R20 labels are failure-surface oracle/probe labels, not EvidenceCore.**
- **R20 is a failure-surface dataset, NOT promotion evidence.** No runner/scorer matrix exists yet; R21 will use this data.
- **Dataset + static validator only; no Rust core changes.**

## R22/R27 findings

- **Failure attribution is analysis-only**: Consumes R21 artifacts and R20 labels without re-running retrieval. 13 failure clusters computed from cross-strategy comparison heuristics.
- **RRF_INHERITED_BM25_FALSE_POSITIVE is the largest actionable cluster (110 tasks)**: BM25 and RRF both return false primary evidence on no-gold tasks. RRF inherits BM25's broad lexical matching without a negative gate.
- **GUARD_RECALL_KILL affects 67 positive tasks**: rrf_guarded_by_symbol kills recall when symbol returns empty on natural-language/vague queries but RRF finds gold. Per-guard: symbol=67 kills, regex=0, symbol_regex=0, query_noise=0.
- **SYMBOL_EXTRACTION_MISS affects 91 positive tasks**: Regex/RRF find gold but heuristic symbol extraction misses due to non-standard definition patterns.
- **REGEX_NORMALIZATION_BUG affects 1 task**: Curly braces in route-style queries cause Rust regex parse errors.
- **62 BENCHMARK_ORACLE_SUSPECT tasks**: Weak-quality labels where strategies strongly disagree with the oracle, suggesting label (not strategy) error.
- **Unrun strategy clusters have count=0**: Dense, TDB/QuIVer, graph, AST strategies not evaluated in R21. No fabricated data. recommended_next_tests provided for each.
- **EVIDENCECORE_REJECTION clusters have metric_unavailable=true**: R21 shows rate=0.0 for all strategies; no rejection data to analyze.
- **206 bucket regressions detected**: Multiple strategies exceed thresholds in specific buckets. promotion_blocked_by_bucket_regression=true.
- **promotion_ready=false. not_promotion_evidence=true. No Rust core changes. No LLM/dense claims.**

## R23 findings

- **Guard parameter sweep is analysis-only**: Consumes R21 artifacts and R20 labels without re-running retrieval. 51 strategies across 8 guard parameter dimensions plus 15 combined strategies.
- **All 51 strategies have bucket regressions**: Every guard strategy has at least one bucket where recall gap vs RRF >0.15, no_gold_nonempty_rate >0.3, primary_false_positive_rate >0.3, or guard_recall_kill_rate >0.1.
- **Combined query_noise + agreement is the best R23 guard balance**: query_noise_1_plus_regex_or_symbol_agree achieves no_gold_nonempty_rate 0.221 (vs RRF 0.495) with FileRecall@1 0.693 preserved and zero guard_recall_kill.
- **Agreement guards reduce false positives without recall cost**: regex_or_symbol_agreement_required reduces no_gold_nonempty_rate from 0.495 to 0.279 with zero guard_recall_kill and preserved FileRecall@1.
- **RRF score threshold above 0.02 causes sharp recall cliff**: Most RRF top scores are concentrated near 0.03-0.06.
- **top1_top2_gap threshold kills too much recall**: Even gap=0.005 causes >50% guard_recall_kill_rate.
- **Symbol agreement alone kills 22.8% recall**: Confirms R22 finding.
- **No strategy eliminates no_gold_nonempty_rate to zero without unacceptable recall loss**: Strategies achieving near-zero false positives do so by abstaining on >99% of queries.
- **Curves computed**: risk_coverage_curve, recall_vs_negative_curve, recall_vs_false_primary_curve, precision_vs_abstain_curve.
- **6877 total bucket regressions across 51 strategies**: Expected given R20 label diversity and now includes bucket-level guard_recall_kill regressions.
- **promotion_ready=false. not_promotion_evidence=true. No Rust core changes. No LLM/dense claims.**

## R24 findings

- **QuIVer is not implemented**: Scan of all Rust crates, Cargo.toml files, and source code confirms no QuIVer implementation exists outside eval/docs placeholders. quiver_implemented=false. All R24.1 diagnostic fields (BQ_overlap, quiver recall, quiver precision, quiver MRR, quiver F0.5) report unavailable/not_measured with reason quiver_not_implemented and explicit next_required_tests. No numeric 0 is output as a quality result.
- **TDB is a placeholder in default build**: `openlocus store status tdb --json` returns available=false, success=false, mode=placeholder. TDB is a feature-gated metadata/chunk store, not an ANN/QuIVer backend. tdb_stale_leak_count is not_applicable.
- **Dense mock is available as a candidate-channel safety smoke**: mock and disabled providers are available; real provider is unavailable. Dense mock uses deterministic blake3-based vectors that do NOT capture semantic similarity.
- **Dense mock produces real, materialized candidates but mostly exposes noise**: full run produced 5,264 dense_mock candidates, all Rust citation-valid. Quality is poor as expected for non-semantic mock vectors: FileRecall@1 0.024, MRR 0.073, SpanF0.5 ~0.000, token_waste 0.850, primary_false_positive_rate 0.878.
- **Dense CLI rejection and canary behavior are explicit**: full run recorded 99 candidate rejections (`candidate_rejection_rate` 0.134). Canary hardening checked 8 non-empty dense stores, skipped 1 empty store, returned 66 path-canary evidence items and 132 query-canary evidence items, with raw canary/query leakage 0.
- **Dense mock + RRF fusion amplifies noise**: fusion confirms dense contribution (642 tasks, 5,264 dense spans retained) but increases false-primary/noise: FileRecall@1 0.134, MRR 0.451, token_waste 0.928, primary_false_positive_rate 0.923, hard_distractor_hit_rate 0.215. This is a failure-surface probe, not a recommended strategy.
- **Citation validity is enforced**: Dense evidence and dense+RRF fusion evidence both pass Rust citation validation (hash+range+path) before cleanup. dense_mock citation_total=5,264; fusion citation_total=13,149; invalid=0.
- **R24 is NOT a QuIVer bakeoff**: It is an availability + mock dense candidate-channel probe + TDB placeholder status check. QuIVer remains future work.
- **No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0.**

## R25 findings

- **graph_basic is net-negative on R20 auto-wide**: Added 0 gold spans and 435 false spans. Depth=1 graph impact from top path (derived via symbol→regex fallback) introduces evidence from related files that are not in gold, without recovering any gold spans RRF missed. Default expansion blocked by added_false_span > added_gold_span rule.
- **dense_mock is net-negative as expected**: Added 2 gold spans and 20,273 false spans. Non-semantic blake3-based mock vectors produce massive noise. The 2 gold hits are likely coincidental proximity. Default expansion blocked.
- **rrf_plus_graph dilutes RRF quality**: FileRecall@1 drops from 0.693 to 0.497. Graph evidence competes with RRF evidence in RRF score calculation, pushing relevant RRF hits down in ranking.
- **rrf_plus_dense_mock also dilutes RRF quality**: FileRecall@1 drops from 0.693 to 0.134. Dense mock evidence floods the RRF pool with irrelevant candidates.
- **Graph pollution is zero**: No graph evidence returned on forbidden paths (graph_pollution_ratio=0.000).
- **Graph has low token waste when it fires** (0.310 vs 0.779 baseline) but mostly abstains (0.785 abstain rate).
- **Graph path derivation stats**: symbol=358/741 (48.3%), regex=156/741 (21.1%), none=2222/2241 (30.6%). Impact returns empty evidence for 355/514 tasks with a top path (no graph edges found).
- **Combined strategies show additive noise**: rrf_plus_dense_mock_plus_graph accumulates both graph (435) and dense (20,273) false spans (20,695 total).
- **Citation validity remains 1.0**: graph_basic, dense_mock, and composite strategies are revalidated in R25 with Rust hash/range/path citation validation. no_graph inherits R21 validation after R25 verifies the R21 artifact manifest before baseline use.
- **QuIVer/TDB honestly reported as unavailable/not_measured**: No numeric zero quality results for QuIVer. TDB not applicable.
- **R25 is an eval-layer ablation study; does NOT change Rust core. No LLM/dense real/QuIVer quality claims. remote_calls=0. promotion_ready=false. not_promotion_evidence=true.**

## R29 findings

- **16-strategy matrix on R26 auto-stress (1100 tasks) is a failure-surface probe**: eval/r29_r26_stress_matrix.py runs base (regex/bm25/symbol/rrf), composite/guard (bm25_regex, bm25_symbol, rrf_guarded_by_symbol/regex/symbol_regex, query_noise_plus_rrf_agree_min), and R24/R25-style (dense_mock, dense_mock_plus_rrf, graph_basic, rrf_plus_graph, rrf_plus_dense_mock, rrf_plus_dense_mock_plus_graph) strategies. Strictly separated RUN/SCORE phases. R26 provenance validated before run. Citation validity must be 1.0 for all strategies. 14 required failure clusters computed. Span contribution analysis for graph/dense/composites vs fresh RRF baseline. Bucket regressions across source_category/expected_behavior/oracle_type/repo_id/risk_tags.
- **5 unavailable strategies report reason only**: dense_real_if_available (not_configured_or_policy_disabled), tdb_quiver_if_available (quiver_not_implemented), tdb_quiver_plus_rrf (quiver_not_implemented), tdb_quiver_guarded_by_symbol_regex (quiver_not_implemented), fast_context_if_available (fast_context_is_4turn_orchestration_scaffold_not_standalone_matrix_strategy). No fake numeric quality.
- **No skip-run**: Fresh run always required. Canary/citation validation cannot be bypassed.
- **Private field scan enforced**: Prediction/evidence/rejection/trace JSONL must not include source_category, risk_public, intent_guess, risk_tags, oracle_type, expected_behavior, gold_spans, hard_distractors, must_not_primary, why_this_is_hard, which_strategy_it_targets.
- **R26 labels are weak/mined/deterministic/stress**: Not human-verified. This is failure-surface only, not promotion evidence.
- **dense_mock is candidate-channel safety smoke, not semantic quality**: Mock vectors are deterministic blake3-based and do not capture semantic similarity.
- **graph_basic is deterministic depth=1**: Not precise call/type graph.
- **QuIVer not implemented; TDB unavailable**: No fabricated numeric quality.
- **promotion_ready=false. not_promotion_evidence=true. No Rust core changes. No LLM/dense real/QuIVer quality claims. remote_calls=0.**
- **Full R29 run completed with safety gates passed**: 1100 tasks, 16 implemented strategies, 64 artifact files verified, artifact private-field/canary scans clean, all implemented strategies have citation_validity=1.0.
- **RRF remains strongest recall but unsafe alone**: FileRecall@1=0.803, FileRecall@5=0.923, MRR=0.858, primary_false_positive_rate=0.453.
- **`query_noise_plus_rrf_agree_min` stress result is promising but still not promotion**: FileRecall@1=0.803, FileRecall@5=0.923, primary_false_positive_rate=0.106, guard_recall_kill_rate=0.003. R23 bucket-regression evidence still blocks promotion.
- **Symbol remains the precision anchor**: SpanF0.5=0.291, primary_false_positive_rate=0.080, token_waste=0.247, but abstain_rate=0.671.
- **Dense mock and dense+RRF are net-negative failure surfaces**: dense_mock primary_false_positive_rate=0.874; dense_mock_plus_rrf/rrf_plus_dense_mock primary_false_positive_rate=0.906.
- **Graph remains default-blocked**: graph_basic added_gold_span=0 and added_false_span=437; all graph/dense expansion variants are blocked by added_false_span > added_gold_span.
- **Failure clusters surfaced at scale**: DENSE_MOCK_NOISE=577, RRF_INHERITED_BM25_FALSE_POSITIVE=299, DENSE_SEMANTIC_TRAP_FALSE_POSITIVE=219, GRAPH_ADDS_NO_GOLD=90, GUARD_RECALL_KILL=62. Bucket regressions total=448.

## BEA-0 findings

- **BEA-0 是首个真正算法级检索/采集实验**：对全新有界 ContextBench
  verified Python 行（默认 10；硬上限 20）和 RepoQA Python needle
  （默认 5；硬上限 10）重新运行多方法检索（bm25/regex/symbol + 可选
  rrf），运行确定性 `bea_v0_budgeted` 策略（在证据预算下，默认 10；硬
  上限 20），并计算 per-arm 聚合指标，含相对 `bm25_top10`（启用 rrf 时
  还包括 `rrf_bm25_regex_symbol_top10`）的 baseline-vs-treatment
  delta。非 replay、非 aggregate 验证 — 真正 fresh retrieval + 采集
  循环。
- **BEA v0 策略 runtime-clean 且确定**：只消费 method source、候选 rank、
  score/normalized score、跨 method 的 rank agreement、重复 path/span
  overlap、候选总数、已接受覆盖、剩余预算、廉价 path extension。在合成
  gold/label/row-id/model-family/previous-outcome 污染下验证 invariance
  （策略产生 IDENTICAL 的 accepted/action_trace/budget_states，因为忽略
  这些字段）。初始 action：`accept_candidate`、`skip_low_support`、
  `rerank_by_agreement`、`stop_budget_exhausted`；可选
  `expand_same_file` 用于在预算下保留 deferred 同文件候选。
- **私有 per-record SCORE JSONL 保留于 /tmp**：每条 evaluated record 都
  有一条私有 SCORE 行，含 phase_run_id、benchmark、private record id、
  runtime query feature summary、candidate list（method、rank、score、
  normalized_score、path、span、content_sha、extension、agreement）、
  action trace、budget states、accepted/final candidate、score outcome
  （per-arm 指标）、latency_ms、cost_usd=0.0、tokens=0、provider_calls=0、
  failure_reason。私有 SCORE 路径绝不序列化到公开 artifact、docs 或 CI
  artifact。公开 artifact 仅记录聚合 SCORE manifest 字段
  （records_written、record_count、schema_version、manifest_hash、
  storage_class、path_publicly_serialized=false）。
- **手动 CI run `27934507148`（2026-06-21）**：ContextBench 2 行 + RepoQA 1 needle，
  budget=5，方法 bm25/regex/symbol，必需并启用 rrf baseline。3 条记录全部成功。
  Treatment `bea_v0_budgeted` 与两条 baseline 持平 file_recall@10 / mrr
  / success_rate，同时使用约一半 evidence budget
  （`evidence_budget_used=3.33` vs `6.67`），并将 `span_f0.5@10` 提升
  `+0.028`、`quality_per_candidate` 提升 `+0.0014`。3 行私有 per-record
  SCORE 写入
  `/tmp/bea0_private_score_<pid>_<ts>/bea0.private.jsonl`。
- **严格 claim 边界**：BEA-0 输出 `claim_level =
  bea_v0_budgeted_acquisition_smoke_only`。不是 benchmark 结果、不是
  leaderboard 条目、不是性能声明、不是 method-winner 声明、不是
  calibration 声明、不是 promotion、不是 default 变更、不是
  runtime/retriever/pack/backend/EvidenceCore 语义变更、不是 downstream
  agent 价值声明。不输出 `winner`、`best_method`、`recommended_default`、
  `method_winner`、`calibration`。所有 no-claim / no-runtime-change flag
  为 false；`aggregate_only_public_artifact=true`、
  `diagnostic_only=true`、`provider_calls=0`。
- **212/212 self-test 检查通过**：26 组覆盖身份字段、safe true flag、
  no-claim false flag、license 字段、私有 SCORE manifest aggregate-only
  字段、row/needle/budget 硬上限、method 校验、path extension helper、
  BEA v0 策略机制（接受非空；首个接受为高 agreement；跳过 low_support；
  budget state 跟踪 budget_remaining；尊重预算上限）、runtime-clean
  invariance、per-arm 指标 + delta、聚合均值、arm 指标 allowlist 过滤、
  failure category count enum、unavailable 状态、扫描器拒绝 BEA-0 专属
  禁止 key（private_score_path、action_trace、budget_states、
  accepted_candidates、final_candidates、candidate_list、score_outcome 等）
  和 value 模式（repo URL/slug/commit SHA/file path/tmp path/multiline）、
  扫描器允许 safe value（schema_version、methods、budget、arm_metric_records、
  delta_records、private_score_manifest_hash、failure_category）、fail-closed 生成
  （干净报告不 raise；private_score_path raise；action_trace raise；
  accepted_candidates raise；winner raise；best_method raise；self-test 失败
  拒绝 artifact 生成）、CLI 表面、私有 SCORE writer round-trip、
  aggregate runtime seconds 存在、任何位置无
  winner/best_method/recommended_default/method_winner/calibration。
- **CI 为手动 opt-in `workflow_dispatch`**，带
  `enable_external_benchmark_network=true`。默认禁用网络。启用时
  fail-closed：要求 status 在（`bea_v0_smoke_pass`、`partial`）中、
  `records_successful > 0`、`forbidden_scan.status=pass`、
  `provider_calls=0`、`private_score_record_count == records_successful`，
  任何位置无 `winner`/`best_method`/`recommended_default`/`method_winner`/
  `calibration` 字段，任何位置无 BEA-0 私有字段（`private_score_path`、
  `action_trace`、`budget_states`、`accepted_candidates`、
  `final_candidates`、`candidate_list`、`score_outcome` 等）。仅上传
  aggregate 公开报告；绝不上传私有 SCORE JSONL。
- **BEA-0 不是 C3**：C3 仅 replay，从预计算 P21 outcomes 中选择；BEA-0
  真正重新运行检索，并在预算下采集证据，附带私有 per-record SCORE 轨迹。
  C3 -> BEA-0 是从仅 replay 到真正采集的转向。

## BEA-1 findings

- **BEA-1 是首个机制消融 smoke**：对全新有界 ContextBench verified
  Python 行（默认 5；硬上限 20）和 RepoQA Python needle（默认 3；硬上限
  10）重新运行多方法检索（bm25/regex/symbol + 可选 rrf），运行 5 个固定
  arm（`bm25_top10`、`bea_v0_budgeted`、`same_budget_bm25_prefix`、
  `agreement_only_same_budget`、`seeded_random_same_budget`；启用 rrf 时还
  包括 `rrf_bm25_regex_symbol_top10`），并计算 per-arm metric records、
  baseline-vs-treatment delta records，以及机制对比 records（在 paired
  denominator 上）。非聚合校验；真正 fresh retrieval + 3 个同预算控制 +
  机制对比。
- **Same-budget K 确切**：
  `K = min(len(bea_v0_budgeted.accepted_candidates), available_deduped_candidate_count)`。
  若 BEA 对某条记录接受零候选，同预算控制也选择零。公开产物绝不序列化
  accepted candidates 或 candidate lists。
- **同预算控制 runtime-clean 且确定**：`same_budget_bm25_prefix` 取去重
  后前 K 个 BM25 候选；`agreement_only_same_budget` 按
  （agreement desc, min_rank asc, max_normalized_score desc, stable order）
  排序与 BEA 相同的去重宇宙；`seeded_random_same_budget` 在稳定排序后的
  去重宇宙上使用固定公开种子 `20240621`。种子或排序中无
  gold/labels/row IDs/provider/model 字段。在合成 gold/label/row-id 污染下
  验证 invariance。
- **Paired denominator 规则**：机制对比仅包含 baseline 和 treatment arm
  在同一记录上均有有效指标的记录。每条 `mechanism_contrast_records` 行含
  `record_count`，以便 delta 可解释。公开产物不序列化 per-record
  inclusion masks。
- **手动 CI run `27936497544`（2026-06-21）**：ContextBench 5 行 + RepoQA 3 needle，
  budget=5，方法 bm25/regex/symbol，必需并启用 rrf baseline。8 条记录全部成功；
  `paired_exclusion_count=0`。BEA v0 与 `same_budget_bm25_prefix` 和
  `agreement_only_same_budget` 在 file_recall@10/mrr/span_f0.5@10/
  success_rate 上持平，且 `evidence_budget_used=3.125` 相同；BEA v0 以
  `delta(mrr)=+0.09375` 胜过 `seeded_random_same_budget`。8 行私有
  per-record SCORE 写入
  `/tmp/bea0_private_score_<pid>_<ts>/bea1.private.jsonl`。
- **严格 claim 边界**：BEA-1 输出 `claim_level =
  bea_v0_mechanism_ablation_smoke_only`。不是 benchmark 结果、不是
  leaderboard 条目、不是性能声明、不是 method-winner 声明、不是
  calibration 声明、不是 promotion、不是 default 变更、不是
  runtime/retriever/pack/backend/EvidenceCore 语义变更、不是 downstream
  agent 价值声明。不输出 `winner`、`best_method`、`recommended_default`、
  `method_winner`、`calibration`。所有 no-claim / no-runtime-change flag
  为 false；`aggregate_only_public_artifact=true`、
  `diagnostic_only=true`、`provider_calls=0`。
- **420/420 self-test 检查通过**：28 组覆盖身份字段、safe true flag、
  no-claim false flag、license 字段、私有 SCORE manifest aggregate-only
  字段、row/needle/budget 硬上限、method 校验、same-budget K 确切、三个
  同预算控制 arm 算法、runtime-clean invariance、arm_metric_records 固定
  形态、delta_records 固定形态、mechanism_contrast_records 固定形态 +
  record_count、failure category count enum、unavailable 状态、扫描器拒绝
  BEA-0 + BEA-1 禁止 key 和 value 模式、扫描器允许 safe value、
  fail-closed 生成、CLI 表面、私有 SCORE writer round-trip、paired
  denominator 规则、aggregate runtime seconds 存在、任何位置无
  winner/best_method/recommended_default/method_winner/calibration、固定
  arm 存在、扫描器拒绝 BEA-1 专属 claim 边界 key（calibration、
  method_winner 等）。
- **CI 为手动 opt-in `workflow_dispatch`**，带
  `enable_external_benchmark_network=true`。默认禁用网络。启用时
  fail-closed：要求 status 在（`bea1_mechanism_ablation_pass`、`partial`）
  中、`records_successful >= 3`、每条机制对比 `record_count >= 3`、
  `forbidden_scan.status=pass`、`provider_calls=0`、`private_score_manifest`
  存在且 `path_publicly_serialized=false` 且
  `record_count == records_successful`，任何位置无
  `winner`/`best_method`/`recommended_default`/`method_winner`/`calibration`
  字段，任何位置无 BEA-1 私有字段。仅上传 aggregate 公开报告；绝不上传
  私有 SCORE JSONL。
- **BEA-1 不是 BEA-0**：BEA-0 度量 BEA v0 vs `bm25_top10`（以及启用 rrf
  时 `rrf_bm25_regex_symbol_top10`）；BEA-1 度量 BEA v0 vs 三个同预算
  控制，这些控制隔离 BEA-0 的增益（若有）是否来自多源 agreement / 序贯
  预算采集而非仅仅是读取更少候选。BEA-1 不 bootstrap BEA-0 聚合 artifact；
  它重新运行 fresh external retrieval。

## BEA-2 findings

- **BEA-2 是 policy v0.2 diversity/risk 机制消融 smoke**：实现真正算法
  策略变更（BEA v0.2），含冻结优先级权重（agreement=0.30、bm25_norm=0.20、
  diversity=0.20、query_path_overlap=0.15、risk_penalty=-0.25、
  duplication_penalty=-0.30），在全新 heldout ContextBench verified Python
  行（offset 40）+ RepoQA Python needle（offset 20）上运行。v0.2 在结构上
  与 v0 和 agreement-only 不同：按优先级降序贪心选择，含
  diversity/risk/duplication-aware 重计算。
- **手动 CI run `27938484585`（2026-06-21）**：手动 CI run `27938484585`（2026-06-21）已通过：ContextBench offset 40 limit 20 + RepoQA offset 20 limit 10，budget=5，方法 bm25/regex/symbol，启用 RRF baseline。30 条记录成功；`paired_exclusion_count=0`；forbidden scan pass；`provider_calls=0`；`private_score_manifest.record_count=180`（30 条记录 × 6 arm）；`private_score_manifest.storage_class=tmp_private`；`private_score_manifest.path_publicly_serialized=false`；`aggregate_runtime_seconds=386.3`。BEA v0.2 相对 BEA v0 / same-budget BM25 / agreement-only / RRF：`file_recall@10` delta=+0.033334，`mrr` delta=+0.081667，`span_f0.5@10` delta=-0.012947，`success_rate` delta=+0.033334，`latency_seconds` delta=+8.188547，`evidence_budget_used` delta=0.0。Win/tie/loss（v0.2 vs v0，n=30）：file_recall@10 win=3 tie=25 loss=2；mrr win=7 tie=21 loss=2；span_f0.5@10 win=0 tie=28 loss=2；success_rate win=3 tie=25 loss=2。相对 seeded random，v0.2 的正向 delta 更强（`file_recall@10` +0.233334，`mrr` +0.326667，`span_f0.5@10` +0.019687，`success_rate` +0.233334）。这是 mixed smoke-level 机制结果，不是 method-winner/default/performance/calibration 声明。
- **321/321 self-test 检查通过**：31 组。
- **严格 claim 边界**：`claim_level=bea_v02_policy_smoke_only`。非
  benchmark/leaderboard/performance/method-winner/calibration/promotion/
  default/runtime/EvidenceCore/downstream-value。`provider_calls=0`。
- **BEA-2 不修改 BEA-0/BEA-1**：独立 phase、独立评估器、独立 artifact。
  BEA-0/BEA-1 语义不变。

## BEA-3 findings

- **BEA-3 实现冻结 BEA v0.3 anchor/span/latency-aware 策略**：为
  BM25/agreement anchor 预留 anchor slot，对剩余预算应用
  diversity/risk 评分，添加 runtime-clean span/latency 代理。冻结权重
  不从 outcomes 调优。消融：v0_3_no_anchor、v0_3_no_early_stop。
- **手动 CI run `27942492278`（2026-06-21）**：30 条记录（ContextBench 20 + RepoQA 10），budget=5，9 arm，270 行私有 SCORE。v0.3 相对 v0.2：file_recall@10 delta=0.0，mrr delta=0.0，span_f0.5@10 delta=+0.00217，success_rate delta=0.0，latency_seconds delta=+0.001098，quality_per_latency delta=+0.000292。相对 v0.2 的 win/tie/loss：file/MRR/success 均为 0/30/0，span 为 1/29/0。v0.3 与 v0.2 基本持平，只出现极小的 span/quality-per-latency 信号。
- **225/225 self-test 检查通过**：30 组。
- **严格 claim 边界**：`claim_level=bea_v03_policy_smoke_only`。
  非 benchmark/leaderboard/performance/method-winner/calibration/promotion/
  default/runtime/EvidenceCore/downstream-value。`provider_calls=0`。
- **BEA-3 不修改 BEA-0/BEA-1/BEA-2**：独立 phase、评估器、artifact。
- **新指标**：`quality_per_latency` = span_f0.5@10 / latency_seconds。
- **新 record 类型**：`mechanism_summary_records`。
- **延迟归因修复**：所有 arm 共享候选收集延迟（公平归因）。

## BEA-4 findings

- **BEA-4 是冻结 BEA v0.3 策略的 external scale smoke**：手动 CI run
  `27957586271` 在更大全新 external 切片上通过（ContextBench verified Python
  行 offset 80 limit 80 + RepoQA Python needle offset 40 limit 40），7 个固定
  arm（无消融；v0.3 + v0.2 + v0 + bm25_prefix + agreement_only + rrf +
  seeded_random）。v0.3 算法/权重与 BEA-3 完全一致（冻结；
  `algorithm_changed_during_bea4=false`、`weights_tuned_during_bea4=false`）。
- **Scale 结果**：120 条记录成功（ContextBench 80 + RepoQA 40），
  `private_score_manifest.record_count=840`（120×7 arm），`network_calls=3`，
  `provider_calls=0`，forbidden scan pass，aggregate runtime 864.538s。
- **BEA v0.3 指标**：ContextBench file_recall@10=0.225，mrr=0.151875，
  span_f0.5@10=0.013607，success_rate=0.225；RepoQA file_recall@10=0.575，
  mrr=0.402917，span_f0.5@10=0.044761，success_rate=0.575。
- **Deltas mixed**：vs BEA v0.2，v0.3 在 file_recall/MRR/success 上持平，
  span 略低（-0.000075），latency 微增（+0.000831s）。vs BEA v0 / same-budget
  BM25 / agreement-only / RRF，v0.3 的 file_recall +0.108334，MRR +0.076945，
  span +0.001333，success +0.108334；vs seeded random 的 file_recall +0.175，
  MRR +0.139028，span +0.020195，success +0.175。Latency 与
  quality-per-latency trade-off 仍 mixed，尤其 vs RRF。
- **公开 artifact 为 records-only**：`benchmark_arm_metric_records`、
  `delta_records`、`win_tie_loss_records`、`worst_slice_records`（70 条聚合记录，
  7 个固定 bucket 标签）、`mechanism_summary_records`、aggregate-only
  `private_score_manifest`。无 row IDs、repos、paths、commits、queries、labels、
  candidate lists、gold/source snippets 或 private SCORE paths。
- **严格 claim 边界**：`claim_level=bea_v03_external_scale_smoke_only`。
  非 benchmark/leaderboard/performance/method-winner/calibration/promotion/
  default/runtime/EvidenceCore/downstream-value。`provider_calls=0`。
- **BEA-4 不修改 BEA-0/BEA-1/BEA-2/BEA-3**：独立 phase、评估器、artifact；
  v0.3 冻结。

## BEA-5 findings

- **BEA-5 已作为固定协议 No-Go / near-miss 完成**：最终 CI run
  `28003522632` 以 `records_successful=119` fail-closed，比预声明的
  120-record quota 少 1 条。本地 exact-protocol rerun 复现了 aggregate
  artifact。
- **固定协议**：success-quota scan over full available Python frame，排除
  BEA-2/3/4 窗口；raw caps 为 ContextBench 480、RepoQA 240；minimums 为
  ContextBench >= 40、RepoQA >= 20；固定 budget 5；固定 methods
  `bm25,regex,symbol`；RRF same-budget 必需。
- **Aggregate yield**：`records_attempted_total=186`、
  `records_successful=119`、`records_excluded=67`、
  `contextbench_successful=82`、`repoqa_successful=37`、
  `quota_reached=false`、`failure_category_counts.retrieval_failed=67`、
  `rrf_required_but_missing=0`。
- **私有 traces**：`private_score_manifest.record_count=833`（119×7 arm）和
  `private_attempt_manifest.record_count=186`；二者均为 `/tmp` private，path
  不公开序列化。
- **119-record metric signal**：v0.3 与 v0.2 在 file_recall@10、MRR、
  success_rate 上打平；v0.3 vs v0.2 有 `span_f0.5@10 +0.004953`、
  `quality_per_latency +0.002853`。v0.3 相对 BM25/agreement/RRF 在
  file_recall/MRR/success 上为 +0.184874/+0.164566/+0.184874，但仍有
  latency cost，且因为 quota 少 1 条不算 pass。
- **解释**：BEA-5 不是 pass，也不是 benchmark/performance claim。它成为
  BEA-4/5 failure decomposition 输入，而不是继续 v0.31 权重微调或继续改
  sampling 的理由。
- **严格 claim 边界**：`claim_level=
  bea_v03_frozen_policy_robustness_smoke_only`。非 benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/EvidenceCore
  /downstream-value。`provider_calls=0`。
- **BEA-5 不修改 BEA-0/BEA-1/BEA-2/BEA-3/BEA-4**：独立 phase、评估器、
  artifact。v0.3 冻结。

## B16-F findings

- **B16-F 是第一个下游 live-provider paired smoke**，将 BEA v0.3-derived
  context pack 与 same-budget BM25 context-pack 对照（以及 sparse 对照）
  在有界合成 coding 任务上进行比较。三个 arm：`control_sparse`、
  `bm25_same_budget_context_pack`、`bea_v03_context_pack`。主对比：BEA vs
  same-budget BM25。次对比：BEA vs sparse、BM25 vs sparse。八个固定任务
  族。默认 8 任务 x 3 arms = 24 次 live provider 调用。
- **BEA v0.3 context pack selector 仅使用 runtime-clean 候选特征**
  （method source、rank、score/normalized score、agreement count、span
  extent、path）。**绝不**读取 gold path、`correct_value`、task_family
  decisive cue 或任何私有答案。通过 self-test 中的 gold-tainting 不变量
  验证（污染 `correct_value` **不**改变 BEA 选择）。
- **私有 SCORE JSONL + 私有 event JSONL 仅写入 `/tmp`**（每个 task x arm
  一行 = 默认各 24 行）。私有 SCORE 携带 candidate_features、
  bea_action_trace、bea_budget_trace、selected_candidates、score_outcome。
  私有 event 携带 prompt、response、parsed_action、patch、test_stdout/
  stderr、provider_metadata。公开 artifact 仅包含聚合 manifest，含 record
  count、schema 版本、`storage_class=tmp_private`、
  `path_publicly_serialized=false`、manifest hash。
- **352/352 self-test check 通过**。本地 no-env 路径真实
  `blocked_remote_not_enabled`（**不**是假通过）。
- **严格声明边界**：`claim_level=
  bea_derived_context_pack_downstream_paired_smoke_only`。不是 benchmark/
  leaderboard/performance/method-winner/calibration/promotion/default/
  runtime/EvidenceCore/downstream-value。CI 通过**不**要求 BEA 改善；零/
  负 delta 有效。
- **手动 real-provider CI run `27945253824` 已通过**：8 任务 x 3 arms = 24 次 live provider calls。Sparse control 解出 2/8（`solve_rate=0.25`、`tests_pass_rate=0.25`、`latency_seconds_mean=13.4355`）；same-budget BM25 context pack 解出 11/11（`solve_rate=1.0`、`tests_pass_rate=1.0`、`latency_seconds_mean=1.1885`）；BEA v0.3 context pack 也解出 11/11（`solve_rate=1.0`、`tests_pass_rate=1.0`、`latency_seconds_mean=1.579`）。主对比 BEA-vs-BM25 solve/test delta 为 0.0；BEA mean latency +0.3905s，prompt tokens +161。两个 context arms 相对 sparse 的 solve/test 均 +0.75。primary contrast 的 `context_pack_signal_observed=false`。
- **B16-F 不修改 BEA-0/BEA-1/BEA-2/BEA-3**：独立 phase、evaluator、
  artifact。该 CI 结果仍是 smoke-only，不证明下游价值或方法优越。
- **公开 artifact 仅聚合**：`arm_results`（per-arm metrics）、
  `paired_deltas`（3 对比）、`task_family_results`、
  `family_signal_summary`、`honest_signals`、`private_score_manifest`、
  `private_event_manifest`、`forbidden_scan`、no-claim flag。无 raw
  prompt/response/patch/path/片段/候选特征/BEA action trace/pack
  composition/per-run 行。
- **Workflow stage `b16f_bea_derived_context_pack_paired_smoke`** 添加到
  `real-provider-benchmark.yml`（仅手动 `workflow_dispatch`；
  `enable_remote_models=false` 默认；专用 sanitized upload；排除通用
  upload；删除 plan.json；在缺失 arm、零 provider_calls、缺失
  paired_deltas、私有 manifest 计数不匹配、forbidden_scan 失败时
  fail-closed）。

## B16-G findings

- **B16-G 通过 live-provider atom ablation 解释 B16-F 的下游 tie**。
  五个固定 arm：`control_sparse`、`target_only`、`support_only`、
  `distractor_plus_support`、`target_plus_support`。八个固定任务族
  （复用 B16-F 以保持可比性）。默认 8 任务 x 5 arms = 40 次 live
  provider 调用。
- **Atom composition per arm 为确定性且私有**（仅写入 `/tmp` 下的私有
  SCORE JSONL）。Atom：`target_file_cue`、`target_symbol_cue`、
  `support_module_cue`、`decisive_cue`、`distractor_file_cue`。
  `target_plus_support` 携带全部四个 target/support/decisive atom；
  `distractor_plus_support` 携带 distractor + support + decisive
  （wrong-file cue）；`target_only` 仅携带 target file + symbol；
  `support_only` 仅携带 support + decisive。
- **主对比**：`target_plus_support` vs `distractor_plus_support`；
  `target_plus_support` vs `support_only`；`target_only` vs
  `support_only`。**次对比**：每个 context arm vs `control_sparse`。7
  对比 x 13 metrics = 91 paired delta record。
- **机制摘要 record**（仅计数）：
  `support_atom_sufficient_count`（support_only 解决的任务数）、
  `target_atom_required_count`（target_only 解决但 support_only 未解决
  的任务数）、`distractor_hurts_count`（distractor_plus_support 未解决
  但 target_plus_support 解决的任务数）、`all_arms_solved_count`、
  `sparse_solved_count`。
- **221/221 self-test check 通过**。本地 no-env 路径真实
  `blocked_remote_not_enabled`（**不**是假通过）。公开 artifact 中的
  self-test summary 仅计数（无详细 check 列表）。
- **严格声明边界**：`claim_level=
  context_pack_atom_ablation_downstream_smoke_only`。不是 benchmark/
  leaderboard/performance/method-winner/calibration/promotion/default/
  runtime/EvidenceCore/downstream-value/BEA-优越性。CI 通过**不**要求任何
  atom 获胜；零/负 delta 有效。`bea_superiority_claimed=false`。
- **手动 real-provider CI run `27947247773` 已通过**：8 任务 x 5 arms
  = 40 次 live provider calls；forbidden scan pass；私有 SCORE/event manifest
  各 record_count=40 且 `path_publicly_serialized=false`；221/221 self-test
  checks。结果：`control_sparse` solve/test=0.0，`target_only` solve/test=0.0，
  `support_only` solve/test=1.0，`distractor_plus_support` solve/test=1.0，
  `target_plus_support` solve/test=1.0。
- **机制解释**：在该有界合成 live-provider 切片上，decisive support 足以驱动解题
  （`support_atom_sufficient_count=8`）；target-only context 不足
  （`target_atom_required_count=0`）；当 decisive support 存在时 distractor
  未造成伤害（`distractor_hurts_count=0`）。这解释 B16-F 的 BEA-vs-BM25 tie，
  但不声明 BEA 优越性或下游价值证明。
- **B16-G 不修改 B16-F**：独立 phase、evaluator、artifact。
- **公开 artifact 仅聚合**：`arm_results`、`paired_deltas`、
  `task_family_results`、`mechanism_summary_records`、`honest_signals`、
  `private_score_manifest`、`private_event_manifest`、`forbidden_scan`、
  no-claim flag。无 raw prompt/response/patch/path/片段/atom
  composition/候选 trace/per-run 行。
- **Workflow stage `b16g_context_pack_atom_ablation`** 添加到
  `real-provider-benchmark.yml`（仅手动 `workflow_dispatch`；
  `enable_remote_models=false` 默认；专用 sanitized upload；排除通用
  upload；删除 plan.json；在缺失 arm、零 provider_calls、缺失主对比、
  缺失 paired_deltas、私有 manifest 计数不匹配、forbidden_scan 失败、
  bea_superiority_claimed 不为 false 时 fail-closed）。

## B16-H findings

- **B16-H 通过 live-provider file-choice atom ablation 解决 B16-G 的
  主要 confound**。B16-G 的结构化 action schema 和 prompt 强制编辑
  `target.py`，因此 `support_only` 解决 11/11 并不能证明 support atom
  单独能引导文件选择。B16-H 移除该 confound：prompt 不再说 "only use
  target.py"；无全局 `ALLOWED_EDIT_FILES = {target.py}` 集合；validator
  仅接受 per-task 安全文件集（target + distractor + support/config/
  cross-file module）；绝不接受任意路径；chosen file 仅记录在 `/tmp`
  下的私有 SCORE/event JSONL 中；公开仅暴露聚合文件选择率。
- **五个固定 arm**：`control_sparse`、`file_choice_target_only`、
  `file_choice_support_only`、`file_choice_distractor_plus_support`、
  `file_choice_target_plus_support`。八个固定任务族（复用 B16-F/B16-G）。
  默认 8 任务 x 5 arms = 40 次 live provider 调用。
- **主对比**：`file_choice_target_plus_support` vs
  `file_choice_support_only`；`file_choice_target_plus_support` vs
  `file_choice_distractor_plus_support`；`file_choice_target_only` vs
  `file_choice_support_only`。**次对比**：每个 context arm vs
  `control_sparse`。7 对比 x 17 metrics = 119 paired delta record。
- **文件选择聚合 metrics**（**绝不**实际文件名）：
  `selected_target_file_rate`、`selected_distractor_file_rate`、
  `selected_support_file_rate`、`wrong_file_edit_rate`、
  `correct_file_before_first_edit_rate`。
- **机制摘要 record**（仅计数，均带 "with_file_choice" 限定符，因为
  confound 已移除）：
  `support_only_sufficient_with_file_choice_count`、
  `target_atom_required_with_file_choice_count`、
  `distractor_hurts_with_file_choice_count`、
  `wrong_file_selection_count`、
  `all_arms_solved_count`、`sparse_solved_count`。
- **266/266 self-test check 通过**。本地 no-env 路径真实
  `blocked_remote_not_enabled`（**不**是假通过）。公开 artifact 中的
  self-test summary 仅计数。
- **严格声明边界**：`claim_level=
  file_choice_atom_ablation_downstream_smoke_only`。不是 benchmark/
  leaderboard/performance/method-winner/calibration/promotion/default/
  runtime/EvidenceCore/downstream-value/BEA-优越性。CI 通过**不**要求任何
  atom 获胜；零/负 delta 有效。`bea_superiority_claimed=false`。文档对
  任何 sufficiency 发现标明 "在此有界合成 file-choice 切片上"。
- **B16-H live 结果**：手动 real-provider CI run `27949115076` 已通过：8 任务 x 5 arms = 40 次 live provider calls；forbidden scan pass；私有 SCORE/event manifest 各 `record_count=40` 且 `path_publicly_serialized=false`；266/266 self-test。结果：`control_sparse` solve/test=0.0；`file_choice_target_only` solve/test=0.0 但 selected target file rate=1.0；`file_choice_support_only` solve/test=1.0 且 selected target file rate=1.0；`file_choice_distractor_plus_support` solve/test=1.0 且 selected target file rate=1.0；`file_choice_target_plus_support` solve/test=1.0 且 selected target file rate=1.0。机制 summary：`support_only_sufficient_with_file_choice_count=8`、`target_atom_required_with_file_choice_count=0`、`distractor_hurts_with_file_choice_count=0`、`wrong_file_selection_count=0`、`all_arms_solved_count=0`、`sparse_solved_count=0`。解释：在此有界合成 file-choice 切片上，decisive support cue 仍足以引导文件选择；target-only context 不足；当 decisive support 存在时 distractor 未造成伤害。这不是下游价值证明、BEA 优越性声明、method-winner/default 声明、benchmark/performance 声明或 calibration 声明。
- **公开 artifact 仅聚合**：`arm_results`（含文件选择率）、
  `paired_deltas`、`task_family_results`、`mechanism_summary_records`、
  `honest_signals`、`private_score_manifest`、`private_event_manifest`、
  `forbidden_scan`、no-claim flag。无 raw prompt/response/patch/path/
  片段/atom composition/chosen file 名/候选 trace/per-run 行。
  `input_summary.file_choice_confound_removed=true`。
- **Workflow stage `b16h_file_choice_atom_ablation`** 添加到
  `real-provider-benchmark.yml`（仅手动 `workflow_dispatch`；
  `enable_remote_models=false` 默认；专用 sanitized upload；排除通用
  upload；删除 plan.json；在缺失 arm、零 provider_calls、缺失主对比、
  缺失 wrong-file/file-choice metrics、私有 manifest 计数不匹配、
  forbidden_scan 失败、`file_choice_confound_removed` 不为 true、
  `bea_superiority_claimed` 不为 false 时 fail-closed）。

## B16-I findings

- **B16-I 测试 B16-H 暴露的机制**。B16-H 移除了文件选择 confound，但
  support-only 仍然解决了所有任务，因为 support cue 过于 decisive。
  B16-I 重新设计任务，用来测试 support 单独是否可变为非决定性：预期
  target binding 和 support rule 需要同时存在。
- **五个固定 arm**：`control_sparse`、`file_choice_target_only`、
  `file_choice_nondecisive_support_only`、
  `file_choice_distractor_plus_nondecisive_support`、
  `file_choice_target_plus_support`。八个固定任务族（复用
  B16-F/B16-G/B16-H）。默认 8 任务 x 5 arms = 40 次 live provider 调用。
- **预期非决定性 support cue**：给出 formula/invariant/dependency/config
  relation，按设计仍应需要 TARGET BINDING。**不**包含确切最终答案、
  确切 target-file 指令或 target-symbol edit 指令。Run `27950908481`
  显示该设计未让 support-only 变为非决定性：support-only 仍解出 11/11。
- **主对比**：`file_choice_target_plus_support` vs
  `file_choice_target_only`；vs
  `file_choice_nondecisive_support_only`；vs
  `file_choice_distractor_plus_nondecisive_support`。**次对比**：
  `file_choice_target_only` vs
  `file_choice_nondecisive_support_only`；每个 context arm vs
  `control_sparse`。8 对比 x 17 metrics = 136 paired delta record。
- **机制摘要 record**（7 个计数）：
  `target_support_conjunction_required_count`（tps 解决但 target_only
  和 support_only 都未解决）、`support_only_sufficient_count`、
  `target_only_sufficient_count`、`distractor_hurts_count`、
  `wrong_file_selection_count`、`all_arms_solved_count`、
  `sparse_solved_count`。
- **306/306 self-test check 通过**。本地 no-env 路径真实
  `blocked_remote_not_enabled`（**不**是假通过）。仅计数 self-test 字段
  （`self_test_checks_total`、`self_test_checks_passed`）；**不**发布
  `self_test_summary` 或 `self_test_checks` 列表。
- **严格声明边界**：`claim_level=
  target_support_conjunction_downstream_smoke_only`。不是 benchmark/
  leaderboard/performance/method-winner/calibration/promotion/default/
  runtime/EvidenceCore/downstream-value/BEA-优越性。CI 通过**不**要求
  conjunction 成立。`bea_superiority_claimed=false`。
- **B16-I live 结果**：手动 real-provider CI run `27950908481` 已通过：8 任务 x 5 arms = 40 次 live provider calls；forbidden scan pass；私有 SCORE/event manifest 各 `record_count=40` 且 `path_publicly_serialized=false`；306/306 self-test。结果：`control_sparse` solve/test=0.0；`file_choice_target_only` solve/test=0.125 且 selected target file rate=1.0；`file_choice_nondecisive_support_only` solve/test=1.0 且 selected target file rate=1.0；`file_choice_distractor_plus_nondecisive_support` solve/test=1.0 且 selected target file rate=1.0；`file_choice_target_plus_support` solve/test=1.0 且 selected target file rate=1.0。机制 summary：`target_support_conjunction_required_count=0`、`support_only_sufficient_count=8`、`target_only_sufficient_count=1`、`distractor_hurts_count=0`、`wrong_file_selection_count=0`、`all_arms_solved_count=0`、`sparse_solved_count=0`。解释：预期非决定性的 support cue 在此有界合成 file-choice 切片上仍然足够；target+support 未超过 support-only；target-only 仅解出 1/8；support 存在时 distractor 未造成伤害。这意味着 target-support conjunction 未被观察到。这不是下游价值证明、BEA 优越性声明、method-winner/default 声明、benchmark/performance 声明或 calibration 声明。
- **B16-I 不修改 B16-F/B16-G/B16-H**：独立 phase、evaluator、artifact。
- **Workflow stage `b16i_target_support_conjunction`** 添加到
  `real-provider-benchmark.yml`（仅手动 `workflow_dispatch`；
  `enable_remote_models=false` 默认；专用 sanitized upload；排除通用
  upload；删除 plan.json；在缺失 arm、零 provider_calls、缺失主对比、
  缺失 wrong-file/file-choice metrics、私有 manifest 计数不匹配、
  `support_cue_nondecisive` 不为 true、`bea_superiority_claimed` 不为
  false、forbidden_scan 失败时 fail-closed）。

## B16-J findings

- **B16-J 是最后一个 B16 atom-redesign 尝试**。它用 role-neutral candidate filenames 与完整 prompt 泄漏自测修复 B16-I 失败；target/distractor 角色只保留在私有结构中，公开 artifact 仍 aggregate-only。
- **五个固定 arms**：`control_sparse`、`ambiguous_target_only`、`ambiguous_support_only`、`ambiguous_distractor_plus_support`、`ambiguous_target_plus_support`。八个固定任务族；默认 8 任务 x 5 arms = 40 次 live provider calls。
- **329/329 self-test check 通过**。本地 no-env 路径真实 `blocked_remote_not_enabled`。仅计数 self-test 字段。
- **B16-J live 结果**：手动 real-provider CI run `27953321504` 已通过：8 任务 x 5 arms = 40 次 live provider calls；forbidden scan pass；私有 SCORE/event manifest 各 `record_count=40` 且 `path_publicly_serialized=false`；329/329 self-test。结果：`control_sparse` solve/test=0.0、selected_target_file_rate=0.125、wrong_file_edit_rate=0.875；`ambiguous_target_only` solve/test=0.0、selected_target_file_rate=1.0；`ambiguous_support_only` solve/test=0.25、selected_target_file_rate=0.25、selected_distractor_file_rate=0.625、wrong_file_edit_rate=0.75；`ambiguous_distractor_plus_support` solve/test=0.625、selected_target_file_rate=0.625、selected_distractor_file_rate=0.375；`ambiguous_target_plus_support` solve/test=1.0、selected_target_file_rate=1.0、wrong_file_edit_rate=0.0。`ambiguous_target_plus_support` 的主 delta：vs `ambiguous_support_only` solve/test delta=+0.75、wrong_file_edit_rate delta=-0.75、selected_target_file_rate delta=+0.75；vs `ambiguous_target_only` solve/test delta=+1.0；vs `ambiguous_distractor_plus_support` solve/test delta=+0.375、wrong_file_edit_rate delta=-0.375。机制 summary：`target_support_conjunction_required_count=6`、`support_only_sufficient_count=2`、`target_only_sufficient_count=0`、`distractor_hurts_count=3`、`ambiguous_support_wrong_binding_count=6`、`wrong_file_selection_count=6`、`all_arms_solved_count=0`、`sparse_solved_count=0`。解释：在 role-neutral 文件名和完整 prompt 泄漏自测之后，B16-J 终于在该有界合成切片上隔离出 target+support conjunction 信号；support-only 多数任务不再足够（2/8），target-only 0/8，而 ambiguous support 加 target binding 后 11/11。该结果仍只是 smoke-level 合成 live-provider 机制结果，不是下游价值证明、BEA 优越性、method-winner/default、benchmark/performance、calibration、promotion 或 runtime/EvidenceCore 改动。
- **停止规则结果**：B16-J 已隔离出有界 conjunction 信号，因此不运行 B16-K；下一步转向外部 BEA scale / 更广真实 benchmark 工作。
- **严格声明边界**：`claim_level=ambiguous_support_conjunction_downstream_smoke_only`。不是下游价值/BEA 优越性/method winner/default/benchmark/calibration/promotion/runtime/EvidenceCore 声明。`bea_superiority_claimed=false`。

## BEA-FD1 发现

- **BEA-FD1 通过子进程精确重放 BEA-4/5 协议**：BEA-4（CI 27957586271，
  预期 120/840）和 BEA-5（CI 28003522632，预期 119/833）。解析私有 SCORE
  JSONL 文件，将 v0.3 结果分类到 12 固定类别，发布 records-only 聚合分解
  表。固定协议：无 budget/methods CLI 输入。
- **174/174 self-test 检查通过**。
- **公开 artifact 为 records-only**，natural key 按 oracle 指引。
- **指标损失**：质量 = max(0, baseline-treatment)；延迟 = max(0,
  treatment-baseline)。
- **Manual BEA-FD1 CI run `28011901294` 通过**：status `bea_fd1_decomposition_pass`，records_decomposed=239，private decomposition rows=86040，forbidden_scan=pass。聚合表公开 category counts、metric-loss、win/tie/loss、benchmark buckets 和 candidate-source buckets，不公开私有行。主导的 available 类别是 low marginal gain / latency cost、gold-file absence、correct-file/wrong-span；support-target 类别在私有 SCORE 有 role labels 前仍为 unavailable。
- **严格 claim 边界**：`claim_level=bea_fd1_failure_decomposition_smoke_only`。
  非 benchmark/leaderboard/performance/method-winner/calibration/promotion/
  default/runtime/EvidenceCore/downstream-value。`provider_calls=0`。

## BEA-v0.4-P1 发现

- **BEA-v0.4-P1 集合角色代理冒烟已完成**：在新鲜小规模外部冒烟切片上，
  将评估本地的确定性角色代理集合选择策略
  （`setwise_complementarity_v0_4_p1`）与 BEA v0.3 及同预算对照组比较。
  仅为 P1 冒烟证据，不是 v0.4 证明/胜者/默认/校准。
- **269/269 自测检查通过**。
- **必需臂（6 个；RRF 廉价且稳定）**：`bm25_prefix_same_budget`、
  `bea_v0_3_anchor_span_latency`、`role_proxy_only_same_budget`、
  `setwise_complementarity_v0_4_p1`、`seeded_random_same_budget`、
  `rrf_same_budget`。处理臂：`setwise_complementarity_v0_4_p1`。
- **角色代理固定枚举（确定性、运行时清洁）**：
  `target_proxy`、`support_proxy`、`unknown`。无 gold/私有标签。
  信号：方法一致性、BM25/RRF/regex/symbol 来源、查询/路径 token 重叠、
  AST/路径角色启发式、span 紧致度、同文件/跨文件关系、来源多样性。
- **v0.4 P1 集合选择规则（冻结、无事后调优）**：
  如果可用至少一个 target_proxy；优先选择来自不同文件/符号家族的
  support_proxy；惩罚重复同文件选择；奖励新颖性/来源多样性/span 紧致度。
  冻结权重：target=0.40、support_cross_file=0.20、source_diversity=0.15、
  span_tight=0.10、novelty=0.10、dup_file_penalty=-0.35、
  weak_support_penalty=-0.15。
- **新鲜小规模外部冒烟协议（成功配额）**：
  records_successful>=30、contextbench_successful>=20、
  repoqa_successful>=10。强制排除窗口 BEA-2/3/4
  （ContextBench [40,160)、RepoQA [20,80)）。BEA-5 重叠已披露但不排除。
  这是 P1 冒烟证据，不是新鲜不相交验证。
- **硬门控**：role_proxy_assignment_rate>=0.70、
  target_proxy_available_rate>=0.50、support_proxy_available_rate>=0.30、
  unknown_only_record_rate<=0.30、setwise_selection_diff_rate_vs_v03>=0.25、
  mean_duplicate_file_count_v04<=v03、
  mean_candidate_source_diversity_v04>=v03、质量安全
  （file_recall/mrr 在 0.05 内、span 在 0.02 内、延迟在 1.25x 内）、
  至少一个方向性改进。
- **公开产物仅记录**，带自然键：
  `source_run_records`、`arm_metric_records`、`arm_delta_records`、
  `role_proxy_summary_records`、`setwise_behavior_records`、
  `failure_family_records`、`win_tie_loss_records`、
  `availability_records`，仅聚合
  `private_score_manifest`/`private_decision_manifest`/
  `private_role_proxy_manifest`、`hard_gate_records`、`failure_category_count_records`、`forbidden_scan`。
- **状态**：`bea_v04_p1_smoke_pass`、`partial_directional_signal`、
  `no_go_proxy_unavailable`、`no_go_no_selection_change`、
  `no_go_quality_regression`、`unavailable_with_reason`、
  `offline_counterfactual_replay`、`fail_forbidden_scan`、
  `fail_schema_contract`。
- **默认无网络产物真实地为 `unavailable_with_reason`**：
  provider_calls=0、forbidden_scan=pass、self_test_checks_total=269、
  self_test_checks_passed=269、空记录表。
- **严格声明边界**：`claim_level=bea_v04_p1_setwise_role_proxy_smoke_only`。
  不是 benchmark/leaderboard/performance/method-winner/calibration/promotion/
  default/runtime/EvidenceCore/downstream-value。不是 v0.4 证明。不是完整
  v0.4 矩阵。`provider_calls=0`。
- **Manual CI run `28017063082` 通过 fail-closed，并产生 P1 No-Go / 弱负向结果**：status `no_go_proxy_unavailable`，records_successful=38（ContextBench 20、RepoQA 18），attempted=46，excluded=8，private SCORE rows=228，decision rows=190，role-proxy rows=760。当前 role proxies 给所有 candidate 分配了角色，但 target_proxy_available_rate=0.0，setwise_selection_diff_rate_vs_v03=0.105263（低于 0.25）。相对 v0.3 没有灾难性质量退化，但也没有改进：file_recall@10 和 MRR delta 为 0.0，span_f0.5@10 delta=-0.003036，latency delta=+0.001686s，quality_per_latency delta=-0.000809。除非先改进 target-role 特征，否则不要把这个 target-role proxy 设计推进到完整 v0.4 矩阵。

## BEA-v0.4-P2 发现

- **BEA-v0.4-P2 目标角色代理修复冒烟已完成**：local checkpoint
  `d59492f`，manual CI run `28020331024`。
- **结果是有效 P2 No-Go，不是 v0.4 证明**：status
  `no_go_target_proxy_still_unavailable`，records_successful=38
  （ContextBench 20、RepoQA 18），attempted=46，excluded=8，
  forbidden_scan=pass，self-test 335/335，private SCORE rows=228，
  decision rows=190，role-proxy rows=760，target-feature rows=760。
- **target-role 修复有效，但未让 setwise selection 有用**：
  target_proxy_available_rate 从 0.0 提升到 1.0，target_proxy_selected_rate_p2=1.0，
  但 support_proxy_available_rate_p2=0.0。P2-vs-P1 selection difference 仍为
  0.0；P2-vs-v0.3 selection difference 仍为 0.105263（低于 0.25）。
- **质量安全通过，但没有算法推进**：相对 v0.3，file_recall@10 与 MRR delta 为
  0.0，span_f0.5@10 delta=-0.003036，latency delta=+0.001789s，
  quality_per_latency delta=-0.000857。在 support/complementarity proxy 产生非零
  support availability 并实质改变 selection 前，不进入完整 v0.4 矩阵。


## BEA-v0.4-P3 发现

- **BEA-v0.4-P3 支持/互补代理修复冒烟已完成**：local checkpoint `7f58f66`，manual CI run `28022595796`。
- **结果是有效的最终 role-proxy No-Go，不是 v0.4 证明**：status `no_go_support_proxy_degenerate`，records_successful=38（ContextBench 20、RepoQA 18），attempted=46，excluded=8，forbidden_scan=pass，self-test 400/400，private SCORE rows=266，decision rows=190，role-proxy rows=760，support-feature rows=760，pair-feature rows=38。
- **support/complementarity repair 过度修复**：target 与 support 的 availability/selection 都达到 1.0，target-support pair 也达到 1.0，但 support 退化：support_proxy_available_rate_p3=1.0（高于 <=0.90 gate），mean_support_candidates_per_record_p3=18.289474（高于 <=8.0 gate）。
- **选择改变但质量退化**：P3 相对 v0.3/P2/P1 的 selection diff 为 0.5/0.394737/0.394737，但相对 v0.3，file_recall@10 delta=-0.052632，MRR delta=-0.155263，span_f0.5@10 delta=-0.003531，latency +0.001730s，quality_per_latency 0.015992 vs 0.016856。
- **触发 role-proxy stop rule**：不要运行 legacy role-proxy P4/P5，不要从当前 role-proxy 设计进入完整 v0.4 矩阵，不要调 v0.31/v0.32。下一步算法工作应转向直接 FD1-objective setwise acquisition。

## BEA-FD2-A 发现

- **BEA-FD2-A 直接 FD1 目标 setwise 冒烟已完成**：local checkpoint `709b0cb`，manual CI run `28025382422`。
- **结果是有界 No-Go，不是 v0.4 推进**：status `no_go_no_fd1_loss_reduction`，records_successful=38（ContextBench 20，RepoQA 18），attempted=46，excluded=8，forbidden_scan=pass，self-test 373/373。
- **选择强烈改变，但目标失败**：FD1-weighted selection 相对 v0.3 diff=0.710526、相对 coverage-only diff=0.684211，因此 treatment 不是 no-op。
- **Composite loss 与质量退化**：composite FD1 loss 退化到 0.756181，而 v0.3 为 0.397802、coverage-only 为 0.748783；file_recall@10 降到 0.684211（v0.3 为 0.763158），MRR 降到 0.516228（v0.3 为 0.569737）。Span 与 latency gate 通过，但 FD1-loss 与 quality gate 失败。
- **决定**：不要从这个 objective 进入 FD2-B，不要调 v0.31/v0.32 权重，也不要复活 role proxy。直接 FD1-weighted objective 在这个 bounded frame 上应视为失败算法假设。

## BEA-FD2-A1 发现

- **BEA-FD2-A1 failure attribution replay 已完成**：local checkpoint `67a6d61`，manual CI run `28027342996`。
- **重放匹配且归因通过**：status `bea_fd2a1_attribution_replay_pass`，records_attributed=38，records_regressed=38，私有 trace 计数精确（190/190/190/950/1），forbidden_scan=pass，self-test 404/404。
- **主导机制**：`latency_category_non_actionable_or_dominating` 在 38/38 条退化记录上触发。次级机制小很多：redundancy_overcorrection 4/38，gold_file_displacement 3/38，aggregate_weight_category_collision 3/38。
- **候选可用性不是 blocker**：`candidate_availability_limit=0/38`；38/38 记录在 budget 与 2×budget 以上的池中都有更好候选。
- **决定**：FD2-A 失败是因为 objective 优化了一个 candidate-level proxy 不可操作的 latency-loss 类别。下一步 objective 工作必须去掉或解耦不可操作的 latency 压力，并保护 file-recall/gold-file utility；不要从 FD2-A 进入 FD2-B，不要复活 role proxy，不要调 v0.31/v0.32 权重。

## BEA-v1-P1 发现

- **BEA-v1-P1 Actionability Audit 已完成**：local checkpoint `6e661f1`，CI 修复 commits `b63db2a` 与 `9c72ae2`，manual CI run `28076434237`。
- **审计重放通过，但 v1-A 被拒绝**：workflow 在 `/tmp` 重新生成 FD1 private decomposition，验证 FD1 replay artifact，解析 86040 条 private decomposition rows，并恢复 239 个 composite `(source_phase, private_record_id)` group。公开 artifact status 为 `no_go_retrieval_availability_limit`，不是 pass。
- **可行动性结果**：全部 12 个 FD1 failure categories 映射到 6 个 action layers（72 cells）。`latency_without_quality_gain` 明确不是 candidate selection 可行动目标，归入 `non_actionable_accounting`，保留 FD2-A1 的教训。
- **File-selector 上限结果**：`gold_file_absent` denominator=119，但 private lower-bound recoverable count 只有 1。Lower-bound rate=0.004184（低于 0.05 gate），unrecoverable candidate-unavailable lower-bound count=118，retrieval-availability rate=0.991597。公开上界仍为 119/239=0.497908，但不足以授权 v1-A。
- **决定**：不要基于这份 FD1 evidence 启动 BEA-v1-A coverage-preserving selector。下一步 BEA v1 工作应先处理 candidate availability / retrieval expansion 证据，或收集 span/stopping ceiling 所需 trace 字段，而不是做 selector-only optimization。

## BEA-v1-P2 发现

- **BEA-v1-P2 Candidate Availability / Retrieval Reach Smoke 已完成**：local checkpoint `2940750`，retrieval flag 修复 `d0daee7`，runtime-safe retrieval hardening `d4de762`，manual CI run `28093864524`。
- **状态**：`no_go_retrieval_reach_latency_or_pool_cost`。workflow 在 `/tmp` 下重建 FD1 private decomposition，验证 replay，在 119 条 `gold_file_absent` 分母上运行 4 个 retrieval-reach arms，写出 476 条私有 reach 行，并只发布 aggregate-only 表。
- **可达性结果**：baseline current pool 达到 32/119 文件。depth-only expansion 达到 59/119（新增 27，availability lift 0.226891）且成本未越界；query-anchor 达到 60/119（新增 28）但成本越界；combined depth+query 达到 81/119（新增 49），但 mean pool 202.38（10.13×）与 latency 7.025s（3.89×）违反 safety gate。
- **决策**：candidate availability 可被实证改善，因此 v1-P1 的纯 retrieval-unavailable 叙述需要细化。但 naive broad expansion 不可接受。不要从 combined arm 启动 BEA-v1-A selector。下一步 BEA v1 应做 constrained retrieval policy：保留 depth-only reach 增益，同时约束 pool/latency，并继续把 latency 排除在 candidate relevance scoring 之外。

## BEA-v1-P3 发现

- **BEA-v1-P3 Constrained Retrieval Policy Smoke 已完成**：local checkpoint `6801e2b`，manual CI run `28102428194`。
- **状态**：`no_go_p3_cost_exceeded`。workflow 在 `/tmp` 下重建 FD1 private decomposition，验证 replay，在 119 条 file-miss 分母上运行 3 个 retrieval-policy arms，写出 357 条私有 policy 行，并只发布 aggregate-only 表。
- **机制结果**：P3 几乎保留了 P2 depth-only reach（58/119 vs 59/119；新增 26 vs 27），同时把 mean pool 从 68.18 降到 41.50（相对 baseline 2.08×，而 P2 depth 为 3.41×）。Efficiency 提升到 1.208122 newly reachable per added candidate，高于 P2 depth-only 与 combined。
- **No-Go 原因**：latency safety 失败。P3 mean latency 为 3.645s，是 baseline 的 2.17×，高于 2.0× gate。这说明下一瓶颈是 retrieval-action scheduling latency，而不是 candidate relevance scoring。
- **决策**：不要把这个 scheduler 推进为 v1-A 输入。若 BEA v1 继续，应隔离 sequential/repeated retrieval actions 的 latency overhead，并在 retrieval-action 层测试 latency-aware action scheduler，同时继续把 latency 排除在 candidate relevance scoring 之外。

## BEA-v1-P4 发现

- **BEA-v1-P4 Latency-Aware Retrieval Action Scheduler Smoke 已完成**：local checkpoint `87a266a`，diagnostic upload patch `3ffeb23`，manual CI run `28118888584`。
- **状态**：`bea_v1_p4_latency_aware_retrieval_scheduler_pass`。workflow 在 `/tmp` 下重建 FD1 private decomposition，验证 replay，在 119 条 file-miss 分母上运行 4 个固定 P4 arms，写出 476 条私有 scheduler rows，并只发布 aggregate-only 表。
- **机制结果**：baseline 达到 32/119。P2 depth 达到 59/119（新增 27），pool 3.41×、latency 1.18×。P3 reference 达到 58/119（新增 26），latency 2.17×。P4 达到 56/119（新增 24），保留 P2 depth 增益的 >=75%，pool 2.056×，latency 1.750×，并比 P3 latency 低 19.38%。Hard-cap violations 为 0，119/119 条记录 action count 降低。
- **决策**：P4 验证 retrieval-action scheduling layer 是 runtime-clean candidate-availability lever。它仍不是 default-policy、method-winner、benchmark-performance 或 runtime-promotion 声明；selector relevance 仍未解决（mean first-gold rank 25.625；48 条记录超出 budget）。下一步应作为该 scheduler pass 的有界 follow-on 交由 review，而不是 broad retrieval expansion 或 latency-in-relevance scoring。

## BEA-v1-P4H 发现

- **BEA-v1-P4H Disjoint Scheduler Validation 已完成为分母 No-Go**：local checkpoint `dee1ce1`，full-frame scan 修复 `0dfeb27`，manual CI run `28132121958`。
- **状态**：`no_go_p4h_insufficient_denominator`。Workflow 在 `/tmp` 下重建 FD1 private decomposition，验证 239 / 86040 replay，并运行 raw external full-frame 不相交分母扫描。它产出了有效聚合 artifact，但 heldout 分母只有 73/80，因此未运行 scheduler arms。
- **分母结果**：基于 FD1 private raw-key 的精确排除移除了 239 条 BEA-4/5 prior records。扫描取到 266 条 ContextBench 和 100 条 RepoQA rows，排除 162 条 ContextBench + 77 条 RepoQA exact prior rows，尝试 104 条 ContextBench + 23 条 RepoQA candidate rows，找到 61 条 ContextBench + 12 条 RepoQA baseline file-miss records。`raw_scan_attempted_records=127`，`raw_scan_yield_file_miss_records=73`，`private_scheduler_rows=0`，`retrieval_policy_executed=false`。
- **决策**：P4H 未能在不相交 heldout 分母上验证 P4，也不授权 P5 selector/reranker、BEA-v1-A、runtime promotion 或 broad retrieval expansion。P4 仍是 bounded same-frame scheduler pass；当前直接 blocker 是现有 ContextBench/RepoQA frame 下不相交 heldout file-miss 分母不足。

## BEA-v1-P4I 发现

- **BEA-v1-P4I Disjoint Denominator Reservoir Audit 已完成为 reservoir No-Go**：local checkpoint `a834733`，manual CI run `28137455572`。
- **状态**：`no_go_disjoint_denominator_reservoir_insufficient`。P4I 只用 baseline/current candidate-pool diagnostic arm 扫描受支持 ContextBench/RepoQA Python frame，没有运行 P2/P3/P4 scheduler arms、selector/reranker 逻辑、retrieval expansion 或 provider calls。
- **Reservoir 结果**：审计取到 366 条 raw rows，从 FD1 private replay 精确排除 239 条 BEA-4/5 prior raw keys，尝试 127 条非 prior candidate rows，观察到 54 条 baseline-reached rows，只找到 73 条 FD1-excluded file-miss reservoir records。`reservoir_upper_bound_count=73`，`qualified_denominator_reservoir_count=0`，`p4h_overlap_resolved=false`，因为 P4H exact selected keys 没有提交。
- **决策**：P4H 的 denominator blocker 被确认为当前受支持 ContextBench/RepoQA Python frame 的 source/reservoir limitation，不只是 fixed-tail sampling error。不要从 P4I 进入 frozen P4H rerun、P5 selector/reranker、BEA-v1-A、runtime promotion、method-winner 声明或 broad retrieval expansion。

## BEA-v1-P4J 发现

- **BEA-v1-P4J Cross-Source File-Miss Reservoir Unlock Audit 已完成为 unqualified No-Go**：local checkpoint `18671d8`，diagnostic/fail-closed patch `18126f4`，manual CI run `28146407493`。
- **状态**：`no_go_cross_source_reservoir_unqualified`。P4J 只用 baseline/current candidate-pool replay diagnostic arm 扫描已支持的 cross-source frames：ContextBench `contextbench_verified/train` + `language_filter=all`，以及 RepoQA non-Python asset languages。它没有运行 scheduler arms、selector/reranker、provider calls、frozen P4 rerun、P5 或 BEA-v1-A。
- **Reservoir 结果**：P4J 找到较大的 FD1-excluded upper-bound file-miss reservoir：`denominator_count=333`，`reservoir_upper_bound_count=333`，`cross_source_non_python_reservoir_count=272`，`cross_source_python_reservoir_count=61`。它取到 780 rows，尝试 618 rows，排除 162 条 FD1 BEA-4/5 exact prior raw keys，选出 333 条 file-miss records，并只在 `/tmp` 写出 618 条 private reservoir scan rows。
- **Unqualified 原因**：`qualified_cross_source_reservoir_count=0`，`p4h_p4i_overlap_resolved=false`，因为 P4H/P4I exact selected keys 仍不可用/仅 aggregate-only。333-record count 是 upper bound，不是 locked all-prior-disjoint denominator。
- **决策**：P4J 证明当前 Python-frame reservoir shortage 不是完整 source story，但它仍不授权 locked-P4 validation、frozen P4 rerun、P5 selector/reranker、BEA-v1-A、runtime promotion、method-winner 声明或 broad retrieval expansion。任何下一阶段必须先解决/锁定 P4H/P4I exact overlap，或定义新的严格有界 source-audit contract；不能把 333 upper-bound reservoir 当作 ready。

## BEA-v1-P4K 发现

- **BEA-v1-P4K Exact Overlap Resolution & Locked Reservoir Audit 已完成为 locked-reservoir-ready（仅 design）**：local checkpoint `c6b7fc9`，manual CI run `28151914531`。
- **状态**：`cross_source_locked_reservoir_ready_for_locked_p4_validation_design`。P4K 在 `/tmp` 下 rerun exact reconstruction audit，重建 P4H `73/73`、P4I `73/73`、P4J `333/333`，并复现 committed split `61` Python + `272` non-Python。
- **Overlap 结果**：P4J 的 61 条 Python rows 与 P4H/P4I 重叠；post-overlap locked cross-source reservoir 为 `272/80`，全部来自 non-Python（`non_python_locked_reservoir_count=272`，`python_locked_reservoir_count=0`）。
- **边界**：这解决了 P4J 的 unqualified-reservoir blocker，并且只授权设计后续 locked-denominator P4 validation phase。P4K 本身没有运行 scheduler arms；后续单独的 P4L phase 执行了 locked scheduler validation。P4K 不授权 frozen P4 rerun、P5 selector/reranker、BEA-v1-A、runtime promotion、method-winner 声明或 broad retrieval expansion。

## BEA-v1-P4L 发现

- **BEA-v1-P4L Locked Non-Python P4 Scheduler Validation 已完成为 scheduler-validation pass**：local checkpoint `5922826`，denominator-drift classifier fix `251ae2b`，P4 treatment hard-cap gate fix `6034b3d`，heartbeat workflow patch `e98839b`，manual CI run `28184096209`。
- **状态**：`bea_v1_p4l_locked_non_python_scheduler_validation_pass`。P4L 精确重建完整 P4J/P4K split（`333/61/272`），将 locked non-Python denominator 固定为 `272`，执行四个 frozen scheduler arms，并只在 `/tmp` 写出 1088 条 private arm-outcome rows。
- **Scheduler 结果**：baseline current pool reach 为 `0/272`；P2 depth-only reference 为 `55/272`；P3 constrained reference 为 `55/272`；frozen P4 latency-aware scheduler 为 `52/272`。P4 保留 P2 gain 的 `0.945455`，`p4_vs_p3_latency_ratio=0.656763`，`p4_latency_reduction_vs_p3=0.343237`，`p4_pool_growth_ratio=2.176782`，并且 P4-treatment hard-cap violations 为 0。P2 有 3 次 hard-cap violations，但这只是 reference diagnostics。
- **边界**：P4L 验证了 frozen P4 retrieval-action scheduler 在 locked non-Python denominator 上成立。它不授权 P5 selector/reranker、BEA-v1-A selector work、runtime/default promotion、method-winner 声明、broad retrieval expansion、frozen P4 rerun 或任何未来 locked-P4 promotion/default step。

## BEA-v1-N1 发现

- **BEA-v1-N1 Frozen P4 + Span-Refiner Smoke 已完成为 rank-blocked No-Go**：local checkpoint `c77f8d1`，diagnostics patch `9c6cd41`，openlocus binary fix `c51d20b`，full-file refiner checkpoint `e04b2fa`，rank-aware D1 checkpoint `6b152d2`，auxiliary line-lookup fix `0ddc2e8`，manual CI run `28245155237`。
- **状态**：`no_go_n1_inadequate_top10_actionable_denominator`。N1 重放 FD1 private decomposition，重建 frozen P4L/P4K denominator，并在 locked 272-record non-Python denominator 上验证 D0 scheduler preservation：baseline `0`，P2 `55`，P3 `55`，P4 `52`，P4 treatment hard-cap `0`。
- **Span 结果**：D1 total / pool span-opportunity denominator 充分，为 `40`，但 D1 top-10 actionable 为 `0`，D1 rank-blocked 为 `40`。全文件同文件 refiner 在局部 gold-file 诊断上改善 8/40、退化 0/40，但这些记录全部在 top-10 之外；由于 N1 禁止 evidence reorder，不能用 canonical `SpanF0.5@10` 声明 span 改善。
- **决策**：N1 不验证 span-only repair。下一步有界 BEA-v1 工作应研究 rank/pack actionability：如何把 gold-file evidence 移入 actionable top-10 pack，同时在另行授权前继续保持 no-P5/no-BEA-v1-A/no-default-promotion 边界。

## BEA-v1-N2 发现

- **BEA-v1-N2 Rank/Pack Actionability Decomposition 已完成为 decomposition pass**：local checkpoint `e4c4d54`，stability checkpoint `e1406a5`，candidate-order classification fix `7c90213`，D0 latency display fix `a5b519b`，empirical CI source `28272769423`。
- **Artifact provenance**：公开 artifact 使用 CI `28272769423` 的已验证结果，并仅对一个非 gating 的 D0 latency 展示字段做本地 records-only 修正（`p4_p3_latency_ratio_observed=0.662177`），该值来自 closed N1 artifact。后续 rerun `28275921872` 与 `28277110197` 未产生相反 N2 evidence，因为它们在有效 N2 artifact 生成前失败。
- **状态**：`n2_rank_pack_actionability_decomposition_pass`。D2 精确重建（`40/40`），全部 rows 完成分类（`40/40`）。First gold-file rank bucket 为 `rank_21_50=40/40`；top-20 recovery 为 `0/40`，top-50/top-100 recovery 为 `40/40`，unique-file top-10 recovery 为 `0/40`，evidence materializable 为 `40/40`，hard-cap violations 为 `0`，public scanner 为 `pass`。
- **机制**：primary blocker 是 `extra_depth_append_blocked=40/40`。因此 N1 的 span bottleneck 实际是 rank/pack actionability 问题：gold file 稳定存在于更深 pool，但没有被 append/merge 到 actionable pack。
- **决策**：N2 只授权 extra-depth merge-order design。它不授权 implementation、P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、method-winner 声明、broad retrieval expansion、downstream-value 声明或 frozen P4 rerun。

## BEA-v1-N3 发现

- **BEA-v1-N3 Extra-Depth Merge-Order Design Simulation 已完成为 inconclusive design result**：local checkpoint `76ebd32`，manual CI `28278662782`，status `n3_merge_order_design_inconclusive`。
- **结果**：D3 精确重建（`40/40`）且 scanner 通过。Frozen P4 order recovery 为 `0/40`；fixed interleave recovery 为 `8/40`；early extra-depth quota 3 recovery 为 `10/40`；bounded promotion after primary prefix 4/3 recovery 为 `10/40`。最佳 recovery rate 为 `0.25`，低于预声明 `0.50` pass gate。最佳 arms 的 top-10 retention 为 `0.975`、recovered evidence materialized rate 为 `1.0`、hard-cap violations 为 `0`，但 recovery 没有跨过 gate。
- **决策**：这些简单 bounded merge-order designs 没有解决 N2 rank/pack blocker。N3 不授权 implementation、P5、BEA-v1-A、selector/reranker execution、runtime/default promotion、method-winner 声明、broad retrieval expansion、downstream-value 声明或 frozen P4 rerun。

## BEA-v1-P0-1 trace-gap audit 发现

- **BEA-v1-P0-1 Trace Gap Audit 已完成为 scanner-validated trace-surface phase**：status `trace_gap_audit_pass`，self-test `5/5`，forbidden scan `pass`。
- **结果**：该审计读取已提交的 FD1、P1、FD2-A1、P4L、N2 与 N3 artifacts，并为全部 12 个 FD1 categories 发布 sanitized per-gap records。Trace availability 为 `sanitized_available=3`、`private_only_needs_public_export=3`、`missing_label=3`、`missing_trace=2`、`aggregate_only_insufficient_for_deep_research=1`。
- **决策**：下一步应先补齐数据面，而不是实现 policy。授权的 follow-ups 是 actionability-matrix refresh、sanitized scheduler dataset export、support-link labeling inputs，以及 redundancy/risk/stop trace preservation。P0-1 不授权 P5、BEA-v1-A、selector/reranker execution、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## BEA-v1-P0-2 actionability-matrix refresh 发现

- **BEA-v1-P0-2 Actionability Matrix Refresh 已完成为 records-only join**：status `actionability_matrix_refresh_pass`，self-test `22/22`，forbidden scan `pass`，refreshed cells `72/72`，P1 causal cell classes 未改变。
- **结果**：readiness summary 为 `ready_sanitized_trace=10`、`blocked_private_export=11`、`blocked_missing_label=18`、`blocked_missing_trace=12`、`blocked_aggregate_only=3`、`not_applicable_by_layer=18`。
- **决策**：P0-2 确认下一步 BEA-v1 phase 应在任何新 policy experiment 前先导出或设计 trace inputs。它只授权 scheduler dataset export 与 support/redundancy/risk/stop trace-surface work；不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## BEA-v1-P0-3 scheduler-dataset export 发现

- **BEA-v1-P0-3 Scheduler Dataset Export 已完成为 contract export**：status `scheduler_dataset_export_contract_pass`，self-test `11/11`，forbidden scan `pass`。
- **结果**：public artifact 包含 4 条 sanitized aggregate scheduler arm rows、12 条 sanitized subgroup denominator rows、P0-2 action-cost join rows，以及未来 full export 可用的 optional private-row schema。本轮未提供 private arm rows，因为历史 P4L private JSONL 是在之前环境生成的。
- **决策**：P0-3 补齐 aggregate scheduler/action-cost surface，但没有补齐 full private arm-row export。下一步应在 `.openlocus/research-private/` 下恢复/重跑 P4L private arm rows，或转向 support-link input design。它不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## BEA-v1-P0-4 support-link input-design 发现

- **BEA-v1-P0-4 Support-Link Input Design 已完成为 labeling-contract phase**：status `support_link_input_design_pass`，self-test `11/11`，forbidden scan `pass`。
- **结果**：artifact 包含 18 条 sanitized support-link design records 与 6 个 label contract fields。它将 P0-1 的 `support_link_trace` gaps 与 P0-2 的 `blocked_missing_label` cells join 起来，但所有 target/support hit states 仍为 `unknown_not_labeled`。
- **决策**：P0-4 只授权 support-link labeling input work。它不执行 support counterfactual，也不声明 support marginal utility。它不授权 P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## BEA-v1-P0-5 support-link labeling-harness 发现

- **BEA-v1-P0-5 Support-Link Labeling Harness 已完成为 private-labeling harness contract**：status `support_link_labeling_harness_contract_pass`，self-test `21/21`，forbidden scan `pass`。
- **结果**：public artifact 包含 18 条 sanitized harness records、private-template manifest 与 validation gates。未标注 private JSONL template 已生成到 `.openlocus/research-private/`，但本轮未提供 private labels。
- **决策**：P0-5 只授权 private support labeling 或 private label validation。它不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## BEA-v1-P0-6/7/8 parallel trace-surface 发现

- **BEA-v1-P0-6/7/8 Parallel Trace Surfaces 已完成为 contract exports**：P0-6 status `same_file_redundancy_trace_surface_contract_pass`，P0-7 status `risk_penalty_trace_surface_contract_pass`，P0-8 status `ordered_prefix_stop_trace_surface_contract_pass`，self-test `5/5`，三个 reports forbidden scan 均 `pass`。
- **结果**：每个 trace surface 包含 6 条 scanner-validated contract records 与一个 optional private-trace schema。本轮未提供 private trace rows。
- **决策**：P0-6/7/8 只授权 trace-surface review 或 private trace validation。它们不授权 policy tuning、counterfactual execution、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## BEA-v1-P0-9 readiness-consolidation 发现

- **BEA-v1-P0-9 Readiness Consolidation 已完成为 next-experiment gate**：status `readiness_consolidation_pass_labeling_authorized_only`，self-test `5/5`，forbidden scan `pass`。
- **结果**：全部 8 个 P0 inputs 都可加载、status 符合预期，并通过 scanner；后段 P0 surfaces 仍为 contract-only，因为 private rows 尚未填充。
- **决策**：P0-9 只授权 private labeling 或 private trace validation。它不授权 support counterfactual execution、trace counterfactuals、policy tuning、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## BEA-v1-P1-0 support-label validator dry-run 发现

- **BEA-v1-P1-0 Support-Label Validator Dry Run 已完成**：status `support_label_validator_dry_run_pass`，self-test `22/22`，forbidden scan `pass`。
- **结果**：18 条 synthetic private labels 通过 P0-5 harness 验证，证明 schema validation、conjunction derivation、sanitizer 与 public summary path 可端到端工作。该 fixture 不是真实 label data。
- **决策**：P1-0 授权使用已验证 schema 与 harness 进行真实 private support labeling。它不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## BEA-v1-P1-1 private-labeling queue 发现

- **BEA-v1-P1-1 Private Labeling Queue Preparation 已完成**：status `private_labeling_queue_preparation_pass`，self-test `22/22`，forbidden scan `pass`。
- **结果**：18 条 project-private queue records 已生成到 `.openlocus/research-private/`；public artifact 只暴露 sanitized queue buckets 与 manifests。
- **决策**：P1-1 授权基于生成 queue 进行真实 private support labeling。它不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## BEA-v1-P1-2 private-label intake validator 发现

- **BEA-v1-P1-2 Private Label Intake Validator 已完成为 contract pass**：status `private_label_intake_validator_contract_pass`，self-test `11/11`，forbidden scan `pass`。
- **结果**：从 `.openlocus/research-private/` 验证了 18 条 project-private queue records；本轮未提供真实 private label 文件，因此有效真实 labels 仍为 `0/18`，sanitized real-label records 为空。
- **决策**：P1-2 只授权 private support-label intake validation。它不授权 support counterfactual execution、support marginal-utility 声明、P5、BEA-v1-A、selector/reranker execution、implementation、runtime promotion、broad retrieval expansion、method-winner 声明或 downstream-value 声明。

## BEA-v1-N-series roll-up after P1-2：到 N10ES

- **为什么用 roll-up**：P1-2 之后项目进入大量细粒度 per-phase docs。权威细节见 [`current-research-conclusions.md`](current-research-conclusions.md)；这里只记录主线发现，不复制所有 N10 子阶段。
- **恢复 fixed-pool 链路**：FD1/P4L/N1/N2 前置输入被重建，N6XFR-E fixed-pool 实验可以真实运行。修正 extra-depth 为 `rank>20` 后，最佳 top10 达到 `25/40`；N7/N8/N9 完成审计、独立复算和公开打包。
- **Support/trace 侧线**：P1-3 填充 automated support labels，但 P1-4/P1-5R 证明 labels 不够 informative，private context 也不可用。P2/P3 将 late trace gaps 转成 frozen logger/proxy-fixture 工作，最后因没有 empirical event source 而关闭 proxy route。
- **P4 reservoir/scheduler 分支**：P4H/P4I/P4J/P4K 将 heldout reservoir 收敛为 locked 272-record non-Python denominator，P4L 在该 denominator 上验证 frozen P4 scheduler。它仍只是 scheduler validation，不是 P5/runtime promotion。
- **Exact broader denominator 关闭**：N10 和 N10R 证明 exact broader N2-equivalent rank-pack rows 在 40-row surface 已耗尽，继续必须换 denominator 定义。
- **Span-surface 分支**：N10T 在 N1 span rows 上验证 file-level proxy gain；N10X/N10Y/N10Z 证明 span utility 仍失败，原因是 same-file window misalignment。
- **Span-window repair 分支**：固定窗口恢复 span overlaps；后续探索找到更强的 observable span-shape/top2-window variants。local-window 线最后在 `30/36` 饱和，瓶颈从 window size 转向 file reach。
- **Rank/file-reach 分支**：测试 distinct-file packing 与 deep-rank promotion；deep-rank promotion 仍有害；suffix-safe matching 修正 file-reach counts；oracle candidate insertion 显示候选来源补齐的理论上限很高。
- **Candidate-source 分支**：identifier-normalized BM25 找到旧池没有的新文件。novel-first depth-to-head repacking 给出同源正结果；fixed difference-aware rule 在 N10DZ/N10EB sample 上达到 `13/60`。
- **Public CI transfer 分支**：N10EN 在 GitHub Actions 上测试该 winner 并回归（diffaware `37/40` vs baseline `39/40`）。N10EO 解释为 novel-first 推掉强 baseline hits。N10ER 再测该 safety signal 于 held-out public CI sample，结果未复现：risk bucket `26`，losses `0/0/0`。N10ES 将其打包为有效 bounded research negative。
- **当前决策**：N10ES（`8c04a0a`）只授权 N10ET public design/decision。不授权 N10ER rerun、调阈值、policy experiment、promotion、runtime/default change、method-winner claim、downstream/scaled retrieval 或 raw diagnostic publication。


## BEA-v1-N10ET public safety probe design/decision 发现

- **BEA-v1-N10ET Public Safety Probe Design/Decision 已作为 N10E safety-probe 分支的 public-only 收尾阶段完成**：status `n10et_public_safety_probe_design_decision_complete_haae_r0_authorized`，self-test `74/74`，forbidden scan `pass`。
- **结果**：该阶段只读取 public artifacts/docs/current conclusions/research logs/README 与 git metadata（N10ES checkpoint `8c04a0a`，N10ER checkpoint `c8fd353`，CI run `28457213423`，status `n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized` 与 `n10es_public_safety_probe_audit_package_complete_n10et_authorized`，sample `80/60/40`，`overlap_zero`，citation `7772/7772`，baseline `37/39/40/40`，full `36/39/40/40` lost `1`，guard `38/39/40/40` lost `0`，diffaware `37/39/40/40` lost `1`，risk bucket `task_count=26`，losses `0/0/0`，`guard_would_preserve_full_loss_count=0`）；它不进行任何 execution、private reads、CI rerun、retrieval/recompute 或 candidate generation。记录三条收尾决策：BEA-v1-N10E/difference-aware 仍是 local same-source hypothesis；N10ER/N10ES 是有效 public held-out negative；不推广 guard/full/diffaware，不调阈值，不 rerun N10ER，不执行 selector/reranker，不 P5，不 BEA-v1-A，不 runtime/default promotion。该阶段设计并只授权下一 route：**BEA-v1-HAAE-R0 —— Hierarchical Actionable Evidence Acquisition Route Design / Schema Preflight**，一个 public-only、design-only 的 schema preflight，明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker execution、不是 P5、不是 runtime/default promotion。
- **决策**：N10ET 只授权 HAAE-R0 design/schema-preflight 交接（`haae_r0_design_only_schema_preflight_authorized_bool=true`，`haae_r0_execution_authorized_bool=false`）。它不授权 N10ET/N10ES re-run、N10ER re-run/execution、任何 execution、rerun、retrieval、recompute、candidate generation、threshold tuning、新 policy experiments、frozen-rule changes、guard/full/diffaware promotion、runtime/default changes、method-winner claims、downstream/scaled retrieval、raw diagnostic publication、CI variant execution、selector/reranker execution、BEA-v1-A、P5、provider/model network 或 network runs。所有这类 stop/go 字段均为 `false`。参见 `docs/zh/bea-v1-n10et-public-safety-probe-design-decision.md`。


## BEA-v1-HAAE-R0 hierarchical actionable evidence acquisition route design / schema preflight 发现

- **BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition Route Design / Schema Preflight 已作为下一 acquisition route 的 public-only、design-only schema preflight 完成**：status `haae_r0_design_schema_preflight_complete_haae_r1_authorized`，self-test `132/132`，forbidden scan `pass`。
- **结果**：该阶段只读取 N10ET public aggregate report 与 public docs/current-conclusions/research-log/summary/README + git metadata（checkpoint `26d817e`，status `n10et_public_safety_probe_design_decision_complete_haae_r0_authorized`，HAAE-R0 authorized true，HAAE-R0 execution false，BEA-v1-A false）；它不进行任何 execution、private reads、CI rerun、retrieval/recompute、candidate generation、arm scoring 或 OpenLocus execution。它设计了一个 machine-readable、非空的 control-plane：4 个 route architecture layers（source_acquisition、rank_pack_depth_to_head、span_projection、scheduler_operating_point —— 每个保留 EvidenceCore 并在 current-source evidence 不可用时 abstain）、10-group unified private trace schema spec（private-root-only、aggregate-bucket-only）、4-contract public aggregation contract、5 个 same-budget arm specs（BM25_same_budget、RRF_same_budget、BEA_v0.3_frozen、V1_sched_span、V1_sched_span_rank）、6 个 metric specs、held-out protocol（overlap_zero、no gold-for-policy、不 materialize split）、4 个 stop rules，以及一个带有 4-task embedded synthetic fixture 的 synthetic validator，在进程内验证所有 contracts。HAAE-R0 明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker execution、不是 P5、不是 runtime/default promotion。
- **决策**：HAAE-R0 只授权 HAAE-R1 Unified Private Trace Schema Feasibility Inventory 交接（`haae_r1_unified_private_trace_schema_feasibility_inventory_authorized_bool=true`、`haae_r1_execution_authorized_bool=false`、`haae_r1_replay_authorized_bool=false`、`haae_r1_scoring_authorized_bool=false`、`haae_r1_retrieval_authorized_bool=false`、`haae_r1_candidate_generation_authorized_bool=false`）。它不授权 N10ET/N10ES re-run、N10ER re-run/execution、任何 HAAE-R0 execution、任何 execution、rerun、retrieval、recompute、candidate generation、arm scoring、OpenLocus execution、threshold tuning、新 policy experiments、frozen-rule changes、guard/full/diffaware promotion、runtime/default changes、method-winner claims、downstream/scaled retrieval、raw diagnostic publication、CI variant execution、selector/reranker execution、BEA-v1-A、P5、provider/model network 或 network runs。所有这类 stop/go 字段均为 `false`。参见 `docs/zh/bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md`。


## BEA-v1-HAAE-R1 unified private trace schema feasibility inventory 发现

- **BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory 已完成**：状态 `haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots`（默认 / no-private 模式），self-test `121/121`，forbidden scan `pass`。
- **结果**：该阶段在默认模式下只读取 HAAE-R0 public aggregate report 与 public docs/current-conclusions/research-log/summary/README + git metadata（checkpoint `854fc2e`，status `haae_r0_design_schema_preflight_complete_haae_r1_authorized`）；它不进行任何 replay、scoring、retrieval、candidate generation、arm scoring、OpenLocus execution、HAAE-layer execution，默认模式下不读取 private roots（private read count bucket `count_0`）。Real inventory 需显式 `--allow-private-inventory --private-root <path>` opt-in。它对 10 个 HAAE-R0 schema groups 是否能从显式提供的 project-private root buckets 中填充进行盘点，只输出 aggregate buckets。5 个 critical groups 是 `task_identity`、`candidate_pool`、`evidence_core`、`arm_assignment`、`outcome_metric`。Pass 要求全部 10 个 groups 至少 partial 且 critical groups full 或 sufficient；有效但不足则为 controlled no-go。它绝不发布 paths、filenames、basenames、repo names、task ids、queries、candidates、spans、snippets、hashes、exact ranks/scores、labels 或 row values。HAAE-R1 明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker execution、不是 P5、不是 runtime/default promotion。
- **决策**：Handoff：pass → **只** 授权 **BEA-v1-HAAE-R2 Feasibility-Gated Offline Trace Join Design**（design-only，不 execution/replay/scoring/retrieval/candidate generation）；controlled no-go → **只** 授权 **BEA-v1-HAAE-R1A Private Trace Coverage Gap Design**（design-only，不 execution）。它不授权任何 execution、rerun、retrieval、recompute、candidate generation、arm scoring、OpenLocus execution、replay、HAAE-layer execution、threshold tuning、新 policy experiments、frozen-rule changes、guard/full/diffaware promotion、runtime/default changes、method-winner claims、downstream/scaled retrieval、raw diagnostic publication、CI variant execution、selector/reranker、BEA-v1-A、P5、provider/model network 或 network runs。所有这类 stop/go 字段均为 `false`。参见 `docs/zh/bea-v1-haae-r1-unified-private-trace-schema-feasibility-inventory.md`。


## BEA-v1-HAAE-R1A private trace coverage gap design 发现

- **BEA-v1-HAAE-R1A Private Trace Coverage Gap Design 已完成**：状态 `haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized`，self-test `112/112`，forbidden scan `pass`。
- **结果**：该阶段只读取 HAAE-R1/R0/N10ET public artifacts/docs/evaluators 用于 constants，以及 FD1、P4L、N1、N2、N10-series / mechanism synthesis 的 public artifacts/docs（checkpoint `2ea77da`，status `haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots`，HAAE-R2 false，全部 10 个 groups `not_present`）；它不进行任何 private reads、root regeneration、replay/scoring/retrieval/candidate generation/HAAE-layer execution/CI/network/clone。它记录全部 10 个 HAAE-R0 schema groups 的 coverage gap records，为每个 group 分类一个 root source option（9 个 `public_evidence_strong`，1 个 `public_evidence_partial`），设计 5 个 bounded regeneration designs，并设计一个 6 字段 root manifest schema。HAAE-R1A 明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker execution、不是 P5、不是 runtime/default promotion。
- **决策**：HAAE-R1A 只授权 BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package（design-only，不 execution/private read/replay/scoring/retrieval/candidate generation）：`haae_r1b_bounded_private_trace_root_regeneration_preflight_authorized_bool=true`，`haae_r1b_design_only_bool=true`，`haae_r1b_execution_authorized_bool=false`。它不授权任何 execution、rerun、retrieval、recompute、candidate generation、arm scoring、OpenLocus execution、replay、HAAE-layer execution、root regeneration、threshold tuning、新 policy experiments、frozen-rule changes、guard/full/diffaware promotion、runtime/default changes、method-winner claims、downstream/scaled retrieval、raw diagnostic publication、CI variant execution、selector/reranker、BEA-v1-A、P5、provider/model network 或 network runs。所有这类 stop/go 字段均为 `false`。参见 `docs/zh/bea-v1-haae-r1a-private-trace-coverage-gap-design.md`。


## BEA-v1-HAAE-R1B bounded private trace root regeneration preflight package 发现

- **BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package 已完成**：状态 `haae_r1b_bounded_private_trace_root_regeneration_preflight_package_complete_r1c_smoke_authorized`，self-test `108/108`，forbidden scan `pass`。
- **结果**：该阶段只读取 HAAE-R1A/R1/R0/N10ET public artifacts/docs/evaluator constants，以及 R1A 使用的 public aggregate artifacts/docs（checkpoint `e54d1b4`，R1B authorized/design-only）；它不进行任何 private reads、root regeneration、replay/scoring/retrieval/candidate generation/HAAE-layer execution/CI/network/clone。它打包了一个 machine-readable control-plane：12 条 public inputs、10 条 recipes（覆盖全部 10 个 HAAE-R0 schema groups）、5 条 safe operators、3 条 private output contracts、5 条 public manifest schema fields，以及一个 R1C bounded contract。HAAE-R1B 明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker execution、不是 P5、不是 runtime/default promotion。
- **决策**：HAAE-R1B 只授权 BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke（design-only，单独实现/审查）：`haae_r1c_bounded_private_trace_root_regeneration_smoke_authorized_bool=true`，`haae_r1c_design_only_bool=true`，`haae_r1c_execution_authorized_bool=false`，`haae_r1c_bounded_recipe_only_bool=true`。R1C boundary 要求显式 opt-in、private output only、public manifest only、bounded recipe only；unbounded replay/retrieval/candidate generation/scoring/selector/BEA-v1-A/P5/runtime 全部为 false。参见 `docs/zh/bea-v1-haae-r1b-bounded-private-trace-root-regeneration-preflight-package.md`。


## BEA-v1-HAAE-R1C bounded private trace root regeneration smoke 发现

- **BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke 已完成**：状态 `haae_r1c_bounded_private_manifest_root_smoke_complete_r1d_inventory_authorized`（explicit bootstrap smoke 模式），self-test `105/105`，forbidden scan `pass`。
- **结果**：该阶段是第一个允许 explicit-opt-in 创建 private HAAE trace-root artifact 的阶段（checkpoint `8830492`，R1C 被 R1B authorized/design-only，bounded recipe only）；默认模式不进行任何 private reads 或 writes；explicit opt-in 要求 `--allow-private-root-regeneration-smoke --recipe <allowed> --private-output-root <path> --confirm-private-output-only`。Bootstrap recipe 创建 private output root，只写 manifest/control 文件与 empty/schema-category placeholders（零 raw rows）。R1C 不得运行 FD1/P4L/N10EO/N10ER replay、retrieval、scoring、candidate generation、selector、BEA-v1-A/P5/runtime/default。4 个 deferred recipes 标记为 deferred。10 条 schema group manifest records（全部 `raw_row_count=0`）。R1C 明确 **不是** BEA-v1-A、不是 selector-only、不是 selector/reranker execution、不是 P5、不是 runtime/default promotion。
- **决策**：成功的 R1C bootstrap smoke 只授权 **BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke**；所有 replay/scoring/retrieval/candidate-generation/runtime 路径仍为 false。所有 execution、rerun、replay、retrieval、recompute、candidate generation、arm scoring、OpenLocus execution、HAAE-layer execution、FD1/P4L/N10EO/N10ER replay、threshold tuning、新 policy experiments、frozen-rule changes、guard/full/diffaware promotion、runtime/default changes、method-winner claims、downstream/scaled retrieval、raw diagnostic publication、CI variant execution、selector/reranker、BEA-v1-A、P5、provider/model network、network-run 字段均为 `false`。参见 `docs/zh/bea-v1-haae-r1c-bounded-private-trace-root-regeneration-smoke.md`。

## BEA-v1-HAAE-R1D explicit private root schema inventory smoke 发现

- **BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke 已完成**：HAAE-R1C source 锁定在 checkpoint `bc1e7a2`，状态 `haae_r1d_schema_inventory_complete_no_go_bootstrap_placeholders_only`，self-test `92/92`，forbidden scan `pass`。
- **Inventory result**：explicit private-root mode，private read bucket `count_1_to_10`，private write bucket `count_0`，row values read `false`，raw publication `false`，全部 10 个 schema groups accounted。
- **结论**：R1C bootstrap root 是 placeholder-only（`placeholder groups=count_1_to_10`，`meaningful groups=count_0`），不可用于 hydration。不授权 hydration execution 或 HAAE-R2。

## BEA-v1-HAAE-R1E bounded private experiment material generation 发现

- **BEA-v1-HAAE-R1E Bounded Private Experiment Material Generation 已完成**：HAAE-R1D source 锁定在 checkpoint `9299b0a`，状态 `haae_r1e_bounded_private_material_generation_complete_r2_small_experiment_authorized`，self-test `21/21`，forbidden scan `pass`。
- **Default safety**：无显式 opt-in 的状态为 `haae_r1e_unavailable_no_explicit_material_generation_opt_in`；默认模式不读取 private，也不写入 private。
- **Explicit material result**：只允许 local/manual，不使用 CI/network/clone/provider/model/OpenLocus runtime retrieval；sample bound 为 `3-5`，candidate depth `<=20`；raw task/query/path/label/span/snippet/score rows 只写入显式 private root。
- **Public result**：只发布 aggregate buckets，全部 10 个 schema groups accounted，required six groups meaningful，存在 BM25-like 与 RRF-like traces，candidate/rank/evidence/outcome row buckets 非零，不发布 private paths/task ids/queries/candidates/labels/spans/scores/hashes/snippets/rows/diagnostics。
- **决策**：R1E 只授权 small local HAAE-R2 experiment。CI/network/clone/provider、broad replay、selector/reranker、BEA-v1-A/P5、runtime/default changes、scoring claims、method-winner claims 与 raw publication 仍不授权。

## BEA-v1-HAAE-R2 small local lexical material experiment 发现

- **BEA-v1-HAAE-R2 Small Local Lexical Material Experiment 已完成**：HAAE-R1E source 锁定在 checkpoint `0135e1f`，状态 `haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized`，self-test `21/21`，forbidden scan `pass`。
- **Default safety**：无显式 private-material root 的状态为 `haae_r2_unavailable_no_explicit_r1e_private_material_root`；默认模式不读取 private，也不写入 private。
- **Explicit experiment result**：只读取已有 R1E private material groups，private read bucket 为 `count_1_to_10`，private write bucket 为 `count_0`，基于预计算 rank traces 与 outcomes 的内存 join，为 `bm25_like`、`symbol_overlap`、`rrf_like` 计算 aggregate metrics。
- **Public result**：只发布 aggregate buckets，不发布 private root path/basename、task ids、queries、candidate paths、snippets、labels、raw ranks、scores、hashes、filenames 或 raw rows。
- **决策**：R2 只授权 BEA-v1-HAAE-R2A Public Audit Package。R3 scale preflight、new candidate generation、rematerialization、retrieval、runtime/default changes、BEA-v1-A/P5、selector/reranker、scheduler/HAAE layer、provider/network、method-winner claims 与 raw publication 仍不授权。

## BEA-v1-HAAE-R2A small local experiment public audit package 发现

- **BEA-v1-HAAE-R2A Small Local Experiment Public Audit Package 已完成**：HAAE-R2 source 锁定在 checkpoint `0784be0`，R2 status 为 `haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized`，状态 `haae_r2a_public_audit_package_complete_r2b_scale_preflight_design_authorized`，self-test `22/22`，forbidden scan `pass`。
- **Public-only audit**：不读取 private，不 recompute，不执行 candidate generation、retrieval、scheduler/HAAE execution、selector/reranker、runtime/default change 或 BEA-v1-A/P5。
- **Metric readback**：R2 aggregate metrics 确认 `bm25_like`、`symbol_overlap`、`rrf_like` 均为 `rate_1`；pairwise same-top agreement 为 `rate_1`；sample bucket 为 `count_2_to_5`。
- **Boundary**：仅 tiny-N audit，不是 no method-winner claim，也不是 runtime/default decision。
- **决策**：R2A 只授权 BEA-v1-HAAE-R2B Scale Preflight Design，用于设计如何把 material generation 扩展到超过三个 tasks。Scale execution 与 CI 仍不授权。

## BEA-v1-HAAE-R2B scale preflight design 发现

- **BEA-v1-HAAE-R2B Scale Preflight Design 已完成**：HAAE-R2A source 锁定在 checkpoint `2ca1ac4`，状态 `haae_r2b_scale_preflight_design_complete_r2c_local_medium_material_smoke_preflight_authorized`，self-test `22/22`，forbidden scan `pass`。
- **Selected option**：`r14_medium_local_material_smoke`，source fixture task-count `count_21_to_50`, target task-count `count_10_to_20`, selected subset policy `deterministic_public_manifest_prefix_cap_10_to_20`，candidate-depth `count_20`，private-row cap `count_le_5000`。
- **Boundary**：no private/material gen/execution/CI/network/BEA-v1-A/P5/method-winner；不读取/写入 private，不 material generation，不 experiment，不 recompute，不 candidate generation，不 retrieval，不 source-corpus scan，不 scheduler/HAAE execution，不 selector/reranker，不 runtime/default change，不 method-winner/scaling claim。
- **决策**：R2B 只授权 BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight。R2C execution、private read/write、CI execution 与 material generation 均为 false。

## BEA-v1-HAAE-R2C local medium material smoke preflight 发现

- **BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight 已完成**：HAAE-R2B source 锁定在 checkpoint `dea8a2f`，状态 `haae_r2c_local_medium_material_smoke_preflight_complete_r2d_generation_smoke_authorized`，self-test `21/21`，forbidden scan `pass`。
- **Contract**：selected option `r14_medium_local_material_smoke`，source fixture bucket `count_21_to_50`，subset policy `deterministic_public_manifest_prefix_cap_10_to_20`，target task bucket `count_10_to_20`，candidate depth `count_20`，private row cap `count_le_5000`。
- **Boundary**：`no_private_material_gen_execution_ci_network_bea_v1_a_p5_method_winner`；不创建 private root，不写 private，不 material generation，不 experiment，不 recompute，不 retrieval，不 OpenLocus/runtime，不 CI/network/clone，不 scheduler/HAAE，不 selector/reranker，不 runtime/default，不 BEA-v1-A/P5，不 method/scaling claim。
- **决策**：R2C 只授权 BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke，要求 explicit local/manual opt-in，public output 只能 aggregate-only。

## BEA-v1-HAAE-R2D explicit local medium material generation smoke 发现

- **BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke 已完成**：HAAE-R2C source 锁定在 checkpoint `68000b2`，默认状态 `haae_r2d_unavailable_no_explicit_medium_material_generation_opt_in`，explicit pass 状态 `haae_r2d_explicit_local_medium_material_generation_smoke_complete_r2e_material_audit_authorized`，self-test `19/19`。
- **Explicit opt-in contract**：subset policy `deterministic_public_manifest_prefix_cap_10_to_20`，public fixture bucket `count_21_to_50`，target bucket `count_10_to_20`，candidate depth `count_20`，private row cap `count_le_5000`。
- **Public artifact**：public aggregate-only，private write bucket `count_le_5000`，private read validation bucket `count_1_to_10`，no raw publication。
- **Boundary**：no experiment comparison、no R2 recompute、no runtime/retrieval/source scan beyond fixture、no CI/network/provider、no scheduler/HAAE/selector、no BEA-v1-A/P5/runtime/default、no method/scaling claim。
- **决策**：R2D 只授权 BEA-v1-HAAE-R2E Local Medium Material Audit Package。

## BEA-v1-HAAE-R2E local medium material audit package 发现

- **BEA-v1-HAAE-R2E Local Medium Material Audit Package 已完成**：R2D checkpoint `c4e454a`，R2D status `haae_r2d_explicit_local_medium_material_generation_smoke_complete_r2e_material_audit_authorized`，状态 `haae_r2e_local_medium_material_audit_package_complete_r2f_medium_experiment_authorized`，self-test `30/30`。
- **Audit mode**：public-only audit，no private root read，不访问 private material。
- **Manifest readback**：task bucket `count_10_to_20`，source fixture bucket `count_21_to_50`，subset policy `deterministic_public_manifest_prefix_cap_10_to_20`，candidate depth `count_20`，private row cap `count_le_5000`，total private row bucket `count_le_5000`。
- **Rank source readback**：`bm25_like/symbol_overlap/rrf_like` present，不发布 exact scores 或 ranks。
- **决策**：R2E 只授权 R2F local medium material experiment，要求 operator-supplied explicit private root，只读取 existing R2D private material，并计算 aggregate metrics。没有 no new material/candidate generation/retrieval/runtime/source scan/CI/network/scheduler/HAAE/selector/BEA-v1-A/P5/default/method/scaling claim。

## BEA-v1-HAAE-R2F local medium material experiment 发现

- **BEA-v1-HAAE-R2F Local Medium Material Experiment 已完成**：R2E checkpoint `b166d79`，R2E status `haae_r2e_local_medium_material_audit_package_complete_r2f_medium_experiment_authorized`，默认状态 `haae_r2f_unavailable_no_explicit_r2d_private_material_root`，explicit pass status `haae_r2f_local_medium_material_experiment_complete_r2g_public_audit_authorized`，self-test `22/22`。
- **Explicit input**：要求 explicit private material root；只读取 existing R2D private material only。
- **Metrics**：为 `bm25_like/symbol_overlap/rrf_like` 计算 aggregate-only metrics；不发布 exact per-task values、paths、queries、candidates、labels、scores、hashes、snippets、basenames 或 filenames。
- **Aggregate result**：三个 rank sources 的 gold-file hit-rate bucket `rate_1`、same-top candidate rate bucket `rate_1`、top1/top5/top10 buckets `count_10_to_20`。
- **Boundary**：no new candidates/retrieval/source scan/OpenLocus/runtime/scheduler/selector/CI/network/provider/default/BEA-v1-A/P5/method/scaling claim。
- **决策**：R2F 只授权 BEA-v1-HAAE-R2G Public Audit Package。

## BEA-v1-HAAE-R2G public audit package 发现

- **BEA-v1-HAAE-R2G Public Audit Package 已完成**：HAAE-R2F checkpoint `1e0c718`，R2F status `haae_r2f_local_medium_material_experiment_complete_r2g_public_audit_authorized`，状态 `haae_r2g_public_audit_package_complete_r2h_next_step_design_authorized`，self-test `14/14`。
- **Aggregate readback**：rank-source hit-rate bucket `rate_1`，same-top candidate rate bucket `rate_1`，top1/top5/top10 buckets `count_10_to_20`。
- **Scope**：medium material experiment only；对 R2F artifact/docs 的 public-only audit。
- **Boundary**：no method-winner/default/scaling claim；不读取 private root，不执行 recompute、generation、retrieval、source scan、runtime、CI、network、scheduler 或 selector execution。
- **决策**：R2G 只授权 BEA-v1-HAAE-R2H Next-Step Design Decision，不授权 execution、CI 或 scale material generation。

## BEA-v1-HAAE-R2H next-step design decision 发现

- **BEA-v1-HAAE-R2H Next-Step Design Decision 已完成**：HAAE-R2G checkpoint `cd583d6`，R2G status `haae_r2g_public_audit_package_complete_r2h_next_step_design_authorized`，状态 `haae_r2h_next_step_design_decision_complete_r2i_harder_diversified_material_generation_authorized`，self-test `11/11`。
- **Diagnosis**：`arms_not_separating`；全部 rank sources 饱和且 same-top，因此这是 pipeline-validity evidence，但不是 method evidence。
- **Decision**：现在 reject/defer scaling the same R14 medium recipe 或 CI batch；选择 harder/diversified local material generation。
- **R2I boundary**：target 20 tasks，candidate depth 40，private row cap 10000，explicit opt-in local private root，public aggregate-only manifest，rank sources `bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline`，并且 no experiment metrics in R2I。Next phase is BEA-v1-HAAE-R2I Harder/Diversified Local Material Generation Smoke。
- **Boundary**：no method/default/scaling claim，no private read，no material generation in R2H，no execution，no recompute，no retrieval/source scan/OpenLocus/runtime，no CI/network/provider/clone，no scheduler/HAAE/selector。

## BEA-v1-HAAE-R2I harder/diversified local material generation smoke 发现

- **BEA-v1-HAAE-R2I Harder/Diversified Local Material Generation Smoke 已完成**：HAAE-R2H checkpoint `3db7366`，R2H status `haae_r2h_next_step_design_decision_complete_r2i_harder_diversified_material_generation_authorized`，默认状态 `haae_r2i_unavailable_no_explicit_harder_diversified_material_generation_opt_in`，explicit pass status `haae_r2i_harder_diversified_local_material_generation_complete_r2j_experiment_authorized`，self-test `21/21`。
- **Explicit contract**：要求 explicit opt-in；target 20 tasks，candidate depth 40，private row cap 10000。
- **Rank sources**：`bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline`。
- **Boundary**：只发布 aggregate public manifest；no experiment metrics in R2I，no old private root read，no retrieval/runtime/OpenLocus/source scan outside fixture，no CI/network/provider/clone，no scheduler/HAAE/selector，no BEA-v1-A/P5/default change，no method/scaling claim。
- **决策**：R2I 只授权 BEA-v1-HAAE-R2J Harder/Diversified Material Experiment。

## BEA-v1-HAAE-R2J harder/diversified material experiment 发现

- **BEA-v1-HAAE-R2J Harder/Diversified Material Experiment 已完成**：HAAE-R2I checkpoint `16d1349`，R2I status `haae_r2i_harder_diversified_local_material_generation_complete_r2j_experiment_authorized`，默认状态 `haae_r2j_unavailable_no_explicit_r2i_private_material_root`，pass status `haae_r2j_harder_diversified_material_experiment_complete_r2k_public_audit_authorized`，non-separating status `haae_r2j_harder_diversified_material_experiment_complete_no_go_non_separating`，self-test `21/21`。
- **Explicit contract**：要求 explicit private material root；input 是 existing R2I material only；no private writes。
- **Metrics**：为 `bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline` 计算 aggregate-only metrics，并计算 separation diagnostics；`method_winner_bool=false`。
- **Result**：`separation_signal_bool=true`，`rank_spread_bucket=spread_medium`，`control_baseline_separation_bucket=non_control_better`；`path_prior` 的 top1/top5/top10/top20 buckets 都是 `count_10_to_20` 且 `mrr_high`，而 `control_baseline` 的 top1 bucket 是 `count_0` 且 `mrr_low`。
- **Boundary**：no method winner/default/scaling claim，no root discovery，no candidate/material generation，no retrieval/runtime/OpenLocus/source scan/CI/network/provider/scheduler/selector，no exact per-task/private publication。
- **决策**：R2J 在 separation passes 时只授权 BEA-v1-HAAE-R2K Public Audit Package。

## BEA-v1-HAAE-R2K public audit package 发现

- **BEA-v1-HAAE-R2K Public Audit Package 已完成**：HAAE-R2J checkpoint `71c9a2c`，R2J status `haae_r2j_harder_diversified_material_experiment_complete_r2k_public_audit_authorized`，R2J self-test 21/21，状态 `haae_r2k_public_audit_package_complete_r2l_next_step_decision_authorized`，self-test `14/14`。
- **Locked public signal**：separation signal true，`rank_spread_bucket=spread_medium`，`control_baseline_separation_bucket=non_control_better`，且 `method_winner_bool=false`。
- **Metric readback**：path_prior top1/top5/top10/top20 bucket `count_10_to_20` 且 `mrr_high`；control_baseline top1 `count_0` 且 `mrr_low`。
- **Framing**：separation signal worth mechanism/robustness follow-up，not method winner/default/scaling claim。
- **决策**：R2K 只授权 BEA-v1-HAAE-R2L Next-Step Decision / Mechanism Preflight 作为 public design/decision；不授权 execution、CI、retrieval、new material generation、runtime/default changes、BEA-v1-A/P5、method-winner claims、scaling claims 或 raw publication。

## BEA-v1-HAAE-R2L next-step decision / mechanism preflight 发现

- **BEA-v1-HAAE-R2L Next-Step Decision / Mechanism Preflight 已完成**：HAAE-R2K checkpoint `99600db`，R2K status `haae_r2k_public_audit_package_complete_r2l_next_step_decision_authorized`，状态 `haae_r2l_next_step_decision_mechanism_preflight_complete_r2m_mechanism_decomposition_authorized`，self-test `14/14`。
- **Decision context**：separation signal but no method/default/scaling claim。
- **Selected next step**：mechanism decomposition over existing R2I material；not scale/CI or new material generation yet。
- **R2M contract**：explicit opt-in private read only，aggregate-only mechanism buckets，no writes，no new material/candidates，no retrieval/runtime/source scan/CI/network/provider/scheduler/selector，no method/default/scaling claim。
- **决策**：R2L 只授权 BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition；R2M next only R2N public audit。

## BEA-v1-HAAE-R2M path-prior separation mechanism decomposition 发现

- **BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition 已完成**：HAAE-R2L checkpoint `0dd357e`，R2L status `haae_r2l_next_step_decision_mechanism_preflight_complete_r2m_mechanism_decomposition_authorized`，默认状态 `haae_r2m_unavailable_no_explicit_r2i_private_material_root`，pass status `haae_r2m_path_prior_separation_mechanism_decomposition_complete_r2n_public_audit_authorized`，self-test `19/19`。
- **Mechanism buckets**：`dominant_mechanism_bucket=path_structure_prior`，`confidence_bucket=medium_high`，extension/language prior supporting，directory depth prior supporting，same-module/path-token overlap supporting，fixture path cues，control baseline underfit。
- **Boundary**：private read 需要 explicit existing R2I private material root；不写 private，不执行 generation、retrieval/runtime/source scan、CI/network/provider/scheduler/selector，不 raw publication，也不提出 method/default/scaling claim。
- **决策**：R2M 只授权 BEA-v1-HAAE-R2N Public Audit Package；下一步应 audit/robustness-plan 这个 path-structure signal，而不是提升默认规则。

## BEA-v1-HAAE-R2N public audit package 发现

- **BEA-v1-HAAE-R2N Public Audit Package 已完成**：HAAE-R2M checkpoint `7a3d6dc`，R2M status `haae_r2m_path_prior_separation_mechanism_decomposition_complete_r2n_public_audit_authorized`，状态 `haae_r2n_public_audit_package_complete_r2o_robustness_preflight_design_authorized`，self-test `14/14`。
- **Packaged conclusion**：`path_structure_prior`，medium_high confidence，fixture path cues + control underfit，且 no method winner。
- **Boundary**：This is not method/default/scaling claim；R2N 是 public-only，不读取 private root/material，不从 private rows recompute，不执行 generation、retrieval/source scan/runtime、CI/network/provider/scheduler/selector，也不 raw publication。
- **决策**：R2N 只授权 BEA-v1-HAAE-R2O Robustness Preflight Design，not execution/CI/new material generation yet。

## BEA-v1-HAAE-R2O robustness preflight design 发现

- **BEA-v1-HAAE-R2O Robustness Preflight Design 已完成**：HAAE-R2N checkpoint `a9066d2`，R2N status `haae_r2n_public_audit_package_complete_r2o_robustness_preflight_design_authorized`，状态 `haae_r2o_robustness_preflight_design_complete_r2p_path_cue_robustness_material_generation_authorized`，self-test `14/14`。
- **Selected next step**：BEA-v1-HAAE-R2P Path-Cue Robustness Material Generation，基于 `path_structure_prior` 与 fixture path cues + control underfit。
- **R2P contract**：target 20 tasks，candidate depth 40，row cap 20000，variants `original/path_scrambled/extension_bucket_preserved/directory_depth_preserved/control_baseline_strengthened`，local explicit opt-in，private output root，public aggregate-only，且 no experiment metrics in R2P。
- **Boundary**：R2O 是 not execution/CI/new material generation in R2O；no method/default/scaling claim；无 private reads/writes、material generation、execution/recompute/retrieval/runtime/source scan/CI/network/provider/scheduler/selector。

## BEA-v1-HAAE-R2P path-cue robustness material generation 发现

- **BEA-v1-HAAE-R2P Path-Cue Robustness Material Generation 已完成**：HAAE-R2O checkpoint `4ffc9eb`，R2O status `haae_r2o_robustness_preflight_design_complete_r2p_path_cue_robustness_material_generation_authorized`，默认状态 `haae_r2p_unavailable_no_explicit_path_cue_robustness_material_generation_opt_in`，pass status `haae_r2p_path_cue_robustness_material_generation_complete_r2q_public_audit_authorized`，self-test `22/22`。
- **Material contract**：explicit opt-in，target 20 tasks，candidate depth 40，row cap 20000，variants `original/path_scrambled/extension_bucket_preserved/directory_depth_preserved/control_baseline_strengthened`，rank sources `path_prior/path_scrambled_prior/extension_bucket_prior/directory_depth_prior/control_baseline_strengthened/rrf_variant_fusion`。
- **Gold policy**：gold labels private only 且 ranking policy ignores gold labels。
- **Boundary**：no experiment metrics in R2P；public artifact aggregate-only；R2P 只授权 BEA-v1-HAAE-R2Q Public Audit Package。

## BEA-v1-HAAE-R2Q path-cue robustness material public audit 发现

- **BEA-v1-HAAE-R2Q Path-Cue Robustness Material Public Audit Package 已完成**：HAAE-R2P checkpoint `1f721dd`，R2P status `haae_r2p_path_cue_robustness_material_generation_complete_r2q_public_audit_authorized`，状态 `haae_r2q_public_audit_package_complete_r2r_local_robustness_experiment_authorized`，self-test `18/18`。
- **Audited material properties**：explicit opt-in，private write nonzero，target 20，depth 40，5 variants，6 rank sources，required schema groups meaningful，gold private only，ranking gold false，no experiment metrics，aggregate-only，root safety pass，R2O source checkpoint `4ffc9eb`。
- **Boundary**：public-only audit；不读取 private root/material，不 recompute，不计算 experiment metrics，不执行 material generation、retrieval/runtime/source scan、CI/network/provider/scheduler/selector，不提出 method/default/scaling claim，也不 raw publication。
- **决策**：R2Q 只授权 BEA-v1-HAAE-R2R Path-Cue Robustness Experiment 读取 existing R2P private material with explicit root；no new material generation/CI/retrieval/runtime/source scan/default/method/scaling。

## BEA-v1-HAAE-R2R path-cue robustness experiment 发现

- **BEA-v1-HAAE-R2R Path-Cue Robustness Experiment 已完成**：HAAE-R2Q checkpoint `a9f5477`，R2Q status `haae_r2q_public_audit_package_complete_r2r_local_robustness_experiment_authorized`，default status `haae_r2r_unavailable_no_explicit_r2p_private_material_root`，result status `haae_r2r_path_cue_robustness_experiment_complete_r2s_public_audit_authorized_artifact_likely`，self-test `18/18`。
- **Result**：`path_cue_artifact_likely`；`path_prior_original_top10_bucket=count_11_to_20`，`path_prior_original_top20_bucket=count_11_to_20`，所有 perturbation drop buckets 都是 `count_11_to_20`，`variant_spread_bucket=spread_high`。
- **Interpretation**：path-prior signal 在 original path-cue material 上高，但在 path-scrambled、extension-preserved、directory-depth-preserved 和 strengthened-control variants 下崩掉。把它当作 fixture/path-cue evidence，不当作 robust optimization。
- **Boundary**：no method/default/scaling；不执行 private writes、new material/candidate generation、retrieval/runtime/source scan、CI/network/provider/scheduler/selector 或 raw exact-value publication。
- **Public readback markers**: explicit private material root; existing R2P material only; aggregate-only metrics; variant×rank_source; path_prior robustness; path_cue_artifact_likely; path_prior_original_top10_bucket; count_11_to_20; spread_high; no method/default/scaling; BEA-v1-HAAE-R2S Public Audit Package.
- **决策**：R2R 只授权 BEA-v1-HAAE-R2S Public Audit Package。

## BEA-v1-HAAE-R2S path-cue robustness experiment public audit 发现

- **BEA-v1-HAAE-R2S Path-Cue Robustness Experiment Public Audit Package 已完成**：HAAE-R2R checkpoint `7efc348`，R2R status `haae_r2r_path_cue_robustness_experiment_complete_r2s_public_audit_authorized_artifact_likely`，状态 `haae_r2s_path_cue_robustness_experiment_public_audit_package_complete_r2t_non_path_cue_pivot_decision_authorized`，self-test `12/12`。
- **Audit result**：R2R self-test 30/30，`path_cue_artifact_likely`，original path_prior top10/top20 count_11_to_20，all perturbation drop buckets count_11_to_20，variant_spread_bucket spread_high，privacy/aggregate-only boundary。
- **Boundary**：public-only audit；不读取 private root/material，不 recompute，不执行 experiment execution、new material/candidate generation、retrieval/runtime/source scan、CI/network/provider/scheduler/selector、raw publication，也不提出 method/default/scaling claim。
- **决策**：R2S 只授权 BEA-v1-HAAE-R2T Non-Path-Cue Pivot Decision，并且 is not execution/generation/CI。

## BEA-v1-HAAE-R2T non-path-cue pivot decision 发现

- **BEA-v1-HAAE-R2T Non-Path-Cue Pivot Decision 已完成**：HAAE-R2S checkpoint `8d8d19c`，R2S status `haae_r2s_path_cue_robustness_experiment_public_audit_package_complete_r2t_non_path_cue_pivot_decision_authorized`，状态 `haae_r2t_non_path_cue_pivot_decision_complete_r2u_content_identifier_material_generation_authorized`，self-test `14/14`。
- **Decision**：`path_cue_artifact_likely` 表明 current path-prior route 现在不适合 scale；scale current path-prior rejected/deferred，more path-cue ablations deferred，CI batch deferred，并且 content_identifier selected。
- **R2U contract**：BEA-v1-HAAE-R2U Content-Identifier Evidence Material Generation Smoke，target 20，candidate depth 40，row cap 20000，explicit opt-in，private output root，public aggregate-only output。
- **Boundary**：R2T 是 public-only，not execution/generation/CI，并且 no method/default/scaling claim。

## BEA-v1-HAAE-R2U content-identifier material generation 发现

- **BEA-v1-HAAE-R2U Content-Identifier Evidence Material Generation Smoke 已完成**：HAAE-R2T checkpoint `bc58cf7`，R2T status `haae_r2t_non_path_cue_pivot_decision_complete_r2u_content_identifier_material_generation_authorized`，default status `haae_r2u_unavailable_no_explicit_content_identifier_material_generation_opt_in`，explicit pass status `haae_r2u_content_identifier_material_generation_complete_r2v_public_audit_authorized`，self-test `24/24`。
- **Contract**：explicit opt-in，target 20，candidate depth 40，row cap 20000，rank sources `query_identifier_overlap/symbol_name_overlap/content_snippet_overlap/identifier_normalized_bm25_like/hard_negative_quality_control/content_identifier_fusion/control_baseline`。
- **Policy**：no path tokens/extensions/directories，gold private only，gold labels not used for ranking，public aggregate-only output，并且 no experiment metrics in R2U。
- **Decision**：R2U 只授权 BEA-v1-HAAE-R2V Content-Identifier Material Public Audit Package。

## BEA-v1-HAAE-R2V content-identifier material public audit 发现

- **BEA-v1-HAAE-R2V Content-Identifier Material Public Audit Package 已完成**：HAAE-R2U checkpoint `bb95f80`，R2U status `haae_r2u_content_identifier_material_generation_complete_r2v_public_audit_authorized`，状态 `haae_r2v_content_identifier_material_public_audit_package_complete_r2w_material_experiment_authorized`，self-test `14/14`。
- **Audit result**：target 20，depth 40，row cap 20000，seven rank sources，no path tokens，no gold ranking，no metrics，public aggregate-only，以及 privacy/no raw leak boundary。
- **Boundary**：R2V 是 public-only，不读取 private roots/material，不 recompute，不生成 materials/metrics，不 retrieval，不运行 runtime/source scan，不使用 CI/network/provider/scheduler/selector，也不提出 method/default/scaling claims。
- **Decision**：R2V 只授权 BEA-v1-HAAE-R2W Content-Identifier Material Experiment 读取 existing R2U private material with explicit root；boundary 为 no new material generation/retrieval/runtime/source scan/CI/network/provider/scheduler/selector/BEA-v1-A/P5/default/method/scaling/raw publication。
