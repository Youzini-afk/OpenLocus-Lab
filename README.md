# OpenLocus

OpenLocus is a **local-first, evidence-gated code-fact retrieval kernel** for
coding agents. It is local-first, but not local-only: exact search, symbol,
BM25, graph, read, and citation validation stay local; model/provider layers may
be used only behind explicit policy and CI opt-in gates.

The project is currently a research prototype, not a production default engine.
Its core invariant is stable:

```text
EvidenceCore = path + line range + content_sha + score + why + channels
```

Every intelligent layer — BM25, AST chunks, dense candidates, graph expansion,
LLM-derived views, context packs, provider output, QuIVer/TDB experiments, and
policy routing — must bottom out in **current-source EvidenceCore** or explicitly
abstain / request more context. Candidate is not fact.

## Current research status

Status date: **2026-06-28**.

OpenLocus is now in the **BEA v1 actionability / retrieval-action scheduling**
line. The current question is no longer “which retrieval channel is globally
strongest?”; it is:

> How do we convert high-reach, high-false-cost candidate pools into low-false-
> cost, citation-valid Evidence without weakening `EvidenceCore`?

The latest closed phase is **BEA-v1-N10CE: Span-Shape Gated Refinement Sweep**:

```text
status: span_shape_gated_refinement_sweep_complete_n10cf_authorized
self-test: 15 / 15
forbidden scan: pass
private span rows read: 213
variant count: 12
cheaper-preserves-short-anchor variants: 0
recall-improves-short-anchor variants: 2
best below-pm200 short-only variant: short_only_before75_after225 at 24 / 30, cost10 3000
next allowed phase: BEA-v1-N10CF Span-Shape Gated Refinement Audit Package
```

N1 first showed that span-only repair was rank-blocked: D1 total / pool
span-opportunity was 40, but D1 top-10 actionable was 0. N2 decomposed those 40
rank-blocked records and localized the blocker to extra-depth append/merge-order.
N3 then tested three frozen, deterministic merge-order designs without new
retrieval, selectors, rerankers, P5, or BEA-v1-A:

```text
D3 design denominator: 40

frozen P4 order:                            0 / 40
fixed interleave 2-primary/1-extra after 4: 8 / 40
early extra-depth quota 3:                 10 / 40
bounded promotion after prefix 4/3:        10 / 40

best recovery rate: 0.25 < 0.50 pass gate
```

N3 is an inconclusive/negative design result: the simple bounded merge-order
designs do not solve the N2 blocker. It does **not** authorize implementation,
P5, BEA-v1-A, selector/reranker execution, runtime/default promotion,
method-winner claims, broad retrieval expansion, downstream-value claims, or a
frozen P4 rerun.

The follow-up trace-gap audit converted the post-N3 state into explicit trace
requirements for deep research agents. Rank/pack and merge-order review already
have sanitized rows from N2/N3, but the BEA-v1 mechanism surface still needs
sanitized public exports or new labels for action-cost, support-link, same-file
redundancy, risk-penalty, and ordered-prefix stop traces before new policy
experiments.

P0-2 then refreshed the P1 actionability matrix with P0-1 trace readiness without
mutating P1 causal cell classes. The result confirms the next work is data-surface
work: scheduler/action-cost export, support-link labeling input, same-file
redundancy trace, risk-penalty trace, and ordered-prefix stop trace.

P0-3 exported the scheduler/action-cost dataset contract from committed P4L and
P0-2 artifacts. Aggregate scheduler arms and subgroup denominator buckets are now
public as sanitized rows. Full per-arm private export remains optional because
the historical P4L private JSONL was generated in a previous environment; future
private rows should live under `.openlocus/research-private/` and be supplied via
`--private-arm-outcomes-jsonl`.

P0-4 converted the `support_link_trace` gap into a scanner-validated labeling
input contract. It publishes 18 sanitized support-link design rows and six label
fields, but keeps all target/support hit states unlabeled and does not execute a
support counterfactual.

P0-5 turned the P0-4 contract into a private labeling harness. It can emit an
unlabeled JSONL template under `.openlocus/research-private/` and validate a
completed private label JSONL, while public artifacts contain only sanitized
manifests, harness rows, and summaries.

P0-6/7/8 then closed the remaining parallel trace-surface contracts for
same-file redundancy, risk-penalty removal, and ordered-prefix stop decisions.
These are scanner-validated contract exports only; no private trace rows are
populated yet.

P0-9 consolidated P0-1 through P0-8 into a single next-experiment gate. All P0
artifacts load and pass scanners, but most late surfaces are still contract-only;
the only newly allowed next action is private labeling or private trace
validation.

P1-0 validated the P0-5 private support-label harness end to end with a synthetic
private fixture under `.openlocus/research-private/`. This proves the label
validator path works, but does not create real labels and does not authorize a
support counterfactual.

P1-1 prepared the real private support-labeling queue under
`.openlocus/research-private/`. The public artifact exposes only sanitized queue
buckets and confirms the queue is ready for private labeling.

P1-2 adds a private label intake validator over the P1-1 queue. In the current
run it validates the queue contract and public/private shape join, but no real
private labels were supplied, so support counterfactual execution remains
blocked.

P1-3 fills that queue with deterministic agent-generated private proxy labels
under `.openlocus/research-private/` and validates them through P0-5/P1-2. The
labels are explicitly not human labels, not human-calibrated E/S, not support
utility evidence, and not mechanism evidence; support counterfactual execution
remains blocked.

P1-4 audits those automated labels through direct P1-2 intake and verifies their
origin metadata, but returns `no_go_p1_4_low_evidence_labels`: all 18 labels keep
target/support hit buckets unknown and conjunction ambiguous. P1-5 denominator
audit and support counterfactual execution remain unauthorized.

P1-5R checks whether existing support-label surfaces contain source/context
linkage to improve automated labels without guessing. They do not: the available
rows contain only bucket/proxy fields, so no improved labels are generated and
P1-5 remains unauthorized.

P2-0 checks whether the P4L private arm-outcome rows can be recovered from local
project-private storage or an explicitly supplied private `/tmp` JSONL and
exported through the P0-3 scheduler/action-cost contract. The committed P4L
manifest records 1,088 private rows, but the local private JSONL is absent, so
P2-0 is a No-Go and does not guess or rerun arms by default.

P2-1 extracts committed ordered-prefix / early-stop evidence into scanner-safe
public rows. It finds useful aggregate evidence across eight sources, but no
local private ordered-prefix trace, so row-level private-trace readiness remains
blocked and no stop-policy change is authorized.

P2-2 audits the combined same-file redundancy and risk-penalty trace surfaces.
Both P0-6 and P0-7 contracts are present with six rows each, but no local private
trace JSONL is available for either surface; trace counterfactuals and policy
tuning remain blocked.

P2-3 closes the current late trace route by consolidating P1-5R, P2-0, P2-1, and
P2-2. All five late surfaces remain blocked, so the only allowed next step is
P3-0 frozen upstream trace-capture harness design: schema/instrumentation
planning only, not execution, policy, or retrieval.

P3-0 designs the frozen upstream trace-capture harness for all five blocked
surfaces. It defines private schemas, public projections, instrumentation target
buckets, frozen replay requirements, and fail-closed validation gates, but it
does not execute trace capture, retrieval, reruns, counterfactuals, policy, or
runtime changes. It authorizes only P3-1 dry-run preflight as a separate phase.

P3-1 performs the static dry-run preflight for that harness. Required evaluator
anchors are checked by file existence/text only, with no imports or execution.
It authorizes only P3-2 frozen trace logger patch design; patch application,
trace capture execution, private row writes, retrieval, reruns, and runtime
behavior changes remain blocked.

P3-2 designs isolated frozen trace logger helpers, writer contracts, behavior
preservation gates, and synthetic tests for the five surfaces. It does not apply
patches or hook evaluators. It authorizes only P3-3 isolated helper patch review;
trace capture execution, private row writes, retrieval, reruns, and runtime
behavior changes remain blocked.

P3-3 adds the isolated helper module and synthetic patch-review evaluator only.
The helper functions are pure transformations for the five surfaces and the
review confirms static constraints, synthetic fixture validation, negative
privacy fixture rejection, and scanner-safe public projections. It authorizes
only P3-4 hook-in preflight design; hook application, trace capture execution,
private row writes, retrieval, reruns, and runtime behavior changes remain
blocked.

P3-4 statically designs hook-in points for the five frozen trace surfaces. It
checks prior P3 artifacts, inspects target buckets by read-only text markers, and
defines hook event contracts, helper call contracts, replay preconditions, output
boundaries, and behavior-preservation gates. It authorizes only P3-5 static
patch-plan review; hook application, hook execution, trace capture, private row
writes, retrieval, reruns, and runtime behavior changes remain blocked.

P3-5 reviews the frozen trace logger hook-in patch plan as bucketed records only.
It plans default-off logging-only hook wiring and synthetic/no-execution
validation for a future P3-6 phase, but does not apply patches, execute hooks,
capture traces, write private rows, run retrieval, rerun P4L/N1/N2, or change
runtime behavior.

P3-6 applies only default-off, logging-only hook shims to selected evaluator
files. The shims are not called by default, expose no CLI or environment
enablement, add no private-path arguments, and perform no writes. P3-6 authorizes
only P3-7 capture-execution preflight; it still does not execute trace capture,
write private rows, run retrieval, rerun P4L/N1/N2, or change runtime behavior.

P3-7 performs capture-execution preflight only. It validates static hook
readiness, the explicit enablement contract, the project-private root, the P3-8
manifest schema, and helper-only synthetic fixtures without importing target
evaluators or calling hook shims. It authorizes only P3-8 explicit capture smoke
over predeclared frozen/materialized fixtures; no retrieval, reruns, private row
writes, policy, P5, v1-A, or runtime/default promotion is authorized.

P3-8 checks for the predeclared frozen/materialized event fixture manifest and
events required for explicit capture smoke. The current workspace has no such
fixtures, so P3-8 is a No-Go before private writes: no private rows or private
manifest are created, and P3-9 manifest audit is not authorized.

P3-8F designs and preflights proxy fixture materialization after the P3-8 No-Go.
It maps all five surfaces to committed proxy/contract sources and records the
missing empirical fields, but writes no fixture files and no private trace rows.
It authorizes only P3-8G proxy fixture materialization smoke, with no trace
capture, retrieval, reruns, counterfactuals, policy, P5, v1-A, or runtime/default
promotion.

P3-8G materializes exactly two ignored project-private proxy fixture files for
the five surfaces. They are proxy fixtures only, not captured traces and not P3-8
empirical fixture files. The current P3-8 schema does not accept them, so P3-8G
authorizes only P3-8H proxy fixture compatibility preflight and still does not
authorize capture, private trace rows, retrieval, reruns, policy, P5, v1-A, or
runtime/default promotion.

P3-8H validates the private P3-8G proxy fixtures without serializing private
filenames, paths, or raw payloads publicly. The fixtures are schema-valid and the
proxy origin boundary is clean, but P3-8 empirical schema compatibility remains
false. P3-8H authorizes only P3-8I explicit proxy fixture logger smoke design;
no P3-8 code change, capture, private trace rows, retrieval, reruns, policy, P5,
v1-A, or runtime/default promotion is authorized.

P3-8I designs a separate explicit proxy fixture logger smoke evaluator. It keeps
P3-8 empirical mode unchanged, requires default-disabled explicit proxy mode, and
plans helper-only proxy fixture build/validate/sanitize with sanitized public
projection only. It authorizes only P3-8J separate evaluator implementation; no
P3-8 modification, capture, private trace rows, target evaluator calls,
retrieval, reruns, policy, P5, v1-A, or runtime/default promotion is authorized.

P3-8J implements that separate proxy smoke evaluator. It reads existing ignored
P3-8G private proxy fixtures, imports only the helper module, validates helper
build/validate/sanitize/public-projection for all five surfaces, and emits only
sanitized public projection rows. It does not modify private files or write
private trace rows, and it authorizes only P3-8K public projection audit.

P3-8K audits only those P3-8J sanitized public projections. It confirms shape
and proxy boundary validity for five surfaces while recording that the projection
is proxy-only, not empirical evidence, and not adequate for denominator or
counterfactual claims. It authorizes only P3-8L projection field adequacy and
empirical fixture requirement decision; no private reads, helper imports, capture,
private writes, retrieval, reruns, policy, P5, v1-A, or runtime/default promotion
is authorized.

P3-8L closes the proxy route for mechanism work. The proxy projections are valid
as a logger-smoke shape audit, but they are not empirical trace evidence and are
not sufficient for denominator audits, counterfactuals, or mechanism claims. The
only authorized next step is P3-8M empirical frozen event fixture acquisition
design; no capture execution or private trace writes are authorized.

P3-8M designs the empirical frozen/materialized event fixture acquisition route
for the five surfaces. It reads only the P3-8L public artifact, produces
design-only acquisition and schema records, and authorizes only P3-8N preflight.
It does not generate fixtures, execute capture, write private rows, import helper
or target evaluators, run retrieval/reruns/counterfactuals, tune policy, or
promote runtime/default behavior.

P3-8N performs the empirical fixture acquisition preflight and fails closed
because no empirical event source is declared. It reads only the P3-8M public
artifact and gitignore metadata; it performs no private inventory read and no
private reads/writes. It authorizes only P3-8O source declaration design.

P3-8O designs the future empirical event source declaration schema and validation
rules. It allows only existing materialized event logs or explicit future capture
mode plans as source modes; proxy fixtures, aggregate proxies, and contract
templates are rejected. It authorizes only P3-8P declaration intake preflight.

P3-8P performs declaration intake preflight. The default local run has no explicit
`--declaration-json`, so it returns a No-Go without broad private scanning,
private writes, fixture generation, or capture execution. P3-8Q is not authorized
until a future explicit declaration passes all intake gates.

P3-8PS audits committed public artifacts for any existing legitimate empirical
frozen/materialized event source that could support declaration authoring. It
finds none: current surfaces are proxy-only, aggregate-only, contract-only, or
blocked by missing private traces/context. No next phase is authorized until a
real empirical event source is created or supplied.

N4 returns to the public N1/N2/N3/P4L rank-blocker evidence after the P3 trace
source route stopped. It finds 40 scanner-safe rank-blocked cases with fixed-pool
deeper evidence and non-inconclusive merge/order signal, so it authorizes only N5
fixed-pool rank-order experiment preflight using existing pools and no new
retrieval.

N5 completes that preflight without execution. It freezes the 40 N4 sanitized
rank-blocker cases, declares exactly four fixed-pool order-transform arms
(`baseline_n2_order`, `extra_depth_promote_before_primary_prefix_4`,
`bounded_interleave_primary2_extra1`, and
`late_extra_depth_demote_after_primary_prefix_8`), and defines N6 metrics and pass
gates. N5 authorizes only BEA-v1-N6 execution of those predeclared arms over the
fixed public N2/N3 pool fields; it still forbids new retrieval, P4L/N1/N2/N3
reruns, selector/reranker execution, private reads, policy/runtime changes,
counterfactuals, method-winner claims, and downstream-value claims.

