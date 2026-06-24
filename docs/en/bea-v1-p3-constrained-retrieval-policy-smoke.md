# BEA-v1-P3: Constrained Retrieval Policy Smoke

Date: 2026-06-24 (BEA-v1-P3 — third phase of BEA v1 Hierarchical
Actionable Evidence Acquisition. Run after the BEA-v1-P2 result
checkpoint `930dd48`. P2 ran a candidate-availability / retrieval-reach
smoke over the FD1 `gold_file_absent` denominator (119 records) and
found that runtime-clean retrieval expansion can recover additional
gold files, but naive broad expansion is too costly: baseline reached
32/119; depth-only reached 59/119 (+27, pool 3.41×, latency 1.18×);
query-anchor reached 60/119 (+28) but exceeded cost; combined
depth+query reached 81/119 (+49) but violated pool/latency safety
(10.13× pool, 3.89× latency). P2 status is
`no_go_retrieval_reach_latency_or_pool_cost`. P3 is the first real
retrieval-action policy in BEA v1, not a selector / default /
promotion. It is NOT BEA v0.4 repair, NOT FD2-B / FD2-C, NOT P4 / P5,
NOT v0.31 / v0.32 tuning, NOT B16-K, NOT a selector / acquisition
phase, NOT dense/graph/QuIVer quality mixing, NOT latency-in-relevance
scoring, and NOT a re-run of P1 or P2.)

> `claim_level = bea_v1_p3_constrained_retrieval_policy_smoke_only`.
> All no-claim / no-runtime-change flags false. `provider_calls_made=false`
> is binding. `role_proxy_used=false`,
> `gold_labels_used_for_query_construction=false`,
> `gold_labels_used_for_policy=false`,
> `latency_in_candidate_relevance=false`, and
> `query_anchors_used_in_p3_arm=false` are binding.

## Binding context

- BEA-v1-P2 result checkpoint: `930dd48`; status
  `no_go_retrieval_reach_latency_or_pool_cost`. P2 showed runtime-clean
  retrieval expansion can recover 27–49 additional gold files, but
  naive broad expansion is too costly (combined arm 10.13× pool, 3.89×
  latency).
- BEA-v1-P1 result checkpoint: `d96e860`; status
  `no_go_retrieval_availability_limit`. `gold_file_absent`
  denominator=119, file-selector lower-bound recoverable count=1,
  retrieval availability rate=0.991597.
- P3 runs a deterministic, provider-free, network-enabled constrained
  retrieval policy over the FD1 `gold_file_absent` denominator (exactly
  119 records). It tests whether a runtime-clean constrained retrieval
  scheduler can preserve most of the P2 depth-only reach (59/119)
  while bounding pool / latency.

## Retrieval policy arms (3)

1. `current_bea_candidate_pool_replay` — current BEA runtime-clean
   retrieval pool (bm25/regex/symbol + derived RRF), depth=1. Anchors
   the v1-P1 / v1-P2 baseline. Expected ~32/119.
2. `p2_depth_only_reference` — same P2 depth-only expansion (depth=4,
   same methods, no query anchors). Reference only. Expected ~59/119.
3. `p3_constrained_depth_policy` — main treatment. A runtime-clean
   constrained retrieval scheduler that starts from the baseline pool,
   computes only public diagnostics, applies at most one extra depth
   round under predeclared under-retrieval conditions, merges with a
   marginal new-file-yield filter, and stops on a hard candidate cap /
   unique-file cap / action budget.

## P3 policy mechanism (runtime-clean retrieval scheduler)

The P3 arm is a **retrieval-action policy**, NOT candidate relevance
scoring. Latency is measured and used only as a stop / safety metric,
never as a relevance signal.

