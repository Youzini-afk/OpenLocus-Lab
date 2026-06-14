# P30 Admission Model V3 Report

- Schema: `p30-admission-v3-report-v1`
- Generated: 2026-06-14T10:32:36.412515+00:00
- Status: `self_test_only`
- Self-test: True
- External calls: 0

## Policies compared

| Policy | Description |
|---|---|
| candidate_baseline | No LLM; use local candidate baseline. |
| llm_span_narrow | Always run LLM span narrowing. |
| llm_filter | Always run LLM filtering. |
| llm_abstain_filter | Always run abstaining LLM filter. |
| bucket_routed_v0 | P25 bucket-routed role policy (imported baseline). |
| admission_v3 | Explainable monotonic scorecard with hard guards; actions: abstain, admit_symbol_regex_union, admit_rrf_primary, admit_llm_span_narrow, apply_llm_filter, supporting_only, weak_candidate_only. |

## Aggregate results

| Policy | tasks | +tasks | no_gold | SpanF0.5 | PFP | no_gold PFP | added_gold | added_false | filter_kill_rate | abstain_rate | selective_risk |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 14 | 10 | 4 | 0.1429 | 0.1857 | 0.4000 | 10 | 36 | 0.0000 | 0.0000 | n/a |
| llm_span_narrow | 14 | 10 | 4 | 0.2286 | 0.1214 | 0.3000 | 10 | 22 | 0.0000 | 0.0000 | n/a |
| llm_filter | 14 | 10 | 4 | 0.0857 | 0.0286 | 0.1000 | 0 | 4 | 1.0000 | 0.0000 | n/a |
| llm_abstain_filter | 14 | 10 | 4 | 0.0714 | 0.0143 | 0.0500 | 0 | 0 | 1.0000 | 1.0000 | n/a |
| bucket_routed_v0 | 14 | 10 | 4 | 0.1686 | 0.0536 | 0.0750 | 7 | 11 | 0.3000 | 0.1429 | n/a |
| admission_v3 | 14 | 10 | 4 | 0.1529 | 0.0200 | 0.0375 | 5 | 3 | 0.5000 | 0.5000 | 0.0100 |

## Deltas vs candidate baseline

| Policy | SpanF0.5 | PFP | added_gold | added_false |
|---|---:|---:|---:|---:|
| candidate_baseline | 0.0000 | 0.0000 | 0 | 0 |
| llm_span_narrow | 0.0857 | -0.0643 | 0 | -14 |
| llm_filter | -0.0571 | -0.1571 | -10 | -32 |
| llm_abstain_filter | -0.0714 | -0.1714 | -10 | -36 |
| bucket_routed_v0 | 0.0257 | -0.1321 | -3 | -25 |
| admission_v3 | 0.0100 | -0.1657 | -5 | -33 |

## Deltas vs bucket_routed_v0

| Policy | SpanF0.5 | PFP | added_gold | added_false |
|---|---:|---:|---:|---:|
| candidate_baseline | -0.0257 | 0.1321 | 3 | 25 |
| llm_span_narrow | 0.0600 | 0.0679 | 3 | 11 |
| llm_filter | -0.0829 | -0.0250 | -7 | -7 |
| llm_abstain_filter | -0.0971 | -0.0393 | -7 | -11 |
| bucket_routed_v0 | 0.0000 | 0.0000 | 0 | 0 |
| admission_v3 | -0.0157 | -0.0336 | -2 | -8 |

## admission_v3 action distribution

| Action | Count | Rate |
|---:|---:|---:|
| abstain | 7 | 0.5 |
| admit_llm_span_narrow | 1 | 0.07142857142857142 |
| admit_rrf_primary | 1 | 0.07142857142857142 |
| admit_symbol_regex_union | 3 | 0.21428571428571427 |
| apply_llm_filter | 0 | n/a |
| supporting_only | 2 | 0.14285714285714285 |
| weak_candidate_only | 0 | n/a |

## Score bands (admission_v3)

Bands are scorecard score ranges, not held-out calibrated probabilities. They show how aggregate metrics vary with the deterministic scorecard score.

