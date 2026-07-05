# OpenLocus v2 FRK Product Workflow Bounded Retrieval Repair Prototype

状态：`frk_product_workflow_bounded_retrieval_repair_prototype_complete_no_lift_stop_or_failure_decomposition`

公开报告：[`artifacts/frk_product_workflow_bounded_retrieval_repair_prototype/frk_product_workflow_bounded_retrieval_repair_prototype_report.json`](../../artifacts/frk_product_workflow_bounded_retrieval_repair_prototype/frk_product_workflow_bounded_retrieval_repair_prototype_report.json)

评估脚本：`eval/frk_product_workflow_bounded_retrieval_repair_prototype.py`

## 范围

本阶段是先前授权的 same-budget retrieval repair 的 executable bounded prototype。它只新增一个 prototype arm：`frk_bounded_repair_wrong_file_guard_fixed_budget`。

评估器读取 Phase-5 benchmark report、Phase-6 decomposition report、Phase-7 design report，并且只有在 `--confirm-private-input` 后读取 existing private product-workflow traces。只有在 `--confirm-private-output` 后，才会把 Phase-1 schema-valid private prototype rows 写入 ignored `runs/frk_product_workflow_bounded_repair_private_*/`。

## 执行契约

- 只执行 local OpenLocus actions
- 与 Phase 5 使用相同 task set
- candidate/read/validate cap bucket 保持 `count_2_to_5`
- channel families 限制为 existing `bm25_text`、`symbol_regex`、`existing_hybrid_retrieve`
- 不新增 channels、providers、network、CI、source scan、candidate generation、candidate expansion、training、runtime/default changes 或 kernel hardening
- wrong-file/intent guard 在第二次 read 前执行；若不可判定，则使用 deterministic fixed ordering
- labels/gold 只在 action selection 之后用于 private scoring

## 结果

Prototype 完成，schema/privacy/currentness gates 通过，但相对 previous hybrid 与 best fixed baseline 没有 lift：

- prototype utility bucket：`rate_25_to_50`
- previous hybrid bucket：`rate_25_to_50`
- best fixed baseline bucket：`rate_50_to_75`
- delta vs previous hybrid：`negative_delta`
- delta vs best fixed baseline：`negative_delta`

Mechanism-impact buckets 仅以 aggregate-only 形式发布，覆盖 wrong-file/rank-miss、read-budget/top-k pressure、no-hit、stale/currentness failure 与 validation failure。

## Stop/go

收口决策：停止当前 bounded repair candidate。授权下一路线：`none_for_current_repair_candidate`；只有未来出现单独证明的 `new_product_workflow_pain_or_new_trace_evidence_decision` 时才能重新选择新路线。

不授权：D2/model scaling、RPM training、runtime/default changes、provider/network/CI、method/scale/winner/default claims、broad source scan、candidate expansion、new channel families、kernel hardening、raw/private trace publication、FRK-J、FRK-B/C resurrection、FRK-I revival、LDI-B easy continuation、HAAE-SG 或 HAAE-T。
