# BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke

Date: 2026-06-30

BEA-v1-HAAE-R1C is the **first explicit-opt-in phase** allowed to create a
private HAAE trace-root artifact, but only as a **bounded smoke** of the
root/output/manifest pipeline. Locked source: HAAE-R1B commit/artifact
`8830492`. R1C must NOT run FD1/P4L/N10EO/N10ER replay, retrieval, scoring,
candidate generation, selector, BEA-v1-A/P5/runtime/default.

## Mode

- **Default / no-private mode** (no `--allow-private-root-regeneration-smoke`):
  performs **no** private reads or writes and produces status
  `haae_r1c_unavailable_no_explicit_opt_in`.
- **Explicit opt-in mode** requires ALL of:
  - `--allow-private-root-regeneration-smoke`
  - `--recipe <allowed_recipe_bucket>` (one of:
    `bootstrap_private_manifest_root_smoke`,
    `operator_supplied_existing_root_manifest_smoke`,
    `public_aggregate_source_option_manifest_smoke`)
  - `--private-output-root <path>` (must not be a public tracked
    docs/artifacts/eval location; must not be a symlink; must not contain path
    traversal; bounded depth)
  - `--confirm-private-output-only`
  - optional `--private-input-root <path>` (existing-root recipe only)

The output root is validated: it must be explicit, must not be public
tracked, must not be a symlink, must not allow path traversal, and must have
bounded depth and a bounded write set. No concrete path/basename/filename
is ever published.

## Allowed recipes

1. **`bootstrap_private_manifest_root_smoke`** (default explicit-opt-in
   recipe): creates an explicit private output root, writes only
   manifest/control files and empty/schema-category placeholders, **zero**
   raw task/query/candidate/span/score rows. Public artifact carries
   bucketized manifest only.
2. **`operator_supplied_existing_root_manifest_smoke`** (optional): explicit
   input/output roots, metadata/schema inventory only, no row values, public
   aggregate buckets only.
3. **`public_aggregate_source_option_manifest_smoke`** (optional): public-only
   projection, no private input.

## Deferred (forbidden in R1C) recipes

4 deferred replay recipes: `fd1_decomposition_replay_recipe`,
`p4l_scheduler_replay_recipe`, `n10eo_diagnostic_rerun_recipe`,
`n10er_public_ci_replay_recipe`. All are marked as deferred with
`replay_authorized_bool=false`.

## HAAE-R1B source lock

```text
haae r1b checkpoint: 8830492
haae r1b status: haae_r1b_bounded_private_trace_root_regeneration_preflight_package_complete_r1c_smoke_authorized
haae r1b next allowed phase: BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke
haae r1c authorized by haae r1b: true
haae r1c design only: true
haae r1c execution / private_read / replay / scoring / retrieval / candidate_generation: false
haae r1c bounded_recipe_only: true
haae r1c unbounded_replay / unbounded_retrieval / unbounded_candidate_generation: false
haae r0 non-identity booleans: all true
haae r1b source locked: true
```

## Result (default no-private mode)

```text
status: haae_r1c_bounded_private_manifest_root_smoke_complete_r1d_inventory_authorized
self-test: 105 / 105
forbidden scan: pass
private input reads: 0
private writes: 1
retrieval executions: 0
replays: 0
fd1/p4l/n10eo/n10er replays: 0
haae layer executions: 0
clone/build/search: false
haae r1b source locked: true (checkpoint 8830492)
10 schema groups accounted: true
4 deferred recipes: true
next allowed phase: BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke
```

## 10 schema group manifest records

All 10 HAAE-R0 schema groups have manifest records with
`raw_row_count=0` and `placeholder_kind_bucket=empty_schema_category`:
task_identity, anchor_source, candidate_pool, rank_pack, span_projection,
scheduler_action, evidence_core, arm_assignment, outcome_metric,
safety_probe_signal.

## Boundary

R1C is explicitly **not** BEA-v1-A, not selector-only, not selector/reranker
execution, not P5, not a runtime/default promotion, not a HAAE-layer
execution, not a replay, not a scoring, not a retrieval, not a candidate
generation. R1C must not run FD1/P4L/N10EO/N10ER replay. Successful R1C
authorizes only R1D schema inventory, not any of these executions. All such
claim-boundary and stop/go fields are `false`.

## Stop/go

Successful R1C bootstrap smoke authorizes only **BEA-v1-HAAE-R1D Explicit
Private Root Schema Inventory Smoke**. Default/no-opt-in mode still authorizes
no next phase. All execution, rerun, replay, retrieval,
recompute, candidate generation, arm scoring, OpenLocus execution,
HAAE-layer execution, FD1/P4L/N10EO/N10ER replay, threshold tuning, new
policy experiments, frozen-rule changes, guard/full/diffaware promotion,
runtime/default changes, method-winner claims, downstream/scaled retrieval,
raw diagnostic publication, CI variant execution, selector/reranker,
BEA-v1-A, P5, provider/model network, and network-run fields are `false`.

## Workflow

- Smoke helper: `eval/bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke.py`
- The helper exposes `--self-test`, `--validate-report`, `--out`,
  `--haae-r1b-report`, `--allow-private-root-regeneration-smoke`, `--recipe`,
  `--private-output-root`, `--confirm-private-output-only`, and
  `--private-input-root`. Default mode produces the unavailable artifact
  without any private reads or writes; the committed result uses explicit
  bootstrap smoke mode and publishes only the aggregate manifest.

## Artifact

- Helper: `eval/bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke.py`
- Report: `artifacts/bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke/bea_v1_haae_r1c_bounded_private_trace_root_regeneration_smoke_report.json`
