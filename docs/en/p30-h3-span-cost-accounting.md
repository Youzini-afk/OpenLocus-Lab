# P30-H3 Action-Specific Span-Cost Accounting

- Schema: `p30-h3-action-span-cost-report-v1`
- Generated: 2026-06-15T09:37:50.611108+00:00
- Tasks: 19 (+14 / no_gold 5)
- Status: `score_phase_only_accounting=true`, `diagnostic_only=true`, `promotion_ready=false`, `default_should_change=false`.

## Budget policy (accounting-only)

- Primary-admit actions: `added_false_span <= added_gold_span` (budget=1.0 false/gold).
- Non-primary actions: `added_false_span == 0`.
- Unclassified baseline strategies: `added_false_span <= added_gold_span` (budget=1.0 false/gold).
- Accounting-only diagnostic budget. Primary admission actions are expected to keep added_false_span <= added_gold_span. Non-primary actions are expected to add zero false spans. Unclassified baseline strategy actions are expected to be net-neutral.

## Policy-level span-cost summary

| Policy | tasks | primary_false_cost | non_primary_false_cost | unclassified_false_cost | budget_violations | budget_violation_rate |
|---|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 19 | 0 | 0 | 48 | 19 | 1.0000 |
| llm_span_narrow | 19 | 29 | 0 | 0 | 19 | 1.0000 |
| llm_filter | 19 | 0 | 5 | 0 | 19 | 1.0000 |
| llm_abstain_filter | 19 | 0 | 0 | 0 | 0 | 0.0000 |
| bucket_routed_v0 | 19 | 8 | 2 | 4 | 8 | 0.4211 |
| admission_v3 | 19 | 5 | 1 | 0 | 3 | 0.1579 |
| admission_v3_h1 | 19 | 5 | 1 | 0 | 3 | 0.1579 |
| admission_v3_h2 | 19 | 0 | 11 | 0 | 14 | 0.7368 |
| admission_v3_h4 | 19 | 0 | 13 | 0 | 16 | 0.8421 |

## Action span-cost table: candidate_baseline

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | unclassified | 19 | 1.0000 | 14 | 48 | 3.4286 | 0.2917 | -34 | -82 | 0 | 0 | True |

### Worst actions by false cost: candidate_baseline

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| candidate_baseline | unclassified | 19 | 48 | 14 | 3.4286 |

### Worst actions by gold kill: candidate_baseline

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| candidate_baseline | unclassified | 19 | 0 | 0.0000 |

## Action span-cost table: llm_span_narrow

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llm_span_narrow | primary | 19 | 1.0000 | 14 | 29 | 2.0714 | 0.4828 | -15 | -44 | 0 | 5 | True |

### Worst actions by false cost: llm_span_narrow

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_span_narrow | primary | 19 | 29 | 14 | 2.0714 |

### Worst actions by gold kill: llm_span_narrow

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_span_narrow | primary | 19 | 0 | 0.0000 |

## Action span-cost table: llm_filter

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llm_filter | non_primary | 19 | 1.0000 | 0 | 5 | n/a | 0.0000 | -5 | -10 | 14 | 5 | True |

### Worst actions by false cost: llm_filter

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_filter | non_primary | 19 | 5 | 0 | n/a |

### Worst actions by gold kill: llm_filter

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_filter | non_primary | 19 | 14 | 1.0000 |

## Action span-cost table: llm_abstain_filter

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llm_abstain_filter | non_primary | 19 | 1.0000 | 0 | 0 | n/a | n/a | 0 | 0 | 14 | 5 | False |

### Worst actions by false cost: llm_abstain_filter

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_abstain_filter | non_primary | 19 | 0 | 0 | n/a |

### Worst actions by gold kill: llm_abstain_filter

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_abstain_filter | non_primary | 19 | 14 | 1.0000 |

## Action span-cost table: bucket_routed_v0

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | unclassified | 2 | 0.1053 | 2 | 4 | 2.0000 | 0.5000 | -2 | -6 | 0 | 0 | True |
| llm_abstain_filter | non_primary | 3 | 0.1579 | 0 | 0 | n/a | n/a | 0 | 0 | 0 | 3 | False |
| llm_filter | non_primary | 6 | 0.3158 | 0 | 2 | n/a | 0.0000 | -2 | -4 | 4 | 2 | True |
| llm_span_narrow | primary | 8 | 0.4211 | 8 | 8 | 1.0000 | 1.0000 | 0 | -8 | 0 | 0 | False |

### Worst actions by false cost: bucket_routed_v0

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_span_narrow | primary | 8 | 8 | 8 | 1.0000 |
| candidate_baseline | unclassified | 2 | 4 | 2 | 2.0000 |
| llm_filter | non_primary | 6 | 2 | 0 | n/a |
| llm_abstain_filter | non_primary | 3 | 0 | 0 | n/a |

### Worst actions by gold kill: bucket_routed_v0

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_filter | non_primary | 6 | 4 | 1.0000 |
| candidate_baseline | unclassified | 2 | 0 | 0.0000 |
| llm_abstain_filter | non_primary | 3 | 0 | n/a |
| llm_span_narrow | primary | 8 | 0 | 0.0000 |

