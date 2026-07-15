# Product Stack Bakeoff — B2.4 Fresh Qualified Holdout Protocol

Date: 2026-07-16

Status: `product_bakeoff_b24_execution_failed_closed_no_result`

B2.4 is closed without a tournament result. The corrected launcher crossed the formal attempt boundary only after worker entry and qualified-runner admission, but the single frozen run stopped after two of 48 complete groups. In the incomplete next group, production BM25 receipts reported nonzero skipped invalid hits; the frozen parser requires this counter to remain zero, so the execution-integrity gate rejected those contexts and the runner terminated before the complete matrix, scoring, ranking, shortlist selection, or any product-default decision. Private terminal evidence is frozen, and no restart or retry is authorized.

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
- [`product_bakeoff_b24_launcher_preexecution_correction.json`](../../artifacts/product_bakeoff_b24_prelaunch_correction/product_bakeoff_b24_launcher_preexecution_correction.json)
- [`product_bakeoff_b24_holdout_readiness.json`](../../artifacts/product_bakeoff_b24_readiness/product_bakeoff_b24_holdout_readiness.json)
- [`product_bakeoff_b24_failed_closed_aggregate.json`](../../artifacts/product_bakeoff_b24/product_bakeoff_b24_failed_closed_aggregate.json)
- [`product_bakeoff_b24_bm25_tokenizer_repair.json`](../../artifacts/product_bakeoff_b24_repair/product_bakeoff_b24_bm25_tokenizer_repair.json)

## Parent locks

B2.4 locks the aggregate-only B2.1 failed-closed result, including its two incomplete attempts, zero scoring, and absence of a tournament result. It also locks the exact passed B2.3 runner-qualification artifact. That artifact authorizes fresh holdout authoring but explicitly does not authorize tournament execution.

The same qualified machine instance must be used for the future tournament. Its exact profile, identifier, and storage location remain private. The private qualification receipt is revalidated immediately before execution; a changed stable profile closes the launch.

## Fresh holdout boundary

The final private frame contains 12 repository snapshots and 48 newly authored logical tasks: Rust, Python, and TypeScript crossed with small, medium, large, and xlarge visible-source bands, with four task roles per repository. Every selected repository slug and `(slug, commit)` identity must be absent from both the B2 and B2.1 empirical frames and from the closed preflight/qualification exclusion registry.

Each of the 12 slots has at least two candidates whose order and expected license are frozen before authoring. Failover may occur only before any treatment output. The inherited offline B2 author creates all queries and oracle rows without adapter output. No final task may be executed before the repository, task, oracle, source, runtime, timeout, and qualification bindings are frozen.

## Corrected freeze and replacement readiness

Private authoring completed on the same qualified machine. The first aggregate checkpoint was superseded before treatment because its pre-launch validator did not reproduce the parent B2.3 private-receipt serialization. B2.3 hashes the closed receipt shape with `private_receipt_digest` present and empty; B2.4 had removed that field. The corrected validator now reproduces the parent serialization exactly, and its self-test consumes a receipt built by the parent B2.3 implementation.

The prior readiness, freeze receipt, and launch authorization were invalidated with zero treatment output. The unchanged private manifests were re-frozen against the corrected runtime. This replacement readiness confirms 12 selected repository snapshots, 48 logical tasks, and 48 oracle records; zero overlap with 24 historical empirical repositories and the closed exclusion registry; 24 excluded repositories and one excluded synthetic source; and zero provider calls, scoring, ranking, or logical treatment records. No repository identity, candidate order, failover detail, task text, query, path, oracle row, or private digest is published.

## Pre-execution launcher correction

The superseded readiness commit `e516f059592405289caf0124034759d6cf6769e5` passed CI run `29446543053`, the exact qualified machine profile was revalidated with zero stable changes, and a private launch authorization was created. The launcher wrote a PID receipt and returned an acknowledgement, but its background handoff invoked the tracked mode-`100644` script directly instead of through `bash`. The operating system rejected the handoff before worker entry. No full-run entrypoint, runner admission, launch release, runs directory, task treatment, or provider call occurred.