N6 attempts the authorized fixed-pool rank-order experiment using only committed
public N5/N4/N2/N3/P4L artifacts, but correctly stops as No-Go because exact
per-case public outcome fields for the four N5/N6 arms are unavailable. N3 has
analogous design-arm rows, but their names and semantics are not exact N6 arms,
so N6 does not map them as results and does not infer from aggregate counts.

N6F closes the N6 public-field gap as a design-only phase. It defines the required
bucket-only public schema for future arm outcome materialization: 160 rows (40
fixed cases × four exact N6 arms) with anonymous case/arm ids, exact-arm semantics
boolean, no candidate-pool/new-retrieval/selector-reranker booleans, recovery
buckets, rank-shift bucket, regression bucket, hard-cap bucket, and materialized
boolean. It authorizes only N6G read-only public source discovery, not generation
or an N6 rerun.

N6G performs that read-only public source discovery and closes as No-Go. N3 has
160 per-case analogue rows, but its arm names and semantics are not exact N6
arms; N6 has empty per-case arm outcomes; N6F is design-only; N5 is contract-only;
and N4/N2 are per-case rather than exact per-case-per-arm outcome sources. Covered
exact public rows remain 0/160, so the fixed-pool route is closed until an exact
public 160-row arm-outcome source exists.

N6XR then attempts an explicit bounded candidate-pool recapture smoke but stops
before execution. Public N4 case ids are positional over N2 sanitized rows, with
no raw-record join key, candidate pools, raw ranks, or order fields available in
committed public artifacts. The smallest replay route requires full P4L
reconstruction over 272 records with network, repository clones, OpenLocus
baseline retrieval, and full rerun scope, which is outside the bounded 40-case
N6XR authorization. The result is a data-surface No-Go, not a method failure.

N6X-FR introduces the first explicitly broader full-frozen reconstruction capture
boundary, but the default local checkpoint is preflight-only. It verifies public
N4/N5/N6/N6F/N6G/N6XR/P4L/N2 artifacts and local prerequisite buckets without
running network, clone, OpenLocus binary execution, or replay. The default run is
No-Go because the release binary and required private reconstruction inputs are
not locally available under scanner-safe preflight.

N6XFR-B checks whether those local prerequisites can be recovered. The Rust
workspace, lockfile, package, binary declaration, and build-command bucket are
present, but the local cargo registry cache is unavailable, so building would
require an unapproved crates.io/static.crates.io dependency fetch. N6XFR-B does
not run cargo build and still records FD1/P4L/N-series private reconstruction
inputs as unavailable.

N6XFR-C applies the newly authorized narrow build-recovery scope and runs exactly
the release build command for `openlocus-cli`. The build succeeds and creates the
release binary bucket, but FD1/P4L/N-series private reconstruction inputs are
still unavailable, so N6X-FR canary/full capture remains unauthorized.

N6XFR-D performs the final read-only metadata inventory of the repo
research-private bucket. It finds zero FD1, P4L, N-series candidate-pool, or N6
arm-outcome reconstruction input candidates, reads no private content, publishes
no private paths or names, and closes the full-frozen reconstruction route under
current local authorization.

The final BEA-v1 mechanism route synthesis closes the current autonomous route.
It summarizes the positive empirical anchors (P4L, N1, N2, N3, N4), records that
the support-label, trace-surface, fixed-pool rank-order, and full-frozen
reconstruction routes are all blocked on missing real empirical/private inputs,
and authorizes no autonomous next experiment from current artifacts.

N6XFR-E then reopens the fixed-pool rank-order route under a new explicit local
recovery directive using recovered private N2 rank-pack rows. It computes all 160
N6F-schema public arm outcomes for the four N5 fixed-pool transforms, but the
best arm recovers 25/40 into top-10 versus the N5 pass threshold of 16/40,
so the recovered fixed-pool rank-order experiment passes its predeclared gate.

N7 audits the N6XFR-E public artifact without reading private rows or recomputing
outcomes. It confirms the 40-case / 4-arm / 160-row public result, best arm
`extra_depth_promote_before_primary_prefix_4`, top-10 recovery 25/40, 0
regressions, fixed-pool arm semantics, and N6F public schema match. It authorizes
only N8 independent recompute over the same private rows and same four arms.

N8 independently reimplements the same four fixed-pool transforms and reads only
the single scoped recovered private N2 row bucket. It matches N6XFR-E per-arm
top-10/top-20/regression counts exactly and reproduces the threshold pass:
`extra_depth_promote_before_primary_prefix_4` reaches 25/40 top-10 and 34/40
top-20 with 0 regressions. It authorizes only N9 replication package.

N9 packages the public replication chain and claim boundary. It reads public
artifacts only, confirms N6XFR-E -> N7 -> N8 consistency, records that recompute
still requires the same uncommitted recovered N2 rank-pack rows, and authorizes
only N10 broader frozen denominator validation preflight.

N10 preflights broader frozen-denominator validation without computing new arm
outcomes. The recovered 40-row rank pack is exact but not broader; P4L/N1 provide
broader context buckets but not N2-equivalent rank-pack rows under the current
public/metadata-only boundary. N10 therefore closes as No-Go until broader
N2-equivalent rank-pack rows exist.

N10R then checks whether the existing N2 builder can target additional rows
without a full P4L rerun. Scoped private schema counts are available, and the N2
row builder helper exists, but the current N2 CLI is monolithic full
locked-denominator reconstruction with no targeted denominator filter. N10R does
not materialize rows and closes as No-Go until a targeted builder or explicit full
rerun is authorized.

N10T explicitly changes surface: it is a proxy/span-surface validation, not an
N2-equivalent broader-denominator validation. It reads only the scoped N1 span
rows, preserves the fixed pool, and reorders the `p4_evidence` list by N5-style
rank buckets. The proxy result passes its threshold: extra-depth promotion before
the primary prefix reaches 34/213 top-10 file reach versus 0 baseline, with 0
regressions. It authorizes only N10U proxy result audit.

N10U audits N10T using public artifacts only. It confirms the proxy boundary
(`n1_span_p4_evidence_order_proxy`, not N2-equivalent validation), the exact
213-row denominator, reachable-in-pool count 52, best arm, top10/top20 34/44,
delta 34, regressions 0, and threshold pass. It authorizes only N10V independent
recompute over the same private span rows; broad private reads remain forbidden.

N10V independently recomputes the N10T proxy result over the same scoped private
span rows and same four arms without importing or calling N10T code. It matches
N10T exactly: eligible denominator 213, reachable-in-pool 52, best arm
`span_extra_depth_promote_before_primary_prefix_4`, top10/top20 34/44, delta 34,
regressions 0, and threshold pass. It authorizes only N10W public replication
package.

N10W packages the N10T/N10U/N10V proxy chain using public artifacts only. It
confirms stable metrics across validation, audit, and independent recompute, and
records the claim boundary: proxy/span-surface only, not N2-equivalent, not
runtime/default policy, not a method winner, and not downstream-value evidence.
It authorizes only N10X stronger-validation preflight with no execution.

N10X performs that stronger validation directly at span level using the scoped
recovered N1 span rows. The file-level proxy gain remains visible, but the stricter
span-overlap top-10 metric reaches only 9 cases against a threshold of 11, so the
phase completes below threshold. It authorizes only N10Y public result audit.

N10Y audits N10X using public artifacts only. It confirms the below-threshold
span-level result is complete and not an infrastructure failure: file-level gain
does not pass the stricter span-level utility gate. It authorizes only N10Z
failure-decomposition preflight with no execution.

N10Z directly decomposes the span-level failure for the N10X best arm. It shows
the 25-case gap is entirely same-file/no-overlap: 17 spans before the gold window
and 8 after it, with no malformed schema or record-bug bucket. This authorizes
only N10AA span-window repair preflight; it does not authorize repair execution.

N10AA designs the fixed span-window repair smoke without executing it. The primary
N10AB variant is a gold-free symmetric +/-50-line expansion on top-10 evidence
spans after the N10T best arm, with optional +/-20 and +/-100 sensitivity variants.
It authorizes only N10AB fixed span-window repair smoke over the same private span
rows; N10AA itself does not authorize private reads or repair execution.

N10AB executes that fixed-window smoke on the scoped recovered N1 span rows. The
primary +/-50 variant raises top-10 span overlap from 9 to 19, passes the threshold
of 11, and loses zero original span hits. This remains a span-surface repair smoke,
not runtime/default policy or downstream-value evidence, and authorizes only N10AC
public repair-smoke audit.

N10AC audits the N10AB public repair-smoke result without private reads or
recompute. It confirms pm50 top-10/top-20 expanded span overlap 19/23, pm20
15/19, pm100 21/25, baseline 9/10, delta +10, threshold 11, zero original span-hit
loss, unchanged candidate pool, no candidate add/remove, and gold-only evaluation.
It authorizes only N10AD independent recompute over the same private span rows.

N10AD independently recomputes the fixed-window repair smoke over the same scoped
private span rows without importing or calling N10AB code. It matches N10AB exactly:
baseline 9/10, pm20 15/19, pm50 19/23, pm100 21/25, pm50 delta +10, and zero
lost original span hits. It authorizes only N10AE public replication package.

N10AE packages the public N10AB/N10AC/N10AD replication chain. It confirms N10AB
pass, N10AC audit completion, N10AD independent recompute match, pm50 19/23 with
delta +10 over baseline 9/10, threshold 11, zero lost original hits, and unchanged
candidate pool. It authorizes only N10AF next-step selection / stronger-validation
preflight.

N10AF directly validates robustness across predeclared subgroups for the fixed pm50
repair. It reproduces the global N10AE result (baseline 9, pm50 19, delta +10,
lost hits 0) and shows positive delta in seven predeclared subgroup buckets with no
negative delta for baseline-span-hit cases. It authorizes only N10AG public
claim-boundary audit/package.

N10AG locks the public claim boundary: the allowed claim is only a scoped N1
span-surface fixed-pool pm50 span-window repair smoke/robustness pass. It packages
N10AB pass, N10AC audit, N10AD independent match, N10AE replication, and N10AF
robustness. It authorizes only N10AH default-off implementation feasibility
preflight, not actual runtime implementation or default promotion.

N10AH adds the isolated pure helper `eval/bea_v1_span_window_repair_helpers.py`
and a synthetic implementation smoke. The helper expands line windows and evidence
record line bounds without filesystem IO, private reads, path/content/gold
requirements, hook-in, or runtime/default config changes. It authorizes only N10AI
default-off integration preflight.

N10AI statically preflights integration and recommends a new
`future_eval_only_span_projection_adapter` rather than modifying N10AB, N10X, N10T,
or runtime paths. The recommended target is eval-only, default-off, not an existing
runtime path, and low behavior-risk. It authorizes only N10AJ default-off eval-only
adapter patch.

N10AJ adds the new eval-only adapter `eval/bea_v1_span_window_projection_adapter.py`.
The adapter is default-off, pure, imports the N10AH helper, preserves record count
and order, returns unchanged non-mutating copies when disabled, and expands only
`start_line`/`end_line` when explicitly enabled. It uses synthetic fixtures only
and authorizes only N10AK public/synthetic fixture audit.

N10AK packages the public/synthetic adapter chain. It confirms N10AJ adapter patch,
N10AI target selection, and N10AH helper validity without private reads or empirical
metric recompute. It authorizes only N10AL scoped eval-only adapter integration
smoke.

N10AL performs the scoped eval-only integration smoke using the N10AJ adapter over
the same recovered N1 span rows. It reproduces the N10AB/N10AD pm50 aggregates:
baseline top10/top20 span overlap 9/10, pm50 top10/top20 19/23, delta +10, and
0 original span-hit losses, with candidate pool/order unchanged. It authorizes
only N10AM public result audit/package.

N10AM packages the N10AL result using public artifacts only. It confirms the
eval-only adapter reproduces the scoped N1 pm50 aggregate and keeps candidate
pool/order unchanged, without private reads or empirical recompute. It authorizes
only N10AN default-off existing-evaluator hook feasibility preflight.

N10AN performs a public/static hook feasibility preflight. It statically inspects
the adapter/helper and candidate N10AB/N10X/N10T evaluator surfaces without
importing or executing them. Because direct hook-in would mutate existing
validated evaluators, it selects `new_adapter_enabled_variant_evaluator` for
N10AO and authorizes only a new default-off eval-only variant evaluator patch.

N10AO adds that new eval-only variant evaluator without modifying existing
validated evaluators or runtime code. The generated artifact used explicit scoped
enablement to read the same recovered N1 span rows and reproduced the pm50
aggregate: baseline top10/top20 9/10, pm50 top10/top20 19/23, delta +10, and 0
original span-hit losses, with candidate pool/order unchanged. Default mode still
performs no private read or metric recompute.

N10AP packages the N10AO result using public artifacts only. It confirms the new
eval-only variant evaluator reproduces the scoped N1 pm50 aggregate under
explicit enablement, keeps default/private-read-by-default disabled, and performs
no private read or recompute in the audit package. It authorizes only N10AQ
heldout/external validation source-discovery preflight.

N10AQ performs bounded local source discovery and schema sniffing for a heldout or
external span-surface row source. It finds no eligible heldout source: the only
candidate with required span-surface shape is the existing N10 source or not
distinguishable from it, and other candidates are schema-incomplete or too small.
N10AQ therefore does not authorize N10AR validation.

N10AQ-R checks whether a heldout span-surface source can be acquired by a bounded
local command/source or frozen replay without broad retrieval/rerun. It finds no
bounded acquisition path: no distinct heldout denominator is declared, no expected
row count >=50 is available, and recovered N1/P4L/N2 surfaces are same-source,
consumer-only, or require broader replay. N10AR remains unauthorized.

N10AS is a same-source exploratory sweep over 15 fixed span-window variants on the
existing N1 span-surface proxy, using only the known N10T best order. It reads the
same 213 scoped private span rows and keeps candidate pool/order fixed. The
frontier has clear tiers: `pm30` is the low-cost point (top10/top20 18/22),
`before25_after75` and `pm75` are balanced points (20/24 and 21/25), and
`pm200` is the max-recall point (25/30) with very-high cost proxy. This is not
heldout, not N2-equivalent, not runtime/default, and not a method/downstream
claim.

N10AT packages the N10AS exploratory sweep as a public-only audit. It confirms the
frontier tiers (`pm30` 18/22 low-cost, `before25_after75` 20/24 balanced, `pm75`
21/25 balanced, and `pm200` 25/30 max-recall) without private reads or recompute,
and authorizes only N10AU independent recompute of the same fixed 15-variant grid.

