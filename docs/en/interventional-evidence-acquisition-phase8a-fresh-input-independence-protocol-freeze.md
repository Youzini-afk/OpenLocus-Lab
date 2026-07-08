# Interventional Evidence Acquisition Phase 8A Fresh-Input Independence Protocol Freeze

Date: 2026-07-08

Status: `phase8a_protocol_freeze_no_execution_no_claim`

Public report: [`phase8a_fresh_input_independence_protocol_freeze_report.json`](../../artifacts/phase8a_fresh_input_independence_protocol_freeze/phase8a_fresh_input_independence_protocol_freeze_report.json)

## Scope

Phase 8A is docs/report-only. It defines a future fresh-input construction and independence-audit contract for possible Phase 8B. It does not claim that independence was achieved, passed, validated, or repaired.

Phase 8A performed no private input reads, no ignored `runs/` reads, no manifest reads, no public repository fetch/clone, no source reads, no task generation, no candidate registry population, no row/outcome scoring, and no runner execution. It makes no model, training, provider, LLM, runtime, default, product, or method claim.

## Frozen future Phase 8B contract

- Phase 8B must be input construction and independence audit first, not scoring.
- Any private candidate source registry belongs under ignored `runs/` in Phase 8B, not Phase 8A.
- Phase 8B must explicitly exclude Phase 5B, 7B, 7C, and 7E provenance.
- Comparable repo identity must cover normalized URL forms, owner/name, fork/source repository if detectable, commit/SHA, clone origin, package/module identity where available, exact paths/ranges/hashes, task IDs, and file-family closeness if privately detectable.
- Attempt budget: at most 2 independent construction attempts; at most 16 candidate repos inspected; target 8-12 accepted repos; future task hard max 150 if later scoring is separately allowed.
- Replacement is allowed only before outcome scoring and only for clone failure, unavailable SHA, insufficient eligible files, or failed independence/materialization precheck. Replacement is never allowed after evidence outcomes are observed.
- Hard stops include nonzero overlap, inability to establish comparable identity, inability to reach accepted task count without loosening freshness, any need to publish exact/private details, or any scoring before input independence audit passes.
- Public output remains aggregate-only: no repo names/URLs/owners, commits/SHAs, paths/ranges/hashes/snippets, task IDs, row IDs, manifest paths, run dirs, per-repo/per-task details, or singleton buckets.

## Boundary

Phase 8A forbids another Phase 7E repair loop. The only next authorized action is a separate Phase 8B input-construction/audit step that still performs no scoring until input independence audit passes.
