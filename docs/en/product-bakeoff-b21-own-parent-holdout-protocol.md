# Product Stack Bakeoff — B2.1 Own-Parent Holdout Protocol

Date: 2026-07-15

Status: `product_bakeoff_b21_protocol_frozen_no_execution_no_result`

B2.1 is a new confirmatory holdout tournament, not a repair or continuation of the incomplete B2 matrix. B2 failed closed before scoring because the six valid context outputs for a two-step task did not share one source path. B2.1 preserves that target divergence as part of the treatment effect: each arm's support step follows only that arm's own same-execution context target.

The executable protocol and public design report are:

- [`product_bakeoff_b21_protocol.py`](../../eval/product_bakeoff_b21_protocol.py)
- [`product_bakeoff_b21_protocol_report.json`](../../artifacts/product_bakeoff_b21_protocol/product_bakeoff_b21_protocol_report.json)

## Parent lock and non-reuse boundary

B2.1 is bound to the B2 implementation checkpoint `55e0ebaaaf6f25c5c7d5c13ffc6ee58825e7d915` and failed-closed closeout checkpoint `07bfd116622bd0ed9a2bc654abec3bb98a7f38df`. B2's 24 observed context records remain unscored and cannot be resumed, repaired, imputed, or reused.

The new empirical frame must contain 12 repository identities absent from the B2 frame and 48 newly authored task/oracle rows. The B2 task margins and offline authoring rules are inherited unchanged, so the failure is not used to tune task families, queries, or labels. Final holdout tasks cannot be executed by any arm before the B2.1 runtime freeze.

## Experimental unit and lifecycle

The independent unit remains one logical task (`n=48`). Repository is a nested cluster. Cache state and four repetitions are technical repeated measurements, not additional independent observations. All six S0–S5 stacks run every task in a randomized complete block, with the same repository split-plot lifecycle, rotating cold task, 288 index builds, and 1,440 logical records.

## Own-parent two-step policy

For each two-step task, all six context steps run first in frozen arm order. Each normal support request is bound to the accepted context target from the same arm, task, repetition, and episode. Paths and ranges may differ across arms. No majority vote, intersection, oracle-fixed common parent, or cross-arm substitution is permitted.

If an accepted context outcome does not provide exactly one ready primary target, the harness emits a closed `parent_unavailable` support-opportunity record. It counts as support and task failure but does not abort the complete matrix. A rejected, timed-out, or malformed context remains an infrastructure-invalid run and fails closed.

The fairness gate still requires identical task query, source visibility, budget, timeout, cache label, and split-plot lifecycle. Support parent fields may differ only because they are derived from each arm's own context output. Context fingerprints remain equal across arms; support comparison uses a static fingerprint that excludes treatment-mediated parent fields and separately verifies same-arm lineage.

## Scoring and promotion

Task-level quality, component earn-in rules, non-inferiority limits, resource ceilings, eligibility floors, tie handling, and zero/one/multiple-finalist outcomes remain inherited from B2. A two-step task succeeds only when that arm's context target is oracle-valid and its same-arm support output matches a frozen relation. Terminal support opportunities are failures and are reported at arm aggregate; they are excluded from query-latency percentiles so a missing parent is neither rewarded nor imputed as a measured query.

No interim quality looks, early elimination, task replacement, selective rerun, or rule switch are allowed. Scoring remains isolated until the complete logical matrix, source, lineage, resource, zero-network, determinism, and privacy gates pass.

## Privacy boundary

Repository identities, task text, queries, paths, ranges, oracle rows, private manifest/freeze digests, per-task divergence, per-cell resources, and private run paths remain private. Public output is arm-level and predeclared-stratum aggregate only. B2.1 CI receives no private holdout inputs and runs only public protocol/implementation tests and report validation.

## Frozen identifiers

- B2.1 spec digest: `b21spec_a4460a279280e872`
- B2.1 source bundle digest: `b21src_76e3433599291e9061c4449b32557b9a3ad2998cfc0a739f69a5632a4e47b7d3`
- B2.1 holdout-frame digest: `b21frame_f50eda42c3403eb877e46a07b257a8a0ce8930759422c7536963f7d96eee8571`
- B2.1 execution-schedule digest: `b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3`
- B2.1 protocol-report digest: `b21protocol_f1c833bfe2bae7d0ca11c15b6ba5c62650adde88f399217b6171e7156a61d7b7`

## Next authorized work

Implement the fresh-holdout admission overlay, same-arm lineage runner, terminal support record, isolated scorer, and aggregate-only result validator. Pass synthetic tests, fault injection, and unused-repository real-source preflight before materializing the final holdout frame. No B2.1 empirical result exists at this checkpoint.
