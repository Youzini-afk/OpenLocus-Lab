# Product Bakeoff B4 Independent Replication Protocol

Date: 2026-07-18

Status: `product_bakeoff_b4_independent_replication_protocol_frozen_no_runtime_no_holdout_no_execution`

B4 is a new future experiment, not a continuation or reinterpretation of B3. The public B3 aggregate is used only to select a bounded three-arm question and sensitivity scenarios. B3 repositories, tasks, queries, oracles, treatment output, ranks, and launch authorization are not reused, and B3 is not counted as a confirmatory replication.

The machine-readable preregistration is [`product_bakeoff_b4_protocol_report.json`](../../artifacts/product_bakeoff_b4_protocol/product_bakeoff_b4_protocol_report.json).

## Independent replication structure

B4 compares S0, S1, and S4 over twelve mutually disjoint panels. Every panel contains one fresh repository for each language-by-size slot, for 12 repositories per panel, and each repository contributes the four frozen task roles. The complete design therefore contains 144 repository clusters and 576 paired logical tasks. Every task receives all three arms.

The repository is the independent quality cluster. B4 deliberately does not repeat the same task and count those repetitions as additional evidence. Instead, each repository/arm receives one formal lifecycle: one cold task and three warm tasks, with the cold role exactly balanced inside every panel. This reduces the formal plan to 432 index builds, 2,160 logical groups, and 2,160 logical records while preserving the independent panels that address B3's real replication weakness.

All repositories, tasks, queries, oracles, panel assignments, cache assignments, and schedules must be authored and frozen before the first treatment observation. Every repository frame used by B2 through B3 is excluded, panels may not overlap, and authoring acceptance is arm-agnostic.

The three arms use all six treatment orders. Within every panel, each order is exactly balanced separately for cold and warm tasks and separately for every task role. This also exactly balances arm position and first-order predecessor effects on the cache-stratified execution surface.

## Analysis and decision rules

The confirmatory primary outcome is paired task-success difference. Paired task-utility net-win rate, status/target success, and context F0.5 are key secondary estimation and ranking outcomes, not extra confirmatory tests. Task utility is lexicographic—task success, harmful-evidence absence, status/target success, then context F0.5—rather than an opaque weighted score. The inference target is the mean effect over the twelve frozen panels, not an unrestricted population effect. Point estimates and ordinary 95% estimation intervals are always published. The two planned primary-outcome comparisons, S1 versus S0 and S4 versus S0, use Bonferroni control with two-sided alpha 0.025 each and a simultaneous 97.5% interval for confirmatory gates.

At least eight of twelve panel point estimates must be positive. The equal-direction null tail for eight or more positives is 0.193847, so this is explicitly a heterogeneity guard, not a second significance test. Familywise error control comes from the aggregate adjusted intervals; zero-effect panels are not counted as positive.

Every terminal result ranks all three arms before applying deployment gates. Quality rank is lexicographic by task-success rate, harmful-evidence rate, status/target success, and context F0.5. Resource rank uses warm-query geometric mean followed by peak-RSS P95. Exact ties share competition rank. The terminal publication also includes paired effects, both interval levels, panel direction counts, gate outcomes, and the four-dimensional quality/resource Pareto frontier. A failed gate cannot erase the estimates or produce an empty ranking.

S1 is the default-candidate track and S4 is the optional high-recall track. Both require a task-success point effect of at least six percentage points, a positive simultaneous 97.5% lower bound, at least eight positive panels, and a harmful-evidence risk-difference upper simultaneous bound no greater than two percentage points. S1 must keep the warm-query upper 95% ratio at or below 1.20 and peak RSS at or below 1.15; S4 uses limits of 2.10 and 1.25. These are eligibility gates, not substitutes for the published comparison, and any promotion still requires a separate fresh Phase C validation.

## Bounded storage and execution

B4 does not require all 144 repositories to remain expanded. Authoring clones one candidate at a time, materializes a content-bound compact source snapshot, then removes the clone before moving to the next candidate. Git history, dependency caches, and build outputs are not retained. Formal execution streams frozen snapshots through bounded lanes with at most one expanded repository per lane; each result is durably appended before that lane's scratch is reclaimed.

The lane count, CPU affinity, and measured working-set allowance must be qualified and frozen before treatment and must remain identical for every arm. They cannot be increased adaptively after output begins. Disk admission is derived from the measured frozen snapshots and qualified runner working set—there is no arbitrary fixed free-disk floor—and no GPU is required.

## Power and sample-size sensitivity

The deterministic Monte Carlo model evaluates the joint quality gate—significance, practical effect size, and panel-direction consistency—not significance alone. It combines seven effect sizes, repository ICC values of 0.05, 0.15, and 0.25, and mean-centered between-panel effect spreads of 0, four, and eight percentage points. Each of the 63 scenarios uses 2,000 simulations and reports a Monte Carlo interval. The assumed paired discordance is 0.50 because B3 did not publish task-level discordance. Resource and harmful-evidence gates are not power-modelled because no defensible planning distributions exist for them.

For a true mean effect of twelve percentage points, aggregate-test power ranges from 0.793 to 0.947 and joint-quality-gate power ranges from 0.777 to 0.929. Six of nine nuisance scenarios reach at least 0.80 joint-quality power, and the minimum across the preregistered moderate-nuisance subset is 0.849. The protocol therefore makes no universal 80% power claim and exposes the adverse-case sensitivity directly.

The frozen sample-size comparison shows why B4 stops at twelve panels. Under the lowest-power preregistered twelve-panel nuisance combination, estimated joint-quality power is 0.777 for twelve panels and 0.925 for eighteen panels. Eighteen panels would require 216 repositories and 3,240 records—50% more formal work. Because B4 always publishes estimates, ranks, and the Pareto frontier even when an eligibility gate misses, and because promotion still needs fresh Phase C evidence, that extra cost is not imposed solely to cover the most adverse unidentified nuisance case.

## Current boundary

Only the protocol and synthetic validation exist. Runner, scorer, publication, runtime qualification, fresh private holdout, readiness, launch authorization, and treatment execution are not yet authorized. The next action is local implementation and fault testing of those control surfaces; no compute server is needed at this checkpoint.
