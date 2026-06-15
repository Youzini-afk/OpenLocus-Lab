# P52C Diagnostic Local Verifier Scoring Simulator

- Schema: `p52c-local-verifier-scoring-simulator-v1`
- Generated: 2026-06-15T20:46:38.289063+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P52C: 0
- LLM calls by P52C: 0
- Prompt construction by P52C: False
- Source reads attempted by P52C: True
- Source reads bounded by P52C: True
- Local verifier score available: False
- Tasks: 5 positive=3 no_gold=2
- Candidate pool availability: `partial`
- P52B report source: `not_provided`
- P52A report source: `not_provided`
- P52 report source: `not_provided`
- P49 report source: `not_provided`

## Purpose

P52C computes deterministic, gold-free diagnostic score buckets from P52B source-backed features, P52A materialization outcomes, and P52/P49 metadata. It is a SCORE-phase-only scoring simulator, not a verifier pass/fail phase, not Evidence, and not an admission/default/promotion stage.

## Methodology

- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).
- Normalize candidates with P46/P49 helpers and resolve bounded repo roots with P52A helpers.
- Recompute bounded source outcomes and source-shape features through existing P52A/P52B helpers.
- Build the fixed gold-free formula `p52c_diagnostic_score_v0` from positive and negative components; unavailable components are not counted.
- Emit only aggregate score buckets (`high`, `medium`, `low`, `unavailable`) and binned score distribution; no raw candidate scores are published.
- Break down aggregated counts/rates by safe public dimensions (metadata/source-feature buckets, path kind, subtype axes, RRF backing, public bucket/risk tag, strategy, pack strategy).
- Gold spans and existing P21 role outcomes are used only inside `score_phase_diagnostic_correlation` after score buckets are fixed.

## Safety notes

- P52C does not call an LLM, construct prompts, or make remote calls.
- P52C does not produce a verifier pass/fail or local-verifier admission score.
- P52C scores are not Evidence and do not prove P51/P53 quality.
- Source reads are bounded and aggregate-only when available.
- Raw source, snippets, paths, spans, digests, task/candidate identifiers, queries, and provider keys are never stored.

## Score availability

- Availability enum: `partial_source_backed`
- Candidate denominator: 11
- Score candidate denominator: 9
- Source-backed score candidate denominator: 5
- Metadata-only candidate denominator: 4
- Score unavailable count/rate: 2 / 0.1818
- Source read attempts/success: 11 / 8 (0.7273)
- Bounded-span feature candidate denominator: 5

## Diagnostic score distribution

| Bucket | Count | Rate |
|---|---:|---:|
| diagnostic_score_high | 5 | 0.5556 |
| diagnostic_score_medium | 0 | 0.0000 |
| diagnostic_score_low | 4 | 0.4444 |
| diagnostic_score_unavailable | 2 | 0.1818 |

### Score bin distribution

| Bin | Count |
|---|---:|
| <=-3 | 0 |
| -2_-1 | 4 |
| 0_1 | 0 |
| 2_3 | 2 |
| >=4 | 3 |
| unavailable | 2 |

### Positive component rates

| Component | Checkable | Positive Rate |
|---|---|---:|
| source_read_success | 5 | 1.0000 |
| line_range_valid | 11 | 0.4545 |
| bounded_span_feature_available | 11 | 0.4545 |
| nonempty_span | 5 | 1.0000 |
| code_like_token | 5 | 1.0000 |
| signature_like_heuristic | 5 | 0.6000 |
| rrf_backing | 9 | 0.2222 |
| symbol_regex_fusion_span_overlap | 9 | 0.1111 |
| metadata_low_risk | 9 | 0.1111 |
| metadata_medium_risk | 9 | 0.1111 |

### Negative component rates

| Component | Checkable | Negative Rate |
|---|---|---:|
| digest_mismatch | 11 | 0.1818 |
| span_over_cap | 11 | 0.0000 |
| blank_only | 5 | 0.0000 |
| comment_only | 5 | 0.0000 |
| import_only | 5 | 0.0000 |
| generated_or_vendor_path_kind | 9 | 0.0000 |
| unknown_path_kind | 9 | 0.0000 |
| metadata_high_risk | 9 | 0.7778 |
| source_feature_high_risk | 11 | 0.7273 |
| source_feature_unavailable | 11 | 0.0000 |

## SCORE-phase diagnostic correlation (not used for score construction)

| Bucket | GoldFile Count | GoldFile | GoldSpan | FileRightSpanWrong | NoGold | ExistingRoleDelta |
|---:|---:|---:|---:|---:|---:|---:|
| diagnostic_score_high | 3 | 0.6000 | 0.2000 | 0.4000 | 0.4000 | 0.0200 |
| diagnostic_score_medium | 0 | n/a | n/a | n/a | n/a | n/a |
| diagnostic_score_low | 0 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |
| diagnostic_score_unavailable | 0 | 0.0000 | 0.0000 | 0.0000 | 1.0000 | n/a |

## Conclusion

- Self-test-only diagnostic scoring simulator scored 11 synthetic candidates across 5 tasks; this is not quality evidence.
- P52C scores are deterministic, gold-free diagnostic buckets only. They are not Evidence, do not produce a verifier pass/fail, do not admit candidates, and do not claim default/promotion. Source reads are bounded and aggregate-only when available.
- Score availability: `partial_source_backed`; source-backed scored candidates: 5; metadata-only scored candidates: 4; unavailable: 2.
