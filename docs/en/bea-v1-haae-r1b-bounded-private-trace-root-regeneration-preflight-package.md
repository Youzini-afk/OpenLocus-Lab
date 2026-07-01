# BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package

Date: 2026-06-30

BEA-v1-HAAE-R1B is the **public-only, design-only preflight package** for
bounded private trace root regeneration, opened by the HAAE-R1A coverage gap
design (checkpoint `e54d1b4`, status
`haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized`).

R1B is **not** an execution phase. It must not: read private data, write
private data, regenerate roots, execute replay/scoring/retrieval/candidate
generation/HAAE layers, run CI/network/clone/build/search, or authorize
BEA-v1-A/P5/selector/runtime/default. It is explicitly **not** BEA-v1-A, not
selector-only, not selector/reranker execution, not P5, not a runtime/default
promotion.

## Allowed public inputs

- the committed HAAE-R1A public aggregate report (the coverage gap design
  that authorized R1B);
- the HAAE-R1/R0/N10ET public aggregate reports (upstream locks);
- the HAAE-R1A/R1/R0/N10ET evaluators for constants only (never executed);
- public aggregate artifacts/docs used by R1A (FD1, P4L, N1, N2, N10-series /
  mechanism synthesis) for recipe classification;
- the README/current-research-conclusions/research-log/research-summary public
  readback;
- git metadata: the `e54d1b4` checkpoint that recorded the HAAE-R1A result.

## HAAE-R1A source lock

```text
haae r1a checkpoint: e54d1b4
haae r1a status: haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized
haae r1a next allowed phase: BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package
haae r1b authorized by haae r1a: true (haae_r1b_bounded_private_trace_root_regeneration_preflight_authorized_bool)
haae r1b design only: true
haae r1b execution / private_read / replay / scoring / retrieval / candidate_generation: false
haae r0 non-identity booleans: all true
haae r1a source locked: true
no_ci_rerun / no_retrieval / no_recompute / no_private_input_read: true
no_replay / no_scoring / no_candidate_generation / no_haae_layer_execution: true
no_root_regeneration / no_network_run / no_clone_build_search: true
```

## Result

```text
status: haae_r1b_bounded_private_trace_root_regeneration_preflight_package_complete_r1c_smoke_authorized
self-test: 108 / 108
forbidden scan: pass
private input reads: 0
root regenerations: 0
replays: 0
haae layer executions: 0
network runs: 0
clone/build/search: false
haae r1a source locked: true (checkpoint e54d1b4)
recipe catalog covers all 10 groups: true
operator checklist present: true
private output contract present: true
public manifest schema present: true
r1c bounded contract present: true
next allowed phase: BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke
```

## Recipe catalog (10 recipes, covers all 10 HAAE-R0 schema groups)

| # | Group | Recipe | Kind |
|---|---|---|---|
| 0 | task_identity | fd1_decomposition_replay_recipe | decomposition_replay |
| 1 | anchor_source | normalized_bm25_anchor_recovery_recipe | public_aggregate_derivation |
| 2 | candidate_pool | n10eo_diagnostic_rerun_recipe | diagnostic_rerun |
| 3 | rank_pack | n2_rank_pack_decomposition_recipe | public_aggregate_derivation |
| 4 | span_projection | span_window_repair_branch_recipe | public_aggregate_derivation |
| 5 | scheduler_action | p4l_scheduler_replay_recipe | scheduler_replay |
| 6 | evidence_core | fd1_plus_n10er_evidence_core_recipe | hybrid_decomposition_replay_plus_public_aggregate |
| 7 | arm_assignment | p4l_arm_outcome_5_arms_recipe | arm_outcome_replay |
| 8 | outcome_metric | n10er_n10es_outcome_metric_recipe | public_aggregate_derivation |
| 9 | safety_probe_signal | safety_probe_lineage_recipe | public_aggregate_derivation |

## Operator checklist (5 safe operators)

1. **explicit_opt_in_private_root_enumeration** — enumerate explicitly supplied
   private root buckets under explicit opt-in. Bounded depth, no symlink escape.
2. **fd1_decomposition_replay_operator** — replay FD1 decomposition to regenerate
   private rows. Private output only; public manifest count buckets only.
3. **p4l_scheduler_replay_operator** — replay frozen P4 scheduler to regenerate
   private arm-outcome rows. Private output only; public manifest count only.
4. **public_aggregate_derivation_operator** — derive public aggregate buckets
   from existing public artifacts. No private reads, no replay.
5. **public_manifest_writer_operator** — write the public manifest (aggregate
   count buckets only) from private output. No raw release.

## Private output contract

3 contracts: `private_output_only` (private rows to explicit opt-in output
only), `public_manifest_count_only` (public artifact carries count buckets
only), `bounded_recipe_only` (R1C recipes bounded by R1B catalog; no unbounded
replay/retrieval/candidate generation).

## Public manifest schema

5 fields: `anonymous_recipe_id` (opaque_id), `private_row_count_bucket`
(ordinal), `group_coverage_map_bucket` (categorical), `manifest_hash_bucket`
(opaque_hash), `no_raw_release_bool` (bool). All aggregate-bucket-only.

## R1C bounded contract

R1C is a bounded private trace root regeneration smoke. It requires explicit
opt-in, produces private output only, publishes public manifest count buckets
only, and is bounded by the recipe catalog from R1B. Unbounded
replay/retrieval/candidate generation/scoring/selector/BEA-v1-A/P5/runtime are
all false. R1C is separately implemented/reviewed; R1B itself executes nothing.

## Boundary

HAAE-R1B is explicitly **not** BEA-v1-A, not selector-only, not
selector/reranker execution, not P5, not a runtime/default promotion, not a
HAAE-layer execution, not a replay, not a scoring, not a retrieval, not a
candidate generation, not a root regeneration. All such claim-boundary and
stop/go fields are `false`.

## Stop/go

Pass → authorizes **only** BEA-v1-HAAE-R1C Bounded Private Trace Root
Regeneration Smoke (design-only, separately implemented/reviewed):
`haae_r1c_bounded_private_trace_root_regeneration_smoke_authorized_bool=true`,
`haae_r1c_design_only_bool=true`, `haae_r1c_execution_authorized_bool=false`,
`haae_r1c_bounded_recipe_only_bool=true`,
`haae_r1c_unbounded_replay_authorized_bool=false`, etc.

## Workflow

- Preflight helper:
  `eval/bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package.py`
- The helper exposes `--self-test`, `--validate-report`, `--out`, and
  `--haae-r1a-report`. It reads only the HAAE-R1A public report and public
  docs; performs no execution, no private reads, no root regeneration.

## Artifact

- Helper: `eval/bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package.py`
- Report: `artifacts/bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package/bea_v1_haae_r1b_bounded_private_trace_root_regeneration_preflight_package_report.json`