The corrected launcher resolves its own absolute path and invokes it explicitly through `bash`. It does not report success after merely writing a PID. The worker first writes a private entry receipt, the runner validates all frozen inputs and the qualified machine and writes its admission receipt, and only then may the launcher atomically issue a private launch release. That release, after runner admission, is the formal tournament-attempt boundary. A CI probe exercises this exact background handoff while the tracked script remains non-executable. The old launch authorization and readiness are superseded; the unchanged holdout has now been rebound without reauthoring, re-frozen against the corrected source, and represented by the replacement readiness artifact above.

## Formal attempt and terminal integrity failure

Replacement readiness commit `20d279a39eda578ba4027fbaec3da6b6065279a1` passed CI run `29453549335`. A new private launch authorization was bound to that checkpoint, the qualified machine was revalidated, the worker entered, the runner admitted the frozen inputs, and the launcher issued the attempt-1 release. The formal tournament boundary was therefore crossed exactly once.

The process completed two of 48 groups, with 60 logical records at the last completed-group boundary. During the incomplete next group, the production BM25 receipts reported that invalid hits had been skipped. The inherited strict parser freezes `invalid_hits_skipped == 0`; a nonzero value is not silently accepted because it means the retrieval result omitted source-invalid cells. The affected context executions therefore became failed results, and the own-parent scoreability boundary stopped the runner. This was not a provider/model failure or a CPU, memory, disk-capacity, timeout, or launcher failure.

The full 1,440-record matrix does not exist. No pre-score gate, scorer, ranking, shortlist, or default decision ran. The terminal exit code is 1, private failure evidence has been frozen separately, and the protocol forbids restart, resume, selective rerun, recomputation, integrity-gate relaxation, or reuse of incomplete output after the formal boundary.

## Post-closeout engineering repair

Private terminal evidence and a source-only synthetic reproduction isolated a cross-layer tokenizer mismatch. The B2 author and the production identifier predicate both admitted exact identifiers beginning with an underscore, while the persistent BM25 line verifier used an independent splitter that discarded every token beginning with `_`. Tantivy still retrieved matching indexed documents, but line verification received an empty token set and counted the hits as invalid. The zero-invalid-hit gate behaved correctly by rejecting that envelope.

Repair checkpoint `665fd51bba0eae52ade8d5f3c37069217de38916` removed the independent splitter. Persistent BM25 now resolves and reuses the actual tokenizer configured for the indexed content field, so indexing, query parsing, and current-source line verification share one token contract. Regression coverage includes the ordinary persistent search path, the reusable index handle, and the real `bakeoff-query` CLI envelope. The core index suite passed 136/136, the CLI suite passed 52/52, clippy passed with warnings denied, and Linux retrieval CI run `29457607093` succeeded.

This engineering repair does not reopen B2.4 or convert its incomplete output into a result. It authorizes only the design of a separately preregistered B2.5 with a fresh holdout, explicit B2.4 repository exclusion, a source-only query compatibility gate bound before treatment, and repaired-runtime qualification.

## Experimental design

The independent unit is one logical task (`n=48`). Repository is a nested cluster. Four repetitions and cold/warm cache observations are technical repeated measurements, not additional independent units. All six S0–S5 treatments run every task as a randomized complete task block on one qualified machine, using the inherited seeded schedule and repository split-plot lifecycle.

No arm or group sharding, interim quality look, adaptive elimination, task replacement, selective retry, missing-cell imputation, or cross-machine migration is permitted. Exact equal quality or resource vectors receive shared competition ranks; a unique winner is never forced.

## Long-run timeout bridge

B2.1 failed twice at the same short timeout boundary. B2.3 raised the outer phase limit to 600 seconds, but the inherited adapter command layer still carried the old 25-second cap. B2.4 freezes both layers explicitly: the request/worker limit is 600 seconds and the inner prepare/index/query command limit is 570 seconds. The inner limit remains below the outer limit so the parent harness retains fail-closed control.

