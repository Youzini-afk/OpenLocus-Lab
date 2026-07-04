# OpenLocus v2 Current Route Closure

Date: 2026-07-04

OpenLocus v2 starts from a closed-route baseline, not from another open-ended preflight chain. Phase 1 is complete when the public closure document, strict RPM state-action trace schema, validator self-tests, and aggregate-only schema report are present.

## Closed routes

The following routes are stopped unless a concrete failing test, defect report, or product workflow pain appears:

- FRK kernel hardening continuation after FRK-N.
- FRK existing-trace selector variants after FRK-I no lift.
- FRK-B/C RankPack resurrection after downstream/proxy no-lift and failure decomposition.
- HAAE simple scheduler redesign after HAAE-S/HAAE-SF no lift.
- LDI-A/LDI-B continuation on easy baseline-sufficient slices.
- Static support-pair repair variants that do not add outcome-aligned executable evidence.

## Preserved invariants

- EvidenceCore remains the hard contract: candidate is not fact; counted evidence must rematerialize current source and pass path/range/content validation.
- Public artifacts for this route are aggregate/schema-only unless a later explicit sanitized-row contract is authorized; private state-action traces remain private.
- Label and outcome information is allowed only after action or offline evaluation; no label leakage into state or action features.
- FastContext is not a runnable baseline. Hitmux may be product/baseline reference only if locally runnable and bounded.

## Phase 1 RPM trace schema

Phase 1 adds `eval/rpm_trace_schema.py` and the public report [`artifacts/rpm_trace_schema/rpm_trace_schema_report.json`](../../artifacts/rpm_trace_schema/rpm_trace_schema_report.json). The schema is strict and fail-closed: required groups are trace identity, task state, state features, action, policy learning support, observation/result, EvidenceCore linkage, outcome/label, privacy/execution, and stop/go/source locks/readback.

The validator enforces closed enums, required fields, no unknown top-level keys, bucketized public fields, unique trace/step identifiers, monotonic step ordering, label timing/isolation, label-blind state/action features, behavior-policy probability markers, EvidenceCore currentness checks, and public aggregate-only leak scanning.

## Stop/go

Phase 1 authorizes exactly one next executable direction to be selected and implemented separately:

1. **RPM-D0 trace capture**: schema-conformant private state-action trace capture with aggregate-only public report.
2. **FRK product workflow benchmark**: executable product-workflow benchmark with private traces and aggregate-only public report.

Not authorized: RPM training, default/method/scale/winner claims, provider/network/CI/runtime-default claims, FRK-J, FRK-B/C resurrection, LDI-B easy-slice continuation, HAAE-SG/T, broad source scan, candidate generation expansion, retrieval/pack rerun as new algorithm work, or raw publication.
