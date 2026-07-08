# Interventional Evidence Acquisition Phase 7C Formal Fresh Public-Repo Validation

日期：2026-07-08

Status: `repair_formal_pipeline_no_claim`

Authorization: `formal_confirmed_private_io_confirmed_public_repo_fetch_used`

## 范围

Phase 7C 在已冻结的 Phase 7A protocol 下运行 formal fresh public-repo validation runner。本次运行采用 formal lower target bucket：repo count 为 `bucket_formal_repo_target`，task count 为 `bucket_formal_task_target`，每个 repo 最多 20 tasks；但 prior-overlap rejection 在 public result rows 产生前阻止了 row scoring。

Private public-repo inputs、manifest 和 rows 只保留在 ignored `runs/` 下。Public artifact 只包含 aggregate/coarse 信息，不包含 repo names、URLs、owners、commits、paths、ranges、hashes、snippets、task IDs、row IDs、manifests、run directories 或 per-repo/per-task detail。

Public report：[`phase7c_fresh_public_repo_validation_formal_report.json`](../../artifacts/phase7c_fresh_public_repo_validation_formal/phase7c_fresh_public_repo_validation_formal_report.json)。

## Validation boundaries

Runner gate Phase 7A public report，拒绝 manifest-supplied execution，要求 private input/output 和 public-repo-fetch confirmations，拒绝 local-clone/synthetic sources，只为 freshness rejection 读取 prior Phase 5B 与 Phase 7B private material；当 overlap rejection 发现 nonzero prior overlap 时，以 repair/no-claim status 停止。Public artifact 仍为 aggregate-only，不发布 private overlap details。

## Interpretation

该结果只记录 formal no-claim validation artifact。它不是 method comparison，不是 product/default/runtime/deployment/training claim；未使用 provider、LLM、model update、runtime/default change、deployment change 或新 retrieval family。
