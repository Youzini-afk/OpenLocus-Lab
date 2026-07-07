# Interventional Evidence Acquisition Phase 3B Closeout

Date: 2026-07-07

Phase: `phase3b_cross_phase_public_replication_closeout`

Status: `phase3b_cross_phase_public_replication_closeout_no_claim`

This is a public closeout only. It uses the already public Phase 2 and Phase 3 aggregate reports. It does not read private rows, read source for new evidence, collect data, add scripts, add evaluator modes, or create private artifacts.

## Public inputs

- Phase 2 report: [`phase2_small_fair_local_comparison_pilot_report.json`](../../artifacts/phase2_small_fair_local_comparison_pilot/phase2_small_fair_local_comparison_pilot_report.json).
- Phase 3 report: [`phase3_independent_local_holdout_validation_screen_report.json`](../../artifacts/phase3_independent_local_holdout_validation_screen/phase3_independent_local_holdout_validation_screen_report.json).

Both reports are public aggregate-only reports.

## Replicated bucket-level pattern

Phase 2 and Phase 3 both show the same protocol-level pattern at bucket level:

- Both passed local validation checks used for their reports.
- Both public reports are no-claim positive screens.
- Both report best fixed acquisition baseline bucket `count_21_to_50`.
- Both report best fixed local baseline bucket `count_21_to_50`.
- Both report control success bucket `count_0`.
- EvidenceCore boundaries held: candidate-found is not evidence, and counted success requires current-source materialization with hash/currentness checks.
- Private/public boundaries held: private rows were not published and public outputs stayed aggregate-only.

This means the small local comparison protocol is worth preserving as a research asset.

## What this does not prove

This closeout does not prove which method is best. The best fixed label is a baseline, not a winner.

It also does not justify:

- lift or signal claims;
- product readiness claims;
- runtime/default changes;
- provider/network changes;
- model training;
- OpenLocus v3 branding.

## Risks and limits

- Buckets are coarse.
- Exact effects are hidden for privacy.
- Private tasks are not public-auditable.
- Positive screens are not generalization proof.
- The best fixed label is the baseline, not a winner.

## Future Phase 4 note

If there is any Phase 4, it should start as design-only action-outcome learning precheck. No model training should begin until feature, label, leakage, and split rules are written and reviewed.

Phase 4 design is now documented in [`interventional-evidence-acquisition-phase4-learning-precheck-design.md`](./interventional-evidence-acquisition-phase4-learning-precheck-design.md). It remains design-only and does not authorize training.
