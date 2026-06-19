# B18 OOD / Temporal Evaluation

Date: 2026-06-19

B18 是 **OOD（out-of-distribution）/ temporal evaluation** 阶段。
目标是产出一个 **frozen、preregistered 的 OOD / temporal
evaluation**，在 **no-retuning protocol** 下（no policy search、no
quality strategy tuning、no retrieval policy change、no EvidenceCore
semantics change、no default change、no promotion）跨五个 FROZEN
split axes——`temporal_split`、`repo_split`、`language_split`、
`model_family_split`、`adversarial_split`——评估 retrieval /
candidate / Evidence pipeline，使 in-distribution average 不会被误
读为 OOD 或 temporal generalization。

B18 是一个 **bounded preregistration + public-aggregate no-go
screen phase**，NOT 真正的 OOD / temporal evaluation，NOT policy
search，NOT quality strategy tuning，NOT default change，NOT
EvidenceCore semantics change，NOT promotion。当前 skeleton 不执行
任何真正的 OOD / temporal evaluation、不做 per-record replay、不
构造 commit-chronology temporal split、不做 adversarial holdout、
不计算 per-repo / per-language / per-model-family cell、不计算
worst-group 或 CVaR metric。Frozen preregistration
（`eval/b18_ood_temporal_evaluation.py`）定义 split axes、required
per-record inputs、metric registry、hard gates 与 experimental
structure（no-OOD-temporal-evaluation feasibility → frozen no-
retuning protocol → per-axis holdout evaluation → worst-group /
CVaR reporting）；bounded public-aggregate no-go screen 读取已发布
的 B11 prospective matrix aggregate report 以及可选的 R15 / R20 /
R26 repos.lock.jsonl 与 dataset manifest，emit 一个
`no_go_public_aggregate_only`（或
`public_aggregate_carry_forward_only`）verdict。

> **Important claim boundary.** B18 IS the ood-temporal-evaluation
> *stage*（`stage_is_ood_temporal_evaluation=true`），但当前 skeleton
> 不执行任何真正的 OOD / temporal evaluation
> （`ood_temporal_evaluation_performed=false`），不做 metrics
> evaluation（`metrics_evaluated=false`），不做 policy search
>（`policy_search_performed=false`），不做 quality strategy tuning
>（`quality_strategy_tuned=false`），不做 promotion
>（`promotion_ready=false`）。Synthetic-fixture / `--input` stub
> report 设置 `promotion_ready=false`、
> `default_should_change=false`、
> `evidencecore_semantics_changed=false`、
> `retrieval_policy_changed=false`、`metrics_evaluated=false`、
> `new_provider_calls=0`，使 public artifact 不会被误读为经验性
> B18 OOD / temporal 结果。本 commit 严格是 skeleton / no-go commit：
> 当前 flags（`ood_temporal_evaluation_performed=false`、
> `metrics_evaluated=false`、`policy_search_performed=false`、
> `quality_strategy_tuned=false`、
> `real_ood_temporal_supported=false`）保持 false。任何未来真正的
> B18 经验路径都需要其独立的 preregistration；该未来路径的精确
> flag schema 是 future work，不存在于本 skeleton。本 commit 的
> B18 结果仅为 research candidates：本 skeleton / no-go commit 不
> 授权任何 default change、retrieval-policy change、backend quality
> promotion、OOD / temporal evaluation、EvidenceCore modification，
> 也不声称任何 retrieval variant 改进了 downstream agent。

> **Important no-retuning boundary.** OOD / temporal evaluation 是
> 在 **frozen no-retuning protocol** 下的 **generalization** 对比。
> 一个 retrieval variant 若在 in-distribution task-screen split 上
> 获胜，但在 temporal / repo / language / model_family /
> adversarial holdout 上回退，则无论其 in-distribution 数字如何都
> 会被拒绝。No-retuning protocol 是使 OOD / temporal evaluation 有
> 意义的前提条件：没有它，OOD / temporal 对比会静默地把
> generalization 换成 in-distribution fit。

