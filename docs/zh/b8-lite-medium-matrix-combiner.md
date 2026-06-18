# B8-lite Medium Matrix Combiner

Status: `ok`
Claim level: `derived_aggregate_of_frozen_policy_validations`

B8-lite is a **derived aggregate rollup** of two `b6c-frozen-policy-validation-v0` aggregate reports (B6C / B6F). It performs no per-task, per-repo, per-candidate, or source-record reads, makes no provider calls (`new_provider_calls=0`), performs no policy search, and declares no winner / default / promotion. It is **not** a new validation run and **not** a model-robust claim; it is single-model only.

## Source contract

- Inputs: exactly two `b6c-frozen-policy-validation-v0` aggregate reports.
- Each input must have `status=ok`, `claim_level=frozen_policy_fresh_validation`, `self_test=false`, `aggregate_only_public_artifact=true`, all raw/repo/task/candidate flags false, `policy_search_performed=false`, and `promotion_ready/default_should_change/evidencecore_semantics_changed=false`.
- Cross-report: `frozen_policy_names`, `policy_rules`, and `comparability.{model,output_mode,plain_pack_layout,hard_pack_layout}` must match exactly.
- `status=ok` requires `--private-disjointness-verified`; otherwise the combiner emits `blocked_disjointness` because it cannot itself prove the two source runs did not share tasks/repos.

## Aggregate policy families

| Policy family | source | +gold | +false | F/G | SpanF0.5 | PFP | LLM calls | net 2x | gold kill vs P25 | false reduction vs P25 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `ambiguous_query_weak_only_default_use_p25_action` | frozen | 21 | 34 | 1.6190 | 0.0467 | 0.0000 | 62 | -47 | 0 | 7 |
| `negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action` | frozen | 12 | 13 | 1.0833 | 0.0296 | 0.0000 | 13 | -14 | 6 | 28 |
| `p25_bucket_routed_v0_plain` | baseline | 21 | 41 | 1.9524 | 0.0467 | 0.0417 | 94 | -61 | 0 | 0 |

## Combination rules

- Counts summed directly: task / comparable / positive / no_gold / excluded / added_gold / added_false / action_counts / effective_llm_action_count / provider_call_estimate / fallback_to_baseline_count / missing_action_outcome_count / gold_kill_vs_p25 / false_reduction_vs_p25.
- `false_per_gold` recomputed as added_false / added_gold.
- `net_span_value_2x` recomputed as added_gold - 2 * added_false.
- `mean_span_f05` and `mean_primary_false_positive_rate` recomputed as task_count-weighted means.
- `no_gold_false_primary_rate` recomputed as a no_gold_task_count-weighted mean.
- `action_rates` and `effective_llm_action_rate` recomputed against the summed task_count.

## Safety invariants

```text
claim_level=derived_aggregate_of_frozen_policy_validations
policy_search_performed=false
new_provider_calls=0
derived_aggregate_rollup=true
single_model_only=true
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
remote_calls_by_policy_search=0
aggregate_only_public_artifact=true
public_per_repo_rows=false
public_per_task_rows=false
repo_ids_in_artifact=false
repo_names_in_artifact=false
repo_set_hash_in_artifact=false
winner_declared=false
default_recommendation_declared=false
promotion_declared=false
```

The public artifact does not emit input paths, repo names, repo IDs, task IDs, candidate IDs, digests, hashes, per-repo rows, or a repo-set hash. Source workflow run IDs may be echoed when supplied (run IDs are not repo/path identifiers).

