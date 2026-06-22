# BEA-5 Frozen-Policy Larger/Cross-Slice Robustness Smoke

Date: 2026-06-21 (BEA-5 frozen-policy larger/cross-slice robustness smoke for
the frozen BEA v0.3 policy, over a fresh disjoint larger external slice —
ContextBench verified Python rows offset 160 + RepoQA Python needles offset
80 — with private per-record SCORE JSONL in `/tmp` and records-shaped
aggregate-only public artifact including robustness summary)

BEA-5 is the **frozen-policy robustness smoke** for the frozen BEA v0.3
policy. It runs a fresh, disjoint larger/cross-slice external robustness
smoke (ContextBench verified Python rows offset 160 limit 120, RepoQA Python
needles offset 80 limit 60) and tests whether BEA-4's conclusions are stable
before any BEA v0.4 tuning. **The v0.3 algorithm and weights are frozen
exactly as in BEA-3/BEA-4; this phase is robustness measurement, not a new
algorithm.**

BEA-5 is explicitly **not** a benchmark result, **not** a leaderboard entry,
**not** a performance claim, **not** a method-winner claim, **not** a
calibration claim, **not** a promotion, **not** a default/policy change,
**not** a runtime/retriever/pack/backend/EvidenceCore semantic change, and
**not** an algorithm change. The `algorithm_changed_during_bea5` and
`weights_tuned_during_bea5` flags are both `false` (binding).

> `claim_level = bea_v03_frozen_policy_robustness_smoke_only`. All no-claim /
> no-runtime-change flags false.

## Frozen policy

`bea_v0_3_anchor_span_latency` is identical to BEA-3/BEA-4 (frozen weights:
anchor=0.35, span_tight=0.15, anchor_file_support=0.10,
weak_support_penalty=-0.20, early_stop_margin=0.05). No algorithm/weight
change during BEA-5.

## Required arms (7; RRF required never optional)

- `bea_v0_3_anchor_span_latency` (treatment)
- `bea_v0_2_diversity_risk`
- `bea_v0`
- `bm25_prefix_same_budget`
- `agreement_only_same_budget`
- `rrf_same_budget` (REQUIRED; CI fails if RRF disabled/missing)
- `seeded_random_same_budget`

BEA-3's ablations (`bea_v0_3_no_anchor`, `bea_v0_3_no_early_stop`) are **NOT**
in BEA-5 fixed arms. BEA-5 has NO `--enable-rrf-baseline` CLI flag; RRF is
always required.

## Fresh disjoint larger slice

- ContextBench verified Python rows: offset 160, limit 120 (hard cap 120).
- RepoQA Python needles: offset 80, limit 60 (hard cap 60).
- Local smoke may use smaller bounds for speed (e.g. 2+2); CI requires
  >=120 records_successful and nonzero ContextBench + RepoQA contribution.

## Public artifact shape

Records-only (no dynamic arm dicts). All record tables must be unique by
their natural key:

- `benchmark_arm_metric_records`: natural key `(benchmark, arm, metric)`
- `delta_records`: natural key `(baseline_arm, treatment_arm, metric)`
- `win_tie_loss_records`: natural key `(baseline_arm, treatment_arm, metric)`
- `worst_slice_records`: natural key `(benchmark, arm, query_length_bucket,
  candidate_pool_size_bucket, budget_exhaustion_bucket, file_kind_mix_bucket,
  method_agreement_bucket, rank_gap_bucket)`
- `mechanism_summary_records`: natural key `(mechanism_field,)`
- `robustness_summary_records`: natural key `(robustness_field,)`
- aggregate-only `private_score_manifest`: `{records_written, record_count,
  schema_version, manifest_hash, storage_class, path_publicly_serialized=false}`

No dict mirrors such as `arm_metrics`, `deltas`, `aggregate_metrics`, or
dynamic method maps.

## Robustness summary fields

Each record: `{robustness_field, value, record_count}`.

- `cross_slice_v03_vs_v02_mrr_delta`: mean mrr delta v0.3-v0.2 across paired records
- `cross_slice_v03_vs_v0_mrr_delta`
- `cross_slice_v03_vs_v02_file_recall_delta`
- `cross_slice_v03_vs_v0_file_recall_delta`
- `v03_vs_v02_sign_stability_mrr`: fraction of paired records where v0.3 >= v0.2 on mrr
- `v03_vs_v0_sign_stability_mrr`
- `v03_vs_v02_sign_stability_file_recall`
- `v03_vs_v0_sign_stability_file_recall`
- `v03_quality_per_latency_mean`
- `rrf_quality_per_latency_mean`
- `v03_vs_rrf_quality_per_latency_delta`
- `worst_slice_cluster_<bucket_field>_<bucket_value>`: count of worst slices per bucket value (for each of the 6 non-benchmark bucket fields)

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

