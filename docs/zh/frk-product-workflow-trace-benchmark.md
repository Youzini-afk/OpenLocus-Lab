# OpenLocus v2 FRK Product Workflow Trace Benchmark

状态：`frk_product_workflow_trace_benchmark_complete_no_lift_failure_decomposition_or_trace_expansion`

公开报告：[`artifacts/frk_product_workflow_trace_benchmark/frk_product_workflow_trace_benchmark_report.json`](../../artifacts/frk_product_workflow_trace_benchmark/frk_product_workflow_trace_benchmark_report.json)

评估脚本：`eval/frk_product_workflow_trace_benchmark.py`

## 范围

本阶段实现 OpenLocus v2 trace-driven evidence-acquisition 的下一个 executable product-workflow benchmark。它是 fixed、bounded、local 的产品工作流基准，不是 preflight、audit、kernel hardening continuation、training run、provider run、CI claim、runtime/default change、method claim、scale claim 或 winner claim。

benchmark 在可用时执行真实本地 OpenLocus CLI actions，并比较 same-budget local arms：

- `text_bm25_baseline`
- `symbol_regex_baseline`
- `openlocus_hybrid_retrieve`

公开 artifact 仅为 aggregate-only。Private task ids、expected labels、paths、ranges、hashes、snippets、queries、per-task outcomes、private refs、evidence filenames 与 private trace paths 都只保留在 ignored private storage，不公开。

## 执行与覆盖

本次执行的公开 aggregate report 记录：

- task coverage bucket：`count_6_to_20`
- workflow family coverage：CLI/API lookup、EvidenceCore/currentness/citation validation、trace/report/schema debugging、docs/readback consistency、index/search behavior
- arm coverage：三个 same-budget arms
- episode coverage bucket：`count_gt_50`
- row coverage bucket：`count_gt_50`
- action coverage：`bounded_retrieval`、`read_current_source`、`validate_evidence`、`workflow_step`
- Phase-1 RPM trace schema pass、labels-after-action isolation、pre-action currentness non-leakage、privacy pass，以及 aggregate-only publication

Primary success proxy 是 `validated_current_evidence_matches_private_expected_workflow_need`，只以 aggregate buckets 发布。

## 结果

benchmark 已达到 diversity 与真实本地执行要求，但本次 OpenLocus hybrid retrieve arm 没有超过 best fixed baseline：

- best fixed baseline bucket：`rate_50_to_75`
- candidate arm bucket：`rate_25_to_50`
- candidate-vs-best-baseline delta bucket：`negative_vs_best_baseline`

因此这是 no-lift product-workflow 结果。它不是 method、default、scale、winner、runtime、provider、network、CI 或 training claim。

## Stop/go

授权下一阶段：`frk_product_workflow_failure_decomposition_or_trace_expansion`。

不授权：D2/training、runtime/default changes、provider/network/CI claims、method/scale/winner/default claims、raw publication、private trace publication、broad source scan、candidate expansion、kernel hardening continuation、old heuristic chains、FRK-J、FRK-B/C resurrection、FRK-I variants、LDI-B easy continuation、HAAE-SG 或 HAAE-T。
