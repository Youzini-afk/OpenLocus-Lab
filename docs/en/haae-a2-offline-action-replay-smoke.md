# OpenLocus v2 HAAE-A2 Offline Action Replay Smoke

Status: `haae_a2_offline_action_replay_smoke_complete_baseline_sufficient_stop`

Public report: [`artifacts/haae_a2_offline_action_replay_smoke/haae_a2_offline_action_replay_smoke_report.json`](../../artifacts/haae_a2_offline_action_replay_smoke/haae_a2_offline_action_replay_smoke_report.json)

Evaluator: `eval/haae_a2_offline_action_replay_smoke.py`

## Scope

HAAE-A2 is an executable offline replay smoke over existing FRK-P2R private nested `openlocus.state_action_trace.v2` rows only. It reads the latest ignored FRK-P2R rows only after `--confirm-private-input` and writes no private output.

This phase is not trace capture, not a retrieval prototype, and not training/model fitting. It executes no retrieval/search/read/citation validation, generates no candidates, performs no source scan, and makes no runtime/default/method/scale/winner claim.

## Replay contract

- Replay is limited to logged episodes and logged actions.
- Policies use only pre-action `task`, `state`, `action`, `behavior_policy`, prior observations, and budget fields available at each step.
- Final stop-row `outcome.downstream_proxy` is used only after a replay action sequence is fixed for scoring.
- If a policy selects an action absent from the logged episode at that step, it is marked `off_policy_not_evaluable` and never counted as success.
- No counterfactual outcomes are synthesized.
- Same-budget gates require no more actions, reads, or validations than the logged cap, and no new action type/channel/candidate.

## Arms

Baselines:

- `logged_behavior_policy`
- `fixed_read_then_validate_then_stop`
- `fixed_read_then_stop`
- `fixed_stop_immediate`

Deterministic label-blind candidate policies:

- `budget_guarded_validate_policy`
- `evidence_uncertainty_policy`
- `candidate_pool_guard_policy`
- `support_need_policy`
- `currentness_guard_policy`
- `combined_budget_uncertainty_candidate_policy`

## Result

The smoke loaded private row bucket `count_gt_50` and private episode bucket `count_21_to_50`. Strict nested TraceV2 validation, leakage scans, deterministic label-blind policy validation, same-budget validation, EvidenceCore/currentness regression checks, read/validate budget regression checks, and public privacy scans passed.

At least one candidate policy was evaluable on `count_21_to_50` episodes, but the best candidate policy did not beat the best fixed baseline on final downstream-proxy utility. The result is baseline-sufficient rather than positive signal.

## Stop/go

Only `stop_haae_a2_policy_route_baseline_sufficient` is authorized.

Route closeout: the current v2 trace-driven HAAE policy line is closed under current evidence. The route-level authorized next value is `none_for_current_v2_trace_driven_policy_line`; future reopening requires `new_product_workflow_pain_or_new_trace_evidence_decision`, not another HAAE-A2 tweak or decomposition loop.

Never authorized directly: HAAE-A3 heldout design, RPM-D2, training/model fitting/model scaling, runtime/default changes, provider/model/network/CI, new retrieval/candidate expansion/source scan, kernel hardening, method/scale/winner/default claims, raw/private trace publication, or closed-route revival.
