# BEA-v1-N10EQ Score/Guard Safety Probe Design

Date: 2026-06-30

BEA-v1-N10EQ is a **public-artifact-only design** phase that sits after the
N10EP checkpoint `0a54b49`. It *designs* (does not execute) a forward
score/guard safety probe that, given the frozen arm order and the public N10EO
aggregate mechanism buckets, would flag tasks where the `full` novel-first arm
may displace an already-strong baseline gold file (rank 1-5) into ranks 11-20.
The conservative stop/go authorizes only the **N10ER bounded public CI
score/guard safety probe contract** (a design-only handoff); it does **not**
authorize N10ER execution.

Allowed inputs (public only): the N10EP, N10EO, N10EN, and N10EM public
artifacts/docs/evaluator contracts. Forbidden inputs: the private diagnostic
rerun, private orders/labels, raw candidates/paths/queries/tasks/repos, per-task
diagnostics, cloned repo contents, CI temp dirs, and any new retrieval output.
N10EQ reads none of these; it consumes only public aggregate bucket values.

## N10EP source lock

```text
checkpoint: 0a54b49
status: n10ep_design_response_pass_n10eq_authorized
n10eq_design_only_authorized: true
n10eq_execution_authorized: false
next_phase: BEA-v1-N10EQ Score/Guard Safety Probe Design
source_locked: true
```

## Mechanism lock (re-derived from N10EO public aggregate)

```text
n10eo checkpoint: 6f8eeda
primary mechanism: novel_first_displaced_baseline_gold_from_top10
novel_first_displaced = 2
baseline_gold_rank_1_to_5_displaced = 2
candidate_available_beyond_top10 = 2
guard_better_than_full = 2
full_lost_guard_preserved = 2
low_novelty_bucket_loss = 2
diffaware_full_guard_would_preserve = 2
mechanism_locked: true
```

Both locked misfires fall in the low-novelty (`top5_novel_candidate_item_count_0_to_2`)
bucket: `full` promoted low-novelty candidates ahead of an already-strong
baseline gold hit. `guard` would have preserved both.

## Result

```text
status: n10eq_score_guard_safety_probe_design_pass_n10er_contract_authorized
self-test: 98 / 98
forbidden scan: pass
design-only: true
aggregate-buckets-only: true
n10er_contract_authorized_bool: true
n10er_execution_authorized_bool: false
next allowed phase: BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe
```

## Future probe features (design-only, 7 features)

Each feature derives from **public aggregate buckets only**; none reads
per-task candidates/labels/paths/ranks/gold directly, none tunes the threshold.

| Feature | Addresses misfires | Derivation |
|---|---|---|
| `top5_novel_candidate_item_count_bucket` | 2 | public aggregate novelty buckets (frozen 0_to_2 / 3 / 4_to_5) |
| `baseline_prefix_strength` | 2 | public aggregate baseline hit buckets |
| `baseline_gold_proxy` | 2 | public aggregate baseline hit buckets (bucket-level proxy, not gold labels) |
| `full_displacement_risk` | 2 | public aggregate combination (low-novelty + strong-prefix) |
| `guard_preservation_ref` | 2 | public aggregate guard outcome buckets (reference, not promotion) |
| `candidate_available_beyond_top10` | 2 | public aggregate mechanism buckets |
| `arm_selection` | 2 | frozen rule observable only |

## Probe input/output contracts

**Input contract**: N10EQ itself reads only public artifacts. If N10ER is
separately authorized, it may privately produce/read bounded public-CI arm
orders, raw candidate lists, retrieval output, per-task diagnostic state, and
score-phase labels after orders are frozen. These are execution-time private
inputs only: raw orders/candidates/labels/paths/queries/tasks/repos are never
public outputs, and gold is never used for policy selection.

**Output contract**: the probe emits **aggregate-bucket safety flags only**
(per-bucket displacement-risk counts, guard-preservation reference counts,
arm-selection counts). It does **not** emit per-task flags on raw
candidates/paths/ranks, per-task gold presence, threshold-tuned values,
method-winner claims, or runtime/default changes. Outputs are
scanner-validated for privacy.

## N10ER pass/fail gates (design-only)

1. N10ER may use private bounded-CI execution inputs, but public output must be aggregate-only with zero raw publication.
2. Displacement-risk output is aggregate-bucket only (no per-task raw output).
3. No threshold tuning (frozen threshold >= 4 unchanged).
4. No method-winner claim (no guard/full/diffaware promotion).
5. No runtime/default change (safety probe stays opt-in/eval-only).
6. Reproducibility check on a held-out manifest-listed public sample (not the
   locked N10EN sample); a pass requires an aggregate report without promotion.

All gates are evaluated on aggregate buckets; none uses gold for policy.

## Risk controls (7, all controlled)

| Risk | Mitigation |
|---|---|
| aggregate overinterpretation from two cases | bucket-level proxies; held-out public sample gate blocks locked-sample reuse |
| hindsight threshold tuning in probe design | features use frozen buckets observationally; threshold_tuning_bool=false; N10ER gate blocks tuning |
| guard promotion from two cases | guard_preservation_ref is a reference, not promotion; promotion_authorized_bool=false |
| private diagnostic leakage into probe features | every feature derives from public aggregates only; reads_per_task_data_bool=false; scanner blocks raw keys |
| runtime/default creep via safety probe | runtime_default_change_bool=false; N10ER gate blocks runtime/default change |
| N10ER execution creep from contract authorization | contract_authorized=true but execution_authorized=false; stop/go separates contract from execution |
| feature proxy treated as gold | proxy is bucket-level aggregate inference; score-phase labels may be private in N10ER, but gold_used_for_policy_bool=false |

## Boundary

N10EQ authorizes only the **design** of a score/guard safety probe from public
aggregate artifacts, plus the **N10ER bounded public CI contract handoff**
(design-only). It does **not** authorize: N10ER execution, N10EQ execution,
threshold tuning, new policy experiments, frozen-rule changes, promotion of
guard/full/diffaware, runtime/default changes, method-winner claims,
downstream/scaled retrieval, selector/reranker, provider/model network, raw
diagnostic publication, CI variant execution, or any change to the frozen
rule. All claim-boundary fields for these are `false`.
`n10er_contract_authorized_bool=true` but `n10er_execution_authorized_bool=false`.

Next allowed phase: **BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe**
(contract authorized, execution not authorized).

## Artifact

- Helper: `eval/bea_v1_n10eq_score_guard_safety_probe_design.py`
- Report: `artifacts/bea_v1_n10eq_score_guard_safety_probe_design/bea_v1_n10eq_score_guard_safety_probe_design_report.json`
