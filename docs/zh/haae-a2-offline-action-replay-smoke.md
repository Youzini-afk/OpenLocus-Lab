# OpenLocus v2 HAAE-A2 Offline Action Replay Smoke

状态：`haae_a2_offline_action_replay_smoke_complete_baseline_sufficient_stop`

公开报告：[`artifacts/haae_a2_offline_action_replay_smoke/haae_a2_offline_action_replay_smoke_report.json`](../../artifacts/haae_a2_offline_action_replay_smoke/haae_a2_offline_action_replay_smoke_report.json)

评估脚本：`eval/haae_a2_offline_action_replay_smoke.py`

## 范围

HAAE-A2 是只基于 existing FRK-P2R private nested `openlocus.state_action_trace.v2` rows 的 executable offline replay smoke。它只在 `--confirm-private-input` 后读取最新 ignored FRK-P2R rows，且不写入 private output。

本阶段不是 trace capture，不是 retrieval prototype，也不是 training/model fitting。它不执行 retrieval/search/read/citation validation，不生成 candidates，不 source scan，也不提出 runtime/default/method/scale/winner claim。

## Replay contract

- Replay 仅限 logged episodes 与 logged actions。
- Policies 只使用每一步可用的 pre-action `task`、`state`、`action`、`behavior_policy`、prior observations 与 budget fields。
- Final stop-row `outcome.downstream_proxy` 只在 replay action sequence 固定后用于 scoring。
- 如果 policy 在某一步选择了 logged episode 中不存在的 action，则标记为 `off_policy_not_evaluable`，且永不计为 success。
- 不合成 counterfactual outcomes。
- Same-budget gates 要求 action/read/validate 数量不超过 logged cap，且不引入 new action type/channel/candidate。

## Arms

Baselines：

- `logged_behavior_policy`
- `fixed_read_then_validate_then_stop`
- `fixed_read_then_stop`
- `fixed_stop_immediate`

Deterministic label-blind candidate policies：

- `budget_guarded_validate_policy`
- `evidence_uncertainty_policy`
- `candidate_pool_guard_policy`
- `support_need_policy`
- `currentness_guard_policy`
- `combined_budget_uncertainty_candidate_policy`

## 结果

本次 smoke 载入 private row bucket `count_gt_50` 与 private episode bucket `count_21_to_50`。Strict nested TraceV2 validation、leakage scans、deterministic label-blind policy validation、same-budget validation、EvidenceCore/currentness regression checks、read/validate budget regression checks 与 public privacy scans 均通过。

至少一个 candidate policy 在 `count_21_to_50` episodes 上可评估，但最佳 candidate policy 没有在 final downstream-proxy utility 上超过最佳 fixed baseline。因此结果是 baseline-sufficient，而不是 positive signal。

## Stop/go

仅授权 `stop_haae_a2_policy_route_baseline_sufficient`。

绝不直接授权：HAAE-A3 heldout design、RPM-D2、training/model fitting/model scaling、runtime/default changes、provider/model/network/CI、new retrieval/candidate expansion/source scan、kernel hardening、method/scale/winner/default claims、raw/private trace publication 或 closed-route revival。