N10AU independently recomputes the full 15-variant grid over the same scoped N1
span rows without importing or calling the N10AS evaluator. All variant aggregates
and frontier tiers match N10AS/N10AT exactly. It remains same-source exploratory
N1 proxy evidence only and authorizes only N10AV public replication/package.

N10AV consolidates N10AS/N10AT/N10AU into a public replication package. It records
the same frontier tiers, performs no private reads or recompute, and lists only
bounded follow-up options: cost-sensitive mechanism decomposition, default-off
adapter variants over selected frontier points, or broader/heldout replay only if
new source authorization/data exists. It authorizes only N10AW follow-up selection
audit, not execution.

N10AW performs the authorized cost-sensitive mechanism decomposition over the
locked frontier tiers. The cumulative top-10 span hits are baseline 9, pm30 18,
before25_after75 20, pm75 21, and pm200 25, with no lost previous hits. Newly
recovered cases are bucketed as before/after gold-window gaps: pm30 adds 8 before
and 1 after, before25_after75 adds 2 before, pm75 adds 1 after, and pm200 adds 3
before and 1 after. The max-recall pm200 gains are wider recovery of the same
before/after miss pattern, not a qualitatively different late-rank mechanism.

N10AX packages that frontier and mechanism boundary publicly without private reads
or recompute. It locks the allowed claim to scoped same-source N1 span-surface
proxy cost-sensitive evidence: pm200 is a very-high-cost max-recall point, and its
extra gains remain before/after gold-window gap recovery. It authorizes only N10AY
cost-aware adapter frontier smoke over the same scoped rows and adapter/helper
imports.

N10AY executes that cost-aware adapter frontier smoke over the same scoped N1 rows.
Using the default-off eval-only adapter path and no existing evaluator/runtime
hook-in, it reproduces the locked frontier aggregates: pm30 18/22,
before25_after75 20/24, pm75 21/25, and pm200 25/30, with candidate pool/order
unchanged and zero lost original hits. It authorizes only N10AZ public audit/package.

N10AZ audits and packages the N10AY adapter frontier smoke publicly. It confirms
the adapter/helper path, no existing evaluator import/call/hook-in, no
runtime/default hook, row-count provenance from N10AY, and the locked frontier
metrics. It authorizes only N10BA cost-aware span-window selection rule smoke over
the same scoped rows, using predeclared operating points only.

N10BA evaluates those predeclared named operating points directly: `low_cost=pm30`
at 18/22, `balanced=before25_after75` at 20/24, and `max_recall=pm200` at 25/30.
It uses no new window sizes, no adaptive per-case selection, no runtime/default
behavior, and no candidate pool/order changes. It authorizes only N10BB public
audit/package.

N10BB packages N10BA publicly without private reads or recompute. It confirms the
three named operating points, their deltas versus baseline, zero lost previous
hits, unchanged candidate pool/order, adapter/helper-only path, no existing
evaluator hook-in, and no runtime/default hook. It authorizes only N10BC
operating-point tradeoff decomposition over the same scoped rows.

N10BC decomposes the tradeoff across baseline, low_cost, balanced, and max_recall
on the same scoped rows. It confirms marginal top-10 gains of +9, +2, and +5 for
low_cost, balanced, and max_recall respectively, with lost previous hits 0 at all
steps. The marginal max_recall gains are still before/after gold-window gap
recoveries, not a qualitatively new mechanism. It authorizes only N10BD public
tradeoff package.

N10BD packages the N10BC tradeoff publicly without private reads or recompute. It
locks the baseline/low_cost/balanced/max_recall metrics, zero lost previous hits,
unchanged candidate pool/order, and same before/after gap mechanism. It authorizes
only N10BE cost-aware operating-point decision smoke with budget buckets mapping
to the three named operating points; this remains non-runtime and non-default.

N10BE evaluates the budget-bucket decision smoke directly over the same scoped
rows: strict_budget selects low_cost/pm30 at 18/22 with cost 600, moderate_budget
selects balanced/before25_after75 at 20/24 with cost 1000, and recall_budget
selects max_recall/pm200 at 25/30 with cost 4000. It is a research decision smoke
only, not a runtime/default recommendation, and authorizes only N10BF public audit
package.

N10BF packages the N10BE budget decisions publicly without private reads or
recompute. It confirms strict/moderate/recall mappings and keeps the boundary as a
research decision only. It authorizes only N10BG comparison of those decisions
against the original fixed pm50 comparator over the same scoped rows.

N10BG compares the three budget-conditioned decisions against fixed pm50: pm30 is
slightly worse but cheaper, `before25_after75` dominates pm50 at equal cost, and
pm200 yields higher recall at much higher cost. N10BH packages those comparator
facts publicly without private reads or recompute and authorizes only N10BI
direction-mechanism decomposition of pm50 vs `before25_after75`.

N10BI decomposes pm50 vs `before25_after75` on the same scoped rows. It confirms
the asymmetric point gains one top-10 and one top-20 span hit at the same cost,
loses zero pm50 top-10 hits, and the new top-10 gain is a before-gold gap bucket.
Gold/miss direction is not used to choose per-record windows. It authorizes only
N10BJ public asymmetry mechanism package.

N10BJ packages the N10BI asymmetry mechanism publicly without private reads or
recompute. It locks pm50 `19/23`, `before25_after75` `20/24`, same cost `1000`,
net `+1/+1`, gained bucket `before_gold_gap=1`, and all lost buckets `0`. It
authorizes only N10BK neighboring asymmetry micro-sweep at the same cost proxy.

N10BK runs the same-cost direction-sensitivity micro-sweep over five predeclared
total-cost-100 variants. `before25_after75` remains the best point at 20/24;
pm50 is 19/23; before-heavy variants are weaker; the trend is nonmonotonic. It
authorizes only N10BL public direction-sensitivity package.

N10BL packages the N10BK direction-sensitivity result publicly without private
reads or recompute. It locks the same-cost five-point sweep, winner
`before25_after75`, after-heavy winner bucket, and nonmonotonic trend. It
authorizes only N10BM after-heavy local asymmetry refinement sweep at fixed total
cost 100.

N10BM runs the authorized after-heavy local refinement sweep over seven
predeclared fixed-cost-100 variants. `before25_after75` remains on the local
optimum plateau: `before20_after80` through `before40_after60` all score 20/24,
while `before10_after90` and `before15_after85` score 20/23. No prior hits are
lost relative to before25_after75 or pm50 in top-10. It authorizes only N10BN
public local-refinement package.

N10BN packages the N10BM local-refinement result publicly without private reads or
recompute. It locks the top10-primary/top20-tiebreak winner rule and the plateau
from `before20_after80` through `before40_after60`, concluding that
`before25_after75` is a plateau member rather than a unique magic value. It
authorizes only N10BO plateau mechanism decomposition.

N10BO decomposes the N10BM plateau directly over the same scoped N1 rows. All five
plateau variants recover the same top10/top20 sets (common = union = 20/24), with
zero case swaps and zero lost pm50 top10 hits. The common top10 direction buckets
are 10 before-gold gaps, 1 after-gold gap, 9 already-overlap, and 0 other. It
authorizes only N10BP public plateau mechanism package.

N10BP packages the N10BO plateau mechanism publicly without private reads or
recompute. It locks the stable plateau facts (all five variants at 20/24,
common=union, unique cases=0, lost pm50=0) and authorizes only N10BQ plateau
cost-minimization sweep across the stable ratio family and four fixed total costs.

N10BQ runs the authorized plateau cost-minimization sweep over 20 predeclared
variants: the five stable plateau ratios across total costs 60, 80, 100, and 120.
Cost 60 does not preserve the plateau (best 19/23); cost 80 preserves it with one
variant (`cost80_before25_after75`, 20/24); costs 100 and 120 preserve it for all
five ratios. It authorizes only N10BR public cost-minimization package.

N10BR packages the N10BQ cost-minimization result publicly without private reads
or recompute. It locks the 20-variant grid, the cost summary, and the minimum
cost preserving the plateau: `80`, with chosen research operating point
`cost80_before25_after75`. This is not a runtime/default recommendation or a
method-winner claim. It authorizes only N10BS boundary-cost refinement over the
fixed 25/75 ratio.

N10BS runs the authorized fixed-ratio boundary-cost refinement over seven costs
(`65`, `70`, `75`, `80`, `85`, `90`, `95`) at ratio `25/75`. Costs 65/70/75 fail
to preserve the plateau, while costs 80/85/90/95 preserve it at 20/24 with no
lost plateau core. The minimum preserving cost remains 80 and the boundary margin
from the first failing value below it is 5. It authorizes only N10BT public
boundary-cost package.

N10BT packages the N10BS boundary-cost result publicly without private reads or
recompute. It locks fixed 25/75 costs 65/70/75/80/85/90/95, the minimum preserving
cost 80, first failing cost 75, margin 5, and chosen research point
`cost80_before25_after75`. It authorizes only N10BU boundary-case mechanism
decomposition of cost75 vs cost80.

N10BU decomposes the one plateau-core case that cost75 misses but cost80 recovers.
The file hit remains top10 at both costs, and the recovered span is bucketed as a
near `before_gold_gap` just outside the 75-cost window. This explains the observed
cost boundary without publishing paths, lines, spans, snippets, gold, candidates,
or exact ranks. It authorizes only N10BV public boundary-case mechanism package.

N10BV packages the N10BU one-case mechanism publicly without private reads or
recompute. It locks cost75/cost80 comparison counts, the single transition case,
and the near before-gold boundary mechanism. It authorizes only N10BW adapter
operating-point smoke for `cost80_before25_after75` through the default-off
eval-only adapter path.

N10BW uses the default-off eval-only adapter/helper path to reproduce the selected
`cost80_before25_after75` operating point (before=20, after=60). The adapter smoke
matches the N10BS/N10BT/N10BU aggregate expectation: top10/top20 20/24, lost
plateau core 0, file-hit top10 count 34, and candidate pool/order unchanged. It
does not hook existing evaluators or runtime/default behavior, and authorizes only
N10BX public adapter operating-point package.

N10BX packages the N10BW adapter operating-point smoke publicly without private
reads or recompute. It locks the default-off adapter path, cost80 before/after
20/60 counts, top10/top20 20/24, lost plateau core 0, file-hit top10 count 34,
and N10BS/N10BT/N10BU aggregate match. It authorizes only same-source exploratory
N10BY optimization over scoped N1 rows.

N10BY tests 12 predeclared same-source cost-efficient span-window policies over
the same scoped rows. None beat the cost80 anchor under the declared success
rules: lower-cost fixed variants and rank-conditioned policies lose at least one
anchor top10 hit or reduce top20, while top20-only matches 20/24 without lowering
top10 cost. It authorizes only N10BZ public audit/package.

N10BZ packages the N10BY sweep publicly without private reads or recompute. It
locks the negative finding that no tested fixed-window cost-efficient policy
improves beyond the cost80 anchor on the same-source N1 rows. This is useful
negative research, not a stop condition; it authorizes only N10CA next mechanism
search outside the fixed-window family.

N10CA tests a same-file span cluster bridge mechanism outside the fixed-window
family. Across nine predeclared top10/top20 bridge/no-bridge variants, the best
result is 15/19, all variants lose five cost80 anchor top10 hits, and no
cluster-bridge variant improves the cost80 or pm200 anchors. It authorizes only
N10CB public audit/package.

N10CB packages the N10CA negative result publicly without private reads or
recompute. It confirms the same-file cluster/bridge family underperforms the
local-window anchor and that the current positive signal remains local
single-candidate boundary expansion rather than multi-candidate bridging. It
authorizes only N10CC next mechanism search outside both fixed-window and
cluster-bridge families.

N10CC tests observable span-shape gated expansion outside the fixed-window and
cluster-bridge families. Using only original span-length and candidate-position
buckets, it finds four recall-improving same-source variants but no
cost-efficient anchor-preserving variant: `short_only_before50_after150` and
`short_medium_before50_after150` reach 22/27 at top10 cost 2000, while the pm200
anchor remains 25/30. It authorizes only N10CD public audit/package.

N10CD packages the N10CC positive same-source result publicly without private
reads or recompute. It confirms the policy-input boundary and locks the signal:
large expansion gated by observable short span shape improves over cost80 at
lower top10 cost than pm200 all-spans. It authorizes only N10CE span-shape
refinement on the same scoped rows with fixed/predeclared variants.

N10CE refines that short-span gated signal with 12 fixed variants. It finds no
cheaper variant preserving the 22/27 short50/150 anchor, but it identifies a
same-source recall ladder: short-only 60/180 reaches 23/27 at cost10 2400 and
short-only 75/225 reaches 24/30 at cost10 3000, still below pm200 all-spans
cost10 4000. It authorizes only N10CF public audit/package.

N10 heldout validation is therefore closed for the current local state. Further
N10AR-style validation requires one of three concrete inputs before any new
execution: (1) supplied heldout span-surface rows with ordered evidence and gold
line ranges for at least 50 rows; (2) an explicitly scoped frozen replay command
with a declared denominator distinct from the N10 source; or (3) explicit
authorization for broader benchmark replay/retrieval. Without one of those, do
not continue autonomous heldout discovery/preflight phases from the same local
artifacts.

Provenance note: N2 remains the source decomposition (`28272769423`, result
checkpoint `ce47caf`); N3 is the downstream design simulation over that closed N2
D2 denominator.

High-level guardrail status:

```text
promotion_ready=false
default_should_change=false
evidencecore_semantics_changed=false
runtime_clean_general_algorithm_claimed=false
downstream_agent_value_proven=false
method_winner_claimed=false
benchmark_performance_claimed=false
bea_v1_a_authorized=false
p5_selector_reranker_authorized=false
broad_retrieval_expansion_authorized=false
ood_temporal_supported=false
quiver_systems_supported=false
```

See the current report index:

- [`docs/current-research-conclusions.md`](docs/current-research-conclusions.md)
- [`docs/en/current-research-conclusions.md`](docs/en/current-research-conclusions.md)
- [`docs/zh/current-research-conclusions.md`](docs/zh/current-research-conclusions.md)

## BEA v1 snapshot

### What is established

- **BEA v0.3 remains mixed, not a winner.** BEA-4 scaled frozen v0.3 to
  120 successful records, and BEA-5 ended as a strict fixed-protocol No-Go /
  near-miss at 119/120.
- **Failure decomposition changed the direction.** BEA-FD1 decomposed BEA-4/5
  failures; FD2-A and FD2-A1 showed that directly weighting aggregate FD1 loss
  let non-actionable latency dominate candidate selection.
- **Selector-only BEA-v1-A is under-justified.** BEA-v1-P1 found the
  file-selector lower-bound recoverability for `gold_file_absent` was only
  1/119.
