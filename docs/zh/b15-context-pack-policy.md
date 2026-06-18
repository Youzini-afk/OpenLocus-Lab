# B15 Context Pack Policy

Date: 2026-06-18

B15 是 **context pack policy** 阶段。目标是产出一个 **frozen、preregistered
的 PackPolicy**，将 `(role, runtime_state, model_profile)` 映射到一组确定
的 **atom set**（一个 context pack 在给定 decision role、runtime state 与
abstract model profile 下应当暴露的 pack-layout atoms），并基于 B11/B13
live runs 的 per-record pack atom flags + per-record outcomes + role +
runtime_state + model_profile + group membership 进行验证。

B15 是一个 **bounded planning / feasibility 阶段**，**不是** empirical
atom-level ablation。当前 skeleton **不**执行任何 empirical atom ablation，
也**不**进行 PackPolicy learning。frozen preregistration
（`eval/b15_context_pack_policy.py`）定义了 PackPolicy 契约、atom registry、
role 集合、runtime_state 契约、model_profile 抽象、metric registry、hard
gates 与 experimental structure（no-LLM feasibility → fractional factorial
live atom screen → freeze candidate policy → fresh validation）；位于
`eval/b15_public_aggregate_prior_screen.py` 的 bounded public-aggregate
prior / no-go screen 读取已发布的公共 aggregates（包括作为弱 directional
prior 的 B2 contrastive-pack experiment），并发出 `no_go_public_aggregate_only`
或 `prior_screen_only` verdict。

> **重要 claim 边界。** B15 **是** context-pack-policy *stage*
> （`stage_is_context_pack_policy=true`），但当前 skeleton **不**执行任何
> empirical atom ablation（`atom_ablation_performed=false`），也**不**进行
> PackPolicy learning（`pack_policy_learned=false`）。synthetic-fixture /
> `--input` stub 报告设置 `per_record_inputs_available=false`、
> `promotion_ready=false`、`default_should_change=false`、
> `evidencecore_semantics_changed=false`、`policy_search_performed=false`、
> `quality_strategy_tuned=false`、`new_provider_calls=0`，使该公共 artifact
> 不会被误读为 empirical B15 PackPolicy 结果。本 commit 严格是
> skeleton / no-go commit：当前 flags（`pack_policy_learned=false`、
> `atom_ablation_performed=false`、`promotion_ready=false`、
> `default_should_change=false`、`evidencecore_semantics_changed=false`）
> 保持 false。任何未来真实的 B15 empirical 路径都需要其自身的单独
> preregistration；该未来路径的精确 flag schema（包括任何
> `pack_policy_learned` / `atom_ablation_performed` 设置）是 future work，
> **不**存在于当前 skeleton 中。本 commit 中的 B15 结果仅是 research
> candidates：它们指导未来的 context-pack routing，但本 skeleton/no-go
> commit 不授权任何 default change、任何 policy promotion、任何 PackPolicy
> promotion 或任何 EvidenceCore 修改。

> **重要 public-aggregate 边界。** 真实的 B15 PackPolicy preregistration +
> validation 需要私有 / ephemeral 的 per-record inputs：per-record pack atom
> flags（pack 中包含哪些 atoms）、per-record outcomes（所选 span / candidate
> 是否正确）、role-specific paired outputs（同一 record 在不同 role 下被回答）、
> runtime_state per record（candidate pool 形状、score distribution、
> schema-repair 状态）、model_profile paired blocks（同一 record 在不同
> abstract capability profiles 下被回答）、用于 worst-group split 的 group
> membership，以及 randomized atom assignment + balance stats。这些在当前
> 任何公共 artifact 中均不存在。位于
> `eval/b15_public_aggregate_prior_screen.py` 的 bounded public-aggregate
> prior / no-go screen 读取已发布的 B2 pack experiment、B14 public-aggregate
> feasibility report，以及（当存在时）B4-B9 / P21-G / P49 公共 aggregates，
> 在 `artifacts/b15_context_pack_policy/` 下发出
> `no_go_public_aggregate_only`（或当至少 B2 directional prior 可用时为
> `prior_screen_only`）报告。该 screen 从不声称 empirical PackPolicy
> learning，从不从 aggregate means 计算 atom-effect metric，也从不声明
> winner。

