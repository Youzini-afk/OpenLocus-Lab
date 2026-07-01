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

Status date: **2026-06-30**.

OpenLocus is now in the **BEA v1 actionability / retrieval-action scheduling**
line. The current question is no longer “which retrieval channel is globally
strongest?”; it is:

> How do we convert high-reach, high-false-cost candidate pools into low-false-
> cost, citation-valid Evidence without weakening `EvidenceCore`?

**The BEA-v1-N10E safety-probe branch is now closed.** N10ES (checkpoint
`8c04a0a`) packaged the N10ER bounded public CI score/guard safety probe as a
valid public held-out negative — CI run `28457213423`, status
`n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized`, sample
`80/60/40`, citation `7772/7772`, baseline `37/39/40/40`, full `36/39/40/40`,
guard `38/39/40/40`, diffaware `37/39/40/40`, risk bucket `task_count=26`,
losses `0/0/0` — and authorized only N10ET. N10ET (close-out design/decision,
checkpoint `26d817e`, status
`n10et_public_safety_probe_design_decision_complete_haae_r0_authorized`) then
locked N10ES/N10ER as a valid public held-out negative, confirmed the
difference-aware rule remains a local same-source hypothesis (not a
transferable method), and authorized **only** the next route:
**BEA-v1-HAAE-R0 — Hierarchical Actionable Evidence Acquisition Route Design /
Schema Preflight**. HAAE-R0 is explicitly **not** BEA-v1-A, not selector-only,
not selector/reranker execution, not P5, and not a runtime/default promotion.

**BEA-v1-HAAE-R0: Hierarchical Actionable Evidence Acquisition Route Design /
Schema Preflight** is now complete as the public-only, design-only schema
preflight for the next acquisition route (checkpoint `854fc2e`, status
`haae_r0_design_schema_preflight_complete_haae_r1_authorized`). HAAE-R0 locks
the N10ET source (checkpoint `26d817e`), designs a machine-readable,
non-empty control-plane — 4 route architecture layers (source_acquisition,
rank_pack_depth_to_head, span_projection, scheduler_operating_point), a 10-group
unified private trace schema spec, a 4-contract public aggregation contract,
5 same-budget arm specs (BM25_same_budget, RRF_same_budget, BEA_v0.3_frozen,
V1_sched_span, V1_sched_span_rank), 6 metric specs, a held-out protocol, 4 stop
rules, and a synthetic validator with an embedded 4-task synthetic fixture —
and authorizes **only** the next phase: **BEA-v1-HAAE-R1 — Unified Private
Trace Schema Feasibility Inventory** (explicit private roots only, aggregate
buckets only, no replay/scoring/retrieval/candidate generation). HAAE-R0 is
explicitly **not** BEA-v1-A, not selector-only, not selector/reranker
execution, not P5, and not a runtime/default promotion. It performs no
execution, no private reads, no CI rerun, no retrieval/recompute, no candidate
generation, no arm scoring, and no OpenLocus execution.

**BEA-v1-HAAE-R1: Unified Private Trace Schema Feasibility Inventory** is now
complete as the feasibility inventory for the unified private trace schema
(checkpoint `854fc2e`, status
`haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots`,
self-test `121/121`). HAAE-R1 locks the HAAE-R0 source (checkpoint `854fc2e`,
status `haae_r0_design_schema_preflight_complete_haae_r1_authorized`) and
inventories whether the 10 HAAE-R0 schema groups (`task_identity`,
`anchor_source`, `candidate_pool`, `rank_pack`, `span_projection`,
`scheduler_action`, `evidence_core`, `arm_assignment`, `outcome_metric`,
`safety_probe_signal`) can be populated from explicitly supplied
project-private root buckets, emitting aggregate buckets only. The 5 critical
groups are `task_identity`, `candidate_pool`, `evidence_core`, `arm_assignment`,
`outcome_metric`. Default/no-private mode produces the unavailable artifact
(no explicit private roots, private read count bucket `count_0`); real
inventory requires explicit `--allow-private-inventory --private-root <path>`
opt-in. HAAE-R1 performs no replay, no scoring, no retrieval, no candidate
generation, no arm scoring, no OpenLocus execution, and no HAAE-layer
execution. It never publishes paths, filenames, basenames, repo names, task
ids, queries, candidates, spans, snippets, hashes, exact ranks/scores, labels,
or row values. HAAE-R1 is explicitly **not** BEA-v1-A, not selector-only, not
selector/reranker execution, not P5, and not a runtime/default promotion. The
handoff is: pass → authorizes only **BEA-v1-HAAE-R2 Feasibility-Gated Offline
Trace Join Design** (design-only, no execution/replay/scoring/retrieval/
candidate generation); controlled no-go → authorizes only **BEA-v1-HAAE-R1A
Private Trace Coverage Gap Design** (design-only, no execution).

**BEA-v1-HAAE-R1A: Private Trace Coverage Gap Design** is now complete as the
public-only design phase responding to the HAAE-R1 coverage gap (checkpoint
`2ea77da`, status
`haae_r1_feasibility_inventory_unavailable_no_explicit_private_roots`,
self-test `112/112`, R1A status
`haae_r1a_private_trace_coverage_gap_design_complete_r1b_preflight_authorized`,
checkpoint `e54d1b4`). HAAE-R1A locks the HAAE-R1 source (confirmed all 10 schema
groups `not_present`, HAAE-R2 false), classifies a root source option for each
of the 10 groups (9 `public_evidence_strong`, 1 `public_evidence_partial`),
designs 5 bounded regeneration designs (explicit opt-in, FD1 private
decomposition, P4L private arm-outcome, N10EO private diagnostic rerun, N10ER
public CI replay), designs a 6-field root manifest schema, and authorizes
**only** the next phase: **BEA-v1-HAAE-R1B Bounded Private Trace Root
Regeneration Preflight Package** (design-only, no execution/private read/
replay/scoring/retrieval/candidate generation). HAAE-R1A performs no private
reads, no root regeneration, no replay/scoring/retrieval/candidate generation/
HAAE-layer execution/CI/network/clone. It is explicitly **not** BEA-v1-A, not
selector-only, not selector/reranker execution, not P5, and not a
runtime/default promotion.

**BEA-v1-HAAE-R1B: Bounded Private Trace Root Regeneration Preflight Package**
is now complete as the public-only, design-only preflight package (checkpoint
`e54d1b4`, status
`haae_r1b_bounded_private_trace_root_regeneration_preflight_package_complete_r1c_smoke_authorized`,
self-test `108/108`). HAAE-R1B locks the HAAE-R1A source (confirmed R1B
authorized/design-only, all execution false), packages a machine-readable
control-plane — 12 public inputs, 10 recipes (covering all 10 HAAE-R0 schema
groups), 5 safe operators, 3 private output contracts, 5 public manifest schema
fields, and an R1C bounded contract — and authorizes **only** the next phase:
**BEA-v1-HAAE-R1C Bounded Private Trace Root Regeneration Smoke** (design-only,
 separately implemented/reviewed). R1B performs no private reads, no root
 regeneration, no replay/scoring/retrieval/candidate generation/HAAE-layer
 execution/CI/network/clone. It is explicitly **not** BEA-v1-A, not
 selector-only, not selector/reranker execution, not P5, and not a
 runtime/default promotion.

**BEA-v1-HAAE-R1C: Bounded Private Trace Root Regeneration Smoke** is now
complete as the first explicit-opt-in phase allowed to create a private HAAE
trace-root artifact (checkpoint `8830492`, status
`haae_r1c_bounded_private_manifest_root_smoke_complete_r1d_inventory_authorized`,
self-test `105/105`, private writes `1`). R1C is a bounded smoke of the root/output/manifest pipeline: it must NOT run
FD1/P4L/N10EO/N10ER replay, retrieval, scoring, candidate generation,
selector, BEA-v1-A/P5/runtime/default. Default/no-private mode performs no
private reads or writes and produces the unavailable artifact. Explicit
opt-in (`--allow-private-root-regeneration-smoke --recipe
bootstrap_private_manifest_root_smoke --private-output-root <path>
--confirm-private-output-only`) creates an explicit private output root,
writes only manifest/control files and empty/schema-category placeholders
with **zero** raw task/query/candidate/span/score rows, and publishes a
bucketized manifest only. The successful bootstrap smoke authorizes only
**BEA-v1-HAAE-R1D Explicit Private Root Schema Inventory Smoke**; replay,
scoring, retrieval, candidate generation, selector, BEA-v1-A/P5, and runtime
remain false. R1C is explicitly **not** BEA-v1-A, not
selector-only, not selector/reranker execution, not P5, and not a
runtime/default promotion.

The detailed source of truth for the closed N10E branch and the HAAE route is
[`docs/en/current-research-conclusions.md`](docs/en/current-research-conclusions.md)
(EN) / [`docs/zh/current-research-conclusions.md`](docs/zh/current-research-conclusions.md)
(ZH), together with the per-phase N10EO/N10EP/N10EQ/N10ER/N10ES/N10ET/HAAE-R0/
HAAE-R1/HAAE-R1A/HAAE-R1B/HAAE-R1C docs. The chronological narrative below
preserves the N10EM → N10EN → N10EO → N10EP → N10EQ → N10ER → N10ES → N10ET →
HAAE-R0 → HAAE-R1 → HAAE-R1A → HAAE-R1B → HAAE-R1C progression as historical
context.

**BEA-v1-HAAE-R1D: Explicit Private Root Schema Inventory Smoke** is complete as
a controlled No-Go for the R1C bootstrap root (checkpoint `bc1e7a2`, status
`haae_r1d_schema_inventory_complete_no_go_bootstrap_placeholders_only`, self-test
`92/92`). R1D ran explicit private-root schema/category inventory only: private
read bucket `count_1_to_10`, private write bucket `count_0`, row values read
`false`, raw publication `false`, and all 10 HAAE schema groups accounted. The
root is bootstrap placeholders only: placeholder groups `count_1_to_10`,
meaningful groups `count_0`. It authorizes no hydration execution and no
HAAE-R2; any future work must be a separate bounded hydration preflight or an
operator-supplied meaningful root, still with replay/scoring/retrieval/candidate
generation/BEA-v1-A/P5/runtime false.

**BEA-v1-HAAE-R1E: Bounded Private Experiment Material Generation** is now
complete as the first explicit-opt-in phase allowed to generate tiny real
private material rows (source lock `9299b0a`, status
`haae_r1e_bounded_private_material_generation_complete_r2_small_experiment_authorized`,
self-test `21/21`). Default/no-opt-in mode performs no private reads or writes
and emits status `haae_r1e_unavailable_no_explicit_material_generation_opt_in`.
Explicit mode is local/manual only and requires
`--allow-private-material-generation --private-output-root <temp-or-ignored-root>
--sample-size <=5 --candidate-depth <=20 --confirm-private-rows-only`. The
materializer uses public R14 sanity tasks and labels privately, scans only a
bounded committed Rust corpus from the R14 lock, and writes raw task/query/path/
label/rank/evidence rows only under the explicit private root. The public
artifact is aggregate-only and scanner-passed: no private path, task id, query,
candidate path/name, span, score, hash, label, snippet, row, or diagnostic value
is published. R1E authorizes only a small local HAAE-R2 experiment; CI, network,
clone, provider/model calls, selector/reranker, BEA-v1-A/P5, runtime/default
change, broad replay, and method-winner claims remain false.

**BEA-v1-HAAE-R2: Small Local Lexical Material Experiment** is complete as a
tiny local/manual aggregate experiment over existing R1E private material (source
lock `0135e1f`, status
`haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized`,
self-test `21/21`). Default mode performs no private reads or writes and emits
status `haae_r2_unavailable_no_explicit_r1e_private_material_root`. Explicit mode
requires `--allow-private-material-experiment --private-material-root <existing-r1e-private-material-root>
--confirm-aggregate-publication-only`; the supplied root is read only and is not
published. R2 compares only precomputed `rank_pack` traces (`bm25_like`,
`symbol_overlap`, `rrf_like`) joined in memory with `outcome_metric` to compute
aggregate buckets. It performs no private writes, new candidate generation,
rematerialization, source-corpus scan, broad retrieval, OpenLocus runtime,
scheduler/HAAE-layer execution, selector/reranker, CI/network/clone/provider,
BEA-v1-A/P5, runtime/default change, raw publication, method-winner claim, or R3
scale authorization. R2 authorizes only **BEA-v1-HAAE-R2A Public Audit Package**.

