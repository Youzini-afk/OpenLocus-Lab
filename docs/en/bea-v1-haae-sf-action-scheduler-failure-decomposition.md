# BEA-v1-HAAE-SF Action Scheduler Failure Decomposition

Status: implemented. Self-test: `41/41`.

Public artifact: [`bea_v1_haae_sf_action_scheduler_failure_decomposition_report.json`](../../artifacts/bea_v1_haae_sf_action_scheduler_failure_decomposition/bea_v1_haae_sf_action_scheduler_failure_decomposition_report.json).

## Contract

- Source lock: HAAE-S checkpoint `5a49c90`, status `haae_s_no_go_scheduler_no_lift_over_fixed_baselines`, self-test `57/57`, with HAAE-T not authorized.
- Parent stop locks: FRK-F checkpoint `63528e8`, status `frk_f_stop_current_frk_b_c_pack_route_baseline_sufficient`; LDI-A checkpoint `aaf3a1c`, status `ldi_a_stop_derived_index_route_baseline_sufficient`.
- Default mode reads only the HAAE-S public action scheduler smoke artifact. Private trace roots are read only with explicit `--confirm-explicit-private-read --private-trace-root <runs/...>`.
- This is not a preflight/audit chain and not a new scheduler experiment.

## Failure decomposition

- fixed_baseline_saturation_high
- scheduler action degeneracy is not shown by the public aggregate report.
- state_feature_gap_unknown_public_aggregate_only
- oracle_gap_private_only
- EvidenceCore/currentness is locked by the HAAE-S aggregate currentness record.
- Label timing is locked as labels-after-actions.
- lock scheduler_no_lift via `haae_s_no_go_scheduler_no_lift_over_fixed_baselines`.

## Decision

- Status: `haae_sf_action_scheduler_failure_decomposition_complete_stop_track_b_simple_scheduler_route`.
- Decision: stop_track_b_simple_scheduler_route.
- HAAE-SG state-feature redesign smoke authorized = false.
- Return-to-route bucket: FRK/benchmark track unless a future explicit private decomposition shows both a concrete state-feature failure mode and private-ceiling opportunity.

## Boundary

The public artifact is aggregate-only. It publishes no raw private trace rows, task IDs, queries, paths, spans, hashes, exact scores, exact ranks, or private roots.

Forbidden work remains forbidden: no RPM/provider/network/CI/runtime/default/candidate generation/policy change/new traces/raw publication.

## Validation

```bash
python3 eval/bea_v1_haae_sf_action_scheduler_failure_decomposition.py --self-test
python3 eval/bea_v1_haae_sf_action_scheduler_failure_decomposition.py
python3 eval/bea_v1_haae_sf_action_scheduler_failure_decomposition.py --validate-report artifacts/bea_v1_haae_sf_action_scheduler_failure_decomposition/bea_v1_haae_sf_action_scheduler_failure_decomposition_report.json
```

The validator fails closed for source drift, HAAE-T authorization drift, private trace use without explicit args, labels used for policy selection, new candidate generation, scheduler policy changes, new trace generation, raw leaks, exact metric publication, stop/go overauthorization, and gate/synthetic/readback integrity.