> **CRITICAL 反伪造边界。** skeleton **绝不可**从 aggregate means 计算伪造
> 的 atom-effect 指标。aggregate means（例如 B2 pack-layout 的聚合
> SpanF0.5 / PFP）不包含 per-record (atom_flag, outcome) pairs，因此从中
> 计算的任何 atom-level causal effect 都是伪造。B2 pack experiment **仅**
> 可作为 `low_n_single_model_aggregate_directional_prior`（一个弱 directional
> 提示：contrastive structure 并非自动更好），**不能**作为 atom-level
> causality、role-specific PackPolicy 或 calibrated policy 证明。synthetic
> fixture 仅验证 atom registry、role 集合、runtime_state 契约、model_profile
> 抽象、metric names 与 hard gates 已正确接线；它**不**把 synthetic
> atom-effect values 当作 empirical B15 结果呈现。报告 surface
> `atom_ablation_performed=false`、`pack_policy_learned=false` 与
> `no_fake_atom_effects_from_aggregate_means=true`，使读者无法将 skeleton
> 误读为 empirical B15 PackPolicy 结果。

## Preregistration declaration

下列 artifacts、PackPolicy 契约、atom registry、role 集合、runtime_state
契约、model_profile 抽象、metric registry、hard gates、experimental
structure 与 predeclared success/failure criteria 均在任何 B15 empirical
runs 之前 **FROZEN**。B15 empirical runs 开始后，不允许对 atom registry、
role 集合、runtime_state 契约、model_profile 抽象、metric registry、hard
gates 或 success criteria 进行 retuning。任何 post-hoc analysis 必须标注为
exploratory，并需要单独的 validation round。

### Frozen artifacts

- `balanced_policy_v1_benchmark_routed`（B10 frozen spec）—— 仅引用，不修改
- `balanced_policy_v1_runtime_shadow_ambiguous_branch`（B10B shadow
  predicate）—— 仅引用，不修改
- B11/B12/B13/B14 frozen criteria —— 仅引用，不修改
- B15 algorithm spec 自身
  （`artifacts/b15_context_pack_policy/b15_context_pack_policy.algorithm.json`）
  —— 在任何 PackPolicy runs 之前冻结；stable sha256
- 引用的现有 pack layouts（仅定义，不修改）：
  `topk_plain_v0`、`topk_scores_provenance_v0`、
  `contrastive_competitor_v0`、`hard_distractor_contrast_v0`
  （来自 `eval/p21_llm_rich_candidate.py` 的 `PACK_LAYOUTS`）、P49
  contrastive candidate pack scaffold，以及 P21-G atom/pack experiments

## Objective

产出一个 **frozen、preregistered 的 PackPolicy**：

```text
PackPolicy(role, runtime_state, model_profile) -> atom set
```

将一个 decision role、一个 runtime state 与一个 abstract model profile
映射到 context pack 应当暴露的确定性 pack-layout atom 集合。PackPolicy
在 B15 内部**不**被学习；它由 preregistration + bounded live atom screen
冻结，再进行 fresh validation。B15 **不**学习 LLM，**不**改变 EvidenceCore，
**不** promote default，也**不**声称 atom-level causal 结论。

## Roles

PackPolicy 以 pack 所服务的 decision role 为索引。Roles 为 FROZEN：

- `span_narrow` —— 将 top-k candidate pool 收窄到最相关的 span(s)
- `filter_reject` —— 拒绝不应进入 EvidenceCore 的 false-positive candidates
- `request_more_context` —— 判断当前 pack 是否足够，或是否需要更多 context
  （neighbor window、更大的 top-k、source materialization）
- `source_test_disambiguation` —— 通过 surfacing source-backed test / type /
  signature atoms，在同 anchor / 同 path candidates 之间消歧

一条 PackPolicy row 为 `(role, runtime_state, model_profile) -> atom set`。
相同的 `(runtime_state, model_profile)` 在不同 role 下可映射到不同 atom
sets。

## Runtime state contract

