# B14 Uncertainty Calibration

Date: 2026-06-18

B14 是继 B13（distributionally robust policy search）之后的 **uncertainty
calibration** 阶段。目标是针对 balanced-policy candidate 进行 **model-
independent uncertainty calibration**：从 local candidate signals、model
output structure 与 cross-model disagreement 构建每条记录的 uncertainty
score（绝不针对特定 model name 进行校准），再用 **risk-coverage**、
**selective risk**、**ECE** 与 **PFP-at-fixed-coverage** 指标评估该 score，
并附 worst-group 报告与 rotating leave-one-model-family-out 验证。

> **重要 claim 边界。** B14 **是** uncertainty-calibration *stage*
> （`stage_is_uncertainty_calibration=true`），但当前 skeleton **不**执行任何
> empirical uncertainty calibration
> （`uncertainty_calibration_performed=false`）。synthetic-fixture / `--input`
> stub 报告设置 `calibrated_model_claim=false` 与
> `per_record_inputs_available=false`，使该公共 artifact 不会被误读为
> empirical B14 calibration。即使未来 empirical B14 run 找到一个 well-
> calibrated 的 uncertainty score，其结果也**不**被 promoted。
> `promotion_ready=false`、`default_should_change=false`，且 `EvidenceCore`
> 语义不变。B14 结果仅是 research candidates：它们指导 B16（downstream
> agent evaluation）与任何未来的 selective-abstention policy，但 B14 不授权
> 任何 default change、任何 policy promotion、任何 calibrated-model claim
> 或任何 EvidenceCore 修改。B14 是 B10-B19 Breakthrough Sprint 中的
> second-priority / parallel-track item。

> **重要 public-aggregate 边界。** 真实的 B14 uncertainty calibration 需要
> 私有 / ephemeral 的 per-record inputs：per-record uncertainty scores（或
> 计算 score 所需的原始 signals）、per-record binary outcomes（所选 span 是否
> 正确）、paired cross-model outputs（用于 cross-model disagreement）、
> schema-repair per-call rows（用于 model output structure）以及 candidate
> score distributions / entropy（用于 local candidate signals）。这些在公共
> B11 aggregate、B12 public-aggregate screen 与 B13 public-aggregate
> feasibility report 中均不存在，因此仅凭公共 aggregates 无法进行真实的
> B14 calibration。位于 `eval/b14_public_aggregate_feasibility_screen.py`
> 的 bounded public-aggregate feasibility / no-go screen 读取已发布的 B11、
> B12 与 B13 artifacts，在 `artifacts/b14_uncertainty_calibration/` 下发出
> `no_go_public_aggregate_only`（或当 B11 aggregate 无记录时
> `insufficient_data_public_aggregate_only`）feasibility 报告。该 screen 从不
> 声称 empirical uncertainty calibration，从不计算 ECE / risk-coverage /
> selective risk / PFP-at-coverage，从不声明 calibrated model，也从不声明
> winner。

> **CRITICAL 反伪造边界。** skeleton **绝不可**从 aggregate means 计算伪造的
> ECE / risk-coverage / selective-risk / PFP-at-coverage 指标。aggregate
> means 不包含 per-record (uncertainty, outcome) pairs，因此从中计算的任何
> calibration metric 都是伪造。synthetic fixture 仅验证 metric NAMES、gate
> thresholds、coverage levels、ECE bin 定义与 split protocol 已正确接线；
> 它**不**把 synthetic metric values 当作 empirical calibration 结果呈现。
> 报告 surface `metrics_evaluated=false` 与
> `no_fake_metrics_from_aggregate_means=true`，使读者无法将 skeleton 误读
> 为 empirical B14 calibration。

## Preregistration declaration

下列 artifacts、signal families、metric registry、coverage levels、ECE bin
定义、split protocol、validation methodology 与 predeclared success/failure
criteria 均在任何 B14 calibration runs 之前 **FROZEN**。B14 calibration runs
开始后，不允许对 signal families、metric registry、coverage levels、ECE bin
count、split fractions 或 success criteria 进行 retuning。任何 post-hoc
analysis 必须标注为 exploratory，并需要单独的 validation round。

