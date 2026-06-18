# B13 Distributionally Robust Policy Search

Date: 2026-06-18

B13 是继 B12（mechanism decomposition）之后的 **distributionally robust policy
search** 阶段。目标是找到一个含 6-10 条 rules 的 policy，仅使用
runtime-observable features，优化 **worst-group utility**（而非平均值），并通过
rotating leave-one-model-family-out 进行验证。

> **重要 claim 边界。** B13 **是** policy-search *stage*
> （`stage_is_policy_search=true`），但当前 skeleton **不**执行任何 empirical
> policy search（`empirical_policy_search_performed=false`）。synthetic-fixture /
> `--input` stub 报告设置 `policy_search_performed=false`，使该公共 artifact
> 不会被误读为 empirical B13 run。即使未来 empirical B13 search 运行，其结果也
> **不**被 promoted。`promotion_ready=false`、`default_should_change=false`，
> 且 `EvidenceCore` 语义不变。B13 结果仅是 research candidates：它们指导 B14
> （uncertainty calibration）与 B16（downstream agent evaluation），但 B13 不授权
> 任何 default change、任何 policy promotion、或任何 EvidenceCore 修改。B13 是
> B10-B19 Breakthrough Sprint 中最后一个 "immediate priority" item；其余 items
> （B14-B19）为 second priority 或 parallel tracks。

> **重要 public-aggregate 边界。** 真实的 B13 distributionally robust policy
> search 需要私有 / ephemeral 的 per-record P21 records（含 `route_features` +
> per-strategy outcomes + group membership）以及 rotating
> leave-one-model-family-out 的 train/test 划分。这些在公共 B11 aggregate 与 B12
> public-aggregate screen 中均不存在，因此仅凭公共 aggregates 无法进行真实的
> B13 search。位于 `eval/b13_public_aggregate_feasibility_screen.py` 的 bounded
> public-aggregate feasibility / no-go screen 读取已发布的 B11 与 B12 artifacts，
> 在 `artifacts/b13_dro_policy_search/` 下发出
> `no_go_public_aggregate_only`（或当 B11 aggregate 无记录时
> `insufficient_data_public_aggregate_only`）feasibility 报告。该 screen 从不
> 声称 empirical policy search，从不选择 rule，也从不声明 winner。

## Preregistration declaration

下列 artifacts、rule grammar 约束、optimization objective、search 约束、
validation methodology 与 predeclared success/failure criteria 均在任何 B13
search runs 之前 **FROZEN**。B13 search runs 开始后，不允许对 objective、rule
grammar、search budget 或 success criteria 进行 retuning。任何 post-hoc analysis
必须标注为 exploratory，并需要单独的 validation round。

### Frozen artifacts

- `balanced_policy_v1_benchmark_routed`（B10 frozen spec；sha256 位于
  `artifacts/b10_runtime_feature_audit/balanced_policy_v1_benchmark_routed.algorithm.json`）
  —— 仅引用，不修改
- `balanced_policy_v1_runtime_shadow_ambiguous_branch`（B10B shadow predicate）
  —— 仅引用，不修改
- B11/B12 frozen criteria —— 仅引用，不修改
- B13 algorithm spec 自身
  （`artifacts/b13_dro_policy_search/b13_dro_policy_search.algorithm.json`）
  —— 在任何 search runs 之前冻结；stable sha256

## Objective

找到一个含 6-10 条 rules 的 policy，仅使用 runtime-observable features，最大化
worst-group utility：

> **最大化** `worst_group = min over {model_family, repo, language, task_bucket}`
> 的 `RobustUtility`，**或** `CVaR_20%`（最差 20% per-group utility 的平均）。

其中：

```text
RobustUtility = SpanF0.5
              - λ * PFP
              - μ * normalized_cost
              - ν * normalized_latency
```

Predeclared parameters（镜像 B11/B12）：

- `λ = 1.0`（PFP weight；`ROBUST_UTILITY_LAMBDA`）
- `μ = 0.1`（normalized cost weight；`ROBUST_UTILITY_MU`）
- `ν = 0.1`（normalized latency weight；`ROBUST_UTILITY_NU`）
- `CVaR α = 0.20`（最差 20% 尾部平均；`CVAR_ALPHA`）

## Rule grammar constraints

### Maximum rules

- 最少 rules：6
- 最多 rules：10（`MAX_RULES = 10`）
- 最多 search iterations：1000（`MAX_SEARCH_ITERATIONS = 1000`）

### Allowed runtime features

每条 rule 仅使用来自 `route_features` 的 runtime-observable features
（`ALLOWED_RUNTIME_FEATURES`）：

- `query_noise`
- `candidate_support_exists`
- `local_anchor`
- `rrf_backed_by_anchor`
- `candidate_count`
- `symbol_regex_agree_file`
- `symbol_regex_agree_span`
- `rrf_anchor_agree_file`
- `rrf_anchor_agree_span`
- `dense_support_present`

