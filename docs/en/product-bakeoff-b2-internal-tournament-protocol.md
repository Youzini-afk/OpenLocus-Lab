# Product Stack Bakeoff — B2 Internal Tournament Protocol Freeze

Date: 2026-07-14

Status: `product_bakeoff_b2_protocol_frozen_no_execution_no_result`

B2 is now preregistered as a bounded internal product-decision tournament. This checkpoint freezes the experimental design, task margins, run order, scoring rules, gates, promotion logic, tie handling, and privacy boundary. It has not materialized the empirical task set, run an adapter, scored a task, selected a finalist, or chosen a product default.

The executable protocol and closed public report are:

- [`product_bakeoff_b2_protocol.py`](../../eval/product_bakeoff_b2_protocol.py)
- [`product_bakeoff_b2_protocol_report.json`](../../artifacts/product_bakeoff_b2_protocol/product_bakeoff_b2_protocol_report.json)

## Parent lock

B2 is bound to the formally closed B1 mechanics bundle:

- B1 source checkpoint: `0b6f2e13b1dbc679eb1f827c28a8abd5403dcd58`
- B1 closeout checkpoint: `617b452cf24ac7294b49133caf18ee8f279e1dfe`
- B1 source bundle: `b1src_fa5b30ca188d08a491206e13acfe3faa9a5070a68be2222ba349392101b136d2`
- B1 runtime bundle used by the closing run: `b1run_01c1fdcfe6d77f3d1f8101f66a90191a1f4a620d43e39a139b686149e0b2a896`

Any change to the B1 mechanics surface requires an explicit B2 re-freeze before empirical execution.

## Experimental unit and blocking

The independent experimental unit is one logical task, so the tournament sample size is exactly 48. All six S0–S5 stacks run on every task; each task is therefore a complete comparison block. Repository, language, and size are known nuisance factors. Repetitions, cold/warm observations, context/support steps, candidates, evidence spans, and resource samples are repeated or nested measurements, not additional independent tasks.

The private empirical frame must contain 12 frozen repository snapshots:

- languages: Rust, Python, and TypeScript;
- visible-source size bands: small, medium, large, and xlarge;
- one repository for every language × size combination;
- four tasks per repository, one for each role: direct, relational, workflow, and restraint.

This produces 48 tasks. The exact public margins are:

- 16 tasks per language;
- 12 tasks per size band;
- 12 tasks per role;
- 36 one-shot tasks and 12 two-step tasks;
- 36 deterministic, 6 ambiguous multi-target, and 6 no-answer tasks;
- the nine answerable task families receive 4 tasks each; ambiguous_target and no_answer receive 6 each.

Actual repository identities, task text, queries, oracle rows, and labels stay private. The public report exposes only the frozen slot structure and its digest.

## Split-plot lifecycle and run order

Index construction is the hard-to-change factor. B2 therefore uses a repository-block split-plot lifecycle instead of rebuilding an index for every task:

- four technical repetitions;
- one fresh index build per repository × arm × repetition;
- the four repository tasks then run against that state;
- exactly one task is the cold observation and the other three are warm reuse;
- the cold role rotates so every task is cold once and warm three times.

The complete design requires 288 index builds and 1,440 validated records: 864 one-shot records plus 576 context/support records. Technical repetition improves the resource and determinism measurements but does not change independent `n=48`.

The base arm order is derived from a fixed seed. Orthogonal cyclic rotations balance every arm exactly across execution positions within size, task-role, and repetition strata. Language strata contain 64 schedule rows and therefore cannot divide perfectly by six; every arm-position count is constrained to 10–12.

## Task admission and scoring

Before any arm output exists, the private repository, task, and oracle manifests must be frozen and digested. Tasks cannot be built or edited using adapter output. Queries cannot disclose a repository identity, source path, or line number.

