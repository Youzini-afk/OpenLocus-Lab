# BEA-v1-FRK-I Existing-Trace Algorithm Design Prototype

Status: implemented. Self-test: `57/57`.

Public artifact: [`bea_v1_frk_i_existing_trace_algorithm_design_report.json`](../../artifacts/bea_v1_frk_i_existing_trace_algorithm_design/bea_v1_frk_i_existing_trace_algorithm_design_report.json).

## Contract

- Source lock: FRK-H checkpoint `a95988f`, status `frk_h_existing_trace_wider_suite_stress_complete_frk_i_existing_trace_algorithm_design_authorized`, self-test `58/58`.
- Default mode performs no private read and emits `frk_i_unavailable_no_explicit_existing_trace_algorithm_opt_in`.
- Explicit mode requires `--use-local-n6xfr-recovery --confirm-explicit-private-read`; `--existing-trace-root` is accepted only when safe and under the local recovery root.
- This is an empirical prototype over existing N6XFR private trace rows only.

## Prototype

- Algorithm bucket: `availability_weighted_rankpack_selector`.
- Design: deterministic, nonlearned, label-blind selector using existing metadata only: materializable/top100 availability, language/source buckets, and arm-family metadata.
- Labels/gold are used only after design for aggregate scoring.

## Aggregate result

- Status: `frk_i_existing_trace_algorithm_design_complete_stop_existing_trace_algorithm_route_no_lift`.
- Baselines: best_fixed_existing_arm_baseline bucket `rate_low`; median_fixed_existing_arm_baseline bucket `rate_low`.
- Prototype selector bucket: `rate_low`.
- Prototype vs best fixed delta bucket: `neutral_no_lift`.
- Coverage bucket: `coverage_high`; slice consistency bucket: `flat_or_negative`; slice failure mode bucket: `low_arm_spread_limits_algorithm`; generalization risk bucket: `risk_medium`.
- Oracle ceiling bucket is private diagnostic only and bucketized.
- Decision: stop_existing_trace_algorithm_route_no_lift; FRK-J Existing-Trace Algorithm Validation authorized = false.

## Boundary

The report is aggregate-only. It publishes no private root, path, basename, task ID, query, raw label, line range, snippet, score, rank, hash, or exact metric.

Forbidden work remains false: no new candidates, retrieval rerun, source scan, pack rerun, new traces, scheduler policy change, RPM, provider/network/CI, runtime/default/method/scale/winner claim, or raw publication.

## Validation

```bash
python3 eval/bea_v1_frk_i_existing_trace_algorithm_design.py --self-test
python3 eval/bea_v1_frk_i_existing_trace_algorithm_design.py --use-local-n6xfr-recovery --confirm-explicit-private-read
python3 eval/bea_v1_frk_i_existing_trace_algorithm_design.py --validate-report artifacts/bea_v1_frk_i_existing_trace_algorithm_design/bea_v1_frk_i_existing_trace_algorithm_design_report.json
```

The validator fails closed for source drift, unsafe or missing private roots, schema invalidity, label use in design, labels not scoring-only, nondeterministic/learned algorithm drift, overauthorization, comparison/slice/risk drift, FRK-J authorization without positive lift, public leaks, exact metric publication, stop/go errors, and gate/synthetic/readback integrity.
