# R18 Threshold/Guard Calibration Sweep

**Eval-layer research only. Does NOT change Rust core.**

## Safety

All source safety gates passed.
Citation safety is inherited from source validated predictions; no new citation validation is claimed.

### Source Report Safety Summary

- R15-M_safety_passed: True
- R15-M_canary_passed: True
- R15-stress_safety_passed: True
- R15-stress_canary_passed: True
- citation_inherited_from_validated_methods: True
- baseline_prediction_consistency_checked: True
- citation_hash_checked_all_methods: True

## Repo Split

- Train repos (6): codex2api, fast-context-mcp, gemini-web2api, grok2api, infinite-canvas, kiro2
- Holdout repos (3): smartsearch, triviumdb, windsurf2api

## Sweep Thresholds

[0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05, 0.08]

## Strategy Metrics (full_medium)

| Strategy | file_recall@1 | mrr | span_f0.5@10 | token_waste@10 | hard_negative_hit_rate@10 | negative_nonempty_rate@10 |
|---|---|---|---|---|---|---|
| regex | 0.8519 | 0.8887 | 0.2630 | 0.6767 | 0.2889 | 0.0000 |
| bm25 | 0.5481 | 0.6227 | 0.1884 | 0.6394 | 0.2296 | 0.6452 |
| symbol | 0.8074 | 0.8198 | 0.3103 | 0.2043 | 0.0519 | 0.0000 |
| rrf | 0.9407 | 0.9628 | 0.2519 | 0.6961 | 0.2593 | 0.6452 |
| query_only_router_v0 | 0.9037 | 0.9184 | 0.3146 | 0.5390 | 0.2370 | 0.0000 |
| rrf_guarded_by_symbol_regex | 0.9407 | 0.9628 | 0.2519 | 0.6961 | 0.2593 | 0.0000 |
| rrf_score_min_0.0_regex_or_symbol | 0.8519 | 0.8702 | 0.2124 | 0.6360 | 0.2370 | 0.0000 |
| rrf_score_min_0.0_symbol | 0.8519 | 0.8702 | 0.2124 | 0.6360 | 0.2370 | 0.0000 |
| query_noise_plus_rrf_score_min_0.0 | 0.9407 | 0.9610 | 0.2516 | 0.6891 | 0.2593 | 0.0000 |
| query_noise_plus_rrf_agree_min_0.0 | 0.9407 | 0.9610 | 0.2516 | 0.6891 | 0.2593 | 0.0000 |
| rrf_score_min_0.005_regex_or_symbol | 0.8519 | 0.8702 | 0.2124 | 0.6360 | 0.2370 | 0.0000 |

## Strategy Metrics (train_medium)

| Strategy | file_recall@1 | mrr | span_f0.5@10 | token_waste@10 | hard_negative_hit_rate@10 | negative_nonempty_rate@10 |
|---|---|---|---|---|---|---|
| regex | 0.9111 | 0.9417 | 0.2738 | 0.6520 | 0.3000 | 0.0000 |
| bm25 | 0.4778 | 0.5760 | 0.1873 | 0.5496 | 0.2000 | 0.6190 |
| symbol | 0.8000 | 0.8000 | 0.3042 | 0.1296 | 0.0000 | 0.0000 |
| rrf | 0.9889 | 0.9944 | 0.2626 | 0.6722 | 0.2889 | 0.6190 |
| query_only_router_v0 | 0.9333 | 0.9417 | 0.3262 | 0.4942 | 0.2000 | 0.0000 |
| rrf_guarded_by_symbol_regex | 0.9889 | 0.9944 | 0.2626 | 0.6722 | 0.2889 | 0.0000 |
| rrf_score_min_0.0_regex_or_symbol | 0.8556 | 0.8611 | 0.2092 | 0.5923 | 0.2556 | 0.0000 |
| rrf_score_min_0.0_symbol | 0.8556 | 0.8611 | 0.2092 | 0.5923 | 0.2556 | 0.0000 |
| query_noise_plus_rrf_score_min_0.0 | 0.9889 | 0.9944 | 0.2626 | 0.6722 | 0.2889 | 0.0000 |
| query_noise_plus_rrf_agree_min_0.0 | 0.9889 | 0.9944 | 0.2626 | 0.6722 | 0.2889 | 0.0000 |
| rrf_score_min_0.005_regex_or_symbol | 0.8556 | 0.8611 | 0.2092 | 0.5923 | 0.2556 | 0.0000 |

