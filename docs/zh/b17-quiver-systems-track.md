# B17 QuIVer Systems Track

Date: 2026-06-18

B17 是 **QuIVer systems track** 阶段。目标是产出一个 **frozen、
preregistered 的 backend bakeoff**，在 **frozen candidate-quality
policy** 下对比 ANN backend candidates 的 backend systems metrics
（latency、memory、build time、update cost、index size），使 backend
quality 不会在对比 latency / memory / build / update / index-size
数据时被静默放宽。

B17 是一个 **bounded planning / diagnostic 阶段**，**不是** QuIVer
production backend，**不是** ANN quality promotion，**不是** default
change，**不是** EvidenceCore semantics change。当前 skeleton 不执行任何
real ANN backend bakeoff、不执行 HNSW run、不执行 QuIVer/Vamana graph
run、不产出 candidate-set equivalence matrix across backends、不产出
update-cost / build-time / index-size benchmark、不执行 stale/citation
cross-backend validation。frozen preregistration
（`eval/b17_quiver_systems_track.py`）定义 backend set、candidate-set
equivalence constraints、metric registry、hard gates 与 experimental
structure（no-backend-bakeoff feasibility → frozen candidate-quality
policy → ANN backend bakeoff → candidate-set equivalence validation）；
bounded public-systems diagnostic carry-forward / no-go screen
（`eval/b17_public_systems_diagnostic_screen.py`）读取已发布的 R33
readiness + R34/R36 anchor-proto + real-provider P3/P4 quiver diagnostics
+ 可选 R24 QuIVer/TDB/dense probe，并发出 `no_go_quiver_graph_missing`
（或 `diagnostic_carry_forward_only`）verdict。

> **Important claim boundary.** B17 **是** quiver-systems-track
> *stage*（`stage_is_quiver_systems_track=true`），但当前 skeleton 不执行
> ANN backend bakeoff（`ann_backend_bakeoff_performed=false`）、不验证
> candidate-set equivalence（`candidate_set_equivalence_validated=false`）、
> 不实现 QuIVer/Vamana graph（`quiver_graph_implemented=false`）、不
> promote backend quality（`backend_quality_promoted=false`）。
> synthetic-fixture / `--input` stub 报告设置 `promotion_ready=false`、
> `default_should_change=false`、
> `evidencecore_semantics_changed=false`、`retrieval_policy_changed=false`、
> `metrics_evaluated=false`、`new_provider_calls=0`，使该公共 artifact
> 不会被误读为 empirical B17 systems bakeoff 结果。此 commit 严格是
> skeleton / no-go commit：当前 flags（`ann_backend_bakeoff_performed=false`、
> `candidate_set_equivalence_validated=false`、
> `quiver_graph_implemented=false`、`backend_quality_promoted=false`）保持
> false。任何未来 real B17 empirical 路径都需要其自己的独立 preregistration；
> 该未来路径的精确 flag schema 是 future work，**不**在当前 skeleton 中。
> 本 commit 中的 B17 结果仅为 research candidates：此 skeleton / no-go commit
> 不授权 default change、不授权 retrieval-policy change、不授权 backend
> quality promotion、不授权 QuIVer graph implementation、不修改
> EvidenceCore，也不声称任何 backend 改进 downstream agent。

> **Important systems-vs-quality boundary.** systems bakeoff 是
> **systems** 对比（latency / memory / build / update / index-size），处于
> **frozen candidate-quality policy** 之下。一个 backend 在 latency 上胜出
> 但违反 candidate-set equivalence，无论其 systems 数据如何，都将被拒绝。
> frozen candidate-quality policy 是使 systems bakeoff 有意义的前置条件：没有
> 它，backend latency 对比会静默地以质量换速度。

