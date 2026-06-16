# P60 RMC Policy v2 v0

> 中文译本待补充 / Chinese translation pending
>
> 本文件遵循 `docs/en/` 与 `docs/zh/` 镜像约定。当前保留英文原文，以便在中文译本完成前不丢失内容。

## English source / 英文原文

# P60 RMC Policy v2 v0

- Schema: `p60-rmc-policy-v2-v0`
- Generated: 2026-06-16T12:18:47.898223+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P60: 0
- LLM calls by P60: 0
- Provider config read by P60: False
- Prompt construction by P60: False
- Source reads attempted by P60: False
- Tasks: 8 positive=5 no_gold=3
- Candidate pool availability: `available`
- Gold span availability: `available`
- Reach metrics available: True

## Purpose

P60 advances the `request_more_context` (RMC) diagnostic from P47/P48 geometry/overlay into a comparable policy matrix. For the same frozen candidate/task inputs, each policy selects only the **next diagnostic action**. P60 reports aggregate routing counts, SCORE-phase gold-reach/false-cost diagnostics, and labeled cost/latency **estimates**. RMC is not evidence, not admission, and not a default; P60 declares no winner and recommends no default policy.

## Methodology

- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).
- Build a RUN-phase gold-free construction view: strip `label`, `labels`, `p31_score_gold`, `gold`, `gold_spans`, `has_gold`, and `score_group` before normalization.
- Freeze each policy's per-candidate next-action selection using only public task bucket, risk tags, allowlisted route features, and gold-free candidate/subtype metadata.
- After all selections are frozen, load private labels only for the explicitly-marked `gold_reach_diagnostics` and `false_cost_diagnostics` blocks.
- Output is aggregate-only: counts, rates, and cost/latency estimates by policy; no per-task/per-candidate rows; no winner or default recommendation.

## Safety notes

- P60 does not call an LLM or any remote provider.
- P60 does not create evidence or admit candidates.
- P60 does not read source files.
- P60 does not read provider configuration.
- P60 does not construct prompts or request envelopes.
- P60 does not change defaults or recommend a promotion.
- All cost/latency values are labeled estimates; P60 does not measure real provider spend or latency.

## Policy comparison matrix

| Policy | Family | Availability | CandDenom | RMC_Cands | RMC_Rate | local_verifier | contrastive_pack | p51c_span_narrow | filter | weak_candidate_only |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_p25_bucket_routed_v0 | reference | `available` | 16 | 16 | 1.0000 | 0 | 9 | 1 | 4 | 2 |
| h4b_selective_readmission | reference | `available` | 16 | 16 | 1.0000 | 0 | 3 | 0 | 6 | 7 |
| rmc_all_uncertain | rmc | `available` | 16 | 16 | 1.0000 | 16 | 0 | 0 | 0 | 0 |
| rmc_high_diagnostic_only | rmc | `available` | 14 | 14 | 1.0000 | 8 | 0 | 0 | 6 | 0 |
| rmc_span_overlap_only | rmc | `available` | 14 | 14 | 1.0000 | 0 | 0 | 7 | 7 | 0 |
| rmc_symbol_regex_fusion_only | rmc | `available` | 14 | 14 | 1.0000 | 4 | 0 | 0 | 10 | 0 |
| rmc_high_score_plus_contrast_pack | rmc | `available` | 14 | 14 | 1.0000 | 0 | 2 | 0 | 12 | 0 |
| rmc_high_score_plus_source_backed_verifier | rmc | `available` | 14 | 14 | 1.0000 | 8 | 0 | 0 | 6 | 0 |

## Gold reach diagnostics (SCORE-phase only)

