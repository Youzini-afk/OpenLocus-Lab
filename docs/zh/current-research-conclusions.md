# OpenLocus 当前研究结论

日期：2026-06-20

范围：R0-R45 至 B 系列机制/策略研究、C1-C4 外部 benchmark/readiness 工作，以及 Step 6 / D 系列 dual-rubric 控制面 harness 到 D4-series rollup。

状态：研究结论总结，不是 promotion request，不是默认策略升级申请。

## 2026-06-20 历史状态：C4 Readiness 完成；D4-Series Rollup 完成；D5-H 阻塞

OpenLocus 已完成 C4 外部 benchmark readiness 序列，并完成 Step 6 / D 系列
dual-rubric 控制面序列直到 D4-series rollup。最新提交 checkpoint 为 `b7c65dd`
（`add D4 harness rollup`），记录 `claim_level=d4_series_harness_rollup_only`
和 `status=d5_blocked_no_real_human_manual_labels`。

C4 序列建立了外部 benchmark readiness 边界，但**不**声明 benchmark 性能：
ContextBench schema 与 verified row-mapping smokes、SWE-Explore row-mapping 及
负向 line-budget shape 观察、CORE-Bench source-readiness no-go、RepoQA
source/schema-contract readiness。所有公开 artifact 仍保持 aggregate-only，不持久化
raw benchmark rows、labels、row-level hashes、paths、spans、prompts、responses、
snippets、provider payloads 或私有标识符。

D 系列把 Step 6 dual-rubric relevance 从 deterministic scaffold 推进到 proxy
mappability、true-label protocol preregistration，并完成整个 D4 控制面链：

```text
D4a execution gate / dry-run
-> D4b true-label bundle harness
-> D4c annotation packet builder harness
-> D4d human annotation runbook/checklist
-> D4e filled-packet -> D4b bundle converter harness
-> D4f D4b bundle validation / gate-check harness
-> D4-series rollup / D5 blocked status
```

这只是控制面就绪，不是真实 E/S 经验校准。D4 rollup 只阻塞 D5-H / 人工参考校准：
当前不存在真实人工/手工 labels，没有在真实 labels 上运行 D4e real local
conversion，没有在真实 labels 上运行 D4f real local validation，且真实 labels 的
min-N/k/agreement/CI 门尚未通过。D4 rollup 在 flat 字段与嵌套
`d5_prerequisites` 对象中显式记录这些人工参考阻塞项。这个历史控制面状态已由下方
D5-A0 实证转折接续：缺少人工/手工标签不阻塞自动/程序化 D5-A 路径。

