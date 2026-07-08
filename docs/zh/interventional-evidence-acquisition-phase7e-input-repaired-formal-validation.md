# Interventional Evidence Acquisition Phase 7E Input-Repaired Formal Validation

日期：2026-07-08

Status: `repair_formal_pipeline_no_claim`

Authorization: `formal_private_input_private_output_public_repo_fetch_confirmed`

## 范围

Phase 7E 按 Phase 7D input-repair boundary 执行了一次 formal no-claim rerun。它在显式提供 `--confirm-private-input`、`--confirm-private-output` 和 `--confirm-public-repo-fetch` 后，执行 current-run public repository fetch/materialization。Private candidate inputs、manifest、rows、clone materialization 与 replacement audit 只写入 ignored `runs/phase7e_input_repaired_formal_validation/...`。

Public aggregate report：[`phase7e_input_repaired_formal_validation_report.json`](../../artifacts/phase7e_input_repaired_formal_validation/phase7e_input_repaired_formal_validation_report.json)。

## 保持冻结的规则

- Prior-overlap 被视为 input ineligibility，并且 repair 只在 row generation 和 outcome scoring 前进行。
- Replacement 使用 deterministic non-performance rule：`stable_public_candidate_order_then_first_eligible_bucket_only`。
- Manifest-supplied execution、local clone sources、synthetic sources，以及缺少 comparable repo ID 的输入会被拒绝。
- Phase 7A/7C labels、formal caps、EvidenceCore success semantics、privacy boundary 和 no-claim posture 保持冻结。
- Phase 5B、Phase 7B 与 Phase 7C private material 只用于 overlap rejection，不用于 scoring 或 tuning。

## Public result

Public report status 为 `repair_formal_pipeline_no_claim`。Coarse public buckets 记录 formal repo/task target buckets；由于 repaired input 在 row generation/outcome scoring 前仍命中 nonzero prior-overlap bucket，因此 public row bucket 为 zero；replacement bucket 为 `bucket_six_to_eight`，overlap bucket 为 `bucket_nonzero_to_three`，stop/abstain success 为 zero，route-specific validation passed。

公开内容不包含 repository names、URLs、owners、commits、paths、ranges、hashes、snippets、row IDs、task IDs、manifests、run directories、singleton buckets 或 private details。

## Non-claims

该结果不建立 method winner、lift、product/default/runtime/deployment change、provider 或 remote-model claim、training result，也不新增 retrieval family。它只是 aggregate-only formal repair_formal_pipeline_no_claim checkpoint。