**BEA-v1-HAAE-R2A Small Local Experiment Public Audit Package** is complete as a
public-only audit/package of the R2 aggregate artifact (source lock `0784be0`,
R2 status `haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized`,
status `haae_r2a_public_audit_package_complete_r2b_scale_preflight_design_authorized`,
self-test `22/22`). The audit reads no private material and performs no recompute,
candidate generation, retrieval, scheduler/HAAE execution, selector/reranker,
runtime/default change, or BEA-v1-A/P5 action. It confirms the R2 tiny-N aggregate
readback: `bm25_like`, `symbol_overlap`, and `rrf_like` all have hit-rate bucket
`rate_1`, pairwise same-top agreement bucket `rate_1`, and sample bucket
`count_2_to_5`. This remains a tiny-N audit with no method-winner claim and no
runtime/default decision. R2A authorizes only **BEA-v1-HAAE-R2B Scale Preflight Design**
over how to expand material generation beyond three tasks; it does not
authorize scale execution or CI.

**BEA-v1-HAAE-R2B Scale Preflight Design** is complete as a public-only
design/preflight (R2A checkpoint `2ca1ac4`, status
`haae_r2b_scale_preflight_design_complete_r2c_local_medium_material_smoke_preflight_authorized`,
self-test `22/22`). It selects `r14_medium_local_material_smoke` as the bounded
local/manual next option, with source fixture task-count `count_21_to_50`, target task-count `count_10_to_20`, selected subset policy `deterministic_public_manifest_prefix_cap_10_to_20`,
candidate-depth `count_20`, and private-row cap `count_le_5000`. The boundary is
no private/material gen/execution/CI/network/BEA-v1-A/P5/method-winner: no
private reads/writes, material generation, experiments, recompute, candidate
generation, retrieval, source-corpus scan, scheduler/HAAE execution,
selector/reranker, CI/network/clone, runtime/default change, BEA-v1-A/P5, or
method-winner/scaling claim. R2B authorizes only **BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight**; R2C execution, private read/write, CI execution, and
material generation remain false.

**BEA-v1-HAAE-R2C Local Medium Material Smoke Preflight** is complete as a
public-only preflight/package (R2B checkpoint `dea8a2f`, status
`haae_r2c_local_medium_material_smoke_preflight_complete_r2d_generation_smoke_authorized`,
self-test `21/21`). It locks `r14_medium_local_material_smoke`, source fixture
bucket `count_21_to_50`, subset policy `deterministic_public_manifest_prefix_cap_10_to_20`,
target task bucket `count_10_to_20`, candidate depth `count_20`, and private row
cap `count_le_5000`. Boundary: `no_private_material_gen_execution_ci_network_bea_v1_a_p5_method_winner`.
R2C creates no private root, writes no private rows, generates no material, runs
no experiment, recompute, retrieval, source scan beyond fixture count,
OpenLocus/runtime, network/clone/CI, scheduler/HAAE, selector/reranker,
runtime/default, BEA-v1-A/P5, or method/scaling claim. It authorizes only
**BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke** with explicit
local/manual opt-in, private rows under an explicit private root, and public
aggregate-only output.

**BEA-v1-HAAE-R2D Explicit Local Medium Material Generation Smoke** is implemented
with safe default unavailable mode and explicit opt-in private material generation
(R2C checkpoint `68000b2`, default status
`haae_r2d_unavailable_no_explicit_medium_material_generation_opt_in`, pass status
`haae_r2d_explicit_local_medium_material_generation_smoke_complete_r2e_material_audit_authorized`,
self-test `19/19`). Explicit opt-in is required. It uses subset policy
`deterministic_public_manifest_prefix_cap_10_to_20`, public fixture bucket
`count_21_to_50`, target bucket `count_10_to_20`, candidate depth `count_20`, and
private row cap `count_le_5000`. In explicit mode the private write bucket is
`count_le_5000` and private read validation bucket is `count_1_to_10`; default
mode writes `count_0`. The public artifact is public aggregate-only with no raw publication.
Boundaries remain: no experiment comparison, no R2 recompute,
no runtime/retrieval/source scan beyond fixture, no CI/network/provider,
no scheduler/HAAE/selector, no BEA-v1-A/P5/runtime/default, and
no method/scaling claim. R2D authorizes only **BEA-v1-HAAE-R2E Local Medium Material Audit Package**.

**BEA-v1-HAAE-R2E Local Medium Material Audit Package** is complete as a
public-only audit of the R2D public aggregate artifact (R2D checkpoint `c4e454a`,
R2D status `haae_r2d_explicit_local_medium_material_generation_smoke_complete_r2e_material_audit_authorized`,
status `haae_r2e_local_medium_material_audit_package_complete_r2f_medium_experiment_authorized`,
self-test `30/30`). It performs public-only audit with no private root read,
no private material access, and no temporary-directory scan. The audit confirms
task bucket `count_10_to_20`, source fixture bucket `count_21_to_50`, subset
policy `deterministic_public_manifest_prefix_cap_10_to_20`, candidate depth
`count_20`, private row cap `count_le_5000`, total private row bucket
`count_le_5000`, and rank sources `bm25_like/symbol_overlap/rrf_like`. R2E
authorizes only **R2F local medium material experiment** with an operator-supplied
explicit private root, reading existing R2D private material only, and computing
aggregate metrics. There is no new material/candidate generation/retrieval/runtime/source scan/CI/network/scheduler/HAAE/selector/BEA-v1-A/P5/default/method/scaling claim.

**BEA-v1-HAAE-R2F Local Medium Material Experiment** is complete as the first
medium experiment over the existing R2D private material (R2E checkpoint `b166d79`,
R2E status `haae_r2e_local_medium_material_audit_package_complete_r2f_medium_experiment_authorized`,
default status `haae_r2f_unavailable_no_explicit_r2d_private_material_root`, pass
status `haae_r2f_local_medium_material_experiment_complete_r2g_public_audit_authorized`,
self-test `22/22`). Explicit mode used an explicit private material root and
reads existing R2D private material only. It computes aggregate-only metrics for
rank sources `bm25_like/symbol_overlap/rrf_like`: all three have gold-file hit-rate bucket `rate_1`, same-top candidate rate bucket `rate_1`, and top1/top5/top10 buckets `count_10_to_20`. It publishes no path, basename,
filename, task, query, candidate, label, score, hash, snippet, or exact per-task
value. Boundary: no new candidates/retrieval/source scan/OpenLocus/runtime/scheduler/selector/CI/network/provider/default/BEA-v1-A/P5/method/scaling claim.
R2F authorizes only **BEA-v1-HAAE-R2G Public Audit Package**.

**BEA-v1-HAAE-R2G Public Audit Package** is complete as a public-only audit of
the R2F aggregate artifact (R2F checkpoint `1e0c718`, R2F status
`haae_r2f_local_medium_material_experiment_complete_r2g_public_audit_authorized`,
status `haae_r2g_public_audit_package_complete_r2h_next_step_design_authorized`,
self-test `14/14`). It confirms rank-source hit-rate bucket `rate_1`, same-top
candidate rate bucket `rate_1`, and top1/top5/top10 buckets `count_10_to_20`.
This is a medium material experiment only with no method-winner/default/scaling claim.
R2G reads only public artifacts/docs and authorizes only **BEA-v1-HAAE-R2H Next-Step Design Decision**; it does not authorize execution, CI, scale material
generation, runtime/default changes, BEA-v1-A/P5, method-winner claims, scaling
claims, or raw publication.

**BEA-v1-HAAE-R2H Next-Step Design Decision** is complete as a public-only design
decision (R2G checkpoint `cd583d6`, R2G status
`haae_r2g_public_audit_package_complete_r2h_next_step_design_authorized`, status
`haae_r2h_next_step_design_decision_complete_r2i_harder_diversified_material_generation_authorized`,
self-test `11/11`). Diagnosis: `arms_not_separating`; R2H will reject/defer scaling the same R14 medium recipe or CI batch now and selects harder/diversified local material generation. R2I boundary: target 20 tasks, candidate depth 40, private row cap 10000, explicit opt-in local private root, public aggregate-only manifest,
rank sources `bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline`,
and no experiment metrics in R2I. Boundary remains no method/default/scaling claim,
no private read, no material generation in R2H, no execution, no recompute,
no retrieval/source scan/OpenLocus/runtime, no CI/network/provider/clone, and no
scheduler/HAAE/selector. R2H authorizes only **BEA-v1-HAAE-R2I Harder/Diversified Local Material Generation Smoke**.

**BEA-v1-HAAE-R2I Harder/Diversified Local Material Generation Smoke** is implemented
with safe default mode and explicit opt-in private material generation (R2H
checkpoint `3db7366`, R2H status
`haae_r2h_next_step_design_decision_complete_r2i_harder_diversified_material_generation_authorized`,
default status `haae_r2i_unavailable_no_explicit_harder_diversified_material_generation_opt_in`,
pass status `haae_r2i_harder_diversified_local_material_generation_complete_r2j_experiment_authorized`,
self-test `21/21`). explicit opt-in is required. The locked design is target 20 tasks,
candidate depth 40, private row cap 10000, and rank sources
`bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline`.
R2I writes private rows only under an explicit operator root and publishes only an
aggregate public manifest. It computes no experiment metrics in R2I and performs
no old private root read, retrieval/runtime/OpenLocus/source scan outside fixture,
CI/network/provider/clone, scheduler/HAAE/selector, BEA-v1-A/P5/default change,
or method/scaling claim. R2I authorizes only **BEA-v1-HAAE-R2J Harder/Diversified Material Experiment**.

**BEA-v1-HAAE-R2J Harder/Diversified Material Experiment** is complete over the existing R2I private material (R2I checkpoint `16d1349`, R2I status `haae_r2i_harder_diversified_local_material_generation_complete_r2j_experiment_authorized`, default status `haae_r2j_unavailable_no_explicit_r2i_private_material_root`, pass status `haae_r2j_harder_diversified_material_experiment_complete_r2k_public_audit_authorized`, non-separating status `haae_r2j_harder_diversified_material_experiment_complete_no_go_non_separating`, self-test `21/21`). Explicit private material root is required and input is existing R2I material only. R2J publishes aggregate-only metrics for rank sources `bm25_like/symbol_overlap/path_prior/structure_token_overlap/rrf_like/control_baseline`, plus separation diagnostics, with `method_winner_bool=false`. Result: `separation_signal_bool=true`, `rank_spread_bucket=spread_medium`, and `control_baseline_separation_bucket=non_control_better`. Bucket-level signal: `path_prior` reaches top1/top5/top10/top20 buckets `count_10_to_20` with `mrr_high`, while `control_baseline` has top1 bucket `count_0` and `mrr_low`. This is a separation signal, not a method winner/default/scaling claim. Boundary: no method winner/default/scaling claim, no root discovery, no private writes, no candidate/material generation, and no retrieval/runtime/OpenLocus/source scan/CI/network/provider/scheduler/selector. R2J authorizes only **BEA-v1-HAAE-R2K Public Audit Package**.

**BEA-v1-HAAE-R2K Public Audit Package** is complete as a public-only audit/package of the R2J aggregate artifact (R2J checkpoint `71c9a2c`, R2J status `haae_r2j_harder_diversified_material_experiment_complete_r2k_public_audit_authorized`, R2J self-test 21/21, status `haae_r2k_public_audit_package_complete_r2l_next_step_decision_authorized`, self-test `14/14`). It locks separation signal true, `rank_spread_bucket=spread_medium`, `control_baseline_separation_bucket=non_control_better`, `method_winner_bool=false`, path_prior top1/top5/top10/top20 buckets `count_10_to_20` with `mrr_high`, and control_baseline top1 `count_0` with `mrr_low`. The result is framed as a separation signal worth mechanism/robustness follow-up, not method winner/default/scaling claim. R2K authorizes only **BEA-v1-HAAE-R2L Next-Step Decision / Mechanism Preflight** as public design/decision; it does not authorize execution, CI, retrieval, new material generation, runtime/default changes, BEA-v1-A/P5, method-winner claims, scaling claims, or raw publication.

