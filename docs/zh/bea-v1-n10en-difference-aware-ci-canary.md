# BEA-v1-N10EN Difference-Aware Winner Broader-Sample CI Validation Canary

日期：2026-06-30

BEA-v1-N10EN 是 frozen difference-aware rule 的第一个真正的 bounded public CI canary。它 gate 在 BEA-v1-N10EM public replication package 及其 scoped `n10en_ci_handoff_records` 上，且仅 `workflow_dispatch` 触发。

## 默认行为（fail-closed）

当 `enable_public_github_network` 保持默认 `false` 时，canary **不** clone、build、search 或生成 candidates。它输出 fail-closed / unavailable artifact 并以 exit 0 退出：

```text
status: n10en_public_github_network_disabled_unavailable_fail_closed
forbidden scan: pass
run_phase_labels_used_bool: false
score_phase_labels_used_bool: false
clone_run_bool: false
search_run_bool: false
```

这是提交到 repo 的安全状态。已提交的 artifact 是 network-disabled fail-closed report，不是真实 canary run。

## Network-enabled canary

当显式设置 `enable_public_github_network` 为 `true` 时，canary：

- 仅 clone **manifest-listed public repos**（复用 `ci_clone_and_lock_repo.py`）；
- 先用 `--no-labels` 生成 **public tasks**，使 RUN phase 看不到 labels/gold；
- build 并使用 checked-out local OpenLocus CLI 在 runner temp space 内 materialize temporary public candidates；
- **在 N10EN helper 内部** apply 四个 frozen transforms（不通过 bend `ci_run_strategy_matrix`）；
- 固定 RUN-phase orders 之后，再生成 score-phase labels 并对固定 orders 打分（labels/gold 仅用于 aggregate scoring，不用于 policy）；
- 仅上传 sanitized aggregate-only report。

### Candidate / run contract

- Baseline candidates：`openlocus search bm25 <query> --limit 100 --json`。
- Old-pool proxy：`openlocus search regex <query> --json`（截取前 20；CLI regex 子命令无 `--limit` flag）与 `openlocus search symbol <query> --limit 20 --json` file identities 的 union。
- Frozen transforms（自 N10EL/N10EK 逐字移植）：
  - `baseline` = raw BM25 top-100 order；
  - `full` = full novel-first（novel candidates 在 old-pool 之前，top-10 head）；
  - `guarded` = 保留原 top-5，再从 rank >5 追加 distinct novel files 直到 top-10；
  - `diffaware` = 若 top5 novel candidate item count >= 4 则 `guarded` 否则 `full`。
- Top-5 novelty 计数 **candidate items，不是 distinct files**。
- RUN phase 输入仅为 public tasks；不读取 labels/gold。
- Orders 仅写入 runner temp space，从不 upload。

### Score contract

- Labels/gold 仅在 RUN outputs 固定之后生成/读取。
- Gold 仅用于 aggregate scoring，从不用于 policy。
- Report booleans：`run_phase_labels_used_bool=false`、`score_phase_labels_used_bool=true`、`gold_used_for_policy_bool=false`。

## Aggregate report schema

Sanitized report 仅含 aggregate。它记录：schema/phase/status；N10EM gate 及 scoped handoff 授权；repo/task/candidate counts；`baseline`/`full`/`guard`/`diffaware` top10/top20/top50/top100；lost baseline top10；selected-arm counts；top-5 novelty buckets；citation-validity aggregate；run/score flags；privacy scan；claim boundaries。

artifact 中禁止：repo names/URLs、commit SHAs、task IDs、queries、paths/filenames、candidate lists/orders、labels/gold spans、exact ranks、scores、snippets/content、hashes/provider payloads。

## CI pass/fail semantics

workflow 仅在 contract failures 时失败：N10EM gate 失败、build/clone 失败、task-generation 失败、no tasks、privacy-scan 失败、RUN phase 使用 labels、provider/network policy 违反、citation-validation 失败、raw-upload 违反。

Outcome regression 是有效的 research result，**不是** infrastructure failure。outcome status 记录 `positive` / `neutral` / `regression` 并 handoff 给 N10EO。

## Boundary

N10EN 仅授权 bounded public CI clone/build/search、runner temp space 内的 temporary public candidate materialization、RUN outputs 固定之后的 score-phase labels，以及 sanitized aggregate upload。它不授权 private rows、provider/model network、remote embeddings、QuIVer/dense real、external benchmark downloads、raw candidate/label/query/path upload、runtime/default changes、selector/reranker、method-winner claims、downstream claims、heldout/generalization claims、scaled retrieval 或 production retrieval changes。

## Artifact

- Helper：`eval/bea_v1_n10en_difference_aware_ci_canary.py`
- Workflow：`.github/workflows/bea-v1-n10en-difference-aware-ci-canary.yml`
- Report：`artifacts/bea_v1_n10en_difference_aware_ci_canary/bea_v1_n10en_difference_aware_ci_canary_report.json`