### Forbidden features

- **禁止 benchmark-private labels**：`task_bucket`、`task_risk_tags` 是 B10
  benchmark-routed spec 的 benchmark-private 依赖；B13 不得读取。
- **禁止 score-private fields**：`has_gold`、`score_group`、`outcome_metrics`
  仅在 score phase 使用，任何 routing rule 都不得读取。
- **`algorithm_spec` 中禁止 model names**：B13 必须使用 `model_profile`
  capabilities（如 `adapter.supports_reliable_span_narrow`、
  `adapter.cost_class`、`adapter.latency_class`），不得使用 "Kimi"、"Qwen"、
  "DeepSeek"、"GLM" 等原始 model 名称。B13 evaluator 通过 special invariant
  `algorithm_spec_has_no_model_names=true` 强制执行。

### Allowed model_profile capabilities（仅引用，不搜索）

Rules 可读取 `model_profile` capability fields：

- `supports_reliable_span_narrow`（boolean）
- `cost_class`（enum：low / medium / high）
- `latency_class`（enum：low / medium / high）

这些 capabilities **不是** model names；它们是抽象的 adapter-level capability
描述符。

### Rule grammar

Rules 是对 allowed features 的简单 predicates，例如：

- `query_noise > 0`
- `candidate_support_exists AND NOT rrf_backed_by_anchor`
- `local_anchor AND symbol_regex_agree_span`

### Allowed actions

每条 rule 映射到一个 action（`ALLOWED_ACTIONS`）：

- `weak_only`
- `use_p25_action`
- `use_local_baseline`

**禁止 LLM actions**：B13 是 replay/search-only evaluator；它不发出任何 live LLM
call action。Action space 在构造上即为 LLM-free。

### Search method

- Bounded grid + greedy refinement（无 learned classifier，无 neural policy）。
- Pure Python：不使用 numpy / sklearn / scipy。
- 最多 rules：10。
- 最多 search iterations：1000。

## Validation methodology

### Rotating leave-one-model-family-out

候选 policy 必须通过 **全部 3 个 rotations** 才被视为
"distributionally robust"：

| Rotation | Train on | Test on |
| --- | --- | --- |
| `loo_kimi` | Qwen + DeepSeek（Flash + Pro） | Kimi |
| `loo_qwen` | Kimi + DeepSeek（Flash + Pro） | Qwen |
| `loo_deepseek` | Kimi + Qwen | DeepSeek（Flash + Pro） |

Held-out model family 仅用于 evaluation；train families 的任何 rule、threshold、
action 都不得窥视 test family。在任一 rotation 上 regression 超出 predeclared
threshold 的 policy **不是** distributionally robust。

## Predeclared success/failure criteria

下列 criteria 在任何 B13 search runs 之前 FROZEN（`PREDECLARED_CRITERIA`）：

| Outcome | Criterion |
| --- | --- |
| **Success** | 找到一个 policy，其 worst-group utility ≥ B10 balanced policy 的 worst-group utility，且全部 3 个 rotations 通过（无超出 thresholds 的 regression）。 |
| **Failure** | 未找到任何能改进 worst-group utility 超过 B10 的 policy。 |
| **Partial** | Policy 改进了部分 groups 但不是全部（如 3 个 rotations 中改进 2 个、第 3 个 regression）。 |

Rotation regression thresholds（镜像 B11/B12 的 `≈` 与 `>` thresholds）：

- `worst_group_delta_threshold = 0.02`（若 policy 的 worst-group
  `RobustUtility` 在 B10 的 ±0.02 以内，或严格更优，则该 rotation 通过）
- `strictly_greater_threshold = 0.02`（严格改进 margin）
- `cvar_alpha = 0.20`（CVaR 尾部分数）

B13 verdict 框架发出下列之一：

- `success`（找到 policy + 全部 3 个 rotations 通过 + worst-group utility ≥ B10）
- `failure`（未找到改进 worst-group utility 超过 B10 的 policy）
- `partial`（部分 groups 改进，不是全部）
- `insufficient_data`（synthetic fixture，或记录不足以 search）
- `not_implemented`（`--input` stub，真实 search 延后）

## Data requirement

B13 需要 B11 live runs 的 P21 records（4 model families × 8 repos）。每条 P21
record 已含 per-strategy outcomes，故每条候选 rule 的 per-record outcome 可
通过从现有 records 选取对应 per-strategy outcome 计算（replay）。Search 本身不需要
新的 live LLM calls。

若 P21 records 不可用，B13 无法进行真实 search；evaluator 发出
`insufficient_data`（synthetic fixture self-test）或 `not_implemented`
（`--input` stub）。

## CI workflow design