**BEA-v1-HAAE-R2L Next-Step Decision / Mechanism Preflight** is complete as a public-only decision package (R2K checkpoint `99600db`, R2K status `haae_r2k_public_audit_package_complete_r2l_next_step_decision_authorized`, status `haae_r2l_next_step_decision_mechanism_preflight_complete_r2m_mechanism_decomposition_authorized`, self-test `14/14`). Because R2J/R2K produced a separation signal but no method/default/scaling claim, R2L selects mechanism decomposition over existing R2I material; not scale/CI or new material generation yet. R2M requires explicit opt-in private read only and publishes aggregate-only mechanism buckets. R2L authorizes only **BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition**; R2M next only R2N public audit.

**BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition** is complete with default no-private-read mode and explicit opt-in reading of an explicit existing R2I private material root (R2L checkpoint `0dd357e`, R2L status `haae_r2l_next_step_decision_mechanism_preflight_complete_r2m_mechanism_decomposition_authorized`, default status `haae_r2m_unavailable_no_explicit_r2i_private_material_root`, pass status `haae_r2m_path_prior_separation_mechanism_decomposition_complete_r2n_public_audit_authorized`, self-test `19/19`). Public aggregate result: `dominant_mechanism_bucket=path_structure_prior`, `confidence_bucket=medium_high`, extension/language prior supporting, directory depth prior supporting, same-module/path-token overlap supporting, fixture pool contains path cues, and control baseline underfits. Boundary: no method/default/scaling claim, no private writes, no generation/retrieval/runtime/source scan/CI/network/provider/scheduler/selector, and no raw paths/tokens/extensions/filenames/directories/task ids/queries/snippets/labels/exact ranks/scores/hashes/line ranges/per-task values. R2M authorizes only **BEA-v1-HAAE-R2N Public Audit Package**.

**BEA-v1-HAAE-R2N Public Audit Package** is complete as a public-only audit/package of the committed R2M aggregate artifact (R2M checkpoint `7a3d6dc`, R2M status `haae_r2m_path_prior_separation_mechanism_decomposition_complete_r2n_public_audit_authorized`, status `haae_r2n_public_audit_package_complete_r2o_robustness_preflight_design_authorized`, self-test `14/14`). It packages the R2M conclusion `path_structure_prior`, medium_high confidence, fixture path cues + control underfit, and no method winner; this is not method/default/scaling claim. R2N reads only public R2M artifacts/docs and authorizes only **BEA-v1-HAAE-R2O Robustness Preflight Design**, not execution/CI/new material generation yet.

**BEA-v1-HAAE-R2O Robustness Preflight Design** is complete as a public-only design package (R2N checkpoint `a9066d2`, R2N status `haae_r2n_public_audit_package_complete_r2o_robustness_preflight_design_authorized`, status `haae_r2o_robustness_preflight_design_complete_r2p_path_cue_robustness_material_generation_authorized`, self-test `14/14`). It keeps the mechanism context `path_structure_prior` with fixture path cues + control underfit, and selects **BEA-v1-HAAE-R2P Path-Cue Robustness Material Generation** as the next bounded step. R2P contract: local explicit opt-in, private output root, public aggregate-only, target 20 tasks, candidate depth 40, row cap 20000, variants `original/path_scrambled/extension_bucket_preserved/directory_depth_preserved/control_baseline_strengthened`, and no experiment metrics in R2P. R2O itself is not execution/CI/new material generation in R2O and makes no method/default/scaling claim.

**BEA-v1-HAAE-R2P Path-Cue Robustness Material Generation** is implemented with safe default mode and explicit opt-in private material generation (R2O checkpoint `4ffc9eb`, R2O status `haae_r2o_robustness_preflight_design_complete_r2p_path_cue_robustness_material_generation_authorized`, default status `haae_r2p_unavailable_no_explicit_path_cue_robustness_material_generation_opt_in`, pass status `haae_r2p_path_cue_robustness_material_generation_complete_r2q_public_audit_authorized`, self-test `22/22`). Explicit opt-in is required. The locked bounds are target 20 tasks, candidate depth 40, row cap 20000, variants `original/path_scrambled/extension_bucket_preserved/directory_depth_preserved/control_baseline_strengthened`, and rank sources `path_prior/path_scrambled_prior/extension_bucket_prior/directory_depth_prior/control_baseline_strengthened/rrf_variant_fusion`. gold labels private only and ranking policy ignores gold labels. R2P computes no experiment metrics in R2P and authorizes only **BEA-v1-HAAE-R2Q Public Audit Package**.

**BEA-v1-HAAE-R2Q Path-Cue Robustness Material Public Audit Package** is complete as a public-only audit of the committed R2P aggregate artifact (R2P checkpoint `1f721dd`, R2P status `haae_r2p_path_cue_robustness_material_generation_complete_r2q_public_audit_authorized`, status `haae_r2q_public_audit_package_complete_r2r_local_robustness_experiment_authorized`, self-test `18/18`). It confirms explicit opt-in, private write nonzero, target 20, depth 40, 5 variants, 6 rank sources, required schema groups meaningful, gold private only, ranking gold false, no experiment metrics, aggregate-only, root safety pass, and R2O source checkpoint `4ffc9eb`. R2Q authorizes only **BEA-v1-HAAE-R2R Path-Cue Robustness Experiment** over existing R2P private material with an explicit private root; no new material generation/CI/retrieval/runtime/source scan/default/method/scaling.

**BEA-v1-HAAE-R2R Path-Cue Robustness Experiment** is complete as an explicit private-material-root experiment (R2Q checkpoint `a9f5477`, R2Q status `haae_r2q_public_audit_package_complete_r2r_local_robustness_experiment_authorized`, default status `haae_r2r_unavailable_no_explicit_r2p_private_material_root`, result status `haae_r2r_path_cue_robustness_experiment_complete_r2s_public_audit_authorized_artifact_likely`, self-test `18/18`). It reads existing R2P material only and computes aggregate-only metrics by variant×rank_source plus path_prior robustness. Result: `path_cue_artifact_likely`; `path_prior_original_top10_bucket` and top20 are `count_11_to_20`, but path-scrambled, extension-preserved, depth-preserved, and strengthened-control drops are also `count_11_to_20`, with `variant_spread_bucket=spread_high`. Boundary: no method/default/scaling. R2R authorizes only **BEA-v1-HAAE-R2S Public Audit Package**.

**BEA-v1-HAAE-R2S Path-Cue Robustness Experiment Public Audit Package** is complete as a public-only audit/package (R2R checkpoint `7efc348`, R2R status `haae_r2r_path_cue_robustness_experiment_complete_r2s_public_audit_authorized_artifact_likely`, status `haae_r2s_path_cue_robustness_experiment_public_audit_package_complete_r2t_non_path_cue_pivot_decision_authorized`, self-test `12/12`). It confirms self-test 30/30, `path_cue_artifact_likely`, original path_prior top10/top20 count_11_to_20, all perturbation drop buckets count_11_to_20, variant_spread_bucket spread_high, and privacy/aggregate-only boundary. R2S is not execution/generation/CI and authorizes only **BEA-v1-HAAE-R2T Non-Path-Cue Pivot Decision**; no execution, CI, retrieval, new material generation, default/runtime, method winner, or scaling claim is authorized.

**BEA-v1-HAAE-R2T Non-Path-Cue Pivot Decision** is complete as a public-only design/decision package (R2S checkpoint `8d8d19c`, R2S status `haae_r2s_path_cue_robustness_experiment_public_audit_package_complete_r2t_non_path_cue_pivot_decision_authorized`, status `haae_r2t_non_path_cue_pivot_decision_complete_r2u_content_identifier_material_generation_authorized`, self-test `14/14`). Using the `path_cue_artifact_likely` result, it marks scale current path-prior rejected/deferred, more path-cue ablations deferred, CI batch deferred, and content_identifier selected. Next phase is **BEA-v1-HAAE-R2U Content-Identifier Evidence Material Generation Smoke** with target 20, candidate depth 40, row cap 20000, explicit opt-in, private output root, and public aggregate-only output. R2T is not execution/generation/CI and makes no method/default/scaling claim.

**BEA-v1-HAAE-R2U Content-Identifier Evidence Material Generation Smoke** is complete with safe default mode and explicit opt-in private material generation (R2T checkpoint `bc58cf7`, R2T status `haae_r2t_non_path_cue_pivot_decision_complete_r2u_content_identifier_material_generation_authorized`, default status `haae_r2u_unavailable_no_explicit_content_identifier_material_generation_opt_in`, pass status `haae_r2u_content_identifier_material_generation_complete_r2v_public_audit_authorized`, self-test `25/25`). The explicit run used target 20, candidate depth 40, row cap 20000, explicit opt-in, and rank sources `query_identifier_overlap/symbol_name_overlap/content_snippet_overlap/identifier_normalized_bm25_like/hard_negative_quality_control/content_identifier_fusion/control_baseline`. Policy: no path tokens/extensions/directories for ranking, gold private only, gold labels not used for ranking, and public aggregate-only output. R2U authorizes only **BEA-v1-HAAE-R2V Content-Identifier Material Public Audit Package**.

**BEA-v1-HAAE-R2V Content-Identifier Material Public Audit Package** is complete as a public-only audit of the committed R2U aggregate artifact (R2U checkpoint `bb95f80`, R2U status `haae_r2u_content_identifier_material_generation_complete_r2v_public_audit_authorized`, status `haae_r2v_content_identifier_material_public_audit_package_complete_r2w_material_experiment_authorized`, self-test `14/14`). It locks target 20, depth 40, row cap 20000, seven rank sources, no path tokens, no gold ranking, no metrics, public aggregate-only, and privacy/no raw leak boundary. R2V authorizes only **BEA-v1-HAAE-R2W Content-Identifier Material Experiment** over existing R2U private material with explicit private root; no new material generation/retrieval/runtime/source scan/CI/network/provider/scheduler/selector/BEA-v1-A/P5/default/method/scaling/raw publication.

**BEA-v1-HAAE-R2W Content-Identifier Material Experiment** is implemented with safe default mode and explicit existing-R2U-private-material experiment support (R2V checkpoint `b8522de`, R2V status `haae_r2v_content_identifier_material_public_audit_package_complete_r2w_material_experiment_authorized`, R2U source checkpoint bb95f80, default status `haae_r2w_unavailable_no_explicit_r2u_private_material_root`, pass status `haae_r2w_content_identifier_material_experiment_complete_r2x_public_audit_authorized_signal_present` or `haae_r2w_content_identifier_material_experiment_complete_r2x_public_audit_authorized_weak_or_no_signal`, self-test `25/25`). Explicit mode reads existing R2U material only and computes aggregate-only metrics for seven rank sources. Material context is `query_derived_identifier_decoys`, `real_file_candidate_evidence_bool=false`, `file_retrieval_claim_bool=false`, and `method_winner_claim_bool=false`. Boundary: no generation/candidate creation/retrieval/runtime/source scan/CI/network/provider/scheduler/selector/default/method/scaling. R2W authorizes only **BEA-v1-HAAE-R2X Content-Identifier Material Experiment Public Audit Package**.

The previous package phase was **BEA-v1-N10EM: Difference-Aware Winner Public Replication Package**:

```text
status: difference_aware_winner_public_replication_package_complete_n10en_authorized
self-test: 11 / 11
forbidden scan: pass
N10EK winner top10/top20/top50/top100: 13 / 16 / 20 / 26
N10EL audit top10/top20/top50/top100: 13 / 16 / 20 / 26
chain consistent: true
gold used for policy: false
old-pool membership used for policy: true
full/guard outcome membership used for policy: false
next allowed phase: BEA-v1-N10EN Broader-Sample CI Validation Canary
```

N10EM packages the N10EK/N10EL public chain: the fixed difference-aware rule
(`top5_novel_candidate_item_count >= 4` selects guarded, otherwise full) reached
`13/16/20/26`, and the independent audit reproduced the exact same counts with
zero lost baseline top10 hits. The only authorized next step is broader-sample / CI
validation canary. N10EM itself remains public-only/no-execution, while its handoff
explicitly authorizes N10EN-only bounded public CI clone/build/search, temporary
candidate materialization, score-phase labels, and sanitized aggregate upload. No
runtime/default, production retrieval change, provider network, method/downstream,
or heldout/generalization claim is authorized.

**BEA-v1-N10EN: Difference-Aware Winner Broader-Sample CI Validation Canary**
has now run as the first real bounded public CI canary for the frozen rule:

