# B12 Mechanism Decomposition

Date: 2026-06-18（2026-06-19 更新：C1 private-records adapter 已接入）

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

## C1 private per-record records（2026-06-19）

B12 现在**不再**仅消费 public aggregate，而是通过共享 C1 adapter
（`eval/c1_private_records.py`）消费 **private per-record P21 records**。adapter
加载冻结的 P21 v1 payload
（`schema_version == "p25-policy-records-ephemeral-v1"`），校验顶层 privacy flags
（`not_artifact_for_commit=true`；raw query/snippet/prompt/response flags 为 false；
`gold_spans_stored=false`），并把每条 record 规范化为内存视图，带显式的**三类
taint model**：

1. **runtime-clean `route_features`** —— runtime-clean policy 唯一可读的类别。
2. **benchmark route labels**（`task_bucket`、`task_risk_tags`）—— 用于分析冻结的
   benchmark-routed policies（B10/B11/B12 variants A/C/D），**不是** runtime-clean
   policy 输入。
3. **score/outcome/private fields**（`score_group`、per-strategy outcomes、
   `p31_score_gold`、`p31_candidate_pools`、`p33b_anchor_subtypes`）—— 仅因文件为
   runner-temp/private 且永不上传而被允许；**绝不**作为 routing 输入。

adapter **不**拒绝 `p31_score_gold_spans_stored=true`：P31 gold spans 仅在 private
runner-temp 输入下被允许。adapter **从不**写入 public artifacts；稳定的 private
per-record hash 仅保留在内存/内部，**绝不**出现在 public B12 report 中。B12 从
adapter 派生 aggregate-only metrics 并运行自己的 forbidden-key scan。

完整 C1 research record 见 `.slim/deepwork/c1-private-per-record-research-records.md`。

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
| **B**（deterministic call-reduction control） | `P25 for all，但对 `actual_call_avoided_set` 中的 records 改用 `candidate_baseline`` | 是 `weak_only` routing 还是仅在同一 records 上跳过 LLM call 起作用 |
| **C**（ambiguous weak_only only） | 同 A（balanced policy 只有 ambiguous→weak_only 规则） | 冗余检查；A≡C，分析时合并 |
| **D**（P25 default only） | `P25 for all`（无 ambiguous→weak_only 规则）—— baseline | routing rule 是否真的有用 |
| **E**（random same-count call-reduction control） | `P25 for all，但用冻结 seed 从 P25 LLM-eligible 总体中 hash-select 与 `actual_call_avoided_set` 相同数量的 records，对它们改用 `candidate_baseline`` | H2（是否只是调用减少，在任意同规模子集上？） |

### 关键集合定义（FROZEN）

- `balanced_branch_set` = balanced v1 `ambiguous_or_query_noise` predicate 命中的
  records（benchmark route labels `ambiguous` / `hallucination_risk` /
  `weak_candidates`，或 `route_features.query_noise > 0`）。注：此 predicate 读取
  benchmark route labels（category-2 taint），这正是 balanced_v1 为
  benchmark-routed、**而非** runtime-clean 的原因。
- `p25_llm_subset` = D/P25（`route_bucket_routed_v0`）会选择 `llm_span_narrow` /
  `llm_filter` / `llm_abstain_filter`（LLM 计费 strategies）之一的 records。
- `actual_call_avoided_set = balanced_branch_set ∩ p25_llm_subset` —— balanced
  policy 的 routing 实际避免了 D/P25 本会发起的 LLM call 的 records。这是 B
  variant 的干预集合。
- E random subset：用冻结 seed（`e_random_seed=20260618`）从 `p25_llm_subset`
  中 hash-select `len(actual_call_avoided_set)` 条 records。局限：仅使用单个冻结
  seed；seed-averaging 可后续添加。

四个集合在 public report 中**仅以 COUNT 形式**报告（`total_records`、
`complete_records`、`balanced_branch_count`、`p25_llm_eligible_count`、
`actual_call_avoided_count`、`random_selected_count`）。**绝不**输出 per-record
hash、task_id、raw/private repo_id、path、span 或 P31/P33 block。Aggregate group
metrics 只使用 synthetic/preregistration fixture 的 public preregistered repo labels，或
private `--input` replay 的 anonymized `public_repo_group_NNN` labels。

### A≡C equivalence

