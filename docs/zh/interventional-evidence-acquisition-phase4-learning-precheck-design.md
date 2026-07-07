# Interventional Evidence Acquisition Phase 4 Learning Precheck Design

日期：2026-07-07

Phase: `phase4_action_outcome_learning_precheck_design`

Status: `phase4_action_outcome_learning_precheck_design_only_no_training_no_claim`

这只是 design。它不训练 model，不授权 training，不读取 private rows，不收集 data，不改变 CI，不改变 runtime/default behavior，不新增 retrieval families，也不提出 method claim。

Phase 4A non-training precheck 现已在既有 ignored Phase 2/3 private rows 上本地运行。Public report：[`phase4a_private_row_feature_leakage_balance_precheck_report.json`](../../artifacts/phase4a_private_row_feature_leakage_balance_precheck/phase4a_private_row_feature_leakage_balance_precheck_report.json)，status 为 `feature_balance_precheck_ready_no_training`。它只检查 feature contract、leakage rules 和 class balance。不训练、不拟合、不评分、不排序，也不声称 predictive performance。

## Phase 2、Phase 3 和 Phase 3B 说明了什么

Phase 2 和 Phase 3 说明 small local comparison protocol 可以在 hard current-source tasks 上运行，并在 bucket level 复现同类 pattern：

- controls 保持 `count_0`；
- EvidenceCore materialization checks 保持 intact；
- public outputs 保持 aggregate-only；
- best fixed local/acquisition baseline buckets 在 public screens 中是 nontrivial。

Phase 3B 将这些内容作为 public replication summary 收尾。它没有证明 method winner、lift、signal、product readiness 或 default change。

这足以设计一个 learning precheck，但不足以 training、deploy 或 promote model。

## Future learning question

Pre-action、non-leaky features 是否能预测在 hard tasks 上哪个 local evidence-finding action 值得尝试？

该问题只面向 future screen。它不声称 learning 一定有效。

## Allowed future features

Future feature rows 只能使用 action 前已经存在的信息：

- query 或 task coarse family bucket；
- candidate pool coarse stats，例如 bucketed count、top-score bucket 和 rank-diversity bucket；
- action label；
- budget bucket 和 coarse availability flags；
- 如果未来存在 multi-step trace，可使用 prior step count 或 budget bucket。

所有 features 应为 bucketed 或 categorical。Public output 必须保持 aggregate-only。

## Forbidden and leaky features

Future precheck 不得使用会泄露答案或暴露 private data 的 features：

- actual success label；
- target path、range、hash 或 content；
- post-action read result；
- downstream validation result；
- exact private task ID；
- source snippets；
- gold labels；
- provider payloads、prompts 或 responses。

任何 leakage rule failure 都应 fail closed。

## Future target labels

可能的 target labels，仅 design：

- `evidence_success`，使用与 Phase 2/3 相同的 EvidenceCore definition；
- `cost_adjusted_success_bucket`，只有在之后单独设计后才可使用。

`stop` 和 `abstain` 仍保持 controls。Candidate-found alone 不是 evidence。

## Split discipline

Future precheck 必须避免 task leakage：

- 尽可能按 task family、repo 或 file-family hold out；
- train/validation splits 之间不得有 task leakage；
- public output 中不得包含 exact paths、ranges、hashes、snippets、private IDs 或 private manifests；
- public reports 只使用 buckets。

## Minimum precheck before any training

在考虑任何 model training 前，future design 必须先：

- aggregate-only 检查 feature coverage；
- aggregate-only 检查 class balance；
- 使用 fail-closed validator 检查 leakage rules；
- 在运行前写出 stop/go thresholds。

通过该 precheck 也不是 model evidence。它只说明 tiny learning experiment 是否安全到可以考虑。

## Stop/go outcomes

- `stop_no_learning_claim`：停止；无 learning claim。
- `repair_feature_contract_no_claim`：修复 feature、label、split 或 privacy contract。
- `learning_precheck_ready_no_training`：precheck design 已准备好，但仍未授权 training。

## Hard forbidden list

该 Phase 4 design 不授权：

- 现在进行 model training；
- RPM-D2 或 model scaling；
- LLM/provider/network actions；
- runtime/default changes；
- new retrieval families；
- winner、lift 或 signal claims；
- OpenLocus v3 branding 或 product promotion。

任何 future training step 都需要在 feature、label、leakage 和 split rules 写出后，再经过单独 explicit decision。
