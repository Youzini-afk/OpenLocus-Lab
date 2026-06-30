# BEA-v1-N10ET Public Safety Probe Design/Decision

Date: 2026-06-30

BEA-v1-N10ET is the **public-only close-out design/decision** phase for the
BEA-v1-N10E safety-probe branch. It sits after the N10ES checkpoint `8c04a0a`,
which packaged the N10ER bounded public CI score/guard safety probe as a valid
research negative and explicitly authorized only N10ET. N10ET performs **no
execution** and reads **only** public artifacts/docs/current
conclusions/research logs/README and git metadata:

- the committed N10ES public aggregate report (the audit package);
- the committed N10ER public aggregate report (for direct locked-fact
  confirmation, public aggregate fields only);
- the N10ES/N10ER evaluators/workflows for schema/status validation only
  (never executed — no rerun/recompute);
- the N10ES/N10ER EN/ZH docs, EN/ZH current-research-conclusions, EN/ZH
  research-log/summary, and README public readback;
- git metadata: the `8c04a0a` checkpoint that recorded the N10ES result and the
  `c8fd353` checkpoint that recorded the N10ER result / CI run `28457213423`
  (head `2e7894e`).

Forbidden: any private reads (`.openlocus/research-private/`, `/tmp` rerun
paths, CI raw logs, repo clones, raw candidates/orders/labels/paths/queries/
tasks/repos, per-task diagnostics, N10EO private rerun data), any CI rerun, any
retrieval/recompute, any candidate generation, any selector/reranker execution,
any threshold tuning, any promotion, any runtime/default change, or any
method-winner claim.

## N10ES / N10ER source lock

```text
n10es checkpoint: 8c04a0a
n10er checkpoint: c8fd353 (git commit recording the N10ER result)
n10er CI run: 28457213423 (head 2e7894e)
n10er status: n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized
n10es status: n10es_public_safety_probe_audit_package_complete_n10et_authorized
n10es next_allowed_phase: BEA-v1-N10ET Public Safety Probe Design/Decision
n10eq checkpoint: 7963831 (upstream, from N10ES source lock)
n10ep checkpoint: 0a54b49 (upstream, from N10ES source lock)
n10eo checkpoint: 6f8eeda (upstream)
n10es source locked: true
no_ci_rerun / no_retrieval / no_recompute / no_private_input_read: true
source_locked: true
```

## Result

```text
status: n10et_public_safety_probe_design_decision_complete_haae_r0_authorized
self-test: 74 / 74
forbidden scan: pass
private input reads: 0
retrieval executions: 0
recomputes: 0
CI reruns: 0
candidate generations: 0
clone/build/search: false
n10es source locked: true
next allowed phase: BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition
                   Route Design / Schema Preflight
```

## Locked N10ER public aggregates (re-confirmed from N10ES audit; no recompute)

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

## Decision (close-out for the BEA-v1-N10E safety-probe branch)

1. **BEA-v1-N10E / difference-aware remains a local same-source hypothesis.**
   The difference-aware rule (`top5_novel_candidate_item_count >= 4` selects
   guarded, otherwise full) reached `13/60` on the same-source N10DZ/N10EB
   sample but regressed on the N10EN public CI canary (`37/40` vs baseline
   `39/40`), and its held-out safety signal did not reproduce on the N10ER
   public CI sample (risk bucket `26`, losses `0/0/0`). It remains a local
   same-source hypothesis, not a transferable method.
2. **N10ER / N10ES are a valid public held-out negative.** The N10ER held-out
   public CI safety probe (CI run `28457213423`) reproduced zero
   baseline-displacement signal in a sufficient risk bucket (`task_count=26`,
   full/guard/diffaware losses `0/0/0`,
   `guard_would_preserve_full_loss_count=0`). N10ES locked this as a valid
   research negative, not a CI failure. The pair (N10ER, N10ES) is a valid
   public held-out negative for the N10EO low-novelty full-displacement /
   guard-preservation safety signal.
