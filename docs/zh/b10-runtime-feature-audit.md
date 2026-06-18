# B10 运行期特征审计 + Balanced Policy v1 冻结

Date: 2026-06-18

B10 把 B6C 主 balanced candidate `ambiguous_query_weak_only_default_use_p25_action`
冻结为 algorithm spec `balanced_policy_v1_benchmark_routed`，并审计该 spec 实际读取
的每一条 routing feature 的 provenance。B10 **不**跑模型、**不**搜索、**不**改变冻结策略、
**不**改变 `EvidenceCore`。

这是 **benchmark-routed 研究 algorithm spec only**。它**不是** runtime-feature-only policy，
**不是** default 变更，**不是** promotion candidate。

## Algorithm spec

```text
algorithm_spec_id: balanced_policy_v1_benchmark_routed
claim_level: benchmark_routed_algorithm_spec_only
source frozen candidate: ambiguous_query_weak_only_default_use_p25_action
frozen spec file: eval/b6c_frozen_candidates.json
frozen spec hash matched: true
promotion_ready: false
default_should_change: false
evidencecore_semantics_changed: false
runtime_clean: false
runtime_feature_only_mode_supported: false
```

规则（顺序、predicates、actions 均已对照 `eval/b6c_frozen_candidates.json` 与其
`frozen_spec_sha256` 校验）：

| # | Rule | Predicates | Action | Default |
| --- | --- | --- | --- | --- |
| 1 | `ambiguous_query_weak_only` | `ambiguous_or_query_noise` | `weak_only` | 否 |
| 2 | `default_use_p25` | `always_true` | `use_p25_action` | 是 |

## Predicate provenance

`ambiguous_or_query_noise` 实现为 `b6_lite_interpretable_policy_search._noisy_or_ambiguous`，
即 `_ambiguous_like(task) or _query_noise(task)`：

* `_ambiguous_like` 读取 benchmark 公开标签 `task_bucket` 与 `task_risk_tags` 中的
  `{ambiguous, hallucination_risk, weak_candidates}`。这是 **benchmark public 依赖**，
  不是 runtime feature。
* `_query_noise` 读取确定性 runtime feature `route_features.query_noise`。这是
  **deterministic runtime 依赖**。

`always_true` 即 `lambda _t: True`，无依赖（deterministic）。

## Action provenance

`weak_only` 解析为 `plain.outcomes.weak_candidate_only`，不调 LLM。

`use_p25_action` 委托给
`p25_bucket_policy.route_bucket_routed_v0(task, choose_negative_strategy([task]))`，
因此**继承** P25 的确定性 runtime route_features：`route_features.candidate_count`、
`route_features.candidate_support_exists`。当前 P25 exact/unique 短路由 bucket
labels 驱动，而不是读取 `route_features.unique_symbol_anchor`。P25 还会重新读取
`task_bucket`/`task_risk_tags`（benchmark public）。

## 运行期特征审计摘要

```text
benchmark_public_dependencies:
  - task_bucket
  - task_risk_tags

deterministic_runtime_dependencies:
  - route_features.query_noise
  - always_true
  - route_features.candidate_count          # use_p25_action -> P25 继承
  - route_features.candidate_support_exists  # use_p25_action -> P25 继承

score_private_dependencies_for_routing: []
score_private_used_for_aggregate_scoring:
  - has_gold
  - score_group
  - outcome_metrics
```

### 为什么 `runtime_clean = false`

runtime-feature-only policy 不会有 `task_bucket`/`task_risk_tags` 标签。而
`ambiguous_or_query_noise` 的 `_ambiguous_like` 分支必须读取这些标签，否则无法求值。
当标签缺失且 `route_features.query_noise = 0` 时，该 predicate 对所有 task 都为 `False`，
于是 spec 会把所有 task 路由到 `default_use_p25`，`ambiguous_query_weak_only` 规则永远不触发。
因此：

* `runtime_clean = false`
* `runtime_feature_only_mode_supported = false`
* `runtime_feature_only_mode_would_fail = true`

B10 self-test 用一个 runtime-only probe task 显式断言这一点。

### Score-private 字段边界

路由阶段**不使用**任何 score-private 字段。`has_gold`、`score_group`、`outcome_metrics`
仅在 action 选定之后用于聚合打分（与 P25/P30 同样的 RUN/SCORE 分离不变式）。B10 self-test
断言 `score_private_dependencies_for_routing == []`。

## 被排除的 adapter 层

`model_adapter`、`output_mode`、provider 凭证、provider endpoint、provider 密钥**不是**
该 algorithm spec 的一部分。它们是被排除的 adapter 层（见
[`b4-b9-model-robust-evidence-conversion.md`](b4-b9-model-robust-evidence-conversion.md)）。
output mode 被视为 model-adapter 配置参数，而不是 OpenLocus algorithm 变量。

## Aggregate-only 公开 artifact

公开 artifact 不包含任何 per-task / per-repo / candidate / path / span 标识，不包含 snippets、
prompts、responses、gold spans、provider keys、base URLs、API keys 或 content hashes。B10
self-test 对两份公开 JSON artifact 扫描禁用公开键（`task_id`、`repo_id`、`candidate_id`、
`path`、`span`、`snippet`、`prompt`、`response`、`gold_spans`、`provider_key`、`base_url`、
`api_key`、`content_sha`）以及保守的泄漏值模式（content hash、URL、凭证赋值）。冻结 SHA-256
十六进制值只保留在输入文件 `eval/b6c_frozen_candidates.json` 中；公开 artifact 只带
`frozen_spec_hash_matched=true` 布尔值。

## 安全不变式

```text
claim_level=benchmark_routed_algorithm_spec_only
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
candidate_not_fact=true
llm_output_not_evidence=true
aggregate_only_public_artifact=true
policy_search_performed=false
frozen_policy_search=true
runtime_clean=false
runtime_feature_only_mode_supported=false
score_private_dependencies_for_routing=[]
```

## 下一步：`balanced_policy_v1_runtime_shadow`

下一步**不是** promotion，**不是** default 变更，而是 `balanced_policy_v1_runtime_shadow`：
用纯 runtime features（`query_noise`、`candidate_support_exists`、anchor disagreement）替换
`ambiguous_or_query_noise` 中的 ambiguous bucket/tag 分支，并在同一批冻结记录上对该
benchmark-routed spec 做 action-agreement replay。目标是得到 runtime-feature-only 的 balanced
policy。该 runtime-shadow policy **不是**本 spec。

## Artifacts

* `artifacts/b10_runtime_feature_audit/b10_runtime_feature_audit_report.json`
* `artifacts/b10_runtime_feature_audit/balanced_policy_v1_benchmark_routed.algorithm.json`

## Self-test

```bash
python3 eval/b10_runtime_feature_audit.py --self-test
```

self-test 校验精确的冻结 spec hash、rule 顺序、predicates、actions；复用
`b6_lite_interpretable_policy_search` 与 `p25_bucket_policy` 断言真实的 predicate/action
provenance；断言 `runtime_feature_only_mode_would_fail` 且 `runtime_clean=false`（原因是
`task_bucket`/`task_risk_tags`）；断言无禁用公开键；并断言
`score_private_dependencies_for_routing=[]`。
