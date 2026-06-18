# B16 Downstream Coding-Agent Evaluation

Date: 2026-06-18

B16 是 **downstream coding-agent evaluation** 阶段。目标是产出一个
**frozen、preregistered 的 paired within-task randomized controlled
trial (RCT)**，衡量某个 candidate retrieval/context variant 是否能
改进下游 coding agent（而非仅 retrieval aggregates），基于真实、
paired、isolated-workspace 的 agent runs。

B16 是一个 **bounded planning / feasibility 阶段**，**不是** live
downstream agent evaluation。当前 skeleton 不执行任何 live downstream
agent runs，不执行 patch execution，不评估 agent-behavior metrics，
也不评估 solve rate。frozen preregistration
(`eval/b16_downstream_agent_evaluation.py`) 定义了 arm set、task
types、metric registry、hard gates 与 experimental structure
（no-LLM feasibility → paired live agent RCT → freeze candidate
retrieval variant → fresh validation）；bounded public-aggregate
feasibility / no-go screen
(`eval/b16_public_aggregate_feasibility_screen.py`) 读取已发布的
B11 matrix + B12/B13/B14/B15 公共 screens，并发出
`no_go_public_aggregate_only`（或
`insufficient_data_public_aggregate_only`）verdict。

> **Important claim boundary。** B16 **是** downstream-agent-evaluation
> *stage*（`stage_is_downstream_agent_evaluation=true`），但当前
> skeleton 不执行任何 live downstream agent runs
>（`downstream_agent_runs_performed=false`），不执行 patch execution
>（`patch_execution_performed=false`），不评估 agent-behavior metrics
>（`agent_behavior_metrics_evaluated=false`），也不评估 solve rate
>（`solve_rate_evaluated=false`）。synthetic-fixture / `--input` stub
> 报告设置 `per_record_inputs_available=false`、
> `promotion_ready=false`、`default_should_change=false`、
> `evidencecore_semantics_changed=false`、
> `retrieval_variant_promoted=false`、
> `policy_search_performed=false`、`quality_strategy_tuned=false`、
> `new_provider_calls=0`，使该公共 artifact 不会被误读为 empirical
> B16 downstream agent 结果。此 commit 严格是 skeleton / no-go commit：
> 当前 flags
>（`downstream_agent_runs_performed=false`、
> `patch_execution_performed=false`、
> `agent_behavior_metrics_evaluated=false`、
> `solve_rate_evaluated=false`、`per_record_inputs_available=false`、
> `promotion_ready=false`、`default_should_change=false`、
> `evidencecore_semantics_changed=false`、
> `retrieval_variant_promoted=false`）保持 false。任何未来真实的 B16
> empirical 路径都需要其自身独立的 preregistration；该未来路径的确切
> flag schema 是 future work，在当前 skeleton 中**不**存在。此 commit
> 中的 B16 结果仅为 research candidates：此 skeleton/no-go commit
> 不授权 default change、retrieval-variant promotion、EvidenceCore
> 修改，也不声称 retrieval improvements improve coding agents。

> **Important retrieval-vs-downstream boundary。** B10-B15
> retrieval/context candidate research 是 **retrieval research**；
> 它**不**证明 downstream coding-agent value。Retrieval improvements
> **不是** downstream agent improvements。B15 PackPolicy **不是**
> downstream agent improvement。真实 B16 downstream agent evaluation
> 需要 private / ephemeral 的 per-run paired agent outputs：同一 task
> 在两个 arms 下的 paired live downstream agent runs、per-run agent
> event logs（tool calls、first-file-before-edit timing、wrong-file-edit
> annotations）、per-run patches / diffs、per-run test execution
> results、per-run solve labels、per-run tool-call / token / latency /
> cost rows、per-run isolated fresh workspace proof、per-run randomized
> arm order、以及 task oracle / hidden-test manifest。这些在当前公共
> artifact 中均不存在。位于
> `eval/b16_public_aggregate_feasibility_screen.py` 的 bounded
> public-aggregate feasibility / no-go screen 读取已发布的 B11 matrix、
> B12 public screen、B13 public feasibility、B14 public feasibility
> 与 B15 public prior-screen 报告，并在
> `artifacts/b16_downstream_agent_evaluation/` 下发出
> `no_go_public_aggregate_only`（或
> `insufficient_data_public_aggregate_only`）报告。该 screen 从不
> 声称 downstream agent value，从不从 retrieval aggregates 计算
> solve-rate / tool-call / token / latency / cost metric，从不
> promote retrieval variant，从不 freeze candidate retrieval variant，
> 也从不声明 winner。

