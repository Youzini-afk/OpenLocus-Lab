# Product Stack Bakeoff — B2.4 Fresh Qualified Holdout Protocol

Date: 2026-07-15

Status: `product_bakeoff_b24_prelaunch_receipt_validation_corrected_no_treatment_output`

B2.4 is a new confirmatory tournament envelope after B2.1 failed closed and the B2.3 constrained Linux runner passed its public qualification. The private B2.4 holdout has been authored, but the first readiness checkpoint is superseded before execution because a pre-launch validator did not reproduce the parent B2.3 private-receipt hash serialization. This correction checkpoint contains no treatment output, score, rank, shortlist, or product-default decision.

The executable public contract is:

- [`product_bakeoff_b24_protocol.py`](../../eval/product_bakeoff_b24_protocol.py)
- [`product_bakeoff_b24_corpus.py`](../../eval/product_bakeoff_b24_corpus.py)
- [`product_bakeoff_b24_runner.py`](../../eval/product_bakeoff_b24_runner.py)
- [`product_bakeoff_b24_scorer.py`](../../eval/product_bakeoff_b24_scorer.py)
- [`product_bakeoff_b24_readiness.py`](../../eval/product_bakeoff_b24_readiness.py)
- [`product_bakeoff_b24_cli.py`](../../eval/product_bakeoff_b24_cli.py)
- [`product_bakeoff_b24_linux_longrun.sh`](../../scripts/product_bakeoff_b24_linux_longrun.sh)
- [`product-bakeoff-b24-holdout.yml`](../../.github/workflows/product-bakeoff-b24-holdout.yml)
- [`product_bakeoff_b24_protocol_report.json`](../../artifacts/product_bakeoff_b24_protocol/product_bakeoff_b24_protocol_report.json)

## Parent locks

B2.4 locks the aggregate-only B2.1 failed-closed result, including its two incomplete attempts, zero scoring, and absence of a tournament result. It also locks the exact passed B2.3 runner-qualification artifact. That artifact authorizes fresh holdout authoring but explicitly does not authorize tournament execution.

The same qualified machine instance must be used for the future tournament. Its exact profile, identifier, and storage location remain private. The private qualification receipt is revalidated immediately before execution; a changed stable profile closes the launch.

## Fresh holdout boundary

The final private frame contains 12 repository snapshots and 48 newly authored logical tasks: Rust, Python, and TypeScript crossed with small, medium, large, and xlarge visible-source bands, with four task roles per repository. Every selected repository slug and `(slug, commit)` identity must be absent from both the B2 and B2.1 empirical frames and from the closed preflight/qualification exclusion registry.

Each of the 12 slots has at least two candidates whose order and expected license are frozen before authoring. Failover may occur only before any treatment output. The inherited offline B2 author creates all queries and oracle rows without adapter output. No final task may be executed before the repository, task, oracle, source, runtime, timeout, and qualification bindings are frozen.

## Superseded readiness checkpoint and correction

Private authoring completed on the same qualified machine. The superseded aggregate checkpoint confirmed 12 selected repository snapshots, 48 logical tasks, and 48 oracle records, with zero overlap against the 24 historical empirical repositories or the closed exclusion registry. It published an exclusion count of 24 and one excluded synthetic source, but no repository identity, candidate order, failover detail, task text, query, path, oracle row, or private digest.

The pre-launch gate then exposed a serialization mismatch: B2.3 hashes the closed private-receipt shape with `private_receipt_digest` present and empty, while the B2.4 validator removed that field before hashing. The validator now reproduces the parent serialization exactly and its self-test consumes a receipt built by the parent B2.3 implementation. The prior readiness and private launch authorization are invalidated before any treatment output; the unchanged private manifests must be re-frozen against this corrected runtime and a replacement aggregate readiness checkpoint must pass CI.

## Experimental design

The independent unit is one logical task (`n=48`). Repository is a nested cluster. Four repetitions and cold/warm cache observations are technical repeated measurements, not additional independent units. All six S0–S5 treatments run every task as a randomized complete task block on one qualified machine, using the inherited seeded schedule and repository split-plot lifecycle.

No arm or group sharding, interim quality look, adaptive elimination, task replacement, selective retry, missing-cell imputation, or cross-machine migration is permitted. Exact equal quality or resource vectors receive shared competition ranks; a unique winner is never forced.

## Long-run timeout bridge

B2.1 failed twice at the same short timeout boundary. B2.3 raised the outer phase limit to 600 seconds, but the inherited adapter command layer still carried the old 25-second cap. B2.4 freezes both layers explicitly: the request/worker limit is 600 seconds and the inner prepare/index/query command limit is 570 seconds. The inner limit remains below the outer limit so the parent harness retains fail-closed control.

This timeout bridge applies identically to every arm and to prepare, index, context, and support operations. It is frozen before private authoring and cannot be changed after any treatment output.

## Execution and monitoring

The future tournament is one standalone process under `nohup` or `screen`, not a private GitHub Actions job. A public aggregate-only readiness checkpoint must first be committed and pass CI. Only then may a private launch-authorization receipt bind that readiness commit and CI run to the frozen private inputs and runtime.

There is exactly one tournament attempt. Once any treatment output exists, process or machine restart, resume, complete restart, selective rerun, recomputation, timeout editing, or task/oracle editing closes B2.4 without a result. Monitoring may expose only process state, completed-group count, logical-record count, and terminal exit state; no interim arm, quality, resource, or ranking metric may be inspected.

## Privacy and publication

Repository identities, candidate order and failover, task text, queries, paths, ranges, oracle rows, private manifests, freeze/runtime/launch digests, per-task output, exact runner profile, and private locations remain private. The holdout readiness artifact may publish only preregistered counts and boolean gates. A tournament result may be published only after the full 1,440-record matrix and every pre-score gate pass, and even then only arm-level and preregistered-stratum aggregates are allowed.

## Frozen public identifiers

- B2.4 spec digest: `b24spec_d64f8821238a58ec`
- B2.4 source bundle digest: `b24src_9fef21caad5def69af3c381d51018a2d8cfe4a48361babe71458b9f7283eff76`
- B2.4 holdout-frame digest: `b24frame_429a87368330b5c33c8c30a771fd5f62c2f445d9408598bf25cbf0d0fad64d07`
- Inherited execution-schedule digest: `b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3`
- B2.4 protocol-report digest: `b24protocol_c1afab8cf3c64cfca78f55e5fefd6b84cdd430c9e6c78cd36af2c0bacf7c6b4f`
- Superseded readiness checkpoint and CI: `cc0cbc15476809b735b3c958214b525a2790e0bf`, run `29445399981` (`success`), zero treatment output

## Next authorized action

Commit this receipt-validation correction and obtain green public CI. Then invalidate the superseded private freeze and launch authorization, re-freeze the unchanged private manifests against the corrected source bundle, publish a replacement aggregate-only readiness checkpoint, and obtain another green CI run. Only then may one new private launch authorization be created and the single standalone tournament attempt begin.
