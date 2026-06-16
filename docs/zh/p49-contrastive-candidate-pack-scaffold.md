# P49 Contrastive Candidate Pack Scaffold

- Schema: `p49-contrastive-candidate-pack-scaffold-v1`
- Generated: 2026-06-16T18:48:24.905815+00:00
- Status: `self_test_only`
- Self-test: True
- Hard-distractor proxy: `metadata_hard_distractor_proxy_v1`
- Remote calls by P49: 0
- LLM calls by P49: 0
- Source reads by P49: False
- Tasks: 4 positive=3 no_gold=1
- Candidate pool availability: `partial`
- Gold span availability: `available`
- Reach metrics available: True
- P50 report source: `not_provided`
- P48 report source: `not_provided`

## Purpose

P49 builds deterministic candidate-pack shapes from candidate metadata only and reports aggregate pack-shape diagnostics. It is a SCORE-phase-only scaffold, not a policy improvement phase.

## Methodology

- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).
- Normalize raw candidate pools into metadata-only records (rank, score, channels, subtype axes, path-kind).
- Deduplicate candidates by path/span/strategy-affinity privately; never publish identifiers.
- Build three deterministic pack shapes per task: top-k flat, anchor-contrast, and conservative-anchor.
- Pack construction uses metadata only and never gold/outcome/cost signals.
- The `hard_distractor` slot is filled using a metadata-only RUN proxy (`metadata_hard_distractor_proxy_v1`). The proxy is defined over candidate rank, score, path-kind contrast, channel/provenance disagreement, P33B subtype source/agreement class, RRF backing, span-width geometry, same-file/cross-file competitor shape, and public task-bucket/risk tags. Labels, gold, and source text are never used.
- After packs are built, compute SCORE-phase diagnostics using gold spans and outcome costs; these are clearly marked `not_used_for_pack_construction=true`.
- Output is aggregate-only: counts, rates, and distributions by pack strategy, public task bucket, and public risk tag.

## Safety notes

- P49 does not call an LLM.
- P49 does not create evidence.
- P49 does not admit candidate spans.
- P49 does not read source files.
- P49 does not validate content_sha.
- P49 does not change defaults.
- P49 does not prove that future candidate-pack designs will improve quality.
- Pack slots are candidate metadata only; they are not evidence, not validated, and do not represent LLM-ready quality.

## Pack build summary

| Strategy | Denominator | BuildRate | EmptyRate | MeanCands | P95Cands | MeanLines | P95Lines | DedupeDropRate | OverflowRate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| topk_flat_pack_v0 | 3 | 1.0000 | 0.0000 | 1.3333 | 1.9000 | 7.3333 | 10.5000 | 0.7143 | 0.0000 |
| anchor_contrast_pack_v0 | 3 | 1.0000 | 0.0000 | 1.3333 | 1.9000 | 7.3333 | 10.5000 | 0.7143 | 0.0000 |
| conservative_anchor_pack_v0 | 3 | 1.0000 | 0.0000 | 1.3333 | 1.9000 | 7.3333 | 10.5000 | 0.7143 | 0.0000 |

## Contrast metrics

| Strategy | SameFilePair | CrossFilePair | SourceTestPair | DocConfigPair | HardDistractor | RRFAgreement | SymbolRegexAgreement | SubtypeDiversity | PathKindDiversity | ChannelDiversity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| topk_flat_pack_v0 | 0.3333 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.6667 | 0.3333 | 0.0000 | 0.0000 | 0.0000 |
| anchor_contrast_pack_v0 | 0.3333 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.6667 | 0.3333 | 0.0000 | 0.0000 | 0.0000 |
| conservative_anchor_pack_v0 | 0.3333 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.6667 | 0.3333 | 0.0000 | 0.0000 | 0.0000 |

## Provenance completeness

| Strategy | Score | Channels | Subtype | Rank | Span | PathKind | Complete |
|---|---:|---:|---:|---:|---:|---:|---:|
| topk_flat_pack_v0 | 0.0000 | 0.0000 | 0.7500 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| anchor_contrast_pack_v0 | 0.0000 | 0.0000 | 0.7500 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| conservative_anchor_pack_v0 | 0.0000 | 0.0000 | 0.7500 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |

## Hard-distractor repair coverage (metadata-only proxy)

| Strategy | ProxyPackCount | ProxyPackRate | AvailableCount | SlotFillCount | SlotFillRate | OverflowBlocked | Definition |
|---|---:|---:|---:|---:|---:|---:|---|
| topk_flat_pack_v0 | 1 | 0.3333 | 1 | 0 | 0.0000 | 0 | `metadata_hard_distractor_proxy_v1` |
| anchor_contrast_pack_v0 | 1 | 0.3333 | 1 | 1 | 0.3333 | 0 | `metadata_hard_distractor_proxy_v1` |
| conservative_anchor_pack_v0 | 1 | 0.3333 | 1 | 1 | 0.3333 | 0 | `metadata_hard_distractor_proxy_v1` |

## SCORE-phase diagnostics (not used for pack construction)

| Strategy | GoldFileInPack | GoldSpanInPack | GoldSpanInAnchor | GoldSpanInContrast | FileRightSpanWrong | NoGoldPackNonempty | NoGoldHardDistractor | RMCTriggerPack |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| topk_flat_pack_v0 | 1.0000 | 0.5000 | 0.5000 | 0.0000 | 0.5000 | 1.0000 | 0.0000 | 0.6667 |
| anchor_contrast_pack_v0 | 1.0000 | 0.5000 | 0.5000 | 0.0000 | 0.5000 | 1.0000 | 0.0000 | 0.6667 |
| conservative_anchor_pack_v0 | 1.0000 | 0.5000 | 0.5000 | 0.0000 | 0.5000 | 1.0000 | 0.0000 | 0.6667 |

## Conclusion

- Self-test-only scaffold built candidate packs for 4 synthetic tasks; this is not quality evidence.
- Pack construction used candidate metadata only (rank, score, channels, subtype axes, path-kind). Gold and outcome costs were used only for explicitly-marked SCORE-phase diagnostics.
- P49 does not call an LLM, does not create evidence, does not admit candidate spans, does not read source files, does not validate content_sha, and does not change defaults.
- P49 does not prove P51 will improve quality.
- topk_flat_pack_v0: pack_build_denominator=3, pack_build_rate=1.0.
- anchor_contrast_pack_v0: pack_build_denominator=3, pack_build_rate=1.0.
- conservative_anchor_pack_v0: pack_build_denominator=3, pack_build_rate=1.0.
