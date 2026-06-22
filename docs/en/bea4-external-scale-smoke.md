# BEA-4 External Scale Smoke

Date: 2026-06-21 (BEA-4 external scale smoke for the frozen BEA v0.3 policy,
over a larger fresh external slice — ContextBench verified Python rows offset
80 + RepoQA Python needles offset 40 — with private per-record SCORE JSONL
in `/tmp` and records-shaped aggregate-only public artifact including
worst-slice visibility)

BEA-4 is the **external scale smoke** for the frozen BEA v0.3 policy. It
measures scale behavior of v0.3 + same-budget controls over a larger fresh
external slice and publishes records-only aggregate output with worst-slice
visibility. **The v0.3 algorithm and weights are frozen exactly as in BEA-3;
this phase is scale measurement, not a new algorithm.**

BEA-4 is explicitly **not** a benchmark result, **not** a leaderboard entry,
**not** a performance claim, **not** a method-winner claim, **not** a
calibration claim, **not** a promotion, **not** a default/policy change,
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change, and
**not** an algorithm change. The `algorithm_changed_during_bea4` and
`weights_tuned_during_bea4` flags are both `false` (binding).

> `claim_level = bea_v03_external_scale_smoke_only`. All no-claim /
> no-runtime-change flags false.

## Frozen policy

`bea_v0_3_anchor_span_latency` is identical to BEA-3 (frozen weights:
anchor=0.35, span_tight=0.15, anchor_file_support=0.10,
weak_support_penalty=-0.20, early_stop_margin=0.05). No algorithm/weight
change during BEA-4.

## Required arms (no ablations)

- `bm25_prefix_same_budget`
- `agreement_only_same_budget`
- `rrf_same_budget` (required)
- `bea_v0`
- `bea_v0_2_diversity_risk`
- `bea_v0_3_anchor_span_latency` (treatment)
- `seeded_random_same_budget`

BEA-3's ablations (`bea_v0_3_no_anchor`, `bea_v0_3_no_early_stop`) are
**NOT** in BEA-4 fixed arms (scale measurement, not ablation).

## Fresh primary slice

- ContextBench verified Python rows: offset 80, limit 80 (hard cap 80).
- RepoQA Python needles: offset 40, limit 40 (hard cap 40).
- Local smoke may use smaller bounds for speed; manual CI uses the full
  scale slice (or fallback ContextBench 50 + RepoQA 25 if runtime
  concerns, never another tiny 20 + 10 calling itself scale).

## Public artifact shape

Records-only (no dynamic arm dicts):

- `benchmark_arm_metric_records`: `{benchmark, arm, metric, value, record_count}`
- `delta_records`: `{baseline_arm, treatment_arm, metric, delta}` (v0.3 vs
  bm25, agreement, rrf, v0.2, v0, random; v0 as fixed baseline arm)
- `win_tie_loss_records`: `{baseline_arm, treatment_arm, metric, win, tie,
  loss, record_count}` (paired denominator; v0.3 vs each control)
- `worst_slice_records`: `{benchmark, arm, query_length_bucket,
  candidate_pool_size_bucket, budget_exhaustion_bucket, file_kind_mix_bucket,
  method_agreement_bucket, rank_gap_bucket, record_count, file_recall@10,
  mrr, span_f0.5@10, success_rate, evidence_budget_used, latency_seconds,
  quality_per_candidate, quality_per_latency}` (worst N=5 per
  benchmark × arm, sorted ascending by span_f0.5@10)
- `mechanism_summary_records`: `{mechanism_field, value, record_count}`
- aggregate-only `private_score_manifest`: `{records_written, record_count,
  schema_version, manifest_hash, storage_class, path_publicly_serialized=false}`

## Worst-slice bucket labels (fixed public aggregate)

Only these 7 fixed public aggregate bucket labels; NO row IDs, repos, paths,
commits, queries, labels, candidate lists, or gold/source snippets:

- `benchmark`: contextbench | repoqa
- `query_length_bucket`: short | medium | long | empty
- `candidate_pool_size_bucket`: small | medium | large | empty
- `budget_exhaustion_bucket`: full | partial | empty
- `file_kind_mix_bucket`: pure_python | mixed | non_python | empty
- `method_agreement_bucket`: high | medium | low | empty
- `rank_gap_bucket`: narrow | medium | wide | empty

## Validation

```text
python3 -m py_compile eval/bea4_external_scale_smoke.py  => PASS
python3 eval/bea4_external_scale_smoke.py --self-test  => PASS (237/237 checks)
python3 eval/bea4_external_scale_smoke.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 80 --contextbench-row-limit 3 \
  --repoqa-needle-offset 40 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol --enable-rrf-baseline \
  --out artifacts/bea4_external_scale_smoke/bea4_external_scale_smoke_report.json  => PASS
  (status: bea4_external_scale_smoke_pass, 5 records successful,
   private_score_manifest.record_count=35 (5×7 arms),
   private_score_storage_class=tmp_private,
   private_score_path_publicly_serialized=false,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea4=false, weights_tuned_during_bea4=false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Real bounded local smoke result (2026-06-21)

Bounded local smoke (ContextBench offset 80 limit 3 + RepoQA offset 40
limit 2, budget=5, methods bm25/regex/symbol, rrf baseline required and enabled):
5 records successful, `paired_exclusion_count=0`, forbidden scan pass,
`provider_calls=0`, `private_score_manifest.record_count=35` (5×7 arms),
`private_score_storage_class=tmp_private`,
`private_score_path_publicly_serialized=false`.

Win/tie/loss (v0.3 vs v0, n=5): file_recall@10 win=1 tie=4 loss=0; mrr
win=2 tie=3 loss=0; span_f0.5@10 win=1 tie=3 loss=1; success_rate win=1
tie=4 loss=0.

Delta records (v0.3 vs controls): vs `bea_v0_2_diversity_risk` all deltas
0.0 (v0.3 ties v0.2 on all primary metrics on this bounded sample); vs
`bea_v0`/`agreement_only`/`bm25_prefix`/`rrf_same_budget` file_recall@10
+0.2 / mrr +0.2 / success_rate +0.2 / span_f0.5@10 -0.020628; vs
`seeded_random` file_recall@10 +0.4 / mrr +0.266667 / span_f0.5@10
+0.038277 / success_rate +0.4.

Mechanism summary: anchor_used_rate=1.0, early_stop_rate=0.0,
mean_budget_used=5.0, mean_latency_seconds=6.3926, mean_span_extent=5.0,
span_proxy_bucket_tight=25.

Worst-slice records: 27 slices emitted across (benchmark × arm)
combinations with `record_count >= 1` each, sorted ascending by
span_f0.5@10. All bucket labels are fixed public aggregate labels; no
row IDs, repos, paths, commits, queries, labels, candidate lists, or
gold/source snippets.

This is an honest smoke-level scale result, not a method-winner, calibration,
default, promotion, runtime/retriever/EvidenceCore, or downstream-agent-value
claim. The full scale slice (ContextBench 80 + RepoQA 40) is pending manual
CI run.

## Caveats

- BEA-4 is eval/diagnostic only. NOT benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value claim.
- The v0.3 algorithm and weights are frozen exactly as in BEA-3.
  `algorithm_changed_during_bea4=false`,
  `weights_tuned_during_bea4=false` (binding).
- Bounded local smoke used 3+2 records for speed. The full scale slice
  (ContextBench 80 + RepoQA 40) is pending manual CI run; this committed
  artifact reflects the local smoke only.
- Network-enabled CI is scale-only: it fails unless at least 75 records succeed
  and both ContextBench and RepoQA contribute nonzero records. Smaller 3+2 runs
  are local validation only, not CI result evidence.
- All no-claim / no-runtime-change flags false; EvidenceCore semantics
  unchanged. BEA-0/BEA-1/BEA-2/BEA-3 semantics not mutated.
