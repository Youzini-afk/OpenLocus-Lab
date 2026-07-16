# Product Stack Bakeoff — B2.5 Fresh Tokenizer-Qualified Holdout

Date: 2026-07-16

Status: `product_bakeoff_b25_protocol_ready_runtime_qualification_pending_no_private_holdout_no_tournament_no_result`

B2.5 is a separately preregistered tournament. It does not reopen B2.4, score its incomplete output, reuse its exposed holdout, or reuse its launch authorization. The only inherited material is the already frozen B2.1 execution/scoring design and the aggregate engineering evidence that explains why B2.4 failed and how the production BM25 verifier was repaired.

The executable public contract is:

- [`product_bakeoff_b25_protocol.py`](../../eval/product_bakeoff_b25_protocol.py)
- [`product_bakeoff_b25_query_gate.py`](../../eval/product_bakeoff_b25_query_gate.py)
- [`product_bakeoff_b25_runtime_qualification.py`](../../eval/product_bakeoff_b25_runtime_qualification.py)
- [`product_bakeoff_b25_corpus.py`](../../eval/product_bakeoff_b25_corpus.py)
- [`product_bakeoff_b25_runner.py`](../../eval/product_bakeoff_b25_runner.py)
- [`product_bakeoff_b25_scorer.py`](../../eval/product_bakeoff_b25_scorer.py)
- [`product_bakeoff_b25_readiness.py`](../../eval/product_bakeoff_b25_readiness.py)
- [`product_bakeoff_b25_cli.py`](../../eval/product_bakeoff_b25_cli.py)
- [`product_bakeoff_b25_linux_longrun.sh`](../../scripts/product_bakeoff_b25_linux_longrun.sh)
- [`product-bakeoff-b25-holdout.yml`](../../.github/workflows/product-bakeoff-b25-holdout.yml)
- [`product_bakeoff_b25_protocol_report.json`](../../artifacts/product_bakeoff_b25_protocol/product_bakeoff_b25_protocol_report.json)

## Why B2.5 is a new tournament

B2.4 crossed its formal attempt boundary once and then stopped before the complete 1,440-record matrix. The strict production receipt parser correctly rejected a nonzero `invalid_hits_skipped` counter, so no scoring, ranking, shortlist, or product-default decision existed. That terminal state remains immutable.

The later engineering investigation found that the old persistent-BM25 line verifier used an independent query splitter. Exact identifiers beginning with `_` were accepted by the author and indexed by Tantivy, but the verifier discarded the leading-underscore token and rejected otherwise current hits. The repair makes indexing, query parsing, and line verification reuse the tokenizer configured for the indexed content field. The public parents are the [B2.4 failed-closed aggregate](../../artifacts/product_bakeoff_b24/product_bakeoff_b24_failed_closed_aggregate.json) and the [post-closeout BM25 repair aggregate](../../artifacts/product_bakeoff_b24_repair/product_bakeoff_b24_bm25_tokenizer_repair.json).

The repair is engineering evidence only. The B2.5 source bundle explicitly binds the repaired persistent-BM25 source file and its real `bakeoff-query` regression test, but a new confirmatory result still requires new repositories, new tasks, new oracle rows, a new freeze, a new readiness checkpoint, and one new formal attempt.

## Fresh holdout and historical exclusions

The final private frame still contains 12 repository snapshots and 48 logical tasks: Rust, Python, and TypeScript crossed with small, medium, large, and xlarge visible-source bands, with four frozen task roles per repository.

B2.5 excludes three complete historical frames: B2, B2.1, and B2.4. The union must contain exactly 36 distinct repository slugs and 36 distinct `(slug, commit)` identities. Every B2.5 candidate and selected repository must be outside that union and outside the closed preflight, qualification, practice, and synthetic-source exclusion registry. Every slot has at least two preregistered candidates, and all candidate identities are unique across slots.

The frozen B2 offline author remains the only task author. Candidate failover must finish before any treatment output. Repository identities, candidate order, failover decisions, task text, queries, paths, spans, and oracle rows remain private.

## Repaired-runtime qualification before private authoring

No private holdout may be authored until the repaired production binary passes a synthetic qualification on a Linux runner compatible with the frozen B2.3 runner class. Every stable parent-machine field except `cgroup_memory_limit_bytes` must match exactly. The memory limit may differ only when the current profile still passes the frozen B2.3 memory-limit and available-memory gates; CPU, storage, OS, toolchain, swap, and file-limit drift remain fail-closed. The OpenLocus binary bytes are deliberately requalified rather than required to match the pre-repair binary.

This narrow relocation allowance exists only before B2.5 runtime qualification. The resulting private B2.5 receipt freezes the complete current runner profile and binary, and runner admission immediately before the tournament must match that receipt exactly. No later machine migration is allowed.

