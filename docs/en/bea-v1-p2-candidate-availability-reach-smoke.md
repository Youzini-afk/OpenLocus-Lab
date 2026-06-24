# BEA-v1-P2: Candidate Availability / Retrieval Reach Smoke

Date: 2026-06-23 (BEA-v1-P2 — second phase of BEA v1 Hierarchical
Actionable Evidence Acquisition. Run after the BEA-v1-P1 result
checkpoint `d96e860`. P1 parsed the validated FD1 private replay
(86040 rows / 239 groups) and rejected selector-only BEA-v1-A:
`gold_file_absent` denominator=119, file-selector lower-bound
recoverable count=1, retrieval availability rate=0.991597. A selector
cannot recover absent gold files. P2 tests candidate availability /
retrieval reach, not selection. It is NOT BEA v0.4 repair, NOT FD2-B /
FD2-C, NOT P4 / P5, NOT v0.31 / v0.32 tuning, NOT B16-K, NOT a selector
/ acquisition phase, NOT dense/graph/QuIVer quality mixing, and NOT a
re-run of P1.)

> `claim_level = bea_v1_p2_candidate_availability_reach_smoke_only`.
> All no-claim / no-runtime-change flags false. `provider_calls_made=false`
> is binding. `role_proxy_used=false` and `gold_labels_used_for_query_construction=false`
> are binding.

## Binding context

- BEA-v1-P1 result checkpoint: `d96e860`; status
  `no_go_retrieval_availability_limit`. P1 parsed the validated FD1
  private replay (86040 rows / 239 groups) and found
  `gold_file_absent` denominator=119, file-selector lower-bound
  recoverable count=1, retrieval availability rate=0.991597.
- P2 runs a deterministic, provider-free, network-enabled retrieval
  reach smoke over the FD1 `gold_file_absent` denominator (exactly
  119 records). It compares the current BEA candidate pool with small
  runtime-clean expansion arms to determine whether gold files become
  available before selector work.

## Retrieval reach arms (4)

1. `current_bea_candidate_pool_replay` — current BEA runtime-clean
   retrieval pool (bm25/regex/symbol + RRF/derived RRF). Anchors the
   v1-P1 baseline.
2. `expanded_pool_more_depth_same_methods` — same methods, larger
   candidate generation depth before packing (4x). Tests truncation
   vs true retrieval miss.
3. `expanded_pool_query_anchor_variants` — runtime-clean query
   variants from public task text only (identifier tokens, path-like
   tokens, symbol-like tokens, import/package tokens, camel/snake
   splits). No gold paths, private labels, role/support proxy, or
   post-hoc tuning.
4. `expanded_pool_depth_plus_query_anchor` — depth expansion + query-
   anchor variants together (combined arm).

## Metrics (over the 119 denominator)

- `gold_file_available_any_pool` — gold file found in any arm's pool.
- `gold_file_available_at_50/100/200` — gold file found within rank
  50/100/200.
- `first_gold_file_rank_mean/median` — mean/median first gold-file rank.
- `candidate_pool_size_mean` — mean candidate pool size.
- `retrieval_latency_mean_seconds` — mean retrieval latency.
- `duplicate_file_rate` — duplicate-file rate.
- `newly_reachable_count` — records where gold became available in an
  expanded arm but not in the baseline.
- `still_unavailable_count` — records where gold was not found in any arm.

## Stop / go back to v1-A

Reopen BEA-v1-A only if ALL of the following hold:

1. Newly reachable gold files on the 119 denominator are material:
   `newly_available_count >= 25` OR `availability_lift >= 0.20`, where
   `availability_lift = newly_reachable_count / 119` (not divided by the
   tiny baseline-available count).
2. Lift does not require pool/latency explosion: pool size <= 4x
   baseline and latency <= 2x baseline.
3. At least one runtime-clean mechanism dominates (depth, query, or
   combined arm has `newly_reachable > 0`).
4. No gold/private labels used at runtime (binding flag
   `gold_labels_used_for_query_construction=false`).
5. Expanded pool leaves a selector/packer problem: gold reachable but
   often below final budget (proxied by `first_gold_file_rank_mean >
   budget`).

Otherwise No-Go and pivot to retrieval-layer design or trace
collection for span/stopping ceilings.

## Public artifact contract

Aggregate-only, records-only. No public record IDs, paths, queries,
snippets, gold files, candidate lists, per-record ranks, private trace
paths, or private row payloads.

Required public tables (records-only, natural keys):

- `source_run_records`: `(source_phase, source_ci_run_id)` — FD1 + P1
  binding context with replay-artifact validation fields.
- `denominator_records`: `(source_phase, benchmark)` — per-(sp, bm)
  denominator count.
