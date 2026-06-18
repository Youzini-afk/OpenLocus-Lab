# B10B 运行期 shadow replay（仅 ambiguous 分支）

Date: 2026-06-18

B10B 是 B10 冻结 `balanced_policy_v1_benchmark_routed` 之后的下一步。它**不**跑模型、
**不**搜索、**不**调整策略质量、**不**默认化。它只测试一个固定的、预先声明的、仅依赖
runtime feature 的 shadow predicate，能否在同批记录上复现冻结 benchmark-routed spec 的
**ambiguous 分支**动作。

> **重要的 claim 边界。** B10B **不**证明 runtime-clean balanced policy。它只测试
> runtime features 能否 shadow ambiguous 分支。默认 `use_p25_action` 仍然委托给 P25
> benchmark-routed 行为，因此这是**仅 ambiguous 分支的 runtime-shadow**，不是
> runtime-feature-only policy，不是 default 变更，不是 promotion candidate，不改变
> `EvidenceCore`。

## 范围与 claim level

```text
algorithm_spec_id: balanced_policy_v1_runtime_shadow_ambiguous_branch
claim_level: ambiguous_branch_runtime_shadow_only
full_runtime_clean_policy: false
ambiguous_branch_runtime_shadow_only: true
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
policy_search_performed: false
quality_strategy_tuned: false
runtime_calls_by_replay: 0
model_calls_by_replay: 0
aggregate_only_public_artifact: true
```

## Target action（镜像 B10 冻结 spec）

target action 在每条记录上复现冻结的 `balanced_policy_v1_benchmark_routed` 语义：

```text
target_action = weak_only if ambiguous_or_query_noise else use_p25_action
ambiguous_or_query_noise = _ambiguous_like(task) or _query_noise(task)
```

* `_ambiguous_like` 读取 benchmark 公开标签 `task_bucket` 与 `task_risk_tags`，匹配
  `{ambiguous, hallucination_risk, weak_candidates}`（benchmark public 依赖）。
* `_query_noise` 读取 `route_features.query_noise`（确定性 runtime）。

## Shadow action（仅 runtime features，预先声明，不搜索）

shadow action **只**读取 runtime `route_features`，绝不读取 `task_bucket`、
`task_risk_tags`、`has_gold`、`score_group`、outcome metrics：

```text
shadow_action = weak_only if runtime_shadow_ambiguous else use_p25_action
runtime_shadow_ambiguous = query_noise
                         OR (candidate_support_exists AND anchor_disagreement_proxy)
anchor_disagreement_proxy = local_anchor AND NOT rrf_backed_by_anchor
```

`anchor_disagreement_proxy` 是 ambiguous 分支的 runtime-only 代理：本地存在 anchor
（`local_anchor`）但未被 RRF 印证（`NOT rrf_backed_by_anchor`）。

### 所需 runtime features

必须四项全部存在，shadow action 才能在该记录上求值：

* `route_features.query_noise`
* `route_features.candidate_support_exists`
* `route_features.local_anchor`
* `route_features.rrf_backed_by_anchor`

**缺失特征策略。** 如果某条记录上任意所需 runtime feature 缺失，该记录被标记为
`missing`，shadow action **不会**被静默默认为 `false`。如果所有记录都缺失某些所需
feature，report 状态为 `insufficient_runtime_features` 而不是 `ok`。

## Replay source 参数

replay 携带显式 `replay_source` 字段，声明记录来源。允许两个取值：

