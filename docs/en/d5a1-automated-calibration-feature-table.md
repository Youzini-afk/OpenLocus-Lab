# D5-A1 Automated Calibration Feature Table (Public Aggregate-Only Artifact)

## Scope and claim boundary

D5-A1 moves from empirical smokes to **calibration-ready weak-supervision
features** by machine-reading committed aggregate artifacts and
computing deterministic feature records. D5-A1 is **empirical feature
extraction over real prior runs**, not a research-log summary and not
calibration.

D5-A1 is explicitly **not** calibration, **not** a calibrated model
claim, **not** a policy/default recommendation, **not** a method
winner claim, **not** an external benchmark performance claim, **not**
a downstream agent value claim, **not** a leaderboard entry, and
**not** a runtime/retriever/pack/backend/default-policy/EvidenceCore
semantic change. It makes NO provider calls and NO remote provider
calls. The bootstrap statistics and feature records are weak-supervision
features for future calibration / manual review, NOT calibrated labels
or policy recommendations.

- Claim level: `automated_calibration_feature_extraction_only`.
- Mode: `committed_aggregate_feature_extraction`;
  phase `D5-A1`.
- Status enum: `automated_calibration_feature_table_pass` on success;
  `fail_input_contract` if a required input artifact is missing,
  has a schema/status mismatch, or has unsafe claim flags;
  `fail_forbidden_scan` on scanner failure.
- D5-A1 is **eval/diagnostic only**. It is NOT calibration, NOT a
  calibrated model claim, NOT a policy/default recommendation, NOT a
  benchmark result, NOT downstream utility, NOT true E/S calibration,
  NOT an external benchmark performance claim, NOT a leaderboard entry,
  NOT a method winner, and NOT a promotion.

## Input artifacts

D5-A1 machine-reads committed aggregate artifacts (not research logs
or freeform docs):

### Required inputs

1. **F1-D** — `artifacts/f1d_cross_benchmark_retrieval_robustness/f1d_cross_benchmark_retrieval_robustness_report.json`
   (schema `f1d_cross_benchmark_retrieval_robustness.v1`, status
   `cross_benchmark_retrieval_robustness_pass`). Source of retrieval
   robustness bootstrap signals (bm25_vs_empty, regex_vs_bm25,
   symbol_vs_bm25 retrieval_utility point/CI/sign stability).
2. **F1-C** — `artifacts/f1c_cross_benchmark_retrieval_utility/f1c_cross_benchmark_retrieval_utility_report.json`
   (schema `f1c_cross_benchmark_retrieval_utility.v1`, status
   `cross_benchmark_retrieval_utility_pass`). Cross-benchmark utility
   anchor.
3. **C5-C** — `artifacts/c5c_contextbench_verified_method_matrix_scale/c5c_contextbench_verified_method_matrix_scale_report.json`
   (schema `c5c_contextbench_verified_method_matrix_scale_smoke.v1`,
   status `contextbench_method_matrix_scale_smoke_pass`). Source of
   ContextBench method agreement/disagreement counts.
4. **C5-F** — `artifacts/c5f_repoqa_method_matrix_scale/c5f_repoqa_method_matrix_scale_report.json`
   (schema `c5f_repoqa_method_matrix_scale_smoke.v1`, status
   `repoqa_method_matrix_scale_smoke_pass`). Source of RepoQA method
   agreement/disagreement counts.
5. **B16-E** — `artifacts/b16e_broader_live_provider_paired_smoke/b16e_broader_live_provider_paired_smoke_report.json`
   (schema `b16e_broader_live_provider_paired_smoke.v1`, status
   `broader_live_provider_paired_smoke_pass`). Source of live provider
   delta signals (context_pack_signal_observed, solve_rate delta,
   families positive/zero/negative).

### Optional inputs (included only if present and claim-safe)

6. **D5-A0** — `artifacts/d5a_automated_es_calibration/d5a_automated_es_calibration_report.json`
   (schema `d5a_automated_es_calibration.v1`, status
   `automated_es_calibration_smoke_pass`). Automated E/S calibration
   smoke anchor.
7. **B16-D** — `artifacts/b16d_less_trivial_live_provider_paired_smoke/b16d_less_trivial_live_provider_paired_smoke_report.json`
   (schema `b16d_less_trivial_live_provider_paired_smoke.v1`, status
   `live_provider_less_trivial_paired_smoke_pass`). Secondary live
   signal.

Optional inputs that are missing, invalid, schema-mismatched,
status-mismatched, or claim-unsafe are recorded as `skipped_optional`
with an aggregate reason category only (no raw paths/content).

