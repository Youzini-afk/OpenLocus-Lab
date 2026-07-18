# Product Bakeoff B3 Post-result Design Audit

Date: 2026-07-18

Status: `product_bakeoff_b3_decision_and_replication_design_audited_result_frozen`

The formal B3 execution remains valid and frozen. It completed all 48 logical tasks, 360 groups, and 1,440 records, passed every pre-score integrity gate, and made zero provider/network calls. This audit does not reopen, rescore, rerank, or reclassify that result. Its purpose is narrower: determine whether the frozen decision and replication design answered the intended product-selection question strongly enough.

The machine-readable audit is [`product_bakeoff_b3_design_audit.json`](../../artifacts/product_bakeoff_b3_design_audit/product_bakeoff_b3_design_audit.json).

## Decision-rule finding

B3 reused the absolute B2 quality floors without calibrating their reachability on the fresh B3 panel. The observed candidate maxima were below the corresponding floors across every core dimension:

| Measure | Frozen floor | Best B3 candidate | B3 baseline |
|---|---:|---:|---:|
| task success | 34 | 29 | 23 |
| one-shot success | 30 | 26 | 23 |
| answerable-target success | 34 | 27 | 19 |
| ambiguous-status success | 5 | 1 | 1 |
| minimum language stratum | 11 | 9 | 7 |
| minimum size stratum | 8 | 5 | 4 |
| minimum role stratum | 8 | 3 | 0 |

All five candidates therefore shared the same seven absolute-floor failures. The S0 baseline was checked for execution integrity but was not subjected to those candidate floors; if evaluated counterfactually under the same floor gate, it would fail the same seven dimensions. Candidates were removed before competition ranking, so the implemented competition-tie rule was never reached and both quality and resource rank maps were empty.

This means B3 validly answered a narrow deployment-eligibility question under its frozen rules, but did not provide the relative ordering and uncertainty needed for a useful product-selection decision.

## Replication finding

B3 was one frozen holdout panel. The quality evidence comprised 48 paired logical tasks nested in 12 repository clusters. Four technical repetitions checked repeatability and resource behavior; they did not create additional independent quality samples. The 1,440 logical records therefore cannot be treated as an independent sample size, and B3 did not estimate between-panel variability or support a population-generalization claim.

The public aggregates retain planning signals only. S1 improved task success by 3 and answerable-target success by 5 relative to S0 while keeping warm-query P95 near the baseline. S4 improved task success by 6 and one-shot success by 3 but used roughly twice the warm-query time. These are descriptive pilot observations, not confirmatory effects, and B3 is not counted as a B4 replication.

## Corrective route

B4 narrows the experiment to S0, S1, and S4; freezes twelve mutually disjoint panels before treatment; treats repositories as replication clusters; ranks every arm before deployment gates; and always publishes paired effects, confidence intervals, competition ranks, panel-direction counts, and a Pareto frontier. Exact ties continue to share rank. A failed deployment gate may block promotion, but it can no longer erase the comparative result.

No B4 runtime, private holdout, launch authorization, or treatment output exists at this checkpoint.
