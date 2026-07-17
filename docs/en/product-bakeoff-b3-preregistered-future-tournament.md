# Product Bakeoff B3 Preregistered Future Tournament

Date: 2026-07-17

Status: `product_bakeoff_b3_protocol_frozen_no_runtime_no_holdout_no_execution_no_result`

B3 is a new future experiment. It does not reopen, retry, resume, score, rank, or reinterpret B2.5. The B2.5 terminal `failed_closed_no_result` aggregate remains authoritative, and no B2.5 treatment output, private holdout, or launch authorization may be reused.

The public preregistration is [`product_bakeoff_b3_protocol_report.json`](../../artifacts/product_bakeoff_b3_protocol/product_bakeoff_b3_protocol_report.json). The executable protocol is [`product_bakeoff_b3_protocol.py`](../../eval/product_bakeoff_b3_protocol.py), and the gate/scorer-shared repeatability policy is [`product_bakeoff_b3_repeatability.py`](../../eval/product_bakeoff_b3_repeatability.py).

This phase reads no private holdout, produces no treatment output, and grants no execution authority. The rented Linux server can remain off.

## Design corrections frozen before any new output

B3 corrects four design weaknesses without changing any historical result:

1. The 48 logical tasks are no longer described as 48 independent repositories. They are nested within 12 frozen repository snapshots. A task remains the paired quality-analysis unit, while the repository is the dependence cluster and the limit on generalization.
2. The six arms use a six-sequence Williams design. This balances both arm position and first-order predecessor effects, whereas the historical cyclic rotation explicitly balanced position only.
3. The pre-score repeatability gate and scorer canonicalization call one shared implementation. A missing whole group, duplicated repetition, or wrong cache signature can no longer disappear behind a grouping pass.
4. The attempt boundary is tied to the first durable treatment observation—an accepted or rejected run record or output—not to launch-release creation alone. Audited zero-observation handoff failures may be repaired before that boundary; any failure after the boundary remains terminal and non-retryable.

## Experimental structure

| Level | Count | Interpretation |
| --- | ---: | --- |
| Frozen repository snapshots | 12 | Dependence clusters in a stratified fixed frame; not a random population sample |
| Logical tasks | 48 | Primary paired quality-analysis units, four nested in each repository |
| Treatment stacks | 6 | Every task receives every stack as a complete within-task block |
| Technical repetitions | 4 | One cold and three warm observations; not additional quality sample size |
| Frozen schedule rows | 192 | One task/repetition row before arm expansion |
| Logical score groups | 360 | 288 context groups plus 72 two-step support groups |
| Adapter observations | 1,440 | Resource and repeatability observations, not 1,440 independent experiments |

The primary claim is a product decision on this exact frozen frame. B3 does not preregister a population hypothesis test, and unadjusted task-level independence p-values are forbidden. Quality is scored once per logical task after the repeatability gate passes. Technical observations remain valid resource measurements but do not increase the quality sample size.

Exact ties remain ties. Equal quality vectors and equal resource vectors receive shared competition ranks such as `1, 1, 3`; B3 does not force a unique winner, and decision-equivalent arms may all advance.

## Williams randomization and split-plot lifecycle

The public seed is `openlocus-b3-20260717-williams6-splitplot-v1`.

For six treatments, the Williams basis contains six permutations. Across one complete set of six sequences:

- each arm appears once in each position;
- every ordered pair of distinct arms occurs once as an immediate predecessor-successor pair;
- no arm immediately precedes itself.

The 192 task/repetition rows assign these sequences with frozen language, size, role, and repetition coefficients. Validation requires:

- exact sequence, arm-position, and ordered-predecessor balance overall;
- exact balance within every repetition, size band, and task role;
- a bounded language-stratum sequence range of 10 through 12;
- one cold task and three warm tasks for every repository/repetition lifecycle;
- every task to rotate through cold exactly once and warm exactly three times.

The repository/arm/repetition index lifecycle remains a split plot. Cold/warm observations share the declared repository state and are technical repeated measurements, not independent index-build experiments.