- **Retrieval-action scheduling is the viable BEA v1 lever so far.** P2/P3/P4
  showed candidate availability can improve when retrieval expansion is
  constrained and latency is handled at the action-scheduler layer, not inside
  candidate relevance scoring.
- **The disjoint denominator is now locked; N1 is rank-blocked; N2 localizes the blocker; N3 simple designs are insufficient.** P4H/P4I showed the supported
  Python frame only had 73/80 file-miss records; P4J found a 333-record
  cross-source upper-bound reservoir; P4K resolved exact overlap and locked a
  272-record non-Python denominator; P4L validated the frozen P4 scheduler on
  that locked denominator; N1 then found D1_total=40 but D1_top10_actionable=0,
  N2 classified all 40 as extra-depth append/merge-order blocked, and N3 tested
  three bounded merge-order designs but only recovered 8/40 or 10/40.

### What remains unresolved

- N3 did not find a passing merge-order design, and P0-1/P0-2 now show the next
  empirical question must first expose the missing trace surface: sanitized
  scheduler/action-cost rows, support-link labels, same-file redundancy trace,
  risk-penalty trace, and ordered-prefix stop trace.
- P0-3 has closed the aggregate scheduler/action-cost export contract, but not a
  full private arm-row export. The remaining practical fork is either to recover
  or rerun P4L private arm rows under `.openlocus/research-private/`, or move to
  support-link input design for the `blocked_missing_label` cells.
- P0-4 has closed the support-link input-design contract. The next support phase
  must either create scanner-validated private labels under this contract or stay
  at design level; it still cannot claim support marginal utility.
- P0-5 has closed the private labeling harness contract, and P1-3 now supplies
  scanner-validated agent-generated private proxy labels. These are not human
  labels or mechanism evidence, so support counterfactual execution remains
  unauthorized.
- P0-6/7/8 have closed the remaining trace-surface contracts, but they are not
  populated private trace exports. Policy tuning and counterfactual execution
  remain unauthorized until project-local private rows validate cleanly.
- P0-9 prevents contract-pass artifacts from being read as populated mechanism
  evidence. Support counterfactuals, trace counterfactuals, policy tuning, P5,
  and BEA-v1-A all remain blocked.
- P1-0 authorizes private support labeling using the validated schema and
  harness. P1-3 completed an automated/agent-generated fill, but support
  counterfactual execution remains blocked because these are queue/design-field
  proxy labels with unknown target/support hit buckets. P1-4 confirms they are
  intake-valid but too low-evidence for a P1-5 denominator audit. No
  human-calibrated claim is made or required.
- P1-1 authorizes labeling against the generated project-private queue. It still
  does not authorize support counterfactual execution or support marginal-utility
  claims.
- P1-3 authorizes only automated private support-label fill and P1-2 intake
  validation. It does not authorize support counterfactual execution, support
  marginal-utility claims, mechanism evidence claims, P5, or BEA-v1-A.
- P1-4 authorizes only automated-label reliability auditing. It does not
  authorize P1-5, support counterfactual execution, support marginal-utility
  claims, mechanism evidence claims, P5, or BEA-v1-A.
- P1-5R authorizes only feasibility auditing for improved automated support
  labels. It found no reconstructable private source context and does not
  generate guessed labels or authorize P1-5/support counterfactuals.
- P2-0 authorizes only scheduler private arm-row recovery and sanitized export.
  It found no local P4L private arm rows, does not tune policy, does not run broad
  network replay by default, and does not authorize implementation/runtime
  promotion.
- P2-1 authorizes only ordered-prefix stop evidence surface extraction. It is
  aggregate-only locally and does not authorize stop-policy changes,
  counterfactual execution, implementation, or runtime promotion.
- P2-2 authorizes only redundancy/risk trace availability auditing. It found no
  local private trace rows and does not authorize trace counterfactuals, policy
  tuning, implementation, or runtime promotion.
- P2-3 authorizes only late trace surface closure and the next-experiment decision.
  It allows only P3-0 frozen upstream trace-capture harness design; all execution,
  counterfactual, policy, implementation, runtime, P5, and v1-A flags remain false.
- P3-0 authorizes only frozen upstream trace-capture harness schema and
  instrumentation planning. It allows P3-1 dry-run preflight only; actual trace
  capture, retrieval execution, reruns, counterfactuals, policy tuning,
  implementation, runtime promotion, P5, and v1-A remain unauthorized.
- P3-1 authorizes only static dry-run preflight and the next P3-2 logging-only
  patch design phase. It does not authorize patch application, trace capture
  execution, private trace row writes, retrieval, reruns, policy changes,
  implementation, runtime promotion, P5, or v1-A.
- P3-2 authorizes only isolated frozen trace logger helper patch review and
  synthetic tests in a separate P3-3 phase. It does not authorize evaluator
  hook-in, trace capture execution, private row writes, retrieval, reruns, policy
  changes, runtime promotion, P5, or v1-A.
- P3-3 authorizes only P3-4 frozen trace logger hook-in preflight design. It does
  not authorize hook application, trace capture execution, private row writes,
  retrieval, reruns, policy changes, runtime promotion, P5, or v1-A.
- P3-4 authorizes only P3-5 frozen trace logger hook-in patch-plan review. It
  does not authorize patch application, hook execution, trace capture execution,
  private row writes, retrieval, reruns, policy changes, runtime promotion, P5,
  or v1-A.
- P3-5 authorizes only P3-6 default-off logging-only hook wiring with
  synthetic/no-execution validation. It does not authorize trace capture, private
  row writes, retrieval, P4L/N1/N2 reruns, policy changes, runtime promotion, P5,
  or v1-A.
- P3-6 authorizes only P3-7 frozen trace logger capture execution preflight. It
  does not authorize capture execution, private row writes, retrieval,
  P4L/N1/N2 reruns, policy changes, runtime promotion, P5, or v1-A.
- P3-7 authorizes only P3-8 frozen trace logger explicit capture smoke over
  predeclared frozen/materialized event fixtures. It does not authorize retrieval,
  P4L/N1/N2 reruns, support labeling, counterfactuals, policy changes, runtime
  promotion, P5, or v1-A.
- P3-8 authorizes no next phase in the current workspace because required frozen
  event fixtures are unavailable. It does not write private rows, run retrieval,
  rerun P4L/N1/N2, run support labeling, execute counterfactuals, tune policy,
  promote runtime/default behavior, authorize P5, or authorize v1-A.
- P3-8F authorizes only P3-8G proxy fixture materialization smoke. P3-8F itself
  writes no private files, and P3-8G remains limited to proxy fixture files only:
  no trace capture, private trace rows, retrieval, P4L/N1/N2 reruns, support
  labeling, counterfactuals, denominator audit, policy tuning, runtime/default
  promotion, P5, or v1-A.
- P3-8G authorizes only P3-8H proxy fixture compatibility preflight. It writes
  proxy fixture files only and does not authorize P3-8 capture execution, private
  trace rows, retrieval, P4L/N1/N2 reruns, support labeling, counterfactuals,
  denominator audits, policy tuning, runtime/default promotion, P5, or v1-A.
- P3-8H authorizes only P3-8I explicit proxy fixture logger smoke design. It does
  not authorize P3-8 code changes, P3-8 capture execution, private trace rows,
  retrieval, P4L/N1/N2 reruns, support labeling, counterfactuals, denominator
  audits, policy tuning, runtime/default promotion, P5, or v1-A.
- P3-8I authorizes only P3-8J explicit proxy fixture logger smoke evaluator
  implementation as a separate evaluator. It does not authorize P3-8 changes,
  empirical capture, private trace rows, target evaluator imports/calls,
  retrieval, P4L/N1/N2 reruns, support labeling, counterfactuals, policy tuning,
  runtime/default promotion, P5, or v1-A.
- P3-8J authorizes only P3-8K proxy fixture smoke public projection audit. It
  does not authorize P3-8 changes, empirical capture, private trace rows, target
  evaluator imports/calls, retrieval, P4L/N1/N2 reruns, support labeling,
  counterfactuals, policy tuning, runtime/default promotion, P5, or v1-A.
- P3-8K authorizes only P3-8L projection field adequacy and empirical fixture
  requirement decision. It does not authorize private fixture reads, helper
  imports, P3-8 changes, empirical capture, private trace rows, retrieval,
  P4L/N1/N2 reruns, support labeling, counterfactuals, policy tuning,
  runtime/default promotion, P5, or v1-A.
- P3-8L closes the proxy route and authorizes only P3-8M empirical frozen event
  fixture acquisition design. It does not authorize private fixture reads, helper
  imports, trace capture execution, private trace writes, retrieval, P4L/N1/N2
  reruns, support labeling, counterfactuals, policy tuning, runtime/default
  promotion, P5, or v1-A.
- P3-8M authorizes only P3-8N empirical fixture acquisition preflight. It does
  not authorize fixture generation, capture execution, private fixture or trace
  writes, helper imports, target evaluator imports, retrieval, P4L/N1/N2 reruns,
  support labeling, counterfactuals, policy tuning, runtime/default promotion,
  P5, or v1-A.
- P3-8N authorizes only P3-8O empirical event source declaration design. It does
  not authorize fixture generation, capture execution, private reads/writes,
  helper imports, target evaluator imports, retrieval, P4L/N1/N2 reruns, support
  labeling, counterfactuals, policy tuning, runtime/default promotion, P5, or
  v1-A.
- P3-8O authorizes only P3-8P empirical event source declaration intake preflight.
  It does not authorize fixture generation, capture execution, private reads or
  writes, helper imports, target evaluator imports, retrieval, P4L/N1/N2 reruns,
  support labeling, counterfactuals, policy tuning, runtime/default promotion,
  P5, or v1-A.
- P3-8P authorizes no next phase in the default local run because no explicit
  empirical source declaration is supplied. It does not authorize fixture
  generation, capture execution, private writes, helper imports, target evaluator
  imports, retrieval, P4L/N1/N2 reruns, support labeling, counterfactuals, policy
  tuning, runtime/default promotion, P5, or v1-A.
- P3-8PS authorizes no next phase because committed public artifacts contain no
  legitimate empirical frozen/materialized event source. It does not authorize
  declaration generation, fixture generation, capture execution, private reads or
  writes, retrieval/reruns, support labeling, counterfactuals, policy tuning,
  runtime/default promotion, P5, or v1-A.
- N4 authorizes only N5 fixed-pool rank-order experiment preflight. It does not
  authorize new retrieval, reruns, selector/reranker execution, P5, BEA-v1-A,
  counterfactual execution, policy tuning, runtime/default promotion,
  method-winner claims, or downstream-value claims.
- N5 authorizes only N6 fixed-pool rank-order experiment execution over the 40
  frozen N4 sanitized cases and four predeclared fixed-pool order-transform arms.
  It does not authorize candidate-pool mutation, new retrieval, reruns,
  selector/reranker execution, private reads, policy/runtime changes,
  counterfactuals, method-winner claims, or downstream-value claims.
- N6 is a No-Go for missing exact public per-case arm outcome fields. It does not
  authorize N7 result audit, candidate-pool mutation, new retrieval, reruns,
  selector/reranker execution, private reads, policy/runtime changes,
  counterfactuals, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N6F authorizes only N6G read-only public arm-field source discovery. It does not
  authorize N6 rerun, field generation/materialization, private reads,
  retrieval/reruns, selector/reranker execution, policy/runtime changes,
  counterfactuals, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N6G authorizes no next phase because no exact public 160-row arm-outcome source
  exists. It does not authorize N6H, materialization, generation, N6 rerun,
  private reads, retrieval/reruns, selector/reranker execution, policy/runtime
  changes, counterfactuals, P5, BEA-v1-A, method-winner claims, or downstream-value
  claims.
- N6XR authorizes no next phase because no bounded 40-case candidate-pool replay
  path or exact public 160-row source exists. It does not authorize N7, N6 rerun,
  full rerun, retrieval, private reads, candidate-pool generation/materialization,
  selector/reranker execution, policy/runtime changes, counterfactuals, P5,
  BEA-v1-A, method-winner claims, or downstream-value claims.
- N6X-FR authorizes no next phase in the default local checkpoint because full-
  frozen reconstruction prerequisites are unavailable. It does not authorize N7,
  canary/full-40 execution, retrieval, full rerun, network/git clone, private
  reads, selector/reranker execution, policy/runtime changes, counterfactuals,
  P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N6XFR-B authorizes no next phase because building OpenLocus would require
  unapproved network dependency fetch and private reconstruction inputs are still
  unavailable. It does not authorize cargo build, N6X-FR canary/full capture,
  retrieval, full rerun, network/git clone, private reads, selector/reranker
  execution, policy/runtime changes, counterfactuals, P5, BEA-v1-A,
  method-winner claims, or downstream-value claims.
- N6XFR-C authorizes no N6X-FR canary/full capture because private FD1/P4L inputs
  remain unavailable even though the release binary was built. It does not
  authorize retrieval, full rerun, benchmark repository clone, OpenLocus binary
  execution, private reads, selector/reranker execution, policy/runtime changes,
  counterfactuals, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N6XFR-D authorizes only final mechanism route synthesis because no private
  reconstruction input candidates were found in the scoped metadata inventory. It
  does not authorize private reads, OpenLocus binary execution, retrieval, full
  rerun, candidate generation/materialization, N6X-FR canary/full execution,
  selector/reranker execution, policy/runtime changes, counterfactuals, P5,
  BEA-v1-A, method-winner claims, or downstream-value claims.
- The final BEA-v1 mechanism route synthesis authorizes no autonomous next
  experiment from current artifacts. Future work requires external empirical
  inputs or a new research directive; it does not authorize private reads,
  OpenLocus binary execution, retrieval, reruns, candidate generation or
  materialization, selector/reranker execution, policy/runtime changes,
  counterfactuals, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N6XFR-E authorizes only N7 recovered result audit. It does not authorize
  runtime/default promotion, policy changes, retrieval/reruns, candidate-pool
  generation/materialization, selector/reranker execution, counterfactuals, P5,
  BEA-v1-A, method-winner claims, or downstream-value claims.
- N7 authorizes only N8 independent recompute over the same private rows and same
  four arms. It does not authorize P5, BEA-v1-A, selector/reranker execution,
  retrieval expansion, runtime/default promotion, policy changes,
  counterfactuals, method-winner claims, or downstream-value claims.
- N8 authorizes only N9 recovered fixed-pool result replication package. It does not authorize
  P5, BEA-v1-A, selector/reranker execution, retrieval expansion, additional
  reruns, runtime/default promotion, policy changes, counterfactuals,
  method-winner claims, or downstream-value claims.
