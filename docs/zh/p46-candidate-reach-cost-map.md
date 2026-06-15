# P46 候选召回 × 成本 / 候选到证据物化门

> 中文译本待补充。以下内容保留英文原文以便查阅。

## English source / 英文原文

# P46 Candidate Reach × Cost / Candidate-to-Evidence Materialization Gate

## Purpose

P46 measures how much candidate evidence reaches private gold spans (`reach`) and how much
span-level false risk each strategy incurs (`cost`).  It is a SCORE-phase-only diagnostic that
uses the P31-H1 candidate-pool handoff and P33-B subtype handoff, but never emits per-task rows.

## Methodology

- Reads `p25-policy-records-ephemeral-v1` records produced by `p21_llm_rich_candidate.py`.
- Computes aggregate reach@K (GoldFile, GoldSpan, UniqueGoldSpan) per strategy.
- Computes outcome span-cost metrics (added_gold_span, added_false_span, false/gold, net value 1x/2x, SpanF0.5, PFP).
- Includes candidate materialization diagnostics from pool metadata; source-file validation defaults to unavailable unless a checkout root is provided.
- Breaks down reach/cost by public task bucket, risk tag, and P33-B subtype axes when available.
- Replays `bucket_routed_v0` and `admission_v3_h4b` routing decisions to expose route span cost.

## Current placeholder findings

- This report is scaffold / CI placeholder output; do not use it as quality evidence.
- Reach metrics available when `p31_candidate_pools` and `p31_score_gold` are present.
- Materialization source-read availability defaults to `source_read_unavailable`.
- Policy route evaluation depends on route features and subtype handoff.

## Safety posture

- No remote model calls are made during P46 evaluation.
- Public outputs contain only aggregate counts/rates by strategy, public bucket, risk tag, and subtype axis.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`.

## Next unlocks

- P47/P48 should consume this aggregate map to test evidence-materialization gates and budget-aware admission thresholds.
