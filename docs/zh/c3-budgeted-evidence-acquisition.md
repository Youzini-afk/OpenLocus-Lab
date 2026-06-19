# C3 Budgeted Evidence Acquisition v0

日期：2026-06-19

C3 是继 C2/B12 之后的 **budgeted evidence acquisition** 阶段。它是一个基于
C1 私有记录适配器（`eval/c1_private_records.py`）的**真实 replay policy
实验**，而非 planner 或 skeleton。一个小的、冻结的、可解释的候选策略集合
（每个策略只是一个 runtime-clean `route_features` 字典的纯函数）被 replay
到 P21 的 per-strategy outcomes 上，并在 common-complete 分母下将其
**budgeted evidence utility** 与两个 baseline（P25 和 balanced_v1）进行比较。

> **重要的 claim 边界。** C3 是 budgeted replay policy 实验，**不**是 promotion
> step。per-cell 公开报告是 **diagnostic-rank-only**：它只输出充分的 aggregate
> 统计信息和按 utility 的候选策略诊断排序，但**绝不**声明 winner。per-cell
> 候选选择被推迟到 matrix combiner。`promotion_ready=false`、
> `default_should_change=false`，`EvidenceCore` 语义不变。

## Runtime-clean 硬规则

候选策略**必须只**接收一个 `route_features` 字典（投影到冻结的 feature
allowlist），**绝不**接收 `PrivateRecord`。候选路由**绝不**读取
`task_bucket`、`task_risk_tags`、`has_gold`、`score_group`、`outcomes`、
`task_id`、`repo_id`、`model_family`、`language`、私有 hash 等。

evaluator 通过**真实的 PrivateRecord 字段 scrub 测试**验证 routing invariance：
为每条记录构建一个 scrubbed 副本，其中每个非 `route_features` 字段
（`task_bucket`、`task_risk_tags`、`score_group`、`has_gold`、`outcomes`、
`outcome_present`、`task_id`、`repo_id`、`model_family`、`language`、
`private_record_hash`、`source_ordinal`、p31/p33 块、`taint`）被替换为
**保证与原始值不同**的 sentinel/permuted 值（例如 `not has_gold`、反转的
`outcome_present` 布尔值）。确认 scrubbed 记录的 `route_features` 与原始相同，
确认每个 scrubbed 私有字段确实不同，并确认从 scrubbed 记录的投影
`route_features` 计算的候选策略 actions 与原始选择一致。公开报告暴露两个
aggregate 布尔值：

- `selected_actions_invariant_under_private_field_permutation=true`
- `runtime_clean_policy_inputs_only=true`

## 允许的 runtime features（冻结）

C1 `route_features` 在 P21 中出现的字段与此冻结 allowlist 的交集。缺失的
feature 视为 false / 0：

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

`route_features` 本身**绝不**出现在公开报告中（它是 forbidden key）；只输出
冻结的 feature-name 列表和 aggregate `feature_presence_counts`。

## 允许的 candidate actions（冻结）

候选策略**必须**只选择这 5 个 action 之一。P25 和 balanced_v1 **不**是
candidate actions；它们只是 baseline，必须标记
`runtime_clean_candidate_policy=false`、`benchmark_label_taint=true`。

- `candidate_baseline`
- `weak_candidate_only`
- `llm_span_narrow`
- `llm_filter`
- `llm_abstain_filter`

## 冻结的候选策略集合

一个小的、可解释的、固定的集合，**不**是从 outcome 派生的。在 algorithm
spec 中冻结；不从 outcomes 调参。

| Policy id | 规则 |
| --- | --- |
| `local_only` | 永远 `candidate_baseline` |
| `weak_on_noise_else_local` | 若 `query_noise>0` 则 `weak_candidate_only` 否则 `candidate_baseline` |
| `span_narrow_on_anchor_else_local` | 若 `local_anchor` 且 `rrf_backed_by_anchor` 则 `llm_span_narrow` 否则 `candidate_baseline` |
| `filter_on_noise_else_span_narrow_on_anchor_else_local` | 若 `query_noise>0` 则 `llm_filter`，elif `local_anchor` 且 `rrf_backed_by_anchor` 则 `llm_span_narrow`，否则 `candidate_baseline` |
| `abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local` | 若 `local_anchor` 且非 `rrf_backed_by_anchor` 则 `llm_abstain_filter`，elif `local_anchor` 且 `rrf_backed_by_anchor` 则 `llm_span_narrow`，否则 `candidate_baseline` |
| `weak_on_disagreement_span_on_anchor_else_local` | 若 `local_anchor` 且非 `rrf_backed_by_anchor` 则 `weak_candidate_only`，elif `local_anchor` 且 `rrf_backed_by_anchor` 则 `llm_span_narrow`，否则 `candidate_baseline` |

