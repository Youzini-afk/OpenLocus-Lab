# BEA-v1-FRK-H Existing-Trace Wider-Suite Stress

Status: implemented. Self-test: `58/58`.

Public artifact: [`bea_v1_frk_h_existing_trace_wider_suite_stress_report.json`](../../artifacts/bea_v1_frk_h_existing_trace_wider_suite_stress/bea_v1_frk_h_existing_trace_wider_suite_stress_report.json).

## Contract

- Source lock: FRK-G checkpoint `0167445`, status `frk_g_existing_trace_wider_denominator_audit_complete_frk_h_wider_suite_stress_authorized`, self-test `46/46`.
- Default mode performs no private read and emits `frk_h_unavailable_no_explicit_existing_trace_stress_opt_in`.
- Explicit mode requires `--use-local-n6xfr-recovery --confirm-explicit-private-read`; `--existing-trace-root` is accepted only when safe and under the local recovery root.
- This is an empirical existing-trace stress only. It reads existing N6XFR recovery JSONL rows and does not generate candidates, rerun retrieval, scan sources, rerun packs from source, or change scheduler policy.

## Aggregate stress result

- Status: `frk_h_existing_trace_wider_suite_stress_complete_frk_i_existing_trace_algorithm_design_authorized`.
- Denominator integrity: task_count_ge_50, language/source diversity medium-plus, label coverage nonzero, currentness partial existing-trace-only.
- Arm performance stress: best existing arm has nonzero gold bucket, fixed baseline saturation not high, and arm_spread_bucket spread_low.
- Availability/headroom: availability_limited_bool false, and headroom_present is present because existing arms leave aggregate opportunity while fixed baseline saturation is not high.
- Slice stress: language/source/arm-family/availability slices are represented as aggregate buckets only.
- Opportunity classification: opportunity_present_weak.
- Decision: FRK-I Existing-Trace Algorithm Design authorized.

## Boundary

The report is aggregate-only. It publishes no private root, path, basename, task ID, query, raw label, line range, snippet, score, rank, hash, or exact metric.

Forbidden work remains false: no candidate generation, retrieval rerun, source scan, pack rerun from source, scheduler policy change, new trace generation, RPM training, provider/network/CI, runtime/default claim, or raw publication.

## Validation

```bash
python3 eval/bea_v1_frk_h_existing_trace_wider_suite_stress.py --self-test
python3 eval/bea_v1_frk_h_existing_trace_wider_suite_stress.py --use-local-n6xfr-recovery --confirm-explicit-private-read
python3 eval/bea_v1_frk_h_existing_trace_wider_suite_stress.py --validate-report artifacts/bea_v1_frk_h_existing_trace_wider_suite_stress/bea_v1_frk_h_existing_trace_wider_suite_stress_report.json
```

The validator fails closed for source drift, unsafe or missing private roots, schema invalidity, denominator/label/currentness/saturation/headroom/slice/opportunity bucket drift, overauthorization, public leaks, exact metric publication, stop/go errors, and gate/synthetic/readback integrity.
