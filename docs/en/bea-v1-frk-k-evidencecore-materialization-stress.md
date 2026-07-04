# BEA-v1-FRK-K EvidenceCore Materialization Stress Benchmark

Status: implemented. Self-test: `58/58`.

Public artifact: [`bea_v1_frk_k_evidencecore_materialization_stress_report.json`](../../artifacts/bea_v1_frk_k_evidencecore_materialization_stress/bea_v1_frk_k_evidencecore_materialization_stress_report.json).

## Contract

- Source lock: FRK-I checkpoint `cc4885d`, status `frk_i_existing_trace_algorithm_design_complete_stop_existing_trace_algorithm_route_no_lift`; FRK-J is not authorized.
- Default mode performs no local stress run and creates no temporary snapshot.
- Explicit mode requires `--run-local-evidencecore-stress --confirm-temp-snapshot`.
- This is a practical local EvidenceCore materialization/currentness/stale-rejection stress, not ranking lift and not FRK-J/B/C/LDI-B/HAAE-SG/RPM.

## Empirical fixture coverage

The local run creates a bounded ignored temporary snapshot and deterministic fixture families: symbol_definition_fixture, config_key_fixture, function_callsite_fixture, path_filename_fixture, near_duplicate_fixture, moved_file_fixture, deleted_file_fixture, stale_range_fixture, line_insertion_fixture, and alias_or_rename_fixture.

Public fixture coverage bucket: `coverage_all_required_families`.

## Aggregate result

- Status: `frk_k_evidencecore_materialization_stress_complete_frk_l_kernel_hardening_authorized`.
- Validity bucket: `validity_high`.
- Currentness bucket: `currentness_pass`.
- Stale rejection: `stale_rejection_pass`.
- Deleted file trap: deleted_file_rejected.
- Moved/line-insertion handling: rematerialized or safely rejected.
- Near duplicate trap: near_duplicate_rejected.
- Latency/resource buckets: latency_usable and resource_bounded.
- Decision: FRK-L Kernel Hardening authorized.

## Boundary

The report is aggregate-only. It publishes no temp root, paths, queries, snippets, hashes, exact timings, exact counts, raw candidates, or raw fixture content.

Stopped/forbidden routes remain false: FRK-J, FRK-B/C, LDI-B, HAAE-SG/HAAE-T, RPM, provider/network/CI, runtime/default, method/scale/winner claims, candidate generation, retrieval rerun, source scan, pack rerun, and raw publication.

## Validation

```bash
python3 eval/bea_v1_frk_k_evidencecore_materialization_stress.py --self-test
python3 eval/bea_v1_frk_k_evidencecore_materialization_stress.py --run-local-evidencecore-stress --confirm-temp-snapshot
python3 eval/bea_v1_frk_k_evidencecore_materialization_stress.py --validate-report artifacts/bea_v1_frk_k_evidencecore_materialization_stress/bea_v1_frk_k_evidencecore_materialization_stress_report.json
```

The validator fails closed for source lock drift, stopped-route drift, temp snapshot escape/symlink, missing fixtures, invalid citation schema/range/empty citations, stale/deleted/moved/near-duplicate/latency failures, overauthorization, public leaks, exact metric publication, stop/go errors, and gate/synthetic/readback integrity.