当前 no-claim 状态保持不变：

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
runtime_clean_general_algorithm_claimed=false
downstream_agent_value_proven=false
true_e_s_calibration_claimed=false
external_benchmark_performance_claimed=false
d5_public_aggregate_candidate_allowed=false
```

因此该历史段落不应被理解为全局研究停止。它只阻止 human-calibrated 声明与
runtime/default-policy 变更。当前活跃下一步是 D5-A 自动实证校准以及下游/外部
benchmark 实验，而不是继续新增 control-plane-only E1 preregistration。

## 2026-06-20 D5-A0 自动 E/S 校准 Smoke（实证转折）

D4-series rollup 之后，研究轨迹被修正：控制面阶段在此停止，D5-A0 产出控制面
之后的首个实证 smoke。D5-H / 人工参考 / 人工校准审计在真实人工/手动 true E/S
标签采集前仍属 out of scope/不可用；D5-A 自动/程序化实证路径已激活并继续。
D5-A0 从已提交的 r14 sanity span 标签（gold spans +
hard negatives）在真实 OpenLocus retrieval 输出（regex、bm25、symbol、rrf）
上派生**自动 E 标签**与**确定性 S-proxy 标签**，调用
`eval/run_retrieval.py` 将输出写入临时 `/tmp`（绝不提交）。已提交 artifact
仅聚合：不提交 raw predictions、per-candidate 行、path/span/snippet/hash/
query/gold/hard-negative 标签。

这是 smoke-only。它**不**声明 true E/S 校准，**不**采集新人工/手动标签，
**不**审计人工参考标签，**不**通过任何公开发布门，**不**提升任何 candidate，
也**不**解锁 D5-H / 人工参考 / 人工校准声明或 default/policy/公开发布声明。自动
E/S 标签是从已提交 span 标签（最初为
span-recall 指标采集，而非为 true E/S 评分准则采集）派生的；它们**不是**真实
人工/手动 E/S 分数，也**不是** D3 dual-rubric E/S 分数。D5-A0 不解锁
default/policy/公开发布或人工校准声明；D5-H / 人工参考 / 人工校准审计在
人工标签到位前仍属 out of scope。所有无声明 / 无运行时变更标志保持 false
（`promotion_ready=false`、`default_should_change=false`、
`retriever_changed=false`、`pack_builder_changed=false`、
`model_calls_changed=false`、`backend_changed=false`、
`default_policy_changed=false`、`evidencecore_semantics_changed=false`、
`runtime_clean_general_algorithm_claimed=false`、
`downstream_agent_value_proven=false`、
`external_benchmark_performance_claimed=false`、
`human_e_s_calibration_claimed=false`、
`automated_e_s_calibration_claimed=false`、
`d5_human_reference_calibration_unblocked=false`、
`automated_d5a_path_active=true`）。未修改
runtime/retriever/pack/model/backend/default-policy 文件。详见
[D5-A0 详细报告](d5a-automated-es-calibration.md)。

## 2026-06-20 B16-A 最小 Mock 下游 Paired Run（实证下游 agent smoke）

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
子进程测试**，并在 paired control/treatment arms 上计算聚合行为指标。
treatment pack 对设计子集因果地改变 mock agent 的行为（treatment
solve_rate=1.0 vs control solve_rate=0.0）。

这是 smoke-only。它**不**声明下游 agent 价值，**不**声明 live agent
泛化，**不**声明外部基准测试性能，**不**声明真实用户任务，**不**提升
任何 candidate，也**不**改变 runtime/retriever/pack/backend/
default-policy/EvidenceCore 语义。per-run event log、patch 和测试输出
仅留在 `/tmp`，**绝不**提交或上传。提交的 artifact 仅含聚合数据：不含
task ID、工作区路径、文件路径、源码片段、patch/diff、测试输出、raw
event log、per-run 行、私有 ID，也不含超出确定性 mock 身份以外的
provider/model 信息。所有无声明 / 无运行时变更标志保持 false
（`live_llm_agent=false`、`provider_calls_made=false`、
`remote_calls_made=false`、`downstream_agent_value_proven=false`、
`promotion_ready=false`、`default_should_change=false`、
`runtime_behavior_changed=false`、`retriever_changed=false`、
`pack_builder_changed=false`、`backend_changed=false`、
`default_policy_changed=false`、`evidencecore_semantics_changed=false`、
`external_benchmark_performance_claimed=false`、
`live_agent_generalization_claimed=false`、
`real_user_task_claimed=false`）。确定性 mock run 标志
（`downstream_agent_runs_performed=true`、
`deterministic_mock_agent=true`、`synthetic_micro_tasks_used=true`、
`paired_arms_evaluated=true`、`real_file_edits_performed=true`、
`real_test_commands_executed=true`、
`agent_behavior_metrics_evaluated=true`、
`aggregate_only_public_artifact=true`、`diagnostic_only=true`）是仅
有的额外 true 标志。未修改任何 runtime/retriever/pack/model/
backend/default-policy 文件。完整 B16 下游 coding-agent 评估阶段仍是
需要真实 provider 调用的 live paired agent run 的有界规划/可行性阶段。
详见 [B16-A 详细报告](b16a-minimal-mock-agent-paired-run.md)。

## 2026-06-21 B16-B Less-Separable Mock 下游 Paired-Agent 压力测试

> 中文译本待补充。以下为英文原文，避免内容丢失。

Following B16-A, B16-B extends the deterministic/mock downstream
paired-agent empirical run from deliberately separable micro bugs to a
harder **less-separable multi-cue stress** task family. B16-B
(`eval/b16b_less_separable_mock_paired_run.py` ->
`artifacts/b16b_less_separable_mock_paired_run/b16b_less_separable_mock_paired_run_report.json`,
schema `b16b_less_separable_mock_paired_run.v1`,
`claim_level=deterministic_mock_downstream_paired_stress_only`,
`status=mock_downstream_paired_stress_pass`,
`mode=public_aggregate_synthetic_stress_tasks`, phase `B16-B`) generates
deterministic synthetic public less-separable stress tasks in code,
creates a fresh `/tmp` workspace per task+arm with real multi-file
Python modules, runs a **deterministic mock agent** (no live LLM, no
provider calls, no remote calls) that performs **real file edits** and
runs **real subprocess tests**, and computes aggregate behavior metrics
over paired control_sparse/treatment_multi_cue arms. Solving requires
combining four cues (target_file + target_symbol + operation_hint +
support_relation); missing any cue causes a deterministic wrong
action. The treatment multi-cue pack causally alters the mock agent's
behavior (treatment solve_rate=1.0 vs control solve_rate=0.0).

This is stress-only. It does NOT claim downstream agent value, does NOT
claim live agent generalization, does NOT claim external benchmark
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
deterministic-mock-stress-run flags
(`downstream_agent_runs_performed=true`,
`deterministic_mock_agent=true`, `paired_run_executed=true`,
`real_file_edits_performed=true`,
`subprocess_tests_executed=true`,
`less_separable_stress_tasks=true`,
`aggregate_only_public_artifact=true`, `diagnostic_only=true`) are the
only additional true flags. No runtime/retriever/pack/model/
backend/default-policy files were modified. See the
[B16-B detailed report](b16b-less-separable-mock-paired-run.md).

## 2026-06-21 B16-C Live-Provider 下游 Paired Smoke（实证 live-provider 转折）

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
`replace_return_value` / `no_op`；无任意路径，无 shell），运行真实
子进程测试，并在 paired `control_sparse` / `treatment_context_pack`
arms 上计算聚合行为指标。

手动 CI run `27900913599`（`real-provider-benchmark`，
`stage=b16c_live_provider_paired_smoke`，`enable_remote_models=true`）完成
`status=live_provider_paired_smoke_pass`；已提交 artifact 现在镜像该
sanitized aggregate CI report。该 run 执行 2 个合成任务 / 4 次 live provider
call，4/4 calls 成功，invalid_json_count=0，并通过 workflow privacy
validator。两个 arm 都解出两个平凡 micro 任务（`control_sparse`
solve_rate=1.0；`treatment_context_pack` solve_rate=1.0），因此
treatment-minus-control solve-rate delta 为 0.0。默认本地 no-env 路径在未
开启 remote opt-in / provider env 不可用时仍真实输出
`blocked_remote_not_enabled` / `unavailable_no_local_provider_env`。

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
`evidencecore_semantics_changed=false`）。live-run 标志**仅**在 live
run 实际执行时为 true，否则为 false。不发布 raw model 路由前缀；仅记
录规范化的 `model_display_category`。未修改任何
runtime/retriever/pack/model/backend/default-policy 文件。B16-C upload surface
仅包含 sanitized aggregate report；`plan.json` 等通用 `real-provider` artifacts
已从 B16-C artifact upload 中排除。完整 B16 下游 coding-agent 评估阶段仍是
有界规划/可行性阶段。详见
[B16-C 详细报告](b16c-live-provider-paired-smoke.md)。

## 2026-06-21 B16-D Less-Trivial Live-Provider 下游 Paired Smoke（更难 live smoke）

继 B16-C 之后，B16-D 是更难的 live-provider paired smoke，任务族更不
平凡。B16-D
（`eval/b16d_less_trivial_live_provider_paired_smoke.py`，复用 B16-C
的 `eval/provider_client.py`）->
`artifacts/b16d_less_trivial_live_provider_paired_smoke/b16d_less_trivial_live_provider_paired_smoke_report.json`，
schema `b16d_less_trivial_live_provider_paired_smoke.v1`、
`claim_level=less_trivial_live_provider_downstream_paired_smoke_only`、
`mode=public_aggregate_synthetic_less_trivial_tasks`、阶段 `B16-D`）
生成确定性 less-trivial 多文件任务（target.py + distractor.py +
support.py + test_target.py；同符号 distractor；需要 support
relation），为每个 task+arm 创建全新 `/tmp` 工作区，仅当
`--allow-remote` + `OPENLOCUS_ALLOW_REMOTE=1` + provider env 全部设
置时运行 **live LLM agent**（OpenAI 兼容），本地应用模型的结构化
edit action（仅白名单 `target.py`；action
`replace_return_value` / `choose_helper_constant` / `no_op`；
distractor/support 不可编辑），运行真实子进程测试，并在 paired
`control_sparse` / `treatment_context_pack` arms 上计算聚合行为指
标。treatment 含 target file cue、target symbol cue、
support-relation cue 及 exact edit constraint；control 缺少决定性
cue。

手动 CI run `27901644438`（`real-provider-benchmark`，
`stage=b16d_less_trivial_live_provider_paired_smoke`，
`enable_remote_models=true`）完成
`live_provider_less_trivial_paired_smoke_pass` 并通过 privacy validation。已提交
artifact 现在镜像该 sanitized aggregate CI report：4 个合成任务 / 8 次 live
provider calls，8/8 provider calls succeeded，invalid JSON count 0，control
solve_rate=0.5，treatment solve_rate=1.0，treatment-minus-control solve_rate
delta `+0.5`，tests_pass_rate delta `+0.5`，且
`context_pack_signal_observed=true`。默认本地 no-provider-env 路径仍真实输出
`blocked_remote_not_enabled`，live-run 标志为 false。

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
微型合成 smoke 信号，不是下游价值或泛化证明。完整 B16
下游 coding-agent 评估阶段仍是有界规划/可行性阶段。详见
[B16-D 详细报告](b16d-less-trivial-live-provider-paired-smoke.md)。

## 2026-06-21 B16-E Broader Live-Provider 下游 Paired Smoke（任务族矩阵）

继 B16-D 之后，B16-E 将 live-provider paired smoke 扩展为含四个固定族
的异构合成任务族矩阵。B16-E
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
`treatment_context_pack` arms 上计算聚合行为指标 + 族级记录。

手动 CI run `27902925812`（`real-provider-benchmark`，
`stage=b16e_broader_live_provider_paired_smoke`，
`enable_remote_models=true`）完成
`broader_live_provider_paired_smoke_pass` 并通过 privacy validation。已提交
artifact 现在镜像该 sanitized aggregate CI report：8 个合成任务 / 16 次 live
provider calls；16/16 provider calls succeeded；invalid JSON count 0；
forbidden scan pass；control_sparse solve_rate=0.125、tests_pass_rate=0.125；
treatment_context_pack solve_rate=1.0、tests_pass_rate=1.0；
treatment-minus-control solve/test delta `+0.875`；4/4 families had positive
solve-rate delta；`context_pack_signal_observed=true`。

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

## 2026-06-21 F1-B Retrieval-Derived Counterfactual Utility Smoke

F1-B 将 F1 从纯合成 context variants 推进到 **retrieval-derived**
counterfactual utility。F1-B（`eval/f1b_retrieval_derived_counterfactual_utility_smoke.py`，
向后兼容导入 C5-A helpers）->
`artifacts/f1b_retrieval_derived_counterfactual_utility/f1b_retrieval_derived_counterfactual_utility_report.json`，
schema `f1b_retrieval_derived_counterfactual_utility_smoke.v1`、
`claim_level=retrieval_derived_counterfactual_utility_smoke_only`、
`mode=public_aggregate_contextbench_retrieval_counterfactual`、阶段
`F1-B`）使用真实 ContextBench verified rows、临时 /tmp repo clones、
真实 OpenLocus retrieval（bm25,regex,symbol）及 `eval/score.py` 指标
计算聚合 counterfactual candidate-set 效用 delta。五个 variants 和四个
effects；指标为 `file_recall@10`、`mrr`、`span_f0.5@10`、
`success_rate`。仅 records-shaped；无动态 dict 镜像；无
winner/best/default 字段；无 E/S 校准记法。无 provider 调用。
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

## 2026-06-21 F1 反事实证据效用 Smoke

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

## P57 泛化门控 v0

P57 是一个确定性的、无线上 LLM/无 provider 的聚合级泛化就绪门控，运行于 P51B 之后。它只消费现有聚合报告 JSON（P46/P47/P48/P49/P50/P52/P52A/P52B/P52C、可选 P51、必须 P51B），校验上游安全标志、完整性与可用性。P57 不读取源文件、候选池、提示词、响应或 provider 配置，也不在公开产物中发布路径、标识符、区间、摘要或密钥。对于单 slice/self-test 运行，P57 按设计报告 `insufficient_matrix`；它不是质量证据，不是 promotion/默认门控，也不是线上就绪证据。详见 [P57 报告](p57-generalization-gate.md)。

## P58 Source-Backed Verifier Calibration v0

P58 是一个确定性的、无线上 LLM/无 provider 的聚合级校准报告，运行于 P57 之后。它只消费 P48、P52C、P51B、P57（可选 P52B/P52A/P49）的聚合 JSON 报告，把上游的可用性与分布转成粗粒度的规划/行动提示桶。P58 不是 verifier、不是 admission、不是 Evidence、不是默认/promotion、不是线上就绪证据。它不读取源文件、候选池、任务、提示词、响应、repo lock 或 provider 配置，只输出聚合计数、比例与校准桶。详见 [P58 报告](p58-source-backed-verifier-calibration.md)。

## P59 Contrastive Pack Coverage & Counterfactual Study v0

P59 是一个确定性的、无线上 LLM/无 provider、仅聚合的预支出前置诊断，运行于 P58 之后。它从同样的 P25 临时记录重建 P49 对比候选包，并测量冻结后的包是否在触发任何 LLM 支出前就包含后续 LLM 角色所需的必要对比信息。P59 不是质量评估器、不是 admission、不是 Evidence、不是默认/promotion、不是线上就绪证据。包的构造是 gold-free 的，仅使用候选元数据；私有 labels 只在包冻结后、在显式标记的 `score_phase_gold_coverage` 块中加载。它不读取源文件、不构造提示词、不调用 provider。详见 [P59 报告](p59-contrastive-pack-coverage-counterfactual.md)。

## P60 RMC Policy v2 v0

P60 是一个确定性的、无线上 LLM/无 provider、仅聚合的诊断策略对比层，将 P47/P48 的 `request_more_context`（RMC）几何/覆盖层推进为一个可比较的策略矩阵。对同一批冻结的候选/任务输入，每个策略只选择下一个诊断动作；P60 报告聚合路由计数、SCORE-phase 黄金召回/错误代价诊断，以及标注为估算的成本/延迟估算。RMC 不是证据、不是准入、不是默认策略；P60 不声明胜者、不推荐默认策略。详见 [P60 报告](p60-rmc-policy-v2.md)。

## P61 预支出门控 v0

P61 是一个确定性的、无线上 LLM/无 provider、仅聚合的预支出门控，运行于 P60 之后。它只消费现有聚合报告（P57、P58、P59、P60、P51-B 必须；P52C 可选），并输出一个前置条件就绪决策，判断未来 P51-C 线上 LLM 微运行是否值得考虑。P61 不调用 provider、不构造提示词、不读取源文件/临时记录、不认可 Evidence、不修改默认值、不晋升、不授权 provider 支出。它只报告前置条件；开启线上运行仍需单独的 workflow_dispatch 或人工决策。对于单 slice/self-test 运行，P61 按设计报告 `insufficient_inputs` 或 `self_test_only`。它不是质量证据、不是 promotion/默认门控，也不是线上就绪授权。详见 [P61 报告](p61-pre-spend-gate.md)。

## P51-C0 实时 LLM 微运行规划器 / 显式选择加入门禁

P51-C0 是一个仅作规划用途的显式选择加入门禁，用于校验未来是否可以手动启动 P51-C 实时 LLM 微运行。它只消费聚合 P61 预支出门控报告和 P51-B 干跑 opt-in 合约，不调用 provider、不构造提示词、不读取源码、不接纳 Evidence、不修改默认值、不授权支出。它要求显式传入 `--p51c-live-opt-in`、匹配的 `I_UNDERSTAND_P51C_NOT_EVIDENCE` ack、`dataset=ci_smoke`、允许列表内的仓库、支持的输出模式（`json_schema_strict` 或 `tool_call`）、P61 状态为 `micro_run_preconditions_met` 且 provider 花费/授权标志为 false，以及 P51-B 合约就绪、源码支持资格、模式有效、redaction 前置条件满足、预算上限被尊重。它只输出聚合规划/门禁信息，使用 `repo_scope='public_ci_smoke_allowlist'`，绝不暴露原始仓库身份、路径、区间、提示词、响应、provider、model、URL 或 key。`remote_calls_by_p51c=0`、`llm_calls_by_p51c=0`、`remote_requests_by_p51c=0`、`prompt_construction_by_p51c=false`、`p51c_live_calls_disabled=true`、`provider_spend_authorized=false`、`live_run_authorized=false`。它不是 Evidence、不是质量证据、不是授权、也不是上线/默认/推广门控。详见 [P51-C0 报告](p51c-live-micro-run-planner.md)。

## P62 Generalization Matrix Aggregator v0

P62 是一个确定性的、无线上 LLM/无 provider、仅聚合的泛化矩阵聚合器，运行于 P61 之后。它只消费多个 slice 的聚合报告（P57、P58、P59、P60、P51-B），把每个 slice 的已发布聚合报告集组合成一个 >=4 个**不同** slice 的泛化矩阵。P62 不读取源文件、gold labels、私有 labels、临时记录、候选池、提示词、响应或 provider 配置；不调用 provider；不构造提示词；不承认 Evidence；不修改默认值；不授权 provider 支出。P62 使用规范化的已清理摘要与内部 SHA-256 对 slice 去重，确保同一份 slice 被复制 4 次不会夸大 slice_count。P62 只发布计数（`content_distinct_input_count`、`duplicate_input_count`、`eligible_distinct_slice_count`、`exact_duplicate_inputs_rejected_count`），不发布 repo 身份、数据集、路径、摘要或签名。当存在 >=4 个不同且 eligible 的 slice 时，P62 会输出一个 P57 兼容的 `--input-matrix` JSON 文件，供 P57 消费。它不是质量证据，不是 promotion/默认门控，也不是线上就绪证据。详见 [P62 报告](p62-generalization-matrix-aggregator.md)。

## P63 Cross-Run Slice Collector / Matrix Runner v0

P63 是一个确定性的、离线、无 provider、无线上 LLM、仅聚合的跨 run slice 收集器与编排器，运行于 P62 之后。它只接受已经下载好的本地 per-run 产物目录，校验每个目录仅包含允许清单中的聚合 JSON 报告文件，构建 P62 slice 清单，然后离线运行 P62 -> P57 -> P61。P63 不从网络抓取产物、不调用 provider、不构造提示词、不读取源文件、任务、候选、提示词、响应、trace 或临时记录，也不暴露 run、repo、数据集或目录身份。它不是 fetcher、不是质量证据、不是 provider 支出授权、不是 repo 或数据集多样性证明，也不是 promotion/默认门控或线上就绪授权。P63 只输出聚合计数与状态枚举；任何未来线上 provider 运行都需要单独的 workflow_dispatch 或人工决策。详见 [P63 报告](p63-cross-run-slice-collector.md)。

第一次真实 cross-run dry-run 使用了四个成功的 `ci_smoke` 运行，并设置 `max_tasks=6` 与 `round_robin_public_buckets`（`py_flask`、`js_express`、`go_gin`、`rust_ripgrep`）。P63 接受了 4/4 个清理后的 slice 目录，P62 报告 4 个 distinct eligible slices，P57 在 24 个聚合任务上达到 `diagnostic_matrix_complete`（`positive=9`、`no_gold=15`）。P61 最初以 `blocked_missing_actionability` 阻断，因为 P59 报告 `blocked_missing_hard_distractor`。

随后 P59B 用 gold-free 的 `metadata_hard_distractor_proxy_v1` 修复 hard-distractor/actionability 前置条件，并加入更严格 workflow gate；它没有放宽 P61，也没有用 labels 构造 pack。P51-B 随后加入 redaction-policy precondition，让 P61 能在不构造 prompt/payload 的情况下区分 `required_defined_satisfied` 与缺失 redaction policy。第二轮四 slice round-robin dry-run（`py_flask` 27643271948、`js_express` 27643273360、`go_gin` 27643274763、`rust_ripgrep` 27643276402）达到 `P61 status=micro_run_preconditions_met`，reason 为 `all_required_preconditions_present`。这仍然只是前置条件信号：它不授权 live LLM 支出、不改变默认策略、不 promotion，也不改变 EvidenceCore。真正的 P51-C live micro-run 仍需要单独显式 workflow_dispatch 或人工决策。

## B1 Live LLM Rich Candidate Run

B1 是 pre-spend gates 之后的第一个 Breakthrough Sprint 真实质量实验。它使用现有 P21 rich-candidate harness 与 P25 scorer，在四个 public repos（`py_flask`、`js_express`、`go_gin`、`rust_ripgrep`）上每个 repo 跑 6 个 round-robin public-bucket tasks。`Kimi-K2.7-Code` 分别以 `tool_call` 与 `json_schema_strict` 两种模式运行。8 个 runs 全部成功并通过 privacy gates。最强结果是 `tool_call` 模式下的 `llm_span_narrow`：24 个 tasks 上，added gold 从 8 增到 9，added false spans 从 43 降到 5，mean SpanF0.5 从 0.1099 提升到 0.2849，mean primary false-positive rate 从 0.1250 降到 0.0625。`json_schema_strict` 也保持 schema-stable，但更慢且留下更多 false spans。B1 显示 rich candidate span narrowing 有真实质量信号，但它不是 Evidence、不是 promotion，也不是默认策略变更。详见 [B1 详细报告](b1-live-llm-rich-candidate-run.md)。

## B2 Contrastive Pack Quality Experiment

B2 在 P21 live rich-candidate harness 中加入 `--pack-layout`，并在同一个四 repo、每 repo 6 task 的矩阵上比较四种 live pack 结构：`topk_plain_v0`、`topk_scores_provenance_v0`、`contrastive_competitor_v0`、`hard_distractor_contrast_v0`。16 个 tool-call runs 全部成功。主要结论是：contrastive structure 并不是自动更好。对 `llm_span_narrow` 来说，`topk_plain_v0` 保持了最低 PFP（`0.0625`），同时有 9 个 added gold 和 6 个 added false spans。`hard_distractor_contrast_v0` 把 false spans 从 6 降到 5，但杀掉两个 gold spans，并把 mean PFP 翻倍到 `0.1250`。`topk_scores_provenance_v0` 的 mean SpanF0.5 最高（`0.2829`），但 false spans 和 latency 都更高。因此 hard-distractor contrast 应该只选择性路由到 filter/no-gold/hard-distractor cases，而不是作为通用 span-narrow pack。详见 [B2 详细报告](b2-contrastive-pack-quality-experiment.md)。

## B1C Cross-Model Rich Candidate Rerun

B1C 在更新后的 active LLM roster 上重跑 B1 的 `topk_plain_v0` rich-candidate 矩阵。Kimi-K2.7-Code tool_call 仍是 reference 配置：24/24 schema-valid calls、0 fallback、9 added gold、5 added false、mean SpanF0.5 0.2825、mean PFP 0.0625。GLM-5.2 在 `json_schema_strict` 下可用（23/24 schema-valid、7 added gold、7 added false、mean SpanF0.5 0.2192），但 tool_call 仍然 noisy。Qwen3.6-27B 扩展了 27B dense 小模型覆盖，但两种输出模式都有明显 rate-limit/fallback 噪声；当前 Qwen 结果应视为 plumbing/rate-limit evidence，而不是质量证据。详见 [B1C 详细报告](b1c-cross-model-rich-candidate-rerun.md)。

## B3 Request-More-Context Quality Experiment

B3 使用同一个 workflow job 内的两个 P21 live pack layout 比较 P25 bucket routing 与固定 request-more-context treatments：`topk_plain_v0` 用于 span narrowing，`hard_distractor_contrast_v0` 用于 filter routing。第一版固定 RMC policy 没有超过 P25。P25 达到 8 added gold / 7 added false，mean SpanF0.5 0.0890，mean PFP 0.0417。两个 LLM-routed RMC 变体都是 7 added gold / 8 added false，mean SpanF0.5 0.0820，mean PFP 0.0833。local conservative route 避免了 PFP，但 recall 崩掉。B3 因此指向 interpretable policy search 或更窄的 bucket-specific routing repair，而不是固定全局 RMC 规则。详见 [B3 详细报告](b3-rmc-quality-experiment.md)。

## B6-lite Interpretable Policy Search

B6-lite 在 paired `topk_plain_v0` 与 `hard_distractor_contrast_v0` P21 ephemeral records 上运行 bounded rule search。在四 repo Kimi tool-call smoke matrix 中，它发现了低 false-cost 的候选路由，但还不是稳健 policy。`ambiguous_query_weak_only_default_use_p25_action` 观察到与 P25 相同的 added gold，同时少一个 false span、PFP 更低，但它只在一个 repo 的 Pareto frontier 上出现，并且仍使用 12 个 LLM actions。`negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action` false cost 很低且 net span value 为正，但 gold/SpanF0.5 更低。B6-lite 因此指向带真实 leave-one-repo-out 的 combined-matrix B6B search，而不是 default change。详见 [B6-lite 详细报告](b6-lite-interpretable-policy-search.md)。

## B6B Combined-Matrix Interpretable Policy Search

B6B 合并四个 public repo slices 的 paired P21 records，并执行真正的 split-before-search leave-one-repo-out：在三个 repo slices 上训练小型可解释 grammar，冻结 Pareto policies，再在 held-out slice 上评估。Live run `27689938744` 找到了低 false-cost 的候选策略，但仍没有 default policy。`ambiguous_query_weak_only_default_use_p25_action` 在聚合上保留了接近 P25 的 held-out gold/SpanF0.5，同时降低 false spans（7 gold / 5 false，对比 P25 的 7 / 8）和观察到的 PFP（0.0 对比 0.0833）。`negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action` false 更低（4 gold / 1 false），但 gold 损失太多，不适合作为 deep-quality 默认。B6B 仍然只是 diagnostic-only，需要更多 repo/model 的 fresh validation。详见 [B6B 详细报告](b6b-combined-policy-search.md)。

## B6C Frozen-Policy Validation Protocol

B6C 冻结 B6B 识别出的两个候选策略，并定义它们与固定 P25 bucket-routed baseline 的 fresh-validation 协议。B6C 不执行搜索、规则生成或 winner 选择；冻结策略文件会做 exact-spec/hash 校验，非 self-test 运行还必须提供 `b6c_fresh_validation_contract`，证明 records 是在冻结后生成且没有根据 B6C 结果回调。当前提交的 artifact 只是 self-test protocol check（`claim_level=self_test_synthetic_protocol_check`），不是已完成的 fresh validation。真正 live B6C 运行必须产出 `claim_level=frozen_policy_fresh_validation` 后，才可作为 fresh validation evidence 使用。公开报告仍只输出聚合数据，不暴露 repo/task/candidate 标识或原始内容。B6C 是 diagnostic-only，不是 promotion gate。详见 [B6C 详细报告](b6c-frozen-policy-validation.md)。

第一次 live B6C 运行（`27706742419`）已经产出 `claim_level=frozen_policy_fresh_validation`，freshness contract 有效，且 fresh records 上没有重新搜索策略。`ambiguous_query_weak_only_default_use_p25_action` 保留了 P25 的 8 个 added gold 和相同 mean SpanF0.5，同时把 false spans 从 6 降到 5、观察到的 PFP 降为 0，并把有效 LLM actions 从 24 减半到 12。更保守的 frozen policy 达到 5 gold / 1 false，net span value 为正，但 gold 损失太多，不适合作为 deep-quality 路径。这支持一个 balanced-policy 假设，但仍不是 default change。

B6E 把同一冻结策略验证扩大到 48 个 comparable tasks（`27717886432`，四个 public repo slices × 12 个 round-robin tasks）。主 balanced-policy candidate 再次保留了 P25 的 added gold 和 mean SpanF0.5，同时把 false spans 从 17 降到 14，移除了 observed PFP，并把 estimated LLM actions 从 47 降到 31。这增强了同一四仓 public universe 内的 balanced-policy hypothesis，但仍然是单模型结果，不是 repo-generalization，也不是 default change。

B6F 在另一组四个 public repo slices 上复用同一冻结策略（`27735809672`，4 × 12 tasks）。主 balanced-policy candidate 再次保留 P25 的 added gold 和 mean SpanF0.5，同时把 false spans 从 24 降到 20、移除 observed PFP、并把 estimated LLM actions 从 47 降到 31。这是第一个支持该 balanced-policy hypothesis 的 repo-generalization smoke；但它仍然是单模型、低样本，不是 default/promotion。

## B8-lite Medium Matrix Combiner

B8-lite combines the B6E and B6F frozen-policy validation reports into a derived 96-task aggregate over eight public repo slices. It performs no new provider calls, no policy search, and no per-task/per-repo reads. The main balanced-policy candidate matches P25's 21 added gold and weighted mean SpanF0.5 while reducing false spans from 41 to 34, removing observed PFP, and reducing estimated LLM actions from 94 to 62. This strengthens the single-model balanced-policy hypothesis, but remains a derived aggregate rollup, not a new live validation run or default change. See the [B8-lite detailed report](b8-lite-medium-matrix-combiner.md).

## B6D Cross-Adapter Frozen-Policy Validation

B6D 在不改变冻结策略、不重新搜索的前提下，测试 B6C 的冻结策略方向在另一个 model adapter 下是否 quality-interpretable。第一次 live B6D run（`27716082836`）成功完成，但报告 `status=not_quality_interpretable`：GLM-5.2 `json_schema_strict` 的 `schema_valid_rate=0.75`、`infra_failure_rate=0.25`，低于 adapter-health 阈值。因此 direction consistency 是 `not_determinable`，policy-family quality metrics 保持 null。这是 adapter-health evidence，不是对冻结策略的负面质量结论。Output mode 被视为 model-adapter 配置参数，而不是 OpenLocus 算法变量。详见 [B6D 详细报告](b6d-cross-adapter-frozen-validation.md)。

## B9A Adapter Health Repair Screen

B9A 用 sequential small live runs 筛查 GLM-5.2 和 Qwen3.6-27B adapter profiles。它不是 quality leaderboard，并且把 output mode 当作 model-adapter 配置参数。Qwen3.6-27B `json_schema_strict` 通过了这轮小型 health screen（`schema_valid_rate=1.0`，`infra_failure_rate=0.0`），可以用于谨慎的低流量后续验证。GLM-5.2 `json_schema_strict` 相比 tool-call 行为有所改善，但仍低于 quality-interpretable 阈值（`schema_valid_rate=0.833`，`infra_failure_rate=0.333`）。GLM tool-call 和 Qwen tool-call 仍然太 noisy，不适合关键路径验证。详见 [B9A 详细报告](b9a-adapter-health-report.md)。

## B9B Qwen Low-Volume Quality Follow-up

B9B 在 Qwen3.6-27B 已通过 health screen 的 `json_schema_strict` adapter 下，顺序运行低流量 P21 rich-candidate jobs。该 adapter 继续保持健康（`schema_valid_rate=1.0`，`infra_failure_rate=0.0`），并产出 quality-interpretable 的 span-narrow 信号：7 added gold / 4 added false，false_per_gold 0.571，mean SpanF0.5 0.2831，mean PFP 0.0625。因此在这个 adapter profile 下，Qwen 不应再只被视为 plumbing/rate-limit evidence；但这仍是小规模单 adapter follow-up，不是 default model，也不是 output-mode leaderboard 结果。详见 [B9B 详细报告](b9b-qwen-low-volume-quality-follow-up.md)。

## B9C Qwen Frozen-Policy Validation

B9C 在 Qwen3.6-27B `json_schema_strict` adapter 下验证 B6C 冻结 balanced policy。Run `27744695226` 成功完成，且 `quality_interpretable=true`、`direction_consistency=consistent_with_kimi`。Balanced frozen policy 保留了 P25 的 6 个 added gold 和 mean SpanF0.5，同时把 false spans 从 5 降到 4，移除 observed PFP，并把 estimated LLM actions 从 24 降到 12。这是 balanced-policy direction 的第一个 secondary-adapter 支持，但仍是 low-n smoke，不是 default/promotion 结果。详见 [B9C 详细报告](b9c-qwen-frozen-policy-validation.md)。

## B9D DeepSeek / GLM Participation Screen

B9D 检查 DeepSeek 和 GLM adapters 是否能参与后续实验，同时避免把 adapter noise 变成研究主线。DeepSeek-V4-Flash 和 DeepSeek-V4-Pro 都在 `tool_call` 与 `json_schema_strict` 下完成了小型 sequential screen，`schema_valid_rate=1.0` 且 `infra_failure_rate=0.0`。Flash 的 span-narrow 更偏 recall（12 tasks 上 4 gold / 3 false），Pro 更保守（2 gold / 1 false）。GLM-5.2 基于 B9A/B6D 仍属于 supported but noisy，应保持 opt-in/exploratory，不进 critical path。这是 participation recommendation，不是 model leaderboard。详见 [B9D 详细报告](b9d-deepseek-glm-participation-screen.md)。

## B4/B9 模型稳健证据转换

B4/B9 将 `algorithm_spec`（模型无关的策略定义）与 `model_adapter`（模型 + 输出模式的健康状态）分离，并重编码 B1、B1C、B2、B3 的 live quality 聚合结果。它仅聚合、不是门控、不是仅前置条件阶段、不改变 `EvidenceCore`。`span_narrow_topk_plain_v0` 只在两个 matched Kimi adapter delta 上呈现 `low_n_directional_signal`；GLM-5.2 json_schema_strict 因没有 matched baseline delta，只能作为 secondary observed cross-family validation。固定 RMC 变体（`rmc_hybrid_v0`、`rmc_llm_pack_routed_v0`、`rmc_local_conservative_v0`）均为 `not_supported`。Qwen adapter 受 rate-limit 噪声影响，应排除在质量聚合之外。详见 [B4/B9 详细报告](b4-b9-model-robust-evidence-conversion.md)。

## B10 运行期特征审计 + Balanced Policy v1 冻结

B10 把 B6C 主 balanced candidate `ambiguous_query_weak_only_default_use_p25_action` 冻结为 algorithm spec `balanced_policy_v1_benchmark_routed`，并审计该 spec 实际读取的每一条 routing feature 的 provenance。它不跑模型、不搜索、不改变冻结策略、不改变 `EvidenceCore`。这是 **benchmark-routed 研究 algorithm spec only**（`claim_level=benchmark_routed_algorithm_spec_only`），**不是** runtime-feature-only policy，**不是** default 变更，**不是** promotion candidate。

审计明确写出：`ambiguous_or_query_noise` 即 `_ambiguous_like or _query_noise`，其中 `_ambiguous_like` 读取 benchmark 公开标签 `task_bucket`/`task_risk_tags`（benchmark public 依赖），`_query_noise` 读取确定性 runtime feature `route_features.query_noise`。默认 action `use_p25_action` 委托给 `p25.route_bucket_routed_v0`，因此继承 P25 的确定性 runtime route_features（`candidate_count`、`candidate_support_exists`）。P25 exact/unique 短路当前由 bucket labels 驱动，而不是读取 `unique_symbol_anchor` route feature。`runtime_clean=false` 且 `runtime_feature_only_mode_supported=false`，因为 `_ambiguous_like` 分支在缺少 `task_bucket`/`task_risk_tags` 时无法求值；runtime-feature-only 模式会把所有 task 路由到默认 action，`ambiguous_query_weak_only` 规则永不触发。路由不使用任何 score-private 字段（`score_private_dependencies_for_routing=[]`）；`has_gold`、`score_group`、`outcome_metrics` 仅在 action 选定后用于聚合打分。`model_adapter`、`output_mode` 以及 provider 凭证/endpoint/密钥是被排除的 adapter 层，不属于 algorithm spec。公开 artifact 仅聚合，不包含任何禁用公开键（`task_id`、`repo_id`、`candidate_id`、`path`、`span`、`snippet`、`prompt`、`response`、`gold_spans`、`provider_key`、`base_url`、`api_key`、`content_sha`）。`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`。下一步是 `balanced_policy_v1_runtime_shadow`：用纯 runtime features（`query_noise`、`candidate_support_exists`、anchor disagreement）替换 ambiguous bucket/tag 分支，并对该 benchmark-routed spec 做 action-agreement replay——该 runtime-shadow policy **不是**本 spec。详见 [B10 详细报告](b10-runtime-feature-audit.md)。

## B10B Runtime-Shadow Replay（仅 ambiguous 分支）

B10B 是 B10 冻结 `balanced_policy_v1_benchmark_routed` 之后的下一步。它不跑模型、不搜索、不调整策略质量、不默认化。它只测试一个固定预先声明的、仅依赖 runtime feature 的 shadow predicate，能否在同批记录上复现冻结 benchmark-routed spec 的 **ambiguous 分支**动作。强化后的 evaluator 携带 verdict 框架（`runtime_shadow_ambiguous_supported` + `support_claim` + `support_claim_reason`）、10 个 predeclared acceptance gates（其中 `label_driven_ambiguous_min_denominator: 10` 是 HARD gate，**不是** escape clause）、分层 agreement metrics（`target_weak_only_recall`、`target_use_p25_specificity`、`shadow_weak_only_precision`、`label_driven_ambiguous_recall_qn0`）、silent-failure 检查、直接实现的 Cohen's kappa（不依赖 numpy/sklearn），以及不一致子集上的 4 分区 outcome-equivalence 审计（仅审计；outcome 绝不回馈到路由）。leakage guard 现在除了修改 `task_bucket`/`task_risk_tags`/`has_gold`/`score_group` 之外，还会修改 `outcome_metrics`。在 synthetic fixture 上的当前 verdict 为 `runtime_shadow_ambiguous_supported=false`、`support_claim="mechanics_only_synthetic_fixture"`、`replay_source="synthetic_fixture"` —— 即 **mechanics-validated scaffold、empirical validation 待补**，而非 empirical-support claim。所有安全不变式均保留（`claim_level=ambiguous_branch_runtime_shadow_only`、`full_runtime_clean_policy=false`、`ambiguous_branch_runtime_shadow_only=true`、`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`runtime_calls_by_replay=0`、`model_calls_by_replay=0`）。empirical support 要求 B10B 在真实 CI ephemeral 记录上（`--records <path>`）运行且通过所有 predeclared gate；在此之前，B11 应被 framing 为 **exploratory prospective stress test**，**不是** “supported validation”。详见 [B10B 详细报告](b10b-runtime-shadow-replay.md)。