| Band | count | +count | no_gold | frac_positive | SpanF0.5 | PFP |
|---|---:|---:|---:|---:|---:|---:|
| hard_guard | 7 | 3 | 4 | 0.4286 | 0.0286 | 0.0214 |
| high_admit | 5 | 5 | 0 | 1.0000 | 0.3480 | 0.0260 |
| medium_admit | 1 | 1 | 0 | 1.0000 | 0.1000 | 0.0000 |
| neutral | 1 | 1 | 0 | 1.0000 | 0.1000 | 0.0000 |

## Outcome fallback caveat

- Missing action outcomes for admission_v3: 0
- Fallback strategy counts: {}
- If an action selected by admission_v3 has no measured outcome in the input record, the evaluator falls back to `candidate_baseline` for primary-admit actions or a zero-primary surrogate for `abstain`/`supporting_only`/`weak_candidate_only`. Real evaluation should use ephemeral records that include outcomes for every action the model can select.

## Routing rules

- exact_unique_symbol_anchor + low query_noise -> admit_symbol_regex_union
- symbol_anchor or regex_anchor + local_anchor + low/moderate query noise -> admit_symbol_regex_union
- rrf_backed_by_anchor + local_anchor + moderate query noise -> admit_rrf_primary
- llm_span_narrow_valid + within_candidate + moderate query noise -> admit_llm_span_narrow
- negative/dense_quiver_trap/hard_distractor or deeply penalized score -> abstain or apply_llm_filter
- ambiguous bucket with dense/graph supporting signal -> supporting_only; without -> apply_llm_filter
- weak_candidates or weak local signal -> weak_candidate_only

## Per-task routing (self-test only)

| task_id | repo_id | task_bucket | task_risk_tags | action | score |
|---|---|---|---|---|---|
| p30-001 | py_flask | exact_symbol_unique | exact_symbol, unique_symbol, high_confidence | admit_symbol_regex_union | 5 |
| p30-002 | py_flask | positive | symbol_anchor, route_handler | admit_symbol_regex_union | 3 |
| p30-003 | js_express | positive | likely_positive | admit_symbol_regex_union | 3 |
| p30-004 | py_flask | positive | high_confidence | admit_rrf_primary | 3 |
| p30-005 | js_express | positive | likely_positive | admit_llm_span_narrow | 4 |
| p30-006 | js_express | config | config, positive | abstain | 1 |
| p30-007 | js_express | negative | negative | abstain | -6 |
| p30-008 | js_express | negative | negative | abstain | -6 |
| p30-009 | py_flask | dense_quiver_trap | dense_false_positive | supporting_only | -5 |
| p30-010 | js_express | dense_quiver_trap | dense_false_positive, hard_distractor | supporting_only | -6 |
| p30-011 | py_flask | ambiguous | ambiguous, weak_candidates | abstain | -5 |
| p30-012 | js_express | ambiguous | ambiguous, hallucination_risk | abstain | -6 |
| p30-013 | py_flask | ambiguous | weak_candidates | abstain | -5 |
| p30-014 | js_express | unknown | other | abstain | 0 |

## Conclusion

- Self-test-only scaffold evaluated 14 synthetic tasks; this is not quality evidence.
- admission_v3 uses an explainable monotonic scorecard over public task_bucket, task_risk_tags, and route_features; it does not use score_group, has_gold, or gold during routing.
- Baseline SpanF0.5=0.14285714285714285, PFP=0.18571428571428572; admission_v3 SpanF0.5=0.15285714285714286, PFP=0.02.
- No policy is promotion-ready or default-ready.
- Next: compare admission_v3 to P25 real smoke and P22/P23 guard surfaces in ephemeral remote runs.

## Safety notes

- No remote model calls were made during admission evaluation.
- Routing uses only RUN-phase public task metadata; labels/gold are used only for aggregate scoring after actions are fixed.
- This report contains only public task metadata, strategy/action names, and aggregate metrics.
- Raw queries, snippets, prompts, responses, gold spans, private labels, provider keys, and provider fields are not stored.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `external_calls=0`.
