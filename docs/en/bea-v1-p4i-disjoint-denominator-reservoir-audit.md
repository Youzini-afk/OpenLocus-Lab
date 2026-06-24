# BEA-v1-P4I: Disjoint Denominator Reservoir Audit

Date: 2026-06-24. BEA-v1-P4I is a bounded **denominator/source audit**
performed after the BEA-v1-P4H No-Go. It does **not** run P2/P3/P4 scheduler
arms, does **not** validate a scheduler, does **not** expand retrieval, does
**not** execute a selector/reranker, and does **not** authorize P5 or
BEA-v1-A. The only diagnostic arm is `current_bea_candidate_pool_replay`.

> `claim_level = bea_v1_p4i_disjoint_denominator_reservoir_audit_only`.
> `provider_calls_made=false`, `gold_labels_used_for_query_construction=false`,
> `gold_labels_used_for_policy=false`, `latency_in_candidate_relevance=false`,
> `query_anchors_used_in_p4_arm=false`, `selector_or_reranker_changed=false`,
> `selector_or_reranker_executed=false`,
> `p2_depth_only_reference_executed=false`,
> `p3_constrained_depth_policy_reference_executed=false`,
> `p4_latency_aware_action_scheduler_executed=false`, `p5_authorized=false`,
> `v1_a_authorized=false`, and `frozen_p4h_rerun_authorized=false` (default)
> are binding.

## Motivation (P4H No-Go)

- P4H result checkpoint `9305701`; CI run `28132121958` (green, but a valid
  No-Go); full-frame scan fix `0dfeb27`; local checkpoint `dee1ce1`.
- P4H status `no_go_p4h_insufficient_denominator`: the full-frame disjoint
  scan found only **73/80** heldout baseline file-miss records (61
  ContextBench, 12 RepoQA). The P2/P3/P4 scheduler arms were not executed
  because the hard denominator gate of 80 was not lowered.
- P4H exhausted the available supported Python frames: 266 ContextBench rows
  fetched (of limit 480) and 100 RepoQA rows fetched (of limit 240), with 239
  prior exact raw keys excluded (162 ContextBench + 77 RepoQA).
- P4H does **not** authorize P5 / BEA-v1-A.

P4I answers the open question left by P4H: is the 73/80 blocker just the
current ContextBench/RepoQA Python-frame denominator being exhausted, or is
disjoint file-miss denominator scarcity structural?

## Scope (binding)

- P4I is a **denominator/source audit only**. It is NOT P5, NOT BEA-v1-A, NOT
  scheduler validation, NOT retrieval expansion, NOT selector/reranker, NOT
  broad retrieval.
- It scans only already-supported external benchmark raw frames/adapters that
  can be evaluated with the existing `current_bea_candidate_pool_replay`
  diagnostic arm: ContextBench (`offset=0`, `limit=480`) and RepoQA
  (`offset=0`, `limit=240`).
- A candidate denominator record is a baseline/current candidate pool **miss**
  of the gold file (`gold_file_available=false`). The only diagnostic arm is
  `current_bea_candidate_pool_replay`. P2/P3/P4 scheduler arms are NOT run.
- The scan does **not** stop at an 80-record target; it counts the full
  FD1-excluded upper-bound file-miss reservoir and separately reports whether
  that reservoir is qualified as all-prior-disjoint.

## Denominator construction

- The P4I reservoir is **not** the FD1 `gold_file_absent` tail and does not
  reuse the prior P1/P2/P3/P4 FD1 denominator.
- P4I performs a full-frame raw external disjoint file-miss reservoir quota
  scan over the supported Python frames:
  - ContextBench: `offset=0`, `limit=480`.
  - RepoQA: `offset=0`, `limit=240`.
- Exact prior raw-key exclusion is used **where available**. From the FD1
  private decomposition, only **BEA-4 and BEA-5** exact raw keys are available
  (`exact_prior_exclusion_scope =
  fd1_private_exact_bea4_bea5_raw_keys_only`). This is disclosed as the
  exact-exclusion scope; exact keys are NOT faked for other prior phases.
- For P1/P2/P3/P4 the FD1 BEA-4/BEA-5 exact superset already covers their
  shared 119-record denominator, so only an aggregate disclosure
  (`covered_by_fd1_bea4_bea5_exact_superset`) is emitted.