### Frozen artifacts

- `balanced_policy_v1_benchmark_routed`（B10 frozen spec）—— 仅引用，不修改
- `balanced_policy_v1_runtime_shadow_ambiguous_branch`（B10B shadow
  predicate）—— 仅引用，不修改
- B11/B12/B13 frozen criteria —— 仅引用，不修改
- B14 algorithm spec 自身
  （`artifacts/b14_uncertainty_calibration/b14_uncertainty_calibration.algorithm.json`）
  —— 在任何 calibration runs 之前冻结；stable sha256

## Objective

从三个允许的 signal families 产生一个 **model-independent** 的 uncertainty
score `u(record) ∈ [0, 1]`，然后在 held-out test split 上用 risk-coverage、
selective risk、ECE 与 PFP-at-fixed-coverage 进行评估，并附 worst-group 报告
与 rotating leave-one-model-family-out 验证。

## Target uncertainties

该 uncertainty score 针对 **所选 span / candidate correctness** 预测：
`u(record)` 应为一个 calibrated probability，表示 balanced policy 在该记录上
所选 span / candidate 是否正确。calibration TARGET 是 per-record binary
outcome（所选 span 是否正确）；它作为 evaluation target 是必需的，但**绝不
可**作为 feature 进入 uncertainty score。

## Allowed signal families

uncertainty score 由三个允许的 signal families 构建。任何 signal 不得引用原始
model name；signals 仅从 local candidate state、model output structure 与
cross-model disagreement 计算。

### Family 1：`local_candidate_signals`

仅从 candidate state 计算；无 labels，无 model names。这些描述路由决策所基于
的 candidate pool 形态。

- `candidate_count`
- `candidate_support_exists`
- `score_distribution_spread`
- `top1_top2_score_gap`
- `entropy_proxy`
- `anchor_disagreement`
- `rrf_backed_by_anchor`
- `dense_support_present`

### Family 2：`model_output_structure`

从 model 的结构化输出计算，**而非** model 身份。这些描述 model 是否产生了
schema-valid、span-narrow-valid、within-candidate 的 response。

- `schema_valid`
- `llm_span_narrow_valid`
- `llm_span_within_candidate`
- `output_mode_stable`
- `schema_repair_invoked`

### Family 3：`cross_model_disagreement`

从两条或多条 model family 在**同一**记录上的 paired outputs 计算。这些需要
跨 model family 的 paired per-record outputs。

- `per_record_action_disagreement`
- `span_overlap_disagreement`
- `rank_disagreement_topk`

## Forbidden labels / forbidden features

B14 **不得**将 benchmark-private labels 或 score-private fields 用作
UNCERTAINTY SIGNALS（features）。per-record outcomes（所选 span 是否正确）
是 calibration TARGET，不是 signal；它作为 evaluation target 是必需的，但
**绝不可**进入 uncertainty score。

Forbidden signal features：

- `task_bucket`、`task_risk_tags`（benchmark-private labels）
- `has_gold`、`score_group`、`outcome_metrics`（score-private fields）
- `gold_spans`、`must_not_primary`、`expected_behavior`、`oracle_type`、
  `risk_tags`（label / oracle fields）

**`algorithm_spec` 中无原始 model names**：B14 必须使用抽象 `family_slots`
（`family_a`/`family_b`/`family_c`/`family_d`）与 signal-family capabilities，
而非 "Kimi"、"Qwen"、"DeepSeek" 或 "GLM" 等原始 model names。B14 evaluator
通过 special invariant `algorithm_spec_has_no_model_names=true` 强制此点。

## Required per-record inputs

真实 B14 calibration 要求以下每条记录均具备。若任一缺失，真实 B14 无法运行，
skeleton 发出 `insufficient_data` / `not_implemented`。

- `per_record_uncertainty_signals`（计算 uncertainty score 所需的原始
  signals）
- `per_record_outcome_binary`（所选 span 是否正确；calibration TARGET）
- `paired_cross_model_outputs`（用于 cross-model disagreement signals）
- `schema_repair_per_call_rows`（用于 model output structure signals）
- `candidate_score_distribution`（用于 local candidate signals —— entropy /
  top1-top2 gap / spread）
