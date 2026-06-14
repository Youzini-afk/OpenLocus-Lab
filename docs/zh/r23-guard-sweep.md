# R23 Guard Parameter Sweep

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R23 Guard Parameter Sweep

## Objective

Eval-layer guard parameter sweep consuming R21 artifacts and R20 labels. Produces guard parameter sweep with curves and bucket analysis. Does NOT re-run retrieval, does NOT change Rust core.

## Architecture

Strictly analysis-only SCORE phase:
- Loads R21 predictions (rrf, regex, symbol) + R20 labels + R21 report
- Never invokes openlocus CLI
- Labels only in score phase; never used for routing
- Guard semantics: based on raw RRF evidence; if guard condition fails then abstain

## Guard dimensions swept

| Parameter | Values | Semantics |
|---|---|---|
| query_noise_threshold | 0, 1, 2, 3, 4, 5, 6 | Deterministic noise score from vague/fabricated/misspell/noise tokens |
| rrf_score_threshold | 0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.07, 0.1 | RRF top score must exceed threshold |
| regex_agreement_required | True | Regex predictions must have evidence |
| symbol_agreement_required | True | Symbol predictions must have evidence |
| regex_or_symbol_agreement_required | True | Regex OR symbol must have evidence |
| top1_top2_gap_threshold | 0.0, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05 | Top1 score - top2 score must exceed gap |
| identifier_density_threshold | 0, 1, 2, 3 | Query must have >= threshold identifier-like tokens |
| candidate_channel_count_threshold | 0, 1, 2, 3, 4 | Top evidence channels union must have >= threshold channels |

Plus 15 combined strategies covering the most promising parameter combinations from R21/R22 analysis.

## Output

`runs/r23-guard-sweep.json` with:
- `promotion_ready: false`, `not_promotion_evidence: true`
- `source_report_sha`, `labels_sha`, `artifact_manifest_sha` — verified
- `sweep_count` — 51 strategies
- `strategies` — per-strategy params, metrics, bucket_regressions, promotion_blocked_by_bucket_regression
- `curves` — risk_coverage_curve, recall_vs_negative_curve, recall_vs_false_primary_curve, precision_vs_abstain_curve
- `bucket_summary` — by repo, language, query_category/query_type alias, risk_tag, intent_guess, expected_behavior, positive_negative_ambiguous
- `observations` — best observations (not "candidates for default")

## Metrics computed

FileRecall@1/3/5, MRR, SpanF0.5, SpanPrecision, SpanRecall, token_waste, no_gold_nonempty_rate, primary_false_positive_rate, must_not_primary_violation_rate, abstain_rate, weak_candidate_rate, hard_distractor_hit_rate, guard_recall_kill_rate vs raw RRF.

## Bucket regression criteria

A strategy is `promotion_blocked_by_bucket_regression` if:
- Any bucket recall gap vs RRF > 0.15
- no_gold_nonempty_rate > 0.3 in any bucket
- primary_false_positive_rate > 0.3 in any bucket
- guard_recall_kill_rate > 0.1 in any bucket

## Key observations

1. **All 51 strategies have bucket regressions**: Every guard strategy has at least one bucket where the recall gap, no_gold_nonempty_rate, primary_false_positive_rate, or guard_recall_kill_rate exceeds the regression threshold. This confirms R20 labels are diverse enough to surface real trade-offs.

2. **Query noise guard is effective but insufficient alone**: `query_noise_threshold_1` preserves FileRecall@1 (0.693) with zero guard_recall_kill, but no_gold_nonempty_rate remains at 0.437.

3. **Agreement guards reduce false positives without recall cost**: `regex_or_symbol_agreement_required` reduces no_gold_nonempty_rate from 0.495 to 0.279 with zero guard_recall_kill and preserved FileRecall@1 (0.693).

4. **Combined query_noise + agreement is the best R23 guard balance**: `query_noise_1_plus_regex_or_symbol_agree` achieves no_gold_nonempty_rate 0.221 with FileRecall@1 0.693 and zero guard_recall_kill. This mirrors the R21 `query_noise_plus_rrf_agree_min` result.

5. **RRF score threshold above 0.02 causes sharp recall cliff**: Most RRF top scores are concentrated near 0.03-0.06; thresholds above 0.02 reject substantial recall.

6. **top1_top2_gap threshold kills too much recall**: Gap thresholds even at 0.005 cause >50% guard_recall_kill_rate, indicating RRF evidence pairs are often close in score.

7. **Symbol agreement alone kills 22.8% recall**: This confirms the R22 finding that `rrf_guarded_by_symbol` is too aggressive.

8. **No strategy eliminates no_gold_nonempty_rate to zero without unacceptable recall cost**: The strategies that achieve near-zero false positives (gap_threshold >= 0.02) do so by abstaining on >99% of queries.

## Safety

- promotion_ready=false, not_promotion_evidence=true always
- No promotion claims, no dense/LLM/QuIVer quality claims
- Labels only in score phase; never used for routing
- R21 artifacts manifest verified fail-closed for every recorded artifact path, sha256, byte count, and JSONL line count
- Analysis-only no CLI
- R20 labels weak/mined; not promotion evidence

## Caveats

- R20 labels are weak/mined (258 weak, 315 mined_high_confidence, 168 mined); not promotion evidence
- Guard parameter sweep is analysis-only; no Rust core changes
- Bucket regression thresholds (0.15 recall gap, 0.3 no_gold, 0.3 pfp, 0.1 kill) are heuristic
- All strategies blocked by bucket regression; this is expected given R20 label diversity
- Combined strategies are observations, not promotions
- query_noise_score is deterministic/heuristic; not learned from data

