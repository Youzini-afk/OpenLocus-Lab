# B19 理论综合 —— Model-Robust Selective Evidence Conversion

日期：2026-06-19

B19 是 B10-B18 Breakthrough Sprint 的 **理论综合**。它是 **仅综合**：**不**运行任何 provider，**不**修改 retrieval / default / EvidenceCore，**不**声明 promotion。它把 B10 / B10B / B11 / B12 / B13 / B14 / B15 / B16 / B17 / B18 综合成一份关于候选算法概念 **Model-Robust Selective Evidence Conversion** 的论文式算法报告。

> **重要 claim 边界。** B19 是综合，**不是**新实验。`is_synthesis_only=true`、`is_new_experiment=false`、`ran_providers=false`、`new_provider_calls=0`、`changed_retrieval_default_evidencecore=false`。本综合仅 carry forward 已发布的 B10-B18 public-aggregate 结论，**不**引入任何新的 empirical claim。所有 no-promotion 标志均显式为 false：`promotion_ready=false`、`default_should_change=false`、`evidencecore_semantics_changed=false`、`runtime_clean_policy_supported=false`、`downstream_agent_value_proven=false`、`ood_temporal_supported=false`、`quiver_systems_supported=false`。**不**引入任何伪造 metrics；唯一逐字 carry forward 的 empirical 数字是 B11 official integrated matrix 的 deltas（balanced_v1 vs p25），self-test 会逐字节断言它们与源 aggregate artifact 一致。

> **CRITICAL 反伪造边界。** 本综合**绝不可**在 B10-B18 之外引入新的 metrics、新的 verdict 或新的 claim。B12 / B13 / B14 / B15 / B16 / B17 / B18 的 no-go / screen-only / prior-screen 状态**原样** carry forward。B11 `partial_with_failure` **原样** carry forward。B10 `runtime_clean=false` 与 B10B `runtime_shadow_ambiguous_supported=false` **原样** carry forward。综合中的 prose 是对 B10-B18 evidence boundary 的重述，**不是**新 evidence。

> **公共 artifact 边界。** B19 公共 artifact（`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`）是 aggregate-only，禁止 raw records / paths / spans / snippets / prompts / responses / gold labels / `content_sha` / provider keys / api keys。self-test 运行一个 B19 专用的 forbidden-key scan（forbidden keys + digest-like values，报告自身的 drift-guard self-hash 被白名单豁免）并断言其干净。

## 算法概念

**Model-Robust Selective Evidence Conversion** 是一个 model-robust、runtime-clean、evidence-gated 的策略：通过把 recall 与 admission 解耦、选择性路由 LLM 角色、并在跨 model adapter 上优化 worst-group utility，将高召回 / 高错误代价的本地候选池选择性地转换为 current-source `EvidenceCore` spans。

### 输入

- `query`
- `local_candidate_pool`
- `runtime_observable_uncertainty`
- `model_capability_profile`
- `latency_cost_budget`

### 输出 / 动作

- `local_only`
- `weak_or_supporting`
- `llm_span_narrow`
- `llm_filter`
- `abstain`
- `request_more_context`
- `evidencecore_materialization`

每个被选中的动作都必须终止于一个 current-source `EvidenceCore` 物化（path + start_line + end_line + content_sha + score + why + channels）或一个显式的 abstain / request-more-context 信号。任何动作都**不得**把候选、LLM 输出或 supporting view 作为 Evidence 发出。

### 核心原则

1. **Recall / admission 解耦** —— 召回来自本地候选；admission 是单独的决策。
2. **LLM 角色选择性路由** —— `span_narrow` / `filter` 仅在 runtime predicate 命中且预算允许时触发；LLM 永不作为全局默认 pass。
3. **算法 / model-adapter 分离** —— `algorithm_spec` 是 model-independent 的（仅 runtime features + 抽象 capability slots）；`model_adapter`（模型身份 + 输出模式 + provider 凭据）是被排除的 adapter 层。
4. **仅运行期可观测特征（用于 runtime-clean 策略）** —— 无 benchmark-private labels（`task_bucket`、`task_risk_tags`）、无 score-private 字段（`has_gold`、`score_group`、outcome metrics）、`algorithm_spec` 中无原始模型名。
5. **Worst-group / 跨模型鲁棒优化** —— 优化 `min_group(SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency)`，而非 in-distribution average。
6. **候选必须物化进 current-source EvidenceCore** —— current-source 读取是最终事实权威；stale / 不匹配的 `content_sha` 候选被拒绝。

## 问题陈述

