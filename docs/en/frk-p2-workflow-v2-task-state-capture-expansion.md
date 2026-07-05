# OpenLocus v2 FRK-P2 Workflow V2 Task-State Capture Expansion

Status: `frk_p2_workflow_v2_capture_complete_targeted_capture_repair_only`

Public report: [`artifacts/frk_p2_workflow_v2_task_state_capture_expansion/frk_p2_workflow_v2_task_state_capture_expansion_report.json`](../../artifacts/frk_p2_workflow_v2_task_state_capture_expansion/frk_p2_workflow_v2_task_state_capture_expansion_report.json)

Evaluator: `eval/frk_p2_workflow_v2_task_state_capture_expansion.py`

## Scope

FRK-P2 is an executable TraceV2 capture expansion authorized by TraceV2-A. It directly emits strict nested `openlocus.state_action_trace.v2` rows for a predeclared bounded product-workflow manifest.

This is trace capture only. It is not a design/audit-only phase, not a new retrieval prototype, and not RPM/HAAE training or replay.

## Execution contract

- Default mode is unavailable/no-op unless `--confirm-private-output` is supplied.
- Private input is not required by default; no private labels or task alignment are read.
- Private output rows are written only under ignored `runs/frk_p2_workflow_v2_capture_private_*/`.
- Local actions are bounded to the existing channel families `bm25_text`, `symbol_regex`, and `existing_hybrid_retrieve`, with fixed caps and no adaptive escalation.
- The phase may execute local OpenLocus retrieval/search, `openlocus read`, and `openlocus citations validate` for trace capture, but it does not add algorithms/channels, expand candidates beyond caps, scan broadly, call providers/network/CI, train/model-scale/RPM-D2, replay HAAE-A2, change runtime/defaults, harden kernels, or publish raw/private traces.

## Result

The run produced aggregate-only public output:

- private episode bucket: `count_21_to_50`
- private row bucket: `count_gt_50`
- workflow family, query type, budget class, wrong-file-cost, expected-primary-role, and support-role buckets: `count_3_to_5`
- action coverage: `retrieve_candidates`, `read_next`, `validate_now`, and `stop`
- TraceV2 schema validation, label-after-action isolation, currentness leakage scan, EvidenceCore/candidate-state separation, and privacy scan: passed
- critical nested coverage: mostly high, but candidate-pool and downstream-proxy coverage remain low and unknown/missingness remains `count_gt_50`

## Stop/go

HAAE-A2 replay is **not** authorized from this run because the positive gate requires medium/high critical nested coverage for all groups and unknown missingness below `count_gt_50`.

Authorized next phase: `targeted_frk_p2_workflow_v2_capture_repair_only`.

Not authorized: new retrieval algorithm/channel family, broad source scan, candidate expansion beyond caps, provider/model/network/CI, RPM-D2 training/model scaling, HAAE-A2 replay/training inside this phase, runtime/default change, method/scale/winner/default claims, kernel hardening, raw/private trace publication, FRK-J/B/C, FRK-I revival, HAAE-SG/T, LDI-B easy continuation, or bounded repair route revival.