## B11 Prospective Blind Validation

B11 是冻结的 balanced policy `balanced_policy_v1_benchmark_routed` 在 2026-06-18 policy freeze 之后生成的新 repos 与新 tasks 上进行的首次 prospective validation，不对 policies、thresholds 或 success criteria 做任何 retuning。它比较 4 个 policies（Local baseline、P25 `p25.route_bucket_routed_v0`、Balanced v1 `balanced_policy_v1_benchmark_routed`、Conservative `rmc_local_conservative_v0`），覆盖 4 个 model families（`Kimi-K2.7-Code`、`Qwen3.6-27B`、`DeepSeek-V4-Flash`、`DeepSeek-V4-Pro`；GLM-5.2 因噪声大被排除）。Predeclared success/failure/partial criteria 带有显式 overall 与 worst-group thresholds（`Δgold_span`、`ΔSpanF0.5`、`ΔPFP`、`Δfalse_spans`、`ΔLLM_calls`），以及 `RobustUtility` = `min_group(SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency)` 聚合，均已在任何 live runs 之前于 preregistration 中冻结。B10B `--records` 已集成到 CI 中，在每次 B11 run 之后运行，给 B10B 带来首次 empirical validation。B11 是 prospective stress test，不是 promotion step：`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`。plan、CI workflow 定义与 report-aggregator skeleton 可自主完成；实际 live LLM runs 需要用户 `workflow_dispatch` 触发且 `enable_remote_models=true`。详见 [B11 详细报告](b11-prospective-blind-validation.md)。

### B11 official integrated matrix 结果（2026-06-18）

B11 official integrated matrix 在 8 个 public repo slice 与 4 个 model family 上完成 32/32 runs（两次 transient `provider_status` 失败已重试），共 384 条记录。该聚合是已下载 aggregate-only public B11/B10B artifacts 的 **derived aggregate rollup**（`eval/b11_matrix_combiner.py` → `artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`）；未读取任何 raw records、paths、prompts、responses、snippets 或 private labels。Verdict 计数：`success 8`、`partial 23`、`failure 1`；aggregate verdict `partial_with_failure`。

Overall weighted means（384 条记录）——`local_baseline` / `p25` / `balanced_v1` / `conservative`：`gold_span 0.377604 / 0.247396 / 0.244792 / 0.125000`；`false_span 1.203125 / 0.236979 / 0.182292 / 0.236979`；`span_f0_5 0.062197 / 0.064538 / 0.062639 / 0.023611`；`PFP 0.083333 / 0.020833 / 0.000000 / 0.000000`；`model_calls 0.0 / 0.958333 / 0.604167 / 0.000000`。balanced_v1 相对 P25 的 deltas：`Δgold_span -0.002604`、`Δfalse_span -0.054688`、`ΔSpanF0.5 -0.001899`、`ΔPFP -0.020833`、`Δmodel_calls -0.354167` —— balanced_v1 平均上保持近乎一致的 SpanF0.5/gold，同时减少了 false spans、PFP 与 model calls。按 model family：`deepseek_flash`（partial 6 / success 2）、`deepseek_pro`（partial 5 / success 3）、`kimi`（partial 5 / success 2 / **failure 1** —— 一个 `py_fastapi` slice 超出 `failure_spanf05_delta`）、`qwen`（partial 7 / success 1）。

B10B 在每次 B11 run 之后运行（32/32 报告）；所有 run 的 `runtime_shadow_ambiguous_supported=false`，`support_claim="empirical_replay_support_pending"`（原因 `insufficient_label_driven_denominator`；观测到的最大 `label_driven_ambiguous_denominator_qn0=3`，远低于 10 条记录的 hard gate），因此 B10B runtime-shadow predicate 仍为 empirical-pending。

**结论**：B11 为 **mixed/partial**。该结果加强了 algorithm-candidate 信号（balanced_v1 平均上保持与 P25 近乎一致的 SpanF0.5/gold，同时减少 false spans、PFP 与 model calls），但**并未**证明一个 runtime-clean 的 general algorithm，**未** promotion，**未**改变 default，**未**改变 EvidenceCore semantics。唯一的 Kimi 失败 slice 与 B10B denominator-pending predicate 是 B12（mechanism decomposition）需要解决的开放问题。建议下一步：B12。


## B12 Mechanism Decomposition

B12 是继 B11 之后的 mechanism-decomposition 阶段。它通过 5 个 ablation variants（A full balanced、B deterministic call-reduction control、C ambiguous weak_only only[按构造 ≡A]、D P25 default、E random same-count call-reduction control）与 4 个 predeclared hypotheses（H1 ambiguous routing、H2 LLM call reduction、H3 P25 fallback sufficiency、H4 model-specific）分解**为什么**冻结的 balanced policy `balanced_policy_v1_benchmark_routed`（B10）有效（若 B11 证实其泛化）。B12 为 replay-only（每条 P21 record 已含 per-strategy outcomes，故每个 variant 通过选取对应 per-strategy outcome 计算；evaluator 不产生 live LLM calls）。截至 C1 slice（2026-06-19），B12 **现在通过共享 C1 adapter**（`eval/c1_private_records.py`）**消费 private per-record P21 records** —— `--input` 路径**不再是 stub**；它产出真实 aggregate-only report，含 5 个 variants 的 per-variant replay、count reporting（`total_records` / `complete_records` / `balanced_branch_count` / `p25_llm_eligible_count` / `actual_call_avoided_count` / `random_selected_count`）及 scientific verdict。

**Taint model + actual-call-avoided 定义。** C1 adapter 使用三类 taint model：(1) runtime-clean `route_features`；(2) benchmark route labels（`task_bucket`、`task_risk_tags`）—— 用于分析冻结的 benchmark-routed policies，但**非** runtime-clean；(3) score/outcome/private fields（`score_group`、per-strategy outcomes、`p31_score_gold`、`p31_candidate_pools`、`p33b_anchor_subtypes`）—— 仅因文件为 runner-temp/private 而被允许。`balanced_branch_set` = balanced v1 `ambiguous_or_query_noise` predicate 命中的 records（读取 benchmark labels —— 这正是 balanced_v1 为 benchmark-routed、**而非** runtime-clean 的原因）。`p25_llm_subset` = D/P25 会选择 LLM strategy 的 records。`actual_call_avoided_set = balanced_branch_set ∩ p25_llm_subset` —— balanced routing 实际避免了 D 本会发起的 LLM call 的 records（B-variant 干预集合）。E 使用单个冻结 seed（`e_random_seed=20260618`）从 `p25_llm_subset` hash-select 相同数量（注明单 seed 局限；seed-averaging 延后）。

**修订后（C1）H1-H3 criteria** —— 在任何 empirical replay 之前：balanced policy 预期**保持** gold/span 与 D 大致持平（**不**要求增加）、**减少** false/PFP/model_calls 相对 D，并**优于** B/E 在 false/PFP/RobustUtility 上以支持 targeted ambiguous routing。A **不**被要求增加 gold/span。H4 在已知 model families 少于 2 个时为 `insufficient_data`。**H4 insufficient_data 不阻断 H1-H3 mechanism verdict** —— report 携带 `h4_insufficient_data_blocks_overall_verdict=false` 和 `h1_h3_verdict_independent_of_h4=true`，因此单 model B12 CI slices 可评估 H1-H3，而 H4 需要多 model 聚合。

B12 是 mechanism decomposition，**不是** promotion step：`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`。public B12 report 为 **aggregate-only** —— 不输出 task_id、raw/private repo_id、path、span、candidate_id、content_sha、per-record hash、P31/P33 block 或 raw prompt/response/snippet/provider field（仅 COUNTS）。Aggregate group metrics 只使用 synthetic/preregistration fixtures 的 public preregistered repo labels，或 private `--input` replays 的 anonymized `public_repo_group_NNN` labels。Scientific verdicts（`supported` / `refuted` / `partial` / `insufficient_data`）返回 exit 0；mechanical/privacy/schema 错误返回 nonzero；scientific no-result 是有效 CI 结论，**不**使 CI 失败。详见 [B12 详细报告](b12-mechanism-decomposition.md)。

### C2 B12 CI canary（2026-06-19）

C2 在真实 CI run 上验证了新的 C1/B12 路径：`py_fastapi × Kimi × round_robin_public_buckets × 12 tasks`（run `27816890557`）产出 B12 report，字段为 `replay_source="ci_ephemeral_records"`、`total_records=12`、`complete_records=12`、`incomplete_record_count=0`、`balanced_branch_count=4`、`p25_llm_eligible_count=10`、`actual_call_avoided_count=4`、`random_selected_count=4`。public report 仍为 aggregate-only 且 privacy-safe。该 canary verdict 为 `partial`：H1 `refuted`、H2 `refuted`、H3 `supported`、H4 `insufficient_data`（single model family）。这只是 canary-level mechanism result，不是完整 B12 结论。下一步是对 B11 repo/model cells 跑完整 B12 matrix。

### C2/B12 official matrix aggregate（2026-06-19）

**C2/B12 official matrix aggregate** 把 28 个 analyzable 的 per-run B12 `b12-mechanism-decomposition-report-v0` 公共 aggregate 报告合并为一份 derived aggregate（`eval/b12_matrix_combiner.py` → `artifacts/b12_mechanism_decomposition/b12_matrix_aggregate_report.json`，schema `b12-mechanism-matrix-aggregate-report-v0`）。它是有界的 aggregate-only rollup：只读取已下载的公共 B12 报告，不进行 provider calls（`new_provider_calls=0`）、不进行 policy search（`policy_search_performed=false`）、不进行 threshold tuning，也**不**做 promotion/default/runtime-clean/EvidenceCore-semantics 声明。覆盖：`28/32` cells analyzable；`4` 个 `ts_vite` cells 因 `coverage_insufficient_no_remote_llm_snippet` 被排除（即使 `max_tasks=24` 也未 exercise remote LLM snippets；这是覆盖缺口，**不是** B12 mechanism failure）。Records：共 `336`（每 cell `12`）。Verdict counts：`partial: 28`。Hypothesis status counts：H1 `supported: 3 / refuted: 25`、H2 `supported: 8 / refuted: 20`、H3 `supported: 28`、H4 `insufficient_data: 28`（每个 cell 都是 single-model-family slice，故 H4 需跨 cell 的 multi-model aggregation；按设计 H4 insufficient_data **不**阻断 H1-H3 verdict）。Record-weighted A（full balanced）deltas vs D（P25 default）：`Δgold_span 0.0`、`ΔSpanF0.5 0.0`、`Δfalse_span -0.029762`、`ΔPFP -0.014881`、`Δmodel_calls -0.333333`；vs E（random call reduction）：`Δgold_span -0.044643`、`ΔSpanF0.5 0.001569`、`Δfalse_span -0.592262`、`ΔPFP -0.026786`、`Δmodel_calls 0.0`；vs B（deterministic call reduction）：`Δgold_span 0.0`、`ΔSpanF0.5 0.0`、`Δfalse_span -0.130952`、`ΔPFP -0.035714`、`Δmodel_calls 0.0`。Weighted mean robust utility (A)：`0.054155`。Replay count totals：`balanced_branch_count=112`、`p25_llm_eligible_count=324`、`actual_call_avoided_count=112`、`random_selected_count=112`。Overall verdict：`partial_with_coverage_exclusions` —— **不是**全局 `supported` verdict，**不** promotion、**不** default change、**不** runtime-clean general algorithm claim、**不** EvidenceCore semantics change。所有 safety flags：`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`policy_search_performed=false`、`runtime_clean_policy_supported=false`、`new_provider_calls=0`、`candidate_not_fact=true`。建议下一步：B13 distributionally robust policy search **需谨慎**（B13 绝不可被当作被 B12 supported verdict 授权），或未来重跑 B12 matrix 以闭合 `ts_vite` 覆盖缺口。详见 [B12 详细报告](b12-mechanism-decomposition.md)。

### B12 public aggregate mechanism screen（2026-06-18）

新增一个有界的 **public-aggregate mechanism screen**（`eval/b12_public_aggregate_screen.py` → `artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`）。这**不是**完整的 B12 per-record replay。explorer/oracle 的结论是：从当前的 public B11 aggregate 无法完成 full B12 replay —— 它缺少 per-record route decisions、ambiguous-subset membership、deterministic call-reduction variant B、random call-reduction variant E 以及 `weak_candidate_only` per-strategy outcomes。该 screen 因此发出**逐 hypothesis 的 screen status**，从不发出单一全局 `supported` verdict，并对 aggregate deltas 应用**相同的**冻结数值门槛（±0.02 approx-equality、0.05 H4 family-spread）。

B11 official matrix aggregate（32 runs / 384 records）的逐 hypothesis screen 结果：

- **H1（ambiguous routing）：`inconclusive_unavailable_ablation_controls`** —— public aggregate 无 per-record route decisions、无 ambiguous subset、无 variants B/E。该 screen **不**声称 H1 support。
- **H2（LLM call reduction）：`reduced_calls_observed_causal_mechanism_inconclusive`** —— `Δmodel_calls -0.354167`，因此描述性观察到 reduced calls，但缺少 variant E（random call reduction）无法归因 causal mechanism。该 screen **不**声称 H2 causal support。
- **H3（P25 fallback sufficiency）：`aggregate_primary_parity_supported_consistent_with_h3`** —— `Δgold_span -0.002604` 与 `ΔSpanF0.5 -0.001899` 均在 ±0.02 内，因此 aggregate primary parity 成立（与 H3 在 aggregate 层面一致）。这**不是**完整的 H3 supported verdict：从 aggregate deltas 无法得出 per-record fallback sufficiency 结论。
- **H4（model-specific）：`family_gold_spread_not_supported_model_repo_interaction_inconclusive`** —— per-family gold_span delta spread 为 `0.010417`（deepseek_flash 0.0、deepseek_pro 0.0、kimi -0.010417、qwen 0.0），at or below 0.05 family-level threshold，因此 H4 在 predeclared family-level gold-span spread criterion 下 **not supported**。这**不是**完整的 H4 refutation：Kimi `py_fastapi` failure slice 意味着 model×repo interaction 在无 per-record 数据时仍 inconclusive。

Safety fields 原样保留：`aggregate_only_public_artifact=true`、`candidate_not_fact=true`、`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`new_provider_calls=0`。该 screen **不**声称 promotion、default change、runtime-clean general algorithm、H1 support、H2 causal support 或 full H4 refutation。建议下一步：future ephemeral-record B12 replay，或 B13 robust policy search **谨慎进行**（B13 不得被视为由 B12 supported verdict 授权）。详见 [B12 详细报告](b12-mechanism-decomposition.md)。

## B13 Distributionally Robust Policy Search

B13 是继 B12 之后的 distributionally-robust policy-search 阶段。它搜索一个含 6-10 条 rules 的 policy，仅使用 runtime-observable `route_features`（无 benchmark-private labels、无 score-private fields、`algorithm_spec` 中无原始 model names），优化 worst-group utility 或 `CVaR_20%`，并通过 3 个 rotating leave-one-model-family-out rotations 验证。Allowed actions 为 LLM-free（`weak_only`、`use_p25_action`、`use_local_baseline`）；search method 为 bounded grid + greedy refinement（pure Python）。B13 **是** policy-search *stage*（`stage_is_policy_search=true`），但当前 skeleton **不**执行 empirical policy search（`empirical_policy_search_performed=false`）；synthetic-fixture / `--input` stub 报告设置 `policy_search_performed=false`、`policy_found=false`、`rotations_evaluated=false`、`rotations_defined=true`、`rotation_count=3`、`winner_declared=false`，使该公共 artifact 不会被误读为 empirical B13 run。synthetic / stub 报告仅发出 rotation *定义*（无 per-rotation 的 `passes=true` / `all_rotations_pass=true` / `test_worst_group_utility` / `delta_vs_b10_reference`）；skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或 `not_implemented`（ci_ephemeral_records stub）——`success` / `failure` / `partial` 保留给未来 `policy_search_performed=true` 的 empirical 路径，该路径在当前 skeleton 中**不**存在。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的路径。其结果**不**被 promoted（`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`）；它们是 research candidates，输入 B14（uncertainty calibration）与 B16（downstream agent evaluation）。`--input` 路径为 stub（verdict `not_implemented`）；B13 需要 B11 live runs 的 P21 records。真实的 B13 distributionally robust policy search 无法仅凭公共 aggregates 完成：位于 `eval/b13_public_aggregate_feasibility_screen.py` 的 bounded public-aggregate feasibility / no-go screen 读取已发布的 B11 aggregate + B12 public screen，在 `artifacts/b13_dro_policy_search/` 下发出 `verdict=no_go_public_aggregate_only`（或 `insufficient_data_public_aggregate_only`），并设置 `policy_found=false`、`rotations_evaluated=false`、`full_b13_possible_from_public_artifacts=false`；它从不选择 rule，从不声明 winner，也从不声称 empirical policy search。B13 是 B10-B19 Breakthrough Sprint 中最后一个 "immediate priority" item。详见 [B13 详细报告](b13-distributionally-robust-policy-search.md)。