3. **No guard/full/diffaware promotion, no threshold tuning, no N10ER rerun.**
   No guard/full/diffaware promotion, no threshold tuning, no N10ER rerun, no
   CI variant execution, no selector/reranker execution, no new policy
   experiment, no runtime/default change, no method-winner claim, no
   downstream/scaled retrieval, no raw diagnostic publication. All such
   stop/go fields remain `false`.

## Next route — BEA-v1-HAAE-R0 (design/schema preflight only)

N10ET designs (no execution) and authorizes **only** the next route:
**BEA-v1-HAAE-R0 — Hierarchical Actionable Evidence Acquisition Route Design /
Schema Preflight**. HAAE-R0 is a design/schema preflight only: it designs how
evidence-acquisition actions can be layered hierarchically (anchor /
span-window / candidate-source / scheduler / safety-probe) while preserving
`EvidenceCore` and abstaining when current-source evidence is unavailable, and
preflights the route's public schema, source inputs, claim boundary, and
stop/go contract before any future execution-authorized phase is opened.

HAAE-R0 reads only public artifacts/docs and git metadata: the closed
N10ES/N10ER/N10EQ/N10EP/N10EO public aggregates, the BEA-v1 actionability-matrix
/ trace-surface contracts, and the research-design schemas. It performs no
private reads, no CI rerun, no retrieval/recompute, no candidate generation,
and no selector/reranker execution.

### HAAE-R0 explicit non-identities

HAAE-R0 is explicitly **not** any of the following (each route record and the
stop/go record carries the corresponding non-identity boolean):

- **not BEA-v1-A** — it is not the coverage-preserving selector route.
- **not selector-only** — it is not a selector-only design.
- **not selector/reranker execution** — it does not execute a selector or
  reranker.
- **not P5** — it is not the P5 selector/reranker phase.
- **not runtime/default promotion** — it does not change runtime/default
  behavior.

## Risk controls

| Risk | Mitigation |
|---|---|
| promotion from a valid research negative | guard_full_diffaware_promotion_authorized_bool=false; method_winner_claim_authorized_bool=false; no arm is promoted |
| hindsight threshold tuning from no-signal | threshold_tuning_authorized_bool=false; frozen rule unchanged; any threshold design must use held-out public evidence |
| N10ER rerun creep | n10er_re_run_authorized_bool=false; ci_variant_execution_authorized_bool=false; recompute_authorized_bool=false; rerun_authorized_bool=false |
| HAAE-R0 drift into selector / P5 / runtime | every HAAE-R0 route record carries the non-identity booleans; selector_reranker_authorized_bool=false; runtime_default_change_authorized_bool=false; bea_v1_a_authorized_bool=false; p5_authorized_bool=false |
| runtime/default creep | runtime_default_change_authorized_bool=false; any HAAE route remains opt-in/eval-only; no runtime or default change |
| private diagnostic leakage | N10ET reads only public aggregate artifacts/docs/git metadata; forbidden_scan blocks raw per-task/paths/orders/labels keys and private rerun paths; aggregate_buckets_only_bool=true |
| aggregate overinterpretation from two cases / no-signal | N10ET is a public-only close-out design/decision; no promotion, no rule change, no method-winner claim; HAAE-R0 is design/schema-preflight only |

## Pass/fail gates (20 logical checks / 21 artifact gate records, audit-only)

