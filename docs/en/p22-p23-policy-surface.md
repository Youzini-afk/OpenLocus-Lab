# P22/P23 Evidence-Seeking Retrieval Policy Surface

P22 freezes the current decision surfaces; P23 decomposes where local deterministic candidates lose gold or create false primary.

## Safety / Policy

- promotion_ready: `False`
- default_should_change: `False`
- external_calls: `0`
- run_phase_public_only: `True`
- labels_loaded_after_run: `True`

Terminology note: “research baseline candidate” below is for P25/P30 experiments only. It is not a default/promotion recommendation.

## Surfaces

| Surface | Tasks | Repos | Type | Research baseline candidate | Key conclusion |
|---|---:|---:|---|---|---|
| r20_positive | 120 | 9/9 | positive_only | `symbol_regex_union` | RRF maximizes positive-slice reach (Reach@5=0.975, SpanReach@5=0.95), but symbol has the best SpanF0.5; symbol_regex_union is a better precision/reach experimental baseline for P25/P30 than plain RRF. This capped R20 run has no no-gold tasks. |
| r26_guard | 120 | 9/9 | guard_only_no_gold | `rrf_guarded_by_symbol_regex` | No-gold stress surface confirms BM25/RRF create false primary while symbol/regex/union/guard abstain; use this surface to calibrate admission guards, not gold reach. |

## R20 Positive Surface Metrics

| Strategy | Reach@5 | SpanReach@5 | CandidateAbsent | Top1FileWrong | Top1FileRightSpanWrong | FileRec@5 | SpanF0.5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25 | 0.65 | 0.49166666666666664 | 0.275 | 0.25 | 0.26666666666666666 | 0.65 | 0.14109740213002428 |
| regex | 0.7416666666666667 | 0.7416666666666667 | 0.2 | 0.4166666666666667 | 0.058333333333333334 | 0.7416666666666667 | 0.22254121007936678 |
| rrf | 0.975 | 0.95 | 0.0 | 0.18333333333333332 | 0.05 | 0.975 | 0.23545166444323612 |
| rrf_guarded_by_symbol_regex | 0.975 | 0.95 | 0.0 | 0.18333333333333332 | 0.05 | 0.975 | 0.23545166444323612 |
| symbol | 0.8583333333333333 | 0.85 | 0.14166666666666666 | 0.06666666666666667 | 0.03333333333333333 | 0.8583333333333333 | 0.31693019506014986 |
| symbol_regex_union | 0.9333333333333333 | 0.925 | 0.016666666666666666 | 0.1 | 0.041666666666666664 | 0.9333333333333333 | 0.24362848322649017 |

## R26 Guard/No-Gold Surface Metrics

| Strategy | NoGoldFP | Abstain |
|---|---:|---:|
| bm25 | 0.2833333333333333 | 0.7166666666666667 |
| regex | 0.0 | 1.0 |
| rrf | 0.2833333333333333 | 0.7166666666666667 |
| rrf_guarded_by_symbol_regex | 0.0 | 1.0 |
| symbol | 0.0 | 1.0 |
| symbol_regex_union | 0.0 | 1.0 |

## Policy Implications

1. P25 should not evaluate global LLM roles on a single mixed average; use R20-like positive reach and R26-like guard stress separately.
2. RRF remains the recall base (best reach), but symbol/regex anchors remain necessary for precision and admission.
3. Use RRF as the recall reference, and `symbol_regex_union` as the precision/reach experimental baseline candidate for P25/P30.
4. Admission V3 should treat dense/LLM as supporting actions after local candidate reach and guard surfaces are known.
