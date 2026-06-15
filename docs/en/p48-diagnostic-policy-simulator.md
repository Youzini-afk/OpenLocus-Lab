# P48 Diagnostic Policy Simulator / Request-More-Context Overlay

- Schema: `p48-diagnostic-policy-simulator-v1`
- Generated: 2026-06-15T16:11:08.308496+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P48: 0
- Source reads by P48: False
- Request-more-context is not evidence: True
- Span geometry only: True
- Tasks: 4 positive=3 no_gold=1
- Candidate pool availability: `partial`
- Gold span availability: `available`
- Reach metrics available: True
- P50 gate source: `not_provided`
- P50 quality gate status: `not_provided`

## Purpose

P48 overlays the P47 `request_more_context` span-geometry gate on the P25 `bucket_routed_v0` and P30-H4B `admission_v3_h4b` route policies. It simulates how many risky candidate-derived primary actions would be replaced by a geometry-only context request. NoEvidenceCore semantics change, no source reads occur, and no policy is promoted to default.

## Methodology

- Replay `reference_bucket_routed_v0` and `reference_admission_v3_h4b`.
- Build `p48_p25_rmc_overlay_v0`: replace eligible P25 primary actions with `request_more_context` when the P47 gate accepts the top candidate.
- Build `p48_h4b_rmc_overlay_v0`: replace eligible H4B primary admits with `request_more_context` when the P47 gate accepts.
- Leave `p48_conversion_admission_unavailable` explicitly unavailable (P46 source-read materialization is not wired).
- Report aggregate action counts, primary-action counts, request-more-context counts, demoted-primary counts, outcome/cost fallback rates, and measured primary cost only for existing actions.
- Report span-geometry diagnostics (line budgets, overfetch, gap-type distribution, gold capture) only for accepted candidates after routing decisions.
- No source files are read; no remote model calls are made; no per-task rows, paths, spans, gold spans, or private labels are emitted.

## Route simulation summary

| Lane | Availability | Selected | Primary | RMC count | Demoted primary | OutcomeFallback | CostFallback | QualityComparable |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| reference_bucket_routed_v0 | partial_missing_cost_fields | 4 | 2 | 0 | n/a | n/a | n/a | False |
| reference_admission_v3_h4b | partial_missing_cost_fields | 4 | 1 | 0 | n/a | n/a | n/a | False |
| p48_p25_rmc_overlay_v0 | partial_missing_cost_fields | 4 | 1 | 1 | 1 | n/a | n/a | False |
| p48_h4b_rmc_overlay_v0 | partial_missing_cost_fields | 4 | 0 | 1 | 1 | n/a | n/a | False |
| p48_conversion_admission_unavailable | unavailable_source_read_unavailable | - | - | - | - | - | - | False |

## Action distribution per lane

- **reference_bucket_routed_v0**: llm_abstain_filter=1, llm_filter=1, llm_span_narrow=2
- **reference_admission_v3_h4b**: admit_symbol_regex_union=1, apply_llm_filter=1, weak_candidate_only=2
- **p48_p25_rmc_overlay_v0**: llm_abstain_filter=1, llm_filter=1, llm_span_narrow=1, request_more_context=1
- **p48_h4b_rmc_overlay_v0**: apply_llm_filter=1, request_more_context=1, weak_candidate_only=2

## Measured primary cost (existing primary actions only)

| Lane | Availability | Primary actions with cost | added_gold | added_false |
|---|---:|---:|---:|---:|
| reference_bucket_routed_v0 | available | 2 | 2 | 2 |
| reference_admission_v3_h4b | available | 1 | 1 | 0 |
| p48_p25_rmc_overlay_v0 | available | 1 | 1 | 1 |
| p48_h4b_rmc_overlay_v0 | missing_primary_actions | 0 | n/a | n/a |

## Request-more-context geometry (accepted candidates only)

| Lane | Considered | Accepted | Rejected | AcceptRate | RawBudget | ExpandedBudget | MeanLines | P95Lines | Overfetch | GoldCapture | NoGoldExpanded | GoldGain |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| p48_p25_rmc_overlay_v0 | 2 | 1 | 1 | 0.5000 | 6 | 12 | 12.0000 | 12.0000 | 1.0000 | 1 | 0 | 0 |
| p48_h4b_rmc_overlay_v0 | 1 | 1 | 0 | 1.0000 | 6 | 12 | 12.0000 | 12.0000 | 1.0000 | 1 | 0 | 0 |

## Gap type distribution (accepted candidates)

| Lane | Adjacent/Overlap | SameFileNear | SameFileFar | CandidateAbsent |
|---|---:|---:|---:|---:|
| p48_p25_rmc_overlay_v0 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| p48_h4b_rmc_overlay_v0 | 1.0000 | 0.0000 | 0.0000 | 0.0000 |

## Conclusion

- Self-test-only scaffold simulated 4 synthetic tasks; this is not quality evidence.
- P48 is SCORE-phase-only. No source files were read and no EvidenceCore semantics were changed.
- `request_more_context` is a span-geometry diagnostic, not evidence, not admission, and not a default.
- P25 overlay: request_more_context_count=1, demoted_primary_count=1, quality_comparable=False.
- H4B overlay: request_more_context_count=1, demoted_primary_count=1, quality_comparable=False.
- P46 materialization availability: source_read_unavailable. P48 conversion/admission lane is unavailable by design.
- No policy is promotion-ready or default-ready.

## Safety notes

- No remote model calls were made during P48 simulation.
- No source files were read and no AST/source trim was attempted.
- This report contains only aggregate counts/rates by lane and action.
- No task IDs, candidate IDs, paths, spans, gold spans, private labels, route features, snippets, prompts, responses, or provider keys are stored.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `remote_calls_by_p48=0`, `source_reads_attempted_by_p48=false`, `request_more_context_not_evidence=true`, `span_geometry_only_context=true`.
- `request_more_context` is not evidence and does not change defaults or Rust/EvidenceCore.