```text
status: difference_aware_winner_ci_canary_outcome_regression
CI run: 28449370879
head sha: 9d0da19
forbidden scan: pass
N10EM gate: authorized (handoff scoped to N10EN public CI only)
repo_count: 2
public_task_count: 80
task_with_candidates_count: 58
scored_task_count: 58
task_with_gold_count: 40
baseline top10/top20/top50/top100: 39 / 40 / 40 / 40
full novel-first:                 37 / 40 / 40 / 40 (lost baseline top10: 2)
guarded top5:                     39 / 40 / 40 / 40 (lost baseline top10: 0)
diffaware:                        37 / 40 / 40 / 40 (lost baseline top10: 2)
selected arms: full=49, guarded=9
citation validity: 3636 / 3636
```

The workflow remains `workflow_dispatch` only and `enable_public_github_network`
still defaults to `false`; the safe default emits a fail-closed report with no
clone/build/search. The successful CI run above explicitly enabled public GitHub
network, cloned manifest-listed public repos only (reusing
`ci_clone_and_lock_repo.py`), generates public tasks with `--no-labels` first
(reusing `ci_generate_tasks.py`), applies the four frozen transforms (baseline raw
BM25, full novel-first, guarded keep-top5-then-distinct-novel-fill, diffaware
guarded iff top5 novel candidate item count >= 4 else full) inside the dedicated
N10EN helper rather than by bending `ci_run_strategy_matrix`, fixes RUN orders,
then generates score-phase labels and scores the fixed orders (labels/gold for
aggregate scoring only, never policy). The uploaded report is aggregate-only and
scanner-validated; CI fails on contract/privacy/build/clone/task failures but not
on outcome regression. N10EN is an effective broader-sample negative for the
N10EK same-row winner: the difference-aware switch regressed relative to baseline
on this public CI canary. The next phase is N10EO failure analysis, not promotion.

**BEA-v1-N10EO: Difference-Aware CI Regression Failure Analysis** explains why
the N10EN canary regressed:

```text
status: n10eo_failure_analysis_pass_mechanism_identified
self-test: 50 / 50
forbidden scan: pass
N10EN source locked: true (canary run 28449370879)
diagnostic_source: private_diagnostic_rerun
primary mechanism: novel_first_displaced_baseline_gold_from_top10
```

N10EO locks the N10EN aggregate artifact, then uses a matching private
diagnostic rerun rather than inferring per-task mechanisms from aggregate counts.
It emits aggregate-bucket-only diagnostics. The regression mechanism is
identified: diffaware chose `full` on 49 tasks (top5_novel < 4); on 2 of those,
`full`'s novel-first reordering displaced baseline gold already at ranks 1-5 down
to ranks 11-20. `guard` would have preserved both. The lost-baseline mechanism
buckets confirm: `novel_first_displaced = 2`,
`baseline_gold_rank_1_to_5_displaced = 2`, `candidate_available_beyond_top10 =
2`, all other mechanisms 0. No per-task candidates/labels/queries/paths/ranks
are published. N10EO does not authorize runtime/default, method-winner,
selector/reranker, or any change to the frozen rule.

N10EO authorizes only **BEA-v1-N10EP Design-Only Threshold-Misfire Mechanism
Response**: aggregate-bucket mechanism analysis/design. It does not authorize
threshold tuning, new policy experiments, frozen-rule changes, promotion of
guard/full/diffaware, runtime/default changes, method-winner claims,
downstream/scaled retrieval, or raw diagnostic publication.

**BEA-v1-N10EP: Design-Only Threshold-Misfire Mechanism Response** is a
public-artifact-only design packaging phase after the N10EO checkpoint
`6f8eeda`. It performs **no execution** and reads no private diagnostic inputs:

```text
status: n10ep_design_response_pass_n10eq_authorized
self-test: 69 / 69
forbidden scan: pass
design-only: true
aggregate-buckets-only: true
N10EO source locked: true (checkpoint 6f8eeda)
mechanism: novel_first_displaced_baseline_gold_from_top10 (low-novelty bucket loss = 2)
next allowed phase: BEA-v1-N10EQ Score/Guard Safety Probe Design
```

N10EP re-expresses the N10EO aggregate values
(baseline/full/guard/diffaware top10 `39/37/39/37`; full_lost `2`, guard_lost
`0`, diffaware_lost `2`; `guard_better_than_full = 2`;
`full_lost_guard_preserved = 2`; `baseline_gold_rank_1_to_5_displaced = 2`;
`candidate_available_beyond_top10 = 2`; `low_novelty_bucket_loss = 2`) as a
design-only response. It packages three design options: the **N10EQ** score/guard
safety probe design (authorized for the next phase, design-only), the **N10ER**
public CI small variant design (packaged but not authorized under the
conservative default), and `stop_design_only_insufficient`. Six risk controls
are recorded (aggregate overinterpretation from two cases, hindsight threshold
tuning, guard promotion from two cases, public CI variant as method winner,
private diagnostic leakage, runtime/default creep) — all controlled. The
conservative stop/go authorizes only the N10EQ design with **no execution**:
all execution, threshold-tuning, promotion, runtime/default, method-winner, and
CI-variant-execution fields are `false`. N10EP reads only public aggregate
artifacts (N10EO/N10EN/N10EM); no private diagnostic rerun, raw candidates,
orders, labels, paths, or per-task diagnostics are read or published.

**BEA-v1-N10EQ: Score/Guard Safety Probe Design** is a public-artifact-only
design phase after the N10EP checkpoint `0a54b49`. It *designs* (does not
execute) a forward safety probe:

```text
status: n10eq_score_guard_safety_probe_design_pass_n10er_contract_authorized
self-test: 112 / 112
forbidden scan: pass
design-only: true
aggregate-buckets-only: true
n10er_contract_authorized_bool: true
n10er_execution_authorized_bool: false
next allowed phase: BEA-v1-N10ER Bounded Public CI Score/Guard Safety Probe
```

N10EQ re-locks the N10EO mechanism from public aggregates (checkpoint
`6f8eeda`, primary mechanism `novel_first_displaced_baseline_gold_from_top10`,
2 misfires in the low-novelty 0_to_2 bucket) and designs 7 forward probe
features (`top5_novel_candidate_item_count_bucket`, `baseline_prefix_strength`,
`baseline_gold_proxy`, `full_displacement_risk`, `guard_preservation_ref`,
`candidate_available_beyond_top10`, `arm_selection`). Every feature derives
from public aggregate buckets only — N10EQ reads no per-task candidates/labels/
paths/ranks/gold and no threshold is tuned. The future N10ER input contract is
practical: if separately authorized, N10ER may privately produce/read bounded-CI
orders, candidates, retrieval output, per-task diagnostic state, and score-phase
labels after orders are frozen. Those remain private execution-time inputs; the
public output contract emits aggregate-bucket safety flags only (no raw orders,
candidates, labels, paths, queries, tasks, repos, exact ranks, method-winner
claim, or runtime/default change). Six N10ER pass/fail gates are designed
(private execution inputs with aggregate-only publication, aggregate-only output,
no threshold tuning, no method-winner, no runtime/default, held-out public reproducibility check) —
all evaluated on aggregate buckets with gold_used_for_policy_bool=false. Seven
risk controls are recorded (aggregate overinterpretation from two cases,
hindsight threshold tuning, guard promotion from two cases, private diagnostic
leakage, runtime/default creep, N10ER execution creep, feature proxy as gold)
— all controlled. The conservative stop/go authorizes only the N10ER contract
handoff: `n10er_contract_authorized_bool=true` but
`n10er_execution_authorized_bool=false`. All execution, threshold-tuning,
promotion, runtime/default, method-winner, CI-variant-execution, and network
fields are `false`. N10EQ reads only public aggregate artifacts; no private
diagnostic inputs are read.

**BEA-v1-N10ER: Bounded Public CI Score/Guard Safety Probe** has run as a real
bounded public CI safety probe after the N10EQ checkpoint `7963831`:

```text
status: n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized
CI run: 28457213423
self-test: 53 / 53
forbidden scan: pass
public_task_count: 80
scored_task_count: 60
task_with_gold_count: 40
baseline top10/top20/top50/top100: 37 / 39 / 40 / 40
full novel-first:                 36 / 39 / 40 / 40 (lost baseline top10: 1)
guarded top5:                     38 / 39 / 40 / 40 (lost baseline top10: 0)
diffaware:                        37 / 39 / 40 / 40 (lost baseline top10: 1)
risk bucket task_count: 26
risk bucket full/guard/diffaware lost baseline: 0 / 0 / 0
signal reproduced: false
n10es_audit_authorized_bool: true (stop/go)
next allowed phase: BEA-v1-N10ES Bounded Public CI Safety Probe Audit
```

When network is explicitly enabled, N10ER reuses N10EN retrieval/order plumbing
verbatim (frozen transforms, clone-and-lock, generate-tasks, OpenLocus search)
**without** mutating N10EN semantics/artifacts, runs a held-out
manifest-listed public sample (`canary_small_heldout`/`canary_medium_heldout`,
small `80/50/30`, medium `160/100/60`; held-out via
manifest-listed repos after the N10EN reference repo prefix, with a private
overlap check that publishes only overlap count/bucket aggregates), fixes RUN-phase orders before generating score-phase labels
(gold for aggregate scoring only, never policy), computes the seven
N10EQ-designed safety features as aggregate buckets only
(top5_novelty_bucket, baseline_prefix_strength, baseline_gold_proxy,
full_displacement_risk, guard_preservation_ref, candidate_available_beyond_top10,
arm_selection), and uploads only a sanitized aggregate-only report. The
published artifact includes `n10eq_source_lock_records`,
`execution_boundary_records` (`n10en_artifact_mutated_bool=false`,
`n10en_semantics_reused_verbatim_bool=true`,
`n10en_private_task_ids_read_bool=false`, `frozen_rule_changed_bool=false`,
`threshold_tuned_bool=false`, `public_artifact_aggregate_only_bool=true`),
`sample_records`, `arm_aggregate_records`, `safety_feature_bucket_records`,
`safety_signal_aggregate_records`, `pass_fail_gate_records` (9 gates, all aggregate,
`gate_uses_gold_for_policy_bool=false`), `claim_boundary_records`, and
`stop_go_records` authorizing only N10ES audit. The safety signal did not
reproduce on this held-out public CI sample: the risk bucket was large enough
(`26`) but full/guard/diffaware all lost `0` baseline hits inside that bucket.
This is a valid research negative, not CI failure. It does not authorize N10ER re-run, threshold tuning, promotion,
runtime/default, method-winner, downstream/scaled retrieval, or CI variant
execution.

**BEA-v1-N10ES: Public Safety Probe Audit/Package** is a public-only,
no-execution audit of the N10ER result after the `c8fd353` checkpoint:

```text
status: n10es_public_safety_probe_audit_package_complete_n10et_authorized
self-test: 37 / 37
forbidden scan: pass
private input reads: 0
retrieval executions: 0
recomputes: 0
CI reruns: 0
n10er source locked: true (checkpoint c8fd353, CI run 28457213423)
next allowed phase: BEA-v1-N10ET Public Safety Probe Design/Decision
```

N10ES reads **only** the N10ER public aggregate report (+ N10ER
evaluator/workflow for schema/status validation only) and git metadata; it
performs no CI rerun, retrieval, recompute, clone, build, or search, and reads
no private directories, CI raw logs, repo clones, raw
candidates/orders/labels/paths/queries/tasks/repos, per-task diagnostics, or
N10EO private rerun data. It locks the N10ER result (status
`n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized`, sample
`80/60/40`, `overlap_zero`, citation `7772/7772`, baseline `37/39/40/40`, full
`36/39/40/40` lost `1`, guard `38/39/40/40` lost `0`, diffaware `37/39/40/40`
lost `1`, risk bucket `task_count=26`, losses `0/0/0`,
`guard_would_preserve_full_loss_count=0`), re-expresses those aggregates as
`n10er_metric_audit_records` (`recomputed_bool=false`, all
`metric_match_bool=true`), and records the interpretation: the risk bucket was
sufficient but full/guard/diffaware lost `0/0/0` inside it and
`guard_would_preserve_full_loss_count=0`, so the safety signal did not
reproduce — a valid research negative, not CI failure. The published artifact
includes `n10er_source_lock_records`, `n10er_metric_audit_records`,
`n10er_arm_audit_records`, `interpretation_records`, `public_package_records`,
`claim_boundary_records`, `pass_fail_gate_records` (13 audit gates, including
N10ER next-phase and public readback checks, all
aggregate, `gate_uses_gold_for_policy_bool=false`,
`gate_performs_ci_rerun_bool=false`, `gate_reads_private_input_bool=false`),
and `stop_go_records`. The conservative stop/go authorizes **only** the N10ET
public-only design/decision handoff (`n10et_design_decision_authorized_bool=true`);
all execution, rerun, retrieval, recompute, tuning, promotion, runtime/default,
method-winner, downstream/scaled retrieval, raw diagnostic publication, CI
variant execution, selector/reranker, provider/model network, and network-run
fields are `false`. See `docs/en/bea-v1-n10es-public-safety-probe-audit-package.md`.

