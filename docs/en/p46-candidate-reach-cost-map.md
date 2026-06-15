# P46 Candidate Reach × Cost / Candidate-to-Evidence Materialization Gate

- Schema: `p46-candidate-reach-cost-map-v1`
- Generated: 2026-06-15T14:07:08.090388+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P46: 0
- Candidate pool availability: `partial`
- Gold span availability: `available`
- Reach metrics available: True
- Materialization availability: `source_read_unavailable`
- Tasks: 4 positive=3 no_gold=1

## Purpose

P46 measures how much candidate evidence reaches private gold spans (`reach`) and how much span-level false risk each strategy incurs (`cost`).  It is a SCORE-phase-only diagnostic that uses the P31-H1 candidate-pool handoff and P33-B subtype handoff, but never emits per-task rows.

## Methodology

- Reads `p25-policy-records-ephemeral-v1` records produced by `p21_llm_rich_candidate.py`.
- Computes aggregate reach@K (GoldFile, GoldSpan, UniqueGoldSpan) per strategy.
- Computes outcome span-cost metrics (added_gold_span, added_false_span, false/gold, net value 1x/2x, SpanF0.5, PFP).
- Includes candidate materialization diagnostics from pool metadata; source-file validation defaults to unavailable unless a checkout root is provided.
- Breaks down reach/cost by public task bucket, risk tag, and P33-B subtype axes when available.
- Replays `bucket_routed_v0` and `admission_v3_h4b` routing decisions to expose route span cost.

## Current placeholder findings

- This report is `self_test_only`; do not use it as quality evidence.
- Reach metrics available: True.
- Materialization source-read availability: `source_read_unavailable`.
- Policy route evaluation: False.

## Outcome cost map by strategy

| Strategy | tasks | +task | no_gold | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | mean SpanF0.5 | mean PFP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 4 | 3 | 1 | 3 | 9 | 3.0000 | 0.3333 | -6 | -15 | 0.1450 | 0.2050 |
| rrf_primary | 4 | 3 | 1 | 2 | 5 | 2.5000 | 0.4000 | -3 | -8 | 0.1650 | 0.1150 |
| symbol_primary | 4 | 3 | 1 | 1 | 0 | 0.0000 | n/a | 1 | 1 | 0.2500 | 0.0500 |
| regex_primary | 4 | 3 | 1 | 0 | 0 | n/a | n/a | 0 | 0 | 0.0000 | 0.0000 |
| symbol_regex_union | 4 | 3 | 1 | 2 | 1 | 0.5000 | 2.0000 | 1 | 0 | 0.1667 | 0.0000 |
| llm_span_narrow | 4 | 3 | 1 | 2 | 2 | 1.0000 | 1.0000 | 0 | -2 | 0.2200 | 0.0750 |
| llm_filter | 4 | 3 | 1 | 0 | 0 | n/a | n/a | 0 | 0 | 0.0667 | 0.0000 |
| llm_abstain_filter | 4 | 3 | 1 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| supporting_only | 4 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| weak_candidate_only | 4 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Reach × cost map by strategy and K

| Strategy | K | GoldFileReach | GoldSpanReach | UniqueGoldSpanReach | CandidateAbsent | FileRightSpanWrong |
|---|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 1 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| candidate_baseline | 3 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| candidate_baseline | 5 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| candidate_baseline | 10 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| candidate_baseline | 20 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| rrf_primary | 1 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| rrf_primary | 3 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| rrf_primary | 5 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| rrf_primary | 10 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| rrf_primary | 20 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| symbol_primary | 1 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| symbol_primary | 3 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| symbol_primary | 5 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| symbol_primary | 10 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| symbol_primary | 20 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| regex_primary | 1 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |
| regex_primary | 3 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |
| regex_primary | 5 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |
| regex_primary | 10 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |
| regex_primary | 20 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |
| symbol_regex_union | 1 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| symbol_regex_union | 3 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| symbol_regex_union | 5 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| symbol_regex_union | 10 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| symbol_regex_union | 20 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| llm_span_narrow | 1 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| llm_span_narrow | 3 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| llm_span_narrow | 5 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| llm_span_narrow | 10 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| llm_span_narrow | 20 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| llm_filter | 1 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| llm_filter | 3 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| llm_filter | 5 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| llm_filter | 10 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| llm_filter | 20 | 1.0000 | 0.5000 | 0.0000 | 0.0000 | 0.5000 |
| llm_abstain_filter | 1 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |
| llm_abstain_filter | 3 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |
| llm_abstain_filter | 5 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |
| llm_abstain_filter | 10 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |
| llm_abstain_filter | 20 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |

## Unique span reach@5

