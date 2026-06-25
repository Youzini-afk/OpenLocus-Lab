# BEA-v1-P4L: Locked Non-Python P4 Scheduler Validation

Date: 2026-06-25. BEA-v1-P4L is a bounded **scheduler-validation phase**
performed after the BEA-v1-P4K result (checkpoint `dccfb64`, CI
`28151914531`, `cross_source_locked_reservoir_ready_for_locked_p4_validation_design`,
locked non-Python denominator 272). It validates whether the frozen BEA-v1-P4
retrieval-action scheduler generalizes from the original same-frame Python
denominator to the P4K-locked, all-prior-disjoint non-Python cross-source
reservoir.

This is a scheduler-validation phase only. It is **not** P5, not BEA-v1-A, not
selector/reranker work, not runtime/default promotion, not a method-winner
claim, not parameter tuning, not threshold search, not new arms, not broad
retrieval expansion, not frozen P4 rerun on the old Python denominator, and not
latency-in-relevance scoring.

> `claim_level = bea_v1_p4l_locked_non_python_scheduler_validation_only`.
> `provider_calls_made=false`, `latency_in_candidate_relevance=false`,
> `selector_or_reranker_executed=false`, `p5_authorized=false`,
> `v1_a_authorized=false`, `frozen_p4_rerun_authorized=false`,
> `future_locked_p4_validation_authorized=false`, `locked_p4_validation_authorized=false`,
> `parameter_tuning_executed=false`, `threshold_search_executed=false`,
> `new_arms_added=false` are binding.

## Fixed denominator

The P4K locked reservoir exactly:

- P4K result checkpoint: `dccfb64`
- P4K CI run: `28151914531`
- Required reconstructed counts: P4H 73/73, P4I 73/73, P4J 333/333 (61 Python
  + 272 non-Python), P4J overlap with P4H/P4I: 61, locked denominator: 272,
  all non-Python.

The implementation reconstructs the locked denominator before running any
scheduler arm. It must reproduce the full P4J/P4K split (333 total, 61 Python,
272 non-Python) and the locked non-Python denominator (272). If those counts do
not match, the status is `no_go_p4l_locked_denominator_unavailable` or
`fail_schema_contract`; it must NOT silently change the denominator.

## Allowed frozen arms

Run only these 4 arms, with definitions frozen from prior committed P2/P3/P4
code:

1. `baseline_current_candidate_pool` (depth=1, no query anchors)
2. `p2_depth_only_reference` (depth=4, no query anchors)
3. `p3_constrained_depth_policy_reference` (constrained depth policy)
4. `p4_latency_aware_action_scheduler_frozen` (frozen P4 scheduler)

No new arm, selector, reranker, scoring policy, parameter search, threshold
search, or weight tuning is allowed.

## Frozen thresholds (no post-hoc tuning)

- P4 retained-gain ratio ≥ 0.75 (P4's improvement over baseline / P2's
  improvement over baseline)
- P4 latency ratio vs P3 ≤ 2.0
- P4 latency reduction vs P3 ≥ 0.10
- P4 pool growth ratio ≤ 4.0
- P4-treatment hard-cap violations = 0; reference-arm hard-cap violations are reported only.

## Statuses

- `bea_v1_p4l_locked_non_python_scheduler_validation_pass` — exact denominator
  reconstruction (333/61/272 with locked non-Python denominator 272), scheduler
  arms executed, P4 improves reach over baseline, P4 retains ≥ 0.75 of P2 reach
  gain, P4 latency below frozen P3 threshold, pool growth within frozen cap,
  P4-treatment hard-cap violations zero, subgroup guard pass. Reference-arm
  hard-cap violations are reported but do not decide the P4 treatment gate.
- `no_go_p4l_locked_non_python_scheduler_validation_failed` — denominator exact
  but P4 fails one or more frozen gates.
- `no_go_p4l_locked_denominator_unavailable` — locked denominator cannot be
  reconstructed to exactly 272.
- `unavailable_with_reason` — default no-network artifact (honest, not a pass).
- `fail_schema_contract` / `fail_forbidden_scan` — privacy/schema/provenance
  failures. No `fail_*` status is CI-valid for a network-enabled real run.

## Public artifact contract

Required aggregate-only record tables (records-only; no dynamic dicts):

