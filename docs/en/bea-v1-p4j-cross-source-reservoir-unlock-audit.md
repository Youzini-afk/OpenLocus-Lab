# BEA-v1-P4J: Cross-Source File-Miss Reservoir Unlock Audit

Date: 2026-06-25. BEA-v1-P4J is a bounded **cross-source denominator/source
audit** performed after the BEA-v1-P4I No-Go (checkpoint `cc19f5b`, CI run
`28137455572`, `no_go_disjoint_denominator_reservoir_insufficient` with 73/80
disjoint file-miss records). It does **not** run P2/P3/P4 scheduler arms,
does **not** validate a scheduler, does **not** expand retrieval, does **not**
execute a selector/reranker, does **not** call any provider, does **not** run
runtime/default promotion or method-winner logic, and does **not** authorize
P5, BEA-v1-A, or frozen P4 rerun. The only diagnostic arm is
`current_bea_candidate_pool_replay`.

> `claim_level = bea_v1_p4j_cross_source_reservoir_unlock_audit_only`.
> `provider_calls_made=false`, `gold_labels_used_for_query_construction=false`,
> `gold_labels_used_for_policy=false`, `latency_in_candidate_relevance=false`,
> `query_anchors_used_in_p4_arm=false`, `selector_or_reranker_changed=false`,
> `selector_or_reranker_executed=false`,
> `p2_depth_only_reference_executed=false`,
> `p3_constrained_depth_policy_reference_executed=false`,
> `p4_latency_aware_action_scheduler_executed=false`,
> `v1_a_selector_executed=false`, `p5_authorized=false`,
> `v1_a_authorized=false`, `frozen_p4_rerun_authorized=false`, and
> `locked_p4_validation_executed=false` are binding.

## Motivation (P4H/P4I No-Go)

- P4H result checkpoint `9305701`; CI run `28132121958`; status
  `no_go_p4h_insufficient_denominator`: the full-frame disjoint scan found
  only **73/80** heldout baseline file-miss records.
- P4I result checkpoint `cc19f5b`; CI run `28137455572`; status
  `no_go_disjoint_denominator_reservoir_insufficient`: the full-frame
  disjoint reservoir scan over the supported ContextBench/RepoQA **Python**
  frames found only **73/80** FD1-excluded file-miss reservoir records
  (61 ContextBench, 12 RepoQA). P4H overlap remained unresolved (P4H exact
  selected keys are private/aggregate-only).

P4J answers the open question left by P4H/P4I: is the 73/80 blocker specific to
the currently supported ContextBench/RepoQA **Python** frame, or can
alternative already-supported **cross-source frames** unlock at least 80
baseline file-miss denominator records?

## Scope (binding)

- P4J is a **cross-source denominator/source audit only**. It is NOT P5, NOT
  BEA-v1-A, NOT scheduler validation, NOT retrieval expansion, NOT
  selector/reranker, NOT broad retrieval, NOT method-winner logic, NOT
  runtime/default promotion, NOT frozen P4 rerun.
- It scans only already-supported cross-source frames, evaluated with the
  existing `current_bea_candidate_pool_replay` diagnostic arm:
  1. ContextBench `contextbench_verified/train` with `language_filter="all"`
     via `c5a._fetch_contextbench_rows(limit, "all")`. The `default` config is
     NOT used (that would be new dataset integration).
  2. RepoQA non-Python top-level asset languages via
     `c5d._download_asset_to_bytes` + `c5d._decompress_asset` +
     `c5d._parse_repoqa_needles(parsed, lang, limit)`. The c5d CLI is bypassed
     because its argparse currently only allows Python.
- A candidate denominator record is a baseline/current candidate pool **miss**
  of the gold file (`gold_file_available=false`). The only diagnostic arm is
  `current_bea_candidate_pool_replay`. P2/P3/P4 scheduler arms are NOT run.
- The scan does **not** stop at an 80-record target; it counts the full
  cumulative cross-source file-miss reservoir upper bound and separately
  reports whether that reservoir is qualified as all-prior-disjoint.

## Excluded source frames (documented)

- SWE-Explore: schema/row-map only; no `repo_url` / `base_commit` clone path.
- CORE-Bench: readiness probe only; no row-to-retrieval adapter.
- SWE-bench original: no adapter in repo.
- ContextBench `default` config: not yet integrated; using it would be new
  dataset integration, which is out of P4J scope.