N10ES also explicitly audits N10ER's stop/go `next_allowed_phase` and public
readback consistency across README, EN/ZH N10ER docs, and EN/ZH current
conclusions.

**BEA-v1-N10ET: Public Safety Probe Design/Decision** is the public-only
close-out design/decision phase for the N10E safety-probe branch, after the
N10ES checkpoint `8c04a0a`:

```text
status: n10et_public_safety_probe_design_decision_complete_haae_r0_authorized
self-test: 74 / 74
forbidden scan: pass
private input reads: 0
retrieval executions: 0
recomputes: 0
CI reruns: 0
candidate generations: 0
n10es / n10er source locked: true (checkpoint 8c04a0a / c8fd353, CI run 28457213423)
next allowed phase: BEA-v1-HAAE-R0 Hierarchical Actionable Evidence Acquisition
                   Route Design / Schema Preflight
```

N10ET reads **only** the N10ES + N10ER public aggregate reports and public
docs/current-conclusions/research-log/summary/README + git metadata; it performs
no CI rerun, retrieval, recompute, candidate generation, clone, build, or
search, and reads no private directories, CI raw logs, repo clones, raw
candidates/orders/labels/paths/queries/tasks/repos, per-task diagnostics, or
N10EO private rerun data. It locks the N10ES/N10ER public facts (CI run
`28457213423`, status
`n10er_safety_probe_complete_no_signal_reproduced_n10es_authorized` and
`n10es_public_safety_probe_audit_package_complete_n10et_authorized`, sample
`80/60/40`, `overlap_zero`, citation `7772/7772`, baseline `37/39/40/40`, full
`36/39/40/40` lost `1`, guard `38/39/40/40` lost `0`, diffaware `37/39/40/40`
lost `1`, risk bucket `task_count=26`, losses `0/0/0`,
`guard_would_preserve_full_loss_count=0`), records the close-out decisions
(N10E/difference-aware remains a local same-source hypothesis; N10ER/N10ES are
a valid public held-out negative; no guard/full/diffaware promotion, no
threshold tuning, no N10ER rerun), and designs + authorizes **only** the next
route: **BEA-v1-HAAE-R0 — Hierarchical Actionable Evidence Acquisition Route
Design / Schema Preflight**. HAAE-R0 is explicitly **not** BEA-v1-A, not
selector-only, not selector/reranker execution, not P5, and not a
runtime/default promotion. The published artifact includes
`n10es_source_lock_records`, `decision_records`, `haae_r0_route_records`,
`risk_control_records`, `public_package_records`, `claim_boundary_records`,
`pass_fail_gate_records` (20 audit gates, including N10ES next-phase, public
readback, and HAAE-R0 non-identity gates, all aggregate,
`gate_uses_gold_for_policy_bool=false`, `gate_performs_ci_rerun_bool=false`,
`gate_reads_private_input_bool=false`), and `stop_go_records`. The conservative
stop/go authorizes **only** the HAAE-R0 design/schema-preflight handoff
(`haae_r0_design_only_schema_preflight_authorized_bool=true`,
`haae_r0_execution_authorized_bool=false`); all execution, rerun, retrieval,
recompute, candidate generation, tuning, promotion, runtime/default,
method-winner, downstream/scaled retrieval, raw diagnostic publication, CI
variant execution, selector/reranker, BEA-v1-A, P5, provider/model network,
and network-run fields are `false`. See
`docs/en/bea-v1-n10et-public-safety-probe-design-decision.md`.

**BEA-v1-HAAE-R0: Hierarchical Actionable Evidence Acquisition Route Design /
Schema Preflight** is the public-only, design-only schema preflight for the
next acquisition route, opened by the N10ET close-out (checkpoint `26d817e`):

```text
status: haae_r0_design_schema_preflight_complete_haae_r1_authorized
self-test: 132 / 132
forbidden scan: pass
private input reads: 0
retrieval executions: 0
recomputes: 0
CI reruns: 0
candidate generations: 0
arm scorings: 0
openlocus executions: 0
n10et source locked: true (checkpoint 26d817e, status
  n10et_public_safety_probe_design_decision_complete_haae_r0_authorized)
next allowed phase: BEA-v1-HAAE-R1 Unified Private Trace Schema Feasibility Inventory
```

HAAE-R0 reads **only** the N10ET public aggregate report and public
docs/current-conclusions/research-log/summary/README + git metadata; it performs
no CI rerun, retrieval, recompute, candidate generation, arm scoring, OpenLocus
execution, clone, build, or search, and reads no private directories, CI raw
logs, repo clones, raw candidates/orders/labels/paths/queries/tasks/repos, or
per-task diagnostics. It locks the N10ET public facts (checkpoint `26d817e`,
status `n10et_public_safety_probe_design_decision_complete_haae_r0_authorized`,
HAAE-R0 authorized true, HAAE-R0 execution false, BEA-v1-A false), and designs a
machine-readable, non-empty control-plane: `route_architecture_records` (4
hierarchical layers — source_acquisition, rank_pack_depth_to_head,
span_projection, scheduler_operating_point, each preserving `EvidenceCore` and
abstaining when current-source evidence is unavailable),
`unified_private_schema_spec_records` (10 private-root-only,
aggregate-bucket-only groups), `public_aggregation_contract_records` (4
aggregations), `arm_spec_records` (BM25_same_budget, RRF_same_budget,
BEA_v0.3_frozen, V1_sched_span, V1_sched_span_rank — same budget, no execution,
no scoring, no tuning in HAAE-R0), `metric_spec_records` (6 aggregate metrics),
`heldout_protocol_records` (overlap_zero, no gold-for-policy, no split
materialized), `stop_rule_records` (4 abstain rules preserving EvidenceCore),
`synthetic_validator_records` (an embedded 4-task synthetic fixture that
validates all contracts in-process — not real data, not replay, not retrieval,
not candidate generation), and `haae_r1_contract_records` (the HAAE-R1
contract). The published artifact also includes `source_lock_records`,
`risk_control_records`, `public_package_records`, `claim_boundary_records`,
`pass_fail_gate_records` (27 audit gates, including N10ET source-lock,
concrete-schema/arm/metric, synthetic-validator, public readback, and HAAE-R0
non-identity gates, all aggregate, `gate_uses_gold_for_policy_bool=false`,
`gate_performs_ci_rerun_bool=false`, `gate_reads_private_input_bool=false`), and
`stop_go_records`. The conservative stop/go authorizes **only** the HAAE-R1
Unified Private Trace Schema Feasibility Inventory handoff
(`haae_r1_unified_private_trace_schema_feasibility_inventory_authorized_bool=true`,
`haae_r1_execution_authorized_bool=false`,
`haae_r1_replay_authorized_bool=false`,
`haae_r1_scoring_authorized_bool=false`,
`haae_r1_retrieval_authorized_bool=false`,
`haae_r1_candidate_generation_authorized_bool=false`); all execution, rerun,
retrieval, recompute, candidate generation, arm scoring, OpenLocus execution,
tuning, promotion, runtime/default, method-winner, downstream/scaled retrieval,
raw diagnostic publication, CI variant execution, selector/reranker, BEA-v1-A,
P5, provider/model network, and network-run fields are `false`. HAAE-R0 is
explicitly **not** BEA-v1-A, not selector-only, not selector/reranker
execution, not P5, and not a runtime/default promotion. See
`docs/en/bea-v1-haae-r0-hierarchical-actionable-evidence-acquisition-design-schema-preflight.md`.

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

N10CF packages the N10CE refinement publicly without private reads or recompute.
It confirms `short_only_before75_after225` is the best short-span-gated frontier
point (`24/30`) but not the global same-source best (`pm200` remains `25/30`). It
authorizes only N10CG fixed/predeclared observable-rule follow-up on the gap or
cheaper preservation of `24/30`.

N10CG tests 12 fixed observable hybrid span-shape rules using only original span
length and candidate position buckets. Two variants recover the pm200 top10 and
exceed its top20 at lower cost: `short75_225_top3_all_pm200` reaches 25/31 at
cost10/cost20 3300/6300, and `short75_225_top5_all_pm200` reaches 25/31 at
3500/6500. It authorizes only N10CH public audit/package.

N10CH packages the N10CG positive hybrid result publicly without private reads or
recompute. It confirms `short75_225_top3_all_pm200` and
`short75_225_top5_all_pm200` recover pm200 at lower cost, while `top10` all-pm200
is not counted as a success because top10 cost is not below pm200. It authorizes
only N10CI independent recompute or adapter smoke for `short75_225_top3_all_pm200`.

N10CI independently recomputes `short75_225_top3_all_pm200` without importing or
calling N10CG code. It matches N10CG/N10CH exactly: 25/31 at cost10/cost20
3300/6300, with 0 lost short75/225 hits and unchanged candidate pool/order. It
authorizes only N10CJ public replication package.

N10CJ packages the N10CG/N10CH/N10CI winning-hybrid chain publicly without private
reads or recompute. It confirms the `short75_225_top3_all_pm200` result and the
independent recompute match, and authorizes only N10CK default-off adapter smoke
for the winning hybrid.

N10CK uses the existing default-off eval-only span-window adapter path to reproduce
`short75_225_top3_all_pm200`: 25/31 at cost10/cost20 3300/6300, with 0 lost
short75/225 hits and unchanged candidate pool/order. It does not modify runtime
defaults or hook existing validated evaluators, and authorizes only N10CL public
adapter-smoke package.

N10CL packages the N10CK adapter smoke publicly without private reads or recompute.
It confirms the default-off adapter/helper path reproduced the winning hybrid,
that default/runtime settings and existing evaluator hooks remain unchanged, and
authorizes only N10CM next-step decision between continued mechanism exploration
and a formal default-off variant evaluator.

N10CM continues with a same-source fixed-variant refinement sweep of the winning
hybrid. It finds one lower-cost preservation: `short75_225_top2_all_pm200`
preserves 25/31 at cost10/cost20 3200/6200, saving 100/100 versus the top3 pm200
winning rule. No variant improves beyond 25/31. This authorizes only N10CN public
audit/package.

N10CN packages the N10CM result publicly without private reads or recompute. It
confirms `short75_225_top2_all_pm200` preserves 25/31 at lower cost and authorizes
only a default-off adapter smoke for that refined hybrid.

N10CO uses the existing default-off eval-only adapter/helper path to reproduce the
refined hybrid `short75_225_top2_all_pm200`: 25/31 at cost10/cost20 3200/6200,
0 lost winning top10 hits, file-hit top10 count 34, and unchanged candidate
pool/order. It does not enable runtime/default behavior or hook existing
evaluators, and authorizes only N10CP public adapter-smoke package.

N10CP packages the N10CO adapter smoke publicly without private reads or recompute.
It confirms the refined hybrid aggregate, the default-off adapter boundary, and no
existing evaluator/runtime/retrieval/selector hook. It authorizes only N10CQ
next-step decision between continued cost/quality exploration and a formal
default-off variant evaluator for the refined hybrid.

N10CQ decomposes the refined hybrid mechanism directly. It shows top2 all-span
pm200 recovers exactly one top10 case over top1, top3 adds no further top10 cases,
and the remaining refined-hybrid top10 misses are mostly file-not-in-top10. It
authorizes only N10CR mechanism-guided refined-hybrid sweep over fixed variants
derived from N10CQ.

N10CR runs that mechanism-guided local saturation sweep. Contrary to the expected
possible saturation outcome, `top2_pm300_short75_225` improves the refined anchor
from 25/31 to 26/32 at cost10/cost20 3600/6600, without changing candidate order
or adding candidates. Local span-window repair is therefore not saturated yet,
although the largest remaining blocker is still rank/file reach (`file_not_in_top10`
remains 167). N10CR authorizes only N10CS public package.

