# BEA-v1-P3-8P Empirical Event Source Declaration Intake Preflight

Date: 2026-06-28

BEA-v1-P3-8P validates whether a real empirical event source declaration has been explicitly supplied and is schema-valid. The default local run performs no broad private scan and, because no declaration is supplied, fails closed.

## Result

```text
status: no_go_p3_8p_empirical_source_declaration_missing
self-test: 13 / 13
forbidden scan: pass
declaration supplied: false
P3-8Q fixture acquisition plan preflight authorized: false
fixture generation authorized: false
trace capture execution authorized: false
private write authorized: false
```

P3-8P binds to the P3-8O declaration-design artifact. It can validate an explicitly supplied declaration via `--declaration-json`, but it does not search `.openlocus`, does not serialize the exact declaration path or filename, and does not write private files.

## Boundary

This phase performs declaration intake preflight only. It does not generate fixtures, execute capture, read broad private inventories, write private rows, import helpers or target evaluators, run retrieval, rerun P4L/N1/N2, run support labeling, execute counterfactuals, tune policy, or promote runtime/default behavior.

## Handoff

In the default No-Go run, P3-8Q is not authorized. If a future explicit declaration passes all schema, surface coverage, source mode, privacy, and claim-boundary gates, only **BEA-v1-P3-8Q Empirical Fixture Acquisition Plan Preflight** would be authorized; that preflight remains no fixture generation and no capture execution.

## Artifact

- Script: `eval/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight.py`
- Report: `artifacts/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight/bea_v1_p3_8p_empirical_event_source_declaration_intake_preflight_report.json`
