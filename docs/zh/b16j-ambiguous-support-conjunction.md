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

## 注意事项

- B16-J 是 eval/诊断专用。不是下游价值/BEA 优越性/method winner/default/
  benchmark/calibration/promotion/runtime/EvidenceCore 声明。
- support cue 按构造意图是 ambiguous；support-only 不提供 target binding，
  除非 live 模型仍能绕过该设计推断出 binding。
- 有界合成样本。sufficiency 限于"在此有界合成 ambiguous-support file-choice
  切片上"。
- 所有 no-claim/no-runtime-change flag 为 false。live-run flag 仅在 live run
  时为 true。无 runtime/retriever/pack/model/backend/default-policy 文件修改。
