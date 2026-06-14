# R19 Large/Stress Guard Generalization Validation

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R19 Large/Stress Guard Generalization Validation

**Eval-layer research only. Does NOT change Rust core.**

## Safety

All source safety gates passed.
Citation safety is inherited from source validated predictions; no new citation validation is claimed.

### Source Report Safety Summary

- R15-L_safety_passed: True
- R15-L_canary_passed: True
- R15-stress_safety_passed: True
- R15-stress_canary_passed: True
- citation_inherited_from_validated_methods: True
- baseline_prediction_consistency_checked: True
- citation_hash_checked_all_methods: True

## Label Quality

### R15-large
- Total: 294
- Quality distribution: {'mined': 270, 'weak': 24}
- Has gold spans: 270
- Has hard negatives: 270
- Negative count: 24
- **Caveat**: R15-L labels are mostly weak/mined; used only for generalization smoke, not as promotion evidence.

### R15-stress
- Total: 19
- Quality distribution: {'human_reviewed': 3, 'weak': 16}
- Has gold spans: 0
- Has hard negatives: 0
- Negative count: 19
- **Caveat**: R15-stress has only 19 tasks and mostly weak labels; used only as a small false-positive stress surface, not as promotion evidence.

## Strategy Metrics (R15-large)

| Strategy | file_recall@1 | file_recall@5 | file_recall@10 | mrr | span_f0.5@10 | token_waste@10 | hard_negative_hit_rate@10 | negative_nonempty_rate@10 | success_rate |
|---|---|---|---|---|---|---|---|---|---|
| regex | 0.8481 | 0.9407 | 0.9667 | 0.8839 | 0.2698 | 0.6624 | 0.0815 | 0.0417 | 1.0000 |
| bm25 | 0.4593 | 0.6444 | 0.6630 | 0.5341 | 0.1556 | 0.5878 | 0.0889 | 0.9167 | 1.0000 |
| symbol | 0.8222 | 0.8519 | 0.8667 | 0.8381 | 0.3604 | 0.1849 | 0.0148 | 0.0000 | 1.0000 |
| rrf | 0.9111 | 0.9926 | 0.9963 | 0.9489 | 0.2644 | 0.6769 | 0.0815 | 0.9167 | 1.0000 |
| query_only_router_v0 | 0.8852 | 0.9259 | 0.9370 | 0.9022 | 0.3192 | 0.5202 | 0.0556 | 0.3333 | 1.0000 |
| rrf_guarded_by_symbol_regex | 0.9111 | 0.9926 | 0.9963 | 0.9489 | 0.2644 | 0.6769 | 0.0815 | 0.0417 | 1.0000 |
| query_noise_plus_rrf_agree_min_0.0 | 0.9037 | 0.9815 | 0.9852 | 0.9406 | 0.2632 | 0.6664 | 0.0815 | 0.0000 | 1.0000 |
| query_noise_plus_rrf_agree_min_0.02 | 0.9000 | 0.9741 | 0.9778 | 0.9350 | 0.2625 | 0.6595 | 0.0815 | 0.0000 | 1.0000 |
| query_noise_plus_rrf_score_min_0.02 | 0.9000 | 0.9741 | 0.9778 | 0.9350 | 0.2625 | 0.6595 | 0.0815 | 0.0000 | 1.0000 |

## Strategy Metrics (R15-stress)

| Strategy | file_recall@1 | file_recall@5 | file_recall@10 | mrr | span_f0.5@10 | token_waste@10 | hard_negative_hit_rate@10 | negative_nonempty_rate@10 | success_rate |
|---|---|---|---|---|---|---|---|---|---|
| regex | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0.4737 | 1.0000 |
| bm25 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0.6842 | 1.0000 |
| symbol | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0.1053 | 1.0000 |
| rrf | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0.6842 | 1.0000 |
| query_only_router_v0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0.1579 | 1.0000 |
| rrf_guarded_by_symbol_regex | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0.4737 | 1.0000 |
| query_noise_plus_rrf_agree_min_0.0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0.0000 | 1.0000 |
| query_noise_plus_rrf_agree_min_0.02 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0.0000 | 1.0000 |
| query_noise_plus_rrf_score_min_0.02 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | 0.0000 | 1.0000 |

## Deltas vs RRF Baseline

### R15-large

**query_only_router_v0 vs RRF:**
- file_recall@1: -0.0259
- file_recall@5: -0.0667
- file_recall@10: -0.0593
- mrr: -0.0467
- span_f0.5@10: +0.0549
- token_waste@10: -0.1567
- hard_negative_hit_rate@10: -0.0259
- negative_nonempty_rate@10: -0.5833

**rrf_guarded_by_symbol_regex vs RRF:**
- file_recall@1: +0.0000
- file_recall@5: +0.0000
- file_recall@10: +0.0000
- mrr: +0.0000
- span_f0.5@10: +0.0000
- token_waste@10: +0.0000
- hard_negative_hit_rate@10: +0.0000
- negative_nonempty_rate@10: -0.8750

**query_noise_plus_rrf_agree_min_0.0 vs RRF:**
- file_recall@1: -0.0074
- file_recall@5: -0.0111
- file_recall@10: -0.0111
- mrr: -0.0083
- span_f0.5@10: -0.0012
- token_waste@10: -0.0105
- hard_negative_hit_rate@10: +0.0000
- negative_nonempty_rate@10: -0.9167

**query_noise_plus_rrf_agree_min_0.02 vs RRF:**
- file_recall@1: -0.0111
- file_recall@5: -0.0185
- file_recall@10: -0.0185
- mrr: -0.0139
- span_f0.5@10: -0.0019
- token_waste@10: -0.0174
- hard_negative_hit_rate@10: +0.0000
- negative_nonempty_rate@10: -0.9167