## Fail-closed input validation

D5-A1 validates every input artifact fail-closed:

- **Required artifact missing** => status `fail_input_contract` and
  nonzero CLI exit.
- **Schema version mismatch** (required) => `fail_input_contract`.
- **Status mismatch** (required) => `fail_input_contract`.
- **Unsafe claim flag** in any input (any of
  `true_e_s_calibration_claimed`,
  `automated_e_s_full_calibration_claimed`,
  `human_e_s_calibration_claimed`, `calibrated_model_claimed`,
  `policy_recommendation_claimed`, `method_winner_claimed`,
  `external_benchmark_performance_claimed`,
  `downstream_agent_value_proven`, `promotion_ready`,
  `default_should_change`, runtime/retriever/pack/backend/default-policy/
  EvidenceCore change flags) => `fail_input_contract`.
- **Input `forbidden_scan.status`** must be `pass` if the field exists
  => otherwise `fail_input_contract`.
- **Optional artifacts** included only if present and claim-safe;
  otherwise recorded as `skipped_optional` with an aggregate reason
  category only.

## Extracted signals

D5-A1 extracts deterministic signals from input artifacts (one fixed
record per signal):

### Retrieval robustness signals (from F1-D)

- `bm25_vs_empty_retrieval_utility`: point_estimate, ci_p05, ci_p50,
  ci_p95, sign_positive/negative/zero_fraction, sample_units,
  bootstrap_replicates, bootstrap_seed.
- `regex_vs_bm25_retrieval_utility`: negative stability.
- `symbol_vs_bm25_retrieval_utility`: negative stability.

### External benchmark agreement/disagreement signals (from C5-C + C5-F)

- `bm25_positive_on_both_benchmarks`: bm25 file_recall@10 > 0 on both
  ContextBench and RepoQA. Counts only.
- `regex_symbol_negative_on_both_benchmarks`: regex and symbol
  file_recall@10 == 0 on both benchmarks. Counts only.
- `benchmark_method_agreement`: methods_agree count and
  methods_disagree count (where C5-C and C5-F agree on positive/
  negative direction).

### Live provider delta signals (from B16-E)

- `b16e_context_pack_signal`: context_pack_signal_observed,
  solve_rate_delta, families_evaluated, families_positive,
  families_zero, families_negative.

### Optional signals (from D5-A0 / B16-D if loaded)

- `d5a0_automated_calibration_smoke_anchor`: D5-A0 smoke anchor.
- `b16d_secondary_live_signal`: B16-D secondary live signal.

## Calibration features

D5-A1 computes deterministic calibration feature records (weak-
supervision features for future calibration / manual review, NOT
calibrated labels):

- `bm25_vs_empty_retrieval_utility_magnitude`: magnitude bucket
  (`strong_positive` / `weak_positive` / `zero` / `negative`).
- `bm25_vs_empty_sign_stability`: sign stability bucket
  (`stable_positive` / `majority_positive` / `minority_positive` /
  `never_positive`).
- `regex_vs_bm25_sign_stability`: negative sign stability bucket.
- `symbol_vs_bm25_sign_stability`: negative sign stability bucket.
- `live_provider_solve_rate_delta`: solve rate delta bucket
  (`strong_positive` / `weak_positive` / `zero` / `negative`).
- `live_provider_family_distribution`: family distribution bucket
  (`all_families_positive` / `mixed_families` /
  `all_families_negative` / `all_families_zero`).
- `cross_signal_alignment`: cross-signal alignment label (see below).

## Cross-signal alignment labels (fixed allowlist)

- `retrieval_robust_positive_plus_live_positive`: bm25_vs_empty
  sign_positive >= 0.95 AND B16-E context_pack_signal_observed AND
  solve_rate_delta > 0 AND families_positive > 0.
- `retrieval_negative_methods_plus_live_not_supported`: regex/symbol
  vs_bm25 sign_negative >= 0.95 AND live signal absent or not positive.
- `retrieval_only_insufficient`: retrieval signals present but no live
  signal.
- `conflicting_signals`: retrieval and live signals conflict (e.g.,
  retrieval robust positive but live negative, or retrieval negative
  but live positive).

## Readiness buckets (fixed allowlist)

- `ready_for_manual_review`: retrieval_robust_positive +
  live_positive (strongest signal).
- `needs_more_live_downstream`: retrieval positive but live signal
  absent or weak.
- `retrieval_only_insufficient`: retrieval signals only, no live.
- `conflicting_signals`: retrieval and live conflict.
- `insufficient_signal`: no signals at all.

## Recommended next measurements (measurement-only, NOT policy/default)