## Action span-cost table: admission_v3

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abstain | non_primary | 9 | 0.4737 | 0 | 0 | n/a | n/a | 0 | 0 | 5 | 4 | False |
| admit_llm_span_narrow | primary | 1 | 0.0526 | 1 | 1 | 1.0000 | 1.0000 | 0 | -1 | 0 | 0 | False |
| admit_rrf_primary | primary | 2 | 0.1053 | 2 | 4 | 2.0000 | 0.5000 | -2 | -6 | 0 | 0 | True |
| admit_symbol_regex_union | primary | 4 | 0.2105 | 4 | 0 | 0.0000 | n/a | 4 | 4 | 0 | 0 | False |
| supporting_only | non_primary | 2 | 0.1053 | 0 | 0 | n/a | n/a | 0 | 0 | 1 | 1 | False |
| weak_candidate_only | non_primary | 1 | 0.0526 | 0 | 1 | n/a | 0.0000 | -1 | -2 | 1 | 0 | True |

### Worst actions by false cost: admission_v3

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| admit_rrf_primary | primary | 2 | 4 | 2 | 2.0000 |
| admit_llm_span_narrow | primary | 1 | 1 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 0 | n/a |
| abstain | non_primary | 9 | 0 | 0 | n/a |
| admit_symbol_regex_union | primary | 4 | 0 | 4 | 0.0000 |

### Worst actions by gold kill: admission_v3

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| abstain | non_primary | 9 | 5 | 1.0000 |
| supporting_only | non_primary | 2 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 1.0000 |
| admit_llm_span_narrow | primary | 1 | 0 | 0.0000 |
| admit_rrf_primary | primary | 2 | 0 | 0.0000 |

## Action span-cost table: admission_v3_h1

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abstain | non_primary | 9 | 0.4737 | 0 | 0 | n/a | n/a | 0 | 0 | 5 | 4 | False |
| admit_llm_span_narrow | primary | 1 | 0.0526 | 1 | 1 | 1.0000 | 1.0000 | 0 | -1 | 0 | 0 | False |
| admit_rrf_primary | primary | 2 | 0.1053 | 2 | 4 | 2.0000 | 0.5000 | -2 | -6 | 0 | 0 | True |
| admit_symbol_regex_union | primary | 4 | 0.2105 | 4 | 0 | 0.0000 | n/a | 4 | 4 | 0 | 0 | False |
| supporting_only | non_primary | 2 | 0.1053 | 0 | 0 | n/a | n/a | 0 | 0 | 1 | 1 | False |
| weak_candidate_only | non_primary | 1 | 0.0526 | 0 | 1 | n/a | 0.0000 | -1 | -2 | 1 | 0 | True |

### Worst actions by false cost: admission_v3_h1

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| admit_rrf_primary | primary | 2 | 4 | 2 | 2.0000 |
| admit_llm_span_narrow | primary | 1 | 1 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 0 | n/a |
| abstain | non_primary | 9 | 0 | 0 | n/a |
| admit_symbol_regex_union | primary | 4 | 0 | 4 | 0.0000 |

### Worst actions by gold kill: admission_v3_h1

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| abstain | non_primary | 9 | 5 | 1.0000 |
| supporting_only | non_primary | 2 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 1.0000 |
| admit_llm_span_narrow | primary | 1 | 0 | 0.0000 |
| admit_rrf_primary | primary | 2 | 0 | 0.0000 |

## Action span-cost table: admission_v3_h2

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abstain | non_primary | 2 | 0.1053 | 0 | 0 | n/a | n/a | 0 | 0 | 2 | 0 | False |
| admit_symbol_regex_union | primary | 1 | 0.0526 | 1 | 0 | 0.0000 | n/a | 1 | 1 | 0 | 0 | False |
| apply_llm_filter | non_primary | 7 | 0.3684 | 0 | 4 | n/a | 0.0000 | -4 | -8 | 3 | 4 | True |
| supporting_only | non_primary | 2 | 0.1053 | 0 | 0 | n/a | n/a | 0 | 0 | 1 | 1 | False |
| weak_candidate_only | non_primary | 7 | 0.3684 | 0 | 7 | n/a | 0.0000 | -7 | -14 | 7 | 0 | True |

### Worst actions by false cost: admission_v3_h2

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 7 | 7 | 0 | n/a |
| apply_llm_filter | non_primary | 7 | 4 | 0 | n/a |
| abstain | non_primary | 2 | 0 | 0 | n/a |
| admit_symbol_regex_union | primary | 1 | 0 | 1 | 0.0000 |
| supporting_only | non_primary | 2 | 0 | 0 | n/a |

### Worst actions by gold kill: admission_v3_h2

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 7 | 7 | 1.0000 |
| apply_llm_filter | non_primary | 7 | 3 | 1.0000 |
| abstain | non_primary | 2 | 2 | 1.0000 |
| supporting_only | non_primary | 2 | 1 | 1.0000 |
| admit_symbol_regex_union | primary | 1 | 0 | 0.0000 |

## Action span-cost table: admission_v3_h4

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| apply_llm_filter | non_primary | 7 | 0.3684 | 0 | 4 | n/a | 0.0000 | -4 | -8 | 3 | 4 | True |
| supporting_only | non_primary | 3 | 0.1579 | 0 | 0 | n/a | n/a | 0 | 0 | 2 | 1 | False |
| weak_candidate_only | non_primary | 9 | 0.4737 | 0 | 9 | n/a | 0.0000 | -9 | -18 | 9 | 0 | True |

### Worst actions by false cost: admission_v3_h4

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 9 | 9 | 0 | n/a |
| apply_llm_filter | non_primary | 7 | 4 | 0 | n/a |
| supporting_only | non_primary | 3 | 0 | 0 | n/a |

### Worst actions by gold kill: admission_v3_h4

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 9 | 9 | 1.0000 |
| apply_llm_filter | non_primary | 7 | 3 | 1.0000 |
| supporting_only | non_primary | 3 | 2 | 1.0000 |

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