> **CRITICAL anti-fabrication boundary.** skeleton **绝不可**从现有 R33 / R34
> / R36 / R24 diagnostics 计算伪造的 candidate_set_overlap_at_k /
> gold_retention_delta / span_f0_5_delta / primary_false_positive_delta /
> p50_latency / p95_latency / hot_memory / build_time / update_cost /
> index_size / recall_tolerance_violation_count 指标。那些 diagnostics 仅是
> BQ / flat_f32 / bq_topk_f32_rerank diagnostics；它们**不**包含 QuIVer/Vamana
> graph 实现、HNSW run 或 candidate-set equivalence matrix across backends，
> 因此任何从它们计算的 B17 systems metric 都是 fabrication。synthetic
> fixture 仅验证 backend set、candidate-set equivalence constraints、metric
> names 与 hard gates 是否正确接线；它**不**把 synthetic metric values 呈现
> 为 empirical B17 systems 结果。报告暴露
> `ann_backend_bakeoff_performed=false`、
> `candidate_set_equivalence_validated=false`、
> `quiver_graph_implemented=false`、`backend_quality_promoted=false`、
> `metrics_evaluated=false` 与 `no_fake_ann_metrics_from_diagnostics=true`，
> 使读者无法把 skeleton 误读为 empirical B17 systems bakeoff 结果。

## Preregistration declaration

以下 artifacts、backend set、candidate-set equivalence constraints、
metric registry、hard gates、experimental structure 与 predeclared
success/partial/failure criteria 在任何 B17 empirical systems bakeoff 之前
**FROZEN**。在任何 B17 empirical systems runs 开始后，不允许重新调整 backend
set、candidate-set equivalence constraints、metric registry、hard gates 或
success criteria。任何 post-hoc 分析必须标注为 exploratory 并要求独立的
validation round。

### Frozen artifacts

- `r33_quiver_readiness`（R33 BQ readiness diagnostic）— referenced、
  not modified；**diagnostic-only carry-forward**，非 promotion evidence，
  非 quality proof
- `r34_r36_quiver_anchor_proto`（R34/R36 anchor-proto diagnostic）—
  referenced、not modified；**diagnostic-only carry-forward**，非
  promotion evidence，非 quality proof
- B17 algorithm spec 本身
  （`artifacts/b17_quiver_systems_track/b17_quiver_systems_track.algorithm.json`）
  — 在任何 systems bakeoff 之前 frozen；stable sha256

## Systems-only objective (FROZEN)

产出一个 **frozen、preregistered 的 backend bakeoff**，在 **frozen
candidate-quality policy** 下对比 ANN backend candidates 的 backend systems
metrics（latency、memory、build time、update cost、index size），使 backend
quality 不会在对比时被静默放宽。B17 不 learn backend、不在当前 skeleton 中
实现 QuIVer/Vamana graph、不修改 EvidenceCore、不 promote default、不
promote backend、不修改 retrieval policy，也不声称任何 backend 改进
downstream agent。

## Candidate backends (FROZEN)

backend set 是 B17 systems bakeoff 可在 frozen candidate-quality policy 下
对比的 ANN backend candidates 的封闭集合：

- `flat_f32_reference` — reference backend（ground-truth nearest-neighbor
  search；candidate-set equivalence baseline）
- `hnsw_candidate` — HNSW candidate backend（现有 diagnostic-era
  candidate；当前任何公共 artifact 中不存在 HNSW run）
- `bq_topk_f32_rerank_candidate` — BQ top-k + f32 rerank candidate backend
  （现有 diagnostic-era candidate）
- `quiver_vamana_prototype` — QuIVer/Vamana graph backend（B17 systems-
  track 终极目标；**未实现** — `quiver_vamana_implemented=false`）
- `tdb_vector_candidate` — 可选 store/backend candidate only；**非**
  Evidence source，默认 EXCLUDED
  （`store_backend_candidate_only_never_evidence_source`）

Primary comparison backends（始终存在）：`flat_f32_reference` vs candidate
backends（`hnsw_candidate`、`bq_topk_f32_rerank_candidate`、
`quiver_vamana_prototype`）。

## Candidate-set equivalence constraints (FROZEN)