1. **Baseline round**: collect bm25 / literal-regex / symbol candidates
   at depth=1, derive RRF from the method result lists, dedupe. This is
   the baseline pool (reuses P2's runtime-safe retrieval helpers).
2. **Runtime-clean diagnostics** (public signals only; no gold / private
   labels, no post-hoc tuning): unique file count, duplicate-file rate,
   method agreement count, non-empty channels, normalized score mass /
   spread, query-token / path-token overlap.
3. **Under-retrieval trigger**: apply ONE extra depth round (depth=4,
   no query anchors — query anchors are DISABLED in the main P3 arm)
   iff ANY predeclared condition holds:
   - unique file count < 15 (low unique file count),
   - duplicate-file rate > 0.50 (high duplicate-file rate),
   - non-empty channels ≤ 2 (too few non-empty channels),
   - normalized score mass < 5.0 (low score mass).
4. **Marginal new-file yield filter**: merge extra-round candidates
   whose file is NEW vs the baseline pool. Skip the merge entirely if
   the extra round yields < 2 new unique files (degenerate extra round).
5. **Stop conditions**: hard candidate cap (100 per record, ≤120),
   unique-file cap (80), action budget (≤1 extra-depth round), or
   marginal new-file yield below threshold.
6. **Gold-file reach** is computed on the final merged + deduped +
   capped pool. Gold paths are used ONLY to check reach, never to
   construct the pool or policy.

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
- `hard_cap_violation_count` — P3 arm records exceeding the hard
  candidate cap.
- `newly_reachable_per_added_candidate` — policy efficiency.

## Research success gates

P3 passes only if ALL of the following hold:

1. **Reach preservation**: newly reachable ≥ 20/119 OR retains ≥ 75%
   of P2 depth-only newly reachable (≥ 21 of +27).
2. **Cost safety**: mean pool multiplier ≤ 4.0× baseline; mean latency
   multiplier ≤ 2.0× baseline; hard cap violation count = 0.
3. **Policy efficiency**: `newly_reachable_per_added_candidate` better
   than P2 combined (0.268638) and not materially worse than P2
   depth-only (≥ 80% of 0.560077).
4. **Selector relevance remains**: enough reachable gold files remain
   outside final budget (mean first-gold rank > 5 OR ≥ 25 records have
   first-gold rank > budget).

## No-Go statuses

- `no_go_p3_reach_not_preserved` — P3 did not preserve enough of the
  P2 depth-only reach.
- `no_go_p3_cost_exceeded` — pool / latency / hard-cap safety violated.
- `no_go_p3_policy_degenerate` — policy efficiency degenerate, no
  runtime-clean dominance, or no selector problem remains.
- `no_go_p3_replay_mismatch` — FD1 replay / denominator mismatch,
  baseline / depth-reference reach drift, or retrieval policy not
  executed.

CI / schema / privacy failures (`fail_forbidden_scan`,
`fail_schema_contract`) fail CI and are NOT valid research statuses.

## Hard validity gates (fail-closed)

- FD1 replay validated 239 / 86040.
- Denominator exactly 119.
- Baseline reach reproduced within tolerance (expected 32, ±3).
- P2 depth-only reference reach reproduced within tolerance (expected
  59, ±3).
- P3 retrieval executed for all 119 records.
- Private reach rows = denominator × arms = 119 × 3 = 357.
- `forbidden_scan.status=pass`.
- No provider calls, no gold / private labels in policy / query
  construction, no selector / packer / default / runtime promotion, no
  role proxies, latency not in candidate relevance, query anchors not
  used in the P3 arm.

## Public artifact contract

Aggregate-only, records-only. No public record IDs, paths, queries,
snippets, gold files, candidate lists, per-record ranks, private trace
paths, or private row payloads.

Required public tables (records-only, natural keys):

- `source_run_records`: `(source_phase, source_ci_run_id)` — FD1 + P1
  + P2 binding context with replay-artifact validation fields and P3
  policy config hash.
- `denominator_records`: `(source_phase, benchmark)` — per-(sp, bm)
  denominator count.
- `arm_reach_records`: `(arm_name,)` — per-arm aggregate reach metrics.
- `arm_delta_records`: `(arm_name,)` — per-arm delta vs baseline.
- `arm_cost_records`: `(arm_name, cost_axis)` — per-arm pool / latency
  multipliers + hard-cap violation count.
- `policy_action_records`: `(policy_action,)` — per-policy-action count
  (baseline_only / extra_depth_triggered /
  extra_depth_skipped_low_yield).
- `policy_stop_reason_records`: `(stop_reason,)` — per-stop-reason count.
- `efficiency_records`: `(efficiency_axis,)` — per-arm
  newly_reachable_per_added_candidate vs P2 combined / depth.
- `reach_bucket_records`: `(arm_name, reach_bucket)`.
- `rank_band_records`: `(arm_name, rank_band)`.
- `cost_safety_records`: `(cost_safety_axis,)` — max pool / latency
  multipliers across arms.
- `stop_go_records`: `(stop_go_decision,)` — P3 policy decision.
- `gate_records`: `(gate,)` — fail-closed gates.
- `private_manifest_records`: `(manifest_name,)` — FD1 private replay
  and BEA-v1-P3 private policy trace manifests; paths never serialized.
- `failure_category_count_records`: `(failure_category,)`.
- `framing`, `forbidden_scan`.

## CI gates (fail-closed)

The manual CI workflow `bea-v1-p3-constrained-retrieval-policy.yml`
runs only on `workflow_dispatch` with
`enable_external_benchmark_network=true`. It regenerates the FD1
private decomposition under `/tmp` (NOT `$RUNNER_TEMP`), validates the
replay report, reruns the P3 constrained retrieval policy smoke
(network + OpenLocus binary, no provider secrets), and uploads only the
aggregate report. Private JSONL/JSON files are NEVER uploaded.

Fail-closed validation:

- `status` is one of: `bea_v1_p3_constrained_retrieval_policy_pass` |
  `no_go_p3_reach_not_preserved` | `no_go_p3_cost_exceeded` |
  `no_go_p3_policy_degenerate`. `no_go_p3_replay_mismatch` is a
  replay/default failure status, not a CI-valid real-run result.
- FD1 replay matches 239 / 86040.
- Denominator exactly 119.
- `fd1_private_decomposition_parsed=true` and
  `replay_artifact_validated=true` for real-run statuses.
- `provider_calls_made=false`.
- `gold_labels_used_for_query_construction=false`.
- `gold_labels_used_for_policy=false`.
- `latency_in_candidate_relevance=false`.
- `query_anchors_used_in_p3_arm=false`.
- `forbidden_scan.status=pass`.
- Records-only public shape; natural-key uniqueness.
- No forbidden top-level fields (private / per-record / claim /
  dynamic-dict / self-test detail / forbidden-scope flags).

## Statuses

- `bea_v1_p3_constrained_retrieval_policy_pass` — reach preserved, cost
  safety ok, policy efficiency better than combined and not materially
  worse than depth, runtime-clean dominance, selector problem remains.
- `no_go_p3_reach_not_preserved` — P3 reach below preservation threshold.
- `no_go_p3_cost_exceeded` — pool / latency / hard-cap safety violated.
- `no_go_p3_policy_degenerate` — efficiency degenerate, no runtime-clean
  dominance, or no selector problem remains.
- `no_go_p3_replay_mismatch` — FD1 replay / denominator mismatch, reach
  drift, or retrieval policy not executed; not CI-valid when network is
  enabled.
- `unavailable_with_reason` — default no-network artifact.
- `fail_forbidden_scan` / `fail_schema_contract` — schema/leak failure.


## Manual CI result

Manual CI run `28102428194` completed green in 1h22m03s. The workflow
regenerated FD1 private decomposition under `/tmp`, validated the replay,
ran all 3 P3 arms over the 119-record `gold_file_absent` denominator,
wrote 357 private policy rows, and uploaded only the aggregate public
artifact.

Public status is `no_go_p3_cost_exceeded`, not pass. The constrained
policy produced a strong retrieval-action mechanism signal but missed the
predeclared latency safety gate:

- baseline current pool: 32/119 files available, mean pool 19.98, mean
  latency 1.677s;
- P2 depth-only reference: 59/119 available, +27 newly reachable, mean
  pool 68.18 (3.41×), mean latency 1.991s (1.19×);
- P3 constrained depth policy: 58/119 available, +26 newly reachable,
  availability lift 0.218487, mean pool 41.50 (2.08×), mean latency
  3.645s (2.17×).

P3 retained 26/27 of the P2 depth-only newly reachable files and cut mean
pool size from 68.18 to 41.50 while improving newly-reachable-per-added
candidate efficiency to 1.208122 (above both P2 depth-only and combined).
It also preserved the downstream selector problem: mean first-gold rank
25.69, with 50 records above the budget. However, mean latency was
2.17× baseline, above the 2.0× gate, so the phase is a bounded No-Go on
cost safety.

Decision: the constrained retrieval-action policy idea is not rejected on
reach or pool efficiency, but this exact scheduler cannot be promoted to
v1-A input because latency safety failed. The next BEA v1 step, if any,
should isolate why latency rose despite fewer candidates (sequential
extra-depth scheduling / repeated channel calls) and test a latency-aware
action scheduler at the retrieval-action layer, still without putting
latency into candidate relevance scoring.

## Validation

```text
python3 -m py_compile eval/bea_v1_p3_constrained_retrieval_policy_smoke.py  => PASS
python3 eval/bea_v1_p3_constrained_retrieval_policy_smoke.py --self-test  => PASS (365/365 checks)
python3 eval/bea_v1_p3_constrained_retrieval_policy_smoke.py \
  --out artifacts/bea_v1_p3_constrained_retrieval_policy/bea_v1_p3_constrained_retrieval_policy_smoke_report.json  => PASS
  (default no-network status: unavailable_with_reason,
   stop_go_decision: no_go_p3_replay_mismatch,
   forbidden_scan=pass, denominator_count=0,
   provider_calls_made=false,
   latency_in_candidate_relevance=false,
   query_anchors_used_in_p3_arm=false,
   self_test_checks_total=365, self_test_checks_passed=365)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Caveats

- BEA-v1-P3 is eval/diagnostic only. NOT benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value claim.
- Gold/private labels are used ONLY for evaluation/scoring reach, never
  to construct queries/candidates/policy.
  `gold_labels_used_for_query_construction=false` and
  `gold_labels_used_for_policy=false` are binding.
- Latency is measured and used only as a stop / safety metric, never as
  a candidate relevance signal. `latency_in_candidate_relevance=false`
  is binding.
- Query anchors are DISABLED in the main P3 arm.
  `query_anchors_used_in_p3_arm=false` is binding.
- The P3 evaluator does NOT run retrieval/provider calls during default
  artifact generation. The CI workflow reruns the constrained retrieval
  policy via subprocess; the evaluator reads the results.
- Private per-record traces (policy diagnostics, actions taken, stop
  reasons, per-arm candidate list/ranks, gold-file reach labels,
  latency/pool-size, config hash) are under `/tmp` only and NEVER
  uploaded.
- BEA-v1-P3 is NOT BEA v0.4 repair, NOT FD2-B, NOT FD2-C, NOT P4,
  NOT P5, NOT v0.31/v0.32 tuning, NOT B16-K, NOT dense/graph/QuIVer
  quality mixing, NOT a selector/packer runtime change, NOT
  latency-in-relevance scoring.