> **CRITICAL anti-fabrication boundary。** skeleton **绝不可**从
> retrieval aggregates 计算伪造的 solve-rate /
> correct-file-before-first-edit / wrong-file-edits / tool-call /
> token / latency / cost 指标。B11/B12/B13/B14/B15 artifacts 是
> retrieval/context candidate research；它们**不**包含 per-run
> paired agent outputs，因此从中计算的任何 downstream agent metric
> 都是 fabrication。synthetic fixture 仅验证 arm set、task types、
> metric names 与 hard gates 已正确连接；它**不**将 synthetic
> metric values 当作 empirical B16 结果呈现。报告呈现
> `downstream_agent_runs_performed=false`、
> `patch_execution_performed=false`、
> `agent_behavior_metrics_evaluated=false`、
> `solve_rate_evaluated=false` 与
> `no_fake_downstream_metrics_from_retrieval_aggregates=true`，
> 使读者不会误将 skeleton 当作 empirical B16 downstream agent 结果。

## Preregistration declaration

以下 artifacts、arm set、task types、metric registry、hard gates、
experimental structure 与 predeclared success/partial/failure criteria
在任何 B16 empirical runs 之前已 **FROZEN**。B16 empirical runs 开始
后，不允许对 arm set、task types、metric registry、hard gates 或
success criteria 进行 retuning。任何 post-hoc 分析必须标记为
exploratory 并需要独立的 validation round。

### Frozen artifacts

- `balanced_policy_v1_benchmark_routed`（B10 frozen spec）— referenced，
  not modified
- `balanced_policy_v1_runtime_shadow_ambiguous_branch`（B10B shadow
  predicate）— referenced，not modified
- B11/B12/B13/B14/B15 frozen criteria — referenced，not modified
- B16 algorithm spec 本身
  (`artifacts/b16_downstream_agent_evaluation/b16_downstream_agent_evaluation.algorithm.json`)
  — 在任何 downstream agent runs 之前 frozen；stable sha256

## Objective

产出一个 **frozen、preregistered 的 paired within-task RCT**，衡量
candidate retrieval/context variant 是否在 paired live agent runs
（isolated fresh workspace、randomized arm order、除 retrieval/context
variant 外相同的 budget/tools/prompt、no cross-run memory）下改进
downstream coding agent。B16 RCT **不是** retrieval aggregate 分析；
它是 downstream agent RCT。B16 不 learn LLM，不修改 EvidenceCore，
不 promote default，不 promote retrieval variant，也不声称
retrieval improvements improve coding agents。

## Arms (FROZEN)

arm set 是 B16 paired RCT 可比较的 retrieval/context variants 的
closed set：

- `control_current_retrieval_v0` — 当前 retrieval stack（control
  arm）
- `balanced_v1_retrieval_candidate` — balanced_v1 retrieval
  candidate（treatment arm）
- `candidate_pack_policy_v0` — EXPLORATORY ONLY；仅当真实 B15
  candidate PackPolicy 存在时才包含
  (`only_if_b15_real_candidate_exists`)。B15 skeleton 不产出
  candidate（`pack_policy_learned=false`），因此该 arm 默认 EXCLUDED。
- `gold_context_ceiling` — DEBUGGING-ONLY；提供 gold context 作为
  ceiling reference (`debugging_only_never_promoted`)。NEVER 用于
  promotion；默认 EXCLUDED。

Primary comparison arms（始终存在）：
`control_current_retrieval_v0` vs
`balanced_v1_retrieval_candidate`。

## Task types (FROZEN)

task-type set 是 B16 paired RCT 可评估的 downstream coding-agent
tasks 的 closed set。Task types 是 model-independent 且
label-free：它们描述 agent task shape，而不是 benchmark-private
oracle 或 hidden tests。

