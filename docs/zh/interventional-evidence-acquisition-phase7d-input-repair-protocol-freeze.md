# Interventional Evidence Acquisition Phase 7D Input-Repair Protocol Freeze

日期：2026-07-08

Status: `phase7d_input_repair_protocol_freeze_no_execution_no_claim`

Authorization: `docs_report_only_no_execution`

## 范围

Phase 7D 在 Phase 7C repair_formal_pipeline_no_claim checkpoint 之后，冻结 possible later Phase 7E run 的 input-repair protocol。它只是 docs/report-only：不读取 private rows、manifest、provenance 或 `runs/`；不 fetch 或 clone public repository；不生成 benchmark rows；不执行 outcome scoring；不读取 source；不进行 model fit/training；不使用 provider/network/LLM；不改变 runtime/default/deployment；也不新增 retrieval family。

Public report：[`phase7d_input_repair_protocol_freeze_report.json`](../../artifacts/phase7d_input_repair_protocol_freeze/phase7d_input_repair_protocol_freeze_report.json)。

## 冻结的 input-repair protocol

- Prior-overlap 是 input ineligibility condition。
- Replacement 只允许在 row generation 前、outcome scoring 前进行。
- Replacement selection 必须 deterministic、auditable，在任何 row/outcome effects 前冻结，并且不得基于 performance。
- Replacement logic 不得在 row 或 outcome effects 之后 tune。
- Phase 7A/7C labels、formal caps、EvidenceCore success semantics、privacy boundary 和 no-claim posture 保持冻结。
- Replacement 与 overlap reporting 只能是 aggregate bucket；不得公开 private details 或 singleton buckets。

## Must-not-cross boundary

Phase 7D 不读取 private rows、manifests、provenance、run directories 或 private repository details。它不 fetch/clone public repos，不生成 benchmark rows，不 score outcomes，不 train/fit models，不改变 labels/caps/EvidenceCore/privacy/no-claim rules，不在 effects 之后 tune replacement logic，不发布 private repo details，也不提出 method winner/lift/product/default/runtime/deployment/training claims。

## Phase 7E boundary

Phase 7E 只有在 Phase 7D 已提交且 CI green，并且在既有 low-resource/no-claim 约束下显式进入 Phase 7E boundary 后，才可以执行。任何 Phase 7E output 仍受 aggregate-only public reporting 与 frozen no-claim posture 约束。
