# BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory

Date: 2026-06-30

BEA-v1-HAAE-R1 is the **feasibility inventory** for the unified private trace
schema designed by HAAE-R0 (checkpoint `854fc2e`). It is **not** a replay,
scoring, retrieval, candidate-generation, or HAAE-layer execution phase. It
inventories whether the 10 HAAE-R0 schema groups can be populated from
explicitly supplied project-private root buckets, emitting **aggregate buckets
only**.

## Mode

- **Default / no-private mode** (no `--allow-private-inventory`): HAAE-R1 does
  **not** read private roots. It produces an `unavailable` public artifact (no
  explicit private roots supplied) or runs `--self-test` only. No private
  filesystem access occurs in default mode.
- **Real inventory mode** (`--allow-private-inventory --private-root <path>`,
  repeatable): the only private operations performed are enumerating explicitly
  supplied project-private root buckets (no symlink escape, bounded depth, no
  traversal outside the explicitly supplied root buckets),
  identifying candidate files by extension/type/schema bucket, and parsing
  schemas/JSON keys to stream row-count buckets, column presence buckets, type
  compatibility buckets, missingness buckets, and anonymous join-shape
  availability buckets.

HAAE-R1 **never** publishes paths, filenames, basenames, repo names, task ids,
queries, candidates, spans, snippets, hashes, exact ranks/scores, labels, or
row values. Every record is aggregate-bucket-only. The safe parser rejects
unknown args generically without echoing values.

## HAAE-R0 source lock

```text
haae r0 checkpoint: 854fc2e
haae r0 status: haae_r0_design_schema_preflight_complete_haae_r1_authorized
haae r0 next allowed phase: BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory
haae r1 authorized by haae r0: true (haae_r1_unified_private_trace_schema_feasibility_inventory_authorized_bool)
haae r1 execution authorized by haae r0: false (haae_r1_execution_authorized_bool)
haae r1 replay / scoring / retrieval / candidate_generation authorized: false
n10et checkpoint: 26d817e (upstream)
n10et status: n10et_public_safety_probe_design_decision_complete_haae_r0_authorized
haae r0 non-identity booleans: all true (not_bea_v1_a, not_selector_only,
  not_selector_reranker_execution, not_p5, not_runtime_default_promotion)
haae r0 source locked: true
no_ci_rerun / no_retrieval / no_recompute / no_private_input_read: true
no_replay / no_scoring / no_candidate_generation / no_haae_layer_execution: true
```

## Result

```text
status: haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots
self-test: 121 / 121
forbidden scan: pass
private read count bucket: count_0 (default mode)
retrieval executions: 0
recomputes: 0
CI reruns: 0
candidate generations: 0
arm scorings: 0
openlocus executions: 0
replays: 0
haae layer executions: 0
haae r0 source locked: true (checkpoint 854fc2e)
10 schema groups accounted: true
critical groups: task_identity, candidate_pool, evidence_core, arm_assignment, outcome_metric
```

(The default/no-private mode produces the `unavailable_no_explicit_private_roots`
artifact. Real inventory requires explicit `--allow-private-inventory
--private-root <path>` opt-in and would produce a `pass` /
`controlled_no_go` artifact based on coverage. The status above reflects the
default mode.)

## 10 schema groups accounted

| # | Group | Critical | Columns |
|---|---|---|---|
| 0 | task_identity | yes | anonymous_task_id, repo_bucket, language_bucket |
| 1 | anchor_source | no | anchor_kind_bucket, acquisition_cost_bucket |
| 2 | candidate_pool | yes | candidate_count_bucket, depth_distribution_bucket |
| 3 | rank_pack | no | topk_pack_bucket, novel_vs_old_pool_bucket |
| 4 | span_projection | no | span_window_bucket, span_overlap_bucket |
| 5 | scheduler_action | no | scheduled_action_bucket, action_cost_bucket |
| 6 | evidence_core | yes | path_bucket, line_range_bucket, content_sha_bucket, score_bucket, why_bucket, channels_bucket |
| 7 | arm_assignment | yes | arm_bucket, budget_bucket |
| 8 | outcome_metric | yes | citation_validity_bucket, file_recovery_topk_bucket, lost_baseline_top10_bucket |
| 9 | safety_probe_signal | no | full_guard_diffaware_loss_bucket, risk_bucket_signal |

All 10 groups are accounted in `schema_group_feasibility_records`. The 5
critical groups are `task_identity`, `candidate_pool`, `evidence_core`,
`arm_assignment`, `outcome_metric`.

## Coverage buckets

Each group's coverage is bucketed as: `full` (all columns present with rows),
`sufficient` (at least half the columns present for critical groups, or any
presence for non-critical groups), `partial` (some columns present but below
the sufficient threshold), `missing` (no columns present despite rows), or
`not_present` (no rows observed). Row counts are bucketed as `count_0`,
`count_1_to_10`, `count_11_to_100`, `count_101_to_1000`, `count_1001_plus`.