- `bug_localization`
- `small_code_edit`
- `test_selection`
- `multi_file_feature`
- `refactor_impact`

## Paired within-task randomization (FROZEN)

真实 B16 是 paired within-task randomized controlled trial。每个 task
在两个 arms（control 与 treatment）下运行两次，满足：

- **paired within-task randomization** — 同一 task 在两个 arms 下
  被回答，以便 per-task noise 被 differenced out；
- **isolated fresh workspace** per run — runs 之间无状态泄漏；
- **randomized arm order** — arm order 按 task 随机化，以将 arm 与
  run order 解耦；
- **same budget / tools / prompt EXCEPT the retrieval/context variant**
  — 唯一变化的因素是 retrieval/context variant
  (`operational_parity_same_tools_budget_prompt_except_retrieval_variant=true`)；
- **no cross-run memory** — agent 对 paired run 无记忆
  (`operational_parity_no_cross_run_memory=true`)。

真实 B16 run 必须产出 per-run event logs、patches/diffs、test
execution results、solve labels 与 tool-call/token/latency/cost rows。

## Metric registry (FROZEN)

当真实 per-run paired agent inputs 可用时，B16 将计算这些 metric
NAMES。skeleton 定义它们并验证 hard gates，但**不**从 retrieval
aggregates 计算伪造的 metric values。

- `solve_rate`（per-arm paired-task solve rate，来自 solve labels）
- `correct_file_before_first_edit`（per-arm 中第一次 edit 落在
  正确 file 的比例，来自 first-file-before-first-edit event）
- `wrong_file_edits`（per-arm 中 edit 到错误 file 的 count 或
  rate，来自 wrong-file-edit annotations）
- `tool_calls_before_first_edit`（per-arm 中 first edit 之前的
  tool-call count，来自 agent event logs）
- `context_tokens`（per-arm context token count，来自 per-run
  token rows）
- `tests_pass`（per-arm 中 tests 通过的 run 比例，来自 test
  execution results）
- `latency`（per-arm run latency，来自 per-run latency rows）
- `cost`（per-arm run cost，来自 per-run cost rows）

每个 metric 都需要 per-run paired agent outputs；**没有** metric 可
从 retrieval aggregates 计算。

## Hard gates (FROZEN)

以下 hard gates 在任何 B16 downstream agent runs 之前已 FROZEN。任何
未通过 gate 的 candidate retrieval variant 都被拒绝，无论其
aggregate solve-rate 或任何 retrieval-aggregate signal 如何。

- **feasibility_gate**：真实 B16 需要 paired live agent runs、
  agent event logs、patches/diffs、test execution results、solve
  labels、first-file-before-first-edit events、wrong-file-edit
  annotations、tool-call/token/latency/cost rows、isolated workspace
  proof、randomized arm order 与 task oracle/hidden-test manifest。
  skeleton 不评估此 gate（无真实 per-run inputs）；仅定义它。
- **denominator_gate**：每个 (task_type, arm) cell 的 denominator
  必须 ≥ frozen minimum
  (`min_denominator_per_task_type_arm_cell=30`)；无 small-denominator
  solve-rate claim 可被 promoted。skeleton 不评估此 gate；仅定义它。
- **leakage_gate**：无 benchmark-private label、无 hidden-test
  answer、无 solve label 作为 feature 进入 retrieval variant 或
  agent prompt；solve labels 是 validation TARGET，**不是** input。
- **operational_parity_gate**：arms 必须共享相同的 budget、tools
  与 prompt，EXCEPT retrieval/context variant，且每个 run 有
  isolated fresh workspace、randomized arm order 与 no cross-run
  memory
  (`operational_parity_token_budget_match_tolerance=0.10`、
  `operational_parity_latency_match_tolerance=0.15`)。skeleton 不评估
  此 gate；仅定义它。
- **privacy_gate**：`aggregate_only_public_artifact=true`；无 raw
  records、task IDs、repo IDs、candidate IDs、paths、spans、snippets、
  prompts、responses、diffs、patches、test execution results、solve
  labels、first-file-before-first-edit events、wrong-file-edit
  annotations、tool-call/token/latency/cost rows、agent event logs、
  gold spans、private labels、provider keys、base URLs、API
  keys/secrets/tokens、content SHAs、digests 或 line ranges 出现在
  任何公共 artifact 中；skeleton 中 `new_provider_calls=0`。