- N9 authorizes only N10 broader frozen denominator validation preflight. It does
  not authorize capture, private reads, recompute, retrieval/reruns, new-arm
  search, selector/reranker execution, P5, BEA-v1-A, runtime/default promotion,
  method-winner claims, or downstream-value claims.
- N10 authorizes no N11 or execution. It does not authorize private content reads,
  retrieval/reruns, candidate generation/materialization, selector/reranker
  execution, P5, BEA-v1-A, runtime/default promotion, method-winner claims, or
  downstream-value claims.
- N10R authorizes no N10S. It does not authorize materializing broader rows from
  N1 span evidence, OpenLocus/N2/P4L execution, retrieval/reruns, generated
  private rows, selector/reranker execution, P5, BEA-v1-A, runtime/default
  promotion, method-winner claims, or downstream-value claims.
- N10T authorizes only N10U N1 span-surface proxy result audit. It does not
  authorize N2-equivalent validation, private reads beyond the scoped span rows,
  retrieval/reruns, candidate generation/materialization, selector/reranker
  execution, P5, BEA-v1-A, runtime/default promotion, method-winner claims, or
  downstream-value claims.
- N10U authorizes only N10V independent recompute over the same private span rows.
  It does not authorize broad private reads, runtime/default promotion,
  method-winner claims, downstream-value claims, P5, BEA-v1-A,
  selector/reranker execution, retrieval/reruns, new-arm search, counterfactuals,
  or policy changes.
- N10V authorizes only N10W public replication package. It does not authorize
  broad private reads, runtime/default promotion, method-winner claims,
  downstream-value claims, P5, BEA-v1-A, selector/reranker execution,
  retrieval/reruns, new-arm search, counterfactuals, or policy changes.
- N10W authorizes only N10X stronger-validation preflight. It does not authorize
  execution, private reads, recompute, runtime/default promotion, P5, BEA-v1-A,
  selector/reranker execution, retrieval/reruns, new-arm search, method-winner
  claims, or downstream-value claims.
- N10X authorizes only N10Y public result audit. It does not authorize
  runtime/default promotion, P5, BEA-v1-A, selector/reranker execution,
  retrieval/reruns, candidate generation/materialization, new arms,
  method-winner claims, or downstream-value claims.
- N10Y authorizes only N10Z span-level failure-decomposition preflight. It does
  not authorize private reads, recompute, execution, runtime/default promotion,
  P5, BEA-v1-A, selector/reranker execution, retrieval/reruns, new-arm search,
  method-winner claims, or downstream-value claims.
- N10Z authorizes only N10AA span-window repair preflight. It does not authorize
  repair execution, retrieval/reruns, runtime/default promotion, P5, BEA-v1-A,
  selector/reranker execution, new-arm search, method-winner claims, or
  downstream-value claims.
- N10AA authorizes only N10AB fixed span-window repair smoke. It does not authorize
  private reads or repair execution within N10AA, retrieval/reruns, OpenLocus
  execution, candidate generation/materialization, new-arm search,
  selector/reranker execution, P5, BEA-v1-A, runtime/default promotion,
  method-winner claims, or downstream-value claims.
- N10AB authorizes only N10AC public repair-smoke result audit. It does not
  authorize runtime/default promotion, P5, BEA-v1-A, selector/reranker execution,
  retrieval/reruns, new-arm search, method-winner claims, or downstream-value
  claims.
- N10AC authorizes only N10AD independent recompute over the same private span
  rows. It does not authorize broad private reads, runtime/default promotion,
  retrieval/reruns, candidate generation/materialization, new-arm search,
  selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10AD authorizes only N10AE public replication package. It does not authorize
  private reads, runtime/default promotion, retrieval/reruns, candidate
  generation/materialization, new-arm search, selector/reranker execution, P5,
  BEA-v1-A, method-winner claims, or downstream-value claims.
- N10AE authorizes only N10AF next-step selection / stronger-validation preflight.
  It does not authorize private reads, runtime/default promotion, retrieval/reruns,
  candidate generation/materialization, new-arm search, selector/reranker
  execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N10AF authorizes only N10AG public claim-boundary audit/package. It does not
  authorize private reads, runtime/default promotion, retrieval/reruns, candidate
  generation/materialization, new-arm search, adaptive window tuning,
  selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10AG authorizes only N10AH default-off implementation feasibility preflight. It
  does not authorize actual runtime implementation, private reads, retrieval/reruns,
  candidate generation/materialization, new-arm search, adaptive tuning,
  selector/reranker execution, P5, BEA-v1-A, runtime/default promotion,
  method-winner claims, or downstream-value claims.
- N10AH authorizes only N10AI default-off span-window helper integration preflight.
  It does not authorize hook-in, runtime/default enablement, retrieval/reruns,
  selector/reranker execution, P5, BEA-v1-A, private reads, candidate generation,
  gold-as-policy behavior, adaptive tuning, method-winner claims, or
  downstream-value claims.
- N10AI authorizes only N10AJ default-off eval-only span projection adapter patch.
  It does not authorize existing evaluator hook-in, runtime/default enablement,
  private reads by default, retrieval/rerun, candidate generation, selector/reranker
  execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N10AJ authorizes only N10AK eval-only adapter public fixture integration audit
  package. It does not authorize existing evaluator hook-in, runtime/default
  enablement, private reads by default, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10AK authorizes only N10AL scoped eval-only adapter integration smoke. It does
  not authorize existing evaluator hook-in, runtime/default enablement, private
  reads by default, retrieval/rerun, candidate generation, selector/reranker
  execution, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N10AL authorizes only N10AM eval-only adapter integration result audit package.
  It does not authorize existing evaluator hook-in, runtime/default enablement,
  additional private reads, retrieval/rerun, candidate generation/materialization,
  new arms/window tuning, selector/reranker execution, P5, BEA-v1-A,
  method-winner claims, or downstream-value claims.
- N10AM authorizes only N10AN default-off existing-evaluator hook feasibility
  preflight. It does not authorize existing evaluator hook-in, runtime/default
  enablement, private reads, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10AN authorizes only N10AO default-off adapter-enabled variant evaluator patch.
  It does not authorize existing evaluator hook-in, modifying existing validated
  evaluators, runtime/default enablement, retrieval/rerun, candidate generation,
  new arms/window tuning, selector/reranker execution, P5, BEA-v1-A,
  method-winner claims, or downstream-value claims.
- N10AO authorizes only N10AP adapter-enabled variant evaluator result audit
  package. It does not authorize additional private reads, existing evaluator
  hook-in, modifying existing validated evaluators, runtime/default enablement,
  retrieval/rerun, candidate generation, new arms/window tuning,
  selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10AP authorizes only N10AQ heldout/external validation source-discovery
  preflight. It does not authorize direct experiment execution, private reads,
  runtime/default enablement, retrieval/rerun, candidate generation, new
  arms/window tuning, selector/reranker execution, P5, BEA-v1-A, method-winner
  claims, or downstream-value claims.
- N10AQ authorizes no next validation phase until heldout span-surface rows are
  supplied. It does not authorize N10AR, private reads, validation execution,
  runtime/default enablement, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10AQ-R authorizes no next validation phase until a bounded heldout span-surface
  acquisition path or rows are supplied. It does not authorize OpenLocus
  execution, retrieval/rerun, benchmark replay, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, runtime/default changes,
  method-winner claims, or downstream-value claims.
- N10AS authorizes only N10AT exploratory span-window variant sweep audit package.
  It does not authorize private reads, extra sweeps, heldout validation claims,
  runtime/default changes, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, adaptive tuning, method-winner
  claims, or downstream-value claims.
- N10AT authorizes only N10AU independent recompute of the full fixed 15-variant
  grid over the same scoped private rows. It does not authorize extra sweeps, new
  variants, heldout validation claims, runtime/default changes, retrieval/rerun,
  candidate generation, adaptive tuning, selector/reranker execution, P5,
  BEA-v1-A, method-winner claims, or downstream-value claims.
- N10AU authorizes only N10AV exploratory span-window variant sweep replication
  package. It does not authorize private reads, extra sweeps, new variants,
  heldout validation claims, runtime/default changes, retrieval/rerun, candidate
  generation, adaptive tuning, selector/reranker execution, P5, BEA-v1-A,
  method-winner claims, or downstream-value claims.
- N10AV authorizes only N10AW exploratory span-window follow-up selection audit.
  It does not authorize private reads, variant recompute, new sweeps, new variants,
  adaptive tuning, heldout validation, runtime/default changes, retrieval/rerun,
  candidate generation, selector/reranker execution, P5, BEA-v1-A, method-winner
  claims, or downstream-value claims.
- N10AW authorizes only N10AX cost-sensitive frontier claim package. It does not
  authorize private reads, recompute, new variants, adaptive tuning,
  heldout/generalization claims, runtime/default changes, retrieval/rerun,
  candidate generation, selector/reranker execution, P5, BEA-v1-A, method-winner
  claims, or downstream-value claims.
- N10AX authorizes only N10AY cost-aware adapter frontier smoke over the same scoped
  N1 rows with adapter/helper imports only. It does not authorize runtime/default,
  heldout/generalization, method-winner/downstream claims, retrieval/rerun,
  candidate generation/materialization, selector/reranker execution, P5, BEA-v1-A,
  new variants, or adaptive tuning.
- N10AY authorizes only N10AZ public adapter frontier smoke audit/package. It does
  not authorize additional private reads, existing evaluator hook-in,
  runtime/default promotion, new variants, adaptive tuning, retrieval/rerun,
  candidate generation/materialization, selector/reranker execution, P5,
  BEA-v1-A, method-winner claims, downstream-value claims, or
  heldout/generalization claims.
- N10AZ authorizes only N10BA cost-aware span-window selection rule smoke over the
  same scoped rows and predeclared operating points (`pm30`, `before25_after75`,
  `pm200`). It does not authorize runtime/default, heldout/generalization,
  method-winner/downstream claims, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, new variants, or adaptive tuning.
- N10BA authorizes only N10BB public audit/package. It does not authorize private
  reads beyond the same scoped rows, runtime/default promotion, new variants,
  adaptive selection, retrieval/rerun, candidate generation, selector/reranker
  execution, P5, BEA-v1-A, heldout/generalization claims, method-winner claims,
  or downstream-value claims.
- N10BB authorizes only N10BC operating-point tradeoff decomposition over the same
  scoped rows and no new variants. It does not authorize runtime/default,
  heldout/generalization, method-winner/downstream claims, retrieval/rerun,
  candidate generation, selector/reranker execution, P5, BEA-v1-A, or adaptive
  selection.
- N10BC authorizes only N10BD public tradeoff package. It does not authorize
  private reads, runtime/default, new variants, adaptive selection,
  heldout/generalization, method-winner/downstream claims, retrieval/rerun,
  candidate generation, selector/reranker execution, P5, or BEA-v1-A.
- N10BD authorizes only N10BE cost-aware operating-point decision smoke. It does
  not authorize runtime/default recommendation, broad private reads, new variants,
  adaptive selection, heldout/generalization, method-winner/downstream claims,
  retrieval/rerun, candidate generation, selector/reranker execution, P5, or
  BEA-v1-A.
- N10BE authorizes only N10BF public budget-decision package. It does not
  authorize runtime/default recommendation, extra private reads, new variants,
  adaptive selection, heldout/generalization, method-winner/downstream claims,
  retrieval/rerun, candidate generation, selector/reranker execution, P5, or
  BEA-v1-A.
- N10BF authorizes only N10BG cost-aware decisions vs fixed-pm50 comparator. It
  does not authorize runtime/default recommendation, broad private reads, new
  variants, adaptive selection, heldout/generalization, method-winner/downstream
  claims, retrieval/rerun, candidate generation, selector/reranker execution, P5,
  or BEA-v1-A.
- N10BG authorizes only N10BH public comparator package. It does not authorize
  broad private reads, runtime/default recommendation, new variants, adaptive
  selection, heldout/generalization, method-winner/downstream claims,
  retrieval/rerun, candidate generation, selector/reranker execution, P5, or
  BEA-v1-A.
- N10BH authorizes only N10BI asymmetric window direction mechanism decomposition
  over pm50 vs `before25_after75` on the same scoped rows. It does not authorize
  new variants, adaptive/default behavior, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims,
  method-winner claims, or downstream-value claims.
- N10BI authorizes only N10BJ public asymmetry mechanism package. It does not
  authorize private reads, new variants, adaptive tuning, runtime/default
  behavior, retrieval/rerun, candidate generation, selector/reranker execution,
  P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or
  downstream-value claims.
- N10BJ authorizes only N10BK neighboring asymmetry micro-sweep over the same
  scoped rows and same cost proxy `1000` with the predeclared five variants. It
  does not authorize new cost budgets, adaptive per-row choices, runtime/default
  behavior, retrieval/rerun, candidate generation, selector/reranker execution,
  P5, BEA-v1-A, heldout/generalization claims, method-winner claims, or
  downstream-value claims.
- N10BK authorizes only N10BL public direction-sensitivity package. It does not
  authorize private reads, new variants, adaptive choice, new cost budgets,
  runtime/default behavior, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims,
  method-winner claims, or downstream-value claims.
- N10BL authorizes only N10BM after-heavy local asymmetry refinement sweep over
  the same scoped rows and fixed total cost 100 with seven predeclared variants.
  It does not authorize other variants, adaptive per-row choice, new cost budgets,
  runtime/default behavior, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims,
  method-winner claims, or downstream-value claims.
- N10BM authorizes only N10BN public local-refinement package. It does not
  authorize private reads, other variants, adaptive per-row choice, new cost
  budgets, runtime/default behavior, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims,
  method-winner claims, or downstream-value claims.
- N10BN authorizes only N10BO plateau mechanism decomposition over the same scoped
  rows and plateau variants (`20/80`, `25/75`, `30/70`, `35/65`, `40/60`). It
  does not authorize other variants, adaptive per-row choice, new cost budgets,
  runtime/default behavior, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims,
  method-winner claims, or downstream-value claims.
- N10BO authorizes only N10BP public plateau mechanism package. It does not
  authorize private reads, other variants, adaptive per-row choice, new cost
  budgets, runtime/default behavior, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, heldout/generalization claims,
  method-winner claims, or downstream-value claims.
- N10BP authorizes only N10BQ plateau cost-minimization sweep over the same scoped
  rows, stable plateau ratio family, and total costs 60/80/100/120. It does not
  authorize adaptive tuning, new ratios outside the family, runtime/default
  behavior, heldout/generalization claims, method/downstream claims,
  retrieval/rerun, candidate generation, selector/reranker execution, P5, or
  BEA-v1-A.
- N10BQ authorizes only N10BR public cost-minimization package. It does not
  authorize private reads, adaptive tuning, new ratios outside the family,
  runtime/default behavior, heldout/generalization claims, method/downstream
  claims, retrieval/rerun, candidate generation, selector/reranker execution, P5,
  or BEA-v1-A.
