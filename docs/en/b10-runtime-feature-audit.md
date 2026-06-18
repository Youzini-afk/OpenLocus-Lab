# B10 Runtime Feature Audit + Balanced Policy v1 Freeze

Date: 2026-06-18

B10 freezes the B6C main balanced candidate
`ambiguous_query_weak_only_default_use_p25_action` as the algorithm spec
`balanced_policy_v1_benchmark_routed` and audits the provenance of every
routing feature the spec actually reads. B10 does **not** run any model, does
**not** search, does **not** change the frozen policy, and does **not** change
`EvidenceCore`.

This is a **benchmark-routed research algorithm spec only**. It is NOT a
runtime-feature-only policy, NOT a default change, NOT a promotion candidate.

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

Rules (exact order, predicates, actions; verified against
`eval/b6c_frozen_candidates.json` and its `frozen_spec_sha256`):

| # | Rule | Predicates | Action | Default |
| --- | --- | --- | --- | --- |
| 1 | `ambiguous_query_weak_only` | `ambiguous_or_query_noise` | `weak_only` | no |
| 2 | `default_use_p25` | `always_true` | `use_p25_action` | yes |

## Predicate provenance

`ambiguous_or_query_noise` is implemented as
`b6_lite_interpretable_policy_search._noisy_or_ambiguous`, which is
`_ambiguous_like(task) or _query_noise(task)`:

* `_ambiguous_like` reads the benchmark public labels `task_bucket` and
  `task_risk_tags` for `{ambiguous, hallucination_risk, weak_candidates}`.
  This is a **benchmark public dependency**, not a runtime feature.
* `_query_noise` reads the deterministic runtime feature
  `route_features.query_noise`. This is a **deterministic runtime dependency**.

`always_true` is `lambda _t: True` and has no dependencies (deterministic).

## Action provenance

`weak_only` resolves to `plain.outcomes.weak_candidate_only`; no LLM call.

`use_p25_action` delegates to
`p25_bucket_policy.route_bucket_routed_v0(task, choose_negative_strategy([task]))`
and therefore **inherits** P25's deterministic runtime route_features:
`route_features.candidate_count` and `route_features.candidate_support_exists`.
P25 exact/unique short-circuiting is currently driven by bucket labels rather
than by a `route_features.unique_symbol_anchor` read. P25 also re-reads
`task_bucket`/`task_risk_tags` (benchmark public).

## Runtime feature audit summary

```text
benchmark_public_dependencies:
  - task_bucket
  - task_risk_tags

deterministic_runtime_dependencies:
  - route_features.query_noise
  - always_true
  - route_features.candidate_count          # inherited from use_p25_action -> P25
  - route_features.candidate_support_exists  # inherited from use_p25_action -> P25

score_private_dependencies_for_routing: []
score_private_used_for_aggregate_scoring:
  - has_gold
  - score_group
  - outcome_metrics
```

### Why `runtime_clean = false`

A runtime-feature-only policy would have no `task_bucket`/`task_risk_tags`
labels. The `ambiguous_or_query_noise` predicate cannot be evaluated without
those labels because its `_ambiguous_like` branch reads them. With labels
absent and `route_features.query_noise = 0`, the predicate is `False` for every
task, so the spec would route everything to the `default_use_p25` action and
the `ambiguous_query_weak_only` rule would never fire. Therefore:

* `runtime_clean = false`
* `runtime_feature_only_mode_supported = false`
* `runtime_feature_only_mode_would_fail = true`

This is asserted by the B10 self-test using a runtime-only probe task.

### Score-private field boundary

Routing uses **no** score-private fields. `has_gold`, `score_group`, and
`outcome_metrics` are used only for aggregate scoring after actions are chosen
(the same RUN/SCORE separation invariant used by P25/P30). The B10 self-test
asserts `score_private_dependencies_for_routing == []`.

## Excluded adapter layer

`model_adapter`, `output_mode`, provider credentials, provider endpoint, and
provider secrets are **NOT** part of this algorithm spec. They are an excluded
adapter layer (see
[`b4-b9-model-robust-evidence-conversion.md`](b4-b9-model-robust-evidence-conversion.md)).
Output mode is treated as a model-adapter configuration parameter, not an
OpenLocus algorithm variable.

## Aggregate-only public artifact

The public artifacts emit no per-task / per-repo / candidate / path / span
identifiers, no snippets, prompts, responses, gold spans, provider keys, base
URLs, API keys, or content hashes. The B10 self-test scans both published JSON
artifacts for the forbidden public keys
(`task_id`, `repo_id`, `candidate_id`, `path`, `span`, `snippet`, `prompt`,
`response`, `gold_spans`, `provider_key`, `base_url`, `api_key`,
`content_sha`) and for conservative leaked-value patterns (content hashes,
URLs, credential assignments). The literal frozen SHA-256 hex is kept only in
the input file `eval/b6c_frozen_candidates.json`; the public artifacts carry
the boolean `frozen_spec_hash_matched=true` instead.

## Safety invariants

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

## Next step: `balanced_policy_v1_runtime_shadow`

The next step is **not** promotion and **not** a default change. It is
`balanced_policy_v1_runtime_shadow`: replace the ambiguous bucket/tag branch of
`ambiguous_or_query_noise` with pure runtime features
(`query_noise`, `candidate_support_exists`, anchor disagreement) and run an
action-agreement replay against this benchmark-routed spec. The goal is a
runtime-feature-only balanced policy whose action distribution agrees with this
spec on the same frozen records. That runtime-shadow policy is **not** this
spec.

## Artifacts

* `artifacts/b10_runtime_feature_audit/b10_runtime_feature_audit_report.json`
* `artifacts/b10_runtime_feature_audit/balanced_policy_v1_benchmark_routed.algorithm.json`

## Self-test

```bash
python3 eval/b10_runtime_feature_audit.py --self-test
```

The self-test verifies the exact frozen spec hash, rule order, predicates, and
actions; reuses `b6_lite_interpretable_policy_search` and `p25_bucket_policy`
to assert the real predicate/action provenance; asserts
`runtime_feature_only_mode_would_fail` and `runtime_clean=false` because of
`task_bucket`/`task_risk_tags`; asserts no forbidden public keys; and asserts
`score_private_dependencies_for_routing=[]`.