- **promotion_false_gate**：`promotion_ready=false`、
  `default_should_change=false`、
  `evidencecore_semantics_changed=false`、
  `retrieval_variant_promoted=false`、
  `downstream_agent_runs_performed=false`、
  `patch_execution_performed=false`、
  `agent_behavior_metrics_evaluated=false`、
  `solve_rate_evaluated=false`、
  `policy_search_performed=false`、
  `quality_strategy_tuned=false` 始终存在，因此 skeleton / stub /
  no-go 报告不会被误读为 promoted retrieval variant 或 downstream
  agent 结果。

## Split protocol (FROZEN)

真实 B16 将 per-run inputs 拆分为 **task-screen split** 与
**fresh-validation split**，按 (task_type, repo, model_family)
stratified。split protocol 为
`stratified_by_task_type_repo_model_family`，`task_screen_fraction=0.50`
与 `fresh_validation_fraction=0.50`。fresh-validation split held out
且 reported once
(`fresh_validation_split_reported_once=true`)。fresh-validation split
上的任何 metric 都不可反馈到 task screen 或 candidate-retrieval-
variant freeze。

## Worst-group reporting

B16 报告 `{task_type, repo, model_family, language}` groups 的
worst-group metrics，加上 `CVaR_20%` tail average（worst 20% of
group metrics）。CVaR tail fraction 为 `cvar_alpha=0.20`（frozen）。

## Privacy / publication gates

公共 artifacts 必须 aggregate-only。B16 evaluator 强制：

- **无** raw records、task IDs、repo IDs、candidate IDs、paths、
  spans、snippets、prompts、responses、diffs、patches、test
  execution results、solve labels、first-file-before-first-edit
  events、wrong-file-edit annotations、tool-call/token/latency/cost
  rows、agent event logs、gold spans、private labels、provider keys、
  base URLs、API keys/secrets/tokens、content SHAs、digests 或
  line ranges 出现在任何公共 artifact 中；
- **无** raw filesystem path strings、64-char hex digests、http(s)
  URLs 或 credential assignments 作为 values；
- `aggregate_only_public_artifact=true`；
- `new_provider_calls=0`（skeleton；无 live LLM calls 且无 live
  downstream agent runs）；
- `forbidden_public_key_scan_clean=true`。

## Predeclared success / partial / failure criteria

以下 criteria 在任何 B16 empirical runs 之前已 FROZEN
(`PREDECLARED_CRITERIA`)：

| Outcome | Criterion |
| --- | --- |
| **Success** | frozen candidate retrieval variant 在 fresh-validation split 上 solve rate 比 control arm 提升 ≥ `0.02`（每个 task type），且 `correct_file_before_first_edit` 提升 ≥ `0.02`、`wrong_file_edits` 回归 ≤ `0.15`，且每个 estimated metric 都在 frozen denominator 与 operational-parity gates 内，且 cost per arm 已报告。 |
| **Partial** | 部分 task types 在 solve rate 上提升但非全部；或 `wrong_file_edits` 在一个 task type 上回归；或一个 metric 在 denominator/operational-parity gates 内而另一个不在。 |
| **Failure** | 在 fresh-validation split 上无 task type 在 solve rate 上提升，或任何 hard gate 失败（feasibility、denominator、leakage、operational parity、privacy、promotion false）。 |

Frozen numeric gates：

- `solve_rate_strictly_greater_threshold = 0.02`
- `correct_file_before_first_edit_strictly_greater_threshold = 0.02`
- `wrong_file_edits_regression_threshold = 0.15`
- `cvar_alpha = 0.20`
- `task_screen_fraction = 0.50`
- `fresh_validation_fraction = 0.50`
- `min_denominator_per_task_type_arm_cell = 30`
- `randomization_balance_max_imbalance = 0.05`
- `operational_parity_token_budget_match_tolerance = 0.10`
- `operational_parity_latency_match_tolerance = 0.15`
- `cost_reported_per_arm = true`

B16 verdict 框架发出以下之一：