> **CRITICAL anti-fabrication boundary.** Skeleton MUST NOT 从现有
> B11 aggregate means 或 R15 / R20 / R26 repo locks 计算伪造的
> ood_generalization_gap / temporal_holdout_delta /
> repo_holdout_metric / language_holdout_metric /
> model_family_holdout_metric / adversarial_robustness_score /
> worst_group_metric / cvar_tail_metric / per_cell_denominator /
> temporal_split_integrity / no_retuning_proof_metric /
> citation_validity / stale_evidencecore_rejection_rate metrics。
> B11 aggregate 仅带 public model-family means + repo slice list +
> sanitized failure slices，但 NO per-record、per-time-index、
> per-repo-per-language cell、model_family x repo matrix、
> adversarial holdout outcome、temporal holdout outcome；R15 / R20 /
> R26 repo locks 是 synthetic / static snapshots，无真实 commit
> chronology 或 time axis。任何从中计算的 B18 OOD / temporal
> metric 都是 fabrication。Synthetic fixture 仅验证 split axes、
> metric names、hard gates 与 required inputs 是否正确连接；它
> 不呈现 synthetic metric values 作为经验性 B18 OOD / temporal
> 结果。Report 暴露 `ood_temporal_evaluation_performed=false`、
> `metrics_evaluated=false`、`policy_search_performed=false`、
> `quality_strategy_tuned=false`、
> `real_ood_temporal_supported=false`、
> `no_fake_ood_metrics_from_aggregate_means=true`，使读者无法将
> skeleton 误读为经验性 B18 OOD / temporal 结果。

## Preregistration declaration

下列 artifacts、split axes、required per-record inputs、metric
registry、hard gates、experimental structure 与 predeclared
success / partial / failure criteria 在任何 B18 经验性 OOD /
temporal evaluation 之前 **FROZEN**。在 B18 经验性 OOD / temporal
runs 开始后，不允许 retuning split axes、no-retuning protocol、
metric registry、hard gates 或 success criteria。任何 post-hoc
分析必须标注为 exploratory 并要求独立的 validation round。

### Frozen artifacts

- `b11_prospective_matrix_aggregate`（B11 prospective matrix
  aggregate report）——referenced，不修改；**aggregate-only carry-
  forward**，not promotion evidence，not quality proof，not OOD /
  temporal proof
- `r15_repos_lock`（R15 repos.lock.jsonl）——referenced，不修改；
  **metadata-only carry-forward**（repo counts、language metadata
  availability）；synthetic static snapshot，not temporal proof
- `r20_auto_wide_repos_lock`（R20 repos.lock.jsonl）——referenced，
  不修改；**metadata-only carry-forward**；synthetic static snapshot
- `r26_auto_stress_repos_lock`（R26 repos.lock.jsonl）——referenced，
  不修改；**metadata-only carry-forward**；synthetic static snapshot
- B18 algorithm spec 自身
  （`artifacts/b18_ood_temporal_evaluation/b18_ood_temporal_evaluation.algorithm.json`）
  ——在任何 OOD / temporal evaluation 之前 frozen；stable sha256

## Generalization-only objective (FROZEN)

产出 **frozen、preregistered 的 OOD / temporal evaluation**，在
**no-retuning protocol** 下跨五个 frozen split axes，使 in-
distribution average 不会被误读为 OOD / temporal generalization。
B18 在本 skeleton 中不执行真正的 OOD / temporal evaluation，不
> search policy，不 tune quality strategy，不改 EvidenceCore，不
> promote default，不改 retrieval policy，也不声称任何 retrieval
> variant 改进 downstream agent。

## Split axes (FROZEN)

Split axes 是 B18 evaluation 必须报告的 OOD / temporal axes 闭集。
每个 axis 有 FROZEN holdout 定义；省略任何 axis 的 B18 evaluation
都是不完整的。

- `temporal_split`——按时间 / commit-chronology 的 holdout（later
  commits 从 earlier commits 中 holdout，per repo）；R15 / R20 /
  R26 repo locks 仅带单一 static snapshot commit label（如
  `r15-snapshot`），NOT 真实 chronological ordering
- `repo_split`——leave-one-repo-out holdout（一个 repo 从其余
  holdout）；B11 aggregate 仅带 sanitized repo slice list，NOT
  per-repo outcome cells
- `language_split`——leave-one-language-out holdout（一个 primary
  language 从其余 holdout）；B11 aggregate 无 per-language cells
- `model_family_split`——leave-one-model-family-out holdout（一个
  model family 从其余 holdout）；B11 aggregate 仅报告 per-model-
  family means，NOT model_family x repo matrix
