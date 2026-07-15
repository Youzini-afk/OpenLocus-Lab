# Product Stack Bakeoff — B2.2 Self-Hosted Execution Design

Date: 2026-07-15

Status: `product_bakeoff_b22_runner_protocol_ready_no_runner_no_holdout_no_result`

B2.2 is a new confirmatory experiment design after B2.1 failed closed twice at the same timeout boundary on an underpowered local machine. This phase does not author a holdout, does not read any B2.2 private input, and does not execute any treatment arm. It implements a strong-runner qualification and a manual self-hosted GitHub Actions path so another large matrix cannot start on an unsuitable machine.

The executable surface is:

- [`product_bakeoff_b22_protocol.py`](../../eval/product_bakeoff_b22_protocol.py)
- [`product_bakeoff_b22_runner_qualification.py`](../../eval/product_bakeoff_b22_runner_qualification.py)
- [`product-bakeoff-b22-runner.yml`](../../.github/workflows/product-bakeoff-b22-runner.yml)
- [`product_bakeoff_b22_protocol_report.json`](../../artifacts/product_bakeoff_b22_protocol/product_bakeoff_b22_protocol_report.json)

## Why the full tournament is not local

Small synthetic tests remain local. Public compilation, self-tests, fault injection, report drift, and documentation checks run on GitHub-hosted CI. The sustained qualification and any future private tournament run on one dedicated strong self-hosted runner.

The private holdout cannot be committed to this public repository or copied into a normal hosted runner. That privacy constraint does not imply using the current workstation. The correct boundary is an ephemeral self-hosted runner with private inputs preprovisioned outside the checkout and only a validated aggregate artifact allowed to leave the machine.

## Experimental design boundary

The independent unit remains one logical task (`n=48`). Repository remains a nested cluster. Cache state and four repetitions remain technical repeated measurements. Runner machine is a fixed nuisance block: all six treatments, all groups, and the final analysis must use one machine and one frozen runtime. Group-, repository-, or arm-level sharding across multiple runners is forbidden because machine performance would become confounded with treatment, cache, or run order.

The randomized complete task blocks, repository split-plot lifecycle, own-parent two-step policy, quality thresholds, resource ceilings, tie policy, and zero/one/multiple-finalist outcomes remain inherited. There are no interim quality looks.

## Strong-runner class

The runner must satisfy all of these gates before stress execution:

- Windows x64, at least 16 logical CPUs;
- at least 64 GiB physical memory and 40 GiB available at job start;
- at least 200 GiB free on a fixed local scratch volume outside the checkout;
- Git, Python, Rust, Cargo, and the checked-out release OpenLocus binary available;
- a dedicated one-job runner carrying the custom label `openlocus-b22-private`;
- no private path, exact hardware profile, runner name, or machine identifier in public output.

Sequential I/O qualification writes and rereads one 512 MiB file with `fsync`, verifies its hash, and requires at least 150 MiB/s for both write and read. Exact observed throughput remains private.

## Sustained qualification workload

Hardware labels alone are not trusted. After the profile and I/O gates pass, the qualifier deterministically generates a public synthetic TypeScript corpus with 10,000 files and exactly 72 MiB of visible source. It then runs three consecutive real split-plot groups using all six adapters, the frozen arm rotation, the real copy/index/query/support lifecycle, and the inherited 30-second phase timeout.

The required outcome is 3/3 groups, 90/90 logical records, all normal records accepted, zero timeout, zero parent-receipt error, zero terminal support, zero provider/network calls, and total wall time no greater than 45 minutes. This workload runs before any private holdout input is read. A failed runner may be requalified because qualification has no treatment output.

## Public-repository self-hosted security

The repository is public, so the private job is never triggered by `push` or `pull_request`. It requires manual `workflow_dispatch`, the `b22-private-execution` protected environment, the labels `self-hosted`, `windows`, `x64`, and `openlocus-b22-private`, and an ephemeral runner that processes one job and is then destroyed or wiped. GitHub recommends ephemeral self-hosted runners for autoscaling and warns that public-repository workflows can expose persistent self-hosted machines to untrusted code; the workflow therefore keeps the runner offline except for an approved manual job and pins external actions to full commit SHAs. See GitHub's [self-hosted runner reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners), [workflow routing guide](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/use-in-a-workflow), and [runner access warning](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access).

The job uses read-only repository permissions, does not persist checkout credentials, does not use an actions cache, and uploads one exact validated aggregate JSON file. Runner diagnostic logs must be forwarded to restricted external storage before ephemeral operation, as recommended by GitHub.

## Operational practice

1. Create the protected environment `b22-private-execution` and require a reviewer.
2. Provision a dedicated ephemeral Windows x64 VM meeting the frozen resource class.
3. Put scratch storage on a fixed local SSD and set the runner-service environment variable `OPENLOCUS_B22_SCRATCH_ROOT`; do not put private data in the checkout.
4. Register the runner with the custom label `openlocus-b22-private` and ephemeral mode.
5. Forward runner diagnostic logs to restricted storage.
6. Dispatch `product-bakeoff-b22-runner` with mode `runner_qualification` from `main`.
7. Validate and commit only the uploaded aggregate qualification result.
8. Author a fresh B2.2 holdout only after that result is green.

At this checkpoint the repository has no registered self-hosted runner, so the actual strong-runner qualification has not executed. The local profile-only practice rejected the current workstation on logical CPU, total memory, available memory, and free-scratch gates; it correctly skipped the 512 MiB I/O test and the 72 MiB stress corpus and reported `private_input_read=false`. A permitted small local lifecycle practice then completed 1/1 group and 30/30 logical records over the real six adapters with zero timeout and zero provider/network calls.

## Retry and future execution policy

The synthetic runner qualification may be repeated before private input is read. A future B2.2 tournament gets exactly one attempt after qualification and freeze. Once any future arm output exists, complete restart, selective retry, missing-cell imputation, timeout change, task/oracle edit, and cross-runner migration are all forbidden. An infrastructure failure closes B2.2 without a result.

The future holdout must contain 12 new repository identities and 48 new task/oracle rows, excluding all B2, B2.1, real-preflight, and qualification sources. No B2 or B2.1 empirical cell may be reused.

## Frozen identifiers

- B2.2 spec digest: `b22spec_adf15e2598e9f7c4`
- B2.2 source bundle digest: `b22src_05d40bb6c20414aa8ec0972d087e53750d0af635f0a57857ceddd864b4b1ea47`
- B2.2 protocol report digest: `b22protocol_a84b309cf327a81325eb38451682beb8077cd93e2e9a49b3befc65fc4219e425`

## Next authorized work

Provision and qualify the strong ephemeral runner. Do not create or read a B2.2 private holdout and do not execute a treatment arm until the aggregate runner qualification is committed and remotely green.