- For P4H the exact 73 selected raw keys are private (`/tmp` only, never
  committed, not in FD1), so only an aggregate disclosure
  (`p4h_exact_keys_private_tmp_only_aggregate_disclosure`) is emitted and exact
  keys are NOT faked. The reservoir is therefore reported as an FD1-excluded
  upper-bound file-miss pool which may overlap with P4H's heldout selection.
- The scan uses stable raw order after exclusions. For each raw row, P4I clones
  the repository, runs only `current_bea_candidate_pool_replay`, and selects
  the row for the reservoir only when the baseline/current candidate pool
  misses the gold file.
- The reservoir is constructed before any future scheduler outcomes. There
  are no treatment arms.
- The public artifact publishes only aggregate attempt/yield/exclusion counts
  by source, benchmark, and raw window, plus subgroup counts and the
  cumulative reservoir count. Private per-record keys, row indices, queries,
  repository URLs, gold paths, candidate paths, manifests, and traces are
  written under `/tmp` only.

## Hard validity gates

- `reservoir_upper_bound_count >= 80` for reservoir availability evidence.
- `qualified_denominator_reservoir_count >= 80` and `p4h_overlap_resolved=true`
  for `reservoir_ready_for_frozen_p4h_rerun`.
- Exact prior exclusion used where available; no private raw keys/ids
  serialized.
- The denominator/reservoir is constructed before any future scheduler
  outcomes (there are no treatment arms).
- Aggregate-only, records-only public artifact: no dynamic dicts for public
  metrics (only `framing` and `forbidden_scan` are fixed-schema dicts;
  `forbidden_scan.violation_categories` is a list).
- `forbidden_scan.status=pass`.
- No provider calls.
- No retrieval policy change, no selector/reranker execution, no
  latency-in-relevance, no P2/P3/P4 scheduler arms.
- Blocking failures (scan failed, scan not attempted, clone failed,
  unexpected exception) cannot be reported as an insufficient denominator;
  they yield `fail_schema_contract` (fail-closed).

## Statuses

- `reservoir_ready_for_frozen_p4h_rerun` — qualified disjoint file-miss
  reservoir reaches `>= 80`. This authorizes **only** a frozen P4H scheduler
  validation rerun on a locked denominator. It does **not** authorize P5,
  BEA-v1-A, runtime promotion, method-winner claims, broad retrieval
  expansion, or selector/reranker execution. `frozen_p4h_rerun_authorized=true`
  is expressed only inside `stop_go_records`; the top-level guard field remains
  false. `p5_authorized=false`, `v1_a_authorized=false`, etc.
- `no_go_disjoint_denominator_reservoir_insufficient` — still `< 80` after
  scanning the supported frames. This confirms FD1-excluded file-miss denominator
  scarcity is structural for the currently supported frames.
- `no_go_disjoint_denominator_reservoir_unqualified` — the FD1-excluded
  upper-bound reservoir reaches `>=80`, but P4H exact raw keys are unavailable,
  so overlap with P4H's 73 heldout records is unresolved. This does not
  authorize a frozen P4H rerun.
- `unavailable_with_reason` — default no-network artifact (honest, not a
  pass).
- `fail_schema_contract` / `fail_forbidden_scan` — privacy/schema/provenance
  failures. No `fail_*` status is CI-valid for a network-enabled real run.

The network workflow validator fails-closed for privacy/schema failures and
accepts only `reservoir_ready_for_frozen_p4h_rerun`,
`no_go_disjoint_denominator_reservoir_insufficient`, or
`no_go_disjoint_denominator_reservoir_unqualified` as valid research outcomes
(plus `unavailable_with_reason` only in the no-network default path).

## Stop rules (exact)

1. If the reservoir scan was not attempted (network disabled, prerequisites
   missing), the default artifact is `unavailable_with_reason` (no-network
   path only). The scan is never faked.
2. If a blocking failure occurs during the scan (raw fetch failed, clone
   failed, unexpected exception, FD1 replay/schema mismatch), the status is
   `fail_schema_contract` (fail-closed). Blocking failures are never reported
   as `no_go_disjoint_denominator_reservoir_insufficient`.
