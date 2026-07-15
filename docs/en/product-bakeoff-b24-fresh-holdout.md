# Product Stack Bakeoff — B2.4 Fresh Qualified Holdout Protocol

Date: 2026-07-16

Status: `product_bakeoff_b24_execution_failed_closed_no_result`

B2.4 was a new confirmatory tournament envelope after B2.1 failed closed and the B2.3 constrained Linux runner passed its public qualification. The private holdout and runtime were frozen, the corrected aggregate readiness checkpoint passed CI, and a private launch authorization was created. The single standalone launch was acknowledged, but its `nohup` worker handoff tried to execute a tracked `100644` shell script directly and was rejected before the worker entered. No runner admission, runs directory, treatment output, score, rank, shortlist, or product-default decision exists. The preregistered one-attempt and infrastructure-failure rules close B2.4 without a result.

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
- [`product_bakeoff_b24_holdout_readiness.json`](../../artifacts/product_bakeoff_b24_readiness/product_bakeoff_b24_holdout_readiness.json)
- [`product_bakeoff_b24_failed_closed_aggregate.json`](../../artifacts/product_bakeoff_b24/product_bakeoff_b24_failed_closed_aggregate.json)

## Parent locks

B2.4 locks the aggregate-only B2.1 failed-closed result, including its two incomplete attempts, zero scoring, and absence of a tournament result. It also locks the exact passed B2.3 runner-qualification artifact. That artifact authorizes fresh holdout authoring but explicitly does not authorize tournament execution.

The same qualified machine instance must be used for the future tournament. Its exact profile, identifier, and storage location remain private. The private qualification receipt is revalidated immediately before execution; a changed stable profile closes the launch.

## Fresh holdout boundary

The final private frame contains 12 repository snapshots and 48 newly authored logical tasks: Rust, Python, and TypeScript crossed with small, medium, large, and xlarge visible-source bands, with four task roles per repository. Every selected repository slug and `(slug, commit)` identity must be absent from both the B2 and B2.1 empirical frames and from the closed preflight/qualification exclusion registry.

Each of the 12 slots has at least two candidates whose order and expected license are frozen before authoring. Failover may occur only before any treatment output. The inherited offline B2 author creates all queries and oracle rows without adapter output. No final task may be executed before the repository, task, oracle, source, runtime, timeout, and qualification bindings are frozen.

## Corrected freeze and replacement readiness

Private authoring completed on the same qualified machine. The first aggregate checkpoint was superseded before treatment because its pre-launch validator did not reproduce the parent B2.3 private-receipt serialization. B2.3 hashes the closed receipt shape with `private_receipt_digest` present and empty; B2.4 had removed that field. The corrected validator now reproduces the parent serialization exactly, and its self-test consumes a receipt built by the parent B2.3 implementation.

The prior readiness, freeze receipt, and launch authorization were invalidated with zero treatment output. The unchanged private manifests were re-frozen against the corrected runtime. This replacement readiness confirms 12 selected repository snapshots, 48 logical tasks, and 48 oracle records; zero overlap with 24 historical empirical repositories and the closed exclusion registry; 24 excluded repositories and one excluded synthetic source; and zero provider calls, scoring, ranking, or logical treatment records. No repository identity, candidate order, failover detail, task text, query, path, oracle row, or private digest is published.

## Terminal launch failure and closeout

Execution was gated on readiness commit `e516f059592405289caf0124034759d6cf6769e5` and successful CI run `29446543053`. The exact qualified machine profile was revalidated with zero stable changes, and attempt-1 launch authorization was created. The launcher wrote its PID receipt and returned an acknowledgement, but the tracked launcher file was mode `100644`; its background handoff invoked that file directly instead of through `bash`. `nohup` therefore stopped at the operating-system permission boundary. The worker did not enter, the full-run entrypoint did not run, no runner-admission receipt or runs directory was created, and treatment output remained zero.

