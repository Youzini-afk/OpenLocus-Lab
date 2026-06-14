# P25 Bucket-Routed LLM Role Policy Report

- Schema: `p25-bucket-policy-v1`
- Generated: 2026-06-14T09:23:23.494875+00:00
- Status: `self_test_only`
- Self-test: True

## Policies compared

| Policy | Description |
|---|---|
| candidate_baseline | No LLM; use local candidate baseline strategy. |
| global_span_narrow | Run `llm_span_narrow` on every task. |
| global_filter | Run `llm_filter` on every task. |
| global_abstain_filter | Run `llm_abstain_filter` on every task. |
| bucket_routed_v0 | Route by public `task_bucket`/`task_risk_tags`: span_narrow on positive/high-confidence buckets, filter/abstain on negative/dense-false-positive buckets, skip LLM for exact-symbol+unique-anchor tasks, fallback otherwise. |

## Aggregate results

| Policy | tasks | +tasks | no_gold | FileRecall@5 | SpanF0.5 | added_gold | added_false | PFP | no_gold PFP | filter_kill_rate | abstain_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 12 | 8 | 4 | 0.5250 | 0.1150 | 7 | 45 | 0.3250 | 0.5875 | 0.0000 | 0.0000 |
| global_span_narrow | 12 | 8 | 4 | 0.5250 | 0.1242 | 6 | 33 | 0.2375 | 0.4750 | 0.0000 | 0.0000 |
| global_filter | 12 | 8 | 4 | 0.5250 | 0.0850 | 0 | 9 | 0.0833 | 0.1875 | 0.8750 | 0.0000 |
| global_abstain_filter | 12 | 8 | 4 | 0.5250 | 0.0700 | 0 | 3 | 0.0500 | 0.1250 | 0.8750 | 1.0000 |
| bucket_routed_v0 | 12 | 8 | 4 | 0.5250 | 0.1225 | 5 | 12 | 0.0833 | 0.1500 | 0.2500 | 0.1667 |

## Success layers

| Policy | candidate_success | model_success | admission_success | evidence_success |
|---|---:|---:|---:|---:|
| candidate_baseline | 8 (66.67%) | 8 (66.67%) | 12 (100.00%) | 8 (66.67%) |
| global_span_narrow | 8 (66.67%) | 6 (50.00%) | 12 (100.00%) | 6 (50.00%) |
| global_filter | 8 (66.67%) | 5 (41.67%) | 12 (100.00%) | 1 (8.33%) |
| global_abstain_filter | 8 (66.67%) | 5 (41.67%) | 12 (100.00%) | 1 (8.33%) |
| bucket_routed_v0 | 8 (66.67%) | 10 (83.33%) | 12 (100.00%) | 6 (50.00%) |

## bucket_routed_v0 routing rules

- exact_symbol + unique symbol/symbol anchor -> candidate_baseline (skip LLM)
- positive/likely_positive/high_confidence/config/route_handler with support -> llm_span_narrow
- negative/dense_false_positive/ambiguous/hallucination_risk/weak_candidates -> fixed filter/abstain
- otherwise -> candidate_baseline
- Fixed negative strategy: `llm_abstain_filter`

## Per-task routing (self-test only)

| task_id | repo_id | task_bucket | task_risk_tags | action |
|---|---|---|---|---|
| p25-001 | py_flask | positive | high_confidence | llm_span_narrow |
| p25-002 | py_flask | positive | likely_positive, route_handler | llm_span_narrow |
| p25-003 | py_flask | exact_symbol_unique | exact_symbol, unique_symbol | candidate_baseline |
| p25-004 | js_express | config | config, positive | llm_span_narrow |
| p25-005 | js_express | negative | negative | llm_abstain_filter |
| p25-006 | js_express | negative | negative | llm_abstain_filter |
| p25-007 | js_express | dense_quiver_trap | dense_false_positive | llm_filter |
| p25-008 | js_express | dense_quiver_trap | dense_false_positive, hard_distractor | llm_filter |
| p25-009 | py_flask | ambiguous | ambiguous, weak_candidates | llm_filter |
| p25-010 | py_flask | ambiguous | ambiguous, hallucination_risk | llm_filter |
| p25-011 | py_flask | ambiguous | weak_candidates | llm_filter |
| p25-012 | js_express | unknown | other | candidate_baseline |

## Conclusion

- Self-test-only scaffold evaluated 12 synthetic tasks; this is not quality evidence.
- Bucket-routed v0 uses a priori negative strategy 'llm_abstain_filter' and routes span_narrow to likely-positive tasks.
- Baseline FileRecall@5=0.525, SpanF0.5=0.115; routed FileRecall@5=0.525, SpanF0.5=0.1225, PFP=0.08333333333333333.
- No policy is promotion-ready or default-ready.

## Safety notes

- No remote model calls were made during policy evaluation.
- This report contains only public task metadata, strategy names, and aggregate metrics.
- Raw queries, snippets, prompts, responses, gold spans, private labels, provider keys, and provider fields are not stored.
- `promotion_ready=false`, `default_should_change=false`, `external_calls=0`.
