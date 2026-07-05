# OpenLocus v2 FRK Product Workflow Specific Retrieval Repair Design

状态：`frk_product_workflow_specific_retrieval_repair_design_complete_bounded_prototype_authorized`

公开报告：[`artifacts/frk_product_workflow_specific_retrieval_repair_design/frk_product_workflow_specific_retrieval_repair_design_report.json`](../../artifacts/frk_product_workflow_specific_retrieval_repair_design/frk_product_workflow_specific_retrieval_repair_design_report.json)

评估脚本：`eval/frk_product_workflow_specific_retrieval_repair_design.py`

## 范围

本阶段是针对 product-workflow hybrid retrieve arm 的 narrow same-budget repair design-with-static-replay-simulation。它使用 existing trace evidence 与 public reports 对 bounded repair design 做 sanity-check；它不是 prose-only design，不是 prototype execution，也不是 new retrieval experiment。

允许输入包括公开的 product-workflow benchmark 与 failure-decomposition reports、用于 schema/action/arm naming readback 的 evaluator scripts、Phase-1 schema validator，以及只有在 `--confirm-private-input` 后读取的 latest ignored private product-workflow traces。评估器不会 rerun retrieval、search、read、citation validation、source scan、candidate generation、training/scaling、provider/model calls、network/CI、runtime/default changes 或 kernel hardening。

## 设计

选定的 design family 是 `wrong_file_guard_fixed_budget_read_allocation`：

- 保持相同 candidate cap bucket：`count_2_to_5`
- 保持相同 read cap bucket：`count_2_to_5`
- 只使用 existing benchmark channel families：`bm25_text`、`symbol_regex`、`existing_hybrid_retrieve`
- 保持 EvidenceCore currentness 与 label-after-action discipline
- 在第二次 read 前加入 wrong-file/intent consistency guard
- 将 top-k pressure 视为 fixed-budget read allocation 问题，而不是 candidate expansion 授权

## Static replay 结果

对 existing private traces 的 static replay 显示存在 nonzero affected-loss coverage，且没有 dominant unresolved/proxy-risk blocker：

- replayable trace coverage bucket：`count_6_to_20`
- mechanism coverage bucket：`count_6_to_20`
- estimated affected-loss bucket：`count_6_to_20`
- unresolved/inconclusive bucket：`count_0`
- proxy-risk bucket：`low`
- confidence bucket：`high`

所有 concrete-design gates 均通过，包括对 source mechanisms `wrong_file_or_rank_miss` 与 `read_budget_or_topk_limit` 的 exact readback、same budget、no new channel family、schema-valid private replay，以及 aggregate-only privacy。

## Stop/go

授权下一阶段：`frk_product_workflow_bounded_retrieval_repair_prototype`。

不授权：D2/model scaling、RPM training、runtime/default changes、provider/network/CI claims、method/scale/winner/default claims、broad source scans、candidate expansion、本 design phase 中的 new retrieval experiments、kernel hardening continuation、old heuristic chains、raw/private trace publication、FRK-J、FRK-B/C resurrection、FRK-I variants、LDI-B easy continuation、HAAE-SG 或 HAAE-T。
