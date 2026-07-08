# Interventional Evidence Acquisition Phase 7C Formal Fresh Public-Repo Validation

Date: 2026-07-08

Status: `repair_formal_pipeline_no_claim`

Authorization: `formal_confirmed_private_io_confirmed_public_repo_fetch_used`

## Scope

Phase 7C ran the formal fresh public-repo validation runner under the already frozen Phase 7A protocol. The run used the formal lower target bucket: repo count `bucket_formal_repo_target`, task count `bucket_formal_task_target`, and max 20 tasks per repo, but prior-overlap rejection blocked row scoring before any public result rows were emitted.

Private public-repo inputs, manifest, and rows stayed under ignored `runs/`. The public artifact is aggregate/coarse only and does not include repo names, URLs, owners, commits, paths, ranges, hashes, snippets, task IDs, row IDs, manifests, run directories, or per-repo/per-task detail.

Public report: [`phase7c_fresh_public_repo_validation_formal_report.json`](../../artifacts/phase7c_fresh_public_repo_validation_formal/phase7c_fresh_public_repo_validation_formal_report.json).

## Validation boundaries

The runner gated on the Phase 7A public report, rejected manifest-supplied execution, required private input/output and public-repo-fetch confirmations, rejected local-clone/synthetic sources, checked overlap against prior Phase 5B and Phase 7B private material only for freshness rejection, and stopped with a repair/no-claim status when overlap rejection found nonzero prior overlap. The public artifact remains aggregate-only and publishes no private overlap details.

## Interpretation

This records a formal no-claim validation artifact only. It is not a method comparison, not a product/default/runtime/deployment/training claim, and used no provider, LLM, model update, runtime/default change, deployment change, or new retrieval family.