### New stage: `b13_dro_policy_search`

向 `.github/workflows/real-provider-benchmark.yml` 添加新 stage
`b13_dro_policy_search`。该 stage 对 B11 live runs 产生的 P21 ephemeral records
运行 B13 search aggregator（replay）。Search 本身为 replay-only，不发出 live LLM
calls。

### Workflow inputs

- `stage`：`b13_dro_policy_search`
- `replay_source`：`ci_ephemeral_records`（仅 replay）
- `enable_remote_models`：不需要（search 为 replay-only）

### Run matrix

- Replay：1 个 run（消费 4 model families × 8 repos 的 B11 P21 records）。

## B10B/B11/B12 integration

- B13 search 消费 B11 P21 records（`replay_source="ci_ephemeral_records"`）。
- B13 引用（不修改）B10 frozen spec、B10B shadow predicate、B11/B12 frozen
  criteria。
- B13 结果输入 B14（uncertainty calibration）与 B16（downstream agent
  evaluation）。一个通过全部 3 个 rotations 的 B13-found policy 是 B14/B16 的
  research candidate；它**不**被 promoted。

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
stage_is_policy_search=true（B13 stage 即 policy search）
empirical_policy_search_performed=false（skeleton 不执行 empirical search）
policy_search_performed=false（synthetic/stub 报告；用 stage_is_policy_search=true
                              标注 stage）