N10CS packages N10CR publicly without private reads or recompute. It confirms the
positive local result, `local_window_not_saturated`, residual same-file/no-span
overlap reduced from 9 to 8, and no rank/file pivot authorization from N10CR. It
authorizes only N10CT exploration around `top2_pm300_short75_225` under a future
oracle-scoped contract.

N10CT runs the top2 override window neighborhood sweep over exactly nine pm values
from pm200 through pm400. It finds pm275 is the minimum tested window preserving
the pm300 26/32 result at lower cost (3500/6500), while pm400 improves to 27/33
at cost10/cost20 4000/7000. Candidate pool/order remains unchanged, and N10CT
authorizes only N10CU public package.

N10CU packages the N10CT neighborhood publicly without private reads or recompute.
It confirms pm275 as the minimal tested 26/32-preserving point, pm400 as a new
27/33 same-source proxy improvement, and no candidate pool/order changes. It
authorizes only N10CV follow-up around the pm400 gain under a future oracle scope.

N10CV decomposes the pm400 marginal gain over exactly pm275/pm300/pm400. pm400
adds one top10 and one top20 case versus pm300; the new case is a top2 override,
same-file before-gold, near-boundary (51-100 bucket) recovery. Remaining pm400
misses still include 7 same-file/no-span and 12 span-beyond-top10 cases, so N10CV
authorizes only N10CW high-window neighborhood exploration.

N10CW runs that high-window neighborhood sweep over exactly pm300/350/400/450/500/
600/800/1000. Higher top2 windows continue improving the same-source proxy: pm450
reaches 28/34, pm800 reaches 29/35, and pm1000 reaches 30/36. Local window
saturation remains false, and N10CW authorizes only N10CX public package.

N10CX packages the N10CW high-window sweep publicly without private reads or
recompute. It confirms the 8 fixed variants, pm1000 maximum 30/36, remaining
pm1000 misses (file-not-in-top10 167, same-file/no-span 4, span-beyond-top10 12),
and no top3/medium-long gates. It authorizes only N10CY next mechanism decision.

N10CY decomposes the pm400→pm800→pm1000 high-window gains over the same scoped N1
rows. pm800 adds +2/+2 over pm400; pm1000 adds +1/+1 over pm800; pm1000 totals
30/36 at cost10/cost20 6400/9400. The new cases are still same-file boundary
expansions, while the dominant residual remains file-not-in-top10. N10CY
authorizes only N10CZ oracle-scoped next exploration decision.

N10CZ runs the top2 local-window upper-bound smoke. Larger top2 windows pm1500,
pm2000, and pm5000 do not improve beyond pm1000's 30/36, and the top2 file-extent
proxy underperforms at 22/29. The local-window family is saturated under this
upper-bound test and file reach dominates the residual. N10CZ authorizes only
N10DA public package; it does not itself authorize rank/file experiments.

N10DA packages N10CZ publicly without private reads or recompute. It locks the
conclusion that the local pm-growth line should stop: pm1000 and larger windows
remain 30/36, the file-extent proxy is worse at 22/29, and the remaining misses
are dominated by file-not-in-top10. N10DA authorizes only N10DB rank/file reach
branch scoping or experiment as decided by oracle.

N10DB scopes gold-free rank/file-reach policy fields on the same N1 span rows. It
finds ordered `p4_evidence`, private candidate file identifiers, sufficient pool
length, and substantial duplicate-file pressure in top10/top20 buckets. It does
not execute any policy outcomes. It selects `file_dedup_distinct_file_packing` and
authorizes only N10DC distinct-file packing smoke.

N10DC executes that distinct-file packing smoke over the same scoped N1 rows and
same candidate pool. One-file-per-file packing improves top10 file reach from 14 to 19 and top10 span from
13 to 16, but it loses 1 baseline top10 span hit. The top10-only version reaches
file/span top20 20/18; the top20-then-top10 version exposes more top20 reach at
47/24. `max_per_file_2_top10` is the safer zero-loss variant: file top10/top20
16/19 and span top10/top20 15/17. Candidate
generation, materialization, addition, and removal remain zero. N10DC authorizes
only N10DD public package.

N10DD packages the corrected N10DC results publicly without private reads or
recompute. It distinguishes the aggressive one-file-per-file tradeoff (higher
file/top20 reach but 1 baseline span regression) from the conservative
`max_per_file_2_top10` tradeoff (smaller +2/+2 top10 file/span gain with zero
baseline span regression). N10DD authorizes only N10DE regression-vs-zero-loss
mechanism decomposition.

N10DE decomposes that tradeoff over the same scoped rows: aggressive distinct-file
packing gains more by pulling rank-11-20 evidence into top10, but strict file
uniqueness displaces one rank-1-10 span hit; max-per-file-2 preserves that case.
N10DF then tests fixed hybrid packing variants. `prefix7_then_distinct_fill_top10`
matches the aggressive top10 span count of 16 while avoiding the single baseline
span regression; `prefix5` also reaches 16 but keeps the regression. N10DG packages
N10DF publicly as a promising top10-safe packing hybrid, not a default winner,
because prefix7 does not repair top20 reach (17/19 vs aggressive 24/47). N10DG
authorizes only N10DH under the next oracle contract.

N10DH combines fixed packing with span-window projection over the same scoped rows in the N10T best-order setting, not the N10DC original-order anchor.
Top2 projection is computed after the fixed packing order. Prefix7 + short75/top2
pm1000 matches window-only 30/36 but does not improve it; the aggressive reference
also stays 30/36 and remains labeled `aggressive_reference_not_safe_default`. The
interpretation is `packing_does_not_improve_n10t_window_strategy`: once N10T order already gives file reach 34/44, this packing layer adds no further window-strategy gain. N10DH authorizes only N10DI public package.

N10DI packages N10DH publicly without private reads or recompute. It validates the
scope as `n10t_best_order_setting`, with `original_order_packing_anchor_used_bool=false`
and `n10dc_original_order_result_reused_as_anchor_bool=false`. It preserves the
boundary that N10DF prefix7 remains top10-safe in the original-order packing
setting, while N10DH does not show packing improvement over the N10T window
strategy. N10DI authorizes only N10DJ under a future oracle-scoped rank/file-reach
empirical contract.

N10DJ runs that oracle-scoped same-source rank/file-reach smoke from the N10T-best
order. Eight fixed order variants preserve the original candidate pool and use the
current fixed span projection for span scoring. None improves the N10T anchor file
top10 count of 34 or projected span top10 count of 30; several promotion variants
regress top10. N10DJ authorizes only N10DK public package.

N10DK packages N10DJ publicly without private reads or recompute. It confirms that
blind deeper-band promotion is harmful, while distinct-fill and max-per-file-2
variants are neutral against the N10T anchor. The next useful question is why
correct files remain absent from N10T top10 and what observable structure predicts
safe promotion. N10DK authorizes only N10DL residual analysis.

N10DL performs that residual mechanism analysis without executing a new policy. Of
179 top10 file misses, 10 have first gold file in ranks 11-20, 8 in ranks 21-50,
and 161 are absent from the local candidate pool. Top10 duplicate pressure is
medium/high for 54 misses, but those pressure cases are not the 11-50 reachable
residuals; they are in the absent-from-pool bucket. The viable N10DM signal is
therefore not duplicate-pressure promotion. It is a narrower no-duplicate-pressure
deep-rank probe over the 18 reachable residuals. Gold-free observable fields exist
for candidate rank, private file identity, duplicate pressure, file repeat count,
and span-length bucket, while source/channel, method, and score buckets are
incomplete. N10DL authorizes only N10DM residual-aware fixed-variant smoke.

N10DM executes that fixed-variant smoke with activation limited to rows whose N10T
top10 has no duplicate-file pressure. All five promotion variants are harmful:
none improves top10 file or projected span reach, although some recover rank11-20
residuals while losing more anchor hits. Candidate pool membership is unchanged,
candidate add/remove counts remain zero, and N10DM authorizes only N10DN public
package.

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
- N10CF authorizes only N10CG span-shape mechanism follow-up using fixed/
  predeclared observable rules on the same scoped rows. It does not authorize
  runtime/default promotion, heldout/generalization claims, retrieval/rerun,
  candidate generation/add/remove/reorder, cluster/bridge execution, adaptive
  tuning, selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10CG authorizes only N10CH public observable hybrid span-shape rule sweep audit
  package. It does not authorize private reads, new variants, runtime/default
  promotion, heldout/generalization claims, retrieval/rerun, candidate generation/
  add/remove/reorder, cluster/bridge execution, adaptive tuning,
  selector/reranker execution, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10CH authorizes only N10CI independent recompute or adapter smoke for
  `short75_225_top3_all_pm200`. It does not authorize runtime/default promotion,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, cluster/bridge execution, adaptive tuning, selector/reranker execution,
  P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N10CI authorizes only N10CJ public winning-hybrid replication package. It does
  not authorize additional private reads, runtime/default promotion,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, adaptive tuning, selector/reranker execution, P5, BEA-v1-A,
  method-winner claims, or downstream-value claims.
- N10CJ authorizes only N10CK default-off adapter smoke for the winning hybrid. It
  does not authorize runtime/default enablement, existing evaluator hook-in,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-
  value claims.
- N10CK authorizes only N10CL public adapter-smoke package. It does not authorize
  additional private reads, runtime/default enablement, existing evaluator hook-in,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-
  value claims.
- N10CL authorizes only N10CM winning-hybrid next-step decision. It does not
  authorize runtime/default enablement, existing evaluator hook-in,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-
  value claims.
- N10CM authorizes only N10CN public cost-reduction refinement audit package. It
  does not authorize additional private reads, recompute, new variants,
  runtime/default enablement, existing evaluator hook-in, heldout/generalization
  claims, retrieval/rerun, candidate generation/add/remove/reorder, adaptive
  tuning, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N10CN authorizes only N10CO default-off adapter smoke for the refined hybrid
  `short75_225_top2_all_pm200`. It does not authorize runtime/default enablement,
  existing evaluator hook-in, heldout/generalization claims, retrieval/rerun,
  candidate generation/add/remove/reorder, adaptive tuning, P5, BEA-v1-A,
  method-winner claims, or downstream-value claims.
- N10CO authorizes only N10CP public adapter-smoke package. It does not authorize
  additional private reads, runtime/default enablement, existing evaluator hook-in,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-
  value claims.
- N10CP authorizes only N10CQ refined-hybrid next-step decision. It does not
  authorize runtime/default enablement, existing evaluator hook-in,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-
  value claims.
- N10CQ authorizes only N10CR mechanism-guided refined-hybrid sweep using the same
  scoped rows and fixed variants derived from N10CQ. It does not authorize
  runtime/default enablement, existing evaluator hook-in, heldout/generalization
  claims, retrieval/rerun, candidate generation/add/remove/reorder, adaptive
  tuning, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N10CR authorizes only N10CS public package. It does not authorize runtime/default
  enablement, existing evaluator hook-in, heldout/generalization claims,
  retrieval/rerun, candidate generation/add/remove/reorder, rank/file promotion,
  adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N10CS authorizes only N10CT exploration around `top2_pm300_short75_225`. It does
  not authorize runtime/default enablement, existing evaluator hook-in,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, rank/file promotion, adaptive tuning, P5, BEA-v1-A, method-winner
  claims, or downstream-value claims.
- N10CT authorizes only N10CU public package. It does not authorize private reads,
  recompute, new variants, runtime/default enablement, existing evaluator hook-in,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, top3 overrides, medium/long extra gates, adaptive tuning, P5, BEA-v1-A,
  method-winner claims, or downstream-value claims.
- N10CU authorizes only N10CV follow-up around the pm400 gain. It does not authorize
  private reads, recompute, new variants, runtime/default enablement, existing
  evaluator hook-in, heldout/generalization claims, retrieval/rerun, candidate
  generation/add/remove/reorder, top3 overrides, adaptive tuning, P5, BEA-v1-A,
  method-winner claims, or downstream-value claims.
- N10CV authorizes only N10CW top2 override high-window neighborhood sweep. It
  does not authorize runtime/default enablement, heldout/generalization claims,
  retrieval/rerun, candidate generation/add/remove/reorder, top3 overrides,
  adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N10CW authorizes only N10CX top2 override high-window neighborhood public
  package. It does not authorize private reads, recompute, new variants,
  runtime/default enablement, heldout/generalization claims, retrieval/rerun,
  candidate generation/add/remove/reorder, top3 overrides, medium/long gates,
  adaptive tuning, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N10CX authorizes only N10CY top2 high-window next mechanism decision. It does
  not authorize private reads, recompute, new variants, runtime/default enablement,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, top3 overrides, medium/long gates, adaptive tuning, P5, BEA-v1-A,
  method-winner claims, or downstream-value claims.