- N10BR authorizes only N10BS boundary-cost refinement sweep over the same scoped
  rows, fixed 25/75 ratio, and total costs 65/70/75/80/85/90/95. It does not
  authorize private reads beyond the same scoped rows, new ratios, adaptive tuning,
  ranking/order changes, runtime/default behavior, heldout/generalization claims,
  method/downstream claims, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, or BEA-v1-A.
- N10BS authorizes only N10BT public boundary-cost package. It does not authorize
  private reads, new ratios, adaptive tuning, ranking/order changes,
  runtime/default behavior, heldout/generalization claims, method/downstream
  claims, retrieval/rerun, candidate generation, selector/reranker execution, P5,
  or BEA-v1-A.
- N10BT authorizes only N10BU boundary-case mechanism decomposition over the same
  scoped rows comparing fixed 25/75 costs 75 and 80. It does not authorize new
  variants, adaptive tuning, runtime/default behavior, heldout/generalization
  claims, method/downstream claims, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, or BEA-v1-A.
- N10BU authorizes only N10BV public boundary-case mechanism package. It does not
  authorize private reads, new variants, adaptive tuning, runtime/default
  behavior, heldout/generalization claims, method/downstream claims,
  retrieval/rerun, candidate generation, selector/reranker execution, P5, or
  BEA-v1-A.
- N10BV authorizes only N10BW adapter operating-point smoke for
  `cost80_before25_after75` through the default-off eval-only adapter path. It
  does not authorize private reads beyond the same scoped rows, existing evaluator
  hook-in, runtime/default behavior, new variants, adaptive tuning,
  heldout/generalization claims, method/downstream claims, retrieval/rerun,
  candidate generation, selector/reranker execution, P5, or BEA-v1-A.
- N10BW authorizes only N10BX public adapter operating-point package. It does not
  authorize private reads, existing evaluator hook-in, runtime/default behavior,
  new variants, adaptive tuning, heldout/generalization claims, method/downstream
  claims, retrieval/rerun, candidate generation, selector/reranker execution, P5,
  or BEA-v1-A.
- N10BX authorizes only N10BY cost-aware operating-point exploratory optimization
  over the same scoped N1 rows. It does not authorize runtime/default promotion,
  existing evaluator hook-in, heldout/generalization claims, method/downstream
  claims, retrieval/rerun, candidate generation, selector/reranker execution, P5,
  or BEA-v1-A.
- N10BY authorizes only N10BZ public audit/package. It does not authorize private
  reads, extra sweeps, new variants, adaptive tuning, runtime/default promotion,
  heldout/generalization claims, method/downstream claims, retrieval/rerun,
  candidate generation, selector/reranker execution, P5, or BEA-v1-A.
- N10BZ authorizes only N10CA next mechanism search outside the fixed-window
  family, same-source empirical if possible. It does not authorize runtime/default
  promotion, heldout/generalization claims, retrieval/rerun, candidate generation,
  selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10CA authorizes only N10CB public same-file cluster bridge audit/package. It
  does not authorize private reads, new variants, adaptive tuning, runtime/default
  promotion, heldout/generalization claims, method/downstream claims,
  retrieval/rerun, candidate generation/add/remove/reorder, selector/reranker
  execution, P5, or BEA-v1-A.
- N10CB authorizes only N10CC next mechanism search outside fixed-window and
  cluster-bridge families. It does not authorize runtime/default promotion,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10CC authorizes only N10CD public observable span-shape gated expansion
  audit/package. It does not authorize private reads, new variants, runtime/default
  promotion, heldout/generalization claims, retrieval/rerun, candidate generation/
  add/remove/reorder, cluster/bridge execution, adaptive tuning,
  selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10CD authorizes only N10CE span-shape refinement on the same scoped N1 rows
  with fixed/predeclared variants. It does not authorize runtime/default
  promotion, heldout/generalization claims, retrieval/rerun, candidate generation/
  add/remove/reorder, cluster/bridge execution, adaptive tuning,
  selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10CE authorizes only N10CF public span-shape refinement audit/package. It does
  not authorize private reads, new variants, runtime/default promotion,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, cluster/bridge execution, adaptive tuning, selector/reranker execution,
  P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- The repo does **not** currently contain a real non-Python downstream solve/test
  harness for the locked denominator. Existing B16 downstream harnesses are
  synthetic Python-only; ContextBench/RepoQA locked-denominator records currently
  provide retrieval-reach / gold-path signals, not downstream task success.
- Therefore P4L/N1/N2/N3 are not downstream-value evidence. The next bounded step
  must not be a mislabeled downstream smoke or an immediate P5/v1-A selector.

## What OpenLocus does **not** claim today

OpenLocus currently does **not** claim:

- a promoted retrieval policy,
- a default policy change,
- a method winner,
- BEA-v1-A selector readiness,
- P5 selector/reranker authorization,
- broad retrieval expansion readiness,
- downstream coding-agent solve-rate improvement,
- OOD/temporal generalization,
- QuIVer systems readiness,
- dense/graph/LLM-derived content as Evidence,
- or any change to `EvidenceCore` semantics.

Research artifacts are no longer assumed to be aggregate-only. New mechanism
and actionability phases should publish **scanner-validated, deep-research-agent
readable per-record analysis artifacts** whenever the data license and safety
boundary allow it. These artifacts should expose enough structure for follow-up
research agents to audit mechanisms: anonymous record ids, benchmark/language/
source buckets, arm names, action/state features, hit/miss booleans, rank or
rank-bucket fields, latency/pool/action-cost buckets, disagreement categories,
risk classes, and sanitized trace-gap/actionability fields. Aggregate-only output
is still appropriate for external datasets or provider runs whose redistribution
rules forbid row-level release. Raw prompts, responses, snippets, provider
payloads, secrets, provider keys, API keys, unsanitized private rows, and any
source-linkable private data must not be committed.

## Quick start

Build / inspect the CLI:

```bash
cargo run -p openlocus-cli -- --help
```

Representative commands:

```bash
# Source-backed read.
cargo run -p openlocus-cli -- read README.md:1-40 --json

# Repository scan.
cargo run -p openlocus-cli -- scan --json

# Exact / lexical / symbol search.
cargo run -p openlocus-cli -- search regex "EvidenceCore" --json
cargo run -p openlocus-cli -- search bm25 "candidate evidence" --json
cargo run -p openlocus-cli -- search symbol EvidenceCore --json

# Multi-channel retrieval.
cargo run -p openlocus-cli -- retrieve "EvidenceCore materialization" --channels regex,bm25,symbol --json

# Citation validation: true source hash/range/excerpt validation.
cargo run -p openlocus-cli -- citations validate evidence.json --json

# Session-local current-context helper.
cargo run -p openlocus-cli -- context-lite --write-files --json

# Persistent index experiments.
cargo run -p openlocus-cli -- index build --chunk-strategy line --json
cargo run -p openlocus-cli -- index validate --json

# Provider / derived / dense scaffolds are experimental.
cargo run -p openlocus-cli -- provider status --json
cargo run -p openlocus-cli -- derived build --experimental --write-files --json
cargo run -p openlocus-cli -- dense build --experimental --json
```

Some subcommands are research scaffolds. Anything marked `--experimental` should
be treated as candidate/diagnostic infrastructure, not a stable product API.

## Research entry points

Important scripts and artifacts:

