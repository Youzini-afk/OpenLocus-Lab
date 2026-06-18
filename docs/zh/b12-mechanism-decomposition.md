# B12 Mechanism Decomposition

Date: 2026-06-18

B12 是继 B11（prospective blind validation）之后的 **mechanism decomposition**
阶段。目标是通过 5 个 ablation variants（A-E）和 4 个 predeclared hypotheses
（H1-H4）理解**为什么**冻结的 balanced policy
`balanced_policy_v1_benchmark_routed`（B10）有效（如果 B11 证实它泛化）。

> **重要 claim 边界。** B12 是 mechanism decomposition，**不是** promotion step。
> 即使 B12 支持一个或多个 hypotheses，`promotion_ready=false`、
> `default_should_change=false`，且 `EvidenceCore` 语义不变。B12 的结论只决定哪个
> mechanism（ambiguous routing、LLM-call reduction、P25 fallback sufficiency 或
> model-specific 行为）驱动了 balanced policy 的增益，进而指导 B13
>（distributionally robust policy search）。

## Preregistration declaration

下列 artifacts、ablation variant 定义、hypothesis support/refute criteria 均在
任何 B12 ablation runs 之前 **FROZEN**。B12 ablation runs 开始后不允许 retuning。
任何 post-hoc analysis 必须标注为 exploratory，并需要单独的 validation round。

### Frozen artifacts

- `balanced_policy_v1_benchmark_routed`（B10 frozen spec；sha256 在
  `artifacts/b10_runtime_feature_audit/balanced_policy_v1_benchmark_routed.algorithm.json`）
- `balanced_policy_v1_runtime_shadow_ambiguous_branch`（B10B shadow predicate；
  sha256 `c201eb709dc0112c2bb91db33917c6d20ea48582924821a2bda7950709e754ba`）
- `rmc_local_conservative_v0`（Conservative policy；冻结于
  `eval/b6_lite_interpretable_policy_search.py`）
- `p25.route_bucket_routed_v0`（P25 policy；冻结于 `eval/p25_bucket_policy.py`）
- B10B 10 个 predeclared acceptance gates（含
  `label_driven_ambiguous_min_denominator: 10` hard gate）
- B10B verdict 框架（`runtime_shadow_ambiguous_supported` + `support_claim` +
  `support_claim_reason`）
- 本文档中的全部 ablation variant 定义（A-E）与 hypothesis criteria（H1-H4）

## Objective

将 balanced policy 的增益机制分解为以下 4 个候选解释之一（或多个）：

> Balanced policy 的增益来自 (H1) 特定的 `ambiguous→weak_only` routing rule、
> (H2) 通用的 LLM 调用减少、(H3) P25 default action 单独即足够，还是 (H4)
> model-family-specific 行为？

## Scope

如果 P21 records 可用（每条 record 已含 per-strategy outcomes），B12 可作为纯
**replay** 完成：每个 ablation variant 通过从现有 records 中选取对应的
per-strategy outcome 即可计算。如果 P21 records 不可用，B12 需要新的 live
ablation runs（workflow_dispatch + `enable_remote_models=true`）。

### Minimum viable B12

- 与 B11 相同的 8 repos、4 model families、4 policies（因此 B12 可直接 replay
  B11 live run records）。
- 每 record 计算 5 个 ablation variants（A-E）。
- 预计运行时间：分钟级（replay）或每 model family 4-6 小时 CI（live ablation）。

## Ablation variants

Balanced policy `balanced_policy_v1_benchmark_routed` 只有一条 routing rule：
`ambiguous→weak_only, else P25`。下列 5 个 ablation variants 把该规则分解为可能
驱动其增益的各个组件。

| Variant | 定义 | 测试 |
| --- | --- | --- |
| **A**（full balanced） | `ambiguous→weak_only, else P25` —— 完整 balanced policy | Reference（被分析的 policy） |
| **B**（deterministic LLM reduction） | `P25 for all，但对 ambiguous tasks 跳过 LLM`（改用 `candidate_baseline`） | 是 `weak_only` 还是仅跳过 LLM 起作用 |
| **C**（ambiguous weak_only only） | 同 A（balanced policy 只有 ambiguous→weak_only 规则） | 冗余检查；A≡C，分析时合并 |
| **D**（P25 default only） | `P25 for all`（无 ambiguous→weak_only 规则）—— baseline | routing rule 是否真的有用 |
| **E**（random LLM reduction） | `P25 for all，但随机跳过与 A 同样数量的 LLM calls` | H2（是否只是调用减少？） |

