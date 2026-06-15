# P50 Fixed-Suite Validation / Anti-Overfit Gate

- Schema: `p50-fixed-suite-validation-v1`
- Generated: 2026-06-15T16:11:08.357678+00:00
- Status: `self_test_only`
- Quality gate: `insufficient_fixed_suite`
- Self-test: True
- Remote calls by P50: 0
- Source reads by P50: False
- Tasks: 4 positive=3 no_gold=1 repos=2

## Purpose

P50 validates that an evaluation suite is healthy and fixed enough to serve as an anti-overfit gate. 
It is a deterministic, SCORE-phase-only discipline phase, not a policy improvement phase.

## Methodology

- Loads `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).
- Computes hashes over the suite manifest and evaluator configuration; publishes only the digests.
- Reports aggregate suite composition, availability, and fallback rates.
- Compares the aggregate span cost of `bucket_routed_v0` and `admission_v3_h4b` route policies.
- Carries forward P46 reach/cost/materialization and P47 span-geometry diagnostics with explicit not-evidence flags.
- Carries forward P48 diagnostic-policy simulator lane availability and aggregate overlay action-count summaries only; P48 is not evidence, not admission, and not a default.

## Suite composition

- Input records: 4
- Tasks: 4
- Repositories: 2 (count only; no repo IDs are published)
- Positive / no-gold tasks: 3 / 1
- Candidate pool availability: `partial`
- Gold span availability: `available`
- P33-B subtype availability: `available`
- Outcome availability: `partial`
- Fallback outcome rate: n/a
- Missing cost-field rate: n/a

## Hashes

- Suite manifest sha256: `fd44ed577a7d3e47b8ce656c2e0040c65b05758f0825ae32c13c41085090d98f`
- Evaluator config sha256: `45bec88fbf38b39af2e7387c8f6545a36a3faa228ea5a762aa1a4c41db7a8996`
- Note: This hash covers private per-task identifiers and public metadata. Raw components are not published.

## Public bucket distribution

| Bucket | Count |
|---|---:|
| ambiguous | 1 |
| negative | 1 |
| positive | 2 |

## Risk tag distribution

| Tag | Count |
|---|---:|
| ambiguous | 1 |
| high_confidence | 1 |
| negative | 1 |
| symbol_anchor | 1 |

## Policy route comparison

| Policy | Selected | OutcomeFallback | CostFallback | Actions |
|---|---:|---:|---:|---:|
| admission_v3_h4b | 4 | n/a | n/a | admit_symbol_regex_union=1, apply_llm_filter=1, weak_candidate_only=2 |
| bucket_routed_v0 | 4 | n/a | n/a | llm_abstain_filter=1, llm_filter=1, llm_span_narrow=2 |

## Key-strategy outcome cost

| Strategy | Availability | Tasks | + | no_gold | OutcomeMissing | CostMissing | added_gold | added_false | net_1x |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate_baseline | available | 4 | 3 | 1 | 0 | 0 | 3 | 9 | -6 |
| symbol_regex_union | available | 4 | 3 | 1 | 1 | 1 | 2 | 1 | 1 |
| rrf_primary | available | 4 | 3 | 1 | 2 | 2 | 2 | 5 | -3 |
| llm_span_narrow | available | 4 | 3 | 1 | 2 | 2 | 2 | 2 | 0 |

## Baseline/policy delta

Availability: `missing_or_partial_cost_fields` — delta not computed.

## P46 carry-forward (aggregate only)

- Reach/cost map availability: `available`; materialization availability: `source_read_unavailable`
- Materialization overall: seen=14, valid=None, rate=n/a, unavailable_reason=source_read_unavailable

## P47 carry-forward (aggregate only)

- Variant map availability: `available`; gap breakdown availability: `available`; hypothetical upper bound availability: `available`
- span_geometry_only: `True`
- expanded_candidate_not_evidence: `True`

## P48 carry-forward (aggregate only)

- `p48_variant_availability='available'`
- P48 schema version: `p48-diagnostic-policy-simulator-v1`
- request_more_context_not_evidence: `True`
- span_geometry_only_context: `True`
- p48_p25_rmc_overlay_v0: availability=`partial_missing_cost_fields`, selected=4, rmc_count=1, demoted_primary=1, quality_comparable=False, actions=[llm_abstain_filter=1, llm_filter=1, llm_span_narrow=1, request_more_context=1]
- p48_h4b_rmc_overlay_v0: availability=`partial_missing_cost_fields`, selected=4, rmc_count=1, demoted_primary=1, quality_comparable=False, actions=[apply_llm_filter=1, request_more_context=1, weak_candidate_only=2]
- p48_conversion_admission_unavailable: availability=`unavailable_source_read_unavailable`, selected=n/a, rmc_count=n/a, demoted_primary=n/a, quality_comparable=n/a, actions=[n/a]

## Quality gate

- Status: `insufficient_fixed_suite`
- Reasons:
  - self_test_only
  - status=self_test_only
  - task_count=4 < 6
  - bucket_routed_v0 has non-zero outcome/cost fallback
  - admission_v3_h4b has non-zero outcome/cost fallback

## Conclusion

- P50 fixed-suite anti-overfit gate is `insufficient_fixed_suite`; this is a scaffold/health report.
- self_test_only
- status=self_test_only
- task_count=4 < 6
- bucket_routed_v0 has non-zero outcome/cost fallback
- admission_v3_h4b has non-zero outcome/cost fallback
- P50 is an evaluation discipline phase, not a policy improvement phase.
- P48 diagnostic-policy simulator availability: `available`; P48 carry-forward contains only aggregate overlay lane summaries and does not infer promotion from span-geometry signals.
- Suite manifest hash (sha256): `fd44ed577a7d3e47b8ce656c2e0040c65b05758f0825ae32c13c41085090d98f`.
- Evaluator config hash (sha256): `45bec88fbf38b39af2e7387c8f6545a36a3faa228ea5a762aa1a4c41db7a8996`.
- Candidate pool availability: `partial`; gold span availability: `available`.
- All outputs are aggregate-only; no per-task rows, task IDs, candidate IDs, paths, gold spans, private labels, snippets, prompts, responses, or provider keys are published.

## Safety notes

- No remote model calls were made during P50 evaluation.
- No source files were read by P50.
- This report contains only aggregate counts/rates; no per-task rows are published.
- No task IDs, candidate IDs, paths, spans, gold spans, private labels, route features, snippets, prompts, responses, repo IDs, or provider keys are stored.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`.
- `remote_calls_by_p50=0`, `source_reads_attempted_by_p50=false`, `score_phase_only_metrics=true`, `aggregate_only_public_artifact=true`.