- `adversarial_split`——adversarial holdout（stress-category
  outcomes 从 in-distribution outcomes holdout）；R20 / R26
  manifests 带 stress category availability，NOT adversarial
  holdout outcomes

## No-retuning protocol (FROZEN)

No-retuning protocol 在任何 B18 经验性 OOD / temporal evaluation
之前 FROZEN：

- `no_retuning_protocol = true`
- `no_policy_search = true`（`policy_search_performed=false`）
- `no_quality_strategy_tuning = true`（`quality_strategy_tuned=false`）
- `no_retrieval_policy_change = true`（`retrieval_policy_changed=false`）
- `no_evidencecore_semantics_change = true`
  （`evidencecore_semantics_changed=false`）
- `no_default_change = true`（`default_should_change=false`）
- `no_promotion = true`（`promotion_ready=false`）

任何 holdout split 上的 metric 都不得反馈到 task screen、no-
retuning protocol、retrieval policy 或 EvidenceCore semantics。

## Metric registry (FROZEN)

当真实 per-record OOD / temporal inputs 可用时 B18 将计算的 metric
NAMES。Skeleton 定义它们并验证 hard gates，但不从 B11 aggregate
means 或 R15 / R20 / R26 repo locks 计算伪造的 metric values。

- `ood_generalization_gap`
- `temporal_holdout_delta`
- `repo_holdout_metric`
- `language_holdout_metric`
- `model_family_holdout_metric`
- `adversarial_robustness_score`
- `worst_group_metric`
- `cvar_tail_metric`
- `per_cell_denominator`
- `temporal_split_integrity`
- `no_retuning_proof_metric`
- `citation_validity`
- `stale_evidencecore_rejection_rate`

每个 metric 都需要 per-record OOD / temporal inputs（per-record
records、per-record time index、per-record commit chronology、per-
record repo / language / model_family axes、per-record task
category、per-record adversarial holdout membership、per-record
temporal holdout membership、per-record outcome label、per-record
citation validity、per-record stale rejection、per-record
EvidenceCore rejection、per-record randomized run order proof、
per-record no-retuning proof、shared frozen evaluation protocol
manifest）；没有一个能从 B11 aggregate means 或 R15 / R20 / R26
repo locks 计算。

## Hard gates (FROZEN)

下列 hard gates 在任何 B18 OOD / temporal evaluation 之前 FROZEN。
任何 split axis 或 evaluation run 若未通过任何 gate 都会被拒绝，
无论其 aggregate OOD / temporal metrics 如何。

- **per_record_data_gate**：没有 per-record outcome records，B18
  OOD / temporal evaluation 无法完成。Skeleton 不评估此 gate；仅
  定义并报告当前状态。
- **time_axis_gate**：每个 per-record outcome 必须带真实 time
  index（非单一 static snapshot commit label）。Skeleton 不评估
  此 gate；仅定义。
- **commit_chronology_gate**：每个 repo 必须带真实 commit
  chronology（commits 的 chronological ordering，非单一
  snapshot）。R15 / R20 / R26 repo locks 不满足此 gate（单一
  static snapshot commit label）。Skeleton 不评估此 gate；仅定义。
- **no_retuning_gate**：每个 B18 evaluation run 必须带 no-retuning
  proof（无 policy search、无 quality strategy tuning、无 retrieval
  policy change、无 EvidenceCore semantics change）。Skeleton 不
  评估此 gate；仅定义。
- **adversarial_holdout_gate**：每个 B18 evaluation 必须报告
  adversarial holdout outcomes per axis。Skeleton 不评估此 gate；
  仅定义。
- **temporal_holdout_gate**：每个 B18 evaluation 必须报告 temporal
  holdout outcomes per axis。Skeleton 不评估此 gate；仅定义。
- **evidencecore_materialization_gate**：每个 per-record outcome
  必须通过 EvidenceCore materialize 且 citation-valid；任何 B18
  path 不得绕过 EvidenceCore。Skeleton 不评估此 gate；仅定义。
- **stale_citation_gate**：stale 与 EvidenceCore-rejected
  candidates 必须在每个 axis 上被拒绝；citation validity 必须
  为 `1.0`。Skeleton 不评估此 gate；仅定义。
