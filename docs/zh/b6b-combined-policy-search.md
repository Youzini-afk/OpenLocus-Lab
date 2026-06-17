# B6B 组合矩阵可解释策略搜索

> 中文译本待补充。本文件先保留英文原文，避免内容丢失。

## English source / 英文原文

# B6B Combined-Matrix Interpretable Policy Search

Date: 2026-06-17

B6B is the multi-repo extension of B6-lite.  It merges paired P21 ephemeral
records from several repos and performs a true leave-one-repo-out policy search:

* `topk_plain_v0` records supply `candidate_baseline`, `llm_span_narrow`,
  `llm_filter`, `llm_abstain_filter`, and `weak_candidate_only` outcomes.
* `hard_distractor_contrast_v0` records supply a hard-distractor `llm_filter`
  outcome for the same task set.

For each held-out repo, B6B trains the pre-registered interpretable rule grammar
on all other repos, selects the Pareto-frontier policies on that training set,
freezes them, and evaluates them on the held-out repo.  Fixed P25 bucket-routed and
fixed RMC baselines are also evaluated on every held-out repo.

## Live run matrix

```text
repo count: 4 public repo slices
dataset: ci_smoke
tasks per repo: 6
task_sample_mode: round_robin_public_buckets
model: [mk]Kimi-K2.7-Code
output mode: tool_call
plain pack: topk_plain_v0
hard pack: hard_distractor_contrast_v0
stage: b6b_combined_policy_search
```

All records are paired per repo inside `$RUNNER_TEMP`; only the aggregate B6B
report and markdown doc are uploaded.

## Rule grammar

The search space is intentionally small and identical to B6-lite:

* at most 5 rules per policy;
* at most 3 predicates per rule;
* rules matched first-to-default;
* minimum rule support observed in the training split, capped at 3.

Public routing features are `task_bucket`, `task_risk_tags`, and allowlisted
`route_features` booleans (candidate support, symbol anchors, query noise, etc.).
`has_gold`/`score_group` are used only after a policy is frozen, for aggregate
scoring.

Example rule templates:

* exact symbol + unique anchor -> `candidate_baseline`
* positive / likely-positive bucket with candidate support -> `plain_span_narrow`
* hard / dense / negative tags -> `hard_distractor_filter`, `abstain_filter`, or `weak_only`
* ambiguous or query-noise -> `use_p25_action`, `abstain_filter`, or `weak_only`
* default -> `use_p25_action` or `candidate_baseline`

## Leave-one-repo-out protocol

Policy selection is split from held-out evaluation:

1. Train set = all repos except the held-out repo.
2. Generate the grammar on the train set, deduplicate action signatures, and
   keep the Pareto-frontier policies plus the fixed baselines.
3. Freeze the selected policies.
4. Evaluate every selected policy on the held-out repo.
5. Aggregate across all held-out folds; publish only counts, means, and worst-case
   deltas versus P25.

No per-repo rows with repo identity are published.

## Report outputs

The public artifact is aggregate-only:

* per-policy-family added gold/false spans, false/gold ratio, mean SpanF0.5,
  primary false-positive rate, no-gold false-primary rate;
* effective LLM action count / provider-call estimate;
* net span value 2x and mean/worst held-out deltas versus P25;
* held-out Pareto frontier across quality, false, and cost;
* routing invariance check result;
* fold count and included repo count (counts only; no repo names).

Safety invariants are explicit: `promotion_ready=false`,
`default_should_change=false`, `evidencecore_semantics_changed=false`,
`remote_calls_by_policy_search=0`, `claim_level=leave_one_repo_diagnostic_only`,
and no task/repo/candidate/path/snippet/prompt/response/gold content in the
artifact.

## Interpretation

B6B is a diagnostic-only next step after B6-lite.  By training on a multi-repo
matrix and evaluating on held-out repos, it separates policy selection from the
repo where the policy is scored.  Because the public artifact remains
aggregate-only and leave-one-repo-out still observes only the four public CI
smoke repos, the results are not claims of model-robust policy performance.

B6B does not change defaults, does not admit Evidence, and does not promote a
policy.
