# Product Stack Bakeoff — B2.3 Constrained Linux Long-Run Design

Date: 2026-07-15

Status: `product_bakeoff_b23_linux_longrun_protocol_ready_no_runner_qualification_no_holdout_no_result`

B2.3 preserves B2.2 as an unexecuted strong-runner design checkpoint and introduces a new execution-environment contract for a dedicated, quota-limited Linux container. This checkpoint does not author or read a private holdout, execute a treatment arm, score a tournament, or select a default.

The executable public surface is:

- [`product_bakeoff_b23_protocol.py`](../../eval/product_bakeoff_b23_protocol.py)
- [`product_bakeoff_b23_runner_qualification.py`](../../eval/product_bakeoff_b23_runner_qualification.py)
- [`product_bakeoff_b23_linux_bootstrap.sh`](../../scripts/product_bakeoff_b23_linux_bootstrap.sh)
- [`product-bakeoff-b23-linux.yml`](../../.github/workflows/product-bakeoff-b23-linux.yml)
- [`product_bakeoff_b23_protocol_report.json`](../../artifacts/product_bakeoff_b23_protocol/product_bakeoff_b23_protocol_report.json)

## Why B2.3 is a new checkpoint

B2.2 froze a Windows x64 strong-runner class before any runner was registered or qualified. Rewriting those thresholds in place would erase the audit trail. B2.3 therefore locks the B2.2 report's repository bytes after cross-platform line-ending normalization and locks its semantic digests, then changes only the execution-environment design. No B2.2 private input or treatment output exists.

Lower speed is not itself a treatment confounder when every arm runs on the same qualified machine and the frozen complete arm rotation is preserved inside each logical-task block. Provider-host contention remains an uncontrolled nuisance, so performance claims are restricted to this one qualified machine and may not be generalized across machines.

## Experimental-design boundary

The independent unit remains one logical task (`n=48`). Repository remains a nested cluster. Cache state and four repetitions remain technical repeated measurements. Every task block contains the complete six-arm rotation, preserving the inherited randomized complete-block and split-plot schedule. Repository-, group-, or arm-level sharding across machines is forbidden.

There are no interim quality looks, arm eliminations, timeout edits, task edits, or outcome-conditioned pauses. Only one final analysis is allowed after a complete future matrix.

## Constrained Linux runner class

Qualification reads effective container limits rather than trusting host-wide `/proc` totals. Both cgroup v1 and v2 are supported. Before workload execution the container must have:

- Linux x64;
- a finite effective CPU quota of at least 8 CPUs;
- a finite cgroup memory limit of at least 32 GiB and at least 24 GiB available inside that limit;
- no active swap;
- at least 300 GiB free on non-rotational local block storage outside the checkout;
- an idle cgroup CPU rate no greater than 250 millicores during the admission sample;
- a soft open-file limit of at least 65,535;
- Python 3.10 or newer, Git, Rust 1.95.0, Cargo 1.95.0, and the release OpenLocus binary;
- no concurrent user workload.

Exact cgroup files, hardware profile, mount source, paths, runner name, and machine identity stay in the private receipt.

## I/O and sustained qualification

The I/O gate writes 512 MiB, calls `fsync`, reads the file back, and verifies its hash. Sequential write and read throughput must each reach at least 150 MiB/s. Exact observations remain private.

After the profile and I/O gates pass, the qualifier creates a deterministic public synthetic TypeScript repository with 10,000 files and exactly 72 MiB of visible source. It runs three consecutive real split-plot groups across all six adapters, using the inherited copy/index/query/support lifecycle and arm rotation. Each lifecycle phase has the predeclared 600-second timeout and the whole stress gate has a six-hour cap.

Passing requires 3/3 groups, 90/90 logical records, all normal records accepted, zero timeout, zero terminal support, zero parent-receipt error, and zero provider/network calls.

After the stress gate, the qualifier samples the runner profile again. CPU and memory limits, mount identity, tool versions, open-file limits, and the release OpenLocus binary digest must remain stable, and all capacity gates must still pass. A failed recheck or any stable-field drift fails closed. The private receipt and public aggregate are written as new atomic files inside an attempt-specific qualification root; an existing output is never overwritten.

## Qualification versus the future tournament

Public contract checks run on GitHub-hosted Linux. The sustained qualification is a manually approved job routed to one ephemeral GitHub runner registration on the constrained Linux machine. After that single job, the registration is removed and the machine stays offline from GitHub.

The future private tournament will not run as a GitHub Actions job. It will be one standalone process kept alive across SSH disconnects under `screen` or `nohup`, because a long confirmatory run must not depend on an expiring workflow token. That future launcher and holdout remain unauthorized until runner qualification is committed and remotely green.

Once any future arm output exists, a process or machine restart closes B2.3 without a result. Completed cells may not be recomputed; complete restart, selective retry, missing-cell imputation, cross-runner migration, and timeout modification are forbidden.

## Bootstrap and privacy

The bootstrap installs the pinned Rust 1.95 toolchain under a caller-supplied private data-volume root. Rustup 1.29.0 is downloaded from the official archive and checked against its published SHA-256 file. The script does not register a runner, clone a private holdout, or start qualification.

The repository is public. Pull requests and pushes cannot start the private qualification job. The job has read-only repository permission, does not retain checkout credentials, uses no Actions cache, pins external actions to full commit SHAs, and uploads only a strictly validated aggregate JSON. GitHub recommends ephemeral self-hosted runners and external retention of runner diagnostics; see the [self-hosted runner reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners).

## Local validation boundary

Only compilation, protocol self-tests, fault injection, cgroup parser fixtures, public-report validation, bootstrap syntax, and a previously bounded one-group lifecycle micro-test may run on the local workstation. The 512 MiB qualification I/O gate, 72 MiB three-group stress gate, and future private tournament belong on the rented Linux runner.

## Frozen identifiers

- B2.3 spec digest: `b23spec_b9281d2e323f8103`
- B2.3 source bundle digest: `b23src_86530c25e22fc30a61a311bf1abe4f93a3406d872806201460a6a0f77db174fc`
- B2.3 protocol report digest: `b23protocol_e4b80a244846a70d5bdb7a9a5cd37e42987b3c8523ac9ffd7172130d149bfd69`

## Next authorized work

Bootstrap the constrained Linux container, configure a protected one-job qualification runner registration, and execute only the public synthetic qualification. Do not create or read a B2.3 private holdout and do not execute a treatment arm until the public qualification aggregate is committed and remotely green.