本地候选池（RRF、symbol/regex、dense）经常能命中 gold file/span，但带有高 false-span 与 primary-false-positive 代价。一次全局 LLM pass 在混合 task buckets 上不安全，而 benchmark-routed 策略无法 promotion，因为它依赖运行期不可得的 labels。问题在于：如何在不削弱 evidence 契约、不让任一模型的行为成为 OpenLocus 算法、不把 in-distribution average 误读为跨模型 / OOD / temporal generalization 的前提下，把高召回 / 高错误代价的候选转换为低错误代价、citation-valid 的 `EvidenceCore` spans。

## 算法草稿（伪代码）

```text
function CONVERT(query, local_candidate_pool, runtime_uncertainty,
                 model_profile, latency_cost_budget):
    # 1. RUN-phase routing 仅使用 runtime-observable features。
    feats = observe_runtime_features(local_candidate_pool, query)
    if not feats.all_present:
        return ACTION_REQUEST_MORE_CONTEXT
    # 2. Recall / admission 解耦：召回来自本地候选；admission 是单独决策。
    recall_pool = local_candidate_pool
    # 3. Worst-group / 跨模型鲁棒动作选择。
    action = robust_select(
        features=feats,
        uncertainty=runtime_uncertainty,
        model_profile=model_profile,
        budget=latency_cost_budget,
        objective=RobustUtility_worst_group,
        adapter=model_adapter,  # 不属于 algorithm_spec
    )
    # 4. LLM 角色是选择性的：仅当 runtime predicate 命中且预算允许时触发 span_narrow / filter。
    if action in {LLM_SPAN_NARROW, LLM_FILTER}:
        llm_view = model_adapter.call(action, recall_pool, budget)
        llm_view.not_evidence = True
    # 5. 候选必须物化进 current-source EvidenceCore。
    evidence = materialize_current_source_evidencecore(action, recall_pool, llm_view)
    if evidence is None:
        return ACTION_ABSTAIN or ACTION_REQUEST_MORE_CONTEXT
    return evidence  # EvidenceCore: path, start_line, end_line,
                     # content_sha, score, why, channels
```

## 证据边界

每个被选中的动作都必须终止于一个 current-source `EvidenceCore` 物化（path + start_line + end_line + content_sha + score + why + channels）或一个显式的 abstain / request-more-context 信号。LLM 输出仅是 `not_evidence=true` 的候选 / supporting channels；它们可以 narrow、filter 或 disambiguate，但**绝不**可成为 Evidence，**绝不**产出 gold labels，**绝不**产出 citation verdicts，**绝不**产出 promotion verdicts。current-source 读取是最终事实权威；stale / 不匹配的 `content_sha` 候选被拒绝。

## 策略学习循环

该循环为：

1. 冻结一个仅使用 runtime-observable features 的 `algorithm_spec`。
2. 运行一个 preregistered、no-retuning 的 prospective validation（B11）。
3. 通过 per-record replay 分解机制（B12，需要 per-record 数据）。
4. 搜索一个 worst-group / 跨模型鲁棒策略（B13，需要 per-record group/action outcomes）。
5. 校准一个 model-independent 的 uncertainty score（B14，需要 per-record (uncertainty, outcome) pairs）。
6. 从 per-record atom effects 学习一个冻结的 PackPolicy（B15，需要 per-record atom flags）。
7. 评估 downstream agent value（B16，需要 paired agent runs）。
8. 评估 OOD / temporal generalization（B18，需要 per-record time axis）。

每个缺少所需 per-record inputs 的循环迭代都会发出 no-go / prior-screen / `insufficient_data` verdict，且**不**自动 promotion。Promotion 是一个单独的、未来的、evidence-gated 决策；它**绝不**是循环本身的输出。

## Adapter 边界

`algorithm_spec` 是 model-independent 的：它只引用 runtime-observable `route_features` 与抽象 `model_profile` capability slots（`cost_class`、`latency_class`、`supports_reliable_span_narrow`、`family_slots`）。`model_adapter`（模型身份 + 输出模式 + provider 凭据 / endpoints / secrets）是被排除的 adapter 层，**不**属于 algorithm spec。输出模式（`tool_call` / `json_schema_strict`）是 model-adapter 配置参数，**不**是 OpenLocus 算法变量。一个 noisy adapter 不能成为关于算法的质量结论，一个算法质量 claim 也不能作为 adapter leaderboard 被偷运进来。

## 评估协议

