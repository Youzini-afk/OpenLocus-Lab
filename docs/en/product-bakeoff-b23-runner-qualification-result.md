# Product Stack Bakeoff — B2.3 Runner Qualification Result

Date: 2026-07-15

Status: `product_bakeoff_b23_runner_qualified_no_private_input_read`

The constrained Linux runner passed the frozen B2.3 public synthetic qualification on the exact source bundle identified below. This checkpoint qualifies the same machine instance for future B2.3 work and authorizes only the next private-holdout authoring phase. It does not authorize tournament execution, publish a hardware identity, or select a product stack.

The validated public aggregate is [`product_bakeoff_b23_runner_qualification.json`](../../artifacts/product_bakeoff_b23_runner_qualification/product_bakeoff_b23_runner_qualification.json). Its SHA-256 is `b22229479ed3744321a4a6b09e454d06dc873f08d366069c738e6109c72a7e95`.

## Frozen result

- profile admission passed;
- post-stress profile revalidation executed and passed;
- the 512 MiB write/fsync/read/hash I/O gate passed;
- 3/3 sustained groups completed;
- 90/90 logical records were normal and accepted;
- timeout, terminal-support, parent-receipt-error, and provider/network-call counts were all zero;
- the six-hour wall-clock cap was met;
- no private input was read.

Exact throughput, cgroup observations, hardware identity, mount source, paths, and runner name remain only in the private receipt.

## Audit chain

- B2.3 spec digest: `b23spec_b9281d2e323f8103`
- B2.3 source bundle digest: `b23src_c674402a50183c6d3bb6eec0d855900dbfe7822929eb9656965077f9336057eb`
- qualification digest: `b23qual_0ba839c5e02c96a7c8c879532ad354f19a6405cd6dd3f9885baa2ea3c1a499a1`
- final protected CI run: [29415970142](https://github.com/Youzini-afk/OpenLocus-Lab/actions/runs/29415970142)

An earlier run passed the qualification and aggregate-validation gates but failed only while uploading through a provider private CA. The workflow was repaired to trust the Linux system CA bundle without disabling TLS verification, the source bundle was refrozen, and the complete qualification was rerun from scratch. The final run passed every job step, uploaded the validated aggregate, and automatically removed the one-job runner registration.

## Scope of authorization

`future_holdout_authoring_authorized=true` permits the next phase to author and freeze the new 12-repository, 48-task private holdout under the preregistered exclusion rules. `future_tournament_execution_authorized=false` remains binding. No treatment arm may run until that holdout is independently audited and a later checkpoint explicitly authorizes the one-attempt tournament.
