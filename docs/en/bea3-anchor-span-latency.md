# BEA-3 Anchor/Span/Latency-Aware Policy Smoke

Date: 2026-06-21 (BEA-3 anchor/span/latency-aware policy smoke over fresh
heldout ContextBench verified Python rows offset 60 + RepoQA Python needles
offset 30, with private per-record SCORE JSONL in `/tmp` and records-shaped
aggregate-only public artifact)

BEA-3 implements a **frozen BEA v0.3 algorithmic policy** that targets
BEA-2's mixed result: preserve file/MRR/success gains while reducing
span_f0.5 and latency regressions. v0.3 reserves anchor slots for
BM25/agreement anchors, applies diversity/risk scoring to remaining budget,
adds runtime-clean span/latency proxies (tighter line-span bonus,
same-file-as-anchor support bonus, risk bucket penalties, weak-support +
low-BM25 penalty, fixed marginal-priority early stop after anchors), and is
compared against v0.2, v0, and same-budget controls on fresh heldout
records.

BEA-3 is explicitly **not** a benchmark result, **not** a leaderboard entry,
**not** a performance claim, **not** a method-winner claim, **not** a
calibration claim, **not** a promotion, **not** a default/policy change, and
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change.

> `claim_level = bea_v03_policy_smoke_only`. All no-claim /
> no-runtime-change flags false.

## v0.3 frozen policy

`bea_v0_3_anchor_span_latency`:

- reserve first `anchor_count=min(2,budget)` slots for BM25/agreement anchors;
- apply diversity/risk scoring only to remaining budget;
- add runtime-clean span/latency proxies: tighter line-span bonus,
  same-file-as-anchor support bonus, risk bucket penalties, weak-support +
  low-BM25 penalty, fixed marginal-priority early stop after anchors;
- never use gold labels/spans/files, row/needle IDs, repo identity, outcome
  history, provider/model identity, or benchmark-only labels.

Frozen weights: `anchor=0.35`, `span_tight=0.15`,
`anchor_file_support=0.10`, `weak_support_penalty=-0.20`,
`early_stop_margin=0.05`. These are NOT tuned from outcomes.

Required ablations: `v0_3_no_anchor` (no anchor reservation),
`v0_3_no_early_stop` (no marginal-priority early stop).

## Required arms

`bea_v0_3_anchor_span_latency`, `bea_v0_3_no_anchor`,
`bea_v0_3_no_early_stop`, `bea_v0_2_diversity_risk`, `bea_v0`,
`bm25_prefix_same_budget`, `agreement_only_same_budget`,
`seeded_random_same_budget`, `rrf_same_budget` when available.

## Fresh primary slice

ContextBench offset 60, limit 20. RepoQA offset 30, limit 10. Local smoke
uses smaller bounds (3+2) for speed; CI uses full 20+10.

## Public artifact shape

Records only (no dynamic arm dicts):

- `benchmark_arm_metric_records`: `{benchmark, arm, metric, value, record_count}`
- `delta_records`: `{baseline_arm, treatment_arm, metric, delta}`
- `mechanism_contrast_records`: `{contrast, baseline_arm, treatment_arm, metric, delta, record_count}`
- `win_tie_loss_records`: `{baseline_arm, treatment_arm, metric, win, tie, loss, record_count}`
- `mechanism_summary_records`: `{mechanism_field, value, record_count}` (anchor_used_rate, early_stop_rate, mean_budget_used, mean_latency_seconds, mean_span_extent, span_proxy_bucket counts)
- aggregate-only `private_score_manifest`

Metrics: `file_recall@10`, `mrr`, `span_f0.5@10`, `success_rate`,
`evidence_budget_used`, `candidate_count_read`, `latency_seconds`,
`quality_per_candidate`, `quality_per_latency`.

## Latency attribution

All arms share the candidate-collection latency (fair attribution). v0.3
also gets incremental policy time. Controls get 0.0 (in-process, no
retrieval).

## Validation

```text
python3 -m py_compile eval/bea3_anchor_span_latency.py  => PASS
python3 eval/bea3_anchor_span_latency.py --self-test  => PASS (225/225 checks)
python3 eval/bea3_anchor_span_latency.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 60 --contextbench-row-limit 3 \
  --repoqa-needle-offset 30 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea3_anchor_span_latency/bea3_anchor_span_latency_report.json  => PASS
  (status: bea3_anchor_span_latency_pass, 5 records successful,
   private_score_manifest.record_count=45 (5×9 arms),
   private_score_storage_class=tmp_private,
   private_score_path_publicly_serialized=false,
   provider_calls=0, forbidden_scan=pass)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Manual CI result (run `27942492278`, 2026-06-21)

Fixed CI run `27942492278` passed after adding the required v0.3-vs-v0.2
`delta_records` validation. The superseded green run `27941717490` is not used as
the result artifact because its public delta surface was incomplete.

30 records successful (ContextBench 20 + RepoQA 10). 270 private SCORE rows
(30 × 9 arms). `forbidden_scan=pass`, `provider_calls=0`,
`private_score_manifest.record_count=270`, `path_publicly_serialized=false`,
`aggregate_runtime_seconds=398.532`.

BEA v0.3 vs BEA v0.2 on the 30-record CI slice:

```text
file_recall@10 delta: 0.0        (win=0, tie=30, loss=0)
mrr delta: 0.0                   (win=0, tie=30, loss=0)
span_f0.5@10 delta: +0.00217     (win=1, tie=29, loss=0)
success_rate delta: 0.0          (win=0, tie=30, loss=0)
latency_seconds delta: +0.001098
evidence_budget_used delta: 0.0
quality_per_latency delta: +0.000292
```

BEA v0.3 vs BEA v0 / same-budget BM25 / agreement-only / RRF on the same
slice: file_recall@10 +0.066667, mrr +0.130556, success_rate +0.066667,
span_f0.5@10 -0.010068. Against seeded random: file_recall@10 +0.2, mrr
+0.231667, span_f0.5@10 +0.015826, success_rate +0.2.

Mechanism summary: anchor_used_rate=1.0, early_stop_rate=0.0,
mean_budget_used=4.333333, mean_latency_seconds=8.7516,
mean_span_extent=4.246667.

Interpretation: v0.3 did not materially improve file/MRR/success over v0.2 on
this slice; it produced a tiny positive span/quality-per-latency signal with
near-identical latency. This is a weak/mixed smoke result, not a method winner or
default-policy claim.

## Caveats

- BEA-3 is eval/diagnostic only. NOT benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value claim.
- v0.3 weights are frozen constants, NOT tuned from outcomes.
- Bounded CI sample (30 records). Smoke, not rigorous evaluation.
- v0.3 is effectively tied with v0.2 on file/MRR/success, with only a tiny
  positive span/quality-per-latency signal.
- All no-claim / no-runtime-change flags false; EvidenceCore semantics
  unchanged. BEA-0/BEA-1/BEA-2 semantics not mutated.