## Strategy Metrics (holdout_medium)

| Strategy | file_recall@1 | mrr | span_f0.5@10 | token_waste@10 | hard_negative_hit_rate@10 | negative_nonempty_rate@10 |
|---|---|---|---|---|---|---|
| regex | 0.7333 | 0.7827 | 0.2380 | 0.7262 | 0.2667 | 0.0000 |
| bm25 | 0.6889 | 0.7160 | 0.1901 | 0.8192 | 0.2889 | 0.7000 |
| symbol | 0.8222 | 0.8593 | 0.3173 | 0.3537 | 0.1556 | 0.0000 |
| rrf | 0.8444 | 0.8996 | 0.2272 | 0.7439 | 0.2000 | 0.7000 |
| query_only_router_v0 | 0.8444 | 0.8720 | 0.2790 | 0.6285 | 0.3111 | 0.0000 |
| rrf_guarded_by_symbol_regex | 0.8444 | 0.8996 | 0.2272 | 0.7439 | 0.2000 | 0.0000 |
| rrf_score_min_0.0_regex_or_symbol | 0.8444 | 0.8885 | 0.2158 | 0.7232 | 0.2000 | 0.0000 |
| rrf_score_min_0.0_symbol | 0.8444 | 0.8885 | 0.2158 | 0.7232 | 0.2000 | 0.0000 |
| query_noise_plus_rrf_score_min_0.0 | 0.8444 | 0.8941 | 0.2262 | 0.7229 | 0.2000 | 0.0000 |
| query_noise_plus_rrf_agree_min_0.0 | 0.8444 | 0.8941 | 0.2262 | 0.7229 | 0.2000 | 0.0000 |
| rrf_score_min_0.005_regex_or_symbol | 0.8444 | 0.8885 | 0.2158 | 0.7232 | 0.2000 | 0.0000 |

## Strategy Metrics (stress)

| Strategy | file_recall@1 | mrr | span_f0.5@10 | token_waste@10 | hard_negative_hit_rate@10 | negative_nonempty_rate@10 |
|---|---|---|---|---|---|---|
| regex | N/A | N/A | N/A | N/A | N/A | 0.4737 |
| bm25 | N/A | N/A | N/A | N/A | N/A | 0.6842 |
| symbol | N/A | N/A | N/A | N/A | N/A | 0.1053 |
| rrf | N/A | N/A | N/A | N/A | N/A | 0.6842 |
| query_only_router_v0 | N/A | N/A | N/A | N/A | N/A | 0.1579 |
| rrf_guarded_by_symbol_regex | N/A | N/A | N/A | N/A | N/A | 0.4737 |
| query_noise_plus_rrf_agree_min_0.0 | N/A | N/A | N/A | N/A | N/A | 0.0000 |
| query_noise_plus_rrf_agree_min_0.005 | N/A | N/A | N/A | N/A | N/A | 0.0000 |
| query_noise_plus_rrf_agree_min_0.01 | N/A | N/A | N/A | N/A | N/A | 0.0000 |
| query_noise_plus_rrf_agree_min_0.015 | N/A | N/A | N/A | N/A | N/A | 0.0000 |
| query_noise_plus_rrf_score_min_0.02 | N/A | N/A | N/A | N/A | N/A | 0.0000 |

## Selected Calibration Candidate

- **Strategy**: rrf_guarded_by_symbol_regex
- **Selection Rule**: eligible if train negative_nonempty_rate@10<=0.05 AND train FileRecall@1>=(RRF_train FileRecall@1 - 0.05); among eligible maximize train MRR, then minimize token_waste@10, then preserve deterministic strategy generation order
- **Met Constraints**: True

### Selected Candidate Deltas vs RRF

**Full R15-M:**
- file_recall@1: +0.0000
- file_recall@5: +0.0000
- file_recall@10: +0.0000
- mrr: +0.0000
- span_f0.5@10: +0.0000
- token_waste@10: +0.0000
- hard_negative_hit_rate@10: +0.0000
- negative_nonempty_rate@10: -0.6452