- `success`（所有 task types 在 solve rate 上提升，所有 gates 在
  fresh-validation split 上通过）
- `failure`（无提升，或任何 hard gate 失败）
- `partial`（部分 task types 提升，非全部；或一个 gate 处于边界）
- `insufficient_data`（synthetic fixture，或 runs 过少）
- `not_implemented`（`--input` stub，真实 downstream agent RCT
  deferred）

skeleton 仅发出 `insufficient_data`（synthetic fixture）或
`not_implemented`（ci_ephemeral_records stub）；`success` / `failure`
/ `partial` **不**由本 skeleton 发出。任何未来真实 B16 empirical
路径若要发出它们，需要其自身独立的 preregistration，其确切 flag
schema 是 future work 且**不**在本 skeleton 中。此 commit 严格保持
`downstream_agent_runs_performed=false`、
`patch_execution_performed=false`、
`agent_behavior_metrics_evaluated=false` 与
`solve_rate_evaluated=false`。

## Required per-record inputs (real-B16 data contract)

真实 B16 downstream agent evaluation 需要以下所有 per-run。若任一
缺失，真实 B16 无法运行，skeleton 发出 `insufficient_data` /
`not_implemented`。

- `per_run_paired_arm_assignment`
- `per_run_agent_event_log`
- `per_run_patch_or_diff`
- `per_run_test_execution_result`
- `per_run_solve_label`
- `per_run_first_file_before_first_edit_event`
- `per_run_wrong_file_edit_annotation`
- `per_run_tool_calls_tokens_latency_cost`
- `per_run_isolated_fresh_workspace_proof`
- `per_run_randomized_arm_order`
- `per_run_no_cross_run_memory_proof`
- `per_task_oracle_or_hidden_test_manifest`

## Retrieval-vs-downstream boundary

B10-B15 retrieval/context candidate research 是 **retrieval
research**；它**不**证明 downstream coding-agent value。

- B11 matrix deltas 是 retrieval deltas，**不是** downstream
  solve-rate improvements。
- B12 mechanism decomposition 是 retrieval mechanism screen，**不是**
  downstream agent mechanism proof。
- B13 policy search 是 retrieval policy search，**不是** downstream
  agent policy。
- B14 uncertainty calibration 是 retrieval calibration feasibility
  screen，**不是** downstream agent calibration。
- B15 PackPolicy 是 retrieval/context pack-policy candidate，**不
  是** downstream agent improvement。

Retrieval improvements **不是** downstream agent improvements。B15
PackPolicy **不是** downstream agent improvement。B16 是唯一能衡量
downstream agent value 的阶段，而 B16 skeleton **不**执行该衡量。

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
retrieval_variant_promoted=false
stage_is_downstream_agent_evaluation=true (B16 stage IS downstream agent evaluation)
downstream_agent_runs_performed=false (skeleton 不执行 live agent runs)
patch_execution_performed=false (skeleton 不执行 patch execution)
agent_behavior_metrics_evaluated=false (skeleton 不评估 agent behavior metrics)
solve_rate_evaluated=false (skeleton 不评估 solve rate)
per_record_inputs_available=false (skeleton；无真实 per-run inputs)
policy_search_performed=false
quality_strategy_tuned=false
new_provider_calls=0 (skeleton；无 live LLM calls)
no_fake_downstream_metrics_from_retrieval_aggregates=true
aggregate_only_public_artifact=true
```

## What B16 does NOT prove

- B16 **不**运行 live downstream agent runs。
- B16 **不**执行 patches。
- B16 **不**评估 agent-behavior metrics。
- B16 **不**评估 solve rate。
- B16 **不**从 retrieval aggregates 计算 solve-rate /
  correct-file-before-first-edit / wrong-file-edits / tool-call /
  token / latency / cost metrics。
- B16 **不**promote 任何 retrieval variant。
- B16 **不**修改任何 defaults。
- B16 **不**修改 `EvidenceCore` semantics。
- B16 **不**声称 retrieval improvements improve coding agents。
- B16 **不**声称 B15 PackPolicy improves downstream agents。
- B16 结果仅为 research candidates；B16-frozen candidate retrieval
  variant **不是** promoted retrieval variant，也**不是** new
  default，除非通过标准 promotion process 单独 promote。
- B16 的 `--input` 路径是 stub（`verdict="not_implemented"`）；
  完整 downstream agent RCT deferred 到后续 task。
- B10-B15 retrieval/context candidate research **不是** downstream
  agent value。

## Self-test (read-only) and explicit artifact regeneration

```bash
python3 eval/b16_downstream_agent_evaluation.py --self-test
python3 eval/b16_downstream_agent_evaluation.py --regenerate-artifacts
python3 eval/b16_downstream_agent_evaluation.py --self-test
python3 eval/b16_public_aggregate_feasibility_screen.py --self-test
python3 eval/b16_public_aggregate_feasibility_screen.py \
    --out artifacts/b16_downstream_agent_evaluation/b16_public_aggregate_feasibility_report.json