一个 candidate backend 仅在它对 reference backend（`flat_f32_reference`）
保持 candidate quality 在 frozen tolerances 之内时才被允许进入 systems
bakeoff。这些 constraints 是 FROZEN；任何 backend 若失败任一 constraint，
无论其 latency / memory / build / update / index-size 数据如何，都将被拒绝。

- `candidate_set_overlap_at_k` — overlap@K vs reference 必须在 frozen K set
  （`[10, 50, 100]`）的每个 K 上达到或超过 frozen 最小 overlap；最小
  overlap `0.90`
- `gold_retention_delta_within_tolerance` — `gold_retention_delta` vs
  reference 必须在 frozen tolerance 之内（无超出 frozen margin 的 quality
  回归）；tolerance `0.05`
- `primary_false_positive_delta_guard` —
  `primary_false_positive_delta` vs reference 不得超过 frozen guard（无
  PFP 回归）；guard `0.05`
- `span_f0_5_delta_within_tolerance` — `SpanF0.5_delta` vs reference 必须
  在 frozen tolerance 之内（无 span-quality 回归）；tolerance `0.05`
- `citation_validity_required` — `citation_validity` 对每个 backend 必须
  为 `1.0`（fail-closed citation 与 range validation）
- `stale_evidencecore_rejection_required` — stale 与 EvidenceCore-rejected
  candidates 必须被每个 backend 拒绝（无 stale leakage）
- `no_default_expansion_required` — 任何 candidate backend 未经独立
  promotion 不得扩展 default retrieval policy

## Metric registry (FROZEN)

B17 在有 real per-backend systems bakeoff inputs 时将计算的 metric NAMES。
skeleton 定义它们并验证 hard gates，但**不**从现有 R33/R34/R36/R24
diagnostics 计算伪造的 metric values。

- `candidate_set_overlap_at_k`
- `gold_retention_delta`
- `span_f0_5_delta`
- `primary_false_positive_delta`
- `p50_latency`
- `p95_latency`
- `hot_memory`
- `build_time`
- `update_cost`
- `index_size`
- `recall_tolerance_violation_count`

每个 metric 都需要 per-backend systems bakeoff inputs（index build records、
search latency records、hot memory records、index size records、update cost
records、candidate-set-at-K records、gold retention records、span F0.5
records、PFP records、citation validity records、stale rejection records、
EvidenceCore rejection records、recall tolerance violation records、
randomized run order proof、isolated index workspace proof、shared frozen
candidate-quality manifest）；**没有** metric 可从现有 R33/R34/R36/R24
diagnostics 计算。

## Hard gates (FROZEN)

以下 hard gates 在任何 B17 systems bakeoff 之前 FROZEN。任何 candidate
backend 若失败任一 gate，无论其 aggregate systems metrics 如何，都将被
拒绝。

- **quiver_graph_implementation_gate**：在 QuIVer 或 Vamana graph backend 被
  实现之前，B17 systems bakeoff 无法完成（当前
  `quiver_vamana_implemented=false`）。skeleton 不评估此 gate；它仅定义它并
  报告当前状态。
- **backend_parity_gate**：每个 backend 必须在相同的 frozen candidate-
  quality policy、相同的 shared frozen candidate-quality manifest、相同的
  randomized run order 与相同的 isolated index workspace 下运行；唯一变化
  的因素是 backend
  （`operational_parity_build_time_match_tolerance=0.20`、
  `operational_parity_update_cost_match_tolerance=0.20`）。skeleton 不评估
  此 gate；它仅定义它。
- **candidate_set_equivalence_gate**：每个 candidate backend 必须满足每个
  candidate-set equivalence constraint vs reference backend（overlap@K、
  gold_retention_delta、primary_false_positive_delta、SpanF0.5_delta、
  citation_validity、stale/EvidenceCore rejection、no default expansion）。
  skeleton 不评估此 gate；它仅定义它。
- **evidencecore_materialization_gate**：每个 backend 的输出必须通过
  EvidenceCore materialize 并具有 citation-valid evidence；任何 backend 不得
  绕过 EvidenceCore。skeleton 不评估此 gate；它仅定义它。
