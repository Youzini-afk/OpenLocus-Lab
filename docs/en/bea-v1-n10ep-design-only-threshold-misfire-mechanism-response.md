# BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism Response

Date: 2026-06-30

BEA-v1-N10EP is a **public-artifact-only design packaging** phase that sits
after the N10EO checkpoint `6f8eeda`. It re-expresses the N10EO aggregate
mechanism buckets as a *design-only* response: it describes forward design
options (N10EQ score/guard safety probe, N10ER public CI small variant, and a
stop-design-only-insufficient option), records the risk controls that bound
those options, and emits a conservative stop/go decision. N10EP performs **no
execution**.

Allowed inputs (public only): the committed N10EO public aggregate artifact,
the N10EN public aggregate artifact, the N10EM public artifact/docs/evaluator
contract, and public docs/code metadata. Forbidden inputs:
`/tmp/n10eo_diag_rerun`, `orders.private.json`, private labels JSONL, raw
candidates/orders/paths/queries/tasks/repos, per-task diagnostics, cloned repo
contents, and any new retrieval/CI variants/policy execution. N10EP reads none
of the private diagnostic inputs that N10EO used; it consumes only public
aggregate bucket values.

## N10EO source lock

```text
checkpoint: 6f8eeda
status: n10eo_failure_analysis_pass_mechanism_identified
next_allowed_phase: BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism Response
source_locked: true (status, primary mechanism, aggregate counts, mechanism
  buckets, full/guard outcome, low-novelty bucket loss all match)
```

## Result

```text
status: n10ep_design_response_pass_n10eq_authorized
self-test: 69 / 69
forbidden scan: pass
design-only: true
aggregate-buckets-only: true
next allowed phase: BEA-v1-N10EQ Score/Guard Safety Probe Design
```

## Mechanism response summary (public aggregate values)

The frozen difference-aware rule is
`if top5_novel_candidate_item_count >= 4 then guarded else full`. On the N10EN
public CI canary, the rule misfired on 2 of 49 `full`-selected tasks:
`full`'s novel-first reordering displaced baseline gold already at rank 1-5
into ranks 11-20. `guard` would have preserved both.

| Aggregate | Value |
|---|---|
| baseline / full / guard / diffaware top10 | 39 / 37 / 39 / 37 |
| full_lost / guard_lost / diffaware_lost | 2 / 0 / 2 |
| guard_better_than_full | 2 |
| full_lost_guard_preserved | 2 |
| baseline_gold_rank_1_to_5_displaced | 2 |
| candidate_available_beyond_top10 | 2 |
| novel_first_displaced_baseline_gold_from_top10 | 2 |
| low_novelty_bucket_loss (0_to_2 bucket) | 2 |
| diffaware_full_guard_would_preserve | 2 |

Both losses fall in the low-novelty (`top5_novel_candidate_item_count_0_to_2`)
bucket: `full` promoted low-novelty candidates ahead of an already-strong
baseline hit. The gold candidate remained available beyond top-10, so the
loss is a reordering displacement, not a missing-candidate failure.

## Design options (design-only, no execution)

### N10EQ — Score/Guard Safety Probe Design

Design a score/guard safety probe that, given a frozen arm order and the
`top5_novel_candidate_item_count` feature, flags tasks where the full
novel-first arm may displace an already-strong baseline gold file (rank 1-5)
into ranks 11-20. The probe uses only aggregate-bucket diagnostics from N10EO;
no per-task candidates/labels/paths/ranks are read. This design is
**authorized for the next phase** (design-only; execution still unauthorized).

### N10ER — Public CI Small Variant Design

Design a small public CI variant that re-runs the frozen difference-aware rule
on a slightly different manifest-listed public sample to confirm whether the
threshold-misfire reproduces or was a 2-case artifact. The design is
public-CI-only and reuses the N10EN bounded canary scope. Under the
conservative default this design is **packaged but not yet authorized** for
the next phase (use `--authorize-n10er-design` to authorize both N10EQ and
N10ER designs; execution remains unauthorized either way).

### Stop — Design-Only Insufficient

Design-only analysis from 2 aggregate misfire cases is insufficient to resolve
the threshold-misfire. No design is promoted to execution on the strength of 2
cases alone; further bounded public evidence is required before any rule
change, promotion, or execution.

## Risk controls

| Risk | Mitigation |
|---|---|
| aggregate overinterpretation from two cases | design-only response; no promotion or rule change; explicit stop_design_only_insufficient option |
| hindsight threshold tuning | threshold_tuning_authorized_bool=false; frozen rule unchanged; any threshold design must use held-out public evidence |
| guard promotion from two cases | guard_full_diffaware_promotion_authorized_bool=false; no arm is promoted; design-only N10EQ safety probe instead |
| public CI variant as method winner | method_winner_claim_authorized_bool=false; N10ER is design-only, not executed, not a method winner even if later run |
| private diagnostic leakage | N10EP reads only public aggregate artifacts; forbidden_scan blocks raw per-task/paths/orders/labels keys and the private rerun path |
| runtime/default creep | runtime_default_change_authorized_bool=false; any safety probe remains opt-in/eval-only; no runtime or default change |

## Boundary

N10EP authorizes only **design-only** response packaging from the N10EO public
aggregate artifact. It explicitly does **not** authorize: threshold tuning, new
policy experiments, frozen-rule changes, promotion of guard/full/diffaware,
runtime/default changes, method-winner claims, downstream/scaled retrieval,
selector/reranker, provider/model network, raw diagnostic publication, CI
variant execution, or any change to the frozen rule. All claim-boundary fields
for these are `false`. The conservative stop/go authorizes only the N10EQ
design (no execution); the N10ER design is packaged but not authorized under
the default. No private diagnostic inputs are read.

Next allowed phase: **BEA-v1-N10EQ Score/Guard Safety Probe Design**
(design-only, no execution).

## Artifact

- Helper: `eval/bea_v1_n10ep_design_only_threshold_misfire_mechanism_response.py`
- Report: `artifacts/bea_v1_n10ep_design_only_threshold_misfire_mechanism_response/bea_v1_n10ep_design_only_threshold_misfire_mechanism_response_report.json`
