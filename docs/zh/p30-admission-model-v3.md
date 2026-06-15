# P30 Admission Model V3 Report

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# P30 Admission Model V3 Report

- Schema: `p30-admission-v3-report-v1`
- Generated: 2026-06-15T12:06:15.305533+00:00
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
| admission_v3_h4 | P33-B anchor-subtype deterministic budget overlay; demotes all primary-admit candidates based on subtype agreement_class, never promotes from subtype evidence alone, and remains a diagnostic-only non-default lane. |
| admission_v3_h4b | P33-B selective primary re-admission diagnostic; extremely narrow strict gate allows `admit_symbol_regex_union` or `admit_rrf_primary` only when fusion/span/RRF/public-anchor conditions all hold; everything else is hard-guarded or demoted to non-primary actions. |

## Aggregate results

| Policy | tasks | +tasks | no_gold | SpanF0.5 | PFP | no_gold PFP | added_gold | added_false | filter_kill_rate | abstain_rate | selective_risk |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 23 | 18 | 5 | 0.1565 | 0.1652 | 0.4000 | 18 | 56 | 0.0000 | 0.0000 | n/a |
| llm_span_narrow | 23 | 18 | 5 | 0.2504 | 0.1043 | 0.3000 | 18 | 33 | 0.0000 | 0.0000 | n/a |
| llm_filter | 23 | 18 | 5 | 0.0939 | 0.0217 | 0.1000 | 0 | 5 | 1.0000 | 0.0000 | n/a |
| llm_abstain_filter | 23 | 18 | 5 | 0.0783 | 0.0109 | 0.0500 | 0 | 0 | 1.0000 | 1.0000 | n/a |
| bucket_routed_v0 | 23 | 18 | 5 | 0.2000 | 0.0522 | 0.0700 | 14 | 19 | 0.2222 | 0.1304 | n/a |
| admission_v3 | 23 | 18 | 5 | 0.1139 | 0.0457 | 0.0400 | 9 | 17 | 0.5000 | 0.4783 | 0.0238 |
| admission_v3_h1 | 23 | 18 | 5 | 0.1600 | 0.0235 | 0.0400 | 9 | 8 | 0.5000 | 0.4783 | 0.0122 |
| admission_v3_h2 | 23 | 18 | 5 | 0.1113 | 0.0326 | 0.0800 | 5 | 11 | 0.7222 | 0.0870 | 0.0298 |
| admission_v3_h4 | 23 | 18 | 5 | 0.0157 | 0.0391 | 0.0800 | 0 | 14 | 1.0000 | 0.0000 | 0.0391 |
| admission_v3_h4b | 23 | 18 | 5 | 0.0374 | 0.0426 | 0.0600 | 2 | 19 | 0.8889 | 0.0000 | 0.0426 |

## Quality comparability

| Policy | quality_comparable | blocked_by_missing_action_outcomes | selected_action_fallback_rate |
|---|---:|---:|---:|
| admission_v3 | False | True | 0.4783 |
| admission_v3_h1 | True | False | 0.0000 |
| admission_v3_h2 | True | False | 0.0000 |
| admission_v3_h4 | True | False | 0.0000 |
| admission_v3_h4b | True | False | 0.0000 |

## Deltas vs candidate baseline

| Policy | SpanF0.5 | PFP | added_gold | added_false |
|---|---:|---:|---:|---:|
| candidate_baseline | 0.0000 | 0.0000 | 0 | 0 |
| llm_span_narrow | 0.0939 | -0.0609 | 0 | -23 |
| llm_filter | -0.0626 | -0.1435 | -18 | -51 |
| llm_abstain_filter | -0.0783 | -0.1543 | -18 | -56 |
| bucket_routed_v0 | 0.0435 | -0.1130 | -4 | -37 |
| admission_v3 | -0.0426 | -0.1196 | -9 | -39 |
| admission_v3_h1 | 0.0035 | -0.1417 | -9 | -48 |
| admission_v3_h2 | -0.0452 | -0.1326 | -13 | -45 |
| admission_v3_h4 | -0.1409 | -0.1261 | -18 | -42 |
| admission_v3_h4b | -0.1191 | -0.1226 | -16 | -37 |

## Deltas vs bucket_routed_v0

| Policy | SpanF0.5 | PFP | added_gold | added_false |
|---|---:|---:|---:|---:|
| candidate_baseline | -0.0435 | 0.1130 | 4 | 37 |
| llm_span_narrow | 0.0504 | 0.0522 | 4 | 14 |
| llm_filter | -0.1061 | -0.0304 | -14 | -14 |
| llm_abstain_filter | -0.1217 | -0.0413 | -14 | -19 |
| bucket_routed_v0 | 0.0000 | 0.0000 | 0 | 0 |
| admission_v3 | -0.0861 | -0.0065 | -5 | -2 |
| admission_v3_h1 | -0.0400 | -0.0287 | -5 | -11 |
| admission_v3_h2 | -0.0887 | -0.0196 | -9 | -8 |
| admission_v3_h4 | -0.1843 | -0.0130 | -14 | -5 |
| admission_v3_h4b | -0.1626 | -0.0096 | -12 | 0 |

