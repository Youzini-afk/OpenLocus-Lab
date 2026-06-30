# BEA-v1-N10EN Difference-Aware Winner Broader-Sample CI Validation Canary

Date: 2026-06-30

BEA-v1-N10EN is the first real bounded public CI canary for the frozen
difference-aware rule. It is gated on the BEA-v1-N10EM public replication package
and its scoped `n10en_ci_handoff_records`, and it is `workflow_dispatch` only.

## Default behavior (fail-closed)

With `enable_public_github_network` left at its default `false`, the canary
does NOT clone, build, search, or generate candidates. It emits a fail-closed /
unavailable artifact and exits 0:

```text
status: n10en_public_github_network_disabled_unavailable_fail_closed
forbidden scan: pass
run_phase_labels_used_bool: false
score_phase_labels_used_bool: false
clone_run_bool: false
search_run_bool: false
```

This is the safe state committed to the repo. The committed artifact is the
network-disabled fail-closed report, not a real canary run.

## Network-enabled canary

When `enable_public_github_network` is explicitly set to `true`, the canary:

- clones **manifest-listed public repos only** (reusing `ci_clone_and_lock_repo.py`);
- generates **public tasks with `--no-labels` first** so the RUN phase sees no
  labels/gold;
- builds and uses the checked-out local OpenLocus CLI to materialize temporary
  public candidates in runner temp space;
- applies the four frozen transforms **inside the N10EN helper** (not by bending
  `ci_run_strategy_matrix`);
- fixes the RUN-phase orders, THEN generates score-phase labels and scores the
  fixed orders (labels/gold used for aggregate scoring only, never for policy);
- uploads only a sanitized aggregate-only report.

### Candidate / run contract

- Baseline candidates: `openlocus search bm25 <query> --limit 100 --json`.
- Old-pool proxy: union of `openlocus search regex <query> --json` (sliced to
  20; the CLI regex subcommand has no `--limit` flag) and
  `openlocus search symbol <query> --limit 20 --json` file identities.
- Frozen transforms (ported verbatim from N10EL/N10EK):
  - `baseline` = raw BM25 top-100 order;
  - `full` = full novel-first (novel candidates before old-pool, top-10 head);
  - `guarded` = keep original top-5, then append distinct novel files from rank >5 until top-10;
  - `diffaware` = `guarded` iff top5 novel candidate item count >= 4 else `full`.
- Top-5 novelty counts **candidate items, not distinct files**.
- RUN phase input is public tasks only; no labels/gold are read.
- Orders are written to runner temp space only and are never uploaded.

### Score contract

- Labels/gold are generated/read only after RUN outputs are fixed.
- Gold is used only for aggregate scoring, never for policy.
- Report booleans: `run_phase_labels_used_bool=false`,
  `score_phase_labels_used_bool=true`, `gold_used_for_policy_bool=false`.

## Aggregate report schema

The sanitized report is aggregate-only. It records: schema/phase/status; the
N10EM gate and scoped handoff authorization; repo/task/candidate counts;
`baseline`/`full`/`guard`/`diffaware` top10/top20/top50/top100; lost baseline
top10; selected-arm counts; top-5 novelty buckets; citation-validity
aggregate; run/score flags; privacy scan; and claim boundaries.

Forbidden in the artifact: repo names/URLs, commit SHAs, task IDs, queries,
paths/filenames, candidate lists/orders, labels/gold spans, exact ranks,
scores, snippets/content, hashes/provider payloads.

## CI pass/fail semantics

The workflow fails on contract failures only: N10EM gate failure, build/clone
failure, task-generation failure, no tasks, privacy-scan failure, labels used in
the RUN phase, provider/network policy violation, citation-validation failure,
or raw-upload violation.

Outcome regression is a valid research result, **not** an infrastructure
failure. The outcome status records `positive` / `neutral` / `regression` and
hands off to N10EO.

## Boundary

N10EN authorizes only bounded public CI clone/build/search, temporary public
candidate materialization in runner temp space, score-phase labels after RUN
outputs are fixed, and sanitized aggregate upload. It does not authorize
private rows, provider/model network, remote embeddings, QuIVer/dense real,
external benchmark downloads, raw candidate/label/query/path upload,
runtime/default changes, selector/reranker, method-winner claims, downstream
claims, heldout/generalization claims, scaled retrieval, or production
retrieval changes.

## Artifact

- Helper: `eval/bea_v1_n10en_difference_aware_ci_canary.py`
- Workflow: `.github/workflows/bea-v1-n10en-difference-aware-ci-canary.yml`
- Report: `artifacts/bea_v1_n10en_difference_aware_ci_canary/bea_v1_n10en_difference_aware_ci_canary_report.json`
