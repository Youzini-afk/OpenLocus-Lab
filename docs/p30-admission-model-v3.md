# P30 Admission Model V3 Report

- Schema: `p30-admission-v3-report-v1`
- Generated: 2026-06-14T12:31:43.849245+00:00
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
| admission_v3_h1 | Same scorecard as admission_v3, evaluated against P30-H1 handoff records that include pre-SCORE local-anchor features and measured local-anchor outcomes (symbol_regex_union, rrf_primary, supporting_only, weak_candidate_only). |
| admission_v3_h2 | Stricter local-anchor policy over the same P30-H1 records; demotes file-only agreement and unanchored LLM spans to weak/supporting/abstain, and requires span-level/exact-unique-symbol agreement for primary admissions. |

## Aggregate results

| Policy | tasks | +tasks | no_gold | SpanF0.5 | PFP | no_gold PFP | added_gold | added_false | filter_kill_rate | abstain_rate | selective_risk |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 14 | 10 | 4 | 0.1429 | 0.1857 | 0.4000 | 10 | 36 | 0.0000 | 0.0000 | n/a |
| llm_span_narrow | 14 | 10 | 4 | 0.2286 | 0.1214 | 0.3000 | 10 | 22 | 0.0000 | 0.0000 | n/a |
| llm_filter | 14 | 10 | 4 | 0.0857 | 0.0286 | 0.1000 | 0 | 4 | 1.0000 | 0.0000 | n/a |
| llm_abstain_filter | 14 | 10 | 4 | 0.0714 | 0.0143 | 0.0500 | 0 | 0 | 1.0000 | 1.0000 | n/a |
| bucket_routed_v0 | 14 | 10 | 4 | 0.1686 | 0.0536 | 0.0750 | 7 | 11 | 0.3000 | 0.1429 | n/a |
| admission_v3 | 14 | 10 | 4 | 0.1014 | 0.0429 | 0.0375 | 5 | 9 | 0.5000 | 0.4286 | 0.0245 |
| admission_v3_h1 | 14 | 10 | 4 | 0.1457 | 0.0236 | 0.0375 | 5 | 4 | 0.5000 | 0.4286 | 0.0135 |
| admission_v3_h2 | 14 | 10 | 4 | 0.0600 | 0.0357 | 0.0750 | 1 | 7 | 0.9000 | 0.1429 | 0.0306 |

## Quality comparability

| Policy | quality_comparable | blocked_by_missing_action_outcomes | selected_action_fallback_rate |
|---|---:|---:|---:|
| admission_v3 | False | True | 0.5000 |
| admission_v3_h1 | True | False | 0.0000 |
| admission_v3_h2 | True | False | 0.0000 |

## Deltas vs candidate baseline

| Policy | SpanF0.5 | PFP | added_gold | added_false |
|---|---:|---:|---:|---:|
| candidate_baseline | 0.0000 | 0.0000 | 0 | 0 |
| llm_span_narrow | 0.0857 | -0.0643 | 0 | -14 |
| llm_filter | -0.0571 | -0.1571 | -10 | -32 |
| llm_abstain_filter | -0.0714 | -0.1714 | -10 | -36 |
| bucket_routed_v0 | 0.0257 | -0.1321 | -3 | -25 |
| admission_v3 | -0.0414 | -0.1429 | -5 | -27 |
| admission_v3_h1 | 0.0029 | -0.1621 | -5 | -32 |
| admission_v3_h2 | -0.0829 | -0.1500 | -9 | -29 |

## Deltas vs bucket_routed_v0

| Policy | SpanF0.5 | PFP | added_gold | added_false |
|---|---:|---:|---:|---:|
| candidate_baseline | -0.0257 | 0.1321 | 3 | 25 |
| llm_span_narrow | 0.0600 | 0.0679 | 3 | 11 |
| llm_filter | -0.0829 | -0.0250 | -7 | -7 |
| llm_abstain_filter | -0.0971 | -0.0393 | -7 | -11 |
| bucket_routed_v0 | 0.0000 | 0.0000 | 0 | 0 |
| admission_v3 | -0.0671 | -0.0107 | -2 | -2 |
| admission_v3_h1 | -0.0229 | -0.0300 | -2 | -7 |
| admission_v3_h2 | -0.1086 | -0.0179 | -6 | -4 |

## admission_v3 action distribution

| Action | Count | Rate |
|---:|---:|---:|
| abstain | 6 | 0.42857142857142855 |
| admit_llm_span_narrow | 1 | 0.07142857142857142 |
| admit_rrf_primary | 1 | 0.07142857142857142 |
| admit_symbol_regex_union | 3 | 0.21428571428571427 |
| apply_llm_filter | 0 | n/a |
| supporting_only | 2 | 0.14285714285714285 |
| weak_candidate_only | 1 | 0.07142857142857142 |

