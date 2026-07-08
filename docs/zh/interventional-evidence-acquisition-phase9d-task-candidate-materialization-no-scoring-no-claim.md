# Interventional Evidence Acquisition Phase 9D Task-Candidate Materialization

日期：2026-07-09

Status: `repair_task_materialization_no_claim`

Authorization: `phase9d_task_candidate_materialization_no_scoring_no_claim`

Public report: [`phase9d_task_candidate_materialization_no_scoring_no_claim_report.json`](../../artifacts/phase9d_task_candidate_materialization_no_scoring_no_claim/phase9d_task_candidate_materialization_no_scoring_no_claim_report.json)

## 范围

Phase 9D 仅为 bounded low-resource task-candidate construction 与 private source-reference materialization phase。它 gate 于 Phase 9C public report/status `phase9c_task_construction_materialization_protocol_freeze_no_execution_no_scoring_no_claim`，以及 Phase 9C docs/report 中的 CI references。

Execution 需要两个显式确认：`--confirm-phase9b-private-registry-read` 和 `--confirm-private-output`。Dry self-test 与 report validation 不读取 Phase 9B private registry，也不读取 source repositories。

## Materialization boundary

Phase 9D 只有在显式 private-registry-read confirmation 下，才可读取 ignored Phase 9B private accepted-source registry。它只有在显式 private-output confirmation 下，才可把 private manifests 与 materialization rows 写入 ignored `runs/phase9d_task_candidate_materialization_no_scoring_no_claim/...`。

Task candidates 只是 inventory。它们是 evidence-finding、file-localizable code-task candidates。它们不是 benchmark labels、outcomes、gold rows、success rows，也不是 evidence-success evaluations。Materialization 本身不是 evidence success。

## Deterministic construction rules

Candidate construction 保留 Phase 9B private registry order，并且不使用 random shuffle。Replacement 只能发生在 labels/outcomes/scoring 之前：先考虑同一 source 的 next deterministic candidate，必要时再转到 next source。Replacement 不使用 performance、evidence、model 或 downstream feedback。

Phase 9C caps 保持精确：target task-candidate bucket 48-72、hard cap up to 96、per-source task cap up to 8、minimum distinct sources at least 8。若 caps 后 diversity 低于 minimum，Phase 9D 必须 stop 或 repair，而不能 pass。

## Public result

Public report 仅 aggregate-only。它包含 phase/status/schema、Phase 9C gate refs、private-read authorization attestation、task-candidate inventory summary、materialization summary、diversity summary、no-claim boundary、privacy summary、validation summary，以及 conservative recommendation。

当前 public status 为 `repair_task_materialization_no_claim`。Public aggregate buckets 显示 constructed inventory 为 `bucket_zero`、materialized references 为 `bucket_zero`、observed distinct sources 为 `bucket_zero`，并且 source-reference currentness reread 在私有侧不可用。这是一次失败的 materialization attempt/checkpoint，不是 pass。

Phase 9D 没有 fetch 或 clone public repositories。它只是在显式 private-registry-read confirmation 下，尝试从已经 ignored 的 Phase 9B private accepted-source registry 直接 materialize。Zero-materialization repair state 被保留下来，而不是在原地修成通过。未来如果要为了 materialization 做 public source fetch/clone，必须另开 frozen boundary，并使用显式确认。

这次 materialization failure 不是任何 evidence-acquisition method 成功或失败的证据。它只说明 source-materialization readiness 不足。Private manifests 只保留在 ignored `runs/` 下；public report 不包含 exact repo/source/task/path/hash/snippet/owner/URL/commit/manifest/run-dir/per-source/per-task facts。

## No-claim boundary

Phase 9D 不执行 strategy scoring、labels、outcomes、evidence-success evaluation、model fitting/training、RPM-D2/model scaling、provider/LLM calls、runtime/default/product changes，也不提出 method/product/performance/training/provider/model/scoring/outcome/evidence-success/runtime/default claims。

如果未来另一个 boundary 成功 materialize task rows，这些 rows 也仍然只是 candidate inventory。它们不是 labels、outcomes、gold rows、success rows，也不是 evidence_success。Materialization 本身不是 evidence_success。
