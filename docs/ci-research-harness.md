# CI Research Harness (R46–R50)

## Overview

The CI research harness provides a fully automated, deterministic benchmark pipeline for evaluating OpenLocus retrieval strategies in CI. It enforces strict RUN/SCORE phase separation, citation validity, private-field isolation, and no-promotion guarantees.

## Requirements

| Req | Component | Description |
|-----|-----------|-------------|
| R46 | `ci_repos/openlocus-ci-repos-v1.yaml` | Repo catalog for CI benchmark targets |
| R46 | `ci_clone_and_lock_repo.py` | Clone, hash, and lock repos into `repo-lock.json` |
| R47 | `ci_generate_tasks.py` | Generate public tasks JSONL and private labels JSONL from `repo-lock.json` |
| R48 | `ci_run_strategy_matrix.py` | RUN phase: execute strategies on public tasks with citation validation |
| R49 | `ci_score_strategy_matrix.py` | SCORE phase: compute metrics against labels |
| R50 | `ci_validate_report.py` | Gate CI: assert all invariants hold |

## RUN/SCORE Boundary

The RUN phase and SCORE phase are strictly separated:

- **RUN phase** (`ci_run_strategy_matrix.py`):
  - Inputs: public tasks JSONL + `repo-lock.json` + openlocus binary + out-dir
  - Loads **only** public task fields: `test_id`, `repo_id`, `query`, `public_version`, `source`
  - Never reads labels or private fields
  - Runs all implemented strategies against isolated repo roots
  - Validates citations fail-closed via `openlocus citations validate` while repo roots exist
  - Scans all run artifacts for private-field leakage
  - Writes all run artifacts (predictions, traces, rejections) before any label access

- **SCORE phase** (`ci_score_strategy_matrix.py`):
  - Inputs: labels JSONL + run output directory
  - Computes metrics using helper semantics compatible with `r29_r26_stress_matrix.py`
  - Never invokes the openlocus CLI
  - Computes `delta_vs_r29_baseline` for strategies with R29 baseline data
  - Reports `promotion_ready=false`, `default_should_change=false`

This separation ensures the runner cannot accidentally use label information, and the scorer cannot accidentally invoke the binary.

## Repo Lock

`repo-lock.json` is the single source of truth for external repo content:

- Each entry contains: `repo_id`, `commit`, `source` (path/type), `content_manifest_sha`, `metadata` (extensions, files, lines), `policy` (exclude patterns)
- The content manifest SHA is computed by normalizing all source files (sorted by path, SHA-256 per file, line-count) and hashing the concatenation
- The RUN phase re-verifies the manifest SHA before creating isolated roots
- Unknown `repo_id` values are critical failures — the harness never falls back to the full workspace

## Task Categories

`ci_generate_tasks.py` auto-generates six categories from repo source scanning:

| Category | Expected Behavior | Description |
|----------|------------------|-------------|
| `positive` | `primary_evidence` | Exact symbol names from source; should be easily retrievable |
| `negative` | `abstain` or `no_primary` | Non-existent symbols/features; tests hallucination resistance |
| `ambiguous` | `weak_candidates` or `abstain` | Vague/ambiguous queries; tests noise detection |
| `hard_distractor` | `primary_evidence` | Same-name symbols across files; tests disambiguation |
| `stale-like` | `abstain` | Deprecated/stale concept queries; tests outdated-match resistance |
| `dense_quiver_trap` | `abstain` | Vector/QuIVer terminology that doesn't exist; tests false-positive from naming |

Public tasks contain **only**: `test_id`, `repo_id`, `query`, `public_version`, `source`.

Private labels contain: `gold_spans`, `hard_distractors`, `must_not_primary`, `expected_behavior`, `source_category`, `risk_tags`, `oracle_type`, `why_this_is_hard`, `which_strategy_it_targets`.

## Strategy Matrix

### Implemented (11)

1. `regex` — openlocus search regex
2. `bm25` — openlocus search bm25
3. `symbol` — openlocus search symbol
4. `rrf` — openlocus retrieve (RRF fusion)
5. `bm25_regex` — RRF fuse bm25+regex
6. `bm25_symbol` — RRF fuse bm25+symbol
7. `query_noise_plus_rrf_agree_min` — noise guard + agreement threshold
8. `rrf_guarded_by_symbol_regex` — RRF only if symbol or regex has evidence
9. `dense_mock` — openlocus dense build/search --provider mock
10. `ast_chunk_bm25` — BM25 with AST chunking
11. `graph_basic` — derive top path → openlocus impact --depth 1