## One repeatability definition for gate and scorer

The shared B3 policy is oracle-blind but retains all output features that can change the frozen quality score or same-arm support routing.

For a context observation it retains:

- admitted scoreable outcome class;
- candidate-set empty/nonempty state;
- pack status;
- evidence path/line union;
- target path/line union;
- target cardinality class: empty, single, or multiple;
- support-set empty/nonempty state.

For a support observation it retains the admitted scoreable class and the union keyed by relation kind, parent target id, path, and lines. A terminal support observation retains its validated terminal class, reason, and the full context score/routing projection.

Target cardinality is intentionally not discarded. A single ready target permits same-arm support execution and support credit; two duplicate target objects do not, even if their line union equals one target. Evidence and support segmentation may be normalized when their scorer atom unions are unchanged, but target single-versus-multiple routing is scientifically different.

Candidate-native scores and ordering, evidence/support duplicate segmentation, excerpts, channels, explanations, status-reason text, exact pack serialization, and diagnostic receipts are excluded from the quality projection. Their exact diagnostic hashes may be recorded privately. Diagnostic-only drift does not fail the quality gate, but it is not silently erased.

The caller must supply the complete expected observation plan. The shared core verifies all 360 groups, repetitions 1 through 4, and the exact one-cold/three-warm signatures before selecting the lowest-repetition representative for quality scoring. Resource observations are never canonicalized or required to be equal.

Source currentness, record validation and scoreability, workspace strictness, split-plot lifecycle, same-arm parent lineage, cross-arm static fairness, and zero provider-network calls remain separate mandatory gates.

## Attempt boundary and recovery policy

A private launch release by itself does not consume the only result-bearing attempt. Before the first durable treatment observation, recovery is allowed only when all of the following are audited:

- no durable treatment record or output exists, and no treatment payload was operator-visible;
- the frozen protocol, holdout, queries, and oracles are unchanged;
- all working state is discarded and recreated;
- any replacement runner receives a new public qualification and readiness checkpoint before launch.

The first durable treatment observation, including a rejected run record, crosses the attempt boundary. From that point onward there is exactly one attempt: no complete restart, machine-loss resume, selective cell retry, missing-cell imputation, or completed-cell recomputation is allowed. A post-boundary failure closes without a tournament result.

This boundary preserves anti-adaptation after evidence exists without treating a proven zero-output launcher or handoff failure as scientific data.

## Frozen phase order

The required order is:

1. public B3 protocol and repeatability freeze;
2. local B3 runner/scorer integration and synthetic fault testing;
3. public CI validation;
4. exact Linux runtime qualification on the future machine;
5. fresh private holdout authoring and freeze;
6. aggregate-only public readiness commit and green CI;
7. one private launch authorization and release;
8. one complete tournament attempt and terminal closeout.

Current readiness stops at step 1. The B3 runner and scorer are not yet integrated, the runtime is not qualified, no private holdout exists, and execution is not authorized. The next local phase should finish those implementation surfaces and their fault tests before the server is started for exact runtime qualification.

## Public validation

The protocol self-test validates 192 schedule rows, 360 complete logical groups, and 1,440 expected observations. It checks Williams position and predecessor balance, repository clustering statements, the shared gate/scorer policy, target-cardinality routing, tie handling, parent terminal locks, and the zero-output versus post-output boundary. Fault injection rejects missing groups, duplicated repetitions, scorer-relevant drift, target-cardinality drift, parent-lock drift, pseudoreplication claims, disabled carryover balance, post-output retry, privacy expansion, execution over-authorization, and digest drift.

The public protocol digest is `b3protocol_d823432f1db3dedbf51e344dee25eddf41d67fd4ce33f0f284cae5fed66a3a92`; the spec digest is `b3spec_bee900dd30fe0ce7`.

## Remaining limit

B3 is a preregistered design, not a tournament result. It changes no product default and makes no empirical arm claim. The server should stay off until the local runner/scorer integration and public synthetic qualification are complete and CI-green.