| Strategy | GoldSpanReach | UniqueGoldSpanReach | UniqueShare |
|---|---:|---:|---:|
| candidate_baseline | 0.5000 | 0.0000 | 0.0000 |
| rrf_primary | 0.5000 | 0.0000 | 0.0000 |
| symbol_primary | 1.0000 | 0.0000 | 0.0000 |
| regex_primary | 0.0000 | 0.0000 | n/a |
| symbol_regex_union | 0.5000 | 0.0000 | 0.0000 |
| llm_span_narrow | 0.5000 | 0.0000 | 0.0000 |
| llm_filter | 0.5000 | 0.0000 | 0.0000 |
| llm_abstain_filter | 0.0000 | 0.0000 | n/a |

## Materialization diagnostics

- Overall availability: `source_read_unavailable`
- Overall: candidates_seen=14, materialized_valid=0, materialization_rate=n/a
- Note: Source-file materialization validation is currently not wired by default. P46 reports `source_read_unavailable` unless the ephemeral record explicitly carries a private checkout root.

### Materialization by strategy

| Strategy | availability | seen | valid | invalid_path | invalid_range | stale_sha | missing_file | other | rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | source_read_unavailable | 4 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| rrf_primary | source_read_unavailable | 2 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| symbol_primary | source_read_unavailable | 1 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| regex_primary | missing_pool | - | - | - | - | - | - | - | n/a |
| symbol_regex_union | source_read_unavailable | 3 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| llm_span_narrow | source_read_unavailable | 2 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| llm_filter | source_read_unavailable | 2 | 0 | 0 | 0 | 0 | 0 | 0 | n/a |
| llm_abstain_filter | missing_pool | - | - | - | - | - | - | - | n/a |

## Public bucket breakdown@5 (symbol_regex_union)

| Bucket | tasks | pos | no_gold | GoldFileReach | GoldSpanReach | added_gold | added_false | net_1x |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ambiguous | 1 | 1 | 0 | n/a | n/a | n/a | n/a | n/a |
| negative | 1 | 0 | 1 | n/a | n/a | 0 | 0 | 0 |
| positive | 2 | 2 | 0 | 1.0000 | 0.5000 | 2 | 1 | 1 |

## P33-B subtype combination breakdown@5 (symbol_regex_union)

| Combination | tasks | pos | no_gold | GoldFileReach | GoldSpanReach | added_gold | added_false | net_1x |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| symbol_only__single_source__rrf_no | 1 | 1 | 0 | 1.0000 | 0.0000 | 1 | 1 | 0 |
| symbol_regex_fusion__span_overlap__rrf_yes | 1 | 1 | 0 | 1.0000 | 1.0000 | 1 | 0 | 1 |

## Policy route snapshots

### bucket_routed_v0 (`partial_missing_cost_fields`)

- selected_task_count=4, selected_with_outcome=4, selected_missing_outcome=0, outcome_fallback_rate=0.0, selected_with_cost=3, selected_missing_cost=1, cost_fallback_rate=0.25
| Action | availability | selected | cost_present | cost_missing | added_gold | added_false | false/gold | net_1x |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| llm_abstain_filter | missing_cost_fields | 1 | 0 | 1 | n/a | n/a | n/a | n/a |
| llm_filter | available | 1 | 1 | 0 | 0 | 0 | n/a | 0 |
| llm_span_narrow | available | 2 | 2 | 0 | 2 | 2 | 1.0000 | 0 |

### admission_v3_h4b (`partial_missing_cost_fields`)

- selected_task_count=4, selected_with_outcome=2, selected_missing_outcome=2, outcome_fallback_rate=0.5, selected_with_cost=2, selected_missing_cost=2, cost_fallback_rate=0.5
| Action | availability | selected | cost_present | cost_missing | added_gold | added_false | false/gold | net_1x |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| admit_symbol_regex_union | available | 1 | 1 | 0 | 1 | 0 | 0.0000 | 1 |
| apply_llm_filter | available | 1 | 1 | 0 | 0 | 0 | n/a | 0 |
| weak_candidate_only | missing_cost_fields | 2 | 0 | 2 | n/a | n/a | n/a | n/a |

## Conclusion

- Self-test-only scaffold evaluated 4 synthetic tasks; this is not quality evidence.
- P46 is SCORE-phase-only. Candidate pools and private gold spans were used only for aggregate metrics after RUN.
- Baseline@5 GoldFileReach=1.0, GoldSpanReach=0.5, CandidateAbsentRate=0.0, FileRightSpanWrongRate=0.5.
- Materialization diagnostics: source_read_unavailable. Source-file materialization validation is currently not wired by default; P46 reports source_read_unavailable unless the ephemeral record explicitly carries a private checkout root.
- Outcome cost map available for 8 strategies.
- P33-B subtype breakdowns cover 2 tasks.
- No policy is promotion-ready or default-ready.
- Next: P47/P48 should consume this aggregate map to test evidence-materialization gates and budget-aware admission thresholds.

## Safety notes

- No remote model calls were made during P46 evaluation.
- This report contains only aggregate counts/rates by strategy, public bucket, risk tag, and subtype axis.
- No task IDs, candidate IDs, paths, spans, gold spans, private labels, route features, snippets, prompts, responses, or provider keys are stored.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `remote_calls_by_p46=0`, `score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`.
