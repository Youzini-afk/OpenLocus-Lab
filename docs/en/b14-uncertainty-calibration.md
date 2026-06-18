# B14 Uncertainty Calibration

Date: 2026-06-18

B14 is the **uncertainty calibration** phase that follows B13 (distributionally
robust policy search). The goal is **model-independent uncertainty
calibration** for the balanced-policy candidate: produce an uncertainty score
per record (never calibrated to a specific model name) from local candidate
signals, model output structure, and cross-model disagreement, then evaluate
that score with **risk-coverage**, **selective risk**, **ECE**, and
**PFP-at-fixed-coverage** metrics, with worst-group reporting and rotating
leave-one-model-family-out validation.

> **Important claim boundary.** B14 IS the uncertainty-calibration *stage*
> (`stage_is_uncertainty_calibration=true`), but the shipped skeleton performs
> NO empirical uncertainty calibration
> (`uncertainty_calibration_performed=false`). The synthetic-fixture /
> `--input` stub reports set `calibrated_model_claim=false` and
> `per_record_inputs_available=false` so the public artifact cannot be mistaken
> for an empirical B14 calibration. Even when a future empirical B14 run finds
> a well-calibrated uncertainty score, the results are NOT promoted.
> `promotion_ready=false`, `default_should_change=false`, and `EvidenceCore`
> semantics are unchanged. B14 results are research candidates only: they
> inform B16 (downstream agent evaluation) and any future selective-abstention
> policy, but B14 does not authorize any default change, any policy promotion,
> any calibrated-model claim, or any EvidenceCore modification. B14 is a
> second-priority / parallel-track item in the B10-B19 Breakthrough Sprint.

> **Important public-aggregate boundary.** Real B14 uncertainty calibration
> requires private / ephemeral per-record inputs: per-record uncertainty
> scores (or the raw signals to compute them), per-record binary outcomes
> (was the selected span correct), paired cross-model outputs (for
> cross-model disagreement), schema-repair per-call rows (for model output
> structure), and candidate score distributions / entropy (for local
> candidate signals). None of those are present in the public B11 aggregate,
> the B12 public-aggregate screen, or the B13 public-aggregate feasibility
> report, so real B14 calibration cannot be performed from public aggregates
> alone. The bounded public-aggregate feasibility / no-go screen at
> `eval/b14_public_aggregate_feasibility_screen.py` reads the published B11,
> B12, and B13 artifacts and emits a `no_go_public_aggregate_only` (or, when
> the B11 aggregate itself has no records,
> `insufficient_data_public_aggregate_only`) feasibility report under
> `artifacts/b14_uncertainty_calibration/`. The screen never claims empirical
> uncertainty calibration, never computes ECE / risk-coverage / selective
> risk / PFP-at-coverage, never declares a calibrated model, and never
> declares a winner.

> **CRITICAL anti-fabrication boundary.** The skeleton MUST NOT compute fake
> ECE / risk-coverage / selective-risk / PFP-at-coverage metrics from
> aggregate means. Aggregate means do not contain per-record (uncertainty,
> outcome) pairs, so any calibration metric computed from them would be a
> fabrication. The synthetic fixture validates only that the metric NAMES,
> gate thresholds, coverage levels, ECE bin definition, and split protocol
> are wired correctly; it does not present synthetic metric values as
> empirical calibration results. The report surfaces
> `metrics_evaluated=false` and `no_fake_metrics_from_aggregate_means=true`
> so a reader cannot mistake the skeleton for an empirical B14 calibration.

## Preregistration declaration

The following artifacts, signal families, metric registry, coverage levels,
ECE bin definition, split protocol, validation methodology, and predeclared
success/failure criteria are **FROZEN** before any B14 calibration runs. No
retuning of the signal families, the metric registry, the coverage levels,
the ECE bin count, the split fractions, or the success criteria is allowed
after B14 calibration runs begin. Any post-hoc analysis must be labeled
exploratory and require a separate validation round.

### Frozen artifacts

- `balanced_policy_v1_benchmark_routed` (B10 frozen spec) — referenced,
  not modified
- `balanced_policy_v1_runtime_shadow_ambiguous_branch` (B10B shadow
  predicate) — referenced, not modified
- B11/B12/B13 frozen criteria — referenced, not modified
- B14 algorithm spec itself
  (`artifacts/b14_uncertainty_calibration/b14_uncertainty_calibration.algorithm.json`)
  — frozen before any calibration runs; stable sha256

## Objective

Produce a **model-independent** uncertainty score `u(record) ∈ [0, 1]` from
the three allowed signal families, then evaluate it on a held-out test split
with risk-coverage, selective risk, ECE, and PFP-at-fixed-coverage, with
worst-group reporting and rotating leave-one-model-family-out validation.

