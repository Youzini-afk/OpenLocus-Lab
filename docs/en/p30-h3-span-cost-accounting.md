# P30-H3 Action-Specific Span-Cost Accounting

- Schema: `p30-h3-action-span-cost-report-v1`
- Generated: 2026-06-15T12:01:08.462667+00:00
- Tasks: 23 (+18 / no_gold 5)
- Status: `score_phase_only_accounting=true`, `diagnostic_only=true`, `promotion_ready=false`, `default_should_change=false`.

## Budget policy (accounting-only)

- Primary-admit actions: `added_false_span <= added_gold_span` (budget=1.0 false/gold).
- Non-primary actions: `added_false_span == 0`.
- Unclassified baseline strategies: `added_false_span <= added_gold_span` (budget=1.0 false/gold).
- Accounting-only diagnostic budget. Primary admission actions are expected to keep added_false_span <= added_gold_span. Non-primary actions are expected to add zero false spans. Unclassified baseline strategy actions are expected to be net-neutral.

## Policy-level span-cost summary

| Policy | tasks | primary_false_cost | non_primary_false_cost | unclassified_false_cost | budget_violations | budget_violation_rate |
|---|---:|---:|---:|---:|---:|---:|
| candidate_baseline | 23 | 0 | 0 | 56 | 23 | 1.0000 |
| llm_span_narrow | 23 | 33 | 0 | 0 | 23 | 1.0000 |
| llm_filter | 23 | 0 | 5 | 0 | 23 | 1.0000 |
| llm_abstain_filter | 23 | 0 | 0 | 0 | 0 | 0.0000 |
| bucket_routed_v0 | 23 | 11 | 2 | 6 | 9 | 0.3913 |
| admission_v3 | 23 | 7 | 1 | 0 | 4 | 0.1739 |
| admission_v3_h1 | 23 | 7 | 1 | 0 | 4 | 0.1739 |
| admission_v3_h2 | 23 | 0 | 11 | 0 | 14 | 0.6087 |
| admission_v3_h4 | 23 | 0 | 14 | 0 | 17 | 0.7391 |
| admission_v3_h4b | 23 | 2 | 17 | 0 | 20 | 0.8696 |

## Action span-cost table: candidate_baseline

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | unclassified | 23 | 1.0000 | 18 | 56 | 3.1111 | 0.3214 | -38 | -94 | 0 | 0 | True |

### Worst actions by false cost: candidate_baseline

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| candidate_baseline | unclassified | 23 | 56 | 18 | 3.1111 |

### Worst actions by gold kill: candidate_baseline

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| candidate_baseline | unclassified | 23 | 0 | 0.0000 |

## Action span-cost table: llm_span_narrow

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llm_span_narrow | primary | 23 | 1.0000 | 18 | 33 | 1.8333 | 0.5455 | -15 | -48 | 0 | 5 | True |

### Worst actions by false cost: llm_span_narrow

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_span_narrow | primary | 23 | 33 | 18 | 1.8333 |

### Worst actions by gold kill: llm_span_narrow

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_span_narrow | primary | 23 | 0 | 0.0000 |

## Action span-cost table: llm_filter

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llm_filter | non_primary | 23 | 1.0000 | 0 | 5 | n/a | 0.0000 | -5 | -10 | 18 | 5 | True |

### Worst actions by false cost: llm_filter

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_filter | non_primary | 23 | 5 | 0 | n/a |

### Worst actions by gold kill: llm_filter

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_filter | non_primary | 23 | 18 | 1.0000 |

## Action span-cost table: llm_abstain_filter

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llm_abstain_filter | non_primary | 23 | 1.0000 | 0 | 0 | n/a | n/a | 0 | 0 | 18 | 5 | False |

### Worst actions by false cost: llm_abstain_filter

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_abstain_filter | non_primary | 23 | 0 | 0 | n/a |

### Worst actions by gold kill: llm_abstain_filter

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_abstain_filter | non_primary | 23 | 18 | 1.0000 |

## Action span-cost table: bucket_routed_v0

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | unclassified | 3 | 0.1304 | 3 | 6 | 2.0000 | 0.5000 | -3 | -9 | 0 | 0 | True |
| llm_abstain_filter | non_primary | 3 | 0.1304 | 0 | 0 | n/a | n/a | 0 | 0 | 0 | 3 | False |
| llm_filter | non_primary | 6 | 0.2609 | 0 | 2 | n/a | 0.0000 | -2 | -4 | 4 | 2 | True |
| llm_span_narrow | primary | 11 | 0.4783 | 11 | 11 | 1.0000 | 1.0000 | 0 | -11 | 0 | 0 | False |

