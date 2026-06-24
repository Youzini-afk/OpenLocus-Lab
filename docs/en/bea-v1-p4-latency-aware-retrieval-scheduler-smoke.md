# BEA-v1-P4: Latency-Aware Retrieval Action Scheduler Smoke

Date: 2026-06-24 (BEA-v1-P4 — fourth phase of BEA v1 Hierarchical
Actionable Evidence Acquisition. Run after the BEA-v1-P3 result
checkpoint `eda2087`. P3 ran a constrained retrieval policy smoke over
the FD1 `gold_file_absent` denominator (119 records) and produced a
strong retrieval-action mechanism signal but failed latency safety:
baseline reached 32/119; P2 depth-only reached 59/119 (+27); P3
constrained reached 58/119 (+26), pool 41.50 / 2.08× baseline, latency
3.645s / 2.17× baseline > 2.0 gate, efficiency 1.208122. P3 status is
`no_go_p3_cost_exceeded`. P4 isolates whether P3's latency failure came
from avoidable sequential / redundant retrieval actions and tests one
runtime-clean scheduler fix that reduces latency while preserving P3 /
P2 reach. It is NOT BEA v0.4 repair, NOT FD2-B / FD2-C, NOT legacy P4 /
P5, NOT v0.31 / v0.32 tuning, NOT B16-K, NOT a selector / acquisition
phase, NOT dense/graph/QuIVer quality mixing, NOT latency-in-relevance
scoring, and NOT a re-run of P1, P2, or P3.)

> `claim_level = bea_v1_p4_latency_aware_retrieval_scheduler_smoke_only`.
> All no-claim / no-runtime-change flags false. `provider_calls_made=false`
> is binding. `role_proxy_used=false`,
> `gold_labels_used_for_query_construction=false`,
> `gold_labels_used_for_policy=false`,
> `latency_in_candidate_relevance=false`, and
> `query_anchors_used_in_p4_arm=false` are binding.

## Binding context

- BEA-v1-P3 result checkpoint: `eda2087`; status
  `no_go_p3_cost_exceeded`. P3 preserved reach and pool efficiency but
  failed latency safety: baseline 32/119, P2 depth 59/119 (+27), P3
  constrained 58/119 (+26), pool 41.50 (2.08×), latency 3.645s (2.17× >
  2.0 gate), efficiency 1.208122, selector relevance remains (mean
  first-gold rank 25.69, 50 records above budget).
- BEA-v1-P2 result checkpoint: `930dd48`; status
  `no_go_retrieval_reach_latency_or_pool_cost`.
- BEA-v1-P1 result checkpoint: `d96e860`; status
  `no_go_retrieval_availability_limit`. `gold_file_absent`
  denominator=119, file-selector lower-bound recoverable count=1,
  retrieval availability rate=0.991597.
- P4 runs a deterministic, provider-free, network-enabled latency-aware
  retrieval-action scheduler over the FD1 `gold_file_absent`
  denominator (exactly 119 records). It tests whether a runtime-clean
  scheduler that selects extra-depth channel actions (instead of P3's
  full extra-depth round across all channels) can reduce latency while
  preserving P3 / P2 reach.

## Retrieval scheduler arms (4, fixed)

1. `current_bea_candidate_pool_replay` — current BEA runtime-clean
   retrieval pool (bm25/regex/symbol + derived RRF), depth=1. Anchors
   the v1-P1 / v1-P2 / v1-P3 baseline. Expected ~32/119.
2. `p2_depth_only_reference` — same P2 depth-only expansion (depth=4,
   same methods, no query anchors). Reference only. Expected ~59/119.
3. `p3_constrained_depth_policy_reference` — exact P3 policy, expected
   ~58/119, latency ~2.17×. Failure reference only.
4. `p4_latency_aware_action_scheduler` — main treatment, same retrieval
   methods, no query anchors, action scheduling only.

## P4 scheduler mechanism (runtime-clean retrieval-action scheduler)

The P4 arm is a **retrieval-action scheduler**, NOT candidate relevance
scoring. Latency is measured and used only to decide actions / stop and
for cost gates, never to rank candidates.

