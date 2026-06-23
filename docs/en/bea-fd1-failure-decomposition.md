# BEA-FD1: BEA-4/5 Frozen Replay Failure Decomposition

Date: 2026-06-22 (BEA-FD1 failure decomposition — replays frozen BEA-4 and
BEA-5 protocols exactly via subprocess, parses private SCORE JSONL files,
classifies v0.3 treatment outcomes into a fixed 12-category enum, publishes
records-only aggregate decomposition tables)

BEA-FD1 replays both final protocols exactly: BEA-4 (CI `27957586271`,
expected 120/840) and BEA-5 (CI `28003522632`, expected 119/833). It does
NOT change BEA v0.3, sampling, gates, arms, or weights. It does NOT implement
v0.4.

> `claim_level = bea_fd1_failure_decomposition_smoke_only`. All no-claim /
> no-runtime-change flags false.

## Replay protocol

Network-enabled BEA-FD1 runs `eval/bea4_external_scale_smoke.py` and
`eval/bea5_frozen_policy_robustness.py` via subprocess with exact protocol
inputs and `--private-score-dir` under a BEA-FD1 temp private dir. It parses
the resulting `bea4.private.jsonl` and `bea5.private.jsonl` files and temp
public artifacts to compute aggregate decomposition.

- BEA-4: ContextBench offset 80 limit 80, RepoQA offset 40 limit 40, budget 5,
  methods bm25,regex,symbol, RRF required. Expected 120 successful / 840
  private SCORE rows.
- BEA-5: ContextBench offset 0 limit 480, RepoQA offset 0 limit 240, budget 5,
  methods bm25,regex,symbol. Expected 119 successful / 833 private SCORE rows.

If replay counts mismatch expected, status is partial/unavailable, not pass.

## Required comparisons

v0.3 treatment vs: v0.2, v0, bm25_prefix_same_budget, agreement_only_same_budget,
rrf_same_budget.

## Fixed category enum (12)

`gold_file_absent`, `gold_span_absent`, `correct_file_wrong_span`,
`redundant_same_file_candidates`, `too_many_anchor_slots`,
`missing_support_candidate`, `support_selected_without_target`,
`target_selected_without_support`, `risk_penalty_removed_gold`,
`early_stop_too_early`, `budget_spent_on_low_marginal_gain`,
`latency_without_quality_gain`.

## Available vs unavailable categories

- **Available**: `gold_file_absent` (file_recall==0), `correct_file_wrong_span`
  (file hit, span==0), `too_many_anchor_slots` (anchor_slots>2),
  `early_stop_too_early` (early_stop triggered, quality<=baseline),
  `budget_spent_on_low_marginal_gain` (full budget, quality<=baseline),
  `latency_without_quality_gain` (latency>baseline, quality delta<=0).
- **unavailable_missing_trace**: `redundant_same_file_candidates`,
  `risk_penalty_removed_gold`.
- **unavailable_no_support_label**: `missing_support_candidate`,
  `support_selected_without_target`, `target_selected_without_support`.

## Public artifact tables (records-only, natural keys)

- `source_run_records`: `(source_phase, source_ci_run_id)`
- `category_summary_records`: `(source_phase, benchmark, category, category_availability)`
- `category_metric_loss_records`: `(source_phase, benchmark, category, baseline_arm, treatment_arm, metric)`
- `category_win_tie_loss_records`: `(source_phase, benchmark, category, baseline_arm, treatment_arm, metric)`
- `bucket_category_records`: `(source_phase, benchmark, bucket_type, bucket_value, category)`
- `candidate_source_category_records`: `(source_phase, benchmark, candidate_source_bucket, category)`
- `availability_records`: `(source_phase, benchmark, category, category_availability)`
- `private_decomposition_manifest`: aggregate-only (count/hash/storage/path=false)

## Metric loss

- Quality metrics: `loss = max(0, baseline_metric - treatment_metric)`.
- Latency: `loss = max(0, treatment_latency - baseline_latency)`.
- Records include `loss_sum`, `loss_mean`, `delta_mean`, `record_count`.

## Validation

```text
python3 -m py_compile eval/bea_fd1_failure_decomposition.py  => PASS
python3 eval/bea_fd1_failure_decomposition.py --self-test  => PASS (170/170 checks)
python3 eval/bea_fd1_failure_decomposition.py \
  --out artifacts/bea_fd1_failure_decomposition/bea_fd1_failure_decomposition_report.json  => PASS
  (status: unavailable_with_reason, no-network artifact,
   provider_calls=0, forbidden_scan=pass,
   algorithm_changed_during_bea_fd1=false, weights_tuned_during_bea_fd1=false,
   self_test_checks_total=170, self_test_checks_passed=170)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Caveats

- BEA-FD1 is eval/diagnostic only. NOT benchmark/leaderboard/performance/
  method-winner/calibration/promotion/default/runtime/EvidenceCore/
  downstream-value claim.
- v0.3 algorithm/weights frozen; `algorithm_changed_during_bea_fd1=false`.
- Fixed protocol: no budget/methods CLI inputs; exact BEA-4/5 defaults.
- Full BEA-4/BEA-5 replay CI pending; committed artifact reflects no-network
  unavailable state only.
- `redundant_same_file_candidates` and `risk_penalty_removed_gold` marked
  `unavailable_missing_trace` in first implementation.
- `missing_support_candidate`, `support_selected_without_target`,
  `target_selected_without_support` marked `unavailable_no_support_label`
  (no support/target labels invented).
