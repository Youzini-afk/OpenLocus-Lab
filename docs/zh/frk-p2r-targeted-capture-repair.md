# OpenLocus v2 FRK-P2R Targeted Capture Repair

状态：`frk_p2r_capture_repair_complete_haae_a2_replay_authorized`

公开报告：[`artifacts/frk_p2r_targeted_capture_repair/frk_p2r_targeted_capture_repair_report.json`](../../artifacts/frk_p2r_targeted_capture_repair/frk_p2r_targeted_capture_repair_report.json)

评估脚本：`eval/frk_p2r_targeted_capture_repair.py`

## 范围

FRK-P2R 是由 FRK-P2 授权的 executable targeted capture repair。它重新生成更丰富的 private nested `openlocus.state_action_trace.v2` rows，并修复两个 blocker 的 target-scoped coverage accounting：

1. `state.candidate_pool` coverage low。
2. `outcome.downstream_proxy` row-level missingness high，且 all-row coverage low。

本阶段不是 new retrieval prototype，也不是 design/audit-only phase。

## 执行契约

- 默认模式在没有 `--confirm-private-output` 时是 unavailable/no-op。
- Private output rows 只写入 ignored `runs/frk_p2r_targeted_capture_repair_private_*/`。
- 使用与 FRK-P2 相同的 manifest shape、product-workflow families、fixed caps 和 existing channel families：`bm25_text`、`symbol_regex`、`existing_hybrid_retrieve`。
- Local bounded actions 仍然是 existing retrieval/search、`openlocus read` 和 `openlocus citations validate`。
- 本阶段只增加 instrumentation：candidate count、unique file count、rankpack arm/size/dedup/diversity、remaining read/validate budget、top1 source/channel、label-blind top1 role guess，以及 stop rows 上的 final downstream proxy。
- Candidate-pool coverage 只在 retrieval 结果可用后的 rows（`read_next`、`validate_now`、`stop`）上评估。Downstream proxy coverage 在 stop/final rows 上评估。公开报告同时给出 all-row 与 target-scoped coverage buckets。

## 结果

本次运行只发布 aggregate-only public output：

- private episode bucket：`count_21_to_50`
- private row bucket：`count_gt_50`
- target-scoped `state.candidate_pool` coverage：`coverage_high`
- target-scoped candidate-pool label-blind feature coverage：`coverage_high`
- candidate miss/rank proxies：`not_available_pre_action`，不是 gold-derived
- target-scoped stop-row `outcome.downstream_proxy` coverage：`coverage_high`
- target-scoped unknown/missingness bucket：`count_0`
- all-row downstream proxy coverage 按设计仍为 `coverage_low`，因为 non-final rows 使用 `not_applicable_nonfinal`
- schema/privacy/label/currentness/EvidenceCore-separation checks：passed

## Stop/go

全部 positive HAAE-A2 gates 均通过，因此唯一授权下一阶段为：

`haae_a2_offline_action_replay_smoke_over_frk_p2r_v2_rows`

仍然禁止：new retrieval algorithm/channel family、candidate expansion beyond fixed caps、broad source scan、adaptive escalation、provider/model/network/CI、本阶段内 HAAE-A2 replay、RPM-D2 training/model fitting/model scaling、runtime/default change、method/scale/winner/default claim、kernel hardening、raw/private trace publication、FRK-J/B/C、FRK-I revival、HAAE-SG/T、LDI-B easy continuation 和 bounded repair route revival。
