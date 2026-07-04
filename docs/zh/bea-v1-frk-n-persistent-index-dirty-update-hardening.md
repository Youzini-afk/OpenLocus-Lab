# BEA-v1-FRK-N Persistent Index Dirty-Update Hardening

状态：已完成。Checkpoint：`09c3624`。

代码面：`crates/openlocus-index/src/persistent.rs`。

## Contract

- 来源：FRK-M checkpoint `b8d970d`。
- 范围：关闭 FRK-M 后发现的 dirty/status/update path-safety 具体 gap。
- 不创建 research artifact，不修改 ranking，不授权 candidate generation、retrieval rerun、source scan、pack rerun、provider/network/CI/runtime/default/method/scale/winner claim、RPM 或 raw publication。

## Change

FRK-N 加固了 persistent-index dirty/status/update paths：

- `status_index` 在 filesystem `exists` 或 read 前先验证 manifest entry path。
- unsafe indexed path 和 symlink escape 会让 status 变为 unclean/rebuild-required。
- `dirty_index` 在 filesystem probing 前先验证 manifest entry path。
- unsafe indexed path 变为 update-required，而不是读取 repository 外部。
- skipped unsafe entry 不会被 probe 到 repository 外部。
- single-path `update_index(..., path=Some(...))` 在 filesystem probing 前拒绝 absolute 和 parent path。

## Regression coverage

FRK-N 新增或加强 tests，覆盖：

- indexed manifest `../escape.rs` 在 status/dirty 中 unclean；
- indexed file 被替换为指向 root 外部的 symlink 后 status/dirty unclean；
- skipped unsafe manifest entry 不读取 root 外部；
- dirty modify/add/delete/skipped-to-indexed update 后 `validate_index` valid 且 `dirty_index` clean；
- update 后 old modified/deleted query terms 不 emitted stale/invalid hits；
- unsafe single-path update 在 probing 前被拒绝。

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

FRK-N 关闭了当前 bounded EvidenceCore/kernel hardening 线。没有具体 failing test、defect report 或 product workflow pain 时，不再授权新的 FRK phase。
