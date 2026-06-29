# BEA-v1-N6XFR-C Cargo Dependency Fetch and Release Binary Build Recovery

Date: 2026-06-29

BEA-v1-N6XFR-C is the narrowly scoped build-recovery step after N6XFR-B found that a release binary was missing and cargo dependency fetch would be required. This phase is explicitly limited to one cargo build command with crates.io/static.crates.io dependency fetch as needed:

```text
cargo build --locked --release -p openlocus-cli
```

It does not run the OpenLocus binary, `cargo run`, retrieval, benchmark repository clones, P4L/N1/N2/N3 reruns, candidate-pool generation/materialization, selector/reranker execution, counterfactuals, P5, BEA-v1-A, runtime/default changes, or private content reads.

## Result

```text
status: partial_n6xfrc_binary_built_private_inputs_missing
self-test: 15 / 15
forbidden scan: pass
binary exists after build: true
binary available after recovery: true
cargo exit code bucket: zero
raw cargo log public: false
private FD1/P4L inputs available: false
```

## Build summary

The scoped cargo build succeeded and the release binary bucket `target_release_openlocus` is available after recovery. Public reporting is intentionally coarse: command bucket, exit-code bucket, duration bucket, binary-before/after booleans, and build status only. Raw cargo logs are not published.

## Remaining blocker

N6XFR-C is only a partial recovery. FD1 private decomposition, P4L private source, and N-series candidate-pool source inputs remain unavailable. The phase does not read private file contents and does not serialize private file paths or names.

## Decision

N6XFR-C does not authorize N6X-FR canary or full capture. The next allowed phase is `none_until_fd1_p4l_private_inputs_are_supplied`. It also does not authorize retrieval, full rerun, benchmark repository clone, OpenLocus binary execution, private reads, P5, BEA-v1-A, selector/reranker execution, counterfactuals, runtime/default changes, method-winner claims, or downstream-value claims.

## Artifact

- Script: `eval/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery.py`
- Report: `artifacts/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery_report.json`