Prospective、preregistered、no-retuning validation。Success / partial / failure 标准在任何 live runs **之前**冻结，使用显式的 overall 与 worst-group 阈值（`Δgold_span`、`ΔSpanF0.5`、`ΔPFP`、`Δfalse_spans`、`ΔLLM_calls`），加上一个 worst-group `RobustUtility = min_group(SpanF0.5 - λ*PFP - μ*normalized_cost - ν*normalized_latency)`，其中 `λ=1.0`、`μ=0.1`、`ν=0.1`。validation 使用 rotating leave-one-model-family-out rotations 与 stratified fresh-validation splits。Per-record replay 是机制（B12）、DRO（B13）、calibration（B14）、pack policy（B15）、downstream agent value（B16）、QuIVer systems（B17）与 OOD / temporal（B18）的 evidence boundary。公共 artifacts 是 aggregate-only；per-record records 留在 runner temp 下。

## 综合证据（B10-B18）

- **B10** —— `balanced_policy_v1_benchmark_routed` 是 benchmark-routed，**不是** runtime-clean。`_ambiguous_like` 分支读取 benchmark public labels `task_bucket` / `task_risk_tags`，因此一个 runtime-feature-only 模式**绝不**会触发 `ambiguous_query_weak_only` 规则。`runtime_clean=false`、`runtime_feature_only_mode_supported=false`。Claim level：`benchmark_routed_algorithm_spec_only`。
- **B10B** —— 提供了一个 mechanics-validated 的 runtime-shadow scaffold + CI 集成。empirical support 处于 pending，因为在所有 B11 runs 中 label-driven ambiguous denominator 都低于 10-record hard gate（最大观测 `label_driven_ambiguous_denominator_qn0=3`）。synthetic fixture 上的 verdict：`mechanics_only_synthetic_fixture`；CI records 上：`empirical_replay_support_pending`。Claim level：`ambiguous_branch_runtime_shadow_only`。
- **B11** —— Official integrated matrix：32/32 final cells、384 records、aggregate verdict `partial_with_failure`（success 8 / partial 23 / failure 1）。Balanced v1 vs P25 deltas：`Δgold_span -0.002604`、`ΔSpanF0.5 -0.001899`、`Δfalse_span -0.054688`、`ΔPFP -0.020833`、`Δmodel_calls -0.354167`。加强了 algorithm-candidate signal，但**不**是 promotion。Claim level：`derived_aggregate_of_b11_prospective_validation_reports`。
- **B12** —— public aggregate 无法识别机制。完整的 B12 per-record replay 从 public B11 aggregate 无法完成：它缺少 per-record route decisions、ambiguous-subset membership、deterministic call-reduction variant B、random call-reduction variant E 与 `weak_candidate_only` per-strategy outcomes。仅发出 per-hypothesis screen statuses，**绝不**发出单一全局 `supported` verdict。Claim level：`bounded_public_aggregate_mechanism_screen_of_b11_aggregate`。
- **B13** —— public aggregate 无法运行真实 DRO search。真实 B13 需要 per-record group / action outcomes 与基于 per-record records 的 rotating leave-one-model-family-out rotations。Verdict：`no_go_public_aggregate_only`。Claim level：`bounded_public_aggregate_feasibility_screen_of_b11_b12_aggregates`。
- **B14** —— 无法从 public aggregates 校准 uncertainty。真实 B14 需要 per-record uncertainty scores、per-record binary outcomes、paired cross-model outputs、schema-repair per-call rows 与 candidate score distributions。Verdict：`no_go_public_aggregate_only`。Claim level：`bounded_public_aggregate_feasibility_screen_of_b11_b12_b13_aggregates`。
- **B15** —— 无法从 public aggregates 学习 Context Pack Policy。真实 B15 需要 per-record pack atom flags、per-record outcomes、role-specific paired outputs、model_profile paired blocks、randomized atom assignment、balance stats 与 token-budget-matched controls。B15 当前价值仅是 preregistration / prior screen（B2 仅可作为 `low_n_single_model_aggregate_directional_prior` 使用）。Verdict：`prior_screen_only`。Claim level：`bounded_public_aggregate_prior_screen_of_b2_b14_and_optional_aggregates`。
- **B16** —— downstream agent value 未被证明。真实 B16 需要 paired live downstream agent runs、per-run patches/diffs、test execution results、solve labels、first-file-before-first-edit events、wrong-file-edit annotations、tool-call/token/latency/cost rows、isolated workspace proof、randomized arm order 与 task oracle/hidden-test manifest。retrieval 改进**不**是 downstream agent 改进。Verdict：`no_go_public_aggregate_only`。Claim level：`bounded_public_aggregate_feasibility_screen_of_b11_b12_b13_b14_b15_aggregates`。
- **B17** —— QuIVer systems track 是 no-go，因为 QuIVer graph / vector backend 缺失。现有 R33 / R34 / R36 / R24 与 real-provider P3 / P4 诊断是 diagnostic-only carry-forward：它们**不**实现 QuIVer / Vamana graph backend，**不**包含 HNSW run，**不**包含跨 backends 的 candidate-set equivalence matrix。这是一个仅 systems 的未来 track。Verdict：`no_go_quiver_graph_missing`。Claim level：`bounded_public_systems_diagnostic_carry_forward_screen_of_r33_r34_r36_real_p3_p4_r24`。
- **B18** —— OOD / temporal evaluation 从 public aggregate 是 no-go。真实 B18 需要 per-record temporal / repo / language / model_family / adversarial axes，带真实 time axis 与 commit chronology。public B11 aggregate 仅带 weighted means 与 sanitized failure slice list；R15 / R20 / R26 repo locks 是 synthetic static snapshots。Verdict：`no_go_public_aggregate_only`。Claim level：`bounded_public_aggregate_no_go_screen_of_b11_r15_r20_r26`。

