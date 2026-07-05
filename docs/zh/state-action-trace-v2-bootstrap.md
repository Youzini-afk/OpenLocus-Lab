# OpenLocus v2 TraceV2-A Product Workflow Trace Bootstrap

状态：`tracev2_a_bootstrap_complete_frk_p2_capture_expansion_authorized`

公开报告：[`artifacts/state_action_trace_v2_bootstrap/state_action_trace_v2_bootstrap_report.json`](../../artifacts/state_action_trace_v2_bootstrap/state_action_trace_v2_bootstrap_report.json)

评估脚本：`eval/state_action_trace_v2_bootstrap.py`

## 范围

TraceV2-A 是 trace-driven fast evidence acquisition 的第一个 executable data-prep/bootstrap phase。它把 existing ignored/private Phase-5 product-workflow traces 与 existing ignored/private Phase-8 bounded-repair prototype traces 转换并审计为严格的 `openlocus.state_action_trace.v2` rows。

本阶段不是 schema-preflight chain，也不是 new retrieval experiment。

## 执行契约

- 默认模式在没有 private confirmations 时是 unavailable/no-op。
- Private inputs 仅限 existing Phase-5 product-workflow traces/labels 和 existing Phase-8 prototype traces/labels，且只有在 `--confirm-private-input` 后读取。
- Private output rows 只有在 `--confirm-private-output` 后写入 ignored `runs/state_action_trace_v2_bootstrap_private_*/`。
- Bootstrap 只执行 conversion/audit：不执行 retrieval、search、read、citation validation、new candidates、source scan、task expansion、provider/model/network/CI、training/model fitting/RPM-D2、runtime/default change、kernel hardening、method/scale/winner/default claim、raw/private trace publication 或 bounded-repair-route revival。

## TraceV2 schema

转换后的 private rows 使用 schema version `openlocus.state_action_trace.v2`，并要求以下 top-level groups：

`schema_version`, `trace_id`, `episode_id`, `step_index`, `task`, `state`, `action`, `behavior_policy`, `observation`, `evidence_linkage`, `outcome`, `privacy_execution`, `source_lock`。

`state` group 嵌套为 `candidate_pool`、`rankpack`、`evidence_state`、`budget_state` 和 `uncertainty_state`。`observation` group 嵌套 observed cost buckets，`outcome` group 嵌套 downstream proxy buckets。Legacy traces 中不可观察的事实会显式标为 `unknown` 或 `not_observable_from_source_trace`；这些值会计入 critical-coverage gates 的 missingness。

Validator 会拒绝 unknown top-level keys、missing required groups、bad action enums、duplicate/non-monotonic steps、labels before action、label/gold leakage into state/action、post-action currentness in pre-action state、invented non-observable state facts、EvidenceCore linkage 与 candidate state 混淆，以及 forbidden execution/privacy flags。

## 结果

本次转换 schema-valid 且 privacy-safe，公开输出仅为 aggregate-only：

- private output row bucket：`count_gt_50`
- private output episode bucket：`count_gt_50`
- action coverage：`expand_depth`、`read_next`、`validate_now` 和 `stop`
- TraceV2 schema validation：passed
- label-after-action isolation：passed
- currentness leakage scan：passed
- critical field coverage：low；unknown/missingness bucket 为 `count_gt_50`；coverage gaps dominate，因为 legacy traces 不包含足够显式的 workflow-family、candidate-pool detail、rankpack、budget、uncertainty、content-SHA/currentness、cost-token 与 downstream-proxy state，不能安全授权 offline replay

## Stop/go

授权下一阶段：`frk_p2_workflow_v2_task_state_capture_expansion`。

不授权：基于 existing v2 rows 的 HAAE-A2 replay、RPM-D2 training/model scaling、runtime/default change、new retrieval prototype、broad FRK repair、kernel hardening、retrieval/search/read/citation validation execution、candidate generation、source scan、provider/network/CI、method/scale/winner/default claims、raw/private trace publication、FRK-J/B/C、FRK-I revival、HAAE-SG/T、LDI-B easy continuation 或 current bounded repair route revival。
