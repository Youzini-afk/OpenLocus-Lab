# BEA-v1-HAAE-SF Action Scheduler Failure Decomposition

状态：已实现。Self-test：`41/41`。

Public artifact：[`bea_v1_haae_sf_action_scheduler_failure_decomposition_report.json`](../../artifacts/bea_v1_haae_sf_action_scheduler_failure_decomposition/bea_v1_haae_sf_action_scheduler_failure_decomposition_report.json)。

## Contract

- Source lock：HAAE-S checkpoint `5a49c90`，status `haae_s_no_go_scheduler_no_lift_over_fixed_baselines`，self-test `57/57`，且 HAAE-T not authorized。
- Parent stop locks：FRK-F checkpoint `63528e8`，status `frk_f_stop_current_frk_b_c_pack_route_baseline_sufficient`；LDI-A checkpoint `aaf3a1c`，status `ldi_a_stop_derived_index_route_baseline_sufficient`。
- Default mode 只读取 HAAE-S public action scheduler smoke artifact。Private trace root 只能在显式 `--confirm-explicit-private-read --private-trace-root <runs/...>` 时读取。
- 本阶段不是 preflight/audit chain，也不是新的 scheduler experiment。

## Failure decomposition

- fixed_baseline_saturation_high
- scheduler action degeneracy 在 public aggregate report 中未显示。
- state_feature_gap_unknown_public_aggregate_only
- oracle_gap_private_only
- EvidenceCore/currentness 由 HAAE-S aggregate currentness record 锁定。
- Label timing 锁定为 labels-after-actions。
- 通过 `haae_s_no_go_scheduler_no_lift_over_fixed_baselines` 锁定 scheduler_no_lift。

## Decision

- Status：`haae_sf_action_scheduler_failure_decomposition_complete_stop_track_b_simple_scheduler_route`。
- Decision：stop_track_b_simple_scheduler_route。
- HAAE-SG state-feature redesign smoke authorized = false。
- Return-to-route bucket：FRK/benchmark track，除非未来 explicit private decomposition 同时显示 concrete state-feature failure mode 和 private-ceiling opportunity。

## Boundary

Public artifact is aggregate-only。不公开 raw private trace rows、task IDs、queries、paths、spans、hashes、exact scores、exact ranks 或 private roots。

Forbidden work remains forbidden：no RPM/provider/network/CI/runtime/default/candidate generation/policy change/new traces/raw publication。

## Validation

```bash
python3 eval/bea_v1_haae_sf_action_scheduler_failure_decomposition.py --self-test
python3 eval/bea_v1_haae_sf_action_scheduler_failure_decomposition.py
python3 eval/bea_v1_haae_sf_action_scheduler_failure_decomposition.py --validate-report artifacts/bea_v1_haae_sf_action_scheduler_failure_decomposition/bea_v1_haae_sf_action_scheduler_failure_decomposition_report.json
```

Validator 会对 source drift、HAAE-T authorization drift、未显式传参读取 private trace、labels used for policy selection、new candidate generation、scheduler policy change、new trace generation、raw leak、exact metric publication、stop/go overauthorization 以及 gate/synthetic/readback integrity fail closed。
