# BEA-v1-HAAE-R1A Private Trace Coverage Gap Design

Date: 2026-06-30

BEA-v1-HAAE-R1A is the **public-only design** phase that responds to the
HAAE-R1 coverage gap (checkpoint `2ea77da`, status
`haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots`). It is
**not** an execution phase: no private reads, no root regeneration, no
replay/scoring/retrieval/candidate generation/HAAE-layer execution/CI/network/
clone. It is explicitly **not** BEA-v1-A, not selector-only, not
selector/reranker execution, not P5, not a runtime/default promotion.

## Inputs allowed (public only)

- the committed HAAE-R1 public aggregate report (confirmed all 10 groups
  `not_present`);
- the committed HAAE-R0 public aggregate report (designed the 10 groups);
- the N10ET public aggregate report (the close-out design/decision);
- the HAAE-R1/R0/N10ET evaluators for constants only (never executed);
- public artifacts/docs for FD1, P4L, N1, N2, N10-series / mechanism synthesis
  to classify source option buckets;
- the HAAE-R1/R0 EN/ZH docs, EN/ZH current-research-conclusions, EN/ZH
  research-log/summary, and README public readback;
- git metadata: the `2ea77da` checkpoint that recorded the HAAE-R1 result.

Forbidden: any traversal of ignored project-private namespaces, temporary
private output namespaces, ignored roots, `target`, `runs`, clones; any private reads; any root regeneration; any
replay/scoring/retrieval/candidate generation/HAAE-layer execution; any CI
rerun; any network; any clone/build/search; any BEA-v1-A/P5/selector/runtime/
default.

## HAAE-R1 source lock

```text
haae r1 checkpoint: 2ea77da
haae r1 status: haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots
haae r1 next allowed phase: BEA-v1-HAAE-R1A Private Trace Coverage Gap Design
haae r2 authorized by haae r1: false (haae_r2_feasibility_gated_offline_trace_join_design_authorized_bool)
haae r1 execution / replay / scoring / retrieval / candidate_generation: false
haae r1 coverage: unavailable (all 10 groups not_present)
haae r0 checkpoint: 854fc2e (upstream)
n10et checkpoint: 26d817e (upstream)
haae r0 non-identity booleans: all true
haae r1 source locked: true
no_ci_rerun / no_retrieval / no_recompute / no_private_input_read: true
no_replay / no_scoring / no_candidate_generation / no_haae_layer_execution: true
no_root_regeneration / no_network_run / no_clone_build_search: true
```

## Result

```text
status: haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized
self-test: 112 / 112
forbidden scan: pass
private input reads: 0
retrieval executions: 0
recomputes: 0
CI reruns: 0
candidate generations: 0
arm scorings: 0
openlocus executions: 0
replays: 0
haae layer executions: 0
root regenerations: 0
network runs: 0
clone/build/search: false
haae r1 source locked: true (checkpoint 2ea77da)
10 schema groups accounted: true
source option count: 10
bounded regeneration designs: 5
root manifest schema fields: 6
next allowed phase: BEA-v1-HAAE-R1B Bounded Private Trace Root Regeneration Preflight Package
```

## 10 schema groups coverage gap

| # | Group | Critical | HAAE-R1 Coverage | Source Option | Evidence Strength |
|---|---|---|---|---|---|
| 0 | task_identity | yes | not_present | fd1_private_decomposition_manifest | strong |
| 1 | anchor_source | no | not_present | n10dw_normalized_bm25_recovery_mechanism | partial |
| 2 | candidate_pool | yes | not_present | n10eo_private_diagnostic_rerun_mechanism | strong |
| 3 | rank_pack | no | not_present | n2_rank_pack_actionability_decomposition | strong |
| 4 | span_projection | no | not_present | n10aa_to_n10bn_span_window_repair_branch | strong |
| 5 | scheduler_action | no | not_present | p4l_private_arm_outcome_manifest | strong |
| 6 | evidence_core | yes | not_present | fd1_private_decomposition_plus_n10er_citation | strong |
| 7 | arm_assignment | yes | not_present | p4l_private_arm_outcome_5_arms | strong |
| 8 | outcome_metric | yes | not_present | n10er_n10es_public_arm_aggregates | strong |
| 9 | safety_probe_signal | no | not_present | n10eq_n10er_n10es_n10et_safety_probe_lineage | strong |