**query_noise_plus_rrf_score_min_0.02 vs RRF:**
- file_recall@1: -0.0111
- file_recall@5: -0.0185
- file_recall@10: -0.0185
- mrr: -0.0139
- span_f0.5@10: -0.0019
- token_waste@10: -0.0174
- hard_negative_hit_rate@10: +0.0000
- negative_nonempty_rate@10: -0.9167

### R15-stress

**query_only_router_v0 vs RRF:**
- negative_nonempty_rate@10: -0.5263

**rrf_guarded_by_symbol_regex vs RRF:**
- negative_nonempty_rate@10: -0.2105

**query_noise_plus_rrf_agree_min_0.0 vs RRF:**
- negative_nonempty_rate@10: -0.6842

**query_noise_plus_rrf_agree_min_0.02 vs RRF:**
- negative_nonempty_rate@10: -0.6842

**query_noise_plus_rrf_score_min_0.02 vs RRF:**
- negative_nonempty_rate@10: -0.6842

## Deltas vs Symbol Baseline

### R15-large

**query_only_router_v0 vs Symbol:**
- file_recall@1: +0.0630
- file_recall@5: +0.0741
- file_recall@10: +0.0704
- mrr: +0.0641
- span_f0.5@10: -0.0412
- token_waste@10: +0.3354
- hard_negative_hit_rate@10: +0.0407
- negative_nonempty_rate@10: +0.3333

**rrf_guarded_by_symbol_regex vs Symbol:**
- file_recall@1: +0.0889
- file_recall@5: +0.1407
- file_recall@10: +0.1296
- mrr: +0.1108
- span_f0.5@10: -0.0960
- token_waste@10: +0.4920
- hard_negative_hit_rate@10: +0.0667
- negative_nonempty_rate@10: +0.0417

**query_noise_plus_rrf_agree_min_0.0 vs Symbol:**
- file_recall@1: +0.0815
- file_recall@5: +0.1296
- file_recall@10: +0.1185
- mrr: +0.1025
- span_f0.5@10: -0.0972
- token_waste@10: +0.4815
- hard_negative_hit_rate@10: +0.0667
- negative_nonempty_rate@10: +0.0000

**query_noise_plus_rrf_agree_min_0.02 vs Symbol:**
- file_recall@1: +0.0778
- file_recall@5: +0.1222
- file_recall@10: +0.1111
- mrr: +0.0969
- span_f0.5@10: -0.0979
- token_waste@10: +0.4746
- hard_negative_hit_rate@10: +0.0667
- negative_nonempty_rate@10: +0.0000

**query_noise_plus_rrf_score_min_0.02 vs Symbol:**
- file_recall@1: +0.0778
- file_recall@5: +0.1222
- file_recall@10: +0.1111
- mrr: +0.0969
- span_f0.5@10: -0.0979
- token_waste@10: +0.4746
- hard_negative_hit_rate@10: +0.0667
- negative_nonempty_rate@10: +0.0000

### R15-stress

**query_only_router_v0 vs Symbol:**
- negative_nonempty_rate@10: +0.0526

**rrf_guarded_by_symbol_regex vs Symbol:**
- negative_nonempty_rate@10: +0.3684

**query_noise_plus_rrf_agree_min_0.0 vs Symbol:**
- negative_nonempty_rate@10: -0.1053

**query_noise_plus_rrf_agree_min_0.02 vs Symbol:**
- negative_nonempty_rate@10: -0.1053

**query_noise_plus_rrf_score_min_0.02 vs Symbol:**
- negative_nonempty_rate@10: -0.1053

## Generalization Assessment

- **selected_candidate_large_ok**: True
- **selected_candidate_stress_ok**: False
- **stress_zero_observation_repeated**: True
- **promotion_ready**: False
- **Reason**: R15-L labels are weak/mined; R15-stress has only 19 tasks. No promotion from R19 generalization smoke. Requires human-verified labels and larger stress dataset.

## Conclusions

1. rrf_guarded_by_symbol_regex generalizes to R15-L: negative_nonempty 0.042 vs RRF 0.917 (delta -0.875), FileRecall@1 0.911 vs RRF 0.911 (delta +0.000). However, R15-L labels are weak/mined; this is generalization smoke only, not promotion evidence.
2. rrf_guarded_by_symbol_regex stress negative_nonempty 0.474 > symbol baseline 0.105. The selected candidate does NOT improve stress beyond symbol. Query noise guard is needed for stress improvement.
3. query_noise_plus_rrf_agree_min_0.0 achieves stress negative_nonempty=0.000, repeating the R18 observation. On R15-L, negative_nonempty=0.000 with FileRecall@1=0.9037. This is an observation, not promotion evidence; R15-L labels are weak/mined and stress is only 19 tasks.
4. No core default promotion from R19: R15-L labels are weak/mined, R15-stress has only 19 tasks. Generalization smoke only.
5. No LLM/dense/provider claims. All routing uses query text and prediction features only.

## Caveats

- R19 is an eval-layer generalization validation; does NOT change Rust core.
- R15-L labels are mostly weak/mined; used for generalization smoke only, not as promotion evidence.
- R15-stress has only 19 tasks; metric estimates are very noisy.
- R15-L has 294 tasks but label quality is predominantly 'mined' and 'weak'; recall/precision numbers are not reliable for quality conclusions.
- Guard strategies were calibrated on R15-M in R18; R15-L generalization is a smoke test, not a validation.
- Citation safety is inherited from validated source predictions; no new citation validation is claimed for guard-produced evidence.
- No LLM/dense/provider claims are made.
- Routing decisions are deterministic and reproducible from the same inputs.
- promotion_ready is always false in R19; requires human-verified labels and larger stress dataset.