- `group_membership_for_worst_group_split`（model_family × repo，用于分层
  split 与 worst-group 报告）

## Split / calibration / test protocol

真实 B14 将 per-record inputs 划分为 **calibration split** 与 **test split**，
按 (model_family, repo) 分层。split protocol 为
`stratified_by_model_family_and_repo`，`calibration_fraction=0.50`、
`test_fraction=0.50`。calibration split 是唯一允许进行 recalibration /
temperature fitting 的 split
（`recalibration_allowed_on_calibration_split_only=true`）；test split 被held
out 并仅报告一次（`test_split_reported_once=true`）。test split 上的任何
metric 不得回馈到 recalibration。

## Coverage levels

报告 `selective_risk` 与 `pfp_at_fixed_coverage` 的固定 coverage levels。这些
已 FROZEN，因此在真实 B14 runs 开始后无法进行 post-hoc coverage threshold
tuning：

- `0.50`
- `0.70`
- `0.90`
- `0.95`
- `0.99`

## ECE target definition

ECE（Expected Calibration Error）在 test split 上使用 **equal-width binning**
在 `[0, 1]` 上划分为 `ece_bin_count=15` 个 bins（`ece_bin_scheme=
equal_width`）进行计算。对每个 bin `B_m`，计算平均 confidence
`conf(B_m)` 与平均 accuracy `acc(B_m)`，则

```text
ECE = Σ_m (|B_m| / N) * |conf(B_m) - acc(B_m)|
```

bin count 已 FROZEN，因此无法进行 post-hoc bin-count tuning。

## Worst-group reporting

B14 在 `{model_family, repo, language, task_bucket}` groups 上报告 worst-group
metrics，并附 `CVaR_20%` tail average（最差 20% group metrics 的平均）。
CVaR tail fraction 为 `cvar_alpha=0.20`（frozen）。

### Rotating leave-one-model-family-out

candidate uncertainty score 若要被视为 robustly calibrated，B14 必须通过**全部
3 个 rotations**，与 B13 一致：

| Rotation | Train on | Test on |
| --- | --- | --- |
| `loo_family_a` | Qwen + DeepSeek (Flash + Pro) | Kimi |
| `loo_family_b` | Kimi + DeepSeek (Flash + Pro) | Qwen |
| `loo_family_c_and_d` | Kimi + Qwen | DeepSeek (Flash + Pro) |

held-out model family 仅用于 evaluation；test split 上的 recalibration 不得
窥探 held-out family。

## Privacy / publication gates

公共 artifacts 必须为 aggregate-only。B14 evaluator 强制：

- **不得**在公共 artifact 中出现 raw records、task IDs、repo IDs、candidate
  IDs、paths、spans、snippets、prompts、responses、gold spans、private
  labels、provider keys、base URLs、API keys/secrets/tokens、content SHAs、
  digests 或 line ranges；
- **不得**以 value 形式出现 raw filesystem path 字符串、64-char hex digests、
  http(s) URLs 或 credential assignments；
- **不得**在 `algorithm_spec` 中出现原始 model names（仅 `family_slots`）；
- `aggregate_only_public_artifact=true`；
- `new_provider_calls=0`（replay / calibration only；无 live LLM calls）；
- `forbidden_public_key_scan_clean=true`。

## Predeclared success / partial / failure criteria

下列 criteria 在任何 B14 calibration runs 之前 FROZEN
（`PREDECLARED_CRITERIA`）：

| Outcome | Criterion |
| --- | --- |
| **Success** | test split 上的 ECE ≤ `0.05` 且 coverage=0.90 处的 selective risk ≤ `0.10` 且 coverage=0.90 处的 worst-group selective risk ≤ `0.15` 且全部 3 个 leave-one-out rotations 通过（无超出 `0.02` approx-equality threshold 的 regression）且至少在一个 metric 上相对参考（uncalibrated）score 有 strictly-greater-than-`0.02` 的改进。 |
| **Partial** | 部分 metrics 通过（例如 test split 上 ECE 在 threshold 内），但并非全部通过（例如某个 rotation 上 worst-group selective risk 出现 regression）。 |
| **Failure** | test split 上 ECE > `0.05`，或 worst-group selective risk at coverage=0.90 差于参考（uncalibrated）score，或任一 rotation 超出 `0.02` approx-equality threshold 的 regression。 |

