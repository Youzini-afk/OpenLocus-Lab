# BEA-v1-HAAE-S Action Scheduler Smoke

Status: implemented. Self-test: `57/57`.

Public artifact: [`bea_v1_haae_s_action_scheduler_smoke_report.json`](../../artifacts/bea_v1_haae_s_action_scheduler_smoke/bea_v1_haae_s_action_scheduler_smoke_report.json).

## Contract

- Source locks: FRK-F checkpoint `63528e8` with status `frk_f_stop_current_frk_b_c_pack_route_baseline_sufficient`; LDI-A checkpoint `aaf3a1c` with status `ldi_a_stop_derived_index_route_baseline_sufficient`.
- Explicit mode reads an operator-supplied existing private trace root and uses private R14 labels for scoring only after action sequences are chosen.
- Policies: `fixed_stop_after_first`, `fixed_top_k_continue`, `best_baseline_pack_order`, `scheduler_confidence_stop`, `scheduler_diversify_on_redundancy`, `scheduler_promote_after_evidencecore_valid`, `scheduler_budget_guard`, and optional private ceiling `oracle_upper_bound_private`.
- Non-oracle policies use the same top-5 budget. The oracle is a private ceiling only and is not used for stop/go.
- Promoted/scored evidence is validated against current-source path/range/hash privately. Derived metadata is not evidence.
- Public report is aggregate-only: no raw task IDs, queries, paths, spans, tags, scores, ranks, hashes, or private roots.

## Status taxonomy

- Default: `haae_s_unavailable_no_explicit_action_scheduler_smoke_opt_in`.
- GO only if scheduler lift exists: `haae_s_action_scheduler_smoke_complete_haae_t_trace_dataset_readiness_authorized`.
- Honest no-lift/stop: `haae_s_no_go_scheduler_no_lift_over_fixed_baselines` or `haae_s_no_go_scheduler_no_lift_over_fixed_baselines`.
- Fail closed: `haae_s_fail_closed_source_trace_privacy_or_consistency_failure`.

## Validation

Required commands:

```bash
python3 eval/bea_v1_haae_s_action_scheduler_smoke.py --self-test
python3 eval/bea_v1_haae_s_action_scheduler_smoke.py --allow-haae-s-action-scheduler-smoke --existing-private-trace-root runs/frk_e_private_1783077424 --confirm-r14-labels-private-scoring --confirm-private-trace-read --confirm-private-traces-written --confirm-evidencecore-currentness --confirm-aggregate-only-public-artifact
python3 eval/bea_v1_haae_s_action_scheduler_smoke.py --validate-report artifacts/bea_v1_haae_s_action_scheduler_smoke/bea_v1_haae_s_action_scheduler_smoke_report.json
```

The validator fails closed for source drift, trace invalidity, label-before-action, oracle stop/go use, degenerate policies, same-budget mismatch, stale EvidenceCore, derived-as-evidence, privacy leaks, stop/go over-authorization, and gate/synthetic/readback/self-test exactness.