- `manual_reference_audit`: manual reference audit is the next
  weak-supervision step toward calibration readiness.
- `heldout_benchmark_scale`: scale retrieval benchmarks on heldout
  subsets to confirm bootstrap stability generalizes.
- `live_downstream_scale`: scale live downstream paired smoke.

Recommendations are **measurement-only**. They are NOT policy/default/
method winner recommendations. D5-A1 never recommends a default,
policy, method winner, or promotion.

## Public artifact shape

Records-shaped lists only (no dynamic dict mirrors):

- `input_artifact_records`: list of fixed records
  `{phase, schema_version, status, required, claim_safe, loaded,
  skipped_reason_category, unit_count}`.
- `signal_records`: list of fixed records (one per extracted signal).
- `calibration_feature_records`: list of fixed records
  `{feature_name, feature_bucket, feature_value, feature_unit}`.
- `readiness_bucket_records`: list of fixed records
  `{bucket, bucket_count}` (one per bucket in the allowlist; the
  selected bucket has count 1, others 0).
- `recommended_next_measurement_records`: list of fixed records
  `{measurement, measurement_rationale}`.

Identity / boundary fields:

- `schema_version` = `d5a1_automated_calibration_feature_table.v1`
- `generated_by`, `generated_at`, `claim_level`, `status`, `mode`,
  `phase`.
- `cross_signal_alignment`, `readiness_bucket`.
- `input_summary`: `required_input_count`, `optional_input_count`,
  `required_loaded_count`, `optional_loaded_count`,
  `optional_skipped_count`, `input_phases`.
- Safe true flags (only when actually true):
  `automated_calibration_feature_extraction_performed`,
  `aggregate_only_public_artifact`, `diagnostic_only`.
- Always-false no-claim flags:
  `true_e_s_calibration_claimed`,
  `automated_e_s_full_calibration_claimed`,
  `human_e_s_calibration_claimed`, `calibrated_model_claimed`,
  `policy_recommendation_claimed`, `method_winner_claimed`,
  `external_benchmark_performance_claimed`,
  `downstream_agent_value_proven`, `promotion_ready`,
  `default_should_change`, `runtime_behavior_changed`,
  `retriever_changed`, `pack_builder_changed`, `backend_changed`,
  `default_policy_changed`, `evidencecore_semantics_changed`,
  `provider_calls_made`, `remote_provider_calls_made`.
- `forbidden_scan` summary (fail-closed before writing JSON).
- `framing`: fixed no-claim framing fields
  (`is_calibration: false`, `is_policy_recommendation: false`).

## CLI

```bash
python3 -m py_compile eval/d5a1_automated_calibration_feature_table.py
python3 eval/d5a1_automated_calibration_feature_table.py --self-test
python3 eval/d5a1_automated_calibration_feature_table.py \
    --out artifacts/d5a1_automated_calibration_feature_table/\
d5a1_automated_calibration_feature_table_report.json
```

No network/provider workflow is required (D5-A1 reads committed
artifacts only). CLI arguments: `--self-test`, `--out`.
Unknown/private-looking arguments are rejected with a generic
`invalid arguments` message (SafeArgumentParser pattern).

## Reused helpers

D5-A1 imports F1-D helpers (backward-compatible; none modified):

- F1-D scanner: `f1d._scan_f1d` (combines F1-C/C5-A/C5-C/C5-E
  scanners and F1-D-specific checks); D5-A1 adds D5-A1-specific
  forbidden keys and record-shape checks.
- F1-D safe value path constants for false-positive suppression.

D5-A1 does NOT mutate F1-D result semantics.

## Forbidden scanner (public, fail-closed)

A strict forbidden-output scanner runs fail-closed before writing the
public JSON. It combines:

- The F1-D forbidden scanner (which itself combines F1-C/C5-A/C5-C/C5-E
  scanners and F1-D-specific forbidden keys, record-shape checks, and
  value-pattern checks).
- D5-A1-specific forbidden keys: raw input artifact paths/content
  (`input_artifact_path`, `input_artifact_content`, `input_artifact_json`,
  `raw_input`, `raw_artifact`), calibration claim keys
  (`calibrated_model`, `calibrated_label`, `calibration_applied`,
  `calibration_performed`), policy/default recommendation keys
  (`policy_recommendation`, `recommended_policy`,
  `recommended_default`, `recommended_method`, `default_method`,
  `winner`, `best_method`, `best_arm`, `best_family`,
  `preferred_method`, `preferred_policy`), raw B16 task text / provider
  payloads (`task_text`, `task_prompt`, `provider_payload`,
  `raw_payload`), per-unit metric array keys (`per_row_metrics`,
  `per_needle_metrics`, `row_metrics`, `needle_metrics`, `row_hashes`,
  `needle_hashes`, `per_unit_metrics`, `per_unit_utility`).
