# Product Bakeoff B4 Offline Control-Plane Integration

Date: 2026-07-18

Status: `product_bakeoff_b4_offline_control_plane_complete_server_required_next_for_exact_linux_qualification`

The B4 raw repository adapter and offline control plane are now implemented and fault-tested without reading a private holdout or producing treatment output. The aggregate machine-readable checkpoint is [`product_bakeoff_b4_control_integration.json`](../../artifacts/product_bakeoff_b4_control_integration/product_bakeoff_b4_control_integration.json).

## Raw execution adapter

Each of the twelve panels runs in a fresh child process over the established B2.1 execution gates and B2.4 timeout envelope. A narrowly scoped override changes the historical surface only for that child: three arms, one repository/arm lifecycle, one repetition, the frozen panel schedule, 180 raw operation groups, and 36 index builds. Every historical function, timeout, adapter registry, schedule function, and constant is restored on both success and exception.

The RUN phase starts before any author, oracle, or scorer module is imported. Historical B3 validation dependencies that previously imported scorer/oracle code transitively are now loaded lazily outside the raw child import surface. Only after a panel's raw matrix and pre-score gates have completed does the child load the frozen oracle and historical task scorer, project 144 identity-free task outcomes, and durably write one exclusive private panel report. Twelve valid reports assemble into exactly 1,728 task outcomes, 2,160 logical records, and 432 index builds for the already frozen B4 analysis engine.

## Private corpus construction and freeze

The authoring controller consumes one shared candidate catalog across twelve repository slots and twelve mutually disjoint panels. It excludes all 60 repositories in the B2, B2.1, B2.4, B2.5, and B3 historical frames plus the explicit exclusion registry. Candidate order is deterministic per slot. A failed candidate advances only that slot; completed repository checkpoints and completed panels are preserved.

On resume, the controller replays every completed panel's candidate plan and cursor, revalidates its selected Git checkout and task/oracle manifests, rebuilds the source-only query-compatibility gate, and reconstructs the exact panel binding. Cache roots are normalized once against the entire private root. Unselected clone directories are deleted using the frozen `clone_root` field, while selected source directories remain intact. Freeze is permitted only after all twelve panels contain 144 distinct repository identities, 576 tasks, valid query/oracle bindings, the exact qualified runtime and CLI bytes, and zero treatment output.

Only aggregate readiness is public. A separate private readiness-binding receipt binds the exact public readiness bytes to the exact global private freeze, and launch authorization must validate both; this closes freeze drift without publishing a private digest. Repository, candidate, task, query, oracle, source-location, private-path, endpoint, and private digest material remains private.

## Runtime and storage policy

The next server step is exact Linux qualification using the production CLI and public synthetic runtime cases. The non-storage runner gates remain the established dedicated Linux class, including at least eight effective CPU cores, a finite memory limit of at least 32 GiB, at least 24 GiB effective available memory at admission, zero active swap, local non-rotational scratch outside the checkout, and the frozen Rust/Python toolchain constraints. No GPU is required.

The former arbitrary disk reservation is not inherited. B4's free-scratch gate is calculated from the largest allowed visible repository, three concurrent arm snapshots within one serial lifecycle, index/render expansion, control receipts, and filesystem margin. The resulting admission threshold is 5,100,273,664 bytes (about 4.75 GiB). Frozen source bytes are already reflected in current free space; panels and repository lifecycles execute serially and disposable working trees are deleted after use.

## Launch, interruption, and attempt boundary

Runtime qualification must first be committed and pass public CI. Private authoring and freeze then produce an aggregate readiness file plus its private freeze-binding receipt. The public readiness must also be committed and pass CI before a private launch authorization can be created.

The Linux launcher uses a detached process group, durable PID identity, private log and exit code, worker-entry and runner-admission handshakes, and a separate launch release. The frozen CLI path is explicitly bound to the historical runner's `OPENLOCUS_CLI` lookup. If admission fails before release with zero observations, a narrow reset removes only the PID/admission/envelope state after the worker is confirmed stopped. That reset is forbidden if a release, durable observation, panel outcome, boundary receipt, terminal state, or public closeout exists.

Launch release alone does not consume the attempt. The first durably persisted normal or terminal raw observation is synchronized and creates the private attempt-boundary receipt; a crash between the observation and receipt is reconciled from the durable inventory. After that boundary, restart, resume, selective retry, imputation, and recomputation remain forbidden. Failure progress is counted from the exact durable observation inventory, including an incomplete current panel, rather than estimated from completed panels.

## Validation and current boundary

Local self-tests and fault tests cover all twelve schedules, real nested runtime overrides, restoration after exceptions, exclusive durable panel output, strict duplicate/non-finite JSON rejection, identity-free projection, full aggregate assembly, candidate depletion and historical overlap, deterministic resume, selected/unselected clone cleanup, calculated resource admission, readiness privacy, launch-release separation, observation/receipt reconciliation, exact aggregate progress, and the zero-observation pre-release reset. The Linux script separately exercises the detached handshake and PID-identity path. CI repeats the control tests on Linux and Windows, checks the raw import fence, parent protocol/engine drift, public privacy, bilingual documentation, and shell launch behavior.

No Linux runtime has yet been qualified for this checkpoint; no private B4 holdout has been authored or frozen; no launch authorization, release, treatment observation, score, rank, or empirical B4 result exists. The compute server is needed only after this control-plane checkpoint is committed and its CI is green.
