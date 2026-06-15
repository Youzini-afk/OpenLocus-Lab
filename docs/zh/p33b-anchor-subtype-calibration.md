# p33b-anchor-subtype-calibration（中文镜像）

中文译本待补充；以下保留英文原文，确保 docs/en 与 docs/zh 文件级 1:1 镜像。

## English source / 英文原文

# P33-B Anchor Subtype Calibration

- Schema: `p33b-anchor-subtype-calibration-v1`
- Generated: 2026-06-15T08:59:26.550003+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P33-B: 0
- P31-H1 handoff detected: True
- P33-B handoff detected: True
- P33-B available: True

- Tasks: 5 positive=4 no_gold=1
- Positive tasks with union pool: 4
- Input summary: P31-H1=True, P33-B=True

## Subtype bucket diagnostics@5

| Bucket | tasks | pos | no_gold | GoldFileReach | GoldSpanReach | FRSW | UniqueSpan | false/gold | net1x | diagnostic_class |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| other__disagree__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__disagree__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__disagree__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__disagree__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__disagree__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__disagree__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__same_file_only__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__same_file_only__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__same_file_only__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__same_file_only__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__same_file_only__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__same_file_only__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__single_source__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__single_source__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__single_source__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__single_source__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__single_source__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__single_source__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__span_overlap__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__span_overlap__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__span_overlap__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__span_overlap__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__span_overlap__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| other__span_overlap__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__disagree__rrf_no__r0 | 1 | 1 | 0 | 0.0000 | 0.0000 | n/a | 0.0000 | 2.0000 | -1 | insufficient_denominator |
| regex_only__disagree__rrf_no__r1 | 1 | 1 | 0 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | n/a | 0 | insufficient_denominator |
| regex_only__disagree__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__disagree__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__disagree__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__disagree__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__same_file_only__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__same_file_only__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__same_file_only__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__same_file_only__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__same_file_only__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__same_file_only__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__single_source__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__single_source__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__single_source__rrf_no__r2 | 1 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | not_measured |
| regex_only__single_source__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__single_source__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__single_source__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__span_overlap__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__span_overlap__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__span_overlap__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__span_overlap__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__span_overlap__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| regex_only__span_overlap__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__disagree__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__disagree__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__disagree__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__disagree__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__disagree__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__disagree__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__same_file_only__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__same_file_only__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__same_file_only__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__same_file_only__rrf_yes__r0 | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 2.0000 | -1 | insufficient_denominator |
| symbol_only__same_file_only__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__same_file_only__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__single_source__rrf_no__r0 | 1 | 1 | 0 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | n/a | -2 | insufficient_denominator |
| symbol_only__single_source__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__single_source__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__single_source__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__single_source__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__single_source__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__span_overlap__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__span_overlap__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__span_overlap__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__span_overlap__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__span_overlap__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_only__span_overlap__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__disagree__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__disagree__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__disagree__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__disagree__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__disagree__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__disagree__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__same_file_only__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__same_file_only__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__same_file_only__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__same_file_only__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__same_file_only__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__same_file_only__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__single_source__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__single_source__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__single_source__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__single_source__rrf_yes__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__single_source__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__single_source__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__span_overlap__rrf_no__r0 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__span_overlap__rrf_no__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__span_overlap__rrf_no__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__span_overlap__rrf_yes__r0 | 1 | 1 | 0 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1 | insufficient_denominator |
| symbol_regex_fusion__span_overlap__rrf_yes__r1 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |
| symbol_regex_fusion__span_overlap__rrf_yes__r2 | 0 | - | - | n/a | n/a | n/a | n/a | n/a | n/a | missing_bucket |

## Calibration matrix@5

Calibration axes: ``s`` = source strength (0=regex_only, 1=symbol_only, 2=symbol_regex_fusion); ``m`` = match quality (0=disagree, 1=same_file_only, 2=span_overlap_unbacked, 3=span_overlap_rrf_backed); ``r`` = risk level (0=low/positive, 1=ambiguous, 2=negative/high risk).