### A≡C equivalence

Variant A 与 Variant C 在构造上**完全相同**：balanced policy
`balanced_policy_v1_benchmark_routed` 只有一条 routing rule
（`ambiguous→weak_only, else P25`），因此 "full balanced policy"（A）与
"ambiguous weak_only only"（C）产生相同的 per-record outcome。此冗余在前向显式
声明（**不是** post-hoc 发现）：在分析中 A≡C，对每个 hypothesis test 将 Variant C
合并入 Variant A。Variant C 保留在 variant 列表中以保持可追溯性与防御性审计
（evaluator 的 A-vs-C delta 检查在每个 metric 上必须恒为零）。

## Hypotheses

所有 delta 均为 overall-mean 上的 `variant_a - comparator`（正值 = 改进）。
"≈" 表示绝对值在 ±0.02 以内，">" 表示严格大于 0.02（即正好 +0.02 视为 "≈"，
**不是** ">"）。Primary quality metrics 为 `gold_span` 与 `span_f0_5`。

### H1（ambiguous routing）

> Balanced policy 的增益来自特定的 `ambiguous→weak_only` routing rule，而非
> 通用 LLM-call reduction，亦非 P25 default 单独。

**Supported if** 同时满足：

- `A > D`（`gold_span`）且 `A > D`（`span_f0_5`）（routing rule 超过 P25 default）
- `A > E`（`gold_span`）且 `A > E`（`span_f0_5`）（routing rule 超过随机
  LLM-call reduction）
- `A > B`（`gold_span`）且 `A > B`（`span_f0_5`）（routing rule 超过确定性
  LLM-skip）

**Refuted if** 任一不满足。

### H2（LLM call reduction）

> Balanced policy 的增益来自减少 LLM 调用 —— 任何减少都会有益，而非特定的
> `weak_only` 路由。

**Supported if** 同时满足：

- `A ≈ E`（`gold_span`）且 `A ≈ E`（`span_f0_5`）（随机 LLM-call reduction
  与 routing rule 持平）
- `A > D`（`gold_span`）且 `A > D`（`span_f0_5`）（减少相对 P25 default 有意义）

**Refuted if** 任一不满足。

### H3（P25 fallback sufficiency）

> `ambiguous→weak_only` routing rule 没用；P25 default action 单独即足够。

**Supported if** 同时满足：

- `D ≈ A`（`gold_span`）（P25 default 单独匹配 full balanced policy 的 gold）
- `D ≈ A`（`span_f0_5`）（P25 default 单独匹配 full balanced policy 的 SpanF0.5）

**Refuted if** 任一不满足。

> 注：H3 与 H1 互斥（若 routing rule 超过 P25 default，则 H3 被反驳）。H1 与 H3
> 不可能同时被 supported。

### H4（model-specific）

> Balanced policy 的 effect sizes 在 model families 之间显著变化（例如 Kimi
> 上 `A > D` 但 DeepSeek 上 `A ≈ D`）。

**Supported if** `A - D` `gold_span` delta 在 model families 之间的最坏 spread
超过 0.05。

**Refuted if** spread ≤ 0.05。

## Methodology

### Replay-based（首选）

若 P21 records 可用（来自 B11 live runs 或 CI ephemeral records），B12 为纯
replay：

1. 对每条 P21 record，per-strategy outcome 已存在（`candidate_baseline`、
   `llm_span_narrow`、`llm_filter` 等）。
2. 对每个 ablation variant（A-E），通过选取合适的 per-strategy outcome 计算
   per-record outcome：
   - **A**：ambiguous tasks 选 `weak_only` outcome，否则选 `p25` outcome。
   - **B**：ambiguous tasks 选 `candidate_baseline` outcome，否则选 `p25` outcome。
   - **C**：与 A 相同。
   - **D**：所有 tasks 选 `p25` outcome。
   - **E**：选 `p25` outcome，但对一个随机抽取、规模与 A 的 ambiguous-task 子集
     相同的子集，改选 `candidate_baseline`（确定性 seed）。