## 当前 empirical 证据

当前最强的 empirical signal 是 B11 official integrated matrix（32/32、384 records）：balanced_v1 vs p25 deltas 在平均意义上保持近持平 SpanF0.5 / gold_span，同时减少 false_span、PFP 与 model_calls。

```text
aggregate_verdict: partial_with_failure
verdict_counts:    {success: 8, partial: 23, failure: 1}
b10b_runtime_shadow_status: empirical_replay_support_pending_due_denominator

deltas_balanced_v1_vs_p25:
  gold_span                    : -0.002604
  span_f0_5                    : -0.001899
  false_span                   : -0.054688
  primary_false_positive_rate  : -0.020833
  model_calls                  : -0.354167
```

当前 empirical 证据加强了 algorithm-candidate signal，但**不**证明一个 runtime-clean general algorithm。B10B runtime-shadow predicate 处于 empirical-pending（在所有 B11 runs 中 label-driven denominator < 10）。B11 是 mixed / partial；一个 Kimi `py_fastapi` slice 超过了 `failure_spanf05_delta` 阈值。

## No-go gaps

- **B12** —— public aggregate 无法识别机制。缺失：per-record route decisions、ambiguous-subset membership、variant B、variant E、`weak_candidate_only` per-strategy outcomes。
- **B13** —— public aggregate 无法运行真实 DRO search。缺失：per-record group/action outcomes、基于 per-record records 的 rotating leave-one-model-family-out rotations。
- **B14** —— 无法从 public aggregates 校准 uncertainty。缺失：per-record uncertainty scores、per-record binary outcomes、paired cross-model outputs、schema-repair per-call rows、candidate score distributions。
- **B15** —— 无法从 public aggregates 学习 Context Pack Policy。缺失：per-record pack atom flags、per-record outcomes、role-specific paired outputs、model_profile paired blocks、randomized atom assignment、balance stats、token-budget-matched controls。
- **B16** —— downstream agent value 未被证明。缺失：paired live agent runs、per-run patches/diffs、test execution results、solve labels、first-file-before-first-edit events、wrong-file-edit annotations、每次运行的 tool-call/token/latency/cost、isolated workspace proof、randomized arm order、task oracle/hidden-test manifest。
- **B17** —— QuIVer systems track no-go：graph / vector backend 缺失。缺失：QuIVer/Vamana graph backend 实现、HNSW backend run、跨 backends 的 candidate-set equivalence matrix、shared frozen candidate-quality manifest。
- **B18** —— OOD / temporal 从 public aggregate 是 no-go。缺失：per-record records、time axis、commit chronology、per-repo-per-language cells、model_family x repo matrix、adversarial holdout outcomes、temporal holdout outcomes。

## Promotion blockers

1. B10 `runtime_clean=false`：冻结的 `balanced_policy_v1` 是 benchmark-routed，**不**是 runtime-clean。
2. B10B 在所有 B11 runs 上 `runtime_shadow_ambiguous_supported=false`（label-driven denominator < 10 hard gate）。
3. B11 `aggregate_verdict=partial_with_failure`（一个 Kimi `py_fastapi` slice 超过 `failure_spanf05_delta`）。
4. B12 / B13 / B14 / B15 / B16 / B17 / B18 均为 public-aggregate no-go 或 screen-only；均不授权 promotion。
5. 在任何当前 public artifact 中均不存在 per-record mechanism、DRO、calibration、pack-policy、downstream-agent、QuIVer 或 OOD/temporal 证据。
6. Promotion 是一个单独的未来 evidence-gated 决策；B10-B18 sprint **不**产生它。

## 下一步研究计划

