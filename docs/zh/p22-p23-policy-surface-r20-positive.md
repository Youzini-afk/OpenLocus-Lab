# P22/P23 Evidence-Seeking Retrieval Policy Surface

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

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
| repo_lock | `63cb24b252808c0f5940765452bb3780d0c11b5015b557e168d377fd08fb0681` |
| tasks | `4263364f33b9066c589c682b30dd402f082c13e8bbdf581c39dabb1a92f675ce` |
| labels | `eb827b9c477e9b3975a5e652c4d7d312eecec7e17f28e920f31e0f711564d5b4` |

## P23 Bottleneck Decomposition

| Strategy | Pos | NoGold | Reach@5 | SpanReach@5 | Absent | FileWrong | FRSW | NoGoldFP | Abstain | FileRec@5 | SpanF0.5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| regex | 120 | 0 | 0.7416666666666667 | 0.7416666666666667 | 0.2 | 0.4166666666666667 | 0.058333333333333334 | 0.0 | 0.0 | 0.7416666666666667 | 0.22254121007936678 |
| bm25 | 120 | 0 | 0.65 | 0.49166666666666664 | 0.275 | 0.25 | 0.26666666666666666 | 0.0 | 0.25833333333333336 | 0.65 | 0.14109740213002428 |
| symbol | 120 | 0 | 0.8583333333333333 | 0.85 | 0.14166666666666666 | 0.06666666666666667 | 0.03333333333333333 | 0.0 | 0.1 | 0.8583333333333333 | 0.31693019506014986 |
| rrf | 120 | 0 | 0.975 | 0.95 | 0.0 | 0.18333333333333332 | 0.05 | 0.0 | 0.0 | 0.975 | 0.23545166444323612 |
| symbol_regex_union | 120 | 0 | 0.9333333333333333 | 0.925 | 0.016666666666666666 | 0.1 | 0.041666666666666664 | 0.0 | 0.0 | 0.9333333333333333 | 0.24362848322649017 |
| rrf_guarded_by_symbol_regex | 120 | 0 | 0.975 | 0.95 | 0.0 | 0.18333333333333332 | 0.05 | 0.0 | 0.0 | 0.975 | 0.23545166444323612 |

## Bottleneck Summary

- surface_type: `positive_only`
- best_candidate_reach_strategy: `rrf`
- highest_no_gold_false_primary_strategy: `None`
- research_baseline_candidate_for_p25_p30: `symbol_regex_union`

P22/P23 are research-only; none of these local deterministic strategies should change defaults. Use RRF as the recall reference and research_baseline_candidate_for_p25_p30 only as a research baseline candidate for P25 admission/filter refinements and P30 guard experiments.

## Next Steps for P25/P30

1. Use the research baseline candidate only for P25/P30 experiments; it is not a default recommendation.
2. Target the highest observed failure bucket (candidate_absent, file_wrong, or file_right_span_wrong) with source-category-specific guards.
3. Re-run after any EvidenceCore or retrieval change to refresh the P22 surface manifest.