## Budgeted Evidence utility（冻结常量）

```text
utility = span_f0_5
          - lambda * added_false_span
          - mu * primary_false_positive_rate
          - cost_weight * model_calls
```

在任何 C3 replay 之前冻结：

- `lambda = 1.0`
- `mu = 1.0`
- `cost_weight = 0.1`

每个所选 action 的 `model_calls` = 1（`llm_span_narrow` / `llm_filter` /
`llm_abstain_filter`），0（`candidate_baseline` / `weak_candidate_only`）。

## Baseline（仅作 baseline，绝不作 candidate policy）

- **P25 baseline**：使用 C1 `compute_p25_strategy(record)` 进行 outcome 选择。
  标记 `benchmark_label_taint=true`（P25 路由读取 benchmark route labels）。
- **balanced_v1 baseline**：若 C1 `balanced_branch_predicate(record)` 则
  `weak_candidate_only` 否则 P25 strategy。标记
  `benchmark_label_taint=true`。

候选策略**绝不**调用 `compute_p25_strategy` / `balanced_branch_predicate`。

## 覆盖规则（common-complete 分母）

- 对一个 cell 的所有候选策略和 baseline 使用 **common-complete** 分母。
- 若任一 policy/baseline 的所选 action outcome 缺失，则该记录被排除并计入
  `incomplete_record_count`。
- 若 `complete_records == 0` => `status=coverage_insufficient`、
  `winner_declared=false`。
- per-cell 报告**绝不**声明 winner。它输出 `cell_diagnostic_rank_only=true`、
  `winner_declared=false`、
  `candidate_selection_deferred_to_matrix_combiner=true`。

## 公开 artifact forbidden fields

递归扫描拒绝 keys/values：`task_id`、`test_id`、`repo_id`、`run_id`、
`private_record_hash`、`record_hash`、`source_ordinal`、`candidate_id`、
`path`、`span`、`content_sha`、`query`、`raw_query`、`snippet`、`prompt`、
`response`、`provider_key`、`api_key`、`base_url`、`score_group`、`has_gold`、
`outcomes`、`strategy_results`、`p31_score_gold`、`p31_candidate_pools`、
`p33b_anchor_subtypes`、`task_risk_tags`、`route_features`、
`private_label`、`private_labels`、`label`、`labels`、`gold_spans`、`hash`、
`digest`、`task_bucket`。扫描对 key 名为精确匹配，因此安全的 metric 名如
`added_false_span` / `primary_false_positive_rate` / `added_gold_span`
仍然允许。

绝不输出 raw `repo_id` / `run_id` / `task_id` / `path` / hash 值。aggregate
`model_family` 和 `language` 计数是允许的。v0 省略 `task_bucket` 计数。

## 报告字段

- `schema_version`：`c3-budgeted-evidence-acquisition-report-v0`
- `generated_by`：`c3_budgeted_evidence_acquisition`
- `claim_level`：`budgeted_replay_policy_experiment_v0`
- `policy_count`、`candidate_policy_ids`、`action_set`、
  `allowed_runtime_features`、`objective_constants`
- `total_records`、`complete_records`、`incomplete_record_count`、`status`
  （`ok_cell_stats` / `coverage_insufficient` / `insufficient_data` /
  `privacy_or_schema_blocked`）
- `per_policy`：每个候选策略的 aggregate 指标（`span_f0_5`、
  `added_gold_span`、`added_false_span`、`primary_false_positive_rate`、
  `model_calls`、`utility` 的 mean + sum）
- `baselines`：`p25` 和 `balanced_v1` 的 aggregate 指标（带 taint 标记）
- `deltas`：每个候选策略 vs `p25` 和 vs `balanced_v1` 的 delta
- `diagnostic_rank_only`：按 mean utility 降序排列的候选策略 id
  （仅诊断；无 winner）
