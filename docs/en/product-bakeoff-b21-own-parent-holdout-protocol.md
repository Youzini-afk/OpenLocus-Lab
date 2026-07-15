# Product Stack Bakeoff — B2.1 Own-Parent Holdout Protocol

Date: 2026-07-15

Status: `product_bakeoff_b21_implementation_ready_preflight_passed_no_holdout_no_result`

B2.1 is a new confirmatory holdout tournament, not a repair or continuation of the incomplete B2 matrix. Its holdout exclusion overlay, own-parent runner, terminal support outcome, isolated scorer, and aggregate-only publisher are now implemented. Three scenarios on two repositories excluded from the final holdout produced 36 logical records: ordinary support, six `parent_unavailable` terminals, and natural cross-path target divergence. All preflights passed with zero provider/network calls. The final 12-repository/48-task holdout has not been materialized or executed.

The executable protocol and public design report are:

- [`product_bakeoff_b21_protocol.py`](../../eval/product_bakeoff_b21_protocol.py)
- [`product_bakeoff_b21_corpus.py`](../../eval/product_bakeoff_b21_corpus.py)
- [`product_bakeoff_b21_runner.py`](../../eval/product_bakeoff_b21_runner.py)
- [`product_bakeoff_b21_scorer.py`](../../eval/product_bakeoff_b21_scorer.py)
- [`product_bakeoff_b21_cli.py`](../../eval/product_bakeoff_b21_cli.py)
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

Task-level quality, component earn-in rules, non-inferiority limits, resource ceilings, eligibility floors, tie handling, and zero/one/multiple-finalist outcomes remain inherited from B2. A two-step task succeeds only when that arm's context target is oracle-valid and its same-arm support output matches a frozen relation. Terminal support opportunities are failures and are reported at arm aggregate; their parent-wrapper measurements are excluded from query-latency and peak-RSS percentiles so a missing parent is neither rewarded nor mixed with an adapter execution measurement.

No interim quality looks, early elimination, task replacement, selective rerun, or rule switch are allowed. Scoring remains isolated until the complete logical matrix, source, lineage, resource, zero-network, determinism, and privacy gates pass.

## Privacy boundary

Repository identities, task text, queries, paths, ranges, oracle rows, private manifest/freeze digests, per-task divergence, per-cell resources, and private run paths remain private. Public output is arm-level and predeclared-stratum aggregate only. B2.1 CI receives no private holdout inputs and runs only public protocol/implementation tests and report validation.

## Frozen identifiers

- B2.1 spec digest: `b21spec_3d656619189a7531`
- B2.1 source bundle digest: `b21src_396d95d5fc098b6cbf7d11ce632d39244be28ac3a93328a803c137c2840ce7cf`
- B2.1 holdout-frame digest: `b21frame_b27001da8dcecb1552596f887fd4af93a319a95f7ce9ef60eb7f11d720d5c5d9`
- B2.1 execution-schedule digest: `b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3`
- B2.1 protocol-report digest: `b21protocol_6d747e5570920e1f2191fd673b9a55521bee6799de0a9d45ef4c96bf596b21bb`

## Next authorized work

Prepare a new 12-repository/48-task holdout frame excluding every B2 and real-preflight repository. Audit only its aggregate margins, freeze its private manifests and one runtime bundle, and then execute the full matrix once without interim quality inspection. No B2.1 empirical result exists at this checkpoint.