- **stale_citation_gate**：stale 与 EvidenceCore-rejected candidates 必须被
  每个 backend 拒绝；每个 backend 的 citation validity 必须为 `1.0`。
  skeleton 不评估此 gate；它仅定义它。
- **privacy_gate**：`aggregate_only_public_artifact=true`；公共 artifact 中
  不得有 raw records、task IDs、repo IDs、candidate IDs、paths、spans、
  snippets、prompts、responses、diffs、patches、test execution results、
  solve labels、agent event logs、backend event logs、index build records、
  search latency records、hot memory records、index size records、gold
  spans、private labels、provider keys、base URLs、API keys/secrets/tokens、
  content SHAs、digests 或 line ranges；skeleton 中 `new_provider_calls=0`。
- **promotion_false_gate**：`promotion_ready=false`、
  `default_should_change=false`、
  `evidencecore_semantics_changed=false`、`retrieval_policy_changed=false`、
  `backend_quality_promoted=false`、`quiver_graph_implemented=false`、
  `ann_backend_bakeoff_performed=false`、
  `candidate_set_equivalence_validated=false`、`metrics_evaluated=false`
  始终存在，使 skeleton / stub / no-go 报告不会被误读为 promoted backend
  或 QuIVer systems bakeoff 结果。

## Split protocol (FROZEN)

Real B17 把 per-backend inputs 划分为 **task-screen split** 与
**fresh-validation split**，按 `(repo, model_family, language)` stratified。
split protocol 为 `stratified_by_repo_model_family_language`，
`task_screen_fraction=0.50` 与 `fresh_validation_fraction=0.50`。
fresh-validation split 被 held out 并 reported once
（`fresh_validation_split_reported_once=true`）。fresh-validation split 上的
任何 metric 都不得回流到 task screen 或 frozen candidate-quality policy。

## Worst-group reporting

B17 报告 `{repo, model_family, language}` groups 上的 worst-group metrics，
加上 `CVaR_20%` tail average（最差 20% 的 group metrics）。CVaR tail
fraction 为 `cvar_alpha=0.20`（frozen）。

## Privacy / publication gates

公共 artifacts 必须为 aggregate-only。B17 evaluator 强制：

- 公共 artifact 中**不得**有 raw records、task IDs、repo IDs、candidate
  IDs、paths、spans、snippets、prompts、responses、diffs、patches、test
  execution results、solve labels、agent event logs、backend event logs、
  index build records、search latency records、hot memory records、index size
  records、gold spans、private labels、provider keys、base URLs、API
  keys/secrets/tokens、content SHAs、digests 或 line ranges；
- **不得**有 raw filesystem path strings、64-char hex digests、http(s) URLs
  或 credential assignments 作为值；
- `aggregate_only_public_artifact=true`；
- `new_provider_calls=0`（skeleton；无 live LLM calls 且无 live ANN backend
  bakeoff）；
- `forbidden_public_key_scan_clean=true`。

## Predeclared success / partial / failure criteria

以下 criteria 在任何 B17 empirical systems bakeoff 之前 FROZEN
（`PREDECLARED_CRITERIA`）：

| Outcome | Criterion |
| --- | --- |
| **Success** | 每个 candidate backend 在 fresh-validation split 上满足每个 candidate-set equivalence constraint vs reference backend，QuIVer/Vamana graph backend 已实现，每个 backend 报告 per-backend latency / memory / build / update / index-size 处于 operational-parity gates 之内，并且 cost/systems metrics per backend 报告。 |
| **Partial** | 部分 candidate backends 满足 candidate-set equivalence 但不是全部；或一个 backend 在 operational-parity gates 之内但另一个不在；或 QuIVer/Vamana graph backend 已实现但 candidate-set equivalence validation 未完成。 |
| **Failure** | 没有 candidate backend 在 fresh-validation split 上满足 candidate-set equivalence，或任何 hard gate 失败（quiver graph implementation、backend parity、candidate-set equivalence、EvidenceCore materialization、stale/citation、privacy、promotion false）。 |