### Worst actions by false cost: bucket_routed_v0

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| llm_span_narrow | primary | 11 | 11 | 11 | 1.0000 |
| candidate_baseline | unclassified | 3 | 6 | 3 | 2.0000 |
| llm_filter | non_primary | 6 | 2 | 0 | n/a |
| llm_abstain_filter | non_primary | 3 | 0 | 0 | n/a |

### Worst actions by gold kill: bucket_routed_v0

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| llm_filter | non_primary | 6 | 4 | 1.0000 |
| candidate_baseline | unclassified | 3 | 0 | 0.0000 |
| llm_abstain_filter | non_primary | 3 | 0 | n/a |
| llm_span_narrow | primary | 11 | 0 | 0.0000 |

## Action span-cost table: admission_v3

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abstain | non_primary | 11 | 0.4783 | 0 | 0 | n/a | n/a | 0 | 0 | 7 | 4 | False |
| admit_llm_span_narrow | primary | 1 | 0.0435 | 1 | 1 | 1.0000 | 1.0000 | 0 | -1 | 0 | 0 | False |
| admit_rrf_primary | primary | 3 | 0.1304 | 3 | 6 | 2.0000 | 0.5000 | -3 | -9 | 0 | 0 | True |
| admit_symbol_regex_union | primary | 5 | 0.2174 | 5 | 0 | 0.0000 | n/a | 5 | 5 | 0 | 0 | False |
| supporting_only | non_primary | 2 | 0.0870 | 0 | 0 | n/a | n/a | 0 | 0 | 1 | 1 | False |
| weak_candidate_only | non_primary | 1 | 0.0435 | 0 | 1 | n/a | 0.0000 | -1 | -2 | 1 | 0 | True |

### Worst actions by false cost: admission_v3

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| admit_rrf_primary | primary | 3 | 6 | 3 | 2.0000 |
| admit_llm_span_narrow | primary | 1 | 1 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 0 | n/a |
| abstain | non_primary | 11 | 0 | 0 | n/a |
| admit_symbol_regex_union | primary | 5 | 0 | 5 | 0.0000 |

### Worst actions by gold kill: admission_v3

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| abstain | non_primary | 11 | 7 | 1.0000 |
| supporting_only | non_primary | 2 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 1.0000 |
| admit_llm_span_narrow | primary | 1 | 0 | 0.0000 |
| admit_rrf_primary | primary | 3 | 0 | 0.0000 |

## Action span-cost table: admission_v3_h1

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abstain | non_primary | 11 | 0.4783 | 0 | 0 | n/a | n/a | 0 | 0 | 7 | 4 | False |
| admit_llm_span_narrow | primary | 1 | 0.0435 | 1 | 1 | 1.0000 | 1.0000 | 0 | -1 | 0 | 0 | False |
| admit_rrf_primary | primary | 3 | 0.1304 | 3 | 6 | 2.0000 | 0.5000 | -3 | -9 | 0 | 0 | True |
| admit_symbol_regex_union | primary | 5 | 0.2174 | 5 | 0 | 0.0000 | n/a | 5 | 5 | 0 | 0 | False |
| supporting_only | non_primary | 2 | 0.0870 | 0 | 0 | n/a | n/a | 0 | 0 | 1 | 1 | False |
| weak_candidate_only | non_primary | 1 | 0.0435 | 0 | 1 | n/a | 0.0000 | -1 | -2 | 1 | 0 | True |

### Worst actions by false cost: admission_v3_h1

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| admit_rrf_primary | primary | 3 | 6 | 3 | 2.0000 |
| admit_llm_span_narrow | primary | 1 | 1 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 0 | n/a |
| abstain | non_primary | 11 | 0 | 0 | n/a |
| admit_symbol_regex_union | primary | 5 | 0 | 5 | 0.0000 |

### Worst actions by gold kill: admission_v3_h1

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| abstain | non_primary | 11 | 7 | 1.0000 |
| supporting_only | non_primary | 2 | 1 | 1.0000 |
| weak_candidate_only | non_primary | 1 | 1 | 1.0000 |
| admit_llm_span_narrow | primary | 1 | 0 | 0.0000 |
| admit_rrf_primary | primary | 3 | 0 | 0.0000 |