Variant A 与 Variant C 在构造上**完全相同**：balanced policy
`balanced_policy_v1_benchmark_routed` 只有一条 routing rule
（`ambiguous→weak_only, else P25`），因此 "full balanced policy"（A）与
"ambiguous weak_only only"（C）产生相同的 per-record outcome。此冗余在前向显式
声明（**不是** post-hoc 发现）：在分析中 A≡C，对每个 hypothesis test 将 Variant C
合并入 Variant A。Variant C 保留在 variant 列表中以保持可追溯性与防御性审计
（evaluator 的 A-vs-C delta 检查在每个 metric 上必须恒为零）。

## Hypotheses

所有 delta 均为 overall-mean 上的 `variant_a - comparator`（正值 = 在
higher-is-better metric 上改进；负值 = 在 lower-is-better metric 上减少）。
"≈" 表示绝对值在 ±0.02 以内，lower-is-better metric 上的"严格减少"指
`(A - comparator) < -0.02`（A 严格更低/更好）。RobustUtility 上的"严格改进"指
`(A - comparator) > 0.02`。Primary quality metrics 为 `gold_span` 与 `span_f0_5`。

> **修订后（C1）criteria。** H1-H3 support criteria 在任何 empirical replay 之前
> 修订，以对齐 balanced_v1 的实际预期 mechanism：balanced policy 预期**保持**
> gold/span 与 D 大致持平（**不**要求增加 gold/span），**减少** false spans / PFP /
> model calls 相对 D，并**优于** B/E 在 false/PFP/RobustUtility 上以支持 targeted
> ambiguous routing。A **不**被要求增加 gold/span。

### H1（ambiguous routing）

> Balanced policy 的增益来自特定的 `ambiguous→weak_only` routing rule —— 它保持
> primary quality、减少 false/PFP/model calls 相对 D，并优于 B（确定性 call-reduction）
> 与 E（随机同规模 call-reduction）在 false/PFP/RobustUtility 上。这支持 targeted
> ambiguous routing 而非通用 call-count reduction。

**Supported if** 同时满足以下四项：

- `A ≈ D`（`gold_span` 与 `span_f0_5`，保持 primary quality —— A **不**被要求增加）
- `A < D`（`false_span`、`primary_false_positive_rate`、`model_calls`，全部严格
  减少 > 0.02）
- `A < B`（`false_span` 与 `primary_false_positive_rate`）且 `RU(A) > RU(B)`
  （routing rule 优于确定性 call-reduction）
- `A < E`（`false_span` 与 `primary_false_positive_rate`）且 `RU(A) > RU(E)`
  （routing rule 优于随机同规模 call-reduction）

**Refuted if** 任一不满足。

### H2（LLM call reduction）

> Balanced policy 的增益来自减少 LLM 调用 —— 任何减少都会有益，而非特定的
> `weak_only` 路由。

**Supported if** 同时满足：

- `A ≈ E`（`gold_span`、`span_f0_5`、`false_span`、`primary_false_positive_rate`，
  随机同规模 call-reduction 与 routing rule 在 quality 与 false/PFP 上持平）
- `A < D`（`model_calls`，减少相对 P25 default 有意义）

**Refuted if** 任一不满足。

### H3（P25 fallback sufficiency）

> `ambiguous→weak_only` routing rule 在 primary quality 上无益；P25 default action
> 单独在 gold/SpanF0.5 上即足够。

**Supported if** 同时满足：

- `D ≈ A`（`gold_span`）（P25 default 单独匹配 full balanced policy 的 gold）
- `D ≈ A`（`span_f0_5`）（P25 default 单独匹配 full balanced policy 的 SpanF0.5）

**Refuted if** 任一不满足。

> 注：H3 与 H1 在 primary-quality 分量上互斥（若 A 保持而 D 偏离，则 H3 被反驳）。
> H1 与 H3 不能基于同一 primary-quality 证据同时被 supported。

### H4（model-specific）

> Balanced policy 的 effect sizes 在 model families 之间显著变化（例如 Kimi
> 上 `A > D` 但 DeepSeek 上 `A ≈ D`）。

**Supported if** `A - D` `gold_span` delta 在 model families 之间的最坏 spread
超过 0.05，**且**至少有 2 个已知 model families。

**Refuted / insufficient_data if** spread ≤ 0.05，或已知 model families 少于 2 个。
H4 默认为 `insufficient_data`，除非 model-family metadata 已知且跨 ≥ 2 个 families。

### H4 insufficient_data **不**阻断 H1-H3 mechanism verdict

