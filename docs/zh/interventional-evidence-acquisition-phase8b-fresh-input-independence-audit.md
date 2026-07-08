# Interventional Evidence Acquisition Phase 8B Fresh-Input Independence Audit

日期：2026-07-08

Phase 8B 仅是 input-construction 和 independence-audit checkpoint。它 gate Phase 8A public protocol freeze，并且只有在显式确认 private output、public repository fetch 和 prior private provenance read 后，才把 candidate registry/manifest 写入 ignored `runs/` storage。

Public report 仅为 aggregate-only：[`phase8b_fresh_input_independence_audit_report.json`](../../artifacts/phase8b_fresh_input_independence_audit/phase8b_fresh_input_independence_audit_report.json)。它记录 status `repair_input_independence_contract_no_claim`：audited registry 保持 no-scoring boundary，并报告 overlap 与 comparable-identity miss 为 zero，但 accepted-repo target missed。Public output 不包含 private repository names、URLs、owners、commits、paths、ranges、hashes、snippets、task IDs、row IDs、manifest paths 或 run directories。

本 phase 不执行 scoring，不生成 labels，不生成 result values，不比较 evidence strategies，不执行 seven-label panel，不声明 route success，也不提出 method/product/default/runtime/provider/training claim。Conservative outcome 是在任何 later scoring phase 被考虑前保持 repair/no-claim。