`runtime_state` 是 candidate pool 与 request state 在 pack 组装时刻的
model-independent、label-free 描述。它仅由 runtime-observable features 计算；
**不**包含 benchmark-private labels、**不**包含 score-private fields、**不**
包含 raw model names。允许的 runtime_state features（FROZEN）：

- `candidate_count`
- `candidate_support_exists`
- `score_distribution_spread`
- `top1_top2_score_gap`
- `anchor_disagreement`
- `rrf_backed_by_anchor`
- `dense_support_present`
- `path_kind_inferable`
- `neighbor_context_available`
- `signature_available`
- `hard_distractor_proxy_available`
- `same_file_competitor_present`
- `schema_repair_invoked`

> 注意：`path_kind_inferable` 是一个 runtime_state feature（对 candidate
> path kind 的粗粒度推断，label-free）。而 `path_kind_flag` 是一个 pack
> **atom**（在 pack 内 surface 的 flag）。两者故意区分，不要混淆。

## Model profile abstraction

`model_profile` 是一个 **abstract capability profile**，**不是** raw model
name。PackPolicy 必须使用 abstract capability slots（`profile_slot_a`、
`profile_slot_b`、`profile_slot_c`、`profile_slot_d`）以及 capability
descriptors。B15 在 `algorithm_spec` 中**不得**引用 "Kimi"、"Qwen"、
"DeepSeek" 或 "GLM" 等 raw model names。abstract capability descriptors
（FROZEN）：

- `long_context_window`
- `structured_output_stable`
- `span_narrow_strict`
- `hard_distractor_sensitive`
- `score_provenance_sensitive`
- `neighbor_context_sensitive`

一个 `model_profile` 是附加到 abstract slot 上的这些 descriptors 子集；
PackPolicy 可基于 capability descriptors 分支，但**绝不**基于 raw model
identity 分支。

## Atom registry

atom registry 是 PackPolicy 可包含或排除的 pack-layout atoms 的 FROZEN
集合。每个 atom 是一个可独立开关（受 experimental-structure 约束）的
pack-layout feature。atom registry（FROZEN）：

- `signature` —— candidate 的 symbol/signature metadata
- `matched_lines` —— 显式 matched line ranges（仅行号；无 raw snippet 内容）
- `raw_snippet` —— bounded raw source snippet 文本
- `neighbor_context` —— candidate 周围的 neighbor window 行
- `scores` —— retrieval score / channel weight 值
- `provenance` —— retrieval channel / source provenance metadata
- `hard_distractor` —— hard-distractor proxy slot
- `same_file_competitor` —— same-file competitor slot
- `path_kind_flag` —— 粗粒度 path-kind flag（test / vendor / generated /
  source）

atoms 在 pack 层级被 toggle；PackPolicy 输出是 atom registry 的子集。
atom registry 是 closed：candidate PackPolicy 不得引入此 registry 之外的
atoms，除非经过单独 preregistration round。

## Forbidden labels / forbidden features

B15 **不得**使用 benchmark-private labels 或 score-private fields 作为
PackPolicy inputs（features）。per-record outcomes（所选 span 是否正确）
是 validation TARGET，**不是** feature；它们作为 evaluation targets 是必需
的，但**绝不**进入 PackPolicy。

Forbidden PackPolicy features（FROZEN）：

- `task_bucket`、`task_risk_tags`（benchmark-private labels）
- `has_gold`、`score_group`、`outcome_metrics`（score-private fields）
- `gold_spans`、`must_not_primary`、`expected_behavior`、`oracle_type`、
  `risk_tags`（label / oracle fields）
- raw model names（`kimi`、`qwen`、`deepseek`、`glm`）—— PackPolicy 仅使用
  abstract `model_profile` slots

**`algorithm_spec` 中无 model names**：B15 必须使用 abstract
`model_profile` slots（`profile_slot_a`/`profile_slot_b`/`profile_slot_c`/
`profile_slot_d`）与 capability descriptors，而非 raw model names。B15
evaluator 通过特殊 invariant `algorithm_spec_has_no_model_names=true`
强制此约束。

## Required per-record inputs

