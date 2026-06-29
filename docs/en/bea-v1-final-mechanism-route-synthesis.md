# BEA-v1 Final Mechanism Route Synthesis

Date: 2026-06-29

BEA-v1 Final Mechanism Route Synthesis closes the current autonomous BEA-v1 mechanism route after N6XFR-D. It is not a new experiment and not a new control-plane chain. It reads only committed public artifacts, performs no OpenLocus execution, retrieval, rerun, build, candidate generation, materialization, selector/reranker work, counterfactual, private read, or policy/runtime change.

## Result

```text
status: bea_v1_mechanism_route_synthesis_complete_blocked_on_external_empirical_inputs
self-test: 14 / 14
forbidden scan: pass
route closures: 4 / 4
next allowed phase: await_external_empirical_inputs_or_new_research_directive
autonomous next experiment authorized: false
```

## Empirical anchors

- P4L validated the frozen P4 scheduler on the locked non-Python denominator: baseline reach 0 over 272 and frozen scheduler reach 52 over 272 under the locked validation boundary.
- N1 showed the 40-case span-refiner opportunity is rank-blocked: top-10 actionable 0 over 40 and rank-blocked 40 over 40.
- N2 localized those 40 rank-blocked cases to extra-depth append / merge-order blocking.
- N3 tested simple deterministic merge-order designs; the best recovered 10 over 40 against a 20-case pass gate, so simple merge-order designs are insufficient.
- N4 confirmed the fixed-pool rank-blocker denominator is adequate and freezes 40 eligible cases for fixed-pool preflight.

## Closed routes

1. **P1 support-label route**: P1-3 produced intake-valid automated proxy labels, but P1-4 found them low-evidence and P1-5R found no private context linkage. Unlock requires real private source/context linkage for support labels.
2. **P2/P3 trace-surface route**: P2-0 found no P4L private arm rows, P2-1 was aggregate-only for ordered-prefix stop evidence, P2-2 found no same-file/risk traces, P2-3 closed the late trace route, and P3-8PS found no existing empirical event source. Unlock requires an empirical frozen event source declaration plus materialized fixtures.
3. **Fixed-pool rank-order route**: N5 preflight was authorized from the N4 denominator, but N6 found exact public per-case arm outcome fields missing, N6F defined the 160-row schema, and N6G found no exact public source. Unlock requires exact public 160-row N6 arm outcomes.
4. **Full-frozen reconstruction route**: N6XR found no bounded replay mapping, N6X-FR preflight was blocked by missing prerequisites, N6XFR-B found build/network and private-input blockers, N6XFR-C recovered the release binary, and N6XFR-D found zero private reconstruction input candidates. Unlock requires FD1/P4L/N-series private reconstruction inputs.

## Conclusion

The current route is exhausted under available public and local inputs. This is not a failure of effort and not evidence that the method cannot work; it is a data-source boundary. Future work requires one of the real external inputs above, not another schema-only autonomous phase.

## Artifact

- Script: `eval/bea_v1_final_mechanism_route_synthesis.py`
- Report: `artifacts/bea_v1_final_mechanism_route_synthesis/bea_v1_final_mechanism_route_synthesis_report.json`