- **privacy_gate**：`aggregate_only_public_artifact=true`；no raw
  records、task IDs、repo IDs、candidate IDs、paths、file paths、
  spans、snippets、prompts、responses、diffs、patches、test
  execution results、solve labels、agent event logs、per-record
  records、time indices、commit chronology、outcome labels、gold
  spans、private labels、provider keys、base URLs、API keys/
  secrets/tokens、content SHAs、digests、line ranges in any
  public artifact；skeleton 中 `new_provider_calls=0`。
- **promotion_false_gate**：`promotion_ready=false`、
  `default_should_change=false`、
  `evidencecore_semantics_changed=false`、
  `retrieval_policy_changed=false`、
  `backend_quality_promoted=false`、
  `stage_is_ood_temporal_evaluation=true`、
  `ood_temporal_evaluation_performed=false`、
  `metrics_evaluated=false`、`policy_search_performed=false`、
  `quality_strategy_tuned=false`、
  `real_ood_temporal_supported=false` 始终存在，使 skeleton /
  stub / no-go report 无法被误读为 promoted retrieval variant 或
  B18 OOD / temporal 结果。

## Split protocol (FROZEN)

真实 B18 将 per-record inputs 分为 **task-screen split** 与
**fresh-validation split**，按 `(repo, language, model_family,
time)` stratify。Split protocol 为
`stratified_by_repo_language_model_family_time`，
`task_screen_fraction=0.50`，`fresh_validation_fraction=0.50`。
Fresh-validation split 被 holdout 并仅报告一次
（`fresh_validation_split_reported_once=true`）。Fresh-validation
split 上的任何 metric 都不得反馈到 task screen 或 no-retuning
protocol。

## Worst-group reporting

B18 报告 `{repo, language, model_family, time,
adversarial_category}` groups 上的 worst-group metrics，加上
`CVaR_20%` tail average（最差 20% 的 group metrics）。CVaR tail
fraction 为 `cvar_alpha=0.20`（frozen）。最小 per-cell
denominator 为 `min_denominator_per_cell=30`；低于此 denominator
的 cells 被抑制并报告为 `insufficient_data`。

## Privacy / publication gates

Public artifacts 必须 aggregate-only。B18 evaluator 强制：

- **no** raw records、task IDs、repo IDs、candidate IDs、paths、
  file paths、spans、snippets、prompts、responses、diffs、patches、
  test execution results、solve labels、agent event logs、per-
  record records、time indices、commit chronology、outcome labels、
  gold spans、private labels、provider keys、base URLs、API keys/
  secrets/tokens、content SHAs、digests、line ranges in any public
  artifact；
- **no** raw filesystem path strings、64-char hex digests、http(s)
  URLs 或 credential assignments 作为 values；
- `aggregate_only_public_artifact=true`；
- `new_provider_calls=0`（skeleton；无 live LLM calls 且无 live
  OOD / temporal evaluation）；
- `forbidden_public_key_scan_clean=true`。

Public no-go screen 同时使用 B18 evaluator 自身的
`_recursive_key_scan`（更严格的 forbidden-key 列表，包含
`file_path`、`gold`、`commit`、`commit_chronology`、`span`、
`raw_record` 等）与 `b6_lite_interpretable_policy_search._walk_forbidden`
（B11 / B12 / B13 / B14 / B15 / B16 / B17 public screens 共用的
public-output scan）。

## Predeclared success / partial / failure criteria

下列 criteria 在任何 B18 经验性 OOD / temporal evaluation 之前
FROZEN（`PREDECLARED_CRITERIA`）：

| Outcome | Criterion |
| --- | --- |
| **Success** | 每个 split axis 报告的 per-cell denominator 高于 frozen minimum，OOD generalization gap 在 frozen tolerance 内，temporal holdout delta 在 frozen tolerance 内，worst-group metric 满足 frozen minimum，no-retuning proof 成立，citation validity 为 `1.0`，且每个 hard gate 在 fresh-validation split 上通过。 |
| **Partial** | 部分 split axes 报告足够的 per-cell denominator 但非全部；或一个 axis 在 OOD / temporal tolerances 内但另一个不在；或 no-retuning proof 成立但 adversarial / temporal holdout outcomes 不完整。 |
| **Failure** | 没有 split axis 在 fresh-validation split 上报告足够的 per-cell denominator，或任何 hard gate 失败（per-record data、time axis、commit chronology、no-retuning、adversarial holdout、temporal holdout、EvidenceCore materialization、stale / citation、privacy、promotion false）。 |