- N10CY authorizes only N10CZ top2 high-window next exploration decision. It does
  not authorize runtime/default enablement, heldout/generalization claims,
  retrieval/rerun, candidate generation/add/remove/reorder, top3 overrides,
  medium/long gates, adaptive tuning, P5, BEA-v1-A, method-winner claims, or
  downstream-value claims.
- N10CZ authorizes only N10DA public upper-bound package. It does not authorize
  local refinement, rank/file experiments, runtime/default enablement,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, top3 overrides, medium/long gates, rank/file promotion, adaptive
  tuning, P5, BEA-v1-A, method-winner claims, or downstream-value claims.
- N10DA authorizes only N10DB rank/file reach branch scoping or experiment, with
  exact scope to be decided by oracle. It does not authorize private reads,
  recompute, new variants, local refinement, runtime/default enablement,
  heldout/generalization claims, retrieval/rerun, candidate generation/add/remove/
  reorder, top3 overrides, adaptive tuning, P5, BEA-v1-A, method-winner claims,
  or downstream-value claims.
- N10DB authorizes only N10DC distinct-file packing rank/file-reach smoke over the
  same scoped rows and same candidate pool, with gold-free file-dedup packing and
  public aggregate outputs only. It does not authorize retrieval/rerun, candidate
  generation/materialization, selector/reranker execution, P5, BEA-v1-A,
  runtime/default changes, heldout/generalization claims, method-winner claims, or
  downstream-value claims.
- N10DC authorizes only N10DD public package. It does not authorize runtime/default
  changes, heldout/generalization claims, retrieval/rerun, candidate generation/
  materialization/add/remove, selector/reranker execution, P5, BEA-v1-A,
  method-winner claims, or downstream-value claims.
- N10DD authorizes only N10DE regression-vs-zero-loss mechanism decomposition over
  the same scoped rows. It does not authorize runtime/default changes,
  heldout/generalization claims, retrieval/rerun, candidate generation/
  materialization/add/remove, selector/reranker execution, P5, BEA-v1-A,
  method-winner claims, or downstream-value claims.
- N10DE authorizes only N10DF hybrid distinct-file packing smoke over the same
  scoped rows and fixed preview variants. It does not authorize runtime/default
  changes, heldout/generalization claims, retrieval/rerun, candidate generation/
  materialization/add/remove, selector/reranker execution, adaptive tuning, P5,
  BEA-v1-A, method-winner claims, or downstream-value claims.
- N10DF authorizes only N10DG hybrid distinct-file packing public package. It does
  not authorize runtime/default changes, heldout/generalization claims,
  retrieval/rerun, candidate generation/materialization/add/remove,
  selector/reranker execution, adaptive tuning, P5, BEA-v1-A, method-winner
  claims, downstream-value claims, or broad private reads.
- N10DG authorizes only N10DH packing-plus-span-window or top20 reach repair
  experiment under a future oracle scope. It does not authorize runtime/default,
  selector/reranker, candidate generation, retrieval/rerun, broad private read,
  P5, BEA-v1-A, method-winner, downstream, or heldout/generalization claims.
- N10DH authorizes only N10DI public package. It does not authorize runtime/default,
  selector/reranker, candidate generation/materialization/add/remove,
  retrieval/rerun, broad private reads, P5, BEA-v1-A, adaptive per-record
  selection, method-winner, downstream, or heldout/generalization claims.
- N10DI authorizes only N10DJ next rank/file-reach empirical experiment under a
  future oracle scope. It does not authorize runtime/default,
  selector/reranker, candidate generation/materialization, retrieval/rerun, broad
  private reads, P5, BEA-v1-A, method-winner, downstream, or heldout/generalization
  claims.
- N10DJ authorizes only N10DK rank/file-reach rank-promotion public package. It
  does not authorize runtime/default, selector/reranker, candidate generation/
  materialization/add/remove, retrieval/rerun, broad private reads, P5, BEA-v1-A,
  method-winner, downstream, adaptive per-record selection, or
  heldout/generalization claims.
- N10DK authorizes only N10DL N10T top10 file-reach residual analysis over the same
  scoped rows. It does not authorize runtime/default, selector/reranker, candidate
  generation/materialization/add/remove, retrieval/rerun, broad private reads, P5,
  BEA-v1-A, method-winner, downstream, adaptive per-record selection, or
  heldout/generalization claims.
- N10DL authorizes only N10DM residual-aware rank/file promotion rule smoke over the
  same scoped rows and fixed variants. It does not authorize runtime/default,
  selector/reranker, candidate generation/materialization/add/remove,
  retrieval/rerun, broad private reads, P5, BEA-v1-A, method-winner, downstream,
  adaptive per-record selection, or heldout/generalization claims.
- N10DM authorizes only N10DN public package. It does not authorize runtime/default,
  selector/reranker, candidate generation/materialization/add/remove,
  retrieval/rerun, broad private reads, P5, BEA-v1-A, method-winner, downstream,
  adaptive tuning, or heldout/generalization claims.
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

eval/bea_v1_n10cf_span_shape_refinement_audit_package.py
  Public package of the N10CE span-shape refinement ladder; authorizes only N10CG
  fixed/predeclared observable-rule follow-up.

eval/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep.py
  Same-source observable hybrid span-shape rule sweep; authorizes only N10CH
  public audit/package.

eval/bea_v1_n10ch_observable_hybrid_rule_audit_package.py
  Public package of the N10CG positive hybrid result; authorizes only N10CI
  candidate strategy recompute or adapter smoke.

eval/bea_v1_n10ci_independent_recompute_winning_hybrid.py
  Independent recompute of `short75_225_top3_all_pm200`; matches N10CG/N10CH and
  authorizes only N10CJ public replication package.

eval/bea_v1_n10cj_winning_hybrid_replication_package.py
  Public package of the winning hybrid replication chain; authorizes only N10CK
  default-off adapter smoke.

eval/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke.py
  Default-off adapter smoke for `short75_225_top3_all_pm200`; reproduces the
  winning aggregate and authorizes only N10CL public package.

eval/bea_v1_n10cl_winning_hybrid_adapter_smoke_package.py
  Public package of N10CK adapter smoke; authorizes only N10CM next-step decision.

eval/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep.py
  Same-source fixed-variant refinement of the winning hybrid; finds one lower-cost
  preserving variant and authorizes only N10CN public audit/package.

eval/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package.py
  Public package of the N10CM refinement result; authorizes only N10CO default-off
  adapter smoke for the refined hybrid.

eval/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke.py
  Default-off adapter smoke for `short75_225_top2_all_pm200`; reproduces the
  refined aggregate and authorizes only N10CP public package.

eval/bea_v1_n10cp_refined_hybrid_adapter_smoke_package.py
  Public package of N10CO refined-hybrid adapter smoke; authorizes only N10CQ
  next-step decision.

eval/bea_v1_n10cq_refined_hybrid_mechanism_decomposition.py
  Mechanism decomposition of the refined hybrid; authorizes only N10CR fixed
  mechanism-guided follow-up.

eval/bea_v1_n10cr_mechanism_guided_local_saturation_sweep.py
  Mechanism-guided local saturation sweep; finds `top2_pm300_short75_225` reaches
  26/32 and authorizes only N10CS public package.

eval/bea_v1_n10cs_local_saturation_package.py
  Public package of the N10CR local saturation result; authorizes only N10CT
  exploration around top2 pm300.

eval/bea_v1_n10ct_top2_override_window_neighborhood_sweep.py
  Same-source top2 override pm-neighborhood sweep; finds pm275 preserves 26/32
  lower than pm300 and pm400 improves to 27/33, authorizing only N10CU package.

eval/bea_v1_n10cu_top2_override_neighborhood_package.py
  Public package of the N10CT top2 override neighborhood; authorizes only N10CV
  follow-up around the pm400 gain.

eval/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition.py
  Decomposes pm400's marginal gain vs pm300 and authorizes only N10CW high-window
  neighborhood exploration.

eval/bea_v1_n10cw_top2_override_high_window_neighborhood_sweep.py
  High-window top2 override sweep; finds pm1000 reaches 30/36 and authorizes only
  N10CX public package.

eval/bea_v1_n10cx_top2_override_high_window_package.py
  Public package of N10CW high-window sweep; authorizes only N10CY next mechanism
  decision.

eval/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition.py
  Same-source decomposition of pm400/pm800/pm1000 marginal gains; authorizes only
  N10CZ next exploration decision.

eval/bea_v1_n10cz_top2_local_window_saturation_upper_bound.py
  Same-source upper-bound smoke for top2 local windows; finds saturation and
  authorizes only N10DA public package.

eval/bea_v1_n10da_top2_local_window_upper_bound_package.py
  Public package of N10CZ upper-bound result; authorizes only N10DB rank/file reach
  branch scoping or experiment as oracle decides.

eval/bea_v1_n10db_rank_file_reach_policy_field_scoping.py
  Private-schema scoping for gold-free rank/file-reach policy fields; selects
  file-dedup distinct-file packing and authorizes only N10DC smoke.

eval/bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke.py
  Direct same-source rank/file-reach smoke for distinct-file packing; authorizes
  only N10DD public package.

eval/bea_v1_n10dd_distinct_file_packing_rank_file_reach_package.py
  Public package of corrected N10DC distinct-file packing tradeoffs; authorizes
  only N10DE regression-vs-zero-loss mechanism decomposition.

eval/bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition.py
  Direct decomposition of aggressive distinct-file regression vs max-per-file-2
  zero-loss tradeoff; authorizes only N10DF hybrid distinct-file packing smoke.

eval/bea_v1_n10df_hybrid_distinct_file_packing_smoke.py
  Direct same-source hybrid distinct-file packing smoke; finds prefix7 zero-loss
  aggressive-equivalent top10 span and authorizes only N10DG public package.

eval/bea_v1_n10dg_hybrid_distinct_file_packing_public_package.py
  Public package of N10DF; frames prefix7 as top10-safe but top20-limited and
  authorizes only N10DH follow-up.

eval/bea_v1_n10dh_packing_span_window_combination_smoke.py
  Direct combination smoke for packing plus span-window projection; finds no
  improvement over window-only and authorizes only N10DI public package.

eval/bea_v1_n10di_packing_span_window_combination_public_package.py
  Public package of N10DH; validates N10T-best-order scope and authorizes only
  N10DJ rank/file-reach empirical follow-up.

eval/bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke.py
  Direct same-source rank/file-reach smoke from N10T-best order; finds no top10
  file/span improvement and authorizes only N10DK public package.

eval/bea_v1_n10dk_n10t_order_rank_promotion_public_package.py
  Public package of N10DJ; frames deeper-band promotion as harmful/neutral and
  authorizes only N10DL residual analysis.

eval/bea_v1_n10dl_n10t_file_reach_residual_analysis.py
  Direct residual analysis of N10T top10 file misses; identifies gold-free signals
  and authorizes only N10DM fixed-variant smoke.

