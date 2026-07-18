# Product Bakeoff B3 Offline Control Plane

Date: 2026-07-18

Status: `product_bakeoff_b3_tournament_complete_aggregate_only`

The executable B3 control plane is complete and fault-tested. The exact Linux runtime is publicly qualified in [`product_bakeoff_b3_runtime_qualification.json`](../../artifacts/product_bakeoff_b3_runtime_qualification/product_bakeoff_b3_runtime_qualification.json), and the fresh private 12-repository, 48-task holdout passed its aggregate-only [`product_bakeoff_b3_readiness.json`](../../artifacts/product_bakeoff_b3_readiness/product_bakeoff_b3_readiness.json) gate before the unique formal launch. That run is now complete; the permitted aggregate result is [`product_bakeoff_b3_result.json`](../../artifacts/product_bakeoff_b3_result/product_bakeoff_b3_result.json).

This phase implements the surfaces that were deliberately absent from the earlier runner/scorer integration: exact Linux runtime qualification, fresh holdout admission against all four historical frames, private freeze, aggregate readiness, CI-bound launch authorization, disconnect-safe launch, the first-durable-observation attempt receipt, aggregate success publication, and aggregate failed-closeout publication.

## Runtime qualification

B3 does not require the identity of a historical server. The current Linux runner must independently satisfy the frozen minimum runner class, execute the actual production CLI and strict `bakeoff-query` parser on the public synthetic tokenizer matrix, and retain an unchanged stable profile across that matrix.

The exact current profile and CLI bytes are written only to a private receipt. The public report contains the minimum class, aggregate pass/fail gates, case categories, and zero-provider-call result. Before authoring, freezing, and formal RUN admission, the current profile is collected again and compared exactly on the frozen stable fields while transient available-memory, free-space, and idle-load values are separately rechecked against minimum gates.

B3 no longer inherits the historical 300 GiB scratch floor. Its scratch gate is derived from the actual serial peak: six byte-identical arm snapshots of the largest permitted visible repository, a four-times snapshot/index allowance, 4 GiB of checkpoint/control margin, 4 GiB of filesystem safety margin, and 2 GiB of rounding/measurement margin. This yields a 16 GiB minimum free-scratch gate. All non-storage B2.3 runner gates remain unchanged. Candidate clones are checkpointed separately and are not converted into a speculative fixed scratch reservation.

The 24 GiB cgroup memory-headroom requirement is retained, but B3 measures effective headroom as raw limit-minus-current usage plus only the kernel's `inactive_file` cache, capped at the cgroup limit. This corrects the cgroup-v1 accounting artifact where clean, reclaimable build/source pages were treated as permanently occupied memory. Active file cache, anonymous memory, shared memory, dirty pages, and writeback are not credited.

## Fresh holdout and readiness

The candidate plan must exclude the disjoint B2, B2.1, B2.4, and B2.5 repository frames: 48 historical repository slugs and identity/commit pairs in total. It must also exclude every registered real preflight source and synthetic qualification source. Each of the 12 repository slots requires at least two unique frozen candidates before authoring.

Authoring now writes one durable checkpoint per completed repository slot. A resumed authoring pass validates the slot-local candidate-plan digest, selected candidate index, repository/license binding, exact Git commit, clean tracked worktree, and four authored task drafts before it skips that slot. A prior clone may be reused only at the exact frozen slot/index/repository location and is put through the complete admission and source scan again. If cache integrity fails, the same candidate is cloned afresh before the next candidate can be considered. Therefore interruption, damaged cache, or a late candidate replacement no longer discards unrelated completed work or changes selection order, while eligibility rules, selected commits, final 12-repository frame, and all 48 tasks remain unchanged.

The private holdout binding covers the selected repository lock, 48 tasks, 48 oracle rows, source-only tokenizer compatibility report, candidate plan, four historical locks, exclusion registry, exact runtime qualification, CLI bytes, B3 Williams schedule, complete 360-group/1,440-observation plan, and shared repeatability policy. Freeze output is exclusive and durably written.

The public readiness report exposes only fixed counts, margins, booleans, public protocol/runtime digests, and a self-digest. It requires zero treatment output, no launch release, no scoring or ranking, and no public tournament result. A private launch authorization may be created only after that exact readiness file is committed and its CI succeeds.

## Attempt boundary and disconnect safety

Worker entry, runner admission, and launch release are three pre-boundary states. None consumes the formal attempt.

The frozen B2.1 append functions are wrapped only during B3 engine execution. A normal or terminal observation is first persisted by the historical writer, then its file and containing directory are synchronized, and only then is the private attempt receipt written atomically. This is the first durable treatment observation and the sole attempt boundary.

If the process dies after the observation file is durable but before the receipt is written, reconciliation detects the exact normal/terminal observation directories and reconstructs the receipt. Therefore this crash window cannot be misclassified as a zero-output launch. A receipt without any durable observation is rejected. After the boundary, restart, resume, selective retry, imputation, and recomputation remain forbidden.

The Linux launcher uses `nohup`, a PID file, an exit-code file, a private log, worker-entry and admission handshakes, and a separate launch release. Its status command emits only worker state, launch/boundary booleans, completed-group count, logical-record count, and exit code; it never emits private paths, identities, queries, metrics, or ranks.

## Success and failure publication

After all 1,440 records and every pre-score gate pass, the scorer is imported lazily, uses the shared B3 canonicalizer, writes the complete score privately, and publishes only six final arm aggregates plus the frozen tournament decision. Exact equal quality or resource vectors share competition rank; a unique winner is not forced.

Any post-boundary failure closes without retry. Its public artifact contains only a closed failure class, completed-group count, validated logical-record count, durable treatment-artifact count, the frozen protocol boundary, and booleans confirming that no arm quality, resource, or ranking metric is present. The separate artifact count also closes the rare case where a crash leaves a durable but incomplete observation file. A hard worker or machine termination can be closed later from the durable private observation inventory without rerunning the matrix.

Pre-boundary zero-observation work state is only audited as potentially recoverable; the tooling never deletes it automatically. Replacing the runner requires a new public runtime qualification and readiness cycle.

## Validation and next action

Cross-module self-tests and fault tests cover source closure, runtime public/private schemas, the computed scratch budget, removal of the inherited 300 GiB floor, cgroup-v1 inactive-file parsing and conservative reclaimable-memory admission, verified-cache reuse without recloning, checkpoint resume without repeated authoring, checkpoint source/plan drift rejection, 48-repository historical exclusion, readiness privacy, success/failure publication, hook restoration, release-without-observation, observation-without-receipt reconciliation, receipt-without-observation rejection, and forbidden post-boundary retry. The Linux launcher separately passes its 13-step handshake and reboot/PID-reuse identity test.

The unique formal B3 attempt completed without restart, resume, retry, imputation, or recomputation. All 48 logical tasks, 360 groups, and 1,440 logical records are complete; every pre-score gate passed and provider/network calls remained zero. The frozen tournament decision is `no_internal_finalist`: no arm entered the default track, optional track, or Phase C shortlist, so the product default remains unchanged. This closes B3 at aggregate-result level; any future experiment must be a separately preregistered phase rather than a continuation of this attempt.