Frozen numeric gates：

- `ood_generalization_gap_maximum = 0.10`
- `temporal_holdout_delta_tolerance = 0.05`
- `worst_group_metric_minimum = 0.50`
- `citation_validity_required = 1.0`
- `stale_evidencecore_rejection_required = true`
- `no_default_expansion_required = true`
- `evidencecore_materialization_required = true`
- `cvar_alpha = 0.20`
- `min_denominator_per_cell = 30`
- `task_screen_fraction = 0.50`
- `fresh_validation_fraction = 0.50`
- `fresh_validation_split_reported_once = true`
- `no_retuning_protocol = true`
- `no_policy_search = true`
- `no_quality_strategy_tuning = true`
- `no_retrieval_policy_change = true`
- `no_evidencecore_semantics_change = true`
- `no_default_change = true`
- `no_promotion = true`

B18 verdict framework emit 之一：

- `success`（每个 split axis 报告足够的 per-cell denominator，OOD
  / temporal tolerances 满足，worst-group minimum 满足，no-retuning
  proof 成立，所有 gates 在 fresh-validation split 上通过）
- `failure`（没有 axis 报告足够的 per-cell denominator，或任何
  hard gate 失败）
- `partial`（部分 axes 报告足够的 denominator，非全部；或 no-
  retuning proof 成立但 holdout outcomes 不完整）
- `insufficient_data`（synthetic fixture，或 per-record inputs 太
  少）
- `not_implemented`（`--input` stub，真实 B18 OOD / temporal
  evaluation 延后）

Skeleton 仅 emit `insufficient_data`（synthetic fixture）或
`not_implemented`（ci_ephemeral_records stub）；`success` /
`failure` / `partial` 不被本 skeleton emit。任何未来真实 B18
经验路径若要 emit 它们都需要独立的 preregistration，其精确 flag
schema 是 future work，不存在于本 skeleton。本 commit 保持
`ood_temporal_evaluation_performed=false`、
`metrics_evaluated=false`、`policy_search_performed=false`、
`quality_strategy_tuned=false`、
`real_ood_temporal_supported=false` 严格为 false。

## Required per-record inputs (real-B18 data contract)

真实 B18 OOD / temporal evaluation 需要下列 per-record 全部。若任
一缺失，真实 B18 无法运行，skeleton emit
`insufficient_data` / `not_implemented`。

- `per_record_record`
- `per_record_time_index`
- `per_record_commit_chronology`
- `per_record_repo_axis`
- `per_record_language_axis`
- `per_record_model_family_axis`
- `per_record_task_category`
- `per_record_adversarial_holdout_membership`
- `per_record_temporal_holdout_membership`
- `per_record_outcome_label`
- `per_record_citation_validity`
- `per_record_stale_rejection`
- `per_record_evidencecore_rejection`
- `per_record_randomized_run_order_proof`
- `per_record_no_retuning_proof`
- `shared_frozen_evaluation_protocol_manifest`

## 现有 B11 / R15 / R20 / R26 aggregate carry-forward

现有 public artifacts 是 **aggregate-only / metadata-only carry-
forward**，not OOD / temporal proof 且 not promotion evidence：

- B11 prospective matrix aggregate
  （`artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`）：
  public model-family means + sanitized repo slice list +
  sanitized failure slices；`promotion_ready=false`；
  `aggregate_only_public_artifact=true`；NO per-record records、NO
  time axis、NO commit chronology、NO per-repo-per-language cells、
  NO model_family x repo matrix、NO adversarial holdout outcomes、
  NO temporal holdout outcomes
- R15 repos.lock.jsonl（`fixtures/r15/repos.lock.jsonl`）：repo
  count + primary language metadata；单一 static snapshot commit
  label（`r15-snapshot`）；NO commit chronology、NO time axis
- R20 repos.lock.jsonl
  （`fixtures/r20_auto_wide/repos.lock.jsonl`）：repo count +
  primary language metadata + stress category availability（来自
  `dataset_manifest.json`）；单一 static snapshot commit label
  （`r20-snapshot`）；NO commit chronology、NO time axis
- R26 repos.lock.jsonl
  （`fixtures/r26_auto_stress/repos.lock.jsonl`）：repo count +
  primary language metadata + stress category availability（来自
  `dataset_manifest.json`）；单一 static snapshot commit label
  （`r26-snapshot`）；NO commit chronology、NO time axis

