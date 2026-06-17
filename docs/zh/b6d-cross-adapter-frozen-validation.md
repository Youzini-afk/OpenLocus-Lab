# B6D 跨适配器冻结策略验证

> 中文译本待补充。本文件先保留英文原文，避免内容丢失。

## English source / 英文原文

# B6D Cross-Adapter Frozen-Policy Validation

Date: 2026-06-17

B6D is the cross-adapter smoke check for the two policies frozen by B6B and
re-evaluated by B6C. It reuses B6C's frozen candidate loading and policy
evaluation logic, but validates the same frozen policies on a DIFFERENT model
adapter: `[mk]GLM-5.2` with `json_schema_strict` output mode. B6D performs **no**
search, rule generation, or winner selection, and it is explicitly a
cross-adapter smoke, not a fresh validation or model-robust claim.

## Frozen policy candidates

B6D reuses `eval/b6c_frozen_candidates.json` — the same frozen candidates file
used by B6C — and checks it against the exact frozen spec hash. B6D must **not**
introduce a new frozen candidates file. The two frozen policies are:

* `ambiguous_query_weak_only_default_use_p25_action`
* `negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action`

Only three predicates are allowed in reconstruction:
`ambiguous_or_query_noise`, `hard_distractor_like`, and `always_true`.

## Cross-adapter protocol

```text
adapter: [mk]GLM-5.2 + json_schema_strict
model_adapter: glm_5_2_json_schema_strict
repo count: 4 public repo slices
dataset: ci_smoke
tasks per repo: 6
task_sample_mode: round_robin_public_buckets
plain pack: topk_plain_v0
hard pack: hard_distractor_contrast_v0
stage: b6d_cross_adapter_frozen_validation
freshness contract: b6d-cross-adapter-frozen-validation-contract-v0
reference adapter (frozen on): b6c_kimi_k2_7_code_tool_call
```

All records are paired per repo inside `$RUNNER_TEMP`; only the aggregate B6D
report and markdown doc are uploaded. Self-test reports are marked
`self_test_only` and must not be interpreted as a live cross-adapter run.

## Quality interpretability gate

Because GLM-5.2 `json_schema_strict` is a different adapter, B6D adds a
quality-interpretability gate before any direction comparison with the B6C
Kimi reference. The public report carries:

* `schema_valid_rate` — from the P21 `call_summary` aggregate
  (`schema_valid_calls / total_calls`);
* `infra_failure_rate` — rate-limit + bad-response fallback surface
  (`(tasks_scored - successful_calls) / total_calls`);
* `quality_interpretable` — `true` only when `schema_valid_rate >= 0.95` AND
  `infra_failure_rate <= 0.05`;
* `direction_consistency` — `consistent_with_kimi`, `inconsistent_with_kimi`,
  or `not_determinable` (the latter when `quality_interpretable` is false).

## Aggregate-only evaluation

B6D merges the paired GLM records and evaluates every frozen policy plus the P25
baseline on the full merged task set. The public report contains only:

* per-policy-family added gold/false spans, false/gold ratio, mean SpanF0.5,
  primary false-positive rate, no-gold false-primary rate;
* effective LLM action count / provider-call estimate;
* net span value 2x and deltas versus P25;
* routing invariance check result;
* frozen policy count and names;
* GLM call summary aggregate and quality-interpretability gate result;
* sample freshness protocol and manifest integrity summary;
* safety flags (`policy_search_performed=false`, `promotion_ready=false`,
  `default_should_change=false`, etc.).

No task IDs, repo IDs, candidate IDs, paths, line ranges, digests, snippets,
prompts, responses, or gold spans are emitted.

## Safety invariants

```text
claim_level=cross_adapter_smoke_only
model_adapter=glm_5_2_json_schema_strict
policy_search_performed=false
policy_search_not_admission=true
frozen_policy_validation=true
cross_adapter_smoke=true
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
remote_calls_by_policy_search=0
aggregate_only_public_artifact=true
public_per_repo_rows=false
public_per_task_rows=false
```

`claim_level` is always `cross_adapter_smoke_only`; it must never be reported as
`model_robust` or `fresh_validation`. B6D declares no winner and recommends no
default change. It is a diagnostic-only cross-adapter follow-on to B6C.

## Live cross-adapter result

Live results are recorded by workflow run ID; this committed file remains a
self-test protocol check until a live run is published.