Frozen numeric gates：

- `candidate_set_overlap_at_k_minimum = 0.90`
- `gold_retention_delta_tolerance = 0.05`
- `primary_false_positive_delta_guard = 0.05`
- `span_f0_5_delta_tolerance = 0.05`
- `citation_validity_required = 1.0`
- `stale_evidencecore_rejection_required = true`
- `no_default_expansion_required = true`
- `equivalence_ks = [10, 50, 100]`
- `cvar_alpha = 0.20`
- `task_screen_fraction = 0.50`
- `fresh_validation_fraction = 0.50`
- `min_denominator_per_backend_repo_cell = 30`
- `operational_parity_build_time_match_tolerance = 0.20`
- `operational_parity_update_cost_match_tolerance = 0.20`
- `operational_parity_same_frozen_candidate_quality_policy = true`
- `operational_parity_no_default_expansion = true`
- `operational_parity_no_evidencecore_semantics_change = true`
- `systems_metrics_reported_per_backend = true`

B17 verdict 框架发出以下之一：

- `success`（每个 candidate backend 满足 candidate-set equivalence，
  QuIVer/Vamana graph 已实现，所有 gates 在 fresh-validation split 上通过）
- `failure`（没有 backend 满足 candidate-set equivalence，或任何 hard gate
  失败）
- `partial`（部分 backends 满足，不是全部；或 QuIVer/Vamana graph 已实现
  但 candidate-set equivalence 未完成）
- `insufficient_data`（synthetic fixture，或 per-backend inputs 过少）
- `not_implemented`（`--input` stub，real QuIVer systems bakeoff 延后）

skeleton 仅发出 `insufficient_data`（synthetic fixture）或
`not_implemented`（ci_ephemeral_records stub）；`success` / `failure` /
`partial` **不**由当前 skeleton 发出。任何未来 real B17 empirical 路径若
可能发出它们，需要其自己的独立 preregistration，且其精确 flag schema 是
future work，**不**在当前 skeleton 中。本 commit 严格保持
`ann_backend_bakeoff_performed=false`、
`candidate_set_equivalence_validated=false`、
`quiver_graph_implemented=false` 与 `backend_quality_promoted=false`。

## Required per-backend inputs (real-B17 data contract)

Real B17 systems bakeoff 需要以下所有 per backend。若任一缺失，real B17
无法运行，skeleton 发出 `insufficient_data` / `not_implemented`。

- `per_backend_index_build_record`
- `per_backend_search_latency_record`
- `per_backend_hot_memory_record`
- `per_backend_index_size_record`
- `per_backend_update_cost_record`
- `per_backend_candidate_set_at_k_record`
- `per_backend_gold_retention_record`
- `per_backend_span_f0_5_record`
- `per_backend_primary_false_positive_record`
- `per_backend_citation_validity_record`
- `per_backend_stale_rejection_record`
- `per_backend_evidencecore_rejection_record`
- `per_backend_recall_tolerance_violation_record`
- `per_backend_randomized_run_order_proof`
- `per_backend_isolated_index_workspace_proof`
- `shared_frozen_candidate_quality_manifest`

## Existing R33/R34/R36 diagnostic carry-forward

现有 diagnostics 是 **diagnostic-only carry-forward**，非 quality proof，
非 promotion evidence：

- R33 readiness diagnostic（`artifacts/r33/quiver_readiness.json`）：仅 BQ2/
  sign-magnitude diagnostics；`quiver_graph_implemented=false`；
  `quiver_quality_metrics_emitted=false`；
  `BQ_diagnostics_only=true`；`promotion_ready=false`