**Holdout R15-M:**
- file_recall@1: +0.0000
- file_recall@5: +0.0000
- file_recall@10: +0.0000
- mrr: +0.0000
- span_f0.5@10: +0.0000
- token_waste@10: +0.0000
- hard_negative_hit_rate@10: +0.0000
- negative_nonempty_rate@10: -0.7000

**R15-stress:**
- negative_nonempty_rate@10: -0.2105

## Pareto Frontier (Full R15-M)

Dimensions: maximize FileRecall@1, SpanF0.5@10; minimize negative_nonempty_rate@10, hard_negative_hit_rate@10

- **query_noise_plus_rrf_agree_min_0.05**: file_recall@1=0.0148, span_f0.5@10=0.0017, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.0444
- **query_noise_plus_rrf_agree_min_0.08**: file_recall@1=0.0000, span_f0.5@10=0.0000, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.0000
- **query_noise_plus_rrf_score_min_0.05**: file_recall@1=0.0148, span_f0.5@10=0.0017, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.0444
- **query_noise_plus_rrf_score_min_0.08**: file_recall@1=0.0000, span_f0.5@10=0.0000, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.0000
- **query_only_router_v0**: file_recall@1=0.9037, span_f0.5@10=0.3146, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.2370
- **rrf_guarded_by_symbol_regex**: file_recall@1=0.9407, span_f0.5@10=0.2519, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.2593
- **rrf_score_min_0.05**: file_recall@1=0.0148, span_f0.5@10=0.0017, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.0444
- **rrf_score_min_0.05_regex_or_symbol**: file_recall@1=0.0148, span_f0.5@10=0.0017, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.0444
- **rrf_score_min_0.05_symbol**: file_recall@1=0.0148, span_f0.5@10=0.0017, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.0444
- **rrf_score_min_0.08**: file_recall@1=0.0000, span_f0.5@10=0.0000, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.0000
- **rrf_score_min_0.08_regex_or_symbol**: file_recall@1=0.0000, span_f0.5@10=0.0000, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.0000
- **rrf_score_min_0.08_symbol**: file_recall@1=0.0000, span_f0.5@10=0.0000, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.0000
- **symbol**: file_recall@1=0.8074, span_f0.5@10=0.3103, negative_nonempty_rate@10=0.0000, hard_negative_hit_rate@10=0.0519

## Conclusions

1. Calibration is promising: selected candidate 'rrf_guarded_by_symbol_regex' improves R15-M negative_nonempty from 0.645 to 0.000 (delta -0.645) with FileRecall@1 0.941 vs RRF 0.941 (delta +0.000). Holdout result is reported separately; selection did not use holdout/stress labels.
2. Holdout supports candidate: negative_nonempty 0.000 vs RRF 0.700 (delta -0.700), FileRecall@1 0.844 vs 0.844 (delta +0.000).
3. R15-stress remains the critical failure surface: candidate negative_nonempty 0.474 remains above symbol baseline 0.105. Threshold/guard on prediction features cannot fully suppress stress false positives.
4. Threshold/guard choices are calibrated on mined R15 data and require larger/human-verified validation before promotion. No core default promotion in R18; this is eval-layer calibration.
5. No LLM/dense/provider claims. All routing uses query text and prediction features only.

## Caveats

- R18 is an eval-layer calibration sweep; does NOT change Rust core.
- Calibration is on mined R15 data; not human-verified.
- Repo-holdout split is deterministic but small (9 repos, 3 holdout); not a substitute for cross-dataset validation.
- R15-stress has only 19 tasks; metric estimates are noisy.
- Sweep thresholds are hand-chosen; exhaustive search would be exponential.
- Pareto frontier depends on chosen dimensions; different dimensions may yield different frontiers.
- No core default promotion unless both R15-M and R15-stress negative_nonempty improve without unacceptable recall/MRR regression.
- Citation safety is inherited from validated source predictions; no new citation validation is claimed for sweep-produced evidence.
- No LLM/dense/provider claims are made.
- Routing decisions are deterministic and reproducible from the same inputs.
