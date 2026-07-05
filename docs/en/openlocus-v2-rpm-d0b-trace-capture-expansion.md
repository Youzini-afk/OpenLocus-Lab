# OpenLocus v2 RPM-D0B Trace Capture Expansion

Date: 2026-07-04

Public report: [`artifacts/rpm_d0b_trace_capture_expansion/rpm_d0b_trace_capture_expansion_report.json`](../../artifacts/rpm_d0b_trace_capture_expansion/rpm_d0b_trace_capture_expansion_report.json)

## Status

RPM-D0B is complete as an expanded private trace-capture phase. It responds to the RPM-D1 finding that the original D0 trace set had insufficient real-trace diversity. The public status is `rpm_d0b_trace_capture_expansion_complete_d1_rerun_authorized`.

This phase does **not** train RPM, does **not** claim that RPM works, and does **not** authorize D2/model scaling, runtime/default behavior, provider/network/CI execution, method/scale/winner/default claims, raw publication, broad source scan, candidate expansion, or retrieval/pack rerun as a new algorithm.

`eval/rpm_d0b_trace_capture_expansion.py` provides:

- `--self-test`
- `--run-local-trace-capture --confirm-private-output`
- `--validate-report artifacts/rpm_d0b_trace_capture_expansion/rpm_d0b_trace_capture_expansion_report.json`

## Execution summary

D0B predeclares a fixed bounded set of 12 local episodes before execution. Each episode executes three real local OpenLocus-style actions: bounded retrieval, current source read, and EvidenceCore citation validation. The required RPM schema action types are covered: `bounded_retrieval`, `read_current_source`, and `validate_evidence`.

The run writes private rows only after `--confirm-private-output` under ignored `runs/` storage. Every row is validated through the Phase 1 RPM trace schema. Retrieval no-hit rows and stale/currentness negative controls are represented as failure-safe outcome rows without treating a bounded CLI miss as a script failure.

## Diversity and negative controls

The private trace set has aggregate buckets for 36 rows, 12 episodes, and three action types. Public output confirms at least 30 rows, at least 10 episodes, all required action types, at least five success-bucket rows, at least five failure-bucket rows, stale/currentness negative-control coverage, retrieval failure-safe coverage, and label timing isolation.

Labels and outcomes are joined only after the action. State/action features remain label-blind and exclude post-action currentness results.

## Privacy and publication boundary

The public artifact is aggregate-only. It does not publish private trace paths, task ids, private refs, exact queries or patterns, raw paths, snippets, hashes, labels, exact row values, raw rows, or private evidence filenames. The public report contains only aggregate row/episode/action/outcome/observation/failure/currentness/label buckets, diversity gate readback, schema/privacy validation, and stop/go.

## Stop/go

Because all D0B gates pass, D0B authorizes only:

- `rpm_d1_bounded_offline_rpm_small_learning_smoke_rerun`

If any D0B gate fails in a future run, the script authorizes only `targeted_d0b_repair_only`. No D2/model scaling, runtime/default, provider/network/CI, training, method/scale/winner/default, raw/broad source scan, candidate expansion, retrieval-pack rerun, FRK-J/B/C, FRK-I variants, LDI-B easy continuation, HAAE-SG/T, or R2BV static support repair is authorized.

## Validation

Required validation for this phase includes:

- `python3 eval/rpm_trace_schema.py --self-test`
- `python3 eval/rpm_trace_schema.py --validate-report artifacts/rpm_trace_schema/rpm_trace_schema_report.json`
- `python3 eval/rpm_d0_trace_capture.py --validate-report artifacts/rpm_d0_trace_capture/rpm_d0_trace_capture_report.json`
- `python3 eval/rpm_d1_learning_smoke.py --validate-report artifacts/rpm_d1_learning_smoke/rpm_d1_learning_smoke_report.json`
- `python3 eval/rpm_d0b_trace_capture_expansion.py --self-test`
- `python3 eval/rpm_d0b_trace_capture_expansion.py --run-local-trace-capture --confirm-private-output`
- `python3 eval/rpm_d0b_trace_capture_expansion.py --validate-report artifacts/rpm_d0b_trace_capture_expansion/rpm_d0b_trace_capture_expansion_report.json`
- optional D1 rerun with `--trace-jsonl <private-d0b-jsonl> --confirm-private-input`
- `python3 scripts/validate_docs_i18n.py`
- `git diff --check`
