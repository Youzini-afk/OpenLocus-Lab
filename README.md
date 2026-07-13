# OpenLocus

OpenLocus is a research and engineering repository for source-backed code context, evidence validation, and bounded evaluation workflows. The core project includes Rust crates and a CLI for repository scanning, source-backed reads, search/retrieval plumbing, citation validation, and local context helpers. The lab material records experiments around evidence quality, evaluator behavior, and route decisions.

The public entrypoint is intentionally short. Detailed dated checkpoints live in the research logs, not in this README.

## Current status

Status date: 2026-07-07.

The current OpenLocus v2 trace-driven HAAE policy line is closed under current evidence. HAAE-A2 offline action replay used existing ignored private TraceV2 rows after explicit private-input confirmation, replayed logged episodes only, and found no reason to continue the current trace-driven policy line. The authorized next route for that line is `none_for_current_v2_trace_driven_policy_line`.

Reopen condition: new product-workflow pain, new trace evidence, or an explicit route decision. Without one of those triggers, HAAE-A3 heldout design, RPM-D2/training, provider/model/network work, runtime/default changes, new retrieval/candidate expansion/source scans, raw/private publication, and closed-route continuations remain unauthorized as continuation or evidence work for the closed trace-driven policy line.

Recent engineering work is evaluator and validation hardening: the self-test quality guard now has static and runtime checks for the current evaluator chain; the CI report validator has a synthetic self-test mode; the public artifact privacy audit exists as a manual local helper. These are quality gates and hygiene checks only. They are not retrieval-lift evidence, method-winner evidence, provider/network readiness, runtime/default promotion, or route reopening.

## Public/private artifact boundary

Public artifacts must be aggregate or sanitized only. Do not commit or publish private traces, prompts, responses, snippets, gold labels, provider payloads, secrets, API keys, unsanitized private rows, or source-linkable private data.

The manual public artifact privacy audit scans committed public files from `git ls-files` in bounded public locations. It does not scan ignored runs, private trace roots, untracked files, or historical git contents. Treat a passing audit as public-surface hygiene evidence only.

EvidenceCore remains the hard contract: a candidate is not fact; counted evidence must rematerialize current source and pass path, range, and content validation.

## Quick start

Build or inspect the CLI:

```bash
cargo run -p openlocus-cli -- --help
```

Representative local CLI commands:

```bash
cargo run -p openlocus-cli -- read README.md:1-40 --json
cargo run -p openlocus-cli -- scan --json
cargo run -p openlocus-cli -- search regex "EvidenceCore" --json
cargo run -p openlocus-cli -- search bm25 "candidate evidence" --json
cargo run -p openlocus-cli -- search symbol EvidenceCore --json
cargo run -p openlocus-cli -- retrieve "EvidenceCore materialization" --channels regex,bm25,symbol --json
cargo run -p openlocus-cli -- citations validate <evidence.json> --json
cargo run -p openlocus-cli -- context-lite --write-files --json
cargo run -p openlocus-cli -- index build --chunk-strategy line --json
cargo run -p openlocus-cli -- index validate --json
```

### Separated persistent index (source root vs state root)

Persistent BM25 supports a separated `--source-root` (where files are scanned, policy is loaded, and current content is re-read) and `--state-root` (where persistent index and telemetry artifacts are written). Persistent INDEX artifacts live only under `state_root/.openlocus/index`; best-effort persistent CLI telemetry traces, when safely writable, live only under `state_root/.openlocus/traces` and never fall back to source; trace failure warns/skips after the core command result. `--state-root` requires `--source-root` and is rejected alone; supported legacy colocated mode remains behavior-compatible, but its trace writes are now checked too (colocated commands are not literally unchanged). Exact guarantee: under a quiescent filesystem tree, pre-existing symlink / Windows reparse point / special-file / wrong-kind descendants and unsafe source-vs-artifact overlap fail closed, and a full typed preflight happens before mutating any EXISTING index artifact; establishing a wholly absent `state_root` trust anchor may create its missing real-directory components before that typed preflight. Exact non-guarantees: no concurrent path-swap/TOCTOU resistance, hard-link or bind-mount defense, hostile/network filesystem defense, or OS sandbox claim. This is B0 engineering readiness only, not S0-S5 tournament/product/fairness evidence.

```bash
cargo run -p openlocus-cli -- index build --source-root ./src --state-root ./state --json
cargo run -p openlocus-cli -- index purge --source-root ./src --state-root ./state --json
```

Provider, derived, dense, and commands marked or gated as experimental are research scaffolds unless a later route explicitly says otherwise.

## Local validation commands

Focused evaluator and privacy checks:

```bash
python scripts/validate_selftest_quality.py --self-test
python scripts/validate_selftest_quality.py
python scripts/validate_selftest_quality.py --runtime-check
python eval/ci_validate_report.py --self-test
python eval/product_bakeoff_conformance.py --self-test
python eval/product_bakeoff_conformance.py --check-drift artifacts/product_bakeoff_a/product_bakeoff_a_report.json
python scripts/public_artifact_privacy_audit.py --self-test
python scripts/public_artifact_privacy_audit.py
python scripts/validate_docs_i18n.py
git diff --check
```

Rust workspace checks:

```bash
cargo fmt --all -- --check
cargo clippy -p openlocus-cli --all-targets -- -D warnings
cargo test --workspace
cargo build --workspace
```

Run only the checks relevant to the change. Remote-provider experiments require explicit opt-in and should not be triggered implicitly by local scripts.

## Documentation links

Product stack bakeoff (Phase A — canonical comparison surface, synthetic-only):

- [EN Phase A design](docs/en/product-bakeoff-phase-a.md)
- [ZH Phase A 设计](docs/zh/product-bakeoff-phase-a.md)
- [Phase A conformance report](artifacts/product_bakeoff_a/product_bakeoff_a_report.json)

Current conclusions:

- [EN current research conclusions](docs/en/current-research-conclusions.md)
- [ZH current research conclusions](docs/zh/current-research-conclusions.md)
- [Current research conclusions index](docs/current-research-conclusions.md)

Route closure and HAAE-A2 closeout:

- [EN HAAE-A2 closeout](docs/en/haae-a2-offline-action-replay-smoke.md)
- [ZH HAAE-A2 closeout](docs/zh/haae-a2-offline-action-replay-smoke.md)
- [HAAE-A2 public report](artifacts/haae_a2_offline_action_replay_smoke/haae_a2_offline_action_replay_smoke_report.json)
- [EN v2 baseline route closure](docs/en/current-route-closure.md)
- [ZH v2 baseline route closure](docs/zh/current-route-closure.md)

Research logs and summaries:

- [EN research log](docs/en/research-log.md)
- [ZH research log](docs/zh/research-log.md)
- [EN research summary](docs/en/research-summary.md)
- [ZH research summary](docs/zh/research-summary.md)

Other entry points:

- [Research design](openlocus-research-design.md)
- [Agent guide](docs/en/AGENTS.md)
- [License](LICENSE) — AGPL-3.0-only

## Notes for contributors

Keep route decisions separate from implementation work. When adding a checkpoint, put detailed evidence in the research logs and link it from concise status summaries. Do not turn local helpers into CI gates unless the route explicitly authorizes that change.