### Unavailable (2)

| Strategy | Reason |
|----------|--------|
| `DenseReal` | not_configured_or_policy_disabled |
| `QuIVer` | quiver_not_implemented |

Unavailable strategies output **reason-only** status files with no metrics or quality numbers. The validator asserts this invariant.

## Delta vs R29 Baseline

The score report includes `delta_vs_r29_baseline` for strategies with R29 baseline data. This enables tracking whether CI benchmark results drift from the known R29 stress-matrix baselines (which ran on 1100 R26 auto-stress tasks).

Key R29 baselines:
- `rrf`: FileRecall@1=0.803, MRR=0.858, primary_false_positive_rate=0.453
- `query_noise_plus_rrf_agree_min`: FileRecall@1=0.803, primary_false_positive_rate=0.106
- `symbol`: FileRecall@1=0.686, SpanF0.5=0.291, primary_false_positive_rate=0.080

CI benchmarks use different repos/tasks than R29, so deltas are expected. The baseline serves as a reference point, not a pass/fail gate.

## Remote Provider Gating

Remote providers (real embeddings, QuIVer) are **disabled by default** in CI and
currently remain reason-only/unavailable in the harness:

- `OPENLOCUS_ALLOW_REMOTE=1` must be explicitly set to enable remote providers
- The GitHub Actions workflow only sets this flag on `workflow_dispatch` with `enable_remote_models=true`
- Scheduled and PR runs never enable remote providers
- Current R50 behavior: `dense_real` / `DenseReal` and `QuIVer` are reported as
  unavailable with reason-only status; no fake quality metrics are emitted
- Future provider execution, if added, must remain `workflow_dispatch`-only,
  require `OPENLOCUS_ALLOW_REMOTE=1`, and stay candidate/supporting-only

## No Promotion

The CI harness explicitly does **not** support promotion:

- `promotion_ready` is always `false`
- `default_should_change` is always `false`
- The harness is a failure-surface probe, not a retrieval strategy promotion mechanism
- Labels are weak/mined/deterministic/stress — not human-verified
- `dense_mock` is candidate-channel safety smoke, not semantic quality
- `graph_basic` is deterministic depth=1, not precise call/type graph

## Citation Validity

Citation validity must be **1.0** for all implemented strategies:

- Every citation is validated via `openlocus citations validate` while isolated roots exist
- Validation is fail-closed: hash + range + path must all be valid
- If any citation is invalid, the run exits non-zero
- The validator (`ci_validate_report.py`) asserts `citation_validity_all_implemented == true`

## Private Field Scan

All artifacts (run and score) are scanned for private-field leakage:

- Forbidden fields: `source_category`, `risk_public`, `intent_guess`, `risk_tags`, `oracle_type`, `expected_behavior`, `gold_spans`, `hard_distractors`, `must_not_primary`, `why_this_is_hard`, `which_strategy_it_targets`
- Run artifacts must not contain any private fields
- Score report includes `private_scan_summary` with `clean: true/false`
- The validator fails CI if the scan is not clean

## GitHub Actions Workflow

`.github/workflows/retrieval-benchmark.yml`:

| Trigger | Tier | Repos | Timeout |
|---------|------|-------|---------|
| `pull_request` | smoke | 4–6 small/medium | 45 min/job |
| `schedule` (nightly) | nightly | 15–20 medium | 45 min/job |
| `schedule` (weekly) | weekly | large repos, repo × task-shard matrix | 45 min/job |
| `workflow_dispatch` | configurable | configurable | configurable |

- `permissions: contents:read` only — no `pull_request_target`
- Unique artifacts per repo/shard (no raw source artifacts or evidence excerpts uploaded)
- `repo-lock.json` used for every external repo
- Remote providers only on `workflow_dispatch` with `enable_remote_models=true`

## Pipeline Flow

```
ci_clone_and_lock_repo.py          →  repo-lock.json
                                        ↓
ci_generate_tasks.py --no-labels      tasks/ci_tasks.jsonl
                                        ↓
ci_run_strategy_matrix.py            run/{strategy}-predictions.jsonl
                                      run/run-manifest.json
                                        ↓
ci_generate_tasks.py                 labels/ci_labels.jsonl
                                        ↓
ci_score_strategy_matrix.py          score/report.json
                                        ↓
ci_validate_report.py                exit 0 or 1
```