3. 聚合 per-variant metrics（overall mean、worst-group、bootstrap CIs、
   RobustUtility）。
4. 应用 predeclared hypothesis criteria。

### Live ablation runs（fallback）

若 P21 records 不可用，B12 需要新的 live runs。将每个 ablation variant 作为
不同的 policy 运行 P21：

- 5 variants × 4 model families × 8 repos = 160 live runs（或批量）。
- 每个 run 产生 P21 ephemeral records（之后亦可 replay）。
- 需要 `workflow_dispatch` + `enable_remote_models=true`。

强烈首选 replay 路径：不产生新 LLM 调用、无成本、完全 deterministic。

## Metrics

与 B11 相同。

### Primary metrics

- `SpanF0.5`
- `MRR`
- Gold retention（`added_gold_span`）
- False spans（`added_false_span`）
- PFP（`primary_false_positive_rate`）
- LLM calls（`model_calls`）
- Cost（估算 provider 成本）
- Latency（p50/p95）

### Aggregation

- Overall mean（跨所有 tasks）
- **Worst-group** 按：
  - Model family（Kimi/Qwen/DeepSeek Flash/DeepSeek Pro）
  - Repo（8 repos）
  - Language（Python/TypeScript/Go/Rust/Java）
  - Task bucket（positive/negative/ambiguous/hard-distractor）

### Statistical

- 95% bootstrap confidence intervals（10,000 resamples，stratified by repo）
- Leave-one-repo-out sensitivity
- Leave-one-model-family-out sensitivity
- Paired deltas（Variant A vs 每个 comparator）
- Holm-Bonferroni correction for multiple comparisons

### RobustUtility

```text
RobustUtility = min_group(
    SpanF0.5
    - λ * PFP
    - μ * normalized_cost
    - ν * normalized_latency
)
```

Predeclared 参数（镜像 B11）：
- `λ = 1.0`
- `μ = 0.1`
- `ν = 0.1`

## Predeclared hypothesis support/refute criteria

所有 delta 均为 overall-mean 上的 `variant_a - comparator`（正值 = 改进）。下列
thresholds 在任何 B12 ablation runs 之前 FROZEN。

| Hypothesis | Support criterion | Refute criterion |
| --- | --- | --- |
| H1（ambiguous routing） | `A > D` 且 `A > E` 且 `A > B`（gold/SpanF0.5，全部 > 0.02） | 任一不满足 |
| H2（LLM call reduction） | `A ≈ E`（gold/SpanF0.5 在 ±0.02 内）且 `A > D` | 任一不满足 |
| H3（P25 fallback sufficiency） | `D ≈ A`（gold/SpanF0.5 在 ±0.02 内） | 任一不满足 |
| H4（model-specific） | `A - D` `gold_span` delta 在 model families 间最坏 spread > 0.05 | spread ≤ 0.05 |

B12 verdict 框架发出以下之一：
- `supported`（全部 4 个 hypotheses supported）
- `refuted`（全部 4 个 hypotheses refuted）
- `partial`（部分 supported、部分 refuted）
- `insufficient_data`（synthetic fixture，或 records 太少无法评估）
- `not_implemented`（`--input` stub，真实计算延后）

## CI workflow design

### New stage: `b12_mechanism_decomposition`

向 `.github/workflows/real-provider-benchmark.yml` 添加新 stage
`b12_mechanism_decomposition`。该 stage 对 B11 live runs 产生的 P21 ephemeral
records 运行 B12 report aggregator（replay），或对新的 live ablation runs 运行
（fallback）。

### Workflow inputs

- `stage`: `b12_mechanism_decomposition`
- `replay_source`: `ci_ephemeral_records`（replay）或 `live_ablation_runs`
  （fallback）
- `enable_remote_models`: `true`（仅 live ablation runs 需要）
- `model_family`: 可选（单 model family 运行）

### Run matrix

- Replay：1 个 run（消费 B11 records）。
- Live ablation：5 variants × 4 model families × 8 repos = 160 runs（批量）。

## B10B/B11 integration

- B12 对 B11 live run records 进行 replay
  （`replay_source="ci_ephemeral_records"`）。
- B12 **不**重新运行 B10B（B10B 是 ambiguous-branch shadow predicate，不是
  ablation variant）。
