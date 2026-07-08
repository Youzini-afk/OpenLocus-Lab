# Interventional Evidence Acquisition Phase 7E Input-Repaired Formal Validation

Date: 2026-07-08

Status: `repair_formal_pipeline_no_claim`

Authorization: `formal_private_input_private_output_public_repo_fetch_confirmed`

## Scope

Phase 7E executed the Phase 7D input-repair boundary as a formal no-claim rerun. It used current-run public repository fetch/materialization under explicit `--confirm-private-input`, `--confirm-private-output`, and `--confirm-public-repo-fetch` confirmations. Private candidate inputs, manifest, rows, clone materialization, and replacement audit were written only under ignored `runs/phase7e_input_repaired_formal_validation/...`.

Public aggregate report: [`phase7e_input_repaired_formal_validation_report.json`](../../artifacts/phase7e_input_repaired_formal_validation/phase7e_input_repaired_formal_validation_report.json).

## Frozen rules preserved

- Prior-overlap is treated as input ineligibility and repair happens only before row generation and outcome scoring.
- Replacement uses the deterministic non-performance rule `stable_public_candidate_order_then_first_eligible_bucket_only`.
- Manifest-supplied execution, local clone sources, synthetic sources, and missing comparable repo IDs are rejected.
- Phase 7A/7C labels, formal caps, EvidenceCore success semantics, privacy boundary, and no-claim posture remain frozen.
- Phase 5B, Phase 7B, and Phase 7C private material is read only for overlap rejection, not for scoring or tuning.

## Public result

The public report status is `repair_formal_pipeline_no_claim`. Coarse public buckets record formal repo and task target buckets, zero public rows because the repaired input still hit a nonzero prior-overlap bucket before row generation/outcome scoring, replacement bucket `bucket_six_to_eight`, overlap bucket `bucket_nonzero_to_three`, zero stop/abstain success, and route-specific validation passed.

No repository names, URLs, owners, commits, paths, ranges, hashes, snippets, row IDs, task IDs, manifests, run directories, singleton buckets, or private details are public.

## Non-claims

This result does not establish a method winner, lift, product/default/runtime/deployment change, provider or remote-model claim, training result, or new retrieval family. It is an aggregate-only formal repair_formal_pipeline_no_claim checkpoint.