These are disclosed in `excluded_source_frame_records`.

## Denominator construction

- The P4J reservoir is **not** the FD1 `gold_file_absent` tail and does not
  reuse the prior P1/P2/P3/P4 FD1 denominator.
- P4J performs a cross-source file-miss reservoir unlock quota scan:
  - ContextBench `all`: `offset=0`, `limit=480`, `language_filter="all"`.
  - RepoQA non-Python: per-language `limit=60`; languages discovered dynamically
    from the downloaded RepoQA release asset (c5d CLI bypassed).
- Exact prior raw-key exclusion is used **where applicable**. From the FD1
  private decomposition, only **BEA-4 and BEA-5** exact raw keys are available
  (`exact_prior_exclusion_scope =
  fd1_private_exact_bea4_bea5_raw_keys_where_applicable_by_construction_disjoint_for_non_python_frames`).
  These are in Python-ordinal space and applied to ContextBench Python rows
  (mapped via running python-ordinal). Exact keys are NOT faked for other prior
  phases.
- For non-Python frames (ContextBench non-Python rows + RepoQA non-Python
  needles), a **by-construction disjoint** basis is disclosed: BEA-4/5 only
  ran on the Python frame, so non-Python rows have no FD1 prior keys
  (`by_construction_disjoint_non_python_frames=true`). This is disclosed, not
  faked.
- For P1/P2/P3/P4 the FD1 BEA-4/5 exact superset already covers their shared
  119-record Python denominator, so only an aggregate disclosure is emitted.
- For P4H/P4I the exact selected keys are private (`/tmp` only, never
  committed, not in FD1), so only aggregate disclosures are emitted and exact
  keys are NOT faked. The reservoir is therefore reported as an FD1-excluded
  upper-bound file-miss pool which may overlap with P4H's/P4I's heldout
  selections. The non-Python subset
  (`cross_source_non_python_reservoir_count`) is by-construction disjoint from
  P4H/P4I (Python-only), but is NOT treated as a qualified all-prior-disjoint
  reservoir unless P4H/P4I overlap is resolved (see below).
- The scan uses stable raw order after exclusions. For each raw row, P4J clones
  the repository, runs only `current_bea_candidate_pool_replay`, and selects
  the row for the reservoir only when the baseline/current candidate pool
  misses the gold file.
- The reservoir is constructed before any future scheduler outcomes. There
  are no treatment arms.
- The public artifact publishes only aggregate attempt/yield/exclusion counts
  by source, frame, benchmark, and language bucket, plus subgroup counts and
  the cumulative reservoir count. Private per-record keys, row indices, queries,
  repository URLs, gold paths, candidate paths, manifests, and traces are
  written under `/tmp` only.

## Hard validity gates

- `reservoir_upper_bound_count >= 80` for reservoir availability evidence.
- `qualified_cross_source_reservoir_count >= 80` and
  `p4h_p4i_overlap_resolved=true` for
  `cross_source_reservoir_ready_for_locked_p4_validation_design`.
- Exact prior exclusion used where applicable; no private raw keys/ids
  serialized.
- The denominator/reservoir is constructed before any future scheduler
  outcomes (there are no treatment arms).
- Aggregate-only, records-only public artifact: no dynamic dicts for public
  metrics (only `framing` and `forbidden_scan` are fixed-schema dicts;
  `forbidden_scan.violation_categories` is a list).
- `forbidden_scan.status=pass`.
- No provider calls.
- No retrieval policy change, no selector/reranker execution, no
  latency-in-relevance, no P2/P3/P4 scheduler arms, no method-winner logic,
  no runtime/default promotion.
- Blocking failures (scan failed, scan not attempted, clone failed, asset
  download/decompress failed, unexpected exception, FD1 replay/schema mismatch)
  cannot be reported as an insufficient denominator; they yield
  `fail_schema_contract` (fail-closed).

## Statuses