## admission_v3 action distribution

| Action | Count | Rate |
|---:|---:|---:|
| abstain | 11 | 0.4782608695652174 |
| admit_llm_span_narrow | 1 | 0.043478260869565216 |
| admit_rrf_primary | 3 | 0.13043478260869565 |
| admit_symbol_regex_union | 5 | 0.21739130434782608 |
| apply_llm_filter | 0 | n/a |
| supporting_only | 2 | 0.08695652173913043 |
| weak_candidate_only | 1 | 0.043478260869565216 |

## admission_v3_h1 action distribution

| Action | Count | Rate |
|---:|---:|---:|
| abstain | 11 | 0.4782608695652174 |
| admit_llm_span_narrow | 1 | 0.043478260869565216 |
| admit_rrf_primary | 3 | 0.13043478260869565 |
| admit_symbol_regex_union | 5 | 0.21739130434782608 |
| apply_llm_filter | 0 | n/a |
| supporting_only | 2 | 0.08695652173913043 |
| weak_candidate_only | 1 | 0.043478260869565216 |

## admission_v3_h2 action distribution

| Action | Count | Rate |
|---:|---:|---:|
| abstain | 2 | 0.08695652173913043 |
| admit_llm_span_narrow | 0 | n/a |
| admit_rrf_primary | 0 | n/a |
| admit_symbol_regex_union | 5 | 0.21739130434782608 |
| apply_llm_filter | 7 | 0.30434782608695654 |
| supporting_only | 2 | 0.08695652173913043 |
| weak_candidate_only | 7 | 0.30434782608695654 |

## admission_v3_h4 action distribution

| Action | Count | Rate |
|---:|---:|---:|
| abstain | 0 | n/a |
| admit_llm_span_narrow | 0 | n/a |
| admit_rrf_primary | 0 | n/a |
| admit_symbol_regex_union | 0 | n/a |
| apply_llm_filter | 7 | 0.30434782608695654 |
| supporting_only | 6 | 0.2608695652173913 |
| weak_candidate_only | 10 | 0.43478260869565216 |

## admission_v3_h4b action distribution

| Action | Count | Rate |
|---:|---:|---:|
| abstain | 0 | n/a |
| admit_llm_span_narrow | 0 | n/a |
| admit_rrf_primary | 1 | 0.043478260869565216 |
| admit_symbol_regex_union | 1 | 0.043478260869565216 |
| apply_llm_filter | 3 | 0.13043478260869565 |
| supporting_only | 2 | 0.08695652173913043 |
| weak_candidate_only | 16 | 0.6956521739130435 |

## admission_v3_h4b rule counts

| Rule | Count |
|---:|---:|
| demote_same_file | 1 |
| demote_span_overlap | 3 |
| filter_dangerous_subtype | 1 |
| hard_guard | 2 |
| missing_handoff | 14 |
| other | 0 |
| strict_rrf_re_admit | 1 |
| strict_union_re_admit | 1 |

- H4B primary opportunities: 2

## Score bands (admission_v3)

Bands are scorecard score ranges, not held-out calibrated probabilities. They show how aggregate metrics vary with the deterministic scorecard score.

| Band | count | +count | no_gold | frac_positive | SpanF0.5 | PFP |
|---|---:|---:|---:|---:|---:|---:|
| hard_guard | 9 | 4 | 5 | 0.4444 | 0.0333 | 0.0222 |
| high_admit | 9 | 9 | 0 | 1.0000 | 0.2133 | 0.0944 |
| medium_admit | 4 | 4 | 0 | 1.0000 | 0.1000 | 0.0000 |
| neutral | 1 | 1 | 0 | 1.0000 | 0.0000 | 0.0000 |

## Outcome fallback caveat

- Missing action outcomes for admission_v3: 11
- Missing action outcomes for admission_v3_h1: 0
- Missing action outcomes for admission_v3_h2: 0
- Missing action outcomes for admission_v3_h4: 0
- Missing action outcomes for admission_v3_h4b: 0
- Fallback strategy counts (admission_v3): {'candidate_baseline': 8, 'zero_primary': 3}
- Fallback strategy counts (admission_v3_h1): {}
- Fallback strategy counts (admission_v3_h2): {}
- Fallback strategy counts (admission_v3_h4): {}
- Fallback strategy counts (admission_v3_h4b): {}
- If an action selected by admission_v3 has no measured outcome in the input record, the evaluator falls back to `candidate_baseline` for primary-admit actions or a zero-primary surrogate for `abstain`/`supporting_only`/`weak_candidate_only`. Real evaluation should use ephemeral records that include outcomes for every action the model can select.
- admission_v3_h1 is designed to have zero missing outcomes when P21 writes P30-H1 enriched handoff records; a non-zero value here indicates the input records lack the required local-anchor outcomes.
- admission_v3_h2 is designed to be fallback-free on P30-H1 records because it selects only from the local-anchor measured outcomes already included in the handoff; a non-zero value here indicates the input records are missing outcomes for actions H2 selects.
- admission_v3_h4 requires measured outcomes for apply_llm_filter, supporting_only, and weak_candidate_only because it does not select primary-admit actions; a non-zero value here indicates the input P33-B handoff lacks outcomes for H4-selected actions.
- admission_v3_h4b requires measured outcomes for apply_llm_filter, supporting_only, weak_candidate_only, admit_symbol_regex_union, and admit_rrf_primary; a non-zero value here indicates the input handoff lacks outcomes for H4B-selected actions.

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

