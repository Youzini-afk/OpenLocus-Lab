# BEA-v1-HAAE-S Action Scheduler Smoke

状态：已实现。Self-test：`57/57`。

Public artifact：[`bea_v1_haae_s_action_scheduler_smoke_report.json`](../../artifacts/bea_v1_haae_s_action_scheduler_smoke/bea_v1_haae_s_action_scheduler_smoke_report.json)。

## Contract

- Source locks：FRK-F checkpoint `63528e8`，status `frk_f_stop_current_frk_b_c_pack_route_baseline_sufficient`；LDI-A checkpoint `aaf3a1c`，status `ldi_a_stop_derived_index_route_baseline_sufficient`。
- Explicit mode 读取 operator-supplied existing private trace root；private R14 labels 只在 action sequences 选定之后用于 scoring。
- Policies：`fixed_stop_after_first`、`fixed_top_k_continue`、`best_baseline_pack_order`、`scheduler_confidence_stop`、`scheduler_diversify_on_redundancy`、`scheduler_promote_after_evidencecore_valid`、`scheduler_budget_guard`，以及 optional private ceiling `oracle_upper_bound_private`。
- Non-oracle policies 使用相同 top-5 budget。Oracle 仅是 private ceiling，不用于 stop/go。
- Promoted/scored evidence 会私下按 current-source path/range/hash 验证。Derived metadata 不是 evidence。
- Public report is aggregate-only：不公开 raw task IDs、queries、paths、spans、tags、scores、ranks、hashes 或 private roots。

## Status taxonomy

- Default：`haae_s_unavailable_no_explicit_action_scheduler_smoke_opt_in`。
- 只有存在 scheduler lift 才 GO：`haae_s_action_scheduler_smoke_complete_haae_t_trace_dataset_readiness_authorized`。
- Honest no-lift/stop：`haae_s_no_go_scheduler_no_lift_over_fixed_baselines` 或 `haae_s_no_go_scheduler_no_lift_over_fixed_baselines`。
- Fail closed：`haae_s_fail_closed_source_trace_privacy_or_consistency_failure`。

## Validation

Required commands：

```bash
python3 eval/bea_v1_haae_s_action_scheduler_smoke.py --self-test
python3 eval/bea_v1_haae_s_action_scheduler_smoke.py --allow-haae-s-action-scheduler-smoke --existing-private-trace-root runs/frk_e_private_1783077424 --confirm-r14-labels-private-scoring --confirm-private-trace-read --confirm-private-traces-written --confirm-evidencecore-currentness --confirm-aggregate-only-public-artifact
python3 eval/bea_v1_haae_s_action_scheduler_smoke.py --validate-report artifacts/bea_v1_haae_s_action_scheduler_smoke/bea_v1_haae_s_action_scheduler_smoke_report.json
```

Validator 会对 source drift、trace invalid、label-before-action、oracle stop/go use、degenerate policies、same-budget mismatch、stale EvidenceCore、derived-as-evidence、privacy leak、stop/go over-authorization，以及 gate/synthetic/readback/self-test exactness fail closed。
