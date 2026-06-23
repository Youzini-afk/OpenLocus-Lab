# BEA-FD2-A1: Direct FD1 Objective Failure Attribution Replay

Date: 2026-06-23 (BEA-FD2-A1 failure-mechanism attribution replay after the
BEA-FD2-A No-Go. It is NOT a new selector/acquisition phase, NOT FD2-B,
NOT P4/P5, and NOT v0.31/v0.32 tuning. It explains *why* direct
aggregate-FD1-loss weighting selected worse evidence sets on the same
bounded FD2-A frame.)

> `claim_level = bea_fd2a1_failure_attribution_replay_only`. All no-claim /
> no-runtime-change flags false. `role_proxy_used=false` and
> `target_support_proxy_used=false` inherited from FD2-A scanner discipline.
> `provider_calls_made=false` is binding.

## Binding context

- BEA-FD2-A result checkpoint: `df82ddb`; local checkpoint: `709b0cb`; CI
  run `28025382422`; status `no_go_no_fd1_loss_reduction`.
- FD2-A changed selection strongly but worsened composite FD1 loss and
  regressed file_recall/MRR versus both frozen v0.3 and coverage-only.
- FD2-A1 reruns FD2-A verbatim (unchanged policy / weights / thresholds /
  arms / budget / methods / frame) with a private trace directory under
  `/tmp`, parses FD2-A private traces, and attributes regressions into
  aggregate mechanism buckets only.

## Mechanism buckets (8)

FD2-A regressions are attributed into aggregate buckets only. A record may
fall into multiple buckets; counts are aggregate.

1. `gold_file_displacement` — v0.3 retained the gold file but FD2-A
   displaced it (actionable).
2. `correct_file_rank_worsened` — both arms retained the gold file but
   FD2-A spent the full budget with no MRR gain vs v0.3 (actionable).
3. `correct_file_span_worsened` — both arms retained the gold file but
   FD2-A lost the correct span (actionable).
4. `redundancy_overcorrection` — v0.3 retained duplicates, FD2-A
   suppressed them, but FD2-A still regressed (overcorrected dedup;
   actionable).
5. `latency_category_non_actionable_or_dominating` — FD2-A latency
   worsened, or the `latency_cost` objective component dominates
   (actionable).
6. `aggregate_weight_category_collision` — opposite movements across FD1
   binary categories (one improves while another worsens) → the frozen
   weights collide (actionable).
7. `candidate_availability_limit` — deduped candidate pool below
   `2*budget` (structural availability limit; No-Go dominating).
8. `diffuse_or_unclassified` — regressed but no actionable bucket matched,
   OR did not regress (no actionable mechanism to attribute; No-Go
   dominating catch-all).

## Data policy

- Rerun FD2-A deterministically with the same fixed 38-record frame and a
  private trace directory under `/tmp`. FD2-A policy / weights /
  thresholds / arms / budget / methods are UNCHANGED.
- Parse FD2-A private score (190), decision (190), FD1-objective feature
  (190), post-hoc decomposition (950), and objective config (1) traces.
- Read the committed FD2-A public artifact and committed FD1 aggregate
  artifact for replay-match context only (read-only; never modified).
- Do NOT tune weights, thresholds, or policy from FD2-A outcomes. Do NOT
  add new records, retrieval methods, arms, or heldout validation.

## Public artifact contract

Aggregate-only, records-only. No private record IDs, paths, queries,
snippets, spans, candidate keys, selected order, objective-config payload,
or private trace paths. Only counts, rates, hashes, schema names, and
aggregate metrics.

Required public tables (records-only, natural keys):

- `source_run_records`: `(source_phase, source_ci_run_id)` — replay-match
  context (expected vs replayed counts, committed status, source
  checkpoint/CI-run/schema/hash).
- `pairwise_outcome_delta_records`: `(baseline_arm, treatment_arm, metric)`
  — repackaged from the committed FD2-A public `arm_delta_records`.
- `mechanism_bucket_records`: `(mechanism_bucket,)` — per-bucket count,
  rate of attributed, rate of regressed, is_actionable,
  is_no_go_dominating.
- `component_delta_records`: `(component, baseline_arm, treatment_arm)`
  — repackaged from the committed FD2-A public `ablation_delta_records`.
- `counterfactual_availability_records`: `(counterfactual_bucket,)` —
  aggregate counts of records where better candidates existed in the pool
  or were selected by v0.3 / coverage.
- `category_collision_records`: `(collision_pair,)` — aggregate counts
  per FD1 category collision pair.