真实的 B15 PackPolicy validation 需要以下**全部** per-record 字段。任何
缺失，real B15 即无法运行，skeleton 发出 `insufficient_data` /
`not_implemented`。

- `per_record_pack_atom_flags`（pack 中包含哪些 atoms）
- `per_record_outcome_binary`（所选 span / candidate 是否正确；validation
  TARGET）
- `role_specific_paired_outputs`（同一 record 在不同 role 下被回答）
- `runtime_state_per_record`（candidate pool 形状、score distribution、
  schema-repair 状态）
- `model_profile_paired_blocks`（同一 record 在不同 abstract capability
  profiles 下被回答）
- `group_membership_for_worst_group_split`（model_family × repo × role，用于
  stratified split 与 worst-group reporting）
- `randomized_atom_assignment`（per-record 的 randomized atom on/off
  assignment，用于 causal atom-effect estimation）
- `randomization_balance_stats`（per atom arm 的 covariate balance）
- `denominator_by_atom_role_model`（atom × role × model_profile cell 的
  denominator counts，防止小-denominator atom-effect 主张）
- `token_budget_matched_controls`（token-budget-matched control packs，避免
  atom effect 与 pack size 混淆）

## Experimental structure (FROZEN)

真实的 B15 按四个 frozen stages 推进。任何 stage 不得跳过，任何 stage 的输出
不得反馈到更早的 stage：

1. **no_llm_feasibility** —— 验证上述 per-record inputs 存在、atom registry
   closed、role 集合 closed、runtime_state 契约 label-free、model_profile 抽象
   无 raw model names、denominator-by-atom/role/model cells 非空。无 LLM 调用。
   仅发出 feasibility verdict。
2. **fractional_factorial_live_atom_screen** —— 在 atom registry 上的
   fractional factorial design（非完整 2^9 factorial；frozen resolution-IV
   fraction），在 ephemeral per-record inputs 上以 randomized atom assignment
   运行。**仅**以 per-record (atom_flag, outcome) pairs 与 balance stats
   估计 atom-level effects。此 stage **不**学习 PackPolicy；仅 screen atom
   effects。
3. **freeze_candidate_policy** —— 从 atom screen + preregistered rules 冻结
   一个 candidate PackPolicy。冻结是 one-shot：此点之后不得 retuning。
   `pack_policy_learned=false` 仍然 surface，因为 candidate 是 frozen
   research candidate，而非 promoted policy。
4. **fresh_validation** —— frozen candidate PackPolicy 在一个 fresh
   per-record split（与 atom screen 无重叠）上验证。validation 按 role、
   runtime_state、model_profile 报告 outcomes 与 predeclared criteria 对比。
   `success` / `partial` / `failure` 保留给此 stage，skeleton **不**发出。

## Metric registry (FROZEN)

这些是 B15 在 real per-record inputs 可用时将计算的 metric NAMES。skeleton
定义它们并验证 hard gates，但**不**从 aggregate means 计算伪造 metric
values。

- `atom_effect_per_atom`（per-atom causal effect on outcome，来自 randomized
  atom assignment）
- `role_pack_outcome`（per-role PackPolicy outcome）
- `runtime_state_pack_outcome`（per-runtime_state PackPolicy outcome）
- `model_profile_pack_outcome`（per-model_profile PackPolicy outcome）
- `worst_group_pack_outcome`（`{model_family, repo, role, language}` groups
  上的 worst-group PackPolicy outcome）
- `cvar_20_pack_outcome`（pack outcome 的 CVaR_20% tail average）
- `token_budget_parity`（token-budget-matched control parity）
- `denominator_per_atom_role_model`（per-cell denominator counts）
- `randomization_balance_per_arm`（per atom arm 的 covariate balance）

每个 metric 都需要 per-record (atom_flag, outcome, role, runtime_state,
model_profile) tuples；**没有任何** metric 可从 aggregate means 计算。

## Hard gates (FROZEN)

下列 hard gates 在任何 B15 empirical runs 之前 FROZEN。任何 gate 失败的
candidate PackPolicy 即被拒绝，无论其 aggregate outcome 如何。