* `synthetic_fixture` — 由 self-test 在内存中合成的记录。verdict 被短路（见下方
  [Verdict 框架](#verdict-框架)），无论指标多干净，都**不能**产生 empirical-support claim。
* `ci_ephemeral_records` — 通过 `--records <path>` 从 CI ephemeral policy-record JSON
  加载的记录。完整 predeclared gate 评估会运行，verdict（原则上）可能产生
  `empirical_replay_support`。

这一区分可避免把 synthetic fixture 误当成 empirical support。

## 仅聚合的 report

公开 report 只输出聚合计数 —— 不含 task/repo/candidate/path/span/snippet/prompt/
response/gold/provider 键，也不含原始 path/digest/provider 字符串。`replay` 块包含：

* `denominator` — 总记录数。
* `complete_feature_count` / `complete_feature_rate` — 所有所需 shadow feature 齐全的
  记录数与比例。
* `missing_feature_counts` / `missing_feature_rates` — 每个 feature 的缺失计数与比例。
* `records_with_any_missing_feature_count` / `_rate`。
* `target_action_distribution` — 全部记录上的 `{weak_only, use_p25_action}`。
* `shadow_action_distribution` — `{weak_only, use_p25_action, missing}`。
* `confusion_matrix_target_x_shadow` — `target_action x shadow_action` 计数。
* `agreement_denominator` / `agreement_overall_rate` — 一致数 / complete 记录数。
* `agreement_per_target_action` — 每个 target-action 在 complete 记录上的一致率。
* `target_weak_only_total` / `target_use_p25_total` /
  `shadow_weak_only_total` / `shadow_use_p25_total`。
* `target_weak_only_recall` — 在 weak_only target 上的分层 recall。
* `target_use_p25_specificity` — 在 use_p25 target 上的分层 specificity。
* `shadow_weak_only_precision` — shadow weak_only 预测的分层 precision。
* `label_driven_ambiguous_recall_qn0` — 在 `query_noise == 0` 的 label-driven 子集上的
  recall（非平凡子集；shadow 不能通过共享 query_noise 平凡地一致）。
* `label_driven_ambiguous_denominator_qn0` — 该 qn0 子集规模；低于 predeclared 下限时
  会令 verdict 失败（HARD gate，见下）。
* `query_noise_only_recall_qn1` — 在共享 feature 的 qn1 子集上的 recall（一致率预期高但
  部分平凡）。
* `cohens_kappa` — 在二分类 is_weak_only 上计算的 Cohen's kappa（仅 complete 记录）。
* `silent_failure_checks` — 见 [Silent-failure 检查](#silent-failure-检查)。
* `outcome_audit` — 见 [Outcome-equivalence 审计](#outcome-equivalence-审计)。
* `feature_provenance` — 每个 feature 的依赖类别与被读取方。
* `status` — `ok` 或 `insufficient_runtime_features`。

report 顶层还额外携带：`replay_source`、`predeclared_gates`（10 个 gate，见
[预先声明的 acceptance gates](#预先声明的-acceptance-gates)）、
`runtime_shadow_ambiguous_supported`（布尔 verdict）、`support_claim`，以及（当 verdict 为
False 时）`support_claim_reason`。

## 泄漏守卫

self-test 断言：修改 `task_bucket`、`task_risk_tags`、`has_gold`、`score_group` **以及**
`outcome_metrics` **不会**改变 shadow action，但当翻转 ambiguous 标签时**会**改变 target
action。这证明 shadow predicate 对 benchmark 公开标签与所有 score-private 字段（含
`outcome_metrics`）不变。

另有一个子测试**只**修改 `outcome_metrics`（其他字段保持基线值），断言 shadow action 与
target action 都不变 —— outcome 是打分输出，绝非路由输入，shadow predicate 与 target
predicate 都不读取 `outcome_metrics`。

## 预先声明的 acceptance gates

这些 gate 在 algorithm spec 中预先声明，使 verdict 不能事后贴合 replay 结果。所有 gate 都是
HARD（逻辑 AND）：

```text
complete_feature_rate_min: 0.95
overall_action_exact_agreement_min: 0.90
target_weak_only_recall_min: 0.85
target_use_p25_specificity_min: 0.90
label_driven_ambiguous_recall_qn0_min: 0.75
label_driven_ambiguous_min_denominator: 10     # HARD gate，不是 escape clause
shadow_weak_only_precision_min: 0.80
cohens_kappa_min: 0.40
outcome_metrics_leakage_tested: true
no_silent_failure_required: true
```

`label_driven_ambiguous_min_denominator: 10` 是 HARD gate：如果 qn0 子集 denominator 低于
10，recall 指标太薄不可信，verdict 为 `False`，且
`support_claim_reason="insufficient_label_driven_denominator"`。它**不是** escape clause
（OR 分支）—— 不会让薄 qn0 子集仅凭 agreement 而通过。

## Verdict 框架

report 携带显式布尔 verdict 与两个支撑字段：

* `runtime_shadow_ambiguous_supported` — 布尔。仅在 `ci_ephemeral_records` 路径下、所有
  predeclared gate 通过时为 True。
* `support_claim` — 取以下之一：
  * `mechanics_only_synthetic_fixture` — replay 跑在 synthetic fixture 上；无论指标如何，
    不做 empirical claim。
  * `empirical_replay_support_pending` — replay 跑在 `ci_ephemeral_records` 上，但至少有
    一个 gate 失败（denominator、agreement、silent failure 或 leakage guard）。
  * `empirical_replay_support` — replay 跑在 `ci_ephemeral_records` 上，且每个 predeclared
    gate 均通过。
* `support_claim_reason` — 当且仅当 verdict 为 `False` 时存在。取以下之一：
  * `synthetic_fixture_only` — synthetic fixture 的短路原因。
  * `insufficient_label_driven_denominator` — qn0 denominator 低于 hard 下限 10。
  * `silent_failure_detected` — silent-failure 检查被触发。
  * `insufficient_agreement` — 至少一个 agreement/precision/kappa gate 失败。
  * `leakage_guard_incomplete` — 不可达兜底；仅在移除 leakage guard patch 时才会触发。

**Synthetic-fixture 短路。** 当 `replay_source == "synthetic_fixture"` 时，verdict 无条件
为 `False`，`support_claim="mechanics_only_synthetic_fixture"`，
`support_claim_reason="synthetic_fixture_only"` —— 指标仍计算并上报，但不做任何 empirical
claim。

## Outcome-equivalence 审计

在不一致子集上，审计按 `(target_action, shadow_action)` 划分记录，并报告每个分区的
outcome-metric 均值（`added_gold_span`、`added_false_span`、`span_f0_5`、
`primary_false_positive_rate`）。共追踪 4 个分区：

* `target_weak_shadow_use_p25` — target 选 weak_only，shadow 选 use_p25。
* `target_use_p25_shadow_weak` — target 选 use_p25，shadow 选 weak_only。
* `agreement_weak_only` — 双方均 weak_only。
* `agreement_use_p25` — 双方均 use_p25_action。

若没有任何记录具备可用 outcome metrics，审计状态为 `no_outcome_data`。outcome **仅用于
审计**：在 action 选定之后计算，**绝不**回馈到路由。shadow predicate 不读取
`outcome_metrics`。

## Silent-failure 检查

四个布尔值用于防止 replay 表面健康、实际退化：

* `all_shadow_ambiguous` — 每条 complete 记录都被 shadow 判为 weak_only（shadow 退化为
  “恒 weak”）。
* `all_shadow_non_ambiguous` — 每条 complete 记录都被 shadow 判为 use_p25_action（shadow
  退化为“恒不 weak”）。
* `base_rate_only_suspected` — `cohens_kappa <= 0.05` 而
  `agreement_overall_rate > 0.5`（一致率高但仅因双方在多数类上同侧；kappa 接近零会暴露
  这一点）。
* `no_silent_failure` — `not (all_shadow_ambiguous or all_shadow_non_ambiguous or
  base_rate_only_suspected)`。这是 predeclared HARD gate。

## Cohen's kappa

Cohen's kappa 直接在二分类 `is_weak_only` 上、仅 complete 记录计算 —— 不依赖
numpy / sklearn。`p_o` 为观察一致率；`p_e` 为偶然一致率
`p_target_weak * p_shadow_weak + (1 - p_target_weak) * (1 - p_shadow_weak)`；
`kappa = (p_o - p_e) / (1 - p_e)`，并加上 `1 - p_e > 0` 与有限性保护。kappa 被限制在
`[-1.0, 1.0]` 区间，由 report 校验器校验。

## 当前 verdict

在 synthetic fixture 下，当前 verdict 为：

```text
replay_source: synthetic_fixture
runtime_shadow_ambiguous_supported: false
support_claim: mechanics_only_synthetic_fixture
support_claim_reason: synthetic_fixture_only
```

这是 **mechanics-validated scaffold**，**不是** empirical-support claim。empirical support
仍处于 pending 状态，直到 B10B 在真实 CI ephemeral 记录上（`--records <path>`）运行且所有
predeclared gate 通过。

## 安全不变式

```text
claim_level=ambiguous_branch_runtime_shadow_only
full_runtime_clean_policy=false
ambiguous_branch_runtime_shadow_only=true
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
policy_search_performed=false
quality_strategy_tuned=false
runtime_calls_by_replay=0
model_calls_by_replay=0
aggregate_only_public_artifact=true
```

## 被排除的 adapter 层

`model_adapter`、`output_mode`、provider 凭证、provider endpoint、provider 密钥**不是**
本 spec 的一部分。它们是被排除的 adapter 层（见
[`b4-b9-model-robust-evidence-conversion.md`](b4-b9-model-robust-evidence-conversion.md)）。
output mode 被视为 model-adapter 配置参数，而不是 OpenLocus algorithm 变量。

## B10B 不证明什么

B10B **不**证明 runtime-clean balanced policy。默认 `use_p25_action` 仍然委托给
`p25.route_bucket_routed_v0`，后者会重新读取 `task_bucket`/`task_risk_tags` 以及继承的
runtime route_features。runtime-feature-only balanced policy 还需要替换默认分支；B10B
只 shadow 了 ambiguous 分支。具体而言，B10B：

* **不**证明 runtime-clean balanced policy；
* **不**改变 default —— `use_p25_action` 仍委托给 P25；
* **不**在 synthetic fixture 上验证 empirical support（synthetic fixture 短路为
  `mechanics_only_synthetic_fixture`）；
* **不**授权 B11 作为“supported validation”；
* **不**改变 `EvidenceCore` 语义；
* **不** promote 或 defaultize 任何 candidate。

### B11 framing

B11 应被 framing 为 **exploratory prospective stress test**，**不是** “supported
validation”，直到 B10B 在真实 CI ephemeral 记录上运行且通过所有 predeclared gate。shadow
predicate 已 FROZEN；B11 期间不调参。任何 predicate 变更都应启动新的冻结 spec / version。

## CI 集成路径

对 CI ephemeral 记录运行 B10B：

```bash
python3 eval/b10b_runtime_shadow_replay.py --records <path>
```

`<path>` 应指向 runner 清理**之前**写入 `$RUNNER_TEMP/p25-policy-records-ephemeral-v1/*.json`
的 CI ephemeral p25-policy-record JSON。replay 在 `replay_source="ci_ephemeral_records"` 模式
下运行，完整 predeclared gate 评估执行。写入的 report 仅聚合（无原始记录、无 per-task 标识），
原始记录绝不提交。

## Artifacts

* `artifacts/b10b_runtime_shadow_replay/balanced_policy_v1_runtime_shadow_ambiguous_branch.algorithm.json`
* `artifacts/b10b_runtime_shadow_replay/b10b_runtime_shadow_replay_report.json`

## Self-test

```bash
python3 eval/b10b_runtime_shadow_replay.py --self-test
```

self-test 在内存中合成 p25-policy-record 风格的记录（不依赖 live artifacts），并运行 10 项
检查：

* `perfect_agreement` — query_noise 触发且 target/shadow 均选 weak_only；无噪声且无 anchor
  分歧的用例中双方均选 use_p25_action。
* `disagreement` — target 选 weak_only（ambiguous label）而 shadow 选 use_p25_action；
  以及 target 选 use_p25_action 而 shadow 选 weak_only（anchor disagreement proxy 触发）。
* `missing_feature` — `local_anchor` 或 `query_noise` 缺失会标记记录为 missing；全部缺失则
  `status="insufficient_runtime_features"`。
* `leakage_guard` — 修改 `task_bucket`/`task_risk_tags`/`has_gold`/`score_group`/
  `outcome_metrics` 不改变 shadow action，但在相关时改变 target action；outcome_metrics-only
  子测试断言两个 predicate 都不读取 outcome。
* `replay_aggregate` — 完整聚合块：混淆矩阵、分层指标、label-driven qn0/qn1 子集、
  Cohen's kappa、silent-failure 检查、outcome 审计分区、verdict 字段。
* `verdict_synthetic_fixture_unsupported` — 干净的 synthetic fixture 绝不能产生
  empirical-support verdict；verdict 为 `False`，
  `support_claim="mechanics_only_synthetic_fixture"`。
* `verdict_insufficient_denominator_unsupported` — 在 `ci_ephemeral_records` replay 中，
  每个 agreement gate 都通过但 qn0 denominator 低于 10 时，verdict 必为 `False`，
  `support_claim="empirical_replay_support_pending"`，
  `support_claim_reason="insufficient_label_driven_denominator"`。
* `forbidden_scan` — 标记禁用公开键与保守泄漏值模式（content hash、URL、凭证赋值、64 位十六
  进制 digest、原始 `/` 分隔路径）；干净的 `module::symbol` provenance 不会被标记。
* `b10_reference` — B10 冻结 spec 在磁盘存在，B10B spec/report 引用其 id 与
  hash-matched 标志。
* `spec_hash_stable` — on-disk algorithm spec 加载、重哈希、重加载后 SHA-256 不变；并等于
  `build_algorithm_spec()` 输出。

## CLI

```bash
python3 eval/b10b_runtime_shadow_replay.py --self-test
python3 eval/b10b_runtime_shadow_replay.py --records <path>
```

`--self-test` 与 `--records` 互斥；二者必选其一。`--self-test` 以
`replay_source="synthetic_fixture"` 模式运行，打印 self-test 结果 JSON。`--records <path>`
加载一个 p25-policy-record 风格的 JSON 数组，以
`replay_source="ci_ephemeral_records"` 模式运行，把仅聚合的 report artifact 写入
`artifacts/b10b_runtime_shadow_replay/b10b_runtime_shadow_replay_report.json`，并打印一个
摘要，包含 `replay_source`、`status`、agreement metrics、`cohens_kappa`、
`silent_failure_checks`、verdict、`support_claim`，以及（若存在）`support_claim_reason`。