- D5-A1 record-shape check: `input_artifact_records`, `signal_records`,
  `calibration_feature_records`, `readiness_bucket_records`,
  `recommended_next_measurement_records` must be lists of records
  (NOT dict-keyed mirrors).
- D5-A1 value-pattern check: rejects raw model routing prefixes
  (reused from F1-D).

No `winner` / `best_method` / `recommended_default` /
`calibrated_model` / `policy_recommendation` fields are emitted. No
per-unit metric arrays, raw input artifact paths/content, or B16 task
text are committed.

## Self-tests

- Artifact identity fields (schema, claim, status, mode, phase,
  generated_by).
- Safe true flags present; no-claim flags false.
- Records-shaped containers (all 5 D5-A1 record containers are lists;
  no dynamic dict mirrors).
- Readiness buckets allowlist (all 5 buckets; selected count 1).
- Recommended measurements are measurement-only (all in
  `manual_reference_audit` / `heldout_benchmark_scale` /
  `live_downstream_scale` allowlist; no policy/default/winner/
  promotion).
- Input contract validation: clean input claim-safe; unsafe claim flag
  detected; input forbidden_scan fail detected.
- Signal extraction: retrieval signals (3), benchmark signals (3),
  live provider signals (1).
- Cross-signal alignment: retrieval_robust_positive_plus_live_positive;
  conflicting when retrieval positive + live negative; retrieval-only
  insufficient when no live.
- Calibration features: records-shaped; cross_signal_alignment bucket.
- Readiness bucket computation: ready_for_manual_review; conflicting;
  retrieval_only_insufficient; insufficient_signal when no signals.
- Full pass report build; forbidden scan clean; self-scan clean.
- Fail-closed input contract (status fail_input_contract; feature
  extraction false).
- Scanner rejections: repo URL, commit SHA, repo slug, task_id key,
  query key, winner key, best_method key, recommended_default key,
  calibrated_model key, policy_recommendation key, per_row_metrics key,
  per_needle_metrics key, provider_payload key, task_text key,
  input_artifact_path key, raw routing prefix value, tmp path, provider
  key, secret sentinel, dict-keyed D5-A1 containers.
- Scanner allows: method/benchmark/signal/feature/bucket/measurement/
  phase labels, signal_records lists.
- Fail-closed generation: clean report does not raise; leaked report
  raises SystemExit; calibrated_model/policy_recommendation leak
  raises SystemExit.
- CLI argument surface.

## Validation

```text
python3 -m py_compile eval/d5a1_automated_calibration_feature_table.py  => PASS
python3 eval/d5a1_automated_calibration_feature_table.py --self-test  => PASS (128/128 checks)
python3 eval/d5a1_automated_calibration_feature_table.py \
  --out artifacts/d5a1_automated_calibration_feature_table/\
d5a1_automated_calibration_feature_table_report.json  => PASS
  (status: automated_calibration_feature_table_pass,
   forbidden_scan: pass, self_test_passed: true,
   cross_signal_alignment: retrieval_robust_positive_plus_live_positive,
   readiness_bucket: ready_for_manual_review,
   signals: 9, features: 7, bucket_records: 5, measurements: 2,
   automated_calibration_feature_extraction_performed: true,
   downstream_agent_value_proven: false,
   true_e_s_calibration_claimed: false,
   external_benchmark_performance_claimed: false,
   method_winner_claimed: false,
   leaderboard_entry_claimed: false,
   promotion_ready: false,
   default_should_change: false,
   retriever_changed: false,
   pack_builder_changed: false,
   backend_changed: false,
   default_policy_changed: false,
   evidencecore_semantics_changed: false,
   calibrated_model_claimed: false,
   policy_recommendation_claimed: false)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

Local feature extraction run produced the following aggregate records
(no raw task/row/needle IDs/repo URLs/commits/paths/spans/source/
snippets/prompts/responses/provider payloads/per-unit metric arrays/
B16 task text/private labels/content hashes/candidate/evidence rows
committed):

```text
status: automated_calibration_feature_table_pass
forbidden_scan: pass
cross_signal_alignment: retrieval_robust_positive_plus_live_positive
readiness_bucket: ready_for_manual_review
input_artifact_records:
  F1-D: required=true, loaded=true, claim_safe=true, unit_count=30
  F1-C: required=true, loaded=true, claim_safe=true, unit_count=30
  C5-C: required=true, loaded=true, claim_safe=true, unit_count=20
  C5-F: required=true, loaded=true, claim_safe=true, unit_count=10
  B16-E: required=true, loaded=true, claim_safe=true, unit_count=16
  D5-A0: required=false, loaded=true, claim_safe=true, unit_count=4
  B16-D: required=false, loaded=true, claim_safe=true, unit_count=8
