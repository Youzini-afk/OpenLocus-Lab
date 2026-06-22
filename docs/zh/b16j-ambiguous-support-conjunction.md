# B16-J Ambiguous-Support Conjunction Live-Provider Smoke（公开仅聚合 artifact）

> 本中文文档与英文文档 `docs/en/b16j-ambiguous-support-conjunction.md` 一一对应。

## 范围与声明边界

B16-J 是最后一个 B16 atom-redesign 尝试。它构造 ambiguous-support 任务，
其中 support-only 按设计不提供 target binding：每个任务有多个安全
plausible target 文件/符号，相同的抽象 support rule 适用于多个候选。

- 声明级别：`ambiguous_support_conjunction_downstream_smoke_only`。
- 模式：`public_aggregate_synthetic_task_family_matrix`；阶段 `B16-J`。
- B16-J 是 **eval/诊断专用**。允许：在有界合成 ambiguous-support
  file-choice 任务上的 live-provider 行为。禁止：下游价值证明、BEA 优越性、
  method/default/winner、基准性能、真实用户任务声明、calibration、promotion、
  runtime/retriever/pack/backend/default-policy/EvidenceCore 改动。

## Arms

1. **`control_sparse`**：无 atom。
2. **`ambiguous_target_only`**：target file cue + target symbol cue；无 support。
3. **`ambiguous_support_only`**：support module cue + ambiguous support rule；
   无 target 文件名/符号/unique noun/确切答案/edit 指令。
4. **`ambiguous_distractor_plus_support`**：distractor + support + rule；错误 binding。
5. **`ambiguous_target_plus_support`**：target + support + rule（conjunction arm）。

主对比：`ambiguous_target_plus_support` vs `ambiguous_support_only`、
vs `ambiguous_target_only`、vs `ambiguous_distractor_plus_support`。

## Ambiguous support 设计

target 文件和 distractor 文件都包含相同符号。support rule 适用于两者。
support-only text 不包含 target 文件名、target 符号、unique noun、确切答案、
edit 指令或 test 路径/名。

## 验证

```text
python3 -m py_compile eval/b16j_ambiguous_support_conjunction.py  => PASS
python3 eval/b16j_ambiguous_support_conjunction.py --self-test  => PASS (329/329 checks)
python3 eval/b16j_ambiguous_support_conjunction.py --out ...  => PASS
  (status: blocked_remote_not_enabled, forbidden_scan: pass,
   self_test_passed: true, phase: B16-J,
   bea_superiority_claimed: false, support_cue_ambiguous: true)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## 手动 CI 结果

手动 real-provider CI run `27953321504` 已通过：8 任务 x 5 arms = 40 次 live provider calls；forbidden scan pass；私有 SCORE/event manifest 各 `record_count=40` 且 `path_publicly_serialized=false`；329/329 self-test。结果：`control_sparse` solve/test=0.0、selected_target_file_rate=0.125、wrong_file_edit_rate=0.875；`ambiguous_target_only` solve/test=0.0、selected_target_file_rate=1.0；`ambiguous_support_only` solve/test=0.25、selected_target_file_rate=0.25、selected_distractor_file_rate=0.625、wrong_file_edit_rate=0.75；`ambiguous_distractor_plus_support` solve/test=0.625、selected_target_file_rate=0.625、selected_distractor_file_rate=0.375；`ambiguous_target_plus_support` solve/test=1.0、selected_target_file_rate=1.0、wrong_file_edit_rate=0.0。`ambiguous_target_plus_support` 的主 delta：vs `ambiguous_support_only` solve/test delta=+0.75、wrong_file_edit_rate delta=-0.75、selected_target_file_rate delta=+0.75；vs `ambiguous_target_only` solve/test delta=+1.0；vs `ambiguous_distractor_plus_support` solve/test delta=+0.375、wrong_file_edit_rate delta=-0.375。机制 summary：`target_support_conjunction_required_count=6`、`support_only_sufficient_count=2`、`target_only_sufficient_count=0`、`distractor_hurts_count=3`、`ambiguous_support_wrong_binding_count=6`、`wrong_file_selection_count=6`、`all_arms_solved_count=0`、`sparse_solved_count=0`。解释：在 role-neutral 文件名和完整 prompt 泄漏自测之后，B16-J 终于在该有界合成切片上隔离出 target+support conjunction 信号；support-only 多数任务不再足够（2/8），target-only 0/8，而 ambiguous support 加 target binding 后 8/8。该结果仍只是 smoke-level 合成 live-provider 机制结果，不是下游价值证明、BEA 优越性、method-winner/default、benchmark/performance、calibration、promotion 或 runtime/EvidenceCore 改动。

## 注意事项

- B16-J 是 eval/诊断专用。不是下游价值/BEA 优越性/method winner/default/
  benchmark/calibration/promotion/runtime/EvidenceCore 声明。
- support cue 按构造意图是 ambiguous；support-only 不提供 target binding，
  除非 live 模型仍能绕过该设计推断出 binding。
- 有界合成样本。sufficiency 限于"在此有界合成 ambiguous-support file-choice
  切片上"。
- 所有 no-claim/no-runtime-change flag 为 false。live-run flag 仅在 live run
  时为 true。无 runtime/retriever/pack/model/backend/default-policy 文件修改。
