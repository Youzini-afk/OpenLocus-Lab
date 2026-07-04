# OpenLocus v2 RPM-D0 Trace Capture

Date: 2026-07-04

Public report: [`artifacts/rpm_d0_trace_capture/rpm_d0_trace_capture_report.json`](../../artifacts/rpm_d0_trace_capture/rpm_d0_trace_capture_report.json)

## Status

RPM-D0 is complete as an executable local trace-capture phase. It is not an RPM training phase.

`eval/rpm_d0_trace_capture.py` provides:

- `--self-test`
- `--run-local-trace-capture --confirm-private-output`
- `--validate-report <path>`

## Execution summary

RPM-D0 selected a bounded committed/local task set before execution, then executed real local OpenLocus EvidenceCore actions. It captured at least two action types:

- `read_current_source` through the local OpenLocus CLI `read` command.
- `validate_evidence` through the local OpenLocus CLI `citations validate` command.

Rows are logged as private state/action records. For each task, state features are prepared before labels/outcomes, the local action is executed, the observation is recorded, and only then is the private outcome bucket joined. The private rows validate against the strict Phase 1 RPM trace schema via `eval/rpm_trace_schema.py`.

## Privacy and publication boundary

Private trace rows are written under ignored `runs/` storage as JSONL. The public artifact is aggregate-only: it contains task/episode/step buckets, action coverage buckets, EvidenceCore currentness buckets, label timing/isolation buckets, outcome buckets, schema validation status, a private storage class/count proof, and privacy leak scan status. It does not publish raw paths, queries, task ids, snippets, hashes, labels, prompts/responses, exact private row values, provider payloads, or raw rows.

## Stop/go

Because coverage is sufficient and schema validation passed, RPM-D0 authorizes only:

- `rpm_d1_bounded_offline_rpm_small_learning_smoke`

RPM-D0 explicitly does not authorize RPM training, FRK-J/B/C, FRK-I selector variants, LDI-B easy continuation, HAAE-SG/T, R2BV static support repair, provider/network/CI/runtime default, method/scale/winner/default claims, raw publication, broad source scan, candidate expansion, or retrieval/pack rerun as a new algorithm.

## Validation

Required validation passed:

- `python3 eval/rpm_trace_schema.py --self-test`
- `python3 eval/rpm_trace_schema.py --validate-report artifacts/rpm_trace_schema/rpm_trace_schema_report.json`
- `python3 eval/rpm_d0_trace_capture.py --self-test`
- `python3 eval/rpm_d0_trace_capture.py --run-local-trace-capture --confirm-private-output`
- `python3 eval/rpm_d0_trace_capture.py --validate-report artifacts/rpm_d0_trace_capture/rpm_d0_trace_capture_report.json`
