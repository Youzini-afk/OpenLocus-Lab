# BEA-v1-P4H: Disjoint Scheduler Validation

Date: 2026-06-24. BEA-v1-P4H validates the frozen BEA-v1-P4 latency-aware
retrieval-action scheduler from checkpoint `f0e99ca` on a disjoint raw external
heldout file-miss denominator. It is an empirical validation and rank-budget
audit, not a control-plane change.

> `claim_level = bea_v1_p4h_disjoint_scheduler_validation_only`.
> `provider_calls_made=false`, `gold_labels_used_for_query_construction=false`,
> `gold_labels_used_for_policy=false`, `latency_in_candidate_relevance=false`,
> `query_anchors_used_in_p4_arm=false`, and `selector_or_reranker_changed=false`
> are binding.

## Binding context

- BEA-v1-P4 checkpoint: `f0e99ca`; status
  `bea_v1_p4_latency_aware_retrieval_scheduler_pass`.
- P4 observed baseline 32/119, P2 depth-only 59/119, P3 reference 58/119,
  P4 frozen scheduler 56/119; P4 pool 2.056350× baseline, latency 1.749695×,
  latency reduction vs P3 19.3806%, hard-cap violations 0.
- P4 selector relevance remained unresolved: mean first reachable gold rank
  25.625, 48 records above budget.
- P4H reuses the same frozen P4 retrieval-action scheduler. It does not tune
  thresholds, add query anchors, broaden retrieval, change selectors/rerankers,
  or use latency in candidate relevance scoring.

## Denominator construction

- The P4H denominator is **not** the FD1 `gold_file_absent` tail. The committed
  FD1 artifact has exactly 119 `gold_file_absent` records, so reusing records
  after the first 119 would produce an empty heldout denominator.
- P4H instead performs a full-frame raw external disjoint success-quota scan over
  the available Python frames:
  - ContextBench: `offset=0`, `limit=480`.
  - RepoQA: `offset=0`, `limit=240`.
- Known BEA-4/5/P1/P2/P3/P4 prior records are excluded using exact private FD1
  raw keys when available. If exact keys are unavailable, the public aggregate
  artifact discloses explicit benchmark/index exclusion windows (for example the
  older fixed BEA-2/3/4 windows) without publishing private row ids.
- The scan uses stable raw order after exclusions. For each raw row, P4H clones the repository,
  runs only `current_bea_candidate_pool_replay`, and selects the row for the
  denominator only when the baseline/current candidate pool misses the gold
  file (`gold_file_available=false`).
- The denominator is constructed before running P2/P3/P4 treatment arms. The
  baseline result from the scan is cached and reused as arm 1 for selected
  denominator records.
- Scanning stops after the target/minimum of 80 denominator records if possible;
  the 80-record gate is not lowered. If fewer than 80 are found after the raw
  windows, P4H fails closed with `no_go_p4h_insufficient_denominator`.
- The public artifact publishes only aggregate attempt/yield/exclusion counts
  by source, benchmark, and raw window. Private per-record keys, row indices,
  queries, repository URLs, gold paths, candidate paths, manifests, and traces
  are written under `/tmp` only.

## Retrieval scheduler arms (4, fixed)

1. `current_bea_candidate_pool_replay` — baseline current BEA candidate pool.
2. `p2_depth_only_reference` — P2 depth-only reference.
3. `p3_constrained_depth_policy_reference` — P3 constrained policy reference.
4. `p4_latency_aware_action_scheduler_frozen` — frozen P4 treatment scheduler.

The treatment name is intentionally distinct from P4 to make the heldout frozen
replication explicit.

## Hard validity gates

- FD1/private replay validates the same 239 / 86040 base behavior as P4 for
  provenance, but FD1 records are not reused as the P4H denominator.
- Raw external denominator scan is attempted, prior raw windows are excluded,
  and the heldout denominator has at least 80 file-miss records.
- Private scheduler rows equal `denominator_count × 4`.
- `forbidden_scan.status=pass`.
- No provider calls.
- No gold/private labels are used for query construction, scheduler policy, or
  candidate ranking.
- `latency_in_candidate_relevance=false`.
- The public artifact is aggregate-only and records-only: no per-record IDs,
  paths, queries, snippets, candidate lists, gold files, private trace paths, or
  private row payloads.

## Replication gates

P4H passes only if the frozen P4 scheduler satisfies all gates on the heldout
denominator:

1. **Reach preservation**: P4H newly reachable is at least 75% of P2 depth-only
   newly reachable, or reaches the denominator-scaled absolute minimum, and is
   at least 90% of P3 reference newly reachable unless P3 itself drifts/fails.
2. **Latency**: P4H latency multiplier is ≤ 2.0× baseline and at least 10%
   lower than P3 reference latency.
3. **Pool/cap**: P4H pool multiplier is ≤ 4.0× baseline and hard-cap
   violations are 0.
4. **Action reduction**: P4H has materially fewer retrieval actions than P3
   (≥25% fewer mean extra-depth actions or the denominator-scaled equivalent of
   at least 20 records with fewer actions).
5. **Subgroup guard**: for any source/benchmark subgroup with `n >= 20`, P4H
   preserves at least 50% of P2 depth gain and stays within latency/pool gates.

## Rank-budget audit

P4H also emits `rank_budget_audit_records` with:

- `rank_budget_bottleneck_confirmed`
- `selector_phase_justified`

The bottleneck is confirmed if mean first reachable gold rank is > 5 or the
denominator-scaled equivalent of at least 25 records remain above budget. This
audit does not fail the scheduler by itself; it only justifies a possible later
selector phase if P4H passes.

## Statuses

- `bea_v1_p4h_disjoint_scheduler_validation_pass`
- `no_go_p4h_insufficient_denominator`
- `no_go_p4h_replay_mismatch`
- `no_go_p4h_reach_not_replicated`
- `no_go_p4h_latency_not_fixed`
- `no_go_p4h_cost_exceeded`
- `no_go_p4h_policy_degenerate`
- `unavailable_with_reason`
- `fail_forbidden_scan` / `fail_schema_contract`

`fail_*` statuses are schema/privacy failures. In a network-enabled real run,
`no_go_p4h_replay_mismatch` is not CI-valid because it indicates replay/schema
or prerequisite mismatch.

## Public artifact contract

Required aggregate-only record tables:

- `source_run_records`
- `denominator_records`
- `denominator_scan_records`
- `prior_raw_exclusion_records`
- `arm_reach_records`
- `arm_delta_records`
- `arm_cost_records`
- `arm_action_records`
- `channel_action_records`
- `scheduler_stop_reason_records`
- `latency_decomposition_records`
- `efficiency_records`
- `reach_bucket_records`
- `rank_band_records`
- `cost_safety_records`
- `subgroup_safety_records`
- `rank_budget_audit_records`
- `stop_go_records`
- `gate_records`
- `private_manifest_records`
- `failure_category_count_records`
- `framing`
- `forbidden_scan`

No dynamic per-record detail, no public private hashes, and no private paths are
serialized.

## Workflow

The manual workflow `bea-v1-p4h-disjoint-scheduler-validation.yml` runs only via
`workflow_dispatch` and accepts `enable_external_benchmark_network`. It builds
the OpenLocus release CLI, runs self-tests, regenerates FD1 private
decomposition under `/tmp`, validates FD1 replay, runs the P4H raw external
disjoint scan plus scheduler validation, validates the report fail-closed,
uploads a prevalidation aggregate report if present, and uploads the final
aggregate report. Private JSONL/JSON traces are not uploaded.

## Local validation

```text
python3 -m py_compile eval/bea_v1_p4h_disjoint_scheduler_validation.py  => PASS
python3 eval/bea_v1_p4h_disjoint_scheduler_validation.py --self-test  => PASS (69/69 checks)
python3 eval/bea_v1_p4h_disjoint_scheduler_validation.py \
  --out artifacts/bea_v1_p4h_disjoint_scheduler_validation/bea_v1_p4h_disjoint_scheduler_validation_report.json  => PASS
  (default no-network status: unavailable_with_reason,
   stop_go_decision: no_go_p4h_replay_mismatch,
   forbidden_scan=pass, denominator_count=0,
   raw_denominator_scan_attempted=false,
   self_test_checks_total=69, self_test_checks_passed=69)
```

CI result is pending until the manual network workflow is run.

## Caveats

- P4H is validation/audit only. It is not a benchmark/leaderboard,
  default-policy, method-winner, runtime-promotion, downstream-value, or v1-A
  authorization claim.
- It does not implement selector/reranker changes.
- Gold/private labels are used only for evaluation/scoring reach.
- Latency remains a scheduling/cost signal only and is never used for candidate
  relevance.
