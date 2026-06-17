# B6C 冻结策略新鲜验证

> 中文译本待补充。本文件先保留英文原文，避免内容丢失。

## English source / 英文原文

# B6C Frozen-Policy Fresh Validation

Date: 2026-06-17

B6C is the fresh-validation protocol for the two policies frozen by B6B. The
evaluator can receive a new paired P21 records sample and evaluate the frozen
policies plus the fixed P25 bucket-routed baseline. B6C performs **no** search,
rule generation, or winner selection. The committed artifact is a self-test only;
live validation must use a manifest with the B6C freshness contract.

## Frozen policy candidates

The two candidates are loaded from `eval/b6c_frozen_candidates.json` and checked
against an exact frozen spec hash:

* `ambiguous_query_weak_only_default_use_p25_action`
* `negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action`

Only three predicates are allowed in B6C reconstruction:
`ambiguous_or_query_noise`, `hard_distractor_like`, and `always_true`.

## Fresh validation protocol

```text
repo count: 4 public repo slices
dataset: ci_smoke
tasks per repo: 6
task_sample_mode: round_robin_public_buckets
model: [mk]Kimi-K2.7-Code
output mode: tool_call
plain pack: topk_plain_v0
hard pack: hard_distractor_contrast_v0
stage: b6c_frozen_policy_validation
freshness contract: b6c-fresh-validation-contract-v0
```

All records are paired per repo inside `$RUNNER_TEMP`; only the aggregate B6C
report and markdown doc are uploaded. Self-test reports are marked
`self_test_only` and must not be interpreted as fresh validation.

## Aggregate-only evaluation

B6C merges the fresh paired records and evaluates every frozen policy and the
P25 baseline on the full merged task set. The public report contains only:

* per-policy-family added gold/false spans, false/gold ratio, mean SpanF0.5,
  primary false-positive rate, no-gold false-primary rate;
* effective LLM action count / provider-call estimate;
* net span value 2x and deltas versus P25;
* routing invariance check result;
* frozen policy count and names;
* sample freshness protocol and manifest integrity summary;
* safety flags (`policy_search_performed=false`, `promotion_ready=false`,
  `default_should_change=false`, etc.).

No task IDs, repo IDs, candidate IDs, paths, line ranges, digests, snippets,
prompts, responses, or gold spans are emitted.

## Safety invariants

```text
claim_level=frozen_policy_fresh_validation
policy_search_performed=false
policy_search_not_admission=true
frozen_policy_validation=true
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
remote_calls_by_policy_search=0
aggregate_only_public_artifact=true
public_per_repo_rows=false
public_per_task_rows=false
```

B6C declares no winner and recommends no default change. It is a diagnostic-only
follow-on to B6B.
