# P22/P23 Evidence-Seeking Retrieval Policy Surface

P22 freezes the decision surface of the current evidence-seeking retrieval policy. P23 decomposes local candidate strategy failures into actionable bottleneck categories.

## Safety / Policy

- promotion_ready: `False`
- default_should_change: `False`
- evidencecore_semantics_changed: `False`
- core_changes: `False`
- external_calls: `0`

## P22 Decision Surface Freeze

- schema_version: `p22-p23-policy-surface-v1`
- tasks_scored: `120`
- repos_available: `9 / 9`

### Input Hashes

| Input | SHA256 |
|---|---|
| repo_lock | `3d60ab401cfb77ad906f61625f32129972b881808d147ee7c7d3489bfa77666d` |
| tasks | `868d21de2c6f955ebf4dcb7235c100e03c0be7c71425ee99bd20155bf1f5c39c` |
| labels | `b7add2500c203aa644339156fd6e557df54232ad282381a3474ea58aa1afddd8` |

## P23 Bottleneck Decomposition

| Strategy | Pos | NoGold | Reach@5 | SpanReach@5 | Absent | FileWrong | FRSW | NoGoldFP | Abstain | FileRec@5 | SpanF0.5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| regex | 0 | 120 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | None | None |
| bm25 | 0 | 120 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.2833333333333333 | 0.7166666666666667 | None | None |
| symbol | 0 | 120 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | None | None |
| rrf | 0 | 120 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.2833333333333333 | 0.7166666666666667 | None | None |
| symbol_regex_union | 0 | 120 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | None | None |
| rrf_guarded_by_symbol_regex | 0 | 120 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | None | None |

## Bottleneck Summary

- surface_type: `guard_only_no_gold`
- best_candidate_reach_strategy: `None`
- highest_no_gold_false_primary_strategy: `bm25`
- research_baseline_candidate_for_p25_p30: `rrf_guarded_by_symbol_regex`

P22/P23 are research-only; none of these local deterministic strategies should change defaults. Use RRF as the recall reference and research_baseline_candidate_for_p25_p30 only as a research baseline candidate for P25 admission/filter refinements and P30 guard experiments.

## Next Steps for P25/P30

1. Use the research baseline candidate only for P25/P30 experiments; it is not a default recommendation.
2. Target the highest observed failure bucket (candidate_absent, file_wrong, or file_right_span_wrong) with source-category-specific guards.
3. Re-run after any EvidenceCore or retrieval change to refresh the P22 surface manifest.