This timeout bridge applies identically to every arm and to prepare, index, context, and support operations. It is frozen before private authoring and cannot be changed after any treatment output.

## Execution and monitoring

The tournament ran as one standalone process under `nohup`, not as a private GitHub Actions job. Its replacement aggregate-only readiness checkpoint was committed and passed public CI before the private launch authorization bound that checkpoint and CI run to the re-frozen private inputs and corrected runtime.

There was exactly one formal tournament attempt. Monitoring was limited to process state, completed-group count, logical-record count, and terminal state. After the launch release, the terminal integrity failure closed B2.4 without a result; no restart, resume, selective rerun, recomputation, launcher edit, timeout edit, integrity-gate edit, or task/oracle edit is permitted.

## Privacy and publication

Repository identities, candidate order and failover, task text, queries, paths, ranges, oracle rows, private manifests, freeze/runtime/launch/failure-evidence digests, partial-group details, per-task output, exact runner profile, and private locations remain private. The public closeout contains only the preregistered progress boundary, terminal state, fixed aggregate failure category, and no-result decision. No arm-level, quality, resource, or ranking metric is published because the complete matrix and pre-score gates did not pass.

## Frozen public identifiers

- B2.4 spec digest: `b24spec_52eefc930fac34f5`
- B2.4 source bundle digest: `b24src_301e5a211de015d86e2607e68d12f69afaf4474fa5f62fdd68d1c0a58f6c634f`
- B2.4 holdout-frame digest: `b24frame_429a87368330b5c33c8c30a771fd5f62c2f445d9408598bf25cbf0d0fad64d07`
- Inherited execution-schedule digest: `b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3`
- B2.4 protocol-report digest: `b24protocol_ec4bc650b509781477fde7cf2c6bf5532221d86e3379364a1df8741570a5c222`
- Launcher-correction checkpoint and CI: `dbeb244f96d9da7aa47b256153d5f5af0e14e481`, run `29449579106` (`success`)
- Replacement readiness digest: `b24ready_86eb4cfe65fed9e38af6f2ce3c369afb257a05055747c17446cad89028718fc0`
- Replacement readiness checkpoint and CI: `20d279a39eda578ba4027fbaec3da6b6065279a1`, run `29453549335` (`success`)
- Failed-closed aggregate digest: `b24failure_a41d6e150a5e5c2752cfb455b0ca5dd1df35687b9489d82e5a888362dc4c4b83`
- Post-closeout BM25 repair digest: `b24repair_2a4e664f19e8c72de3f6f4b09f4476f5313c01b547bbb141cb5c26a394473136`
- BM25 repair checkpoint and CI: `665fd51bba0eae52ade8d5f3c37069217de38916`, run `29457607093` (`success`)
- Corrected protocol checkpoint and CI: `66f55e5b334a13045413b668c1b8fb4dff33af7f`, run `29446095850` (`success`)
- Superseded pre-correction readiness digest: `b24ready_9655d18430c0e8f7e2248a79a403a3847dc378de431ddf6d16867ff21ed31655`
- Superseded readiness checkpoint and CI: `cc0cbc15476809b735b3c958214b525a2790e0bf`, run `29445399981` (`success`), zero treatment output
- Pre-execution launcher-correction digest: `b24prelaunchfix_4442014a2b02de507b1a27a3ff3bc4b8cb9d403c2aa67ac49663ad0a7fd21461`
- Superseded erroneous closeout: checkpoint `e28275987d05101034ce9c8f6aba42bc986faee8`, CI run `29447560057` (`success`), aggregate digest `b24failure_96446da70f2e8d9afd0e6009e04f8b5e3f94699828de88731c37520e292cd672`

## Next authorized action

Keep B2.4 closed as `failed_closed_no_result`. Design B2.5 as a separately preregistered tournament with a fresh holdout, exclusion of every B2.4 repository identity, a source-only query-token compatibility gate bound at authoring, freeze, readiness, and runner admission, and a synthetic qualification of the repaired runtime before any private authoring or treatment output.