- R34/R36 anchor-proto diagnostic
  （`artifacts/r34_r36/quiver_anchor_proto.json`）：flat f32、BQ top-k + f32
  rerank、sharding layouts、anchor-seeded candidate-pool restriction；
  `quiver_mode=diagnostic_only`；
  `quiver_graph_implemented=false`；
  `quiver_default_allowed=false`；
  `quiver_supporting_channel_allowed=true`；
  `dense_or_quiver_role=candidate/supporting-only`；
  `promotion_ready=false`
- real-provider P3 quiver readiness
  （`artifacts/real_provider/p3_real_quiver_readiness.json`）：
  diagnostic-only real-provider variant；
  `quiver_graph_implemented=false`；
  `quiver_quality_metrics_emitted=false`
- real-provider P4 quiver anchor proto
  （`artifacts/real_provider/p4_real_quiver_anchor_proto.json`）：
  diagnostic-only real-provider variant；
  `quiver_mode=diagnostic_only`；
  `quiver_graph_implemented=false`
- R24 QuIVer/TDB/dense probe（`runs/r24-quiver-tdb-probe.json`）：QuIVer
  unavailable/not-implemented；TDB feature-gated metadata/chunk store
  placeholder；dense mock candidate-channel safety/quality smoke（非
  semantic quality）；`promotion_ready=false`

这些 diagnostics 仅为 pre-B17 signals。它们**不**实现 QuIVer/Vamana graph
backend、**不**包含 HNSW run、**不**包含 candidate-set equivalence matrix
across backends。它们以 **diagnostic-only** 形式 carry forward，而非
quality proof。

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
retrieval_policy_changed=false
backend_quality_promoted=false
stage_is_quiver_systems_track=true（B17 stage IS quiver systems track）
quiver_graph_implemented=false（skeleton 不实现 QuIVer 或 Vamana graph）
ann_backend_bakeoff_performed=false（skeleton 不执行 ANN backend bakeoff）
candidate_set_equivalence_validated=false（skeleton 不验证 candidate-set equivalence）
metrics_evaluated=false（skeleton；不从 diagnostics 计算伪造的 ANN metrics）
new_provider_calls=0（skeleton；无 live LLM calls）
no_fake_ann_metrics_from_diagnostics=true
aggregate_only_public_artifact=true
```

## What B17 does NOT prove

- B17 **不**实现 QuIVer 或 Vamana graph backend。
- B17 **不**运行 HNSW backend。
- B17 **不**执行 ANN backend bakeoff。
- B17 **不**验证 cross-backends 的 candidate-set equivalence。
- B17 **不**从现有 R33 / R34 / R36 / R24 diagnostics 计算
  candidate_set_overlap_at_k / gold_retention_delta / span_f0_5_delta /
  primary_false_positive_delta / p50_latency / p95_latency / hot_memory /
  build_time / update_cost / index_size /
  recall_tolerance_violation_count metrics。
- B17 **不** promote 任何 backend。
- B17 **不**改变任何 defaults。
- B17 **不**修改 retrieval policy。
- B17 **不**修改 `EvidenceCore` semantics。
- B17 **不**声称任何 backend 改进 downstream agent。
- B17 结果仅为 research candidates；一个 B17-frozen backend candidate **不**
  是 promoted backend，**不**是 new default，直至通过标准 promotion process
  单独 promoted。
- B17 的 `--input` path 是 stub（`verdict="not_implemented"`）；完整
  QuIVer systems bakeoff + candidate-set equivalence matrix 延后到 later
  task。
- 现有 R33/R34/R36/R24 diagnostics **不**是 quality proof；它们是
  diagnostic-only carry-forward。

## Self-test (read-only) and explicit artifact regeneration

```bash
python3 eval/b17_quiver_systems_track.py --self-test
python3 eval/b17_quiver_systems_track.py --regenerate-artifacts
python3 eval/b17_quiver_systems_track.py --self-test
python3 eval/b17_public_systems_diagnostic_screen.py --self-test
python3 eval/b17_public_systems_diagnostic_screen.py \
    --out artifacts/b17_quiver_systems_track/b17_public_systems_diagnostic_screen_report.json
