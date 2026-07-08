# Interventional Evidence Acquisition Phase 5A Public-Repo Protocol Freeze

日期：2026-07-07

Status: `phase5a_public_repo_protocol_freeze_no_claim`

Authorization: `design_protocol_only_no_execution`

## 范围

Phase 5A 只冻结可能的 Phase 5B public-repo validation protocol。它只是 design/protocol：不 fetch repositories、不生成 tasks、不写 private rows、不读取 source、不改变 CI/workflow，也不实现 Phase 5B runner。

Phase 4E 仍只是 candidate-preserving、no-claim。Phase 5A 不把该 screen 转换为 winner、lift、product、default、runtime 或 readiness claim。

## 冻结的 Phase 5B 范围

- Task target：120 个 hard tasks；valid range 为 100-150；hard maximum 为 150。
- 7 个 labels 意味着 private rows hard maximum 为 1050。
- Repository target：10-12 个 public GitHub repositories；hard maximum 为 16。
- 任何 Phase 5B execution 前，必须冻结 repository URLs、commit SHAs、strata 和 replacement rules。
- Phase 5B 允许的 network use：只针对 frozen URLs/SHAs fetch public GitHub repositories。
- 禁止：LLM/provider calls、search APIs、remote model calls、model training、runtime/default changes、新 retrieval families、staged runs 和 post-outcome tuning。

## 冻结的 7 个 labels

Phase 5B action labels 精确为：

1. `bm25_then_read_top1`
2. `bm25_then_read_next_unique_file`
3. `symbol_regex_then_read_top1`
4. `symbol_regex_then_read_next_unique_file`
5. `read_related_test_when_available`
6. `stop`
7. `abstain`

## Evidence 与 reporting rule

Candidate-found alone 不是 evidence。Counted success 必须有 current-source read、materialization、hash/currentness verification 和 task tie。

Public report 必须 aggregate-only：不公开 raw task IDs、paths、ranges、hashes、snippets、run directories、manifests、singleton buckets 或 per-task details。可以与 best fixed local/acquisition baseline 比较，但不得说 winner、lift、product、default 或 runtime change。

## Hard-stop oracle

如发生以下任一情况，Phase 5B route 必须 stop/fail：

- valid tasks 少于 100；
- tasks 多于 150；
- private rows 多于 1050；
- staged runs 或 post-outcome tuning；
- public private leak 或 singleton public bucket；
- `stop` 或 `abstain` 有非零 success；
- counted evidence 没有 current-source validation；
- 新增 provider、LLM、training、runtime/default 或 retrieval-family work。

## 当前状态

Phase 5A 只作为 protocol freeze 完成。若未来单独实现，下一步只能是在这些 frozen rules 下执行 Phase 5B。本文不提出 evidence claim。