当 H4 为 `insufficient_data` 时，overall B12 verdict **仅基于 H1-H3** 计算。public
report 携带两个显式 flag 确认此策略：

- `h4_insufficient_data_blocks_overall_verdict=false`
- `h1_h3_verdict_independent_of_h4=true`

这意味着**单 model B12 CI slices 仍可评估 H1-H3**（ambiguous routing /
LLM-call reduction / P25 fallback sufficiency），而 **H4（model-specific）需要
多 model 聚合**（≥ 2 个已知 model families）才能为 `supported` 或 `refuted`。因此
单 model CI slice 发出 `H4=insufficient_data` 加真实的 H1-H3 verdict
（`supported` / `refuted` / `partial`），**而非**全局 `insufficient_data`。

## Methodology

### Replay-based（首选）

若 P21 records 可用（来自 B11 live runs 或 CI ephemeral records），B12 为基于 C1
private-records adapter 的纯 replay：

1. C1 adapter 加载 private P21 v1 payload，校验 privacy flags，并以三类 taint model
   规范化每条 record。
2. 对每个 ablation variant（A-E），按冻结的 variant 定义及上述
   `actual_call_avoided_set` / E-random-subset 集合，通过选取合适的 per-strategy
   outcome 计算 per-record outcome：
   - **A**：`balanced_branch_set` 选 `weak_candidate_only`，否则选 P25 outcome。
   - **B**：`actual_call_avoided_set` 选 `candidate_baseline`，否则选 P25 outcome。
   - **C**：与 A 相同。
   - **D**：所有 tasks 选 P25 outcome。
   - **E**：冻结 seed 的 random subset 选 `candidate_baseline`，否则选 P25。
3. 聚合 per-variant metrics（overall mean、worst-group、bootstrap CIs、
   RobustUtility）并报告 count block（`balanced_branch_count` /
   `p25_llm_eligible_count` / `actual_call_avoided_count` /
   `random_selected_count`）。
4. 应用 predeclared（修订后 C1）hypothesis criteria。

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

所有 delta 均为 overall-mean 上的 `variant_a - comparator`（正值 = 在
higher-is-better metric 上改进；负值 = 在 lower-is-better metric 上减少）。下列
thresholds 在任何 B12 ablation runs 之前 FROZEN。H1-H3 criteria 在任何 empirical
replay 之前修订（C1，2026-06-19）以对齐 balanced_v1 的实际预期 mechanism。

| Hypothesis | Support criterion | Refute criterion |
| --- | --- | --- |
| H1（ambiguous routing） | `A ≈ D`（gold/SpanF0.5 在 ±0.02 内）且 `A < D`（false_span/PFP/model_calls，全部 > 0.02）且 `A < B`（false_span/PFP）且 `A < E`（false_span/PFP）且 `RU(A) > RU(B)` 且 `RU(A) > RU(E)`（全部 > 0.02） | 任一不满足 |
| H2（LLM call reduction） | `A ≈ E`（gold/SpanF0.5/false_span/PFP 在 ±0.02 内）且 `A < D`（model_calls > 0.02） | 任一不满足 |
| H3（P25 fallback sufficiency） | `D ≈ A`（gold/SpanF0.5 在 ±0.02 内） | 任一不满足 |
| H4（model-specific） | `A - D` `gold_span` delta 在 model families 间最坏 spread > 0.05 **且** ≥ 2 个已知 model families | spread ≤ 0.05 或 < 2 个已知 model families（insufficient_data） |

B12 verdict 框架发出以下之一：
- `supported`（全部 4 个 hypotheses supported）
- `refuted`（全部 4 个 hypotheses refuted）
- `partial`（部分 supported、部分 refuted）
- `insufficient_data`（synthetic fixture、records 太少，或 H4 < 2 个已知 model families）
- `not_implemented`（保留用于 legacy；`--input` 路径现已为真实实现）

Scientific verdicts（`supported` / `refuted` / `partial` / `insufficient_data`）
返回 exit 0；mechanical/privacy/schema 错误（文件未找到、错误 schema_version、
raw-private-flag 违规、adapter 错误）返回 nonzero。scientific no-result 是有效的 CI
结论，**不得**使 CI 失败。

### Count reporting（aggregate-only）

