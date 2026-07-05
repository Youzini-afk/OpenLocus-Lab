# OpenLocus v2 FRK Product Workflow Failure Decomposition

状态：`frk_product_workflow_failure_decomposition_query_channel_budget_repair_design_authorized`

公开报告：[`artifacts/frk_product_workflow_failure_decomposition/frk_product_workflow_failure_decomposition_report.json`](../../artifacts/frk_product_workflow_failure_decomposition/frk_product_workflow_failure_decomposition_report.json)

评估脚本：`eval/frk_product_workflow_failure_decomposition.py`

## 范围

本阶段解释 FRK product-workflow trace benchmark 中 `openlocus_hybrid_retrieve` 为什么输给 best fixed baseline。它是基于 existing private trace rows 的 executable empirical decomposition。

允许输入仅限 latest ignored private product-workflow trace rows 与 labels、已提交的公开 benchmark report、用于 schema/action/arm naming readback 的 benchmark script，以及 Phase-1 schema validator。评估器在读取 private rows 前要求 `--confirm-private-input`。它不会 rerun retrieval、search、read、citation validation、source scan、candidate generation、provider/model calls、network work、CI、training、model scaling、runtime/default changes、method/winner claims 或 kernel hardening。

## 结果

公开报告仅为 aggregate-only。报告记录 benchmark no-lift readback、private row/episode count buckets、arm-vs-best-baseline outcome matrix buckets、family-level loss concentration buckets 与 mechanism count buckets，但不公开 private trace paths、label paths、task ids、rows、paths、ranges、queries、snippets、hashes、private refs、evidence filenames、exact labels、per-task outcomes 或 per-task mechanisms。

Primary mechanism：`wrong_file_or_rank_miss`。

Secondary mechanism：`read_budget_or_topk_limit`。

Confidence bucket：`high`。

该 decomposition 指向当前 hybrid retrieve candidate 的 query/channel/budget repair-design 问题，而不是 winning/default method 证据。

## Stop/go

授权下一阶段：`frk_product_workflow_specific_retrieval_repair_design`。

不授权：D2/model scaling、RPM training、runtime/default changes、provider/network/CI claims、method/scale/winner/default claims、broad source scans、candidate expansion、new retrieval experiments、kernel hardening continuation、old heuristic chains、raw/private trace publication、FRK-J、FRK-B/C resurrection、FRK-I variants、LDI-B easy continuation、HAAE-SG 或 HAAE-T。
