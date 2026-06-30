# BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition Route Design / Schema Preflight

Date: 2026-06-30

BEA-v1-HAAE-R0 is the **public-only design/schema preflight** for the next
acquisition route, opened by the N10ET close-out (checkpoint `26d817e`). It is
**not** an execution phase. HAAE-R0 reads **only** public artifacts/docs/current
conclusions/research logs/README and git metadata:

- the committed N10ET public aggregate report (the close-out design/decision
  that authorized HAAE-R0);
- the N10ET evaluator for schema/status validation only (never executed — no
  rerun/recompute);
- the N10ET EN/ZH docs, EN/ZH current-research-conclusions, EN/ZH
  research-log/summary, and README public readback;
- git metadata: the `26d817e` checkpoint that recorded the N10ET result.

Forbidden: any private reads (project-private roots, temporary rerun paths, CI
raw logs, repo clones, raw candidates/orders/labels/paths/queries/tasks/repos,
per-task diagnostics), any CI rerun, any retrieval/recompute, any
candidate generation/materialization, any arm scoring, any selector/reranker
execution, any threshold tuning, any promotion, any runtime/default change, any
method/downstream/heldout claim, any OpenLocus execution, any
provider/embedding network call, any P5/BEA-v1-A authorization, or any
runtime/default promotion.

## N10ET source lock

```text
n10et checkpoint: 26d817e
n10et status: n10et_public_safety_probe_design_decision_complete_haae_r0_authorized
n10et next allowed phase: BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition
                           Route Design / Schema Preflight
haae r0 authorized by n10et: true (haae_r0_design_only_schema_preflight_authorized_bool)
haae r0 execution authorized by n10et: false (haae_r0_execution_authorized_bool)
bea_v1_a authorized by n10et: false (bea_v1_a_authorized_bool)
p5 authorized by n10et: false (p5_authorized_bool)
selector/reranker authorized by n10et: false (selector_reranker_authorized_bool)
runtime/default change authorized by n10et: false
n10et haae r0 non-identity booleans: all true (not_bea_v1_a, not_selector_only,
  not_selector_reranker_execution, not_p5, not_runtime_default_promotion)
n10et source locked: true
no_ci_rerun / no_retrieval / no_recompute / no_private_input_read: true
```

## Result

```text
status: haae_r0_design_schema_preflight_complete_haae_r1_authorized
self-test: 132 / 132
forbidden scan: pass
private input reads: 0
retrieval executions: 0
recomputes: 0
CI reruns: 0
candidate generations: 0
arm scorings: 0
openlocus executions: 0
n10et source locked: true (checkpoint 26d817e)
next allowed phase: BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory
```

## HAAE-R0 explicit non-identities

HAAE-R0 is explicitly **not** any of the following (every control-plane record
and the stop/go record carries the corresponding non-identity boolean):

- **not BEA-v1-A** — it is not the coverage-preserving selector route.
- **not selector-only** — it is not a selector-only design.
- **not selector/reranker execution** — it does not execute a selector or
  reranker.
- **not P5** — it is not the P5 selector/reranker phase.
- **not runtime/default promotion** — it does not change runtime/default
  behavior.

## Route architecture (4 hierarchical layers, design-only)

The HAAE route is designed as a 4-layer hierarchical, actionable-evidence
acquisition route. Each layer preserves `EvidenceCore` and abstains when
current-source evidence is unavailable. No layer is executed in HAAE-R0.

1. **source_acquisition** — the anchor/source-acquisition layer defines how
   evidence-acquisition actions obtain candidate sources from a current source
   surface (identifier-normalized BM25, exact search, symbol, graph). It
   abstains when no current-source evidence is available and emits only
   aggregate candidate-pool buckets (no raw candidates/paths/queries).
2. **rank_pack_depth_to_head** — the rank/pack depth-to-head layer defines how
   deep candidates are packed into the head (novel-vs-old-pool-first, bounded
   merge-order, difference-aware guarded/else-full). It operates on aggregate
   rank/pack buckets only and does not execute a selector or reranker.
3. **span_projection** — the span-projection layer defines how spans are
   projected over acquired content (symmetric/asymmetric span windows,
   shape-gated expansion). It emits only aggregate span-overlap buckets and
   abstains when the current source cannot yield a citation-valid span.