The qualification uses no private input. It builds a tiny synthetic index and runs the actual production `bakeoff-query` surface through the strict production parser for four frozen categories:

- an ordinary identifier;
- an identifier beginning with `_`;
- an identifier split by punctuation;
- a one-character identifier.

Every case must return current EvidenceCore-backed BM25 evidence, execute the BM25 receipt, report zero stale hits skipped, report zero invalid hits skipped, and make zero provider or outbound calls. Exact synthetic queries, source, paths, binary digest, and runner profile stay in a private receipt. The public artifact contains only categories, counts, boolean gates, and a public qualification digest.

The aggregate runtime qualification must be committed and pass public CI before private authoring begins. Its publication checkpoint and CI run are then bound into the private holdout.

## Source-only query compatibility gate

After the offline author creates the new private task and oracle manifests, B2.5 runs a source-only compatibility gate before any retrieval adapter is executed. The gate mirrors Tantivy 0.25's `default` analyzer: Unicode alphanumeric runs, removal of tokens whose UTF-8 length is 40 bytes or more, and lowercase normalization.

All 48 queries must produce at least one production token. For every answerable oracle-positive span, at least one normalized query token must occur in the current frozen source line under the production line-verifier substring rule. No-answer tasks require a nonempty token set but have no positive span.

The private gate report contains no query text or source paths. It is created during authoring, recomputed byte-for-byte at freeze and readiness, and its file hash and private digest are bound into the holdout, freeze receipt, launch authorization, and runner admission. Runner admission verifies that binding without importing the oracle or running treatment retrieval.

## Freeze, readiness, and formal attempt boundary

The private freeze binds the fresh repository, task, and oracle manifests; the three historical repository locks; the exclusion registry; the query-gate report; the public and private runtime-qualification receipts; the current OpenLocus binary; the B2.5 source bundle; and the inherited 600-second outer / 570-second inner timeout contract.

Public readiness may expose only aggregate counts and boolean gates: 12 repositories, 48 tasks, 48 oracle records, 36 historical repositories excluded, zero overlap, frozen task margins, runtime qualification passed, query compatibility passed, and zero treatment output. It publishes no private manifest or gate digest.

After readiness is committed and CI is green, one private launch authorization may bind that checkpoint and CI run. The standalone Linux launcher writes a worker-entry receipt, waits for complete runner admission, and only then writes the private launch release. That release after admission—not the PID file or launcher acknowledgement—is the formal attempt boundary.

Before the release, a handoff or validation failure with zero treatment output does not consume the attempt. After the release, no restart, resume, selective retry, recomputation, missing-cell imputation, rule edit, timeout edit, task edit, oracle edit, or machine migration is allowed. A post-boundary failure closes B2.5 without a result.

## Experimental and scoring design

The independent unit is one logical task (`n=48`). Repository is a nested cluster; repetitions and cold/warm cache observations are technical repeated measurements. All six S0–S5 treatments run every task on one admitted machine using the inherited randomized complete task blocks and repository split-plot lifecycle.

The complete expected matrix contains 1,440 logical records and the inherited exact index-build count. There are no interim quality looks, adaptive arm eliminations, or arm/group sharding. Exact equal quality or resource vectors receive shared competition ranks; the scorer never forces a unique winner.

The oracle and scorer remain unloaded until the complete matrix and every pre-score integrity gate pass. Only then may the inherited B2.1 scorer produce an aggregate-only B2.5 result. Repository-level, task-level, per-cell, query, oracle, source-location, exact-runner, and private-digest output remains forbidden.

## Frozen public identifiers

- B2.5 spec digest: `b25spec_1603e85ac197760b`
- B2.5 source bundle digest: `b25src_f293d24c0f3aab207af3571ea3d0bd7a3d7992818f879c217ce5042883cd66d4`
- B2.5 holdout-frame digest: `b25frame_23661bee3726c4b52d6381bee3ad7ea857ca396acb77ee91482b0701978d4e17`
- Inherited execution-schedule digest: `b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3`
- B2.5 protocol-report digest: `b25protocol_cdb3ec1eb55acd1bf5ba1de39a76deccc525b0dbf6f0d7e74d2ee2b2c20e8ba7`

## Current authorized sequence

The server is not needed while this public implementation is being reviewed. The authorized sequence is:

1. commit the B2.5 protocol, implementation, documentation, and protocol report, then obtain green public CI;
2. start the B2.3-class-compatible Linux server and run only the four-case synthetic repaired-runtime qualification;
3. commit its aggregate-only public report and obtain green CI;
4. author the fresh private holdout, run and re-run the source-only query gate, freeze the runtime, and generate aggregate readiness;
5. commit readiness and obtain green CI;
6. create one private launch authorization, re-admit the runner, and release exactly one complete long run.

At the current checkpoint, step 1 is in progress. No runtime qualification, private B2.5 holdout, treatment output, scoring, result, or tournament execution authorization exists.
