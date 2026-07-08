# Interventional Evidence Acquisition Phase 7D Input-Repair Protocol Freeze

Date: 2026-07-08

Status: `phase7d_input_repair_protocol_freeze_no_execution_no_claim`

Authorization: `docs_report_only_no_execution`

## Scope

Phase 7D freezes the input-repair protocol for a possible later Phase 7E run after the Phase 7C repair/no-claim checkpoint. It is docs/report-only: no private row, manifest, provenance, or `runs/` reads; no public repository fetch or clone; no benchmark rows; no outcome scoring; no source reads; no model fit/training; no provider/network/LLM use; no runtime/default/deployment change; and no new retrieval family.

Public report: [`phase7d_input_repair_protocol_freeze_report.json`](../../artifacts/phase7d_input_repair_protocol_freeze/phase7d_input_repair_protocol_freeze_report.json).

## Frozen input-repair protocol

- Prior-overlap is an input ineligibility condition.
- Replacement is allowed only before row generation and before outcome scoring.
- Replacement selection must be deterministic, auditable, frozen before any row/outcome effects, and not performance-based.
- Replacement logic must not be tuned after row or outcome effects.
- Phase 7A/7C labels, formal caps, EvidenceCore success semantics, privacy boundary, and no-claim posture remain frozen.
- Replacement and overlap reporting are aggregate bucket only; no private details or singleton buckets may be public.

## Must-not-cross boundary

Phase 7D does not read private rows, manifests, provenance, run directories, or private repository details. It does not fetch or clone public repos, generate benchmark rows, score outcomes, train/fit models, change labels/caps/EvidenceCore/privacy/no-claim rules, tune replacement logic after effects, publish private repo details, or make method winner/lift/product/default/runtime/deployment/training claims.

## Phase 7E boundary

Phase 7E may execute only after Phase 7D is committed and CI-green, and only when the Phase 7E boundary is explicitly invoked under the existing low-resource/no-claim constraints. Any Phase 7E output remains bound to aggregate-only public reporting and the frozen no-claim posture.