- **privacy_gate**：`aggregate_only_public_artifact=true`；公共 artifact 中
  无 raw records、task IDs、candidate IDs、paths、spans、snippets、prompts、
  responses、gold spans、private labels、provider keys、base URLs、API
  keys/secrets/tokens、content SHAs、digests 或 line ranges；skeleton 中
  `new_provider_calls=0`。
- **leakage_gate**：无 benchmark-private label、无 score-private field、无
  raw model name 进入 PackPolicy（强制 `forbidden_signal_features`）；
  `algorithm_spec_has_no_model_names=true`。
- **adapter_health_gate**：`algorithm_spec` 中无 `model_adapter`、
  `output_mode`、provider credentials、provider endpoints、provider secrets
  或 raw model names（强制 `excluded_adapter_layer`）。
- **randomization_balance_gate**：per-arm covariate balance 必须在 frozen
  threshold 内；randomized atom assignment 必须覆盖每个 (atom, role,
  model_profile) cell。skeleton 不评估此 gate（无 real per-record inputs），
  仅定义它。
- **denominator_gate**：每个 (atom, role, model_profile) cell 必须有
  denominator ≥ frozen minimum；不得 promote 任何小-denominator atom-effect
  主张。skeleton 不评估此 gate，仅定义它。
- **token_budget_gate**：atom effects 必须对 token-budget-matched controls
  报告；任何 atom 不得仅因增大 pack 而被主张有效。skeleton 不评估此 gate，
  仅定义它。
- **promotion_false_gate**：始终存在 `promotion_ready=false`、
  `default_should_change=false`、`evidencecore_semantics_changed=false`、
  `pack_policy_learned=false`、`atom_ablation_performed=false`、
  `policy_search_performed=false`、`quality_strategy_tuned=false`，使 skeleton
  / stub / no-go 报告无法被误读为 promoted PackPolicy。

## Split protocol (FROZEN)

真实的 B15 将 per-record inputs 划分为一个 **atom-screen split** 与一个
**fresh-validation split**，按 (model_family, repo, role) stratified。split
protocol 为 `stratified_by_model_family_repo_role`，其中
`atom_screen_fraction=0.50`、`fresh_validation_fraction=0.50`。
fresh-validation split 为 held out 且 reported once
（`fresh_validation_split_reported_once=true`）。fresh-validation split 上
的任何 metric 不得反馈到 atom screen 或 candidate-policy freeze。

## Worst-group reporting

B15 在 `{model_family, repo, role, language}` groups 上报告 worst-group
metrics，并附 `CVaR_20%` tail average（最差 20% groups 的均值）。CVaR tail
fraction 为 `cvar_alpha=0.20`（frozen）。

## Privacy / publication gates

公共 artifacts 必须为 aggregate-only。B15 evaluator 强制：

- 公共 artifact 中**无** raw records、task IDs、repo IDs、candidate IDs、
  paths、spans、snippets、prompts、responses、gold spans、private labels、
  provider keys、base URLs、API keys/secrets/tokens、content SHAs、digests
  或 line ranges；
- **无** raw filesystem path strings、64-char hex digests、http(s) URLs 或
  credential assignments 作为 values；
- `algorithm_spec` 中**无** raw model names（仅 `model_profile` slots）；
- `aggregate_only_public_artifact=true`；
- `new_provider_calls=0`（skeleton；无 live LLM 调用）；
- `forbidden_public_key_scan_clean=true`。

## Predeclared success / partial / failure criteria

下列 criteria 在任何 B15 empirical runs 之前 FROZEN
（`PREDECLARED_CRITERIA`）：

| Outcome | Criterion |
| --- | --- |
| **Success** | frozen candidate PackPolicy 在 fresh-validation split 上对**每个** role 的 per-role pack outcome 相对 reference（best single pack layout）提升 ≥ `0.02`，worst-group pack outcome 不劣于 per-role mean `0.15`，且 screen 中估计的每个 atom effect 都在 frozen denominator 与 randomization-balance gates 内，且对每个被主张有效的 atom 都成立 token-budget parity。 |
| **Partial** | 部分 roles 提升但非全部；或 worst-group pack outcome 在某一 role 上 regress；或一个 atom effect 在 denominator/balance gates 内但另一个不在。 |
| **Failure** | fresh-validation split 上无 role 提升，或任何 atom effect 在 denominator / randomization-balance / token-budget gates 外估计，或 privacy / leakage / adapter-health gates 失败。 |