- `cross_source_reservoir_ready_for_locked_p4_validation_design` — qualified
  all-prior-disjoint cross-source reservoir reaches `>= 80` with P4H/P4I
  overlap resolved. This authorizes **only** designing a separate frozen P4
  validation on a locked denominator. It does **not** run a scheduler, does
  **not** authorize P5, BEA-v1-A, runtime promotion, method-winner claims,
  broad retrieval expansion, selector/reranker execution, frozen P4 rerun, or
  runtime/default promotion. `locked_p4_validation_design_authorized=true` is
  expressed only inside `stop_go_records`; the top-level guard
  `locked_p4_validation_executed` remains false. `frozen_p4_rerun_authorized=false`.
- `no_go_cross_source_file_miss_reservoir_insufficient` — still `< 80` after
  scanning the supported cross-source frames. This confirms FD1-excluded
  file-miss denominator scarcity is structural for the currently supported
  cross-source frames.
- `no_go_cross_source_reservoir_unqualified` — the FD1-excluded upper-bound
  reservoir reaches `>=80`, but P4H/P4I overlap is unresolved (exact selected
  keys unavailable). This is source-unlock evidence only; no scheduler rerun
  or locked P4 validation design is authorized.
- `unavailable_with_reason` — default no-network artifact (honest, not a
  pass).
- `fail_schema_contract` / `fail_forbidden_scan` — privacy/schema/provenance
  failures. No `fail_*` status is CI-valid for a network-enabled real run.

The network workflow validator fails-closed for privacy/schema failures and
accepts only `cross_source_reservoir_ready_for_locked_p4_validation_design`,
`no_go_cross_source_file_miss_reservoir_insufficient`, or
`no_go_cross_source_reservoir_unqualified` as valid research outcomes (plus
`unavailable_with_reason` only in the no-network default path).

## Stop rules (exact)

1. If the reservoir scan was not attempted (network disabled, prerequisites
   missing), the default artifact is `unavailable_with_reason` (no-network
   path only). The scan is never faked.
2. If a blocking failure occurs during the scan (raw fetch failed, clone
   failed, asset download/decompress failed, unexpected exception, FD1
   replay/schema mismatch, exact prior exclusion unavailable), the status is
   `fail_schema_contract` (fail-closed). Blocking failures are never reported
   as `no_go_cross_source_file_miss_reservoir_insufficient`.
3. If the scan completes and the cumulative upper-bound file-miss reservoir is
   `< 80`, the status is
   `no_go_cross_source_file_miss_reservoir_insufficient`. The hard gate of 80
   is not lowered.
4. If the scan completes and the cumulative upper-bound file-miss reservoir is
   `>= 80` but P4H/P4I overlap is unresolved, the status is
   `no_go_cross_source_reservoir_unqualified`. This does not authorize any
   scheduler rerun or locked P4 validation design.
5. If the scan completes and a qualified all-prior-disjoint cross-source
   reservoir is `>= 80` with overlap resolved, the status is
   `cross_source_reservoir_ready_for_locked_p4_validation_design`. This
   authorizes only designing a separate frozen P4 validation on the locked
   denominator; it does not run a scheduler, select a method, change any
   default, or authorize P5 / BEA-v1-A / runtime promotion / method winner /
   broad retrieval expansion / frozen P4 rerun.
6. `cross_source_reservoir_ready_for_locked_p4_validation_design` does not
   itself run a scheduler, select a method, or change any default. A subsequent
   frozen P4 validation is a separate, explicitly authorized step that must
   lock the denominator and resolve any P4H/P4I overlap using exact keys at
   validation time.

## Public artifact contract

Required aggregate-only record tables (records-only; no dynamic dicts):

- `source_run_records`
- `denominator_reservoir_records`
- `denominator_scan_records`
- `cross_source_frame_records`
- `excluded_source_frame_records`
- `prior_raw_exclusion_records`
- `subgroup_reservoir_records`
- `stop_go_records`
- `gate_records`
- `private_manifest_records`
- `failure_category_count_records`
- `framing`
- `forbidden_scan`

No dynamic per-record detail, no private raw keys/ids/paths, no repo URLs, no
queries, no gold paths, no candidate paths, no snippets, no prompts/responses,
no provider payloads, no private hashes, and no private trace paths are
serialized. The `manifest_hash` in `private_manifest_records` is a
provenance-only file-level integrity hash and does not expose row ids, raw
keys, paths, queries, candidate lists, or trace locations. No row/key/path
hashes are serialized.

## Workflow