## B14 Uncertainty Calibration

B14 是继 B13 之后的 uncertainty-calibration 阶段。它从三个允许的 signal families —— local candidate signals、model output structure 与 cross-model disagreement —— 产生一个**model-independent** 的每条记录 uncertainty score（绝不针对特定 model name 进行校准），并用 risk-coverage、selective risk、ECE 与 PFP-at-fixed-coverage 指标评估该 score，并附 worst-group 报告与 rotating leave-one-model-family-out 验证。signal families 受限：**无** benchmark-private labels（`task_bucket`、`task_risk_tags`）、**无** score-private fields（`has_gold`、`score_group`、`outcome_metrics`）、**无**原始 model names 在 `algorithm_spec` 中（仅抽象 `family_slots`）。per-record outcomes（所选 span 是否正确）是 calibration TARGET，绝非 uncertainty signal feature。frozen coverage levels 为 `[0.50, 0.70, 0.90, 0.95, 0.99]`；ECE 使用 `[0, 1]` 上 15 个 equal-width bins；split protocol 按 (model_family, repo) 分层，`calibration_fraction=0.50` / `test_fraction=0.50`（recalibration 仅在 calibration split 上；test split held out 并仅报告一次）。predeclared success/partial/failure criteria 使用 test-split ECE（≤ 0.05）、coverage=0.90 处 selective risk（≤ 0.10）、coverage=0.90 处 worst-group selective risk（≤ 0.15）与 0.02 approx-equality / strictly-greater rotation threshold，并附 `CVaR_20%` worst-group tail average。

B14 **是** uncertainty-calibration *stage*（`stage_is_uncertainty_calibration=true`），但当前 skeleton **不**执行任何 empirical uncertainty calibration（`uncertainty_calibration_performed=false`）；synthetic-fixture / `--input` stub 报告设置 `calibrated_model_claim=false`、`per_record_inputs_available=false`、`uncertainty_score_found=false`、`rotations_evaluated=false`、`rotations_defined=true`、`rotation_count=3`、`winner_declared=false`、`metrics_evaluated=false`、`no_fake_metrics_from_aggregate_means=true`，使该公共 artifact 不会被误读为 empirical B14 calibration。**CRITICAL**：skeleton **绝不可**从 aggregate means 计算伪造的 ECE / risk-coverage / selective-risk / PFP-at-coverage 指标；synthetic fixture 仅验证 metric NAMES 与 gates（无 per-record (uncertainty, outcome) pairs，无 computed metric values）。synthetic / stub 报告仅发出 rotation *定义*（无 per-rotation 的 `passes=true` / `test_ece` / `test_selective_risk` / `test_risk_coverage_curve` / `test_pfp_at_fixed_coverage` / `delta_vs_reference`）；skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或 `not_implemented`（ci_ephemeral_records stub）——`success` / `failure` / `partial` 保留给未来 `uncertainty_calibration_performed=true` 的 empirical 路径，该路径在当前 skeleton 中**不**存在。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的路径。`--input` stub 要求显式 `--out`，并拒绝写入 checked-in B14 report。其结果**不**被 promoted（`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`）；它们是 research candidates，输入 B16（downstream agent evaluation）与未来 selective-abstention policy 工作。真实的 B14 calibration 无法仅凭公共 aggregates 完成：位于 `eval/b14_public_aggregate_feasibility_screen.py` 的 bounded public-aggregate feasibility / no-go screen 读取已发布的 B11 + B12 + B13 artifacts，在 `artifacts/b14_uncertainty_calibration/` 下发出 `verdict=no_go_public_aggregate_only`（或 `insufficient_data_public_aggregate_only`）；它从不声称 empirical calibration，从不计算 metric，从不选择 uncertainty score，也从不声明 winner。missing inputs 为：无 per-record uncertainty scores、无 per-record outcomes、无 paired cross-model outputs、无 schema-repair per-call rows、无 candidate score distributions/entropy、无 calibration/test split、无 ECE bins、无 fixed-coverage thresholds。B11 mixed/partial、B12 aggregate-screen only 与 B13 no-go 原样 carry forward。详见 [B14 详细报告](b14-uncertainty-calibration.md)。


## B15 Context Pack Policy

B15 是继 B14 之后的 context-pack-policy 阶段。目标是产出一个 **frozen、preregistered 的 PackPolicy**，将 `(role, runtime_state, model_profile)` 映射到一组确定的 **atom set**（context pack 应当暴露的 pack-layout atoms），并基于 B11/B13 live runs 的 per-record pack atom flags + per-record outcomes + role + runtime_state + model_profile + group membership 进行验证。B15 是一个 **bounded planning / feasibility 阶段**，**不是** empirical atom-level ablation。Roles 为 FROZEN（`span_narrow`、`filter_reject`、`request_more_context`、`source_test_disambiguation`）；atom registry 为 FROZEN（`signature`、`matched_lines`、`raw_snippet`、`neighbor_context`、`scores`、`provenance`、`hard_distractor`、`same_file_competitor`、`path_kind_flag`）；runtime_state 契约 label-free 且 model-name-free；model_profile 抽象使用 abstract capability slots（`profile_slot_a`..`profile_slot_d`）+ capability descriptors —— **无** raw model names 在 `algorithm_spec` 中。experimental structure FROZEN 为 4 个 stages：`no_llm_feasibility` → `fractional_factorial_live_atom_screen`（atom registry 上的 resolution-IV fraction，非完整 2^9 factorial）→ `freeze_candidate_policy` → `fresh_validation`（按 `(model_family, repo, role)` stratified，`atom_screen_fraction=0.50` / `fresh_validation_fraction=0.50`，held out 且 reported once）。Hard gates（FROZEN）：`privacy_gate`、`leakage_gate`、`adapter_health_gate`、`randomization_balance_gate`、`denominator_gate`（每 cell 最小 30）、`token_budget_gate`、`promotion_false_gate`。Metric registry（FROZEN，9 个 names）：`atom_effect_per_atom`、`role_pack_outcome`、`runtime_state_pack_outcome`、`model_profile_pack_outcome`、`worst_group_pack_outcome`、`cvar_20_pack_outcome`、`token_budget_parity`、`denominator_per_atom_role_model`、`randomization_balance_per_arm` —— 每个 metric 都需要 per-record (atom_flag, outcome, role, runtime_state, model_profile) tuples；**没有** metric 可从 aggregate means 计算。

B15 **是** context-pack-policy *stage*（`stage_is_context_pack_policy=true`），但当前 skeleton **不**执行任何 empirical atom ablation（`atom_ablation_performed=false`），也**不**进行 PackPolicy learning（`pack_policy_learned=false`）；synthetic-fixture / `--input` stub 报告设置 `per_record_inputs_available=false`、`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`new_provider_calls=0`、`candidate_policy_frozen=false`、`stages_evaluated=false`、`stages_defined=true`、`stage_count=4`、`winner_declared=false`、`metrics_evaluated=false`、`no_fake_atom_effects_from_aggregate_means=true`，使该公共 artifact 不会被误读为 empirical B15 PackPolicy 结果。**CRITICAL**：skeleton **绝不可**从 aggregate means 计算伪造的 atom-effect / role-pack-outcome / worst-group-pack-outcome 指标；synthetic fixture 仅验证 metric NAMES 与 gates（无 per-record (atom_flag, outcome) pairs，无 computed metric values）。synthetic / stub 报告仅发出 stage *定义*（无 per-stage 的 `passes=true` / `atom_effect_per_atom` / `role_pack_outcome` / `worst_group_pack_outcome`）；skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或 `not_implemented`（ci_ephemeral_records stub）——`success` / `failure` / `partial` 保留给未来 `atom_ablation_performed=true` / `pack_policy_learned=true` 的 empirical 路径，该路径在当前 skeleton 中**不**存在。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的路径；`--input` stub 要求显式 `--out`，并拒绝写入 checked-in B15 report。其结果**不**被 promoted（`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`pack_policy_learned=false`、`atom_ablation_performed=false`）；它们是 research candidates，输入 B16（downstream agent evaluation）与未来 context-pack routing 工作。真实的 B15 PackPolicy validation 无法仅凭公共 aggregates 完成：位于 `eval/b15_public_aggregate_prior_screen.py` 的 bounded public-aggregate prior / no-go screen 读取已发布的 B2 contrastive-pack experiment（仅检查存在性）、B14 public-aggregate feasibility report，以及当存在时的 B4-B9 / P21-G / P49 公共 aggregates，在 `artifacts/b15_context_pack_policy/` 下发出 `verdict=prior_screen_only`（或当 B2 缺失时 `no_go_public_aggregate_only`）；它从不声称 empirical PackPolicy learning，从不计算 atom-effect metric，从不冻结 candidate policy，也从不声明 winner。已发布的 B2 contrastive-pack experiment 是 single-model、low-N（每个 layout 24 tasks）、aggregate-only 的 pack-layout 比较；它**仅**可作为 `low_n_single_model_aggregate_directional_prior`（`b2_prior_usable=true`、`b2_prior_claim_level=low_n_single_model_aggregate_directional_prior`），**不能**作为 atom-level causality、role-specific PackPolicy、calibrated policy、cross-model robustness、hard-distractor 通用规则、scores/provenance 通用胜利、default change、promotion 或 EvidenceCore change。missing inputs 为：无 per-record pack atom flags、无 per-record outcomes、无 role-specific paired outputs、无 model_profile paired blocks、无 randomized atom assignment、无 randomization balance stats、无 denominator by atom/role/model、无 token-budget matched controls。B14 no-go 原样 carry forward；它**不**授权 promotion、default change、PackPolicy promotion 或 runtime-clean general algorithm。详见 [B15 详细报告](b15-context-pack-policy.md)。

---

## B16 Downstream Coding-Agent Evaluation

B16 是继 B15 之后的 downstream-coding-agent-evaluation 阶段。目标是产出一个 **frozen、preregistered 的 paired within-task randomized controlled trial (RCT)**，衡量 candidate retrieval/context variant 是否能改进下游 coding agent（而非仅 retrieval aggregates），基于真实、paired、isolated-workspace 的 agent runs。B16 是一个 **bounded planning / feasibility 阶段**，**不是** live downstream agent evaluation。Arms 为 FROZEN 的 primary（`control_current_retrieval_v0`、`balanced_v1_retrieval_candidate`）、exploratory（`candidate_pack_policy_v0`，仅当真实 B15 candidate 存在时才包含 —— B15 skeleton 不产出 candidate，故此 arm 默认 EXCLUDED）与 debugging-only（`gold_context_ceiling`，从不 promoted）。Task types 为 FROZEN（`bug_localization`、`small_code_edit`、`test_selection`、`multi_file_feature`、`refactor_impact`）。paired RCT 强制 paired within-task randomization、isolated fresh workspace per run、randomized arm order、除 retrieval/context variant 外相同的 budget/tools/prompt，以及 no cross-run memory。Hard gates（FROZEN）：`feasibility_gate`、`denominator_gate`（每 (task_type, arm) cell 最小 30）、`leakage_gate`、`operational_parity_gate`（token-budget match tolerance 0.10、latency match tolerance 0.15、除 retrieval variant 外相同 tools/budget/prompt、isolated fresh workspace、randomized arm order、no cross-run memory）、`privacy_gate`、`promotion_false_gate`。Metric registry（FROZEN，8 个 names）：`solve_rate`、`correct_file_before_first_edit`、`wrong_file_edits`、`tool_calls_before_first_edit`、`context_tokens`、`tests_pass`、`latency`、`cost` —— 每个 metric 都需要 per-run paired agent outputs（event logs、patches/diffs、test execution results、solve labels、first-file-before-first-edit events、wrong-file-edit annotations、tool-call/token/latency/cost rows、isolated workspace proof、randomized arm order、task oracle/hidden-test manifest）；**没有** metric 可从 retrieval aggregates 计算。

B16 **是** downstream-agent-evaluation *stage*（`stage_is_downstream_agent_evaluation=true`），但当前 skeleton 不执行任何 live downstream agent runs（`downstream_agent_runs_performed=false`）、不执行 patch execution（`patch_execution_performed=false`）、不评估 agent-behavior metrics（`agent_behavior_metrics_evaluated=false`），也不评估 solve rate（`solve_rate_evaluated=false`）；synthetic-fixture / `--input` stub 报告设置 `per_record_inputs_available=false`、`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`retrieval_variant_promoted=false`、`policy_search_performed=false`、`quality_strategy_tuned=false`、`new_provider_calls=0`、`candidate_retrieval_variant_frozen=false`、`stages_evaluated=false`、`stages_defined=true`、`stage_count=4`、`winner_declared=false`、`metrics_evaluated=false`、`no_fake_downstream_metrics_from_retrieval_aggregates=true`，使该公共 artifact 不会被误读为 empirical B16 downstream agent 结果。**CRITICAL**：skeleton **绝不可**从 retrieval aggregates 计算伪造的 solve-rate / correct-file-before-first-edit / wrong-file-edits / tool-call / token / latency / cost 指标；synthetic fixture 仅验证 metric NAMES 与 gates（无 per-run paired agent outputs，无 computed metric values）。synthetic / stub 报告仅发出 stage *定义*（无 per-stage 的 `passes=true` / `solve_rate` / `correct_file_before_first_edit` / `wrong_file_edits`）；skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或 `not_implemented`（ci_ephemeral_records stub）——`success` / `failure` / `partial` 保留给未来 `downstream_agent_runs_performed=true` / `solve_rate_evaluated=true` 的 empirical 路径，该路径在当前 skeleton 中**不**存在。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的路径；`--input` stub 要求显式 `--out`，并拒绝写入 `artifacts/b16_downstream_agent_evaluation/` 内的任何路径。其结果**不**被 promoted（`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`retrieval_variant_promoted=false`、`downstream_agent_runs_performed=false`、`patch_execution_performed=false`、`agent_behavior_metrics_evaluated=false`、`solve_rate_evaluated=false`）；它们是 research candidates only。真实 B16 downstream agent evaluation 无法仅凭公共 aggregates 完成：bounded public-aggregate feasibility / no-go screen（`eval/b16_public_aggregate_feasibility_screen.py`）读取已发布的 B11 matrix + B12 + B13 + B14 + B15 公共 screens，并在 `artifacts/b16_downstream_agent_evaluation/` 下发出 `verdict=no_go_public_aggregate_only`（或 `insufficient_data_public_aggregate_only`）；它从不声称 downstream agent value，从不从 retrieval aggregates 计算 downstream metric，从不 freeze candidate retrieval variant，从不 promote retrieval variant，也从不声明 winner。B10-B15 retrieval/context candidate research 是 retrieval research；它**不**证明 downstream coding-agent value。Retrieval improvements **不是** downstream agent improvements；B15 PackPolicy **不是** downstream agent improvement。missing inputs 为：无 live paired agent runs、无 agent event logs、无 patches/diffs、无 test execution results、无 solve labels、无 first-file-before-first-edit events、无 wrong-file-edit annotations、无 tool-call/token/latency/cost per run、无 randomized arm order、无 isolated workspace proof、无 task oracle/hidden-test manifest、无 operational parity proof。B11 `partial_with_failure` 与 B12/B13/B14/B15 no-go 或 screen-only statuses 原样 carry forward。详见 [B16 详细报告](b16-downstream-agent-evaluation.md)。

---

## B17 QuIVer Systems Track

B17 是继 B16 之后的 quiver-systems-track 阶段。目标是产出一个 **frozen、preregistered 的 backend bakeoff**，在 **frozen candidate-quality policy** 下对比 ANN backend candidates 的 backend systems metrics（latency、memory、build time、update cost、index size），使 backend quality 不会在对比 systems 数据时被静默放宽。B17 是一个 **bounded planning / diagnostic 阶段**，**不是** QuIVer production backend，**不是** ANN quality promotion，**不是** default change，**不是** EvidenceCore semantics change。Candidate backends 为 FROZEN 的 reference（`flat_f32_reference`）、candidate（`hnsw_candidate`、`bq_topk_f32_rerank_candidate`、`quiver_vamana_prototype` —— QuIVer/Vamana graph backend 终极目标，**未实现**）与 optional-store（`tdb_vector_candidate`，仅 store/backend candidate，**非** Evidence source，默认 EXCLUDED）。Candidate-set equivalence constraints 为 FROZEN（`candidate_set_overlap_at_k` ≥ 0.90 at K=[10,50,100]、`gold_retention_delta` tolerance 0.05、`primary_false_positive_delta` guard 0.05、`span_f0_5_delta` tolerance 0.05、`citation_validity` = 1.0、`stale_evidencecore_rejection_required`、`no_default_expansion_required`）。Hard gates（FROZEN）：`quiver_graph_implementation_gate`、`backend_parity_gate`、`candidate_set_equivalence_gate`、`evidencecore_materialization_gate`、`stale_citation_gate`、`privacy_gate`、`promotion_false_gate`。Metric registry（FROZEN，11 个 names）：`candidate_set_overlap_at_k`、`gold_retention_delta`、`span_f0_5_delta`、`primary_false_positive_delta`、`p50_latency`、`p95_latency`、`hot_memory`、`build_time`、`update_cost`、`index_size`、`recall_tolerance_violation_count` —— 每个 metric 都需要 per-backend systems bakeoff inputs（index build records、search latency records、hot memory records、index size records、update cost records、candidate-set-at-K records、gold retention records、span F0.5 records、PFP records、citation validity records、stale rejection records、EvidenceCore rejection records、recall tolerance violation records、randomized run order proof、isolated index workspace proof、shared frozen candidate-quality manifest）；**没有** metric 可从现有 R33/R34/R36/R24 diagnostics 计算。