- `arm_reach_records`: `(arm_name,)` — per-arm aggregate reach metrics.
- `arm_delta_records`: `(arm_name,)` — per-arm delta vs baseline.
- `reach_bucket_records`: `(arm_name, reach_bucket)` — per-(arm, bucket)
  count.
- `rank_band_records`: `(arm_name, rank_band)` — per-(arm, band) count.
- `cost_safety_records`: `(cost_safety_axis,)` — pool/latency multiplier
  safety checks.
- `stop_go_records`: `(stop_go_decision,)` — v1-A reopen decision.
- `gate_records`: `(gate,)` — fail-closed gates.
- `private_manifest_records`: `(manifest_name,)` — FD1 private replay and
  BEA-v1-P2 private reach trace manifests; paths never serialized.
- `failure_category_count_records`: `(failure_category,)`.
- `framing`, `forbidden_scan`.

## CI gates (fail-closed)

The manual CI workflow `bea-v1-p2-candidate-availability-reach.yml` runs
only on `workflow_dispatch` with `enable_external_benchmark_network=true`.
It regenerates the FD1 private decomposition, validates the replay
report, reruns the P2 retrieval smoke (network + OpenLocus binary, no
provider secrets), and uploads only the aggregate report. Private
JSONL/JSON files are NEVER uploaded.

Fail-closed validation:

- `status` is one of: `bea_v1_p2_retrieval_reach_pass` |
  `no_go_retrieval_reach_insufficient` |
  `no_go_retrieval_reach_latency_or_pool_cost` |
  `no_go_replay_mismatch`.
- FD1 replay matches 239 / 86040.
- Denominator exactly 119.
- `fd1_private_decomposition_parsed=true` and
  `replay_artifact_validated=true` for real-run statuses.
- `provider_calls_made=false`.
- `gold_labels_used_for_query_construction=false`.
- `forbidden_scan.status=pass`.
- Records-only public shape; natural-key uniqueness.
- No forbidden top-level fields (private / per-record / claim /
  dynamic-dict / self-test detail / forbidden-scope flags).

## Statuses

- `bea_v1_p2_retrieval_reach_pass` — newly available material, cost
  safety ok, runtime-clean mechanism dominates, selector problem
  remains.
- `no_go_retrieval_reach_insufficient` — newly available below
  threshold or no runtime-clean mechanism dominates.
- `no_go_retrieval_reach_latency_or_pool_cost` — pool or latency
  multiplier exceeded.
- `no_go_replay_mismatch` — FD1 replay/denominator mismatch or
  retrieval reach not executed.
- `unavailable_with_reason` — default no-network artifact.
- `fail_forbidden_scan` / `fail_schema_contract` — schema/leak failure.

## Validation

```text
python3 -m py_compile eval/bea_v1_p2_candidate_availability_reach_smoke.py  => PASS
python3 eval/bea_v1_p2_candidate_availability_reach_smoke.py --self-test  => PASS (274/274 checks)
python3 eval/bea_v1_p2_candidate_availability_reach_smoke.py \
  --out artifacts/bea_v1_p2_candidate_availability_reach/bea_v1_p2_candidate_availability_reach_smoke_report.json  => PASS
  (default no-network status: unavailable_with_reason,
   stop_go_decision: no_go_replay_mismatch,
   forbidden_scan=pass, denominator_count=0,
   provider_calls_made=false,
   self_test_checks_total=274, self_test_checks_passed=274)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Manual CI result

CI pending — the manual CI workflow must be triggered with
`enable_external_benchmark_network=true` to regenerate the FD1 private
decomposition, validate the replay report, and rerun the P2 retrieval
reach smoke. Until then, the committed artifact remains the honest
`unavailable_with_reason` default.

## Caveats

- BEA-v1-P2 is eval/diagnostic only. NOT benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value claim.
- Gold/private labels are used ONLY for evaluation/scoring reach,
  never to construct queries/candidates.
  `gold_labels_used_for_query_construction=false` is binding.
- The P2 evaluator does NOT run retrieval/provider calls during
  default artifact generation. The CI workflow reruns the retrieval
  smoke via subprocess; the evaluator reads the results.
- Private per-record traces (query variants, candidate lists, gold-file
  match labels, reach buckets, latency/pool-size) are under `/tmp`
  only and NEVER uploaded.
- BEA-v1-P2 is NOT BEA v0.4 repair, NOT FD2-B, NOT FD2-C, NOT P4,
  NOT P5, NOT v0.31/v0.32 tuning, NOT B16-K, NOT dense/graph/QuIVer
  quality mixing, NOT a selector/packer runtime change.
