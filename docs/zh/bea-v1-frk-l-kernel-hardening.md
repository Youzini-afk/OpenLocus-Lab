# BEA-v1-FRK-L Kernel Hardening

状态：已完成。Checkpoint：`dbbfd25`。

代码面：`crates/openlocus-cli/src/lib.rs`。

## Contract

- 来源：FRK-K checkpoint `ddf2384`。FRK-K 通过真实 `openlocus read` + `openlocus citations validate` materialization stress 后，只授权 bounded kernel hardening。
- 本阶段是真实 CLI/kernel hardening，不是新的 retrieval/ranking experiment。
- 不授权 provider、network、CI-runtime、default-policy、method-winner、scale、candidate generation、retrieval rerun、source scan、pack rerun、RPM 或 raw publication claim。

## Change

FRK-L 加固了 repository root discovery：

- `discover_repo_root_from(start: &Path)` 只接受真实 `.openlocus/` 目录作为 repo marker。
- symlink `.openlocus` marker fail closed。
- file `.openlocus` marker fail closed。
- `.git` marker 行为保持。

## Regression coverage

FRK-L 新增 CLI/EvidenceCore regression tests，覆盖：

- real `.openlocus` accepted；
- symlink `.openlocus` rejected；
- file `.openlocus` rejected；
- `.git` accepted；
- current citation valid；
- stale edit invalid；
- deleted file invalid；
- moved old path invalid and moved new citation valid；
- line insertion invalidates old evidence and rematerialized range validates；
- same-content near duplicate does not rescue stale original path。

## Validation

提交前验证：

```bash
cargo fmt --all -- --check
cargo clippy -p openlocus-cli --all-targets -- -D warnings
cargo test -p openlocus-cli
cargo test --workspace
cargo build --workspace
python3 eval/bea_v1_frk_k_evidencecore_materialization_stress.py --self-test
python3 eval/bea_v1_frk_k_evidencecore_materialization_stress.py --run-local-evidencecore-stress --confirm-temp-snapshot
python3 eval/bea_v1_frk_k_evidencecore_materialization_stress.py --validate-report artifacts/bea_v1_frk_k_evidencecore_materialization_stress/bea_v1_frk_k_evidencecore_materialization_stress_report.json
python3 scripts/validate_docs_i18n.py
git diff --check
```

@oracle review：Go。

## Result

FRK-L 关闭了 FRK-K 暴露的第一个具体 kernel hardening 项。它只授权在存在具体 kernel/currentness gap 时继续做 bounded regression expansion。