## Target uncertainties

The uncertainty score targets the **selected span / candidate correctness**
prediction: `u(record)` should be a calibrated probability that the balanced
policy's selected span / candidate is correct for that record. The
calibration TARGET is the per-record binary outcome (was the selected span
correct); it is required as an evaluation target but MUST NEVER enter the
uncertainty score as a feature.

## Allowed signal families

The uncertainty score is built from three allowed signal families. No
signal may reference a raw model name; signals are computed from local
candidate state, model output structure, and cross-model disagreement only.

### Family 1: `local_candidate_signals`

Computed from candidate state only; no labels, no model names. These
describe the shape of the candidate pool a routing decision was made from.

- `candidate_count`
- `candidate_support_exists`
- `score_distribution_spread`
- `top1_top2_score_gap`
- `entropy_proxy`
- `anchor_disagreement`
- `rrf_backed_by_anchor`
- `dense_support_present`

### Family 2: `model_output_structure`

Computed from the model's structured output, NOT from the model identity.
These describe whether the model produced a schema-valid, span-narrow-valid,
within-candidate response.

- `schema_valid`
- `llm_span_narrow_valid`
- `llm_span_within_candidate`
- `output_mode_stable`
- `schema_repair_invoked`

### Family 3: `cross_model_disagreement`

Computed from paired outputs of two or more model families on the SAME
record. These require paired per-record outputs across model families.

- `per_record_action_disagreement`
- `span_overlap_disagreement`
- `rank_disagreement_topk`

## Forbidden labels / forbidden features

B14 must NOT use benchmark-private labels or score-private fields as
UNCERTAINTY SIGNALS (features). Per-record outcomes (was the selected span
correct) are the calibration TARGET, not a signal; they are required as
evaluation targets but must never enter the uncertainty score.

Forbidden signal features:

- `task_bucket`, `task_risk_tags` (benchmark-private labels)
- `has_gold`, `score_group`, `outcome_metrics` (score-private fields)
- `gold_spans`, `must_not_primary`, `expected_behavior`, `oracle_type`,
  `risk_tags` (label / oracle fields)

**NO model names in `algorithm_spec`**: B14 must use abstract `family_slots`
(`family_a`/`family_b`/`family_c`/`family_d`) and signal-family capabilities,
not raw model names like "Kimi", "Qwen", "DeepSeek", or "GLM". The B14
evaluator enforces this with the special invariant
`algorithm_spec_has_no_model_names=true`.

## Required per-record inputs

Real B14 calibration requires ALL of the following per record. If any is
missing, real B14 cannot run and the skeleton emits `insufficient_data` /
`not_implemented`.

- `per_record_uncertainty_signals` (the raw signals needed to compute the
  uncertainty score)
- `per_record_outcome_binary` (was the selected span correct; the
  calibration TARGET)
- `paired_cross_model_outputs` (for cross-model disagreement signals)
- `schema_repair_per_call_rows` (for model output structure signals)
- `candidate_score_distribution` (for local candidate signals — entropy /
  top1-top2 gap / spread)
- `group_membership_for_worst_group_split` (model_family × repo, for
  stratified split and worst-group reporting)

## Split / calibration / test protocol

Real B14 splits per-record inputs into a **calibration split** and a **test
split**, stratified by (model_family, repo). The split protocol is
`stratified_by_model_family_and_repo` with `calibration_fraction=0.50` and
`test_fraction=0.50`. The calibration split is the ONLY split on which any
recalibration / temperature fitting may be applied
(`recalibration_allowed_on_calibration_split_only=true`); the test split is
held out and reported once (`test_split_reported_once=true`). No metric on
the test split may feed back into recalibration.

## Coverage levels

Fixed coverage levels at which `selective_risk` and `pfp_at_fixed_coverage`
are reported. These are FROZEN so no post-hoc coverage threshold tuning is
possible after real B14 runs begin:

- `0.50`
- `0.70`
- `0.90`
- `0.95`
- `0.99`

## ECE target definition

ECE (Expected Calibration Error) is computed on the test split using
**equal-width binning** over `[0, 1]` into `ece_bin_count=15` bins
(`ece_bin_scheme=equal_width`). For each bin `B_m`, compute the average
confidence `conf(B_m)` and average accuracy `acc(B_m)`, then

```text
ECE = Σ_m (|B_m| / N) * |conf(B_m) - acc(B_m)|
```

The bin count is FROZEN so no post-hoc bin-count tuning is possible.

## Worst-group reporting

