# BEA-v1-FRK-M EvidenceCore Kernel Regression Expansion

Status: complete. Checkpoint: `b8d970d`.

Code surface: `crates/openlocus-index/src/persistent.rs`.

## Contract

- Source: FRK-L checkpoint `dbbfd25`.
- Scope: bounded persistent-index EvidenceCore/currentness regression expansion.
- No research artifact, ranking change, candidate generation, provider/network/CI/runtime/default/method/scale/winner claim, pack rerun, source scan, or raw publication.

## Regression coverage

FRK-M added persistent-index tests for:

- current indexed hits producing `Freshness::VerifiedCurrent` through both `search_persistent_bm25` and `PersistentBm25Index::search`;
- current `content_sha`, valid range, and valid excerpt on emitted Evidence;
- stale edit after index build skipped and counted;
- deleted file after index build skipped and counted, plus `validate_index` deletion reporting;
- moved old path rejected and rebuilt new path emitted as current Evidence;
- line insertion invalidating old indexed hits until rebuild;
- same-content duplicate not rescuing a stale original path;
- unsafe `FileRecord` path skipped at build and not searchable;
- unsafe indexed manifest path reported by `validate_index`;
- symlink escape after build skipped by search and reported by `validate_index`.

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

FRK-M expanded the real persistent-index currentness/path-safety regression surface. It did not reopen stopped ranking, RankPack, LDI, HAAE scheduler, RPM, provider, or runtime/default routes.