B17 **是** quiver-systems-track *stage*（`stage_is_quiver_systems_track=true`），但当前 skeleton 不执行 ANN backend bakeoff（`ann_backend_bakeoff_performed=false`）、不验证 candidate-set equivalence（`candidate_set_equivalence_validated=false`）、不实现 QuIVer/Vamana graph（`quiver_graph_implemented=false`）、不 promote backend quality（`backend_quality_promoted=false`）；synthetic-fixture / `--input` stub 报告设置 `promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`retrieval_policy_changed=false`、`metrics_evaluated=false`、`new_provider_calls=0`、`no_fake_ann_metrics_from_diagnostics=true`，使该公共 artifact 不会被误读为 empirical B17 systems bakeoff 结果。**CRITICAL**：skeleton **绝不可**从现有 R33/R34/R36/R24 diagnostics 计算伪造的 candidate_set_overlap_at_k / gold_retention_delta / span_f0_5_delta / primary_false_positive_delta / p50_latency / p95_latency / hot_memory / build_time / update_cost / index_size / recall_tolerance_violation_count 指标；synthetic fixture 仅验证 metric NAMES 与 gates（无 per-backend systems bakeoff inputs，无 computed metric values）。synthetic / stub 报告仅发出 stage *定义*（无 per-stage 的 `passes=true` / `candidate_set_overlap_at_k` / `gold_retention_delta` / `p50_latency` / `hot_memory` / `build_time` / `index_size`）；skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或 `not_implemented`（ci_ephemeral_records stub）——`success` / `failure` / `partial` 保留给未来 `ann_backend_bakeoff_performed=true` / `candidate_set_equivalence_validated=true` / `quiver_graph_implemented=true` 的 empirical 路径，该路径在当前 skeleton 中**不**存在。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的路径；`--input` stub 要求显式 `--out`，并拒绝写入 `artifacts/b17_quiver_systems_track/` 内的任何路径。bounded public-systems diagnostic carry-forward / no-go screen（`eval/b17_public_systems_diagnostic_screen.py`）读取已发布的 R33 readiness + R34/R36 anchor-proto + real-provider P3/P4 quiver diagnostics + 可选 R24 QuIVer/TDB/dense probe，并发出 `verdict=no_go_quiver_graph_missing`（或 `diagnostic_carry_forward_only`）；它从不声称 QuIVer implementation，从不从 diagnostics 计算 ANN metric，从不 promote backend，从不修改 retrieval policy，也从不声明 winner。现有 R33/R34/R36/R24 diagnostics 是 **diagnostic-only carry-forward** —— 它们**不**是 quality proof，**不**是 promotion evidence；它们**不**实现 QuIVer/Vamana graph backend、**不**包含 HNSW run、**不**包含 candidate-set equivalence matrix across backends。详见 [`b17-quiver-systems-track.md`](b17-quiver-systems-track.md)。

---

## B18 OOD / Temporal Evaluation

B18 是继 B17 之后的 ood-temporal-evaluation 阶段。目标是产出一个 **frozen、preregistered 的 OOD / temporal evaluation**，在 **no-retuning protocol** 下（no policy search、no quality strategy tuning、no retrieval policy change、no EvidenceCore semantics change、no default change、no promotion）跨五个 FROZEN split axes（`temporal_split`、`repo_split`、`language_split`、`model_family_split`、`adversarial_split`）评估 retrieval / candidate / Evidence pipeline，使 in-distribution average 不会被误读为 OOD / temporal generalization。B18 是一个 **bounded preregistration + public-aggregate no-go screen 阶段**，**不是** 真正的 OOD / temporal evaluation，**不是** policy search，**不是** quality strategy tuning，**不是** default change，**不是** EvidenceCore semantics change，**不是** promotion。Split axes 为 FROZEN（`temporal_split`、`repo_split`、`language_split`、`model_family_split`、`adversarial_split`）。No-retuning protocol 为 FROZEN（`no_retuning_protocol=true`、`no_policy_search=true`、`no_quality_strategy_tuning=true`、`no_retrieval_policy_change=true`、`no_evidencecore_semantics_change=true`、`no_default_change=true`、`no_promotion=true`）。Hard gates（FROZEN）：`per_record_data_gate`、`time_axis_gate`、`commit_chronology_gate`、`no_retuning_gate`、`adversarial_holdout_gate`、`temporal_holdout_gate`、`evidencecore_materialization_gate`、`stale_citation_gate`、`privacy_gate`、`promotion_false_gate`。Metric registry（FROZEN，13 个 names）：`ood_generalization_gap`、`temporal_holdout_delta`、`repo_holdout_metric`、`language_holdout_metric`、`model_family_holdout_metric`、`adversarial_robustness_score`、`worst_group_metric`、`cvar_tail_metric`、`per_cell_denominator`、`temporal_split_integrity`、`no_retuning_proof_metric`、`citation_validity`、`stale_evidencecore_rejection_rate` —— 每个 metric 都需要 per-record OOD / temporal inputs（per-record records、per-record time index、per-record commit chronology、per-record repo / language / model_family axes、per-record task category、per-record adversarial holdout membership、per-record temporal holdout membership、per-record outcome label、per-record citation validity、per-record stale rejection、per-record EvidenceCore rejection、per-record randomized run order proof、per-record no-retuning proof、shared frozen evaluation protocol manifest）；**没有** metric 可从 B11 aggregate means 或 R15 / R20 / R26 repo locks 计算。

B18 **是** ood-temporal-evaluation *stage*（`stage_is_ood_temporal_evaluation=true`），但当前 skeleton 不执行真正的 OOD / temporal evaluation（`ood_temporal_evaluation_performed=false`）、不做 metrics evaluation（`metrics_evaluated=false`）、不做 policy search（`policy_search_performed=false`）、不做 quality strategy tuning（`quality_strategy_tuned=false`）、不 promote（`promotion_ready=false`）；synthetic-fixture / `--input` stub 报告设置 `promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`retrieval_policy_changed=false`、`metrics_evaluated=false`、`new_provider_calls=0`、`no_fake_ood_metrics_from_aggregate_means=true`，使该公共 artifact 不会被误读为 empirical B18 OOD / temporal 结果。**CRITICAL**：skeleton **绝不可**从现有 B11 aggregate means 或 R15 / R20 / R26 repo locks 计算伪造的 ood_generalization_gap / temporal_holdout_delta / repo_holdout_metric / language_holdout_metric / model_family_holdout_metric / adversarial_robustness_score / worst_group_metric / cvar_tail_metric / per_cell_denominator / temporal_split_integrity / no_retuning_proof_metric / citation_validity / stale_evidencecore_rejection_rate 指标；B11 aggregate 仅带 public model-family means + repo slice list + sanitized failure slices，但 **无** per-record、per-time-index、per-repo-per-language cell、model_family x repo matrix、adversarial holdout outcome、temporal holdout outcome，且 R15 / R20 / R26 repo locks 是 synthetic / static snapshots，无真实 commit chronology 或 time axis。synthetic / stub 报告仅发出 stage *定义*（无 per-stage 的 `passes=true` / `ood_generalization_gap` / `temporal_holdout_delta` / `worst_group_metric` / `cvar_tail_metric` / `per_cell_denominator`）；skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或 `not_implemented`（ci_ephemeral_records stub）——`success` / `failure` / `partial` 保留给未来 `ood_temporal_evaluation_performed=true` / `metrics_evaluated=true` 的 empirical 路径，该路径在当前 skeleton 中**不**存在。`--self-test` 为只读（将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即失败，不修改 checked-in artifacts）；`--regenerate-artifacts` 为唯一会修改 checked-in artifacts 的路径；`--input` stub 要求显式 `--out`，并拒绝写入 `artifacts/b18_ood_temporal_evaluation/` 内的任何路径。bounded public-aggregate no-go screen（`--public-screen --out <path>`，亦从 `--regenerate-artifacts` 运行）读取已发布的 B11 prospective matrix aggregate report 以及可选的 R15 / R20 / R26 repos.lock.jsonl 文件与 dataset manifests，并发出 `verdict=no_go_public_aggregate_only`（或 `public_aggregate_carry_forward_only`）；它从不声称 OOD / temporal evaluation，从不从 aggregate means 计算 OOD / temporal metric，从不 promote retrieval variant，从不修改 retrieval policy，也从不声明 winner。现有 B11 / R15 / R20 / R26 aggregates 是 **aggregate-only / metadata-only carry-forward** —— 它们**不**是 OOD / temporal proof，**不**是 promotion evidence；它们**不**包含 per-record records、time axis、commit chronology、per-repo-per-language cells、model_family x repo matrix、adversarial holdout outcomes 或 temporal holdout outcomes。详见 [`b18-ood-temporal-evaluation.md`](b18-ood-temporal-evaluation.md)。

---

## B19 理论综合 —— Model-Robust Selective Evidence Conversion

B19 是 B10-B18 Breakthrough Sprint 的 **理论综合**。它是 **仅综合**：`is_synthesis_only=true`、`is_new_experiment=false`、`ran_providers=false`、`new_provider_calls=0`、`changed_retrieval_default_evidencecore=false`。它**不**运行任何 provider，**不**修改 retrieval / default / `EvidenceCore`，**不**声明 promotion。它把 B10 / B10B / B11 / B12 / B13 / B14 / B15 / B16 / B17 / B18 综合成一份关于候选算法概念 **Model-Robust Selective Evidence Conversion** 的论文式算法报告 —— 一个 model-robust、runtime-clean、evidence-gated 的策略，通过把 recall 与 admission 解耦、选择性路由 LLM 角色、并在跨 model adapter 上优化 worst-group utility，将高召回 / 高错误代价的本地候选池选择性地转换为 current-source `EvidenceCore` spans。输入：query、local candidate pool、runtime-observable uncertainty、model capability profile、latency/cost budget。输出/动作：local-only、weak/supporting、LLM span-narrow、LLM filter、abstain、request-more-context，然后 `EvidenceCore` 物化。核心原则：recall/admission 解耦；LLM 角色选择性路由；算法/model-adapter 分离；仅运行期可观测特征（用于 runtime-clean 策略）；worst-group / 跨模型鲁棒优化；候选必须物化进 current-source `EvidenceCore`。正式章节：问题陈述、算法草稿/伪代码、证据边界、策略学习循环、adapter 边界、评估协议、当前 empirical 证据、no-go gaps、promotion blockers、下一步研究计划。

B19 仅 carry forward 已发布的 public-aggregate 结论，**不**引入任何新的 empirical claim：**B10** `balanced_policy_v1_benchmark_routed` 是 benchmark-routed，**不**是 runtime-clean（`runtime_clean=false`）；**B10B** mechanics-validated 的 runtime-shadow scaffold + CI 集成，empirical support pending（在所有 B11 runs 中 label-driven denominator < 10）；**B11** official integrated matrix 32/32、384 records、aggregate verdict `partial_with_failure`，balanced_v1 vs p25 deltas `Δgold_span -0.002604` / `ΔSpanF0.5 -0.001899` / `Δfalse_span -0.054688` / `ΔPFP -0.020833` / `Δmodel_calls -0.354167` —— 加强了 algorithm-candidate signal，但**不** promotion；**B12** public aggregate 无法识别机制（需要 per-record strategy/action outcomes）；**B13** public aggregate 无法运行真实 DRO search（需要 per-record group/action outcomes）；**B14** 无法从 public aggregates 校准 uncertainty（需要 per-record/model-output 结构）；**B15** 无法从 public aggregates 学习 Context Pack Policy（当前价值仅是 preregistration/prior screen）；**B16** downstream agent value 未被证明（需要固定 agent harness 与 patch/test outcomes）；**B17** QuIVer systems track no-go（QuIVer graph/vector backend 缺失；仅 systems 的未来 track）；**B18** OOD/temporal 从 public aggregate 是 no-go（需要 per-record temporal/repo/language/model/adversarial axes）。公共 artifact（`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`，schema `b19-theoretical-synthesis-report-v0`）是 aggregate-only，运行一个 B19 专用的 forbidden-key scan（干净），嵌入一个 self-hash drift guard，并逐字节 carry forward B11 deltas。`eval/b19_theoretical_synthesis.py` 的 `--self-test` 验证 required sections、所有 no-promotion flags 为 false、B11 deltas 精确、forbidden scan 干净、docs links 存在、drift guard 匹配。无伪造 metrics；在 B10-B18 之外无新 claim。`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`runtime_clean_policy_supported=false`、`downstream_agent_value_proven=false`、`ood_temporal_supported=false`、`quiver_systems_supported=false`。详见 [B19 报告](b19-theoretical-synthesis.md)。

---

## B10-B19 结论

B10-B19 Breakthrough Sprint 加强了 **Model-Robust Selective Evidence Conversion** algorithm-candidate signal，但**不**证明一个 runtime-clean general algorithm，**不** promotion，**不**修改 defaults，**不**修改 `EvidenceCore` 语义。当前最强的 empirical 证据是 B11 official integrated matrix（`partial_with_failure`、32/32、384 records）：balanced_v1 vs p25 在平均意义上保持近持平 SpanF0.5 / gold_span，同时减少 false_span、PFP 与 model_calls。然而，B10 `runtime_clean=false` 与 B10B `runtime_shadow_ambiguous_supported=false`（label-driven denominator < 10）阻塞了 runtime-clean generalization claim，且 B12 / B13 / B14 / B15 / B16 / B17 / B18 全部是 public-aggregate no-go 或 screen-only，因为每个下游阶段都缺少其所需的 per-record 数据。本综合是一个研究候选，**不**是 promotion。Promotion 是一个单独的、未来的、evidence-gated 决策，需要 (1) 一个 runtime-clean B10B predicate 在真实 CI ephemeral records 上通过其 10-record hard gate，(2) per-record mechanism / DRO / calibration / pack-policy / downstream-agent / QuIVer-systems / OOD-temporal 证据，以及 (3) 一个单独的 promotion preregistration。`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`runtime_clean_policy_supported=false`、`downstream_agent_value_proven=false`、`ood_temporal_supported=false`、`quiver_systems_supported=false`。

---

## C4 外部 Benchmark Adapter —— Schema 就绪 v1（2026-06-20）

C4.1 是 **外部 benchmark adapter / schema 就绪** 阶段。它**不是**外部 benchmark 性能评估，**不是** benchmark 结果，**不是**下游 agent 价值证明，也**不是** promotion 或默认策略变更。它新增一个 evaluator（`eval/c4_external_benchmark_adapters.py`）与一个 canonical aggregate-only 公共 artifact（`artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`，schema `c4_external_benchmark_adapters.v1`，`claim_level=adapter_schema_readiness_only`）。该 evaluator 实现了 ContextBench（`Contextbench/ContextBench`；`default/train` 1136、`contextbench_verified/train` 500；license `unknown_dataset_license`，行级再分发禁用）与 SWE-Explore（`SWE-Explore-Bench/SWE-Explore-Bench`；`default/train` 848；license `cc-by-nc-nd-4.0`，行级再分发与派生 label 发布均禁用）的内置已知 source/schema 元数据，将 `public_task`（aggregate-safe 元数据）与 `private_label`（行级 payload，永不序列化）分离的合成内存行 adapter，仅用于合成 self-test / 私有内存校验的 line range 归一化，针对所有公共 JSON 输出的严格 fail-closed forbidden scanner，仅通过 stdlib `urllib`（无新依赖）的有界 HF datasets-server schema smoke，以及排除时间戳/网络/原始行/本地路径的确定性 `spec_hash`（`9de6609359aa8de4cfe7ca50b1388ebc51d9ee2f016bb3bc6c34e253da5ef153`）。行级 benchmark 内容（行、label、instance ID、repo URL/commit/path、文件路径/span/line range、snippet、problem statement、patch/test、prompt/response、provider payload、content_sha、原始 HF payload、响应体）未被持久化到任何公共 artifact 或 doc。

验证：`python3 -m py_compile eval/c4_external_benchmark_adapters.py` PASS；`python3 eval/c4_external_benchmark_adapters.py --self-test` PASS（9 组：ContextBench adapter 分离、SWE-Explore adapter 分离、line range 归一化、forbidden scan 拒绝注入、no-claim 标志全为 false、spec hash 确定性、aggregate-only 报告、forbidden scan 在生成时阻断泄漏、schema smoke 报告形态）；默认 canonical artifact 生成 PASS（`forbidden_scan: pass`）；ContextBench（`--benchmark contextbench --schema-smoke --limit 3 --out /tmp/c4_contextbench_schema.json` => `forbidden_scan: pass`、`new_network_calls: 4`）与 SWE-Explore（`--benchmark swe_explore --schema-smoke --limit 3 --out /tmp/c4_swe_explore_schema.json` => `forbidden_scan: pass`、`new_network_calls: 3`）的真实 schema smoke 命令 PASS。`/tmp` smoke 输出遵循与已提交 artifact 相同的 aggregate-only 边界。