1. `n10es_public_source_locked` — N10ES public report locked, status + all locked aggregates match.
2. `n10er_public_facts_locked` — N10ER checkpoint / CI run / status match the locked values.
3. `n10es_metric_audit_no_recompute` — metrics re-confirmed from the N10ES audit; no recompute.
4. `n10et_no_threshold_tuning` — frozen threshold unchanged.
5. `n10et_no_method_winner_claim` — no guard/full/diffaware promotion.
6. `n10et_no_runtime_default_change` — close-out stays public/eval-only.
7. `n10et_no_promotion_or_frozen_rule_change` — no promotion, no rule change.
8. `n10et_no_ci_rerun_retrieval_recompute_candidate_generation` — no CI rerun, retrieval, recompute, or candidate generation.
9. `n10et_no_private_input_read` — no private dirs/logs/clones/raw candidates/orders/labels/paths/queries/tasks/repos or per-task diagnostics read.
10. `n10et_no_selector_reranker_no_p5_no_bea_v1_a` — no selector/reranker, no P5, no BEA-v1-A.
11. `n10et_no_n10er_rerun` — no N10ER rerun.
12. `n10et_interpretation_consistent_with_locked_aggregates` — interpretation follows from the locked aggregates.
13. `n10es_stop_go_next_phase_match` — N10ES handed off specifically to N10ET.
14. `n10er_stop_go_next_phase_match` — N10ER handed off specifically to N10ES.
15. `docs_readback_match_gate` — EN/ZH N10ET + N10ES docs match the locked result.
16. `readme_readback_match_gate` — README matches the locked result.
17. `current_conclusions_match_gate` — EN/ZH current conclusions match the locked result.
18. `research_log_match_gate` — EN/ZH research logs match the locked result.
19. `research_summary_match_gate` — EN/ZH research summaries match the locked result.
20. `haae_r0_authorized_design_only_schema_preflight_gate` plus the separate artifact `haae_r0_non_identity_gate` — only HAAE-R0 design/schema preflight authorized, with non-identity booleans.

All gates are aggregate-only with `gate_uses_gold_for_policy_bool=false`,
`gate_performs_ci_rerun_bool=false`, `gate_reads_private_input_bool=false`.

## Claim boundary

N10ET is public-only, aggregate-buckets-only, and design/decision-only. All
execution, rerun, retrieval, recompute, candidate generation, tuning,
promotion, runtime/default, method-winner, downstream/scaled retrieval, raw
diagnostic publication, selector/reranker, provider/model network, network-run,
and gold-for-policy fields are `false`. `ci_rerun_bool=false`,
`retrieval_recompute_bool=false`, `promotion_claim_bool=false`,
`candidate_generation_bool=false`, `n10er_execution_authorized_bool=false`,
`n10er_re_run_authorized_bool=false`. The HAAE-R0 non-identity booleans
(`haae_r0_not_bea_v1_a_bool`, `haae_r0_not_selector_only_bool`,
`haae_r0_not_selector_reranker_execution_bool`, `haae_r0_not_p5_bool`,
`haae_r0_not_runtime_default_promotion_bool`) are all `true`.

## Stop/go

N10ET authorizes **only** the **BEA-v1-HAAE-R0 Hierarchical Actionable Evidence
Acquisition Route Design / Schema Preflight** handoff (public-only,
design-only, no execution):
`haae_r0_design_only_schema_preflight_authorized_bool=true`,
`haae_r0_execution_authorized_bool=false`. It does **not** authorize: N10ET
re-run, N10ES re-run/audit, any execution, rerun, retrieval, recompute,
candidate generation, threshold tuning, new policy experiments, frozen-rule
changes, guard/full/diffaware promotion, runtime/default changes,
method-winner claims, downstream/scaled retrieval, raw diagnostic publication,
CI variant execution, selector/reranker, BEA-v1-A, P5, provider/model network,
or network runs. All such stop/go fields are `false`.

The detailed source of truth for the closed N10E branch is
[`current-research-conclusions.md`](current-research-conclusions.md) together
with the per-phase N10EO/N10EP/N10EQ/N10ER/N10ES docs.

## Workflow

- Design/decision helper: `eval/bea_v1_n10et_public_safety_probe_design_decision.py`
- The helper exposes `--self-test`, `--validate-report`, and `--out`. It reads
  only the N10ES + N10ER public reports and public docs, and performs no
  execution/rerun/recompute/candidate generation.

## Artifact

- Helper: `eval/bea_v1_n10et_public_safety_probe_design_decision.py`
- Report: `artifacts/bea_v1_n10et_public_safety_probe_design_decision/bea_v1_n10et_public_safety_probe_design_decision_report.json`
