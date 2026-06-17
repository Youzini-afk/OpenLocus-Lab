# B6-lite Interpretable Policy Search

Date: 2026-06-17

B6-lite is a live diagnostic stage that searches a small, pre-registered grammar
of interpretable routing rules over paired P21 ephemeral records.  It follows
the B3 input pattern:

* `topk_plain_v0` records supply `candidate_baseline`, `llm_span_narrow`,
  `llm_filter`, `llm_abstain_filter`, and `weak_candidate_only` outcomes.
* `hard_distractor_contrast_v0` records supply a hard-distractor `llm_filter`
  outcome for the same task set.

B6-lite compares the fixed P25 bucket-routed baseline, three B3-style RMC
baselines, and a bounded set of automatically generated rule-based policies.  It
reports a Pareto frontier over quality, cost, and failure dimensions, not a
single winning policy.

## Live run matrix

```text
repos: py_flask, js_express, go_gin, rust_ripgrep
dataset: ci_smoke
tasks per repo: 6
task_sample_mode: round_robin_public_buckets
model: [mk]Kimi-K2.7-Code
output mode: tool_call
stage: b6_lite_policy_search
```

Run IDs:

```text
py_flask      27687069200
js_express    27687070596
go_gin        27687071794
rust_ripgrep  27687073224
```

All four runs completed successfully and passed artifact privacy gates.

## Rule grammar

The search space is intentionally small:

* at most 5 rules per policy;
* at most 3 predicates per rule;
* rules matched first-to-default;
* minimum rule support observed in the run, capped at 3 when possible.

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

## Report outputs

The public artifact is aggregate-only:

* per-policy added gold/false spans, false/gold ratio, mean SpanF0.5, primary
  false-positive rate, no-gold false-primary rate, action counts/rates;
* effective LLM action count / provider-call estimate;
* net span value 2x, gold kill vs P25, false reduction vs P25;
* Pareto frontier across quality, false, and cost;
* overfit diagnostics: leave-one-repo-out and leave-one-bucket-out aggregate
  rank-stability summaries (no repo IDs published).

Safety invariants are explicit: `promotion_ready=false`,
`default_should_change=false`, `evidencecore_semantics_changed=false`,
`remote_calls_by_policy_search=0`, and no task/repo/candidate/path/snippet/prompt/response/gold
content in the artifact.

## Aggregate observations across the four live runs

The following table aggregates policies that appeared in the per-repo reports or
were key baselines. These are observed smoke results, not model-robust policy
claims.

| Policy | Repos observed | Frontier appearances | Gold | False | False/gold | Mean SpanF0.5 avg | Mean PFP avg | LLM actions | Net span value 2x |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `p25_bucket_routed_v0_plain` | 4 | 0 | 8 | 7 | 0.875 | 0.0890 | 0.0417 | 24 | -6 |
| `rmc_hybrid_v0` | 4 | 1 | 8 | 7 | 0.875 | 0.0890 | 0.0833 | 11 | -6 |
| `rmc_llm_pack_routed_v0` | 4 | 0 | 8 | 7 | 0.875 | 0.0890 | 0.0833 | 24 | -6 |
| `ambiguous_query_weak_only_default_use_p25_action` | 4 | 1 | 8 | 6 | 0.750 | 0.0890 | 0.0000 | 12 | -4 |
| `negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action` | 4 | 3 | 5 | 2 | 0.400 | 0.0629 | 0.0000 | 4 | 1 |
| `rmc_local_conservative_v0` | 4 | 4 | 4 | 18 | 4.500 | 0.0226 | 0.0000 | 0 | -32 |
| `default_candidate_baseline` | 4 | 1 | 8 | 43 | 5.375 | 0.0469 | 0.0833 | 0 | -78 |

Two searched policies are worth follow-up, but neither is ready as a default:

```text
ambiguous_query_weak_only_default_use_p25_action:
  Same observed added gold as P25, one fewer false span, lower observed PFP, but
  it appeared on the frontier in only one repo and still uses 12 LLM actions.

negative_weak_only_ambiguous_query_use_p25_action_default_use_p25_action:
  Very low false cost and positive net span value, but lower gold/SpanF0.5; it is
  a candidate for a conservative fast/balanced policy, not a deep quality policy.
```

The leave-one-bucket rank deltas were non-zero in every repo (roughly `0.08` to
`0.75`), and leave-one-repo-out was unavailable inside each single-repo workflow
run. Therefore B6-lite provides candidate routing hypotheses, not robust policy
selection.

## Interpretation

B6-lite confirms the B3 lesson: fixed global RMC is too crude, but the searched
grammar can discover lower-false-cost routing patterns. The best observed
searched candidates mostly keep P25 for uncertain cases and weaken/avoid routes
that B3 showed were too aggressive. This suggests the next version should train
and validate across a combined multi-repo matrix rather than selecting per-repo
frontiers independently.

The next step should be either:

```text
B6B combined-matrix policy search:
  merge the four repo reports/ephemeral records into a single offline search and
  compute leave-one-repo-out properly; or

B7 atom ablation:
  break pack layouts into atoms and search over atom/role/bucket combinations.
```

B6-lite does not change defaults, does not admit Evidence, and does not promote a
policy.