## Routing rules (admission_v3_h4)

- negative/dense_quiver_trap/hard_distractor or deeply penalized score -> supporting_only if dense/graph support; else apply_llm_filter
- ambiguous/hallucination_risk bucket or tag -> weak_candidate_only if span_overlap and no negative; supporting_only if span_overlap+RRF and no negative; supporting_only if dense/graph support; else apply_llm_filter
- exact_unique_symbol_anchor + low query_noise + clear positive bucket -> weak_candidate_only (budget diagnostic); filter otherwise
- span_overlap best subtype in non-negative/ambiguous bucket -> supporting_only if RRF-backed; weak_candidate_only if low-risk public bucket; else apply_llm_filter
- same_file_only subtype -> weak_candidate_only in low-risk public bucket; else apply_llm_filter
- disagree/single_source subtype -> weak_candidate_only only in clearly positive/low-noise public buckets; else apply_llm_filter
- missing P33-B subtype metadata -> conservative weak_candidate_only/supporting_only/apply_llm_filter fallback comparable to bucket-routed behavior
- dense/graph support without usable subtype -> supporting_only
- otherwise -> weak_candidate_only

## Routing rules (admission_v3_h4b)

- negative/dense_quiver_trap/hard_distractor/ambiguous/hallucination_risk or query_noise>0.2 => non-primary (apply_llm_filter/weak_candidate_only)
- missing P33-B subtype handoff => weak_candidate_only (missing_handoff)
- top subtype regex_only / same_file_only / disagree / single_source => non-primary (hard_guard/demote_same_file/filter_dangerous_subtype)
- strict primary re-admit: top subtype is symbol_regex_fusion + span_overlap + rrf_backing + local_anchor + symbol_regex_agree_span + query_noise<=0.1 + low-risk public bucket/tag + (exact_unique_symbol_anchor or rrf_anchor_agree_span) => admit_symbol_regex_union
- optional strict RRF re-admit: same strict gate + rrf_backed_by_anchor + rrf_anchor_agree_span => admit_rrf_primary
- span_overlap fusion failing strict gate => supporting_only (RRF-backed) or weak_candidate_only/filter
- symbol_only or remaining cases => weak_candidate_only

## Conclusion

- Self-test-only scaffold evaluated 23 synthetic tasks; this is not quality evidence.
- admission_v3 uses an explainable monotonic scorecard over pre-SCORE observable task_bucket, task_risk_tags, and route_features; it does not use score_group, has_gold, gold, or outcome metrics during routing.
- Baseline SpanF0.5=0.1565217391304348, PFP=0.16521739130434784; admission_v3 SpanF0.5=0.11391304347826088, PFP=0.04565217391304348.
- admission_v3_h1 (handoff enriched) SpanF0.5=0.16, PFP=0.02347826086956522, quality_comparable=True, selected_action_fallback_rate=0.0.
- admission_v3_h2 (strict local anchor) SpanF0.5=0.11130434782608696, PFP=0.03260869565217391, quality_comparable=True, selected_action_fallback_rate=0.0.
- admission_v3_h4 (P33-B budget overlay) SpanF0.5=0.015652173913043476, PFP=0.0391304347826087, quality_comparable=True, selected_action_fallback_rate=0.0.
- admission_v3_h4b (P33-B selective re-admission) SpanF0.5=0.03739130434782609, PFP=0.042608695652173914, quality_comparable=True, selected_action_fallback_rate=0.0, primary_opportunities=2.
- No policy is promotion-ready or default-ready.
- admission_v3_h1 is a handoff-enrichment diagnostic over P30-H1 records with local-anchor measured outcomes; a non-zero fallback rate on legacy admission_v3 preserves the old missing-outcome behavior for comparison.
- admission_v3_h2 is a stricter local-anchor policy over the same P30-H1 records; it should be fallback-free whenever enriched local-anchor outcomes are present for every selected action.
- Next: compare admission_v3_h1 and admission_v3_h2 to P25 real smoke and P22/P23 guard surfaces in ephemeral remote runs.
- admission_v3 relied on fallback outcomes for 11 action selections; real runs should include measured outcomes for every selected action.

## Safety notes

- No remote model calls were made during admission evaluation.
- Routing uses only RUN-phase public task metadata and private P33-B subtype handoff fields; labels/gold are used only for aggregate scoring after actions are fixed, and private handoff fields are never emitted publicly.
- This report contains only public task metadata, strategy/action names, and aggregate metrics.
- Raw queries, snippets, prompts, responses, gold spans, private labels, provider keys, subtype rows, and provider fields are not stored.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `external_calls=0`, `h4_budget_overlay=true`, `h4b_budget_overlay=true`, `h4b_selective_readmission=true`.