Deterministic tasks have exactly one positive target span; ambiguous tasks have at least two distinct positive target spans; no-answer tasks have none. Every task has at least two distinct frozen negative spans, and positive and negative spans must be disjoint and current-source valid. Two-step tasks require at least one valid support relation.

Context quality is scored on deduplicated `(canonical path, line)` atoms. Precision, recall, and F0.5 are calculated as exact rational values, converted by flooring to integer millionths, and summed over the 42 answerable tasks. Rankings use the unrounded sum, never a rounded mean. A task is marked harmful when any selected evidence line overlaps a frozen negative span.

Quality semantics must be identical across cache state and repetition before the scorer may collapse technical measurements into one task-level result.

## Product gates and promotion tracks

Every empirical result must first pass the complete-matrix, current-citation, source-immutability, determinism, resource-completeness, zero-network, scorer-isolation, and privacy gates. Missing cells are never imputed.

S0 remains the required control and fallback comparison; it is not automatically promoted. S4 and S5 are the default-candidate track. S1, S2, and S3 are optional-capability candidates.

The frozen gates include:

- at least 34/48 successful tasks and 30/36 successful one-shot tasks for candidate eligibility;
- at least 34/42 answerable target successes;
- at least 5/6 correct ambiguous decisions and 5/6 correct no-answer decisions;
- predeclared language, size, and task-role floors;
- no more than 4 answerable tasks containing harmful evidence;
- default-track arms additionally require at least 36/48 task successes and 9/12 support successes;
- quality non-inferiority and bounded warm latency, RSS, cold-index time, and persistent-state size relative to S0.

Every added component must earn inclusion against its immediate comparison stack. Literal and symbol each need a predeclared subset gain or context-quality gain. Graph needs a larger graph-subset gain and stricter cost limits. Support must improve actual support success; better context alone cannot make support “earn” inclusion. S5 must separately prove graph value over S4, so graph cannot hide inside the support stack without paying for its incremental cost.

## Ties and valid outcomes

Quality and resource ranks are separate. Quality uses exact integer counts and fixed-point sums. Equal quality vectors share competition rank, for example `1, 1, 3`. The protocol forbids forcing a unique winner.

Zero, one, or multiple finalists are valid outcomes. If multiple eligible arms fall inside the frozen decision-equivalence margins, all may advance to Phase C; there is no maximum finalist count. When at least one default-track arm passes, the shortlist is drawn from that track. Otherwise the protocol may return an optional-track shortlist or no finalist.

## Anti-adaptation and privacy boundary

After any arm output exists, B2 forbids task addition/removal/replacement, query or oracle edits, threshold/weight/order changes, arm-specific budgets, interim elimination, selective reruns, and missing-cell imputation. An infrastructure-invalid run must be discarded and restarted as a complete new run under a new private run identity.

The empirical tournament runs locally under an ignored directory. CI runs only the public protocol self-test, fault injection, report validation, drift check, and documentation validation. Public empirical output is aggregate-only: no task/repository rows, queries, candidates, paths, ranges, excerpts, hashes, labels, per-cell resources, private run paths, provider payloads, or secrets.

## Frozen identifiers

- B2 spec digest: `b2spec_3b44c386004d933d`
- B2 source bundle digest: `b2src_dfa9d0bcf855fe78968e4ecf8dd6e5a708dcc057ba580f28c1016136352d7687`
- Task-slot digest: `b2slots_a92720057d2f931e1f84c2b3d49af5a4e2efe08661d7c49e375e8835a80149ff`
- Execution-schedule digest: `b2sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3`
- Protocol-report digest: `b2protocol_d23648309bb0b4a3f3b3d39124ed4715f78fa0968a1fe6e3988f610ec1364b1c`

## Next authorized work

Implement the private repository/task admission layer and the B2 runner against this exact protocol. Before the first empirical run, freeze the private task/oracle manifests and one runtime bundle, pass self-test, fault injection, privacy, schedule, and bundle preflight, and then run the complete matrix locally. No B2 quality result exists at this checkpoint.