B14 reports worst-group metrics over `{model_family, repo, language,
task_bucket}` groups, plus a `CVaR_20%` tail average (worst 20% of group
metrics). The CVaR tail fraction is `cvar_alpha=0.20` (frozen).

### Rotating leave-one-model-family-out

B14 must pass **all 3 rotations** for a candidate uncertainty score to be
considered robustly calibrated, mirroring B13:

| Rotation | Train on | Test on |
| --- | --- | --- |
| `loo_family_a` | Qwen + DeepSeek (Flash + Pro) | Kimi |
| `loo_family_b` | Kimi + DeepSeek (Flash + Pro) | Qwen |
| `loo_family_c_and_d` | Kimi + Qwen | DeepSeek (Flash + Pro) |

The held-out model family is used only for evaluation; no recalibration on
the test split may peek at the held-out family.

## Privacy / publication gates

Public artifacts must be aggregate-only. The B14 evaluator enforces:

- **no** raw records, task IDs, repo IDs, candidate IDs, paths, spans,
  snippets, prompts, responses, gold spans, private labels, provider keys,
  base URLs, API keys/secrets/tokens, content SHAs, digests, or line ranges
  in any public artifact;
- **no** raw filesystem path strings, 64-char hex digests, http(s) URLs, or
  credential assignments as values;
- **no** raw model names in `algorithm_spec` (`family_slots` only);
- `aggregate_only_public_artifact=true`;
- `new_provider_calls=0` (replay / calibration only; no live LLM calls);
- `forbidden_public_key_scan_clean=true`.

## Predeclared success / partial / failure criteria

The criteria below are FROZEN before any B14 calibration runs
(`PREDECLARED_CRITERIA`):

| Outcome | Criterion |
| --- | --- |
| **Success** | ECE on the test split ≤ `0.05` AND selective risk at coverage=0.90 on the test split ≤ `0.10` AND worst-group selective risk at coverage=0.90 ≤ `0.15` AND all 3 leave-one-out rotations pass (no regression beyond `0.02` approx-equality threshold) AND strictly-greater-than-`0.02` improvement vs the reference (uncalibrated) score on at least one metric. |
| **Partial** | Some metrics pass (e.g., ECE within threshold on the test split) but not all (e.g., worst-group selective risk regresses on one rotation). |
| **Failure** | ECE on the test split > `0.05`, OR worst-group selective risk at coverage=0.90 worse than the reference (uncalibrated) score, OR any rotation regresses beyond the `0.02` approx-equality threshold. |

Frozen numeric gates:

- `ece_test_threshold = 0.05`
- `selective_risk_at_coverage_0_90_threshold = 0.10`
- `worst_group_selective_risk_at_coverage_0_90_threshold = 0.15`
- `strictly_greater_threshold = 0.02`
- `approx_equal_threshold = 0.02`
- `cvar_alpha = 0.20`
- `coverage_levels = [0.50, 0.70, 0.90, 0.95, 0.99]`
- `ece_bin_count = 15` (`equal_width`)

The B14 verdict framework emits one of:

- `success` (ECE + selective-risk + worst-group + all rotations pass +
  strict improvement)
- `failure` (ECE above threshold, or worst-group selective risk worse, or
  rotation regression)
- `partial` (some metrics pass, not all)
- `insufficient_data` (synthetic fixture, or too few records to calibrate)
- `not_implemented` (`--input` stub, real calibration deferred)

The skeleton only emits `insufficient_data` (synthetic fixture) or
`not_implemented` (ci_ephemeral_records stub); `success` / `failure` /
`partial` are reserved for a future empirical
`uncertainty_calibration_performed=true` path that is NOT present in this
skeleton.

## Data requirement

B14 needs per-record inputs from B11/B13 live runs (4 model families × 8
repos) plus paired cross-model outputs, schema-repair per-call rows, and
candidate score distributions. No new live LLM calls are required for the
calibration itself if the per-record signals are already recorded from
prior runs.

If the per-record inputs are not available, B14 cannot run a real
calibration; the evaluator emits `insufficient_data` (synthetic fixture
self-test) or `not_implemented` (`--input` stub).

