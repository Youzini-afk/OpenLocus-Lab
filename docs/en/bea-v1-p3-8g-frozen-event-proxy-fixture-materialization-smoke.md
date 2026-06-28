# BEA-v1-P3-8G Frozen Event Proxy Fixture Materialization Smoke

Date: 2026-06-28

BEA-v1-P3-8G materializes proxy fixture files from the P3-8F safe proxy source mappings. These files are proxy fixture inputs only; they are not captured trace rows and not empirical P3-8 frozen trace fixtures.

## Result

```text
status: frozen_event_proxy_fixture_materialization_smoke_pass_p3_8h_authorized
self-test: 15 / 15
forbidden scan: pass
private proxy fixture files written: 2
proxy fixture events: 5
P3-8H compatibility preflight authorized: true
```

P3-8G writes exactly two project-private ignored files, reported publicly only as
the buckets `p3_8g_proxy_fixture_manifest_private` and
`p3_8g_proxy_fixture_events_private`. The exact private filenames and paths are
not part of the public artifact.

It does not write the default P3-8 fixture filenames. Each of the five surfaces receives one proxy event with bucketed proxy-safe values and explicit missing empirical field buckets. No real hits, ranks, paths, candidates, queue identifiers, design identifiers, or provider payloads are materialized.

## Boundary

P3-8G does not run P3-8 capture, retrieval, P4L/N1/N2 reruns, support labeling, counterfactuals, policy tuning, selector/reranker work, P5, BEA-v1-A, runtime/default promotion, or broad retrieval. It does not modify the P3-8 evaluator, helper module, target evaluators, or runtime/retrieval files.

The public artifact contains only bucketed summaries. The private proxy files are intentionally ignored and are not committed.

## Compatibility

The current P3-8 schema does **not** accept these proxy fixtures as empirical frozen trace fixtures. P3-8G therefore authorizes only **BEA-v1-P3-8H Proxy Fixture Compatibility Preflight — no capture execution**, where the proxy-mode acceptance or rejection decision can be made without trace capture.

## Artifact

- Script: `eval/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke.py`
- Report: `artifacts/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke/bea_v1_p3_8g_frozen_event_proxy_fixture_materialization_smoke_report.json`
