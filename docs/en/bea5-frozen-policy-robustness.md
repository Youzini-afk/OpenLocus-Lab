# BEA-5 Frozen-Policy Larger/Cross-Slice Robustness Smoke

Date: 2026-06-21 (BEA-5 frozen-policy larger/cross-slice robustness smoke for
the frozen BEA v0.3 policy, over a fresh disjoint larger external slice with
**recovery success-quota sampling** — full available Python benchmark frame
excluding BEA-2/3/4 prior windows — with private per-record SCORE JSONL in
`/tmp` and records-shaped aggregate-only public artifact including robustness
summary)

BEA-5 is the **frozen-policy robustness smoke** for the frozen BEA v0.3
policy. It runs a fresh, disjoint larger/cross-slice external robustness
smoke and tests whether BEA-4's conclusions are stable before any BEA v0.4
tuning. **The v0.3 algorithm and weights are frozen exactly as in
BEA-3/BEA-4; this phase is robustness measurement, not a new algorithm.**

Fixed-tail CI run `27984961904` failed quota due to dataset yield: 72
successful / 126 attempted; ContextBench 53 success; RepoQA 19 success; all
failures `retrieval_failed`; `rrf_required_but_missing=0`; no privacy/schema/
RRF failure. This is **not** a BEA v0.3 algorithm failure and **not** a
BEA-5 result claim. The recovery sampling revision scans the full available
Python frame excluding BEA-2/3/4 windows so RepoQA can reach its 20-record
minimum.

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

## Fresh disjoint larger slice (recovery success-quota sampling)

BEA-5 uses **recovery success-quota sampling** over the full available
Python benchmark frame, excluding mandatory BEA-2/3/4 prior windows. This
replaces the fixed-tail sampling that exhausted available Python rows in CI
run `27984961904`.

- `sampling_mode = "success_quota"`
- `sampling_protocol_version = "bea5_success_quota_disjoint_scan.v1"`
- `sampling_frame_policy =
  "full_available_python_excluding_bea2_bea3_bea4_windows"`
- `excluded_prior_windows_policy =
  "mandatory_bea2_bea3_bea4; bea0_bea1_best_effort_or_disclosed"`
- `bea0_bea1_windows_excluded = false`
- `bea0_bea1_overlap_policy =
  "not_excluded; disclosed; BEA-0 and BEA-1 were small early smoke slices,
  not frozen-v0.3 BEA-2 to BEA-4 windows"`
- ContextBench: scan full available Python frame (offset 0, raw attempt cap
  480), excluding mandatory windows `[40,160)` (BEA-2 `[40,60)`, BEA-3
  `[60,80)`, BEA-4 `[80,160)`).
- RepoQA: scan full available Python frame (offset 0, raw attempt cap 240),
  excluding mandatory windows `[20,80)` (BEA-2 `[20,30)`, BEA-3 `[30,40)`,
  BEA-4 `[40,80)`).
- Python-only filtering remains.
- Stable deterministic order (original index order within each benchmark).
- **Deterministic interleaving**: process ContextBench and RepoQA in
  round-robin fashion so RepoQA can reach its 20-record minimum even if
  ContextBench yields its 40-record quota first.
- Stop only after `total successful >= 120 AND contextbench_successful >=
  40 AND repoqa_successful >= 20`.
- `quota_reached` boolean records whether the target was met.
- Raw caps 480/240 as max attempts per benchmark.
- BEA-5 recovery is a fixed protocol: CLI/workflow inputs must be exactly
  offset 0, caps 480/240, budget 5, and methods `bm25,regex,symbol`.
  Smaller debug caps are intentionally rejected so public requested fields
  cannot drift from the actual sampling frame.

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
- `sampling_protocol_version = "bea5_success_quota_disjoint_scan.v1"`
- `sampling_frame_policy =
  "full_available_python_excluding_bea2_bea3_bea4_windows"`
- `excluded_prior_windows_policy =
  "mandatory_bea2_bea3_bea4; bea0_bea1_best_effort_or_disclosed"`
- `bea0_bea1_windows_excluded = false`
- `bea0_bea1_overlap_policy`: aggregate disclosure string for BEA-0/1 not
  being mandatory exclusions
- `target_successful_records = 120`
- `raw_attempt_cap_contextbench = 480`
- `raw_attempt_cap_repoqa = 240`
- `records_attempted_total`: total attempted across both benchmarks
- `records_excluded`: total excluded (= `records_failed`)
- `quota_reached` boolean
- `contextbench_attempted/successful/excluded`
- `repoqa_attempted/successful/excluded`
- `contextbench_excluded_prior_window_count`: count of rows excluded by
  mandatory BEA-2/3/4 windows
- `repoqa_excluded_prior_window_count`: count of needles excluded by
  mandatory BEA-2/3/4 windows
- `contextbench_eligible_count`: count of rows after exclusion filtering
- `repoqa_eligible_count`: count of needles after exclusion filtering
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
python3 eval/bea5_frozen_policy_robustness.py --self-test  => PASS (435/435 checks)
python3 eval/bea5_frozen_policy_robustness.py \
  --out artifacts/bea5_frozen_policy_robustness/bea5_frozen_policy_robustness_report.json  => PASS
  (status: unavailable_with_reason, no-network artifact,
   sampling_mode=success_quota,
   sampling_protocol_version=bea5_success_quota_disjoint_scan.v1,
   sampling_frame_policy=full_available_python_excluding_bea2_bea3_bea4_windows,
   quota_reached=false, records_attempted_total=0,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea5=false, weights_tuned_during_bea5=false,
   self_test_checks_total=435, self_test_checks_passed=435)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Prior CI run and recovery sampling

Fixed-tail CI run `27984961904` failed quota due to dataset yield:
`records_successful=72`, `records_attempted_total=126`,
`contextbench_successful=53`, `repoqa_successful=19`, `retrieval_failed=54`,
`rrf_required_but_missing=0`. All failures were `retrieval_failed` (repo
clone/materialization failures on the tail slice); no privacy/schema/RRF
failure. This is **not** a BEA v0.3 algorithm failure and **not** a BEA-5
result claim.

The recovery sampling revision scans the full available Python frame
excluding BEA-2/3/4 prior windows, with deterministic interleaving so RepoQA
can reach its 20-record minimum. The full success-quota CI run (raw attempt
caps 480+240, target 120 successful, min 40/20 per benchmark) is pending
manual CI.

## Caveats

- BEA-5 is eval/diagnostic only. NOT benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value claim.
- The v0.3 algorithm and weights are frozen exactly as in BEA-3/BEA-4.
  `algorithm_changed_during_bea5=false`,
  `weights_tuned_during_bea5=false` (binding).
- Fixed-tail CI run `27984961904` failed quota due to dataset yield (72
  successful / 126 attempted), not an algorithm or schema failure. The
  recovery sampling revision scans the full available Python frame excluding
  BEA-2/3/4 windows with deterministic interleaving.
- The full success-quota CI run (raw attempt caps 480+240, target 120
  successful, min 40/20 per benchmark) is pending manual CI; the committed
  artifact reflects the no-network unavailable state only.
- RRF arm is required; CI fails if RRF is disabled/missing.
- All no-claim / no-runtime-change flags false; EvidenceCore semantics
  unchanged. BEA-0/BEA-1/BEA-2/BEA-3/BEA-4 semantics not mutated.
