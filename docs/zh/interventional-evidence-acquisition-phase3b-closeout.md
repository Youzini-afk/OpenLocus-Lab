# Interventional Evidence Acquisition Phase 3B Closeout

日期：2026-07-07

Phase: `phase3b_cross_phase_public_replication_closeout`

Status: `phase3b_cross_phase_public_replication_closeout_no_claim`

这是 public closeout only。它只使用已经公开的 Phase 2 和 Phase 3 aggregate reports。它不读取 private rows，不为新 evidence 读取 source，不收集 data，不新增 scripts，不新增 evaluator modes，也不创建 private artifacts。

## Public inputs

- Phase 2 report：[`phase2_small_fair_local_comparison_pilot_report.json`](../../artifacts/phase2_small_fair_local_comparison_pilot/phase2_small_fair_local_comparison_pilot_report.json)。
- Phase 3 report：[`phase3_independent_local_holdout_validation_screen_report.json`](../../artifacts/phase3_independent_local_holdout_validation_screen/phase3_independent_local_holdout_validation_screen_report.json)。

两个 reports 都是 public aggregate-only reports。

## Replicated bucket-level pattern

Phase 2 和 Phase 3 在 bucket level 上显示同一 protocol-level pattern：

- 两者都通过各自 public reports 使用的 local validation checks。
- 两个 public reports 都是 no-claim positive screens。
- 两者都报告 best fixed acquisition baseline bucket `count_21_to_50`。
- 两者都报告 best fixed local baseline bucket `count_21_to_50`。
- 两者都报告 control success bucket `count_0`。
- EvidenceCore boundaries 保持成立：candidate-found 不是 evidence，counted success 需要带 hash/currentness checks 的 current-source materialization。
- Private/public boundaries 保持成立：private rows 未公开，public outputs 保持 aggregate-only。

这说明 small local comparison protocol 值得作为 research asset 保留。

## 这不证明什么

该 closeout 不证明哪个 method 最好。Best fixed label 是 baseline，不是 winner。

它也不支持：

- lift 或 signal claims；
- product readiness claims；
- runtime/default changes；
- provider/network changes；
- model training；
- OpenLocus v3 branding。

## Risks and limits

- Buckets 是 coarse 的。
- Exact effects 因 privacy 被隐藏。
- Private tasks 不能被 public audit。
- Positive screens 不是 generalization proof。
- Best fixed label 是 baseline，不是 winner。

## Future Phase 4 note

如果有任何 Phase 4，应先从 design-only action-outcome learning precheck 开始。在写出并审查 feature、label、leakage 和 split rules 之前，不应开始 model training。