3. If the scan completes and the cumulative upper-bound file-miss reservoir is
  `< 80`, the status is `no_go_disjoint_denominator_reservoir_insufficient`.
   The hard gate of 80 is not lowered.
4. If the scan completes and the cumulative upper-bound file-miss reservoir is
   `>= 80` but P4H exact-key overlap is unresolved, the status is
   `no_go_disjoint_denominator_reservoir_unqualified`. This does not authorize
   any scheduler rerun.
5. If the scan completes and a qualified all-prior-disjoint file-miss reservoir
   is `>= 80`, the status is `reservoir_ready_for_frozen_p4h_rerun`. This
   authorizes only a frozen P4H scheduler validation rerun on the locked
   denominator; it does not authorize P5 / BEA-v1-A / runtime promotion /
   method winner / broad retrieval expansion.
6. `reservoir_ready_for_frozen_p4h_rerun` does not itself run a scheduler,
   select a method, or change any default. A subsequent frozen P4H rerun is a
   separate, explicitly authorized step that must lock the denominator and
   resolve any P4H overlap using P4H exact keys at rerun time.

## Public artifact contract

Required aggregate-only record tables (records-only; no dynamic dicts):

- `source_run_records`
- `denominator_reservoir_records`
- `denominator_scan_records`
- `prior_raw_exclusion_records`
- `subgroup_reservoir_records`
- `stop_go_records`
- `gate_records`
- `private_manifest_records`
- `failure_category_count_records`
- `framing`
- `forbidden_scan`

No dynamic per-record detail, no private raw keys/ids/paths, and no private
trace paths are serialized. The `manifest_hash` in `private_manifest_records`
is a provenance-only file-level integrity hash and does not expose row ids,
raw keys, paths, queries, candidate lists, or trace locations. No row/key/path
hashes are serialized.

## Workflow

The manual workflow `bea-v1-p4i-disjoint-denominator-reservoir-audit.yml`
runs only via `workflow_dispatch` and accepts
`enable_external_benchmark_network`. It builds the OpenLocus release CLI,
runs self-tests, regenerates FD1 private decomposition under `/tmp`, validates
FD1 replay, runs the P4I raw external disjoint file-miss reservoir scan,
validates the report fail-closed, and uploads the aggregate report. Private
JSONL/JSON traces are not uploaded. The workflow uses no model/provider
secrets.

## Local validation

```text
python3 -m py_compile eval/bea_v1_p4i_disjoint_denominator_reservoir_audit.py  => PASS
python3 eval/bea_v1_p4i_disjoint_denominator_reservoir_audit.py --self-test  => PASS (88/88 checks)
python3 eval/bea_v1_p4i_disjoint_denominator_reservoir_audit.py \
  --out artifacts/bea_v1_p4i_disjoint_denominator_reservoir_audit/bea_v1_p4i_disjoint_denominator_reservoir_audit_report.json  => PASS
  (default no-network status: unavailable_with_reason,
   forbidden_scan=pass, denominator_count=0,
   raw_denominator_scan_attempted=false,
   self_test_checks_total=88, self_test_checks_passed=88)
```

## Caveats

- P4I is a denominator/source audit only. It is not a benchmark/leaderboard,
  default-policy, method-winner, runtime-promotion, downstream-value, P5,
  BEA-v1-A, scheduler-validation, retrieval-expansion, or selector/reranker
  authorization claim.
- The exact-exclusion scope is BEA-4/BEA-5 only (from FD1). P4H's exact 73
  selected keys are private (`/tmp` only) and are not excluded; the reservoir
  is an FD1-excluded upper bound and may overlap with P4H's heldout. If that
  upper bound reaches 80 while P4H overlap remains unresolved, P4I reports
  `no_go_disjoint_denominator_reservoir_unqualified`, not ready.
- The realistic empirical outcome is
  `no_go_disjoint_denominator_reservoir_insufficient`: the supported Python
  frames are exhausted below the 80 gate. If the FD1-excluded upper bound is
  `>=80` but P4H overlap is unresolved, the outcome is
  `no_go_disjoint_denominator_reservoir_unqualified`.
- Gold/private labels are used only for evaluation/scoring file-miss.
- Latency is not measured or used at all (denominator audit, not a scheduler).
