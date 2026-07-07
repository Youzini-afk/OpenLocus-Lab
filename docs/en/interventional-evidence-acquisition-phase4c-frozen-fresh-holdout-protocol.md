# Interventional Evidence Acquisition Phase 4C Frozen Fresh-Holdout Protocol

Date: 2026-07-07

Phase: `phase4c_frozen_fresh_holdout_protocol_design_only`

Status: `phase4c_frozen_fresh_holdout_protocol_design_only_no_execution`

This is design only. It does not read private rows, create manifests, read source for new evidence, collect data, train or fit a model, change CI, change runtime/default behavior, add retrieval families, or make a method claim.

## Why this exists

Phase 4B showed only a small local screen over existing ignored Phase 2/3 private rows. It did not prove a working model, method victory, lift, product readiness, or default change.

The next real check must use fresh hard current-source tasks that were not used in Phase 2, Phase 3, or Phase 4B. Phase 4C freezes that future holdout protocol before any execution, so a later Phase 4D cannot tune on the same private rows.

## Frozen basis

- Code/protocol basis commit: `6626075`.
- Seven existing labels only:
  - `bm25_then_read_top1`
  - `bm25_then_read_next_unique_file`
  - `symbol_regex_then_read_top1`
  - `symbol_regex_then_read_next_unique_file`
  - `read_related_test_when_available`
  - `stop`
  - `abstain`
- Feature set only:
  - `action_label`
  - `task_family_bucket`
  - `availability_bucket`
  - `budget_bucket`
- Screen method: stdlib-only smoothed categorical table, deterministic.
- No sklearn, numpy, torch, provider, network, LLM, or reusable model artifact.
- Fit source must be predeclared Phase 2 training rows or another separately frozen source.
- Do not fit or tune on fresh holdout rows.
- Thresholds, control buckets, status values, and validation rules must be fixed before reading holdout rows.

## Future Phase 4D shape

- Target: 12 fresh hard current-source tasks.
- Hard max: 16 tasks.
- Fixed labels/actions: the same seven labels above.
- Private row cap: 112 rows.
- Private manifest and private rows: ignored `runs/` only.
- No reuse of Phase 2/3/4B tasks where privately detectable.

## Future public report fields

If Phase 4D is separately authorized later, public output may include only aggregate fields:

- coarse task and row buckets;
- screen bucket;
- shuffled/control buckets;
- evidence materialization pass bucket;
- overlap check bucket;
- privacy validation;
- conservative recommendation.

No public output may include private rows, task text, task IDs, exact paths, ranges, hashes, snippets, run directories, manifests, labels, prompts, responses, or provider payloads. No exact `count_1` values should appear.

## Future statuses

Allowed future Phase 4D statuses are only:

- `stop_no_learning_claim`
- `repair_holdout_contract_no_claim`
- `fresh_holdout_screen_positive_no_claim`

## Must-have validations before any Phase 4D result is accepted

- No `runs/` files staged.
- Overlap with Phase 2/3 private tasks, paths, and ranges rejected where privately checkable.
- No feature, threshold, or table changes after holdout rows are read.
- Evidence success requires real current-source read plus private path/range/hash/currentness/range match and task tie.
- Candidate-found alone is not evidence.
- `stop` and `abstain` success remains `count_0`.
- Public report rejects private references, exact `count_1`, and claim terms.
- Public privacy audit and CI are green before any public closeout.

## Forbidden

- No RPM-D2/model scaling.
- No LLM/provider/network.
- No runtime/default change.
- No new retrieval family.
- No reusable model artifact.
- No training on holdout rows.
- No tuning after holdout.
- No winner, lift, product, default, or method claim.
- No public private refs or raw rows.

## Outcome of Phase 4C

Phase 4C freezes the design for a possible future Phase 4D. It does not authorize Phase 4D execution by itself.

## Phase 4D execution note

Phase 4D was later run as a standalone local screen using this frozen protocol. Public report: [`phase4d_frozen_fresh_holdout_report.json`](../../artifacts/phase4d_frozen_fresh_holdout/phase4d_frozen_fresh_holdout_report.json). Status is `fresh_holdout_screen_positive_no_claim`.

The Phase 4D result remains no-claim. It used ignored private input/output, published aggregate buckets only, created no reusable model artifact, and does not support winner, lift, product, default, provider/network, or runtime claims.

## Phase 4E closeout pointer

Phase 4E closes this small-check sequence using only public Phase 4B/4C/4D reports/docs. See [`interventional-evidence-acquisition-phase4e-closeout.md`](./interventional-evidence-acquisition-phase4e-closeout.md). It keeps the route as a research candidate but stops here to avoid result-shopping; any next empirical step needs a separate larger validation decision or independent replication protocol.