4. **scheduler_operating_point** — the scheduler-operating-point layer defines
   how retrieval actions are scheduled under a cost/budget gate (the BEA-v1 P4
   scheduler operating-point contract). It selects an operating point on the
   action-cost frontier and abstains when the operating point would violate
   EvidenceCore or exceed budget. Design-only here; no scheduler is executed.

## Unified private trace schema spec (10 groups, design-only)

HAAE-R0 designs a unified private trace schema with 10 groups. Each group is
**private-root-only** and **aggregate-bucket-only**: no raw per-task
paths/queries/candidates/labels/spans/ranks are ever released. No replay,
no scoring, no retrieval, no candidate generation in HAAE-R0.

| # | Group | Aggregate columns (bucket-only) |
|---|---|---|
| 0 | task_identity | anonymous_task_id, repo_bucket, language_bucket |
| 1 | anchor_source | anchor_kind_bucket, acquisition_cost_bucket |
| 2 | candidate_pool | candidate_count_bucket, depth_distribution_bucket |
| 3 | rank_pack | topk_pack_bucket, novel_vs_old_pool_bucket |
| 4 | span_projection | span_window_bucket, span_overlap_bucket |
| 5 | scheduler_action | scheduled_action_bucket, action_cost_bucket |
| 6 | evidence_core | path_bucket, line_range_bucket, content_sha_bucket, score_bucket, why_bucket, channels_bucket |
| 7 | arm_assignment | arm_bucket, budget_bucket |
| 8 | outcome_metric | citation_validity_bucket, file_recovery_topk_bucket, lost_baseline_top10_bucket |
| 9 | safety_probe_signal | full_guard_diffaware_loss_bucket, risk_bucket_signal |

## Public aggregation contract (4 aggregations, design-only)

The unified private trace schema aggregates into public buckets via 4
aggregation contracts (all aggregate-bucket-only, no raw release):

- **task_count_aggregate** — public_task_count / scored_task_count /
  task_with_gold_count / repo_count (from task_identity + candidate_pool).
- **arm_aggregate** — per-arm top10/top20/top50/top100 file-recovery and
  lost_baseline_top10 (from arm_assignment + outcome_metric).
- **risk_bucket_aggregate** — risk_bucket task_count and full/guard/diffaware
  loss counts (from safety_probe_signal + outcome_metric).
- **citation_aggregate** — citation_valid_count / citation_total_count (from
  evidence_core + outcome_metric).

## Arm specs (5 same-budget arms, design-only)

Five same-budget arms are specified. No arm is executed or scored in HAAE-R0;
no tuning in HAAE-R0. All aggregate-bucket-only.

- **BM25_same_budget** — same-budget BM25 baseline arm (the B16-F/N10ES
  comparator).
- **RRF_same_budget** — same-budget reciprocal-rank-fusion comparator arm.
- **BEA_v0.3_frozen** — the frozen BEA v0.3 policy arm (frozen; no tuning).
- **V1_sched_span** — BEA-v1 scheduler over span projection arm.
- **V1_sched_span_rank** — BEA-v1 scheduler over span + rank/pack arm.

## Metric specs (6 aggregate metrics, design-only)

Six aggregate metrics are specified, all aggregate-bucket-only, no per-task, no
recompute in HAAE-R0:

- citation_validity, file_recovery_top_k, lost_baseline_top10,
  risk_bucket_signal, span_overlap, action_cost.

## Held-out protocol (design-only)

The held-out protocol enforces `overlap_zero` between any future HAAE
execution training/held-out split and the closed N10ES/N10ER public held-out
sample. Gold is never used for policy selection; publication is
aggregate-bucket-only. No split is materialized in HAAE-R0; no held-out
generalization claim is made.

## Stop rules (4 abstain rules, design-only)

Four stop rules preserve `EvidenceCore`:

1. **abstain_when_current_source_unavailable** — abstain when the current
   source cannot yield candidate evidence.
2. **stop_when_citation_invalid** — stop when citation-validation falls below
   threshold.
3. **stop_when_budget_exhausted** — stop when the action-cost budget is
   exhausted.
4. **stop_when_evidence_core_violated** — stop when an action would violate
   EvidenceCore.

## Synthetic validator (embedded synthetic fixture, design-only)

