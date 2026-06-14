# P30-H3 Action-Specific Span-Cost Accounting

- Schema: `p30-h3-action-span-cost-report-v1`
- Generated: 2026-06-14T14:29:54.425513+00:00
- Tasks: 14 (+10 / no_gold 4)
- Status: `score_phase_only_accounting=true`, `diagnostic_only=true`, `promotion_ready=false`, `default_should_change=false`.

## Budget policy (accounting-only)

- Primary-admit actions: `added_false_span <= added_gold_span` (budget=1.0 false/gold).
- Non-primary actions: `added_false_span == 0`.
- Unclassified baseline strategies: `added_false_span <= added_gold_span` (budget=1.0 false/gold).
- Accounting-only diagnostic budget. Primary admission actions are expected to keep added_false_span <= added_gold_span. Non-primary actions are expected to add zero false spans. Unclassified baseline strategy actions are expected to be net-neutral.

## Policy-level span-cost summary

| Policy | tasks | primary_false_cost | non_primary_false_cost | unclassified_false_cost | budget_violations | budget_violation_rate |
|---|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 14 | 0 | 0 | 36 | 14 | 1.0000 |
| llm_span_narrow | 14 | 0 | 0 | 22 | 14 | 1.0000 |
| llm_filter | 14 | 0 | 0 | 4 | 14 | 1.0000 |
| llm_abstain_filter | 14 | 0 | 0 | 0 | 0 | 0.0000 |
| bucket_routed_v0 | 14 | 0 | 0 | 11 | 7 | 0.5000 |
| admission_v3 | 14 | 3 | 1 | 0 | 2 | 0.1429 |
| admission_v3_h1 | 14 | 3 | 1 | 0 | 2 | 0.1429 |
| admission_v3_h2 | 14 | 0 | 7 | 0 | 9 | 0.6429 |

## Action span-cost table: candidate_baseline

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | unclassified | 14 | 1.0000 | 10 | 36 | 3.6000 | 0.2778 | -26 | -62 | 0 | 0 | True |

### Worst actions by false cost: candidate_baseline

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| candidate_baseline | unclassified | 14 | 36 | 10 | 3.6000 |

### Worst actions by gold kill: candidate_baseline

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| candidate_baseline | unclassified | 14 | 0 | 0.0000 |

## Action span-cost table: llm_span_narrow

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llm_span_narrow | unclassified | 14 | 1.0000 | 10 | 22 | 2.2000 | 0.4545 | -12 | -34 | 0 | 4 | True |

### Worst actions by false cost: llm_span_narrow

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_span_narrow | unclassified | 14 | 22 | 10 | 2.2000 |

### Worst actions by gold kill: llm_span_narrow

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_span_narrow | unclassified | 14 | 0 | 0.0000 |

## Action span-cost table: llm_filter

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llm_filter | unclassified | 14 | 1.0000 | 0 | 4 | n/a | 0.0000 | -4 | -8 | 10 | 4 | True |

### Worst actions by false cost: llm_filter

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_filter | unclassified | 14 | 4 | 0 | n/a |

### Worst actions by gold kill: llm_filter

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_filter | unclassified | 14 | 10 | 1.0000 |

## Action span-cost table: llm_abstain_filter

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llm_abstain_filter | unclassified | 14 | 1.0000 | 0 | 0 | n/a | n/a | 0 | 0 | 10 | 4 | False |

### Worst actions by false cost: llm_abstain_filter

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_abstain_filter | unclassified | 14 | 0 | 0 | n/a |

### Worst actions by gold kill: llm_abstain_filter

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_abstain_filter | unclassified | 14 | 10 | 1.0000 |

## Action span-cost table: bucket_routed_v0

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | unclassified | 2 | 0.1429 | 2 | 4 | 2.0000 | 0.5000 | -2 | -6 | 0 | 0 | True |
| llm_abstain_filter | unclassified | 2 | 0.1429 | 0 | 0 | n/a | n/a | 0 | 0 | 0 | 2 | False |
| llm_filter | unclassified | 5 | 0.3571 | 0 | 2 | n/a | 0.0000 | -2 | -4 | 3 | 2 | True |
| llm_span_narrow | unclassified | 5 | 0.3571 | 5 | 5 | 1.0000 | 1.0000 | 0 | -5 | 0 | 0 | False |

### Worst actions by false cost: bucket_routed_v0

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_span_narrow | unclassified | 5 | 5 | 5 | 1.0000 |
| candidate_baseline | unclassified | 2 | 4 | 2 | 2.0000 |
| llm_filter | unclassified | 5 | 2 | 0 | n/a |
| llm_abstain_filter | unclassified | 2 | 0 | 0 | n/a |

### Worst actions by gold kill: bucket_routed_v0

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_filter | unclassified | 5 | 3 | 1.0000 |
| candidate_baseline | unclassified | 2 | 0 | 0.0000 |
| llm_abstain_filter | unclassified | 2 | 0 | n/a |
| llm_span_narrow | unclassified | 5 | 0 | 0.0000 |