eval/bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke.py
  Direct gated deep-rank promotion smoke; finds all no-duplicate-pressure variants
  harmful and authorizes only N10DN public package.
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
- [`artifacts/bea_v1_n10cf_span_shape_refinement_audit_package/bea_v1_n10cf_span_shape_refinement_audit_package_report.json`](artifacts/bea_v1_n10cf_span_shape_refinement_audit_package/bea_v1_n10cf_span_shape_refinement_audit_package_report.json)
- [`artifacts/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep_report.json`](artifacts/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep/bea_v1_n10cg_observable_hybrid_span_shape_rule_sweep_report.json)
- [`artifacts/bea_v1_n10ch_observable_hybrid_rule_audit_package/bea_v1_n10ch_observable_hybrid_rule_audit_package_report.json`](artifacts/bea_v1_n10ch_observable_hybrid_rule_audit_package/bea_v1_n10ch_observable_hybrid_rule_audit_package_report.json)
- [`artifacts/bea_v1_n10ci_independent_recompute_winning_hybrid/bea_v1_n10ci_independent_recompute_winning_hybrid_report.json`](artifacts/bea_v1_n10ci_independent_recompute_winning_hybrid/bea_v1_n10ci_independent_recompute_winning_hybrid_report.json)
- [`artifacts/bea_v1_n10cj_winning_hybrid_replication_package/bea_v1_n10cj_winning_hybrid_replication_package_report.json`](artifacts/bea_v1_n10cj_winning_hybrid_replication_package/bea_v1_n10cj_winning_hybrid_replication_package_report.json)
- [`artifacts/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke_report.json`](artifacts/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke/bea_v1_n10ck_default_off_adapter_winning_hybrid_smoke_report.json)
- [`artifacts/bea_v1_n10cl_winning_hybrid_adapter_smoke_package/bea_v1_n10cl_winning_hybrid_adapter_smoke_package_report.json`](artifacts/bea_v1_n10cl_winning_hybrid_adapter_smoke_package/bea_v1_n10cl_winning_hybrid_adapter_smoke_package_report.json)
- [`artifacts/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep_report.json`](artifacts/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep/bea_v1_n10cm_winning_hybrid_cost_reduction_refinement_sweep_report.json)
- [`artifacts/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package_report.json`](artifacts/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package/bea_v1_n10cn_winning_hybrid_cost_refinement_audit_package_report.json)
- [`artifacts/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke_report.json`](artifacts/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke/bea_v1_n10co_default_off_adapter_refined_hybrid_smoke_report.json)
- [`artifacts/bea_v1_n10cp_refined_hybrid_adapter_smoke_package/bea_v1_n10cp_refined_hybrid_adapter_smoke_package_report.json`](artifacts/bea_v1_n10cp_refined_hybrid_adapter_smoke_package/bea_v1_n10cp_refined_hybrid_adapter_smoke_package_report.json)
- [`artifacts/bea_v1_n10cq_refined_hybrid_mechanism_decomposition/bea_v1_n10cq_refined_hybrid_mechanism_decomposition_report.json`](artifacts/bea_v1_n10cq_refined_hybrid_mechanism_decomposition/bea_v1_n10cq_refined_hybrid_mechanism_decomposition_report.json)
- [`artifacts/bea_v1_n10cr_mechanism_guided_local_saturation_sweep/bea_v1_n10cr_mechanism_guided_local_saturation_sweep_report.json`](artifacts/bea_v1_n10cr_mechanism_guided_local_saturation_sweep/bea_v1_n10cr_mechanism_guided_local_saturation_sweep_report.json)
- [`artifacts/bea_v1_n10cs_local_saturation_package/bea_v1_n10cs_local_saturation_package_report.json`](artifacts/bea_v1_n10cs_local_saturation_package/bea_v1_n10cs_local_saturation_package_report.json)
- [`artifacts/bea_v1_n10ct_top2_override_window_neighborhood_sweep/bea_v1_n10ct_top2_override_window_neighborhood_sweep_report.json`](artifacts/bea_v1_n10ct_top2_override_window_neighborhood_sweep/bea_v1_n10ct_top2_override_window_neighborhood_sweep_report.json)
- [`artifacts/bea_v1_n10cu_top2_override_neighborhood_package/bea_v1_n10cu_top2_override_neighborhood_package_report.json`](artifacts/bea_v1_n10cu_top2_override_neighborhood_package/bea_v1_n10cu_top2_override_neighborhood_package_report.json)
- [`artifacts/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition_report.json`](artifacts/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition/bea_v1_n10cv_top2_pm400_marginal_gain_decomposition_report.json)
- [`artifacts/bea_v1_n10cw_top2_override_high_window_neighborhood_sweep/bea_v1_n10cw_top2_override_high_window_neighborhood_sweep_report.json`](artifacts/bea_v1_n10cw_top2_override_high_window_neighborhood_sweep/bea_v1_n10cw_top2_override_high_window_neighborhood_sweep_report.json)
- [`artifacts/bea_v1_n10cx_top2_override_high_window_package/bea_v1_n10cx_top2_override_high_window_package_report.json`](artifacts/bea_v1_n10cx_top2_override_high_window_package/bea_v1_n10cx_top2_override_high_window_package_report.json)
- [`artifacts/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition_report.json`](artifacts/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition/bea_v1_n10cy_top2_pm1000_marginal_gain_decomposition_report.json)
- [`artifacts/bea_v1_n10cz_top2_local_window_saturation_upper_bound/bea_v1_n10cz_top2_local_window_saturation_upper_bound_report.json`](artifacts/bea_v1_n10cz_top2_local_window_saturation_upper_bound/bea_v1_n10cz_top2_local_window_saturation_upper_bound_report.json)
- [`artifacts/bea_v1_n10da_top2_local_window_upper_bound_package/bea_v1_n10da_top2_local_window_upper_bound_package_report.json`](artifacts/bea_v1_n10da_top2_local_window_upper_bound_package/bea_v1_n10da_top2_local_window_upper_bound_package_report.json)
- [`artifacts/bea_v1_n10db_rank_file_reach_policy_field_scoping/bea_v1_n10db_rank_file_reach_policy_field_scoping_report.json`](artifacts/bea_v1_n10db_rank_file_reach_policy_field_scoping/bea_v1_n10db_rank_file_reach_policy_field_scoping_report.json)
- [`artifacts/bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke/bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke_report.json`](artifacts/bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke/bea_v1_n10dc_distinct_file_packing_rank_file_reach_smoke_report.json)
- [`artifacts/bea_v1_n10dd_distinct_file_packing_rank_file_reach_package/bea_v1_n10dd_distinct_file_packing_rank_file_reach_package_report.json`](artifacts/bea_v1_n10dd_distinct_file_packing_rank_file_reach_package/bea_v1_n10dd_distinct_file_packing_rank_file_reach_package_report.json)
- [`artifacts/bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition/bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition_report.json`](artifacts/bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition/bea_v1_n10de_regression_vs_zero_loss_mechanism_decomposition_report.json)
- [`artifacts/bea_v1_n10df_hybrid_distinct_file_packing_smoke/bea_v1_n10df_hybrid_distinct_file_packing_smoke_report.json`](artifacts/bea_v1_n10df_hybrid_distinct_file_packing_smoke/bea_v1_n10df_hybrid_distinct_file_packing_smoke_report.json)
- [`artifacts/bea_v1_n10dg_hybrid_distinct_file_packing_public_package/bea_v1_n10dg_hybrid_distinct_file_packing_public_package_report.json`](artifacts/bea_v1_n10dg_hybrid_distinct_file_packing_public_package/bea_v1_n10dg_hybrid_distinct_file_packing_public_package_report.json)
- [`artifacts/bea_v1_n10dh_packing_span_window_combination_smoke/bea_v1_n10dh_packing_span_window_combination_smoke_report.json`](artifacts/bea_v1_n10dh_packing_span_window_combination_smoke/bea_v1_n10dh_packing_span_window_combination_smoke_report.json)
- [`artifacts/bea_v1_n10di_packing_span_window_combination_public_package/bea_v1_n10di_packing_span_window_combination_public_package_report.json`](artifacts/bea_v1_n10di_packing_span_window_combination_public_package/bea_v1_n10di_packing_span_window_combination_public_package_report.json)
- [`artifacts/bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke/bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke_report.json`](artifacts/bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke/bea_v1_n10dj_n10t_order_file_reach_rank_promotion_smoke_report.json)
- [`artifacts/bea_v1_n10dk_n10t_order_rank_promotion_public_package/bea_v1_n10dk_n10t_order_rank_promotion_public_package_report.json`](artifacts/bea_v1_n10dk_n10t_order_rank_promotion_public_package/bea_v1_n10dk_n10t_order_rank_promotion_public_package_report.json)
- [`artifacts/bea_v1_n10dl_n10t_file_reach_residual_analysis/bea_v1_n10dl_n10t_file_reach_residual_analysis_report.json`](artifacts/bea_v1_n10dl_n10t_file_reach_residual_analysis/bea_v1_n10dl_n10t_file_reach_residual_analysis_report.json)
- [`artifacts/bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke/bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke_report.json`](artifacts/bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke/bea_v1_n10dm_no_duplicate_pressure_deep_rank_promotion_smoke_report.json)
- [`artifacts/bea_v1_n10dr_real_candidate_source_canary/bea_v1_n10dr_real_candidate_source_canary_report.json`](artifacts/bea_v1_n10dr_real_candidate_source_canary/bea_v1_n10dr_real_candidate_source_canary_report.json)
- [`artifacts/bea_v1_n10ds_real_candidate_source_canary_audit_package/bea_v1_n10ds_real_candidate_source_canary_audit_package_report.json`](artifacts/bea_v1_n10ds_real_candidate_source_canary_audit_package/bea_v1_n10ds_real_candidate_source_canary_audit_package_report.json)
- [`artifacts/bea_v1_n10dt_real_candidate_source_failure_analysis/bea_v1_n10dt_real_candidate_source_failure_analysis_report.json`](artifacts/bea_v1_n10dt_real_candidate_source_failure_analysis/bea_v1_n10dt_real_candidate_source_failure_analysis_report.json)
- [`artifacts/bea_v1_n10du_targeted_candidate_source_variant_canary/bea_v1_n10du_targeted_candidate_source_variant_canary_report.json`](artifacts/bea_v1_n10du_targeted_candidate_source_variant_canary/bea_v1_n10du_targeted_candidate_source_variant_canary_report.json)
- [`artifacts/bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package/bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package_report.json`](artifacts/bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package/bea_v1_n10dv_targeted_candidate_source_variant_canary_public_package_report.json)
- [`artifacts/bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis/bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis_report.json`](artifacts/bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis/bea_v1_n10dw_normalized_bm25_recovery_mechanism_analysis_report.json)
- [`artifacts/bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary/bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary_report.json`](artifacts/bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary/bea_v1_n10dx_normalized_bm25_topk_token_cap_variant_canary_report.json)
- [`artifacts/bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package/bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package_report.json`](artifacts/bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package/bea_v1_n10dy_normalized_bm25_topk_token_cap_canary_public_package_report.json)
- [`artifacts/bea_v1_n10dz_normalized_bm25_expanded_canary/bea_v1_n10dz_normalized_bm25_expanded_canary_report.json`](artifacts/bea_v1_n10dz_normalized_bm25_expanded_canary/bea_v1_n10dz_normalized_bm25_expanded_canary_report.json)
- [`artifacts/bea_v1_n10ea_normalized_bm25_expanded_canary_public_package/bea_v1_n10ea_normalized_bm25_expanded_canary_public_package_report.json`](artifacts/bea_v1_n10ea_normalized_bm25_expanded_canary_public_package/bea_v1_n10ea_normalized_bm25_expanded_canary_public_package_report.json)
- [`artifacts/bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke/bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke_report.json`](artifacts/bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke/bea_v1_n10eb_normalized_bm25_depth_to_head_integration_smoke_report.json)
- [`artifacts/bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package/bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package_report.json`](artifacts/bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package/bea_v1_n10ec_normalized_bm25_depth_to_head_integration_audit_package_report.json)
- [`artifacts/bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis/bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis_report.json`](artifacts/bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis/bea_v1_n10ed_novel_first_depth_to_head_mechanism_analysis_report.json)
- [`artifacts/bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment/bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment_report.json`](artifacts/bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment/bea_v1_n10ee_normalized_bm25_novel_guard_fixed_repacking_experiment_report.json)
- [`artifacts/bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package/bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package_report.json`](artifacts/bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package/bea_v1_n10ef_normalized_bm25_novel_guard_experiment_package_report.json)
- [`artifacts/bea_v1_n10eg_novel_first_guard_complementarity_slicing/bea_v1_n10eg_novel_first_guard_complementarity_slicing_report.json`](artifacts/bea_v1_n10eg_novel_first_guard_complementarity_slicing/bea_v1_n10eg_novel_first_guard_complementarity_slicing_report.json)
- [`artifacts/bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment/bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment_report.json`](artifacts/bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment/bea_v1_n10eh_fixed_full_guard_combination_repacking_experiment_report.json)
- [`artifacts/bea_v1_n10ei_fixed_full_guard_combination_package/bea_v1_n10ei_fixed_full_guard_combination_package_report.json`](artifacts/bea_v1_n10ei_fixed_full_guard_combination_package/bea_v1_n10ei_fixed_full_guard_combination_package_report.json)

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


Result: content_identifier_signal_bucket `signal_present`, rank_spread_bucket `spread_high`, query/fusion/symbol sources have high bucketed signal while control remains low; still not file retrieval evidence.
