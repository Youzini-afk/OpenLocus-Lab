# OpenLocus v2 FRK-P2R Targeted Capture Repair

Status: `frk_p2r_capture_repair_complete_haae_a2_replay_authorized`

Public report: [`artifacts/frk_p2r_targeted_capture_repair/frk_p2r_targeted_capture_repair_report.json`](../../artifacts/frk_p2r_targeted_capture_repair/frk_p2r_targeted_capture_repair_report.json)

Evaluator: `eval/frk_p2r_targeted_capture_repair.py`

## Scope

FRK-P2R is an executable targeted capture repair authorized by FRK-P2. It regenerates richer private nested `openlocus.state_action_trace.v2` rows and repairs target-scoped coverage accounting for two blockers:

1. `state.candidate_pool` coverage was low.
2. `outcome.downstream_proxy` row-level missingness was high and all-row coverage was low.

This phase is not a new retrieval prototype and not a design/audit-only phase.

## Execution contract

- Default mode is unavailable/no-op unless `--confirm-private-output` is supplied.
- Private output rows are written only under ignored `runs/frk_p2r_targeted_capture_repair_private_*/`.
- The same FRK-P2 manifest shape, product-workflow families, fixed caps, and existing channel families are used: `bm25_text`, `symbol_regex`, and `existing_hybrid_retrieve`.
- Local bounded actions remain existing retrieval/search, `openlocus read`, and `openlocus citations validate`.
- The repair adds instrumentation only: candidate count, unique file count, rankpack arm/size/dedup/diversity, remaining read/validate budget, top1 source/channel, label-blind top1 role guess, and final downstream proxy at stop rows.
- Candidate-pool coverage is assessed only on rows after retrieval is available (`read_next`, `validate_now`, `stop`). Downstream proxy coverage is assessed on stop/final rows. Public reporting exposes both all-row and target-scoped coverage buckets.

## Result

The run produced aggregate-only public output:

- private episode bucket: `count_21_to_50`
- private row bucket: `count_gt_50`
- target-scoped `state.candidate_pool` coverage: `coverage_high`
- target-scoped candidate-pool label-blind feature coverage: `coverage_high`
- candidate miss/rank proxies: `not_available_pre_action`, not gold-derived
- target-scoped stop-row `outcome.downstream_proxy` coverage: `coverage_high`
- target-scoped unknown/missingness bucket: `count_0`
- all-row downstream proxy coverage remains `coverage_low`, by design, because non-final rows use `not_applicable_nonfinal`
- schema/privacy/label/currentness/EvidenceCore-separation checks: passed

## Stop/go

All positive HAAE-A2 gates passed, so the only authorized next phase is:

`haae_a2_offline_action_replay_smoke_over_frk_p2r_v2_rows`

Forbidden remain: new retrieval algorithm/channel family, candidate expansion beyond fixed caps, broad source scan, adaptive escalation, provider/model/network/CI, HAAE-A2 replay inside this phase, RPM-D2 training/model fitting/model scaling, runtime/default change, method/scale/winner/default claim, kernel hardening, raw/private trace publication, FRK-J/B/C, FRK-I revival, HAAE-SG/T, LDI-B easy continuation, and bounded repair route revival.