## Action span-cost table: admission_v3

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abstain | non_primary | 6 | 0.4286 | 0 | 0 | n/a | n/a | 0 | 0 | 3 | 3 | False |
| admit_llm_span_narrow | primary | 1 | 0.0714 | 1 | 1 | 1.0000 | 1.0000 | 0 | -1 | 0 | 0 | False |
| admit_rrf_primary | primary | 1 | 0.0714 | 1 | 2 | 2.0000 | 0.5000 | -1 | -3 | 0 | 0 | True |
| admit_symbol_regex_union | primary | 3 | 0.2143 | 3 | 0 | 0.0000 | n/a | 3 | 3 | 0 | 0 | False |
| supporting_only | non_primary | 2 | 0.1429 | 0 | 0 | n/a | n/a | 0 | 0 | 1 | 1 | False |
| weak_candidate_only | non_primary | 1 | 0.0714 | 0 | 1 | n/a | 0.0000 | -1 | -2 | 1 | 0 | True |

### Worst actions by false cost: admission_v3

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| admit_rrf_primary | primary | 1 | 2 | 1 | 2.0000 |
| admit_llm_span_narrow | primary | 1 | 1 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 0 | n/a |
| abstain | non_primary | 6 | 0 | 0 | n/a |
| admit_symbol_regex_union | primary | 3 | 0 | 3 | 0.0000 |

### Worst actions by gold kill: admission_v3

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| abstain | non_primary | 6 | 3 | 1.0000 |
| supporting_only | non_primary | 2 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 1.0000 |
| admit_llm_span_narrow | primary | 1 | 0 | 0.0000 |
| admit_rrf_primary | primary | 1 | 0 | 0.0000 |

## Action span-cost table: admission_v3_h1

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abstain | non_primary | 6 | 0.4286 | 0 | 0 | n/a | n/a | 0 | 0 | 3 | 3 | False |
| admit_llm_span_narrow | primary | 1 | 0.0714 | 1 | 1 | 1.0000 | 1.0000 | 0 | -1 | 0 | 0 | False |
| admit_rrf_primary | primary | 1 | 0.0714 | 1 | 2 | 2.0000 | 0.5000 | -1 | -3 | 0 | 0 | True |
| admit_symbol_regex_union | primary | 3 | 0.2143 | 3 | 0 | 0.0000 | n/a | 3 | 3 | 0 | 0 | False |
| supporting_only | non_primary | 2 | 0.1429 | 0 | 0 | n/a | n/a | 0 | 0 | 1 | 1 | False |
| weak_candidate_only | non_primary | 1 | 0.0714 | 0 | 1 | n/a | 0.0000 | -1 | -2 | 1 | 0 | True |

### Worst actions by false cost: admission_v3_h1

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| admit_rrf_primary | primary | 1 | 2 | 1 | 2.0000 |
| admit_llm_span_narrow | primary | 1 | 1 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 0 | n/a |
| abstain | non_primary | 6 | 0 | 0 | n/a |
| admit_symbol_regex_union | primary | 3 | 0 | 3 | 0.0000 |

### Worst actions by gold kill: admission_v3_h1

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| abstain | non_primary | 6 | 3 | 1.0000 |
| supporting_only | non_primary | 2 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 1.0000 |
| admit_llm_span_narrow | primary | 1 | 0 | 0.0000 |
| admit_rrf_primary | primary | 1 | 0 | 0.0000 |

## Action span-cost table: admission_v3_h2

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abstain | non_primary | 2 | 0.1429 | 0 | 0 | n/a | n/a | 0 | 0 | 2 | 0 | False |
| admit_symbol_regex_union | primary | 1 | 0.0714 | 1 | 0 | 0.0000 | n/a | 1 | 1 | 0 | 0 | False |
| apply_llm_filter | non_primary | 5 | 0.3571 | 0 | 3 | n/a | 0.0000 | -3 | -6 | 2 | 3 | True |
| supporting_only | non_primary | 2 | 0.1429 | 0 | 0 | n/a | n/a | 0 | 0 | 1 | 1 | False |
| weak_candidate_only | non_primary | 4 | 0.2857 | 0 | 4 | n/a | 0.0000 | -4 | -8 | 4 | 0 | True |

### Worst actions by false cost: admission_v3_h2

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 4 | 4 | 0 | n/a |
| apply_llm_filter | non_primary | 5 | 3 | 0 | n/a |
| abstain | non_primary | 2 | 0 | 0 | n/a |
| admit_symbol_regex_union | primary | 1 | 0 | 1 | 0.0000 |
| supporting_only | non_primary | 2 | 0 | 0 | n/a |

### Worst actions by gold kill: admission_v3_h2

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 4 | 4 | 1.0000 |
| abstain | non_primary | 2 | 2 | 1.0000 |
| apply_llm_filter | non_primary | 5 | 2 | 1.0000 |
| supporting_only | non_primary | 2 | 1 | 1.0000 |
| admit_symbol_regex_union | primary | 1 | 0 | 0.0000 |

## Conclusion

- P30-H3 is accounting-only, not a new admission route or policy.
- It derives action-specific span cost from existing policies without changing routes, EvidenceCore semantics, or default strategies.
- Budget violations flag actions whose false-span cost exceeds a diagnostic threshold, not a production cost constraint.
- High non_primary_false_span_cost indicates weak/supporting/filter actions still carry primary false-span risk and need tighter route guards.

## Safety notes

- P30-H3 is score-phase accounting over fixed existing policies; it does not route or admit tasks.
- No remote model calls are made during H3 accounting.
- No raw queries, snippets, prompts, responses, gold spans, private labels, provider keys, or per-task records are emitted.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `external_calls=0`.
