# BEA-v1-FRK-G Existing-Trace Wider Denominator Audit

Status: implemented. Self-test: `46/46`.

Public artifact: [`bea_v1_frk_g_existing_trace_wider_denominator_audit_report.json`](../../artifacts/bea_v1_frk_g_existing_trace_wider_denominator_audit/bea_v1_frk_g_existing_trace_wider_denominator_audit_report.json).

## Contract

- Source lock: HAAE-SF checkpoint `144b84d`, status `haae_sf_action_scheduler_failure_decomposition_complete_stop_track_b_simple_scheduler_route`; HAAE-S checkpoint `5a49c90`, status `haae_s_no_go_scheduler_no_lift_over_fixed_baselines`; FRK-F checkpoint `63528e8`, status `frk_f_stop_current_frk_b_c_pack_route_baseline_sufficient`; LDI-A checkpoint `aaf3a1c`, status `ldi_a_stop_derived_index_route_baseline_sufficient`.
- Default mode performs no private read and emits `frk_g_unavailable_no_explicit_existing_trace_denominator_opt_in`.
- Explicit mode requires `--confirm-explicit-private-read` plus either `--use-local-n6xfr-recovery` or `--existing-trace-root <allowed-root>`.
- This is an existing-trace audit only, not a new pack/scheduler/retrieval experiment.

## Aggregate audit result

- Status: `frk_g_existing_trace_wider_denominator_audit_complete_frk_h_wider_suite_stress_authorized`.
- Denominator shape: task_count_ge_50, medium-plus language/repo-file diversity.
- Label/currentness quality: label coverage high; currentness partial existing-trace-only.
- Saturation/headroom: fixed baseline saturation not high; headroom_present.
- Decision: FRK-H existing-trace wider-suite stress authorized; FRK-H Existing-Trace Wider-Suite Stress authorized = true.

## Boundary

The report is aggregate-only. It publishes no private root, paths, task IDs, queries, labels, line ranges, snippets, scores, ranks, hashes, or exact metrics.

Forbidden work remains false: no candidate generation, retrieval rerun, source scan, pack rerun, scheduler policy change, new trace generation, RPM training, provider/network/CI, runtime/default, or raw publication.

## Validation

```bash
python3 eval/bea_v1_frk_g_existing_trace_wider_denominator_audit.py --self-test
python3 eval/bea_v1_frk_g_existing_trace_wider_denominator_audit.py --use-local-n6xfr-recovery --confirm-explicit-private-read
python3 eval/bea_v1_frk_g_existing_trace_wider_denominator_audit.py --validate-report artifacts/bea_v1_frk_g_existing_trace_wider_denominator_audit/bea_v1_frk_g_existing_trace_wider_denominator_audit_report.json
```

The validator fails closed for source drift, missing explicit root, root safety, schema invalidity, denominator bucket drift, overauthorization, privacy leaks, exact metric publication, stop/go errors, and gate/synthetic/readback integrity.
