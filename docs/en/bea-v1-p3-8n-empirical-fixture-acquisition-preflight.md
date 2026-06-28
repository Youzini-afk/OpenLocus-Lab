# BEA-v1-P3-8N Empirical Fixture Acquisition Preflight

Date: 2026-06-28

BEA-v1-P3-8N is a preflight-only phase for empirical frozen/materialized event fixture acquisition. It reads the P3-8M public artifact and gitignore metadata only. It does not read private fixture inventories, read or write private files, import helper/P3-8/target evaluators, execute capture, generate fixtures, run retrieval, rerun P4L/N1/N2, run support labeling, execute counterfactuals, or tune policy.

## Result

```text
status: no_go_p3_8n_empirical_event_source_not_declared
self-test: 13 / 13
forbidden scan: pass
surface field spec records: 5
empirical event source declared: false
P3-8O source declaration design authorized: true
fixture generation authorized: false
trace capture execution authorized: false
private write authorized: false
```

The P3-8M acquisition design is present and valid, and the project-private root is gitignored by metadata. However, no empirical event source has been declared. P3-8N therefore fails closed before fixture generation, capture execution, or private writes.

## Boundary

P3-8N performs no private inventory read. It only verifies the public input contract, privacy-root metadata, scanner/fail-closed rules, explicit enablement boundaries, and per-surface empirical field specifications. Missing empirical source declaration blocks any move toward fixture generation or capture.

## Handoff

P3-8N authorizes only **BEA-v1-P3-8O Empirical Event Source Declaration Design**. P3-8O is design-only and must not generate fixtures, execute capture, write private data, run retrieval/reruns/support/counterfactuals, tune policy, or promote runtime/default behavior.

## Artifact

- Script: `eval/bea_v1_p3_8n_empirical_fixture_acquisition_preflight.py`
- Report: `artifacts/bea_v1_p3_8n_empirical_fixture_acquisition_preflight/bea_v1_p3_8n_empirical_fixture_acquisition_preflight_report.json`
