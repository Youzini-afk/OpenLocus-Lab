# BEA-v1-FRK-N Persistent Index Dirty-Update Hardening

Status: complete. Checkpoint: `09c3624`.

Code surface: `crates/openlocus-index/src/persistent.rs`.

## Contract

- Source: FRK-M checkpoint `b8d970d`.
- Scope: close the concrete dirty/status/update path-safety gap found after FRK-M.
- No research artifact, ranking change, candidate generation, retrieval rerun, source scan, pack rerun, provider/network/CI/runtime/default/method/scale/winner claim, RPM, or raw publication.

## Change

FRK-N hardened persistent-index dirty/status/update paths:

- `status_index` validates manifest entry paths before filesystem `exists` or read checks.
- Unsafe indexed paths and symlink escapes now make status unclean/rebuild-required.
- `dirty_index` validates manifest entry paths before filesystem probing.
- Unsafe indexed paths become update-required instead of being read outside the repository.
- Skipped unsafe entries are not probed outside the repository.
- Single-path `update_index(..., path=Some(...))` rejects absolute and parent paths before filesystem probing.

## Regression coverage

FRK-N added or strengthened tests for:

- indexed manifest `../escape.rs` unclean in status/dirty;
- indexed file replaced by symlink to outside root unclean in status/dirty;
- skipped unsafe manifest entry not reading outside root;
- dirty modify/add/delete/skipped-to-indexed update leaving `validate_index` valid and `dirty_index` clean;
- old modified/deleted query terms emitting no stale/invalid hits after update;
- unsafe single-path update rejection before probing.

## Validation

Validated before commit:

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

@oracle review: Go.

## Result

FRK-N closes the current bounded EvidenceCore/kernel hardening line. No further FRK phase is authorized without a specific failing test, defect report, or product workflow pain.
