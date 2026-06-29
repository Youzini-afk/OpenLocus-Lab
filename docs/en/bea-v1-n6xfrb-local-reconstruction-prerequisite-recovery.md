# BEA-v1-N6XFR-B Local Reconstruction Prerequisite Recovery

Date: 2026-06-29

BEA-v1-N6XFR-B is a practical local prerequisite recovery smoke after N6X-FR stopped with `no_go_n6xfr_local_prerequisites_unavailable`. It checks whether the local workspace can safely recover the OpenLocus binary and private reconstruction inputs needed for a future N6X-FR canary. It is not a schema-only audit, but it is still fail-closed: it does not run cargo build, network access, retrieval, repository clones, the OpenLocus binary, P4L/N1/N2/N3 reruns, selector/reranker execution, counterfactuals, or private content reads.

## Result

```text
status: no_go_n6xfrb_build_requires_unapproved_network
self-test: 15 / 15
forbidden scan: pass
workspace / Cargo metadata present: true
build command bucket: cargo_build_locked_release_openlocus_cli
cargo registry cache available: false
crates.io dependency fetch required: true
build attempted: false
private FD1/P4L inputs available: false
N6X-FR canary authorized: false
```

## Build prerequisite finding

The Rust workspace, package metadata, lockfile, and binary declaration are present. The correct future build command is represented as the bucket `cargo_build_locked_release_openlocus_cli`, with output bucket `target_release_openlocus`. However, the local cargo registry cache is unavailable, so a first build would require dependency fetch from crates.io/static.crates.io. Because that network access is not preapproved for this checkpoint, N6XFR-B does not run cargo build and closes as No-Go.

## Private input finding

N6XFR-B does not read private file contents and does not serialize private paths or names. It records the required private reconstruction inputs as unavailable: FD1 private decomposition, P4L private source, and N-series candidate-pool source are all false.

## Decision

N6XFR-B does not authorize N6X-FR canary or full capture. The next allowed phase is `none_until_release_binary_or_preapproved_cargo_cache_and_fd1_p4l_private_inputs_exist`. It also does not authorize cargo build, network, retrieval, git clone, OpenLocus binary execution, private reads, P4L/N1/N2/N3 reruns, selector/reranker execution, P5, BEA-v1-A, counterfactuals, runtime/default changes, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery.py`
- Report: `artifacts/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery_report.json`
