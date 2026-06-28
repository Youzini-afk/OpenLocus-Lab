# BEA-v1-P3-8M Empirical Frozen Event Fixture Acquisition Design

Date: 2026-06-28

BEA-v1-P3-8M is a design-only phase that follows P3-8L's closure of the proxy fixture route. It reads only the P3-8L public artifact and does not read private fixtures, write private files, import helpers or target evaluators, execute trace capture, run retrieval, rerun P4L/N1/N2, run support labeling, execute counterfactuals, or tune policy.

## Result

```text
status: empirical_fixture_acquisition_design_pass_p3_8n_authorized
self-test: 12 / 12
forbidden scan: pass
empirical source designs: 5
field requirement rows: 5
capture preconditions: 7
P3-8N empirical fixture acquisition preflight authorized: true
fixture generation authorized: false
trace capture execution authorized: false
private trace row write authorized: false
```

P3-8M translates the P3-8L decision into five surface-level acquisition-design records. Each surface requires true empirical frozen/materialized event fixtures. Proxy fixtures, committed aggregate summaries, and contract templates remain disallowed for mechanism work.

## Boundary

This phase is schema and acquisition planning only. It does not generate fixtures and does not authorize fixture generation in P3-8N. It also does not authorize trace capture, private trace writes, retrieval, P4L/N1/N2 reruns, support labeling, counterfactuals, denominator audits, policy tuning, selector/reranker work, P5, BEA-v1-A, runtime/default promotion, broad retrieval expansion, method-winner claims, or downstream-value claims.

## Handoff

P3-8M authorizes only **BEA-v1-P3-8N Empirical Fixture Acquisition Preflight**. P3-8N is preflight-only and must not execute capture, generate fixtures, write private rows, or run retrieval/rerun/counterfactual/policy work.

## Artifact

- Script: `eval/bea_v1_p3_8m_empirical_fixture_acquisition_design.py`
- Report: `artifacts/bea_v1_p3_8m_empirical_fixture_acquisition_design/bea_v1_p3_8m_empirical_fixture_acquisition_design_report.json`