所有 no-claim 标志保持 false：`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`runtime_clean_general_algorithm_claimed=false`、`downstream_agent_value_proven=false`、`ood_temporal_supported=false`、`quiver_systems_supported=false`。schema smoke 仅确认公共 HF datasets-server schema 端点可达且可解析；它**不**确认 benchmark 质量、label 正确性或对任何下游评估的适用性。合成 self-test 行不提供任何经验支持。详见 [C4 报告](c4-external-benchmark-adapters.md)。

---

## 0. 核心研究判断

OpenLocus 当前最重要的研究结论不是“语义检索已经解决”，而是：项目已经形成了一个可以在不破坏证据契约的前提下研究语义检索、QuIVer、LLM-derived views、graph、admission guard 的 evidence-gated 实验体系。

当前研究姿态要转为质量/效率优先，只保留必要安全边界，而不是继续让模型缺上下文。在 public corpus 或明确 opt-in 的远程 runs 中，可以给模型更丰富的代码上下文：raw snippets、path/symbol/signature metadata、neighbor windows、top-k local candidates 和 retrieval scores，只要排除 secrets、ignored files、provider keys、private labels/gold answers。

这个体系的核心不变量是：

```text
candidate != fact
candidate/supporting channels -> current source read -> content_sha/range validation -> EvidenceCore
```

在这个体系下，真实向量模型已经显示出**候选/文件级召回信号**，但 L1/L2 大型 slice 测试也显示：dense-only/global dense 在更大规模下不稳定，SpanF0.5 很低，primary_false_positive 风险高。P20-LS-A 也显示：低上下文/query-only LLM aliases 不够。RRF 仍是最强 recall base，symbol/regex 仍是 precision anchor，`query_noise_plus_rrf_agree_min` 仍是当前最值得继续研究的 guard candidate。Dense/QuIVer/LLM-derived/graph 暂时仍只能是 candidate/supporting/diagnostic 层，但 P21-G 应该测试跨模型 context injection，而不是继续只给 metadata-only 模型输入，也不是做单模型 token sweep。

---

## 1. 证据强度分层

| 证据层级 | 支持什么 | 不支持什么 |
|---|---|---|
| **强：EvidenceCore、materialization gates、citation validation、CI privacy gates** | 事实权威链路成立：当前文件校验、内容哈希、严格 line range、citation validity、RUN/SCORE 分离、secrets/private-label 排除。 | 不证明任何检索策略应成为默认，也不应在 public/opt-in runs 中强制低上下文模型输入。 |
| **强失败面证据：R29 on R26 auto-stress 1100 tasks** | RRF、symbol、guard、dense_mock、graph 的失败模式已经在较宽 stress bucket 中暴露。 | R26 labels 是 weak/mined/deterministic，不是人工 promotion evidence。 |
| **中等：real-provider P8/P9 CI scale-up** | 真实向量在有界 public repo slice 上出现了初步、可复验的文件级召回信号；QuIVer BQ 诊断值得继续。 | 样本仍小，span quality 与 default safety 未证明。 |
| **中等偏强负证据：L1/L2 large-repo slice** | dense-only/global dense 在更大 slice 上不稳定，L2 四个 repo 的 PFP 都为 `1.0`，SpanF0.5 极低。 | 仍不是 full-repo exhaustive benchmark；不证明 rich raw-code embedding views 无效。 |
| **方向性：P1-P7 self-tests 与 bounded runs** | provider、LLM status、local harness、anchor-seeded 假设在机制上可跑。 | tiny/self-test 结果可能被更大 public corpus 推翻。 |
| **非质量证据：dense_mock、LLM-generated stress、unavailable QuIVer/TDB** | 适合失败面发现与管线验证。 | 不能作为 semantic quality 或 promotion evidence。 |

---

## 2. 主要研究结论

### 2.1 RRF 仍是召回底座

RRF 在 R26/R29 上仍然是最强 recall channel：FileRecall@1 约 `0.803`，FileRecall@5 约 `0.923`。这说明多路本地 lexical/symbol 信号融合确实能覆盖更多任务。

但 RRF 的核心风险也很明确：primary false-positive 高，R29 中约 `0.453`。也就是说，RRF 适合做 recall base，但不能裸奔成为 primary admission。它需要 guard、anchor 或 admission model。

### 2.2 Symbol 和 regex 是精度锚点

Symbol 在 R29 中保持了 precision-anchor 角色：SpanF0.5 约 `0.291`，primary_false_positive_rate 约 `0.080`。它的问题不是太吵，而是 abstain 高、覆盖不足。因此，symbol extraction repair 是非常有价值的 recall-safe 改进方向。

Regex 也仍然是基础 anchor，但需要 normalization。用户 query 不应该默认当 raw regex；需要区分 literal search、explicit regex search、identifier search、path search。R39/R40 的结果支持 `regex_hybrid_normalized` 继续扩大验证。

### 2.3 当前最强 guard candidate 仍是 `query_noise_plus_rrf_agree_min`

R29 中 `query_noise_plus_rrf_agree_min` 基本保留了 RRF recall，同时把 RRF 的 primary false-positive 从约 `0.453` 降到约 `0.106`，guard_recall_kill_rate 约 `0.003`。这是目前最清楚的 guard 正信号。

但是它仍然不能 promotion：R23 guard sweep 出现大量 bucket regression，R26/R29 本身也不是人工 high-confidence promotion tier。因此它是“继续深入验证的 guard candidate”，不是默认策略。

### 2.4 真实向量有文件级召回信号，但还不是 span evidence

P8/P9 的 CI scale-up 显示：真实 embedding 在有界 public corpus slice 上出现了初步、可复验的文件级召回信号。比如 bounded Flask slice 上 P2 的 FileRecall@1=`0.800`、FileRecall@3=`1.000`；多语言 bge-m3 smoke 中 Go/Python 表现强，Rust 中等，JS Express 更弱。

但后续 L1/L2 大型 slice 测试削弱了这个乐观信号：当扩大到 60 tasks / 1000 records / 2000 files 后，Django/Kubernetes 的 FileRecall@1 降到约 `0.25`，Next.js/Deno 接近 `0`，四个 repo 的 primary_false_positive_rate 都是 `1.0`，SpanF0.5 最高也只有约 `0.022`。这说明 dense 当前更像“候选支持通道”，而不是可直接作为 EvidenceCore primary span 的证据通道。

### 2.5 第一批结果没有证明“大模型更好”

P9a 在同一个 Flask slice 上比较了 `BAAI/bge-m3`、`Qwen/Qwen3-Embedding-0.6B`、`Qwen/Qwen3-Embedding-4B`、`Qwen/Qwen3-Embedding-8B`。这个小样本中，8B 没有明显优于小模型；bge-m3 和 Qwen 0.6B/4B 都达到 FileRecall@1=`1.000`，8B 为 `0.800`。

这不能说明小模型一定更好，但足以提醒我们：后续不应默认假设最大 embedding 模型最好，而应在相同任务、corpus、cap 下继续 bakeoff，并同时记录 latency/cost。

### 2.6 Anchor-seeded dense/QuIVer 有希望，但尚不安全

早期 tiny/self-test 中，anchor-seeded dense/QuIVer 看起来很乐观：P4 best strategy 曾出现 added_gold=`2`、added_false=`0`。但 P8a 在真实 public Flask slice 上出现了反向信号：FileRecall@1=`1.000`，但 added_gold=`3`、added_false=`15`。

L1 P4 进一步强化了 blocked 结论：`py_django` best anchor strategy added_gold=`0`、added_false=`40`；`go_kubernetes` added_gold=`5`、added_false=`44`。

这正是 research harness 的价值：小样本乐观信号被更真实的 corpus 约束住了。当前结论不是“anchor-seeded 不行”，而是：anchor-seeded 方向仍值得继续，但必须继续 supporting-only，并重点优化 span targeting 与 false-span suppression。

### 2.7 QuIVer 仍是诊断阶段，但 BQ 信号不再是空的

P3 在真实 embedding 上做了 BQ readiness 诊断。Flask slice 上 BQ_overlap@10=`0.680`、BQ_overlap@50=`0.728`、BQ_vs_f32_MRR=`1.000`，quiver_fit 标记为 `promising`。这说明 BQ/QuIVer 方向值得继续，而不是直接放弃。

L1 P3 在更大 slice 上仍有非空 BQ 诊断信号：Django 标记为 `promising`，Kubernetes 为 `mixed`。这仍只是 BQ diagnostic，不是 QuIVer graph/ANN quality。

但 QuIVer graph/Vamana 后端尚未实现，当前没有 ANN graph quality claim。QuIVer 仍然只能是 diagnostic/prototype-only。

### 2.8 Graph expansion 继续 blocked

R25/R29/P6 都支持同一结论：graph 不适合默认 expansion。R29 中 graph_basic added_gold=`0`、added_false=`437`。Graph 更可能适合 explainer、rerank feature、impact/test selector，而不是默认 recall expansion。

### 2.9 LLM-derived 适合 stress 和 hint，不适合事实层

真实 LLM provider 已经跑通，P5 生成了 derived/stress 结果。但这些输出必须保持 `not_evidence=true`：LLM 不能生成 Evidence，不能生成 gold label，不能做 citation verdict，也不能做 promotion verdict。

当前 LLM 最适合的角色是：query aliases、symbol tags、intent views、candidate rerank/filter/span narrowing、failure/stress generation。它可以扩大失败面，也可以帮助解释 rich candidate context，但不能替代 EvidenceCore。

P20-LS 把这条边界变成了可执行检查：LS0 做安全预检，LS1 生成 `not_evidence=true` query aliases 并只作为 candidate/supporting 检索扩展评测，LS3 默认只写 public stress split。初始离线 slice 已经给出警告信号；随后 P20-LS-A 用真实 LLM provider（`Kimi-K2.7-Code`）跑了 self-test 与 9 个真实 CI corpus runs。schema/guardrail 表现可以接受，但低上下文/query-only alias 质量完全失败：9 个真实 runs 中 0 个 quality pass，added_gold_span=`289`、added_false_span=`8312`（约 28.8:1 false:gold），平均 fabricated_identifier_rate 约 `0.459`。因此低上下文 LLM query aliases 已经 blocked，不应继续扩大。这不是 rich-context LLM retrieval 的结论；后续 alias/retrieval 研究应使用 source snippets、candidate metadata、symbol/path inventories 和 prompt/context matrices。

### 2.10 P21-G 应研究跨模型上下文注入效应

下一阶段模型研究不应该继续把 metadata-only remote input 当作默认姿态，但也不应把某一个模型的最佳 token budget 当成 OpenLocus 的全局规律。对于 public corpus 和明确 opt-in 的远程 runs，模型应该拿到足够代码事实：raw code snippets、path headers、signatures、symbol bodies、neighboring lines、local retrieval scores、hard distractors、top-k candidate sets。必要边界仍然保留：排除 secrets、ignored files、provider keys、private labels/gold answers；EvidenceCore 仍是最终事实权威；不让 LLM 做 promotion judge。

P21-G 应跨 embedding 与 LLM model profiles、query buckets、repo types、roles 和 layouts 比较 context atoms 与 context packs。主变量不是固定 token cap，而是注入的信息：signatures、matched lines、source/test/doc flags、retrieval scores、body windows、neighbor symbols、related tests、hard distractors、candidate uncertainty 和 inventory grounding。P21-G1E 显示裸 dense context atoms 仍只能 supporting-only：`pack2_evidence_sketch` 是 model-averaged SpanF0.5 最好的策略，`atom_signature` 是 FileRecall@5 最好的策略，但 false spans 远多于 gold spans（`17924` vs `2876`）。P21-G2E 显示 constrained dense 有 modest supporting value：`dense_atom_signature_rrf_file_constrained` 的 SpanF0.5 avg `0.163` vs RRF `0.1508`，PFP avg `0.0`，`11/16` runs 有用。Dense 仍不能 primary。P21-G3L 显示 LLM rich candidate roles 有信号但强烈依赖模型/仓库：`llm_span_narrow` avg ΔSpanF0.5 `+0.0418`，Flash/Kimi 在 `py_flask` 最明显；filter/abstain 降 false 但经常杀 gold；GLM-5.1 schema degradation 阻止继续扩大，需先做 prompt/schema repair。每份报告都必须同时记录质量、效率和跨模型泛化：SpanF0.5、added_gold/false、PFP、provider calls、input/output tokens/chars、p50/p95 latency、cost、model-averaged treatment effect、per-model effect 和 effect variance。

P21-G3L-R 是 LLM roles 的 structured-output repair 路线。rich-candidate harness 已支持 `prompt_only`、`json_object`、`json_schema_strict`、`tool_call` 四种输出模式，记录 provider-rejection fallback diagnostics，并允许一次不再走 fallback ladder 的 schema repair retry。第一轮 GLM-focused smoke 已跑 4 output modes × 2 repos：`tool_call` 目前是 GLM 最优模式（avg SpanNarrow Δ `+0.0677`，repair success `3/5`），`prompt_only` 应阻断，`json_object` 仍不够，`json_schema_strict` mixed。随后顺序低并发重跑 `tool_call`，去除了 provider HTTP 429 噪声，并把 GLM SpanNarrow avg Δ 提到 `+0.1361`；下一轮 bucketed P21-G3L 应让 GLM 使用 `tool_call`。

P21-G3B 新增 public-safe bucket sampling（`task_bucket` 与 `task_risk_tags`），并确认 global LLM roles 不能跨 mixed buckets 默认启用。在 6-run bucketed smoke 中，LLM roles 能显著降低 PFP，但经常同时杀掉 gold spans。`span_narrow` 仍适合 likely-positive / high-confidence tasks，但不是跨桶默认策略。`filter` 和 `abstain` 只能路由到 negative / dense-false-positive / ambiguous buckets，不能全局默认。

P22/P23 把下一阶段从“继续比较单个通道”推进到 evidence-seeking policy surface。当前冻结了两个本地、无远程调用的决策面：`r20_positive` 用于正例 candidate reach，`r26_guard` 用于 no-gold guard stress。R20 capped positive slice 显示 RRF 仍是 reach base（`Reach@5=0.975`，`SpanReach@5=0.95`），但 symbol 的本地 SpanF0.5 最好（`0.3169`），`symbol_regex_union` 是进入 P25/P30 的 precision/reach 实验基线候选。R26 显示 BM25/RRF 仍会在 no-gold 噪声查询上制造 false primary（`0.2833`），而 symbol/regex/union/guard 会 abstain。因此 P25/P30 必须分开优化：召回保留、false-primary 抑制、EvidenceCore materialization 是三个不同成功层级。

### 2.11 P25 bucket-routed LLM role policy 评估器已就绪

`eval/p25_bucket_policy.py` 是一个确定性、无远程调用的策略评估器。当前提交的报告只是经过净化的 self-test 脚手架（`status=self_test_only`、`not_quality_evidence=true`），不是质量证据。真实 P25 评估现在必须使用 `eval/p21_llm_rich_candidate.py --p25-policy-records-out` 在 SCORE 阶段生成的临时 records；这些 records 留在 runner temp，不上传，P25 只上传聚合指标。`bucket_routed_v0` 只按 allowlisted public `task_bucket`/`task_risk_tags` 路由：`llm_span_narrow` 用于 likely-positive / high-confidence 桶，固定先验的 `llm_filter`/`llm_abstain_filter` 用于 negative / dense-false-positive / ambiguous 桶，exact-symbol + unique-symbol-anchor 任务跳过 LLM，其余回退到 candidate baseline。P21 aggregate summary 和非 ephemeral schema 会被拒绝为 `status=insufficient_task_detail`。这只是 P25/P30 evidence-seeking policy surface 的脚手架，不是 promotion 结论。

第一轮真实 P25 remote smoke 使用这个安全的 P21→P25 ephemeral handoff，完成 6 个成功聚合 runs（`Flash/Kimi/GLM × py_flask/js_express`，每个 run 18 个按 bucket 抽样任务）。`bucket_routed_v0` 显著降低 false spans（`108 -> 28`）和平均 PFP（约 `-0.0926`），但也损失了一些 gold spans（`24 -> 21`）；平均 SpanF0.5 只小幅正向（`+0.0026`），且强依赖 repo/model。因此 P25 适合作为 P30 Admission V3 的 false-primary reducer 组件，而不是 default policy。

### 2.12 P30 Admission Model V3 脚手架已就绪

`eval/p30_admission_model_v3.py` 是一个确定性、无远程调用的 admission model
研究脚手架（schema `p30-admission-v3-report-v1`）。当前提交的报告同样是经过净化的
self-test 脚手架（`status=self_test_only`、`not_quality_evidence=true`），不是质量证据。
真实 P30 评估仍需使用
`eval/p21_llm_rich_candidate.py --p25-policy-records-out` 在 SCORE 阶段生成的临时
`p25-policy-records-ephemeral-v1` records；这些记录留在 runner temp，不上传，P30 只上传聚合指标。

P30 只从 RUN-phase 公开可观测特征进行路由：public `task_bucket`、
`task_risk_tags` 和 `route_features`。`score_group`、`has_gold`、gold spans、
private labels 和 outcome metrics 只在动作确定后用于聚合评分。允许的动作包括
`abstain`、`admit_symbol_regex_union`、`admit_rrf_primary`、
`admit_llm_span_narrow`、`apply_llm_filter`、`supporting_only`、
`weak_candidate_only`。`admission_v3` 评分卡结合可解释单调特征分数（query noise、
exact/unique symbol anchor、symbol/regex/local anchors、RRF backed by anchor、
LLM span-narrow validity/within candidate）与 negative/ambiguous/dense-false-positive
桶的 hard guard。dense 和 graph 信号只允许作为 supporting feature，不能发明 primary evidence。

评估器比较 `candidate_baseline`、`llm_span_narrow`、`llm_filter`、
`llm_abstain_filter`、`bucket_routed_v0`（从 P25 复用）和 `admission_v3`。
报告 task count、SpanF0.5、PFP、added gold/false spans、filter gold kill rate、
abstain rate、action counts、score bands、selective risk proxy、与
candidate baseline 和 `bucket_routed_v0` 的 mean deltas，以及对输入中没有测量 outcome
的动作的 fallback 计数。公开输出会递归扫描禁用键
（raw query/snippet/prompt/response/gold/gold_spans/private labels/provider keys）。
`promotion_ready=false`、`default_should_change=false`、
`evidencecore_semantics_changed=false`、`candidate_not_fact=true`、`external_calls=0`。

P30 不是 promotion candidate。下一步应把它接入真实 P25 ephemeral smoke records，
与 P25 `bucket_routed_v0` 以及 P22/P23 evidence-seeking guard surfaces 进行比较。

第一轮真实 P30 remote smoke 已完成 6 个成功 runs（`Flash/Kimi/GLM × py_flask/js_express`，每个 run 18 个按 bucket 抽样任务）。结果确认当前 `admission_v3` 脚手架过于保守：baseline added gold/false 为 `27/102`，P25 `bucket_routed_v0` 为 `19/39`，P30 `admission_v3` 为 `17/41`。P30 匹配了平均 PFP 降幅（`-0.0833`），但平均 SpanF0.5 delta 比 `bucket_routed_v0` 更差（`-0.0102` vs `+0.0010`）。非零 fallback counts 表明当前 ephemeral handoff 还缺少更丰富本地 admission 动作所需的 measured outcomes/features。下一步应扩展 P21/P22 handoff，加入 measured `symbol_regex_union` / `rrf_primary` outcomes 和安全 route features，再重跑 P30。

P30-H1 已实现这个 handoff repair。它作为 measurement repair 成功，但作为 policy improvement 失败。6 个真实 runs 中 `admission_v3_h1` 的 selected-action fallback 为 0，因此比较已经 quality-comparable；但 P25 `bucket_routed_v0` 仍更强：`20/37` added gold/false，平均 ΔSpanF0.5 为 `+0.0020`；P30-H1 为 `18/87`，平均 ΔSpanF0.5 为 `-0.0350`。新的结论是：missing handoff 掩盖了 scorecard 本身的问题，`admit_symbol_regex_union` 太宽，放进了很多 false spans。下一步 P30-H2 应收紧 local-anchor admission，而不是继续加新通道。

P30-H2 收紧了 local-anchor admission，但这次 quality repair 仍失败。它保持 fallback-free 和 quality-comparable，但结果为 `15/90` added gold/false；H1 是 `18/87`，P25 `bucket_routed_v0` 是 `16/36`。平均 ΔSpanF0.5：H2 `-0.0370`，H1 `-0.0346`，P25 `-0.0052`。新的诊断是：问题不只是 primary admission 太宽；weak/supporting/filter actions 仍然保留了过多 span-level false cost。P30-H3 现在已把 action-specific span-cost accounting 和 false-span budgets 实现为一个仅 SCORE 阶段的诊断性会计层；它不改变 admission 路由，而是从现有 `bucket_routed_v0`、`admission_v3_h1`、`admission_v3_h2` 及 baseline 对比策略推导每个动作的成本，并输出专用报告 `artifacts/p30_admission_v3/p30_h3_span_cost_report.json`（schema `p30-h3-action-span-cost-report-v1`）。

真实 P30-H3 smoke（6 个成功 runs，108 个任务）更精确地解释了 P30 的失败模式。baseline 是 `27/102` added gold/false spans；P25 `bucket_routed_v0` 仍是最强 reference，为 `19/45`；P30-H1 为 `18/88`；P30-H2 为 `15/90`。H3 显示 P30-H1/H2 的 false-span 成本主要来自 primary local-admit actions（`admit_symbol_regex_union`，以及 H2 的 `admit_rrf_primary`），而 `supporting_only` 的主要代价是杀掉 gold、造成 recall loss，并不是新增 false spans。因此 P30-H4 应该给 primary local-admit actions 设定明确 action budgets，而不是继续整体收紧所有 non-primary actions。

### 2.13 P31 Candidate Reach Ceiling Study 脚手架已就绪

`eval/p31_candidate_reach_ceiling.py` 是一个确定性、无远程调用的诊断性脚手架
（schema `p31-candidate-reach-ceiling-report-v1`）。当前提交的 self-test 产物是
经过净化的合成数据（`status=self_test_only`、`not_quality_evidence=true`），不是质量证据。
P31 仅用于 SCORE 阶段：labels 只在 RUN 之后加载，并仅用于聚合指标；它不影响路由或准入决策。

P31 测量候选证据本身在没有任何路由或准入决策前覆盖 gold label 的能力。
输入与 P25/P30 相同，是 `p25-policy-records-ephemeral-v1` 临时 records。
当 records 尚未携带候选证据池时，P31 会报告
`candidate_pool_availability=missing_candidate_pool` 和
`reach_metrics_available=false`，然后只计算 outcome-only fallback 指标，而不是伪造 reach 零值。
当候选池存在时，它会报告 K=1/3/5/10/20 的聚合 `GoldFileReach@K`、`GoldSpanReach@K`、
`GoldSpanExactReach@K`、`CandidateAbsentRate@K`、`FileRightSpanWrongRate@K`，
以及与 `candidate_baseline` 对比的 `ModelMissGivenGoldPresent@K`、
动作/策略诊断指标（`FilterKillGoldRate`、`AdmissionFalsePrimaryRate`、
`AdmissionFalseSpanPerNoGoldTask`）、`EvidenceCoreRejectRate`
（无 rejection 字段时为 `not_measured`），以及满足 `funnel_sums_to_positive_tasks=true` 的 K=5 失败漏斗。

P31-H1 扩展了 P21 rich-candidate 临时 handoff：临时 records 现在携带轻量级候选池
（`p31_candidate_pools`）与仅 SCORE 阶段使用的 private gold spans（`p31_score_gold`），
并标记 `p31_h1_candidate_reach_handoff=true` 与
`p31_h1_schema_version="p31-h1-candidate-reach-handoff-v1"`。
池内条目仅保留 `rank`、`path`、`start_line`、`end_line`，以及可选的 `content_sha`、
`score`、`channels`；不含 snippet、原始 query/prompt/response 或 provider 字段。

P31-H2 增加 strategy-level reach matrix，覆盖 `candidate_baseline`、`rrf_primary`、
`symbol_regex_union`、`llm_span_narrow`、`llm_filter`、`llm_abstain_filter`。
当 H1 候选池存在时，它按公共 `repo_id` 与 `task_bucket` 聚合 reach@5，
报告 unique reach share、pairwise file/span overlap 与 Jaccard span、
双向 marginal gain，以及固定策略组合的并集 reach。缺失的策略池会报告
`availability=missing_pool`，而不是伪造零值。

公开产物仅限聚合指标：不含 per-task 行、原始 query/snippet/prompt/response、
candidate paths/spans、gold spans、private labels 或 provider 字段。
安全标志锁定：`promotion_ready=false`、`default_should_change=false`、
`evidencecore_semantics_changed=false`、`candidate_not_fact=true`、
`remote_calls_by_p31=0`、`score_phase_only_metrics=true`、
`aggregate_only_public_artifact=true`。


第一轮真实 P31-H1 reach smoke 已完成 6 个成功 runs（`Flash/Kimi/GLM × py_flask/js_express`，共 108 个任务、48 个 positive tasks）。所有 runs 都检测到 H1 handoff，且 reach metrics 均可用。candidate baseline 在 K=5 时只覆盖 `24/48` 个 positive tasks 的文件和 span（`GoldFileReach@5=0.5000`、`GoldSpanReach@5=0.5000`），而 `FileRightSpanWrongRate@5=0/24`。这说明本轮 smoke 的第一瓶颈是 candidate absence，而不是文件内 span localization。相同 runs 中 P25 `bucket_routed_v0` 的 false-span 成本仍明显低于 P30-H1/H2（P25 added gold/false `20/46`，H1 `18/87`，H2 `15/90`），但 P31 说明：只调 admission 无法找回缺失的一半 positive tasks。

P31-H2 strategy reach matrix 的重跑说明：下一步更应该修 anchor，而不是再加一个 LLM role。K=5 时，`candidate_baseline` 覆盖 `24/48` 个 positive spans，`rrf_primary` 覆盖 `21/48`，而 `symbol_regex_union` 覆盖 `42/48`。`symbol_regex_union` 贡献 `18/48` 个 unique span hits，而 `candidate_baseline + rrf_primary` 和 `candidate_baseline + llm_span_narrow` 都仍停在 `24/48`。因此 `symbol_regex_union` 是高 reach 的 candidate expansion source，但 P30-H3 已经证明它直接 primary admit 不安全。下一步应进入 P33 anchor repair/calibration，以及 P32/P30-H4 在 local-anchor primary admission 前加入 action budget。

第一轮真实 P33 anchor precision smoke 进一步确认：目前没有任何 observed anchor bucket 可以被视为 primary-safe。最强 calibration cell（`a3_r0_s2`：span agreement、low-risk、RRF-span-backed）覆盖 `42/48` 个 positive spans，但 `false_per_gold≈8.69`、`net_span_value_2x=-786`。`symbol_regex_agree_span` 在其 bucket 内覆盖 `9/9` 个 positives，但仍有 `false_per_gold=4.0`；`symbol_regex_disagree` 覆盖 `27/30`，但 `false_per_gold≈13.44`；`regex_only` 更差（`false_per_gold=22.5`）。因此 P33 保留 P31-H2 的结论：anchors 是主要 reach lever；同时强化 P30-H3 的结论：anchor primary admission 必须被 budget 约束。下一步 P33-B 应修复/校准 symbol 和 regex 子类型；P32/P30-H4 不应在没有 held-out budget validation 前 promote 任何 local-anchor bucket。

### 2.14 P33 Reach-Preserving Precision Anchor Repair 脚手架已就绪

`eval/p33_anchor_precision_repair.py` 是一个确定性、无远程调用的诊断性脚手架
（schema `p33-anchor-precision-repair-report-v1`）。它复用 P31 使用的 P21/P31-H1
临时 records：需要 `p31_candidate_pools`、`p31_score_gold`、公共
`task_bucket`/`task_risk_tags` 以及 RUN 阶段可观测的 `route_features`。
labels 与 gold spans 只在 SCORE 阶段用于聚合指标。当候选池或 gold spans 缺失时，
P33 报告 `availability=missing_pool`/`not_measured`，而不是伪造零值。

P33 定义了 anchor taxonomy v1，包括 `exact_unique_symbol_anchor`、
`unique_symbol_anchor`、`symbol_anchor_only`、`regex_anchor_only`、
`symbol_regex_agree_span`/`agree_file`/`disagree`、
`rrf_anchor_agree_span`/`agree_file`/`unbacked`、公共桶
（`positive`/`ambiguous`/`negative`）、风险标签（`hard_distractor`、
`dense_false_positive`）、query-noise 等级，以及有界组合桶如
`symbol_regex_agree_span_low_risk`、`rrf_span_backed`、
`negative_or_ambiguous_with_anchor` 等。每个桶报告 task count、positive/no_gold count、
`GoldFileReach@5`、`GoldSpanReach@5`、`FileRightSpanWrongRate@5`、span cost 聚合
（`added_gold_span`、`added_false_span`、`false_per_gold`、`gold_per_false`、
`net_span_value_1x/2x`）、平均 `SpanF0.5` 与平均 `primary_false_positive_rate`，
以及 diagnostic class
（`primary_candidate_safe_observed`、`supporting_only_observed`、
`needs_budget_guard`、`blocked_high_false_cost`、
`insufficient_denominator`）。

三维校准矩阵的三个维度为：`anchor_strength`
（0=无 anchor，1=仅有 symbol/regex，2=文件级 agreement，3=span 级 agreement，
4=exact_unique_symbol_span_agreement）、`risk_level`
（0=低风险/positive，1=ambiguous，2=negative/高风险）、`rrf_backing_level`
（0=无 RRF backing，1=仅文件级，2=span 级），报告同样的聚合诊断并标记单调性异常。
`p33_to_p32_handoff` 按 diagnostic class 分组 budget candidate buckets，
并显式设置 `frozen_policy=false`。

公开产物仅限聚合指标：不含 per-task 行、task IDs、原始 query/snippet/prompt/response、
route features、candidate paths/spans、gold spans、private labels 或 provider 字段。
安全标志锁定：`promotion_ready=false`、`default_should_change=false`、
`evidencecore_semantics_changed=false`、`candidate_not_fact=true`、
`remote_calls_by_p33=0`、`score_phase_only_metrics=true`、
`aggregate_only_public_artifact=true`。

### 2.15 P33-B Anchor Subtype Calibration 脚手架已就绪

`eval/p33b_anchor_subtype_calibration.py` 是一个确定性、无远程调用的诊断性脚手架
（schema `p33b-anchor-subtype-calibration-v1`）。它扩展了 P21 的临时 handoff，
为每个 `symbol_regex_union` 候选增加了私有 subtype 元数据
（`p33b_anchor_subtypes`，schema `p33b-anchor-subtypes-v1`），将其分类为
`symbol_only`、`regex_only`、`symbol_regex_fusion`，并标注 agreement class
（`single_source`、`same_file_only`、`span_overlap`、`disagree`）、
`rank_bin`、`candidate_count_bin`、`span_width_bin` 以及 per-candidate
`rrf_backing`。同时新增 `symbol_primary` 和 `regex_primary` 候选池，供
P31 覆盖研究使用。

P33-B 消费这些临时 records，将私有 subtype 行与 `symbol_regex_union` 候选对齐，
仅在 SCORE 阶段使用 `p31_score_gold` 和 strategy outcomes 计算聚合指标。
它报告有界 subtype bucket 的诊断：task count、positive/no-gold count、
`SubtypeGoldFileReach@5`、`SubtypeGoldSpanReach@5`、
`FileRightSpanWrongRate@5`、`UniqueSubtypeSpanReach@5`、span cost 聚合
（粗粒度 task-level attribution）、`delta_vs_candidate_baseline`，
以及带最小分母门控的 diagnostic class。三维校准矩阵覆盖
`source_strength`（0=regex_only，1=symbol_only，2=symbol_regex_fusion）、
`match_quality`（0=disagree，1=same_file_only，2=span_overlap_unbacked，
3=span_overlap_rrf_backed）和 `risk_level`，报告同样诊断并标记单调性异常。
`p33b_to_p32_handoff` 按 diagnostic class 分组 budget candidate buckets，
并显式设置 `frozen_policy=false`。

公开产物仍仅限聚合指标：不含 per-task 行、task IDs、原始 query/snippet/prompt/response、
candidate paths/spans、gold spans、private labels、route features、subtype 行或
provider 字段。安全标志锁定：`promotion_ready=false`、
`default_should_change=false`、`evidencecore_semantics_changed=false`、
`candidate_not_fact=true`、`remote_calls_by_p33b=0`、
`score_phase_only_metrics=true`、`aggregate_only_public_artifact=true`。

真实 P33-B subtype smoke（6 个成功 runs，108 个 task observations：36 positive、72 no-gold）在更细粒度上确认了 P33 结论：没有任何 observed subtype bucket 可以 primary-safe。`span_overlap` 是最好的粗粒度 agreement class（`GoldSpanReach=1.0`、`false_per_gold≈1.78`），但在 2x false-span penalty 下仍是 net-negative。`symbol_regex_fusion` 在本轮 smoke 中 subtype span reach 也完整，但 added gold/false 仍为 `24/66`（`false_per_gold=2.75`）。`same_file_only` 更弱（`false_per_gold≈2.18`），`disagree` / `single_source` buckets 被 false-span cost 主导。RRF backing 有帮助，但不足以让 anchor 安全（`rrf_yes false_per_gold≈4.67`）。因此 P33-B subtype bucket 应作为 P32/P30-H4 action budget 输入，而不是 primary admission。

### 2.16 P32 / P30-H4 确定性预算覆盖层已就绪

`eval/p30_admission_model_v3.py` 现已实现 `admission_v3_h4`，即 P32/P30-H4 预算覆盖层策略。H4 是确定性、无远程调用、仅诊断用途的 lane。它从 P21 短暂 handoff 读取私有 P33-B 子类型元数据（`p33b_anchor_subtypes`、`p33b_anchor_subtypes_schema`），结合 RUN-phase 公开特征，测试 budgeted demotion。它不改动 Rust/EvidenceCore 语义、默认 pipeline 策略或任何生产 admission 路由。

P33-B 已证明任何 subtype 都不 primary-safe：即便是最好的 `span_overlap` bucket，`false_per_gold≈1.78` 且在 2x false-span penalty 下 net-negative；`disagree` 与 `single_source` 危险；`same_file_only` 更弱。因此 H4 仅基于 subtype 证据不会选择 `admit_symbol_regex_union`、`admit_rrf_primary` 或 `admit_llm_span_narrow`，其动作限定为 `apply_llm_filter`、`supporting_only`、`weak_candidate_only` 和 `abstain`。规则保守：negative/dense/ambiguous 任务过滤或弃权；低危公开 bucket 中 `span_overlap` 若带 RRF backing 则归为 `supporting_only`，否则 `weak_candidate_only`；`same_file_only` 仅在明确 positive bucket 中归为 `weak_candidate_only`；`disagree`/`single_source` 除非公开 bucket 强 positive 且 query noise 低，否则过滤。缺失 subtype 元数据时退化到类 `bucket_routed_v0` 的保守回退。

归一化后的内存任务会携带 P31/P33-B 私有 handoff 字段（`p31_candidate_pools`、`p31_score_gold`、`p33b_anchor_subtypes`、`p33b_anchor_subtypes_schema`）供 SCORE-phase 使用，但这些键不会出现在 P30 公开产物中。报告标志锁定为 `h4_budget_overlay=true`、`promotion_ready=false`、`default_should_change=false`；当存在 P33-B 记录时，`h4_available=true` / `p33b_handoff_detected=true`。H4 与 H1/H2 一样报告 `quality_comparable`、`blocked_by_missing_action_outcomes` 和 `selected_action_fallback_rate`；real-provider CI gate 现在要求 H4 存在，并在 `p21_llm_rich` 真实记录上质量可比且 selected-action fallback 为零。

第一轮真实 P30-H4 remote smoke 完成 6 个成功 runs。它 quality-comparable 且 fallback-free，但过度保守：H4 产生 `0` added gold spans 和 `0` added false spans，mean SpanF0.5 为 `0.0000`。相同 runs 中 P25 `bucket_routed_v0` 仍是最佳 reference（added gold/false `27/34`，mean SpanF0.5 `0.0768`）。因此 H4 是 safety lower bound 和有价值的负结果，不是可部署 admission policy。下一轮 H4 应测试 budgeted selective re-admission 或 `request_more_context`，而不是 all-demotion。

### 2.17 P32 / P30-H4B 选择性 primary re-admission 已就绪

`eval/p30_admission_model_v3.py` 现已同时实现 `admission_v3_h4b`，即 P32/P30-H4B 选择性 primary re-admission 诊断策略。H4B 是确定性、无远程调用、仅诊断用途的 lane。它与 H4 使用相同的私有 P33-B subtype handoff 和 RUN-phase 公开特征，但测试一个极窄的严格合取条件，以判断是否允许 primary-admit 动作。

严格门仅在以下全部满足时才选择 `admit_symbol_regex_union`：最优子类型为 `symbol_regex_fusion` + `span_overlap` + `rrf_backing`；`local_anchor` 和 `symbol_regex_agree_span` 为真；`query_noise <= 0.1`；公开 bucket/tag 属于低危 positive 集合；且 `exact_unique_symbol_anchor` 或 `rrf_anchor_agree_span` 至少一个为真。若同时还有 `rrf_backed_by_anchor` 和 `rrf_anchor_agree_span`，H4B 可选择 `admit_rrf_primary`。其余任务一律 hard-guard 或降级，包括 negative/dense/ambiguous/hallucination/high-noise 及最优子类型为 `regex_only`/`same_file_only`/`disagree`/`single_source` 的情况。

公开产物包含 `h4b_available`、`h4b_budget_overlay=true`、`h4b_selective_readmission=true`、`h4b_primary_opportunity_count` 以及 rule 聚合计数（`strict_union_re_admit`、`strict_rrf_re_admit`、`hard_guard`、`missing_handoff`、`demote_span_overlap`、`demote_same_file`、`filter_dangerous_subtype`）。H4B 还报告 `quality_comparable`、`selected_action_fallback_rate`、`false_per_gold`、`net_span_value_2x` 以及来自 P30-H3 会计的 span-cost summary。合成 self-test 中 H4B 质量可比且 fallback-free，并触发少量严格 primary opportunity。真实 H4B smoke 已完成 6 个成功 provider runs：H4B quality-comparable 且 fallback-free，并摆脱 H4A 全刹车失败（added gold/false `0/0 -> 24/41`）。但它仍未超过 P25 `bucket_routed_v0`（P25 added gold/false `25/30`，mean SpanF0.5 `0.0683`；H4B `0.0433`），因此 H4B 是有希望的研究方向，但不是 promotion candidate。下一轮应进一步收紧 strict RRF re-admission，或在 primary admission 前引入 `request_more_context`。

---

## 3. 当前研究假设

| 假设 | 当前状态 | 需要什么来确认 |
|---|---|---|
| RRF 应保留为 recall base。 | R29 强支持，但必须配 guard。 | 在人工与 stress tier 上 guard 后仍稳定召回。 |
| symbol/regex 应作为 precision anchor。 | 强支持。 | 更广 symbol repair 后 false-positive 不升。 |
| dense 目前应保持 supporting-only。 | 当前 L1/L2 证据已经 blocking dense-only/global dense 的 primary/default。 | rich raw-code/snippet views 能稳定 added_gold > added_false，PFP 低，latency/cost 可接受。 |
| anchor-seeded dense/QuIVer 可能比 global dense 更安全。 | 有希望但信号混合。 | 多 repo 上可复验地抑制 false span。 |
| BQ 诊断可能适配当前 code embedding 分布。 | Flask 诊断信号积极。 | 分片 BQ/proto graph 在速度/质量上有优势且不增 false。 |
| 小 embedding 模型可能足够。 | P9 初步支持继续比较。 | 更多 repo 同任务并记录 latency/cost。 |
| LLM-derived 可安全扩大失败面。 | 机制可行，质量未证。 | rich context derived views 增加 gold 或 stress coverage，且不诱导 primary hallucination。 |
| LLM query aliases 能在不污染 primary 的情况下改善 anchor。 | 低上下文 P20-LS-A query aliases 对 `Kimi-K2.7-Code` 已 blocked：真实 runs 0/9 quality pass，false:gold span≈28.8:1，平均 fabricated identifier rate≈0.459。 | Grounded variant 成功：从 repo inventories 或 top-k candidate context 中选择 aliases，`alias_added_gold > alias_added_false`，PFP 不升，fabricated identifier rate 低。 |
| Context atoms 能跨模型泛化。 | P21-G planned hypothesis。 | Signature/matched-lines/scores/flags/body-window atoms 具有正向 model-averaged treatment effect，模型间方差低，且不增加 PFP。 |
| Rich LLM candidate support 能改善 span targeting。 | P21-G role hypothesis。 | 在 snippet-backed local candidates 上 rerank/filter/span-narrow，SpanF0.5 上升、false spans 下降，latency/cost 可接受。 |

---

## 4. 矛盾信号与负结果

这些负结果是目前最有价值的部分之一，因为它们防止研究结论过早乐观：

1. **P4 tiny 乐观信号被 P8a 弱化**：tiny self-test 中 anchor-seeded added_false=`0`，但 public Flask slice 中 added_false=`15`。
2. **Dense file recall 与 span quality 分离**：多个 P8/P9 结果显示 FileRecall 可以很好，但 SpanF0.5 仍低。
3. **RRF recall 与 false-primary 绑定**：RRF 强召回同时携带高 false-primary，说明 admission 比 raw recall 更关键。
4. **Graph expansion 多次 net-negative**：graph_basic 在 R29 中几乎只加 false，不加 gold。
5. **更大 embedding 模型未在首批样本中胜出**：8B 没有压倒 0.6B/4B/bge-m3。
6. **JS Express 表现弱于 Go/Python/Rust**：真实 embedding 质量有语言/框架差异，不能只看平均数。
7. **P20-LS 低上下文 alias expansion 真实-provider scale-up 失败**：所有 guardrails 通过，但 query-only aliases 在真实 CI runs 上 false spans 远多于 gold spans（8312 vs 289），且 fabricated identifier rate 高；这阻断低上下文 LLM alias scale-up，不阻断 rich-context LLM retrieval。

---

## 5. 当前质量与边界策略

新的研究优先级是质量与效率。边界应该保护事实层和 secrets，而不是让模型缺少有用的 public-code context。目前所有研究结论都依赖以下必要边界继续成立：

- `EvidenceCore` 仍是唯一事实层。
- Dense/QuIVer/graph/LLM-derived 只能产出 candidate/supporting/diagnostic，不直接产出 Evidence。
- Evidence 必须来自当前源文件读取，并通过 `content_sha` 与 line range 校验。
- RUN phase 不读取 private labels；SCORE phase 才读取 labels。
- 真实 provider 只在 `workflow_dispatch + enable_remote_models=true + OPENLOCUS_ALLOW_REMOTE=1` 下运行。
- 报告与 artifacts 不上传 provider URL/key、private labels 或 gold answers。Raw snippets 可以在明确 public/opt-in rich-context runs 中发送给 provider，但不应作为 artifacts 提交，除非明确说明。
- unavailable strategy 只能 reason-only，不能输出假质量数字。

质量优先的 public/opt-in remote runs 中可以使用：

- 经过 secret/ignore 过滤后的 raw code snippets/chunks；
- path、symbol、signature、doc heading、neighbor-line context；
- top-k local candidate metadata 和 retrieval scores；
- 用于权衡 quality、cost、latency 的 prompt/context matrices。

---

## 6. 目前真正建立了什么

目前已经比较稳地建立了四件事：

1. **事实层安全约束可执行**：EvidenceCore + materialization + citation validation 不是口号，而是已经贯穿本地检索、store、graph、dense、CI runner 的机制。
2. **本地 lexical/symbol/RRF 仍是主干**：真实模型进场后，并没有取代 RRF/symbol/regex，反而更明确需要它们作为 anchor 与 guard。
3. **真实模型有价值，但高度依赖上下文**：embedding 有 file-level signal，LLM 可扩展 stress/derived views，QuIVer BQ 值得继续；它们都不能直接进入事实层，但后续测试应给模型 richer code context。
4. **实验体系能发现反例**：P4 → P8a、P20-LS offline → remote scale-up 的变化说明系统可以把 tiny 乐观或“只是 schema-safe”的结果拉回现实，这对长期研究非常重要。

---

## 7. 阶段摘要索引

详细阶段报告均保留；本节只是索引，不替代原报告。

### R0-R13：本地事实层与安全脚手架

- R0/R1：local evidence kernel、read/scan/search、trace、citation validation。
- R2：regex/BM25/symbol/RRF local bakeoff。
- R3：StoreHit materialization gate 与 conservative store。
- R4：DerivedIndexView safety scaffold；derived views are not Evidence。
- R5：deterministic graph scaffold；graph output is not direct Evidence。
- R6：deterministic fast-context orchestration scaffold。
- R7-R10：persistent BM25、AST chunking、quality bakeoff、incremental index。
- R11：TDB Level0 adapter probe；metadata/chunks only，无 retrieval quality claim。
- R12：real-repo incremental robustness bench。
- R13：provider/dense safety scaffold with mock embeddings and no remote quality claim。

### R14-R29：benchmark 与失败面扩张

- R14-R16：scaled benchmark foundation、external multi-repo expansion、multi-method bakeoff。
- R17-R19：query router、guard calibration、large/stress guard generalization。
- R20-R23：auto-wide failure-surface dataset、strategy matrix、failure attribution、guard sweep。
- R24-R25：QuIVer/TDB availability probe、dense_mock/graph ablation；graph/dense default expansion blocked。
- R26：auto-stress-1000 static dataset。
- R28：conservative promotion candidate report；no default change。
- R29：R26 strategy matrix；RRF recall strong、symbol precision anchor、query-noise guard promising、graph/dense blocked。

### R30-R45：真实模型准备与诊断扩展

- R30：freeze R29 baseline。
- R31：real embedding provider smoke and safety gates。
- R32：embedding view bakeoff harness。
- R33：QuIVer BQ readiness diagnostics。
- R34-R36：QuIVer/BQ prototype and anchor-seeded dense/quiver experiments。
- R37-R38：LLM-derived views and stress expansion；not Evidence。
- R39-R40：symbol extraction and regex normalization repair tracks。
- R41-R42：graph role research and admission model v2 rules。
- R43-R45：integrated long-run report；no promotion。

### P1-P9：真实 provider 与 CI 逐步放大

- P1：real embedding and LLM smoke，provider access validated。
- P2：bounded real embedding view bakeoff。
- P3：real embedding QuIVer BQ readiness。
- P4：real embedding anchor prototype。
- P5：LLM-derived/stress harness with not-evidence boundary。
- P6：repair/admission replay。
- P7：real-provider summary。
- P8/P9：GitHub Actions public corpus scale-up、model bakeoff、multilingual smoke。

### P20-P25/P30：LLM 放大、策略路由与可解释 admission

- P20-LS/P20-LS-A：低上下文/query-only LLM aliases safety-passed 但 quality-failed；direct low-context alias scale-up blocked。
- P21-G：跨模型 context-injection 阶段，使用 context atoms、context packs、candidate metadata、model profiles、roles、layouts，并记录 latency/cost。P21-G1E 显示 `pack2_evidence_sketch`、`atom_signature` 有 file/span 信号但 naked dense false spans 占主导。P21-G2E 显示 constrained dense 有 modest supporting value（`dense_atom_signature_rrf_file_constrained`），但 dense-only 仍只是 diagnostic/non-primary。P21-G3L 显示 LLM span narrowing 有 promising 但 model/repo-specific 信号；filter/abstain 需要 prompt/bucket routing，GLM 需要 schema repair。
- P25：bucket-routed LLM role policy 评估器。确定性、无远程、只按公开 `task_bucket`/`task_risk_tags` 路由；能降低 false primary 但也会损失一些 gold span；作为 P30 输入有价值，不是默认策略。
- P30：Admission Model V3 研究脚手架。确定性可解释评分卡加 hard guard，只从 pre-SCORE 公开特征路由，比较多个 baseline 和 `admission_v3`/`admission_v3_h1`/`admission_v3_h2`，输出 score bands/selective risk/deltas、action-specific span-cost accounting（P30-H3），并递归扫描公开输出中的禁用键。P30-H1 修复了 missing outcomes；P30-H2 收紧 local-anchor admission 后仍弱于 P25；P30-H3 现在提供诊断性动作成本会计而不改路由。

### C5-A：ContextBench verified 检索性能 smoke

- C5-A：第一个外部-benchmark-形态的检索性能 smoke。从 HF datasets-server `/rows` 读取有界 ContextBench verified subset（默认 5 行；硬上限 20；仅 stdlib `urllib`），在临时 `/tmp` 目录下通过 `git clone --filter=blob:none --no-checkout` 然后 `git checkout` 检出引用仓库到 `base_commit`，运行 OpenLocus `bm25` 检索（无 provider 调用），通过 `eval/score.py` 对 `gold_context` spans 打分，并仅提交 aggregate 公共报告。Schema `c5_contextbench_verified_performance_smoke.v1`、`claim_level=external_benchmark_retrieval_performance_smoke_only`、`status=pass|partial|unavailable_with_reason`、`mode=contextbench_verified_retrieval_performance_smoke`、阶段 `C5-A`。113/113 self-test 检查通过。Safe true 标志（仅当实际为真时为 true）：`external_benchmark_rows_read`、`repositories_materialized_transiently`、`openlocus_retrieval_executed`、`score_py_metrics_computed`、`performance_smoke`、`aggregate_only_public_artifact`、`diagnostic_only`。所有无声明 / 无运行时变更标志为 false（`external_benchmark_performance_claimed`、`downstream_agent_value_proven`、`promotion_ready`、`default_should_change`、`runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、`backend_changed`、`default_policy_changed`、`evidencecore_semantics_changed`、`provider_calls_made`、`remote_provider_calls_made`）。License：`dataset_license_status=unknown_dataset_license`、`row_level_redistribution_allowed=false`、`derived_row_level_publication_allowed=false`、`aggregate_metrics_publication=aggregate_only_smoke`。CI 是单独的手动 opt-in `workflow_dispatch`，带 `enable_external_benchmark_network=true`；无 provider secrets/vars；仅上传 aggregate 报告。如果网络 smoke 无法完成，artifact 为真实的 `unavailable_with_reason`，带真实失败类别（无 stale/fake pass）。C5-A **不是** benchmark 结果、**不是** leaderboard 条目、**不是**性能声称、**不是**promotion、**不是**默认变更、**不是**runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不是**下游 agent 价值声称。见 `docs/en/c5-contextbench-verified-performance-smoke.md`。

