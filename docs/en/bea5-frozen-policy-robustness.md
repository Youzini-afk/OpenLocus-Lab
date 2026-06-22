# BEA-5 Frozen-Policy Larger/Cross-Slice Robustness Smoke

Date: 2026-06-21 (BEA-5 frozen-policy larger/cross-slice robustness smoke for
the frozen BEA v0.3 policy, over a fresh disjoint larger external slice —
ContextBench verified Python rows offset 160 + RepoQA Python needles offset
80 — with private per-record SCORE JSONL in `/tmp` and records-shaped
aggregate-only public artifact including robustness summary)

BEA-5 is the **frozen-policy robustness smoke** for the frozen BEA v0.3
policy. It runs a fresh, disjoint larger/cross-slice external robustness
smoke (ContextBench verified Python rows offset 160 limit 240, RepoQA Python
needles offset 80 limit 120) and tests whether BEA-4's conclusions are stable
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

## Fresh disjoint larger slice (success-quota sampling)

BEA-5 uses **success-quota sampling** over a larger disjoint raw scan. The
same offsets as BEA-4 are kept, but raw attempt caps are larger to allow
stopping once the target number of successful records is reached:

- ContextBench verified Python rows: offset 160, raw attempt cap 480 (hard
  cap 480).
- RepoQA Python needles: offset 80, raw attempt cap 240 (hard cap 240).
- `target_successful_records = 120`. Evaluation stops once 120 successful
  records are collected across both benchmarks.
- `sampling_mode = "success_quota"`.
- Requires nonzero ContextBench + RepoQA contribution; CI gates require
  `contextbench_successful >= 40` and `repoqa_successful >= 20`.
- `quota_reached` boolean records whether the target was met.
- Local smoke may use smaller raw attempt caps for speed (e.g. 3+2); local
  debug artifacts will truthfully show `status=partial` and
  `quota_reached=false` until the target is reached in manual CI.

This success-quota sampling is a bounded fix after CI failures on raw
disjoint slices that produced only 72 successful records. It is NOT a silent
cap bump and NOT a No-Go; it explicitly samples more raw attempts to reach
the declared target of 120 successful records.

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
- `benchmark_attempt_records`: natural key `(benchmark,)` — per-benchmark
  attempted/successful/excluded counts
- aggregate-only `private_score_manifest`: `{records_written, record_count,
  schema_version, manifest_hash, storage_class, path_publicly_serialized=false}`
- aggregate-only `private_attempt_manifest`: `{records_written, record_count,
  schema_version, manifest_hash, storage_class, path_publicly_serialized=false}`

No dict mirrors such as `arm_metrics`, `deltas`, `aggregate_metrics`, or
dynamic method maps.

## Success-quota public fields

- `sampling_mode = "success_quota"`
- `target_successful_records = 120`
- `raw_attempt_cap_contextbench = 480`
- `raw_attempt_cap_repoqa = 240`
- `records_attempted_total`: total attempted across both benchmarks
- `records_excluded`: total excluded (= `records_failed`)
- `quota_reached` boolean
- `contextbench_attempted/successful/excluded`
- `repoqa_attempted/successful/excluded`
- `benchmark_attempt_records`: records list with per-benchmark counts

## Private traces

- Successful records: private SCORE JSONL rows
  (`records_successful × 7 arms`) under `/tmp` only.
- Failed/excluded attempts: separate private attempt JSONL under `/tmp` only
  (`records_attempted_total` rows), one row per attempted record with
  `phase_run_id`, `benchmark`, `private_attempt_id`, `outcome_category`,
  `attempt_reason`. No raw query/path/repo/gold in public.
- Public manifests record only counts/hash/storage_class/path=false.

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
python3 eval/bea5_frozen_policy_robustness.py --self-test  => PASS (385/385 checks)
python3 eval/bea5_frozen_policy_robustness.py \
  --enable-external-benchmark-network \
  --contextbench-row-offset 160 --contextbench-row-limit 3 \
  --repoqa-needle-offset 80 --repoqa-needle-limit 2 \
  --budget 5 --methods bm25,regex,symbol \
  --out artifacts/bea5_frozen_policy_robustness/bea5_frozen_policy_robustness_report.json  => PASS
  (status: partial, 3 records successful,
   sampling_mode=success_quota, target_successful_records=120,
   quota_reached=false, records_attempted_total=5, records_excluded=2,
   contextbench_attempted=3, contextbench_successful=2, contextbench_excluded=1,
   repoqa_attempted=2, repoqa_successful=1, repoqa_excluded=1,
   private_score_manifest.record_count=21 (3×7 arms),
   private_attempt_manifest.record_count=5 (= records_attempted_total),
   private_score_storage_class=tmp_private,
   private_score_path_publicly_serialized=false,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea5=false, weights_tuned_during_bea5=false,
   self_test_checks_total=385, self_test_checks_passed=385)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Real bounded local smoke result (2026-06-21, success-quota fix)

Bounded local smoke (ContextBench offset 160 limit 3 + RepoQA offset 80
limit 2, budget=5, methods bm25/regex/symbol): this is a small local
debug smoke with `status=partial` because only 3 of 120 target successful
records were collected. `quota_reached=false`. `records_attempted_total=5`
(3 ContextBench + 2 RepoQA), `records_successful=3`, `records_excluded=2`.
`contextbench_successful=2`, `repoqa_successful=1`.

`private_score_manifest.record_count=21` (3×7 arms),
`private_attempt_manifest.record_count=5` (= records_attempted_total),
`private_score_storage_class=tmp_private`,
`private_score_path_publicly_serialized=false`,
`algorithm_changed_during_bea5=false`, `weights_tuned_during_bea5=false`.

`benchmark_attempt_records`:
`contextbench: attempted=3, successful=2, excluded=1`;
`repoqa: attempted=2, successful=1, excluded=1`.

This local artifact truthfully shows the success-quota sampling fields and
is NOT a CI-scale result. The full success-quota CI run (raw attempt caps
480+240, target 120 successful) is pending manual CI; CI will fail-closed
unless `records_successful >= 120`, `quota_reached=true`,
`contextbench_successful >= 40`, `repoqa_successful >= 20`,
`private_attempt_manifest.record_count == records_attempted_total`, and
`private_score_manifest.record_count == records_successful × 7`.

## Caveats

- BEA-5 is eval/diagnostic only. NOT benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value claim.
- The v0.3 algorithm and weights are frozen exactly as in BEA-3/BEA-4.
  `algorithm_changed_during_bea5=false`,
  `weights_tuned_during_bea5=false` (binding).
- Bounded local smoke used 3+2 records for speed and truthfully shows
  `status=partial`, `quota_reached=false`. The full success-quota CI run
  (raw attempt caps 480+240, target 120 successful) is pending manual CI;
  the committed artifact reflects the local smoke only. Local debug may use
  small caps but must not be recorded as CI scale evidence.
- Success-quota sampling is an explicit bounded fix after CI failures on raw
  disjoint slices that produced only 72 successful records. It is NOT a
  silent cap bump and NOT a No-Go.
- RRF arm is required; CI fails if RRF is disabled/missing.
- All no-claim / no-runtime-change flags false; EvidenceCore semantics
  unchanged. BEA-0/BEA-1/BEA-2/BEA-3/BEA-4 semantics not mutated.
