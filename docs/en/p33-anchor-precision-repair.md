# P33 Reach-Preserving Precision Anchor Repair

- Schema: `p33-anchor-precision-repair-report-v1`
- Generated: 2026-06-14T18:59:49.693099+00:00
- Status: `ok`
- Self-test: False
- Remote calls by P33: 0
- P31-H1 handoff detected: True
- P33 available: True

- Tasks: 3 positive=2 no_gold=1
- Positive tasks with pools: 2

## Bucket taxonomy diagnostics@5

| Bucket | tasks | pos | no_gold | GoldFileReach | GoldSpanReach | FRSW | false/gold | net1x | diagnostic_class |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| exact_unique_symbol_anchor | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| unique_symbol_anchor | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_anchor_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_anchor_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_agree_span | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.0000 | 3.0000 | -2 | insufficient_denominator |
| symbol_regex_agree_file | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_disagree | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| rrf_anchor_agree_span | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.0000 | 3.0000 | -2 | insufficient_denominator |
| rrf_anchor_agree_file | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| rrf_unbacked | 2 | 1 | 1 | 0.0000 | 0.0000 | n/a | n/a | 0 | insufficient_denominator |
| positive_bucket | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| ambiguous_bucket | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| negative_bucket | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| hard_distractor_tag | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| dense_false_positive_tag | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| query_noise_low | 3 | 2 | 1 | 0.5000 | 0.5000 | 0.0000 | 3.0000 | -2 | insufficient_denominator |
| query_noise_medium | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| query_noise_high | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_agree_span_low_risk | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_agree_file_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| rrf_span_backed | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.0000 | 3.0000 | -2 | insufficient_denominator |
| rrf_file_backed_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| negative_or_ambiguous_with_anchor | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |

## Baseline comparison (`candidate_baseline`)@5

| Bucket | tasks | pos | no_gold | GoldFileReach | GoldSpanReach | FRSW | false/gold | net1x | diagnostic_class |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| exact_unique_symbol_anchor | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| unique_symbol_anchor | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_anchor_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_anchor_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_agree_span | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 1 | insufficient_denominator |
| symbol_regex_agree_file | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_disagree | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| rrf_anchor_agree_span | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 1 | insufficient_denominator |
| rrf_anchor_agree_file | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| rrf_unbacked | 2 | 1 | 1 | 0.0000 | 0.0000 | n/a | n/a | 0 | insufficient_denominator |
| positive_bucket | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| ambiguous_bucket | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| negative_bucket | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| hard_distractor_tag | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| dense_false_positive_tag | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| query_noise_low | 3 | 2 | 1 | 0.5000 | 0.5000 | 0.0000 | 0.0000 | 1 | insufficient_denominator |
| query_noise_medium | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| query_noise_high | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_agree_span_low_risk | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_agree_file_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| rrf_span_backed | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 1 | insufficient_denominator |
| rrf_file_backed_only | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| negative_or_ambiguous_with_anchor | 0 | - | - | n/a | n/a | n/a | n/a | n/a | missing_bucket |

## Calibration matrix@5

Calibration axes: ``a`` = anchor strength (0=none, 1=symbol_or_regex_only, 2=file_agreement, 3=span_agreement, 4=exact_unique_symbol_span_agreement); ``r`` = risk level (0=low/positive, 1=ambiguous, 2=negative/high risk); ``s`` = RRF backing level (0=none, 1=file-only, 2=span).

| Cell | tasks | GoldFileReach | GoldSpanReach | FRSW | net1x | diagnostic_class |
|---|---:|---:|---:|---:|---:|
| a0_r0_s0 | 2 | 0.0000 | 0.0000 | n/a | 0 | insufficient_denominator |
| a0_r0_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a0_r0_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a0_r1_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a0_r1_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a0_r1_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a0_r2_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a0_r2_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a0_r2_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a1_r0_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a1_r0_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a1_r0_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a1_r1_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a1_r1_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a1_r1_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a1_r2_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a1_r2_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a1_r2_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a2_r0_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a2_r0_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a2_r0_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a2_r1_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a2_r1_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a2_r1_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a2_r2_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a2_r2_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a2_r2_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a3_r0_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a3_r0_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a3_r0_s2 | 1 | 1.0000 | 1.0000 | 0.0000 | -2 | insufficient_denominator |
| a3_r1_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a3_r1_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a3_r1_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a3_r2_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a3_r2_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a3_r2_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a4_r0_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a4_r0_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a4_r0_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a4_r1_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a4_r1_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a4_r1_s2 | 0 | n/a | n/a | n/a | n/a | empty |
| a4_r2_s0 | 0 | n/a | n/a | n/a | n/a | empty |
| a4_r2_s1 | 0 | n/a | n/a | n/a | n/a | empty |
| a4_r2_s2 | 0 | n/a | n/a | n/a | n/a | empty |


## P33-to-P32 handoff (budget candidates, not frozen policy)

- `primary_candidate_safe_observed`: (none)
- `supporting_only_observed`: (none)
- `needs_budget_guard`: query_noise_low, rrf_anchor_agree_span, rrf_span_backed, rrf_unbacked, symbol_regex_agree_span
- `blocked_high_false_cost`: (none)

## Conclusion

- P33 evaluated 3 real ephemeral records.
- P33-H1 handoff detected; 5/25 anchor taxonomy buckets have sufficient data. Diagnostics are aggregate-only and do not prescribe policy.
- No Rust core, EvidenceCore, default strategy, or remote change is made by P33.
- P33 is SCORE-phase-only; labels are loaded after RUN.

## Safety notes

- No remote model calls were made during P33 evaluation.
- Labels are loaded only after RUN for aggregate SCORE-phase metrics.
- This report contains only aggregate bucket diagnostics and public task metadata.
- Raw queries, snippets, prompts, responses, candidate paths/spans, gold spans, private labels, route features, and provider fields are not stored.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `remote_calls_by_p33=0`, `score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`.
