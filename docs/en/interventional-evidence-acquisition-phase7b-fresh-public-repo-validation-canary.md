# Interventional Evidence Acquisition Phase 7B Fresh Public-Repo Validation Canary

Date: 2026-07-07

Status: `phase7b_canary_pipeline_check_passed_no_claim`

Authorization: `canary_pipeline_only_confirmed_private_io_confirmed_public_repo_fetch_used`

## Scope

Phase 7B ran a canary-only pipeline check under the Phase 7A boundary. It deliberately used a much smaller canary scale than the Phase 7A formal-validation target/caps; it did not execute the formal 80-120 task validation. It required explicit private input/output confirmation, wrote private canary manifest/rows only under ignored `runs/`, and published only an aggregate public report.

This canary did not run formal validation and does not answer whether the route works. It used no provider, LLM, model update, runtime/default/product change, deployment change, or new retrieval family. Public repository fetch was used under explicit confirmation for the fresh public-repo canary input.

## Canary checks

The canary gated on the Phase 7A public report, performed private overlap rejection against Phase 5B rows for freshness, built a bounded private canary manifest, constructed full seven-label rows per task, and enforced EvidenceCore materialization checks. Candidate-found alone was not counted as evidence, and `stop`/`abstain` success stayed zero.

Public report: [`phase7b_fresh_public_repo_validation_canary_report.json`](../../artifacts/phase7b_fresh_public_repo_validation_canary/phase7b_fresh_public_repo_validation_canary_report.json).

## Interpretation

The result means only that the fresh-validation canary pipeline passed its bounded no-claim checks. It is not formal validation, not a research conclusion, not a method comparison, and not a product/default/runtime/deployment/training claim.