```

`eval/b17_quiver_systems_track.py --self-test` 运行是 **read-only**：它根据
synthetic fixture（definitions-only；无 per-backend systems bakeoff inputs，
无 computed metric values）验证 backend set、candidate-set equivalence
constraints、metric registry、hard gates 与 experimental structure，并将
in-memory 期望的 algorithm spec + report 与 on-disk artifacts 对比，**drift
即失败**。它**不**修改 checked-in artifacts。它发出
`stage_is_quiver_systems_track=true`、`quiver_graph_implemented=false`、
`ann_backend_bakeoff_performed=false`、
`candidate_set_equivalence_validated=false`、
`backend_quality_promoted=false`、`metrics_evaluated=false`、
`new_provider_calls=0`、`no_fake_ann_metrics_from_diagnostics=true`，使
synthetic-fixture 报告明确**不**是 empirical B17 systems bakeoff 结果。

read-only self-test 运行以下检查：

1. `forbidden_scan` — forbidden public keys/values 扫描
2. `spec_hash_stable` — algorithm spec sha256 稳定性
3. `backend_set_closed` — reference / candidate / optional-store backends
   封闭且互斥；QuIVer/Vamana graph backend 未实现；optional store backend
   默认 excluded
4. `candidate_set_equivalence_constraints` — 7 个 frozen constraints，
   包含所需 IDs
5. `metric_registry` — 11 个 metric names；无 aggregate-mean metrics
6. `hard_gates_defined` — quiver graph implementation / backend parity /
   candidate-set equivalence / EvidenceCore materialization /
   stale-citation / privacy / promotion-false gates 已定义
7. `experimental_structure_frozen` — 4 个 frozen stages；无 feedback
8. `no_fake_ann_metrics_from_diagnostics` — synthetic fixture 无 per-backend
   systems bakeoff inputs 且无 metric values
9. `input_stub_not_implemented` — `--input` stub 返回 `not_implemented`
10. `reference_diagnostics_pinned` — R33 readiness + R34/R36 anchor-proto
    diagnostic-only carry-forward artifacts 在 disk 上存在
11. `artifacts_match_in_memory` — read-only drift 检查：in-memory 期望
    spec + report 与 on-disk artifacts 一致

`python3 eval/b17_quiver_systems_track.py --regenerate-artifacts` 是**唯一**
会修改 checked-in artifacts 的路径：它从当前 build functions（重新）写入
on-disk algorithm spec + synthetic-fixture report。修改后，重新运行
`--self-test` 以确认 on-disk artifacts 现在与 in-memory 期望对象一致（无
drift）。

`--input` path 是 non-canonical stub path：它要求显式 `--out` 目标，并拒绝
写入 `artifacts/b17_quiver_systems_track/` 内的任何路径（canonical report、
algorithm spec 或 public systems diagnostic screen report）。它可以为开发
写入临时 stub report，但**不**修改 checked-in B17 artifacts。

`eval/b17_public_systems_diagnostic_screen.py --self-test` 运行验证 bounded
public-systems diagnostic carry-forward / no-go screen，使用 synthetic 最小
R33 + R34/R36 + real-provider P3 + P4 + R24 fixture。它发出
`verdict=no_go_quiver_graph_missing`（或
`diagnostic_carry_forward_only`），其中
`quiver_graph_implemented=false`、
`ann_backend_bakeoff_performed=false`、
`candidate_set_equivalence_validated=false`、
`backend_quality_promoted=false`、`metrics_evaluated=false`、
`full_b17_systems_bakeoff_possible_from_public_artifacts=false`。

## Artifacts

- `artifacts/b17_quiver_systems_track/b17_quiver_systems_track.algorithm.json`
  （frozen spec；deterministic、stable sha256；仅通过
  `--regenerate-artifacts` 重新生成）
- `artifacts/b17_quiver_systems_track/b17_quiver_systems_track_report.json`
  （synthetic-fixture self-test report，verdict `insufficient_data`；
  `quiver_graph_implemented=false`、
  `ann_backend_bakeoff_performed=false`、
  `candidate_set_equivalence_validated=false`、
  `backend_quality_promoted=false`、
  `stage_is_quiver_systems_track=true`、
  `no_fake_ann_metrics_from_diagnostics=true`；
  无 empirical per-backend metric values）
- `artifacts/b17_quiver_systems_track/b17_public_systems_diagnostic_screen_report.json`
  （bounded public-systems diagnostic carry-forward / no-go screen 报告；
  `verdict=no_go_quiver_graph_missing`（或
  `diagnostic_carry_forward_only`）；
  `full_b17_systems_bakeoff_possible_from_public_artifacts=false`；
  carry forward R33 `quiver_graph_implemented=false` 与
  `quiver_quality_metrics_emitted=false`、R34/R36
  `quiver_mode=diagnostic_only`、real-provider P3/P4 diagnostic-only
  statuses、以及 R24 QuIVer/TDB/dense probe statuses；aggregate-only，无
  raw event traces、paths、diffs、prompts/responses、hidden tests 或 task
  IDs）

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B17 plan 文档（本文件）
- B17 evaluator skeleton（`eval/b17_quiver_systems_track.py`）+ read-only
  `--self-test`（将 in-memory 期望 artifacts 与 on-disk artifacts 对比，
  drift 即失败）+ explicit `--regenerate-artifacts` 修改路径
- B17 frozen algorithm spec + synthetic-fixture report artifacts
- B17 bounded public-systems diagnostic carry-forward / no-go screen
  （`eval/b17_public_systems_diagnostic_screen.py`）+ self-test +
  `artifacts/b17_quiver_systems_track/b17_public_systems_diagnostic_screen_report.json`
  （读取已发布的 R33 + R34/R36 + real-provider P3/P4 quiver diagnostics +
  可选 R24 probe；发出 `no_go_quiver_graph_missing` /
  `diagnostic_carry_forward_only`；从不声称 QuIVer implementation，从不
  从 diagnostics 计算 ANN metric，从不 promote backend，从不声明 winner）

### Needs QuIVer/Vamana graph backend implementation

- B17 real systems bakeoff 需要 QuIVer 或 Vamana graph backend 实现、一个
  HNSW backend run、per-backend systems bakeoff inputs（index build records、
  search latency records、hot memory records、index size records、update
  cost records、candidate-set-at-K records、gold retention records、span
  F0.5 records、PFP records、citation validity records、stale rejection
  records、EvidenceCore rejection records、recall tolerance violation
  records、randomized run order proof、isolated index workspace proof），
  以及一个 shared frozen candidate-quality manifest。若这些 records 尚未
  产出，B17 发出 `insufficient_data` / `not_implemented`。

### Needs user review

- 结果解释
- 决定是否推进到 real B17 empirical systems bakeoff 路径（需要独立
  preregistration；必须包含 QuIVer 或 Vamana graph backend 实现）
- 决定是否从 minimum viable backend set 扩展到更大的集合（需要独立
  preregistration）

## Next steps after B17

- **B17 success**（未来 real B17 路径）：每个 candidate backend 满足
  candidate-set equivalence vs reference backend，QuIVer/Vamana graph backend
  已实现，所有 hard gates 通过。通过标准 promotion process 推进；B17 success
  **不**自动 promote。
- **B17 failure**（未来 real B17 路径）：没有 candidate backend 满足
  candidate-set equivalence。当前 retrieval stack 继续；不 promote backend。
- **B17 partial**（未来 real B17 路径）：部分 backends 满足，不是全部。调查
  backend-conditional candidate-quality policies；可能在独立 B17B round 中
  扩展 backend set（需要独立 preregistration）。
- **B17 skeleton / no-go**（本 commit）：bounded public-systems diagnostic
  carry-forward / no-go screen 确认 real B17 无法仅凭公共 diagnostics 完成
  ——QuIVer/Vamana graph backend 缺失。Real B17 需要 QuIVer/Vamana graph
  backend 实现 + per-backend systems bakeoff inputs。
