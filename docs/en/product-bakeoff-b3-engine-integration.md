# Product Bakeoff B3 Runner/Scorer Engine Integration

Date: 2026-07-17

Status: `product_bakeoff_b3_runner_scorer_integration_complete_no_runtime_no_holdout_no_execution_no_result`

This phase turns the B3 preregistration into executable runner/scorer mechanics without touching any historical B2, B2.1, B2.4, or B2.5 module. It does not qualify a runtime, author a private holdout, authorize execution, produce treatment output, score a tournament, or change the B2.5 terminal `failed_closed_no_result` conclusion.

The public aggregate is [`product_bakeoff_b3_engine_integration.json`](../../artifacts/product_bakeoff_b3_engine_integration/product_bakeoff_b3_engine_integration.json). The implementation is split between [`product_bakeoff_b3_runner.py`](../../eval/product_bakeoff_b3_runner.py) and [`product_bakeoff_b3_scorer.py`](../../eval/product_bakeoff_b3_scorer.py).

Parent protocol checkpoint `291c5a0041d94224a6dfff10838c6ed50110ddb4` passed cross-platform CI run `29565270451` before this integration phase began.

## Runner integration

The B3 runner reuses the frozen B2.1 execution loop because that loop already implements the expensive and safety-critical mechanics:

- isolated six-arm execution;
- source-currentness and writable-state-root checks;
- record validation and scoreability;
- repository split-plot lifecycle and exact index-build counts;
- same-arm own-parent support lineage;
- cross-arm static fairness;
- zero provider/network calls;
- scorer/oracle import isolation.

Only two historical hooks are replaced inside a bounded single-process context:

1. the historical schedule factory/digest is replaced by the preregistered B3 Williams schedule;
2. the historical exact semantic gate is replaced by the B3 shared score-and-routing repeatability gate.

The B2.4 long-run envelope continues to provide the qualified long-run adapters and nested request/child-command timeouts. A future B3 outer launch layer must provide a closed freeze-receipt validator before the engine can run.

Every injected function is identity-checked before replacement and restored in `finally`, including when the enclosed run raises. Nested or pre-existing overrides fail closed. The historical files remain byte-unchanged.

The B2.1 execution-key gate still validates the exact ordered 1,440-record list. Because that list is built while the B3 schedule is injected, arm order, task order, repetition, cache state, operation order, and group completeness remain bound to the Williams schedule rather than only to the repeatability projection.

## Scorer integration

The B3 scorer calls `product_bakeoff_b3_repeatability.canonicalize_for_scoring` directly. It does not call either historical B2.1 exact-hash canonicalizer.

After the shared canonicalizer validates all 360 logical groups and selects one quality representative per group, the scorer reuses only these frozen mechanics:

- B2 oracle/task scoring;
- B2.1 own-parent terminal support scoring;
- arm-level count and fixed-point aggregation;
- warm query, RSS, cold index, and index-state percentile calculations;
- component-earned inclusion gates;
- separate quality and resource competition ranks;
- shared exact ties and decision-equivalent co-finalists.

The scorer refuses to run before all runner gates pass, before the 1,440-record logical matrix is complete, or when repository/task/freeze/oracle bindings are absent or drifted. Public tournament-result construction remains deliberately unimplemented until readiness and launch authorization are frozen.

## Proof that the hidden old gate is gone

The synthetic end-to-end fixture contains all 360 logical score groups and 1,440 observations. Every group has deliberately different historical diagnostic semantic hashes across its four repetitions while preserving the B3 score/routing projection.

On exactly that fixture:

- the frozen historical B2.1 semantic gate fails;
- the B3 runner gate passes all 360 groups and privately counts 360 diagnostic-drift groups;
- the B3 scorer selects repetition 1 for all 360 groups through the same canonicalization core;
- the historical B2.1 scorer canonicalizers are replaced with functions that raise immediately if called, yet B3 scorer canonicalization still passes;
- a duplicate second target with the same target-line union is rejected because it changes single-target support routing;
- a wholly missing group or wrong repetition/cache signature is rejected.

This is a behavioral integration proof. The runner and scorer no longer merely claim to share a policy; tests make the old exact-hash path unusable and verify that the B3 path still works.

## Separation of quality and resources

The shared canonicalizer selects one representative only for logical quality scoring. It does not collapse or require equality of resource observations. All valid cold/warm/repetition timing and memory measurements remain in the frozen B2.1 resource populations.

Diagnostic serialization drift is privately countable but cannot change the quality result when score/routing semantics are identical. Source, fairness, lineage, provider isolation, completeness, and runtime measurements remain independent gates and are never inferred from the projection.

## Validation

Local validation covers:

- 360 expected groups and 1,440 expected observation signatures;
- successful schedule/gate injection and restoration;
- restoration after an injected exception;
- rejection of nested override, missing task, duplicate task identity, target-cardinality drift, missing logical group, and scorer-before-gates;
- inherited B2.1 runner and scorer self-tests/fault tests;
- a poisoned historical scorer-canonicalization path that is proven unused.

The public integration digest is `b3engine_a61e54a2fe426f00ac081345ce379300b4cf8c59bdbcc43eca99f9f104579535`.

## Remaining work and server state

The server should remain off. The next offline phase must implement and fault-test:

1. the B3 private freeze and aggregate-only readiness contract;
2. launch admission and the first-durable-treatment-observation boundary receipt;
3. the CLI and disconnect-safe launcher;
4. public synthetic runtime qualification and startup handshakes;
5. the final public result/failed-closeout boundary.

Only after those local surfaces are frozen and CI-green should the server be started for exact Linux runtime qualification. No private holdout exists yet, and execution remains unauthorized.