## Counts-only self-test summary

The public artifact records ONLY counts, not the self-test detail list:

- `self_test_passed`: bool
- `self_test_checks_total`: int (expected 285)
- `self_test_checks_passed`: int

Forbidden public fields: `self_test_checks`, `self_test_details`,
`self_test_list`, `checks`, `check_list`.

## Validation

```text
python3 -m py_compile eval/bea5_frozen_policy_robustness.py  => PASS
python3 eval/bea5_frozen_policy_robustness.py --self-test  => PASS (285/285 checks)
python3 eval/bea5_frozen_policy_robustness.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 160 --contextbench-row-limit 2 \
  --repoqa-needle-offset 81 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol \
  --out artifacts/bea5_frozen_policy_robustness/bea5_frozen_policy_robustness_report.json  => PASS
  (status: bea5_frozen_policy_robustness_pass, 4 records successful,
   private_score_manifest.record_count=28 (4×7 arms),
   private_score_storage_class=tmp_private,
   private_score_path_publicly_serialized=false,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea5=false, weights_tuned_during_bea5=false,
   self_test_checks_total=285, self_test_checks_passed=285)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Real bounded local smoke result (2026-06-21)

Bounded local smoke (ContextBench offset 160 limit 2 + RepoQA offset 81
limit 2, budget=5, methods bm25/regex/symbol): 4 records successful,
`paired_exclusion_count=0`, forbidden scan pass, `provider_calls=0`,
`private_score_manifest.record_count=28` (4×7 arms),
`private_score_storage_class=tmp_private`,
`private_score_path_publicly_serialized=false`,
`algorithm_changed_during_bea5=false`, `weights_tuned_during_bea5=false`.

Win/tie/loss (v0.3 vs v0, n=4): file_recall@10 win=2 tie=2 loss=0; mrr
win=2 tie=1 loss=1; span_f0.5@10 win=2 tie=2 loss=0; success_rate win=2
tie=2 loss=0.

Delta records (v0.3 vs controls, mrr): vs `bea_v0_2_diversity_risk` delta=0.0
(v0.3 ties v0.2 on mrr); vs `bea_v0`/`agreement_only`/`bm25_prefix`/
`rrf_same_budget` mrr delta=+0.070833; vs `seeded_random` mrr delta=+0.1125.

Robustness summary (selected): `cross_slice_v03_vs_v02_mrr_delta=0.0`,
`cross_slice_v03_vs_v0_mrr_delta=0.070833`,
`cross_slice_v03_vs_v0_file_recall_delta=0.5`,
`v03_vs_v02_sign_stability_mrr=1.0`,
`v03_vs_v0_sign_stability_mrr=0.75`,
`v03_quality_per_latency_mean=0.058183`,
`rrf_quality_per_latency_mean=0.011407`,
`v03_vs_rrf_quality_per_latency_delta=0.046776`.

Public record tables: 140 `benchmark_arm_metric_records`, 60 `delta_records`,
24 `win_tie_loss_records`, 22 `worst_slice_records`, 6
`mechanism_summary_records`, 20 `robustness_summary_records`. All record
tables verified unique by natural key.

This is an honest smoke-level robustness result, not a method-winner,
calibration, default, promotion, runtime/retriever/EvidenceCore, or
downstream-agent-value claim. The full scale slice (ContextBench 120 +
RepoQA 60) is pending manual CI run; the committed artifact reflects the
local smoke only.

## Caveats

- BEA-5 is eval/diagnostic only. NOT benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value claim.
- The v0.3 algorithm and weights are frozen exactly as in BEA-3/BEA-4.
  `algorithm_changed_during_bea5=false`,
  `weights_tuned_during_bea5=false` (binding).
- Bounded local smoke used 2+2 records for speed. The full robustness slice
  (ContextBench 120 + RepoQA 60) is pending manual CI run; the committed
  artifact reflects the local smoke only. Local debug may use 2+2 only and
  must not be recorded as CI scale evidence.
- RRF arm is required; CI fails if RRF is disabled/missing.
- All no-claim / no-runtime-change flags false; EvidenceCore semantics
  unchanged. BEA-0/BEA-1/BEA-2/BEA-3/BEA-4 semantics not mutated.
