# B6-lite 可解释策略搜索

> 中文译本待补充。本文件先保留英文原文，避免内容丢失。

## English source / 英文原文

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

## Status

Self-tested scaffold ready; real paired P21 ephemeral records will be populated
by the `b6_lite_policy_search` workflow stage.

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

## Interpretation so far

The self-test scaffold produces a deterministic frontier and demonstrates that
the evaluator can:

1. load paired P21 ephemeral records,
2. evaluate P25 and B3-style baselines,
3. enumerate a bounded rule grammar,
4. compute Pareto dominance,
5. report aggregate overfit diagnostics,
6. keep the public artifact free of per-task identifiers.

Real-provider runs are required before any quality conclusion can be drawn.