## admission_v3_h1 action distribution

| Action | Count | Rate |
|---:|---:|---:|
| abstain | 6 | 0.42857142857142855 |
| admit_llm_span_narrow | 1 | 0.07142857142857142 |
| admit_rrf_primary | 1 | 0.07142857142857142 |
| admit_symbol_regex_union | 3 | 0.21428571428571427 |
| apply_llm_filter | 0 | n/a |
| supporting_only | 2 | 0.14285714285714285 |
| weak_candidate_only | 1 | 0.07142857142857142 |

## admission_v3_h2 action distribution

| Action | Count | Rate |
|---:|---:|---:|
| abstain | 2 | 0.14285714285714285 |
| admit_llm_span_narrow | 0 | n/a |
| admit_rrf_primary | 0 | n/a |
| admit_symbol_regex_union | 1 | 0.07142857142857142 |
| apply_llm_filter | 5 | 0.35714285714285715 |
| supporting_only | 2 | 0.14285714285714285 |
| weak_candidate_only | 4 | 0.2857142857142857 |

## Score bands (admission_v3)

Bands are scorecard score ranges, not held-out calibrated probabilities. They show how aggregate metrics vary with the deterministic scorecard score.

| Band | count | +count | no_gold | frac_positive | SpanF0.5 | PFP |
|---|---:|---:|---:|---:|---:|---:|
| hard_guard | 7 | 3 | 4 | 0.4286 | 0.0286 | 0.0214 |
| high_admit | 5 | 5 | 0 | 1.0000 | 0.2240 | 0.0900 |
| medium_admit | 1 | 1 | 0 | 1.0000 | 0.1000 | 0.0000 |
| neutral | 1 | 1 | 0 | 1.0000 | 0.0000 | 0.0000 |

## Outcome fallback caveat

- Missing action outcomes for admission_v3: 7
- Missing action outcomes for admission_v3_h1: 0
- Missing action outcomes for admission_v3_h2: 0
- Fallback strategy counts (admission_v3): {'candidate_baseline': 4, 'zero_primary': 3}
- Fallback strategy counts (admission_v3_h1): {}
- Fallback strategy counts (admission_v3_h2): {}
- If an action selected by admission_v3 has no measured outcome in the input record, the evaluator falls back to `candidate_baseline` for primary-admit actions or a zero-primary surrogate for `abstain`/`supporting_only`/`weak_candidate_only`. Real evaluation should use ephemeral records that include outcomes for every action the model can select.
- admission_v3_h1 is designed to have zero missing outcomes when P21 writes P30-H1 enriched handoff records; a non-zero value here indicates the input records lack the required local-anchor outcomes.
- admission_v3_h2 is designed to be fallback-free on P30-H1 records because it selects only from the local-anchor measured outcomes already included in the handoff; a non-zero value here indicates the input records are missing outcomes for actions H2 selects.

## Routing rules (admission_v3)

- exact_unique_symbol_anchor + low query_noise -> admit_symbol_regex_union
- symbol_anchor or regex_anchor + local_anchor + low/moderate query noise -> admit_symbol_regex_union
- rrf_backed_by_anchor + local_anchor + moderate query noise -> admit_rrf_primary
- llm_span_narrow_valid + within_candidate + moderate query noise -> admit_llm_span_narrow
- negative/dense_quiver_trap/hard_distractor or deeply penalized score -> abstain or apply_llm_filter
- ambiguous bucket with dense/graph supporting signal -> supporting_only; without -> apply_llm_filter
- weak_candidates or weak local signal -> weak_candidate_only

## Routing rules (admission_v3_h2)

- negative/dense_quiver_trap/hard_distractor bucket or negative/hard_distractor/dense_false_positive tag -> supporting_only if dense/graph support; else apply_llm_filter
- ambiguous/hallucination_risk bucket or tag -> weak_candidate_only if strong span agreement and query_noise <= 0.2; supporting_only if dense/graph support; else apply_llm_filter
- exact_unique_symbol_anchor + symbol_anchor + query_noise <= 0.1 -> admit_symbol_regex_union
- symbol_regex_agree_span + positive bucket + query_noise <= 0.2 + no negative tags -> admit_symbol_regex_union
- symbol_regex_agree_file only + positive bucket + query_noise <= 0.2 + no negative tags -> weak_candidate_only
- rrf_anchor_agree_span + positive bucket + query_noise <= 0.2 + no negative tags -> admit_rrf_primary
- rrf_anchor_agree_file only + positive bucket + query_noise <= 0.2 + no negative tags -> weak_candidate_only
- llm_span_narrow_valid + within_candidate + (symbol_regex_agree_span or rrf_anchor_agree_span or exact_unique_symbol_anchor) + positive bucket + query_noise <= 0.2 + no negative tags -> admit_llm_span_narrow
- remaining local_anchor -> weak_candidate_only
- dense_support_present or graph_support_present -> supporting_only
- otherwise -> abstain

