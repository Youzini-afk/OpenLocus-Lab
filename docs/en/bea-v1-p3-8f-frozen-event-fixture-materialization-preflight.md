# BEA-v1-P3-8F Frozen Event Fixture Materialization Preflight

Date: 2026-06-28

BEA-v1-P3-8F is a design/preflight phase for future frozen/materialized event fixture materialization. It does not generate fixture files, write project-private files, write private trace rows, run P3-8 capture, run retrieval, rerun P4L/N1/N2, run support labeling, execute counterfactuals, tune policy, authorize selector/reranker/P5/BEA-v1-A work, or promote runtime/default behavior.

## Result

```text
status: frozen_event_fixture_materialization_preflight_pass_p3_8g_authorized
self-test: 11 / 11
forbidden scan: pass
fixture source mappings: 5 / 5
safe proxy source mappings: 5 / 5
private files written in P3-8F: 0
P3-8G proxy fixture materialization authorized: true
```

P3-8F validates the P3-8 No-Go artifact, P3-7 pass artifact, and P3-6 pass artifact, then maps each trace surface to committed proxy/contract sources:

- `support_link`: committed proxy label summaries from P1-3/P1-4, with P1-5R confirming missing source/context linkage.
- `scheduler_action_cost`: committed P0-3 contract template only, not arm-outcome evidence.
- `ordered_prefix_stop`: committed aggregate proxy evidence from P2-1, not row-level stop trace.
- `same_file_redundancy`: committed P0-6 contract template only.
- `risk_penalty`: committed P0-7 contract template only.

These are **proxy fixture plans**, not honest empirical captured event fixtures. Missing empirical fields are recorded per surface.

## Boundary

P3-8F does not materialize fixtures and does not write under `.openlocus/research-private/`. It verifies the private file inventory is unchanged during the phase. Public records contain only bucketed source mappings, proxy claim boundaries, schema completion summaries, and future materialization plans.

## Handoff

P3-8F authorizes only **BEA-v1-P3-8G Frozen Event Fixture Materialization Smoke**: proxy fixture files only, no trace capture. P3-8G may write private fixture files only in its own phase; private trace rows, retrieval, P4L/N1/N2 reruns, support labeling, counterfactuals, denominator audits, policy tuning, selector/reranker/P5/BEA-v1-A work, runtime/default promotion, method-winner claims, and downstream-value claims remain unauthorized.

## Artifact

- Script: `eval/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight.py`
- Report: `artifacts/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight/bea_v1_p3_8f_frozen_event_fixture_materialization_preflight_report.json`
