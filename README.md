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

The latest closed phase is **BEA-v1-N10U: N1 Span-Surface Proxy Result Audit**:

```text
status: n1_span_surface_proxy_result_audit_pass_n10v_authorized
self-test: 15 / 15
forbidden scan: pass
surface: n1_span_p4_evidence_order_proxy
N2-equivalent validation: false
eligible denominator: 213
reachable in pool: 52
best arm: span_extra_depth_promote_before_primary_prefix_4
best top10 file reach: 34
best top20 file reach: 44
best delta top10 vs baseline: 34
best regressions vs baseline: 0
next allowed phase: BEA-v1-N10V Independent Recompute N1 Span-Surface Proxy
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