B2.4 preregistered one tournament attempt and required infrastructure failure to close without a result. The launch is therefore not repaired or repeated inside B2.4, even though no task was exposed to a treatment. Private failure evidence is frozen separately; only the aggregate boundary above is public.

## Experimental design

The independent unit is one logical task (`n=48`). Repository is a nested cluster. Four repetitions and cold/warm cache observations are technical repeated measurements, not additional independent units. All six S0–S5 treatments run every task as a randomized complete task block on one qualified machine, using the inherited seeded schedule and repository split-plot lifecycle.

No arm or group sharding, interim quality look, adaptive elimination, task replacement, selective retry, missing-cell imputation, or cross-machine migration is permitted. Exact equal quality or resource vectors receive shared competition ranks; a unique winner is never forced.

## Long-run timeout bridge

B2.1 failed twice at the same short timeout boundary. B2.3 raised the outer phase limit to 600 seconds, but the inherited adapter command layer still carried the old 25-second cap. B2.4 freezes both layers explicitly: the request/worker limit is 600 seconds and the inner prepare/index/query command limit is 570 seconds. The inner limit remains below the outer limit so the parent harness retains fail-closed control.

This timeout bridge applies identically to every arm and to prepare, index, context, and support operations. It is frozen before private authoring and cannot be changed after any treatment output.

## Execution and monitoring

The tournament was configured as one standalone process under `nohup`, not a private GitHub Actions job. Its aggregate-only readiness checkpoint was committed and passed CI before a private launch-authorization receipt bound the readiness commit and CI run to the frozen private inputs and runtime.

There was exactly one tournament attempt. The worker handoff failed before treatment output, but the protocol also states that infrastructure failure closes without a result; no second launch, restart, resume, selective rerun, recomputation, launcher edit, timeout edit, or task/oracle edit is authorized inside B2.4. Monitoring exposed only process state and zero progress counts; no interim arm, quality, resource, or ranking metric was inspected.

## Privacy and publication

Repository identities, candidate order and failover, task text, queries, paths, ranges, oracle rows, private manifests, freeze/runtime/launch digests, per-task output, exact runner profile, and private locations remain private. The holdout readiness artifact may publish only preregistered counts and boolean gates. A tournament result may be published only after the full 1,440-record matrix and every pre-score gate pass, and even then only arm-level and preregistered-stratum aggregates are allowed.

## Frozen public identifiers

- B2.4 spec digest: `b24spec_d64f8821238a58ec`
- B2.4 source bundle digest: `b24src_9fef21caad5def69af3c381d51018a2d8cfe4a48361babe71458b9f7283eff76`
- B2.4 holdout-frame digest: `b24frame_429a87368330b5c33c8c30a771fd5f62c2f445d9408598bf25cbf0d0fad64d07`
- Inherited execution-schedule digest: `b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3`
- B2.4 protocol-report digest: `b24protocol_c1afab8cf3c64cfca78f55e5fefd6b84cdd430c9e6c78cd36af2c0bacf7c6b4f`
- Corrected protocol checkpoint and CI: `66f55e5b334a13045413b668c1b8fb4dff33af7f`, run `29446095850` (`success`)
- Replacement readiness digest: `b24ready_9655d18430c0e8f7e2248a79a403a3847dc378de431ddf6d16867ff21ed31655`
- Superseded readiness checkpoint and CI: `cc0cbc15476809b735b3c958214b525a2790e0bf`, run `29445399981` (`success`), zero treatment output
- Failed-closed aggregate digest: `b24failure_96446da70f2e8d9afd0e6009e04f8b5e3f94699828de88731c37520e292cd672`

## Next authorized action

Close B2.4 as `failed_closed_no_result`. Do not relaunch, resume, repair, score, or reuse its launch authorization. Any later product tournament must be separately preregistered with an explicit disconnect-safe launcher gate and an explicit, pre-launch decision about whether the still-unopened private holdout may be retained.