### C5-B：ContextBench verified 检索方法矩阵 smoke

- C5-B：C5-A 的有界多方法矩阵扩展。从 HF datasets-server `/rows` 读取有界 ContextBench verified subset **一次**（跨所有方法共享；每方法默认 5 行；硬上限 10；仅 stdlib `urllib`），在临时 `/tmp` 目录下通过 `git clone --filter=blob:none --no-checkout` 然后 `git checkout` 检出引用仓库到 `base_commit`，跨请求方法矩阵运行 OpenLocus 检索（默认 `bm25,regex,symbol`；允许 `bm25,regex,text,symbol`；固定 `baseline_method=bm25`；无 provider 调用），通过 `eval/score.py` 对每种方法针对 benchmark label spans 打分，并仅提交一个 aggregate 公共报告，其中包含每方法记录和仅 aggregate 的、与固定 `bm25` baseline 的 delta。Schema `c5b_contextbench_verified_method_matrix_smoke.v1`、`claim_level=external_benchmark_retrieval_method_matrix_smoke_only`、`status=pass|partial|unavailable_with_reason|fail_schema_contract|fail_forbidden_scan`、`mode=contextbench_verified_retrieval_method_matrix_smoke`、阶段 `C5-B`。161/161 self-test 检查通过。Safe true 标志（仅当实际为真时为 true）：`external_benchmark_rows_read`、`repositories_materialized_transiently`、`openlocus_retrieval_executed`、`score_py_metrics_computed`、`method_matrix_smoke`、`aggregate_only_public_artifact`、`diagnostic_only`。所有无声明 / 无运行时变更标志为 false（`external_benchmark_performance_claimed`、`leaderboard_entry_claimed`、`downstream_agent_value_proven`、`promotion_ready`、`default_should_change`、`baseline_is_policy_candidate`、`runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、`backend_changed`、`default_policy_changed`、`evidencecore_semantics_changed`、`provider_calls_made`、`remote_provider_calls_made`）。License：`dataset_license_status=unknown_dataset_license`、`row_level_redistribution_allowed=false`、`derived_row_level_publication_allowed=false`、`aggregate_metrics_publication=aggregate_only_smoke`。方法 metric allowlist：`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`。`method_results` 是记录列表（**非**以方法名为 key 的 dict）。**不**输出 `winner`、`best_method`、`recommended_default` 或任何暗示策略/默认决策的字段。CI 是单独的手动 opt-in `workflow_dispatch`，带 `enable_external_benchmark_network=true`；无 provider secrets/vars；无 `OPENLOCUS_LLM`/`OPENLOCUS_EMBEDDING` env；仅上传 aggregate 报告。如果网络 smoke 无法完成，artifact 为真实的 `unavailable_with_reason`，带真实失败类别（无 stale/fake pass）。C5-B **不是** benchmark 结果、**不是** leaderboard 条目、**不是**性能声称、**不是**promotion、**不是**默认变更、**不是**runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不是**下游 agent 价值声称。见 `docs/en/c5b-contextbench-verified-method-matrix-smoke.md`。

### C5-C：ContextBench verified 检索方法矩阵 scale smoke

- C5-C：C5-B 的有界 20 行方法矩阵 scale 扩展。从 HF datasets-server `/rows` **一次性**读取有界 20 行 ContextBench verified subset（跨全部 3 个方法共享；每方法默认 20 行；硬上限 20；仅 stdlib `urllib`），在临时 `/tmp` 目录下（每方法+每行一次）通过 `git clone --filter=blob:none --no-checkout` 然后 `git checkout` 检出引用仓库到 `base_commit`，跨请求方法矩阵运行 OpenLocus 检索（默认 `bm25,regex,symbol`；C5-C 仅允许 `bm25,regex,symbol`；**不**允许 `text`；固定 `baseline_method=bm25`；无 provider 调用），通过 `eval/score.py` 对每种方法针对 benchmark label spans 打分，并仅提交一个 aggregate 公共报告，其中包含每方法记录（列表，**非**以方法名为 key 的 dict）、可选的每方法 `aggregate_runtime_seconds`、仅 aggregate 的与固定 `bm25` baseline 的 delta，以及一个 `input_summary` 块。Schema `c5c_contextbench_verified_method_matrix_scale_smoke.v1`、`claim_level=external_benchmark_retrieval_method_matrix_scale_smoke_only`、`status=contextbench_method_matrix_scale_smoke_pass|partial|unavailable_with_reason|fail_forbidden_scan`、`mode=contextbench_verified_bounded_scale_method_matrix`、阶段 `C5-C`。177/177 self-test 检查通过。Safe true 标志（仅当实际为真时为 true）：`retrieval_scale_smoke_performed`、`openlocus_retrieval_executed`、`score_py_metrics_computed`、`aggregate_only_public_artifact`、`diagnostic_only`（C5-C **不**使用 C5-B 的 `method_matrix_smoke` 标志或 C5-A 的 `external_benchmark_rows_read`/`repositories_materialized_transiently`/`performance_smoke` 标志）。所有无声明 / 无运行时变更标志为 false（`external_benchmark_performance_claimed`、`leaderboard_entry_claimed`、`downstream_agent_value_proven`、`promotion_ready`、`default_should_change`、`baseline_is_policy_candidate`、`runtime_behavior_changed`、`retriever_changed`、`pack_builder_changed`、`backend_changed`、`default_policy_changed`、`evidencecore_semantics_changed`、`provider_calls_made`、`remote_provider_calls_made`）。License：`dataset_license_status=unknown_dataset_license`、`row_level_redistribution_allowed=false`、`derived_row_level_publication_allowed=false`、`aggregate_metrics_publication=aggregate_only_smoke`。方法 metric allowlist：`file_recall@10`、`mrr`、`span_f0.5@10`、`success_rate`。`method_results` 是记录列表（**非**以方法名为 key 的 dict）。**不**输出 `winner`、`best_method`、`recommended_default` 或任何暗示策略/默认决策的字段。CI 是单独的手动 opt-in `workflow_dispatch`，带 `enable_external_benchmark_network=true`；无 provider secrets/vars；无 `OPENLOCUS_LLM`/`OPENLOCUS_EMBEDDING` env；仅上传 aggregate 报告。如果网络 smoke 无法完成，artifact 为真实的 `unavailable_with_reason`，带真实失败类别（无 stale/fake pass）。C5-C **不是** benchmark 结果、**不是** leaderboard 条目、**不是**性能声称、**不是**promotion、**不是**默认变更、**不是**runtime/retriever/pack/backend/EvidenceCore 语义变更，也**不是**下游 agent 价值声称。见 `docs/en/c5c-contextbench-method-matrix-scale-smoke.md`。

关键详细报告：

- `docs/final-research-report.md` — R0-R29 historical report。
- `docs/research-summary.md` — stage-by-stage status summary。
- `docs/r29-r26-stress-matrix.md` — R29 matrix and failure clusters。
- `docs/r45-promotion-candidate-report.md` — R30-R45 conclusion checkpoint。
- `docs/real-provider-p7-summary.md` — P1-P6 real-provider summary。
- `docs/real-provider-ci-scale-p8-p9.md` — first CI scale-up results。
- `docs/zh/real-provider-ci-large-scale.md` — L1/L2 大型真实-provider测试结论。
- `docs/p20-llm-large-scale.md` — P20-LS-A 低上下文 LLM alias scale-up 结果。
- `docs/p21-g-cross-model-context-injection.md` — P21-G 跨模型 context-injection 计划。
- `docs/p25-bucket-routed-policy.md` — P25 bucket-routed LLM role policy。
- `docs/p30-admission-model-v3.md` — P30 Admission Model V3 报告。
- `docs/p30-admission-model-v3-remote-smoke.md` — 第一轮 P30 真实 remote smoke。
- `docs/p30-h1-remote-smoke.md` — P30-H1 enriched handoff 真实 remote smoke。
- `docs/p30-h2-remote-smoke.md` — P30-H2 stricter local-anchor admission 真实 remote smoke。
- `docs/p30-h3-span-cost-accounting.md` — P30-H3 action-specific span-cost accounting（仅诊断、仅 SCORE 阶段、不改路由）。
- `docs/p30-h3-remote-smoke.md` — P30-H3 真实 remote smoke 的 action-cost 诊断。
- `docs/en/c5-contextbench-verified-performance-smoke.md` — C5-A ContextBench verified 检索性能 smoke（aggregate-only；外部 benchmark 检索 smoke；不是 benchmark 结果、不是 leaderboard 条目、不是性能声称、不是 promotion、不是默认变更、不是下游 agent 价值声称）。
- `docs/en/c5b-contextbench-verified-method-matrix-smoke.md` — C5-B ContextBench verified 检索方法矩阵 smoke（aggregate-only；多方法矩阵 smoke；默认 bm25,regex,symbol；固定 baseline_method=bm25；每方法记录；仅 aggregate 的与 bm25 的 delta；无 winner/best_method/recommended_default；不是 benchmark 结果、不是 leaderboard 条目、不是性能声称、不是 promotion、不是默认变更、不是下游 agent 价值声称）。
- `docs/en/c5c-contextbench-method-matrix-scale-smoke.md` — C5-C ContextBench verified 检索方法矩阵 scale smoke（aggregate-only；有界 20 行方法矩阵 scale smoke；仅 bm25,regex,symbol（无 text）；固定 baseline_method=bm25；每方法记录带可选 aggregate_runtime_seconds；仅 aggregate 的与 bm25 的 delta；input_summary 块；无 winner/best_method/recommended_default；不是 benchmark 结果、不是 leaderboard 条目、不是性能声称、不是 promotion、不是默认变更、不是下游 agent 价值声称）。

---

## 8. 下一步研究问题

下一步不是 promotion，而是更大、更细、更可复现的验证：

1. 将 L2 task set 固定为可复现 suite，避免 task generation drift。
2. 在 public/opt-in corpus 上跑 P21-G context atom screening：signatures、matched lines、retrieval scores、flags、body windows、neighbors、related tests、hard distractors。
3. 在完成 false-span analysis 后，再把 P3/P4 扩到更多 repo。
4. 在同一任务集上继续比较 bge-m3 与 Qwen 0.6B/4B/8B，加入 latency/cost。
5. 把 P5 stress traps 接入 anchored dense/QuIVer 验证，看 added_gold 是否持续大于 added_false。
6. 在 R26/R38 上复验 symbol repair 和 regex normalization，重点看 bucket regression。
7. 把 real dense support score 接入 admission_v2 研究，但只作为 supporting feature。
8. 继续 QuIVer sharding/prototype，直到有 graph/ANN 后端质量证据再谈 QuIVer quality。
9. 如果重新研究 LLM query aliases，只测试 grounded variants：从 inventories 中选择 aliases，或在看到 top-k local candidate snippets 后生成 aliases。
10. 跑 P21-G rich LLM candidate support：在 snippet-backed local candidates 上 rerank/filter/span-narrow/abstain/inventory_alias，记录 model-averaged/per-model effects，并报告质量、latency、token、cost trade-off。
11. P30-H3：为 weak/supporting/filter outcomes 加入 action-specific span-cost accounting 和 false-span budgets，然后再继续 route tuning。

---

## 9. 当前一句话总结

OpenLocus 目前已经建立了一条质量与证据双重约束的研究路线：本地 lexical/symbol/RRF 是事实检索主干；真实 embedding、QuIVer、LLM-derived、graph 只有在 grounded 与 validated 时才有价值。L1/L2 证明 dense-only/global dense 不能 primary/default；P20-LS-A 证明低上下文/query-only LLM aliases 不能按当前形式扩大。下一阶段的关键问题是：哪些 context atoms、packs、roles、layouts 和 model profiles 能让 real-model retrieval 跨模型稳定增加 gold，同时不以不可接受的 latency/cost 增加 false-primary 与 false-span。P30 提供了一个确定性的可解释 admission 脚手架，用于横向比较这些策略面。