## Pass / no-go / unavailable

- **Pass** (`haae_r1_feasibility_inventory_pass_haae_r2_authorized`): all 10
  groups at least partial **and** the 5 critical groups full or sufficient.
- **Controlled no-go**
  (`haae_r1_feasibility_inventory_controlled_no_go_haae_r1a_authorized`):
  valid inventory but insufficient (at least one group partial-but-not-
  sufficient, or a critical group missing/insufficient).
- **Unavailable** (`haae_r1_feasibility_inventory_unavailable_no_locked_source`
  / `..._no_explicit_private_roots`): no locked HAAE-R0 source, or default
  mode with no explicit private roots.

Fail-closed statuses: `fail_haae_r0_source_lock_mismatch`,
`fail_forbidden_scan`, `fail_schema_contract`, `fail_contract_violation`,
`fail_private_boundary_violation`, `fail_forbidden_operation`.

## Public artifact records

The artifact carries: `source_lock_records`, `private_root_inventory_records`,
`schema_group_feasibility_records` (10 groups),
`schema_column_feasibility_records`, `cross_group_join_feasibility_records`,
`public_aggregation_feasibility_records`, `coverage_summary_records`,
`synthetic_validator_records` (3 embedded synthetic full/partial/missing
fixtures), `risk_control_records` (6 controls), `public_package_records`,
`claim_boundary_records`, `pass_fail_gate_records` (27 audit gates),
`stop_go_records`, and `forbidden_scan`.

## Public aggregation feasibility

The 4 HAAE-R0 public aggregation contracts (`task_count_aggregate`,
`arm_aggregate`, `risk_bucket_aggregate`, `citation_aggregate`) each carry a
`feasibility_bucket` (`feasible` / `not_feasible`) based on whether all source
groups have at least partial coverage. No raw aggregation values are
published.

## No replay / scoring / retrieval / candidate generation / HAAE-layer execution

HAAE-R1 is a feasibility inventory only. It performs **no** replay, **no**
scoring, **no** retrieval, **no** candidate generation, **no** arm scoring,
**no** OpenLocus execution, and **no** HAAE-layer execution. The synthetic
validators run in-process on embedded synthetic fixtures only (not real data,
not replay, not retrieval, not candidate generation).

## Boundary

HAAE-R1 is explicitly **not** BEA-v1-A, not selector-only, not
selector/reranker execution, not P5, not a runtime/default promotion, not a
HAAE-layer execution, not a replay, not a scoring, not a retrieval, not a
candidate generation. All such claim-boundary and stop/go fields are `false`.
The HAAE-R0 non-identity booleans (`haae_r0_not_bea_v1_a_bool`,
`haae_r0_not_selector_only_bool`,
`haae_r0_not_selector_reranker_execution_bool`, `haae_r0_not_p5_bool`,
`haae_r0_not_runtime_default_promotion_bool`) are all `true`.

## Stop/go

- **Pass** → authorizes **only** BEA-v1-HAAE-R2 Feasibility-Gated Offline
  Trace Join Design (design-only, no execution/replay/scoring/retrieval/
  candidate generation): `haae_r2_feasibility_gated_offline_trace_join_design_authorized_bool=true`,
  `haae_r2_execution_authorized_bool=false`.
- **No-go** → authorizes **only** BEA-v1-HAAE-R1A Private Trace Coverage Gap
  Design (design-only, no execution):
  `haae_r1a_private_trace_coverage_gap_design_authorized_bool=true`,
  `haae_r1a_execution_authorized_bool=false`.

It does **not** authorize: any execution, rerun, retrieval, recompute,
candidate generation, arm scoring, OpenLocus execution, replay, HAAE-layer
execution, threshold tuning, new policy experiments, frozen-rule changes,
guard/full/diffaware promotion, runtime/default changes, method-winner claims,
downstream/scaled retrieval, raw diagnostic publication, CI variant execution,
selector/reranker, BEA-v1-A, P5, provider/model network, or network runs. All
such stop/go fields are `false`.

The detailed source of truth for the HAAE-R0 schema preflight is
[`docs/en/bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md`](bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md)
and [`current-research-conclusions.md`](current-research-conclusions.md).

## Workflow

- Feasibility-inventory helper:
  `eval/bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory.py`
- The helper exposes `--self-test`, `--validate-report`, `--out`,
  `--allow-private-inventory`, and `--private-root` (repeatable). Default
  mode produces the unavailable/no-explicit-roots artifact without reading
  any private roots.

## Artifact

- Helper: `eval/bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory.py`
- Report: `artifacts/bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory/bea_v1_haae_r1_unified_private_trace_schema_feasibility_inventory_report.json`