Frozen numeric gates：

- `ece_test_threshold = 0.05`
- `selective_risk_at_coverage_0_90_threshold = 0.10`
- `worst_group_selective_risk_at_coverage_0_90_threshold = 0.15`
- `strictly_greater_threshold = 0.02`
- `approx_equal_threshold = 0.02`
- `cvar_alpha = 0.20`
- `coverage_levels = [0.50, 0.70, 0.90, 0.95, 0.99]`
- `ece_bin_count = 15`（`equal_width`）

B14 verdict 框架发出以下之一：

- `success`（ECE + selective-risk + worst-group + 全部 rotations 通过 + 严格改进）
- `failure`（ECE 超过 threshold，或 worst-group selective risk 更差，或
  rotation regression）
- `partial`（部分 metrics 通过，并非全部）
- `insufficient_data`（synthetic fixture，或记录过少无法 calibrate）
- `not_implemented`（`--input` stub，真实 calibration 延后）

skeleton 仅发出 `insufficient_data`（synthetic fixture）或 `not_implemented`
（ci_ephemeral_records stub）；`success` / `failure` / `partial` 保留给未来
`uncertainty_calibration_performed=true` 的 empirical 路径，该路径在当前
skeleton 中**不**存在。

## Data requirement

B14 需要 B11/B13 live runs 的 per-record inputs（4 model families × 8 repos），
加上 paired cross-model outputs、schema-repair per-call rows 与 candidate
score distributions。若 per-record signals 已由先前 runs 记录，则 calibration
本身无需新的 live LLM calls。

若 per-record inputs 不可用，B14 无法运行真实 calibration；evaluator 发出
`insufficient_data`（synthetic fixture self-test）或 `not_implemented`
（`--input` stub）。

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
stage_is_uncertainty_calibration=true (B14 stage 即为 uncertainty calibration)
uncertainty_calibration_performed=false (skeleton 不执行 empirical calibration)
calibrated_model_claim=false (不声称任何 model 被 calibrated)
per_record_inputs_available=false (skeleton；无真实 per-record inputs)
policy_search_performed=false
quality_strategy_tuned=false
metrics_evaluated=false (skeleton；不从 aggregate means 伪造 metric values)
no_fake_metrics_from_aggregate_means=true
runtime_calls_by_replay=0 (replay 不产生新的 live calls)
model_calls_by_replay=0 (replay 不产生新的 LLM calls)
aggregate_only_public_artifact=true
algorithm_spec_has_no_model_names=true (B14 special invariant)
```

## What B14 does NOT prove

- B14 **不** calibration 任何 model。
- B14 **不** 作出任何 `calibrated_model_claim`。
- B14 **不** promotion 任何 policy 或任何 uncertainty score。
- B14 **不** 改变任何 default。
- B14 **不** 改变 `EvidenceCore` 语义。
- B14 **不** 在未经单独 user review 的情况下授权 B16。
- B14 结果仅是 research candidates；B14-found calibrated uncertainty score
  **不是** calibrated-model claim，也**不是**新 default，直至通过标准
  promotion 流程被单独 promotion。
- B14 的 `--input` 路径为 stub（`verdict="not_implemented"`）；完整
  calibration 计算延后到后续任务。
- B14 **不** 从 aggregate means 计算 ECE / risk-coverage / selective risk /
  PFP-at-coverage。

## Self-test (read-only) and explicit artifact regeneration

```bash
python3 eval/b14_uncertainty_calibration.py --self-test
python3 eval/b14_uncertainty_calibration.py --regenerate-artifacts
python3 eval/b14_public_aggregate_feasibility_screen.py --self-test
python3 eval/b14_public_aggregate_feasibility_screen.py \
    --out artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json
