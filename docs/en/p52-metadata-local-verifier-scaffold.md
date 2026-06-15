# P52 Metadata-Only Local Verifier Scaffold

- Schema: `p52-metadata-local-verifier-scaffold-v1`
- Generated: 2026-06-15T17:53:52.926366+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P52: 0
- LLM calls by P52: 0
- Source reads by P52: False
- Prompt construction by P52: False
- Tasks: 4 positive=3 no_gold=1
- Candidate pool availability: `partial`
- Gold span availability: `available`
- Reach metrics available: True
- Source-required features availability: `unavailable_source_read_not_wired`
- P49 report source: `not_provided`
- P49 pack not evidence: `not_provided`
- P50 report source: `not_provided`
- P50 quality gate status: `not_provided`
- P48 report source: `not_provided`
- P48 overlay availability: `not_provided`

## Purpose

P52 inventories metadata-verifier feature availability and candidate-risk buckets before any source-read or LLM span-narrow phase. It is a SCORE-phase-only scaffold, not a verifier pass/fail phase.

## Methodology

- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).
- Normalize raw candidate pools into metadata-only records using P46/P49 helpers.
- Compute metadata feature availability, checkable metadata signals, and unavailable source/query verifier fields.
- Classify every candidate into a metadata-risk bucket using only public metadata (path-kind, span width, rank, subtype axes, risk tags).
- Rebuild P49 pack strategies in-memory and report aggregate pack-level risk diagnostics.
- After metadata extraction, compute SCORE-phase diagnostic correlations with gold spans/outcomes where available; these are marked `not_used_for_feature_construction=true`.
- Output is aggregate-only: counts, rates, and distributions by pack strategy, public task bucket, and risk tag.

## Safety notes

- P52 does not verify source text.
- P52 does not read files.
- P52 does not call an LLM.
- P52 does not construct prompts.
- P52 does not validate EvidenceCore.
- P52 does not produce evidence.
- P52 does not produce a verifier pass/fail score.
- P52 metadata gates are candidate-risk diagnostics only.
- P52 does not prove P51/P53 quality.

## Metadata feature availability (task-wide)

| Denom | PathKind | SpanWidth | Score | Channels | Subtype | Rank | SourceStrategy | Complete |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.7500 | 1.0000 | 1.0000 | 0.0000 |

## Metadata checkable features (task-wide)

| Denom | RRF | SymReg | PathKind | SpanReasonable | RMCTrigger |
|---:|---:|---:|---:|---:|---:|
| 4 | 0.5000 | 0.2500 | 1.0000 | 1.0000 | 0.5000 |

## Metadata gate v0 risk buckets

| Bucket | Count | Rate |
|---|---:|---:|
| metadata_medium_risk | 3 | 0.2500 |
| metadata_unavailable | 0 | 0.0000 |
| metadata_low_risk | 3 | 0.2500 |
| metadata_high_risk | 6 | 0.5000 |

## Pack-level risk diagnostics

| Denom | LowRiskAnchor | HighRiskDistractor | AllMetadataAvail | SourceRequiredUnavailable | GateDiversity |
|---:|---:|---:|---:|---:|---:|
| 9 | 0.3333 | 0.3333 | 0.0000 | 1.0000 | 0.3333 |

## SCORE-phase diagnostic correlations (not used for feature construction)

- Diagnostic correlation availability: `available`

| Bucket | Candidates | GoldFile | GoldSpan | FileRightSpanWrong |
|---:|---:|---:|---:|---:|
| metadata_medium_risk | 3 | 1.0000 | 0.0000 | 1.0000 |
| metadata_unavailable | 0 | n/a | n/a | n/a |
| metadata_low_risk | 3 | 1.0000 | 1.0000 | 0.0000 |
| metadata_high_risk | 3 | 1.0000 | 0.0000 | 1.0000 |

- No-gold high-risk candidate rate: 1.0000 (1/1)

## Conclusion

- Self-test-only verifier inventoried metadata features for 4 synthetic tasks; this is not quality evidence.
- Feature extraction used candidate metadata only (rank, score, channels, subtype axes, path-kind, span width). Gold spans and outcomes were used only for explicitly-marked SCORE-phase diagnostic correlations.
- P52 does not verify source text, does not read files, does not call an LLM, does not construct prompts, does not validate EvidenceCore, does not produce evidence, and does not produce a verifier pass/fail score.
- P52 metadata gates are candidate-risk diagnostics only and do not prove P51/P53 quality.
- Metadata-complete rate (task-wide): 0.0; source-required features availability: unavailable_source_read_not_wired.
