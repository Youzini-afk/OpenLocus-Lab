# Interventional Evidence Acquisition Phase 9A Protocol Freeze

Date: 2026-07-09

Status: `phase9a_protocol_freeze_no_execution_no_claim`

Authorization: `protocol_freeze_only_docs_report_no_execution_no_claim`

Public report: [`phase9a_protocol_freeze_no_execution_no_claim_report.json`](../../artifacts/phase9a_protocol_freeze_no_execution_no_claim/phase9a_protocol_freeze_no_execution_no_claim_report.json)

## Scope

Phase 9A is protocol-freeze-only public documentation and an aggregate public report. It is not continuation, repair, completion, or direct execution of Phase 8B. It uses only already-public aggregate Phase 8B/8C facts as motivation: Phase 8B did not pass into scoring eligibility under the frozen cap, and Phase 8C stopped the current Phase 8 construction attempt after a public closeout.

No private reads, ignored `runs/` reads, manifest reads, Phase 8B private registry or pool reads, Phase 8B accepted/rejected repository inspection, repository fetch/clone, source reads, task generation, candidate registry population, candidate pool construction, data collection, row/outcome scoring, labels, evidence-success evaluation, model fitting, provider or LLM calls, runtime/default/product changes, direct Phase 9 execution, or repair of the Phase 8B accepted-repository count occurred in Phase 9A.

## Frozen clean-room source-universe rule

Future Phase 9B source-list construction must be clean-room. The Phase 9B source list must be generated without reading the Phase 8B private pool, manifests, registry, logs, provenance, accepted candidates, rejected candidates, near misses, or any other Phase 8B private material.

Because Phase 9A cannot read the Phase 8B private registry, it does not claim that any reuse was checked safe. Instead, the frozen anti-laundering rule excludes reuse of all Phase 8B private material.

## Predeclared acquisition recipe

Future Phase 9B may only use neutral public acquisition channels under this frozen recipe. The channel order is fixed before any inspection:

1. `public_language_registry_top_projects_index`;
2. `public_ecosystem_topic_index`;
3. `public_package_metadata_dependents_index`.

Manual named seed repositories, private candidate sources, and prior-phase candidate sources are forbidden.

Within each channel, ordering is deterministic and uses these public metadata keys in this order: normalized public project identity ascending, stable public-metadata rank ascending, default-branch name ascending, and channel-local index ascending. Seed label `phase9a_clean_room_public_seed_v1` is a version label only; randomness, random shuffle, and post-hoc resampling are forbidden.

The frozen quotas are: accepted-source target 12, minimum accepted sources for a later audit pass 8, total candidate inspection cap 48, per-channel inspection cap 16, and initial per-channel quota 16. Eligibility must be decided before scoring from public metadata/materialization facts only: public accessibility without authentication, source archive materializable before scoring, declared or publicly auditable license, default branch or equivalent revision resolvable, in-scope language/file mix detectable from public metadata, and not private/prior-phase/manual named seed material.

Replacement is deterministic: replace unavailable or ineligible sources with the next uninspected item from the same frozen channel stream; if that stream is exhausted, continue round-robin to the next channel in the frozen order. Replacement must happen before any scoring, labels, or outcomes, and must not use performance, outcome, evidence-success, or Phase 8B private feedback. Performance-based replacement is forbidden.

## Identity normalization before inspection

Before source inspection, future Phase 9B must normalize public project identity, deduplicate candidate identities, and check public fork/mirror equivalence where publicly available. These identity checks use public metadata only and must happen before inspection or availability decisions.

## Availability-first gate

Availability is a gate before scoring, not a scoring result. Future Phase 9B must check access, license/materialization feasibility, and availability before scoring. Unavailable sources must be replaced before scoring under the frozen replacement rules.

## Privacy contract

Public output remains aggregate-only. It must not publish repository names, URLs, owners, commits, paths, hashes, snippets, task IDs, row IDs, manifest paths, run directories, singleton buckets, or per-repository/per-task facts.

## Hard stops

The protocol stops if any of these occur or would be required:

- any attempt to read Phase 8B private material;
- identity normalization not completed before inspection;
- availability gate not completed before scoring;
- ordering, quota, or replacement-rule drift;
- public reporting would require exact private or source identifiers;
- any scoring before a later audit passes.

## Future Phase 9B boundary

Phase 9B may only construct and audit candidate sources under this frozen protocol. Scoring remains forbidden until a later audit passes under a separate authorization. Phase 9A itself authorizes no direct Phase 9 execution and makes no method, product, performance, training, provider, model, scoring, outcome, evidence-success, runtime, default, or deployment claim.
