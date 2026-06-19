# C3 Budgeted Evidence Acquisition v0

Date: 2026-06-19

C3 is the **budgeted evidence acquisition** phase that follows C2/B12. It is a
real **replay** policy experiment over the C1 private-records adapter
(`eval/c1_private_records.py`), not a planner or skeleton. A small frozen set
of interpretable candidate policies (each a function of a runtime-clean
`route_features` dict only) is replayed against P21 per-strategy outcomes, and
their **budgeted evidence utility** is compared against two baselines (P25 and
balanced_v1) under a common-complete denominator.

> **Important claim boundary.** C3 is a budgeted replay policy experiment, not
> a promotion step. The per-cell public report is **diagnostic-rank-only**: it
> emits sufficient aggregate statistics and a diagnostic ordering of candidate
> policies by utility, but it MUST NOT declare a winner. Per-cell candidate
> selection is deferred to the matrix combiner. `promotion_ready=false`,
> `default_should_change=false`, `EvidenceCore` semantics unchanged.

## Runtime-clean hard rule

Candidate policies MUST receive only a `route_features` dict (projected to the
frozen feature allowlist), NEVER a `PrivateRecord`. Candidate routing MUST NOT
read `task_bucket`, `task_risk_tags`, `has_gold`, `score_group`, `outcomes`,
`task_id`, `repo_id`, `model_family`, `language`, private hashes, etc.

The evaluator verifies routing invariance via a **real PrivateRecord-field
scrub test**: for each record, a scrubbed copy is built where every non-
`route_features` field (`task_bucket`, `task_risk_tags`, `score_group`,
`has_gold`, `outcomes`, `outcome_present`, `task_id`, `repo_id`,
`model_family`, `language`, `private_record_hash`, `source_ordinal`, p31/p33
blocks, `taint`) is replaced with sentinel/permuted values **guaranteed to
differ** from the original (e.g. `not has_gold`, inverted `outcome_present`
bools). The scrubbed record's `route_features` is confirmed identical to the
original's, every scrubbed private field is confirmed to actually differ, and
candidate policy actions computed from the scrubbed record's projected
`route_features` are confirmed identical to the original selections. The
public report surfaces two aggregate booleans:

- `selected_actions_invariant_under_private_field_permutation=true`
- `runtime_clean_policy_inputs_only=true`

## Allowed runtime features (frozen)

Intersection of C1 `route_features` present in P21 and this frozen allowlist.
Absent features are treated as false / 0:

- `query_noise`
- `candidate_support_exists`
- `local_anchor`
- `rrf_backed_by_anchor`
- `candidate_count`
- `symbol_regex_agree_file`
- `symbol_regex_agree_span`
- `rrf_anchor_agree_file`
- `rrf_anchor_agree_span`
- `dense_support_present`

`route_features` itself is never emitted in the public report (it is a
forbidden key); only the frozen feature-name list and aggregate
`feature_presence_counts` are surfaced.

## Allowed candidate actions (frozen)

Candidate policies MUST select one of these 5 actions. P25 and balanced_v1
are NOT candidate actions; they are baselines only and must be marked
`runtime_clean_candidate_policy=false`, `benchmark_label_taint=true`.

- `candidate_baseline`
- `weak_candidate_only`
- `llm_span_narrow`
- `llm_filter`
- `llm_abstain_filter`

## Frozen candidate policy set

A small interpretable fixed set, NOT outcome-derived. Frozen in the algorithm
spec; no tuning from outcomes.

| Policy id | Rule |
| --- | --- |
| `local_only` | always `candidate_baseline` |
| `weak_on_noise_else_local` | if `query_noise>0` then `weak_candidate_only` else `candidate_baseline` |
| `span_narrow_on_anchor_else_local` | if `local_anchor` and `rrf_backed_by_anchor` then `llm_span_narrow` else `candidate_baseline` |
| `filter_on_noise_else_span_narrow_on_anchor_else_local` | if `query_noise>0` then `llm_filter` elif `local_anchor` and `rrf_backed_by_anchor` then `llm_span_narrow` else `candidate_baseline` |
| `abstain_filter_on_disagreement_else_span_narrow_on_anchor_else_local` | if `local_anchor` and not `rrf_backed_by_anchor` then `llm_abstain_filter` elif `local_anchor` and `rrf_backed_by_anchor` then `llm_span_narrow` else `candidate_baseline` |
| `weak_on_disagreement_span_on_anchor_else_local` | if `local_anchor` and not `rrf_backed_by_anchor` then `weak_candidate_only` elif `local_anchor` and `rrf_backed_by_anchor` then `llm_span_narrow` else `candidate_baseline` |