quality_strategy_tuned=false
runtime_calls_by_replay=0（replay 不产生新 live calls）
model_calls_by_replay=0（replay 不产生新 LLM calls）
aggregate_only_public_artifact=true
algorithm_spec_has_no_model_names=true（B13 special invariant）
```

synthetic / stub 报告中的 `policy_search_performed=false` 是有意为之：它防止
该公共 artifact 被误读为 empirical B13 search。`stage_is_policy_search=true`
承担 stage 定义（B13 *是* policy-search stage）；
`empirical_policy_search_performed=false` 明确表示 skeleton 未执行 empirical
search。

## What B13 does NOT prove

- B13 **不** promote 任何 policy。
- B13 **不** 改变任何 defaults。
- B13 **不** 改变 `EvidenceCore` 语义。
- B13 **不** 授权 B14/B16，除非经过单独的用户 review。
- B13 结果仅是 research candidates；一个 B13-found policy **不是** 新 default，
  除非通过标准 promotion 流程单独 promoted。
- B13 的 `--input` 路径为 stub（`verdict="not_implemented"`）；完整 search
  计算延后到后续任务。

## Self-test（只读）与显式 artifact 重新生成

```bash
python3 eval/b13_dro_policy_search.py --self-test
python3 eval/b13_dro_policy_search.py --regenerate-artifacts
python3 eval/b13_public_aggregate_feasibility_screen.py --self-test
```

`eval/b13_dro_policy_search.py --self-test` 运行为**只读**：在不进行 live
runs 的情况下验证 report aggregator mechanics（仅 synthetic fixture；
`replay_source="synthetic_fixture"`；verdict `insufficient_data`），并将内存中
期望的 algorithm spec + report 与 on-disk artifacts 比对，**drift 即失败**。
它**不**向磁盘写入任何内容。它发出 `stage_is_policy_search=true`、
`empirical_policy_search_performed=false`、
`policy_search_performed=false`，以及顶层 `policy_found=false`、
`rotations_evaluated=false`、`rotations_defined=true`、`rotation_count=3`、
`winner_declared=false`，使 synthetic-fixture 报告明确**不是** empirical B13
search。synthetic / stub 报告仅发出 rotation *定义*
（`rotations_defined=true`、`rotation_count=3`、`rotations_evaluated=false`）；
它们**从不**发出 per-rotation 的 `passes=true`、`all_rotations_pass=true`、
`test_worst_group_utility` 或 `delta_vs_b10_reference` 仿佛是 empirical 的。
skeleton verdict 框架仅发出 `insufficient_data`（synthetic fixture）或
`not_implemented`（ci_ephemeral_records stub）；`success` / `failure` /
`partial` 保留给未来 `policy_search_performed=true` 的 empirical 路径，该路径
在当前 skeleton 中**不**存在。

只读 self-test 运行 9 个 checks：

1. `forbidden_scan` —— forbidden public keys/values 扫描（含 algorithm spec 上的
   原始 model-name 扫描）
2. `spec_hash_stable` —— algorithm spec sha256 稳定性
3. `synthetic_fixture_metrics` —— synthetic fixture metrics
4. `rule_grammar_valid` —— rule grammar（仅允许 features + actions）
5. `search_mechanics_stub` —— bounded-grid + greedy-refinement mechanics stub
6. `leave_one_out_rotations_defined` —— 3 个 leave-one-model-family-out
   rotations（仅定义；无 empirical per-rotation passes / utilities / deltas）
7. `input_stub_not_implemented` —— `--input` stub 返回 `not_implemented`
8. `reference_specs_pinned` —— B10/B10B/B11/B12 reference specs 在磁盘上存在
9. `artifacts_match_in_memory` —— 只读 drift 检查：内存中期望 spec + report
   匹配 on-disk artifacts

`python3 eval/b13_dro_policy_search.py --regenerate-artifacts` 是唯一的
mutating 路径：它从当前 build functions（重新）写入 on-disk algorithm spec +
synthetic-fixture report。mutating 后，重新运行 `--self-test` 以确认 on-disk
artifacts 现已匹配内存中期望对象（无 drift）。

`eval/b13_public_aggregate_feasibility_screen.py --self-test` 针对一个合成的
最小 B11 + B12 fixture 验证 bounded public-aggregate feasibility / no-go
screen。它发出 `verdict=no_go_public_aggregate_only`（或当 B11 aggregate 无记录
时为 `insufficient_data_public_aggregate_only`），并设置
`policy_search_performed=false`、`empirical_policy_search_performed=false`、
`policy_found=false`、`rotations_evaluated=false`。运行 4 个 checks：
`happy_path`、`input_validation_blocks`、`insufficient_data_branch`、
`forbidden_scan`。

## Artifacts

- `artifacts/b13_dro_policy_search/b13_dro_policy_search.algorithm.json`
  （frozen spec；deterministic，stable sha256；仅通过
  `--regenerate-artifacts` 重新生成）
- `artifacts/b13_dro_policy_search/b13_dro_policy_search_report.json`
  （synthetic-fixture self-test 报告，verdict `insufficient_data`；
  `policy_search_performed=false`、
  `empirical_policy_search_performed=false`、
  `stage_is_policy_search=true`、`policy_found=false`、
  `rotations_evaluated=false`、`rotations_defined=true`、
  `rotation_count=3`、`winner_declared=false`；无 empirical per-rotation
  passes / utilities / deltas）
- `artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json`
  （bounded public-aggregate feasibility / no-go screen 报告；
  `verdict=no_go_public_aggregate_only` 或
  `insufficient_data_public_aggregate_only`；`policy_found=false`、
  `rotations_evaluated=false`、
  `full_b13_possible_from_public_artifacts=false`）

## What's autonomous vs. needs user action

### Autonomous（现在可做）

- B13 plan 文档（本文件）
- B13 CI workflow 定义（新 stage `b13_dro_policy_search`）
- B13 report aggregator skeleton（`eval/b13_dro_policy_search.py`）+
  只读 `--self-test`（将内存中期望 artifacts 与 on-disk artifacts 比对，drift
  即失败）与显式 `--regenerate-artifacts` mutating 路径（发出
  `stage_is_policy_search=true`、
  `empirical_policy_search_performed=false`、
  `policy_search_performed=false`、`policy_found=false`、
  `rotations_evaluated=false`、`rotations_defined=true`、`rotation_count=3`、
  `winner_declared=false`；无 empirical per-rotation passes / utilities /
  deltas）
- B13 frozen algorithm spec + synthetic-fixture report artifacts
- B13 bounded public-aggregate feasibility / no-go screen
  （`eval/b13_public_aggregate_feasibility_screen.py`）+ self-test +
  `artifacts/b13_dro_policy_search/b13_public_aggregate_feasibility_report.json`
  （读取已发布的 B11 aggregate + B12 public screen；发出
  `no_go_public_aggregate_only` / `insufficient_data_public_aggregate_only`；
  从不声称 empirical policy search、从不选择 rule、从不声明 winner）

### Needs P21 records

- B13 真实 search 需要 B11 live runs 的 P21 records（4 model families × 8
  repos）。若这些 records 尚未生成，B13 发出 `insufficient_data` /
  `not_implemented`。

### Needs user review

- 结果解读
- 决定是否以 B13-found policy 作为 research candidate 推进到 B14（uncertainty
  calibration）或 B16（downstream agent evaluation）
- 决定是否从 minimum viable 扩展为 full B13（更多 rules、更多 features、更多
  rotations）

## Next steps after B13

- **B13 success**：识别出一个 distributionally robust policy candidate
  （worst-group utility ≥ B10，全部 3 个 rotations 通过）。推进到 B14 在该
  candidate 上 calibrate uncertainty，并在 B16 中 downstream 测试。
- **B13 failure**：没有 policy 能改进 worst-group utility 超过 B10。B10 仍是
  frozen balanced policy；B14/B16 应以 B10 作为 reference policy。
- **B13 partial**：部分 groups 改进，不是全部。研究 group-conditional rules；
  可能放宽 worst-group objective 或在单独的 B13B round 中扩展 rule grammar
  （需单独 preregistration）。
