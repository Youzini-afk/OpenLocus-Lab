# BEA-v1-FRK-H Existing-Trace Wider-Suite Stress

状态：已实现。Self-test：`58/58`。

Public artifact：[`bea_v1_frk_h_existing_trace_wider_suite_stress_report.json`](../../artifacts/bea_v1_frk_h_existing_trace_wider_suite_stress/bea_v1_frk_h_existing_trace_wider_suite_stress_report.json)。

## Contract

- Source lock：FRK-G checkpoint `0167445`，status `frk_g_existing_trace_wider_denominator_audit_complete_frk_h_wider_suite_stress_authorized`，self-test `46/46`。
- Default mode 不读取 private trace，并输出 `frk_h_unavailable_no_explicit_existing_trace_stress_opt_in`。
- Explicit mode 需要 `--use-local-n6xfr-recovery --confirm-explicit-private-read`；`--existing-trace-root` 只有在 safe 且位于 local recovery root 下才接受。
- 本阶段只是 empirical existing-trace stress。它只读取 existing N6XFR recovery JSONL rows，不生成 candidates、不 rerun retrieval、不 source scan、不从 source rerun packs，也不改变 scheduler policy。

## Aggregate stress result

- Status：`frk_h_existing_trace_wider_suite_stress_complete_frk_i_existing_trace_algorithm_design_authorized`。
- Denominator integrity：task_count_ge_50，language/source diversity medium-plus，label coverage nonzero，currentness partial existing-trace-only。
- Arm performance stress：best existing arm 有 nonzero gold bucket，fixed baseline saturation not high，arm_spread_bucket spread_low。
- Availability/headroom：availability_limited_bool false，且 headroom_present 存在，因为 existing arms 留下 aggregate opportunity while fixed baseline saturation is not high。
- Slice stress：language/source/arm-family/availability slices 都只以 aggregate buckets 表示。
- Opportunity classification：opportunity_present_weak。
- Decision：FRK-I Existing-Trace Algorithm Design authorized。

## Boundary

Public report is aggregate-only。不公开 private root、path、basename、task ID、query、raw label、line range、snippet、score、rank、hash 或 exact metric。

Forbidden work remains false：no candidate generation、retrieval rerun、source scan、pack rerun from source、scheduler policy change、new trace generation、RPM training、provider/network/CI、runtime/default claim 或 raw publication。

## Validation

```bash
python3 eval/bea_v1_frk_h_existing_trace_wider_suite_stress.py --self-test
python3 eval/bea_v1_frk_h_existing_trace_wider_suite_stress.py --use-local-n6xfr-recovery --confirm-explicit-private-read
python3 eval/bea_v1_frk_h_existing_trace_wider_suite_stress.py --validate-report artifacts/bea_v1_frk_h_existing_trace_wider_suite_stress/bea_v1_frk_h_existing_trace_wider_suite_stress_report.json
```

Validator 会对 source drift、unsafe or missing private roots、schema invalidity、denominator/label/currentness/saturation/headroom/slice/opportunity bucket drift、overauthorization、public leaks、exact metric publication、stop/go errors，以及 gate/synthetic/readback integrity fail closed。