- B12 的 frozen artifacts 包括 B10、B10B、B11、P25 与 Conservative specs（与
  B11 相同集合，再加上 B11 spec 本身）。
- B12 evaluator skeleton 验证 B10/B10B/B11 reference specs 在 disk 上存在且已
  pinned（`frozen_reference_specs_pinned_on_disk`）。

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
runtime_calls_by_replay=0（replay 不产生新 live calls）
model_calls_by_replay=0（replay 不产生新 LLM calls）
aggregate_only_public_artifact=true
policy_search_performed=false（B12 期间不做 policy tuning）
quality_strategy_tuned=false
replay_only_no_live_ablation_runs_in_evaluator=true
```

## Artifacts

- `artifacts/b12_mechanism_decomposition/b12_mechanism_decomposition.algorithm.json`
  （frozen spec；deterministic、稳定 sha256）
- `artifacts/b12_mechanism_decomposition/b12_mechanism_decomposition_report.json`
  （synthetic-fixture self-test report，verdict `insufficient_data`）

## Self-test

```bash
python3 eval/b12_mechanism_decomposition.py --self-test
```

不进行 live runs 即验证 report aggregator 机制（仅 synthetic fixture；
`replay_source="synthetic_fixture"`；verdict `insufficient_data`）。self-test 运行
10 个检查：

1. `forbidden_scan` —— forbidden public keys/values 扫描
2. `spec_hash_stable` —— algorithm spec sha256 稳定性
3. `synthetic_fixture_metrics` —— synthetic fixture（含 A≡C equivalence）
4. `hypothesis_evaluation_stub` —— hypothesis 评估机制
5. `input_stub_not_implemented` —— `--input` stub 返回 `not_implemented`
6. `reference_specs_pinned` —— B10/B10B/B11 reference specs 在 disk 上存在
7. `artifacts_regenerated` —— 从 build 函数重新生成 on-disk artifacts
8. `on_disk_artifacts_validated` —— 验证 on-disk spec + report
9. `ablation_variants_defined` —— 5 个 ablation variants + A≡C equivalence
10. `hypotheses_defined` —— 4 个 hypotheses + predeclared criteria

## What's autonomous vs. needs user action

### Autonomous（现在即可做）

- B12 plan 文档（本文件）
- B12 CI workflow 定义（新 stage `b12_mechanism_decomposition`）
- B12 report aggregator skeleton（`eval/b12_mechanism_decomposition.py`）+
  self-test
- B12 frozen algorithm spec + synthetic-fixture report artifacts

### Needs workflow_dispatch

- Live ablation runs（若 P21 records 不可用；需 `enable_remote_models=true` +
  `OPENLOCUS_ALLOW_REMOTE=1`）
- 用户触发每个 model family 的 live ablation run

### Needs user review

- 结果解读
- 是否进入 B13（distributionally robust policy search）的决策
- 是否从 minimum viable 扩展到 full B12 的决策

## What B12 does NOT prove

- B12 **不**证明 balanced policy 已可 promotion。
- B12 **不**更改任何 defaults。
- B12 **不**更改 `EvidenceCore` 语义。
- B12 **不**授权 B13，需单独用户评审。
- B12 **不**对 balanced policy 做 tuning（无 policy search；policy 自 B10 起冻结）。
- B12 的 `--input` 路径为 stub（`verdict="not_implemented"`）；完整 per-record
  replay 计算延后到后续任务。

## Next steps after B12

- **B12 supports H1**：`ambiguous→weak_only` routing rule 是 active mechanism。
  进入 B13，用 distributionally robust objectives 优化 routing rule。
- **B12 supports H2**：增益仅来自 LLM-call reduction。Balanced policy 过度工程化；
  更简单的 random-skip policy 也可行。B13 应搜索最简充分 policy。
- **B12 supports H3**：routing rule 无益；P25 default 已足够。Balanced policy 增加
  复杂度而无收益。B13 应考虑是否移除 routing rule。
- **B12 supports H4**：mechanism 是 model-family-specific。B13 应搜索
  model-family-conditional policies。
- **B12 refutes all**：balanced policy 的增益无法由这四个候选 mechanism 解释。
  B13 应探索替代 mechanism（如 candidate-pool size effects、task-difficulty
  interactions）。