## Budgeted Evidence utility (frozen constants)

```text
utility = span_f0_5
          - lambda * added_false_span
          - mu * primary_false_positive_rate
          - cost_weight * model_calls
```

Frozen before any C3 replay:

- `lambda = 1.0`
- `mu = 1.0`
- `cost_weight = 0.1`

`model_calls` per selected action = 1 for `llm_span_narrow` / `llm_filter` /
`llm_abstain_filter`, 0 for `candidate_baseline` / `weak_candidate_only`.

## Baselines (baselines ONLY, never candidate policies)

- **P25 baseline**: uses C1 `compute_p25_strategy(record)` for outcome
  selection. Marked `benchmark_label_taint=true` (P25 routing reads benchmark
  route labels).
- **balanced_v1 baseline**: if C1 `balanced_branch_predicate(record)` then
  `weak_candidate_only` else P25 strategy. Marked
  `benchmark_label_taint=true`.

Candidate policies MUST NOT call `compute_p25_strategy` /
`balanced_branch_predicate`.

## Coverage rules (common-complete denominator)

- A **common-complete** denominator is used across all candidate policies and
  baselines for a cell.
- If any selected action outcome is missing for a record for any policy or
  baseline, that record is excluded and counted as `incomplete_record_count`.
- If `complete_records == 0` => `status=coverage_insufficient`,
  `winner_declared=false`.
- The per-cell report MUST NOT declare a winner. It emits
  `cell_diagnostic_rank_only=true`, `winner_declared=false`,
  `candidate_selection_deferred_to_matrix_combiner=true`.

## Public artifact forbidden fields

Recursive scan rejects keys/values: `task_id`, `test_id`, `repo_id`, `run_id`,
`private_record_hash`, `record_hash`, `source_ordinal`, `candidate_id`, `path`,
`span`, `content_sha`, `query`, `raw_query`, `snippet`, `prompt`, `response`,
`provider_key`, `api_key`, `base_url`, `score_group`, `has_gold`, `outcomes`,
`strategy_results`, `p31_score_gold`, `p31_candidate_pools`,
`p33b_anchor_subtypes`, `task_risk_tags`, `route_features`,
`private_label`, `private_labels`, `label`, `labels`, `gold_spans`, `hash`,
`digest`, `task_bucket`. The scan is exact-match on key names, so safe metric
names like `added_false_span` / `primary_false_positive_rate` /
`added_gold_span` remain allowed.

Raw `repo_id` / `run_id` / `task_id` / `path` / hash values are never emitted.
Aggregate `model_family` and `language` counts are OK. `task_bucket` counts
are omitted for v0.

## Report fields

- `schema_version`: `c3-budgeted-evidence-acquisition-report-v0`
- `generated_by`: `c3_budgeted_evidence_acquisition`
- `claim_level`: `budgeted_replay_policy_experiment_v0`
- `policy_count`, `candidate_policy_ids`, `action_set`,
  `allowed_runtime_features`, `objective_constants`
- `total_records`, `complete_records`, `incomplete_record_count`, `status`
  (`ok_cell_stats` / `coverage_insufficient` / `insufficient_data` /
  `privacy_or_schema_blocked`)
- `per_policy`: per candidate policy aggregate metrics (mean + sum of
  `span_f0_5`, `added_gold_span`, `added_false_span`,
  `primary_false_positive_rate`, `model_calls`, `utility`)
- `baselines`: aggregate metrics for `p25` and `balanced_v1` (with taint flags)
- `deltas`: per candidate policy deltas vs `p25` and vs `balanced_v1`
- `diagnostic_rank_only`: candidate policy ids sorted by descending mean
  utility (diagnostic ONLY; no winner)