Frozen numeric gates：

- `strictly_greater_threshold = 0.02`
- `approx_equal_threshold = 0.02`
- `worst_group_pack_outcome_regression_threshold = 0.15`
- `cvar_alpha = 0.20`
- `atom_screen_fraction = 0.50`
- `fresh_validation_fraction = 0.50`
- `min_denominator_per_atom_role_model_cell = 30`
- `randomization_balance_max_imbalance = 0.05`
- `token_budget_match_tolerance = 0.10`

B15 verdict 框架发出下列之一：

- `success`（所有 roles 提升，fresh-validation split 上所有 gates 通过）
- `failure`（无提升，或任何 hard gate 失败）
- `partial`（部分 roles 提升，非全部；或一个 gate 边界）
- `insufficient_data`（synthetic fixture，或记录过少）
- `not_implemented`（`--input` stub，real PackPolicy validation 推迟）

skeleton 仅发出 `insufficient_data`（synthetic fixture）或
`not_implemented`（ci_ephemeral_records stub）；`success` / `failure` /
`partial` 在当前 skeleton 中**不**被发出。任何未来真实 B15 empirical
路径若可能发出它们，都需要其自身的单独 preregistration，其精确 flag
schema（包括任何 `pack_policy_learned` / `atom_ablation_performed` 设置）
是 future work，**不**存在于当前 skeleton 中。本 commit 严格保持
`pack_policy_learned=false` 与 `atom_ablation_performed=false`。

## B2 prior usage boundary

已发布的 B2 contrastive-pack experiment
（`docs/en/b2-contrastive-pack-quality-experiment.md`）是一个 **single-model、
low-N（每个 layout 24 tasks）、aggregate-only** 的 pack-layout 比较，覆盖
四个 repos。B2 的主要结论 —— contrastive structure **并非自动更好**，
最佳 pack 取决于哪种 error 更重要 —— **仅**可作为
`low_n_single_model_aggregate_directional_prior` 使用：一个弱 directional
提示，表明 PackPolicy 应按 role 与 runtime_state 条件化，而非采用单一全局
pack layout。

B2 **不是**：

- atom-level causality（B2 报告的是 pack-layout aggregates，而非 per-atom
  effects）
- role-specific PackPolicy 证明（B2 未改变 role）
- calibrated policy（B2 未 calibrate 任何东西）
- cross-model robustness（B2 使用一个 model profile）
- hard-distractor 通用规则（B2 的 hard-distractor 结果是 single-model、
  low-N）
- scores/provenance 通用胜利（B2 的 scores/provenance 结果混合且更高延迟）
- default change 或 promotion（B2 明确不 promote）
- EvidenceCore change（B2 明确不改变 EvidenceCore）

B15 public-aggregate prior screen **仅**将 B2 以 `b2_prior_usable=true` +
`b2_prior_claim_level=low_n_single_model_aggregate_directional_prior` carry
forward。真实 B15 PackPolicy validation 需要上述 per-record inputs；B2 单独
不足。

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
stage_is_context_pack_policy=true (B15 stage IS context pack policy)
pack_policy_learned=false (skeleton 不进行 PackPolicy learning)
atom_ablation_performed=false (skeleton 不进行 empirical atom ablation)
per_record_inputs_available=false (skeleton；无 real per-record inputs)
policy_search_performed=false
quality_strategy_tuned=false
new_provider_calls=0 (skeleton；无 live LLM 调用)
no_fake_atom_effects_from_aggregate_means=true
aggregate_only_public_artifact=true
algorithm_spec_has_no_model_names=true (B15 special invariant)
```

## What B15 does NOT prove

- B15 **不**学习 PackPolicy。
- B15 **不**进行 empirical atom ablation。
- B15 **不**从 aggregate means 估计 atom-level causal effects。
- B15 **不** promote 任何 PackPolicy。
- B15 **不**改变任何 defaults。
- B15 **不**改变 `EvidenceCore` 语义。
- B15 **不**授权 B16（需单独 user review）。
- B15 结果仅是 research candidates；B15-frozen candidate PackPolicy
  **不是** promoted policy，**不是**新 default，直至通过标准 promotion 流程
  单独 promote。
- B15 的 `--input` 路径是 stub（`verdict="not_implemented"`）；完整
  PackPolicy validation 推迟到后续任务。
- B15 **不**从 aggregate means 计算 atom-effect / role-pack-outcome /
  worst-group-pack-outcome metrics。
- B2 **不是** atom-level causality、role-specific PackPolicy、calibrated
  policy、cross-model robustness、hard-distractor 通用规则、scores/provenance
  通用胜利、default change、promotion 或 EvidenceCore change。

## Self-test (read-only) and explicit artifact regeneration

```bash
python3 eval/b15_context_pack_policy.py --self-test
python3 eval/b15_context_pack_policy.py --regenerate-artifacts
python3 eval/b15_context_pack_policy.py --self-test
python3 eval/b15_public_aggregate_prior_screen.py --self-test
python3 eval/b15_public_aggregate_prior_screen.py \
    --out artifacts/b15_context_pack_policy/b15_public_aggregate_prior_screen_report.json
