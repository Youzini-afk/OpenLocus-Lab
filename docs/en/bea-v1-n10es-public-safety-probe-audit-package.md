# BEA-v1-N10ES Public Safety Probe Audit/Package

Date: 2026-06-30

BEA-v1-N10ES is the **public safety probe audit/package** — a public-only,
no-execution audit of the BEA-v1-N10ER bounded public CI score/guard safety
probe result. It reads **only** the N10ER public aggregate report (+ the N10ER
evaluator/workflow for schema/status validation only) and git metadata (the
`c8fd353` checkpoint that recorded the N10ER result and CI run `28457213423`).
It performs **no** CI rerun, retrieval, recompute, clone, build, or search, and
reads no private directories, CI raw logs, repo clones, raw
candidates/orders/labels/paths/queries/tasks/repos, per-task diagnostics, or
N10EO private rerun data.

## Result

```text
status: n10es_public_safety_probe_audit_package_complete_n10et_authorized
self-test: 31 / 31
forbidden scan: pass
private input reads: 0
retrieval executions: 0
recomputes: 0
CI reruns: 0
clone/build/search: false
n10er source locked: true
next allowed phase: BEA-v1-N10ET Public Safety Probe Design/Decision
```

## N10ER source lock

N10ES locks the N10ER result from its public report and git metadata:

```text
n10er checkpoint: c8fd353 (git commit recording the N10ER result)
n10er CI run: 28457213423 (head 2e7894e)
n10er status: n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized
n10eq checkpoint: 7963831 (upstream, from N10ER source lock)
n10ep checkpoint: 0a54b49 (upstream, from N10ER source lock)
n10eo checkpoint: 6f8eeda (upstream)
n10er report scan: pass
n10er stop/go n10es_audit_authorized: true
source_locked: true
```

## Metric audit (re-expressed from the N10ER public report; no recompute)

N10ES re-expresses the N10ER aggregate metrics and confirms each matches the
locked values — without recomputing anything:

```text
sample: public_task_count=80, scored_task_count=60, task_with_gold_count=40, repo_count=2
heldout overlap: overlap_zero (overlap_count=0)
citation validity: 7772 / 7772
arm aggregates (top10/top20/top50/top100, lost baseline top10):
  baseline:  37 / 39 / 40 / 40 (lost 0)
  full:      36 / 39 / 40 / 40 (lost 1)
  guard:     38 / 39 / 40 / 40 (lost 0)
  diffaware: 37 / 39 / 40 / 40 (lost 1)
risk bucket: task_count=26
risk losses full/guard/diffaware: 0 / 0 / 0
guard_would_preserve_full_loss_count: 0
```

All metric audit `metric_match_bool=true`; every metric record has
`recomputed_bool=false`.

## Interpretation

```text
interpretation_bucket: valid_research_negative
risk_bucket_sufficient: true (task_count=26 >= 5)
signal_reproduced: false
signal_not_reproduced: true
ci_failure: false
not_ci_failure: true
```

The risk bucket was sufficient (`task_count=26`), yet full/guard/diffaware each
lost `0` baseline top-10 hits inside that bucket and
`guard_would_preserve_full_loss_count=0`, so the low-novelty + strong-baseline
full-displacement / guard-preservation safety signal did not reproduce. This is
a **valid research negative, not a CI failure**. The N10ER workflow fails on
contract/privacy/build/clone failures, not on valid no-signal or inconclusive
research results.

## Pass/fail gates (13, audit-only)

1. `n10er_public_source_locked` — N10ER public report locked, status + all locked aggregates match.
2. `n10er_metric_audit_no_recompute` — metrics re-expressed from the public report; no recompute.
3. `n10es_no_threshold_tuning` — frozen threshold unchanged.
4. `n10es_no_method_winner_claim` — no guard/full/diffaware promotion.
5. `n10es_no_runtime_default_change` — audit stays public/eval-only.
6. `n10es_no_promotion_or_frozen_rule_change` — no promotion, no rule change.
7. `n10es_no_ci_rerun_retrieval_recompute` — no CI rerun, retrieval, or recompute.
8. `n10es_no_private_input_read` — no private dirs/logs/clones/raw candidates/orders/labels/paths/queries/tasks/repos or per-task diagnostics read.
9. `n10es_interpretation_consistent_with_locked_aggregates` — interpretation follows from the locked aggregates.
10. `n10er_stop_go_next_phase_match_gate` — N10ER handed off specifically to N10ES.
11. `docs_readback_match_gate` — EN/ZH N10ER docs match the locked result.
12. `readme_readback_match_gate` — README matches the locked result.
13. `current_conclusions_match_gate` — EN/ZH current conclusions match the locked result.

All gates are aggregate-only with `gate_uses_gold_for_policy_bool=false`,
`gate_performs_ci_rerun_bool=false`, `gate_reads_private_input_bool=false`.

## Claim boundary

N10ES is public-only, aggregate-buckets-only, and design/decision-only. All
execution, rerun, retrieval, recompute, tuning, promotion, runtime/default,
method-winner, downstream/scaled retrieval, raw diagnostic publication,
selector/reranker, provider/model network, network-run, and gold-for-policy
fields are `false`. `ci_rerun_bool=false`, `retrieval_recompute_bool=false`,
`promotion_claim_bool=false`, `n10er_execution_authorized_bool=false`,
`n10er_re_run_authorized_bool=false`.

## Stop/go

N10ES authorizes **only** the **BEA-v1-N10ET Public Safety Probe
Design/Decision** handoff (public-only, design/decision-only):
`n10et_design_decision_authorized_bool=true`. It does **not** authorize: N10ES
re-run, any execution, rerun, retrieval, recompute, threshold tuning, new
policy experiments, frozen-rule changes, guard/full/diffaware promotion,
runtime/default changes, method-winner claims, downstream/scaled retrieval, raw
diagnostic publication, CI variant execution, selector/reranker, provider/model
network, or network runs. All such stop/go fields are `false`.

## Workflow

- Audit helper: `eval/bea_v1_n10es_public_safety_probe_audit_package.py`
- The helper exposes `--self-test`, `--validate-report`, and `--out`. It reads
  only the N10ER public report JSON and performs no execution/rerun/recompute.

## Artifact

- Helper: `eval/bea_v1_n10es_public_safety_probe_audit_package.py`
- Report: `artifacts/bea_v1_n10es_public_safety_probe_audit_package/bea_v1_n10es_public_safety_probe_audit_package_report.json`
