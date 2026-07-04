# BEA-v1-FRK-M EvidenceCore Kernel Regression Expansion

状态：已完成。Checkpoint：`b8d970d`。

代码面：`crates/openlocus-index/src/persistent.rs`。

## Contract

- 来源：FRK-L checkpoint `dbbfd25`。
- 范围：bounded persistent-index EvidenceCore/currentness regression expansion。
- 不创建 research artifact，不修改 ranking，不授权 candidate generation、provider/network/CI/runtime/default/method/scale/winner claim、pack rerun、source scan 或 raw publication。

## Regression coverage

FRK-M 新增 persistent-index tests，覆盖：

- current indexed hits 通过 `search_persistent_bm25` 与 `PersistentBm25Index::search` 都产生 `Freshness::VerifiedCurrent`；
- emitted Evidence 带当前 `content_sha`、valid range、valid excerpt；
- index build 后 stale edit 被跳过并计数；
- index build 后 deleted file 被跳过并计数，且 `validate_index` 报告 deletion；
- moved old path rejected，rebuild 后 new path emitted as current Evidence；
- line insertion 使 old indexed hit 在 rebuild 前失效；
- same-content duplicate 不会 rescue stale original path；
- unsafe `FileRecord` path 在 build 时跳过且不可搜索；
- unsafe indexed manifest path 被 `validate_index` 报告；
- build 后 symlink escape 被 search 跳过并由 `validate_index` 报告。

## Validation

提交前验证：

```bash
cargo fmt --all -- --check
cargo clippy -p openlocus-index --all-targets -- -D warnings
cargo test -p openlocus-index
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

FRK-M 扩展了真实 persistent-index currentness/path-safety regression surface。它没有重新打开已经停止的 ranking、RankPack、LDI、HAAE scheduler、RPM、provider 或 runtime/default 路线。