1. **Baseline round**: collect bm25 / literal-regex / symbol at depth=1
   **per-channel** (cached with timings); derive RRF from the method
   result lists. This caches baseline channel outputs so extra-depth
   does NOT rerun the same baseline work (P3 reran baseline work inside
   its extra round; P4 caches it).
2. **Runtime-clean per-channel diagnostics** (public signals only; no
   gold / private labels, no post-hoc tuning): non-empty channels,
   unique file count, duplicate-file rate, method agreement, per-channel
   new-file yield from baseline, score mass / spread, query-token /
   path-token overlap, per-channel elapsed time from current run.
3. **Extra-depth channel gating**: instead of P3's full extra-depth
   round across all channels, choose extra-depth actions per channel:
   - Run extra depth only for channels whose baseline result is sparse
     or high-yield-looking.
   - Skip channels that are empty / failing, saturated, duplicate-heavy,
     or already overlapped by another channel.
   - Stop when unique-file cap / candidate cap / action budget reached.
   - Cache / reuse baseline channel outputs so extra-depth does not
     rerun the same baseline work.
   - Keep one simple predeclared policy, no threshold search / matrix.
4. **No query anchors** in P4.
5. **Latency can be measured and used only to decide actions / stop and
   for cost gates, not to rank candidates.**

### Concrete P4 scheduler

- Collect baseline per-channel outputs with timings.
- Compute per-channel unique file contribution and overlap.
- Eligible extra-depth channels:
  - baseline channel non-empty, not failed;
  - channel unique file count below a cap (60) OR channel contributes
    at least a minimum unique-file share (≥10%) vs baseline;
  - skip channels with excessive duplicate rate (>0.70) or high overlap
    with already selected channels (≥0.85);
  - optionally prefer cheapest / high-yield channels from baseline
    diagnostics (action ordering, NOT candidate ranking by latency).
- Execute at most 1-2 extra-depth channel actions total (predeclared).
- Merge baseline + new unique-file candidates from chosen extra-depth
  channels, cap candidates ≤100 and unique files ≤80.

## Metrics (over the 119 denominator)

- `gold_file_available_any_pool` — gold file found in any arm's pool.
- `gold_file_available_at_50/100/200` — gold file found within rank
  50/100/200.
- `first_gold_file_rank_mean/median` — mean/median first gold-file rank.
- `candidate_pool_size_mean` — mean candidate pool size.
- `retrieval_latency_mean_seconds` — mean retrieval latency.
- `duplicate_file_rate` — duplicate-file rate.
- `newly_reachable_count` — records where gold became available in an
  arm but not in the baseline.
- `still_unavailable_count` — records where gold was not found in any
  arm.
- `pool_size_multiplier` / `latency_multiplier` — per-arm cost vs
  baseline.
- `hard_cap_violation_count` — P4 arm records exceeding the hard
  candidate cap.
- `newly_reachable_per_added_candidate` — scheduler efficiency.
- `p4_mean_extra_depth_actions` / `p3_mean_extra_depth_actions` —
  per-record action count comparison.
- `p4_extra_depth_latency_share` — share of total P4 latency spent in
  extra-depth actions.

## Research success gates

P4 passes only if ALL of the following hold:

1. **Reach preservation**: newly reachable ≥ 20/119 OR retains ≥ 75%
   of P2 depth-only newly reachable (≥ 21 of +27).
2. **Latency fix**: P4 latency multiplier ≤ 2.0× baseline AND P4 latency
   < P3 latency by at least 10% relative.
3. **Pool safety**: P4 pool multiplier ≤ 4.0× baseline; hard candidate
   cap violations = 0.
4. **Efficiency / action improvement**: newly reachable per added
   candidate ≥ 80% of P3 OR better than P2 combined; action count lower
   than P3 on a material share (≥ 25% fewer extra-depth channel actions
   OR ≥ 20 records with fewer actions).
5. **Selector relevance remains**: enough reachable gold files remain
   outside final budget (mean first-gold rank > 5 OR ≥ 25 records have
   first-gold rank > budget).

## No-Go statuses

