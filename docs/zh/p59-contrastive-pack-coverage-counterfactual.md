# P59 Contrastive Pack Coverage & Counterfactual Study v0

- Schema: `p59-contrastive-pack-coverage-counterfactual-v0`
- Generated: 2026-06-16T18:48:25.030514+00:00
- Status: `self_test_only`
- Self-test: True
- Hard-distractor proxy: `metadata_hard_distractor_proxy_v1`
- Hard-distractor labels not used for pack construction: True
- Remote calls by P59: 0
- LLM calls by P59: 0
- Provider config read by P59: False
- Prompt construction by P59: False
- Source reads attempted by P59: False
- Tasks: 8 positive=7 no_gold=1
- Candidate pool availability: `available`
- Gold span availability: `available`
- Reach metrics available: True

## Purpose

P59 rebuilds deterministic P49 candidate packs in memory and reports whether the frozen packs contain the prerequisite contrastive information a later LLM role would need, **before** any LLM spend. It is a pre-spend prerequisite diagnostic, not a quality evaluator, not admission, not Evidence, and not a default/promotion gate.

## Methodology

- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).
- Rebuild P49 packs deterministically using candidate metadata only; no gold/labels are used during pack construction.
- Measure gold-free contrastive coverage: same-file competitors, hard distractors, source/test pairs, doc/source pairs, cross-file competitors, path-kind/channel/subtype diversity.
- Hard-distractor coverage uses the P49 metadata-only RUN proxy (`metadata_hard_distractor_proxy_v1`). The proxy uses candidate rank, score, path-kind, channel, subtype, RRF backing, span-width, and public task-bucket/risk tags; labels, gold, and source text are never used.
- Report RUN-phase `hard_distractor_repair_coverage` (proxy-based) and SCORE-phase `score_phase_hard_distractor_coverage` (label-backed denominator, `not_used_for_pack_construction=true`).
- Record `actionability_thresholds` with the minimum rates and actual denominators used by the P61-compatible `llm_spend_actionability_bucket` enum.
- After packs are frozen, load labels only for the explicitly-marked SCORE-phase coverage and counterfactual diagnostics.
- Output is aggregate-only: counts, rates, and coverage breakdowns by public task bucket, public risk tag, and pack strategy.

## Safety notes

- P59 does not call an LLM.
- P59 does not create evidence.
- P59 does not admit candidate spans.
- P59 does not read source files.
- P59 does not validate content_sha.
- P59 does not change defaults.
- P59 does not claim that packs are high-quality or that a future LLM will succeed.
- Pack slots are candidate metadata only; they are not evidence, not validated, and do not represent LLM-ready quality.

## Pack coverage summary

| Strategy | Denominator | Nonempty | NonemptyRate | GoldSpanCoverage | GoldFileCoverage | FileRightSpanWrong | HardDistractorRate | CrossFileRate | SameFileRate | SourceTestRate | DocSourceRate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| topk_flat_pack_v0 | 8 | 8 | 1.0000 | 0.8571 | 1.0000 | 0.1429 | 0.8750 | 0.7500 | 0.2500 | 0.1250 | 0.1250 |
| anchor_contrast_pack_v0 | 8 | 8 | 1.0000 | 0.8571 | 1.0000 | 0.1429 | 0.8750 | 0.7500 | 0.2500 | 0.1250 | 0.1250 |
| conservative_anchor_pack_v0 | 8 | 8 | 1.0000 | 0.8571 | 1.0000 | 0.1429 | 0.8750 | 0.7500 | 0.2500 | 0.1250 | 0.1250 |

## Hard-distractor repair coverage (RUN phase, metadata-only proxy)

| Strategy | ProxyPackCount | ProxyPackRate | AvailableCount | SlotFillCount | SlotFillRate | OverflowBlocked | Definition |
|---|---:|---:|---:|---:|---:|---:|---|
| topk_flat_pack_v0 | 7 | 0.8750 | 7 | 0 | 0.0000 | 0 | `metadata_hard_distractor_proxy_v1` |
| anchor_contrast_pack_v0 | 7 | 0.8750 | 7 | 1 | 0.1250 | 0 | `metadata_hard_distractor_proxy_v1` |
| conservative_anchor_pack_v0 | 7 | 0.8750 | 7 | 1 | 0.1250 | 0 | `metadata_hard_distractor_proxy_v1` |

## SCORE-phase hard-distractor coverage (label-backed, not used for pack construction)

| Strategy | Availability | Denominator | PresentCount | PresentRate | MissingCount | MissingRate |
|---|---|---:|---:|---:|---:|---:|
| topk_flat_pack_v0 | available | 7 | 6 | 0.8571 | 1 | 0.1429 |
| anchor_contrast_pack_v0 | available | 7 | 6 | 0.8571 | 1 | 0.1429 |
| conservative_anchor_pack_v0 | available | 7 | 6 | 0.8571 | 1 | 0.1429 |

## Counterfactual actionability

| Strategy | SpanNarrowDenom | GoldPresent | Impossible | FilterDenom | HardPresent | MissingContrast | Joint | MinGoldRate | MinHardRate | Actionability |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| topk_flat_pack_v0 | 7 | 6 | 1 | 8 | 7 | 1 | 5 | 0.5 | 0.5 | `actionable` |
| anchor_contrast_pack_v0 | 7 | 6 | 1 | 8 | 7 | 1 | 5 | 0.5 | 0.5 | `actionable` |
| conservative_anchor_pack_v0 | 7 | 6 | 1 | 8 | 7 | 1 | 5 | 0.5 | 0.5 | `actionable` |

## Conclusion

- Self-test-only deterministic pack coverage diagnostic rebuilt P49 packs for 8 synthetic tasks; this is not quality evidence.
- Pack construction was gold-free and used only candidate metadata; labels were loaded only after packs were frozen.
- P59 does not call an LLM, does not create evidence, does not admit candidate spans, does not read source files, does not validate content_sha, and does not change defaults.
- P59 reports only aggregate preconditions for later LLM spend; it does not claim that packs are high-quality or that an LLM will succeed.
- topk_flat_pack_v0: pack_build_denominator=8, pack_nonempty_count=8.
- anchor_contrast_pack_v0: pack_build_denominator=8, pack_nonempty_count=8.
- conservative_anchor_pack_v0: pack_build_denominator=8, pack_nonempty_count=8.