## Safety invariants

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
stage_is_uncertainty_calibration=true (B14 stage IS uncertainty calibration)
uncertainty_calibration_performed=false (skeleton performs no empirical calibration)
calibrated_model_claim=false (no model is claimed to be calibrated)
per_record_inputs_available=false (skeleton; no real per-record inputs)
policy_search_performed=false
quality_strategy_tuned=false
metrics_evaluated=false (skeleton; no fake metric values from aggregate means)
no_fake_metrics_from_aggregate_means=true
runtime_calls_by_replay=0 (replay makes no new live calls)
model_calls_by_replay=0 (replay makes no new LLM calls)
aggregate_only_public_artifact=true
algorithm_spec_has_no_model_names=true (B14 special invariant)
```

## What B14 does NOT prove

- B14 does **not** calibrate any model.
- B14 does **not** make any `calibrated_model_claim`.
- B14 does **not** promote any policy or any uncertainty score.
- B14 does **not** change any defaults.
- B14 does **not** change `EvidenceCore` semantics.
- B14 does **not** authorize B16 without separate user review.
- B14 results are research candidates only; a B14-found calibrated
  uncertainty score is NOT a calibrated-model claim and is NOT the new
  default until separately promoted via the standard promotion process.
- B14's `--input` path is a stub (`verdict="not_implemented"`); full
  calibration computation is deferred to a later task.
- B14 does **not** compute ECE / risk-coverage / selective risk /
  PFP-at-coverage from aggregate means.

## Self-test (read-only) and explicit artifact regeneration

```bash
python3 eval/b14_uncertainty_calibration.py --self-test
python3 eval/b14_uncertainty_calibration.py --regenerate-artifacts
python3 eval/b14_public_aggregate_feasibility_screen.py --self-test
python3 eval/b14_public_aggregate_feasibility_screen.py \
    --out artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json