- `no_go_p4_reach_not_preserved` — P4 did not preserve enough reach.
- `no_go_p4_latency_not_fixed` — latency safety still violated.
- `no_go_p4_cost_exceeded` — pool / hard-cap safety violated.
- `no_go_p4_policy_degenerate` — efficiency / action degenerate, no
  runtime-clean dominance, or no selector problem remains.
- `no_go_p4_replay_mismatch` — FD1 replay / denominator mismatch,
  baseline / depth / P3 reference reach drift, or retrieval scheduler
  not executed.

CI / schema / privacy failures (`fail_forbidden_scan`,
`fail_schema_contract`) fail CI and are NOT valid research statuses.

## Hard validity gates (fail-closed)

- FD1 replay validated 239 / 86040.
- Denominator exactly 119.
- Baseline reach reproduced within tolerance (expected 32, ±3).
- P2 depth-only reference reach reproduced within tolerance (expected
  59, ±3).
- P3 reference reach reproduced within tolerance (expected 58, ±3).
- P4 retrieval executed for all 119 records.
- Private policy rows = denominator × arms = 119 × 4 = 476.
- `forbidden_scan.status=pass`.
- No provider calls, no gold / private labels in scheduler / query
  construction, no selector / packer / default / runtime promotion, no
  role proxies, latency not in candidate relevance, query anchors not
  used in the P4 arm.

## Public artifact contract

Aggregate-only, records-only. No public record IDs, paths, queries,
snippets, gold files, candidate lists, per-record ranks, private trace
paths, or private row payloads.

Required public tables (records-only, natural keys):

- `source_run_records`: `(source_phase, source_ci_run_id)` — FD1 + P1
  + P2 + P3 binding context with replay-artifact validation fields and
  P4 scheduler config hash.
- `denominator_records`: `(source_phase, benchmark)`.
- `arm_reach_records`: `(arm_name,)` — per-arm aggregate reach metrics.
- `arm_delta_records`: `(arm_name,)` — per-arm delta vs baseline.
- `arm_cost_records`: `(arm_name, cost_axis)` — per-arm pool / latency
  multipliers + hard-cap violation count.
- `arm_action_records`: `(arm_name, scheduler_action)` — per-scheduler
  -action count (baseline_only / extra_depth_selected).
- `channel_action_records`: `(channel_name, channel_action)` —
  per-channel aggregate action count.
- `scheduler_stop_reason_records`: `(scheduler_stop_reason,)`.
- `latency_decomposition_records`: `(latency_axis,)` — baseline vs
  extra-depth latency decomposition.
- `efficiency_records`: `(efficiency_axis,)` — per-arm
  newly_reachable_per_added_candidate vs P3 / P2 combined / depth.
- `reach_bucket_records`: `(arm_name, reach_bucket)`.
- `rank_band_records`: `(arm_name, rank_band)`.
- `cost_safety_records`: `(cost_safety_axis,)` — max pool / latency
  multipliers across treatment arms (excludes P3 failure reference).
- `stop_go_records`: `(stop_go_decision,)` — P4 scheduler decision.
- `gate_records`: `(gate,)` — fail-closed gates.
- `private_manifest_records`: `(manifest_name,)` — FD1 private replay
  and BEA-v1-P4 private scheduler trace manifests; paths never
  serialized.
- `failure_category_count_records`: `(failure_category,)`.
- `framing`, `forbidden_scan`.

## CI gates (fail-closed)

The manual CI workflow `bea-v1-p4-latency-aware-retrieval-scheduler.yml`
runs only on `workflow_dispatch` with
`enable_external_benchmark_network=true`. It regenerates the FD1
private decomposition under `/tmp` (NOT `$RUNNER_TEMP`), validates the
replay report, reruns the P4 latency-aware retrieval scheduler smoke
(network + OpenLocus binary, no provider secrets), and uploads only the
aggregate report. Private JSONL/JSON files are NEVER uploaded.

Fail-closed validation:

- `status` is one of: `bea_v1_p4_latency_aware_retrieval_scheduler_pass`
  | `no_go_p4_reach_not_preserved` | `no_go_p4_latency_not_fixed` |
  `no_go_p4_cost_exceeded` | `no_go_p4_policy_degenerate`.
  `no_go_p4_replay_mismatch` is a replay/default failure status, not a
  CI-valid real-run result.