这些 artifacts 仅为 pre-B18 signals。它们不含 per-record OOD /
temporal inputs，不含真实 time axis 或 commit chronology，不含
per-repo-per-language cells 或 model_family x repo matrix。它们
作为 **aggregate-only / metadata-only** carry-forward，而非 OOD /
temporal proof。

## Missing inputs that block real B18

Bounded public-aggregate no-go screen 枚举了从 public aggregates
阻塞真实 B18 的具体 missing inputs：

- `no_per_record_records`
- `no_time_axis`
- `no_commit_chronology`
- `no_per_repo_per_language_cells_in_public_b11`
- `no_model_family_x_repo_matrix`
- `no_adversarial_holdout_outcomes`
- `no_temporal_holdout_outcomes`

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
retrieval_policy_changed=false
backend_quality_promoted=false
stage_is_ood_temporal_evaluation=true (B18 stage IS OOD / temporal evaluation)
ood_temporal_evaluation_performed=false (skeleton performs no OOD / temporal evaluation)
metrics_evaluated=false (skeleton; no fake OOD / temporal metrics from aggregate means)
policy_search_performed=false (no-retuning protocol)
quality_strategy_tuned=false (no-retuning protocol)
real_ood_temporal_supported=false
new_provider_calls=0 (skeleton; no live LLM calls)
no_fake_ood_metrics_from_aggregate_means=true
aggregate_only_public_artifact=true
```

## What B18 does NOT prove

- B18 **不**执行真正的 OOD / temporal evaluation。
- B18 **不**replay per-record outcomes。
- B18 **不**构造真实 temporal / commit-chronology split。
- B18 **不**构造 adversarial holdout。
- B18 **不**计算 per-repo / per-language / per-model-family cells。
- B18 **不**从 B11 aggregate means 或 R15 / R20 / R26 repo locks
  计算 ood_generalization_gap / temporal_holdout_delta /
  repo_holdout_metric / language_holdout_metric /
  model_family_holdout_metric / adversarial_robustness_score /
  worst_group_metric / cvar_tail_metric / per_cell_denominator /
  temporal_split_integrity / no_retuning_proof_metric /
  citation_validity / stale_evidencecore_rejection_rate metrics。
- B18 **不**search policy。
- B18 **不**tune quality strategy。
- B18 **不**promote 任何 retrieval variant。
- B18 **不**改变任何 defaults。
- B18 **不**改变 retrieval policy。
- B18 **不**改变 `EvidenceCore` semantics。
- B18 **不**声称任何 retrieval variant 改进 downstream agent。
- B18 结果仅为 research candidates；一个 B18-frozen retrieval
  candidate 不是 promoted retrieval variant，也不是新的 default，
  除非通过标准 promotion 流程单独 promote。
- B18 的 `--input` path 是 stub（`verdict="not_implemented"`）；
  完整 per-record OOD / temporal evaluation 延后到后续 task。
- 现有 B11 / R15 / R20 / R26 aggregates **不是** OOD / temporal
  proof；它们是 aggregate-only / metadata-only carry-forward。

## Self-test (read-only) 与 explicit artifact regeneration

```bash
python3 eval/b18_ood_temporal_evaluation.py --self-test
python3 eval/b18_ood_temporal_evaluation.py --regenerate-artifacts
python3 eval/b18_ood_temporal_evaluation.py --self-test
python3 eval/b18_ood_temporal_evaluation.py \
    --public-screen --out artifacts/b18_ood_temporal_evaluation/b18_public_ood_temporal_screen_report.json