1. 用纯 runtime features（`query_noise`、`candidate_support_exists`、anchor disagreement）替换 benchmark-routed ambiguous 分支，并在真实 CI ephemeral records 上运行 B10B，直到 10-record hard gate 通过。
2. 收集 per-record route / action / group outcomes，使 B12 mechanism decomposition 与 B13 DRO search 能真正运行。
3. 收集 per-record (uncertainty, binary outcome) pairs，使 B14 能校准一个 model-independent 的 uncertainty score。
4. 收集 per-record pack atom flags + role + runtime_state + model_profile，使 B15 能学习一个冻结的 PackPolicy。
5. 搭建一个固定的 downstream agent harness，带 isolated fresh workspaces、randomized arm order 与 patch/test outcome 捕获，使 B16 能证明（或反驳）downstream value。
6. 实现一个 QuIVer / Vamana graph backend 与一个 shared frozen candidate-quality manifest，使 B17 能运行真实的 systems bakeoff。
7. 收集 per-record temporal / repo / language / model_family / adversarial axes，带真实 time axis 与 commit chronology，使 B18 能在 no-retuning protocol 下运行真实的 OOD / temporal evaluation。
8. 仅在上述完成之后，再开启一个单独的 promotion preregistration；综合本身**绝不**授权 promotion。

## 结论

```text
promotion_ready                     : false
default_should_change               : false
evidencecore_semantics_changed      : false
runtime_clean_policy_supported      : false
downstream_agent_value_proven       : false
ood_temporal_supported              : false
quiver_systems_supported            : false
is_synthesis_only                   : true
is_new_experiment                   : false
ran_providers                       : false
new_provider_calls                  : 0
changed_retrieval_default_evidencecore : false
aggregate_only_public_artifact      : true
forbidden_public_scan_clean         : true
report_drift_guarded                : true
```

B10-B18 Breakthrough Sprint 加强了 **Model-Robust Selective Evidence Conversion** algorithm-candidate signal（B11 近持平 SpanF0.5 / gold，同时减少 false-span、PFP 与 model calls），但**不**证明一个 runtime-clean general algorithm，**不** promotion，**不**修改 defaults，**不**修改 EvidenceCore 语义。每个下游阶段（机制、DRO、校准、pack policy、downstream agent、QuIVer systems、OOD / temporal）目前都因缺失 per-record 数据而被阻塞。本综合是一个研究候选，**不是** promotion。

## Artifacts

- `artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`（aggregate-only 机器可读综合；schema `b19-theoretical-synthesis-report-v0`；claim level `theoretical_synthesis_of_b10_through_b18`；所有 no-promotion 标志为 false；B11 deltas 精确；forbidden public scan 干净；报告内容 hash drift-guarded；无 raw records / paths / spans / snippets / prompts / responses / gold labels / content_sha / provider keys / api keys）
- `eval/b19_theoretical_synthesis.py`（pure Python；`--self-test` 只读验证 required sections、no-promotion flags、B11 deltas、forbidden scan、docs links、drift guard；`--regenerate-artifacts` 重写 canonical report 并重跑 self-test；`--input` 是一个 `not_implemented` stub，因为 B19 是 synthesis-only）

## 哪些可自动完成 vs. 需要用户动作

### 可自动完成（本次 commit）

- B19 综合文档（本文件 + `docs/en/b19-theoretical-synthesis.md`）
- B19 综合报告 JSON（`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`）
- B19 evaluator（`eval/b19_theoretical_synthesis.py`），带只读 `--self-test` 与显式 `--regenerate-artifacts` 修改路径
- `docs/en/research-summary.md`、`docs/zh/research-summary.md`、`docs/en/current-research-conclusions.md`、`docs/zh/current-research-conclusions.md`、`docs/en/research-log.md`、`docs/zh/research-log.md` 中的 B19 条目

### 需要前瞻性 per-record 数据收集（非本次 commit）

- B10B runtime-shadow empirical support（在真实 CI ephemeral records 上运行，直到 10-record hard gate 通过）
- B12 mechanism decomposition per-record replay
- B13 DRO search（基于 per-record group/action outcomes）
- B14 uncertainty calibration（基于 per-record (uncertainty, outcome) pairs）
- B15 PackPolicy learning（基于 per-record atom flags）
- B16 downstream agent evaluation（基于 paired live agent runs）
- B17 QuIVer systems bakeoff（在 graph backend 存在之后）
- B18 OOD / temporal evaluation（基于 per-record temporal axes）

### 需要用户评审

- 结果解读
- 是否开启一个单独的 promotion preregistration 的决策（综合本身**绝不**授权 promotion）

详见 [`current-research-conclusions.md`](current-research-conclusions.md) 中的 B10-B19 bottom line。
