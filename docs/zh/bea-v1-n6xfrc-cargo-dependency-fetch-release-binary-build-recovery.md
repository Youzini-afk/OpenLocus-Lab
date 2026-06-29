# BEA-v1-N6XFR-C Cargo Dependency Fetch and Release Binary Build Recovery

日期：2026-06-29

BEA-v1-N6XFR-C 是 N6XFR-B 发现 release binary 缺失且需要 cargo dependency fetch 之后的窄范围 build-recovery step。本阶段明确只允许一个 cargo build command，并允许 crates.io/static.crates.io dependency fetch：

```text
cargo build --locked --release -p openlocus-cli
```

它不运行 OpenLocus binary，不运行 `cargo run`，不运行 retrieval，不 clone benchmark repositories，不 rerun P4L/N1/N2/N3，不生成或 materialize candidate pools，不执行 selector/reranker，不做 counterfactual，不授权 P5、BEA-v1-A、runtime/default changes，也不读取 private content。

## 结果

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

该 scoped cargo build 成功，且 release binary bucket `target_release_openlocus` 在 recovery 后可用。Public reporting 故意保持 coarse：只公开 command bucket、exit-code bucket、duration bucket、binary before/after booleans 与 build status。Raw cargo logs 不公开。

## Remaining blocker

N6XFR-C 只是 partial recovery。FD1 private decomposition、P4L private source 与 N-series candidate-pool source inputs 仍不可用。本阶段不读取 private file contents，也不公开 private file paths 或 names。

## 决策

N6XFR-C 不授权 N6X-FR canary 或 full capture。下一阶段为 `none_until_fd1_p4l_private_inputs_are_supplied`。它也不授权 retrieval、full rerun、benchmark repository clone、OpenLocus binary execution、private reads、P5、BEA-v1-A、selector/reranker execution、counterfactuals、runtime/default changes、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery.py`
- Report: `artifacts/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery_report.json`