| Policy | PosDenom | GoldFileReach | GoldSpanOverlap | FileRightSpanWrong |
|---|---|---:|---:|---:|---:|
| baseline_p25_bucket_routed_v0 | 5 | 8 | 5 | 3 |
| h4b_selective_readmission | 5 | 8 | 5 | 3 |
| rmc_all_uncertain | 5 | 8 | 5 | 3 |
| rmc_high_diagnostic_only | 5 | 8 | 5 | 3 |
| rmc_span_overlap_only | 5 | 8 | 5 | 3 |
| rmc_symbol_regex_fusion_only | 5 | 8 | 5 | 3 |
| rmc_high_score_plus_contrast_pack | 5 | 8 | 5 | 3 |
| rmc_high_score_plus_source_backed_verifier | 5 | 8 | 5 | 3 |

## False cost diagnostics (SCORE-phase only)

| Policy | NoGoldDenom | RMC_on_NoGold | FalseCost | FalseRate | FalsePerGoldReached |
|---|---|---:|---:|---:|---:|
| baseline_p25_bucket_routed_v0 | 3 | 3 | 2 | 0.6667 | 0.4000 |
| h4b_selective_readmission | 3 | 3 | 3 | 1.0000 | 0.6000 |
| rmc_all_uncertain | 3 | 3 | 0 | 0.0000 | 0.0000 |
| rmc_high_diagnostic_only | 3 | 3 | 2 | 0.6667 | 0.4000 |
| rmc_span_overlap_only | 3 | 3 | 3 | 1.0000 | 0.6000 |
| rmc_symbol_regex_fusion_only | 3 | 3 | 2 | 0.6667 | 0.4000 |
| rmc_high_score_plus_contrast_pack | 3 | 3 | 3 | 1.0000 | 0.6000 |
| rmc_high_score_plus_source_backed_verifier | 3 | 3 | 2 | 0.6667 | 0.4000 |

## Conclusion

- Self-test-only deterministic RMC policy matrix evaluated 8 synthetic tasks; this is not quality evidence.
- Policy selection was gold-free and used only public task metadata, route features, and candidate metadata; labels were loaded only after selections were frozen.
- P60 does not call an LLM, does not create evidence, does not admit candidates, does not read source files, and does not recommend a default policy and declares no winner.
- P60 reports only aggregate next-action routing rates and SCORE-phase reach/false-cost diagnostics; all policies are treated as diagnostic alternatives, not promotion candidates.
- baseline_p25_bucket_routed_v0: rmc_candidate_count=16 next_actions={'contrastive_pack': 9, 'filter': 4, 'p51c_span_narrow': 1, 'weak_candidate_only': 2, 'local_verifier': 0}.
- h4b_selective_readmission: rmc_candidate_count=16 next_actions={'contrastive_pack': 3, 'filter': 6, 'p51c_span_narrow': 0, 'weak_candidate_only': 7, 'local_verifier': 0}.
- rmc_all_uncertain: rmc_candidate_count=16 next_actions={'contrastive_pack': 0, 'filter': 0, 'p51c_span_narrow': 0, 'weak_candidate_only': 0, 'local_verifier': 16}.
- rmc_high_diagnostic_only: rmc_candidate_count=14 next_actions={'contrastive_pack': 0, 'filter': 6, 'p51c_span_narrow': 0, 'weak_candidate_only': 0, 'local_verifier': 8}.
- rmc_span_overlap_only: rmc_candidate_count=14 next_actions={'contrastive_pack': 0, 'filter': 7, 'p51c_span_narrow': 7, 'weak_candidate_only': 0, 'local_verifier': 0}.
- rmc_symbol_regex_fusion_only: rmc_candidate_count=14 next_actions={'contrastive_pack': 0, 'filter': 10, 'p51c_span_narrow': 0, 'weak_candidate_only': 0, 'local_verifier': 4}.
- rmc_high_score_plus_contrast_pack: rmc_candidate_count=14 next_actions={'contrastive_pack': 2, 'filter': 12, 'p51c_span_narrow': 0, 'weak_candidate_only': 0, 'local_verifier': 0}.
- rmc_high_score_plus_source_backed_verifier: rmc_candidate_count=14 next_actions={'contrastive_pack': 0, 'filter': 6, 'p51c_span_narrow': 0, 'weak_candidate_only': 0, 'local_verifier': 8}.