```

`eval/b15_context_pack_policy.py --self-test` 运行是 **read-only**：它针对
synthetic fixture（仅 definitions；无 per-record (atom_flag, outcome) pairs，
无 computed atom-effect values）验证 PackPolicy 契约、atom registry、role
集合、runtime_state 契约、model_profile 抽象、metric registry、hard gates 与
experimental structure，并将内存中期望的 algorithm spec + report 与 on-disk
artifacts 比对，**drift 即失败**。它**不**修改 checked-in artifacts。它发出
`stage_is_context_pack_policy=true`、`pack_policy_learned=false`、
`atom_ablation_performed=false`、`per_record_inputs_available=false`、
`promotion_ready=false`、`default_should_change=false`、
`evidencecore_semantics_changed=false`、`policy_search_performed=false`、
`quality_strategy_tuned=false`、`new_provider_calls=0`、
`no_fake_atom_effects_from_aggregate_means=true`，使 synthetic-fixture 报告
明确无误地**不是** empirical B15 PackPolicy 结果。

read-only self-test 运行以下检查：

1. `forbidden_scan` —— forbidden public keys/values 扫描（含 algorithm spec
   上的 raw model-name 扫描）
2. `spec_hash_stable` —— algorithm spec sha256 稳定性
3. `atom_registry_closed` —— atom registry closed 且与 forbidden features
   不相交
4. `role_set_closed` —— 4 个 roles，closed 集合
5. `runtime_state_contract` —— runtime_state features label-free 且
   model-name-free
6. `model_profile_abstraction` —— 仅 abstract capability slots，spec 中无
   raw model names
7. `metric_registry` —— 9 个 metric names；无 aggregate-mean metrics
8. `hard_gates_defined` —— privacy / leakage / adapter-health /
   randomization-balance / denominator / token-budget / promotion-false gates
   已定义
9. `experimental_structure_frozen` —— 4 个 frozen stages；无反馈
10. `no_fake_atom_effects_from_aggregate_means` —— synthetic fixture 无
    per-record pairs 且无 atom-effect values
11. `input_stub_not_implemented` —— `--input` stub 返回 `not_implemented`
12. `reference_specs_pinned` —— B10/B10B/B11/B12/B13/B14 reference specs 在
    disk 上存在
13. `artifacts_match_in_memory` —— read-only drift 检查：内存中期望 spec +
    report 与 on-disk artifacts 匹配

`python3 eval/b15_context_pack_policy.py --regenerate-artifacts` 是**唯一**
会修改 checked-in artifacts 的路径：它（重）写 on-disk algorithm spec +
synthetic-fixture report。修改后，重新运行 `--self-test` 以确认 on-disk
artifacts 与内存中期望对象匹配（无 drift）。

`--input` 路径是 non-canonical stub 路径：它要求显式 `--out` 目标，并拒绝
写入 checked-in `b15_context_pack_policy_report.json`。它可以写入一个临时
stub 报告用于开发，但**不**修改 checked-in B15 artifacts。

`eval/b15_public_aggregate_prior_screen.py --self-test` 运行针对一个
synthetic minimal B2 + B14 + optional B4-B9 / P21-G / P49 fixture 验证
bounded public-aggregate prior / no-go screen。它发出
`verdict=no_go_public_aggregate_only` 或 `prior_screen_only`，并带
`pack_policy_learned=false`、`atom_ablation_performed=false`、
`per_record_inputs_available=false`、
`atom_level_inference_possible=false`、
`role_specific_policy_possible=false`、`calibration_possible=false`、
`new_live_runs_required=true`、`b2_prior_usable=true`、
`b2_prior_claim_level=low_n_single_model_aggregate_directional_prior`。

## Artifacts

- `artifacts/b15_context_pack_policy/b15_context_pack_policy.algorithm.json`
  （frozen spec；deterministic，stable sha256；仅通过
  `--regenerate-artifacts` 重新生成）
- `artifacts/b15_context_pack_policy/b15_context_pack_policy_report.json`
  （synthetic-fixture self-test 报告，verdict `insufficient_data`；
  `pack_policy_learned=false`、`atom_ablation_performed=false`、
  `per_record_inputs_available=false`、
  `stage_is_context_pack_policy=true`、
  `no_fake_atom_effects_from_aggregate_means=true`；无 empirical per-atom
  metric values）
- `artifacts/b15_context_pack_policy/b15_public_aggregate_prior_screen_report.json`
  （bounded public-aggregate prior / no-go screen 报告；
  `verdict=no_go_public_aggregate_only` 或 `prior_screen_only`；
  `b2_prior_usable=true`、
  `b2_prior_claim_level=low_n_single_model_aggregate_directional_prior`、
  `atom_level_inference_possible=false`、
  `role_specific_policy_possible=false`、
  `calibration_possible=false`、`new_live_runs_required=true`）

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B15 plan 文档（本文件）
- B15 evaluator skeleton（`eval/b15_context_pack_policy.py`）+ read-only
  `--self-test`（将内存中期望 artifacts 与 on-disk artifacts 比对，drift 即
  失败）+ 显式 `--regenerate-artifacts` 修改路径
- B15 frozen algorithm spec + synthetic-fixture report artifacts
- B15 bounded public-aggregate prior / no-go screen
  （`eval/b15_public_aggregate_prior_screen.py`）+ self-test +
  `artifacts/b15_context_pack_policy/b15_public_aggregate_prior_screen_report.json`
  （读取已发布的 B2 + B14 artifacts，以及当存在时的 B4-B9 / P21-G / P49
  公共 aggregates；发出 `no_go_public_aggregate_only` /
  `prior_screen_only`；从不声称 empirical PackPolicy learning，从不计算
  atom-effect metric，从不声明 winner）

### Needs per-record ephemeral inputs

- B15 real PackPolicy validation 需要 per-record pack atom flags、per-record
  outcomes、role-specific paired outputs、runtime_state per record、
  model_profile paired blocks、group membership、randomized atom assignment、
  randomization balance stats、denominator-by-atom/role/model cells 与
  token-budget-matched controls，来自 B11/B13 live runs。若这些 records 尚未
  产生，B15 发出 `insufficient_data` / `not_implemented`。

### Needs user review

- 结果解释
- 决定是否进入 B16（downstream agent evaluation），使用 B15-frozen
  candidate PackPolicy 作为 research candidate
- 决定是否从 minimum viable atom registry 扩展到更大 atom set（需单独
  preregistration）

## Next steps after B15

- **B15 success**：frozen candidate PackPolicy 在 fresh-validation split 上
  改善 per-role pack outcome，所有 hard gates 通过。进入 B16，将其作为
  context-pack routing candidate 下游测试。
- **B15 failure**：无 candidate PackPolicy 满足 predeclared criteria。默认
  pack layout（`topk_plain_v0`）继续；B16 应使用现有 pack layout。
- **B15 partial**：部分 roles 提升，非全部。调研 role-conditional
  PackPolicy；可能在单独 B15B round 扩展 atom registry（需单独
  preregistration）。