All 10 groups have at least one source option with `public_evidence_strong` or
`public_evidence_partial`. 9 groups have `public_evidence_strong`; 1 group
(`anchor_source`) has `public_evidence_partial`.

## Bounded regeneration design

5 bounded regeneration designs:

1. **explicit_opt_in_private_root_enumeration** — regeneration requires
   explicit opt-in via `--allow-private-inventory --private-root <path>`. No
   implicit private root enumeration. No traversal outside explicitly supplied project-private root buckets or
   temporary private output buckets. Bounded depth, no symlink escape.
2. **fd1_private_decomposition_regeneration** — regenerate FD1 private
   decomposition rows by replaying the FD1 decomposition under explicit
   opt-in. Produces private rows in a temporary private output bucket only; public artifact carries
   manifest count buckets only. Source groups: task_identity, evidence_core.
3. **p4l_private_arm_outcome_regeneration** — regenerate P4L private
   arm-outcome rows by replaying the frozen P4 scheduler on the locked
   272-record non-Python denominator. Produces private arm-outcome rows in a temporary private output bucket only. Source groups: scheduler_action, arm_assignment,
   outcome_metric.
4. **n10eo_private_diagnostic_rerun_regeneration** — regenerate N10EO private
   diagnostic rerun. Produces private diagnostic rows in a temporary private output bucket only;
   public artifact carries aggregate mechanism buckets only. Source groups:
   candidate_pool, rank_pack, safety_probe_signal.
5. **n10er_public_ci_replay_regeneration** — regenerate N10ER public CI safety
   probe by replaying the bounded public CI canary under explicit opt-in with
   network enabled. Source groups: outcome_metric, safety_probe_signal.

## Root manifest schema design

6 manifest schema fields: `anonymous_root_id` (opaque_id_bucket),
`root_present_bool` (bool_bucket), `file_count_bucket` (ordinal_bucket),
`extension_distribution_bucket` (categorical_bucket),
`group_coverage_map_bucket` (categorical_bucket), `no_raw_release_bool`
(bool_bucket). All aggregate-bucket-only; no raw paths/filenames.

## Decision

**Pass** — source lock passes, HAAE-R1 unavailable/no roots confirmed,
HAAE-R2 false, all 10 groups accounted, at least one source option
`public_evidence_strong`/`partial` (9 strong, 1 partial), bounded regeneration
design and root manifest schema present, docs/readback pass, no private/
execution. Authorizes **only** BEA-v1-HAAE-R1B Bounded Private Trace Root
Regeneration Preflight Package (design-only, no execution/private read/
replay/scoring/retrieval/candidate generation).

## Boundary

HAAE-R1A is explicitly **not** BEA-v1-A, not selector-only, not
selector/reranker execution, not P5, not a runtime/default promotion, not a
HAAE-layer execution, not a replay, not a scoring, not a retrieval, not a
candidate generation, not a root regeneration. All such claim-boundary and
stop/go fields are `false`.

## Stop/go

Pass → authorizes **only** BEA-v1-HAAE-R1B Bounded Private Trace Root
Regeneration Preflight Package (design-only):
`haae_r1b_bounded_private_trace_root_regeneration_preflight_authorized_bool=true`,
`haae_r1b_design_only_bool=true`, `haae_r1b_execution_authorized_bool=false`,
`haae_r1b_private_read_authorized_bool=false`,
`haae_r1b_replay_authorized_bool=false`, etc.

No-go → closeout: explicit roots required; no further phase authorized.

## Workflow

- Design helper: `eval/bea_v1_haae_r1a_private_trace_coverage_gap_design.py`
- The helper exposes `--self-test`, `--validate-report`, `--out`, and
  `--haae-r1-report`. It reads only the HAAE-R1 public report and public docs;
  performs no execution, no private reads, no root regeneration.

## Artifact

- Helper: `eval/bea_v1_haae_r1a_private_trace_coverage_gap_design.py`
- Report: `artifacts/bea_v1_haae_r1a_private_trace_coverage_gap_design/bea_v1_haae_r1a_private_trace_coverage_gap_design_report.json`