```

`eval/b18_ood_temporal_evaluation.py --self-test` 运行是 **read-
only**：它针对 synthetic fixture（definitions-only；无 per-record
OOD / temporal inputs，无 computed metric values）验证 split axes、
required per-record inputs、metric registry、hard gates 与
experimental structure，并将 in-memory expected algorithm spec +
report 与 on-disk artifacts 对比，**在 drift 时失败**。它不修改
checked-in artifacts。它不在 stdout 中 emit raw spec sha256
（mirror B17；仅 boolean `algorithm_spec_sha256_matched` /
`algorithm_spec_sha256_stable` flags 被暴露）。它 emit
`stage_is_ood_temporal_evaluation=true`、
`ood_temporal_evaluation_performed=false`、
`metrics_evaluated=false`、`policy_search_performed=false`、
`quality_strategy_tuned=false`、
`real_ood_temporal_supported=false`、`new_provider_calls=0`、
`no_fake_ood_metrics_from_aggregate_means=true`，使 synthetic-
fixture report 明确 NOT 经验性 B18 OOD / temporal 结果。

Read-only self-test 运行这些 checks：

1. `forbidden_scan`——forbidden public keys/values scan（覆盖
   task-spec 列表：raw records、task_id、path、file_path、span、
   snippet、prompt、response、gold、label、content_sha、
   provider_key、api_key）
2. `spec_hash_stable`——algorithm spec sha256 稳定性
3. `split_axes_closed`——5 个 frozen axes；no-retuning protocol
   frozen
4. `required_per_record_inputs`——required inputs（real-B18 data
   contract）
5. `missing_inputs_for_real_b18`——task spec 的 7 个 frozen gaps 存在
6. `metric_registry`——13 个 metric names 定义；无 aggregate-mean
   metrics
7. `hard_gates_defined`——per-record data / time axis / commit
   chronology / no-retuning / adversarial holdout / temporal holdout
   / EvidenceCore materialization / stale-citation / privacy /
   promotion-false gates 定义
8. `experimental_structure_frozen`——4 个 frozen stages；无 feedback
9. `no_fake_ood_metrics_from_aggregate_means`——synthetic fixture
   无 per-record OOD / temporal inputs 且无 metric values
10. `input_stub_not_implemented`——`--input` stub 返回
    `not_implemented`
11. `reference_artifacts_pinned`——B11 aggregate + R15 / R20 / R26
    repo locks 在磁盘上存在
12. `public_screen_no_go`——bounded public no-go screen emit
    `no_go_public_aggregate_only` 且无伪造 metrics
13. `public_screen_optional_artifacts_absent`——缺失的 R15 / R20 /
    R26 artifacts 被报告为 `not_present` 而非失败
14. `artifacts_match_in_memory`——read-only drift check：in-memory
    expected spec + report 与 on-disk artifacts 匹配

`python3 eval/b18_ood_temporal_evaluation.py --regenerate-artifacts`
是唯一修改 checked-in artifacts 的 path：它从当前 build functions
（re）写入 on-disk algorithm spec + synthetic-fixture report +
canonical public no-go screen report。修改后，重新运行 `--self-test`
确认 on-disk artifacts 现在与 in-memory expected objects 匹配（无
drift）。

`--input` path 是 non-canonical stub path：它要求显式 `--out`
destination，并拒绝写入 `artifacts/b18_ood_temporal_evaluation/`
内的任何 path（canonical report、algorithm spec 或 public no-go
screen report）。它可以写入 temporary stub report 用于开发，但
不修改 checked-in B18 artifacts。

`--public-screen --out <path>` path 从当前 public artifacts（B11
aggregate + 可选 R15 / R20 / R26 repo locks 与 manifests）运行
bounded public-aggregate no-go screen 并写入显式 `--out` path。若
`--out` 缺失，canonical public screen artifact 仅在从
`--regenerate-artifacts` 调用时才被写入；否则非 self-test 调用
要求 `--out` 以避免意外 checked-in mutation。

`--public-screen` self-test（通过 `public_screen_no_go` 与
`public_screen_optional_artifacts_absent` self-test checks）针对
真实 on-disk B11 + R15 + R20 + R26 public artifacts 验证 bounded
public no-go screen。它 emit
`verdict=no_go_public_aggregate_only`（或
`public_aggregate_carry_forward_only`），带
`ood_temporal_evaluation_performed=false`、
`metrics_evaluated=false`、`policy_search_performed=false`、
`quality_strategy_tuned=false`、
`real_ood_temporal_supported=false`、
`full_b18_ood_temporal_evaluation_possible_from_public_artifacts=false`。

## Artifacts

- `artifacts/b18_ood_temporal_evaluation/b18_ood_temporal_evaluation.algorithm.json`
  （frozen spec；deterministic，stable sha256；仅通过
  `--regenerate-artifacts` 重新生成）
- `artifacts/b18_ood_temporal_evaluation/b18_ood_temporal_evaluation_report.json`
  （synthetic-fixture self-test report，verdict
  `insufficient_data`；
  `ood_temporal_evaluation_performed=false`、
  `metrics_evaluated=false`、`policy_search_performed=false`、
  `quality_strategy_tuned=false`、
  `real_ood_temporal_supported=false`、
  `stage_is_ood_temporal_evaluation=true`、
  `no_fake_ood_metrics_from_aggregate_means=true`；
  无经验性 per-record metric values）
- `artifacts/b18_ood_temporal_evaluation/b18_public_ood_temporal_screen_report.json`
  （bounded public-aggregate no-go screen report；
  `verdict=no_go_public_aggregate_only`（或
  `public_aggregate_carry_forward_only`）；
  `full_b18_ood_temporal_evaluation_possible_from_public_artifacts=false`；
  carry forward B11 `promotion_ready=false`、
  `aggregate_only_public_artifact=true`，以及 per-record / time /
  cell / matrix / holdout axes 的缺失；carry forward R15 / R20 /
  R26 repo counts、language metadata availability、stress category
  availability；aggregate-only / metadata-only，无 raw records、
  paths、prompts、responses、snippets、diffs、patches、test
  results、task IDs、repo IDs、content SHAs 或 commit chronology）

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B18 plan document（本文件）
- B18 evaluator skeleton（`eval/b18_ood_temporal_evaluation.py`）
  + read-only `--self-test`（将 in-memory expected artifacts 与
  on-disk artifacts 对比，在 drift 时失败）+ explicit
  `--regenerate-artifacts` mutating path + `--public-screen --out`
  bounded public no-go screen path
- B18 frozen algorithm spec + synthetic-fixture report artifacts
- B18 bounded public-aggregate no-go screen +
  `artifacts/b18_ood_temporal_evaluation/b18_public_ood_temporal_screen_report.json`
  （读取已发布的 B11 matrix + 可选 R15 / R20 / R26 repo locks 与
  manifests；emit `no_go_public_aggregate_only` /
  `public_aggregate_carry_forward_only`；从不声称 OOD / temporal
  evaluation，从不从 aggregate means 计算 OOD / temporal metric，
  从不 promote retrieval variant，从不改变 retrieval policy，从
  不 declare winner）

### Needs prospective per-record data collection

- B18 真实 OOD / temporal evaluation 需要 prospective per-record
  outcome records，带真实 time axis 与 commit chronology per repo，
  加上 per-repo / per-language / per-model-family cells 与
  adversarial 与 temporal holdout memberships，在 frozen no-retuning
  protocol 下，加上 per-record citation validity、stale rejection、
  EvidenceCore rejection、randomized run order proof、no-retuning
  proof，以及 shared frozen evaluation protocol manifest。若这些
  records 尚未产生，B18 emit `insufficient_data` /
  `not_implemented`。

### Needs user review

- Results interpretation
- 决定是否进行真实 B18 经验性 OOD / temporal evaluation path（需要
  独立 preregistration；必须包含带真实 time axis 与 commit
  chronology 的 prospective per-record data collection）
- 决定是否从 minimum viable split axis set 扩展到更大 set（需要
  独立 preregistration）

## Next steps after B18

- **B18 success**（未来真实 B18 path）：每个 split axis 报告足够
  的 per-cell denominator，OOD / temporal tolerances 满足，worst-
  group minimum 满足，no-retuning proof 成立，所有 hard gates 通
  过。通过标准 promotion 流程推进；B18 success 不 auto-promote。
- **B18 failure**（未来真实 B18 path）：没有 split axis 报告足够
  的 per-cell denominator。当前 retrieval stack 继续；无 retrieval
  variant 被 promote。
- **B18 partial**（未来真实 B18 path）：部分 axes 报告足够的
  denominator，非全部。调查 axis-conditional candidate-quality
  policies；可能在独立 B18B round 中扩展 axis set（需要独立
  preregistration）。
- **B18 skeleton / no-go**（本 commit）：bounded public-aggregate
  no-go screen 确认真实 B18 无法仅从 public aggregates 执行——
  public artifacts 缺少 per-record records、time axis、commit
  chronology、per-repo-per-language cells、model_family x repo
  matrix、adversarial holdout outcomes 与 temporal holdout
  outcomes。真实 B18 需要带真实 time axis 与 commit chronology 的
  prospective per-record data collection。