- `feature_presence_counts`: aggregate-only
- `selected_actions_invariant_under_private_field_permutation`,
  `runtime_clean_policy_inputs_only`
- `safety_invariants` / privacy flags

## Modes

- `--self-test`: synthetic fixture only; **read-only** (builds expected spec +
  report in memory and compares to on-disk artifacts, failing on drift; does
  NOT mutate checked-in artifacts); MUST NOT claim empirical support
  (`empirical_algorithm_experiment_performed=false`).
- `--regenerate-artifacts`: the **only** path that writes the canonical
  synthetic algorithm spec + self-test report to
  `artifacts/c3_budgeted_evidence_acquisition/`. Use after code changes, then
  run `--self-test` to confirm.
- `--input <path>`: loads private P21 v1 records via the C1 adapter and writes
  an aggregate-only public report. Sets
  `empirical_algorithm_experiment_performed=true` and
  `policy_search_or_enumeration_performed=true`.

## CI workflow integration

C3 is wired into the P21 step of
`.github/workflows/real-provider-benchmark.yml`: after B12 consumes the SAME
ephemeral `$P25_RECORDS` and before `rm -f "$P25_RECORDS"`, C3 runs:

```bash
python3 eval/c3_budgeted_evidence_acquisition.py \
  --input "$P25_RECORDS" \
  --out artifacts/real_provider_ci/c3_budgeted_evidence_acquisition_report.json
```

Per-cell C3 emits **sufficient stats only and no winner**. The aggregate
booleans `selected_actions_invariant_under_private_field_permutation` and
`runtime_clean_policy_inputs_only` are surfaced for the matrix combiner.
`remote_calls_by_c3=0` and `model_calls_by_replay=0` (replay-only).

## Safety invariants

```text
empirical_algorithm_experiment_performed=true (only with --input on real records)
policy_search_or_enumeration_performed=true (frozen enumeration, no tuning)
replay_only=true
remote_calls_by_c3=0
model_calls_by_replay=0
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
aggregate_only_public_artifact=true
winner_declared=false
cell_diagnostic_rank_only=true
candidate_selection_deferred_to_matrix_combiner=true
```

## Self-test

```bash
python3 eval/c3_budgeted_evidence_acquisition.py --self-test
python3 eval/c1_private_records.py --self-test
```

The C3 self-test verifies: forbidden scan, spec hash stability, frozen
action/feature allowlists, frozen objective constants, runtime-clean
invariance (real PrivateRecord-field scrub test), P25/balanced are NOT
candidate policies, synthetic-fixture mechanics, `--input` full mode on a
synthetic C1 payload, missing-outcome => `coverage_insufficient`, no
per-cell winner, on-disk artifacts match in-memory build (drift detection),
and docs paths exist if practical. The self-test is strictly read-only and
MUST NOT mutate checked-in artifacts; use `--regenerate-artifacts` to update
canonical artifacts. Synthetic fixtures confer no empirical support.

## Artifacts

- `artifacts/c3_budgeted_evidence_acquisition/c3_budgeted_evidence_acquisition.algorithm.json`
  (frozen spec; deterministic, stable sha256)
- `artifacts/c3_budgeted_evidence_acquisition/c3_budgeted_evidence_acquisition_report.json`
  (synthetic-fixture self-test report; `status` is a mechanics result, NOT
  empirical)
- `artifacts/real_provider_ci/c3_budgeted_evidence_acquisition_report.json`
  (CI ephemeral-records replay report; scientific status is a valid CI outcome,
  may be `ok_cell_stats` / `coverage_insufficient` / `insufficient_data`)

## What C3 does NOT prove

- C3 does NOT prove any candidate policy is ready for promotion.
- C3 does NOT change any defaults.
- C3 does NOT change `EvidenceCore` semantics.
- C3 does NOT tune candidate policies from outcomes (the set is frozen).
- C3 does NOT declare a per-cell winner; selection is deferred to the matrix
  combiner.
- C3's `--input` replay is real, but its output is diagnostic-rank-only. No
  promotion / no default change follows.
