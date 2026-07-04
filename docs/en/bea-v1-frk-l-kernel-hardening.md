# BEA-v1-FRK-L Kernel Hardening

Status: complete. Checkpoint: `dbbfd25`.

Code surface: `crates/openlocus-cli/src/lib.rs`.

## Contract

- Source: FRK-K checkpoint `ddf2384`, which authorized only bounded kernel hardening after real `openlocus read` + `openlocus citations validate` materialization stress.
- This phase is real CLI/kernel hardening, not a new retrieval/ranking experiment.
- No provider, network, CI-runtime, default-policy, method-winner, scale, candidate-generation, retrieval-rerun, source-scan, pack-rerun, RPM, or raw-publication claim is authorized.

## Change

FRK-L hardened repository root discovery:

- `discover_repo_root_from(start: &Path)` now accepts a real `.openlocus/` directory as a repo marker.
- Symlinked `.openlocus` markers fail closed.
- File `.openlocus` markers fail closed.
- `.git` marker behavior is preserved.

## Regression coverage

FRK-L added CLI/EvidenceCore regression tests for:

- real `.openlocus` accepted;
- symlink `.openlocus` rejected;
- file `.openlocus` rejected;
- `.git` accepted;
- current citation valid;
- stale edit invalid;
- deleted file invalid;
- moved old path invalid and moved new citation valid;
- line insertion invalidates old evidence and rematerialized range validates;
- same-content near duplicate does not rescue a stale original path.

## Validation

Validated before commit:

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

@oracle review: Go.

## Result

FRK-L closed the first concrete kernel hardening item exposed by FRK-K. It authorized only bounded follow-up regression expansion where a concrete kernel/currentness gap existed.