```text
eval/p21_llm_rich_candidate.py
  Live rich-candidate harness.

eval/p25_bucket_policy.py
  Deterministic P25 bucket-routed reference policy.

eval/b10_runtime_feature_audit.py
  B10 balanced-policy feature provenance audit.

eval/b10b_runtime_shadow_replay.py
  Runtime-shadow replay scaffold for the ambiguous branch.

eval/b11_prospective_validation.py
  B11 per-record evaluator for the prospective matrix.

eval/b11_matrix_combiner.py
  Aggregate-only combiner for the 32-cell B11 integrated matrix.

eval/b12_public_aggregate_screen.py
  B12 bounded mechanism screen over public aggregate data.

eval/b13_public_aggregate_feasibility_screen.py
  B13 public-aggregate feasibility / no-go screen.

eval/b14_public_aggregate_feasibility_screen.py
  B14 public-aggregate uncertainty-calibration no-go screen.

eval/b15_context_pack_policy.py
  B15 context-pack policy preregistration / scaffold.

eval/b16_downstream_agent_evaluation.py
  B16 downstream-agent evaluation preregistration / scaffold.

eval/b17_quiver_systems_track.py
eval/b17_public_systems_diagnostic_screen.py
  B17 QuIVer systems-track scaffold and public diagnostic screen.

eval/b18_ood_temporal_evaluation.py
  B18 OOD/temporal preregistration + public no-go screen.

eval/b19_theoretical_synthesis.py
  B19 Model-Robust Selective Evidence Conversion synthesis.

eval/bea_v1_p4l_locked_non_python_scheduler_validation.py
  Locked non-Python frozen-P4 scheduler validation over the 272-record P4K
  denominator.

eval/bea_v1_n1_frozen_p4_span_refiner_smoke.py
  Frozen-P4 span-refiner smoke with D0 scheduler preservation and rank-aware D1
  total/top-10/rank-blocked denominators.

eval/bea_v1_n2_rank_pack_actionability_decomposition.py
  Rank/pack decomposition for N1's 40 rank-blocked records; authorizes only
  extra-depth merge-order design.

eval/bea_v1_n5_fixed_pool_rank_order_experiment_preflight.py
  No-execution fixed-pool rank-order experiment preflight freezing 40 N4 cases,
  four order-transform arms, N6 metrics, and pass gates.

eval/bea_v1_n6_fixed_pool_rank_order_experiment.py
  Public-artifact fixed-pool rank-order experiment evaluator; No-Go when exact
  public per-case fields for the N5/N6 arms are unavailable.

eval/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design.py
  Design-only public arm-field schema closure for future fixed-pool arm outcome
  materialization; authorizes only N6G read-only public source discovery.

eval/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit.py
  Read-only public source discovery audit; No-Go because candidate sources are
  analogue-only, aggregate-only, contract-only, or missing exact N6 arm fields.

eval/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke.py
  Fail-closed bounded candidate-pool recapture smoke; No-Go because the bounded
  40-case replay mapping is unavailable without full P4L reconstruction.

eval/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture.py
  Preflight-only full-frozen reconstruction capture boundary; No-Go when local
  binary/private reconstruction prerequisites are unavailable.

eval/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery.py
  Local prerequisite recovery smoke; No-Go because cargo build would require
  unapproved dependency-fetch network and private inputs remain unavailable.

eval/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery.py
  Scoped cargo dependency-fetch and release binary build recovery; partial
  because private reconstruction inputs remain unavailable.

eval/bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit.py
  Read-only metadata inventory of private reconstruction input buckets; No-Go
  because FD1/P4L/N-series/N6 candidates are unavailable.

eval/bea_v1_final_mechanism_route_synthesis.py
  Final public-artifact synthesis closing the autonomous BEA-v1 mechanism route;
  blocked on external empirical/private inputs.

eval/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment.py
  Recovered fixed-pool rank-order experiment over 40 private N2 rank-pack rows;
  passes with best top-10 recovery 25/40.

eval/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit.py
  Public-artifact-only audit of N6XFR-E; passes and authorizes only N8
  independent recompute over the same private rows and four arms.

eval/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms.py
  Independent recompute of the same private rows and four fixed-pool arms;
  matches N6XFR-E and authorizes only N9 replication package.

eval/bea_v1_n9_recovered_fixed_pool_result_replication_package.py
  Public replication package for the recovered fixed-pool result; authorizes only
  N10 broader frozen denominator validation preflight.

eval/bea_v1_n10_broader_frozen_denominator_validation_preflight.py
  Preflight for broader frozen-denominator validation; No-Go because broader
  N2-equivalent rank-pack rows are unavailable.

eval/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight.py
  Preflight for targeted N2 row generation; No-Go because the existing N2 builder
  lacks targeted denominator filtering and requires full reconstruction.

eval/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation.py
  N1 span-surface proxy fixed-pool rank-order validation; passes proxy threshold
  and authorizes only N10U proxy result audit.

eval/bea_v1_n10u_n1_span_surface_proxy_result_audit.py
  Public-artifact-only audit of N10T; passes and authorizes only N10V
  independent recompute over the same private span rows.

eval/bea_v1_n10v_independent_recompute_n1_span_surface_proxy.py
  Independent recompute of the N10T span-surface proxy over the same scoped
  private rows; matches N10T and authorizes only N10W public package.

eval/bea_v1_n10w_n1_span_surface_proxy_replication_package.py
  Public replication package for the N10T/N10U/N10V proxy chain; authorizes only
  N10X stronger-validation preflight with no execution.

eval/bea_v1_n10x_n1_span_surface_span_level_utility_validation.py
  Direct span-level utility validation over the N1 span surface; completes below
  threshold and authorizes only N10Y public result audit.

eval/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit.py
  Public-only audit of N10X; confirms complete below-threshold result and
  authorizes only N10Z failure-decomposition preflight.

eval/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition.py
  Direct decomposition of the N10X span-level gap; identifies same-file span-window
  misalignment and authorizes only N10AA repair preflight.

eval/bea_v1_n10aa_span_window_repair_preflight.py
  Gold-free fixed span-window repair design; authorizes only N10AB repair smoke
  and performs no repair execution.

eval/bea_v1_n10ab_fixed_span_window_repair_smoke.py
  Executes fixed symmetric span-window repair smoke over the scoped N1 span rows;
  pm50 passes and authorizes only N10AC public audit.

eval/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit.py
  Public audit of the N10AB repair-smoke result; confirms pm50 pass and authorizes
  only N10AD independent recompute.

eval/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke.py
  Independent recompute of the N10AB fixed-window repair smoke; matches aggregates
  and authorizes only N10AE public replication package.

eval/bea_v1_n10ae_fixed_span_window_repair_replication_package.py
  Public replication package for N10AB/N10AC/N10AD fixed-window repair chain;
  authorizes only N10AF preflight.

eval/bea_v1_n10af_fixed_span_window_repair_robustness_validation.py
  Direct subgroup robustness validation for the fixed pm50 repair; passes and
  authorizes only N10AG public claim-boundary audit/package.

eval/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package.py
  Public claim-boundary package for the fixed pm50 repair chain; authorizes only
  N10AH default-off implementation feasibility preflight.

eval/bea_v1_span_window_repair_helpers.py
  Pure default-off helper functions for fixed span-window expansion.

eval/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke.py
  Synthetic implementation smoke for the isolated helper; authorizes only N10AI
  integration preflight.

eval/bea_v1_n10ai_default_off_span_window_helper_integration_preflight.py
  Static integration preflight recommending a future eval-only span projection
  adapter; authorizes only N10AJ adapter patch.

eval/bea_v1_span_window_projection_adapter.py
  Default-off eval-only adapter that projects synthetic/eval span records through
  the pure fixed-window helper without IO, hook-in, or runtime/default behavior.

eval/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch.py
  Synthetic patch smoke for the adapter; authorizes only N10AK public fixture
  integration audit package.

eval/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package.py
  Public/synthetic audit package for the N10AH/N10AI/N10AJ adapter chain;
  authorizes only N10AL scoped eval-only integration smoke.

eval/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke.py
  Scoped empirical eval-only integration smoke using the N10AJ adapter over the
  same recovered N1 span rows; reproduces N10AB pm50 and authorizes only N10AM.

eval/bea_v1_n10am_eval_only_adapter_integration_result_audit_package.py
  Public-only audit package for the N10AL adapter integration result; authorizes
  only N10AN default-off hook feasibility preflight.

eval/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight.py
  Static preflight selecting a new adapter-enabled eval-only variant evaluator;
  authorizes only N10AO and does not hook existing validated evaluators.

eval/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator.py
  New default-off eval-only variant evaluator importing the adapter; explicit
  scoped enablement reproduces pm50 and authorizes only N10AP audit/package.

eval/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package.py
  Public-only audit package for the N10AO variant result; authorizes only N10AQ
  heldout/external validation source-discovery preflight.

eval/bea_v1_n10aq_heldout_span_surface_source_discovery.py
  Bounded local source discovery/schema sniffing for heldout span-surface rows;
  closes No-Go because no eligible heldout source is present.

eval/bea_v1_n10aqr_heldout_span_surface_acquisition_feasibility.py
  Feasibility decision for acquiring heldout span-surface rows; closes No-Go
  because no bounded acquisition command/source is available.

eval/bea_v1_n10as_exploratory_span_window_variant_sweep.py
  Same-source exploratory sweep over 15 fixed span-window variants on the N1
  proxy; reports low-cost/balanced/max-recall frontier points and authorizes
  only N10AT audit/package.

eval/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package.py
  Public-only audit/package for the N10AS sweep frontier tiers; authorizes only
  N10AU independent recompute over the same scoped rows and fixed grid.

eval/bea_v1_n10au_independent_recompute_span_window_variant_sweep.py
  Independent recompute of the full 15-variant N10AS grid over the same scoped N1
  span rows; matches N10AS/N10AT and authorizes only N10AV package.

eval/bea_v1_n10av_exploratory_span_window_sweep_replication_package.py
  Public replication package for N10AS/N10AT/N10AU frontier tiers; authorizes only
  N10AW follow-up selection audit.

eval/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition.py
  Cost-sensitive decomposition of the locked frontier tiers; finds incremental
  pm200 gains are same before/after gold-window miss recovery and authorizes only
  N10AX public claim package.

eval/bea_v1_n10ax_cost_sensitive_frontier_claim_package.py
  Public claim package for N10AW/N10AV/N10AU/N10AS cost-sensitive frontier facts;
  authorizes only N10AY cost-aware adapter frontier smoke.

eval/bea_v1_n10ay_cost_aware_adapter_frontier_smoke.py
  Direct empirical adapter smoke over locked cost-aware frontier tiers; matches
  N10AW/N10AV aggregates and authorizes only N10AZ public audit/package.

eval/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package.py
  Public audit package for N10AY adapter frontier smoke; authorizes only N10BA
  cost-aware span-window selection rule smoke.

eval/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke.py
  Direct smoke for predeclared low/balanced/max-recall operating points; authorizes
  only N10BB public audit/package.

eval/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package.py
  Public audit package for N10BA operating points; authorizes only N10BC
  operating-point tradeoff decomposition.

eval/bea_v1_n10bc_operating_point_tradeoff_decomposition.py
  Direct decomposition of low/balanced/max-recall operating-point tradeoffs;
  authorizes only N10BD public tradeoff package.

eval/bea_v1_n10bd_operating_point_tradeoff_package.py
  Public package of N10BC tradeoff facts; authorizes only N10BE cost-aware
  operating-point decision smoke.

eval/bea_v1_n10be_cost_aware_operating_point_decision_smoke.py
  Direct budget-bucket decision smoke over strict/moderate/recall operating
  points; authorizes only N10BF public audit package.

eval/bea_v1_n10bf_cost_aware_budget_decision_package.py
  Public package of N10BE budget-conditioned decisions; authorizes only N10BG
  fixed-pm50 comparator smoke.

eval/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator.py
  Direct comparator of budget-conditioned decisions against fixed pm50;
  authorizes only N10BH public comparator package.

eval/bea_v1_n10bh_pm50_comparator_package.py
  Public package of N10BG pm50 comparator facts; authorizes only N10BI asymmetric
  window direction mechanism decomposition.

eval/bea_v1_n10bi_asymmetric_window_direction_decomposition.py
  Direct decomposition of pm50 vs before25_after75 direction mechanism; authorizes
  only N10BJ public mechanism package.

eval/bea_v1_n10bj_asymmetric_window_mechanism_package.py
  Public package of N10BI asymmetry mechanism facts; authorizes only N10BK
  neighboring asymmetry micro-sweep.

eval/bea_v1_n10bk_neighboring_asymmetry_micro_sweep.py
  Direct same-cost five-point asymmetry sweep; authorizes only N10BL public
  direction-sensitivity package.

eval/bea_v1_n10bl_direction_sensitivity_package.py
  Public package of N10BK direction-sensitivity facts; authorizes only N10BM
  after-heavy local asymmetry refinement sweep.

eval/bea_v1_n10bm_after_heavy_local_asymmetry_refinement.py
  Direct fixed-cost after-heavy local refinement sweep; authorizes only N10BN
  public local-refinement package.

eval/bea_v1_n10bn_local_refinement_package.py
  Public package of N10BM local-refinement facts; authorizes only N10BO plateau
  mechanism decomposition.

eval/bea_v1_n10bo_plateau_mechanism_decomposition.py
  Direct decomposition of the after-heavy plateau common/union cases; authorizes
  only N10BP public plateau mechanism package.

eval/bea_v1_n10bp_plateau_mechanism_package.py
  Public package of N10BO stable plateau facts; authorizes only N10BQ plateau
  cost-minimization sweep.

eval/bea_v1_n10bq_plateau_cost_minimization_sweep.py
  Direct 20-variant plateau cost-minimization sweep; authorizes only N10BR public
  cost-minimization package.

eval/bea_v1_n10br_cost_minimization_package.py
  Public package of N10BQ cost-minimization facts; authorizes only N10BS
  boundary-cost refinement sweep.

eval/bea_v1_n10bs_boundary_cost_refinement_sweep.py
  Direct fixed-ratio boundary-cost refinement sweep over costs 65..95; authorizes
  only N10BT public boundary-cost package.

eval/bea_v1_n10bt_boundary_cost_package.py
  Public package of N10BS boundary-cost facts; authorizes only N10BU boundary-case
  mechanism decomposition.

eval/bea_v1_n10bu_boundary_case_mechanism_decomposition.py
  Direct one-case decomposition of the cost75/cost80 boundary; authorizes only
  N10BV public boundary-case mechanism package.

eval/bea_v1_n10bv_boundary_case_mechanism_package.py
  Public package of N10BU one-case boundary facts; authorizes only N10BW adapter
  operating-point smoke for cost80_before25_after75.

eval/bea_v1_n10bw_adapter_operating_point_smoke.py
  Adapter-path smoke for cost80_before25_after75; authorizes only N10BX public
  adapter operating-point package.

eval/bea_v1_n10bx_adapter_operating_point_package.py
  Public package of the N10BW adapter operating-point smoke; authorizes only N10BY
  same-source exploratory optimization over scoped N1 rows.

eval/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep.py
  Same-source exploratory sweep of 12 predeclared cost-efficient span-window
  policies; authorizes only N10BZ public audit/package.

eval/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package.py
  Public package of the N10BY negative fixed-window policy sweep; authorizes only
  N10CA next mechanism search outside the fixed-window family.

eval/bea_v1_n10ca_same_file_span_cluster_bridge_smoke.py
  Same-source same-file span cluster bridge smoke outside the fixed-window family;
  authorizes only N10CB public audit/package.

eval/bea_v1_n10cb_cluster_bridge_audit_package.py
  Public package of the N10CA negative same-file cluster bridge result; authorizes
  only N10CC next mechanism search outside fixed-window and cluster-bridge
  families.

eval/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke.py
  Same-source observable span-shape gated expansion smoke; authorizes only N10CD
  public audit/package.

eval/bea_v1_n10cd_observable_span_shape_audit_package.py
  Public package of the N10CC observable span-shape positive signal; authorizes
  only N10CE span-shape refinement.

eval/bea_v1_n10ce_span_shape_gated_refinement_sweep.py
  Same-source refinement of short-span gated expansion variants; authorizes only
  N10CF public audit/package.
```

Key reports:

- [`artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json`](artifacts/b11_prospective_matrix/b11_prospective_matrix_aggregate_report.json)
- [`artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json`](artifacts/b12_mechanism_decomposition/b12_public_aggregate_screen_report.json)
- [`artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json`](artifacts/b19_theoretical_synthesis/b19_theoretical_synthesis_report.json)
- [`artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json`](artifacts/bea_v1_p4l_locked_non_python_scheduler_validation/bea_v1_p4l_locked_non_python_scheduler_validation_report.json)
- [`artifacts/bea_v1_n1_frozen_p4_span_refiner_smoke/bea_v1_n1_frozen_p4_span_refiner_smoke_report.json`](artifacts/bea_v1_n1_frozen_p4_span_refiner_smoke/bea_v1_n1_frozen_p4_span_refiner_smoke_report.json)
- [`artifacts/bea_v1_n2_rank_pack_actionability_decomposition/bea_v1_n2_rank_pack_actionability_decomposition_report.json`](artifacts/bea_v1_n2_rank_pack_actionability_decomposition/bea_v1_n2_rank_pack_actionability_decomposition_report.json)
- [`artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json`](artifacts/bea_v1_n5_fixed_pool_rank_order_experiment_preflight/bea_v1_n5_fixed_pool_rank_order_experiment_preflight_report.json)
- [`artifacts/bea_v1_n6_fixed_pool_rank_order_experiment/bea_v1_n6_fixed_pool_rank_order_experiment_report.json`](artifacts/bea_v1_n6_fixed_pool_rank_order_experiment/bea_v1_n6_fixed_pool_rank_order_experiment_report.json)
- [`artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json`](artifacts/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design/bea_v1_n6f_fixed_pool_public_arm_field_materialization_design_report.json)
- [`artifacts/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit_report.json`](artifacts/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit/bea_v1_n6g_fixed_pool_arm_field_source_discovery_audit_report.json)
- [`artifacts/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke_report.json`](artifacts/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke_report.json)
- [`artifacts/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture_report.json`](artifacts/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture_report.json)
- [`artifacts/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery_report.json`](artifacts/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery/bea_v1_n6xfrb_local_reconstruction_prerequisite_recovery_report.json)
- [`artifacts/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery_report.json`](artifacts/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery/bea_v1_n6xfrc_cargo_dependency_fetch_release_binary_build_recovery_report.json)
- [`artifacts/bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit/bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit_report.json`](artifacts/bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit/bea_v1_n6xfrd_private_reconstruction_input_inventory_recovery_audit_report.json)
- [`artifacts/bea_v1_final_mechanism_route_synthesis/bea_v1_final_mechanism_route_synthesis_report.json`](artifacts/bea_v1_final_mechanism_route_synthesis/bea_v1_final_mechanism_route_synthesis_report.json)
- [`artifacts/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment_report.json`](artifacts/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment/bea_v1_n6xfre_recovered_fixed_pool_rank_order_experiment_report.json)
- [`artifacts/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit_report.json`](artifacts/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit/bea_v1_n7_recovered_fixed_pool_rank_order_result_audit_report.json)
- [`artifacts/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms_report.json`](artifacts/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms/bea_v1_n8_independent_recompute_same_private_rows_same_four_arms_report.json)
- [`artifacts/bea_v1_n9_recovered_fixed_pool_result_replication_package/bea_v1_n9_recovered_fixed_pool_result_replication_package_report.json`](artifacts/bea_v1_n9_recovered_fixed_pool_result_replication_package/bea_v1_n9_recovered_fixed_pool_result_replication_package_report.json)
- [`artifacts/bea_v1_n10_broader_frozen_denominator_validation_preflight/bea_v1_n10_broader_frozen_denominator_validation_preflight_report.json`](artifacts/bea_v1_n10_broader_frozen_denominator_validation_preflight/bea_v1_n10_broader_frozen_denominator_validation_preflight_report.json)
- [`artifacts/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight_report.json`](artifacts/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight/bea_v1_n10r_targeted_n2_rank_pack_generation_preflight_report.json)
- [`artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json`](artifacts/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation/bea_v1_n10t_n1_span_surface_rank_order_proxy_validation_report.json)
- [`artifacts/bea_v1_n10u_n1_span_surface_proxy_result_audit/bea_v1_n10u_n1_span_surface_proxy_result_audit_report.json`](artifacts/bea_v1_n10u_n1_span_surface_proxy_result_audit/bea_v1_n10u_n1_span_surface_proxy_result_audit_report.json)
- [`artifacts/bea_v1_n10v_independent_recompute_n1_span_surface_proxy/bea_v1_n10v_independent_recompute_n1_span_surface_proxy_report.json`](artifacts/bea_v1_n10v_independent_recompute_n1_span_surface_proxy/bea_v1_n10v_independent_recompute_n1_span_surface_proxy_report.json)
- [`artifacts/bea_v1_n10w_n1_span_surface_proxy_replication_package/bea_v1_n10w_n1_span_surface_proxy_replication_package_report.json`](artifacts/bea_v1_n10w_n1_span_surface_proxy_replication_package/bea_v1_n10w_n1_span_surface_proxy_replication_package_report.json)
- [`artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json`](artifacts/bea_v1_n10x_n1_span_surface_span_level_utility_validation/bea_v1_n10x_n1_span_surface_span_level_utility_validation_report.json)
- [`artifacts/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit_report.json`](artifacts/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit/bea_v1_n10y_n1_span_surface_span_level_utility_result_audit_report.json)
- [`artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json`](artifacts/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition/bea_v1_n10z_n1_span_surface_span_level_failure_decomposition_report.json)
- [`artifacts/bea_v1_n10aa_span_window_repair_preflight/bea_v1_n10aa_span_window_repair_preflight_report.json`](artifacts/bea_v1_n10aa_span_window_repair_preflight/bea_v1_n10aa_span_window_repair_preflight_report.json)
- [`artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json`](artifacts/bea_v1_n10ab_fixed_span_window_repair_smoke/bea_v1_n10ab_fixed_span_window_repair_smoke_report.json)
- [`artifacts/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit_report.json`](artifacts/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit/bea_v1_n10ac_fixed_span_window_repair_smoke_result_audit_report.json)
- [`artifacts/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke_report.json`](artifacts/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke/bea_v1_n10ad_independent_recompute_fixed_span_window_repair_smoke_report.json)
- [`artifacts/bea_v1_n10ae_fixed_span_window_repair_replication_package/bea_v1_n10ae_fixed_span_window_repair_replication_package_report.json`](artifacts/bea_v1_n10ae_fixed_span_window_repair_replication_package/bea_v1_n10ae_fixed_span_window_repair_replication_package_report.json)
- [`artifacts/bea_v1_n10af_fixed_span_window_repair_robustness_validation/bea_v1_n10af_fixed_span_window_repair_robustness_validation_report.json`](artifacts/bea_v1_n10af_fixed_span_window_repair_robustness_validation/bea_v1_n10af_fixed_span_window_repair_robustness_validation_report.json)
- [`artifacts/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package_report.json`](artifacts/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package/bea_v1_n10ag_fixed_span_window_repair_claim_boundary_package_report.json)
- [`artifacts/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke_report.json`](artifacts/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke/bea_v1_n10ah_default_off_span_window_helper_implementation_smoke_report.json)
- [`artifacts/bea_v1_n10ai_default_off_span_window_helper_integration_preflight/bea_v1_n10ai_default_off_span_window_helper_integration_preflight_report.json`](artifacts/bea_v1_n10ai_default_off_span_window_helper_integration_preflight/bea_v1_n10ai_default_off_span_window_helper_integration_preflight_report.json)
- [`artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json`](artifacts/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch/bea_v1_n10aj_default_off_eval_only_span_projection_adapter_patch_report.json)
- [`artifacts/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package_report.json`](artifacts/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package/bea_v1_n10ak_eval_only_adapter_public_fixture_audit_package_report.json)
- [`artifacts/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke_report.json`](artifacts/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke/bea_v1_n10al_scoped_eval_only_adapter_integration_smoke_report.json)
- [`artifacts/bea_v1_n10am_eval_only_adapter_integration_result_audit_package/bea_v1_n10am_eval_only_adapter_integration_result_audit_package_report.json`](artifacts/bea_v1_n10am_eval_only_adapter_integration_result_audit_package/bea_v1_n10am_eval_only_adapter_integration_result_audit_package_report.json)
- [`artifacts/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight_report.json`](artifacts/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight/bea_v1_n10an_default_off_existing_evaluator_hook_feasibility_preflight_report.json)
- [`artifacts/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator_report.json`](artifacts/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator/bea_v1_n10ao_default_off_adapter_enabled_variant_evaluator_report.json)
- [`artifacts/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package_report.json`](artifacts/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package/bea_v1_n10ap_adapter_enabled_variant_evaluator_result_audit_package_report.json)
- [`artifacts/bea_v1_n10aq_heldout_span_surface_source_discovery/bea_v1_n10aq_heldout_span_surface_source_discovery_report.json`](artifacts/bea_v1_n10aq_heldout_span_surface_source_discovery/bea_v1_n10aq_heldout_span_surface_source_discovery_report.json)
- [`artifacts/bea_v1_n10aqr_heldout_span_surface_acquisition_feasibility/bea_v1_n10aqr_heldout_span_surface_acquisition_feasibility_report.json`](artifacts/bea_v1_n10aqr_heldout_span_surface_acquisition_feasibility/bea_v1_n10aqr_heldout_span_surface_acquisition_feasibility_report.json)
- [`artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json`](artifacts/bea_v1_n10as_exploratory_span_window_variant_sweep/bea_v1_n10as_exploratory_span_window_variant_sweep_report.json)
- [`artifacts/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package_report.json`](artifacts/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package/bea_v1_n10at_exploratory_span_window_variant_sweep_audit_package_report.json)
- [`artifacts/bea_v1_n10au_independent_recompute_span_window_variant_sweep/bea_v1_n10au_independent_recompute_span_window_variant_sweep_report.json`](artifacts/bea_v1_n10au_independent_recompute_span_window_variant_sweep/bea_v1_n10au_independent_recompute_span_window_variant_sweep_report.json)
- [`artifacts/bea_v1_n10av_exploratory_span_window_sweep_replication_package/bea_v1_n10av_exploratory_span_window_sweep_replication_package_report.json`](artifacts/bea_v1_n10av_exploratory_span_window_sweep_replication_package/bea_v1_n10av_exploratory_span_window_sweep_replication_package_report.json)
- [`artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json`](artifacts/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition/bea_v1_n10aw_cost_sensitive_span_window_frontier_mechanism_decomposition_report.json)
- [`artifacts/bea_v1_n10ax_cost_sensitive_frontier_claim_package/bea_v1_n10ax_cost_sensitive_frontier_claim_package_report.json`](artifacts/bea_v1_n10ax_cost_sensitive_frontier_claim_package/bea_v1_n10ax_cost_sensitive_frontier_claim_package_report.json)
- [`artifacts/bea_v1_n10ay_cost_aware_adapter_frontier_smoke/bea_v1_n10ay_cost_aware_adapter_frontier_smoke_report.json`](artifacts/bea_v1_n10ay_cost_aware_adapter_frontier_smoke/bea_v1_n10ay_cost_aware_adapter_frontier_smoke_report.json)
- [`artifacts/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package_report.json`](artifacts/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package/bea_v1_n10az_cost_aware_adapter_frontier_smoke_audit_package_report.json)
- [`artifacts/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke_report.json`](artifacts/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke/bea_v1_n10ba_cost_aware_span_window_selection_rule_smoke_report.json)
- [`artifacts/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package_report.json`](artifacts/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package/bea_v1_n10bb_cost_aware_selection_rule_smoke_audit_package_report.json)
- [`artifacts/bea_v1_n10bc_operating_point_tradeoff_decomposition/bea_v1_n10bc_operating_point_tradeoff_decomposition_report.json`](artifacts/bea_v1_n10bc_operating_point_tradeoff_decomposition/bea_v1_n10bc_operating_point_tradeoff_decomposition_report.json)
- [`artifacts/bea_v1_n10bd_operating_point_tradeoff_package/bea_v1_n10bd_operating_point_tradeoff_package_report.json`](artifacts/bea_v1_n10bd_operating_point_tradeoff_package/bea_v1_n10bd_operating_point_tradeoff_package_report.json)
- [`artifacts/bea_v1_n10be_cost_aware_operating_point_decision_smoke/bea_v1_n10be_cost_aware_operating_point_decision_smoke_report.json`](artifacts/bea_v1_n10be_cost_aware_operating_point_decision_smoke/bea_v1_n10be_cost_aware_operating_point_decision_smoke_report.json)
- [`artifacts/bea_v1_n10bf_cost_aware_budget_decision_package/bea_v1_n10bf_cost_aware_budget_decision_package_report.json`](artifacts/bea_v1_n10bf_cost_aware_budget_decision_package/bea_v1_n10bf_cost_aware_budget_decision_package_report.json)
- [`artifacts/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator_report.json`](artifacts/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator/bea_v1_n10bg_cost_aware_decisions_vs_fixed_pm50_comparator_report.json)
- [`artifacts/bea_v1_n10bh_pm50_comparator_package/bea_v1_n10bh_pm50_comparator_package_report.json`](artifacts/bea_v1_n10bh_pm50_comparator_package/bea_v1_n10bh_pm50_comparator_package_report.json)
- [`artifacts/bea_v1_n10bi_asymmetric_window_direction_decomposition/bea_v1_n10bi_asymmetric_window_direction_decomposition_report.json`](artifacts/bea_v1_n10bi_asymmetric_window_direction_decomposition/bea_v1_n10bi_asymmetric_window_direction_decomposition_report.json)
- [`artifacts/bea_v1_n10bj_asymmetric_window_mechanism_package/bea_v1_n10bj_asymmetric_window_mechanism_package_report.json`](artifacts/bea_v1_n10bj_asymmetric_window_mechanism_package/bea_v1_n10bj_asymmetric_window_mechanism_package_report.json)
- [`artifacts/bea_v1_n10bk_neighboring_asymmetry_micro_sweep/bea_v1_n10bk_neighboring_asymmetry_micro_sweep_report.json`](artifacts/bea_v1_n10bk_neighboring_asymmetry_micro_sweep/bea_v1_n10bk_neighboring_asymmetry_micro_sweep_report.json)
- [`artifacts/bea_v1_n10bl_direction_sensitivity_package/bea_v1_n10bl_direction_sensitivity_package_report.json`](artifacts/bea_v1_n10bl_direction_sensitivity_package/bea_v1_n10bl_direction_sensitivity_package_report.json)
- [`artifacts/bea_v1_n10bm_after_heavy_local_asymmetry_refinement/bea_v1_n10bm_after_heavy_local_asymmetry_refinement_report.json`](artifacts/bea_v1_n10bm_after_heavy_local_asymmetry_refinement/bea_v1_n10bm_after_heavy_local_asymmetry_refinement_report.json)
- [`artifacts/bea_v1_n10bn_local_refinement_package/bea_v1_n10bn_local_refinement_package_report.json`](artifacts/bea_v1_n10bn_local_refinement_package/bea_v1_n10bn_local_refinement_package_report.json)
- [`artifacts/bea_v1_n10bo_plateau_mechanism_decomposition/bea_v1_n10bo_plateau_mechanism_decomposition_report.json`](artifacts/bea_v1_n10bo_plateau_mechanism_decomposition/bea_v1_n10bo_plateau_mechanism_decomposition_report.json)
- [`artifacts/bea_v1_n10bp_plateau_mechanism_package/bea_v1_n10bp_plateau_mechanism_package_report.json`](artifacts/bea_v1_n10bp_plateau_mechanism_package/bea_v1_n10bp_plateau_mechanism_package_report.json)
- [`artifacts/bea_v1_n10bq_plateau_cost_minimization_sweep/bea_v1_n10bq_plateau_cost_minimization_sweep_report.json`](artifacts/bea_v1_n10bq_plateau_cost_minimization_sweep/bea_v1_n10bq_plateau_cost_minimization_sweep_report.json)
- [`artifacts/bea_v1_n10br_cost_minimization_package/bea_v1_n10br_cost_minimization_package_report.json`](artifacts/bea_v1_n10br_cost_minimization_package/bea_v1_n10br_cost_minimization_package_report.json)
- [`artifacts/bea_v1_n10bs_boundary_cost_refinement_sweep/bea_v1_n10bs_boundary_cost_refinement_sweep_report.json`](artifacts/bea_v1_n10bs_boundary_cost_refinement_sweep/bea_v1_n10bs_boundary_cost_refinement_sweep_report.json)
- [`artifacts/bea_v1_n10bt_boundary_cost_package/bea_v1_n10bt_boundary_cost_package_report.json`](artifacts/bea_v1_n10bt_boundary_cost_package/bea_v1_n10bt_boundary_cost_package_report.json)
- [`artifacts/bea_v1_n10bu_boundary_case_mechanism_decomposition/bea_v1_n10bu_boundary_case_mechanism_decomposition_report.json`](artifacts/bea_v1_n10bu_boundary_case_mechanism_decomposition/bea_v1_n10bu_boundary_case_mechanism_decomposition_report.json)
- [`artifacts/bea_v1_n10bv_boundary_case_mechanism_package/bea_v1_n10bv_boundary_case_mechanism_package_report.json`](artifacts/bea_v1_n10bv_boundary_case_mechanism_package/bea_v1_n10bv_boundary_case_mechanism_package_report.json)
- [`artifacts/bea_v1_n10bw_adapter_operating_point_smoke/bea_v1_n10bw_adapter_operating_point_smoke_report.json`](artifacts/bea_v1_n10bw_adapter_operating_point_smoke/bea_v1_n10bw_adapter_operating_point_smoke_report.json)
- [`artifacts/bea_v1_n10bx_adapter_operating_point_package/bea_v1_n10bx_adapter_operating_point_package_report.json`](artifacts/bea_v1_n10bx_adapter_operating_point_package/bea_v1_n10bx_adapter_operating_point_package_report.json)
- [`artifacts/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep_report.json`](artifacts/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep/bea_v1_n10by_same_source_cost_efficient_span_window_policy_sweep_report.json)
- [`artifacts/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package_report.json`](artifacts/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package/bea_v1_n10bz_cost_efficient_policy_sweep_audit_package_report.json)
- [`artifacts/bea_v1_n10ca_same_file_span_cluster_bridge_smoke/bea_v1_n10ca_same_file_span_cluster_bridge_smoke_report.json`](artifacts/bea_v1_n10ca_same_file_span_cluster_bridge_smoke/bea_v1_n10ca_same_file_span_cluster_bridge_smoke_report.json)
- [`artifacts/bea_v1_n10cb_cluster_bridge_audit_package/bea_v1_n10cb_cluster_bridge_audit_package_report.json`](artifacts/bea_v1_n10cb_cluster_bridge_audit_package/bea_v1_n10cb_cluster_bridge_audit_package_report.json)
- [`artifacts/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke_report.json`](artifacts/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke/bea_v1_n10cc_observable_span_shape_gated_expansion_smoke_report.json)
- [`artifacts/bea_v1_n10cd_observable_span_shape_audit_package/bea_v1_n10cd_observable_span_shape_audit_package_report.json`](artifacts/bea_v1_n10cd_observable_span_shape_audit_package/bea_v1_n10cd_observable_span_shape_audit_package_report.json)
- [`artifacts/bea_v1_n10ce_span_shape_gated_refinement_sweep/bea_v1_n10ce_span_shape_gated_refinement_sweep_report.json`](artifacts/bea_v1_n10ce_span_shape_gated_refinement_sweep/bea_v1_n10ce_span_shape_gated_refinement_sweep_report.json)

Documentation mirror check:

```bash
python3 scripts/validate_docs_i18n.py
```

## Development checks

Common local checks:

```bash
cargo fmt --all --check
cargo test --workspace
python3 scripts/validate_docs_i18n.py
python3 eval/b19_theoretical_synthesis.py --self-test
```

For live provider experiments, use the GitHub workflow with explicit opt-in. Do
not run remote providers implicitly from local scripts.

## Repository notes

- Main design document: [`openlocus-research-design.md`](openlocus-research-design.md)
- Agent usage guide: [`docs/en/AGENTS.md`](docs/en/AGENTS.md)
- Current research conclusions: [`docs/current-research-conclusions.md`](docs/current-research-conclusions.md)
- License: [`LICENSE`](LICENSE) (AGPL-3.0-only)