- `gate_records`: `(gate,)` — fail-closed gates.
- `private_manifest_records`: `(manifest_name,)` — path never serialized;
  counts/hashes/storage only.
- `failure_category_count_records`: `(failure_category,)`.
- `framing`, `forbidden_scan`.

## CI gates (fail-closed)

The manual CI workflow `bea-fd2a1-failure-attribution-replay.yml` runs
only on `workflow_dispatch` with `enable_external_benchmark_network=true`.
Real replay requires public network access AND the committed FD1 artifact
AND a built OpenLocus binary. No provider secrets/vars/model env. Private
JSONL/JSON files are NEVER uploaded.

Fail-closed validation (real run only):

- `records_attributed == 38`.
- Private trace counts exact: score 190, decision 190, FD1-objective
  feature 190, post-hoc decomposition 950, objective config 1.
- Private trace parse failures: zero.
- `forbidden_scan.status == pass`.
- `replay_protocol_match == true` (parsed counts match expected AND
  committed; committed status is No-Go; records_successful == 38).
- `provider_calls_made == false`.
- All 8 mechanism buckets present; sum of bucket assignments >=
  records_attributed (records can be in multiple buckets).
- Records-only public shape; natural-key uniqueness for every public
  record table.
- No forbidden top-level fields (private / per-record / claim / dynamic
  dict mirrors / self-test detail).

Allowed statuses (real run): `bea_fd2a1_attribution_replay_pass` |
`no_go_mechanism_diffuse` | `no_go_candidate_availability_limit`.
`unavailable_with_reason` is only valid for the default no-network artifact;
`no_go_replay_mismatch`, `fail_forbidden_scan`, and
`fail_schema_contract` are failure statuses, not CI-valid results.

## Statuses

- `bea_fd2a1_attribution_replay_pass` — replay matched; >=60% of
  regressing records fall into one or two actionable buckets; not
  candidate-availability-dominated; not diffuse-dominated.
- `no_go_mechanism_diffuse` — regressions are diffuse (actionable
  concentration < 0.60), OR no records regressed (nothing to attribute).
- `no_go_candidate_availability_limit` — candidate-availability bucket
  holds the plurality of regressing records.
- `no_go_replay_mismatch` — private trace counts / committed status /
  records_successful do not match the committed FD2-A outcome; this is not a
  CI-valid result.
- `unavailable_with_reason` — default no-network artifact (truthful;
  not a fake pass).
- `fail_forbidden_scan` / `fail_schema_contract` — schema/leak failure; not
  CI-valid results.

## Stop / go after FD2-A1

Go to design a new objective ONLY if:

- >=60% of FD2-A regressions fall into one or two actionable mechanism
  buckets, AND
- counterfactual aggregate tables show better candidates existed in the
  pool or were selected by v0.3 / coverage, AND
- the resulting correction is structural, not "try new weights."

No-Go if failures are diffuse, dominated by candidate availability, a
replay mismatch, or only fixable by post-hoc weight tweaking.

## Validation

```text
python3 -m py_compile eval/bea_fd2a1_failure_attribution_replay.py  => PASS
python3 eval/bea_fd2a1_failure_attribution_replay.py --self-test  => PASS (404/404 checks)
python3 eval/bea_fd2a1_failure_attribution_replay.py \
  --out artifacts/bea_fd2a1_failure_attribution/bea_fd2a1_failure_attribution_replay_report.json  => PASS
  (status: unavailable_with_reason, no-network artifact,
   provider_calls_made=false, forbidden_scan=pass,
   role_proxy_assigned=false, records_attributed=0,
   self_test_checks_total=404, self_test_checks_passed=404)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Caveats

- BEA-FD2-A1 is eval/diagnostic only. NOT benchmark/leaderboard/
  performance/method-winner/calibration/promotion/default/runtime/
  EvidenceCore/downstream-value claim.
- The default no-network artifact is honestly `unavailable_with_reason`
  with `provider_calls_made=false` and `records_attributed=0`; it is NOT
  a fake pass. The committed FD2-A public artifact is read for
  replay-match context (status / schema / hash only); no private traces
  are parsed in the default no-network path.
- A real replay requires public network + the committed FD1 artifact +
  a built OpenLocus binary; it reruns FD2-A verbatim under `/tmp` and
  parses the resulting private traces. Private traces are NEVER committed
  or uploaded.
- FD2-A policy / weights / thresholds are UNCHANGED in FD2-A1; the rerun
  reuses `bea_fd2a_direct_fd1_objective_setwise_smoke` verbatim.
- This is the same P1/P2/P3 success-quota frame with disclosed overlap;
  it is NOT fresh disjoint validation and NOT FD2-B.