```

`eval/b14_uncertainty_calibration.py --self-test` 运行为**只读**：它针对
synthetic fixture（仅 definitions；无 per-record (uncertainty, outcome) pairs，
无 computed metric values）验证 signal-family grammar、metric-name registry、
coverage levels、ECE bin 定义、split protocol 与 rotation definitions，并将
内存中期望的 algorithm spec + report 与 on-disk artifacts 比对，**drift 即
失败**。它**不**修改 checked-in artifacts。它发出
`stage_is_uncertainty_calibration=true`、
`uncertainty_calibration_performed=false`、`calibrated_model_claim=false`、
`per_record_inputs_available=false`、`metrics_evaluated=false` 与
`no_fake_metrics_from_aggregate_means=true`，以及顶层
`uncertainty_score_found=false`、`rotations_evaluated=false`、
`rotations_defined=true`、`rotation_count=3`、`winner_declared=false`，使
synthetic-fixture 报告明确**不是** empirical B14 calibration。synthetic /
stub 报告仅发出 rotation *定义*（`rotations_defined=true`、
`rotation_count=3`、`rotations_evaluated=false`）；它们从不发出 per-rotation 的
`passes=true`、`test_ece`、`test_selective_risk`、`test_risk_coverage_curve`、
`test_pfp_at_fixed_coverage` 或 `delta_vs_reference`。skeleton verdict 框架仅
发出 `insufficient_data`（synthetic fixture）或 `not_implemented`
（ci_ephemeral_records stub）；`success` / `failure` / `partial` 保留给未来
`uncertainty_calibration_performed=true` 的 empirical 路径，该路径在当前
skeleton 中**不**存在。

只读 self-test 运行 11 个 checks：

1. `forbidden_scan` —— forbidden public keys/values 扫描（含 algorithm spec
   上的 raw model-name 扫描）
2. `spec_hash_stable` —— algorithm spec sha256 稳定性
3. `signal_family_grammar` —— 3 个 signal families 互斥，无 forbidden
   features，outcomes 是 inputs 而非 signals
4. `metric_registry` —— 定义 6 个 metric names；无 aggregate-mean metrics
5. `coverage_levels_and_ece_bins` —— coverage levels + ECE bin 定义
6. `split_protocol` —— 按 model_family 与 repo 分层的 calibration/test split
7. `leave_one_out_rotations_defined` —— 3 个 rotations（仅定义；无 empirical
   per-rotation metric values）
8. `no_fake_metrics_from_aggregate_means` —— synthetic fixture 无 per-record
   pairs 且无 metric values
9. `input_stub_not_implemented` —— `--input` stub 返回 `not_implemented`
10. `reference_specs_pinned` —— B10/B10B/B11/B12/B13 reference specs 在 disk
    上存在
11. `artifacts_match_in_memory` —— 只读 drift check：内存中期望 spec + report
    与 on-disk artifacts 匹配

`python3 eval/b14_uncertainty_calibration.py --regenerate-artifacts` 是**唯一**
会修改 checked-in artifacts 的路径：它从当前 build functions（重新）写入 on-disk algorithm spec +
synthetic-fixture report。mutating 后，重新运行 `--self-test` 以确认 on-disk
artifacts 现在与内存中期望对象匹配（无 drift）。

`--input` 路径是 non-canonical stub path：它要求显式 `--out` destination，且拒绝写入
checked-in 的 `b14_uncertainty_calibration_report.json`。它可为开发写出临时 stub report，
但不会修改 checked-in B14 artifacts。

`eval/b14_public_aggregate_feasibility_screen.py --self-test` 运行针对一个
synthetic minimal B11 + B12 + B13 fixture 验证 bounded public-aggregate
feasibility / no-go screen。它发出
`verdict=no_go_public_aggregate_only`（或 B11 aggregate 无记录时
`insufficient_data_public_aggregate_only`），并设置
`uncertainty_calibration_performed=false`、`calibrated_model_claim=false`、
`per_record_inputs_available=false`、`uncertainty_score_found=false`、
`rotations_evaluated=false`、`metrics_evaluated=false` 与
`no_fake_metrics_from_aggregate_means=true`。它运行 4 个 checks：
`happy_path`、`input_validation_blocks`、`insufficient_data_branch` 与
`forbidden_scan`。

## Artifacts

- `artifacts/b14_uncertainty_calibration/b14_uncertainty_calibration.algorithm.json`
  （frozen spec；deterministic，stable sha256；仅通过
  `--regenerate-artifacts` 重新生成）
- `artifacts/b14_uncertainty_calibration/b14_uncertainty_calibration_report.json`
  （synthetic-fixture self-test 报告，verdict `insufficient_data`；
  `uncertainty_calibration_performed=false`、
  `calibrated_model_claim=false`、`per_record_inputs_available=false`、
  `stage_is_uncertainty_calibration=true`、`metrics_evaluated=false`、
  `no_fake_metrics_from_aggregate_means=true`、
  `uncertainty_score_found=false`、`rotations_evaluated=false`、
  `rotations_defined=true`、`rotation_count=3`、`winner_declared=false`；
  无 empirical per-rotation metric values）
- `artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json`
  （bounded public-aggregate feasibility / no-go screen 报告；
  `verdict=no_go_public_aggregate_only` 或
  `insufficient_data_public_aggregate_only`；
  `uncertainty_score_found=false`、`rotations_evaluated=false`、
  `full_b14_possible_from_public_artifacts=false`、
  `metrics_evaluated=false`、`no_fake_metrics_from_aggregate_means=true`）

## What's autonomous vs. needs user action

### Autonomous（现在可做）

- B14 plan 文档（本文件）
- B14 report aggregator skeleton（`eval/b14_uncertainty_calibration.py`）+
  只读 `--self-test`（将内存中期望 artifacts 与 on-disk artifacts 比对，drift
  即失败）与显式 `--regenerate-artifacts` mutating 路径（发出
  `stage_is_uncertainty_calibration=true`、
  `uncertainty_calibration_performed=false`、
  `calibrated_model_claim=false`、`per_record_inputs_available=false`、
  `metrics_evaluated=false`、`no_fake_metrics_from_aggregate_means=true`、
  `uncertainty_score_found=false`、`rotations_evaluated=false`、
  `rotations_defined=true`、`rotation_count=3`、`winner_declared=false`；
  无 empirical per-rotation metric values）
- B14 frozen algorithm spec + synthetic-fixture report artifacts
- B14 bounded public-aggregate feasibility / no-go screen
  （`eval/b14_public_aggregate_feasibility_screen.py`）+ self-test +
  `artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json`
  （读取已发布的 B11 + B12 + B13 artifacts；发出
  `no_go_public_aggregate_only` / `insufficient_data_public_aggregate_only`；
  从不声称 empirical calibration，从不计算 metric，从不选择 uncertainty
  score，从不声明 winner）

### 需要 per-record ephemeral inputs

- B14 真实 calibration 需要 B11/B13 live runs 的 per-record uncertainty
  scores、per-record binary outcomes、paired cross-model outputs、schema-repair
  per-call rows 与 candidate score distributions。若这些记录尚未产生，B14 发出
  `insufficient_data` / `not_implemented`。

### 需要 user review

- 结果解读
- 决定是否使用 B14-found calibrated uncertainty score 作为 research candidate
  进入 B16（downstream agent evaluation）
- 决定是否将 B14-found uncertainty score 用于未来 selective-abstention policy
  工作（需单独 preregistration）
- 决定是否从 minimum viable 扩展到 full B14（更多 signals、更多 rotations、
  更多 groups）

## Next steps after B14

- **B14 success**：识别出一个 calibrated、model-independent 的 uncertainty
  score（test split 上 ECE ≤ 0.05，coverage=0.90 处 worst-group selective
  risk ≤ 0.15，全部 3 个 rotations 通过）。进入 B16 将其作为 selective-
  abstention signal 下游测试。
- **B14 failure**：无 calibrated uncertainty score 满足 predeclared criteria。
  balanced policy 继续在没有 calibrated uncertainty score 的情况下运行；B16
  应使用 uncalibrated reference。
- **B14 partial**：部分 metrics 通过，并非全部。调查 group-conditional
  calibration；可能在一个单独的 B14B round 中扩展 signal families（需单独
  preregistration）。