- FD1 replay matches 239 / 86040.
- Denominator exactly 119.
- `fd1_private_decomposition_parsed=true` and
  `replay_artifact_validated=true` for real-run statuses.
- `provider_calls_made=false`.
- `gold_labels_used_for_query_construction=false`.
- `gold_labels_used_for_policy=false`.
- `latency_in_candidate_relevance=false`.
- `query_anchors_used_in_p4_arm=false`.
- `forbidden_scan.status=pass`.
- Records-only public shape; natural-key uniqueness.
- No forbidden top-level fields (private / per-record / claim /
  dynamic-dict / self-test detail / forbidden-scope flags).

## Statuses

- `bea_v1_p4_latency_aware_retrieval_scheduler_pass` — reach preserved,
  latency fixed, cost safety ok, efficiency / action improvement,
  runtime-clean dominance, selector problem remains.
- `no_go_p4_reach_not_preserved` — P4 reach below preservation threshold.
- `no_go_p4_latency_not_fixed` — latency multiplier > 2.0× or latency
  not reduced ≥10% vs P3.
- `no_go_p4_cost_exceeded` — pool / hard-cap safety violated.
- `no_go_p4_policy_degenerate` — efficiency / action degenerate, no
  runtime-clean dominance, or no selector problem remains.
- `no_go_p4_replay_mismatch` — FD1 replay / denominator mismatch, reach
  drift, or retrieval scheduler not executed; not CI-valid when network
  is enabled.
- `unavailable_with_reason` — default no-network artifact.
- `fail_forbidden_scan` / `fail_schema_contract` — schema/leak failure.

## Manual CI result

(Full result writeback waits until CI. The default no-network artifact
is `unavailable_with_reason` with `stop_go_decision=no_go_p4_replay_mismatch`;
self-test passes with 378/378 checks.)

## Validation

```text
python3 -m py_compile eval/bea_v1_p4_latency_aware_retrieval_scheduler_smoke.py  => PASS
python3 eval/bea_v1_p4_latency_aware_retrieval_scheduler_smoke.py --self-test  => PASS (378/378 checks)
python3 eval/bea_v1_p4_latency_aware_retrieval_scheduler_smoke.py \
  --out artifacts/bea_v1_p4_latency_aware_retrieval_scheduler/bea_v1_p4_latency_aware_retrieval_scheduler_smoke_report.json  => PASS
  (default no-network status: unavailable_with_reason,
   stop_go_decision: no_go_p4_replay_mismatch,
   forbidden_scan=pass, denominator_count=0,
   provider_calls_made=false,
   latency_in_candidate_relevance=false,
   query_anchors_used_in_p4_arm=false,
   self_test_checks_total=375, self_test_checks_passed=375)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Caveats

- BEA-v1-P4 is eval/diagnostic only. NOT benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value claim.
- Gold/private labels are used ONLY for evaluation/scoring reach, never
  to construct queries/candidates/scheduler.
  `gold_labels_used_for_query_construction=false` and
  `gold_labels_used_for_policy=false` are binding.
- Latency is measured and used only to decide actions / stop and for
  cost gates, never as a candidate relevance signal.
  `latency_in_candidate_relevance=false` is binding.
- Query anchors are DISABLED in the P4 arm.
  `query_anchors_used_in_p4_arm=false` is binding.
- The P4 evaluator does NOT run retrieval/provider calls during default
  artifact generation. The CI workflow reruns the latency-aware
  retrieval scheduler via subprocess; the evaluator reads the results.
- Private per-record traces (scheduler diagnostics, per-channel actions
  / timings, stop reasons, per-arm candidate list/ranks, gold-file reach
  labels, latency/pool-size, config hash) are under `/tmp` only and
  NEVER uploaded.
- BEA-v1-P4 is NOT BEA v0.4 repair, NOT FD2-B, NOT FD2-C, NOT legacy
  P4, NOT P5, NOT v0.31/v0.32 tuning, NOT B16-K, NOT dense/graph/QuIVer
  quality mixing, NOT selector/packer runtime change, NOT
  latency-in-relevance scoring.
