# P51 LLM Span Narrow 2.0 / Candidate Filter Diagnostic

- Schema: `p51-llm-span-narrow-2-diagnostic-v1`
- Generated: 2026-06-15T19:54:53.223998+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P51: 0
- LLM calls by P51: 0
- Prompt construction by P51: False
- Tasks: 7 positive=5 no_gold=2
- Candidate pool availability: `partial`
- Gold span availability: `available`
- Reach metrics available: True
- P52B report source: `not_provided`
- P52A report source: `not_provided`
- P52 report source: `not_provided`
- P49 report source: `not_provided`
- P50 report source: `not_provided`
- P48 report source: `not_provided`

## Purpose

P51 selects diagnostic candidates for a future LLM span-narrow/filter/abstain phase and publishes prompt-blueprint metadata only. It is a deterministic first-tranche scaffold with no live LLM calls.

## Methodology

- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).
- Normalize candidates with P46/P49 helpers, preserving only public metadata in memory.
- Apply a gold-free, deterministic selector based on metadata risk, public task bucket/risk tags, and contrast-pack feasibility; P47/P48 RMC overlay availability is reported separately.
- Build metadata-only prompt-blueprint shapes from selected candidates; no prompt strings are constructed.
- Replay existing P21 role outcomes where present and report aggregate task-level deltas; missing outcomes are unavailable.
- SCORE-phase diagnostics correlate selected candidates with private gold spans after selection; they are not used for selection.

## Safety notes

- P51 first tranche does not call an LLM.
- P51 prompt blueprints are not prompts and are not sent to any provider.
- P51 does not create Evidence, validate EvidenceCore, admit candidates, or change defaults.
- LLM outputs remain candidate/supporting diagnostics only.
- No quality/default/promotion claim is made.

## Candidate selection

- Candidate denominator: 10
- Pack denominator: 2
- Selected for span narrow: 4 (0.4000)
- Selected for filter: 0 (0.0000)
- Selected for abstain review: 0 (0.0000)
- Selection unavailable: 0 (0.0000)
- Skip reason counts:
  - no_contrast_pack: 1 (0.1000)
  - metadata_high_risk: 5 (0.5000)
  - missing_candidate_pool: 1 (0.1000)
  - selection_unavailable: 0 (0.0000)

## Prompt blueprint metadata

- Availability: `available`
- Blueprint count: 6
- Mean candidates per blueprint: 2.0000
- P95 candidates per blueprint: 2.0000
- Mean source-lines budget: 11.0000
- P95 source-lines budget: 12.0000
- Mean context-chars budget: 440.0000
- P95 context-chars budget: 480.0000
- Pack strategy mix: {'topk_flat_pack_v0': 2, 'anchor_contrast_pack_v0': 2, 'conservative_anchor_pack_v0': 2}
- Metadata risk bucket mix: {'metadata_low_risk_count': 6, 'metadata_medium_risk_count': 6, 'metadata_high_risk_count': 0, 'metadata_unavailable_count': 0}
- Path kind mix: {'source': 12}
- Source-feature bucket mix: `unavailable` (per_candidate_source_feature_mix_unavailable_first_tranche)
- Prompt construction by P51: `False`
- Raw prompt text available: `False`

## Existing role replay

- Existing role output availability: `partial_existing_role_outputs`
- Tasks with baseline outcomes: 7
- Tasks with llm_span_narrow outcomes: 3
- Tasks with llm_filter outcomes: 6
- Tasks with llm_abstain_filter outcomes: 4
- Role output coverage rate: 0.2857
- llm_span_narrow ΔSpanF0.5 mean: 0.0300
- llm_span_narrow ΔSpanF0.5 p95: 0.0470
- llm_span_narrow added-gold delta mean: 0.0000
- llm_span_narrow added-false delta mean: -0.6667
- llm_filter false-primary delta mean: -0.1640
- llm_abstain_filter abstained rate: 0.7500

## High-uncertainty diagnostic

- High-uncertainty candidate count: 4 (0.4000)
- High-uncertainty tasks with existing role outputs: 1 (0.5000)
- Existing role helped count: 1 (1.0000)
- Existing role harmed count: 0 (0.0000)

## SCORE-phase diagnostic correlation (not used for selection)

- Gold-file rate selected: 0.5000
- Gold-span rate selected: 0.5000
- File-right-span-wrong rate selected: 0.0000
- No-gold selected rate: 0.0000
- Existing role added-gold span delta mean: 0.0000
- Existing role added-false span delta mean: -1.0000
- Existing role false-per-gold: n/a

## Conclusion

- Self-test-only scaffold selected 4 candidates across 7 synthetic tasks; this is not quality evidence.
- Candidate selection used aggregate metadata and public risk tags only. Gold, source text, and raw queries were not used for selection.
- Prompt blueprints are metadata-only shapes, not constructed prompts, and are not sent to any provider.
- Existing P21 LLM role outcomes were replayed only when present; missing outcomes are reported as unavailable.
- P51 does not call an LLM, does not create Evidence, does not validate EvidenceCore, and does not change defaults or promote candidates.