| Cell | tasks | GoldFileReach | GoldSpanReach | FRSW | net1x | diagnostic_class |
|---|---:|---:|---:|---:|---:|
| s0_m0_r0 | 1 | 0.0000 | 0.0000 | n/a | -1 | insufficient_denominator |
| s0_m0_r1 | 1 | 1.0000 | 0.0000 | 1.0000 | 0 | insufficient_denominator |
| s0_m0_r2 | 1 | n/a | n/a | n/a | n/a | not_measured |
| s0_m1_r0 | 0 | n/a | n/a | n/a | n/a | empty |
| s0_m1_r1 | 0 | n/a | n/a | n/a | n/a | empty |
| s0_m1_r2 | 0 | n/a | n/a | n/a | n/a | empty |
| s0_m2_r0 | 0 | n/a | n/a | n/a | n/a | empty |
| s0_m2_r1 | 0 | n/a | n/a | n/a | n/a | empty |
| s0_m2_r2 | 0 | n/a | n/a | n/a | n/a | empty |
| s0_m3_r0 | 0 | n/a | n/a | n/a | n/a | empty |
| s0_m3_r1 | 0 | n/a | n/a | n/a | n/a | empty |
| s0_m3_r2 | 0 | n/a | n/a | n/a | n/a | empty |
| s1_m0_r0 | 1 | 1.0000 | 0.0000 | 1.0000 | -2 | insufficient_denominator |
| s1_m0_r1 | 0 | n/a | n/a | n/a | n/a | empty |
| s1_m0_r2 | 0 | n/a | n/a | n/a | n/a | empty |
| s1_m1_r0 | 1 | 1.0000 | 1.0000 | 0.0000 | -1 | insufficient_denominator |
| s1_m1_r1 | 0 | n/a | n/a | n/a | n/a | empty |
| s1_m1_r2 | 0 | n/a | n/a | n/a | n/a | empty |
| s1_m2_r0 | 0 | n/a | n/a | n/a | n/a | empty |
| s1_m2_r1 | 0 | n/a | n/a | n/a | n/a | empty |
| s1_m2_r2 | 0 | n/a | n/a | n/a | n/a | empty |
| s1_m3_r0 | 0 | n/a | n/a | n/a | n/a | empty |
| s1_m3_r1 | 0 | n/a | n/a | n/a | n/a | empty |
| s1_m3_r2 | 0 | n/a | n/a | n/a | n/a | empty |
| s2_m0_r0 | 0 | n/a | n/a | n/a | n/a | empty |
| s2_m0_r1 | 0 | n/a | n/a | n/a | n/a | empty |
| s2_m0_r2 | 0 | n/a | n/a | n/a | n/a | empty |
| s2_m1_r0 | 0 | n/a | n/a | n/a | n/a | empty |
| s2_m1_r1 | 0 | n/a | n/a | n/a | n/a | empty |
| s2_m1_r2 | 0 | n/a | n/a | n/a | n/a | empty |
| s2_m2_r0 | 0 | n/a | n/a | n/a | n/a | empty |
| s2_m2_r1 | 0 | n/a | n/a | n/a | n/a | empty |
| s2_m2_r2 | 0 | n/a | n/a | n/a | n/a | empty |
| s2_m3_r0 | 1 | 1.0000 | 1.0000 | 0.0000 | 1 | insufficient_denominator |
| s2_m3_r1 | 0 | n/a | n/a | n/a | n/a | empty |
| s2_m3_r2 | 0 | n/a | n/a | n/a | n/a | empty |

- **file_reach_non_increasing_with_risk** violations: s0_m0: r0->r1

## P33-B-to-P32 handoff (budget candidates, not frozen policy)

- `budget_candidate_observed`: (none)
- `supporting_only_observed`: (none)
- `needs_budget_guard`: regex_only__disagree__rrf_no__r0, regex_only__disagree__rrf_no__r1, symbol_only__same_file_only__rrf_yes__r0, symbol_only__single_source__rrf_no__r0, symbol_regex_fusion__span_overlap__rrf_yes__r0
- `blocked_high_false_cost`: (none)

## Conclusion

- Self-test-only scaffold evaluated 5 synthetic tasks; not quality evidence.
- P33-B handoff detected; 5/96 subtype buckets have sufficient data. Diagnostics are aggregate-only, coarse task-level attribution, and do not prescribe policy.
- No Rust core, EvidenceCore, default strategy, or remote change is made by P33-B.
- P33-B is SCORE-phase-only; labels are loaded after RUN.

## Safety notes

- No remote model calls were made during P33-B evaluation.
- Labels are loaded only after RUN for aggregate SCORE-phase metrics.
- This report contains only aggregate subtype diagnostics and public task metadata.
- Span cost attribution is coarse task-level attribution from symbol_regex_union outcomes, not per-candidate causation.
- Raw queries, snippets, prompts, responses, candidate paths/spans, gold spans, private labels, route features, subtype rows, and provider fields are not stored.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `remote_calls_by_p33b=0`, `score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`.