- `source_run_records`
- `arm_metrics_records`
- `subgroup_records`
- `stop_go_records`
- `gate_records`
- `private_manifest_records`
- `failure_category_count_records`
- `framing`
- `forbidden_scan`

`self_test_checks_total` and `self_test_checks_passed` are counts-only (int);
no `self_test_checks` list field is present. No private row IDs, raw keys, repo
URLs, base commits, queries, candidate paths, gold paths, snippets, or provider
payloads are serialized. Private per-record arm outcomes and scheduler traces
are written under `/tmp` only with `path_publicly_serialized=false`.

## Workflow

The manual workflow
`bea-v1-p4l-locked-non-python-scheduler-validation.yml` runs only via
`workflow_dispatch` and accepts `enable_external_benchmark_network`. It builds
the OpenLocus release CLI, runs self-tests, regenerates FD1 private
decomposition under `/tmp`, validates the 239/86040 replay, reconstructs the
P4K locked non-Python denominator, runs the 4 frozen scheduler arms, validates
the report fail-closed, and uploads the aggregate report. A prevalidation
artifact is uploaded before the validator (always, for diagnosability) without
compromising the final fail-closed gate. Private directories use `/tmp`, not
`$RUNNER_TEMP`.

## Local validation

```text
python3 -m py_compile eval/bea_v1_p4l_locked_non_python_scheduler_validation.py  => PASS
python3 eval/bea_v1_p4l_locked_non_python_scheduler_validation.py --self-test  => PASS (122/122 checks)
python3 eval/bea_v1_p4l_locked_non_python_scheduler_validation.py \
  --out artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json  => PASS
  (default no-network status: unavailable_with_reason,
   forbidden_scan=pass, locked_denominator_count=0,
   scheduler_arms_executed=false,
   self_test_checks_total=122, self_test_checks_passed=122)
```

## CI result

Manual network-enabled CI run `28184096209` completed green in 2h33m08s after
the heartbeat workflow patch `e98839b`. Earlier attempts are superseded:

- `28160078060` exposed a false No-Go caused by summing reference-arm hard-cap
  violations into the P4 treatment gate.
- `28166304912` correctly reported live reconstruction drift as a denominator
  No-Go under the corrected classifier.
- `28175852713` failed before P4L because FD1 replay only rebuilt 215/239
  groups.
- `28178712989` regenerated FD1 successfully but the evaluator step produced no
  artifact, so `e98839b` added a CI heartbeat wrapper without changing the
  validator.

Final status: `bea_v1_p4l_locked_non_python_scheduler_validation_pass`.

The final artifact exactly reconstructs P4J/P4K (`333/61/272`) and the locked
non-Python denominator (`272`). All scheduler arms executed and private arm
outcomes were written under `/tmp` only (`record_count=1088`). Public aggregate
metrics:

| Arm | Reach | Mean pool | Mean latency | Hard-cap violations |
|---|---:|---:|---:|---:|
| baseline current pool | 0/272 | 13.871324 | 2.059338s | 0 |
| P2 depth-only reference | 55/272 | 53.084559 | 1.863294s | 3 |
| P3 constrained reference | 55/272 | 31.058824 | 3.626279s | 0 |
| frozen P4 latency-aware scheduler | 52/272 | 30.194853 | 2.381607s | 0 |

P4 preserved `0.945455` of the P2 depth-only reach gain, improved reach by 52
over baseline, reduced latency versus P3 by `0.343237` (`p4_vs_p3_latency_ratio=0.656763`),
kept pool growth within cap (`2.176782`), and had zero P4-treatment hard-cap
violations. The 3 hard-cap violations on P2 are reference-arm diagnostics only.
`forbidden_scan.status=pass`.

## Caveats

- P4L is a scheduler-validation phase. It is not a benchmark/leaderboard,
  default-policy, method-winner, runtime-promotion, downstream-value, P5,
  BEA-v1-A, retrieval-expansion, selector/reranker, parameter-tuning,
  threshold-search, new-arms, or runtime/default-promotion authorization claim.
- The pass status means this P4L locked scheduler validation ran and passed its
  frozen gates on the 272-record non-Python denominator. It does NOT authorize
  P5, BEA-v1-A, runtime promotion, method-winner claims, broad retrieval
  expansion, selector/reranker execution, frozen P4 reruns, or any future
  locked-P4 promotion/default step.
- The frozen thresholds are from prior P4; no post-hoc tuning.
- Gold/private labels are used only for evaluation/scoring file-miss.