- `feature_presence_counts`：仅 aggregate
- `selected_actions_invariant_under_private_field_permutation`、
  `runtime_clean_policy_inputs_only`
- `safety_invariants` / privacy flags

## 模式

- `--self-test`：仅 synthetic fixture；**只读**（在内存中构建期望的 spec +
  报告并与磁盘 artifact 比较，发现 drift 则失败；**不**修改 checked-in
  artifact）；**绝不**声称 empirical support
  （`empirical_algorithm_experiment_performed=false`）。
- `--regenerate-artifacts`：**唯一**写入 canonical synthetic algorithm spec
  + self-test 报告到
  `artifacts/c3_budgeted_evidence_acquisition/` 的路径。代码修改后使用，然后运行
  `--self-test` 确认。
- `--input <path>`：通过 C1 适配器加载私有 P21 v1 记录并写入 aggregate-only
  公开报告。设置
  `empirical_algorithm_experiment_performed=true` 和
  `policy_search_or_enumeration_performed=true`。

## CI workflow 集成

C3 接入 `.github/workflows/real-provider-benchmark.yml` 的 P21 step：在 B12
消费 SAME ephemeral `$P25_RECORDS` 之后、`rm -f "$P25_RECORDS"` 之前，C3 运行：

```bash
python3 eval/c3_budgeted_evidence_acquisition.py \
  --input "$P25_RECORDS" \
  --out artifacts/real_provider_ci/c3_budgeted_evidence_acquisition_report.json
```

per-cell C3 **只输出充分统计信息且不声明 winner**。aggregate 布尔
`selected_actions_invariant_under_private_field_permutation` 和
`runtime_clean_policy_inputs_only` 为 matrix combiner 暴露。
`remote_calls_by_c3=0` 且 `model_calls_by_replay=0`（仅 replay）。

## Safety invariants

```text
empirical_algorithm_experiment_performed=true（仅 --input 真实记录时）
policy_search_or_enumeration_performed=true（冻结枚举，不调参）
replay_only=true
remote_calls_by_c3=0
model_calls_by_replay=0
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
aggregate_only_public_artifact=true
winner_declared=false
cell_diagnostic_rank_only=true
candidate_selection_deferred_to_matrix_combiner=true
```

## Self-test

```bash
python3 eval/c3_budgeted_evidence_acquisition.py --self-test
python3 eval/c1_private_records.py --self-test
```

C3 self-test 验证：forbidden 扫描、spec hash 稳定、冻结的
action/feature allowlist、冻结的 objective 常量、runtime-clean invariance
（真实 PrivateRecord 字段 scrub 测试）、P25/balanced 不是 candidate policy、
synthetic-fixture mechanics、在 synthetic C1 payload 上的 `--input` 完整模式、
missing-outcome => `coverage_insufficient`、无 per-cell winner、磁盘 artifact 与
内存构建一致（drift 检测）、以及 docs 路径在可行时存在。self-test 严格只读，
**绝不**修改 checked-in artifact；使用 `--regenerate-artifacts` 更新 canonical
artifact。synthetic fixture 不赋予任何 empirical support。

## Artifacts

- `artifacts/c3_budgeted_evidence_acquisition/c3_budgeted_evidence_acquisition.algorithm.json`
  （冻结 spec；确定性、稳定 sha256）
- `artifacts/c3_budgeted_evidence_acquisition/c3_budgeted_evidence_acquisition_report.json`
  （synthetic-fixture self-test 报告；`status` 是 mechanics 结果，**不**是
  empirical）
- `artifacts/real_provider_ci/c3_budgeted_evidence_acquisition_report.json`
  （CI ephemeral-records replay 报告；scientific status 是有效的 CI 结果，
  可能是 `ok_cell_stats` / `coverage_insufficient` / `insufficient_data`）

## C3 不证明什么

- C3 **不**证明任何候选策略已准备好 promotion。
- C3 **不**改变任何 default。
- C3 **不**改变 `EvidenceCore` 语义。
- C3 **不**从 outcomes 调参候选策略（集合是冻结的）。
- C3 **不**声明 per-cell winner；选择推迟到 matrix combiner。
- C3 的 `--input` replay 是真实的，但其输出仅是 diagnostic-rank-only。不跟随任何
  promotion / default change。
