# OpenLocus v2 FRK-P2 Workflow V2 Task-State Capture Expansion

状态：`frk_p2_workflow_v2_capture_complete_targeted_capture_repair_only`

公开报告：[`artifacts/frk_p2_workflow_v2_task_state_capture_expansion/frk_p2_workflow_v2_task_state_capture_expansion_report.json`](../../artifacts/frk_p2_workflow_v2_task_state_capture_expansion/frk_p2_workflow_v2_task_state_capture_expansion_report.json)

评估脚本：`eval/frk_p2_workflow_v2_task_state_capture_expansion.py`

## 范围

FRK-P2 是由 TraceV2-A 授权的 executable TraceV2 capture expansion。它在 predeclared bounded product-workflow manifest 上直接输出严格 nested `openlocus.state_action_trace.v2` rows。

本阶段只做 trace capture。它不是 design/audit-only phase，不是 new retrieval prototype，也不是 RPM/HAAE training 或 replay。

## 执行契约

- 默认模式在没有 `--confirm-private-output` 时是 unavailable/no-op。
- 默认不需要 private input；不读取 private labels 或 task alignment。
- Private output rows 只写入 ignored `runs/frk_p2_workflow_v2_capture_private_*/`。
- Local actions 限定为 existing channel families `bm25_text`、`symbol_regex` 和 `existing_hybrid_retrieve`，固定 caps，且没有 adaptive escalation。
- 本阶段可为 trace capture 执行本地 OpenLocus retrieval/search、`openlocus read` 和 `openlocus citations validate`，但不新增 algorithms/channels，不超过 caps 扩展 candidates，不 broad scan，不调用 providers/network/CI，不 train/model-scale/RPM-D2，不 replay HAAE-A2，不改变 runtime/defaults，不 harden kernels，也不发布 raw/private traces。

## 结果

本次运行只发布 aggregate-only public output：

- private episode bucket：`count_21_to_50`
- private row bucket：`count_gt_50`
- workflow family、query type、budget class、wrong-file-cost、expected-primary-role 和 support-role buckets：`count_3_to_5`
- action coverage：`retrieve_candidates`、`read_next`、`validate_now` 和 `stop`
- TraceV2 schema validation、label-after-action isolation、currentness leakage scan、EvidenceCore/candidate-state separation 和 privacy scan：passed
- critical nested coverage 大部分为 high，但 candidate-pool 与 downstream-proxy coverage 仍为 low，unknown/missingness 仍为 `count_gt_50`

## Stop/go

本次运行**不授权** HAAE-A2 replay，因为 positive gate 要求所有 critical nested groups 都达到 medium/high coverage，且 unknown missingness 低于 `count_gt_50`。

授权下一阶段：`targeted_frk_p2_workflow_v2_capture_repair_only`。

不授权：new retrieval algorithm/channel family、broad source scan、candidate expansion beyond caps、provider/model/network/CI、RPM-D2 training/model scaling、本阶段内 HAAE-A2 replay/training、runtime/default change、method/scale/winner/default claims、kernel hardening、raw/private trace publication、FRK-J/B/C、FRK-I revival、HAAE-SG/T、LDI-B easy continuation 或 bounded repair route revival。