The manual workflow
`bea-v1-p4j-cross-source-reservoir-unlock-audit.yml` runs only via
`workflow_dispatch` and accepts `enable_external_benchmark_network`. It builds
the OpenLocus release CLI, runs self-tests, regenerates FD1 private
decomposition under `/tmp`, validates the 239-record / 86040-row FD1 replay,
runs the P4J cross-source file-miss reservoir scan, validates the report
fail-closed, and uploads the aggregate report. Private JSONL/JSON traces are
written under `/tmp` only and are never uploaded. The workflow uses no
model/provider secrets. Private directories use `/tmp`, not `$RUNNER_TEMP`;
only the final public report is staged at `$RUNNER_TEMP` for upload.

## Local validation

```text
python3 -m py_compile eval/bea_v1_p4j_cross_source_reservoir_unlock_audit.py  => PASS
python3 eval/bea_v1_p4j_cross_source_reservoir_unlock_audit.py --self-test  => PASS (118/118 checks)
python3 eval/bea_v1_p4j_cross_source_reservoir_unlock_audit.py \
  --out artifacts/bea_v1_p4j_cross_source_reservoir_unlock_audit/bea_v1_p4j_cross_source_reservoir_unlock_audit_report.json  => PASS
  (default no-network status: unavailable_with_reason,
   forbidden_scan=pass, denominator_count=0,
   cross_source_reservoir_scan_attempted=false,
   self_test_checks_total=118, self_test_checks_passed=118)
```

## CI result

Pending. The network-enabled CI run has not yet been executed. The default
no-network artifact is `unavailable_with_reason` (honest, not a pass). A real
network-enabled run is required to produce a research outcome.

The realistic empirical outcome is expected to be one of:
- `no_go_cross_source_file_miss_reservoir_insufficient` (cross-source reservoir
  upper bound `< 80`), or
- `no_go_cross_source_reservoir_unqualified` (upper bound `>= 80` but P4H/P4I
  overlap unresolved).

The `cross_source_reservoir_ready_for_locked_p4_validation_design` status
requires both a qualified `>= 80` all-prior-disjoint reservoir AND resolved
P4H/P4I overlap; since P4H/P4I exact selected keys remain unavailable unless
regenerated under `/tmp`, this status is not expected from a default
network-enabled run unless the workflow regenerates P4H/P4I exact keys and
resolves the overlap, which is out of P4J scope.

## Caveats

- P4J is a cross-source denominator/source audit only. It is not a
  benchmark/leaderboard, default-policy, method-winner, runtime-promotion,
  downstream-value, P5, BEA-v1-A, scheduler-validation, retrieval-expansion,
  selector/reranker, frozen-P4-rerun, or runtime/default-promotion authorization
  claim.
- The exact-exclusion scope is BEA-4/BEA-5 only (from FD1), applied where
  applicable (ContextBench Python rows via python-ordinal). P4H's/P4I's exact
  selected keys are private (`/tmp` only) and are not excluded; the reservoir
  is an FD1-excluded upper bound and may overlap with P4H's/P4I's heldout
  selections. If that upper bound reaches 80 while P4H/P4I overlap remains
  unresolved, P4J reports `no_go_cross_source_reservoir_unqualified`, not ready.
- The non-Python subset (`cross_source_non_python_reservoir_count`) is
  by-construction disjoint from P4H/P4I (Python-only) but is NOT treated as a
  qualified all-prior-disjoint reservoir unless P4H/P4I overlap is resolved by
  regenerating their exact selected keys under `/tmp`.
- `cross_source_reservoir_ready_for_locked_p4_validation_design` does NOT
  authorize frozen P4 rerun (`frozen_p4_rerun_authorized=false`); it authorizes
  only designing a separate locked-P4 validation on the locked denominator.
- Gold/private labels are used only for evaluation/scoring file-miss.
- Latency is not measured or used at all (denominator audit, not a scheduler).
- The ContextBench `default` config is intentionally excluded (new dataset
  integration is out of scope); only `contextbench_verified/train` with
  `language_filter="all"` is used.
- The RepoQA c5d CLI is bypassed because its argparse only allows Python;
  non-Python asset languages are parsed directly via
  `c5d._parse_repoqa_needles(parsed, lang, limit)`.
