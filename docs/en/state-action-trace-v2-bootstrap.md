# OpenLocus v2 TraceV2-A Product Workflow Trace Bootstrap

Status: `tracev2_a_bootstrap_complete_frk_p2_capture_expansion_authorized`

Public report: [`artifacts/state_action_trace_v2_bootstrap/state_action_trace_v2_bootstrap_report.json`](../../artifacts/state_action_trace_v2_bootstrap/state_action_trace_v2_bootstrap_report.json)

Evaluator: `eval/state_action_trace_v2_bootstrap.py`

## Scope

TraceV2-A is the first executable data-prep/bootstrap phase for trace-driven fast evidence acquisition. It converts and audits existing ignored/private Phase-5 product-workflow traces plus existing ignored/private Phase-8 bounded-repair prototype traces into strict `openlocus.state_action_trace.v2` rows.

This phase is not a schema-preflight chain and not a new retrieval experiment.

## Execution contract

- Default mode is unavailable/no-op unless private confirmations are supplied.
- Private inputs are limited to existing Phase-5 product-workflow traces/labels and existing Phase-8 prototype traces/labels, read only with `--confirm-private-input`.
- Private output rows are written only with `--confirm-private-output` under ignored `runs/state_action_trace_v2_bootstrap_private_*/`.
- The bootstrap performs conversion/audit only: no retrieval, search, read, citation validation, new candidates, source scan, task expansion, provider/model/network/CI, training/model fitting/RPM-D2, runtime/default change, kernel hardening, method/scale/winner/default claim, raw/private trace publication, or bounded-repair-route revival.

## TraceV2 schema

Converted private rows use schema version `openlocus.state_action_trace.v2` and require these top-level groups:

`schema_version`, `trace_id`, `episode_id`, `step_index`, `task`, `state`, `action`, `behavior_policy`, `observation`, `evidence_linkage`, `outcome`, `privacy_execution`, `source_lock`.

The `state` group is nested into `candidate_pool`, `rankpack`, `evidence_state`, `budget_state`, and `uncertainty_state`. The `observation` group nests observed cost buckets, and the `outcome` group nests downstream proxy buckets. Unknown legacy facts are represented explicitly as `unknown` or `not_observable_from_source_trace`; they are counted as missingness for critical-coverage gates.

The validator rejects unknown top-level keys, missing required groups, bad action enums, duplicate/non-monotonic steps, labels before action, label/gold leakage into state/action, post-action currentness in pre-action state, invented non-observable state facts, EvidenceCore linkage conflation with candidate state, and forbidden execution/privacy flags.

## Result

The conversion was schema-valid and privacy-safe, with aggregate-only public output:

- private output row bucket: `count_gt_50`
- private output episode bucket: `count_gt_50`
- action coverage: `expand_depth`, `read_next`, `validate_now`, and `stop`
- TraceV2 schema validation: passed
- label-after-action isolation: passed
- currentness leakage scan: passed
- critical field coverage: low; unknown/missingness bucket `count_gt_50`; coverage gaps dominate because legacy traces do not carry enough explicit workflow-family, candidate-pool detail, rankpack, budget, uncertainty, content-SHA/currentness, cost-token, and downstream-proxy state for safe offline replay authorization

## Stop/go

Authorized next phase: `frk_p2_workflow_v2_task_state_capture_expansion`.

Not authorized: HAAE-A2 replay over existing v2 rows, RPM-D2 training/model scaling, runtime/default change, new retrieval prototype, broad FRK repair, kernel hardening, retrieval/search/read/citation validation execution, candidate generation, source scan, provider/network/CI, method/scale/winner/default claims, raw/private trace publication, FRK-J/B/C, FRK-I revival, HAAE-SG/T, LDI-B easy continuation, or current bounded repair route revival.