public B12 report 携带 `replay_counts` block，仅含 COUNTS：`total_records`、
`complete_records`、`balanced_branch_count`、`p25_llm_eligible_count`、
`actual_call_avoided_count`、`random_selected_count`、`e_random_seed` 及
`e_seed_limitation` 说明。**绝不**输出 per-record hash、task_id、raw/private
repo_id、path、span、candidate_id、content_sha、P31/P33 block 或 raw
prompt/response/snippet/provider field。Aggregate group metrics 只使用
synthetic/preregistration fixture 的 public preregistered repo labels，或 private
`--input` replay 的 anonymized `public_repo_group_NNN` labels。

## CI workflow design

### P21 step 集成

B12 已接入 `.github/workflows/real-provider-benchmark.yml` 的 P21 step：在 B10B/B11
消费同一 ephemeral `$P25_RECORDS` 之后、`rm -f "$P25_RECORDS"` 之前，运行 B12：

```bash
python3 eval/b12_mechanism_decomposition.py --input "$P25_RECORDS" \
  --out artifacts/real_provider_ci/b12_mechanism_decomposition_report.json
```

scientific no-result（`insufficient_data` / `refuted` / `partial`）是有效结果，**不得**
使 CI 失败；仅 file/parse/privacy/schema 错误失败（workflow 中的 validator block
校验 `schema_version`、`generated_by`、no-promotion flags、forbidden-key/value scan
及必需的 aggregate sections）。validator 的 banned keys 包括
`private_record_hash`、`p31_candidate_pools`、`p31_score_gold`、
`p33b_anchor_subtypes`、`route_features`、`task_id`、`repo_id`、`path`、`content_sha`
及 raw prompt/response/provider fields。

### Workflow inputs（用于未来 live ablation runs）

- `stage`: `b12_mechanism_decomposition`
- `replay_source`: `ci_ephemeral_records`（replay，当前）或 `live_ablation_runs`
  （fallback，尚未接入）
- `enable_remote_models`: `true`（仅 live ablation runs 需要）
- `model_family`: 可选（单 model family 运行）

### Run matrix

- Replay：1 个 run（消费 B11/P21 ephemeral records）。**当前。**
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
- `artifacts/real_provider_ci/b12_mechanism_decomposition_report.json`
  （CI ephemeral-records replay report；verdict 为 scientific result，可能为
  `insufficient_data` / `refuted` / `partial` / `supported`）

## Self-test

```bash
python3 eval/b12_mechanism_decomposition.py --self-test
python3 eval/c1_private_records.py --self-test
```

B12 self-test 在 synthetic fixture 上验证 report aggregator 机制（verdict
`insufficient_data`），**并**对 C1 adapter 的 synthetic v1 payload 做真实 `--input`
replay（verdict 为真实 scientific verdict，**非** `not_implemented`）。它运行 10 个检查：

1. `forbidden_scan` —— forbidden public keys/values 扫描
2. `spec_hash_stable` —— algorithm spec sha256 稳定性
3. `synthetic_fixture_metrics` —— synthetic fixture（含 A≡C equivalence）
4. `hypothesis_evaluation_stub` —— hypothesis 评估机制
5. `input_full_mode` —— `--input` 通过 C1 adapter 加载 private P21 v1 records，
   计算 per-variant metrics + counts，并发出真实 verdict
6. `reference_specs_pinned` —— B10/B10B/B11 reference specs 在 disk 上存在
7. `artifacts_regenerated` —— 从 build 函数重新生成 on-disk artifacts
8. `on_disk_artifacts_validated` —— 验证 on-disk spec + report
9. `ablation_variants_defined` —— 5 个 ablation variants + A≡C equivalence
10. `hypotheses_defined` —— 4 个 hypotheses + predeclared（修订后 C1）criteria

## What's autonomous vs. needs user action

### Autonomous（现在即可做）

- B12 plan 文档（本文件）
- B12 CI workflow 集成（P21 step，在 B10B/B11 之后）
- B12 report aggregator（`eval/b12_mechanism_decomposition.py`），含基于 C1
  private-records adapter 的真实 `--input` replay + self-test
- C1 共享 private-records adapter（`eval/c1_private_records.py`）+ self-test
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
- B12 的 `--input` replay 现已为真实实现（不再为 stub），但其 verdict 仅为
  mechanism decomposition。**不**随之 promotion / default change。
- B12 的 `balanced_branch_predicate` 读取 benchmark route labels（category-2 taint）；
  这正是 balanced_v1 为 benchmark-routed、**而非** runtime-clean general algorithm
  证明的原因。

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
