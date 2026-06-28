# BEA-v1-P3-8L Projection Field Adequacy and Empirical Fixture Requirement Decision

Date: 2026-06-28

BEA-v1-P3-8L is a decision-only closure phase for the proxy fixture route. It reads only the P3-8K public artifact and does not read private fixtures, import helpers or target evaluators, execute capture, run retrieval, rerun P4L/N1/N2, run support labeling, execute counterfactuals, or tune policy.

## Result

```text
status: proxy_route_closure_empirical_fixtures_required
self-test: 11 / 11
forbidden scan: pass
proxy route closed: true
P3-8M empirical fixture acquisition design authorized: true
trace capture execution authorized: false
private trace row write authorized: false
```

P3-8L accepts the P3-8K conclusion that the proxy public projections are shape-valid for a logger-smoke audit but are not empirical trace evidence. They are not adequate for denominator audits, counterfactuals, or mechanism-evidence claims.

## Decision

The proxy route is closed for mechanism work. True empirical frozen/materialized event fixtures are required before mechanism work, denominator audits, counterfactuals, or trace-capture claims can proceed. Committed aggregate proxies, contract templates, and proxy fixtures are not sufficient substitutes.

## Handoff

P3-8L authorizes only **BEA-v1-P3-8M Empirical Frozen Event Fixture Acquisition Design**. P3-8M is design-only and does not authorize capture execution, private trace writes, retrieval, P4L/N1/N2 reruns, support labeling, counterfactuals, policy tuning, selector/reranker work, P5, BEA-v1-A, runtime/default promotion, broad retrieval expansion, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_p3_8l_projection_field_adequacy_decision.py`
- Report: `artifacts/bea_v1_p3_8l_projection_field_adequacy_decision/bea_v1_p3_8l_projection_field_adequacy_decision_report.json`