signal_records:
  bm25_vs_empty_retrieval_utility (F1-D): point=+0.465035, ci=[+0.298938, +0.464512, +0.624026], sign+=1.0, units=30
  regex_vs_bm25_retrieval_utility (F1-D): sign-=1.0, units=30
  symbol_vs_bm25_retrieval_utility (F1-D): sign-=1.0, units=30
  bm25_positive_on_both_benchmarks (C5-C+C5-F): bm25_positive_on_both=true
  regex_symbol_negative_on_both_benchmarks (C5-C+C5-F): regex_negative=true, symbol_negative=true
  benchmark_method_agreement (C5-C+C5-F): agree=3, disagree=0
  b16e_context_pack_signal (B16-E): solve_rate_delta=+0.875, families_positive=4
  d5a0_automated_calibration_smoke_anchor (D5-A0)
  b16d_secondary_live_signal (B16-D)
calibration_feature_records:
  bm25_vs_empty_retrieval_utility_magnitude: bucket=weak_positive, value=0.465035
  bm25_vs_empty_sign_stability: bucket=stable_positive, value=1.0
  regex_vs_bm25_sign_stability: bucket=stable_negative, value=1.0
  symbol_vs_bm25_sign_stability: bucket=stable_negative, value=1.0
  live_provider_solve_rate_delta: bucket=strong_positive, value=0.875
  live_provider_family_distribution: bucket=all_families_positive, value=4
  cross_signal_alignment: bucket=retrieval_robust_positive_plus_live_positive
readiness_bucket_records:
  ready_for_manual_review: count=1
  needs_more_live_downstream: count=0
  retrieval_only_insufficient: count=0
  conflicting_signals: count=0
  insufficient_signal: count=0
recommended_next_measurement_records:
  manual_reference_audit
  heldout_benchmark_scale
```

This is automated calibration feature extraction over committed
aggregate artifacts. It is not calibration, not a calibrated model
claim, not a policy/default/method winner recommendation, not a
benchmark result, not downstream utility, and not a promotion.

## Caveats

- D5-A1 is the public aggregate-only automated calibration feature
  table artifact. It is eval/diagnostic only. It does NOT change
  runtime, retriever, pack, backend, or default policy; it does NOT
  change EvidenceCore semantics. It is NOT calibration, NOT a
  calibrated model claim, NOT a policy/default recommendation, NOT a
  benchmark result, NOT downstream utility, NOT true E/S calibration,
  NOT an external benchmark performance claim, NOT a leaderboard entry,
  NOT a method winner, and NOT a promotion.
- D5-A1 machine-reads committed aggregate artifacts. It does NOT
  summarize research logs or freeform docs. It does NOT re-run any
  retrieval or scoring pipeline.
- D5-A1 makes NO provider calls and NO remote provider calls. All
  input data is read from committed aggregate artifacts (aggregate
  counts and metrics only).
- D5-A1 does NOT prove downstream agent value.
  `downstream_agent_value_proven=false`.
- D5-A1 does NOT claim true E/S calibration.
  `true_e_s_calibration_claimed=false`.
- D5-A1 does NOT claim a calibrated model.
  `calibrated_model_claimed=false`.
- D5-A1 does NOT make policy/default recommendations.
  `policy_recommendation_claimed=false`.
- D5-A1 does NOT claim a method winner.
  `method_winner_claimed=false`.
- The features are weak-supervision features for future calibration /
  manual review, NOT calibrated labels. The readiness buckets are
  diagnostic buckets, NOT promotion/default gates.
- The recommended next measurements are measurement-only (manual
  reference audit, heldout benchmark scale, live downstream scale).
  They are NOT policy/default/method winner recommendations.
- The cross-signal alignment and readiness bucket are deterministic
  functions of the input artifact signals. They are NOT calibrated
  labels and NOT policy decisions.
- All no-claim / no-runtime-change flags remain false; diagnostic
  flags (`aggregate_only_public_artifact`, `diagnostic_only`) remain
  true; `automated_calibration_feature_extraction_performed=true` only
  when feature extraction actually executed.
- No runtime/retriever/pack/model/backend/default-policy files were
  modified. No promotion/default/runtime claims change.
