# Interventional Evidence Acquisition Phase 7A Fresh Public-Repo Validation Protocol Freeze

日期：2026-07-07

Status: `phase7a_protocol_freeze_no_execution_no_claim`

Authorization: `design_only_no_execution`

## 范围

Phase 7A 冻结 possible later Phase 7B fresh public-repo validation protocol。它只是 design-only：不 fetch 或 clone repository、不生成 tasks、不运行 canary、不读取 source、不读取 private rows 或 `runs/`、不进行 model fit 或 training、不使用 provider/network/LLM、不改变 runtime/default/product，也不新增 retrieval family。

## 冻结的 Phase 7B 范围

- Fresh public repositories 和 tasks 不得在 Phase 5B 中使用过。
- Repository target：8-12；hard maximum 16。
- Task target：80-120；hard maximum 150；每个 repository 最多 20 tasks。
- 同 7 个 labels：`bm25_then_read_top1`、`bm25_then_read_next_unique_file`、`symbol_regex_then_read_top1`、`symbol_regex_then_read_next_unique_file`、`read_related_test_when_available`、`stop`、`abstain`。
- 每个 task 使用 full-panel。
- Possible public statuses 只能是：`stop_no_claim`、`repair_fresh_validation_contract_no_claim`、`fresh_public_repo_validation_positive_no_claim`。

## Freshness 与 replacement rules

Phase 7B 必须私下检查并拒绝与 Phase 5B 的 overlap：repository URL/name/owner（如可得）、pinned commit/SHA、task IDs、paths/ranges/hashes/materialization snippets，以及如果私下可检测的 too-close file-family buckets。Public output 只能公开 boolean/bucket overlap summaries。

Replacement 只允许因为 pre-outcome invalidity：clone failure、pinned SHA unavailable、insufficient eligible files，或 scoring 前 EvidenceCore materialization impossible。禁止在看到 outcomes 后 replacement。

## Evidence 与 reporting boundary

Candidate-found alone 不是 evidence。Counted success 必须有 current source read、materialization、content digest、currentness reread、range match 和 task tie。`stop`/`abstain` success 必须保持 `bucket_zero`。

任何 positive Phase 7B status 也只表示 frozen actions 下、privacy/control checks 成立时的 nonzero aggregate EvidenceCore-valid local evidence acquisition。它不是 method comparison、performance increase、chosen strategy、product/default/runtime/deployment 或 training claim。

Future public reports 必须 aggregate-only：count buckets、label coverage buckets、evidence success buckets、best fixed local/acquisition baseline bucket、privacy summary 和 EvidenceCore validation。禁止公开 repository names/URLs/owners、exact commits/SHAs、exact paths/ranges/hashes/snippets、task IDs/row IDs、manifests/run directories、per-repo/per-task/per-fold details、singleton buckets 和 claim wording。

## 当前状态

Phase 7A 只作为 protocol freeze 完成。Phase 7B runner、clone、task generation 或 validation execution 只能在 Phase 7A 已提交且 CI green，并在既有 low-resource/no-claim 约束下显式进入 Phase 7B 边界后继续。
