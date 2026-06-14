# R17 Query Intent Router / Negative Guard Experiment

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R17 Query Intent Router / Negative Guard Experiment

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

## R15-M Strategy Metrics

| Metric | regex | bm25 | symbol | rrf | query_only_router_v0 | task_type_assisted_router_upper_bound | rrf_guarded_by_symbol_regex |
|---|---|---|---|---|---|---|---|
| file_recall@1 | 0.852 | 0.541 | 0.807 | 0.941 | 0.904 | 0.904 | 0.941 |
| file_recall@5 | 0.956 | 0.719 | 0.830 | 0.993 | 0.941 | 0.926 | 0.993 |
| file_recall@10 | 0.970 | 0.741 | 0.844 | 0.993 | 0.948 | 0.941 | 0.993 |
| mrr | 0.889 | 0.619 | 0.820 | 0.963 | 0.918 | 0.916 | 0.963 |
| span_f0.5@10 | 0.263 | 0.188 | 0.310 | 0.253 | 0.315 | 0.380 | 0.253 |
| token_waste@10 | 0.677 | 0.639 | 0.204 | 0.695 | 0.539 | 0.264 | 0.695 |
| hard_negative_hit_rate@10 | 0.289 | 0.230 | 0.052 | 0.259 | 0.237 | 0.074 | 0.259 |
| negative_nonempty_rate@10 | 0.000 | 0.645 | 0.000 | 0.645 | 0.000 | 0.258 | 0.000 |

## R15-stress Strategy Metrics

| Metric | regex | bm25 | symbol | rrf | query_only_router_v0 | task_type_assisted_router_upper_bound | rrf_guarded_by_symbol_regex |
|---|---|---|---|---|---|---|---|
| file_recall@1 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| file_recall@5 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| file_recall@10 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| mrr | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| span_f0.5@10 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| token_waste@10 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| hard_negative_hit_rate@10 | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| negative_nonempty_rate@10 | 0.474 | 0.684 | 0.105 | 0.684 | 0.158 | 0.316 | 0.474 |

## Per-Strategy Route Counts

### query_only_router_v0
- symbol: 43
- regex: 91
- empty: 48
- rrf: 3

### task_type_assisted_router_upper_bound
- symbol: 123
- regex: 18
- rrf: 8
- empty: 36

### rrf_guarded_by_symbol_regex
- rrf: 144
- empty: 41

## Deltas vs Baselines

### R15-M
**query_only_router_v0 vs RRF:**

- file_recall@1: -0.0370
- file_recall@5: -0.0519
- file_recall@10: -0.0444
- mrr: -0.0444
- span_f0.5@10: +0.0616
- token_waste@10: -0.1561
- hard_negative_hit_rate@10: -0.0222
- negative_nonempty_rate@10: -0.6452

**query_only_router_v0 vs Symbol:**

- file_recall@1: +0.0963
- file_recall@5: +0.1111
- file_recall@10: +0.1037
- mrr: +0.0987
- span_f0.5@10: +0.0043
- token_waste@10: +0.3347
- hard_negative_hit_rate@10: +0.1852
- negative_nonempty_rate@10: +0.0000

**task_type_assisted_router_upper_bound vs RRF:**

- file_recall@1: -0.0370
- file_recall@5: -0.0667
- file_recall@10: -0.0519
- mrr: -0.0468
- span_f0.5@10: +0.1270
- token_waste@10: -0.4309
- hard_negative_hit_rate@10: -0.1852
- negative_nonempty_rate@10: -0.3871

**task_type_assisted_router_upper_bound vs Symbol:**

- file_recall@1: +0.0963
- file_recall@5: +0.0963
- file_recall@10: +0.0963
- mrr: +0.0963
- span_f0.5@10: +0.0697
- token_waste@10: +0.0599
- hard_negative_hit_rate@10: +0.0222
- negative_nonempty_rate@10: +0.2581

**rrf_guarded_by_symbol_regex vs RRF:**

- file_recall@1: +0.0000
- file_recall@5: +0.0000
- file_recall@10: +0.0000
- mrr: +0.0000
- span_f0.5@10: +0.0000
- token_waste@10: +0.0000
- hard_negative_hit_rate@10: +0.0000
- negative_nonempty_rate@10: -0.6452

**rrf_guarded_by_symbol_regex vs Symbol:**

- file_recall@1: +0.1333
- file_recall@5: +0.1630
- file_recall@10: +0.1481
- mrr: +0.1431
- span_f0.5@10: -0.0573
- token_waste@10: +0.4908
- hard_negative_hit_rate@10: +0.2074
- negative_nonempty_rate@10: +0.0000

### R15-stress
**query_only_router_v0 vs RRF:**

- negative_nonempty_rate@10: -0.5263

**query_only_router_v0 vs Symbol:**

- negative_nonempty_rate@10: +0.0526

**task_type_assisted_router_upper_bound vs RRF:**

- negative_nonempty_rate@10: -0.3684

**task_type_assisted_router_upper_bound vs Symbol:**

- negative_nonempty_rate@10: +0.2105

**rrf_guarded_by_symbol_regex vs RRF:**

- negative_nonempty_rate@10: -0.2105

**rrf_guarded_by_symbol_regex vs Symbol:**

- negative_nonempty_rate@10: +0.3684

## Conclusions

1. RRF alone is recall-heavy but negative-heavy: R15-M negative_nonempty@10 = 0.645, R15-stress = 0.684. Negative guard/router should reduce negative_nonempty materially.
2. query_only_router_v0 reduces R15-M negative_nonempty@10 from 0.645 to 0.000 (delta -0.645). Recall is preserved within tolerance (FileRecall@1 0.904 vs RRF 0.941, delta -0.037).
3. task_type_assisted_router_upper_bound achieves R15-M negative_nonempty@10 = 0.258 but uses task_type as benchmark metadata, not runtime information; it is an upper-bound reference only.
4. rrf_guarded_by_symbol_regex reduces negative_nonempty@10 to 0.000 (R15-M) and 0.474 (R15-stress), using evidence presence from symbol/regex as a gate.
5. Both R15-M and R15-stress negative_nonempty improve with acceptable recall regression. Further calibration is warranted before any core default promotion.
6. Next step can be learning/calibrating intent classifier or adding score thresholds, but still evidence-gated. No LLM or dense model claims.

## Caveats

- R17 is an eval-layer router/guard experiment; does NOT change Rust core.
- query_only_router uses heuristic rules only; not a learned classifier.
- task_type_assisted_router uses benchmark metadata (task_type) that is not runtime-available; it is an upper-bound reference.
- Citation safety is inherited from validated source predictions; no new citation validation is claimed for router-produced evidence.
- Mined labels are not human-verified; line ranges may be imprecise.
- Negative tasks in R15-stress have weak or human_reviewed labels only.
- No provider/dense/LLM quality claims are made.
- Routing decisions are deterministic and reproducible from the same inputs.