An embedded synthetic fixture (4 synthetic tasks with aggregate buckets only)
validates that the schema/arm/metric/heldout/stop-rule/HAAE-R1 contracts are
machine-readable and self-consistent. The fixture is **not** real data, **not**
a replay, **not** retrieval, **not** candidate generation; it exists only to
prove the control-plane is non-empty and internally consistent. The validator
runs in-process; `validates_schema_bool`, `validates_arms_bool`,
`validates_metrics_bool`, `validates_heldout_bool`, `validates_stop_rules_bool`,
and `validates_haae_r1_contract_bool` are all `true`.

## HAAE-R1 contract (design-only, authorizes only feasibility inventory)

HAAE-R0 designs and authorizes **only** the next phase: **BEA-v1-HAAE-R1 —
Unified Private Trace Schema Feasibility Inventory**. HAAE-R1 is explicitly
limited to:

- a feasibility inventory of the unified private trace schema (whether the 10
  schema groups can be populated from explicit private roots);
- **explicit project-private root buckets only**;
- **aggregate buckets only**;
- **no replay, no scoring, no retrieval, no candidate generation**;
- **no execution of any HAAE layer**;
- it is a feasibility check, **not** execution.

`feasibility_inventory_only_bool=true`, `no_execution_of_haae_layers_bool=true`,
`execution_authorized_bool=false`.

## Risk controls

| Risk | Mitigation |
|---|---|
| HAAE-R0 drift into selector / P5 / runtime | every control-plane record carries the non-identity booleans; selector_reranker_authorized_bool=false; bea_v1_a_authorized_bool=false; p5_authorized_bool=false; runtime_default_change_authorized_bool=false |
| HAAE-R0 drift into execution | every record carries design_only_bool=true, schema_preflight_bool=true, execution_authorized_bool=false; the synthetic validator runs in-process on an embedded fixture only and carries no_replay/no_retrieval/no_candidate_generation/no_scoring=true |
| HAAE-R0 empty control-plane | the artifact carries concrete machine-readable records: 4 route architecture layers, 10 schema groups, 4 aggregation contracts, 5 arm specs, 6 metric specs, 1 heldout protocol, 4 stop rules, and a synthetic validator with an embedded 4-task fixture that validates all contracts in-process |
| HAAE-R1 scope creep beyond feasibility inventory | the HAAE-R1 contract record explicitly limits HAAE-R1 to feasibility_inventory_only_bool=true, private_roots_only_bool=true, aggregate_buckets_only_bool=true, no_replay/no_scoring/no_retrieval/no_candidate_generation=true, no_execution_of_haae_layers_bool=true |
| private diagnostic leakage | HAAE-R0 reads only public aggregate artifacts/docs/git metadata; forbidden_scan blocks raw per-task/paths/orders/labels keys and private rerun paths; every schema group carries aggregate_buckets_only_bool=true, private_root_only_bool=true, no_raw_release_bool=true |
| runtime/default creep | runtime_default_change_authorized_bool=false; any HAAE route remains opt-in/eval-only; no runtime or default change |

## Pass/fail gates (27 audit gates, aggregate-only)