```

`eval/b16_downstream_agent_evaluation.py --self-test` 运行是
**read-only**：它针对 synthetic fixture（definitions-only；无
per-run paired agent outputs，无 computed metric values）验证
arm set、task types、metric registry、hard gates 与 experimental
structure，并将 in-memory expected algorithm spec + report 与
on-disk artifacts 比对，**drift 即失败**。它**不**修改 checked-in
artifacts。它发出
`stage_is_downstream_agent_evaluation=true`、
`downstream_agent_runs_performed=false`、
`patch_execution_performed=false`、
`agent_behavior_metrics_evaluated=false`、
`solve_rate_evaluated=false`、`per_record_inputs_available=false`、
`promotion_ready=false`、`default_should_change=false`、
`evidencecore_semantics_changed=false`、
`retrieval_variant_promoted=false`、
`policy_search_performed=false`、`quality_strategy_tuned=false`、
`new_provider_calls=0`、
`no_fake_downstream_metrics_from_retrieval_aggregates=true`，因此
synthetic-fixture 报告明确**不**是 empirical B16 downstream agent
结果。

read-only self-test 运行以下检查：

1. `forbidden_scan` — forbidden public keys/values scan
2. `spec_hash_stable` — algorithm spec sha256 稳定性
3. `arm_set_closed` — primary / exploratory / debug arms 闭合且
   互不相交；control 与 treatment 不同
4. `task_types_closed` — 5 个 closed-set task types
5. `metric_registry` — 8 个 metric names 定义；无 aggregate-mean
   metrics
6. `hard_gates_defined` — feasibility / denominator / leakage /
   operational-parity / privacy / promotion-false gates 定义
7. `experimental_structure_frozen` — 4 个 frozen stages；无反馈
8. `no_fake_downstream_metrics_from_retrieval_aggregates` —
   synthetic fixture 无 per-run paired agent outputs 与 metric
   values
9. `input_stub_not_implemented` — `--input` stub 返回
   `not_implemented`
10. `reference_specs_pinned` — B10/B10B/B11/B12/B13/B14/B15
    reference specs 在 disk 上存在
11. `artifacts_match_in_memory` — read-only drift check：in-memory
    expected spec + report 与 on-disk artifacts 一致

`python3 eval/b16_downstream_agent_evaluation.py --regenerate-artifacts`
是**唯一**修改 checked-in artifacts 的路径：它从当前 build
functions 重写 on-disk algorithm spec + synthetic-fixture report。
修改后，重新运行 `--self-test` 以确认 on-disk artifacts 与
in-memory expected objects 一致（无 drift）。

`--input` 路径是非规范 stub 路径：它需要显式 `--out` 目标，并拒绝
写入 `artifacts/b16_downstream_agent_evaluation/` 内的任何路径
（canonical report、algorithm spec 或 public-aggregate feasibility
report）。它可写入临时 stub 报告用于开发，但不修改 checked-in B16
artifacts。

`eval/b16_public_aggregate_feasibility_screen.py --self-test` 运行
针对 synthetic minimal B11 + B12 + B13 + B14 + B15 fixture 验证
bounded public-aggregate feasibility / no-go screen。它发出
`verdict=no_go_public_aggregate_only`（或
`insufficient_data_public_aggregate_only`），并设置
`downstream_agent_runs_performed=false`、
`patch_execution_performed=false`、
`agent_behavior_metrics_evaluated=false`、
`solve_rate_evaluated=false`、
`per_record_inputs_available=false`、
`retrieval_variant_promoted=false`、
`full_b16_possible_from_public_artifacts=false`。

## Artifacts

- `artifacts/b16_downstream_agent_evaluation/b16_downstream_agent_evaluation.algorithm.json`
  (frozen spec；deterministic，stable sha256；仅通过
  `--regenerate-artifacts` 重新生成)
- `artifacts/b16_downstream_agent_evaluation/b16_downstream_agent_evaluation_report.json`
  (synthetic-fixture self-test report，verdict `insufficient_data`；
  `downstream_agent_runs_performed=false`、
  `patch_execution_performed=false`、
  `agent_behavior_metrics_evaluated=false`、
  `solve_rate_evaluated=false`、
  `per_record_inputs_available=false`、
  `stage_is_downstream_agent_evaluation=true`、
  `no_fake_downstream_metrics_from_retrieval_aggregates=true`；
  无 empirical per-run metric values)
- `artifacts/b16_downstream_agent_evaluation/b16_public_aggregate_feasibility_report.json`
  (bounded public-aggregate feasibility / no-go screen report；
  `verdict=no_go_public_aggregate_only` (或
  `insufficient_data_public_aggregate_only`)；
  `full_b16_possible_from_public_artifacts=false`；
  carry forward B11 `partial_with_failure` 与 B12/B13/B14/B15
  no-go 或 screen-only statuses；aggregate-only，无 raw event
  traces、paths、diffs、prompts/responses、hidden tests 或 task IDs)

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B16 plan document (this file)
- B16 evaluator skeleton (`eval/b16_downstream_agent_evaluation.py`)
  + read-only `--self-test` (compares in-memory expected artifacts
  to on-disk artifacts, fails on drift) 与 explicit
  `--regenerate-artifacts` mutating path
- B16 frozen algorithm spec + synthetic-fixture report artifacts
- B16 bounded public-aggregate feasibility / no-go screen
  (`eval/b16_public_aggregate_feasibility_screen.py`) + self-test +
  `artifacts/b16_downstream_agent_evaluation/b16_public_aggregate_feasibility_report.json`
  (读取已发布的 B11 matrix + B12/B13/B14/B15 公共 screens；发出
  `no_go_public_aggregate_only` /
  `insufficient_data_public_aggregate_only`；从不声称 downstream
  agent value，从不从 retrieval aggregates 计算 downstream metric，
  从不 promote retrieval variant，从不声明 winner)

### Needs per-run ephemeral paired agent outputs

- B16 真实 downstream agent evaluation 需要 paired live downstream
  agent runs、per-run agent event logs、per-run patches/diffs、
  per-run test execution results、per-run solve labels、per-run
  first-file-before-first-edit events、per-run wrong-file-edit
  annotations、per-run tool-call/token/latency/cost rows、per-run
  isolated fresh workspace proof、per-run randomized arm order 与
  task oracle/hidden-test manifest。若这些 records 尚未产出，B16
  发出 `insufficient_data` / `not_implemented`。

### Needs user review

- Results interpretation
- 决定是否进入真实 B16 empirical 路径（需要独立 preregistration）
- 决定是否从 minimum viable task-type set 扩展到更大 set（需要独立
  preregistration）

## Next steps after B16

- **B16 success**（未来真实 B16 路径）：frozen candidate retrieval
  variant 在 fresh-validation split 上提升 solve rate，所有 hard
  gates 通过。通过标准 promotion process 推进；B16 success **不**
  auto-promote。
- **B16 failure**（未来真实 B16 路径）：无 candidate retrieval
  variant 满足 predeclared criteria。当前 retrieval stack 继续；
  无 retrieval variant 被 promoted。
- **B16 partial**（未来真实 B16 路径）：部分 task types 提升，非
  全部。调查 task-type-conditional retrieval variants；可能在独立的
  B16B round 中扩展 task-type set（需要独立 preregistration）。
- **B16 skeleton / no-go**（此 commit）：bounded public-aggregate
  feasibility / no-go screen 确认真实 B16 无法仅凭公共 aggregates
  完成。真实 B16 需要 ephemeral per-run paired agent outputs。