## Action span-cost table: admission_v3_h2

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| abstain | non_primary | 2 | 0.0870 | 0 | 0 | n/a | n/a | 0 | 0 | 2 | 0 | False |
| admit_symbol_regex_union | primary | 5 | 0.2174 | 5 | 0 | 0.0000 | n/a | 5 | 5 | 0 | 0 | False |
| apply_llm_filter | non_primary | 7 | 0.3043 | 0 | 4 | n/a | 0.0000 | -4 | -8 | 3 | 4 | True |
| supporting_only | non_primary | 2 | 0.0870 | 0 | 0 | n/a | n/a | 0 | 0 | 1 | 1 | False |
| weak_candidate_only | non_primary | 7 | 0.3043 | 0 | 7 | n/a | 0.0000 | -7 | -14 | 7 | 0 | True |

### Worst actions by false cost: admission_v3_h2

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 7 | 7 | 0 | n/a |
| apply_llm_filter | non_primary | 7 | 4 | 0 | n/a |
| abstain | non_primary | 2 | 0 | 0 | n/a |
| admit_symbol_regex_union | primary | 5 | 0 | 5 | 0.0000 |
| supporting_only | non_primary | 2 | 0 | 0 | n/a |

### Worst actions by gold kill: admission_v3_h2

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 7 | 7 | 1.0000 |
| apply_llm_filter | non_primary | 7 | 3 | 1.0000 |
| abstain | non_primary | 2 | 2 | 1.0000 |
| supporting_only | non_primary | 2 | 1 | 1.0000 |
| admit_symbol_regex_union | primary | 5 | 0 | 0.0000 |

## Action span-cost table: admission_v3_h4

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| apply_llm_filter | non_primary | 7 | 0.3043 | 0 | 4 | n/a | 0.0000 | -4 | -8 | 3 | 4 | True |
| supporting_only | non_primary | 6 | 0.2609 | 0 | 0 | n/a | n/a | 0 | 0 | 5 | 1 | False |
| weak_candidate_only | non_primary | 10 | 0.4348 | 0 | 10 | n/a | 0.0000 | -10 | -20 | 10 | 0 | True |

### Worst actions by false cost: admission_v3_h4

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 10 | 10 | 0 | n/a |
| apply_llm_filter | non_primary | 7 | 4 | 0 | n/a |
| supporting_only | non_primary | 6 | 0 | 0 | n/a |

### Worst actions by gold kill: admission_v3_h4

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 10 | 10 | 1.0000 |
| supporting_only | non_primary | 6 | 5 | 1.0000 |
| apply_llm_filter | non_primary | 7 | 3 | 1.0000 |

## Action span-cost table: admission_v3_h4b

| Action | kind | selected | selected_rate | added_gold | added_false | false/gold | gold/false | net_1x | net_2x | gold_kill | false_reduction | budget_violated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| admit_rrf_primary | primary | 1 | 0.0435 | 1 | 2 | 2.0000 | 0.5000 | -1 | -3 | 0 | 0 | True |
| admit_symbol_regex_union | primary | 1 | 0.0435 | 1 | 0 | 0.0000 | n/a | 1 | 1 | 0 | 0 | False |
| apply_llm_filter | non_primary | 3 | 0.1304 | 0 | 1 | n/a | 0.0000 | -1 | -2 | 2 | 1 | True |
| supporting_only | non_primary | 2 | 0.0870 | 0 | 0 | n/a | n/a | 0 | 0 | 2 | 0 | False |
| weak_candidate_only | non_primary | 16 | 0.6957 | 0 | 16 | n/a | 0.0000 | -16 | -32 | 12 | 4 | True |

### Worst actions by false cost: admission_v3_h4b

| Action | kind | selected | added_false | added_gold | false/gold |
|---|---:|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 16 | 16 | 0 | n/a |
| admit_rrf_primary | primary | 1 | 2 | 1 | 2.0000 |
| apply_llm_filter | non_primary | 3 | 1 | 0 | n/a |
| admit_symbol_regex_union | primary | 1 | 0 | 1 | 0.0000 |
| supporting_only | non_primary | 2 | 0 | 0 | n/a |

### Worst actions by gold kill: admission_v3_h4b

| Action | kind | selected | gold_kill | gold_kill_rate |
|---|---:|---:|---:|---:|
| weak_candidate_only | non_primary | 16 | 12 | 1.0000 |
| apply_llm_filter | non_primary | 3 | 2 | 1.0000 |
| supporting_only | non_primary | 2 | 2 | 1.0000 |
| admit_rrf_primary | primary | 1 | 0 | 0.0000 |
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