1. `n10et_public_source_locked` — N10ET public report locked, status + all locked fields match.
2. `n10et_status_locked` — N10ET status matches the locked value.
3. `n10et_haae_r0_authorized_match` — N10ET authorized HAAE-R0 design/schema preflight.
4. `n10et_haae_r0_execution_false_match` — N10ET did not authorize HAAE-R0 execution.
5. `n10et_bea_v1_a_false_match` — N10ET did not authorize BEA-v1-A.
6. `n10et_non_identity_match` — N10ET carried the HAAE-R0 non-identity booleans.
7. `haae_r0_no_threshold_tuning` — frozen thresholds unchanged.
8. `haae_r0_no_method_winner_claim` — no method-winner claim.
9. `haae_r0_no_runtime_default_change` — close-out stays public/eval-only.
10. `haae_r0_no_promotion_or_frozen_rule_change` — no promotion, no rule change.
11. `haae_r0_no_ci_rerun_retrieval_recompute_candidate_generation` — no CI rerun, retrieval, recompute, or candidate generation.
12. `haae_r0_no_private_input_read` — no private dirs/logs/clones/raw candidates/orders/labels/paths/queries/tasks/repos or per-task diagnostics read.
13. `haae_r0_no_selector_reranker_no_p5_no_bea_v1_a` — no selector/reranker, no P5, no BEA-v1-A.
14. `haae_r0_no_arm_scoring` — no arm scoring.
15. `haae_r0_no_openlocus_execution` — no OpenLocus execution.
16. `haae_r0_route_architecture_design_only` — all 4 route architecture layers design-only, no execution.
17. `haae_r0_schema_groups_concrete` — 10 unified private schema groups present.
18. `haae_r0_arm_specs_concrete` — 5 arm specs present.
19. `haae_r0_metric_specs_concrete` — 6 metric specs present.
20. `haae_r0_synthetic_validator_passes` — the embedded synthetic validator passes.
21. `haae_r0_non_identity_gate` — HAAE-R0 non-identity booleans all true.
22. `docs_readback_match_gate` — EN/ZH HAAE-R0 + N10ET docs match.
23. `readme_readback_match_gate` — README matches.
24. `current_conclusions_match_gate` — EN/ZH current conclusions match.
25. `research_log_match_gate` — EN/ZH research logs match.
26. `research_summary_match_gate` — EN/ZH research summaries match.
27. `haae_r1_contract_feasibility_inventory_only_gate` — HAAE-R1 contract limits to feasibility inventory only.

All gates are aggregate-only with `gate_uses_gold_for_policy_bool=false`,
`gate_performs_ci_rerun_bool=false`, `gate_reads_private_input_bool=false`.

## Claim boundary

HAAE-R0 is public-only, aggregate-buckets-only, design-only, and
schema-preflight-only. All execution, rerun, retrieval, recompute, candidate
generation, arm scoring, OpenLocus execution, tuning, promotion,
runtime/default, method-winner, downstream/scaled retrieval, raw diagnostic
publication, selector/reranker, provider/model network, network-run, and
gold-for-policy fields are `false`. `candidate_generation_bool=false`,
`arm_scoring_bool=false`, `openlocus_execution_bool=false`,
`haae_r0_execution_authorized_bool=false`,
`haae_r1_execution_authorized_bool=false`,
`haae_r1_replay_authorized_bool=false`,
`haae_r1_scoring_authorized_bool=false`,
`haae_r1_retrieval_authorized_bool=false`,
`haae_r1_candidate_generation_authorized_bool=false`. The HAAE-R0 non-identity
booleans (`haae_r0_not_bea_v1_a_bool`, `haae_r0_not_selector_only_bool`,
`haae_r0_not_selector_reranker_execution_bool`, `haae_r0_not_p5_bool`,
`haae_r0_not_runtime_default_promotion_bool`) are all `true`.

## Stop/go

HAAE-R0 authorizes **only** the **BEA-v1-HAAE-R1 Unified Private Trace Schema
Feasibility Inventory** handoff (public-only, design-only, explicit private
roots only, aggregate buckets only, no replay/scoring/retrieval/candidate
generation):
`haae_r1_unified_private_trace_schema_feasibility_inventory_authorized_bool=true`,
`haae_r1_execution_authorized_bool=false`,
`haae_r1_replay_authorized_bool=false`,
`haae_r1_scoring_authorized_bool=false`,
`haae_r1_retrieval_authorized_bool=false`,
`haae_r1_candidate_generation_authorized_bool=false`. It does **not** authorize:
N10ET re-run, any HAAE-R0 execution, any execution, rerun, retrieval, recompute,
candidate generation, arm scoring, OpenLocus execution, threshold tuning, new
policy experiments, frozen-rule changes, guard/full/diffaware promotion,
runtime/default changes, method-winner claims, downstream/scaled retrieval, raw
diagnostic publication, CI variant execution, selector/reranker, BEA-v1-A, P5,
provider/model network, or network runs. All such stop/go fields are `false`.

## Workflow

- Design/schema-preflight helper:
  `eval/bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight.py`
- The helper exposes `--self-test`, `--validate-report`, and `--out`. It reads
  only the N10ET public report and public docs, and performs no
  execution/rerun/recompute/candidate generation/arm scoring/OpenLocus execution.

## Artifact

- Helper: `eval/bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight.py`
- Report: `artifacts/bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight/bea_v1_haae_r0_hierarchical_actionable_evidence_acquisition_design_schema_preflight_report.json`