```

The `eval/b14_uncertainty_calibration.py --self-test` run is **read-only**:
it verifies the signal-family grammar, metric-name registry, coverage
levels, ECE bin definition, split protocol, and rotation definitions against
a synthetic fixture (definitions-only; no per-record (uncertainty, outcome)
pairs, no computed metric values) and compares the in-memory expected
algorithm spec + report to the on-disk artifacts, **failing on drift**. It
does NOT mutate checked-in artifacts. It emits
`stage_is_uncertainty_calibration=true`,
`uncertainty_calibration_performed=false`, `calibrated_model_claim=false`,
`per_record_inputs_available=false`, `metrics_evaluated=false`, and
`no_fake_metrics_from_aggregate_means=true`, plus top-level
`uncertainty_score_found=false`, `rotations_evaluated=false`,
`rotations_defined=true`, `rotation_count=3`, `winner_declared=false`, so
the synthetic-fixture report is unambiguously NOT an empirical B14
calibration. Synthetic / stub reports emit only rotation *definitions*
(`rotations_defined=true`, `rotation_count=3`,
`rotations_evaluated=false`); they never emit per-rotation `passes=true`,
`test_ece`, `test_selective_risk`, `test_risk_coverage_curve`,
`test_pfp_at_fixed_coverage`, or `delta_vs_reference` as if empirical. The
skeleton verdict framework emits only `insufficient_data` (synthetic
fixture) or `not_implemented` (ci_ephemeral_records stub); `success` /
`failure` / `partial` are reserved for a future empirical
`uncertainty_calibration_performed=true` path that is NOT present in this
skeleton.

The read-only self-test runs 11 checks:

1. `forbidden_scan` — forbidden public keys/values scan (incl. raw
   model-name scan on the algorithm spec)
2. `spec_hash_stable` — algorithm spec sha256 stability
3. `signal_family_grammar` — 3 signal families disjoint, no forbidden
   features, outcomes are inputs not signals
4. `metric_registry` — 6 metric names defined; no aggregate-mean metrics
5. `coverage_levels_and_ece_bins` — coverage levels + ECE bin definition
6. `split_protocol` — calibration/test stratified by model_family and repo
7. `leave_one_out_rotations_defined` — 3 rotations (definitions only; no
   empirical per-rotation metric values)
8. `no_fake_metrics_from_aggregate_means` — synthetic fixture has no
   per-record pairs and no metric values
9. `input_stub_not_implemented` — `--input` stub returns `not_implemented`
10. `reference_specs_pinned` — B10/B10B/B11/B12/B13 reference specs
    present on disk
11. `artifacts_match_in_memory` — read-only drift check: in-memory expected
    spec + report match the on-disk artifacts

`python3 eval/b14_uncertainty_calibration.py --regenerate-artifacts` is
the ONLY path that mutates checked-in artifacts: it (re)writes the on-disk algorithm spec +
synthetic-fixture report from the current build functions. After mutating,
re-run `--self-test` to confirm the on-disk artifacts now match the
in-memory expected objects (no drift).

The `--input` path is a non-canonical stub path: it requires an explicit
`--out` destination and refuses to write the checked-in
`b14_uncertainty_calibration_report.json`. It can write a temporary stub
report for development, but it does not mutate checked-in B14 artifacts.

The `eval/b14_public_aggregate_feasibility_screen.py --self-test` run
verifies the bounded public-aggregate feasibility / no-go screen against a
synthetic minimal B11 + B12 + B13 fixture. It emits
`verdict=no_go_public_aggregate_only` (or
`insufficient_data_public_aggregate_only` when the B11 aggregate has no
records), with `uncertainty_calibration_performed=false`,
`calibrated_model_claim=false`, `per_record_inputs_available=false`,
`uncertainty_score_found=false`, `rotations_evaluated=false`,
`metrics_evaluated=false`, and `no_fake_metrics_from_aggregate_means=true`.
It runs 4 checks: `happy_path`, `input_validation_blocks`,
`insufficient_data_branch`, and `forbidden_scan`.

## Artifacts

- `artifacts/b14_uncertainty_calibration/b14_uncertainty_calibration.algorithm.json`
  (frozen spec; deterministic, stable sha256; regenerated only via
  `--regenerate-artifacts`)
- `artifacts/b14_uncertainty_calibration/b14_uncertainty_calibration_report.json`
  (synthetic-fixture self-test report, verdict `insufficient_data`;
  `uncertainty_calibration_performed=false`,
  `calibrated_model_claim=false`, `per_record_inputs_available=false`,
  `stage_is_uncertainty_calibration=true`, `metrics_evaluated=false`,
  `no_fake_metrics_from_aggregate_means=true`,
  `uncertainty_score_found=false`, `rotations_evaluated=false`,
  `rotations_defined=true`, `rotation_count=3`, `winner_declared=false`;
  no empirical per-rotation metric values)
- `artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json`
  (bounded public-aggregate feasibility / no-go screen report;
  `verdict=no_go_public_aggregate_only` or
  `insufficient_data_public_aggregate_only`;
  `uncertainty_score_found=false`, `rotations_evaluated=false`,
  `full_b14_possible_from_public_artifacts=false`,
  `metrics_evaluated=false`, `no_fake_metrics_from_aggregate_means=true`)

## What's autonomous vs. needs user action

### Autonomous (can be done now)

- B14 plan document (this file)
- B14 report aggregator skeleton (`eval/b14_uncertainty_calibration.py`) +
  read-only `--self-test` (compares in-memory expected artifacts to on-disk
  artifacts, fails on drift) and explicit `--regenerate-artifacts` mutating
  path (emits `stage_is_uncertainty_calibration=true`,
  `uncertainty_calibration_performed=false`,
  `calibrated_model_claim=false`, `per_record_inputs_available=false`,
  `metrics_evaluated=false`, `no_fake_metrics_from_aggregate_means=true`,
  `uncertainty_score_found=false`, `rotations_evaluated=false`,
  `rotations_defined=true`, `rotation_count=3`, `winner_declared=false`;
  no empirical per-rotation metric values)
- B14 frozen algorithm spec + synthetic-fixture report artifacts
- B14 bounded public-aggregate feasibility / no-go screen
  (`eval/b14_public_aggregate_feasibility_screen.py`) + self-test +
  `artifacts/b14_uncertainty_calibration/b14_public_aggregate_feasibility_report.json`
  (reads the published B11 + B12 + B13 artifacts; emits
  `no_go_public_aggregate_only` / `insufficient_data_public_aggregate_only`;
  never claims empirical calibration, never computes a metric, never
  selects an uncertainty score, never declares a winner)

### Needs per-record ephemeral inputs

- B14 real calibration requires per-record uncertainty scores, per-record
  binary outcomes, paired cross-model outputs, schema-repair per-call rows,
  and candidate score distributions from B11/B13 live runs. If those records
  are not yet produced, B14 emits `insufficient_data` / `not_implemented`.

### Needs user review

- Results interpretation
- Decision to proceed to B16 (downstream agent evaluation) using a
  B14-found calibrated uncertainty score as a research candidate
- Decision to use a B14-found uncertainty score for future selective-
  abstention policy work (separate preregistration required)
- Decision to expand from minimum viable to full B14 (more signals, more
  rotations, more groups)

## Next steps after B14

- **B14 success**: a calibrated, model-independent uncertainty score is
  identified (ECE ≤ 0.05 on the test split, worst-group selective risk at
  coverage=0.90 ≤ 0.15, all 3 rotations pass). Proceed to B16 to test it
  downstream as a selective-abstention signal.
- **B14 failure**: no calibrated uncertainty score meets the predeclared
  criteria. The balanced policy continues without a calibrated uncertainty
  score; B16 should use the uncalibrated reference.
- **B14 partial**: some metrics pass, not all. Investigate group-conditional
  calibration; possibly expand the signal families in a separate B14B round
  (separate preregistration required).