## Per-task routing (self-test only)

| task_id | repo_id | task_bucket | task_risk_tags | v3_action | v3_score | h1_action | h1_score | h2_action | h2_score |
|---|---|---|---|---|---|---|---|---|---|
| p30-001 | py_flask | exact_symbol_unique | exact_symbol, unique_symbol, high_confidence | admit_symbol_regex_union | 5 | admit_symbol_regex_union | 5 | admit_symbol_regex_union | 5 |
| p30-002 | py_flask | positive | symbol_anchor, route_handler | admit_symbol_regex_union | 3 | admit_symbol_regex_union | 3 | weak_candidate_only | 3 |
| p30-003 | js_express | positive | likely_positive | admit_symbol_regex_union | 3 | admit_symbol_regex_union | 3 | weak_candidate_only | 3 |
| p30-004 | py_flask | positive | high_confidence | admit_rrf_primary | 3 | admit_rrf_primary | 3 | weak_candidate_only | 3 |
| p30-005 | js_express | positive | likely_positive | admit_llm_span_narrow | 3 | admit_llm_span_narrow | 3 | abstain | 3 |
| p30-006 | js_express | config | config, positive | abstain | 1 | abstain | 1 | weak_candidate_only | 1 |
| p30-007 | js_express | negative | negative | abstain | -7 | abstain | -7 | apply_llm_filter | -7 |
| p30-008 | js_express | negative | negative | abstain | -7 | abstain | -7 | apply_llm_filter | -7 |
| p30-009 | py_flask | dense_quiver_trap | dense_false_positive | supporting_only | -6 | supporting_only | -6 | supporting_only | -6 |
| p30-010 | js_express | dense_quiver_trap | dense_false_positive, hard_distractor | supporting_only | -7 | supporting_only | -7 | supporting_only | -7 |
| p30-011 | py_flask | ambiguous | ambiguous, weak_candidates | abstain | -6 | abstain | -6 | apply_llm_filter | -6 |
| p30-012 | js_express | ambiguous | ambiguous, hallucination_risk | abstain | -7 | abstain | -7 | apply_llm_filter | -7 |
| p30-013 | py_flask | ambiguous | weak_candidates | abstain | -6 | abstain | -6 | apply_llm_filter | -6 |
| p30-014 | js_express | unknown | other | weak_candidate_only | -1 | weak_candidate_only | -1 | abstain | -1 |

## Conclusion

- Self-test-only scaffold evaluated 14 synthetic tasks; this is not quality evidence.
- admission_v3 uses an explainable monotonic scorecard over pre-SCORE observable task_bucket, task_risk_tags, and route_features; it does not use score_group, has_gold, gold, or outcome metrics during routing.
- Baseline SpanF0.5=0.14285714285714285, PFP=0.18571428571428572; admission_v3 SpanF0.5=0.10142857142857144, PFP=0.042857142857142864.
- admission_v3_h1 (handoff enriched) SpanF0.5=0.1457142857142857, PFP=0.023571428571428573, quality_comparable=True, selected_action_fallback_rate=0.0.
- admission_v3_h2 (strict local anchor) SpanF0.5=0.060000000000000005, PFP=0.03571428571428571, quality_comparable=True, selected_action_fallback_rate=0.0.
- No policy is promotion-ready or default-ready.
- admission_v3_h1 is a handoff-enrichment diagnostic over P30-H1 records with local-anchor measured outcomes; a non-zero fallback rate on legacy admission_v3 preserves the old missing-outcome behavior for comparison.
- admission_v3_h2 is a stricter local-anchor policy over the same P30-H1 records; it should be fallback-free whenever enriched local-anchor outcomes are present for every selected action.
- Next: compare admission_v3_h1 and admission_v3_h2 to P25 real smoke and P22/P23 guard surfaces in ephemeral remote runs.
- admission_v3 relied on fallback outcomes for 7 action selections; real runs should include measured outcomes for every selected action.

## Safety notes

- No remote model calls were made during admission evaluation.
- Routing uses only RUN-phase public task metadata; labels/gold are used only for aggregate scoring after actions are fixed.
- This report contains only public task metadata, strategy/action names, and aggregate metrics.
- Raw queries, snippets, prompts, responses, gold spans, private labels, provider keys, and provider fields are not stored.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `external_calls=0`.
